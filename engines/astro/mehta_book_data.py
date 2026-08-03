#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared constants and cleaned Mehta book lookups."""
from __future__ import annotations

import re

from bhardwaj_semantic import pick_book_clause

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}
GROUP_I = {1, 2, 4, 5, 7, 9, 10, 11}
GROUP_II = {3, 6, 8, 12}


def house_of(sign: str, lagna: str) -> int:
    return (SIGNS.index(sign) - SIGNS.index(lagna)) % 12 + 1


_CONTAMINATION = (
    r"Horoscope of\b",
    r"Gandhiji\b",
    r"Nargis Dutt\b",
    r"Tagore\b",
    r"PAGE\s+\d+",
    r"Yogas of the\b",
)


def sanitize_mehta_clause(text: str) -> str:
    if not text:
        return ""
    text = re.sub(
        r"={3,}\s*PAGE\s+\d+\s*={3,}.*?MODERN TECHNIQUES\s*",
        " ",
        text,
        flags=re.I | re.S,
    )
    for stop in _CONTAMINATION:
        text = re.split(stop, text, maxsplit=1, flags=re.I)[0]
    text = re.sub(
        r"^Boss's favour is judged from the 7.+?,\s*",
        "",
        text,
        count=1,
        flags=re.I | re.S,
    )
    text = re.sub(r"\s+In the\s*$", "", text, flags=re.I)
    text = re.sub(r"\bd\?ridra\b", "daridra", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < 18:
        return ""
    if re.search(r"Horoscope of|PAGE\s+\d+", text, re.I):
        return ""
    return text


def pick_mehta_clause(raw: str, dignity: str = "", direction: str = "neutral") -> str:
    cleaned = sanitize_mehta_clause(raw)
    if not cleaned:
        return ""
    return pick_book_clause(cleaned, dignity, direction)


def lookup_mehta_lord(book: dict, lord_of: int, lord_in: int, direction: str = "neutral") -> str:
    raw = ""
    if lord_of == 1:
        raw = book.get("lagna_lord_in_house", {}).get(str(lord_in), "")
    elif lord_of == 2:
        raw = book.get("second_lord_in_house", {}).get(str(lord_in), "")
    elif lord_of == 7:
        raw = book.get("seventh_lord_in_house", {}).get(str(lord_in), "")
    elif lord_of == 10:
        raw = book.get("tenth_lord_in_house", {}).get(str(lord_in), "")
    else:
        raw = book.get("house_lord_in_house", {}).get(str(lord_of), {}).get(str(lord_in), "")
    return pick_mehta_clause(raw, "", direction)
