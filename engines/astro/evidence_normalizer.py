"""Normalize raw technique votes into customer-safe canonical evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

_METHOD_CUSTOMER = {
    "the classical method": "Birth-chart structure",
    "the strength-scoring method": "Point-score method",
    "occupancy": "Birth-chart structure",
    "the cancellation rule": "Birth-chart structure",
    "chart combinations": "Birth-chart structure",
    "the confirmation chart": "Divisional-chart confirmation",
    "the cross-check chart": "Divisional-chart confirmation",
    "the nadi method": "Case-based confirmation",
    "the sub-lord method": "Specialist timing cross-check",
    "the karaka method": "Life-pattern cross-check",
    "the modern-technique method": "Modern technique",
    "the case-book method": "Case-based confirmation",
    "the vulnerability-indication method": "Wellbeing indicators",
    "the birth-star method": "Birth-pattern cross-check",
    "the lifespan method": "Long-term pattern indicators",
    "the point-score method": "Point-score method",
    "the classical rule-book": "Classical rule check",
    "the sky right now": "Current transit",
    "the period clock": "Dasha timing",
    "dasha timing": "Dasha timing",
    "a further classical method": "Classical confirmation",
}

_FAMILY_TAGS: dict[str, list[str]] = {
    "career": ["career_visibility", "responsibility", "professional_progress"],
    "money": ["financial_progress", "resource_discipline", "income"],
    "love": ["relationship", "partnership", "emotional_expression"],
    "home": ["domestic_stability", "family_responsibility"],
    "children": ["creativity", "children", "expression"],
    "health": ["wellbeing", "routine", "preventive_attention"],
    "learning": ["learning", "guidance", "direction"],
    "inner": ["inner_life", "reflection", "spiritual"],
}

# Classical / case-book stock that must never be truncated into customer HTML.
_CLASSICAL_RAW = re.compile(
    r"debt-ridden|hurt by fire|free from enemies|strong appetite|"
    r"you will be|bereaved|inauspicious deeds|manglik|"
    r"blood disorders|high blood pressure|"
    r"Existing chart-rule|area ruler|"
    r"Combination\s+\d+|recognition_tag_|"
    r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+house|"
    r"8th lord|9th lord|10th lord|11th lord|12th lord|"
    r"sub[- ]lord|karakamsa|atmakaraka|cusp|"
    r"nakshatra|varga|lagna|bhava|jamakkol|prashna kundali|"
    r"case-book|technical reason)\b",
    re.I,
)

# Technical vote prose is useful to the mathematics layer but is never a
# semantic customer fact.  Detect the common forms at the canonical boundary
# so they are replaced by an area-level semantic fallback instead of being
# merely clipped or rewritten later in HTML.
_TECHNICAL_RAW = re.compile(
    r"\b(?:rules?\s+it|house\s+strength\s+\d+(?:\.\d+)?\s+of\s+\d+|"
    r"sit(?:s|\s+here)|placed\s+in\s+your\s+\d+(?:st|nd|rd|th)|"
    r"ninth-part\s+chart|birth[- ]chart\s+promise|"
    r"the\s+(?:classical|confirmation|cross-check|strength-scoring)\s+method)\b",
    re.I,
)


@dataclass
class CanonicalEvidence:
    method_id: str
    method_label: str
    family: str
    direction: str
    strength: float
    confidence: float
    semantic_tags: list[str] = field(default_factory=list)
    normalized_reason: str = ""


def _customer_method(method: str) -> str:
    raw = str(method or "").strip()
    if raw in _METHOD_CUSTOMER:
        return _METHOD_CUSTOMER[raw]
    low = raw.lower()
    for key, label in _METHOD_CUSTOMER.items():
        if key in low or low in key:
            return label
    if "transit" in low or "sky" in low:
        return "Current transit"
    if "dasha" in low or "period" in low or "yogini" in low:
        return "Dasha timing"
    if "varga" in low or "chart" in low:
        return "Divisional-chart confirmation"
    return "Astrology method"


def _family_for_method(method: str) -> str:
    try:
        import report_confluence as CF
        return CF._family_for_method(method)
    except Exception:  # noqa: BLE001
        return "specialist"


def _direction_from_value(value: float) -> str:
    if value > 0.4:
        return "support"
    if value < -0.4:
        return "caution"
    return "neutral"


def _semantic_tags(area: str, direction: str) -> list[str]:
    base = list(_FAMILY_TAGS.get(area, ["life_pattern"]))
    if direction == "caution":
        base.append("pressure")
    elif direction == "support":
        base.append("progress")
    return base[:4]


def _safe_fallback(
    *,
    method_label: str,
    direction: str,
    area: str = "",
    seed: str = "",
) -> str:
    try:
        from qa_checks.customer_text_sanitizer import sanitize_customer_text
        return sanitize_customer_text(
            "",
            method_label=method_label,
            direction=direction,
            area=area,
            seed=seed or method_label,
        )
    except Exception:  # noqa: BLE001
        bucket = (direction or "").lower()
        if bucket in ("support", "up"):
            return f"{method_label} supports this part of the reading."
        if bucket in ("caution", "down"):
            return (
                f"{method_label} suggests more care with routine, "
                f"discipline and avoidable risk."
            )
        return f"{method_label} contributes to this reading."


def _normalize_reason_text(
    because: str,
    *,
    method_label: str,
    direction: str,
    area: str = "",
) -> str:
    """Never return truncated classical prose — replace, do not clip."""
    raw = str(because or "").strip()
    if not raw or _CLASSICAL_RAW.search(raw) or _TECHNICAL_RAW.search(raw):
        return _safe_fallback(
            method_label=method_label, direction=direction, area=area, seed=raw[:48],
        )

    try:
        from qa_checks.customer_text_sanitizer import (
            is_customer_safe,
            sanitize_customer_text,
        )
        if not is_customer_safe(raw, area=area):
            return sanitize_customer_text(
                raw,
                method_label=method_label,
                direction=direction,
                area=area,
                seed=raw[:48],
            )
        cleaned = sanitize_customer_text(
            raw,
            method_label=method_label,
            direction=direction,
            area=area,
        )
        if cleaned and is_customer_safe(cleaned, area=area):
            return cleaned
    except Exception:  # noqa: BLE001
        pass

    return _safe_fallback(
        method_label=method_label, direction=direction, area=area, seed=raw[:48],
    )


def normalize_vote(
    vote: Any,
    *,
    area: str = "",
    family: str = "",
) -> CanonicalEvidence:
    """Convert a raw Vote into customer-safe canonical evidence."""
    method = str(getattr(vote, "method", "") or "")
    value = float(getattr(vote, "value", 0) or 0)
    because = str(getattr(vote, "because", "") or "")
    direction = _direction_from_value(value)
    fam = family or _family_for_method(method)
    label = _customer_method(method)
    reason = _normalize_reason_text(
        because, method_label=label, direction=direction, area=area)
    return CanonicalEvidence(
        method_id=method or fam,
        method_label=label,
        family=fam,
        direction=direction,
        strength=min(1.0, abs(value) / 2.0),
        confidence=min(1.0, 0.45 + abs(value) * 0.25),
        semantic_tags=_semantic_tags(area, direction),
        normalized_reason=reason,
    )


def normalize_classical_evidence(
    vote: Any, *, area: str = "",
) -> CanonicalEvidence:
    """Document-named entry point — classical / rule-book votes."""
    return normalize_vote(vote, area=area, family="classical")


def normalize_casebook_evidence(
    vote: Any, *, area: str = "",
) -> CanonicalEvidence:
    """Document-named entry point — Bhardwaj / case-book votes."""
    return normalize_vote(vote, area=area, family="specialist")


def normalize_specialist_evidence(
    vote: Any, *, area: str = "",
) -> CanonicalEvidence:
    """Document-named entry point — KP / Jaimini / Goel / etc."""
    return normalize_vote(vote, area=area, family="specialist")
