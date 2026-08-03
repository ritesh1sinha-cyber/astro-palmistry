#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Goel Saptamsha - Santana tithi, grandchildren, twins, yogas (rules14)."""
from __future__ import annotations

from typing import Any

from astro_precompute import get_dignity
from goel_saptamsha_coverage import SIGN_LORD
from goel_varga import SIGNS, house_from_lagna, navamsha_sign, saptamsha_sign
from vedic_varga_goel import BENEFICS, MALEFICS, VargaChart

GRAHAS = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}
DUAL_SIGNS = {"Gemini", "Pisces"}
FRUITFUL = {"Cancer", "Scorpio", "Pisces"}
SEMI_FRUITFUL = {"Taurus", "Libra", "Sagittarius", "Capricorn"}
RIKTA_TITHIS = {4, 9, 14}


def _abs_longitude(planets: dict, name: str) -> float | None:
    p = planets.get(name, {})
    sign = p.get("sign", "")
    if sign not in SIGNS:
        return None
    return SIGNS.index(sign) * 30.0 + float(p.get("degree_in_sign", 0))


def _is_odd_sign(sign: str) -> bool:
    return SIGNS.index(sign) % 2 == 0


def _is_even_sign(sign: str) -> bool:
    return SIGNS.index(sign) % 2 == 1


def _lon_to_sign(lon: float) -> str:
    return SIGNS[int(lon // 30) % 12]


def compute_santana_tithi(pc: dict) -> dict[str, Any]:
    """Jatakdesamarga: (Moon - Sun) * 5 mod 360 -> paksha + tithi."""
    planets = pc.get("planets", {})
    moon = _abs_longitude(planets, "Moon")
    sun = _abs_longitude(planets, "Sun")
    if moon is None or sun is None:
        return {"computed": False}

    diff = (moon - sun) % 360
    remainder = (diff * 5) % 360
    if remainder < 180:
        paksha = "shukla"
        tithi = min(15, int(remainder // 12) + 1)
    else:
        paksha = "krishna"
        tithi = min(15, int((remainder - 180) // 12) + 1)

    is_amavasya = remainder >= 348 or remainder < 12 and paksha == "krishna" and tithi >= 14
    is_rikta = tithi in RIKTA_TITHIS

    verdict = ""
    tone = "green"
    if is_amavasya or (paksha == "krishna" and tithi >= 13):
        verdict = "Progeny is very difficult; even adoption may not come easily."
        tone = "hard"
    elif paksha == "krishna" and tithi in (11, 12):
        verdict = "Conception may occur but a live birth is unlikely without strong remedial support."
        tone = "hard"
    elif paksha == "krishna" and 7 <= tithi <= 10:
        verdict = "Progeny may come after worship of Lord Subramanian (Murugan) and patience with delay."
        tone = "amber"
    elif paksha == "krishna" and tithi <= 4:
        verdict = "Progeny may come after second marriage themes or feeding Brahmins (classical Santana rule)."
        tone = "amber"
    elif paksha == "krishna":
        verdict = "Krishna paksha Santana tithi - getting children needs more effort than Shukla paksha charts."
        tone = "amber"
    elif paksha == "shukla" and tithi <= 5:
        verdict = "Children are promised but arrive slowly and gradually."
        tone = "green"
    elif paksha == "shukla" and tithi >= 10:
        verdict = "Children tend to come relatively quickly once dasha and saptamsha cooperate."
        tone = "green"
    else:
        verdict = "Shukla paksha Santana tithi supports progeny at a normal pace."
        tone = "green"

    if is_rikta:
        verdict += " Rikta tithi (4th, 9th, or 14th) is not conducive - pair with sphuta and D7 before a firm yes."
        tone = "amber" if tone == "green" else tone

    return {
        "computed": True,
        "paksha": paksha,
        "tithi": tithi,
        "remainder_deg": round(remainder, 2),
        "rikta": is_rikta,
        "amavasya": is_amavasya,
        "verdict": verdict,
        "tone": tone,
        "label": f"{paksha} paksha, tithi {tithi}",
    }


def _sphuta_full(pc: dict, female: bool, d7: VargaChart | None) -> dict[str, Any]:
    planets = pc.get("planets", {})
    j = _abs_longitude(planets, "Jupiter")
    if j is None:
        return {"computed": False}
    if female:
        m, ma = _abs_longitude(planets, "Moon"), _abs_longitude(planets, "Mars")
        if m is None or ma is None:
            return {"computed": False}
        lon = (j + m + ma) % 360
        label, need_even = "Kshetra Sphuta (KS)", True
    else:
        v, s = _abs_longitude(planets, "Venus"), _abs_longitude(planets, "Sun")
        if v is None or s is None:
            return {"computed": False}
        lon = (j + v + s) % 360
        label, need_even = "Beeja Sphuta (BS)", False

    deg = lon % 30
    d1_sign = _lon_to_sign(lon)
    d9_sign = navamsha_sign(d1_sign, deg)
    d7_sign = saptamsha_sign(d1_sign, deg)
    if d7:
        d7_house = house_from_lagna(d7_sign, d7.lagna) if d7.lagna in SIGNS else 0
    else:
        d7_house = 0

    checks = {
        "d1": _is_even_sign(d1_sign) if need_even else _is_odd_sign(d1_sign),
        "d9": _is_even_sign(d9_sign) if need_even else _is_odd_sign(d9_sign),
        "d7": _is_even_sign(d7_sign) if need_even else _is_odd_sign(d7_sign),
    }
    match_count = sum(1 for v in checks.values() if v)
    in_trik = d7_house in (6, 8, 12) if d7_house else False
    in_kendra_trikona = d7_house in (1, 4, 5, 7, 9, 10) if d7_house else False

    return {
        "computed": True,
        "label": label,
        "d1_sign": d1_sign,
        "d9_sign": d9_sign,
        "d7_sign": d7_sign,
        "d7_house": d7_house,
        "checks": checks,
        "match_count": match_count,
        "promise_ok": match_count >= 2,
        "in_trik": in_trik,
        "in_kendra_trikona": in_kendra_trikona,
        "dual_sign": d1_sign in DUAL_SIGNS,
    }


def analyze_grandchildren(d7: VargaChart) -> dict[str, Any]:
    h9 = d7.benefic_score(9)
    tenants = d7.tenants(9)
    lord9 = d7.house_lord(9)
    lord9_h = d7.planet_house(lord9)
    jup9 = d7.planet_house("Jupiter") == 9

    if h9 >= 1 and jup9:
        level = "strong"
        text = "Grandchildren are a live theme - ninth house of saptamsha is supported and Jupiter sits there."
    elif h9 >= 1:
        level = "good"
        text = "Fortune through grandchildren is likely - the saptamsha ninth house carries benefic promise."
    elif h9 <= -1:
        level = "weak"
        text = "Grandchildren may be fewer, late, or emotionally distant - ninth house of saptamsha is stressed."
    else:
        level = "mixed"
        text = "Grandchildren are possible but not a dominant life theme - ninth house is neutral."

    deity = lord9
    return {
        "score": h9,
        "level": level,
        "text": text,
        "tenants": tenants,
        "lord9": lord9,
        "lord9_house": lord9_h,
        "jupiter_in_9": jup9,
        "worship_lord": deity,
    }


def analyze_twins(
    pc: dict, d7: VargaChart, d9: VargaChart | None, sphuta: dict,
) -> dict[str, Any]:
    planets = pc.get("planets", {})
    lagna = pc.get("meta", {}).get("lagna_sign", "") or pc.get("lagna", {}).get("sign", "")
    moon_sign = planets.get("Moon", {}).get("sign", "")
    hits: list[str] = []
    score = 0

    if lagna in DUAL_SIGNS and planets.get("Mercury", {}).get("sign") == lagna:
        hits.append("Mercury in dual sign on birth lagna")
        score += 2
    if lagna in DUAL_SIGNS or moon_sign in DUAL_SIGNS:
        if "Mercury" in {planets.get(p, {}).get("sign") for p in ("Mercury",)}:
            pass
        if lagna in DUAL_SIGNS and moon_sign in DUAL_SIGNS:
            hits.append("Birth lagna and Moon in dual or even signs")
            score += 1
    if planets.get("Mercury", {}).get("house") == 10:
        hits.append("Mercury in tenth house (classical twins indicator)")
        score += 2
    if sphuta.get("dual_sign"):
        hits.append("Beeja/Kshetra sphuta in dual sign")
        score += 2
    if d7 and SIGN_LORD.get(d7.lagna) in ("Mercury", "Jupiter"):
        ll_sign = d7.signs.get(d7.house_lord(1), "")
        if ll_sign in DUAL_SIGNS:
            hits.append("Saptamsha lagna lord in dual sign")
            score += 1
    if d9 and d7 and d7.benefic_score(1) >= 0:
        trines = [d7.house_sign(h) for h in (1, 5, 9)]
        if any(s in FRUITFUL | SEMI_FRUITFUL for s in trines):
            hits.append("Fruitful saptamsha trines with promise on lagna")
            score += 1
    for p in ("Rahu", "Ketu"):
        if sphuta.get("computed") and sphuta.get("d1_sign"):
            # sphuta on axis with nodes in D1
            ps = planets.get(p, {}).get("sign", "")
            if ps and sphuta["d1_sign"] == ps:
                hits.append(f"Sphuta sign aligned with {p} axis")
                score += 1

    likely = score >= 3
    return {"score": score, "hits": hits, "likely": likely}


def analyze_bahu_putra(pc: dict, d9: VargaChart | None, sphuta: dict) -> dict[str, Any]:
    planets = pc.get("planets", {})
    hl = pc.get("house_lords", {})
    l7 = hl.get(7, hl.get("7", {})).get("lord", "")
    hits: list[str] = []

    for pl, data in planets.items():
        d9s = data.get("navamsha_sign") or navamsha_sign(
            data.get("sign", ""), float(data.get("degree_in_sign", 0)),
        )
        if pl in ("Sun", "Jupiter") and d9s in ("Sagittarius", "Gemini"):
            hits.append(f"{pl} in Sagittarius/Gemini navamsha")

    if d9 and d9.planet_house("Rahu") == 5:
        rahu_sign = d9.signs.get("Rahu", "")
        if rahu_sign and rahu_sign not in ("Capricorn", "Aquarius"):
            hits.append("Rahu in fifth of navamsha (not in Saturn sign)")

    if sphuta.get("dual_sign"):
        hits.append("Sphuta in dual sign")

    l1 = hl.get(1, hl.get("1", {})).get("lord", "")
    l2 = hl.get(2, hl.get("2", {})).get("lord", "")
    l5 = hl.get(5, hl.get("5", {})).get("lord", "")
    if l7 and l7 in (l1, l2, l5):
        hits.append("Seventh lord linked to first/second/fifth lords")

    return {"hits": hits, "active": len(hits) >= 2}


def analyze_kakvandhya(pc: dict, d7: VargaChart) -> dict[str, Any]:
    planets = pc.get("planets", {})
    hl = pc.get("house_lords", {})
    lagna = pc.get("meta", {}).get("lagna_sign", "")
    l1 = hl.get(1, hl.get("1", {})).get("lord", "")
    l5 = hl.get(5, hl.get("5", {})).get("lord", "")
    l5_data = planets.get(l5, {})
    l5_h = l5_data.get("house", 0)
    l5_dig = get_dignity(l5, l5_data.get("sign", "")) if l5 else ""
    hits: list[str] = []

    if l5_h == 6 and l1 == "Mars":
        hits.append("Fifth lord in sixth and lagna lord is Mars")
    h5_d1 = [p for p, d in planets.items() if d.get("house") == 5]
    if l5_dig == "debilitated" and "Saturn" in h5_d1 and "Mercury" in h5_d1:
        hits.append("Debilitated fifth lord with Saturn and Mercury in birth fifth")
    if l5_dig == "debilitated" and l5_h in (6, 8, 12) and "Mercury" in h5_d1:
        hits.append("Debilitated fifth lord in trik with Mercury in fifth")

    return {"hits": hits, "active": len(hits) >= 1}


def analyze_bond_strain(pc: dict, d7: VargaChart) -> dict[str, Any]:
    planets = pc.get("planets", {})
    hl = pc.get("house_lords", {})
    l5 = hl.get(5, hl.get("5", {})).get("lord", "")
    l5_h = planets.get(l5, {}).get("house", 0)
    l6 = hl.get(6, hl.get("6", {})).get("lord", "")
    hits: list[str] = []
    score = 0

    if l5_h in (6, 12):
        hits.append(f"Birth fifth lord {l5} in {l5_h}th house - child may behave like an enemy at times")
        score += 2
    if l6 and d7.planet_house(l6) in (1, 5):
        hits.append("Sixth lord touches saptamsha lagna or fifth")
        score += 1
    if d7.benefic_score(4) <= -1 and d7.benefic_score(10) <= -1:
        hits.append("Both happiness (4th) and care (10th) axes stressed in saptamsha")
        score += 2
    jup_h = d7.planet_house("Jupiter")
    if jup_h in (6, 8, 12):
        hits.append("Jupiter karaka in dusthana of saptamsha - devotion needs conscious work")
        score += 1

    return {"hits": hits, "score": score, "strained": score >= 2}


def analyze_adoption_path(d7: VargaChart, denial_hits: list[str]) -> dict[str, Any]:
    lagna_ben = d7.benefic_score(1) >= 1
    if denial_hits and lagna_ben:
        return {
            "active": True,
            "text": "Biological denial is flagged, but benefic support on saptamsha lagna keeps the door open for adoption or a child through non-biological means.",
        }
    if denial_hits:
        return {"active": False, "text": ""}
    return {"active": False, "text": ""}


def analyze_d7_house_extras(d7: VargaChart) -> dict[str, Any]:
    h2, h11, h12 = d7.benefic_score(2), d7.benefic_score(11), d7.benefic_score(12)
    return {
        "values_inheritance": {
            "score": h2,
            "text": (
                "Values and inheritance pass cleanly to children."
                if h2 >= 1
                else "Second house of saptamsha is stressed - family values and wealth transfer need deliberate planning."
                if h2 <= -1
                else "Mixed sanskar and inheritance theme - teach by example."
            ),
        },
        "gains_from_children": {
            "score": h11,
            "text": (
                "Eleventh house supported - parental hopes and gains through children are likely fulfilled."
                if h11 >= 1
                else "Gains from children may disappoint unless expectations stay realistic."
                if h11 <= -1
                else "Moderate gains and friendship among children is possible."
            ),
        },
        "upbringing_expense": {
            "score": h12,
            "text": (
                "Twelfth house is calm - upbringing expenses stay manageable."
                if h12 >= 0
                else "Twelfth house stressed - heavy expenses or private worries around raising children."
            ),
        },
    }


def analyze_worthy_child(d7: VargaChart, first_child_house: int) -> dict[str, Any]:
    """Raj yoga hint from first child house as lagna (Goel Ch.5)."""
    ref_sign = d7.house_sign(first_child_house)
    ref_idx = SIGNS.index(ref_sign)
    kendra_from_child = [SIGNS[(ref_idx + o) % 12] for o in (0, 3, 6, 9)]
    benefic_kendra = 0
    for sign in kendra_from_child:
        for p in GRAHAS:
            if d7.signs.get(p) == sign and p in BENEFICS:
                benefic_kendra += 1
    child_5th_sign = SIGNS[(ref_idx + 4) % 12]
    jup_in_child_5th = d7.signs.get("Jupiter") == child_5th_sign
    strong = benefic_kendra >= 2 or jup_in_child_5th
    return {
        "strong": strong,
        "text": (
            "At least one child carries raj-yoga potential from their saptamsha house - worthy, status-bearing progeny is possible."
            if strong
            else "Worthy children come through effort and upbringing; raj-yoga from the first child-house is not dominant."
        ),
    }


def analyze_saptamsha_extras(
    pc: dict, d7: VargaChart, d9: VargaChart | None, female: bool,
    denial_hits: list[str], first_child_h: int,
) -> dict[str, Any]:
    sphuta = _sphuta_full(pc, female, d7)
    return {
        "santana_tithi": compute_santana_tithi(pc),
        "sphuta_full": sphuta,
        "grandchildren": analyze_grandchildren(d7),
        "twins": analyze_twins(pc, d7, d9, sphuta),
        "bahu_putra": analyze_bahu_putra(pc, d9, sphuta),
        "kakvandhya": analyze_kakvandhya(pc, d7),
        "bond_strain": analyze_bond_strain(pc, d7),
        "adoption": analyze_adoption_path(d7, denial_hits),
        "house_extras": analyze_d7_house_extras(d7),
        "worthy_child": analyze_worthy_child(d7, first_child_h),
    }
