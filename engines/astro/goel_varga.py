#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Goel / Parashari varga helpers for disease location (D3, D6, D27)."""
from __future__ import annotations

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

FIRE = {0, 4, 8}
EARTH = {1, 5, 9}
AIR = {2, 6, 10}
WATER = {3, 7, 11}


def _idx(sign: str) -> int:
    return SIGNS.index(sign)


def drekkana_sign(sign: str, deg_in_sign: float) -> str:
    """D3: 0-10 same; 10-20 fifth; 20-30 ninth (Goel rules7)."""
    i = _idx(sign)
    if deg_in_sign < 10:
        return SIGNS[i]
    if deg_in_sign < 20:
        return SIGNS[(i + 4) % 12]
    return SIGNS[(i + 8) % 12]


def drekkana_third(deg_in_sign: float) -> int:
    """1=head-neck band, 2=neck-navel, 3=navel-feet within sign segment."""
    if deg_in_sign < 10:
        return 1
    if deg_in_sign < 20:
        return 2
    return 3


def kalaka_origin(deg_in_sign: float) -> str:
    """1st kalaka (internal) vs 2nd kalaka (external) per 5-degree halves."""
    segment = min(int(deg_in_sign / 5), 5)
    return "internal" if segment % 2 == 0 else "external"


def shashthamsha_sign(sign: str, deg_in_sign: float) -> str:
    """Cyclical D6: odd signs from Aries, even from Libra (Goel table p.40)."""
    part = min(int(deg_in_sign / 5), 5)
    start = 0 if _idx(sign) % 2 == 0 else 6
    return SIGNS[(start + part) % 12]


def saptavimshamsha_sign(sign: str, deg_in_sign: float) -> str:
    """D27: element-based start, 27 parts of 16 min 40 sec (30/27 deg)."""
    i = _idx(sign)
    if i in FIRE:
        start = 0
    elif i in EARTH:
        start = 3
    elif i in AIR:
        start = 6
    else:
        start = 9
    part = min(int(deg_in_sign / (30 / 27)), 26)
    return SIGNS[(start + part) % 12]


def house_from_lagna(body_sign: str, lagna: str) -> int:
    return (_idx(body_sign) - _idx(lagna)) % 12 + 1


def house_from_sign(body_sign: str, ref_sign: str) -> int:
    return (_idx(body_sign) - _idx(ref_sign)) % 12 + 1


def navamsha_part(sign: str, deg_in_sign: float) -> int:
    """Navamsha pada 1-9 within sign (3 deg 20 min each)."""
    return min(int(deg_in_sign / (30 / 9)), 8) + 1


def navamsha_sign(sign: str, deg_in_sign: float) -> str:
    """Parashari D9 (modality method per Goel rules3)."""
    i = _idx(sign)
    part = min(int(deg_in_sign / (30 / 9)), 8)
    if i % 3 == 0:  # movable
        start = i
    elif i % 3 == 1:  # fixed
        start = (i + 8) % 12
    else:  # dual
        start = (i + 4) % 12
    return SIGNS[(start + part) % 12]


# Goel rules3 - vish navamsha (1st pada of fire/earth, 5th of air, 9th of water groups)
VISH_NAVAMSHA = {
    "Aries": {1}, "Taurus": {1}, "Virgo": {1}, "Sagittarius": {1},
    "Gemini": {5}, "Leo": {5}, "Libra": {5}, "Aquarius": {5},
    "Cancer": {9}, "Scorpio": {9}, "Capricorn": {9}, "Pisces": {9},
}

# Pushkar navamsha (curated subset - benefic-strengthening padas per Goel table)
PUSHKAR_NAVAMSHA = {
    ("Cancer", 7), ("Leo", 3), ("Virgo", 1), ("Libra", 5), ("Scorpio", 3),
    ("Sagittarius", 7), ("Capricorn", 5), ("Aquarius", 1), ("Pisces", 3),
    ("Taurus", 7),
}


def is_vargottama(d1_sign: str, d9_sign: str) -> bool:
    return d1_sign == d9_sign


def is_vish_navamsha(d1_sign: str, deg_in_sign: float) -> bool:
    return navamsha_part(d1_sign, deg_in_sign) in VISH_NAVAMSHA.get(d1_sign, set())


def is_pushkar_navamsha(d1_sign: str, deg_in_sign: float) -> bool:
    return (d1_sign, navamsha_part(d1_sign, deg_in_sign)) in PUSHKAR_NAVAMSHA


def saptamsha_sign(sign: str, deg_in_sign: float) -> str:
    """Parashari D7 (Goel rules14): odd signs from same sign; even from 7th sign."""
    i = _idx(sign)
    part = min(int(deg_in_sign / (30 / 7)), 6)
    start = i if i % 2 == 0 else (i + 6) % 12
    return SIGNS[(start + part) % 12]


def dashamsha_sign(sign: str, deg_in_sign: float) -> str:
    """Parashari D10 (Goel rules13): 3 deg parts; odd signs from same sign; even from 9th sign."""
    i = _idx(sign)
    part = min(int(deg_in_sign / 3), 9)
    start = i if i % 2 == 0 else (i + 8) % 12
    return SIGNS[(start + part) % 12]

