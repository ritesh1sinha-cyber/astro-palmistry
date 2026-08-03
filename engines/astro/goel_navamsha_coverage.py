#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Goel Predict with Navamsha - book topic coverage map (rules3 + OCR TOC)."""
from __future__ import annotations

# status: checked | partial | n_a
BOOK_TOPICS: list[dict[str, str]] = [
    # Ch 1 Basics
    {"chapter": "1", "topic": "D9 casting (Parashari)", "key": "d9_cast"},
    {"chapter": "1", "topic": "Pushkar navamsha", "key": "pushkar"},
    {"chapter": "1", "topic": "Vargottama navamsha", "key": "vargottama"},
    {"chapter": "1", "topic": "Vish navamsha harm flags", "key": "vish"},
    {"chapter": "1", "topic": "Navamsha deities / tattvas", "key": "deities"},
    # Ch 2 Marriage
    {"chapter": "2", "topic": "Marriage promise (D1+D9 7th)", "key": "marriage_promise"},
    {"chapter": "2", "topic": "Marriage quality (karaka D1+D9)", "key": "marriage_quality"},
    {"chapter": "2", "topic": "D1 vs D9 long-term trajectory", "key": "d1_d9_trajectory"},
    {"chapter": "2", "topic": "Denial of marriage", "key": "denial"},
    {"chapter": "2", "topic": "Separation / divorce (D9 7th lord, 4th)", "key": "separation"},
    {"chapter": "2", "topic": "Spouse longevity (D9 7th vs 8th)", "key": "spouse_longevity"},
    {"chapter": "2", "topic": "Marriage foreign / other (DK + nodes)", "key": "foreign_marriage"},
    # Ch 3 Match making
    {"chapter": "3", "topic": "Synastry / kundali Milan", "key": "match_making"},
    # Ch 4 Multiple / affairs
    {"chapter": "4", "topic": "Multiple relations / marriages", "key": "multiple_relations"},
    {"chapter": "4", "topic": "Affairs / love / sexual urge (Mars+Venus D9)", "key": "affairs_sexual"},
    {"chapter": "4", "topic": "2nd lord sanskar in D9", "key": "sanskar_2nd"},
    # Ch 5 Timing
    {"chapter": "5", "topic": "Marriage timing (dasha lords)", "key": "marriage_timing"},
    {"chapter": "5", "topic": "Trimshamsha (D30) timing", "key": "d30_timing"},
    {"chapter": "5", "topic": "Jaimini chara dasha timing", "key": "jaimini_timing"},
    {"chapter": "5", "topic": "Transit triggers (Jupiter/Saturn)", "key": "transit_timing"},
    # Ch 6 Beeja
    {"chapter": "6", "topic": "Rashi Tulya / Beeja Kundali strength", "key": "beeja"},
    # Ch 7 Hazards
    {"chapter": "7", "topic": "Vish navamsha dasha karakatwa harm", "key": "vish_dasha"},
    {"chapter": "7", "topic": "Khara / 64th navamsha / 22nd dreshkana", "key": "khara_64"},
    # Ch 8 Religion
    {"chapter": "8", "topic": "Devotion / D9 trines & 9th", "key": "devotion"},
    {"chapter": "8", "topic": "Change of religion", "key": "religion_change"},
    {"chapter": "8", "topic": "Occult / astrology learning", "key": "occult"},
    {"chapter": "8", "topic": "Timing of worship", "key": "worship_timing"},
]

SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

VISH_KARAKATWA = {
    "Sun": "father / authority",
    "Moon": "mother / mind",
    "Mars": "siblings / surgery",
    "Mercury": "maternal kin / speech",
    "Jupiter": "children / wisdom",
    "Venus": "marriage / comfort",
    "Saturn": "career / chronic strain",
    "Rahu": "foreign / obsession",
    "Ketu": "spirituality / losses",
}
