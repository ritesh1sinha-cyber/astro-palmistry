#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Goel Trishamsha extras - tattva, fortune matrix, D1 6/8 source, kendra tone (rules15)."""
from __future__ import annotations

from typing import Any

from astro_precompute import get_dignity
from vedic_varga_goel import (
    BENEFIC_LAGNA_LORDS,
    BENEFICS,
    MALEFIC_LAGNA_LORDS,
    MALEFICS,
    VargaChart,
)

TRIK = {6, 8, 12}
KENDRA = {1, 4, 7, 10}
TRIKONA = {1, 5, 9}
STRONG_DIGNITY = {"exalted", "own_sign", "moolatrikona"}

TATTVA = {
    "fire": {"Aries", "Leo", "Sagittarius"},
    "earth": {"Taurus", "Virgo", "Capricorn"},
    "air": {"Gemini", "Libra", "Aquarius"},
    "water": {"Cancer", "Scorpio", "Pisces"},
}
OPPOSITE_TATTVA = {"fire": "water", "water": "fire", "earth": "air", "air": "earth"}


def _sign_tattva(sign: str) -> str:
    for name, signs in TATTVA.items():
        if sign in signs:
            return name
    return ""


def _tone_from_score(score: int) -> str:
    if score >= 1:
        return "benefic"
    if score <= -1:
        return "malefic"
    return "mixed"


def _lagna_fortune_tone(d30: VargaChart) -> tuple[str, int, list[str]]:
    lagna_ll = d30.house_lord(1)
    tenants = d30.tenants(1)
    score = d30.benefic_score(1)
    facts: list[str] = []

    if lagna_ll in BENEFIC_LAGNA_LORDS:
        score += 1
        facts.append(f"benefic sign {d30.lagna} rises")
    elif lagna_ll in MALEFIC_LAGNA_LORDS:
        score -= 1
        facts.append(f"malefic sign {d30.lagna} rises")

    aff = [p for p in tenants if p in MALEFICS]
    ben = [p for p in tenants if p in BENEFICS]
    if aff and not ben:
        score -= 2
        facts.append(f"malefics on lagna ({', '.join(aff)}) without benefic relief")
    elif ben:
        score += 1
        facts.append(f"benefics on lagna ({', '.join(ben)})")

    if lagna_ll in tenants:
        score += 1
        facts.append("lagna lord conjoins lagna")

    return _tone_from_score(score), score, facts


def _lord_fortune_tone(d30: VargaChart, lord: str) -> tuple[str, int, list[str]]:
    if not lord:
        return "mixed", 0, []
    h = d30.planet_house(lord)
    sign = d30.signs.get(lord, "")
    dig = get_dignity(lord, sign)
    score = 0
    facts: list[str] = []

    if dig in STRONG_DIGNITY or dig == "friendly_sign":
        score += 1
        facts.append(f"{lord} dignified in {sign or 'D30'}")
    elif dig in ("debilitated", "enemy_sign"):
        score -= 1
        facts.append(f"{lord} weak in {sign or 'D30'}")

    if h in KENDRA | TRIKONA:
        score += 1
    elif h in TRIK:
        score -= 1
        facts.append(f"{lord} in trik house {h}")

    tenants_h = d30.tenants(h) if h else []
    if any(p in MALEFICS for p in tenants_h) and not any(p in BENEFICS for p in tenants_h):
        score -= 1
        facts.append(f"malefic company on {lord}")

    return _tone_from_score(score), score, facts


def _fortune_profile(lagna_tone: str, ll_tone: str) -> dict[str, Any]:
    """Goel Ch.03 lagna x lagna-lord matrix (a-e)."""
    profiles = {
        ("benefic", "benefic"): (
            "fortunate",
            "Fortunate birth - life problems are fewer and you are unlikely to invite trouble by your own deeds.",
        ),
        ("mixed", "benefic"): (
            "mixed_fortunate_deeds",
            "Mixed fortune at birth, but lagna lord is strong - adversity comes and goes without much self-sabotage.",
        ),
        ("benefic", "mixed"): (
            "fortunate_self_swing",
            "Fortunate birth promise, but lagna lord is mixed - you can create both luck and friction by your own choices.",
        ),
        ("malefic", "benefic"): (
            "unfortunate_redeemed",
            "Unfortunate birth load, but a strong lagna lord - hardship is mostly circumstantial, not self-invited.",
        ),
        ("malefic", "malefic"): (
            "unfortunate_self",
            "Unfortunate Trishamsha - adversity is heavy and lagna lord is afflicted, so self-deeds can multiply misfortune.",
        ),
        ("mixed", "mixed"): (
            "mixed",
            "Fortune and adversity alternate - neither charmed nor cursed; dasha and conduct decide the swing.",
        ),
        ("benefic", "malefic"): (
            "fortunate_self_risk",
            "Birth promise is good, but afflicted lagna lord - watch hostile sub-periods when choices amplify trouble.",
        ),
        ("malefic", "mixed"): (
            "unfortunate_partial",
            "Heavy birth karma with a mixed manager - problems are real but not every setback is self-made.",
        ),
        ("mixed", "malefic"): (
            "mixed_self_risk",
            "Mixed lagna with afflicted lagna lord - external luck varies and self-deeds can invite extra friction.",
        ),
    }
    key = (lagna_tone, ll_tone)
    label, text = profiles.get(key, profiles[("mixed", "mixed")])
    return {"label": label, "text": text, "lagna_tone": lagna_tone, "ll_tone": ll_tone}


def _tattva_clash(d1_lagna: str, d30_lagna: str) -> dict[str, Any]:
    t1, t2 = _sign_tattva(d1_lagna), _sign_tattva(d30_lagna)
    clash = bool(t1 and t2 and OPPOSITE_TATTVA.get(t1) == t2)
    text = ""
    if clash:
        text = (
            f"Birth lagna ({d1_lagna}, {t1}) and Trishamsha lagna ({d30_lagna}, {t2}) sit in opposite tattvas - "
            "Goel reads extra friction between promise and material results."
        )
    return {"clash": clash, "d1_tattva": t1, "d30_tattva": t2, "text": text}


def _d1_problem_lords(pc: dict, d30: VargaChart) -> dict[str, Any]:
    hl = pc.get("house_lords", {})
    l6 = hl.get(6, hl.get("6", {})).get("lord", "")
    l8 = hl.get(8, hl.get("8", {})).get("lord", "")
    out: dict[str, Any] = {"lords": [], "text": ""}
    parts: list[str] = []
    for lord, theme in ((l6, "illness and dispute"), (l8, "fear and sudden setback")):
        if not lord:
            continue
        h = d30.planet_house(lord)
        sign = d30.signs.get(lord, "")
        parts.append(f"birth {theme.split()[0]} lord {lord} in D30 house {h} ({sign})")
        out["lords"].append({"lord": lord, "d30_house": h, "d30_sign": sign, "theme": theme})
    if parts:
        out["text"] = (
            "Examination rule: natal sixth and eighth lords in Trishamsha show where trouble originates - "
            + "; ".join(parts) + "."
        )
    return out


def _kendra_trikona_tone(d30: VargaChart, fortunate: bool) -> dict[str, Any]:
    scores = []
    for h in sorted(KENDRA | TRIKONA):
        scores.append((h, d30.benefic_score(h)))
    good = sum(1 for _, s in scores if s >= 1)
    bad = sum(1 for _, s in scores if s <= -1)
    if fortunate:
        text = (
            "Kendra and trikona houses act as fortune-givers in a fortunate Trishamsha - "
            + (f"{good} angular/trinal houses are supported." if good else "support is modest but present.")
        )
        tone = "green"
    else:
        text = (
            "In an unfortunate Trishamsha, kendra and trikona can carry adversity - "
            + (f"{bad} angular/trinal houses are stressed." if bad else "stress shows through lagna lord action.")
        )
        tone = "amber"
    return {"good": good, "bad": bad, "text": text, "tone": tone}


def _character_axis(pc: dict, d30: VargaChart) -> dict[str, Any]:
    """Stronger of birth lagna vs Moon in Trishamsha (book female horoscopy - applies to all)."""
    d1_lagna = pc.get("meta", {}).get("lagna_sign", "")
    moon_d1 = pc.get("planets", {}).get("Moon", {}).get("sign", "")
    ref = d1_lagna
    if moon_d1:
        moon_h = pc.get("planets", {}).get("Moon", {}).get("house", 0)
        lagna_h = 1
        if moon_h in (1, 4, 7, 10) and lagna_h not in (1, 4, 7, 10):
            ref = moon_d1
        elif moon_d1 == d30.lagna:
            ref = moon_d1
    moon_d30_h = d30.planet_house("Moon")
    moon_d30_sign = d30.signs.get("Moon", "")
    text = (
        f"Character examination uses Trishamsha Moon in house {moon_d30_h or '?'} ({moon_d30_sign}) - "
        "mental tone under which actions are done when adversity hits."
    )
    if moon_d30_h in TRIK:
        text += " Moon in a trik house of Trishamsha - emotional stress colours how setbacks are handled."
    elif moon_d30_h in KENDRA:
        text += " Moon in a kendra of Trishamsha - emotional resilience is workable with mind-care."
    return {"ref_sign": ref, "moon_d30_house": moon_d30_h, "moon_d30_sign": moon_d30_sign, "text": text}


def _early_marriage_flag(pc: dict, d30: VargaChart) -> dict[str, Any]:
    d1_lagna = pc.get("meta", {}).get("lagna_sign", "")
    sat_h = d30.planet_house("Saturn")
    active = sat_h == 1 and d1_lagna in ("Capricorn", "Aquarius")
    text = ""
    if active:
        text = (
            "Saturn in Trishamsha lagna with Saturn-ruled birth lagna - Goel (Navamsha book cross-ref) "
            "allows early union, but marriage quality may need maturity and remedies."
        )
    return {"active": active, "text": text}


def _marriage_friction(d30: VargaChart, fortunate: bool) -> dict[str, Any]:
    h7 = d30.benefic_score(7)
    lagna_ll = d30.house_lord(1)
    harsh = h7 <= -1 or (lagna_ll in MALEFIC_LAGNA_LORDS and d30.benefic_score(1) <= 0)
    text = ""
    if harsh:
        text = (
            "Trishamsha lagna or seventh house is stressed - Goel ties this to daily partnership friction "
            "and strain in married life, not merely late marriage."
        )
    elif h7 >= 1:
        text = "Trishamsha seventh house is supported - marriage is not the main misfortune channel."
    elif fortunate:
        text = "Partnership sits in a neutral band - union is manageable if Navamsha cooperates."
    return {"harsh": harsh, "score": h7, "text": text}


def _house_extras(d30: VargaChart) -> dict[str, Any]:
    h4 = d30.benefic_score(4)
    h12 = d30.benefic_score(12)
    return {
        "comfort_morals": {
            "score": h4,
            "text": (
                "Fourth house supported - morals, home peace, and inner comfort are maintainable."
                if h4 >= 0
                else "Fourth house stressed - morals and home peace need conscious upkeep (Goel)."
            ),
        },
        "loss_isolation": {
            "score": h12,
            "text": (
                "Twelfth house benefic - losses and isolation themes are lighter."
                if h12 >= 0
                else "Twelfth house malefic - hidden losses, hospital, or self-invited trouble themes are live."
            ),
        },
    }


def analyze_trishamsha_extras(
    pc: dict,
    d30: VargaChart,
    lagna_tone: str,
    fortunate: bool,
) -> dict[str, Any]:
    d1_lagna = pc.get("meta", {}).get("lagna_sign", "")
    ll = d30.house_lord(1)
    l8 = d30.house_lord(8)
    ll_tone, _, ll_facts = _lord_fortune_tone(d30, ll)
    l8_tone, _, l8_facts = _lord_fortune_tone(d30, l8)
    profile = _fortune_profile(lagna_tone, ll_tone)
    return {
        "fortune_profile": profile,
        "ll_tone": ll_tone,
        "ll_facts": ll_facts,
        "l8_tone": l8_tone,
        "l8_facts": l8_facts,
        "tattva_clash": _tattva_clash(d1_lagna, d30.lagna),
        "problem_lords": _d1_problem_lords(pc, d30),
        "kendra_trikona": _kendra_trikona_tone(d30, fortunate),
        "character_axis": _character_axis(pc, d30),
        "early_marriage": _early_marriage_flag(pc, d30),
        "marriage_friction": _marriage_friction(d30, fortunate),
        "house_extras": _house_extras(d30),
    }
