#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Panchang + timed muhurat slots via PyJHora (birth place / local day)."""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

from astro_precompute import NAKSHATRAS, normalize_nakshatra

_PYJHORA_SRC = Path(os.environ.get("PYJHORA_SRC", Path(__file__).parent / "pyjhora" / "src"))
if str(_PYJHORA_SRC) not in sys.path:
    sys.path.insert(0, str(_PYJHORA_SRC))

try:
    import swisseph as swe
    from jhora.panchanga import drik
    from jhora import const as pj_const

    _PJ = True
except Exception:
    _PJ = False

LUNAR_MONTHS = [
    "", "Chaitra", "Vaishakh", "Jyeshtha", "Ashadha", "Shravan", "Bhadrapada",
    "Ashwin", "Kartik", "Margashirsha", "Paush", "Magha", "Phalgun",
]

WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

CHOGHADIA_LABEL = {
    0: ("Udveg", "avoid"),
    1: ("Chara", "good"),
    2: ("Labh", "good"),
    3: ("Amrit", "good"),
    4: ("Kaal", "avoid"),
    5: ("Shubha", "good"),
    6: ("Rog", "avoid"),
}

# Disha Shool - avoid travel direction on weekday (rules37 travel chapter).
DISHA_SHOOL = {
    0: "East",      # Sunday
    1: "West",      # Monday - OCR also Sat east; use primary
    2: "North",     # Tuesday
    3: "North",     # Wednesday
    4: "South",     # Thursday
    5: "West",      # Friday
    6: "East",      # Saturday
}


def _jd_local_noon(d: date, tz: float) -> float:
    if not _PJ:
        raise RuntimeError("PyJHora + pyswisseph required for muhurat panchang")
    return swe.julday(d.year, d.month, d.day, 12.0 - tz)


def _nak_name(nak_no: int) -> str:
    if 1 <= nak_no <= 27:
        return NAKSHATRAS[nak_no - 1]
    return ""


def _tithi_paksha(tithi: int) -> tuple[int, str]:
    """Return (day-in-paksha 1-15, 'shukla'|'krishna')."""
    if tithi <= 15:
        return tithi, "shukla"
    return tithi - 15, "krishna"


def _is_rikta_tithi(tithi: int) -> bool:
    day, _ = _tithi_paksha(tithi)
    return day in (4, 9, 14)


def _karana_is_bhadra(karana_data: list) -> bool:
    """Vishti / Bhadra karana (indices 7, 15, 23, ... in 60-karana cycle)."""
    if not karana_data:
        return False
    k = int(karana_data[0])
    return k >= 7 and (k - 7) % 8 == 0


def fetch_day_panchang(
    target: date,
    *,
    latitude: float,
    longitude: float,
    timezone: float,
    place_name: str = "BirthPlace",
) -> dict[str, Any]:
    """Panchang at local noon + sunrise-based slot timings."""
    if not _PJ:
        return {"available": False, "error": "PyJHora not available"}

    jd = _jd_local_noon(target, timezone)
    place = drik.Place(place_name, latitude, longitude, timezone)

    tithi_row = drik.tithi(jd, place)
    tithi_num = int(tithi_row[0])
    nak_row = drik.nakshatra(jd, place)
    nak_num = int(nak_row[0])
    weekday = int(drik.vaara(jd))
    lunar = drik.lunar_month_date(jd, place)
    lunar_month = int(lunar[0]) if lunar else 0
    is_adhik = bool(lunar[3]) if len(lunar) > 3 else False

    yog = drik.yogam(jd, place)
    kar = drik.karana(jd, place)

    day_paksha, paksha = _tithi_paksha(tithi_num)

    chogh = drik.gauri_choghadiya(jd, place)
    day_slots: list[dict[str, Any]] = []
    night_slots: list[dict[str, Any]] = []
    for i, (gc_type, start, end) in enumerate(chogh):
        label, tone = CHOGHADIA_LABEL.get(int(gc_type), ("", "mixed"))
        row = {
            "type_id": int(gc_type),
            "label": label,
            "tone": tone,
            "start": start,
            "end": end,
            "period": "day" if i < 8 else "night",
        }
        (day_slots if i < 8 else night_slots).append(row)

    abhijit = drik.abhijit_muhurta(jd, place)
    durm = drik.durmuhurtam(jd, place)
    durm_pairs = []
    for i in range(0, len(durm), 2):
        if i + 1 < len(durm):
            durm_pairs.append({"start": durm[i], "end": durm[i + 1]})

    rahu_kaal = drik.raahu_kaalam(jd, place)
    yamagandam = drik.yamaganda_kaalam(jd, place)
    gulikai = drik.gulikai_kaalam(jd, place)

    hora = drik.shubha_hora(jd, place)
    hora_slots = [
        {"planet_id": int(h[0]), "start": h[1], "end": h[2]}
        for h in hora[:24]
    ]

    global_discard = []
    if is_adhik:
        global_discard.append("Adhik maas - avoid new auspicious works")
    if _is_rikta_tithi(tithi_num):
        global_discard.append("Rikta tithi - thin for new beginnings")
    if _karana_is_bhadra(kar):
        global_discard.append("Bhadra (Vishti) karana - discard for auspicious work")
    if tithi_num in (15, 30):
        pass  # Purnima/Amavasya context-dependent

    return {
        "available": True,
        "date": target.isoformat(),
        "weekday": WEEKDAYS[weekday],
        "weekday_idx": weekday,
        "tithi": tithi_num,
        "tithi_day": day_paksha,
        "paksha": paksha,
        "is_purnima": tithi_num == 15,
        "is_amavasya": tithi_num == 30,
        "nakshatra": _nak_name(nak_num),
        "nakshatra_idx": nak_num,
        "lunar_month": LUNAR_MONTHS[lunar_month] if 0 < lunar_month < len(LUNAR_MONTHS) else "",
        "lunar_month_idx": lunar_month,
        "adhik_maas": is_adhik,
        "yoga": int(yog[0]) if yog else 0,
        "karana": int(kar[0]) if kar else 0,
        "global_discard": global_discard,
        "disha_shool": DISHA_SHOOL.get(weekday, ""),
        "abhijit": {"start": abhijit[0], "end": abhijit[1]},
        "durmuhurta": durm_pairs,
        "rahu_kaal": {"start": rahu_kaal[0], "end": rahu_kaal[1]},
        "yamagandam": {"start": yamagandam[0], "end": yamagandam[1]},
        "gulikai": {"start": gulikai[0], "end": gulikai[1]},
        "choghadiya_day": day_slots,
        "choghadiya_night": night_slots,
        "hora": hora_slots,
        "source": "PyJHora panchang + rules37 Bhardwaj muhurat chapter",
    }
