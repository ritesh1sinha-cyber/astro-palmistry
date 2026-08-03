#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge Mehta Modern Techniques blocks into Vimshottari report."""
from __future__ import annotations

import html
import json
from pathlib import Path

from mehta_analysis import MehtaSection, analyze_all_sections
from mehta_chart import MehtaChart
from mehta_prose import mehta_lord_table_rows, mehta_year_ahead_html
from report_language import client_prose

BASE = Path(__file__).resolve().parent
MEHTA_DATA = BASE / "mehta_book_data.json"


def _e(s: str) -> str:
    return html.escape(str(s))


def _load_book() -> dict:
    if not MEHTA_DATA.is_file():
        return {}
    return json.loads(MEHTA_DATA.read_text(encoding="utf-8"))


def build_mehta_chart(pc: dict) -> MehtaChart | None:
    book = _load_book()
    if not book:
        return None
    return MehtaChart(pc, book)


def _section_block(sec: MehtaSection) -> str:
    tone = {"good": "good", "amber": "amber"}.get(sec.tone, "")
    cls = f" sec {tone}" if tone else " sec"
    return (
        f"<div class='{cls.strip()}'>"
        f"<h1>{_e(sec.title)}</h1>"
        f"<p class='pred'>{_e(client_prose(sec.prediction))}</p>"
        f"<p class='fine'>({_e(sec.facts)})</p>"
        "</div>"
    )


def mehta_snapshot_html(chart: MehtaChart) -> str:
    intro = next((s for s in analyze_all_sections(chart) if s.id == "intro"), None)
    if not intro:
        return ""
    steps = chart.book.get("intro_steps", [])
    steps_html = ""
    if steps:
        items = "".join(f"<li>{_e(s)}</li>" for s in steps[:12])
        steps_html = (
            "<details class='appendix' style='margin:.75rem 0'>"
            "<summary>Mehta twelve-step method (reference)</summary>"
            f"<ol>{items}</ol></details>"
        )
    return (
        "<h1>Mehta Modern Techniques snapshot</h1>"
        "<p class='pred'>Mehta (rules4) judges the same chart by house lords, karakas, yogas, and navamsha cross-check. "
        "Vimshottari above gives <strong>when</strong>; Mehta below gives <strong>which life themes activate</strong> in each house.</p>"
        f"<div class='callout-mehta'><p class='pred' style='margin:0'>{_e(intro.prediction)}</p></div>"
        f"{steps_html}"
    )


def mehta_timing_html(chart: MehtaChart) -> str:
    return (
        "<h1>Mehta dasha windows (house-lord view)</h1>"
        + mehta_year_ahead_html(chart)
    )


def mehta_house_chapters_html(chart: MehtaChart) -> str:
    ids = {f"ch{i:02d}" for i in range(1, 13)}
    blocks = []
    for sec in analyze_all_sections(chart):
        if sec.id in ids:
            blocks.append(_section_block(sec))
    if not blocks:
        return ""
    return (
        "<h1>Mehta life reading by house (Chapters I-XII)</h1>"
        "<p class='fine'>Affirmative Mehta book lines fused with your placements - "
        "complements Vimshottari domain sections above.</p>"
        + "".join(blocks)
    )


def mehta_special_chapters_html(chart: MehtaChart) -> str:
    want = {"ch13", "ch14", "ch15", "ch17", "ch18", "ch19"}
    blocks = []
    for sec in analyze_all_sections(chart):
        if sec.id in want:
            blocks.append(_section_block(sec))
    return "".join(blocks)


def mehta_lord_table_html(chart: MehtaChart) -> str:
    rows = mehta_lord_table_rows(chart)
    if not rows:
        return ""
    body = "".join(
        f"<tr><td>{h}</td><td>{lord}</td><td>{occ}</td><td>{_e(client_prose(txt))}</td></tr>"
        for h, lord, occ, txt in rows
    )
    return (
        "<h2>Mehta house-lord table (reference)</h2>"
        "<table class='simple'><tr><th>House ruled</th><th>Lord</th><th>Sits in</th><th>Mehta read</th></tr>"
        + body
        + "</table>"
    )


def mehta_merged_body(chart: MehtaChart) -> str:
    """All Mehta HTML blocks for insertion into Vimshottari render."""
    return (
        mehta_snapshot_html(chart)
        + mehta_timing_html(chart)
        + mehta_house_chapters_html(chart)
        + mehta_special_chapters_html(chart)
    )
