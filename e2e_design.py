#!/usr/bin/env python3
"""End-to-end check that the CARD DESIGN is what a customer receives.

    python3 e2e_design.py                 # SQLite + local store, no services
    python3 e2e_design.py --keep          # keep the HTML and print the paths
    python3 e2e_design.py --out ./preview # write the HTML somewhere you choose

Different from `e2e_check.py`, which drives the HTTP API and proves the stack is
alive. This one calls the job handlers directly, in-process, and then reads the
stored bytes back out of the object store — the same bytes `/api/file/{token}`
serves to the browser. So it answers the question that actually matters after a
design change:

    is the new design what gets STORED, or only what the renderers can produce?

That distinction is not academic. The card renderers were finished and tested for
weeks while `core.handlers` still called the old long-form generators, so every
renderer test passed and every customer saw the old report.

Needs no Postgres, no Redis and no API. Measured at ~4 seconds warm — the
ephemeris pass and the twelve lanes are both fast; it is the palm CV that is
slow, and this check does not touch it.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def bootstrap(store_dir: Path, db_path: Path) -> None:
    """Point the app at throwaway storage before anything imports config."""
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")
    os.environ.setdefault("LOCAL_STORE", str(store_dir))
    os.environ.setdefault("APP_SECRET", "e2e-design-local-only")
    os.environ.setdefault("ENV", "dev")
    os.environ.setdefault("DEV_LOGIN", "1")
    # The engines live in engines/ and engines/astro/. The Docker image sets
    # PYTHONPATH; a bare venv does not, so do it here rather than making the
    # reader remember.
    for p in (HERE, HERE / "engines", HERE / "engines" / "astro"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    # Several engine files annotate with `str | None` and have no
    # `from __future__ import annotations`, so they need 3.10+. On 3.9 the repo
    # ships an import hook that rewrites those annotations; load it before any
    # engine import rather than failing with a confusing TypeError.
    if sys.version_info < (3, 10):
        try:
            import _py39_shim  # noqa: F401
        except Exception as exc:                                     # noqa: BLE001
            print(f"[e2e] Python {sys.version_info.major}."
                  f"{sys.version_info.minor} and the 3.9 shim did not load "
                  f"({exc}). Use Python 3.10 or newer.", file=sys.stderr)
    if not os.environ.get("PYJHORA_SRC"):
        # The engines want the DIRECTORY CONTAINING the `jhora` package, and
        # "PyJHora source not found" is the single most common local failure.
        # find_spec locates it without importing (jhora prints on import), and
        # covers user-site installs that site.getsitepackages() misses.
        try:
            import importlib.util
            spec = importlib.util.find_spec("jhora")
            origin = getattr(spec, "origin", None) if spec else None
            if origin:
                os.environ["PYJHORA_SRC"] = str(Path(origin).parent.parent)
        except Exception:                                            # noqa: BLE001
            pass
    if not os.environ.get("PYJHORA_SRC"):
        print("[e2e] PyJHora not found. Install it (pip install PyJHora==4.7.0) "
              "or set PYJHORA_SRC to the directory containing the `jhora` "
              "package.", file=sys.stderr)


# What must never reach a reader. Every entry here was found in real output at
# some point, which is why the list looks arbitrary — it is not.
LEAK = re.compile(
    r"\b(longevity|lifespan|life-risk|maraka|mrityu|killer|handbook|Book OCR|"
    r"precomputed:|Deterministic rule engine|ritxx|rule-based|hard-coded)\b",
    re.I)
# "21.5" became "21. 5" when a sentence-tidying rule met a whole document.
# Checked on the RAW html: stripping tags first joins separate elements and
# produces false positives.
DECIMAL_SPLIT = re.compile(r"\b\d+\.\s+\d\b")

RITESH = {"name": "Ritesh Kumar Sinha", "dob": "1985-03-08", "tob": "13:05",
          "place": "Patna", "lat": 25.5941, "lon": 85.1376, "tz": 5.5,
          "gender": 0}
ADITI = {"name": "Aditi", "dob": "1989-07-29", "tob": "00:05",
         "place": "Patna", "lat": 25.5941, "lon": 85.1376, "tz": 5.5,
         "gender": 1}

RESULTS: list[tuple[str, bool]] = []
SAVED: list[tuple[str, Path]] = []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true",
                    help="keep the generated HTML instead of deleting it")
    ap.add_argument("--out", default="", help="directory for the HTML")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="e2e-design-"))
    out_dir = Path(args.out) if args.out else tmp / "html"
    out_dir.mkdir(parents=True, exist_ok=True)
    bootstrap(tmp / "storage", tmp / "e2e.db")

    from core.db import init_schema, upsert_user
    from core.store import report_keys, store
    import core.handlers as H

    init_schema()
    user = upsert_user(email="e2e-design@test.local", name="Ritesh Kumar Sinha")

    def halves(rid: str) -> tuple[str, str]:
        fk, pk = report_keys(rid)
        st = store()
        return (st.get(fk).decode("utf-8", "ignore"),
                st.get(pk).decode("utf-8", "ignore"))

    def audit(label: str, rid: str, *, must=(), must_not=(), paid_must=()) -> None:
        free, paid = halves(rid)
        for tag, doc in (("free", free), ("paid", paid)):
            p = out_dir / f"{label}.{tag}.html"
            p.write_text(doc, encoding="utf-8")
            SAVED.append((f"{label} ({tag})", p))
        print(f"\n{label}: free {len(free):,}B  paid {len(paid):,}B")
        ok = True
        for probe in must:
            hit = probe.lower() in free.lower()
            ok &= hit
            print(f"   {'ok  ' if hit else 'MISS'} free shows:  {probe}")
        for probe in must_not:
            hit = probe.lower() in free.lower()
            ok &= not hit
            print(f"   {'ok  ' if not hit else 'BAD '} free omits:  {probe}")
        for probe in paid_must:
            hit = probe.lower() in paid.lower()
            ok &= hit
            print(f"   {'ok  ' if hit else 'MISS'} paid shows:  {probe}")
        for tag, doc in (("free", free), ("paid", paid)):
            m = LEAK.search(doc)
            if m:
                ctx = doc[max(0, m.start() - 60):m.start() + 70].replace("\n", " ")
                print(f"   LEAK in {tag}: {m.group(0)!r}  …{ctx}…")
                ok = False
            d = DECIMAL_SPLIT.search(doc)
            if d:
                print(f"   NUMBER SPLIT in {tag}: {d.group(0)!r}")
                ok = False
        print(f"   -> {'PASS' if ok else 'FAIL'}")
        RESULTS.append((label, ok))

    print("=" * 74)
    print("Every reading below is generated, stored, and read back from storage.")
    print("=" * 74)

    audit("numerology", H.h_numerology(user, dict(RITESH))["reportId"],
          must=("life path", "lo shu", "personal year", "--ink:#16181d"),
          paid_must=("life path",))

    audit("kundali_match", H.h_kundali_match(user, {
        "groomName": "Ritesh", "groomDob": RITESH["dob"],
        "groomTob": RITESH["tob"], "groomLat": RITESH["lat"],
        "groomLon": RITESH["lon"], "groomTz": 5.5, "groomPlace": "Patna",
        "brideName": "Aditi", "brideDob": ADITI["dob"], "brideTob": ADITI["tob"],
        "brideLat": ADITI["lat"], "brideLon": ADITI["lon"], "brideTz": 5.5,
        "bridePlace": "Patna"})["reportId"],
        must=("36", "Ritesh", "Aditi"),
        # A compatibility report's remedies are the dosha remedies. Career
        # gemstones appearing here was a real copy-paste bug.
        must_not=("gemstone",),
        paid_must=("the full matching report",))

    audit("horary", H.h_horary(user, {
        "question": "Will the property deal go through?",
        "qDate": "2026-08-04", "qTime": "21:40",
        "location": "Patna, India"})["reportId"],
        must=("you asked", "property"),
        must_not=("the two traditions disagree",),
        paid_must=("working",))

    print("\n(the flagship: 12 specialist lanes, then the confluence)")
    r = H.h_full_report(user, {**RITESH, "question": "When will I change my job?"})
    audit("full_report", r["reportId"],
          must=("data-verdict", "your past", "everything, one price",
                "--ink:#16181d"),
          paid_must=("the full analyst working",))
    meta = r.get("meta") or {}
    lanes = meta.get("lanes") or {}
    print(f"   design tag: {meta.get('design')}")
    print(f"   lanes built: {lanes.get('built')} · failed: {lanes.get('failed')}")
    RESULTS.append(("design tag is cards-v2", meta.get("design") == "cards-v2"))
    RESULTS.append(("all 12 lanes built", (lanes.get("built") or 0) >= 12))

    print("\n" + "=" * 74)
    bad = [n for n, ok in RESULTS if not ok]
    print(f"{len(RESULTS) - len(bad)}/{len(RESULTS)} checks passed")
    if args.keep or args.out:
        print("\nOpen these in a browser:")
        for label, path in SAVED:
            print(f"   {label:<24} {path}")
    else:
        shutil.rmtree(tmp, ignore_errors=True)
        print("\n(run with --keep to inspect the HTML)")
    print("VERDICT:", "PASS" if not bad else "FAIL — " + ", ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
