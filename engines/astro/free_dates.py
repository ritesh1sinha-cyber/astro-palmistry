"""What a free reading may say about time.

The free half is allowed to prove itself against the reader's past: a period
that already started, a window that has already run, a milestone they can
check against their own life. It is not allowed to say when the current
period ends or when the next one begins — that is the paid half's answer, and
the free page advertises it as locked.

So the rule is a date comparison, not a topic list: on or before the
consultation date, show it; after it, withhold it. Every surface that prints a
date into a free page goes through here so the two halves cannot drift.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Optional

__all__ = [
    "LOCKED_DATE_PHRASE",
    "LOCKED_WINDOW_PHRASE",
    "is_past",
    "may_show",
    "drop_future_dates",
    "strip_future_sentences",
]

# One phrase, so the page reads as a single voice and QA can grep for it. The
# inline form is a noun phrase because it substitutes into a running sentence
# where a date used to sit ("runs through a date in the full reading").
LOCKED_DATE_PHRASE = "a date in the full reading"
LOCKED_WINDOW_PHRASE = "dated in the full reading"

_MONTHS = ("january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december")
_MONTH_N = {name: i + 1 for i, name in enumerate(_MONTHS)}
_MONTH_N.update({name[:3]: i + 1 for i, name in enumerate(_MONTHS)})

# "October 2026", "Oct 2026", "11 Oct 2026", "2026-10", "2026-10-11"
_MONTH_YEAR = re.compile(
    r"\b(?:(\d{1,2})\s+)?(" + "|".join(_MONTHS) + r"|"
    + "|".join(m[:3] for m in _MONTHS) + r")\.?\s+(20\d\d)\b", re.IGNORECASE)
_ISO = re.compile(r"\b(20\d\d)-(\d{2})(?:-(\d{2}))?\b")
_BARE_YEAR = re.compile(r"\b(20\d\d)\b")

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _as_date(value: Any) -> Optional[date]:
    """Best-effort date from whatever the engines hand around."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    m = _ISO.search(text)
    if m:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3) or 1)
        try:
            return date(year, month, day)
        except ValueError:
            return None
    m = _MONTH_YEAR.search(text)
    if m:
        month = _MONTH_N.get(m.group(2).lower()[:3])
        if not month:
            return None
        try:
            return date(int(m.group(3)), month, int(m.group(1) or 1))
        except ValueError:
            return None
    return None


def is_past(value: Any, today: Optional[date] = None) -> bool:
    """True when ``value`` names a date at or before the consultation day.

    An unparseable value is not treated as past. A free surface that cannot
    tell what it is holding should withhold it.
    """
    d = _as_date(value)
    if d is None:
        return False
    ref = today or date.today()
    # Month-precision dates land on the 1st. The month in progress counts as
    # already-happened, otherwise the current period's own start month would
    # read as a future date for most of the month it begins in.
    return (d.year, d.month) <= (ref.year, ref.month)


def may_show(value: Any, today: Optional[date] = None, *,
             paid: bool = False) -> bool:
    """Whether a page at this access tier may print ``value``."""
    if paid:
        return True
    return is_past(value, today)


def drop_future_dates(text: Any, today: Optional[date] = None, *,
                      paid: bool = False,
                      replacement: str = LOCKED_DATE_PHRASE) -> str:
    """Swap future dates inside a sentence for the locked phrase.

    Used where the surrounding sentence is worth keeping — "this eases as the
    period turns over" still tells the reader something once the month is
    removed. Ranges collapse to one phrase rather than repeating it twice.
    """
    t = str(text or "")
    if paid or not t:
        return t
    ref = today or date.today()

    def sub(match: re.Match) -> str:
        return match.group(0) if is_past(match.group(0), ref) else replacement

    out = _MONTH_YEAR.sub(sub, t)
    out = _ISO.sub(sub, out)
    # A range that lost both ends says the same thing twice.
    out = re.sub(
        r"(" + re.escape(replacement) + r")\s*(?:[-–—]|to|through|until)\s*"
        + re.escape(replacement), r"\1", out, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", out).strip()


def strip_future_sentences(text: Any, today: Optional[date] = None, *,
                           paid: bool = False) -> str:
    """Drop whole sentences that lean on a future date.

    For prose where a half-redacted sentence would read worse than no
    sentence. A bare future year counts, since "the 2033 window" is the same
    disclosure as the month.
    """
    t = str(text or "")
    if paid or not t:
        return t
    ref = today or date.today()
    kept = []
    for sentence in _SENTENCE_SPLIT.split(t):
        dated = list(_MONTH_YEAR.finditer(sentence)) + list(_ISO.finditer(sentence))
        if any(not is_past(m.group(0), ref) for m in dated):
            continue
        if not dated and any(int(y) > ref.year
                             for y in _BARE_YEAR.findall(sentence)):
            continue
        kept.append(sentence.strip())
    return " ".join(x for x in kept if x).strip()
