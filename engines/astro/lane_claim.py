#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified claim object for multi-lane confluence."""
from __future__ import annotations

from dataclasses import dataclass


DOMAINS = (
    "personality",
    "father",
    "mother",
    "family",
    "career",
    "finance",
    "marriage",
    "children",
    "health",
    "property",
    "future",
)

DOMAIN_TITLE = {
    "personality": "Your Personality & Character",
    "father": "Father & the Authority Line",
    "mother": "Mother & Emotional Roots",
    "family": "Siblings & Family Bonds",
    "career": "Career & Profession",
    "finance": "Wealth & Finances",
    "marriage": "Spouse & Marriage",
    "children": "Children & Creativity",
    "health": "Health & Disease",
    "property": "Home & Property",
    "future": "Near Future & Life Direction",
}

SECTION_TO_DOMAIN: dict[str, str] = {
    "intro": "personality",
    "personality": "personality",
    "birth_star": "personality",
    "wiring": "personality",
    "profession": "career",
    "career": "career",
    "ch10": "career",
    "gems_kl_10th": "career",
    "goel_raja_yoga": "career",
    "marriage": "marriage",
    "ch07": "marriage",
    "ch18": "marriage",
    "children": "children",
    "ch05": "children",
    "gems_kl_5th": "children",
    "health": "health",
    "ch06": "health",
    "ch08": "health",
    "ch14": "health",
    "finance": "finance",
    "ch02": "finance",
    "ch11": "finance",
    "property": "property",
    "ch04": "property",
    "gems_kl_4th": "property",
    "travel": "future",
    "ch09": "father",
    "gems_kl_9th": "future",
    "spiritual": "future",
    "gems_kl_12th_moksha": "future",
    "gems_kl_12th_devotion": "future",
    "remedies": "future",
    "dasha": "future",
    "pratyantar": "future",
    "ch15": "future",
    "ch17": "personality",
    "ch19": "personality",
    "goel_karakas": "personality",
    "goel_mindset": "personality",
    "goel_three_lagnas": "personality",
    "siblings": "family",
    "ch03": "family",
    "parents": "family",
    "ch13": "future",
}


@dataclass
class LaneClaim:
    lane: str
    section_id: str
    domain: str
    direction: str  # positive | caution | neutral
    text: str
    timing: str = ""
    tone: str = "neutral"


def tone_to_direction(tone: str) -> str:
    if tone in ("good", "green"):
        return "positive"
    if tone in ("amber", "attention", "red"):
        return "caution"
    return "neutral"


def map_domain(section_id: str, title: str = "") -> str:
    sid = section_id.lower()
    if sid in SECTION_TO_DOMAIN:
        return SECTION_TO_DOMAIN[sid]
    tl = title.lower()
    if "father" in tl or "9th" in tl or "paternal" in tl:
        return "father"
    if "mother" in tl or "4th" in tl or "maternal" in tl:
        return "mother"
    if "sibling" in tl or "brother" in tl or "3rd" in tl:
        return "family"
    if "marriage" in tl or "spouse" in tl or "partner" in tl:
        return "marriage"
    if "child" in tl or "progeny" in tl or "5th" in tl:
        return "children"
    if "career" in tl or "profession" in tl or "10th" in tl:
        return "career"
    if "health" in tl or "6th" in tl or "longevity" in tl:
        return "health"
    if "wealth" in tl or "finance" in tl or "2nd" in tl or "gain" in tl:
        return "finance"
    if "travel" in tl or "foreign" in tl:
        return "future"
    if "home" in tl or "property" in tl:
        return "property"
    if "spiritual" in tl or "moksha" in tl or "karmic" in tl or "remed" in tl:
        return "future"
    if "dasha" in tl or "future" in tl or "timing" in tl or "now" in tl:
        return "future"
    return "personality"
