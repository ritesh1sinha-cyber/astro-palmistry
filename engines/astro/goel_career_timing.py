#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Goel Predict with Dashamsha - career rise / job-change timing (rules13 + Vimshottari).

Book rules:
  D1 career set: 10th house, 10th lord, Sun, Saturn, Mercury
  D10 dynamic: lagna, 10th, 11th + lords of lagna and 10th
  Common grahas -> career peaks in their MD/AD

Milestone ages scored from chart tone + full-life dasha scan (past and future).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from astro_precompute import VIMSH_LORDS, build_antardashas

MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
BENEFICS = {"Moon", "Mercury", "Jupiter", "Venus"}

MILESTONE_AGES = (22, 24, 26, 28, 30, 32, 35, 38, 40, 45)


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


def _d1_career_set(pc: dict, analysis: dict) -> set[str]:
    planets = pc.get("planets", {})
    s: set[str] = set()
    l10 = analysis.get("lord10_d1", "")
    if l10:
        s.add(l10)
    for p in analysis.get("d1_h10_planets", []):
        s.add(p)
    for k in ("Sun", "Saturn", "Mercury"):
        if k in planets:
            s.add(k)
    return s


def _d10_career_set(analysis: dict) -> set[str]:
    houses = analysis.get("d10_houses", {})
    s: set[str] = set()
    for h in (1, 10, 11):
        s.update(houses.get(h, []))
    if analysis.get("d10_lagna_lord"):
        s.add(analysis["d10_lagna_lord"])
    if analysis.get("lord10_d10"):
        s.add(analysis["lord10_d10"])
    return s


def _classify_age_tone(analysis: dict) -> str:
    """early_rise | steady | late_bloom from D10 scores + fall risk + Saturn mode."""
    ex = analysis.get("extras", {})
    fall = ex.get("fall_risk", {}).get("level", "low")
    sat_mode = ex.get("saturn_career", {}).get("mode", "mixed")
    lagna_score = analysis.get("d10_lagna_score", 0)
    h10 = analysis.get("h10_score", 0)
    up = ex.get("upachaya", {}).get("strong", False)

    if fall == "high" or sat_mode == "service":
        return "steady"
    if up and lagna_score >= 1 and h10 >= 0:
        return "early_rise"
    if lagna_score <= -1 or h10 <= -1:
        return "late_bloom"
    return "steady"


def _chart_tone_scores(tone: str) -> dict[int, float]:
    if tone == "early_rise":
        return {24: 4.0, 26: 5.0, 28: 4.0, 30: 3.0}
    if tone == "late_bloom":
        return {32: 4.0, 35: 5.0, 38: 5.0, 40: 4.0, 28: 2.0}
    return {26: 4.0, 28: 5.0, 30: 5.0, 32: 4.0, 35: 3.0}


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


def _ad_career_weight(
    ad_lord: str, md_lord: str,
    common: set[str], d1_set: set[str], d10_set: set[str],
) -> tuple[int, str]:
    if ad_lord in common:
        if md_lord in common:
            return 8, "common AD inside common MD"
        return 6, "common career planet antardasha"
    if ad_lord in d10_set:
        if md_lord in common:
            return 4, "dashamsha graha AD, common MD"
        return 3, "dashamsha career house graha antardasha"
    if ad_lord in d1_set:
        return 2, "birth tenth-house significator antardasha"
    if md_lord in common and ad_lord in BENEFICS:
        return 2, "benefic AD under career MD"
    return 0, ""


def _score_milestone_ages(
    dob: date,
    all_ads: list[dict],
    common: set[str],
    d1_set: set[str],
    d10_set: set[str],
    age_tone: str,
) -> tuple[dict[int, float], list[dict]]:
    tone_base = _chart_tone_scores(age_tone)
    scores: dict[int, float] = dict(tone_base)
    periods: list[dict] = []

    for ad in all_ads:
        try:
            start = datetime.strptime(ad["start"][:10], "%Y-%m-%d").date()
            end = datetime.strptime(ad["end"][:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        a0 = _age_between(dob, start)
        a1 = _age_between(dob, end)
        if a1 < 18 or a0 > 55:
            continue
        w, reason = _ad_career_weight(ad["ad_lord"], ad["md_lord"], common, d1_set, d10_set)
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


def _top_ages(scores: dict[int, float], n: int = 5, min_score: float = 3.0) -> list[int]:
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    out = [age for age, sc in ranked if sc >= min_score][:n]
    return out or ([ranked[0][0]] if ranked else [])


def _primary_period(periods: list[dict], display_ages: list[int]) -> dict | None:
    if not periods:
        return None
    targets = display_ages[:4]
    center = targets[len(targets) // 2] if targets else 30

    def score(p: dict) -> float:
        s = float(p["weight"])
        if any(p["age_start"] - 1 <= t <= p["age_end"] + 1 for t in targets):
            s += 10.0
        if p["lord"] in {"Sun", "Saturn", "Mercury"} and "common" in p.get("reason", ""):
            s += 2.0
        if p["lord"] == p["md_lord"]:
            s -= 2.0
        s -= abs(p["mid_age"] - center) * 0.35
        return s

    return max(periods, key=score)


def compute_career_timing(pc: dict, analysis: dict) -> dict[str, Any]:
    d1_set = _d1_career_set(pc, analysis)
    d10_set = _d10_career_set(analysis)
    common = sorted(d1_set & d10_set)
    age_tone = _classify_age_tone(analysis)
    dob = _parse_dob(pc)

    all_ads = _all_antardashas(pc)
    milestone_scores: dict[int, float] = {}
    periods: list[dict] = []
    if dob:
        milestone_scores, periods = _score_milestone_ages(
            dob, all_ads, set(common), d1_set, d10_set, age_tone,
        )

    potential_ages = _top_ages(milestone_scores)
    display_ages = sorted(potential_ages[:5])
    primary_period = _primary_period(periods, display_ages)

    return {
        "d1_significators": sorted(d1_set),
        "d10_significators": sorted(d10_set),
        "common_significators": common,
        "age_tone": age_tone,
        "potential_ages": potential_ages,
        "display_ages": display_ages,
        "milestone_scores": milestone_scores,
        "career_periods": periods,
        "primary_period": primary_period,
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
    ages = timing.get("display_ages") or sorted(timing.get("potential_ages", []))
    common = timing.get("common_significators", [])
    primary = timing.get("primary_period")
    tone = timing.get("age_tone", "steady")

    parts: list[str] = []
    if ages:
        parts.append(f"Likely career peak or job-change ages in this chart: {_format_age_list(ages)}.")
    if primary:
        a0, a1 = primary["age_start"], primary["age_end"]
        lord, md = primary.get("lord", ""), primary.get("md_lord", "")
        if a0 != a1:
            parts.append(
                f"Strongest dasha support at age {a0}-{a1} ({lord} antardasha"
                + (f", {md} mahadasha" if md and md != lord else "")
                + ")."
            )
        else:
            parts.append(f"Strongest dasha support at age {a0} ({lord} period).")

    if tone == "late_bloom":
        parts.append("Afflicted dashamsha or service-tone Saturn pushes visible rise toward the mid-thirties unless an earlier common-planet dasha intervenes.")
    elif tone == "early_rise":
        parts.append("Upachaya and dashamsha lagna support allow an earlier name - twenties and early thirties can carry promotion or self-employment.")
    else:
        parts.append("Birth tenth house and dashamsha cooperate - career builds in steady steps when shared career dasha runs.")

    if common:
        joined = ", ".join(common[:-1]) + f" and {common[-1]}" if len(common) > 1 else common[0]
        parts.append(f"Key timing planets (shared in birth chart and dashamsha): {joined}.")

    parts.append("Fine-tune the month when Saturn or Jupiter transits your tenth house or dashamsha tenth lord during these dasha years.")
    return " ".join(parts)
