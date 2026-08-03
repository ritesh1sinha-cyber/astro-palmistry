#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BNN foundation sections from the legacy gold report (chart-generic)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from bnn_chart_text import (
    antar_chart_note,
    book_clause,
    book_planet_sign,
    dignity_phrase,
    esc,
    karaka_planet,
    lord_line,
    placement_fact,
    stellium_houses,
    traffic_class,
)
from bnn_chart import lord_verdict

if TYPE_CHECKING:
    from bnn_chart import BnnChart, BnnTiming


def _rule(text: str) -> str:
    return f'<div class="bnn-rule">BNN: {esc(text)}</div>'


def foundation_html(ch: "BnnChart") -> str:
    ll = ch.lord_of_house(1)
    ll_h = ch.h(ll) if ll in ch.planets else 0
    ll_dig = dignity_phrase(ch.dig(ll)) if ll in ch.planets else ""
    ll_clause = book_planet_sign(ch, ll, "positive" if ch.dig(ll) in ("exalted", "own_sign", "moolatrikona") else "neutral")

    left = [
        "<h2>Lagna and its lord</h2>",
        _rule("Lagna lord's sign and house set the primary life theme."),
        f'<p class="pred"><strong>Lagna {esc(ch.lagna)}</strong> - lord <strong>{esc(ll)}</strong> '
        f'{esc(ll_dig)} in the {ll_h}th ({esc(ch.sign(ll)) if ll in ch.planets else "-"})</p>',
    ]
    if ll_clause:
        left.append(f'<p class="pred">{esc(ll_clause)}</p>')
    if ll_h in (1, 4, 5, 9, 10, 11) and ch.dig(ll) in ("exalted", "own_sign", "moolatrikona"):
        left.append(
            '<p class="pred good-note">When the lagna lord is strong in a kendra or trikona, '
            "authority and dharmic effort tend to pay over time.</p>"
        )

    right_parts = []
    for house_n, planets in stellium_houses(ch):
        rows = "".join(
            f"<tr><td>{esc(p)}</td><td>{esc(book_planet_sign(ch, p) or placement_fact(ch, p))}</td></tr>"
            for p in planets
        )
        right_parts.append(
            f"<h2>{house_n}th-house stellium ({len(planets)} planets)</h2>"
            + _rule("Multiple planets in one house multiply that life theme - several domains compete in the same arena.")
            + f"<table class='facts'><tr><th>Planet</th><th>BNN contribution</th></tr>{rows}</table>"
        )
    if not right_parts:
        amk = karaka_planet(ch, "Amatyakarak")
        if amk:
            right_parts.append(
                f"<h2>Career karaka (Amatyakarak)</h2><p class='pred'>{esc(placement_fact(ch, amk))}</p>"
                + (f"<p class='pred'>{esc(book_planet_sign(ch, amk))}</p>" if book_planet_sign(ch, amk) else "")
            )

    right_col = "".join(right_parts) if right_parts else "<p class='fine'>No three-planet stellium in D1.</p>"
    grid = (
        "<div class='grid2'>"
        f"<div>{''.join(left)}</div>"
        f"<div>{right_col}</div>"
        "</div>"
    )
    return f"<h1>Chart foundation</h1>{grid}"


def personality_table_html(ch: "BnnChart") -> str:
    rows = []
    moon = ch.planets.get("Moon", {})
    if moon:
        nak = f"{moon.get('nakshatra', '')} Pada {moon.get('pada', '')}".strip()
        moon_txt = book_planet_sign(ch, "Moon") or (
            f"Moon in the {moon.get('house')}th colours emotion and habit; "
            f"you need this house theme to feel settled."
        )
        rows.append(("Nakshatra / Moon", nak, moon_txt))

    rows.append((
        "Lagna",
        ch.lagna,
        f"{ch.lagna} rising sets temperament and first impression; lagna lord {ch.lord_of_house(1)} "
        f"steers how you initiate projects.",
    ))

    ak = ch.atmakaraka() or karaka_planet(ch, "Atmakarak")
    if ak and ak in ch.planets:
        rows.append(("Atmakaraka", ak, book_planet_sign(ch, ak) or placement_fact(ch, ak)))

    ll = ch.lord_of_house(1)
    if ll in ch.planets:
        rows.append((
            f"Lagna lord {ll}",
            f"{ch.sign(ll)} - house {ch.h(ll)}",
            book_planet_sign(ch, ll) or f"{ll} as lagna lord in the {ch.h(ll)}th defines core effort and stamina.",
        ))

    for node in ("Rahu", "Ketu"):
        if node in ch.planets:
            rows.append((
                node,
                f"{ch.sign(node)} - house {ch.h(node)}",
                book_planet_sign(ch, node) or placement_fact(ch, node),
            ))

    body = "".join(
        f"<tr><td><strong>{esc(a)}</strong></td><td>{esc(b)}</td><td>{esc(c)}</td></tr>"
        for a, b, c in rows
    )
    return (
        "<h1>Core personality (BNN)</h1>"
        + _rule("Lagna, Moon, Atmakaraka, and nodal tenants describe temperament before dasha timing.")
        + f"<table class='facts'><tr><th>Factor</th><th>Placement</th><th>BNN reading</th></tr>{body}</table>"
    )


def education_html(ch: "BnnChart") -> str:
    h4 = ch.house_sign(4)
    h5l = ch.lord_of_house(5)
    h9 = ch.house_sign(9)
    clauses = book_clause(
        book_planet_sign(ch, "Mercury", "positive"),
        book_planet_sign(ch, h5l) if h5l in ch.planets else "",
        book_planet_sign(ch, ch.lord_of_house(9)) if ch.lord_of_house(9) in ch.planets else "",
        max_n=4,
    )
    tenants_4 = ch.in_house(4)
    tenant_note = ""
    if tenants_4:
        tenant_note = (
            f"<p class='pred'>Planets in the 4th ({', '.join(tenants_4)}): "
            "primary schooling and home atmosphere carry their combined tone.</p>"
        )
    intel = (
        f"<p class='pred'><strong>Intelligence (5th lord {h5l}):</strong> {esc(lord_line(ch, 5))}</p>"
        if h5l in ch.planets
        else ""
    )
    higher = (
        f"<p class='pred'><strong>Higher learning (9th {h9}):</strong> {esc(lord_line(ch, 9))}</p>"
    )
    bullets = "".join(f"<li>{esc(c)}</li>" for c in clauses)
    return (
        "<h1>Education</h1>"
        + _rule("4th house = foundational schooling; 5th lord = intelligence; 9th = higher education; Mercury = academic skill.")
        + "<div class='grid2'>"
        + f"<div><p class='pred'><strong>Primary (4th {h4}):</strong> {esc(lord_line(ch, 4))}</p>{tenant_note}</div>"
        + f"<div>{intel}{higher}</div>"
        + "</div>"
        + (f"<ul>{bullets}</ul>" if bullets else "")
    )


def wealth_property_html(ch: "BnnChart") -> str:
    l2 = ch.lord_of_house(2)
    l11 = ch.lord_of_house(11)
    l4 = ch.lord_of_house(4)
    wealth_bits = [
        f"<p class='pred'><strong>Wealth axis:</strong> 2nd lord {l2}, 11th lord {l11}.</p>",
        f"<p class='pred'>{esc(lord_line(ch, 2))}</p>",
        f"<p class='pred'>{esc(lord_line(ch, 11))}</p>",
    ]
    if l2 == l11 and l2 in ch.planets:
        wealth_bits.append(
            "<p class='pred good-note'>When the same planet rules both wealth and gains, career and income "
            "loop together - effort in the 10th-house theme feeds both.</p>"
        )
    ven = book_planet_sign(ch, "Venus", "positive")
    if ven:
        wealth_bits.append(f"<p class='pred'>{esc(ven)}</p>")

    prop_bits = [
        f"<p class='pred'><strong>Property (4th {ch.house_sign(4)}):</strong> lord {l4}.</p>",
        f"<p class='pred'>{esc(lord_line(ch, 4))}</p>",
    ]
    for p in ch.in_house(4):
        prop_bits.append(f"<p class='pred'>{esc(placement_fact(ch, p))}</p>")

    return (
        "<h1>Wealth and property</h1>"
        + _rule("2nd and 11th lords show money flow; 4th house and its lord show property and emotional home.")
        + "<div class='grid2'>"
        + f"<div><h2>Wealth</h2>{''.join(wealth_bits)}</div>"
        + f"<div><h2>Property</h2>{''.join(prop_bits)}</div>"
        + "</div>"
    )


def marriage_timing_html(ch: "BnnChart", bt: "BnnTiming") -> str:
    l7 = ch.lord_of_house(7)
    dk = karaka_planet(ch, "Darakaraka")
    watch = {l7, "Venus", dk} - {""}
    items = []
    for w in bt.antar_windows():
        if w["lord"] in watch:
            items.append(
                f"<li><strong>{w['md']}-{w['lord']}</strong>: "
                f"{w['start'].strftime('%d %b %Y').lstrip('0')} - {w['end'].strftime('%d %b %Y').lstrip('0')} "
                f"- marriage-sensitive sub-period ({antar_chart_note(ch, w['lord'])}).</li>"
            )
        if len(items) >= 6:
            break
    if not items:
        return ""
    return (
        "<h2>Marriage timing windows (extract dates)</h2>"
        + _rule("Marriage often ripens in periods of the 7th lord, Venus, or Darakaraka.")
        + f"<ul>{''.join(items)}</ul>"
        + '<p class="fine">Calibration against your actual marriage date improves confidence.</p>'
    )


def career_verdict_html(ch: "BnnChart") -> str:
    tone = lord_verdict(ch, ch.lord_of_house(10))
    amk = karaka_planet(ch, "Amatyakarak")
    bits = [lord_line(ch, 10)]
    if amk:
        bits.append(f"Amatyakarak {amk}: {placement_fact(ch, amk)}")
    for p in ch.in_house(10):
        bits.append(book_planet_sign(ch, p) or placement_fact(ch, p))
    from bnn_book_data import load_bnn_book, lookup_profession_sign, humanize_bnn
    prof = humanize_bnn(lookup_profession_sign(load_bnn_book(), ch.house_sign(10)))
    if prof:
        bits.append(prof)
    cls = traffic_class(tone)
    return (
        f'<div class="{cls}"><strong>BNN career signature</strong><br>'
        + "<br>".join(esc(x) for x in bits[:5])
        + "</div>"
    )