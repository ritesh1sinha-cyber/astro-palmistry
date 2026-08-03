#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Goel Navamsha - spouse personality, marital happiness, affair, divorce (Ch.2-4).
Scores internally; client text is plain prediction only.
"""
from __future__ import annotations

from typing import Any

from goel_navamsha_coverage import SIGN_LORD

from goel_varga import SIGNS

MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
BENEFICS = {"Moon", "Mercury", "Jupiter", "Venus"}

# Goel / BPHS tone for D9 7th sign (spouse character sketch)
SEVENTH_SIGN_SPOUSE = {
    "Aries": "direct, active, and independent",
    "Taurus": "steady, sensual, and comfort-loving",
    "Gemini": "talkative, witty, and mentally agile",
    "Cancer": "nurturing, home-centred, and emotionally deep",
    "Leo": "proud, warm, and status-conscious",
    "Virgo": "practical, detail-minded, and service-oriented",
    "Libra": "graceful, diplomatic, and partnership-focused",
    "Scorpio": "intense, private, and emotionally magnetic",
    "Sagittarius": "open, philosophical, and freedom-loving",
    "Capricorn": "serious, dutiful, and career-minded",
    "Aquarius": "unconventional, friendly, and idealistic",
    "Pisces": "soft, imaginative, and spiritually inclined",
}

LORD_HOUSE_SPOUSE = {
    1: "strong personality; marriage shapes your self-image",
    2: "wealth and family values through the union",
    3: "sibling-like rapport; much travel or communication",
    4: "domestic anchor; partner tied to home and mother",
    5: "romance, creativity, and children are central",
    6: "service, health, or conflict themes in the bond",
    7: "partner is the focal point of life",
    8: "deep transformation; inheritance or secrecy",
    9: "dharma, travel, or guru-like spouse",
    10: "career-linked union; spouse supports public life",
    11: "gains and social network through marriage",
    12: "foreign link, private love, or spiritual retreat together",
}


def _score_happiness(h4: list[str], venus_d9: dict) -> tuple[int, list[str]]:
    hits, facts = 0, []
    if not h4:
        hits += 2
        facts.append("Navamsha fourth house is clear - Goel reads marital happiness")
    else:
        aff = [p for p in h4 if p in MALEFICS]
        ben = [p for p in h4 if p in BENEFICS]
        if aff and not ben:
            facts.append(f"Malefics in navamsha fourth ({', '.join(aff)}) strain home peace")
        elif ben and not aff:
            hits += 2
            facts.append(f"Benefics in navamsha fourth ({', '.join(ben)}) support happiness")
        else:
            hits += 1
            facts.append("Mixed fourth house - happiness with effort")
    if venus_d9.get("d9_dignity") == "exalted":
        hits += 2
        facts.append("Venus exalted in navamsha - lasting affection and bedroom harmony")
    elif venus_d9.get("d9_dignity") in ("own_sign", "moolatrikona"):
        hits += 1
    return min(100, hits * 25), facts


def _score_divorce(l7: dict, h7: list[str], h1: list[str], lord8_d9: str, l8: dict, h4: list[str]) -> tuple[int, list[str]]:
    risk, facts = 0, []
    dig = l7.get("d9_dignity", "")
    h = l7.get("d9_house", 0)
    # Exalted Venus in 12 is protective (Goel), not divorce
    if dig in ("debilitated", "enemy_sign"):
        risk += 35
        facts.append("Navamsha seventh lord debilitated - hard to sustain marriage")
    elif dig in ("exalted", "own_sign", "moolatrikona"):
        risk -= 20
        facts.append("Navamsha seventh lord strong - marriage manager holds")
    elif h in (6, 8) and dig not in ("exalted", "own_sign"):
        risk += 25
        facts.append(f"Seventh lord in trik house {h} in navamsha")
    elif h == 12 and dig not in ("exalted", "own_sign", "moolatrikona"):
        risk += 15

    if sum(1 for p in h7 if p in MALEFICS) >= 2:
        risk += 25
        facts.append("Heavy malefics on navamsha seventh")
    if l8.get("d9_house") in (7, 8) or lord8_d9 == l7.get("planet", ""):
        risk += 15
        facts.append("Eighth-house link to seventh - separation theme possible")

    malefic_lagna = sum(1 for p in h1 if p in MALEFICS) > len(h1) / 2
    if malefic_lagna and len(h1) >= 2:
        risk += 15
        facts.append("Navamsha lagna under malefic load - reluctance or friction")

    if h4 and any(p in MALEFICS for p in h4):
        risk += 10
        facts.append("Afflicted fourth - unhappiness can push toward separation")

    if any(p in BENEFICS for p in h7) or dig in ("exalted", "own_sign"):
        risk -= 15
        facts.append("Benefic balance reduces divorce likelihood")

    return max(0, min(100, risk)), facts


def _score_affair(h7: list[str], l7: dict, h4: list[str], h5: list[str], h8: list[str],
                  sexual_urge: bool, lord5_d9: str, l5: dict) -> tuple[int, list[str]]:
    risk, facts = 0, []
    malefic_h7 = sum(1 for p in h7 if p in MALEFICS) >= 1 or (not h7 and False)
    # Goel: malefic 7th + benefic unafflicted 7th lord -> affairs
    if h7 and any(p in MALEFICS for p in h7) and l7.get("d9_dignity") in ("exalted", "own_sign", "friendly_sign", "neutral_sign"):
        risk += 40
        facts.append("Malefic on navamsha seventh with strong seventh lord - affair pattern")
    if sexual_urge:
        risk += 30
        facts.append("Mars and Venus linked in navamsha - high attraction drive")
    if h5 and h8:
        risk += 20
        facts.append("Fifth and eighth houses active - secret attraction theme")
    if lord5_d9 and l5.get("d9_house") in (7, 8):
        risk += 15
        facts.append("Fifth lord tied to seventh/eighth - love-affair signature")
    if h4 and any(p in MALEFICS for p in h4) and not any(p in MALEFICS for p in h7):
        risk += 25
        facts.append("Unhappy fourth with clean seventh - affair may run beside marriage")

    if not h7 and l7.get("d9_dignity") == "exalted":
        risk = max(0, risk - 25)
        facts.append("Empty benefic seventh axis - loyalty outweighs side attractions")

    return max(0, min(100, risk)), facts


def analyze_marriage_life(pc: dict, analysis: dict) -> dict[str, Any]:
    houses = analysis.get("d9_houses", {})
    enriched = analysis.get("d9_enriched", {})
    d9_lagna = analysis.get("d9_lagna", "")
    lord7_sign = analysis.get("lord7_d9_sign", "")
    lord7 = analysis.get("lord7_d9", "")
    l7 = enriched.get(lord7, {})
    l7["planet"] = lord7
    h7 = houses.get(7, [])
    h4 = houses.get(4, [])
    h5 = houses.get(5, [])
    h8 = houses.get(8, [])
    h1 = houses.get(1, [])
    venus = enriched.get("Venus", {})
    moon = enriched.get("Moon", {})
    dk = analysis.get("darakaraka", "")
    dk_e = enriched.get(dk, {}) if dk else {}

    lord5_sign = SIGNS[(SIGNS.index(d9_lagna) + 4) % 12] if d9_lagna else ""
    lord5_d9 = SIGN_LORD.get(lord5_sign, "")
    l5 = enriched.get(lord5_d9, {})

    lord8_sign = SIGNS[(SIGNS.index(d9_lagna) + 7) % 12] if d9_lagna else ""
    lord8_d9 = SIGN_LORD.get(lord8_sign, "")
    l8 = enriched.get(lord8_d9, {})

    # Spouse personality (always descriptive, not scored)
    spouse_traits = []
    if lord7_sign:
        spouse_traits.append(f"Navamsha seventh is {lord7_sign} - spouse tends to be {SEVENTH_SIGN_SPOUSE.get(lord7_sign, 'distinctive')}.")
    if h7:
        spouse_traits.append(f"Planets with the spouse ({', '.join(h7)}) colour temperament directly.")
    if l7.get("d9_house"):
        spouse_traits.append(
            f"Seventh lord {lord7} sits in the {l7['d9_house']}th house - {LORD_HOUSE_SPOUSE.get(l7['d9_house'], 'marriage theme')}."
        )
    if dk and dk_e:
        spouse_traits.append(
            f"Spouse karaka {dk} sits in navamsha {dk_e.get('d9_sign')} (house {dk_e.get('d9_house')})."
        )
        if dk == "Mars":
            spouse_traits.append("Mars as spouse significator - partner is energetic, courageous, possibly technical or athletic.")
        elif dk == "Venus":
            spouse_traits.append("Venus as spouse significator - partner is attractive, artistic, and harmony-seeking.")
        elif dk == "Jupiter":
            spouse_traits.append("Jupiter as spouse significator - partner is wise, generous, and principled.")
        elif dk == "Saturn":
            spouse_traits.append("Saturn as spouse significator - partner is mature, disciplined, possibly older or sober in manner.")
    if moon.get("d9_sign"):
        spouse_traits.append(
            f"Moon in navamsha {moon['d9_sign']} hints at spouse complexion and emotional tone (Goel uses Moon for colour)."
        )

    happy_score, happy_facts = _score_happiness(h4, venus)
    divorce_risk, divorce_facts = _score_divorce(l7, h7, h1, lord8_d9, l8, h4)
    affair_risk, affair_facts = _score_affair(
        h7, l7, h4, h5, h8, analysis.get("sexual_urge", False), lord5_d9, l5,
    )

    extras = _marriage_extras(pc, analysis, h5, h7, l5, lord5_d9, dk, dk_e, venus, enriched)

    return {
        "spouse_traits": spouse_traits,
        "happiness_score": happy_score,
        "happiness_facts": happy_facts,
        "divorce_risk": divorce_risk,
        "divorce_facts": divorce_facts,
        "affair_risk": affair_risk,
        "affair_facts": affair_facts,
        "lord7_sign": lord7_sign,
        "lord7": lord7,
        **extras,
    }


def _marriage_extras(
    pc: dict, analysis: dict, h5: list, h7: list, l5: dict, lord5: str,
    dk: str, dk_e: dict, venus: dict, enriched: dict,
) -> dict[str, Any]:
    """Love/arranged, foreign spouse, age gap, multiple marriage, denial, mangal."""
    planets = pc.get("planets", {})
    lagna = analysis.get("d1_lagna", "")
    d1_h7 = analysis.get("d1_h7_planets", [])
    denial = bool(analysis.get("denial_hits"))
    multiple = len(analysis.get("multiple_signals", [])) >= 2

    # Love marriage: 5th lord linked to 7th (Goel Ch.4 love affairs)
    love = False
    if l5.get("d9_house") in (5, 7, 8) or lord5 == analysis.get("lord7_d9"):
        love = True
    if h5 and (analysis.get("lord7_d9") in h5 or venus.get("d9_house") in (5, 7)):
        love = True

    # Foreign / other
    foreign = bool(analysis.get("dk_foreign")) or venus.get("d9_house") == 12
    if dk_e.get("d9_house") in (9, 12):
        foreign = True
    if enriched.get("Rahu", {}).get("d9_house") == 9:
        foreign = True

    # Spouse age gap - Saturn in D9 5th/7th or DK with Saturn tone
    saturn = enriched.get("Saturn", {})
    age_gap = saturn.get("d9_house") in (5, 7) or dk == "Saturn"
    if saturn.get("d9_house") == 5:
        age_gap = True  # Goel timely example: Saturn in 7th gave age difference

    # Mangal - Mars in classic houses from D1 lagna or D9 lagna (1,2,4,7,8,12)
    mars_d1 = planets.get("Mars", {})
    mars_h = mars_d1.get("house", 0)
    mangal_houses = {1, 2, 4, 7, 8, 12}
    mangal = mars_h in mangal_houses or "Mars" in d1_h7 or "Mars" in h7
    mars_d9_h = enriched.get("Mars", {}).get("d9_house", 0)
    if mars_d9_h in mangal_houses:
        mangal = True

    return {
        "love_marriage": love,
        "foreign_spouse": foreign,
        "spouse_age_gap": age_gap,
        "multiple_marriage": multiple,
        "marriage_denial": denial,
        "mangal_dosha": mangal,
    }
