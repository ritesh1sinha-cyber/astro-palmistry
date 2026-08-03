#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Goel health confluence: merge chart layers into scored themes.
Only themes where >= CONFLUENCE_MIN of *relevant* lanes agree become predictions.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFLUENCE_MIN = 70

THEMES: dict[str, dict[str, Any]] = {
    "face_eyes_oral": {
        "title": "Face, eyes, mouth & head",
        "core_lanes": ["D27", "D3_6", "Lagna nak", "Yogini"],
        "keywords": [
            "face", "eye", "mouth", "head", "dental", "teeth", "ear", "throat", "oral", "ent",
        ],
        "prediction": (
            "Stress in your chart tends to show through the face and head zone first: eyes, sinuses, "
            "teeth, or tension headaches before illness spreads elsewhere."
        ),
        "prevent": "Eye/dental checks, screen breaks, salt moderation, steady sleep.",
    },
    "blood_pressure_heart": {
        "title": "Blood pressure & circulation",
        "core_lanes": ["Moon nak", "Lagna nak", "D27", "D1"],
        "keywords": ["blood pressure", "bp", "arter", "vein", "heart", "circulation", "hypertension"],
        "prediction": (
            "Circulation and blood-pressure sensitivity is a repeating pattern; routine vitals "
            "during heavy dasha years are worthwhile."
        ),
        "prevent": "Annual BP check, walking, limit excess salt when stressed.",
    },
    "ent_lungs_breath": {
        "title": "Lungs, breathing & ENT",
        "core_lanes": ["Lagna nak", "Moon nak", "D27", "D6"],
        "keywords": ["lung", "breath", "asthma", "bronch", "ent", "respiratory", "cough", "chest"],
        "prediction": (
            "Upper airway and chest sensitivity can flare with colds, allergies, or fatigue; "
            "treat early symptoms rather than pushing through."
        ),
        "prevent": "Avoid smoke/dust, warm fluids in season change, light breathing exercise.",
    },
    "bowel_gut": {
        "title": "Bowels, colon & digestion",
        "core_lanes": ["Moon nak", "D3_8", "Moon sign", "Timing", "D1"],
        "keywords": ["bowel", "colon", "intestin", "digest", "stomach", "abdom", "navel", "liver", "gut"],
        "prediction": (
            "Digestive rhythm is a weak link: irregular meals, worry, or cold foods may disturb "
            "bowels or abdominal comfort."
        ),
        "prevent": "Fixed meal times, warm cooked food when under stress, do not ignore persistent gut pain.",
    },
    "urinary_reproductive": {
        "title": "Urinary & pelvic area",
        "core_lanes": ["D3_8", "D27", "D1", "Timing"],
        "keywords": ["urinary", "genital", "kidney", "bladder", "reproductive", "pelvic"],
        "prediction": (
            "The 8th-house thread highlights the pelvic and urinary zone; hydration and timely "
            "checkups matter more than fear."
        ),
        "prevent": "Stay hydrated, do not ignore recurring pelvic or urinary discomfort.",
    },
    "chronic_hidden": {
        "title": "Slow-building / chronic strain",
        "core_lanes": ["D27", "D1", "Timing", "Yogini", "D6"],
        "keywords": ["chronic", "8th", "hidden", "debilitated", "long-term", "saturn", "rahu"],
        "prediction": (
            "This is a slow-burn signature: symptoms may build quietly during Jupiter or Saturn "
            "windows; patience, discipline, and early testing beat last-minute crisis care."
        ),
        "prevent": "Yearly full checkup, steady routine, Maha Mrityunjaya or Hanuman practice when under strain.",
    },
}


def _blob(*parts: str) -> str:
    return " ".join(p for p in parts if p).lower()


def _kw(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def _sign_body() -> dict:
    p = Path(__file__).resolve().parent / "goel_disease_book_data.json"
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8")).get("sign_body_parts", {})
    return {}


def build_health_confluence(analysis: dict[str, Any], pc: dict | None = None) -> dict[str, Any]:
    pc = pc or {}
    planets = pc.get("planets", {})
    lagna = pc.get("meta", {}).get("lagna_sign", "")
    moon_sign = planets.get("Moon", {}).get("sign", "")

    zones = analysis.get("d27_vulnerability_zones", [])
    loc6 = next((x for x in analysis.get("d3_localization", []) if "6th" in x.get("label", "")), None)
    loc8 = next((x for x in analysis.get("d3_localization", []) if "8th" in x.get("label", "")), None)
    moon_nak = next((n for n in analysis.get("nakshatra_clusters", []) if "Moon" in n.get("source", "")), None)
    lagna_nak = next((n for n in analysis.get("nakshatra_clusters", []) if "Lagna" in n.get("source", "")), None)
    d6_6 = next((d for d in analysis.get("d6_disease_type", []) if "6th" in d.get("label", "")), None)
    d6_8 = next((d for d in analysis.get("d6_disease_type", []) if "8th" in d.get("label", "")), None)
    active = analysis.get("active_health_periods", [])
    upcoming = analysis.get("upcoming_health_windows", [])[:2]
    yogini = analysis.get("yogini_health", [])
    baseline = " ".join(analysis.get("constitutional_baseline", []))
    afflicted = analysis.get("afflicted_planets", [])
    sign_body = _sign_body()

    from goel_varga import house_from_lagna

    lane_results: dict[str, tuple[bool, str]] = {}

    # D27 - best matching zone per theme evaluated per-theme later; store all zones text
    zone_blobs = [
        _blob(z.get("zone", ""), " ".join(z.get("reasons", [])), z.get("d27_sign", ""))
        for z in zones[:3]
    ]

    if loc6:
        lane_results["D3_6"] = (
            True,
            loc6.get("body_external", ""),
        )  # placeholder; theme filter below
    if loc8:
        lane_results["D3_8"] = (True, loc8.get("body_external", ""))
    if moon_nak:
        lane_results["Moon nak"] = (True, moon_nak.get("tendency", ""))
    if lagna_nak:
        lane_results["Lagna nak"] = (True, lagna_nak.get("tendency", ""))
    if moon_sign:
        mb = sign_body.get(moon_sign, {})
        lane_results["Moon sign"] = (True, _blob(mb.get("external", ""), mb.get("internal", "")))
    lane_results["D6"] = (True, _blob(
        *(d.get("meaning", "") for d in (d6_6, d6_8) if d),
        *(d.get("tone", "") for d in (d6_6, d6_8) if d),
    ))
    lane_results["D1"] = (True, _blob(baseline, " ".join(afflicted)))
    lane_results["Timing"] = (True, _blob(*(p.get("note", "") for p in active + upcoming)))
    lane_results["Yogini"] = (True, _blob(*yogini))

    def _d27_hit(kws: list[str], tid: str) -> tuple[bool, str]:
        for z in zones[:3]:
            blob = _blob(z.get("zone", ""), " ".join(z.get("reasons", [])))
            if tid == "chronic_hidden" and z.get("severity") == "high":
                return True, f"{z.get('zone')} (Saturn+Rahu flag)"
            if _kw(blob, kws):
                return True, z.get("zone", "")
        return False, ""

    def _d3_hit(key: str, kws: list[str]) -> tuple[bool, str]:
        loc = loc6 if key == "D3_6" else loc8
        if not loc:
            return False, ""
        blob = _blob(loc.get("body_external", ""), loc.get("body_internal", ""), loc.get("d1", ""))
        hit = _kw(blob, kws) or (key == "D3_6" and "head" in blob)
        return hit, loc.get("body_external", "")

    def _nak_hit(key: str, kws: list[str]) -> tuple[bool, str]:
        n = moon_nak if key == "Moon nak" else lagna_nak
        if not n:
            return False, ""
        return _kw(n.get("tendency", ""), kws), n.get("nakshatra", "")

    def _moon_sign_hit(kws: list[str]) -> tuple[bool, str]:
        if not moon_sign:
            return False, ""
        mb = sign_body.get(moon_sign, {})
        blob = _blob(mb.get("external", ""), mb.get("internal", ""))
        if moon_sign == "Virgo" and _kw("bowel gut digest abdom navel", " ".join(kws)):
            return True, "Virgo digestion zone"
        return _kw(blob, kws), moon_sign

    def _d6_hit(kws: list[str], tid: str) -> tuple[bool, str]:
        hit = False
        for d in (d6_6, d6_8):
            if not d:
                continue
            if _kw(_blob(d.get("meaning", ""), d.get("tone", "")), kws):
                hit = True
            if tid == "chronic_hidden" and d.get("tone") == "chronic":
                hit = True
        return hit, "D6 lords"

    def _d1_hit(kws: list[str], tid: str) -> tuple[bool, str]:
        hit = _kw(baseline, kws)
        if tid == "chronic_hidden":
            hit = hit or "8th lord" in baseline or "opposite Raja Yoga" in baseline
            hit = hit or any(p in afflicted for p in ("Jupiter", "Saturn"))
        if tid == "urinary_reproductive":
            hit = hit or "8th lord" in baseline
        return hit, "D1 pillars"

    def _timing_hit(kws: list[str], tid: str) -> tuple[bool, str]:
        periods = list(active) + list(upcoming)
        vim = pc.get("vimshottari", {})
        cur_ad = next(
            (a for a in vim.get("current_md_antardashas", []) if a.get("status") == "current"),
            None,
        )
        if cur_ad and not any(p.get("lord") == cur_ad.get("ad_lord") for p in periods):
            from goel_disease_analysis import _fmt_range

            periods.insert(0, {
                "lord": cur_ad.get("ad_lord", ""),
                "range": _fmt_range(cur_ad.get("start", ""), cur_ad.get("end", "")),
                "note": f"Current {cur_ad.get('ad_lord', '')} antardasha.",
            })
        for p in periods:
            lord, note = p.get("lord", ""), p.get("note", "")
            if tid == "chronic_hidden" and lord in ("Jupiter", "Saturn"):
                return True, f"{lord} {p.get('range', '')}"
            if tid == "face_eyes_oral" and lord in ("Mars", "Saturn", "Rahu"):
                return True, f"{lord} {p.get('range', '')}"
            if tid == "bowel_gut" and lord in ("Ketu", "Moon", "Mercury"):
                return True, f"{lord} {p.get('range', '')}"
            if _kw(note, kws):
                return True, f"{lord} {p.get('range', '')}"
        return False, ""

    def _yogini_hit(kws: list[str], tid: str) -> tuple[bool, str]:
        if tid == "chronic_hidden" and any("Ulka" in y for y in yogini):
            return True, "Ulka Yogini"
        if tid == "face_eyes_oral" and any(_kw(y, ["teeth", "ear", "eye", "face"]) for y in yogini):
            return True, "Ulka (teeth/ears)"
        return any(_kw(y, kws) for y in yogini), "Yogini"

    evaluators = {
        "D27": lambda tid, kws: _d27_hit(kws, tid),
        "D3_6": lambda tid, kws: _d3_hit("D3_6", kws),
        "D3_8": lambda tid, kws: _d3_hit("D3_8", kws),
        "Moon nak": lambda tid, kws: _nak_hit("Moon nak", kws),
        "Lagna nak": lambda tid, kws: _nak_hit("Lagna nak", kws),
        "Moon sign": lambda tid, kws: _moon_sign_hit(kws),
        "D6": lambda tid, kws: _d6_hit(kws, tid),
        "D1": lambda tid, kws: _d1_hit(kws, tid),
        "Timing": lambda tid, kws: _timing_hit(kws, tid),
        "Yogini": lambda tid, kws: _yogini_hit(kws, tid),
    }

    scored: list[dict] = []
    for tid, spec in THEMES.items():
        kws = spec["keywords"]
        core = spec["core_lanes"]
        hits: list[str] = []
        for lane in core:
            ev = evaluators.get(lane)
            if not ev:
                continue
            ok, detail = ev(tid, kws)
            if ok:
                hits.append(f"{lane}" + (f": {detail}" if detail else ""))

        total = len(core)
        pct = round(100 * len(hits) / total) if total else 0
        if pct < CONFLUENCE_MIN:
            continue

        watch = [
            h.split(": ", 1)[-1]
            for h in hits
            if h.startswith("Timing:") or (tid == "face_eyes_oral" and h.startswith("Yogini:"))
        ]
        if not watch:
            for p in active[:1]:
                watch = [f"{p['lord']} {p.get('range', '')}"]
                break

        scored.append({
            "theme_id": tid,
            "title": spec["title"],
            "match_pct": pct,
            "prediction": spec["prediction"],
            "preventive": spec["prevent"],
            "watch": [w.split(": ", 1)[-1] if ": " in w else w for w in watch][:2],
            "lanes_hit": hits,
            "lanes_total": total,
        })

    scored.sort(key=lambda x: (-x["match_pct"], x["title"]))
    snapshot = _build_snapshot(analysis, scored, active, upcoming)
    return {"min_pct": CONFLUENCE_MIN, "predictions": scored[:4], "snapshot": snapshot}


def _build_snapshot(analysis, scored, active, upcoming) -> dict[str, str]:
    base = []
    for line in analysis.get("constitutional_baseline", [])[:2]:
        base.append(line.split(" - ")[0].strip())
    constitution = ". ".join(base) + "." if base else "Mixed D1 health signature."

    now = f"Active: {active[0]['lord']} ({active[0].get('range', '')})." if active else ""
    nxt = f"Next: {upcoming[0]['lord']} ({upcoming[0].get('range', '')})." if upcoming else ""
    focus = ", ".join(p["title"] for p in scored[:3]) or "None at 70%+ agreement."

    return {"constitution": constitution, "active_window": now, "next_window": nxt, "focus": focus}
