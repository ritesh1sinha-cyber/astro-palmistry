"""The palm trust block must recognise the person without claiming their life.

A hand can show a tendency or an unmet need. It cannot know that someone has a
problem, and palmistry here has no clock, so it cannot know when either. These
tests hold both lines, plus the boundary that keeps the palm engine's own
vocabulary — planet-named mounts, detector ids, fine marks a photograph cannot
support — out of what the model is given.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))


def _aspects():
    from llm.schemas import PalmAspectFacts

    return [
        PalmAspectFacts(
            aspect="career", title="Career & Direction", direction="support",
            strength="strong", confidence="high", score=2.0,
            semantic_summary="Your work rewards staying with something long enough to get good at it.",
        ),
        PalmAspectFacts(
            aspect="health", title="Health & Vitality", direction="mixed",
            strength="tentative", confidence="low", score=0.0,
            semantic_summary="Your energy responds to routine more than to effort.",
        ),
        PalmAspectFacts(
            aspect="love", title="Relationships & Emotions", direction="mixed",
            strength="moderate", confidence="moderate", score=1.0,
            semantic_summary="You give warmth selectively rather than freely.",
        ),
    ]


def _confluence():
    """Shape the palm confluence engine actually produces."""
    return {
        "dominant_hand": "right",
        "lines": [
            {"key": "life", "title": "Life line", "agreement": "reinforced",
             "statement": "Your vitality is consistent across both hands."},
            {"key": "head", "title": "Head line", "agreement": "reinforced",
             "statement": "Your thinking is consistent across both hands."},
            {"key": "fate", "title": "Fate line", "agreement": "developed",
             "statement": "Your direction reads stronger on your Right hand."},
            {"key": "heart", "title": "Heart line", "agreement": "latent",
             "statement": "The underlying hand suggests a strong need for warmth."},
        ],
        "mounts": [
            {"mount": "jupiter",
             "statement": "You seem to have grown into a stronger need to lead."},
            {"mount": "venus",
             "statement": "The underlying hand suggests a strong need for warmth "
                          "and close family connection."},
        ],
    }


def _palm_facts(access: str = "free", *, photo_grade: str = "fair"):
    from llm.palm_state import build_hand_contrast, build_palm_state
    from llm.schemas import PalmFacts

    aspects = _aspects()
    contrast = build_hand_contrast(_confluence(), dominant_hand="right")
    return PalmFacts(
        first_name="Meera",
        access=access,                                       # type: ignore[arg-type]
        photo_grade=photo_grade,
        special_marks_allowed=photo_grade == "good",
        aspects=aspects,
        demanding_aspect="health",
        demanding_aspect_label="Health & Vitality",
        hand_contrast=contrast,
        palm_state=build_palm_state(
            aspects, contrast=contrast, demanding_aspect="health",
            photo_grade=photo_grade),
    )


# --- Module 1: the two hands -------------------------------------------------
def test_the_dominant_hand_is_read_as_the_present_expression():
    from llm.palm_state import build_hand_contrast

    contrast = build_hand_contrast(_confluence(), dominant_hand="right")
    assert contrast is not None
    assert contrast.dominant_hand == "right"
    assert any("direction" in t for t in contrast.developed), (
        "a line stronger on the lived hand is something they grew into")
    assert any("emotional" in t for t in contrast.latent), (
        "a line stronger on the other hand is a need with less room")


def test_agreement_across_both_hands_reads_as_long_standing():
    from llm.palm_state import build_hand_contrast

    both_agree = {"dominant_hand": "right", "lines": [
        {"key": "life", "agreement": "reinforced"},
        {"key": "head", "agreement": "reinforced"},
    ]}
    contrast = build_hand_contrast(both_agree, dominant_hand="right")
    assert contrast is not None
    assert contrast.agreement == "high"
    assert contrast.steady and not contrast.developed and not contrast.latent


def test_one_photographed_hand_produces_no_contrast_at_all():
    """No comparison is a fact about the photographs, not about the person."""
    from llm.palm_state import build_hand_contrast

    assert build_hand_contrast(None) is None
    assert build_hand_contrast({}) is None


def test_the_contrast_never_carries_a_planet_named_mount():
    from llm.facts import public_fact_payload

    payload = json.dumps(public_fact_payload(_palm_facts())).lower()
    for planet in ("jupiter", "saturn", "venus", "mercury", "apollo", "moon", "mars"):
        assert planet not in payload, f"{planet} is astrology jargon in a palm reading"


# --- Module 2: the current state --------------------------------------------
def test_the_area_asking_for_care_becomes_a_mind_topic():
    state = _palm_facts().palm_state
    assert state is not None
    topics = {t.area: t for t in state.mind_now}
    assert "health" in topics
    assert topics["health"].experience, "the topic must carry words to speak with"


def test_the_demanding_area_and_the_mind_block_name_the_same_life():
    """The page must not name two different hard areas a few paragraphs apart."""
    from llm.palm_state import build_palm_state

    aspects = _aspects()
    state = build_palm_state(aspects, demanding_aspect="love")
    assert state.mind_now[0].area == "love"


def test_a_well_supported_area_still_gets_a_place():
    """A block that only names problems reads as a warning, not a reading."""
    state = _palm_facts().palm_state
    assert state is not None
    assert "career" in {t.area for t in state.mind_now}


def test_every_mind_topic_stays_a_possibility():
    state = _palm_facts().palm_state
    assert state is not None
    assert state.mind_now
    for topic in state.mind_now:
        assert topic.is_fact is False


def test_the_palm_state_block_invents_no_age_or_date():
    """Palmistry here has no clock; ages live only in future_windows.

    Any digit in this block would also ground that digit for the whole page,
    letting prose print numbers the palm age gate exists to catch.
    """
    from llm.facts import public_fact_payload

    block = public_fact_payload(_palm_facts())["palm_state"]
    assert not any(ch.isdigit() for ch in json.dumps(block))


def test_a_poor_photograph_says_so_in_the_block():
    facts = _palm_facts(photo_grade="poor")
    assert facts.palm_state is not None
    assert facts.palm_state.confidence_note
    assert facts.palm_state.uncertainty == "high"


def test_the_blocks_survive_the_public_allowlist():
    """A field missing from the allowlist is dropped in silence."""
    from llm.facts import public_fact_payload

    payload = public_fact_payload(_palm_facts())
    assert payload["palm_state"]["mind_now"][0]["label"]
    assert payload["palm_state"]["chapter_tone"]
    assert payload["hand_contrast"]["steady"]


def test_free_keeps_the_trust_blocks_without_the_full_breakdown():
    from llm.facts import project_for_access

    free = project_for_access(_palm_facts(access="paid"), "free")
    assert free.palm_state is not None and free.palm_state.mind_now
    assert free.hand_contrast is not None and free.hand_contrast.steady
    assert len(free.palm_state.domains) <= 3
    assert free.future_windows == [], "age windows stay paid"


# --- The gates ---------------------------------------------------------------
def test_a_mind_line_must_name_a_theme_the_hands_showed():
    from llm.validate import validate_mind_now_line

    facts = _palm_facts()
    good = "Your energy may be asking for more routine than it used to."
    invented = "A court case may be weighing on you at the moment."
    assert validate_mind_now_line(good, facts) == []
    assert "mind_now_topic_not_in_facts" in validate_mind_now_line(invented, facts)


def test_a_mind_line_must_stay_hedged():
    from llm.validate import validate_mind_now_line

    flat = "Your health is the thing weighing on you right now."
    assert "mind_now_stated_as_fact" in validate_mind_now_line(flat, _palm_facts())


def test_three_lines_about_one_theme_are_recognised_as_one_topic():
    """Handed three experience phrases, a model spends all three on the first.

    That silently drops the area that is going well, which is the half of the
    block that stops it reading as a list of warnings.
    """
    from llm.validate import mind_now_topic_index

    facts = _palm_facts()
    areas = [t.area for t in facts.palm_state.mind_now]
    assert len(set(areas)) > 1, "fixture must offer more than one topic"
    health = areas.index("health")
    for line in (
        "You may be carrying more attention to routine.",
        "Your energy may run out sooner than it used to.",
        "You may be feeling the need for rest and consistency.",
    ):
        assert mind_now_topic_index(line, facts) == health
    other = "Career & Destiny: forward movement may be part of your days now."
    assert mind_now_topic_index(other, facts) != health


def test_the_two_hand_story_cannot_claim_a_change_that_was_not_found():
    from llm.validate import validate_hand_contrast_note
    from llm.palm_state import build_hand_contrast
    from llm.schemas import PalmFacts

    same = build_hand_contrast(
        {"dominant_hand": "right", "lines": [
            {"key": "life", "agreement": "reinforced"},
            {"key": "head", "agreement": "reinforced"},
        ]}, dominant_hand="right")
    facts = PalmFacts(access="free", aspects=_aspects(), hand_contrast=same)
    claim = ("Your right hand shows how much you have grown into your work "
             "since you started out.")
    assert "hand_contrast_change_not_in_facts" in validate_hand_contrast_note(
        claim, facts)
    honest = ("Your energy and the way you think read much the same on both "
              "hands, so those parts of you look long-standing.")
    assert validate_hand_contrast_note(honest, facts) == []


def test_the_two_hand_story_cannot_say_they_agree_on_a_one_sided_trait():
    """The exact sentence the model wrote on a real reading.

    A trait that reads stronger on the underlying hand is a need with less
    room, so calling it shared reverses the finding — in the paragraph a
    reader is most likely to quote back.
    """
    from llm.validate import validate_hand_contrast_note

    facts = _palm_facts()
    assert facts.hand_contrast is not None
    assert "warmth and closeness" in facts.hand_contrast.latent_traits
    assert "hand_contrast_agreement_misstated" in validate_hand_contrast_note(
        "Both hands agree on the importance of ambition and warmth and "
        "closeness.", facts)
    assert validate_hand_contrast_note(
        "Your energy and vitality reads much the same on both hands.",
        facts) == []


def test_the_two_hand_story_cannot_hand_out_life_areas():
    """The comparison is made of line themes and traits, never of aspects."""
    from llm.validate import validate_hand_contrast_note

    assert "hand_contrast_uses_life_areas" in validate_hand_contrast_note(
        "Your right hand shows a clear path forward in character, love and "
        "career, while your left hand hints at a need for rest.", _palm_facts())


def test_a_palm_reading_cannot_reach_the_body():
    """A photograph of a hand cannot see a symptom."""
    from llm.rules import check_prose

    facts = _palm_facts()
    assert "palm_bodily_claim" in check_prose(
        "This stress could show up as changes in digestion.", facts)
    assert check_prose(
        "Your energy may run out sooner than it used to, so routine matters "
        "more than effort right now.", facts) == []


def test_the_care_note_is_not_the_first_mind_line_again():
    from llm.humanize import _merge_conversational_palm_facts

    facts = _palm_facts()
    line = ("Health & Vitality: more attention to routine and energy that runs "
            "out sooner than it used to may well be part of your days now.")
    merged = _merge_conversational_palm_facts(
        {
            "personality": "x" * 60,
            "current_phase": "y" * 60,
            "hardest_area_note": ("more attention to routine and energy that "
                                  "runs out sooner than it used to."),
            "mind_now": [line],
        },
        facts, access="free",
    )
    assert merged["hardest_area_note"] != (
        "more attention to routine and energy that runs out sooner than it used to.")
    assert "Health & Vitality" in merged["hardest_area_note"]


def _chat(answer: str, ids=("palm_state",)):
    from llm.schemas import ChatAnswer

    return ChatAnswer(answer=answer, out_of_scope=False, used_fact_ids=list(ids))


def test_a_follow_up_cannot_promise_an_outcome_at_an_age():
    """The bait question, and the answer this reading must never give.

    The line-timing engine says when a theme reads most strongly. Turning that
    into "you will be rich between 27 and 36" is a promise no photograph of a
    hand can support.
    """
    from llm.validate import validate_chat_answer

    facts = _palm_facts(access="paid")
    facts.future_windows = [{"age_window": [27, 36], "domain": "career_direction",
                             "confidence": "moderate"}]
    bad = _chat("Becoming rich is likely to occur between the ages of 27 and 36.")
    assert "chat_palm_age_outcome" in validate_chat_answer(bad, facts)
    fine = _chat("Your hands do not promise wealth at a particular age; this "
                 "theme simply reads more strongly around ages 27 to 36.")
    assert "chat_palm_age_outcome" not in validate_chat_answer(fine, facts)


def test_a_follow_up_cannot_swap_what_each_hand_showed():
    from llm.validate import validate_chat_answer

    facts = _palm_facts(access="paid")
    swapped = _chat(
        "Your right hand highlights warmth and closeness, while your left hand "
        "shows the ambition you have built up.")
    assert "hand_contrast_attribution_swapped" in validate_chat_answer(swapped, facts)
    right = _chat(
        "Your right hand shows the ambition you grew into, while your left hand "
        "carries more warmth and closeness than your routine gives room for.")
    assert "hand_contrast_attribution_swapped" not in validate_chat_answer(right, facts)


def test_a_one_word_area_answer_loses_to_the_deterministic_line():
    """"Positive." passes every gate and tells the reader nothing."""
    from llm.humanize import _merge_conversational_palm_facts

    facts = _palm_facts(access="paid")
    merged = _merge_conversational_palm_facts(
        {"personality": "x" * 60, "current_phase": "y" * 60,
         "areas": {"career": {"outlook": "Positive.", "timing": "Present.",
                              "manifestation": "Forward movement."}}},
        facts, access="paid",
    )
    career = merged["areas"]["career"]
    assert career["outlook"] != "Positive."
    assert "long enough to get good at it" in career["outlook"]
    assert career["timing"] == ""


def test_the_two_hand_story_cannot_be_written_without_a_comparison():
    from llm.validate import validate_hand_contrast_note
    from llm.schemas import PalmFacts

    facts = PalmFacts(access="free", aspects=_aspects())
    assert "hand_contrast_without_facts" in validate_hand_contrast_note(
        "Your left hand shows what you started with.", facts)
    assert validate_hand_contrast_note("", facts) == []


def test_palm_prose_cannot_assert_a_circumstance_it_cannot_know():
    from llm.rules import check_prose

    facts = _palm_facts()
    assert "asserted_circumstance" in check_prose(
        "You are dealing with a long-running dispute at work.", facts)
    assert check_prose(
        "Your energy may be asking for more routine than it used to.",
        facts) == []


def test_a_fair_photograph_keeps_fine_marks_out_of_the_block():
    """Marks a fair photograph cannot support must not become a mind topic."""
    from llm.rules import check_prose

    facts = _palm_facts(photo_grade="fair")
    assert "palm_mark_not_supported_by_quality" in check_prose(
        "A trident on your palm points to recognition ahead.", facts)


# --- The deterministic path --------------------------------------------------
def test_the_block_is_written_by_python_when_the_model_is_off():
    from llm.fallback import conversational_palm_fallback

    fb = conversational_palm_fallback(_palm_facts())
    assert fb["mind_now"], "the free trust block must not go blank"
    assert len(fb["why_now"]) > 40
    assert len(fb["hand_contrast_note"]) > 40
    assert all("may" in line or "if" in line.lower() for line in fb["mind_now"])


def test_the_deterministic_palm_block_passes_its_own_gates():
    """Fallback prose is what most readers see; it has to clear QA too."""
    from llm.fallback import conversational_palm_fallback
    from llm.rules import check_prose
    from llm.validate import (
        validate_hand_contrast_note,
        validate_mind_now_line,
        validate_why_now,
    )

    facts = _palm_facts()
    fb = conversational_palm_fallback(facts)
    for line in fb["mind_now"]:
        assert check_prose(line, facts) == [], line
        assert validate_mind_now_line(line, facts) == [], line
    assert check_prose(fb["why_now"], facts) == []
    assert validate_why_now(fb["why_now"]) == []
    assert check_prose(fb["hand_contrast_note"], facts) == []
    assert validate_hand_contrast_note(fb["hand_contrast_note"], facts) == []


def test_the_free_page_renders_both_new_sections():
    from llm.fallback import conversational_palm_fallback

    sys.path[:0] = [str(HERE.parent.parent.parent)]
    from core import palm_conversational as PC

    facts = _palm_facts()
    html = PC.render({"confluence": _confluence()}, name="Meera", paid=False,
                     prose=conversational_palm_fallback(facts))
    # The "on your mind" lines now sit inside the current-phase section rather
    # than under a heading of their own, but they keep the same guard: a hand
    # shows what is likely, never what is happening.
    assert "Where your hands place you now" in html
    assert "what you have made of it" in html
    assert "read from the palm, not known about your life" in html
