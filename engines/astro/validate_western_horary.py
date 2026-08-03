#!/usr/bin/env python3
"""Validate the deterministic Western horary engine against Anthony Louis's book cases.

For each book chart (event data from ``validate_rules_v6_ephemeris.EVENTS``), cast the
chart with Swiss Ephemeris using the book's own house system, run our judgment engine
(``western_horary_report.judge``), and compare the YES/NO lean against the outcome
recorded in ``western-horary-data/rules_v6.json``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import swisseph as swe

sys.path.insert(0, str(Path(__file__).resolve().parent / "western-horary-data"))

import western_horary_rules as R
from western_horary_report import judge
from validate_rules_v6_ephemeris import EVENTS, HOUSE_CODES, NAME_TO_SWE

FLG = swe.FLG_MOSEPH | swe.FLG_SPEED

# Curated traditional quesited-house assignment + a short note per genuine horary case.
# (Event/retrospective/synthetic charts are excluded — they are not yes/no quesited questions.)
CASES = {
    2:  (2,  "Lost object — where is the GameBoy"),
    9:  (5,  "Will I ever have children (Lilly)"),
    11: (2,  "Lost object — missing TV clicker"),
    12: (2,  "Should I buy the computerised test (acquire possession)"),
    15: (2,  "Stolen money — will it be recovered (Lilly)"),
    16: (10, "Should we buy the stained-glass business"),
    17: (7,  "Will I marry"),
    19: (2,  "Will I need to buy a new air conditioner"),
    20: (2,  "Will Luis get the loan (loan = money coming to querent, 2nd house)"),
    21: (6,  "Have you found our cat (small animal)"),
    22: (10, "Will I get the job with Llewellyn"),
    24: (7,  "Should I move to the new office (7th — house of removals)"),
    34: (2,  "Lost object — where are my house keys"),
    39: (7,  "Will I marry Michael"),
    41: (2,  "Lost object — where did I put the medication"),
    43: (5,  "When will my son be toilet trained (child)"),
    44: (10, "Will this book be published (honour/career)"),
    47: (7,  "Will he return"),
    # --- second batch (10 more) ---
    8:  (4,  "Is my house going to burn down (4th — home)"),
    10: (6,  "Would he find a secretary (6th — employees)"),
    18: (7,  "When shall my imprisoned husband be delivered/released"),
    26: (4,  "Should I buy the real estate / Mr B's houses (4th — property)"),
    28: (2,  "Lost object — where are Rachel's missing eyeglasses"),
    35: (11, "Where is Nick (missing friend — 11th house, Louis's revised reading)"),
    36: (7,  "Where is Tommy (missing runaway — 7th house named person)"),
    45: (10, "Will the ad fly / succeed (10th — success)"),
    52: (7,  "Will the marriage happen (7th)"),
    53: (2,  "Lost object — where is John's GameBoy"),
}


def build_chart(ev) -> dict:
    """Construct the precompute_western-shaped chart dict from a book event."""
    jd = ev.jd_ut
    hsys = HOUSE_CODES[ev.house]
    cusps, ascmc = swe.houses(jd, ev.lat, ev.lon, hsys)
    asc, mc = ascmc[0], ascmc[1]
    planets = {}
    for name, pid in NAME_TO_SWE.items():
        xx, _ = swe.calc_ut(jd, pid, FLG)
        lon, sp = xx[0], xx[3]
        planets[name] = {
            "longitude": round(lon, 4), "sign": R.sign_of(lon),
            "deg_in_sign": round(R.deg_in_sign(lon), 4),
            "house": _house_of(lon, cusps), "speed_deg_per_day": round(sp, 4),
            "retrograde": sp < 0,
        }
    sun_h = planets["Sun"]["house"]
    return {
        "meta": {"julian_day_ut": jd, "chart_type": "day" if 7 <= sun_h <= 12 else "night",
                 "lat": ev.lat, "lon": ev.lon, "q_date": "", "q_time_ut_approx": ""},
        "angles": {"ascendant_deg": round(asc, 4), "asc_sign": R.sign_of(asc),
                   "asc_deg_in_sign": round(R.deg_in_sign(asc), 4),
                   "mc_deg": round(mc, 4), "mc_sign": R.sign_of(mc)},
        "cusps": [round(c, 4) for c in cusps],
        "planets": planets,
    }


def _house_of(lon: float, cusps) -> int:
    lon = R.norm360(lon)
    for i in range(12):
        a, b = cusps[i], cusps[(i + 1) % 12]
        if a < b:
            if a <= lon < b:
                return i + 1
        else:
            if lon >= a or lon < b:
                return i + 1
    return 1


def lean(score: float) -> str:
    if score >= 0.6:
        return "YES"
    if score <= -0.6:
        return "NO"
    return "MIXED"


def main() -> None:
    rows = {c["case_id"]: c for c in json.loads(
        (Path(__file__).resolve().parent / "western-horary-data" / "rules_v6.json").read_text())}

    print(f"{'Case':>4} {'Book':>4} {'Engine':>6} {'Match':>6}  Verdict / question")
    print("-" * 100)
    hits = total = 0
    mixed_ok = 0
    details = []
    for cid in sorted(CASES):
        if cid not in EVENTS or cid not in rows:
            continue
        qh, note = CASES[cid]
        expected = rows[cid].get("result", "")
        data = build_chart(EVENTS[cid])
        j = judge(data, note, qh)
        eng = lean(j["score"])
        # YES/NO strict match; MIXED counts as a soft (non-contradicting) result.
        if eng == expected:
            mark = "OK"; hits += 1
        elif eng == "MIXED":
            mark = "~soft"; mixed_ok += 1
        else:
            mark = "MISS"
        total += 1
        print(f"{cid:>4} {expected:>4} {eng:>6} {mark:>6}  {j['verdict']} ({j['confidence']}, {j['score']:+.1f}) — {note}")
        details.append((cid, expected, eng, mark, j, note))

    print("-" * 100)
    print(f"Strict matches: {hits}/{total}  |  soft (engine MIXED, not contradicting): {mixed_ok}  |  "
          f"hard misses: {total - hits - mixed_ok}")

    # Show reasoning for hard misses to guide rule tuning.
    print("\n=== Hard misses — engine reasoning ===")
    for cid, exp, eng, mark, j, note in details:
        if mark == "MISS":
            print(f"\nCase {cid} (book {exp}, engine {eng}) — {note}")
            print(f"  querent {j['asc_lord']} {j['asc_ed']['score']:+d} | quesited {j['q_lord']} {j['q_ed']['score']:+d} "
                  f"| moon_void={j['moon_void']}")
            for r in j["reasons"]:
                print(f"    - {r}")


if __name__ == "__main__":
    main()
