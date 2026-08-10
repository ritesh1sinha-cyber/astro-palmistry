"""Generate free/paid full reports for overfitting check (3 sample charts)."""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path[:0] = ["/app/engines/astro", "/app", "/app/engines"]

from astro_precompute import resolve_precompute  # noqa: E402
import deep_evidence as DE  # noqa: E402
import report_render as RD  # noqa: E402

OUT = Path("/tmp/review_samples/oversample")

FORBIDDEN_MINOR = re.compile(
    r"\b(promotion|salary|spouse|marriage|marry|wedding)\b", re.I)
OLD_CAREER_PAST = (
    "Your work was easier to move forward, and people were more likely to notice you."
)

SAMPLES = [
    {
        "slug": "ramesh_1986-03-08_delhi",
        "name": "Ramesh",
        "dob": "1986-03-08",
        "tob": "13:00",
        "lat": 28.6139,
        "lon": 77.2090,
        "tz": 5.5,
        "place": "New Delhi",
        "gender": 1,
    },
    {
        "slug": "suresh_1990-01-12_delhi",
        "name": "Suresh",
        "dob": "1990-01-12",
        "tob": "00:05",
        "lat": 28.6139,
        "lon": 77.2090,
        "tz": 5.5,
        "place": "New Delhi",
        "gender": 1,
    },
    {
        "slug": "gyanesh_2012-01-01_hyderabad",
        "name": "Gyanesh",
        "dob": "2012-01-01",
        "tob": "10:00",
        "lat": 17.3850,
        "lon": 78.4867,
        "tz": 5.5,
        "place": "Hyderabad",
        "gender": 1,
    },
]


def _body(html: str) -> str:
    return re.sub(r"<style>.*?</style>", "", html or "", flags=re.S)


def _checks(sample: dict, free: str, paid: str) -> dict:
    fb, pb = _body(free), _body(paid)
    both = fb + pb
    checks = {
        "no_old_career_past_line": OLD_CAREER_PAST not in both,
        "has_past_events": 'class="past-event' in fb or 'class="past-event' in pb,
    }
    if sample["slug"].startswith("gyanesh"):
        checks["minor_no_adult_terms"] = not FORBIDDEN_MINOR.search(both)
        checks["minor_studies_label"] = (
            "Studies" in both or "studies" in both or "teacher" in both.lower()
        )
    return checks


def gen_one(sample: dict) -> dict:
    pc = resolve_precompute(
        sample["name"], sample["dob"], birth_time=sample["tob"],
        latitude=sample["lat"], longitude=sample["lon"],
        timezone=sample["tz"], place_name=sample["place"],
        gender=sample["gender"])
    DE.begin(pc, lat=sample["lat"], lon=sample["lon"], tz=sample["tz"])
    try:
        free, paid, meta = RD._full_report_inner(
            pc, name=sample["name"], question="", today=date.today(),
            price=298, bundle_price=298, lat=sample["lat"], lon=sample["lon"],
            tz=sample["tz"], first=sample["name"])
    finally:
        DE.end()

    OUT.mkdir(parents=True, exist_ok=True)
    free_path = OUT / f"{sample['slug']}_free.html"
    paid_path = OUT / f"{sample['slug']}_paid.html"
    free_path.write_text(free, encoding="utf-8")
    paid_path.write_text(paid, encoding="utf-8")
    checks = _checks(sample, free, paid)
    return {
        "sample": {k: sample[k] for k in (
            "slug", "name", "dob", "tob", "place", "lat", "lon", "tz")},
        "free_bytes": len(free),
        "paid_bytes": len(paid),
        "free_path": str(free_path),
        "paid_path": str(paid_path),
        "checks": checks,
        "meta_free": meta.get("freeSections"),
        "meta_paid": meta.get("paidSections"),
    }


def main() -> int:
    results = []
    for sample in SAMPLES:
        print(f"Generating {sample['slug']} ...", flush=True)
        results.append(gen_one(sample))
    summary = {"count": len(results), "results": results}
    (OUT / "index.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    failed = []
    for row in results:
        for k, v in (row.get("checks") or {}).items():
            if v is False:
                failed.append(f"{row['sample']['slug']}:{k}")
    if failed:
        print("FAILED:", ", ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
