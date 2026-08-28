"""Regression tests for the Palmistry confidence/human-correlation hardening."""
from __future__ import annotations

from palm_api.quality_gate import apply_checklist_quality_gate, apply_quality_gate
from palm_api.special_marks import _compose_mark_meaning
from palm_api.palm_remedies import PalmRemedy, format_remedy_line
from core.palm_cards import _technical_evidence
from engines.astro.llm.facts import build_palm_facts
from engines.astro.llm.rules import check_prose


def test_poor_photo_withholds_marks_and_timing():
    feats = {
        "quality": {"grade": "poor"},
        "special_marks": [{"type": "trident", "zone": "jupiter", "confidence": 0.9}],
        "lines": {"life": {"detected": True}},
    }
    apply_quality_gate(feats)
    assert feats["special_marks"] == []
    assert feats["quality"]["future_timing_allowed"] is False
    items = [{"kind": "line", "timing": {"estimated_age": 37, "age_range": [35, 38]}}]
    gated = apply_checklist_quality_gate(items, feats["quality"])
    assert gated[0]["timing"] is None


def test_fair_photo_widens_timing_and_hides_marks():
    feats = {"quality": {"grade": "fair"}, "special_marks": [{"type": "star"}]}
    apply_quality_gate(feats)
    assert feats["special_marks"] == []
    gated = apply_checklist_quality_gate(
        [{"kind": "line", "timing": {"estimated_age": 37, "age_range": [35, 38]}}],
        feats["quality"],
    )
    assert gated[0]["timing"]["age_range"] == [34, 39]


def test_special_marks_are_modifiers_not_promises():
    text = _compose_mark_meaning("trident", "jupiter").lower()
    assert "promises" not in text
    assert "guarantee" not in text
    assert "leadership" in text


def test_remedy_line_never_exposes_internal_source_id():
    text = format_remedy_line(PalmRemedy(
        "do", "Optional practice", "Measured focus",
        "Steady attention is what this marking responds to",
        "special_marks.MARK_READING"))
    # The line is the action and nothing else: neither the rule id that
    # produced it nor the internal reason text belongs in front of a customer.
    assert "special_marks.MARK_READING" not in text
    assert text.strip() == "Measured focus"


def test_paid_evidence_does_not_expose_book_source_or_traditional_raw_text():
    html = _technical_evidence({
        "points": [{
            "text": "Career visibility may grow through depth and credibility.",
            "traditional_meaning": "Raw classical text should never be shown",
            "book_label": "palmistry_how_to_master",
            "page": 133,
            "reinforced": True,
        }]
    }, paid=True)
    assert "palmistry_how_to_master" not in html
    assert "Raw classical text" not in html
    assert "Career visibility" in html


def test_palm_facts_respect_poor_photo_gate():
    raw = {
        "confluence": {
            "dominant_hand": "right",
            "life_aspects": [{"key": "career", "strength": "strong", "summary": "Career visibility may improve."}],
        },
        "reading_result": {
            "measurement_quality": {
                "photo_grade": "poor",
                "interpretation_confidence": "low",
                "special_marks_allowed": False,
                "future_timing_allowed": False,
            },
            "future_windows": [{"age_window": [36, 39], "domain": "career"}],
            "special_marks": [{"id": "trident"}],
        },
    }
    facts = build_palm_facts(raw, name="Test", access="paid")
    assert facts.photo_confidence == "low"
    assert facts.future_windows == []
    assert facts.special_mark_ids == []
    assert facts.aspects[0].strength != "strong"


def test_palm_llm_rejects_raw_line_language_and_unsupported_marks():
    class F:
        kind = "palm"
        photo_grade = "fair"
        special_marks_allowed = False
        future_windows = []

    errors = check_prose("Your fate line shows a trident and promises leadership.", {
        "kind": "palm", "photo_grade": "fair", "special_marks_allowed": False,
    })
    assert any(e.startswith("palm_") for e in errors)
