#!/usr/bin/env python3
"""Generate free/paid palm HTML from left+right palm photos."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "engines"), str(ROOT / "engines" / "astro"), str(ROOT)]
sys.path[:] = [
    p for p in sys.path
    if not (Path(p).resolve().name == "core" and (Path(p) / "queue.py").is_file())
]

from palm_api.pipeline import analyze_image_paths  # noqa: E402
from core.palm_report import build_palm_html_reading  # noqa: E402

DEFAULT_RIGHT = Path(r"C:\Users\IN009287\Downloads\R.jpg")
DEFAULT_LEFT = Path(r"C:\Users\IN009287\Downloads\L.jpg")
OUT_DIR = ROOT / "ci-storage" / "review_html"


def main() -> int:
    right = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_RIGHT
    left = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_LEFT
    name = sys.argv[3] if len(sys.argv) > 3 else "Seeker"
    age = int(sys.argv[4]) if len(sys.argv) > 4 else 30

    for p in (right, left):
        if not p.is_file():
            print(f"FAIL missing {p}", file=sys.stderr)
            return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    overlay_dir = OUT_DIR / "palm_overlays"
    raw = analyze_image_paths(
        [str(right), str(left)], active_hand="right", overlay_dir=overlay_dir)
    params = {"name": name, "age": age, "gender": "other", "dominant": "right"}
    free_html, paid_html, meta = build_palm_html_reading(raw, params, price=499)

    slug = f"{name.lower().replace(' ', '_')}_palm"
    free_path = OUT_DIR / f"{slug}_free.html"
    paid_path = OUT_DIR / f"{slug}_paid.html"
    meta_path = OUT_DIR / f"{slug}_meta.json"

    free_path.write_text(free_html, encoding="utf-8")
    paid_path.write_text(paid_html, encoding="utf-8")
    meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")

    print(json.dumps({
        "free": str(free_path),
        "paid": str(paid_path),
        "meta": str(meta_path),
        "free_bytes": len(free_html),
        "paid_bytes": len(paid_html),
        "aspects": len((raw.get("confluence") or {}).get("life_aspects") or []),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
