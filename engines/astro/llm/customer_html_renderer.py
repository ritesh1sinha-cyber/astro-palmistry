"""Clean, dumb HTML renderer for CustomerReport.

This renderer receives ONLY the CustomerReport JSON and produces clean HTML.
It NEVER accesses internal analysis data. It NEVER invents content.
Empty fields = section does not render (never "pending" or "TBD").
"""
from __future__ import annotations

import html as _html
from typing import Any

from .report_schema import CustomerReport, LifeArea


def _esc(text: str) -> str:
    """HTML-escape text."""
    return _html.escape(text or "")


def _render_life_area(area: LifeArea) -> str:
    """Render a single life-area card."""
    parts: list[str] = []
    cls = f"card {area.tone_class}" if area.tone_class else "card"
    parts.append(f'<div class="{cls}">')
    parts.append(f'<div class="card__title">{_esc(area.label)}</div>')
    if area.chip:
        parts.append(f'<span class="chip {area.tone_class}">{_esc(area.chip)}</span>')

    if area.conclusion:
        parts.append(f'<div class="card__summary">{_esc(area.conclusion)}</div>')
    if area.astrological_basis:
        parts.append(f'<div class="card__body"><strong>Astrological basis:</strong> {_esc(area.astrological_basis)}</div>')
    if area.interpretation:
        parts.append(f'<div class="card__body"><strong>What this means:</strong> {_esc(area.interpretation)}</div>')
    if area.outlook:
        parts.append(f'<div class="card__body"><strong>Outlook:</strong> {_esc(area.outlook)}</div>')
    if area.timing:
        parts.append(f'<div class="card__body"><strong>Timing:</strong> {_esc(area.timing)}</div>')
    if area.manifestation:
        parts.append(f'<div class="card__body"><strong>How this may show up:</strong> {_esc(area.manifestation)}</div>')
    if area.remedy:
        parts.append(f'<div class="card__body"><strong>What helps:</strong> {_esc(area.remedy)}</div>')
    if area.transition_note:
        parts.append(f'<div class="card__footer"><em>{_esc(area.transition_note)}</em></div>')

    parts.append("</div>")
    return "\n".join(parts)


def _render_life_areas(areas: list[LifeArea]) -> str:
    """Render the life-areas grid."""
    if not areas:
        return ""
    sections: list[str] = []
    sections.append('<section class="life-areas" id="life-areas">')
    sections.append('<h2>Life Areas</h2>')
    sections.append('<div class="life-areas__grid">')
    for area in areas:
        sections.append(_render_life_area(area))
    sections.append("</div>")
    sections.append("</section>")
    return "\n".join(sections)


def render_customer_report(report: CustomerReport) -> str:
    """Render the CustomerReport to clean HTML.

    This is the ONLY function that produces customer-facing HTML.
    Empty fields = section does NOT render.
    """
    sections: list[str] = []

    # --- Header ---
    sections.append("<!DOCTYPE html>")
    sections.append('<html lang="en">')
    sections.append("<head>")
    sections.append('<meta charset="utf-8">')
    sections.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    sections.append(f"<title>{_esc(report.meta.name)} - Birth Chart Reading</title>")
    sections.append(_base_css())
    sections.append("</head>")
    sections.append("<body>")

    # --- Subject name + birth data ---
    sections.append('<header class="report-header">')
    sections.append(f'<h1>{_esc(report.meta.name)} - Birth Chart Reading</h1>')
    if report.meta.birth_date or report.meta.birth_time or report.meta.birth_place:
        parts = []
        if report.meta.birth_date:
            parts.append(_esc(report.meta.birth_date))
        if report.meta.birth_time:
            parts.append(_esc(report.meta.birth_time))
        if report.meta.birth_place:
            parts.append(_esc(report.meta.birth_place))
        sections.append(f'<div class="subject-meta">{" | ".join(parts)}</div>')
    sections.append("</header>")

    # --- Section B: Opening + Tone ---
    if report.summary.headline or report.summary.opening:
        sections.append('<section class="summary" id="summary">')
        if report.summary.headline:
            sections.append(f'<h2>Summary</h2>')
            sections.append(f'<p class="summary__headline">{_esc(report.summary.headline)}</p>')
        if report.summary.opening:
            sections.append(f'<p class="summary__opening">{_esc(report.summary.opening)}</p>')
        if report.summary.strengths:
            sections.append('<div class="summary__list"><strong>Strengths:</strong> ')
            sections.append(", ".join(_esc(s) for s in report.summary.strengths))
            sections.append("</div>")
        if report.summary.watch:
            sections.append('<div class="summary__list"><strong>Watch areas:</strong> ')
            sections.append(", ".join(_esc(s) for s in report.summary.watch))
            sections.append("</div>")
        sections.append("</section>")

    # --- Section B: Tone chip ---
    if report.tone.chip:
        sections.append(f'<div class="tone-chip {report.tone.tone_class}">{_esc(report.tone.chip)}</div>')

    # --- Section C: Life Areas ---
    sections.append(_render_life_areas(report.life_areas))

    # --- Section D: Life State ---
    if report.meta.access == "paid":
        has_mind = bool(report.life_state.what_is_on_your_mind)
        has_why = bool(report.life_state.why_this_period_feels_this_way)
        has_family = bool(report.life_state.family_note)
        if has_mind or has_why or has_family:
            sections.append('<section class="life-state" id="current-situation">')
            sections.append("<h2>Current Life State</h2>")
            if has_mind:
                sections.append('<div class="life-state__mind"><strong>What may be on your mind:</strong>')
                sections.append("<ul>")
                for line in report.life_state.what_is_on_your_mind:
                    sections.append(f"<li>{_esc(line)}</li>")
                sections.append("</ul></div>")
            if has_why:
                sections.append(f'<div class="life-state__why"><strong>Why this period feels this way:</strong> {_esc(report.life_state.why_this_period_feels_this_way)}</div>')
            if has_family:
                sections.append('<div class="life-state__family"><strong>Family context:</strong>')
                sections.append("<ul>")
                for line in report.life_state.family_note:
                    sections.append(f"<li>{_esc(line)}</li>")
                sections.append("</ul></div>")
            sections.append("</section>")

    # --- Section E: Current Period ---
    if report.current_period.vedic_period or report.current_period.phase_label:
        sections.append('<section class="current-period" id="current-period">')
        sections.append("<h2>Current Period</h2>")
        if report.current_period.vedic_period:
            sections.append(f'<p class="period__vedic">{_esc(report.current_period.vedic_period)}</p>')
        if report.current_period.phase_label:
            sections.append(f'<p class="period__phase">{_esc(report.current_period.phase_label)}</p>')
        if report.current_period.phase_description:
            sections.append(f'<p class="period__description">{_esc(report.current_period.phase_description)}</p>')
        sections.append("</section>")

    # --- Section E: Future Outlook ---
    if report.future_outlook.recent_months:
        sections.append('<section class="future-outlook" id="timing-outlook">')
        sections.append("<h2>Timing and Outlook</h2>")
        if report.future_outlook.recent_months:
            sections.append(f'<p>{_esc(report.future_outlook.recent_months)}</p>')
        if report.future_outlook.near_term:
            sections.append(f'<p>{_esc(report.future_outlook.near_term)}</p>')
        if report.future_outlook.longer_term:
            sections.append(f'<p>{_esc(report.future_outlook.longer_term)}</p>')
        sections.append("</section>")

    # --- Section F: Closing Guidance ---
    if report.closing_guidance.final_guidance:
        sections.append('<section class="closing-guidance" id="final-guidance">')
        sections.append("<h2>Final Practical Guidance</h2>")
        sections.append(f'<p>{_esc(report.closing_guidance.final_guidance)}</p>')
        sections.append("</section>")

    # --- Footer ---
    sections.append('<footer class="report-footer">')
    sections.append(f"<p>Generated for {_esc(report.meta.name)}</p>")
    sections.append("</footer>")

    sections.append("</body>")
    sections.append("</html>")
    return "\n".join(sections)


def _base_css() -> str:
    """Minimal CSS for the clean report."""
    return """<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Georgia,serif;background:#0b0d17;color:#d4d4e0;line-height:1.7;padding:2rem;max-width:900px;margin:0 auto}
h1{color:#e8d5b7;font-size:1.6rem;text-align:center;border-bottom:1px solid #333;padding-bottom:1rem}
h2{color:#e8d5b7;font-size:1.2rem;margin:2rem 0 1rem;border-bottom:1px solid #222;padding-bottom:.3rem}
h3{color:#e8d5b7;font-size:1rem;margin:1rem 0 .5rem}
.subject-meta{text-align:center;color:#999;margin-bottom:2rem;font-size:.9rem}
.summary__headline{color:#e8d5b7;font-size:1.1rem;margin-bottom:.5rem}
.summary__opening{margin-bottom:1rem}
.summary__list{margin:.5rem 0;color:#aaa;font-size:.9rem}
.tone-chip{display:inline-block;padding:.2rem .8rem;border-radius:12px;font-size:.8rem;margin:1rem 0}
.tone-chip.green{background:#1a3a1a;color:#6fcf6f;border:1px solid #2d5a2d}
.tone-chip.yellow{background:#3a3a1a;color:#cfcf6f;border:1px solid #5a5a2d}
.tone-chip.red{background:#3a1a1a;color:#cf6f6f;border:1px solid #5a2d2d}
.life-areas__grid{display:grid;gap:1.5rem}
.card{background:#12151f;border:1px solid #222;border-radius:8px;padding:1.2rem}
.card__title{font-size:1.1rem;color:#e8d5b7;font-weight:bold;margin-bottom:.5rem}
.card__summary{color:#ccc;margin-bottom:.8rem;font-style:italic}
.card__body{margin:.5rem 0;color:#bbb;font-size:.95rem}
.card__footer{margin-top:.8rem;color:#888;font-size:.85rem;border-top:1px solid #222;padding-top:.5rem}
.chip{display:inline-block;padding:.1rem .6rem;border-radius:10px;font-size:.75rem;margin-bottom:.5rem}
.chip.green{background:#1a3a1a;color:#6fcf6f;border:1px solid #2d5a2d}
.chip.yellow{background:#3a3a1a;color:#cfcf6f;border:1px solid #5a5a2d}
.chip.red{background:#3a1a1a;color:#cf6f6f;border:1px solid #5a2d2d}
.life-state ul{margin:.3rem 0 .3rem 1.5rem}
.life-state li{margin:.3rem 0}
.life-state__mind,.life-state__why,.life-state__family{margin:.8rem 0}
.period__vedic{color:#e8d5b7;margin-bottom:.3rem}
.period__phase{margin-bottom:.3rem}
.future-outlook p{margin:.5rem 0}
.closing-guidance p{color:#ccc;font-style:italic}
.report-footer{text-align:center;margin-top:3rem;color:#666;font-size:.8rem;border-top:1px solid #222;padding-top:1rem}
</style>"""
