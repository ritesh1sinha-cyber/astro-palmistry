#!/usr/bin/env python3
"""
vedic_vimshottari_report.py - Deterministic Vimshottari Dasha report (NO LLM).

Replaces the Cursor Vimshottari lane. This is the timing backbone of the whole
reading, so the engine is prediction-first and dasha-driven:

  * Mahadasa + Antardasa dates come from the precompute (Lahiri Vimshottari grid,
    itself parsed from the AstroSage extract).
  * Pratyantardasa (sub-sub periods of the running antardasa) are computed
    deterministically from the standard Vimshottari proportions (PD_duration =
    AD_duration * PD_years / 120, in classical order starting from the AD lord).
  * Every period gets natural-language, dated, book-backed prediction text built
    by fusing each lord's house-lordship, house-occupancy, dignity and natural
    significations in THIS chart.

Whole-sign houses are recomputed from sign + Lagna (precompute's stored ``house``
is unreliable for Saturn-ruled placements).

Sources: Laghu Parashari framework; Boney's multi-lagna composite approach;
standard Parashari Vimshottari rules. Fully offline - no model, no network.
Mehta Modern Techniques (rules4) merged for house-lord depth.
"""
from __future__ import annotations

import argparse
import html
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from astro_precompute import resolve_precompute
from chart_client import female_from_pc
from chart_resolve import add_chart_source_args, chart_kwargs_from_args
from vedic_varga_goel import (
    analyze_d7, analyze_d9, analyze_d10, analyze_d30, parse_shodashvarga, varga_facts_table,
    vargas_from_precompute,
)
from vim_mehta_merge import build_mehta_chart, mehta_lord_table_html, mehta_merged_body
from boney_divisional_timing import (
    adjust_verdict_by_crosscheck,
    boney_lord_snippet,
    dignity_crosscheck_for_lord,
    render_boney_period_block,
    score_active_period,
)
from gk_transit_dasha import (
    gk_window_snippet,
    render_gk_transit_dasha_block,
    score_gk_transit_dasha_window,
    score_transit_dasha_synergy,
    upcoming_eventful_years,
)

BASE_DIR = Path(__file__).resolve().parent
GOLD = BASE_DIR / "reports" / "Ritz_reprot" / "Vedic_Vimshottari_Ritz_20260408.html"

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = {"Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
             "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
             "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
             "Pisces": "Jupiter"}
HOUSE_THEME = {
    1: "self, body & identity", 2: "wealth, family & speech", 3: "courage, siblings & communication",
    4: "home, mother & property", 5: "children, creativity & education", 6: "work, service, debts & health",
    7: "marriage & partnerships", 8: "transformation, longevity & hidden matters", 9: "fortune, dharma & long travel",
    10: "career & public standing", 11: "gains, income & networks", 12: "foreign lands, expenses & spirituality",
}
HOUSE_EVENTS = {
    1: "new beginnings, initiatives, and a renewed focus on health and personal direction",
    2: "family matters, savings, income flow, and changes in food, speech or accumulated assets",
    3: "communication projects, short travels, sibling matters, courage and self-driven effort",
    4: "home, property or vehicle matters, the mother's wellbeing, and emotional/educational foundations",
    5: "children, romance, creative and speculative ventures, education and devotional pursuits",
    6: "the job/service arena, competition, debts or litigation, and daily-work and health discipline",
    7: "marriage and partnerships, business deals, public dealings and travel",
    8: "transformation, research, inheritance/joint resources, sudden change and matters that need depth",
    9: "fortune, higher learning, dharma, mentors, the father, and long journeys",
    10: "career, status, authority and public recognition",
    11: "gains, income, fulfilment of desires, networks and promotions",
    12: "foreign lands, relocation, expenses, spirituality, retreat and letting-go",
}
PLANET_KARAKA = {
    "Sun": "authority, government, father, vitality and recognition",
    "Moon": "the mind, mother, home, emotions and public connection",
    "Mars": "energy, courage, siblings, property, drive and decisive action",
    "Mercury": "intellect, communication, commerce, skill and learning",
    "Jupiter": "wisdom, wealth, children, dharma, mentorship and expansion",
    "Venus": "relationships, spouse, comfort, creativity, luxury and the arts",
    "Saturn": "discipline, service, patience, longevity, labour and structure",
    "Rahu": "foreign and unconventional currents, technology, ambition and sudden gains",
    "Ketu": "specialisation, research, detachment, spirituality and inner work",
}
PLANET_KEYWORD = {"Sun": "authority", "Moon": "emotional & domestic", "Mars": "drive & energy",
                  "Mercury": "intellect & communication", "Jupiter": "wisdom & expansion",
                  "Venus": "relationship & creativity", "Saturn": "discipline & service",
                  "Rahu": "ambition & the unconventional", "Ketu": "specialisation & depth"}
DIGNITY_WORD = {"exalted": "exalted", "moolatrikona": "in moolatrikona", "own_sign": "in its own sign",
                "debilitated": "debilitated", "neutral_sign": "neutral", "friend_sign": "in a friend's sign",
                "enemy_sign": "in an enemy's sign", "great_friend_sign": "in a great friend's sign"}
STRONG = ("exalted", "own_sign", "moolatrikona", "great_friend_sign")
WEAK = ("debilitated", "enemy_sign")

VIM_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
VIM_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
             "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}

MAHA_PLAIN = {
    "Sun": "A chapter of visibility, authority, and stepping into the spotlight.",
    "Moon": "A feeling-led chapter - home, family, and emotional security take centre stage.",
    "Mars": "A driven chapter - competition, courage, and pushing through obstacles.",
    "Mercury": "A busy-minded chapter - deals, study, writing, and short travel.",
    "Jupiter": "A luck-leaning chapter - teachers, fair dealing, and gradual expansion.",
    "Venus": "A comfort chapter - love, art, savings, and enjoying what you earn.",
    "Saturn": "A duty chapter - slow solid gain, patience, and reputation over shortcuts.",
    "Rahu": "An ambitious chapter - foreign links, tech, and unconventional paths.",
    "Ketu": "A quieter chapter - letting go, research, and fewer material attachments.",
}

ANTAR_PLAIN = {
    "Sun": "Authority and recognition move - lead cleanly, watch ego and heat.",
    "Moon": "Feelings and home life colour everything - nurture, don't neglect rest.",
    "Mars": "Drive spikes - act, but pace yourself so you do not burn out.",
    "Mercury": "Paperwork, deals, and study pick up - organise before you expand.",
    "Jupiter": "Luck and mentors help - say yes to fair growth, skip over-promising.",
    "Venus": "Love, comfort, and creative joy rise - enjoy, but keep one reserve.",
    "Saturn": "Duty and delay - consolidate; rewards come through discipline.",
    "Rahu": "Restless change - foreign, tech, or unconventional pulls tempt you.",
    "Ketu": "Quiet inward work - finish old tasks, let one draining habit go.",
}

PLANET_REMEDY = {
    "Sun": "Sundays: sunlight walk, respect elders, keep routine check-ups sensible.",
    "Moon": "Mondays: calm evening, simple food, journal feelings, call family.",
    "Mars": "Tuesdays: exercise cleanly, channel anger into sport or work - not arguments.",
    "Mercury": "Wednesdays: clear emails, organise papers, study one useful skill.",
    "Jupiter": "Thursdays: modest charity or teaching; avoid risky loans.",
    "Venus": "Fridays: art, kindness, beauty at home - nurture close bonds.",
    "Saturn": "Saturdays: discipline, sleep on time, help someone older; patience pays.",
    "Rahu": "Ground weekly: limit screens and speculation; stick to one practical goal.",
    "Ketu": "Quiet hour daily: meditation, finish an old task, let one habit go.",
}

DOMAIN_LEAD = {
    "wealth": "Money moves in waves - Vimshottari shows when to save and when to spend.",
    "career": "Work and reputation rise on their own schedule - these antardasas mark the push points.",
    "marriage": "Partnership has its own rhythm - some sub-periods open love, others ask for patience.",
    "children": "Family, romance, and creativity share one emotional lane - timing helps.",
    "health": "Routine slips hurt most in certain sub-periods - prevention beats crisis fixes.",
    "growth": "Luck, mentors, study, and travel can lift you when other areas feel stuck.",
}


def _e(s) -> str:
    return html.escape(str(s))


def _ord(n) -> str:
    n = int(n)
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th"))


def house_of(sign: str, lagna: str) -> int:
    return (SIGNS.index(sign) - SIGNS.index(lagna)) % 12 + 1


def _pd(iso: str) -> date:
    return datetime.strptime(iso[:10], "%Y-%m-%d").date()


def _dmy(d: date) -> str:
    return d.strftime("%d %b %Y").lstrip('0')


def _moy(d: date) -> str:
    return d.strftime("%b %Y")


class Vim:
    def __init__(self, pc: dict):
        self.pc = pc
        self.lagna = pc["meta"]["lagna_sign"]
        self.lagna_idx = SIGNS.index(self.lagna)
        self.name = pc["meta"]["client"]
        self.age = int(pc["meta"]["age"])
        self.lagna_lord = SIGN_LORD[self.lagna]
        self.planets = {}
        for nm, v in pc["planets"].items():
            self.planets[nm] = {
                "sign": v["sign"], "degree": v.get("degree_in_sign", 0.0),
                "nakshatra": v.get("nakshatra", ""), "dignity": v.get("dignity", "neutral_sign"),
                "house": house_of(v["sign"], self.lagna),
                "func": v.get("functional_status", "neutral"),
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
        self.seq = pc["vimshottari"]["sequence"]
        self.cur_md = pc["vimshottari"]["current_md"]
        self.antars = pc["vimshottari"]["current_md_antardashas"]

    def role(self, p: str) -> str:
        ruled = self.rules.get(p, [])
        occ = self.planets[p]["house"]
        r = " & ".join(_ord(h) for h in ruled) if ruled else "-"
        return f"{r} lord in the {_ord(occ)}"

    def short_theme(self, p: str) -> str:
        occ = self.planets[p]["house"]
        return f"{PLANET_KEYWORD[p].capitalize()} via {HOUSE_THEME[occ].split(',')[0]}"

    def strength_note(self, p: str) -> str:
        dig = self.planets[p]["dignity"]
        if dig in STRONG:
            return "Being well-dignified, it delivers its results with strength and relative ease."
        if dig in WEAK:
            return ("Being weak in dignity, its results arrive after effort or initial friction - "
                    "patience converts the period's pressure into gain.")
        return "Its moderate dignity gives steady, workmanlike results rather than dramatic swings."

    def prediction(self, p: str, level: str = "antardasa") -> str:
        pl = self.planets[p]
        ruled = self.rules.get(p, [])
        occ = pl["house"]
        ruled_txt = " and ".join(_ord(h) for h in ruled) if ruled else "no rashi (node)"
        return (f"{p} - your {ruled_txt} lord, placed in the {_ord(occ)} house "
                f"({pl['sign']}, {DIGNITY_WORD.get(pl['dignity'], pl['dignity'])}) - steers this "
                f"{level} toward {HOUSE_EVENTS[occ]}. As natural significator of {PLANET_KARAKA[p]}, "
                f"those themes colour the period. {self.strength_note(p)}")

    # ── pratyantar of a given antardasa ───────────────────────────────────
    def pratyantar(self, ad_lord: str, ad_start: date, ad_end: date) -> list[dict]:
        total_days = (ad_end - ad_start).days
        if total_days <= 0:
            return []
        start_i = VIM_ORDER.index(ad_lord)
        order = VIM_ORDER[start_i:] + VIM_ORDER[:start_i]
        out = []
        cur = ad_start
        for k, pd_lord in enumerate(order):
            frac = VIM_YEARS[pd_lord] / 120.0
            dur = total_days * frac
            end = ad_start + timedelta(days=round(sum(VIM_YEARS[order[i]] for i in range(k + 1)) / 120.0 * total_days))
            out.append({"lord": pd_lord, "start": cur, "end": end})
            cur = end
        if out:
            out[-1]["end"] = ad_end
        return out



def _verdict_tag(kind: str) -> str:
    labels = {
        "good": ("Good phase", "tag-good"),
        "attention": ("Needs attention", "tag-warn"),
        "hard": ("Challenging", "tag-hard"),
    }
    text, cls = labels.get(kind, ("Mixed", "tag-warn"))
    return f'<span class="{cls}">{text}</span>'


def _lord_verdict_d1(v: "Vim", p: str) -> str:
    pl = v.planets.get(p, {})
    dig = pl.get("dignity", "neutral_sign")
    occ = pl.get("house", 1)
    if dig in STRONG or occ in (1, 4, 5, 9, 10, 11):
        return "good"
    if dig in WEAK or occ in (6, 8, 12):
        return "hard"
    return "attention"


def _lord_verdict(v: "Vim", p: str) -> str:
    base = _lord_verdict_d1(v, p)
    cc = dignity_crosscheck_for_lord(v.pc, p)
    if cc.get("available"):
        return adjust_verdict_by_crosscheck(base, cc.get("tier", "neutral"))
    return base


def _boney_lord_hint(v: "Vim", p: str) -> str:
    snip = boney_lord_snippet(v.pc, p)
    if not snip:
        return ""
    return f" <span class='fine'>({html.escape(snip)})</span>"


def _gk_window_hint(v: "Vim", w: dict) -> str:
    gk = score_gk_transit_dasha_window(
        md=w["md"], ad=w["lord"], pc=v.pc, w_start=w["start"], w_end=w["end"],
    )
    snip = gk_window_snippet(gk)
    if not snip:
        return ""
    return f" <span class='fine'>({html.escape(snip)})</span>"


def _human_antar(v: "Vim", lord: str, md: str) -> str:
    occ = v.planets[lord]["house"]
    ruled = v.rules.get(lord, [])
    bits = [ANTAR_PLAIN.get(lord, "")]
    if ruled:
        bits.append(f"It rules your {_ord(ruled[0])}" + (f" and {_ord(ruled[1])}" if len(ruled) > 1 else "") + ".")
    bits.append(f"Through the {_ord(occ)} house, {HOUSE_THEME[occ].split(',')[0]} is loud.")
    return " ".join(bits)


def _antar_windows(v: "Vim") -> list[dict]:
    out = []
    for a in v.antars:
        s, e = _pd(a["start"]), _pd(a["end"])
        out.append({"lord": a["ad_lord"], "start": s, "end": e, "md": v.cur_md["md_lord"]})
    return out


def _snapshot(v: "Vim") -> str:
    today = date.today()
    cur = next((a for a in v.antars if a.get("status") == "current"), None)
    bits = [
        "<strong>Where you are now:</strong> Vimshottari is your <strong>120-year life clock</strong> - "
        "mahadasa sets the chapter, antardasa sets the scene."
    ]
    bits.append(
        f"Big chapter <strong>{v.cur_md['md_lord']}</strong> until "
        f"<strong>{_dmy(_pd(v.cur_md['end']))}</strong> - {MAHA_PLAIN.get(v.cur_md['md_lord'], '')}"
    )
    if cur:
        bits.append(
            f"Current slice <strong>{v.cur_md['md_lord']}-{cur['ad_lord']}</strong> until "
            f"<strong>{_dmy(_pd(cur['end']))}</strong> {_verdict_tag(_lord_verdict(v, cur['ad_lord']))}: "
            f"{_human_antar(v, cur['ad_lord'], v.cur_md['md_lord'])}"
        )
    return " ".join(bits)


def _timeline(v: "Vim", n: int = 5) -> str:
    today = date.today()
    rows = []
    for w in _antar_windows(v):
        if w["end"] < today:
            continue
        if len(rows) >= n:
            break
        label = "Now" if w["start"] <= today < w["end"] else ("Next" if len(rows) == 1 else "Later")
        cls = ' class="cur"' if label == "Now" else ""
        rows.append(
            f"<tr{cls}><td><strong>{label}</strong></td>"
            f"<td>{_dmy(w['start'])} - {_dmy(w['end'])}</td>"
            f"<td>{_verdict_tag(_lord_verdict(v, w['lord']))}</td>"
            f"<td><strong>{w['md'][:3]}-{w['lord'][:3]}</strong> - {_human_antar(v, w['lord'], w['md'])}{_boney_lord_hint(v, w['lord'])}{_gk_window_hint(v, w)}</td></tr>"
        )
    if not rows:
        return "<p class='pred'>Antardasa dates not parsed.</p>"
    return (
        "<table class='simple'><tr><th>When</th><th>Dates</th><th>Verdict</th><th>What it means for you</th></tr>"
        + "".join(rows) + "</table>"
    )


def _slice_block(v: "Vim", windows: list, wrap: str) -> str:
    if not windows:
        return ""
    paras = []
    for w in windows:
        paras.append(
            f"<p class='pred'>{_verdict_tag(_lord_verdict(v, w['lord']))} "
            f"<strong>{_dmy(w['start'])} → {_dmy(w['end'])} ({w['md'][:3]}-{w['lord'][:3]}):</strong> "
            f"{_human_antar(v, w['lord'], w['md'])}{_boney_lord_hint(v, w['lord'])}{_gk_window_hint(v, w)}</p>"
        )
    return f"<div class='{wrap}'>" + "".join(paras) + "</div>"


def _recent_past(v: "Vim", n: int = 3) -> str:
    today = date.today()
    past = [w for w in _antar_windows(v) if w["end"] <= today][-n:]
    return _slice_block(v, past, "callout-past")


def _future_paras(v: "Vim", n: int = 3) -> str:
    today = date.today()
    fut = [w for w in _antar_windows(v) if w["start"] > today][:n]
    body = _slice_block(v, fut, "callout-future")
    nxt_md = next((m for m in v.seq if _pd(m["end"]) > today and m["md_lord"] != v.cur_md["md_lord"]), None)
    if nxt_md:
        body += (
            f"<p class='pred'><strong>From {_dmy(_pd(nxt_md['start']))}:</strong> next mahadasa "
            f"<strong>{nxt_md['md_lord']}</strong> - {MAHA_PLAIN.get(nxt_md['md_lord'], '')}</p>"
        )
    return body


def _domain_hit(v: "Vim", lord: str, domain: str) -> bool:
    houses = {"wealth": {2, 11}, "career": {6, 10}, "marriage": {7, 2},
              "children": {5}, "health": {6, 8, 12}, "growth": {3, 9, 12}}[domain]
    occ = v.planets[lord]["house"]
    return occ in houses or any(h in houses for h in v.rules.get(lord, []))


def _domain_section(v: "Vim", domain: str, fallback: str, boney_period: dict | None = None) -> str:
    today = date.today()
    cur = next((a for a in v.antars if a.get("status") == "current"), None)
    cur_lord = cur["ad_lord"] if cur else v.cur_md["md_lord"]
    tag = _verdict_tag(_lord_verdict(v, cur_lord) if _domain_hit(v, cur_lord, domain) else "attention")
    wins = []
    for w in _antar_windows(v):
        if w["end"] <= today or not _domain_hit(v, w["lord"], domain):
            continue
        wins.append(f"{_dmy(w['start'])} - {_dmy(w['end'])} ({w['lord'][:3]})")
        if len(wins) >= 2:
            break
    lead = f"<p class='pred'>{tag} {DOMAIN_LEAD[domain]}"
    if wins:
        lead += f" Worth watching: {', '.join(wins)}."
    lead += "</p>"
    parts = [lead]
    hits = 0
    for w in _antar_windows(v):
        if w["end"] <= today or not _domain_hit(v, w["lord"], domain):
            continue
        parts.append(
            f"<p class='pred'>{_verdict_tag(_lord_verdict(v, w['lord']))} "
            f"<strong>{_dmy(w['start'])} → {_dmy(w['end'])} ({w['md'][:3]}-{w['lord'][:3]}):</strong> "
            f"{ANTAR_PLAIN.get(w['lord'], '')}</p>"
        )
        hits += 1
        if hits >= 4:
            break
    if hits == 0:
        parts.append(f"<p class='pred'>{_verdict_tag('attention')} {fallback}</p>")
    if boney_period and domain in boney_period.get("domains", {}):
        bd = boney_period["domains"][domain]
        if bd.get("available"):
            parts.append(
                f"<p class='fine'><strong>Boney {bd.get('varga_key', 'varga')} (rules45):</strong> "
                f"{html.escape(bd.get('summary', ''))}</p>"
            )
    return "".join(parts)


def _personality_section(v: "Vim") -> str:
    moon = v.planets["Moon"]
    ll = v.planets[v.lagna_lord]
    return (
        f"<p class='pred'>{_verdict_tag(_lord_verdict(v, 'Moon'))} Your emotional baseline is Moon in "
        f"<strong>{moon['sign']}</strong> ({_ord(moon['house'])} house) - feelings show up around "
        f"{HOUSE_THEME[moon['house']].split(',')[0]}.</p>"
        f"<p class='pred'>{_verdict_tag(_lord_verdict(v, v.lagna_lord))} Life direction runs through "
        f"<strong>{v.lagna_lord}</strong> in <strong>{ll['sign']}</strong> - "
        f"{HOUSE_THEME[ll['house']].split(',')[0]} colours your path.</p>"
    )


def _remedies_section(v: "Vim") -> str:
    cur = next((a for a in v.antars if a.get("status") == "current"), None)
    seen, items = set(), []
    for p in ((cur or {}).get("ad_lord"), v.cur_md.get("md_lord"), v.lagna_lord):
        if p and p in PLANET_REMEDY and p not in seen:
            seen.add(p)
            label = " (active sub)" if p == (cur or {}).get("ad_lord") else ""
            items.append(f"<li><strong>{p}</strong>{label}: {PLANET_REMEDY[p]}</li>")
    items.append("<li>Keep agreements written - honest dealing protects luck more than rituals alone.</li>")
    return "<ul>" + "".join(items[:6]) + "</ul>"


def _prat_appendix(v: "Vim", ad: dict) -> str:
    if not ad:
        return ""
    rows = []
    today = date.today()
    for pd in v.pratyantar(ad["ad_lord"], _pd(ad["start"]), _pd(ad["end"])):
        cur = ' class="cur"' if pd["start"] <= today < pd["end"] else ""
        rows.append(
            f"<tr{cur}><td>{pd['lord']}</td><td>{_dmy(pd['start'])} - {_dmy(pd['end'])}</td>"
            f"<td>{ANTAR_PLAIN.get(pd['lord'], '')[:50]}…</td></tr>"
        )
    return (
        "<h2>Pratyantar (sub-sub) - current antardasa</h2>"
        "<table class='simple'><tr><th>Lord</th><th>Dates</th><th>Theme</th></tr>"
        + "".join(rows[:12]) + "</table>"
    )


def _appendix(v: "Vim", vargas: dict, mehta_chart=None) -> str:
    md_rows = "".join(
        f"<tr><td>{m['md_lord']}</td><td>{_dmy(_pd(m['start']))} - {_dmy(_pd(m['end']))}</td></tr>"
        for m in v.seq if _pd(m["end"]).year >= date.today().year - 5
    )
    varga_bits = ""
    for key, title in (("D7", "Saptamsha"), ("D9", "Navamsha"), ("D10", "Dashamsha"), ("D30", "Trimshamsha")):
        if key in vargas:
            ch = vargas[key]
            varga_bits += f"<p class='fine'><strong>{title}</strong> lagna: {ch.lagna}</p>"
    mehta_bits = mehta_lord_table_html(mehta_chart) if mehta_chart else ""
    return f"""<details class='appendix'><summary>Chart facts (technical)</summary>
<h2>Mahadasa timeline (recent + future)</h2>
<table class='simple'><tr><th>Lord</th><th>Dates</th></tr>{md_rows}</table>
{_prat_appendix(v, next((a for a in v.antars if a.get('status') == 'current'), None))}
{varga_bits}
{mehta_bits}
</details>"""


def _detect_female(text: str) -> bool:
    return bool(re.search(r"\bSex\s+Female\b", text, re.I))


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
    return (
        "body{font-family:Georgia,serif;max-width:46rem;margin:auto;padding:1.5rem;line-height:1.55}"
        ".card{background:#fff;border:1px solid #e0e0e0;border-radius:6px;padding:1.25rem 1.75rem}"
        ".callout{background:#e0f7fa;border-left:4px solid #006064;padding:.85rem 1rem;margin:1rem 0}"
        ".callout-future{background:#e8f5e9;border-left:4px solid #2e7d32;padding:.85rem 1rem;margin:1rem 0}"
        ".callout-past{background:#fff8e1;border-left:4px solid #f9a825;padding:.85rem 1rem;margin:1rem 0}"
        ".pred{margin:.65rem 0}table.simple{width:100%;border-collapse:collapse;font-size:.9rem}"
        "table.simple th,table.simple td{border:1px solid #e0e0e0;padding:.45rem}"
        "tr.cur td{background:#e0f7fa}details.appendix{margin-top:1.5rem;font-size:.88rem}"
        "h1{font-size:1.25rem;color:#006064;margin-top:1.5rem}"
        ".callout-mehta{background:#e8eaf6;border-left:4px solid #3949ab;padding:.85rem 1rem;margin:1rem 0}"
        ".callout-gk{background:#fff3e0;border-left:4px solid #e65100;padding:.85rem 1rem;margin:1rem 0}"
        ".sec.good .pred{border-left:3px solid #2e7d32;padding-left:.65rem}"
        ".sec.amber .pred{border-left:3px solid #f9a825;padding-left:.65rem}"
        ".pred-card{border:1px solid #e0e0e0;border-radius:6px;padding:.85rem 1rem;margin:.75rem 0}"
        ".pred-card.green{border-left:4px solid #2e7d32;background:#f1f8f4}"
        ".pred-card.good{border-left:4px solid #3949ab;background:#e8eaf6}"
        ".pred-card.neutral{border-left:4px solid #78909c;background:#fafafa}" + tags
    )


def render(v: "Vim", dob_disp: str, tob: str = "", place: str = "",
           vargas: dict | None = None, female: bool = False,
           mehta_chart=None) -> str:
    nm = _e(v.name)
    today = date.today()
    cur = next((a for a in v.antars if a.get("status") == "current"), None)
    md = v.cur_md["md_lord"]
    vargas = vargas or {}

    d7_block = d9_block = d10_block = d30_block = ""
    if "D7" in vargas:
        d7 = vargas["D7"]
        d7_block = (
            "<h1>Children - Saptamsha (D7) deep dive</h1>"
            "<p class='pred'>Goel treats Saptamsha as the <strong>final word on children</strong> - promise, count, "
            "happiness from progeny, and their path. Below is read from your Shodashvarga table.</p>"
            + analyze_d7(d7, v.lagna, v.houses[5]["lord"], female, v)
            + varga_facts_table(d7, "Saptamsha")
        )
    if "D9" in vargas:
        d9 = vargas["D9"]
        d9_block = (
            "<h1>Marriage - Navamsha (D9) deep dive</h1>"
            "<p class='pred'>Navamsha shows <strong>how marriage matures over time</strong> - promise, quality, "
            "happiness at home, and denial/delay flags. D9 outweighs D1 for long-term partnership tone.</p>"
            + analyze_d9(d9, female, v.houses[7]["lord"], v)
            + varga_facts_table(d9, "Navamsha")
        )
    if "D10" in vargas:
        d10 = vargas["D10"]
        d10_block = (
            "<h1>Profession - Dashamsha (D10) deep dive</h1>"
            "<p class='pred'>Dashamsha is the <strong>karmamsha</strong> - inward career drive and outward public face. "
            "Goel uses D10 for profession type, status, independence, and rise/fall tone.</p>"
            + analyze_d10(d10, v.houses[10]["lord"], v.lagna, v)
            + varga_facts_table(d10, "Dashamsha")
        )
    if "D30" in vargas:
        d30 = vargas["D30"]
        d30_block = (
            "<h1>Fortune &amp; adversity - Trimshamsha (D30) deep dive</h1>"
            "<p class='pred'>Trimshamsha is Goel's <strong>arista phalam</strong> chart - fortune vs misfortune, "
            "marriage-quality stress, and chronic trouble. Rules15 focal points: lagna lord, 8th lord, Moon, 8th house. "
            "Cross-check Navamsha (D9) for marriage outcome.</p>"
            + analyze_d30(
                d30, v.lagna, v.houses[7]["lord"], v.houses[6]["lord"], v.houses[8]["lord"], female, v,
                vargas.get("D9"),
            )
            + varga_facts_table(d30, "Trimshamsha")
        )

    mehta_block = mehta_merged_body(mehta_chart) if mehta_chart else ""

    ad_lord = cur["ad_lord"] if cur else md
    boney_period = score_active_period(md, ad_lord, v.pc)
    boney_block = render_boney_period_block(boney_period)

    gk_synergy = score_transit_dasha_synergy(md=md, ad=ad_lord, pc=v.pc, target=today)
    dob_s = v.pc.get("meta", {}).get("dob", "")
    birth_year = _pd(dob_s).year if dob_s else today.year - v.age
    gk_block = render_gk_transit_dasha_block(
        gk_synergy,
        upcoming_eventful_years(v.pc, birth_year),
    )

    body = f"""
  <article class="card">
    <h1 style="color:var(--heading);">Your life reading - Vimshottari Dasha</h1>
    <dl class="meta">
      <dt>Client</dt><dd>{nm}</dd>
      <dt>Born</dt><dd>{_e(dob_disp)}{('  |  ' + _e(tob)) if tob else ''}{('  |  ' + _e(place)) if place else ''}</dd>
      <dt>Lagna</dt><dd>{v.lagna}  |  age {v.age}</dd>
      <dt>Report date</dt><dd>{today.strftime('%d %B %Y').lstrip('0')}</dd>
    </dl>
    <p class="lead">This reading tracks <strong>which planet period you are in</strong> - the 120-year Vimshottari cycle.
    Each slice has a plain verdict: <span class="tag-good">Good phase</span>,
    <span class="tag-warn">Needs attention</span>, or <span class="tag-hard">Challenging</span>.
    Mehta Modern Techniques (rules4) adds house-lord depth; divisional sections (D7/D9/D10/D30) follow Goel;
    Boney rules45 cross-checks period lords in Navamsha and event vargas;
    GK rules11 pairs today's transits with your running MD-AD.</p>

    <div class="callout">{_snapshot(v)}</div>
    {boney_block}
    {gk_block}

    <h1>The chapter you are in (big picture)</h1>
    <p class="pred">The long <strong>{md}</strong> chapter runs <strong>{_dmy(_pd(v.cur_md['start']))} - {_dmy(_pd(v.cur_md['end']))}</strong>. {MAHA_PLAIN.get(md, '')}</p>
    <p class="pred">{_verdict_tag(_lord_verdict(v, md))} {_human_antar(v, md, md)}{_boney_lord_hint(v, md)}</p>

    <h1>Your timeline - what is coming</h1>
    <p class="pred">Each row is an antardasa within your current mahadasa - when the planet touches money, love, or work houses, that theme gets louder.</p>
    {_timeline(v)}

    <h1>Recent past</h1>
    {_recent_past(v) or '<p class="pred">No recent antardasas in window.</p>'}

    <h1>Right now ({today.strftime('%d %B %Y').lstrip('0')})</h1>
    <p class="pred">{((_verdict_tag(_lord_verdict(v, cur['ad_lord'])) + ' You are in <strong>' + md + '-' + cur['ad_lord'] + '</strong> until <strong>' + _dmy(_pd(cur['end'])) + '</strong>. ' + _human_antar(v, cur['ad_lord'], md) + _boney_lord_hint(v, cur['ad_lord'])) if cur else 'Current antardasa not parsed.')}</p>

    <h1>Near future</h1>
    {_future_paras(v) or '<p class="pred">No future antardasas parsed.</p>'}

    <h1>Who you are underneath</h1>
    {_personality_section(v)}

    <h1>Job &amp; career</h1>
    {_domain_section(v, 'career', 'No strong career antardasa sits immediately ahead - steady skill-building still counts.', boney_period)}

    <h1>Marriage &amp; partnership</h1>
    {_domain_section(v, 'marriage', 'No dominant love window is right around the corner - daily honesty still moves things forward.', boney_period)}

    <h1>Children &amp; creativity</h1>
    {_domain_section(v, 'children', 'No urgent child-or-creative window is flagged - patience and small steps still add up.', boney_period)}

    <h1>Wealth &amp; joint resources</h1>
    {_domain_section(v, 'wealth', 'No standout money slice is immediate - steady habits matter more than timing right now.')}

    <h1>Health &amp; energy</h1>
    {_domain_section(v, 'health', 'No acute health-flag slice is next - keep sleep, meals, and check-ups sensible anyway.')}
    <p class="note">Educational only - see a doctor for symptoms.</p>

    <h1>Growth, mentors &amp; support</h1>
    {_domain_section(v, 'growth', 'Growth comes through steady conduct until a Jupiter or Venus window opens.')}

    {mehta_block}

    <h1>Remedies - simple weekly habits</h1>
    {_remedies_section(v)}

    {d10_block}
    {d9_block}
    {d30_block}
    {d7_block}

    <p class="note">Your Jaimini, Yogini, or KP report may name different timings - that is normal.
    Use Vimshottari for <strong>mahadasa/antardasa precision</strong>; Mehta for <strong>house-lord themes</strong>; D7/D9/D10/D30 for life-area depth.</p>

    {_appendix(v, vargas, mehta_chart)}

    <p class="note">Educational astrology only. Sources: Laghu Parashari; Mehta Modern Techniques (rules4); Goel - Saptamsha, Navamsha, Dashamsha, Trimshamsha; Boney - Intricate Patterns of Destiny (rules45); GK - Planetary Transit and Dasa Period (rules11).
    Pratyantar dates are computed from standard proportions. This report does not diagnose illness or predict death.</p>
  </article>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Vimshottari + Mehta reading - {nm}</title>
<style>{_css()}</style></head><body>{body}</body></html>"""


def generate_vimshottari_html(
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
    v = Vim(pc)
    d = datetime.strptime(dob, "%Y-%m-%d").date()
    vargas = vargas_from_precompute(pc)
    if not vargas.get("D7") and extracted_path and Path(extracted_path).exists():
        vargas = parse_shodashvarga(Path(extracted_path).read_text(encoding="utf-8", errors="ignore"))
    female = female_from_pc(pc)
    mehta_chart = build_mehta_chart(pc)
    doc = render(v, d.strftime("%d %B %Y").lstrip('0'), tob, place, vargas, female, mehta_chart)
    cur_ad = next((a for a in v.antars if a.get("status") == "current"), None)
    summary = {
        "lagna": v.lagna,
        "current_md": v.cur_md["md_lord"],
        "current_ad": cur_ad["ad_lord"] if cur_ad else None,
        "md_period": f"{v.cur_md['start'][:7]}..{v.cur_md['end'][:7]}",
        "d7_lagna": vargas.get("D7").lagna if "D7" in vargas else None,
        "d9_lagna": vargas.get("D9").lagna if "D9" in vargas else None,
        "d10_lagna": vargas.get("D10").lagna if "D10" in vargas else None,
        "d30_lagna": vargas.get("D30").lagna if "D30" in vargas else None,
        "mehta_merged": mehta_chart is not None,
    }
    return doc, summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Deterministic Vimshottari report (no LLM)")
    ap.add_argument("name")
    ap.add_argument("dob")
    ap.add_argument("extracted", nargs="?", default=None, help="Optional legacy AstroSage extract")
    add_chart_source_args(ap)
    ap.add_argument("--tob", default="")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    kw = chart_kwargs_from_args(args)
    doc, summary = generate_vimshottari_html(
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
    out = Path(args.out) if args.out else BASE_DIR / "reports" / f"Vedic_Vimshottari_{args.name}_preview.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(f"MD={summary['current_md']} AD={summary['current_ad']} ({summary['md_period']})")
    print(f"D7={summary.get('d7_lagna')} D9={summary.get('d9_lagna')} D10={summary.get('d10_lagna')} D30={summary.get('d30_lagna')}")
    print(f"written → {out}")


if __name__ == "__main__":
    main()
