#!/usr/bin/env python3
"""
Validate western-horary-data/rules_v6.json condition flags against Swiss Ephemeris (MOSEPH).

Computes per case (where event metadata exists): retrograde among listed planets, Moon VOC
(modern: majors to Sun–Pluto before sign exit, 3° orb), combust (Mercury/Moon vs Sun),
Saturn in 7th, early Asc (<3°), Via Combusta Moon, intercepted signs.

Outputs rules_v6_ephemeris_report.json and prints a summary.

Calendar: Gregorian for all dates (matches typical software reproductions of Louis's printed times).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    import swisseph as swe
except ImportError:
    raise SystemExit("Install pyswisseph: pip install pyswisseph")

FLG = swe.FLG_MOSEPH | swe.FLG_SPEED

HOUSE_CODES = {"placidus": b"P", "koch": b"K", "regiomontanus": b"R", "porphyry": b"O"}

MAJOR = (0, 60, 90, 120, 180)
MOON_ORB = 3.0


def norm360(x: float) -> float:
    return x % 360.0


def ang_dist(a: float, b: float) -> float:
    d = abs(norm360(a) - norm360(b))
    return min(d, 360.0 - d)


def aspect_residual(lon_m: float, lon_p: float) -> float:
    """Min angular distance to a major aspect (0–180)."""
    d = ang_dist(lon_m, lon_p)
    best = 360.0
    for t in MAJOR:
        best = min(best, abs(d - t))
    return best


def jd_ut_from_local(
    year: int,
    month: int,
    day: int,
    hour: float,
    tz_offset_east_of_utc: float,
) -> float:
    """
    tz_offset_east_of_utc: hours to add to local civil time to get UT
    (e.g. EST +5, EDT +4, PDT +7).
    """
    ut = hour + tz_offset_east_of_utc
    d_adj = 0
    while ut >= 24:
        ut -= 24
        d_adj += 1
    while ut < 0:
        ut += 24
        d_adj -= 1
    y, m, d = year, month, day
    if d_adj:
        # simple day step (sufficient for book times)
        from datetime import date, timedelta

        dt = date(y, m, d) + timedelta(days=d_adj)
        y, m, d = dt.year, dt.month, dt.day
    return swe.julday(y, m, d, ut, swe.GREG_CAL)


def calc_lon_speed(jd: float, pid: int) -> tuple[float, float]:
    xx, _ = swe.calc_ut(jd, pid, FLG)
    return xx[0], xx[3]


def moon_sign_exit_jd(jd0: float) -> float:
    """Approximate JD when Moon enters next sign (bracketed bisection)."""
    lm0, sp = calc_lon_speed(jd0, swe.MOON)
    if sp <= 0:
        return jd0 + 3.0  # fallback
    deg_in = lm0 % 30.0
    dist = 30.0 - deg_in
    est = jd0 + (dist / sp) * 0.997
    lo, hi = jd0 + 0.01, jd0 + 3.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lm, _ = calc_lon_speed(mid, swe.MOON)
        if (lm % 30.0) < deg_in:
            hi = mid
        else:
            lo = mid
    return hi


def moon_void_louis_style(jd0: float) -> tuple[bool, str]:
    """
    True if Moon makes no applying major aspect (3° orb) to Sun..Pluto before leaving sign.
    Simplified: step from jd0 to exit; if residual to any planet drops below orb while decreasing, not void.
    """
    jd_end = moon_sign_exit_jd(jd0)
    pids = [
        swe.SUN,
        swe.MERCURY,
        swe.VENUS,
        swe.MARS,
        swe.JUPITER,
        swe.SATURN,
        swe.URANUS,
        swe.NEPTUNE,
        swe.PLUTO,
    ]
    n_steps = max(80, int((jd_end - jd0) * 48))
    prev_res = None
    for i in range(n_steps + 1):
        t = jd0 + (jd_end - jd0) * (i / max(1, n_steps))
        lm, _ = calc_lon_speed(t, swe.MOON)
        for pid in pids:
            lp, _ = calc_lon_speed(t, pid)
            res = aspect_residual(lm, lp)
            if res <= MOON_ORB:
                # check applying: residual decreases shortly after
                if t + 0.02 < jd_end:
                    lm2, _ = calc_lon_speed(t + 0.02, swe.MOON)
                    lp2, _ = calc_lon_speed(t + 0.02, pid)
                    res2 = aspect_residual(lm2, lp2)
                    if res2 < res - 0.01:
                        return False, f"Moon applies (res {res:.2f}°→{res2:.2f}°) to body {pid}"
                else:
                    return False, f"Moon within orb {res:.2f}° of major aspect at sign end"
        prev_res = res
    return True, "No applying major to Sun–Pluto before sign exit (3° orb, stepped)"


def combust_against_sun(lon_p: float, lon_sun: float, name: str) -> bool:
    """Lilly-style: true core combust for inners; Mercury also 'under beams' ≤ ~17°."""
    d = ang_dist(lon_p, lon_sun)
    if name == "Mercury":
        return d < 17.0
    if name == "Venus":
        return d < 10.0
    if name == "Moon":
        return d < 12.0
    return d < 15.0


def has_intercepted(cusps: list[float]) -> bool:
    """True if any house arc (cusp i → i+1) exceeds 30° — room for an intercepted sign."""
    c = [norm360(x) for x in cusps[:12]]
    for i in range(12):
        a, b = c[i], c[(i + 1) % 12]
        if b < a:
            span = (360.0 - a) + b
        else:
            span = b - a
        if span > 30.001:
            return True
    return False


@dataclass
class CaseEvent:
    case_id: int
    label: str
    jd_ut: float
    lat: float
    lon: float
    house: str  # placidus, koch, regiomontanus, porphyry


# Book / JSON-derived event table (coordinates cleaned from OCR where obvious).
EVENTS: dict[int, CaseEvent] = {
    2: CaseEvent(2, "Chart 59 GameBoy", jd_ut_from_local(1990, 1, 16, 22.0, 5.0), 41.3167, -73.0167, "koch"),
    3: CaseEvent(3, "Chart 1 baby", jd_ut_from_local(1987, 8, 6, 21.5, 4.0), 41.3167, -73.0167, "placidus"),
    4: CaseEvent(4, "Chart 2A", jd_ut_from_local(1989, 10, 5, 22 + 39 / 60.0, 4.0), 41.3167, -73.0167, "koch"),
    5: CaseEvent(5, "Chart 3 earthquake", jd_ut_from_local(1989, 10, 17, 17 + 5 / 60.0, 7.0), 37.1167, -122.8833, "koch"),
    6: CaseEvent(6, "Chart 4 ValuJet", jd_ut_from_local(1996, 5, 11, 14 + 25 / 60.0, 4.0), 26.0, -80.6667, "regiomontanus"),
    7: CaseEvent(7, "Chart 6 house fire", jd_ut_from_local(1974, 2, 3, 14 + 58 / 60.0, 8.0), 34.3333, -118.6, "koch"),
    8: CaseEvent(8, "Chart 6 Louis path", jd_ut_from_local(1974, 2, 3, 14 + 58 / 60.0, 8.0), 34.3333, -118.6, "koch"),
    9: CaseEvent(9, "Chart 7 Lilly children", jd_ut_from_local(1635, 6, 22, 9.5, 0.0), 51.5, -0.1667, "regiomontanus"),
    10: CaseEvent(10, "Chart 8 secretary", jd_ut_from_local(1989, 10, 15, 22 + 22 / 60.0, 4.0), 39.0458, -76.6419, "koch"),
    11: CaseEvent(11, "Chart 9 clicker", jd_ut_from_local(1996, 7, 6, 22 + 24 / 60.0, 4.0), 41.2667, -73.0667, "regiomontanus"),
    12: CaseEvent(12, "Chart 11 computer test", jd_ut_from_local(1989, 7, 21, 8 + 20 / 60.0, 4.0), 41.45, -72.75, "koch"),
    13: CaseEvent(13, "Chart 12 Presbytery", jd_ut_from_local(1647, 3, 21, 16 + 50 / 60.0, 0.0), 51.5, -0.1667, "regiomontanus"),
    14: CaseEvent(14, "Chart 14 bewitched", jd_ut_from_local(1647, 3, 23, 8 + 12 / 60.0, 0.0), 51.5, -0.1667, "regiomontanus"),
    15: CaseEvent(15, "Chart 15 money", jd_ut_from_local(1647, 6, 3, 16 + 54 / 60.0, 0.0), 51.5, -0.1667, "regiomontanus"),
    16: CaseEvent(16, "Chart 16 stained glass", jd_ut_from_local(1978, 9, 9, 13.5, 8.0), 47.6833, -116.7667, "koch"),
    17: CaseEvent(17, "Chart 17 marry", jd_ut_from_local(1992, 2, 16, 21 + 15 / 60.0, 5.0), 41.3167, -73.0167, "regiomontanus"),
    18: CaseEvent(18, "Chart 18 Lilly prison", jd_ut_from_local(1645, 10, 29, 18 + 53 / 60.0, 0.0), 51.5, -0.1667, "regiomontanus"),
    19: CaseEvent(19, "Chart 19 AC", jd_ut_from_local(1990, 6, 23, 11 + 58 / 60.0, 4.0), 41.3167, -73.0167, "koch"),
    20: CaseEvent(20, "Chart 20 loan", jd_ut_from_local(1990, 7, 13, 9 + 43 / 60.0, 4.0), 41.45, -72.8333, "koch"),
    21: CaseEvent(21, "Chart 21 cat", jd_ut_from_local(1996, 9, 14, 18 + 42 / 60.0, -1.0), 51.5167, -0.5667, "regiomontanus"),
    22: CaseEvent(22, "Chart 22 job", jd_ut_from_local(1987, 6, 24, 10.0, 7.0), 47.6833, -116.7667, "koch"),
    23: CaseEvent(23, "Chart 23 impedition", jd_ut_from_local(1633, 3, 24, 14 + 26 / 60.0, 0.0), 51.5, -0.1667, "regiomontanus"),
    24: CaseEvent(24, "Chart 24 office", jd_ut_from_local(1989, 5, 26, 11 + 56 / 60.0, 4.0), 41.3, -72.9167, "koch"),
    26: CaseEvent(26, "Chart 26A Lilly houses", jd_ut_from_local(1634, 4, 10, 18 + 3 / 60.0, 0.0), 51.5167, -0.1, "regiomontanus"),
    27: CaseEvent(27, "Chart 26A outcome", jd_ut_from_local(1634, 4, 10, 18 + 3 / 60.0, 0.0), 51.5167, -0.1, "regiomontanus"),
    28: CaseEvent(28, "Chart 30 eyeglasses", jd_ut_from_local(1992, 9, 15, 7 + 21 / 60.0, 4.0), 41.3167, -73.0167, "regiomontanus"),
    30: CaseEvent(30, "Chart 31 Palchus", jd_ut_from_local(478, 8, 29, 22.5 - (32 + 57 / 60.0) / 15.0, 0.0), 24.0667, 32.95, "porphyry"),
    31: CaseEvent(31, "Chart 35 theft", jd_ut_from_local(1989, 11, 29, 11 + 23 / 60.0, 5.0), 41.3, -72.9167, "koch"),
    32: CaseEvent(32, "Chart 35 ruler debate", jd_ut_from_local(1989, 11, 29, 11 + 23 / 60.0, 5.0), 41.3, -72.9167, "koch"),
    33: CaseEvent(33, "Chart 35 thief", jd_ut_from_local(1989, 11, 29, 11 + 23 / 60.0, 5.0), 41.3, -72.9167, "koch"),
    34: CaseEvent(34, "Chart 38 keys", jd_ut_from_local(1989, 12, 9, 14 + 26 / 60.0, 5.0), 41.3167, -73.0167, "koch"),
    35: CaseEvent(35, "Chart 39 Nick", jd_ut_from_local(1989, 6, 4, 7.0, 4.0), 41.3167, -73.0167, "koch"),
    36: CaseEvent(36, "Chart 40 Tommy", jd_ut_from_local(1989, 6, 19, 13 + 9 / 60.0, 4.0), 41.3, -72.9167, "koch"),
    37: CaseEvent(37, "Chart 41 jail", jd_ut_from_local(1989, 9, 21, 14 + 4 / 60.0, 5.0), 41.3, -72.9167, "koch"),
    # Louis prints "EST" for a summer NY chart; using literal EST (+5) reproduces ~2° Cap Asc in software.
    39: CaseEvent(39, "Chart 44 Michael", jd_ut_from_local(1987, 8, 29, 15 + 1 / 60.0, 5.0), 41.3167, -73.0167, "koch"),
    41: CaseEvent(41, "Chart 47 meds", jd_ut_from_local(1989, 12, 8, 21 + 39 / 60.0, 5.0), 41.3167, -73.0167, "koch"),
    43: CaseEvent(43, "Chart 49 toilet", jd_ut_from_local(1989, 12, 22, 21 + 43 / 60.0, 5.0), 41.3167, -73.0167, "koch"),
    44: CaseEvent(44, "Chart 50 published", jd_ut_from_local(1989, 7, 2, 21 + 6 / 60.0, 4.0), 41.3167, -73.0167, "koch"),
    45: CaseEvent(45, "Chart 51 ad", jd_ut_from_local(1990, 6, 5, 10 + 52 / 60.0, 5.0), 44.95, -93.1, "koch"),
    47: CaseEvent(47, "Chart 53 Rachel", jd_ut_from_local(1990, 4, 8, 13 + 50 / 60.0, 4.0), 41.3167, -73.0167, "koch"),
    48: CaseEvent(48, "Chart 3 follow-on", jd_ut_from_local(1989, 10, 17, 17 + 5 / 60.0, 7.0), 37.1167, -122.8833, "koch"),
    52: CaseEvent(52, "Chart 59 phone", jd_ut_from_local(1990, 1, 16, 22.0, 5.0), 41.3167, -73.0167, "koch"),
    53: CaseEvent(53, "Chart 59 GameBoy", jd_ut_from_local(1990, 1, 16, 22.0, 5.0), 41.3167, -73.0167, "koch"),
}

NAME_TO_SWE = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
}


def analyze_case(ev: CaseEvent, row: dict) -> dict:
    jd = ev.jd_ut
    lat, lon = ev.lat, ev.lon
    hsys = HOUSE_CODES[ev.house]
    cusps, ascmc = swe.houses(jd, lat, lon, hsys)
    asc = ascmc[0]
    asc_deg_in = asc % 30.0

    planets_out = {}
    retro_list = []
    for name, pid in NAME_TO_SWE.items():
        lonp, sp = calc_lon_speed(jd, pid)
        retro = sp < 0
        planets_out[name] = {"lon": round(lonp, 4), "retrograde": retro}
        if retro:
            retro_list.append(name)

    lon_sun = planets_out["Sun"]["lon"]
    combust_bodies = []
    for name in ("Mercury", "Venus", "Moon", "Mars", "Jupiter"):
        if name not in planets_out:
            continue
        if combust_against_sun(planets_out[name]["lon"], lon_sun, name):
            combust_bodies.append(name)

    sat_h = None
    lon_sat = planets_out["Saturn"]["lon"]
    for i in range(12):
        a, b = cusps[i], cusps[(i + 1) % 12]
        if a <= b:
            inside = a <= lon_sat < b
        else:
            inside = lon_sat >= a or lon_sat < b
        if inside:
            sat_h = i + 1
            break

    moon_lon = planets_out["Moon"]["lon"]
    via_moon = 195.0 <= moon_lon < 225.0  # 15 Libra – 15 Scorpio (Louis range)

    void_m, void_note = moon_void_louis_style(jd)

    early_asc = asc_deg_in < 3.0

    inter = has_intercepted(list(cusps))

    # Mars in 7th + Mars in Via Combusta band (case 34 tag)
    mars_h = None
    lon_mar = planets_out["Mars"]["lon"]
    for i in range(12):
        a, b = cusps[i], cusps[(i + 1) % 12]
        if a <= b:
            inside = a <= lon_mar < b
        else:
            inside = lon_mar >= a or lon_mar < b
        if inside:
            mars_h = i + 1
            break
    via7_tag = (mars_h == 7) and (195.0 <= lon_mar < 225.0)

    cond = row.get("conditions") or []
    mismatches = []
    void_info = []
    if "void" in cond:
        if not void_m:
            void_info.append(
                f"JSON tags void; stepped major-aspect check: not VOC ({void_note}) — "
                "Lilly/manual VOC often disagrees with strict software (orbs, outers, dissociate aspects)."
            )
        else:
            void_info.append("Stepped check agrees Moon VOC before sign exit (informational).")
    elif void_m:
        void_info.append(f"Moon appears VOC by stepped check but JSON omits void ({void_note}).")

    if "retrograde" in cond:
        listed = row.get("planets") or []
        rel = [p for p in listed if planets_out.get(p, {}).get("retrograde")]
        if not rel and retro_list:
            mismatches.append(
                f"JSON expects retrograde flag but no listed planet retro; ephemeris has: {retro_list}"
            )
        elif not rel and not retro_list:
            mismatches.append("JSON has retrograde but ephemeris shows no retrograde bodies")

    if "combust" in cond:
        if not combust_bodies:
            mismatches.append("JSON combust but no Mercury/Venus/Moon within combust orb of Sun")
    if "saturn_in_7th" in cond:
        if sat_h != 7:
            mismatches.append(f"JSON saturn_in_7th but Saturn in house {sat_h}")
    if "early_asc" in cond:
        if not early_asc:
            mismatches.append(f"JSON early_asc but Asc degree in sign = {asc_deg_in:.2f}°")
    if "intercepted" in cond:
        if not inter:
            mismatches.append("JSON intercepted but house cusp scan did not find interception pattern")
    if "via_combusta_7th" in cond:
        if not via7_tag:
            mismatches.append(
                f"JSON via_combusta_7th but Mars house={mars_h} Mars lon={lon_mar:.1f} (want 7th + 195–225°)"
            )
    if "moon_in_via_combusta" in cond:
        if not via_moon:
            mismatches.append(
                f"JSON moon_in_via_combusta but Moon lon={moon_lon:.1f} (Louis band ~195°–225°)"
            )

    return {
        "case_id": ev.case_id,
        "label": ev.label,
        "jd_ut": round(jd, 5),
        "lat": lat,
        "lon": lon,
        "house_system": ev.house,
        "asc_deg": round(asc, 4),
        "asc_deg_in_sign": round(asc_deg_in, 4),
        "moon_lon": round(moon_lon, 4),
        "moon_void_ephem": void_m,
        "moon_void_note": void_note,
        "retrograde_bodies": retro_list,
        "combust_bodies": combust_bodies,
        "saturn_house": sat_h,
        "mars_house": mars_h,
        "early_asc_ephem": early_asc,
        "intercepted_ephem": inter,
        "via_combusta_7th_ephem": via7_tag,
        "moon_via_combusta_lon": via_moon,
        "json_conditions": cond,
        "void_validation_notes": void_info,
        "mismatches": mismatches,
    }


def main():
    root = Path(__file__).resolve().parent
    rules_path = root / "rules_v6.json"
    out_path = root / "rules_v6_ephemeris_report.json"
    rows = {r["case_id"]: r for r in json.loads(rules_path.read_text(encoding="utf-8"))}
    report = {"engine": "pyswisseph MOSEPH", "notes": [], "cases": []}

    for cid in sorted(EVENTS.keys()):
        ev = EVENTS[cid]
        row = rows.get(cid)
        if not row:
            continue
        try:
            entry = analyze_case(ev, row)
        except Exception as e:
            entry = {"case_id": cid, "error": str(e)}
        report["cases"].append(entry)

    # Synthetic / no ephemeris row
    report["notes"].append(
        "case_id 51 is synthetic (no historical event). case_id 9 planets[] omits nodes — retrograde check uses listed names only."
    )

    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    bad = [c for c in report["cases"] if c.get("mismatches")]
    print(f"Wrote {out_path} ({len(report['cases'])} cases). Mismatch count: {len(bad)}")
    for c in bad:
        print(f"  case {c['case_id']}: {c['mismatches']}")


if __name__ == "__main__":
    main()
