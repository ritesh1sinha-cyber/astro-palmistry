#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Concise Goel health section - confluence-only predictions (70%+)."""
from __future__ import annotations

import html
from typing import Any

from goel_disease_confluence import build_health_confluence


def _e(s: str) -> str:
    return html.escape(str(s))


def render_disease_section(analysis: dict[str, Any], pc: dict | None = None) -> str:
    if analysis.get("error"):
        return f"<div class='pred-card amber'><div class='pred-body'>{_e(analysis['error'])}</div></div>"

    conf = build_health_confluence(analysis, pc)
    snap = conf.get("snapshot", {})
    preds = conf.get("predictions", [])
    min_pct = conf.get("min_pct", 70)

    parts = [
        f"<p class='fine'>{_e(analysis.get('disclaimer', ''))}</p>",
    ]

    # Snapshot - 3 short lines max
    parts.append("<div class='callout'>")
    if snap.get("constitution"):
        parts.append(f"<p class='pred'><strong>Constitution:</strong> {_e(snap['constitution'])}</p>")
    if snap.get("active_window"):
        parts.append(f"<p class='pred'>{_e(snap['active_window'])}</p>")
    if snap.get("next_window"):
        parts.append(f"<p class='pred'>{_e(snap['next_window'])}</p>")
    parts.append(f"<p class='pred'><strong>Confirmed focus (&ge;{min_pct}% match):</strong> {_e(snap.get('focus', ''))}</p>")
    parts.append("</div>")

    if not preds:
        parts.append(
            "<div class='pred-card neutral'><div class='pred-body'>"
            "No single body-system theme reached 70% agreement across D1, D3, D6, D27, "
            "and nakshatra layers in your chart. Treat this as a low-specificity map - "
            "routine checkups and general wellness habits are enough unless symptoms appear."
            "</div></div>"
        )
    else:
        parts.append(
            f"<p class='lead'>Only patterns where at least <strong>{min_pct}%</strong> of Goel "
            f"layers agree are listed below.</p>"
        )
        for p in preds:
            tone = "amber" if p["match_pct"] >= 85 else "green"
            watch = "; ".join(p.get("watch", []))
            agree = "; ".join(p.get("lanes_hit", [])[:4])
            parts.append(f"<div class='pred-card {tone}'>")
            parts.append(
                f"<div class='pred-head'>{_e(p['title'])} "
                f"<span class='badge hi'>{p['match_pct']}% match</span></div>"
            )
            parts.append(f"<div class='pred-body'>")
            parts.append(f"<p>{_e(p['prediction'])}</p>")
            if agree:
                parts.append(f"<p><strong>Chart agrees:</strong> {_e(agree)}</p>")
            if watch:
                parts.append(f"<p><strong>When:</strong> {_e(watch)}</p>")
            parts.append(f"<p><strong>Prevention:</strong> {_e(p['preventive'])}</p>")
            parts.append("</div></div>")

    # Compact remedies � top 2 chart-specific only
    rem = [r for r in analysis.get("remedies", []) if r.get("planet") != "General"][:2]
    if rem:
        parts.append("<h2 style='font-size:1rem;margin-top:1rem'>Support (this chart)</h2>")
        for r in rem:
            why = ", ".join(r.get("why", [])[:2])
            parts.append(
                f"<div class='pred-card amber'><div class='pred-body'>"
                f"<strong>{_e(r['planet'])}</strong> - {_e(why)}. "
                f"{_e(r.get('mantra', ''))}. {_e(r.get('charity', ''))}"
                f"</div></div>"
            )

    # Collapsed evidence for auditors
    hits_all = []
    for p in preds:
        hits_all.extend(p.get("lanes_hit", []))
    if hits_all:
        rows = "".join(f"<li>{_e(x)}</li>" for x in hits_all[:12])
        parts.append(
            f"<details class='appendix'><summary>Confluence lanes (technical)</summary>"
            f"<ul style='font-size:.85rem'>{rows}</ul></details>"
        )

    return "\n".join(parts)
