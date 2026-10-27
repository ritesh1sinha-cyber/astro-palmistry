#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
palmistry_consultation_reading.py — Advanced Multi-Aspect Palmistry Consultation & Facts Engine

Synthesizes dermatoglyphic neural timing, ridge contour models, and computer vision feature extraction.
Zero external author or book references. Fully personalized to the native's specific measured features.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from palm_api.life_aspects import build_life_aspects  # noqa: F401 — kept for optional multi_aspect path


def generate_personalized_scientific_secrets(client_name: str, raw_cv: dict, hand_shape: str, lang: str = "en") -> list[dict[str, str]]:
    """
    Generates 100% personalized scientific palmistry findings based on the native's
    exact measured Computer Vision features, line densities, and hand morphology.
    """
    lang_code = str(lang or "").lower().strip()
    is_hi = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_te = lang_code in ("te_en", "tenglish", "te", "telugu")
    quality = raw_cv.get("quality") or {}
    if str(quality.get("grade") or "poor").lower() == "poor":
        return []
    # Every card below states only what the photo measured. This function used
    # to return five fixed paragraphs for every customer ("density 0.132",
    # "sealed triangle, zero fractures") whatever the hand looked like, which is
    # how a photo with no palm in it received a confident reading.
    minor = raw_cv.get("minor_lines") or {}
    cards: list[dict[str, str]] = []

    sol = minor.get("ring_of_solomon") or {}
    if sol.get("detected") and str(sol.get("strength") or "") in ("moderate", "strong"):
        cards.append({
            "id": "solomon_ring_psychic_radar",
            "title": "A Ring of Solomon on your Mount of Jupiter",
            "subtitle": "A fine arc around the base of the index finger",
            "scientific_fact": (
                f"The image analysis traced an arc around the base of your index finger "
                f"(measured line density {sol.get('density')}, strength: {sol.get('strength')}). "
                f"Traditionally this ring is read as a natural feel for people and "
                f"what lies behind what they say."
            ),
            "entertainment_insight": (
                "Treat it as a prompt for reflection: do you tend to sense a person's "
                "mood or motive early? If yes, the ring and your experience agree."
            ),
        })

    return cards


def _evidence_only_consultation(
    analysis_res: dict[str, Any], client_name: str, lang: str = "en"
) -> dict[str, Any]:
    """Build consultation cards only from measurements that actually exist."""
    raw_cv = analysis_res.get("cv_raw_features") or {}
    lang_code = str(lang or "").lower().strip()
    is_hi = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_te = lang_code in ("te_en", "tenglish", "te", "telugu")
    quality = raw_cv.get("quality") or {}
    grade = str(quality.get("grade") or "poor").lower()
    base = {
        "client_name": client_name,
        "gender": (analysis_res.get("meta") or {}).get("gender", "unknown"),
        "hand_shape": "Unknown",
        "measured": bool(raw_cv),
        "sections": {},
        "timing_milestones": [],
        "multi_aspect_confluence": [],
    }
    if grade == "poor" or not raw_cv:
        base["quality_note"] = (
            "Palm photo quality measured karne ke liye kaafi nahi hai."
            if is_hi else
            "Palm photo quality measured consultation kosam saripodu."
            if is_te else
            "Palm photo quality is insufficient for a measured consultation."
        )
        return base

    morphology = raw_cv.get("morphology") or {}
    hand_shape = str(morphology.get("hand_type") or "").strip().title()
    base["hand_shape"] = hand_shape or "Unknown"
    sections: dict[str, Any] = {}
    if hand_shape and hand_shape.lower() != "unknown":
        if is_hi:
            cp_title = f"{hand_shape} Haath Ki Mool Aakriti"
            cp_narrative = f"Aapke haath ka swabhav {hand_shape} tatva se juda hai. Yeh aapko teez soch, samajhdari aur vyavaharik kshamta pradan karta hai."
        elif is_te:
            cp_title = f"{hand_shape} Cheyi Moola Aakaram"
            cp_narrative = f"Mee cheyi {hand_shape} tatvanni darshisthundi. Idi meeku alochana shakthi, teekshnamaina buddhi mariyu practical approach isthundi."
        else:
            cp_title = f"{hand_shape} Hand Archetype & Constitution"
            cp_narrative = f"Your hand exhibits classic {hand_shape} archetype proportions, favoring intellectual agility, strategic communication, and dignified adaptability."
        sections["core_persona"] = {
            "title": cp_title,
            "narrative": cp_narrative,
        }

    lines = raw_cv.get("lines") or {}
    line_configs = {
        "head": {
            "en": ("Head Line (Line of Intellect)", "Your Head Line reflects a balanced, analytical mind with pragmatic focus and strategic foresight."),
            "hi": ("Mastishk Rekha (Head Line)", "Aapki mastishk rekha spasht aur santulit soch ko darshati hai, jo sankat mein bhi shant nirnay lene mein madad karti hai."),
            "te": ("Mastishka Rekha (Head Line)", "Mee mastishka rekha spashthamaina alochana mariyu samasya parishkara naipunyanni darshisthundi."),
        },
        "heart": {
            "en": ("Heart Line (Emotional Equilibrium)", "Your Heart Line indicates loyal attachments, balanced emotional maturity, and high dignity in personal relationships."),
            "hi": ("Hriday Rekha (Heart Line)", "Aapki hriday rekha vishwasniya sambandhon, aadar aur paripakva bhavnatmak santulan ka sanket deti hai."),
            "te": ("Hrudaya Rekha (Heart Line)", "Mee hrudaya rekha nammakamaina sambandhalu mariyu paripakvamaina bhavodvegamulanu chupisthundi."),
        },
        "life": {
            "en": ("Life Line (Vitality & Endurance)", "A well-curved, unbroken Life Line marks sound constitutional stamina, resilience under pressure, and steady vitality."),
            "hi": ("Jeevan Rekha (Life Line)", "Spasht jeevan rekha uttam sharirik urja, rogapratirodhak kshamta aur jeevan ke prati dridh sankalp ko darshati hai."),
            "te": ("Jeevitha Rekha (Life Line)", "Spashthamaina jeevitha rekha manchi aarogyam, vitality mariyu sthiramaina manobhalanni chupisthundi."),
        },
        "fate": {
            "en": ("Fate Line (Career & Self-Mastery)", "An ascending Fate Line highlights steady professional growth, self-made authority, and strategic focus."),
            "hi": ("Bhagya Rekha (Fate Line)", "Aapki bhagya rekha swayam-nirmit safalta, anushasit career aur deerghakalin unnati ka sanket deti hai."),
            "te": ("Bhagya Rekha (Fate Line)", "Mee bhagya rekha swayam krushi tho vache vruthi vikasam mariyu sthiramaina unnadathani chupisthundi."),
        },
    }
    for key, cfg in line_configs.items():
        row = lines.get(key) if isinstance(lines, dict) else None
        if not isinstance(row, dict) or not row.get("detected"):
            continue
        section_key = {
            "head": "mind_architecture",
            "heart": "heart_equilibrium",
            "life": "vitality_shield",
            "fate": "career_trajectory",
        }[key]
        lang_key = "hi" if is_hi else ("te" if is_te else "en")
        title, narrative = cfg[lang_key]
        sections[section_key] = {
            "title": title,
            "narrative": narrative,
        }

    minor = raw_cv.get("minor_lines") or {}
    minor_dict = {
        "ring_of_solomon": {
            "en": ("Ring of Solomon (Guru Mudrika)", "Psychic insight, leadership presence, and immediate character intuition."),
            "hi": ("Guru Mudrika (Ring of Solomon)", "Vyaktitva aur mann ki baat ko turant samajhne ki prakritik kshamta."),
            "te": ("Guru Mudrika (Ring of Solomon)", "Manushula swabhavam mariyu antharyam grahinche shakthi."),
        },
        "solomon": {
            "en": ("Ring of Solomon (Guru Mudrika)", "Psychic insight, leadership presence, and immediate character intuition."),
            "hi": ("Guru Mudrika (Ring of Solomon)", "Vyaktitva aur mann ki baat ko turant samajhne ki prakritik kshamta."),
            "te": ("Guru Mudrika (Ring of Solomon)", "Manushula swabhavam mariyu antharyam grahinche shakthi."),
        },
        "sun": {
            "en": ("Surya Rekha (Line of Sun / Apollo)", "Prominence, creative distinction, and public recognition for your work."),
            "hi": ("Surya Rekha (Sun Line)", "Karya kshetra mein pratishtha, samman aur creative safalta ka yog."),
            "te": ("Surya Rekha (Sun Line)", "Udyogam mariyu vruthilo gouravam, recognition mariyu kirthi."),
        },
        "apollo": {
            "en": ("Surya Rekha (Line of Sun / Apollo)", "Prominence, creative distinction, and public recognition for your work."),
            "hi": ("Surya Rekha (Sun Line)", "Karya kshetra mein pratishtha, samman aur creative safalta ka yog."),
            "te": ("Surya Rekha (Sun Line)", "Udyogam mariyu vruthilo gouravam, recognition mariyu kirthi."),
        },
        "mercury": {
            "en": ("Budh Rekha (Line of Mercury / Commerce)", "Commercial acumen, eloquent speech, and sharp strategic business logic."),
            "hi": ("Budh Rekha (Mercury Line)", "Vyaparik buddhi, spasht vaani aur strategic calculation mein kushal."),
            "te": ("Budh Rekha (Mercury Line)", "Vyapara dhorani, spashthamaina maata mariyu practical planning."),
        },
        "girdle_of_venus": {
            "en": ("Shukra Mudrika (Girdle of Venus)", "Aesthetic refinement, emotional depth, and high creative receptivity."),
            "hi": ("Shukra Mudrika (Girdle of Venus)", "Kalaatmak ruchi, saundarya bodh aur gehri bhavnatmak sensitivity."),
            "te": ("Shukra Mudrika (Girdle of Venus)", "Kalaatmakata, saundarya drushti mariyu lothaina bhavodvegam."),
        },
        "mars_sister": {
            "en": ("Mangal Sahayak Rekha (Inner Mars / Vitality Shield)", "Inherent physical resilience and protective stamina during heavy workloads."),
            "hi": ("Mangal Sahayak Rekha (Vitality Shield)", "Sharirik kshamta, rogapratirodhak shakti aur suraksha kavach."),
            "te": ("Mangal Sahayak Rekha (Vitality Shield)", "Aarogya balam, roga nirodhaka shakthi mariyu rakshana kavacham."),
        },
        "mystic_cross": {
            "en": ("Mystic Cross (Rahasya Chinh)", "Strong intuitive radar and deep interest in hidden sciences or philosophical truth."),
            "hi": ("Mystic Cross (Rahasya Chinh)", "Gehri aantarik prerna aur gupt vidyaon ya adhyatma mein ruchi."),
            "te": ("Mystic Cross (Rahasya Chinh)", "Anthardrushti, adhyathmika asakthi mariyu sookshma grahana shakthi."),
        },
    }
    detected_minor = []
    if isinstance(minor, dict):
        for key, row in minor.items():
            if isinstance(row, dict) and row.get("detected"):
                lang_key = "hi" if is_hi else ("te" if is_te else "en")
                line_info = minor_dict.get(key.lower(), {
                    "en": (str(row.get("title") or key).replace("_", " ").title(), "A distinct minor line marking refined subconscious focus."),
                    "hi": (str(row.get("title") or key).replace("_", " ").title(), "Ek shubh minor line jo vishesh pratibha ko badhati hai."),
                    "te": (str(row.get("title") or key).replace("_", " ").title(), "Oka vishesha minor line mee prathibhaku balam isthundi."),
                })
                m_name, m_meaning = line_info[lang_key]
                status_txt = "Spasht Drishtigat" if is_hi else ("Spashthamga Kanipinchindi" if is_te else "Distinctly Formed")
                detected_minor.append({
                    "name": m_name,
                    "status": status_txt,
                    "meaning": m_meaning,
                })
    if detected_minor:
        sections["minor_power_lines"] = {
            "title": (
                "Vishesh Rekhayein Aur Shubh Mudrikayein" if is_hi else
                "Vishesha Rekhalu Mariyu Shubha Mudrikalu" if is_te else
                "Minor Power Lines & Auspicious Markings"
            ),
            "lines": detected_minor[:8],
        }

    # No "wealth vault" / "palmist counsel" cards: they asserted an enclosed
    # triangle and personality traits that the image analysis never measures,
    # and were identical for every customer. Absent keys are skipped downstream.
    sections["scientific_secrets"] = generate_personalized_scientific_secrets(client_name, raw_cv, hand_shape, lang=lang)
    base["sections"] = sections
    return base


def generate_palm_consultation_sections(
    analysis_res: dict, client_name: str | None = None, lang: str = "en"
) -> dict[str, Any]:
    """
    Synthesizes palm analysis into comprehensive, fascinating consultation sections:
    1. Core Hand Persona & Elemental Drive
    2. Cognitive Architecture & Mind Wiring (Writer's Fork)
    3. Career Trajectory & Timing Roadmap (Age 35 Pivot -> 50-75+ Runway)
    4. Vitality, Stamina & The Inner Shield (Sister Mars Line)
    5. Emotional Climate & Heart Posture (Solomon's Equilibrium)
    6. Minor Power Lines & Hidden Antennas (Sun Line, Mercury Line, Girdle of Venus, Solomon Ring)
    7. The Closed Wealth Triangle (The Money Vault)
    8. Dual-Hand Secret (Inborn Blueprint vs Manifested Reality)
    9. Palmist's Personal Counsel & Strategy
    10. Personalized Scientific Palmistry Curiosities (Prof. Dayanand)
    """
    meta = analysis_res.get("meta", {})
    if not client_name:
        client_name = meta.get("client_name", "Native")
    # All callers use the same measured, quality-gated projection.
    return _evidence_only_consultation(
        analysis_res, client_name or "Native", lang=lang)


def save_palm_consultation_json(
    analysis_res: dict,
    out_path: str | Path,
) -> Path:
    """Saves complete LLM-ready raw facts JSON payload."""
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    consultation_data = generate_palm_consultation_sections(analysis_res)
    meta = analysis_res.get("meta", {})

    json_payload = {
        "engine_version": "Palmistry_Consultation_Engine_v2.0",
        "generated_at": datetime.now().isoformat(),
        "methodology": [
            "Scientific Dermatoglyphic Neural Mapping",
            "Classical Ridge Contour & Progression System",
            "Computer Vision Topography & Morphological Analysis"
        ],
        "client_metadata": {
            "name": meta.get("client_name", "Native"),
            "gender": meta.get("gender", "male"),
            "dominant_hand_shape": consultation_data["hand_shape"],
            "cv_processed": meta.get("cv_features_detected", True),
        },
        "verified_palm_facts": {
            k: consultation_data["sections"].get(k)
            for k in ("core_persona", "mind_architecture", "career_trajectory", "vitality_shield", "heart_equilibrium", "minor_power_lines")
            if consultation_data["sections"].get(k)
        },
        "scientific_laws_and_curiosities_personalized": consultation_data["sections"].get("scientific_secrets", []),
        "master_chronological_milestone_timeline": consultation_data.get("timing_milestones", []),
        "multi_aspect_confluence_domains": consultation_data.get("multi_aspect_confluence", []),
        "llm_prompt_instructions": {
            "role": "You are a master scientific palmist providing a personal, face-to-face consultation to the client.",
            "task": "Synthesize the verified palm facts, minor power lines, wealth triangle, timing roadmap, and personalized scientific curiosities above into an empowering, warm, deeply perceptive consultation reading.",
            "guidelines": [
                "Strictly adhere to the verified line shapes, timings, and mount formations provided.",
                "Speak directly to the native with empathy, clarity, and authority.",
                "Highlight the native's personalized scientific palmistry facts that are present in verified_palm_facts, and never state a feature the facts do not contain.",
                "Do NOT introduce astrological terminology (keep focus purely on palmistry, morphology, and dermatoglyphics).",
                "Explain both the inborn potential (left hand) and active reality (right hand).",
            ]
        }
    }

    path.write_text(json.dumps(json_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
