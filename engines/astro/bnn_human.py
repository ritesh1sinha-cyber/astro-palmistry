#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BNN prediction prose - chart-generic book lookups + legacy timing tables."""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from bnn_book_data import house_from_jupiter, humanize_bnn, load_bnn_book, lookup_from_jupiter, lookup_node_in_house
from bnn_chart import BODY, fmt_date, lord_verdict
from bnn_chart_text import (
    antar_chart_note,
    antar_unload,
    book_clause,
    book_planet_sign,
    conjunction_pairs,
    esc,
    intro_stack,
    karaka_planet,
    lord_line,
    placement_fact,
)
from bnn_combination import is_claimed, pair_section_html
from bnn_foundation import career_verdict_html, marriage_timing_html

if TYPE_CHECKING:
    from bnn_chart import BnnChart, BnnTiming


def _venus_window(bt: "BnnTiming") -> dict | None:
    for w in bt.antar_windows():
        if w["lord"] == "Venus" and w["end"] > date.today():
            return w
    return None


def human_intro(ch: "BnnChart", bt: "BnnTiming") -> str:
    return intro_stack(ch, bt)


def human_personality(ch: "BnnChart", bt: "BnnTiming") -> tuple[str, str]:
    """Synthesis paragraph - detailed table lives in foundation module."""
    fact = f"Lagna {ch.lagna} - Moon {ch.sign('Moon')} {ch.h('Moon')}th - AK {ch.atmakaraka() or '-'}"
    pairs = []
    for a, b in conjunction_pairs(ch)[:2]:
        pairs.append(f"{a}-{b} in the {ch.h(a)}th")
    synth = (
        f"Your BNN temperament blends {ch.lagna} rising with Moon in the {ch.h('Moon')}th. "
        + ("Key conjunctions: " + "; ".join(pairs) + ". " if pairs else "")
        + "Combination chapters below carry the full Avasthi bullet lists; this section is synthesis only."
    )
    return synth, fact


def human_conjunction_section(ch: "BnnChart", a: str, b: str, male: bool = True) -> tuple[str, str, str]:
    return pair_section_html(ch, a, b, male=male)


def human_marriage(ch: "BnnChart", bt: "BnnTiming") -> tuple[str, str, str]:
    l7 = ch.lord_of_house(7)
    fact = lord_line(ch, 7)
    parts = book_clause(
        book_planet_sign(ch, l7),
        book_planet_sign(ch, "Venus", "positive"),
        max_n=3,
    )
    dk = karaka_planet(ch, "Darakaraka")
    if dk and dk in ch.planets:
        parts.append(
            f"Darakaraka {dk} in {ch.sign(dk)} (house {ch.h(dk)}, {ch.dig(dk).replace('_', ' ')}): "
            "spouse tone follows this planet's house themes."
        )
    occ = ch.in_house(7)
    if occ:
        parts.append(f"Planets in the 7th ({', '.join(occ)}): partnership field is coloured by their joint influence.")
    ven = _venus_window(bt)
    if ven:
        parts.append(
            f"Partnership-friendly sub-period: Venus antar {fmt_date(ven['start'].isoformat())} - "
            f"{fmt_date(ven['end'].isoformat())}."
        )
    timing = marriage_timing_html(ch, bt)
    html_extra = f"<div class='marriage-timing'>{timing}</div>" if timing else ""
    pred = " ".join(parts)
    return pred, fact, html_extra


def human_career(ch: "BnnChart", bt: "BnnTiming") -> tuple[str, str, str]:
    fact = lord_line(ch, 10)
    parts = book_clause(
        book_planet_sign(ch, ch.lord_of_house(10)),
        book_planet_sign(ch, karaka_planet(ch, "Amatyakarak")) if karaka_planet(ch, "Amatyakarak") else "",
        max_n=3,
    )
    for p in ch.in_house(10):
        parts.append(book_planet_sign(ch, p) or placement_fact(ch, p))
    verdict = career_verdict_html(ch)
    pred = " ".join(parts[:4])
    return pred, fact, verdict


def human_health(ch: "BnnChart") -> tuple[str, str]:
    fact = lord_line(ch, 6)
    book = load_bnn_book()
    parts = book_clause(
        book_planet_sign(ch, ch.lord_of_house(6)),
        humanize_bnn(lookup_node_in_house(book, "Rahu", ch.h("Rahu"))) if "Rahu" in ch.planets else "",
        max_n=3,
    )
    parts.append(
        f"Watch {BODY.get(ch.lagna, 'lagna body zone')} (lagna) and "
        f"{BODY.get(ch.house_sign(6), '6th-house zone')} (6th) under stress cycles."
    )
    for p in ch.in_house(6):
        parts.append(placement_fact(ch, p))
    return " ".join(parts[:4]), fact


def human_children(ch: "BnnChart", bt: "BnnTiming") -> tuple[str, str]:
    fact = lord_line(ch, 5)
    pk = karaka_planet(ch, "Putrakaraka")
    parts = book_clause(
        book_planet_sign(ch, ch.lord_of_house(5)),
        book_planet_sign(ch, "Jupiter", "positive"),
        book_planet_sign(ch, pk) if pk else "",
        max_n=3,
    )
    if "Ketu" in ch.in_house(5):
        parts.append("Ketu in the 5th: fewer, late, or spiritually independent children are common BNN themes.")
    return " ".join(parts), fact


def human_travel(ch: "BnnChart") -> tuple[str, str]:
    fact = lord_line(ch, 9)
    parts = book_clause(
        book_planet_sign(ch, ch.lord_of_house(9)),
        book_planet_sign(ch, "Sun"),
        book_planet_sign(ch, "Rahu"),
        max_n=3,
    )
    return " ".join(parts), fact


def human_siblings(ch: "BnnChart") -> tuple[str, str]:
    fact = lord_line(ch, 3)
    bk = karaka_planet(ch, "Bhratrukaraka")
    parts = book_clause(
        book_planet_sign(ch, ch.lord_of_house(3)),
        book_planet_sign(ch, bk) if bk else "",
        book_planet_sign(ch, "Mars"),
        max_n=3,
    )
    return " ".join(parts), fact


def human_parents(ch: "BnnChart") -> tuple[str, str]:
    fact = f"Sun {ch.h('Sun')}th - Moon {ch.h('Moon')}th - 9th {lord_line(ch, 9)}"
    moon = book_planet_sign(ch, "Moon")
    if moon and is_claimed(moon):
        moon = f"Moon in {ch.sign('Moon')} (house {ch.h('Moon')}): emotional inheritance from the mother line."
    sun = book_planet_sign(ch, "Sun") or (
        f"Sun in {ch.sign('Sun')} (house {ch.h('Sun')}): father/authority themes follow the 9th-and-10th tone."
    )
    jup = book_planet_sign(ch, "Jupiter") or placement_fact(ch, "Jupiter")
    return " ".join(x for x in (moon, sun, jup) if x), fact


def human_past_themes(ch: "BnnChart") -> str:
    return human_past_themes_html(ch)


def human_past_themes_html(ch: "BnnChart") -> str:
    bullets = []
    for a, b in conjunction_pairs(ch):
        bullets.append(
            f"<li><strong>{a} + {b} (house {ch.h(a)}):</strong> recurring {a}-{b} themes - "
            "see conjunction section for book bullets.</li>"
        )
    for p in ("Jupiter", "Saturn", "Rahu", "Ketu"):
        if p in ch.planets and ch.dig(p) == "debilitated":
            bullets.append(
                f"<li><strong>{p} debilitated in house {ch.h(p)}:</strong> lessons through restraint and patience in "
                f"{p}'s house topics.</li>"
            )
    intro = (
        "<p class='pred'>BNN karmic headings are metaphorical - reflective colour, not literal memory.</p>"
    )
    if not bullets:
        return intro
    return intro + "<ul>" + "".join(bullets[:5]) + "</ul>"


def human_past_slice(ch: "BnnChart", bt: "BnnTiming") -> str:
    md = bt.cur_md
    if not md:
        return ""
    parts = [
        f"<p class='pred'><strong>{md.get('md_lord', '-')} mahadasha (from {fmt_date(md.get('start'))}):</strong> "
        f"major chapter coloured by {md.get('md_lord', '-')} in house {ch.h(md.get('md_lord', '')) if md.get('md_lord') in ch.planets else '-'}.</p>"
    ]
    today = date.today()
    recent = []
    for w in bt.antar_windows():
        if w["end"] < today:
            recent.append(w)
    for w in recent[-2:]:
        parts.append(
            f"<p class='pred'><strong>{w['md']}-{w['lord']} antar</strong> "
            f"({fmt_date(w['start'].isoformat())} - {fmt_date(w['end'].isoformat())}): "
            f"{antar_unload(ch, w['lord'])}</p>"
        )
    cur = bt.current_antar()
    if cur.get("ad_lord"):
        parts.append(
            f"<p class='pred'><strong>Handover now:</strong> {cur['ad_lord']} antar until "
            f"{fmt_date(cur.get('end'))} - {antar_unload(ch, cur['ad_lord'])}</p>"
        )
    return "<div class='callout-past'>" + "".join(parts) + "</div>"


def human_dasha(ch: "BnnChart", bt: "BnnTiming") -> str:
    md = bt.cur_md
    if not md:
        return "Dasha dates not parsed from extract."
    md_lord = md.get("md_lord", "")
    parts = [
        f"Since {fmt_date(md.get('start'))} you are in {md_lord} mahadasha until {fmt_date(md.get('end'))} - "
        f"{antar_chart_note(ch, md_lord)}.",
    ]
    cur = bt.current_antar()
    if cur.get("ad_lord"):
        parts.append(
            f"{cur['ad_lord']} antar until {fmt_date(cur.get('end'))}: {antar_unload(ch, cur['ad_lord'])}"
        )
    ven = _venus_window(bt)
    if ven:
        parts.append(
            f"Venus antar {fmt_date(ven['start'].isoformat())} - {fmt_date(ven['end'].isoformat())}: "
            f"{antar_unload(ch, 'Venus')}"
        )
    return " ".join(parts)


def human_timing_table(ch: "BnnChart", bt: "BnnTiming") -> str:
    rows = []
    today = date.today()
    for w in bt.antar_windows():
        if w["end"] < today and w["status"] != "current":
            continue
        lord = w["lord"]
        start = fmt_date(w["start"].isoformat())
        end = fmt_date(w["end"].isoformat())
        activate = antar_chart_note(ch, lord)
        unload = antar_unload(ch, lord)
        label = "active now" if w["start"] <= today < w["end"] else ""
        if w["end"] < today:
            label = "recent"
        rows.append(
            f"<tr><td><strong>{w['md']}-{lord}</strong>{(' (' + label + ')') if label else ''}</td>"
            f"<td>{start} - {end}</td><td>{esc(activate)}</td><td>{esc(unload)}</td></tr>"
        )
        if len(rows) >= 5:
            break
    if not rows:
        return ""
    return (
        "<h1>Next dasha windows (Vimshottari + BNN)</h1>"
        "<p class='pred'>Antardasha dates from your extract - cross-check in your software.</p>"
        "<table class='time'><tr><th>Phase</th><th>Window</th><th>Chart activation</th>"
        "<th>BNN-style focus</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def human_remedies(ch: "BnnChart", bt: "BnnTiming") -> str:
    items = []
    cur = bt.current_antar()
    if cur.get("ad_lord"):
        items.append(
            f"Honour the running {cur['ad_lord']} antar until {fmt_date(cur.get('end'))}: "
            f"{antar_unload(ch, cur['ad_lord'])}"
        )
    for p, v in ch.planets.items():
        if v["dignity"] == "debilitated" and p in ("Mercury", "Jupiter", "Venus", "Saturn", "Mars"):
            items.append(f"{p} debilitated: steady planet-day discipline and ethical conduct in house {v['house']} themes.")
    items.append("Keep agreements written - conduct protects luck more than fear rituals.")
    return " ".join(items[:4])


def antardasha_card(ch: "BnnChart", lord: str, start: date, end: date, label: str = "") -> str:
    suffix = f" ({label})" if label else ""
    body = antar_unload(ch, lord)
    return (
        f"<strong>{fmt_date(start.isoformat())} - {fmt_date(end.isoformat())}</strong> "
        f"{lord} antardasha{suffix}. {body}"
    )
