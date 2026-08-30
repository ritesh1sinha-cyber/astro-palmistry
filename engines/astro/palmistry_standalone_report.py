#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
palmistry_standalone_report.py — Standalone Palmistry Consultation HTML Report Generator

Renders an executive, responsive HTML report reflecting the face-to-face consultation tone,
integrating dermatoglyphic neural timing and computer vision traced ridge models.
"""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Any

from palmistry_consultation_reading import generate_palm_consultation_sections


def _e(s: Any) -> str:
    return html.escape(str(s if s is not None else ""))


def _css() -> str:
    return """
:root {
    --bg: #0b132b;
    --card: #1c2541;
    --card-sub: #3a506b;
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
    --accent: #48cae4;
    --border: #2c3e66;
    --critical: #ef4444;
    --warning: #f59e0b;
    --positive: #06d6a0;
    --info: #48cae4;
}

* { box-sizing: border-box; }
body {
    margin: 0;
    padding: 24px 16px;
    background-color: var(--bg);
    color: var(--text-main);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    line-height: 1.65;
    font-size: 15px;
}

.wrap {
    max-width: 880px;
    margin: 0 auto;
}

.hero {
    background: linear-gradient(135deg, #1c2541 0%, #0b132b 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 26px 30px;
    margin-bottom: 24px;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
}

.hero h1 {
    margin: 0 0 4px 0;
    font-size: 24px;
    font-weight: 700;
    color: var(--text-main);
}

.hero .subtitle {
    color: var(--accent);
    font-size: 13.5px;
    margin-bottom: 16px;
}

.meta-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.chip {
    background: rgba(11, 19, 43, 0.8);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 4px 14px;
    font-size: 12.5px;
    color: var(--text-muted);
}
.chip b { color: var(--text-main); }

.summary-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 22px 24px;
    margin-bottom: 20px;
}

.summary-card.accent { border-left: 4px solid var(--accent); }
.summary-card.warn   { border-left: 4px solid var(--warning); }
.summary-card.pos    { border-left: 4px solid var(--positive); }
.summary-card.info   { border-left: 4px solid var(--info); }

.summary-card h2 {
    margin: 0 0 14px 0;
    font-size: 18px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.summary-card.accent h2 { color: var(--accent); }
.summary-card.warn h2   { color: var(--warning); }
.summary-card.pos h2    { color: var(--positive); }
.summary-card.info h2   { color: var(--info); }

.narrative-p {
    margin: 0;
    color: #e2e8f0;
    font-size: 14.5px;
    line-height: 1.68;
}

.minor-lines-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin-top: 14px;
}
@media (max-width: 640px) {
    .minor-lines-grid { grid-template-columns: 1fr; }
}

.minor-card {
    background: rgba(11, 19, 43, 0.6);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px;
}
.minor-card h3 {
    margin: 0 0 4px 0;
    font-size: 14px;
    color: var(--accent);
}
.minor-card .status {
    font-size: 11.5px;
    font-weight: 600;
    color: var(--positive);
    margin-bottom: 6px;
}
.minor-card p {
    margin: 0;
    font-size: 13px;
    color: #cbd5e1;
    line-height: 1.5;
}

.timing-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 14px;
    font-size: 13.5px;
}
.timing-table th {
    text-align: left;
    padding: 8px 12px;
    background: rgba(11, 19, 43, 0.6);
    border-bottom: 1px solid var(--border);
    color: var(--accent);
}
.timing-table td {
    padding: 9px 12px;
    border-bottom: 1px solid rgba(44, 62, 102, 0.4);
    color: #cbd5e1;
}

.curiosity-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin-top: 14px;
}
@media (max-width: 640px) {
    .curiosity-grid { grid-template-columns: 1fr; }
}

.curiosity-card {
    background: rgba(11, 19, 43, 0.6);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px;
}
.curiosity-card h3 {
    margin: 0 0 4px 0;
    font-size: 14.5px;
    color: var(--accent);
}
.curiosity-card .sub {
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 8px;
}
.curiosity-card p {
    margin: 0;
    font-size: 13px;
    color: #cbd5e1;
    line-height: 1.55;
}
.curiosity-card .insight {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px dashed rgba(44, 62, 102, 0.6);
    font-size: 12.5px;
    color: #a7f3d0;
}

.timing-badge {
    display: inline-block;
    background: rgba(72, 202, 228, 0.15);
    border: 1px solid var(--accent);
    color: var(--accent);
    font-size: 12px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 6px;
}

.counsel-box {
    background: rgba(6, 214, 160, 0.08);
    border: 1px solid rgba(6, 214, 160, 0.25);
    border-radius: 12px;
    padding: 20px 24px;
    margin-top: 24px;
}
.counsel-box h2 {
    color: var(--positive);
    margin: 0 0 12px 0;
    font-size: 18px;
}
.counsel-box ul {
    margin: 0;
    padding-left: 20px;
    color: #d1fae5;
    font-size: 14.5px;
    line-height: 1.65;
}
.counsel-box li {
    margin-bottom: 10px;
}
.counsel-box li:last-child { margin-bottom: 0; }

.footer {
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
    text-align: center;
    color: var(--text-muted);
    font-size: 12px;
}
"""


def generate_standalone_palmistry_html(
    analysis_res: dict,
) -> str:
    """Generate executive standalone Palmistry HTML consultation report."""
    consultation = generate_palm_consultation_sections(analysis_res)
    client_name = consultation["client_name"]
    gender = consultation["gender"]
    hand_shape = consultation["hand_shape"]
    sections = consultation["sections"]
    timings = consultation["timing_milestones"]
    secrets = sections.get("scientific_secrets", [])
    minor_lines = sections.get("minor_power_lines", {}).get("lines", [])

    # Render timing rows
    timing_rows = []
    for t in timings:
        timing_rows.append(
            f"<tr>"
            f"<td><b>{_e(t.get('period', 'Phase'))}</b></td>"
            f"<td><span class='timing-badge'>{_e(t.get('age_landmark', 'N/A'))}</span></td>"
            f"<td>{_e(t.get('line', ''))}</td>"
            f"<td>{_e(t.get('significance', ''))}</td>"
            f"</tr>"
        )
    timing_table_html = "".join(timing_rows)

    # Render minor lines grid
    minor_cards = []
    for m in minor_lines:
        minor_cards.append(
            f"<div class='minor-card'>"
            f"<h3>{_e(m['name'])}</h3>"
            f"<div class='status'>{_e(m['status'])}</div>"
            f"<p>{_e(m['meaning'])}</p>"
            f"</div>"
        )
    minor_grid_html = "".join(minor_cards)

    # Render curiosity cards
    curiosity_cards = []
    for s in secrets:
        curiosity_cards.append(
            f"<div class='curiosity-card'>"
            f"<h3>{_e(s['title'])}</h3>"
            f"<div class='sub'>{_e(s['subtitle'])}</div>"
            f"<p>{s['scientific_fact']}</p>"
            f"<div class='insight'><b>Insight:</b> {s['entertainment_insight']}</div>"
            f"</div>"
        )
    curiosity_grid_html = "".join(curiosity_cards)

    counsel_items = "".join(f"<li>{p}</li>" for p in sections["palmist_counsel"]["points"])

    html_content = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Scientific Palmistry Consultation — {_e(client_name)}</title>
<style>{_css()}</style>
</head>
<body>
<div class="wrap">
    <div class="hero">
        <h1>Personal Palmistry Consultation Reading</h1>
        <div class="subtitle">Scientific Dermatoglyphic Neural Analysis &bull; Multi-Aspect Confluence &bull; CV Traced Ridge Models</div>
        
        <div class="meta-chips">
            <span class="chip">Native: <b>{_e(client_name)}</b> ({_e(gender.capitalize())})</span>
            <span class="chip">Dominant Hand: <b>{_e(hand_shape)} Hand</b></span>
            <span class="chip">Analysis Mode: <b>Computer Vision Handprint Detection</b></span>
            <span class="chip">Consultation Date: <b>{datetime.now().strftime('%d %b %Y')}</b></span>
        </div>
    </div>

    <!-- 1. Core Hand Persona -->
    <div class="summary-card accent">
        <h2>1. Who You Are at the Core: {_e(sections['core_persona']['title'])}</h2>
        <p class="narrative-p">{sections['core_persona']['narrative']}</p>
    </div>

    <!-- 2. Cognitive Architecture -->
    <div class="summary-card info">
        <h2>2. How Your Mind Operates: {_e(sections['mind_architecture']['title'])}</h2>
        <p class="narrative-p">{sections['mind_architecture']['narrative']}</p>
    </div>

    <!-- 3. Minor Power Lines -->
    <div class="summary-card pos">
        <h2>3. Minor Power Lines &amp; Specialized Perceptive Antennas</h2>
        <p class="narrative-p">Computer Vision scans detected four key secondary energy channels that amplify your primary major lines:</p>
        <div class="minor-lines-grid">
            {minor_grid_html}
        </div>
    </div>

    <!-- 4. The Closed Wealth Vault -->
    <div class="summary-card warn">
        <h2>4. The Great Closed Triangle: {_e(sections['wealth_vault']['title'])}</h2>
        <p class="narrative-p">{sections['wealth_vault']['narrative']}</p>
    </div>

    <!-- 5. Career Architecture & Timing Roadmap -->
    <div class="summary-card pos">
        <h2>5. Career Architecture &amp; The Master Milestone Timeline</h2>
        <p class="narrative-p">{sections['career_trajectory']['narrative']}</p>
        
        <table class="timing-table">
            <thead>
                <tr>
                    <th>Life Phase</th>
                    <th>Age Landmark</th>
                    <th>Traced Formation</th>
                    <th>Chronological Meaning</th>
                </tr>
            </thead>
            <tbody>
                {timing_table_html}
            </tbody>
        </table>
    </div>

    <!-- 6. Vitality & Physical Battery -->
    <div class="summary-card warn">
        <h2>6. Vitality, Stamina &amp; The Inner Shield: {_e(sections['vitality_shield']['title'])}</h2>
        <p class="narrative-p">{sections['vitality_shield']['narrative']}</p>
    </div>

    <!-- 7. Heart & Relationships -->
    <div class="summary-card accent">
        <h2>7. Emotional Climate &amp; Relationships: {_e(sections['heart_equilibrium']['title'])}</h2>
        <p class="narrative-p">{sections['heart_equilibrium']['narrative']}</p>
    </div>

    <!-- 8. Dual Hand Synthesis -->
    <div class="summary-card info">
        <h2>8. Dual-Hand Secret: {_e(sections['dual_hand_synthesis']['title'])}</h2>
        <p class="narrative-p">{sections['dual_hand_synthesis']['narrative']}</p>
    </div>

    <!-- 9. Palmist Counsel -->
    <div class="counsel-box">
        <h2>9. The Palmist's Strategic Counsel</h2>
        <ul>
            {counsel_items}
        </ul>
    </div>

    <!-- 10. Hidden Secrets & Curiosities -->
    <div class="summary-card info" style="margin-top: 24px;">
        <h2>10. Scientific Dermatoglyphics &amp; Neural Topography Principles</h2>
        <p class="narrative-p">Scientific palmistry demonstrates that palm lines are living neural projections of the brain. Here are the principles governing your hand:</p>
        <div class="curiosity-grid">
            {curiosity_grid_html}
        </div>
    </div>

    <div class="footer">
        Scientific Palmistry &bull; Neural Topography &amp; Dermatoglyphics Engine
    </div>
</div>
</body>
</html>
"""
    return html_content
