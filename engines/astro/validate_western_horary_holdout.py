#!/usr/bin/env python3
"""HELD-OUT validation: 10 NEW Anthony Louis charts that were never used to tune the
engine's rules. Chart data is taken verbatim from the book's chart headers; the expected
result is the book's stated outcome. This tests whether the confirmed book rules
generalise — not whether they were curve-fitted.
"""
from __future__ import annotations

import sys
from pathlib import Path

import swisseph as swe

sys.path.insert(0, str(Path(__file__).resolve().parent / "western-horary-data"))

import western_horary_rules as R
from western_horary_report import judge
from validate_rules_v6_ephemeris import (EVENTS, HOUSE_CODES, NAME_TO_SWE,
                                         CaseEvent, jd_ut_from_local)
from validate_western_horary import build_chart, lean

# Charts taken directly from the book headers (date, local time, tz-west, lat, lon, hsys).
NEW = {
    "Ch29 Missing kitten":    (CaseEvent(290, "", jd_ut_from_local(1994, 1, 13, 20 + 24/60, 5.0), 41.3167, -73.0167, "regiomontanus"), 6,  "YES", "lost pet — found next evening"),
    "Ch33 Watch & ring":      (CaseEvent(330, "", jd_ut_from_local(1989, 8, 8, 6 + 49/60, 5.0), 41.3167, -73.0167, "koch"), 2,  "YES", "lost valuables — were at home"),
    "Ch36 Eyeglass case":     (CaseEvent(360, "", jd_ut_from_local(1989, 9, 10, 9 + 24/60, 5.0), 41.3167, -73.0167, "koch"), 2,  "YES", "lost case — found (Scorpio 3° rising)"),
    "Ch57 Auditorium keys":   (CaseEvent(570, "", jd_ut_from_local(1993, 4, 20, 9 + 39/60, 5.0), 41.65, -85.00, "koch"), 2,  "YES", "lost keys — recovered"),
    "Ch58 Missing orthodont": (CaseEvent(580, "", jd_ut_from_local(1992, 10, 5, 18.0, 4.0), 41.2667, -73.0667, "regiomontanus"), 7,  "YES", "missing person — was located"),
    "Ch42 Will baby live":    (CaseEvent(420, "", jd_ut_from_local(1989, 9, 1, 17 + 54/60, 5.0), 41.3167, -73.0167, "koch"), 5,  "NO",  "Mercury(baby) square Saturn(death) — baby died"),
}
# Charts already present in the ephemeris EVENTS table but NOT used to tune the rules.
FROM_EVENTS = {
    7:  (4,  "NO",  "Will my house burn down — it did not"),
    14: (12, "NO",  "If bewitched — not bewitched (Lilly)"),
    30: (2,  "YES", "Palchus — stolen linen recovered"),
    37: (12, "YES", "Will I go to jail (book outcome)"),
}


def run():
    rows = []
    print(f"{'Chart':<26} {'Book':>4} {'Engine':>6} {'Match':>6}  Verdict")
    print("-" * 90)
    hits = soft = miss = 0
    for name, (ev, qh, expected, note) in NEW.items():
        d = build_chart(ev)
        j = judge(d, note, qh)
        eng = lean(j["score"])
        mark = "OK" if eng == expected else ("~soft" if eng == "MIXED" else "MISS")
        hits += eng == expected; soft += (eng == "MIXED" and eng != expected); miss += (mark == "MISS")
        print(f"{name:<26} {expected:>4} {eng:>6} {mark:>6}  {j['verdict']} ({j['score']:+.1f}) — {note}")
        rows.append((name, expected, eng, mark, j, note))
    for cid, (qh, expected, note) in FROM_EVENTS.items():
        d = build_chart(EVENTS[cid])
        j = judge(d, note, qh)
        eng = lean(j["score"])
        mark = "OK" if eng == expected else ("~soft" if eng == "MIXED" else "MISS")
        hits += eng == expected; soft += (eng == "MIXED" and eng != expected); miss += (mark == "MISS")
        print(f"{('Ch case ' + str(cid) + ' ' + note[:14]):<26} {expected:>4} {eng:>6} {mark:>6}  {j['verdict']} ({j['score']:+.1f}) — {note}")
        rows.append((f"case{cid}", expected, eng, mark, j, note))

    total = len(rows)
    print("-" * 90)
    print(f"Exact matches: {hits}/{total}  |  soft (engine MIXED, not contradicting): {soft}  |  hard misses: {miss}")
    print("\n=== reasoning for non-exact ===")
    for name, exp, eng, mark, j, note in rows:
        if mark != "OK":
            print(f"\n{name} (book {exp}, engine {eng} {j['score']:+.2f}) asc_lord={j['asc_lord']} q_lord={j['q_lord']}")
            for r in j["reasons"]:
                print("   -", r)


if __name__ == "__main__":
    run()
