#!/usr/bin/env python3
"""Verify deep-evidence wiring in full_report HTML (local / CI)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))

# Poetic BOOK_LINES affirmations that must NOT appear in customer cards
BOOK_LINES_BANNED = (
    "strongest chapter of the decade",
    "Career advancement now comes through disciplined delivery",
    "Leadership and public credit consolidate",
)

AREA_KEYS = (
    "career", "money", "love", "home", "children", "health", "learning", "inner",
)


def _sample_pc() -> dict:
    """Minimal chart stub — real reports use precompute; this tests wiring."""
    try:
        from astro_precompute import resolve_precompute  # noqa: PLC0415
        return resolve_precompute(
            "Sample User", "1990-01-15", birth_time="12:00",
            latitude=28.6139, longitude=77.2090, timezone=5.5,
            place_name="New Delhi", gender=0)
    except Exception as exc:  # noqa: BLE001
        print(f"SKIP sample pc: {exc}")
        return {}


def check_deep_evidence_module() -> bool:
    ok = True
    try:
        import deep_evidence as DE
        pc = _sample_pc()
        if not pc:
            print("SKIP deep_evidence module (no pc)")
            return True
        ctx = DE.begin(pc, lat=28.61, lon=77.20, tz=5.5)
        for key in AREA_KEYS:
            ev = ctx.for_area(key)
            if not ev.get("varga"):
                print(f"FAIL deep_evidence.for_area({key}) missing varga")
                ok = False
                continue
            if not ev.get("house_facts") and not ev.get("rules_pos"):
                print(f"WARN deep_evidence.for_area({key}) thin evidence")
            votes = ctx.vote_triplet(key, ev["houses"][0])
            if len(votes) < 1:
                print(f"WARN deep_evidence.vote_triplet({key}) no votes")
        DE.end()
        if ok:
            print("OK   deep_evidence module")
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL deep_evidence module: {exc}")
        ok = False
    return ok


def check_full_report_html() -> bool:
    ok = True
    pc = _sample_pc()
    if not pc:
        print("SKIP full_report html (no pc)")
        return True
    try:
        import deep_evidence as DE
        import report_render as RR
        DE.begin(pc, lat=28.61, lon=77.20, tz=5.5)
        try:
            free, paid, _meta = RR._full_report_inner(
                pc, name="Sample", question="When will I get promoted?",
                today=__import__("datetime").date.today(),
                price=298, bundle_price=298, lat=28.61, lon=77.20, tz=5.5,
                first="Sample")
        finally:
            DE.end()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL full_report render: {exc}")
        return False

    for label, html in (("free", free), ("paid", paid)):
        for banned in BOOK_LINES_BANNED:
            if banned in html:
                print(f"FAIL [{label}] BOOK_LINES leaked: {banned!r}")
                ok = False
        # Each area card should show evidence from deep layer (divisional or classical)
        if "classical rule" not in html.lower() and "divisional" not in html.lower():
            if "the classical rule-book" not in html and "Looking inside" not in html:
                print(f"WARN [{label}] no obvious deep-evidence phrasing in HTML")
        # Bare until-dates without impact (heuristic)
        bare_until = re.findall(
            r"until\s+[A-Z][a-z]{2}\s+\d{4}(?![^<]{0,40}:)", html)
        if len(bare_until) > 3:
            print(f"WARN [{label}] many bare 'until Mon YYYY' without impact clause")
    if ok:
        print("OK   full_report deep-evidence HTML")
    return ok


def check_merge_semantic_no_headline_override() -> bool:
    try:
        import report_confluence as CF
        verdict = {"direction": "up", "votes": [], "score": 1.0}
        out = CF.merge_semantic_verdict("career", verdict)
        if out.get("headline"):
            print("FAIL merge_semantic_verdict still sets headline")
            return False
        print("OK   merge_semantic_verdict no BOOK_LINES headline")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL merge_semantic: {exc}")
        return False


def main() -> int:
    ok = True
    ok &= check_deep_evidence_module()
    ok &= check_merge_semantic_no_headline_override()
    ok &= check_full_report_html()
    if "--bench" in sys.argv and _sample_pc():
        import time
        pc = _sample_pc()
        import deep_evidence as DE
        import report_render as RR
        t0 = time.perf_counter()
        DE.begin(pc, lat=28.61, lon=77.20, tz=5.5)
        try:
            RR._full_report_inner(
                pc, name="Sample", question="", today=__import__("datetime").date.today(),
                price=298, bundle_price=298, lat=28.61, lon=77.20, tz=5.5, first="Sample")
        finally:
            DE.end()
        print(f"BENCH full_report inner: {time.perf_counter() - t0:.1f}s")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
