#!/usr/bin/env python3
"""
vedic_pillar_report.py — Deterministic "Pillar of Life" report (NO LLM).

Replaces the Cursor Pillar lane. Implements Marc Boney's *The Pillar of Life*
method (rules27.md): evaluate the Lagna and the Lagna Lord — the central pillar
of the chart — through a fixed checklist, dispositor chain, special yogas, a net
strength score, and (the prediction core) a dasha-timed map of when the Lagna
Lord, its dispositor and the marakas fire.

Most structural data (seven-factor checklist, neecha bhanga, dispositor chain,
special yogas, functional status) is taken from astro_precompute. Whole-sign
houses and navamsa signs are recomputed here deterministically (precompute's
navamsa is unreliable; its Saturn house can be wrong). Dasha dates come from the
Vimshottari grid; marakas / Mrityu-Bhaga flags come from the longevity precompute.

Prediction-first: snapshot → timeline → pillar verdict → wealth/job/marriage/
children/health/growth in plain English. Technical tables live in a collapsed appendix.

Fully offline and reproducible — no model, no network.
"""
from __future__ import annotations

import argparse
import html
from datetime import date, datetime
from pathlib import Path

from astro_precompute import resolve_precompute
from chart_resolve import add_chart_source_args, chart_kwargs_from_args

BASE_DIR = Path(__file__).resolve().parent
GOLD = BASE_DIR / "reports" / "Vedic_Pillar_Ritz_20260408.html"

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = {"Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
             "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
             "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
             "Pisces": "Jupiter"}
HOUSE_THEME = {1: "self & body", 2: "wealth & family", 3: "courage & communication",
               4: "home & mother", 5: "children & creativity", 6: "work, service & health",
               7: "marriage & partnership", 8: "transformation & longevity", 9: "fortune & dharma",
               10: "career & status", 11: "gains & networks", 12: "foreign & expense"}
AREA_LABEL = {
    1: "your body and personal confidence", 2: "money, family, and savings",
    3: "skills, courage, and short travel", 4: "home, roots, and emotional security",
    5: "children, romance, and creative projects", 6: "daily work and health habits",
    7: "marriage and committed partnership", 8: "shared finances and deep change",
    9: "luck, mentors, and long journeys", 10: "career and public reputation",
    11: "income, gains, and fulfilled goals", 12: "foreign ties, rest, and letting go",
}
LAGNA_TRAIT = {
    "Aries": "bold, direct, and quick to act",
    "Taurus": "steady, comfort-loving, and patient with money",
    "Gemini": "curious, verbal, and mentally restless",
    "Cancer": "feeling-led, protective, and home-centred",
    "Leo": "warm, proud, and wanting to be seen",
    "Virgo": "analytical, service-minded, and detail-focused",
    "Libra": "relational, fair-minded, and drawn to harmony",
    "Scorpio": "intense, private, and built for deep change",
    "Sagittarius": "hopeful, restless, and belief-driven",
    "Capricorn": "serious, disciplined, and playing the long game",
    "Aquarius": "independent, unconventional, and future-minded",
    "Pisces": "imaginative, compassionate, and porous to mood",
}
LL_CAREER = {
    "Sun": "leadership, government, medicine, or any role where you must be visibly credible",
    "Moon": "public-facing work, care, food, hospitality, or trades that read the mood of people",
    "Mars": "engineering, sport, surgery, defence, real estate, or any field that rewards courage",
    "Mercury": "writing, IT, trade, analytics, teaching, and communication-heavy work",
    "Jupiter": "teaching, law, finance, counselling, academia, or advisory roles",
    "Venus": "design, arts, hospitality, beauty, diplomacy, or work that blends comfort with craft",
    "Saturn": "institutional roles, research, labour-intensive fields, law, and the slow climb",
    "Rahu": "technology, media, foreign trade, aviation, and unconventional careers",
    "Ketu": "research, healing, niche technology, and behind-the-scenes or spiritual work",
}
BODY_ZONE = {
    "Aries": "head, blood pressure, and nervous tension", "Taurus": "throat, neck, and thyroid",
    "Gemini": "lungs, shoulders, and breath", "Cancer": "stomach, chest, and digestion",
    "Leo": "heart, spine, and circulation", "Virgo": "gut, intestines, and assimilation",
    "Libra": "kidneys, lower back, and fluid balance", "Scorpio": "reproductive and eliminatory systems",
    "Sagittarius": "hips, thighs, and liver", "Capricorn": "knees, bones, joints, and skin",
    "Aquarius": "calves, ankles, and circulation", "Pisces": "feet, lymph, and immunity",
}
LORD_PERIOD = {
    "Sun": "Visibility and authority rise — stand up for yourself, but do not burn bridges for ego.",
    "Moon": "Feelings and family matter more than headlines — nurture what stabilises you first.",
    "Mars": "Energy and drive spike — act boldly, but pace yourself so you do not overheat.",
    "Mercury": "A busy mind season — deals, study, writing, and short trips pick up.",
    "Jupiter": "A gentler, luck-leaning stretch — mentors, fairness, and long-view choices help.",
    "Venus": "Comfort and connection rise — love, art, and enjoying what you earn feel natural.",
    "Saturn": "Slow, serious work — rewards come through discipline, not shortcuts.",
    "Rahu": "Restless ambition — foreign links, tech, and unconventional moves tempt you.",
    "Ketu": "A quieter, inward spell — research, letting go, and fewer material attachments.",
}
DIGNITY_WORD = {"exalted": "exalted", "moolatrikona": "in moolatrikona", "own_sign": "in own sign",
                "debilitated": "debilitated", "neutral_sign": "neutral", "friend_sign": "in a friend's sign",
                "enemy_sign": "in an enemy's sign", "great_friend_sign": "in a great friend's sign"}
NAT_MALEFIC = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
NAT_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
KENDRA = {1, 4, 7, 10}
TRIKONA = {1, 5, 9}
DUSTHANA = {6, 8, 12}
STRONG = ("exalted", "own_sign", "moolatrikona", "great_friend_sign")
WEAK = ("debilitated", "enemy_sign")
# special-aspect targets (houses ahead a planet aspects, besides the 7th)
SPECIAL_ASPECT = {"Mars": [4, 8], "Jupiter": [5, 9], "Saturn": [3, 10]}


def _e(s) -> str:
    return html.escape(str(s))


def _ord(n) -> str:
    n = int(n)
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th"))


def house_of(sign: str, lagna: str) -> int:
    return (SIGNS.index(sign) - SIGNS.index(lagna)) % 12 + 1


def navamsa_sign(sign: str, deg: float) -> str:
    """Continuous-zodiac navamsa (deterministically correct)."""
    idx = SIGNS.index(sign)
    within = int(deg / (30.0 / 9.0))  # 0..8
    return SIGNS[(idx * 9 + within) % 12]


def navamsa_dignity(planet: str, nav_sign: str) -> str:
    if SIGN_LORD[nav_sign] == planet:
        return "own_sign"
    # cheap friend/enemy not modelled; report own vs other
    return "other"


def _dms(deg: float) -> str:
    d = int(deg)
    m = int((deg - d) * 60)
    s = int(round((((deg - d) * 60) - m) * 60))
    if s == 60:
        s, m = 0, m + 1
    return f"{d}°{m:02d}'{s:02d}\""


def _pd(iso: str) -> date:
    return datetime.strptime(iso[:10], "%Y-%m-%d").date()


def _moy(d: date) -> str:
    return d.strftime("%b %Y")


class Pillar:
    def __init__(self, pc: dict):
        self.pc = pc
        self.lagna = pc["meta"]["lagna_sign"]
        self.lagna_idx = SIGNS.index(self.lagna)
        self.name = pc["meta"]["client"]
        self.lagna_lord = SIGN_LORD[self.lagna]
        self.func = pc["pillar"].get("functional_status", {})
        self.planets = {}
        for nm, v in pc["planets"].items():
            sign = v["sign"]
            deg = v.get("degree_in_sign", 0.0)
            self.planets[nm] = {
                "sign": sign, "degree": deg, "nakshatra": v.get("nakshatra", ""),
                "pada": v.get("pada", ""), "dignity": v.get("dignity", "neutral_sign"),
                "house": house_of(sign, self.lagna), "navamsa": navamsa_sign(sign, deg),
                "retro": bool(v.get("retrograde", False)),
            }
        self.rules = {p: [] for p in self.planets}
        self.houses = {}
        for h in range(1, 13):
            sign = SIGNS[(self.lagna_idx + h - 1) % 12]
            lord = SIGN_LORD[sign]
            self.houses[h] = {"sign": sign, "lord": lord,
                              "tenants": [nm for nm, v in self.planets.items() if v["sign"] == sign]}
            if lord in self.rules:
                self.rules[lord].append(h)
        self.ll = self.planets[self.lagna_lord]
        # precompute structural blocks
        self.seven = pc["pillar"]["seven_factors"]
        self.nb = pc["pillar"]["neecha_bhanga"]
        self.chain = pc["pillar"]["dispositor_chain"]
        self.yogas = pc["pillar"]["special_yogas"]
        # vimshottari + maraka
        self.seq = pc["vimshottari"]["sequence"]
        self.cur_md = pc["vimshottari"]["current_md"]
        self.antars = pc["vimshottari"]["current_md_antardashas"]
        lg = pc.get("longevity", {})
        self.maraka_lords = {lg.get("maraka_1", {}).get("lord"), lg.get("maraka_2", {}).get("lord")}
        self.maraka_lords.discard(None)
        self.mb_critical = {x["planet"] for x in lg.get("critical_mb", []) if x.get("critical")}
        self.dispositor = SIGN_LORD[self.ll["sign"]]

    # ── influences on the lagna lord ──────────────────────────────────────
    def aspecting(self, target_house: int) -> list[str]:
        out = []
        for nm, v in self.planets.items():
            h = v["house"]
            targets = [(h + 6 - 1) % 12 + 1]  # 7th aspect
            for off in SPECIAL_ASPECT.get(nm, []):
                targets.append((h + off - 1 - 1) % 12 + 1)
            if target_house in targets:
                out.append(nm)
        return out

    def conjunct(self) -> list[str]:
        return [nm for nm, v in self.planets.items()
                if v["sign"] == self.ll["sign"] and nm != self.lagna_lord]

    def hemming(self) -> dict:
        h = self.ll["house"]
        prev_h = (h - 2) % 12 + 1
        next_h = h % 12 + 1
        prev_sign = self.houses[prev_h]["sign"]
        next_sign = self.houses[next_h]["sign"]
        prev_p = [nm for nm, v in self.planets.items() if v["sign"] == prev_sign and nm in NAT_MALEFIC]
        next_p = [nm for nm, v in self.planets.items() if v["sign"] == next_sign and nm in NAT_MALEFIC]
        return {"papa": bool(prev_p and next_p), "prev": prev_p, "next": next_p,
                "prev_sign": prev_sign, "next_sign": next_sign}

    # ── scoring ───────────────────────────────────────────────────────────
    def score(self) -> dict:
        s = 50
        dig = self.ll["dignity"]
        if dig in STRONG:
            s += 18
        elif dig == "debilitated":
            s -= 18
        elif dig == "enemy_sign":
            s -= 8
        h = self.ll["house"]
        if h in KENDRA:
            s += 14
        elif h in TRIKONA:
            s += 12
        elif h in DUSTHANA:
            s -= 12
        if self.nb.get("neecha_bhanga_present"):
            s += 12
        # benefic conjunctions / aspects
        good = [p for p in self.conjunct() + self.aspecting(h) if p in NAT_BENEFIC]
        s += min(12, 4 * len(set(good)))
        bad = [p for p in self.conjunct() + self.aspecting(h) if p in NAT_MALEFIC]
        s -= min(10, 4 * len(set(bad)))
        hem = self.hemming()
        if hem["papa"]:
            s -= 8
        # dispositor strength
        disp = self.planets[self.dispositor]
        if disp["dignity"] in STRONG and disp["house"] not in DUSTHANA:
            s += 8
        elif disp["dignity"] == "debilitated" or disp["house"] in DUSTHANA:
            s -= 8
        # navamsa
        if self.ll["navamsa"] == self.ll["sign"] or SIGN_LORD[self.ll["navamsa"]] == self.lagna_lord:
            s += 6
        overall = max(8, min(95, s))
        # domain scores
        career = max(10, min(95, overall + (12 if h == 10 else 0)
                             + (10 if any(p in NAT_BENEFIC for p in self.conjunct()) else 0)))
        health = max(10, min(95, overall - (12 if dig == "debilitated" else 0)
                             - (8 if hem["papa"] else 0)
                             - (6 if any(p in self.maraka_lords for p in [self.dispositor]) else 0)))
        # chain
        chain_strong = sum(1 for c in self.chain if c.get("dignity") in STRONG)
        chain = max(10, min(95, 25 + 18 * chain_strong))
        return {"overall": overall, "career": career, "health": health, "chain": chain}

    def verdict_word(self, pct: int) -> str:
        if pct >= 75:
            return "STRONG"
        if pct >= 60:
            return "MODERATE–STRONG"
        if pct >= 45:
            return "MODERATE"
        if pct >= 30:
            return "MODERATE–WEAK"
        return "WEAK"


# ───────────────────────── prediction engine (NL) ─────────────────────────────


def _fmt_iso(iso: str) -> str:
    if not iso:
        return "—"
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%d %b %Y").lstrip('0')
    except Exception:
        return str(iso)


def _house_class_word(h: int) -> str:
    if h in KENDRA:
        return "a powerful angular house"
    if h in TRIKONA:
        return "an auspicious trine house"
    if h in DUSTHANA:
        return "a challenging house"
    return "a steady house"


def _dignity_plain(dig: str) -> str:
    return DIGNITY_WORD.get(dig, dig.replace("_", " "))


def _pillar_roles(p: Pillar, lord: str) -> list[str]:
    roles = []
    if lord == p.lagna_lord:
        roles.append("lagna lord")
    if lord == p.dispositor:
        roles.append("dispositor")
    if lord in p.maraka_lords:
        roles.append("maraka")
    if lord in p.mb_critical:
        roles.append("Mrityu-Bhaga sensitive")
    return roles


def _period_forecast(p: Pillar, lord: str) -> str:
    roles = _pillar_roles(p, lord)
    occ_h = p.planets[lord]["house"]
    area = AREA_LABEL.get(occ_h, HOUSE_THEME.get(occ_h, "life themes"))
    base = LORD_PERIOD.get(lord, f"Life turns toward {area}.")
    if "lagna lord" in roles:
        return f"{base} Your lagna lord is active — identity, courage, and personal direction move to the front."
    if "dispositor" in roles:
        return f"{base} The planet steering your lagna lord runs — choices feel more consequential than usual."
    if "maraka" in roles or "Mrityu-Bhaga" in " ".join(roles):
        return f"{base} A health-watch window — guard sleep, meals, and stress; schedule preventive checks."
    if occ_h in KENDRA | TRIKONA:
        return f"{base} Themes around {area} are easier to push forward now."
    return base


def _verdict_plain(p: Pillar, sc: dict) -> str:
    v = p.verdict_word(sc["overall"]).replace("–", "-").lower()
    h = p.ll["house"]
    dig = _dignity_plain(p.ll["dignity"])
    nb = ""
    if p.nb.get("neecha_bhanga_present"):
        nb = f" Its debility is cancelled ({p.nb.get('verdict', 'neecha bhanga')}), which softens the weakness."
    lead = "career" if sc["career"] >= sc["health"] else "health and stamina"
    return (
        f"Your central pillar reads as <strong>{v}</strong> ({sc['overall']}%). "
        f"{p.lagna_lord} as lagna lord sits in the <strong>{_ord(h)} house</strong> "
        f"({_house_class_word(h)}) — {dig} in {p.ll['sign']}.{nb} "
        f"The chart is workable for real-world success, with <strong>{lead}</strong> leading the story."
    )


def _snapshot(p: Pillar) -> str:
    cur = next((a for a in p.antars if a.get("status") == "current"), {})
    ad = cur.get("ad_lord", "")
    trait = LAGNA_TRAIT.get(p.lagna, "distinctive and purposeful")
    bits = [
        f"<strong>Where you are now:</strong> You come across as <strong>{trait}</strong>. "
        f"The larger chapter is <strong>{p.cur_md.get('md_lord', '')}</strong> until {_fmt_iso(p.cur_md.get('end', ''))}."
    ]
    if ad:
        bits.append(
            f" Through {_fmt_iso(cur.get('end', ''))}, <strong>{ad}</strong> colours daily life — "
            f"{_period_forecast(p, ad)}"
        )
    bits.append(
        f" Your life pillar is anchored in <strong>{AREA_LABEL.get(p.ll['house'], 'personal direction')}</strong>."
    )
    return " ".join(bits)


def _timeline(p: Pillar, n_future: int = 5) -> str:
    rows = []
    seq = [a for a in p.antars if a.get("status") in ("current", "future")]
    for i, a in enumerate(seq[:n_future]):
        label = "Now" if a["status"] == "current" else ("Next" if i == 1 else "Later")
        cls = ' class="cur"' if label == "Now" else ""
        rows.append(
            f"<tr{cls}><td><strong>{label}</strong></td>"
            f"<td>{_fmt_iso(a['start'])} – {_fmt_iso(a['end'])}</td>"
            f"<td>{a['ad_lord']}</td>"
            f"<td>{_period_forecast(p, a['ad_lord'])}</td></tr>"
        )
    if not rows:
        return "<p class='pred'>Dasha dates not fully parsed from extract.</p>"
    return (
        "<table class='time'><tr><th>When</th><th>Dates</th><th>Period lord</th><th>What to expect</th></tr>"
        + "".join(rows) + "</table>"
    )


def _pillar_strength(p: Pillar, sc: dict) -> str:
    fav, adv = [], []
    conj = p.conjunct()
    asp = p.aspecting(p.ll["house"])
    hem = p.hemming()
    for c in conj:
        if c in NAT_BENEFIC:
            fav.append(f"{c} sits with your lagna lord and lends support")
        else:
            adv.append(f"{c} conjunct your lagna lord adds pressure")
    for a in asp:
        (fav if a in NAT_BENEFIC else adv).append(f"{a} aspects your lagna lord from the {_ord(p.planets[a]['house'])} house")
    if hem["papa"]:
        adv.append("malefic hemming (Papa-Katari) flanks the lagna lord")
    disp = p.planets[p.dispositor]
    if disp["dignity"] in STRONG and disp["house"] not in DUSTHANA:
        fav.append(f"{p.dispositor} as dispositor is well placed and steadies results")
    elif disp["dignity"] == "debilitated" or disp["house"] in DUSTHANA:
        adv.append(f"{p.dispositor} as dispositor is weak and can delay delivery")
    if p.nb.get("neecha_bhanga_present"):
        fav.append("debility cancellation (neecha bhanga) protects the lagna lord")
    if SIGN_LORD[p.ll["navamsa"]] == p.lagna_lord:
        fav.append("strong navamsa placement backs the lagna lord")
    lagna_clear = any("protected" in f.get("result", "").lower() for f in p.seven)
    if lagna_clear:
        fav.append("the lagna itself is not directly afflicted")
    parts = [f"<p class='pred'>{_verdict_plain(p, sc)}</p>"]
    if fav:
        parts.append(f"<p class='pred'>What helps: {'; '.join(fav[:3])}.</p>")
    if adv:
        parts.append(f"<p class='pred'>What to watch: {'; '.join(adv[:3])}.</p>")
    if p.yogas:
        parts.append(f"<p class='pred'>Special lift: {p.yogas[0]}.</p>")
    return "".join(parts)


def _ll_maha_window(p: Pillar) -> str:
    dob_y = int(p.pc["meta"]["dob"][:4])
    for m in p.seq:
        if m["md_lord"] == p.lagna_lord:
            s, e = _pd(m["start"]), _pd(m["end"])
            if e.year > date.today().year:
                return f"<p class='pred'><strong>Lagna-lord major chapter:</strong> {_moy(s)} – {_moy(e)} " \
                       f"(ages {s.year - dob_y}–{e.year - dob_y}) — identity and life direction become primary.</p>"
    # future antar windows where LL activates
    bits = []
    md = p.cur_md.get("md_lord", "")
    for a in p.antars:
        if a.get("status") not in ("current", "future"):
            continue
        if a["ad_lord"] == p.lagna_lord:
            bits.append(f"<strong>{md}–{p.lagna_lord}</strong> ({_fmt_iso(a['start'])} – {_fmt_iso(a['end'])})")
        if len(bits) >= 2:
            break
    if bits:
        return f"<p class='pred'><strong>When your pillar fires:</strong> {', '.join(bits)}.</p>"
    return ""


def _career_section(p: Pillar) -> str:
    h = p.ll["house"]
    field = LL_CAREER.get(p.lagna_lord, "work that fits your natural wiring")
    lines = [
        f"<p class='pred'>Your public life grows through <strong>{field}</strong>. "
        f"Because the lagna lord sits in the <strong>{_ord(h)} house</strong>, "
        f"{AREA_LABEL.get(h, HOUSE_THEME[h])} are woven into how the world knows you — not a side story.</p>",
    ]
    if h == 10:
        lines.append("<p class='pred'>Career and reputation are structurally central. Push one visible goal at a time; "
                     "office politics drain more energy than they are worth.</p>")
    elif h == 5:
        lines.append("<p class='pred'>Creative leadership, teaching, performing, or guiding young minds suit you "
                     "better than anonymous back-office work. Recognition often follows a project you care about personally.</p>")
    elif h == 6:
        lines.append("<p class='pred'>Service, problem-solving, and health-related fields are natural lanes. "
                     "Success comes through competence and reliability, not shortcuts.</p>")
    for a in p.antars:
        if a.get("status") not in ("current", "future"):
            continue
        lord = a["ad_lord"]
        if p.planets[lord]["house"] in (10, 6) or lord == p.lagna_lord:
            tag = "Now" if a["status"] == "current" else "Career window"
            lines.append(f"<p class='pred'><strong>{tag}:</strong> {_fmt_iso(a['start'])} – {_fmt_iso(a['end'])} — "
                         f"{_period_forecast(p, lord)}</p>")
            break
    return "".join(lines)


def _wealth_section(p: Pillar) -> str:
    h2 = p.houses[2]["lord"]
    h11 = p.houses[11]["lord"]
    lines = [
        f"<p class='pred'>Money flows when <strong>{AREA_LABEL.get(p.planets[h2]['house'], 'savings')}</strong> "
        f"and <strong>{AREA_LABEL.get(p.planets[h11]['house'], 'gains')}</strong> are active. "
        f"Income tends to arrive in waves — bank the good months instead of spending freely.</p>",
    ]
    if p.ll["house"] == 2:
        lines.append("<p class='pred'>Wealth and family values are built into your life pillar — "
                     "financial stability grows when home and earning stay aligned.</p>")
    elif p.ll["house"] == 11:
        lines.append("<p class='pred'>Networks and fulfilled ambitions expand income over time — "
                     "one strong alliance or client can matter more than many small gigs.</p>")
    return "".join(lines)


def _marriage_section(p: Pillar) -> str:
    lord7 = p.houses[7]["lord"]
    h7 = p.planets[lord7]["house"]
    ven = p.planets["Venus"]
    lines = [
        f"<p class='pred'>Partnership opens through <strong>{AREA_LABEL.get(h7, 'relationship themes')}</strong>. "
        + ("Bonds deepen after tests — honest talk beats polite silence."
           if h7 in DUSTHANA else
           "Lasting love is possible when both people show up on ordinary days, not only grand gestures.")
        + "</p>",
    ]
    if "Venus" in p.conjunct():
        lines.append("<p class='pred'>Venus with your lagna lord colours love with warmth and creativity — "
                     "romance, art, and enjoying life together matter as much as duty.</p>")
    if p.ll["house"] in (5, 7):
        lines.append("<p class='pred'>Love and partnership are not background themes for you — "
                     "they are part of how you express who you are.</p>")
    for a in p.antars:
        if a.get("status") not in ("current", "future"):
            continue
        lord = a["ad_lord"]
        if lord in (lord7, "Venus") or p.planets[lord]["house"] in (5, 7):
            lines.append(f"<p class='pred'><strong>Relationship timing:</strong> {_fmt_iso(a['start'])} – "
                           f"{_fmt_iso(a['end'])} — partnership decisions feel easier to make or deepen.</p>")
            break
    return "".join(lines)


def _children_section(p: Pillar) -> str:
    h = p.ll["house"]
    lord5 = p.houses[5]["lord"]
    lines = []
    if h == 5:
        lines.append("<p class='pred'>Children, romance, and creative projects are <strong>central to your life pillar</strong>, "
                     "not side interests. What you birth — literally or creatively — defines much of your story.</p>")
    else:
        lines.append(f"<p class='pred'>Children and creative joy tie to <strong>{AREA_LABEL.get(p.planets[lord5]['house'], 'the 5th-house lane')}</strong>. "
                     f"Patience beats control when timelines do not match your hopes.</p>")
    if "Ketu" in p.conjunct() and h == 5:
        lines.append("<p class='pred'>Ketu with the lagna lord can delay or spiritualise progeny — "
                     "fewer children, later timing, or a strong pull toward creative rather than biological parenthood.</p>")
    if "Venus" in p.conjunct() and h == 5:
        lines.append("<p class='pred'>Venus beside your lagna lord favours romance, art, and children who bring pride — "
                     "channel the same warmth into one focused creative project at a time.</p>")
    return "".join(lines)


def _health_section(p: Pillar) -> str:
    sign6 = p.houses[6]["sign"]
    watch = [BODY_ZONE.get(p.lagna, "general vitality"), BODY_ZONE.get(sign6, "daily stamina")]
    lines = [
        f"<p class='pred'>Over the years, guard <strong>{watch[0]}</strong> and <strong>{watch[1]}</strong>. "
        f"Stress shows here first when sleep, meals, or boundaries slip.</p>",
    ]
    if p.hemming()["papa"]:
        lines.append("<p class='pred'>Malefic hemming on the lagna lord flags periodic health friction — "
                     "prevention and steady routine beat crisis fixes.</p>")
    maraka_bits = []
    for a in p.antars:
        if a.get("status") not in ("current", "future"):
            continue
        if a["ad_lord"] in p.maraka_lords or a["ad_lord"] in p.mb_critical:
            maraka_bits.append(f"<strong>{a['ad_lord']}</strong> ({_fmt_iso(a['start'])} – {_fmt_iso(a['end'])})")
        if len(maraka_bits) >= 2:
            break
    if maraka_bits:
        lines.append(f"<p class='pred'><strong>Health-watch windows:</strong> {', '.join(maraka_bits)} — "
                     f"schedule check-ups and avoid piling stress in those months.</p>")
    return "".join(lines) + "<p class='note'>Educational only — see a doctor for symptoms.</p>"


def _growth_section(p: Pillar) -> str:
    lord9 = p.houses[9]["lord"]
    h9 = p.planets[lord9]["house"]
    lines = [
        f"<p class='pred'>Luck, mentors, and inner growth open through <strong>{AREA_LABEL.get(h9, 'belief and travel')}</strong>. "
        f"Study, pilgrimage, or an honest teacher can lift you when shortcuts fail.</p>",
    ]
    strong_chain = sum(1 for c in p.chain if c.get("dignity") in STRONG)
    if strong_chain:
        lines.append("<p class='pred'>Your dispositor chain ends on a strong note — "
                     "even when intermediate steps wobble, the pillar does not fully collapse.</p>")
    elif p.planets[p.dispositor]["dignity"] == "debilitated":
        lines.append(f"<p class='pred'>A weak dispositor ({p.dispositor}) means gains come through effort and clean conduct, "
                     f"not automatic grace — stay patient with slow-building luck.</p>")
    return "".join(lines)


def _personality_brief(p: Pillar) -> str:
    trait = LAGNA_TRAIT.get(p.lagna, "purposeful")
    lines = [
        f"<p class='pred'>You come across as <strong>{trait}</strong> — that is the tone of your {p.lagna} rising.</p>",
        f"<p class='pred'>Day-to-day drive runs through <strong>{AREA_LABEL.get(p.ll['house'], 'personal direction')}</strong>, "
        f"while your emotional centre sits in <strong>{AREA_LABEL.get(p.planets['Moon']['house'], 'inner life')}</strong>.</p>",
    ]
    if p.conjunct():
        partners = [c for c in p.conjunct() if c != p.lagna_lord]
        if partners:
            lines.append(f"<p class='pred'>Close companions in the chart — <strong>{', '.join(partners)}</strong> — "
                         f"colour how you love, work, and push for what matters.</p>")
    return "".join(lines)


def _appendix(p: Pillar) -> str:
    return f"""<details class='appendix'><summary>Pillar chart facts (technical)</summary>
<h2>Chart essentials</h2>{_essentials(p)}
<h2>Lagna seven factors</h2>{_seven_table(p)}
<h2>Lagna lord dignity</h2>{_dignity_table(p)}
<h2>Influences on {p.lagna_lord}</h2>{_influences(p)}
<h2>Dispositor chain</h2>{_chain(p)}
<h2>Life implications (table)</h2>{_life_implications(p)}
<h2>Full mahadasa map</h2>{_dasha_table(p)}
</details>"""


def _dignity_table(p: Pillar) -> str:
    h = p.ll["house"]
    dig = _dignity_plain(p.ll["dignity"])
    rows = [
        ("Sign dignity", f"{p.lagna_lord} in {p.ll['sign']} = {dig}."),
        ("House placement", f"{_ord(h)} house — {_house_class_word(h)}."),
        ("Neecha Bhanga", p.nb.get("verdict", "Not applicable")),
        ("Navamsa", f"{p.lagna_lord} in {p.ll['navamsa']} navamsa"
         + (" (own — strong)" if SIGN_LORD[p.ll["navamsa"]] == p.lagna_lord else "")),
    ]
    body = "".join(f"<tr><td><strong>{_e(a)}</strong></td><td>{_e(b)}</td></tr>" for a, b in rows)
    return f"<table><tbody>{body}</tbody></table>"


# ───────────────────────────── render helpers (appendix) ─────────────────────


def _css() -> str:
    try:
        t = GOLD.read_text(encoding="utf-8")
        i, j = t.find("<style>"), t.find("</style>")
        if i != -1 and j != -1:
            return t[i + 7:j]
    except Exception:
        pass
    return (":root{--heading:#6b4c9a;--accent:#2a7a4a;--text:#1a1a2e;--muted:#6b6b7a;--bg:#f5f0eb;--card:#fff;--border:#d8cfc4}"
            "body{font-family:Georgia,serif;line-height:1.7;color:var(--text);background:var(--bg);margin:0;padding:1.5rem}"
            ".card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:1.5rem;max-width:48rem;margin:auto}"
            "h1{font-size:1.25rem;color:var(--heading);border-bottom:2px solid var(--heading);padding-bottom:.35rem;margin-top:1.4rem}"
            ".lead,.pred{font-size:.96rem;margin:.6rem 0}.meta{display:grid;grid-template-columns:auto 1fr;gap:.2rem .8rem;font-size:.9rem;margin:1rem 0}"
            ".meta dt{color:var(--muted)}.callout{background:#f3eefb;border-left:4px solid var(--heading);padding:12px 16px;border-radius:8px;margin:1rem 0}"
            ".note{font-size:.85rem;color:var(--muted);font-style:italic}table{width:100%;border-collapse:collapse;font-size:.85rem;margin:.6rem 0}"
            "th,td{border:1px solid var(--border);padding:.4rem;text-align:left}tr.cur td{background:#fff9f0}"
            "details.appendix{margin-top:1.5rem;font-size:.88rem}")


def _essentials(p: Pillar) -> str:
    rows = []
    order = [p.lagna_lord, p.dispositor] + [x for x in p.conjunct() if x not in (p.lagna_lord, p.dispositor)]
    order += [x for x in ["Moon", "Mars", "Saturn", "Rahu", "Sun", "Ketu", "Jupiter", "Venus", "Mercury"]
              if x not in order]
    seen = set()
    # Lagna row
    lag_nav = navamsa_sign(p.lagna, p.pc["meta"].get("lagna_degree", 0.0) % 30)
    rows.append(f"<tr><td><strong>Lagna (ASC)</strong></td><td>{p.lagna}</td>"
                f"<td>{_dms(p.pc['meta'].get('lagna_degree',0.0)%30)}</td><td>1st</td>"
                f"<td>{_e(p.pc['meta'].get('lagna_nakshatra',''))} Pada {p.pc['meta'].get('lagna_pada','')}</td>"
                f"<td>{lag_nav}</td></tr>")
    for nm in order:
        if nm in seen or nm not in p.planets:
            continue
        seen.add(nm)
        v = p.planets[nm]
        tag = ""
        if nm == p.lagna_lord:
            tag = " (Lagna Lord)"
        elif nm == p.dispositor:
            tag = " (Dispositor of LL)"
        elif nm in p.conjunct():
            tag = " (conjunct LL)"
        dg = DIGNITY_WORD.get(v["dignity"], v["dignity"])
        flag = " ⚠" if v["dignity"] == "debilitated" else (" ✓" if v["dignity"] in STRONG else "")
        nav_note = " (own)" if SIGN_LORD[v["navamsa"]] == nm else ""
        rows.append(f"<tr><td><strong>{nm}{tag}</strong></td><td>{v['sign']}{flag}</td>"
                    f"<td>{_dms(v['degree'])}</td><td>{_ord(v['house'])}</td>"
                    f"<td>{_e(v['nakshatra'])} Pada {v['pada']}</td><td>{v['navamsa']}{nav_note}</td></tr>")
    hmap = " · ".join(f"{h}={p.houses[h]['sign'][:2]}" for h in range(1, 13))
    return (f"<table><thead><tr><th>Point</th><th>Sign</th><th>Degree</th><th>House</th>"
            f"<th>Naksatra / Pada</th><th>Navamsa</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
            f"<div class='sub-note'>House map from {p.lagna} lagna: {hmap}</div>")


def _seven_table(p: Pillar) -> str:
    rows = []
    for f in p.seven:
        res = f.get("result", "")
        cls = "hl-green" if res.upper().startswith(("YES", "NO (PROT")) or "protect" in res.lower() else "hl-amber"
        badge = "badge-green" if cls == "hl-green" else "badge-amber"
        rows.append(f"<tr class='{cls}'><td><strong>{_e(f['factor'])}</strong></td>"
                    f"<td>{_e(f.get('detail',''))}</td><td><span class='badge {badge}'>{_e(res)}</span></td></tr>")
    return ("<table><thead><tr><th>Factor</th><th>Condition in this chart</th><th>Status</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>")


def _influences(p: Pillar) -> str:
    conj = p.conjunct()
    asp = p.aspecting(p.ll["house"])
    hem = p.hemming()
    fav, adv = [], []
    for c in conj:
        v = p.planets[c]
        line = f"<tr><td><strong>{c} conjunct</strong></td><td>{c} in {v['sign']} ({DIGNITY_WORD.get(v['dignity'],v['dignity'])})"
        if c in NAT_BENEFIC and v["dignity"] in STRONG:
            fav.append(line + " — a strong benefic association lifting the lagna lord.</td></tr>")
        elif c in NAT_BENEFIC:
            fav.append(line + " — benefic company supporting the lagna lord.</td></tr>")
        else:
            adv.append(line + " — a malefic in the same sign pressures the lagna lord.</td></tr>")
    for a in asp:
        v = p.planets[a]
        line = f"<tr><td><strong>{a}'s aspect</strong></td><td>{a} from {v['sign']} aspects the lagna lord"
        (fav if a in NAT_BENEFIC else adv).append(line + ".</td></tr>")
    if hem["papa"]:
        adv.append(f"<tr><td><strong>Papa-Katari (hemming)</strong></td><td>Malefics flank the lagna lord — "
                   f"{', '.join(hem['prev'])} in {hem['prev_sign']} and {', '.join(hem['next'])} in {hem['next_sign']}. "
                   f"A real blemish that periodically activates health/identity friction.</td></tr>")
    disp = p.planets[p.dispositor]
    if disp["dignity"] == "debilitated" or disp["house"] in DUSTHANA:
        adv.append(f"<tr><td><strong>Weak dispositor</strong></td><td>{p.dispositor} (lord of {p.ll['sign']}) is "
                   f"{DIGNITY_WORD.get(disp['dignity'],disp['dignity'])} in the {_ord(disp['house'])} house — a weak "
                   f"dispositor dilutes the lagna lord's delivery.</td></tr>")
    if not fav:
        fav.append("<tr><td>—</td><td>No outstanding benefic support on the lagna lord.</td></tr>")
    if not adv:
        adv.append("<tr><td>—</td><td>No notable affliction on the lagna lord.</td></tr>")
    return (f"<div class='grid2'><div><table><thead><tr><th colspan='2'>✅ Favourable on {p.lagna_lord}</th></tr></thead>"
            f"<tbody>{''.join(fav)}</tbody></table></div>"
            f"<div><table><thead><tr><th colspan='2'>⚠ Adverse on {p.lagna_lord}</th></tr></thead>"
            f"<tbody>{''.join(adv)}</tbody></table></div></div>")


def _chain(p: Pillar) -> str:
    out = ""
    for k, c in enumerate(p.chain):
        dig = DIGNITY_WORD.get(c.get("dignity"), c.get("dignity", ""))
        strong = c.get("dignity") in STRONG
        note = ("In own/exaltation — a strong link." if strong
                else ("Debilitated / weak link." if c.get("dignity") == "debilitated"
                      else f"{dig}; in the {_ord(c.get('house',0))} house."))
        out += (f"<div class='chain-step'><div class='chain-node'>{c['planet']}<br>{c['sign']} · {_ord(c.get('house',0))}</div>"
                f"<div class='chain-detail'>{_e(note)}</div></div>")
        if k < len(p.chain) - 1:
            out += "<div class='chain-arrow'>↓ dispositor</div>"
    strong_links = sum(1 for c in p.chain if c.get("dignity") in STRONG)
    verdict = ("The chain ends well — a well-dignified link grounds the lagna lord and prevents collapse despite weak "
               "intermediate steps." if strong_links else
               "The chain is weak throughout — the lagna lord lacks a strong dispositor grounding.")
    return out + f"<div class='callout amber'><strong>Dispositor Chain Verdict:</strong> {_e(verdict)}</div>"


def _dasha_table(p: Pillar) -> str:
    """The prediction core: when the Lagna Lord, dispositor and marakas fire."""
    today = date.today()
    dob_y = int(p.pc["meta"]["dob"][:4])
    rows = []
    # whole-life MD rows
    for m in p.seq:
        s, e = _pd(m["start"]), _pd(m["end"])
        lord = m["md_lord"]
        age = f"{s.year - dob_y}–{e.year - dob_y}"
        cls, role = "", []
        if lord == p.lagna_lord:
            role.append("LAGNA LORD mahadasa — its full pillar energy")
            cls = "hl-purple"
        if lord == p.dispositor:
            role.append("dispositor of the lagna lord runs")
        if lord in p.maraka_lords:
            role.append("maraka period")
        if lord in p.mb_critical:
            role.append("Mrityu-Bhaga sensitive")
        if s <= today < e:
            cls = cls or "hl-amber"
            role.append("CURRENT")
        rtxt = "; ".join(role) if role else f"{lord} in {p.planets[lord]['sign']} ({_ord(p.planets[lord]['house'])})"
        theme = (f"{HOUSE_THEME[p.planets[lord]['house']].capitalize()} emphasis."
                 + (" Lagna-lord themes (identity, health, direction) become primary." if lord == p.lagna_lord else "")
                 + (" Health-awareness window — preventive care advised." if (lord in p.maraka_lords or lord in p.mb_critical) else ""))
        rows.append(f"<tr class='{cls}'><td><strong>{lord} MD</strong></td><td>{_moy(s)} – {_moy(e)}</td>"
                    f"<td>{age}</td><td>{_e(rtxt)}</td><td>{_e(theme)}</td></tr>")
    # current-MD antardashas highlighting LL / maraka / MB
    ad_rows = []
    md = p.cur_md["md_lord"]
    for a in p.antars:
        s, e = _pd(a["start"]), _pd(a["end"])
        lord = a["ad_lord"]
        if e < today and not (s <= today < e):
            pass
        cls, role = "", []
        if lord == p.lagna_lord:
            role.append("lagna lord activates in the career/identity house")
            cls = "hl-green"
        if lord in p.maraka_lords:
            role.append("maraka")
            cls = "hl-amber"
        if lord in p.mb_critical:
            role.append("Mrityu-Bhaga critical → highest health-watch")
            cls = "hl-red"
        if s <= today < e:
            role.append("CURRENT")
            cls = cls or "hl-amber"
        occ = p.planets[lord]["house"]
        theme = (f"{HOUSE_THEME[occ].capitalize()} themes active."
                 + (" Strongest career-supporting window of the decade." if (lord in p.conjunct() and occ == 10) else "")
                 + (" Convergent health-sensitivity — schedule preventive checks." if (lord in p.maraka_lords or lord in p.mb_critical) else ""))
        ad_rows.append(f"<tr class='{cls}'><td><strong>{md[:3]}–{lord[:3]}</strong></td><td>{_moy(s)} – {_moy(e)}</td>"
                       f"<td>{_e('; '.join(role) if role else 'sub-period')}</td><td>{_e(theme)}</td></tr>")
    md_tbl = ("<table><thead><tr><th>Mahadasa</th><th>Dates</th><th>Age</th><th>Pillar connection</th>"
              "<th>Life theme</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>")
    ad_tbl = ("<h3>Current Decade — Antardasa Activation of the Pillar</h3>"
              "<table><thead><tr><th>Antardasa</th><th>Dates</th><th>Pillar role</th><th>Life theme</th></tr></thead>"
              "<tbody>" + "".join(ad_rows) + "</tbody></table>")
    return md_tbl + ad_tbl


def _life_implications(p: Pillar) -> str:
    h = p.ll["house"]
    rows = [
        ("Career & Profession",
         f"With the lagna lord {p.lagna_lord} in the {_ord(h)} house ({HOUSE_THEME[h]}), "
         f"{HOUSE_THEME[h].split('&')[0].strip()} is structurally central to this life. "
         f"{'Exalted benefic company strengthens the career house. ' if any(x in NAT_BENEFIC and p.planets[x]['dignity'] in STRONG for x in p.conjunct()) else ''}"),
        ("Health & Body",
         "Moderate vulnerability where the lagna lord is weak or hemmed; strongest health-watch falls in maraka and "
         "Mrityu-Bhaga sub-periods flagged in the dasha table. Preventive care during those windows is the key action."),
        ("Identity & Self",
         f"The {p.lagna} lagna and its lord {p.lagna_lord} set the tone of self-expression; "
         f"identity questions surface most during the lagna lord's and its dispositor's periods."),
    ]
    body = "".join(f"<tr><td><strong>{_e(a)}</strong></td><td>{_e(b)}</td></tr>" for a, b in rows)
    return f"<table><thead><tr><th>Life Domain</th><th>Implication</th></tr></thead><tbody>{body}</tbody></table>"


def render(p: Pillar, dob_disp: str, tob: str = "", place: str = "") -> str:
    nm = _e(p.name)
    today = date.today()
    sc = p.score()
    h = p.ll["house"]
    meta_place = f" · {_e(place)}" if place else ""
    meta_tob = f" · {_e(tob)}" if tob else ""

    body = f"""
  <article class="card">
    <h1 style="color:var(--heading,#6b4c9a);">Your life reading — Pillar of Life</h1>
    <dl class="meta">
      <dt>Client</dt><dd>{nm}</dd>
      <dt>Birth</dt><dd>{_e(dob_disp)}{meta_tob}{meta_place}</dd>
      <dt>Lagna</dt><dd>{p.lagna} · lord {p.lagna_lord} in {_ord(h)} house ({p.ll['sign']})</dd>
      <dt>Report date</dt><dd>{today.strftime('%d %B %Y').lstrip('0')}</dd>
    </dl>
    <p class="lead">A plain-English reading from your chart's central pillar — the lagna and lagna lord — with dated
    periods for money, work, love, health, and direction. Technical tables are in the appendix.</p>

    <div class="callout">{_snapshot(p)}</div>

    <h1>Your timeline — what comes when</h1>
    <p class="pred">You remain in the <strong>{p.cur_md.get('md_lord', '')}</strong> major chapter until
    {_fmt_iso(p.cur_md.get('end', ''))}. Below are the sub-periods ahead and what they tend to bring.</p>
    {_timeline(p)}
    {_ll_maha_window(p)}

    <h1>Your pillar — strength and direction</h1>
    {_pillar_strength(p, sc)}

    <h1>Job &amp; career</h1>
    {_career_section(p)}

    <h1>Wealth &amp; income</h1>
    {_wealth_section(p)}

    <h1>Marriage &amp; partnership</h1>
    {_marriage_section(p)}

    <h1>Children &amp; creativity</h1>
    {_children_section(p)}

    <h1>Health &amp; energy</h1>
    {_health_section(p)}

    <h1>Growth, travel &amp; upliftment</h1>
    {_growth_section(p)}

    <h1>Who you are — in brief</h1>
    {_personality_brief(p)}

    {_appendix(p)}

    <p class="note">Educational astrology only. Timings are from your Vimshottari extract — cross-check important dates in your software.</p>
  </article>"""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Vedic reading — Pillar — {nm}</title>
<style>{_css()}</style></head><body>{body}</body></html>"""


def generate_pillar_html(
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
    p = Pillar(pc)
    d = datetime.strptime(dob, "%Y-%m-%d").date()
    doc = render(p, d.strftime("%d %B %Y").lstrip('0'), tob, place)
    sc = p.score()
    summary = {"lagna": p.lagna, "lagna_lord": p.lagna_lord, "ll_sign": p.ll["sign"],
               "ll_house": p.ll["house"], "ll_dignity": p.ll["dignity"],
               "neecha_bhanga": bool(p.nb.get("neecha_bhanga_present")),
               "overall": sc["overall"], "verdict": p.verdict_word(sc["overall"])}
    return doc, summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Deterministic Pillar of Life report (no LLM)")
    ap.add_argument("name")
    ap.add_argument("dob")
    ap.add_argument("extracted", nargs="?", default=None, help="Optional legacy AstroSage extract")
    add_chart_source_args(ap)
    ap.add_argument("--tob", default="")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    kw = chart_kwargs_from_args(args)
    doc, summary = generate_pillar_html(
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
    out = Path(args.out) if args.out else BASE_DIR / "reports" / f"Vedic_Pillar_{args.name}_preview.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(f"LL={summary['lagna_lord']} in {summary['ll_sign']} (H{summary['ll_house']}, {summary['ll_dignity']}) "
          f"NB={summary['neecha_bhanga']} → {summary['verdict']} ({summary['overall']}%)")
    print(f"written → {out}")


if __name__ == "__main__":
    main()
