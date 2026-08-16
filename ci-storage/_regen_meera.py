"""Regenerate Meera classical report from cached precompute."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "ci-storage" / "review_html" / "classical"

pc = json.loads((ROOT / "ci-storage" / "_meera_pc.json").read_text(encoding="utf-8"))

import sys
sys.path[:0] = [str(ROOT / "engines" / "astro"), str(ROOT), str(ROOT / "engines")]

from classical_report import classical_report

free, paid, meta = classical_report(
    pc, name="Meera Nair", dob="1990-01-15", tob="12:00",
    place="New Delhi", price=298, bundle_price=298)

(OUT / "meera_free.html").write_text(free, encoding="utf-8")
(OUT / "meera_paid.html").write_text(paid, encoding="utf-8")
(OUT / "meera_meta.json").write_text(
    json.dumps(meta, indent=2, default=str), encoding="utf-8")

print(f"FREE: {len(free)} bytes")
print(f"PAID: {len(paid)} bytes")
print(f"Design: {meta['design']}")
print(f"Sections: {meta['paidSections']}")
print("Done - files written to", OUT)
