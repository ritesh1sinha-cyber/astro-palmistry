"""Plain-language impact clauses — every astrological fact gets a consequence."""

from __future__ import annotations

from typing import Any, Optional

from report_language import client_prose

# What each dasha lord tends to do in real life (area-agnostic baseline).
DASHA_IMPACT = {
    "Sun": "visibility and authority move — put your name on work that outlasts the quarter",
    "Moon": "home, mood and the people close to you take priority — protect sleep and routine",
    "Mars": "friction and push — finish what you started before escalating",
    "Mercury": "paperwork, talks and negotiation — put agreements in writing",
    "Jupiter": "expansion and sponsorship — ask someone senior to speak for you",
    "Venus": "relationships and comfort — repair goodwill before pressing a request",
    "Saturn": "delay and discipline — finish the verifiable part; half-done work stalls at review",
    "Rahu": "ambition and the unfamiliar — verify what looks too convenient",
    "Ketu": "detachment — step back for a fortnight; gripping harder rarely helps",
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
                 houses_owned: Optional[list] = None) -> str:
    """Lord + optional end date → one sentence with real-life meaning."""
    lord = (lord or "").strip()
    if not lord:
        return ""
    base = DASHA_IMPACT.get(lord, "emphasis shifts in this part of life")
    area_bit = AREA_DASHA.get(area, "")
    parts = [base]
    if area_bit:
        parts.append(area_bit)
    text = "; ".join(parts)
    if end_pretty:
        return client_prose(f"{lord} runs until {end_pretty}: {text}.")
    return client_prose(f"{lord} period: {text}.")


def period_impact(md_lord: str, ad_lord: str, *, end_pretty: str = "",
                   area: str = "") -> str:
    """Mahadasha–antardasha chapter line with impact."""
    if md_lord and ad_lord:
        md_feel = DASHA_IMPACT.get(md_lord, "background theme")
        ad_feel = DASHA_IMPACT.get(ad_lord, "week-to-week feel")
        core = (f"{md_lord} sets the background ({md_feel}); "
                f"{ad_lord} is what you feel week to week ({ad_feel})")
    elif md_lord:
        core = dasha_impact(md_lord, area=area).rstrip(".")
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
        house_phrase = f"the {h}th house"
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
