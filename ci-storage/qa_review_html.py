"""Spot-check regenerated review HTML for suggestion-spec issues."""
from __future__ import annotations

import re
from pathlib import Path

OUT = Path("/tmp/review_samples")
NEEDLES = [
    "has been pressing on",
    "fight off illness",
    "nobody else will tell",
    "weigh the mixed",
    "energy. and which",
    "energy — and which",
    "Home and family matters may be taking",
    "You may feel a stronger need",
    "recover from setbacks",
    "ask someone senior",
    "Some charts also indicate",
    "Strong agreement",
    "Good agreement",
    "Mixed agreement",
    "Mixed evidence",
    "Jupiter runs until",
    "Saturn runs until",
    "considered suitable",
    "Birth chart, current timing and major planetary movement agree",
    "career chart",
    "learning chart",
    "Your learning chart",
    "well-built for",
]


def main() -> int:
    for name in ("astro_full_report_free.html", "astro_full_report_paid.html"):
        p = OUT / name
        t = p.read_text(encoding="utf-8")
        body = re.sub(r"<style>.*?</style>", "", t, flags=re.S)
        print("===", name, "bytes", len(t))
        for needle in NEEDLES:
            print(f"  {needle!r}: {body.count(needle)}")
        sc = re.findall(r'class="pred-scenario">(.*?)</p>', body)
        print("  present scenarios:")
        for s in sc[:8]:
            print("   -", re.sub(r"\s+", " ", s)[:180])
        traits = re.findall(r'<ul class="traits">(.*?)</ul>', body, flags=re.S)
        if traits:
            items = re.findall(r"<li>(.*?)</li>", traits[0])
            print("  traits:")
            for i in items:
                print("   -", i[:200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
