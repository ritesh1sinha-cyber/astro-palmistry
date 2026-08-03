#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Goel Trishamsha - adversity / stress timing (rules15 + Vimshottari).

D1 stress set: lagna lord, 6th lord, 8th lord, Moon
D30 focal set: lagna lord, 8th lord, Moon, planets on D30 lagna and 8th
Common grahas -> friction peaks in their MD/AD
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from astro_precompute import VIMSH_LORDS, build_antardashas

BENEFICS = {"Moon", "Mercury", "Jupiter", "Venus"}

MILESTONE_AGES = (24, 28, 32, 35, 38, 42, 45, 50)


def _fmt_range(start: str, end: str) -> str:
    try:
        s = datetime.strptime(start[:10], "%Y-%m-%d").strftime("%b %Y")
        e = datetime.strptime(end[:10], "%Y-%m-%d").strftime("%b %Y")
        return f"{s} - {e}"
    except ValueError:
        return ""


def _parse_dob(pc: dict) -> date | None:
    dob_str = pc.get("meta", {}).get("dob", "")
    if not dob_str:
        return None
    try:
        return datetime.strptime(dob_str[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _age_between(dob: date, when: date) -> int:
    return (when - dob).days // 365


def _d1_stress_set(pc: dict, analysis: dict) -> set[str]:
    s: set[str] = set()
    for key in ("lord1_d1", "lord6_d1", "lord8_d1"):
        v = analysis.get(key, "")
        if v:
            s.add(v)
    if "Moon" in pc.get("planets", {}):
        s.add("Moon")
    return s


def _d30_stress_set(analysis: dict) -> set[str]:
    s: set[str] = set()
    if analysis.get("d30_lagna_lord"):
        s.add(analysis["d30_lagna_lord"])
    if analysis.get("lord8_d30"):
        s.add(analysis["lord8_d30"])
    s.add("Moon")
    for h in (1, 8):
        s.update(analysis.get("d30_houses", {}).get(h, []))
    return s


def _classify_age_tone(analysis: dict) -> str:
    profile = analysis.get("extras", {}).get("fortune_profile", {}).get("label", "mixed")
    if profile in ("unfortunate_self", "unfortunate_redeemed", "unfortunate_partial"):
        return "heavy"
    if profile in ("fortunate", "mixed_fortunate_deeds"):
        return "light"
    return "moderate"


def _chart_tone_scores(tone: str) -> dict[int, float]:
    if tone == "heavy":
        return {32: 4.0, 35: 5.0, 38: 5.0, 42: 4.0, 28: 3.0}
    if tone == "light":
        return {28: 2.0, 32: 2.5, 35: 2.0}
    return {28: 3.0, 32: 4.0, 35: 4.0, 38: 3.0}


def _all_antardashas(pc: dict) -> list[dict]:
    out: list[dict] = []
    for md in pc.get("vimshottari", {}).get("sequence", []):
        md_lord = md.get("md_lord", "")
        if md_lord not in VIMSH_LORDS:
            continue
        md_idx = VIMSH_LORDS.index(md_lord)
        for ad in build_antardashas(md, md_idx):
            out.append({
                "md_lord": md_lord,
                "ad_lord": ad["ad_lord"],
                "start": ad["start"],
                "end": ad["end"],
                "range": _fmt_range(ad["start"], ad["end"]),
            })
    return out


def _ad_stress_weight(
    ad_lord: str, md_lord: str,
    common: set[str], d1_set: set[str], d30_set: set[str],
) -> tuple[int, str]:
    if ad_lord in common:
        if md_lord in common:
            return 8, "common AD inside common MD"
        return 6, "common stress planet antardasha"
    if ad_lord in d30_set:
        if md_lord in common:
            return 4, "Trishamsha focal graha AD, common MD"
        return 3, "Trishamsha focal graha antardasha"
    if ad_lord in d1_set:
        return 2, "birth stress lord antardasha"
    if md_lord in common and ad_lord not in BENEFICS:
        return 2, "malefic AD under stress MD"
    return 0, ""


def _score_milestone_ages(
    dob: date,
    all_ads: list[dict],
    common: set[str],
    d1_set: set[str],
    d30_set: set[str],
    age_tone: str,
) -> tuple[dict[int, float], list[dict]]:
    scores: dict[int, float] = dict(_chart_tone_scores(age_tone))
    periods: list[dict] = []
    for ad in all_ads:
        try:
            start = datetime.strptime(ad["start"][:10], "%Y-%m-%d").date()
            end = datetime.strptime(ad["end"][:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        a0 = _age_between(dob, start)
        a1 = _age_between(dob, end)
        if a1 < 18 or a0 > 70:
            continue
        w, reason = _ad_stress_weight(ad["ad_lord"], ad["md_lord"], common, d1_set, d30_set)
        if w < 2:
            continue
        mid = (a0 + a1) // 2
        periods.append({
            "md_lord": ad["md_lord"],
            "lord": ad["ad_lord"],
            "start": ad["start"],
            "end": ad["end"],
            "range": ad["range"],
            "age_start": a0,
            "age_end": a1,
            "mid_age": mid,
            "weight": w,
            "reason": reason,
        })
        for age in MILESTONE_AGES:
            if a0 - 1 <= age <= a1 + 1:
                scores[age] = scores.get(age, 0) + w * 0.85
    return scores, periods


def _top_ages(scores: dict[int, float], n: int = 4, min_score: float = 3.0) -> list[int]:
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    out = [age for age, sc in ranked if sc >= min_score][:n]
    return out or ([ranked[0][0]] if ranked else [])


def _primary_period(periods: list[dict], display_ages: list[int]) -> dict | None:
    if not periods:
        return None
    targets = display_ages[:3]
    center = targets[len(targets) // 2] if targets else 35

    def score(p: dict) -> float:
        s = float(p["weight"])
        if any(p["age_start"] - 1 <= t <= p["age_end"] + 1 for t in targets):
            s += 10.0
        if p["lord"] in {"Saturn", "Mars", "Rahu"} and "common" in p.get("reason", ""):
            s += 2.0
        s -= abs(p["mid_age"] - center) * 0.3
        return s

    return max(periods, key=score)


def compute_stress_timing(pc: dict, analysis: dict) -> dict[str, Any]:
    d1_set = _d1_stress_set(pc, analysis)
    d30_set = _d30_stress_set(analysis)
    common = sorted(d1_set & d30_set)
    age_tone = _classify_age_tone(analysis)
    dob = _parse_dob(pc)

    all_ads = _all_antardashas(pc)
    milestone_scores: dict[int, float] = {}
    periods: list[dict] = []
    if dob:
        milestone_scores, periods = _score_milestone_ages(
            dob, all_ads, set(common), d1_set, d30_set, age_tone,
        )

    display_ages = sorted(_top_ages(milestone_scores))
    return {
        "d1_significators": sorted(d1_set),
        "d30_significators": sorted(d30_set),
        "common_significators": common,
        "age_tone": age_tone,
        "display_ages": display_ages,
        "milestone_scores": milestone_scores,
        "stress_periods": periods,
        "primary_period": _primary_period(periods, display_ages),
    }


def _format_age_list(ages: list[int]) -> str:
    if not ages:
        return ""
    if len(ages) == 1:
        return str(ages[0])
    if len(ages) == 2:
        return f"{ages[0]} and {ages[1]}"
    return ", ".join(str(a) for a in ages[:-1]) + f", and {ages[-1]}"


def timing_client_paragraph(timing: dict[str, Any]) -> str:
    ages = timing.get("display_ages", [])
    common = timing.get("common_significators", [])
    primary = timing.get("primary_period")
    tone = timing.get("age_tone", "moderate")

    parts: list[str] = []
    if ages:
        parts.append(f"Likely adversity or stress peak ages in this chart: {_format_age_list(ages)}.")
    if primary:
        a0, a1 = primary["age_start"], primary["age_end"]
        lord = primary.get("lord", "")
        md = primary.get("md_lord", "")
        if a0 != a1:
            parts.append(
                f"Strongest friction dasha at age {a0}-{a1} ({lord} antardasha"
                + (f", {md} mahadasha" if md and md != lord else "")
                + ")."
            )
        else:
            parts.append(f"Strongest friction dasha at age {a0} ({lord} period).")

    if tone == "heavy":
        parts.append("Unfortunate Trishamsha tone - slow down in hostile sub-periods; remedies for lagna and eighth lords matter.")
    elif tone == "light":
        parts.append("Fortunate Trishamsha softens adversity dasha - setbacks are usually manageable with conduct.")
    else:
        parts.append("Mixed fortune chart - stress rises when shared Trishamsha and birth lords run together.")

    if common:
        joined = ", ".join(common[:-1]) + f" and {common[-1]}" if len(common) > 1 else common[0]
        parts.append(f"Key stress planets (shared in birth chart and Trishamsha): {joined}.")

    parts.append("Perform simple remedies for Trishamsha lagna lord and eighth lord during these antardashas.")
    return " ".join(parts)
