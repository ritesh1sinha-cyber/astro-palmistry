#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Book-backed rule tables for daily Moon guide (no invented lore)."""
from __future__ import annotations

import json
from pathlib import Path

from gemstone_remedy import GEM_DATA

BASE_DIR = Path(__file__).resolve().parent

# Woods rules23 / numerology_skill.md lucky series (root digit -> list)
LUCKY_SERIES: dict[int, list[int]] = {
    1: [1, 10, 19, 28, 37, 46],
    2: [2, 11, 20, 29, 38, 47],
    3: [3, 12, 21, 30, 39, 48],
    4: [4, 13, 22, 31, 40, 49],
    5: [5, 14, 23, 32, 41, 50],
    6: [6, 15, 24, 33, 42, 51],
    7: [7, 16, 25, 34, 43, 52],
    8: [8, 17, 26, 35, 44, 53],
    9: [9, 18, 27, 36, 45, 54],
}

# Classical 9-fold Tarabala (count from janma nakshatra) - action rules
# Sources: standard panchang Tarabala; names align Complete Indian Predictive OCR (Sampat, Sadhak, Mitr...)
TARABALA_RULES: dict[int, dict] = {
    1: {
        "name": "Janma",
        "tone": "caution",
        "summary": "Birth-star return - conserve vitality.",
        "dos": [
            ("Rest, hydrate, and complete unfinished chores only.", "Tarabala/Janma - classical panchang"),
            ("Offer water or milk Monday-style if Moon is nakshatra lord.", "rules40 Moon day discipline"),
        ],
        "donts": [
            ("Do not inaugurate new projects, sign major contracts, or open new accounts.", "Tarabala/Janma"),
            ("Avoid long-distance travel unless urgent.", "Tarabala/Janma"),
        ],
    },
    2: {
        "name": "Sampat",
        "tone": "auspicious",
        "summary": "Wealth-star - gains through steady effort.",
        "dos": [
            ("Collect pending payments; reconcile one ledger line.", "Tarabala/Sampat - Complete Indian Predictive OCR"),
            ("Bank or invest only after double-checking figures.", "Tarabala/Sampat"),
        ],
        "donts": [
            ("Do not lend large sums on verbal trust today.", "Tarabala/Sampat caution"),
        ],
    },
    3: {
        "name": "Vipat",
        "tone": "caution",
        "summary": "Obstacle-star - friction in plans.",
        "dos": [
            ("Keep backup plans for commutes and meetings.", "Tarabala/Vipat"),
        ],
        "donts": [
            ("Avoid risky travel routes and sharp deadlines.", "Tarabala/Vipat - OCR notes 3rd from Janma as Vipat"),
            ("Postpone equipment purchases unless essential.", "Tarabala/Vipat"),
        ],
    },
    4: {
        "name": "Kshema",
        "tone": "auspicious",
        "summary": "Comfort-star - stability themes.",
        "dos": [
            ("Strengthen home or workspace order - one concrete fix.", "Tarabala/Kshema"),
            ("Eat on time; protect sleep rhythm.", "Tarabala/Kshema"),
        ],
        "donts": [
            ("Do not ignore minor health niggles.", "Tarabala/Kshema"),
        ],
    },
    5: {
        "name": "Pratyari",
        "tone": "caution",
        "summary": "Enemy-star - interpersonal static.",
        "dos": [
            ("Listen first in debates; document agreements in writing.", "Tarabala/Pratyari"),
        ],
        "donts": [
            ("Avoid provocative posts, sarcasm, and legal threats.", "Tarabala/Pratyari - OCR 5th from Janma"),
        ],
    },
    6: {
        "name": "Sadhaka",
        "tone": "auspicious",
        "summary": "Achievement-star - effort converts.",
        "dos": [
            ("Finish one competitive task before sunset.", "Tarabala/Sadhaka - Complete Indian Predictive OCR"),
            ("Schedule health or fitness discipline early.", "Tarabala/Sadhaka"),
        ],
        "donts": [
            ("Do not scatter effort across too many open tasks.", "Tarabala/Sadhaka"),
        ],
    },
    7: {
        "name": "Vadha",
        "tone": "caution",
        "summary": "Danger-star - trim exposure.",
        "dos": [
            ("Handle routine work; keep stakes low.", "Tarabala/Vadha"),
        ],
        "donts": [
            ("Avoid elective medical procedures and high-adrenaline gambles.", "Tarabala/Vadha - OCR 7th from Janma"),
            ("Defer hostile negotiations.", "Tarabala/Vadha"),
        ],
    },
    8: {
        "name": "Mitra",
        "tone": "auspicious",
        "summary": "Friend-star - alliances help.",
        "dos": [
            ("Meet allies, mentors, or peers for a focused working session.", "Tarabala/Mitra - OCR Mitr"),
            ("Send one gratitude message to a supporter.", "Tarabala/Mitra"),
        ],
        "donts": [
            ("Do not isolate when a collaboration would solve the block.", "Tarabala/Mitra"),
        ],
    },
    9: {
        "name": "Parama Mitra",
        "tone": "auspicious",
        "summary": "Peak friend-star - among the brighter windows.",
        "dos": [
            ("Schedule an auspicious act you have delayed (study, prayer, client pitch).", "Tarabala/Parama Mitra - OCR ParamMitra"),
        ],
        "donts": [
            ("Do not waste the window on passive scrolling.", "Tarabala/Parama Mitra"),
        ],
    },
}

CHANDRA_RULES: dict[int, dict] = {
    1: {"name": "Janma Rasi", "tone": "caution", "dos": [("Move gently; prioritise emotional honesty with yourself.", "Chandrabal/Janma Rasi")], "donts": [("Avoid emotional ultimatums.", "Chandrabal/Janma Rasi")]},
    2: {"name": "Sampat Rasi", "tone": "auspicious", "dos": [("Voice financial boundaries kindly.", "Chandrabal/Sampat")], "donts": [("Avoid impulse spending to soothe mood.", "Chandrabal/Sampat")]},
    3: {"name": "Vipat Rasi", "tone": "caution", "dos": [("Confirm commute and gadget backups.", "Chandrabal/Vipat")], "donts": [("Avoid sarcastic replies in chat.", "Chandrabal/Vipat")]},
    4: {"name": "Kshema Rasi", "tone": "auspicious", "dos": [("Tidy one home corner; eat comfort food mindfully.", "Chandrabal/Kshema")], "donts": [("Avoid major home fights when tired.", "Chandrabal/Kshema")]},
    5: {"name": "Pratyari Rasi", "tone": "caution", "dos": [("Channel creativity without speculative bets.", "Chandrabal/Pratyari")], "donts": [("Avoid romantic or lottery ultimatums.", "Chandrabal/Pratyari")]},
    6: {"name": "Sadhaka Rasi", "tone": "auspicious", "dos": [("Close one service task early; hydrate.", "Chandrabal/Sadhaka")], "donts": [("Avoid skipping meals while grinding.", "Chandrabal/Sadhaka")]},
    7: {"name": "Vadha Rasi", "tone": "caution", "dos": [("Listen more than you lobby in partnerships.", "Chandrabal/Vadha")], "donts": [("Avoid legal ultimatums in partnerships.", "Chandrabal/Vadha")]},
    8: {"name": "Mitra Rasi", "tone": "auspicious", "dos": [("Research one buried question calmly.", "Chandrabal/Mitra")], "donts": [("Avoid sharing joint secrets casually.", "Chandrabal/Mitra")]},
    9: {"name": "Parama Mitra Rasi", "tone": "auspicious", "dos": [("Read or study ten pages; thank a teacher figure.", "Chandrabal/Parama Mitra")], "donts": [("Avoid cynical takes on faith or study.", "Chandrabal/Parama Mitra")]},
}

# Three rotating variants per house-from-Moon (Bhardwaj gochar house themes + rules10 house karakatva)
HOUSE_ACTIONS: dict[int, dict[str, list[tuple[str, str]]]] = {
    1: {
        "dos": [
            ("Set one visible self-care act before noon.", "Gochar 1st-from-Moon / identity"),
            ("Dress with intention aligned to weekday lord colour.", "rules40/41 weekday"),
        ],
        "donts": [("Avoid harsh self-criticism at first mirror glance.", "Gochar 1st-from-Moon")],
    },
    2: {
        "dos": [("Reconcile one wallet or family-speech topic.", "Gochar 2nd-from-Moon / wealth speech")],
        "donts": [("Avoid comfort shopping without a list.", "Gochar 2nd-from-Moon")],
    },
    3: {
        "dos": [("Send the postponed message; short walk or sibling call.", "Gochar 3rd-from-Moon / courage")],
        "donts": [("Avoid triple-booking your calendar.", "Gochar 3rd-from-Moon")],
    },
    4: {
        "dos": [("Cook or eat something that feels like home.", "Gochar 4th-from-Moon / nest")],
        "donts": [("Avoid property arguments when fatigued.", "Gochar 4th-from-Moon")],
    },
    5: {
        "dos": [("Creative play 20 minutes - music, sketch, or child time.", "Gochar 5th-from-Moon / creativity")],
        "donts": [("Avoid speculative bets today.", "Gochar 5th-from-Moon")],
    },
    6: {
        "dos": [("Finish one health or service task before others interrupt.", "Gochar 6th-from-Moon / effort")],
        "donts": [("Avoid skipping meals during chore marathons.", "Gochar 6th-from-Moon")],
    },
    7: {
        "dos": [("Listen fully in a partnership talk; note agreements.", "Gochar 7th-from-Moon / contracts")],
        "donts": [("Avoid signing partnership papers while reactive.", "Gochar 7th-from-Moon")],
    },
    8: {
        "dos": [("Update insurance, passwords, or joint-money detail.", "Gochar 8th-from-Moon / research")],
        "donts": [("Avoid occult experiments or revenge plots.", "Gochar 8th-from-Moon")],
    },
    9: {
        "dos": [
            ("Thank a mentor; read ten uplifting pages.", "Gochar 9th-from-Moon / fortune"),
            ("Plan pilgrimage, course, or father-linked call if pending.", "Gochar 9th-from-Moon / dharma"),
        ],
        "donts": [
            ("Avoid cynical hot takes on faith or study.", "Gochar 9th-from-Moon"),
            ("Do not force long-distance travel without Tarabala support.", "Gochar 9th + Tarabala gate"),
        ],
    },
    10: {
        "dos": [("Ship one career deliverable; polish public wording.", "Gochar 10th-from-Moon / visibility")],
        "donts": [("Avoid public fights with authority.", "Gochar 10th-from-Moon")],
    },
    11: {
        "dos": [("Ping a network ally; note one income idea without over-promising.", "Gochar 11th-from-Moon / gains")],
        "donts": [("Avoid boasting about gains not yet secured.", "Gochar 11th-from-Moon")],
    },
    12: {
        "dos": [("Donate or discard one item; protect sleep.", "Gochar 12th-from-Moon / release")],
        "donts": [("Avoid late-night scrolling that steals rest.", "Gochar 12th-from-Moon")],
    },
}

GOCHAR_MOON_RULES = {
    "auspicious": ("Lean into emotional initiatives - Moon gochar house is in Bhardwaj auspicious set.", "Bhardwaj/gochar_auspicious Moon"),
    "inauspicious": ("Defer emotional ultimatums - Moon gochar house is in Bhardwaj inauspicious set.", "Bhardwaj/gochar_inauspicious Moon"),
}

GOCHAR_SUN_RULES = {
    "auspicious": ("Use late morning for one visible authority task.", "Bhardwaj/gochar_auspicious Sun"),
    "inauspicious": ("Keep Sun-themed power moves modest today.", "Bhardwaj/gochar_inauspicious Sun"),
}

GOCHAR_MERCURY_RULES = {
    "auspicious": ("Send the important email or study block before lunch.", "Bhardwaj/gochar_auspicious Mercury"),
    "inauspicious": ("Read fine print twice; avoid rushed signatures.", "Bhardwaj/gochar_inauspicious Mercury"),
}

SAV_RULES = {
    "low": ("Proof-stack promises - Moon crosses a sub-25 SAV sign (rules10).", "rules10/SAV below 25"),
    "high": ("Push one deliverable - Moon crosses 30+ SAV sign (rules10).", "rules10/SAV 30+"),
}


def _load_nakshatra_effects() -> dict[str, str]:
    path = BASE_DIR / "bhardwaj_book_data.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8")).get("nakshatra_effects", {})
    return {}


def color_from_gem_rules(planet: str) -> tuple[str, str]:
    """Extract wear/colour hint from rules40/41 GEM_DATA behavior - no invented palette."""
    g = GEM_DATA.get(planet, {})
    behavior = g.get("behavior", "")
    charity = g.get("charity", "")
    sub = g.get("sub", "")
    # Parse explicit wear hints from behavior
    bl = behavior.lower()
    if "wear white" in bl:
        color = "white or pearl"
    elif "wear red" in bl:
        color = "red or coral"
    elif "green clothes" in bl or "green" in bl:
        color = "green"
    elif "yellow" in bl:
        color = "yellow or saffron"
    elif "black" in bl or "blue" in bl:
        color = "navy or charcoal"
    else:
        color = sub.split("/")[0].strip() if sub else "neutral cream"
    return color, f"rules40/41 {planet} behavior: {behavior[:60]}"


def pick_variant(items: list, seed: int) -> tuple[str, str] | None:
    if not items:
        return None
    return items[seed % len(items)]


def nakshatra_daily_snippet(transit_nak: str, seed: int, kind: str = "do") -> tuple[str, str] | None:
    fx = _load_nakshatra_effects().get(transit_nak, "")
    if not fx:
        return None
    parts = [p.strip() for p in fx.replace("  ", " ").split(".") if len(p.strip()) > 20]
    if not parts:
        return fx[:120], f"Bhardwaj/nakshatra_effects/{transit_nak}"
    caution_words = ("sin", "suffer", "pain", "disease", "stress", "loss", "enemy")
    if kind == "do":
        pool = [p for p in parts if not any(w in p.lower() for w in caution_words)] or parts[:1]
    else:
        pool = [p for p in parts if any(w in p.lower() for w in caution_words)]
        if not pool:
            return None
    p = pool[seed % len(pool)]
    return p + ".", f"Bhardwaj/nakshatra_effects/{transit_nak}"


def ad_remedy_line(ad_lord: str) -> tuple[str, str] | None:
    g = GEM_DATA.get(ad_lord)
    if not g:
        return None
    return g.get("charity", g.get("behavior", "")), f"rules40/41 antardasha lord {ad_lord}"
