#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chandra_naadi_analysis.py — Chandra Naadi Astrology Analysis Engine

Implements the complete diagnostic and predictive rule set for Vedic Moon Naadi transit methodology.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import swisseph as swe

from astro_precompute import (
    DIGNITY_TABLE,
    ENEMIES,
    FRIENDS,
    SIGN_LORDS,
    SIGNS,
    VIMSH_LORDS,
    VIMSH_YEARS,
    get_dignity,
    get_functional_status,
    house_from_lagna,
    house_sign,
    sign_index,
)
from chandra_naadi_book_data import (
    BHAVA_QUERY_MAP,
    CHILDBIRTH_RULES,
    CONJUNCTION_RULES,
    DEATH_RULES,
    DEBT_MATRIX,
    MAANDI_WEEKDAY_CONSTANTS,
    MARRIAGE_SCENARIOS,
    MARS_TRANSIT_BHAVA,
    PLANET_DISEASE_MAP,
    RASHI_KARAKATHWAS,
    REMEDIES,
    SPECIAL_RULES,
    TRANSIT_SATURN_EFFECTS,
    YOGA_DEFINITIONS,
)

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
PLANETS_7 = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

SWE_PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
    "Rahu": swe.MEAN_NODE,
}

SPECIAL_ASPECTS = {
    "Mars": [3, 6, 7],      # 4th, 7th, 8th houses
    "Jupiter": [4, 6, 8],   # 5th, 7th, 9th houses
    "Saturn": [2, 6, 9],    # 3rd, 7th, 10th houses
}

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Rich, comprehensive classical aspect predictions from Chandra Naadi (Ch. 5 & 17)
ASPECT_RULES = {
    ("Sun", "Moon"): "Promotes harmony between paternal and maternal traditions; native undertakes frequent travels for administrative or public works, possessing intuitive leadership.",
    ("Sun", "Mars"): "Dynamic boldness and authoritative executive command, but creates sudden temperamental surges, accidental injuries, or friction with superiors.",
    ("Sun", "Mercury"): "Sharp commercial intellect, mathematical acumen, high capability in official correspondence, accounting, and public administration.",
    ("Sun", "Jupiter"): "Royal dignity, high administrative honors, noble character, deep social respect, and strong leadership in public or religious institutions.",
    ("Sun", "Venus"): "Father attains wealth and luxurious standing; native gains royal/governmental favor, artistic appreciation, and radiant personality.",
    ("Sun", "Saturn"): "Karmic friction with authority figures or paternal figures; delayed recognition in early career, requiring steadfast discipline and perseverance.",
    ("Sun", "Rahu"): "Father endured intense life struggles; native experiences sudden career shifts, eye sensitivity, and an intense drive for public validation.",
    ("Sun", "Ketu"): "Paternal spiritual heritage; native possesses deep philosophical detachment, keen intuition, and may face official/tax documentation disputes.",

    ("Moon", "Sun"): "Paternal support, emotional nobility, desire for social recognition, and strong executive decision-making under pressure.",
    ("Moon", "Mars"): "Athletic vitality, sharp courageous temperament, voracious appetite, connection to maternal property, and potential disputes over real estate.",
    ("Moon", "Mercury"): "Vivid imagination, poetic/expressive intellect, diplomatic counseling skills, psychological acumen, and quick commercial strategy.",
    ("Moon", "Jupiter"): "Gaja Kesari Radiance: Bestows broad societal respect, high moral stature, lasting legacy, prosperity for children, and generous hospitality.",
    ("Moon", "Venus"): "Refined elegance, artistic and musical tastes, charming social presence, fondness for perfumes/luxuries, and pleasant domestic atmosphere.",
    ("Moon", "Saturn"): "Punarpoo Ray: Serious, introspective temperament with initial obstacles turning into grand success after persistent effort; watch against overthinking.",
    ("Moon", "Rahu"): "Hyper-intuitive imagination, creative talent in media/visuals, vivid dreams, but prone to anxiety, allergies, or digestive sensitivities.",
    ("Moon", "Ketu"): "Spiritual introspection, dispassion toward material ostentation, occult sensitivity, detachment from domestic entanglements.",

    ("Mars", "Sun"): "High physical courage, authoritative demeanor, leadership in engineering/military/governance, with a tendency toward fiery impatience.",
    ("Mars", "Moon"): "Intense emotional energy, drive in landed property/agriculture, bold decision-making, and dynamic protective instincts for family.",
    ("Mars", "Mercury"): "Rapid analytical reflexes, sharp engineering and computational skills, piercing speech, but prone to academic shifts or debate disputes.",
    ("Mars", "Jupiter"): "Courageous commander, protector of family and righteousness, dynamic executive power, high generosity, and temple administration interests.",
    ("Mars", "Venus"): "Passionate artistic and mechanical drive, acquisition of premium real estate/vehicles, multi-trade commercial success, and charismatic persona.",
    ("Mars", "Saturn"): "Mandaara / Thaara Ray: Remarkable endurance in heavy mechanical/technical work; requires patience in marriage and caution against bone/limb injuries.",
    ("Mars", "Rahu"): "Fearless technical drive, machinery/electrical expertise, intense ambition, but demands caution against hasty driving and machinery accidents.",
    ("Mars", "Ketu"): "Surgical and precision technical skill, tailoring/wiring mastery, disputes over mortgaged assets; worship of Lord Kalabhairava recommended.",

    ("Mercury", "Sun"): "High formal education, administrative competence, analytical intelligence, and respected communication skills in commerce or law.",
    ("Mercury", "Moon"): "Deep psychological insight, creative storytelling, counseling ability, quick commercial adaptability, and restless mental energy.",
    ("Mercury", "Mars"): "Sharp critical acumen, computational mastery, technical drafting, but prone to blunt speech and contractual disputes.",
    ("Mercury", "Jupiter"): "Scholarly distinction, authorship, dignified advisory, financial consulting, academic leadership, and high societal credibility.",
    ("Mercury", "Venus"): "Madhana Gopala Ray: Exceptional aesthetic elegance, mastery of music, arts, and persuasive literature; charming and polite orator.",
    ("Mercury", "Saturn"): "Legal, auditing, and land-document scrutiny; meticulous accounting skills; delayed formal recognition compensated by practical expertise.",
    ("Mercury", "Rahu"): "Intuitive oratory, excellence in IT, telecommunications, and digital media; watch against skin allergies and contract fraud.",
    ("Mercury", "Ketu"): "Unconventional intellectual mastery, legal/arbitration acumen, break in conventional studies followed by specialized wisdom.",

    ("Jupiter", "Sun"): "Bestows governmental honors, paternal prosperity, high ethical leadership, administrative dignity, and patronage from elders.",
    ("Jupiter", "Moon"): "Gaja Kesari Influence: Elevates emotional composure, societal goodwill, financial stability for progeny, and auspicious domestic events.",
    ("Jupiter", "Mars"): "Magnanimous courage, authoritative judicial or executive capability, righteous leadership, and success in high-level management.",
    ("Jupiter", "Mercury"): "Authoritative advisor, academician, publisher, commercial guide, trusted financial mediator, and respected counselor.",
    ("Jupiter", "Venus"): "Abundant prosperity, ethical and luxurious lifestyle, mutual marital harmony, refined cultural patronage, and high social standing.",
    ("Jupiter", "Saturn"): "Dutiful, serene, and deeply philosophical; acts as the pillars and breadwinners of the family; steady wealth accumulation.",
    ("Jupiter", "Rahu"): "Guru Chandal Influence: Unconventional philosophical outlook, challenges orthodox dogmas, achieves dramatic non-traditional success.",
    ("Jupiter", "Ketu"): "Ascetic wisdom, profound spiritual detachment, mastery of sacred philosophy, philanthropic nature, and pilgrimage pursuits.",

    ("Venus", "Sun"): "Refined aristocratic tastes, governmental and royal connections, attractive physical radiance, and prosperity through fine arts/luxury.",
    ("Venus", "Moon"): "Harmonious social demeanor, romantic charm, appreciation of fine cuisine and music, and prosperous domestic comforts.",
    ("Venus", "Mars"): "Dynamic passion, artistic entrepreneurship, prosperity in luxury merchandise, real estate, and vibrant partnership ventures.",
    ("Venus", "Mercury"): "Madhana Gopala Ray: Aesthetic eloquence, mastery of literature and arts, diplomatic charm, and lucrative commercial alliances.",
    ("Venus", "Jupiter"): "Supreme auspiciousness, marital bliss, luxurious vehicles and assets, high cultural honors, and deep spiritual grace.",
    ("Venus", "Saturn"): "Substantial financial accumulation through banking, real estate, luxury trade, or long-standing corporate partnerships.",
    ("Venus", "Rahu"): "High charisma, media/cinema magnetism, sudden financial windfalls, attraction to unconventional luxury or relationships.",
    ("Venus", "Ketu"): "Spiritual grace, dispassion toward material vanity, marital life guided by spiritual values, electronic/aesthetic skills.",

    ("Saturn", "Sun"): "Demands rigorous self-discipline; tests relationship with seniors and father, culminating in hard-earned permanent authority.",
    ("Saturn", "Moon"): "Punarpoo Ray: Deep emotional resilience forged through obstacles; methodical work ethic, turning initial struggles into solid success.",
    ("Saturn", "Mars"): "Mandaara Ray: Relentless mechanical stamina, physical endurance, revolutionary work ethic; demands marital patience.",
    ("Saturn", "Mercury"): "Meticulous auditing, accounting, legal documentation, land survey, and analytical precision with delayed but solid gains.",
    ("Saturn", "Jupiter"): "Reverent spiritual nature, patient builder of institutions, unwavering duty toward dependents, and enduring legacy.",
    ("Saturn", "Venus"): "Steady accumulation of wealth, financial stability, loyal partnerships, and prosperity stabilizing after initial career delays.",
    ("Saturn", "Rahu"): "Transformative career struggles leading to extraordinary mastery, mass influence, and technological/industrial breakthroughs.",
    ("Saturn", "Ketu"): "Deep spiritual dispassion, mastery in technical/crafts/judicial fields; success achieved through complete detachment from greed.",

    ("Rahu", "Sun"): "Intense ambition for public visibility, father endured hardships, sudden career reversals transformed into major breakthroughs.",
    ("Rahu", "Moon"): "Hyper-creative imagination, artistic visual talent, psychological intuition, with periodic mental restlessness.",
    ("Rahu", "Mars"): "Fierce competitive boldness, mastery over machinery and cutting-edge technology, requiring caution against rash impulses.",
    ("Rahu", "Mercury"): "Brilliant strategic thinking, success in digital media and IT, innovative communication, and rapid commercial expansion.",
    ("Rahu", "Jupiter"): "Guru Chandal Dynamic: Radical expansion of boundaries, unconventional success in foreign or mass institutions.",
    ("Rahu", "Venus"): "Glamour, media magnetism, sudden financial windfalls, and prosperity in visual arts, design, or luxury markets.",
    ("Rahu", "Saturn"): "Mass leadership potential, unconventional career rise, endurance through formidable life crises to achieve power.",
    ("Rahu", "Ketu"): "Karmic Axis Alignment: Operates as the dual polarity of cosmic evolution — balances present material drives with past spiritual roots.",

    ("Ketu", "Sun"): "Paternal spiritual inclination, administrative detachment, keen intuitive discernment, and mastery of traditional mantras.",
    ("Ketu", "Moon"): "Occult and meditative depth, detachment from emotional drama, maternal spiritual roots, and psychological insight.",
    ("Ketu", "Mars"): "Surgical precision, martial detachment, expertise in electrics, law, or indigenous healing; worship of Kalabhairava advised.",
    ("Ketu", "Mercury"): "Analytical auditing precision, break in standard education followed by specialized mastery in law, code, or mathematics.",
    ("Ketu", "Jupiter"): "Aandi / Ascetic Ray: Profound spiritual detachment, saintly disposition in daily life, and dedication to spiritual knowledge.",
    ("Ketu", "Venus"): "Detachment from superficial luxury, deep spiritual devotion (Lord Ganesha / Hanuman), and refined classical aesthetic sense.",
    ("Ketu", "Saturn"): "Karmic detachment at workplace, success in law, medicine, auditing, and temple services; freedom from greed brings peace.",
    ("Ketu", "Rahu"): "Karmic Axis Alignment: Bridges past-life karmic resolution (Ketu) with present-life evolutionary expansion (Rahu).",
}

PLANET_ACTIVATION_THEMES = {
    "Sun": "Career authority, administrative/governmental interactions, father's status, public reputation, and leadership responsibilities.",
    "Moon": "Emotional peace, mother's health, residential transitions, travel, public popularity, and financial liquidity.",
    "Mars": "Landed assets, property transactions, siblings, technical projects, physical courage, and executive decisions.",
    "Mercury": "Commercial agreements, intellectual learning, writing, trade negotiations, accounting, and business partnerships.",
    "Jupiter": "Spiritual merit, financial advisory, progeny welfare, noble recognition, and higher philosophical learning.",
    "Venus": "Marital harmony, luxury vehicles, fine arts, relationship commitments, and liquid asset accumulation.",
    "Saturn": "Professional duties, structural organizational work, managing long-term responsibilities, and labor/staff leadership.",
    "Rahu": "Unconventional career expansion, technology/digital ventures, foreign associations, and material cravings.",
    "Ketu": "Spiritual detachment, legal/arbitration settlement, resolving ancestral commitments, and occult intuition.",
}


@dataclass
class ChandraNaadiReading:
    rule_id: str
    category: str
    title: str
    condition_met: bool
    condition_desc: str
    prediction: str
    severity: str  # "info" | "positive" | "caution" | "warning" | "critical"
    planets_involved: list[str]
    houses_involved: list[int]
    chapter_ref: str
    modifiers: list[str] = field(default_factory=list)
    remedies: list[str] = field(default_factory=list)


def compute_maandi(sun_degree_abs: float, weekday: str, is_daytime: bool) -> float:
    """Computes Maandi longitude using GK formula."""
    time_of_day = "day" if is_daytime else "night"
    constant = MAANDI_WEEKDAY_CONSTANTS.get(weekday, {}).get(time_of_day, 0)
    return (sun_degree_abs + constant) % 360


def get_transit_positions(dt: datetime) -> dict:
    """Compute all planet sidereal positions at datetime dt using swisseph."""
    try:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        hour_decimal = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        jd = swe.julday(dt.year, dt.month, dt.day, hour_decimal)
        res = {}
        for p_name, p_id in SWE_PLANETS.items():
            pos, ret = swe.calc_ut(jd, p_id, swe.FLG_SIDEREAL)
            lon = pos[0]
            sign_idx = int(lon // 30) % 12
            degree = lon % 30
            sign = SIGNS[sign_idx]
            res[p_name] = {"sign": sign, "degree": degree, "abs_degree": lon}

            if p_name == "Rahu":
                k_lon = (lon + 180) % 360
                k_sign_idx = int(k_lon // 30) % 12
                k_sign = SIGNS[k_sign_idx]
                res["Ketu"] = {"sign": k_sign, "degree": k_lon % 30, "abs_degree": k_lon}
        return res
    except Exception:
        return {}


def planet_aspects_sign(planet: str, planet_sign: str, target_sign: str) -> bool:
    """Check if planet in planet_sign aspects target_sign using Parashari drishti."""
    if not planet_sign or not target_sign or planet_sign not in SIGNS or target_sign not in SIGNS:
        return False
    offsets = SPECIAL_ASPECTS.get(planet, [6])
    p_idx = sign_index(planet_sign)
    t_idx = sign_index(target_sign)
    for off in offsets:
        if (p_idx + off) % 12 == t_idx:
            return True
    return False


def natal_planets_in_sign(pc: dict, sign: str) -> list[str]:
    """Return list of natal planet names in the given sign."""
    return [p for p, d in pc.get("planets", {}).items() if d.get("sign") == sign]


def is_strong(planet: str, sign: str) -> bool:
    """True if dignity is exalted, own_sign, moolatrikona, or friendly_sign."""
    dig = get_dignity(planet, sign)
    return dig in ["exalted", "own_sign", "moolatrikona", "friendly_sign", "great_friend_sign"]


def is_weak(planet: str, sign: str) -> bool:
    """True if dignity is debilitated or enemy_sign."""
    dig = get_dignity(planet, sign)
    return dig in ["debilitated", "enemy_sign", "great_enemy_sign"]


def detect_parivarthana(pc: dict) -> list[dict]:
    """Detect mutual exchange of house lords."""
    res = []
    lagna = pc.get("meta", {}).get("lagna_sign")
    if not lagna:
        return res
    lords_houses = {}
    for h in range(1, 13):
        h_sign = house_sign(h, lagna)
        lord = SIGN_LORDS[h_sign]
        lords_houses[h] = lord

    for h1 in range(1, 13):
        for h2 in range(h1 + 1, 13):
            l1 = lords_houses[h1]
            l2 = lords_houses[h2]
            p1_sign = pc.get("planets", {}).get(l1, {}).get("sign")
            p2_sign = pc.get("planets", {}).get(l2, {}).get("sign")
            h1_sign = house_sign(h1, lagna)
            h2_sign = house_sign(h2, lagna)
            if p1_sign == h2_sign and p2_sign == h1_sign and l1 != l2:
                res.append({"house_a": h1, "house_b": h2, "planet_a": l1, "planet_b": l2})
    return res


def get_birth_weekday(dob_str: str) -> str:
    try:
        dt = datetime.strptime(dob_str, "%Y-%m-%d")
        return WEEKDAY_NAMES[dt.weekday()]
    except Exception:
        return "Sunday"


def is_daytime_birth(birth_time_str: str) -> bool:
    try:
        parts = [int(x) for x in birth_time_str.split(":")[:2]]
        return 6 <= parts[0] < 18
    except Exception:
        return True


# ══════════════════════════════════════════════════════════════════
#  ANALYSIS SECTIONS
# ══════════════════════════════════════════════════════════════════

def analyze_core_methodology(pc: dict, transit: dict) -> tuple[list[ChandraNaadiReading], list[str]]:
    """Evaluate dynamic transit Moon connection and activation themes."""
    readings = []
    connected = []
    t_moon_sign = transit.get("Moon", {}).get("sign")
    if not t_moon_sign:
        return readings, connected

    for p, d in pc.get("planets", {}).items():
        p_sign = d.get("sign")
        if not p_sign:
            continue
        is_conjunct = (p_sign == t_moon_sign)
        is_aspected = planet_aspects_sign(p, p_sign, t_moon_sign)
        if is_conjunct or is_aspected:
            connected.append(p)
            theme = PLANET_ACTIVATION_THEMES.get(p, "Major karmic developments.")
            rel_type = "Direct Conjunction" if is_conjunct else "Aspectual Ray"
            readings.append(ChandraNaadiReading(
                rule_id=f"1.1_{p.upper()}",
                category="Core",
                title=f"Transit Moon Activates Natal {p} ({rel_type})",
                condition_met=True,
                condition_desc=f"Transit Moon in {t_moon_sign} connects with natal {p} in {p_sign}.",
                prediction=f"Active Life Theme: {theme} The native experiences heightened focus, opportunities, and unfolding events in {p} significations.",
                severity="info",
                planets_involved=[p, "Moon"],
                houses_involved=[],
                chapter_ref="Chapter 1",
            ))

    return readings, connected


def analyze_conjunctions(pc: dict, gender: str) -> list[ChandraNaadiReading]:
    """Evaluate 2-planet conjunctions with full book predictions."""
    readings = []
    by_sign = {}
    for p, d in pc.get("planets", {}).items():
        s = d.get("sign")
        if s:
            by_sign.setdefault(s, []).append(p)

    for s, plist in by_sign.items():
        if len(plist) >= 2:
            for i in range(len(plist)):
                for j in range(i + 1, len(plist)):
                    p1, p2 = plist[i], plist[j]
                    fs = frozenset({p1, p2})
                    rule = CONJUNCTION_RULES.get(fs)
                    if not rule:
                        continue

                    preds = rule.get("predictions", [])
                    pred_text = " ".join(preds)
                    mods = list(rule.get("modifiers", []))
                    yoga = rule.get("yoga_name")

                    # Gender specific additions
                    if gender.lower() == "male" and rule.get("male_specific"):
                        mods.extend(rule.get("male_specific", []))
                    elif gender.lower() == "female" and rule.get("female_specific"):
                        mods.extend(rule.get("female_specific", []))

                    # Degree comparison for Sun+Mercury
                    if fs == frozenset({"Sun", "Mercury"}):
                        sun_deg = pc.get("planets", {}).get("Sun", {}).get("degree_in_sign", 0)
                        mer_deg = pc.get("planets", {}).get("Mercury", {}).get("degree_in_sign", 0)
                        if mer_deg > sun_deg:
                            mods.append("Mercury degree > Sun degree: High mathematical, analytical, and formal academic acumen.")
                        else:
                            mods.append("Sun degree > Mercury degree: Practical commercial intelligence; career thrives through non-traditional applied skills.")

                    # Combustion check for Sun+Venus
                    if fs == frozenset({"Sun", "Venus"}):
                        sun_deg = pc.get("planets", {}).get("Sun", {}).get("degree_in_sign", 0)
                        ven_deg = pc.get("planets", {}).get("Venus", {}).get("degree_in_sign", 0)
                        if abs(sun_deg - ven_deg) < 5:
                            mods.append("DEEP COMBUSTION (< 5°): Venus is closely combust — requires conscious care in reproductive vitality and relationship patience.")

                    severity = "critical" if "Saturn" in [p1, p2] and "Mars" in [p1, p2] else "warning" if "Rahu" in [p1, p2] or "Ketu" in [p1, p2] else "info"
                    title = f"{p1} + {p2} Conjunction in {s}"
                    if yoga:
                        title += f" ({yoga})"

                    readings.append(ChandraNaadiReading(
                        rule_id=f"4.1_{p1[:3].upper()}_{p2[:3].upper()}",
                        category="Conjunction",
                        title=title,
                        condition_met=True,
                        condition_desc=f"{p1} and {p2} are conjunct in {s}.",
                        prediction=pred_text,
                        severity=severity,
                        planets_involved=[p1, p2],
                        houses_involved=[],
                        chapter_ref="Chapter 4",
                        modifiers=mods,
                    ))

    return readings


def analyze_aspects(pc: dict) -> list[ChandraNaadiReading]:
    """Evaluate Parashari and composite ray aspects with real classical predictions."""
    readings = []
    planets_data = pc.get("planets", {})

    for p1, d1 in planets_data.items():
        for p2, d2 in planets_data.items():
            if p1 == p2:
                continue
            s1, s2 = d1.get("sign"), d2.get("sign")
            if s1 and s2 and planet_aspects_sign(p1, s1, s2):
                aspect_pred = ASPECT_RULES.get(
                    (p1, p2),
                    f"{p1} projects its energy onto {p2}, blending their significations and creating dynamic life developments in their portfolios."
                )
                severity = "warning" if (p1 in ["Saturn", "Mars", "Rahu", "Ketu"] and p2 in ["Sun", "Moon", "Venus"]) else "info"
                readings.append(ChandraNaadiReading(
                    rule_id=f"5.1_{p1[:3].upper()}_{p2[:3].upper()}",
                    category="Aspect",
                    title=f"{p1} Aspects {p2}",
                    condition_met=True,
                    condition_desc=f"{p1} in {s1} casts an aspect on {p2} in {s2}.",
                    prediction=aspect_pred,
                    severity=severity,
                    planets_involved=[p1, p2],
                    houses_involved=[],
                    chapter_ref="Chapters 5 & 17",
                ))

    return readings


def analyze_bhava_significations(pc: dict) -> list[ChandraNaadiReading]:
    """Evaluate active houses (with occupants or key angles) and lord placements."""
    readings = []
    lagna = pc.get("meta", {}).get("lagna_sign")
    if not lagna:
        return readings

    for h in range(1, 13):
        h_sign = house_sign(h, lagna)
        lord = SIGN_LORDS.get(h_sign, "")
        occupants = natal_planets_in_sign(pc, h_sign)

        # Only evaluate houses with occupants or key kendra/trikona houses (1, 4, 5, 7, 9, 10)
        if not occupants and h not in [1, 4, 5, 7, 9, 10]:
            continue

        bdata = BHAVA_QUERY_MAP.get(h, {})
        domain = bdata.get("domain", f"House {h}")
        signifs = bdata.get("significations", [])
        signifs_str = ", ".join(signifs[:4])

        if occupants:
            occ_str = ", ".join(occupants)
            pred = f"{occ_str} occupies House {h} ({domain}). Governs: {signifs_str}. The combined energies of {occ_str} actively drive the native's achievements, resources, and life choices in this domain."
            title = f"House {h} ({domain}): {occ_str} Posited"
            severity = "warning" if any(p in ["Rahu", "Ketu", "Saturn", "Mars"] for p in occupants) and h in [6, 8, 12] else "info"
        else:
            pred = f"House {h} ({domain}) is ruled by {lord}. Governs: {signifs_str}. Provides the structural foundation for this portfolio."
            title = f"House {h} ({domain}) Portfolio"
            severity = "info"

        readings.append(ChandraNaadiReading(
            rule_id=f"6.1_H{h}",
            category="Bhava",
            title=title,
            condition_met=True,
            condition_desc=f"House {h} is {h_sign}, ruled by {lord}.",
            prediction=pred,
            severity=severity,
            planets_involved=occupants + ([lord] if lord else []),
            houses_involved=[h],
            chapter_ref="Chapter 6",
        ))

    return readings


def analyze_yogas(pc: dict) -> list[ChandraNaadiReading]:
    """Detect and evaluate all classical Chandra Naadi yogas."""
    readings = []

    # 1. Parivarthana Yoga
    pariv = detect_parivarthana(pc)
    for p in pariv:
        readings.append(ChandraNaadiReading(
            rule_id="8.1_PARIVARTHANA",
            category="Yoga",
            title=f"Parivarthana Yoga (House {p['house_a']} & House {p['house_b']})",
            condition_met=True,
            condition_desc=f"Mutual sign exchange between {p['planet_a']} and {p['planet_b']}.",
            prediction="Mutual exchange causes complete inversion of fortunes (initial struggle turns into lasting triumph, or vice versa). Strengthens both houses significantly during active transits.",
            severity="positive",
            planets_involved=[p["planet_a"], p["planet_b"]],
            houses_involved=[p["house_a"], p["house_b"]],
            chapter_ref="Chapter 8",
        ))

    # 2. Gaja Kesari Yoga
    j_sign = pc.get("planets", {}).get("Jupiter", {}).get("sign")
    m_sign = pc.get("planets", {}).get("Moon", {}).get("sign")
    if j_sign and m_sign:
        if j_sign == m_sign or planet_aspects_sign("Moon", m_sign, j_sign) or planet_aspects_sign("Jupiter", j_sign, m_sign):
            readings.append(ChandraNaadiReading(
                rule_id="8.2_GAJA_KESARI",
                category="Yoga",
                title="Gaja Kesari Yoga",
                condition_met=True,
                condition_desc=f"Jupiter ({j_sign}) and Moon ({m_sign}) in mutual conjunction or aspect.",
                prediction="Bestows lasting social prestige, generous leadership, wealth accumulated for children, and wide societal respect, though accompanied by emotional sensitivity.",
                severity="positive",
                planets_involved=["Jupiter", "Moon"],
                houses_involved=[],
                chapter_ref="Chapter 8",
            ))

    # 3. Madhana Gopala Yoga
    v_sign = pc.get("planets", {}).get("Venus", {}).get("sign")
    mer_sign = pc.get("planets", {}).get("Mercury", {}).get("sign")
    if v_sign and v_sign == mer_sign:
        readings.append(ChandraNaadiReading(
            rule_id="8.3_MADHANA_GOPALA",
            category="Yoga",
            title="Madhana Gopala Yoga",
            condition_met=True,
            condition_desc=f"Mercury and Venus conjunct in {v_sign}.",
            prediction="Connoisseur of fine arts, music, and elegant literature. Charming conversationalist, refined dressing, diplomatic negotiation power, and lucrative commercial alliances.",
            severity="positive",
            planets_involved=["Mercury", "Venus"],
            houses_involved=[],
            chapter_ref="Chapter 8",
        ))

    # 4. Mandaara / Thaara Dosha
    ma_sign = pc.get("planets", {}).get("Mars", {}).get("sign")
    sat_sign = pc.get("planets", {}).get("Saturn", {}).get("sign")
    if ma_sign and sat_sign and ma_sign == sat_sign:
        readings.append(ChandraNaadiReading(
            rule_id="8.4_MANDAARA_THAARA",
            category="Yoga",
            title="Mandaara Yoga / Thaara Dosha",
            condition_met=True,
            condition_desc=f"Mars and Saturn conjunct in {ma_sign}.",
            prediction="Formidable technical/mechanical endurance, revolutionary work ethic, but warns against bone injuries and requires conscious patience in marital communication.",
            severity="warning",
            planets_involved=["Mars", "Saturn"],
            houses_involved=[],
            chapter_ref="Chapter 8 & 14",
            remedies=["Settle domestic differences privately without third-party exposure; worship Lord Kalabhairava."],
        ))

    return readings


def analyze_health(pc: dict) -> list[ChandraNaadiReading]:
    """Evaluate medical vulnerabilities using PLANET_DISEASE_MAP."""
    readings = []
    lagna = pc.get("meta", {}).get("lagna_sign")
    if not lagna:
        return readings

    h6_sign = house_sign(6, lagna)
    h8_sign = house_sign(8, lagna)
    h6_planets = natal_planets_in_sign(pc, h6_sign)
    h8_planets = natal_planets_in_sign(pc, h8_sign)

    for p in set(h6_planets + h8_planets):
        dis = PLANET_DISEASE_MAP.get(p, [])
        dis_str = ", ".join(dis)
        h_num = 6 if p in h6_planets else 8
        readings.append(ChandraNaadiReading(
            rule_id=f"9.2.1_{p.upper()}",
            category="Health",
            title=f"Health Vulnerability: {p} in House {h_num}",
            condition_met=True,
            condition_desc=f"{p} occupies Dusthana House {h_num}.",
            prediction=f"Health sensitivities indicated in {p} portfolios: {dis_str}. Preventive health care and disciplined routine recommended.",
            severity="caution",
            planets_involved=[p],
            houses_involved=[h_num],
            chapter_ref="Chapter 9",
        ))

    return readings


def analyze_debts(pc: dict) -> list[ChandraNaadiReading]:
    """Evaluate financial liabilities using DEBT_MATRIX."""
    readings = []
    rahu_sign = pc.get("planets", {}).get("Rahu", {}).get("sign")
    ketu_sign = pc.get("planets", {}).get("Ketu", {}).get("sign")

    for p in PLANETS_7:
        p_sign = pc.get("planets", {}).get(p, {}).get("sign")
        if p_sign in [rahu_sign, ketu_sign]:
            node = "Rahu" if p_sign == rahu_sign else "Ketu"
            fs = frozenset({p, node})
            causes = DEBT_MATRIX.get(fs, [])
            c_text = ", ".join(causes)
            readings.append(ChandraNaadiReading(
                rule_id=f"9.2.5_{p[:3].upper()}_{node[:3].upper()}",
                category="Debt",
                title=f"Karmic Debt Pattern: {p} + {node}",
                condition_met=True,
                condition_desc=f"{p} is conjunct {node} in {p_sign}.",
                prediction=f"Financial obligations or loan commitments indicated for: {c_text}. Native must avoid uncollateralized lending or speculative over-extension.",
                severity="warning",
                planets_involved=[p, node],
                houses_involved=[],
                chapter_ref="Chapter 16",
            ))

    return readings


def analyze_marriage(pc: dict, gender: str) -> list[ChandraNaadiReading]:
    """Evaluate relationship and marital prospects from classical Naadi frameworks."""
    readings = []
    v_s = pc.get("planets", {}).get("Venus", {}).get("sign")
    ma_s = pc.get("planets", {}).get("Mars", {}).get("sign")
    me_s = pc.get("planets", {}).get("Mercury", {}).get("sign")

    if gender.lower() == "male":
        v_strong = is_strong("Venus", v_s) if v_s else False
        me_strong = is_strong("Mercury", me_s) if me_s else False
        v_dig = pc.get("planets", {}).get("Venus", {}).get("dignity", "neutral")
        if v_strong:
            pred = f"Venus (Wife) stands strong in {v_s} ({v_dig}). The spouse is dignified, noble, and brings lasting prosperity and domestic harmony to the household."
            sev = "positive"
        else:
            pred = f"Venus (Wife) posited in {v_s} ({v_dig}). Marital life flourishes when expectations are aligned through clear communication and mutual patience."
            sev = "caution"
    else:
        ma_strong = is_strong("Mars", ma_s) if ma_s else False
        ma_dig = pc.get("planets", {}).get("Mars", {}).get("dignity", "neutral")
        if ma_strong:
            pred = f"Mars (Husband) stands strong in {ma_s} ({ma_dig}). The husband is ambitious, protective, energetic, and brings structural stability to the family."
            sev = "positive"
        else:
            pred = f"Mars (Husband) posited in {ma_s} ({ma_dig}). Domestic partnership thrives through mutual respect and shared decision-making."
            sev = "caution"

    readings.append(ChandraNaadiReading(
        rule_id="9.3.1_MARRIAGE",
        category="Marriage",
        title="Marriage & Relationship Foundations",
        condition_met=True,
        condition_desc=f"Evaluated relationship significators for {gender} native.",
        prediction=pred,
        severity=sev,
        planets_involved=["Venus", "Mars", "Mercury"],
        houses_involved=[7],
        chapter_ref="Chapter 9",
    ))

    return readings


def analyze_childbirth(pc: dict, transit: dict) -> list[ChandraNaadiReading]:
    """Evaluate progeny and childbirth indications."""
    readings = []
    j_s = pc.get("planets", {}).get("Jupiter", {}).get("sign")
    s_s = pc.get("planets", {}).get("Saturn", {}).get("sign")
    r_s = pc.get("planets", {}).get("Rahu", {}).get("sign")

    if j_s and s_s and j_s == s_s:
        readings.append(ChandraNaadiReading(
            rule_id="9.1.2_SPERM_MOTILITY",
            category="Childbirth",
            title="Jupiter + Saturn Conjunction (Childbirth Timing)",
            condition_met=True,
            condition_desc=f"Jupiter and Saturn conjunct in {j_s}.",
            prediction="Initial delay in progeny timing due to slow motility/conception factors. Conception succeeds smoothly when transiting Jupiter moves ahead of natal Saturn.",
            severity="caution",
            planets_involved=["Jupiter", "Saturn"],
            houses_involved=[5],
            chapter_ref="Chapter 9",
        ))

    if j_s and r_s and j_s == r_s:
        readings.append(ChandraNaadiReading(
            rule_id="9.1.1_IVF_ASSISTED",
            category="Childbirth",
            title="Jupiter + Rahu Conjunction (Assisted Conception)",
            condition_met=True,
            condition_desc=f"Jupiter and Rahu conjunct in {j_s}.",
            prediction="Prime indicator for modern assisted reproductive treatments (IVF/clinical care) when transits align favorably.",
            severity="info",
            planets_involved=["Jupiter", "Rahu"],
            houses_involved=[5],
            chapter_ref="Chapter 9",
        ))

    return readings


def analyze_death_danger(pc: dict) -> list[ChandraNaadiReading]:
    """Compute Maandi longitude and evaluate longevity indicators."""
    readings = []
    dob = pc.get("meta", {}).get("dob", "1990-01-01")
    bt = pc.get("meta", {}).get("birth_time", "12:00")
    sun_deg = pc.get("planets", {}).get("Sun", {}).get("abs_degree", 0.0)

    weekday = get_birth_weekday(dob)
    daytime = is_daytime_birth(bt)
    maandi_lon = compute_maandi(sun_deg, weekday, daytime)
    maandi_s = SIGNS[int(maandi_lon // 30) % 12]

    readings.append(ChandraNaadiReading(
        rule_id="9.4.1_MAANDI",
        category="Death",
        title=f"Karmic Pivot: Maandi in {maandi_s} ({maandi_lon:.2f}°)",
        condition_met=True,
        condition_desc=f"Computed Maandi at {maandi_lon:.2f}° in {maandi_s}.",
        prediction="Maandi acts as the primary indicator for extreme danger and karmic resolution. Transit of Moon or dasha lords across this degree requires mindful health and travel caution.",
        severity="info",
        planets_involved=[],
        houses_involved=[8],
        chapter_ref="Chapter 9",
    ))

    return readings


def analyze_business(pc: dict, transit: dict) -> list[ChandraNaadiReading]:
    """Evaluate business and career developments through transit Saturn."""
    readings = []
    t_sat_s = transit.get("Saturn", {}).get("sign")
    if not t_sat_s:
        return readings

    for p, d in pc.get("planets", {}).items():
        if d.get("sign") == t_sat_s:
            s_data = TRANSIT_SATURN_EFFECTS.get(p, {})
            if isinstance(s_data, dict):
                eff_text = s_data.get("effect", "")
                warn_text = s_data.get("warning", "")
                pred_text = eff_text + (" " + warn_text if warn_text else "")
            else:
                pred_text = str(s_data)

            readings.append(ChandraNaadiReading(
                rule_id=f"9.5.1_SATURN_{p.upper()}",
                category="Business",
                title=f"Transit Saturn Contacting Natal {p}",
                condition_met=True,
                condition_desc=f"Transit Saturn in {t_sat_s} transits over natal {p}.",
                prediction=f"Professional Impact: {pred_text}",
                severity="caution",
                planets_involved=["Saturn", p],
                houses_involved=[10],
                chapter_ref="Chapter 9",
            ))

    return readings


def analyze_transits(pc: dict, transit: dict) -> list[ChandraNaadiReading]:
    """Evaluate Mars transit through houses from natal Lagna."""
    readings = []
    lagna = pc.get("meta", {}).get("lagna_sign")
    t_mars_s = transit.get("Mars", {}).get("sign")

    if lagna and t_mars_s:
        h = house_from_lagna(lagna, t_mars_s)
        eff = MARS_TRANSIT_BHAVA.get(h, "Dynamic shifts in energy and decision-making.")
        readings.append(ChandraNaadiReading(
            rule_id=f"2.1_MARS_H{h}",
            category="Transit",
            title=f"Transit Mars in House {h} ({t_mars_s})",
            condition_met=True,
            condition_desc=f"Mars transits House {h} from Lagna.",
            prediction=f"Transit Mars Effect: {eff}",
            severity="warning" if h in [6, 8, 12] else "info",
            planets_involved=["Mars"],
            houses_involved=[h],
            chapter_ref="Chapter 2",
        ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  MASTER ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════

def analyze_chandra_naadi(
    pc: dict,
    *,
    analysis_datetime: datetime | None = None,
    gender: str = "male",
) -> dict:
    """
    Master orchestrator for Chandra Naadi analysis.
    Takes precomputed chart dict (from compute_chart) and evaluates all book rules.
    """
    if analysis_datetime is None:
        analysis_datetime = datetime.now()

    transit = get_transit_positions(analysis_datetime)
    core_readings, connected_planets = analyze_core_methodology(pc, transit)
    conjunction_readings = analyze_conjunctions(pc, gender)
    aspect_readings = analyze_aspects(pc)
    bhava_readings = analyze_bhava_significations(pc)
    yoga_readings = analyze_yogas(pc)
    health_readings = analyze_health(pc)
    debt_readings = analyze_debts(pc)
    childbirth_readings = analyze_childbirth(pc, transit)
    marriage_readings = analyze_marriage(pc, gender)
    death_readings = analyze_death_danger(pc)
    business_readings = analyze_business(pc, transit)
    transit_readings = analyze_transits(pc, transit)

    all_readings = (
        core_readings
        + conjunction_readings
        + aspect_readings
        + bhava_readings
        + yoga_readings
        + health_readings
        + debt_readings
        + childbirth_readings
        + marriage_readings
        + death_readings
        + business_readings
        + transit_readings
    )

    fired_readings = [r for r in all_readings if r.condition_met]
    critical_alerts = [r.title for r in fired_readings if r.severity == "critical"]
    positive_indicators = [r.title for r in fired_readings if r.severity == "positive"]

    client_name = pc.get("meta", {}).get("client", "Native")
    dob = pc.get("meta", {}).get("dob", "")
    lagna = pc.get("meta", {}).get("lagna_sign", "")

    # Maandi
    sun_deg = pc.get("planets", {}).get("Sun", {}).get("abs_degree", 0.0)
    weekday = get_birth_weekday(dob)
    daytime = is_daytime_birth(pc.get("meta", {}).get("birth_time", "12:00"))
    maandi_lon = compute_maandi(sun_deg, weekday, daytime)
    maandi_sign = SIGNS[int(maandi_lon // 30) % 12]

    return {
        "meta": {
            "client": client_name,
            "dob": dob,
            "analysis_datetime": str(analysis_datetime),
            "gender": gender,
            "lagna": lagna,
            "maandi_degree": maandi_lon,
            "maandi_sign": maandi_sign,
        },
        "transit_snapshot": transit,
        "connected_planets": connected_planets,
        "conjunction_readings": conjunction_readings,
        "aspect_readings": aspect_readings,
        "bhava_readings": bhava_readings,
        "yoga_readings": yoga_readings,
        "health_readings": health_readings,
        "debt_readings": debt_readings,
        "childbirth_readings": childbirth_readings,
        "marriage_readings": marriage_readings,
        "death_readings": death_readings,
        "business_readings": business_readings,
        "transit_readings": transit_readings,
        "all_readings": all_readings,
        "summary": {
            "total_rules_evaluated": len(all_readings),
            "rules_fired": len(fired_readings),
            "critical_alerts": critical_alerts,
            "positive_indicators": positive_indicators,
        },
    }
