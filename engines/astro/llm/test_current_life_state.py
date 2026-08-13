"""The current-life-state block must recognise the phase without claiming it.

Two things can go wrong in a trust section, and both are worse than saying
nothing. Naming a subject the reading never flagged is cold reading, and
stating any of it flatly turns "what your chart makes likely" into a claim
about a life we cannot see.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))


def _cards():
    from llm.schemas import CardFacts

    return [
        CardFacts(
            area="money", label="Money & Financial Stability", kind="challenge",
            status="indicated", activation_status="strongly_active",
            confidence="high", agreement="strong", direction="caution",
            support_n=0, caution_n=3,
        ),
        CardFacts(
            area="profession", label="Career & Professional Life", kind="promise",
            status="supported", activation_status="active", confidence="moderate",
            agreement="partial", direction="support", support_n=3, caution_n=1,
        ),
        CardFacts(
            area="learning", label="Learning & Study", kind="promise",
            status="weak", activation_status="inactive", confidence="low",
            agreement="weak", direction="neutral",
        ),
    ]


def _report_facts(access: str = "free"):
    from llm.life_state import build_life_state
    from llm.schemas import ReportFacts

    cards = _cards()
    return ReportFacts(access=access, cards=cards,
                       life_state=build_life_state(cards))


def test_an_active_pressure_area_becomes_a_mind_topic():
    from llm.life_state import build_life_state

    state = build_life_state(_cards())
    topics = {t.area: t for t in state.mind_now}
    assert "money" in topics
    assert topics["money"].likelihood == "likely"
    assert topics["money"].experience, "the topic must carry words to speak with"


def test_a_quiet_unsupported_area_is_not_put_in_their_mind():
    from llm.life_state import build_life_state

    state = build_life_state(_cards())
    assert "learning" not in {t.area for t in state.mind_now}


def test_every_mind_topic_stays_a_possibility():
    from llm.life_state import build_life_state

    for topic in build_life_state(_cards()).mind_now:
        assert topic.is_fact is False


def test_a_supported_area_reads_as_a_supported_chapter():
    from llm.life_state import build_life_state
    from llm.schemas import CardFacts

    state = build_life_state([CardFacts(
        area="profession", label="Career", kind="promise",
        status="strongly_supported", activation_status="strongly_active",
        confidence="high", agreement="strong", direction="support",
        support_n=4, caution_n=0,
    )])
    assert state.chapter_tone == "supported"
    assert state.domains[0].support in ("high", "very_high")


def test_methods_that_disagree_read_as_a_mixed_chapter():
    from llm.life_state import build_life_state
    from llm.schemas import CardFacts

    state = build_life_state([CardFacts(
        area="money", label="Money", kind="promise", status="mixed",
        activation_status="active", confidence="low", agreement="weak",
        direction="mixed", support_n=2, caution_n=2,
    )])
    assert state.chapter_tone == "mixed"
    assert state.domains[0].contradiction is True


def test_a_demanding_running_phase_is_not_reported_as_steady():
    """The card verdicts can read calm while the phase itself is the hard part."""
    from llm.life_state import build_life_state
    from llm.schemas import CardFacts

    quiet = [CardFacts(area="home", label="Home", status="mixed",
                       activation_status="weak", direction="neutral")]
    assert build_life_state(quiet, phase_tone="demanding").chapter_tone == "pressured"


def test_the_life_state_block_carries_no_numbers():
    """Bands, never scores.

    Any digit in the facts grounds that digit for the whole page, so a score
    in this block would quietly license prose to print numbers the date gate
    exists to catch.
    """
    from llm.facts import public_fact_payload

    block = public_fact_payload(_report_facts())["life_state"]
    assert not any(ch.isdigit() for ch in json.dumps(block))


def test_the_mind_block_survives_the_public_allowlist():
    """A field missing from the allowlist is dropped in silence."""
    from llm.facts import public_fact_payload

    block = public_fact_payload(_report_facts())["life_state"]
    assert block["mind_now"], "mind_now must reach the model"
    assert block["mind_now"][0]["label"]
    assert block["chapter_tone"]


def test_free_names_the_themes_without_the_full_area_breakdown():
    from llm.facts import project_for_access

    free = project_for_access(_report_facts(access="paid"), "free")
    assert free.life_state is not None
    assert free.life_state.mind_now
    assert len(free.life_state.domains) <= 3


def test_a_mind_line_must_name_a_topic_the_reading_flagged():
    from llm.validate import validate_mind_now_line

    facts = _report_facts()
    good = "Money may be taking more of your attention than usual right now."
    invented = "A court case may be weighing on you at the moment."
    assert validate_mind_now_line(good, facts) == []
    assert "mind_now_topic_not_in_facts" in validate_mind_now_line(invented, facts)


def test_a_mind_line_must_stay_hedged():
    from llm.validate import validate_mind_now_line

    flat = "Money is the thing weighing on you right now."
    assert "mind_now_stated_as_fact" in validate_mind_now_line(flat, _report_facts())


def test_prose_cannot_assert_a_circumstance_it_cannot_know():
    from llm.rules import check_prose

    facts = _report_facts()
    assert "asserted_circumstance" in check_prose(
        "You are dealing with a long-running dispute at work.", facts)
    assert "asserted_circumstance" in check_prose(
        "Your mother is unwell and that is taking your attention.", facts)
    # The hedged version of the same observation is the whole point of the block.
    assert check_prose(
        "Money pressure may be taking more of your attention than usual.",
        facts) == []


def test_the_why_paragraph_cannot_read_our_own_fields_aloud():
    """Banded levels are input, not phrasing.

    Given "emotional_pressure: low, decision_pressure: high", a model will
    write that sentence back almost verbatim, which is the one line a reader
    would quote as proof that nobody looked at their chart.
    """
    from llm.validate import validate_why_now

    assert "why_now_recites_fact_fields" in validate_why_now(
        "Your emotional pressure is low but the decision pressure is high.")
    assert validate_why_now(
        "Nothing here is heavy on its own, but the choices in front of you "
        "carry more weight than they usually would.") == []


def test_the_hard_area_and_the_mind_block_name_the_same_life():
    """The dashboard and this block must not disagree on the same page.

    Card verdicts alone can rank a quiet area above the one the report is
    already telling them to take care of, so the report's own list of areas
    needing care is what decides.
    """
    from llm.life_state import build_life_state
    from llm.schemas import CardFacts

    cards = [
        CardFacts(area="home", label="Home & Family", status="mixed",
                  activation_status="active", direction="neutral",
                  confidence="moderate", agreement="partial"),
        CardFacts(area="profession", label="Career", kind="promise",
                  status="supported", activation_status="active",
                  confidence="moderate", agreement="partial",
                  direction="support", support_n=3),
    ]
    state = build_life_state(cards, needs_care=["home"])
    assert state.mind_now[0].area == "home"
    assert build_life_state(cards).mind_now[0].area != "home", (
        "without the dashboard hint the card verdicts alone would rank "
        "differently, which is what this alignment is for")


def test_the_block_is_written_by_python_when_the_model_is_off():
    from llm.fallback import conversational_fallback

    fb = conversational_fallback(_report_facts())
    assert fb["mind_now"], "the free trust block must not go blank"
    assert len(fb["why_now"]) > 40
    assert all("may" in line or "if" in line.lower() for line in fb["mind_now"])


def test_the_deterministic_block_passes_its_own_gates():
    """Fallback prose is what most readers see; it has to clear QA too."""
    from llm.fallback import conversational_fallback
    from llm.rules import check_prose
    from llm.validate import validate_mind_now_line

    facts = _report_facts()
    fb = conversational_fallback(facts)
    for line in fb["mind_now"]:
        assert check_prose(line, facts) == [], line
        assert validate_mind_now_line(line, facts) == [], line
    assert check_prose(fb["why_now"], facts) == []
