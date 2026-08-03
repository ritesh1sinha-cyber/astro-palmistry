#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RTVD gold-style foundation sections (chart essentials, age table, methodology)."""
from __future__ import annotations

from typing import Any

from rtvd_book_data import load_rtvd_book


def _dual_lord_houses(r: Any, h: int) -> list[int]:
    lord = r.houses[h]["lord"]
    return [hh for hh in range(1, 13) if hh != h and r.houses[hh]["lord"] == lord]


def chart_essentials_html(r: Any) -> str:
    rows = []
    for h in range(1, 13):
        hh = r.houses[h]
        dual = _dual_lord_houses(r, h)
        dual_note = ""
        if dual:
            dual_note = f' <span class="muted">(also rules {", ".join(str(x) for x in dual)})</span>'
        rows.append(
            f"<tr><td>{h}</td><td>{hh['sign']}</td>"
            f"<td>{hh['lord']}{dual_note}</td>"
            f"<td>{hh['lord_house']}</td></tr>"
        )
    return (
        '<h1>1 - Chart essentials (whole-sign from lagna)</h1>'
        '<p class="fact">Each calendar year maps to one sign-house from your Ascendant. '
        'Year-lord placement and dual lordship drive the read.</p>'
        '<table><tr><th>House</th><th>Sign</th><th>Lord</th><th>Lord sits in</th></tr>'
        + "".join(rows)
        + "</table>"
    )


def _row_class(y: dict, peak_ages: set[int], warn_ages: set[int]) -> str:
    if y["age"] in peak_ages:
        return "peak"
    if y["age"] in warn_ages:
        return "warn"
    if y["tone"] == "bad":
        return "bad"
    if y["tone"] == "good":
        return "cur"
    return ""


def age_reference_html(
    r: Any,
    years: list[dict],
    peak_ages: set[int],
    warn_ages: set[int],
    age_min: int = 1,
    age_max: int = 72,
) -> str:
    rows = []
    for y in years:
        if y["age"] < age_min or y["age"] > age_max:
            continue
        cls = _row_class(y, peak_ages, warn_ages)
        tr = f'<tr class="{cls}">' if cls else "<tr>"
        dual = _dual_lord_houses(r, y["house"])
        dual_txt = f" (+{dual[0]})" if dual else ""
        rows.append(
            f"{tr}"
            f'<td>{y["age"]}</td><td>{y["calendar"]}</td>'
            f'<td>{y["house"]}</td><td>{y["sign"]}</td>'
            f'<td>{y["lord"]}{dual_txt}</td>'
            f'<td>{y["lord_house"]}</td>'
            f'<td>{y["from_moon"]} from Moon</td>'
            f'<td>{y["tone"]}</td></tr>'
        )
    return (
        '<h1>2 - Age to house reference</h1>'
        '<p class="fact">Age 1 = 1st house; cycle repeats every 12 years. '
        'Green = benefic mass on year sign/lord; amber = stress; red = malefic mass.</p>'
        '<table><tr><th>Age</th><th>Year</th><th>House</th><th>Sign</th>'
        '<th>Lord</th><th>Lord in</th><th>Moon view</th><th>Tone</th></tr>'
        + "".join(rows)
        + "</table>"
    )


def methodology_html() -> str:
    book = load_rtvd_book()
    rules = book.get("general_rules", [])
    cert = book.get("certainty_levels", [])
    items = "".join(f"<li>{r}</li>" for r in rules[:18])
    cert_items = "".join(f"<li>{c}</li>" for c in cert)
    return (
        '<h1>0 - Methodology (book-backed)</h1>'
        f'<p class="pred">{book.get("methodology_lead", "")}</p>'
        "<h2>General rules (Guru Rajesh)</h2><ul>" + items + "</ul>"
        "<h2>Certainty hierarchy</h2><ul>" + cert_items + "</ul>"
    )


def vimshottari_cross_html(pc: dict | None, years: list[dict], age_min: int, age_max: int) -> str:
    if not pc or "vimshottari" not in pc:
        return ""
    vim = pc["vimshottari"]
    md = vim.get("current_md") or {}
    md_lord = md.get("md_lord", "")
    md_rng = f"{md.get('start', '')} to {md.get('end', '')}" if md else ""
    ads = vim.get("current_md_antardashas") or []
    cur_ad = next((a for a in ads if a.get("status") == "current"), ads[0] if ads else {})
    ad_lord = cur_ad.get("ad_lord", "")
    ad_rng = f"{cur_ad.get('start', '')} to {cur_ad.get('end', '')}" if cur_ad else ""
    dasha_note = f"MD {md_lord} ({md_rng}); AD {ad_lord} ({ad_rng})"
    rows = []
    for y in years:
        if y["age"] < age_min or y["age"] > age_max:
            continue
        rows.append(
            f"<tr><td>{y['age']}</td><td>{y['calendar']}</td>"
            f"<td>{y['house']} ({y['sign']})</td>"
            f"<td>{y['lord']}</td>"
            f"<td>{dasha_note}</td></tr>"
        )
    if not rows:
        return ""
    return (
        '<h1>3 - Vimshottari triangulation note</h1>'
        '<p class="fact">RTVD gives the annual house; Vimshottari and transits narrow the month. '
        'Forward dating should align active MD/AD lords with the year-lord chain.</p>'
        '<table><tr><th>Age</th><th>Calendar</th><th>RTVD house</th><th>Year-lord</th>'
        '<th>Dasha context</th></tr>'
        + "".join(rows[:24])
        + "</table>"
    )
