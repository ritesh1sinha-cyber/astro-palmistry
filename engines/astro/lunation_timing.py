#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exact New Moon / Full Moon times and Boland ritual windows (rules44 Ch.3/Ch.6)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional

try:
    import swisseph as swe

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    _SWE = True
except Exception:
    _SWE = False


def _require_swe() -> None:
    if not _SWE:
        raise RuntimeError("pyswisseph required for lunation timing")


def _jd_ut(d: date, hour_ut: float = 12.0) -> float:
    _require_swe()
    return swe.julday(d.year, d.month, d.day, hour_ut)


def _elongation_deg(jd_ut: float) -> float:
    sun_lon = swe.calc_ut(jd_ut, swe.SUN, swe.FLG_SIDEREAL)[0][0] % 360.0
    moon_lon = swe.calc_ut(jd_ut, swe.MOON, swe.FLG_SIDEREAL)[0][0] % 360.0
    return (moon_lon - sun_lon) % 360.0


def _lunation_error(jd_ut: float, kind: str) -> float:
    e = _elongation_deg(jd_ut)
    if kind == "new_moon":
        return min(e, 360.0 - e)
    return abs(e - 180.0)


def _find_lunation_jd(anchor_jd: float, kind: str, direction: str) -> float:
    """Return JD (UT) of nearest prev/next new_moon or full_moon to anchor."""
    span = 16.0  # days; synodic month ~29.5
    if direction == "prev":
        lo, hi = anchor_jd - span, anchor_jd
    else:
        lo, hi = anchor_jd, anchor_jd + span
    for _ in range(64):
        m1 = lo + (hi - lo) / 3.0
        m2 = hi - (hi - lo) / 3.0
        if _lunation_error(m1, kind) < _lunation_error(m2, kind):
            hi = m2
        else:
            lo = m1
    return (lo + hi) / 2.0


def _jd_to_local_datetime(jd_ut: float, tz_hours: float) -> datetime:
    y, m, d, ut = swe.revjul(jd_ut, swe.GREG_CAL)
    base = datetime(y, m, d)
    return base + timedelta(hours=ut + tz_hours)


def _fmt_local(dt: datetime) -> str:
    return dt.strftime("%A %d %B %Y, %I:%M %p").lstrip("0").replace(" 0", " ")


def _tz_label(tz_hours: float) -> str:
    sign = "+" if tz_hours >= 0 else "-"
    h = int(abs(tz_hours))
    m = int(round((abs(tz_hours) - h) * 60))
    if m:
        return f"UTC{sign}{h}:{m:02d}"
    return f"UTC{sign}{h}"


def _local_day_bounds(target: date) -> tuple[datetime, datetime]:
    start = datetime(target.year, target.month, target.day)
    return start, start + timedelta(days=1)


def _find_exact_lunation_jd(anchor_jd: float, kind: str) -> tuple[float, float]:
    """Return (prev_jd, next_jd) of exact conjunction/opposition."""
    prev_jd = _find_lunation_jd(anchor_jd, kind, "prev")
    next_jd = _find_lunation_jd(anchor_jd, kind, "next")
    return prev_jd, next_jd


def _pick_new_moon_jd(target: date, tz_hours: float) -> Optional[float]:
    """
    Return exact New Moon JD if target local day overlaps Boland window
    [exact New Moon, exact + 3 days). Wishes are after exact NM (Ch.3).
    """
    local_noon_jd = _jd_ut(target, 12.0 - tz_hours)
    prev_jd, next_jd = _find_exact_lunation_jd(local_noon_jd, "new_moon")
    day_start, day_end = _local_day_bounds(target)
    for exact_jd in (prev_jd, next_jd):
        if _lunation_error(exact_jd, "new_moon") > 0.2:
            continue
        exact_local = _jd_to_local_datetime(exact_jd, tz_hours)
        window_end = exact_local + timedelta(days=3)
        if day_start < window_end and day_end > exact_local:
            return exact_jd
    return None


def is_new_moon_applicable(target: date, timezone: float = 5.5) -> bool:
    _require_swe()
    return _pick_new_moon_jd(target, timezone) is not None


def is_full_moon_applicable(target: date, timezone: float = 5.5) -> bool:
    """True when target day overlaps primary or night-before Full Moon ceremony."""
    _require_swe()
    local_noon_jd = _jd_ut(target, 12.0 - timezone)
    prev_jd, next_jd = _find_exact_lunation_jd(local_noon_jd, "full_moon")
    day_start, day_end = _local_day_bounds(target)
    for exact_jd in (prev_jd, next_jd):
        if _lunation_error(exact_jd, "full_moon") > 0.2:
            continue
        exact_local = _jd_to_local_datetime(exact_jd, timezone)
        night_start, night_end = _full_moon_ceremony_window(exact_local)
        alt_start = night_start - timedelta(days=1)
        alt_end = night_end - timedelta(days=1)
        for start, end in ((night_start, night_end), (alt_start, alt_end)):
            if day_start < end and day_end > start:
                return True
    return False


def _active_new_moon_jd(target: date, tz_hours: float) -> float:
    """New Moon JD for timing card; raises if not applicable."""
    jd = _pick_new_moon_jd(target, tz_hours)
    if jd is None:
        local_noon_jd = _jd_ut(target, 12.0 - tz_hours)
        _, next_jd = _find_exact_lunation_jd(local_noon_jd, "new_moon")
        return next_jd
    return jd


def _active_full_moon_jd(target: date, tz_hours: float) -> float:
    """Full Moon nearest to target (prev if today is FM/waning, else next)."""
    local_noon_jd = _jd_ut(target, 12.0 - tz_hours)
    prev_jd = _find_lunation_jd(local_noon_jd, "full_moon", "prev")
    next_jd = _find_lunation_jd(local_noon_jd, "full_moon", "next")
    prev_dist = abs(local_noon_jd - prev_jd)
    next_dist = abs(next_jd - local_noon_jd)
    return prev_jd if prev_dist <= next_dist else next_jd


def _full_moon_ceremony_window(exact_local: datetime) -> tuple[datetime, datetime]:
    """Night-of-Full-Moon window: evening before peak through following morning."""
    if exact_local.hour < 12:
        night = exact_local.date() - timedelta(days=1)
    else:
        night = exact_local.date()
    start = datetime(night.year, night.month, night.day, 18, 0)
    end = start + timedelta(hours=12)  # 6 PM -> 6 AM
    return start, end


def next_new_moon_display(target: date, timezone: float = 5.5) -> str:
    """Local date/time of the next exact New Moon after target morning."""
    _require_swe()
    local_noon_jd = _jd_ut(target, 12.0 - timezone)
    _, next_jd = _find_exact_lunation_jd(local_noon_jd, "new_moon")
    return _fmt_local(_jd_to_local_datetime(next_jd, timezone))


def compute_lunation_timing(
    target: date,
    *,
    kind: str,
    timezone: float = 5.5,
    place: str = "",
) -> Optional[dict[str, Any]]:
    """
    kind: 'new_moon' | 'full_moon'
    Returns exact local time plus Boland ritual start/end windows.
    """
    _require_swe()
    if kind == "new_moon":
        exact_jd = _pick_new_moon_jd(target, timezone)
        if exact_jd is None:
            return None
        exact_local = _jd_to_local_datetime(exact_jd, timezone)
        peak_end = exact_local + timedelta(hours=8)
        extended_end = exact_local + timedelta(days=3)
        local_noon_jd = _jd_ut(target, 12.0 - timezone)
        in_peak = exact_jd <= local_noon_jd <= exact_jd + (8.0 / 24.0)
        in_extended = exact_jd <= local_noon_jd <= exact_jd + 3.0
        return {
            "kind": "new_moon",
            "exact_local": exact_local.isoformat(),
            "exact_display": _fmt_local(exact_local),
            "peak_window_start_local": exact_local.isoformat(),
            "peak_window_start_display": _fmt_local(exact_local),
            "peak_window_end_local": peak_end.isoformat(),
            "peak_window_end_display": _fmt_local(peak_end),
            "extended_window_end_local": extended_end.isoformat(),
            "extended_window_end_display": _fmt_local(extended_end),
            "timezone": timezone,
            "timezone_label": _tz_label(timezone),
            "place": place,
            "in_peak_window": in_peak,
            "in_extended_window": in_extended,
            "note_peak": (
                "Best window (Boland Ch.3): as soon as possible after exact New Moon, "
                "ideally within 8 hours."
            ),
            "note_extended": (
                "Extended window (Boland Ch.3): up to 3 days after exact New Moon is acceptable."
            ),
        }
    if kind == "full_moon":
        if not is_full_moon_applicable(target, timezone):
            return None
        exact_jd = _active_full_moon_jd(target, timezone)
        exact_local = _jd_to_local_datetime(exact_jd, timezone)
        night_start, night_end = _full_moon_ceremony_window(exact_local)
        prev_night_start = night_start - timedelta(days=1)
        prev_night_end = night_end - timedelta(days=1)
        return {
            "kind": "full_moon",
            "exact_local": exact_local.isoformat(),
            "exact_display": _fmt_local(exact_local),
            "ceremony_start_local": night_start.isoformat(),
            "ceremony_start_display": _fmt_local(night_start),
            "ceremony_end_local": night_end.isoformat(),
            "ceremony_end_display": _fmt_local(night_end),
            "alt_ceremony_start_local": prev_night_start.isoformat(),
            "alt_ceremony_start_display": _fmt_local(prev_night_start),
            "alt_ceremony_end_local": prev_night_end.isoformat(),
            "alt_ceremony_end_display": _fmt_local(prev_night_end),
            "timezone": timezone,
            "timezone_label": _tz_label(timezone),
            "place": place,
            "note_ceremony": (
                "Primary ceremony night (Boland Ch.6): on the night of the Full Moon "
                "(evening through following morning, local birth-place time)."
            ),
            "note_alt": (
                "The night before exact Full Moon is also powerful for forgiveness work."
            ),
        }
    return None
