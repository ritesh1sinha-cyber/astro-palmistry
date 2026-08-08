#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
planet_confluence_report.py — one report per graha, read across every technique.

For each planet (Sun … Ketu) the report shows:
  * natal placement (house, sign, dignity, nakshatra, navamsha, retrograde)
  * which house(s) it rules from the lagna
  * Vedic drishti — which houses/planets it aspects, and who aspects it
  * overall strength (dignity, functional role, BAV, aspects, house placement)
  * Vimśottarī Mahadasha & Antardasha windows and what to expect
  * multi-technique confluence table (Parāśarī, KP, Jaimini, Aṣṭakavarga, …)

CLI:
    python3 planet_confluence_report.py --planets all --name Sample \\
        --dob 1990-01-15 --time 12:00 --place "New Delhi, India"
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from pathlib import Path
from typing import Any, Optional

from astro_precompute import SIGNS, VIMSH_LORDS, build_antardashas
from client_question_engine import (
    HOUSE_KARAKAS,
    QuestionContext,
    evaluate_question_techniques,
    synthesize_answer,
)
from client_report_html import client_css, finalize_report_html
from goel_marriage_timing import _all_antardashas
from house_confluence_report import HOUSE_AREAS, PLANET_REMEDY, TECH_DISPLAY, FAMILY_ORDER, _humanize_note
from vedic_pillar_report import (
    DIGNITY_WORD,
    KENDRA,
    LORD_PERIOD,
    NAT_BENEFIC,
    NAT_MALEFIC,
    Pillar,
    SPECIAL_ASPECT,
    STRONG,
    TRIKONA,
    WEAK,
    _ord,
)
from vedic_vimshottari_report import (
    ANTAR_PLAIN,
    HOUSE_EVENTS,
    MAHA_PLAIN,
    PLANET_KARAKA,
    Vim,
)

BASE_DIR = Path(__file__).resolve().parent
GRAHAS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
DUSTHANA = {6, 8, 12}

PLANET_AREAS: dict[str, dict[str, Any]] = {
    "Sun": {
        "title": "The Sun",
        "areas": [
            "Soul, core identity and life force",
            "Father, authority figures and government",
            "Vitality, confidence and public recognition",
            "Leadership and the ability to stand in your own light",
        ],
        "summary": "The Sun is your inner king — vitality, father, authority and the "
                   "confidence to lead. When strong, life opens; when weak, ego and health need care.",
    },
    "Moon": {
        "title": "The Moon",
        "areas": [
            "Mind, emotions and inner peace",
            "Mother, nurturing and home comfort",
            "Public mood and how others feel around you",
            "Memory, habits and daily wellbeing",
        ],
        "summary": "The Moon is your emotional weather — mind, mother, home and the "
                   "rhythm of daily life. Its strength steadies everything else.",
    },
    "Mars": {
        "title": "Mars",
        "areas": [
            "Courage, drive and physical energy",
            "Siblings, land and property matters",
            "Competition, surgery and decisive action",
            "Anger channelled into productive force",
        ],
        "summary": "Mars is your fire — courage, siblings, property and the push to act. "
                   "Well placed it wins battles; poorly placed it burns bridges.",
    },
    "Mercury": {
        "title": "Mercury",
        "areas": [
            "Intellect, speech and business sense",
            "Writing, trade, accounts and skill",
            "Learning, humour and adaptability",
            "Nerves, hands and quick thinking",
        ],
        "summary": "Mercury is your messenger — speech, trade, study and clever dealing. "
                   "It connects ideas to income when dignified.",
    },
    "Jupiter": {
        "title": "Jupiter",
        "areas": [
            "Wisdom, teachers and dharma",
            "Wealth, children and expansion",
            "Faith, law and fair dealing",
            "Protection and grace in hard times",
        ],
        "summary": "Jupiter is your guru — wisdom, children, wealth and the luck that "
                   "arrives when you act with integrity.",
    },
    "Venus": {
        "title": "Venus",
        "areas": [
            "Love, marriage and partnership",
            "Comfort, luxury and the arts",
            "Vehicles, beauty and social charm",
            "What you attract and enjoy",
        ],
        "summary": "Venus is your magnet — love, comfort, creativity and the pleasures "
                   "that make life worth living.",
    },
    "Saturn": {
        "title": "Saturn",
        "areas": [
            "Discipline, duty and long-term results",
            "Career through slow, honest work",
            "Elders, workers and chronic matters",
            "Fear converted into maturity",
        ],
        "summary": "Saturn is your taskmaster — patience, service and rewards that arrive "
                   "late but stay. It teaches through delay, not denial.",
    },
    "Rahu": {
        "title": "Rahu",
        "areas": [
            "Ambition, obsession and foreign currents",
            "Technology, media and unconventional paths",
            "Sudden rise, illusion and hunger for more",
            "Breaking old rules to reach new ground",
        ],
        "summary": "Rahu amplifies desire — foreign links, tech, fame and the restless "
                   "push beyond your upbringing.",
    },
    "Ketu": {
        "title": "Ketu",
        "areas": [
            "Detachment, spirituality and past karma",
            "Research, occult and specialisation",
            "Letting go, moksha and inner vision",
            "Sudden cuts that redirect your path",
        ],
        "summary": "Ketu strips away — research, spirituality and the release of what "
                   "no longer serves your soul.",
    },
}


@dataclass
class PlanetTechVerdict:
    technique_id: str
    label: str
    family: str
    direction: str
    note: str
    timing: str = ""


def _e(s: Any) -> str:
    return escape(str(s) if s is not None else "")


def _dignity_plain(dig: str) -> str:
    return DIGNITY_WORD.get(str(dig or "").lower(), str(dig or "—"))


def _aspect_houses(from_house: int, planet: str) -> list[int]:
    targets = [(from_house + 6 - 1) % 12 + 1]
    for off in SPECIAL_ASPECT.get(planet, []):
        targets.append((from_house + off - 1 - 1) % 12 + 1)
    return sorted(set(targets))


def _aspect_labels(from_h: int, to_h: int, planet: str) -> str:
    labels: list[str] = []
    if (from_h + 6 - 1) % 12 + 1 == to_h:
        labels.append("7th")
    for off in SPECIAL_ASPECT.get(planet, []):
        if (from_h + off - 1 - 1) % 12 + 1 == to_h:
            labels.append(f"{off}th")
    return "/".join(labels) or "7th"


def _bav_on_sign(pc: dict, planet: str, sign: str) -> Optional[int]:
    row = (pc.get("ashtakavarga") or {}).get("bav", {}).get(planet)
    if not row or sign not in SIGNS:
        return None
    try:
        return int(row[SIGNS.index(sign)])
    except Exception:
        return None


def _karaka_houses(planet: str) -> list[int]:
    return [h for h, kars in HOUSE_KARAKAS.items() if planet in kars]


def _houses_for_planet(pillar: Pillar, planet: str) -> list[int]:
    hs: set[int] = set(pillar.rules.get(planet, []))
    occ = pillar.planets[planet]["house"]
    hs.add(occ)
    for ah in _aspect_houses(occ, planet):
        hs.add(ah)
    hs.update(_karaka_houses(planet))
    return sorted(hs)


def _primary_house(pillar: Pillar, planet: str) -> int:
    ruled = pillar.rules.get(planet, [])
    return ruled[0] if ruled else pillar.planets[planet]["house"]


def _domain_for_house(h: int) -> str:
    return HOUSE_AREAS.get(h, {}).get("domain", "general")


def _strength_score(planet: str, pillar: Pillar, pc: dict) -> tuple[int, list[str]]:
    pl = pillar.planets[planet]
    notes: list[str] = []
    s = 50
    dig = pl["dignity"]
    if dig in STRONG:
        s += 20
        notes.append("strong dignity")
    elif dig in WEAK:
        s -= 20
        notes.append("weak dignity")
    h = pl["house"]
    if h in KENDRA:
        s += 12
        notes.append("kendra placement")
    elif h in TRIKONA:
        s += 8
        notes.append("trikona placement")
    elif h in DUSTHANA:
        s -= 14
        notes.append("dusthana placement")
    func = str(pc.get("planets", {}).get(planet, {}).get("functional_status", ""))
    if "yogakaraka" in func:
        s += 14
        notes.append("yogakaraka for your lagna")
    elif "benefic" in func:
        s += 6
    elif "malefic" in func or "maraka" in func:
        s -= 6
    bav = _bav_on_sign(pc, planet, pl["sign"])
    if bav is not None:
        if bav >= 5:
            s += 8
            notes.append(f"{bav} bindus on its sign")
        elif bav <= 3:
            s -= 8
            notes.append(f"only {bav} bindus on its sign")
    incoming = pillar.aspecting(h)
    ben = sum(1 for a in incoming if a in NAT_BENEFIC and a != planet)
    mal = sum(1 for a in incoming if a in NAT_MALEFIC and a != planet)
    s += ben * 4 - mal * 4
    if ben:
        notes.append(f"aspected by benefics ({', '.join(a for a in incoming if a in NAT_BENEFIC)})")
    if mal:
        notes.append(f"aspected by malefics ({', '.join(a for a in incoming if a in NAT_MALEFIC)})")
    nb = pc.get("pillar", {}).get("neecha_bhanga", {})
    if isinstance(nb, dict) and nb.get(planet):
        s += 10
        notes.append("neecha bhanga (debility cancelled)")
    if pl.get("retro"):
        notes.append("retrograde — results turn inward or delay")
    return max(0, min(100, s)), notes


def _strength_label(score: int) -> str:
    if score >= 75:
        return "Strong"
    if score >= 58:
        return "Moderately strong"
    if score >= 42:
        return "Average"
    if score >= 28:
        return "Below average"
    return "Weak — needs support"


def _eval_parashari(planet: str, pillar: Pillar, pc: dict) -> PlanetTechVerdict:
    pl = pillar.planets[planet]
    dig = pl["dignity"]
    h = pl["house"]
    if dig in STRONG and h not in DUSTHANA:
        d = "positive"
    elif dig in WEAK or h in DUSTHANA:
        d = "caution"
    else:
        d = "neutral"
    ruled = pillar.rules.get(planet, [])
    ruled_txt = ", ".join(_ord(x) for x in ruled) if ruled else "none (node)"
    note = (f"House {h} in {pl['sign']} ({_dignity_plain(dig)}); "
            f"rules {ruled_txt}")
    return PlanetTechVerdict("parashari", "Natal placement", "Parāśarī (classical Vedic)", d, note)


def _eval_functional(planet: str, pc: dict) -> PlanetTechVerdict:
    func = str(pc.get("planets", {}).get(planet, {}).get("functional_status", "neutral"))
    func_h = func.replace("_", " ")
    if "yogakaraka" in func or "benefic" in func:
        d = "positive"
    elif "malefic" in func or "maraka" in func:
        d = "caution"
    else:
        d = "neutral"
    return PlanetTechVerdict("functional", "Functional role for your lagna",
                             "Parāśarī (classical Vedic)", d, f"Acts as {func_h} in your chart")


def _eval_drishti(planet: str, pillar: Pillar) -> PlanetTechVerdict:
    h = pillar.planets[planet]["house"]
    out_hs = _aspect_houses(h, planet)
    incoming = [a for a in pillar.aspecting(h) if a != planet]
    out_parts = []
    for th in out_hs:
        tenants = pillar.houses[th]["tenants"]
        lbl = _aspect_labels(h, th, planet)
        ttxt = f" ({', '.join(tenants)})" if tenants else ""
        out_parts.append(f"House {th} [{lbl}]{ttxt}")
    note = f"Aspects: {'; '.join(out_parts) or '—'}. "
    if incoming:
        note += f"Aspected by: {', '.join(incoming)}."
        ben = sum(1 for a in incoming if a in NAT_BENEFIC)
        mal = sum(1 for a in incoming if a in NAT_MALEFIC)
        d = "positive" if ben > mal else ("caution" if mal > ben else "neutral")
    else:
        note += "No strong incoming graha drishti."
        d = "neutral"
    return PlanetTechVerdict("drishti", "Graha drishti (aspects)", "Parāśarī (classical Vedic)", d, note)


def _eval_ashtakavarga(planet: str, pillar: Pillar, pc: dict) -> PlanetTechVerdict:
    if planet in ("Rahu", "Ketu"):
        return PlanetTechVerdict("ashtakavarga", "Bindu strength", "Aṣṭakavarga",
                                 "abstain", "Nodes use other strength measures")
    sign = pillar.planets[planet]["sign"]
    bav = _bav_on_sign(pc, planet, sign)
    if bav is None:
        return PlanetTechVerdict("ashtakavarga", "Bindu strength", "Aṣṭakavarga",
                                 "abstain", "BAV unavailable")
    if bav >= 5:
        d = "positive"
    elif bav <= 3:
        d = "caution"
    else:
        d = "neutral"
    return PlanetTechVerdict("ashtakavarga", "Bindu strength on its sign", "Aṣṭakavarga",
                             d, f"{bav} bindus in {sign} (5+ strong, 3− light)")


def _eval_navamsha(planet: str, pc: dict) -> PlanetTechVerdict:
    body = pc.get("planets", {}).get(planet, {})
    d9 = body.get("navamsha_sign") or (pc.get("divisional", {}).get("D9", {}) or {}).get(planet)
    if not d9:
        return PlanetTechVerdict("navamsha", "Navāṁśa (D9) support", "Divisional charts",
                                 "abstain", "D9 data unavailable")
    from astro_precompute import get_dignity
    d1d = body.get("dignity", "")
    d9d = get_dignity(planet, d9)
    if d9d in STRONG:
        d = "positive"
        note = f"D9 {d9} ({_dignity_plain(d9d)}) — divisional support"
    elif d9d in WEAK:
        d = "caution"
        note = f"D9 {d9} ({_dignity_plain(d9d)}) — divisional strain"
    else:
        d = "neutral"
        note = f"D9 {d9} ({_dignity_plain(d9d)})"
    if d1d in WEAK and d9d in STRONG:
        note += "; D9 rescues weak D1 placement"
    return PlanetTechVerdict("navamsha", "Navāṁśa (D9) support", "Divisional charts", d, note)


def _eval_jaimini(planet: str, pc: dict) -> PlanetTechVerdict:
    karakas = (pc.get("cara_karakas") or {}).get("karakas") or []
    roles = [k["role"] for k in karakas if k.get("planet") == planet]
    if not roles:
        return PlanetTechVerdict("jaimini", "Chara kāraka role", "Jaimini", "neutral",
                                 "Not among the seven Chara kārakas")
    role = roles[0].replace("karaka", " kāraka").replace("Atma", "Ātma").replace("Amatya", "Amātya")
    d = "positive" if roles[0] in ("Atmakarak", "Putrakaraka") else "neutral"
    if roles[0] == "Darakaraka":
        d = "positive"
    return PlanetTechVerdict("jaimini", "Chara kāraka role", "Jaimini", d,
                             f"Serves as {role} — a primary life significator in Jaimini")


def _eval_kp(planet: str, pc: dict) -> PlanetTechVerdict:
    kp_h = (pc.get("kp") or {}).get("planet_signification", {}).get(planet)
    if not kp_h:
        return PlanetTechVerdict("kp", "KP house significator", "Krishnamurti Paddhati (KP)",
                                 "abstain", "KP significations unavailable")
    hs = ", ".join(f"House {h}" for h in sorted(kp_h))
    d = "positive" if any(h in (1, 5, 9, 10, 11) for h in kp_h) else "neutral"
    if any(h in (6, 8, 12) for h in kp_h) and not any(h in (1, 5, 9, 10, 11) for h in kp_h):
        d = "caution"
    return PlanetTechVerdict("kp", "KP house links", "Krishnamurti Paddhati (KP)", d,
                             f"Signifies {hs} in KP system")


def _eval_vim_dasha(planet: str, pc: dict) -> PlanetTechVerdict:
    vim = pc.get("vimshottari", {})
    cur_md = vim.get("current_md", {}).get("md_lord", "")
    cur_ad = next((a["ad_lord"] for a in vim.get("current_md_antardashas", [])
                   if a.get("status") == "current"), "")
    md_rows = [m for m in vim.get("sequence", []) if m.get("md_lord") == planet]
    if planet == cur_md:
        d = "positive"
        note = f"Currently running {planet} Mahadasha"
    elif planet == cur_ad:
        d = "positive"
        note = f"Currently running {planet} Antardasha (within {cur_md} MD)"
    elif md_rows:
        nxt = next((m for m in md_rows if m.get("status") in ("current", "future")), md_rows[-1])
        d = "neutral"
        note = f"{planet} Mahadasha {nxt.get('start', '')[:7]} to {nxt.get('end', '')[:7]}"
    else:
        ads = [a for a in _all_antardashas(pc) if a.get("ad_lord") == planet]
        fut = [a for a in ads if a.get("start", "") >= str(date.today())]
        if fut:
            d = "neutral"
            note = f"Next {planet} Antardasha: {fut[0].get('range', '')}"
        else:
            d = "neutral"
            note = f"{len(md_rows)} Mahadasha chapter(s) in life; not active now"
    timing = ""
    if md_rows:
        timing = f"{md_rows[0].get('start', '')[:7]} – {md_rows[-1].get('end', '')[:7]}"
    return PlanetTechVerdict("vimshottari", "Daśā activation", "Daśā timing", d, note, timing)


def _eval_conjunct(planet: str, pillar: Pillar) -> PlanetTechVerdict:
    sign = pillar.planets[planet]["sign"]
    mates = [n for n, v in pillar.planets.items() if v["sign"] == sign and n != planet]
    if not mates:
        return PlanetTechVerdict("conjunct", "Same-sign conjunctions", "Parāśarī (classical Vedic)",
                                 "neutral", "No other graha in the same sign")
    ben = [m for m in mates if m in NAT_BENEFIC]
    mal = [m for m in mates if m in NAT_MALEFIC]
    note = f"Shares {sign} with {', '.join(mates)}"
    if ben and not mal:
        d = "positive"
    elif mal and not ben:
        d = "caution"
    else:
        d = "neutral"
    return PlanetTechVerdict("conjunct", "Same-sign conjunctions", "Parāśarī (classical Vedic)", d, note)


def evaluate_planet_techniques(planet: str, pillar: Pillar, pc: dict) -> list[PlanetTechVerdict]:
    out = [
        _eval_parashari(planet, pillar, pc),
        _eval_functional(planet, pc),
        _eval_drishti(planet, pillar),
        _eval_conjunct(planet, pillar),
        _eval_ashtakavarga(planet, pillar, pc),
        _eval_navamsha(planet, pc),
        _eval_vim_dasha(planet, pc),
        _eval_jaimini(planet, pc),
        _eval_kp(planet, pc),
    ]
    # Cross-house confluence via shared question engine
    ph = _primary_house(pillar, planet)
    hs = _houses_for_planet(pillar, planet)
    ctx = QuestionContext(
        question=f"How strong and supportive is {planet} in my chart?",
        topic="general",
        domain=_domain_for_house(ph),
        title=f"{PLANET_AREAS[planet]['title']} strength",
        intent="general",
        primary_house=ph,
        houses=hs,
        favorable_houses=[],
        denying_houses=[],
    )
    meta = pc.get("meta", {})
    for v in evaluate_question_techniques(ctx, pc, birth_kw={
        "dob": meta.get("dob", ""), "birth_time": meta.get("birth_time", ""),
    }):
        if v.direction == "abstain":
            continue
        fam = TECH_DISPLAY.get(v.technique_id, (v.label, "Confluence gate"))[1]
        out.append(PlanetTechVerdict(
            v.technique_id, TECH_DISPLAY.get(v.technique_id, (v.label, fam))[0],
            fam, v.direction, _humanize_note(v.note), v.timing,
        ))
    return [v for v in out if v.direction != "abstain"]


def _synthesize_planet(verdicts: list[PlanetTechVerdict]) -> dict[str, Any]:
    applicable = [v for v in verdicts if v.direction != "abstain"]
    pos = sum(1 for v in applicable if v.direction == "positive")
    cau = sum(1 for v in applicable if v.direction == "caution")
    neu = sum(1 for v in applicable if v.direction == "neutral")
    total = len(applicable) or 1
    pct = int(round(pos / total * 100))
    if pct >= 70 and pos > cau:
        conf = "HIGH"
    elif pct >= 55:
        conf = "MODERATE"
    elif pct >= 40:
        conf = "LOW"
    else:
        conf = "LOW"
    return {
        "confluence_pct": pct,
        "confidence": conf,
        "positive_votes": pos,
        "caution_votes": cau,
        "neutral_votes": neu,
        "total_techniques": total,
    }


def _ad_period_reading(ad_lord: str, md_lord: str, vim: Vim) -> str:
    """
    One distinct line per Antardasha row: how the sub-period lord plays
    inside the Mahadasha chapter (not the same generic ANTAR_PLAIN every time).
    """
    if ad_lord == md_lord:
        return (
            f"{ad_lord} runs both layers — themes double up. "
            f"{ANTAR_PLAIN.get(ad_lord, '')}"
        )
    ad_pl = vim.planets[ad_lord]
    ad_occ = ad_pl["house"]
    md_occ = vim.planets[md_lord]["house"]
    ad_ruled = vim.rules.get(ad_lord, [])
    md_ruled = vim.rules.get(md_lord, [])
    ad_kw = PLANET_KARAKA.get(ad_lord, ad_lord).split(",")[0].strip().lower()
    md_kw = PLANET_KARAKA.get(md_lord, md_lord).split(",")[0].strip().lower()
    house_bit = HOUSE_EVENTS.get(ad_occ, "this part of life").split(",")[0].strip().lower()
    md_chapter = MAHA_PLAIN.get(md_lord, "").split(".")[0].strip().lower()
    ruled_bits = ""
    if ad_ruled:
        ruled_bits = f" It rules {_ord(ad_ruled[0])}" + (
            f" and {_ord(ad_ruled[1])}" if len(ad_ruled) > 1 else ""
        ) + "."
    return (
        f"{ad_lord} antardasha under {md_lord} mahadasha ({md_chapter}): "
        f"{ad_lord} in the {_ord(ad_occ)} house colours {ad_kw}, while the background "
        f"chapter keeps {md_kw} active. Expect movement in {house_bit}.{ruled_bits}"
    )


def _dasha_section(planet: str, pc: dict, vim: Vim) -> str:
    md_rows = [m for m in pc.get("vimshottari", {}).get("sequence", []) if m.get("md_lord") == planet]
    rows = ""
    for m in md_rows:
        st, en = m.get("start", "")[:10], m.get("end", "")[:10]
        status = m.get("status", "")
        badge = "pos" if status == "current" else ("neu" if status == "future" else "")
        badge_lbl = status.title() if status else ""
        pred = MAHA_PLAIN.get(planet, "")
        badge_html = f'<span class="bdg {badge}">{badge_lbl}</span>' if badge_lbl else ""
        rows += (
            f"<tr><td><strong>Mahadasha</strong></td>"
            f"<td>{_e(st)} → {_e(en)} {badge_html}</td>"
            f"<td>{_e(pred)} {vim.strength_note(planet)}</td></tr>"
        )
    ads = [a for a in _all_antardashas(pc) if a.get("ad_lord") == planet]
    today_s = str(date.today())

    def _ad_sort(a: dict) -> tuple:
        st, en = a.get("start", ""), a.get("end", "")
        if st <= today_s <= en:
            return (0, st)
        if st > today_s:
            return (1, st)
        return (2, st)

    ads.sort(key=_ad_sort)
    current = [a for a in ads if a.get("start", "") <= today_s <= a.get("end", "")]
    future = [a for a in ads if a.get("start", "") > today_s][:5]
    past = sorted([a for a in ads if a.get("end", "") < today_s], key=lambda x: x.get("start", ""))[-3:]
    picked: list[dict] = []
    seen: set[tuple] = set()
    for a in current + future + past:
        key = (a.get("md_lord"), a.get("start", "")[:10])
        if key in seen:
            continue
        seen.add(key)
        picked.append(a)

    for a in picked:
        st, en = a.get("start", "")[:10], a.get("end", "")[:10]
        md_lord = a.get("md_lord", "")
        is_cur = a.get("start", "") <= today_s <= a.get("end", "")
        cur_badge = ' <span class="bdg pos">Current</span>' if is_cur else ""
        reading = _ad_period_reading(planet, md_lord, vim)
        rows += (
            f"<tr><td>Antardasha ({_e(md_lord)} MD)</td>"
            f"<td>{_e(st)} → {_e(en)}{cur_badge}</td>"
            f"<td>{_e(reading)}</td></tr>"
        )
    if not rows:
        return "<p class='fine'>No Mahadasha/Antardasha tables available for this graha.</p>"
    lead = vim.prediction(planet, "mahadasha")
    expect = LORD_PERIOD.get(planet, "")
    return f"""
<p>{_e(lead)}</p>
<p style="margin-top:.6rem"><strong>In this planet's dasha, broadly expect:</strong> {_e(expect)}</p>
<table class="tech">
  <tr><th>Period type</th><th>Dates</th><th>What to expect</th></tr>
  {rows}
</table>"""


_BADGE = {"positive": ("Supportive", "pos"), "caution": ("Caution", "cau"), "neutral": ("Neutral", "neu")}


def _extra_css() -> str:
    return """
.planet-num{font-size:.8rem;letter-spacing:.16em;text-transform:uppercase;opacity:.8}
.areas{list-style:none;padding:0;margin:.4rem 0 0}
.areas li{padding:7px 0 7px 26px;position:relative;border-bottom:1px solid var(--border)}
.areas li:before{content:"\\2022";position:absolute;left:6px;color:var(--accent);font-weight:700}
.gauge{display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.gnum{font-size:2.6rem;font-weight:800;line-height:1}
.strnum{font-size:2rem;font-weight:800;color:var(--accent)}
.pill{display:inline-block;padding:3px 12px;border-radius:999px;font-size:.78rem;font-weight:700}
.pill.HIGH,.pill.VERY{background:#e6f4ea;color:#1f6b42}
.pill.MODERATE{background:#fdf2dd;color:#9a5a00}
.pill.LOW{background:#fae7e7;color:#9a2a2a}
.tally{font-size:.86rem;color:var(--muted)}
table.tech{width:100%;border-collapse:collapse;font-size:.9rem;margin:8px 0 0}
table.tech th,table.tech td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--border);vertical-align:top}
table.tech th{font-size:.74rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.fam{font-weight:700;color:var(--accent);background:#f6f4fb}
.bdg{display:inline-block;padding:2px 9px;border-radius:999px;font-size:.74rem;font-weight:700;white-space:nowrap}
.bdg.pos{background:#e6f4ea;color:#1f6b42}
.bdg.cau{background:#fdf2dd;color:#9a5a00}
.bdg.neu{background:#eee;color:#555}
.aspect-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:.6rem}
@media(max-width:640px){.aspect-grid{grid-template-columns:1fr}}
.mini-card{background:#faf9f7;border:1px solid var(--border);border-radius:8px;padding:12px 14px}
.mini-card h4{margin:0 0 6px;font-size:.88rem;color:var(--accent)}
"""


def generate_planet_confluence_html(
    pc: dict,
    planet: str,
    client_name: str = "Client",
) -> tuple[str, dict]:
    area = PLANET_AREAS[planet]
    meta = pc.get("meta", {})
    pillar = Pillar(pc)
    vim = Vim(pc)
    pl = pillar.planets[planet]
    body = pc.get("planets", {}).get(planet, {})
    ruled = pillar.rules.get(planet, [])
    occ_h = pl["house"]
    score, score_notes = _strength_score(planet, pillar, pc)
    verdicts = evaluate_planet_techniques(planet, pillar, pc)
    merged = _synthesize_planet(verdicts)
    pct = merged["confluence_pct"]
    conf = merged["confidence"]
    conf_cls = "VERY" if conf.startswith("VERY") else conf

    lagna = meta.get("lagna_sign", "")
    lagna_deg = meta.get("lagna_degree", "")
    try:
        lagna_deg = f"{float(lagna_deg):.1f}°"
    except (TypeError, ValueError):
        pass

    areas_html = "".join(f"<li>{_e(a)}</li>" for a in area["areas"])
    ruled_txt = ", ".join(f"House {h} ({pillar.houses[h]['sign']})" for h in ruled) if ruled else "none — nodes do not rule signs"

    # Outgoing aspects
    out_lines = []
    for th in _aspect_houses(occ_h, planet):
        lbl = _aspect_labels(occ_h, th, planet)
        tenants = pillar.houses[th]["tenants"]
        t = f" — occupants: {', '.join(tenants)}" if tenants else ""
        out_lines.append(f"<li>House {th} ({pillar.houses[th]['sign']}) [{lbl} aspect]{t}</li>")
    out_html = "".join(out_lines) or "<li>Standard 7th-house aspect only</li>"

    incoming = [a for a in pillar.aspecting(occ_h) if a != planet]
    in_html = "".join(f"<li>{_e(a)} aspects House {occ_h} where {planet} sits</li>" for a in incoming) or "<li>No other graha drishti directly on this placement</li>"

    conj = [n for n, v in pillar.planets.items() if v["sign"] == pl["sign"] and n != planet]
    conj_txt = ", ".join(conj) if conj else "none"

    jaimini_roles = [k["role"] for k in (pc.get("cara_karakas") or {}).get("karakas", []) if k.get("planet") == planet]
    jaimini_txt = jaimini_roles[0] if jaimini_roles else "—"

    # Technique table
    by_family: dict[str, list] = {}
    for v in verdicts:
        by_family.setdefault(v.family, []).append(v)
    rows = ""
    for fam in FAMILY_ORDER + [f for f in by_family if f not in FAMILY_ORDER]:
        items = by_family.get(fam)
        if not items:
            continue
        rows += f'<tr><td class="fam" colspan="3">{_e(fam)}</td></tr>'
        for v in items:
            label, cls = _BADGE.get(v.direction, ("Neutral", "neu"))
            timing = f' <span class="fine">{_e(v.timing)}</span>' if v.timing else ""
            rows += (
                f"<tr><td>{_e(v.label)}</td>"
                f'<td><span class="bdg {cls}">{label}</span></td>'
                f"<td>{_e(_humanize_note(v.note))}{timing}</td></tr>"
            )

    dasha_html = _dasha_section(planet, pc, vim)
    remedy = PLANET_REMEDY.get(planet, "")
    remedy_block = ""
    if score < 55 or merged["caution_votes"] > merged["positive_votes"]:
        remedy_block = f"""
<div class="card amber">
  <h3>Strengthen {planet}</h3>
  <p>{_e(remedy)}</p>
  <p class="fine">Steady habit over a few months — not a one-day ritual.</p>
</div>"""

    today = datetime.now().strftime("%d %B %Y")
    retro = " · retrograde" if pl.get("retro") else ""
    nak = body.get("nakshatra", "")
    pada = body.get("pada", "")
    d9 = body.get("navamsha_sign") or (pc.get("divisional", {}).get("D9", {}) or {}).get(planet, "—")

    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{_e(planet)} — Planet Report — {_e(client_name)}</title>
<style>{client_css()}{_extra_css()}</style></head><body>
<div class="wrap">

  <div class="hero">
    <div class="planet-num">Planet report</div>
    <h1>{_e(area['title'])}</h1>
    <p style="margin:.3rem 0 0;opacity:.92">{_e(area['summary'])}</p>
    <div class="meta" style="margin-top:.6rem"><span>{_e(client_name)}</span>
      <span>Lagna: {_e(lagna)} {_e(lagna_deg)}</span>
      <span>{_e(today)}</span></div>
  </div>

  <div class="card">
    <h2>What {planet} signifies for you</h2>
    <ul class="areas">{areas_html}</ul>
    <p class="fine" style="margin-top:.6rem">Natural karaka themes: {_e(PLANET_KARAKA.get(planet, ''))}</p>
  </div>

  <div class="card">
    <h2>Overall verdict — across all methods</h2>
    <div class="gauge">
      <div><div class="gnum">{pct}%</div><div class="tally">confluence</div></div>
      <div><div class="strnum">{score}</div><div class="tally">strength score / 100</div></div>
      <div>
        <div style="font-size:1.05rem;font-weight:700">{_e(_strength_label(score))}</div>
        <div style="margin:.3rem 0"><span class="pill {conf_cls}">{_e(conf)} confidence</span></div>
        <div class="tally">{merged['positive_votes']} supportive · {merged['caution_votes']} caution ·
          {merged['neutral_votes']} neutral</div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>Natal placement</h2>
    <p><strong>House {occ_h}</strong> in <strong>{_e(pl['sign'])}</strong>
      ({_e(_dignity_plain(pl['dignity']))}{retro})</p>
    <p>Nakshatra: {_e(nak)} pada {_e(pada)} · Navāṁśa: {_e(d9)}</p>
    <p><strong>Rules:</strong> {_e(ruled_txt)}</p>
    <p><strong>Functional role:</strong> {_e(str(body.get('functional_status','')).replace('_',' '))}</p>
    <p><strong>Conjunctions:</strong> {_e(conj_txt)}</p>
    <p><strong>Jaimini role:</strong> {_e(jaimini_txt)}</p>
    <p class="fine">Strength factors: {'; '.join(_e(n) for n in score_notes)}</p>
  </div>

  <div class="card">
    <h2>Graha drishti — aspects</h2>
    <div class="aspect-grid">
      <div class="mini-card">
        <h4>{planet} aspects (outgoing)</h4>
        <ul class="areas">{out_html}</ul>
      </div>
      <div class="mini-card">
        <h4>Aspected by (incoming)</h4>
        <ul class="areas">{in_html}</ul>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>How each system reads {planet}</h2>
    <table class="tech">
      <tr><th>Technique</th><th>Verdict</th><th>Reading</th></tr>
      {rows}
    </table>
  </div>

  <div class="card">
    <h2>Daśā — when {planet} runs, what to expect</h2>
    {dasha_html}
  </div>
  {remedy_block}

</div></body></html>"""

    _label = _strength_label(score)
    _lead = (f"{_label} — {planet} sits in House {occ_h} in {pl['sign']} "
             f"({_dignity_plain(pl['dignity'])}); {merged['positive_votes']} of "
             f"{merged['total_techniques']} techniques read it supportively ({pct}%).")
    summary = {
        "planet": planet,
        "title": area["title"],
        "confluence_pct": pct,
        "strength_score": score,
        "confidence": conf,
        "house": occ_h,
        "sign": pl["sign"],
        "rules": ruled,
        "verdict_word": _label,
        "lead": _lead,
    }
    return finalize_report_html(doc, client_name), summary


def write_planet_confluence_report(
    pc: dict,
    planet: str,
    out_dir: Path,
    client_name: str = "Client",
    slug: str = "",
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    html_doc, _ = generate_planet_confluence_html(pc, planet, client_name)
    slug = slug or client_name.strip().replace(" ", "_")
    path = out_dir / f"Planet_{planet}_{slug}.html"
    path.write_text(html_doc, encoding="utf-8")
    return path


def write_all_planet_reports(
    pc: dict,
    out_dir: Path,
    client_name: str = "Client",
    planets: Optional[list[str]] = None,
) -> list[Path]:
    planets = planets or GRAHAS
    return [write_planet_confluence_report(pc, p, out_dir, client_name) for p in planets]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Per-planet multi-technique confluence report")
    ap.add_argument("--planet", default="", help="Single planet e.g. Sun")
    ap.add_argument("--planets", default="all", help="'all' or comma-separated list")
    ap.add_argument("--name", default="Sample")
    ap.add_argument("--dob", default="1990-01-15")
    ap.add_argument("--time", default="12:00")
    ap.add_argument("--place", default="New Delhi, India")
    ap.add_argument("--lat", type=float, default=28.6139)
    ap.add_argument("--lon", type=float, default=77.2090)
    ap.add_argument("--tz", type=float, default=5.5)
    ap.add_argument("-o", "--out", default="")
    args = ap.parse_args()

    if args.planet:
        plist = [args.planet]
    elif args.planets.strip().lower() == "all":
        plist = GRAHAS
    else:
        plist = [p.strip() for p in args.planets.split(",") if p.strip()]

    from astro_chart_bridge import compute_chart

    pc = compute_chart(
        client_name=args.name, dob=args.dob, birth_time=args.time,
        place=args.place, latitude=args.lat, longitude=args.lon, timezone=args.tz,
    )
    if not pc:
        raise SystemExit("Could not compute chart.")

    out_dir = Path(args.out) if args.out else (BASE_DIR / "reports" / args.name)
    for p in plist:
        if p not in GRAHAS:
            print(f"Skip unknown graha: {p}")
            continue
        path = write_planet_confluence_report(pc, p, out_dir, args.name)
        print(f"Wrote {path}")
