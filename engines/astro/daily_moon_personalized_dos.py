#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Human, chart-personalized Do/Don't lines for the daily Moon guide."""
from __future__ import annotations

from datetime import date
from typing import Any

from ashtakavarga_analysis import HOUSE_LIFE_THEME, PLANET_THEME
from lunation_timing import is_new_moon_applicable
from vedic_jaimini_report import PERIOD_PLAIN as JAIMINI_SIGN_PLAIN
from daily_moon_rules_data import (
    CHANDRA_RULES,
    HOUSE_ACTIONS,
    TARABALA_RULES,
    pick_variant,
)

# Today's mood when Moon transits this nakshatra (not birth-text from books).
NAK_TRANSIT_MOOD: dict[str, dict[str, str]] = {
    "Ashwini": {
        "do": "move quickly on one small fix - energy is restless and wants a win before noon.",
        "dont": "don't start three things at once; pick one lane and finish it.",
    },
    "Bharani": {
        "do": "finish something you've been avoiding - the day supports closure more than fresh starts.",
        "dont": "don't pick fights over money or control; let small irritations pass.",
    },
    "Krittika": {
        "do": "cut clutter - donate, delete, or simplify one corner of home or inbox.",
        "dont": "don't speak sharply when you're only half-listening.",
    },
    "Rohini": {
        "do": "treat your body kindly - good food, unhurried comfort, and steady pacing beat hustle today.",
        "dont": "don't ignore a scratchy throat or fatigue; rest before you push harder.",
    },
    "Mrigashira": {
        "do": "follow one curious thread - research, explore, or take a short walk that clears your head.",
        "dont": "don't scatter your attention across ten tabs and call it productivity.",
    },
    "Ardra": {
        "do": "name what you're feeling out loud to someone safe - storms pass faster when they're witnessed.",
        "dont": "don't send the angry message; draft it, breathe, revisit tomorrow.",
    },
    "Punarvasu": {
        "do": "reconnect with someone who once felt like home - a call, voice note, or warm meal.",
        "dont": "don't repeat an old argument expecting a new ending.",
    },
    "Pushya": {
        "do": "nurture - cook, check on family, or mentor someone with patience.",
        "dont": "don't over-give until you're resentful; boundaries still matter.",
    },
    "Ashlesha": {
        "do": "protect your peace - limit draining conversations and keep plans simple.",
        "dont": "don't manipulate outcomes with guilt or secrecy.",
    },
    "Magha": {
        "do": "honor lineage - thank an elder, tidy a photo, or own one proud family story.",
        "dont": "don't perform status for strangers; keep dignity private today.",
    },
    "Purva Phalguni": {
        "do": "make room for pleasure - music, romance, or creative play without apology.",
        "dont": "don't overspend to buy a mood that fades by evening.",
    },
    "Uttara Phalguni": {
        "do": "keep a promise you made - reliability lands better than charisma today.",
        "dont": "don't dodge a commitment because you're tired; renegotiate honestly instead.",
    },
    "Hasta": {
        "do": "use your hands - fix, craft, organise, or solve a practical puzzle step by step.",
        "dont": "don't nitpick yourself or others over tiny imperfections.",
    },
    "Chitra": {
        "do": "polish one visible thing - outfit, portfolio line, or how you present an idea.",
        "dont": "don't chase perfection on something no one will see this week.",
    },
    "Swati": {
        "do": "stay flexible - adjust plans without drama if the wind shifts.",
        "dont": "don't lock into rigid timelines when signals are still moving.",
    },
    "Vishakha": {
        "do": "focus ambition on one target - finish the hard middle, not just the exciting start.",
        "dont": "don't compete for applause; compete for completion.",
    },
    "Anuradha": {
        "do": "lean on your circle - ask for help, share a meal, or co-work quietly.",
        "dont": "don't go lone-wolf on something a friend could halve in an hour.",
    },
    "Jyeshtha": {
        "do": "handle the senior conversation with respect - listen first, advise second.",
        "dont": "don't challenge authority when you're actually seeking reassurance.",
    },
    "Mula": {
        "do": "pull one weed at the root - end a habit, subscription, or grudge that's costing you.",
        "dont": "don't burn bridges you'll need next month; cut cleanly, not theatrically.",
    },
    "Purva Ashadha": {
        "do": "declare what you believe - write it, say it, or recommit to a value quietly.",
        "dont": "don't preach; live the point in one small act instead.",
    },
    "Uttara Ashadha": {
        "do": "play the long game - schedule the follow-up, not just the launch.",
        "dont": "don't quit on day three of a discipline you chose on purpose.",
    },
    "Shravana": {
        "do": "listen more than you talk - someone is giving you a clue if you'll hear it.",
        "dont": "don't fill silence with noise just to feel busy.",
    },
    "Dhanishta": {
        "do": "celebrate a small win with people who showed up for you.",
        "dont": "don't compare your chapter to someone else's highlight reel.",
    },
    "Shatabhisha": {
        "do": "guard recovery time - sleep, hydrate, and limit stimulants.",
        "dont": "don't self-diagnose online and spiral; book the sensible check if worried.",
    },
    "Purva Bhadrapada": {
        "do": "channel intensity into one creative or spiritual outlet - journal, chant, or walk alone.",
        "dont": "don't doom-scroll when you need grounding.",
    },
    "Uttara Bhadrapada": {
        "do": "offer calm to someone stressed - your steadiness is useful today.",
        "dont": "don't absorb other people's panic as your own homework.",
    },
    "Revati": {
        "do": "close the loop gently - send the thank-you, return the call, release the grudge.",
        "dont": "don't start a journey without checking tickets, keys, and timing twice.",
    },
}

TARA_PERSONAL: dict[int, dict[str, str]] = {
    1: {
        "do": "Your birth star {natal_nak} is in Janma tara - treat today like a soft reboot. Rest, hydrate, and tie up loose ends only.",
        "dont": "Skip launches, big signatures, and new accounts - your chart is conserving vitality, not spending it.",
    },
    2: {
        "do": "Sampat tara favours your wallet - chase one pending payment or clear a small financial loose end.",
        "dont": "Don't lend large amounts on a handshake today; get it in writing or wait.",
    },
    3: {
        "do": "Vipat tara means friction - build a Plan B for commute, meetings, and tech before you need it.",
        "dont": "Don't bet on perfect timing; leave buffer space in the calendar.",
    },
    4: {
        "do": "Kshema tara steadies home base - fix one comfort detail (meal, bed, desk) and eat on time.",
        "dont": "Don't ignore a nagging health signal because you're 'too busy'.",
    },
    5: {
        "do": "Pratyari tara stirs people-static - listen first, document agreements, and keep tone neutral.",
        "dont": "Avoid provocative posts, sarcasm, and ultimatums in chat.",
    },
    6: {
        "do": "Sadhaka tara helps you finish - close one competitive task before sunset and move your body.",
        "dont": "Don't skip lunch while grinding; your energy collapses faster than you think.",
    },
    7: {
        "do": "Vadha tara asks for low stakes - handle routine work and keep exposure modest.",
        "dont": "Defer hostile negotiations, elective risks, and adrenaline gambles.",
    },
    8: {
        "do": "Mitra tara opens allies - book a working session with someone who gets your work.",
        "dont": "Don't isolate when collaboration would solve the block in an hour.",
    },
    9: {
        "do": "Parama Mitra is a bright window - schedule the pitch, prayer, or study block you've postponed.",
        "dont": "Don't waste the window on passive scrolling when action is supported.",
    },
}

CHANDRA_PERSONAL: dict[int, dict[str, str]] = {
    1: {"do": "Chandrabal sits on your birth Moon sign - move gently and be honest with yourself about what you feel.", "dont": "Don't issue emotional ultimatums to people you care about."},
    2: {"do": "Moon-sign energy supports speech about money - state a boundary kindly.", "dont": "Don't soothe mood with impulse shopping."},
    3: {"do": "Short trips and messages need backup plans today.", "dont": "Don't fire off sarcastic replies you'll regret."},
    4: {"do": "Home and mother-linked routines want attention - one tidy corner helps.", "dont": "Don't pick property or family fights when you're tired."},
    5: {"do": "Creative spark is live - give yourself twenty minutes of play.", "dont": "Don't gamble time or money on a hunch."},
    6: {"do": "Service and health tasks convert well - finish one chore early.", "dont": "Don't marathon tasks on an empty stomach."},
    7: {"do": "Partnership talks go better when you listen fully.", "dont": "Don't sign partnership papers while reactive."},
    8: {"do": "Deep research pays off - update passwords, insurance, or joint-money details.", "dont": "Don't poke sleeping conflicts for drama."},
    9: {"do": "Fortune lane is open - thank a mentor or read ten pages that uplift you.", "dont": "Don't post cynical takes about faith, teachers, or study."},
    10: {"do": "Career visibility is activated - ship one professional deliverable.", "dont": "Don't fight authority in public today."},
    11: {"do": "Gains and networks hum - ping an ally with a concrete ask.", "dont": "Don't boast about money you haven't banked yet."},
    12: {"do": "Release something - donate, discard, or protect sleep early.", "dont": "Don't let late-night scrolling steal tomorrow's clarity."},
}

AD_PERSONAL: dict[str, tuple[str, str]] = {
    "Sun": ("Let someone else take the spotlight once today - your {ad} antardasha clears when ego softens.", "Sun antardasha"),
    "Moon": ("Eat on time and check in with family - {ad} antardasha rewards emotional steadiness.", "Moon antardasha"),
    "Mars": ("Burn energy constructively: walk, gym, or finish a hard task - don't let {ad} antardasha become irritability.", "Mars antardasha"),
    "Mercury": ("Write the email, study block, or invoice before lunch - {ad} antardasha loves clean communication.", "Mercury antardasha"),
    "Jupiter": ("Teach or thank one person who helped you learn - {ad} antardasha expands through gratitude.", "Jupiter antardasha"),
    "Venus": ("Grooming and warmth matter - dress with care and say something kind to your closest person.", "Venus antardasha"),
    "Saturn": ("Do one boring-but-necessary task without complaint - {ad} antardasha respects discipline over drama.", "Saturn antardasha"),
    "Rahu": ("Channel hunger into one bold but legal move; skip shortcuts that need explaining later.", "Rahu antardasha"),
    "Ketu": ("Give away one thing you don't need or feed a stray animal - {ad} antardasha lightens when you let go.", "Ketu antardasha"),
}

PD_PERSONAL: dict[str, tuple[str, str]] = {
    "Sun": ("Pratyantar Sun wants one clean leadership act - send the update, don't grandstand.", "Sun pratyantar"),
    "Moon": ("Pratyantar Moon favours comfort rituals - eat on time and touch base with someone who feels like home.", "Moon pratyantar"),
    "Mars": ("Pratyantar Mars is hot - channel it into exercise or finishing one stubborn task before noon.", "Mars pratyantar"),
    "Mercury": ("Pratyantar Mercury rewards a focused inbox block - one thread, one outcome.", "Mercury pratyantar"),
    "Jupiter": ("Pratyantar Jupiter opens a mentor door - thank a teacher or read one chapter that upgrades your thinking.", "Jupiter pratyantar"),
    "Venus": ("Pratyantar Venus colours today - one small pleasure (food, music, grooming) without overspending.", "Venus pratyantar"),
    "Saturn": ("Pratyantar Saturn respects boring follow-through - tick one admin task you've postponed.", "Saturn pratyantar"),
    "Rahu": ("Pratyantar Rahu is restless - pick one bold but legal move instead of five half-starts.", "Rahu pratyantar"),
    "Ketu": ("Pratyantar Ketu asks for quiet release - donate, delete, or skip one draining commitment.", "Ketu pratyantar"),
}

WEEKDAY_COLOR_HINT: dict[str, str] = {
    "Sun": "white, cream, or gold",
    "Moon": "white or pearl",
    "Mars": "red or coral",
    "Mercury": "green",
    "Jupiter": "yellow or saffron",
    "Venus": "white or pastel pink",
    "Saturn": "navy, black, or charcoal",
}


def _first_name(client: str) -> str:
    return (client or "You").strip().split()[0]


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def _item(text: str, source: str = "") -> dict[str, str]:
    return {"text": text, "source": source}


def _day_seed(target: date, *parts: Any) -> int:
    raw = f"{target.isoformat()}|{'|'.join(str(p) for p in parts)}"
    return sum(ord(c) for c in raw) % 9973


def build_personalized_dos_donts(
    *,
    client: str,
    target: date,
    natal_moon_sign: str,
    natal_moon_nak: str,
    lagna: str,
    moon_transit: dict[str, Any],
    sun_transit: dict[str, Any],
    merc_transit: dict[str, Any],
    tara_idx: int,
    chandra_idx: int,
    weekday_lord: str,
    md_lord: str,
    ad_lord: str,
    pd_lord: str = "",
    jaimini_pd_sign: str = "",
    moon_aus: bool,
    moon_inaus: bool,
    sun_aus: bool,
    sun_inaus: bool,
    merc_aus: bool,
    merc_inaus: bool,
    moon_sav: int,
    moon_bav: int,
    slow_notes: list[str],
    moon_phase: str = "",
    new_moon_applicable: bool = False,
) -> tuple[list[dict[str, str]], list[dict[str, str]], str]:
    """Return conversational Do/Don't lists plus a one-line intro for the report."""
    name = _first_name(client)
    seed = _day_seed(target, natal_moon_nak, moon_transit.get("house_from_moon"), tara_idx, ad_lord, pd_lord)
    moon_h = int(moon_transit.get("house_from_moon", 1))
    moon_sign = moon_transit.get("sign", "")
    transit_nak = moon_transit.get("nakshatra", "")
    theme = HOUSE_LIFE_THEME.get(moon_h, "today's emotional focus")

    must_dos: list[dict[str, str]] = []
    must_donts: list[dict[str, str]] = []
    extra_dos: list[dict[str, str]] = []
    extra_donts: list[dict[str, str]] = []

    colors = WEEKDAY_COLOR_HINT.get(weekday_lord, "a calm neutral")
    must_dos.append(_item(
        f"{name}, lean into {colors} today - {target.strftime('%A')} answers to {weekday_lord}, "
        f"and that colour steadies your {PLANET_THEME.get(weekday_lord, 'day')} without feeling costume-y.",
        f"rules40/41 weekday {weekday_lord}",
    ))

    tara_tpl = TARA_PERSONAL.get(tara_idx, TARA_PERSONAL[1])
    must_dos.append(_item(
        tara_tpl["do"].format(natal_nak=natal_moon_nak),
        f"Tarabala/{TARABALA_RULES[tara_idx]['name']}",
    ))
    must_donts.append(_item(
        tara_tpl["dont"].format(natal_nak=natal_moon_nak),
        f"Tarabala/{TARABALA_RULES[tara_idx]['name']}",
    ))

    house_do = pick_variant(HOUSE_ACTIONS.get(moon_h, {}).get("dos", []), seed)
    house_dont = pick_variant(HOUSE_ACTIONS.get(moon_h, {}).get("donts", []), seed + 1)
    if house_do:
        text = house_do[0]
        must_dos.append(_item(
            f"Moon crosses your {_ordinal(moon_h)} house from birth {natal_moon_sign} Moon ({theme}) "
            f"in {moon_sign} - {text[0].lower() + text[1:] if text and text[0].isupper() else text}",
            house_do[1],
        ))
    if house_dont:
        text = house_dont[0]
        must_donts.append(_item(
            f"With Moon lighting your {_ordinal(moon_h)} house from natal Moon, "
            f"{text[0].lower() + text[1:] if text and text[0].isupper() else text}",
            house_dont[1],
        ))

    if chandra_idx != tara_idx:
        ch = CHANDRA_PERSONAL.get(chandra_idx, {})
        if ch.get("do"):
            extra_dos.append(_item(ch["do"], f"Chandrabal/{CHANDRA_RULES[chandra_idx]['name']}"))
        if ch.get("dont"):
            extra_donts.append(_item(ch["dont"], f"Chandrabal/{CHANDRA_RULES[chandra_idx]['name']}"))

    nak_mood = NAK_TRANSIT_MOOD.get(transit_nak, {})
    if nak_mood.get("do"):
        extra_dos.append(_item(
            f"Moon is in {transit_nak} today - {nak_mood['do']}",
            f"Transit nakshatra {transit_nak}",
        ))
    if nak_mood.get("dont"):
        extra_donts.append(_item(
            f"While Moon travels {transit_nak}, {nak_mood['dont']}",
            f"Transit nakshatra {transit_nak}",
        ))

    if new_moon_applicable:
        must_dos.append(_item(
            f"New Moon window is live - after your main work, do the wish ritual; your {moon_sign} Moon supports planting intentions now.",
            "rules44 New Moon",
        ))

    if pd_lord and pd_lord in PD_PERSONAL:
        line, src = PD_PERSONAL[pd_lord]
        must_dos.append(_item(line, src))

    if jaimini_pd_sign and jaimini_pd_sign in JAIMINI_SIGN_PLAIN:
        raw = JAIMINI_SIGN_PLAIN[jaimini_pd_sign]
        plain = raw.split(" - ")[0].strip() if " - " in raw else raw[:80].strip()
        must_dos.append(_item(
            f"Jaimini pratyantar is in {jaimini_pd_sign} - {plain.lower()}.",
            f"Jaimini Chara pratyantar {jaimini_pd_sign}",
        ))

    if ad_lord and ad_lord in AD_PERSONAL:
        line, src = AD_PERSONAL[ad_lord]
        extra_dos.append(_item(line.format(ad=ad_lord), src))

    if merc_aus:
        extra_dos.append(_item(
            f"Mercury is in a friendly lane from your Moon - send the important email or study block "
            f"before lunch while your {natal_moon_sign} mind is clearest.",
            "Bhardwaj gochar Mercury",
        ))
    elif merc_inaus:
        extra_donts.append(_item(
            "Mercury is scratchy from your Moon today - read fine print twice and avoid rushed signatures.",
            "Bhardwaj gochar Mercury",
        ))

    if sun_aus:
        extra_dos.append(_item(
            f"Sun supports visibility from your Moon - use late morning for one authority task that matters to your {lagna} rising chart.",
            "Bhardwaj gochar Sun",
        ))
    elif sun_inaus:
        extra_donts.append(_item(
            f"Sun is pressuring your gochar houses today, {name} - keep power plays modest and let results speak.",
            "Bhardwaj gochar Sun",
        ))

    if moon_aus:
        extra_dos.append(_item(
            "Emotional initiatives get a green light - say what you feel to the right person, not the whole feed.",
            "Bhardwaj gochar Moon",
        ))
    elif moon_inaus:
        extra_donts.append(_item(
            "Moon's gochar lane is tense - defer emotional ultimatums until you've slept on them.",
            "Bhardwaj gochar Moon",
        ))

    if moon_sav >= 30:
        extra_dos.append(_item(
            f"Moon crosses a strong {moon_sav}-point sign for you - push one deliverable in {theme} before the day dissolves.",
            "rules10 SAV",
        ))
    elif moon_sav < 25:
        extra_donts.append(_item(
            f"Moon is in a thin {moon_sav}-point zone - over-promise on {theme} and you'll be chasing proof all week.",
            "rules10 SAV",
        ))

    for note in slow_notes[:1]:
        if "stressed gochar" in note.lower() or "pace major" in note.lower():
            pl = note.split()[1] if len(note.split()) > 1 else "a slow planet"
            extra_donts.append(_item(
                f"{pl} is leaning on your Moon emotionally - don't force a big decision in that area today; observe one more cycle.",
                "Slow-graha confluence",
            ))

    def _dedupe(items: list[dict]) -> list[dict]:
        seen: set[str] = set()
        out: list[dict] = []
        for it in items:
            t = it["text"]
            if t in seen:
                continue
            seen.add(t)
            out.append(it)
        return out

    def _fill(must: list[dict], extra: list[dict], cap: int = 5) -> list[dict]:
        combined = _dedupe(must + extra)
        if len(must) >= cap:
            return must[:cap]
        return combined[:cap]

    dos = _fill(must_dos, extra_dos)
    donts = _fill(must_donts, extra_donts)

    stack = "-".join(x for x in (md_lord, ad_lord, pd_lord) if x)
    jai_bit = f", Jaimini {jaimini_pd_sign} pratyantar" if jaimini_pd_sign else ""
    intro = (
        f"Written for {name}'s chart: natal Moon in {natal_moon_sign}/{natal_moon_nak}, "
        f"{lagna} rising, today Moon in {moon_sign}/{transit_nak} ({_ordinal(moon_h)} from birth Moon), "
        f"{TARABALA_RULES[tara_idx]['name']} tara, Vim {stack}{jai_bit}."
    )
    return dos[:5], donts[:5], intro
