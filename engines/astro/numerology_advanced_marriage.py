#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Advanced Numerological Marriage Compatibility Assessment (7-phase protocol).

Psychic (Moolank), Destiny (Bhagyank), Seferal/Vedic grid planes, adverse
combinations, 5-step decision matrix, and cross-correction remedies.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from numerology_report import PLANET, reduce_num

# Phase I - Psychic archetypes (Moolank = reduced birth day).
PSYCHIC_TRAITS = {
    1: "Leadership, courage, administrative authority, independence (Sun).",
    2: "Friendly, modest, diplomatic, sensitive (Moon).",
    3: "Cheerful, creative, counseling/advisory skill (Jupiter).",
    4: "Disciplined, practical, scientific, managerial (Rahu).",
    5: "Versatile, energetic, adaptable free spirit (Mercury).",
    6: "Artistic, loving, caring, family-oriented (Venus).",
    7: "Philosophical, research-oriented, prefers solitude (Ketu).",
    8: "Executive ability, material focus, disciplined authority (Saturn).",
    9: "Humanitarian, impulsive, broad-minded, compassionate (Mars).",
}

# Phase II - Psychic enmity (Anemical numbers).
PSYCHIC_ENEMIES: dict[int, set[int]] = {
    1: {5, 6},
    2: {5, 8},
    3: {4, 8},
    4: {3, 5},
    5: {2, 4},
    6: {1, 8},
    7: {1, 9},
    8: {3, 6},
    9: {1, 7},
}

# Phase III - Destiny trajectory bands (Bhagyank).
DESTINY_OPPORTUNITY = {1, 5, 9}
DESTINY_MIXED = {2, 3, 6}
DESTINY_HARDSHIP = {4, 7, 8}

DESTINY_TRAJECTORY = {
    "opportunity": "Opportunity path - recognition, mobility, favourable openings.",
    "mixed": "Mixed path - repeated effort, high responsibility, emotional strain possible.",
    "hardship": "Hardship path - sudden hurdles, financial swings, slow progress; family harmony taxed.",
}

# Phase IV - Seferal grid planes (Vedic 3x3 layout).
PLANES = {
    "spiritual": {"digits": (3, 1, 9), "label": "Spiritual (intellect, wisdom)"},
    "emotional": {"digits": (6, 7, 5), "label": "Emotional (attachment, connection)"},
    "physical": {"digits": (2, 8, 4), "label": "Physical (work, material life)"},
}

# Phase V - Adverse marital combinations.
LOWER_ADVERSE = [
    (6, 7), (6, 2), (2, 8), (9, 5), (9, 4), (6, 5), (9, 8), (6, 4),
]
HIGHER_ADVERSE = [
    (1, 2, 4), (6, 1, 7), (2, 7, 9), (2, 8, 4),
    (6, 9, 4), (6, 7, 5), (9, 5, 4), (6, 2, 8), (8, 4, 5),
]

# Phase VII - Remedy lookup.
CRYSTAL_REMEDIES = {
    "pink": ("Rose Quartz", "Love and emotional softness"),
    "green": ("Peridot", "Adaptability and balance - softens rigidity in 1/8 types"),
    "yellow": ("Citrine", "Creativity and clarity - strengthens spiritual plane 3-1-9"),
    "purple": ("Amethyst", "Discipline and healthy detachment - balances over-possessive 6"),
}
DESTINY_YANTRA = {
    3: "Jupiter Yantra - manage over-burdened responsibility in mixed-3 destiny.",
    7: "Ketu Yantra - stabilise financial fluctuation in hardship-7 destiny.",
    4: "Rahu Yantra - channel discipline without suppressing partner freedom.",
    8: "Saturn Yantra - balance material drive with relational warmth.",
}
SOUND_REMEDIES = {
    6: "Venus mantra / Shukra peace when 6 is afflicted by 1 or 7 in grid.",
    1: "Sun mantra when 1-6 ego clash combination (6-1-7) is active.",
    7: "Ketu mantra when detachment cluster (2-7-9) is active.",
}


def psychic_number(dob: date) -> int:
    return reduce_num(dob.day, keep_master=False)


def destiny_number(dob: date) -> int:
    raw = sum(int(c) for c in f"{dob.day:02d}{dob.month:02d}{dob.year}")
    return reduce_num(raw, keep_master=False)


def _digits_from_component(value: int, width: int) -> list[int]:
    return [int(c) for c in f"{value:0{width}d}" if c != "0"]


def seferal_present_digits(dob: date) -> set[int]:
    """Build Seferal grid inputs per protocol (5 sources, no within-source repeat)."""
    present: set[int] = set()

    for d in _digits_from_component(dob.day, 2):
        present.add(d)

    for d in _digits_from_component(dob.month, 2):
        present.add(d)

    year_last_two = _digits_from_component(dob.year % 100, 2)
    year_set = set(year_last_two)
    present.update(year_set)

    if year_last_two:
        yr_reduced = reduce_num(sum(year_last_two), keep_master=False)
        if yr_reduced not in year_set:
            present.add(yr_reduced)

    present.add(destiny_number(dob))
    return present


def _destiny_band(n: int) -> str:
    if n in DESTINY_OPPORTUNITY:
        return "opportunity"
    if n in DESTINY_HARDSHIP:
        return "hardship"
    return "mixed"


def _plane_analysis(present: set[int]) -> dict[str, Any]:
    rows = {}
    for key, info in PLANES.items():
        digits = info["digits"]
        count = sum(1 for d in digits if d in present)
        if count >= 3:
            strength = "fully_activated"
            label = "Fully activated"
        elif count == 2:
            strength = "strong"
            label = "Strong"
        elif count == 1:
            strength = "weak"
            label = "Weak"
        else:
            strength = "empty"
            label = "Empty (critical deficiency)"
        rows[key] = {
            "label": info["label"],
            "digits": digits,
            "present": [d for d in digits if d in present],
            "count": count,
            "strength": strength,
            "strength_label": label,
        }
    return rows


def _combo_present(present: set[int], combo: tuple[int, ...]) -> bool:
    return all(d in present for d in combo)


def _adverse_combos(present: set[int]) -> dict[str, Any]:
    higher = [list(c) for c in HIGHER_ADVERSE if _combo_present(present, c)]
    higher_tuples = [tuple(h) for h in higher]
    lower = []
    for combo in LOWER_ADVERSE:
        if _combo_present(present, combo):
            if not any(set(combo).issubset(set(h)) for h in higher_tuples):
                lower.append(list(combo))
    return {
        "higher": higher,
        "lower": lower,
        "higher_count": len(higher),
        "lower_count": len(lower),
    }


def _psychic_enmity(a: int, b: int) -> dict[str, Any]:
    enemies_a = PSYCHIC_ENEMIES.get(a, set())
    enemies_b = PSYCHIC_ENEMIES.get(b, set())
    mutual = (b in enemies_a) or (a in enemies_b)
    who = []
    if b in enemies_a:
        who.append(f"Groom psychic {a} vs bride psychic {b}")
    if a in enemies_b:
        who.append(f"Bride psychic {b} vs groom psychic {a}")
    return {
        "anemical": mutual,
        "detail": "; ".join(who) if who else "No psychic enmity flagged.",
    }


def _plane_couple_analysis(g_planes: dict, b_planes: dict) -> dict[str, Any]:
    common_empty = []
    polarities = []
    for key in PLANES:
        gs = g_planes[key]["strength"]
        bs = b_planes[key]["strength"]
        if gs == "empty" and bs == "empty":
            common_empty.append(PLANES[key]["label"])
        if gs == "fully_activated" and bs == "empty":
            polarities.append(
                f"Groom fully activated {PLANES[key]['label']} vs bride empty - needs unmet."
            )
        elif bs == "fully_activated" and gs == "empty":
            polarities.append(
                f"Bride fully activated {PLANES[key]['label']} vs groom empty - needs unmet."
            )
    return {"common_empty": common_empty, "polarities": polarities}


def _build_remedies(
    *,
    g_psychic: int,
    b_psychic: int,
    g_destiny: int,
    b_destiny: int,
    enmity: dict,
    g_adverse: dict,
    b_adverse: dict,
    polarities: list[str],
) -> list[dict[str, Any]]:
    remedies: list[dict[str, Any]] = []

    if enmity.get("anemical"):
        pair = sorted([g_psychic, b_psychic])
        if pair == [1, 6]:
            remedies.append({
                "type": "crystal_color",
                "for": "Psychic 1-6 enmity",
                "steps": [
                    "Groom (Psychic 1): wear green / Peridot for adaptability (Mercury-5 frequency).",
                    "Bride (Psychic 6): wear blue-purple / Amethyst for discipline and healthy detachment.",
                ],
            })
        elif 8 in pair and 9 in pair:
            remedies.append({
                "type": "crystal_color",
                "for": "Psychic 8-9 value clash",
                "steps": [
                    "Groom/bride with Psychic 8: green Peridot to soften executive materialism.",
                    "Partner with Psychic 9: pink Rose Quartz to keep humanitarian warmth in daily life.",
                ],
            })
        elif 4 in pair and 5 in pair:
            remedies.append({
                "type": "crystal_color",
                "for": "Psychic 4-5 structure vs freedom",
                "steps": [
                    "Psychic 4 partner: yellow Citrine for flexible structure.",
                    "Psychic 5 partner: green Peridot to honour routine without feeling caged.",
                ],
            })
        else:
            remedies.append({
                "type": "crystal_color",
                "for": "Psychic enmity",
                "steps": [
                    "Both partners: pink Rose Quartz or rose clothing on Fridays for emotional repair.",
                    "Schedule weekly structured dialogue - enmity pairs widen when unspoken.",
                ],
            })

    for role, dest, adverse in (
        ("Groom", g_destiny, g_adverse),
        ("Bride", b_destiny, b_adverse),
    ):
        if dest in DESTINY_YANTRA:
            remedies.append({
                "type": "yantra",
                "for": f"{role} Destiny {dest}",
                "steps": [DESTINY_YANTRA[dest]],
            })

    for role, adverse in (("Groom", g_adverse), ("Bride", b_adverse)):
        combos = adverse.get("higher") or []
        if [6, 1, 7] in combos or (6, 1, 7) in [tuple(x) for x in combos]:
            remedies.append({
                "type": "sound",
                "for": f"{role} grid ego-clash cluster 6-1-7",
                "steps": [SOUND_REMEDIES[6], SOUND_REMEDIES[1]],
            })
        if [2, 7, 9] in combos:
            remedies.append({
                "type": "sound",
                "for": f"{role} detachment cluster 2-7-9",
                "steps": [SOUND_REMEDIES[7]],
            })
        if [2, 8, 4] in combos:
            remedies.append({
                "type": "crystal_color",
                "for": f"{role} depressive cluster 2-8-4",
                "steps": [
                    "Yellow Citrine near workspace; strengthen spiritual plane 3-1-9.",
                    "Daily sunlight walk - physical plane activation for 2-8-4 imbalance.",
                ],
            })

    if polarities:
        remedies.append({
            "type": "cross_correction",
            "for": "Plane polarity",
            "steps": [
                "Partner with the fuller emotional plane leads with patience; do not demand matching depth overnight.",
                "Empty-plane partner: yellow Citrine (spiritual), pink Rose Quartz (emotional), green Peridot (physical) per deficient plane.",
            ],
        })

    # Deduplicate by 'for' key.
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for r in remedies:
        k = r.get("for", "")
        if k in seen:
            continue
        seen.add(k)
        unique.append(r)
    return unique


def _decision_framework(
    *,
    enmity: dict,
    g_destiny_band: str,
    b_destiny_band: str,
    plane_couple: dict,
    g_adverse: dict,
    b_adverse: dict,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    reject_reasons: list[str] = []
    caution_reasons: list[str] = []

    # Step 1 - Psychic alignment.
    if enmity.get("anemical"):
        steps.append({"step": 1, "name": "Psychic alignment", "pass": False, "detail": enmity["detail"]})
        caution_reasons.append("Psychic enmity present - chronic difference of opinion risk.")
    else:
        steps.append({"step": 1, "name": "Psychic alignment", "pass": True, "detail": "No anemical psychic pairing."})

    # Step 2 - Destiny load.
    dual_hardship = g_destiny_band == "hardship" and b_destiny_band == "hardship"
    if dual_hardship:
        steps.append({
            "step": 2, "name": "Destiny load", "pass": False,
            "detail": "Both carry hardship destiny (4/7/8) - situational overload risk.",
        })
        reject_reasons.append("Dual hardship Bhagyank - external collapse risk on the union.")
    else:
        steps.append({"step": 2, "name": "Destiny load", "pass": True, "detail": "Not dual hardship destiny."})

    # Step 3 - Common empty planes.
    common_empty = plane_couple.get("common_empty") or []
    if common_empty:
        steps.append({
            "step": 3, "name": "Plane symmetry", "pass": False,
            "detail": f"Both lack: {', '.join(common_empty)}",
        })
        reject_reasons.append(f"Common empty plane(s): {', '.join(common_empty)}")
    else:
        steps.append({"step": 3, "name": "Plane symmetry", "pass": True, "detail": "No shared empty plane."})

    # Step 4 - Polarity.
    polarities = plane_couple.get("polarities") or []
    if polarities:
        steps.append({
            "step": 4, "name": "Polarity check", "pass": False,
            "detail": "; ".join(polarities),
        })
        reject_reasons.append("Full-vs-empty plane polarity - unmet relational needs.")
    else:
        steps.append({"step": 4, "name": "Polarity check", "pass": True, "detail": "No terminal plane polarity."})

    # Step 5 - Higher-order density.
    h_total = (g_adverse.get("higher_count") or 0) + (b_adverse.get("higher_count") or 0)
    if h_total >= 3:
        steps.append({
            "step": 5, "name": "Combination density", "pass": False,
            "detail": f"{h_total} higher-order adverse clusters across both grids.",
        })
        reject_reasons.append("High density of higher-order adverse grid combinations.")
    elif h_total >= 1:
        steps.append({
            "step": 5, "name": "Combination density", "pass": False,
            "detail": f"{h_total} higher-order adverse cluster(s) - monitor closely.",
        })
        caution_reasons.append("Higher-order adverse grid combinations present.")
    else:
        steps.append({
            "step": 5, "name": "Combination density", "pass": True,
            "detail": "No higher-order adverse clusters.",
        })

    has_opportunity = (
        g_destiny_band == "opportunity" or b_destiny_band == "opportunity"
    )

    if reject_reasons:
        verdict, headline = "reject", "Advanced numerology flags terminal structural risk."
    elif enmity.get("anemical") or not has_opportunity or caution_reasons:
        verdict, headline = "caution", "Union viable only with deliberate cross-remediation and pacing."
    else:
        verdict, headline = "recommend", "Advanced numerology supports long-term viability."

    return {
        "verdict": verdict,
        "headline": headline,
        "steps": steps,
        "reject_reasons": reject_reasons,
        "caution_reasons": caution_reasons,
        "has_opportunity_destiny": has_opportunity,
    }


def _person_profile(dob: date, role: str) -> dict[str, Any]:
    psychic = psychic_number(dob)
    destiny = destiny_number(dob)
    present = seferal_present_digits(dob)
    planes = _plane_analysis(present)
    adverse = _adverse_combos(present)
    band = _destiny_band(destiny)
    return {
        "role": role,
        "psychic": psychic,
        "psychic_planet": PLANET.get(psychic, str(psychic)),
        "psychic_traits": PSYCHIC_TRAITS.get(psychic, ""),
        "destiny": destiny,
        "destiny_band": band,
        "destiny_note": DESTINY_TRAJECTORY[band],
        "seferal_digits": sorted(present),
        "planes": planes,
        "adverse": adverse,
    }


def advanced_marriage_assessment(
    *,
    groom_dob: str,
    bride_dob: str,
) -> dict[str, Any]:
    from birth_place_resolve import normalize_dob

    gd = date.fromisoformat(normalize_dob(groom_dob))
    bd = date.fromisoformat(normalize_dob(bride_dob))

    groom = _person_profile(gd, "groom")
    bride = _person_profile(bd, "bride")

    enmity = _psychic_enmity(groom["psychic"], bride["psychic"])
    plane_couple = _plane_couple_analysis(groom["planes"], bride["planes"])
    decision = _decision_framework(
        enmity=enmity,
        g_destiny_band=groom["destiny_band"],
        b_destiny_band=bride["destiny_band"],
        plane_couple=plane_couple,
        g_adverse=groom["adverse"],
        b_adverse=bride["adverse"],
    )
    remedies = _build_remedies(
        g_psychic=groom["psychic"],
        b_psychic=bride["psychic"],
        g_destiny=groom["destiny"],
        b_destiny=bride["destiny"],
        enmity=enmity,
        g_adverse=groom["adverse"],
        b_adverse=bride["adverse"],
        polarities=plane_couple.get("polarities") or [],
    )

    return {
        "available": True,
        "protocol": "Advanced Numerological Marriage Compatibility (7-phase)",
        "groom": groom,
        "bride": bride,
        "psychic_enmity": enmity,
        "plane_couple": plane_couple,
        "decision": decision,
        "remedies": remedies,
        "source": "Professional 7-phase protocol: Psychic/Destiny/Seferal grid/planes/adverse combos",
    }
