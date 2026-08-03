#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Goel Trishamsha - client-facing prediction cards (rules15)."""
from __future__ import annotations

import html
from typing import Any

from goel_stress_timing import timing_client_paragraph


def _e(s: str) -> str:
    return html.escape(str(s))


def _fortune_card(analysis: dict) -> dict:
    ex = analysis.get("extras", {})
    profile = ex.get("fortune_profile", {})
    tone_map = {
        "fortunate": "green",
        "mixed_fortunate_deeds": "green",
        "fortunate_self_swing": "neutral",
        "fortunate_self_risk": "amber",
        "mixed": "neutral",
        "mixed_self_risk": "amber",
        "unfortunate_redeemed": "amber",
        "unfortunate_partial": "amber",
        "unfortunate_self": "amber",
    }
    label = profile.get("label", "mixed")
    text = profile.get("text", "")
    facts = analysis.get("lagna_facts", [])
    if facts:
        text += " Signs: " + "; ".join(facts[:3]) + "."
    return {
        "title": "Fortune vs misfortune (Trishamsha lagna)",
        "text": text,
        "tone": tone_map.get(label, "neutral"),
        "theme_id": "fortune",
    }


def _lagna_lord_card(analysis: dict) -> dict:
    lord = analysis.get("d30_lagna_lord", "")
    h = analysis.get("d30_lagna_lord_house", 0)
    ex = analysis.get("extras", {})
    ll_tone = ex.get("ll_tone", "mixed")
    facts = ex.get("ll_facts", [])
    if ll_tone == "benefic":
        text = (
            f"Trishamsha lagna lord {lord} in house {h} is strong - you can fulfill the promise and "
            "fight adversity without inviting extra trouble by your own deeds."
        )
        tone = "green"
    elif ll_tone == "malefic":
        text = (
            f"Trishamsha lagna lord {lord} in house {h} is afflicted - Goel warns that hostile sub-periods "
            "can multiply misfortune through your own choices. Slow down and remedy this lord."
        )
        tone = "amber"
    else:
        text = (
            f"Trishamsha lagna lord {lord} in house {h} is mixed - ability to convert adversity into learning varies by dasha."
        )
        tone = "neutral"
    if facts:
        text += " " + "; ".join(facts[:2]) + "."
    return {"title": "Lagna lord action (focal)", "text": text, "tone": tone, "theme_id": "ll"}


def _eighth_house_card(analysis: dict) -> dict:
    h8 = analysis.get("h8_score", 0)
    lord = analysis.get("lord8_d30", "")
    h = analysis.get("lord8_d30_house", 0)
    if h8 >= 1:
        text = (
            f"Trishamsha eighth house is supported - sudden setbacks are easier to absorb. "
            f"Eighth lord {lord} in house {h} needs routine remedial attention in its dasha."
        )
        tone = "green"
    elif h8 <= -1:
        text = (
            f"Malefic weight on Trishamsha eighth house - chronic setbacks, hidden fears, or relapse tone. "
            f"Eighth lord {lord} in house {h} is a focal remedial planet."
        )
        tone = "amber"
    else:
        text = (
            f"Trishamsha eighth house is neutral - outcomes depend on dasha lords and conduct. "
            f"Eighth lord {lord} sits in house {h}."
        )
        tone = "neutral"
    return {"title": "Eighth house (focal)", "text": text, "tone": tone, "theme_id": "h8"}


def _eighth_lord_card(analysis: dict) -> dict:
    ex = analysis.get("extras", {})
    l8_tone = ex.get("l8_tone", "mixed")
    lord = analysis.get("lord8_d30", "")
    facts = ex.get("l8_facts", [])
    text = (
        f"Eighth lord {lord} examination: "
        + (
            "well connected - source of trouble can be managed with remedies."
            if l8_tone == "benefic"
            else (
                "afflicted - fear, surgery, or sudden loss themes need prevention."
                if l8_tone == "malefic"
                else "mixed - stress comes in waves rather than one fixed channel."
            )
        )
    )
    if facts:
        text += " " + "; ".join(facts[:2]) + "."
    tone = "green" if l8_tone == "benefic" else ("amber" if l8_tone == "malefic" else "neutral")
    return {"title": "Eighth lord (focal)", "text": text, "tone": tone, "theme_id": "l8"}


def _moon_card(analysis: dict) -> dict:
    h = analysis.get("moon_d30_house", 0)
    ex = analysis.get("extras", {}).get("character_axis", {})
    text = ex.get("text", f"Moon in Trishamsha house {h}.")
    tone = "amber" if h in (6, 8, 12) else ("green" if h in (1, 4, 7, 10) else "neutral")
    return {"title": "Moon (focal)", "text": text, "tone": tone, "theme_id": "moon"}


def _problem_lords_card(analysis: dict) -> dict | None:
    pl = analysis.get("extras", {}).get("problem_lords", {})
    if not pl.get("text"):
        return None
    return {"title": "Source of trouble (D1 6th & 8th lords)", "text": pl["text"], "tone": "amber", "theme_id": "problem"}


def _tattva_card(analysis: dict) -> dict | None:
    tc = analysis.get("extras", {}).get("tattva_clash", {})
    if not tc.get("clash"):
        return None
    return {"title": "Tattva clash", "text": tc["text"], "tone": "amber", "theme_id": "tattva"}


def _kendra_card(analysis: dict) -> dict | None:
    kt = analysis.get("extras", {}).get("kendra_trikona", {})
    if not kt.get("text"):
        return None
    return {"title": "Kendra & trikona tone", "text": kt["text"], "tone": kt.get("tone", "neutral"), "theme_id": "kendra"}


def _marriage_card(analysis: dict) -> dict:
    mf = analysis.get("extras", {}).get("marriage_friction", {})
    text = mf.get("text", "Marriage quality in Trishamsha needs Navamsha cross-check.")
    tone = "amber" if mf.get("harsh") else ("green" if "not the main" in text else "neutral")
    return {"title": "Marriage friction (D30)", "text": text, "tone": tone, "theme_id": "marriage"}


def _early_marriage_card(analysis: dict) -> dict | None:
    em = analysis.get("extras", {}).get("early_marriage", {})
    if not em.get("active"):
        return None
    return {"title": "Early union flag", "text": em["text"], "tone": "neutral", "theme_id": "early_marriage"}


def _timing_card(analysis: dict) -> dict:
    timing = analysis.get("stress_timing_detail", {})
    return {
        "title": "Adversity timing",
        "text": timing_client_paragraph(timing) if timing else "Timing needs dasha tables from the birth extract.",
        "tone": "amber" if timing.get("age_tone") == "heavy" else "neutral",
        "theme_id": "timing",
    }


def _overlap_card(analysis: dict) -> dict | None:
    if not analysis.get("d1_lagna_stress_overlap"):
        return None
    return {
        "title": "Birth-Trishamsha lagna overlap",
        "text": (
            "A planet stressing both birth lagna and Trishamsha lagna is a classic Goel misfortune marker - "
            "remedy that graha and avoid major decisions in its hostile antardashas."
        ),
        "tone": "amber",
        "theme_id": "overlap",
    }


def _house_extra_cards(analysis: dict) -> list[dict]:
    hx = analysis.get("extras", {}).get("house_extras", {})
    if not hx:
        return []
    out = []
    for key, title in (("comfort_morals", "Character & home peace (D30 4th)"), ("loss_isolation", "Losses & isolation (D30 12th)")):
        block = hx.get(key, {})
        if block.get("text"):
            out.append({
                "title": title,
                "text": block["text"],
                "tone": "green" if block.get("score", 0) >= 0 else "amber",
                "theme_id": key,
            })
    return out


def trishamsha_client_cards(analysis: dict) -> list[dict]:
    if analysis.get("error"):
        return []

    ordered: list[dict | None] = [
        _fortune_card(analysis),
        _lagna_lord_card(analysis),
        _eighth_house_card(analysis),
        _eighth_lord_card(analysis),
        _moon_card(analysis),
        _problem_lords_card(analysis),
        _tattva_card(analysis),
        _kendra_card(analysis),
        _marriage_card(analysis),
        _early_marriage_card(analysis),
        _overlap_card(analysis),
        _timing_card(analysis),
        *_house_extra_cards(analysis),
    ]
    return [c for c in ordered if c]


def render_trishamsha_section(analysis: dict) -> str:
    if analysis.get("error"):
        return f"<div class='pred-card amber'><div class='pred-body'>{_e(analysis['error'])}</div></div>"

    d30 = analysis.get("d30_lagna", "")
    parts = [
        "<p class='fine'>Educational astrology only (Goel, Predict with Trishamsha).</p>",
        f"<div class='callout'><p class='pred'>Trishamsha (D30) is Goel's fortune-and-misfortune chart (arista phalam) - "
        f"your Trishamsha lagna is <strong>{_e(d30)}</strong>. "
        "Examination focal points: lagna lord, eighth lord, Moon, and eighth house. "
        "Cross-check Navamsha for marriage; disease lane uses D30 separately when health is asked.</p></div>",
    ]
    for card in trishamsha_client_cards(analysis):
        tone = card.get("tone", "neutral")
        parts.append(
            f"<div class='pred-card {tone}'><div class='pred-title'>{_e(card['title'])}</div>"
            f"<div class='pred-body'>{_e(card['text'])}</div></div>"
        )
    return "\n".join(parts)
