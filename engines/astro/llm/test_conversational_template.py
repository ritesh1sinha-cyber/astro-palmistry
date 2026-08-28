"""Tests for the compact conversational LLM-on template switch."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ENGINES = HERE.parents[1]
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))
if str(ENGINES) not in sys.path:
    sys.path.insert(0, str(ENGINES))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_conversational_fallback_has_required_free_fields():
    from llm.fallback import conversational_fallback
    from llm.schemas import CardFacts, RecentMonthFact, ReportFacts

    facts = ReportFacts(
        first_name="Meera",
        access="free",
        personality_traits=["You tend to act quickly when you see an opportunity."],
        phase_tone="mixed",
        phase_end="2026-10",
        recent_months=[RecentMonthFact(
            start="2026-02", end="2026-08", area="home",
            label="Home & Family", direction_label="Mixed period",
            headline="Home is mostly workable.",
        )],
        hardest_area_labels=["Work & Career"],
        cards=[CardFacts(area="career", label="Work & Career")],
    )
    out = conversational_fallback(facts)
    assert out["conversational"] is True
    assert "act quickly" in out["personality"]
    assert "two ways" in out["current_phase"].lower() or "patience" in out["current_phase"].lower()
    # The free overlay names the stretch, never when it ends — that date is
    # the paid answer.
    assert "october 2026" not in out["current_phase"].lower()
    assert out["recent_months"]
    assert "Work & Career" in out["hardest_area_note"]
    assert out["areas"] == {}  # free has no area detail


def test_conversational_fallback_paid_includes_areas():
    from llm.fallback import conversational_fallback
    from llm.schemas import CardFacts, ReportFacts, WindowFact

    facts = ReportFacts(
        first_name="Meera",
        access="paid",
        personality_traits=["Recognition matters to you."],
        phase_tone="supportive",
        cards=[CardFacts(
            area="career",
            label="Work & Career",
            outlook_line="Progress is mixed but responsibility is growing.",
            manifestations=["greater responsibility before reward"],
            remedy_text="Ask one senior person to speak for you.",
            timing_windows=[WindowFact(start="2027-11", end="2028-02", label="career")],
        )],
    )
    out = conversational_fallback(facts)
    career = out["areas"]["career"]
    assert "work & career" in career["outlook"].lower()
    assert "November 2027" in career["timing"]
    assert "February 2028" in career["timing"]
    blob = (career["outlook"] + " " + career["manifestation"]).lower()
    assert "greater responsibility" in blob
    assert career["remedy"] == "Ask one senior person to speak for you."


def test_non_english_prose_is_rejected():
    """A multilingual model must not ship a page the reader cannot read."""
    from llm.rules import check_prose
    from llm.schemas import CardFacts, ReportFacts

    facts = ReportFacts(access="paid", cards=[CardFacts(area="career")])
    assert "non_english_text" in check_prose(
        "工作与职业的内在支持和当前时期都不强烈。", facts)
    assert check_prose(
        "Your work and career reads as mixed, so steady effort matters.", facts) == []


def test_palm_area_text_is_trimmed_on_a_sentence_boundary():
    from llm.fallback import clean_palm_summary, clip_sentences

    assert clean_palm_summary(
        "Together, these signs point to two related parts of your temperament: "
        "Your energy is tied to conversation."
    ) == "Your energy is tied to conversation."
    clipped = clip_sentences("One short line. " + "A" * 400, 100)
    assert clipped == "One short line."
    long_single = "word " * 80
    assert len(clip_sentences(long_single, 220)) <= 220


def test_challenge_area_cannot_be_sold_as_an_opportunity():
    from llm.schemas import CardFacts
    from llm.validate import validate_conversational_area

    card = CardFacts(area="health", label="Health & Energy", kind="challenge")
    assert validate_conversational_area(
        "outlook",
        "This is a genuine opportunity window and the period is actively supporting it.",
        card,
    ) == ["challenge_framed_as_opportunity"]
    assert validate_conversational_area(
        "outlook",
        "This part of the reading asks for steady care rather than a push.",
        card,
    ) == []


def test_window_label_is_readable():
    from llm.fallback import _readable_window_label

    assert _readable_window_label("May 2024 → Oct 2026") == "May 2024 to October 2026"


def test_every_demanding_area_carries_a_remedy():
    """A difficulty is never presented without the step that helps."""
    from llm.fallback import conversational_fallback
    from llm.schemas import CardFacts, ReportFacts

    facts = ReportFacts(
        access="paid",
        personality_traits=["You move early on opportunities."],
        cards=[
            CardFacts(area="career", label="Work & Career", status="mixed",
                      direction="mixed"),
            CardFacts(area="health", label="Health & Energy", kind="challenge",
                      status="indicated", direction="caution"),
            CardFacts(area="money", label="Money", status="weak",
                      direction="down"),
        ],
    )
    out = conversational_fallback(facts)
    for area in ("career", "health", "money"):
        assert out["areas"][area]["outlook"]
        assert out["areas"][area]["remedy"], area


def test_free_projection_strips_area_remedies_not_personality():
    from llm.facts import project_for_access
    from llm.schemas import CardFacts, ReportFacts

    paid = ReportFacts(
        access="paid",
        personality_traits=["You tend to act quickly."],
        phase_tone="mixed",
        phase_end="2026-10",
        cards=[CardFacts(
            area="career",
            remedy_text="Ask a senior person.",
            approved_remedies=["Ask a senior person."],
            remedy_eligible=True,
        )],
    )
    free = project_for_access(paid, "free")
    assert free.personality_traits
    assert free.phase_tone == "mixed"
    assert free.cards[0].remedy_text == ""
    assert free.cards[0].approved_remedies == []


def test_deterministic_prose_still_earns_the_conversational_page():
    """The layout must not depend on the model answering.

    Nothing accepted used to mean the classic cards page, so a reading changed
    shape the moment the model was off or failing. A complete overlay is now
    enough, whoever wrote the sentences.
    """
    from report_render import _use_conversational

    prose = {"conversational": True, "personality": "You tend to act quickly."}
    assert _use_conversational(prose, llm_enabled=False, accepted=0) is True
    assert _use_conversational(prose, llm_enabled=True, accepted=4) is True


def test_an_incomplete_overlay_falls_back_to_the_classic_page():
    """Without prose to carry it, the conversational page has nothing to say."""
    from report_render import _use_conversational

    assert _use_conversational({}, llm_enabled=True, accepted=4) is False
    assert _use_conversational(
        {"conversational": True, "personality": "  "},
        llm_enabled=True, accepted=4) is False


def test_the_flag_restores_the_accepted_only_rule():
    """CONVERSATIONAL_WHEN_LLM_OFF=0 is the one-variable rollback."""
    from core.config import S
    from report_render import _use_conversational

    prose = {"conversational": True, "personality": "You tend to act quickly."}
    before = S.conversational_when_llm_off
    S.conversational_when_llm_off = False
    try:
        assert _use_conversational(prose, llm_enabled=False, accepted=0) is False
        assert _use_conversational(prose, llm_enabled=True, accepted=0) is False
        assert _use_conversational(prose, llm_enabled=True, accepted=2) is True
    finally:
        S.conversational_when_llm_off = before


def test_conversational_render_has_unlock_on_free():
    from llm.fallback import conversational_fallback
    from llm.schemas import ReportFacts
    import report_conversational as RConv

    facts = ReportFacts(
        first_name="Meera",
        access="free",
        personality_traits=["You tend to act quickly when you see an opportunity."],
        phase_tone="mixed",
    )
    prose = conversational_fallback(facts)
    html = RConv.render(
        {"lagna": {"sign": "Aries"}, "planets": {"Moon": {"sign": "Leo"}}},
        name="Meera", paid=False, price=298, cards=[], prose=prose,
        footer_unlock=True,
    )
    assert 'data-unlock="1"' in html
    assert "YOUR CHART SIGNATURE" in html
    assert "WHO YOU ARE" in html
    assert "THE ROAD AHEAD" not in html  # no cards on this free render
    assert "1. CHART SIGNATURE" not in html
    assert "See the full reading, area by area" in html


def test_free_conversational_page_shows_what_it_is_holding_back():
    """The free view must name the locked depth and how to buy it.

    The classic page has always carried the blurred paid sections and the
    bundle offer. Readings only reached the conversational page when the model
    answered, so nobody noticed they were missing until that page became the
    default. A free reading that ends on a bare CTA is a worse offer.
    """
    from llm.fallback import conversational_fallback
    from llm.schemas import ReportFacts
    import report_conversational as RConv

    facts = ReportFacts(
        first_name="Meera",
        access="free",
        personality_traits=["You tend to act quickly when you see an opportunity."],
        phase_tone="mixed",
    )
    prose = conversational_fallback(facts)
    pc = {"lagna": {"sign": "Aries"}, "planets": {"Moon": {"sign": "Leo"}}}
    upsell = "<section id='marker-locked'>locked depth</section>"

    free = RConv.render(pc, name="Meera", paid=False, price=298, cards=[],
                        prose=prose, footer_unlock=True, upsell_html=upsell)
    assert "marker-locked" in free

    paid = RConv.render(pc, name="Meera", paid=True, price=298, cards=[],
                        prose=prose, footer_unlock=False, upsell_html=upsell)
    assert "marker-locked" not in paid, "a paying reader is not sold the report again"


def test_palm_render_carries_the_prose_inside_the_computed_spine():
    from llm.fallback import conversational_palm_fallback
    from llm.schemas import PalmAspectFacts, PalmFacts
    from core.palm_conversational import render as palm_render

    facts = PalmFacts(
        first_name="Meera",
        access="paid",
        age_years=30,
        personality_traits=["You think better by talking things through."],
        life_stage_note="Around age 31, your vitality enters a meaningful chapter.",
        demanding_aspect="health",
        demanding_aspect_label="Health & Vitality",
        aspects=[PalmAspectFacts(
            aspect="career",
            title="Career & Direction",
            semantic_summary="Experience has become an advantage over time.",
            recognize=["consistency has helped your professional position"],
            age_window=[27, 36],
            strength="moderate",
        )],
    )
    prose = conversational_palm_fallback(facts)
    raw = {
        "confluence": {
            "dominant_hand": "right",
            "life_aspects": [{
                "key": "career", "title": "Career & Direction",
                "strength": "moderate", "summary": "Experience helps.",
            }],
        },
        "right": {},
        "left": {},
    }
    html = palm_render(raw, name="Meera", age=30, paid=True, prose=prose)
    # The sections are computed from the measurements, and the prose lands
    # inside them: the personality paragraph opens the section that shows the
    # hand it was read from rather than standing under a heading of its own.
    assert "Your hands, and what I traced on them" in html
    assert "Where You Are Now, Meera" in html
    assert "Your Core Hand Archetype &amp; Temperament" in html
    assert "Innate Blueprint vs. Self-Made Evolution" in html
    assert "You think better by talking things through." in html
    assert "vitality enters a meaningful chapter" in html
