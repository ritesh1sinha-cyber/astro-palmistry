#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
astro_palmistry_report.py - Astro-Palmistry lane (Jyotis Saraswati).

Derives birth-data sketch from phalange line counts per Chapter XVII,
optionally cross-checks against known birth chart data.

Usage:
    python3 astro_palmistry_report.py --name Client --json counts.json --out reports/...
    python3 validate_astro_palmistry_cases.py
"""
from __future__ import annotations

import argparse
import html
import json
from datetime import date
from pathlib import Path
from typing import Any, Optional

from astro_palmistry_cases import ALL_CASES
from astro_palmistry_chart_lane import chart_analysis_html
from astro_palmistry_engine import (
    DerivedBirthData,
    PalmLineCounts,
    counts_from_manual_table,
    derive_from_lines,
)
from client_report_html import client_css, finalize_report_html

BASE_DIR = Path(__file__).resolve().parent
BOOK_JSON = BASE_DIR / "astro_palmistry_book_data.json"


def _e(s: Any) -> str:
    return html.escape(str(s))


def _load_book_meta() -> dict:
    if BOOK_JSON.is_file():
        try:
            return json.loads(BOOK_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"title": "Astro-Palmistry", "rule_count": 0}


def _steps_html(steps: list[str]) -> str:
    items = "".join(f"<li>{_e(s)}</li>" for s in steps)
    return f'<ol class="steps">{items}</ol>'


def _tri_row(label: str, tri: tuple[str, str, str], rem: int) -> str:
    return (
        f"<tr><td>{_e(label)}</td><td>{rem}</td>"
        f"<td>{_e(', '.join(tri))}</td></tr>"
    )


def _reference_cases_html() -> str:
    rows = []
    for c in ALL_CASES:
        exp = ", ".join(f"{k}={v}" for k, v in c.expected.items())
        status = "validated" if c.validation == "full" else "answer key"
        rows.append(
            f"<tr><td>{c.id}</td><td>{_e(c.title)}</td>"
            f"<td>{_e(status)}</td><td>{_e(exp)}</td></tr>"
        )
    return (
        "<table class='tl'><tr><th>#</th><th>Case</th><th>Status</th><th>Expected</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def _cross_check(
    derived: DerivedBirthData,
    known_dob: Optional[str],
    known_time: Optional[str],
    known_asc: Optional[str],
) -> str:
    if not any([known_dob, known_time, known_asc]):
        return ""
    parts = ["<div class='card amber'><h3>Cross-check with known birth data</h3><ul class='bullets'>"]
    if known_asc:
        ok = derived.ascendant_sign.lower() == known_asc.strip().lower()
        mark = "matches" if ok else "differs from"
        parts.append(
            f"<li>Palm-derived lagna <strong>{_e(derived.ascendant_sign)}</strong> "
            f"{mark} stated {_e(known_asc)}.</li>"
        )
    if known_dob:
        parts.append(
            f"<li>Known DOB {_e(known_dob)}: reconcile tithi ({derived.tithi}, {derived.paksha}), "
            f"solar sign ({derived.solar_sign}), weekday ({derived.weekday}) with ephemeris.</li>"
        )
    if known_time:
        parts.append(
            f"<li>Known time {_e(known_time)}: refine within lagna duration table "
            f"(Capricorn 1h59m, Leo 2h34m, etc.).</li>"
        )
    parts.append("</ul></div>")
    return "".join(parts)


def generate_astro_palmistry_html(
    *,
    client_name: str,
    counts: PalmLineCounts,
    out_path: Path,
    known_dob: str = "",
    known_time: str = "",
    known_place: str = "",
    known_asc: str = "",
    impression_age: Optional[int] = None,
    report_date: Optional[date] = None,
    cv_analysis: Optional[dict] = None,
    chart_mode: bool = False,
    chart_analysis: Optional[dict] = None,
) -> Path:
    book = _load_book_meta()
    rdate = report_date or date.today()

    if chart_mode and chart_analysis:
        derived = None
        hero = (
            f"<p>Chart-driven astro-palmistry: each planet in its house is a <strong>line main</strong> "
            f"for that palm zone. Other planets are <strong>sub-planets</strong> whose house positions "
            f"carry book meanings (e.g. Jupiter@8 main + Ketu@5 sub + Mercury@10 sub). "
            f"Confluence merges themes; CV marks zones on your palm photo.</p>"
        )
        facts = (
            f"<p class='fine'>Lagna <strong>{_e(chart_analysis.get('lagna', ''))}</strong>"
            + (f" &middot; DOB {_e(chart_analysis.get('dob', ''))}" if chart_analysis.get("dob") else "")
            + (f" &middot; {_e(chart_analysis.get('birth_time', ''))}" if chart_analysis.get("birth_time") else "")
            + "</p>"
        )
        body_main = chart_analysis_html(chart_analysis)
        steps_block = ""
        planets_block = ""
        cross = ""
    else:
        derived = derive_from_lines(counts)
        hero = (
            f"<p>Phalange line counts from both hands are applied using the Saraswati "
            f"astro-palmistry method (Chapter XVII). This yields a <em>rough</em> birth "
            f"sketch: tithi, solar month, weekday, rising sign, and outer-planet "
            f"triplicities before ephemeris reconciliation.</p>"
        )
        facts = f"""
<table class="tl">
  <tr><th>Field</th><th>From palm lines</th></tr>
  <tr><td>Lunar tithi</td><td>{derived.tithi} ({_e(derived.paksha)})</td></tr>
  <tr><td>Solar month sign</td><td>{_e(derived.solar_sign)}</td></tr>
  <tr><td>Weekday</td><td>{_e(derived.weekday)}</td></tr>
  <tr><td>Ascendant (rough)</td><td><strong>{_e(derived.ascendant_sign)}</strong> (rem {derived.asc_remainder})</td></tr>
</table>"""
        body_main = ""
        steps_block = f"""
  <div class="section-h">Calculation steps</div>
  <div class="card">{_steps_html(derived.steps)}</div>

  <div class="section-h">Outer planets (triplicity)</div>
  <div class="card">{(
        "<table class='tl'><tr><th>Body</th><th>Rem</th><th>Triplicity signs</th></tr>"
        + _tri_row("Jupiter", derived.jupiter_triplicity, derived.jupiter_remainder)
        + _tri_row("Saturn", derived.saturn_triplicity, derived.saturn_remainder)
        + _tri_row("Rahu", derived.rahu_triplicity, derived.rahu_remainder)
        + _tri_row("Ketu (opposite)", derived.ketu_triplicity, derived.rahu_remainder)
        + "</table>"
        + "<p class='fine'>Pick the sign within each triplicity that matches the birth-year ephemeris "
        "(book allows -1 remainder adjustment for Saturn/Jupiter/Rahu).</p>"
    )}</div>"""
        cross = _cross_check(derived, known_dob, known_time, known_asc)
        planets_block = ""

    age_note = ""
    if impression_age and not chart_mode and derived:
        est_year = rdate.year - impression_age
        age_note = (
            f"<p class='fine'>Impression age ~{impression_age} suggests birth year near "
            f"<strong>{est_year}</strong> (check ephemeris for {derived.solar_sign} + tithi + weekday).</p>"
        )

    cv_block = ""
    if cv_analysis and not chart_mode:
        q = cv_analysis.get("quality", "?")
        cv_block = f'<p class="fine">Line counts from <strong>CV</strong> (MediaPipe + phalange ROIs). Quality: <strong>{_e(q)}</strong>.</p>'
        agg = cv_analysis.get("aggregated") or {}
        if agg:
            cv_block += (
                "<table class='tl'><tr><th>CV aggregate</th><th>Count</th></tr>"
                + "".join(f"<tr><td>{_e(k)}</td><td>{_e(v)}</td></tr>" for k, v in agg.items())
                + "</table>"
            )
        retake = cv_analysis.get("needs_retake") or []
        if retake:
            items = "".join(f"<li><strong>{_e(r.get('slot',''))}</strong>: {_e(r.get('reason',''))}</li>" for r in retake[:14])
            cv_block += f'<div class="note" style="margin-top:10px"><p><strong>Sharper photos recommended</strong></p><ul class="bullets">{items}</ul></div>'

    body = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<title>Astro-Palmistry - {_e(client_name)}</title>
<style>{client_css()}
.steps {{ margin:.5rem 0 .75rem 1.2rem; font-size:.9rem; }}
.steps li {{ margin:.35rem 0; }}
.fine {{ font-size:.88rem; color:var(--muted); }}
</style>
</head><body>
<div class="wrap">
  <div class="hero">
    <h1>Astro-Palmistry Report</h1>
    <div class="tag">{_e(client_name)}</div>
    <div class="meta">
      <span>Report {rdate.isoformat()}</span>
      <span>Source: {_e(book.get('title', 'Astro-Palmistry'))}</span>
      <span>{book.get('rule_count', 0)} corpus rules indexed</span>
    </div>
  </div>

  <div class="note">
    {"Chart positions are mapped to palm mounts and lines per Saraswati Astro-Palmistry. Upload finger close-ups later to confirm what the chart predicts on the hand." if chart_mode else "Palm-derived birth data is a <strong>first sketch</strong>. Final date, time, and planet positions require ephemeris matching (Chapter IX) and lagna tables. Three Chapter XVII worked examples validate this engine; cases 4-6 are reader answer keys."}
  </div>

  <div class="section-h">{"Chart-based palm read" if chart_mode else "Summary from your hand counts"}</div>
  <div class="card green">{hero}{cv_block}{facts}{age_note}</div>
  {body_main}

  {cross}

  {steps_block}

  <div class="section-h">Next steps</div>
  <div class="card blue">
    <ul class="bullets">
      {("<li>Photograph Plain of Mars, upper Mars (Ketu zone), and mounts named in each house section.</li>"
        "<li>Compare debilitated vs exalted signatures (Mars, Mercury, Venus) against the dignity notes above.</li>"
        "<li>Re-run with palm CV once close-ups are ready to cross-check chart vs counted lines.</li>"
        "<li>Read marriage, children, and career themes from 5th / 7th / 10th house palm zones.</li>")
       if chart_mode else
       ("<li>Match tithi + solar sign + weekday to a concrete date in the ephemeris.</li>"
        "<li>Use ascendant sign + place latitude for lagna time window (Saturn, Friend or Foe tables).</li>"
        "<li>Refine exact time with (ASC+Sun)/2=Moon or (Sun+Moon)/2 formulas when planets are known.</li>"
        "<li>Cast D1 and read personality, marriage, career per astro-palmistry corpus.</li>")}
    </ul>
    {f'<p class="fine">Known place: {_e(known_place)}</p>' if known_place else ''}
  </div>

  <details class="appendix">
    <summary>Chapter XVII validation cases (book)</summary>
    {_reference_cases_html()}
  </details>
</div>
</body></html>"""

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(finalize_report_html(body, client_name), encoding="utf-8")
    return out_path


def counts_from_dict(d: dict) -> PalmLineCounts:
    return counts_from_manual_table(
        moon_a=int(d["moon_a"]),
        moon_b=int(d["moon_b"]),
        month_a=int(d["month_a"]),
        month_b=int(d["month_b"]),
        day_left=int(d["day_left"]),
        day_right=int(d["day_right"]),
        asc_a=int(d["asc_a"]),
        asc_b=int(d["asc_b"]),
        thumb_lines=int(d["thumb_lines"]),
        percussion_lines=int(d["percussion_lines"]),
        bright_half=bool(d.get("bright_half", True)),
        yav_crossed=bool(d.get("yav_crossed", False)),
        jupiter_adj=int(d.get("jupiter_adj", 0)),
        saturn_adj=int(d.get("saturn_adj", 0)),
        rahu_adj=int(d.get("rahu_adj", 0)),
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate Astro-Palmistry HTML report")
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", help="JSON file with PalmLineCounts fields")
    ap.add_argument("--example", type=int, choices=[1, 2, 3], help="Use Chapter XVII case counts")
    ap.add_argument("--known-dob", default="")
    ap.add_argument("--known-time", default="")
    ap.add_argument("--known-place", default="")
    ap.add_argument("--known-asc", default="")
    ap.add_argument("--impression-age", type=int, default=0)
    args = ap.parse_args()

    if args.example:
        case = ALL_CASES[args.example - 1]
        if case.counts is None:
            raise SystemExit(f"Example {args.example} has no line-count table in the book.")
        counts = case.counts
    elif args.json:
        counts = counts_from_dict(json.loads(Path(args.json).read_text(encoding="utf-8")))
    else:
        raise SystemExit("Provide --json counts or --example N")

    generate_astro_palmistry_html(
        client_name=args.name,
        counts=counts,
        out_path=Path(args.out),
        known_dob=args.known_dob,
        known_time=args.known_time,
        known_place=args.known_place,
        known_asc=args.known_asc,
        impression_age=args.impression_age or None,
    )
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
