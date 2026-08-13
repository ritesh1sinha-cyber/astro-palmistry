"""PalmFacts must not leak detector-only signals or blocked special marks."""
from __future__ import annotations

from engines.astro.llm.facts import build_palm_facts


def _raw(grade="fair"):
    return {
        "confluence": {
            "dominant_hand": "right",
            "life_aspects": [{
                "key": "career",
                "title": "Career & Direction",
                "strength": "strong",
                "summary": "You may do better professionally when you build depth and credibility over time.",
                "points": [{"rule_id": "R25_career", "text": "safe"}],
            }],
            "predictions": [
                {"title": "Your head line", "line_key": "head", "age": 33,
                 "age_range": [30, 36], "text": "A decision phase."},
            ],
        },
        "reading_result": {
            "measurement_quality": {
                "photo_grade": grade,
                "interpretation_confidence": "moderate",
                "special_marks_allowed": grade == "good",
                "future_timing_allowed": grade != "poor",
                "age_precision": "wider_window" if grade == "fair" else "window",
                "quality_note": "Fine marks withheld" if grade != "good" else "",
            },
            "canonical_signals": [
                {"signal_id": "HAND_AIR"},
                {"signal_id": "TRIDENT_ON_JUPITER"},
                {"signal_id": "FATE_LINE_CLEAN"},
            ],
            "future_windows": [{
                "age_window": [30, 36],
                "domain": "mind_decision",
                "line": "head",
                "confidence": "moderate",
            }],
            "special_marks": [{"id": "TRIDENT_ON_JUPITER"}],
        },
    }


def test_fair_photo_blocks_special_marks_and_raw_detector_signals():
    facts = build_palm_facts(_raw("fair"), name="Meera", access="paid")
    assert facts.special_marks_allowed is False
    assert facts.special_mark_ids == []
    assert all("TRIDENT" not in sid for sid in sum((a.signal_ids for a in facts.aspects), []))


def test_semantic_summary_is_preserved_for_llm():
    facts = build_palm_facts(_raw("fair"), name="Meera", access="paid")
    assert facts.aspects[0].semantic_summary.startswith("You may do better professionally")


def test_future_window_keeps_line_domain():
    facts = build_palm_facts(_raw("fair"), name="Meera", access="paid")
    assert facts.future_windows[0]["domain"] == "mind_decision"
