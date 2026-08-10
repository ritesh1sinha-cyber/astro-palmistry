"""Age / life-stage bands for manifestation vocabulary.

Age is computed at a target date (event / future-window start), not only
at report "today". All thresholds and area rules come from config/.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from interpretation.stage_config import (
    area_rule,
    band_for_age,
    default_manifestation,
    eligible_manifestations,
    narrative_area_for,
)


def _parse_dob(meta: dict) -> Optional[date]:
    raw = (meta or {}).get("dob") or ""
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except (TypeError, ValueError):
        return None


def dob_of(pc: dict) -> Optional[date]:
    return _parse_dob(pc.get("meta") or {})


def age_years_at(dob: Optional[date], target: date) -> int:
    """Completed age in whole years at target_date."""
    if not dob:
        return 0
    years = target.year - dob.year
    if (target.month, target.day) < (dob.month, dob.day):
        years -= 1
    return max(0, years)


def get_age_band_for_age(age: int) -> str:
    return band_for_age(age)


def get_age_band(dob: Optional[date], target_date: date) -> str:
    return get_age_band_for_age(age_years_at(dob, target_date))


def age_years(pc: dict, *, today: Optional[date] = None) -> int:
    """Reader age in whole years at report date (or supplied today)."""
    today = today or date.today()
    meta = pc.get("meta") or {}
    dob = _parse_dob(meta)
    if dob:
        return age_years_at(dob, today)
    try:
        return max(0, int(meta.get("age") or 0))
    except (TypeError, ValueError):
        return 0


def age_band(pc: dict, *, today: Optional[date] = None) -> str:
    """Age band at report date (legacy helper). Prefer age_band_at for windows."""
    return get_age_band_for_age(age_years(pc, today=today))


def age_band_at(pc: dict, target: Optional[date] = None) -> str:
    """Age band at a specific calendar date (past event or future window)."""
    target = target or date.today()
    dob = dob_of(pc)
    if dob:
        return get_age_band(dob, target)
    return age_band(pc, today=target)


def age_at_period(pc: dict, period_start: Optional[date]) -> int:
    if not period_start:
        return age_years(pc)
    dob = dob_of(pc)
    if dob:
        return age_years_at(dob, period_start)
    return age_years(pc)


def is_minor(band: str) -> bool:
    return band in ("child", "teen")


def is_pre_adult(band: str) -> bool:
    return band in ("child", "teen", "young_adult")


def narrative_area(area: str, band: str) -> str:
    """Map card area key to narrative domain for life stage (from config)."""
    return narrative_area_for(area, band)


def filter_scores_for_stage(
    scores: dict[str, int],
    *,
    area: str,
    age_band: str,
    narrative: str,
) -> dict[str, int]:
    """Drop manifestation classes not eligible for this life stage."""
    allowed = eligible_manifestations(age_band, narrative, area)
    if not allowed:
        return scores
    filtered = {k: v for k, v in scores.items() if k in allowed}
    if filtered:
        return filtered
    # Band-safe default — never restore adult-only classes
    fb = default_manifestation(age_band, narrative, area)
    return {fb: 1}
