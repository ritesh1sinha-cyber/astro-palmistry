#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BNN conjunction pair parsing from book OCR."""
from __future__ import annotations

import re

from bnn_book_data import _norm_pair, humanize_bnn, load_bnn_book, sanitize_bnn_clause

_FEMALE_ONLY = re.compile(
    r"female chart|in females|molestation|rape|miscarriage|"
    r"inter-caste marriage|husband may live in a foreign|"
    r"charts of combination|possibility of$|especially severe for females|"
    r"paranormal molestation|untimely death of a brother|no elder brother|"
    r"death of a male family member|separation\.|divorce",
    re.I,
)

_CATEGORY_SPLIT = re.compile(
    r"(Personality\s*&?\s*Behavior|Family|Professional Life|Education|"
    r"Finance|Sister|Brother/Husband|Female Chart)\s*:",
    re.I,
)

_CLAIMED: set[str] = set()


def reset_claimed() -> None:
    _CLAIMED.clear()


def is_claimed(text: str) -> bool:
    return _fp(text) in _CLAIMED


def mark_claimed(text: str) -> None:
    if text:
        _CLAIMED.add(_fp(text))


def combination_raw(book: dict, a: str, b: str) -> str:
    combos = book.get("combinations", {})
    key = _norm_pair(a, b)
    entries = (
        combos.get(key)
        or combos.get(f"{a.title()}-{b.title()}")
        or combos.get(f"{b.title()}-{a.title()}")
        or []
    )
    if entries:
        return entries[0].get("text", "") if isinstance(entries[0], dict) else str(entries[0])
    return book.get("pairs_159", {}).get(key, "")


def _fp(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())[:120]


def _sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", text)
    out: list[str] = []
    for p in parts:
        p = p.strip().strip(":")
        if len(p) >= 28:
            out.append(p)
    return out


def _tag_category(sent: str) -> str:
    low = sent.lower()
    if any(w in low for w in ("education", "study", "learning", "school", "informed")):
        return "Education & wealth"
    if any(w in low for w in ("wife", "spouse", "marriage", "opposite sex", "sweet-talk")):
        return "Spouse & charm"
    if any(w in low for w in ("brother", "sister", "daughter", "grandparent")):
        return "Family"
    if any(w in low for w in ("vehicle", "metal", "land", "danger", "disputed")):
        return "Health & safety"
    if any(w in low for w in ("wealth", "earn", "finance", "comfortable")):
        return "Wealth & lifestyle"
    if any(w in low for w in ("courage", "anger", "bold", "jealousy", "bad deeds", "greenery", "house")):
        return "Personality"
    return "General"


def _parse_blocks(raw: str) -> list[tuple[str, str]]:
    parts = _CATEGORY_SPLIT.split(raw)
    if len(parts) <= 1:
        return [("General", raw)]
    blocks: list[tuple[str, str]] = []
    i = 1
    while i + 1 < len(parts):
        label = re.sub(r"\s+", " ", parts[i]).strip()
        body = parts[i + 1].strip()
        if label.lower() != "female chart":
            blocks.append((label, body))
        i += 2
    return blocks or [("General", raw)]


def _short_label(label: str) -> str:
    return {
        "personality & behavior": "Personality",
        "family": "Family",
        "professional life": "Career",
        "education": "Education",
        "finance": "Wealth",
    }.get(label.lower(), label)


def combination_bullets(
    book: dict,
    a: str,
    b: str,
    *,
    male: bool = True,
    max_n: int = 8,
    skip_fps: set[str] | None = None,
    claim: bool = True,
) -> list[str]:
    raw = sanitize_bnn_clause(combination_raw(book, a, b))
    if not raw:
        return []
    skip = skip_fps or set()
    bullets: list[str] = []
    for label, body in _parse_blocks(raw):
        if label.lower() == "female chart":
            continue
        for sent in _sentences(body):
            if male and _FEMALE_ONLY.search(sent):
                continue
            line = humanize_bnn(sent)
            if not line or _fp(line) in skip:
                continue
            cat = _short_label(label if label != "General" else _tag_category(line))
            tagged = f"{cat}: {line}" if not line.lower().startswith(cat.lower()) else line
            if claim:
                mark_claimed(line)
            bullets.append(tagged)
            if len(bullets) >= max_n:
                return bullets
    return bullets


def pair_section_html(
    ch,
    a: str,
    b: str,
    *,
    male: bool = True,
    reg=None,
) -> tuple[str, str, str]:
    """Return (title, fact_line, html_body) for one conjunction."""
    book = load_bnn_book()
    sign = ch.sign(a) if a in ch.planets else ""
    house = ch.h(a) if a in ch.planets else 0
    title = f"{a}-{b} conjunction ({sign}, house {house})"
    fact = f"{sign} - house {house} - BNN Combination from Avasthi manual"

    bullets = combination_bullets(book, a, b, male=male, max_n=8, claim=True)
    if not bullets:
        fallback = humanize_bnn(combination_raw(book, a, b)[:400])
        bullets = [fallback] if fallback else []

    if not bullets:
        return title, fact, "<p class='pred'>No book clause matched this pair.</p>"

    items = "".join(f"<li>{_esc(x)}</li>" for x in bullets)
    entries = book.get("combinations", {}).get(_norm_pair(a, b), [])
    combo_num = entries[0].get("num", "") if entries and isinstance(entries[0], dict) else ""
    if combo_num:
        intro = (
            f"<p class='pred'><strong>Combination {combo_num}</strong> ({a}-{b} in {sign}, house {house}): "
            f"book themes applied to your D1 chart.</p>"
        )
    else:
        intro = f"<p class='pred'>BNN manual themes for {a}-{b} in {sign}, house {house}:</p>"
    return title, fact, intro + f"<ul>{items}</ul>"


def _esc(s: str) -> str:
    import html
    return html.escape(s)
