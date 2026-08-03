#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vedic_bnn_report.py - Standalone Bhrigu Nandi Nadi lane (book OCR, D1 only).

Usage:
    python3 vedic_bnn_report.py <name> <YYYY-MM-DD> [--precomputed path.json]
    python3 vedic_bnn_report.py <name> <YYYY-MM-DD> --time HH:MM --lat ... --lon ... --tz ...
"""
from __future__ import annotations

import argparse
import html
import re
from datetime import date, datetime
from pathlib import Path

from astro_precompute import resolve_precompute
from chart_client import female_from_pc, source_label
from chart_resolve import add_chart_source_args, chart_kwargs_from_args
from bnn_chart import BnnChart, BnnTiming, fmt_date, load_bnn_chart
from bnn_prose import LifeSection, bnn_hero, bnn_year_ahead_html, build_life_sections

BASE_DIR = Path(__file__).resolve().parent
GOLD = BASE_DIR / "reports" / "Vedic_BNN_Ritz_20260408.html"

Chart = BnnChart


def _e(s) -> str:
    return html.escape(str(s))


def _css() -> str:
    try:
        t = GOLD.read_text(encoding="utf-8")
        i, j = t.find("<style>"), t.find("</style>")
        if i != -1 and j != -1:
            extra = (
                ".sec.good .pred{border-left:3px solid #2e7d32;padding-left:.65rem}"
                ".sec.amber .pred{border-left:3px solid #f9a825;padding-left:.65rem}"
                ".hero{background:#e8f4fd;border-left:4px solid #0d47a1;padding:1rem;margin:1rem 0}"
                ".pred-card{border:1px solid #e0e0e0;border-radius:6px;padding:.85rem 1rem;margin:.75rem 0}"
                ".pred-card.green,.pred-card.good{border-left:4px solid #2e7d32;background:#f1f8f4}"
                ".pred-card.neutral{border-left:4px solid #78909c;background:#fafafa}"
                ".fine{font-size:.86rem;color:#555;margin:.35rem 0 0}"
                ".sec ul{margin:.5rem 0 .75rem 1.2rem;padding:0}"
                ".sec ul li{margin:.4rem 0;line-height:1.5}"
                ".grid2{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin:.75rem 0}"
                "@media(max-width:640px){.grid2{grid-template-columns:1fr}}"
                ".bnn-rule{background:#f5f5f5;border-left:3px solid #78909c;padding:.5rem .75rem;"
                "margin:.5rem 0;font-size:.86rem;color:#444}"
                ".traffic-green{background:#e8f5e9;border-left:4px solid #2e7d32;padding:.75rem 1rem;margin:.75rem 0}"
                ".traffic-amber{background:#fff8e1;border-left:4px solid #f9a825;padding:.75rem 1rem;margin:.75rem 0}"
                ".traffic-neutral{background:#fafafa;border-left:4px solid #bdbdbd;padding:.75rem 1rem;margin:.75rem 0}"
                ".good-note{color:#1b5e20}"
            )
            return t[i + 7 : j] + extra
    except Exception:
        pass
    return (
        "body{font-family:Georgia,serif;max-width:46rem;margin:auto;padding:1.5rem;line-height:1.62}"
        ".card{background:#fff;border:1px solid #e0e0e0;padding:1.25rem 1.75rem;border-radius:8px}"
        "h1{font-size:1.22rem;color:#0d47a1;margin-top:1.5rem}"
        ".pred{margin:.65rem 0}.hero{background:#e8f4fd;border-left:4px solid #0d47a1;padding:1rem;margin:1rem 0}"
        ".sec ul{margin:.5rem 0 .75rem 1.2rem}.sec ul li{margin:.4rem 0}"
        "table.facts{width:100%;border-collapse:collapse;font-size:.85rem}"
        "table.facts th,table.facts td{border:1px solid #e0e0e0;padding:.4rem}"
        "details.appendix{margin-top:1.5rem;font-size:.88rem}"
    )


def _section_body(sec: LifeSection) -> str:
    parts: list[str] = []
    if sec.prediction:
        parts.append(f'<p class="pred">{_e(sec.prediction)}</p>')
    if sec.html_body:
        parts.append(sec.html_body)
    return "".join(parts)


def _section_html(sec: LifeSection) -> str:
    tone_cls = {"good": "good", "amber": "amber"}.get(sec.tone, "")
    fact = f'<p class="fine">({_e(sec.fact)})</p>' if sec.fact else ""
    body = _section_body(sec)
    return f"""
<div class="sec {tone_cls}">
  <h1>{_e(sec.title)}</h1>
  {body}
  {fact}
</div>"""


def _d1_table(ch: BnnChart) -> str:
    from bnn_chart import SIGN_LORD

    order = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    rows = [
        f"<tr><td>Asc</td><td>{ch.lagna}</td><td>1</td>"
        f"<td>Lord {SIGN_LORD[ch.lagna]} - {ch.pc['meta'].get('lagna_nakshatra', '')}</td></tr>"
    ]
    for p in order:
        v = ch.planets[p]
        notes = []
        if v["dignity"] in ("exalted", "debilitated", "own_sign", "moolatrikona"):
            notes.append(v["dignity"].replace("_", " "))
        conj = ch.conj_with(p)
        if conj:
            notes.append("with " + " & ".join(conj))
        if v["retrograde"]:
            notes.append("retrograde")
        if v.get("nakshatra"):
            notes.append(v["nakshatra"])
        rows.append(
            f"<tr><td>{p}</td><td>{v['sign']}</td><td>{ch.h(p)}</td>"
            f"<td>{', '.join(notes)}</td></tr>"
        )
    return (
        "<table class='facts'><tr><th>Planet</th><th>Sign</th><th>House</th><th>Notes</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def _detect_female(text: str) -> bool:
    return bool(re.search(r"\bSex\s+Female\b", text, re.I))


def render_bnn_html(
    ch: BnnChart,
    bt: BnnTiming,
    sections: list[LifeSection],
    dob_disp: str,
    tob: str = "",
    place: str = "",
    extract_path: str = "",
) -> str:
    nm = _e(ch.name)
    today = date.today()
    hero = bnn_hero(ch, bt)
    timing = bnn_year_ahead_html(ch, bt)
    body_sections = "".join(_section_html(s) for s in sections if s.domain != "intro")

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>BNN reading - {nm}</title>
<style>{_css()}</style></head><body>
  <article class="card">
    <h1 style="color:#0d47a1;border:none;margin-top:0;">Bhrigu Nandi Nadi — chart reading</h1>
    <p class="note" style="margin-top:0;">Standalone <strong>BNN lane only</strong> (whole-sign D1, Avasthi book combinations + chart-foundation blocks).
    Vimshottari dates from your extract — not AstroSage generic phal. D9/D7/D10 belong in separate lane reports.</p>
    <dl class="meta" style="display:grid;grid-template-columns:auto 1fr;gap:.25rem .75rem;font-size:.92rem;color:#b0106b;">
      <dt>Client</dt><dd>{nm}</dd>
      <dt>Born</dt><dd>{_e(dob_disp)}{(' · ' + _e(tob)) if tob else ''}{(' · ' + _e(place)) if place else ''}</dd>
      <dt>Lagna</dt><dd>{ch.lagna} · AK {ch.atmakaraka() or '-'}</dd>
      <dt>Source</dt><dd><code>{_e(extract_path or 'extract')}</code></dd>
      <dt>Report date</dt><dd>{today.strftime('%d %B %Y').lstrip('0')}</dd>
    </dl>

    <div class="hero"><p class="pred" style="margin:0;">{_e(hero)}</p></div>
    {timing}

    {body_sections}

    <details class="appendix" style="margin-top:1.5rem;font-size:.88rem;">
      <summary>D1 chart facts (technical appendix)</summary>
      <h2>Whole-sign placements from lagna</h2>
      {_d1_table(ch)}
      <h2>Mahadasa (extract)</h2>
      <p class="fine">Current MD {bt.cur_md.get('md_lord', '-')} until {fmt_date(bt.cur_md.get('end'))}</p>
    </details>

    <p class="note">Educational Jyotisha only. Verify critical dates in your software. Not medical or legal advice.</p>
  </article>
</body></html>"""


def generate_bnn_html(
    client_name: str,
    dob: str,
    *,
    extracted_path: str | None = None,
    tob: str = "",
    place: str = "",
    precomputed_path: str | None = None,
    birth_time: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone: float | None = None,
    gender: int | None = None,
) -> tuple[str, dict]:
    pc = resolve_precompute(
        client_name, dob,
        extracted_path=extracted_path,
        precomputed_path=precomputed_path,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        place_name=place,
        gender=gender,
    )
    ch, bt = load_bnn_chart(pc=pc, client_name=client_name, dob=dob)
    female = female_from_pc(pc)
    sections = build_life_sections(ch, bt, male=not female)
    try:
        dob_disp = datetime.strptime(dob, "%Y-%m-%d").strftime("%d %B %Y").lstrip('0')
    except Exception:
        dob_disp = dob
    src = source_label(
        precomputed_path=precomputed_path,
        birth_time=birth_time,
        extracted_path=extracted_path,
    )
    doc = render_bnn_html(ch, bt, sections, dob_disp, tob, place, src)
    summary = {
        "lagna": ch.lagna,
        "atmakaraka": ch.atmakaraka(),
        "current_md": bt.cur_md.get("md_lord", ""),
        "debilitated": [p for p, v in ch.planets.items() if v["dignity"] == "debilitated"],
        "exalted": [p for p, v in ch.planets.items() if v["dignity"] == "exalted"],
        "sections": len(sections),
        "conjunctions": list(ch.conjunctions.keys()),
    }
    return doc, summary


def main() -> None:
    ap = argparse.ArgumentParser(description="BNN report from Avasthi book OCR (D1 only)")
    ap.add_argument("name")
    ap.add_argument("dob")
    ap.add_argument("extracted", nargs="?", default=None, help="Optional legacy AstroSage extract")
    add_chart_source_args(ap)
    ap.add_argument("--tob", default="")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    kw = chart_kwargs_from_args(args)
    doc, summary = generate_bnn_html(
        args.name, args.dob,
        extracted_path=args.extracted,
        tob=args.tob, place=args.place or kw.get("place_name", ""),
        precomputed_path=kw.get("precomputed_path"),
        birth_time=kw.get("birth_time"),
        latitude=kw.get("latitude"),
        longitude=kw.get("longitude"),
        timezone=kw.get("timezone"),
        gender=kw.get("gender"),
    )
    out = Path(args.out) if args.out else BASE_DIR / "reports" / f"BNN_{args.name}_preview.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(
        f"sections={summary['sections']} lagna={summary['lagna']} AK={summary['atmakaraka']} "
        f"MD={summary['current_md']} conjunctions={summary['conjunctions']}"
    )
    print(f"written -> {out}")


if __name__ == "__main__":
    main()
