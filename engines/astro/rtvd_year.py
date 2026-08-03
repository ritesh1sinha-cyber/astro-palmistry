#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RTVD year-level analysis: certainty, nakshatra chain, topic windows."""
from __future__ import annotations

from typing import Any

from rtvd_book_data import load_rtvd_book, topic_spec

NAK_LORD = {
    "Ashwini": "Ketu", "Bharani": "Venus", "Krittika": "Sun", "Rohini": "Moon",
    "Mrigashira": "Mars", "Ardra": "Rahu", "Punarvasu": "Jupiter", "Pushya": "Saturn",
    "Ashlesha": "Mercury", "Magha": "Ketu", "Purva Phalguni": "Venus", "Uttara Phalguni": "Sun",
    "Hasta": "Mercury", "Chitra": "Mars", "Swati": "Rahu", "Vishakha": "Jupiter",
    "Anuradha": "Saturn", "Jyeshtha": "Mercury", "Mula": "Ketu", "Purva Ashadha": "Venus",
    "Uttara Ashadha": "Sun", "Shravana": "Moon", "Dhanishta": "Mars", "Shatabhisha": "Rahu",
    "Purva Bhadrapada": "Jupiter", "Uttara Bhadrapada": "Saturn", "Revati": "Mercury",
}


def nakshatra_lord(r: Any, planet: str) -> str:
    nk = r.planets.get(planet, {}).get("nakshatra", "")
    return NAK_LORD.get(nk, "")


def certainty_level(r: Any, y: dict, target_houses: list[int]) -> int:
    """1=highest ... 4=backdrop; 0=no direct link."""
    lord = y["lord"]
    lp = r.planets.get(lord, {})
    lh = lp.get("house", 0)
    if lh in target_houses:
        return 1
    nk_l = nakshatra_lord(r, lord)
    if nk_l:
        nk_h = r.planets.get(nk_l, {}).get("house", 0)
        nk_own = [h for h in range(1, 13) if r.houses[h]["lord"] == nk_l]
        if nk_h in target_houses or any(h in target_houses for h in nk_own):
            return 2
    for th in target_houses:
        th_lord = r.houses[th]["lord"]
        if th_lord == lord:
            return 3
        if lp.get("sign") == r.houses[th]["sign"]:
            return 3
    if y["house"] in target_houses:
        return 4
    return 0


def year_analysis_rows(r: Any, y: dict) -> list[tuple[str, str]]:
    lord = y["lord"]
    lp = r.planets.get(lord, {})
    nk = lp.get("nakshatra", "")
    nk_l = nakshatra_lord(r, lord)
    nk_h = r.planets.get(nk_l, {}).get("house", "") if nk_l else ""
    dual = [hh for hh in range(1, 13) if hh != y["house"] and r.houses[hh]["lord"] == lord]
    rows = [
        ("Active house", f"{y['house']} ({y['sign']})"),
        ("Year-lord", lord + (f" (also rules {dual[0]})" if dual else "")),
        ("Lord placed in", f"{lp.get('sign', '?')} - house {lp.get('house', '?')}"),
    ]
    if nk:
        rows.append(("Lord nakshatra", f"{nk} (lord {nk_l}, in house {nk_h})"))
    rows.append(("From Moon", f"{y['from_moon']} from Moon sign"))
    return rows


def topic_window_years(
    r: Any,
    years: list[dict],
    domain: str,
    age_min: int,
    age_max: int,
) -> list[dict]:
    book = load_rtvd_book()
    spec = topic_spec(book, domain)
    if not spec:
        return []
    primary = spec.get("primary")
    if primary is None:
        primary = list(dict.fromkeys(
            list(spec.get("father", [])) + list(spec.get("mother", []))
        ))
    also = spec.get("also", [])
    targets = list(dict.fromkeys(primary + also))
    hits = []
    for y in years:
        if y["age"] < age_min or y["age"] > age_max:
            continue
        lvl = certainty_level(r, y, targets)
        if lvl == 0:
            continue
        hits.append({**y, "certainty": lvl})
    hits.sort(key=lambda x: (x["certainty"], -x["age"]))
    return hits[:12]


def topic_prose(r: Any, domain: str, hits: list[dict]) -> tuple[str, str, str]:
    book = load_rtvd_book()
    spec = topic_spec(book, domain)
    rules = book.get("topic_rules", {}).get(domain, [])[:2]
    primary = spec.get("primary")
    if primary is None:
        primary = list(dict.fromkeys(
            list(spec.get("father", [])) + list(spec.get("mother", []))
        ))
    also = spec.get("also", [])
    ages_note = spec.get("ages_note", "")
    rule_txt = " ".join(rules) if rules else ""
    if hits:
        top = hits[0]
        pred = (
            f"Strongest {domain} window in the scan: age {top['age']} ({top['calendar']}) - "
            f"house {top['house']} ({top['sign']}), year-lord {top['lord']} "
            f"(certainty level {top['certainty']}). "
        )
        if len(hits) > 1:
            others = ", ".join(f"age {h['age']}" for h in hits[1:4])
            pred += f"Also watch {others}. "
    else:
        pred = f"No high-certainty {domain} windows in the selected age band; check wider table. "
    pred += f"Book houses: primary {primary}, also {also}. {ages_note}. "
    if rule_txt:
        pred += rule_txt[:200]
    fact = f"RTVD {domain}: targets {_targets_str(primary, also)}"
    return pred, fact, ""


def _targets_str(primary: list, also: list) -> str:
    parts = []
    if primary:
        parts.append("primary " + str(primary))
    if also:
        parts.append("also " + str(also))
    return "; ".join(parts)


def illustrative_card_html(r: Any, y: dict, title: str, fired: str, walk: str) -> str:
    rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in year_analysis_rows(r, y)
    )
    return (
        f'<h2>{title}</h2><div class="card"><table><tr><th>Item</th><th>Value</th></tr>{rows}'
        f'<tr><td>Rule fired</td><td>{fired}</td></tr></table>'
        f'<p><strong>Rule walk:</strong> {walk}</p></div>'
    )
