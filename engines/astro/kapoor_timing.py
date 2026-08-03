#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dheer Kapoor - Predictive Astrology & Timing of Events (6 Techniques).
Implemented lanes usable without Jagannath Hora: Age of Activation, Paribhraman
house-year, marriage denial markers. Kaal Chakra / Lagnamsa / Bhrigu Pada need
separate dasha engines (not in PyJHora path yet).
"""
from __future__ import annotations

from datetime import date
from typing import Any

from astro_precompute import SIGNS, get_dignity, house_from_lagna

KAPOOR_RULES = {
    "source": "Predictive Astrology & Timing of Events (Dheer Kapoor, 2025)",
    "ocr": "book_ocr/predictive_astrology_six_techniques/",
    "implemented": [
        "Age of Activation of planets (cross-check dasha window ages)",
        "Paribhraman Paddti house-year activation",
        "Marriage denial: Jupiter-Venus 6-8, Ketu 8th from Venus, malefics in 7th",
        "Marriage support: Jupiter conjunct/aspect Venus",
        "12th-house planet marriage potential at planet activation age",
        "Debilitated dasha lord weak at activation age",
    ],
    "pending": [
        "Kaal Chakra Dasha (nakshatra dasha - separate software)",
        "Lagnamsa Dasha per varga (Jagannath Hora)",
        "Bhrigu Pada Dasha (Arudha progression)",
        "Full Paribhraman annual chart (degree-level day/week)",
    ],
}

# Age of Activation bands (years of life) - Kapoor table p.43-44
PLANET_ACTIVATION_AGES: dict[str, list[tuple[int, int]]] = {
    "Saturn": [(1, 6), (36, 41), (71, 76)],
    "Rahu": [(7, 12), (42, 47), (77, 82)],
    "Ketu": [(13, 18), (48, 53), (88, 93)],
    "Jupiter": [(16, 21), (46, 51), (76, 81), (91, 96)],
    "Sun": [(22, 23), (52, 53), (57, 58), (82, 83), (92, 93)],
    "Moon": [(24, 24), (54, 54), (59, 59), (84, 84), (94, 94)],
    "Venus": [(25, 27), (55, 57), (60, 62), (85, 87), (95, 97)],
    "Mars": [(28, 33), (58, 63), (63, 68), (88, 93)],
    "Mercury": [(34, 35), (64, 70), (99, 105)],
}

EVENT_PARIBHRAMAN_HOUSES: dict[str, list[int]] = {
    "marriage": [7, 2, 11],
    "child": [5, 9, 4],
    "career": [10, 6, 11],
    "property": [4, 11, 12],
    "education": [5, 9, 4],
    "travel": [12, 9, 3],
    "business": [7, 10, 11],
}

EVENT_ACTIVATION_LORDS: dict[str, list[str]] = {
    "marriage": ["Venus", "Jupiter"],
    "child": ["Jupiter", "Venus"],
    "career": ["Saturn", "Sun", "Mercury"],
    "property": ["Mars", "Moon", "Saturn"],
    "education": ["Mercury", "Jupiter"],
    "travel": ["Rahu", "Moon"],
    "business": ["Mercury", "Venus", "Jupiter"],
}

MALEFICS = frozenset({"Sun", "Mars", "Saturn", "Rahu", "Ketu"})
BENEFICS = frozenset({"Moon", "Mercury", "Jupiter", "Venus"})
GRAHAS = MALEFICS | BENEFICS


def _age_on(dob: date, when: date) -> int:
    return max(0, (when - dob).days // 365)


def _in_activation_band(planet: str, age: int) -> bool:
    for lo, hi in PLANET_ACTIVATION_AGES.get(planet, []):
        if lo <= age <= hi:
            return True
    return False


def paribhraman_house(age: int) -> int:
    """House activated in year `age` (Kapoor: age 19 -> 7th house)."""
    if age < 1:
        return 1
    return ((age - 1) % 12) + 1


def _house_distance(h1: int, h2: int) -> int:
    return (h2 - h1) % 12


def _shashtashtaka(h1: int, h2: int) -> bool:
    d = _house_distance(h1, h2)
    return d in (5, 7)  # 6th or 8th house apart


def _jupiter_aspects_planet_sign(jup_sign: str, target_sign: str) -> bool:
    if jup_sign not in SIGNS or target_sign not in SIGNS:
        return False
    diff = (SIGNS.index(target_sign) - SIGNS.index(jup_sign)) % 12
    return diff in (0, 4, 6, 8)  # conjunct, 5th, 7th, 9th sign aspects


def assess_kapoor_marriage_static(planets: dict, *, female: bool) -> dict[str, Any]:
    """Kapoor marriage promise/denial markers (case studies 12-13)."""
    karaka = "Jupiter" if female else "Venus"
    reasons: list[str] = []
    denial: list[str] = []

    v = planets.get(karaka, {})
    j = planets.get("Jupiter", {})
    k = planets.get("Ketu", {})
    v_h, j_h, k_h = v.get("house"), j.get("house"), k.get("house")

    tenants_7 = [
        p for p in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
        if planets.get(p, {}).get("house") == 7
    ]
    malefic_7 = [p for p in tenants_7 if p in MALEFICS]
    benefic_7 = [p for p in tenants_7 if p in BENEFICS]
    if malefic_7 and not benefic_7:
        denial.append(f"Malefics only in 7th ({', '.join(malefic_7)})")

    if v_h and j_h and _shashtashtaka(v_h, j_h):
        denial.append("Jupiter and Venus in 6-8 (late / denied marriage theme)")
    elif v_h and j_h:
        if v_h == j_h:
            reasons.append("Jupiter conjunct marriage karaka")
        elif _jupiter_aspects_planet_sign(j.get("sign", ""), v.get("sign", "")):
            reasons.append("Jupiter aspects marriage karaka (Kapoor blessing)")

    if v_h and k_h:
        eighth_from_v = (v_h + 6 - 1) % 12 + 1
        if k_h == eighth_from_v:
            denial.append(f"Ketu 8th from {karaka} (marriage denial)")

    for p in GRAHAS:
        if planets.get(p, {}).get("house") == 12:
            reasons.append(f"{p} in 12th can time marriage at {p} activation age")

    return {"reasons": reasons, "denial": denial}


def kapoor_age_activation_hits(
    dob: date,
    start: date,
    end: date,
    md_lord: str,
    ad_lord: str,
    event_kind: str,
) -> list[str]:
    """Window ages vs Kapoor Age of Activation for dasha lords."""
    hits: list[str] = []
    mid = start + (end - start) // 2
    for when in (start, mid, end):
        age = _age_on(dob, when)
        for lord in (ad_lord, md_lord):
            if lord and _in_activation_band(lord, age):
                hits.append(f"Age {age}: {lord} activation year")
    priority = set(EVENT_ACTIVATION_LORDS.get(event_kind, []))
    if any(l in h for h in hits for l in priority if l in h):
        return hits[:4]
    return hits[:2] if hits else []


def kapoor_paribhraman_hits(
    dob: date,
    start: date,
    end: date,
    event_kind: str,
) -> list[str]:
    houses = set(EVENT_PARIBHRAMAN_HOUSES.get(event_kind, []))
    if not houses:
        return []
    hits: list[str] = []
    y0 = _age_on(dob, start)
    y1 = _age_on(dob, end)
    for age in range(y0, y1 + 1):
        h = paribhraman_house(age)
        if h in houses:
            hits.append(f"Age {age}: Paribhraman {h}th house year")
            if len(hits) >= 3:
                break
    return hits


def kapoor_lord_placement_at_activation(
    lord: str,
    planets: dict,
) -> tuple[bool, str]:
    """Exalted/own vs debilitated at activation (Kapoor rule 2-3)."""
    pdata = planets.get(lord, {})
    sign = pdata.get("sign", "")
    dig = get_dignity(lord, sign)
    if dig in ("exalted", "own_sign", "moolatrikona"):
        return True, f"{lord} well placed ({dig}) for activation delivery"
    if dig == "debilitated":
        return False, f"{lord} debilitated - weak event delivery at activation"
    return True, f"{lord} mixed dignity at activation"


def kapoor_confirm_window(
    *,
    dob: date,
    window_start: date,
    window_end: date,
    md_lord: str,
    ad_lord: str,
    event_kind: str,
    planets: dict,
    composite_tier: str,
) -> dict[str, Any]:
    """Kapoor cross-check on an already composite-qualified window."""
    age_hits = kapoor_age_activation_hits(dob, window_start, window_end, md_lord, ad_lord, event_kind)
    par_hits = kapoor_paribhraman_hits(dob, window_start, window_end, event_kind)
    placement_ok = True
    place_notes: list[str] = []
    for lord in (ad_lord, md_lord):
        if not lord:
            continue
        ok, note = kapoor_lord_placement_at_activation(lord, planets)
        place_notes.append(note)
        if not ok:
            placement_ok = False

    kapoor_score = len(age_hits) + len(par_hits) + (2 if placement_ok else 0)
    if composite_tier == "high" and age_hits and par_hits and placement_ok:
        tier = "confirmed"
    elif composite_tier in ("high", "medium") and (age_hits or par_hits) and placement_ok:
        tier = "kapoor_supported"
    elif age_hits or par_hits:
        tier = "kapoor_partial"
    else:
        tier = "kapoor_weak"

    return {
        "kapoor_tier": tier,
        "kapoor_score": kapoor_score,
        "age_activation_hits": age_hits,
        "paribhraman_hits": par_hits,
        "placement_notes": place_notes,
        "placement_ok": placement_ok,
    }
