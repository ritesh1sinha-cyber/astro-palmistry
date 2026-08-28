"""Full-page free/paid date gate and the reactivated allowlist.

The conversational unit tests in qa_checks/test_free_date_gate.py hold the
renderer. This one builds the real full_report so a wiring change cannot
quietly reopen the future on the customer page.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT), str(ROOT / "engines"), str(ROOT / "engines" / "astro")]


def test_full_report_free_has_no_future_dates_and_no_remedy_leak():
    import free_gate_check as G
    import llm_parity_check as P

    P.llm_off()
    from datetime import date
    today = date.today()
    free, paid, _meta = P.build_full_report()
    free_txt, paid_txt = G.visible(free), G.visible(paid)

    ahead = G.future_dates(free_txt, today)
    behind = G.past_dates(free_txt, today)
    assert not ahead, ahead
    assert behind, "free full report must keep a past date as proof"
    assert G.MONTH_YEAR.findall(paid_txt), "paid full report must keep its dates"

    leaks = [
        m.start() for m in __import__("re").finditer(
            r"Targeted (?:Vedic|Astrological) Upaya", free)
        if __import__("re").search(
            r"\b(?:Chant|chant|donate|Donate|Offer|Recite)\b",
            free[m.start():m.start() + 400])
    ]
    assert not leaks


def test_date_guard_allowlist_is_nonempty_and_softens_nothing_real():
    import date_guard_diff as D

    assert D.main() == 0
