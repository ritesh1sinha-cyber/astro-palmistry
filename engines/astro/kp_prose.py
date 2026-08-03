#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Human prediction-first prose for KP lane."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from kp_analysis import KPSection, analyze_all_chapters
from kp_human import antardasha_card, human_intro, human_now_callout, human_timing_table

if TYPE_CHECKING:
    from kp_chart import KPChart


@dataclass
class LifeSection:
    title: str
    prediction: str
    fact: str
    tone: str = "neutral"
    domain: str = ""
    html_body: str = ""


def build_life_sections(kp: "KPChart") -> list[LifeSection]:
    return [
        LifeSection(
            s.title, s.prediction, s.facts, s.tone, s.id,
            html_body=getattr(s, "html_body", ""),
        )
        for s in analyze_all_chapters(kp)
    ]


def kp_hero(kp: "KPChart") -> str:
    return human_intro(kp)


def kp_now_callout(kp: "KPChart") -> str:
    return human_now_callout(kp)


def kp_year_ahead_html(kp: "KPChart") -> str:
    table = human_timing_table(kp)
    if table:
        return table
    today = date.today()
    cards: list[str] = []
    shown = 0
    for w in kp.antar_windows():
        if w["end"] < today:
            continue
        if shown >= 4:
            break
        label = "active now" if w["start"] <= today < w["end"] else ("next up" if shown == 1 else "")
        tone = "green" if w["start"] <= today < w["end"] else ("good" if w["lord"] == "Venus" else "neutral")
        body = antardasha_card(kp, w["lord"], w["start"], w["end"], label)
        cards.append(f"<div class='pred-card {tone}'><p class='pred' style='margin:0;'>{body}</p></div>")
        shown += 1
    if not cards:
        return ""
    return "<h1>Timing - dasha windows</h1>" + "".join(cards)
