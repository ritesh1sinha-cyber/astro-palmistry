#!/usr/bin/env python3
"""
vedic_blindchart_report.py — Deterministic Blind-Chart (Nadi) reading (NO LLM).

Replaces the Cursor BlindChart lane. Implements Dr. K. Guru Rajesh's Nadi blind-
chart method: each planet narrates a person or life domain, read from the chart
alone — Jupiter = the native, Sun = father, Moon = mother, Mercury = education,
Venus = wife/wealth, Saturn = profession. Timing uses **Jupiter progression
(1 sign / year)** and **Saturn progression (2.5 years / sign)** from their natal
signs.

Uncalibrated by design — descriptive and forward-oriented, not matched to a
claimed biography unless dated events are supplied.

Whole-sign houses are recomputed from sign + Lagna (precompute's stored house
field is unreliable for Saturn-ruled placements).

Fully offline and reproducible — no model, no network.
"""
from __future__ import annotations

import argparse
import html
import re
from datetime import datetime, date
from pathlib import Path

from astro_precompute import resolve_precompute
from chart_client import female_from_pc
from chart_resolve import add_chart_source_args, chart_kwargs_from_args

BASE_DIR = Path(__file__).resolve().parent
GOLD = BASE_DIR / "reports" / "Ritz_reprot" / "Vedic_BlindChart_Ritz_20260408.html"

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}
STRONG = ("exalted", "own_sign", "moolatrikona", "great_friend_sign")
WEAK = ("debilitated", "enemy_sign")
SIGN_BODY = {
    "Aries": "head and brain", "Taurus": "face, throat and neck",
    "Gemini": "shoulders, arms and lungs", "Cancer": "chest and stomach",
    "Leo": "heart and upper back", "Virgo": "intestines and digestion",
    "Libra": "kidneys and lower back", "Scorpio": "excretory and reproductive systems",
    "Sagittarius": "hips and thighs", "Capricorn": "knees, joints and bones",
    "Aquarius": "calves and ankles", "Pisces": "feet and lymphatic system",
}
DIGNITY_WORD = {"exalted": "exalted", "moolatrikona": "in moolatrikona", "own_sign": "in its own sign",
                "debilitated": "debilitated", "neutral_sign": "neutral", "friend_sign": "in a friend's sign",
                "enemy_sign": "in an enemy's sign", "great_friend_sign": "in a great friend's sign"}
PLANET_PERSON = {
    "Jupiter": "you (the native)", "Sun": "father", "Moon": "mother", "Mars": "sibling / drive",
    "Mercury": "intellect / education", "Venus": "spouse / wealth", "Saturn": "profession / karma",
    "Rahu": "ambition / the unconventional", "Ketu": "detachment / spirituality",
}
PLANET_REMEDY = {
    "Sun": "Sundays: sunlight walk, respect elders, keep routine check-ups sensible.",
    "Moon": "Mondays: calm evening, simple food, journal feelings, call family.",
    "Mars": "Tuesdays: exercise cleanly, channel anger into sport or work — not arguments.",
    "Mercury": "Wednesdays: clear emails, organise papers, study one useful skill.",
    "Jupiter": "Thursdays: modest charity or teaching; avoid risky loans.",
    "Venus": "Fridays: art, kindness, beauty at home — nurture close bonds.",
    "Saturn": "Saturdays: discipline, sleep on time, help someone older; patience pays.",
    "Rahu": "Ground weekly: limit screens and speculation; stick to one practical goal.",
    "Ketu": "Quiet hour daily: meditation, finish an old task, let one habit go.",
}
DOMAIN_LEAD = {
    "wealth": "Wealth in blind-chart method flows through Venus and the 11th-from-Saturn engine — progression shows when it opens.",
    "career": "Saturn defines professional identity; Jupiter and Saturn progressions mark when career themes intensify.",
    "marriage": "Partnership quality is read from Venus (male) or Jupiter (female) and Moon-from-spouse-karaka — progressions time the windows.",
    "children": "Ketu and the 5th-house story colour children; progression activations suggest when the theme stirs.",
    "health": "Jupiter sign, Mars+Rahu cluster, and Saturn progression bands flag body zones needing prevention.",
    "growth": "Jupiter chain and education Mercury shape inner growth — progression through Jupiter's sign recasts direction.",
}


def _e(s) -> str:
    return html.escape(str(s))


def _ord(n) -> str:
    n = int(n)
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th"))


def house_of(sign: str, lagna: str) -> int:
    return (SIGNS.index(sign) - SIGNS.index(lagna)) % 12 + 1


def sign_in_house(h: int, lagna: str) -> str:
    return SIGNS[(SIGNS.index(lagna) + h - 1) % 12]


def from_x(sign: str, base_sign: str) -> int:
    return (SIGNS.index(sign) - SIGNS.index(base_sign)) % 12 + 1


def _pd(iso: str) -> date:
    return datetime.strptime(iso[:10], "%Y-%m-%d").date()


def _dmy(d: date) -> str:
    return d.strftime("%d %b %Y").lstrip('0')


def _verdict_tag(kind: str) -> str:
    labels = {
        "good": ("Good phase", "tag-good"),
        "attention": ("Needs attention", "tag-warn"),
        "hard": ("Challenging", "tag-hard"),
    }
    text, cls = labels.get(kind, ("Mixed", "tag-warn"))
    return f'<span class="{cls}">{text}</span>'


def _detect_female(text: str) -> bool:
    return bool(re.search(r"\bSex\s+Female\b", text, re.I))


class Blind:
    def __init__(self, pc: dict, dob: date):
        self.pc = pc
        self.dob = dob
        self.lagna = pc["meta"]["lagna_sign"]
        self.name = pc["meta"]["client"]
        self.age = int(pc["meta"]["age"])
        self.planets = {}
        for nm, v in pc["planets"].items():
            self.planets[nm] = {"sign": v["sign"], "degree": v.get("degree_in_sign", 0.0),
                                "dignity": v.get("dignity", "neutral_sign"),
                                "house": house_of(v["sign"], self.lagna),
                                "retro": bool(v.get("retrograde", False))}
        self.by_sign: dict[str, list[str]] = {}
        for nm, v in self.planets.items():
            self.by_sign.setdefault(v["sign"], []).append(nm)
        self.jup_idx = SIGNS.index(self.planets["Jupiter"]["sign"])
        self.sat_idx = SIGNS.index(self.planets["Saturn"]["sign"])
        self.rules = {p: self._houses_ruled(p) for p in self.planets}
        self.houses = {}
        for h in range(1, 13):
            sign = sign_in_house(h, self.lagna)
            lord = SIGN_LORD[sign]
            self.houses[h] = {
                "sign": sign, "lord": lord,
                "tenants": [nm for nm, v in self.planets.items() if v["sign"] == sign],
            }

    def _houses_ruled(self, lord: str) -> list[int]:
        if lord not in self.planets or lord in ("Rahu", "Ketu"):
            return []
        return [n for n in range(1, 13) if SIGN_LORD[sign_in_house(n, self.lagna)] == lord]

    def lord_of_house(self, n: int) -> str:
        return SIGN_LORD[sign_in_house(n, self.lagna)]

    def pressure_sign(self) -> str:
        """Sign where Mars and Rahu cluster — friction trigger in this method."""
        mr = {self.planets["Mars"]["sign"], self.planets["Rahu"]["sign"]}
        return self.planets["Mars"]["sign"] if len(mr) == 1 else self.planets["Mars"]["sign"]

    def jup_prog(self, age: int) -> str:
        return SIGNS[(self.jup_idx + age) % 12]

    def sat_prog(self, age: int) -> str:
        return SIGNS[(self.sat_idx + int(age / 2.5)) % 12]

    def chain_ahead(self, planet: str, count: int = 3) -> list[tuple[str, list[str]]]:
        """Occupied signs ahead of a planet in zodiac order (excluding its own sign)."""
        base = SIGNS.index(self.planets[planet]["sign"])
        out = []
        for step in range(1, 12):
            sign = SIGNS[(base + step) % 12]
            occ = [p for p in self.by_sign.get(sign, []) if p not in ("Uranus", "Neptune", "Pluto")]
            if occ:
                out.append((sign, occ))
            if len(out) >= count:
                break
        return out

    def dig(self, p: str) -> str:
        return DIGNITY_WORD.get(self.planets[p]["dignity"], "neutral")


def _lord_verdict(b: Blind, p: str) -> str:
    pl = b.planets.get(p, {})
    dig = pl.get("dignity", "neutral_sign")
    occ = pl.get("house", 1)
    if dig in STRONG or occ in (1, 4, 5, 9, 10, 11):
        return "good"
    if dig in WEAK or occ in (6, 8, 12):
        return "hard"
    return "attention"


def _prog_verdict(b: Blind, jup_sign: str, sat_sign: str) -> str:
    pressure = b.pressure_sign()
    if sat_sign == pressure or jup_sign == pressure:
        return "hard"
    for sign in (jup_sign, sat_sign):
        occ = [p for p in b.by_sign.get(sign, []) if p in b.planets]
        if any(b.planets[p]["dignity"] in STRONG for p in occ):
            return "good"
        if any(b.planets[p]["dignity"] in WEAK for p in occ):
            return "hard"
        h = house_of(sign, b.lagna)
        if h in (6, 8, 12):
            return "attention"
    return "good"


def _prog_states(b: Blind, age_lo: int, age_hi: int) -> list[dict]:
    """Distinct Jupiter/Saturn progression states across an age band."""
    states, last = [], None
    for age in range(age_lo, age_hi + 1):
        js, ss = b.jup_prog(age), b.sat_prog(age)
        if (js, ss) == last:
            continue
        last = (js, ss)
        j_occ = [p for p in b.by_sign.get(js, []) if p in PLANET_PERSON]
        s_occ = [p for p in b.by_sign.get(ss, []) if p in PLANET_PERSON]
        jh, sh = house_of(js, b.lagna), house_of(ss, b.lagna)
        note = []
        if j_occ:
            note.append(f"Jupiter activates {'+'.join(j_occ)} in {js}")
        else:
            note.append(f"Jupiter in {js} ({_ord(jh)} from lagna)")
        if s_occ:
            note.append(f"Saturn presses on {'+'.join(s_occ)} in {ss}")
        else:
            note.append(f"Saturn in {ss} ({_ord(sh)})")
        states.append({
            "age": age, "year": b.dob.year + age,
            "jup": js, "sat": ss, "note": "; ".join(note) + ".",
            "verdict": _prog_verdict(b, js, ss),
        })
    return states


def _css() -> str:
    tags = (
        ".tag-good{display:inline-block;background:#e8f5e9;color:#2e7d32;font-size:.82rem;"
        "font-weight:600;padding:.15rem .45rem;border-radius:3px;margin-right:.35rem}"
        ".tag-warn{display:inline-block;background:#fff8e1;color:#e65100;font-size:.82rem;"
        "font-weight:600;padding:.15rem .45rem;border-radius:3px;margin-right:.35rem}"
        ".tag-hard{display:inline-block;background:#ffebee;color:#c62828;font-size:.82rem;"
        "font-weight:600;padding:.15rem .45rem;border-radius:3px;margin-right:.35rem}"
    )
    return (
        "body{font-family:Georgia,serif;max-width:46rem;margin:auto;padding:1.5rem;line-height:1.55}"
        ".card{background:#fff;border:1px solid #e0e0e0;border-radius:6px;padding:1.25rem 1.75rem}"
        ".meta{display:grid;grid-template-columns:auto 1fr;gap:.2rem .75rem;font-size:.92rem;margin:1rem 0}"
        ".meta dt{color:#555}.meta dd{margin:0}"
        ".lead{font-size:.95rem;color:#333;margin:1rem 0}"
        ".callout{background:#e0f7fa;border-left:4px solid #006064;padding:.85rem 1rem;margin:1rem 0}"
        ".callout-future{background:#e8f5e9;border-left:4px solid #2e7d32;padding:.85rem 1rem;margin:1rem 0}"
        ".callout-past{background:#fff8e1;border-left:4px solid #f9a825;padding:.85rem 1rem;margin:1rem 0}"
        ".pred{margin:.65rem 0}.note{font-size:.85rem;color:#555;margin-top:1rem}"
        "table.simple{width:100%;border-collapse:collapse;font-size:.9rem}"
        "table.simple th,table.simple td{border:1px solid #e0e0e0;padding:.45rem}"
        "tr.cur td{background:#e0f7fa}details.appendix{margin-top:1.5rem;font-size:.88rem}"
        "h1{font-size:1.25rem;color:#006064;margin-top:1.5rem}ul li,ol li{margin:.35rem 0}" + tags
    )


def _chain_phrase(b: Blind, chain: list) -> str:
    parts = []
    for sign, occ in chain:
        parts.append("+".join(occ))
    return " → ".join(parts)


def _prog_timeline(b: Blind, age_lo: int | None = None, age_hi: int | None = None,
                   label_now: bool = True) -> str:
    """Jupiter/Saturn progression bands with verdict column."""
    lo = age_lo if age_lo is not None else b.age
    hi = age_hi if age_hi is not None else b.age + 8
    rows = []
    for st in _prog_states(b, lo, hi):
        lbl = ""
        if label_now and st["age"] == b.age:
            lbl = ' class="cur"'
            when = "<strong>Now</strong>"
        elif st["age"] == b.age + 1:
            when = "<strong>Next</strong>"
        else:
            when = f"~{st['year']}"
        rows.append(
            f"<tr{lbl}><td>{when} (age {st['age']})</td>"
            f"<td>J: {st['jup']} · S: {st['sat']}</td>"
            f"<td>{_verdict_tag(st['verdict'])}</td>"
            f"<td>{_e(st['note'])}</td></tr>"
        )
    if not rows:
        return "<p class='pred'>Progression states not computed.</p>"
    return (
        "<table class='simple'><tr><th>When</th><th>Progression</th><th>Verdict</th><th>What activates</th></tr>"
        + "".join(rows) + "</table>"
    )


def _snapshot(b: Blind) -> str:
    cur_jup, cur_sat = b.jup_prog(b.age), b.sat_prog(b.age)
    v = _prog_verdict(b, cur_jup, cur_sat)
    jup = b.planets["Jupiter"]
    chain = _chain_phrase(b, b.chain_ahead("Jupiter", 3))
    return (
        "<strong>Where you are now:</strong> Blind-chart method reads <strong>Jupiter as you</strong> "
        f"and times life through <strong>Jupiter (1 yr/sign)</strong> and <strong>Saturn (2.5 yr/sign)</strong> "
        f"progressions. Your Jupiter sits in <strong>{jup['sign']}</strong> ({b.dig('Jupiter')}) — "
        f"chain ahead: <strong>{chain}</strong>. "
        f"At age <strong>{b.age}</strong>: Jupiter at <strong>{cur_jup}</strong>, Saturn at <strong>{cur_sat}</strong> "
        f"{_verdict_tag(v)}."
    )


def _domain_lead(b: Blind, domain: str) -> str:
    cur_jup, cur_sat = b.jup_prog(b.age), b.sat_prog(b.age)
    tag = _verdict_tag(_prog_verdict(b, cur_jup, cur_sat))
    wins = []
    for st in _prog_states(b, b.age, b.age + 8):
        if st["age"] <= b.age:
            continue
        if domain == "career" and (st["sat"] == b.planets["Saturn"]["sign"] or "Saturn" in st["note"]):
            wins.append(f"~{st['year']} ({st['sat'][:3]})")
        elif domain == "wealth" and (st["sat"] == b.planets["Venus"]["sign"] or "Venus" in st["note"]):
            wins.append(f"~{st['year']}")
        elif domain == "marriage" and (st["jup"] == b.planets["Venus"]["sign"] or "Venus" in st["note"]):
            wins.append(f"~{st['year']}")
        elif domain == "health" and st["sat"] == b.pressure_sign():
            wins.append(f"~{st['year']} (pressure sign)")
        if len(wins) >= 2:
            break
    lead = f"<p class='pred'>{tag} {DOMAIN_LEAD[domain]}"
    if wins:
        lead += f" Worth watching: {', '.join(wins)}."
    lead += "</p>"
    return lead


def _remedies_section(b: Blind) -> str:
    lagna_lord = SIGN_LORD[b.lagna]
    items = []
    for p in ("Jupiter", "Saturn", lagna_lord, "Venus"):
        if p in PLANET_REMEDY:
            items.append(f"<li><strong>{p}</strong>: {PLANET_REMEDY[p]}</li>")
    items.append(
        "<li>During Saturn progression through your Mars+Rahu sign, document agreements and protect health routines.</li>"
    )
    items.append("<li>Supply five dated milestones to calibrate progression timing — uncorrected bands carry ±1 year.</li>")
    return "<ul>" + "".join(items[:6]) + "</ul>"


def _appendix(b: Blind) -> str:
    d1_rows = "".join(
        f"<tr><td>{p}</td><td>{v['sign']}</td><td>{v['house']}</td>"
        f"<td>{b.dig(p)}{' · retro' if v.get('retro') else ''}</td></tr>"
        for p, v in b.planets.items() if p in PLANET_PERSON
    )
    prog_rows = "".join(
        f"<tr><td>~{st['year']} (age {st['age']})</td><td>J: {st['jup']} · S: {st['sat']}</td>"
        f"<td>{_verdict_tag(st['verdict'])}</td></tr>"
        for st in _prog_states(b, b.age, b.age + 15)
    )
    return f"""<details class='appendix'><summary>Chart facts (technical)</summary>
<h2>Blind-chart progression reference</h2>
<p class='fine'>Jupiter natal: {b.planets['Jupiter']['sign']} (1 sign/year from age 0) · Saturn natal: {b.planets['Saturn']['sign']} (2.5 yr/sign) · Pressure sign (Mars+Rahu): {b.pressure_sign()} · Chain ahead of Jupiter: {_chain_phrase(b, b.chain_ahead('Jupiter', 3))}</p>
<h2>Progression bands (next 15 years)</h2>
<table class='simple'><tr><th>When</th><th>Jupiter · Saturn</th><th>Verdict</th></tr>{prog_rows}</table>
<h2>D1 placements (karaka map)</h2>
<table class='simple'><tr><th>Planet</th><th>Sign</th><th>House</th><th>Notes</th></tr>{d1_rows}</table>
</details>"""


def _section_personality(b: Blind, chain_txt: str, mars_rahu_sign: str) -> str:
    jup = b.planets["Jupiter"]
    P = b.planets
    ven_note = (
        " Venus is <strong>exalted</strong> — grace, earning power, and refined skill are durable themes."
        if P["Venus"]["dignity"] == "exalted" else ""
    )
    return (
        f"<p class='pred'>{_verdict_tag(_lord_verdict(b, 'Jupiter'))} Your <strong>Jupiter — the planet that "
        f"represents <em>you</em></strong> — sits in <strong>{jup['sign']}, {b.dig('Jupiter')}</strong> in the "
        f"{_ord(jup['house'])} house. Chain ahead: <strong>{chain_txt}</strong>.{ven_note}</p>"
        f"<p class='pred'><strong>Father (Sun in {P['Sun']['sign']}, {b.dig('Sun')}):</strong> principled, "
        f"institution-facing authority. <strong>Mother (Moon in {P['Moon']['sign']}, {b.dig('Moon')}):</strong> "
        f"practical, service-oriented care — verify before treating as literal biography.</p>"
        f"<p class='pred'>The <strong>Mars+Rahu</strong> cluster in {mars_rahu_sign} is the recurring "
        f"<strong>pressure trigger</strong> — when progressions activate {mars_rahu_sign}, intensity and "
        f"competition rise.</p>"
    )


def _section_education(b: Blind) -> str:
    P = b.planets
    merc_note = (
        "is in debilitation but joined by strong Venus — intuitive intelligence outweighs textbook struggle."
        if P["Mercury"]["dignity"] == "debilitated" and "Venus" in b.by_sign.get(P["Mercury"]["sign"], [])
        else "shapes an intelligent, communicative learner."
    )
    return (
        f"<p class='pred'>{_verdict_tag(_lord_verdict(b, 'Mercury'))} <strong>Mercury in {P['Mercury']['sign']} "
        f"({b.dig('Mercury')})</strong> {merc_note} Study fields lean creative, financial, or communicative "
        f"rather than purely physical sciences.</p>"
    )


def _section_career(b: Blind, elev_sign: str, income_planets: list) -> str:
    P = b.planets["Saturn"]
    retro = " (retrograde)" if P["retro"] else ""
    income = (
        f"{', '.join(income_planets)} in {elev_sign} (11th from Saturn)"
        if income_planets else f"the 11th from Saturn ({elev_sign})"
    )
    return (
        f"<p class='pred'><strong>Saturn in {P['sign']}{retro}</strong> defines professional identity: depth, "
        f"investigation, research, financial analysis, or work beneath the surface. Your strength is finding "
        f"what others cannot see.</p>"
        f"<p class='pred'><strong>Income engine:</strong> {income} shows earnings through care for quality and "
        f"serving people well.</p>"
    )


def _section_marriage(b: Blind, female: bool, moon_from_spouse: int, mars_rahu_sign: str) -> str:
    P = b.planets
    karaka = "Jupiter" if female else "Venus"
    k = P[karaka]
    if female:
        partner_line = (
            f"<strong>Jupiter {b.dig('Jupiter')} in {k['sign']}</strong> colours your spouse: wise, "
            f"expansive, teacher-like when dignified."
            if k["dignity"] in STRONG else
            f"<strong>Jupiter in {k['sign']}</strong> describes a spouse who grows through patience and lived experience."
        )
        moon_base = P["Jupiter"]["sign"]
    else:
        partner_line = (
            f"<strong>Venus {b.dig('Venus')} in {k['sign']}</strong> — the strongest spouse placement: educated, "
            f"intelligent, emotionally capable."
            if k["dignity"] == "exalted" else
            f"<strong>Venus {b.dig('Venus')} in {k['sign']}</strong> describes a graceful, relationship-oriented partner."
        )
        moon_base = P["Venus"]["sign"]
    moon_from = from_x(P["Moon"]["sign"], moon_base)
    return (
        f"<p class='pred'>{partner_line}</p>"
        f"<p class='pred'><strong>Moon in the {_ord(moon_from)} from {karaka}</strong> ({P['Moon']['sign']}) "
        f"tells character: practical, analytical, care through service.</p>"
        f"<p class='pred'><strong>Mars+Rahu in the {_ord(from_x(mars_rahu_sign, moon_base))} from {karaka}</strong> "
        f"classically tests partnership ease — heat or financial friction in early-union years in case literature.</p>"
    )


def _section_children(b: Blind) -> str:
    k = b.planets["Ketu"]
    return (
        f"<p class='pred'><strong>Ketu in {k['sign']}</strong> ({_ord(k['house'])} house) invites detachment, "
        f"surprise, or unconventional timing in the child story — calibrate with dated events.</p>"
    )


def _section_wealth(b: Blind, mars_rahu_sign: str, cur_sat: str) -> str:
    ven = b.planets["Venus"]
    ven_line = (
        "The planet of happiness is exalted — long-term financial struggle is not the base promise."
        if ven["dignity"] == "exalted" else "Wealth arrives with grace and quality when conduct stays clean."
    )
    sat_note = (
        " (structured-wealth window — discipline over luck)"
        if cur_sat == ven["sign"] else ""
    )
    return (
        f"<p class='pred'><strong>Venus {b.dig('Venus')} in {ven['sign']}</strong> is the strongest wealth indicator. "
        f"{ven_line} Earlier Mars+Rahu in the {_ord(from_x(mars_rahu_sign, ven['sign']))} from Venus marks "
        f"possible turbulence phases.</p>"
        f"<p class='pred'><strong>Now (age {b.age}):</strong> Saturn progressing through {cur_sat}{sat_note}.</p>"
    )


def _section_health(b: Blind, mars_rahu_sign: str) -> str:
    jup = b.planets["Jupiter"]
    sat = b.planets["Saturn"]
    sat_r = " (retrograde)" if sat["retro"] else ""
    return (
        f"<p class='pred'><strong>Jupiter in {jup['sign']}:</strong> {SIGN_BODY[jup['sign']]} — proactive care "
        f"from the early forties converts susceptibility to strength.</p>"
        f"<p class='pred'><strong>Mars+Rahu in {mars_rahu_sign}:</strong> {SIGN_BODY[mars_rahu_sign]} — "
        f"accident-prone or high-inflammation sensitivity when progressions re-touch this sign.</p>"
        f"<p class='pred'><strong>Saturn in {sat['sign']}{sat_r}:</strong> {SIGN_BODY[sat['sign']]} — chronic, "
        f"slow-building issues respond best to preventive maintenance.</p>"
        f"<p class='pred'><strong>Mercury {b.dig('Mercury')}:</strong> stress shows as overthinking or sleep "
        f"disruption — creative output is an effective outlet.</p>"
    )


def _recent_past_prog(b: Blind) -> str:
    past = [st for st in _prog_states(b, max(0, b.age - 6), b.age - 1) if st["age"] < b.age][-3:]
    if not past:
        return ""
    bits = []
    for st in past:
        bits.append(
            f"<p class='pred'>{_verdict_tag(st['verdict'])} <strong>Age {st['age']} (~{st['year']}):</strong> "
            f"J {st['jup']} · S {st['sat']} — {st['note']}</p>"
        )
    return "<div class='callout-past'>" + "".join(bits) + "</div>"


def _near_future_prog(b: Blind) -> str:
    fut = [st for st in _prog_states(b, b.age + 1, b.age + 8) if st["age"] > b.age][:3]
    if not fut:
        return ""
    bits = []
    for st in fut:
        bits.append(
            f"<p class='pred'>{_verdict_tag(st['verdict'])} <strong>Age {st['age']} (~{st['year']}):</strong> "
            f"J {st['jup']} · S {st['sat']} — {st['note']}</p>"
        )
    pressure = b.pressure_sign()
    bits.append(
        f"<p class='pred'><strong>Watch:</strong> when Saturn progression reaches <strong>{pressure}</strong> "
        f"(Mars+Rahu sign) — higher-friction band; document agreements and protect health.</p>"
    )
    return "<div class='callout-future'>" + "".join(bits) + "</div>"


def render(b: Blind, dob_disp: str, tob: str, place: str, female: bool = False) -> str:
    nm = _e(b.name)
    today = date.today()
    P = b.planets
    chain_txt = _chain_phrase(b, b.chain_ahead("Jupiter", 3))
    jup = P["Jupiter"]
    cur_jup, cur_sat = b.jup_prog(b.age), b.sat_prog(b.age)
    cur_jup_occ = [p for p in b.by_sign.get(cur_jup, []) if p in PLANET_PERSON]
    cur_sat_occ = [p for p in b.by_sign.get(cur_sat, []) if p in PLANET_PERSON]
    mars_rahu_sign = b.pressure_sign()
    elev_sign = SIGNS[(b.sat_idx + 10) % 12]
    income_planets = [p for p in b.by_sign.get(elev_sign, []) if p in PLANET_PERSON]
    gender = "female" if female else "male"
    moon_from_spouse = from_x(P["Moon"]["sign"], P["Jupiter"]["sign"] if female else P["Venus"]["sign"])

    right_now = (
        f"{_verdict_tag(_prog_verdict(b, cur_jup, cur_sat))} At age <strong>{b.age}</strong>: "
        f"<strong>Saturn</strong> progressing through <strong>{cur_sat}</strong>"
        f"{(' (' + '+'.join(cur_sat_occ) + ')') if cur_sat_occ else ''} — "
        f"{'creative–financial emphasis' if cur_sat == P['Venus']['sign'] else 'restructuring'} window. "
        f"<strong>Jupiter</strong> at <strong>{cur_jup}</strong>"
        f"{(' (lagna — identity review)' if cur_jup == b.lagna else (' (' + '+'.join(cur_jup_occ) + ')' if cur_jup_occ else ' (' + _ord(house_of(cur_jup, b.lagna)) + ' from lagna)'))}."
    )

    body = f"""
  <article class="card">
    <h1 style="color:#006064;">Your life reading — Blind Chart (Nāḍī)</h1>
    <dl class="meta">
      <dt>Client</dt><dd>{nm} · {gender}</dd>
      <dt>Born</dt><dd>{_e(dob_disp)}{(' · ' + _e(tob)) if tob else ''}{(' · ' + _e(place)) if place else ''}</dd>
      <dt>Lagna</dt><dd>{b.lagna} · age {b.age}</dd>
      <dt>Calibration</dt><dd><strong>None supplied</strong> — progression bands are exploratory (±1 year)</dd>
      <dt>Report date</dt><dd>{today.strftime('%d %B %Y').lstrip('0')}</dd>
    </dl>
    <p class="lead">Dr. K. Guru Rajesh's blind-chart method reads <strong>each planet as a person or life domain</strong>
    from the D1 chart alone — no biography assumed. Timing uses <strong>Jupiter progression (1 yr/sign)</strong>
    and <strong>Saturn progression (2.5 yr/sign)</strong> from natal positions. Each window has a plain verdict:
    <span class="tag-good">Good phase</span>, <span class="tag-warn">Needs attention</span>, or
    <span class="tag-hard">Challenging</span>. All life-area readings stay on the <strong>D1 karaka map</strong>
    and progression bands — no divisional charts used here.
    For reflection only — not medical, legal, or investment advice.</p>

    <div class="callout">{_snapshot(b)}</div>

    <h1>The chapter you are in (big picture)</h1>
    <p class="pred">Your natal <strong>Jupiter in {jup['sign']}</strong> sets the life-design spine — the zodiac chain
    ahead runs <strong>{chain_txt}</strong>. Progressions from age <strong>{b.age}</strong> forward intensify whichever
    sign Jupiter and Saturn currently occupy.</p>
    <p class="pred">{_verdict_tag(_lord_verdict(b, 'Jupiter'))} Core temperament is read from Jupiter's sign, dignity,
    and house — not from biography you supplied.</p>

    <h1>Your timeline — what is coming</h1>
    <p class="pred">Each row is a Jupiter/Saturn progression band — when a band touches Mars+Rahu or exalted Venus,
    that theme gets louder.</p>
    {_prog_timeline(b)}

    <h1>Recent past</h1>
    {_recent_past_prog(b) or '<p class="pred">No distinct past progression transitions in the look-back window.</p>'}

    <h1>Right now ({today.strftime('%d %B %Y').lstrip('0')})</h1>
    <p class="pred">{right_now}</p>

    <h1>Near future</h1>
    {_near_future_prog(b) or '<p class="pred">No future progression transitions parsed.</p>'}

    <h1>Who you are underneath</h1>
    {_section_personality(b, chain_txt, mars_rahu_sign)}

    <h1>Job &amp; career</h1>
    {_domain_lead(b, 'career')}
    {_section_career(b, elev_sign, income_planets)}

    <h1>Marriage &amp; partnership</h1>
    {_domain_lead(b, 'marriage')}
    {_section_marriage(b, female, moon_from_spouse, mars_rahu_sign)}

    <h1>Children &amp; creativity</h1>
    {_domain_lead(b, 'children')}
    {_section_children(b)}

    <h1>Wealth &amp; joint resources</h1>
    {_domain_lead(b, 'wealth')}
    {_section_wealth(b, mars_rahu_sign, cur_sat)}

    <h1>Health &amp; energy</h1>
    {_domain_lead(b, 'health')}
    {_section_health(b, mars_rahu_sign)}
    <p class="note">Educational only — see a doctor for symptoms.</p>

    <h1>Growth, mentors &amp; support</h1>
    {_domain_lead(b, 'growth')}
    {_section_education(b)}
    <p class="pred">Ahead of Jupiter the chain <strong>{chain_txt}</strong> reads as elder influences and mentors —
    your real birth order is <strong>not assumed</strong>.</p>

    <h1>Remedies — simple weekly habits</h1>
    {_remedies_section(b)}

    <h1>Next decade — five headline themes</h1>
    <ol>
      <li><strong>Current window (age {b.age}):</strong> Saturn on {cur_sat} rewards disciplined financial and professional action.</li>
      <li><strong>Jupiter at {cur_jup}:</strong> identity recasting chapter — use it for deliberate direction change.</li>
      <li><strong>Watch Saturn into {mars_rahu_sign}:</strong> higher-friction band when progression reaches the Mars+Rahu sign.</li>
      <li><strong>Health anchors:</strong> {jup['sign']} ({SIGN_BODY[jup['sign']]}) and {P['Saturn']['sign']} ({SIGN_BODY[P['Saturn']['sign']]}) need preventive routines.</li>
      <li><strong>Venus {b.dig('Venus')}:</strong> relationships, wealth, and refinement are durable engines when conduct stays clean.</li>
    </ol>

    <p class="note">Your Vimshottari, BNN, or KP report may name different timings — that is normal.
    Blind-chart timing is <strong>progression-based</strong> (Jupiter/Saturn signs), not Vimshottari antardasa.
    Supply five dated milestones to calibrate before treating forward windows as locked.</p>

    {_appendix(b)}

    <p class="note">Educational astrology only. Source: Dr. K. Guru Rajesh blind-chart / Nāḍī method (rules17).
    Deterministic rule engine — no LLM. Does not diagnose illness or predict death.</p>
  </article>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Blind Chart reading — {nm}</title>
<style>{_css()}</style></head><body>{body}</body></html>"""


def generate_blindchart_html(
    client_name: str,
    dob: str,
    *,
    extracted_path: str | None = None,
    tob: str = "",
    place: str = "",
    precomputed_path: str | None = None,
    birth_time: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone: float | None = None,
    gender: int | None = None,
) -> tuple[str, dict]:
    pc = resolve_precompute(
        client_name, dob,
        extracted_path=extracted_path,
        precomputed_path=precomputed_path,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        place_name=place,
        gender=gender,
    )
    d = datetime.strptime(dob, "%Y-%m-%d").date()
    b = Blind(pc, d)
    female = female_from_pc(pc)
    doc = render(b, d.strftime("%d %B %Y").lstrip('0'), tob, place, female)
    summary = {
        "lagna": b.lagna,
        "jupiter_sign": b.planets["Jupiter"]["sign"],
        "jup_prog_now": b.jup_prog(b.age),
        "sat_prog_now": b.sat_prog(b.age),
        "chain": [s for s, _ in b.chain_ahead("Jupiter", 3)],
        "female": female,
    }
    return doc, summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Deterministic Blind-Chart (Nadi) report (no LLM)")
    ap.add_argument("name")
    ap.add_argument("dob")
    ap.add_argument("extracted", nargs="?", default=None, help="Optional legacy AstroSage extract")
    add_chart_source_args(ap)
    ap.add_argument("--tob", default="")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    kw = chart_kwargs_from_args(args)
    doc, summary = generate_blindchart_html(
        args.name, args.dob,
        extracted_path=args.extracted,
        tob=args.tob, place=args.place or kw.get("place_name", ""),
        precomputed_path=kw.get("precomputed_path"),
        birth_time=kw.get("birth_time"),
        latitude=kw.get("latitude"),
        longitude=kw.get("longitude"),
        timezone=kw.get("timezone"),
        gender=kw.get("gender"),
    )
    out = Path(args.out) if args.out else BASE_DIR / "reports" / f"Vedic_BlindChart_{args.name}_preview.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(f"jupiter={summary['jupiter_sign']} jup_prog_now={summary['jup_prog_now']} "
          f"sat_prog_now={summary['sat_prog_now']} chain={summary['chain']}")
    print(f"written → {out}")


if __name__ == "__main__":
    main()
