#!/usr/bin/env python3
"""Desktop smoke: Ritz palms → free/paid HTML and head/life relation."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# engines first; never put ROOT/core on PYTHONPATH — it shadows stdlib `queue`
# and breaks MediaPipe landmarking.
sys.path[:0] = [str(ROOT / "engines"), str(ROOT / "engines" / "astro"), str(ROOT)]
# Drop a direct `core/` entry if a caller exported it.
sys.path[:] = [p for p in sys.path
               if not (Path(p).resolve().name == "core"
                       and (Path(p) / "queue.py").is_file())]

from palm_api.pipeline import analyze_image_paths  # noqa: E402
from core.palm_report import build_palm_html_reading  # noqa: E402

LEFT = Path(r"C:\Users\rites\Downloads\Compressed\palm\ritz_leftpalm.jpg")
RIGHT = Path(r"C:\Users\rites\Downloads\Compressed\palm\ritz_rightpalm.jpg")
JUNK = ("triplicity", "chart-from-palm", "weekday-born", "phalange count", "capricorn")
# These strings are the hardcoded fallbacks used when `palm_voice` fails to
# import (see engines/palm_api/conclusive.py::_make_verdict and
# engines/palm_api/confluence.py). If any of these show up, the real
# prediction logic silently broke and the report is running on boilerplate.
FALLBACKS = (
    "your hands show a clear pattern here",
    "reads differently between hands.",
    "is consistent across both hands.",
)
# Text-corruption regressions the `palm_voice`/`astro_voice` finalize passes
# can (re)introduce once real prediction sentences start flowing through them:
# a blanket " mount" -> " area" replace once turned the "Mount by mount"
# heading into "Mount by area", and an overly broad dangling-connector
# cleanup once ate the word "with." off the end of real sentences.
TEXT_BUGS = ("mount by area", "born why:")


def check(label: str, html: str, *, paid: bool) -> list[str]:
    fails: list[str] = []
    print("==", label, "==")
    for name, ok in (
        ("Left hand caption", "Left hand" in html),
        ("Right hand caption", "Right hand" in html),
        ("at least one image", "<img " in html),
        ("proof block", 'class="proof"' in html),
    ):
        print(("OK  " if ok else "FAIL"), name)
        if not ok:
            fails.append(f"{label}: {name}")
    if paid:
        for name, ok in (
            ("unlocked evidence", 'class="evidence">' in html),
            ("workings points", '<ul class="palm-points">' in html),
            ("no unlock CTA", 'data-unlock="1"' not in html),
        ):
            print(("OK  " if ok else "FAIL"), name)
            if not ok:
                fails.append(f"{label}: {name}")
    else:
        for name, ok in (
            ("locked evidence", "evidence locked-inline" in html),
            ("unlock CTA", 'data-unlock="1"' in html),
            ("no workings list", '<ul class="palm-points">' not in html),
        ):
            print(("OK  " if ok else "FAIL"), name)
            if not ok:
                fails.append(f"{label}: {name}")
    junk = [t for t in JUNK if t in html.lower()]
    print(("OK  " if not junk else "FAIL"), "junk phrases", junk or "none")
    if junk:
        fails.append(f"{label}: junk {junk}")
    generic = [t for t in FALLBACKS if t in html.lower()]
    print(("OK  " if not generic else "FAIL"), "no generic fallback verdicts", generic or "none")
    if generic:
        fails.append(f"{label}: generic fallback {generic}")
    corrupted = [t for t in TEXT_BUGS if t in html.lower()]
    print(("OK  " if not corrupted else "FAIL"), "no text-corruption regressions", corrupted or "none")
    if corrupted:
        fails.append(f"{label}: text corruption {corrupted}")
    return fails


def main() -> int:
    for p in (LEFT, RIGHT):
        if not p.is_file():
            print("FAIL missing", p)
            return 1
    out = Path(tempfile.mkdtemp(prefix="ritz_palm_"))
    raw = analyze_image_paths(
        [str(RIGHT), str(LEFT)], active_hand="right", overlay_dir=out / "ov")
    free, paid, meta = build_palm_html_reading(
        raw, {"name": "Ritz", "age": 34, "gender": "male", "dominant": "right"},
        price=499)
    (out / "free.html").write_text(free, encoding="utf-8")
    (out / "paid.html").write_text(paid, encoding="utf-8")
    (out / "meta.json").write_text(
        json.dumps(meta, indent=2, default=str), encoding="utf-8")

    fails: list[str] = []
    for hand in ("left", "right"):
        feats = (raw.get(hand) or {}).get("features") or {}
        rel = (feats.get("lines") or {}).get("head", {}).get("start_relation")
        ov = bool((raw.get(hand) or {}).get("overlay_path"))
        print(f"{hand}: start_relation={rel} overlay={ov}")
        if not ov:
            fails.append(f"{hand} overlay missing")
        if rel not in ("merged", "separated", "separated_wide"):
            fails.append(f"{hand} start_relation invalid: {rel!r}")

    fails += check("free", free, paid=False)
    fails += check("paid", paid, paid=True)
    print("meta.design=", meta.get("design"))
    print("OUT", out)
    print("RESULT", "PASS" if not fails else "FAIL")
    for f in fails:
        print(" -", f)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
