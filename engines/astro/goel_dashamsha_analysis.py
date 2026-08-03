#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Goel D10 chart analysis - career topics (rules13 / Predict with Dashamsha)."""
from __future__ import annotations

from typing import Any

from astro_precompute import get_dignity
from goel_career_timing import compute_career_timing
from goel_dashamsha_extras import analyze_dashamsha_extras
from vedic_varga_goel import (
    BENEFICS,
    D10_INNER_LORD_IN,
    D10_TENTH_LORD_IN,
    MALEFICS,
    VargaChart,
    parse_shodashvarga,
    varga_from_divisional,
)

GRAHAS = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}


def _hl(hl: dict, n: int) -> dict:
    return hl.get(n, hl.get(str(n), {}))


def _affliction_count(planets: list[str]) -> tuple[int, int]:
    aff = sum(1 for p in planets if p in MALEFICS)
    ben = sum(1 for p in planets if p in BENEFICS)
    return aff, ben


def _d10_from_pc(pc: dict, extract_text: str = "") -> VargaChart | None:
    vc = varga_from_divisional(pc, "D10")
    if vc:
        return vc
    if extract_text:
        return parse_shodashvarga(extract_text).get("D10")
    return None


def _build_d10_houses(d10: VargaChart) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {h: [] for h in range(1, 13)}
    for p in GRAHAS:
        h = d10.planet_house(p)
        if h:
            out[h].append(p)
    return out


def analyze_dashamsha_chart(pc: dict, extract_text: str = "") -> dict[str, Any]:
    d10 = _d10_from_pc(pc, extract_text)
    if not d10:
        return {"error": "Dashamsha (D10) not found — need divisional.D10 in precompute or Shodashvarga extract."}

    d9 = varga_from_divisional(pc, "D9")
    if not d9 and extract_text:
        d9 = parse_shodashvarga(extract_text).get("D9")
    lagna = pc.get("meta", {}).get("lagna_sign", "") or pc.get("lagna", {}).get("sign", "")
    hl = pc.get("house_lords", {})
    lord10_d1 = _hl(hl, 10).get("lord", "")

    d1_h10 = []
    for pl, data in pc.get("planets", {}).items():
        if pl in GRAHAS and data.get("house") == 10:
            d1_h10.append(pl)

    d10_houses = _build_d10_houses(d10)
    d10_lagna_lord = d10.house_lord(1)
    lord10_d10 = d10.house_lord(10)
    ll_h = d10.planet_house(d10_lagna_lord)
    t10_h = d10.planet_house(lord10_d10)

    lagna_t = d10.tenants(1)
    aff_l, ben_l = _affliction_count(lagna_t)
    d10_lagna_score = ben_l - aff_l
    h10_score = d10.benefic_score(10)
    h11_score = d10.benefic_score(11)
    h8_score = d10.benefic_score(8)

    boss_friction = ll_h == 5
    sudden_rise = (
        d10.planet_house(d10.house_lord(3)) == 10
        or d10.planet_house(lord10_d10) == 3
        or "Mars" in d10.tenants(3) + d10.tenants(10)
    )

    ll_dig = get_dignity(d10_lagna_lord, d10.signs.get(d10_lagna_lord, ""))
    career_promise = "mixed"
    if d10_lagna_score >= 1 and h10_score >= 0:
        career_promise = "strong"
    elif d10_lagna_score <= -1 or h10_score <= -1:
        career_promise = "strained"

    extras = analyze_dashamsha_extras(pc, d10, d9, lord10_d1)

    payload = {
        "d10_lagna": d10.lagna,
        "d10_lagna_lord": d10_lagna_lord,
        "d10_lagna_lord_house": ll_h,
        "d10_lagna_lord_meaning": D10_INNER_LORD_IN.get(ll_h, ""),
        "lord10_d10": lord10_d10,
        "lord10_d10_house": t10_h,
        "lord10_d10_meaning": D10_TENTH_LORD_IN.get(t10_h, ""),
        "lord10_d1": lord10_d1,
        "d1_h10_planets": d1_h10,
        "d10_houses": d10_houses,
        "d10_lagna_score": d10_lagna_score,
        "h10_score": h10_score,
        "h11_score": h11_score,
        "h8_score": h8_score,
        "career_promise": career_promise,
        "boss_friction": boss_friction,
        "sudden_rise": sudden_rise,
        "d10_lagna_lord_dignity": ll_dig,
        "extras": extras,
    }
    payload["career_timing_detail"] = compute_career_timing(pc, payload)
    return payload
