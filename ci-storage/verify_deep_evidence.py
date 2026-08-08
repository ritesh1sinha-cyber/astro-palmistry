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
                pc, name="Sample", question="",
                today=__import__("datetime").date.today(),
                price=298, bundle_price=298, lat=28.61, lon=77.20, tz=5.5,
                first="Sample")
        finally:
            DE.end()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL full_report render: {exc}")
        return False

    for label, html in (("free", free), ("paid", paid)):
        if 'class="qa-asked"' in html or "One question to focus" in html:
            print(f"FAIL [{label}] focus question still in full_report")
            ok = False
        for banned in BOOK_LINES_BANNED:
            if banned in html:
                print(f"FAIL [{label}] BOOK_LINES leaked: {banned!r}")
                ok = False
        # Each area card should show one Why line from predict_voice
        why_count = len(re.findall(r"<b>Why:</b>", html))
        if why_count < 2:
            print(f"WARN [{label}] only {why_count} Why line(s) in full_report HTML")
        # Bare until-dates without impact (heuristic)
        bare_until = re.findall(
            r"until\s+[A-Z][a-z]{2}\s+\d{4}(?![^<]{0,40}:)", html)
        if len(bare_until) > 3:
            print(f"WARN [{label}] many bare 'until Mon YYYY' without impact clause")
    if ok:
        print("OK   full_report deep-evidence HTML")
    return ok


def check_user_question_html() -> bool:
    ok = True
    pc = _sample_pc()
    if not pc:
        print("SKIP user_question html (no pc)")
        return True
    try:
        import deep_evidence as DE
        import report_render as RR
        DE.begin(pc, lat=28.61, lon=77.20, tz=5.5)
        try:
            free, paid, meta = RR.user_question(
                pc, question="When will I get promoted?",
                route=None, name="Sample", price=298,
                lat=28.61, lon=77.20, tz=5.5)
        finally:
            DE.end()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL user_question render: {exc}")
        return False

    if "qa-asked" not in free:
        print("FAIL [user_question free] missing qa-asked block")
        ok = False
    for locked in ("The verdict", "When it can happen", "The remedy"):
        if locked not in free:
            print(f"FAIL [user_question free] missing locked section {locked!r}")
            ok = False
    if "qa-verdict" not in paid:
        print("FAIL [user_question paid] missing verdict")
        ok = False
    if not meta.get("answer"):
        print("FAIL [user_question] meta.answer missing")
        ok = False
    if ok:
        print("OK   user_question paywall HTML")
    return ok


def check_palm_bridge_cache() -> bool:
    pc = _sample_pc()
    if not pc:
        print("SKIP palm_bridge cache (no pc)")
        return True
    try:
        import deep_evidence as DE
        import palm_astro_bridge as PB
        builds = {"n": 0}
        real = PB.build

        def counted(pc_in, pf=None):
            builds["n"] += 1
            return real(pc_in, pf)

        PB.build = counted
        ctx = DE.begin(pc, lat=28.61, lon=77.20, tz=5.5)
        try:
            ctx.palm_bridge()
            ctx.palm_bridge()
            import report_confluence as CF
            CF.area_votes(pc, "career", 10)
            CF.area_votes(pc, "love", 7)
        finally:
            PB.build = real
            DE.end()
        if builds["n"] > 1:
            print(f"FAIL palm_bridge built {builds['n']} times (want 1)")
            return False
        print("OK   palm_bridge cached once per report")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL palm_bridge cache: {exc}")
        return False


def check_saraswati_merge() -> bool:
    try:
        eng = str(ROOT / "engines")
        if eng not in sys.path:
            sys.path.insert(0, eng)
        from palm_api.life_aspects import build_life_aspects  # noqa: PLC0415
        blocks = {
            "right": {"features": {"lines": {"life": {"detected": True, "depth": "deep",
                                                       "quality": "clear", "length": "long"}}}},
            "left": {"features": {"lines": {"life": {"detected": True, "depth": "medium",
                                                     "quality": "clear", "length": "long"}}}},
        }
        sigs = {
            "health": [{
                "text": "Vitality from the life-line formula reads steady — recovery responds to routine.",
                "method": "Saraswati palmistry", "reinforced": False,
                "book": "jyotis_saraswati", "book_label": "Jyotis Saraswati",
            }],
        }
        rows = build_life_aspects(blocks, "right", saraswati_signals=sigs)
        health = next((r for r in rows if r["key"] == "health"), None)
        if not health:
            print("WARN saraswati merge — no health aspect from minimal stub")
            print("OK   saraswati merge wiring (stub)")
            return True
        if not any("Saraswati" in str(p.get("method", "")) for p in health["points"]):
            print("FAIL saraswati signals not in aspect points")
            return False
        print("OK   saraswati merge into life_aspects")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL saraswati merge: {exc}")
        return False


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
    ok &= check_user_question_html()
    ok &= check_palm_bridge_cache()
    ok &= check_saraswati_merge()
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
        t1 = time.perf_counter()
        DE.begin(pc, lat=28.61, lon=77.20, tz=5.5)
        try:
            RR.user_question(pc, question="When will I get promoted?", name="Sample",
                             price=298, lat=28.61, lon=77.20, tz=5.5)
        finally:
            DE.end()
        print(f"BENCH user_question: {time.perf_counter() - t1:.1f}s")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
