#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BNN book corpus load, sanitize, and chart lookups (rules24)."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from bhardwaj_semantic import pick_book_clause

from report_language import client_prose, neutralize_spouse_terms

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "bnn_book_data.json"

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

_CONTAMINATION = (
    r"========== PAGE",
    r"BHRIGU NANDI NADI",
    r"Example \d+:",
    r"Querent picks",
    r"Female Chart Specific",
    r"In a female chart",
    r"In females,",
)


def _norm_pair(a: str, b: str) -> str:
    x, y = sorted([a.title(), b.title()], key=str.lower)
    return f"{x}|{y}"


def sanitize_bnn_clause(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"={3,}\s*PAGE\s+\d+\s*={3,}.*", " ", text, flags=re.I | re.S)
    text = re.sub(r"BHRIGU NANDI NADI:\s*ASTROLOGY SIMPLIFIED", " ", text, flags=re.I)
    text = re.sub(r"NADI:\s*ASTROLOGY SIMPLIFIED", " ", text, flags=re.I)
    for stop in _CONTAMINATION:
        text = re.split(stop, text, maxsplit=1, flags=re.I)[0]
    text = re.sub(r"[\u00a9\u00ae@]\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^:\s*", "", text)
    if len(text) < 20 or re.search(r"PAGE\s+\d+", text, re.I):
        return ""
    return text


def pick_bnn_clause(raw: str, dignity: str = "", direction: str = "neutral") -> str:
    cleaned = sanitize_bnn_clause(raw)
    if not cleaned:
        return ""
    cleaned = re.sub(
        r"^(Personality & Behavior|Family|Professional Life|Education|Spouse and Family|"
        r"Finance and Vehicles|Development and Finance|Traits|Fields of Study)[:\s]*",
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(
        r"^(On Father and Son|Rashi impact can be seen on the Jeev Tatva).*?(?=Father|Son|\w+\s+(?:\(|:))",
        "",
        cleaned,
        count=1,
        flags=re.I | re.S,
    )
    cleaned = re.sub(r"^[A-Za-z]+:\s*(?:Father|Brother|Land|Native)\s*:\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.split(
        r"Jupiter in Pisces|Debilitation of Jupiter|Key Jupiter Combination|"
        r"Jupiter in Capricorn \(Mars|Sun Combinations and Their Effects",
        cleaned,
        maxsplit=1,
    )[0].strip()
    cleaned = re.sub(
        r"^Impact on (?:Father|Mother|Wife|Sister).*?:\s*",
        "",
        cleaned,
        flags=re.I,
    )
    return pick_book_clause(cleaned, dignity, direction)


# Life-area keywords that must not bleed across BNN OCR clauses
_FAMILY_TOPIC = re.compile(
    r"\b(father|mother|wife|husband|brother|sister|brothers|sisters)\b",
    re.I,
)
_LAND_TOPIC = re.compile(
    r"\b(land or property|real estate|property gains|assets through|jeev tatva)\b",
    re.I,
)
_SPOUSE_CHARACTER = re.compile(
    r"\b(your spouse is|your wife is|your husband is|husband is of|spouse is of good character)\b",
    re.I,
)

# Domains where father/mother/land/spouse BNN lines are inappropriate
_STRICT_DOMAINS = frozenset({
    "children", "speech", "health", "career", "finance", "travel", "education", "current",
})


def clause_ok_for_domain(text: str, domain: str) -> bool:
    """Return False when a BNN clause belongs to another life area."""
    if not text or not domain:
        return True
    dom = domain.lower()
    if dom in ("marriage", "property", "personality", "spiritual"):
        return True
    if dom == "children" and re.search(r"\b(child|progeny|student|5th|creative|intelligence)\b", text, re.I):
        if not _FAMILY_TOPIC.search(text):
            return True
    tl = text.lower()
    if dom in _STRICT_DOMAINS:
        if _FAMILY_TOPIC.search(text):
            return False
        if _LAND_TOPIC.search(text):
            return False
        if _SPOUSE_CHARACTER.search(tl):
            return False
    return True


@lru_cache(maxsize=1)
def load_bnn_book() -> dict:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Run build_bnn_data.py first - missing {DATA_PATH}")
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def lookup_planet_sign(book: dict, planet: str, sign: str, dignity: str = "", direction: str = "neutral") -> str:
    raw = book.get("planet_in_sign", {}).get(planet, {}).get(sign, "")
    return pick_bnn_clause(raw, dignity, direction)


def lookup_combination(book: dict, a: str, b: str, direction: str = "neutral") -> str:
    combos = book.get("combinations", {})
    key = _norm_pair(a, b)
    entries = combos.get(key) or combos.get(f"{a.title()}-{b.title()}") or combos.get(f"{b.title()}-{a.title()}") or []
    if not entries:
        return lookup_pair_159(book, a, b, direction)
    raw = entries[0].get("text", "") if isinstance(entries[0], dict) else str(entries[0])
    return pick_bnn_clause(raw, "", direction)


def lookup_pair_159(book: dict, a: str, b: str, direction: str = "neutral") -> str:
    raw = book.get("pairs_159", {}).get(_norm_pair(a, b), "")
    return pick_bnn_clause(raw, "", direction)


def lookup_from_jupiter(book: dict, planet: str, house: int, direction: str = "neutral") -> str:
    raw = book.get("planet_in_house_from_jupiter", {}).get(planet, {}).get(str(house), "")
    return pick_bnn_clause(raw, "", direction)


def lookup_node_in_house(book: dict, node: str, house: int, direction: str = "neutral") -> str:
    key = "rahu_in_house" if node.title() == "Rahu" else "ketu_in_house"
    raw = book.get(key, {}).get(str(house), "")
    return pick_bnn_clause(raw, "", direction)


def lookup_fourth_tenant(book: dict, planet: str, direction: str = "neutral") -> str:
    raw = book.get("fourth_house_planet", {}).get(planet, "")
    return pick_bnn_clause(raw, "", direction)


def lookup_node_sign(book: dict, node: str, sign: str, direction: str = "neutral") -> str:
    key = "rahu_in_sign" if node.title() == "Rahu" else "ketu_in_sign"
    raw = book.get(key, {}).get(sign, "")
    return pick_bnn_clause(raw, "", direction)


def lookup_profession_sign(book: dict, sign: str, direction: str = "positive") -> str:
    raw = book.get("profession_by_sign", {}).get(sign, "")
    return pick_bnn_clause(raw, "", direction)


def house_from_jupiter(jupiter_sign: str, planet_sign: str) -> int:
    return (SIGNS.index(planet_sign) - SIGNS.index(jupiter_sign)) % 12 + 1


def collect_clauses(*clauses: str, max_n: int = 3) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for c in clauses:
        c = (c or "").strip()
        if not c or c in seen:
            continue
        seen.add(c)
        out.append(c)
        if len(out) >= max_n:
            break
    return out


def humanize_bnn(line: str) -> str:
    if not line:
        return ""
    line = re.sub(r"^\d+\.\s*", "", line.strip())
    line = neutralize_spouse_terms(line)
    for a, b in (
        (r"\bThe native\b", "You"),
        (r"\bNative is\b", "You are"),
        (r"\bNative will\b", "You will"),
        (r"\bNative may\b", "You may"),
        (r"\bNative can\b", "You can"),
        (r"\bNative has\b", "You have"),
        (r"\bthe native\b", "you"),
        (r"\bsuppresses it\b", "suppress it"),
        (r"\bThe spouse\b", "Your spouse"),
        (r"\bThe wife\b", "Your spouse"),
        (r"\bThe husband\b", "Your spouse"),
        (r"\bYou are daring, strong and does not\b", "You are daring and strong but do not"),
        (r"\bthe more informed they are, the more they will earn\b", "the more you learn, the more you earn"),
        (r"\bdo not easily show anger but suppress it\b", "do not show anger easily but suppress it"),
        (r"\beasily makes friendships\b", "easily make friendships"),
        (r"\bYou's\b", "Your"),
    ):
        line = re.sub(a, b, line, flags=re.I)
    line = client_prose(line)
    if line and line[0].islower():
        line = line[0].upper() + line[1:]
    return line
