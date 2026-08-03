#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Goel D9 chart analysis - all single-chart book topics (rules3)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from astro_precompute import get_dignity
from goel_marriage_life import analyze_marriage_life
from goel_marriage_timing import compute_marriage_timing
from goel_navamsha_coverage import BOOK_TOPICS, SIGN_LORD, VISH_KARAKATWA
from goel_varga import (
    SIGNS,
    house_from_lagna,
    house_from_sign,
    is_pushkar_navamsha,
    is_vargottama,
    is_vish_navamsha,
    navamsha_part,
    navamsha_sign,
)

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "goel_navamsha_book_data.json"
MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
BENEFICS = {"Moon", "Mercury", "Jupiter", "Venus"}
GRAHAS = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}
KENDRA_TRIKONA = {1, 4, 5, 7, 9, 10}


def _load_book() -> dict:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Run build_navamsha_data.py first - missing {DATA_PATH}")
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _deg(data: dict) -> float:
    return float(data.get("degree_in_sign", 0))


def _hl(hl: dict, n: int) -> dict:
    return hl.get(n, hl.get(str(n), {}))


def _fmt_range(start: str, end: str) -> str:
    from datetime import datetime

    try:
        s = datetime.strptime(start[:10], "%Y-%m-%d").strftime("%b %Y")
        e = datetime.strptime(end[:10], "%Y-%m-%d").strftime("%b %Y")
        return f"{s} - {e}"
    except ValueError:
        return f"{start[:7]} - {end[:7]}"


def _planets_in_house(d9_map: dict[str, str], ref: str, house: int) -> list[str]:
    return [p for p, s in d9_map.items() if house_from_sign(s, ref) == house]


def _d9_signs(pc: dict) -> tuple[str, dict[str, str], dict[str, dict]]:
    lagna = pc.get("meta", {}).get("lagna_sign", "") or pc.get("lagna", {}).get("sign", "")
    lagna_deg = float(
        pc.get("meta", {}).get("lagna_degree", pc.get("lagna", {}).get("degree_in_sign", 0))
    )
    planets = pc.get("planets", {})
    d9_lagna = navamsha_sign(lagna, lagna_deg) if lagna else ""
    d9_map: dict[str, str] = {}
    enriched: dict[str, dict] = {}

    for pl, data in planets.items():
        if pl not in GRAHAS or "sign" not in data:
            continue
        d1 = data["sign"]
        deg = _deg(data)
        d9 = data.get("navamsha_sign") or navamsha_sign(d1, deg)
        d9_map[pl] = d9
        enriched[pl] = {
            "d1_sign": d1,
            "d9_sign": d9,
            "d1_house": data.get("house") or house_from_lagna(d1, lagna),
            "d9_house": house_from_sign(d9, d9_lagna) if d9_lagna else 0,
            "d1_dignity": data.get("dignity") or get_dignity(pl, d1),
            "d9_dignity": get_dignity(pl, d9),
            "vargottama": is_vargottama(d1, d9),
            "vish": is_vish_navamsha(d1, deg),
            "pushkar": is_pushkar_navamsha(d1, deg),
            "navamsha_part": navamsha_part(d1, deg),
            "retrograde": data.get("retrograde", False),
        }
    return d9_lagna, d9_map, enriched


def _affliction_count(house_planets: list[str]) -> tuple[int, int]:
    aff = sum(1 for p in house_planets if p in MALEFICS)
    ben = sum(1 for p in house_planets if p in BENEFICS)
    return aff, ben


def _build_coverage(status_map: dict[str, tuple[str, str]]) -> list[dict]:
    out = []
    for t in BOOK_TOPICS:
        st, detail = status_map.get(t["key"], ("partial", "Not evaluated"))
        out.append({**t, "status": st, "detail": detail})
    return out


def analyze_navamsha_chart(pc: dict, book: dict | None = None) -> dict[str, Any]:
    book = book or _load_book()
    lagna = pc.get("meta", {}).get("lagna_sign", "")
    hl = pc.get("house_lords", {})
    planets = pc.get("planets", {})
    d9_lagna, d9_map, d9_enriched = _d9_signs(pc)

    if not d9_lagna or not d9_map:
        return {"error": "Could not compute D9 from chart degrees.", "evidence": []}

    lord7_d1 = _hl(hl, 7).get("lord", "")
    lord7_d9_sign = SIGNS[(SIGNS.index(d9_lagna) + 6) % 12]
    lord7_d9 = SIGN_LORD[lord7_d9_sign]
    d9_lagna_lord = SIGN_LORD[d9_lagna]
    lord2_d1 = _hl(hl, 2).get("lord", "")
    lord9_d9_sign = SIGNS[(SIGNS.index(d9_lagna) + 8) % 12]

    d9_houses = {h: _planets_in_house(d9_map, d9_lagna, h) for h in range(1, 13)}
    d1_h7 = _planets_in_house({p: d["d1_sign"] for p, d in d9_enriched.items()}, lagna, 7)

    venus = d9_enriched.get("Venus", {})
    jupiter = d9_enriched.get("Jupiter", {})
    mars = d9_enriched.get("Mars", {})
    l7d9 = d9_enriched.get(lord7_d9, {})
    d9_ll = d9_enriched.get(d9_lagna_lord, {})
    lord2_d9 = d9_enriched.get(lord2_d1, {}) if lord2_d1 else {}

    # DK foreign marriage
    dk = ""
    dk_data: dict = {}
    for k in pc.get("cara_karakas", {}).get("karakas", []):
        if k.get("role") == "Darakaraka":
            dk = k.get("planet", "")
            dk_data = d9_enriched.get(dk, {})
            break

    flags: list[str] = []
    vish_dasha: list[str] = []
    for pl, e in d9_enriched.items():
        if e.get("vargottama"):
            flags.append(f"{pl} vargottama")
        if e.get("vish"):
            flags.append(f"{pl} vish navamsha")
            vish_dasha.append(
                f"{pl} dasha: watch {VISH_KARAKATWA.get(pl, 'significations')} (Goel Ch.7)"
            )
        if e.get("pushkar"):
            flags.append(f"{pl} pushkar navamsha")

    aff_d9_7, ben_d9_7 = _affliction_count(d9_houses[7])
    aff_d1_7, ben_d1_7 = _affliction_count(d1_h7)
    aff_7lord = (
        l7d9.get("d9_dignity") in ("debilitated", "enemy_sign")
        or (
            l7d9.get("d9_house") in (6, 8)
            and l7d9.get("d9_dignity") not in ("exalted", "own_sign", "moolatrikona")
        )
    )

    trajectory: list[str] = []
    for pl in GRAHAS - {"Rahu", "Ketu"}:
        e = d9_enriched.get(pl, {})
        if not e:
            continue
        d1d, d9d = e.get("d1_dignity"), e.get("d9_dignity")
        if d1d == "debilitated" and d9d in ("exalted", "own_sign", "moolatrikona"):
            trajectory.append(f"{pl} D1 debil -> D9 strong ({e['d9_sign']})")
        elif d1d in ("exalted", "own_sign") and d9d in ("debilitated", "enemy_sign"):
            trajectory.append(f"{pl} D1 strong -> D9 weak ({e['d9_sign']})")

    denial_hits: list[str] = []
    if aff_d9_7 >= 3 and ben_d9_7 == 0:
        denial_hits.append("D9 7th: 3+ malefics, no benefic")
    if aff_d1_7 >= 3 and ben_d1_7 == 0:
        denial_hits.append("D1 7th: 3+ malefics, no benefic")
    if d9_houses[7] and any(p in MALEFICS for p in d9_houses[7]) and d9_houses[9]:
        denial_hits.append("Malefic in D9 7th + graha in D9 9th")
    if venus.get("d9_house") == 1 and d9_houses[1] == ["Venus"]:
        denial_hits.append("Venus alone in D9 lagna (male denial rule)")
    if jupiter.get("d9_house") == 1 and d9_houses[1] == ["Jupiter"]:
        denial_hits.append("Jupiter alone in D9 lagna (female denial rule)")

    # Ch4 multiple relations
    multiple_signals: list[str] = []
    if d9_ll and (
        d9_ll.get("vargottama")
        or d9_ll.get("d9_dignity") in ("exalted", "debilitated", "own_sign")
    ):
        multiple_signals.append(f"D9 lagna lord {d9_lagna_lord} in special status ({d9_ll['d9_dignity']})")
    upachaya_occupied = sum(1 for h in (3, 6, 10, 11) if d9_houses[h])
    if d9_houses[10] and upachaya_occupied >= 2:
        multiple_signals.append(f"D9 upachaya load: H10 {d9_houses[10]} + {upachaya_occupied} upachaya occupied")
    if jupiter and (
        jupiter.get("d9_dignity") in ("debilitated", "enemy_sign") or jupiter.get("retrograde")
    ) and jupiter.get("d9_house") in (1, 7, 10):
        multiple_signals.append("Afflicted Jupiter on D9 lagna/7th/10th axis (Ch.4)")
    if lord2_d9 and (
        lord2_d9.get("d9_house") in (6, 8, 12)
        or lord2_d9.get("d9_dignity") in ("debilitated", "enemy_sign")
    ):
        multiple_signals.append(f"D1 2nd lord {lord2_d1} weak in D9 H{lord2_d9.get('d9_house')}")

    # Mars + Venus D9 sexual urge
    sexual_urge = False
    sexual_note = ""
    if mars and venus:
        if mars["d9_sign"] == venus["d9_sign"]:
            sexual_urge = True
            sexual_note = "Mars + Venus conjunct in D9 - high sexual drive (Goel Ch.4)"
        elif abs(SIGNS.index(mars["d9_sign"]) - SIGNS.index(venus["d9_sign"])) == 6:
            sexual_urge = True
            sexual_note = "Mars opposite Venus in D9 - high preoccupation (Goel Ch.4)"

    # Beeja / rashi tulya
    beeja_strong: list[str] = []
    beeja_weak: list[str] = []
    for pl, e in d9_enriched.items():
        h = house_from_lagna(e["d9_sign"], lagna)
        if h in KENDRA_TRIKONA:
            beeja_strong.append(f"{pl} D9->{e['d9_sign']} falls D1 H{h} (kendra/trikona)")
        elif h in (6, 8, 12):
            beeja_weak.append(f"{pl} D9->{e['d9_sign']} falls D1 H{h} (trik)")

    # Religion / spirituality
    spiritual_signals: list[str] = []
    if d9_houses[9]:
        spiritual_signals.append(f"D9 9th occupied: {d9_houses[9]}")
    ketu = d9_enriched.get("Ketu")
    if jupiter and ketu and jupiter["d9_sign"] == ketu["d9_sign"]:
        spiritual_signals.append("Jupiter + Ketu in D9 - religious insight (Goel Ch.8)")
    religion_change: list[str] = []
    lord8_d9 = SIGN_LORD[SIGNS[(SIGNS.index(d9_lagna) + 7) % 12]]
    l8d9 = d9_enriched.get(lord8_d9, {})
    if l8d9 and l8d9.get("d9_house") in (9, 8) or house_from_sign(l8d9.get("d9_sign", ""), d9_lagna) in (8, 9):
        religion_change.append(f"D9 8th lord {lord8_d9} linked to D9 8th/9th religion axis")
    if lord2_d9 and lord2_d9.get("d9_dignity") in ("debilitated", "enemy_sign"):
        religion_change.append(f"Weak D1 2nd lord {lord2_d1} in D9 - sanskar shift possible")

    # DK foreign
    dk_foreign: list[str] = []
    if dk and dk_data:
        if dk in ("Rahu", "Ketu"):
            dk_foreign.append(f"DK {dk} - foreign/other spouse (Goel; confirm in D9 H{dk_data.get('d9_house')})")
        elif dk == "Saturn":
            dk_foreign.append(f"DK Saturn - status/caste mismatch theme in D9 H{dk_data.get('d9_house')}")
        if dk_data.get("d9_house") in (9, 12):
            dk_foreign.append(f"DK in D9 H{dk_data['d9_house']} - distant/other union")

    # Marriage timing windows from vimshottari
    timing_lords = {lord7_d9, d9_lagna_lord, "Venus", "Jupiter", lord7_d1} - {""}
    marriage_windows: list[dict] = []
    vim = pc.get("vimshottari", {})
    cur_md = vim.get("current_md", {})
    for ad in vim.get("current_md_antardashas", []):
        ad_l = ad.get("ad_lord", "")
        if ad_l in timing_lords and ad.get("status") in ("current", "future"):
            marriage_windows.append({
                "lord": ad_l,
                "range": _fmt_range(ad.get("start", ""), ad.get("end", "")),
                "status": ad.get("status", ""),
                "note": f"Touches D9 marriage axis ({ad_l})",
            })
    for md in vim.get("sequence", [])[:8]:
        if md.get("md_lord") in timing_lords:
            marriage_windows.append({
                "lord": md["md_lord"],
                "range": _fmt_range(md.get("start", ""), md.get("end", "")),
                "status": "future_md",
                "note": "Mahadasha of D9 marriage significator",
            })
    marriage_windows = marriage_windows[:4]

    # D9 8th mangalya (study-only, cautious)
    aff_d9_8, _ = _affliction_count(d9_houses[8])
    mangalya_note = ""
    if aff_d9_8 >= 2:
        mangalya_note = "D9 8th under malefic load - Goel mangalya study flag (confluence only; not alarmist)"

    karaka_notes = []
    if venus:
        karaka_notes.append(
            f"Venus: D1 {venus['d1_sign']} H{venus['d1_house']} ({venus['d1_dignity']}); "
            f"D9 {venus['d9_sign']} H{venus['d9_house']} ({venus['d9_dignity']})"
        )
    if jupiter:
        karaka_notes.append(
            f"Jupiter: D1 {jupiter['d1_sign']} H{jupiter['d1_house']} ({jupiter['d1_dignity']}); "
            f"D9 {jupiter['d9_sign']} H{jupiter['d9_house']} ({jupiter['d9_dignity']})"
        )

    timing_payload = {
        "lord7_d1": lord7_d1,
        "lord7_d9": lord7_d9,
        "d9_lagna_lord": d9_lagna_lord,
        "d1_h7_planets": d1_h7,
        "d9_houses": d9_houses,
        "d9_enriched": d9_enriched,
    }
    marriage_timing = compute_marriage_timing(pc, timing_payload)
    marriage_life = analyze_marriage_life(pc, {
        "d9_houses": d9_houses,
        "d9_enriched": d9_enriched,
        "d9_lagna": d9_lagna,
        "lord7_d9_sign": lord7_d9_sign,
        "lord7_d9": lord7_d9,
        "darakaraka": dk,
        "sexual_urge": sexual_urge,
    })

    status_map: dict[str, tuple[str, str]] = {
        "d9_cast": ("checked", f"D9 lagna {d9_lagna} from Parashari modality method"),
        "pushkar": ("checked" if any("pushkar" in f for f in flags) else "checked", ", ".join(f for f in flags if "pushkar" in f) or "Computed for all grahas"),
        "vargottama": ("checked" if any("vargottama" in f for f in flags) else "checked", ", ".join(f for f in flags if "vargottama" in f) or "None flagged"),
        "vish": ("checked" if any("vish" in f for f in flags) else "checked", ", ".join(f for f in flags if "vish" in f) or "None flagged"),
        "deities": ("partial", "Deity/tattva table not automated - use book Ch.1 for pada nuance"),
        "marriage_promise": ("checked", f"D1 7th {d1_h7 or 'empty'}; D9 7th {d9_houses[7] or 'empty'}; denial {len(denial_hits)} hits"),
        "marriage_quality": ("checked", karaka_notes[0] if karaka_notes else "Karaka reviewed"),
        "d1_d9_trajectory": ("checked" if trajectory else "checked", "; ".join(trajectory[:2]) or "No strong D1-D9 flip"),
        "denial": ("checked", "; ".join(denial_hits) if denial_hits else "No denial rule fired"),
        "separation": ("checked", f"D9 7th lord {lord7_d9} H{l7d9.get('d9_house')}; D9 4th {d9_houses[4] or 'empty'}"),
        "spouse_longevity": ("partial" if mangalya_note else "checked", mangalya_note or "D9 7th/8th reviewed - no strong malefic cluster"),
        "foreign_marriage": ("checked" if dk_foreign else "checked", "; ".join(dk_foreign) if dk_foreign else f"DK {dk or '?'} D9 H{dk_data.get('d9_house', '?')}"),
        "match_making": ("n_a", "Requires partner chart (Goel Ch.3 synastry)"),
        "multiple_relations": ("checked" if multiple_signals else "checked", "; ".join(multiple_signals[:2]) or "No Ch.4 multi-marriage cluster"),
        "affairs_sexual": ("checked", sexual_note if sexual_urge else "Mars-Venus D9 not conjunct/opposite"),
        "sanskar_2nd": ("checked", f"D1 2nd lord {lord2_d1} in D9 H{lord2_d9.get('d9_house', '?')}" if lord2_d1 else "2nd lord unknown"),
        "marriage_timing": (
            "checked" if marriage_timing.get("windows") else "partial",
            "; ".join(f"{w['lord']} {w['range']}" for w in marriage_timing.get("windows", [])[:2])
            or "No dasha window flagged",
        ),
        "d30_timing": ("partial", "D30 from extract table possible; full rule needs D30 lagna cross-check"),
        "jaimini_timing": ("partial", "Jaimini chara dasha in separate lane; DK available for timing"),
        "transit_timing": ("partial", "Live Jupiter/Saturn transit to D9 lagna lord - use gochar section"),
        "beeja": ("checked", f"{len(beeja_strong)} planets strong in Beeja; {len(beeja_weak)} in D1 trik"),
        "vish_dasha": ("checked" if vish_dasha else "checked", "; ".join(vish_dasha[:3]) or "No vish navamsha dasha warnings"),
        "khara_64": ("partial", "Khara/64th/22nd need hora + division math - flags vish severity only"),
        "devotion": ("checked" if spiritual_signals else "checked", "; ".join(spiritual_signals[:2]) or "D9 9th/trines reviewed"),
        "religion_change": ("checked" if religion_change else "checked", "; ".join(religion_change) if religion_change else "No strong change-of-faith combo"),
        "occult": ("partial", "Ketu/Mercury 8th link - see D9 8th occupants: " + str(d9_houses[8])),
        "worship_timing": ("partial", "Worship timing tied to dasha of D9 9th lord / Jupiter"),
    }

    return {
        "disclaimer": book.get("disclaimer", ""),
        "d9_lagna": d9_lagna,
        "d9_lagna_lord": d9_lagna_lord,
        "d1_lagna": lagna,
        "lord7_d1": lord7_d1,
        "lord2_d1": lord2_d1,
        "lord7_d9_sign": lord7_d9_sign,
        "lord7_d9": lord7_d9,
        "darakaraka": dk,
        "d9_enriched": d9_enriched,
        "d9_houses": d9_houses,
        "d1_h7_planets": d1_h7,
        "constitutional_baseline": [
            f"D9 lagna {d9_lagna} (D1 {lagna}) - marriage desire/inclination (Goel Ch.2).",
            f"D9 7th {lord7_d9_sign}: {d9_houses[7] or 'empty'}; lord {lord7_d9} in D9 H{l7d9.get('d9_house', '?')}.",
        ],
        "marriage_karaka": karaka_notes,
        "trajectory": trajectory,
        "flags": flags,
        "denial_hits": denial_hits,
        "aff_d9_7": aff_d9_7,
        "ben_d9_7": ben_d9_7,
        "aff_d1_7": aff_d1_7,
        "ben_d1_7": ben_d1_7,
        "aff_7lord": aff_7lord,
        "multiple_signals": multiple_signals,
        "sexual_urge": sexual_urge,
        "sexual_note": sexual_note,
        "beeja_strong": beeja_strong,
        "beeja_weak": beeja_weak,
        "spiritual_signals": spiritual_signals,
        "religion_change": religion_change,
        "dk_foreign": dk_foreign,
        "marriage_windows": marriage_windows,
        "marriage_timing_detail": marriage_timing,
        "marriage_life": marriage_life,
        "vish_dasha": vish_dasha,
        "mangalya_note": mangalya_note,
        "coverage": _build_coverage(status_map),
        "evidence": karaka_notes + trajectory + flags + denial_hits,
    }
