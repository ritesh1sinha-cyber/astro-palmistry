#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared chart-generic KP phrasing (cusp subs, links, dasha)."""
from __future__ import annotations

import html
from typing import TYPE_CHECKING

from kp_book_data import career_nature, csl_planet_note, humanize_kp, links_verdict
from kp_chart import HOUSE_TOPICS, fmt

if TYPE_CHECKING:
    from kp_chart import KPChart

DOMAIN_FOR_HOUSE = {
    5: "children",
    6: "health",
    7: "marriage",
    10: "career",
    11: "career",
}


def esc(s: str) -> str:
    return html.escape(str(s))


def csl_row(kp: "KPChart", h: int) -> tuple[str, str, str, str]:
    c = kp.cusp(h)
    return c.get("sub", ""), c.get("nak", ""), c.get("sign", ""), c.get("degree", "")


def planet_voice(planet: str, *, short: bool = True) -> str:
    note = csl_planet_note(planet)
    if not note:
        return f"{planet}-ruled themes"
    if short:
        return note.split(",")[0].strip().rstrip(".").lower()
    return note.rstrip(".").lower()


def verdict_phrase(verdict: str) -> str:
    return {
        "promised": "promised in the KP sense",
        "denied": "delayed or tested until supportive dasha runs",
        "mixed": "mixed - needs the right dasha season",
        "weak": "weak unless dasha activates significators",
    }.get(verdict, "neutral")


def house_verdict(kp: "KPChart", house: int, domain: str | None = None) -> tuple[str, str, set[int], set[int]]:
    sub = kp.csl(house)
    dom = domain or DOMAIN_FOR_HOUSE.get(house, "career")
    v, hit_f, hit_u = links_verdict(kp.links(sub), dom)
    return sub, v, hit_f, hit_u


def antar_focus(kp: "KPChart", lord: str) -> str:
    if not lord:
        return "Keep routines steady in this slice."
    links = sorted(kp.links(lord))
    houses = ", ".join(str(h) for h in links[:4]) if links else "its natal houses"
    voice = planet_voice(lord)
    bits = [f"{lord} antardasha activates houses {houses} - {voice}."]
    nature = career_nature(set(links))
    if nature:
        bits.append(humanize_kp(nature[0]))
    for h in (7, 10, 5):
        if h in links:
            bits.append(f"House {h} ({HOUSE_TOPICS[h]}) gets louder.")
    return " ".join(bits[:3])


def praty_focus(kp: "KPChart", lord: str) -> str:
    if not lord:
        return ""
    links = sorted(kp.links(lord))[:4]
    return (
        f"{lord} pratyantar colours the next few weeks - {planet_voice(lord)}. "
        f"Linked houses: {', '.join(str(h) for h in links) or 'see planet table'}."
    )


def ruling_summary(kp: "KPChart") -> str:
    parts = []
    lag = kp.ruling.get("Lagna", [])
    moon = kp.ruling.get("Moon", [])
    day = kp.ruling.get("Day Lord", [])
    if len(lag) >= 3:
        parts.append(
            f"Lagna ruling chain {lag[0]}/{lag[1]}/{lag[2]} colours how you start conversations and projects."
        )
    elif lag:
        parts.append(f"Lagna ruling planets: {', '.join(lag)}.")
    if len(moon) >= 3:
        parts.append(
            f"Moon line {moon[0]}/{moon[1]}/{moon[2]} steers emotional decisions - cool down before property or family deals."
        )
    if day:
        parts.append(f"Day lord: {', '.join(day)}.")
    return " ".join(parts)


def sig_phrase(kp: "KPChart", house: int) -> str:
    sig = kp.signif.get(house, [])
    if not sig:
        return "no strong significator cluster"
    if len(sig) >= 4:
        return f"busy house ({len(sig)} significators: {', '.join(sig[:4])}...)"
    return f"significators {', '.join(sig)}"


def intro_stack(kp: "KPChart") -> str:
    c1, n1, s1, _ = csl_row(kp, 1)
    maha = (kp.maha or {}).get("lord", "")
    cur = kp.current_antar()
    pr = kp.current_pratyantar()
    parts = [
        f"You read as a {kp.lagna} chart with {c1} on the rising cusp - {planet_voice(c1)} colours first impressions.",
    ]
    if maha and cur.get("lord"):
        parts.append(
            f"Running clock: {maha} mahadasha, {cur['lord']} antar until {fmt(cur['end'])}."
        )
        parts.append(antar_focus(kp, cur["lord"]))
    if pr.get("lord"):
        parts.append(praty_focus(kp, pr["lord"]))
    ruling = ruling_summary(kp)
    if ruling:
        parts.append(ruling)
    return " ".join(parts)
