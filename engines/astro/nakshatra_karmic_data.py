#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lookup 108 nakshatra karmic tales from parsed OCR JSON."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from astro_precompute import NAKSHATRAS, normalize_nakshatra

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "nakshatra_karmic_data.json"

SPELL_VARIANTS = {
    "Krittika": ["Kritika", "Krittika"],
    "Jyeshtha": ["Jyestha", "Jyeshtha"],
    "Mrigashira": ["Mrigashira", "Mrigashirsha"],
    "Dhanishtha": ["Dhanishta", "Dhanishtha"],
    "Purva Bhadrapada": ["Purva Bhadrapada", "Purvabhadra"],
    "Uttara Bhadrapada": ["Uttara Bhadrapada", "Uttarabhadra"],
}


@lru_cache(maxsize=1)
def load_tales() -> dict:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Run build_nakshatra_data.py first - missing {DATA_PATH}")
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def lookup_tale(nakshatra: str, pada: int) -> dict | None:
    nak = normalize_nakshatra(nakshatra)
    if nak not in NAKSHATRAS:
        return None
    book = load_tales()
    by_key = book.get("by_key", {})
    p = int(pada)

    def _get(n: str, pad: int) -> dict | None:
        key = f"{n}|{pad}"
        if key in by_key:
            return by_key[key]
        for alt in SPELL_VARIANTS.get(n, [n]):
            k2 = f"{alt}|{pad}"
            if k2 in by_key:
                return by_key[k2]
        return None

    hit = _get(nak, p)
    if hit:
        return hit
    for near in (p - 1, p + 1):
        if 1 <= near <= 4:
            alt = _get(nak, near)
            if alt:
                alt = dict(alt)
                alt["fallback_pada"] = near
                return alt
    return None


def chart_stars(pc: dict) -> dict:
    """Moon (required), Lagna, Sun nakshatra+pada from precompute."""
    planets = pc.get("planets", {})
    lagna = pc.get("lagna", {})
    meta = pc.get("meta", {})
    out: dict[str, dict] = {}

    def _add(label: str, nak: str, pada: int | str):
        if not nak or nak == "?":
            return
        try:
            p = int(pada)
        except (TypeError, ValueError):
            return
        tale = lookup_tale(nak, p)
        out[label] = {
            "nakshatra": normalize_nakshatra(nak),
            "pada": p,
            "tale": tale,
        }

    moon = planets.get("Moon", {})
    _add("moon", moon.get("nakshatra", meta.get("moon_nakshatra", "")), moon.get("pada", ""))

    _add("lagna", lagna.get("nakshatra", meta.get("lagna_nakshatra", "")), lagna.get("pada", meta.get("lagna_pada", "")))

    sun = planets.get("Sun", {})
    _add("sun", sun.get("nakshatra", ""), sun.get("pada", ""))
    return out


def theme_tags(body: str) -> list[str]:
    text = body.lower()
    tags: list[str] = []
    checks = [
        ("trust and betrayal", ("betray", "infidel", "adulter", "deceit")),
        ("greed and debt", ("greed", "stolen", "debt", "miser", "theft")),
        ("duty and service", ("duty", "service", "dharma", "scholar", "brahmin")),
        ("loss and grief", ("death", "demise", "grief", "sorrow", "tragedy")),
        ("redemption", ("redemption", "repent", "forgiv", "purif")),
        ("relationship knots", ("consort", "marriage", "spouse", "love")),
        ("health and worry", ("ailment", "disease", "suffer", "worry", "distress")),
        ("wealth and craft", ("gold", "wealth", "craft", "merchant", "business")),
    ]
    for label, kws in checks:
        if any(k in text for k in kws):
            tags.append(label)
    return tags[:4]


def short_title(tale: dict) -> str:
    title = (tale.get("title") or "").strip()
    if title:
        return title
    body = tale.get("body", "")
    m = re.match(r"^(.{20,90}?)[.:]", body)
    return m.group(1) if m else "Karmic tale"


def summarize_tale(tale: dict, max_sentences: int = 3) -> str:
    body = tale.get("body", "")
    if not body:
        return ""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if len(s.strip()) > 30]
    pick = sents[:2]
    if tale.get("moral") and tale["moral"] not in pick:
        pick.append(tale["moral"])
    return " ".join(pick[:max_sentences])
