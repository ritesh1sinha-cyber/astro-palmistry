"""Chat answers may only use placements, gems and years the tools computed."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from llm.grounding import (  # noqa: E402
    deterministic_from_ledger,
    enforce_grounding,
    extract_ledger,
)


def _results() -> dict:
    return {
        "life_area_confluence": {
            "lagna": "Gemini",
            "lagna_lord": "Mercury",
            "primary_house": 4,
            "primary_house_sign": "Virgo",
            "primary_house_lord": "Mercury",
            "primary_lord_placement": "House 10 in Pisces (12.00°)",
            "classical_verdict": "Your chart shows mixed support for property.",
            "breakthrough_period": "March 29, 2029 to August 25, 2029",
        },
        "gemstone_audit": {
            "lagna": "Gemini",
            "lagna_lord": "Mercury",
            "audit": {
                "Mercury": {
                    "gem": "Emerald (Panna)", "status": "RECOMMENDED",
                    "house": 10, "owned_houses": [1, 4],
                },
                "Jupiter": {
                    "gem": "Yellow Sapphire (Pukhraj)", "status": "AVOID",
                    "house": 8,
                },
                "Venus": {
                    "gem": "Diamond / White Zircon (Heera)",
                    "status": "RECOMMENDED", "house": 10,
                },
                "Saturn": {
                    "gem": "Blue Sapphire (Neelam)", "status": "MANTRA_ONLY",
                    "house": 6,
                },
            },
        },
        "lal_kitab": {
            "findings": [{
                "title": "Moon in House 4",
                "summary": "Offer milk to shivalinga.",
            }],
        },
        "mind_and_transits": {
            "findings": [{
                "title": "Ketu",
                "summary": "Resolving ancestral commitments.",
            }],
        },
    }


def test_ledger_places_jupiter_in_8_capricorn():
    led = extract_ledger(_results())
    assert led.natal["Jupiter"].house == 8
    assert led.natal["Jupiter"].sign == "Capricorn"
    assert led.natal["Mercury"].house == 10
    assert led.natal["Mercury"].sign == "Pisces"
    assert led.house_signs[4] == "Virgo"
    assert led.this_year_supported is False
    assert "2029" in led.years


def test_rejects_moved_jupiter_and_this_year_overclaim():
    led = extract_ledger(_results())
    bad = (
        "Your 4th house is in Virgo. Jupiter in Cancer (2nd house) and "
        "Saturn in Pisces (10th house) help. There is a possibility of "
        "buying a house this year, especially within the specified window."
    )
    problems = enforce_grounding(bad, led, "can I buy a house this year")
    blob = " ".join(problems)
    assert "Jupiter" in blob and "Cancer" in blob
    assert "this year" in blob


def test_accepts_true_placements_and_the_2029_window():
    led = extract_ledger(_results())
    good = (
        "Your 4th house is in Virgo, and Mercury, who rules it, sits in "
        "Pisces in the 10th house. Venus is also in Pisces in the 10th. "
        "The strongest window already named is March 29, 2029 to "
        "August 25, 2029 — not this year. Do not wear yellow sapphire; "
        "your chart marks it avoid. Emerald is the stone it marks safe."
    )
    assert enforce_grounding(good, led, "can I buy a house this year") == []


def test_rejects_avoid_gem_offered_as_mercury_alternative():
    led = extract_ledger(_results())
    bad = (
        "Wear an emerald on your little finger. If you have doubts, "
        "consider a mantra-only gemstone for Mercury, such as a "
        "yellow sapphire on your index finger."
    )
    problems = enforce_grounding(bad, led, "shud i wear emrald")
    assert any("Yellow Sapphire" in p or "Pukhraj" in p or "AVOID" in p
               for p in problems)


def test_accepts_recommended_emerald():
    led = extract_ledger(_results())
    good = (
        "Your chart marks emerald safe to wear for Mercury, who sits in "
        "Pisces in the 10th house. Wear it only as the evidence allows."
    )
    assert enforce_grounding(good, led, "shud i wear emrald") == []


def test_rejects_scaffolding_headings():
    led = extract_ledger(_results())
    bad = (
        "Your chart is mixed.\n\n### Key Points:\n"
        "Mercury sits in Pisces in the 10th house."
    )
    assert any("heading" in p for p in enforce_grounding(bad, led, "property"))


def test_deterministic_stays_inside_the_ledger():
    led = extract_ledger(_results())
    text = deterministic_from_ledger(led, "can I buy a house this year")
    assert "2029" in text
    assert "this year" in text.lower()
    assert "Lal Kitab" in text
    assert "Chandra Naadi" in text
    assert "the native" not in text.lower()
    assert enforce_grounding(text, led, "can I buy a house this year") == []


def test_deterministic_gem_question_does_not_open_on_property():
    led = extract_ledger(_results())
    text = deterministic_from_ledger(led, "shud i wear emrald")
    assert "emerald" in text.lower()
    assert "pukhraj" in text.lower() or "yellow sapphire" in text.lower()
    assert "property" not in text.lower()
    assert enforce_grounding(text, led, "shud i wear emrald") == []


def test_rejects_false_extra_lordship():
    led = extract_ledger(_results())
    bad = (
        "Emerald is safe. Mercury rules the 1st house (trine) and the "
        "10th house. Wear it as the evidence allows."
    )
    problems = enforce_grounding(bad, led, "shud i wear emrald")
    assert any("does not rule house 10" in p for p in problems)


def test_lordship_is_not_treated_as_a_placement():
    led = extract_ledger(_results())
    good = (
        "Mercury rules the 4th house and sits in Pisces in the 10th house. "
        "Wait for March 29, 2029 to August 25, 2029 rather than this year."
    )
    assert enforce_grounding(good, led, "can I buy a house this year") == []
