#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Goel D30 chart analysis - fortune/misfortune topics (rules15 / Predict with Trishamsha)."""
from __future__ import annotations

from typing import Any

from astro_precompute import get_dignity
from goel_stress_timing import compute_stress_timing
from goel_trishamsha_extras import _lagna_fortune_tone, analyze_trishamsha_extras
from vedic_varga_goel import (
    MALEFIC_LAGNA_LORDS,
    BENEFICS,
    MALEFICS,
    VargaChart,
    parse_shodashvarga,
    varga_from_divisional,
)

GRAHAS = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}


def _hl(hl: dict, n: int) -> dict:
    return hl.get(n, hl.get(str(n), {}))


def _d30_from_pc(pc: dict, extract_text: str = "") -> VargaChart | None:
    vc = varga_from_divisional(pc, "D30")
    if vc:
        return vc
    if extract_text:
        return parse_shodashvarga(extract_text).get("D30")
    return None


def _build_d30_houses(d30: VargaChart) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {h: [] for h in range(1, 13)}
    for p in GRAHAS:
        h = d30.planet_house(p)
        if h:
            out[h].append(p)
    return out


def analyze_trishamsha_chart(pc: dict, extract_text: str = "", female: bool = False) -> dict[str, Any]:
    if not female:
        g = pc.get("meta", {}).get("gender", pc.get("gender"))
        female = g == 1 or g == "female"
    d30 = _d30_from_pc(pc, extract_text)
    if not d30:
        return {"error": "Trishamsha (D30) not found — need divisional.D30 in precompute or Shodashvarga extract."}

    d9 = varga_from_divisional(pc, "D9")
    if not d9 and extract_text:
        d9 = parse_shodashvarga(extract_text).get("D9")
    hl = pc.get("house_lords", {})
    lord1_d1 = _hl(hl, 1).get("lord", "")
    lord6_d1 = _hl(hl, 6).get("lord", "")
    lord7_d1 = _hl(hl, 7).get("lord", "")
    lord8_d1 = _hl(hl, 8).get("lord", "")

    d30_houses = _build_d30_houses(d30)
    d30_lagna_lord = d30.house_lord(1)
    lord8_d30 = d30.house_lord(8)
    ll_h = d30.planet_house(d30_lagna_lord)
    l8_h = d30.planet_house(lord8_d30)
    moon_h = d30.planet_house("Moon")

    lagna_tone, lagna_score, lagna_facts = _lagna_fortune_tone(d30)
    fortunate = lagna_tone == "benefic"
    misfortune = lagna_tone == "malefic"

    h8_score = d30.benefic_score(8)
    h7_score = d30.benefic_score(7)
    h4_score = d30.benefic_score(4)

    flags: list[str] = []
    if misfortune and d30.house_lord(1) in MALEFIC_LAGNA_LORDS:
        flags.append("misfortune_lagna")
    ll_dig = get_dignity(d30_lagna_lord, d30.signs.get(d30_lagna_lord, ""))
    if ll_h in (6, 8, 12) and ll_dig in ("debilitated", "enemy_sign"):
        flags.append("self_trouble")
    if h8_score <= -1:
        flags.append("h8_stress")
    if moon_h in (6, 8, 12):
        flags.append("moon_stress")
    if h7_score <= -1:
        flags.append("harsh_marriage")

    malefic_on_lagna = [p for p in d30.tenants(1) if p in MALEFICS]
    d1_lagna = pc.get("meta", {}).get("lagna_sign", "")
    d1_lagna_stress = any(
        p in malefic_on_lagna and pc.get("planets", {}).get(p, {}).get("house") == 1
        for p in malefic_on_lagna
    )

    extras = analyze_trishamsha_extras(pc, d30, lagna_tone, fortunate)

    payload: dict[str, Any] = {
        "female": female,
        "d30_lagna": d30.lagna,
        "d30_lagna_lord": d30_lagna_lord,
        "d30_lagna_lord_house": ll_h,
        "lord8_d30": lord8_d30,
        "lord8_d30_house": l8_h,
        "lord1_d1": lord1_d1,
        "lord6_d1": lord6_d1,
        "lord7_d1": lord7_d1,
        "lord8_d1": lord8_d1,
        "d1_lagna": d1_lagna,
        "d30_houses": d30_houses,
        "lagna_tone": lagna_tone,
        "lagna_score": lagna_score,
        "lagna_facts": lagna_facts,
        "fortunate": fortunate,
        "misfortune": misfortune,
        "h8_score": h8_score,
        "h7_score": h7_score,
        "h4_score": h4_score,
        "moon_d30_house": moon_h,
        "flags": flags,
        "d1_lagna_stress_overlap": d1_lagna_stress,
        "d9_available": d9 is not None,
        "extras": extras,
    }
    payload["stress_timing_detail"] = compute_stress_timing(pc, payload)
    return payload
