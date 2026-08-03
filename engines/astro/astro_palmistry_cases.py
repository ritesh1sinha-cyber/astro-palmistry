#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chapter XVII practical cases - ground truth from Astro-Palmistry (Jyotis Saraswati)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from astro_palmistry_engine import DerivedBirthData, PalmLineCounts, derive_from_lines


@dataclass
class PracticalCase:
    id: int
    title: str
    counts: Optional[PalmLineCounts]
    expected: dict
    validation: str  # "full" | "reference"
    notes: str = ""


CASE_1 = PracticalCase(
    id=1,
    title="First Example - Lady (1932)",
    counts=PalmLineCounts(
        moon_a=17, moon_b=26,
        month_a=16, month_b=20,
        day_left=19, day_right=25,
        asc_a=19, asc_b=22,
        thumb_lines=16, percussion_lines=13,
        bright_half=True,
    ),
    expected={
        "tithi": 11,
        "paksha_contains": "bright",
        "solar_sign": "Pisces",
        "weekday": "Friday",
        "ascendant_sign": "Capricorn",
        "jupiter_in": "Cancer",
        "rahu_in": "Pisces",
        "dob": "1932-03-18",
        "time_approx": "04:50",
        "latitude": "31d08N",
        "longitude": "74d26E",
    },
    validation="full",
    notes="Full worked example pp.449-455.",
)

CASE_2 = PracticalCase(
    id=2,
    title="Second Example - Author (1928)",
    counts=PalmLineCounts(
        moon_a=15, moon_b=18,
        month_a=14, month_b=17,
        day_left=18, day_right=25,
        asc_a=17, asc_b=19,
        thumb_lines=13, percussion_lines=17,
        bright_half=True,
        saturn_adj=-1,
    ),
    expected={
        "tithi": 1,
        "paksha_contains": "bright",
        "solar_sign": "Virgo",
        "weekday": "Sunday",
        "ascendant_sign": "Leo",
        "jupiter_in": "Aries",
        "saturn_in": "Scorpio",
        "rahu_in": "Taurus",
        "dob": "1928-10-13",
        "time_approx": "03:58",
        "latitude": "30d12N",
        "longitude": "71d28E",
    },
    validation="full",
    notes="Author chart pp.459-464; Saturn remainder -1.",
)

CASE_3 = PracticalCase(
    id=3,
    title="Third Example - Lady (1951)",
    counts=PalmLineCounts(
        moon_a=16, moon_b=21,
        month_a=23, month_b=25,
        day_left=25, day_right=26,
        asc_a=17, asc_b=28,
        thumb_lines=19, percussion_lines=11,
        bright_half=False,
        yav_crossed=True,
        jupiter_adj=-1,
        saturn_adj=1,
        rahu_adj=1,
    ),
    expected={
        "tithi": 14,
        "paksha_contains": "dark",
        "solar_sign": "Pisces",
        "weekday": "Friday",
        "ascendant_sign": "Taurus",
        "jupiter_in": "Pisces",
        "saturn_in": "Virgo",
        "rahu_in": "Aquarius",
        "dob": "1951-04-06",
        "time_approx": "08:26",
        "latitude": "29d23N",
        "longitude": "77d01E",
    },
    validation="full",
    notes="Amavasya case pp.465-469.",
)

CASE_4 = PracticalCase(
    id=4,
    title="Fourth Example - Lady (1956)",
    counts=None,
    expected={
        "dob": "1956-05-07",
        "time_approx": "00:00",
        "latitude": "28d39N",
        "longitude": "77d13E",
    },
    validation="reference",
    notes="Hand prints pp.477-478; answer key on p.469.",
)

CASE_5 = PracticalCase(
    id=5,
    title="Fifth Example - Self-made man (~1923)",
    counts=None,
    expected={
        "birth_year_approx": 1923,
        "impression_year": 1978,
        "impression_age": 55,
        "traits": "self-made, wealthy, children, property, conveyance",
    },
    validation="reference",
    notes="Hand prints pp.479-480.",
)

CASE_6 = PracticalCase(
    id=6,
    title="Sixth Example - Delhi native (1955)",
    counts=None,
    expected={
        "dob": "1955-08-24",
        "time_approx": "14:52",
        "place": "Delhi",
        "ascendant_sign": "Sagittarius",
    },
    validation="reference",
    notes="Left-hand print p.481.",
)

ALL_CASES: list[PracticalCase] = [CASE_1, CASE_2, CASE_3, CASE_4, CASE_5, CASE_6]


def run_case(case: PracticalCase) -> Optional[DerivedBirthData]:
    if case.counts is None:
        return None
    return derive_from_lines(case.counts)
