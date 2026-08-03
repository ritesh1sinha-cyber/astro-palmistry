#!/usr/bin/env python3
"""
KP Horary engine - Chart A (1-249 Placidus) + Chart B (Ruling Planets).

Uses canonical KP 1-249 table (JyotishPortal / KSK sub-lord divisions) and
Swiss Ephemeris for Placidus cusps + tropical planet positions at judgment time.
"""
from __future__ import annotations

import json
from pathlib import Path

from horary_precompute import (
    NAK_SPAN_DEG, SIGN_LORDS, SIGNS, TOPIC_BHAVAS,
    get_nakshatra, PYTHON_WEEKDAY_TO_VEDIC,
)

_BASE = Path(__file__).resolve().parent
_KP_TABLE: list[dict] | None = None


def _swe_planet_ids(swe) -> dict[str, int]:
    return {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS,
        "Mars": swe.MARS, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE,
    }


def load_kp_table() -> list[dict]:
    global _KP_TABLE
    if _KP_TABLE is None:
        _KP_TABLE = json.loads((_BASE / "kp_249_table.json").read_text(encoding="utf-8"))
    return _KP_TABLE


def kp_number_lookup(kp_num: int) -> dict:
    """Canonical KP horary number -> sidereal ascendant longitude + sub-lord chain."""
    if not 1 <= kp_num <= 249:
        return {"error": f"KP number {kp_num} out of range 1-249"}
    row = load_kp_table()[kp_num - 1]
    sid = row["sidereal_lon"]
    nak = get_nakshatra(sid)
    return {
        "kp_number": kp_num,
        "sign": row["sign"],
        "degree_in_sign": row["degree_in_sign"],
        "approx_degree": round(row["degree_in_sign"], 2),
        "approx_sidereal_lon": round(sid, 4),
        "sidereal_asc_deg": sid,
        "nakshatra": row["nakshatra"],
        "star_lord": row["star_lord"],
        "sub_lord": row["sub_lord"],
        "sign_lord": SIGN_LORDS[row["sign"]],
        "table_sub_lord": row["sub_lord"],
        "table_star_lord": row["star_lord"],
        "asc_sub_lord": nak["sub_lord"],
        "asc_star_lord": nak["star_lord"],
    }


def _require_swe():
    import swisseph as swe
    swe.set_ephe_path("")
    swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
    return swe


def kp_ayanamsa(jd_ut: float) -> float:
    """KP / Krishnamurti ayanamsa at judgment time (Arumugam: Ayan Type K.P.)."""
    return float(_require_swe().get_ayanamsa_ut(jd_ut))


def get_armc_for_tropical_asc(target_tropical_asc: float, lat: float, eps: float = 23.4392911) -> float:
    swe = _require_swe()
    lo, hi = 0.0, 360.0
    for _ in range(70):
        mid = (lo + hi) / 2.0
        _c, ascmc = swe.houses_armc(mid, lat, eps, b"P")
        a = ascmc[0] % 360
        d = (a - target_tropical_asc + 180) % 360 - 180
        if d < 0:
            lo = mid
        else:
            hi = mid
    return hi


def tropical_planets(jd_ut: float) -> dict[str, float]:
    swe = _require_swe()
    flg = swe.FLG_SWIEPH
    out: dict[str, float] = {}
    for name, pid in _swe_planet_ids(swe).items():
        out[name] = swe.calc_ut(jd_ut, pid, flg)[0][0] % 360
    out["Ketu"] = (out["Rahu"] + 180) % 360
    return out


def placidus_cusps_tropical(sidereal_asc: float, jd_ut: float, lat: float) -> tuple[list[float], float]:
    """Placidus cusps (tropical) for Chart A: fixed KP# sidereal ASC at judgment latitude."""
    swe = _require_swe()
    ayan = kp_ayanamsa(jd_ut)
    trop_asc = (sidereal_asc + ayan) % 360
    armc = get_armc_for_tropical_asc(trop_asc, lat)
    cusps, _ = swe.houses_armc(armc, lat, 23.4392911, b"P")
    return [cusps[i] % 360 for i in range(12)], ayan


def placidus_house(tropical_lon: float, cusps: list[float]) -> int:
    lon = tropical_lon % 360
    for h in range(12):
        a, b = cusps[h], cusps[(h + 1) % 12]
        if a <= b:
            if a <= lon < b:
                return h + 1
        elif lon >= a or lon < b:
            return h + 1
    return 0


def sign_index(lon: float) -> int:
    return int(lon // 30) % 12


def rashi_aspect_targets(from_sign_idx: int, planet: str) -> set[int]:
    """Whole-rashi aspects: sign indices aspected by planet from its sign."""
    if planet == "Saturn":
        offs = {2, 6, 9}
    elif planet == "Jupiter":
        offs = {4, 6, 8}
    elif planet == "Mars":
        offs = {3, 6, 7}
    else:
        offs = {6}
    return {(from_sign_idx + o) % 12 for o in offs}


def planet_significations_kp(
    planet: str,
    cusps_trop: list[float],
    planets_trop: dict[str, float],
    ayanamsa: float,
) -> set[int]:
    sig: set[int] = set()
    if planet not in planets_trop:
        return sig

    occ = placidus_house(planets_trop[planet], cusps_trop)
    if occ:
        sig.add(occ)

    for h in range(1, 13):
        cusp_sid = (cusps_trop[h - 1] - ayanamsa) % 360
        if SIGN_LORDS[SIGNS[sign_index(cusp_sid)]] == planet:
            sig.add(h)

    sid = (planets_trop[planet] - ayanamsa) % 360
    star = get_nakshatra(sid)["star_lord"]
    if star in planets_trop:
        sh = placidus_house(planets_trop[star], cusps_trop)
        if sh:
            sig.add(sh)
        for h in range(1, 13):
            cusp_sid = (cusps_trop[h - 1] - ayanamsa) % 360
            if SIGN_LORDS[SIGNS[sign_index(cusp_sid)]] == star:
                sig.add(h)
    return sig


def bhava_significators(
    house_n: int,
    cusps_trop: list[float],
    planets_trop: dict[str, float],
    ayanamsa: float,
) -> set[str]:
    """
    Planets signifying bhava N (KSK / Arumugam 2.4): occupancy, lordship, star-lord links.
    Implemented via planet->house significations (book List A uses significators, not occupants only).
    """
    out: set[str] = set()
    for planet in planets_trop:
        if house_n in planet_significations_kp(planet, cusps_trop, planets_trop, ayanamsa):
            out.add(planet)
    return out


def list_a_significators(
    cusps_trop: list[float],
    planets_trop: dict[str, float],
    ayanamsa: float,
    houses: list[int],
) -> list[str]:
    """List A: deduped union of significators of topic favourable bhavas (Chart A)."""
    found: set[str] = set()
    for h in houses:
        found |= bhava_significators(h, cusps_trop, planets_trop, ayanamsa)
    return sorted(found)


def list_a_occupants(cusps_trop: list[float], planets_trop: dict[str, float], houses: list[int]) -> list[str]:
    """Placidus occupants only (diagnostic; book List A uses significators)."""
    found = []
    for pname, lon in planets_trop.items():
        if placidus_house(lon, cusps_trop) in houses:
            found.append(pname)
    return sorted(set(found))


def compute_chart_a(kp_num: int, jd_ut: float, lat: float, lon: float) -> dict:
    kp = kp_number_lookup(kp_num)
    sid_asc = kp["sidereal_asc_deg"]
    cusps, ayan = placidus_cusps_tropical(sid_asc, jd_ut, lat)
    planets = tropical_planets(jd_ut)

    cusp_info = {}
    for h in range(1, 13):
        c_sid = (cusps[h - 1] - ayan) % 360
        nk = get_nakshatra(c_sid)
        cusp_info[str(h)] = {
            "tropical_deg": round(cusps[h - 1], 4),
            "sidereal_deg": round(c_sid, 4),
            "sign": SIGNS[sign_index(c_sid)],
            "nakshatra": nk["nakshatra"],
            "star_lord": nk["star_lord"],
            "sub_lord": nk["sub_lord"],
        }

    return {
        "kp": kp,
        "sidereal_asc_deg": sid_asc,
        "ayanamsa": round(ayan, 4),
        "cusps_tropical": [round(c, 4) for c in cusps],
        "cusp_info": cusp_info,
        "planets_tropical": {p: round(v, 4) for p, v in planets.items()},
        "planet_houses": {p: placidus_house(lon, cusps) for p, lon in planets.items()},
    }


def compute_chart_b(jd_ut: float, lat: float, lon: float) -> dict:
    swe = _require_swe()
    _cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, b"P", swe.FLG_SIDEREAL | swe.FLG_SWIEPH)
    sid_asc = ascmc[0] % 360
    ayan = kp_ayanamsa(jd_ut)
    trop_asc = (sid_asc + ayan) % 360
    planets = tropical_planets(jd_ut)
    lagna_sign = SIGNS[sign_index(trop_asc)]
    moon_trop = planets["Moon"]
    moon_sid = (moon_trop - ayan) % 360
    moon_sign_trop = SIGNS[sign_index(moon_trop)]
    moon_sign_sid = SIGNS[sign_index(moon_sid)]
    lagna_nak = get_nakshatra(sid_asc)
    moon_nak = get_nakshatra(moon_sid)

    return {
        "sidereal_asc_deg": round(sid_asc, 4),
        "tropical_asc_deg": round(trop_asc, 4),
        "lagna_sign": lagna_sign,
        "lagna_sign_lord": SIGN_LORDS[lagna_sign],
        "lagna_star_lord": lagna_nak["star_lord"],
        "moon_sign": moon_sign_sid,
        "moon_sign_tropical": moon_sign_trop,
        "moon_sign_lord": SIGN_LORDS[moon_sign_sid],
        "moon_star_lord": moon_nak["star_lord"],
        "moon_sidereal_deg": round(moon_sid, 4),
        "planets_tropical": planets,
        "ayanamsa": ayan,
    }


def _moon_conjunct_planets(moon_trop: float, planets: dict[str, float], orb_deg: float = NAK_SPAN_DEG / 4) -> list[str]:
    out = []
    m_sign = sign_index(moon_trop)
    for p, lon in planets.items():
        if p in ("Moon", "Ketu"):
            continue
        if sign_index(lon) == m_sign:
            out.append(p)
        diff = abs((lon - moon_trop + 180) % 360 - 180)
        if diff <= orb_deg:
            out.append(p)
    return sorted(set(out))


def _node_shadow_planets(node: str, planets: dict[str, float], base_rp: set[str]) -> list[str]:
    extras = []
    if node not in planets:
        return extras
    sign_lord = SIGN_LORDS[SIGNS[sign_index(planets[node])]]
    if sign_lord in base_rp:
        extras.append(node)
    return extras


def compute_ruling_planets_full(chart_b: dict, q_weekday: int) -> dict:
    planets = chart_b["planets_tropical"]
    trop_asc = chart_b["tropical_asc_deg"]
    lagna_si = sign_index(trop_asc)
    moon_trop = planets["Moon"]
    moon_si = sign_index(moon_trop)

    rp: list[str] = []
    day_lord = PYTHON_WEEKDAY_TO_VEDIC[q_weekday]
    rp.append(day_lord)
    rp.append(chart_b["lagna_sign_lord"])
    rp.append(chart_b["lagna_star_lord"])

    for p, lon in planets.items():
        if p == "Ketu":
            continue
        if sign_index(lon) == lagna_si:
            rp.append(p)

    for p, lon in planets.items():
        if p in ("Rahu", "Ketu"):
            continue
        if lagna_si in rashi_aspect_targets(sign_index(lon), p):
            rp.append(p)

    rp.append(chart_b["moon_sign_lord"])
    rp.append(chart_b["moon_star_lord"])
    rp.extend(_moon_conjunct_planets(moon_trop, planets))

    for p, lon in planets.items():
        if p in ("Rahu", "Ketu"):
            continue
        if moon_si in rashi_aspect_targets(sign_index(lon), p):
            rp.append(p)

    base = set(rp)
    for node in ("Rahu", "Ketu"):
        rp.extend(_node_shadow_planets(node, planets, base))

    deduped = list(dict.fromkeys(rp))
    return {
        "day_lord": day_lord,
        "lagna_sign_lord": chart_b["lagna_sign_lord"],
        "lagna_star_lord": chart_b["lagna_star_lord"],
        "moon_sign_lord": chart_b["moon_sign_lord"],
        "moon_star_lord": chart_b["moon_star_lord"],
        "all_ruling_planets": deduped,
        "chart_b_lagna_sign": chart_b["lagna_sign"],
        "planets_in_lagna_rasi": sorted(
            p for p, lon in planets.items() if p != "Ketu" and sign_index(lon) == lagna_si
        ),
    }


def topic_list_a_houses(topic: str) -> list[int]:
    if topic in ("disease_cure", "recovery"):
        return [5, 6, 11]
    tb = TOPIC_BHAVAS.get(topic, TOPIC_BHAVAS["general"])
    return sorted(set(tb["favorable"] + [tb["primary"]]))


def kp_promise_verdict(topic: str, chart_a: dict) -> dict:
    tb = TOPIC_BHAVAS.get(topic, TOPIC_BHAVAS["general"])
    primary = tb["primary"]
    cusp = chart_a["cusp_info"][str(primary)]
    sub_lord = cusp["sub_lord"]
    planets = chart_a["planets_tropical"]
    ayan = chart_a["ayanamsa"]
    cusps = chart_a["cusps_tropical"]

    sub_planet = sub_lord
    sub_house = chart_a["planet_houses"].get(sub_planet, 0)
    sub_sid = (planets.get(sub_planet, 0) - ayan) % 360 if sub_planet in planets else 0
    star_lord = get_nakshatra(sub_sid)["star_lord"] if sub_planet in planets else sub_lord

    star_sigs = planet_significations_kp(star_lord, cusps, planets, ayan) if star_lord in planets else set()
    significations = sorted(star_sigs)

    fav = set(tb["favorable"])
    den = set(tb["denying"])
    fav_hits = sorted(set(significations) & fav)
    den_hits = sorted(set(significations) & den)

    if fav_hits and not den_hits:
        verdict, reason = "YES", f"Star-lord {star_lord} signifies favorable {fav_hits}"
    elif den_hits and not fav_hits:
        verdict, reason = "NO", f"Star-lord {star_lord} signifies denying {den_hits}"
    elif fav_hits and den_hits:
        verdict, reason = "CONDITIONAL", f"Mixed: favorable {fav_hits} vs denying {den_hits}"
    else:
        verdict, reason = "CONDITIONAL", f"Star-lord {star_lord} weak house link"

    return {
        "primary_bhava": primary,
        "cusp_sub_lord": sub_lord,
        "cusp_star_lord": cusp["star_lord"],
        "sub_lord_planet": sub_planet,
        "sub_lord_house": sub_house,
        "star_lord": star_lord,
        "significations": significations,
        "fav_hits": fav_hits,
        "den_hits": den_hits,
        "verdict": verdict,
        "reason": reason,
    }


def compute_kp_horary(kp_num: int, jd_ut: float, lat: float, lon: float, topic: str, q_weekday: int) -> dict:
    chart_a = compute_chart_a(kp_num, jd_ut, lat, lon)
    chart_b = compute_chart_b(jd_ut, lat, lon)
    rp = compute_ruling_planets_full(chart_b, q_weekday)
    promise = kp_promise_verdict(topic, chart_a)
    la_houses = topic_list_a_houses(topic)
    list_a = list_a_significators(
        chart_a["cusps_tropical"], chart_a["planets_tropical"], chart_a["ayanamsa"], la_houses,
    )
    list_c = sorted(set(list_a) & set(rp["all_ruling_planets"]))

    kp_meta = dict(chart_a["kp"])
    kp_meta["chart_a"] = True
    kp_meta["promise"] = promise
    kp_meta["list_a"] = list_a
    kp_meta["list_a_houses"] = la_houses
    kp_meta["list_c"] = list_c
    kp_meta["chart_b_lagna_rasi_planets"] = rp["planets_in_lagna_rasi"]

    return {
        "kp_data": kp_meta,
        "chart_a": chart_a,
        "chart_b": chart_b,
        "ruling_planets": rp,
        "promise": promise,
        "list_a": list_a,
        "list_c": list_c,
    }
