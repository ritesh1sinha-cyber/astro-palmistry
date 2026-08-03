#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Numerology marriage compatibility lane for kundali matching.

Sources: Woods rules23 (LP/SU High-Low, Relationship Number) +
Avasthi rules38 (compatibility triads, partner tips).
"""
from __future__ import annotations

from datetime import date
from typing import Any

from numerology_report import (
    AVASTHI_GROUPS,
    AVASTHI_THEME,
    avasthi_group,
    compute,
    reduce_num,
)

# Woods Life Path High/Low matrix (rules23 OCR p.93-94; symmetric; row 7 calibrated).
_LP_HIGH: dict[tuple[int, int], bool] = {}
_ROWS = {
    1: [1, 1, 1, 0, 0, 1, 1, 1, 0],
    2: [0, 1, 0, 1, 1, 1, 1, 1, 1],
    3: [0, 0, 0, 1, 0, 0, 0, 1, 1],
    4: [1, 0, 0, 1, 1, 1, 1, 0, 1],
    5: [0, 1, 0, 1, 0, 0, 0, 0, 0],
    6: [1, 0, 0, 1, 1, 0, 0, 1, 1],
    7: [1, 1, 0, 1, 0, 0, 1, 0, 1],
    8: [1, 0, 1, 0, 1, 0, 0, 0, 0],
    9: [0, 0, 1, 0, 0, 1, 1, 1, 0],
}
for i, row in _ROWS.items():
    for j, v in enumerate(row, 1):
        _LP_HIGH[(i, j)] = bool(v)
        _LP_HIGH[(j, i)] = bool(v)

# Soul Urge matrix not legible in OCR (p.95); reconstructed with SU1 calibration (High 1,4; Low 3,9).
_SU_HIGH: dict[tuple[int, int], bool] = {}
_SU_ROWS = {
    1: [1, 0, 0, 1, 0, 0, 0, 0, 0],
    2: [0, 1, 0, 1, 0, 1, 1, 1, 0],
    3: [0, 0, 1, 0, 0, 0, 0, 0, 0],
    4: [1, 1, 0, 1, 0, 0, 0, 1, 0],
    5: [0, 0, 0, 0, 1, 0, 0, 0, 0],
    6: [0, 1, 0, 0, 0, 1, 0, 0, 0],
    7: [0, 1, 0, 0, 0, 0, 1, 0, 0],
    8: [0, 1, 1, 1, 0, 0, 0, 1, 0],
    9: [0, 0, 0, 0, 0, 0, 0, 0, 1],
}
for i, row in _SU_ROWS.items():
    for j, v in enumerate(row, 1):
        _SU_HIGH[(i, j)] = bool(v)
        _SU_HIGH[(j, i)] = bool(v)

RELATIONSHIP_TEXT = {
    1: "Power-couple energy - thrive when you share a bold joint goal and keep future plans alive.",
    2: "Communication is the hinge - speak from the heart, listen back, and rebalance give-and-take.",
    3: "Playful, adventurous bond - keep spontaneity and fun in the routine or passion fades.",
    4: "Grounded, practical partnership - home chores, money and daily structure must stay fair.",
    5: "Needs freshness and healthy space - travel, novelty and room to breathe keep it alive.",
    6: "Sanctuary bond - nurture each other, but guard against one-sided caretaking.",
    7: "Deep soul connection - stay vulnerable; small-talk routines kill intimacy here.",
    8: "Power-and-money balance - regular honest check-ins so one partner does not dominate.",
    9: "Karmic completion theme - serve something larger together; take private time to reconnect.",
}

PARTNER_TIPS = {
    1: [
        "Respect their need to lead and decide - do not micromanage their initiatives.",
        "Be direct and confident; they respond to clarity, not passive hints.",
        "Give them room to shine publicly while you hold steady support privately.",
    ],
    2: [
        "Lead with empathy and reassurance - harsh tone lands harder than intended.",
        "Invite their feelings before offering fixes; listening is the main gift.",
        "Keep agreements gentle and consistent; sudden coldness shakes their trust.",
    ],
    3: [
        "Match their creative spark with encouragement, not criticism of fluff.",
        "Allow social expression and variety - boredom is their relationship poison.",
        "Laugh together often; lightness is how they repair after friction.",
    ],
    4: [
        "Honor reliability - show up on time and keep promises concrete.",
        "Discuss plans in an orderly way; last-minute chaos frustrates them.",
        "Be financially transparent; practical security is their love language.",
    ],
    5: [
        "Do not cage their freedom - trust and variety keep them engaged.",
        "Keep conversation lively and curious; mental stimulation matters.",
        "Plan small adventures; routine without novelty drains the bond.",
    ],
    6: [
        "Show affection through care - home, family and quality time count.",
        "Reciprocate nurturing; they give deeply but notice imbalance fast.",
        "Beauty and harmony at home prevent needless emotional flare-ups.",
    ],
    7: [
        "Respect solitude - alone time is not rejection.",
        "Go deep in conversation; superficial chatter feels empty to them.",
        "Share research, spirituality or a private hobby as couple glue.",
    ],
    8: [
        "Be straightforward about money, roles and authority.",
        "Acknowledge their ambition without competing for control.",
        "Deliver results, not excuses - respect is earned through competence.",
    ],
    9: [
        "Support their ideals and charitable impulses without mocking them.",
        "Give them space to serve the wider world, then pull focus back to us.",
        "Forgive quickly - they carry old patterns and want a fresh chapter.",
    ],
}


def _parse_dob(dob: str) -> date:
    from birth_place_resolve import normalize_dob

    return date.fromisoformat(normalize_dob(dob))


def _compat_rating(a: int, b: int, table: dict[tuple[int, int], bool]) -> str:
    ar, br = reduce_num(a, keep_master=False), reduce_num(b, keep_master=False)
    if table.get((ar, br), False):
        return "high"
    return "low"


def _relationship_number(c1: dict, c2: dict) -> int:
    def _pair(c: dict) -> int:
        lp = reduce_num(c["life_path"], keep_master=False)
        ex = reduce_num(c["expression"], keep_master=False)
        return reduce_num(lp + ex, keep_master=False)

    return reduce_num(_pair(c1) + _pair(c2), keep_master=False)


def _avasthi_pairing(groom_n: int, bride_n: int) -> dict[str, Any]:
    g, b = avasthi_group(groom_n), avasthi_group(bride_n)
    same = g == b
    if same:
        verdict = "harmonious"
        note = (
            f"Both in Group {g} ({AVASTHI_GROUPS[g]}) - "
            f"{AVASTHI_THEME[g].split('(')[0].strip().lower()}; shared rhythm."
        )
    else:
        verdict = "bridging"
        note = (
            f"Group {g} ({AVASTHI_GROUPS[g]}) with Group {b} ({AVASTHI_GROUPS[b]}) - "
            "opposites-attract potential; needs conscious bridging, not assumption of ease."
        )
    return {"groom_group": g, "bride_group": b, "verdict": verdict, "note": note}


def _score_lane(ratings: list[str]) -> int:
    pts = {"high": 2, "low": 0}
    return sum(pts.get(r, 1) for r in ratings)


def marriage_numerology_compat(
    *,
    groom_name: str,
    groom_dob: str,
    bride_name: str,
    bride_dob: str,
) -> dict[str, Any]:
    """Full numerology compatibility block for a couple."""
    if not groom_name.strip() or not bride_name.strip():
        return {"available": False, "reason": "Both full names are required for numerology."}

    gd = _parse_dob(groom_dob)
    bd = _parse_dob(bride_dob)
    g = compute(groom_name.strip(), gd)
    b = compute(bride_name.strip(), bd)

    lp_rating = _compat_rating(g["life_path"], b["life_path"], _LP_HIGH)
    su_rating = _compat_rating(g["soul_urge"], b["soul_urge"], _SU_HIGH)

    av_lp = _avasthi_pairing(g["lp_root"], b["lp_root"])
    av_bd = _avasthi_pairing(g["birth_day"], b["birth_day"])
    av_ex = _avasthi_pairing(
        reduce_num(g["expression"], keep_master=False),
        reduce_num(b["expression"], keep_master=False),
    )
    av_su = _avasthi_pairing(
        reduce_num(g["soul_urge"], keep_master=False),
        reduce_num(b["soul_urge"], keep_master=False),
    )

    rel_n = _relationship_number(g, b)
    rel_text = RELATIONSHIP_TEXT.get(rel_n, "")

    partner_destiny = reduce_num(b["lp_root"], keep_master=False)
    tips = PARTNER_TIPS.get(partner_destiny, [])

    score = _score_lane([lp_rating, su_rating])
    max_score = 4
    if av_lp["verdict"] == "harmonious":
        score += 1
        max_score += 1
    if av_su["verdict"] == "harmonious":
        score += 1
        max_score += 1

    if score >= max_score - 1:
        band, headline = "favourable", "Numerology lanes largely agree - temperament and inner needs align well."
    elif score >= max_score // 2:
        band, headline = "mixed", "Numerology is mixed - strong pockets with areas that need conscious bridging."
    else:
        band, headline = "caution", "Numerology shows friction - apply the relationship guidance below deliberately."

    warn_18 = 18 in (
        g["life_path_raw"], b["life_path_raw"],
        g["expr_total"], b["expr_total"],
    )

    advanced: dict[str, Any] = {"available": False}
    try:
        from numerology_advanced_marriage import advanced_marriage_assessment

        advanced = advanced_marriage_assessment(
            groom_dob=groom_dob,
            bride_dob=bride_dob,
        )
    except Exception as exc:
        advanced = {"available": False, "reason": str(exc)}

    return {
        "available": True,
        "groom": {
            "name": g["name"],
            "life_path": g["life_path"],
            "lp_root": g["lp_root"],
            "birth_day": g["birth_day"],
            "expression": g["expression"],
            "soul_urge": g["soul_urge"],
            "chaldean_root": g["chaldean_root"],
            "avasthi_lp_group": avasthi_group(g["lp_root"]),
        },
        "bride": {
            "name": b["name"],
            "life_path": b["life_path"],
            "lp_root": b["lp_root"],
            "birth_day": b["birth_day"],
            "expression": b["expression"],
            "soul_urge": b["soul_urge"],
            "chaldean_root": b["chaldean_root"],
            "avasthi_lp_group": avasthi_group(b["lp_root"]),
        },
        "life_path_compat": {
            "rating": lp_rating,
            "label": "High" if lp_rating == "high" else "Low",
            "groom_lp": reduce_num(g["life_path"], keep_master=False),
            "bride_lp": reduce_num(b["life_path"], keep_master=False),
        },
        "soul_urge_compat": {
            "rating": su_rating,
            "label": "High" if su_rating == "high" else "Low",
            "groom_su": reduce_num(g["soul_urge"], keep_master=False),
            "bride_su": reduce_num(b["soul_urge"], keep_master=False),
        },
        "avasthi": {
            "life_path": av_lp,
            "birth_day": av_bd,
            "expression": av_ex,
            "soul_urge": av_su,
            "groups": AVASTHI_GROUPS,
            "themes": AVASTHI_THEME,
        },
        "relationship_number": {
            "number": rel_n,
            "text": rel_text,
            "formula": "Each: LP + Expression -> one digit; sum both -> reduce.",
        },
        "partner_tips": {
            "destiny_number": partner_destiny,
            "tips": tips,
            "for": bride_name.strip(),
        },
        "warnings": ["Avoid compound 18 for wedding dates or house numbers."] if warn_18 else [],
        "verdict": {"band": band, "headline": headline, "score": score, "max_score": max_score},
        "advanced": advanced,
        "source": "Woods rules23 + Avasthi rules38 + 7-phase Advanced Marriage protocol",
    }
