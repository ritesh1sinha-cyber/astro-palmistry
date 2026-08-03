#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Goel D7 chart analysis - children topics (rules14 / Predict with Saptamsha)."""
from __future__ import annotations

from typing import Any

from astro_precompute import get_dignity
from goel_children_timing import compute_children_timing
from goel_saptamsha_coverage import SIGN_LORD
from goel_saptamsha_extras import analyze_saptamsha_extras
from goel_varga import SIGNS, house_from_sign, navamsha_sign
from vedic_varga_goel import (
    BENEFICS,
    MALEFICS,
    VargaChart,
    _child_houses,
    parse_shodashvarga,
    varga_from_divisional,
)

GRAHAS = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}

MALE_SIGNS = {"Aries", "Cancer", "Leo", "Libra", "Scorpio", "Sagittarius"}
FEMALE_SIGNS = {"Taurus", "Virgo", "Capricorn", "Aquarius"}
DUAL_SIGNS = {"Gemini", "Pisces"}
MALE_PLANETS = {"Sun", "Mars", "Jupiter", "Rahu"}
FEMALE_PLANETS = {"Moon", "Venus", "Ketu"}

D7_LAGNA_CHILD_NATURE = {
    "Sun": "heroic, courageous, and status-conscious",
    "Moon": "gentle, intelligent, and emotionally close",
    "Mars": "bold, proud, and sometimes hard to manage",
    "Mercury": "clever, talkative, and quick to learn",
    "Jupiter": "wise, respectful, and dharmic",
    "Venus": "artistic, affectionate, and drawn to beauty",
    "Saturn": "serious, dutiful, and slower to warm up",
}


def _hl(hl: dict, n: int) -> dict:
    return hl.get(n, hl.get(str(n), {}))


def _affliction_count(planets: list[str]) -> tuple[int, int]:
    aff = sum(1 for p in planets if p in MALEFICS)
    ben = sum(1 for p in planets if p in BENEFICS)
    return aff, ben


def _beeja_kshetra(pc: dict, female: bool, d7: VargaChart | None = None) -> dict[str, Any]:
    from goel_saptamsha_extras import _sphuta_full
    sp = _sphuta_full(pc, female, d7)
    if not sp.get("computed"):
        return {"computed": False}
    return {
        "computed": True,
        "label": sp["label"],
        "d1_sign": sp["d1_sign"],
        "d9_sign": sp["d9_sign"],
        "d7_sign": sp.get("d7_sign", ""),
        "d7_house": sp.get("d7_house", 0),
        "match_count": sp.get("match_count", 0),
        "promise_ok": sp.get("promise_ok", False),
        "in_kendra_trikona": sp.get("in_kendra_trikona", False),
        "in_trik": sp.get("in_trik", False),
    }


def _d7_from_pc(pc: dict, extract_text: str = "") -> VargaChart | None:
    vc = varga_from_divisional(pc, "D7")
    if vc:
        return vc
    if extract_text:
        vargas = parse_shodashvarga(extract_text)
        if "D7" in vargas:
            return vargas["D7"]
    return None


def _build_d7_houses(d7: VargaChart) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {h: [] for h in range(1, 13)}
    for p in GRAHAS:
        h = d7.planet_house(p)
        if h:
            out[h].append(p)
    return out


def _sign_gender(sign: str) -> str:
    if sign in MALE_SIGNS:
        return "male"
    if sign in FEMALE_SIGNS:
        return "female"
    return "dual"


def _planet_gender(planet: str, dignity: str = "") -> str:
    if dignity == "exalted":
        return "male"
    if dignity == "debilitated":
        return "female"
    if planet in MALE_PLANETS:
        return "male"
    if planet in FEMALE_PLANETS:
        return "female"
    return "common"


def _child_gender_goel(
    d7: VargaChart, d9: VargaChart | None, child_house: int, d9_enriched: dict,
) -> dict[str, Any]:
    """Goel Ch.8: lord of child house -> D9 -> decider -> D7 placement."""
    child_sign = d7.house_sign(child_house)
    child_lord = SIGN_LORD[child_sign]
    child_lord_d9 = d9.signs.get(child_lord, "") if d9 else ""
    if not child_lord_d9 and child_lord in d9_enriched:
        child_lord_d9 = d9_enriched[child_lord].get("d9_sign", "")
    decider = SIGN_LORD.get(child_lord_d9, child_lord) if child_lord_d9 else child_lord
    decider_d7_h = d7.planet_house(decider)
    decider_d7_sign = d7.signs.get(decider, d7.house_sign(decider_d7_h) if decider_d7_h else child_sign)
    dec_dig = get_dignity(decider, decider_d7_sign) if decider_d7_sign else "neutral_sign"
    d9_dec = d9_enriched.get(decider, {}) if decider in d9_enriched else {}

    if dec_dig in ("exalted", "own_sign", "moolatrikona") or d9_dec.get("d9_dignity") in (
        "exalted", "own_sign", "moolatrikona",
    ):
        gender = _planet_gender(decider, dec_dig)
        method = "decider planet (strong in D9/D7)"
    else:
        gender = _sign_gender(decider_d7_sign)
        method = f"decider in {decider_d7_sign} (D7 sign gender)"

    if gender == "dual" or gender == "common":
        gender = _planet_gender(decider, dec_dig)
        method += " + planet gender tie-break"

    if gender == "common":
        gender = "dual"

    label = {"male": "boy", "female": "girl", "dual": "mixed / confirm at birth"}.get(gender, "mixed")
    return {
        "child_house": child_house,
        "child_lord": child_lord,
        "decider": decider,
        "decider_d7_sign": decider_d7_sign,
        "gender": gender,
        "label": label,
        "method": method,
    }


def _count_children(d7: VargaChart, d1_h5: list[str]) -> dict[str, Any]:
    seq = _child_houses(d7)
    count = 0
    stop = ""
    for h in seq:
        tenants = d7.tenants(h)
        lord = d7.house_lord(h)
        aff, ben = _affliction_count(tenants)
        active = bool(tenants) or ben > aff
        if not active and aff > 0 and ben == 0:
            break
        if "Ketu" in tenants and len(tenants) == 1:
            count += 1
            stop = f"Ketu alone in child-house {_house_word(h)} caps the line."
            break
        if "Ketu" in tenants and lord == "Ketu" and len(tenants) <= 2:
            count += 1
            stop = f"Ketu with child-house lord in {_house_word(h)} caps the line."
            break
        if active or d7.benefic_score(h) >= 0:
            count += 1
        if count >= 5:
            break

    d1_bonus = len(d1_h5) + sum(1 for p in d1_h5 if p in BENEFICS)
    if count == 0 and d1_bonus >= 1:
        count = 1

    if count >= 4:
        band = "several (three to five)"
    elif count == 3:
        band = "two to three"
    elif count == 2:
        band = "one or two"
    elif count == 1:
        band = "one primary child"
    else:
        band = "none or adoption path"

    return {"count_score": count, "band": band, "stop_reason": stop}


def _house_word(h: int) -> str:
    return f"{h}{'th' if h not in (1, 2, 3) else ['', 'st', 'nd', 'rd'][h]}"


def _child_health_score(d7: VargaChart, child_house: int) -> tuple[int, list[str]]:
    """6th and 8th from child house in D7 (rules14)."""
    ref = d7.house_sign(child_house)
    risk, facts = 0, []
    for offset, theme in ((5, "illness"), (7, "longevity / surgery risk")):
        sign = SIGNS[(SIGNS.index(ref) + offset) % 12]
        h = house_from_sign(sign, d7.lagna)
        tenants = d7.tenants(h)
        aff, ben = _affliction_count(tenants)
        if aff >= 2:
            risk += 35
            facts.append(f"Malefics on {_house_word(h)} from child axis ({theme})")
        elif aff == 1 and ben == 0:
            risk += 20
            facts.append(f"Strain on {_house_word(h)} from child axis")
        elif ben >= 1:
            facts.append(f"Benefic support on {_house_word(h)} from child axis")
    h6 = d7.benefic_score(6)
    h8 = d7.benefic_score(8)
    if h6 <= -1:
        risk += 15
    if h8 <= -1:
        risk += 20
        facts.append("D7 8th house stressed - miscarriage or child obstacle theme")
    if "Saturn" in d7.tenants(8) and "Rahu" in d7.tenants(8):
        risk += 15
        facts.append("Saturn and Rahu on D7 8th - chronic health caution for children")
    return min(100, risk), facts


def analyze_saptamsha_chart(pc: dict, extract_text: str = "", female: bool = False) -> dict[str, Any]:
    if not female:
        g = pc.get("meta", {}).get("gender", pc.get("gender"))
        if g is None and pc.get("raw_sections", {}).get("gender") is not None:
            g = pc["raw_sections"]["gender"]
        female = g == 1 or g == "female"
    d7 = _d7_from_pc(pc, extract_text)
    if not d7:
        return {"error": "Saptamsha (D7) not found — need divisional.D7 in precompute or Shodashvarga extract."}

    d9 = varga_from_divisional(pc, "D9")
    if not d9 and extract_text:
        d9 = parse_shodashvarga(extract_text).get("D9")
    lagna = pc.get("meta", {}).get("lagna_sign", "") or pc.get("lagna", {}).get("sign", "")
    hl = pc.get("house_lords", {})
    lord5_d1 = _hl(hl, 5).get("lord", "")
    lord5_d7 = d7.house_lord(5)
    lord9_d7 = d7.house_lord(9)
    d7_lagna_lord = d7.house_lord(1)

    d1_h5 = []
    if lagna:
        for pl, data in pc.get("planets", {}).items():
            if pl in GRAHAS and data.get("house") == 5:
                d1_h5.append(pl)

    d7_houses = _build_d7_houses(d7)
    lagna_t = d7.tenants(1)
    aff_l, ben_l = _affliction_count(lagna_t)
    d7_lagna_score = ben_l - aff_l

    denial_hits: list[str] = []
    if aff_l >= 2 and ben_l == 0:
        denial_hits.append("D7 lagna under malefic load with no benefic relief")
    ll = d7_lagna_lord
    ll_h = d7.planet_house(ll)
    ll_dig = get_dignity(ll, d7.signs.get(ll, ""))
    if ll_h in (6, 8, 12) and ll_dig in ("debilitated", "enemy_sign"):
        denial_hits.append("D7 lagna lord weak in trik/dusthana")
    if "Jupiter" in lagna_t and len(lagna_t) == 1 and ll == "Jupiter" and ll_dig == "moolatrikona":
        denial_hits.append("Jupiter alone in D7 lagna (moolatrikona) - desire for children may be absent")

    saturn_delay = d7.saturn_touches({1, 5, 9})
    saturn_relief = any(d7.benefic_score(h) > 0 for h in (1, 5, 9)) if saturn_delay else False

    beeja = _beeja_kshetra(pc, female, d7)

    child_seq = _child_houses(d7)
    first_h = child_seq[0]
    child_count = _count_children(d7, d1_h5)

    extras = analyze_saptamsha_extras(pc, d7, d9, female, denial_hits, first_h)

    d9_enriched: dict[str, dict] = {}
    for pl in GRAHAS:
        data = pc.get("planets", {}).get(pl, {})
        if not data.get("sign"):
            continue
        d1 = data["sign"]
        deg = float(data.get("degree_in_sign", 0))
        d9s = data.get("navamsha_sign") or navamsha_sign(d1, deg)
        d9_enriched[pl] = {
            "d9_sign": d9s,
            "d9_dignity": get_dignity(pl, d9s),
        }

    genders = []
    for i, h in enumerate(child_seq[: min(child_count["count_score"], 3) or 1]):
        genders.append({**_child_gender_goel(d7, d9, h, d9_enriched), "child_index": i + 1})

    h4 = d7.benefic_score(4)
    h10 = d7.benefic_score(10)
    jup_h = d7.planet_house("Jupiter")

    health_risk, health_facts = _child_health_score(d7, first_h)

    follows_parent = (
        ll_dig in ("exalted", "own_sign", "moolatrikona", "friendly_sign")
        and ll_h in (1, 4, 5, 7, 9, 10, 11)
    )

    payload = {
        "d7_lagna": d7.lagna,
        "d7_lagna_lord": d7_lagna_lord,
        "d7_lagna_score": d7_lagna_score,
        "d7_houses": d7_houses,
        "lord5_d1": lord5_d1,
        "lord5_d7": lord5_d7,
        "lord9_d7": lord9_d7,
        "d1_h5_planets": d1_h5,
        "denial_hits": denial_hits,
        "saturn_delay": saturn_delay,
        "saturn_delay_relief": saturn_relief,
        "beeja_kshetra": beeja,
        "child_count": child_count,
        "child_houses_seq": child_seq,
        "first_child_house": first_h,
        "child_genders": genders,
        "happiness_score": max(0, min(100, 50 + h4 * 20 + (10 if jup_h in (1, 5, 9) else 0))),
        "h4_score": h4,
        "h10_score": h10,
        "health_risk": health_risk,
        "health_facts": health_facts,
        "follows_parent_profession": follows_parent,
        "child_nature": D7_LAGNA_CHILD_NATURE.get(d7_lagna_lord, "mixed temperament"),
        "jupiter_d7_house": jup_h,
        "extras": extras,
    }

    payload["children_timing_detail"] = compute_children_timing(pc, payload)
    payload["coverage"] = _coverage_map(payload)
    return payload


def _coverage_map(analysis: dict) -> dict[str, tuple[str, str]]:
    timing = analysis.get("children_timing_detail", {})
    bc = analysis.get("beeja_kshetra", {})
    ex = analysis.get("extras", {})
    st = ex.get("santana_tithi", {})
    gc = ex.get("grandchildren", {})
    return {
        "d7_promise": (
            "checked",
            f"D7 lagna {analysis.get('d7_lagna')} score {analysis.get('d7_lagna_score')}",
        ),
        "saturn_delay": (
            "checked" if analysis.get("saturn_delay") else "partial",
            "Saturn on D7 lagna/5th/9th" if analysis.get("saturn_delay") else "No Saturn delay flag",
        ),
        "beeja_kshetra": (
            "checked" if bc.get("computed") else "partial",
            f"{bc.get('label', '')} D1/D9/D7 match {bc.get('match_count', 0)}/3" if bc.get("computed") else "BS/KS not computed",
        ),
        "santana_tithi": (
            "checked" if st.get("computed") else "partial",
            st.get("label", "") if st.get("computed") else "needs Sun/Moon",
        ),
        "child_count": ("checked", analysis.get("child_count", {}).get("band", "")),
        "child_gender": ("checked", "; ".join(g["label"] for g in analysis.get("child_genders", []))),
        "child_timing": (
            "checked" if timing.get("display_ages") else "partial",
            ", ".join(str(a) for a in timing.get("display_ages", [])),
        ),
        "happiness_children": ("checked", f"D7 4th score {analysis.get('h4_score')}"),
        "child_health": ("checked", f"risk {analysis.get('health_risk')}"),
        "child_profession": (
            "checked",
            "follows parent" if analysis.get("follows_parent_profession") else "own path likely",
        ),
        "grandchildren": ("checked", gc.get("level", "")),
        "twins": (
            "checked" if ex.get("twins", {}).get("likely") else "partial",
            f"score {ex.get('twins', {}).get('score', 0)}",
        ),
        "worthy_children": (
            "checked",
            "strong" if ex.get("worthy_child", {}).get("strong") else "moderate",
        ),
        "bond_strain": (
            "checked" if ex.get("bond_strain", {}).get("strained") else "partial",
            f"score {ex.get('bond_strain', {}).get('score', 0)}",
        ),
    }
