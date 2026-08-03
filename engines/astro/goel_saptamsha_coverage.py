#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Goel Predict with Saptamsha - book topic coverage map (rules14)."""
from __future__ import annotations

SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

BOOK_TOPICS = [
    {"chapter": "1", "topic": "D7 scope & casting", "key": "d7_scope"},
    {"chapter": "1", "topic": "D1 fifth house promise", "key": "d1_fifth_promise"},
    {"chapter": "1", "topic": "Jupiter karaka (parent bond)", "key": "jupiter_karaka"},
    {"chapter": "2", "topic": "D7 lagna promise / delay / denial", "key": "d7_promise"},
    {"chapter": "2", "topic": "Saturn delay on D7", "key": "saturn_delay"},
    {"chapter": "2", "topic": "BS / KS sphuta", "key": "beeja_kshetra"},
    {"chapter": "2", "topic": "Santana tithi", "key": "santana_tithi"},
    {"chapter": "5", "topic": "Worthy children (lagna lord / raj yoga)", "key": "worthy_children"},
    {"chapter": "5", "topic": "Child follows parent profession", "key": "child_profession"},
    {"chapter": "7", "topic": "Happiness from children (D7 4th)", "key": "happiness_children"},
    {"chapter": "7", "topic": "Child health (D7 6th / 8th)", "key": "child_health"},
    {"chapter": "8", "topic": "Number of children", "key": "child_count"},
    {"chapter": "8", "topic": "Gender of children", "key": "child_gender"},
    {"chapter": "9", "topic": "Timing of childbirth (Vimshottari)", "key": "child_timing"},
    {"chapter": "4", "topic": "Twins / multiple birth", "key": "twins"},
    {"chapter": "3", "topic": "Troubled child-parent bond", "key": "bond_strain"},
    {"chapter": "7", "topic": "Grandchildren (D7 9th)", "key": "grandchildren"},
    {"chapter": "2", "topic": "Kakvandhya / Bahu Putra yogas", "key": "special_yogas"},
    {"chapter": "2", "topic": "Adoption path", "key": "adoption"},
    {"chapter": "7", "topic": "D7 2nd / 11th / 12th themes", "key": "house_extras"},
]
