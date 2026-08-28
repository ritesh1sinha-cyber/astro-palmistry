"""What the free half of every report is allowed to say about time.

The free page proves itself against the reader's past and sells its future.
This renders each kind at both tiers and checks that rule holds, because the
two halves are written in different modules and drift silently otherwise.

Run: python ci-storage/free_gate_check.py
"""

from __future__ import annotations

import html
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT), str(ROOT / "engines"), str(ROOT / "engines" / "astro")]

MONTH_YEAR = re.compile(
    r"(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+20\d\d")
ISO = re.compile(r"\b20\d\d-\d{2}(?:-\d{2})?\b")

OUT = HERE / "parity"


def visible(doc: str) -> str:
    """Customer-visible text: no CSS, no script, no tags."""
    body = re.split(r"</style>", doc)[-1]
    body = re.sub(r"<script.*?</script>", " ", body, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body)))


def future_dates(text: str, today: date) -> list[str]:
    from free_dates import is_past
    found = [m.group(0) for m in MONTH_YEAR.finditer(text)]
    found += [m.group(0) for m in ISO.finditer(text)]
    return sorted({d for d in found if not is_past(d, today)})


def past_dates(text: str, today: date) -> list[str]:
    from free_dates import is_past
    found = [m.group(0) for m in MONTH_YEAR.finditer(text)]
    return sorted({d for d in found if is_past(d, today)})


def main() -> int:
    import llm_parity_check as P

    P.llm_off()
    today = date.today()
    OUT.mkdir(parents=True, exist_ok=True)
    failures = 0

    builders = [
        ("full_report", P.build_full_report),
        ("user_question", P.build_user_question),
        ("horary", P.build_horary),
        ("palm", lambda: P.build_palm(False) + (None,)),
    ]
    for kind, build in builders:
        try:
            free, paid, _meta = build()
        except Exception as exc:                                     # noqa: BLE001
            print(f"[{kind}] build failed: {exc}")
            failures += 1
            continue
        (OUT / f"gate_{kind}_free.html").write_text(free, encoding="utf-8")
        (OUT / f"gate_{kind}_paid.html").write_text(paid, encoding="utf-8")

        free_txt, paid_txt = visible(free), visible(paid)
        ahead = future_dates(free_txt, today)
        behind = past_dates(free_txt, today)
        paid_all = MONTH_YEAR.findall(paid_txt)

        ok = not ahead
        print(f"[{kind}] free future dates: {len(ahead)} "
              f"{'OK' if ok else 'FAIL ' + str(ahead[:8])}")
        print(f"[{kind}] free past dates kept: {len(behind)} {behind[:6]}")
        print(f"[{kind}] paid dates: {len(set(paid_all))}")
        if not ok:
            failures += 1

        # A remedy the reader has not bought must not be in the markup at all,
        # blurred or otherwise — CSS is not a paywall. Every occurrence, since
        # the page builds its remedy boxes in more than one module.
        leaks = [m.start() for m in re.finditer(r"Targeted (?:Vedic|Astrological) Upaya", free)
                 if re.search(r"\b(?:Chant|chant|donate|Donate|Offer|Recite)\b",
                              free[m.start():m.start() + 400])]
        if leaks:
            print(f"[{kind}] FAIL real remedy text in free markup "
                  f"({len(leaks)} of "
                  f"{len(re.findall(r'Targeted (?:Vedic|Astrological) Upaya', free))})")
            failures += 1

    print()
    print("free date gate:", "PASS" if not failures else f"{failures} FAILURE(S)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
