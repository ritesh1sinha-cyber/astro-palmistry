#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Goel Saptamsha - client-facing prediction cards (rules14)."""
from __future__ import annotations

import html
from typing import Any

from goel_children_timing import timing_client_paragraph


def _e(s: str) -> str:
    return html.escape(str(s))


def _promise_card(analysis: dict) -> dict:
    score = analysis.get("d7_lagna_score", 0)
    denial = analysis.get("denial_hits", [])
    if denial:
        text = (
            "Progeny is strained or blocked on the saptamsha map. "
            + denial[0]
            + ". Benefic support on saptamsha lagna can still allow a child through adoption when desire is present."
        )
        tone = "amber"
    elif score >= 1:
        text = (
            f"Saptamsha lagna {analysis.get('d7_lagna')} is supported - the desire for children is present "
            "and effort can bear fruit. D7 has final say over the birth fifth house; here it confirms promise."
        )
        tone = "green"
    elif score <= -1:
        text = (
            "Malefic weight on saptamsha lagna - delay, fewer children, or a non-biological path needs honest consideration."
        )
        tone = "amber"
    else:
        text = (
            "Saptamsha lagna is mixed - children are not denied outright, but timing and patience matter."
        )
        tone = "neutral"
    return {"title": "Promise of children", "text": text, "tone": tone, "theme_id": "promise"}


def _santana_card(analysis: dict) -> dict | None:
    st = analysis.get("extras", {}).get("santana_tithi", {})
    if not st.get("computed"):
        return None
    tone = {"green": "green", "amber": "amber", "hard": "amber"}.get(st.get("tone", "neutral"), "neutral")
    return {
        "title": "Santana tithi (progeny karma)",
        "text": f"Classical Santana tithi is {st.get('label', '')}. {st.get('verdict', '')}",
        "tone": tone,
        "theme_id": "santana",
    }


def _beeja_card(analysis: dict, female: bool) -> dict | None:
    bk = analysis.get("beeja_kshetra", {})
    if not bk.get("computed"):
        return None
    label = bk.get("label", "Sphuta")
    need = "even" if female else "odd"
    mc = bk.get("match_count", 0)
    parts = [
        f"{label} falls in {bk.get('d1_sign')} (D1), {bk.get('d9_sign')} (D9), {bk.get('d7_sign')} (D7).",
        f"It matches the {need}-sign fertility rule in {mc} of 3 charts.",
    ]
    if bk.get("in_kendra_trikona"):
        parts.append("Sphuta sits in a kendra or trikona of saptamsha - children can bring comfort and luxury.")
    elif bk.get("in_trik"):
        parts.append("Sphuta in a trik house of saptamsha - physical or karmic strain around progeny needs remedies.")
    if not bk.get("promise_ok"):
        parts.append("Pair sphuta with Santana tithi and D7 lagna before treating fertility as fully open.")
    return {
        "title": "Fertility sphuta (BS / KS)",
        "text": " ".join(parts),
        "tone": "green" if bk.get("promise_ok") else "amber",
        "theme_id": "beeja",
    }


def _count_card(analysis: dict) -> dict:
    cc = analysis.get("child_count", {})
    band = cc.get("band", "unclear")
    stop = cc.get("stop_reason", "")
    text = f"This chart points to {band}."
    if stop:
        text += f" {stop}"
    bahu = analysis.get("extras", {}).get("bahu_putra", {})
    if bahu.get("active"):
        text += " Bahu Putra yoga indicators suggest the upper band is possible if dasha supports."
    kak = analysis.get("extras", {}).get("kakvandhya", {})
    if kak.get("active"):
        text += " Kakvandhya yoga warns only one child or difficulty conceiving again - treat count as capped."
    text += " Mother chart weighs heavily on count; father chart on sex."
    tone = "green" if cc.get("count_score", 0) >= 2 else ("amber" if cc.get("count_score", 0) == 1 else "neutral")
    return {"title": "Number of children", "text": text, "tone": tone, "theme_id": "count"}


def _timing_card(analysis: dict) -> dict:
    timing = analysis.get("children_timing_detail", {})
    return {
        "title": "Timing of childbirth",
        "text": timing_client_paragraph(timing) if timing else "Timing needs dasha tables from the birth extract.",
        "tone": "green",
        "theme_id": "timing",
    }


def _gender_cards(analysis: dict) -> list[dict]:
    cards = []
    for g in analysis.get("child_genders", [])[:3]:
        idx = g.get("child_index", 1)
        ord_ = {1: "First", 2: "Second", 3: "Third"}.get(idx, f"{idx}th")
        cards.append({
            "title": f"{ord_} child - gender indication",
            "text": (
                f"{ord_} child reads as a {g.get('label', 'mixed')} indication "
                f"({g.get('method', 'child-house decider rule')}). Confirm after birth - dual signs and Mercury/Saturn can swing either way."
            ),
            "tone": "neutral",
            "theme_id": f"gender_{idx}",
        })
    return cards


def _grandchildren_card(analysis: dict) -> dict:
    gc = analysis.get("extras", {}).get("grandchildren", {})
    worship = gc.get("worship_lord", "")
    text = gc.get("text", "Grandchildren theme follows the saptamsha ninth house.")
    if worship:
        text += f" For progeny blessings, worship connected with {worship} (ninth lord of saptamsha) is the traditional remedy."
    tone = {"strong": "green", "good": "green", "weak": "amber"}.get(gc.get("level", "mixed"), "neutral")
    return {"title": "Grandchildren", "text": text, "tone": tone, "theme_id": "grandchildren"}


def _twins_card(analysis: dict) -> dict | None:
    tw = analysis.get("extras", {}).get("twins", {})
    if not tw.get("hits") and not tw.get("likely"):
        return None
    if tw.get("likely"):
        text = "Twin or multiple-birth indicators are strong: " + "; ".join(tw["hits"][:3]) + "."
    else:
        text = "Some twin signatures exist but are not dominant: " + "; ".join(tw["hits"][:2]) + "."
    return {
        "title": "Twins / multiple birth",
        "text": text,
        "tone": "amber" if tw.get("likely") else "neutral",
        "theme_id": "twins",
    }


def _worthy_card(analysis: dict) -> dict:
    wc = analysis.get("extras", {}).get("worthy_child", {})
    return {
        "title": "Worthy / distinguished child",
        "text": wc.get("text", "Raj yoga from the first child-house is moderate."),
        "tone": "green" if wc.get("strong") else "neutral",
        "theme_id": "worthy",
    }


def _happiness_card(analysis: dict) -> dict:
    h4 = analysis.get("h4_score", 0)
    jup = analysis.get("jupiter_d7_house", 0)
    if h4 >= 1 and jup in (1, 5, 9):
        text = (
            "You are likely to draw real joy and pride from your children. "
            "The saptamsha fourth house is supported and Jupiter sits well - affection and respect can grow over the years."
        )
        tone = "green"
    elif h4 <= -1:
        text = (
            "Happiness from children comes with worry or emotional cost. "
            "The saptamsha fourth house is stressed - invest deliberately in communication and boundaries."
        )
        tone = "amber"
    else:
        text = (
            "Happiness from children depends on how you nurture the bond. "
            "The saptamsha fourth house is neutral - daily kindness matters more than the chart alone."
        )
        tone = "green"
    return {"title": "Happiness from children", "text": text, "tone": tone, "theme_id": "happiness"}


def _bond_card(analysis: dict) -> dict | None:
    bd = analysis.get("extras", {}).get("bond_strain", {})
    if not bd.get("strained") and not bd.get("hits"):
        return None
    text = "Parent-child bond needs conscious work: " + "; ".join(bd.get("hits", [])[:2]) + "."
    return {"title": "Parent-child bond", "text": text, "tone": "amber", "theme_id": "bond"}


def _health_card(analysis: dict) -> dict:
    risk = analysis.get("health_risk", 0)
    if risk >= 55:
        text = (
            "Child health needs proactive care in this map. "
            "Sixth and eighth houses from the child axis in saptamsha carry malefic weight - schedule prevention, not panic."
        )
        tone = "amber"
    elif risk >= 30:
        text = (
            "Some health vigilance around children is wise. "
            "One saptamsha stress point on the child axis suggests watchful parenting during harsh dasha years."
        )
        tone = "amber"
    else:
        text = (
            "No strong child-health alarm in saptamsha. "
            "Routine care and calm response to illness are enough unless dasha of afflicted sixth or eighth lords runs."
        )
        tone = "green"
    return {"title": "Children's health", "text": text, "tone": tone, "theme_id": "health"}


def _profession_card(analysis: dict) -> dict:
    h10 = analysis.get("h10_score", 0)
    follows = analysis.get("follows_parent_profession", False)
    nature = analysis.get("child_nature", "")
    parts = [f"Children tend to be {nature} (saptamsha lagna lord tone)."]
    if follows:
        parts.append(
            "A strong saptamsha lagna lord suggests at least one child follows the parent's profession or public path."
        )
    elif h10 >= 1:
        parts.append(
            "The saptamsha tenth house is supported - children may do well professionally and remember you kindly later."
        )
    else:
        parts.append(
            "Children may succeed on their own terms rather than copying your career - the saptamsha tenth house is mixed."
        )
    tone = "green" if h10 >= 0 or follows else "neutral"
    return {"title": "Children's nature & profession", "text": " ".join(parts), "tone": tone, "theme_id": "profession"}


def _house_extra_cards(analysis: dict) -> list[dict]:
    hx = analysis.get("extras", {}).get("house_extras", {})
    if not hx:
        return []
    return [
        {
            "title": "Values & inheritance",
            "text": hx.get("values_inheritance", {}).get("text", ""),
            "tone": "green" if hx.get("values_inheritance", {}).get("score", 0) >= 0 else "amber",
            "theme_id": "values",
        },
        {
            "title": "Gains from children",
            "text": hx.get("gains_from_children", {}).get("text", ""),
            "tone": "green" if hx.get("gains_from_children", {}).get("score", 0) >= 0 else "neutral",
            "theme_id": "gains",
        },
        {
            "title": "Upbringing & expenses",
            "text": hx.get("upbringing_expense", {}).get("text", ""),
            "tone": "amber" if hx.get("upbringing_expense", {}).get("score", 0) < 0 else "green",
            "theme_id": "expenses",
        },
    ]


def _delay_card(analysis: dict) -> dict | None:
    if not analysis.get("saturn_delay"):
        return None
    relief = analysis.get("saturn_delay_relief")
    text = (
        "Saturn touches saptamsha lagna, fifth, or ninth - classical saptamsha rules read a wait before conception. "
        + ("Benefic relief on Saturn shortens the delay." if relief else "Without benefic relief the wait can stretch into the thirties.")
    )
    return {"title": "Delay factor", "text": text, "tone": "amber", "theme_id": "delay"}


def _adoption_card(analysis: dict) -> dict | None:
    ad = analysis.get("extras", {}).get("adoption", {})
    if not ad.get("active") or not ad.get("text"):
        return None
    return {"title": "Adoption path", "text": ad["text"], "tone": "neutral", "theme_id": "adoption"}


def saptamsha_client_cards(analysis: dict, female: bool = False) -> list[dict]:
    if analysis.get("error"):
        return []

    ordered: list[dict | None] = [
        _promise_card(analysis),
        _count_card(analysis),
        _santana_card(analysis),
        _beeja_card(analysis, female),
        _delay_card(analysis),
        _adoption_card(analysis),
        _timing_card(analysis),
        _grandchildren_card(analysis),
        _worthy_card(analysis),
        _twins_card(analysis),
        *_gender_cards(analysis),
        _happiness_card(analysis),
        _bond_card(analysis),
        _health_card(analysis),
        _profession_card(analysis),
        *_house_extra_cards(analysis),
    ]
    return [c for c in ordered if c]


def render_saptamsha_section(analysis: dict, female: bool = False) -> str:
    if analysis.get("error"):
        return f"<div class='pred-card amber'><div class='pred-body'>{_e(analysis['error'])}</div></div>"

    d7 = analysis.get("d7_lagna", "")
    parts = [
        "<p class='fine'>Educational astrology only (Goel, Predict with Saptamsha).</p>",
        f"<div class='callout'><p class='pred'>Saptamsha (D7) is the final word on children in this system - "
        f"your saptamsha lagna is <strong>{_e(d7)}</strong>. "
        "Birth fifth house and Jupiter start the story; D7 confirms promise, count, sex, timing, grandchildren, health, and how children treat you.</p></div>",
    ]

    cards = saptamsha_client_cards(analysis, female)
    if not cards:
        parts.append("<div class='pred-card neutral'><div class='pred-body'>Insufficient D7 data for predictions.</div></div>")
    else:
        for c in cards:
            parts.append(f"<div class='pred-card {c['tone']}'>")
            parts.append(f"<div class='pred-head'>{_e(c['title'])}</div>")
            parts.append(f"<div class='pred-body'><p>{_e(c['text'])}</p></div></div>")

    return "\n".join(parts)
