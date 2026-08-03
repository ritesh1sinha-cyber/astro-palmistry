#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Birth time rectification via dated life events + Vimshottari/varga scoring (PyJHora)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from astro_precompute import (
    SIGN_LORDS,
    VIMSH_LORDS,
    build_antardashas,
    house_from_lagna,
    house_sign,
    precompute_from_chart,
)
from natal_from_pyjhora import BirthInput, compute_chart_btr

# Manley / rules5 event -> house / karaka / varga mapping
EVENT_SPECS: dict[str, dict[str, Any]] = {
    "first_job": {
        "label": "First job",
        "houses": [10, 6],
        "karakas": ["Sun", "Mercury", "Jupiter", "Saturn"],
        "varga": "D10",
        "bhavat": 11,
    },
    "higher_education": {
        "label": "Higher education",
        "houses": [9, 4, 5],
        "karakas": ["Jupiter", "Mercury"],
        "varga": "D24",
        "bhavat": None,
    },
    "foreign_travel": {
        "label": "Foreign travel / major move",
        "houses": [12, 9, 3],
        "karakas": ["Rahu", "Moon", "Saturn"],
        "varga": "D4",
        "bhavat": None,
    },
    "marriage": {
        "label": "Marriage",
        "houses": [7, 2],
        "karakas": ["Venus", "Jupiter"],
        "varga": "D9",
        "bhavat": 9,
    },
    "child": {
        "label": "First child",
        "houses": [5, 9],
        "secondary_houses": [4],  # home/family theme (lower weight)
        "karakas": ["Jupiter", "Venus"],
        "varga": "D7",
        "bhavat": None,
    },
}

DEFAULT_WINDOW_MIN = 90
DEFAULT_STEP_MIN = 1
FINE_WINDOW_SEC = 240
FINE_STEP_SEC = 30
AUTO_APPLY_MARGIN = 8.0
MIN_EVENTS_FOR_AUTO = 3

# Manley Precision Sandwich - approximate minutes per varga lagna (rules5 ss6-7).
# Minutes per varga-lagna ≈ 120 / divisional-factor (30° of D1 ≈ 120 min).
# D81/D108/D144 are ultra-fine micro-charts used only as the final tie-break.
VARGA_FUNNEL_WINDOWS: dict[str, float] = {
    "D1": 120,
    "D4": 30,
    "D7": 17,
    "D9": 13,
    "D10": 12,
    "D24": 5,
    "D60": 2,
    "D81": 1.5,
    "D108": 1.1,
    "D144": 0.83,
}

# Ultra-fine rectification charts (sub-2-minute lagna). Only scored at the
# 30-second fine-scan stage, never during the coarse 1-minute scan.
ULTRA_FINE_VARGAS = ("D81", "D108", "D144")

# Optional custom event categories (for bachelors, property, illness, etc.)
CUSTOM_CATEGORY_SPECS: dict[str, dict[str, Any]] = {
    "career": {
        "label": "Career milestone",
        "houses": [10, 6, 11],
        "karakas": ["Sun", "Mercury", "Jupiter", "Saturn"],
        "varga": "D10",
        "bhavat": 11,
    },
    "education": {
        "label": "Education",
        "houses": [9, 4, 5],
        "karakas": ["Jupiter", "Mercury"],
        "varga": "D24",
        "bhavat": None,
    },
    "travel": {
        "label": "Travel / relocation",
        "houses": [12, 9, 3, 4],
        "karakas": ["Rahu", "Moon", "Saturn"],
        "varga": "D4",
        "bhavat": None,
    },
    "marriage": {
        "label": "Marriage / partnership",
        "houses": [7, 2],
        "karakas": ["Venus", "Jupiter"],
        "varga": "D9",
        "bhavat": 9,
    },
    "child": {
        "label": "Childbirth",
        "houses": [5, 9],
        "secondary_houses": [4],
        "karakas": ["Jupiter", "Venus"],
        "varga": "D7",
        "bhavat": None,
    },
    "property": {
        "label": "Property / home",
        "houses": [4, 11],
        "karakas": ["Mars", "Saturn", "Venus", "Moon"],
        "varga": "D4",
        "bhavat": None,
    },
    "business": {
        "label": "Business start",
        "houses": [7, 10, 11],
        "karakas": ["Mercury", "Jupiter", "Venus"],
        "varga": "D10",
        "bhavat": None,
    },
    "promotion": {
        "label": "Promotion / recognition",
        "houses": [10, 11],
        "karakas": ["Sun", "Jupiter"],
        "varga": "D10",
        "bhavat": 11,
    },
    "illness": {
        "label": "Major illness / surgery",
        "houses": [6, 8],
        "karakas": ["Saturn", "Mars", "Sun"],
        "varga": "D60",
        "bhavat": None,
    },
    "death": {
        "label": "Death in family",
        "houses": [8, 12, 2],
        "karakas": ["Saturn", "Mars"],
        "varga": "D60",
        "bhavat": None,
    },
    "legal": {
        "label": "Legal / court matter",
        "houses": [6, 7, 9],
        "karakas": ["Saturn", "Mars", "Mercury"],
        "varga": "D9",
        "bhavat": None,
    },
    "award": {
        "label": "Award / honour",
        "houses": [10, 11, 9],
        "karakas": ["Sun", "Jupiter"],
        "varga": "D10",
        "bhavat": 11,
    },
    "recovery": {
        "label": "Recovery from illness",
        "houses": [5, 11, 1],
        "secondary_houses": [6],
        "karakas": ["Jupiter", "Sun", "Moon"],
        "varga": "D9",
        "bhavat": None,
    },
    "wealth": {
        "label": "Business / wealth rise",
        "houses": [2, 11, 10],
        "karakas": ["Jupiter", "Venus", "Mercury"],
        "varga": "D2",
        "bhavat": 11,
    },
    "status_uplift": {
        "label": "Social status upliftment",
        "houses": [10, 11, 9],
        "karakas": ["Sun", "Jupiter", "Mercury"],
        "varga": "D10",
        "bhavat": 11,
    },
    "separation": {
        "label": "Separation / divorce",
        "houses": [7, 8, 12],
        "karakas": ["Saturn", "Mars", "Venus"],
        "varga": "D9",
        "bhavat": None,
    },
    "sibling": {
        "label": "Sibling milestone",
        "houses": [3, 11],
        "karakas": ["Mars", "Mercury"],
        "varga": "D4",
        "bhavat": None,
    },
    "other": {
        "label": "Life event",
        "houses": [1, 10],
        "karakas": ["Sun", "Moon", "Saturn"],
        "varga": "D60",
        "bhavat": None,
    },
}

RULES_COVERAGE: dict[str, Any] = {
    "book": "rules5.md / Manley Precision Sandwich",
    "six_factors": [
        "relevant bhava (D1)",
        "bhava lord",
        "karaka",
        "varga lagna",
        "D1 bhava lord in varga",
        "bhavat bhavam",
        "D60 minute-level cross-check",
    ],
    "precision_sandwich_vargas": ["D1", "D4", "D7", "D9", "D10", "D24", "D60"],
    "ultra_fine_tiebreak_vargas": list(ULTRA_FINE_VARGAS),
    "ultra_fine_note": (
        "D81/D108/D144 change lagna within ~1 minute; scored only at the 30-sec "
        "fine-scan stage as a final tie-break inside the D60 (~2 min) slot."
    ),
    "funnel_windows_min": VARGA_FUNNEL_WINDOWS,
    "vimshottari": "Mahadasha + Antardasha (MD/AD must fit before finer levels)",
    "fine_levels_345": (
        "Pratyantara/Sukshma/Prana (345 tie-break) not auto-scored - "
        "book p.82: use only when MD+AD already fit adjacent candidates"
    ),
    "de_emphasized": ["nakshatra primary", "transits primary", "character traits", "Chandra lagna decider"],
    "scan_phases": [
        f"coarse +/-{DEFAULT_WINDOW_MIN} min @ {DEFAULT_STEP_MIN} min",
        f"fine +/-{FINE_WINDOW_SEC // 60} min @ {FINE_STEP_SEC} sec when shift likely",
    ],
}


@dataclass
class BtrEvent:
    kind: str
    when: date
    label: str = ""
    spec: dict[str, Any] | None = None


@dataclass
class BtrCandidate:
    time_hms: str
    offset_min: int
    total_score: float
    event_scores: dict[str, dict[str, Any]] = field(default_factory=dict)
    lagna_sign: str = ""
    lagna_degree: float = 0.0


def parse_event_date(raw: str) -> date | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    m = re.match(r"^(\d{4})-(\d{1,2})(?:-(\d{1,2}))?$", raw)
    if not m:
        return None
    y, mo = int(m.group(1)), int(m.group(2))
    d = int(m.group(3)) if m.group(3) else 15
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def event_spec(ev: BtrEvent) -> dict[str, Any]:
    if ev.spec:
        return ev.spec
    return EVENT_SPECS[ev.kind]


def _infer_category(label: str) -> str:
    low = label.lower()
    keys = (
        ("marriage", ("marry", "wedding", "spouse", "engagement")),
        ("child", ("child", "birth", "baby", "son", "daughter")),
        ("education", ("degree", "college", "university", "graduat", "education", "exam")),
        ("travel", ("abroad", "foreign", "relocat", "move", "immigr", "travel")),
        ("career", ("job", "employ", "career", "work", "hired")),
        ("promotion", ("promot", "raise", "recognition")),
        ("property", ("house", "property", "flat", "land", "home purchase")),
        ("business", ("business", "startup", "company")),
        ("illness", ("surgery", "hospital", "illness", "disease", "accident")),
        ("death", ("death", "died", "funeral", "passed")),
        ("legal", ("court", "legal", "lawsuit", "divorce filing")),
        ("separation", ("separat", "divorce", "breakup")),
        ("sibling", ("sibling", "brother", "sister")),
        ("award", ("award", "honour", "honor", "prize")),
    )
    for cat, words in keys:
        if any(w in low for w in words):
            return cat
    return "other"


def parse_custom_events(raw: str) -> list[BtrEvent]:
    """Parse optional free-form events: 'Label: YYYY-MM-DD' or 'Label | date | category'."""
    out: list[BtrEvent] = []
    for idx, line in enumerate((raw or "").splitlines()):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        label, date_s, category = "", "", ""
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 2 and parse_event_date(parts[1]):
                label, date_s = parts[0], parts[1]
                category = parts[2].lower() if len(parts) > 2 else _infer_category(label)
            elif len(parts) >= 2 and ":" in parts[0]:
                # "Label: YYYY-MM-DD | category"
                label, date_s = [p.strip() for p in parts[0].split(":", 1)]
                category = parts[1].lower() if parts[1] else _infer_category(label)
            else:
                continue
        elif ":" in line:
            label, date_s = [p.strip() for p in line.split(":", 1)]
            category = _infer_category(label)
        else:
            continue
        when = parse_event_date(date_s)
        if not when:
            continue
        cat = category if category in CUSTOM_CATEGORY_SPECS else _infer_category(label)
        base = dict(CUSTOM_CATEGORY_SPECS[cat])
        base["label"] = label or base["label"]
        out.append(BtrEvent(kind=f"custom_{idx}", when=when, label=base["label"], spec=base))
    return out


def parse_events_from_form(fields: dict[str, str], custom_events: str = "") -> list[BtrEvent]:
    out: list[BtrEvent] = []
    for kind in EVENT_SPECS:
        when = parse_event_date(fields.get(kind, ""))
        if when:
            out.append(BtrEvent(kind=kind, when=when, label=EVENT_SPECS[kind]["label"]))
    out.extend(parse_custom_events(custom_events))
    return out


def _parse_hms(time_str: str) -> tuple[int, int, int]:
    parts = [int(x) for x in time_str.strip().replace(".", ":").split(":")]
    while len(parts) < 3:
        parts.append(0)
    return parts[0], parts[1], parts[2]


def _format_hms(h: int, m: int, s: int) -> str:
    return f"{h:02d}:{m:02d}:{s:02d}"


def _offset_time(base: str, delta_min: int) -> str:
    h, m, s = _parse_hms(base)
    dt = datetime(2000, 1, 1, h, m, s) + timedelta(minutes=delta_min)
    return _format_hms(dt.hour, dt.minute, dt.second)


def _offset_time_sec(base: str, delta_sec: int) -> str:
    h, m, s = _parse_hms(base)
    dt = datetime(2000, 1, 1, h, m, s) + timedelta(seconds=delta_sec)
    return _format_hms(dt.hour, dt.minute, dt.second)


def _house_lords(lagna_sign: str, planets: dict) -> dict[int, dict]:
    hl: dict[int, dict] = {}
    for h in range(1, 13):
        hs = house_sign(h, lagna_sign)
        lord = SIGN_LORDS[hs]
        ld = planets.get(lord, {})
        hl[h] = {
            "sign": hs,
            "lord": lord,
            "lord_sign": ld.get("sign", "?"),
            "lord_house": ld.get("house"),
        }
    return hl


def dasha_at_date(vimsh: dict, when: date) -> dict[str, str]:
    """MD + AD lords active on event date."""
    sequence = vimsh.get("sequence") or []
    md_row = None
    for row in sequence:
        start = date.fromisoformat(row["start"])
        end = date.fromisoformat(row["end"])
        if start <= when < end:
            md_row = row
            break
    if not md_row:
        return {}
    md_lord = md_row["md_lord"]
    md_idx = VIMSH_LORDS.index(md_lord)
    ads = build_antardashas(md_row, md_idx)
    ad_row = next(
        (a for a in ads if date.fromisoformat(a["start"]) <= when < date.fromisoformat(a["end"])),
        {},
    )
    return {"md_lord": md_lord, "ad_lord": ad_row.get("ad_lord", "")}


def _shares_house(p1: str, p2: str, planets: dict) -> bool:
    h1 = planets.get(p1, {}).get("house")
    h2 = planets.get(p2, {}).get("house")
    return bool(h1 and h2 and h1 == h2)


def _varga_house_of(planet: str, divisional: dict, varga_key: str) -> int | None:
    v = divisional.get(varga_key) or {}
    lagna_v = v.get("Lagna")
    psign = v.get(planet)
    if not lagna_v or not psign:
        return None
    return house_from_lagna(psign, lagna_v)


def _score_lord_for_event(
    lord: str,
    spec: dict,
    planets: dict,
    house_lords: dict[int, dict],
    divisional: dict,
    clues: list[str],
    *,
    ultra_fine: bool = False,
) -> float:
    """Manley six-factor clues for one dasha lord (rules5.md section 8)."""
    score = 0.0
    pdata = planets.get(lord, {})
    phouse = pdata.get("house")
    houses = list(spec["houses"])
    sec = spec.get("secondary_houses") or []
    karakas = spec["karakas"]
    varga = spec.get("varga")
    bhavat = spec.get("bhavat")

    for h in houses:
        if phouse == h:
            score += 3.0
            clues.append(f"{lord} in {h}th (D1)")
        hl = house_lords.get(h, {})
        if hl.get("lord") == lord:
            score += 2.0
            clues.append(f"{lord} rules {h}th")
    for h in sec:
        if phouse == h:
            score += 1.5
            clues.append(f"{lord} in {h}th secondary (D1)")

    if lord in karakas:
        score += 2.0
        clues.append(f"{lord} is karaka")

    for k in karakas:
        if k != lord and _shares_house(lord, k, planets):
            score += 2.5
            clues.append(f"{lord} with karaka {k} (D1)")

    for h in houses:
        hl = house_lords.get(h, {}).get("lord")
        if hl and hl != lord and _shares_house(lord, hl, planets):
            score += 2.5
            clues.append(f"{lord} with {h}th lord {hl} (D1)")

    if bhavat and phouse == bhavat:
        score += 1.5
        clues.append(f"{lord} in bhavat-bhavam {bhavat}")

    if varga:
        vh = _varga_house_of(lord, divisional, varga)
        if vh == 1:
            score += 3.5
            clues.append(f"{lord} in {varga} lagna")
        elif vh in houses:
            score += 2.0
            clues.append(f"{lord} in {vh}th ({varga})")
        elif vh in sec:
            score += 1.0
            clues.append(f"{lord} in {vh}th ({varga}, secondary)")

        for h in houses:
            hl = house_lords.get(h, {}).get("lord")
            if not hl:
                continue
            hl_vh = _varga_house_of(hl, divisional, varga)
            if hl_vh in (1, h) and (lord == hl or _shares_house(lord, hl, planets)):
                score += 2.0
                clues.append(f"D1 {h}th lord {hl} in {varga} h{hl_vh}")

    # D60 minute-level cross-check (Precision Sandwich outer slice - rules5 ss6-7)
    if divisional.get("D60"):
        vh60 = _varga_house_of(lord, divisional, "D60")
        if vh60 == 1:
            score += 2.0
            clues.append(f"{lord} in D60 lagna (~2 min window)")
        elif vh60 in houses:
            score += 1.5
            clues.append(f"{lord} in {vh60}th (D60)")
        elif vh60 in sec:
            score += 1.0
            clues.append(f"{lord} in {vh60}th (D60, secondary)")

    # Ultra-fine tie-break (D81/D108/D144) — only at the 30-sec fine-scan stage,
    # so the sub-minute lagna noise never pollutes the coarse 1-min scan. Small
    # weights: these only discriminate between candidates already tied on D60.
    if ultra_fine:
        for vkey, w_lagna, w_house in (("D108", 1.0, 0.6), ("D144", 0.8, 0.4), ("D81", 0.6, 0.3)):
            if not divisional.get(vkey):
                continue
            vhu = _varga_house_of(lord, divisional, vkey)
            if vhu == 1:
                score += w_lagna
                clues.append(f"{lord} in {vkey} lagna (ultra-fine tie-break)")
            elif vhu in houses:
                score += w_house
                clues.append(f"{lord} in {vhu}th ({vkey}, ultra-fine)")

    return score


def _strength_label(score: float) -> str:
    """Spectrum of certainty (rules5): one clue (~2+) = plausible."""
    if score >= 7:
        return "strong"
    if score >= 4:
        return "medium"
    if score >= 2:
        return "plausible"
    return "fail"


def score_event(
    event: BtrEvent,
    parsed_chart: dict,
    pc: dict,
    *,
    ultra_fine: bool = False,
) -> dict[str, Any]:
    """Six-factor style score for one event at one trial time."""
    spec = event_spec(event)
    lagna_sign = parsed_chart["lagna"]["sign"]
    planets = parsed_chart["planets"]
    divisional = parsed_chart.get("divisional") or {}
    house_lords = _house_lords(lagna_sign, planets)
    dasha = dasha_at_date(pc.get("vimshottari", {}), event.when)
    md, ad = dasha.get("md_lord", ""), dasha.get("ad_lord", "")
    lords = [x for x in [md, ad] if x]

    clues: list[str] = []
    score = 0.0
    for lord in lords:
        score += _score_lord_for_event(
            lord, spec, planets, house_lords, divisional, clues, ultra_fine=ultra_fine
        )

    if event.kind == "child" and ad == "Moon" and planets.get("Moon", {}).get("house") == 4:
        score += 2.0
        clues.append("Moon AD with Moon in 4th (family expansion)")

    strength = _strength_label(score)
    return {
        "event": event.kind,
        "label": event.label or spec.get("label", event.kind),
        "date": str(event.when),
        "md_lord": md,
        "ad_lord": ad,
        "score": round(score, 1),
        "strength": strength,
        "varga": spec.get("varga", "D1"),
        "clues": clues[:10],
    }


def _lagna_funnel(parsed: dict) -> list[dict[str, Any]]:
    div = parsed.get("divisional") or {}
    order = ("D4", "D7", "D9", "D10", "D24", "D60", *ULTRA_FINE_VARGAS)
    rows = [{"varga": "D1", "lagna": parsed.get("lagna", {}).get("sign"), "window_min": VARGA_FUNNEL_WINDOWS["D1"]}]
    for key in order:
        if key in div:
            rows.append({
                "varga": key,
                "lagna": div[key].get("Lagna"),
                "window_min": VARGA_FUNNEL_WINDOWS.get(key),
                "ultra_fine": key in ULTRA_FINE_VARGAS,
            })
    return rows


def _chart_for_time(
    inp: BirthInput,
    time_hms: str,
) -> tuple[dict, dict]:
    trial = BirthInput(
        client_name=inp.client_name,
        dob=inp.dob,
        birth_time=time_hms,
        latitude=inp.latitude,
        longitude=inp.longitude,
        timezone=inp.timezone,
        place_name=inp.place_name,
        ayanamsa=inp.ayanamsa,
        gender=inp.gender,
    )
    parsed = compute_chart_btr(trial)
    pc = precompute_from_chart(parsed, inp.client_name, inp.dob, source="pyjhora_btr")
    return parsed, pc


def score_candidate(
    inp: BirthInput,
    time_hms: str,
    offset_min: int,
    events: list[BtrEvent],
    *,
    offset_sec: int = 0,
    ultra_fine: bool = False,
) -> BtrCandidate:
    parsed, pc = _chart_for_time(inp, time_hms)
    event_scores = {
        ev.kind: score_event(ev, parsed, pc, ultra_fine=ultra_fine)
        for ev in events
    }
    total = sum(v["score"] for v in event_scores.values())
    lagna = parsed.get("lagna", {})
    return BtrCandidate(
        time_hms=time_hms,
        offset_min=offset_min if offset_sec == 0 else offset_min,
        total_score=round(total, 1),
        event_scores=event_scores,
        lagna_sign=lagna.get("sign", ""),
        lagna_degree=float(lagna.get("degree_in_sign", 0)),
    )


def _scan_candidates(
    inp: BirthInput,
    base_time: str,
    events: list[BtrEvent],
    *,
    window_min: int,
    step_min: int,
) -> list[BtrCandidate]:
    out: list[BtrCandidate] = []
    for off in range(-window_min, window_min + 1, step_min):
        t = _offset_time(base_time, off)
        out.append(score_candidate(inp, t, off, events))
    return out


def _fine_scan_around(
    inp: BirthInput,
    center_time: str,
    events: list[BtrEvent],
    trial_offset_min: int,
) -> list[BtrCandidate]:
    """D60-grade refinement: +/-4 min at 30 sec steps (rules5 ~2 min/lagna)."""
    out: list[BtrCandidate] = []
    for off_sec in range(-FINE_WINDOW_SEC, FINE_WINDOW_SEC + 1, FINE_STEP_SEC):
        t = _offset_time_sec(center_time, off_sec)
        off_min = trial_offset_min + int(round(off_sec / 60))
        out.append(score_candidate(inp, t, off_min, events, offset_sec=off_sec, ultra_fine=True))
    return out


def rectify_birth_time(
    *,
    client_name: str,
    dob: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    timezone: float,
    place_name: str = "",
    gender: int = 0,
    events: list[BtrEvent] | None = None,
    event_fields: dict[str, str] | None = None,
    custom_events: str = "",
    window_min: int = DEFAULT_WINDOW_MIN,
    step_min: int = DEFAULT_STEP_MIN,
    auto_apply: bool = True,
) -> dict[str, Any]:
    """
    Precision Sandwich scan: coarse +/-window_min, then D60-grade fine scan when needed.
    Scores life events via Manley six-factor + varga funnel (D4/D7/D9/D10/D24/D60).
    """
    if events is None:
        events = parse_events_from_form(event_fields or {}, custom_events)

    base_time = birth_time if len(birth_time.split(":")) >= 3 else birth_time + ":00"
    inp = BirthInput(
        client_name=client_name,
        dob=dob,
        birth_time=base_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        place_name=place_name,
        gender=gender,
    )

    if not events:
        return {
            "skipped": True,
            "reason": "No BTR event dates provided.",
            "trial_time": base_time,
            "corrected_time": base_time,
            "apply": False,
        }

    candidates = _scan_candidates(inp, base_time, events, window_min=window_min, step_min=step_min)
    trial_coarse = next((c for c in candidates if c.offset_min == 0), candidates[len(candidates) // 2])
    best_coarse = max(candidates, key=lambda c: (c.total_score, -abs(c.offset_min)))

    # ── Equal-footing refinement ──────────────────────────────────────────
    # The coarse scan finds the strongest region; we then ALWAYS refine to the
    # second around it (and around the trial when they differ). Every refined
    # candidate AND the exact trial time are scored with the same ultra-fine
    # (D81/D108/D144) terms, so trial vs best is judged fairly and BTR narrows
    # the time on its own.
    run_fine = True
    trial = score_candidate(inp, trial_coarse.time_hms, 0, events, ultra_fine=True)
    fine_pool: list[BtrCandidate] = [trial]
    fine_pool.extend(_fine_scan_around(inp, best_coarse.time_hms, events, best_coarse.offset_min))
    if best_coarse.time_hms != trial_coarse.time_hms:
        fine_pool.extend(_fine_scan_around(inp, trial_coarse.time_hms, events, 0))
    candidates.extend(c for c in fine_pool if c is not trial)
    best = max(fine_pool, key=lambda c: (c.total_score, -abs(c.offset_min)))

    trial_parsed, _ = _chart_for_time(inp, trial.time_hms)
    best_parsed, _ = _chart_for_time(inp, best.time_hms)

    trial_n_strong = sum(
        1 for ev in events
        if trial.event_scores[ev.kind]["strength"] in ("strong", "medium", "plausible")
    )
    trial_n_medium_plus = sum(
        1 for ev in events
        if trial.event_scores[ev.kind]["strength"] in ("strong", "medium")
    )
    n_strong = sum(
        1 for ev in events
        if best.event_scores[ev.kind]["strength"] in ("strong", "medium", "plausible")
    )
    avg = best.total_score / max(len(events), 1)
    trial_avg = trial.total_score / max(len(events), 1)
    if trial_n_medium_plus >= 4 and trial_avg >= 6:
        confidence = "high"
    elif trial_n_medium_plus >= 3 and trial_avg >= 4:
        confidence = "medium"
    elif n_strong >= 4 and avg >= 6:
        confidence = "high"
    elif n_strong >= 3 and avg >= 4:
        confidence = "medium"
    else:
        confidence = "low"

    per_event_wins = sum(
        1 for ev in events
        if best.event_scores[ev.kind]["score"] >= trial.event_scores[ev.kind]["score"] + 2
    )
    improved = best.total_score >= trial.total_score + AUTO_APPLY_MARGIN
    # A decisive, multi-event improvement (now measured on equal footing) lets
    # BTR override the "trust the entered clock" guards and auto-narrow the time.
    decisive = (
        improved
        and per_event_wins >= max(2, len(events) - 1)
        and n_strong >= trial_n_strong
        and best.time_hms != trial.time_hms
    )
    trial_solid = trial_n_medium_plus >= 3 and trial_avg >= 5
    if trial_solid and not decisive:
        apply = False
    elif abs(best.offset_min) > 30 and trial_avg >= 4 and not decisive:
        apply = False
    else:
        apply = (
            auto_apply
            and improved
            and len(events) >= MIN_EVENTS_FOR_AUTO
            and confidence in ("high", "medium")
            and best.time_hms != trial.time_hms
            and per_event_wins >= max(3, len(events) - 1)
            and n_strong >= trial_n_strong
        )

    trial_verdict = "approve_trial" if (
        not apply
        and trial_n_strong >= max(3, len(events) - 1)
        and trial_n_medium_plus >= 2
    ) else ("shift_suggested" if not apply and improved else ("applied" if apply else "inconclusive"))

    display_events = (
        list(best.event_scores.values()) if apply else list(trial.event_scores.values())
    )

    suggested_offset = best.offset_min
    suggested_offset_sec = 0
    if best.time_hms != trial.time_hms:
        th, tm, ts = _parse_hms(trial.time_hms)
        bh, bm, bs = _parse_hms(best.time_hms)
        t0 = th * 3600 + tm * 60 + ts
        t1 = bh * 3600 + bm * 60 + bs
        diff = t1 - t0
        if diff > 12 * 3600:
            diff -= 24 * 3600
        elif diff < -12 * 3600:
            diff += 24 * 3600
        suggested_offset = int(round(diff / 60))
        suggested_offset_sec = diff

    return {
        "skipped": False,
        "trial_time": trial.time_hms,
        "corrected_time": best.time_hms if apply else trial.time_hms,
        "suggested_time": best.time_hms,
        "suggested_score": best.total_score,
        "trial_score": trial.total_score,
        "best_score": best.total_score,
        "offset_minutes": suggested_offset,
        "offset_seconds": suggested_offset_sec,
        "fine_scan_used": run_fine,
        "confidence": confidence,
        "apply": apply,
        "trial_verdict": trial_verdict,
        "lagna_trial": f"{trial.lagna_sign} {trial.lagna_degree:.2f} deg",
        "lagna_best": f"{best.lagna_sign} {best.lagna_degree:.2f} deg",
        "funnel_trial": _lagna_funnel(trial_parsed),
        "funnel_best": _lagna_funnel(best_parsed),
        "rules_coverage": RULES_COVERAGE,
        "events_used": len(events),
        "events_strong_medium": n_strong,
        "trial_events_strong_medium": trial_n_strong,
        "trial_events_medium_plus": trial_n_medium_plus,
        "per_event_wins": per_event_wins,
        "event_results": display_events,
        "trial_event_results": list(trial.event_scores.values()),
        "best_event_results": list(best.event_scores.values()),
        "message": _result_message(trial, best, apply, confidence, len(events), trial_verdict, suggested_offset),
    }


def _result_message(
    trial: BtrCandidate,
    best: BtrCandidate,
    apply: bool,
    confidence: str,
    n_events: int,
    trial_verdict: str = "inconclusive",
    suggested_offset: int = 0,
) -> str:
    if apply:
        sign = "-" if suggested_offset < 0 else "+"
        return (
            f"BTR adjusted birth time {trial.time_hms} -> {best.time_hms} "
            f"({sign}{abs(suggested_offset)} min). Score {trial.total_score} -> {best.total_score}. "
            f"Confidence: {confidence}."
        )
    if trial_verdict == "approve_trial":
        return (
            f"Trial time {trial.time_hms} verified - {n_events} events checked "
            f"(score {trial.total_score}, {confidence}). "
            f"Precision Sandwich: D7/D9 narrow ~17/13 min bands; D60 ~2 min. "
            f"Weak marriage/child alone do not overturn a confirmed clock when other events fit."
        )
    if trial_verdict == "shift_suggested":
        sign = "-" if suggested_offset < 0 else "+"
        return (
            f"Trial time may be off. Nearby best match: {best.time_hms} "
            f"({sign}{abs(suggested_offset)} min from trial, score {best.total_score} vs {trial.total_score}). "
            f"Review event table and funnel lagnas; apply manually if convinced ({confidence})."
        )
    if best.offset_min == 0 or abs(best.total_score - trial.total_score) < 1:
        return (
            f"Trial time {trial.time_hms} confirmed by {n_events} event(s) "
            f"(score {trial.total_score}, {confidence})."
        )
    return (
        f"Trial time kept ({trial.time_hms}). Best candidate {best.time_hms} "
        f"score {best.total_score} vs trial {trial.total_score} - insufficient margin "
        f"for auto-apply ({confidence})."
    )
