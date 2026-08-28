"""Prove the reactivated date guard softens nothing the engine really computed.

The guard was dead for the whole life of the full report (a NameError into a
bare except left the allowlist empty). Switching it back on is the one change
here that can silently rewrite good prose, so this renders with the guard
active and with it bypassed, and diffs every date and every softened phrase.

Run: python ci-storage/date_guard_diff.py
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT), str(ROOT / "engines"), str(ROOT / "engines" / "astro")]

MONTH_YEAR = re.compile(
    r"(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+20\d\d")
SOFTENED = "later in the cycle"


def visible(doc: str) -> str:
    body = re.split(r"</style>", doc)[-1]
    body = re.sub(r"<script.*?</script>", " ", body, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body)))


def main() -> int:
    import llm_parity_check as P

    P.llm_off()
    import report_render as RR
    import qa_checks.date_guard as DG

    sizes: list[int] = []
    real_scrub = RR._scrub

    def spy(doc, *, allowed_dates=None):
        sizes.append(len(allowed_dates or ()))
        return real_scrub(doc, allowed_dates=allowed_dates)

    RR._scrub = spy
    guarded = P.build_full_report()

    # Same render with the softener neutralised, so any difference is the
    # guard's doing and nothing else.
    real_soften = DG.soften_unvalidated_dates
    DG.soften_unvalidated_dates = lambda text, *, allowed=None: text
    bare = P.build_full_report()
    DG.soften_unvalidated_dates = real_soften
    RR._scrub = real_scrub

    print(f"allowlist sizes seen: {sizes}")
    if not any(sizes):
        print("FAIL the allowlist is still empty — the guard is not running")
        return 1

    failures = 0
    for i, tier in ((0, "free"), (1, "paid")):
        g, b = visible(guarded[i]), visible(bare[i])
        g_dates, b_dates = set(MONTH_YEAR.findall(g)), set(MONTH_YEAR.findall(b))
        lost = sorted(b_dates - g_dates)
        softened = g.count(SOFTENED) - b.count(SOFTENED)
        print(f"[{tier}] dates unguarded={len(b_dates)} guarded={len(g_dates)} "
              f"softened_phrases={softened}")
        if lost:
            print(f"[{tier}] FAIL guard removed real dates: {lost}")
            failures += 1
        for d in lost:
            m = re.search(re.escape(d), b)
            if m:
                print(f"        context: ...{b[max(0, m.start() - 120):m.end() + 60]}...")

    print()
    print("date guard:", "PASS" if not failures else f"{failures} FAILURE(S)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
