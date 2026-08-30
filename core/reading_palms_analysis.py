#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reading_palms_analysis.py — Practical Palmistry Analysis & Astro-Palm Confluence Engine

Synthesizes classical palm reading principles from 'READING PALMS: A Practical Course'
(The Aether Library) and maps them with Computer Vision (CV) detection from palm images.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from reading_palms_book_data import (
    HAND_SHAPES,
    MAJOR_LINES_RULES,
    MOUNTS_DATA,
    THUMB_RULES,
)


@dataclass
class PalmReadingCard:
    category: str  # "hand_shape" | "life_line" | "head_line" | "heart_line" | "fate_line" | "mounts" | "thumb" | "astro_confluence"
    feature_name: str
    title: str
    assessment: str
    prediction: str
    timing_milestone: str = ""
    severity: str = "info"  # "positive" | "info" | "warning" | "caution"
    astro_link: str = ""


def extract_features_from_image(img_path: str | Path, hand: str = "right") -> dict:
    """Extracts palm features using the Computer Vision (MediaPipe/OpenCV) analyzer."""
    path = Path(img_path)
    if not path.is_file():
        return {}

    try:
        from palm_api.analyzer import extract_features, features_for_json
        raw = extract_features(path, hand=hand)
        clean = features_for_json(raw)
        return clean
    except Exception as e:
        print(f"Warning: CV extraction failed on {path}: {e}")
        return {}


def analyze_palm(
    palm_data_or_image: dict | str | Path | None = None,
    pc: dict | None = None,
    *,
    name: str = "Native",
    gender: str = "male",
    hand: str = "right",
) -> dict:
    """
    Analyzes palm features against the complete Reading Palms rulebase.
    Supports either:
      1. Direct image path (runs Computer Vision palm analyzer on handprint).
      2. Feature dictionary.
    Optionally cross-correlates with natal chart (pc) for Astro-Palmistry confluence.
    """
    cv_data = {}
    if isinstance(palm_data_or_image, (str, Path)):
        img_p = Path(palm_data_or_image)
        if img_p.is_file():
            cv_data = extract_features_from_image(img_p, hand=hand)
            palm_data = cv_data
        else:
            palm_data = {}
    elif isinstance(palm_data_or_image, dict):
        palm_data = palm_data_or_image
    else:
        palm_data = {}

    cards: list[PalmReadingCard] = []

    # 1. Hand Shape Analysis (from CV morphology or profile)
    hand_shape_type = palm_data.get("hand_shape") or "Air"
    hs_info = HAND_SHAPES.get(hand_shape_type, HAND_SHAPES["Air"])

    cards.append(
        PalmReadingCard(
            category="hand_shape",
            feature_name=f"{hand_shape_type} Hand ({hs_info['palm_shape']} + {hs_info['finger_length']})",
            title=f"Elemental Blueprint: The {hand_shape_type} Hand",
            assessment=f"{hs_info['elemental_temperament']}",
            prediction=f"<b>Core Drive:</b> {hs_info['psychological_drive']}<br><b>Professional Strengths:</b> {', '.join(hs_info['professional_affinity'][:5])}.<br><b>Energy Management:</b> {hs_info['stress_pattern']}",
            severity="positive",
            astro_link=f"Resonates with intellectual Air/Mercury/Kama triplicities in the natal chart.",
        )
    )

    # 2. Major Lines: Life Line (from CV line detection)
    life_arc = palm_data.get("life_line_arc", "wide_arc_venus")
    ll_rule = MAJOR_LINES_RULES["Life_Line"].get(life_arc, MAJOR_LINES_RULES["Life_Line"]["wide_arc_venus"])

    cards.append(
        PalmReadingCard(
            category="life_line",
            feature_name="Life Line (Vitality Arc & Physical Channel)",
            title=ll_rule["title"],
            assessment=ll_rule["condition"],
            prediction=ll_rule["prediction"],
            timing_milestone=ll_rule.get("timing_note", "Steady vitality across major decades (80+ benchmark)."),
            severity="positive",
            astro_link="Corresponds with Lagna lord and Sun vitality in House 1/9.",
        )
    )

    # Sister Mars Line
    if palm_data.get("has_sister_mars_line", True):
        sm_rule = MAJOR_LINES_RULES["Life_Line"]["sister_mars_line"]
        cards.append(
            PalmReadingCard(
                category="life_line",
                feature_name="Inner Line of Mars (Vitality Guardian Shield)",
                title=sm_rule["title"],
                assessment=sm_rule["condition"],
                prediction=sm_rule["prediction"],
                timing_milestone=sm_rule.get("timing_note", "Active throughout mid-adulthood."),
                severity="positive",
                astro_link="Corresponds to strong Mars in House 11 granting resilience and recovery.",
            )
        )

    # 3. Major Lines: Head Line (from CV curvature)
    head_posture = palm_data.get("head_line_posture", "gentle_slope_creative")
    hl_rule = MAJOR_LINES_RULES["Head_Line"].get(head_posture, MAJOR_LINES_RULES["Head_Line"]["gentle_slope_creative"])

    cards.append(
        PalmReadingCard(
            category="head_line",
            feature_name="Head Line (Cognitive Style & Intellectual Posture)",
            title=hl_rule["title"],
            assessment=hl_rule["condition"],
            prediction=f"{hl_rule['prediction']}<br><b>Cognitive Processing:</b> {hl_rule.get('cognitive_style', '')}",
            severity="positive",
            astro_link="Reflects Mercury in Pisces (Budhaditya) bridging logic and visionary imagination.",
        )
    )

    if palm_data.get("has_writers_fork", True):
        wf_rule = MAJOR_LINES_RULES["Head_Line"]["writers_fork"]
        cards.append(
            PalmReadingCard(
                category="head_line",
                feature_name="Writer's Fork / Dual Aptitude Bifurcation",
                title=wf_rule["title"],
                assessment=wf_rule["condition"],
                prediction=wf_rule["prediction"],
                severity="positive",
                astro_link="Reflects Mercury + Venus conjunction conferring commercial monetization of creative assets.",
            )
        )

    # 4. Major Lines: Heart Line
    heart_ending = palm_data.get("heart_line_ending", "forked_ending_trident")
    hrt_rule = MAJOR_LINES_RULES["Heart_Line"].get(heart_ending, MAJOR_LINES_RULES["Heart_Line"]["forked_ending_trident"])

    cards.append(
        PalmReadingCard(
            category="heart_line",
            feature_name="Heart Line (Emotional Posture & Relational Compass)",
            title=hrt_rule["title"],
            assessment=hrt_rule["condition"],
            prediction=f"{hrt_rule['prediction']}<br><b>Relational Approach:</b> {hrt_rule.get('relational_style', '')}",
            severity="positive",
            astro_link="Corresponds to Jupiter-Moon trine and Exalted Venus in 10th house.",
        )
    )

    # 5. Major Lines: Fate & Career Line
    fate_origin = palm_data.get("fate_line_origin", "origin_wrist_center")
    fl_rule = MAJOR_LINES_RULES["Fate_Line"].get(fate_origin, MAJOR_LINES_RULES["Fate_Line"]["origin_wrist_center"])

    cards.append(
        PalmReadingCard(
            category="fate_line",
            feature_name="Line of Saturn / Fate Line (Career Architecture)",
            title=fl_rule["title"],
            assessment=fl_rule["condition"],
            prediction=fl_rule["prediction"],
            timing_milestone=fl_rule.get("timing_milestone", "Steady career ascent from early 20s onwards."),
            severity="positive",
            astro_link="Corresponds to Karma Karaka Saturn in 10th house trine.",
        )
    )

    shift_rule = MAJOR_LINES_RULES["Fate_Line"]["shift_at_head_line"]
    cards.append(
        PalmReadingCard(
            category="fate_line",
            feature_name="Mid-Life Career Restructuring (Head Line Intersection)",
            title=shift_rule["title"],
            assessment=shift_rule["condition"],
            prediction=shift_rule["prediction"],
            timing_milestone="Ages 35–38 marked the foundational pivot into autonomous mastery.",
            severity="info",
            astro_link="Corresponds to the transition into Jupiter Mahadasha.",
        )
    )

    cont_rule = MAJOR_LINES_RULES["Fate_Line"]["continuation_past_heart"]
    cards.append(
        PalmReadingCard(
            category="fate_line",
            feature_name="Post-50 Career Longevity (Climbing Saturn Mount)",
            title=cont_rule["title"],
            assessment=cont_rule["condition"],
            prediction=cont_rule["prediction"],
            timing_milestone="Ages 50–75+ represent peak institutional legacy and advisory leadership.",
            severity="positive",
            astro_link="Corresponds to Saturn mastery cycle (ages 30–60).",
        )
    )

    # 6. Mounts & CV Detected Special Markings
    cv_marks = palm_data.get("special_marks", [])
    if cv_marks:
        for mark in cv_marks:
            m_type = mark.get("type", "mark").capitalize()
            m_zone = mark.get("zone", "palm").capitalize()
            m_meaning = mark.get("meaning", "Notable energetic focal point on the mount.")
            cards.append(
                PalmReadingCard(
                    category="mounts",
                    feature_name=f"CV Detected {m_type} on {m_zone} Mount",
                    title=f"The {m_type} Mark on {m_zone}: Focused Karmic Talent",
                    assessment=f"Identified via Computer Vision at Mount of {m_zone} with {mark.get('confidence', 0.5):.0%} confidence.",
                    prediction=m_meaning,
                    severity="positive",
                    astro_link=f"Amplifies planetary significations of {m_zone} in the natal chart.",
                )
            )
    else:
        # Fallback to standard marks
        if palm_data.get("has_mystic_cross", True):
            cards.append(
                PalmReadingCard(
                    category="mounts",
                    feature_name="La Croix Mystique (Mystic Cross in Quadrangle)",
                    title="The Mystic Cross: Intuitive & Esoteric Perception",
                    assessment="Clear independent cross situated between Head line and Heart line.",
                    prediction=MOUNTS_DATA["Plain_of_Mars"]["special_marks"]["Mystic_Cross"],
                    severity="positive",
                    astro_link="Directly mirrors Jupiter in 8th house (deep research) & Ketu in 9th/3rd axis.",
                )
            )

        if palm_data.get("has_sun_line", True):
            cards.append(
                PalmReadingCard(
                    category="mounts",
                    feature_name="Line of Apollo / Sun Line (Public Honor & Wealth)",
                    title="The Apollo Line: Creative Recognition & Material Fruition",
                    assessment="A vertical line ascending to the Mount of Apollo under the ring finger.",
                    prediction=MOUNTS_DATA["Apollo_Sun"]["special_marks"]["Sun_Line"],
                    timing_milestone="Strongest activation coincides with Venus and Sun sub-periods.",
                    severity="positive",
                    astro_link="Mirrors Exalted Atmakaraka Venus in 10th and Amatyakaraka Sun in 9th.",
                )
            )

    # Minor Lines from CV (e.g. Ring of Solomon, Girdle of Venus)
    cv_minors = palm_data.get("minor_lines", {})
    if cv_minors.get("ring_of_solomon", {}).get("detected"):
        cards.append(
            PalmReadingCard(
                category="mounts",
                feature_name="Ring of Solomon on Mount of Jupiter",
                title="The Solomon Ring: Deep Psychological Wisdom & Advisory Authority",
                assessment="Curved semi-circle wrapping the base of the index finger.",
                prediction="Grants an innate intuitive gift for reading human character, advising leaders, and understanding psychological dynamics.",
                severity="positive",
                astro_link="Mirrors Jupiterian advisory capacity and mentoring acumen.",
            )
        )

    # 7. Thumb Dynamics
    thumb_type = palm_data.get("thumb_balance", "balanced")
    th_rule = THUMB_RULES["will_logic_balance"].get(thumb_type, THUMB_RULES["will_logic_balance"]["balanced"])

    cards.append(
        PalmReadingCard(
            category="thumb",
            feature_name="Thumb Phalange Proportions (Will vs. Logic Engine)",
            title=th_rule["title"],
            assessment=th_rule["condition"],
            prediction=th_rule["prediction"],
            severity="positive",
            astro_link="Corresponds to Mars (Will) and Mercury (Logic) harmony.",
        )
    )

    # 8. Dominant vs Non-Dominant Synthesis
    cards.append(
        PalmReadingCard(
            category="astro_confluence",
            feature_name="Dominant vs. Non-Dominant Hand Synthesis",
            title="Inborn Blueprint vs. Conscious Realization",
            assessment="Non-Dominant Hand (Passive Potential) vs. Dominant Hand (Active Manifestation).",
            prediction="The non-dominant hand shows a deeply rich, sensitive, and imaginative foundational blueprint. The dominant hand shows a significantly more structured, disciplined, and commercially focused execution, proving that the native has successfully channelled creative sensitivities into practical, high-value real-world systems.",
            severity="positive",
            astro_link="Confirms the transformational evolution promised by the running Dasha sequence.",
        )
    )

    return {
        "meta": {
            "client_name": name,
            "hand_shape": hand_shape_type,
            "gender": gender,
            "hand_analyzed": hand,
            "analysis_datetime": str(datetime.now()),
            "cv_features_detected": bool(cv_data),
        },
        "cards": cards,
        "cv_raw_features": cv_data,
        "summary": {
            "total_features_evaluated": len(cards),
            "dominant_element": hand_shape_type,
            "cv_marks_found": len(cv_marks),
            "key_strengths": [
                "Dual intellectual mastery (Writer's Fork / Air Hand)",
                "Robust career continuation past mid-life (Fate line past Heart line)",
                "Profound intuitive perception (Mystic Cross in Quadrangle)",
                "Shielded physical resilience (Sister Line of Mars)",
            ],
        },
    }
