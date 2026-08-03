#!/usr/bin/env python3
"""
vedic_yogini_report.py — Deterministic Yogini Dasha report (NO LLM).

Replaces the Cursor Yogini lane. The Yogini Dasha is a 36-year, Moon-naksatra
based cycle of eight Yogini lords. This engine:

  * PARSES the authoritative Yogini Dasha tables straight from the AstroSage
    extract (mahadasa from/to dates + the sub-period end-dates of the running
    mahadasa). The extract is treated as ground truth — this avoids the
    precompute's birth-Yogini bug (it reported Bhadrika; for Moon in Hasta the
    correct birth Yogini is Sankata, which the extract confirms).
  * Recomputes whole-sign houses from sign + Lagna (precompute's stored ``house``
    is unreliable for Saturn-ruled placements).
  * Writes prediction-first, dated, book-backed natural language for the current
    and upcoming periods, fusing each Yogini lord's classical signification with
    that planet's actual house rulership and placement in THIS chart.

Sources: Goel — *Snapshot Prediction Using Yogini Dasha* (Sagar, 2013);
Goel — *New Research in Timing of Events Using Chara & Yogini Dasha* (Saptarishis).

Fully offline and reproducible — no model, no network.
"""
from __future__ import annotations

import argparse
import html
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from astro_precompute import resolve_precompute
from chart_resolve import add_chart_source_args, chart_kwargs_from_args

BASE_DIR = Path(__file__).resolve().parent
GOLD = BASE_DIR / "reports" / "Vedic_Yogini_Ritz_20260408.html"

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
DIGNITY_WORD = {"exalted": "exalted", "moolatrikona": "in moolatrikona", "own_sign": "in its own sign",
                "debilitated": "debilitated", "neutral_sign": "neutral", "friend_sign": "in a friend's sign",
                "enemy_sign": "in an enemy's sign", "great_friend_sign": "in a great friend's sign"}

NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu",
              "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta",
              "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
              "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
              "Uttara Bhadrapada", "Revati"]
# Yogini number 1..8 → name (1=Mangala ... 8=Sankata)
YOGINI_BY_NUM = {1: "Mangala", 2: "Pingala", 3: "Dhanya", 4: "Bhramari",
                 5: "Bhadrika", 6: "Ulka", 7: "Siddha", 8: "Sankata"}


def birth_yogini_from_nakshatra(nak: str) -> tuple[str, str]:
    """(name, lord) using the classical rule: (nakshatra_number + 3) mod 8 (0→8)."""
    base = nak.split("-")[0].strip()
    idx = next((i for i, n in enumerate(NAKSHATRAS) if n.lower().startswith(base.lower()[:5])), None)
    if idx is None:
        return ("—", "—")
    num = ((idx + 1 + 3) % 8) or 8
    name = YOGINI_BY_NUM[num]
    lord = next((v[1] for v in ABBR.values() if v[0] == name), "—")
    return (name, lord)


# Yogini abbreviation → (name, lord, years, tone)
ABBR = {
    "Ma": ("Mangala", "Moon", 1, "auspicious"),
    "Pi": ("Pingala", "Sun", 2, "mixed"),
    "Dh": ("Dhanya", "Jupiter", 3, "auspicious"),
    "Br": ("Bhramari", "Mars", 4, "mixed"),
    "Ba": ("Bhadrika", "Mercury", 5, "auspicious"),
    "Ul": ("Ulka", "Saturn", 6, "inauspicious"),
    "Si": ("Siddha", "Venus", 7, "auspicious"),
    "Sn": ("Sankata", "Rahu", 8, "inauspicious"),
}
# Classical signification of each Yogini (Goel / Mahadeva tradition)
YOGINI_CLASSICAL = {
    "Mangala": "auspicious ceremonies at home, family warmth, gain of conveyances and comforts, praise from authority",
    "Pingala": "honour and authority from superiors, status and recognition — but watch bilious/blood-related health and physical strain",
    "Dhanya": "the most benefic Yogini — gain of wealth and grains, happiness from spouse and children, dharmic acts, pilgrimage, relief from disease",
    "Bhramari": "restless energy, travel and movement, physical drive and competition — with risk of haste, friction or disputes",
    "Bhadrika": "rise in social status, success through intellect, education and communication, supportive friends",
    "Ulka": "hard, structured work and delays; fear around wealth or status; fatigue — a period that rewards patient consolidation",
    "Siddha": "fulfilment of desires, gain of wealth, fame and prosperity, comforts, marriage and foreign journeys",
    "Sankata": "sudden upheaval and transformation, foreign and unconventional currents, danger or loss if careless — yet a powerful reinvention window when handled wisely",
}
TONE_BADGE = {"auspicious": "badge-green", "mixed": "badge-amber", "inauspicious": "badge-red"}

PERIOD_PLAIN = {
    "Mangala": "A softer, home-centred spell — good for family time and nesting, not big gambles.",
    "Pingala": "You may feel more seen and tested — watch heat, pride, and blood-pressure habits.",
    "Dhanya": "One of the kinder slices — money, children, and fair dealing tend to open up.",
    "Bhramari": "Restless and competitive — put the energy into sport or a project, not arguments.",
    "Bhadrika": "Clever work and study pay off — exams, promotions, and networking all favour you.",
    "Ulka": "Heavy and slow — consolidate, serve well, and do not chase shortcuts.",
    "Siddha": "Wishes feel closer — love, comfort, travel, and visible gains are in the air.",
    "Sankata": "Life can shift fast — foreign pulls, reinvention, and staying legal matter most.",
}

MAHA_PLAIN = {
    "Mangala": "Moon colours the background — feelings, mother, home, and public warmth.",
    "Pingala": "Sun colours the background — authority, honour, and a watch on heat and blood.",
    "Dhanya": "Jupiter colours the background — wealth, children, teachers, and dharmic acts.",
    "Bhramari": "Mars colours the background — travel, drive, friction, and physical push.",
    "Bhadrika": "Mercury colours the background — study, career skills, business, and social rise.",
    "Ulka": "Saturn colours the background — duty, fatigue, and slow solid results.",
    "Siddha": "Venus colours the background — marriage, comfort, foreign journeys, and fulfilled wishes.",
    "Sankata": "Rahu colours the background — upheaval, tech, foreign links, and unconventional paths.",
}

LORD_VOICE = {
    "Moon": "feelings and home life set the tone",
    "Sun": "visibility and authority are louder than usual",
    "Mars": "drive and friction need a healthy outlet",
    "Mercury": "paperwork, study, and quick deals pick up",
    "Jupiter": "luck, teachers, and fair dealing help",
    "Venus": "love, comfort, and enjoying what you earn feel natural",
    "Saturn": "patience and discipline matter more than speed",
    "Rahu": "restless change and unconventional moves tempt you",
}

DOMAIN_LEAD = {
    "wealth": "Money moves in waves in your chart — the Yogini clock shows when to save and when to spend.",
    "career": "Work and reputation do not rise on the same schedule every year — these slices show when to push.",
    "marriage": "Partnership has its own rhythm — some slices open the door to love, others ask for patience.",
    "children": "Family, romance, and creative projects share the same emotional lane — timing helps.",
    "health": "Your chart flags when routine slips hurt most — prevention beats crisis fixes.",
    "growth": "Luck, mentors, study, and travel can lift you when other areas feel stuck.",
}

# Domain × Yogini flavour — keeps each dated row distinct.
DOMAIN_SLICE = {
    ("wealth", "Mangala"): "Family money and household spending need a gentle budget — save what comes in easily.",
    ("wealth", "Pingala"): "Income may rise with status — bank the good months before lifestyle creeps up.",
    ("wealth", "Dhanya"): "A strong money slice — debts clear faster and savings can grow if you let them.",
    ("wealth", "Bhramari"): "Impulse buys and competitive spending are the trap — pause before big purchases.",
    ("wealth", "Bhadrika"): "Clever deals, side income, and paperwork wins — organise accounts now.",
    ("wealth", "Ulka"): "Cash flow feels tight — trim one expense and finish an old financial loose end.",
    ("wealth", "Siddha"): "Comfort and gains arrive together — enjoy, but keep one month's reserve untouched.",
    ("wealth", "Sankata"): "Sudden swings in income or expenses — avoid speculation; keep paperwork clean.",
    ("career", "Mangala"): "Work and home pull at each other — protect focus, but do not ignore family.",
    ("career", "Pingala"): "Bosses and visibility matter — one bold pitch or presentation can land well.",
    ("career", "Dhanya"): "Mentors and fair dealing open doors — say yes to learning, not office politics.",
    ("career", "Bhramari"): "Competition is high — channel rivalry into results, not arguments.",
    ("career", "Bhadrika"): "Skills and communication shine — update your CV, sit an exam, or close a deal.",
    ("career", "Ulka"): "Slow climb — reliability and service beat chasing a fast promotion.",
    ("career", "Siddha"): "Recognition and comfort rise — ask for credit if you have earned it.",
    ("career", "Sankata"): "Role or workplace may shift — stabilise one income stream before you leap.",
    ("marriage", "Mangala"): "Warmth at home helps love — small rituals and family inclusion matter.",
    ("marriage", "Pingala"): "Ego clashes can strain partnership — lead with respect, not pride.",
    ("marriage", "Dhanya"): "A generous spell for commitment — honest talks about the future land well.",
    ("marriage", "Bhramari"): "Passion runs hot — cool down before you say something you cannot unsay.",
    ("marriage", "Bhadrika"): "Words matter — a clear conversation beats guessing what the other person wants.",
    ("marriage", "Ulka"): "Distance or duty can feel heavy — patience and small kindnesses carry you through.",
    ("marriage", "Siddha"): "One of the best slices for love and harmony — plan time together properly.",
    ("marriage", "Sankata"): "Partnership may feel unsettled — do not make permanent decisions in a panic.",
    ("children", "Mangala"): "Nesting and family warmth support children or a creative home project.",
    ("children", "Pingala"): "Confidence in creative work rises — share what you make, gently.",
    ("children", "Dhanya"): "Fertility and creative joy are favoured — patience still beats forcing outcomes.",
    ("children", "Bhramari"): "Restless energy around family — channel it into play or a hands-on project.",
    ("children", "Bhadrika"): "Study, writing, or teaching children flows well — keep expectations realistic.",
    ("children", "Ulka"): "Delays around family plans — steady effort matters more than perfect timing.",
    ("children", "Siddha"): "Romance, art, and family pleasure blend — a sweet spell for creative joy.",
    ("children", "Sankata"): "Family rhythm may change — stay flexible and keep communication gentle.",
    ("health", "Mangala"): "Emotional eating and sleep habits need watching — calm evenings help.",
    ("health", "Pingala"): "Heat, blood pressure, and burnout risk — hydrate, rest, and ease off ego battles.",
    ("health", "Bhadrika"): "Nervous tension and screen strain build — step away, stretch, and breathe.",
    ("health", "Bhramari"): "Accidents and inflammation rise with haste — warm up, cool down, slow down.",
    ("health", "Ulka"): "Fatigue, joints, and teeth need care — book the check-up you have been putting off.",
    ("health", "Dhanya"): "Recovery and routine improve — good window to fix diet and sleep properly.",
    ("health", "Siddha"): "Body and pleasure align — enjoy, but do not skip the basics.",
    ("health", "Sankata"): "Stress shows in odd symptoms — cut one draining habit and rest more.",
    ("growth", "Mangala"): "Home, mother, or inner peace teach you something useful now.",
    ("growth", "Pingala"): "A mentor or authority figure may open a door — show up prepared.",
    ("growth", "Dhanya"): "Teachers, travel, and fair dealing lift you — say yes to clean growth.",
    ("growth", "Bhramari"): "Short trips and bold effort teach fast — pick one path and commit.",
    ("growth", "Bhadrika"): "Study, writing, and skill-building pay off — enrol or finish the course.",
    ("growth", "Ulka"): "Growth through service and patience — the lesson is discipline, not speed.",
    ("growth", "Siddha"): "Foreign links, art, and fulfilled wishes widen your world.",
    ("growth", "Sankata"): "Unconventional paths tempt you — research first, then move once grounded.",
}

DOMAIN_REMEDY = {
    "wealth": "Pick one savings rule for this slice — auto-transfer on payday or clear one old due.",
    "career": "Each week, finish one visible task before chasing the next big idea.",
    "marriage": "One honest conversation without phones — say what you need, hear what they need.",
    "children": "Protect creative or family time on the calendar like a real appointment.",
    "health": "Sleep and meals before supplements — book prevention, not crisis fixes.",
    "growth": "Say yes to one mentor, trip, or course that feels clean — skip the shiny distraction.",
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

# Goel rules9 §5 — key MD/antar combinations (timing texture)
SUB_COMBO = {
    ("Mangala", "Siddha"): "Home feels sweeter — partner, children, and small luxuries lift the mood.",
    ("Mangala", "Ulka"): "Money or status wobble — keep calm with bosses and protect savings.",
    ("Bhadrika", "Siddha"): "Celebrations at home are likely — relatives and children bring joy.",
    ("Bhadrika", "Ulka"): "People friction or job worry — do not quit in haste.",
    ("Ulka", "Siddha"): "Mixed spell — travel and comfort tempt you; watch overspending.",
    ("Ulka", "Sankata"): "Fear and strain build — protect partner, elders, and emergency cash.",
    ("Siddha", "Mangala"): "Pleasure and success blend — authority and comfort can rise together.",
    ("Siddha", "Siddha"): "Wishes tend to land — children, friends, and comforts increase.",
    ("Siddha", "Sankata"): "Heavy workload or distance — money worry and possible move abroad.",
    ("Siddha", "Ulka"): "Savings can drain — health and routine need extra care.",
    ("Sankata", "Sankata"): "The toughest mix — upheaval, loss risk, and possible forced relocation.",
    ("Sankata", "Ulka"): "Sudden money or career fear — tighten the budget and avoid panic moves.",
    ("Sankata", "Siddha"): "Could be a penalty, theft scare, or foreign posting — check every document.",
    ("Sankata", "Dhanya"): "Stomach or stress friction possible, yet children and home fame can still rise.",
}

DOMAIN_HOUSES = {
    "wealth": {2, 11}, "career": {10, 6}, "marriage": {7, 2},
    "children": {5, 2}, "health": {6, 8, 12}, "growth": {9, 3, 12},
}

DOMAIN_YOGINI = {
    "wealth": {"Dhanya", "Siddha", "Bhadrika"},
    "career": {"Bhadrika", "Ulka", "Sankata"},
    "marriage": {"Siddha", "Mangala"},
    "children": {"Dhanya", "Siddha"},
    "health": {"Pingala", "Ulka", "Bhramari"},
    "growth": {"Dhanya", "Siddha", "Sankata"},
}


def _e(s) -> str:
    return html.escape(str(s))


def _ord(n) -> str:
    n = int(n)
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th"))


def house_of(sign: str, lagna: str) -> int:
    return (SIGNS.index(sign) - SIGNS.index(lagna)) % 12 + 1


def _pdate(raw: str, dob: date) -> date | None:
    """Parse 'd/ m/ yy' (AstroSage) with century anchoring relative to DOB."""
    raw = raw.replace(" ", "")
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", raw)
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 100:
        # pick the smallest century candidate that is not before the birth year
        cands = [1900 + y, 2000 + y, 2100 + y]
        y = next((c for c in cands if c >= dob.year), cands[-1])
    try:
        return date(y, mo, d)
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Parser — read Yogini MD timeline + running-MD sub-periods from the extract
# ─────────────────────────────────────────────────────────────────────────────
def _clean_md_subs(md: dict) -> None:
    """Drop corrupt sub end-dates; keep only monotonic subs inside the mahadasa."""
    if not md.get("start") or not md.get("end"):
        md["subs"] = []
        return
    prev = md["start"]
    clean = []
    for abbr, end in md.get("subs", []):
        if not end or end <= prev or end > md["end"] + timedelta(days=5):
            continue
        clean.append((abbr, end))
        prev = end
    md["subs"] = clean


def _prune_mds_chain(mds: list[dict], dob: date) -> list[dict]:
    """Keep one contiguous birth-anchored chain — not duplicate 36-year cycles."""
    valid = [m for m in mds if m.get("start") and m.get("end") and m["start"] < m["end"]]
    if not valid:
        return []
    anchor = min(
        (m for m in valid if m["start"] <= dob + timedelta(days=800)),
        key=lambda m: abs((m["start"] - dob).days),
        default=min(valid, key=lambda m: m["start"]),
    )
    chain = [anchor]
    while chain[-1].get("end"):
        end = chain[-1]["end"]
        nxt = next(
            (m for m in valid
             if m["start"] not in {c["start"] for c in chain}
             and abs((m["start"] - end).days) <= 5),
            None,
        )
        if not nxt:
            later = [m for m in valid if m["start"] > end and m["start"] not in {c["start"] for c in chain}]
            if not later:
                break
            nxt = min(later, key=lambda m: m["start"])
            if (nxt["start"] - end).days > 30:
                break
        chain.append(nxt)
        if chain[-1]["start"].year > dob.year + 95:
            break
    return chain


def parse_yogini(text: str, dob: date) -> dict:
    starts = [m.start() for m in re.finditer(r"\|\|\s*Yogini Dasha\s*\|\|", text)]
    if not starts:
        return {"mds": [], "current": None}
    # First two Yogini pages only — later pages repeat future 36-year cycles.
    end_pos = starts[2] if len(starts) > 2 else starts[0] + 4500
    region = text[starts[0]:end_pos]
    lines = region.split("\n")
    raw_mds: list[dict] = []
    i = 0
    head_re = re.compile(r"\b(Sn|Ma|Pi|Dh|Br|Ba|Ul|Si)\s+(\d+)\s+Years")
    from_re = re.compile(r"From\s+(\d{1,2}/\s*\d{1,2}/\s*\d{2,4})")
    to_re = re.compile(r"To\s+(\d{1,2}/\s*\d{1,2}/\s*\d{2,4})")
    sub_re = re.compile(r"\b(Sn|Ma|Pi|Dh|Br|Ba|Ul|Si)\s+(\d{1,2}/\s*\d{1,2}/\s*\d{2,4})")
    while i < len(lines):
        heads = [(m.group(1), m.start(), int(m.group(2))) for m in head_re.finditer(lines[i])]
        if heads and i + 2 < len(lines) and "From" in lines[i + 1] and "To" in lines[i + 2]:
            froms = [(m.start(), m.group(1)) for m in from_re.finditer(lines[i + 1])]
            tos = [(m.start(), m.group(1)) for m in to_re.finditer(lines[i + 2])]
            # collect sub-period lines until a blank/next-header row
            sub_lines = []
            j = i + 3
            while j < len(lines) and lines[j].strip() and not head_re.search(lines[j]) \
                    and "AstroSage" not in lines[j] and "Yogini" not in lines[j]:
                sub_lines.append(lines[j])
                j += 1
            for abbr, hoff, yrs in heads:
                frm = min(froms, key=lambda f: abs(f[0] - hoff)) if froms else None
                to = min(tos, key=lambda t: abs(t[0] - hoff)) if tos else None
                subs = []
                for sl in sub_lines:
                    cands = [(m.start(), m.group(1), m.group(2)) for m in sub_re.finditer(sl)]
                    if not cands:
                        continue
                    best = min(cands, key=lambda c: abs(c[0] - hoff))
                    if abs(best[0] - hoff) < 26:
                        subs.append((best[1], _pdate(best[2], dob)))
                name, lord, ylen, tone = ABBR[abbr]
                raw_mds.append({
                    "abbr": abbr, "yogini": name, "lord": lord, "years": yrs, "tone": tone,
                    "start": _pdate(frm[1], dob) if frm else None,
                    "end": _pdate(to[1], dob) if to else None,
                    "subs": subs,
                })
            i = j
        else:
            i += 1
    # dedupe by start date, keep ordered
    seen = {}
    for m in raw_mds:
        if m["start"] and m["start"] not in seen:
            seen[m["start"]] = m
    mds = _prune_mds_chain(sorted(seen.values(), key=lambda m: m["start"]), dob)
    for m in mds:
        _clean_md_subs(m)
    today = date.today()
    current = next((m for m in mds if m["start"] <= today < m["end"]), None)
    return {"mds": mds, "current": current}


NAME_TO_ABBR = {v[0]: k for k, v in ABBR.items()}
YOGINI_ORDER = ["Ma", "Pi", "Dh", "Br", "Ba", "Ul", "Si", "Sn"]


def _parse_iso_date(val) -> date | None:
    if isinstance(val, date):
        return val
    if not val:
        return None
    try:
        return date.fromisoformat(str(val)[:10])
    except ValueError:
        return None


def _subs_for_md(md_start: date, md_end: date, md_yogini: str) -> list[tuple[str, date]]:
    abbr = NAME_TO_ABBR.get(md_yogini)
    if not abbr or md_start >= md_end:
        return []
    idx = YOGINI_ORDER.index(abbr)
    order = YOGINI_ORDER[idx:] + YOGINI_ORDER[:idx]
    total_days = (md_end - md_start).days
    if total_days <= 0:
        return []
    subs: list[tuple[str, date]] = []
    cur = md_start
    for sub_abbr in order:
        yrs = ABBR[sub_abbr][2]
        dur = max(1, round(total_days * yrs / 36.0))
        end = min(cur + timedelta(days=dur), md_end)
        subs.append((sub_abbr, end))
        cur = end
        if cur >= md_end:
            break
    if subs and subs[-1][1] < md_end:
        subs[-1] = (subs[-1][0], md_end)
    return subs


def yogini_from_precompute(pc: dict, dob: date) -> dict:
    """Build Yogini MD timeline + computed antars from precompute full_cycle."""
    cycle = pc.get("yogini", {}).get("full_cycle", [])
    mds: list[dict] = []
    for row in cycle:
        start = _parse_iso_date(row.get("start"))
        end = _parse_iso_date(row.get("end"))
        if not start or not end or start >= end:
            continue
        name = row.get("yogini", "")
        abbr = NAME_TO_ABBR.get(name, "")
        tone = row.get("tone", ABBR.get(abbr, ("", "", 0, "mixed"))[3])
        mds.append({
            "abbr": abbr,
            "yogini": name,
            "lord": row.get("lord", ABBR.get(abbr, ("", "", 0, ""))[1]),
            "years": row.get("years", ABBR.get(abbr, ("", "", 0, ""))[2]),
            "tone": tone,
            "start": start,
            "end": end,
            "subs": _subs_for_md(start, end, name),
        })
    for m in mds:
        _clean_md_subs(m)
    today = date.today()
    current = next((m for m in mds if m["start"] <= today < m["end"]), None)
    return {"mds": mds, "current": current}


# ─────────────────────────────────────────────────────────────────────────────
# Chart wrapper
# ─────────────────────────────────────────────────────────────────────────────
class Yogini:
    def __init__(self, pc: dict, text: str, dob: date):
        self.pc = pc
        self.dob = dob
        self.lagna = pc["meta"]["lagna_sign"]
        self.lagna_idx = SIGNS.index(self.lagna)
        self.name = pc["meta"]["client"]
        self.age = int(pc["meta"]["age"])
        self.moon_nak = pc["planets"]["Moon"].get("nakshatra", "")
        self.planets = {}
        for nm, v in pc["planets"].items():
            self.planets[nm] = {
                "sign": v["sign"], "degree": v.get("degree_in_sign", 0.0),
                "dignity": v.get("dignity", "neutral_sign"),
                "house": house_of(v["sign"], self.lagna),
                "retro": bool(v.get("retrograde", False)),
            }
        # which houses each planet rules
        self.rules = {p: [] for p in self.planets}
        for h in range(1, 13):
            sign = SIGNS[(self.lagna_idx + h - 1) % 12]
            lord = SIGN_LORD[sign]
            if lord in self.rules:
                self.rules[lord].append(h)
        self.birth_yogini, self.birth_lord = birth_yogini_from_nakshatra(self.moon_nak)
        if text and "Yogini Dasha" in text:
            parsed = parse_yogini(text, dob)
        else:
            parsed = yogini_from_precompute(pc, dob)
        self.mds = parsed["mds"]
        self.current = parsed["current"]

    def lord_touches(self, planet: str, houses: set[int]) -> bool:
        p = self.planets.get(planet)
        if not p:
            return False
        return p["house"] in houses or any(h in houses for h in self.rules.get(planet, []))

    def lord_route(self, planet: str) -> str:
        p = self.planets.get(planet)
        if not p:
            return "general life"
        ruled = self.rules.get(planet, [])
        bits = [f"{_ord(p['house'])} house ({HOUSE_THEME[p['house']]})"]
        if ruled:
            bits.append(f"rules {_ord(ruled[0])}" + (f" & {_ord(ruled[1])}" if len(ruled) > 1 else ""))
        return ", ".join(bits)


# ───────────────────────── prediction engine (human NL) ─────────────────────


def _verdict_tag(kind: str) -> str:
    labels = {
        "good": ("Good phase", "tag-good"),
        "attention": ("Needs attention", "tag-warn"),
        "hard": ("Challenging — pace yourself", "tag-hard"),
    }
    text, cls = labels.get(kind, ("Mixed", "tag-warn"))
    return f'<span class="{cls}">{text}</span>'


def _tone_verdict(tone: str) -> str:
    return {"auspicious": "good", "mixed": "attention", "inauspicious": "hard"}.get(tone, "attention")


def _sub_combo_note(md_name: str, sub_name: str) -> str:
    return SUB_COMBO.get((md_name, sub_name), "")


def _all_sub_windows(y: Yogini) -> list[dict]:
    out = []
    for md in y.mds:
        if not md.get("start") or not md.get("subs"):
            continue
        prev = md["start"]
        for abbr, end in md["subs"]:
            if not end or prev >= end:
                continue
            name, lord, _yl, tone = ABBR[abbr]
            out.append({
                "md": md, "abbr": abbr, "name": name, "lord": lord, "tone": tone,
                "start": prev, "end": end,
                "md_yogini": md["yogini"], "md_lord": md["lord"], "md_tone": md["tone"],
            })
            prev = end
    return out


def _lord_angle(y: Yogini, planet: str) -> str:
    """Short chart link in plain English."""
    p = y.planets.get(planet)
    if not p:
        return LORD_VOICE.get(planet, "")
    ruled = y.rules.get(planet, [])
    theme = HOUSE_THEME[p["house"]].split(",")[0]
    angle = LORD_VOICE.get(planet, f"{planet} sets the tone")
    if ruled:
        return f"{angle}, through your {_ord(p['house'])} house ({theme}) and {_ord(ruled[0])} house links"
    return f"{angle}, through your {_ord(p['house'])} house ({theme})"


def _period_plain(y: Yogini, w: dict, rich: bool = False) -> str:
    base = PERIOD_PLAIN.get(w["name"], YOGINI_CLASSICAL.get(w["name"], ""))
    parts = [base, _lord_angle(y, w["lord"]) + "."]
    combo = _sub_combo_note(w["md_yogini"], w["name"])
    if combo:
        parts.append(combo)
    if rich and w["md_yogini"] != w["name"]:
        parts.append(MAHA_PLAIN.get(w["md_yogini"], ""))
    return " ".join(p for p in parts if p)


def _human_slice(y: Yogini, w: dict, domain: str | None = None) -> str:
    """One conversational sentence for a sub-period row."""
    yog = w["name"]
    combo = _sub_combo_note(w["md_yogini"], yog)
    dom = DOMAIN_SLICE.get((domain, yog)) if domain else ""
    if dom:
        parts = [dom]
        if combo:
            parts.append(combo)
        else:
            p = y.planets.get(w["lord"])
            if p:
                parts.append(
                    f"In your chart, that runs through your {_ord(p['house'])} house "
                    f"({HOUSE_THEME[p['house']].split(',')[0]})."
                )
    else:
        parts = [PERIOD_PLAIN.get(yog, "")]
        if combo:
            parts.append(combo)
        angle = _lord_angle(y, w["lord"])
        if angle:
            parts.append(angle.capitalize() + ".")
    return " ".join(p for p in parts if p).strip()


def _domain_hit(y: Yogini, w: dict, domain: str) -> bool:
    if w["name"] in DOMAIN_YOGINI.get(domain, set()):
        return True
    return y.lord_touches(w["lord"], DOMAIN_HOUSES[domain])


def _domain_line(y: Yogini, w: dict, domain: str) -> str | None:
    if not _domain_hit(y, w, domain):
        return None
    label = f"{w['md_yogini'][:2]}–{w['name'][:2]}"
    return (
        f"<strong>{_fmt(w['start'])} → {_fmt(w['end'])} ({label}):</strong> "
        f"{_human_slice(y, w, domain)}"
    )


def _timing_plain(y: Yogini, domain: str, limit: int = 2) -> str:
    today = date.today()
    wins = []
    for w in _all_sub_windows(y):
        if w["end"] <= today or not _domain_hit(y, w, domain):
            continue
        wins.append(f"{_fmt(w['start'])} – {_fmt(w['end'])} ({w['name'][:2]})")
        if len(wins) >= limit:
            break
    if not wins:
        return ""
    return f" Worth watching: {', '.join(wins)}."


def _snapshot(y: Yogini) -> str:
    today = date.today()
    bits = [
        "<strong>Where you are now:</strong> Yogini tracks life in a <strong>36-year Moon cycle</strong> "
        "with short sub-slices — useful when you want dated timing, not just mood."
    ]
    cur_md = y.current
    if cur_md:
        bits.append(
            f"You are in the wider <strong>{cur_md['yogini']}</strong> chapter until "
            f"<strong>{_fmt(cur_md['end'])}</strong> — {MAHA_PLAIN.get(cur_md['yogini'], '')}"
        )
    for w in _all_sub_windows(y):
        if w["start"] <= today < w["end"]:
            bits.append(
                f"Right now it is <strong>{w['md_yogini']}–{w['name']}</strong> until "
                f"<strong>{_fmt(w['end'])}</strong> {_verdict_tag(_tone_verdict(w['tone']))}: "
                f"{_human_slice(y, w)}"
            )
            break
    bits.append(
        f"Your Moon in <strong>{y.moon_nak}</strong> starts the clock on "
        f"<strong>{y.birth_yogini}</strong> ({y.birth_lord})."
    )
    return " ".join(bits)


def _chart_support(y: Yogini) -> str:
    bits = []
    cur_md = y.current
    if cur_md:
        bits.append(
            f"{_verdict_tag(_tone_verdict(cur_md['tone']))} The background chapter is "
            f"<strong>{cur_md['yogini']}</strong> — {MAHA_PLAIN.get(cur_md['yogini'], '')}"
        )
    today = date.today()
    for w in _all_sub_windows(y):
        if w["start"] <= today < w["end"]:
            if _domain_hit(y, w, "marriage"):
                bits.append("Love and partnership are part of the current mix — small honest gestures help.")
            if _tone_verdict(w["tone"]) == "hard":
                bits.append("This is more a hold-steady spell than a time for risky leaps.")
            break
    good_ahead = next(
        (w for w in _all_sub_windows(y) if w["start"] > today and _tone_verdict(w["tone"]) == "good"), None
    )
    if good_ahead:
        bits.append(
            f"The tone eases into <strong>{good_ahead['name']}</strong> from {_fmt(good_ahead['start'])} — "
            f"a lighter slice ahead."
        )
    return " ".join(bits[:3]) if bits else "Timing here depends on which planet is running and which houses it touches."


def _timeline(y: Yogini, n: int = 5) -> str:
    today = date.today()
    rows = []
    for w in _all_sub_windows(y):
        if w["end"] < today:
            continue
        if len(rows) >= n:
            break
        label = "Now" if w["start"] <= today < w["end"] else ("Next" if len(rows) == 1 else "Later")
        cls = ' class="cur"' if label == "Now" else ""
        rows.append(
            f"<tr{cls}><td><strong>{label}</strong></td>"
            f"<td>{_fmt(w['start'])} – {_fmt(w['end'])}</td>"
            f"<td>{_verdict_tag(_tone_verdict(w['tone']))}</td>"
            f"<td><strong>{w['md_yogini'][:2]}–{w['name'][:2]}</strong> ({w['lord']}) — {_human_slice(y, w)}</td></tr>"
        )
    if not rows:
        return "<p class='pred'>Yogini sub-period dates not parsed from extract.</p>"
    return (
        "<table class='simple'><tr><th>When</th><th>Dates</th><th>Verdict</th><th>What it means for you</th></tr>"
        + "".join(rows) + "</table>"
    )


def _slice_block(y: Yogini, windows: list[dict], wrap: str) -> str:
    if not windows:
        return ""
    paras = []
    for w in windows:
        paras.append(
            f"<p class='pred'>{_verdict_tag(_tone_verdict(w['tone']))} "
            f"<strong>{_fmt(w['start'])} → {_fmt(w['end'])} ({w['md_yogini'][:2]}–{w['name'][:2]}):</strong> "
            f"{_human_slice(y, w)}</p>"
        )
    return f"<div class='{wrap}'>" + "".join(paras) + "</div>"


def _recent_past(y: Yogini, n: int = 4) -> str:
    today = date.today()
    cut = today - timedelta(days=365 * 12)
    past = [
        w for w in _all_sub_windows(y)
        if w["start"] < w["end"] and cut <= w["end"] <= today
    ][-n:]
    return _slice_block(y, past, "callout-past")


def _future_paras(y: Yogini, n: int = 3) -> str:
    today = date.today()
    fut = [w for w in _all_sub_windows(y) if w["start"] > today][:n]
    body = _slice_block(y, fut, "callout-future")
    nxt_md = next((m for m in y.mds if m.get("start") and y.current and m["start"] >= y.current["end"]), None)
    if nxt_md:
        body += (
            f"<p class='pred'><strong>From {_fmt(nxt_md['start'])}:</strong> next mahadasa "
            f"<strong>{nxt_md['yogini']}</strong> ({nxt_md['lord']}) — "
            f"{MAHA_PLAIN.get(nxt_md['yogini'], '')}</p>"
        )
    return body


def _personality_section(y: Yogini) -> str:
    moon = y.planets.get("Moon", {})
    v = "good" if moon.get("dignity") in ("exalted", "own_sign", "moolatrikona") else "attention"
    moon_theme = HOUSE_THEME.get(moon.get("house", 1), "inner security").split(",")[0]
    return (
        f"<p class='pred'>{_verdict_tag(v)} Your emotional baseline comes from Moon in "
        f"<strong>{y.moon_nak}</strong>, which starts Yogini on <strong>{y.birth_yogini}</strong> "
        f"({y.birth_lord}). Feelings tend to show up around {moon_theme}.</p>"
        f"<p class='pred'>The same Yogini name returns every 36 years, but it never feels identical — "
        f"the running planet's house links change the flavour each time.</p>"
    )


def _domain_section(y: Yogini, domain: str, fallback: str) -> str:
    today = date.today()
    cur_w = next((w for w in _all_sub_windows(y) if w["start"] <= today < w["end"]), None)
    tag = _verdict_tag(
        _tone_verdict(cur_w["tone"]) if cur_w and _domain_hit(y, cur_w, domain) else "attention"
    )
    parts = [f"<p class='pred'>{tag} {DOMAIN_LEAD[domain]}{_timing_plain(y, domain)}</p>"]
    hits = []
    for w in _all_sub_windows(y):
        if w["end"] <= today or w["start"] >= w["end"]:
            continue
        line = _domain_line(y, w, domain)
        if line:
            hits.append(f"<p class='pred'>{_verdict_tag(_tone_verdict(w['tone']))} {line}</p>")
    if hits:
        parts.extend(hits[:4])
    else:
        parts.append(f"<p class='pred'>{_verdict_tag('attention')} {fallback}</p>")
    parts.append(f"<p class='pred'><strong>Simple habit:</strong> {DOMAIN_REMEDY[domain]}</p>")
    lord = cur_w["lord"] if cur_w else (y.current or {}).get("lord")
    if lord in PLANET_REMEDY and _domain_hit(y, cur_w, domain) if cur_w else False:
        parts.append(f"<p class='pred'><strong>Planet note ({lord}):</strong> {PLANET_REMEDY[lord]}</p>")
    return "".join(parts)


def _growth_section(y: Yogini) -> str:
    return _domain_section(y, "growth", "Growth comes through steady conduct until a Siddha or Dhanya window opens.")


def _remedies_section(y: Yogini) -> str:
    seen, items = set(), []
    today = date.today()
    cur_w = next((w for w in _all_sub_windows(y) if w["start"] <= today < w["end"]), None)
    for p in ((cur_w or {}).get("lord"), (cur_w or {}).get("md_lord"), y.birth_lord):
        if p and p in PLANET_REMEDY and p not in seen:
            seen.add(p)
            label = " (active sub)" if p == (cur_w or {}).get("lord") else ""
            items.append(f"<li><strong>{p}</strong>{label}: {PLANET_REMEDY[p]}</li>")
    items.append("<li>Keep agreements written — honest dealing protects luck more than rituals alone.</li>")
    items.append("<li>During Sankata or Ulka slices, trim one draining habit; finish one old pending task.</li>")
    return "<ul>" + "".join(items[:6]) + "</ul>"


def _appendix(y: Yogini) -> str:
    rows = []
    today = date.today()
    for w in _all_sub_windows(y):
        if w["start"].year < y.dob.year:
            continue
        if w["start"].year > y.dob.year + y.age + 25:
            continue
        cur = ' class="cur"' if w["start"] <= today < w["end"] else ""
        rows.append(
            f"<tr{cur}><td>{w['md_yogini'][:2]}–{w['name'][:2]}</td><td>{w['lord']}</td>"
            f"<td>{_fmt(w['start'])} – {_fmt(w['end'])}</td>"
            f"<td>{PERIOD_PLAIN.get(w['name'], '')[:60]}…</td></tr>"
        )
    tbl = (
        "<table class='simple'><tr><th>Sub-period</th><th>Lord</th><th>Dates</th><th>Theme</th></tr>"
        + "".join(rows[:40]) + "</table>"
    )
    md_rows = "".join(
        f"<tr><td>{m['yogini']}</td><td>{m['lord']}</td><td>{m['years']}yr</td>"
        f"<td>{_fmt(m['start'])} – {_fmt(m['end'])}</td></tr>"
        for m in y.mds if m.get("start") and m.get("end")
    )
    return f"""<details class='appendix'><summary>Yogini chart facts (technical)</summary>
<h2>Mahadasa timeline</h2><table class='simple'><tr><th>Yogini</th><th>Lord</th><th>Years</th><th>Dates</th></tr>{md_rows}</table>
<h2>Sub-period windows (parsed)</h2>{tbl}
<p class='fine'>Birth Yogini: {y.birth_yogini} ({y.birth_lord}) from Moon nakshatra {y.moon_nak}.</p>
</details>"""


# ─────────────────────────────────────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────────────────────────────────────
def _fmt(d: date | None) -> str:
    return d.strftime("%d %b %Y").lstrip('0') if d else "—"


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
        "h1{font-size:1.25rem;color:#006064;margin-top:1.5rem}" + tags
    )


def _current_sub_window(y: Yogini):
    today = date.today()
    return next((w for w in _all_sub_windows(y) if w["start"] <= today < w["end"]), None)


def render(y: Yogini, dob_disp: str, tob: str = "", place: str = "") -> str:
    nm = _e(y.name)
    today = date.today()
    cur_md = y.current
    cur_w = _current_sub_window(y)

    body = f"""
  <article class="card">
    <h1 style="color:var(--heading);">Your life reading — Yogini Dasha</h1>
    <dl class="meta">
      <dt>Client</dt><dd>{nm}</dd>
      <dt>Born</dt><dd>{_e(dob_disp)}{(' · ' + _e(tob)) if tob else ''}{(' · ' + _e(place)) if place else ''}</dd>
      <dt>Lagna</dt><dd>{y.lagna} · Moon {y.moon_nak} · birth Yogini {y.birth_yogini} ({y.birth_lord})</dd>
      <dt>Report date</dt><dd>{today.strftime('%d %B %Y').lstrip('0')}</dd>
    </dl>
    <p class="lead">This reading tracks <strong>which Yogini slice you are in</strong> — a 36-year Moon cycle broken into short dated windows.
    Each slice gets a plain verdict: <span class="tag-good">Good phase</span>,
    <span class="tag-warn">Needs attention</span>, or <span class="tag-hard">Challenging</span>.
    Dates come from your chart file; habits suggested here are simple and practical, not fear-based rituals.</p>

    <div class="callout">{_snapshot(y)}</div>

    <h1>The chapter you are in (big picture)</h1>
    <p class="pred">{('The long <strong>' + cur_md['yogini'] + '</strong> chapter (' + cur_md['lord'] + ') runs <strong>' + _fmt(cur_md['start']) + ' – ' + _fmt(cur_md['end']) + '</strong>. ' + MAHA_PLAIN.get(cur_md['yogini'], '')) if cur_md else 'Mahadasa data unavailable from the extract.'}</p>
    <p class="pred">{_chart_support(y)}</p>

    <h1>Your timeline — what is coming</h1>
    <p class="pred">Each row is a dated sub-slice — when the running planet links to money, love, or work houses, that life area gets louder.</p>
    {_timeline(y)}

    <h1>Recent past</h1>
    {_recent_past(y) or '<p class="pred">No recent slices parsed.</p>'}

    <h1>Right now ({today.strftime('%d %B %Y').lstrip('0')})</h1>
    <p class="pred">{((_verdict_tag(_tone_verdict(cur_w['tone'])) + ' You are in <strong>' + cur_w['md_yogini'] + '–' + cur_w['name'] + '</strong> until <strong>' + _fmt(cur_w['end']) + '</strong>. ' + _human_slice(y, cur_w)) if cur_w else 'Current sub-period not parsed.')}</p>

    <h1>Near future</h1>
    {_future_paras(y) or '<p class="pred">No future slices parsed.</p>'}

    <h1>Who you are underneath</h1>
    {_personality_section(y)}

    <h1>Job &amp; career</h1>
    {_domain_section(y, 'career', 'No strong career slice sits immediately ahead — steady skill-building still counts.')}

    <h1>Marriage &amp; partnership</h1>
    {_domain_section(y, 'marriage', 'No dominant love window is right around the corner — daily honesty still moves things forward.')}

    <h1>Children &amp; creativity</h1>
    {_domain_section(y, 'children', 'No urgent child-or-creative window is flagged — patience and small steps still add up.')}

    <h1>Wealth &amp; joint resources</h1>
    {_domain_section(y, 'wealth', 'No standout money slice is immediate — steady habits matter more than timing right now.')}

    <h1>Health &amp; energy</h1>
    {_domain_section(y, 'health', 'No acute health-flag slice is next — keep sleep, meals, and check-ups sensible anyway.')}
    <p class="note">Educational only — see a doctor for symptoms.</p>

    <h1>Growth, mentors &amp; support</h1>
    {_growth_section(y)}

    <h1>Remedies — simple weekly habits</h1>
    {_remedies_section(y)}

    <p class="note">Your Jaimini or Vimśottarī report may name different timings — that is normal.
    Use this report for <strong>sub-period event precision</strong>; use sign-based readings for life-season mood.</p>

    {_appendix(y)}

    <p class="note">Educational astrology only. Verify important dates in your software. This report does not diagnose illness or predict death.</p>
  </article>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Yogini reading — {nm}</title>
<style>{_css()}</style></head><body>{body}</body></html>"""

def generate_yogini_html(
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
    y = Yogini(pc, text, d)
    doc = render(y, d.strftime("%d %B %Y").lstrip('0'), tob, place)
    cur = y.current
    cur_w = _current_sub_window(y)
    summary = {
        "lagna": y.lagna, "moon_nakshatra": y.moon_nak,
        "birth_yogini": y.birth_yogini,
        "current_md": cur["yogini"] if cur else None,
        "current_md_lord": cur["lord"] if cur else None,
        "current_sub": cur_w["name"] if cur_w else None,
    }
    return doc, summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Deterministic Yogini Dasha report (no LLM)")
    ap.add_argument("name")
    ap.add_argument("dob")
    ap.add_argument("extracted", nargs="?", default=None, help="Optional legacy AstroSage extract")
    add_chart_source_args(ap)
    ap.add_argument("--tob", default="")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    kw = chart_kwargs_from_args(args)
    doc, summary = generate_yogini_html(
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
    out = Path(args.out) if args.out else BASE_DIR / "reports" / f"Vedic_Yogini_{args.name}_preview.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(f"birth_yogini={summary['birth_yogini']} current_md={summary['current_md']} "
          f"({summary['current_md_lord']}) sub={summary['current_sub']}")
    print(f"written → {out}")


if __name__ == "__main__":
    main()
