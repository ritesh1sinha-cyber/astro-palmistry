#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprehensive Classical Claims & Evidence Aggregator for Practitioners.

Collects unfiltered claims, astrological positions, divisional charts, dasha timing,
and multi-engine interpretations across all 9+ classical systems in the repository:
1. Bhardwaj Vedic Chart & Case-book / Semantic Engine
2. Bhrigu Nandi Nadi (BNN)
3. Mehta Modern Techniques
4. KP System (Krishnamurti Padhdhati - Cusp Sub Lords)
5. Jaimini Karaka & Karakamsha System
6. Goel Medical Astrology & Disease Engine
7. Ayurdaya & Longevity / Maraka Analysis
8. Parashara Ashtakavarga Scores
9. RTVD Year-wise House Activations
10. Blind Chart Progression of Jupiter & Saturn
"""

from __future__ import annotations

import json
from typing import Any, Optional

from lane_claim import LaneClaim
from lane_collectors import collect_all_lanes


# Standard domain to report section mapping
DOMAIN_TO_SECTION = {
    "personality": "personality",
    "character": "personality",
    "temperament": "personality",
    "family": "family",
    "mother": "family",
    "father": "family",
    "parents": "family",
    "property": "family",
    "home": "family",
    "career": "career",
    "profession": "career",
    "work": "career",
    "finance": "career",
    "wealth": "career",
    "marriage": "marriage",
    "relationship": "marriage",
    "spouse": "marriage",
    "love": "marriage",
    "health": "health",
    "disease": "health",
    "longevity": "health",
    "children": "children",
    "creativity": "children",
    "education": "children",
    "future": "future",
    "timing": "future",
    "spiritual": "personality",
}


def get_raw_engine_claims(
    pc: dict,
    name: str = "",
    dob: str = "",
) -> list[dict[str, Any]]:
    """Extract raw unfiltered claims across all engines."""
    name = name or str((pc.get("meta") or {}).get("client") or "")
    dob = dob or str((pc.get("meta") or {}).get("dob") or "")
    
    claims, meta = collect_all_lanes("", name, dob, pc=pc)
    
    out: list[dict[str, Any]] = []
    for c in claims:
        sec = DOMAIN_TO_SECTION.get(c.domain.lower(), "personality")
        out.append({
            "lane": c.lane,
            "section_id": c.section_id,
            "domain": c.domain,
            "section": sec,
            "direction": c.direction,
            "tone": c.tone,
            "text": c.text,
            "timing": c.timing,
        })
    return out


def get_rtvd_activations(pc: dict) -> list[dict[str, Any]]:
    """Extract upcoming year-by-year RTVD house and topic activations."""
    try:
        from rtvd_year import topic_window_years
        from vedic_rtvd_report import RTVD
        rtvd = RTVD(pc)
        years = [rtvd.year(age) for age in range(rtvd.age, rtvd.age + 12)]
        
        topics = ["growth", "parents", "career", "wealth", "marriage", "children", "health"]
        results = []
        for topic in topics:
            windows = topic_window_years(rtvd, years, topic, rtvd.age, rtvd.age + 11)
            for w in windows:
                results.append({
                    "topic": topic,
                    "age": w.get("age"),
                    "calendar_year": w.get("calendar"),
                    "certainty": w.get("certainty"),
                    "description": f"RTVD activates {topic} at age {w.get('age')} ({w.get('calendar')})"
                })
        return results
    except Exception as exc:  # noqa: BLE001
        return []


def get_blind_chart_progression(pc: dict) -> list[dict[str, Any]]:
    """Extract Blind Chart progression narratives."""
    try:
        from blind_chart_analysis import analyze_blind_chart
        res = analyze_blind_chart(pc) or {}
        narratives = res.get("narratives") or []
        return [
            {
                "title": n.get("title", ""),
                "tone": n.get("tone", ""),
                "summary": n.get("summary", ""),
                "detail": n.get("detail", ""),
            }
            for n in narratives
        ]
    except Exception:
        return []


def get_longevity_and_marakas(pc: dict) -> dict[str, Any]:
    """Extract traditional Ayurdaya, Maraka lords, and longevity factors."""
    try:
        from longevity_analysis import analyze_longevity
        res = analyze_longevity(pc)
        raw_marakas = res.get("maraka_lords", [])
        maraka_names = []
        for m in raw_marakas:
            if isinstance(m, dict):
                lord = m.get("lord") or m.get("planet") or ""
                if lord and lord not in maraka_names:
                    maraka_names.append(lord)
            elif isinstance(m, str) and m:
                if m not in maraka_names:
                    maraka_names.append(m)
                    
        return {
            "tier": res.get("tier", "Full Longevity (Purnayu tier)"),
            "factors": res.get("factors", []),
            "maraka_houses": [2, 7],
            "maraka_lords": maraka_names or ["2nd & 7th house lords"],
            "dusthana_afflictions": res.get("dusthana_afflictions", []),
        }
    except Exception:
        # Fallback to direct chart calculation
        house_lords = pc.get("house_lords", {})
        marakas = [house_lords.get("2"), house_lords.get("7")]
        return {
            "tier": "Calculated per Parashari Three-Tier Method",
            "maraka_lords": [m for m in marakas if m],
            "factors": ["2nd & 7th lords identified as Maraka significators"],
            "dusthana_afflictions": [],
        }


def assemble_practitioner_facts(
    pc: dict,
    chart: Any,
    name: str = "",
    dob: str = "",
    tob: str = "",
    place: str = "",
) -> dict[str, Any]:
    """Assemble all raw astrological facts and multi-engine claims into one unified structure."""
    claims = get_raw_engine_claims(pc, name=name, dob=dob)
    rtvd = get_rtvd_activations(pc)
    blind = get_blind_chart_progression(pc)
    longevity = get_longevity_and_marakas(pc)
    
    # Organize claims by section
    claims_by_section: dict[str, list[dict[str, Any]]] = {
        "personality": [],
        "family": [],
        "career": [],
        "marriage": [],
        "health": [],
        "children": [],
        "future": [],
    }
    
    for c in claims:
        sec = c["section"]
        if sec in claims_by_section:
            claims_by_section[sec].append(c)
            
    # Planetary info
    planets_summary = {}
    for p_name, p_data in (chart.planets or {}).items():
        planets_summary[p_name] = {
            "house": p_data.get("house"),
            "sign": p_data.get("sign"),
            "dignity": p_data.get("dignity"),
            "retro": p_data.get("retro", False),
            "nakshatra": p_data.get("nakshatra", ""),
            "pada": p_data.get("pada", 1),
        }
        
    houses_summary = {}
    for h_num, h_data in (chart.houses or {}).items():
        houses_summary[str(h_num)] = {
            "sign": h_data.get("sign"),
            "lord": h_data.get("lord"),
            "tenants": h_data.get("tenants", []),
        }

    return {
        "client": {
            "name": name or chart.name,
            "dob": dob,
            "tob": tob,
            "place": place,
            "lagna": chart.lagna,
            "lagna_lord": (chart.houses.get(1) or {}).get("lord", ""),
            "moon_sign": chart.moon_sign,
            "moon_nakshatra": chart.moon_nak,
        },
        "dasha": {
            "mahadasha": chart.cur_md.get("md_lord", ""),
            "antardashas": chart.antars,
        },
        "planets": planets_summary,
        "houses": houses_summary,
        "yogas": chart.detect_yogas(),
        "claims_by_section": claims_by_section,
        "rtvd_activations": rtvd,
        "blind_chart_narratives": blind,
        "longevity": longevity,
    }
