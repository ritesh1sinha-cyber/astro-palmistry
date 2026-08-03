#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Muhurat checker: score a date for one event + suggest next good dates (rules37)."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from astro_precompute import compute_cara_karakas, precompute_from_chart
from muhurat_daily import _day_windows
from muhurat_event_rules import (
    CHART_AWARE_EVENTS,
    event_requirements,
    get_event_rule,
    list_event_catalog,
    score_event_muhurat,
)
from muhurat_panchang import fetch_day_panchang
from natal_from_pyjhora import BirthInput, compute_chart_btr


def _build_pc_from_birth(
    *,
    client_name: str,
    client_dob: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    timezone: float,
    place_name: str,
    gender: int = 0,
) -> dict:
    base = birth_time if birth_time.count(":") >= 2 else birth_time + ":00"
    inp = BirthInput(
        client_name=client_name,
        dob=client_dob,
        birth_time=base,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        place_name=place_name,
        gender=gender,
    )
    parsed = compute_chart_btr(inp)
    pc = precompute_from_chart(parsed, client_name, client_dob, source="pyjhora_muhurat")
    pc.setdefault("meta", {})["dob"] = client_dob
    pc["cara_karakas"] = compute_cara_karakas(parsed.get("planets", {}))
    return pc


def _empty_pc(dob: str = "") -> dict:
    pc: dict = {"meta": {}, "planets": {}}
    if dob:
        pc["meta"]["dob"] = dob[:10]
    return pc


def resolve_pc_for_muhurat(
    *,
    session_dir: Path | None,
    event_id: str,
    client_name: str,
    client_dob: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    timezone: float,
    place_name: str,
    gender: int = 0,
    load_pc_for_session=None,
) -> dict:
    """Prefer session precompute; else build chart when required; else panchang-only."""
    rule = get_event_rule(event_id)
    req = event_requirements(rule)

    if session_dir and (session_dir / "session_manifest.json").is_file():
        try:
            if load_pc_for_session:
                pc = load_pc_for_session(session_dir)
                if client_dob:
                    pc.setdefault("meta", {})["dob"] = client_dob[:10]
                return pc
        except FileNotFoundError:
            pass

    if req["panchang_only"]:
        return _empty_pc()

    if req["requires_dob"] and not req["requires_natal_chart"]:
        if not client_dob.strip():
            raise ValueError("Date of birth is required for this event (e.g. mundan odd-year check).")
        return _empty_pc(client_dob)

    if req["requires_natal_chart"]:
        if not client_dob.strip():
            raise ValueError("Date of birth is required for this event (uses your birth star).")
        if not birth_time.strip():
            raise ValueError("Birth time is required for this event (natal chart needed).")
        return _build_pc_from_birth(
            client_name=client_name or "Client",
            client_dob=client_dob.strip()[:10],
            birth_time=birth_time.strip(),
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            place_name=place_name or "BirthPlace",
            gender=gender,
        )

    if client_dob.strip() and birth_time.strip():
        return _build_pc_from_birth(
            client_name=client_name or "Client",
            client_dob=client_dob.strip()[:10],
            birth_time=birth_time.strip(),
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            place_name=place_name or "BirthPlace",
            gender=gender,
        )
    return _empty_pc(client_dob if client_dob.strip() else "")


def _score_one_day(
    rule,
    target: date,
    pc: dict,
    latitude: float,
    longitude: float,
    timezone: float,
    place_name: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    panchang = fetch_day_panchang(
        target,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        place_name=place_name,
    )
    if not panchang.get("available"):
        return {"verdict": "avoid", "summary": panchang.get("error", "Panchang unavailable")}, panchang
    scored = score_event_muhurat(rule, panchang, pc, target)
    return scored, panchang


def find_next_good_dates(
    *,
    event_id: str,
    start_date: date,
    pc: dict,
    latitude: float,
    longitude: float,
    timezone: float,
    place_name: str,
    max_scan_days: int = 120,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    rule = get_event_rule(event_id)
    if not rule:
        return []

    good: list[dict[str, Any]] = []
    mixed: list[dict[str, Any]] = []

    for offset in range(1, max_scan_days + 1):
        d = start_date + timedelta(days=offset)
        scored, panchang = _score_one_day(
            rule, d, pc, latitude, longitude, timezone, place_name,
        )
        if not panchang.get("available"):
            continue
        row = {
            "date": d.isoformat(),
            "weekday": panchang.get("weekday", ""),
            "nakshatra": panchang.get("nakshatra", ""),
            "tithi_day": panchang.get("tithi_day"),
            "paksha": panchang.get("paksha"),
            "verdict": scored.get("verdict", "avoid"),
            "summary": scored.get("summary", ""),
        }
        if scored.get("verdict") == "good":
            good.append(row)
            if len(good) >= max_results:
                break
        elif scored.get("verdict") == "mixed" and len(mixed) < max_results:
            mixed.append(row)

    return good if good else mixed[:max_results]


def check_muhurat(
    *,
    event_id: str,
    target: date,
    pc: dict,
    latitude: float,
    longitude: float,
    timezone: float,
    place_name: str = "BirthPlace",
    suggest_alternatives: bool = True,
) -> dict[str, Any]:
    rule = get_event_rule(event_id)
    if not rule:
        return {"available": False, "error": f"Unknown event type: {event_id}"}

    req = event_requirements(rule)

    scored, panchang = _score_one_day(
        rule, target, pc, latitude, longitude, timezone, place_name,
    )
    if not panchang.get("available"):
        return {"available": False, "error": panchang.get("error", "Panchang failed")}

    windows = _day_windows(panchang)
    best_slot = windows.get("good_choghadiya", [{}])[0] if windows.get("good_choghadiya") else {}

    alternatives: list[dict[str, Any]] = []
    if suggest_alternatives and scored.get("verdict") != "good":
        alternatives = find_next_good_dates(
            event_id=event_id,
            start_date=target,
            pc=pc,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            place_name=place_name,
        )

    verdict = scored.get("verdict", "avoid")
    headline = {
        "good": "This day looks auspicious for this event.",
        "mixed": "This day is workable but not ideal - use a strong hour or pick an alternative below.",
        "avoid": "This day is not recommended - see suggested dates below.",
    }.get(verdict, "")

    if req.get("panchang_only") and not pc.get("planets"):
        chart_notes = list(scored.get("chart_notes", []))
        chart_notes.insert(
            0,
            "General panchang only - no birth chart used. Add DOB and birth time for chart-specific refinements.",
        )
        scored["chart_notes"] = chart_notes

    return {
        "available": True,
        "event_id": event_id,
        "event_label": rule.label,
        "event_plain": rule.plain,
        "target_date": target.isoformat(),
        "verdict": verdict,
        "headline": headline,
        "summary": scored.get("summary", ""),
        "checks": scored.get("checks", []),
        "chart_notes": scored.get("chart_notes", []),
        "needs_partner_chart": scored.get("needs_partner_chart", False),
        "chart_aware": event_id in CHART_AWARE_EVENTS,
        "panchang_only": req.get("panchang_only", False),
        "panchang_location": place_name,
        "panchang": {
            "weekday": panchang.get("weekday"),
            "tithi_day": panchang.get("tithi_day"),
            "paksha": panchang.get("paksha"),
            "nakshatra": panchang.get("nakshatra"),
            "lunar_month": panchang.get("lunar_month"),
            "global_discard": panchang.get("global_discard", []),
        },
        "day_windows": {
            "abhijit": windows.get("abhijit"),
            "best_choghadiya": best_slot,
            "tri_kaal": windows.get("tri_kaal", []),
            "durmuhurta": windows.get("durmuhurta", []),
            "avoid_choghadiya": windows.get("avoid_choghadiya", []),
            "day_summary": _windows_plain(windows, panchang),
        },
        "alternatives": alternatives,
        "source": "rules37 + PyJHora panchang",
    }


def _windows_plain(windows: dict, panchang: dict) -> str:
    bits = []
    b = windows.get("good_choghadiya", [])
    if b:
        bits.append(f"Best hour: {b[0]['label']} {b[0]['start']}-{b[0]['end']}")
    ab = windows.get("abhijit", {})
    if ab.get("start"):
        bits.append(f"Abhijit {ab['start']}-{ab['end']}")
    rk = panchang.get("rahu_kaal") or {}
    if rk.get("start"):
        bits.append(f"Avoid Rahu Kaal {rk['start']}-{rk['end']}")
    for slot in windows.get("tri_kaal") or []:
        if slot.get("label") != "Rahu Kaal" and slot.get("start"):
            bits.append(f"Avoid {slot['label']} {slot['start']}-{slot['end']}")
    return ". ".join(bits)


def event_catalog() -> list[dict[str, Any]]:
    return list_event_catalog()
