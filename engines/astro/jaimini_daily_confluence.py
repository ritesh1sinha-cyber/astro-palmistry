#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jaimini Chara dasha daily confluence: cara karakas (AK, AmK, PK, GK, etc.)
qualified by SAV/BAV in running maha/antar/pratyantar signs (rules6 + rules10).
"""
from __future__ import annotations

from typing import Any

from astro_precompute import SIGNS
from ashtakavarga_analysis import HOUSE_LIFE_THEME, bav_transit_meaning, sav_house_meaning
from vedic_jaimini_report import PERIOD_PLAIN as JAIMINI_SIGN_PLAIN, house_of

KARAKA_SHORT = {
    "Atmakarak": "AK",
    "Amatyakarak": "AmK",
    "Putrakaraka": "PK",
    "Matrukaraka": "MK",
    "Bhratrukaraka": "BK",
    "Gnatikaraka": "GK",
    "Darakaraka": "DK",
}

KARAKA_ROLE_PLAIN = {
    "Atmakarak": "your soul-purpose theme",
    "Amatyakarak": "work and career",
    "Putrakaraka": "creativity and children",
    "Matrukaraka": "home and mother themes",
    "Bhratrukaraka": "siblings and peers",
    "Gnatikaraka": "stress and rivals",
    "Darakaraka": "partner and marriage",
}

KARAKA_THEME = {
    "Atmakarak": "soul purpose and what the day should serve long-term",
    "Amatyakarak": "career, status, and professional decisions",
    "Putrakaraka": "children, creativity, study, and speculative courage",
    "Matrukaraka": "mother, home base, and emotional roots",
    "Bhratrukaraka": "siblings, peers, and collaborative effort",
    "Gnatikaraka": "obstacles, rivals, and health friction",
    "Darakaraka": "partner, marriage tone, and one-to-one deals",
}

# Which karakas matter most at each Chara tier (rules6 daily focus).
LEVEL_KARAKAS = {
    "maha": ("Atmakarak", "Amatyakarak"),
    "antar": ("Amatyakarak", "Putrakaraka", "Darakaraka"),
    "pd": ("Atmakarak", "Amatyakarak", "Putrakaraka", "Gnatikaraka", "Darakaraka"),
}


def _karaka_table(pc: dict) -> dict[str, dict[str, Any]]:
    block = pc.get("cara_karakas") or {}
    rows = block.get("karakas") if isinstance(block, dict) else []
    if not rows:
        rows = pc.get("jaimini", {}).get("karakas", [])
    return {k["role"]: k for k in rows if k.get("role")}


def _sav_bav(pc: dict, sign: str, planet: str | None = None) -> tuple[int, int]:
    av = pc.get("ashtakavarga", {})
    sav_list = av.get("sav", [28] * 12)
    si = SIGNS.index(sign) if sign in SIGNS else 0
    sav = int(sav_list[si]) if si < len(sav_list) else 28
    bav = 4
    if planet:
        pb = av.get("bav", {}).get(planet, [4] * 12)
        bav = int(pb[si]) if si < len(pb) else 4
    return sav, bav


def _sav_band(sav: int) -> str:
    if sav >= 30:
        return "strong"
    if sav >= 25:
        return "moderate"
    return "weak"


def _jaimini_aspect_targets(sign: str) -> set[str]:
    if sign not in SIGNS:
        return set()
    i = SIGNS.index(sign)
    return {SIGNS[(i + d) % 12] for d in (2, 4, 6, 8)}


def _residents_in_sign(pc: dict, sign: str) -> list[str]:
    if not sign:
        return []
    return [p for p, d in pc.get("planets", {}).items() if d.get("sign") == sign and p in SIGNS[1:]]


def _karaka_slice_note(
    *,
    role: str,
    karaka: dict[str, Any],
    chara_sign: str,
    sav: int,
    bav: int,
    birth_lagna: str,
) -> dict[str, Any]:
    planet = karaka.get("planet", "")
    natal_sign = karaka.get("sign", "")
    short = KARAKA_SHORT.get(role, role[:2])
    theme = KARAKA_THEME.get(role, "life themes")
    h_from_chara = house_of(natal_sign, chara_sign) if natal_sign and chara_sign else 0
    h_from_lagna = house_of(natal_sign, birth_lagna) if natal_sign and birth_lagna else karaka.get("house", 0)
    in_sign = natal_sign == chara_sign
    aspects = _jaimini_aspect_targets(chara_sign)
    aspected = natal_sign in aspects
    sav_band = _sav_band(sav)
    bav_ok = bav >= 4
    bav_weak = bav <= 2

    score = 0
    notes: list[str] = []
    if in_sign:
        score += 2
        notes.append(f"{short} {planet} sits in this Chara sign natally - direct karaka activation")
    elif aspected:
        score += 1
        notes.append(f"{short} {planet} in {natal_sign} receives Jaimini sign-aspect from {chara_sign}")
    if sav_band == "strong":
        score += 1
    elif sav_band == "weak":
        score -= 1
    if bav_ok:
        score += 1
    elif bav_weak:
        score -= 1

    house_theme = HOUSE_LIFE_THEME.get(int(h_from_chara), "this life area")
    note = (
        f"{short} ({planet}): {theme}. "
        f"Chara sign {chara_sign} SAV {sav} ({sav_band}), {planet} BAV {bav}/8. "
        f"From Chara lagna: {_ordinal(h_from_chara)} house ({house_theme})."
    )
    if notes:
        note += " " + notes[0] + "."

    return {
        "role": role,
        "short": short,
        "planet": planet,
        "natal_sign": natal_sign,
        "natal_house": h_from_lagna,
        "house_from_chara": h_from_chara,
        "in_sign": in_sign,
        "aspected": aspected,
        "sav": sav,
        "bav": bav,
        "sav_band": sav_band,
        "score": score,
        "note": note,
    }


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def build_jaimini_daily_confluence(
    *,
    pc: dict,
    birth_lagna: str,
    jaimini: dict[str, Any],
) -> dict[str, Any]:
    """
    Confluence of running Chara maha/antar/pd signs with cara karakas + SAV/BAV.
    """
    jm = jaimini.get("maha", "")
    ja = jaimini.get("antar", "")
    jp = jaimini.get("pd", "")
    if not jm and not ja and not jp:
        return {"available": False, "reading": "", "lanes": [], "levels": [], "score": 0}

    karakas = _karaka_table(pc)
    if not karakas:
        return {"available": False, "reading": "Cara karaka table missing in precompute.", "lanes": [], "levels": [], "score": 0}

    levels: list[dict[str, Any]] = []
    total_score = 0
    highlights: list[str] = []

    tier_map = (
        ("maha", jm, "Chara mahadasha"),
        ("antar", ja, "Chara antardasha"),
        ("pd", jp, "Chara pratyantar"),
    )
    for level_key, sign, label in tier_map:
        if not sign or sign not in SIGNS:
            continue
        sav, _ = _sav_bav(pc, sign)
        residents = ", ".join(_residents_in_sign(pc, sign)) or "none"
        sav_note = sav_house_meaning(
            house_of(sign, birth_lagna) if birth_lagna in SIGNS else 1,
            sav,
            sign,
            residents,
        )
        karaka_rows: list[dict[str, Any]] = []
        for role in LEVEL_KARAKAS.get(level_key, ()):
            k = karakas.get(role)
            if not k:
                continue
            _, bav = _sav_bav(pc, sign, k.get("planet"))
            row = _karaka_slice_note(
                role=role,
                karaka=k,
                chara_sign=sign,
                sav=sav,
                bav=bav,
                birth_lagna=birth_lagna,
            )
            karaka_rows.append(row)
            total_score += row["score"]
            if row["score"] >= 2:
                role_plain = KARAKA_ROLE_PLAIN.get(role, KARAKA_SHORT.get(role, role))
                highlights.append(f"{role_plain} is strongly active in {sign}")

        sign_plain = JAIMINI_SIGN_PLAIN.get(sign, "")
        levels.append({
            "level": level_key,
            "label": label,
            "sign": sign,
            "sav": sav,
            "sav_band": _sav_band(sav),
            "sign_theme": sign_plain,
            "sav_note": sav_note,
            "karakas": karaka_rows,
        })

    reading_parts: list[str] = []
    for lv in levels:
        kbits = "; ".join(r["note"][:120] for r in lv["karakas"][:3])
        reading_parts.append(
            f"{lv['label']} {lv['sign']} (SAV {lv['sav']}, {lv['sav_band']}): {lv['sign_theme']} "
            f"Karakas: {kbits}"
        )

    lanes: list[dict[str, Any]] = []
    for lv in levels:
        ksig = ", ".join(
            f"{r['short']} BAV {r['bav']}/8"
            for r in lv["karakas"]
        )
        lanes.append({
            "lane": f"Jaimini {lv['level']}",
            "signal": f"{lv['sign']} SAV {lv['sav']}; {ksig}",
            "weight": "high" if lv["sav_band"] == "strong" else "medium",
        })

    # Best karaka BAV line for antar (today's sub-chapter)
    antar_lv = next((x for x in levels if x["level"] == "antar"), None)
    bav_summary = ""
    if antar_lv and antar_lv["karakas"]:
        amk = next((r for r in antar_lv["karakas"] if r["role"] == "Amatyakarak"), None)
        if amk:
            bav_summary = bav_transit_meaning(
                amk["planet"],
                amk["house_from_chara"],
                amk["bav"],
                antar_lv["sav"],
            )

    tone = "supportive"
    if total_score <= -1:
        tone = "caution"
    elif total_score < 2:
        tone = "mixed"

    return {
        "available": True,
        "levels": levels,
        "highlights": highlights,
        "lanes": lanes,
        "score": total_score,
        "tone": tone,
        "bav_summary": bav_summary,
        "reading": " ".join(reading_parts),
        "source": "rules6 Jaimini Chara + rules10 Ashtakavarga on dasha signs",
    }
