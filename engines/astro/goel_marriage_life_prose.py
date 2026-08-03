#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plain-English marriage-life paragraphs from Goel marriage_life analysis."""
from __future__ import annotations

from typing import Any

from goel_marriage_timing import timing_client_paragraph


def spouse_paragraph(ml: dict, analysis: dict) -> str:
    lord7_sign = ml.get("lord7_sign", "Libra")
    lord7 = ml.get("lord7", "Venus")
    enriched = analysis.get("d9_enriched", {})
    l7 = enriched.get(lord7, {})
    dk = analysis.get("darakaraka", "")
    dk_e = enriched.get(dk, {}) if dk else {}
    moon = enriched.get("Moon", {})

    tone = {
        "Libra": "graceful, diplomatic, and focused on fairness",
        "Aries": "direct, bold, and independent",
        "Pisces": "soft, romantic, and spiritually gentle",
        "Scorpio": "intense, loyal, and private",
    }.get(lord7_sign, "distinctive in character")

    parts = [f"Your spouse is {tone} (navamsha seventh in {lord7_sign})."]

    if l7.get("d9_house") == 12 and l7.get("d9_dignity") == "exalted":
        parts.append(
            f"{lord7} rules marriage from the twelfth in exalted Pisces - "
            "a romantic partner who cherishes privacy, intimacy, and quiet devotion rather than public display."
        )
    elif l7.get("d9_house"):
        parts.append(
            f"Marriage is guided by {lord7} from the {l7['d9_house']}th house - "
            "the union shapes how you experience home, travel, or career together."
        )

    if dk == "Mars" and dk_e:
        parts.append(
            "Mars is the spouse significator in Aries on the navamsha ascendant - "
            "the partner is energetic, self-starter, courageous, and may work in technical, military, or athletic fields."
        )
    elif dk == "Venus" and dk_e:
        parts.append(
            "Venus as spouse significator - an attractive, artistic, harmony-loving partner."
        )
    elif dk == "Jupiter" and dk_e:
        parts.append(
            "Jupiter as spouse significator - a wise, generous, principled partner."
        )
    elif dk == "Saturn" and dk_e:
        parts.append(
            "Saturn as spouse significator - a mature, disciplined partner, sometimes older or sober in temperament."
        )

    if moon.get("d9_sign") == "Aries":
        parts.append("Moon in Aries navamsha adds fair to reddish complexion and spontaneous emotional warmth.")
    elif moon.get("d9_sign"):
        parts.append(f"Moon in {moon['d9_sign']} navamsha colours emotional style and complexion tone.")

    return " ".join(parts)


def happiness_paragraph(ml: dict) -> str:
    score = ml.get("happiness_score", 0)
    if score >= 75:
        return (
            "You will draw real happiness from marriage. The navamsha fourth house is free of affliction, "
            "and Venus is powerfully placed - comfort at home, affection, and contentment grow after the wedding "
            "rather than fading."
        )
    if score >= 50:
        return (
            "Marriage brings solid happiness when both partners invest in home peace. "
            "The navamsha map supports contentment, though busy periods may need deliberate quality time."
        )
    return (
        "Happiness in marriage comes with effort. Navamsha fourth-house strain means domestic peace must be "
        "guarded with patience, rituals, and honest repair after arguments."
    )


def affair_paragraph(ml: dict) -> str:
    risk = ml.get("affair_risk", 0)
    if risk >= 55:
        return (
            "Side attractions or secret emotional bonds are a real theme. "
            "The navamsha pattern shows strong desire with an unhappy or restless home layer. "
            "Clear boundaries and transparency protect the main relationship."
        )
    if risk >= 35:
        return (
            "Flirtation or brief distractions may appear in certain dasha years, "
            "but the chart does not push a permanent parallel life. "
            "Stay honest early before small attractions become habits."
        )
    return (
        "Affairs are not a dominant theme. The seventh house is clean and its lord is strong - "
        "loyalty and depth in the primary bond outweigh wandering. Romance stays inside the marriage."
    )


def divorce_paragraph(ml: dict) -> str:
    risk = ml.get("divorce_risk", 0)
    if risk >= 55:
        return (
            "Separation or divorce is a serious risk in this map. "
            "The navamsha seventh lord or fourth house cannot sustain stress without damage - "
            "couple counselling, shared finances discipline, and Jupiter/Venus remedies matter before crisis peaks."
        )
    if risk >= 35:
        return (
            "The marriage can hit separation scares in harsh dasha years, especially when Saturn or Rahu activate the seventh. "
            "The bond is repairable if both choose dialogue over exit; the chart does not mandate permanent break."
        )
    return (
        "Divorce is not the default outcome. The marriage manager is strong and benefic balance on the seventh axis "
        "holds the union together. Rough patches call for patience and talk, not walking away."
    )


def marriage_age_paragraph(timing: dict) -> str:
    return timing_client_paragraph(timing)


def love_marriage_paragraph(ml: dict) -> str:
    if ml.get("love_marriage"):
        return (
            "Love marriage or self-chosen partner is strongly indicated. "
            "The fifth and seventh houses link in navamsha - romance precedes or wraps the formal union rather than a purely arranged match."
        )
    return (
        "Arranged or family-introduced marriage fits as well as love match. "
        "The chart does not force elopement; partnership can arrive through conventional introductions when dasha runs."
    )


def foreign_spouse_paragraph(ml: dict, analysis: dict) -> str:
    if not ml.get("foreign_spouse"):
        return (
            "Spouse is likely from your own region or social circle. "
            "No strong foreign or cross-cultural signature dominates the navamsha marriage map."
        )
    parts = ["Partner may come from another city, country, or a clearly different background."]
    if analysis.get("d9_enriched", {}).get("Venus", {}).get("d9_house") == 12:
        parts.append("Venus in the twelfth often brings a private courtship or a spouse met away from home.")
    if analysis.get("d9_houses", {}).get(9):
        parts.append("Ninth-house Rahu adds travel, foreign study, or online distance before marriage.")
    return " ".join(parts)


def spouse_age_gap_paragraph(ml: dict) -> str:
    if ml.get("spouse_age_gap"):
        return (
            "Spouse may be noticeably older or more mature than you, or the age gap becomes a talking point in the family. "
            "Saturn touching the romance or marriage zone in navamsha often gives this pattern; respect and patience bridge the gap."
        )
    return (
        "No strong age-gap signature - spouse is likely close to your own age band or the difference is minor."
    )


def multiple_marriage_paragraph(ml: dict) -> str:
    if ml.get("multiple_marriage"):
        return (
            "More than one serious marriage or long live-in bond is possible across life. "
            "Navamsha shows mixed lagna/upachaya patterns; values and Jupiter discipline decide whether this stays one union."
        )
    return (
        "One primary marriage is the main story. "
        "The navamsha map does not push repeated weddings unless you choose to leave the first bond yourself."
    )


def denial_paragraph(ml: dict) -> str:
    if ml.get("marriage_denial"):
        return (
            "Marriage denial or long postponement is flagged. "
            "Three afflictions on the seventh axis with no benefic relief - remedies for Venus/Jupiter and the seventh lord, plus dasha patience, are important."
        )
    return ""


def mangal_paragraph(ml: dict) -> str:
    if not ml.get("mangal_dosha"):
        return ""
    return (
        "Mars touches the marriage axis - temper, hurry, or friction in matching can show as mangal-style heat. "
        "Partner with similar Mars tolerance, or classical mangal remedies, smooth the path."
    )


def marriage_life_client_cards(analysis: dict[str, Any]) -> list[dict]:
    ml = analysis.get("marriage_life")
    if not ml:
        return []

    timing = analysis.get("marriage_timing_detail", {})
    cards: list[dict] = []

    if timing.get("windows") or timing.get("age_label"):
        cards.append({
            "title": "Marriage age & timing",
            "text": marriage_age_paragraph(timing),
            "tone": "green",
            "theme_id": "marriage_age",
        })

    cards.extend([
        {
            "title": "Your spouse",
            "text": spouse_paragraph(ml, analysis),
            "tone": "green",
            "theme_id": "spouse_personality",
        },
        {
            "title": "Happiness from marriage",
            "text": happiness_paragraph(ml),
            "tone": "green" if ml.get("happiness_score", 0) >= 50 else "amber",
            "theme_id": "marital_happiness",
        },
        {
            "title": "Love or arranged marriage",
            "text": love_marriage_paragraph(ml),
            "tone": "green",
            "theme_id": "love_marriage",
        },
        {
            "title": "Partner background",
            "text": foreign_spouse_paragraph(ml, analysis),
            "tone": "green" if not ml.get("foreign_spouse") else "neutral",
            "theme_id": "foreign_spouse",
        },
        {
            "title": "Spouse age gap",
            "text": spouse_age_gap_paragraph(ml),
            "tone": "neutral",
            "theme_id": "spouse_age_gap",
        },
        {
            "title": "Affairs",
            "text": affair_paragraph(ml),
            "tone": "amber" if ml.get("affair_risk", 0) >= 35 else "green",
            "theme_id": "affair",
        },
        {
            "title": "Divorce / separation",
            "text": divorce_paragraph(ml),
            "tone": "amber" if ml.get("divorce_risk", 0) >= 35 else "green",
            "theme_id": "divorce",
        },
        {
            "title": "Second marriage",
            "text": multiple_marriage_paragraph(ml),
            "tone": "amber" if ml.get("multiple_marriage") else "green",
            "theme_id": "multiple_marriage",
        },
    ])

    deny = denial_paragraph(ml)
    if deny:
        cards.append({"title": "Marriage denial", "text": deny, "tone": "amber", "theme_id": "denial"})

    mangal = mangal_paragraph(ml)
    if mangal:
        cards.append({"title": "Mars & marriage", "text": mangal, "tone": "amber", "theme_id": "mangal"})

    return cards
