"""The free astro page may prove itself against the past, never the future."""
from __future__ import annotations

from datetime import date
from pathlib import Path
import html as html_lib
import re
import sys

HERE = Path(__file__).resolve()
ENG = HERE.parents[1]
if str(ENG) not in sys.path:
    sys.path.insert(0, str(ENG))

TODAY = date(2026, 8, 27)
MONTH_YEAR = re.compile(
    r"(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+20\d\d")

_PC = {
    "lagna": {"sign": "Capricorn"},
    "planets": {"Moon": {"sign": "Taurus", "nakshatra": "Rohini"}},
    "vimshottari": {
        "current_md": {"md_lord": "Rahu", "start": "2024-05-17", "end": "2042-05-17"},
        "current_md_antardashas": [
            {"status": "previous", "ad_lord": "Mercury",
             "start": "2022-11-01", "end": "2024-05-17"},
            {"status": "current", "ad_lord": "Jupiter",
             "start": "2024-05-17", "end": "2026-10-11"},
            {"status": "upcoming", "ad_lord": "Saturn",
             "start": "2026-10-11", "end": "2029-03-01"},
        ],
    },
}

_PROSE = {
    "astrological_basis": "Capricorn rising with Moon in Taurus.",
    "personality": "You tend to take important commitments seriously.",
}


def _visible(doc: str) -> str:
    body = re.split(r"</style>", doc, flags=re.I)[-1]
    body = re.sub(r"<script.*?</script>", " ", body, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " ", body)))


def _render(*, paid: bool) -> str:
    import report_conversational as R
    return R.render(_PC, name="Meera", today=TODAY, paid=paid, prose=_PROSE)


def test_free_astro_keeps_past_dates_and_locks_the_future():
    from free_dates import is_past

    free = _render(paid=False)
    paid = _render(paid=True)
    free_txt, paid_txt = _visible(free), _visible(paid)

    future_on_free = [d for d in MONTH_YEAR.findall(free_txt) if not is_past(d, TODAY)]
    past_on_free = [d for d in MONTH_YEAR.findall(free_txt) if is_past(d, TODAY)]
    assert not future_on_free, future_on_free
    assert past_on_free, "free page must keep at least one past date as proof"

    paid_dates = set(MONTH_YEAR.findall(paid_txt))
    assert paid_dates, "paid page must still print the dated windows"
    assert any(not is_past(d, TODAY) for d in paid_dates), paid_dates

    # The running period's start is the proof the reader can check.
    assert "May 2024" in free_txt or "17 May 2024" in free
    assert "House Axis" not in free


def test_free_astro_does_not_leak_the_real_remedy():
    free = _render(paid=False)
    leaks = [
        m.start() for m in re.finditer(r"Targeted (?:Vedic|Astrological) Upaya", free)
        if re.search(r"\b(?:Chant|chant|donate|Donate|Offer|Recite)\b",
                     free[m.start():m.start() + 400])
    ]
    assert not leaks
    assert "House Axis" not in free
