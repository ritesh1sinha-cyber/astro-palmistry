#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge Jaimini books lane (Goel + Gems + Jewels) into Chara dasha report."""
from __future__ import annotations

import html
from typing import TYPE_CHECKING

from jaimini_book_data import load_book
from jaimini_books_analysis import BookSection, analyze_all_sections
from jaimini_books_chart import JaiminiBooksChart, ROLE_ORDER, ROLE_SHORT
from jaimini_books_prose import LifeSection, build_life_sections
from jaimini_prose import (
    book_appendix,
    jaimini_intro_callout,
    jewels_argala_note,
    kl_corpus_section,
    raja_yoga_section,
)

if TYPE_CHECKING:
    from vedic_jaimini_report import Jaimini


def _e(s: str) -> str:
    return html.escape(str(s))


def build_books_chart(pc: dict) -> JaiminiBooksChart:
    return JaiminiBooksChart.from_precompute(pc)


def _life_block(sec: LifeSection) -> str:
    tone = {"good": "good", "attention": "amber"}.get(sec.tone, "")
    cls = f" sec {tone}" if tone else " sec"
    fact = f'<p class="fine">({_e(sec.fact)})</p>' if sec.fact else ""
    return (
        f'<div class="{cls.strip()}">'
        f"<h1>{_e(sec.title)}</h1>"
        f'<p class="pred">{_e(sec.prediction)}</p>'
        f"{fact}"
        "</div>"
    )


def _book_block(sec: BookSection) -> str:
    tone = {"good": "good", "attention": "amber"}.get(sec.tone, "")
    cls = f" sec {tone}" if tone else " sec"
    quote = f'<p class="fine">Book: {_e(sec.book_quote)}</p>' if sec.book_quote else ""
    return (
        f'<div class="{cls.strip()}">'
        f"<h1>{_e(sec.title)}</h1>"
        f'<p class="pred">{_e(sec.prediction)}</p>'
        f"{quote}"
        f'<p class="fine">({_e(sec.fact)})</p>'
        "</div>"
    )


def _books_karaka_table(chart: JaiminiBooksChart) -> str:
    rows = []
    for r in ROLE_ORDER:
        k = chart.role(r)
        if not k:
            continue
        rows.append(
            f"<tr><td>{ROLE_SHORT[r]}</td><td><strong>{k['planet']}</strong></td>"
            f"<td>{k['sign']}</td><td>{k['house']} from lagna</td></tr>"
        )
    if not rows:
        return ""
    return (
        "<h2>Cara karakas (books reference)</h2>"
        "<table class='simple'><tr><th>Role</th><th>Planet</th><th>Sign</th><th>House</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def books_prose_html(chart: JaiminiBooksChart) -> str:
    blocks = []
    for sec in build_life_sections(chart):
        if sec.domain == "snapshot":
            continue
        blocks.append(_life_block(sec))
    return "".join(blocks)


def books_analysis_html(chart: JaiminiBooksChart, book: dict) -> str:
    blocks = []
    for sec in analyze_all_sections(chart, book):
        blocks.append(_book_block(sec))
    return "".join(blocks)


def prose_bridge_html(jm: "Jaimini", book: dict) -> str:
    """KL corpus + raja yoga + Jewels argala using shared Jaimini engine."""
    from vedic_jaimini_report import house_of, sign_aspects_from, sign_at

    parts = []
    kl = kl_corpus_section(jm, book)
    if kl:
        parts.append(f"<h1>Karakamsha depth (Gems rules30)</h1>{kl}")
    raja = raja_yoga_section(jm, book, sign_aspects_from, house_of)
    if raja:
        parts.append(f"<h1>Raja yoga scan (Goel rules6)</h1>{raja}")
    jewels = jewels_argala_note(jm, book, sign_at)
    if jewels:
        parts.append(jewels)
    return "".join(parts)


def books_merged_body(jm: "Jaimini", pc: dict, book: dict | None = None) -> str:
    """All books HTML for insertion into Chara dasha render."""
    book = book or load_book()
    chart = build_books_chart(pc)
    hero = next((s for s in build_life_sections(chart) if s.domain == "snapshot"), None)
    hero_html = ""
    if hero:
        hero_html = f'<div class="callout-books"><p class="pred" style="margin:0">{_e(hero.prediction)}</p></div>'

    matched = len(analyze_all_sections(chart, book))
    return (
        jaimini_intro_callout(book)
        + "<h1>Jaimini book depth (Goel + Gems + Jewels)</h1>"
        + "<p class='pred'>Chara dasha above gives <strong>when</strong> each life season runs. "
        "This block gives <strong>structure</strong>: karakas, Karakamsha houses, argala, and status yogas "
        "from the three Jaimini books (rules6, rules30, rules31).</p>"
        + hero_html
        + prose_bridge_html(jm, book)
        + "<h1>Life themes from Karakamsha &amp; karakas</h1>"
        + books_prose_html(chart)
        + "<h1>Book-backed checks (Goel / Gems / Jewels)</h1>"
        + books_analysis_html(chart, book)
        + book_appendix(book, matched)
        + _books_karaka_table(chart)
    )
