#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vedic_kp_report.py — Standalone Krishnamurti Paddhati lane (chapter-by-chapter).

Usage:
    python3 vedic_kp_report.py <name> <YYYY-MM-DD> [--precomputed path.json]
    python3 vedic_kp_report.py <name> <YYYY-MM-DD> --time HH:MM --lat ... --lon ... --tz ...
"""
from __future__ import annotations

import argparse
import html
from datetime import date, datetime
from pathlib import Path

from astro_precompute import resolve_precompute
from chart_resolve import add_chart_source_args, chart_kwargs_from_args
from kp_chart import KPChart, fmt, load_kp_chart
from kp_prose import LifeSection, build_life_sections, kp_hero, kp_now_callout, kp_year_ahead_html

BASE_DIR = Path(__file__).resolve().parent
GOLD = BASE_DIR / "reports" / "Vedic_KP_Ritz_20260408.html"


def _e(s) -> str:
    return html.escape(str(s))


def _ord(n: int) -> str:
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n if n < 20 else n % 10, 'th')}"


def _css() -> str:
    tags = (
                ".sec ul{margin:.5rem 0 .75rem 1.2rem;padding:0}"
                ".sec ul li{margin:.4rem 0;line-height:1.5}"
                ".pred-card{border:1px solid #e0e0e0;border-radius:6px;padding:.85rem 1rem;margin:.75rem 0}"
                ".pred-card.green,.pred-card.good{border-left:4px solid #2e7d32;background:#f1f8f4}"
                ".pred-card.neutral{border-left:4px solid #78909c;background:#fafafa}"
                ".callout-time{background:#e8f5e9;border-left:4px solid #2e7d32;padding:.75rem 1rem;margin:1rem 0;font-size:.98rem}"
                ".fine{font-size:.86rem;color:#555;margin:.35rem 0 0}"
                ".kp-rule{background:#f5f5f5;border-left:3px solid #7b1fa2;padding:.5rem .75rem;margin:.5rem 0;font-size:.86rem;color:#444}"
                ".traffic-green{background:#e8f5e9;border-left:4px solid #2e7d32;padding:.75rem 1rem;margin:.75rem 0}"
                ".traffic-amber{background:#fff8e1;border-left:4px solid #f9a825;padding:.75rem 1rem;margin:.75rem 0}"
                ".traffic-neutral{background:#fafafa;border-left:4px solid #bdbdbd;padding:.75rem 1rem;margin:.75rem 0}"
    )
    try:
        t = GOLD.read_text(encoding="utf-8")
        i, j = t.find("<style>"), t.find("</style>")
        if i != -1 and j != -1:
            return t[i + 7:j] + tags
    except Exception:
        pass
    return (
        "body{font-family:Georgia,serif;max-width:46rem;margin:auto;padding:1.5rem;line-height:1.62}"
        ".card{background:#fff;border:1px solid #e0e0e0;padding:1.25rem 1.75rem;border-radius:8px}"
        "h1{font-size:1.22rem;color:#0d47a1;margin-top:1.5rem}"
        ".pred{margin:.65rem 0}.fine{font-size:.86rem;color:#555}"
        ".hero{background:#f3e5f5;border-left:4px solid #6a1b9a;padding:1rem;margin:1rem 0}"
        ".sec.good .pred{border-left:3px solid #2e7d32;padding-left:.65rem}"
        ".sec.amber .pred{border-left:3px solid #f9a825;padding-left:.65rem}"
        ".pred-card{border:1px solid #e0e0e0;border-radius:6px;padding:.85rem 1rem;margin:.75rem 0}"
        ".pred-card.green,.pred-card.good{border-left:4px solid #2e7d32;background:#f1f8f4}"
        ".pred-card.neutral{border-left:4px solid #78909c;background:#fafafa}"
        "table.kp{width:100%;border-collapse:collapse;font-size:.8rem}"
        "table.kp th,table.kp td{border:1px solid #e0e0e0;padding:.35rem}"
        "table.kp th{background:#ede7f6}" + tags
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


def _cusp_table(kp: KPChart) -> str:
    rows = []
    for c in kp.cusps:
        rows.append(
            f"<tr><td>{c['cusp']}</td><td>{c['degree']}</td><td>{c['sign']}</td>"
            f"<td>{c['nak']}</td><td><strong>{c['sub']}</strong></td><td>{c['ss']}</td></tr>"
        )
    return (
        "<table class='kp'><tr><th>H</th><th>Degree</th><th>Sign</th><th>Nak</th>"
        "<th>CSL</th><th>SS</th></tr>" + "".join(rows) + "</table>"
    )


def _planet_table(kp: KPChart) -> str:
    rows = []
    for p in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        v = kp.planets.get(p)
        if not v:
            continue
        rows.append(
            f"<tr><td>{p}</td><td>{v['degree']}</td><td>{v['sign']}</td>"
            f"<td>{v['nak']}</td><td>{v['sub']}</td><td>{v['ss']}</td></tr>"
        )
    return (
        "<table class='kp'><tr><th>Planet</th><th>Degree</th><th>Sign</th>"
        "<th>Nak</th><th>Sub</th><th>SS</th></tr>" + "".join(rows) + "</table>"
    )


def _signif_table(kp: KPChart) -> str:
    rows = "".join(
        f"<tr><td>{h}</td><td>{', '.join(kp.signif.get(h, []))}</td></tr>" for h in range(1, 13)
    )
    return "<table class='kp'><tr><th>House</th><th>Significators</th></tr>" + rows + "</table>"


def _planet_signif_table(kp: KPChart) -> str:
    rows = "".join(
        f"<tr><td>{p}</td><td>{', '.join(_ord(h) for h in kp.planet_signif.get(p, []))}</td></tr>"
        for p in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
        if p in kp.planet_signif
    )
    return "<table class='kp'><tr><th>Planet</th><th>Houses signified</th></tr>" + rows + "</table>"


def _dasha_table(kp: KPChart) -> str:
    rows = "".join(f"<tr><td>{a['lord']}</td><td>{fmt(a['end'])}</td></tr>" for a in kp.antars)
    maha = kp.maha
    head = (
        f"<p class='pred'><strong>{maha['lord']} mahā</strong> "
        f"{fmt(maha['start'])} – {fmt(maha['end'])} (KP Vimshottari).</p>"
        if maha else ""
    )
    return head + (
        "<table class='kp'><tr><th>Antardaśā</th><th>Ends (KP)</th></tr>" + rows + "</table>"
    )


def _praty_table(kp: KPChart) -> str:
    if not kp.pratyantars:
        return "<p class='fine'>Pratyantar grid not parsed for current antar.</p>"
    rows = "".join(
        f"<tr><td>{p['lord']}</td><td>{fmt(p['start'])}</td><td>{fmt(p['end'])}</td></tr>"
        for p in kp.pratyantars
    )
    cur = kp.current_antar()
    title = f"Pratyantar — {kp.maha.get('lord')}–{cur.get('lord')} antar" if cur else "Pratyantar"
    return (
        f"<p class='pred'>{title}</p>"
        "<table class='kp'><tr><th>Lord</th><th>Start</th><th>End</th></tr>" + rows + "</table>"
    )


def render_kp_html(
    kp: KPChart,
    sections: list[LifeSection],
    pc: dict,
    dob_disp: str,
    tob: str = "",
    place: str = "",
    extract_path: str = "",
    source_label: str = "pyjhora",
) -> str:
    nm = _e(kp.name)
    today = date.today()
    hero = kp_hero(kp)
    callout = kp_now_callout(kp)
    timing = kp_year_ahead_html(kp)
    body_sections = "".join(_section_html(s) for s in sections if s.domain != "intro")

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Vedic reading — KP — {nm}</title>
<style>{_css()}</style></head><body>
  <article class="card">
    <h1 style="color:#0d47a1;border:none;margin-top:0;">Krishnamurti Paddhati — chapter reading</h1>
    <p class="note" style="margin-top:0;">Standalone <strong>KP lane</strong>. Houses and timing follow
    <strong>cusp sub lords</strong> and <strong>KP Vimshottari</strong> computed via PyJHora (KP ayanamsa, Placidus cusps) — not whole-sign D1 alone.
    Merged report: book-backed CSL verdicts + legacy gold foundation tables. Final confluence is a later step.</p>
    <dl class="meta" style="display:grid;grid-template-columns:auto 1fr;gap:.25rem .75rem;font-size:.92rem;color:#b0106b;">
      <dt>Client</dt><dd>{nm}</dd>
      <dt>Born</dt><dd>{_e(dob_disp)}{(' · ' + _e(tob)) if tob else ''}{(' · ' + _e(place)) if place else ''}</dd>
      <dt>Lagna</dt><dd>{kp.lagna} · CSL-1 {kp.csl(1) or '—'}</dd>
      <dt>Ayanāṃśa</dt><dd>K. P. New (PyJHora KP)</dd>
      <dt>Source</dt><dd><code>{_e(source_label)}</code></dd>
      <dt>Report date</dt><dd>{today.strftime('%d %B %Y').lstrip('0')}</dd>
    </dl>

    <div class="hero"><p class="pred" style="margin:0;">{_e(hero)}</p></div>
    {callout}
    {timing}

    <p class="lead">Below: what each life area means for you in plain English. KP uses <strong>cusp sub lords</strong> and the dasha clock from PyJHora — technical tables sit in the appendix.</p>

    {body_sections}

    <p class="note">Your Jaimini, Mehta, or Vimśottarī report may name different timings — normal.
    Use this file for <strong>cusp-level precision</strong>; use sign-based lanes for seasonal mood.</p>

    <details class="appendix" style="margin-top:1.5rem;font-size:.88rem;">
      <summary>KP chart facts (technical appendix)</summary>
      <h2>Cuspal sub lords</h2>{_cusp_table(kp)}
      <h2>Planet star / sub</h2>{_planet_table(kp)}
      <h2>Significators of houses</h2>{_signif_table(kp)}
      <h2>Planet signification</h2>{_planet_signif_table(kp)}
      <h2>Vimśottari antar (KP)</h2>{_dasha_table(kp)}
      <h2>Pratyantar (current antar)</h2>{_praty_table(kp)}
    </details>

    <p class="note">Educational Jyotiṣa only. Verify cusp subs and daśā cuts in your software before major decisions.</p>
  </article>
</body></html>"""


def generate_kp_html(
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
    d = datetime.strptime(dob, "%Y-%m-%d").date()
    kp = load_kp_chart(
        extracted_path=extracted_path or "",
        client_name=client_name,
        dob=dob,
        pc=pc,
    )
    sections = build_life_sections(kp)
    if precomputed_path:
        source_label = f"precomputed:{precomputed_path}"
    elif birth_time and latitude is not None:
        source_label = "pyjhora:birth_flags"
    elif extracted_path:
        source_label = f"extract:{extracted_path}"
    else:
        source_label = pc.get("kp", {}).get("source", "pyjhora")
    doc = render_kp_html(
        kp, sections, pc, d.strftime("%d %B %Y").lstrip('0'), tob, place,
        extracted_path or "", source_label=source_label,
    )
    summary = {
        "lagna": kp.lagna,
        "cusp_subs": {c["cusp"]: c["sub"] for c in kp.cusps},
        "maha": kp.maha.get("lord"),
        "current_antar": kp.current_antar().get("lord"),
        "current_pratyantar": kp.current_pratyantar().get("lord"),
        "sections": len(sections),
        "pratyantars": len(kp.pratyantars),
    }
    return doc, summary


def main() -> None:
    ap = argparse.ArgumentParser(description="KP chapter report (deterministic)")
    ap.add_argument("name")
    ap.add_argument("dob")
    ap.add_argument("extracted", nargs="?", default=None, help="Optional legacy AstroSage extract")
    add_chart_source_args(ap)
    ap.add_argument("--tob", default="")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    kw = chart_kwargs_from_args(args)
    doc, summary = generate_kp_html(
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
    out = Path(args.out) if args.out else BASE_DIR / "reports" / f"KP_{args.name}_preview.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(
        f"sections={summary['sections']} praty={summary['pratyantars']} "
        f"maha={summary['maha']} antar={summary['current_antar']} "
        f"pratyantar={summary['current_pratyantar']}"
    )
    print("cusp subs:", summary["cusp_subs"])
    print(f"written → {out}")


if __name__ == "__main__":
    main()
