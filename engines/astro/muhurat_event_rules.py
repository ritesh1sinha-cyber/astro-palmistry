#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Event muhurat rules from rules37 / Bhardwaj Complete Indian Predictive Astrology ch. Muhurta.
General panchang filters + chart-specific notes where the book requires natal data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable

from astro_precompute import normalize_nakshatra

# Lunar month index 1-12 (Chaitra..Phalgun)
M = {
    "vaishakh": {2},
    "jyeshtha": {3},
    "ashadha": {4},
    "shravan": {5},
    "magha": {11},
    "phalgun": {12},
    "margashirsha": {9},
    "kartik": {8},
    "all_except_paush_chaitra": {2, 3, 4, 5, 6, 7, 8, 9, 11, 12},
    "all_except_chaitra_paush": {2, 3, 4, 5, 6, 7, 8, 9, 11, 12},
    "foundation_months": {2, 5, 8, 9, 10, 11, 12},
    "grih_months": {2, 3, 11, 9, 12},
}

# Weekday index 0=Sun .. 6=Sat
WD = {
    "mon_fri": {1, 3, 4, 5},
    "sun_fri": {0, 1, 3, 4, 5},
    "sun_sat": {0, 1, 3, 4, 5, 6},
    "mon_sat": {1, 2, 3, 4, 5, 6},
    "tue_thu_fri": {2, 4, 5},
    "sun_mars_jup_sat": {0, 2, 4, 6},
    "sun_mars_merc_jup": {0, 2, 3, 4},
}

# Nakshatra canonical names
N = {
    "naming": {
        "Ashwini", "Rohini", "Mrigashira", "Chitra", "Revati", "Punarvasu", "Pushya",
        "Swati", "Shravana", "Anuradha", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada",
    },
    "mundan": {
        "Ashwini", "Pushya", "Hasta", "Mrigashira", "Chitra", "Revati", "Punarvasu", "Swati",
        "Shravana", "Dhanishtha", "Shatabhisha", "Jyeshtha",
    },
    "akshararambh": {
        "Ashwini", "Ardra", "Pushya", "Hasta", "Mrigashira", "Chitra", "Revati", "Punarvasu",
        "Swati", "Shravana", "Anuradha", "Jyeshtha",
    },
    "engagement": {
        "Krittika", "Rohini", "Hasta", "Mrigashira", "Chitra", "Shravana",
        "Purva Phalguni", "Purva Ashadha", "Purva Bhadrapada",
    },
    "marriage_general": {
        "Rohini", "Mrigashira", "Magha", "Uttara Phalguni", "Hasta", "Swati", "Anuradha",
        "Mula", "Uttara Ashadha", "Uttara Bhadrapada", "Revati",
    },
    "business": {
        "Ashwini", "Rohini", "Pushya", "Mula", "Hasta", "Uttara Phalguni", "Uttara Ashadha",
        "Uttara Bhadrapada", "Mrigashira", "Chitra", "Revati", "Punarvasu", "Anuradha", "Shravana",
    },
    "medicine": {
        "Ashwini", "Rohini", "Pushya", "Mula", "Hasta", "Swati", "Mrigashira", "Chitra", "Revati",
        "Punarvasu", "Shravana", "Dhanishtha", "Shatabhisha", "Jyeshtha",
    },
    "surgery": {"Ashwini", "Rohini", "Hasta", "Swati", "Mrigashira", "Chitra", "Anuradha", "Shravana"},
    "land": {
        "Mrigashira", "Punarvasu", "Ashlesha", "Magha", "Vishakha", "Anuradha",
        "Purva Phalguni", "Purva Ashadha", "Purva Bhadrapada", "Mula", "Swati", "Shatabhisha", "Revati",
    },
    "suit": {"Bharani", "Ardra", "Ashlesha", "Magha", "Purva Phalguni", "Purva Ashadha", "Purva Bhadrapada", "Jyeshtha", "Mula"},
    "buy": {"Ashwini", "Chitra", "Swati", "Shatabhisha", "Revati", "Shravana"},
    "sell": {"Purva Phalguni", "Purva Ashadha", "Purva Bhadrapada", "Vishakha", "Krittika", "Ashlesha", "Bharani"},
    "meet": {"Shravana", "Dhanishtha"},  # + Dhruva/Mridu/Kshipra groups simplified
    "travel": {
        "Ashwini", "Mrigashira", "Punarvasu", "Pushya", "Hasta", "Anuradha", "Shravana", "Dhanishtha", "Revati",
    },
    "foundation": {
        "Rohini", "Mrigashira", "Pushya", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada",
        "Hasta", "Chitra", "Swati", "Anuradha", "Shatabhisha", "Revati",
    },
    "grih": {
        "Ashwini", "Rohini", "Mrigashira", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada",
        "Hasta", "Chitra", "Swati", "Pushya", "Anuradha", "Dhanishtha", "Revati",
    },
}


def _tithis_both(*days: int) -> set[int]:
    out: set[int] = set()
    for d in days:
        out.add(d)
        out.add(d + 15)
    return out


@dataclass
class EventMuhuratRule:
    id: str
    label: str
    plain: str
    weekdays: set[int] = field(default_factory=set)
    tithis: set[int] = field(default_factory=set)
    tithis_shukla_only: set[int] = field(default_factory=set)
    tithis_krishna_only: set[int] = field(default_factory=set)
    allow_purnima: bool = False
    nakshatras: set[str] = field(default_factory=set)
    lunar_months: set[int] = field(default_factory=set)
    discard_natal_nakshatra: bool = False
    chart_specific: str = ""
    needs_partner_chart: bool = False
    odd_year_only: bool = False
    extra_check: Callable[[dict, dict], tuple[bool, str]] | None = None


def _buy_tithi_window(panchang: dict, _pc: dict) -> tuple[bool, str]:
    """Ekadashi Shukla to Panchami Krishna - approximate tithi window."""
    t = panchang["tithi"]
    ok = 11 <= t <= 15 or 16 <= t <= 20
    return ok, "Best buying window is Shukla Ekadashi through Krishna Panchami per rules37"


def _sell_tithi_window(panchang: dict, _pc: dict) -> tuple[bool, str]:
    t = panchang["tithi"]
    ok = 11 <= t <= 15 or 16 <= t <= 20
    return ok, "Selling window mirrors the buy-cycle dates in rules37"


EVENT_RULES: list[EventMuhuratRule] = [
    EventMuhuratRule(
        "naming", "Naming / Jatkarma", "Name the child (11th-12th day after birth)",
        weekdays=WD["mon_fri"], tithis=_tithis_both(2, 3, 5, 7, 10, 11, 12),
        nakshatras=N["naming"],
        chart_specific="Chart-specific: first name syllable should match birth nakshatra pada or birth-sign letters (rules37).",
    ),
    EventMuhuratRule(
        "mundan", "Mundan (first haircut)", "Child's first haircut ceremony",
        weekdays=WD["mon_fri"],
        tithis=_tithis_both(2, 3, 5, 6, 7, 10, 11, 12) | {13, 15},
        lunar_months=M["vaishakh"] | M["jyeshtha"] | M["ashadha"] | M["magha"] | M["phalgun"],
        nakshatras=N["mundan"],
        odd_year_only=True,
        chart_specific="Chart-specific: perform in an odd year of the child's age; muhurat lagna must not fall in 8th from child's birth sign or lagna (pick time slot on the day).",
    ),
    EventMuhuratRule(
        "akshararambh", "Akshararambh (start learning)", "Begin alphabets / schooling",
        weekdays=WD["mon_fri"], tithis=_tithis_both(2, 3, 5, 7, 10, 11, 12),
        lunar_months=M["vaishakh"] | M["jyeshtha"] | M["ashadha"] | M["magha"] | M["phalgun"],
        nakshatras=N["akshararambh"],
        chart_specific="Face east at start; prefer lagna in 2nd, 3rd, 6th, 9th or 12th at the chosen hour.",
    ),
    EventMuhuratRule(
        "engagement", "Engagement", "Engagement / roka ceremony",
        weekdays=WD["sun_fri"],
        tithis=_tithis_both(2, 3, 5, 6, 7, 8, 10, 11, 12) | {16, 13, 15},
        tithis_krishna_only={1},
        lunar_months=M["all_except_paush_chaitra"],
        nakshatras=N["engagement"],
    ),
    EventMuhuratRule(
        "marriage", "Marriage", "Wedding ceremony",
        weekdays=WD["sun_fri"],
        nakshatras=N["marriage_general"],
        lunar_months=M["all_except_paush_chaitra"],
        needs_partner_chart=True,
        chart_specific="Chart-specific: full marriage muhurat needs BOTH bride and groom birth signs - common auspicious dates, Jupiter/Venus non-combust, lagna shuddhi at the wedding hour.",
    ),
    EventMuhuratRule(
        "business_start", "Start business / shop", "Open shop, company, or new venture",
        weekdays=WD["sun_sat"],
        tithis=_tithis_both(1, 2, 3, 5, 6, 7, 10, 11, 12) | {13, 15},
        lunar_months=M["all_except_chaitra_paush"],
        nakshatras=N["business"],
        chart_specific="At the opening hour: 8th and 12th houses of muhurat lagna should be empty.",
    ),
    EventMuhuratRule(
        "medicine", "Medicine (make / take)", "Start medicine or important dose",
        weekdays=WD["sun_fri"],
        tithis=_tithis_both(2, 3, 5, 7, 10, 11, 12) | {16, 13},
        tithis_krishna_only={1},
        nakshatras=N["medicine"],
        discard_natal_nakshatra=True,
    ),
    EventMuhuratRule(
        "surgery", "Surgery", "Schedule operation",
        weekdays=WD["sun_mars_jup_sat"],
        tithis=_tithis_both(2, 3, 5, 6, 7, 10, 12) | {13},
        nakshatras=N["surgery"],
        discard_natal_nakshatra=True,
    ),
    EventMuhuratRule(
        "buy_land", "Buy land", "Purchase property / land",
        weekdays={2, 4, 5},
        tithis=_tithis_both(2, 5, 6, 10, 11) | {16, 15},
        tithis_krishna_only={1},
        lunar_months=M["vaishakh"] | M["jyeshtha"] | M["ashadha"] | M["margashirsha"] | M["magha"] | M["phalgun"],
        nakshatras=N["land"],
    ),
    EventMuhuratRule(
        "legal_suit", "File legal suit", "Court case / formal legal filing",
        weekdays=WD["sun_mars_merc_jup"],
        tithis=_tithis_both(3, 5, 8, 10) | {13, 15},
        nakshatras=N["suit"],
        chart_specific="Malefics in 3rd, 6th, 11th and pure 8th house of muhurat lagna preferred at filing time.",
    ),
    EventMuhuratRule(
        "buy", "Buy (general)", "Purchase valuables / assets",
        weekdays=WD["mon_fri"], nakshatras=N["buy"], extra_check=_buy_tithi_window,
    ),
    EventMuhuratRule(
        "sell", "Sell", "Sell assets / exit position",
        weekdays=WD["mon_fri"], nakshatras=N["sell"], extra_check=_sell_tithi_window,
        chart_specific="Avoid Aquarius lagna at the moment of sale (rules37).",
    ),
    EventMuhuratRule(
        "meet_official", "Meet senior / official", "Boss meeting, government office, authority",
        weekdays=WD["sun_fri"],
        nakshatras=N["meet"],
        chart_specific="Prefer lagna occupied/aspected by benefics; malefics in 3rd, 6th, 11th; strong Moon.",
    ),
    EventMuhuratRule(
        "travel", "Travel", "Start a journey",
        tithis=_tithis_both(1, 2, 3, 5, 7, 10, 11, 13),
        tithis_krishna_only={1},
        nakshatras=N["travel"],
        chart_specific="General: avoid Disha Shool direction today. Chart-specific: avoid lagna in Cancer, Scorpio, Pisces, Taurus and 8th-from-birth-sign lagna for travel start.",
    ),
    EventMuhuratRule(
        "foundation", "Foundation stone", "Lay foundation / begin construction",
        weekdays={1, 3, 4, 5, 6},
        tithis=_tithis_both(2, 3, 5, 6, 7, 10, 11, 12) | {13, 15},
        lunar_months=M["foundation_months"],
        nakshatras=N["foundation"],
        chart_specific="Check Moon nakshatra not in 'sleeping land' position from Sun; dig direction per Vastu Sun sign.",
    ),
    EventMuhuratRule(
        "grih_pravesh", "Griha pravesh", "Enter new home",
        weekdays={1, 3, 4, 5, 6},
        tithis=_tithis_both(2, 3, 5, 7, 10, 11) | {15},
        lunar_months=M["grih_months"],
        nakshatras=N["grih"],
        chart_specific="Chart-specific: stable upachaya lagna (3rd, 6th, 10th, 11th) from YOUR birth sign or lagna at entry time; Kalash Chakra nakshatra from transit Sun.",
    ),
]


PLANET_HORA = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

EVENT_RULES_BY_ID = {r.id: r for r in EVENT_RULES}

# Events where natal chart / DOB materially affects the score (not panchang-only).
CHART_AWARE_EVENTS = {
    "naming", "mundan", "medicine", "surgery", "marriage", "travel",
    "grih_pravesh", "business_start", "legal_suit", "akshararambh",
}


def event_requirements(rule: EventMuhuratRule | None) -> dict[str, bool]:
    """What birth data is required before scoring."""
    if not rule:
        return {"requires_dob": False, "requires_natal_chart": False, "panchang_only": True}
    requires_dob = bool(rule.odd_year_only)
    requires_natal_chart = bool(rule.discard_natal_nakshatra or rule.id == "naming")
    panchang_only = not requires_dob and not requires_natal_chart
    return {
        "requires_dob": requires_dob,
        "requires_natal_chart": requires_natal_chart,
        "panchang_only": panchang_only,
    }


def list_event_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": r.id,
            "label": r.label,
            "plain": r.plain,
            "needs_chart": r.id in CHART_AWARE_EVENTS,
            "needs_partner": r.needs_partner_chart,
            "odd_year": r.odd_year_only,
            **event_requirements(r),
        }
        for r in EVENT_RULES
    ]


def get_event_rule(event_id: str) -> EventMuhuratRule | None:
    return EVENT_RULES_BY_ID.get(event_id)


def _age_completed_years(dob: date, target: date) -> int:
    y = target.year - dob.year
    if (target.month, target.day) < (dob.month, dob.day):
        y -= 1
    return y


def score_event_muhurat(
    rule: EventMuhuratRule,
    panchang: dict[str, Any],
    pc: dict[str, Any],
    target: date,
) -> dict[str, Any]:
    """Score one event: general panchang + chart-specific flags."""
    checks: list[tuple[str, bool, str]] = []
    natal_moon_nak = normalize_nakshatra(
        pc.get("planets", {}).get("Moon", {}).get("nakshatra", "")
    )
    natal_lagna = pc.get("meta", {}).get("lagna_sign") or pc.get("lagna", {}).get("sign", "")
    natal_moon_sign = pc.get("planets", {}).get("Moon", {}).get("sign", "")

    if panchang.get("global_discard"):
        for g in panchang["global_discard"]:
            checks.append(("Global", False, g))

    wd = panchang["weekday_idx"]
    if rule.weekdays:
        ok = wd in rule.weekdays
        checks.append(("Weekday", ok, f"{panchang['weekday']} {'fits' if ok else 'not in auspicious list'}"))

    t = panchang["tithi"]
    pak = panchang["paksha"]
    t_ok = True
    if rule.tithis:
        t_ok = t in rule.tithis or (rule.allow_purnima and t == 15)
        checks.append(("Tithi", t_ok, f"Tithi {panchang['tithi_day']} {pak}"))
    if rule.tithis_shukla_only:
        for d in rule.tithis_shukla_only:
            if pak == "shukla" and panchang["tithi_day"] == d:
                checks.append(("Tithi (Shukla)", True, f"Krishna/Shukla special tithi {d} ok"))
    if rule.tithis_krishna_only and pak == "krishna" and panchang["tithi_day"] == 1:
        checks.append(("Tithi (Krishna 1)", True, "Krishna Pratipada included"))

    if rule.lunar_months:
        lm = panchang.get("lunar_month_idx", 0)
        ok = lm in rule.lunar_months
        checks.append(("Lunar month", ok, panchang.get("lunar_month", "")))

    nak = normalize_nakshatra(panchang.get("nakshatra", ""))
    if rule.nakshatras:
        ok = nak in rule.nakshatras
        checks.append(("Nakshatra", ok, nak))

    if rule.discard_natal_nakshatra and natal_moon_nak and nak == natal_moon_nak:
        checks.append(("Birth star", False, f"Avoid your birth nakshatra ({natal_moon_nak}) for this event"))

    chart_notes: list[str] = []
    if rule.chart_specific:
        chart_notes.append(rule.chart_specific)
    if rule.needs_partner_chart:
        chart_notes.append("Today's score is general panchang only - wedding timing needs both partners' charts.")

    if rule.odd_year_only:
        dob_s = pc.get("meta", {}).get("dob") or pc.get("birth", {}).get("dob", "")
        if dob_s:
            try:
                y, m, d = [int(x) for x in dob_s[:10].split("-")]
                age = _age_completed_years(date(y, m, d), target)
                odd = age % 2 == 1
                checks.append(("Odd year of age", odd, f"Age {age} - mundan traditionally in odd years (1st, 3rd, 5th-)" if odd else f"Age {age} - not an odd year for mundan"))
            except Exception:
                chart_notes.append("Add date of birth to check odd-year rule for mundan.")
        else:
            chart_notes.append("Date of birth needed for mundan odd-year check.")

    if rule.id == "travel" and panchang.get("disha_shool"):
        chart_notes.append(f"Today avoid starting travel toward the {panchang['disha_shool']} (Disha Shool).")

    if rule.id == "naming" and natal_moon_nak:
        chart_notes.append(f"Your birth star {natal_moon_nak} guides the naming syllable - separate from today's panchang score.")

    if rule.extra_check:
        ok, note = rule.extra_check(panchang, pc)
        checks.append(("Date window", ok, note))

    passed = sum(1 for _, ok, _ in checks if ok)
    failed = sum(1 for _, ok, _ in checks if not ok)
    total = len(checks)

    if failed == 0 and passed >= 2:
        verdict = "good"
        plain = f"Good day to plan {rule.plain.lower()} - panchang supports it."
    elif failed <= 1 and passed >= 2:
        verdict = "mixed"
        plain = f"Mixed for {rule.plain.lower()} - possible with care and a strong hour."
    else:
        verdict = "avoid"
        plain = f"Not ideal for {rule.plain.lower()} - consider another date."

    fails = [msg for _, ok, msg in checks if not ok]
    return {
        "id": rule.id,
        "label": rule.label,
        "plain": rule.plain,
        "verdict": verdict,
        "summary": plain,
        "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in checks],
        "chart_notes": chart_notes,
        "needs_partner_chart": rule.needs_partner_chart,
        "natal_context": {
            "moon_nakshatra": natal_moon_nak,
            "moon_sign": natal_moon_sign,
            "lagna": natal_lagna,
        },
    }


def score_all_events(
    panchang: dict[str, Any],
    pc: dict[str, Any],
    target: date,
) -> list[dict[str, Any]]:
    if not panchang.get("available"):
        return []
    return [score_event_muhurat(r, panchang, pc, target) for r in EVENT_RULES]
