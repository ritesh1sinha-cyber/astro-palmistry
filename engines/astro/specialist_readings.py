"""Canonical customer-safe bundle for the specialist astrology engines.

The individual engines intentionally keep their rich diagnostic output for
development and analyst use.  Customer reports consume this small projection
so the engines have one production entry point and sensitive diagnostics never
leak into prose by accident.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Any


_BLOCKED_TERMS = (
    "accident",
    "amputation",
    "childbirth",
    "disease",
    "death",
    "danger",
    "fertility",
    "ivf",
    "medical",
    "miscarriage",
    "mortality",
    "progeny",
    "sperm",
)
_BLOCKED_CATEGORIES = {
    "childbirth",
    "death",
    "medical",
    "progeny",
    "sports injury",
}


def _value(item: Any, key: str, default: Any = "") -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _customer_finding(item: Any) -> dict[str, Any] | None:
    condition_met = _value(item, "condition_met", None)
    if condition_met is False:
        return None
    category = str(_value(item, "category", "") or "").strip()
    title = str(_value(item, "title", "") or "").strip()
    prediction = str(
        _value(item, "prediction", "")
        or _value(item, "synthesis_prediction", "")
        or ""
    ).strip()
    if condition_met is None and not prediction:
        return None
    haystack = f"{category} {title} {prediction}".lower()
    if category.lower() in _BLOCKED_CATEGORIES:
        return None
    if any(term in haystack for term in _BLOCKED_TERMS):
        return None
    severity = str(_value(item, "severity", "") or _value(item, "assessment_badge", "info"))
    if severity.lower() == "critical":
        return None
    if not title or not prediction:
        return None
    return {
        "category": category[:60],
        "title": title[:160],
        "summary": prediction[:600],
        "severity": severity[:30],
        "planet": str(_value(item, "transit_planet", "") or "")[:30],
        "house": int(_value(item, "house", 0) or 0),
    }


def _project(items: Any, *, limit: int = 8) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items or []:
        row = _customer_finding(item)
        if row:
            out.append(row)
        if len(out) >= limit:
            break
    return out


def build_specialist_readings(
    pc: dict,
    *,
    today: date | None = None,
    gender: str = "male",
) -> dict[str, Any]:
    """Run the new specialist engines once for one report date.

    The returned structure contains only fired, customer-safe findings.  An
    unavailable engine is represented explicitly so callers can distinguish
    "no finding" from "engine did not run".
    """
    eval_date = today or date.today()
    analysis_datetime = datetime.combine(eval_date, time(12, 0))
    result: dict[str, Any] = {
        "evaluation_date": eval_date.isoformat(),
        "chandra_naadi": {"status": "unavailable", "findings": []},
        "rahu_ketu": {"status": "unavailable", "findings": []},
        "transit_matrix": {"status": "unavailable", "findings": []},
    }

    try:
        from chandra_naadi_analysis import analyze_chandra_naadi

        raw = analyze_chandra_naadi(
            pc, analysis_datetime=analysis_datetime, gender=gender
        )
        result["chandra_naadi"] = {
            "status": "available",
            "findings": _project(raw.get("all_readings"), limit=8),
        }
    except Exception as exc:  # noqa: BLE001
        print(f"[specialist_readings] Chandra Naadi unavailable: {exc}", flush=True)

    try:
        from rahu_ketu_analysis import analyze_rahu_ketu

        raw = analyze_rahu_ketu(
            pc, gender=gender, analysis_date=eval_date)
        result["rahu_ketu"] = {
            "status": "available",
            "findings": _project(raw.get("all_readings"), limit=8),
        }
    except Exception as exc:  # noqa: BLE001
        print(f"[specialist_readings] Rahu/Ketu unavailable: {exc}", flush=True)

    try:
        from transit_planet_analysis import analyze_transit_planet

        raw = analyze_transit_planet(
            pc, analysis_datetime=analysis_datetime, gender=gender
        )
        result["transit_matrix"] = {
            "status": "available",
            "findings": _project(raw.get("cards"), limit=8),
        }
    except Exception as exc:  # noqa: BLE001
        print(f"[specialist_readings] Transit matrix unavailable: {exc}", flush=True)

    return result
