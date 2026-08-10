"""Report-level validation — aggregate QA counts for recognition/past sections."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from qa_checks.age_context_check import age_violations
from qa_checks.claim_validator import (
    is_personalized_claim, legacy_archetype_banned, validate_claim,
)
from qa_checks.duplicate_check import DuplicateTracker
from qa_checks.health_safety_check import health_violations
from qa_checks.semantic_similarity import semantic_too_similar
from qa_checks.specificity import is_specific_enough, specificity_score
from qa_checks.trajectory_check import has_trajectory_contradiction
from qa_checks.why_safety_check import safe_why_text, why_is_safe


@dataclass
class ReportValidationResult:
    age_violations: int = 0
    unsupported_claims: int = 0
    medical_prediction_claims: int = 0
    exact_duplicate_personalized_claims: int = 0
    semantic_duplicate_personalized_claims: int = 0
    semantic_duplicate_warnings: int = 0
    specificity_rejections: int = 0
    generic_fallbacks: int = 0
    legacy_archetype_hits: int = 0
    health_violations: int = 0
    why_violations: int = 0
    trajectory_contradictions: int = 0
    claims_checked: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (
            self.age_violations == 0
            and self.unsupported_claims == 0
            and self.medical_prediction_claims == 0
            and self.exact_duplicate_personalized_claims == 0
            and self.semantic_duplicate_personalized_claims == 0
            and self.specificity_rejections == 0
            and self.generic_fallbacks == 0
            and self.legacy_archetype_hits == 0
            and self.health_violations == 0
            and self.why_violations == 0
            and self.trajectory_contradictions == 0
        )


class ReportValidator:
    """Track personalized vs generic claims with different duplicate rules."""

    def __init__(self) -> None:
        self._personalized = DuplicateTracker()
        self._generic = DuplicateTracker()
        self._personalized_texts: list[tuple[str, tuple]] = []
        self.result = ReportValidationResult()

    def sanitize_why(
        self,
        why: str,
        *,
        band: str,
        meaning=None,
    ) -> str:
        """Return safe why text; count violations on raw input."""
        raw = (why or "").strip()
        if raw and not why_is_safe(raw, band=band):
            self.result.why_violations += 1
            if health_violations(raw):
                self.result.health_violations += len(health_violations(raw))
                self.result.medical_prediction_claims += len(health_violations(raw))
            if legacy_archetype_banned(raw):
                self.result.legacy_archetype_hits += 1
            self.result.errors.append(f"unsafe_why:{raw[:40]}")
        return safe_why_text(raw, band=band, meaning=meaning)

    def check_claim(
        self,
        text: str,
        *,
        band: str,
        signature: tuple,
        meaning=None,
        direction: str = "",
        companion_text: str = "",
    ) -> bool:
        """Return True if claim may ship."""
        self.result.claims_checked += 1
        if not text:
            return False

        if meaning is not None and getattr(meaning, "source_engine", "manifestation_engine") != "manifestation_engine":
            self.result.legacy_archetype_hits += 1
            self.result.errors.append("legacy_source_engine")
            return False

        if legacy_archetype_banned(text):
            self.result.legacy_archetype_hits += 1
            self.result.errors.append(f"legacy_archetype:{text[:40]}")
            return False

        if "timing activity without a confidently specific" in text.lower():
            self.result.generic_fallbacks += 1
            return False

        av = age_violations(text, band)
        if av:
            self.result.age_violations += len(av)
            return False

        hv = health_violations(text)
        if hv:
            self.result.health_violations += len(hv)
            self.result.medical_prediction_claims += len(hv)
            return False

        v = validate_claim(text, meaning, section="recognition")
        if not v["allowed"]:
            self.result.unsupported_claims += 1
            self.result.errors.append(f"{v['reason']}:{text[:40]}")
            return False

        personalized = v.get("personalized_claim", is_personalized_claim(text))
        if meaning and getattr(meaning, "area", "") == "health":
            trace_len = len(getattr(meaning, "evidence_trace", None) or [])
            if trace_len < 2 or not is_specific_enough(text, minimum=4):
                personalized = False
        elif personalized and not is_specific_enough(text, minimum=3):
            self.result.specificity_rejections += 1
            self.result.errors.append(f"low_specificity:{text[:40]}")
            return False

        if direction and companion_text:
            if has_trajectory_contradiction(direction, text, companion_text):
                self.result.trajectory_contradictions += 1
                self.result.errors.append(f"trajectory:{text[:40]}")
                return False

        tracker = self._personalized if personalized else self._generic
        if tracker.check(text, signature):
            if personalized:
                self.result.exact_duplicate_personalized_claims += 1
                self.result.errors.append(f"dup_personalized:{text[:40]}")
                return False

        if personalized:
            for prev_text, prev_sig in self._personalized_texts:
                if prev_sig == signature:
                    continue
                if semantic_too_similar(text, prev_text, threshold=0.90):
                    self.result.semantic_duplicate_personalized_claims += 1
                    self.result.errors.append(f"semantic_dup:{text[:40]}")
                    return False
                if semantic_too_similar(text, prev_text, threshold=0.82):
                    self.result.semantic_duplicate_warnings += 1

        tracker.register(text, signature)
        if personalized:
            self._personalized_texts.append((text, signature))
        return True

    def to_dict(self) -> dict:
        r = self.result
        return {
            "age_violations": r.age_violations,
            "unsupported_claims": r.unsupported_claims,
            "medical_prediction_claims": r.medical_prediction_claims,
            "exact_duplicate_personalized_claims": r.exact_duplicate_personalized_claims,
            "semantic_duplicate_personalized_claims": r.semantic_duplicate_personalized_claims,
            "semantic_duplicate_warnings": r.semantic_duplicate_warnings,
            "specificity_rejections": r.specificity_rejections,
            "generic_fallbacks": r.generic_fallbacks,
            "legacy_archetype_hits": r.legacy_archetype_hits,
            "health_violations": r.health_violations,
            "why_violations": r.why_violations,
            "trajectory_contradictions": r.trajectory_contradictions,
            "claims_checked": r.claims_checked,
            "passed": r.passed,
            "errors": r.errors[:20],
        }
