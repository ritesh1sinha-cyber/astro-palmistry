"""Generate Classical Vedic Report review HTML.

Runs inside the API container:
  docker exec ... python /tmp/gen_classical_samples.py

Locally, point PYJHORA_SRC at a directory containing `jhora` and run:
  set PYTHONPATH=engines;engines/astro
  python ci-storage/gen_classical_samples.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

if Path("/app").is_dir():
    sys.path[:0] = ["/app/engines/astro", "/app", "/app/engines"]
    OUT = Path("/tmp/review_samples/classical")
else:
    ROOT = Path(__file__).resolve().parent.parent
    sys.path[:0] = [str(ROOT / "engines" / "astro"), str(ROOT), str(ROOT / "engines")]
    OUT = ROOT / "ci-storage" / "review_html" / "classical"

OUT.mkdir(parents=True, exist_ok=True)

SAMPLES = [
    {"slug": "meera", "name": "Meera Nair", "dob": "1990-01-15", "tob": "12:00",
     "lat": 28.6139, "lon": 77.2090, "tz": 5.5, "place": "New Delhi", "gender": 1},
    {"slug": "ramesh", "name": "Ramesh", "dob": "1986-03-08", "tob": "13:00",
     "lat": 28.6139, "lon": 77.2090, "tz": 5.5, "place": "New Delhi", "gender": 0},
]


def generate(sample: dict) -> dict:
    from astro_precompute import resolve_precompute
    from classical_report import classical_report

    print(f"[classical] {sample['slug']} ...", flush=True)
    pc = resolve_precompute(
        sample["name"], sample["dob"], birth_time=sample["tob"],
        latitude=sample["lat"], longitude=sample["lon"],
        timezone=sample["tz"], place_name=sample["place"],
        gender=sample.get("gender", 0))

    free, paid, meta = classical_report(
        pc, name=sample["name"], dob=sample["dob"], tob=sample["tob"],
        place=sample["place"], price=298, bundle_price=298)

    slug = sample["slug"]
    (OUT / f"{slug}_free.html").write_text(free, encoding="utf-8")
    (OUT / f"{slug}_paid.html").write_text(paid, encoding="utf-8")
    (OUT / f"{slug}_meta.json").write_text(
        json.dumps(meta, indent=2, default=str), encoding="utf-8")
    return {
        "slug": slug,
        "free_bytes": len(free),
        "paid_bytes": len(paid),
        "lagna": meta.get("lagna"),
        "mahadasha": meta.get("mahadasha"),
        "paid_sections": meta.get("paidSections"),
    }


def main() -> int:
    only = {s for s in (os.getenv("CLASSICAL_SLUGS") or "").split(",") if s}
    rows = [generate(s) for s in SAMPLES if not only or s["slug"] in only]
    (OUT / "summary.json").write_text(
        json.dumps(rows, indent=2, default=str), encoding="utf-8")
    for row in rows:
        print(json.dumps(row, default=str), flush=True)
    print(f"[classical] wrote {len(rows)} sample(s) to {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
