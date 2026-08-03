#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Goel D9 confluence - predictions only when >= 70% of relevant lanes agree."""
from __future__ import annotations

from typing import Any

CONFLUENCE_MIN = 70

THEMES: dict[str, dict] = {
    "marriage_quality": {
        "title": "Marriage quality (D9 outcome)",
        "core_lanes": ["Karaka D9", "D9 7th lord", "D9 7th", "D1 vs D9", "Flags"],
        "prediction": (
            "Partnership matures into a solid long-term bond when D9 karaka is strong - "
            "Goel treats D9 as the final marriage tone, not the first impression from D1."
        ),
        "prevent": "Invest in trust and routine after wedding; do not judge union only by early D1 chemistry.",
    },
    "marriage_promise": {
        "title": "Marriage promise",
        "core_lanes": ["D9 lagna", "D9 7th", "Karaka D1", "Denial check"],
        "prediction": (
            "Marriage is promised in the chart: D9 lagna and seventh axis support union rather than denial."
        ),
        "prevent": "Choose timing when dasha supports Venus/Jupiter and 7th lord; avoid fear-based delay.",
    },
    "marriage_strain": {
        "title": "Marital strain / sustainability watch",
        "core_lanes": ["D9 7th lord", "D9 4th", "D9 7th", "Denial check", "Flags"],
        "prediction": (
            "Domestic or partnership stress can recur when D9 seventh lord or fourth house is under malefic load - "
            "discipline and honest talk matter more than dramatic exits."
        ),
        "prevent": "Couple counselling early; protect home peace; Saturn-style patience on 4th-house themes.",
    },
    "d1_d9_improvement": {
        "title": "Life improves in second half (D9 stronger than D1)",
        "core_lanes": ["D1 vs D9", "Karaka D9", "D9 lagna", "Flags"],
        "prediction": (
            "Goel's D1-vs-D9 rule: what looks weak or debilitated in the birth chart can deliver better "
            "results after marriage or mid-life when the navamsha layer is strong."
        ),
        "prevent": "Do not write off Jupiter/Venus periods early; build habits that match your strong D9 signs.",
    },
    "spiritual_dharma": {
        "title": "Spiritual / dharma inclination (D9 trines)",
        "core_lanes": ["D9 9th", "Jupiter D9", "D9 lagna", "Flags"],
        "prediction": (
            "D9 ninth and Jupiter themes point to growing devotion, pilgrimage, or guru-centred practice "
            "alongside worldly life."
        ),
        "prevent": "Regular quiet practice; support teachers; avoid mixing spirituality with escapism.",
    },
    "partnership_foreign": {
        "title": "Partner from different background / foreign link",
        "core_lanes": ["DK foreign", "Karaka D9", "D9 12th", "Flags"],
        "prediction": (
            "D9 twelfth-house or nodal karaka patterns can draw a spouse from another region, culture, "
            "or social background (Goel + DK themes)."
        ),
        "prevent": "Respect both families' customs; legal clarity if cross-border.",
    },
    "marriage_timing": {
        "title": "Marriage-friendly dasha windows",
        "core_lanes": ["Dasha timing", "Karaka D9", "D9 7th lord", "D9 lagna lord"],
        "prediction": (
            "Union or formal commitment tends to crystallise when dasha touches Venus, Jupiter, "
            "or the D9 lagna/7th lords (Goel Ch.5 - triangulate with transits)."
        ),
        "prevent": "Use these windows for engagement/marriage decisions; avoid forced timing outside them.",
    },
    "beeja_strength": {
        "title": "Dasha fruits stronger via Beeja (Rashi Tulya D9)",
        "core_lanes": ["Beeja", "D1 vs D9", "Karaka D9", "Flags"],
        "prediction": (
            "Several planets sit in kendra/trikona of D1 when mapped through D9 signs - Goel's Beeja rule: "
            "mahadasha results deliver more reliably for those grahas."
        ),
        "prevent": "Prioritise career/dharma actions aligned with strong Beeja planets in their dasha.",
    },
    "vish_period_caution": {
        "title": "Vish navamsha dasha - karakatwa under strain",
        "core_lanes": ["Vish dasha", "Flags", "Denial check", "D9 7th lord"],
        "prediction": (
            "Planets in vish navamsha can hurt their significations during their dasha (Goel Ch.7) - "
            "extra care in those life areas when the period runs."
        ),
        "prevent": "Remedies for the afflicted karaka; do not take major risks in that domain in peak dasha.",
    },
    "multiple_relations": {
        "title": "Multiple partnerships / affair tendency",
        "core_lanes": ["Multiple Ch4", "D9 lagna lord", "2nd lord D9", "Jupiter D9"],
        "prediction": (
            "Goel Ch.4 flags suggest more than one serious bond or parallel attraction is possible - "
            "values (2nd house) and afflicted Jupiter in D9 weaken single-partner permanence."
        ),
        "prevent": "Clear boundaries; strengthen Jupiter practices; avoid hidden parallel ties.",
    },
}


def build_navamsha_confluence(analysis: dict[str, Any], pc: dict | None = None) -> dict[str, Any]:
    if analysis.get("error"):
        return {"min_pct": CONFLUENCE_MIN, "predictions": [], "snapshot": {}}

    pc = pc or {}
    d9_lagna = analysis.get("d9_lagna", "")
    houses = analysis.get("d9_houses", {})
    enriched = analysis.get("d9_enriched", {})
    venus = enriched.get("Venus", {})
    jupiter = enriched.get("Jupiter", {})
    lord7 = analysis.get("lord7_d9", "")
    l7 = enriched.get(lord7, {})
    flags = analysis.get("flags", [])
    denial = analysis.get("denial_hits", [])
    trajectory = analysis.get("trajectory", [])
    aff_7lord = analysis.get("aff_7lord", False)
    marriage_windows = analysis.get("marriage_windows", [])
    beeja_strong = analysis.get("beeja_strong", [])
    vish_dasha = analysis.get("vish_dasha", [])
    multiple_signals = analysis.get("multiple_signals", [])
    dk_foreign = analysis.get("dk_foreign", [])
    d9_lagna_lord = analysis.get("d9_lagna_lord", "")
    d9_ll = enriched.get(d9_lagna_lord, {})
    lord2_d1 = analysis.get("lord2_d1", "")
    lord2_d9 = enriched.get(lord2_d1, {}) if lord2_d1 else {}

    def _lane_d9_lagna(_tid: str) -> tuple[bool, str]:
        h1 = houses.get(1, [])
        if d9_lagna in ("Taurus", "Libra", "Cancer", "Pisces"):
            return True, f"{d9_lagna} lagna (benefic-ruled tone)"
        if len(h1) >= 2:
            return True, f"{len(h1)} grahas in D9 lagna"
        return d9_lagna in ("Aries", "Leo", "Sagittarius"), d9_lagna

    def _lane_d9_7th(tid: str) -> tuple[bool, str]:
        h7 = houses.get(7, [])
        if tid == "marriage_strain" and (h7 and any(p in {"Saturn", "Rahu", "Ketu", "Mars", "Sun"} for p in h7)):
            return True, f"malefics in D9 7th: {h7}"
        if tid in ("marriage_promise", "marriage_quality") and not h7:
            return True, "D9 7th empty - lord carries promise"
        ben = sum(1 for p in h7 if p in {"Venus", "Jupiter", "Moon", "Mercury"})
        if tid == "marriage_promise" and ben:
            return True, f"benefics in D9 7th: {h7}"
        return bool(h7), str(h7)

    def _lane_karaka_d9(tid: str) -> tuple[bool, str]:
        hits = []
        for label, k in (("Venus", venus), ("Jupiter", jupiter)):
            if not k:
                continue
            strong = k.get("d9_dignity") in ("exalted", "own_sign", "moolatrikona")
            weak = k.get("d9_dignity") in ("debilitated", "enemy_sign")
            if tid == "marriage_quality" and strong:
                hits.append(f"{label} exalted/strong in D9 H{k['d9_house']}")
            elif tid == "marriage_strain" and weak:
                hits.append(f"{label} weak in D9")
            elif tid == "partnership_foreign" and k.get("d9_house") in (12, 9):
                hits.append(f"{label} in D9 H{k['d9_house']}")
            elif tid == "d1_d9_improvement" and k.get("d1_dignity") == "debilitated" and strong:
                hits.append(f"{label} D1 debil -> D9 strong")
        return bool(hits), "; ".join(hits)

    def _lane_karaka_d1(tid: str) -> tuple[bool, str]:
        v_strong = venus.get("d1_dignity") in ("exalted", "own_sign", "moolatrikona")
        return v_strong or jupiter.get("d1_dignity") in ("exalted", "own_sign"), "D1 karaka dignity"

    def _lane_7th_lord(tid: str) -> tuple[bool, str]:
        if not l7:
            return False, ""
        h = l7.get("d9_house", 0)
        dig = l7.get("d9_dignity", "")
        if tid == "marriage_strain":
            return aff_7lord or dig in ("debilitated", "enemy_sign") or h in (6, 8, 12), f"{lord7} in D9 H{h}"
        return dig in ("exalted", "own_sign", "moolatrikona", "friendly_sign") or h in (1, 4, 7, 10, 11), f"{lord7} in D9 H{h}"

    def _lane_d9_4th(tid: str) -> tuple[bool, str]:
        h4 = houses.get(4, [])
        if tid == "marriage_strain" and any(p in {"Saturn", "Rahu", "Mars"} for p in h4):
            return True, f"stress grahas in D9 4th: {h4}"
        return not h4 or any(p in {"Venus", "Jupiter", "Moon"} for p in h4), str(h4 or "empty")

    def _lane_d9_9th(tid: str) -> tuple[bool, str]:
        h9 = houses.get(9, [])
        return bool(h9), str(h9)

    def _lane_d9_12th(tid: str) -> tuple[bool, str]:
        h12 = houses.get(12, [])
        if venus.get("d9_house") == 12:
            return True, "Venus in D9 12th (exaltation zone / bed pleasure)"
        return bool(h12), str(h12)

    def _lane_d1_vs_d9(tid: str) -> tuple[bool, str]:
        return bool(trajectory), "; ".join(trajectory[:2])

    def _lane_denial(tid: str) -> tuple[bool, str]:
        if tid == "marriage_promise":
            return len(denial) == 0, "no denial rule triggered" if not denial else denial[0]
        if tid == "marriage_strain":
            return bool(denial), "; ".join(denial[:2])
        return not denial, "clear"

    def _lane_flags(tid: str) -> tuple[bool, str]:
        if tid == "marriage_quality" and any("pushkar" in f for f in flags):
            return True, next(f for f in flags if "pushkar" in f)
        if tid in ("marriage_strain", "vish_period_caution") and any("vish" in f for f in flags):
            return True, next(f for f in flags if "vish" in f)
        if tid == "spiritual_dharma" and any("Jupiter" in f for f in flags):
            return True, "Jupiter flag"
        if tid == "d1_d9_improvement" and any("vargottama" in f for f in flags):
            return True, next(f for f in flags if "vargottama" in f)
        return bool(flags), flags[0] if flags else ""

    def _lane_dk_foreign(tid: str) -> tuple[bool, str]:
        return bool(dk_foreign), "; ".join(dk_foreign[:2])

    def _lane_dasha_timing(tid: str) -> tuple[bool, str]:
        if not marriage_windows:
            return False, ""
        w = marriage_windows[0]
        return True, f"{w['lord']} {w['range']} ({w.get('status', '')})"

    def _lane_beeja(tid: str) -> tuple[bool, str]:
        return len(beeja_strong) >= 3, f"{len(beeja_strong)} planets in D1 kendra/trikona via D9"

    def _lane_vish_dasha(tid: str) -> tuple[bool, str]:
        return bool(vish_dasha), vish_dasha[0] if vish_dasha else ""

    def _lane_multiple_ch4(tid: str) -> tuple[bool, str]:
        return len(multiple_signals) >= 2, "; ".join(multiple_signals[:2])

    def _lane_d9_lagna_lord(tid: str) -> tuple[bool, str]:
        if not d9_ll:
            return False, ""
        if tid == "multiple_relations":
            special = d9_ll.get("vargottama") or d9_ll.get("d9_dignity") in (
                "exalted", "debilitated", "own_sign",
            )
            return special, f"{d9_lagna_lord} in D9 H{d9_ll.get('d9_house')} ({d9_ll.get('d9_dignity')})"
        return d9_ll.get("d9_dignity") not in ("debilitated", "enemy_sign"), f"{d9_lagna_lord} D9 H{d9_ll.get('d9_house')}"

    def _lane_2nd_lord_d9(tid: str) -> tuple[bool, str]:
        if not lord2_d9:
            return False, ""
        weak = lord2_d9.get("d9_house") in (6, 8, 12) or lord2_d9.get("d9_dignity") in ("debilitated", "enemy_sign")
        return weak if tid == "multiple_relations" else not weak, f"{lord2_d1} in D9 H{lord2_d9.get('d9_house')}"

    def _lane_jupiter_d9(tid: str) -> tuple[bool, str]:
        if not jupiter:
            return False, ""
        aff = jupiter.get("d9_dignity") in ("debilitated", "enemy_sign") or jupiter.get("retrograde")
        if tid == "multiple_relations":
            return aff and jupiter.get("d9_house") in (1, 7, 10), f"Jupiter D9 H{jupiter.get('d9_house')}"
        return not aff, f"Jupiter D9 H{jupiter.get('d9_house')}"

    evaluators = {
        "D9 lagna": _lane_d9_lagna,
        "D9 7th": _lane_d9_7th,
        "Karaka D9": _lane_karaka_d9,
        "Karaka D1": _lane_karaka_d1,
        "D9 7th lord": _lane_7th_lord,
        "D9 4th": _lane_d9_4th,
        "D9 9th": _lane_d9_9th,
        "D9 12th": _lane_d9_12th,
        "D1 vs D9": _lane_d1_vs_d9,
        "Denial check": _lane_denial,
        "Flags": _lane_flags,
        "DK foreign": _lane_dk_foreign,
        "Dasha timing": _lane_dasha_timing,
        "Beeja": _lane_beeja,
        "Vish dasha": _lane_vish_dasha,
        "Multiple Ch4": _lane_multiple_ch4,
        "D9 lagna lord": _lane_d9_lagna_lord,
        "2nd lord D9": _lane_2nd_lord_d9,
        "Jupiter D9": _lane_jupiter_d9,
    }

    scored: list[dict] = []
    for tid, spec in THEMES.items():
        core = spec["core_lanes"]
        hits: list[str] = []
        for lane in core:
            ev = evaluators.get(lane)
            if not ev:
                continue
            ok, detail = ev(tid)
            if ok:
                hits.append(f"{lane}: {detail}" if detail else lane)

        total = len(core)
        pct = round(100 * len(hits) / total) if total else 0
        if pct < CONFLUENCE_MIN:
            continue

        scored.append({
            "theme_id": tid,
            "title": spec["title"],
            "match_pct": pct,
            "prediction": spec["prediction"],
            "preventive": spec["prevent"],
            "lanes_hit": hits,
            "lanes_total": total,
        })

    scored.sort(key=lambda x: (-x["match_pct"], x["title"]))
    focus = ", ".join(p["title"] for p in scored[:3]) or "None at 70%+ agreement."
    snap = {
        "d9_lagna": f"D9 lagna {d9_lagna} (D1 {analysis.get('d1_lagna', '')} rising).",
        "karaka": analysis.get("marriage_karaka", [""])[0] if analysis.get("marriage_karaka") else "",
        "focus": focus,
    }
    return {"min_pct": CONFLUENCE_MIN, "predictions": scored[:4], "snapshot": snap}
