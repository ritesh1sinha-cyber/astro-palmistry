#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Goel general rules for divisional chart inspection (Comprehensive Prediction by Divisional Charts)."""
from __future__ import annotations

from html import escape
from typing import Any

from astro_precompute import get_dignity

_BENEFICS = frozenset({"Moon", "Mercury", "Jupiter", "Venus"})
_MALEFICS = frozenset({"Sun", "Mars", "Saturn", "Rahu", "Ketu"})
_KENDRA_TRIKONA = frozenset({1, 4, 5, 7, 9, 10})
_NEXT_GOOD = frozenset({2, 11})
_DUSTHANA = frozenset({3, 6, 8, 12})

_VARGA_KARAKA: dict[str, str | None] = {
    "D1": None,
    "D2": "Jupiter",
    "D3": "Mars",
    "D4": "Moon",
    "D7": "Jupiter",
    "D9": "Venus",
}

_VARGA_THEME: dict[str, str] = {
    "D1": "life overall",
    "D2": "wealth and resources",
    "D3": "siblings, courage, and karma fruits",
    "D4": "home, property, and happiness",
    "D7": "children and progeny",
    "D9": "marriage, partnership, and dharma maturity",
}

# Pull higher-varga karaka/theme from the book corpus to avoid duplication.
try:
    from divisional_book_corpus import HIGHER_VARGA_CORPUS as _HVC
    for _v, _c in _HVC.items():
        _VARGA_KARAKA.setdefault(_v, _c.get("karaka") or None)
        _VARGA_THEME.setdefault(_v, _c.get("theme", "this life area"))
except Exception:  # noqa: BLE001 - corpus optional at import
    pass

_DIGNITY_WORD = {
    "exalted": "exalted",
    "own_sign": "in own sign",
    "moolatrikona": "in moolatrikona",
    "great_friend_sign": "well supported",
    "friendly": "fairly good",
    "neutral_sign": "average",
    "neutral": "average",
    "enemy_sign": "under pressure",
    "debilitated": "debilitated",
    "unknown": "unclear",
}


def _dig(d: str) -> str:
    return _DIGNITY_WORD.get(d, d.replace("_", " "))


def _ordinal(n: int) -> str:
    if n == 1:
        return "1st"
    if n == 2:
        return "2nd"
    if n == 3:
        return "3rd"
    return f"{n}th"


def _is_exception_good(varga: str, planet: str, house: int) -> bool:
    if planet == "Mars" and house == 6:
        return True
    if planet == "Mercury" and house == 8:
        return True
    if varga == "D4" and planet == "Mercury" and house == 8:
        return True
    if varga == "D9" and planet == "Venus" and house == 12:
        return True
    return False


def _house_placement_verdict(varga: str, planet: str, house: int | None, role: str) -> tuple[str, str, int]:
    """Score planet placement in varga per Goel rule 1."""
    if not house:
        return "neutral", f"{role} {planet}: house position unavailable.", 0

    if _is_exception_good(varga, planet, house):
        return (
            "positive",
            f"{role} {planet} in {_ordinal(house)} house — favourable by classical exception for this chart.",
            2,
        )

    dig_note = ""
    score = 0
    if house in _KENDRA_TRIKONA:
        score = 2
        place = "kendra/trikona (best for divisional charts)"
    elif house in _NEXT_GOOD:
        score = 1
        place = "2nd/11th (next-best for divisional charts)"
    elif house in _DUSTHANA:
        score = -2
        place = "3rd/6th/8th/12th (stress houses — weak even if dignified)"
    else:
        score = 0
        place = f"house {house}"

    if score >= 2:
        v = "positive"
    elif score <= -2:
        v = "caution"
    else:
        v = "neutral"

    return v, f"{role} {planet} sits in {_ordinal(house)} house ({place}).{dig_note}", score


def _lagna_strength(
    varga: str,
    chart: dict[str, Any],
    karaka: str | None,
) -> tuple[str, str, int]:
    """Goel rule 3 — lagna must be strong for varga results to deliver."""
    h1 = chart.get("houses", {}).get(1, {})
    tenants: list[str] = list(h1.get("tenants") or [])
    lagna = chart.get("lagna", "")
    score = 0
    notes: list[str] = []

    if not tenants:
        notes.append(f"{varga} lagna ({lagna}) is unoccupied — strength depends mainly on lagna lord placement.")
    else:
        non_karaka = [p for p in tenants if p != karaka]
        if karaka and karaka in tenants:
            score -= 2
            notes.append(
                f"Karaka {karaka} occupies {varga} lagna — classical rule treats this as unfavourable for smooth results."
            )
        if non_karaka:
            benefics = [p for p in non_karaka if p in _BENEFICS]
            malefics = [p for p in non_karaka if p in _MALEFICS]
            if benefics:
                score += 1
                notes.append(
                    f"Benefic(s) {', '.join(benefics)} on {varga} lagna strengthen the chart foundation."
                )
            if malefics and not benefics:
                score -= 1
                notes.append(
                    f"Malefic(s) {', '.join(malefics)} on {varga} lagna — results come with effort or sharp edges."
                )
            elif malefics and benefics:
                notes.append(
                    f"Mixed planets on lagna ({', '.join(tenants)}) — both support and stress are active."
                )

    # Subh kartari — benefics in 2nd and 12th from lagna
    h2t = chart.get("houses", {}).get(2, {}).get("tenants") or []
    h12t = chart.get("houses", {}).get(12, {}).get("tenants") or []
    subh_2 = any(p in _BENEFICS for p in h2t)
    subh_12 = any(p in _BENEFICS for p in h12t)
    if subh_2 and subh_12:
        score += 1
        notes.append("Subh kartari on lagna (benefics in 2nd and 12th) — protective frame for this varga.")
    elif subh_2 or subh_12:
        notes.append("Partial kartari on lagna — one side is protected, the other is open.")

    if score >= 1:
        return "positive", " ".join(notes), score
    if score <= -1:
        return "caution", " ".join(notes), score
    return "neutral", " ".join(notes) if notes else f"{varga} lagna strength is average.", score


def inspect_varga_chart(
    varga: str,
    chart: dict[str, Any],
    pc: dict,
    d1_lagna_lord: str = "",
) -> dict[str, Any]:
    """
    Goel general inspection for a divisional chart:
    1. D1 lagna lord well placed in varga
    2. Varga lagna lord well placed in varga
    3. Karaka well placed in varga (not in varga lagna)
    4. Varga lagna strength
    """
    karaka = _VARGA_KARAKA.get(varga)
    theme = _VARGA_THEME.get(varga, "this life area")
    planets = chart.get("planets") or {}
    checks: list[dict[str, Any]] = []
    total = 0

    # D1 lagna lord in varga
    if d1_lagna_lord:
        d1_ll = planets.get(d1_lagna_lord) or {}
        h = d1_ll.get("house")
        sign = d1_ll.get("sign", "")
        dig = get_dignity(d1_lagna_lord, sign) if sign else "unknown"
        v, note, sc = _house_placement_verdict(varga, d1_lagna_lord, h, "Birth-chart lagna lord")
        note += f" Dignity in {varga}: {_dig(dig)}."
        checks.append({"label": "D1 lagna lord in varga", "verdict": v, "note": note, "score": sc})
        total += sc

    # Varga lagna lord in varga
    v_ll = chart.get("lagna_lord", "")
    v_ll_h = chart.get("lagna_lord_varga_house")
    if v_ll_h is None and v_ll:
        v_ll_h = (planets.get(v_ll) or {}).get("house")
    v_ll_sign = chart.get("lagna_lord_varga_sign") or (planets.get(v_ll) or {}).get("sign", "")
    v_ll_dig = chart.get("lagna_lord_dignity_varga") or (
        get_dignity(v_ll, v_ll_sign) if v_ll_sign else "unknown"
    )
    if v_ll:
        v, note, sc = _house_placement_verdict(varga, v_ll, v_ll_h, f"{varga} lagna lord")
        note += f" Dignity in {varga}: {_dig(v_ll_dig)}."
        if v_ll_dig in ("exalted", "own_sign", "moolatrikona"):
            sc += 1
            note += " Strong dignity supports delivery."
        elif v_ll_dig in ("debilitated", "enemy_sign"):
            sc -= 1
            note += " Weak dignity delays results even in a good house."
        checks.append({"label": f"{varga} lagna lord", "verdict": v, "note": note, "score": sc})
        total += sc

    # Karaka
    if karaka:
        k = planets.get(karaka) or {}
        k_h = k.get("house")
        k_sign = k.get("sign", "")
        k_dig = get_dignity(karaka, k_sign) if k_sign else "unknown"
        if k_h == 1:
            checks.append({
                "label": f"Karaka {karaka}",
                "verdict": "caution",
                "note": (
                    f"Karaka {karaka} sits in {varga} lagna — classical rule: karaka in divisional lagna "
                    f"does not give smooth results for {theme}."
                ),
                "score": -2,
            })
            total -= 2
        else:
            v, note, sc = _house_placement_verdict(varga, karaka, k_h, f"Karaka {karaka}")
            note += f" Dignity in {varga}: {_dig(k_dig)}."
            checks.append({"label": f"Karaka {karaka}", "verdict": v, "note": note, "score": sc})
            total += sc

    # Lagna strength
    lv, lnote, lsc = _lagna_strength(varga, chart, karaka)
    checks.append({"label": f"{varga} lagna strength", "verdict": lv, "note": lnote, "score": lsc})
    total += lsc

    if total >= 4:
        overall = "strong"
        summary = (
            f"Overall, this {varga} chart has a <strong>strong foundation</strong> for {theme}. "
            f"Birth-chart lagna lord, {varga} lagna lord, and lagna strength support the house-by-house promises below."
        )
        tone = "positive"
    elif total >= 1:
        overall = "moderate"
        summary = (
            f"This {varga} chart is <strong>moderately supported</strong> for {theme}. "
            f"Some results flow easily; others need dasha timing, effort, or remedies on the weak points noted here."
        )
        tone = "neutral"
    else:
        overall = "weak"
        summary = (
            f"This {varga} chart shows <strong>stress on the foundation</strong> for {theme}. "
            f"House promises may feel delayed or uneven until lagna lord and karaka are strengthened — "
            f"read house sections with this filter in mind."
        )
        tone = "caution"

    return {
        "varga": varga,
        "overall": overall,
        "tone": tone,
        "summary": summary,
        "checks": checks,
        "score": total,
    }


def inspect_d1_pillar(pillar: Any, pc: dict) -> dict[str, Any]:
    """D1 inspection — strong lagna + lagna lord required before divisional charts deliver (Goel + corpus)."""
    meta = pc.get("meta", {})
    lagna = meta.get("lagna_sign", "")
    ll = pillar.lagna_lord
    ll_pl = pc.get("planets", {}).get(ll, {})
    ll_h = ll_pl.get("house")
    ll_sign = ll_pl.get("sign", "")
    ll_dig = get_dignity(ll, ll_sign) if ll_sign else "unknown"
    ps = pillar.score()["overall"]

    checks: list[dict[str, Any]] = []
    total = 0

    v, note, sc = _house_placement_verdict("D1", ll, ll_h, "Lagna lord")
    note += f" Dignity: {_dig(ll_dig)}."
    if ll_dig in ("exalted", "own_sign", "moolatrikona"):
        sc += 1
    elif ll_dig in ("debilitated", "enemy_sign"):
        sc -= 1
    checks.append({"label": "Lagna lord placement", "verdict": v, "note": note, "score": sc})
    total += sc

    h1_t = [
        n for n, p in pc.get("planets", {}).items()
        if p.get("house") == 1 and n in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
    ]
    chart_stub = {
        "lagna": lagna,
        "houses": {
            1: {"tenants": h1_t},
            2: {"tenants": [n for n, p in pc.get("planets", {}).items() if p.get("house") == 2]},
            12: {"tenants": [n for n, p in pc.get("planets", {}).items() if p.get("house") == 12]},
        },
    }
    lv, lnote, lsc = _lagna_strength("D1", chart_stub, None)
    checks.append({"label": "D1 lagna strength", "verdict": lv, "note": lnote, "score": lsc})
    total += lsc

    if ps >= 7:
        checks.append({
            "label": "Pillar of Life score",
            "verdict": "positive",
            "note": f"Pillar score {ps}/10 — birth lagna is strong enough to carry divisional promises.",
            "score": 2,
        })
        total += 2
    elif ps >= 4:
        checks.append({
            "label": "Pillar of Life score",
            "verdict": "neutral",
            "note": f"Pillar score {ps}/10 — moderate birth lagna; divisional charts modify but do not replace D1.",
            "score": 0,
        })
    else:
        checks.append({
            "label": "Pillar of Life score",
            "verdict": "caution",
            "note": f"Pillar score {ps}/10 — afflicted birth lagna; strengthen D1 before expecting full varga results.",
            "score": -1,
        })
        total -= 1

    if total >= 4:
        overall, tone = "strong", "positive"
        summary = (
            "Your birth chart lagna and lagna lord are <strong>well supported</strong>. "
            "This is the trunk — divisional charts (D2, D3, D4, D7…) can deliver on their themes when dasha activates them."
        )
    elif total >= 1:
        overall, tone = "moderate", "neutral"
        summary = (
            "Your birth chart lagna is <strong>moderately strong</strong>. "
            "Divisional promises work in phases — lean on favourable dasha periods and lagna lord remedies."
        )
    else:
        overall, tone = "weak", "caution"
        summary = (
            "Your birth chart lagna needs <strong>support</strong> before divisional charts fully deliver. "
            "Remedies for lagna lord and health/confidence are priority; varga readings below are filtered through this."
        )

    return {
        "varga": "D1",
        "overall": overall,
        "tone": tone,
        "summary": summary,
        "checks": checks,
        "score": total,
    }


def goel_inspection_html(result: dict[str, Any], title: str | None = None) -> str:
    """Prominent HTML block for Goel varga inspection."""
    varga = result.get("varga", "")
    tone = result.get("tone", "neutral")
    summary = result.get("summary", "")
    overall = result.get("overall", "moderate")
    badge = {"strong": "Favourable foundation", "moderate": "Mixed foundation", "weak": "Weak foundation"}.get(
        overall, "Mixed foundation"
    )
    bdg = {"positive": "pos", "neutral": "neu", "caution": "cau"}.get(tone, "neu")
    hdr = title or f"Chart foundation — {varga} lagna & lagna lord (mandatory first check)"

    rows = []
    for c in result.get("checks", []):
        cv = c.get("verdict", "neutral")
        cbdg = {"positive": "pos", "neutral": "neu", "caution": "cau"}.get(cv, "neu")
        clbl = {"positive": "Favourable", "neutral": "Mixed", "caution": "Watch"}.get(cv, "Mixed")
        rows.append(
            f'<tr><td>{escape(c.get("label", ""))}</td>'
            f'<td><span class="bdg {cbdg}">{clbl}</span></td>'
            f'<td>{escape(c.get("note", ""))}</td></tr>'
        )

    return (
        f'<h2 class="section-h">{escape(hdr)}</h2>'
        f'<div class="card d7-conclusion {tone}">'
        f'<p class="verdict"><span class="bdg {bdg}">{badge}</span> {summary}</p>'
        f'<p class="fine">Per classical divisional-chart rules: birth lagna lord, {varga} lagna lord, '
        f'karaka (where applicable), and {varga} lagna strength must be checked before house results are taken at full strength.</p>'
        f'<table class="tech"><thead><tr><th>Check</th><th>Status</th><th>Reading</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
        f"</div>"
    )
