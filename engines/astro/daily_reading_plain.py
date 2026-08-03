#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plain-English daily Vedic reading - human astrologer voice, not book jargon."""
from __future__ import annotations

from typing import Any

from ashtakavarga_analysis import HOUSE_LIFE_THEME, PLANET_THEME

# Short house labels for everyday speech.
HOUSE_SHORT = {
    1: "how you show up and start things",
    2: "money habits and family talk",
    3: "messages, siblings, and small trips",
    4: "home, comfort, and emotional grounding",
    5: "creativity, romance, and children",
    6: "daily work, health routines, and problem-solving",
    7: "partnerships and one-to-one deals",
    8: "shared money, research, and deep change",
    9: "beliefs, teachers, travel, and luck",
    10: "career, reputation, and public image",
    11: "friends, income ideas, and gains",
    12: "rest, expenses, and letting go",
}

KARAKA_ROLE_PLAIN = {
    "Atmakarak": "what your soul is nudging you toward",
    "Amatyakarak": "work and professional standing",
    "Putrakaraka": "creativity, study, and children",
    "Matrukaraka": "home and mother-linked themes",
    "Bhratrukaraka": "siblings, peers, and teamwork",
    "Gnatikaraka": "stress points, rivals, and health friction",
    "Darakaraka": "partner, marriage, and close bonds",
}

VIM_CHAPTER_PLAIN = {
    "Sun": "a chapter about stepping into the spotlight and owning your authority",
    "Moon": "a chapter coloured by feelings, family, and where you feel safe",
    "Mars": "a chapter that rewards courage, direct action, and healthy competition",
    "Mercury": "a chapter favouring study, deals, writing, and smart networking",
    "Jupiter": "a longer growth phase - mentors, learning, and fair expansion",
    "Venus": "a chapter about love, comfort, taste, and earning through what you enjoy",
    "Saturn": "a slower chapter where discipline and reputation are built brick by brick",
    "Rahu": "a restless chapter - ambition, foreign links, and unconventional moves",
    "Ketu": "an inward chapter - letting go, research, and fewer material attachments",
}

VIM_TODAY_PLAIN = {
    "Sun": "today favours one visible task - lead calmly, avoid ego battles",
    "Moon": "feelings run close to the surface - honour rest and family tone",
    "Mars": "energy is up - act on one priority, don't vent through arguments",
    "Mercury": "mail, study, and paperwork convert if you organise first",
    "Jupiter": "mentors and modest growth help - don't over-promise",
    "Venus": "comfort, warmth, and relationship ease are available",
    "Saturn": "boring, steady tasks pay off - shortcuts backfire",
    "Rahu": "restless appetite for change - ground one practical move",
    "Ketu": "quiet inward work - release one draining habit or commitment",
}

JAIMINI_SIGN_DAILY = {
    "Aries": "competitive spark - push one goal, skip pointless fights",
    "Taurus": "steady comfort - invest in quality, not speed",
    "Gemini": "talk, learn, and connect - finish what you start",
    "Cancer": "home and feelings first - nurture before you negotiate",
    "Leo": "visibility and pride - perform, but stay generous",
    "Virgo": "detail and service - fix one messy corner of life",
    "Libra": "balance in relationships - charm works, indecision doesn't",
    "Scorpio": "depth and intensity - probe, don't dramatise",
    "Sagittarius": "big-picture optimism - travel, teach, or plan ahead",
    "Capricorn": "duty and structure - respect timelines and elders",
    "Aquarius": "networks and causes - choose your circle wisely",
    "Pisces": "intuition and retreat - soften edges, avoid escapism",
}

TARA_PLAIN = {
    "Janma": "the day mirrors your inner weather - move gently with your mood",
    "Sampat": "resources and small gains open more easily than usual",
    "Vipat": "expect a bump or two - keep plans flexible",
    "Kshema": "security and recovery themes - good for stabilising routines",
    "Pratyak": "opposition energy - compromise beats confrontation",
    "Sadhaka": "effort converts - a solid day for purposeful work",
    "Naidhana": "thin for big risks - handle essentials and rest",
    "Mitra": "allies and goodwill help - reach out to the right people",
    "Ati-Mitra": "strong friendly backing - collaborations can click",
}

CHANDRA_PLAIN = {
    "Janma Rasi": "emotional sensitivity is high - protect your peace",
    "Sampat Rasi": "money and comfort themes feel supportive",
    "Vipat Rasi": "minor irritations may surface - don't take bait",
    "Kshema Rasi": "body and routine favour calm, restorative choices",
    "Pratyak Rasi": "others may push back - stay diplomatic",
    "Sadhaka Rasi": "confidence and follow-through are stronger than average",
    "Naidhana Rasi": "low reserves - postpone heavy emotional labour",
    "Mitra Rasi": "social warmth helps the day flow",
    "Ati-Mitra Rasi": "people genuinely want to help - accept support",
}


def _short_house(h: int) -> str:
    return HOUSE_SHORT.get(int(h), "this part of life")


def _bav_plain(planet: str, bav: int) -> str:
    pt = PLANET_THEME.get(planet, planet.lower())
    if bav >= 6:
        return f"{planet} ({pt}) has a clear runway"
    if bav >= 5:
        return f"{planet} ({pt}) moves well with steady effort"
    if bav >= 4:
        return f"{planet} ({pt}) progresses in stops and starts"
    if bav >= 3:
        return f"{planet} ({pt}) needs tighter focus - avoid parallel bets"
    return f"{planet} ({pt}) is under pressure - protect energy and skip gambles"


def _karaka_bullet(row: dict[str, Any]) -> str:
    planet = row.get("planet", "")
    bav = int(row.get("bav", 4))
    if bav >= 5:
        return f"{planet} has a helpful tailwind here - lean in if it feels right."
    if bav >= 4:
        return f"{planet} moves in fits and starts - one focused block beats multitasking."
    if bav >= 3:
        return f"{planet} needs patience - do not force outcomes before they ripen."
    return f"{planet} is under strain - protect your energy and keep stakes modest."


def _karaka_hint(row: dict[str, Any]) -> str:
    role = row.get("role", "")
    theme = KARAKA_ROLE_PLAIN.get(role, "life themes")
    bullet = _karaka_bullet(row)
    if row.get("in_sign"):
        return f"For {theme}, {bullet} This area is directly lit up right now."
    if row.get("aspected"):
        return f"For {theme}, {bullet} Support is in the background if you stay steady."
    return f"For {theme}, {bullet}"


def _jaimini_plain_paragraph(jaimini_conf: dict[str, Any]) -> str:
    if not jaimini_conf.get("available"):
        return ""
    parts: list[str] = []
    antar = next((x for x in jaimini_conf.get("levels", []) if x["level"] == "antar"), None)
    pd = next((x for x in jaimini_conf.get("levels", []) if x["level"] == "pd"), None)
    if antar:
        sign = antar["sign"]
        flavour = JAIMINI_SIGN_DAILY.get(sign, antar.get("sign_theme", ""))
        parts.append(
            f"A second timing clock points at {sign} energy this week - {flavour}."
        )
        hints = [_karaka_hint(r) for r in antar.get("karakas", [])[:2]]
        if hints:
            parts.append(" ".join(hints))
    if pd:
        sign = pd["sign"]
        flavour = JAIMINI_SIGN_DAILY.get(sign, pd.get("sign_theme", ""))
        parts.append(f"The sharpest slice of today sits in {sign}: {flavour}.")
    return " ".join(parts)


def _gk_plain(gk: dict[str, Any], karmic: bool) -> str:
    if not gk.get("available"):
        return ""
    if gk.get("supportive"):
        return (
            "Slow-moving planets are backing your current life chapter today - "
            "when you act, the sky is more likely to meet you halfway."
        )
    if karmic:
        return (
            "Even when the day looks good on paper, results may feel delayed or "
            "benefit others before they reach you - keep expectations modest."
        )
    if gk.get("dampened"):
        return "Good ideas may need an extra push to land - persistence beats timing today."
    return (
        "Your long-term life chapter is setting the tone; today's sky is not adding "
        "a dramatic push either way - rely on your own rhythm."
    )


def _boney_plain(ad_boney: dict[str, Any], ad: str) -> str:
    if not ad_boney.get("available") or not ad:
        return ""
    tier = ad_boney.get("tier", "")
    if tier in ("strong_both", "upgrade"):
        return (
            f"The sub-chapter ruled by {ad} has solid inner backing - "
            "promises made now are more likely to stick."
        )
    if tier in ("weak_both", "downgrade"):
        return (
            f"The sub-chapter ruled by {ad} is running on mixed inner fuel - "
            "under-promise and over-deliver."
        )
    return ""


def _moon_plain(
    moon_sign: str,
    moon_h: int,
    tara: dict[str, Any],
    chandra: dict[str, Any],
    moon_aus: bool,
    moon_inaus: bool,
) -> str:
    theme = _short_house(moon_h)
    tara_name = tara.get("name", "")
    chandra_name = chandra.get("name", "")
    tara_bit = TARA_PLAIN.get(tara_name, "")
    chandra_bit = CHANDRA_PLAIN.get(chandra_name, "")
    bits = [
        f"The Moon is in {moon_sign} today, stirring {theme} for you.",
    ]
    if tara_bit:
        bits.append(tara_bit[0].upper() + tara_bit[1:] + ".")
    if chandra_bit and chandra_bit != tara_bit:
        bits.append(chandra_bit[0].upper() + chandra_bit[1:] + ".")
    if moon_aus:
        bits.append("Emotional initiatives get a modest green light.")
    elif moon_inaus:
        bits.append("Keep emotional stakes low - reactions may run hotter than facts.")
    return " ".join(bits)


def _vim_background(md: str, ad: str, pc: dict, lagna: str) -> str:
    md_bit = VIM_CHAPTER_PLAIN.get(md, "")
    ad_bit = VIM_TODAY_PLAIN.get(ad, "")
    parts = []
    if md_bit:
        parts.append(f"In the background of your life, {md_bit.rstrip('.')}.")
    if ad_bit:
        pl = pc.get("planets", {}).get(ad, {})
        h = int(pl.get("house") or 1)
        parts.append(
            f"Right now the {ad} phase asks you to {ad_bit.rstrip('.')}. "
            f"That theme links to {_short_house(h)} in your chart."
        )
    return " ".join(parts)


def _vim_today(pd: str, pc: dict, lagna: str) -> str:
    if not pd:
        return ""
    bit = VIM_TODAY_PLAIN.get(pd, "").rstrip(".")
    pl = pc.get("planets", {}).get(pd, {})
    h = int(pl.get("house") or 1)
    return f"Today's finest timing sits with {pd}: {bit}. This colours {_short_house(h)}."


def _slow_note_plain(note: str) -> str:
    if not note:
        return ""
    low = note.lower()
    if "jupiter" in low and "supportive" in low:
        return "Jupiter is quietly backing you from the friendship-and-gains corner of your chart - helpful allies or income ideas may surface."
    if "saturn" in low and ("pressure" in low or "caution" in low):
        return "Saturn asks for patience today - respect deadlines and avoid shortcuts."
    if "mars" in low:
        return "Mars adds extra drive - channel it into one task, not arguments."
    if "sav" in low or "bav" in low:
        return ""
    return note.split(";")[0].strip() + "."


def _triggers_plain(vim_hits: list[str], jai_hits: list[str], moon_sign: str) -> str:
    bits = []
    if vim_hits:
        bits.append(
            f"The Moon in {moon_sign} touches planets that rule your current life timing "
            f"({', '.join(vim_hits)}) - moods and events may feel personally pointed."
        )
    if jai_hits:
        bits.append(
            f"The Moon also echoes your parallel timing sign ({', '.join(jai_hits)}) - "
            "a day when inner and outer clocks align."
        )
    return " ".join(bits)


def _gochar_plain(
    moon_aus: bool,
    moon_inaus: bool,
    sun_aus: bool,
    sun_inaus: bool,
    merc_aus: bool,
    merc_inaus: bool,
) -> str:
    bits = []
    if sun_aus:
        bits.append("One visible task or leadership moment can land well.")
    elif sun_inaus:
        bits.append("Authority moves need humility - don't force the spotlight.")
    if merc_aus:
        bits.append("Mail, study, and signatures flow better before noon.")
    elif merc_inaus:
        bits.append("Double-check messages and contracts - rushed words slip.")
    return " ".join(bits)


def _verdict_plain(verdict: str) -> str:
    mapping = {
        "supportive for steady progress when Vim and Jaimini clocks are respected - avoid rash launches.": (
            "Overall: a workable day for steady progress - move with your timing, not against it."
        ),
        "thin for big bets; handle essentials, rest, and low-stakes tasks.": (
            "Overall: not a day for big bets - handle essentials, rest, and keep stakes low."
        ),
        "mixed; use the morning for clarity work and keep the afternoon flexible.": (
            "Overall: mixed - use the morning for clarity, keep the afternoon flexible."
        ),
    }
    return mapping.get(verdict, verdict)


def build_plain_daily_reading(
    *,
    name: str,
    md: str,
    ad: str,
    pd: str,
    pc: dict,
    lagna: str,
    moon_sign: str,
    moon_h: int,
    tara: dict[str, Any],
    chandra: dict[str, Any],
    moon_aus: bool,
    moon_inaus: bool,
    sun_aus: bool,
    sun_inaus: bool,
    merc_aus: bool,
    merc_inaus: bool,
    jaimini_conf: dict[str, Any],
    gk: dict[str, Any],
    karmic: bool,
    ad_boney: dict[str, Any],
    vim_hits: list[str],
    jai_hits: list[str],
    dual_agree: str,
    slow_notes: list[str],
    verdict: str,
    jai_stack: str = "",
) -> dict[str, Any]:
    """Return structured plain-English paragraphs for the daily Vedic block."""
    first = name.strip().split()[0] if name else "You"

    background = _vim_background(md, ad, pc, lagna)
    today_slice = _vim_today(pd, pc, lagna)
    jaimini_bit = _jaimini_plain_paragraph(jaimini_conf)
    moon_bit = _moon_plain(moon_sign, moon_h, tara, chandra, moon_aus, moon_inaus)
    gochar_bit = _gochar_plain(moon_aus, moon_inaus, sun_aus, sun_inaus, merc_aus, merc_inaus)
    trigger_bit = _triggers_plain(vim_hits, jai_hits, moon_sign)
    gk_bit = _gk_plain(gk, karmic)
    boney_bit = _boney_plain(ad_boney, ad)

    paragraphs: list[str] = []
    if background:
        paragraphs.append(background)
    if today_slice:
        paragraphs.append(today_slice)
    if jaimini_bit:
        paragraphs.append(jaimini_bit)
    if moon_bit:
        paragraphs.append(moon_bit)
    if gochar_bit:
        paragraphs.append(gochar_bit)
    if trigger_bit:
        paragraphs.append(trigger_bit)
    if gk_bit:
        paragraphs.append(gk_bit)
    if boney_bit:
        paragraphs.append(boney_bit)
    if dual_agree and "concur" in dual_agree.lower():
        paragraphs.append(
            "Both major timing systems agree on today's theme - when you feel a pull, trust it."
        )
    if slow_notes:
        sn = _slow_note_plain(slow_notes[0])
        if sn:
            paragraphs.append(sn)

    verdict_plain = _verdict_plain(verdict)
    paragraphs.append(verdict_plain)

    return {
        "paragraphs": paragraphs,
        "reading": "\n\n".join(paragraphs),
        "verdict_plain": verdict_plain,
        "work_hint": _work_hint(jaimini_conf),
        "personal_hint": _personal_hint(jaimini_conf, pd, pc),
    }


def _work_hint(jaimini_conf: dict[str, Any]) -> str:
    antar = next((x for x in jaimini_conf.get("levels", []) if x["level"] == "antar"), None)
    if not antar:
        return ""
    amk = next((r for r in antar.get("karakas", []) if r["role"] == "Amatyakarak"), None)
    if not amk:
        return ""
    base = _karaka_bullet(amk)
    if amk.get("aspected"):
        return f"{base} Career energy is building quietly - steady output beats a dramatic push."
    return base


def _personal_hint(jaimini_conf: dict[str, Any], pd: str, pc: dict) -> str:
    pd_lv = next((x for x in jaimini_conf.get("levels", []) if x["level"] == "pd"), None)
    if not pd_lv:
        return ""
    dk = next((r for r in pd_lv.get("karakas", []) if r["role"] == "Darakaraka"), None)
    pk = next((r for r in pd_lv.get("karakas", []) if r["role"] == "Putrakaraka"), None)
    bits = []
    if dk:
        bits.append(f"Relationships: {_karaka_bullet(dk)}")
    if pk:
        bits.append(f"Creativity and children: {_karaka_bullet(pk)}")
    return " ".join(bits)


def plain_jaimini_karaka_bullets(jaimini_conf: dict[str, Any]) -> list[dict[str, str]]:
    """Client-facing bullets for the Jaimini subsection."""
    if not jaimini_conf.get("available"):
        return []
    bullets: list[dict[str, str]] = []
    label_map = {
        "maha": "This year-phase",
        "antar": "This month-week phase",
        "pd": "Today's sharpest slice",
    }
    for lv in jaimini_conf.get("levels", []):
        sign = lv["sign"]
        flavour = JAIMINI_SIGN_DAILY.get(sign, lv.get("sign_theme", ""))
        head = f"{label_map.get(lv['level'], lv['label'])} ({sign}): {flavour}"
        bullets.append({"head": head, "detail": ""})
        for row in lv.get("karakas", [])[:3]:
            bullets.append({
                "head": KARAKA_ROLE_PLAIN.get(row["role"], row["role"]),
                "detail": _karaka_bullet(row),
            })
    return bullets


def plain_opening(
    *,
    client: str,
    target,
    tone: str,
    moon_t: dict,
    tara: dict,
    chandra: dict,
    moon_h: int,
    verdict_plain: str,
) -> str:
    tone_word = {
        "bright": "a genuinely supportive",
        "mixed-positive": "a quietly promising",
        "steady": "a balanced, workmanlike",
        "mixed-caution": "a mixed-signal",
        "sensitive": "an emotionally thin",
    }.get(tone, "a nuanced")
    theme = _short_house(int(moon_h))
    tara_name = tara.get("name", "") if isinstance(tara, dict) else str(tara)
    chandra_name = chandra.get("name", "") if isinstance(chandra, dict) else str(chandra)
    return (
        f"{client}, {target.strftime('%A %d %B %Y')} opens with {tone_word} feel. "
        f"The Moon in {moon_t.get('sign', '')} stirs {theme}. "
        f"Star strength: {tara_name}; Moon strength: {chandra_name}. "
        f"{verdict_plain}"
    )
