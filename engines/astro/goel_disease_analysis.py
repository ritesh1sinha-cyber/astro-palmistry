#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chart-specific disease vulnerability analysis per Goel (rules7).
Uses only facts from precompute + computed vargas - no invented placements.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from goel_varga import (
    SIGNS,
    drekkana_sign,
    drekkana_third,
    house_from_lagna,
    house_from_sign,
    kalaka_origin,
    saptavimshamsha_sign,
    shashthamsha_sign,
)

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "goel_disease_book_data.json"

MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
WEAK = {"debilitated", "enemy_sign"}
STRONG = {"exalted", "own_sign", "moolatrikona", "great_friend_sign"}


def _load_book() -> dict:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Run build_goel_disease_data.py first  -  missing {DATA_PATH}")
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _deg(planet: dict) -> float:
    return float(planet.get("degree_in_sign", 0))


def _fmt_range(start: str, end: str) -> str:
    try:
        s = datetime.strptime(start[:10], "%Y-%m-%d").strftime("%b %Y")
        e = datetime.strptime(end[:10], "%Y-%m-%d").strftime("%b %Y")
        return f"{s} - {e}"
    except ValueError:
        return f"{start[:7]} - {end[:7]}"


def _afflicted(planet: str, data: dict, lagna: str) -> bool:
    if not data:
        return False
    dig = data.get("dignity", "")
    sign = data.get("sign", "")
    h = house_from_lagna(sign, lagna) if sign in SIGNS else data.get("house", 0)
    if dig in WEAK or h in (6, 8, 12):
        return True
    fs = data.get("functional_status", "")
    if fs in ("functional_malefic", "maraka") and h in (1, 7):
        return True
    return False


def analyze_disease_chart(pc: dict, book: dict | None = None) -> dict[str, Any]:
    """Return structured, evidence-linked disease analysis for one natal chart."""
    book = book or _load_book()
    planets = pc.get("planets", {})
    lagna = pc.get("meta", {}).get("lagna_sign", "")
    lagna_deg = float(pc.get("meta", {}).get("lagna_degree", pc.get("lagna", {}).get("degree_in_sign", 0)))
    hl = pc.get("house_lords", {})
    evidence: list[str] = []

    def _hl(n: int) -> dict:
        return hl.get(n, hl.get(str(n), {}))

    if not lagna or not planets:
        return {"error": "Missing lagna or planets in precompute data.", "evidence": []}

    def _house(sign: str) -> int:
        return house_from_lagna(sign, lagna) if sign in SIGNS else 0

    lord6 = _hl(6).get("lord", "")
    lord8 = _hl(8).get("lord", "")
    lord1 = _hl(1).get("lord", "")
    lord12 = _hl(12).get("lord", "")

    # D1 constitutional baseline
    baseline_notes: list[str] = []
    ll_data = planets.get(lord1, {})
    l6_data = planets.get(lord6, {})
    l8_data = planets.get(lord8, {})

    if l6_data:
        h6 = _house(l6_data.get("sign", ""))
        baseline_notes.append(
            f"6th lord {lord6} in {l6_data.get('sign')} (house {h6}, "
            f"{l6_data.get('dignity', 'neutral').replace('_', ' ')}) - primary illness significator."
        )
        evidence.append(f"D1: 6th lord {lord6} in house {h6}")
    if l8_data:
        h8 = _house(l8_data.get("sign", ""))
        baseline_notes.append(
            f"8th lord {lord8} in {l8_data.get('sign')} (house {h8}, "
            f"{l8_data.get('dignity', 'neutral').replace('_', ' ')}) - chronic/crisis health theme."
        )
        evidence.append(f"D1: 8th lord {lord8} in house {h8}")

    if ll_data.get("sign") and _house(ll_data["sign"]) == 8:
        baseline_notes.append(f"Lagna lord {lord1} in 8th house  -  Goel flags constitutional health tension.")
        evidence.append(f"D1: lagna lord {lord1} in 8th")

    if l8_data.get("sign") and _house(l8_data["sign"]) == 6 and lord8:
        baseline_notes.append(
            f"8th lord {lord8} in 6th  -  Goel 'opposite Raja Yoga': obstacles can convert to recovery through discipline."
        )
        evidence.append("D1: 8th lord in 6th (opposite Raja Yoga)")

    moon = planets.get("Moon", {})
    mars = planets.get("Mars", {})
    saturn = planets.get("Saturn", {})
    if moon and mars and saturn:
        if _afflicted("Moon", moon, lagna) and _house(mars.get("sign", "")) in (1, 4, 7, 8) and _house(saturn.get("sign", "")) in (1, 4, 7, 8):
            baseline_notes.append("Moon under stress with Mars and Saturn both angular  -  mind-body stress pattern (Goel).")
            evidence.append("D1: Moon + Mars + Saturn angular stress")

    afflicted_list = [p for p in planets if p in MALEFICS | {"Mercury", "Jupiter", "Venus"} and _afflicted(p, planets[p], lagna)]

    # Varga computations
    d6_lagna_sign = shashthamsha_sign(lagna, lagna_deg)
    varga_rows: list[dict] = []
    d27_map: dict[str, list[str]] = {}

    for pl, data in planets.items():
        if pl not in MALEFICS | {"Sun", "Moon", "Mercury", "Jupiter", "Venus"}:
            continue
        sign = data.get("sign", "")
        deg = _deg(data)
        if not sign:
            continue
        d3s = drekkana_sign(sign, deg)
        d6s = shashthamsha_sign(sign, deg)
        d27s = saptavimshamsha_sign(sign, deg)
        d6_h = house_from_sign(d6s, d6_lagna_sign)
        varga_rows.append({
            "planet": pl,
            "d1_sign": sign,
            "degree": round(deg, 2),
            "d3_sign": d3s,
            "d3_band": drekkana_third(deg),
            "kalaka": kalaka_origin(deg),
            "d6_sign": d6s,
            "d6_house": d6_h,
            "d27_sign": d27s,
            "d27_zone": book["d27_body_zones"].get(d27s, ""),
            "d3_body": book["sign_body_parts"].get(d3s, {}).get("external", ""),
        })
        d27_map.setdefault(d27s, []).append(pl)

    # D27 vulnerability zones
    zones: list[dict] = []
    trik_lords = {lord6, lord8, lord12} - {""}

    for d27_sign, pls in sorted(d27_map.items()):
        zone = book["d27_body_zones"].get(d27_sign, "")
        if not zone:
            continue
        malefic_here = [p for p in pls if p in MALEFICS]
        trik_here = [p for p in pls if p in trik_lords]
        reasons = []
        if malefic_here:
            reasons.append(f"malefic(s) {', '.join(malefic_here)} in D27 {d27_sign}")
        if trik_here:
            reasons.append(f"trik lord(s) {', '.join(trik_here)} in D27 {d27_sign}")
        if not reasons:
            continue
        severity = "medium"
        if "Saturn" in pls and "Rahu" in pls:
            severity = "high"
            reasons.append("Saturn + Rahu same D27 sign (Goel chronic/serious flag)")
            evidence.append(f"D27: Saturn+Rahu in {d27_sign} -> {zone}")
        if "Mars" in pls:
            reasons.append("Mars in zone  -  surgical/invasive tone possible")
        zones.append({
            "zone": zone,
            "d27_sign": d27_sign,
            "planets": pls,
            "reasons": reasons,
            "severity": severity,
        })

    zones.sort(key=lambda z: (0 if z["severity"] == "high" else 1, -len(z["planets"])))

    # Disease lord localization (D3 + kalaka)
    localization: list[dict] = []
    for lord, label in ((lord6, "6th lord"), (lord8, "8th lord")):
        data = planets.get(lord, {})
        if not data or not data.get("sign"):
            continue
        deg = _deg(data)
        d3s = drekkana_sign(data["sign"], deg)
        body = book["sign_body_parts"].get(d3s, {})
        origin = kalaka_origin(deg)
        localization.append({
            "lord": lord,
            "label": label,
            "d1": f"{data['sign']} house {_house(data['sign'])}",
            "d3_sign": d3s,
            "body_external": body.get("external", ""),
            "body_internal": body.get("internal", ""),
            "kalaka": origin,
            "kalaka_meaning": book["kalaka_rules"].get(origin, ""),
        })
        evidence.append(f"D3: {label} {lord} -> {d3s} ({body.get('external', '')}); kalaka={origin}")

    # Nakshatra disease clusters
    nak_clusters: list[dict] = []
    nak_book = book.get("nakshatra_disease_tendency", {})
    moon_nak = moon.get("nakshatra", pc.get("meta", {}).get("moon_nakshatra", ""))
    lagna_nak = pc.get("meta", {}).get("lagna_nakshatra", "")
    if lagna_nak in ("?", "", None):
        lagna_nak = ""

    for label, nak in (("Moon birth star", moon_nak), ("Lagna star", lagna_nak)):
        if not nak:
            continue
        canon = nak
        tend = nak_book.get(canon, "")
        if not tend:
            for k in nak_book:
                if k.lower() in nak.lower() or nak.lower() in k.lower():
                    tend = nak_book[k]
                    canon = k
                    break
        if tend:
            nak_clusters.append({"source": label, "nakshatra": canon, "tendency": tend})
            evidence.append(f"Nakshatra: {label} {canon} -> {tend[:80]}")

    # Cross-check nakshatra vs top D27 zone
    primary_zone = zones[0]["zone"] if zones else ""
    for nc in nak_clusters:
        nc["aligns_with_d27"] = any(
            word in primary_zone.lower()
            for word in nc["tendency"].lower().split(",")[0].split()[:3]
        ) if primary_zone else False

    # D6 disease type for key lords
    d6_timing: list[dict] = []
    for lord, label in ((lord6, "6th lord"), (lord8, "8th lord")):
        row = next((r for r in varga_rows if r["planet"] == lord), None)
        if not row:
            continue
        h = row["d6_house"]
        meaning = book["d6_house_meanings"].get(str(h), "")
        tone = "acute/curable" if h == 6 else ("chronic" if h == 8 else ("hospital" if h == 12 else "mixed"))
        d6_timing.append({
            "lord": lord,
            "label": label,
            "d6_house": h,
            "d6_sign": row["d6_sign"],
            "tone": tone,
            "meaning": meaning,
        })
        evidence.append(f"D6: {label} in D6 house {h} -> {tone}")

    # Vimshottari health windows
    vim = pc.get("vimshottari", {})
    today = date.today()
    watch_lords = {lord6, lord8, lord12} - {""}
    active: list[dict] = []
    upcoming: list[dict] = []

    cur_md = vim.get("current_md", {})
    md_lord = cur_md.get("md_lord", "")
    if md_lord in watch_lords:
        active.append({
            "level": "mahadasha",
            "lord": md_lord,
            "range": _fmt_range(cur_md.get("start", ""), cur_md.get("end", "")),
            "note": f"{md_lord} rules a trik house (6th/8th/12th) in your chart.",
        })
    elif md_lord and _house(planets.get(md_lord, {}).get("sign", "")) in (6, 8, 12):
        active.append({
            "level": "mahadasha",
            "lord": md_lord,
            "range": _fmt_range(cur_md.get("start", ""), cur_md.get("end", "")),
            "note": f"{md_lord} mahadasha while {md_lord} sits in house {_house(planets[md_lord]['sign'])} (dusthana health theme).",
        })

    role_note = {
        lord6: "6th lord - acute illness window",
        lord8: "8th lord - chronic/crisis health window",
        lord12: "12th lord - confinement/recovery theme",
    }

    for ad in vim.get("current_md_antardashas", []):
        ad_l = ad.get("ad_lord", "")
        if ad_l in watch_lords and ad.get("status") in ("current", "future"):
            entry = {
                "level": "antardasha",
                "lord": ad_l,
                "range": _fmt_range(ad.get("start", ""), ad.get("end", "")),
                "status": ad.get("status", ""),
                "note": role_note.get(ad_l, f"Sub-period of {ad_l} activates its health role."),
            }
            (active if ad.get("status") == "current" else upcoming).append(entry)
        elif ad.get("status") in ("current", "future") and ad_l and _house(planets.get(ad_l, {}).get("sign", "")) in (6, 8, 12):
            entry = {
                "level": "antardasha",
                "lord": ad_l,
                "range": _fmt_range(ad.get("start", ""), ad.get("end", "")),
                "status": ad.get("status", ""),
                "note": f"{ad_l} sub-period while {ad_l} occupies house {_house(planets[ad_l]['sign'])}.",
            }
            (active if ad.get("status") == "current" else upcoming).append(entry)

    for md in vim.get("sequence", []):
        if md.get("md_lord") not in watch_lords:
            continue
        try:
            end = datetime.strptime(md["end"][:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if end < today:
            continue
        try:
            start = datetime.strptime(md["start"][:10], "%Y-%m-%d").date()
        except ValueError:
            start = today
        if start <= today <= end:
            continue
        if not any(u.get("lord") == md["md_lord"] and u.get("level") == "mahadasha" for u in upcoming):
            upcoming.append({
                "level": "mahadasha",
                "lord": md["md_lord"],
                "range": _fmt_range(md["start"], md["end"]),
                "note": f"Full {md['md_lord']} mahadasha  -  long health-theme window.",
            })

    upcoming = upcoming[:4]

    # Yogini overlay
    yogini = pc.get("yogini", {})
    yogini_watch: list[str] = []
    yh = book.get("yogini_health_tone", {})
    cur_y = yogini.get("current_yogini")
    if cur_y:
        name = cur_y.get("yogini", "")
        if name in yh:
            yogini_watch.append(f"Current Yogini {name}: {yh[name]}")
            evidence.append(f"Yogini: {name} active")
    nxt_y = yogini.get("next_yogini")
    if nxt_y and nxt_y.get("yogini") in ("Ulka", "Pingala", "Bhramari", "Sankata"):
        yogini_watch.append(f"Next Yogini {nxt_y['yogini']} ({_fmt_range(nxt_y['start'], nxt_y['end'])}): {yh.get(nxt_y['yogini'], '')}")

    # Remedies  -  only for planets flagged in THIS chart
    remedy_targets: list[str] = []
    cur_ad = next((a for a in vim.get("current_md_antardashas", []) if a.get("status") == "current"), None)
    if cur_md.get("md_lord"):
        remedy_targets.append(cur_md["md_lord"])
    if cur_ad and cur_ad.get("ad_lord"):
        remedy_targets.append(cur_ad["ad_lord"])
    for pl in afflicted_list:
        if pl not in remedy_targets:
            remedy_targets.append(pl)
    for pl in (lord6, lord8):
        if pl and pl not in remedy_targets:
            remedy_targets.append(pl)

    remedies = []
    seen = set()
    for pl in remedy_targets:
        if pl in seen or pl not in book.get("planet_remedy", {}):
            continue
        seen.add(pl)
        r = book["planet_remedy"][pl]
        why = []
        if pl == lord6:
            why.append("6th lord in your chart")
        if pl == lord8:
            why.append("8th lord in your chart")
        if pl in afflicted_list:
            why.append(f"afflicted in D1 ({planets[pl].get('sign')} house {_house(planets[pl].get('sign', ''))})")
        if cur_md.get("md_lord") == pl:
            why.append("current mahadasha lord")
        if cur_ad and cur_ad.get("ad_lord") == pl:
            why.append("current antardasha lord")
        remedies.append({"planet": pl, "why": why, **r})

    # Universal Goel health practice
    remedies.append({
        "planet": "General",
        "why": ["Goel health chapter  -  supportive for all charts"],
        "mantra": "Maha Mrityunjaya Japa (108x daily for 40 days when under health stress)",
        "charity": "Serve patients or elderly; avoid neglect of routine checkups",
        "gem": "None required  -  mantra and discipline first",
    })

    confidence = "medium"
    if zones and (active or nak_clusters):
        confidence = "high" if zones[0].get("severity") == "high" else "medium"
    elif not zones:
        confidence = "low"

    return {
        "disclaimer": "Astrological study for awareness and prevention only  -  not medical diagnosis or treatment. Consult a licensed physician for health concerns.",
        "confidence": confidence,
        "constitutional_baseline": baseline_notes,
        "afflicted_planets": afflicted_list,
        "d27_vulnerability_zones": zones[:5],
        "d3_localization": localization,
        "nakshatra_clusters": nak_clusters,
        "d6_disease_type": d6_timing,
        "varga_detail": varga_rows,
        "active_health_periods": active,
        "upcoming_health_windows": upcoming,
        "yogini_health": yogini_watch,
        "remedies": remedies[:6],
        "evidence": evidence,
        "d6_lagna_sign": d6_lagna_sign,
    }
