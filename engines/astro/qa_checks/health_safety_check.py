"""Health safety — no diagnosis or guaranteed recovery claims."""

from __future__ import annotations

import re

HEALTH_FORBIDDEN = re.compile(
    r"\b(recover(ed|y)? from illness|fight off illness|diagnos|disease|"
    r"medication|prescription|you will recover|guaranteed recovery|"
    r"cured|illness faster than average)\b",
    re.I,
)


def _load_patterns() -> list[re.Pattern[str]]:
    patterns = [HEALTH_FORBIDDEN]
    try:
        from interpretation.stage_config import health_language_rules
        rules = health_language_rules()
        for pat in rules.get("forbidden_patterns") or []:
            patterns.append(re.compile(pat, re.I))
    except Exception:  # noqa: BLE001
        pass
    return patterns


_PATTERNS = _load_patterns()


def health_violations(text: str) -> list[str]:
    found: list[str] = []
    for pat in _PATTERNS:
        m = pat.search(text or "")
        if m:
            found.append(m.group(0))
    return found


def wellbeing_replacement(theme: str = "medical") -> str:
    """Safe wellbeing wording from config."""
    try:
        from interpretation.stage_config import health_language_rules
        reps = health_language_rules().get("wellbeing_replacements") or {}
        return str(reps.get(theme) or reps.get("medical") or "")
    except Exception:  # noqa: BLE001
        return (
            "Consistency, rest and timely follow-up may be particularly "
            "important during demanding periods."
        )
