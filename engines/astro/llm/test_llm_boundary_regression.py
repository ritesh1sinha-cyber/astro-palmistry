"""Regression tests for the deterministic -> facts -> LLM boundary.

These tests deliberately do not call Qwen. They protect the contract that
must hold regardless of model/provider.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))


def test_public_payload_hides_internal_and_signal_metadata():
    from llm.facts import public_fact_payload
    from llm.schemas import PalmFacts, PalmAspectFacts

    facts = PalmFacts(
        aspects=[PalmAspectFacts(
            aspect="career",
            signal_ids=["R25_career"],
            point_ids=["R28_career"],
            semantic_summary="Career confidence may strengthen with experience.",
        )],
        facts_hash="secret",
        engine_version="astro-2026.08.11",
    )
    payload = public_fact_payload(facts)
    raw = str(payload)
    assert "R25_career" not in raw
    assert "R28_career" not in raw
    assert "secret" not in raw
    assert "2026.08.11" not in raw
    assert payload["aspects"][0]["semantic_summary"]


def test_free_projection_cannot_contain_exact_windows_or_remedies():
    from llm.facts import project_for_access
    from llm.schemas import CardFacts, ReportFacts, WindowFact

    facts = ReportFacts(
        access="paid",
        cards=[CardFacts(
            area="career",
            status="supported",
            activation_status="active",
            window=WindowFact(
                start="2028-06",
                end="2029-02",
                label="career recognition",
                confidence="high",
                source="validated_confluence",
            ),
            approved_remedies=["approved remedy"],
            remedy_eligible=True,
            allowed_dates=["2028-06", "2029-02"],
        )],
        timing_windows=[WindowFact(
            start="2028-06", end="2029-02",
            label="career recognition", confidence="high",
        )],
    )
    free = project_for_access(facts, "free")
    card = free.cards[0]
    assert not card.approved_remedies
    assert card.remedy_eligible is False
    assert not card.allowed_dates
    assert card.window is not None
    assert card.window.start == ""
    assert card.window.end == ""
    assert free.timing_windows[0].start == ""
    assert free.timing_windows[0].end == ""


def test_question_weak_promise_cannot_be_soft_escalated():
    from llm.validate import validate_prose_against_facts
    from llm.schemas import QuestionFacts

    facts = QuestionFacts(
        question="Will my career improve?",
        promise_status="insufficient_evidence",
        direction="mixed",
        confidence="low",
    )

    class Prose:
        answer = "You have a moderate chance of positive developments."
        def model_dump(self):
            return {"answer": self.answer}

    errors = validate_prose_against_facts(Prose(), facts)
    assert "weak_promise_positive_escalation" in errors


def test_raw_astrology_technical_language_is_rejected():
    from llm.validate import validate_prose_against_facts
    from llm.schemas import HoraryFacts

    facts = HoraryFacts(label="Leaning yes", confidence="moderate")

    class Prose:
        verdict_line = "The sub-lord and karakamsa strongly support this."
        def model_dump(self):
            return {"verdict_line": self.verdict_line}

    errors = validate_prose_against_facts(Prose(), facts)
    # Field-prefixed errors from check_prose_fields (e.g. verdict_line:classical_raw)
    assert any(
        e.startswith("invented_astrology_term:") or ":invented_astrology_term:" in e
        or e.startswith("sanskrit:") or ":sanskrit:" in e or e.endswith("classical_raw")
        or e == "classical_raw"
        for e in errors
    )


def test_customer_boundary_removes_legacy_rule_fragments():
    from qa_checks.customer_text_sanitizer import sanitize_html_document, validate_customer_text

    html = (
        "<p>8th lord Saturn occupies your 6th house.</p>"
        "<p>Sub-lord supports this. karakamsa adds pressure.</p>"
        "<p>Love, Marriage &amp; Emotions</p>"
        "<details><summary>Technical detail</summary>"
        "<p>case-book method</p></details>"
    )
    clean = sanitize_html_document(html)
    assert "8th lord" not in clean.lower()
    assert "sub-lord" not in clean.lower()
    assert "karakamsa" not in clean.lower()
    assert "case-book" not in clean.lower()
    assert "Technical detail" not in clean
    assert ("Relationships & Emotions" in clean
            or "Relationships &amp; Emotions" in clean)
    assert not validate_customer_text(clean)


def test_canonical_why_normalizes_raw_rule_text():
    from canonical_result import _normalized_why
    from report_confluence import Vote

    result = _normalized_why(
        {
            "direction": "support",
            "votes": [
                Vote(
                    "the classical method",
                    1.2,
                    "8th lord Saturn occupies your 6th house.",
                )
            ],
            "families": [],
        },
        "career",
    )
    text = " ".join(result["supporting"] + [
        x for row in result["rows"] for x in row.get("reasons", [])
    ])
    assert "8th lord" not in text.lower()
    assert result["rows"][0]["label"] == "Birth-chart structure"
