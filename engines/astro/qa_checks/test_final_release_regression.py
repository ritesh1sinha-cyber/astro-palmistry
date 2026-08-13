"""Final cross-tab regression guards for Astro/Palm/ Horary/User Question."""
from __future__ import annotations

from pathlib import Path

from qa_checks.customer_text_sanitizer import (
    sanitize_html_document,
    validate_customer_text,
)
from horary_answer import filter_horary_timing_for_question
from palm_api.quality_gate import filter_special_mark_findings


def test_customer_firewall_removes_hybrid_technical_prose():
    html = """
    <div>Rahu–Jupiter period activates your a chart factor connected with this area</div>
    <div>traditional chart check check</div>
    <div>house strength 24 of 56 — below average</div>
    """
    cleaned = sanitize_html_document(html)
    assert "a chart factor connected" not in cleaned.lower()
    assert "traditional chart check check" not in cleaned.lower()
    assert not validate_customer_text(cleaned)


def test_free_question_has_no_placeholder_tokens():
    source = Path(__file__).resolve().parents[1] / "question_answer.py"
    text = source.read_text(encoding="utf-8")
    assert "XXXXXXX" not in text
    assert "XXXX XXXX" not in text


def test_horary_this_year_filters_next_year_trigger():
    verdicts = {
        "western": {"timing": [
            ("2026-10-01", "inside", ""),
            ("2027-07-26", "outside", ""),
        ]},
        "vedic": {},
    }
    western = {"timing": [
        ("2026-11-01", "inside", ""),
        ("2027-07-26", "outside", ""),
    ]}
    vedic = {"timing": [{"date": "2026-12-01"}, {"date": "2027-01-01"}]}
    v, w, vc = filter_horary_timing_for_question(
        "Will this job offer come through this year?",
        "2026-08-12",
        verdicts,
        western,
        vedic,
    )
    assert len(v["western"]["timing"]) == 1
    assert len(w["timing"]) == 1
    assert len(vc["timing"]) == 1


def test_fair_palm_hides_special_mark_findings():
    items = [
        {"kind": "mark", "title": "Trident (Trishul)", "conclusive": {"verdict": "x"}},
        {"kind": "line", "title": "Fate line", "conclusive": {"verdict": "y"}},
    ]
    fair = filter_special_mark_findings(items, {"grade": "fair"})
    good = filter_special_mark_findings(items, {"grade": "good"})
    assert len(fair) == 1 and fair[0]["kind"] == "line"
    assert len(good) == 2
