#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Human daily Moonology reading from Boland Ch.2/9/10 + lunation context (rules44)."""
from __future__ import annotations

from datetime import date
from typing import Any

from moonology_house_cosmic import HOUSE_COSMIC

# Ch.9 - how the day *feels* when Moon transits this sign (plain English)
SIGN_DAY_FEEL: dict[str, str] = {
    "Aries": "emotions run hot and fast; you want movement and honest reactions, not polite small talk",
    "Taurus": "your mood wants comfort, good food, and a slower pace; forcing speed will grate",
    "Gemini": "your head buzzes with messages, ideas, and errands; conversation is the main outlet",
    "Cancer": "home, family, and safety matter more than ambition; nest-building beats networking",
    "Leo": "you want to be seen and enjoyed; creative flair and warmth land better than shrinking back",
    "Virgo": "you notice what is out of place; fixing, sorting, and health habits feel satisfying",
    "Libra": "relationship tone colours everything; fairness, charm, and one-to-one time matter",
    "Scorpio": "feelings run deep; you may probe what is hidden, but lighten up if intensity turns sharp",
    "Sagittarius": "optimism and bigger-picture thinking pull you; small-minded worry feels suffocating",
    "Capricorn": "practical duty and long-term aims surface; structure helps, but do not skip all joy",
    "Aquarius": "you think about the group, the future, and what needs to change; frankness can sting",
    "Pisces": "dreamy, porous moods; spiritual or artistic time works better than hard-edged debate",
}

# Ch.10 - what the house adds to your chart today
HOUSE_DAY_FEEL: dict[int, str] = {
    1: "feelings sit right at the surface; how you present yourself and how you feel about your body are linked",
    2: "money, self-worth, and what you own tug at your mood; spending and security are emotional topics",
    3: "talks, siblings, neighbours, and short trips carry extra feeling; say what you mean, kindly",
    4: "home and family pull you inward; pottering, cooking, or resting at base restores you",
    5: "play, romance, creativity, and children brighten the mood if you make room for them",
    6: "work, service, and health routines want attention; small useful tasks calm the nerves",
    7: "partners and one-to-one deals are emotionally charged; listen before you lobby",
    8: "shared money, trust, and private fears may surface; go slowly with intensity",
    9: "travel, study, faith, or big-picture plans feel within reach; broaden the mental horizon",
    10: "career, reputation, and authority themes colour the day; public moves need emotional honesty",
    11: "friends, wishes, and community matter; check whether old dreams still excite you",
    12: "you need quiet; secrets, dreams, and month-end processing want solitude more than crowds",
}

PHASE_DAY_FEEL: dict[str, str] = {
    "New Moon": "a clean-slate emotional pulse; plant intentions after the exact conjunction and feel them as already real",
    "Waxing Crescent": "faith in fresh starts; revisit last month's wishes and keep visualising until they feel believable",
    "First Quarter": "a push to commit or quit; friction is asking you to act on what still matters",
    "Gibbous Moon": "tweak plans before the peak; patience now prevents a late stumble",
    "Full Moon": "emotional volume is high; release grudges, name blessings, and let the month climax pass through you",
    "Disseminating Moon": "exhale after the peak; share a lesson and accept what already landed",
    "Third Quarter": "honest audit time; drop a habit that no longer fits the person you are becoming",
    "Balsamic Moon": "low battery and soft edges; rest, surrender, and let the old cycle dissolve gently",
}

PHASE_BEFORE_NM: str = (
    "The sky is nearly dark Moon. Wishes belong after exact New Moon, not tonight. "
    "Use today to rest, clear mental clutter, and line up what you will ask for once the cycle turns."
)


def _first_name(client: str) -> str:
    return (client or "You").strip().split()[0]


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def build_daily_moon_reading(
    *,
    client: str,
    target: date,
    moon_sign: str,
    moon_house: int,
    lagna: str,
    phase: str,
    phase_astronomical: str = "",
    phase_note: str = "",
    element: str = "",
    lunation_applicable: str = "",
    lunation_timing: dict[str, Any] | None = None,
    love_zone_note: str = "",
    personal_lunation: str = "",
    is_new_moon_day: bool = False,
    is_full_moon_day: bool = False,
    new_moon_themes: list[str] | None = None,
    full_moon_message: str = "",
) -> dict[str, str]:
    """Return human paragraphs for the day (not bullet rule dumps)."""
    name = _first_name(client)
    weekday = target.strftime("%A")
    sign_feel = SIGN_DAY_FEEL.get(moon_sign, "today's lunar mood colours ordinary tasks")
    house_feel = HOUSE_DAY_FEEL.get(moon_house, "this part of your chart is emotionally active")
    zone = HOUSE_COSMIC.get(moon_house, {}).get("zone", f"{_ordinal(moon_house)} house")
    phase_feel = PHASE_DAY_FEEL.get(phase, "")

    opening = (
        f"{name}, on this {weekday} the Moon moves through {moon_sign} "
        f"({_ordinal(moon_house)} house from your {lagna} rising chart, {zone}). "
        f"Boland's read: {sign_feel}, and because the Moon is crossing your {_ordinal(moon_house)} house, "
        f"{house_feel}."
    )

    phase_para = ""
    if is_new_moon_day and lunation_timing:
        exact = lunation_timing.get("exact_display", "")
        peak_end = lunation_timing.get("peak_window_end_display", "")
        theme = (new_moon_themes or ["steady intentions that match your real values"])[0].rstrip(".")
        phase_para = (
            f"This is your New Moon in {moon_sign}. After {exact}, do the wish ritual "
            f"(ideally before {peak_end}). Boland's theme for this sign: {theme.lower()}. "
            f"Write ten wishes, speak them until they feel true in your body, then take one grounded step today."
        )
        if moon_house == 12:
            phase_para += (
                " Your 12th house is active, so keep it private: journal, release a fear list safely, "
                "and rest once you have planted the intentions."
            )
    elif is_full_moon_day and lunation_timing:
        exact = lunation_timing.get("exact_display", "")
        start = lunation_timing.get("ceremony_start_display", "")
        end = lunation_timing.get("ceremony_end_display", "")
        msg = full_moon_message or "let the month climax move through you, then clear space with forgiveness"
        phase_para = (
            f"Full Moon peaks at {exact}. Tonight ({start} to {end}) is for the forgiveness and gratitude "
            f"ceremony. {msg.capitalize() if msg[0].islower() else msg}"
        )
    elif phase_note:
        phase_para = phase_note
    elif phase_feel:
        astro = f" ({phase_astronomical} astronomically)" if phase_astronomical else ""
        phase_para = f"Cycle note{astro}: {phase_feel}."

    practical = _practical_paragraph(
        name=name,
        moon_sign=moon_sign,
        moon_house=moon_house,
        phase=phase,
        is_new_moon_day=is_new_moon_day,
        element=element,
    )

    watch = _watch_paragraph(moon_sign=moon_sign, moon_house=moon_house, phase=phase)

    paragraphs = [opening]
    if phase_para:
        paragraphs.append(phase_para)
    paragraphs.append(practical)
    if watch:
        paragraphs.append(watch)
    if love_zone_note:
        paragraphs.append(love_zone_note)
    if personal_lunation:
        paragraphs.append(personal_lunation)

    full = " ".join(paragraphs)
    return {
        "daily_reading": full,
        "opening": opening,
        "phase_paragraph": phase_para,
        "practical_paragraph": practical,
        "watch_paragraph": watch,
        "at_a_glance": (
            f"Moon in {moon_sign} ({element or 'lunar'} tone) | "
            f"{_ordinal(moon_house)} from {lagna} rising | {phase} phase"
        ),
    }


def _practical_paragraph(
    *,
    name: str,
    moon_sign: str,
    moon_house: int,
    phase: str,
    is_new_moon_day: bool,
    element: str,
) -> str:
    tips: list[str] = []
    if moon_sign == "Taurus":
        tips.append("eat well and move slowly")
    elif moon_sign == "Gemini":
        tips.append("handle the one conversation you have been postponing")
    elif moon_sign == "Virgo":
        tips.append("tidy one corner or health habit")
    elif moon_sign == "Cancer":
        tips.append("cook or nest at home")
    elif moon_sign == "Leo":
        tips.append("show one talent without apology")
    else:
        tips.append(f"lean into {SIGN_DAY_FEEL.get(moon_sign, 'the lunar mood')}")

    if moon_house == 12:
        tips.append("guard an hour of solitude")
    elif moon_house == 9:
        tips.append("read or plan something that expands your horizon")
    elif moon_house == 10:
        tips.append("make one professional move visible")
    elif moon_house == 7:
        tips.append("give a partner or ally your full attention")
    elif moon_house == 4:
        tips.append("touch base with home or family")

    if phase == "Balsamic Moon" and not is_new_moon_day:
        tips.append("sleep a little earlier than usual")

    joined = "; ".join(tips[:3])
    return f"Practical steer for {name}: {joined.capitalize()}."


def _watch_paragraph(*, moon_sign: str, moon_house: int, phase: str) -> str:
    pitfalls: list[str] = []
    if moon_sign == "Taurus":
        pitfalls.append("stubborn stand-offs over comfort or money")
    if moon_sign == "Gemini":
        pitfalls.append("scattered chatter that wastes the morning")
    if moon_sign == "Scorpio":
        pitfalls.append("digs that turn into suspicion")
    if moon_house == 12:
        pitfalls.append("doom-scrolling when you need real rest")
    if moon_house == 8:
        pitfalls.append("forcing joint-money talks while reactive")
    if phase == "Full Moon":
        pitfalls.append("blaming others during an emotional spike")

    if not pitfalls:
        return ""
    return f"Watch for: {', '.join(pitfalls[:2])}."
