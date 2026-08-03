#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vedic_jaimini_books_report.py - Jaimini BOOK lane (Goel + Boney Gems + Jewels).

Prediction-first human read from three Jaimini books (karakas, KL, argala, raja yoga).
NOT Chara dasha timing - use vedic_jaimini_report.py for sign-period dates.

Usage:
    python3 build_jaimini_data.py
    python3 vedic_jaimini_books_report.py <extracted_txt> <name> <YYYY-MM-DD> [-o out.html]
"""
from __future__ import annotations

import argparse
import html
from datetime import date, datetime
from pathlib import Path

try:
    from client_report_html import finalize_report_html
except Exception:  # pragma: no cover
    finalize_report_html = lambda h, client_name="": h  # noqa: E731

from astro_precompute import precompute
from jaimini_book_data import load_book
from jaimini_books_chart import JaiminiBooksChart, ROLE_ORDER, ROLE_SHORT
from jaimini_books_prose import LifeSection, build_life_sections

BASE_DIR = Path(__file__).resolve().parent


def _e(s) -> str:
    return html.escape(str(s))


def _css() -> str:
    return """
:root{--heading:#006064;--magenta:#b0106b;--border:#e0e0e0;--muted:#555}
body{font-family:Georgia,serif;max-width:46rem;margin:auto;padding:1.5rem;line-height:1.62;color:#1a1a1a;background:#fafafa}
.card{background:#fff;border:1px solid var(--border);border-radius:6px;padding:1.5rem 1.75rem;border-top:3px solid var(--heading);box-shadow:0 1px 3px rgba(0,0,0,.06)}
h1{font-size:1.28rem;color:var(--heading);border-bottom:2px solid var(--heading);padding-bottom:.35rem;margin-top:1.5rem}
h1:first-of-type{margin-top:0;border:none;padding:0}
.lead{font-size:1.06rem;color:#333;margin-bottom:1rem}
.pred{margin:.7rem 0}
.fine{font-size:.86rem;color:var(--muted);margin:.3rem 0 0}
.meta{color:var(--magenta);font-size:1.02rem;margin-bottom:1rem}
.meta dt{font-weight:bold;margin-top:.35rem}
.meta dd{margin:0}
.note{font-size:.86rem;color:var(--muted);margin-top:1rem}
.hero{background:#e0f7fa;border-left:4px solid var(--heading);padding:.9rem 1rem;margin:1rem 0;border-radius:4px;font-size:1.04rem}
.sec{margin:.85rem 0 .35rem}
.sec.good .pred{border-left:3px solid #2e7d32;padding-left:.65rem}
.sec.amber .pred{border-left:3px solid #f9a825;padding-left:.65rem}
details.appendix{margin-top:1.25rem;font-size:.88rem}
table.simple{width:100%;border-collapse:collapse;font-size:.88rem;margin:.75rem 0}
table.simple th,table.simple td{border:1px solid var(--border);padding:.45rem;vertical-align:top}
table.simple th{background:#b2ebf2;color:#004d40}
"""


def _karaka_table(chart: JaiminiBooksChart) -> str:
    rows = []
    for r in ROLE_ORDER:
        k = chart.role(r)
        if not k:
            continue
        rows.append(
            f"<tr><td>{ROLE_SHORT[r]}</td><td><strong>{k['planet']}</strong></td>"
            f"<td>{k['sign']}</td><td>{k['house']} from lagna</td></tr>"
        )
    return (
        "<table class='simple'><tr><th>Role</th><th>Planet</th><th>Sign</th><th>House</th></tr>"
        + "".join(rows) + "</table>"
    )


def _section_html(sec: LifeSection) -> str:
    tone_cls = {"good": "good", "attention": "amber"}.get(sec.tone, "")
    fact = f'<p class="fine">({_e(sec.fact)})</p>' if sec.fact else ""
    return f"""
<div class="sec {tone_cls}">
  <h1>{_e(sec.title)}</h1>
  <p class="pred">{_e(sec.prediction)}</p>
  {fact}
</div>"""


def render_books_html(
    chart: JaiminiBooksChart,
    sections: list[LifeSection],
    book: dict,
    dob_disp: str,
    tob: str = "",
    place: str = "",
) -> str:
    nm = _e(chart.name)
    today = date.today()
    hero = sections[0] if sections and sections[0].domain == "snapshot" else None
    body_secs = [s for s in sections if s.domain != "snapshot"]

    hero_html = ""
    if hero:
        hero_html = f'<div class="hero">{_e(hero.prediction)}</div>'

    domain_html = "".join(_section_html(s) for s in body_secs)

    body = f"""
<article class="card">
  <h1 style="color:var(--heading);">Your Jaimini life reading</h1>
  <dl class="meta">
    <dt>Client</dt><dd>{nm}</dd>
    <dt>Born</dt><dd>{_e(dob_disp)}{(' | ' + _e(tob)) if tob else ''}{(' | ' + _e(place)) if place else ''}</dd>
    <dt>Rising</dt><dd>{chart.lagna} | Karakamsha {chart.karakamsa or '-'}</dd>
    <dt>Report</dt><dd>{today.strftime('%d %B %Y').lstrip('0')}</dd>
  </dl>
  <p class="lead">This reading turns the classical Jaimini method into plain life predictions:
  <strong>who you are, career bent, love style, home, belief, and spiritual promise</strong> through soul planets,
  inner-chart (Karakamsha) themes, support patterns, and status combinations.
  For <strong>dated sign-period timing</strong>, use your separate Chara dasha report.</p>

  {hero_html}

  {domain_html}

  <details class="appendix">
    <summary>Technical reference (karakas &amp; sources)</summary>
    <h1 style="font-size:1rem;border:none">Cara karakas</h1>
    {_karaka_table(chart)}
    <p class="fine">Arudha lagna {chart.arudha_lagna}; Upapada {chart.upapada}.</p>
    <p class="fine">Book corpus: {', '.join(book.get('sources', []))}. Rebuild: python3 build_jaimini_data.py</p>
    <p class="fine">Excluded: Goel Chara/Mandook/Narayan dasha chapters (timing-only).</p>
  </details>
  <p class="note">Educational astrology only. Not medical, legal, or investment advice.</p>
</article>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Jaimini reading - {nm}</title>
<style>{_css()}</style></head><body>{body}</body></html>"""


def generate_books_html(
    extracted_path: str, client_name: str, dob: str, tob: str = "", place: str = "",
) -> tuple[str, dict]:
    pc = precompute(extracted_path, client_name, dob)
    book = load_book()
    chart = JaiminiBooksChart.from_precompute(pc)
    sections = build_life_sections(chart)
    dob_disp = datetime.strptime(dob, "%Y-%m-%d").strftime("%d %B %Y").lstrip('0')
    doc = render_books_html(chart, sections, book, dob_disp, tob, place)
    summary = {
        "karakamsa": chart.karakamsa,
        "atmakaraka": chart.role("Atmakarak").get("planet"),
        "sections": len(sections),
        "raja_yoga_pairs": len(chart.raja_yoga_pairs()),
    }
    return doc, summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Jaimini books - human prediction report (not Chara dasha)")
    ap.add_argument("extracted")
    ap.add_argument("name")
    ap.add_argument("dob")
    ap.add_argument("--tob", default="")
    ap.add_argument("--place", default="")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    doc, summary = generate_books_html(args.extracted, args.name, args.dob, args.tob, args.place)
    out = Path(args.out) if args.out else BASE_DIR / "reports" / f"Jaimini_Books_{args.name}_preview.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(finalize_report_html(doc, args.name), encoding="utf-8")
    print(
        f"AK={summary['atmakaraka']} KL={summary['karakamsa']} "
        f"sections={summary['sections']} raja_yogas={summary['raja_yoga_pairs']}"
    )
    print(f"written -> {out}")


if __name__ == "__main__":
    main()
