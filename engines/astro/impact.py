"""Plain-language impact clauses — every astrological fact gets a consequence."""

from __future__ import annotations

from typing import Any, Optional

from report_language import client_prose


def _ord(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    return f"{n}" + ("th" if 10 <= n % 100 <= 20
                     else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


# What each dasha lord tends to do in real life (area-agnostic baseline).
DASHA_IMPACT = {
    "Sun": "visibility and authority move. Put your name on work that outlasts the quarter",
    "Moon": "home, mood and the people close to you take priority. Protect sleep and routine",
    "Mars": "friction and push. Finish what you started before escalating",
    "Mercury": "paperwork, communication and negotiation. Keep important agreements clear and put key decisions in writing",
    "Jupiter": "expansion, guidance and sponsorship. This is a period to use experienced support rather than relying on effort alone",
    "Venus": "relationships and comfort. Repair goodwill before pressing a request",
    "Saturn": "discipline, patience and completion. Finish the verifiable part carefully; half-done work is more likely to stall at review",
    "Rahu": "ambition and the unfamiliar. Verify what looks too convenient",
    "Ketu": "detachment. Step back for a fortnight; gripping harder rarely helps",
}

AREA_DASHA = {
    "career": "promotions and recognition come from disciplined delivery, not hype",
    "money": "income moves through networks and what you can prove on paper",
    "love": "partnership quality matters more than timing a grand gesture",
    "home": "property and family decisions need patience and clear paperwork",
    "children": "progeny and creative projects need steady effort, not force",
    "health": "energy and recovery respond to routine — rest is not optional",
    "learning": "study and luck open through teachers and consistent practice",
    "inner": "spiritual and inner life deepen when you withdraw from noise",
}

STAGE_AREA_DASHA: dict[str, dict[str, str]] = {
    "career": {
        "child": "achievement and responsibility show through school and activities",
        "teen": "study recognition and responsibility matter more than shortcuts",
        "young_adult": "early career visibility grows through skills and steady effort",
        "adult": "recognition and responsibility come from disciplined delivery, not hype",
        "mature_adult": "leadership and recognition come from disciplined delivery",
        "senior": "legacy and mentoring matter more than chasing new titles",
    },
    "money": {
        "child": "resource habits and family context shape how you think about money",
        "teen": "allowance, savings habits and family resources matter",
        "young_adult": "income and independence develop through practical decisions",
        "senior": "preservation and stability matter more than new risk",
    },
    "love": {
        "child": "friendships and family bonds need patience and clear communication",
        "teen": "friendships and close bonds need patience more than intensity",
        "young_adult": "relationship quality matters more than timing a grand gesture",
        "senior": "companionship and family bonds need steady care",
    },
    "children": {
        "child": "creative projects and activities need steady effort, not force",
        "teen": "personal projects and creativity need patience and consistency",
        "young_adult": "future family context develops gradually, not all at once",
        "senior": "family continuity and patience matter more than forcing pace",
    },
}


def area_dasha_clause(area: str, band: str = "adult") -> str:
    """Stage-aware area clause for chapter/dasha copy."""
    by_area = STAGE_AREA_DASHA.get(area) or {}
    return by_area.get(band) or AREA_DASHA.get(area, "")

DIGNITY_IMPACT = {
    "exalted": "this placement over-delivers when you act with confidence",
    "moolatrikona": "this placement is at full strength — use it directly",
    "own_sign": "this placement is reliable — steady effort converts",
    "friendly_sign": "this placement supports you with consistent effort",
    "neutral_sign": "this placement is workable — neither a free pass nor a block",
    "enemy_sign": "this placement tests you — expect extra effort for the same result",
    "debilitated": "this placement starts slow — prove competence before expecting reward",
}

VARGA_IMPACT = {
    "strong": "the specialised chart for this area is well-built — promises here can deliver",
    "mixed": "the specialised chart is workable — timing and effort matter",
    "weak": "the specialised chart is under strain — go steady and use remedies",
}


def dasha_impact(lord: str, *, area: str = "", end_pretty: str = "",
                 houses_owned: Optional[list] = None,
                 age_band: str = "adult") -> str:
    """Lord + optional end date → one sentence with real-life meaning."""
    lord = (lord or "").strip()
    if not lord:
        return ""
    base = DASHA_IMPACT.get(lord, "emphasis shifts in this part of life")
    area_bit = area_dasha_clause(area, age_band) if area else ""
    parts = [base]
    if area_bit:
        parts.append(area_bit)
    text = ". ".join(p.rstrip(".") for p in parts if p)
    # Prefer full month names when the caller passed a short date token.
    end_txt = (end_pretty or "").strip()
    month_map = {
        "Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April",
        "May": "May", "Jun": "June", "Jul": "July", "Aug": "August",
        "Sep": "September", "Oct": "October", "Nov": "November", "Dec": "December",
    }
    for short, long in month_map.items():
        if end_txt.startswith(short + " "):
            end_txt = long + end_txt[len(short):]
            break
    if end_txt:
        return client_prose(f"{lord} runs until {end_txt}: {text}.")
    return client_prose(f"{lord} period: {text}.")


# Short week-to-week feel — different framing from DASHA_IMPACT parentheticals.
DASHA_WEEKLY: dict[str, str] = {
    "Sun": "a push to be seen and take clearer ownership",
    "Moon": "mood, home needs and the people closest to you asking more attention",
    "Mars": "sharper friction and a need to finish before escalating",
    "Mercury": "more paperwork, messages and negotiation detail",
    "Jupiter": "openings through guidance, teaching or sponsorship",
    "Venus": "relationship repair and comfort mattering before hard requests",
    "Saturn": "slower progress, greater responsibility and a stronger need to finish what you start",
    "Rahu": "ambition toward unfamiliar options that still need checking",
    "Ketu": "a pull to step back rather than grip harder",
}


def period_impact(md_lord: str, ad_lord: str, *, end_pretty: str = "",
                   area: str = "", age_band: str = "adult") -> str:
    """Mahadasha–antardasha chapter line with impact.

    When MD and AD are the same planet, avoid repeating the identical parenthetical.
    """
    if md_lord and ad_lord:
        if md_lord == ad_lord:
            theme = DASHA_IMPACT.get(md_lord, "background theme")
            weekly = DASHA_WEEKLY.get(ad_lord, "the tone of ordinary weeks")
            core = (f"{md_lord} sets the broader tone: {theme}. "
                    f"You may feel this as {weekly}")
        else:
            md_feel = DASHA_IMPACT.get(md_lord, "background theme")
            weekly = DASHA_WEEKLY.get(ad_lord) or DASHA_IMPACT.get(
                ad_lord, "week-to-week feel")
            core = (f"{md_lord} sets the broader tone: {md_feel}. "
                    f"{ad_lord} is what you feel week to week — {weekly}")
    elif md_lord:
        core = dasha_impact(md_lord, area=area, age_band=age_band).rstrip(".")
    else:
        return ""
    if end_pretty:
        return client_prose(f"{core}. Through {end_pretty}.")
    return client_prose(f"{core}.")


def placement_impact(planet: str, house: Any, dignity: str = "",
                     *, area: str = "") -> str:
    """Planet in house with dignity → consequence."""
    planet = (planet or "").strip()
    if not planet:
        return ""
    dig = (dignity or "neutral_sign").lower().replace(" ", "_")
    dig_line = DIGNITY_IMPACT.get(dig, DIGNITY_IMPACT["neutral_sign"])
    try:
        h = int(house)
        house_phrase = f"the {_ord(h)} house"
    except (TypeError, ValueError):
        house_phrase = "this house"
    return client_prose(f"{planet} in {house_phrase}: {dig_line}.")


def varga_impact(code: str, strength: str, *, area_name: str = "") -> str:
    """Divisional chart strength → plain consequence."""
    s = (strength or "mixed").lower()
    line = VARGA_IMPACT.get(s, VARGA_IMPACT["mixed"])
    label = area_name or code or "this area"
    return client_prose(f"The {code} chart for {label} is {s}. {line}.")


def window_impact(rating: str, *, period: str = "", reason: str = "") -> str:
    """Dasha window rating → actionable line."""
    word = {
        "fav": "a good window to push this area",
        "mix": "workable with patience. Mixed signals",
        "chal": "demanding. Avoid big bets here",
    }.get((rating or "mix").lower(), "mixed signals")
    out = word
    if period:
        out = f"{period}: {word}"
    if reason:
        out += f" ({reason[:90]})"
    return client_prose(out)
