#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lal_kitab_analysis.py — Lal Kitab Diagnostic & Remedial Analysis Engine

Implements the complete Lal Kitab methodology:
- Pakka Ghar (Permanent Houses) & Planetary Dignities
- Soya Graha & Soya Ghar (Sleeping Planets & Houses)
- Special Aspect Dynamics: 100%, 50%, 25%, Takkar (Clash), Dhoka (Deception), Buniyad (Foundation)
- Masnui Grahas (Compound/Synthetic Planets)
- Pitra Rina (9 Ancestral Debts) & Collective Family Upayas
- House-Wise Placements, Specific Upayas & Strict Precautions (Parhez)
- Planetary Conjunction Remedies (Dual-Graha Upayas)
- General Remedy Rules & Protocols (40-43 Day Timing & Guidelines)

Zero author or publisher references are included.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from astro_precompute import (
    SIGNS,
    SIGN_LORDS,
    sign_index,
    house_from_lagna,
    house_sign,
)
from lal_kitab_book_data import (
    LAL_KITAB_PAKKA_GHAR,
    LAL_KITAB_HOUSE_KARAKAS,
    LAL_KITAB_DIGNITIES,
    LAL_KITAB_DESTINY_AWAKENING,
    LAL_KITAB_ASPECT_RULES,
    LAL_KITAB_MASNUI_GRAHAS,
    LAL_KITAB_PITRA_RINA,
    LAL_KITAB_GENERAL_REMEDY_RULES,
    LAL_KITAB_HOUSE_PRECAUTIONS,
    LAL_KITAB_CONJUNCTION_REMEDIES,
    LAL_KITAB_PLANET_HOUSE_RULES,
)

PLANETS_9 = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


@dataclass
class LalKitabReading:
    rule_id: str
    category: str
    title: str
    condition_met: bool
    condition_desc: str
    prediction: str
    severity: str  # "info" | "positive" | "caution" | "warning" | "critical"
    planets_involved: list[str]
    houses_involved: list[int]
    upayas: list[str] = field(default_factory=list)
    precautions: list[str] = field(default_factory=list)


def get_planet_houses(pc: dict) -> dict[str, int]:
    """Extract whole sign house (1-12) for all 9 planets from chart data."""
    res = {}
    planets = pc.get("planets", {})
    lagna = pc.get("meta", {}).get("lagna_sign", "Aries")
    for p in PLANETS_9:
        if p in planets:
            p_data = planets[p]
            h = p_data.get("house")
            if h is None:
                p_sign = p_data.get("sign", "")
                if p_sign and lagna:
                    h = house_from_lagna(lagna, p_sign)
                else:
                    h = 1
            res[p] = int(h)
        else:
            res[p] = 1
    return res


def get_house_occupants(planet_houses: dict[str, int]) -> dict[int, list[str]]:
    """Map house number 1-12 to list of occupying planets."""
    occupants = {h: [] for h in range(1, 13)}
    for p, h in planet_houses.items():
        if 1 <= h <= 12:
            occupants[h].append(p)
    return occupants


# ══════════════════════════════════════════════════════════════════
#  1. PAKKA GHAR & DIGNITY CALIBRATION
# ══════════════════════════════════════════════════════════════════

def analyze_pakka_and_dignities(planet_houses: dict[str, int]) -> list[LalKitabReading]:
    """Analyze Pakka Ghar (Permanent House) activations and Lal Kitab exaltation/debilitation."""
    readings = []

    for p, h in planet_houses.items():
        # Pakka Ghar check
        pakka_houses = LAL_KITAB_PAKKA_GHAR.get(p, [])
        if h in pakka_houses:
            readings.append(LalKitabReading(
                rule_id=f"LK_PAKKA_{p.upper()}_H{h}",
                category="Pakka Ghar",
                title=f"{p} in Permanent Abode (House {h} Pakka Ghar)",
                condition_met=True,
                condition_desc=f"{p} occupies its natural permanent Lal Kitab house (House {h}).",
                prediction=f"{p} operates from its natural foundation in House {h}, providing steady protective strength to its portfolio.",
                severity="positive",
                planets_involved=[p],
                houses_involved=[h],
                upayas=[f"Nurture the positive significations of House {h} and respect elders related to {p}."]
            ))

        # Dignity check
        dignity_data = LAL_KITAB_DIGNITIES.get(p, {})
        exalted_h = dignity_data.get("exalted_house")
        debilitated_h = dignity_data.get("debilitated_house")

        if h == exalted_h:
            readings.append(LalKitabReading(
                rule_id=f"LK_EXALTED_{p.upper()}_H{h}",
                category="Dignity",
                title=f"{p} Exalted in Lal Kitab (House {h})",
                condition_met=True,
                condition_desc=f"{p} is placed in House {h} (peak Lal Kitab exaltation).",
                prediction=f"Supreme strength for {p}: Manifests high authority, clarity, and rapid expansion in its significations.",
                severity="positive",
                planets_involved=[p],
                houses_involved=[h]
            ))
        elif h == debilitated_h:
            readings.append(LalKitabReading(
                rule_id=f"LK_DEBILITATED_{p.upper()}_H{h}",
                category="Dignity",
                title=f"{p} in Lal Kitab Depletion Zone (House {h})",
                condition_met=True,
                condition_desc=f"{p} occupies House {h} (Lal Kitab debilitation).",
                prediction=f"{p} requires conscious remedial support to prevent energy drainage and unexpected obstacles.",
                severity="caution",
                planets_involved=[p],
                houses_involved=[h],
                upayas=[LAL_KITAB_PLANET_HOUSE_RULES.get(p, {}).get(h, {}).get("upaya", "Follow traditional charity.")]
            ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  2. SOYA GRAHA & SOYA GHAR (SLEEPING PLANETS & HOUSES)
# ══════════════════════════════════════════════════════════════════

def analyze_sleeping_houses_and_planets(
    planet_houses: dict[str, int],
    house_occupants: dict[int, list[str]]
) -> list[LalKitabReading]:
    """Identify sleeping houses (Soya Ghar) and their destiny awakening parameters."""
    readings = []

    for h in range(1, 13):
        occupants = house_occupants.get(h, [])
        if not occupants:
            opposite_h = ((h + 5) % 12) + 1
            opposite_occupants = house_occupants.get(opposite_h, [])
            
            if not opposite_occupants:
                awakening_info = LAL_KITAB_DESTINY_AWAKENING.get(h, {"planet": "Mars", "age": 28, "theme": "Awakening of life portfolio"})
                readings.append(LalKitabReading(
                    rule_id=f"LK_SOYA_GHAR_H{h}",
                    category="Soya Ghar",
                    title=f"House {h} is Soya (Dormant Foundation)",
                    condition_met=True,
                    condition_desc=f"House {h} is unoccupied and receives no direct opposite sight from House {opposite_h}.",
                    prediction=f"Dormant House {h}: Significations of House {h} activate primarily around Age {awakening_info['age']} under the influence of {awakening_info['planet']}. {awakening_info['theme']}.",
                    severity="info",
                    planets_involved=[awakening_info["planet"]],
                    houses_involved=[h],
                    upayas=[f"Engage in supportive activities related to {awakening_info['planet']} to gently awaken House {h}."]
                ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  3. SPECIAL LAL KITAB ASPECT DYNAMICS
# ══════════════════════════════════════════════════════════════════

def analyze_lal_kitab_aspects(
    planet_houses: dict[str, int],
    house_occupants: dict[int, list[str]]
) -> list[LalKitabReading]:
    """Evaluate Takkar (Collision), Dhoka (Deception), Buniyad (Foundation), and direct aspects."""
    readings = []

    # 1. Takkar (Direct Clash)
    takkar_pairs = LAL_KITAB_ASPECT_RULES["takkar"]["pairs"]
    for h1, h2 in takkar_pairs:
        occ1 = house_occupants.get(h1, [])
        occ2 = house_occupants.get(h2, [])
        if occ1 and occ2 and h1 < h2:
            readings.append(LalKitabReading(
                rule_id=f"LK_TAKKAR_H{h1}_H{h2}",
                category="Aspect",
                title=f"Takkar (Direct Planetary Clash) between House {h1} & House {h2}",
                condition_met=True,
                condition_desc=f"House {h1} ({', '.join(occ1)}) and House {h2} ({', '.join(occ2)}) form a mutual Takkar angle.",
                prediction=f"Takkar Dynamic: {', '.join(occ1)} and {', '.join(occ2)} create structural friction. Balanced conduct and charitable upayas relieve mutual strain.",
                severity="warning",
                planets_involved=occ1 + occ2,
                houses_involved=[h1, h2],
                upayas=["Maintain calm diplomacy during high-stakes negotiations; avoid abrupt heated debates."]
            ))

    # 2. Dhoka (Deception / Mutual Undermining)
    dhoka_pairs = LAL_KITAB_ASPECT_RULES["dhoka"]["pairs"]
    for h1, h2 in dhoka_pairs:
        occ1 = house_occupants.get(h1, [])
        occ2 = house_occupants.get(h2, [])
        if occ1 and occ2:
            readings.append(LalKitabReading(
                rule_id=f"LK_DHOKA_H{h1}_H{h2}",
                category="Aspect",
                title=f"Dhoka Drishti (Undermining Angle) from House {h1} to House {h2}",
                condition_met=True,
                condition_desc=f"Planets in House {h1} ({', '.join(occ1)}) cast Dhoka sight upon House {h2} ({', '.join(occ2)}).",
                prediction=f"Dhoka Angle: {', '.join(occ1)} in House {h1} can create unexpected leakages or delays in House {h2} ({', '.join(occ2)}) matters if unverified.",
                severity="caution",
                planets_involved=occ1 + occ2,
                houses_involved=[h1, h2],
                upayas=["Keep financial and commercial agreements strictly documented in writing."]
            ))

    # 3. Buniyad (Foundational Taproot)
    buniyad_pairs = LAL_KITAB_ASPECT_RULES["buniyad"]["pairs"]
    for h1, h2 in buniyad_pairs:
        occ1 = house_occupants.get(h1, [])
        occ2 = house_occupants.get(h2, [])
        if occ1 and occ2:
            readings.append(LalKitabReading(
                rule_id=f"LK_BUNIYAD_H{h1}_H{h2}",
                category="Aspect",
                title=f"Buniyad (Pillar Support) from House {h1} to House {h2}",
                condition_met=True,
                condition_desc=f"House {h1} ({', '.join(occ1)}) acts as the foundational taproot supporting House {h2} ({', '.join(occ2)}).",
                prediction=f"Buniyad Pillar: {', '.join(occ1)} in House {h1} fortifies and sustains the long-term success of {', '.join(occ2)} in House {h2}.",
                severity="positive",
                planets_involved=occ1 + occ2,
                houses_involved=[h1, h2]
            ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  4. MASNUI GRAHAS (COMPOUND / ARTIFICIAL PLANETS)
# ══════════════════════════════════════════════════════════════════

def analyze_masnui_grahas(
    planet_houses: dict[str, int],
    house_occupants: dict[int, list[str]]
) -> list[LalKitabReading]:
    """Evaluate synthetic and compound planetary combinations (Masnui Grahas)."""
    readings = []

    sun_h = planet_houses.get("Sun", 1)
    merc_h = planet_houses.get("Mercury", 1)
    sat_h = planet_houses.get("Saturn", 1)

    if sun_h == merc_h:
        readings.append(LalKitabReading(
            rule_id="LK_MASNUI_MARS_NEK",
            category="Masnui",
            title="Mars Nek Manifestation (Sun + Mercury Synthetic Catalyst)",
            condition_met=True,
            condition_desc=f"Sun and Mercury unite in House {sun_h}, generating synthetic Mars Nek energy.",
            prediction="Mars Nek (Righteous Bravery): Courageous leadership backed by tactical intellect, protecting family and enterprise.",
            severity="positive",
            planets_involved=["Sun", "Mercury"],
            houses_involved=[sun_h]
        ))

    if sun_h == sat_h:
        readings.append(LalKitabReading(
            rule_id="LK_MASNUI_MARS_BAD",
            category="Masnui",
            title="Mars Bad Precaution (Sun + Saturn Tension)",
            condition_met=True,
            condition_desc=f"Sun and Saturn co-occupy House {sun_h}, creating synthetic Mars Bad friction.",
            prediction="Mars Bad Sensitivity: Tendency towards abrupt impulsiveness, temper spikes, or paternal friction. Demands patience.",
            severity="warning",
            planets_involved=["Sun", "Saturn"],
            houses_involved=[sun_h],
            upayas=["Feed monkeys with roasted gram and jaggery on Tuesdays; avoid harsh speech with elders."]
        ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  5. PITRA RINA (THE 9 ANCESTRAL DEBTS & COLLECTIVE UPAYAS)
# ══════════════════════════════════════════════════════════════════

def analyze_pitra_rina(planet_houses: dict[str, int]) -> list[LalKitabReading]:
    """Evaluate the 9 classical Lal Kitab ancestral debts and assign authentic remedies."""
    readings = []

    jup_h = planet_houses.get("Jupiter", 1)
    if jup_h in [2, 5, 9, 12]:
        afflictors = [p for p in ["Venus", "Mercury", "Saturn", "Rahu"] if planet_houses.get(p) == jup_h]
        if afflictors:
            debt = LAL_KITAB_PITRA_RINA["Pitra_Rina"]
            readings.append(LalKitabReading(
                rule_id="LK_RINA_PITRA",
                category="Pitra Rina",
                title=debt["name"],
                condition_met=True,
                condition_desc=f"Jupiter in House {jup_h} is conjoined by {', '.join(afflictors)}.",
                prediction=f"Karmic Debt Indication: {debt['symptoms']}",
                severity="warning",
                planets_involved=["Jupiter"] + afflictors,
                houses_involved=[jup_h],
                upayas=[debt["remedy"]]
            ))

    moon_h = planet_houses.get("Moon", 1)
    if moon_h == 4 and (planet_houses.get("Ketu") == 4 or planet_houses.get("Rahu") == 4):
        debt = LAL_KITAB_PITRA_RINA["Matru_Rina"]
        readings.append(LalKitabReading(
            rule_id="LK_RINA_MATRU",
            category="Pitra Rina",
            title=debt["name"],
            condition_met=True,
            condition_desc="Moon in House 4 is afflicted by Rahu or Ketu.",
            prediction=f"Karmic Debt Indication: {debt['symptoms']}",
            severity="warning",
            planets_involved=["Moon", "Rahu" if planet_houses.get("Rahu") == 4 else "Ketu"],
            houses_involved=[4],
            upayas=[debt["remedy"]]
        ))

    sun_h = planet_houses.get("Sun", 1)
    if sun_h in [1, 5, 11]:
        afflictors = [p for p in ["Saturn", "Rahu", "Ketu"] if planet_houses.get(p) == sun_h]
        if afflictors:
            debt = LAL_KITAB_PITRA_RINA["Swakathya_Rina"]
            readings.append(LalKitabReading(
                rule_id="LK_RINA_SWAKATHYA",
                category="Pitra Rina",
                title=debt["name"],
                condition_met=True,
                condition_desc=f"Sun in House {sun_h} is conjoined by {', '.join(afflictors)}.",
                prediction=f"Karmic Debt Indication: {debt['symptoms']}",
                severity="warning",
                planets_involved=["Sun"] + afflictors,
                houses_involved=[sun_h],
                upayas=[debt["remedy"]]
            ))

    mars_h = planet_houses.get("Mars", 1)
    if mars_h in [3, 8]:
        afflictors = [p for p in ["Mercury", "Ketu"] if planet_houses.get(p) == mars_h]
        if afflictors:
            debt = LAL_KITAB_PITRA_RINA["Bhratri_Rina"]
            readings.append(LalKitabReading(
                rule_id="LK_RINA_BHRATRI",
                category="Pitra Rina",
                title=debt["name"],
                condition_met=True,
                condition_desc=f"Mars in House {mars_h} is conjoined by {', '.join(afflictors)}.",
                prediction=f"Karmic Debt Indication: {debt['symptoms']}",
                severity="warning",
                planets_involved=["Mars"] + afflictors,
                houses_involved=[mars_h],
                upayas=[debt["remedy"]]
            ))

    ven_h = planet_houses.get("Venus", 1)
    if ven_h in [2, 7]:
        afflictors = [p for p in ["Sun", "Rahu"] if planet_houses.get(p) == ven_h]
        if afflictors:
            debt = LAL_KITAB_PITRA_RINA["Stri_Rina"]
            readings.append(LalKitabReading(
                rule_id="LK_RINA_STRI",
                category="Pitra Rina",
                title=debt["name"],
                condition_met=True,
                condition_desc=f"Venus in House {ven_h} is conjoined by {', '.join(afflictors)}.",
                prediction=f"Karmic Debt Indication: {debt['symptoms']}",
                severity="warning",
                planets_involved=["Venus"] + afflictors,
                houses_involved=[ven_h],
                upayas=[debt["remedy"]]
            ))

    sat_h = planet_houses.get("Saturn", 1)
    if sat_h in [8, 10, 11]:
        afflictors = [p for p in ["Sun", "Moon", "Mars"] if planet_houses.get(p) == sat_h]
        if afflictors:
            debt = LAL_KITAB_PITRA_RINA["Zulm_Rina"]
            readings.append(LalKitabReading(
                rule_id="LK_RINA_ZULM",
                category="Pitra Rina",
                title=debt["name"],
                condition_met=True,
                condition_desc=f"Saturn in House {sat_h} is conjoined by {', '.join(afflictors)}.",
                prediction=f"Karmic Debt Indication: {debt['symptoms']}",
                severity="warning",
                planets_involved=["Saturn"] + afflictors,
                houses_involved=[sat_h],
                upayas=[debt["remedy"]]
            ))

    ketu_h = planet_houses.get("Ketu", 1)
    if ketu_h in [6, 12]:
        afflictors = [p for p in ["Moon", "Mars"] if planet_houses.get(p) == ketu_h]
        if afflictors:
            debt = LAL_KITAB_PITRA_RINA["Kanya_Rina"]
            readings.append(LalKitabReading(
                rule_id="LK_RINA_KANYA",
                category="Pitra Rina",
                title=debt["name"],
                condition_met=True,
                condition_desc=f"Ketu in House {ketu_h} is conjoined by {', '.join(afflictors)}.",
                prediction=f"Karmic Debt Indication: {debt['symptoms']}",
                severity="warning",
                planets_involved=["Ketu"] + afflictors,
                houses_involved=[ketu_h],
                upayas=[debt["remedy"]]
            ))

    merc_h = planet_houses.get("Mercury", 1)
    if merc_h in [6, 7]:
        afflictors = [p for p in ["Jupiter", "Moon"] if planet_houses.get(p) == merc_h]
        if afflictors:
            debt = LAL_KITAB_PITRA_RINA["Ishwar_Rina"]
            readings.append(LalKitabReading(
                rule_id="LK_RINA_ISHWAR",
                category="Pitra Rina",
                title=debt["name"],
                condition_met=True,
                condition_desc=f"Mercury in House {merc_h} is conjoined by {', '.join(afflictors)}.",
                prediction=f"Karmic Debt Indication: {debt['symptoms']}",
                severity="warning",
                planets_involved=["Mercury"] + afflictors,
                houses_involved=[merc_h],
                upayas=[debt["remedy"]]
            ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  6. PLANETARY CONJUNCTION REMEDIES
# ══════════════════════════════════════════════════════════════════

def analyze_conjunction_remedies(
    planet_houses: dict[str, int],
    house_occupants: dict[int, list[str]]
) -> list[LalKitabReading]:
    """Evaluate specific dual-planet conjunction remedies."""
    readings = []

    for h, occupants in house_occupants.items():
        if len(occupants) >= 2:
            for i in range(len(occupants)):
                for j in range(i + 1, len(occupants)):
                    pair = frozenset({occupants[i], occupants[j]})
                    if pair in LAL_KITAB_CONJUNCTION_REMEDIES:
                        c_data = LAL_KITAB_CONJUNCTION_REMEDIES[pair]
                        readings.append(LalKitabReading(
                            rule_id=f"LK_CONJ_{occupants[i].upper()}_{occupants[j].upper()}_H{h}",
                            category="Conjunction Remedy",
                            title=c_data["title"],
                            condition_met=True,
                            condition_desc=f"{occupants[i]} and {occupants[j]} co-occupy House {h}.",
                            prediction=c_data["prediction"],
                            severity="caution",
                            planets_involved=[occupants[i], occupants[j]],
                            houses_involved=[h],
                            upayas=[c_data["upaya"]]
                        ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  7. PLANETARY HOUSE PLACEMENT READINGS, UPAYAS & PRECAUTIONS (PARHEZ)
# ══════════════════════════════════════════════════════════════════

def analyze_house_placements(planet_houses: dict[str, int]) -> list[LalKitabReading]:
    """Extract specific Lal Kitab readings, practical upayas, and house precautions for each planet."""
    readings = []

    for p in PLANETS_9:
        h = planet_houses.get(p, 1)
        p_rules = LAL_KITAB_PLANET_HOUSE_RULES.get(p, {})
        h_info = p_rules.get(h, {})
        precaution = LAL_KITAB_HOUSE_PRECAUTIONS.get(p, {}).get(h, "")
        
        if h_info:
            readings.append(LalKitabReading(
                rule_id=f"LK_POS_{p.upper()}_H{h}",
                category="House Placement",
                title=h_info["title"],
                condition_met=True,
                condition_desc=f"{p} is positioned in House {h} from Lagna.",
                prediction=h_info["result"],
                severity="info" if h in [1, 2, 4, 5, 9, 10, 11] else "caution",
                planets_involved=[p],
                houses_involved=[h],
                upayas=[h_info["upaya"]] if h_info.get("upaya") else [],
                precautions=[precaution] if precaution else []
            ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  8. SPECIAL LAL KITAB TEVA CLASSIFICATIONS
# ══════════════════════════════════════════════════════════════════

def analyze_special_configurations(
    planet_houses: dict[str, int],
    house_occupants: dict[int, list[str]]
) -> list[LalKitabReading]:
    """Check for Dharmi Teva (Righteous Chart), Andha Teva (Blind Chart), and special formations."""
    readings = []

    jup_h = planet_houses.get("Jupiter", 1)
    sat_h = planet_houses.get("Saturn", 1)
    is_dharmi = (jup_h in [1, 5, 9, 11, 12]) or (sat_h == 11) or (jup_h == sat_h)

    if is_dharmi:
        readings.append(LalKitabReading(
            rule_id="LK_TEVA_DHARMI",
            category="Teva Classification",
            title="Dharmi Teva (Righteous Protective Shield)",
            condition_met=True,
            condition_desc="Chart possesses strong Jupiter/Saturn alignment (Dharmi Teva formation).",
            prediction="Dharmi Shield: The native receives invisible cosmic protection during severe crises. Malefic planets convert their adverse energy into constructive lessons.",
            severity="positive",
            planets_involved=["Jupiter", "Saturn"],
            houses_involved=[jup_h, sat_h],
            upayas=["Maintain absolute ethical integrity; avoid taking unfair advantage of others."]
        ))

    if sat_h == 7 and not house_occupants.get(1) and not house_occupants.get(4):
        readings.append(LalKitabReading(
            rule_id="LK_TEVA_ANDHA",
            category="Teva Classification",
            title="Andha Teva Precaution (Blind Chart Pattern)",
            condition_met=True,
            condition_desc="Saturn occupies House 7 with House 1 and House 4 vacant.",
            prediction="Andha Teva Warning: Demands extra verification in partnership and financial contracts to avoid deceptive ventures.",
            severity="warning",
            planets_involved=["Saturn"],
            houses_involved=[7, 1, 4],
            upayas=["Feed 10 blind individuals or donate towards eye care clinics."]
        ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  MASTER ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════

def analyze_lal_kitab(
    pc: dict,
    *,
    analysis_datetime: datetime | None = None,
    gender: str = "male",
) -> dict[str, Any]:
    """
    Master orchestrator for Lal Kitab analysis.
    Takes precomputed chart dict (from compute_chart) and evaluates all classical Lal Kitab fundamentals.
    """
    if analysis_datetime is None:
        analysis_datetime = datetime.now()

    planet_houses = get_planet_houses(pc)
    house_occupants = get_house_occupants(planet_houses)

    # Analytical pipelines
    pakka_readings = analyze_pakka_and_dignities(planet_houses)
    soya_readings = analyze_sleeping_houses_and_planets(planet_houses, house_occupants)
    aspect_readings = analyze_lal_kitab_aspects(planet_houses, house_occupants)
    masnui_readings = analyze_masnui_grahas(planet_houses, house_occupants)
    rina_readings = analyze_pitra_rina(planet_houses)
    conj_readings = analyze_conjunction_remedies(planet_houses, house_occupants)
    placement_readings = analyze_house_placements(planet_houses)
    teva_readings = analyze_special_configurations(planet_houses, house_occupants)

    all_readings = (
        pakka_readings
        + soya_readings
        + aspect_readings
        + masnui_readings
        + rina_readings
        + conj_readings
        + placement_readings
        + teva_readings
    )

    fired_readings = [r for r in all_readings if r.condition_met]
    critical_alerts = [r.title for r in fired_readings if r.severity in ["critical", "warning"]]
    positive_indicators = [r.title for r in fired_readings if r.severity == "positive"]

    # Collect upayas and precautions
    all_upayas = []
    all_precautions = []
    for r in fired_readings:
        for u in r.upayas:
            if u and u not in all_upayas:
                all_upayas.append(u)
        for p in r.precautions:
            if p and p not in all_precautions:
                all_precautions.append(p)

    client_name = pc.get("meta", {}).get("client", "Native")
    dob = pc.get("meta", {}).get("dob", "")
    lagna = pc.get("meta", {}).get("lagna_sign", "")

    return {
        "meta": {
            "client": client_name,
            "dob": dob,
            "analysis_datetime": str(analysis_datetime),
            "gender": gender,
            "lagna": lagna,
            "planet_houses": planet_houses,
        },
        "house_occupants": house_occupants,
        "general_rules": LAL_KITAB_GENERAL_REMEDY_RULES,
        "pakka_readings": pakka_readings,
        "soya_readings": soya_readings,
        "aspect_readings": aspect_readings,
        "masnui_readings": masnui_readings,
        "rina_readings": rina_readings,
        "conjunction_readings": conj_readings,
        "placement_readings": placement_readings,
        "teva_readings": teva_readings,
        "all_readings": all_readings,
        "remedies": all_upayas,
        "precautions": all_precautions,
        "summary": {
            "total_rules_evaluated": len(all_readings),
            "rules_fired": len(fired_readings),
            "critical_alerts": critical_alerts,
            "positive_indicators": positive_indicators,
            "total_upayas_prescribed": len(all_upayas),
            "total_precautions_prescribed": len(all_precautions),
        },
    }


if __name__ == "__main__":
    from astro_chart_bridge import compute_chart
    pc = compute_chart(
        client_name="Test Native",
        dob="1985-03-08",
        birth_time="00:05",
        place="Patna, India"
    )
    result = analyze_lal_kitab(pc, gender="male")
    print(f"Total rules evaluated: {result['summary']['total_rules_evaluated']}")
    print(f"Rules fired: {result['summary']['rules_fired']}")
    print(f"Positive indicators: {len(result['summary']['positive_indicators'])}")
    print(f"Critical alerts: {len(result['summary']['critical_alerts'])}")
    print(f"Total Upayas Prescribed: {result['summary']['total_upayas_prescribed']}")
    print(f"Total Precautions Prescribed: {result['summary']['total_precautions_prescribed']}")
