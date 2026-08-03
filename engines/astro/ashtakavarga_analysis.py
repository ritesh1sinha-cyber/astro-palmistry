#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ashtakavarga donor analysis, kakshaya, Sade Sati, extract parsing."""
from __future__ import annotations

import re
from typing import Any

from ashtakavarga_book_data import load_ashtakavarga_book

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
    "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}
CONTRIBUTORS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Lagna"]

HOUSE_LIFE_THEME = {
    1: "identity, body strength, and how confidently you enter new chapters",
    2: "savings rhythm, family speech, movable assets, and day-to-day security",
    3: "courage, siblings, short travel, messaging, and competitive initiative",
    4: "home base, mother-linked routines, property sentiment, and inner peace",
    5: "children, creativity, romance, speculation, and measured risk-taking",
    6: "daily work, service, health discipline, debts, and winning through effort",
    7: "marriage, contracts, public partners, and one-to-one alliances",
    8: "research depth, inheritance, sudden change, and joint resources",
    9: "fortune, father/guru themes, higher learning, pilgrimage, and long journeys",
    10: "career visibility, reputation, authority, and flagship professional output",
    11: "income experiments, peer networks, gains, and fulfilled ambitions",
    12: "expenses, foreign/retreat themes, sleep, and letting go of excess",
}

PLANET_THEME = {
    "Sun": "authority, visibility, and vitality",
    "Moon": "emotional climate, home rhythm, and public responsiveness",
    "Mars": "drive, competition, and decisive action",
    "Mercury": "communication, analysis, trade, and learning loops",
    "Jupiter": "growth, teaching, wisdom, and lawful expansion",
    "Venus": "comfort, partnership warmth, arts, and income through charm",
    "Saturn": "discipline, delay, structure, and earned results",
    "Rahu": "hunger for scale, foreign/tech threads, and unconventional moves",
    "Ketu": "detachment, cut-offs, research, and spiritualised problem-solving",
}


def sav_house_meaning(house: int, sav: int, sign: str, residents: str = "") -> str:
    theme = HOUSE_LIFE_THEME.get(house, "this life area")
    res = f" Natal planets here ({residents}) colour the tone." if residents and residents != "—" else ""
    if sav >= 35:
        return (
            f"When planets cross {sign}, {theme} tends to over-deliver — results land with unusual traction.{res}"
        )
    if sav >= 30:
        return (
            f"Transit through {sign} supports {theme} above your chart average — effort converts more reliably.{res}"
        )
    if sav >= 25:
        return (
            f"Transit through {sign} is workable but not amplified — {theme} needs deliberate pacing.{res}"
        )
    return (
        f"Transit through {sign} is structurally thin — {theme} takes extra proof stacks and patience.{res}"
    )


def _ord_h(n: int) -> str:
    return f"{n}{'st' if n == 1 else 'nd' if n == 2 else 'rd' if n == 3 else 'th'}"


def bav_transit_meaning(planet: str, house: int, bav: int, sav: int) -> str:
    theme = HOUSE_LIFE_THEME.get(house, "this life area")
    pt = PLANET_THEME.get(planet, planet)
    h = _ord_h(house)
    if bav >= 6:
        lead = f"Strong backing for {pt} while it crosses your {h} house — {theme} can move visibly."
    elif bav >= 5:
        lead = f"Supportive filter for {pt} in the {h} house — {theme} progresses when you stay consistent."
    elif bav >= 4:
        lead = f"Average friction for {pt} in the {h} house — {theme} advances in stops and starts."
    elif bav >= 3:
        lead = f"Low traction for {pt} in the {h} house — {theme} needs tighter routines and fewer parallel bets."
    else:
        lead = f"Compressed window for {pt} in the {h} house — protect {theme}; avoid high-stakes gambles."
    if sav >= 32 and bav >= 4:
        lead += f" High SAV ({sav}) in this sign lifts outcomes beyond the raw BAV score."
    elif sav < 25 and bav <= 3:
        lead += f" Weak SAV ({sav}) here amplifies the drag."
    return lead
PLANET_ROWS = {
    "SUN": "Sun", "MOON": "Moon", "MARS": "Mars", "MERC": "Mercury",
    "JUPI": "Jupiter", "VENU": "Venus", "SATU": "Saturn",
}


def house_lords(lagna_sign: str) -> dict[int, str]:
    li = SIGNS.index(lagna_sign)
    return {h: SIGN_LORD[SIGNS[(li + h - 1) % 12]] for h in range(1, 13)}


def kakshaya_sector(deg_in_sign: float) -> dict:
    book = load_ashtakavarga_book()
    for k in book.get("kakshaya_rulers", []):
        if k["start_deg"] <= deg_in_sign < k["end_deg"]:
            return k
    if deg_in_sign >= 26.25:
        return book["kakshaya_rulers"][-1]
    return book["kakshaya_rulers"][0]


def parse_extract_ashtakavarga(text: str) -> dict | None:
    """Parse AstroSage || Ashtakvarga Table || block if present."""
    if "Ashtakvarga Table" not in text:
        return None
    block = text.split("|| Ashtakvarga Table ||", 1)[-1][:2500]
    sav_m = re.search(r"Total\s+((?:\d+\s+){11}\d+)", block)
    if not sav_m:
        return None
    sav = [int(x) for x in sav_m.group(1).split()]
    if len(sav) != 12:
        return None
    bav: dict[str, list[int]] = {}
    for abbr, planet in PLANET_ROWS.items():
        row_m = re.search(rf"{abbr}\s+((?:\d+\s+){{11}}\d+)", block)
        if row_m:
            bav[planet] = [int(x) for x in row_m.group(1).split()]
    return {"sav": sav, "bav": bav}


def validate_against_extract(computed_sav: list[int], extract: dict | None) -> str:
    if not extract or not extract.get("sav"):
        return ""
    exp = extract["sav"]
    diffs = [abs(computed_sav[i] - exp[i]) for i in range(12)]
    if max(diffs) == 0:
        return "Computed SAV matches extract table exactly."
    if max(diffs) <= 1:
        return f"Computed SAV within 1 bindu of extract (max diff {max(diffs)})."
    return f"Computed SAV diverges from extract (max diff {max(diffs)}) - using computed tables."


def donor_analysis(av: Any, planet: str, sign_idx: int, donors_fn, table: dict) -> dict:
    """Full Step-5 donor read for one transit sign."""
    lords = house_lords(av.lagna)
    lagnesh = SIGN_LORD[av.lagna]
    raw = dict(donors_fn(av, planet, sign_idx))
    auspicious = {1, 5, 9, 10}
    ausp_gave = [h for h in auspicious if raw.get(lords[h], False)]
    wealth_gave = {
        "2nd": raw.get(lords[2], False),
        "11th": raw.get(lords[11], False),
    }
    sixth_gave = raw.get(lords[6], False)
    bt = {
        "Lagna": raw.get("Lagna", False),
        "Lagnesh": raw.get(lagnesh, False),
        "Moon": raw.get("Moon", False),
    }
    bt_all = all(bt.values())
    bt_none_lagna_lagnesh = not bt["Lagna"] and not bt["Lagnesh"]
    self_gave = raw.get(planet, False)
    ruled_houses = [h for h in range(1, 13) if lords[h] == planet]

    health_risk = sixth_gave and bt_none_lagna_lagnesh
    competitive = sixth_gave and bt["Lagna"] and bt["Lagnesh"]
    financial = wealth_gave["2nd"] and wealth_gave["11th"]
    financial_block = not wealth_gave["2nd"] or not wealth_gave["11th"]

    if bt_all:
        verdict = "positive"
        verdict_txt = "All Big Three approve - highly supportive transit environment."
    elif bt_none_lagna_lagnesh:
        verdict = "challenging"
        verdict_txt = "Lagna and Lagnesh both withhold - low traction; health caution."
    elif raw.get(planet, False) and len(ausp_gave) >= 2:
        verdict = "positive"
        verdict_txt = "Planet gives to itself and auspicious lords support key life areas."
    elif financial:
        verdict = "positive"
        verdict_txt = "2nd and 11th lords both donate - wealth/gains favoured."
    elif financial_block and not bt["Moon"]:
        verdict = "mixed"
        verdict_txt = "Wealth lords withhold - financial progress needs extra effort."
    else:
        verdict = "mixed"
        verdict_txt = "Mixed donor pattern - results depend on dasha theme."

    if health_risk:
        verdict_txt += " 6th lord donates without Lagna/Lagnesh - watch health routines."
    elif competitive:
        verdict_txt += " 6th lord with Big Three support favours competitive/service wins."

    return {
        "big_three": bt,
        "auspicious_gave": ausp_gave,
        "wealth": wealth_gave,
        "sixth_gave": sixth_gave,
        "self_gave": self_gave,
        "ruled_houses": ruled_houses,
        "verdict": verdict,
        "verdict_txt": verdict_txt,
        "raw": raw,
    }


def assess_md_ad_criticality(
    av: Any,
    md_lord: str,
    ad_lord: str,
    md_sign_idx: int,
    md_house: int,
    md_bav: int,
    md_sav: int,
    ad_sign_idx: int,
    ad_house: int,
    ad_bav: int,
    ad_sav: int,
    donors_fn,
    table: dict,
    residents: list[str] | None = None,
) -> dict:
    """
    Book-backed (rules10 / Boney) MD+AD overlap criticality.
    No hardcoded sign pairs — thresholds from BAV scale + SAV bands + donor checks.
    """
    reasons: list[str] = []
    tier = ""

    # rules10 BAV scale: 0 calamitous, 1 very unfortunate — narrow span on sight
    if md_bav <= 1 or ad_bav <= 1:
        reasons.append("BAV ≤1 — very unfortunate/calamitous band on this slice (rules10)")
        tier = "bad"

    # rules10 / SKILL: BAV ≤2 unfortunate; ≤3 poor; SAV <25 unfavourable
    if md_bav <= 2 and ad_bav <= 2:
        reasons.append(
            "Mahadasha and antardasha BAV both ≤2 — unfortunate/calamitous band (rules10)"
        )
        tier = "bad"

    if md_bav <= 3 and ad_bav <= 3 and tier != "bad":
        reasons.append("MD and AD both ≤3 — poor/low-traction double filter")

    if md_sav < 25 and md_bav <= 3:
        reasons.append(
            f"Weak SAV ({md_sav}) on mahadasha sign — transit drag amplified (rules10 §4)"
        )
    if ad_sav < 25 and ad_bav <= 3:
        reasons.append(
            f"Weak SAV ({ad_sav}) on antardasha hop — structurally thin house theme"
        )

    if md_lord in getattr(av, "bav", {}):
        da = donor_analysis(av, md_lord, md_sign_idx, donors_fn, table)
        if da["verdict"] == "challenging" and ad_bav <= 3:
            reasons.append(
                "Lagna and Lagnesh both withhold on MD sign — health-cautious backdrop (Step 5)"
            )
        if not da["wealth"]["2nd"] and not da["wealth"]["11th"] and md_bav <= 3 and ad_bav <= 3:
            reasons.append("2nd and 11th lords withhold — wealth friction in this overlap")

    # Ch.3 — natal-sign BAV mutes dasha delivery when planet transits its birth sign
    if hasattr(av, "pos") and hasattr(av, "bav"):
        if md_lord in av.bav and av.pos.get(md_lord) == md_sign_idx:
            nb = av.bav[md_lord][md_sign_idx]
            if nb <= 2 and md_bav <= 3:
                reasons.append(
                    f"{md_lord} natal-sign BAV {nb}/8 — muted mahadasha promise in home sign (Ch.3)"
                )
        if ad_lord in av.bav and av.pos.get(ad_lord) == ad_sign_idx:
            nb = av.bav[ad_lord][ad_sign_idx]
            if nb <= 2 and ad_bav <= 3:
                reasons.append(
                    f"{ad_lord} natal-sign BAV {nb}/8 — thin sub-filter on birth sign (Ch.3)"
                )

    if residents and ad_sav < 25 and ad_bav <= 3:
        reasons.append(
            f"Natal occupant(s) {', '.join(residents)} in weak-SAV zone — tone coloured by placement"
        )

    # Confluence: tier bad OR ≥2 independent book factors (never one signal alone)
    critical = tier == "bad" or len(reasons) >= 2
    if critical and tier != "bad":
        tier = "warn"
    return {"critical": critical, "tier": tier, "reasons": reasons}


def sade_sati_status(moon_sign_idx: int, saturn_sign_idx: int) -> dict:
    """Saturn within one sign before/after Moon = Sade Sati zone."""
    diff = (saturn_sign_idx - moon_sign_idx) % 12
    in_zone = diff in (11, 0, 1)  # 12th, 1st, 2nd from Moon
    phase = {11: "approaching (12th from Moon)", 0: "peak (Moon sign)", 1: "closing (2nd from Moon)"}.get(diff, "")
    return {"active": in_zone, "phase": phase, "offset": diff}


def methodology_html() -> str:
    book = load_ashtakavarga_book()
    rules = "".join(f"<li>{r}</li>" for r in book.get("general_rules", []))
    donors = "".join(f"<li>{d}</li>" for d in book.get("donor_checks", []))
    bav_rows = "".join(
        f"<tr><td>{b['score']}</td><td>{b['label']}</td></tr>"
        for b in book.get("bav_quality", [])
    )
    quote = book.get("mantreswara_quote", "")
    return (
        '<h1>0 - Methodology (book-backed)</h1>'
        f'<p class="pred">{book.get("methodology_lead", "")}</p>'
        f'<p class="fine"><em>{quote}</em> - Mantreswara, Phaladipika (cited in Boney).</p>'
        "<h2>Core rules (rules10 / Marc Boney)</h2><ul>" + rules + "</ul>"
        "<h2>Donor checks (Step 5)</h2><ul>" + donors + "</ul>"
        "<h2>BAV quality scale</h2>"
        "<table><tr><th>Score</th><th>Label</th></tr>" + bav_rows + "</table>"
    )


def donor_table_html(analysis: dict, lagna_sign: str = "") -> str:
    lords = house_lords(lagna_sign) if lagna_sign else {}
    rows = []
    for name, gave in analysis["raw"].items():
        if name == "Lagna":
            label = "Lagna (Ascendant)"
            owns = "self/body"
        else:
            owned = [str(h) for h in range(1, 13) if lords.get(h) == name]
            owns = f"rules H{', H'.join(owned)}" if owned else ""
            label = f"{name} ({owns})" if owns else name
        mark = "<span class='check'>Yes</span>" if gave else "<span class='cross'>No</span>"
        cls = "peak" if gave else ""
        rows.append(f"<tr class='{cls}'><td>{label}</td><td>{mark}</td></tr>")
    extra = (
        f"<p><strong>Auspicious lords giving:</strong> "
        f"{', '.join(str(h) for h in analysis['auspicious_gave']) or 'none'}. "
        f"<strong>2nd lord:</strong> {'Yes' if analysis['wealth']['2nd'] else 'No'}; "
        f"<strong>11th lord:</strong> {'Yes' if analysis['wealth']['11th'] else 'No'}. "
        f"<strong>Self-bindu:</strong> {'Yes' if analysis['self_gave'] else 'No'}"
        f"{'' if not analysis['ruled_houses'] else ' (rules houses ' + ', '.join(str(h) for h in analysis['ruled_houses']) + ')'}. "
        f"<strong>Verdict:</strong> {analysis['verdict_txt']}</p>"
    )
    return (
        "<table><tr><th>Donor</th><th>Gave bindu?</th></tr>"
        + "".join(rows)
        + "</table>"
        + extra
    )
