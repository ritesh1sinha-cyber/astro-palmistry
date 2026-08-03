#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KP foundation blocks from legacy gold report (chart-generic)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from kp_book_data import domain_rules
from kp_chart_text import esc, house_verdict, planet_voice, sig_phrase, verdict_phrase

if TYPE_CHECKING:
    from kp_chart import KPChart

KEY_HOUSES = (1, 5, 6, 7, 10, 11)


def _rule(text: str) -> str:
    return f'<div class="kp-rule">KP: {esc(text)}</div>'


def methodology_html() -> str:
    return (
        "<p class='lead'>KP reads each <strong>bhava from its cusp</strong>. The "
        "<strong>cuspal sub lord (CSL)</strong> is the yes/no switch for that house. Planet results refine through "
        "<strong>star lord</strong> and <strong>sub lord</strong>. Significators show which planets co-relate to "
        "which houses; planet signification shows which houses each planet links.</p>"
    )


def lahiri_warning_html() -> str:
    return (
        '<div class="callout"><strong>Important:</strong> Earlier PDF pages may use <strong>Lahiri</strong> with '
        "different Vimshottari cuts than the <strong>K.P. New</strong> block. "
        "<strong>This report uses only KP-section tables</strong> for timing. "
        "Do not mix Lahiri antar dates with KP pratyantar without reconciling in software.</div>"
    )


def ruling_table_html(kp: "KPChart") -> str:
    rows = []
    for ref, label in (("Lagna", "Lagna"), ("Moon", "Moon"), ("Day Lord", "Day lord")):
        chain = kp.ruling.get(ref, [])
        if not chain:
            continue
        if len(chain) >= 3:
            rows.append(
                f"<tr><td>{label}</td><td>{chain[0]}</td><td>{chain[1]}</td><td>{chain[2]}</td></tr>"
            )
        else:
            rows.append(
                f"<tr><td>{label}</td><td colspan='3'>{', '.join(chain)}</td></tr>"
            )
    if not rows:
        return "<p class='fine'>Ruling planet chain not parsed from extract.</p>"
    return (
        "<h1>Ruling planets (extract)</h1>"
        + "<table class='kp'><tr><th>Reference</th><th>Rasi lord</th><th>Nak lord</th><th>Sub lord</th></tr>"
        + "".join(rows)
        + "</table>"
        + "<p class='note'>KP uses ruling planets in horary; natal reading here leans on <strong>cusp subs</strong> + <strong>dasha</strong>.</p>"
    )


def cusp_promise_grid_html(kp: "KPChart") -> str:
    rows = []
    for h in KEY_HOUSES:
        sub, v, hit_f, hit_u = house_verdict(kp, h)
        topic = {
            1: "identity", 5: "children/creativity", 6: "health", 7: "marriage",
            10: "career", 11: "gains",
        }[h]
        fav = ", ".join(str(x) for x in sorted(hit_f)) or "-"
        unf = ", ".join(str(x) for x in sorted(hit_u)) or "-"
        rows.append(
            f"<tr><td>{h}</td><td><strong>{esc(sub)}</strong></td><td>{esc(topic)}</td>"
            f"<td>{esc(verdict_phrase(v))}</td><td>{fav}</td><td>{unf}</td></tr>"
        )
    return (
        "<h1>House promise grid (CSL links)</h1>"
        + _rule("CSL planet's house links are checked against favourable and unfavourable house sets per KP event groups.")
        + "<table class='kp'><tr><th>H</th><th>CSL</th><th>Topic</th><th>Verdict</th><th>Fav links</th><th>Unfav links</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def key_cusps_table_html(kp: "KPChart") -> str:
    rows = []
    for h in (1, 7, 10, 11):
        c = kp.cusp(h)
        if not c:
            continue
        rows.append(
            f"<tr><td>{h}</td><td>{c.get('degree','')}</td><td>{c.get('sign','')}</td>"
            f"<td>{c.get('nak','')}</td><td><strong>{c.get('sub','')}</strong></td>"
            f"<td>{sig_phrase(kp, h)}</td></tr>"
        )
    body = "".join(rows)
    if not body:
        return ""
    return (
        "<h1>Key cusps at a glance</h1>"
        + "<table class='kp'><tr><th>H</th><th>Degree</th><th>Sign</th><th>Nak</th><th>CSL</th><th>Significators</th></tr>"
        + body
        + "</table>"
    )


def domain_rules_html(domain: str, title: str) -> str:
    rules = domain_rules(domain, max_n=2)
    if not rules:
        return ""
    items = "".join(f"<li>{esc(humanize_rule(r))}</li>" for r in rules)
    return f"<h2>{esc(title)}</h2><ul>{items}</ul>"


def humanize_rule(text: str) -> str:
    from kp_book_data import humanize_kp
    return humanize_kp(text)


def career_highlight_html(kp: "KPChart") -> str:
    sub, v, _, _ = house_verdict(kp, 10, "career")
    sig = sig_phrase(kp, 10)
    cls = "traffic-green" if v == "promised" else ("traffic-amber" if v == "denied" else "traffic-neutral")
    return (
        f'<div class="{cls}"><strong>10th cusp CSL {esc(sub)}</strong> - {esc(verdict_phrase(v))}. '
        f"{esc(sig)}. Career tone: {esc(planet_voice(sub))}.</div>"
    )
