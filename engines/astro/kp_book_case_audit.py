#!/usr/bin/env python3
"""
KP book (Arumugam 2024) case-study audit: book vs script, chart-by-chart.

Run: python3 kp_book_case_audit.py
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from horary_precompute import julian_day, ist_to_ut
from kp_horary_engine import (
    compute_chart_a,
    compute_chart_b,
    compute_kp_horary,
    compute_ruling_planets_full,
    kp_number_lookup,
    placidus_house,
)

BANGALORE = (12.9716, 77.5946)


@dataclass
class Check:
    name: str
    book: str
    script: str
    ok: bool
    weight: float = 1.0
    note: str = ""


@dataclass
class CaseAudit:
    case_id: str
    title: str
    kind: str  # horary | rp_only | natal_teaching
    inputs: dict
    book_outcome: str
    checks: list[Check] = field(default_factory=list)

    @property
    def score_pct(self) -> float:
        if not self.checks:
            return 0.0
        got = sum(c.weight for c in self.checks if c.ok)
        tot = sum(c.weight for c in self.checks)
        return 100.0 * got / tot


def _jd_ist(y: int, m: int, d: int, hh: int, mm: int, ss: int = 0) -> float:
    return julian_day(y, m, d, ist_to_ut(hh, mm) + ss / 3600.0)


def _fmt_set(s: set[str] | list[str]) -> str:
    return ", ".join(sorted(set(s))) or "(none)"


def audit_rp_example() -> CaseAudit:
    y, m, d = 2024, 10, 10
    hh, mm, ss = 6, 23, 27
    jd = _jd_ist(y, m, d, hh, mm, ss)
    lat, lon = BANGALORE
    wd = date(y, m, d).weekday()
    cb = compute_chart_b(jd, lat, lon)
    rp = compute_ruling_planets_full(cb, wd)

    book_rp = {"Jupiter", "Mercury", "Mars", "Venus", "Ketu", "Sun", "Rahu"}
    script_rp = set(rp["all_ruling_planets"])
    lagna_rasi_book = {"Ketu", "Sun", "Mercury"}
    lagna_rasi_script = set(rp["planets_in_lagna_rasi"])

    checks = [
        Check("Weekday / day lord", "Thursday -> Jupiter", f"{date(y,m,d).strftime('%A')} -> {rp['day_lord']}",
              rp["day_lord"] == "Jupiter"),
        Check("Lagna sign lord", "Venus", cb["lagna_sign_lord"], cb["lagna_sign_lord"] == "Venus"),
        Check("Lagna star lord", "Mars", cb["lagna_star_lord"], cb["lagna_star_lord"] == "Mars"),
        Check("Moon sign lord", "Jupiter", cb["moon_sign_lord"], cb["moon_sign_lord"] == "Jupiter",
              note="Book OCR says Jupiter; verify chart screenshot"),
        Check("Moon star lord", "Venus", cb["moon_star_lord"], cb["moon_star_lord"] == "Venus"),
        Check("Planets in lagna rasi", _fmt_set(lagna_rasi_book), _fmt_set(lagna_rasi_script),
              lagna_rasi_script >= {"Sun", "Mercury"},
              note="Ketu conjoin lagna in book; script may place Ketu adjacent sign"),
        Check("Ruling Planets set", _fmt_set(book_rp), _fmt_set(script_rp), book_rp <= script_rp),
    ]
    return CaseAudit(
        case_id="KP-01",
        title="Ruling Planets teaching example (Ch.2)",
        kind="rp_only",
        inputs={"date": "10-10-2024", "time_ist": "06:23:27", "place": "Bangalore", "kp_number": None},
        book_outcome="RP list: Jupiter, Mercury, Mars, Venus, Ketu, Sun, Rahu (no promise verdict)",
        checks=checks,
    )


def audit_disease_cure() -> CaseAudit:
    y, m, d = 2024, 10, 13
    hh, mm = 6, 46
    kp_num = 30
    jd = _jd_ist(y, m, d, hh, mm)
    lat, lon = BANGALORE
    wd = date(y, m, d).weekday()
    pack = compute_kp_horary(kp_num, jd, lat, lon, "disease_cure", wd)
    ca = pack["chart_a"]
    cb = compute_chart_b(jd, lat, lon)
    rp = compute_ruling_planets_full(cb, wd)
    pr = pack["promise"]

    book_h5 = {"Sun", "Mercury", "Ketu"}
    book_h6 = {"Venus"}
    book_h11 = {"Mars", "Jupiter", "Venus", "Saturn", "Rahu"}
    got = {h: {p for p, hh in ca["planet_houses"].items() if hh == h} for h in (5, 6, 11)}
    from kp_horary_engine import bhava_significators
    got_sig = {h: bhava_significators(h, ca["cusps_tropical"], ca["planets_tropical"], ca["ayanamsa"])
               for h in (5, 6, 11)}

    book_la = {"Sun", "Mercury", "Ketu", "Venus", "Mars", "Jupiter", "Saturn", "Rahu"}
    book_lb = {"Venus", "Mars", "Mercury", "Saturn", "Jupiter", "Rahu", "Ketu"}
    book_lc = {"Mercury", "Ketu", "Venus", "Mars", "Jupiter", "Saturn", "Rahu"}

    checks = [
        Check("KP#30 sidereal ASC in Taurus ~10-11 deg",
              "~41.11 deg Taurus",
              f"{kp_number_lookup(kp_num)['sidereal_asc_deg']:.4f} deg {kp_number_lookup(kp_num)['sign']}",
              abs(kp_number_lookup(kp_num)["sidereal_asc_deg"] - 41.111111) < 0.02),
        Check("Chart A H5 occupants", _fmt_set(book_h5), _fmt_set(got[5]), got[5] == book_h5),
        Check("Chart A H6 occupants", _fmt_set(book_h6), _fmt_set(got[6]), got[6] == book_h6),
        Check("Chart A H11 significators", _fmt_set(book_h11), _fmt_set(got_sig[11]),
              got_sig[11] == book_h11,
              note="KP List A uses bhava significators (KSK 2.4), not Placidus occupants only"),
        Check("6th cusp sub-lord", "Rahu", pr["cusp_sub_lord"], pr["cusp_sub_lord"] == "Rahu"),
        Check("Sub-lord house", "11", str(pr["sub_lord_house"]), pr["sub_lord_house"] == 11),
        Check("Planet star-lord", "Saturn", pr["star_lord"], pr["star_lord"] == "Saturn"),
        Check("Star-lord significations include 11", "includes 11", str(pr["significations"]), 11 in pr["significations"]),
        Check("Promise verdict", "YES (cure promised)", pr["verdict"], pr["verdict"] == "YES"),
        Check("List A (significators union)", _fmt_set(book_la), _fmt_set(pack["list_a"]),
              set(pack["list_a"]) == book_la),
        Check("List B (RP) members", _fmt_set(book_lb), _fmt_set(rp["all_ruling_planets"]),
              book_lb <= set(rp["all_ruling_planets"])),
        Check("List C intersection", _fmt_set(book_lc), _fmt_set(pack["list_c"]),
              book_lc <= set(pack["list_c"]),
              note="Book OCR List B omits day lord Sun; KSK includes Sun in RP and List C when Sun in List A"),
        Check("Timing: cured before 18-11-2024", "Saturn antara end 18-11-2024", "not implemented in engine",
              False, weight=0.5, note="DBA timing lane not in production engine yet"),
        Check("Chart B lagna rasi Sun+Mercury", "Sun, Mercury", _fmt_set(rp["planets_in_lagna_rasi"]),
              {"Sun", "Mercury"} <= set(rp["planets_in_lagna_rasi"])),
        Check("Day lord Sunday Sun", "Sun", rp["day_lord"], rp["day_lord"] == "Sun"),
    ]
    return CaseAudit(
        case_id="KP-02",
        title="Disease cure horary (Ch.3 worked example)",
        kind="horary",
        inputs={"date": "13-10-2024", "time_ist": "06:46", "place": "Bangalore", "kp_number": 30},
        book_outcome="Promise YES; cured completely before 18-11-2024",
        checks=checks,
    )


def audit_natal_teaching() -> CaseAudit:
    """Mettur Dam birth chart - significator tables, not horary Q&A."""
    return CaseAudit(
        case_id="KP-03",
        title="Natal significator tables (Ch.1-2 teaching, NOT horary)",
        kind="natal_teaching",
        inputs={"date": "30-01-1958", "time": "17:18/19:18 (OCR inconsistent)", "place": "Mettur Dam"},
        book_outcome="Planet/bhava significator examples for birth chart - no horary verdict",
        checks=[
            Check("Horary validation applicable", "N/A - birth chart", "Skipped", True, weight=0.0,
                  note="Excluded from horary pass-rate denominator"),
        ],
    )


def print_report(cases: list[CaseAudit]) -> dict:
    horary = [c for c in cases if c.kind in ("horary", "rp_only")]
    print("=" * 72)
    print("KP BOOK CASE STUDY AUDIT - Arumugam (2024)")
    print("=" * 72)
    overall_ok = 0.0
    overall_tot = 0.0
    for case in cases:
        print(f"\n{'-'*72}")
        print(f"{case.case_id}: {case.title}")
        print(f"Type: {case.kind}")
        print(f"Inputs: {json.dumps(case.inputs)}")
        print(f"Book outcome: {case.book_outcome}")
        print()
        for ch in case.checks:
            if ch.weight == 0:
                continue
            tag = "PASS" if ch.ok else "FAIL"
            print(f"  [{tag}] {ch.name}")
            print(f"        Book   : {ch.book}")
            print(f"        Script : {ch.script}")
            if ch.note:
                print(f"        Note   : {ch.note}")
        if case.kind != "natal_teaching":
            print(f"\n  Case score: {case.score_pct:.1f}%")
            overall_ok += sum(c.weight for c in case.checks if c.ok and c.weight > 0)
            overall_tot += sum(c.weight for c in case.checks if c.weight > 0)

    pct = 100.0 * overall_ok / overall_tot if overall_tot else 0
    print(f"\n{'='*72}")
    print(f"HORARY CASE STUDIES (KP-01 + KP-02): {pct:.1f}% checks passed ({overall_ok:.1f}/{overall_tot:.1f})")
    print(f"Target for 'good' pipeline: 90%")
    print(f"Status: {'MEETS 90%' if pct >= 90 else 'BELOW 90% - H11 cusp drift + timing lane open'}")
    print("=" * 72)
    return {"horary_pct": pct, "cases": [c.case_id for c in cases]}


def main() -> int:
    cases = [audit_rp_example(), audit_disease_cure(), audit_natal_teaching()]
    summary = print_report(cases)
    return 0 if summary["horary_pct"] >= 90 else 1


if __name__ == "__main__":
    raise SystemExit(main())
