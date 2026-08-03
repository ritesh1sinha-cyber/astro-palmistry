"""Attach book predictions to numbered palm checklist items."""

from __future__ import annotations

from typing import Any

from palm_api.conclusive import build_conclusive_reading, match_rules_for_point
from palm_api.report_format import book_label
from palm_api.timing import estimate_point_timing

LINE_KEY_TO_CATEGORY = {
    "life": "vitality",
    "head": "mind",
    "heart": "heart",
    "fate": "career",
}


def _quote_brief(q: dict[str, Any]) -> dict[str, Any]:
    return {
        "text": q.get("text") or q.get("text_short", ""),
        "book": q.get("book"),
        "book_label": q.get("book_label") or book_label(q.get("book")),
        "page": q.get("page"),
        "score": q.get("score"),
        "is_supporting": q.get("is_supporting", True),
    }


def enrich_checklist_with_predictions(
    checklist: list[dict[str, Any]],
    prediction: dict[str, Any],
    *,
    features: dict[str, Any] | None = None,
    line_groups: dict[str, list[dict[str, Any]]] | None = None,
    palm_size: int = 400,
    corpus: dict[str, Any] | None = None,
    lines: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Each numbered palm finding: conclusive verdict + timing + supporting book quotes."""
    groups = line_groups or {}
    feats = features or {}
    line_props = lines or feats.get("lines") or {}
    out: list[dict[str, Any]] = []

    for item in checklist:
        entry = dict(item)
        kind = item.get("kind")
        key = item.get("key", "")
        timing = None

        if kind == "line":
            props = line_props.get(key) or {}
            seg_n = props.get("segment_count") if props.get("detected") else None
            timing = estimate_point_timing(
                key,
                item.get("x"),
                item.get("y"),
                groups.get(key) or [],
                palm_size,
                segment_count=seg_n,
            )
            if timing:
                entry["timing"] = timing

        matched: list[dict[str, Any]] = []
        if corpus and feats:
            matched = match_rules_for_point(item, feats, corpus, limit=3)

        conclusive = build_conclusive_reading(
            item,
            features=feats,
            timing=timing,
            corpus=corpus or {},
            matched_rules=matched,
        )
        entry["conclusive"] = conclusive

        entry["book_quotes"] = [
            {**_quote_brief(r), "is_supporting": True} for r in matched[:2]
        ]
        out.append(entry)

    return out


def linked_prediction_count(checklist: list[dict[str, Any]]) -> int:
    return sum(len(it.get("book_quotes") or []) for it in checklist)
