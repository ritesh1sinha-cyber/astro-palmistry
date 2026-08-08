#!/usr/bin/env python3
"""CI gate: customer HTML must be prediction-first with one Why line per block."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))

BANNED = (
    "Maha-lord",
    "Antar-lord",
    "Chara-lord",
    "Yogini-lord",
    "neutral_sign",
    "own_sign",
    "enemy_sign",
    "dusthana",
    "varga",
    "D10 chart",
    "D9 chart",
    " BAV",
    " SAV",
    "bindu",
    "of 8 support points",
    "Looking inside this specific chart",
    "In the sky now",
    "Across methods",
    "methods with a view agree",
    "phalange count",
    "Girdle of Venus",
    "Mount of Jupiter",
    "Mount of Saturn",
    "Mount of ",
    "As per your life line",
    "Reading for you:",
    "via minilm",
    "Maha-lord Jupiter",
    "Neecha-Bhanga",
    "Neecha Bhanga",
)


def _sample_pc() -> dict:
    try:
        from astro_precompute import resolve_precompute  # noqa: PLC0415
        return resolve_precompute(
            "Sample User", "1990-01-15", birth_time="12:00",
            latitude=28.6139, longitude=77.2090, timezone=5.5,
            place_name="New Delhi", gender=0)
    except Exception as exc:  # noqa: BLE001
        print(f"SKIP sample pc: {exc}")
        return {}


def _fail_if_banned(html: str, label: str) -> bool:
    ok = True
    low = html or ""
    for tok in BANNED:
        if tok in low:
            print(f"FAIL [{label}] banned token {tok!r}")
            ok = False
    return ok


def _check_why_blocks(html: str, label: str, *, min_count: int = 1) -> bool:
    count = len(re.findall(r"<b>Why:</b>", html or ""))
    if count < min_count:
        print(f"FAIL [{label}] expected >= {min_count} Why lines, found {count}")
        return False
    print(f"OK   [{label}] {count} Why line(s)")
    return True


def check_present_read() -> bool:
    pc = _sample_pc()
    if not pc:
        return True
    try:
        import deep_evidence as DE
        import present_read as PR
        DE.begin(pc, lat=28.61, lon=77.20, tz=5.5)
        try:
            block = PR.build(pc)
            html = PR.render(block)
        finally:
            DE.end()
        ok = _fail_if_banned(html, "present_read")
        ok &= _check_why_blocks(html, "present_read", min_count=2)
        if _has_sentence_dash(html):
            print("FAIL [present_read] sentence-joining dash in customer HTML")
            ok = False
        if ok:
            print("OK   present_read HTML")
        return ok
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL present_read: {exc}")
        return False


def check_full_report() -> bool:
    pc = _sample_pc()
    if not pc:
        return True
    try:
        import deep_evidence as DE
        import report_render as RR
        DE.begin(pc, lat=28.61, lon=77.20, tz=5.5)
        try:
            free, paid, _ = RR._full_report_inner(
                pc, name="Sample", question="",
                today=__import__("datetime").date.today(),
                price=298, bundle_price=298, lat=28.61, lon=77.20, tz=5.5,
                first="Sample")
        finally:
            DE.end()
        ok = _fail_if_banned(free + paid, "full_report")
        ok &= _check_why_blocks(free + paid, "full_report", min_count=3)
        if ok:
            print("OK   full_report HTML")
        return ok
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL full_report: {exc}")
        return False


def check_user_question() -> bool:
    pc = _sample_pc()
    if not pc:
        return True
    try:
        import deep_evidence as DE
        import report_render as RR
        DE.begin(pc, lat=28.61, lon=77.20, tz=5.5)
        try:
            free, paid, _ = RR.user_question(
                pc, question="When will I get promoted?", name="Sample",
                price=298, lat=28.61, lon=77.20, tz=5.5)
        finally:
            DE.end()
        ok = _fail_if_banned(free, "user_question free")
        ok &= _check_why_blocks(free, "user_question free", min_count=1)
        ok &= _fail_if_banned(paid, "user_question paid")
        ok &= _check_why_blocks(paid, "user_question paid", min_count=2)
        if "of 8 support" in paid:
            print("FAIL [user_question paid] BAV wording leaked")
            ok = False
        if ok:
            print("OK   user_question HTML")
        return ok
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL user_question: {exc}")
        return False


def check_palm_html() -> bool:
    try:
        sys.path.insert(0, str(ROOT / "engines"))
        from palm_api import palm_voice as PV
        sample = (
            "As per your Mount of Jupiter, it is full — leadership."
            " Reading for you: you will lead."
        )
        polished = PV.polish_html(sample)
        ok = _fail_if_banned(polished, "palm polish")
        if ok:
            print("OK   palm_voice polish")
        return ok
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL palm polish: {exc}")
        return False


def check_predict_voice_module() -> bool:
    try:
        import predict_voice as PV
        p = PV.compose("career", direction="up", md_lord="Jupiter", ad_lord="Moon",
                       house=10, lord="Saturn", dignity="neutral_sign")
        if "neutral_sign" in p.backing or "neutral_sign" in p.scenario:
            print("FAIL predict_voice dignity leak")
            return False
        if not p.backing or not p.scenario:
            print("FAIL predict_voice empty output")
            return False
        print("OK   predict_voice module")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL predict_voice module: {exc}")
        return False


def check_palm_voice_module() -> bool:
    try:
        sys.path.insert(0, str(ROOT / "engines"))
        from palm_api import palm_voice as PV
        p = PV.format_line_verdict("life", 34, {"depth": "deep"})
        if "As per" in p.text_block() or "Reading for you" in p.text_block():
            print("FAIL palm_voice banned prefix")
            return False
        if "Why:" not in p.text_block():
            print("FAIL palm_voice missing Why")
            return False
        print("OK   palm_voice module")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL palm_voice module: {exc}")
        return False


def _opening_sentence(text: str) -> str:
    plain = re.sub(r"<[^>]+>", " ", text or "")
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain.split(".")[0].strip() if plain else ""


def _has_sentence_dash(text: str) -> bool:
    plain = re.sub(r"<[^>]+>", " ", text or "")
    return bool(re.search(r"\s—\s", plain))


def check_area_cards() -> bool:
    """All eight area headlines must be distinct with chart-specific backing."""
    pc = _sample_pc()
    if not pc:
        return True
    try:
        import deep_evidence as DE
        import predict_voice as PV
        import report_cards as RC

        chart_names = {
            "career": "career chart",
            "money": "wealth chart",
            "love": "marriage chart",
            "home": "home chart",
            "children": "children chart",
            "health": "health chart",
            "learning": "learning chart",
            "inner": "spiritual chart",
        }
        DE.begin(pc, lat=28.61, lon=77.20, tz=5.5)
        try:
            cards = RC.build_cards(pc)
        finally:
            DE.end()

        scenarios = {c.area: c.headline for c in cards}
        if len(scenarios) < 8:
            print(f"FAIL [area_cards] expected 8 areas, got {len(scenarios)}")
            return False
        if len(set(scenarios.values())) < len(scenarios):
            print("FAIL [area_cards] duplicate area scenarios")
            return False

        money_open = _opening_sentence(scenarios.get("money", ""))
        home_open = _opening_sentence(scenarios.get("home", ""))
        if money_open and money_open == home_open:
            print("FAIL [area_cards] money and home share opening sentence")
            return False

        ok = True
        for area, card in ((c.area, c) for c in cards):
            backing = (card.backing or "").lower()
            chart = chart_names.get(area, "")
            if chart and chart not in backing:
                print(f"FAIL [area_cards] {area} backing missing {chart!r}")
                ok = False
            if _has_sentence_dash(card.headline):
                print(f"FAIL [area_cards] sentence dash in {area} headline")
                ok = False
            if _has_sentence_dash(card.backing or ""):
                print(f"FAIL [area_cards] sentence dash in {area} backing")
                ok = False
            if "wealth chart" in (card.headline or "").lower() and area != "money":
                print(f"FAIL [area_cards] wealth chart leaked into {area} headline")
                ok = False
            if "home chart" in (card.headline or "").lower() and area != "home":
                print(f"FAIL [area_cards] home chart leaked into {area} headline")
                ok = False

        for a in RC.AREAS:
            DE.begin(pc, lat=28.61, lon=77.20, tz=5.5)
            try:
                pred = PV.compose_from_area(pc, a.key, a.house)
            finally:
                DE.end()
            if "Why:" in pred.scenario:
                print(f"FAIL [area_cards] Why leaked into {a.key} scenario")
                ok = False
            if not pred.backing:
                print(f"FAIL [area_cards] empty backing for {a.key}")
                ok = False

        if ok:
            print("OK   area_cards distinct + chart-backed")
        return ok
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL area_cards: {exc}")
        return False


def check_opening_prose() -> bool:
    """Personal opening must not use sentence-joining em dashes."""
    pc = _sample_pc()
    if not pc:
        return True
    try:
        import astro_voice as AV
        import report_confluence as CF
        from datetime import date

        now = CF.vimshottari_at(pc, date.today())
        ctx = {
            "name": "Sample User",
            "lagna": pc.get("lagna", ""),
            "nakshatra": (pc.get("planets", {}).get("Moon") or {}).get("nakshatra", ""),
            "lagna_lord": pc.get("lagna_lord", ""),
            "moon_sign": (pc.get("planets", {}).get("Moon") or {}).get("sign", ""),
            "moon_nakshatra": (pc.get("planets", {}).get("Moon") or {}).get("nakshatra", ""),
            "dasha_md": now.get("md", ""),
            "dasha_ad": now.get("ad", ""),
            "age": 36,
            "place": "New Delhi",
            "tob": "12:00",
        }
        html = AV.chart_opening(ctx)
        if _has_sentence_dash(html):
            print("FAIL [chart_opening] sentence-joining dash found")
            return False
        print("OK   chart_opening punctuation")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL chart_opening: {exc}")
        return False


def check_area_report() -> bool:
    """Unified area contract: prediction, proof, when, remedy."""
    pc = _sample_pc()
    if not pc:
        return True
    try:
        import area_report as AR
        import deep_evidence as DE
        import report_cards as RC

        DE.begin(pc, lat=28.61, lon=77.20, tz=5.5)
        try:
            ok = True
            for a in RC.AREAS:
                rep = AR.build_area(pc, a.key, a.house)
                if not rep.prediction:
                    print(f"FAIL [area_report] empty prediction for {a.key}")
                    ok = False
                if not rep.proof:
                    print(f"FAIL [area_report] empty proof for {a.key}")
                    ok = False
                if len(rep.proof) > 220:
                    print(f"FAIL [area_report] proof too long for {a.key}: {len(rep.proof)}")
                    ok = False
                if not rep.when:
                    print(f"FAIL [area_report] empty when for {a.key}")
                    ok = False
                if rep.direction == "down" and not rep.remedy:
                    print(f"FAIL [area_report] down area missing remedy: {a.key}")
                    ok = False
                if _has_sentence_dash(rep.prediction):
                    print(f"FAIL [area_report] dash in prediction for {a.key}")
                    ok = False
                if _has_sentence_dash(rep.proof):
                    print(f"FAIL [area_report] dash in proof for {a.key}")
                    ok = False
        finally:
            DE.end()
        if ok:
            print("OK   area_report contract")
        return ok
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL area_report: {exc}")
        return False


def check_recognition() -> bool:
    """Recognition block must not use sentence-joining dashes."""
    pc = _sample_pc()
    if not pc:
        return True
    try:
        import report_recognition as RR
        blocks = RR.build(pc)
        html = RR.render(blocks)
        ok = _fail_if_banned(html, "recognition")
        if _has_sentence_dash(html):
            print("FAIL [recognition] sentence-joining dash in customer HTML")
            ok = False
        if ok:
            print("OK   recognition punctuation")
        return ok
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL recognition: {exc}")
        return False


def check_remedy_lede() -> bool:
    """Remedy section lede must not use sentence-joining dashes."""
    pc = _sample_pc()
    if not pc:
        return True
    try:
        import report_render as RR
        html = RR._remedy(pc, name="Sample", paid=True)
        m = re.search(r'<p class="remedy-lede">(.*?)</p>', html or "", re.S)
        lede = re.sub(r"<[^>]+>", " ", m.group(1) if m else "")
        lede = re.sub(r"\s+", " ", lede).strip()
        if not lede:
            print("FAIL [remedy_lede] missing remedy-lede paragraph")
            return False
        if _has_sentence_dash(lede):
            print("FAIL [remedy_lede] sentence-joining dash in lede")
            return False
        print("OK   remedy_lede punctuation")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL remedy_lede: {exc}")
        return False


def check_user_question_area_report() -> bool:
    pc = _sample_pc()
    if not pc:
        return True
    try:
        import deep_evidence as DE
        import question_answer as QA
        DE.begin(pc, lat=28.61, lon=77.20, tz=5.5)
        try:
            result = QA.answer(pc, "When will I get promoted?")
        finally:
            DE.end()
        rep = result.get("area_report")
        if rep is None:
            print("FAIL [user_question] missing area_report")
            return False
        if not rep.proof or len(rep.proof) > 220:
            print("FAIL [user_question] area_report proof invalid")
            return False
        print("OK   user_question area_report")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL user_question area_report: {exc}")
        return False


def main() -> int:
    ok = True
    ok &= check_predict_voice_module()
    ok &= check_palm_voice_module()
    ok &= check_area_report()
    ok &= check_area_cards()
    ok &= check_opening_prose()
    ok &= check_recognition()
    ok &= check_present_read()
    ok &= check_remedy_lede()
    ok &= check_full_report()
    ok &= check_user_question()
    ok &= check_user_question_area_report()
    ok &= check_palm_html()
    print(f"\n{'ALL OK' if ok else 'FAILURES'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
