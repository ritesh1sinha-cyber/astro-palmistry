#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KP client prose - chart-generic, book logic under the hood."""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from kp_book_data import career_nature, health_csl_verdict, humanize_kp, links_verdict
from kp_chart import fmt
from kp_chart_text import (
    antar_focus,
    csl_row,
    house_verdict,
    intro_stack,
    planet_voice,
    praty_focus,
    ruling_summary,
    sig_phrase,
    verdict_phrase,
)

if TYPE_CHECKING:
    from kp_chart import KPChart


def _venus_antar(kp: "KPChart"):
    return next((w for w in kp.antar_windows() if w["lord"] == "Venus" and w["end"] > date.today()), None)


def human_intro(kp: "KPChart") -> str:
    return intro_stack(kp)


def human_now_callout(kp: "KPChart") -> str:
    cur_a = kp.current_antar()
    cur_p = kp.current_pratyantar()
    if not cur_a:
        return ""
    maha = (kp.maha or {}).get("lord", "Mahadasha")
    today = date.today()
    bits = [
        f"<strong>Report date {today.strftime('%d %b %Y').lstrip('0')}:</strong> "
        f"You are in <strong>{maha} mahadasha - {cur_a['lord']} antar</strong> until {fmt(cur_a['end'])}."
    ]
    if cur_p:
        bits.append(f" <strong>{cur_p['lord']} pratyantar</strong> until {fmt(cur_p['end'])}.")
    bits.append(f" {humanize_kp(antar_focus(kp, cur_a['lord']))}")
    if cur_p.get("lord"):
        bits.append(humanize_kp(praty_focus(kp, cur_p["lord"])))
    return f'<div class="callout-time"><p class="pred" style="margin:0;">{"".join(bits)}</p></div>'


def human_chart_wiring(kp: "KPChart") -> str:
    c1, n1, _, _ = csl_row(kp, 1)
    c7, n7, _, _ = csl_row(kp, 7)
    c10, n10, s10, _ = csl_row(kp, 10)
    n10s = len(kp.signif.get(10, []))
    heavy = (
        f"Career house is unusually active ({n10s} significators) - job events trigger more often. "
        if n10s >= 4 else ""
    )
    return (
        "<p class='pred'>In KP, each house cusp has a <strong>sub lord</strong> that acts like a yes/no switch. "
        f"Your map is {heavy}Partnership and profession both need the right dasha season to ripen.</p>"
        f"<p class='pred'><strong>Rising CSL {c1} (star {n1}):</strong> {planet_voice(c1)} threads into identity and reputation.</p>"
        f"<p class='pred'><strong>Partnership CSL {c7} (star {n7}):</strong> marriage reads as a growth curriculum, not a side plot.</p>"
        f"<p class='pred'><strong>Profession CSL {c10} (star {n10}, {s10}):</strong> {planet_voice(c10)}.</p>"
    )


def human_personality(kp: "KPChart") -> tuple[str, str]:
    sub, nak, sign, _ = csl_row(kp, 1)
    parts = [
        f"Self-projection carries {planet_voice(sub)} even in casual speech.",
        f"Lagna star/sub ({nak} / {sub}) on {sign} sets temperament.",
    ]
    if kp.csl(10) == sub:
        parts.append("Same planet on 1st and 10th cusps - public role and identity are tightly coupled.")
    ruling = ruling_summary(kp)
    if ruling:
        parts.append(ruling)
    return " ".join(parts), f"CSL-1 {sub}, star {nak}"


def human_marriage(kp: "KPChart") -> tuple[str, str]:
    sub, nak, sign, _ = csl_row(kp, 7)
    _, v, hit_f, hit_u = house_verdict(kp, 7, "marriage")
    parts = [
        f"Partner profile blends {planet_voice(nak)} with {planet_voice(sub)} (CSL-7 {sub}, star {nak} on {sign}).",
        f"KP verdict: {verdict_phrase(v)}.",
    ]
    if hit_f:
        parts.append(f"Favourable links on houses {', '.join(str(h) for h in sorted(hit_f))}.")
    if hit_u:
        parts.append(f"Test links on houses {', '.join(str(h) for h in sorted(hit_u))} - patience in Ketu/Saturn slices.")
    sig7 = kp.signif.get(7, [])
    if sig7:
        parts.append(f"7th significators: {', '.join(sig7)}.")
    ven = _venus_antar(kp)
    if ven:
        parts.append(f"Partnership-friendly band: Venus antar {fmt(ven['start'])} - {fmt(ven['end'])}.")
    return " ".join(parts), f"CSL-7 {sub}, star {nak}"


def human_career(kp: "KPChart") -> tuple[str, str, str]:
    sub, nak, sign, _ = csl_row(kp, 10)
    _, v, hit_f, _ = house_verdict(kp, 10, "career")
    parts = [
        f"Career results tie to {sub} cycles - {planet_voice(sub)} (10th cusp on {sign}, star {nak}).",
        f"KP career verdict: {verdict_phrase(v)}.",
        sig_phrase(kp, 10) + ".",
    ]
    nature = career_nature(kp.links(sub))
    if nature:
        parts.append(humanize_kp(nature[0]))
    if len(kp.signif.get(10, [])) >= 4:
        parts.append("Heavy 10th significator mass - built for visible professional life when dasha cooperates.")
    if hit_f:
        parts.append(f"Supportive links: houses {', '.join(str(h) for h in sorted(hit_f))}.")
    ven = _venus_antar(kp)
    if ven:
        parts.append(f"Polish interviews and promotions in Venus antar {fmt(ven['start'])} - {fmt(ven['end'])}.")
    from kp_foundation import career_highlight_html
    return " ".join(parts), f"CSL-10 {sub}, star {nak}", career_highlight_html(kp)


def human_health(kp: "KPChart") -> tuple[str, str]:
    c6, c8 = kp.csl(6), kp.csl(8)
    book_line = health_csl_verdict(kp.links(c6), kp.links(c8))
    parts = []
    if book_line:
        parts.append(book_line)
    if c6 == kp.csl(5):
        parts.append("Venus on both 5th and 6th cusps - watch comfort-linked health habits.")
    parts.append("Prevention beats ignore-then-crisis; not a medical diagnosis.")
    return " ".join(parts), f"CSL-6 {c6}, CSL-8 {c8}"


def human_children(kp: "KPChart") -> tuple[str, str]:
    sub, nak, sign, _ = csl_row(kp, 5)
    sig5 = kp.signif.get(5, [])
    parts = [
        f"Romance, children, and creativity share {planet_voice(sub)} (CSL-5 {sub} on {sign}, star {nak}).",
    ]
    if len(sig5) >= 4:
        parts.append(f"Busy 5th: {', '.join(sig5)} - many routes to children or creative output.")
    if "Saturn" in sig5:
        parts.append("Saturn co-signifies delay until responsibility feels settled.")
    if "Ketu" in sig5:
        parts.append("Ketu on the lane can mean delay, one turning point, or spiritual approach to progeny.")
    return " ".join(parts), f"CSL-5 {sub}, star {nak}"


def human_travel(kp: "KPChart") -> tuple[str, str]:
    c3, _, s3, _ = csl_row(kp, 3)
    c9, _, s9, _ = csl_row(kp, 9)
    c12 = kp.csl(12)
    if c3 == c9:
        parts = [f"Short and long travel both run through {c3} - duty-linked and scheduled ({s3}/{s9})."]
    else:
        parts = [
            f"Short travel CSL {c3} ({s3}) - {planet_voice(c3)}.",
            f"Long journey CSL {c9} ({s9}) - {planet_voice(c9)}.",
        ]
    if "Rahu" in kp.signif.get(9, []) + kp.signif.get(11, []):
        parts.append("Rahu on 9/11 keeps foreign or different-circle pull in timing.")
    if c12 == "Ketu":
        parts.append("12th cusp Ketu favours retreat abroad over restless tourism.")
    return " ".join(parts), f"CSL-3/9/12 {c3}/{c9}/{c12}"


def human_siblings(kp: "KPChart") -> tuple[str, str]:
    sub, _, sign, _ = csl_row(kp, 3)
    sig3 = kp.signif.get(3, [])
    parts = [f"Sibling and courage themes: CSL-3 {sub} on {sign} - {planet_voice(sub)}."]
    if sig3:
        parts.append(f"Significators: {', '.join(sig3)}.")
    return " ".join(parts), f"CSL-3 {sub}"


def human_parents(kp: "KPChart") -> tuple[str, str]:
    c4, _, s4, _ = csl_row(kp, 4)
    c9, _, s9, _ = csl_row(kp, 9)
    return (
        f"Mother/home CSL {c4} ({s4}) - {planet_voice(c4)}. "
        f"Father/guru line CSL {c9} ({s9}) - {planet_voice(c9)}.",
        f"CSL-4 {c4}, CSL-9 {c9}",
    )


def human_dasha(kp: "KPChart") -> str:
    m = kp.maha
    if not m:
        return "Dasha dates missing from the KP extract."
    lord = m.get("lord", "")
    cur = kp.current_antar()
    try:
        import impact as IMP
        md_line = IMP.dasha_impact(lord, end_pretty=fmt(m["end"]))
    except Exception:  # noqa: BLE001
        md_line = (f"Since {fmt(m['start'])} you are in {lord} mahadasha until "
                   f"{fmt(m['end'])} — {planet_voice(lord)} chapter.")
    lines = [md_line]
    if cur.get("lord"):
        lines.append(antar_focus(kp, cur["lord"]))
    ven = _venus_antar(kp)
    if ven:
        lines.append(f"Venus antar {fmt(ven['start'])} - {fmt(ven['end'])}: partnership and polish band.")
    return " ".join(lines)


def human_pratyantar(kp: "KPChart") -> str:
    cur_a = kp.current_antar()
    cur_p = kp.current_pratyantar()
    if not cur_a:
        return ""
    parts = [f"Inside {cur_a['lord']} antar ({fmt(cur_a['start'])} - {fmt(cur_a['end'])})."]
    if cur_p.get("lord"):
        parts.append(praty_focus(kp, cur_p["lord"]))
    return " ".join(parts)


def human_timing_table(kp: "KPChart") -> str:
    rows = []
    today = date.today()
    maha = (kp.maha or {}).get("lord", "")
    for w in kp.antar_windows():
        if w["end"] < today:
            continue
        lord = w["lord"]
        label = "active now" if w["start"] <= today < w["end"] else ("recent" if w["end"] < today else "")
        read = antar_focus(kp, lord)
        rows.append(
            f"<tr><td><strong>{maha}-{lord}</strong>{(' (' + label + ')') if label else ''}</td>"
            f"<td>{fmt(w['start'])} - {fmt(w['end'])}</td><td>{read}</td></tr>"
        )
        if len(rows) >= 5:
            break
    if not rows:
        return ""
    return (
        "<h1>Next ~24 months - how KP timing unloads</h1>"
        "<p class='pred'>Antardasha windows from <strong>KP Vimshottari</strong> pages only.</p>"
        "<table class='kp'><tr><th>Phase</th><th>Window</th><th>What it means for you</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def human_remedies(kp: "KPChart") -> str:
    cur = kp.current_antar()
    pr = kp.current_pratyantar()
    items = []
    if cur.get("lord"):
        items.append(f"During {cur['lord']} antar until {fmt(cur['end'])}: {antar_focus(kp, cur['lord'])}")
    if pr.get("lord"):
        items.append(f"Pratyantar {pr['lord']}: pace weekly decisions; avoid impulse contracts.")
    items.append("Keep agreements written - conduct protects luck more than fear rituals.")
    return " ".join(items[:3])


def antardasha_card(kp: "KPChart", lord: str, start, end, label: str = "") -> str:
    suffix = f" ({label})" if label else ""
    return (
        f"<strong>{fmt(start)} - {fmt(end)}</strong> {lord} antardasha{suffix}. "
        f"{antar_focus(kp, lord)}"
    )
