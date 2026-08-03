#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daily muhurat section: day windows + all event scores (rules37 + PyJHora)."""
from __future__ import annotations

from datetime import date
from typing import Any

from muhurat_event_rules import EVENT_RULES, PLANET_HORA, score_all_events
from muhurat_panchang import fetch_day_panchang

WEEKDAY_LORD = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


def _plain_day_intro(panchang: dict) -> str:
    parts = [
        f"Panchang at your birth place: {panchang['weekday']}, "
        f"{panchang['tithi_day']} {panchang['paksha']} paksha, "
        f"Moon in {panchang['nakshatra']}, lunar month {panchang.get('lunar_month', '')}."
    ]
    if panchang.get("global_discard"):
        parts.append("Global caution: " + "; ".join(panchang["global_discard"]) + ".")
    return " ".join(parts)


def _day_windows(panchang: dict) -> dict[str, Any]:
    good = []
    avoid = []
    for slot in panchang.get("choghadiya_day", []):
        row = {
            "label": slot["label"],
            "start": slot["start"],
            "end": slot["end"],
            "plain": _choghadiya_plain(slot["label"], slot["tone"]),
        }
        if slot["tone"] == "good":
            good.append(row)
        elif slot["tone"] == "avoid":
            avoid.append(row)

    ab = panchang.get("abhijit", {})
    durm = panchang.get("durmuhurta", [])

    tri_kaal = []
    for key, label, plain in (
        ("rahu_kaal", "Rahu Kaal", "Classic inauspicious window - avoid new starts and ceremonies."),
        ("yamagandam", "Yamagandam", "Yama's hour - avoid important undertakings."),
        ("gulikai", "Gulikai", "Saturnine friction slot - postpone launches if possible."),
    ):
        slot = panchang.get(key) or {}
        if slot.get("start"):
            tri_kaal.append({
                "label": label,
                "start": slot["start"],
                "end": slot["end"],
                "plain": plain,
            })

    hora_good = []
    for h in panchang.get("hora", [])[:12]:
        pid = int(h.get("planet_id", 0))
        if 0 <= pid < len(PLANET_HORA):
            hora_good.append({
                "planet": PLANET_HORA[pid],
                "start": h["start"],
                "end": h["end"],
            })

    return {
        "good_choghadiya": good,
        "avoid_choghadiya": avoid,
        "abhijit": {
            "start": ab.get("start", ""),
            "end": ab.get("end", ""),
            "plain": "Abhijit is the classic midday corrective window - useful when the day is otherwise mixed.",
        },
        "durmuhurta": durm,
        "durmuhurta_plain": "Avoid starting important work during Durmuhurta slots.",
        "tri_kaal": tri_kaal,
        "tri_kaal_plain": "Rahu Kaal, Yamagandam and Gulikai are weekday-fixed inauspicious hours (PyJHora).",
        "hora_day": hora_good[:4],
        "hora_note": "Planetary hours (Hora) from sunrise - match the planet to the work (Mercury for signing, Jupiter for ceremonies, Venus for marriage-related steps).",
    }


def _choghadiya_plain(label: str, tone: str) -> str:
    m = {
        "Amrit": "Best all-purpose window - start what matters.",
        "Shubha": "Clean auspicious slot - good for meetings and beginnings.",
        "Labh": "Gains and profit flavour - commerce-friendly.",
        "Chara": "Movement and travel - good for leaving home or shipping goods.",
        "Kaal": "Sticky timing - postpone launches (choghadiya Kaal; not the same slot as Rahu Kaal tri-kaal).",
        "Rog": "Health-friction tone - avoid medical risk unless emergency.",
        "Udveg": "Anxiety-prone - not for contracts or ceremonies.",
    }
    return m.get(label, "Mixed choghadiya - keep stakes modest.")


def build_daily_muhurat(
    *,
    pc: dict,
    target: date,
    latitude: float,
    longitude: float,
    timezone: float,
    place_name: str = "",
) -> dict[str, Any]:
    panchang = fetch_day_panchang(
        target,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        place_name=place_name or "BirthPlace",
    )
    if not panchang.get("available"):
        return {"available": False, "error": panchang.get("error", "Panchang unavailable")}

    windows = _day_windows(panchang)
    events = score_all_events(panchang, pc, target)

    good_events = [e for e in events if e["verdict"] == "good"]
    mixed_events = [e for e in events if e["verdict"] == "mixed"]
    avoid_events = [e for e in events if e["verdict"] == "avoid"]

    expl = (
        "Muhurat works in two layers. "
        "General panchang (tithi, weekday, nakshatra, choghadiya) is the same for everyone at your birth place on this date. "
        "Chart-specific rules use your birth data - e.g. mundan in an odd year of the child's age, naming from birth star, "
        "surgery avoiding your birth nakshatra, griha pravesh lagna from your birth sign, marriage needing both partners' charts. "
        "Even on a good day, pick the hour (choghadiya, Abhijit, or hora) at ceremony time."
    )

    day_summary = _day_summary_plain(windows, panchang)

    return {
        "available": True,
        "explanation": expl,
        "panchang": panchang,
        "intro": _plain_day_intro(panchang),
        "day_summary": day_summary,
        "windows": windows,
        "events": events,
        "good_events": good_events,
        "mixed_events": mixed_events,
        "avoid_events": avoid_events,
        "event_count": len(EVENT_RULES),
        "source": "rules37 Bhardwaj muhurat chapter + PyJHora choghadiya/Abhijit/Durmuhurta/Rahu Kaal/Hora",
    }


def _day_summary_plain(windows: dict, panchang: dict) -> str:
    bits = []
    if windows["good_choghadiya"]:
        g = windows["good_choghadiya"][0]
        bits.append(f"Strongest day window: {g['label']} choghadiya ({g['start']}-{g['end']}).")
    ab = windows.get("abhijit", {})
    if ab.get("start"):
        bits.append(f"Abhijit safety net: {ab['start']}-{ab['end']}.")
    if windows.get("durmuhurta"):
        d0 = windows["durmuhurta"][0]
        bits.append(f"Skip Durmuhurta around {d0.get('start', '')}-{d0.get('end', '')}.")
    rk = panchang.get("rahu_kaal") or {}
    if rk.get("start"):
        bits.append(f"Avoid Rahu Kaal {rk['start']}-{rk['end']}.")
    for slot in windows.get("tri_kaal") or []:
        if slot.get("label") != "Rahu Kaal" and slot.get("start"):
            bits.append(f"Avoid {slot['label']} {slot['start']}-{slot['end']}.")
    if panchang.get("disha_shool"):
        bits.append(f"Travellers: avoid starting toward {panchang['disha_shool']} (Disha Shool).")
    return " ".join(bits) if bits else "Use Amrit/Shubha choghadiya and Abhijit for important starts."
