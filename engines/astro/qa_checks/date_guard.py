"""Guard exact customer dates — only allow timing-engine windows."""

from __future__ import annotations

import re
from datetime import date
from typing import Iterable, Optional

_MONTH = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
_DATE_RE = re.compile(
    r"\b(" + "|".join(_MONTH) + r")\s+(\d{4})\b",
    re.I,
)


def _month_year(d: date) -> str:
    return f"{_MONTH[d.month - 1]} {d.year}"


def allowed_month_years(windows: Iterable[dict]) -> set[str]:
    """Collect month-year strings from timing-engine window dicts."""
    allowed: set[str] = set()
    for win in windows or []:
        for key in ("start", "end", "until", "from"):
            raw = win.get(key)
            if isinstance(raw, date):
                allowed.add(_month_year(raw))
            elif raw:
                try:
                    from report_confluence import _d
                    parsed = _d(raw)
                    if parsed:
                        allowed.add(_month_year(parsed))
                except Exception:  # noqa: BLE001
                    pass
    return allowed


def soften_unvalidated_dates(
    text: str,
    *,
    allowed: Optional[set[str]] = None,
) -> str:
    """Replace exact month-year phrases not in allowed timing windows."""
    if not text or not allowed:
        return text or ""
    out = text
    for match in _DATE_RE.finditer(text):
        phrase = match.group(0)
        normalized = f"{match.group(1).capitalize()} {match.group(2)}"
        if normalized not in allowed:
            out = out.replace(
                phrase,
                "later in the cycle",
                1,
            )
    return out


def guard_transit_deadline(
    scenario: str,
    until: Optional[date],
    *,
    supported: bool,
) -> str:
    """Ensure deadline phrases only appear when a real end date exists."""
    if not scenario or until is None:
        return re.sub(
            r"\b(?:Use it before|ease after)\s+[^.]+",
            "The more supportive part of this phase comes later in the cycle",
            scenario,
            count=1,
        )
    return scenario
