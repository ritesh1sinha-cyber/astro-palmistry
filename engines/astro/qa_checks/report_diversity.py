"""Combined QA gate with variant retry for one report generation pass."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from interpretation.prediction_meaning import PredictionMeaning

from qa_checks.age_context_check import age_violations
from qa_checks.duplicate_check import DuplicateTracker
from qa_checks.grammar_check import fix_grammar
from qa_checks.health_safety_check import health_violations
from qa_checks.semantic_similarity import semantic_too_similar
from qa_checks.specificity import is_specific_enough, TRANSPARENT_PAID
from qa_checks.unsupported_claims import unsupported_event_detected


class ReportDiversityGate:
    def __init__(self) -> None:
        self.tracker = DuplicateTracker()
        self._headlines: list[tuple[str, tuple]] = []
        self._bullets: list[tuple[str, tuple]] = []
        self.log: list[str] = []

    def _passes(self, text: str, meaning: "PredictionMeaning", *, past: bool) -> bool:
        if meaning.area == "health" and health_violations(text):
            self.log.append(f"health_reject:{text[:40]}")
            return False
        if age_violations(text, meaning.age_band):
            self.log.append(f"age_reject:{text[:40]}")
            return False
        if unsupported_event_detected(text, meaning.manifestations):
            self.log.append(f"unsupported:{text[:40]}")
            return False
        if past and not is_specific_enough(text, minimum=3):
            # Allow transparent fallback through
            if "not provide enough evidence" in text or "full report explains" in text:
                return True
            self.log.append(f"specificity:{text[:40]}")
            return False
        if self.tracker.check(text, meaning.evidence_signature):
            self.log.append(f"exact_dup:{text[:40]}")
            return False
        for prev_text, prev_sig in self._headlines:
            if prev_sig != meaning.evidence_signature:
                if semantic_too_similar(text, prev_text):
                    self.log.append(f"semantic_dup:{text[:40]}")
                    return False
        return True

    def validate_headline(
        self,
        text: str,
        meaning: "PredictionMeaning",
        *,
        max_retries: int = 6,
        past: bool = True,
    ) -> tuple[str, "PredictionMeaning"]:
        from narration.human_renderer import render_future_headline, render_headline

        current_meaning = meaning
        for _ in range(max_retries):
            if past:
                headline = render_headline(current_meaning, past=True)
            else:
                headline = render_future_headline(current_meaning)
            headline = fix_grammar(headline)
            if self._passes(headline, current_meaning, past=past):
                self.tracker.register(headline, current_meaning.evidence_signature)
                self._headlines.append((headline, current_meaning.evidence_signature))
                return headline, current_meaning
            current_meaning = current_meaning.bump_variant()
        headline = fix_grammar(
            render_headline(current_meaning, past=True) if past
            else render_future_headline(current_meaning)
        )
        if past and not is_specific_enough(headline, minimum=3):
            headline = TRANSPARENT_PAID
        self.tracker.register(headline, current_meaning.evidence_signature)
        self._headlines.append((headline, current_meaning.evidence_signature))
        return headline, current_meaning

    def validate_bullets(
        self,
        bullets: list[str],
        meaning: "PredictionMeaning",
    ) -> list[str]:
        out: list[str] = []
        for b in bullets:
            b = fix_grammar(b)
            if unsupported_event_detected(b, meaning.manifestations):
                continue
            if age_violations(b, meaning.age_band):
                continue
            if not is_specific_enough(b, minimum=3):
                continue
            if self.tracker.check(b, meaning.evidence_signature):
                continue
            self.tracker.register(b, meaning.evidence_signature)
            self._bullets.append((b, meaning.evidence_signature))
            out.append(b)
        return out

    def validate_current(
        self, text: str, meaning: "PredictionMeaning"
    ) -> tuple[str, "PredictionMeaning"]:
        return self.validate_headline(text, meaning, past=False)
