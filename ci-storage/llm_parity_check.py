#!/usr/bin/env python3
"""Prove a reading keeps its shape when the model is not answering.

The layout used to depend on whether the LLM produced accepted prose: with it,
readers got the conversational page; without it, the classic cards page or a
conversational page with paragraphs missing. This sweep renders every kind
twice — once with the model's prose marked accepted, once with the model off
entirely — and compares the heading spine of each pair.

Only the wording may differ. A difference in the spine is a failure.

    set PYTHONPATH=engines;engines/astro
    python ci-storage/llm_parity_check.py

Writes the rendered halves to ci-storage/parity/ for eyeballing.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ci-storage" / "parity"
sys.path[:0] = [str(ROOT / "engines" / "astro"), str(ROOT / "engines"), str(ROOT)]

SAMPLE = {
    "name": "Meera Nair",
    "dob": "1990-01-15",
    "tob": "12:00",
    "lat": 28.6139,
    "lon": 77.2090,
    "tz": 5.5,
    "place": "New Delhi, India",
    "gender": 0,
}
QUESTION = "How much hike can I expect this year?"
AREA = "promotion"

HEADING_RE = re.compile(r"<h([1-3])[^>]*>(.*?)</h\1>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")

RULE = "-" * 74
RESULTS: list[tuple[str, bool, str]] = []


def spine(html: str) -> list[str]:
    """The headings a reader scrolls past, in order."""
    out: list[str] = []
    for level, inner in HEADING_RE.findall(html or ""):
        text = WS_RE.sub(" ", TAG_RE.sub(" ", inner)).strip()
        if text:
            out.append(f"h{level}: {text}")
    return out


def say(label: str, ok: bool, note: str = "") -> None:
    RESULTS.append((label, bool(ok), note))
    mark = "ok  " if ok else "FAIL"
    print(f"  {mark} {label}{(' — ' + note) if note else ''}", flush=True)


def compare(kind: str, on: str, off: str, half: str) -> None:
    """The two renders may differ in wording, never in shape."""
    a, b = spine(on), spine(off)
    if a == b:
        say(f"{kind} {half}: same section spine ({len(a)} headings)", True)
        return
    only_on = [h for h in a if h not in b]
    only_off = [h for h in b if h not in a]
    say(f"{kind} {half}: same section spine", False,
        f"{len(a)} vs {len(b)} headings")
    for h in only_on[:6]:
        print(f"       only with the model: {h}", flush=True)
    for h in only_off[:6]:
        print(f"       only without it:    {h}", flush=True)


def write(name: str, free: str, paid: str, meta: dict | None = None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}_free.html").write_text(free, encoding="utf-8")
    (OUT / f"{name}_paid.html").write_text(paid, encoding="utf-8")
    if meta is not None:
        (OUT / f"{name}_meta.json").write_text(
            json.dumps(meta, indent=2, default=str), encoding="utf-8")


# ---------------------------------------------------------------------------
# The model's prose, marked accepted, without calling the model.
#
# What is being checked is structural: that the page no longer changes shape
# with the accepted count. Reusing the deterministic overlay and relabelling it
# as accepted gives the renderer exactly the inputs a live run would, so the
# comparison isolates the thing under test instead of the network.
# ---------------------------------------------------------------------------
def patch_humanize_as_accepted():
    import llm
    from importlib import import_module

    # `llm/__init__.py` re-exports the function, so `llm.humanize` is the
    # function and not the submodule. Ask for the module by name.
    H = import_module("llm.humanize")
    real = H.humanize

    def fake(kind: str, facts, *, access: str = "free") -> dict:
        out = real(kind, facts, access=access)
        overlay = out.get("overlay") or {}
        if not overlay:
            return out
        out = dict(out)
        out["enabled"] = True
        out["fallback_used"] = False
        out["stats"] = {"accepted": max(1, len(overlay)), "rejected": 0,
                        "errors": 0, "rejection_reasons": {}}
        return out

    H.humanize = fake                                        # type: ignore[assignment]
    llm.humanize = fake                                      # type: ignore[assignment]
    # Callers import the symbol inside their own functions, so the module
    # attribute is enough — except where a module bound it at import time.
    for mod in ("report_render", "core.palm_report"):
        m = sys.modules.get(mod)
        if m is not None and callable(getattr(m, "humanize", None)):
            m.humanize = fake                                # type: ignore[attr-defined]
    return real


def restore_humanize(real) -> None:
    import llm
    from importlib import import_module

    import_module("llm.humanize").humanize = real            # type: ignore[assignment]
    llm.humanize = real                                      # type: ignore[assignment]
    for mod in ("report_render", "core.palm_report"):
        m = sys.modules.get(mod)
        if m is not None and callable(getattr(m, "humanize", None)):
            m.humanize = real                                # type: ignore[attr-defined]


def llm_off() -> None:
    os.environ["LLM_ENABLED"] = "0"
    try:
        from core.config import S
        S.llm_enabled = False
    except Exception:                                            # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# renderers
# ---------------------------------------------------------------------------
def build_full_report() -> tuple[str, str, dict]:
    from astro_precompute import resolve_precompute
    import deep_evidence as DE
    import report_render as RD

    s = SAMPLE
    pc = resolve_precompute(
        s["name"], s["dob"], birth_time=s["tob"],
        latitude=s["lat"], longitude=s["lon"], timezone=s["tz"],
        place_name=s["place"], gender=s["gender"])
    DE.begin(pc, lat=s["lat"], lon=s["lon"], tz=s["tz"])
    try:
        return RD._full_report_inner(
            pc, name=s["name"], question="", today=date.today(),
            price=298, bundle_price=1499,
            lat=s["lat"], lon=s["lon"], tz=s["tz"],
            first=s["name"].split()[0])
    finally:
        DE.end()


def build_user_question() -> tuple[str, str, dict]:
    from astro_precompute import resolve_precompute
    import deep_evidence as DE
    import report_render as RD

    try:
        import semantic_fallback
        semantic_fallback.install()
    except Exception:                                            # noqa: BLE001
        pass
    route, area = None, AREA
    try:
        import semantic_question as SQ
        area = SQ.normalize_area(area)
        route = SQ.route(QUESTION, area=area)
    except Exception as exc:                                     # noqa: BLE001
        print(f"  (semantic route unavailable: {exc})", flush=True)

    s = SAMPLE
    pc = resolve_precompute(
        s["name"], s["dob"], birth_time=s["tob"],
        latitude=s["lat"], longitude=s["lon"], timezone=s["tz"],
        place_name=s["place"], gender=s["gender"])
    DE.begin(pc, lat=s["lat"], lon=s["lon"], tz=s["tz"])
    try:
        return RD.user_question(
            pc, question=QUESTION, route=route, area=area,
            name=s["name"], price=1499,
            lat=s["lat"], lon=s["lon"], tz=s["tz"])
    finally:
        DE.end()


def build_horary() -> tuple[str, str, dict]:
    import report_render as RD

    return RD.horary(
        question="Will the property deal go through?",
        verdicts={"western": {"verdict": "Likely yes", "confidence": "moderate"},
                  "vedic": {"verdict": "Uncertain", "confidence": "low"}},
        western_judgment={}, asked="4 August 2026, 21:40",
        name=SAMPLE["name"], horary_price=298, full_report_price=298)


def _hand_block(*, hand_type: str, will: str, mounts: dict) -> dict:
    """A hand the CV could plausibly have measured.

    The shape, line and mount readings all come from measurements, so a fixture
    with empty hands would prove nothing: every section would be dropped for
    want of a body, with or without prose.
    """
    return {
        "features": {
            "quality": {"grade": "good", "score": 0.82},
            "morphology": {
                "hand_type": hand_type,
                "thumb": {"will_vs_logic": will, "length": "long",
                          "opening": "wide"},
            },
            "lines": {
                "life": {"detected": True, "depth": "deep", "length": "long"},
                "head": {"detected": True, "depth": "clear", "length": "long",
                         "slope": "straight"},
                "heart": {"detected": True, "depth": "clear", "curve": "curved"},
                "fate": {"detected": True, "depth": "clear", "shape": "straight"},
            },
            "mounts": mounts,
        },
    }


def palm_fixture() -> dict:
    return {
        "confluence": {
            "dominant_hand": "right",
            "life_aspects": [
                {"key": "career", "title": "Career & Direction",
                 "strength": "moderate", "summary": "Experience helps."},
                {"key": "health", "title": "Health & Vitality",
                 "strength": "weak", "summary": "Rest is owed."},
            ],
            "predictions": [
                {"age": 24, "text": "An early stretch of proving yourself."},
                {"age": 34, "text": "A steadier stretch at work."},
            ],
        },
        "right": _hand_block(
            hand_type="air", will="will_dominant",
            mounts={"jupiter": "prominent", "saturn": "flat",
                    "venus": "prominent"}),
        "left": _hand_block(
            hand_type="air", will="balanced",
            mounts={"jupiter": "flat", "mercury": "prominent"}),
    }


def build_palm(with_prose: bool) -> tuple[str, str]:
    """Palm always uses one template; the question is whether prose reaches it."""
    from core.palm_conversational import render as palm_render
    from llm.fallback import conversational_palm_fallback
    from llm.schemas import PalmAspectFacts, PalmFacts

    prose_free: dict = {}
    prose_paid: dict = {}
    if with_prose:
        facts = PalmFacts(
            first_name="Meera", access="paid", age_years=30,
            personality_traits=["You think better by talking things through."],
            life_stage_note="Around age 31, your vitality enters a new chapter.",
            demanding_aspect="health", demanding_aspect_label="Health & Vitality",
            aspects=[PalmAspectFacts(
                aspect="career", title="Career & Direction",
                semantic_summary="Experience has become an advantage.",
                recognize=["consistency has helped your position"],
                age_window=[27, 36], strength="moderate")])
        prose_paid = conversational_palm_fallback(facts)
        facts.access = "free"
        prose_free = conversational_palm_fallback(facts)

    raw = palm_fixture()
    free = palm_render(raw, name=SAMPLE["name"], age=30, paid=False,
                       prose=prose_free)
    paid = palm_render(raw, name=SAMPLE["name"], age=30, paid=True,
                       prose=prose_paid)
    return free, paid


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-charts", action="store_true",
                    help="skip the kinds that need a precomputed chart")
    args = ap.parse_args()

    llm_off()
    print(f"{RULE}\nLLM-off vs model-answered, same renderer, same shape\n{RULE}",
          flush=True)

    # --- palm: one template, prose optional --------------------------------
    print("\npalm — the prose is optional, the sections are not", flush=True)
    try:
        on_free, on_paid = build_palm(True)
        off_free, off_paid = build_palm(False)
        write("palm_with_prose", on_free, on_paid)
        write("palm_no_prose", off_free, off_paid)
        compare("palm", on_free, off_free, "free")
        compare("palm", on_paid, off_paid, "paid")
        say("palm free half keeps its unlock CTA",
            'data-unlock="1"' in off_free)
    except Exception as exc:                                     # noqa: BLE001
        say("palm renders", False, f"{type(exc).__name__}: {exc}")

    # --- horary ------------------------------------------------------------
    print("\nhorary — verdict page", flush=True)
    try:
        real = patch_humanize_as_accepted()
        try:
            on_free, on_paid, on_meta = build_horary()
        finally:
            restore_humanize(real)
        off_free, off_paid, off_meta = build_horary()
        write("horary_llm_on", on_free, on_paid, on_meta)
        write("horary_llm_off", off_free, off_paid, off_meta)
        compare("horary", on_free, off_free, "free")
        compare("horary", on_paid, off_paid, "paid")
    except Exception as exc:                                     # noqa: BLE001
        say("horary renders", False, f"{type(exc).__name__}: {exc}")

    if args.skip_charts:
        print("\n(skipping chart-backed kinds by request)", flush=True)
    else:
        for label, fn in (("full_report", build_full_report),
                          ("user_question", build_user_question)):
            print(f"\n{label} — chart-backed", flush=True)
            try:
                real = patch_humanize_as_accepted()
                try:
                    on_free, on_paid, on_meta = fn()
                finally:
                    restore_humanize(real)
                off_free, off_paid, off_meta = fn()
                write(f"{label}_llm_on", on_free, on_paid, on_meta)
                write(f"{label}_llm_off", off_free, off_paid, off_meta)
                compare(label, on_free, off_free, "free")
                compare(label, on_paid, off_paid, "paid")
                say(f"{label} design tag matches with and without the model",
                    (on_meta or {}).get("design") == (off_meta or {}).get("design"),
                    f"{(on_meta or {}).get('design')} vs "
                    f"{(off_meta or {}).get('design')}")
                say(f"{label} free half keeps its unlock CTA",
                    'data-unlock="1"' in off_free)
            except Exception as exc:                             # noqa: BLE001
                say(f"{label} renders", False, f"{type(exc).__name__}: {exc}")

    print(f"\n{RULE}")
    bad = [label for label, ok, _ in RESULTS if not ok]
    print(f"{len(RESULTS) - len(bad)}/{len(RESULTS)} checks passed")
    print(f"HTML written to {OUT}")
    print("VERDICT:", "PASS" if not bad else "FAIL — " + "; ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
