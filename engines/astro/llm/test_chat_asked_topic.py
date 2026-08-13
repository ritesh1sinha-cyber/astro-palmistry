"""Follow-ups about the asked question must not be refused as off-topic.

Ask-your-chart for "will I win the case" already answered with a window.
'When can I expect the verdict?' is that same reading, not a new life area.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))


def _case_facts(**kw):
    from llm.schemas import QuestionFacts, WindowFact

    base = dict(
        first_name="Meera",
        access="paid",
        question="will i win the case",
        area_key="legal",
        direction="support",
        confidence="low",
        promise_status="mixed",
        route={"domain": "legal", "topic": "litigation"},
        best=WindowFact(start="April 2030", end="May 2032", confidence="low"),
        windows=[WindowFact(start="April 2030", end="May 2032", confidence="low")],
        allowed_dates=["April 2030", "May 2032"],
    )
    base.update(kw)
    return QuestionFacts(**base)


def test_legal_followups_are_the_asked_topic():
    from llm.rules import followup_is_on_asked_topic

    facts = _case_facts()
    for q in (
        "so, when i can expect result",
        "am asking about case only",
        "legal case am asking..when i can expect verdict",
        "when will the court hearing go",
    ):
        assert followup_is_on_asked_topic(facts, q), q
    assert not followup_is_on_asked_topic(facts, "will I get married next year")


def test_restating_the_asked_case_is_not_an_invented_circumstance():
    from llm.rules import check_prose

    facts = _case_facts()
    assert check_prose(
        "The reading on the case you asked about leans in your favour, "
        "at low confidence. The strongest window already named is "
        "April 2030 to May 2032.",
        facts,
    ) == []
    assert "asserted_circumstance" not in check_prose(
        "You have a case, and the window already named is April 2030 to May 2032.",
        facts,
    )
    # An illness was never asked about.
    assert "asserted_circumstance" in check_prose(
        "You are dealing with an illness that is slowing this down.",
        facts,
    )


def test_full_report_still_cannot_invent_a_court_case():
    from llm.rules import check_prose
    from llm.schemas import ReportFacts

    facts = ReportFacts(first_name="Meera", access="paid")
    assert "asserted_circumstance" in check_prose(
        "You are dealing with a long-running dispute at work.", facts)


def test_deterministic_recap_names_the_window_already_on_the_page():
    from llm.fallback import question_chat_fallback
    from llm.rules import check_prose

    facts = _case_facts()
    text = question_chat_fallback(facts)
    assert "April 2030" in text
    assert "May 2032" in text
    assert check_prose(text, facts) == []
