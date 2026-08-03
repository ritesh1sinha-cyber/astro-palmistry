#!/usr/bin/env python3
"""
vedic_jaimini_report.py — Deterministic Jaimini (Chara) life reading (NO LLM).

Replaces the Cursor Jaimini lane. Uses:
  • Chara karakas (7 soul roles) from ``astro_precompute`` (Chara column,
    matches the AstroSage Jaimini block).
  • Karakāṃśa = the navāṃśa sign of the Ātmakāraka (computed from its longitude).
  • Chara (sign-based) Mahā/Antar daśā from PyJHora (K.N. Rao method, workspace pyjhora/).

Book-backed engine (rules6 Goel, rules30/31 Boney): cara kārakas, Kārakāṃśa,
sign aspects, argala, ārudha/upapada, rājayoga scan, and Chara daśā timing with
kāraka-sign activation windows. Prediction-first prose; technical tables in appendix.

Fully offline and reproducible — no model, no network.
"""
from __future__ import annotations

import argparse
import html
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from astro_precompute import d9_sign, resolve_precompute
from chart_resolve import add_chart_source_args, chart_kwargs_from_args
from jaimini_chara_dasha import chara_dasha_from_precompute
from jaimini_books_merge import books_merged_body

BASE_DIR = Path(__file__).resolve().parent
GOLD = BASE_DIR / "reports" / "Vedic_Jaimini_Ritz_20260408.html"

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
ABBR = {"ARI": "Aries", "TAU": "Taurus", "GEM": "Gemini", "CAN": "Cancer",
        "LEO": "Leo", "VIR": "Virgo", "LIB": "Libra", "SCO": "Scorpio",
        "SAG": "Sagittarius", "CAP": "Capricorn", "AQU": "Aquarius", "PIS": "Pisces"}
SIGN_RE = "|".join(ABBR.keys())

ROLE_LABEL = {
    "Atmakarak": "Ātmakāraka (soul / self)",
    "Amatyakarak": "Amātyakāraka (career / mind)",
    "Bhratrukaraka": "Bhrātṛkāraka (siblings / drive)",
    "Matrukaraka": "Mātṛkāraka (mother / home)",
    "Putrakaraka": "Putrakāraka (children / creativity)",
    "Gnatikaraka": "Jñātikāraka (rivals / work)",
    "Darakaraka": "Dārakāraka (spouse / partner)",
}

# One-line "life chapter" keyword for each sign mahādaśā (master table).
SIGN_CHAPTER = {
    "Aries": "Competition, courage, new starts, initiative.",
    "Taurus": "Stability, money habits, art/music, patience.",
    "Gemini": "Learning to speak, sibling peers, early schooling tone.",
    "Cancer": "Home, mother-land, emotional security peak.",
    "Leo": "Visibility, children pride, creative risk.",
    "Virgo": "Workload, health routines, staff, systems upgrades.",
    "Libra": "Contracts, marriage renewal, aesthetic publics.",
    "Scorpio": "Joint assets, surgery/healing honesty, power tests.",
    "Sagittarius": "Publishing, travel, teachers, belief reset.",
    "Capricorn": "Title, duty, elder care, bone/sleep discipline.",
    "Aquarius": "Networks, ideals, tech/collective.",
    "Pisces": "Closure, compassion projects, liminal prep.",
}

# Everyday "mood" of a sign slice (antardaśā) for the narrative.
SIGN_MOOD = {
    "Aries": "fresh starts, competition, courage and initiative — good for asserting and beginning, with a watch on impulsiveness",
    "Taurus": "stability, money, comfort and patience — a stretch for consolidating resources and slowing down",
    "Gemini": "communication, learning, short trips and networking — curiosity and versatility rise",
    "Cancer": "home, mother, emotional roots and nurturing — tend the inner base and family",
    "Leo": "pride, visibility, children or creative projects and 'being seen' — good for stepping forward; the risk is ego clashes",
    "Virgo": "workload, health routines, fixing details and proving yourself — sort, edit and build skill, but protect rest",
    "Libra": "fairness, contracts, one-to-one deals and public image — choose peace without selling yourself short",
    "Scorpio": "shared money, trust, intimacy, endings that clear space, and health honesty — truth and consolidation over quick wins",
    "Sagittarius": "meaning, travel, study, teachers and the bigger-picture — expand and learn, but avoid over-promising",
    "Capricorn": "structure, duty, the career ladder, elders and slow solid gain — patience and reputation; less fun, more lasting",
    "Aquarius": "friends, teams, causes and future plans — alliances and collective goals come back loud",
    "Pisces": "closure, compassion, retreat, spirituality and foreign threads — wind down and prepare for the new",
}

SIGN_LORD = {"Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
             "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
             "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"}
MOVABLE = {"Aries", "Cancer", "Libra", "Capricorn"}
FIXED = {"Taurus", "Leo", "Scorpio", "Aquarius"}
DUAL = {"Gemini", "Virgo", "Sagittarius", "Pisces"}
NAT_MALEFIC = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
NAT_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
ROLE_SHORT = {
    "Atmakarak": "AK", "Amatyakarak": "AmK", "Bhratrukaraka": "BK", "Matrukaraka": "MK",
    "Putrakaraka": "PK", "Gnatikaraka": "GK", "Darakaraka": "DK",
}
KARAKA_PLAIN = {
    "Atmakarak": ("your inner self and life direction", "big personal choices land now"),
    "Amatyakarak": ("career and public name", "job moves, reputation, and income strategy heat up"),
    "Darakaraka": ("love and marriage", "partnership decisions feel harder to postpone"),
    "Putrakaraka": ("children and creative projects", "family, romance, or a creative baby-project asks for attention"),
    "Matrukaraka": ("home and mother", "property, parents, and emotional roots move"),
    "Bhratrukaraka": ("siblings, father, and mentors", "travel, teachers, or courage themes stir"),
    "Gnatikaraka": ("rivals and health friction", "office politics or stamina dips need handling"),
}
PERIOD_PLAIN = {
    "Aries": "Fresh starts and competition — push one goal, but do not pick fights you will regret.",
    "Taurus": "Money, comfort, and patience — save more than you spend; good for stabilising life.",
    "Gemini": "Talk, study, and short trips — network actively, but finish what you start.",
    "Cancer": "Home and family first — emotional security matters more than headlines.",
    "Leo": "Visibility and creativity — step forward, but watch ego clashes at work or in love.",
    "Virgo": "Workload and health routines — fix details, schedule rest, skip perfectionism spirals.",
    "Libra": "Contracts and one-to-one deals — fair peace beats polite silence in relationships.",
    "Scorpio": "Shared money and trust tests — honest talks on loans, taxes, or intimacy help.",
    "Sagittarius": "Travel, study, and bigger vision — expand, but read contracts twice.",
    "Capricorn": "Duty and career ladder — slow solid gain; guard sleep and joints.",
    "Aquarius": "Friends, teams, and causes — pick the right circle; say no to draining groups.",
    "Pisces": "Closure and rest — wind down, spiritual or foreign threads; avoid escapist spending.",
}
MAHA_PLAIN = {
    "Sagittarius": "A six-year stretch favouring travel, learning, teachers, and resetting what you believe.",
    "Aquarius": "Networks, tech, ideals, and collective goals — alliances matter.",
    "Capricorn": "Serious grown-up tone — duty, title, elders, and reputation.",
}
PLANET_REMEDY = {
    "Sun": "Sundays: sunlight walk, respect elders, keep vitamin D and routine check-ups sensible.",
    "Moon": "Mondays: calm evening, simple food, journal feelings, call family.",
    "Mars": "Tuesdays: exercise cleanly, channel anger into sport or work — not arguments.",
    "Mercury": "Wednesdays: clear emails, organise papers, study one useful skill.",
    "Jupiter": "Thursdays: modest charity or teaching; avoid over-promising or risky loans.",
    "Venus": "Fridays: art, kindness, beauty at home — nurture partner or close friends.",
    "Saturn": "Saturdays: discipline, sleep on time, help someone older; patience pays.",
    "Rahu": "Ground weekly: limit screens and speculation; stick to one practical goal.",
    "Ketu": "Quiet hour daily: meditation, finish an old task, let one draining habit go.",
}
AREA_LABEL = {
    1: "your body and personal confidence", 2: "money, family, and savings",
    3: "skills, courage, and short travel", 4: "home, roots, and emotional security",
    5: "children, romance, and creative projects", 6: "daily work and health habits",
    7: "marriage and committed partnership", 8: "shared finances and deep change",
    9: "luck, mentors, and long journeys", 10: "career and public reputation",
    11: "income, gains, and fulfilled goals", 12: "foreign ties, rest, and letting go",
}
AMK_CAREER = {
    "Sun": "leadership, government, medicine, or visible authority",
    "Moon": "public-facing care, food, hospitality, or mood-led trades",
    "Mars": "engineering, sport, surgery, defence, or competitive fields",
    "Mercury": "writing, IT, trade, analytics, teaching, and communication",
    "Jupiter": "teaching, law, finance, counselling, or advisory work",
    "Venus": "design, arts, hospitality, beauty, diplomacy, or luxury trades",
    "Saturn": "institutional roles, research, law, and the slow professional climb",
}
DK_PARTNER = {
    1: "independent and self-directed", 2: "family- and money-minded",
    3: "communicative and restless", 4: "home-loving and nurturing",
    5: "creative, romantic, and playful", 6: "service-minded and hardworking",
    7: "partnership-focused and fair-minded", 8: "intense, private, and transformative",
    9: "philosophical, worldly, and freedom-loving", 10: "ambitious and status-aware",
    11: "socially active, goal-driven, and independent", 12: "gentle, spiritual, or foreign-linked",
}


def _e(s) -> str:
    return html.escape(str(s))


def house_of(sign: str, lagna: str) -> int:
    return (SIGNS.index(sign) - SIGNS.index(lagna)) % 12 + 1


def _ord(n: int) -> str:
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th"))


def navamsa_sign(sign: str, deg_in_sign: float) -> str:
    lon = SIGNS.index(sign) * 30.0 + float(deg_in_sign)
    return SIGNS[int(lon / (30.0 / 9.0)) % 12]


def sign_at(sign: str, offset: int) -> str:
    return SIGNS[(SIGNS.index(sign) + offset - 1) % 12]


def sign_category(sign: str) -> str:
    if sign in MOVABLE:
        return "movable"
    if sign in FIXED:
        return "fixed"
    return "dual"


def sign_aspects_from(sign: str) -> set[str]:
    """Jaimini rāśi dṛṣṭi (rules6 Part B)."""
    cat = sign_category(sign)
    idx = SIGNS.index(sign)
    if cat == "movable":
        adj = SIGNS[(idx + 1) % 12]
        return {s for s in FIXED if s != adj}
    if cat == "fixed":
        adj = SIGNS[(idx - 1) % 12]
        return {s for s in MOVABLE if s != adj}
    return {s for s in DUAL if s != sign}


def mutual_sign_aspect(a: str, b: str) -> bool:
    return b in sign_aspects_from(a) and a in sign_aspects_from(b)


def arudha_pada(bhava_sign: str, lord_sign: str) -> str:
    """Full-sign ārudha counting (rules6 Part D)."""
    n = (SIGNS.index(lord_sign) - SIGNS.index(bhava_sign)) % 12 + 1
    pada_idx = (SIGNS.index(lord_sign) + n - 1) % 12
    pada = SIGNS[pada_idx]
    rel = (SIGNS.index(pada) - SIGNS.index(bhava_sign)) % 12 + 1
    if rel in (1, 7):
        pada = SIGNS[(pada_idx + 9) % 12]
    return pada


def _parse_date(raw: str, dob: date) -> Optional[date]:
    """Parse 'D/M/YY' (with stray spaces) anchoring the century to >= DOB."""
    m = re.match(r"\s*(\d{1,2})/\s*(\d{1,2})/\s*(\d{2,4})\s*$", raw)
    if not m:
        return None
    d, mo, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if yy < 100:
        yy = (dob.year // 100) * 100 + yy
        if yy < dob.year:
            yy += 100
    try:
        return date(yy, mo, d)
    except ValueError:
        return None


def parse_char_dasha(text: str, dob: date) -> tuple[list[dict], list[dict]]:
    """Return (maha[], antar[]) parsed from the AstroSage Char Daśā tables."""
    i = text.find("Char Maha Dasha")
    if i < 0:
        i = text.find("Char Dasha")
    end = text.find("Transit Today", i)
    if end < 0:
        end = i + 8000
    region = text[i:end]

    a_idx = region.find("Char Antardasha")
    maha_region = region[:a_idx] if a_idx > 0 else region
    antar_region = region[a_idx:] if a_idx > 0 else ""

    maha = []
    for sg, yrs, s, e in re.findall(
            rf"\b({SIGN_RE})\s+(\d+)\s+Years?\s+(\d{{1,2}}/\s*\d{{1,2}}/\s*\d{{2,4}})"
            rf"\s+(\d{{1,2}}/\s*\d{{1,2}}/\s*\d{{2,4}})", maha_region):
        ds, de = _parse_date(s, dob), _parse_date(e, dob)
        if ds and de:
            maha.append({"sign": ABBR[sg], "years": int(yrs), "start": ds, "end": de})

    antar = []
    for sg, s, e in re.findall(
            rf"\b({SIGN_RE})\s+(\d{{1,2}}/\s*\d{{1,2}}/\s*\d{{2,4}})"
            rf"\s+(\d{{1,2}}/\s*\d{{1,2}}/\s*\d{{2,4}})", antar_region):
        ds, de = _parse_date(s, dob), _parse_date(e, dob)
        if ds and de and (de - ds).days > 0:
            antar.append({"sign": ABBR[sg], "start": ds, "end": de})

    maha.sort(key=lambda r: r["start"])
    antar.sort(key=lambda r: r["start"])
    # Deduplicate antar (overlapping page reprints).
    seen, uniq = set(), []
    for r in antar:
        key = (r["sign"], r["start"], r["end"])
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    return maha, uniq


def _fmt(d: date) -> str:
    return d.strftime("%d %b %Y").lstrip('0')


def _fmtm(d: date) -> str:
    return d.strftime("%b %Y")


def _css() -> str:
    tags = (
        ".tag-good{display:inline-block;background:#e8f5e9;color:#2e7d32;font-size:.82rem;"
        "font-weight:600;padding:.15rem .45rem;border-radius:3px;margin-right:.35rem}"
        ".tag-warn{display:inline-block;background:#fff8e1;color:#e65100;font-size:.82rem;"
        "font-weight:600;padding:.15rem .45rem;border-radius:3px;margin-right:.35rem}"
        ".tag-hard{display:inline-block;background:#ffebee;color:#c62828;font-size:.82rem;"
        "font-weight:600;padding:.15rem .45rem;border-radius:3px;margin-right:.35rem}"
    )
    try:
        t = GOLD.read_text(encoding="utf-8")
        i, j = t.find("<style>"), t.find("</style>")
        if i != -1 and j != -1:
            return t[i + 7:j] + tags
    except Exception:
        pass
    return ("body{font-family:Georgia,serif;max-width:46rem;margin:auto;padding:1.5rem}"
            "table{width:100%;border-collapse:collapse}td,th{border:1px solid #ccc;padding:.45rem}"
            "tr.cur td{background:#e0f7fa}details.appendix{margin-top:1.5rem;font-size:.88rem}"
        ".callout-books{background:#e0f7fa;border-left:4px solid #006064;padding:.85rem 1rem;margin:1rem 0}"
        ".sec.good .pred{border-left:3px solid #2e7d32;padding-left:.65rem}"
        ".sec.amber .pred{border-left:3px solid #f9a825;padding-left:.65rem}" + tags)


class Jaimini:
    def __init__(self, pc: dict, dob: date, text: str = ""):
        self.pc = pc
        self.lagna = pc["meta"]["lagna_sign"]
        self.name = pc["meta"]["client"]
        self.karakas = {}
        for k in pc.get("cara_karakas", {}).get("karakas", []):
            sign = k.get("sign")
            self.karakas[k["role"]] = {
                "planet": k["planet"], "sign": sign,
                "house": house_of(sign, self.lagna) if sign in SIGNS else k.get("house"),
                "dignity": k.get("dignity", ""),
            }
        ak = self.karakas.get("Atmakarak", {})
        akp = ak.get("planet")
        jm = pc.get("jaimini", {})
        self.ak_navamsa = jm.get("karakamsa_sign") or (d9_sign(pc, akp) if akp else None)
        self.swamsa = jm.get("swamsa_sign")
        self.maha, self.antar = chara_dasha_from_precompute(pc)
        if not self.maha and text:
            self.maha, self.antar = parse_char_dasha(text, dob)
        self._planets_by_sign = {}
        for nm, v in pc["planets"].items():
            self._planets_by_sign.setdefault(v["sign"], []).append(nm)
        h12 = sign_at(self.lagna, 12)
        self.arudha_lagna = arudha_pada(self.lagna, self.pc["planets"][SIGN_LORD[self.lagna]]["sign"])
        self.upapada = arudha_pada(h12, self.pc["planets"][SIGN_LORD[h12]]["sign"])

    def role(self, r: str) -> dict:
        return self.karakas.get(r, {})

    def planets_in(self, sign: str) -> list[str]:
        return list(self._planets_by_sign.get(sign, []))

    def planet_house(self, planet: str) -> int:
        pl = self.pc["planets"].get(planet)
        return house_of(pl["sign"], self.lagna) if pl else 0

    def kl_house(self, sign: str) -> int:
        return house_of(sign, self.ak_navamsa) if self.ak_navamsa and sign in SIGNS else 0

    def karaka_roles_for_sign(self, sign: str) -> list[str]:
        return [ROLE_SHORT[r] for r, k in self.karakas.items() if k.get("sign") == sign]

    def current_maha(self) -> Optional[dict]:
        t = date.today()
        return next((m for m in self.maha if m["start"] <= t < m["end"]), None)

    def current_antar(self) -> Optional[dict]:
        t = date.today()
        return next((a for a in self.antar if a["start"] <= t < a["end"]), None)


# ───────────────────────── prediction engine (human NL) ───────────────────────


def _verdict_tag(kind: str) -> str:
    labels = {
        "good": ("Good phase", "tag-good"),
        "attention": ("Needs attention", "tag-warn"),
        "hard": ("Challenging — pace yourself", "tag-hard"),
    }
    text, cls = labels.get(kind, ("Mixed", "tag-warn"))
    return f'<span class="{cls}">{text}</span>'


def _period_verdict(jm: Jaimini, sign: str) -> str:
    h = house_of(sign, jm.lagna)
    tenants = jm.planets_in(sign)
    if jm.role("Gnatikaraka").get("sign") == sign:
        return "attention"
    if h in (6, 8, 12) or sum(1 for p in tenants if p in NAT_MALEFIC) >= 2:
        return "hard"
    if "Rahu" in tenants or "Saturn" in tenants:
        return "attention"
    if h in (5, 9, 10, 11) or jm.role("Atmakarak").get("dignity") == "exalted":
        return "good"
    return "attention"


def _karaka_burst(jm: Jaimini, sign: str) -> str:
    bits = []
    for role, (label, effect) in KARAKA_PLAIN.items():
        if jm.role(role).get("sign") == sign:
            bits.append(f"<strong>{label}</strong> — {effect}")
    return "; ".join(bits[:2])


def _period_plain(jm: Jaimini, sign: str, rich: bool = False) -> str:
    base = PERIOD_PLAIN.get(sign, "Life turns on mixed themes — stay steady and avoid rash moves.")
    extra = _karaka_burst(jm, sign)
    if extra:
        base = f"{base} <em>Also:</em> {extra}."
    if rich:
        tenants = jm.planets_in(sign)
        if tenants:
            base += f" Planets colouring this slice: <strong>{', '.join(tenants)}</strong>."
    return base


def _timing_plain(jm: Jaimini, role: str, limit: int = 2) -> str:
    sign = jm.role(role).get("sign")
    if not sign:
        return ""
    today = date.today()
    wins = []
    for a in jm.antar:
        if a["sign"] != sign:
            continue
        if a["end"] < today and not wins:
            continue
        if a["end"] >= today or a["start"] > today:
            wins.append(f"{_fmt(a['start'])} – {_fmt(a['end'])}")
        if len(wins) >= limit:
            break
    if not wins:
        return ""
    return f" <strong>Best windows:</strong> {', '.join(wins)}."


def _snapshot(jm: Jaimini) -> str:
    cur_m, cur_a = jm.current_maha(), jm.current_antar()
    ak = jm.role("Atmakarak")
    bits = ["<strong>Where you are now:</strong> This reading uses <strong>sign-based timing</strong> — like seasons of life, not planet periods."]
    if cur_m:
        mtxt = MAHA_PLAIN.get(cur_m["sign"], SIGN_CHAPTER.get(cur_m["sign"], "").rstrip("."))
        bits.append(
            f"Big chapter <strong>{cur_m['sign']}</strong> until <strong>{_fmt(cur_m['end'])}</strong> — {mtxt}"
        )
    if cur_a:
        v = _period_verdict(jm, cur_a["sign"])
        bits.append(
            f"Current slice <strong>{cur_a['sign']}</strong> until <strong>{_fmt(cur_a['end'])}</strong> "
            f"{_verdict_tag(v)}: {_period_plain(jm, cur_a['sign'])}"
        )
    if ak.get("planet"):
        dig = " — a strong inner anchor" if ak.get("dignity") == "exalted" else ""
        bits.append(
            f"Your core planet is <strong>{ak['planet']}</strong>{dig}; life lessons often circle "
            f"<strong>{AREA_LABEL.get(ak.get('house', 0), 'self-direction')}</strong>."
        )
    return " ".join(bits)


def _timeline(jm: Jaimini, n: int = 5) -> str:
    today = date.today()
    rows = []
    for a in jm.antar:
        if a["end"] < today:
            continue
        if len(rows) >= n:
            break
        label = "Now" if a["start"] <= today < a["end"] else ("Next" if len(rows) == 1 else "Later")
        cls = ' class="cur"' if label == "Now" else ""
        v = _period_verdict(jm, a["sign"])
        rows.append(
            f"<tr{cls}><td><strong>{label}</strong></td>"
            f"<td>{_fmt(a['start'])} – {_fmt(a['end'])}</td>"
            f"<td>{_verdict_tag(v)}</td>"
            f"<td>{_period_plain(jm, a['sign'])}</td></tr>"
        )
    if not rows:
        return "<p class='pred'>Timing dates not parsed from extract.</p>"
    return (
        "<table class='simple'><tr><th>When</th><th>Dates</th><th>Verdict</th><th>What it means for you</th></tr>"
        + "".join(rows) + "</table>"
    )


def _slice_block(jm: Jaimini, items: list[dict], wrap: str) -> str:
    if not items:
        return ""
    paras = []
    for a in items:
        v = _period_verdict(jm, a["sign"])
        paras.append(
            f"<p class='pred'>{_verdict_tag(v)} <strong>{_fmt(a['start'])} → {_fmt(a['end'])} "
            f"({a['sign']}):</strong> {_period_plain(jm, a['sign'], rich=True)}</p>"
        )
    return f"<div class='{wrap}'>" + "".join(paras) + "</div>"


def _recent_past(jm: Jaimini, n: int = 4) -> str:
    today = date.today()
    return _slice_block(jm, [a for a in jm.antar if a["end"] <= today][-n:], "callout-past")


def _future_paras(jm: Jaimini, n: int = 3) -> str:
    today = date.today()
    fut = [a for a in jm.antar if a["start"] > today][:n]
    body = _slice_block(jm, fut, "callout-future")
    nxt_m = next((m for m in jm.maha if m["start"] > today), None)
    if nxt_m:
        body += (
            f"<p class='pred'><strong>From {_fmt(nxt_m['start'])}:</strong> next long chapter "
            f"<strong>{nxt_m['sign']}</strong> — {MAHA_PLAIN.get(nxt_m['sign'], SIGN_CHAPTER.get(nxt_m['sign'], '').lower())}</p>"
        )
    return body


def _chart_strength(jm: Jaimini) -> list[str]:
    """Plain-language lifts and frictions."""
    lifts, frictions = [], []
    pairs = [
        ("Atmakarak", "Amatyakarak", "inner self and career pull together — good for purposeful work"),
        ("Atmakarak", "Putrakaraka", "creativity and life purpose align"),
        ("Atmakarak", "Darakaraka", "love and life direction intertwine"),
    ]
    for r1, r2, note in pairs:
        k1, k2 = jm.role(r1), jm.role(r2)
        p1, p2 = k1.get("planet"), k2.get("planet")
        s1, s2 = k1.get("sign"), k2.get("sign")
        if not p1 or not p2:
            continue
        if s1 == s2 or mutual_sign_aspect(s1, s2):
            lifts.append(f"{_verdict_tag('good')} <strong>{p1}</strong> and <strong>{p2}</strong> support each other — {note}.")
    ak = jm.role("Atmakarak")
    if ak.get("dignity") == "exalted":
        lifts.append(f"{_verdict_tag('good')} Your core planet <strong>{ak.get('planet')}</strong> is exalted — emotional steadiness and savings instinct are real assets.")
    if "Rahu" in jm.planets_in(sign_at(jm.lagna, 11)):
        frictions.append(f"{_verdict_tag('attention')} <strong>Rahu</strong> in your gains zone — ambition is high; avoid risky shortcuts and unclear group deals.")
    if jm.role("Gnatikaraka").get("house") in (3, 6):
        frictions.append(f"{_verdict_tag('attention')} Rival or health-friction planet in a busy house — guard boundaries at work.")
    return (lifts + frictions)[:4]


def _support_human(jm: Jaimini) -> str:
    """Argala translated to plain support/friction."""
    lagna = jm.lagna
    backers, mixed = set(), []
    for ah, vh in zip((4, 2, 11), (10, 12, 3)):
        a_sign, v_sign = sign_at(lagna, ah), sign_at(lagna, vh)
        a_pl, v_pl = jm.planets_in(a_sign), jm.planets_in(v_sign)
        if a_pl and not v_pl:
            backers.update(a_pl)
        elif a_pl and v_pl:
            mixed.append(f"help from <strong>{', '.join(a_pl)}</strong> can feel blocked by <strong>{', '.join(v_pl)}</strong>")
    parts = []
    if backers:
        parts.append(
            f"{_verdict_tag('good')} <strong>{', '.join(sorted(backers))}</strong> quietly backs your confidence — "
            f"initiative and gains get a tailwind."
        )
    if mixed:
        parts.append(f"{_verdict_tag('attention')} {'; '.join(mixed)} — results come, but with delay or competition.")
    if not parts:
        parts.append(f"{_verdict_tag('attention')} No single strong support pattern — outcomes depend on timing slices and your own discipline.")
    return " ".join(parts)


def _argala_note(jm: Jaimini) -> str:
    """rules6 Part F — argala on lagna sign."""
    lagna = jm.lagna
    argala_h = (4, 2, 11)
    virodha_h = (10, 12, 3)
    fav, blocked = [], []
    for ah, vh in zip(argala_h, virodha_h):
        a_sign, v_sign = sign_at(lagna, ah), sign_at(lagna, vh)
        a_pl = jm.planets_in(a_sign)
        v_pl = jm.planets_in(v_sign)
        if a_pl and not v_pl:
            fav.append(f"{', '.join(a_pl)} from {a_sign} ({_ord(ah)} from lagna)")
        elif a_pl and v_pl:
            blocked.append(f"{a_sign} argala by {', '.join(a_pl)} blocked by {', '.join(v_pl)} in {v_sign}")
    parts = []
    if fav:
        parts.append(f"Open argala on your lagna from { '; '.join(fav)} — support for fame, gains, or initiative.")
    if blocked:
        parts.append(f"Mixed argala: {'; '.join(blocked)} — results come, but with competition or delay.")
    if not parts:
        parts.append("No strong argala pattern on the lagna — outcomes depend more on kārakas and active Chara signs.")
    return " ".join(parts)


def _sign_aspect_note(jm: Jaimini) -> str:
    asp = sign_aspects_from(jm.lagna)
    hits = []
    for s in sorted(asp, key=SIGNS.index):
        pl = jm.planets_in(s)
        if pl:
            hits.append(f"<strong>{', '.join(pl)}</strong> in {s} ({_ord(house_of(s, jm.lagna))} house)")
    if not hits:
        return f"From {jm.lagna} lagna, Jaimini sign-aspects reach {', '.join(sorted(asp, key=SIGNS.index)[:4])}… but no planets sit in those signs."
    return f"From {jm.lagna} lagna, sign-aspects highlight: {'; '.join(hits[:4])}."


def _karakamsha_section(jm: Jaimini) -> str:
    if not jm.ak_navamsa:
        return ""
    ak = jm.role("Atmakarak")
    kl = jm.ak_navamsa
    v = "good" if ak.get("dignity") == "exalted" else "attention"
    parts = [
        f"<p class='pred'>{_verdict_tag(v)} Deep down you lead with <strong>{kl}</strong> energy — "
        f"you shine when you own <strong>{AREA_LABEL.get(jm.kl_house(kl), 'confidence')}</strong>, "
        f"even if public life looks different.</p>",
        f"<p class='pred'>Core planet <strong>{ak.get('planet')}</strong> ties career and inner life — "
        f"work feels best when it does not fight your emotional nature.</p>",
    ]
    h6k = sign_at(kl, 6)
    parts.append(
        f"<p class='pred'>{_verdict_tag('attention')} When <strong>{h6k}</strong> periods run, book a health check — "
        f"prevention beats crisis fixes.</p>"
    )
    return "".join(parts)


def _image_note(jm: Jaimini) -> str:
    al_mood = SIGN_MOOD.get(jm.arudha_lagna, "a distinct public face").split("—")[0].strip()
    up_mood = SIGN_MOOD.get(jm.upapada, "partnership themes").split("—")[0].strip()
    return (
        f"<p class='pred'>How others read you: <strong>{al_mood}</strong> ({jm.arudha_lagna} flavour). "
        f"Marriage scripts lean <strong>{up_mood}</strong> ({jm.upapada})."
        f"{_timing_plain(jm, 'Darakaraka')}</p>"
    )


def _career_section(jm: Jaimini) -> str:
    amk = jm.role("Amatyakarak")
    p = amk.get("planet", "")
    field = AMK_CAREER.get(p, "work that fits your wiring")
    v = "good" if amk.get("house") in (4, 5, 9, 10) else "attention"
    remedy = PLANET_REMEDY.get(p, "")
    ah = amk.get("house", 0)
    return (
        f"<p class='pred'>{_verdict_tag(v)} Career runs through <strong>{field}</strong> — "
        f"your work planet <strong>{p}</strong> sits in the <strong>{AREA_LABEL.get(ah, 'professional')}</strong> zone."
        f"{_timing_plain(jm, 'Amatyakarak')}</p>"
        + (f"<p class='pred'><strong>Remedy:</strong> {remedy}</p>" if remedy else "")
    )


def _marriage_section(jm: Jaimini) -> str:
    dk = jm.role("Darakaraka")
    p, h = dk.get("planet", ""), dk.get("house", 0)
    remedy = PLANET_REMEDY.get(p, "")
    seen, stress = set(), []
    for a in jm.antar:
        if a["start"] <= date.today():
            continue
        if _period_verdict(jm, a["sign"]) not in ("hard", "attention"):
            continue
        if a["sign"] in seen:
            continue
        seen.add(a["sign"])
        stress.append(a["sign"])
        if len(stress) >= 2:
            break
    stress_note = ""
    if stress:
        stress_note = (
            f"<p class='pred'>{_verdict_tag('attention')} Love needs extra care during "
            f"<strong>{', '.join(stress)}</strong> slices — duty and friction can crowd romance; "
            f"protect couple time anyway.</p>"
        )
    return (
        f"<p class='pred'>{_verdict_tag('good')} Partner type: <strong>{DK_PARTNER.get(h, 'warm and expressive')}</strong> — "
        f"your love planet <strong>{p}</strong> in the <strong>{AREA_LABEL.get(h, 'relationship')}</strong> zone."
        f"{_timing_plain(jm, 'Darakaraka')}</p>"
        + stress_note
        + (f"<p class='pred'><strong>Remedy:</strong> {remedy}</p>" if remedy else "")
    )


def _children_section(jm: Jaimini) -> str:
    pk = jm.role("Putrakaraka")
    p = pk.get("planet", "")
    return (
        f"<p class='pred'>{_verdict_tag('good')} Children, students, or creative babies-projects favour "
        f"<strong>home-centred visibility</strong> — what you nurture shows in family life, not only on a stage."
        f"{_timing_plain(jm, 'Putrakaraka')}</p>"
        + (f"<p class='pred'><strong>Remedy:</strong> {PLANET_REMEDY.get(p, '')}</p>" if p in PLANET_REMEDY else "")
    )


def _wealth_section(jm: Jaimini) -> str:
    ak = jm.role("Atmakarak")
    jup = jm.pc["planets"].get("Jupiter", {})
    jh = house_of(jup.get("sign", "Aries"), jm.lagna) if jup else 0
    lines = []
    if ak.get("dignity") == "exalted":
        lines.append(
            f"<p class='pred'>{_verdict_tag('good')} Money instinct is <strong>strong</strong> — "
            f"exalted <strong>{ak.get('planet')}</strong> favours saving, family wealth, and comfort.</p>"
        )
    elif ak.get("planet"):
        lines.append(
            f"<p class='pred'>{_verdict_tag('attention')} Wealth mood follows your core planet "
            f"<strong>{ak['planet']}</strong> through <strong>{AREA_LABEL.get(ak.get('house', 0), 'savings')}</strong> — "
            f"steady habits beat lucky swings.</p>"
        )
    if jh:
        lines.append(
            f"<p class='pred'>{_verdict_tag('attention')} Income also links to "
            f"<strong>{AREA_LABEL.get(jh, 'gains')}</strong> (Jupiter in the {_ord(jh)} sector) — "
            f"diversify skills, not gossip.</p>"
        )
    lines.append(
        f"<p class='pred'>{_verdict_tag('attention')} Public image ({jm.arudha_lagna}) can look richer than the bank account — keep books clean.</p>"
    )
    if ak.get("planet") in PLANET_REMEDY:
        lines.append(f"<p class='pred'><strong>Remedy:</strong> {PLANET_REMEDY[ak['planet']]}</p>")
    return "".join(lines)


def _health_section(jm: Jaimini) -> str:
    gk = jm.role("Gnatikaraka")
    p = gk.get("planet", "")
    lines = [
        f"<p class='pred'>{_verdict_tag('attention')} Friction planet <strong>{p}</strong> sits in a busy house — "
        f"stress shows as mental tiredness or sibling/office politics before the body breaks down."
        f"{_timing_plain(jm, 'Gnatikaraka')}</p>",
        f"<p class='pred'>{_verdict_tag('attention')} Guard routine when <strong>{sign_at(jm.lagna, 6)}</strong> "
        f"or <strong>{jm.ak_navamsa and sign_at(jm.ak_navamsa, 6) or 'your 6th-from-inner-sign'}</strong> slices run — "
        f"schedule sleep, meals, and check-ups like meetings.</p>",
    ]
    if p in PLANET_REMEDY:
        lines.append(f"<p class='pred'><strong>Remedy:</strong> {PLANET_REMEDY[p]}</p>")
    return "".join(lines) + "<p class='note'>Educational only — see a doctor for symptoms.</p>"


def _growth_section(jm: Jaimini) -> str:
    lines = [f"<p class='pred'>{lift}</p>" for lift in _chart_strength(jm)]
    bk, mk = jm.role("Bhratrukaraka"), jm.role("Matrukaraka")
    mk_h = mk.get("house", 0)
    bk_h = bk.get("house", 0)
    lines.append(
        f"<p class='pred'>{_verdict_tag('good')} Mother/home planet <strong>{mk.get('planet')}</strong> "
        f"in the {_ord(mk_h)} house colours home and family themes. "
        f"Father/mentor planet <strong>{bk.get('planet')}</strong> in the {_ord(bk_h)} house "
        f"steers travel, teachers, and dharma.</p>"
    )
    return "".join(lines[:4])


def _remedies_section(jm: Jaimini) -> str:
    seen, items = set(), []
    for role in ("Atmakarak", "Amatyakarak", "Darakaraka", "Gnatikaraka"):
        p = jm.role(role).get("planet")
        if p and p in PLANET_REMEDY and p not in seen:
            seen.add(p)
            items.append(f"<li><strong>{p}:</strong> {PLANET_REMEDY[p]}</li>")
    cur = jm.current_antar()
    if cur:
        for p in jm.planets_in(cur["sign"]):
            if p in PLANET_REMEDY and p not in seen:
                seen.add(p)
                items.append(f"<li><strong>{p}</strong> (active now): {PLANET_REMEDY[p]}</li>")
    items.append("<li>Keep agreements written — honest dealing protects luck more than rituals alone.</li>")
    items.append("<li>During heavy slices, trim one draining habit; finish one old pending task.</li>")
    return "<ul>" + "".join(items[:6]) + "</ul>"


def _appendix(jm: Jaimini) -> str:
    return f"""<details class='appendix'><summary>Jaimini chart facts (technical)</summary>
<h2>Chara kārakas</h2>{_karaka_table(jm)}
<h2>Chara mahādaśā</h2>{_maha_table(jm)}
<h2>Sign aspects from lagna</h2><p>{_sign_aspect_note(jm)}</p>
<h2>Argala on lagna</h2><p>{_argala_note(jm)}</p>
<h2>Ārudha / Upapada</h2><p>AL={jm.arudha_lagna}, UP={jm.upapada}</p>
</details>"""


# ───────────────────────────── render helpers (appendix) ────────────────────


def _karaka_table(jm: Jaimini) -> str:
    order = ["Atmakarak", "Amatyakarak", "Bhratrukaraka", "Matrukaraka",
             "Putrakaraka", "Gnatikaraka", "Darakaraka"]
    rows = []
    for r in order:
        k = jm.role(r)
        if not k:
            continue
        dig = f" ({k['dignity'].replace('_',' ')})" if k.get("dignity") in (
            "exalted", "debilitated", "own_sign", "moolatrikona") else ""
        rows.append(f"<tr><td>{ROLE_LABEL.get(r, r)}</td><td><strong>{k['planet']}</strong></td>"
                    f"<td>{k['sign']}{dig}, {_ord(k['house'])} house</td></tr>")
    return ("<table class='simple'><tr><th>Soul role</th><th>Planet</th>"
            "<th>Placement (from lagna)</th></tr>" + "".join(rows) + "</table>")


def _maha_table(jm: Jaimini) -> str:
    rows = []
    t = date.today()
    for m in jm.maha:
        cur = " style='background:#e0f7fa;'" if m["start"] <= t < m["end"] else ""
        rows.append(f"<tr{cur}><td>{m['sign']}</td><td>{m['years']}</td>"
                    f"<td>{_fmt(m['start'])} – {_fmt(m['end'])}</td>"
                    f"<td>{SIGN_CHAPTER.get(m['sign'],'')}</td></tr>")
    return ("<table class='simple'><tr><th>Sign chapter</th><th>Years</th><th>Dates</th>"
            "<th>Life keyword</th></tr>" + "".join(rows) + "</table>")


def render(jm: Jaimini, dob_disp: str, tob: str, place: str, books_block: str = "") -> str:
    nm = _e(jm.name)
    today = date.today()
    cur_m = jm.current_maha()
    cur_a = jm.current_antar()

    body = f"""
  <article class="card">
    <h1 style="color:var(--heading);">Your life reading — Jaimini</h1>
    <dl class="meta">
      <dt>Client</dt><dd>{nm}</dd>
      <dt>Born</dt><dd>{_e(dob_disp)}{(' · ' + _e(tob)) if tob else ''}{(' · ' + _e(place)) if place else ''}</dd>
      <dt>Lagna</dt><dd>{jm.lagna} · Kārakāṃśa {jm.ak_navamsa or '—'}{f' · Svāṃśa {jm.swamsa}' if getattr(jm, 'swamsa', None) else ''}</dd>
      <dt>Report date</dt><dd>{today.strftime('%d %B %Y').lstrip('0')}</dd>
    </dl>
    <p class="lead">This reading tracks <strong>which life season you are in</strong> — like chapters in a book.
    Each chapter has a plain verdict: <span class="tag-good">Good phase</span>,
    <span class="tag-warn">Needs attention</span>, or <span class="tag-hard">Challenging</span>.
    Goel + Gems + Jewels book depth follows the Chara timing sections.</p>

    <div class="callout">{_snapshot(jm)}</div>

    <h1>The chapter you are in (big picture)</h1>
    <p class="pred">{('The long <strong>' + cur_m['sign'] + '</strong> chapter runs <strong>' + _fmt(cur_m['start']) + ' – ' + _fmt(cur_m['end']) + '</strong>. ' + MAHA_PLAIN.get(cur_m['sign'], SIGN_CHAPTER.get(cur_m['sign'],'').rstrip('.'))) if cur_m else 'Chapter data unavailable from the extract.'}</p>
    <p class="pred">{_support_human(jm)}</p>

    <h1>Your timeline — what is coming</h1>
    <p class="pred">When a timing slice matches your love, job, or family sign, that theme gets louder — marriage windows for your partner sign, career windows for your work sign, and so on.</p>
    {_timeline(jm)}

    <h1>Recent past</h1>
    {_recent_past(jm) or '<p class="pred">No recent slices parsed.</p>'}

    <h1>Right now ({today.strftime('%d %B %Y').lstrip('0')})</h1>
    <p class="pred">{((_verdict_tag(_period_verdict(jm, cur_a['sign'])) + ' You are in the <strong>' + cur_a['sign'] + '</strong> slice until <strong>' + _fmt(cur_a['end']) + '</strong>. ' + _period_plain(jm, cur_a['sign'], rich=True)) if cur_a else 'Current slice not parsed.')}</p>

    <h1>Near future</h1>
    {_future_paras(jm) or '<p class="pred">No future slices parsed.</p>'}

    <h1>Who you are underneath</h1>
    {_karakamsha_section(jm) or '<p class="pred">Inner-sign data unavailable.</p>'}
    {_image_note(jm)}

    <h1>Job &amp; career</h1>
    {_career_section(jm)}

    <h1>Marriage &amp; partnership</h1>
    {_marriage_section(jm)}

    <h1>Children &amp; creativity</h1>
    {_children_section(jm)}

    <h1>Wealth &amp; joint resources</h1>
    {_wealth_section(jm)}

    <h1>Health &amp; energy</h1>
    {_health_section(jm)}

    <h1>Growth, mentors &amp; support</h1>
    {_growth_section(jm)}

    {books_block}

    <h1>Remedies — simple weekly habits</h1>
    {_remedies_section(jm)}

    <p class="note">Your Vimshottari or KP report may name different planets — that is normal.
    Use this report for <strong>Chara life-season timing</strong> plus <strong>karaka/Karakamsha structure</strong> from the books.</p>

    {_appendix(jm)}

    <p class="note">Educational astrology only. Verify important dates in your software. This report does not diagnose illness or predict death.</p>
  </article>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Jaimini + books reading — {nm}</title>
<style>{_css()}</style></head><body>{body}</body></html>"""


def generate_jaimini_html(
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
    text = (
        Path(extracted_path).read_text(encoding="utf-8", errors="ignore")
        if extracted_path and Path(extracted_path).exists()
        else ""
    )
    d = datetime.strptime(dob, "%Y-%m-%d").date()
    jm = Jaimini(pc, d, text=text)
    dob_disp = d.strftime("%d %B %Y").lstrip('0')
    books_block = books_merged_body(jm, pc)
    doc = render(jm, dob_disp, tob, place, books_block)
    summary = {
        "atmakaraka": jm.role("Atmakarak").get("planet"),
        "karakamsa": jm.ak_navamsa,
        "current_maha": (jm.current_maha() or {}).get("sign"),
        "current_antar": (jm.current_antar() or {}).get("sign"),
        "maha_count": len(jm.maha), "antar_count": len(jm.antar),
        "books_merged": True,
    }
    return doc, summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Deterministic Jaimini report (no LLM)")
    ap.add_argument("name")
    ap.add_argument("dob")
    ap.add_argument("extracted", nargs="?", default=None, help="Optional legacy AstroSage extract")
    add_chart_source_args(ap)
    ap.add_argument("--tob", default="", help="Birth time display label (optional)")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    kw = chart_kwargs_from_args(args)
    doc, summary = generate_jaimini_html(
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
    out = Path(args.out) if args.out else BASE_DIR / "reports" / f"Vedic_Jaimini_{args.name}_preview.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(f"AK={summary['atmakaraka']} Karakāṃśa={summary['karakamsa']} "
          f"maha={summary['current_maha']} antar={summary['current_antar']} "
          f"(parsed {summary['maha_count']} maha, {summary['antar_count']} antar)")
    print(f"written → {out}")


if __name__ == "__main__":
    main()
