"""A horary follow-up must answer, not announce that it is about to answer.

The chat used to run on the generic consultation prompt, which asks for
200-800 authoritative words citing houses, degrees and nakshatras. A horary
report is one question, one verdict, one window and one remedy, so there was
nothing to fill that with: every turn came back as "Let's delve into the
horary chart provided" and stopped. The facts made it worse — the window the
reader was shown never reached facts.json, so "tell me a date" had no date in
scope at all.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))


class _Plain:
    """Stands in for HoraryPlainAnswer."""

    def __init__(self, answer: str, timing: str, remedy: str) -> None:
        self.answer, self.timing, self.remedy = answer, timing, remedy


PLAIN = _Plain(
    answer="There is no firm yes here, but the chart does not push it far out either.",
    timing="The nearest window is 23 Sep to 29 Oct 2026.",
    remedy="Put your thoughts in writing and re-read what you have already sent.",
)
TIMING = {
    "window": "Sep-2026", "until": "Oct-2026",
    "starts": date(2026, 9, 23), "ends": date(2026, 10, 29),
    "days_away": 9, "near": True, "level": "antara",
}


def _facts(plain=PLAIN, timing=TIMING):
    from llm.facts import build_horary_facts

    return build_horary_facts(
        question="when i will recover from fever",
        verdicts={"kp": {"verdict": "uncertain / qualified", "confidence": "low"}},
        summary={"label": "Genuinely open", "confidence": "low",
                 "area": "disease_cure", "is_yes_no": False},
        name="GrahaRekha", access="paid",
        western_judgment={"asc_lord": "Mercury", "q_lord": "Moon",
                          "area": "disease_cure", "house": 6, "timing": []},
        kp_evidence={"kp_number": 114, "cusp_sub_lord": "Mercury",
                     "star_lord": "Moon",
                     "ruling_planets": ["Moon", "Saturn", "Ketu"],
                     "significations": ["1", "6", "11"]},
        plain=plain, timing=timing)


# --------------------------------------------------------------------------
# The facts must carry the answer the reader was actually shown.
# --------------------------------------------------------------------------
def test_plain_lines_and_window_reach_the_chat_payload():
    from llm.facts import public_fact_payload

    p = public_fact_payload(_facts())
    assert p["plain_answer"] == PLAIN.answer
    assert p["plain_timing"] == PLAIN.timing
    assert p["plain_remedy"] == PLAIN.remedy
    assert p["window_known"] is True
    # "tell me a date" needs a date in scope, in the shapes prose uses.
    assert "23 September 2026" in p["allowed_dates"]
    assert "Oct 2026" in p["allowed_dates"]


def test_kp_payload_carries_no_chart_mechanics():
    """The KP reader is never shown lords or ruling planets — chat must not be
    handed them either, or it pads the answer with them."""
    from llm.facts import public_fact_payload

    p = public_fact_payload(_facts())
    assert p["querent_planet"] == "" and p["quesited_planet"] == ""
    assert p["cusp_sub_lord"] == "" and p["star_lord"] == ""
    assert p["ruling_planets"] == [] and p["significations"] == []
    assert p["moon_description"] == ""
    # The Western remedy string put "Pacify Moon … Om Chandraya Namah" back in.
    assert "Pacify" not in p["hindering_remedy"]
    assert p["hindering_planet"] == "" and p["supportive_planet"] == ""
    assert p["plain_remedy"] == PLAIN.remedy


def test_window_known_is_false_when_the_chart_named_no_window():
    from llm.facts import public_fact_payload

    plain = _Plain(answer=PLAIN.answer,
                   timing="The chart does not mark out a clear window for this.",
                   remedy=PLAIN.remedy)
    p = public_fact_payload(_facts(plain=plain,
                                   timing={"beyond_horizon": True,
                                           "horizon_years": 5}))
    assert p["window_known"] is False
    assert p["allowed_dates"] == []


# --------------------------------------------------------------------------
# The validator has to catch the promise-instead-of-answer reply.
# --------------------------------------------------------------------------
def test_a_promise_of_analysis_with_no_analysis_is_rejected():
    from llm.validate import _chat_stalls

    for stall in (
        "Hello GrahaRekha, I understand you're seeking clarity on when you "
        "might recover. Let's delve into the horary chart provided to gain "
        "insights.",
        "Based on the horary chart provided, there isn't a specific date. "
        "However, we can explore the astrological factors that influence your "
        "recovery.",
        "Let's break this down to understand the situation better.",
        "I'll take a closer look at what is going on here.",
    ):
        assert _chat_stalls(stall) == ["chat_promise_without_answer"], stall


def test_a_direct_answer_is_not_a_stall():
    from llm.validate import _chat_stalls

    for good in (PLAIN.answer, PLAIN.timing, PLAIN.remedy,
                 "The nearest window is 23 Sep to 29 Oct 2026."):
        assert _chat_stalls(good) == []


def test_a_long_answer_that_delivers_may_still_say_lets_look_at_this():
    """The check is promise-without-delivery, not the phrase itself."""
    from llm.validate import _chat_stalls

    body = ("Let's look at what your chart says about this. " + "word " * 120)
    assert _chat_stalls(body) == []


def test_chart_mechanics_in_a_horary_reply_are_rejected():
    from llm.validate import _chat_horary_jargon

    for bad in (
        "Mars is the querent planet and Jupiter the quesited planet.",
        "The cusp sub-lord does not signify the sixth house.",
        "Your ruling planets point to a slow recovery.",
        "The Moon is moving the situation.",
    ):
        assert _chat_horary_jargon(bad) == ["chat_horary_jargon"], bad
    assert _chat_horary_jargon(PLAIN.answer) == []
    # "Sunday" is not the Sun.
    assert _chat_horary_jargon("Do it on Sunday.") == []


def test_a_date_outside_the_window_is_rejected():
    from llm.validate import _chat_horary_dates

    facts = _facts()
    assert _chat_horary_dates(PLAIN.timing, facts) == []
    assert _chat_horary_dates(
        "You should recover around July 2027.", facts
    ) == ["chat_horary_invented_date"]
    assert _chat_horary_dates(
        "Expect it in September 2026.", facts) == []


# --------------------------------------------------------------------------
# When the model fails, the customer still gets the answer off the page.
# --------------------------------------------------------------------------
def test_fallback_leads_with_the_window_when_they_asked_when():
    from llm.fallback import horary_chat_fallback

    facts = _facts()
    for q in ("tell me a date", "when?", "how long will it take"):
        out = horary_chat_fallback(facts, q)
        assert out.startswith(PLAIN.timing), (q, out)
        # Still a complete answer, not just the one line they poked at.
        assert PLAIN.remedy in out


def test_fallback_leads_with_the_remedy_when_they_asked_what_to_do():
    from llm.fallback import horary_chat_fallback

    out = horary_chat_fallback(_facts(), "what should i do")
    assert out.startswith(PLAIN.remedy)
    assert PLAIN.timing in out


def test_fallback_never_promises_analysis_or_leaks_jargon():
    from llm.fallback import horary_chat_fallback
    from llm.validate import _chat_horary_jargon, _chat_stalls

    for q in ("hi", "tell me a date", "what should i do", "are you sure?"):
        out = horary_chat_fallback(_facts(), q)
        assert _chat_stalls(out) == []
        assert _chat_horary_jargon(out) == []
        assert out.strip()


def test_fallback_on_a_legacy_report_with_no_plain_lines_still_says_something():
    """Horary reports written before the KP path have no plain_* fields."""
    from llm.fallback import horary_chat_fallback

    out = horary_chat_fallback({"kind": "horary", "label": "Genuinely open"},
                               "tell me a date")
    assert "Genuinely open" in out
