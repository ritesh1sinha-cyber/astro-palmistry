#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Book-backed Jaimini prose (Goel rules6, Boney rules30/31)."""
from __future__ import annotations

import html
from typing import TYPE_CHECKING

from jaimini_book_data import (
    argala_quality,
    kl_house_of_planet,
    lookup_kl_house_theme,
    lookup_kl_occupation,
    lookup_planet_kl_house,
    planets_in_kl_house,
    scan_raja_yoga_pairs,
)

if TYPE_CHECKING:
    from vedic_jaimini_report import Jaimini


def _e(s: str) -> str:
    return html.escape(str(s))


def _clip(text: str, n: int = 420) -> str:
    text = " ".join(text.split())
    if len(text) <= n:
        return text
    return text[: n - 1].rsplit(" ", 1)[0] + "..."


def jaimini_intro_callout(book: dict) -> str:
    basics = book.get("goel_basics", [])[:5]
    if not basics:
        return ""
    items = "".join(f"<li>{_e(_clip(b, 200))}</li>" for b in basics)
    return (
        "<div class='callout'><p class='pred'><strong>Jaimini first principles (Goel rules6):</strong> "
        "Sign aspects, variable cara karakas, Karakamsha, argala, Chara dasha - separate clock from Vimshottari.</p>"
        f"<ul>{items}</ul></div>"
    )


def kl_corpus_section(jm: "Jaimini", book: dict) -> str:
    """Gems rules30 - planets from Karakamsha lagna."""
    if not jm.ak_navamsa:
        return ""
    kl = jm.ak_navamsa
    ak = jm.role("Atmakarak")
    akp = ak.get("planet", "")
    parts = [
        f"<p class='pred'><strong>Karakamsha ({kl}):</strong> Inner promise chart - Boney applies graha effects "
        "from this lagna in D1 and D9 (karakamsa / svamsa).</p>",
    ]
    if akp:
        occ = lookup_kl_occupation(book, akp)
        if occ:
            parts.append(
                f"<p class='pred'>Your Atmakarak <strong>{akp}</strong> anchors the inner lagna - "
                f"<em>{_e(_clip(occ))}</em></p>"
            )
    for h in (10, 4, 5, 12, 2):
        theme = lookup_kl_house_theme(book, h)
        tenants = planets_in_kl_house(jm.pc, kl, h)
        if theme and tenants:
            clauses = []
            for pl in tenants:
                specific = lookup_planet_kl_house(book, pl, h)
                clauses.append(specific or theme)
            body = _clip(
                clauses[0] if len(clauses) == 1 else f"{theme} Planets present: {', '.join(tenants)}."
            )
            parts.append(
                f"<p class='pred'><strong>{h}th from KL ({', '.join(tenants)}):</strong> {_e(body)}</p>"
            )
        elif theme and h in (12, 5):
            parts.append(f"<p class='pred'><strong>{h}th-from-KL theme:</strong> {_e(_clip(theme))}</p>")
    for pl in jm.pc.get("planets", {}):
        kh = kl_house_of_planet(jm.pc, kl, pl)
        if kh and kh not in (10, 4, 5, 12, 2):
            txt = lookup_planet_kl_house(book, pl, kh)
            if txt:
                parts.append(
                    f"<p class='pred'><strong>{pl} in {kh}th from KL:</strong> {_e(_clip(txt))}</p>"
                )
    return "".join(parts) if len(parts) > 1 else ""


def raja_yoga_section(jm: "Jaimini", book: dict, sign_aspects_from, house_of) -> str:
    def _mutual(a: str, b: str) -> bool:
        return b in sign_aspects_from(a) and a in sign_aspects_from(b)

    hits = scan_raja_yoga_pairs(jm.karakas, jm.pc, _mutual)
    amk = jm.role("Amatyakarak")
    ak = jm.role("Atmakarak")
    extra = []
    if amk.get("sign") and ak.get("sign"):
        rel = house_of(amk["sign"], ak["sign"])
        if rel in (1, 4, 5, 7, 9, 10, 11):
            extra.append(f"AmK in {rel} from AK sign - easier professional success (Goel rules6).")
        elif rel in (6, 8, 12):
            extra.append(f"AmK in trika ({rel}) from AK - success after struggle; patience required.")
    rules = book.get("goel_raja_yoga_pairs", [])[:4]
    if not hits and not extra:
        return (
            "<p class='pred'>No major karaka-pair raja yoga by conjunction/sign aspect in this scan. "
            "Check D9 repetition per Goel.</p>"
        )
    items = "".join(f"<li>{_e(h)}</li>" for h in hits[:5])
    extra_items = "".join(f"<li>{_e(x)}</li>" for x in extra)
    checklist = "".join(f"<li class='fine'>{_e(_clip(r, 160))}</li>" for r in rules)
    return (
        f"<ul>{items}{extra_items}</ul>"
        "<details><summary>Goel raja yoga checklist (rules6)</summary>"
        f"<ul>{checklist}</ul></details>"
    )


def jewels_argala_note(jm: "Jaimini", book: dict, sign_at) -> str:
    lagna = jm.lagna
    benefic, malefic, positions = 0, 0, 0
    for ah in (4, 2, 11):
        a_sign = sign_at(lagna, ah)
        pls = jm.planets_in(a_sign)
        if not pls:
            continue
        positions += 1
        for p in pls:
            if p in {"Jupiter", "Venus", "Mercury", "Moon"}:
                benefic += 1
            else:
                malefic += 1
    tier = argala_quality(book, benefic, malefic, positions)
    tiers = book.get("jewels_argala_tiers", {})
    label = {
        "superior": "Superior",
        "above_average": "Above average",
        "average": "Average",
        "none": "Weak/absent",
    }.get(tier, tier)
    sample = (tiers.get(tier) or [""])[0] if tier in tiers else ""
    body = _clip(sample) if sample else "Jewels rules31: unobstructed argala qualifies yogada planets."
    return f"<p class='fine'><strong>Argala quality (Jewels rules31):</strong> {label} - {_e(body)}</p>"


def career_gems_clause(jm: "Jaimini", book: dict) -> str:
    amk = jm.role("Amatyakarak")
    p = amk.get("planet", "")
    if not p or not jm.ak_navamsa:
        return ""
    pl_sign = jm.pc.get("planets", {}).get(p, {}).get("sign")
    kl_h = jm.kl_house(pl_sign) if pl_sign else 0
    occ = lookup_kl_occupation(book, p)
    kl_txt = lookup_planet_kl_house(book, p, kl_h) if kl_h else ""
    bits = []
    if occ:
        bits.append(_clip(occ))
    if kl_txt:
        bits.append(_clip(kl_txt))
    tenth = lookup_kl_house_theme(book, 10)
    tenth_pl = planets_in_kl_house(jm.pc, jm.ak_navamsa, 10)
    if tenth and tenth_pl:
        bits.append(_clip(f"10th-from-KL ({', '.join(tenth_pl)}): {tenth}"))
    return f" <em>(Gems rules30: {' '.join(bits[:2])})</em>" if bits else ""


def spiritual_12th_clause(jm: "Jaimini", book: dict) -> str:
    if not jm.ak_navamsa:
        return ""
    theme = lookup_kl_house_theme(book, 12)
    pls = planets_in_kl_house(jm.pc, jm.ak_navamsa, 12)
    if not theme:
        return ""
    if pls:
        return f" <em>(12th-from-KL: {', '.join(pls)} - {_clip(theme, 200)})</em>"
    return f" <em>({_clip(theme, 200)})</em>"


def book_appendix(book: dict, matched: int) -> str:
    src = book.get("sources", [])
    items = "".join(f"<li>{_e(s)}</li>" for s in src)
    return (
        f"<details class='appendix'><summary>Book corpus ({matched} clauses matched)</summary>"
        "<p class='fine'>Three-book Jaimini lane - confluence report wires later.</p>"
        f"<ul>{items}</ul>"
        "<p class='fine'>Rebuild: <code>python3 build_jaimini_data.py</code></p></details>"
    )
