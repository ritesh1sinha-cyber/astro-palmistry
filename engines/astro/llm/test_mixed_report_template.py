from datetime import date
from types import SimpleNamespace


def test_mixed_template_keeps_chart_anchors_and_astrologer_prose():
    import report_conversational as R
    from llm.schemas import CardFacts, WindowFact

    card = CardFacts(
        area="profession",
        label="Career & Profession",
        status="supported",
        activation_status="active",
        house=10,
        allowed_planets=["Saturn", "Jupiter"],
        window=WindowFact(start="", end="", label="May 2024 → Oct 2026"),
        timing_windows=[
            WindowFact(start="2027-11-01", end="2028-02-28", label="career_window"),
            WindowFact(start="", end="", label="May 2024 → Oct 2026"),
        ],
    )
    html = R.render(
        {
            "lagna": {"sign": "Capricorn"},
            "planets": {"Moon": {"sign": "Taurus", "nakshatra": "Rohini"}},
            "vimshottari": {
                "current_md": {"md_lord": "Saturn"},
                "current_md_antardashas": [{"status": "current", "ad_lord": "Mercury"}],
            },
        },
        name="Meera",
        today=date(2026, 8, 13),
        paid=True,
        cards=[card],
        prose={
            "astrological_basis": "Saturn's influence on the career axis makes professional progress responsibility-driven.",
            "interpretation": "This is a consolidation phase in which recognition follows sustained responsibility.",
            "personality": "You tend to take important commitments seriously and prefer decisions with substance behind them.",
            "current_phase": "Career matters are taking more weight, but the chart does not show a simple denial of progress.",
            "areas": {
                "profession": {
                    "astrological_basis": "Saturn and Jupiter both support the career reading, with Saturn adding responsibility.",
                    "interpretation": "The combination favours steady professional consolidation rather than an overnight leap.",
                    "outlook": "The career promise is supported and the current period is active.",
                    "timing": "The stronger stretch runs from March 2029 to June 2029.",
                    "manifestation": "This can show through a more defined role or greater responsibility.",
                }
            },
        },
    )
    assert "Capricorn rising" in html
    assert "Moon in Taurus" in html
    assert "Nakshatra: Rohini" in html
    assert "Saturn Mahadasha" in html
    assert "Mercury Antardasha" in html
    assert "Saturn&#x27;s influence on the career axis" in html
    assert "House 10" in html
    assert "underlying promise: Supported" in html
    # The card's only dated window opens in Nov 2027, so the header must not
    # claim the period is running today.
    assert "current activation: Promised, not yet active — opens Nov 2027" in html
    assert "Active now" not in html
    assert "Saturn and Jupiter both support" in html
    assert "Why this reads this way" in html
    assert "01 Nov 2027" in html
    assert "28 Feb 2028" in html
    assert "May 2024 → Oct 2026" in html
    assert "start=" not in html
    assert "The timing engine has not supplied an exact window" not in html
    assert "March 2029" not in html


def test_engine_card_reads_canonical_promise_activation_and_windows():
    import report_conversational as R

    card = SimpleNamespace(
        area="children",
        label="Children",
        house=5,
        direction="support",
        agreement="strong",
        planets=["Jupiter"],
        window="",
        timing_windows=[],
        evidence=[],
        confluence={
            "canonical_result": {
                "promise": {"status": "strongly_supported"},
                "activation": {"status": "strongly_active"},
                "direction": "support",
                "agreement": "strong",
                "timing": {
                    "featured_windows": [
                        {"start": "2026-10-31", "end": "2027-01-25", "label": "children_window"},
                    ]
                },
            }
        },
    )
    html = R.render(
        {"lagna": {"sign": "Aries"}, "planets": {"Moon": {"sign": "Leo"}}},
        name="Meera",
        today=date(2026, 8, 13),
        paid=True,
        cards=[card],
        prose={
            "astrological_basis": "Aries rising with Moon in Leo.",
            "personality": "You tend to act once a direction is clear.",
            "areas": {
                "children": {
                    "outlook": "The area is part of your chart's real potential, and the current period is actively supporting it.",
                    "timing": "This is a genuine opportunity window from March 2029.",
                }
            },
        },
    )
    assert "underlying promise: Strongly supported" in html
    assert "current activation: Promised, not yet active — opens Oct 2026" in html
    assert "Not clearly established" not in html
    assert "31 Oct 2026" in html
    assert "25 Jan 2027" in html
    assert "The timing engine has not supplied an exact window" not in html
    assert "March 2029" not in html


def test_free_template_contains_family_home_and_conversion_teaser():
    import report_conversational as R
    from llm.schemas import CardFacts

    card = CardFacts(
        area="profession",
        label="Career & Profession",
        status="supported",
        activation_status="active",
        house=10,
        allowed_planets=["Saturn", "Jupiter"],
    )
    html = R.render(
        {
            "lagna": {"sign": "Capricorn"},
            "planets": {"Moon": {"sign": "Taurus", "nakshatra": "Rohini"}},
            "vimshottari": {
                "current_md": {"md_lord": "Saturn"},
                "current_md_antardashas": [{"status": "current", "ad_lord": "Mercury"}],
            },
        },
        name="Meera",
        today=date(2026, 8, 13),
        paid=True,
        cards=[card],
        prose={
            "astrological_basis": "Saturn's influence on the career axis makes professional progress responsibility-driven.",
            "interpretation": "This is a consolidation phase in which recognition follows sustained responsibility.",
            "personality": "You tend to take important commitments seriously and prefer decisions with substance behind them.",
            "current_phase": "Career matters are taking more weight, but the chart does not show a simple denial of progress.",
            "areas": {
                "profession": {
                    "astrological_basis": "Saturn and Jupiter both support the career reading, with Saturn adding responsibility.",
                    "interpretation": "The combination favours steady professional consolidation rather than an overnight leap.",
                    "outlook": "The career promise is supported and the current period is active.",
                    "timing": "The stronger stretch runs from November 2027 to February 2028.",
                    "manifestation": "This can show through a more defined role or greater responsibility.",
                }
            },
        },
    )
    assert "Capricorn rising" in html
    assert "Moon in Taurus" in html
    assert "Nakshatra: Rohini" in html
    assert "Saturn Mahadasha" in html
    assert "Mercury Antardasha" in html
    assert "What the chart shows" in html
    assert "Saturn&#x27;s influence on the career axis" in html
    assert "House 10" in html
    assert "underlying promise: Supported" in html
    assert "current activation: Active now" in html
    assert "Saturn and Jupiter both support" in html
    assert "Why this reads this way" in html
    assert "The timing engine has not supplied an exact window" in html
    assert "November 2027" not in html


def test_free_template_contains_family_home_and_conversion_teaser():
    import report_conversational as R
    html = R.render(
        {"lagna": {"sign": "Aries"}, "planets": {"Moon": {"sign": "Leo"}}},
        name="Meera",
        paid=False,
        prose={
            "astrological_basis": "Your Aries rising chart gives the personality a direct and self-starting tone.",
            "personality": "You tend to act decisively once you are convinced a direction is right.",
            "family_note": [
                "Your father comes across as practical and duty-oriented.",
                "Your mother comes across as caring but firm about responsibilities.",
                "Your siblings show an independent streak.",
                "The home you come from appears to have valued responsibility and stability.",
            ],
        },
    )
    assert "FAMILY & HOME" in html
    assert "Father" in html
    assert "Mother" in html
    assert "The full reading also covers the remaining family relationships" in html
    assert "See the full reading, area by area" in html
    assert "Your siblings show an independent streak." not in html
