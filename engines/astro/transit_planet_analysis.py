#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
transit_planet_analysis.py — Planetary Transit Matrix Analysis Engine

Implements the complete real-time transit methodology and timing matrix.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

import swisseph as swe

from astro_precompute import (
    NAKSHATRAS,
    SIGNS,
    SIGN_LORDS,
    VIMSH_LORDS,
    VIMSH_YEARS,
    build_vimshottari_from_moon,
    degree_to_nakshatra,
    get_dignity,
    house_from_lagna,
    sign_index,
)
from transit_planet_book_data import (
    FOUNDATIONAL_PRINCIPLES,
    TRANSIT_JUPITER_OVER_NATAL,
    TRANSIT_KETU_OVER_NATAL,
    TRANSIT_MARS_OVER_NATAL,
    TRANSIT_MERCURY_OVER_NATAL,
    TRANSIT_MOON_OVER_NATAL,
    TRANSIT_RAHU_OVER_NATAL,
    TRANSIT_SATURN_OVER_NATAL,
    TRANSIT_SUN_OVER_NATAL,
    TRANSIT_VENUS_OVER_NATAL,
)

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

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


@dataclass
class GroupedTransitCard:
    transit_planet: str
    transit_sign: str
    transit_degree: float
    house: int
    natal_planets: list[str]
    phase_assessment: str          # "Highly Auspicious" | "Favorable" | "Mixed" | "Challenging / Sensitive"
    assessment_badge: str         # "positive" | "info" | "warning" | "critical"
    synthesis_prediction: str
    next_phase_prediction: str
    preventive_action: str
    ease_date: str
    is_dasha_active: bool = False


def find_sign_exit_date(planet_id: int, start_dt: datetime, current_sign_idx: int) -> str:
    """Calculates exact date when a planet exits its current zodiac sign."""
    try:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        dt = start_dt
        for days in range(1, 3650):
            t = dt + timedelta(days=days)
            jd = swe.julday(t.year, t.month, t.day, t.hour + t.minute / 60.0)
            pos, _ = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL)
            s_idx = int(pos[0] // 30) % 12
            if s_idx != current_sign_idx:
                return t.strftime("%d %b %Y")
        return "N/A"
    except Exception:
        return "N/A"


def find_moon_exit_time(start_dt: datetime, current_sign_idx: int) -> str:
    """Calculates exact date/time when Moon exits its current zodiac sign."""
    try:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        dt = start_dt
        for hours in range(1, 100):
            t = dt + timedelta(hours=hours)
            jd = swe.julday(t.year, t.month, t.day, t.hour + t.minute / 60.0)
            pos, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)
            s_idx = int(pos[0] // 30) % 12
            if s_idx != current_sign_idx:
                return t.strftime("%d %b %Y (%I:%M %p)")
        return "within 48 hours"
    except Exception:
        return "within 48 hours"


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
            res[p_name] = {"sign": sign, "degree": degree, "abs_degree": lon, "sign_idx": sign_idx}

            if p_name == "Rahu":
                k_lon = (lon + 180) % 360
                k_sign_idx = int(k_lon // 30) % 12
                k_sign = SIGNS[k_sign_idx]
                res["Ketu"] = {"sign": k_sign, "degree": k_lon % 30, "abs_degree": k_lon, "sign_idx": k_sign_idx}
        return res
    except Exception:
        return {}


def analyze_transit_planet(
    pc: dict,
    *,
    analysis_datetime: datetime | None = None,
    gender: str = "male",
) -> dict:
    """
    Master analysis function for Transit of Planets system.
    Evaluates current real-time transits contacting natal planets with explicit
    good/bad assessments and preventive guidance.
    """
    if analysis_datetime is None:
        analysis_datetime = datetime.now()

    transit = get_transit_positions(analysis_datetime)
    lagna = pc.get("meta", {}).get("lagna_sign", "")
    dob_str = pc.get("meta", {}).get("dob", "1990-01-01")

    # Compute Vimshottari Dasha accurately
    moon_data = pc.get("planets", {}).get("Moon", {})
    moon_sign = moon_data.get("sign", "Aries")
    moon_deg_in_sign = moon_data.get("degree_in_sign", 0.0)
    moon_nak = moon_data.get("nakshatra", "")
    moon_deg_in_nak = moon_data.get("degree_in_nakshatra", 0.0)

    if not moon_nak or moon_deg_in_nak == 0.0:
        sign_idx = SIGNS.index(moon_sign) if moon_sign in SIGNS else 0
        moon_abs = sign_idx * 30.0 + moon_deg_in_sign
        nak_info = degree_to_nakshatra(moon_abs)
        moon_nak = nak_info["nakshatra"]
        moon_deg_in_nak = moon_abs % (360.0 / 27.0)

    dob_date = datetime.strptime(dob_str, "%Y-%m-%d").date()
    vim = build_vimshottari_from_moon(moon_nak, moon_deg_in_nak, dob_date)
    curr_md = vim.get("current_md", {})
    curr_ad = next((a for a in vim.get("current_md_antardashas", []) if a["status"] == "current"), {})
    next_ad = next((a for a in vim.get("current_md_antardashas", []) if a["status"] == "future"), {})

    active_dasha_lords = {curr_md.get("md_lord"), curr_ad.get("ad_lord")}

    MATRIX_MAP = {
        "Sun": TRANSIT_SUN_OVER_NATAL,
        "Mars": TRANSIT_MARS_OVER_NATAL,
        "Jupiter": TRANSIT_JUPITER_OVER_NATAL,
        "Saturn": TRANSIT_SATURN_OVER_NATAL,
        "Rahu": TRANSIT_RAHU_OVER_NATAL,
        "Ketu": TRANSIT_KETU_OVER_NATAL,
    }

    cards: list[GroupedTransitCard] = []

    for t_p, t_data in transit.items():
        t_sign = t_data.get("sign")
        t_s_idx = t_data.get("sign_idx", 0)
        t_deg = t_data.get("degree", 0.0)

        # Compute exit date
        if t_p == "Moon":
            ease_date = find_moon_exit_time(analysis_datetime, t_s_idx)
        elif t_p in SWE_PLANETS:
            ease_date = find_sign_exit_date(SWE_PLANETS[t_p], analysis_datetime, t_s_idx)
        elif t_p == "Ketu":
            ease_date = find_sign_exit_date(swe.MEAN_NODE, analysis_datetime, t_s_idx)
        else:
            ease_date = "N/A"

        # Correct whole-sign house from Lagna: (t_sign from lagna)
        h_num = house_from_lagna(t_sign, lagna) if lagna else 1

        # Check which natal planets occupy this sign
        conjunct_natal = [p for p, d in pc.get("planets", {}).items() if d.get("sign") == t_sign]
        if not conjunct_natal:
            continue

        is_dasha = (t_p in active_dasha_lords) or any(p in active_dasha_lords for p in conjunct_natal)

        # Consolidate predictions for all conjunct natal planets
        pred_parts = []
        has_warning = False
        has_positive = False

        for n_p in conjunct_natal:
            if t_p in MATRIX_MAP:
                r_entry = MATRIX_MAP[t_p].get(n_p, {})
                pred_parts.append(f"<b>Over Natal {n_p}:</b> {r_entry.get('prediction', '')}")
                if r_entry.get("severity") in ["warning", "critical", "caution"]:
                    has_warning = True
                if r_entry.get("severity") == "positive":
                    has_positive = True
            elif t_p == "Moon":
                pred_parts.append(f"<b>Over Natal {n_p}:</b> {TRANSIT_MOON_OVER_NATAL.get(n_p, '')}")
            elif t_p == "Mercury":
                pred_parts.append(f"<b>Over Natal {n_p}:</b> {TRANSIT_MERCURY_OVER_NATAL.get(n_p, '')}")
            elif t_p == "Venus":
                pred_parts.append(f"<b>Over Natal {n_p}:</b> {TRANSIT_VENUS_OVER_NATAL.get(n_p, '')}")
                has_positive = True

        synthesis_text = " ".join(pred_parts)

        # Determine Phase Assessment & Preventive Action
        if t_p == "Saturn":
            if "Venus" in conjunct_natal or "Mercury" in conjunct_natal:
                phase_assessment = "Constructive but Demanding (Mixed-Positive)"
                badge = "warning"
                next_pred = "When Saturn departs this sign, professional systems stabilize and accumulated financial/structural rewards become permanent."
                preventive = "Avoid speculative uncollateralized investments; strictly verify legal and accounting clauses in all partnership contracts; maintain patience with authorities."
            else:
                phase_assessment = "Challenging / Heavy Testing"
                badge = "warning"
                next_pred = "Transition into the next sign releases mental pressure and removes long-standing professional bottlenecks."
                preventive = "Perform disciplined service, avoid taking hasty loans, and protect bone/joint health through regular physical discipline."
        elif t_p in ["Rahu", "Ketu"]:
            phase_assessment = "Sensitive / Karmic Calibration"
            badge = "warning"
            next_pred = "The upcoming Nodal shift permanently lifts the current area of friction and directs focus toward fresh evolutionary opportunities."
            preventive = "Maintain absolute transparency in finances; avoid illusionary high-return schemes; schedule routine health checkups for the signified organs."
        elif t_p == "Mars":
            if h_num in [6, 8, 12] or "Saturn" in conjunct_natal or "Rahu" in conjunct_natal:
                phase_assessment = "High-Energy / Accident-Sensitive"
                badge = "warning"
                next_pred = "When Mars enters the next sign, physical strain dissolves and domestic harmony returns to baseline."
                preventive = "Exercise conscious control over anger and sharp speech with family; drive carefully; avoid aggressive confrontations."
            else:
                phase_assessment = "Dynamic & Favorable"
                badge = "positive"
                next_pred = "Energy remains productive, laying solid groundwork for upcoming ventures."
                preventive = "Channel excess physical energy into productive technical/property works rather than debates."
        elif t_p in ["Jupiter", "Venus"]:
            phase_assessment = "Highly Auspicious / Favorable"
            badge = "positive"
            next_pred = "Momentum continues to expand into domestic celebrations, material gains, and emotional contentment."
            preventive = "Maximize this auspicious window by finalizing negotiations, expanding networks, and undertaking auspicious initiatives."
        else:
            phase_assessment = "Active Fast-Moving Phase"
            badge = "info"
            next_pred = "The brief decision surge eases smoothly as the planet moves into the subsequent sign."
            preventive = "Stay focused on essential daily priorities; defer impulsive non-essential decisions until the transit settles."

        cards.append(GroupedTransitCard(
            transit_planet=t_p,
            transit_sign=t_sign,
            transit_degree=t_deg,
            house=h_num,
            natal_planets=conjunct_natal,
            phase_assessment=phase_assessment,
            assessment_badge=badge,
            synthesis_prediction=synthesis_text,
            next_phase_prediction=next_pred,
            preventive_action=preventive,
            ease_date=ease_date,
            is_dasha_active=is_dasha,
        ))

    return {
        "meta": {
            "client": pc.get("meta", {}).get("client", "Client"),
            "dob": dob_str,
            "gender": gender,
            "lagna": lagna,
            "analysis_datetime": str(analysis_datetime),
        },
        "transit_snapshot": transit,
        "dasha_info": {
            "current_md": curr_md,
            "current_ad": curr_ad,
            "next_ad": next_ad,
        },
        "cards": cards,
    }
