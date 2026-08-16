#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Classical Vedic LLM Synthesis Layer for Astrologer Consultation.

Takes multi-engine classical facts, divisional charts, dasha timing, and raw claims
across 9+ classical systems (Bhardwaj, BNN, Mehta, KP, Jaimini, Goel, Longevity,
Ashtakavarga, RTVD, Blind Chart), and produces an exhaustive, high-rigor consultation brief.
"""

from __future__ import annotations

import json
from typing import Any, Optional
from pydantic import BaseModel, Field


class SectionSynthesis(BaseModel):
    section_key: str = Field(description="Section identifier")
    synthesis_title: str = Field(description="Display heading for this consultation area")
    narrative: str = Field(description="Exhaustive practitioner-level synthesis citing astrological factors")
    engine_confirmations: list[str] = Field(default_factory=list, description="Points where multiple systems converge")
    diagnostic_contrasts: list[str] = Field(default_factory=list, description="Contrasting readings or dual promises between systems")
    remedial_priorities: list[str] = Field(default_factory=list, description="Remedies specific to this area's afflictions")


class PractitionerConsultationBrief(BaseModel):
    executive_summary: str = Field(description="Overall consultation summary, lagna/rashi signature, and current dasha tone")
    personality_synthesis: SectionSynthesis
    family_synthesis: SectionSynthesis
    career_synthesis: SectionSynthesis
    marriage_synthesis: SectionSynthesis
    health_and_longevity_synthesis: SectionSynthesis
    children_synthesis: SectionSynthesis
    current_period_synthesis: SectionSynthesis
    future_timing_synthesis: SectionSynthesis
    confluence_diagnostic_matrix: list[str] = Field(default_factory=list, description="Summary of multi-system consensus")
    comprehensive_remedies: list[str] = Field(default_factory=list, description="Prioritized classical remedies with astrological reasoning")


PRACTITIONER_SYSTEM_PROMPT = """You are a Master Jyotish Acharya preparing an exhaustive, professional Astrologer's Consultation Brief.
The reader is a professional consulting astrologer who requires complete, unvarnished astrological facts, traditional Shastra indications, and cross-method multi-system confluence.

RULES:
1. Astrological Rigor: Preserve and explicitly name all Lagna, Moon sign, Nakshatras, house lords, planetary dignities (exalted, own sign, debilitated, combust, retrograde), yogas, KP cusp sub-lords, BNN planetary combinations, and Jaimini Karakas.
2. Cross-System Synthesis: Synthesize the findings from Bhardwaj, BNN Nadi, Mehta Modern, KP, Jaimini, Goel Medical, Longevity/Ayurdaya, Ashtakavarga, and RTVD.
3. No Consumer Censorship: Objectively analyze classical medical vulnerabilities, longevity/maraka markers, family friction, or career challenges as recorded in the shastras.
4. Professional Consultation Tone: Write in the authoritative, traditional Jyotish voice of an experienced master astrologer.
5. Actionable Remedies: Propose precise Vedic remedies (Maha Mrityunjaya, Gayatri/Graha Jaap counts, specific gemstone verdicts with reasons, charities on specific days, and conduct/lifestyle corrections).
"""


def _build_deterministic_synthesis(facts: dict[str, Any]) -> dict[str, Any]:
    """Deterministic fallback compiler when LLM is offline."""
    client = facts.get("client", {})
    lagna = client.get("lagna", "")
    moon_sign = client.get("moon_sign", "")
    moon_nak = client.get("moon_nakshatra", "")
    dasha = facts.get("dasha", {})
    md = dasha.get("mahadasha", "")
    claims_by_sec = facts.get("claims_by_section", {})
    
    sections = {}
    for sec_key, title in [
        ("personality", "Personality, Physical Bearing & Core Constitution"),
        ("family", "Family Heritage, Parents & Domestic Karma"),
        ("career", "Professional Authority, Vocation & Financial Rise"),
        ("marriage", "Relationship Dynamics, Partnership & Marital Harmony"),
        ("health", "Health Vulnerabilities, Organ Mapping & Ayurdaya"),
        ("children", "Progeny Indications, Education & Fifth House Lineage"),
        ("future", "Dasha Operation, Transits & Upcoming Horizons"),
    ]:
        sec_claims = claims_by_sec.get(sec_key, [])
        confirmations = []
        contrasts = []
        remedials = []
        
        paragraphs = []
        for c in sec_claims[:8]:
            paragraphs.append(f"[{c.get('lane', 'Vedic')}] {c.get('text', '')}")
            if c.get("direction") == "positive":
                confirmations.append(f"{c.get('lane')}: Affirms strength in {c.get('domain', sec_key)}")
            elif c.get("direction") == "caution":
                contrasts.append(f"{c.get('lane')}: Flags cautionary factors in {c.get('domain', sec_key)}")
                remedials.append(f"Remedial attention required for {c.get('domain', sec_key)} afflictions")
                
        if not paragraphs:
            paragraphs.append(f"Classical readings for {lagna} ascendant with {md} Mahadasha active.")
            
        sections[sec_key] = {
            "section_key": sec_key,
            "synthesis_title": title,
            "narrative": " ".join(paragraphs),
            "engine_confirmations": confirmations[:4],
            "diagnostic_contrasts": contrasts[:4],
            "remedial_priorities": remedials[:3],
        }
        
    return {
        "executive_summary": (
            f"Consultation brief for {client.get('name', 'Native')} born under {lagna} Lagna with Moon in {moon_sign} ({moon_nak}). "
            f"Currently running {md} Mahadasha. Chart reflects distinct karmic patterns verified across multiple classical shastras."
        ),
        "personality_synthesis": sections["personality"],
        "family_synthesis": sections["family"],
        "career_synthesis": sections["career"],
        "marriage_synthesis": sections["marriage"],
        "health_and_longevity_synthesis": sections["health"],
        "children_synthesis": sections["children"],
        "current_period_synthesis": {
            "section_key": "currently",
            "synthesis_title": "Current Dasha Operation & Planetary Demands",
            "narrative": f"Running {md} Mahadasha. Planetary lords activate specific house portfolios demanding focused attention and disciplined remedies.",
            "engine_confirmations": [f"Vimshottari Mahadasha lord {md} governs current overarching life direction."],
            "diagnostic_contrasts": [],
            "remedial_priorities": [f"Pacify {md} through prescribed mantra jaap and Dana."],
        },
        "future_timing_synthesis": sections["future"],
        "confluence_diagnostic_matrix": [
            "Bhardwaj case-book and BNN Nadi cross-confirm primary lagna and 10th house karmic themes.",
            "KP Cusp Sub-Lord alignments define concrete event triggers.",
            "Goel medical indices delineate specific organ vulnerabilities requiring preventive care."
        ],
        "comprehensive_remedies": [
            f"Maha Mrityunjaya Jaap (108 repetitions daily) for overall protection and longevity preservation.",
            f"Prescribed planetary remedies for running {md} Mahadasha lord.",
            "Selective gemstone recommendation based on lagna/trikona beneficence."
        ],
    }


def generate_practitioner_synthesis(facts: dict[str, Any]) -> dict[str, Any]:
    """Generate practitioner consultation brief via LLM, falling back gracefully if offline."""
    try:
        from core.llm_client import complete_model
        
        user_prompt = (
            "Analyze the following multi-engine astrological facts and generate a full Practitioner Consultation Brief:\n\n"
            + json.dumps(facts, indent=2, default=str)
        )
        
        res = complete_model(
            PractitionerConsultationBrief,
            PRACTITIONER_SYSTEM_PROMPT,
            user_prompt,
            temperature=0.3,
        )
        if res is not None:
            return res.model_dump()
    except Exception as exc:  # noqa: BLE001
        print(f"[classical_llm_synthesis] LLM generation fell back: {exc}", flush=True)
        
    return _build_deterministic_synthesis(facts)
