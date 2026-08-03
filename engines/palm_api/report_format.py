"""Format predictions and book citations for the web report."""

from __future__ import annotations

import re
from typing import Any

BOOK_LABELS: dict[str, str] = {
    "apprentice_to_pro_24": "Apprentice to Pro (24 readings)",
    "case_studies_modern_50": "Modern Case Studies (50)",
    "easy_understanding_samudrik": "Easy Understanding of Samudrik",
    "palmistry_for_all": "Palmistry for All",
    "palmistry_how_to_master": "How to Master the Art of Palmistry",
    "practical_handbook_vol1": "Practical Handbook Vol. 1",
    "practical_handbook_vol2_marriage": "Practical Handbook Vol. 2 (Marriage)",
    "principles_self_learning": "Principles of Self-Learning",
    "secrets_profession_popularity": "Secrets of Profession & Popularity",
    "succinct_palmistry": "Succinct Palmistry",
}

CATEGORY_LABELS: dict[str, str] = {
    "vitality": "Life line & vitality",
    "mind": "Head line & mind",
    "heart": "Heart & relationships",
    "career": "Fate line & career",
    "fame": "Sun line & recognition",
    "fingers": "Fingers & hand shape",
    "mounts": "Mounts",
    "remedies": "Remedies",
    "travel": "Travel",
    "general": "General",
}

GENERIC_RE = re.compile(
    r"\b("
    r"legacy of chiromancy|fifth rule|read the whole palm|"
    r"look at your hand|stretch back|for a moment|"
    r"this book|introduction to|chapter one|table of contents|"
    r"no one point should be taken|value judgment|"
    r"self-learning|beginner|student of palmistry|art of palmistry"
    r")\b",
    re.I,
)

CATEGORY_ORDER = (
    "vitality",
    "mind",
    "heart",
    "career",
    "mounts",
    "fingers",
    "fame",
    "travel",
    "remedies",
    "general",
)


def book_label(book_id: str | None) -> str:
    if not book_id:
        return "Unknown source"
    return BOOK_LABELS.get(book_id, book_id.replace("_", " ").title())


def category_label(cat: str | None) -> str:
    return CATEGORY_LABELS.get(cat or "general", (cat or "general").title())


def is_generic_rule(text: str) -> bool:
    return bool(GENERIC_RE.search(text))


def trim_text(text: str, max_len: int = 320) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if max_len <= 0 or len(text) <= max_len:
        return text
    cut = text[:max_len].rsplit(" ", 1)[0]
    return cut + "…"


def enrich_prediction(entry: dict[str, Any], *, trim_for_snapshot: bool = True) -> dict[str, Any]:
    full = re.sub(r"\s+", " ", (entry.get("text") or "")).strip()
    return {
        **entry,
        "book_label": book_label(entry.get("book")),
        "category_label": category_label(entry.get("category")),
        "text": full,
        "text_short": trim_text(full, 280) if trim_for_snapshot else full,
    }


def build_highlights(
    by_category: dict[str, list[dict[str, Any]]],
    *,
    skip_categories: set[str] | None = None,
) -> list[dict[str, str]]:
    """One strongest citation per thematic block for the snapshot."""
    skip = skip_categories or set()
    out: list[dict[str, str]] = []
    for cat in CATEGORY_ORDER:
        if cat in skip:
            continue
        items = by_category.get(cat) or []
        if not items:
            continue
        best = items[0]
        out.append(
            {
                "category": cat,
                "label": category_label(cat),
                "text": trim_text(best.get("text", ""), 220),
                "source": f"{book_label(best.get('book'))}, p.{best.get('page', '?')}",
            }
        )
    return out
