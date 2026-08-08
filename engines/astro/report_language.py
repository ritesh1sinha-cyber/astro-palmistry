#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared client-facing language normalizers for all report lanes."""
from __future__ import annotations

import re


def neutralize_spouse_terms(line: str) -> str:
    """Partner references use spouse / partner - not wife / husband."""
    if not line:
        return ""
    for pat, repl in (
        (r"\bthe husband and wife\b", "you and your spouse"),
        (r"\bHusband and Wife\b", "Spouse"),
        (r"\bhusband and wife\b", "spouse and partner"),
        (r"\bBrother/Husband\b", "Brother/partner"),
        (r"\bYour spouse and wife\b", "You and your spouse"),
        (r"\bYour husband and wife\b", "You and your spouse"),
        (r"\bdefines the husband\b", "defines the spouse"),
        (r"\bdefines the wife\b", "defines the spouse"),
        (r"\bstrongest wife placement\b", "strongest spouse placement"),
        (r"\bstrongest husband placement\b", "strongest spouse placement"),
        (r"\bMarriage and your wife\b", "Marriage and partner"),
        (r"\bMarriage and your husband\b", "Marriage and partner"),
        (r"\bWife's Characteristics\b", "Spouse characteristics"),
        (r"\bWife could\b", "Spouse could"),
        (r"\bwife could\b", "spouse could"),
        (r"\bHusband could\b", "Spouse could"),
        (r"\bhusband could\b", "spouse could"),
        (r"\bin Your wife\b", "in your spouse"),
        (r"\bin your wife\b", "in your spouse"),
        (r"\bin Your husband\b", "in your spouse"),
        (r"\bin your husband\b", "in your spouse"),
        (r"\bin the wife\b", "in the spouse"),
        (r"\bin the husband\b", "in the spouse"),
        (r"\bYour wife\b", "Your spouse"),
        (r"\bYour husband\b", "Your spouse"),
        (r"\byour wife\b", "your spouse"),
        (r"\byour husband\b", "your spouse"),
        (r"\bthe wife\b", "the spouse"),
        (r"\bthe husband\b", "the spouse"),
        (r"\bwife is\b", "spouse is"),
        (r"\bhusband is\b", "spouse is"),
        (r"\bon her body\b", "on their body"),
        (r"\bon his body\b", "on their body"),
        (r"\bfrom her past life\b", "from their past life"),
        (r"\bfrom his past life\b", "from their past life"),
    ):
        line = re.sub(pat, repl, line, flags=re.I)
    return line


def neutralize_partner_pronouns(line: str) -> str:
    """Gender-neutral they/their when prose clearly describes the partner."""
    if not line or not re.search(r"\b(spouse|partner|marriage|7th|wife|husband)\b", line, re.I):
        return line
    subs = (
        (r"\bShe is practical\b", "They are practical"),
        (r"\bshe is practical\b", "they are practical"),
        (r"\bShe may\b", "They may"),
        (r"\bshe may\b", "they may"),
        (r"\bShe is\b", "They are"),
        (r"\bshe holds themselves\b", "they hold themselves"),
        (r"\bshe holds herself\b", "they hold themselves"),
        (r"\bHe is\b", "They are"),
        (r"\bhe holds himself\b", "they hold themselves"),
    )
    for pat, repl in subs:
        line = re.sub(pat, repl, line)
    return line


def normalize_sentence_dashes(text: str) -> str:
    """Replace sentence-joining em dashes with full stops; keep ranges intact."""
    if not text:
        return ""
    out = re.sub(r"\s+—\s+", ". ", text)
    out = re.sub(r"\.\s+\.", ".", out)
    out = re.sub(r"\.{2,}", ".", out)
    return out.strip()


def client_prose(line: str) -> str:
    """Full client-text pass for scraped or composed prediction lines."""
    line = neutralize_spouse_terms(line)
    line = neutralize_partner_pronouns(line)
    line = normalize_sentence_dashes(line)
    return line
