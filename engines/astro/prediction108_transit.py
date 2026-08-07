#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Current-transit and Varshaphal (annual / Tajaka) context for the 108-rule engine.

Builds two dicts and attaches them to `pc` so the transit (ch 84-97) and annual
(ch 98-108) rules in prediction108_rules.py can be evaluated:

    pc["_transit"] – today's sidereal planet positions + houses from natal lagna/Moon
    pc["_annual"]  – the active solar-return chart: annual lagna, Year Lord, Muntha,
                     Tri-Rashi-Pati, Panch-Vargiya strengths, annual positions

Uses the same PyJHora engine as the natal pipeline.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from astro_precompute import SIGNS, SIGN_LORDS, sign_index

_PJ = Path(__file__).resolve().parent / "pyjhora" / "src"
if str(_PJ) not in sys.path:
    sys.path.insert(0, str(_PJ))

PID_NAME = {0: "Sun", 1: "Moon", 2: "Mars", 3: "Mercury", 4: "Jupiter",
            5: "Venus", 6: "Saturn", 7: "Rahu", 8: "Ketu"}


def _house(sign: str, ref_sign: str) -> int:
    if not sign or not ref_sign:
        return 0
    return (sign_index(sign) - sign_index(ref_sign)) % 12 + 1


def _strength_category(score: float) -> str:
    if score is None:
        return "unknown"
    if score > 15:
        return "extraordinary"
    if score >= 10:
        return "strong"
    if score >= 5:
        return "medium"
    return "weak"


def _resolve_coords(pc):
    """Return (lat, lon, tz) from pc — explicit fields, dict birth_place, or geocoded name."""
    meta = pc.get("meta", {})
    # explicit numeric fields if present
    for key in ("_coords",):
        c = meta.get(key)
        if isinstance(c, dict) and c.get("latitude") is not None:
            return float(c["latitude"]), float(c["longitude"]), float(c.get("timezone", 5.5))
    bp = meta.get("birth_place")
    if isinstance(bp, dict) and bp.get("latitude") is not None:
        return float(bp["latitude"]), float(bp["longitude"]), float(bp.get("timezone", 5.5))
    lat, lon = meta.get("latitude"), meta.get("longitude")
    if lat is not None and lon is not None:
        return float(lat), float(lon), float(meta.get("timezone", 5.5))
    # geocode the place-name string
    name = bp if isinstance(bp, str) else (meta.get("birth_place_name") or "")
    if name:
        try:
            from birth_place_resolve import resolve_birth_place
            r = resolve_birth_place(name)
            return float(r["latitude"]), float(r["longitude"]), float(r["timezone"])
        except Exception:
            pass
    return 0.0, 0.0, 5.5


def _place_and_jd_birth(pc):
    from jhora.panchanga import drik
    from jhora import utils
    drik.set_ayanamsa_mode("LAHIRI")
    meta = pc.get("meta", {})
    lat, lon, tz = _resolve_coords(pc)
    place = drik.Place(str(meta.get("client", "Birth")), float(lat), float(lon), float(tz))
    dob = meta.get("dob", "1970-01-01")
    y, m, d = [int(x) for x in dob.split("-")]
    bt = str(meta.get("birth_time", "12:00"))
    parts = [int(x) for x in bt.split(":")] + [0, 0]
    jd_birth = utils.julian_day_number((y, m, d), (parts[0], parts[1], parts[2]))
    return place, jd_birth, (y, m, d)


# ── current transit context ─────────────────────────────────────────
def build_transit_context(pc: dict, on: date | None = None) -> dict:
    from jhora.panchanga import drik
    from jhora import utils
    from jhora.horoscope.chart import charts

    place, _jd_birth, _dob = _place_and_jd_birth(pc)
    on = on or date.today()
    jd = utils.julian_day_number((on.year, on.month, on.day), (12, 0, 0))
    pp = charts.rasi_chart(jd, place)
    retro = set(drik.planets_in_retrograde(jd, place) or [])

    natal_lagna = pc.get("meta", {}).get("lagna_sign", "")
    natal_moon = pc.get("planets", {}).get("Moon", {}).get("sign", "")

    positions = {}
    for entry in pp[1:]:
        pid, (si, deg) = entry[0], entry[1]
        if pid not in PID_NAME:
            continue
        s = SIGNS[si % 12]
        positions[PID_NAME[pid]] = {
            "sign": s, "deg": round(float(deg), 2),
            "retro": pid in retro,
            "house_natal": _house(s, natal_lagna),
            "from_moon": _house(s, natal_moon),
        }
    return {
        "date": on.isoformat(),
        "positions": positions,
        "natal_lagna": natal_lagna,
        "natal_moon": natal_moon,
    }


# ── annual / Varshaphal context ─────────────────────────────────────
def _years_param(dob_tuple, today: date) -> tuple[int, int]:
    y, m, d = dob_tuple
    lived = today.year - y - (1 if (today.month, today.day) < (m, d) else 0)
    return lived, lived + 1  # (completed years, tajaka 'years' param for active varsha)


def build_annual_context(pc: dict, on: date | None = None) -> dict:
    from jhora import const
    from jhora.horoscope.chart import strength
    from jhora.horoscope.transit import tajaka
    from jhora import utils

    place, jd_birth, dob = _place_and_jd_birth(pc)
    on = on or date.today()
    lived, yp = _years_param(dob, on)

    cht, ymd = tajaka.annual_chart(jd_birth, place, divisional_chart_factor=1, years=yp)
    # ymd = [(y,m,d), 'HH:MM:SS']
    ret_ymd, ret_time = ymd[0], ymd[1]
    # if this return is in the future, step back one year
    rd = date(ret_ymd[0], ret_ymd[1], ret_ymd[2])
    if rd > on:
        yp -= 1
        cht, ymd = tajaka.annual_chart(jd_birth, place, divisional_chart_factor=1, years=yp)
        ret_ymd, ret_time = ymd[0], ymd[1]
        rd = date(ret_ymd[0], ret_ymd[1], ret_ymd[2])

    asc_si = cht[0][1][0]
    asc_sign = SIGNS[asc_si % 12]
    asc_lord = SIGN_LORDS.get(asc_sign, "")

    positions = {}
    for entry in cht[1:]:
        pid, (si, deg) = entry[0], entry[1]
        if pid not in PID_NAME:
            continue
        s = SIGNS[si % 12]
        positions[PID_NAME[pid]] = {
            "sign": s, "deg": round(float(deg), 2),
            "house": _house(s, asc_sign),
        }

    # Year Lord (Varshesha)
    try:
        yl_id = tajaka.lord_of_the_year(jd_birth, place, years_from_dob=yp)
        year_lord = PID_NAME.get(yl_id, str(yl_id))
    except Exception:
        year_lord = ""

    # Panch-Vargiya bala at the solar-return moment
    pvb = {}
    try:
        tt = [int(x) for x in str(ret_time).split(":")] + [0, 0]
        jd_ret = utils.julian_day_number(tuple(ret_ymd), (tt[0], tt[1], tt[2]))
        raw = strength.pancha_vargeeya_bala(jd_ret, place)
        pvb = {PID_NAME[k]: round(float(v), 2) for k, v in raw.items() if k in PID_NAME}
    except Exception:
        pvb = {}

    # Muntha
    try:
        muntha_si = tajaka.muntha_house(asc_si, yp) % 12
    except Exception:
        muntha_si = (asc_si + yp) % 12
    muntha_sign = SIGNS[muntha_si]
    muntha_lord = SIGN_LORDS.get(muntha_sign, "")
    muntha_house = _house(muntha_sign, asc_sign)

    # Tri-Rashi-Pati (day/night from annual Sun above/below horizon)
    sun_house = positions.get("Sun", {}).get("house", 0)
    day_birth = sun_house in (7, 8, 9, 10, 11, 12)
    try:
        arr = const.tri_rasi_daytime_lords if day_birth else const.tri_rasi_nighttime_lords
        trp = PID_NAME.get(arr[asc_si % 12], "")
    except Exception:
        trp = ""

    natal_lagna_lord = pc.get("meta", {}).get("lagna_lord", "")

    return {
        "year_param": yp,
        "years_lived": lived,
        "return_date": rd.isoformat(),
        "return_time": ret_time,
        "lagna_sign": asc_sign,
        "lagna_lord": asc_lord,
        "year_lord": year_lord,
        "year_lord_bala": pvb.get(year_lord),
        "year_lord_strength": _strength_category(pvb.get(year_lord)),
        "muntha_sign": muntha_sign,
        "muntha_house": muntha_house,
        "muntha_lord": muntha_lord,
        "tri_rashi_pati": trp,
        "pvb": pvb,
        "positions": positions,
        "natal_lagna_lord": natal_lagna_lord,
        "natal_lagna_lord_bala": pvb.get(natal_lagna_lord),
        "natal_lagna_lord_strength": _strength_category(pvb.get(natal_lagna_lord)),
        "day_birth": day_birth,
    }


def attach_contexts(pc: dict, on: date | None = None,
                    latitude: float | None = None, longitude: float | None = None,
                    timezone: float | None = None) -> dict:
    """Compute transit + annual contexts and attach them to pc (best-effort)."""
    if latitude is not None and longitude is not None:
        pc.setdefault("meta", {})["_coords"] = {
            "latitude": latitude, "longitude": longitude,
            "timezone": 5.5 if timezone is None else timezone,
        }
    try:
        pc["_transit"] = build_transit_context(pc, on)
    except Exception as exc:  # noqa: BLE001
        pc["_transit"] = {"error": str(exc)}
    try:
        pc["_annual"] = build_annual_context(pc, on)
    except Exception as exc:  # noqa: BLE001
        pc["_annual"] = {"error": str(exc)}
    return pc


if __name__ == "__main__":
    from astro_chart_bridge import compute_chart
    pc = compute_chart(client_name="Sample", dob="1990-01-15", birth_time="12:00",
                       place="New Delhi, India", latitude=28.6139, longitude=77.2090, timezone=5.5)
    attach_contexts(pc, latitude=28.6139, longitude=77.2090, timezone=5.5)
    import json
    print(json.dumps(pc["_transit"], indent=2))
    print(json.dumps(pc["_annual"], indent=2))
