"""Claim-level validation — reject unsupported concrete events."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Iterable, Optional

if TYPE_CHECKING:
    from interpretation.prediction_meaning import PredictionMeaning


def _rules() -> dict:
    try:
        from interpretation.stage_config import event_claim_rules
        return event_claim_rules()
    except Exception:  # noqa: BLE001
        return {}


def legacy_archetype_banned(text: str) -> bool:
    """True if text contains a banned legacy historical archetype."""
    low = (text or "").lower()
    for phrase in _rules().get("legacy_archetype_banned") or []:
        if phrase.lower() in low:
            return True
    return False


def classify_claim_level(text: str) -> int:
    """Classify claim into levels 1–4 (higher = more specific event)."""
    t = text or ""
    for pat in _rules().get("level_4_patterns") or []:
        if re.search(pat, t, re.I):
            return 4
    for pat in _rules().get("level_3_patterns") or []:
        if re.search(pat, t, re.I):
            return 3
    if re.search(r"\bmay have\b|\bmay\b|\btend to\b|\bcan\b", t, re.I):
        return 2
    return 1


def is_personalized_claim(text: str, *, claim_level: int = 0) -> bool:
    """Personalized claims need stricter duplicate thresholds."""
    level = claim_level or classify_claim_level(text)
    if level >= 3:
        return True
    low = (text or "").lower()
    generic = _rules().get("generic_guidance_markers") or []
    if any(g in low for g in generic):
        return False
    if re.search(r"\byou (have|had|were|are|changed|received|got|married)\b", low):
        return True
    return level == 2 and not low.startswith("this ")


def _manifestations(meaning: Optional["PredictionMeaning"]) -> set[str]:
    if not meaning:
        return set()
    mans = set(meaning.manifestations or [])
    if meaning.caution:
        mans.add(meaning.caution)
    return mans


def validate_claim(
    text: str,
    meaning: Optional["PredictionMeaning"] = None,
    *,
    section: str = "recognition",
) -> dict:
    """Return validation result; reject Level 3+ without matching manifestations."""
    rules = _rules()
    max_level = int(rules.get("max_recognition_level") or 2) if section == "recognition" else 3
    level = classify_claim_level(text)
    mans = _manifestations(meaning)

    if legacy_archetype_banned(text):
        return {
            "allowed": False,
            "claim_level": level,
            "personalized_claim": is_personalized_claim(text, claim_level=level),
            "reason": "legacy_archetype",
            "replacement": None,
        }

    if level > max_level:
        return {
            "allowed": False,
            "claim_level": level,
            "personalized_claim": True,
            "reason": "claim_level_too_high",
            "replacement": _soft_rewrite(meaning),
        }

    req_map = rules.get("level_3_required_manifestations") or {}
    if level >= 3:
        for pattern, required in req_map.items():
            if re.search(pattern, text or "", re.I):
                if not (mans & set(required)):
                    return {
                        "allowed": False,
                        "claim_level": level,
                        "personalized_claim": True,
                        "reason": "unsupported_concrete_event",
                        "replacement": _soft_rewrite(meaning),
                    }

    from qa_checks.unsupported_claims import unsupported_event_detected
    unsupported = unsupported_event_detected(text, mans)
    if unsupported:
        return {
            "allowed": False,
            "claim_level": level,
            "personalized_claim": True,
            "reason": "unsupported_event",
            "replacement": _soft_rewrite(meaning),
        }

    personalized = is_personalized_claim(text, claim_level=level)
    if meaning and not (meaning.evidence_trace or []):
        personalized = False

    return {
        "allowed": True,
        "claim_level": min(level, max_level),
        "personalized_claim": personalized,
        "reason": "ok",
        "replacement": None,
    }


def _soft_rewrite(meaning: Optional["PredictionMeaning"]) -> Optional[str]:
    """Level-1/2 fallback from manifestation IDs."""
    if not meaning:
        return None
    try:
        from narration.recognition_variants import claim_for_manifestation
        return claim_for_manifestation(
            meaning.primary,
            meaning.secondary,
            meaning.age_band,
            narrative_area=getattr(meaning, "narrative_area", "") or getattr(meaning, "area", ""),
        )
    except Exception:  # noqa: BLE001
        return None


def default_claim_level(section: str = "recognition") -> int:
    rules = _rules()
    if section == "recognition":
        return int(rules.get("default_claim_level") or 2)
    return 2
