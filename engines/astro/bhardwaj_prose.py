#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turn Bhardwaj book lines into plain, human astrologer prose."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

from bhardwaj_semantic import (
    DOMAIN_TITLE,
    lookup_house_lord,
    lookup_lagna_sign,
    lookup_planet_house,
    pick_book_clause,
    _personalize,
)

if TYPE_CHECKING:
    from bhardwaj_semantic import Cluster, Signal

HOUSE_PLAIN = {
    1: "self-image and vitality",
    2: "money, speech, and family",
    3: "courage, skills, and siblings",
    4: "home, mother, and peace of mind",
    5: "children, creativity, and learning",
    6: "health, service, and daily work",
    7: "marriage and partnerships",
    8: "long-term change, inheritance, and hidden matters",
    9: "luck, faith, travel, and father",
    10: "career, status, and public name",
    11: "income, gains, and fulfilment of wishes",
    12: "expenses, foreign lands, and spiritual life",
}

DIGNITY_PLAIN = {
    "exalted": "very strong (exalted)",
    "own_sign": "strong in its own sign",
    "moolatrikona": "very powerful (moolatrikona)",
    "great_friend_sign": "well supported",
    "debilitated": "under strain (debilitated)",
    "enemy_sign": "in a challenging sign",
    "neutral_sign": "moderately placed",
}

DOMAIN_LEAD = {
    "personality": "At the core, this is how you come across and how your mind works.",
    "career": "On the work front, your chart points to the following.",
    "finance": "For money and material comfort, Bhardwaj reads your chart this way.",
    "marriage": "In love and partnership, these are the main themes.",
    "children": "On children, creativity, and education, the book highlights this.",
    "health": "For health and stamina, pay attention to the following pattern.",
    "property": "Home, land, and domestic peace show up as follows.",
    "travel": "Luck, long journeys, and higher purpose align like this.",
    "spiritual": "For inner life, charity, and letting go, the chart suggests this.",
    "current": "Right now, this is the life chapter you are walking through.",
}

DOMAIN_TAKEAWAY = {
    "personality": "Use your natural strengths openly; work on habits that scatter your focus.",
    "career": "Build reputation slowly - your chart favours skill plus visibility, not shortcuts.",
    "finance": "Gains come through effort, property, and smart alliances; avoid risky speculation.",
    "marriage": "Patience and honesty in partnership matter more than speed.",
    "children": "Creative and educational pursuits need steady support, not pressure.",
    "health": "Routine care and calm routines protect you more than occasional extremes.",
    "property": "Invest in home comfort and good relations with family elders.",
    "travel": "Pilgrimage, study, and ethical living strengthen your luck.",
    "spiritual": "Simple weekly charity and prayer steady the mind.",
    "current": "Treat this sub-period as a turning lane - adjust pace, not purpose.",
}

PLANET_ROLE = {
    "Sun": "soul and authority",
    "Moon": "mind and emotions",
    "Mars": "drive and courage",
    "Mercury": "intellect and communication",
    "Jupiter": "wisdom and growth",
    "Venus": "love and comfort",
    "Saturn": "discipline and karma",
    "Rahu": "ambition and worldly hunger",
    "Ketu": "detachment and past patterns",
}

NAKSHATRA_SNIPPETS = {
    "Hasta": (
        "Hasta (Moon's star) gives a quick mind, business sense, and skill with the hands. "
        "You learn fast, speak well, and can turn ideas into practical work. "
        "Stay balanced - stress and skin or stomach sensitivity can flare when life is overloaded."
    ),
    "Ashwini": "Ashwini brings speed, healing energy, and a pioneer spirit.",
    "Rohini": "Rohini blesses charm, creativity, and love of beauty and comfort.",
    "Mrigashira": "Mrigashira adds curiosity, searching nature, and love of travel.",
    "Ardra": "Ardra gives sharp intelligence and intensity; emotions run deep.",
    "Punarvasu": "Punarvasu supports renewal, teaching, and coming back stronger after setbacks.",
    "Pushya": "Pushya is nourishing - duty, care, and steady growth.",
    "Ashlesha": "Ashlesha adds depth, intuition, and strong attachment to close bonds.",
    "Magha": "Magha connects to tradition, ancestors, and natural authority.",
    "Purva Phalguni": "Purva Phalguni favours romance, rest, and creative pleasure.",
    "Uttara Phalguni": "Uttara Phalguni supports marriage, contracts, and helpful patrons.",
    "Chitra": "Chitra brings design sense, pride in craft, and a striking personal style.",
    "Swati": "Swati favours trade, independence, and balanced relationships.",
    "Vishakha": "Vishakha drives ambition, debate, and goal-focused energy.",
    "Anuradha": "Anuradha supports loyalty, friendship, and success abroad.",
    "Jyeshtha": "Jyeshtha adds protectiveness, seniority, and sharp judgment.",
    "Mula": "Mula uproots the old so something truer can grow - intense but transformative.",
    "Purva Ashadha": "Purva Ashadha brings conviction, renewal, and love of water or travel.",
    "Uttara Ashadha": "Uttara Ashadha supports lasting victory through patience and dharma.",
    "Shravana": "Shravana favours listening, learning, and fame through knowledge.",
    "Dhanishtha": "Dhanishtha links to rhythm, wealth, and community visibility.",
    "Shatabhisha": "Shatabhisha adds research mind, healing, and need for private space.",
    "Purva Bhadrapada": "Purva Bhadrapada brings idealism, fire, and spiritual hunger.",
    "Uttara Bhadrapada": "Uttara Bhadrapada supports depth, charity, and calm endurance.",
    "Revati": "Revati blesses compassion, journeys, and safe completion of projects.",
}

YOGA_HUMAN = {
    "Panchmahapurusha - Malavya": (
        "Malavya Yoga (Venus in a power angle) adds grace, comfort, vehicles, fine taste, "
        "and an attractive, harmonious partner when other factors agree."
    ),
    "Amla Yoga": (
        "Amla Yoga (benefics in the 10th from lagna) supports fame, royal favour, "
        "talent, and a respectable public name."
    ),
    "Gajakesari Yoga": (
        "Gajakesari Yoga (Moon and Jupiter in mutual angles) gives wisdom, courage, "
        "merit, and protection in life."
    ),
    "Manglik Dosha": (
        "Mars sits in a marriage-sensitive house - Bhardwaj advises careful matching "
        "and simple Mars remedies rather than fear."
    ),
    "Lakshmi Yoga": (
        "Lakshmi Yoga links beauty, dharma, wealth, and blessings around children."
    ),
    "Lagnadhi Yoga": (
        "Lagnadhi Yoga (benefics around your rising sign) makes you learned, humble, "
        "and successful when you stay sincere."
    ),
}


def _moon_personality_phrase(sign: str) -> str:
    raw = LAGNA_HUMAN.get(sign, "")
    if not raw:
        return ""
    raw = re.sub(rf"^{sign}\s+rising\s+", "In private you are ", raw, flags=re.I)
    raw = re.sub(rf"^{sign}\s+colours the chart with\s+", "Your inner life is ", raw, flags=re.I)
    raw = raw.replace("Your inner life is practicality", "Your inner life is practical")
    raw = raw.replace("Your inner life is practical and detail-oriented - and a need", "You have a practical, detail-oriented inner life with a need")
    raw = re.sub(rf"^{sign}\s+adds\s+", "You ", raw, flags=re.I)
    raw = re.sub(rf"^{sign}\s+steadies the personality with\s+", "You feel steadied by ", raw, flags=re.I)
    raw = re.sub(rf"^{sign}\s+makes you\s+", "You ", raw, flags=re.I)
    return raw


MARRIAGE_LORD_PLAIN = {
    (7, 8): (
        "Marriage is ruled by your 7th lord in the house of deep change and shared resources. "
        "Bhardwaj notes worry around intimacy or urinary health, and phases where emotional closeness "
        "feels strained rather than easy. Patience, clear communication, and matching remedies matter "
        "more than rushing the wedding date."
    ),
}


def _ord(n: int) -> str:
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n if n < 20 else n % 10, 'th')}"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n if n < 20 else n % 10, 'th')}"


def dignity_plain(d: str) -> str:
    return DIGNITY_PLAIN.get(d, d.replace("_", " "))


def house_plain(h: int) -> str:
    return HOUSE_PLAIN.get(h, f"house {h}")


LAGNA_HUMAN = {
    "Aries": (
        "Aries rising gives a direct, energetic, and competitive edge. You like to lead, move fast, "
        "and prefer action over waiting. Fields linked to courage, sports, engineering, police, or independent work suit you."
    ),
    "Taurus": (
        "Taurus rising steadies the personality with patience, love of comfort, and strong will. You value "
        "security, good food, and lasting results. Arts, finance, property, and beauty-related work often appeal."
    ),
    "Gemini": (
        "Gemini rising makes you quick-minded, communicative, and curious. You learn fast and do well in writing, "
        "teaching, sales, media, or any role that uses speech and analysis."
    ),
    "Cancer": (
        "Cancer rising softens the outer personality with sensitivity, care, and attachment to home. You protect "
        "what you love, think with feeling, and often succeed in nurturing roles, trade, or work linked to people."
    ),
    "Leo": (
        "Leo rising adds confidence, pride, and natural authority. You want respect, dislike being ignored, "
        "and shine in leadership, politics, management, or creative visibility."
    ),
    "Virgo": (
        "Virgo colours the chart with practicality, detail, and a need to improve things. You notice errors others "
        "miss, work carefully, and suit education, accounts, health service, or technical fields."
    ),
    "Libra": (
        "Libra rising brings charm, balance, and social intelligence. You seek harmony, enjoy art and partnership, "
        "and often do well in law, design, counselling, or public-facing work."
    ),
    "Scorpio": (
        "Scorpio rising makes you intense, private, and hard to read. You have strong will, deep focus, "
        "and can succeed in research, investigation, surgery, metals, or crisis-handling roles."
    ),
    "Sagittarius": (
        "Sagittarius rising opens the life toward faith, travel, and big ideas. You think broadly, dislike "
        "petty limits, and suit teaching, law, publishing, foreign links, or advisory work."
    ),
    "Capricorn": (
        "Capricorn rising makes you serious, disciplined, and goal-oriented. You build slowly, respect structure, "
        "and often rise through management, government work, engineering, or long-term business."
    ),
    "Aquarius": (
        "Aquarius rising gives independence, social concern, and original thinking. You question old rules, "
        "like useful innovation, and fit industry, technology, social service, or reform-minded work."
    ),
    "Pisces": (
        "Pisces rising adds sensitivity, imagination, and compassion. You absorb atmosphere easily, need meaningful "
        "work, and often suit teaching, healing, arts, charity, or spiritual service."
    ),
}


def _fix_fragmented_periods(text: str) -> str:
    """Merge broken OCR fragments like 'word. next' into smooth sentences."""
    text = re.sub(r"\.\s+([a-z])", lambda m: ", " + m.group(1), text)
    text = re.sub(r",\s+,", ",", text)
    return text


def _dedupe_words(text: str) -> str:
    """Remove obvious repeated phrases in merged book lines."""
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+", text)
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        key = p.lower()[:60]
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return " ".join(out)


def humanize_book_line(line: str, domain: str = "", direction: str = "neutral") -> str:
    """Convert one OCR/book sentence into flowing plain English."""
    if not line:
        return ""
    t = _personalize(line)
    t = re.sub(r"\bSiddharambh\b", "success at the start of new work", t, flags=re.I)
    t = re.sub(r"\bopposite Raja Yoga\b", "a special Raja Yoga that turns obstacles into gain", t, flags=re.I)
    t = re.sub(r"\bdue to the a special\b", "through a special", t, flags=re.I)
    t = re.sub(r"\bManglik\b", "Mars pattern affecting marriage (Manglik)", t, flags=re.I)
    t = re.sub(r"\bdevoid of\b", "may lack", t, flags=re.I)
    t = re.sub(r"\bdeprived of\b", "may miss", t, flags=re.I)
    t = re.sub(r"\bthe govt\.?\b", "government", t, flags=re.I)
    t = re.sub(r"\bstate official\b", "government or official work", t, flags=re.I)
    t = re.sub(r"\broyal servant\b", "honoured by influential people", t, flags=re.I)
    t = re.sub(r"\broyal serving others\b", "honoured by influential people", t, flags=re.I)
    t = re.sub(r"\bYou will be periods of\b", "You may face periods of", t, flags=re.I)
    t = re.sub(r"\bYou will be prone to\b", "You may be prone to", t, flags=re.I)
    t = re.sub(r"\bYou will be eternally\b", "You may feel", t, flags=re.I)
    for sign in (
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
        "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    ):
        t = re.sub(rf"\b{sign.lower()}\b", sign, t, flags=re.I)

    harsh = {
        "filthy": "neglected",
        "humiliated": "undervalued",
        "servant": "serving others",
        "absurd": "unconventional",
        "lazy": "low-energy",
        "little progeny": "delays or fewer children than hoped",
        "afraid of water": "unease around water or travel",
        "devoid of happiness": "periods of emotional distance",
        "eternally anxious": "periods of worry",
        "sexual or urinary diseases": "sensitivity around intimacy or urinary health",
        "wife will have severe disease or will die after marriage": "marriage may face serious health or separation tests",
    }
    if domain in ("health", "current", "marriage") or direction == "caution":
        for old, new in harsh.items():
            t = re.sub(rf"\b{re.escape(old)}\b", new, t, flags=re.I)

    if t.count(",") >= 4:
        chunks = [c.strip() for c in t.split(",") if c.strip()]
        if len(chunks) >= 4:
            mid = min(3, len(chunks) // 2)
            t = ", ".join(chunks[:mid]).rstrip(".") + ". " + ", ".join(chunks[mid:mid + 3]).rstrip(".") + "."
    # Keep only first two sentences for readability
    sents = re.split(r"(?<=[.!?])\s+", t)
    if len(sents) > 2:
        t = " ".join(sents[:2])
    return t


def placement_hook(planet: str, house: int, sign: str, dignity: str, rules: list[int]) -> str:
    role = PLANET_ROLE.get(planet, planet.lower())
    hp = house_plain(house)
    dig = dignity_plain(dignity)
    ruled = ""
    if rules:
        nums = " and ".join(_ord(r) for r in rules[:2])
        ruled = f" It also rules the {nums} house{'s' if len(rules[:2]) > 1 else ''}."
    return f"{planet} ({role}) is in your {hp}, in {sign} - {dig}.{ruled}"


def lord_hook(lord: str, lord_of: int, lord_in: int) -> str:
    topic = house_plain(lord_of)
    where = house_plain(lord_in)
    return f"As lord of {topic}, {lord} operates from the house of {where}."


def _collect_book_lines(members: list["Signal"], book: dict, direction: str) -> list[str]:
    from bhardwaj_semantic import STRONG, WEAK, _sentence_polarity

    lines: list[str] = []

    def rank(m: "Signal") -> int:
        if m.lord_of == 8 and m.lord_in == 6:
            return 5
        if m.planet == "Mars" and m.dignity in STRONG:
            return 4
        if m.dignity in STRONG:
            return 3
        if m.dignity in WEAK:
            return 0
        return 1

    dir_use = direction
    if any(m.planet == "Mars" and m.dignity in STRONG for m in members):
        dir_use = "positive"

    for m in sorted(members, key=rank, reverse=True):
        if m.planet and m.house:
            ln = lookup_planet_house(book, m.planet, m.house, m.dignity, dir_use)
            if ln and ln not in lines:
                if lines and direction == "positive" and _sentence_polarity(ln) == "caution":
                    continue
                lines.append(ln)
        elif m.lord_of and m.lord_in:
            ln = lookup_house_lord(book, m.lord_of, m.lord_in, direction)
            if ln and ln not in lines:
                if lines and direction == "positive" and _sentence_polarity(ln) == "caution":
                    continue
                lines.append(ln)
        if len(lines) >= 1 if direction == "caution" else 2:
            break
    return lines


def synthesize_domain_narrative(
    cl: "Cluster",
    members: list["Signal"],
    chart,
) -> str:
    """One readable paragraph per life domain."""
    domain = cl.domain
    lead = DOMAIN_LEAD.get(domain, "")
    takeaway = DOMAIN_TAKEAWAY.get(domain, "")

    hooks: list[str] = []
    if domain != "personality":
        for m in members[:4]:
            if m.planet and m.house:
                if domain == "finance" and m.planet == "Rahu" and any(
                    x.planet == "Mars" and x.dignity in {"moolatrikona", "exalted", "own_sign"} for x in members
                ):
                    continue
                info = chart.planets.get(m.planet, {})
                hooks.append(placement_hook(
                    m.planet, m.house, info.get("sign", ""), m.dignity or info.get("dignity", ""),
                    chart.rules.get(m.planet, []),
                ))
            elif m.lord_of and m.lord_in:
                hooks.append(lord_hook(chart.houses[m.lord_of]["lord"], m.lord_of, m.lord_in))
            elif m.source == "Lagna chapter":
                hooks.append(
                    f"You were born with {chart.lagna} rising, so {chart.houses[1]['lord']} "
                    f"colours your personality and first impression."
                )
            elif m.source == "Moon sign" and chart.moon_sign != chart.lagna:
                hooks.append(
                    f"Your Moon in {chart.moon_sign} adds an emotional layer - "
                    f"how you feel inside can be more {chart.moon_sign.lower()} than your outer {chart.lagna} mask."
                )

    seen_h: set[str] = set()
    hook_text = ""
    for h in hooks[:1 if domain in ("property", "travel", "children") else 2]:
        if h[:50] in seen_h:
            continue
        seen_h.add(h[:50])
        hook_text += (" " if hook_text else "") + h

    if domain == "personality":
        parts_pred = []
        if LAGNA_HUMAN.get(chart.lagna):
            parts_pred.append(LAGNA_HUMAN[chart.lagna])
        else:
            parts_pred.append(humanize_book_line(
                lookup_lagna_sign(chart.book, chart.lagna, "positive"), domain, "positive"
            ))
        if chart.moon_sign != chart.lagna:
            moon_txt = _moon_personality_phrase(chart.moon_sign)
            if moon_txt:
                parts_pred.append(f"Emotionally, your Moon in {chart.moon_sign}: {moon_txt}")
            elif LAGNA_HUMAN.get(chart.moon_sign):
                parts_pred.append(
                    f"Emotionally, your Moon in {chart.moon_sign} adds depth that differs from your rising sign."
                )
            else:
                ml = humanize_book_line(
                    lookup_lagna_sign(chart.book, chart.moon_sign, "positive"), domain, "positive"
                )
                if ml:
                    parts_pred.append(f"Emotionally, your Moon in {chart.moon_sign}: {ml}")
        pred = " ".join(parts_pred)
    else:
        book_lines = _collect_book_lines(members, chart.book, cl.direction)
        if not book_lines:
            raw = cl.affirmation.split(".", 1)
            if len(raw) > 1:
                book_lines = [raw[1].strip()]
        pred_parts = [humanize_book_line(ln, domain, cl.direction) for ln in book_lines[:2]]
        pred = _dedupe_words(" ".join(pred_parts))

    if domain == "marriage":
        lord_in = None
        for m in members:
            if m.lord_of == 7:
                lord_in = m.lord_in
                break
            if m.source == "Marriage lord" and m.house:
                lord_in = m.house
        if lord_in:
            hook_text = ""
            custom = MARRIAGE_LORD_PLAIN.get((7, lord_in))
            if custom:
                pred = custom
            else:
                lord_txt = lookup_house_lord(
                    chart.book, 7, lord_in,
                    "caution" if lord_in in (6, 8, 12) else "neutral",
                )
                if lord_txt:
                    book_pred = humanize_book_line(
                        lord_txt, "marriage", "caution" if lord_in in (6, 8, 12) else "neutral",
                    )
                    pred = (
                        f"Marriage is ruled by your 7th lord placed in the {house_plain(lord_in)}. "
                        f"Bhardwaj reads this as: {book_pred} "
                        f"Patience, clear communication, and matching remedies matter more than rushing the wedding date."
                    )

    if domain == "health":
        raja = next((m for m in members if m.lord_of == 8 and m.lord_in == 6), None)
        if raja:
            hook_text = lord_hook(chart.houses[8]["lord"], 8, 6)
            lord_txt = lookup_house_lord(chart.book, 8, 6, "positive")
            if lord_txt:
                core = humanize_book_line(lord_txt, "health", "positive")
                pred = (
                    f"Your 8th lord placed in the service-and-work house forms what Bhardwaj calls "
                    f"opposite Raja Yoga - turning obstacles into gain: {core}"
                )
            weak_jup = next(
                (m for m in members if m.planet == "Jupiter" and m.dignity == "debilitated"), None,
            )
            if weak_jup:
                pred += (
                    " Jupiter is debilitated in the change-house, so steady routine and calm habits "
                    "protect you more than fear."
                )
            takeaway = ""

    if pred and domain not in ("personality", "marriage") and not pred.lower().startswith(
        ("you", "your", "this", "bhardwaj", "partnership", "marriage", "gemini", "emotionally")
    ):
        pred = "In Bhardwaj's words: " + pred

    if cl.timing and domain in ("children", "current"):
        timing_note = f" This theme is active in your dasha window ({cl.timing})."
    else:
        timing_note = ""

    if cl.direction == "caution" and domain in ("health", "current", "marriage", "children"):
        balance = " This is not a curse - the chart asks for awareness, routine, and patience rather than fear."
    elif cl.direction == "positive":
        balance = " Taken together, the balance of this area is supportive when you stay sincere and steady."
    else:
        balance = ""

    parts = [lead, hook_text, pred, timing_note, balance, takeaway]
    text = " ".join(p.strip() for p in parts if p and p.strip())
    if domain == "finance":
        text = re.sub(r"obstructing children'?s? happiness,?\s*", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    text = _fix_fragmented_periods(text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\.\s+\.", ".", text)
    return text


def synthesize_period_narrative(chart, signals: list["Signal"]) -> str:
    """Hero / 'where you stand now' in counsellor voice."""
    md_sig = next((s for s in signals if s.source == "Vimshottari"), None)
    ad_sig = next((s for s in signals if s.source == "Antardasha"), None)
    if not md_sig:
        return "Your current dasha chapter is being mapped from the birth chart."

    md = md_sig.planet
    mh = md_sig.house
    md_line = lookup_planet_house(
        chart.book, md, mh, md_sig.dignity,
        "caution" if md_sig.dignity in {"debilitated", "enemy_sign"} else "neutral",
    )
    if md_sig.dignity in {"debilitated", "enemy_sign"}:
        md_human = (
            f"{md} is under strain in the {house_plain(mh)}, so Bhardwaj advises patience, "
            f"ethical effort, and remedial discipline rather than expecting easy luck."
        )
    else:
        md_human = humanize_book_line(md_line, "current", "neutral") if md_line else ""

    intro = (
        f"You are in {md} mahadasha - the major life period ruled by {PLANET_ROLE.get(md, md)}. "
        f"In your chart, {md} sits in the house of {house_plain(mh)}."
    )
    if ad_sig:
        ad = ad_sig.planet
        ah = ad_sig.house
        ad_line = lookup_planet_house(chart.book, ad, ah, ad_sig.dignity, "neutral")
        ad_human = humanize_book_line(ad_line, "current", "neutral") if ad_line else ""
        intro += (
            f" The active sub-period until {md_sig.timing or 'this phase ends'} is {ad} "
            f"(house of {house_plain(ah)})."
        )
        if ad_human:
            intro += f" Bhardwaj links this sub-period with: {ad_human}"
    if md_human:
        intro += f" The broader {md} chapter suggests: {md_human}"

    intro += (
        f" Practically: use this {md} period to work sincerely on {house_plain(mh)} themes"
    )
    if ad_sig:
        intro += f"; the {ad} sub-period spotlights {house_plain(ah)} - pace yourself and finish what is already in motion."
    else:
        intro += "."
    return _fix_fragmented_periods(_dedupe_words(intro))


def nakshatra_narrative(chart) -> str:
    import html as html_mod
    nk = chart.moon_nak or ""
    base = f"<p class='pred'>Your birth star (Moon nakshatra) is <strong>{html_mod.escape(nk)}</strong>.</p>"
    snippet = NAKSHATRA_SNIPPETS.get(nk, "")
    if not snippet:
        fx = chart.book.get("nakshatra_effects", {}).get(nk, "")
        if fx:
            snippet = humanize_book_line(pick_book_clause(fx, "", "positive"))
    if snippet:
        base += f"<p class='pred'>{html_mod.escape(snippet)}</p>"
    gand = chart.book.get("gandmool_nakshatras", [])
    if any(g.lower() in nk.lower() for g in gand):
        base += (
            "<p class='pred tag-warn-inline'>This is a Gandmool birth star - "
            "Bhardwaj recommends a simple peace ritual when the Moon returns to this star.</p>"
        )
    return base


def yoga_narrative(yogas: list[dict]) -> str:
    if not yogas:
        return "<p class='pred'>No major yoga was flagged in this quick scan.</p>"
    bits = []
    for y in yogas:
        name = y["name"]
        body = YOGA_HUMAN.get(name) or humanize_book_line(y.get("result", ""), "personality", "positive")
        bits.append(
            f"<div class='pred-card green'><div class='pred-body'>"
            f"<strong>{name}</strong> - {body}"
            f"</div></div>"
        )
    return "".join(bits)


def gochar_narrative(chart) -> str:
    try:
        import swisseph as swe
    except ImportError:
        return "<p class='pred'>Live transit notes need pyswisseph installed.</p>"

    SIGNS = [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    ]
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(__import__("datetime").date.today().year,
                    __import__("datetime").date.today().month,
                    __import__("datetime").date.today().day, 12.0)
    ref = chart.moon_sign
    ref_idx = SIGNS.index(ref)
    aus = chart.book.get("gochar_auspicious", {})
    inaus = chart.book.get("gochar_inauspicious", {})

    lines = [
        f"Bhardwaj reads today's transits from your Moon sign ({ref}), not from the rising sign alone.",
    ]
    good: list[str] = []
    watch: list[str] = []
    for name, pid in {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
        "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN,
    }.items():
        lon = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)[0][0]
        sign = SIGNS[int(lon // 30) % 12]
        pos = (SIGNS.index(sign) - ref_idx) % 12 + 1
        if pos in aus.get(name, []):
            good.append(f"{name} in {sign} (house {pos} from Moon) - helpful for you now.")
        elif pos in inaus.get(name, []):
            watch.append(f"{name} in {sign} (house {pos} from Moon) - go slow; avoid big gambles this week.")

    if good:
        lines.append("Supportive transits: " + " ".join(good[:3]))
    if watch:
        lines.append("Sensitive transits: " + " ".join(watch[:3]))
    if not good and not watch:
        lines.append("Most planets are in mixed zones - steady routine beats dramatic moves.")
    return f"<div class='callout'>{' '.join(lines)}</div>"


def remedy_narrative(chart) -> str:
    WEAK = {"debilitated", "enemy_sign"}
    cards = []
    REMEDY_PLAIN = {
        "Sun": "Sunday: offer water to the Sun, respect father figures, stay truthful at work.",
        "Moon": "Monday: calm the mind, serve mother or elder women, favour simple white foods.",
        "Mars": "Tuesday: channel anger into exercise; Hanuman prayer helps marriage heat.",
        "Mercury": "Wednesday: study, honest speech, green charity; emerald only if a gemologist agrees.",
        "Jupiter": "Thursday: teach or mentor someone, yellow charity, honour teachers and dharma.",
        "Venus": "Friday: harmony at home, white sweets charity, arts and music soothe the heart.",
        "Saturn": "Saturday: serve the poor or elderly, patience and routine; blue sapphire only if suitable.",
        "Rahu": "Avoid shortcuts and intoxicants; Durga or Chandi path steadies the mind.",
        "Ketu": "Meditation and Ganesha worship; reduce restlessness before big decisions.",
    }
    for pl, v in chart.planets.items():
        if v["dignity"] not in WEAK and v["house"] not in (6, 8, 12):
            continue
        hp = house_plain(v["house"])
        dig = dignity_plain(v["dignity"])
        cards.append(
            f"<div class='pred-card amber'><div class='pred-body'>"
            f"<strong>{pl}</strong> is {dig} in your {hp}. "
            f"{REMEDY_PLAIN.get(pl, 'Weekly planet-day discipline and charity help.')} "
            f"This is supportive care, not fear - Bhardwaj uses remedies to strengthen weak links."
            f"</div></div>"
        )
    if not cards:
        return (
            "<div class='pred-card neutral'><div class='pred-body'>"
            "No planet is critically weak in a dusthana house right now. "
            "Keep a simple weekly rhythm: charity on the day of the planet you feel closest to."
            "</div></div>"
        )
    return "".join(cards[:5])


AD_FOCUS: dict[str, tuple[str, str]] = {
    "Sun": ("authority, father figures, government work, and personal visibility", "career"),
    "Moon": ("home, mother, emotional tides, and public mood", "property"),
    "Mars": ("drive, property, competition, and bold decisions", "finance"),
    "Mercury": ("business, study, contracts, travel, and communication", "career"),
    "Jupiter": ("growth, teachers, faith, children, and long-range opportunity", "travel"),
    "Venus": ("love, marriage, comfort, arts, and social grace", "marriage"),
    "Saturn": ("discipline, delays, hard work, health routines, and karma", "health"),
    "Rahu": ("ambition, foreign links, networks, and unconventional paths", "finance"),
    "Ketu": ("closure, spirituality, research, and letting go of the past", "spiritual"),
}


def _fmt_ad_range(ad: dict) -> str:
    from datetime import datetime
    try:
        s = datetime.strptime(ad["start"][:10], "%Y-%m-%d").strftime("%b %Y")
        e = datetime.strptime(ad["end"][:10], "%Y-%m-%d").strftime("%b %Y")
        return f"{s} - {e}"
    except ValueError:
        return ad.get("start", "")[:7]


def year_ahead_narrative(chart, pc: dict) -> str:
    """Next antardashas inside current mahadasha - plain year-ahead timing."""
    vim = pc.get("vimshottari", {})
    md = vim.get("current_md", {}).get("md_lord", "")
    ads = vim.get("current_md_antardashas", [])
    if not ads or not md:
        return "<p class='pred'>Year-ahead timing needs a verified dasha table in the birth extract.</p>"

    relevant = [a for a in ads if a.get("status") in ("current", "future")][:6]
    if not relevant:
        relevant = ads[-3:]

    intro = (
        f"<p class='lead'>Your year ahead runs inside <strong>{md} mahadasha</strong>. "
        f"Bhardwaj reads each sub-period (antardasha) by where that planet sits in <em>your</em> chart.</p>"
    )
    cards = []
    for ad in relevant:
        lord = ad["ad_lord"]
        info = chart.planets.get(lord, {})
        hp = info.get("house", 0)
        dig = info.get("dignity", "")
        focus, _ = AD_FOCUS.get(lord, (f"{lord}-ruled life themes", "current"))
        ad_dir = "positive" if dig in {"exalted", "own_sign", "moolatrikona"} else "neutral"
        if lord in ("Rahu", "Ketu", "Saturn") and hp in (6, 8, 12):
            ad_dir = "neutral"
        book_raw = lookup_planet_house(chart.book, lord, hp, dig, ad_dir) if hp else ""
        book = humanize_book_line(book_raw, "current", ad_dir) if book_raw else ""
        if book and re.search(r"unfair means|grab the wealth|obstructing children", book, re.I):
            book = ""
        label = "Active now" if ad.get("status") == "current" else "Coming up"
        body = (
            f"<strong>{_fmt_ad_range(ad)}</strong> - {lord} sub-period ({label}). "
            f"Main focus: {focus}. "
        )
        if hp:
            body += f"In your chart {lord} sits in the {house_plain(hp)} ({dignity_plain(dig)}). "
        if book:
            body += f"Bhardwaj notes: {book}"
        tone = "green" if ad.get("status") == "current" else "neutral"
        cards.append(f"<div class='pred-card {tone}'><div class='pred-body'>{body}</div></div>")

    return intro + "".join(cards)
