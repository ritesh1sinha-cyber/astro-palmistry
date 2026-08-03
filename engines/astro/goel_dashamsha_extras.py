#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Goel Dashamsha extras - deities, Saturn mode, rise/fall, fame, education link (rules13)."""
from __future__ import annotations

from typing import Any

from astro_precompute import get_dignity
from goel_varga import SIGNS, dashamsha_sign
from vedic_varga_goel import VargaChart

TRIK = {6, 8, 12}
UPACHAYA = {3, 6, 10, 11}
PP_PLANETS = {"Sun", "Moon", "Mars", "Rahu"}
STRONG_DIGNITY = {"exalted", "own_sign", "moolatrikona"}

DEITIES = [
    ("Indra", "Sun", "Government service, authority, departmental leadership"),
    ("Agni", "Venus", "Energy trades, fire, police, cooking, metallurgy"),
    ("Yama", "Mars", "Law, discipline, judges, bureaucracy, engineering"),
    ("Rakshasa", "Rahu", "Intense work, enforcement, mystery, occult-adjacent fields"),
    ("Varuna", "Saturn", "Water, depth, medicine, foreign trade, skilled crafts"),
    ("Vayu", "Moon", "Movement, writing, teaching, frequent job changes"),
    ("Kubera", "Mercury", "Wealth creation, accounts, tax, banking, commerce"),
    ("Ishana", "Jupiter", "Counsel, teaching, priesthood, advisory roles"),
    ("Brahma", "Mercury", "Creation, wisdom, foundational knowledge work"),
    ("Ananta", "Ketu", "All-pervading fame, zenith recognition when D10 10th is strong"),
]

PLANET_AVOCATION = {
    "Sun": "government, administration, medicine, or leadership roles",
    "Moon": "public dealing, hospitality, liquids, or mass-facing work",
    "Mars": "engineering, army, police, surgery, or competitive fields",
    "Mercury": "accounts, writing, trade, IT, or semi-technical professions",
    "Jupiter": "law, teaching, finance, counselling, or advisory work",
    "Venus": "arts, luxury, design, entertainment, or relationship industries",
    "Saturn": "labour, mining, structure, service, or long-endurance careers",
    "Rahu": "machines, imports, media, or unconventional corporate paths",
    "Ketu": "precision crafts, research, occult, or export-oriented niches",
}


def dashamsha_deity(sign: str, deg_in_sign: float) -> dict[str, Any]:
    """Dashamsha dikpala for a graha longitude (rules13 section 5)."""
    i = SIGNS.index(sign)
    part = min(int(deg_in_sign / 3), 9)
    idx = part if i % 2 == 0 else 9 - part
    name, ruler, flavour = DEITIES[idx]
    return {
        "deity": name,
        "ruler": ruler,
        "flavour": flavour,
        "segment": part + 1,
        "sign": sign,
        "degree": round(deg_in_sign, 2),
    }


def _planet_deity_in_chart(pc: dict, planet: str, d10: VargaChart | None) -> dict[str, Any]:
    data = pc.get("planets", {}).get(planet, {})
    d1_sign = data.get("sign", "")
    deg = float(data.get("degree_in_sign", 0))
    if not d1_sign:
        return {"computed": False}
    base = dashamsha_deity(d1_sign, deg)
    d10_sign = d10.signs.get(planet, "") if d10 else dashamsha_sign(d1_sign, deg)
    d10_h = d10.planet_house(planet) if d10 else 0
    ruler_dig = get_dignity(base["ruler"], d10.signs.get(base["ruler"], d10_sign))
    base.update({
        "computed": True,
        "planet": planet,
        "d10_sign": d10_sign,
        "d10_house": d10_h,
        "ruler_dignity": ruler_dig,
        "ruler_strong": ruler_dig in STRONG_DIGNITY or ruler_dig == "friendly_sign",
    })
    return base


def _saturn_mode_in_chart(chart: VargaChart, d1_lagna: str) -> str:
    """Gocharastha vs Agocharastha per rules13 section 9."""
    sat_sign = chart.signs.get("Saturn", "")
    if not sat_sign:
        return "mixed"
    sat_h = chart.planet_house("Saturn")
    dig = get_dignity("Saturn", sat_sign)
    trik_lord = any(chart.house_lord(h) == "Saturn" for h in TRIK)
    if dig in STRONG_DIGNITY and sat_h not in TRIK and not trik_lord:
        return "gocharastha"
    if dig == "debilitated" or sat_h in TRIK or trik_lord:
        return "agocharastha"
    return "mixed"


def _d1_saturn_mode(pc: dict) -> str:
    sat = pc.get("planets", {}).get("Saturn", {})
    if not sat.get("sign"):
        return "mixed"
    sat_h = int(sat.get("house", 0))
    dig = get_dignity("Saturn", sat["sign"])
    hl = pc.get("house_lords", {})
    trik_lord = any(
        hl.get(h, hl.get(str(h), {})).get("lord") == "Saturn" for h in TRIK
    )
    if dig in STRONG_DIGNITY and sat_h not in TRIK and not trik_lord:
        return "gocharastha"
    if dig == "debilitated" or sat_h in TRIK or trik_lord:
        return "agocharastha"
    return "mixed"


def _saturn_career_modes(pc: dict, d9: VargaChart | None, d10: VargaChart) -> dict[str, Any]:
    modes = {
        "D1": _d1_saturn_mode(pc),
        "D9": _saturn_mode_in_chart(d9, pc.get("meta", {}).get("lagna_sign", "")) if d9 else "mixed",
        "D10": _saturn_mode_in_chart(d10, pc.get("meta", {}).get("lagna_sign", "")),
    }
    g = modes.get("D1")
    a = modes.get("D10")
    if g == a == "gocharastha":
        verdict = "Stable self-employment or high autonomy - Saturn reads as Gocharastha in birth and dashamsha."
        mode = "independent"
    elif g == a == "agocharastha":
        verdict = "Structured service or duty-bound employment suits better - Saturn reads as Agocharastha in both charts."
        mode = "service"
    elif g == "agocharastha" and a == "gocharastha":
        verdict = "Career may shift from service toward independence when dashamsha dasha activates."
        mode = "shift_to_independent"
    elif g == "gocharastha" and a == "agocharastha":
        verdict = "Early independence may give way to institutional roles unless dashamsha lords are strengthened."
        mode = "shift_to_service"
    else:
        verdict = "Mixed Saturn signature - neither pure boss nor pure employee; context and dasha decide."
        mode = "mixed"
    return {"modes": modes, "verdict": verdict, "mode": mode}


def _pp_independence(d10: VargaChart, d1_lagna: str, pc: dict) -> dict[str, Any]:
    d10_pp = [p for p in PP_PLANETS if d10.planet_house(p) in (1, 10)]
    d1_pp = []
    for p in PP_PLANETS:
        h = pc.get("planets", {}).get(p, {}).get("house")
        if h in (1, 10):
            d1_pp.append(p)
    third_tenth = (
        d10.planet_house(d10.house_lord(3)) == 10
        or d10.planet_house(d10.house_lord(10)) == 3
    )
    score = len(d10_pp) * 2 + len(d1_pp)
    if third_tenth:
        score += 2
    if score >= 4:
        level = "strong"
        text = (
            f"Poorna Paramatma grahas ({', '.join(d10_pp) or 'none on D10 angles'}) "
            "support professional independence - self-employment, entrepreneurship, or command roles fit."
        )
    elif score >= 2:
        level = "moderate"
        text = "Some independent streak in the career map - you can lead projects, but full solo risk needs dasha backing."
    else:
        level = "low"
        text = "Service, team roles, or institutional ladders suit better than gambling on solo ventures without dasha support."
    if third_tenth:
        text += " Third-tenth link in dashamsha adds courage for sudden rise or transfers."
    return {"score": score, "level": level, "text": text, "d10_pp": d10_pp, "d1_pp": d1_pp, "third_tenth_link": third_tenth}


def _capricorn_emphasis(d10: VargaChart, d1_lagna: str, pc: dict) -> dict[str, Any]:
    d10_cap = [p for p in d10.signs if p != "lagna" and d10.signs.get(p) == "Capricorn"]
    d1_cap = [p for p, data in pc.get("planets", {}).items() if data.get("sign") == "Capricorn"]
    active = bool(d10_cap) or d10.lagna == "Capricorn" or d1_cap
    text = ""
    if active:
        parts = []
        if d10.lagna == "Capricorn":
            parts.append("Capricorn rises in dashamsha")
        if d10_cap:
            parts.append(f"{', '.join(d10_cap)} in D10 Capricorn")
        if d1_cap:
            parts.append(f"{', '.join(d1_cap)} in birth Capricorn")
        text = (
            "Kaal Purusha tenth-sign emphasis - " + "; ".join(parts) + ". "
            "Duty, structure, endurance, and visible status are career amplifiers."
        )
    return {"active": active, "d10_planets": d10_cap, "d1_planets": d1_cap, "text": text}


def _upachaya_rise(d10: VargaChart) -> dict[str, Any]:
    filled = [h for h in UPACHAYA if d10.tenants(h) or d10.benefic_score(h) >= 0]
    h10_has = bool(d10.tenants(10)) or d10.benefic_score(10) >= 0
    count = len(filled)
    strong = h10_has and count >= 2
    text = ""
    if strong:
        text = (
            "Upachaya houses (3/6/10/11) are active in dashamsha with tenth-house support - "
            "karmic rise through effort, competition, and incremental gains is promised."
        )
    elif count >= 2:
        text = "Partial upachaya support - career grows in steps rather than one overnight jump."
    return {"strong": strong, "count": count, "text": text}


def _fall_risk(d10: VargaChart, d1_lagna: str, pc: dict) -> dict[str, Any]:
    hits: list[str] = []
    score = 0
    t10_lord = d10.house_lord(10)
    t10_h = d10.planet_house(t10_lord)
    if t10_h in TRIK:
        hits.append("D10 tenth lord in trik house")
        score += 2
    if d10.benefic_score(8) <= -1:
        hits.append("Malefic weight on D10 8th - scandal or sudden fall risk if ethics slip")
        score += 2
    if d10.benefic_score(10) <= -1:
        hits.append("Afflicted D10 10th house")
        score += 1
    hl = pc.get("house_lords", {})
    l10 = hl.get(10, hl.get("10", {})).get("lord", "")
    if l10:
        l10_h = pc.get("planets", {}).get(l10, {}).get("house", 0)
        if l10_h in TRIK:
            hits.append("Birth tenth lord in trik")
            score += 1
    level = "high" if score >= 3 else ("moderate" if score >= 1 else "low")
    text = "; ".join(hits) + ". Stay legal, document decisions, and avoid hostile dasha leaps." if hits else ""
    return {"score": score, "level": level, "hits": hits, "text": text}


def _fame_11th(d10: VargaChart) -> dict[str, Any]:
    h11 = d10.benefic_score(11)
    tenants = d10.tenants(11)
    fame_givers = [p for p in tenants if p in ("Sun", "Jupiter", "Venus", "Moon")]
    strong = h11 >= 1 or len(fame_givers) >= 1
    text = ""
    if strong:
        text = "Dashamsha eleventh house is supported - awards, influential networks, and income from reputation are live themes."
        if fame_givers:
            text += f" Fame-givers here: {', '.join(fame_givers)}."
    elif h11 <= -1:
        text = "Eleventh house in dashamsha is stressed - gains may come without public honour, or friends may mislead."
    return {"strong": strong, "score": h11, "fame_planets": fame_givers, "text": text}


def _education_link(pc: dict, d10: VargaChart) -> dict[str, Any]:
    hl = pc.get("house_lords", {})
    l5 = hl.get(5, hl.get("5", {})).get("lord", "")
    if not l5:
        return {"computed": False}
    l5_d10_h = d10.planet_house(l5)
    l5_d10_sign = d10.signs.get(l5, "")
    tags = []
    if l5 in ("Mercury", "Mars", "Saturn") or l5_d10_h in (3, 6, 10):
        tags.append("technical or skill-heavy final path")
    if l5 in ("Venus", "Moon") or l5_d10_h in (5, 12):
        tags.append("creative or people-facing refinement")
    if l5 in ("Sun", "Jupiter") or l5_d10_h in (9, 10):
        tags.append("government, law, or advisory tone")
    text = (
        f"Fifth lord {l5} sits in dashamsha house {l5_d10_h or '?'} ({l5_d10_sign}) - "
        + (", ".join(tags) if tags else "education feeds career through that house channel")
        + "."
    )
    return {"computed": True, "lord5": l5, "d10_house": l5_d10_h, "d10_sign": l5_d10_sign, "text": text, "tags": tags}


def _avocation_blend(d10: VargaChart, d1_10th_lord: str, pc: dict) -> dict[str, Any]:
    tenants_lagna = d10.tenants(1)
    tenants_10 = d10.tenants(10)
    key_planets = list(dict.fromkeys(
        tenants_lagna + tenants_10 + [d1_10th_lord, d10.house_lord(1), d10.house_lord(10)]
    ))
    key_planets = [p for p in key_planets if p in PLANET_AVOCATION]
    flavours = [PLANET_AVOCATION[p] for p in key_planets[:4]]
    text = ""
    if flavours:
        text = "Career flavour from dashamsha lagna/10th and birth tenth lord: " + "; ".join(flavours[:3]) + "."
    return {"planets": key_planets, "text": text}


def _house_extras(d10: VargaChart) -> dict[str, Any]:
    out: dict[str, Any] = {}
    h2 = d10.benefic_score(2)
    out["speech_wealth"] = {
        "score": h2,
        "text": (
            "Second house strong - speech, family business, or stored wealth feeds career."
            if h2 >= 0
            else "Second house stressed - harsh speech or savings leaks can hurt professional harmony."
        ),
    }
    h4 = d10.benefic_score(4)
    out["public_base"] = {
        "score": h4,
        "text": (
            "Fourth house supported - public acceptance, office base, or mass appeal helps profession."
            if h4 >= 0
            else "Fourth house mixed - home-work balance or public acceptance needs deliberate effort."
        ),
    }
    h7 = d10.benefic_score(7)
    out["partnership"] = {
        "score": h7,
        "text": (
            "Seventh house active - partnerships, corporates, or foreign links shape career."
            if h7 >= 0
            else "Seventh house strained - partnership hurdles or corporate politics need patience."
        ),
    }
    h12 = d10.benefic_score(12)
    out["foreign_retreat"] = {
        "score": h12,
        "text": (
            "Twelfth house benefic - foreign firms, MNC, or behind-the-scenes work can prosper."
            if h12 >= 0
            else "Twelfth house malefic - hidden enemies, losses, or isolation themes at work - stay transparent."
        ),
    }
    return out


def analyze_dashamsha_extras(
    pc: dict,
    d10: VargaChart,
    d9: VargaChart | None,
    d1_10th_lord: str,
) -> dict[str, Any]:
    lagna = pc.get("meta", {}).get("lagna_sign", "")
    ll = d10.house_lord(1)
    t10 = d10.house_lord(10)
    deities = {
        "lagna_lord": _planet_deity_in_chart(pc, ll, d10),
        "tenth_lord": _planet_deity_in_chart(pc, t10, d10),
        "sun": _planet_deity_in_chart(pc, "Sun", d10),
        "moon": _planet_deity_in_chart(pc, "Moon", d10),
    }
    return {
        "deities": deities,
        "saturn_career": _saturn_career_modes(pc, d9, d10),
        "pp_independence": _pp_independence(d10, lagna, pc),
        "capricorn": _capricorn_emphasis(d10, lagna, pc),
        "upachaya": _upachaya_rise(d10),
        "fall_risk": _fall_risk(d10, lagna, pc),
        "fame_11th": _fame_11th(d10),
        "education_link": _education_link(pc, d10),
        "avocation": _avocation_blend(d10, d1_10th_lord, pc),
        "house_extras": _house_extras(d10),
    }
