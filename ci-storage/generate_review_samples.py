#!/usr/bin/env python3
"""Generate before/after HTML samples for plan review (astro + palm)."""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ci-storage" / "review_samples"
ASTRO = ROOT / "engines" / "astro"
ENG = ROOT / "engines"


def bootstrap() -> None:
    for p in (ROOT, ENG, ASTRO):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    store = OUT / "_store"
    store.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{store / 'review.db'}"
    os.environ["LOCAL_STORE"] = str(store)
    os.environ.setdefault("APP_SECRET", "review-local-only")
    os.environ.setdefault("ENV", "dev")
    os.environ.setdefault("DEV_LOGIN", "1")
    if sys.version_info < (3, 10):
        import _py39_shim  # noqa: F401


def strip_html(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def write(name: str, html: str, sub: str = "") -> Path:
    d = OUT / sub if sub else OUT
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(html, encoding="utf-8")
    return p


def gen_astro_after() -> dict:
    """Current code: full_report without embedded question + user_question."""
    import deep_evidence as DE
    import report_render as RD

    sample = {"name": "Meera Nair", "dob": "1990-01-15", "tob": "12:00",
              "place": "New Delhi, India", "lat": 28.6139, "lon": 77.2090,
              "tz": 5.5, "gender": 0}
    from astro_precompute import resolve_precompute
    pc = resolve_precompute(
        sample["name"], sample["dob"], birth_time=sample["tob"],
        latitude=sample["lat"], longitude=sample["lon"],
        timezone=sample["tz"], place_name=sample["place"],
        gender=sample["gender"])

    paths = {}
    DE.begin(pc, lat=sample["lat"], lon=sample["lon"], tz=sample["tz"])
    try:
        free, paid, _ = RD._full_report_inner(
            pc, name=sample["name"], question="", today=date.today(),
            price=298, bundle_price=298, lat=sample["lat"], lon=sample["lon"],
            tz=sample["tz"], first="Meera")
        paths["astro_full_report_free.html"] = write(
            "astro_full_report_free.html", free, "after")
        paths["astro_full_report_paid.html"] = write(
            "astro_full_report_paid.html", paid, "after")

        uq_free, uq_paid, uq_meta = RD.user_question(
            pc, question="When will I get promoted?",
            route=None, name=sample["name"], price=298,
            lat=sample["lat"], lon=sample["lon"], tz=sample["tz"])
        paths["astro_user_question_free.html"] = write(
            "astro_user_question_free.html", uq_free, "after")
        paths["astro_user_question_paid.html"] = write(
            "astro_user_question_paid.html", uq_paid, "after")
    finally:
        DE.end()

    return {
        "full_report_has_qa": "qa-asked" in free,
        "user_question_has_locked": all(x in uq_free for x in (
            "The verdict", "When it can happen", "The remedy")),
        "user_question_paid_verdict": "qa-verdict" in uq_paid,
        "paths": {k: str(v) for k, v in paths.items()},
        "answer_meta": uq_meta.get("answer"),
    }


def gen_astro_before() -> dict:
    """Simulate pre-plan full_report: question block embedded via question_answer."""
    from astro_precompute import resolve_precompute
    import deep_evidence as DE
    import report_render as RD
    import question_answer as QA

    sample = {"name": "Meera Nair", "dob": "1990-01-15", "tob": "12:00",
              "lat": 28.6139, "lon": 77.2090, "tz": 5.5, "gender": 0}
    pc = resolve_precompute(
        sample["name"], sample["dob"], birth_time=sample["tob"],
        latitude=sample["lat"], longitude=sample["lon"],
        timezone=sample["tz"], place_name="New Delhi", gender=sample["gender"])
    question = "When will I get promoted?"

    DE.begin(pc, lat=sample["lat"], lon=sample["lon"], tz=sample["tz"])
    try:
        free, paid, _ = RD._full_report_inner(
            pc, name=sample["name"], question="", today=date.today(),
            price=298, bundle_price=298, lat=sample["lat"], lon=sample["lon"],
            tz=sample["tz"], first="Meera")
        # Re-inject old behaviour: question section inside full report
        q_free = QA.render(QA.answer(pc, question, lat=sample["lat"],
                                     lon=sample["lon"], tz=sample["tz"]),
                           name="Meera", paid=False, price=298)
        q_paid = QA.render(QA.answer(pc, question, lat=sample["lat"],
                                     lon=sample["lon"], tz=sample["tz"]),
                           name="Meera", paid=True, price=298)
        # Insert after present read (approximate old slot)
        for tag, qhtml, label in (("free", q_free, "astro_full_report_with_question_free.html"),
                                  ("paid", q_paid, "astro_full_report_with_question_paid.html")):
            doc = free if tag == "free" else paid
            if "data-verdict=" in doc:
                doc = doc.replace('<article class="card" data-verdict=',
                                    qhtml + '\n<article class="card" data-verdict=', 1)
            write(label, doc, "before")
    finally:
        DE.end()

    return {"full_report_had_qa": True, "note": "question block re-injected for comparison"}


def gen_palm_comparison() -> dict:
    """Compare palm aspect cards with/without Saraswati confluence points."""
    from palm_api.life_aspects import build_life_aspects
    from palm_api.confluence import build_confluence

    blocks = {
        "right": {
            "features": {
                "lines": {
                    "life": {"detected": True, "depth": "deep", "quality": "clear",
                             "length": "long", "type": "curved"},
                    "head": {"detected": True, "depth": "medium", "quality": "clear",
                             "length": "long"},
                    "heart": {"detected": True, "depth": "medium", "quality": "clear",
                              "length": "medium"},
                    "fate": {"detected": True, "depth": "deep", "quality": "clear",
                             "length": "long"},
                },
                "mounts": {"jupiter": {"prominence": "high"},
                           "venus": {"prominence": "medium"}},
                "fingers": {"index": {"length": "long"}, "ring": {"length": "long"}},
            },
            "numbered_checklist": [],
        },
        "left": {
            "features": {
                "lines": {
                    "life": {"detected": True, "depth": "medium", "quality": "clear",
                             "length": "long"},
                    "head": {"detected": True, "depth": "medium", "quality": "clear",
                             "length": "long"},
                    "heart": {"detected": True, "depth": "shallow", "quality": "faint",
                              "length": "short"},
                    "fate": {"detected": True, "depth": "medium", "quality": "clear",
                             "length": "medium"},
                },
                "mounts": {"jupiter": {"prominence": "medium"}},
            },
            "numbered_checklist": [],
        },
    }

    before_conf = build_confluence(blocks, "right", saraswati_signals=None)
    saraswati = {
        "character": [{
            "text": ("From the phalange count, your chart-from-palm reads a "
                     "Capricorn rising temperament — the hand should show steady "
                     "finger length and mount emphasis."),
            "method": "Saraswati palmistry", "reinforced": False,
            "book": "jyotis_saraswati", "book_label": "Jyotis Saraswati",
        }],
        "health": [{
            "text": ("Vitality from the life-line formula reads steady — "
                     "recovery responds to routine, not force."),
            "method": "Saraswati palmistry", "reinforced": False,
            "book": "jyotis_saraswati", "book_label": "Jyotis Saraswati",
        }],
        "career": [{
            "text": ("Jupiter's triplicity from the hand lands on Sagittarius — "
                     "sponsorship and public credit move through that quality."),
            "method": "Saraswati palmistry", "reinforced": False,
            "book": "jyotis_saraswati", "book_label": "Jyotis Saraswati",
        }],
    }
    after_conf = build_confluence(blocks, "right", saraswati_signals=saraswati)

    from core.palm_cards import render as palm_render

    raw_before = {"right": blocks["right"], "left": blocks["left"],
                  "active_hand": "right", "confluence": before_conf}
    raw_after = {"right": blocks["right"], "left": blocks["left"],
                 "active_hand": "right", "confluence": after_conf}

    html_before = palm_render(raw_before, paid=False, price=298, name="Review")
    html_after = palm_render(raw_after, paid=False, price=298, name="Review")

    write("palm_free_before.html", html_before, "before")
    write("palm_free_after.html", html_after, "after")

    def saraswati_count(conf):
        n = 0
        for asp in (conf or {}).get("life_aspects") or []:
            for pt in asp.get("points") or []:
                if "Saraswati" in str(pt.get("method", "")):
                    n += 1
        return n

    return {
        "before_saraswati_points": saraswati_count(before_conf),
        "after_saraswati_points": saraswati_count(after_conf),
        "before_aspects": len((before_conf or {}).get("life_aspects") or []),
        "after_aspects": len((after_conf or {}).get("life_aspects") or []),
    }


def write_summary(astro_after: dict, astro_before: dict, palm: dict) -> Path:
    lines = [
        "# Before / After Review Samples",
        "",
        "Generated for plan review: Ask your chart + Saraswati palm confluence.",
        "",
        "## Astro — full report",
        "",
        "| | Before | After |",
        "|---|---|---|",
        f"| Question inside full report | Yes (`qa-asked` block) | "
        f"{'Yes (FAIL)' if astro_after.get('full_report_has_qa') else 'No (removed)'} |",
        f"| Dedicated user_question section | No | Yes (separate HTML files) |",
        "",
        "## Astro — user question (after only)",
        "",
        f"- Free has locked verdict/timing/remedy: "
        f"{astro_after.get('user_question_has_locked')}",
        f"- Paid has verdict: {astro_after.get('user_question_paid_verdict')}",
        f"- Answer meta: `{json.dumps(astro_after.get('answer_meta'), default=str)}`",
        "",
        "## Palm — life aspect confluence",
        "",
        f"- Saraswati points in aspect cards before: {palm.get('before_saraswati_points')}",
        f"- Saraswati points in aspect cards after: {palm.get('after_saraswati_points')}",
        f"- Life aspects matched before/after: "
        f"{palm.get('before_aspects')} / {palm.get('after_aspects')}",
        "",
        "## Files to open in a browser",
        "",
        "### After (current)",
        "- `after/astro_full_report_free.html`",
        "- `after/astro_full_report_paid.html`",
        "- `after/astro_user_question_free.html`",
        "- `after/astro_user_question_paid.html`",
        "- `after/palm_free_after.html`",
        "",
        "### Before (simulated pre-plan)",
        "- `before/astro_full_report_with_question_free.html`",
        "- `before/astro_full_report_with_question_paid.html`",
        "- `before/palm_free_before.html`",
        "",
    ]
    p = OUT / "REVIEW.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def main() -> int:
    bootstrap()
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "_store").exists():
        shutil.rmtree(OUT / "_store", ignore_errors=True)

    print("Generating astro AFTER samples…")
    astro_after = gen_astro_after()
    print(json.dumps(astro_after, indent=2, default=str))

    print("\nGenerating astro BEFORE samples (question embedded)…")
    astro_before = gen_astro_before()

    print("\nGenerating palm BEFORE/AFTER samples…")
    palm = gen_palm_comparison()
    print(json.dumps(palm, indent=2))

    summary = write_summary(astro_after, astro_before, palm)
    print(f"\nWrote {summary}")
    print(f"All samples in: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
