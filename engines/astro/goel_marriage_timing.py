#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Goel Predict with Navamsha - marriage timing (Ch.5 + early/timely/late from Ch.2).

Book rules (generic):
  D1 marriage set: 7th occupants/aspects, 7th lord, Venus/Jupiter karakas
  D9 marriage set: lagna, 2nd, 7th, 10th + lords of lagna and 7th
  Intersection (common grahas) -> marriage in their Vimshottari MD/AD

Age bands (Ch.2):
  Early: D1 lagna planet also on/aspects D30 lagna -> teens / early 20s
  Timely: benefic link on D1 7th AND D9 7th; marriage dasha at social age -> ~21-28
  Late: malefic 7th load, dasha misses standard age, D9 lagna reluctance -> 30+

Client output uses milestone ages (20, 25, 30, 35, 40) scored from chart tone
+ full-life dasha scan (past and future), not only the next upcoming window.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from astro_precompute import VIMSH_LORDS, build_antardashas

MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
BENEFICS = {"Moon", "Mercury", "Jupiter", "Venus"}

# Client-facing milestone ages (Goel social bands + book examples: 16, 21, 33, 40)
MILESTONE_AGES = (20, 22, 25, 27, 28, 30, 32, 35, 38, 40)


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


def _d1_marriage_set(pc: dict, analysis: dict) -> set[str]:
    planets = pc.get("planets", {})
    l7 = analysis.get("lord7_d1", "")
    s = set()
    if l7:
        s.add(l7)
    for p in analysis.get("d1_h7_planets", []):
        s.add(p)
    s.update({"Venus", "Jupiter"})
    return {p for p in s if p in planets}


def _d9_marriage_set(analysis: dict) -> set[str]:
    houses = analysis.get("d9_houses", {})
    s: set[str] = set()
    for h in (1, 2, 7, 10):
        s.update(houses.get(h, []))
    if analysis.get("d9_lagna_lord"):
        s.add(analysis["d9_lagna_lord"])
    if analysis.get("lord7_d9"):
        s.add(analysis["lord7_d9"])
    return s


def _classify_age_tone(pc: dict, analysis: dict) -> str:
    """Return early | timely | late per Goel Ch.2."""
    d1_h7 = analysis.get("d1_h7_planets", [])
    d9_h7 = analysis.get("d9_houses", {}).get(7, [])
    aff_d1 = sum(1 for p in d1_h7 if p in MALEFICS)
    ben_d1 = sum(1 for p in d1_h7 if p in BENEFICS)
    ben_d9 = sum(1 for p in d9_h7 if p in BENEFICS)

    l7d9 = analysis.get("lord7_d9", "")
    enriched = analysis.get("d9_enriched", {}).get(l7d9, {})
    if not d9_h7 and enriched.get("d9_dignity") in ("exalted", "own_sign", "moolatrikona", "friendly_sign"):
        ben_d9 += 1

    d9_h1 = analysis.get("d9_houses", {}).get(1, [])
    malefic_lagna = sum(1 for p in d9_h1 if p in MALEFICS) > sum(1 for p in d9_h1 if p in BENEFICS)

    if aff_d1 >= 2 and ben_d9 == 0 and malefic_lagna:
        return "late"
    if aff_d1 >= 1 and ben_d1 == 0 and ben_d9 == 0:
        return "late"
    if ben_d1 + ben_d9 >= 1 or (not d1_h7 and analysis.get("lord7_d1") in BENEFICS):
        if aff_d1 <= 1 and not malefic_lagna:
            return "timely"
    if malefic_lagna and aff_d1 >= 1:
        return "late"
    return "timely"


def _chart_tone_scores(tone: str) -> dict[int, float]:
    """Baseline age weights from Goel early / timely / late pattern."""
    if tone == "early":
        return {20: 4.0, 22: 5.0, 25: 3.0, 18: 2.0}
    if tone == "late":
        return {30: 4.0, 32: 5.0, 35: 6.0, 38: 4.0, 40: 5.0, 25: 1.5}
    return {25: 5.0, 27: 4.0, 28: 5.0, 30: 4.0, 22: 2.5, 32: 2.0}


def _all_antardashas(pc: dict) -> list[dict]:
    """Every MD/AD period across the full Vimshottari sequence."""
    vim = pc.get("vimshottari", {})
    out: list[dict] = []
    for md in vim.get("sequence", []):
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


def _ad_marriage_weight(
    ad_lord: str, md_lord: str,
    common: set[str], d1_set: set[str], d9_set: set[str],
) -> tuple[int, str]:
    """Score how strongly this AD carries marriage timing (Goel common-planet rule)."""
    if ad_lord in common:
        if md_lord in common:
            return 8, "common AD inside common MD"
        return 6, "common marriage planet antardasha"
    if ad_lord in d9_set:
        if md_lord in common:
            return 4, "navamsha marriage graha AD, common MD"
        return 3, "navamsha marriage house graha antardasha"
    if ad_lord in d1_set:
        return 2, "birth-chart marriage link antardasha"
    if md_lord in common:
        return 1, "common planet mahadasha (weaker alone)"
    return 0, ""


def _score_milestone_ages(
    dob: date,
    all_ads: list[dict],
    common: set[str],
    d1_set: set[str],
    d9_set: set[str],
    tone: str,
    min_age: int = 18,
    max_age: int = 45,
) -> tuple[dict[int, float], list[dict]]:
    """Score standard ages 20-40 from chart tone + every marriage-related dasha."""
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

        weight, reason = _ad_marriage_weight(
            ad["ad_lord"], ad["md_lord"], common, d1_set, d9_set,
        )
        if weight == 0:
            continue

        mid = start + (end - start) // 2
        mid_age = _age_between(dob, mid)
        periods.append({
            "lord": ad["ad_lord"],
            "md_lord": ad["md_lord"],
            "range": ad["range"],
            "age_start": age_start,
            "age_end": age_end,
            "mid_age": mid_age,
            "weight": weight,
            "reason": reason,
        })

        for milestone in MILESTONE_AGES:
            if age_start - 1 <= milestone <= age_end + 1:
                scores[milestone] += weight
            elif abs(milestone - mid_age) <= 2:
                scores[milestone] += weight * 0.6

    return scores, periods


def _top_ages(scores: dict[int, float], n: int = 4, min_score: float = 3.0) -> list[int]:
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    out = [age for age, sc in ranked if sc >= min_score][:n]
    if not out and ranked:
        out = [ranked[0][0]]
    return out


def _age_range_label(ages: list[int]) -> str:
    if not ages:
        return ""
    if len(ages) == 1:
        return f"around age {ages[0]}"
    lo, hi = min(ages), max(ages)
    if hi - lo <= 3:
        return f"around age {lo}-{hi}"
    primary = ages[:3]
    return "around age " + ", ".join(str(a) for a in primary[:-1]) + f", and {primary[-1]}"


def _group_periods(periods: list[dict], top_ages: list[int]) -> list[dict]:
    """Periods that best explain the top milestone ages."""
    if not top_ages:
        return sorted(periods, key=lambda x: -x["weight"])[:3]
    target = set(top_ages)
    matched = [
        p for p in periods
        if any(p["age_start"] - 1 <= a <= p["age_end"] + 1 for a in target)
    ]
    matched.sort(key=lambda x: (-x["weight"], x["age_start"]))
    return matched[:4]


def compute_marriage_timing(pc: dict, analysis: dict) -> dict[str, Any]:
    d1_set = _d1_marriage_set(pc, analysis)
    d9_set = _d9_marriage_set(analysis)
    common = sorted(d1_set & d9_set)
    age_tone = _classify_age_tone(pc, analysis)
    dob = _parse_dob(pc)
    age_now = pc.get("meta", {}).get("age", 0)

    all_ads = _all_antardashas(pc)
    milestone_scores: dict[int, float] = {}
    marriage_periods: list[dict] = []

    if dob:
        milestone_scores, marriage_periods = _score_milestone_ages(
            dob, all_ads, set(common), d1_set, d9_set, age_tone,
        )

    potential_ages = _top_ages(milestone_scores, n=5)
    display_ages = sorted(potential_ages[:4])
    supporting_periods = _group_periods(marriage_periods, potential_ages)
    primary_period = _primary_period(
        supporting_periods or marriage_periods,
        display_ages or sorted(potential_ages),
    )

    age_label = _age_range_label(potential_ages)
    if not age_label:
        age_label = {
            "early": "early twenties or before",
            "timely": "mid-twenties when marriage dasha runs",
            "late": "thirties or later",
        }.get(age_tone, "when marriage dasha runs")

    return {
        "d1_significators": sorted(d1_set),
        "d9_significators": sorted(d9_set),
        "common_significators": common,
        "age_tone": age_tone,
        "age_label": age_label,
        "potential_ages": potential_ages,
        "display_ages": display_ages,
        "milestone_scores": milestone_scores,
        "marriage_periods": marriage_periods,
        "supporting_periods": supporting_periods,
        "primary_period": primary_period,
        "age_now": age_now,
        # legacy keys for coverage / analysis hooks
        "windows": supporting_periods,
        "primary_window": primary_period,
    }


def _format_age_list(ages: list[int]) -> str:
    if not ages:
        return ""
    if len(ages) == 1:
        return str(ages[0])
    if len(ages) == 2:
        return f"{ages[0]} and {ages[1]}"
    return ", ".join(str(a) for a in ages[:-1]) + f", and {ages[-1]}"


def _primary_period(periods: list[dict], display_ages: list[int]) -> dict | None:
    """Best dasha period explaining the top milestone ages (not only highest weight)."""
    if not periods:
        return None
    targets = display_ages[:4] if display_ages else []
    center = targets[len(targets) // 2] if targets else 28

    def score(p: dict) -> float:
        s = float(p["weight"])
        if any(p["age_start"] - 1 <= t <= p["age_end"] + 1 for t in targets):
            s += 10.0
        if p["lord"] in {"Venus", "Jupiter"} and "common" in p.get("reason", ""):
            s += 2.0
        if p["lord"] == p["md_lord"]:
            s -= 3.0
        s -= abs(p["mid_age"] - center) * 0.4
        return s

    return max(periods, key=score)


def _peak_range(period: dict | None) -> tuple[int, int] | None:
    if not period:
        return None
    return period["age_start"], period["age_end"]


def timing_client_paragraph(timing: dict[str, Any]) -> str:
    tone = timing.get("age_tone", "timely")
    ages = timing.get("display_ages") or sorted(timing.get("potential_ages", []))
    common = timing.get("common_significators", [])
    primary = timing.get("primary_period")
    peak = _peak_range(primary)

    parts: list[str] = []

    if ages:
        parts.append(
            f"Likely marriage ages for this chart: {_format_age_list(ages)}."
        )
    elif timing.get("age_label"):
        parts.append(f"Marriage age pattern: {timing['age_label']}.")

    if peak and primary:
        a0, a1 = peak
        lord = primary.get("lord", "")
        md = primary.get("md_lord", "")
        if a0 != a1:
            parts.append(
                f"Strongest dasha support at age {a0}-{a1} "
                f"({lord} antardasha"
                + (f", {md} mahadasha" if md and md != lord else "")
                + ")."
            )
        else:
            parts.append(f"Strongest dasha support at age {a0} ({lord} period).")

    if tone == "early":
        parts.append("Seventh-house and trimamsha pattern allows marriage before the usual social average.")
    elif tone == "late":
        parts.append("Seventh-house strain or navamsha reluctance pushes marriage toward the thirties unless an earlier dasha intervenes.")
    else:
        parts.append("Seventh house and navamsha both carry benefic marriage promise - union fits the normal adult band when the right dasha runs.")

    if common:
        joined = ", ".join(common[:-1]) + f" and {common[-1]}" if len(common) > 1 else common[0]
        parts.append(f"Key timing planets (shared in birth chart and navamsha): {joined}.")

    early_band = [a for a in ages if a <= 25]
    mid_band = [a for a in ages if 26 <= a <= 32]
    late_band = [a for a in ages if a >= 33]
    if early_band and mid_band:
        parts.append(
            f"Earlier window near age {_format_age_list(early_band[:2])}; "
            f"main window near age {_format_age_list(mid_band[:3])}."
        )
    elif mid_band and late_band:
        parts.append(
            f"Primary window near age {_format_age_list(mid_band[:3])}; "
            f"backup near age {_format_age_list(late_band[:2])}."
        )

    parts.append("Fine-tune the month when Jupiter or Saturn transits your Moon or seventh house during these dasha years.")
    return " ".join(parts)
