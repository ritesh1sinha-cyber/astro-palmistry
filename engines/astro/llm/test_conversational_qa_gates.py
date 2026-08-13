"""The QA gates must reject invention without rejecting ordinary language.

Both failures below shipped silently: the palm gate threw away every aspect
that named a line, and the month gate threw away timing that was spelled out
from an abbreviation already present in the facts. In each case the reader
got deterministic template text and the run still looked healthy.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))


def _palm_facts(**kw):
    from llm.schemas import PalmAspectFacts, PalmFacts

    base = dict(
        photo_grade="fair",
        special_marks_allowed=False,
        aspects=[PalmAspectFacts(aspect="career", semantic_summary="Work builds slowly.")],
    )
    base.update(kw)
    return PalmFacts(**base)


def test_palm_line_names_are_ordinary_language():
    from llm.rules import check_prose

    facts = _palm_facts()
    for text in (
        "Your life line suggests steady vitality through your thirties.",
        "Your head line and heart line agree on this theme.",
        "Your fate line reads clearly, so work tends to find a settled direction.",
    ):
        assert check_prose(text, facts) == [], text


def test_palm_gate_still_blocks_jargon_marks_and_overclaim():
    from llm.rules import check_prose

    facts = _palm_facts()
    assert check_prose("The mount of Mercury is prominent.", facts)
    assert check_prose("A star mark suggests recognition.", facts)
    assert check_prose("Your hands promise leadership and fame.", facts)
    assert check_prose("The classical text reads this as a strong sign.", facts)


def test_palm_marks_allowed_when_photo_quality_supports_them():
    from llm.rules import check_prose

    facts = _palm_facts(photo_grade="good", special_marks_allowed=True)
    assert check_prose("A star on the hand adds emphasis here.", facts) == []


def test_populated_aspect_prose_is_not_scored_as_empty():
    """A filled aspect must never be rejected as ``empty_prose``.

    The palm humanizer used to hand the validator an ad-hoc wrapper object
    that had no ``model_dump``, so the text walker saw nothing and every
    aspect was rejected sight-unseen.
    """
    from llm.schemas import PalmAspectProse
    from llm.validate import validate_palm_prose

    prose = PalmAspectProse(
        aspect="career",
        headline="Your work tends to reward staying put long enough to get good.",
        why="Your fate line reads steady rather than sudden.",
        points=["experience has become an advantage over time"],
    )
    assert "empty_prose" not in validate_palm_prose(prose, _palm_facts())


def test_prompt_version_tracks_the_prompt_text():
    """Editing a prompt must invalidate cached prose for that tab.

    The version used to be a hand-maintained string, so a prompt change with
    no bump kept serving the previous wording until the cache expired.
    """
    from llm import rules

    before = rules.prompt_version("palm")
    original = rules._prompt_extra
    rules._prompt_extra = lambda kind: original(kind) + " Extra instruction."
    try:
        after = rules.prompt_version("palm")
    finally:
        rules._prompt_extra = original

    assert before != after
    assert before.startswith("PALM_CONVERSATIONAL_PROMPT_V1-")
    assert rules.prompt_version("palm") == before


def _career_facts():
    from llm.schemas import CardFacts, ReportFacts, WindowFact

    return ReportFacts(
        access="paid",
        cards=[CardFacts(
            area="career",
            label="Work & Career",
            status="mixed",
            window=WindowFact(label="May 2024 - Oct 2026"),
        )],
    )


def test_month_spelled_out_from_an_abbreviation_in_facts_is_allowed():
    from llm.rules import allowed_months_from_facts, check_prose

    facts = _career_facts()
    assert {"may", "october"} <= allowed_months_from_facts(facts)
    assert check_prose("The stronger stretch runs to October 2026.", facts) == []


def test_month_absent_from_facts_is_still_rejected():
    from llm.rules import check_prose

    fails = check_prose("A clearer window opens in March 2029.", _career_facts())
    assert "unexpected_month:march" in fails


def test_evidence_dedupe_drops_filler_and_contradictory_repeats():
    from llm.facts import _dedupe_evidence
    from llm.schemas import EvidenceFact

    items = [
        EvidenceFact(family="other", polarity="support",
                     text="Greater professional responsibility and ownership."),
        EvidenceFact(family="other", polarity="caution",
                     text="Greater professional responsibility and ownership."),
        EvidenceFact(family="other", polarity="caution",
                     text="The chart evidence is summarized in the life-area reading above."),
        EvidenceFact(family="other", polarity="support",
                     text="Case-based confirmation — supports this reading."),
        EvidenceFact(family="other", polarity="support",
                     text="Money earned through work, skills or practical activity."),
    ]
    kept = [e.text for e in _dedupe_evidence(items)]
    assert kept == [
        "Greater professional responsibility and ownership.",
        "Money earned through work, skills or practical activity.",
    ]
