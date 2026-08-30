#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rahu_ketu_analysis.py — Rahu & Ketu: Vedic Nodal Astrology Analysis Engine

Implements the complete diagnostic and predictive rule set for Vedic Rahu & Ketu Shadow Planets' Naadi Astrology.

Evaluates:
  1. Sign Placements (Rahu/Ketu across 12 signs)
  2. House Placements (Rahu/Ketu across 12 houses)
  3. 2-Planet and 3-Planet Conjunctions with Rahu
  4. 2-Planet and 3-Planet Conjunctions with Ketu
  5. Kala Sarpa Yoga vs Kala Sarpa Dosha (12 types, rectification ages, separated planet)
  6. Special Nadi Principles (Sarpa Chandra Ambuli Point, Midpoint, Shadow Punarphoo, Dubious Character)
  7. Progeny Analysis (Puthra Dosha, Puthra Sogam, Female progeny)
  8. Medical Astrology (Disease combos, Scorpio Nodes, PCOD, Accident triad, Amputation)
  9. Dasha-Bhukti & Karma Exposure Timing (12 perilous periods, age exposure formula)
 10. Shadow Yogas (Saya Yoga across 12 houses, Maha Sakthi Yoga, Dhana Yoga)
 11. Ancestral Curses (Paternal & Maternal Poorvika Dosha)
 12. Remedial Measures (Gayatri mantras, deities, temples)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

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
from rahu_ketu_book_data import (
    DASHA_BHUKTI_RULES,
    DHANA_YOGA_RULES,
    FUNDAMENTAL_RULES,
    KALA_SARPA_NOTES,
    KALA_SARPA_RECTIFICATION_AGES,
    KALA_SARPA_TYPES,
    KARMA_EXPOSURE_AGES,
    KETU_CONJUNCTIONS,
    KETU_IN_SIGNS,
    KETU_TRIPLE_CONJUNCTIONS,
    MAHA_SAKTHI_YOGA,
    MEDICAL_RULES,
    PERILOUS_DASHA_PERIODS,
    POORVIKA_DOSHA,
    PROGENY_RULES,
    RAHU_CONJUNCTIONS,
    RAHU_IN_SIGNS,
    RAHU_KETU_IN_HOUSES,
    RAHU_KETU_NATURE,
    RAHU_TRIPLE_CONJUNCTIONS,
    REMEDIES,
    SAYA_YOGA,
    SPECIAL_NADI_PRINCIPLES,
    SPORTS_RULES,
)

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
PLANETS_7 = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
RAHU_STARS = ["Ardra", "Swati", "Shatabhisha"]
KETU_STARS = ["Ashwini", "Magha", "Mula"]


@dataclass
class RahuKetuReading:
    rule_id: str
    category: str
    title: str
    condition_met: bool
    condition_desc: str
    prediction: str
    severity: str  # "info" | "positive" | "caution" | "warning" | "critical"
    planets_involved: list[str] = field(default_factory=list)
    houses_involved: list[int] = field(default_factory=list)
    chapter_ref: str = ""
    modifiers: list[str] = field(default_factory=list)
    remedies: list[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════
#  CORE HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════

def get_rahu_ketu_houses(pc: dict) -> tuple[int, int]:
    """Return (rahu_house, ketu_house) as (int, int)."""
    rh = pc.get("planets", {}).get("Rahu", {}).get("house", 0)
    kh = pc.get("planets", {}).get("Ketu", {}).get("house", 0)
    return int(rh), int(kh)


def get_rahu_ketu_signs(pc: dict) -> tuple[str, str]:
    """Return (rahu_sign, ketu_sign)."""
    rs = pc.get("planets", {}).get("Rahu", {}).get("sign", "")
    ks = pc.get("planets", {}).get("Ketu", {}).get("sign", "")
    return str(rs), str(ks)


def get_planet_abs_degree(pc: dict, planet: str) -> float:
    """Get absolute sidereal degree (0-360) of a planet."""
    pdata = pc.get("planets", {}).get(planet, {})
    if not pdata:
        return 0.0
    sign = pdata.get("sign", "")
    deg_in_sign = pdata.get("degree_in_sign", 0.0)
    s_idx = sign_index(sign) if sign in SIGNS else 0
    return (s_idx * 30.0 + deg_in_sign) % 360.0


def planets_in_sign(pc: dict, sign: str) -> list[str]:
    """Return list of planet names in that sign."""
    if not sign:
        return []
    return [p for p in PLANETS if pc.get("planets", {}).get(p, {}).get("sign") == sign]


def planet_controls_sign(node_sign: str, target_sign: str) -> bool:
    """Rahu/Ketu exercise Control over 1st, 3rd, and 11th houses from their placement."""
    if not node_sign or not target_sign or node_sign not in SIGNS or target_sign not in SIGNS:
        return False
    idx_node = SIGNS.index(node_sign)
    idx_target = SIGNS.index(target_sign)
    diff = (idx_target - idx_node) % 12 + 1
    return diff in [1, 3, 11]


def check_kala_sarpa(pc: dict) -> dict:
    """
    Check if all 7 planets are hemmed between Rahu and Ketu axis.
    Determine:
      - Kala Sarpa Yoga (7 planets moving towards Ketu)
      - Kala Sarpa Dosha (7 planets moving towards Rahu)
      - Ardh Kala Sarpa (6 planets hemmed, 1 separated)
    """
    rahu_sign, ketu_sign = get_rahu_ketu_signs(pc)
    rahu_house, ketu_house = get_rahu_ketu_houses(pc)

    if not rahu_sign or not ketu_sign or rahu_sign not in SIGNS or ketu_sign not in SIGNS:
        return {
            "present": False,
            "type": "none",
            "rahu_house": rahu_house,
            "ketu_house": ketu_house,
            "name": "",
            "separated_planet": None,
        }

    r_idx = SIGNS.index(rahu_sign)
    k_idx = SIGNS.index(ketu_sign)

    # Path from Rahu to Ketu (forward)
    signs_rahu_to_ketu = []
    curr = r_idx
    while True:
        signs_rahu_to_ketu.append(SIGNS[curr])
        if curr == k_idx:
            break
        curr = (curr + 1) % 12

    # Path from Ketu to Rahu (forward)
    signs_ketu_to_rahu = []
    curr = k_idx
    while True:
        signs_ketu_to_rahu.append(SIGNS[curr])
        if curr == r_idx:
            break
        curr = (curr + 1) % 12

    planets_r_to_k = []
    planets_k_to_r = []

    for p in PLANETS_7:
        p_sign = pc.get("planets", {}).get(p, {}).get("sign", "")
        if p_sign in signs_rahu_to_ketu:
            planets_r_to_k.append(p)
        if p_sign in signs_ketu_to_rahu:
            planets_k_to_r.append(p)

    present = False
    k_type = "none"
    separated = None
    name = ""

    # Find the named type from KALA_SARPA_TYPES matching rahu_house/ketu_house
    matched_type_name = "Kala Sarpa"
    for kt in KALA_SARPA_TYPES:
        if kt.get("rahu_house") == rahu_house and kt.get("ketu_house") == ketu_house:
            matched_type_name = kt.get("name", "Kala Sarpa")
            break

    if len(planets_r_to_k) == 7:
        present = True
        k_type = "dosha"
        name = f"{matched_type_name} Kala Sarpa Dosha"
    elif len(planets_k_to_r) == 7:
        present = True
        k_type = "yoga"
        name = f"{matched_type_name} Kala Sarpa Yoga"
    elif len(planets_r_to_k) == 6:
        present = True
        k_type = "ardh_dosha"
        sep_list = [p for p in PLANETS_7 if p not in planets_r_to_k]
        separated = sep_list[0] if sep_list else None
        name = f"Ardh {matched_type_name} Dosha ({separated} Separated)"
    elif len(planets_k_to_r) == 6:
        present = True
        k_type = "ardh_yoga"
        sep_list = [p for p in PLANETS_7 if p not in planets_k_to_r]
        separated = sep_list[0] if sep_list else None
        name = f"Ardh {matched_type_name} Yoga ({separated} Separated)"

    return {
        "present": present,
        "type": k_type,
        "rahu_house": rahu_house,
        "ketu_house": ketu_house,
        "name": name,
        "matched_type_name": matched_type_name,
        "separated_planet": separated,
    }


def compute_sarpa_chandra_point(pc: dict) -> tuple[float, str, float]:
    """
    Calculate the Ambuli/Sarpa Chandra degree from Chapter 44:
      Distance = Rahu_degree - Moon_degree
      Sarpa_Chandra = Moon_degree + (Distance / 2)
    Returns (abs_deg, sign, deg_in_sign).
    """
    rahu_deg = get_planet_abs_degree(pc, "Rahu")
    moon_deg = get_planet_abs_degree(pc, "Moon")

    dist = (rahu_deg - moon_deg) % 360.0
    ambuli_abs = (moon_deg + dist / 2.0) % 360.0

    sign_i = int(ambuli_abs / 30.0) % 12
    deg_in = ambuli_abs % 30.0
    return ambuli_abs, SIGNS[sign_i], deg_in


def compute_rahu_ketu_midpoint(pc: dict) -> tuple[str, str]:
    """
    Axis Midpoints are the 4th and 10th signs from Rahu/Ketu.
    """
    rahu_sign, _ = get_rahu_ketu_signs(pc)
    if not rahu_sign or rahu_sign not in SIGNS:
        return "", ""
    r_idx = SIGNS.index(rahu_sign)
    mid1 = SIGNS[(r_idx + 3) % 12]  # 4th sign
    mid2 = SIGNS[(r_idx + 9) % 12]  # 10th sign
    return mid1, mid2


def check_shadow_punarphoo(pc: dict) -> bool:
    """
    Shadow Planet Punarphoo (Chapter 53):
    House lord of Rahu and house lord of Ketu aspect each other, combine, or interchange signs.
    """
    rahu_sign, ketu_sign = get_rahu_ketu_signs(pc)
    if not rahu_sign or not ketu_sign:
        return False

    rahu_lord = SIGN_LORDS.get(rahu_sign, "")
    ketu_lord = SIGN_LORDS.get(ketu_sign, "")

    if not rahu_lord or not ketu_lord:
        return False
    if rahu_lord == ketu_lord:
        return True

    rl_sign = pc.get("planets", {}).get(rahu_lord, {}).get("sign", "")
    kl_sign = pc.get("planets", {}).get(ketu_lord, {}).get("sign", "")

    if not rl_sign or not kl_sign:
        return False

    # Conjunction
    if rl_sign == kl_sign:
        return True

    # Parivarthana (interchange)
    if rl_sign == ketu_sign and kl_sign == rahu_sign:
        return True

    # Opposition (7th aspect)
    if rl_sign in SIGNS and kl_sign in SIGNS:
        r_i = SIGNS.index(rl_sign)
        k_i = SIGNS.index(kl_sign)
        if (r_i - k_i) % 12 == 6:
            return True

    return False


def get_current_dasha_bhukti(pc: dict) -> tuple[str, str]:
    """Extract current MD and AD from pc['vimshottari']."""
    v = pc.get("vimshottari", {})
    md = v.get("current_md", "") or v.get("dasha", "")
    ad = v.get("current_ad", "") or v.get("bhukti", "")
    if not ad and v.get("current_md_antardashas"):
        ads = v.get("current_md_antardashas", [])
        if ads and isinstance(ads[0], dict):
            ad = ads[0].get("lord", "")
    return md, ad


def is_perilous_period(dasha: str, bhukti: str) -> bool:
    """Check if (dasha, bhukti) matches any of the 12 perilous periods."""
    if not dasha or not bhukti:
        return False
    return (dasha, bhukti) in PERILOUS_DASHA_PERIODS


# ══════════════════════════════════════════════════════════════════
#  SECTION 1: SIGN PLACEMENT ANALYSIS
# ══════════════════════════════════════════════════════════════════

def analyze_sign_placement(pc: dict) -> list[RahuKetuReading]:
    """Evaluate Rahu and Ketu in the 12 signs."""
    readings = []
    rahu_sign, ketu_sign = get_rahu_ketu_signs(pc)

    if rahu_sign in RAHU_IN_SIGNS:
        pred = RAHU_IN_SIGNS[rahu_sign]
        severity = "critical" if rahu_sign == "Scorpio" else "caution" if rahu_sign in ["Aries", "Libra", "Pisces"] else "info"
        title = f"Rahu in {rahu_sign}"
        if rahu_sign == "Sagittarius":
            title += " (Kodanda Rahu)"
        readings.append(RahuKetuReading(
            rule_id=f"RK_SIGN_RAHU_{rahu_sign.upper()}",
            category="sign_placement",
            title=title,
            condition_met=True,
            condition_desc=f"Natal Rahu is placed in {rahu_sign}.",
            prediction=pred,
            severity=severity,
            planets_involved=["Rahu"],
            chapter_ref="Chapters 10 & 58",
        ))

    if ketu_sign in KETU_IN_SIGNS:
        pred = KETU_IN_SIGNS[ketu_sign]
        title = f"Ketu in {ketu_sign}"
        if ketu_sign == "Pisces":
            title += " (Moksha Ketu)"
        readings.append(RahuKetuReading(
            rule_id=f"RK_SIGN_KETU_{ketu_sign.upper()}",
            category="sign_placement",
            title=title,
            condition_met=True,
            condition_desc=f"Natal Ketu is placed in {ketu_sign}.",
            prediction=pred,
            severity="info",
            planets_involved=["Ketu"],
            chapter_ref="Chapter 10",
        ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  SECTION 2: HOUSE PLACEMENT ANALYSIS
# ══════════════════════════════════════════════════════════════════

def analyze_house_placement(pc: dict) -> list[RahuKetuReading]:
    """Evaluate Rahu and Ketu in the 12 houses."""
    readings = []
    rahu_house, ketu_house = get_rahu_ketu_houses(pc)

    if rahu_house in RAHU_KETU_IN_HOUSES:
        entry = RAHU_KETU_IN_HOUSES[rahu_house]
        pred = entry.get("rahu", "")
        severity = "warning" if rahu_house in [5, 7, 8, 12] else "info"
        readings.append(RahuKetuReading(
            rule_id=f"RK_HOUSE_RAHU_H{rahu_house}",
            category="house_placement",
            title=f"Rahu in House {rahu_house}",
            condition_met=True,
            condition_desc=f"Natal Rahu occupies House {rahu_house} from Lagna.",
            prediction=pred,
            severity=severity,
            planets_involved=["Rahu"],
            houses_involved=[rahu_house],
            chapter_ref="Chapter 11",
        ))

    if ketu_house in RAHU_KETU_IN_HOUSES:
        entry = RAHU_KETU_IN_HOUSES[ketu_house]
        pred = entry.get("ketu", "")
        severity = "positive" if ketu_house == 12 else "warning" if ketu_house in [5, 7, 8] else "info"
        readings.append(RahuKetuReading(
            rule_id=f"RK_HOUSE_KETU_H{ketu_house}",
            category="house_placement",
            title=f"Ketu in House {ketu_house}",
            condition_met=True,
            condition_desc=f"Natal Ketu occupies House {ketu_house} from Lagna.",
            prediction=pred,
            severity=severity,
            planets_involved=["Ketu"],
            houses_involved=[ketu_house],
            chapter_ref="Chapter 11",
        ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  SECTION 3: RAHU CONJUNCTIONS (2-PLANET & 3-PLANET)
# ══════════════════════════════════════════════════════════════════

def analyze_rahu_conjunctions(pc: dict) -> list[RahuKetuReading]:
    """Evaluate 2-planet and 3-planet conjunctions with Rahu."""
    readings = []
    rahu_sign, _ = get_rahu_ketu_signs(pc)
    if not rahu_sign:
        return readings

    conjunct_planets = [p for p in PLANETS_7 if pc.get("planets", {}).get(p, {}).get("sign") == rahu_sign]

    # 2-Planet conjunctions with Rahu
    for p in conjunct_planets:
        if p in RAHU_CONJUNCTIONS:
            cdata = RAHU_CONJUNCTIONS[p]
            preds = cdata.get("predictions", [])
            med = cdata.get("medical", [])
            full_text = " ".join(preds)
            if med:
                full_text += " Medical vulnerabilities: " + ", ".join(med) + "."
            severity = "critical" if p in ["Saturn", "Mars", "Sun"] else "warning"
            readings.append(RahuKetuReading(
                rule_id=f"RK_CONJ_RAHU_{p.upper()}",
                category="rahu_conjunction",
                title=f"Rahu + {p} Conjunction",
                condition_met=True,
                condition_desc=f"{p} is conjunct Rahu in {rahu_sign}.",
                prediction=full_text,
                severity=severity,
                planets_involved=["Rahu", p],
                chapter_ref="Chapter 3",
                modifiers=[f"Medical: {', '.join(med)}"] if med else [],
            ))

    # 3-Planet conjunctions with Rahu
    if len(conjunct_planets) >= 2:
        for i in range(len(conjunct_planets)):
            for j in range(i + 1, len(conjunct_planets)):
                p1, p2 = conjunct_planets[i], conjunct_planets[j]
                pair_set = {p1, p2}
                for tr in RAHU_TRIPLE_CONJUNCTIONS:
                    tr_planets = set(tr.get("planets", []))
                    if "Rahu" in tr_planets and pair_set.issubset(tr_planets):
                        preds = tr.get("predictions", [])
                        pred_str = " ".join(preds)
                        readings.append(RahuKetuReading(
                            rule_id=f"RK_TRIPLE_RAHU_{p1.upper()}_{p2.upper()}",
                            category="rahu_triple_conjunction",
                            title=f"Rahu + {p1} + {p2} Triple Conjunction",
                            condition_met=True,
                            condition_desc=f"Rahu, {p1}, and {p2} are conjunct in {rahu_sign}.",
                            prediction=pred_str,
                            severity="critical" if "Saturn" in pair_set or "Mars" in pair_set else "warning",
                            planets_involved=["Rahu", p1, p2],
                            chapter_ref="Chapter 3",
                        ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  SECTION 4: KETU CONJUNCTIONS (2-PLANET & 3-PLANET)
# ══════════════════════════════════════════════════════════════════

def analyze_ketu_conjunctions(pc: dict) -> list[RahuKetuReading]:
    """Evaluate 2-planet and 3-planet conjunctions with Ketu."""
    readings = []
    _, ketu_sign = get_rahu_ketu_signs(pc)
    if not ketu_sign:
        return readings

    conjunct_planets = [p for p in PLANETS_7 if pc.get("planets", {}).get(p, {}).get("sign") == ketu_sign]

    # 2-Planet conjunctions with Ketu
    for p in conjunct_planets:
        if p in KETU_CONJUNCTIONS:
            cdata = KETU_CONJUNCTIONS[p]
            preds = cdata.get("predictions", [])
            full_text = " ".join(preds)
            severity = "critical" if p in ["Saturn", "Mars", "Jupiter"] else "warning"
            readings.append(RahuKetuReading(
                rule_id=f"RK_CONJ_KETU_{p.upper()}",
                category="ketu_conjunction",
                title=f"Ketu + {p} Conjunction",
                condition_met=True,
                condition_desc=f"{p} is conjunct Ketu in {ketu_sign}.",
                prediction=full_text,
                severity=severity,
                planets_involved=["Ketu", p],
                chapter_ref="Chapters 4 & 5",
            ))

    # 3-Planet conjunctions with Ketu
    if len(conjunct_planets) >= 2:
        for i in range(len(conjunct_planets)):
            for j in range(i + 1, len(conjunct_planets)):
                p1, p2 = conjunct_planets[i], conjunct_planets[j]
                pair_set = {p1, p2}
                for tr in KETU_TRIPLE_CONJUNCTIONS:
                    tr_planets = set(tr.get("planets", []))
                    if "Ketu" in tr_planets and pair_set.issubset(tr_planets):
                        preds = tr.get("predictions", [])
                        pred_str = " ".join(preds)
                        readings.append(RahuKetuReading(
                            rule_id=f"RK_TRIPLE_KETU_{p1.upper()}_{p2.upper()}",
                            category="ketu_triple_conjunction",
                            title=f"Ketu + {p1} + {p2} Triple Conjunction",
                            condition_met=True,
                            condition_desc=f"Ketu, {p1}, and {p2} are conjunct in {ketu_sign}.",
                            prediction=pred_str,
                            severity="critical",
                            planets_involved=["Ketu", p1, p2],
                            chapter_ref="Chapter 5",
                        ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  SECTION 5: KALA SARPA YOGA & DOSHA ANALYSIS
# ══════════════════════════════════════════════════════════════════

def analyze_kala_sarpa(pc: dict) -> list[RahuKetuReading]:
    """Evaluate Kala Sarpa formation, karma causes, and rectification age."""
    readings = []
    ks = check_kala_sarpa(pc)

    if not ks["present"]:
        readings.append(RahuKetuReading(
            rule_id="RK_KALA_SARPA_NONE",
            category="kala_sarpa",
            title="No Kala Sarpa Formation",
            condition_met=False,
            condition_desc="Planets are distributed on both sides of the Rahu-Ketu axis.",
            prediction="Chart is free from Kala Sarpa hemming. Individual planetary energies operate independently.",
            severity="info",
            chapter_ref="Chapters 6, 7, 8",
        ))
        return readings

    rahu_h = ks["rahu_house"]
    ketu_h = ks["ketu_house"]

    # Match specific type
    matched = None
    for kt in KALA_SARPA_TYPES:
        if kt.get("rahu_house") == rahu_h and kt.get("ketu_house") == ketu_h:
            matched = kt
            break

    # Rectification age
    pair_key = (rahu_h, ketu_h) if (rahu_h, ketu_h) in KALA_SARPA_RECTIFICATION_AGES else (ketu_h, rahu_h)
    rect_age = KALA_SARPA_RECTIFICATION_AGES.get(pair_key, 33)

    is_yoga = "yoga" in ks["type"]
    severity = "positive" if is_yoga else "warning"

    karma_desc = matched.get("karma_cause", "") if matched else ""
    pred_text = matched.get("prediction", "") if matched else ""

    full_pred = f"Formation: {ks['name']}. "
    if karma_desc:
        full_pred += f"Past Life Karmic Origin: {karma_desc}. "
    if pred_text:
        full_pred += f"Manifestation: {pred_text} "
    if is_yoga:
        full_pred += "Note: Kala Sarpa Yoga confers 75% Yoga and 25% distress, manifesting its full upliftment after age 33."
    else:
        full_pred += f"Note: Natural rectification occurs around age {rect_age}."

    if ks.get("separated_planet"):
        sep = ks["separated_planet"]
        full_pred += f" ARDH KALA SARPA: {sep} sits outside the axis — the significations and relative of {sep} experience complete separation/alienation."

    readings.append(RahuKetuReading(
        rule_id="RK_KALA_SARPA_ACTIVE",
        category="kala_sarpa",
        title=ks["name"],
        condition_met=True,
        condition_desc=f"Axis across House {rahu_h} (Rahu) and House {ketu_h} (Ketu). Hemming: {ks['type']}.",
        prediction=full_pred,
        severity=severity,
        planets_involved=PLANETS,
        houses_involved=[rahu_h, ketu_h],
        chapter_ref="Chapters 6, 7, 8",
        modifiers=[f"Rectification Age: {rect_age}", f"Type: {ks['type']}"],
    ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  SECTION 6: SPECIAL NADI PRINCIPLES
# ══════════════════════════════════════════════════════════════════

def analyze_special_nadi(pc: dict) -> list[RahuKetuReading]:
    """Evaluate unique Nadi techniques for Rahu and Ketu."""
    readings = []

    # 1. Sarpa Chandra (Ambuli) Point (Chapter 44)
    amb_abs, amb_sign, amb_deg = compute_sarpa_chandra_point(pc)
    afflicted_planets = []
    for p in PLANETS_7:
        p_abs = get_planet_abs_degree(pc, p)
        if abs(p_abs - amb_abs) <= 2.0 or abs(p_abs - amb_abs) >= 358.0:
            afflicted_planets.append(p)

    amb_desc = f"Sarpa Chandra (Ambuli) Point calculated at {amb_deg:.2f}° in {amb_sign} (total {amb_abs:.2f}°)."
    if afflicted_planets:
        readings.append(RahuKetuReading(
            rule_id="RK_NADI_AMBULI_POINT",
            category="special_nadi",
            title="Sarpa Chandra (Ambuli) Point Affliction",
            condition_met=True,
            condition_desc=f"{', '.join(afflicted_planets)} is situated within ±2° of the Ambuli Point.",
            prediction=f"Planets on this degree ({', '.join(afflicted_planets)}) suffer severe paralysis of significations. Transits over this point trigger intense karmic turning points.",
            severity="critical",
            planets_involved=afflicted_planets,
            chapter_ref="Chapter 44",
        ))
    else:
        readings.append(RahuKetuReading(
            rule_id="RK_NADI_AMBULI_POINT",
            category="special_nadi",
            title="Sarpa Chandra (Ambuli) Point",
            condition_met=True,
            condition_desc=amb_desc,
            prediction=f"The karmic sensitive degree falls in {amb_sign} at {amb_deg:.2f}°. No natal planets are combusted on this exact degree.",
            severity="info",
            chapter_ref="Chapter 44",
        ))

    # 2. Shadow Planet Punarphoo (Chapter 53)
    if check_shadow_punarphoo(pc):
        readings.append(RahuKetuReading(
            rule_id="RK_NADI_SHADOW_PUNARPHOO",
            category="special_nadi",
            title="Shadow Planet Punarphoo Active",
            condition_met=True,
            condition_desc="Rahu's dispositor and Ketu's dispositor are conjunct, in opposition, or in mutual reception.",
            prediction="Strong romantic attraction and harmony before marriage, but creates intense friction, misunderstanding, or separation within 30 days to a few years after marriage.",
            severity="warning",
            chapter_ref="Chapter 53",
            remedies=["Cultivate emotional patience; avoid exposing private marital arguments to in-laws or third parties."],
        ))

    # 3. Dubious Character & Marital Suspicion (Chapter 21)
    mars_h = pc.get("planets", {}).get("Mars", {}).get("house", 0)
    venus_h = pc.get("planets", {}).get("Venus", {}).get("house", 0)
    mars_sign = pc.get("planets", {}).get("Mars", {}).get("sign", "")
    venus_sign = pc.get("planets", {}).get("Venus", {}).get("sign", "")
    rahu_sign, ketu_sign = get_rahu_ketu_signs(pc)

    dubious_triggered = False
    dubious_reasons = []

    if mars_h == 3:
        dubious_triggered = True
        dubious_reasons.append("Mars in 3rd House")
    if venus_h == 3:
        dubious_triggered = True
        dubious_reasons.append("Venus in 3rd House")
    if mars_sign and (planet_controls_sign(rahu_sign, mars_sign) or planet_controls_sign(ketu_sign, mars_sign)):
        dubious_triggered = True
        dubious_reasons.append("Nodes in 3rd/11th from Mars")
    if venus_sign and (planet_controls_sign(rahu_sign, venus_sign) or planet_controls_sign(ketu_sign, venus_sign)):
        dubious_triggered = True
        dubious_reasons.append("Nodes in 3rd/11th from Venus")

    if dubious_triggered:
        readings.append(RahuKetuReading(
            rule_id="RK_NADI_DUBIOUS_SUSPICION",
            category="special_nadi",
            title="Marital Suspicion Indicator (Dubious Character Rule)",
            condition_met=True,
            condition_desc="; ".join(dubious_reasons),
            prediction="Creates perpetual suspicion, lack of trust, and imaginary fears between partners, disrupting domestic peace.",
            severity="caution",
            planets_involved=["Mars", "Venus", "Rahu", "Ketu"],
            chapter_ref="Chapter 21",
        ))

    # 4. Critical Midpoint of Rahu-Ketu Axis (Chapter 51)
    mid1, mid2 = compute_rahu_ketu_midpoint(pc)
    mid_planets = [p for p in PLANETS_7 if pc.get("planets", {}).get(p, {}).get("sign") in [mid1, mid2]]
    if mid_planets:
        readings.append(RahuKetuReading(
            rule_id="RK_NADI_AXIS_MIDPOINT",
            category="special_nadi",
            title="Planets on Rahu-Ketu Axis Midpoint",
            condition_met=True,
            condition_desc=f"{', '.join(mid_planets)} situated in square signs to Nodes ({mid1} / {mid2}).",
            prediction=f"Planets in the square midpoint signs ({', '.join(mid_planets)}) deliver 25% to 75% life-transforming karmic events during their periods.",
            severity="info",
            planets_involved=mid_planets,
            chapter_ref="Chapter 51",
        ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  SECTION 7: PROGENY ANALYSIS (PUTHRA DOSHA & SOGAM)
# ══════════════════════════════════════════════════════════════════

def analyze_progeny(pc: dict) -> list[RahuKetuReading]:
    """Evaluate Puthra Dosha vs Puthra Sogam and fertility rules."""
    readings = []
    jup_sign = pc.get("planets", {}).get("Jupiter", {}).get("sign", "")
    mars_sign = pc.get("planets", {}).get("Mars", {}).get("sign", "")
    sun_sign = pc.get("planets", {}).get("Sun", {}).get("sign", "")
    sat_sign = pc.get("planets", {}).get("Saturn", {}).get("sign", "")
    rahu_sign, ketu_sign = get_rahu_ketu_signs(pc)

    # 1. Jupiter with Rahu/Ketu (Puthra Dosha)
    if jup_sign in [rahu_sign, ketu_sign]:
        node = "Rahu" if jup_sign == rahu_sign else "Ketu"
        readings.append(RahuKetuReading(
            rule_id="RK_PROGENY_PUTHRA_DOSHA",
            category="progeny",
            title=f"Puthra Dosha: Jupiter Conjunct {node}",
            condition_met=True,
            condition_desc=f"Puthrakaraka Jupiter is conjunct {node} in {jup_sign}.",
            prediction="Significant delay or obstruction in progeny; prime indicator for IVF/assisted reproductive treatments. Children require protective care in early childhood.",
            severity="warning",
            planets_involved=["Jupiter", node],
            chapter_ref="Chapters 23, 24, 32",
            remedies=["Worship Lord Ganesha or Naga Devatha; sponsor education of underprivileged children."],
        ))

    # 2. Mars with Rahu/Ketu (Puthra Sogam)
    if mars_sign in [rahu_sign, ketu_sign]:
        node = "Rahu" if mars_sign == rahu_sign else "Ketu"
        readings.append(RahuKetuReading(
            rule_id="RK_PROGENY_PUTHRA_SOGAM",
            category="progeny",
            title=f"Puthra Sogam: Mars Conjunct {node}",
            condition_met=True,
            condition_desc=f"Mars is conjunct {node} in {mars_sign}.",
            prediction="Native is blessed with children but experiences emotional agony or worry concerning their temperament, physical health, or relationship distance.",
            severity="caution",
            planets_involved=["Mars", node],
            chapter_ref="Chapter 25",
        ))

    # 3. Nodes in 5th from Sun or Saturn
    if sun_sign and rahu_sign and sun_sign in SIGNS and rahu_sign in SIGNS:
        s_i = SIGNS.index(sun_sign)
        r_i = SIGNS.index(rahu_sign)
        k_i = SIGNS.index(ketu_sign)
        if (r_i - s_i) % 12 + 1 == 5 or (k_i - s_i) % 12 + 1 == 5:
            readings.append(RahuKetuReading(
                rule_id="RK_PROGENY_5TH_FROM_SUN",
                category="progeny",
                title="Node in 5th House from Sun",
                condition_met=True,
                condition_desc="Rahu or Ketu occupies the 5th sign from natal Sun.",
                prediction="Ancestral descent and paternal lineage continuity encounter delays and require specific ancestral remedies.",
                severity="caution",
                planets_involved=["Sun", "Rahu" if (r_i - s_i) % 12 + 1 == 5 else "Ketu"],
                chapter_ref="Chapter 26",
            ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  SECTION 8: MEDICAL ASTROLOGY (DISEASES & ACCIDENTS)
# ══════════════════════════════════════════════════════════════════

def analyze_medical(pc: dict) -> list[RahuKetuReading]:
    """Evaluate health vulnerabilities, PCOD, accident triad, and surgery rules."""
    readings = []
    rahu_sign, ketu_sign = get_rahu_ketu_signs(pc)

    # 1. Scorpio Node Placement (PCOD/Reproductive/Rectal)
    if "Scorpio" in [rahu_sign, ketu_sign]:
        node = "Rahu" if rahu_sign == "Scorpio" else "Ketu"
        readings.append(RahuKetuReading(
            rule_id="RK_MED_SCORPIO_NODE",
            category="medical",
            title=f"{node} in Scorpio — Deep Pelvic / Reproductive Sensitivity",
            condition_met=True,
            condition_desc=f"{node} occupies Scorpio (Virulent sign).",
            prediction="High vulnerability to chronic pelvic/uterine complications, PCOD/fibroids (in females), rectal disorders, or hidden infections.",
            severity="warning",
            planets_involved=[node],
            chapter_ref="Chapters 30, 31",
        ))

    # 2. Conjunction-based Medical Rules
    for mrule in MEDICAL_RULES:
        req_planets = mrule.get("planets", [])
        if not req_planets:
            continue

        # Handle '8thLord' special key
        actual_planets = []
        skip = False
        for p in req_planets:
            if p == "8thLord":
                lagna = pc.get("meta", {}).get("lagna_sign", "")
                if lagna:
                    h8_sign = house_sign(8, lagna)
                    h8_lord = SIGN_LORDS.get(h8_sign, "")
                    if h8_lord:
                        actual_planets.append(h8_lord)
                    else:
                        skip = True
                else:
                    skip = True
            else:
                actual_planets.append(p)

        if skip:
            continue

        # Check if all actual_planets share the same sign
        signs = [pc.get("planets", {}).get(p, {}).get("sign", "") for p in actual_planets]
        if all(signs) and len(set(signs)) == 1:
            diseases = mrule.get("diseases", [])
            d_text = ", ".join(diseases)
            readings.append(RahuKetuReading(
                rule_id=f"RK_MED_{'_'.join(actual_planets).upper()}",
                category="medical",
                title=f"Medical Combination: {' + '.join(actual_planets)}",
                condition_met=True,
                condition_desc=f"{' + '.join(actual_planets)} are conjunct in {signs[0]}.",
                prediction=f"Health vulnerabilities indicated: {d_text}.",
                severity="warning",
                planets_involved=actual_planets,
                chapter_ref="Chapter 30",
            ))

    # 3. Accident Triad (Mars + Saturn + Nodes in 3rd/11th)
    mars_sign = pc.get("planets", {}).get("Mars", {}).get("sign", "")
    sat_sign = pc.get("planets", {}).get("Saturn", {}).get("sign", "")
    if mars_sign and sat_sign and mars_sign in SIGNS and sat_sign in SIGNS:
        m_i = SIGNS.index(mars_sign)
        s_i = SIGNS.index(sat_sign)
        # Mars and Saturn conjunct or in opposition
        if m_i == s_i or (m_i - s_i) % 12 == 6:
            # Check if Rahu or Ketu in 3rd or 11th from Mars/Saturn
            if planet_controls_sign(rahu_sign, mars_sign) or planet_controls_sign(ketu_sign, mars_sign):
                readings.append(RahuKetuReading(
                    rule_id="RK_MED_ACCIDENT_TRIAD",
                    category="medical",
                    title="Accident & Injury Triad Active",
                    condition_met=True,
                    condition_desc="Mars-Saturn aspect/conjunction linked with Rahu/Ketu control.",
                    prediction="High risk of bone fractures, vehicle collisions, or surgical procedures. Exercise extreme caution in driving and hazardous work.",
                    severity="critical",
                    planets_involved=["Mars", "Saturn", "Rahu", "Ketu"],
                    chapter_ref="Chapters 48 & 50",
                ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  SECTION 9: DASHA-BHUKTI & KARMIC TIMING
# ══════════════════════════════════════════════════════════════════

def analyze_dasha_timing(pc: dict) -> list[RahuKetuReading]:
    """Evaluate Dasha-Bhukti effects, perilous periods, and karma exposure ages."""
    readings = []
    dasha, bhukti = get_current_dasha_bhukti(pc)

    # 1. Perilous Dasha-Bhukti Check
    if dasha and bhukti and is_perilous_period(dasha, bhukti):
        readings.append(RahuKetuReading(
            rule_id="RK_DASHA_PERILOUS",
            category="dasha_timing",
            title=f"Perilous Dasha Period: {dasha} MD / {bhukti} AD",
            condition_met=True,
            condition_desc=f"Current running period is {dasha} Dasha and {bhukti} Bhukti.",
            prediction="Belongs to the 12 perilous nodal periods (Chapter 40). Requires utmost caution in financial investments, partnerships, legal documents, and health.",
            severity="critical",
            planets_involved=[dasha, bhukti],
            chapter_ref="Chapter 40",
            remedies=["Perform weekly archana to Lord Ganesha / Durga; avoid taking large uncollateralized loans."],
        ))

    # 2. Karma Exposure Age Formula (Chapter 9)
    jup_sign = pc.get("planets", {}).get("Jupiter", {}).get("sign", "")
    ketu_sign = pc.get("planets", {}).get("Ketu", {}).get("sign", "")
    sat_sign = pc.get("planets", {}).get("Saturn", {}).get("sign", "")
    rahu_sign = pc.get("planets", {}).get("Rahu", {}).get("sign", "")

    if jup_sign in SIGNS and ketu_sign in SIGNS:
        j_i = SIGNS.index(jup_sign)
        k_i = SIGNS.index(ketu_sign)
        jk_diff = (k_i - j_i) % 12
        jk_map = KARMA_EXPOSURE_AGES.get("jupiter_ketu_distance", {})
        age_range_jk = jk_map.get(jk_diff, "24 to 36 years")

        readings.append(RahuKetuReading(
            rule_id="RK_KARMA_EXPOSURE_JUPITER_KETU",
            category="dasha_timing",
            title=f"Karmic Exposure Age: Jupiter-Ketu Cycle ({age_range_jk})",
            condition_met=True,
            condition_desc=f"Distance between Jupiter ({jup_sign}) and Ketu ({ketu_sign}) is {jk_diff} signs.",
            prediction=f"Karmic lessons and major life transformations trigger predominantly during ages {age_range_jk}.",
            severity="info",
            planets_involved=["Jupiter", "Ketu"],
            chapter_ref="Chapter 9",
            modifiers=[f"Age Window: {age_range_jk}"],
        ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  SECTION 10: SHADOW YOGAS (SAYA YOGA & MAHA SAKTHI YOGA)
# ══════════════════════════════════════════════════════════════════

def analyze_yogas(pc: dict) -> list[RahuKetuReading]:
    """Evaluate Saya Yoga, Maha Sakthi Yoga, and Dhana Yogas."""
    readings = []
    rahu_house, _ = get_rahu_ketu_houses(pc)
    rahu_sign, ketu_sign = get_rahu_ketu_signs(pc)
    lagna_sign = pc.get("meta", {}).get("lagna_sign", "")
    sun_sign = pc.get("planets", {}).get("Sun", {}).get("sign", "")
    moon_sign = pc.get("planets", {}).get("Moon", {}).get("sign", "")

    # 1. Saya Yoga (Chapters 58 & 59)
    if rahu_house in SAYA_YOGA:
        sdata = SAYA_YOGA[rahu_house]
        kl_lord = sdata.get("kalapurusha_lord", "")
        s_pred = sdata.get("prediction", "")
        readings.append(RahuKetuReading(
            rule_id=f"RK_YOGA_SAYA_H{rahu_house}",
            category="yoga",
            title=f"Saya Yoga via House {rahu_house} (Kalapurusha {kl_lord})",
            condition_met=True,
            condition_desc=f"Rahu occupies House {rahu_house}, channeling the portfolio of Kalapurusha lord {kl_lord}.",
            prediction=f"Saya Yoga directs extraordinary career success and public influence through {kl_lord} domains: {s_pred}.",
            severity="positive",
            planets_involved=["Rahu", kl_lord],
            houses_involved=[rahu_house],
            chapter_ref="Chapters 58 & 59",
        ))

    # 2. Maha Sakthi Yoga (Chapter 55)
    factors = 0
    f_desc = []
    if lagna_sign in [rahu_sign, ketu_sign]:
        factors += 1
        f_desc.append("Lagna with Node")
    if moon_sign in [rahu_sign, ketu_sign]:
        factors += 1
        f_desc.append("Moon with Node")
    if sun_sign in [rahu_sign, ketu_sign]:
        factors += 1
        f_desc.append("Sun with Node")

    if factors > 0:
        pct = 33 if factors == 1 else 66 if factors == 2 else 100
        readings.append(RahuKetuReading(
            rule_id="RK_YOGA_MAHA_SAKTHI",
            category="yoga",
            title=f"Maha Sakthi Yoga ({pct}% Potency)",
            condition_met=True,
            condition_desc=f"{factors}/3 Key Ascendant factors conjoined with Nodes ({', '.join(f_desc)}).",
            prediction="Destroys complacency in personal/domestic life, but confers immense, magnetic leadership and world renown if channelled into selfless public or spiritual service.",
            severity="positive",
            planets_involved=["Sun", "Moon", "Rahu", "Ketu"],
            chapter_ref="Chapter 55",
            modifiers=[f"Potency: {pct}%"],
        ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  SECTION 11: ANCESTRAL CURSES (POORVIKA DOSHA)
# ══════════════════════════════════════════════════════════════════

def analyze_poorvika_dosha(pc: dict) -> list[RahuKetuReading]:
    """Evaluate paternal and maternal Poorvika Dosha configurations."""
    readings = []

    # Paternal Poorvika Dosha
    paternal_combos = POORVIKA_DOSHA.get("paternal", [])
    p_fired = []
    for combo in paternal_combos:
        planets_in_combo = combo.split("+")
        signs = [pc.get("planets", {}).get(p, {}).get("sign", "") for p in planets_in_combo]
        if all(signs) and len(set(signs)) == 1:
            p_fired.append(combo)

    if p_fired:
        manif = POORVIKA_DOSHA.get("manifestation", {}).get("paternal", "")
        readings.append(RahuKetuReading(
            rule_id="RK_POORVIKA_PATERNAL",
            category="poorvika_dosha",
            title=f"Paternal Poorvika Dosha ({', '.join(p_fired)})",
            condition_met=True,
            condition_desc=f"Paternal ancestral affliction present via {', '.join(p_fired)}.",
            prediction=f"Manifestation: {manif}",
            severity="warning",
            chapter_ref="Chapter 13",
            remedies=["Perform annual ancestral Shraddha/Tarpana diligently; revitalize worship of Kula Deivatham (family deity)."],
        ))

    # Maternal Poorvika Dosha
    maternal_combos = POORVIKA_DOSHA.get("maternal", [])
    m_fired = []
    for combo in maternal_combos:
        planets_in_combo = combo.split("+")
        signs = [pc.get("planets", {}).get(p, {}).get("sign", "") for p in planets_in_combo]
        if all(signs) and len(set(signs)) == 1:
            m_fired.append(combo)

    if m_fired:
        manif = POORVIKA_DOSHA.get("manifestation", {}).get("maternal", "")
        readings.append(RahuKetuReading(
            rule_id="RK_POORVIKA_MATERNAL",
            category="poorvika_dosha",
            title=f"Maternal Poorvika Dosha ({', '.join(m_fired)})",
            condition_met=True,
            condition_desc=f"Maternal ancestral affliction present via {', '.join(m_fired)}.",
            prediction=f"Manifestation: {manif}",
            severity="warning",
            chapter_ref="Chapter 13",
            remedies=["Worship Goddess Shakthi / Ambal; offer food and charity to elderly women."],
        ))

    return readings


# ══════════════════════════════════════════════════════════════════
#  SECTION 12: REMEDIAL MEASURES
# ══════════════════════════════════════════════════════════════════

def analyze_remedies(pc: dict, all_readings: list[RahuKetuReading]) -> list[str]:
    """Consolidate specific remedies based on fired chart afflictions."""
    remedy_set = []

    # Check for general Sarpa Dosha
    has_sarpa = any(r.rule_id == "RK_KALA_SARPA_ACTIVE" for r in all_readings)
    if has_sarpa:
        remedy_set.append("Pilgrimage to Thirunageswaram (Tamil Nadu) and Srikalahasti (Andhra Pradesh) to appease Rahu and Ketu.")

    rahu_sign, ketu_sign = get_rahu_ketu_signs(pc)
    for p in PLANETS_7:
        p_sign = pc.get("planets", {}).get(p, {}).get("sign", "")
        if p_sign in [rahu_sign, ketu_sign]:
            for r in REMEDIES:
                cond = r.get("condition", "")
                if f"{p}+" in cond or f"+{p}" in cond:
                    rem_text = f"For {p} conjunct Node: {r.get('remedy', '')}"
                    if rem_text not in remedy_set:
                        remedy_set.append(rem_text)

    return remedy_set


# ══════════════════════════════════════════════════════════════════
#  MASTER ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════

def analyze_rahu_ketu(pc: dict, *, gender: str = "male") -> dict:
    """
    Master entry point for Rahu & Ketu: The Life Changing Planets analysis.
    Takes a precomputed chart dict (from compute_chart) and returns a complete evaluation.
    """
    rahu_sign, ketu_sign = get_rahu_ketu_signs(pc)
    rahu_house, ketu_house = get_rahu_ketu_houses(pc)

    sign_readings = analyze_sign_placement(pc)
    house_readings = analyze_house_placement(pc)
    rahu_conj = analyze_rahu_conjunctions(pc)
    ketu_conj = analyze_ketu_conjunctions(pc)
    kala_sarpa = analyze_kala_sarpa(pc)
    special_nadi = analyze_special_nadi(pc)
    progeny = analyze_progeny(pc)
    medical = analyze_medical(pc)
    dasha_readings = analyze_dasha_timing(pc)
    yogas = analyze_yogas(pc)
    poorvika = analyze_poorvika_dosha(pc)

    all_readings = (
        sign_readings
        + house_readings
        + rahu_conj
        + ketu_conj
        + kala_sarpa
        + special_nadi
        + progeny
        + medical
        + dasha_readings
        + yogas
        + poorvika
    )

    remedies = analyze_remedies(pc, all_readings)
    fired_readings = [r for r in all_readings if r.condition_met]
    critical_alerts = [r.title for r in fired_readings if r.severity == "critical"]
    positive_indicators = [r.title for r in fired_readings if r.severity == "positive"]

    client_name = pc.get("meta", {}).get("client", "Native")
    dob = pc.get("meta", {}).get("dob", "")

    return {
        "meta": {
            "client": client_name,
            "dob": dob,
            "rahu_sign": rahu_sign,
            "rahu_house": rahu_house,
            "ketu_sign": ketu_sign,
            "ketu_house": ketu_house,
            "gender": gender,
        },
        "sign_readings": sign_readings,
        "house_readings": house_readings,
        "rahu_conjunction_readings": rahu_conj,
        "ketu_conjunction_readings": ketu_conj,
        "kala_sarpa_readings": kala_sarpa,
        "special_nadi_readings": special_nadi,
        "progeny_readings": progeny,
        "medical_readings": medical,
        "dasha_readings": dasha_readings,
        "yoga_readings": yogas,
        "poorvika_readings": poorvika,
        "remedies": remedies,
        "all_readings": all_readings,
        "summary": {
            "total_rules_evaluated": len(all_readings),
            "rules_fired": len(fired_readings),
            "critical_alerts": critical_alerts,
            "positive_indicators": positive_indicators,
        },
    }


if __name__ == "__main__":
    from astro_chart_bridge import compute_chart

    pc = compute_chart(client_name="Test", dob="1989-07-29", birth_time="00:05", place="Patna, India")
    result = analyze_rahu_ketu(pc, gender="male")
    print(f"Total rules evaluated: {result['summary']['total_rules_evaluated']}")
    print(f"Rules fired: {result['summary']['rules_fired']}")
    print(f"Rahu: {result['meta']['rahu_sign']} (House {result['meta']['rahu_house']})")
    print(f"Ketu: {result['meta']['ketu_sign']} (House {result['meta']['ketu_house']})")
    print("\n=== FIRED RULES ===")
    for r in result["all_readings"]:
        if r.condition_met:
            print(f"  [{r.severity:8s}] {r.rule_id}: {r.title}")
            print(f"            -> {r.prediction[:90]}...")
