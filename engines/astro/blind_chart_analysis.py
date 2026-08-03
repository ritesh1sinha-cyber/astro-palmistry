#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blind chart (Nadi) analysis - Guru Rajesh method (rules17)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from blind_chart_narrative import build_blind_narratives
from vedic_blindchart_report import (
    STRONG,
    WEAK,
    Blind,
    _chain_phrase,
    _detect_female,
    _lord_verdict,
    _prog_states,
    _prog_verdict,
    from_x,
    house_of,
)

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

SATURN_FIELD = {
    "Aries": "machinery, engineering, competitive fields, or physical effort work",
    "Taurus": "banking, food, finance, or stable institutional roles",
    "Gemini": "communication, business, media, or academic institutions",
    "Cancer": "hospitals, hospitality, liquids, or nurturing industries",
    "Leo": "government, administration, authority, or prestigious institutions",
    "Virgo": "health service, agriculture, detailed technical work, or analysis",
    "Libra": "law, contracts, courts, design, or partnership-based professions",
    "Scorpio": "investigation, research, finance depth, insurance, or crisis work",
    "Sagittarius": "teaching, law, foreign travel, philosophy, or advisory roles",
    "Capricorn": "discipline, military, structure, administration, or labour-intensive careers",
    "Aquarius": "government service, reform, intellectual organisations, or technology",
    "Pisces": "spiritual institutions, foreign lands, hospitals, or fluid/creative work",
}

SUN_FATHER = {
    "Leo": "authority, government, or leadership-facing father",
    "Aquarius": "intellectual, reform-minded, or government-service father",
    "Scorpio": "secretive, research, or depth-work father",
    "Capricorn": "disciplined, service, or structural career father",
    "Libra": "fair-minded, legal, or contract-oriented father",
}

MALE_PLANETS = {"Sun", "Mars", "Jupiter", "Rahu"}
FEMALE_PLANETS = {"Moon", "Venus", "Ketu"}


def _zones(b: Blind, planet: str) -> dict[str, dict[str, Any]]:
    if planet not in b.planets:
        return {}
    base = b.planets[planet]["sign"]
    bi = SIGNS.index(base)
    out: dict[str, dict[str, Any]] = {}
    for offset, label in ((1, "2nd"), (10, "11th"), (6, "7th"), (9, "10th"), (11, "12th")):
        sign = SIGNS[(bi + offset) % 12]
        occ = [p for p in b.by_sign.get(sign, []) if p in b.planets]
        out[label] = {"sign": sign, "planets": occ, "house_from_lagna": house_of(sign, b.lagna)}
    return out


def _sibling_read(b: Blind) -> dict[str, Any]:
    chain = b.chain_ahead("Jupiter", 12)
    males = sorted({p for _, occ in chain for p in occ if p in MALE_PLANETS})
    females = sorted({p for _, occ in chain for p in occ if p in FEMALE_PLANETS})
    n_before = len(chain)
    youngest = n_before >= 2
    text = (
        f"Planets ahead of Jupiter in the zodiac chain: {_chain_phrase(b, chain[:4]) or 'sparse chain'}. "
    )
    if males or females:
        text += f"Male sibling signals: {', '.join(males) or 'none strong'}. "
        text += f"Female sibling signals: {', '.join(females) or 'none strong'}. "
    if youngest:
        text += "Many occupants ahead of Jupiter - the native reads as younger in the sibling line."
    else:
        text += "Fewer planets ahead of Jupiter - the native may be among the earlier-born."
    return {
        "chain": [{"sign": s, "planets": o} for s, o in chain],
        "male_signals": males,
        "female_signals": females,
        "likely_youngest": youngest,
        "text": text.strip(),
    }


def _education_read(b: Blind) -> dict[str, Any]:
    merc = b.planets["Mercury"]
    jup_same = "Jupiter" in b.by_sign.get(merc["sign"], [])
    deb_neecha = merc["dignity"] == "debilitated"
    parts = [f"Mercury in {merc['sign']} ({b.dig('Mercury')}) shapes education and intellect."]
    if jup_same:
        parts.append(
            "Mercury joined Jupiter - despite table enmity, the book calls this a great asset for education."
        )
    elif deb_neecha:
        parts.append("Mercury debilitated - late bloomer or non-linear study path; companion planets decide final success.")
    else:
        parts.append("Fields lean communicative, analytical, commercial, or semi-technical rather than purely manual.")
    tone = "strong" if merc["dignity"] in STRONG or jup_same else ("weak" if merc["dignity"] in WEAK and not jup_same else "mixed")
    return {"tone": tone, "text": " ".join(parts), "mercury_jupiter": jup_same}


def _father_read(b: Blind) -> dict[str, Any]:
    sun = b.planets["Sun"]
    zones = _zones(b, "Sun")
    z2 = zones.get("2nd", {})
    field = SUN_FATHER.get(sun["sign"], f"character coloured by {sun['sign']} themes")
    text = (
        f"Sun in {sun['sign']} ({b.dig('Sun')}) - father reads as {field}. "
    )
    if z2.get("planets"):
        text += f"Second from Sun: {', '.join(z2['planets'])} in {z2['sign']} shapes income and family speech around father."
    return {"text": text, "zones": zones, "tone": _lord_verdict(b, "Sun")}


def _mother_read(b: Blind) -> dict[str, Any]:
    moon = b.planets["Moon"]
    zones = _zones(b, "Moon")
    tenants = b.by_sign.get(moon["sign"], [])
    parts = [f"Moon in {moon['sign']} ({b.dig('Moon')}) - mother is practical and emotionally grounding."]
    if "Mercury" in tenants:
        parts.append("Moon with Mercury - educated, communicative, or administratively capable mother.")
    if "Saturn" in tenants:
        parts.append("Moon with Saturn - disciplined, service-oriented, or labour-intensive mother role.")
    if "Sun" in tenants:
        parts.append("Moon with Sun - authority or public-respect themes around mother.")
    if len(tenants) <= 1:
        parts.append("Moon relatively alone - domestic, home-centric orientation is emphasised in case literature.")
    return {"text": " ".join(parts), "zones": zones, "tone": _lord_verdict(b, "Moon")}


def _career_read(b: Blind) -> dict[str, Any]:
    sat = b.planets["Saturn"]
    zones = _zones(b, "Saturn")
    field = SATURN_FIELD.get(sat["sign"], "work follows Saturn sign themes")
    retro = " Saturn is retrograde - read also from the previous sign for a dual professional thread." if sat["retro"] else ""
    z11 = zones.get("11th", {})
    income = ""
    if z11.get("planets"):
        income = f" Income drivers: {', '.join(z11['planets'])} in {z11['sign']} (11th from Saturn)."
    return {
        "text": f"Saturn in {sat['sign']}{retro} - career field: {field}.{income}",
        "zones": zones,
        "tone": _lord_verdict(b, "Saturn"),
    }


def _marriage_read(b: Blind, female: bool) -> dict[str, Any]:
    karaka = "Jupiter" if female else "Venus"
    k = b.planets[karaka]
    zones = _zones(b, karaka)
    moon_h = from_x(b.planets["Moon"]["sign"], k["sign"])
    mars_rahu = b.pressure_sign()
    mars_from = from_x(mars_rahu, k["sign"])
    if female:
        partner = (
            f"Jupiter in {k['sign']} ({b.dig('Jupiter')}) describes a spouse who is wise, expansive, and teacher-like."
            if k["dignity"] in STRONG
            else f"Jupiter in {k['sign']} describes a spouse who grows through patience and lived experience."
        )
    else:
        partner = (
            f"Venus exalted in {k['sign']} - the strongest spouse placement: educated, graceful, emotionally capable partner."
            if k["dignity"] == "exalted"
            else f"Venus in {k['sign']} ({b.dig('Venus')}) - relationship-oriented, refined partner."
        )
    text = (
        f"{partner} Moon in the {moon_h}th from {karaka} ({b.planets['Moon']['sign']}) adds practical, service-minded character. "
        f"Mars+Rahu pressure in the {mars_from}th from {karaka} can test early union ease - passion or financial heat before settling."
    )
    return {"text": text, "karaka": karaka, "zones": zones, "tone": _lord_verdict(b, karaka)}


def _children_read(b: Blind) -> dict[str, Any]:
    ketu = b.planets["Ketu"]
    h5_sign = SIGNS[(SIGNS.index(b.lagna) + 4) % 12]
    prog_hits = []
    for st in _prog_states(b, 20, 45):
        if st["jup"] == h5_sign or st["jup"] == ketu["sign"]:
            prog_hits.append(st["age"])
        if len(prog_hits) >= 3:
            break
    text = (
        f"Ketu in {ketu['sign']} (house {ketu['house']}) invites unconventional timing or detachment themes in the child story. "
    )
    if prog_hits:
        text += f"Jupiter progression touches progeny angles around ages {', '.join(str(a) for a in prog_hits)} - calibrate with dated events."
    else:
        text += "Watch Jupiter progression through the fifth-house sign for childbirth windows."
    return {"text": text, "prog_ages": prog_hits, "tone": "neutral"}


def _wealth_read(b: Blind) -> dict[str, Any]:
    ven = b.planets["Venus"]
    mars_rahu = b.pressure_sign()
    mf = from_x(mars_rahu, ven["sign"])
    text = (
        f"Venus in {ven['sign']} ({b.dig('Venus')}) is the primary wealth and comfort karaka. "
    )
    if ven["dignity"] == "exalted":
        text += "Exalted Venus - long-term financial struggle is not the base promise. "
    text += f"Mars+Rahu in the {mf}th from Venus marks possible volatility phases in earnings."
    return {"text": text, "tone": _lord_verdict(b, "Venus")}


def _health_read(b: Blind) -> dict[str, Any]:
    from vedic_blindchart_report import SIGN_BODY
    jup = b.planets["Jupiter"]
    mars_rahu = b.pressure_sign()
    sat = b.planets["Saturn"]
    text = (
        f"Jupiter in {jup['sign']} - watch {SIGN_BODY[jup['sign']]}. "
        f"Mars+Rahu in {mars_rahu} - {SIGN_BODY[mars_rahu]} sensitivity when progressions re-touch this sign. "
        f"Saturn in {sat['sign']} - {SIGN_BODY[sat['sign']]} needs preventive maintenance. "
        f"Mercury {b.dig('Mercury')} - stress may show as overthinking; creative output helps."
    )
    tone = "amber" if jup["dignity"] in WEAK or _prog_verdict(b, b.jup_prog(b.age), b.sat_prog(b.age)) == "hard" else "neutral"
    return {"text": text, "tone": tone}


def _decade_bands(b: Blind) -> list[dict[str, Any]]:
    bands = [(0, 10), (10, 20), (20, 30), (30, 40), (40, min(50, b.age + 5))]
    out = []
    for lo, hi in bands:
        if lo > b.age:
            continue
        hi_eff = min(hi, b.age + 8)
        states = _prog_states(b, lo, min(hi_eff, b.age + 8))
        if not states:
            continue
        mid = states[len(states) // 2]
        out.append({
            "label": f"Age {lo}-{hi}",
            "age_lo": lo,
            "age_hi": hi,
            "sample_age": mid["age"],
            "year": mid["year"],
            "jup": mid["jup"],
            "sat": mid["sat"],
            "verdict": mid["verdict"],
            "note": mid["note"],
        })
    return out


def analyze_blind_chart(pc: dict, extract_text: str = "", female: bool = False) -> dict[str, Any]:
    dob_str = pc.get("meta", {}).get("dob", "")
    if not dob_str:
        return {"error": "Date of birth missing from precompute."}
    dob = datetime.strptime(dob_str[:10], "%Y-%m-%d").date()
    if not female:
        g = pc.get("meta", {}).get("gender", pc.get("gender"))
        if g is None and extract_text:
            female = _detect_female(extract_text)
        else:
            female = g == 1 or g == "female"

    b = Blind(pc, dob)
    narratives = build_blind_narratives(b, female)

    return {
        "female": female,
        "lagna": b.lagna,
        "age": b.age,
        "jupiter_sign": b.planets["Jupiter"]["sign"],
        "saturn_sign": b.planets["Saturn"]["sign"],
        "pressure_sign": b.pressure_sign(),
        "cur_jup_prog": b.jup_prog(b.age),
        "cur_sat_prog": b.sat_prog(b.age),
        "narratives": narratives,
    }
