#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Human prediction-first prose for BNN lane."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from bnn_analysis import BnnSection, analyze_all_chapters
from bnn_human import antardasha_card, human_intro, human_timing_table

if TYPE_CHECKING:
    from bnn_chart import BnnChart, BnnTiming


@dataclass
class LifeSection:
    title: str
    prediction: str
    fact: str
    tone: str = "neutral"
    domain: str = ""
    html_body: str = ""


def build_life_sections(ch: "BnnChart", bt: "BnnTiming", male: bool = True) -> list[LifeSection]:
    return [
        LifeSection(
            s.title, s.prediction, s.facts, s.tone, s.id,
            html_body=getattr(s, "html_body", ""),
        )
        for s in analyze_all_chapters(ch, bt, male=male)
    ]


def bnn_hero(ch: "BnnChart", bt: "BnnTiming") -> str:
    return human_intro(ch, bt)


def bnn_year_ahead_html(ch: "BnnChart", bt: "BnnTiming") -> str:
    table = human_timing_table(ch, bt)
    if table:
        return table
    today = date.today()
    cards = []
    shown = 0
    for w in bt.antar_windows():
        if w["end"] < today:
            continue
        if shown >= 4:
            break
        label = "active now" if w["start"] <= today < w["end"] else ("next up" if shown == 1 else "")
        tone = "green" if w["start"] <= today < w["end"] else ("good" if w["lord"] == "Venus" else "neutral")
        body = antardasha_card(ch, w["lord"], w["start"], w["end"], label)
        cards.append(f"<div class='pred-card {tone}'><p class='pred' style='margin:0;'>{body}</p></div>")
        shown += 1
    if not cards:
        return ""
    return "<h1>Next dasha windows</h1>" + "".join(cards)
