"""The personal-life consolidation must keep the reading and drop the jargon.

The source engines write a human observation and the chart reasoning behind it
in the same paragraph. Dropping whole paragraphs loses the observation; keeping
whole paragraphs leaks planet names, book fragments and past-tense claims about
a life history nobody told us.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))


def test_the_human_sentence_survives_its_chart_aside():
    from llm.personal_life import _safe_sentences

    para = (
        "Your mother is practical, detail-conscious, and emotionally grounding - "
        "care shown through service, order, and quiet competence rather than "
        "dramatic display. Moon stands relatively alone: home-centred, "
        "methodical nurturing is the dominant tone. (Moon in Virgo; "
        "2nd-from-Moon Libra.)"
    )
    kept = _safe_sentences(para)
    assert len(kept) == 1
    assert kept[0].startswith("Your mother is practical")
    assert "Moon" not in kept[0] and "(" not in kept[0]


def test_a_trait_must_be_about_them_and_in_the_present():
    from llm.personal_life import _safe_sentences

    para = (
        "Channel the fire into clean ambition, not reactive fights. "
        "These years were restless and competitive; proving yourself mattered "
        "more than comfort. "
        "You tend to act quickly when you see an opening, sometimes before the "
        "people around you are ready."
    )
    kept = _safe_sentences(para, trait=True)
    assert kept == [
        "You tend to act quickly when you see an opening, sometimes before the "
        "people around you are ready."
    ]


def test_book_list_rows_and_fragments_are_not_sentences():
    from llm.personal_life import _safe_sentences

    assert _safe_sentences("Fields of Study: Teaching, Religious Studies.") == []
    assert _safe_sentences("Particularly in challenging situations.") == []


def test_a_family_line_lands_under_the_relation_it_talks_about():
    """Routing by the source's own topic put the mother under the father.

    The engines answer about parents as a pair, so the only reliable subject is
    the one inside the sentence.
    """
    from llm.personal_life import _route_family

    routed = _route_family(
        "Your father reads as principled, institution-facing and duty-heavy. "
        "The mother is authoritative and quietly rules the family. "
        "Achieves gradual growth, with occasional fits of anger."
    )
    assert len(routed["father"]) == 1 and "father" in routed["father"][0]
    assert len(routed["mother"]) == 1 and "mother" in routed["mother"][0]
    # A line that could be about anyone is worse than no line at all.
    assert routed["siblings"] == []


def test_family_notes_are_paid_depth():
    from llm.facts import project_for_access
    from llm.schemas import FamilyNoteFact, ReportFacts

    facts = ReportFacts(access="paid", family_notes=[FamilyNoteFact(
        relation="mother", label="Mother", tags=["practical_support"],
        notes=["Your mother is practical and emotionally grounding."],
        method_count=2,
    )])
    assert project_for_access(facts, "paid").family_notes
    assert project_for_access(facts, "free").family_notes == []


def test_family_tags_stay_inside_the_closed_vocabulary():
    from llm.personal_life import _FAMILY_TAGS, _tags_for

    known = {tag for tag, _ in _FAMILY_TAGS}
    tags = _tags_for("Your father respected rules and carried heavy duty at home.")
    assert tags and set(tags) <= known


def test_the_household_is_kept_when_no_relative_was_named():
    from llm.personal_life import _route_family

    routed = _route_family(
        "The household you grew up in ran on routine and quiet obligation."
    )
    assert len(routed["home"]) == 1
    assert routed["father"] == [] and routed["mother"] == []


def test_a_line_about_the_mother_at_home_belongs_to_the_mother_alone():
    """One sentence under two headings is padding, and the reader sees it."""
    from llm.personal_life import _route_family

    routed = _route_family(
        "Your mother held the home together through service and quiet order."
    )
    assert len(routed["mother"]) == 1
    assert routed["home"] == []


# --- the background block on the page -------------------------------------

def _facts_with_family(**over):
    from llm.schemas import FamilyNoteFact, ReportFacts

    return ReportFacts(
        access="paid",
        first_name="Meera",
        family_notes=[
            FamilyNoteFact(
                relation="father", label="Father",
                tags=["authority_and_discipline"],
                notes=["Your father reads as principled, institution-facing "
                       "and duty-heavy."],
                method_count=1,
            ),
            FamilyNoteFact(
                relation="mother", label="Mother", tags=["practical_support"],
                notes=["Your mother is practical, detail-conscious and "
                       "emotionally grounding."],
                method_count=2,
            ),
        ],
        **over,
    )


def test_a_background_line_must_name_a_relative_the_methods_described():
    from llm.validate import validate_family_line

    facts = _facts_with_family()
    assert validate_family_line(
        "Your mother is practical and grounding, and that steadiness is "
        "where your own order comes from.", facts) == []
    assert "family_note_relation_not_in_facts" in validate_family_line(
        "Your brothers and sisters shaped how you handle conflict.", facts)


def test_one_method_may_lean_but_may_not_declare():
    from llm.validate import validate_family_line

    facts = _facts_with_family()
    assert validate_family_line(
        "Your father comes across as principled and duty-heavy, the kind who "
        "put the institution first.", facts) == []
    assert "family_note_single_method_stated_flatly" in validate_family_line(
        "Your father was principled and duty-heavy above everything else.",
        facts)


def test_the_background_block_never_predicts_anything():
    from llm.validate import validate_family_line

    facts = _facts_with_family()
    assert "family_note_predicts" in validate_family_line(
        "Your mother is practical and grounding, and her health will need "
        "attention next year.", facts)


def test_the_background_block_cannot_borrow_another_relatives_detail():
    from llm.validate import validate_family_line

    facts = _facts_with_family()
    assert "family_note_detail_not_in_facts" in validate_family_line(
        "Your mother travelled constantly and left the raising to others.",
        facts)


def test_python_writes_the_block_when_the_model_is_off():
    from llm.fallback import conversational_fallback
    from llm.validate import validate_family_line

    facts = _facts_with_family()
    lines = conversational_fallback(facts).get("family_note") or []
    assert len(lines) == 2
    # The deterministic prose has to clear the gate it is the fallback for.
    for line in lines:
        assert validate_family_line(line, facts) == []


def test_free_never_shows_the_background_block():
    from llm.fallback import conversational_fallback
    from llm.facts import project_for_access

    free = project_for_access(_facts_with_family(), "free")
    assert conversational_fallback(free).get("family_note") == []
