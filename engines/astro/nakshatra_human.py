#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Human birth-star karmic lesson prose for client reports (rules42)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from nakshatra_karmic_data import chart_stars, short_title, summarize_tale, theme_tags

if TYPE_CHECKING:
    from kp_chart import KPChart

_HABITS = {
    "trust and betrayal": "Choose transparency in close bonds; do not tolerate quiet double-dealing.",
    "greed and debt": "Return what is not yours and keep financial vows clean.",
    "duty and service": "Serve without keeping score; let competence speak louder than status.",
    "loss and grief": "Grieve honestly but do not let fear of loss freeze new commitment.",
    "redemption": "Repair one old wrong before chasing a fresh start.",
    "relationship knots": "Pick partners by character, not charm alone.",
    "health and worry": "When worry rises, tighten sleep and routine before chasing fixes.",
    "wealth and craft": "Let skill and fair dealing build wealth; shortcuts boomerang.",
}


def _ordinal(p: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(p, f"{p}th")


def _chart_echo(pc: dict, tags: list[str]) -> str:
    moon = pc.get("planets", {}).get("Moon", {})
    house = moon.get("house_whole_sign") or moon.get("house")
    sign = moon.get("sign", "")
    if house:
        base = f"with Moon in the {house}th house ({sign}), home and inner security carry this lesson loudly"
    else:
        base = "the emotional tone behind your dasha seasons carries this lesson"
    if "trust and betrayal" in tags or "relationship knots" in tags:
        return f"{base}; loyalty in love and money is the recurring exam."
    if "greed and debt" in tags:
        return f"{base}; clean accounts and fair returns matter more than quick gain."
    return f"{base}."


def human_birth_star(pc: dict) -> tuple[str, str]:
    stars = chart_stars(pc)
    moon = stars.get("moon")
    if not moon or not moon.get("tale"):
        return "", "Moon nakshatra tale not found in OCR corpus"
    tale = moon["tale"]
    nak, pada = moon["nakshatra"], moon["pada"]
    if tale.get("fallback_pada"):
        pada_note = f" (OCR gap - using adjacent {_ordinal(tale['fallback_pada'])} pada text)"
    else:
        pada_note = ""
    tags = theme_tags(tale.get("body", ""))
    title = short_title(tale)
    theme_line = ", ".join(tags) if tags else "karmic consequence and choice"
    habit = _HABITS.get(tags[0], "Act with integrity when comfort tempts you to cut corners.")
    moral = (tale.get("moral") or "").strip()
    if moral and len(moral) > 220:
        moral = moral[:217].rsplit(" ", 1)[0] + "..."
    parts = [
        f"Your birth star is {nak} ({_ordinal(pada)} pada{pada_note}). "
        f"The handbook tale \"{title}\" is metaphorical folklore, not literal history.",
        f"The story turns on {theme_line}: skilled hands and comfort do not excuse broken trust or hidden debt.",
    ]
    if moral:
        parts.append(moral)
    parts.append(
        f"In this life the echo is emotional: {_chart_echo(pc, tags)} "
        f"Practical habit: {habit}"
    )
    lagna = stars.get("lagna")
    if lagna and lagna.get("tale") and (
        lagna["nakshatra"] != nak or lagna["pada"] != pada
    ):
        lt = lagna["tale"]
        lt_tags = theme_tags(lt.get("body", ""))
        lt_theme = lt_tags[0] if lt_tags else "body-path emphasis"
        parts.insert(
            3,
            f"Rising star {lagna['nakshatra']} {_ordinal(lagna['pada'])} pada adds a public-body layer - "
            f"{short_title(lt)} themes ({lt_theme}) colour how others read your path, not only your inner Moon story.",
        )
    fact = f"Moon {nak} pada {pada}, story #{tale.get('story_id', '?')}"
    return " ".join(parts), fact


def human_birth_star_kp(kp: "KPChart") -> tuple[str, str]:
    pred, fact = human_birth_star(kp.pc)
    if not pred:
        return pred, fact
    c7_nak = kp.cusp(7).get("nak", "")
    if c7_nak == "Venus":
        pred += (
            " In KP, Venus stars the 7th cusp - the birth-star lesson on trust and craft "
            "pairs with partnership timing through Jupiter/Venus dasha slices."
        )
    return pred, fact
