"""Regression tests for the canonical full-report -> User Question flow.

The question tab may route a question to a life area, but for areas represented
in the full report it must consume the same CanonicalAreaResult rather than
running a second promise/timing interpretation.
"""
from __future__ import annotations

from datetime import date

import question_answer as QA
import canonical_result
from llm.facts import build_question_facts, project_for_access


def main() -> None:
    fake = {
        "area": "career",
        "promise": {
            "status": "strongly_supported",
            "confidence": "high",
            "direction": "up",
        },
        "activation": {"status": "mixed"},
        "direction": "up",
        "confidence": "high",
        "agreement": "strong",
        "timing": {
            "timing_can_create_promise": False,
            "strong_windows": [{
                "start": date(2028, 6, 1),
                "end": date(2029, 2, 1),
                "aligned": True,
                "confidence": "high",
                "source": "dasha_ashtakavarga_transit_confluence",
                "event_type": "career_window",
                "score": 2.5,
                "period_owns_area": True,
            }],
            "best_window": {
                "start": date(2028, 6, 1),
                "end": date(2029, 2, 1),
                "aligned": True,
                "confidence": "high",
                "source": "dasha_ashtakavarga_transit_confluence",
                "event_type": "career_window",
                "score": 2.5,
            },
        },
        "why": {
            "supporting": ["Career evidence is supportive."],
            "caution": [],
            "rows": [{
                "direction": "support",
                "reasons": ["Career evidence is supportive."],
            }],
        },
        "manifestation": ["role expansion"],
    }

    original = canonical_result.build_area_result
    canonical_result.build_area_result = lambda *a, **k: fake
    try:
        result = QA.answer(
            {"house_lords": {}, "planets": {}},
            "Will I get a promotion?",
            start=date(2026, 8, 11),
        )
        assert result["truth_source"] == "full_report_canonical"
        assert result["canonical_result"] is fake
        assert result["promise"]["status"] == "strongly_supported"
        assert result["activation"]["status"] == "mixed"
        assert result["windows"][0]["strong"] is True

        paid = build_question_facts(result, name="Test", access="paid")
        assert paid.truth_source == "full_report_canonical"
        assert paid.canonical_promise_status == "strongly_supported"
        assert paid.canonical_activation_status == "mixed"
        assert paid.best is not None
        assert paid.best.start == "2028-06-01"
        assert paid.timing_can_create_promise is False

        free = project_for_access(paid, "free")
        assert free.truth_source == "full_report_canonical"
        assert free.canonical_timing
        assert all(not w.start and not w.end for w in free.canonical_timing)
        assert len(free.canonical_evidence) <= 2

        # QA must reject a QuestionFacts payload whose displayed promise has
        # drifted away from the canonical promise.
        from llm.schemas import QuestionProse
        from llm.validate import validate_prose_against_facts
        drift = paid.model_copy(update={"promise_status": "mixed"})
        prose = QuestionProse(
            opening="Here is the answer from your chart.",
            answer="The chart supports this opportunity.",
        )
        errors = validate_prose_against_facts(prose, drift, area="career")
        assert "question_canonical_promise_mismatch" in errors

        print("canonical question flow: PASS")
    finally:
        canonical_result.build_area_result = original


if __name__ == "__main__":
    main()
