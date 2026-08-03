#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Goel rules8 - *New Research in Timing of Events Using Chara & Yogini Dasha*.
Progressive Yogini (PL + nakshatra lord) + Chara MD-lagna lord link.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from astro_precompute import (
    NAKSHATRAS,
    NAK_TO_DASHA_LORD,
    NAK_SPAN,
    SIGN_LORDS,
    SIGNS,
    YOGINI_LORDS,
    YOGINI_NAMES,
    YOGINI_YEARS,
    house_from_lagna,
    house_sign,
    normalize_nakshatra,
)

GOEL_RULES_SOURCE = "rules8.md (Goel - Chara & Yogini timing research)"

EVENT_CHARA_KARAKAS: dict[str, list[str]] = {
    "marriage": ["Darakaraka"],
    "child": ["Putrakaraka"],
    "career": ["Amatyakarak"],
    "property": ["Matrukaraka"],
    "education": ["Putrakaraka", "Amatyakarak"],
    "travel": ["Gnatikaraka", "Atmakarak"],
    "business": ["Amatyakarak", "Bhratrukaraka"],
    "recovery": ["Atmakarak", "Putrakaraka"],
    "wealth": ["Amatyakarak", "Bhratrukaraka"],
    "status": ["Amatyakarak", "Atmakarak"],
}


def _as_date(v) -> date:
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def _overlaps(w_start: date, w_end: date, p_start: date, p_end: date) -> bool:
    return p_end > w_start and p_start < w_end


def _nak_index(nak: str) -> int:
    n = normalize_nakshatra(nak.split("-")[0].strip())
    if n in NAKSHATRAS:
        return NAKSHATRAS.index(n)
    base = nak.split()[0][:6].lower()
    for i, name in enumerate(NAKSHATRAS):
        if name.lower().startswith(base[:5]):
            return i
    return 0


def _nak_pl_sign(nak_idx: int) -> str:
    """Progress lagna sign = sign of nakshatra (rules8 PL)."""
    deg = (nak_idx * NAK_SPAN) % 360.0
    return SIGNS[int(deg // 30) % 12]


def _next_nak_idx(cur: int, birth_nak_idx: int) -> int:
    """Revati -> Rohini jump unless birth in Ashwini/Bharani/Krittika."""
    if cur == 26:
        if birth_nak_idx in (0, 1, 2):
            return 0
        return 3
    return (cur + 1) % 27


def birth_yogini_serial(moon_nak: str) -> int:
    """Yogini serial 1-8: (nak number + 3) mod 8."""
    nak_num = _nak_index(moon_nak) + 1
    rem = (nak_num + 3) % 8
    return 8 if rem == 0 else rem


def build_progressive_yogini_periods(
    dob: date,
    moon_nak: str,
    moon_deg_in_nak: float = 0.0,
    *,
    max_years: float = 90.0,
) -> list[dict[str, Any]]:
    """Yogini maha + antar with paired nakshatra and PL sign (rules8)."""
    birth_nak_idx = _nak_index(moon_nak)
    birth_serial = birth_yogini_serial(moon_nak)
    birth_yog_idx = birth_serial - 1

    fraction_used = min(0.999, max(0.0, moon_deg_in_nak / NAK_SPAN))
    balance = YOGINI_YEARS[birth_yog_idx] * (1.0 - fraction_used)

    periods: list[dict[str, Any]] = []
    cur = dob
    nak_idx = birth_nak_idx
    yog_idx = birth_yog_idx
    end_limit = dob + timedelta(days=int(max_years * 365.25))
    first = True

    while cur < end_limit:
        maha_years = balance if first else float(YOGINI_YEARS[yog_idx])
        first = False
        maha_end = cur + timedelta(days=int(maha_years * 365.25))
        nak_name = NAKSHATRAS[nak_idx]
        pl_sign = _nak_pl_sign(nak_idx)
        nak_lord = NAK_TO_DASHA_LORD[nak_name]

        antar_cursor = cur
        child_years_total = sum(YOGINI_YEARS)
        for sub_i in range(8):
            sub_y_idx = (yog_idx + sub_i) % 8
            sub_years = maha_years * (YOGINI_YEARS[sub_y_idx] / child_years_total)
            sub_end = antar_cursor + timedelta(days=max(1, int(sub_years * 365.25)))
            if sub_end > maha_end:
                sub_end = maha_end
            periods.append({
                "level": "antar",
                "yogini": YOGINI_NAMES[sub_y_idx],
                "lord": YOGINI_LORDS[sub_y_idx],
                "maha_yogini": YOGINI_NAMES[yog_idx],
                "nakshatra": nak_name,
                "nak_lord": nak_lord,
                "pl_sign": pl_sign,
                "start": antar_cursor,
                "end": sub_end,
            })
            antar_cursor = sub_end
            if antar_cursor >= maha_end:
                break

        cur = maha_end
        nak_idx = _next_nak_idx(nak_idx, birth_nak_idx)
        yog_idx = (yog_idx + 1) % 8

    return periods


def _karaka_planets(pc: dict, roles: list[str]) -> set[str]:
    out: set[str] = set()
    for k in (pc.get("cara_karakas") or {}).get("karakas", []):
        if k.get("role") in roles and k.get("planet"):
            out.add(k["planet"])
    return out


def _lord_connects(
    lord: str,
    birth_house_lord: str,
    planets: dict,
    birth_lagna: str,
    event_houses: set[int],
    cara_karakas: set[str],
) -> tuple[bool, str]:
    if not lord:
        return False, ""
    if lord == birth_house_lord:
        return True, f"{lord} same as birth house lord"
    if lord in cara_karakas:
        return True, f"{lord} is cara karaka"
    pdata = planets.get(lord, {})
    psign = pdata.get("sign", "")
    if psign:
        h_from_birth = house_from_lagna(psign, birth_lagna)
        if h_from_birth in event_houses:
            return True, f"{lord} in {h_from_birth}th from birth"
    bdata = planets.get(birth_house_lord, {})
    if psign and bdata.get("sign") == psign:
        return True, f"{lord} conjunct {birth_house_lord}"
    if birth_house_lord in cara_karakas and lord == birth_house_lord:
        return True, "birth lord is karaka"
    return False, ""


def score_yogini_goel_window(
    *,
    w_start: date,
    w_end: date,
    event_kind: str,
    event_houses: set[int],
    birth_lagna: str,
    planets: dict,
    pc: dict,
    moon_nak: str,
    moon_deg_in_nak: float = 0.0,
    dob: date,
) -> dict[str, Any]:
    """Progressive Yogini PL method (rules8 Part B-C)."""
    if not moon_nak or not birth_lagna:
        return {"yes": False, "note": "Moon nakshatra unavailable", "available": False}

    periods = build_progressive_yogini_periods(dob, moon_nak, moon_deg_in_nak)
    hits: list[str] = []
    event_kind_roles = _karaka_planets(pc, EVENT_CHARA_KARAKAS.get(event_kind, []))

    for p in periods:
        if not _overlaps(w_start, w_end, p["start"], p["end"]):
            continue
        pl = p["pl_sign"]
        nak_lord = p["nak_lord"]
        for h in sorted(event_houses):
            pl_house_sign = house_sign(h, pl)
            pl_lord = SIGN_LORDS[pl_house_sign]
            birth_house_sign = house_sign(h, birth_lagna)
            birth_lord = SIGN_LORDS[birth_house_sign]

            ok, note = _lord_connects(pl_lord, birth_lord, planets, birth_lagna, event_houses, event_kind_roles)
            if ok:
                hits.append(
                    f"{p['maha_yogini']}/{p['yogini']} PL {pl}: {note}"
                )
                break

            ok2, note2 = _lord_connects(nak_lord, birth_lord, planets, birth_lagna, event_houses, event_kind_roles)
            if ok2:
                hits.append(f"{p['nakshatra']} lord {nak_lord}: {note2}")
                break

        if hits:
            break

    return {
        "available": True,
        "yes": bool(hits),
        "note": hits[0] if hits else "no PL/birth lord link in Yogini overlap",
        "source": GOEL_RULES_SOURCE,
    }


def score_chara_goel_window(
    *,
    w_start: date,
    w_end: date,
    event_kind: str,
    event_houses: set[int],
    birth_lagna: str,
    planets: dict,
    pc: dict,
    chara: dict,
) -> dict[str, Any]:
    """Chara MD sign as lagna; event house lord must link to birth (rules8 Part D)."""
    from jaimini_chara_dasha import get_chara_dasha

    if not chara or not chara.get("maha"):
        chara = get_chara_dasha(pc)
    if not chara.get("maha") or not birth_lagna:
        return {"yes": False, "note": "Chara dasha unavailable", "available": False}

    cara_roles = _karaka_planets(pc, EVENT_CHARA_KARAKAS.get(event_kind, []))

    hits: list[str] = []
    for m in chara.get("maha", []):
        try:
            m_start = _as_date(m["start"])
            m_end = _as_date(m.get("end") or m["start"])
        except (ValueError, TypeError):
            continue
        if not _overlaps(w_start, w_end, m_start, m_end):
            continue
        maha_lagna = m.get("sign", "")
        if maha_lagna not in SIGNS:
            continue
        for h in sorted(event_houses):
            m_lord = SIGN_LORDS[house_sign(h, maha_lagna)]
            b_lord = SIGN_LORDS[house_sign(h, birth_lagna)]
            ok, note = _lord_connects(m_lord, b_lord, planets, birth_lagna, event_houses, cara_roles)
            if ok:
                hits.append(f"Chara MD {maha_lagna}: {note}")
                break
        if hits:
            break

    return {
        "available": bool(chara.get("maha")),
        "yes": bool(hits),
        "note": hits[0] if hits else "no Chara MD lord link to birth house lord",
        "source": GOEL_RULES_SOURCE,
    }
