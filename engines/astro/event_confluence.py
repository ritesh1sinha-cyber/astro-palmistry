#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-technique confluence for future event timing.
Date released only when >75% agree AND mandatory pillar checklist passes (anti-guesswork gate).
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from astro_precompute import SIGNS, YOGINI_LORDS

CONFLUENCE_THRESHOLD = 0.75  # pct must exceed this (strictly >)

# Mandatory pillars � all must vote yes for a confirmed date
MANDATORY_PILLARS = ("vimshottari", "varga")

# Independent dasha clocks � need >= MIN_PRIMARY_DASHA_YES
PRIMARY_DASHA_IDS = (
    "chara", "chara_goel", "yogini_goel", "yogini",
    "kapoor_age", "kapoor_paribhraman",
    "kalachakra", "lagnamsa", "bhrigu_pada",
)
MIN_PRIMARY_DASHA_YES = 3

# Actualization layer (Boney/Kapoor/KP) � need >= 1
ACTUALIZATION_IDS = ("transit", "gk_transit_dasha", "multi_lagna", "kp_md", "kp_ad", "kp_transit")

# Goel rules8 � at least one must pass when loaded
GOEL_IDS = ("chara_goel", "yogini_goel")

# Chara family � overlap OR Goel lord link
CHARA_FAMILY_IDS = ("chara", "chara_goel")

# Event -> Lagnamsa / Padhanadhamsa divisional factor
EVENT_VARGA_FACTOR: dict[str, int] = {
    "marriage": 9,
    "child": 7,
    "career": 10,
    "property": 4,
    "education": 24,
    "travel": 12,
    "business": 10,
    "recovery": 9,
    "wealth": 2,
    "status": 10,
}

YOGINI_PLANETS = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"}


def _vote_map(techniques: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {v["id"]: v for v in techniques if v.get("id")}


def evaluate_confirmed_release(confluence: dict[str, Any]) -> dict[str, Any]:
    """
    Strict release gate: pct alone is not enough.
    Requires mandatory pillars + chara lane + Goel + multi-dasha + actualization.
    """
    votes = _vote_map(confluence.get("techniques", []))
    checks: list[dict[str, Any]] = []

    def chk(cid: str, label: str, ok: bool, detail: str = ""):
        checks.append({"id": cid, "label": label, "passed": bool(ok), "detail": detail})

    pct = float(confluence.get("confluence_pct", 0))
    pct_ok = pct > CONFLUENCE_THRESHOLD
    chk("pct", f"Confluence > {int(CONFLUENCE_THRESHOLD * 100)}%", pct_ok,
        f"{confluence.get('yes_count', 0)}/{confluence.get('total_techniques', 0)} ({confluence.get('confluence_pct_display', 0)}%)")

    mandatory_ok = True
    for pid in MANDATORY_PILLARS:
        v = votes.get(pid, {})
        if pid in votes:
            ok = bool(v.get("yes"))
            mandatory_ok = mandatory_ok and ok
            chk(pid, v.get("label", pid), ok, v.get("note", ""))

    chara_ok = any(votes.get(i, {}).get("yes") for i in CHARA_FAMILY_IDS if i in votes)
    chk("chara_lane", "Chara overlap OR Goel MD-lagna link", chara_ok,
        "need Boney antar overlap or rules8 lord link")

    goel_loaded = [i for i in GOEL_IDS if i in votes]
    goel_ok = (not goel_loaded) or any(votes[i].get("yes") for i in goel_loaded)
    chk("goel_lane", "Goel Yogini PL or Chara lord (rules8)", goel_ok,
        "progressive Yogini and/or Chara research timing")

    primary_yes = sum(1 for i in PRIMARY_DASHA_IDS if votes.get(i, {}).get("yes"))
    primary_ok = primary_yes >= MIN_PRIMARY_DASHA_YES
    chk("primary_dasha", f">= {MIN_PRIMARY_DASHA_YES} independent dasha clocks", primary_ok,
        f"{primary_yes} of {len([i for i in PRIMARY_DASHA_IDS if i in votes])} applicable")

    actual_ok = any(votes.get(i, {}).get("yes") for i in ACTUALIZATION_IDS if i in votes)
    chk("actualization", "Transit / multi-lagna / KP timing support", actual_ok,
        "differentiates promise from manifestation")

    release_ok = pct_ok and mandatory_ok and chara_ok and goel_ok and primary_ok and actual_ok
    failed = [c for c in checks if not c["passed"]]

    return {
        "release_confirmed": release_ok,
        "checks": checks,
        "failed_checks": failed,
        "policy": (
            "Confirmed date requires: >75% technique agreement, Vim+varga pillars, "
            "Chara lane, Goel rules8 lane, >=3 dasha clocks, and actualization support. "
            "Partial windows are shown but dates withheld."
        ),
    }


def _parse_tob(birth_time: str) -> tuple[int, int, int]:
    parts = [int(x) for x in birth_time.strip().replace(".", ":").split(":")]
    while len(parts) < 3:
        parts.append(0)
    return parts[0], parts[1], parts[2]


def _parse_dob_tuple(dob: str) -> tuple[int, int, int]:
    y, m, d = [int(x) for x in dob.split("-")]
    return y, m, d


def _sign_name(idx: int) -> str:
    return SIGNS[int(idx) % 12]


def _periods_from_dasha_rows(rows: list) -> list[dict[str, Any]]:
    """Normalize PyJHora antar rows -> {start, end, signs, planets}."""
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not row or len(row) < 3:
            continue
        try:
            start_str = str(row[-2])
            dur = float(row[-1])
            start = date.fromisoformat(start_str[:10])
            end = start + timedelta(days=max(1, int(dur * 365.25)))
        except (ValueError, TypeError):
            continue
        lords = list(row[:-2])
        signs: list[str] = []
        planets: list[str] = []
        for x in lords:
            if isinstance(x, int):
                signs.append(_sign_name(x))
            elif isinstance(x, str) and x in SIGNS:
                signs.append(x)
            elif isinstance(x, int) and 0 <= x < len(YOGINI_LORDS):
                planets.append(YOGINI_LORDS[x])
            elif isinstance(x, int) and 0 <= x < 8:
                planets.append(YOGINI_LORDS[x])
        out.append({"start": start, "end": end, "signs": signs, "planets": planets, "raw": lords})
    return out


def _overlaps(w_start: date, w_end: date, p_start: date, p_end: date) -> bool:
    return p_end > w_start and p_start < w_end


def load_supplemental_dashas(
    *,
    dob: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    timezone: float,
    place_name: str = "BirthPlace",
) -> dict[str, Any]:
    """Kaal Chakra, Lagnamsa, Yogini, Bhrigu Pada (Padhanadhamsa) via PyJHora."""
    out: dict[str, Any] = {}
    try:
        import os
        import sys
        from pathlib import Path
        src = Path(os.environ.get("PYJHORA_SRC", Path(__file__).parent / "pyjhora" / "src"))
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
        from jhora.panchanga import drik
        from jhora.horoscope.dhasa.graha import yogini as pj_yogini
        from jhora.horoscope.dhasa.raasi import kalachakra, lagnamsaka, padhanadhamsa
        from jhora import const

        drik.set_ayanamsa_mode("LAHIRI")
        dob_t = _parse_dob_tuple(dob)
        tob_t = _parse_tob(birth_time)
        place = drik.Place(place_name or "BirthPlace", latitude, longitude, timezone)

        kcd_rows = kalachakra.get_dhasa_bhukthi(
            dob_t, tob_t, place, dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA,
        )
        out["kalachakra"] = _periods_from_dasha_rows(kcd_rows)

        yog_rows = pj_yogini.get_dhasa_bhukthi(
            dob_t, tob_t, place, dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA,
        )
        yog_periods: list[dict[str, Any]] = []
        for row in yog_rows or []:
            if len(row) < 4:
                continue
            try:
                start = date.fromisoformat(str(row[2])[:10])
                dur = float(row[3])
                end = start + timedelta(days=max(1, int(dur * 365.25)))
                maha_i, ant_i = int(row[0]), int(row[1])
                planets = []
                for i in (maha_i, ant_i):
                    if 0 <= i < len(YOGINI_LORDS):
                        planets.append(YOGINI_LORDS[i])
                yog_periods.append({"start": start, "end": end, "signs": [], "planets": planets, "raw": row})
            except (ValueError, TypeError):
                continue
        out["yogini"] = yog_periods

        for label, factor in (("lagnamsa_d9", 9), ("lagnamsa_d10", 10), ("lagnamsa_d7", 7)):
            try:
                rows = lagnamsaka.get_dhasa_antardhasa(
                    dob_t, tob_t, place,
                    divisional_chart_factor=factor,
                    dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA,
                )
                out[label] = _periods_from_dasha_rows(rows)
            except Exception:
                out[label] = []

        try:
            bp_rows = padhanadhamsa.get_dhasa_antardhasa(
                dob_t, tob_t, place, method=1,
                dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA,
            )
            out["bhrigu_pada_d9"] = _periods_from_dasha_rows(bp_rows)
        except Exception:
            out["bhrigu_pada_d9"] = []

    except Exception as exc:
        out["error"] = str(exc)
    return out


def _dasha_sign_vote(
    periods: list[dict],
    w_start: date,
    w_end: date,
    target_signs: set[str],
) -> tuple[bool, str]:
    for p in periods:
        if not _overlaps(w_start, w_end, p["start"], p["end"]):
            continue
        for s in p.get("signs", []):
            if s in target_signs:
                return True, f"overlap {s}"
    return False, ""


def _dasha_planet_vote(
    periods: list[dict],
    w_start: date,
    w_end: date,
    target_planets: set[str],
) -> tuple[bool, str]:
    for p in periods:
        if not _overlaps(w_start, w_end, p["start"], p["end"]):
            continue
        for pl in p.get("planets", []):
            if pl in target_planets:
                return True, f"overlap {pl}"
    return False, ""


def score_technique_confluence(
    *,
    event_kind: str,
    w_start: date,
    w_end: date,
    vim_score: float,
    min_vim_score: float,
    lagna_hits: list[str],
    chara_hits: list[str],
    transit_ok: bool,
    varga_key: str,
    clues: list[str],
    kapoor_age_hits: list[str],
    kapoor_par_hits: list[str],
    kapoor_placement_ok: bool,
    target_signs: set[str],
    event_planets: set[str],
    supplemental: dict[str, Any],
    kp: dict[str, Any] | None = None,
    goel: dict[str, Any] | None = None,
    boney: dict[str, Any] | None = None,
    gk: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Each technique votes yes/no; >= 75% applicable = confirmed."""
    votes: list[dict[str, Any]] = []

    def add(tid: str, label: str, yes: bool, note: str = "", applicable: bool = True):
        if applicable:
            votes.append({"id": tid, "label": label, "yes": bool(yes), "note": note})

    add("vimshottari", "Vimshottari MD/AD + houses/varga", vim_score >= min_vim_score,
        f"score {vim_score}")
    add("chara", "Jaimini Chara antar overlap (Boney)", bool(chara_hits),
        "; ".join(chara_hits[:2]) if chara_hits else "no overlap")

    goel = goel or {}
    g_chara = goel.get("chara") or {}
    if g_chara.get("available"):
        add("chara_goel", "Chara MD-lagna lord link (rules8)", g_chara.get("yes", False),
            g_chara.get("note", ""))
    g_yog = goel.get("yogini") or {}
    if g_yog.get("available"):
        add("yogini_goel", "Progressive Yogini PL (rules8)", g_yog.get("yes", False),
            g_yog.get("note", ""))
    else:
        yog = supplemental.get("yogini") or []
        y_ok, y_note = _dasha_planet_vote(yog, w_start, w_end, event_planets)
        add("yogini", "Yogini dasha overlap (classic)", y_ok, y_note, applicable=bool(yog))
    boney = boney or {}
    if boney.get("available"):
        add(
            "boney_divisional",
            "Boney D1+D9+event varga dasha lords (rules45)",
            boney.get("tri_confluence", False) or boney.get("yes", False),
            boney.get("note", ""),
        )
    add("multi_lagna", "Birth + Chandra + dasa lagna", len(lagna_hits) >= 2,
        "; ".join(lagna_hits[:2]) if lagna_hits else "single/none")
    add("transit", "Jupiter/Saturn kendra transit support", transit_ok)
    gk = gk or {}
    if gk.get("available"):
        add(
            "gk_transit_dasha",
            "GK transit over MD/AD lord signs (rules11)",
            gk.get("yes", False),
            gk.get("note", ""),
        )
    varga_hit = any(varga_key in c for c in clues) or vim_score >= min_vim_score + 1
    add("varga", f"Event varga ({varga_key})", varga_hit, varga_key)
    add("kapoor_age", "Kapoor Age of Activation", bool(kapoor_age_hits),
        "; ".join(kapoor_age_hits[:2]) if kapoor_age_hits else "")
    add("kapoor_paribhraman", "Kapoor Paribhraman house-year", bool(kapoor_par_hits),
        "; ".join(kapoor_par_hits[:2]) if kapoor_par_hits else "")
    add("kapoor_placement", "Kapoor lord dignity at activation", kapoor_placement_ok)

    kcd = supplemental.get("kalachakra") or []
    k_ok, k_note = _dasha_sign_vote(kcd, w_start, w_end, target_signs)
    add("kalachakra", "Kaal Chakra dasha (Kapoor)", k_ok, k_note, applicable=bool(kcd))

    vfactor = EVENT_VARGA_FACTOR.get(event_kind, 9)
    lkey = f"lagnamsa_d{vfactor}" if vfactor in (7, 9, 10) else "lagnamsa_d9"
    if lkey not in supplemental and vfactor == 24:
        lkey = "lagnamsa_d9"
    lagn = supplemental.get(lkey) or supplemental.get("lagnamsa_d9") or []
    l_ok, l_note = _dasha_sign_vote(lagn, w_start, w_end, target_signs)
    add("lagnamsa", f"Lagnamsa dasha (D{vfactor})", l_ok, l_note, applicable=bool(lagn))

    bp = supplemental.get("bhrigu_pada_d9") or []
    b_ok, b_note = _dasha_sign_vote(bp, w_start, w_end, target_signs)
    add("bhrigu_pada", "Bhrigu Pada / Padhanadhamsa D9", b_ok, b_note,
        applicable=event_kind in ("marriage", "child", "career") and bool(bp))

    kp = kp or {}
    if kp.get("available"):
        add("kp_csl", "KP CSL promise (rules21)", kp.get("csl_promise", {}).get("yes", False),
            kp.get("csl_promise", {}).get("note", ""))
        add("kp_md", "KP MD signifies event houses", kp.get("md_signifies", {}).get("yes", False),
            kp.get("md_signifies", {}).get("note", ""))
        add("kp_ad", "KP AD signifies event houses", kp.get("ad_signifies", {}).get("yes", False),
            kp.get("ad_signifies", {}).get("note", ""))
        add("kp_sub", "KP sub-lord confirm (rules21)", kp.get("sub_lord_confirm", {}).get("yes", False),
            kp.get("sub_lord_confirm", {}).get("note", ""))
        add("kp_transit", "KP transit on cusp/significators", kp.get("transit_cusp", {}).get("yes", False),
            kp.get("transit_cusp", {}).get("note", ""))

    applicable = [v for v in votes if v.get("yes") is not None]
    yes_count = sum(1 for v in applicable if v["yes"])
    total = len(applicable) or 1
    pct = round(yes_count / total, 3)
    pct_confirmed = pct > CONFLUENCE_THRESHOLD

    base = {
        "threshold": CONFLUENCE_THRESHOLD,
        "yes_count": yes_count,
        "total_techniques": total,
        "confluence_pct": pct,
        "confluence_pct_display": int(round(pct * 100)),
        "pct_confirmed": pct_confirmed,
        "techniques": votes,
    }
    gate = evaluate_confirmed_release(base)
    release_ok = gate["release_confirmed"]
    base["release_gate"] = gate
    base["confirmed"] = release_ok
    base["verdict"] = (
        "confirmed" if release_ok
        else ("strong_partial" if pct_confirmed else ("weak_partial" if pct >= 0.6 else "withheld"))
    )
    return base
