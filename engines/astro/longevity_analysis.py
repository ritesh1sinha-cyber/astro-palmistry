#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Book-backed longevity analysis: MB orbs, maraka ranking, arista, dasha risk."""
from __future__ import annotations

from typing import Any

from longevity_book_data import load_longevity_book

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
    "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
NATURAL_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}


def mb_degree(book: dict, planet: str, sign: str) -> int | None:
    row = book.get("mb_table", {}).get(planet, {})
    val = row.get(sign)
    if val is None:
        return None
    return int(val)


def check_mb(book: dict, planet: str, sign: str, deg: float) -> dict:
    mb = mb_degree(book, planet, sign)
    if mb is None:
        return {"status": "n/a", "diff": None, "mb": None, "orb": None}
    diff = abs(deg - mb)
    orb = book["mb_orbs_deg"].get(planet, book["mb_orbs_deg"].get("Mars", 0.5))
    near_max = book.get("mb_near_max_deg", 1.0)
    if diff <= orb:
        status = "IN MB"
    elif diff <= near_max:
        status = "Near MB"
    else:
        status = "Clear"
    return {
        "status": status,
        "diff": round(diff, 4),
        "diff_minutes": round(diff * 60, 1),
        "mb": mb,
        "orb_minutes": round(orb * 60, 1),
        "natal_degree": round(deg, 4),
    }


def scan_mb_all(book: dict, planets: dict, lagna_sign: str, lagna_deg: float) -> list[dict]:
    rows = []
    lagna_mb = check_mb(book, "Lagna", lagna_sign, lagna_deg % 30)
    rows.append({"planet": "Lagna", "sign": lagna_sign, **lagna_mb})
    for planet, data in planets.items():
        if planet not in book.get("mb_table", {}):
            continue
        sign = data.get("sign", "")
        deg = float(data.get("degree_in_sign", data.get("degree", 0)))
        if sign not in SIGNS:
            continue
        hit = check_mb(book, planet, sign, deg)
        rows.append({"planet": planet, "sign": sign, **hit})
    order = {"IN MB": 0, "Near MB": 1, "Clear": 2, "n/a": 3}
    rows.sort(key=lambda r: (order.get(r["status"], 9), r.get("diff") or 99))
    return rows


def primary_marakas(book: dict, lagna: str) -> tuple[str, str]:
    spec = book["primary_maraka_by_lagna"].get(lagna, {})
    return spec.get("2nd_lord", "?"), spec.get("7th_lord", "?")


def functional_killer(book: dict, lagna: str) -> str:
    return book.get("functional_killer_quote", {}).get(lagna, "")


def maraka_rank_note(book: dict) -> str:
    return (
        "K.N. Rao killer order (from Laghu Parashari): 2nd lord strongest, then 7th lord, "
        "then occupants of 2nd/7th, then planets associated with those lords; "
        "then 12th lord chain; then 8th lord; then 3rd/6th/11th lords."
    )


def classify_ad_book(
    lg: Any,
    ad_lord: str,
    md_lord: str,
    book: dict,
    mb_rows: list[dict],
) -> tuple[str, str, str, str]:
    m1, m2 = primary_marakas(book, lg.lagna)
    maraka_set = {m1, m2}
    mb_map = {r["planet"]: r for r in mb_rows}
    mb_row = mb_map.get(ad_lord, {})
    mb_status = mb_row.get("status", "Clear")

    cls = []
    if ad_lord in maraka_set:
        cls.append("Primary maraka")
        if ad_lord == m1:
            cls.append("2nd lord (strongest killer)")
        if ad_lord == m2:
            cls.append("7th lord")
    if ad_lord in book.get("unqualified_marakas", []):
        cls.append("Unqualified maraka")
    if ad_lord == lg.lagna_lord:
        cls.append("Lagna lord")
    if not cls:
        fn = lg.planets[ad_lord].get("functional", "neutral")
        if fn == "functional_malefic":
            cls.append("Functional malefic")
        elif ad_lord in NATURAL_BENEFIC:
            cls.append("Benefic")
        else:
            cls.append("Neutral")

    score = 0
    if ad_lord in maraka_set:
        score += 3 if ad_lord == m1 else 2
    if ad_lord in book.get("unqualified_marakas", []):
        score += 1
    if mb_status == "IN MB":
        score += 3
    elif mb_status == "Near MB":
        score += 1
    if md_lord in maraka_set:
        score += 1
    if ad_lord == lg.lagna_lord:
        score -= 2
    dig = lg.planets[ad_lord]["dignity"]
    if ad_lord in NATURAL_BENEFIC and dig == "exalted":
        score -= 2
    elif ad_lord in NATURAL_BENEFIC and dig in ("own_sign", "moolatrikona"):
        score -= 1

    if score >= 5:
        risk = "Highest"
    elif score >= 4:
        risk = "High"
    elif score >= 2:
        risk = "Moderate"
    else:
        risk = "Low"

    theme = {
        "Highest": "Peak maraka configuration - maximum health vigilance and upaya. Educational only.",
        "High": "Elevated maraka signature - preventive care strongly advised.",
        "Moderate": "Mixed period - keep health routines firm.",
        "Low": "Relatively protected antardasha within the mahadasha backdrop.",
    }[risk]
    return (" + ".join(cls), mb_status, risk, theme)


def arista_assessment(lg: Any, mb_rows: list[dict], book: dict) -> tuple[list[str], list[str], str]:
    protective, risk = [], []
    ll = lg.lagna_lord
    ll_h = lg.planets[ll]["house"]
    if ll_h in (1, 4, 7, 10):
        protective.append(f"Lagna lord {ll} in kendra (house {ll_h}) - primary body protection.")
    if lg.planets[ll]["dignity"] in ("exalted", "own_sign", "moolatrikona"):
        protective.append(f"Lagna lord {ll} dignified - vitality support.")

    crit_mb = [r for r in mb_rows if r["status"] == "IN MB" and r["planet"] != "Lagna"]
    near_mb = [r for r in mb_rows if r["status"] == "Near MB"]
    m1, m2 = primary_marakas(book, lg.lagna)
    for r in crit_mb:
        extra = ""
        if r["planet"] in (m1, m2):
            extra = " (primary maraka)"
        elif r["planet"] in book.get("unqualified_marakas", []):
            extra = " (unqualified maraka)"
        risk.append(f"{r['planet']} IN MB in {r['sign']}{extra}.")
    for r in near_mb[:3]:
        risk.append(f"{r['planet']} Near MB in {r['sign']}.")

    m2p = lg.planets.get(m2, {})
    if m2p.get("dignity") == "debilitated":
        risk.append(f"7th lord {m2} debilitated in house {m2p.get('house')} - maraka weakened but in dusthana.")

    if len(risk) >= 3 and len(protective) <= 1:
        level = "MODERATE-HIGH"
    elif len(risk) >= 2:
        level = "MODERATE"
    else:
        level = "LOW-MODERATE"
    return protective, risk, level


def methodology_html() -> str:
    book = load_longevity_book()
    slokas = "".join(f"<li>{s}</li>" for s in book.get("maraka_slokas", [])[:8])
    hierarchy = "".join(f"<li>{h}</li>" for h in book.get("rao_hierarchy", []))
    mb_rules = "".join(f"<li>{r}</li>" for r in book.get("mb_rules", []))
    deaths = "".join(f"<li>{d}</li>" for d in book.get("eight_death_types", []))
    return (
        '<section class="section"><h2>0 - Methodology (book OCR)</h2>'
        f'<p class="fine">{book.get("educational_disclaimer", "")}</p>'
        "<h3>Laghu Parashari maraka slokas</h3><ul>" + slokas + "</ul>"
        "<h3>K.N. Rao killer hierarchy</h3><ul>" + hierarchy + "</ul>"
        "<h3>Mrityu Bhaga rules</h3><ul>" + mb_rules + "</ul>"
        "<h3>Eight kinds of death MB can bring</h3><ul>" + deaths + "</ul></section>"
    )
