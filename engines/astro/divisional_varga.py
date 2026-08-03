#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parashari divisional chart helpers (D2 Hora = Cancer/Leo only)."""
from __future__ import annotations

from typing import Any

from astro_precompute import SIGNS, SIGN_LORDS, get_dignity, house_from_lagna, house_sign


def _is_odd_sign(sign: str) -> bool:
    return SIGNS.index(sign) % 2 == 0  # Aries index 0 = odd sign


def parashari_hora_sign(d1_sign: str, degree_in_sign: float) -> str:
    """Map D1 longitude to Parashari hora sign (Leo = Sun hora, Cancer = Moon hora)."""
    first_half = float(degree_in_sign) < 15.0
    if _is_odd_sign(d1_sign):
        return "Leo" if first_half else "Cancer"
    return "Cancer" if first_half else "Leo"


def hora_lord(sign: str) -> str:
    return "Sun" if sign == "Leo" else "Moon"


def hora_part_label(d1_sign: str, degree_in_sign: float) -> str:
    first = float(degree_in_sign) < 15.0
    return "first 15° (stronger hora slice)" if first else "second 15° (weaker hora slice)"


def hora_type_label(d2_sign: str) -> str:
    if d2_sign == "Leo":
        return "Sun hora — wealth through self-effort (Devtas)"
    return "Moon hora — wealth through forefathers and blessings (Pitris)"


# ─────────────────────────── D3 Drekkana ─────────────────────────────────

# Parashari Drekkana lookup table  (sign_idx → [decanate0, decanate1, decanate2])
# First decanate = same sign, second = 5th from sign, third = 9th from sign.
def parashari_d3_sign(d1_sign: str, degree_in_sign: float) -> str:
    """Return D3 sign using Parashari (same, +4, +8) decanate rule."""
    si = SIGNS.index(d1_sign)
    deg = float(degree_in_sign)
    if deg < 10.0:
        offset = 0
    elif deg < 20.0:
        offset = 4
    else:
        offset = 8
    return SIGNS[(si + offset) % 12]


def d3_decanate_index(degree_in_sign: float) -> int:
    if float(degree_in_sign) < 10:
        return 0
    if float(degree_in_sign) < 20:
        return 1
    return 2


def sign_quality(sign: str) -> str:
    movable = {"Aries", "Cancer", "Libra", "Capricorn"}
    fixed = {"Taurus", "Leo", "Scorpio", "Aquarius"}
    if sign in movable:
        return "movable"
    if sign in fixed:
        return "fixed"
    return "dual"


def d3_guna_key(d1_sign: str, degree_in_sign: float) -> str:
    quality = sign_quality(d1_sign)
    dec = d3_decanate_index(degree_in_sign)
    names = ["first", "second", "third"]
    return f"{quality}_{names[dec]}"


def build_parashari_d3_chart(pc: dict) -> dict[str, Any]:
    """Build D3 from D1 longitudes using Parashari Drekkana (same/5th/9th sign)."""
    meta = pc.get("meta", {})
    d1_lagna = meta.get("lagna_sign") or pc.get("lagna", {}).get("sign", "")
    lagna_deg = float(meta.get("lagna_degree") or pc.get("lagna", {}).get("degree_in_sign") or 0)
    d3_lagna = parashari_d3_sign(d1_lagna, lagna_deg)

    # 22nd drekkana: the sign occupying the 8th house at the same degrees as lagna
    # (the decanate at the same degree-within-sign as lagna, but in the 8th-house sign)
    lagna_si = SIGNS.index(d1_lagna)
    h8_sign = SIGNS[(lagna_si + 7) % 12]
    d22_sign = parashari_d3_sign(h8_sign, lagna_deg)

    bodies: dict[str, dict[str, Any]] = {}
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        pl = pc.get("planets", {}).get(name, {})
        d1_sign = pl.get("sign", "")
        deg = float(pl.get("degree_in_sign") or 0)
        if not d1_sign:
            continue
        d3_sign = parashari_d3_sign(d1_sign, deg)
        guna_key = d3_guna_key(d1_sign, deg)
        bodies[name] = {
            "d1_sign": d1_sign,
            "d1_degree": deg,
            "sign": d3_sign,
            "house": house_from_lagna(d3_sign, d3_lagna),
            "decanate": d3_decanate_index(deg) + 1,
            "guna_key": guna_key,
        }

    houses: dict[int, dict[str, Any]] = {}
    for h in range(1, 13):
        hs = house_sign(h, d3_lagna)
        lord = SIGN_LORDS[hs]
        tenants = [n for n, b in bodies.items() if b["sign"] == hs]
        houses[h] = {"sign": hs, "lord": lord, "tenants": tenants}

    ll = SIGN_LORDS[d3_lagna]
    ll_d1 = pc.get("planets", {}).get(ll, {})
    ll_dig = get_dignity(ll, ll_d1.get("sign", "")) if ll_d1.get("sign") else "unknown"
    ll_v_sign = (bodies.get(ll) or {}).get("sign", "")
    ll_v_house = (bodies.get(ll) or {}).get("house")
    ll_v_dig = get_dignity(ll, ll_v_sign) if ll_v_sign else "unknown"

    # D3 also uses precomputed divisional if available
    d3_precomputed = (pc.get("divisional") or {}).get("D3") or {}

    return {
        "method": "Parashari Drekkana (same / 5th / 9th sign)",
        "d1_lagna": d1_lagna,
        "d1_lagna_degree": lagna_deg,
        "lagna": d3_lagna,
        "lagna_lord": ll,
        "lagna_lord_d1_sign": ll_d1.get("sign", ""),
        "lagna_lord_d1_house": ll_d1.get("house"),
        "lagna_lord_dignity_d1": ll_dig,
        "lagna_lord_varga_sign": ll_v_sign,
        "lagna_lord_varga_house": ll_v_house,
        "lagna_lord_dignity_varga": ll_v_dig,
        "d22_sign": d22_sign,
        "planets": bodies,
        "houses": houses,
        "precomputed_lagna": d3_precomputed.get("Lagna", ""),
    }


# ─────────────────────────── D7 Saptamsha ────────────────────────────────

_ODD_SIGNS = {"Aries", "Gemini", "Leo", "Libra", "Sagittarius", "Aquarius"}


def d7_part_index(degree_in_sign: float) -> int:
    """0-based index 0–6 for the 7 parts (each 4°17' ≈ 4.2857°)."""
    return min(int(float(degree_in_sign) / (30 / 7)), 6)


def parashari_d7_sign(d1_sign: str, degree_in_sign: float) -> str:
    """Return D7 sign: odd sign → count from d1_sign forward; even → from 7th sign forward."""
    si = SIGNS.index(d1_sign)
    part = d7_part_index(degree_in_sign)
    start = si if d1_sign in _ODD_SIGNS else (si + 6) % 12
    return SIGNS[(start + part) % 12]


D7_PART_LABELS: dict[int, str] = {
    0: "Kshar",
    1: "Kshira",
    2: "Dadhi",
    3: "Ajyam",
    4: "Ikshu",
    5: "Madhya",
    6: "Suddha Jal",
}


def build_parashari_d7_chart(pc: dict) -> dict[str, Any]:
    """Build D7 from D1 longitudes using Parashari Saptamsha."""
    meta = pc.get("meta", {})
    d1_lagna = meta.get("lagna_sign") or pc.get("lagna", {}).get("sign", "")
    lagna_deg = float(meta.get("lagna_degree") or pc.get("lagna", {}).get("degree_in_sign") or 0)
    d7_lagna = parashari_d7_sign(d1_lagna, lagna_deg)

    # prefer PyJHora precomputed D7 lagna if available
    pj_d7 = (pc.get("divisional") or {}).get("D7") or {}
    if pj_d7.get("Lagna"):
        d7_lagna = pj_d7["Lagna"]

    bodies: dict[str, dict[str, Any]] = {}
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        # prefer precomputed PyJHora position
        pj_sign = pj_d7.get(name, "")
        pl = pc.get("planets", {}).get(name, {})
        d1_sign = pl.get("sign", "")
        deg = float(pl.get("degree_in_sign") or 0)
        if not d1_sign:
            continue
        d7_sign = pj_sign if pj_sign else parashari_d7_sign(d1_sign, deg)
        part_idx = d7_part_index(deg)
        bodies[name] = {
            "d1_sign": d1_sign,
            "d1_degree": deg,
            "sign": d7_sign,
            "house": house_from_lagna(d7_sign, d7_lagna),
            "part_label": D7_PART_LABELS.get(part_idx, ""),
        }

    houses: dict[int, dict[str, Any]] = {}
    for h in range(1, 13):
        hs = house_sign(h, d7_lagna)
        lord = SIGN_LORDS[hs]
        tenants = [n for n, b in bodies.items() if b["sign"] == hs]
        houses[h] = {"sign": hs, "lord": lord, "tenants": tenants}

    ll = SIGN_LORDS[d7_lagna]
    ll_d1 = pc.get("planets", {}).get(ll, {})
    ll_dig = get_dignity(ll, ll_d1.get("sign", "")) if ll_d1.get("sign") else "unknown"
    ll_d7_sign = (bodies.get(ll) or {}).get("sign", "")
    ll_d7_house = (bodies.get(ll) or {}).get("house")
    ll_d7_dig = get_dignity(ll, ll_d7_sign) if ll_d7_sign else "unknown"

    jup = bodies.get("Jupiter") or {}

    return {
        "method": "Parashari Saptamsha",
        "d1_lagna": d1_lagna,
        "d1_lagna_degree": lagna_deg,
        "lagna": d7_lagna,
        "lagna_lord": ll,
        "lagna_lord_d1_sign": ll_d1.get("sign", ""),
        "lagna_lord_d1_house": ll_d1.get("house"),
        "lagna_lord_dignity_d1": ll_dig,
        "lagna_lord_d7_sign": ll_d7_sign,
        "lagna_lord_d7_house": ll_d7_house,
        "lagna_lord_dignity_d7": ll_d7_dig,
        "lagna_lord_varga_sign": ll_d7_sign,
        "lagna_lord_varga_house": ll_d7_house,
        "lagna_lord_dignity_varga": ll_d7_dig,
        "jupiter_d7_house": jup.get("house"),
        "jupiter_d7_sign": jup.get("sign", ""),
        "planets": bodies,
        "houses": houses,
    }


# ─────────────────────────── D4 Chaturthamsha ────────────────────────────

D4_PART_LABELS: dict[int, str] = {
    1: "Sanaka",
    2: "Sananda",
    3: "Sanatana Kumar",
    4: "Sanatana",
}


def d4_part_index(degree_in_sign: float) -> int:
    deg = float(degree_in_sign)
    if deg < 7.5:
        return 0
    if deg < 15.0:
        return 1
    if deg < 22.5:
        return 2
    return 3


def parashari_d4_sign(d1_sign: str, degree_in_sign: float) -> str:
    """Return D4 sign: same / +3 (4th) / +6 (7th) / +9 (10th) from D1 sign."""
    si = SIGNS.index(d1_sign)
    deg = float(degree_in_sign)
    if deg < 7.5:
        offset = 0
    elif deg < 15.0:
        offset = 3
    elif deg < 22.5:
        offset = 6
    else:
        offset = 9
    return SIGNS[(si + offset) % 12]


def build_parashari_d4_chart(pc: dict) -> dict[str, Any]:
    """Build D4 from D1 longitudes using Parashari Chaturthamsha."""
    meta = pc.get("meta", {})
    d1_lagna = meta.get("lagna_sign") or pc.get("lagna", {}).get("sign", "")
    lagna_deg = float(meta.get("lagna_degree") or pc.get("lagna", {}).get("degree_in_sign") or 0)
    d4_lagna = parashari_d4_sign(d1_lagna, lagna_deg)

    bodies: dict[str, dict[str, Any]] = {}
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        pl = pc.get("planets", {}).get(name, {})
        d1_sign = pl.get("sign", "")
        deg = float(pl.get("degree_in_sign") or 0)
        if not d1_sign:
            continue
        part = d4_part_index(deg) + 1
        d4_sign = parashari_d4_sign(d1_sign, deg)
        bodies[name] = {
            "d1_sign": d1_sign,
            "d1_degree": deg,
            "sign": d4_sign,
            "house": house_from_lagna(d4_sign, d4_lagna),
            "part": part,
            "part_deity": D4_PART_LABELS.get(part, ""),
        }

    houses: dict[int, dict[str, Any]] = {}
    for h in range(1, 13):
        hs = house_sign(h, d4_lagna)
        lord = SIGN_LORDS[hs]
        tenants = [n for n, b in bodies.items() if b["sign"] == hs]
        houses[h] = {"sign": hs, "lord": lord, "tenants": tenants}

    ll = SIGN_LORDS[d4_lagna]
    ll_d1 = pc.get("planets", {}).get(ll, {})
    ll_dig = get_dignity(ll, ll_d1.get("sign", "")) if ll_d1.get("sign") else "unknown"
    ll_v_sign = (bodies.get(ll) or {}).get("sign", "")
    ll_v_house = (bodies.get(ll) or {}).get("house")
    ll_v_dig = get_dignity(ll, ll_v_sign) if ll_v_sign else "unknown"
    lagna_part = d4_part_index(lagna_deg) + 1

    d4_precomputed = (pc.get("divisional") or {}).get("D4") or {}

    return {
        "method": "Parashari Chaturthamsha (same / 4th / 7th / 10th sign)",
        "d1_lagna": d1_lagna,
        "d1_lagna_degree": lagna_deg,
        "lagna": d4_lagna,
        "lagna_lord": ll,
        "lagna_part": lagna_part,
        "lagna_part_deity": D4_PART_LABELS.get(lagna_part, ""),
        "lagna_lord_d1_sign": ll_d1.get("sign", ""),
        "lagna_lord_d1_house": ll_d1.get("house"),
        "lagna_lord_dignity_d1": ll_dig,
        "lagna_lord_varga_sign": ll_v_sign,
        "lagna_lord_varga_house": ll_v_house,
        "lagna_lord_dignity_varga": ll_v_dig,
        "planets": bodies,
        "houses": houses,
        "precomputed_lagna": d4_precomputed.get("Lagna", ""),
    }


def build_parashari_d2_chart(pc: dict) -> dict[str, Any]:
    """Build D2 from D1 longitudes using Parashari Cancer/Leo hora rules."""
    meta = pc.get("meta", {})
    d1_lagna = meta.get("lagna_sign") or pc.get("lagna", {}).get("sign", "")
    lagna_deg = float(meta.get("lagna_degree") or pc.get("lagna", {}).get("degree_in_sign") or 0)
    d2_lagna = parashari_hora_sign(d1_lagna, lagna_deg)

    bodies: dict[str, dict[str, Any]] = {}
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        pl = pc.get("planets", {}).get(name, {})
        d1_sign = pl.get("sign", "")
        deg = float(pl.get("degree_in_sign") or 0)
        if not d1_sign:
            continue
        d2_sign = parashari_hora_sign(d1_sign, deg)
        bodies[name] = {
            "d1_sign": d1_sign,
            "d1_degree": deg,
            "sign": d2_sign,
            "house": house_from_lagna(d2_sign, d2_lagna),
            "hora": hora_lord(d2_sign),
            "hora_part": hora_part_label(d1_sign, deg),
        }

    houses: dict[int, dict[str, Any]] = {}
    for h in range(1, 13):
        hs = house_sign(h, d2_lagna)
        lord = SIGN_LORDS[hs]
        tenants = [n for n, b in bodies.items() if b["sign"] == hs]
        houses[h] = {"sign": hs, "lord": lord, "tenants": tenants}

    sun_hora = [n for n, b in bodies.items() if b["sign"] == "Leo"]
    moon_hora = [n for n, b in bodies.items() if b["sign"] == "Cancer"]

    ll = hora_lord(d2_lagna)
    ll_d1 = pc.get("planets", {}).get(ll, {})
    ll_dig = get_dignity(ll, ll_d1.get("sign", "")) if ll_d1.get("sign") else "unknown"
    ll_v_sign = (bodies.get(ll) or {}).get("sign", "")
    ll_v_house = (bodies.get(ll) or {}).get("house")
    ll_v_dig = get_dignity(ll, ll_v_sign) if ll_v_sign else "unknown"

    return {
        "method": "Parashari Hora (Cancer / Leo)",
        "d1_lagna": d1_lagna,
        "d1_lagna_degree": lagna_deg,
        "lagna": d2_lagna,
        "lagna_lord": ll,
        "lagna_lord_d1_sign": ll_d1.get("sign", ""),
        "lagna_lord_d1_house": ll_d1.get("house"),
        "lagna_lord_dignity_d1": ll_dig,
        "lagna_lord_varga_sign": ll_v_sign,
        "lagna_lord_varga_house": ll_v_house,
        "lagna_lord_dignity_varga": ll_v_dig,
        "lagna_hora_type": hora_type_label(d2_lagna),
        "planets": bodies,
        "houses": houses,
        "sun_hora_planets": sun_hora,
        "moon_hora_planets": moon_hora,
    }


# ─────────────────────────── D9 Navamsha ─────────────────────────────────

def build_varga_chart_from_pc(pc: dict, varga: str) -> dict[str, Any]:
    """Generic divisional chart from PyJHora precomputed positions (pc['divisional'][varga]).

    Produces the same chart-dict shape as build_parashari_d9_chart so the shared
    house-examination, Goel inspection and rule-inspection helpers all work.
    Used for the higher vargas (D10, D12, D16, D20, D24, D27, D30, D40, D45, D60).
    """
    varga = varga.upper()
    div = (pc.get("divisional") or {}).get(varga) or {}
    meta = pc.get("meta", {})
    d1_lagna = meta.get("lagna_sign") or pc.get("lagna", {}).get("sign", "")
    v_lagna = div.get("Lagna") or d1_lagna

    bodies: dict[str, dict[str, Any]] = {}
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        pl = pc.get("planets", {}).get(name, {})
        d1_sign = pl.get("sign", "")
        if not d1_sign:
            continue
        deg = float(pl.get("degree_in_sign") or 0)
        v_sign = div.get(name) or d1_sign
        bodies[name] = {
            "d1_sign": d1_sign,
            "d1_degree": deg,
            "sign": v_sign,
            "house": house_from_lagna(v_sign, v_lagna),
            "vargottama": d1_sign == v_sign,
            "varga_dignity": get_dignity(name, v_sign),
        }

    houses: dict[int, dict[str, Any]] = {}
    for h in range(1, 13):
        hs = house_sign(h, v_lagna)
        lord = SIGN_LORDS[hs]
        tenants = [n for n, b in bodies.items() if b["sign"] == hs]
        houses[h] = {"sign": hs, "lord": lord, "tenants": tenants}

    ll = SIGN_LORDS[v_lagna]
    ll_d1 = pc.get("planets", {}).get(ll, {})
    ll_dig_d1 = get_dignity(ll, ll_d1.get("sign", "")) if ll_d1.get("sign") else "unknown"
    ll_v_sign = (bodies.get(ll) or {}).get("sign", "")
    ll_v_house = (bodies.get(ll) or {}).get("house")
    ll_v_dig = get_dignity(ll, ll_v_sign) if ll_v_sign else "unknown"

    return {
        "method": f"{varga} from PyJHora divisional positions",
        "varga": varga,
        "d1_lagna": d1_lagna,
        "lagna": v_lagna,
        "lagna_lord": ll,
        "vargottama_lagna": v_lagna == d1_lagna,
        "lagna_lord_d1_sign": ll_d1.get("sign", ""),
        "lagna_lord_d1_house": ll_d1.get("house"),
        "lagna_lord_dignity_d1": ll_dig_d1,
        "lagna_lord_varga_sign": ll_v_sign,
        "lagna_lord_varga_house": ll_v_house,
        "lagna_lord_dignity_varga": ll_v_dig,
        "planets": bodies,
        "houses": houses,
        "precomputed_lagna": div.get("Lagna", ""),
    }


def build_parashari_d9_chart(pc: dict) -> dict[str, Any]:
    """Build D9 from D1 longitudes using Parashari navamsha (modality method)."""
    from goel_varga import (
        is_pushkar_navamsha,
        is_vargottama,
        is_vish_navamsha,
        navamsha_part,
        navamsha_sign,
    )

    meta = pc.get("meta", {})
    d1_lagna = meta.get("lagna_sign") or pc.get("lagna", {}).get("sign", "")
    lagna_deg = float(meta.get("lagna_degree") or pc.get("lagna", {}).get("degree_in_sign") or 0)
    pj_d9 = (pc.get("divisional") or {}).get("D9") or {}
    d9_lagna = pj_d9.get("Lagna") or navamsha_sign(d1_lagna, lagna_deg)

    bodies: dict[str, dict[str, Any]] = {}
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        pl = pc.get("planets", {}).get(name, {})
        d1_sign = pl.get("sign", "")
        deg = float(pl.get("degree_in_sign") or 0)
        if not d1_sign:
            continue
        pj_sign = pj_d9.get(name, "")
        d9_sign = pj_sign if pj_sign else navamsha_sign(d1_sign, deg)
        part = navamsha_part(d1_sign, deg)
        bodies[name] = {
            "d1_sign": d1_sign,
            "d1_degree": deg,
            "sign": d9_sign,
            "house": house_from_lagna(d9_sign, d9_lagna),
            "navamsha_part": part,
            "vargottama": is_vargottama(d1_sign, d9_sign),
            "pushkar": is_pushkar_navamsha(d1_sign, deg),
            "vish": is_vish_navamsha(d1_sign, deg),
            "d9_dignity": get_dignity(name, d9_sign),
        }

    houses: dict[int, dict[str, Any]] = {}
    for h in range(1, 13):
        hs = house_sign(h, d9_lagna)
        lord = SIGN_LORDS[hs]
        tenants = [n for n, b in bodies.items() if b["sign"] == hs]
        houses[h] = {"sign": hs, "lord": lord, "tenants": tenants}

    ll = SIGN_LORDS[d9_lagna]
    ll_d1 = pc.get("planets", {}).get(ll, {})
    ll_dig = get_dignity(ll, ll_d1.get("sign", "")) if ll_d1.get("sign") else "unknown"
    ll_v_sign = (bodies.get(ll) or {}).get("sign", "")
    ll_v_house = (bodies.get(ll) or {}).get("house")
    ll_v_dig = get_dignity(ll, ll_v_sign) if ll_v_sign else "unknown"
    vargottama_lagna = d9_lagna == d1_lagna

    venus = bodies.get("Venus") or {}
    jupiter = bodies.get("Jupiter") or {}

    return {
        "method": "Parashari Navamsha (movable/fixed/dual method)",
        "d1_lagna": d1_lagna,
        "d1_lagna_degree": lagna_deg,
        "lagna": d9_lagna,
        "lagna_lord": ll,
        "vargottama_lagna": vargottama_lagna,
        "lagna_lord_d1_sign": ll_d1.get("sign", ""),
        "lagna_lord_d1_house": ll_d1.get("house"),
        "lagna_lord_dignity_d1": ll_dig,
        "lagna_lord_varga_sign": ll_v_sign,
        "lagna_lord_varga_house": ll_v_house,
        "lagna_lord_dignity_varga": ll_v_dig,
        "venus_d9_house": venus.get("house"),
        "venus_d9_sign": venus.get("sign", ""),
        "jupiter_d9_house": jupiter.get("house"),
        "jupiter_d9_sign": jupiter.get("sign", ""),
        "planets": bodies,
        "houses": houses,
        "precomputed_lagna": pj_d9.get("Lagna", ""),
    }
