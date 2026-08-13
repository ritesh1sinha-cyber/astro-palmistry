"""Deterministic quality gates for customer-facing palm interpretation.

The image-quality score is part of the prediction contract: a poor photograph
must not be treated as if every fine line, special mark, or age position were
measured with the same confidence as a clear photograph.
"""
from __future__ import annotations

from typing import Any


def quality_policy(quality: dict[str, Any] | None) -> dict[str, Any]:
    q = quality or {}
    grade = str(q.get("grade") or "fair").lower()
    if grade not in {"good", "fair", "poor"}:
        grade = "fair"
    if grade == "good":
        return {
            "grade": grade,
            "interpretation_confidence": "high",
            "special_marks_allowed": True,
            "future_timing_allowed": True,
            "age_precision": "window",
            "note": "Clear enough for normal feature, mark and timing interpretation.",
        }
    if grade == "fair":
        return {
            "grade": grade,
            "interpretation_confidence": "moderate",
            "special_marks_allowed": False,
            "future_timing_allowed": True,
            "age_precision": "wider_window",
            "note": "Fine marks are withheld; line timing is presented as a wider age window.",
        }
    return {
        "grade": "poor",
        "interpretation_confidence": "low",
        "special_marks_allowed": False,
        "future_timing_allowed": False,
        "age_precision": "withheld",
        "note": "The image is not clear enough for fine marks or reliable age-position interpretation.",
    }


def apply_quality_gate(features: dict[str, Any]) -> dict[str, Any]:
    """Mutate a JSON-safe feature dict in place and return it.

    This is deliberately upstream of prediction/confluence so downstream
    modules cannot accidentally turn an uncertain measurement into a strong
    customer claim.
    """
    feats = features or {}
    q = feats.setdefault("quality", {})
    policy = quality_policy(q)
    q.update({
        "interpretation_confidence": policy["interpretation_confidence"],
        "special_marks_allowed": policy["special_marks_allowed"],
        "future_timing_allowed": policy["future_timing_allowed"],
        "age_precision": policy["age_precision"],
        "quality_note": policy["note"],
    })

    if not policy["special_marks_allowed"]:
        feats["special_marks"] = []

    if policy["age_precision"] == "wider_window":
        for line in (feats.get("lines") or {}).values():
            if isinstance(line, dict):
                line["timing_confidence"] = "moderate"
    elif policy["age_precision"] == "withheld":
        for line in (feats.get("lines") or {}).values():
            if isinstance(line, dict):
                line["timing_confidence"] = "withheld"
    return feats



_SPECIAL_MARK_TERMS = (
    "trident", "trishul", "star mark", "grille", "fish mark",
    "triangle mark", "cross mark", "square mark", "circle mark",
    "island mark", "fork mark", "lotus mark", "flag mark",
)


def _is_special_mark_item(item: dict[str, Any]) -> bool:
    """Identify a numbered finding whose meaning depends on a fine/special mark."""
    vals = []
    for key in ("kind", "category", "type", "id", "key", "title", "text", "statement"):
        v = item.get(key)
        if v is not None:
            vals.append(str(v).lower())
    conc = item.get("conclusive") or {}
    for key in ("verdict", "conclusion"):
        v = conc.get(key)
        if v:
            vals.append(str(v).lower())
    blob = " ".join(vals)
    return (
        "special_mark" in blob
        or "special mark" in blob
        or any(term in blob for term in _SPECIAL_MARK_TERMS)
        or str(item.get("category") or "").lower() == "marks"
        or str(item.get("kind") or "").lower() == "mark"
    )


def filter_special_mark_findings(
    checklist: list[dict[str, Any]], quality: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Remove fine-mark findings whenever the photo policy disallows them."""
    policy = quality_policy(quality)
    if policy["special_marks_allowed"]:
        return list(checklist or [])
    return [dict(item) for item in (checklist or []) if not _is_special_mark_item(item)]

def apply_checklist_quality_gate(checklist: list[dict[str, Any]], quality: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Apply the same quality contract to numbered findings/timing."""
    policy = quality_policy(quality)
    source = filter_special_mark_findings(checklist, quality)
    out = []
    for item in source:
        row = dict(item)
        if not policy["future_timing_allowed"]:
            row["timing"] = None
        elif policy["age_precision"] == "wider_window":
            t = dict(row.get("timing") or {})
            age = t.get("estimated_age")
            if isinstance(age, int):
                rng = t.get("age_range") or []
                if len(rng) == 2:
                    lo, hi = int(rng[0]), int(rng[1])
                else:
                    lo, hi = age - 3, age + 3
                t["age_range"] = [max(1, lo - 1), min(98, hi + 1)]
                t["timing_confidence"] = "moderate"
                t["summary"] = f"Around age {age}, within a wider palm-position window."
                row["timing"] = t
        out.append(row)
    return out
