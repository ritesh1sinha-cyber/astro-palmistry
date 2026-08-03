#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vedic_mehta_report.py - Standalone Modern Techniques lane (M.S. Mehta / rules4).

Separate from Bhardwaj composite; confluence wiring comes later.
Usage:
    python3 build_mehta_data.py   # once
    python3 vedic_mehta_report.py <extracted_txt> <name> <YYYY-MM-DD> [-o out.html]
"""
from __future__ import annotations

import argparse
import html
import json
from datetime import date, datetime
from pathlib import Path

try:
    from client_report_html import finalize_report_html
except Exception:  # pragma: no cover
    finalize_report_html = lambda h, client_name="": h  # noqa: E731

from astro_precompute import precompute
from bhardwaj_semantic import _ord
from mehta_book_data import lookup_mehta_lord, pick_mehta_clause
from mehta_chart import MehtaChart
from mehta_prose import (
    LifeSection,
    build_life_sections,
    mehta_hero,
    mehta_year_ahead_html,
)
from mehta_semantic import MehtaSemanticEngine, build_mehta_signals

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "mehta_book_data.json"


def _e(s) -> str:
    return html.escape(str(s))


def _load_book() -> dict:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Run build_mehta_data.py first - missing {DATA_PATH}")
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _clip(text: str, n: int = 220) -> str:
    text = " ".join(text.split())
    if len(text) <= n:
        return text
    return text[: n - 1].rsplit(" ", 1)[0] + "..."


def _css() -> str:
    return """
:root{--heading:#3949ab;--border:#e0e0e0;--muted:#555}
body{font-family:Georgia,serif;max-width:46rem;margin:auto;padding:1.5rem;line-height:1.62;color:#1a1a1a;background:#fafafa}
.card{background:#fff;border:1px solid var(--border);border-radius:8px;padding:1.25rem 1.75rem;border-top:3px solid var(--heading)}
h1{font-size:1.22rem;color:var(--heading);margin-top:1.5rem}
h1:first-of-type{margin-top:0}
.lead{font-size:1.03rem;color:#444}
.pred{margin:.65rem 0}
.fine{font-size:.86rem;color:var(--muted);margin:.35rem 0 0}
.meta{display:grid;grid-template-columns:auto 1fr;gap:.25rem .75rem;font-size:.92rem}
.meta dt{font-weight:600;color:#283593}
.note{font-size:.85rem;color:var(--muted);border-top:1px solid #eee;margin-top:1.5rem;padding-top:.75rem}
.callout{background:#e8eaf6;border-left:4px solid var(--heading);padding:.9rem 1rem;margin:1rem 0;border-radius:4px}
.hero{background:linear-gradient(135deg,#e8eaf6,#ede7f6);border-left:4px solid var(--heading);padding:1rem 1.15rem;margin:1rem 0;border-radius:4px;font-size:1.05rem}
.sec{margin:.85rem 0 .35rem}
.sec.good .pred{border-left:3px solid #2e7d32;padding-left:.65rem}
.sec.amber .pred{border-left:3px solid #f9a825;padding-left:.65rem}
.pred-card{border:1px solid #e0e0e0;border-radius:6px;padding:.85rem 1rem;margin:.75rem 0}
.pred-card.green{border-left:4px solid #2e7d32;background:#f1f8f4}
.pred-card.neutral{border-left:4px solid #78909c;background:#fafafa}
.pred-body{font-size:.98rem}
details.appendix{margin-top:1.25rem;font-size:.88rem}
table.simple{width:100%;border-collapse:collapse;font-size:.85rem}
table.simple th,table.simple td{border:1px solid #e0e0e0;padding:.4rem;vertical-align:top}
table.simple th{background:#e8eaf6;color:#283593}
"""


def _section_html(sec: LifeSection) -> str:
    tone_cls = {"good": "good", "attention": "good", "amber": "amber"}.get(sec.tone, "")
    fact = f'<p class="fine">({_e(sec.fact)})</p>' if sec.fact else ""
    return f"""
<div class="sec {tone_cls}">
  <h1>{_e(sec.title)}</h1>
  <p class="pred">{_e(sec.prediction)}</p>
  {fact}
</div>"""


def _lord_table(chart: MehtaChart) -> str:
    rows = []
    for h in range(1, 13):
        lord = chart.houses[h]["lord"]
        occ = chart.planets[lord]["house"]
        txt = lookup_mehta_lord(
            chart.book, h, occ,
            "caution" if occ in (6, 8, 12) else "neutral",
        )
        rows.append(
            f"<tr><td>{_ord(h)}</td><td>{lord}</td><td>{_ord(occ)}</td>"
            f"<td>{_e(_clip(txt) if txt else '-')}</td></tr>"
        )
    return (
        "<table class='simple'><tr><th>House ruled</th><th>Lord</th><th>Sits in</th><th>Mehta read</th></tr>"
        + "".join(rows) + "</table>"
    )


def render_mehta_html(
    chart: MehtaChart,
    sections: list[LifeSection],
    signals: list,
    pc: dict,
    dob_disp: str,
    tob: str = "",
    place: str = "",
) -> str:
    nm = _e(chart.name)
    today = date.today()
    hero = next((s for s in sections if s.domain == "intro"), None)
    hero_text = hero.prediction if hero else mehta_hero(chart)
    life_html = ""
    for sec in sections:
        if sec.domain == "intro":
            continue
        life_html += _section_html(sec)

    nav_flags = chart.navamsha_dilution_flags()
    _ = nav_flags  # covered in Chapter XVIII section

    evidence_rows = ""
    for sig in signals[:24]:
        evidence_rows += (
            f"<tr><td>{_e(sig.source)}</td><td>{_e(sig.domain)}</td>"
            f"<td>{_e(_clip(sig.anchor or sig.text, 160))}</td></tr>"
        )

    body = f"""
<article class="card">
  <h1 style="margin-top:0;color:#1a237e;">Modern Techniques Reading</h1>
  <dl class="meta">
    <dt>Client</dt><dd>{nm}</dd>
    <dt>Born</dt><dd>{_e(dob_disp)}{('  ' + _e(tob)) if tob else ''}{('  ' + _e(place)) if place else ''}</dd>
    <dt>Map</dt><dd>{chart.lagna} rising  Moon {chart.moon_sign} ({_e(chart.moon_nak)})  Sun {chart.sun_sign}</dd>
    <dt>Dasha</dt><dd>{chart.cur_md['md_lord']} mahadasha</dd>
    <dt>Report</dt><dd>{today.strftime('%d %B %Y').lstrip('0')}</dd>
  </dl>
  <p class="lead">Mehta <em>Modern Techniques</em> reading (rules4): every Part-A chapter below is computed from your placements, then written as plain predictions.</p>

  <div class="hero">{_e(hero_text)}</div>

  <h1>Timing - dasha windows</h1>
  {mehta_year_ahead_html(chart)}

  <h1>Life reading by house</h1>
  <p class="fine">Chapters I through XIX from Mehta's book - no section skipped.</p>
  {life_html}

  <details class="appendix">
    <summary>Mehta twelve-step method (reference)</summary>
    <ol>{"".join(f"<li>{_e(s)}</li>" for s in chart.book.get('intro_steps', []))}</ol>
  </details>

  <details class="appendix">
    <summary>House lords - Mehta book lines (reference)</summary>
    {_lord_table(chart)}
  </details>

  <details class="appendix">
    <summary>Chart signals used (technical)</summary>
    <table class="simple">
      <tr><th>Source</th><th>Domain</th><th>Chart fact</th></tr>
      {evidence_rows}
    </table>
  </details>

  <p class="note">Educational astrology only. Rebuild corpus: <code>python3 build_mehta_data.py</code>.
  Source: rules4.md / MODERN TECHNIQUES.pdf.</p>
</article>"""
    return (
        f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'/>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'/>"
        f"<title>Mehta Modern Techniques - {nm}</title><style>{_css()}</style></head><body>{body}</body></html>"
    )


def generate_mehta_html(
    extracted_path: str,
    client_name: str,
    dob: str,
    tob: str = "",
    place: str = "",
) -> tuple[str, dict]:
    book = _load_book()
    pc = precompute(extracted_path, client_name, dob)
    chart = MehtaChart(pc, book)
    engine = MehtaSemanticEngine(book)
    signals = build_mehta_signals(chart, pc)
    clusters = engine.cluster(signals)
    sections = build_life_sections(chart)
    d = datetime.strptime(dob, "%Y-%m-%d").date()
    doc = render_mehta_html(chart, sections, signals, pc, d.strftime("%d %B %Y").lstrip('0'), tob, place)
    cur = next((a for a in chart.antars if a.get("status") == "current"), None)
    summary = {
        "lagna": chart.lagna,
        "moon_sign": chart.moon_sign,
        "yogas": len(chart.detect_mehta_yogas()),
        "current_md": chart.cur_md["md_lord"],
        "current_ad": cur["ad_lord"] if cur else None,
        "signals": len(signals),
        "clusters": len(clusters),
        "sections": len(sections),
        "seventh_lord_houses": len(book.get("seventh_lord_in_house", {})),
        "tenth_lord_houses": len(book.get("tenth_lord_in_house", {})),
    }
    return doc, summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Mehta Modern Techniques standalone report (rules4)")
    ap.add_argument("extracted")
    ap.add_argument("name")
    ap.add_argument("dob")
    ap.add_argument("--tob", default="")
    ap.add_argument("--place", default="")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    doc, summary = generate_mehta_html(args.extracted, args.name, args.dob, args.tob, args.place)
    out = Path(args.out) if args.out else BASE_DIR / "reports" / f"Mehta_{args.name}_preview.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(finalize_report_html(doc, args.name), encoding="utf-8")
    print(
        f"signals={summary['signals']} sections={summary['sections']} "
        f"7th_lord_text={summary['seventh_lord_houses']} 10th_lord_text={summary['tenth_lord_houses']}"
    )
    print(f"lagna={summary['lagna']} moon={summary['moon_sign']} mehta_yogas={summary['yogas']}")
    print(f"MD={summary['current_md']} AD={summary['current_ad']}")
    print(f"written -> {out}")


if __name__ == "__main__":
    main()
