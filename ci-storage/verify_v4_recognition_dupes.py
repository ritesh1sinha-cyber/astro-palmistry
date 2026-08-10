"""Quick check — no duplicate money/career recognition paragraphs in smoke HTML."""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = [
    ROOT / "ci-storage" / "astro_full_report_paid.html",
    ROOT / "ci-storage" / "astro_full_report_free.html",
]


def main() -> int:
    failed = 0
    for path in HTML:
        if not path.is_file():
            print(f"SKIP missing {path.name}")
            continue
        html = path.read_text(encoding="utf-8")
        claims = re.findall(r'class="recog-claim">([^<]+)', html)
        dups = [t for t, c in Counter(claims).items() if c > 1]
        print(f"{path.name}: {len(claims)} claims, {len(dups)} duplicate texts")
        if dups:
            failed += 1
            for d in dups:
                print(f"  DUP: {d[:80]}")
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
