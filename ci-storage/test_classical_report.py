"""Classical Vedic Report — section order, classical grammar, and hard blocks.

The point of this product is that house/lord/planet/yoga grammar survives all
the way to the page. The shared sanitizer deletes exactly that grammar, so
these tests exist to catch a regression where the classical report is
accidentally routed back through the strict boundary, or where the relaxed
boundary drifts and starts letting through what it must still block.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))

MEERA = {
    "name": "Meera Nair", "dob": "1990-01-15", "tob": "12:00",
    "lat": 28.6139, "lon": 77.2090, "tz": 5.5, "place": "New Delhi", "gender": 1,
}

SECTION_ORDER = [
    "Client Details",
    "1. Personality Traits",
    "2. Family and Background",
    "3. Career and Professional Nature",
    "4. Relationship and Marriage Indications",
    "5. Health and Vitality",
    "6. Children — Health, Education and Path",
    "7. What You Are Going Through Currently",
    "8. Future Predictions",
    "9. Remedies and Guidance",
    "Summary",
]


def _body(html: str) -> str:
    """The report itself, without the shell's section-navigation rail.

    The rail repeats every heading, so an order check against the raw document
    would compare navigation links rather than sections.
    """
    marker = '<div class="wrap">'
    index = html.find(marker)
    return html[index:] if index >= 0 else html


def _text(html: str) -> str:
    import html as H
    stripped = re.sub(r"(?s)<(script|style|nav).*?</\1>", " ", html)
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", stripped)))


@pytest.fixture(scope="module")
def report() -> tuple[str, str, dict]:
    """Render once. The transit scan is the expensive part of this product."""
    try:
        from astro_precompute import resolve_precompute
        from classical_report import classical_report
        pc = resolve_precompute(
            MEERA["name"], MEERA["dob"], birth_time=MEERA["tob"],
            latitude=MEERA["lat"], longitude=MEERA["lon"], timezone=MEERA["tz"],
            place_name=MEERA["place"], gender=MEERA["gender"])
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"chart source unavailable: {exc}")
    return classical_report(
        pc, name=MEERA["name"], dob=MEERA["dob"], tob=MEERA["tob"],
        place=MEERA["place"], price=298)


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

def test_paid_report_has_every_section_in_order(report) -> None:
    _, paid, _ = report
    body = _body(paid)
    positions = [body.find(f">{title}<") for title in SECTION_ORDER]
    missing = [t for t, p in zip(SECTION_ORDER, positions) if p < 0]
    assert not missing, f"missing sections: {missing}"
    assert positions == sorted(positions), "sections are out of order"


def test_header_names_lagna_moon_nakshatra_and_current_dasha(report) -> None:
    _, paid, meta = report
    text = _text(paid)
    assert "Ascendant / Lagna" in text and meta["lagna"] in text
    assert "Moon Sign" in text and meta["moonSign"] in text
    assert "Nakshatra" in text and meta["nakshatra"] in text
    assert f"{meta['mahadasha']} Mahadasha" in text


def test_free_is_a_strict_subset_and_offers_the_rest(report) -> None:
    free, paid, _ = report
    assert free != paid
    assert len(free) < len(paid)
    free_body = _body(free)
    assert "1. Personality Traits" in free_body
    assert "8. Future Predictions" not in free_body
    assert "The rest of the reading" in free_body


def test_future_section_uses_the_three_horizons(report) -> None:
    _, paid, meta = report
    text = _text(paid)
    for label in ("Next 6 Months", "Next 12 Months", "Next 2-3 Years"):
        assert label in text, f"missing horizon {label}"
    assert meta["horizons"] == ["next_6_months", "next_12_months", "next_2_3_years"]


def test_remedies_name_planets_with_a_stated_reason(report) -> None:
    _, paid, meta = report
    text = _text(paid)
    assert f"For {meta['mahadasha']}" in text
    assert "Why this planet:" in text
    assert "Mantra" in text


# ---------------------------------------------------------------------------
# The classical grammar must survive
# ---------------------------------------------------------------------------

def test_house_lord_grammar_reaches_the_page(report) -> None:
    _, paid, _ = report
    text = _text(paid)
    assert re.search(r"\b\d+(?:st|nd|rd|th) lord [A-Z][a-z]+", text), \
        "no house-lord placement survived the boundary"


def test_planet_placements_are_named(report) -> None:
    _, paid, _ = report
    text = _text(paid)
    assert re.search(
        r"\b(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu) "
        r"(?:sits|occupies) in your|"
        r"\b(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu) sits in your",
        text,
    ), "no planet placement survived the boundary"


def test_dasha_vocabulary_is_not_stripped(report) -> None:
    _, paid, _ = report
    text = _text(paid).lower()
    assert "mahadasha" in text
    assert "antardasha" in text
    assert "nakshatra" in text


def test_health_section_names_body_areas_timing_and_a_jaap(report) -> None:
    _, paid, _ = report
    text = _text(paid)
    assert "5. Health and Vitality" in text
    assert "Maha Mrityunjaya" in text, "the prescribed jaap did not survive"
    assert re.search(r"6th house of daily health falls in [A-Z][a-z]+", text), \
        "the health section did not name the 6th house sign"
    assert re.search(r"(?:asks for care|keep in ordinary routine care)", text)


def test_children_section_covers_health_education_and_path(report) -> None:
    _, paid, _ = report
    text = _text(paid)
    assert "6. Children" in text
    for heading in ("Their health", "Their education", "Their path ahead"):
        assert heading in text, f"children section is missing {heading}"
    assert "Santan Gopal" in text
    assert re.search(r"5th house is the child's own ascendant", text)


def test_children_section_makes_no_promise_about_conception(report) -> None:
    _, paid, _ = report
    text = _text(paid).lower()
    for phrase in ("you will conceive", "you will get pregnant", "number of children",
                   "issueless", "barren"):
        assert phrase not in text, f"the children section promised or denied a birth: {phrase}"


def test_every_stone_gets_a_colour_coded_verdict(report) -> None:
    _, paid, _ = report
    lines = re.findall(r'<p class="cv-stone (yes|no)">(.*?)</p>', paid, re.S)
    assert lines, "no gemstone verdict reached the page"
    for state, body in lines:
        flag = "Wear" if state == "yes" else "Do not wear"
        assert f'<span class="cv-flag">{flag}</span>' in body

    text = _text(paid).lower()
    for hedge in ("have it checked", "before wearing", "consult an astrologer"):
        assert hedge not in text, f"the stone verdict was handed back to the client: {hedge}"


# ---------------------------------------------------------------------------
# What must still be blocked
# ---------------------------------------------------------------------------

BLOCKED = (
    "diabetes", "cancer", "tuberculosis", "paralysis", "leprosy",
    "death", "widow", "longevity", "maraka",
    "guaranteed", "certain to", "definitely",
    "evidence_trace", "traceback",
)


def test_no_blocked_wording_survives(report) -> None:
    free, paid, _ = report
    for document in (free, paid):
        text = _text(document).lower()
        found = [word for word in BLOCKED if word in text]
        assert not found, f"blocked wording reached the page: {found}"


def test_body_tendencies_are_still_allowed(report) -> None:
    _, paid, _ = report
    text = _text(paid).lower()
    assert any(word in text for word in ("sleep", "tiredness", "digestion", "anxiety")), \
        "the report cannot describe a period without body tendency language"


# ---------------------------------------------------------------------------
# The boundary profile itself, without a chart
# ---------------------------------------------------------------------------

def test_boundary_keeps_astrology_and_drops_the_offending_sentence() -> None:
    from qa_checks.classical_boundary import (
        classical_violations,
        finalize_classical_html,
    )

    assert classical_violations("Your 7th lord Venus is placed in the 8th house.") == []
    assert classical_violations("Gaja-Kesari Yoga gives wisdom and protection.") == []
    assert classical_violations("Saturn brings tiredness and disturbed sleep.") == []

    assert "named_disease" in classical_violations("You will develop diabetes.")
    assert "mortality" in classical_violations("This indicates the death of the father.")
    assert "guarantee" in classical_violations("Success is guaranteed this year.")

    out = finalize_classical_html(
        "<p>Your 7th lord Venus is in the 8th house. You will develop diabetes.</p>")
    assert "7th lord Venus" in out
    assert "diabetes" not in out


def test_voice_rejects_unusable_book_prose() -> None:
    import classical_voice as CV

    assert not CV.sentence_ok("Aries is the first sign of Zodiac.")
    assert not CV.sentence_ok("You with weak Saturn in lagna will be sick and lazy.")
    assert not CV.sentence_ok("The native will suffer from leprosy and die young.")
    assert CV.sentence_ok("You are of medium height, with an active brain and good memory.")


def test_voice_rejects_family_discord_and_relative_events() -> None:
    import classical_voice as CV

    assert not CV.sentence_ok(
        "The native gets little pleasure from elder brother and tends to divide his family."
    )
    assert not CV.sentence_ok("The native's maternal uncle will be a famous person.")
    assert not CV.sentence_ok("You will have enmity with your own relatives.")


def test_voice_bullet_shape() -> None:
    import classical_voice as CV

    out = CV.bullet("Career mindset", "Mercury rules your 1st and 10th",
                    "you plan before you act")
    assert out.startswith("<li><b>Career mindset</b>: ")
    assert "Mercury rules your 1st and 10th. You plan before you act." in out
