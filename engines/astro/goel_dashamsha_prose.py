#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Goel Dashamsha - client-facing prediction cards (rules13)."""
from __future__ import annotations

import html
from typing import Any

from goel_career_timing import timing_client_paragraph


def _e(s: str) -> str:
    return html.escape(str(s))


def _inner_drive_card(analysis: dict) -> dict:
    score = analysis.get("d10_lagna_score", 0)
    lagna = analysis.get("d10_lagna", "")
    lord = analysis.get("d10_lagna_lord", "")
    h = analysis.get("d10_lagna_lord_house", 0)
    meaning = analysis.get("d10_lagna_lord_meaning", "")
    if score >= 1:
        tone = "green"
        text = (
            f"Dashamsha lagna {lagna} is supported - your inner career drive is clear. "
            f"Lagna lord {lord} in the {h}th house: {meaning}"
        )
    elif score <= -1:
        tone = "amber"
        text = (
            f"Malefic weight on dashamsha lagna {lagna} - motives at work can be tested or conflict-prone. "
            f"Lagna lord {lord} in the {h}th house still channels effort through {meaning.lower() if meaning else 'that house'}."
        )
    else:
        tone = "neutral"
        text = (
            f"Dashamsha lagna {lagna} is mixed - career path is not fixed in youth. "
            f"Lagna lord {lord} in the {h}th house: {meaning}"
        )
    return {"title": "Inner career drive (D10 lagna)", "text": text, "tone": tone, "theme_id": "inner_drive"}


def _public_face_card(analysis: dict) -> dict:
    lord = analysis.get("lord10_d10", "")
    h = analysis.get("lord10_d10_house", 0)
    meaning = analysis.get("lord10_d10_meaning", "")
    h10 = analysis.get("h10_score", 0)
    tone = "green" if h10 >= 0 else "amber"
    text = (
        f"Outward profession runs through dashamsha tenth lord {lord} in the {h}th house - "
        f"{meaning} "
        f"The visible tenth house is {'supported' if h10 >= 0 else 'under stress'} on the karma chart."
    )
    return {"title": "Public profession (D10 10th)", "text": text, "tone": tone, "theme_id": "public_face"}


def _deity_card(analysis: dict, key: str, title: str) -> dict | None:
    d = analysis.get("extras", {}).get("deities", {}).get(key, {})
    if not d.get("computed"):
        return None
    strong = d.get("ruler_strong", False)
    text = (
        f"{d.get('planet', key)} falls in the {d.get('deity')} segment ({d.get('flavour')}). "
        f"Presiding ruler {d.get('ruler')} is {'well placed' if strong else 'mixed'} in dashamsha - "
        f"{'the career flavour can deliver' if strong else 'strengthen that ruler for the theme to succeed'}."
    )
    return {"title": title, "text": text, "tone": "green" if strong else "neutral", "theme_id": f"deity_{key}"}


def _saturn_mode_card(analysis: dict) -> dict:
    sc = analysis.get("extras", {}).get("saturn_career", {})
    modes = sc.get("modes", {})
    text = sc.get("verdict", "") + (
        f" (Birth: {modes.get('D1', '?')}; Navamsha: {modes.get('D9', '?')}; Dashamsha: {modes.get('D10', '?')})."
        if modes else ""
    )
    mode = sc.get("mode", "mixed")
    tone = "green" if mode in ("independent", "shift_to_independent") else ("amber" if mode == "service" else "neutral")
    return {"title": "Self-employed vs service", "text": text, "tone": tone, "theme_id": "saturn_mode"}


def _independence_card(analysis: dict) -> dict:
    pp = analysis.get("extras", {}).get("pp_independence", {})
    return {
        "title": "Professional independence",
        "text": pp.get("text", ""),
        "tone": "green" if pp.get("level") == "strong" else ("neutral" if pp.get("level") == "moderate" else "amber"),
        "theme_id": "independence",
    }


def _capricorn_card(analysis: dict) -> dict | None:
    cap = analysis.get("extras", {}).get("capricorn", {})
    if not cap.get("active") or not cap.get("text"):
        return None
    return {"title": "Status amplifier (Capricorn)", "text": cap["text"], "tone": "green", "theme_id": "capricorn"}


def _timing_card(analysis: dict) -> dict:
    timing = analysis.get("career_timing_detail", {})
    return {
        "title": "Career rise & job-change timing",
        "text": timing_client_paragraph(timing) if timing else "Timing needs dasha tables from the birth extract.",
        "tone": "green",
        "theme_id": "timing",
    }


def _fame_card(analysis: dict) -> dict | None:
    fam = analysis.get("extras", {}).get("fame_11th", {})
    if not fam.get("text"):
        return None
    return {
        "title": "Fame & gains",
        "text": fam["text"],
        "tone": "green" if fam.get("strong") else "amber",
        "theme_id": "fame",
    }


def _upachaya_card(analysis: dict) -> dict | None:
    up = analysis.get("extras", {}).get("upachaya", {})
    if not up.get("text"):
        return None
    return {
        "title": "Karmic rise (upachaya)",
        "text": up["text"],
        "tone": "green" if up.get("strong") else "neutral",
        "theme_id": "upachaya",
    }


def _fall_card(analysis: dict) -> dict | None:
    fr = analysis.get("extras", {}).get("fall_risk", {})
    if fr.get("level", "low") == "low" or not fr.get("text"):
        return None
    return {
        "title": "Fall / scandal watch",
        "text": fr["text"],
        "tone": "amber" if fr.get("level") == "moderate" else "amber",
        "theme_id": "fall",
    }


def _education_card(analysis: dict) -> dict | None:
    ed = analysis.get("extras", {}).get("education_link", {})
    if not ed.get("computed"):
        return None
    return {"title": "Education to career", "text": ed["text"], "tone": "neutral", "theme_id": "education"}


def _avocation_card(analysis: dict) -> dict | None:
    av = analysis.get("extras", {}).get("avocation", {})
    if not av.get("text"):
        return None
    return {"title": "Profession type", "text": av["text"], "tone": "green", "theme_id": "avocation"}


def _boss_friction_card(analysis: dict) -> dict | None:
    if not analysis.get("boss_friction"):
        return None
    return {
        "title": "Boss & authority friction",
        "text": (
            "Dashamsha lagna lord in the fifth house - clever work but unstable bosses or authority clashes. "
            "Build skills under others before independence; benefic dasha can stabilise."
        ),
        "tone": "amber",
        "theme_id": "boss",
    }


def _sudden_rise_card(analysis: dict) -> dict | None:
    if not analysis.get("sudden_rise"):
        return None
    return {
        "title": "Sudden rise potential",
        "text": (
            "Third-tenth link or Mars on dashamsha career angles - courage, transfers, media, or contracts "
            "can spike your name quickly when the right dasha runs."
        ),
        "tone": "green",
        "theme_id": "sudden_rise",
    }


def _house_extra_cards(analysis: dict) -> list[dict]:
    hx = analysis.get("extras", {}).get("house_extras", {})
    if not hx:
        return []
    mapping = [
        ("speech_wealth", "Speech & family business"),
        ("public_base", "Public acceptance & office base"),
        ("partnership", "Partnerships & corporates"),
        ("foreign_retreat", "Foreign / behind-the-scenes work"),
    ]
    cards = []
    for key, title in mapping:
        block = hx.get(key, {})
        if block.get("text"):
            cards.append({
                "title": title,
                "text": block["text"],
                "tone": "green" if block.get("score", 0) >= 0 else "amber",
                "theme_id": key,
            })
    return cards


def dashamsha_client_cards(analysis: dict) -> list[dict]:
    if analysis.get("error"):
        return []

    ordered: list[dict | None] = [
        _inner_drive_card(analysis),
        _public_face_card(analysis),
        _deity_card(analysis, "lagna_lord", "Dashamsha deity - lagna lord"),
        _deity_card(analysis, "tenth_lord", "Dashamsha deity - tenth lord"),
        _avocation_card(analysis),
        _saturn_mode_card(analysis),
        _independence_card(analysis),
        _capricorn_card(analysis),
        _upachaya_card(analysis),
        _sudden_rise_card(analysis),
        _timing_card(analysis),
        _fame_card(analysis),
        _education_card(analysis),
        _boss_friction_card(analysis),
        _fall_card(analysis),
        *_house_extra_cards(analysis),
    ]
    return [c for c in ordered if c]


def render_dashamsha_section(analysis: dict) -> str:
    if analysis.get("error"):
        return f"<div class='pred-card amber'><div class='pred-body'>{_e(analysis['error'])}</div></div>"

    d10 = analysis.get("d10_lagna", "")
    parts = [
        "<p class='fine'>Educational astrology only (Goel, Predict with Dashamsha).</p>",
        f"<div class='callout'><p class='pred'>Dashamsha (D10) is the karma chart for meaningful work - "
        f"your dashamsha lagna is <strong>{_e(d10)}</strong>. "
        "Birth tenth house starts the story; D10 confirms profession type, independence, fame, rise/fall, and timing.</p></div>",
    ]
    for card in dashamsha_client_cards(analysis):
        tone = card.get("tone", "neutral")
        parts.append(
            f"<div class='pred-card {tone}'><div class='pred-title'>{_e(card['title'])}</div>"
            f"<div class='pred-body'>{_e(card['text'])}</div></div>"
        )
    return "\n".join(parts)
