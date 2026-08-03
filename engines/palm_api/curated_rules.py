"""
Curated, verbatim book-cited rules keyed directly to measured palm features.

Unlike `rules_corpus.json` (auto-extracted, noisy), these rules are hand-checked
against the source books and matched on the *exact* feature attribute a point
reports (e.g. thumb length == "short"). They take priority for citations so the
quote that backs a verdict actually states that rule.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from palm_api.paths import DATA_DIR
from palm_api.report_format import book_label

_CURATED_SCORE = 99.0  # always outrank auto-extracted corpus rules


@lru_cache(maxsize=1)
def load_curated_rules() -> list[dict[str, Any]]:
    path = DATA_DIR / "palm_curated_rules.json"
    try:
        with open(path, encoding="utf-8") as fh:
            blob = json.load(fh)
    except (OSError, ValueError):
        return []
    rules = blob.get("rules") if isinstance(blob, dict) else blob
    return rules if isinstance(rules, list) else []


def _resolve_attrs(item: dict[str, Any], features: dict[str, Any]) -> dict[str, Any]:
    """Pull the attribute values relevant to this checklist item from features."""
    kind = item.get("kind")
    key = str(item.get("key", ""))
    morphology = features.get("morphology") or {}
    if kind == "line":
        return dict((features.get("lines") or {}).get(key) or {})
    if kind == "mount":
        return {"level": (features.get("mounts") or {}).get(key)}
    if kind == "finger":
        fingers = morphology.get("fingers") or features.get("fingers") or {}
        return dict(fingers.get(key) or {})
    if kind == "thumb":
        return dict(morphology.get("thumb") or {})
    if kind == "morphology":
        return {
            "hand_type": morphology.get("hand_type"),
            "index_vs_ring": morphology.get("index_vs_ring"),
            "finger_palm_ratio": morphology.get("finger_palm_ratio"),
        }
    if kind == "mark":
        return {"type": key or item.get("mark_type"), "zone": item.get("zone")}
    return {}


def _to_rule_dict(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "score": _CURATED_SCORE,
        "id": rule.get("id"),
        "book": rule.get("book"),
        "page": rule.get("page"),
        "category": rule.get("category", "general"),
        "text": rule.get("text"),
        "book_label": book_label(rule.get("book")),
        "curated": True,
    }


def match_curated_rules(item: dict[str, Any], features: dict[str, Any]) -> list[dict[str, Any]]:
    """Return curated rules whose `when` conditions all match this point, most specific first."""
    kind = item.get("kind")
    key = str(item.get("key", ""))
    attrs = _resolve_attrs(item, features)
    candidates: list[tuple[int, dict[str, Any]]] = []
    for rule in load_curated_rules():
        if rule.get("kind") != kind:
            continue
        rule_key = rule.get("key")
        if rule_key and str(rule_key) != key:
            continue
        when = rule.get("when") or {}
        if not when:
            continue
        ok = True
        for attr, want in when.items():
            have = attrs.get(attr)
            if have is None or str(have).lower() != str(want).lower():
                ok = False
                break
        if not ok:
            continue
        specificity = len(when) + (1 if rule_key else 0)
        candidates.append((specificity, rule))
    candidates.sort(key=lambda x: -x[0])
    return [_to_rule_dict(r) for _, r in candidates]
