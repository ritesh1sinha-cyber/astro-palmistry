#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
naadi_recent.py - "What is on your mind now" and "What happened in the last six
months", read the Chandra Naadi way.

Method (chandra_naadi_analysis, Ch. 1 and the transit chapters):
  * The Moon is the daily trigger. Whichever natal planet the Moon touches (same
    sign, or the Moon's sign falls under that planet's aspect) is the planet whose
    themes are on the mind today.  -> `mind_now`
  * The slow planets (Saturn, Jupiter, Rahu, Ketu, Mars) set the climate for
    months. When one of them lands on, or aspects, a natal planet, that natal
    planet's themes come alive; the Moon's monthly pass over the same planet is
    the day it tends to come to a head.  -> `last_six_months`

Every fact is computed here in Python. The model (when on) only writes the
sentences; `_problems` rejects any line that invents a date, a planet or a jargon
word, and a plain deterministic version is used when the model is off or fails.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from astro_precompute import SIGN_LORDS, SIGNS, get_dignity, house_from_lagna, house_sign

try:                                       # the engine this module is built on
    import chandra_naadi_analysis as CN
except Exception:                          # noqa: BLE001
    CN = None

WINDOW_DAYS = 180
SLOW = ("Saturn", "Jupiter", "Rahu", "Ketu", "Mars")
_WEIGHT = {"Saturn": 5.0, "Jupiter": 4.0, "Rahu": 3.0, "Ketu": 3.0, "Mars": 2.0}

# ---- plain-language vocabulary -------------------------------------------------------------
HOUSE_AREA = {
    1: "yourself: energy, health habits and personal direction",
    2: "money in hand, family and what you say at home",
    3: "effort, short trips, calls, paperwork and siblings",
    4: "home, mother, property and peace of mind",
    5: "children, studies, creative work and matters of the heart",
    6: "daily workload, health routine, loans and small disputes",
    7: "partner, marriage and business partners",
    8: "sudden changes, shared money and hidden matters",
    9: "luck, father or mentors, travel and belief",
    10: "career, boss, status and public name",
    11: "income, gains, friends and long-held wishes",
    12: "expenses, sleep, time away from home and the inner life",
}
HOUSE_SHORT = {
    1: "self", 2: "money and family", 3: "effort and communication", 4: "home and peace of mind",
    5: "children and creativity", 6: "work routine and health", 7: "partnerships",
    8: "sudden change", 9: "luck and father", 10: "career", 11: "income and gains",
    12: "expenses and rest",
}
HOUSE_SCENES = {
    1: "how tired or energetic you feel, a change in routine or looks, a personal decision you have been avoiding",
    2: "money in hand, a family conversation, something you said and wish you had put differently",
    3: "phone calls and messages, paperwork or an agreement, a short trip, a brother or sister",
    4: "the mood at home, your mother, a property or vehicle matter, trouble switching off",
    5: "a child or a student's progress, a creative urge, a matter of the heart, a risky money idea",
    6: "a heavy workload, a health routine you keep skipping, a loan or EMI, a small argument at work",
    7: "your partner or a close business partner, a negotiation, feeling pulled between 'me' and 'we'",
    8: "an unexpected change, shared money or a hidden worry, wanting to know what is really going on",
    9: "your father or a mentor, a plan to travel or study, questioning what you believe or whether luck is with you",
    10: "your boss or work reputation, whether to switch jobs, a project that has to show results",
    11: "payments due or delayed, friends or contacts who can help, a long-held wish coming back to mind",
    12: "spending you did not plan, poor sleep, wanting time alone or away from home, a foreign link",
}
PLANET_STANDS_FOR = {
    "Sun": "authority, bosses, father and your standing",
    "Moon": "peace of mind, mother, money flow and travel",
    "Mars": "property, siblings, courage, drive and technical work",
    "Mercury": "deals, paperwork, studies and business talk",
    "Jupiter": "guidance, children, blessings and money advice",
    "Venus": "partner, comforts, vehicles and spending on pleasure",
    "Saturn": "duties, workload and long-term responsibility",
    "Rahu": "restless ambition, foreign links and online matters",
    "Ketu": "detachment, withdrawal and settling old matters",
}
PLANET_ACTS = {
    "Saturn": "slows things down, tests and asks for patience",
    "Jupiter": "widens, supports and brings advice and goodwill",
    "Rahu": "stirs restlessness, sudden interest and some confusion",
    "Ketu": "loosens the grip and pulls you towards stepping back",
    "Mars": "heats things up, pushes for speed and can bring friction",
}
_JARGON = re.compile(
    r"\b(nakshatra|bhava|drishti|dasha|antardasha|mahadasha|karaka|karaka|lagna|conjunct\w*|aspect\w*|"
    r"transit\w*|gochara|sade sati|naadi|chandrashtama|badhaka|ketu's|house \d+|\d+(st|nd|rd|th) house|"
    r"natal|lagnesh\w*|sidereal|ayanamsa|vimshottari|hyper-?focused|sovereignty|paradigm)\b", re.I)
_HEDGE = re.compile(
    r"\b(may|might|could|likely|probably|tends?|often|perhaps|chances|seems?|possibly|some days|"
    r"can feel|would)\b", re.I)
_DANGER = re.compile(
    r"\b(die|death|dead|cancer|tumou?r|surgery|accident|suicide|divorce|bankrupt\w*|fatal|"
    r"guarantee\w*|definitely|certainly|will lose|you will (lose|fail))\b", re.I)
_DATE_TOKEN = re.compile(
    r"\b\d{1,2}(?:\s*[-\u2013]\s*\d{1,2})?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
    r"(?:\s+\d{4})?\b|\b20\d\d\b", re.I)
_PLANET_NAMES = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")


def _d(x: date | datetime) -> str:
    return f"{x.day} {x.strftime('%b')}"


def _dy(x: date | datetime) -> str:
    return f"{x.day} {x.strftime('%b %Y')}"


def _pstr(n: Any) -> str:
    """Planet entry that may be a dict (md_lord) or a plain string."""
    if isinstance(n, dict):
        return str(n.get("md_lord") or n.get("lord") or "")
    return str(n or "")


# ---- chart helpers -------------------------------------------------------------------------
def _lagna(pc: dict) -> str:
    m = pc.get("meta") or {}
    raw = pc.get("lagna")
    return m.get("lagna_sign") or (raw if isinstance(raw, str) else (raw or {}).get("sign")) or "Aries"


def _owns(lagna: str, planet: str) -> list[int]:
    return [h for h in range(1, 13) if SIGN_LORDS.get(house_sign(h, lagna)) == planet]


def _at(d: date, hour_ut: float = 6.5) -> datetime:
    return datetime(d.year, d.month, d.day, int(hour_ut), int((hour_ut % 1) * 60))


def _positions(d: date) -> dict:
    return CN.get_transit_positions(_at(d)) if CN else {}


def _periods(pc: dict) -> tuple[str, str, Optional[str], Optional[date]]:
    vim = pc.get("vimshottari") or {}
    md = _pstr(vim.get("current_md")) or "Jupiter"
    ads = vim.get("current_md_antardashas") or []
    cur = next((a for a in ads if a.get("status") == "current"), {})
    ad = str(cur.get("ad_lord") or "")
    start = None
    try:
        start = datetime.strptime(str(cur.get("start") or "")[:10], "%Y-%m-%d").date()
    except ValueError:
        pass
    end = str(cur.get("end") or "")[:10] or None
    return md, ad, end, start


def _natal(pc: dict) -> dict:
    return pc.get("planets") or {}


def _contacts(pc: dict, planet: str, sign: str) -> list[dict]:
    """Natal planets this transiting planet sits on or aspects (Chandra Naadi 'connection')."""
    out = []
    for name, info in _natal(pc).items():
        ns = info.get("sign")
        if not ns or name == planet:
            continue
        if ns == sign:
            out.append({"planet": name, "kind": "sits on", "sign": ns, "house": info.get("house")})
        elif CN and CN.planet_aspects_sign(planet, sign, ns):
            out.append({"planet": name, "kind": "looks at", "sign": ns, "house": info.get("house")})
    return out


# ---- facts: mind now -----------------------------------------------------------------------
def _moon_leaves(d: date, now_t: datetime) -> date:
    here = CN.get_transit_positions(now_t).get("Moon", {}).get("sign")
    t = now_t
    for _ in range(40):                                  # 3-hour steps, a little over 5 days
        t += timedelta(hours=3)
        if CN.get_transit_positions(t).get("Moon", {}).get("sign") != here:
            return t.date()
    return (now_t + timedelta(days=2)).date()


def mind_facts(pc: dict, today: date, now_t: Optional[datetime] = None) -> dict:
    if CN is None:
        return {}
    if now_t is None:
        now_t = (datetime.now(timezone.utc).replace(tzinfo=None) if today == date.today() else _at(today))
    lagna = _lagna(pc)
    transit = CN.get_transit_positions(now_t)
    t_moon = (transit.get("Moon") or {}).get("sign")
    if not t_moon:
        return {}
    natal_moon = (_natal(pc).get("Moon") or {}).get("sign") or lagna
    h_lagna = house_from_lagna(t_moon, lagna)
    h_moon = house_from_lagna(t_moon, natal_moon)
    md, ad, end, _start = _periods(pc)
    lagna_lord = SIGN_LORDS.get(lagna, "")

    readings, connected = CN.analyze_core_methodology(pc, transit)
    kinds = {r.planets_involved[0]: ("sits on" if "Direct" in r.title else "looks at")
             for r in readings if r.planets_involved}
    ranked = []
    for p in connected:
        info = _natal(pc).get(p) or {}
        owns = _owns(lagna, p)
        score = (3.0 if kinds.get(p) == "sits on" else 1.5)
        score += 2.0 if p in (md, ad) else 0
        score += 1.5 if p == lagna_lord else 0
        score += 1.0 if (set(owns) & {10, 7, 2, 11, 4}) else 0
        ranked.append({
            "planet": p, "kind": kinds.get(p, "looks at"), "natal_sign": info.get("sign"),
            "natal_house": info.get("house"), "owns": owns,
            "stands_for": PLANET_STANDS_FOR.get(p, ""), "score": round(score, 2)})
    ranked.sort(key=lambda r: -r["score"])
    return {
        "moon_sign": t_moon, "moon_house": h_lagna, "moon_from_moon": h_moon,
        "moon_leaves": _moon_leaves(today, now_t),
        "contacts": ranked[:3], "md": md, "ad": ad, "ad_end": end,
        "chandrashtama": h_moon == 8,
    }


# ---- facts: the last six months ------------------------------------------------------------
def _segments(planet: str, days: list[tuple[date, dict]]) -> list[dict]:
    segs: list[dict] = []
    for d, pos in days:
        sign = (pos.get(planet) or {}).get("sign")
        if not sign:
            continue
        if segs and segs[-1]["sign"] == sign:
            segs[-1]["last"] = d
        else:
            segs.append({"planet": planet, "sign": sign, "first": d, "last": d})
    # drop retrograde blips (a few days back in the old sign) by merging short middle segments
    merged: list[dict] = []
    for i, s in enumerate(segs):
        if (s["last"] - s["first"]).days < 10 and 0 < i < len(segs) - 1:
            continue
        if merged and merged[-1]["sign"] == s["sign"]:
            merged[-1]["last"] = s["last"]
        else:
            merged.append(dict(s))
    return merged


def _moon_passes(pc: dict, natal_sign: str, days: list[tuple[date, dict]], inside: tuple[date, date]) -> list[str]:
    runs: list[tuple[date, date]] = []
    for d, pos in days:
        if not (inside[0] <= d <= inside[1]):
            continue
        if (pos.get("Moon") or {}).get("sign") == natal_sign:
            if runs and (d - runs[-1][1]).days <= 1:
                runs[-1] = (runs[-1][0], d)
            else:
                runs.append((d, d))
    out = []
    for a, b in runs[-3:]:
        out.append(_d(a) if a == b else f"{a.day}\u2013{b.day} {b.strftime('%b')}" if a.month == b.month
                   else f"{_d(a)} \u2013 {_d(b)}")
    return out


def past_facts(pc: dict, today: date) -> list[dict]:
    if CN is None:
        return []
    lagna = _lagna(pc)
    start = today - timedelta(days=WINDOW_DAYS)
    days = [(start + timedelta(days=i), None) for i in range((today - start).days + 1)]
    days = [(d, _positions(d)) for d, _ in days]
    days = [(d, p) for d, p in days if p]
    md, ad, _end, ad_start = _periods(pc)
    out: list[dict] = []

    # the sub-period change, if it fell inside the window: the one hard date in everyone's life
    if ad_start and start <= ad_start <= today:
        out.append({"kind": "period", "date": ad_start, "md": md, "ad": ad, "score": 6.0,
                    "stands_for": PLANET_STANDS_FOR.get(ad, "")})

    cand: list[dict] = []
    for planet in SLOW:
        for s in _segments(planet, days):
            house = house_from_lagna(s["sign"], lagna)
            contacts = _contacts(pc, planet, s["sign"])
            began = s["first"] > start
            ended = s["last"] < today
            dignity = get_dignity(planet, s["sign"])
            score = _WEIGHT[planet] + (3.0 if began else 0) + 0.7 * len(contacts)
            if dignity in ("exalted", "debilitated"):
                score += 1.0
            cand.append({
                "kind": "slow", "planet": planet, "sign": s["sign"], "house": house,
                "began": s["first"] if began else None, "ended": s["last"] if ended else None,
                "first": s["first"], "last": s["last"], "dignity": dignity,
                "contacts": contacts, "score": score,
                "acts": PLANET_ACTS.get(planet, ""), "area": HOUSE_AREA.get(house, ""),
            })
    cand.sort(key=lambda c: -c["score"])
    seen_planets: dict[str, int] = {}
    for c in cand:
        if seen_planets.get(c["planet"], 0) >= 1 or len([o for o in out if o["kind"] == "slow"]) >= 3:
            continue
        seen_planets[c["planet"]] = 1
        # the Moon's monthly pass over the main natal planet it touched: the days it came to a head
        sit = [x for x in c["contacts"] if x["kind"] == "sits on"] or c["contacts"]
        if sit:
            top = sit[0]
            c["main_contact"] = top
            c["trigger_days"] = _moon_passes(pc, top["sign"], days, (c["first"], c["last"]))
        out.append(c)

    out.sort(key=lambda c: c.get("began") or c.get("date") or c.get("first") or start)
    return out[:4]


# ---- paragraphs: facts written by Python, feeling written by the model ---------------------
# A small model restates and mis-attributes facts, so every sentence that carries a planet, a
# date or a sign is built here. The model only adds the human part: what it tends to feel like in
# daily life. Its sentences may not name a planet, a date or a month, so it cannot get one wrong.
_TONE = {
    "Saturn": "heavier and slower than usual",
    "Jupiter": "a little easier, with help turning up",
    "Rahu": "restless and unsettled",
    "Ketu": "distant, or hard to care about",
    "Mars": "hotter and more rushed than usual",
}
_TITLE = {
    "Saturn": "A heavier stretch around {a}",
    "Jupiter": "Support around {a}",
    "Rahu": "Restlessness around {a}",
    "Ketu": "Stepping back around {a}",
    "Mars": "A hotter stretch around {a}",
}


def _two(scenes: str) -> str:
    parts = [x.strip() for x in scenes.split(",") if x.strip()]
    return " and ".join(parts[:2])


PLANET_SCENES = {
    "Sun": "your boss's attitude, an official or government matter, your father, how recognised you feel",
    "Moon": "your mood, your mother, cash flow, a wish to travel",
    "Mars": "an argument you want to win, a property or sibling matter, a technical task, a burst of impatience",
    "Mercury": "an email or a contract, a study or exam decision, a business conversation",
    "Jupiter": "advice from an elder, a child, a loan or investment, a blessing you are waiting for",
    "Venus": "your partner, a purchase for comfort, a vehicle, an artistic itch",
    "Saturn": "a long-pending duty, a heavy workload, a responsibility you cannot hand over",
    "Rahu": "a sudden urge for something new, a foreign link, hours lost to screens",
    "Ketu": "wanting to withdraw, an old matter you want closed, losing interest in something",
}


def _scenes_for(c: dict) -> str:
    """Everyday scenes for a natal planet: its own, then the area it runs."""
    own = PLANET_SCENES.get(c.get("planet") or "", "")
    for h in list(c.get("owns") or [])[:1]:
        if HOUSE_SCENES.get(h):
            return f"{own}; also {HOUSE_SCENES[h]}" if own else HOUSE_SCENES[h]
    return own or HOUSE_SCENES.get(c.get("natal_house") or 0, "")


def mind_units(f: dict) -> list[dict]:
    if not f:
        return []
    cs = f["contacts"]
    units: list[dict] = []
    until = _d(f["moon_leaves"])
    if cs:
        c = cs[0]
        rel = "resting right on" if c["kind"] == "sits on" else "looking straight at"
        units.append({
            "title": "What your mind keeps returning to",
            "a": (f"For these couple of days, until about {until}, the Moon is {rel} your birth {c['planet']}, "
                  f"the part of you that carries {c['stands_for']}."),
            "b": "",
            "topic": f"{c['stands_for']}, showing up through {HOUSE_AREA.get(f['moon_house'], '')}",
            "nature": "weighing on your mind",
            "scenes": f"{PLANET_SCENES.get(c['planet'], '')}; around {HOUSE_SCENES.get(f['moon_house'], '')}",
            "fb": f"You may find {_two(PLANET_SCENES.get(c['planet'], '') or HOUSE_SCENES.get(f['moon_house'], ''))} keep circling back in your thoughts."})
    else:
        units.append({
            "title": "What your mind keeps returning to",
            "a": (f"For these couple of days, until about {until}, the Moon is lighting up the part of your "
                  f"chart that governs {HOUSE_AREA.get(f['moon_house'], '')}."),
            "b": "", "topic": HOUSE_AREA.get(f["moon_house"], ""),
            "scenes": HOUSE_SCENES.get(f["moon_house"], ""),
            "fb": f"You may find {_two(HOUSE_SCENES.get(f['moon_house'], ''))} on your mind more than usual."})
    if len(cs) > 1:
        c = cs[1]
        rel = "resting on" if c["kind"] == "sits on" else "looking at"
        units.append({
            "title": "A second thread",
            "a": f"The Moon is also {rel} your birth {c['planet']}, which stands for {c['stands_for']}.",
            "b": "", "topic": c["stands_for"], "nature": "nudging at the back of your mind",
            "scenes": _scenes_for(c),
            "fb": "You may notice a decision or a conversation about this quietly waiting for an answer."})
    if f.get("chandrashtama"):
        units.append({
            "title": "Handle with care",
            "a": "For about two days the Moon sits in the 8th place from your own Moon, a touchy spot.",
            "b": "", "topic": "a low-energy, touchy stretch", "scenes": "patience running short, feeling drained, postponing big talks",
            "fb": "You may feel easily drained or short on patience, and postponing big talks tends to help."})
    elif f.get("ad"):
        until_t = ""
        if f.get("ad_end"):
            try:
                until_t = f" until {_dy(datetime.strptime(f['ad_end'], '%Y-%m-%d'))}"
            except ValueError:
                until_t = ""
        units.append({
            "title": "The mood underneath",
            "a": (f"Behind all this, your running period is {f['md']} with {f['ad']}{until_t}, and {f['ad']} "
                  f"stands for {PLANET_STANDS_FOR.get(f['ad'], 'steady growth')}."),
            "b": "", "topic": PLANET_STANDS_FOR.get(f["ad"], ""), "nature": "a steady background pull",
            "scenes": "weighing what is really worth your energy, where your attention keeps going",
            "fb": "You may be weighing what is really worth your energy right now."})
    return units[:3]


def past_units(facts: list[dict]) -> list[dict]:
    units: list[dict] = []
    for f in facts:
        if f["kind"] == "period":
            units.append({
                "title": f"A new chapter from {f['date'].strftime('%B')}",
                "a": (f"On {_dy(f['date'])} your running sub-period turned to {f['ad']}, which is about "
                      f"{f['stands_for']}."),
                "b": "", "topic": f["stands_for"], "scenes": "a shift in what takes up your days",
                "fb": "From around then you may have noticed those matters moving to the front of your days."})
            continue
        p = f["planet"]
        short = HOUSE_SHORT.get(f["house"], "life")
        when = (f"From {_dy(f['began'])}" if f.get("began") else
                f"Until {_dy(f['ended'])}" if f.get("ended") else "Through these six months")
        a = f"{when}, {p} sat over the part of your chart that governs {HOUSE_AREA.get(f['house'], '')}."
        b = ""
        mc = f.get("main_contact")
        if mc:
            b = (f" It also {'rested on' if mc['kind'] == 'sits on' else 'pointed at'} your birth "
                 f"{mc['planet']}, the part of you that carries {PLANET_STANDS_FOR.get(mc['planet'], '')}.")
        if f.get("trigger_days"):
            b += f" The days it likely came to a head were around {', '.join(f['trigger_days'])}."
        if f.get("dignity") in ("exalted", "debilitated"):
            b += f" {p} was {'at its strongest' if f['dignity'] == 'exalted' else 'at its weakest'} in that sign."
        units.append({
            "title": _TITLE.get(p, "A stretch around {a}").format(a=short),
            "a": a, "b": b.strip(), "topic": f["area"], "scenes": HOUSE_SCENES.get(f["house"], ""),
            "nature": _TONE.get(p, "different"), "planet": p,
            "fb": f"Things like {_two(HOUSE_SCENES.get(f['house'], ''))} may have felt {_TONE.get(p, 'different')}."})
    return units[:4]


def _compose(u: dict, feel: str) -> dict:
    feel = feel.strip()
    feel = feel[:1].upper() + feel[1:]
    if feel and feel[-1] not in ".!?":
        feel += "."
    text = " ".join(x for x in (u["a"], feel, u.get("b", "")) if x)
    return {"title": u["title"], "text": text}


# ---- the model (feelings only) -------------------------------------------------------------
_SYSTEM = """You are an experienced Vedic astrologer sitting across a table from one client. You talk like a warm, plain-spoken human, never like a report generator.

For each numbered UNIT you get a TOPIC (what part of life is being touched), a NATURE (how it tends to push), and EVERYDAY EXAMPLES. Write ONE short passage per unit saying what this tends to FEEL like in daily life.

HARD RULES
- Exactly one passage per unit, in the same order. 1-2 sentences, 18-45 words each.
- Speak to "you". Hedge honestly: "you may have", "chances are", "it tends to". Never state a feeling or event as certain.
- Be concrete: pick one or two of the EVERYDAY EXAMPLES and weave them into real-life wording. Do not list them all.
- Do NOT name any planet, sign, date, month or number. Do NOT say how long anything lasts.
- Do NOT predict the future and do NOT give advice. Describe what it is like.
- Keep the passage's mood faithful to its NATURE line (a heavy, slow nature must sound heavy and slow; a supportive one supportive).
- No jargon (nakshatra, house, dasha, aspect, conjunction, transit, natal, Naadi). Never mention illness, accident, death, divorce or money disasters.
- Each passage must fit ITS OWN unit's topic and examples only. Never reuse wording from one passage in another.
- Do not start two passages with the same word. No bullet characters, no markdown.
- Tense: for "NOW" units write in the present ("you may be turning over...", "chances are you keep..."); for "PAST" units write in the past ("you may have noticed...", "it probably felt...")."""

_CACHE: dict[str, list[str]] = {}
_MONTH_WORD = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b")
_ENDS = re.compile(r"\b(until|till|stayed|stays|left|leaves|leaving|ended|ends|ending|moved out|lasted|lasts)\b", re.I)


_PAST_TENSE = re.compile(r"\b(felt|weighed|found yourself|caught yourself|had been|may have|might have|"
                         r"probably felt)\b", re.I)


def _feel_problems(feels: list[str], n: int, kind: str = "past") -> list[str]:
    bad: set[str] = set()
    if len(feels) != n:
        bad.add(f"write exactly {n} passages, one per unit, in order")
    firsts = []
    for x in feels:
        if kind == "mind" and _PAST_TENSE.search(x):
            bad.add("these are about right now: use the present tense, not the past")
        if kind == "past" and not re.search(r"\b(have|had|felt|was|were|seemed|probably|may have|might have|noticed|"
                                            r"became|tended)\b", x, re.I):
            bad.add("these are about the past six months: use the past tense")
        words = len(x.split())
        if words < 12 or words > 60:
            bad.add("each passage needs 18-45 words")
        if _JARGON.search(x):
            bad.add(f"jargon word '{_JARGON.search(x).group(0)}'; use plain words")
        if _DANGER.search(x):
            bad.add("mentions a danger or a guaranteed outcome")
        if any(ch in x for ch in ("*", "#", "<", ">", "\u2022")) or re.search(r"\d", x):
            bad.add("no digits, markdown or symbols")
        if _MONTH_WORD.search(x):
            bad.add("do not name a month or date")
        if re.search(r"\b(will|soon|going to|upcoming|finally|eventually|next (?:week|month|year))\b", x, re.I):
            bad.add("do not predict the future; describe what it is like")
        for pl in _PLANET_NAMES:
            if re.search(rf"\b{pl}\b", x):
                bad.add(f"do not name {pl}; planets are named elsewhere")
        if _ENDS.search(x):
            bad.add("do not say when anything ends or how long it lasts")
        if re.search(r"everyday example|\bexamples?\b", x, re.I):
            bad.add("do not mention the examples; weave them in")
        if not _HEDGE.search(x):
            bad.add("hedge: may, probably, tends to, chances are")
        if re.search(r"\b(native|the client)\b", x, re.I):
            bad.add("speak to 'you'")
        if not re.match(r"\s*(you|your|chances|it|this|these|there|perhaps|probably|maybe|odds|most|some|small|"
                        r"every|even|at times|more|many|often|during|when|with|while)\b", x, re.I):
            bad.add("start with a full sentence, usually beginning 'You may...' or 'Chances are...'")
        firsts.append(x.split()[0].lower() if x.split() else "")
    return sorted(bad)[:4]


def _write_feel(kind: str, units: list[dict]) -> Optional[list[str]]:
    try:
        from core.config import S
        if not S.llm_tab_enabled("full_report"):
            return None
        from core.llm_client import complete_model
        from pydantic import BaseModel, ConfigDict, Field
    except Exception:                                                     # noqa: BLE001
        return None
    if not units:
        return None
    blocks = []
    for i, u in enumerate(units, 1):
        tag = "NOW" if kind == "mind" else "PAST"
        blocks.append(f"UNIT {i} ({tag})\nTopic: {u['topic']}\nNature: {u.get('nature') or 'steady'}\n"
                      f"Everyday examples: {u['scenes']}")
    user = (("These are the things on the client's mind in these couple of days (NOW units).\n\n" if kind == "mind"
             else "These describe the client's last six months, oldest first (PAST units).\n\n")
            + "\n\n".join(blocks) + f"\n\nWrite exactly {len(units)} passages.")
    key = hashlib.sha1(user.encode()).hexdigest()
    if key in _CACHE:
        return _CACHE[key]

    class _Item(BaseModel):
        model_config = ConfigDict(extra="forbid")
        feel: str = Field(default="", max_length=420)

    class _Out(BaseModel):
        model_config = ConfigDict(extra="forbid")
        items: list[_Item] = Field(default_factory=list, max_length=6)

    problems: list[str] = []
    for _attempt in range(3):
        try:
            got = complete_model(
                _Out, _SYSTEM,
                user if not problems else user + "\n\nYour previous answer was rejected: "
                + "; ".join(problems) + ". Rewrite it and fix every point.",
                temperature=0.5)
        except Exception as exc:                                          # noqa: BLE001
            print(f"[naadi_recent] {kind} model failed: {type(exc).__name__}: {exc}", flush=True)
            return None
        if got is None:
            return None
        feels = [i.feel.strip().strip('"') for i in got.items if i.feel.strip()]
        problems = _feel_problems(feels, len(units), kind)
        if not problems:
            _CACHE[key] = feels
            return feels
    print(f"[naadi_recent] {kind} model rejected: {problems} last={feels!r}"[:700], flush=True)
    return None


# ---- public --------------------------------------------------------------------------------
def _assemble(units: list[dict], feels: Optional[list[str]]) -> list[dict]:
    return [_compose(u, feels[i] if feels and i < len(feels) else u["fb"]) for i, u in enumerate(units)]


def build(pc: dict, today: Optional[date] = None) -> dict:
    """{'mind': [{title,text}], 'past': [{title,text}], 'by_model': {'mind':bool,'past':bool}}.

    Empty lists when the Chandra Naadi engine is unavailable; the caller keeps its old text then.
    """
    today = today or date.today()
    out: dict[str, Any] = {"mind": [], "past": [], "by_model": {"mind": False, "past": False}}
    try:
        mf = mind_facts(pc, today)
        units = mind_units(mf)
        if units:
            feels = _write_feel("mind", units)
            out["by_model"]["mind"] = feels is not None
            out["mind"] = _assemble(units, feels)
    except Exception as exc:                                              # noqa: BLE001
        print(f"[naadi_recent] mind skipped: {type(exc).__name__}: {exc}", flush=True)
    try:
        units = past_units(past_facts(pc, today))
        if units:
            feels = _write_feel("past", units)
            out["by_model"]["past"] = feels is not None
            out["past"] = _assemble(units, feels)
    except Exception as exc:                                              # noqa: BLE001
        print(f"[naadi_recent] past skipped: {type(exc).__name__}: {exc}", flush=True)
    return out


def render_items(items: list[dict]) -> str:
    from html import escape
    return "".join(f"<li><b>{escape(i['title'])}:</b> {escape(i['text'])}</li>" for i in items)
