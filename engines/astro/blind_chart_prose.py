#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blind chart (Nadi) - prediction-first HTML for Bhardwaj composite (rules17)."""
from __future__ import annotations

import html
from typing import Any


def _e(s: str) -> str:
    return html.escape(str(s))


def render_blind_chart_section(analysis: dict) -> str:
    if analysis.get("error"):
        return f"<div class='pred-card amber'><div class='pred-body'>{_e(analysis['error'])}</div></div>"

    sections = analysis.get("narratives", [])
    age = analysis.get("age", "")
    parts = [
        "<p class='fine'>Guru Rajesh blind-chart method (Nadi) - D1 karakas + Jupiter/Saturn progression. "
        "Educational only; +/- 1 year on timing.</p>",
        f"<div class='callout'><p class='pred'><strong>How to read this:</strong> Each block states what the chart "
        f"shows for your life first; the parenthetical line is the supporting placement. "
        f"Age {age}. Supply five dated milestones to lock timing to your biography.</p></div>",
    ]

    for sec in sections:
        tone = sec.get("tone", "neutral")
        body = " ".join(f"<p class='pred' style='margin:.55rem 0'>{_e(p)}</p>" for p in sec.get("paragraphs", []))
        parts.append(
            f"<div class='pred-card {tone}'><div class='pred-title'>{_e(sec.get('title', ''))}</div>"
            f"<div class='pred-body'>{body}</div></div>"
        )
    return "\n".join(parts)
