#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compute KP chart block from PyJHora (KP ayanamsa + Placidus cusps)."""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

from kp_chart import AB3, SIGNS, abbr
from natal_from_pyjhora import BirthInput, DEFAULT_PYJHORA_SRC, _ensure_pyjhora, _effective_tob, _parse_pj_date

BASE_DIR = Path(__file__).resolve().parent
PJ_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
PLANET_IDS = {n: i for i, n in enumerate(PJ_PLANETS)}
SIGN_LORDS = [
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter",
]
VEDIC_WEEKDAY_LORD = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


def _pid_name(pid: int | str) -> str:
    if isinstance(pid, int) and 0 <= pid < len(PJ_PLANETS):
        return PJ_PLANETS[pid]
    if pid == "L":
        return "Lagna"
    return str(pid)


def _fmt_degree(deg: float) -> str:
    d = int(deg)
    rem = (deg - d) * 60.0
    m = int(rem)
    s = int(round((rem - m) * 60.0))
    if s >= 60:
        s -= 60
        m += 1
    if m >= 60:
        m -= 60
        d += 1
    return f"{d:03d}-{m:02d}-{s:02d}"


def _kp_lord_chain(lon_deg: float, *, levels: int = 4) -> list[str]:
    """Return [rasi_lord, nak_lord, sub_lord, ss, ...] as full planet names."""
    from jhora import utils as pj_utils

    row = pj_utils.kp_lords_for_longitude(
        "x", lon_deg % 360.0,
        include_sign_lord=True,
        include_kp_index=False,
        levels=max(1, levels - 1),
    )["x"]
    return [_pid_name(v) for v in row]


def _kp_lords_dict(lon_deg: float) -> dict[str, str]:
    chain = _kp_lord_chain(lon_deg, levels=4)
    keys = ("rasi_lord", "nak", "sub", "ss")
    return {k: chain[i] if i < len(chain) else "" for i, k in enumerate(keys)}


def _sign_from_lon(lon_deg: float) -> str:
    return SIGNS[int(lon_deg // 30) % 12]


def _vimshottari_kp(jd: float, place, pj_house) -> dict[str, Any]:
    """KP-ayanamsa Vimshottari tables for KP dasha lane."""
    from jhora.horoscope.dhasa.graha import vimsottari

    today = date.today()
    planet_list = pj_house.planet_list

    _, md_rows = vimsottari.get_vimsottari_dhasa_bhukthi(jd, place, dhasa_level_index=1)
    _, ad_rows = vimsottari.get_vimsottari_dhasa_bhukthi(jd, place, dhasa_level_index=2)
    _, pd_rows = vimsottari.get_vimsottari_dhasa_bhukthi(jd, place, dhasa_level_index=3)

    mahas = []
    for i, row in enumerate(md_rows):
        lord = planet_list[row[0]]
        start = _parse_pj_date(row[1])
        end = _parse_pj_date(md_rows[i + 1][1]) if i + 1 < len(md_rows) else start
        mahas.append({"lord": lord, "start": start, "end": end})

    cur = next((m for m in mahas if m["start"] <= today < m["end"]), mahas[0] if mahas else None)
    antars: list[dict] = []
    pratyantars: list[dict] = []
    if cur:
        md_id = planet_list.index(cur["lord"])
        md_ads = [r for r in ad_rows if r[0] == md_id]
        for j, row in enumerate(md_ads):
            ad_lord = planet_list[row[1]]
            start = _parse_pj_date(row[2])
            end = (
                _parse_pj_date(md_ads[j + 1][2])
                if j + 1 < len(md_ads)
                else cur["end"]
            )
            antars.append({"lord": ad_lord, "start": start, "end": end})

        cur_antar = next((a for a in antars if a["start"] <= today < a["end"]), antars[0] if antars else None)
        if cur_antar:
            ad_id = planet_list.index(cur_antar["lord"])
            md_pd = [r for r in pd_rows if r[0] == md_id and r[1] == ad_id]
            for j, row in enumerate(md_pd):
                pr_lord = planet_list[row[2]]
                start = _parse_pj_date(row[3])
                end = (
                    _parse_pj_date(md_pd[j + 1][3])
                    if j + 1 < len(md_pd)
                    else cur_antar["end"]
                )
                pratyantars.append({"lord": pr_lord, "start": start, "end": end})

    return {
        "maha": cur or {},
        "antars": antars,
        "pratyantars": pratyantars,
        "sequence": mahas,
    }


def _compute_significators(cusp_lons: list[float], planet_lons: dict[str, float], ayanamsa: float) -> tuple[dict, dict]:
    """House significators + planet house links (KP occupancy/lordship/star)."""
    from horary_precompute import SIGN_LORDS as H_SIG_LORDS, SIGNS as H_SIGNS
    from kp_horary_engine import bhava_significators, planet_significations_kp, placidus_house, sign_index

    cusps_trop = [((lon + ayanamsa) % 360.0) for lon in cusp_lons]
    planets_trop = {p: ((lon + ayanamsa) % 360.0) for p, lon in planet_lons.items()}

    signif: dict[int, list[str]] = {}
    for h in range(1, 13):
        sig = sorted(bhava_significators(h, cusps_trop, planets_trop, ayanamsa))
        if sig:
            signif[h] = sig

    planet_signif: dict[str, list[int]] = {}
    for planet in PJ_PLANETS:
        houses = sorted(planet_significations_kp(planet, cusps_trop, planets_trop, ayanamsa))
        if houses:
            planet_signif[planet] = houses

    return signif, planet_signif


def compute_kp_block(
    inp: BirthInput,
    *,
    pyjhora_src: Path | None = None,
) -> dict[str, Any]:
    """Full KP block for precompute JSON (KP ayanamsa, Placidus cusps)."""
    src = pyjhora_src or Path(os.environ.get("PYJHORA_SRC", DEFAULT_PYJHORA_SRC))
    _ensure_pyjhora(src)

    import swisseph as swe
    from jhora.panchanga import drik
    from jhora import utils
    from jhora.horoscope.chart import charts
    from jhora.horoscope.chart import house as pj_house

    drik.set_ayanamsa_mode("KP")
    swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)

    dob_parts = tuple(int(x) for x in inp.dob.split("-"))
    tob = _effective_tob(inp)
    place = drik.Place(inp.place_name or "BirthPlace", inp.latitude, inp.longitude, inp.timezone)
    jd = utils.julian_day_number(dob_parts, tob)
    jd_ut = jd - inp.timezone / 24.0
    ayanamsa = float(swe.get_ayanamsa_ut(jd_ut))

    pp = charts.rasi_chart(jd, place)
    cusp_lons = list(drik.bhaava_madhya_kp(jd, place))

    cusps: list[dict] = []
    for i, lon in enumerate(cusp_lons[:12], start=1):
        lords = _kp_lords_dict(lon)
        cusps.append({
            "cusp": i,
            "degree": _fmt_degree(lon),
            "sign": _sign_from_lon(lon),
            "rasi_lord": lords["rasi_lord"],
            "nak": lords["nak"],
            "sub": lords["sub"],
            "ss": lords["ss"],
            "sidereal_deg": round(lon % 360.0, 6),
        })

    planets: dict[str, dict] = {}
    planet_lons: dict[str, float] = {}
    for entry in pp:
        pid = entry[0]
        if pid == "L":
            continue
        if not isinstance(pid, int) or pid >= len(PJ_PLANETS):
            continue
        name = PJ_PLANETS[pid]
        si, deg = entry[1]
        lon = si * 30.0 + deg
        planet_lons[name] = lon
        lords = _kp_lords_dict(lon)
        planets[name] = {
            "degree": _fmt_degree(lon),
            "sign": SIGNS[si],
            "rasi_lord": lords["rasi_lord"],
            "nak": lords["nak"],
            "sub": lords["sub"],
            "ss": lords["ss"],
            "sidereal_deg": round(lon, 6),
        }

    asc_lon = cusp_lons[0]
    asc_chain = _kp_lord_chain(asc_lon, levels=3)
    moon_chain = _kp_lord_chain(planet_lons.get("Moon", 0.0), levels=3)
    dob_date = date.fromisoformat(inp.dob)
    day_lord = VEDIC_WEEKDAY_LORD[dob_date.weekday()]

    ruling = {
        "Lagna": asc_chain[:3],
        "Moon": moon_chain[:3],
        "Day Lord": [day_lord],
    }

    signif, planet_signif = _compute_significators(cusp_lons, planet_lons, ayanamsa)
    dasha = _vimshottari_kp(jd, place, pj_house)
    for key in ("maha",):
        if dasha.get(key):
            for dk in ("start", "end"):
                if isinstance(dasha[key].get(dk), date):
                    dasha[key][dk] = str(dasha[key][dk])
    for bucket in ("antars", "pratyantars", "sequence"):
        for row in dasha.get(bucket, []):
            for dk in ("start", "end"):
                if isinstance(row.get(dk), date):
                    row[dk] = str(row[dk])

    lagna_sign = SIGNS[int(asc_lon // 30) % 12]
    return {
        "ayanamsa": "KP",
        "ayanamsa_value": round(ayanamsa, 6),
        "lagna_sign": lagna_sign,
        "ruling": ruling,
        "cusps": cusps,
        "planets": planets,
        "significators": {str(k): v for k, v in signif.items()},
        "planet_signification": {p: hs for p, hs in planet_signif.items()},
        "dasha": dasha,
        "source": "pyjhora",
    }


def kp_block_from_precompute(pc: dict) -> dict[str, Any] | None:
    return pc.get("kp")


def load_kp_from_precompute(pc: dict, dob: date, client_name: str = "") -> "KPChart":
    """Build KPChart from precomputed kp block (no extract text)."""
    from kp_chart import KPChart

    block = kp_block_from_precompute(pc)
    if not block:
        raise ValueError(
            "Precomputed JSON has no kp block; regenerate with PyJHora natal precompute."
        )
    return KPChart.from_block(pc, block, dob, client_name or pc.get("meta", {}).get("client", ""))
