#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Human prediction-first prose for Mehta Modern Techniques lane."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from bhardwaj_semantic import _ord
from mehta_analysis import HOUSE_TOPICS, MehtaSection, analyze_all_sections

if TYPE_CHECKING:
    from mehta_chart import MehtaChart


@dataclass
class LifeSection:
    title: str
    prediction: str
    fact: str
    tone: str = "neutral"
    domain: str = ""


def _to_life(sec: MehtaSection) -> LifeSection:
    return LifeSection(
        title=sec.title,
        prediction=sec.prediction,
        fact=sec.facts,
        tone=sec.tone,
        domain=sec.id,
    )


def build_life_sections(chart: "MehtaChart") -> list[LifeSection]:
    return [_to_life(s) for s in analyze_all_sections(chart)]


def mehta_hero(chart: "MehtaChart") -> str:
    for s in analyze_all_sections(chart):
        if s.id == "intro":
            return s.prediction
    return ""


def _antardasha_prediction(chart: "MehtaChart", ad_lord: str, house: int, dignity: str) -> str:
    """Chart-specific antardasha read from house placement and dignity."""
    theme = HOUSE_TOPICS.get(house, "life themes").split(",")[0]
    dig = {
        "exalted": "well dignified",
        "debilitated": "strained in dignity",
        "moolatrikona": "in moolatrikona",
        "own_sign": "in own sign",
    }.get(dignity, "moderately placed")
    if dignity in ("exalted", "own_sign", "moolatrikona"):
        return (
            f"{ad_lord} is {dig} in the {_ord(house)}  -  this sub-period favours {theme}. "
            f"Push visible goals in that lane while the window is open."
        )
    if dignity == "debilitated" or house in (6, 8, 12):
        return (
            f"{ad_lord} in the {_ord(house)} ({dig}) tests {theme}  -  consolidate, avoid rash moves, "
            f"and lean on remedies for {ad_lord} during this band."
        )
    return (
        f"{ad_lord} activates {_ord(house)}-house themes ({theme}) in this sub-period  -  "
        f"see the matching Mehta house chapter for the full read."
    )


def mehta_year_ahead_html(chart: "MehtaChart") -> str:
    md = chart.cur_md["md_lord"]
    cards: list[str] = []
    shown = 0
    for ad in chart.antars:
        status = ad.get("status", "")
        if status not in ("current", "future"):
            continue
        ad_lord = ad["ad_lord"]
        info = chart.planets[ad_lord]
        try:
            s = datetime.strptime(ad["start"][:10], "%Y-%m-%d").strftime("%b %Y")
            e = datetime.strptime(ad["end"][:10], "%Y-%m-%d").strftime("%b %Y")
            window = f"{s} - {e}"
        except ValueError:
            window = "n/a"
        label = {"current": "Active now", "future": "Coming up"}.get(status, "")
        tone = "green" if status == "current" else ("good" if ad_lord == "Venus" else "neutral")
        pred = _antardasha_prediction(chart, ad_lord, info["house"], info["dignity"])
        cards.append(
            f"<div class='pred-card {tone}'><div class='pred-body'>"
            f"<strong>{window}</strong> - {ad_lord} antardasha{f' ({label})' if label else ''}. "
            f"{pred}</div></div>"
        )
        shown += 1
        if shown >= 5:
            break

    highlight = ""
    ven_ad = next(
        (a for a in chart.antars if a.get("ad_lord") == "Venus" and a.get("status") == "future"),
        None,
    )
    if ven_ad and chart.planets["Venus"]["dignity"] in ("exalted", "own_sign", "moolatrikona"):
        try:
            vs = datetime.strptime(ven_ad["start"][:10], "%Y-%m-%d").strftime("%b %Y")
            ve = datetime.strptime(ven_ad["end"][:10], "%Y-%m-%d").strftime("%b %Y")
            highlight = (
                f"<p class='pred'><strong>Headline:</strong> Venus antardasha ({vs}  -  {ve}) "
                f"is a strong comfort, relationship, and creative-income window  -  Venus is well placed in your chart.</p>"
            )
        except ValueError:
            pass

    return (
        f"<p class='lead'>Inside <strong>{md} mahadasha</strong>, Mehta reads each antardasha from where that planet sits in your chart - not from generic lists.</p>"
        f"{highlight}"
        + "".join(cards)
    )


def mehta_yoga_narrative(yogas: list[dict]) -> str:
    if not yogas:
        return ""
    from mehta_analysis import YOGA_HUMAN
    items = []
    for y in yogas:
        human = YOGA_HUMAN.get(y["name"])
        text = human or re.sub(r"\bd\?ridra\b", "daridra", y["result"], flags=re.I)
        items.append(f"<li>{text}</li>")
    return f"<ul>{''.join(items)}</ul>"


def mehta_intro_callout(steps: list[str]) -> str:
    return ""


def mehta_lord_table_rows(chart: "MehtaChart") -> list[tuple[str, str, str, str]]:
    """Rows for house-lord appendix: (house, lord, occ, clipped text)."""
    import html as _html
    from bhardwaj_semantic import _ord
    from mehta_book_data import lookup_mehta_lord

    def _clip(text: str, n: int = 220) -> str:
        text = " ".join(text.split())
        if len(text) <= n:
            return text
        return text[: n - 1].rsplit(" ", 1)[0] + "..."

    rows: list[tuple[str, str, str, str]] = []
    for h in range(1, 13):
        lord = chart.houses[h]["lord"]
        occ = chart.planets[lord]["house"]
        txt = lookup_mehta_lord(
            chart.book, h, occ,
            "caution" if occ in (6, 8, 12) else "neutral",
        )
        rows.append(
            (
                _ord(h),
                _html.escape(lord),
                _ord(occ),
                _html.escape(_clip(txt) if txt else "-"),
            )
        )
    return rows
