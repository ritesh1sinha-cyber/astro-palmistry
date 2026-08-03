#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Goel Predict with Saptamsha - childbirth timing (Ch.9 Vimshottari).

Book rules:
  D1: 5th house, 5th lord, Jupiter (Putra karaka)
  D7 dynamic houses: lagna, 2nd, 5th, 9th, 10th + their lords
  Common grahas -> childbirth in their MD/AD (confirm D1 + D7 relation)

Age bands from chart tone + full-life dasha scan (milestone ages, not future-only).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from astro_precompute import VIMSH_LORDS, build_antardashas

MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
BENEFICS = {"Moon", "Mercury", "Jupiter", "Venus"}

MILESTONE_AGES = (24, 26, 28, 30, 32, 35, 38, 40)


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


def _d1_children_set(pc: dict, analysis: dict) -> set[str]:
    planets = pc.get("planets", {})
    s = set()
    l5 = analysis.get("lord5_d1", "")
    if l5:
        s.add(l5)
    for p in analysis.get("d1_h5_planets", []):
        s.add(p)
    s.add("Jupiter")
    return {p for p in s if p in planets}


def _d7_children_set(analysis: dict) -> set[str]:
    houses = analysis.get("d7_houses", {})
    s: set[str] = set()
    for h in (1, 2, 5, 9, 10):
        s.update(houses.get(h, []))
    if analysis.get("d7_lagna_lord"):
        s.add(analysis["d7_lagna_lord"])
    if analysis.get("lord5_d7"):
        s.add(analysis["lord5_d7"])
    if analysis.get("lord9_d7"):
        s.add(analysis["lord9_d7"])
    return s


def _classify_age_tone(analysis: dict) -> str:
    """early | timely | late from Goel D7 Saturn delay + denial signals."""
    if analysis.get("denial_hits"):
        return "late"
    if analysis.get("saturn_delay"):
        return "late" if not analysis.get("saturn_delay_relief") else "timely"
    lagna_score = analysis.get("d7_lagna_score", 0)
    if lagna_score >= 1:
        return "timely"
    if lagna_score <= -1:
        return "late"
    return "timely"


def _chart_tone_scores(tone: str) -> dict[int, float]:
    if tone == "early":
        return {24: 4.0, 26: 5.0, 28: 3.0}
    if tone == "late":
        return {30: 4.0, 32: 5.0, 35: 6.0, 38: 4.0, 28: 2.0}
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


def _ad_weight(ad_lord: str, md_lord: str, common: set[str], d1: set[str], d7: set[str]) -> tuple[int, str]:
    if ad_lord in common:
        if md_lord in common:
            return 8, "common AD inside common MD"
        return 6, "common progeny planet antardasha"
    if ad_lord in d7:
        if md_lord in common:
            return 4, "saptamsha graha AD, common MD"
        return 3, "saptamsha house graha antardasha"
    if ad_lord in d1:
        return 2, "birth-chart fifth/Jupiter link antardasha"
    if md_lord in common:
        return 1, "common planet mahadasha"
    return 0, ""


def _score_milestone_ages(
    dob: date, all_ads: list[dict], common: set[str], d1: set[str], d7: set[str], tone: str,
    min_age: int = 22, max_age: int = 45,
) -> tuple[dict[int, float], list[dict]]:
    scores: dict[int, float] = {a: 0.0 for a in MILESTONE_AGES}
    for age, w in _chart_tone_scores(tone).items():
        if age in scores:
            scores[age] += w

    periods: list[dict] = []
    for ad in all_ads:
        try:
            start = date.fromisoformat(ad["start"][:10])
            end = date.fromisoformat(ad["end"][:10])
        except ValueError:
            continue
        age_start = _age_between(dob, start)
        age_end = _age_between(dob, end)
        if age_end < min_age or age_start > max_age:
            continue
        weight, reason = _ad_weight(ad["ad_lord"], ad["md_lord"], common, d1, d7)
        if weight == 0:
            continue
        mid = start + (end - start) // 2
        periods.append({
            "lord": ad["ad_lord"],
            "md_lord": ad["md_lord"],
            "range": ad["range"],
            "age_start": age_start,
            "age_end": age_end,
            "mid_age": _age_between(dob, mid),
            "weight": weight,
            "reason": reason,
        })
        for milestone in MILESTONE_AGES:
            if age_start - 1 <= milestone <= age_end + 1:
                scores[milestone] += weight
            elif abs(milestone - _age_between(dob, mid)) <= 2:
                scores[milestone] += weight * 0.6
    return scores, periods


def _top_ages(scores: dict[int, float], n: int = 5, min_score: float = 3.0) -> list[int]:
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    out = [age for age, sc in ranked if sc >= min_score][:n]
    return out or ([ranked[0][0]] if ranked else [])


def _primary_period(periods: list[dict], display_ages: list[int]) -> dict | None:
    if not periods:
        return None
    targets = display_ages[:4]
    center = targets[len(targets) // 2] if targets else 28

    def score(p: dict) -> float:
        s = float(p["weight"])
        if any(p["age_start"] - 1 <= t <= p["age_end"] + 1 for t in targets):
            s += 10.0
        if p["lord"] in {"Jupiter", "Venus"} and "common" in p.get("reason", ""):
            s += 2.0
        if p["lord"] == p["md_lord"]:
            s -= 3.0
        s -= abs(p["mid_age"] - center) * 0.4
        return s

    return max(periods, key=score)


def compute_children_timing(pc: dict, analysis: dict) -> dict[str, Any]:
    d1_set = _d1_children_set(pc, analysis)
    d7_set = _d7_children_set(analysis)
    common = sorted(d1_set & d7_set)
    age_tone = _classify_age_tone(analysis)
    dob = _parse_dob(pc)

    all_ads = _all_antardashas(pc)
    milestone_scores: dict[int, float] = {}
    periods: list[dict] = []
    if dob:
        milestone_scores, periods = _score_milestone_ages(
            dob, all_ads, set(common), d1_set, d7_set, age_tone,
        )

    potential_ages = _top_ages(milestone_scores)
    display_ages = sorted(potential_ages[:4])
    primary_period = _primary_period(periods, display_ages)

    return {
        "d1_significators": sorted(d1_set),
        "d7_significators": sorted(d7_set),
        "common_significators": common,
        "age_tone": age_tone,
        "potential_ages": potential_ages,
        "display_ages": display_ages,
        "milestone_scores": milestone_scores,
        "child_periods": periods,
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
    tone = timing.get("age_tone", "timely")

    parts: list[str] = []
    if ages:
        parts.append(f"Likely ages for childbirth in this chart: {_format_age_list(ages)}.")
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

    if tone == "late":
        parts.append("Saturn or denial patterns on saptamsha push conception toward the thirties unless an earlier Jupiter/Venus dasha intervenes.")
    elif tone == "early":
        parts.append("Fifth-house and saptamsha pattern allows children in the mid-twenties when the right dasha runs.")
    else:
        parts.append("Birth fifth house and saptamsha cooperate - children fit the usual adult band when progeny dasha activates.")

    if common:
        joined = ", ".join(common[:-1]) + f" and {common[-1]}" if len(common) > 1 else common[0]
        parts.append(f"Key timing planets (shared in birth chart and saptamsha): {joined}.")

    parts.append("Fine-tune the month when Jupiter transits your fifth house or saptamsha lagna lord during these dasha years.")
    return " ".join(parts)
