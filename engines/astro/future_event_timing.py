#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Next future life-event window from consultation date - only if chart promises the event."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from astro_precompute import (
    SIGNS,
    SIGN_LORDS,
    VIMSH_LORDS,
    build_antardashas,
    compute_cara_karakas,
    get_dignity,
    house_from_lagna,
    house_sign,
    precompute_from_chart,
)
from btr_rectify import CUSTOM_CATEGORY_SPECS, EVENT_SPECS, _house_lords, _score_lord_for_event
from natal_from_pyjhora import BirthInput, compute_chart_btr
from kapoor_timing import (
    KAPOOR_RULES,
    assess_kapoor_marriage_static,
    kapoor_confirm_window,
)
from event_confluence import (
    CONFLUENCE_THRESHOLD,
    MIN_PRIMARY_DASHA_YES,
    load_supplemental_dashas,
    score_technique_confluence,
)
from kp_event_timing import KP_RULES_SOURCE, load_kp_chart, score_kp_event_window
from chara_yogini_timing import GOEL_RULES_SOURCE, score_chara_goel_window, score_yogini_goel_window
from boney_divisional_timing import BONEY_RULES_SOURCE, score_boney_divisional_window
from gk_transit_dasha import GK_RULES_SOURCE, score_gk_transit_dasha_window
from vedic_varga_goel import varga_from_divisional

# Dropdown keys -> scoring spec (same six-factor / varga mapping as BTR)
FUTURE_EVENT_TYPES: dict[str, dict[str, Any]] = {
    "marriage": {
        "label": "Marriage",
        "spec": EVENT_SPECS["marriage"],
        "promise": "marriage",
    },
    "child_birth": {
        "label": "Child birth",
        "spec": EVENT_SPECS["child"],
        "promise": "child",
    },
    "job_change": {
        "label": "Job change / new role",
        "spec": EVENT_SPECS["first_job"],
        "promise": "career",
    },
    "promotion": {
        "label": "Promotion / recognition",
        "spec": CUSTOM_CATEGORY_SPECS["promotion"],
        "promise": "career",
    },
    "house_purchase": {
        "label": "House / property purchase",
        "spec": CUSTOM_CATEGORY_SPECS["property"],
        "promise": "property",
    },
    "higher_education": {
        "label": "Higher education milestone",
        "spec": EVENT_SPECS["higher_education"],
        "promise": "education",
    },
    "foreign_relocation": {
        "label": "Foreign relocation",
        "spec": EVENT_SPECS["foreign_travel"],
        "promise": "travel",
    },
    "business_start": {
        "label": "Business start",
        "spec": CUSTOM_CATEGORY_SPECS["business"],
        "promise": "business",
    },
    "recovery": {
        "label": "Recovery from illness",
        "spec": CUSTOM_CATEGORY_SPECS["recovery"],
        "promise": "recovery",
    },
    "wealth_rise": {
        "label": "Business / wealth rise",
        "spec": CUSTOM_CATEGORY_SPECS["wealth"],
        "promise": "wealth",
    },
    "status_uplift": {
        "label": "Social status upliftment",
        "spec": CUSTOM_CATEGORY_SPECS["status_uplift"],
        "promise": "status",
    },
}

MAX_SCAN_YEARS = 30
SCORE_MIN = {"strong": 4.0, "moderate": 3.0, "weak": 2.5}

# Divisional charts the promise checks read but that the lean BTR scan omits.
# (D4/D7/D9/D10/D24/D60 already live in BTR_DIV_FACTORS.) Each is mapped to the
# classical topic it governs, so promise gating uses the right varga per event:
#   D2  Hora        - wealth / income
#   D6  Shashthamsha- disease, debts, enemies
#   D8  Ashtamsha   - longevity, chronic / sudden issues
#   D11 Rudramsha   - gains, fulfilment of desires (labha)
#   D12 Dwadashamsha- parents, lineage, inherited property
#   D16 Shodashamsha- vehicles, comforts, domestic happiness
#   D27 Bhamsha     - innate strength / vitality
#   D30 Trimshamsha - misfortunes, illness, evils
EVENT_EXTRA_VARGAS: dict[str, int] = {
    "D2": 2, "D6": 6, "D8": 8, "D11": 11, "D12": 12, "D16": 16, "D27": 27, "D30": 30,
}

# Marc Boney rules12 / *Predicting Major Life Events: A Composite Approach*
COMPOSITE_RULES = {
    "source": "rules12.md (Boney 2020, K.N. Rao composite technique)",
    "parashari": [
        "Vimshottari MD+AD with house/karaka/varga links",
        "Birth lagna + Chandra lagna + dasa-lagna (MD sign) cross-check",
        "Relevant varga (D7/D9/D10/D4/D24)",
        "Boney tri-chart gate: D1 + D9 + event varga dasha lords (rules45)",
    ],
    "jaimini": [
        "Chara maha/antar overlap with Vimshottari window",
        "Cara karakas: DK marriage, PK children, AmK career",
        "Chara period sign hits event-house signs",
    ],
    "transit": "Jupiter/Saturn kendra to event-house signs at window midpoint (Boney/Rao composite)",
    "gk_transit_dasha": "GK transit over natal MD/AD lord signs during window (rules11)",
    "confidence_tiers": {
        "high": "Vimshottari + Chara overlap + transit support",
        "medium": "Vimshottari + Chara overlap (or Vim + 2+ lagna reads)",
        "withheld": "Vimshottari only without composite confirmation - date not released",
    },
    "kapoor_crosscheck": KAPOOR_RULES,
    "confluence": (
        f"Anti-guesswork gate: >{int(CONFLUENCE_THRESHOLD * 100)}% technique agreement PLUS mandatory pillars "
        f"(Vim+varga, Chara lane, Goel rules8, >={MIN_PRIMARY_DASHA_YES} dasha clocks, actualization). "
        f"Date withheld if any pillar fails."
    ),
    "kp_timing": KP_RULES_SOURCE,
    "goel_chara_yogini": GOEL_RULES_SOURCE,
    "boney_divisional": BONEY_RULES_SOURCE,
    "gk_transit_dasha": GK_RULES_SOURCE,
}

EVENT_PLANETS: dict[str, set[str]] = {
    "marriage": {"Venus", "Jupiter", "Moon"},
    "child": {"Jupiter", "Moon"},
    "career": {"Sun", "Saturn", "Mercury", "Mars"},
    "property": {"Mars", "Moon", "Venus"},
    "education": {"Mercury", "Jupiter"},
    "travel": {"Rahu", "Moon", "Jupiter"},
    "business": {"Mercury", "Venus", "Mars"},
    "recovery": {"Jupiter", "Sun", "Moon"},
    "wealth": {"Jupiter", "Venus", "Mercury"},
    "status": {"Sun", "Jupiter", "Mercury"},
}

# Jaimini cara-karaka roles used per event (rules12 ch. themes)
EVENT_JAIMINI_ROLES: dict[str, list[str]] = {
    "marriage": ["Darakaraka", "Putrakaraka"],
    "child": ["Putrakaraka", "Darakaraka"],
    "career": ["Amatyakarak", "Atmakarak"],
    "property": ["Matrukaraka", "Amatyakarak"],
    "education": ["Putrakaraka", "Amatyakarak"],
    "travel": ["Atmakarak", "Gnatikaraka"],
    "business": ["Amatyakarak", "Bhratrukaraka"],
    "recovery": ["Atmakarak", "Putrakaraka"],
    "wealth": ["Amatyakarak", "Bhratrukaraka"],
    "status": ["Amatyakarak", "Atmakarak"],
}


def _fmt_month(d: date) -> str:
    return d.strftime("%b %Y")


def _parse_date(raw: str | None) -> date:
    if not raw:
        return date.today()
    raw = raw.strip()[:10]
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return date.today()


def _chart_pc(
    *,
    client_name: str,
    dob: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    timezone: float,
    place_name: str,
    gender: int,
) -> tuple[dict, dict]:
    base = birth_time if birth_time.count(":") >= 2 else birth_time + ":00"
    inp = BirthInput(
        client_name=client_name,
        dob=dob,
        birth_time=base,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        place_name=place_name,
        gender=gender,
    )
    # D6 (disease), D8 (longevity/sudden), D11 (gains) feed the promise checks;
    # they are scoped to this single chart build, not the BTR scan.
    parsed = compute_chart_btr(inp, extra_vargas=EVENT_EXTRA_VARGAS)
    pc = precompute_from_chart(parsed, client_name, dob, source="pyjhora_future")
    pc.setdefault("meta", {})["dob"] = dob
    try:
        from jaimini_chara_dasha import compute_chara_dasha, sync_chara_dasha_keys
        pc["chara_dasha"] = compute_chara_dasha(
            dob, base, latitude, longitude, timezone,
            gender=gender, place_name=place_name or "BirthPlace",
        )
        sync_chara_dasha_keys(pc)
    except Exception:
        pc["chara_dasha"] = {}
    pc["cara_karakas"] = compute_cara_karakas(parsed.get("planets", {}))
    try:
        from kp_event_timing import attach_kp_to_chart_pc
        attach_kp_to_chart_pc(
            parsed, pc,
            client_name=client_name, dob=dob, birth_time=base,
            latitude=latitude, longitude=longitude, timezone=timezone,
            place_name=place_name, gender=gender,
        )
    except Exception:
        pc.setdefault("kp", {})
    return parsed, pc


def _karaka_planet(pc: dict, role: str) -> dict[str, Any]:
    for k in (pc.get("cara_karakas") or {}).get("karakas", []):
        if k.get("role") == role:
            return k
    return {}


def _event_target_signs(
    event_kind: str,
    lagna_sign: str,
    planets: dict,
    pc: dict,
) -> set[str]:
    """Signs that qualify a Chara period for this event (Boney composite)."""
    signs: set[str] = set()
    if not lagna_sign:
        return signs
    meta = FUTURE_EVENT_TYPES.get(event_kind, {})
    spec = meta.get("spec", {})
    for h in spec.get("houses", []) + spec.get("secondary_houses", []):
        signs.add(house_sign(h, lagna_sign))
    for role in EVENT_JAIMINI_ROLES.get(meta.get("promise", ""), []):
        kk = _karaka_planet(pc, role)
        if kk.get("sign"):
            signs.add(kk["sign"])
    for k in spec.get("karakas", []):
        if planets.get(k, {}).get("sign"):
            signs.add(planets[k]["sign"])
    moon = planets.get("Moon", {}).get("sign")
    if moon and meta.get("promise") in ("marriage", "property"):
        for h in (4, 7, 12):
            signs.add(house_sign(h, moon))
    return {s for s in signs if s in SIGNS}


def _lord_house_from_ref(lord: str, ref_lagna: str, planets: dict) -> int | None:
    psign = planets.get(lord, {}).get("sign")
    if not psign or not ref_lagna:
        return None
    return house_from_lagna(psign, ref_lagna)


def _multi_lagna_hits(
    md: str,
    ad: str,
    planets: dict,
    lagna_sign: str,
    spec: dict,
) -> list[str]:
    """Parashari: birth, Chandra, and dasa-lagna eligibility (rules12 / Boney examples)."""
    hits: list[str] = []
    houses = set(spec.get("houses", []) + spec.get("secondary_houses", []))
    bhavat = spec.get("bhavat")
    moon_sign = planets.get("Moon", {}).get("sign", "")
    md_sign = planets.get(md, {}).get("sign", "")

    for label, ref in (("birth", lagna_sign), ("Chandra", moon_sign), ("dasa", md_sign)):
        if not ref:
            continue
        for lord in (ad, md):
            if not lord:
                continue
            h = _lord_house_from_ref(lord, ref, planets)
            if h in houses:
                hits.append(f"{lord} in {h}th from {label} lagna")
            elif bhavat and h == bhavat:
                hits.append(f"{lord} in bhavat-bhavam {bhavat} from {label} lagna")
    return hits


def _chara_overlap_hits(
    chara: dict,
    start: date,
    end: date,
    target_signs: set[str],
) -> list[str]:
    if not chara or not target_signs:
        return []
    hits: list[str] = []
    for row in chara.get("antar", []):
        try:
            a_start = row["start"] if isinstance(row["start"], date) else date.fromisoformat(str(row["start"])[:10])
            a_end = row["end"] if isinstance(row["end"], date) else date.fromisoformat(str(row["end"])[:10])
        except (ValueError, TypeError):
            continue
        if a_end <= start or a_start >= end:
            continue
        ms, ss = row.get("maha_sign", ""), row.get("sign", "")
        if ss in target_signs:
            hits.append(f"Chara antar {ms}-{ss} (antar sign)")
        elif ms in target_signs:
            hits.append(f"Chara antar {ms}-{ss} (maha sign)")
    return hits


def _kendra_relation(sign_a: str, sign_b: str) -> bool:
    if sign_a not in SIGNS or sign_b not in SIGNS:
        return False
    diff = (SIGNS.index(sign_a) - SIGNS.index(sign_b)) % 12
    return diff in (0, 3, 6, 9)


def _transit_support(
    when: date,
    latitude: float,
    longitude: float,
    timezone: float,
    target_signs: set[str],
    place_name: str = "BirthPlace",
) -> tuple[bool, list[str]]:
    """Jupiter/Saturn kendra to event signs at window midpoint (Boney: transits must support)."""
    if not target_signs:
        return False, []
    try:
        import os
        import sys
        from pathlib import Path
        src = Path(os.environ.get("PYJHORA_SRC", Path(__file__).parent / "pyjhora" / "src"))
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
        from jhora.panchanga import drik
        from jhora import utils, const

        drik.set_ayanamsa_mode("LAHIRI")
        place = drik.Place(place_name, latitude, longitude, timezone)
        jd = utils.julian_day_number((when.year, when.month, when.day), (12, 0, 0))
        clues: list[str] = []
        for pname, pid in (("Jupiter", const._JUPITER), ("Saturn", const._SATURN)):
            lon = drik.sidereal_longitude(jd, pid)
            si = int(lon / 30) % 12
            psign = SIGNS[si]
            for ts in target_signs:
                if _kendra_relation(psign, ts):
                    clues.append(f"Transit {pname} in {psign} kendra to {ts}")
                    break
        return bool(clues), clues[:4]
    except Exception:
        return False, []


def _composite_tier(
    vim_score: float,
    min_score: float,
    lagna_hits: list[str],
    chara_hits: list[str],
    transit_ok: bool,
) -> str:
    if vim_score < min_score:
        return "fail"
    if chara_hits and transit_ok:
        return "high"
    if chara_hits or len(lagna_hits) >= 2:
        return "medium"
    if vim_score >= min_score + 2:
        return "low"
    return "withheld"


def _jaimini_promise_notes(event_kind: str, pc: dict) -> tuple[list[str], list[str]]:
    """Static Jaimini promise/denial from cara karakas (rules12)."""
    meta = FUTURE_EVENT_TYPES.get(event_kind, {})
    kind = meta.get("promise", "")
    reasons, denial = [], []
    dk = _karaka_planet(pc, "Darakaraka")
    pk = _karaka_planet(pc, "Putrakaraka")
    amk = _karaka_planet(pc, "Amatyakarak")

    if kind == "marriage" and dk:
        if dk.get("house") in (6, 8, 12):
            denial.append(f"DK {dk['planet']} in dusthana (house {dk['house']})")
        else:
            reasons.append(f"DK {dk['planet']} in house {dk.get('house')} supports partnership theme")
    if kind == "child" and pk:
        if pk.get("house") in (6, 8, 12) and pk.get("dignity") in ("debilitated", "enemy_sign"):
            denial.append(f"PK {pk['planet']} weak in trik/dusthana")
        else:
            reasons.append(f"PK {pk['planet']} active for progeny theme")
    if kind in ("career", "business", "education") and amk:
        if amk.get("dignity") in ("exalted", "own_sign", "moolatrikona"):
            reasons.append(f"AmK {amk['planet']} strong ({amk.get('dignity')})")
        elif amk.get("house") in (6, 8, 12):
            denial.append(f"AmK {amk['planet']} in dusthana")
    return reasons, denial


def _d1_house_lord(pc: dict, house: int) -> dict[str, Any]:
    lagna = pc.get("lagna", {}).get("sign") or pc.get("meta", {}).get("lagna_sign", "")
    if not lagna:
        return {}
    sign = house_sign(house, lagna)
    lord = SIGN_LORDS[sign]
    pdata = pc.get("planets", {}).get(lord, {})
    return {"lord": lord, "sign": sign, "house": pdata.get("house"), "dignity": get_dignity(lord, pdata.get("sign", ""))}


def assess_marriage_promise(pc: dict, *, female: bool) -> dict[str, Any]:
    karaka = "Jupiter" if female else "Venus"
    d9 = varga_from_divisional(pc, "D9")
    reasons: list[str] = []
    denial: list[str] = []

    if not d9:
        return {
            "promised": False,
            "level": "none",
            "summary": "Navamsha data unavailable - cannot assess marriage promise.",
            "reasons": [],
            "denial": ["missing D9"],
        }

    h1, h7, h4 = d9.benefic_score(1), d9.benefic_score(7), d9.benefic_score(4)
    k_h = d9.planet_house(karaka)

    if k_h == 1 and len(d9.tenants(1)) <= 1:
        denial.append(f"{karaka} alone in Navamsha lagna (classical delay/denial marker)")
    if h7 <= -1:
        denial.append("Malefic pressure on Navamsha 7th house")
    if h1 <= -1:
        denial.append("Navamsha lagna under malefic weight")

    d1_7 = _d1_house_lord(pc, 7)
    if d1_7.get("house") in (6, 8, 12) and d1_7.get("dignity") in ("debilitated", "enemy_sign"):
        denial.append(f"D1 7th lord {d1_7.get('lord')} weak in dusthana")

    if len(denial) >= 2 or (denial and h7 <= -1):
        return {
            "promised": False,
            "level": "none",
            "summary": "Chart does not show a reliable marriage promise - no date is given.",
            "reasons": [],
            "denial": denial,
        }

    j_reasons, j_denial = _jaimini_promise_notes("marriage", pc)
    k = assess_kapoor_marriage_static(pc.get("planets", {}), female=female)
    reasons.extend(j_reasons + k.get("reasons", []))
    denial.extend(j_denial + k.get("denial", []))
    if len(denial) >= 2:
        return {
            "promised": False,
            "level": "none",
            "summary": "Parashari + Jaimini do not support marriage promise - no date given.",
            "reasons": [],
            "denial": denial,
        }

    score = h7 + h1 + (1 if k_h in (4, 7, 11) else 0)
    if h7 >= 1:
        reasons.append("Navamsha 7th house supported")
    if h1 >= 0:
        reasons.append("Navamsha lagna open to partnership")
    if k_h in (4, 7, 11):
        reasons.append(f"Marriage karaka {karaka} well placed in Navamsha")

    level = "strong" if score >= 2 and h7 >= 1 else ("moderate" if score >= 0 else "weak")
    if denial:
        level = "weak"
        reasons.append("Some delay markers present - timing may be late, not absent")

    return {
        "promised": True,
        "level": level,
        "summary": f"Marriage is {'clearly' if level == 'strong' else 'conditionally'} promised in the chart.",
        "reasons": reasons or ["Mixed Navamsha - marriage possible with effort"],
        "denial": denial,
    }


def assess_child_promise(pc: dict) -> dict[str, Any]:
    d7 = varga_from_divisional(pc, "D7")
    denial: list[str] = []
    reasons: list[str] = []

    if not d7:
        return {
            "promised": False,
            "level": "none",
            "summary": "Saptamsha data unavailable - cannot assess child promise.",
            "reasons": [],
            "denial": ["missing D7"],
        }

    lagna_score = d7.benefic_score(1)
    h5, h9 = d7.benefic_score(5), d7.benefic_score(9)

    if lagna_score <= -1:
        denial.append("Malefic weight on Saptamsha lagna")
    if h5 <= -1 and h9 <= -1:
        denial.append("5th and 9th of Saptamsha both stressed")

    jup_h = d7.planet_house("Jupiter")
    if jup_h in (6, 8, 12) and lagna_score <= -1:
        denial.append("Jupiter karaka weak in Saptamsha trik/dusthana with afflicted lagna")

    if lagna_score <= -1 and len(denial) >= 2:
        return {
            "promised": False,
            "level": "none",
            "summary": "Chart does not show a clear progeny promise - no childbirth date is given.",
            "reasons": [],
            "denial": denial,
        }

    j_reasons, j_denial = _jaimini_promise_notes("child_birth", pc)
    reasons.extend(j_reasons)
    denial.extend(j_denial)

    if lagna_score >= 1:
        reasons.append("Saptamsha lagna supported")
    if h5 >= 0 or h9 >= 0:
        reasons.append("Child houses active in Saptamsha")
    if d7.saturn_touches({1, 5, 9}):
        reasons.append("Saturn delay factor - window may be later")

    level = "strong" if lagna_score >= 1 and h5 >= 0 else ("moderate" if lagna_score >= 0 else "weak")
    return {
        "promised": True,
        "level": level,
        "summary": f"Progeny is {'clearly' if level == 'strong' else 'conditionally'} promised - timing from dasha.",
        "reasons": reasons or ["Mixed Saptamsha - children possible with patience"],
        "denial": denial,
    }


def assess_career_promise(pc: dict) -> dict[str, Any]:
    d10 = varga_from_divisional(pc, "D10")
    denial, reasons = [], []

    d1_10 = _d1_house_lord(pc, 10)
    if not d10:
        if d1_10.get("dignity") in ("debilitated", "enemy_sign") and d1_10.get("house") in (6, 8, 12):
            return {
                "promised": False,
                "level": "none",
                "summary": "Career houses are too weak - no job-change window is given.",
                "reasons": [],
                "denial": ["D1 10th lord afflicted in dusthana"],
            }
        return {
            "promised": True,
            "level": "moderate",
            "summary": "Career change possible from D1 - Dashamsha not scored.",
            "reasons": ["D1 10th lord available for timing"],
            "denial": [],
        }

    h10, h1 = d10.benefic_score(10), d10.benefic_score(1)
    if h10 <= -1 and h1 <= -1:
        return {
            "promised": False,
            "level": "none",
            "summary": "Dashamsha does not support a meaningful career shift - no date given.",
            "reasons": [],
            "denial": ["Malefic weight on D10 lagna and 10th"],
        }

    if h10 >= 1:
        reasons.append("Dashamsha 10th house supported")
    if h1 >= 0:
        reasons.append("Professional identity active in Dashamsha")
    d11 = varga_from_divisional(pc, "D11")
    if d11 and d11.benefic_score(11) >= 1:
        reasons.append("Ekadashamsha (D11) 11th house supports career gains")
    j_reasons, j_denial = _jaimini_promise_notes("job_change", pc)
    reasons.extend(j_reasons)
    denial.extend(j_denial)
    if len(j_denial) >= 2:
        return {
            "promised": False,
            "level": "none",
            "summary": "Career indicators too weak in Parashari + Jaimini - no date given.",
            "reasons": [],
            "denial": denial,
        }

    level = "strong" if h10 >= 1 else "moderate"
    return {
        "promised": True,
        "level": level,
        "summary": "Career movement is promised in the chart.",
        "reasons": reasons,
        "denial": denial,
    }


def assess_property_promise(pc: dict) -> dict[str, Any]:
    d4 = varga_from_divisional(pc, "D4")
    d1_4 = _d1_house_lord(pc, 4)
    denial, reasons = [], []

    if d1_4.get("house") in (6, 8, 12) and d1_4.get("dignity") in ("debilitated", "enemy_sign"):
        denial.append(f"D1 4th lord {d1_4.get('lord')} weak")

    if d4:
        h4, h1 = d4.benefic_score(4), d4.benefic_score(1)
        if h4 <= -1 and h1 <= -1:
            return {
                "promised": False,
                "level": "none",
                "summary": "Chart does not support property/home acquisition - no date given.",
                "reasons": [],
                "denial": denial + ["Chaturthamsha 4th and lagna stressed"],
            }
        if h4 >= 1:
            reasons.append("Chaturthamsha 4th house supported")
    else:
        if denial:
            return {
                "promised": False,
                "level": "none",
                "summary": "4th-house promise too weak for property timing.",
                "reasons": [],
                "denial": denial,
            }
        reasons.append("D1 4th-house themes available")

    # D16 (Shodashamsha) governs vehicles, fixed assets and domestic comfort.
    d16 = varga_from_divisional(pc, "D16")
    if d16 and d16.benefic_score(4) >= 1:
        reasons.append("Shodashamsha (D16) 4th house supports vehicles/comforts")
    elif d16 and d16.benefic_score(4) <= -1 and d16.benefic_score(1) <= -1:
        denial.append("Shodashamsha (D16) lagna and 4th stressed")
    # D12 (Dwadashamsha) carries parental / inherited property.
    d12 = varga_from_divisional(pc, "D12")
    if d12 and d12.benefic_score(4) >= 1:
        reasons.append("Dwadashamsha (D12) supports parental/inherited property")

    if len(denial) >= 2 and len(reasons) < 2:
        return {
            "promised": False,
            "level": "none",
            "summary": "Property indicators across D4/D16 are too weak - no date given.",
            "reasons": [],
            "denial": denial,
        }
    level = "strong" if len(reasons) >= 3 else ("moderate" if reasons else "weak")
    return {
        "promised": True,
        "level": level,
        "summary": "Property / home acquisition is possible in the chart.",
        "reasons": reasons or ["4th-house activation possible"],
        "denial": denial,
    }


def assess_education_promise(pc: dict) -> dict[str, Any]:
    d1_5 = _d1_house_lord(pc, 5)
    d1_9 = _d1_house_lord(pc, 9)
    reasons: list[str] = []
    denial: list[str] = []
    if d1_5.get("dignity") not in ("debilitated", "enemy_sign"):
        reasons.append("5th lord reasonably placed")
    if d1_9.get("dignity") not in ("debilitated", "enemy_sign"):
        reasons.append("9th lord reasonably placed")

    # D24 (Chaturvimshamsha / Siddhamsha) is the dedicated chart of higher learning.
    d24 = varga_from_divisional(pc, "D24")
    if d24:
        h1, h4, h9 = d24.benefic_score(1), d24.benefic_score(4), d24.benefic_score(9)
        if h4 >= 1 or h9 >= 1:
            reasons.append("Siddhamsha (D24) 4th/9th house supports formal study")
        if h1 >= 0:
            reasons.append("Siddhamsha lagna open to learning")
        if h1 <= -1 and h4 <= -1 and h9 <= -1:
            denial.append("Siddhamsha (D24) lagna, 4th and 9th all stressed")

    if not reasons or (denial and not any("Siddhamsha" in r for r in reasons)):
        return {
            "promised": False,
            "level": "none",
            "summary": "Higher-education houses are too weak - no milestone date given.",
            "reasons": [],
            "denial": denial or ["5th and 9th lords afflicted"],
        }
    level = "strong" if any("Siddhamsha (D24) 4th/9th" in r for r in reasons) and len(reasons) >= 3 else "moderate"
    return {
        "promised": True,
        "level": level,
        "summary": "Further education milestone is possible.",
        "reasons": reasons,
        "denial": denial,
    }


def assess_travel_promise(pc: dict) -> dict[str, Any]:
    d4 = varga_from_divisional(pc, "D4")
    d1_12 = _d1_house_lord(pc, 12)
    d1_9 = _d1_house_lord(pc, 9)
    if d1_12.get("house") in (6, 8) and d1_9.get("house") in (6, 8):
        return {
            "promised": False,
            "level": "none",
            "summary": "Relocation / foreign-move houses lack support - no date given.",
            "reasons": [],
            "denial": ["12th and 9th lords both weak"],
        }
    reasons = ["9th/12th themes available for relocation"]
    if d4 and d4.benefic_score(4) >= 0:
        reasons.append("Chaturthamsha supports change of base")
    return {
        "promised": True,
        "level": "moderate",
        "summary": "Major relocation is possible in the chart.",
        "reasons": reasons,
        "denial": [],
    }


def assess_business_promise(pc: dict) -> dict[str, Any]:
    return assess_career_promise(pc)  # 7th/10th/11th overlap


def assess_recovery_promise(pc: dict) -> dict[str, Any]:
    """Recovery = supportive 1st/5th/11th lords; heavy 6th/8th stress = slower recovery."""
    denial, reasons = [], []
    for h in (1, 5, 11):
        hl = _d1_house_lord(pc, h)
        if hl.get("dignity") in ("exalted", "own_sign", "moolatrikona", "friend_sign"):
            reasons.append(f"H{h} lord {hl.get('lord')} supports recovery")
        if hl.get("house") in (6, 8, 12) and hl.get("dignity") in ("debilitated", "enemy_sign"):
            denial.append(f"H{h} lord {hl.get('lord')} weak in dusthana")
    h6 = _d1_house_lord(pc, 6)
    if h6.get("dignity") in ("exalted", "own_sign") and h6.get("house") in (6, 8):
        denial.append("6th lord strongly emphasises disease theme  -  recovery needs discipline")
    # Health vargas: D6 disease load, D30 misfortunes, D8 longevity, D27 innate vitality.
    d6 = varga_from_divisional(pc, "D6")
    if d6 and d6.benefic_score(1) >= 1:
        reasons.append("Shashthamsha (D6) lagna supported - body resists disease")
    elif d6 and d6.benefic_score(6) >= 1 and d6.benefic_score(1) <= -1:
        denial.append("Shashthamsha (D6) emphasises the disease house over the body")
    d30 = varga_from_divisional(pc, "D30")
    if d30 and d30.benefic_score(1) <= -1:
        denial.append("Trimshamsha (D30) lagna under malefic weight - misfortune lingers")
    elif d30 and d30.benefic_score(1) >= 1:
        reasons.append("Trimshamsha (D30) lagna supported - misfortunes ease")
    d27 = varga_from_divisional(pc, "D27")
    if d27 and d27.benefic_score(1) >= 1:
        reasons.append("Bhamsha (D27) shows good innate vitality")
    elif d27 and d27.benefic_score(1) <= -1:
        denial.append("Bhamsha (D27) shows low innate strength")
    d8 = varga_from_divisional(pc, "D8")
    if d8 and d8.benefic_score(1) <= -1 and d8.benefic_score(8) <= -1:
        denial.append("Ashtamsha (D8) lagna and 8th stressed - chronic/sudden risk")
    j_reasons, j_denial = _jaimini_promise_notes("recovery", pc)
    reasons.extend(j_reasons)
    denial.extend(j_denial)
    if len(denial) >= 3:
        return {
            "promised": False,
            "level": "none",
            "summary": "Recovery indicators are too weak  -  no confirmed window is given.",
            "reasons": [],
            "denial": denial,
        }
    level = "strong" if len(reasons) >= 2 and len(denial) <= 1 else "moderate"
    return {
        "promised": True,
        "level": level,
        "summary": "Recovery is possible in the chart  -  timing follows supportive dasha bands.",
        "reasons": reasons or ["Mixed recovery markers  -  steady care required"],
        "denial": denial,
    }


def assess_wealth_promise(pc: dict) -> dict[str, Any]:
    denial, reasons = [], []
    for h in (2, 11, 10):
        hl = _d1_house_lord(pc, h)
        if hl.get("dignity") in ("exalted", "own_sign", "moolatrikona"):
            reasons.append(f"H{h} lord {hl.get('lord')} strong for wealth/status gains")
        if hl.get("house") in (6, 8, 12) and hl.get("dignity") in ("debilitated", "enemy_sign"):
            denial.append(f"H{h} lord afflicted in dusthana")
    jupiter = pc.get("planets", {}).get("Jupiter", {})
    if get_dignity("Jupiter", jupiter.get("sign", "")) in ("exalted", "own_sign", "moolatrikona"):
        reasons.append("Jupiter (wealth karaka) well placed")
    # D2 (Hora) shows accumulated wealth; D11 (Rudramsha/labha) shows gains.
    d2 = varga_from_divisional(pc, "D2")
    if d2 and d2.benefic_score(2) >= 1:
        reasons.append("Hora (D2) 2nd house supports accumulated wealth")
    elif d2 and d2.benefic_score(1) <= -1 and d2.benefic_score(2) <= -1:
        denial.append("Hora (D2) lagna and 2nd both stressed")
    d11 = varga_from_divisional(pc, "D11")
    if d11 and d11.benefic_score(11) >= 1:
        reasons.append("Ekadashamsha (D11) 11th house supports gains")
    elif d11 and d11.benefic_score(11) <= -1 and d11.benefic_score(1) <= -1:
        denial.append("Ekadashamsha (D11) lagna and 11th stressed")
    j_reasons, j_denial = _jaimini_promise_notes("wealth_rise", pc)
    reasons.extend(j_reasons)
    denial.extend(j_denial)
    if len(denial) >= 2 and len(reasons) < 2:
        return {
            "promised": False,
            "level": "none",
            "summary": "Wealth-rise indicators are weak  -  no date is given.",
            "reasons": [],
            "denial": denial,
        }
    level = "strong" if len(reasons) >= 3 else "moderate"
    return {
        "promised": True,
        "level": level,
        "summary": "Business or wealth rise is promised in the chart.",
        "reasons": reasons or ["Moderate wealth potential from D1"],
        "denial": denial,
    }


def assess_status_promise(pc: dict) -> dict[str, Any]:
    denial, reasons = [], []
    d10 = varga_from_divisional(pc, "D10")
    d1_10 = _d1_house_lord(pc, 10)
    d1_11 = _d1_house_lord(pc, 11)
    if d1_10.get("dignity") in ("exalted", "own_sign", "moolatrikona"):
        reasons.append(f"10th lord {d1_10.get('lord')} supports public standing")
    if d1_11.get("dignity") in ("exalted", "own_sign", "moolatrikona", "friend_sign"):
        reasons.append(f"11th lord {d1_11.get('lord')} supports gains and recognition")
    sun = pc.get("planets", {}).get("Sun", {})
    if get_dignity("Sun", sun.get("sign", "")) in ("exalted", "own_sign", "moolatrikona"):
        reasons.append("Sun (status karaka) well placed")
    if d10 and d10.benefic_score(10) >= 1:
        reasons.append("Dashamsha 10th house supported")
    if d10 and d10.benefic_score(10) <= -1 and d10.benefic_score(1) <= -1:
        denial.append("Malefic weight on D10 lagna and 10th")
    # D11 (labha) backs recognition and fulfilment of ambitions.
    d11 = varga_from_divisional(pc, "D11")
    if d11 and d11.benefic_score(11) >= 1:
        reasons.append("Ekadashamsha (D11) supports recognition and gains")
    j_reasons, j_denial = _jaimini_promise_notes("status_uplift", pc)
    reasons.extend(j_reasons)
    denial.extend(j_denial)
    if len(denial) >= 2 and not reasons:
        return {
            "promised": False,
            "level": "none",
            "summary": "Social-status uplift is not clearly promised  -  no date given.",
            "reasons": [],
            "denial": denial,
        }
    level = "strong" if len(reasons) >= 2 and not denial else "moderate"
    return {
        "promised": True,
        "level": level,
        "summary": "Social status upliftment is promised in the chart.",
        "reasons": reasons or ["Moderate status potential"],
        "denial": denial,
    }


def assess_promise(event_key: str, pc: dict, *, gender: int) -> dict[str, Any]:
    meta = FUTURE_EVENT_TYPES.get(event_key)
    if not meta:
        return {
            "promised": False,
            "level": "none",
            "summary": f"Unknown event type: {event_key}",
            "reasons": [],
            "denial": [],
        }
    female = gender == 1
    kind = meta["promise"]
    if kind == "marriage":
        return assess_marriage_promise(pc, female=female)
    if kind == "child":
        return assess_child_promise(pc)
    if kind == "career":
        return assess_career_promise(pc)
    if kind == "property":
        return assess_property_promise(pc)
    if kind == "education":
        return assess_education_promise(pc)
    if kind == "travel":
        return assess_travel_promise(pc)
    if kind == "business":
        return assess_business_promise(pc)
    if kind == "recovery":
        return assess_recovery_promise(pc)
    if kind == "wealth":
        return assess_wealth_promise(pc)
    if kind == "status":
        return assess_status_promise(pc)
    return {"promised": False, "level": "none", "summary": "Not assessed.", "reasons": [], "denial": []}


# ---------------------------------------------------------------------------
# Remedies (used when an event is NOT promised, or only weakly/doubtfully so).
# Classical significator-based: strengthen the karaka, propitiate, act.
# ---------------------------------------------------------------------------
REMEDY_BANK: dict[str, dict[str, str]] = {
    "Sun": {
        "mantra": "Aditya Hridayam / Om Hram Hrim Hraum Sah Suryaya Namah (Sundays, sunrise).",
        "charity": "Offer water to the rising Sun; donate wheat and jaggery on Sundays.",
        "practice": "Respect father-figures and authority; keep a steady morning routine.",
    },
    "Moon": {
        "mantra": "Om Som Somaya Namah / Chandra Gayatri (Mondays).",
        "charity": "Donate rice, milk or white cloth on Mondays.",
        "practice": "Honour your mother; protect sleep and emotional calm.",
    },
    "Mars": {
        "mantra": "Hanuman Chalisa on Tuesdays; Om Ang Angarakaya Namah.",
        "charity": "Donate red lentils (masoor) on Tuesdays.",
        "practice": "Channel energy through exercise and discipline; avoid rash decisions.",
    },
    "Mercury": {
        "mantra": "Om Bum Budhaya Namah / Vishnu Sahasranama (Wednesdays).",
        "charity": "Donate green moong, books, or help students on Wednesdays.",
        "practice": "Read, write and learn daily; keep your word.",
    },
    "Jupiter": {
        "mantra": "Om Gram Grim Graum Sah Gurave Namah (108x Thursdays).",
        "charity": "Donate yellow items, turmeric, or support teachers/temples on Thursdays.",
        "practice": "Seek a guru's guidance; give to genuine causes; honour elders.",
    },
    "Venus": {
        "mantra": "Om Shum Shukraya Namah / Sri Suktam (Fridays).",
        "charity": "Donate white sweets, ghee or fragrance on Fridays.",
        "practice": "Cultivate kindness and beauty at home; respect your partner.",
    },
    "Saturn": {
        "mantra": "Hanuman Chalisa on Saturdays; Shani mantra under guidance.",
        "charity": "Donate mustard oil, black sesame; serve the elderly and workers on Saturdays.",
        "practice": "Be patient and consistent; keep commitments; serve the needy.",
    },
    "Rahu": {
        "mantra": "Durga Saptashati / Om Durgayai Namah.",
        "charity": "Donate urad dal on Saturdays/Amavasya.",
        "practice": "Limit speculation and screens; finish one practical goal at a time.",
    },
    "Ketu": {
        "mantra": "Ganesha mantra; Ketu Gayatri (Tuesdays).",
        "charity": "Donate blankets to the poor on Tuesdays.",
        "practice": "A quiet daily meditation hour; release one draining habit.",
    },
}

# Topical (deity / vrat / lifestyle) remedy per event kind.
TOPIC_REMEDY: dict[str, str] = {
    "marriage": "Worship Shiva-Parvati (Somvar vrat); Katyayani/Swayamvara Parvati mantra for timely marriage; "
                "serve and bless married couples; avoid finalising alliances during weak periods.",
    "child": "Santana Gopala mantra and worship of Bala Gopala (Krishna); Putrada Ekadashi vrat; "
             "serve children and donate to their care; both partners adopt sattvic routine.",
    "career": "Surya Namaskar at sunrise and Shani seva on Saturdays; uphold discipline and integrity at work; "
              "begin new roles in supportive windows only.",
    "property": "Correct major Vastu faults; worship Bhumi Devi and Ganesha before any purchase; "
                "donate grain/land-related charity; verify papers carefully in weak periods.",
    "education": "Saraswati mantra (Om Aim Saraswatyai Namah) before study; worship at the start of a course; "
                 "donate books and educational support.",
    "travel": "Durga mantra for safe journeys; settle pending dues before relocating; "
              "do Rahu remedies if relocation is foreign.",
    "business": "Ganesha and Lakshmi worship before launch; Shani discipline in operations; "
                "start ventures only in confluent windows.",
    "recovery": "Maha Mrityunjaya mantra daily (especially Mondays) alongside proper medical care; "
                "Dhanvantari mantra; Rudrabhishek; build rest and nutrition into the routine.",
    "wealth": "Sri Lakshmi / Sri Suktam on Fridays and Diwali; honest earning and steady saving; "
              "avoid speculation during weak dasha bands.",
    "status": "Aditya Hridayam and offering water to the Sun; honour elders and authority; "
              "build visible, credible work rather than seeking shortcuts.",
}


def _event_significators(kind: str, gender: int) -> list[str]:
    female = gender == 1
    base = {
        "marriage": ["Jupiter"] if female else ["Venus"],
        "child": ["Jupiter"],
        "career": ["Saturn", "Sun"],
        "business": ["Mercury", "Mars"],
        "property": ["Mars", "Moon"],
        "education": ["Mercury", "Jupiter"],
        "travel": ["Rahu", "Moon"],
        "recovery": ["Sun", "Jupiter"],
        "wealth": ["Jupiter", "Venus"],
        "status": ["Sun", "Jupiter"],
    }
    return base.get(kind, [])


def build_event_remedies(
    event_key: str,
    pc: dict,
    promise: dict[str, Any],
    *,
    gender: int,
) -> list[dict[str, Any]]:
    """Significator-based remedies to steady a denied or doubtful promise."""
    meta = FUTURE_EVENT_TYPES.get(event_key, {})
    kind = meta.get("promise", "")
    label = meta.get("label", "this area")
    blocks: list[dict[str, Any]] = []

    topic = TOPIC_REMEDY.get(kind)
    if topic:
        blocks.append({"title": f"{label} - supportive practice", "items": [topic]})

    seen: set[str] = set()
    for p in _event_significators(kind, gender):
        rb = REMEDY_BANK.get(p)
        if rb and p not in seen:
            seen.add(p)
            blocks.append({
                "title": f"Strengthen {p} (significator)",
                "items": [rb["mantra"], rb["charity"], rb["practice"]],
            })

    # Address the specific weak planet named in any denial marker.
    for d in promise.get("denial", []):
        pl = next((p for p in REMEDY_BANK if p in d and p not in seen), None)
        if pl:
            seen.add(pl)
            rb = REMEDY_BANK[pl]
            blocks.append({
                "title": f"Pacify {pl} (flagged weak: {d})",
                "items": [rb["mantra"], rb["charity"]],
            })
        if len(seen) >= 4:
            break

    blocks.append({
        "title": "How to use these",
        "items": [
            "Remedies steady and ripen a promise; they do not invent one that the chart withholds.",
            "Practise sincerely for a few months, then re-check timing - the window may open or clarify.",
            "For health, remedies support but never replace medical care.",
        ],
    })
    return blocks


def _is_doubtful(promise: dict[str, Any]) -> bool:
    """A promised-but-weak (delayed / obstructed) reading: withhold a firm date."""
    if not promise.get("promised"):
        return True
    if promise.get("level") == "weak":
        return True
    # Conditional promise carrying live obstruction markers.
    return len(promise.get("denial", [])) >= 2 and promise.get("level") != "strong"


def _future_antardashas(pc: dict, from_date: date, max_years: int = MAX_SCAN_YEARS) -> list[dict[str, Any]]:
    cutoff = from_date + timedelta(days=int(max_years * 365.25))
    out: list[dict[str, Any]] = []
    for md in pc.get("vimshottari", {}).get("sequence", []):
        md_lord = md.get("md_lord", "")
        if md_lord not in VIMSH_LORDS:
            continue
        md_idx = VIMSH_LORDS.index(md_lord)
        for ad in build_antardashas(md, md_idx):
            try:
                start = date.fromisoformat(ad["start"][:10])
                end = date.fromisoformat(ad["end"][:10])
            except ValueError:
                continue
            if end <= from_date or start > cutoff:
                continue
            eff_start = max(start, from_date)
            mid = eff_start + (end - eff_start) // 2
            out.append({
                "md_lord": md_lord,
                "ad_lord": ad["ad_lord"],
                "start": str(eff_start),
                "end": str(end),
                "mid": str(mid),
                "range_label": f"{_fmt_month(eff_start)} - {_fmt_month(end)}",
            })
    out.sort(key=lambda x: x["start"])
    return out


def _score_window(spec: dict, parsed: dict, md: str, ad: str) -> tuple[float, list[str]]:
    lagna_sign = parsed["lagna"]["sign"]
    planets = parsed["planets"]
    divisional = parsed.get("divisional") or {}
    house_lords = _house_lords(lagna_sign, planets)
    clues: list[str] = []
    score = 0.0
    for lord in [md, ad]:
        if lord:
            score += _score_lord_for_event(lord, spec, planets, house_lords, divisional, clues)
    return round(score, 1), clues[:8]


def find_next_windows(
    event_key: str,
    parsed: dict,
    pc: dict,
    from_date: date,
    promise_level: str,
    *,
    latitude: float = 0.0,
    longitude: float = 0.0,
    timezone: float = 0.0,
    place_name: str = "",
    birth_time: str = "",
    dob: str = "",
) -> list[dict[str, Any]]:
    """Boney composite: Vimshottari window must overlap Chara or multi-lagna (rules12)."""
    meta = FUTURE_EVENT_TYPES[event_key]
    spec = meta["spec"]
    min_score = SCORE_MIN.get(promise_level, SCORE_MIN["moderate"])
    lagna_sign = parsed["lagna"]["sign"]
    planets = parsed["planets"]
    target_signs = _event_target_signs(event_key, lagna_sign, planets, pc)
    from jaimini_chara_dasha import get_chara_dasha

    chara = get_chara_dasha(pc)
    hits: list[dict[str, Any]] = []
    meta_promise = meta.get("promise", "")
    dob_str = dob or (pc.get("meta") or {}).get("dob", "")
    try:
        dob_date = date.fromisoformat(dob_str[:10])
    except ValueError:
        dob_date = None

    supplemental = load_supplemental_dashas(
        dob=dob_str,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        place_name=place_name or "BirthPlace",
    ) if dob_str and birth_time else {}

    kp_chart = None
    if pc.get("kp", {}).get("cusps"):
        try:
            from kp_chart import KPChart
            kp_chart = KPChart.from_block(pc, pc["kp"], dob_date or date.today(), "")
        except Exception:
            kp_chart = None
    if not kp_chart and dob_str and birth_time:
        kp_chart = load_kp_chart(
            client_name="", dob=dob_str, birth_time=birth_time,
            latitude=latitude, longitude=longitude, timezone=timezone,
            place_name=place_name or "BirthPlace",
        )

    varga_key = spec.get("varga", "D1")
    event_planets = EVENT_PLANETS.get(meta_promise, set(spec.get("karakas", [])))
    event_houses = set(spec.get("houses", []) + spec.get("secondary_houses", []))
    moon = planets.get("Moon", {})

    for w in _future_antardashas(pc, from_date):
        vim_score, clues = _score_window(spec, parsed, w["md_lord"], w["ad_lord"])
        lagna_hits = _multi_lagna_hits(w["md_lord"], w["ad_lord"], planets, lagna_sign, spec)
        try:
            w_start = date.fromisoformat(w["start"][:10])
            w_end = date.fromisoformat(w["end"][:10])
            w_mid = date.fromisoformat(w["mid"][:10])
        except ValueError:
            continue
        chara_hits = _chara_overlap_hits(chara, w_start, w_end, target_signs)[:3]
        transit_ok, transit_clues = _transit_support(
            w_mid, latitude, longitude, timezone, target_signs, place_name,
        )
        tier = _composite_tier(vim_score, min_score, lagna_hits, chara_hits, transit_ok)
        if tier in ("fail", "withheld", "low"):
            continue

        kap: dict[str, Any] = {}
        if dob_date:
            kap = kapoor_confirm_window(
                dob=dob_date,
                window_start=w_start,
                window_end=w_end,
                md_lord=w["md_lord"],
                ad_lord=w["ad_lord"],
                event_kind=meta_promise,
                planets=planets,
                composite_tier=tier,
            )
            if not kap.get("placement_ok") and tier != "high":
                continue

        kp_score = score_kp_event_window(
            kp_chart,
            event_kind=meta_promise,
            md_lord=w["md_lord"],
            ad_lord=w["ad_lord"],
            window_mid=w_mid,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            place_name=place_name,
        )

        goel_scores = {
            "yogini": score_yogini_goel_window(
                w_start=w_start,
                w_end=w_end,
                event_kind=meta_promise,
                event_houses=event_houses,
                birth_lagna=lagna_sign,
                planets=planets,
                pc=pc,
                moon_nak=moon.get("nakshatra", ""),
                moon_deg_in_nak=float(moon.get("degree_in_nakshatra") or 0),
                dob=dob_date or date.today(),
            ),
            "chara": score_chara_goel_window(
                w_start=w_start,
                w_end=w_end,
                event_kind=meta_promise,
                event_houses=event_houses,
                birth_lagna=lagna_sign,
                planets=planets,
                pc=pc,
                chara=chara,
            ),
        }

        boney_score = score_boney_divisional_window(
            md_lord=w["md_lord"],
            ad_lord=w["ad_lord"],
            event_kind=meta_promise,
            pc=pc,
        )

        gk_score = score_gk_transit_dasha_window(
            md=w["md_lord"],
            ad=w["ad_lord"],
            pc=pc,
            w_start=w_start,
            w_end=w_end,
        )

        confluence = score_technique_confluence(
            event_kind=meta_promise,
            w_start=w_start,
            w_end=w_end,
            vim_score=vim_score,
            min_vim_score=min_score,
            lagna_hits=lagna_hits,
            chara_hits=chara_hits,
            transit_ok=transit_ok,
            varga_key=varga_key,
            clues=clues,
            kapoor_age_hits=kap.get("age_activation_hits", []),
            kapoor_par_hits=kap.get("paribhraman_hits", []),
            kapoor_placement_ok=kap.get("placement_ok", False),
            target_signs=target_signs,
            event_planets=event_planets,
            supplemental=supplemental,
            kp=kp_score,
            goel=goel_scores,
            boney=boney_score,
            gk=gk_score,
        )

        all_clues = clues + lagna_hits + chara_hits + transit_clues
        if gk_score.get("note"):
            all_clues.append(gk_score["note"][:120])
        all_clues.extend(kap.get("age_activation_hits", []))
        all_clues.extend(kap.get("paribhraman_hits", []))
        hits.append({
            **w,
            "score": vim_score,
            "composite_tier": tier,
            "kapoor_tier": kap.get("kapoor_tier", "kapoor_weak"),
            "kapoor_score": kap.get("kapoor_score", 0),
            "confluence": confluence,
            "confluence_pct": confluence["confluence_pct"],
            "confluence_verdict": confluence["verdict"],
            "strength": (
                "confirmed" if confluence["confirmed"]
                else ("strong" if tier == "high" else "medium")
            ),
            "clues": all_clues[:14],
            "varga": varga_key,
            "chara_hits": chara_hits,
            "lagna_hits": lagna_hits,
            "transit_support": transit_ok,
            "gk_transit_support": gk_score.get("yes", False),
            "kapoor": kap,
            "kp": kp_score,
            "goel": goel_scores,
            "boney": boney_score,
            "gk": gk_score,
        })

    hits.sort(key=lambda x: (
        x["start"],
        -x.get("confluence_pct", 0),
        -x["score"],
    ))
    return hits


def predict_next_event(
    *,
    client_name: str,
    dob: str,
    birth_time: str,
    rectified_time: str = "",
    latitude: float,
    longitude: float,
    timezone: float,
    place_name: str = "",
    gender: int = 0,
    event_type: str,
    consultation_date: str = "",
) -> dict[str, Any]:
    """
    From consultation date, return next Vimshottari window for a life event
    only when the natal chart promises that event (D7/D9/D10/D4 checks).
    """
    if event_type not in FUTURE_EVENT_TYPES:
        return {
            "ok": False,
            "error": f"Unknown event type: {event_type}",
            "event_type": event_type,
        }

    use_time = (rectified_time or birth_time).strip()
    if not use_time:
        return {"ok": False, "error": "Birth time required."}

    from_dt = _parse_date(consultation_date)
    label = FUTURE_EVENT_TYPES[event_type]["label"]

    parsed, pc = _chart_pc(
        client_name=client_name,
        dob=dob,
        birth_time=use_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        place_name=place_name,
        gender=gender,
    )

    promise = assess_promise(event_type, pc, gender=gender)
    remedies = build_event_remedies(event_type, pc, promise, gender=gender)
    if not promise.get("promised"):
        return {
            "ok": True,
            "promised": False,
            "event_type": event_type,
            "event_label": label,
            "consultation_date": str(from_dt),
            "birth_time_used": use_time,
            "message": (
                promise.get("summary", "Chart does not promise this event - no date given.")
                + " No date is predicted; focus on the remedies below to strengthen the promise."
            ),
            "promise": promise,
            "remedies": remedies,
            "next_window": None,
            "alternates": [],
        }

    # Promised but weak / obstructed = doubtful. Per the rule "predict only when
    # clearly promised", withhold a firm date and lead with remedies instead.
    if _is_doubtful(promise):
        return {
            "ok": True,
            "promised": True,
            "timing_available": False,
            "doubtful": True,
            "event_type": event_type,
            "event_label": label,
            "consultation_date": str(from_dt),
            "birth_time_used": use_time,
            "message": (
                f"{label} is only conditionally / weakly promised (delay or obstruction markers present), "
                f"so no firm date is given. Work the remedies below first, then re-check timing."
            ),
            "promise": promise,
            "remedies": remedies,
            "next_window": None,
            "alternates": [],
        }

    windows = find_next_windows(
        event_type, parsed, pc, from_dt, promise.get("level", "moderate"),
        latitude=latitude, longitude=longitude, timezone=timezone, place_name=place_name,
        birth_time=use_time, dob=dob,
    )
    if not windows:
        return {
            "ok": True,
            "promised": True,
            "timing_available": False,
            "event_type": event_type,
            "event_label": label,
            "consultation_date": str(from_dt),
            "birth_time_used": use_time,
            "message": (
                f"Chart promises {label.lower()}, but no window passes Boney composite rules "
                f"(Vimshottari + Chara overlap or multi-lagna) in the next {MAX_SCAN_YEARS} years. "
                f"Date withheld per rules12."
            ),
            "promise": promise,
            "remedies": remedies,
            "composite_rules": COMPOSITE_RULES,
            "confluence_threshold": CONFLUENCE_THRESHOLD,
            "next_window": None,
            "alternates": [],
        }

    confirmed = [w for w in windows if (w.get("confluence") or {}).get("confirmed")]
    best_partial = windows[0]
    threshold_pct = int(CONFLUENCE_THRESHOLD * 100)

    if not confirmed:
        conf = best_partial.get("confluence") or {}
        gate = conf.get("release_gate") or {}
        failed = gate.get("failed_checks") or []
        fail_txt = ""
        if failed:
            fail_txt = " Failed pillars: " + "; ".join(
                f"{c['label']}" for c in failed[:4]
            ) + "."
        pct_note = ""
        if conf.get("pct_confirmed") and not gate.get("release_confirmed"):
            pct_note = (
                f" ({conf.get('confluence_pct_display', 0)}% techniques agree but mandatory pillars not met)."
            )
        return {
            "ok": True,
            "promised": True,
            "timing_available": False,
            "event_type": event_type,
            "event_label": label,
            "consultation_date": str(from_dt),
            "birth_time_used": use_time,
            "message": (
                f"Chart promises {label.lower()}, but no window passes the full confluence gate "
                f"in the next {MAX_SCAN_YEARS} years{pct_note} "
                f"Best partial: {best_partial['range_label']} at "
                f"{conf.get('yes_count', 0)}/{conf.get('total_techniques', 0)} "
                f"({conf.get('confluence_pct_display', 0)}%) - date withheld.{fail_txt}"
            ),
            "promise": promise,
            "remedies": remedies,
            "composite_rules": COMPOSITE_RULES,
            "kapoor_rules": KAPOOR_RULES,
            "confluence_threshold": CONFLUENCE_THRESHOLD,
            "release_gate_policy": gate.get("policy", ""),
            "best_partial_window": {
                "range_label": best_partial["range_label"],
                "confluence": conf,
            },
            "next_window": None,
            "alternates": [],
        }

    nxt = confirmed[0]
    alts = [w for w in confirmed[1:4]]
    tier = nxt.get("composite_tier", "medium")
    kap_tier = nxt.get("kapoor_tier", "")
    conf = nxt.get("confluence") or {}
    return {
        "ok": True,
        "promised": True,
        "timing_available": True,
        "event_type": event_type,
        "event_label": label,
        "consultation_date": str(from_dt),
        "birth_time_used": use_time,
        "promise": promise,
        "composite_rules": COMPOSITE_RULES,
        "kapoor_rules": KAPOOR_RULES,
        "confluence_threshold": CONFLUENCE_THRESHOLD,
        "composite_confidence": tier,
        "kapoor_confidence": kap_tier,
        "confluence_confidence": conf.get("verdict", ""),
        "next_window": {
            "start": nxt["start"],
            "end": nxt["end"],
            "range_label": nxt["range_label"],
            "md_lord": nxt["md_lord"],
            "ad_lord": nxt["ad_lord"],
            "score": nxt["score"],
            "strength": nxt["strength"],
            "composite_tier": tier,
            "kapoor_tier": kap_tier,
            "varga": nxt["varga"],
            "clues": nxt["clues"],
            "chara_hits": nxt.get("chara_hits", []),
            "lagna_hits": nxt.get("lagna_hits", []),
            "transit_support": nxt.get("transit_support", False),
            "gk_transit_support": nxt.get("gk_transit_support", False),
            "gk": nxt.get("gk", {}),
            "boney": nxt.get("boney", {}),
            "kapoor": nxt.get("kapoor", {}),
            "kp": nxt.get("kp", {}),
            "goel": nxt.get("goel", {}),
            "confluence": conf,
        },
        "alternates": [
            {
                "range_label": a["range_label"],
                "md_lord": a["md_lord"],
                "ad_lord": a["ad_lord"],
                "score": a["score"],
                "strength": a["strength"],
                "composite_tier": a.get("composite_tier"),
                "kapoor_tier": a.get("kapoor_tier"),
                "confluence_pct": a.get("confluence_pct"),
                "confluence_verdict": a.get("confluence_verdict"),
            }
            for a in alts
        ],
        "message": (
            f"Confirmed {label.lower()}: {nxt['range_label']} "
            f"({nxt['md_lord']} MD / {nxt['ad_lord']} AD). "
            f"{conf.get('yes_count', 0)}/{conf.get('total_techniques', 0)} techniques "
            f"({conf.get('confluence_pct_display', 0)}%) + all mandatory pillars passed."
        ),
    }
