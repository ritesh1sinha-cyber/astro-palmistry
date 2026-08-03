#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KP book corpus load and chart lookups (rules19-21 + houses/events OCR)."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "kp_book_data.json"


@lru_cache(maxsize=1)
def load_kp_book() -> dict:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Run build_kp_data.py first - missing {DATA_PATH}")
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def event_group(domain: str) -> dict:
    book = load_kp_book()
    key = {
        "career": "career",
        "marriage": "marriage",
        "children": "children",
        "travel": "travel",
        "education": "education",
        "property": "property",
        "health": "health_bad",
        "health_good": "health_good",
        "recovery": "health_good",
        "wealth": "career",
        "status": "career",
    }.get(domain, domain)
    return book.get("event_groups", {}).get(key, {})


def domain_rules(domain: str, max_n: int = 3) -> list[str]:
    rules = load_kp_book().get("domain_rules", {}).get(domain, [])
    return [r["text"] for r in rules[:max_n]]


def csl_planet_note(planet: str) -> str:
    return load_kp_book().get("csl_planet", {}).get(planet, "")


def career_nature(houses: set[int] | list[int]) -> list[str]:
    book = load_kp_book()
    nature = book.get("career_house_nature", {})
    out = []
    for h in sorted(houses):
        if str(h) in nature:
            out.append(nature[str(h)])
    return out


def links_verdict(links: set[int], domain: str) -> tuple[str, set[int], set[int]]:
    g = event_group(domain)
    fav = set(g.get("fav", []))
    unf = set(g.get("unfav", []))
    hit_f = links & fav
    hit_u = links & unf
    primary = g.get("primary", 0)
    if primary and primary in links:
        score = 2
    else:
        score = 0
    score += len(hit_f) - len(hit_u)
    if score >= 2 and hit_f:
        return "promised", hit_f, hit_u
    if hit_u and len(hit_u) > len(hit_f):
        return "denied", hit_f, hit_u
    if hit_f or hit_u:
        return "mixed", hit_f, hit_u
    return "weak", hit_f, hit_u


def health_csl_verdict(links6: set[int], links8: set[int] | None = None) -> str:
    book = load_kp_book()
    hc = book.get("health_csl", {})
    bad = {6, 8, 12}
    good = {1, 5, 9}
    parts = []
    if links6 & bad and links6 & good:
        parts.append(
            "6th CSL links both illness houses (6/8/12) and recovery houses (1/5/9) - "
            "constitution is mixed; discipline and regular care decide which side dominates."
        )
    elif links6 & bad:
        parts.append(hc.get("chronic", "6th CSL linking 6-8-12 suggests chronic illness tendency."))
    elif links6 & good:
        parts.append(hc.get("recovery", "6th CSL linking 1-5-9 favours quicker recovery."))
    if links8 and links8 & good:
        parts.append(hc.get("eighth_recovery", "8th CSL linking 1-5-9 supports recovery after scares."))
    return " ".join(parts)


def pick_rule(domain: str, keyword: str) -> str:
    rules = load_kp_book().get("domain_rules", {}).get(domain, [])
    kw = keyword.lower()
    for r in rules:
        if kw in r.get("title", "").lower() or kw in r.get("text", "").lower():
            return r["text"]
    return rules[0]["text"] if rules else ""


def timing_steps() -> list[str]:
    return load_kp_book().get("timing", {}).get("six_steps", [])


def humanize_kp(line: str) -> str:
    if not line:
        return ""
    line = re.sub(r"\bthe native\b", "you", line, flags=re.I)
    line = re.sub(r"\bNative\b", "You", line)
    if line and line[0].islower():
        line = line[0].upper() + line[1:]
    return line
