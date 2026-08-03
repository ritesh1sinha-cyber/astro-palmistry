#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bhardwaj rules37 remissions + classical remedies for match doshas."""
from __future__ import annotations

from typing import Any

from astro_precompute import ENEMIES, FRIENDS
from goel_navamsha_coverage import SIGN_LORD
from goel_varga import SIGNS, navamsha_sign

# Prashna Marg five-element nakshatra groups (Bhardwaj p.169 OCR).
NAK_ELEMENT: dict[str, str] = {}
_EARTH = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira"]
_WATER = ["Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni"]
_FIRE = ["Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha"]
_AIR = ["Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana"]
_SKY = ["Dhanishtha", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
for n in _EARTH:
    NAK_ELEMENT[n] = "earth"
for n in _WATER:
    NAK_ELEMENT[n] = "water"
for n in _FIRE:
    NAK_ELEMENT[n] = "fire"
for n in _AIR:
    NAK_ELEMENT[n] = "air"
for n in _SKY:
    NAK_ELEMENT[n] = "sky"
NAK_ELEMENT["Mrigshira"] = "earth"


def _lords_friendly(a: str, b: str) -> bool:
    if not a or not b or a == b:
        return bool(a and b)
    if b in FRIENDS.get(a, []) or a in FRIENDS.get(b, []):
        return True
    if b in ENEMIES.get(a, []) or a in ENEMIES.get(b, []):
        return False
    return True  # neutral counts as unity per many melapaka tables


def _moon_sign_lords(pc: dict) -> tuple[str, str, str]:
    moon = (pc.get("planets") or {}).get("Moon") or {}
    sign = moon.get("sign", "")
    deg = float(moon.get("degree_in_sign") or 0)
    d9 = navamsha_sign(sign, deg) if sign else ""
    return sign, SIGN_LORD.get(sign, ""), SIGN_LORD.get(d9, "")


def _bhakoot_axis(moon_a: str, moon_b: str) -> str:
    if not moon_a or not moon_b:
        return ""
    ia, ib = SIGNS.index(moon_a), SIGNS.index(moon_b)
    diff = (ib - ia) % 12
    if diff == 0:
        return "same sign"
    if diff in (1, 11):
        return "2-12 (dwirdwadash)"
    if diff in (4, 8):
        return "5-9 (nav pancham)"
    if diff in (5, 7):
        return "6-8 (shadashtak)"
    return f"{diff + 1}th from each other"


def assess_remissions(
    groom_pc: dict,
    bride_pc: dict,
    ashtakoota: dict[str, Any],
) -> list[dict[str, Any]]:
    """Bhardwaj remission table (rules37 OCR ~p.168-169)."""
    rows: list[dict[str, Any]] = []
    g_sign, g_lord, g_d9_lord = _moon_sign_lords(groom_pc)
    b_sign, b_lord, b_d9_lord = _moon_sign_lords(bride_pc)
    mutual_d1 = _lords_friendly(g_lord, b_lord)
    mutual_d9 = _lords_friendly(g_d9_lord, b_d9_lord)

    if ashtakoota.get("bhakoot_dosha"):
        axis = _bhakoot_axis(g_sign, b_sign)
        ok = mutual_d1 or mutual_d9
        rows.append({
            "dosha": "Bhakoot",
            "remission_applies": ok,
            "detail": (
                f"Moon signs {g_sign} / {b_sign} ({axis}). "
                f"D1 lords {g_lord}-{b_lord} {'friendly/neutral' if mutual_d1 else 'not friendly'}; "
                f"D9 lords {g_d9_lord}-{b_d9_lord} {'friendly/neutral' if mutual_d9 else 'not friendly'}. "
                + ("Bhardwaj half-guna remission when lords unite (rules37)." if ok
                   else "No lord friendship remission per Bhardwaj.")
            ),
        })

    g_nak = ashtakoota.get("groom_nakshatra", "")
    b_nak = ashtakoota.get("bride_nakshatra", "")
    ge, be = NAK_ELEMENT.get(g_nak, ""), NAK_ELEMENT.get(b_nak, "")
    if ge and be:
        elem_ok = ge == be or {ge, be} <= {"air", "fire"} or ge == "earth" or be == "earth"
        rows.append({
            "dosha": "Nakshatra element (Prashna Marg)",
            "remission_applies": elem_ok,
            "detail": (
                f"Groom {g_nak} ({ge}), bride {b_nak} ({be}). "
                + ("Favorable element pairing per Bhardwaj p.169." if elem_ok
                   else "Water-fire pairing flagged inauspicious in Bhardwaj - strengthen remedies.")
            ),
        })

    for k in ashtakoota.get("koots") or []:
        if k.get("id") in ("yoni", "tara", "gana", "maitri") and not k.get("ok"):
            rows.append({
                "dosha": k.get("label", k.get("id")),
                "remission_applies": mutual_d1 or mutual_d9,
                "detail": (
                    "Bhardwaj: mutual friendship/unity of D1 or D9 sign lords can remit this koot deficit "
                    f"({g_lord}/{b_lord} D1; {g_d9_lord}/{b_d9_lord} D9)."
                ),
            })

    return rows


def remedies_for_match(
    ashtakoota: dict[str, Any],
    doshas: dict[str, Any],
    remissions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Classical remedies from Bhardwaj rules37 + Brihaspati/Rajmartand citations."""
    items: list[dict[str, Any]] = []
    blocking = doshas.get("blocking") or []
    bhakoot_axis = ""
    g_sign = (ashtakoota.get("groom_moon_sign") or "")
    b_sign = (ashtakoota.get("bride_moon_sign") or "")

    for d in blocking:
        name = d.get("name", "")
        if "Nadi" in name:
            items.append({
                "for": "Nadi dosha",
                "source": "Brihaspati Samhita (Bhardwaj rules37 p.170)",
                "steps": [
                    "Chant Mahamrityunjaya Mantra with prescribed count before marriage.",
                    "Perform havan, tarpan, and marjan for Nadi shanti.",
                    "Honour learned Brahmins with dakshina, clothes, and anna-dana.",
                ],
            })
        if "Bhakoot" in name:
            axis = _bhakoot_axis(
                ashtakoota.get("groom_moon_sign", ""),
                ashtakoota.get("bride_moon_sign", ""),
            )
            if "6-8" in axis or "shadashtak" in axis:
                steps = [
                    "Rajmartand: donate a cow and a bull (go-dana) for Shadashtak Bhakoot shanti.",
                    "Feed Brahmins and complete shanti puja before fixing wedding muhurat.",
                ]
            elif "5-9" in axis or "nav pancham" in axis:
                steps = [
                    "Rajmartand: donate silver and bronze articles for Nav Pancham Bhakoot.",
                    "Brahmin bhojan and dakshina after shanti homam.",
                ]
            elif "2-12" in axis or "dwirdwadash" in axis:
                steps = [
                    "Rajmartand: donate clothes, gold (as means allow), and support Brahmin bhojan for Dwi-Dwadash Bhakoot.",
                ]
            else:
                steps = [
                    "Perform Bhakoot shanti homam; Bhardwaj stresses remedies before marriage if dosha is active.",
                ]
            remit = any(r.get("remission_applies") for r in remissions if r.get("dosha") == "Bhakoot")
            if remit:
                steps.insert(0, "Partial remission: friendly D1/D9 lords - still do simplified shanti (Bhardwaj half-guna rule).")
            items.append({
                "for": f"Bhakoot dosha ({axis or 'sign mismatch'})",
                "source": "Rajmartand + Muhurta Chintamani (Bhardwaj rules37 p.170-171)",
                "steps": steps,
            })
        if "Manglik" in name:
            items.append({
                "for": "Manglik dosha",
                "source": "Bhardwaj rules37 Manglik chapter",
                "steps": [
                    "Kanya/Kuja shanti or groom-bride both Manglik mutual cancellation ritual.",
                    "Mars-focused puja on Tuesday; avoid marriage without shanti if only one party is Manglik.",
                ],
            })

    weak_koots = [k for k in (ashtakoota.get("koots") or []) if not k.get("ok")]
    if weak_koots and not blocking:
        items.append({
            "for": "Low koot scores (no hard dosha)",
            "source": "Bhardwaj general + Muhurta Chintamani",
            "steps": [
                "Choose marriage muhurat with strong Jupiter/Venus, Abhijit or benefic choghadiya.",
                "Gayatri or Vishnu sahastra nama on wedding morning; graha shanti for weak koot lords.",
            ],
        })

    if any(not k.get("ok") for k in ashtakoota.get("koots") or [] if k.get("id") == "tara"):
        items.append({
            "for": "Tara / Dina deficit",
            "source": "Bhardwaj remission table",
            "steps": [
                "If D1 or D9 lords are friendly, treat as half-remitted; else Tara shanti on bride nakshatra day.",
                "Charity on the weaker Tara day lord (weekday of Moon star lord).",
            ],
        })

    if not items:
        items.append({
            "for": "Maintenance",
            "source": "General marriage muhurat",
            "steps": [
                "Pick marriage date via Muhurat Checker (rules37 marriage event + event location).",
                "Optional: Vishnu-Lakshmi kalyana puja for auspicious start.",
            ],
        })

    items.append({
        "for": "Mandatory note (Bhardwaj)",
        "source": "Muhurta Chintamani quote rules37 p.171",
        "steps": [
            "Do not marry without shanti when a serious dosha is active - obstacles may follow every step.",
            "Establish the wedding only after peace of faults OR documented remission per melapaka texts.",
        ],
    })
    return items
