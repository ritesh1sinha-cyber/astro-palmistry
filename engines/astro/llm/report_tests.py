"""Regression tests for the customer report pipeline.

Run with: python -m pytest engines/astro/llm/report_tests.py -v
"""
from __future__ import annotations

import re
import textwrap
from typing import Any

import pytest

from .report_schema import (
    ClosingGuidance,
    CurrentPeriod,
    CustomerReport,
    FutureOutlook,
    LifeArea,
    LifeState,
    SubjectMeta,
    SummaryBlock,
    Tone,
)
from .report_validator import validate_customer_report, validate_rendered_html
from .customer_report_builder import build_customer_report
from .customer_html_renderer import render_customer_report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class _FakeFacts:
    """Minimal mock for ReportFacts-like objects."""
    def __init__(self, **kw: Any) -> None:
        self.__dict__.update(kw)


def _make_facts(
    name: str = "Priya",
    birth_date: str = "1994-03-15",
    birth_time: str = "02:30",
    birth_place: str = "Pune, India",
    access: str = "paid",
    cards: list[Any] | None = None,
) -> Any:
    if cards is None:
        cards = []
    return _FakeFacts(
        subject_name=name,
        birth_data={"date": birth_date, "time": birth_time, "place": birth_place},
        language="en",
        cards=cards,
        family_notes=[],
        life_state=type("LS", (), {"mind_now": ["career crossroads"]})(),
    )


def _make_prose(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "conversational": True,
        "astrological_basis": "Saturn's transit through your fourth house brings a period of introspection.",
        "interpretation": "You may feel drawn to reassess your foundations and home life.",
        "personality": "You tend to approach change with careful deliberation.",
        "current_phase": "A reflective period marked by Saturn's influence.",
        "recent_months": "Recent months may have brought changes to your home environment.",
        "hardest_area_note": "Family dynamics may feel strained.",
        "mind_now": ["career crossroads", "family expectations"],
        "why_now": "Saturn's transit activates your fourth house of roots and belonging.",
        "family_note": "Elder family members may need more attention.",
        "final_guidance": "Focus on building stable foundations before making major moves.",
        "areas": {
            "career": {
                "conclusion": "Your career shows a mix of promise and challenge.",
                "astrological_basis": "Saturn in the tenth house of career creates a measured pace.",
                "interpretation": "Professional growth comes through patience and persistence.",
                "outlook": "Steady progress rather than rapid advancement.",
                "timing": "Significant career movement is more likely after mid-2026.",
                "manifestation": "You may feel stalled but groundwork is being laid.",
                "remedy": "Focus on skill-building during this preparatory phase.",
                "transition_note": "",
                "tone_label": "Demanding",
                "tone_class": "yellow",
            },
            "health": {
                "conclusion": "Health requires mindful attention.",
                "astrological_basis": "Sixth house emphasis suggests routine matters need care.",
                "interpretation": "Small daily habits will have outsized impact.",
                "outlook": "Gradual improvement through consistent effort.",
                "timing": "Spring months favor health improvements.",
                "manifestation": "Energy levels may fluctuate with seasons.",
                "remedy": "Maintain consistent sleep and exercise routines.",
                "transition_note": "",
                "tone_label": "Mixed",
                "tone_class": "yellow",
            },
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests: Schema validation
# ---------------------------------------------------------------------------
class TestSchema:
    def test_valid_paid_report(self) -> None:
        report = CustomerReport(
            meta=SubjectMeta(name="Test", birth_date="1990-01-01", access="paid"),
            summary=SummaryBlock(headline="Test headline", opening="Test opening text."),
            life_areas=[
                LifeArea(key="career", conclusion="Career looks steady.", interpretation="Steady growth ahead."),
            ],
            life_state=LifeState(
                what_is_on_your_mind=["career decisions"],
                why_this_period_feels_this_way="Saturn transit.",
            ),
            current_period=CurrentPeriod(vedic_period="Saturn Mahadasha"),
            closing_guidance=ClosingGuidance(final_guidance="Stay patient."),
        )
        assert report.meta.access == "paid"
        assert len(report.life_areas) == 1

    def test_empty_area_rejected(self) -> None:
        with pytest.raises(ValueError, match="conclusion must not be empty"):
            LifeArea(key="career", conclusion="", interpretation="Some text.")

    def test_duplicate_area_rejected(self) -> None:
        with pytest.raises(ValueError, match="Duplicate life area keys"):
            CustomerReport(
                meta=SubjectMeta(name="Test", access="paid"),
                life_areas=[
                    LifeArea(key="career", conclusion="A.", interpretation="B."),
                    LifeArea(key="career", conclusion="C.", interpretation="D."),
                ],
            )

    def test_invalid_access_rejected(self) -> None:
        with pytest.raises(ValueError, match="access must be"):
            SubjectMeta(name="Test", access="vip")


# ---------------------------------------------------------------------------
# Tests: Validator on CustomerReport
# ---------------------------------------------------------------------------
class TestValidatorPreRender:
    def test_valid_paid_report_passes(self) -> None:
        report = CustomerReport(
            meta=SubjectMeta(name="Priya", birth_date="1994-03-15", access="paid"),
            summary=SummaryBlock(headline="Headline", opening="Opening."),
            life_areas=[
                LifeArea(key="career", conclusion="Steady.", interpretation="Growth."),
            ],
            life_state=LifeState(what_is_on_your_mind=["topic"], why_this_period_feels_this_way="Saturn."),
            closing_guidance=ClosingGuidance(final_guidance="Stay focused."),
        )
        vr = validate_customer_report(report)
        assert vr.ok, vr.summary()

    def test_placeholder_in_area_fails(self) -> None:
        report = CustomerReport(
            meta=SubjectMeta(name="Test", birth_date="2000-01-01", access="paid"),
            life_areas=[
                LifeArea(
                    key="career",
                    conclusion="This remedy is linked to a relevant chart factor.",
                    interpretation="Some interpretation.",
                ),
            ],
            life_state=LifeState(what_is_on_your_mind=["x"], why_this_period_feels_this_way="Because."),
            closing_guidance=ClosingGuidance(final_guidance="Guidance."),
        )
        vr = validate_customer_report(report)
        assert not vr.ok
        codes = [e.code for e in vr.errors]
        assert "PLACEHOLDER_LEAK" in codes

    def test_internal_data_in_prose_fails(self) -> None:
        report = CustomerReport(
            meta=SubjectMeta(name="Test", birth_date="2000-01-01", access="paid"),
            life_areas=[
                LifeArea(key="career", conclusion="Ashtakavarga score is high.", interpretation="Growth."),
            ],
            life_state=LifeState(what_is_on_your_mind=["x"], why_this_period_feels_this_way="Because."),
            closing_guidance=ClosingGuidance(final_guidance="Guidance."),
        )
        vr = validate_customer_report(report)
        assert not vr.ok
        codes = [e.code for e in vr.errors]
        assert "INTERNAL_DATA_LEAK" in codes

    def test_guarantee_in_prose_fails(self) -> None:
        report = CustomerReport(
            meta=SubjectMeta(name="Test", birth_date="2000-01-01", access="paid"),
            summary=SummaryBlock(headline="Headline", opening="You will definitely succeed."),
            closing_guidance=ClosingGuidance(final_guidance="Guidance."),
        )
        vr = validate_customer_report(report)
        assert not vr.ok
        codes = [e.code for e in vr.errors]
        assert "GUARANTEE_LEAKED" in codes

    def test_missing_name_fails(self) -> None:
        report = CustomerReport(
            meta=SubjectMeta(name="", birth_date="2000-01-01", access="paid"),
            life_areas=[LifeArea(key="career", conclusion="A.", interpretation="B.")],
            life_state=LifeState(what_is_on_your_mind=["x"], why_this_period_feels_this_way="Y."),
            closing_guidance=ClosingGuidance(final_guidance="Z."),
        )
        vr = validate_customer_report(report)
        assert not vr.ok
        codes = [e.code for e in vr.errors]
        assert "META_NO_NAME" in codes


# ---------------------------------------------------------------------------
# Tests: Validator on rendered HTML
# ---------------------------------------------------------------------------
class TestValidatorPostRender:
    def test_clean_html_passes(self) -> None:
        report = CustomerReport(
            meta=SubjectMeta(name="Test", birth_date="2000-01-01", access="paid"),
            summary=SummaryBlock(headline="Headline.", opening="Opening text."),
            life_areas=[LifeArea(key="career", conclusion="Career conclusion.", interpretation="Career interpretation.")],
            life_state=LifeState(what_is_on_your_mind=["topic"], why_this_period_feels_this_way="Reason."),
            closing_guidance=ClosingGuidance(final_guidance="Stay patient."),
        )
        html = render_customer_report(report)
        vr = validate_rendered_html(html)
        assert vr.ok, vr.summary()

    def test_fallback_text_in_html_fails(self) -> None:
        html = '<p>This remedy is linked to a relevant chart factor and more text here.</p>' * 5
        vr = validate_rendered_html(html)
        assert not vr.ok
        codes = [e.code for e in vr.errors]
        assert "PLACEHOLDER_LEAK" in codes

    def test_duplicate_section_detected(self) -> None:
        html = "<html><body>" + ("<h2>Summary</h2><p>Text about astrology and life areas.</p>" * 6) + "</body></html>"
        vr = validate_rendered_html(html)
        codes = [e.code for e in vr.errors] + [w.code for w in vr.warnings]
        assert "DUPLICATE_SECTION" in codes

    def test_empty_html_fails(self) -> None:
        vr = validate_rendered_html("")
        assert not vr.ok

    def test_guarantee_in_html_detected(self) -> None:
        html = "<p>You will definitely have a great year ahead.</p>" * 20
        vr = validate_rendered_html(html)
        codes = [e.code for e in vr.errors] + [w.code for w in vr.warnings]
        assert "GUARANTEE_LEAKED" in codes


# ---------------------------------------------------------------------------
# Tests: Builder produces valid schema
# ---------------------------------------------------------------------------
class TestBuilder:
    def test_builds_from_facts_and_prose(self) -> None:
        facts = _make_facts()
        prose = _make_prose()
        report = build_customer_report(facts, prose, access="paid")
        assert report.meta.name == "Priya"
        assert report.meta.access == "paid"
        assert len(report.life_areas) == 2
        assert report.life_areas[0].key == "career"
        assert "Saturn" in report.current_period.vedic_period or report.current_period.phase_label
        assert len(report.life_state.what_is_on_your_mind) == 2

    def test_free_access_no_areas(self) -> None:
        facts = _make_facts(access="free")
        prose = _make_prose()
        report = build_customer_report(facts, prose, access="free")
        assert report.meta.access == "free"
        assert report.life_areas == []
        assert report.life_state == LifeState()

    def test_validator_passes_on_built_report(self) -> None:
        facts = _make_facts()
        prose = _make_prose()
        report = build_customer_report(facts, prose, access="paid")
        vr = validate_customer_report(report)
        assert vr.ok, vr.summary()

    def test_full_pipeline_produces_valid_html(self) -> None:
        facts = _make_facts()
        prose = _make_prose()
        report = build_customer_report(facts, prose, access="paid")
        html = render_customer_report(report)
        vr = validate_rendered_html(html)
        assert vr.ok, vr.summary()
        assert len(html) > 500
        assert "Priya" in html
        assert "Final Practical Guidance" in html
        assert "Current Life State" in html


# ---------------------------------------------------------------------------
# Tests: Sentence corruption detection
# ---------------------------------------------------------------------------
class TestCorruption:
    def test_double_period_detected(self) -> None:
        vr = validate_rendered_html("<html><body>" + "<p>Text.. more text here about astrology.</p>" * 10 + "</body></html>")
        codes = [e.code for e in vr.errors] + [w.code for w in vr.warnings]
        assert "SENTENCE_CORRUPTION" in codes

    def test_concatenation_detected(self) -> None:
        vr = validate_rendered_html("<p>This is a sentence.This is another.</p>" * 5)
        codes = [e.code for e in vr.errors] + [w.code for w in vr.warnings]
        assert "SENTENCE_CORRUPTION" in codes


# ---------------------------------------------------------------------------
# Tests: No internal data leakage in builder output
# ---------------------------------------------------------------------------
class TestNoLeakage:
    def test_no_scoring_in_schema(self) -> None:
        facts = _make_facts()
        prose = _make_prose()
        report = build_customer_report(facts, prose, access="paid")
        report_json = report.json()
        assert "raw_score" not in report_json
        assert "weighted_score" not in report_json
        assert "lane_html" not in report_json
        assert "anchor_log" not in report_json
        assert "fact_id" not in report_json
        assert "activation_status" not in report_json
