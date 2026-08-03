#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Goel Navamsha - client-facing predictions only (scoring in background)."""
from __future__ import annotations

import html
import re
from typing import Any

from goel_marriage_life_prose import marriage_life_client_cards, marriage_age_paragraph
from goel_marriage_timing import timing_client_paragraph
from goel_navamsha_confluence import build_navamsha_confluence

CLIENT_TITLES = {
    "marriage_promise": "Marriage",
    "marriage_quality": "Marriage over the years",
    "marriage_strain": "Partnership stress points",
    "d1_d9_improvement": "Life improves with time",
    "spiritual_dharma": "Spiritual path",
    "partnership_foreign": "Spouse / partner background",
    "marriage_timing": "Commitment timing",
    "beeja_strength": "Dasha results",
    "vish_period_caution": "Sensitive periods",
    "multiple_relations": "Relationships",
}


def _e(s: str) -> str:
    return html.escape(str(s))


def _join_names(planets: list[str]) -> str:
    if not planets:
        return ""
    if len(planets) == 1:
        return planets[0]
    if len(planets) == 2:
        return f"{planets[0]} and {planets[1]}"
    return ", ".join(planets[:-1]) + f", and {planets[-1]}"


def _hero_paragraph(analysis: dict[str, Any]) -> str:
    d9 = analysis.get("d9_lagna", "")
    d1 = analysis.get("d1_lagna", "")
    venus = analysis.get("d9_enriched", {}).get("Venus", {})
    lines = [
        f"Your navamsha chart (how life promises ripen) has {d9} rising over {d1} at birth."
    ]
    if venus.get("d9_dignity") == "exalted":
        lines.append(
            "Venus is exalted in both the birth chart and navamsha - Goel reads this as "
            "marriage and deep comfort strengthening with age, not fading after the wedding."
        )
    elif analysis.get("trajectory"):
        lines.append(
            "Several planets look stronger in navamsha than in the birth chart - "
            "results often improve in the second half of life."
        )
    return " ".join(lines)


def _narrative(theme_id: str, analysis: dict[str, Any]) -> str:
    d9 = analysis.get("d9_lagna", "")
    houses = analysis.get("d9_houses", {})
    enriched = analysis.get("d9_enriched", {})
    venus = enriched.get("Venus", {})
    jupiter = enriched.get("Jupiter", {})
    h1 = houses.get(1, [])
    lord7 = analysis.get("lord7_d9", "")
    l7 = enriched.get(lord7, {})
    windows = analysis.get("marriage_windows", [])
    vish = analysis.get("vish_dasha", [])
    dk = analysis.get("darakaraka", "")
    dk_h = enriched.get(dk, {}).get("d9_house", 0) if dk else 0
    trajectory = analysis.get("trajectory", [])
    beeja = analysis.get("beeja_strong", [])
    spiritual = analysis.get("spiritual_signals", [])
    multiple = analysis.get("multiple_signals", [])

    if theme_id == "marriage_promise":
        parts = ["You are built for marriage."]
        if h1:
            parts.append(
                f"Navamsha lagna {d9} holds {_join_names(h1)} - a strong inner drive toward union."
            )
        if not houses.get(7):
            parts.append(
                f"The navamsha seventh house is open; its lord {lord7} "
                f"in the {l7.get('d9_house', '?')}th house carries the promise."
            )
        if venus.get("d1_dignity") == "exalted":
            parts.append("Venus is already exalted in the birth chart, so partnership is a life theme, not a side note.")
        return " ".join(parts)

    if theme_id == "marriage_quality":
        parts = []
        if venus.get("d9_dignity") == "exalted":
            parts.append(
                "Your marriage matures into genuine loyalty and comfort. "
                "Venus is exalted in the birth chart (10th house) and again in navamsha Pisces - "
                "navamsha is the final tone: affection deepens after the wedding, "
                "and the spouse supports your public name and status."
            )
        else:
            parts.append(
                "Partnership steadies over time. Navamsha shows the long-term marriage tone, "
                "and your chart supports a durable bond when trust is nurtured."
            )
        if trajectory:
            parts.append(
                "Mercury looks debilitated in the career chart but strong in navamsha Virgo - "
                "communication with your partner becomes clearer and more honest in mature years."
            )
        return " ".join(parts)

    if theme_id == "marriage_strain":
        parts = [
            "Domestic friction can surface when work stress spills into home life."
        ]
        if l7.get("d9_house") in (6, 8, 12):
            parts.append(
                f"Navamsha seventh lord {lord7} sits in a demanding house - "
                "patience and routine check-ins prevent small issues from becoming exits."
            )
        if houses.get(4):
            parts.append(
                f"Fourth house holds {_join_names(houses[4])}; protect home peace with fixed rituals and calm speech."
            )
        return " ".join(parts)

    if theme_id == "d1_d9_improvement":
        parts = [
            "What looks difficult in the birth chart often delivers better results after marriage or mid-life."
        ]
        for t in trajectory[:2]:
            parts.append(t.replace("D1 debil -> D9 strong", "weak in birth chart but strong in navamsha") + ".")
        if any("vargottama" in f for f in analysis.get("flags", [])):
            parts.append("Mars is vargottama (same sign in both charts) - courage and initiative stay consistent through life.")
        return " ".join(parts)

    if theme_id == "spiritual_dharma":
        parts = ["Spiritual life grows alongside worldly duties."]
        if jupiter.get("d9_house") == 1:
            parts.append(
                "Jupiter sits in the navamsha ascendant - teachers, dharma study, or mentor figures shape your path."
            )
        if houses.get(9):
            parts.append(
                f"Ninth house holds {_join_names(houses[9])} - pilgrimage, foreign teachers, or unconventional faith threads appear."
            )
        for s in spiritual:
            if "Jupiter + Ketu" in s:
                parts.append("Jupiter and Ketu together in navamsha deepen religious insight.")
                break
        parts.append("A steady weekly practice and respect for elders keep this constructive.")
        return " ".join(parts)

    if theme_id == "partnership_foreign":
        parts = []
        if venus.get("d9_house") == 12:
            parts.append(
                "Venus in navamsha twelfth often draws a spouse linked to another region, culture, or a private courtship."
            )
        if analysis.get("dk_foreign"):
            parts.append(analysis["dk_foreign"][0].split("(")[0].strip().rstrip(".") + ".")
        elif dk and dk_h in (9, 12):
            parts.append(
                f"Spouse significator {dk} sits in navamsha house {dk_h} - partner may come from outside your immediate circle."
            )
        return " ".join(parts) or "Partner may arrive from a different background or through travel-linked circumstances."

    if theme_id == "marriage_timing":
        mt = analysis.get("marriage_timing_detail", {})
        if mt:
            return timing_client_paragraph(mt)
        return _fallback_marriage_timing(analysis)

    if theme_id == "beeja_strength":
        n = len(beeja)
        return (
            f"{n} planets map into strong angles of your birth chart through navamsha - "
            "mahadasha of those grahas tends to deliver more reliably (Goel Beeja rule). "
            "Lean into Mercury and Venus periods for career and relationship milestones."
        )

    if theme_id == "vish_period_caution":
        if not vish:
            return ""
        cleaned = []
        for v in vish[:3]:
            v = re.sub(r"\s*\(Goel Ch\.\d+\)", "", v)
            m = re.match(r"(\w+)\s+dasha:\s*watch\s*(.+)", v, re.I)
            if m:
                cleaned.append(f"During {m.group(1)} periods, take extra care around {m.group(2).strip()}")
            else:
                cleaned.append(v)
        body = ". ".join(cleaned) + "."
        return (
            f"{body} Use simple remedies for those planets during their dasha; "
            "avoid reckless moves in those life areas at peak sub-periods."
        )

    if theme_id == "multiple_relations":
        parts = ["More than one serious attachment is possible in this map."]
        for m in multiple[:2]:
            parts.append(m.replace("Ch.4", "").strip().rstrip(".") + ".")
        parts.append("Clear values and Jupiter worship strengthen single-partner permanence.")
        return " ".join(parts)

    return ""


def _fallback_marriage_timing(analysis: dict[str, Any]) -> str:
    windows = analysis.get("marriage_windows", [])
    if not windows:
        return ""
    w = windows[0]
    return (
        f"Marriage activity peaks in {w['lord']} period {w['range']}. "
        "Confirm the month when Jupiter or Saturn activates your seventh house or Moon."
    )


SKIP_WHEN_MARRIAGE_LIFE = {
    "partnership_foreign",
    "marriage_timing",
    "multiple_relations",
}


def _client_cards(analysis: dict[str, Any], scored: list[dict]) -> list[dict]:
    marriage_block = marriage_life_client_cards(analysis)
    marriage_tids = {mc["theme_id"] for mc in marriage_block}

    cards = []
    for p in scored:
        tid = p.get("theme_id", "")
        if tid in marriage_tids or tid in SKIP_WHEN_MARRIAGE_LIFE:
            continue
        text = _narrative(tid, analysis)
        if not text:
            continue
        tone = "amber" if tid in ("vish_period_caution", "marriage_strain") else "green"
        cards.append({
            "title": CLIENT_TITLES.get(tid, p.get("title", "Prediction")),
            "text": text,
            "tone": tone,
            "theme_id": tid,
        })

    has_promise = any(c["theme_id"] == "marriage_promise" for c in cards)
    if has_promise or any(c["theme_id"] == "marriage_quality" for c in cards):
        insert_at = 2
        for i, c in enumerate(cards):
            if c["theme_id"] == "marriage_quality":
                insert_at = i + 1
                break
        for j, mc in enumerate(marriage_block):
            cards.insert(insert_at + j, mc)

    return cards


def render_navamsha_section(analysis: dict[str, Any], pc: dict | None = None) -> str:
    if analysis.get("error"):
        return f"<div class='pred-card amber'><div class='pred-body'>{_e(analysis['error'])}</div></div>"

    conf = build_navamsha_confluence(analysis, pc)
    cards = _client_cards(analysis, conf.get("predictions", []))

    parts = [
        "<p class='fine'>Educational astrology only (Goel, Predict with Navamsha).</p>",
        f"<div class='callout'><p class='pred'>{_e(_hero_paragraph(analysis))}</p></div>",
    ]

    if not cards:
        parts.append(
            "<div class='pred-card neutral'><div class='pred-body'>"
            "Navamsha layers in this chart did not converge strongly enough for a firm life-area call. "
            "Use the main Bhardwaj reading above; revisit navamsha when partnership or dharma questions arise."
            "</div></div>"
        )
    else:
        for c in cards:
            parts.append(f"<div class='pred-card {c['tone']}'>")
            parts.append(f"<div class='pred-head'>{_e(c['title'])}</div>")
            parts.append(f"<div class='pred-body'><p>{_e(c['text'])}</p></div></div>")

    return "\n".join(parts)
