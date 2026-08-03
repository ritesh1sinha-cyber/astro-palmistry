#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Astro-Palmistry calculation engine - Jyotis Saraswati method (Chapter XVII)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

SIGNS = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)

WEEKDAYS = ("Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday")

TRIPLICITY: dict[int, tuple[str, str, str]] = {
    1: ("Aries", "Leo", "Sagittarius"),
    2: ("Taurus", "Virgo", "Capricorn"),
    3: ("Gemini", "Libra", "Aquarius"),
    4: ("Cancer", "Scorpio", "Pisces"),
    5: ("Aries", "Leo", "Sagittarius"),
    6: ("Taurus", "Virgo", "Capricorn"),
    7: ("Gemini", "Libra", "Aquarius"),
    8: ("Cancer", "Scorpio", "Pisces"),
    9: ("Aries", "Leo", "Sagittarius"),
    10: ("Taurus", "Virgo", "Capricorn"),
    11: ("Gemini", "Libra", "Aquarius"),
    0: ("Cancer", "Scorpio", "Pisces"),
    12: ("Cancer", "Scorpio", "Pisces"),
}

DAY_OFFSET = 611


@dataclass
class PalmLineCounts:
    moon_a: int
    moon_b: int
    month_a: int
    month_b: int
    day_left: int
    day_right: int
    asc_a: int
    asc_b: int
    thumb_lines: int
    percussion_lines: int
    bright_half: bool = True
    yav_crossed: bool = False
    jupiter_adj: int = 0
    saturn_adj: int = 0
    rahu_adj: int = 0


@dataclass
class DerivedBirthData:
    tithi: int
    paksha: str
    solar_sign: str
    weekday: str
    ascendant_sign: str
    asc_remainder: int
    jupiter_triplicity: tuple[str, str, str]
    jupiter_remainder: int
    saturn_triplicity: tuple[str, str, str]
    saturn_remainder: int
    rahu_triplicity: tuple[str, str, str]
    rahu_remainder: int
    ketu_triplicity: tuple[str, str, str]
    steps: list[str] = field(default_factory=list)


def _asc_sign(rem: int) -> str:
    rem = rem % 12
    if rem == 0:
        return "Pisces"
    return SIGNS[rem - 1]


def _solar_sign(rem: int) -> str:
    """Solar month remainder: 0=Pisces; else nth sign uses SIGNS[rem] (rem 5 -> Virgo)."""
    rem = rem % 12
    if rem == 0:
        return "Pisces"
    return SIGNS[rem]


def _triplicity(r: int) -> tuple[str, str, str]:
    return TRIPLICITY[r % 12]


def moon_tithi(counts: PalmLineCounts) -> tuple[int, str, list[str]]:
    total = counts.moon_a + counts.moon_b
    raw = (total + 40) * 7
    tithi = raw % 15
    if tithi == 0:
        tithi = 15
    paksha = "Krishna (dark)" if counts.yav_crossed or not counts.bright_half else "Shukla (bright)"
    steps = [
        f"Moon tithi: ({counts.moon_a}+{counts.moon_b}+40)x7/15 -> tithi {tithi}, {paksha}",
    ]
    return tithi, paksha, steps


def solar_month_sign(counts: PalmLineCounts) -> tuple[str, int, list[str]]:
    total = counts.month_a + counts.month_b
    rem = (total * 23) % 12
    sign = _solar_sign(rem)
    steps = [f"Solar month: ({counts.month_a}+{counts.month_b})x23/12 -> rem {rem} -> {sign}"]
    return sign, rem, steps


def weekday_of_birth(counts: PalmLineCounts) -> tuple[str, int, list[str]]:
    total = counts.day_left + counts.day_right + DAY_OFFSET
    rem = (total * 5) % 7
    day = WEEKDAYS[rem]
    steps = [
        f"Weekday: ({counts.day_left}+{counts.day_right}+{DAY_OFFSET})x5/7 -> rem {rem} -> {day}",
    ]
    return day, rem, steps


def ascendant_sign(counts: PalmLineCounts) -> tuple[str, int, list[str]]:
    total = counts.asc_a + counts.asc_b
    rem = (total * 13 + 5) % 12
    sign = _asc_sign(rem)
    steps = [f"Ascendant: ({counts.asc_a}+{counts.asc_b})x13+5 /12 -> rem {rem} -> {sign}"]
    return sign, rem, steps


def planet_triplicities(counts: PalmLineCounts) -> tuple[dict, list[str]]:
    t, p = counts.thumb_lines, counts.percussion_lines
    steps: list[str] = []

    j_rem = (t + p + 27 + counts.jupiter_adj) % 12
    j_tri = _triplicity(j_rem)
    steps.append(f"Jupiter: ({t}+{p}+27) rem {j_rem} -> {j_tri}")

    s_raw = (t * p + counts.saturn_adj) % 12
    s_tri = _triplicity(s_raw)
    steps.append(f"Saturn: ({t}x{p}) rem {s_raw} -> {s_tri}")

    s_sum, s_diff = t + p, abs(t - p)
    r_raw = (s_sum + s_diff + counts.rahu_adj) % 12
    r_tri = _triplicity(r_raw)
    steps.append(f"Rahu: sum={s_sum} diff={s_diff} rem {r_raw} -> {r_tri}")

    return {
        "jupiter": {"remainder": j_rem, "triplicity": j_tri},
        "saturn": {"remainder": s_raw, "triplicity": s_tri},
        "rahu": {"remainder": r_raw, "triplicity": r_tri},
    }, steps


def derive_from_lines(counts: PalmLineCounts) -> DerivedBirthData:
    steps: list[str] = []
    tithi, paksha, s1 = moon_tithi(counts)
    steps.extend(s1)
    solar, _, s2 = solar_month_sign(counts)
    steps.extend(s2)
    weekday, _, s3 = weekday_of_birth(counts)
    steps.extend(s3)
    asc, asc_rem, s4 = ascendant_sign(counts)
    steps.extend(s4)
    planets, s5 = planet_triplicities(counts)
    steps.extend(s5)

    rahu_tri = planets["rahu"]["triplicity"]
    ketu_tri = tuple(SIGNS[(SIGNS.index(s) + 6) % 12] for s in rahu_tri)

    return DerivedBirthData(
        tithi=tithi,
        paksha=paksha,
        solar_sign=solar,
        weekday=weekday,
        ascendant_sign=asc,
        asc_remainder=asc_rem,
        jupiter_triplicity=planets["jupiter"]["triplicity"],
        jupiter_remainder=planets["jupiter"]["remainder"],
        saturn_triplicity=planets["saturn"]["triplicity"],
        saturn_remainder=planets["saturn"]["remainder"],
        rahu_triplicity=rahu_tri,
        rahu_remainder=planets["rahu"]["remainder"],
        ketu_triplicity=ketu_tri,
        steps=steps,
    )


def counts_from_manual_table(**kwargs) -> PalmLineCounts:
    return PalmLineCounts(**kwargs)
