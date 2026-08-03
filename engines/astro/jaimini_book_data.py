#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load jaimini_book_data.json and provide KL / Goel / Jewels lookups."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "jaimini_book_data.json"

NAT_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
NAT_MALEFIC = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}


def load_book(path: Optional[Path] = None) -> dict:
    p = path or DATA_PATH
    if not p.is_file():
        raise FileNotFoundError(f"Run build_jaimini_data.py first - missing {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def lookup_kl_occupation(book: dict, planet: str) -> str:
    return book.get("gems_kl_occupation", {}).get(planet, "")


def lookup_planet_kl_house(book: dict, planet: str, house: int) -> str:
    return book.get("gems_planet_in_kl_house", {}).get(planet, {}).get(str(house), "")


def lookup_kl_house_theme(book: dict, house: int) -> str:
    return book.get("gems_house_themes", {}).get(str(house), "")


def planets_in_kl_house(pc: dict, kl_sign: str, house: int) -> list[str]:
    """Whole-sign: which D1 planets occupy `house` from karakamsa lagna."""
    signs = [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    ]
    if kl_sign not in signs:
        return []
    target = signs[(signs.index(kl_sign) + house - 1) % 12]
    return [nm for nm, v in pc.get("planets", {}).items() if v.get("sign") == target]


def kl_house_of_planet(pc: dict, kl_sign: str, planet: str) -> int:
    signs = [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    ]
    pl = pc.get("planets", {}).get(planet, {})
    sign = pl.get("sign")
    if not sign or kl_sign not in signs:
        return 0
    return (signs.index(sign) - signs.index(kl_sign)) % 12 + 1


def scan_raja_yoga_pairs(karakas: dict, pc: dict, sign_aspects_fn) -> list[str]:
    """Goel rules6 Part E: conjunction or mutual sign aspect among karaka pairs."""
    pairs = [
        ("Atmakarak", "Amatyakarak"), ("Atmakarak", "Putrakaraka"), ("Atmakarak", "Darakaraka"),
        ("Amatyakarak", "Putrakaraka"), ("Amatyakarak", "Darakaraka"),
        ("Putrakaraka", "Darakaraka"),
    ]
    hits = []
    for a, b in pairs:
        sa = karakas.get(a, {}).get("sign")
        sb = karakas.get(b, {}).get("sign")
        if not sa or not sb:
            continue
        if sa == sb or sign_aspects_fn(sa, sb):
            hits.append(
                f"{a} ({karakas[a]['planet']}) + {b} ({karakas[b]['planet']}): "
                f"raja yoga by conjunction or mutual sign aspect."
            )
    return hits


def argala_quality(book: dict, benefic_count: int, malefic_count: int, positions: int) -> str:
    tiers = book.get("jewels_argala_tiers", {})
    if benefic_count >= 2 and positions >= 2:
        return "superior"
    if benefic_count >= 1 and positions >= 2:
        return "above_average"
    if positions >= 1 and malefic_count == 0:
        return "above_average"
    if positions >= 1:
        return "average"
    return "none"
