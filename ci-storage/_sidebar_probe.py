"""Check the section rail lands on every report kind, LLM off for speed."""
from __future__ import annotations

import os
import re
import sys
from datetime import date
from pathlib import Path

os.environ.setdefault("LLM_ENABLED", "0")

sys.path[:0] = ["/app/engines/astro", "/app", "/app/engines"]

import report_render as RD  # noqa: E402
from astro_precompute import resolve_precompute  # noqa: E402

S = {"name": "Meera Nair", "dob": "1990-01-15", "tob": "12:00",
     "lat": 28.6139, "lon": 77.2090, "tz": 5.5, "place": "New Delhi", "gender": 1}

OUT = Path("/tmp/review_samples/sidebar")


def rail(html: str) -> list[str]:
    match = re.search(r'<nav class="secnav".*?</nav>', html or "", re.S)
    if not match:
        return []
    return re.findall(r'<a href="#([^"]+)">([^<]*)</a>', match.group(0))


def check(label: str, html: str) -> None:
    links = rail(html)
    maps = (html or "").count("life-map-intro")
    print(f"\n--- {label}: {len(links)} links, {maps} life-area maps, "
          f"{len(html):,} bytes")
    for anchor, text in links:
        present = f'id="{anchor}"' in html
        print(f"    {'ok ' if present else 'DEAD'} {text}")
    if links:
        assert "@media print" in html, f"{label}: rail must hide in print"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pc = resolve_precompute(S["name"], S["dob"], birth_time=S["tob"],
                            latitude=S["lat"], longitude=S["lon"],
                            timezone=S["tz"], place_name=S["place"],
                            gender=S["gender"])
    today = date.today()
    common = dict(lat=S["lat"], lon=S["lon"], tz=S["tz"])

    free, paid, _ = RD._full_report_inner(
        pc, name=S["name"], question="", today=today, price=298,
        bundle_price=298, first="Meera", **common)
    check("full report free", free)
    check("full report paid", paid)

    q_free, q_paid, _ = RD.user_question(
        pc, question="Will I buy a house?", name=S["name"], price=298,
        today=today, **common)
    check("user question free", q_free)
    check("user question paid", q_paid)

    extra: list[tuple[str, str]] = []

    try:
        from daily_moon_prediction import compute_daily_moon_guide
        guide = compute_daily_moon_guide(pc, today, latitude=S["lat"],
                                         longitude=S["lon"], timezone=S["tz"])
        d_free, d_paid, _ = RD.daily(guide if isinstance(guide, dict) else {},
                                     day=today, name=S["name"], price=298,
                                     pc=pc, **common)
        check("daily free", d_free)
        check("daily paid", d_paid)
        extra += [("daily_free", d_free), ("daily_paid", d_paid)]
    except Exception as exc:  # noqa: BLE001
        print(f"\n--- daily: skipped ({type(exc).__name__}: {exc})")

    try:
        from vedic_horary_report import generate_vedic_horary_html as vgen
        question = "Will I get the job?"
        _, judgment = vgen(question, today.isoformat(), "10:30", "New Delhi", "108")
        h_free, h_paid, _ = RD.horary(
            question=question,
            verdicts={"vedic": {k: judgment.get(k)
                                for k in ("verdict", "confidence", "score")}},
            western_judgment={}, asked=f"{today.isoformat()} 10:30",
            name=S["name"], horary_price=298, full_report_price=1499,
            vedic_customer=judgment.get("customer") or {})
        check("horary free", h_free)
        check("horary paid", h_paid)
        extra += [("horary_free", h_free), ("horary_paid", h_paid)]
    except Exception as exc:  # noqa: BLE001
        import traceback
        print(f"\n--- horary: skipped ({type(exc).__name__}: {exc})")
        traceback.print_exc()

    for slug, html in [("full_free", free), ("full_paid", paid),
                       ("question_free", q_free), ("question_paid", q_paid),
                       *extra]:
        (OUT / f"{slug}.html").write_text(html, encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
