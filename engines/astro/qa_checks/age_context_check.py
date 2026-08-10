"""Age-appropriate language checks — terms loaded from config."""

from __future__ import annotations

import re
from typing import Optional

try:
    from interpretation.stage_config import avoid_context_pattern, forbidden_terms
except Exception:  # noqa: BLE001
    def forbidden_terms(band: str) -> list[str]:  # type: ignore
        return []

    def avoid_context_pattern(band: str) -> Optional[re.Pattern[str]]:  # type: ignore
        return None


# Bands that require age-context filtering
_AGE_FILTER_BANDS = frozenset({"child", "teen", "young_adult"})


def _pattern_for(band: str) -> Optional[re.Pattern[str]]:
    pat = avoid_context_pattern(band)
    if pat:
        return pat
    terms = forbidden_terms(band)
    if not terms:
        return None
    escaped = "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True))
    return re.compile(rf"\b({escaped})\b", re.I)


def age_violations(text: str, age_band: str) -> list[str]:
    if age_band not in _AGE_FILTER_BANDS:
        return []
    pat = _pattern_for(age_band)
    if not pat:
        return []
    hits = pat.findall(text or "")
    return list(dict.fromkeys(hits))
