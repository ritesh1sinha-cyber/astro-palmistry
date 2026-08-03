#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mehta Modern Techniques semantic engine (rules4) - reuses Bhardwaj MiniLM stack."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from bhardwaj_semantic import (
    BhardwajSemanticEngine,
    Cluster,
    Signal,
    HOUSE_DOMAIN,
    STRONG,
    WEAK,
    _dignity_word,
    _ord,
    _sentence_polarity,
    load_corpus,
)
from mehta_book_data import lookup_mehta_lord, pick_mehta_clause

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "mehta_book_data.json"


class MehtaSemanticEngine(BhardwajSemanticEngine):
    """Same MiniLM retrieval; Mehta book JSON and intro corpus."""

    def __init__(self, book: Optional[dict] = None):
        from local_models import load_sentence_transformer

        self.model = load_sentence_transformer()
        self.book = book or json.loads(DATA_PATH.read_text(encoding="utf-8"))
        self.chunks = load_corpus(self.book)
        for step in self.book.get("intro_steps", []):
            from bhardwaj_semantic import BookChunk
            self.chunks.append(BookChunk(step, "intro", "personality", "mehta"))
        self._chunk_emb = self.model.encode(
            [c.text for c in self.chunks], normalize_embeddings=True, show_progress_bar=False,
        )
        from bhardwaj_semantic import THEME_ANCHORS
        import numpy as np
        self._anchor_emb = {}
        for dom, anchors in THEME_ANCHORS.items():
            self._anchor_emb[dom] = self.model.encode(anchors, normalize_embeddings=True)


def build_mehta_signals(chart: MehtaChart, pc: dict) -> list[Signal]:
    s: list[Signal] = []
    lagna = chart.lagna
    moon = chart.moon_sign
    ll = chart.houses[1]["lord"]

    s.append(Signal(
        "Mehta Step 1", "personality", "neutral", "",
        f"{lagna} lagna with Moon in {moon}; Mehta requires judging from lagna, Moon, and Sun together.",
        anchor=f"Your chart opens through {lagna} rising; {ll} is lagna lord in the {_ord(chart.planets[ll]['house'])} house.",
    ))

    moon_h = chart.moon_house_from_lagna()
    wealth_moon = chart.wealth_from_moon()
    s.append(Signal(
        "Moon lagna cross-check", "finance", "neutral", "",
        f"2nd from Moon falls in the {_ord(wealth_moon)} house theme from Chandra lagna.",
        anchor=(
            f"Mehta (Parashara): wealth reads from 2nd from lagna and 2nd from Moon. "
            f"Your Moon sits in the {_ord(moon_h)} from lagna."
        ),
    ))

    for flag in chart.navamsha_dilution_flags():
        s.append(Signal(
            "Navamsha check", "personality", "caution", "",
            flag,
            anchor=flag,
        ))

    maj = chart.sign_majority()
    top = max(maj, key=maj.get)
    s.append(Signal(
        "Sign majority", "personality", "neutral", "",
        f"Planet majority skews {top} ({maj[top]} of 7 traditional grahas).",
        anchor=f"Mehta Step 2b: majority in {top} signs colours temperament and movement.",
    ))

    house_dom = {5: "children", 7: "marriage", 10: "career", 11: "finance", 6: "health", 9: "travel", 4: "property"}

    for pl, info in chart.planets.items():
        h = info["house"]
        dom = house_dom.get(h, HOUSE_DOMAIN.get(h, "personality"))
        dig = info["dignity"]
        direction = "positive" if dig in STRONG or h in (1, 4, 5, 9, 10, 11) else (
            "caution" if dig in WEAK or h in (6, 8, 12) else "neutral"
        )
        if pl == "Venus" and h == 7:
            direction = "positive"
        if pl in ("Sun", "Mercury") and h == 7:
            direction = "caution"
        ruled = chart.rules.get(pl, [])
        ruled_txt = ", ".join(_ord(x) for x in ruled) if ruled else "no house lordship"
        anchor = (
            f"Your {pl} sits in the {_ord(h)} house ({info['sign']}, {_dignity_word(dig)}) "
            f"and rules {ruled_txt}."
        )
        s.append(Signal(
            f"{pl} in house", dom, direction, "",
            f"{anchor} Mehta {pl} in {_ord(h)} house.",
            anchor=anchor,
            planet=pl, house=h, dignity=dig,
        ))

    for h in range(1, 13):
        lord = chart.houses[h]["lord"]
        occ = chart.planets[lord]["house"]
        dom = HOUSE_DOMAIN.get(h, "personality")
        direction = "caution" if occ in (6, 8, 12) else "neutral"
        clause = lookup_mehta_lord(chart.book, h, occ, direction)
        if not clause:
            continue
        anchor = f"As lord of the {_ord(h)} house, {lord} sits in your {_ord(occ)} house."
        pol = _sentence_polarity(clause)
        direction = "positive" if pol == "positive" else ("caution" if pol == "caution" else direction)
        s.append(Signal(
            f"Lord {h} in {occ}", dom, direction, "",
            f"{anchor} {clause[:200]}",
            anchor=anchor,
            lord_of=h, lord_in=occ,
        ))

    for y in chart.detect_mehta_yogas():
        dom = "career" if "Kendra" in y["name"] or "Vipar" in y["name"] else "personality"
        s.append(Signal(
            "Mehta yoga", dom, "positive", "",
            f"{y['name']}: {y['result']}",
            anchor=y["result"],
        ))

    md = chart.cur_md["md_lord"]
    ad = next((a for a in chart.antars if a.get("status") == "current"), None)
    ad_lord = ad["ad_lord"] if ad else md
    timing = ""
    if ad:
        try:
            from datetime import datetime
            sdt = datetime.strptime(ad["start"][:10], "%Y-%m-%d").date().strftime("%b %Y")
            edt = datetime.strptime(ad["end"][:10], "%Y-%m-%d").date().strftime("%b %Y")
            timing = f"{sdt} - {edt}"
        except ValueError:
            pass
    md_h = chart.planets[md]["house"]
    s.append(Signal(
        "Vimshottari (Mehta Ch XV)", "current", "neutral", timing,
        f"Running {md} mahadasha with {ad_lord} antardasha; Mehta: dasha lord as temporary lagna.",
        anchor=(
            f"Mahadasha lord {md} occupies the {_ord(md_h)} house; "
            f"antardasha {ad_lord} modulates this band now."
        ),
        planet=md, house=md_h,
    ))

    return s
