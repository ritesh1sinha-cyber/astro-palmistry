#!/usr/bin/env python3
"""
western_horary_precompute.py — Tropical Placidus chart for Western horary (Louis / Lilly).

Input: question, YYYY-MM-DD, HH:MM (24h IST), location
Output: JSON with asc, mc, cusps, planets + house numbers for LLM (Swiss Ephemeris MOSEPH).

Usage:
  python3 western_horary_precompute.py "Will I get bonus?" "2026-04-10" "01:20" "Hyderabad" [out.json]
"""

from __future__ import annotations

import json
import math
import sys
from datetime import date as Date
from pathlib import Path

from horary_precompute import LOCATIONS, ist_to_ut, julian_day, parse_time

# Julian Day must match horary_precompute.py (same UT / day rollover rules).

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


def lon_to_sign(lon: float) -> tuple[str, float]:
    lon = lon % 360.0
    idx = int(lon // 30)
    return SIGNS[idx], lon % 30


def lon_in_placidus_house(lon: float, cusps: list) -> int:
    """cusps[0]..cusps[11] = house 1..12 cusp tropical longitudes."""
    lon = lon % 360.0
    for i in range(12):
        a, b = cusps[i], cusps[(i + 1) % 12]
        if a < b:
            if a <= lon < b:
                return i + 1
        else:
            if lon >= a or lon < b:
                return i + 1
    return 1


def precompute_western(
    question: str,
    q_date_str: str,
    q_time_str: str,
    location: str = "Hyderabad",
) -> dict:
    hour, minute = parse_time(q_time_str)
    year, month, day = map(int, q_date_str.split("-"))
    q_date_obj = Date(year, month, day)

    loc_key = location.lower().split(",")[0].strip()
    lat, lon = LOCATIONS.get(loc_key, LOCATIONS["hyderabad"])

    ut_hour = ist_to_ut(hour, minute)
    jd_adjustment = 0
    if ut_hour < 0:
        ut_hour += 24
        jd_adjustment = -1
    jd_ut = julian_day(year, month, day, ut_hour) + jd_adjustment

    utc_h = int(ut_hour) % 24
    utc_m = int(round((ut_hour % 1) * 60)) % 60

    out = {
        "meta": {
            "question": question,
            "q_date": q_date_str,
            "q_time_ist": q_time_str,
            "q_time_ut_approx": f"{utc_h:02d}:{utc_m:02d}",
            "location": location,
            "lat": lat,
            "lon": lon,
            "julian_day_ut": round(jd_ut, 6),
            "jd_adjustment_days": jd_adjustment,
            "zodiac": "tropical",
            "house_system": "Placidus",
            "note": "Louis often uses Koch in the book; Placidus is standard fallback. Values are geocentric tropical.",
        },
        "angles": {},
        "cusps": [],
        "planets": {},
        "precompute_engine": None,
        "llm_instructions": "",
    }

    try:
        import swisseph as swe
    except ImportError:
        out["precompute_engine"] = "none_install_pyswisseph"
        out["llm_instructions"] = (
            "pyswisseph not installed. Fetch Tropical Placidus chart from WebSearch/WebFetch "
            "for this exact UTC instant and coordinates; then fill WesternHorary_template.html."
        )
        return out

    cusps, ascmc = swe.houses(jd_ut, lat, lon, b"P")
    asc_deg, mc_deg = ascmc[0], ascmc[1]

    out["angles"] = {
        "ascendant_deg": round(asc_deg, 4),
        "asc_sign": lon_to_sign(asc_deg)[0],
        "asc_deg_in_sign": round(lon_to_sign(asc_deg)[1], 4),
        "mc_deg": round(mc_deg, 4),
        "mc_sign": lon_to_sign(mc_deg)[0],
    }
    out["cusps"] = [round(c, 4) for c in cusps]
    out["precompute_engine"] = "swiss_ephemeris_moseph"

    planet_ids = [
        (swe.SUN, "Sun"),
        (swe.MOON, "Moon"),
        (swe.MERCURY, "Mercury"),
        (swe.VENUS, "Venus"),
        (swe.MARS, "Mars"),
        (swe.JUPITER, "Jupiter"),
        (swe.SATURN, "Saturn"),
        (swe.URANUS, "Uranus"),
        (swe.NEPTUNE, "Neptune"),
        (swe.PLUTO, "Pluto"),
    ]
    for pid, name in planet_ids:
        xx, _ret = swe.calc_ut(jd_ut, pid, swe.FLG_MOSEPH | swe.FLG_SPEED)
        lonp = xx[0]
        sp = xx[3]
        sg, du = lon_to_sign(lonp)
        out["planets"][name] = {
            "longitude": round(lonp, 4),
            "sign": sg,
            "deg_in_sign": round(du, 4),
            "house": lon_in_placidus_house(lonp, cusps),
            "speed_deg_per_day": round(sp, 4),
            "retrograde": sp < 0,
        }

    # Day vs night: Sun alt simplified — Sun in houses 7-12 = day chart (above horizon) for hemisphere
    sun_h = out["planets"]["Sun"]["house"]
    out["meta"]["chart_type"] = "day" if 7 <= sun_h <= 12 else "night"

    out["llm_instructions"] = (
        "Use ONLY these Tropical Placidus values for the Western horary report. "
        "Follow .cursor/skills/western-horary/SKILL.md §2b (Louis Chapter 2 checklist). "
        "Copy reports/WesternHorary_template.html → the output path; remove template note box. "
        "Do NOT include KP, Jamakkol, or Prashna Kundali — Western lane only."
    )
    return out


def main():
    if len(sys.argv) < 5:
        print("Usage: python3 western_horary_precompute.py <question> <YYYY-MM-DD> <HH:MM> <location> [out.json]")
        sys.exit(1)
    question = sys.argv[1]
    q_date = sys.argv[2]
    q_time = sys.argv[3]
    location = sys.argv[4]
    out_path = sys.argv[5] if len(sys.argv) > 5 else "western_horary_precomputed.json"
    data = precompute_western(question, q_date, q_time, location)
    Path(out_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("Western horary pre-compute:", data["precompute_engine"] or "ok")
    print(f"  ASC {data['angles'].get('asc_sign', '?')} {data['angles'].get('asc_deg_in_sign', '')} | chart_type={data['meta'].get('chart_type', '')}")
    for p in ("Sun", "Moon", "Mercury"):
        if p in data["planets"]:
            z = data["planets"][p]
            print(f"  {p}: {z['sign']} {z['deg_in_sign']:.2f} H{z['house']}")


if __name__ == "__main__":
    main()
