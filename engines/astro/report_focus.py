#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report_focus.py - the short "focus" full report.

One page, not a catalogue.  The reader gets:

  free  : the dasha card; chart-derived personality; the TWO life areas the chart
          is loudest about now, each as "what is occupying you" and "where you are
          vulnerable"; gemstones to avoid; technical cross-checks collapsed.
  paid  : the same, then for each of those two areas the next two to three years
          as dated stretches, practical remedies and full gemstone guidance.

Method
  * Chandra Naadi is the primary technique: the slow planets (Saturn, Jupiter,
    Rahu, Ketu, Mars) touching a natal planet decide which area is live.
  * Five other lenses then check that reading and are shown, collapsed:
    the Vedic running period, the divisional charts, Jaimini, the transits and
    Ashtakavarga.  Agreement and disagreement are both reported.
  * Every sentence is built from chart facts (a grade, a house, a planet's
    condition, a dated stretch).  The vocabulary of "what this area looks like at
    your age" is the only fixed text; WHICH area, WHICH tone and WHEN come from the
    chart.  A language model, when switched on, only rewords those facts; its output
    is validated and a plain deterministic version is used when it fails.

Nothing here changes a prediction fact; it only chooses and orders them.  The
module is used only when FULL_REPORT_DESIGN=focus (see report_render.full_report).
"""
from __future__ import annotations

import hashlib
import re
import time
from datetime import date, timedelta
from html import escape
from typing import Any, Optional

import chart_lines as CL
import naadi_recent as NR
from astro_precompute import house_from_lagna

HORIZON_YEARS = 3
SLOW_FORWARD = ("Saturn", "Jupiter", "Rahu", "Ketu")     # Mars changes sign too often to date
_PRESSURE = ("Saturn", "Rahu", "Ketu", "Mars")

# ---------------------------------------------------------------------------------------------
# areas
# ---------------------------------------------------------------------------------------------
AREAS: dict[str, dict] = {
    "career": dict(label="Work and career", topic="your work", houses=(10,), related=(6, 11, 3),
                   karakas=("Sun", "Saturn", "Mercury"), jaimini="amatya"),
    "money": dict(label="Money", topic="money", houses=(2, 11), related=(5, 9, 8),
                  karakas=("Jupiter", "Venus"), jaimini=""),
    "love": dict(label="Relationships", topic="your closest relationship", houses=(7,), related=(5, 2, 11),
                 karakas=("Venus", "Jupiter"), jaimini="dara"),
    "home": dict(label="Home and family", topic="home and family", houses=(4,), related=(2,),
                 karakas=("Moon", "Mars"), jaimini="matru"),
    "children": dict(label="Children", topic="children", houses=(5,), related=(9, 2),
                     karakas=("Jupiter",), jaimini="putra"),
    "health": dict(label="Health and energy", topic="your health and energy", houses=(1, 6), related=(8,),
                   karakas=("Sun", "Moon", "Mars"), jaimini="atma"),
    "learning": dict(label="Studies, luck and guidance", topic="studies and guidance", houses=(9,),
                     related=(5,), karakas=("Jupiter", "Mercury"), jaimini="pitru"),
    "inner": dict(label="Rest, spending and letting go", topic="rest, spending and letting go",
                  houses=(12,), related=(8,), karakas=("Ketu", "Saturn"), jaimini=""),
}

BANDS = ("young", "building", "established", "mature", "elder")


def band_for_age(age: int) -> str:
    if age < 25:
        return "young"
    if age < 35:
        return "building"
    if age < 50:
        return "established"
    if age < 63:
        return "mature"
    return "elder"


# What each area tends to look like at each life stage: (what is on your mind, how people slip).
# This is vocabulary, not prediction: which area, which tone and when all come from the chart.
LEX: dict[str, dict[str, tuple[str, str]]] = {
    "career": {
        "young": ("your first job, your next course or which direction to commit to",
                  "taking the first offer out of anxiety, or putting a choice off until it is made for you"),
        "building": ("a job change, a promotion conversation or whether to start something of your own",
                     "quitting in a flash of frustration, or staying quiet while someone else takes the credit"),
        "established": ("your position, your targets and whether you are growing or just holding on",
                        "carrying more than your share and resenting it, or reacting sharply to a boss or colleague"),
        "mature": ("how long to keep carrying the load, who takes over from you and what your last stretch of work looks like",
                   "clinging to control, or switching off from work before the time is right"),
        "elder": ("staying useful, passing on what you know and how you are remembered at work",
                  "feeling sidelined, or taking on more than your energy can hold"),
    },
    "money": {
        "young": ("pocket money, a first salary, fees and what you can afford",
                  "spending ahead of what you earn, or hiding a money worry from family"),
        "building": ("savings, an EMI or loan, and whether income keeps up with your plans",
                     "borrowing to match other people's lifestyle, or postponing a money decision"),
        "established": ("family expenses, investments and a big commitment such as property or a child's education",
                        "locking money into one bet, or lending without a clear return date"),
        "mature": ("your retirement cushion, what to keep liquid and what to leave for the family",
                   "taking a risky investment to catch up, or worrying more than the numbers justify"),
        "elder": ("income that lasts, medical costs and what you leave behind",
                  "trusting a stranger's offer, or giving away more than you can spare"),
    },
    "love": {
        "young": ("who you are drawn to, a crush or a first serious relationship",
                  "reading too much into small signals, or going quiet when you should speak"),
        "building": ("your partner or a proposal, commitment and the pull between 'me' and 'we'",
                     "bottling up a complaint until it comes out as a fight, or seeking reassurance you could give yourself"),
        "established": ("the state of your marriage or partnership, who carries what, and time for each other",
                        "letting routine replace conversation, or a small argument turning into a cold silence"),
        "mature": ("your partner as the children grow away, and what the two of you want next",
                   "taking each other for granted, or drifting into separate lives"),
        "elder": ("companionship, caring for each other and old hurts coming back up",
                  "withdrawing into silence, or reviving an old grievance"),
    },
    "home": {
        "young": ("life at your parents' home, the rules there and the wish for more freedom",
                  "arguing over small rules, or hiding your plans"),
        "building": ("where you live, a move or shifting out, and how your mother is doing",
                     "feeling torn between your family's expectations and your own plans"),
        "established": ("the house, your parents' needs and keeping peace between the generations at home",
                        "absorbing everyone's stress, or snapping at home after a hard day"),
        "mature": ("the family home, property decisions and relatives who need care",
                   "holding on to a house or an old family argument longer than it serves you"),
        "elder": ("the home you live in, who looks after it and who lives close by",
                  "feeling like a burden, or fretting over matters the family has already settled"),
    },
    "children": {
        "young": ("your studies, your creative side and early thoughts about family",
                  "putting off effort on what you enjoy until the chance has passed"),
        "building": ("planning a child, or a young child's first years",
                     "measuring yourself against other people's timelines"),
        "established": ("your child's school, health and behaviour as they grow",
                        "pushing too hard, or worrying out loud in front of them"),
        "mature": ("your grown children's careers, marriages and independence",
                   "advising when you were not asked, or feeling shut out"),
        "elder": ("your children and grandchildren, and how often you see them",
                  "feeling neglected, or expecting more than they can give"),
    },
    "health": {
        "young": ("energy, sleep, exam stress and eating habits",
                  "burning the candle at both ends, or ignoring a niggle"),
        "building": ("tiredness from work, sleep and the habits you keep postponing",
                     "running on caffeine and deadlines, or skipping a check-up"),
        "established": ("stamina, weight, blood pressure or sugar, and the routine you keep skipping",
                        "pushing through fatigue, or letting stress build up unnoticed"),
        "mature": ("joints, blood pressure and sugar checks, and how long you take to recover",
                   "dismissing a symptom, or overdoing exercise to feel young"),
        "elder": ("regular check-ups, medicines, mobility and sleep",
                  "skipping a medicine, or hiding discomfort from the family"),
    },
    "learning": {
        "young": ("exams, choosing a stream or course, and a teacher or mentor",
                  "following the crowd, or doubting yourself after one bad result"),
        "building": ("further study, a certification or an elder's advice on your next step",
                     "waiting for the right moment while it passes, or ignoring good advice"),
        "established": ("a course to move ahead, a long trip, or your father's or a mentor's guidance",
                        "assuming luck will cover what planning should"),
        "mature": ("teaching, advising younger people and what you believe in",
                   "stubbornness about old methods, or tension with a father figure or mentor"),
        "elder": ("faith, learning for its own sake and passing on what you know",
                  "feeling that your experience is no longer wanted"),
    },
    "inner": {
        "young": ("sleep, time alone, spending you did not plan, or a wish to get away",
                  "withdrawing from friends, or spending to escape"),
        "building": ("expenses that outrun plans, poor sleep, or a stint away from home",
                     "overspending to relax, or running on too little rest"),
        "established": ("tiredness, unplanned expenses and a need for time alone",
                        "saying yes to everything and resenting it afterwards"),
        "mature": ("letting go of old roles, time away and a quieter routine",
                   "holding on to old roles, or lying awake over things you cannot change"),
        "elder": ("rest, prayer, quiet and a lighter life",
                  "restless nights, or a fear of being a burden"),
    },
}

# How strongly each life stage cares about each area (a small prior: the chart decides, age only breaks ties
# and nudges relevance, so a 22-year-old is not led with retirement).
AGE_PRIOR: dict[str, dict[str, float]] = {
    "young": {"learning": 1.2, "career": 1.0, "love": 0.8, "home": 0.5, "health": 0.5, "money": 0.3,
              "inner": 0.2, "children": 0.0},
    "building": {"career": 1.3, "love": 1.0, "money": 0.9, "home": 0.6, "children": 0.5, "health": 0.4,
                 "learning": 0.3, "inner": 0.2},
    "established": {"career": 1.1, "money": 1.0, "home": 0.9, "children": 0.9, "health": 0.7, "love": 0.7,
                    "learning": 0.3, "inner": 0.3},
    "mature": {"health": 1.2, "money": 1.0, "children": 0.8, "home": 0.8, "career": 0.7, "love": 0.6,
               "inner": 0.5, "learning": 0.4},
    "elder": {"health": 1.5, "home": 1.0, "children": 0.8, "inner": 0.8, "money": 0.7, "love": 0.5,
              "learning": 0.4, "career": 0.2},
}

ADVICE: dict[str, dict[str, str]] = {
    "career": {"support": "Ask for the conversation or the opening you have been postponing, and keep a record of what you deliver.",
               "pressure": "Avoid big career moves made in frustration; put agreements in writing and let a decision sit overnight."},
    "money": {"support": "A good stretch to formalise a saving or a plan you keep putting off.",
              "pressure": "Hold off on new loans or large commitments, and keep a cash cushion."},
    "love": {"support": "Say the thing you have been holding back, kindly and early.",
             "pressure": "Pick calm moments for hard talks, and do not decide anything in the middle of an argument."},
    "home": {"support": "Use the stretch to settle a home decision or mend a family rift.",
             "pressure": "Keep family talks short and calm, and postpone big household changes where you can."},
    "children": {"support": "A good time to plan, or to spend focused time with them.",
                 "pressure": "Go gently: listen more than you instruct, and avoid comparing them with others."},
    "health": {"support": "Start the routine or check-up you have been delaying; it is likely to stick.",
               "pressure": "Do not skip sleep or check-ups; small steady habits matter more than big efforts."},
    "learning": {"support": "Apply, enrol or ask the mentor; guidance reaches you more easily now.",
                 "pressure": "Stick to the basics, avoid shortcuts and double-check what you commit to."},
    "inner": {"support": "Use the quiet to rest, travel or clear out on purpose.",
              "pressure": "Watch spending and late nights, and schedule rest before you feel drained."},
}

STAR_TRAIT = {
    "Ashwini": "You tend to move quickly once something interests you, and starting before others feels natural.",
    "Bharani": "You often have strong creative convictions and more staying power than people first notice.",
    "Krittika": "You tend to see through clutter quickly; direct words and clear standards matter to you.",
    "Rohini": "You usually notice beauty, presentation and atmosphere, and creative expression comes naturally to you.",
    "Mrigashira": "Your mind tends to stay curious; you like asking questions and discovering what lies beneath the obvious.",
    "Ardra": "You may analyse life intensely, and difficult experiences often leave you wiser rather than defeated.",
    "Punarvasu": "You tend to recover by returning to what matters, often finding your footing after a setback.",
    "Pushya": "People may rely on you because you are patient, protective and willing to build things steadily.",
    "Ashlesha": "You tend to read emotional undercurrents well and protect your inner circle fiercely.",
    "Magha": "Dignity and self-respect tend to guide you; you notice whether people honour your contribution.",
    "Purva Phalguni": "Warmth, creativity and enjoyable company tend to bring out your best.",
    "Uttara Phalguni": "You tend to take promises seriously and show generosity through reliable actions.",
    "Hasta": "You are often resourceful with practical details and like finding a workable solution.",
    "Chitra": "You tend to notice design and craftsmanship, and care about doing things exceptionally well.",
    "Swati": "Independence matters to you, though you can adapt diplomatically when circumstances change.",
    "Vishakha": "Once a goal matters, you can pursue it with unusual focus and persistence.",
    "Anuradha": "Loyalty and teamwork tend to bring out your best, even across distance or differences.",
    "Jyeshtha": "You tend to notice what others miss and naturally step into a protective or responsible role.",
    "Mula": "You are often driven to get to the root of things, even when that means starting again.",
    "Purva Ashadha": "Strong convictions tend to guide you, and you can be persuasive when you believe in your path.",
    "Uttara Ashadha": "You often make progress through patience and principle rather than noise or haste.",
    "Shravana": "You tend to learn by listening carefully and respecting knowledge that has stood the test of time.",
    "Dhanishtha": "Organisation and resource management may come naturally, especially when you have room to lead.",
    "Shatabhisha": "You may be drawn to research and original ideas, while still needing private space to recharge.",
    "Purva Bhadrapada": "You can be intensely idealistic, with a philosophical streak that searches for deeper meaning.",
    "Uttara Bhadrapada": "Calm endurance and emotional depth tend to be quiet strengths people rely on.",
    "Revati": "You often combine empathy with an artistic sense and a wish to guide things gently to completion.",
}

AK_TRAIT = {
    "Sun": "A recurring lesson is to build self-respect through your actions, not through constant recognition.",
    "Moon": "A recurring lesson is to care deeply without losing your own emotional balance.",
    "Mars": "A recurring theme is learning which battles deserve your energy—and which are better left alone.",
    "Mercury": "A recurring lesson is to use your quick mind with discernment, not simply to stay busy or informed.",
    "Jupiter": "A recurring lesson is to refine what you believe and share it without needing every answer.",
    "Venus": "A recurring lesson is to value love and beauty without giving more than is healthy for you.",
    "Saturn": "A recurring lesson is to respect endurance: what you build slowly often means the most.",
    "Rahu": "A recurring lesson is to understand your strongest desires rather than letting them run you.",
}

PHASE_CHANNEL = {
    "Sun": "authority, recognition and senior people",
    "Moon": "emotional responses, family needs and daily flow",
    "Mars": "initiative, practical action and technical effort",
    "Mercury": "conversations, paperwork and negotiations",
    "Jupiter": "guidance, support and long-term plans",
    "Venus": "relationships, comfort and lifestyle choices",
    "Saturn": "duties, workload and long-term responsibility",
    "Rahu": "ambition, unfamiliar options and restlessness",
    "Ketu": "closure, detachment and unfinished matters",
}

AREA_CHANNEL = {
    ("career", "Sun"): "authority, bosses and professional recognition",
    ("career", "Moon"): "workplace morale, family needs and daily stability",
    ("career", "Mars"): "initiative, technical effort and acting under pressure",
    ("career", "Mercury"): "conversations, paperwork and negotiations",
    ("career", "Jupiter"): "mentorship, guidance and long-term growth",
    ("career", "Venus"): "working relationships, clients and rewards from your work",
    ("career", "Saturn"): "duties, workload and long-term responsibility",
    ("career", "Rahu"): "ambition, unfamiliar roles and restless change",
    ("career", "Ketu"): "closure, detachment and unfinished work",
    ("money", "Sun"): "income, financial standing and control over decisions",
    ("money", "Moon"): "cash flow, family needs and emotional spending",
    ("money", "Mars"): "initiative, property and practical financial decisions",
    ("money", "Mercury"): "paperwork, negotiations and financial planning",
    ("money", "Jupiter"): "guidance, support and long-term planning",
    ("money", "Venus"): "comfort, lifestyle choices and shared expenses",
    ("money", "Saturn"): "obligations, careful budgeting and long-term responsibility",
    ("money", "Rahu"): "ambition, unfamiliar offers and impulsive choices",
    ("money", "Ketu"): "closure, repayment and letting go of old commitments",
}

# Where a house points, as a weight per area (a planet "carries" the houses it holds and rules).
HOUSE_AREAS: dict[int, list[tuple[str, float]]] = {
    1: [("health", 1.0)], 2: [("money", 1.0)], 3: [("career", 0.5)], 4: [("home", 1.0)],
    5: [("children", 1.0), ("learning", 0.5)], 6: [("health", 0.7), ("career", 0.5)],
    7: [("love", 1.0)], 8: [("health", 0.5), ("money", 0.4), ("inner", 0.5)], 9: [("learning", 1.0)],
    10: [("career", 1.0)], 11: [("money", 0.7), ("career", 0.4)], 12: [("inner", 1.0)],
}

PLANET_REMEDY: dict[str, tuple[str, str, str]] = {
    "Sun": ("Sunday", "Om Suryaya Namah", "offer water to the rising sun and make time for your father or a senior you respect"),
    "Moon": ("Monday", "Om Chandraya Namah", "keep your sleep regular, spend a few quiet minutes near water and call your mother"),
    "Mars": ("Tuesday", "Om Mangalaya Namah", "burn off tension with a short bout of exercise and avoid arguments on Tuesdays"),
    "Mercury": ("Wednesday", "Om Budhaya Namah", "read or write a little every day and clear one pending message or piece of paperwork"),
    "Jupiter": ("Thursday", "Om Gurave Namah", "respect a teacher or elder and help a student with books or a meal"),
    "Venus": ("Friday", "Om Shukraya Namah", "keep your living space clean and say one kind, specific thing to someone close"),
    "Saturn": ("Saturday", "Om Shanaischaraya Namah", "finish one long-pending duty properly, help someone who works with their hands and keep your word on time"),
    "Rahu": ("Saturday", "Om Rahave Namah", "cut late-night screen time, avoid impulsive deals and write a plan down before you say yes"),
    "Ketu": ("Tuesday", "Om Ketave Namah", "set aside a few quiet minutes daily and close one old pending matter"),
}

# ---------------------------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------------------------
_e = escape


def _mon(d: Optional[date]) -> str:
    return d.strftime("%b %Y") if d else ""


def _span(a: Optional[date], b: Optional[date]) -> str:
    if a and b:
        return f"{_mon(a)} to {_mon(b)}"
    return _mon(a or b)


def _d(v: Any) -> Optional[date]:
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None


def _months_between(a: date, b: date) -> int:
    return max(0, (b.year - a.year) * 12 + (b.month - a.month))


def _ord(n: int) -> str:
    return CL.ordinal(int(n))


def _sign_of(verdict: str) -> int:
    return {"support": 1, "caution": -1}.get(verdict, 0)


def _area_houses(area: str) -> tuple[int, ...]:
    a = AREAS[area]
    return tuple(a["houses"]) + tuple(a["related"])


def relevance(pc: dict, planet: str, area: str) -> float:
    """How strongly a natal planet carries this area: where it stands, what it rules, what it signifies."""
    if not planet:
        return 0.0
    a = AREAS[area]
    s = 0.0
    h = CL.house_of(pc, planet)
    if h in a["houses"]:
        s += 1.0
    elif h in a["related"]:
        s += 0.4
    for o in CL.owns(pc, planet):
        if o in a["houses"]:
            s += 0.9
        elif o in a["related"]:
            s += 0.35
    if planet in a["karakas"]:
        s += 0.5
    return min(s, 2.2)


def _house_weight(house: int, area: str) -> float:
    a = AREAS[area]
    if house in a["houses"]:
        return 0.8
    if house in a["related"]:
        return 0.3
    return 0.0


def _cover(planet: str, house: int) -> set[int]:
    """Houses a transiting planet stands on or looks at (whole-sign aspects)."""
    offs = {"Jupiter": (0, 4, 6, 8), "Saturn": (0, 2, 6, 9), "Mars": (0, 3, 6, 7)}.get(planet, (0, 6))
    return {((house - 1 + o) % 12) + 1 for o in offs}


def _role(pc: dict, planet: str) -> str:
    h = CL.house_of(pc, planet)
    ruled = CL.owns(pc, planet)
    bits = []
    if h:
        bits.append(f"in your {_ord(h)} house")
    if ruled:
        bits.append("ruling your " + " and ".join(_ord(x) for x in ruled[:2]))
    return f"{planet} ({', '.join(bits)})" if bits else planet


def _tone(planet: str) -> str:
    return NR._TONE.get(planet, "different from usual")


# ---------------------------------------------------------------------------------------------
# context: everything computed once per report
# ---------------------------------------------------------------------------------------------
class Ctx:
    def __init__(self, pc: dict, today: date):
        self.pc = pc
        self.today = today
        try:
            from interpretation.life_stage import age_years
            self.age = int(age_years(pc, today=today))
        except Exception:                                              # noqa: BLE001
            self.age = int((pc.get("meta") or {}).get("age") or 30)
        self.band = band_for_age(self.age)
        self.lagna = NR._lagna(pc)
        self.horizon = today + timedelta(days=int(365.25 * HORIZON_YEARS))
        self.vim = pc.get("vimshottari") or {}
        self.md, self.ad, self.ad_end, self.ad_start = NR._periods(pc)
        self._slow: Optional[list] = None
        self._segments: Optional[dict] = None

    # --- present slow-planet picture (Chandra Naadi) ---
    @property
    def slow(self) -> list[dict]:
        if self._slow is None:
            out: list[dict] = []
            pos = NR._positions(self.today) if NR.CN else {}
            for planet in NR.SLOW:
                sign = (pos.get(planet) or {}).get("sign")
                if not sign:
                    continue
                out.append({"planet": planet, "sign": sign,
                            "house": house_from_lagna(sign, self.lagna),
                            "contacts": NR._contacts(self.pc, planet, sign)})
            self._slow = out
        return self._slow

    # --- Jupiter / Saturn stays with Ashtakavarga points ---
    @property
    def segments(self) -> dict:
        if self._segments is None:
            try:
                import report_timing as RT
                self._segments = RT.transit_segments(self.pc, start=self.today, years=HORIZON_YEARS) or {}
            except Exception:                                          # noqa: BLE001
                self._segments = {}
        return self._segments

    def segment_at(self, planet: str, when: date) -> dict:
        for s in self.segments.get(planet) or []:
            a, b = _d(s.get("start")), _d(s.get("end"))
            if a and b and a <= when <= b:
                return s
        return {}

    def band_at(self, when: date) -> str:
        try:
            import interpretation.life_stage as LS
            dob = LS.dob_of(self.pc)
            return band_for_age(LS.age_years_at(dob, when)) if dob else self.band
        except Exception:                                              # noqa: BLE001
            return self.band


# ---------------------------------------------------------------------------------------------
# Chandra Naadi: which area is live, and what is driving it
# ---------------------------------------------------------------------------------------------
_KIND_W = {"sits on": 1.5, "looks at": 1.0}


def _connection_score(cx: Ctx, area: str) -> tuple[float, Optional[dict]]:
    """Sum of live Chandra Naadi connections for an area, and the strongest one (the driver)."""
    total = 0.0
    best: Optional[dict] = None
    for s in cx.slow:
        w = NR._WEIGHT.get(s["planet"], 2.0)
        hw = _house_weight(s["house"], area)
        if hw:
            val = w * 0.5 * hw
            total += val
            cand = {"planet": s["planet"], "sign": s["sign"], "house": s["house"], "natal": None,
                    "kind": "", "score": val, "via": "house"}
            if best is None or val > best["score"]:
                best = cand
        for c in s["contacts"]:
            rel = relevance(cx.pc, c["planet"], area)
            if rel <= 0:
                continue
            val = w * _KIND_W.get(c["kind"], 1.0) * rel * 0.5
            total += val
            if best is None or val > best["score"]:
                best = {"planet": s["planet"], "sign": s["sign"], "house": s["house"],
                        "natal": c["planet"], "kind": c["kind"], "score": val, "via": "contact"}
    return total, best


def _dasha_score(cx: Ctx, area: str) -> float:
    return 2.0 * relevance(cx.pc, cx.ad, area) * 0.6 + 1.2 * relevance(cx.pc, cx.md, area) * 0.6


def score_areas(cx: Ctx) -> list[dict]:
    rows = []
    prior = AGE_PRIOR.get(cx.band, {})
    for area in AREAS:
        naadi, driver = _connection_score(cx, area)
        dasha = _dasha_score(cx, area)
        age = prior.get(area, 0.5)
        # the chart decides; life stage scales it by up to about a fifth and breaks ties
        total = (naadi + dasha) * (0.7 + 0.3 * age) + age
        rows.append({"area": area, "total": round(total, 3), "naadi": round(naadi, 3),
                     "dasha": round(dasha, 3), "age": age, "driver": driver})
    rows.sort(key=lambda r: (-r["total"], r["area"]))
    return rows


def pick_areas(pc: dict, today: Optional[date] = None, cx: Optional[Ctx] = None) -> list[dict]:
    """The two areas the chart is loudest about now. Deterministic for a chart and a date."""
    cx = cx or Ctx(pc, today or date.today())
    return score_areas(cx)[:2]


def driver_until(cx: Ctx, driver: Optional[dict]) -> Optional[date]:
    """The date the driving planet leaves its current sign (first exit)."""
    if not driver or not NR.CN:
        return None
    planet, sign = driver["planet"], driver["sign"]
    d = cx.today
    for _ in range(0, 1500, 5):
        d += timedelta(days=5)
        got = (NR._positions(d).get(planet) or {}).get("sign")
        if got and got != sign:
            return d
    return None


# ---------------------------------------------------------------------------------------------
# the six lenses
# ---------------------------------------------------------------------------------------------
def _lens(key: str, name: str, verdict: str, plain: str, tech: str) -> dict:
    return {"key": key, "name": name, "verdict": verdict, "plain": plain, "tech": tech}


def lens_naadi(cx: Ctx, area: str, driver: Optional[dict]) -> dict:
    pc = cx.pc
    signed = 0.0
    lines: list[str] = []
    for s in cx.slow:
        base = 1.0 if s["planet"] == "Jupiter" else (-0.6 if s["planet"] == "Mars" else -1.0)
        for c in s["contacts"]:
            rel = relevance(pc, c["planet"], area)
            if rel < 0.9:
                continue
            g = CL.planet_grade(pc, c["planet"])
            val = base * rel * _KIND_W.get(c["kind"], 1.0)
            if val < 0:
                val *= 0.6 if g == "strong" else (1.3 if g == "strained" else 1.0)
            signed += val
            lines.append(f"{s['planet']} (now in {s['sign']}, your {_ord(s['house'])} house) "
                         f"{'rests on' if c['kind'] == 'sits on' else 'looks at'} your birth "
                         f"{_role(pc, c['planet'])}, which is {g}")
        hw = _house_weight(s["house"], area)
        if hw >= 0.8:
            signed += base * 0.5
            lines.append(f"{s['planet']} is passing through your {_ord(s['house'])} house, a house of this area")
    if not lines:
        return _lens("naadi", "Chandra Naadi", "quiet",
                     "No slow planet is pressing on the part of your chart that carries this area right now.",
                     "No slow transit touches a natal planet that rules or holds this area's houses.")
    verdict = "support" if signed > 0.8 else ("caution" if signed < -0.8 else "mixed")
    plain = {"support": "The slow-moving influences touching this area are of the helping kind.",
             "caution": "The slow-moving influences touching this area are of the slowing, testing kind.",
             "mixed": "The slow-moving influences touching this area pull both ways."}[verdict]
    return _lens("naadi", "Chandra Naadi", verdict, plain, "; ".join(lines[:3]) + ".")


def lens_dasha(cx: Ctx, area: str) -> dict:
    pc = cx.pc
    tied = []
    for tag, planet in (("sub-period", cx.ad), ("main period", cx.md)):
        rel = relevance(pc, planet, area)
        if rel >= 0.9:
            tied.append((tag, planet, CL.planet_grade(pc, planet)))
    if not tied:
        return _lens("dasha", "Vedic running period", "quiet",
                     "Your running life period is not directly about this area; it is felt through the slower influences instead.",
                     f"{cx.md} main period with {cx.ad} sub-period; neither holds nor rules a house of this area.")
    grades = [g for _t, _p, g in tied]
    verdict = ("support" if "strong" in grades and "strained" not in grades else
               "caution" if "strained" in grades and "strong" not in grades else "mixed")
    plain = {"support": "Your running life period points at this area and works from strength.",
             "caution": "Your running life period points at this area but works from a weak footing, so results ask for effort.",
             "mixed": "Your running life period points at this area with mixed strength."}[verdict]
    tech = "; ".join(f"{p} ({t}) is {g}: {_role(pc, p)}" for t, p, g in tied) + "."
    return _lens("dasha", "Vedic running period", verdict, plain, tech)


def lens_divisional(cx: Ctx, area: str) -> dict:
    pc = cx.pc
    try:
        import report_confluence as CF
        primary, pname = CF.AREA_VARGA.get(area, ("", ""))
        house = AREAS[area]["houses"][0]
        lord = CL.lord_of(pc, house)
        if not (primary and lord):
            raise ValueError("no varga")
        votes = []
        vs = CF._varga_sign(pc, primary, lord)
        if vs:
            votes.append((primary, vs, CF._dignity_in(lord, vs)))
        d9 = CF._d9_sign(pc, lord)
        d1 = CF._sign_in(pc, lord)
        if d9 and primary != "D9":
            votes.append(("D9", d9, 1.8 if d9 == d1 else CF._dignity_in(lord, d9)))
        if not votes:
            raise ValueError("no signs")
        avg = sum(v for _a, _b, v in votes) / len(votes)
    except Exception:                                                  # noqa: BLE001
        return _lens("divisional", "Divisional charts", "quiet",
                     "The finer sub-charts have nothing decisive to add for this area.",
                     "No divisional placement available for the ruler of this area.")
    verdict = "support" if avg >= 0.8 else ("caution" if avg <= -0.8 else "mixed")
    plain = {"support": "The finer sub-charts for this area back up the main chart.",
             "caution": "The finer sub-charts for this area are weaker than the main chart suggests.",
             "mixed": "The finer sub-charts for this area neither confirm nor deny the main chart."}[verdict]
    d1_sign = CF._sign_in(pc, lord)
    tech = (f"The ruler of your {_ord(house)} house is {lord}. " +
            "; ".join(f"In the {a} chart it is in {b}" + (" (the same sign as in the birth chart)" if b == d1_sign else "")
                      for a, b, _v in votes) + ".")
    return _lens("divisional", "Divisional charts", verdict, plain, tech)


def _jaimini_planet(pc: dict, role_prefix: str) -> str:
    for k in ((pc.get("cara_karakas") or {}).get("karakas") or []):
        if str(k.get("role") or "").lower().startswith(role_prefix):
            return str(k.get("planet") or "")
    return ""


def lens_jaimini(cx: Ctx, area: str, when: Optional[date] = None) -> dict:
    pc = cx.pc
    when = when or cx.today
    try:
        import report_confluence as CF
        j = CF.jaimini_at(pc, when) or {}
    except Exception:                                                  # noqa: BLE001
        j = {}
    houses = set(_area_houses(area))
    sign, antar = j.get("sign"), j.get("antar")
    hs = {s: house_from_lagna(s, cx.lagna) for s in (sign, antar) if s}
    active = {s: h for s, h in hs.items() if h in houses}
    karaka = _jaimini_planet(pc, AREAS[area]["jaimini"]) if AREAS[area]["jaimini"] else ""
    if not active:
        return _lens("jaimini", "Jaimini", "quiet",
                     "The sign-based Jaimini clock is not on this area at the moment.",
                     f"Jaimini main sign {sign or '-'} and sub sign {antar or '-'} fall in houses "
                     f"{', '.join(str(h) for h in hs.values()) or '-'}, outside this area's houses.")
    g = CL.planet_grade(pc, karaka) if karaka else CL.planet_grade(pc, NR.SIGN_LORDS.get(next(iter(active)), ""))
    verdict = {"strong": "support", "strained": "caution"}.get(g, "mixed")
    plain = {"support": "The Jaimini sign clock is on this area and its natural indicator is strong.",
             "caution": "The Jaimini sign clock is on this area and its natural indicator is under strain.",
             "mixed": "The Jaimini sign clock is on this area with a mixed indicator."}[verdict]
    tech = (f"Jaimini main sign {sign} and sub sign {antar} (houses "
            f"{', '.join(str(h) for h in hs.values())}); area indicator "
            f"{karaka or NR.SIGN_LORDS.get(next(iter(active)), '')} is {g}.")
    return _lens("jaimini", "Jaimini", verdict, plain, tech)


def lens_transit(cx: Ctx, area: str, when: Optional[date] = None) -> dict:
    when = when or cx.today
    houses = set(AREAS[area]["houses"])
    parts: list[str] = []
    signed = 0.0
    for planet in ("Jupiter", "Saturn"):
        seg = cx.segment_at(planet, when)
        if not seg:
            continue
        h = int(seg.get("house") or 0)
        bav = seg.get("bav")
        hit = sorted(houses & _cover(planet, h))
        if not hit:
            continue
        pts = f", {bav} Ashtakavarga points there" if bav is not None else ""
        if planet == "Jupiter":
            signed += 1.0 if (bav or 4) >= 4 else 0.4
        else:
            signed -= 0.4 if (bav or 0) >= 5 else 1.0
        parts.append(f"{planet} in {seg.get('sign')} (your {_ord(h)} house{pts}) stands on or looks at "
                     f"your {', '.join(_ord(x) for x in hit)} house")
    if not parts:
        return _lens("transit", "Transits", "quiet",
                     "Jupiter and Saturn are not on this area of your chart at the moment.",
                     "Neither Jupiter nor Saturn stands on or looks at this area's main house.")
    verdict = "support" if signed > 0.3 else ("caution" if signed < -0.3 else "mixed")
    plain = {"support": "Jupiter, the helper, is looking at this area of your chart.",
             "caution": "Saturn, the tester, is leaning on this area of your chart.",
             "mixed": "Jupiter and Saturn both touch this area, one helping and one testing."}[verdict]
    return _lens("transit", "Transits", verdict, plain, "; ".join(parts) + ".")


def lens_ashtakavarga(cx: Ctx, area: str) -> dict:
    sav = (cx.pc.get("ashtakavarga") or {}).get("sav") or []
    houses = AREAS[area]["houses"]
    vals = [sav[h - 1] for h in houses if len(sav) >= h]
    if not vals:
        return _lens("ashtakavarga", "Ashtakavarga", "quiet",
                     "No point-count is available for this area.", "Ashtakavarga table unavailable.")
    avg = sum(vals) / len(vals)
    verdict = "support" if avg >= 30 else ("caution" if avg <= 25 else "mixed")
    plain = {"support": "This area of your chart is well backed by natural support points.",
             "caution": "This area of your chart has fewer support points than most, so effort matters more than luck.",
             "mixed": "This area has an ordinary level of natural support."}[verdict]
    hs = houses[:len(vals)]
    tech = ("Your " + " and ".join(_ord(h) for h in hs) +
            (" house carries " if len(hs) == 1 else " houses carry ") +
            " and ".join(str(v) for v in vals) + " points (a typical house carries about 28).")
    return _lens("ashtakavarga", "Ashtakavarga", verdict, plain, tech)


def all_lenses(cx: Ctx, area: str, driver: Optional[dict]) -> list[dict]:
    return [lens_naadi(cx, area, driver), lens_dasha(cx, area), lens_divisional(cx, area),
            lens_jaimini(cx, area), lens_transit(cx, area), lens_ashtakavarga(cx, area)]


def tally(lenses: list[dict]) -> dict:
    prim = lenses[0]["verdict"]
    others = lenses[1:]
    agree = sum(1 for l in others if prim in ("support", "caution") and l["verdict"] == prim)
    differ = sum(1 for l in others if prim in ("support", "caution") and l["verdict"] == ("caution" if prim == "support" else "support"))
    live = sum(1 for l in others if l["verdict"] != "quiet")
    score = _sign_of(prim) * 2 + sum(_sign_of(l["verdict"]) for l in others)
    direction = "support" if score >= 2 else ("pressure" if score <= -2 else "mixed")
    return {"agree": agree, "differ": differ, "live": live, "score": score, "direction": direction}


# ---------------------------------------------------------------------------------------------
# the two free paragraphs: what is occupying you, where you are vulnerable
# ---------------------------------------------------------------------------------------------
def _scene(cx: Ctx, area: str, band: Optional[str] = None) -> tuple[str, str]:
    return LEX[area][band or cx.band]


def build_now(cx: Ctx, area: str, driver: Optional[dict], lenses: list[dict], tl: dict,
              until: Optional[date]) -> dict:
    scene, _slip = _scene(cx, area)
    planet = (driver or {}).get("planet", "")
    tone = _tone(planet) if planet else "more present than usual"
    s1 = f"Right now your mind keeps going back to this: {scene}. It tends to feel {tone}."
    s2 = ""
    if until:
        n = _months_between(cx.today, until)
        s2 = ("The influence behind this moves slowly, so it tends to stay for roughly "
              + (f"{n} more months" if n >= 2 else "another few weeks") + ", not days.")
    s3 = ""
    if lenses[1]["verdict"] != "quiet":
        s3 = "Your running life period points at the same area, which is why it keeps coming back."
    facts = {"scene": scene, "nature": tone,
             "reason": ("the slow influence touching this area is " + ("helping" if tl["direction"] == "support" else "testing")),
             "stays": (f"about {_months_between(cx.today, until)} more months" if until else ""),
             "period_points_here": bool(s3)}
    return {"fb": " ".join(x for x in (s1, s2, s3) if x), "facts": facts}


def build_risk(cx: Ctx, area: str, driver: Optional[dict], lenses: list[dict], tl: dict) -> dict:
    _scene_t, slip = _scene(cx, area)
    reasons: list[str] = []
    naadi, dasha, div, jai, trn, ash = lenses
    if naadi["verdict"] == "caution" or (driver and driver["planet"] in _PRESSURE):
        reasons.append("the slow pressure on this area is of the testing kind")
    pc = cx.pc
    house = AREAS[area]["houses"][0]
    lord = CL.lord_of(pc, house)
    if lord and CL.planet_grade(pc, lord) == "strained":
        reasons.append("the ruler of this area is in a weak spot in your birth chart, so there is less cushion")
    if dasha["verdict"] == "caution":
        reasons.append("your running life period works from a weak footing here")
    if ash["verdict"] == "caution":
        reasons.append("this area has fewer natural support points than most")
    if div["verdict"] == "caution":
        reasons.append("the finer sub-charts do not back this area as strongly")
    if jai["verdict"] == "caution":
        reasons.append("the Jaimini clock adds strain here")
    first = f"You may be prone to {slip}."
    if reasons:
        second = "Why this area is exposed: " + "; ".join(reasons[:2]) + "."
    else:
        second = ("The other checks lean supportive, so the risk here is more over-reach than weakness.")
    return {"fb": f"{first} {second}", "fb_short": first,
            "facts": {"slip": slip, "exposed_because": reasons[:2] or ["the checks lean supportive; the risk is over-reach"]}}


# ---------------------------------------------------------------------------------------------
# the next two to three years
# ---------------------------------------------------------------------------------------------
def _naadi_segments(cx: Ctx, area: str) -> list[dict]:
    """Slow-planet stays over the next three years that touch this area, by Chandra Naadi connection."""
    if not NR.CN:
        return []
    days = []
    d = cx.today
    while d <= cx.horizon:
        pos = NR._positions(d)
        if pos:
            days.append((d, pos))
        d += timedelta(days=10)
    out: list[dict] = []
    for planet in SLOW_FORWARD:
        for sg in NR._segments(planet, days):
            first, last = sg["first"], sg["last"]
            if last < cx.today:
                continue
            house = house_from_lagna(sg["sign"], cx.lagna)
            contacts = NR._contacts(cx.pc, planet, sg["sign"])
            w = NR._WEIGHT.get(planet, 2.0)
            score = 0.0
            hit = None
            hw = _house_weight(house, area)
            if hw:
                score += w * 0.5 * hw
            for c in contacts:
                rel = relevance(cx.pc, c["planet"], area)
                if rel >= 0.9:
                    v = w * _KIND_W.get(c["kind"], 1.0) * rel * 0.5
                    score += v
                    if hit is None or v > hit[0]:
                        hit = (v, c)
            if score < 1.6:
                continue
            out.append({"planet": planet, "sign": sg["sign"], "house": house,
                        "start": max(first, cx.today), "end": min(last, cx.horizon),
                        "natal": hit[1] if hit else None, "score": score, "kind": "transit"})
    return out


def _dasha_events(cx: Ctx, area: str) -> list[dict]:
    """Changes of the Vedic sub-period or main period inside the horizon that bring a relevant planet."""
    pc = cx.pc
    out: list[dict] = []
    for row in cx.vim.get("current_md_antardashas") or []:
        a, b = _d(row.get("start")), _d(row.get("end"))
        lord = str(row.get("ad_lord") or "")
        if not (a and b and lord) or b < cx.today or a > cx.horizon:
            continue
        rel = relevance(pc, lord, area)
        if rel >= 0.9:
            out.append({"planet": lord, "start": max(a, cx.today), "end": min(b, cx.horizon),
                        "score": 2.0 + rel, "kind": "dasha", "level": "sub-period", "natal": None})
    try:
        md = cx.vim.get("current_md") or {}
        md_end = _d(md.get("end"))
        if md_end and cx.today < md_end <= cx.horizon:
            seq = cx.vim.get("sequence") or []
            nxt = next((r for r in seq if str(r.get("status")) == "future"), None)
            if nxt:
                lord = str(nxt.get("md_lord") or "")
                rel = relevance(pc, lord, area)
                end = min(_d(nxt.get("end")) or cx.horizon, cx.horizon)
                if rel >= 0.9:
                    out.append({"planet": lord, "start": md_end, "end": end, "score": 3.0 + rel,
                                "kind": "dasha", "level": "main period", "natal": None})
    except Exception:                                                  # noqa: BLE001
        pass
    return out


def _phase_lenses(cx: Ctx, area: str, ph: dict) -> list[dict]:
    when = ph["start"]
    prim = lens_naadi_phase(cx, area, ph)
    probe = when if when >= cx.today else cx.today
    try:
        import report_confluence as CF
        v = CF.vimshottari_at(cx.pc, probe) or {}
        md, ad = v.get("md") or cx.md, v.get("ad") or cx.ad
    except Exception:                                                  # noqa: BLE001
        md, ad = cx.md, cx.ad
    saved = (cx.md, cx.ad)
    cx.md, cx.ad = md, ad
    try:
        dasha = lens_dasha(cx, area)
    finally:
        cx.md, cx.ad = saved
    return [prim, dasha, lens_divisional(cx, area), lens_jaimini(cx, area, probe),
            lens_transit(cx, area, probe), lens_ashtakavarga(cx, area)]


def lens_naadi_phase(cx: Ctx, area: str, ph: dict) -> dict:
    planet = ph["planet"]
    if ph["kind"] == "dasha":
        g = CL.planet_grade(cx.pc, planet)
        verdict = {"strong": "support", "strained": "caution"}.get(g, "mixed")
        plain = {"support": "A strong planet for this area takes over the running period.",
                 "caution": "A weak planet for this area takes over the running period.",
                 "mixed": "A mixed planet for this area takes over the running period."}[verdict]
        return _lens("naadi", "Chandra Naadi", verdict, plain,
                     f"{ph['level'].capitalize()} of {_role(cx.pc, planet)}, graded {g}.")
    base = 1.0 if planet == "Jupiter" else -1.0
    nat = ph.get("natal")
    if nat:
        g = CL.planet_grade(cx.pc, nat["planet"])
        val = base * (0.6 if (base < 0 and g == "strong") else (1.3 if (base < 0 and g == "strained") else 1.0))
    else:
        val = base * 0.6
    verdict = "support" if val > 0.5 else ("caution" if val < -0.5 else "mixed")
    plain = {"support": "A helping slow planet passes over this area.",
             "caution": "A slowing, testing planet passes over this area.",
             "mixed": "A slow planet passes over this area with a mixed effect."}[verdict]
    tech = (f"{planet} moves through {ph['sign']} (your {_ord(ph['house'])} house)" +
            (f" and {'rests on' if nat['kind'] == 'sits on' else 'looks at'} your birth {_role(cx.pc, nat['planet'])}"
             if nat else "") + ".")
    return _lens("naadi", "Chandra Naadi", verdict, plain, tech)


def _overlap(a: dict, b: dict) -> float:
    lo, hi = max(a["start"], b["start"]), min(a["end"], b["end"])
    if hi <= lo:
        return 0.0
    shorter = min((a["end"] - a["start"]).days, (b["end"] - b["start"]).days)
    return (hi - lo).days / max(1, shorter)


def _via(cx: Ctx, c: dict, area: str) -> str:
    if c["kind"] == "dasha":
        planet = c["planet"]
    else:
        planet = str((c.get("natal") or {}).get("planet") or "")
    if planet:
        return AREA_CHANNEL.get((area, planet), PHASE_CHANNEL.get(planet, "steady growth"))
    return NR.HOUSE_SHORT.get(int(c.get("house") or 0), "this area of life")


def _scene_bits(scene: str) -> list[str]:
    """'a, b and c' -> ['a', 'b', 'c'], so each stretch can dwell on a different concern."""
    parts = [p.strip() for p in re.split(r",\s*(?:and\s+)?|\s+and\s+", scene) if p.strip()]
    return parts or [scene]


def _phase_fb(kind: str, idx: int, topic: str, via: str, scene: str, tone: str, advice: dict,
              again: bool, *, prev_kind: Optional[str], used_tips: set) -> str:
    tip = advice["support" if kind == "support" else "pressure"]
    first_use = tip not in used_tips
    used_tips.add(tip)
    if again:
        return_frames = {
            "support": [
                f"A familiar source of support may return around {topic}, through {via}. Something you began earlier could benefit from a second look or a fresh conversation.",
                f"Support you have seen before may become available again for {topic}, linked with {via}. This can be a chance to continue something rather than start from scratch.",
                f"Another opening may echo an earlier one around {topic}, with {via} helping. Use what you learned previously and keep expectations realistic.",
                f"The later return of support around {topic} may feel familiar, especially through {via}. Build on an existing effort instead of adding too many new commitments.",
            ],
            "pressure": [
                f"A familiar pressure may return around {topic}, this time through {via}. You may recognise the pattern quickly, which can help you respond with more patience.",
                f"The demands around {topic} may echo an earlier patch, now involving {via}. Recognising the pattern can help you avoid repeating the same reaction.",
                f"Another slower patch may revisit {topic} through {via}. Keep plans flexible and rely on habits that helped you before.",
                f"A later demand around {topic} may resemble previous pressure from {via}. Pace yourself and deal with one responsibility at a time.",
            ],
            "mixed": [
                f"A familiar mixed pattern may return around {topic}, shaped by {via}. Past experience can help you use the easier moments without overreacting to the slow ones.",
                f"An earlier mix of encouragement and delay may revisit {topic}, with {via} involved. Keep your response measured rather than expecting a straight line.",
                f"The next mixed patch around {topic} may resemble a previous one, shaped by {via}. Use the openings, but leave room for revisions.",
                f"Later, an old pattern of starts and pauses may return to {topic} through {via}. Familiarity can help you stay practical.",
            ],
        }[kind]
        text = return_frames[min(idx, len(return_frames) - 1)]
    else:
        frames = {
            "support": [
                f"Life may feel more cooperative around {topic}, especially through {via}. Matters like {scene} could move with less resistance.",
                f"After that, the pace around {topic} may become easier to work with. Support through {via} can help you act on something you have been postponing.",
                f"Earlier efforts around {topic} may begin to show results, helped along by {via}. Keep the next step practical rather than waiting for a perfect opening.",
                f"A more supportive window may open around {topic}, with {via} creating room for progress. Use it to strengthen what is already working.",
            ],
            "pressure": [
                f"Progress around {topic} may feel slower, with {via} asking for patience. Matters like {scene} could feel {tone}; steady effort is likely to work better than a forced decision.",
                f"The pressure around {topic} may increase, this time through {via}. Delays do not necessarily mean failure, but they may ask you to adjust the plan.",
                f"A demanding patch around {topic} may call for restraint, particularly where {via} is concerned. Small, consistent actions are likely to help more than one big push.",
                f"Later, {topic} may again feel {tone}, with {via} setting the pace. Protect your energy and avoid treating a temporary slowdown as a final answer.",
            ],
            "mixed": [
                f"For {topic}, progress and pauses may alternate. Developments through {via} could help with {scene}, but not every delay is likely to resolve at once.",
                f"The pattern around {topic} may stay uneven: some movement through {via}, followed by moments that ask you to wait or revise.",
                f"You may see both encouragement and frustration around {topic}, shaped by {via}. Keep what works and avoid reading too much into one slow week.",
                f"Later, {topic} may swing between easier and slower patches through {via}. Flexibility could matter more than pushing for a fixed outcome.",
            ],
        }[kind]
        text = frames[min(idx, len(frames) - 1)]
    if first_use:
        text += " " + tip
    return text


def build_phases(cx: Ctx, area: str, limit: int = 4) -> list[dict]:
    cands = _naadi_segments(cx, area) + _dasha_events(cx, area)
    cands = [c for c in cands if c["end"] > c["start"] and (c["end"] - c["start"]).days >= 45]
    cands.sort(key=lambda c: -c["score"])
    kept: list[dict] = []
    for c in cands:
        if any(_overlap(c, k) > 0.6 for k in kept):
            continue
        kept.append(c)
        if len(kept) >= limit:
            break
    kept.sort(key=lambda c: c["start"])
    out = []
    seen_driver: set = set()
    used_tips: set = set()
    for c in kept:
        lenses = _phase_lenses(cx, area, c)
        tl = tally(lenses)
        band = cx.band_at(c["start"])
        scene, _slip = LEX[area][band]
        topic = AREAS[area]["topic"]
        kind = {"support": "support", "pressure": "pressure", "mixed": "mixed"}[tl["direction"]]
        planet = c["planet"]
        via = _via(cx, c, area)
        dkey = (planet, c.get("sign"), (c.get("natal") or {}).get("planet"), c["kind"])
        again = dkey in seen_driver
        seen_driver.add(dkey)
        idx = len(out)
        if again:
            head = {
                "support": ("Support returns", "Familiar support", "A second opening", "Renewed support"),
                "pressure": ("Pressure returns", "A familiar demand", "Pressure repeats", "Another careful patch"),
                "mixed": ("A familiar mixed patch", "Mixed signals return", "A repeat of ebbs and flows", "Another uneven patch"),
            }[kind][min(idx, 3)]
        else:
            head = {
                "support": ("More support", "A clearer opening", "Results begin to show", "A useful window"),
                "pressure": ("A demanding patch", "Slower progress", "A careful stretch", "Patience needed"),
                "mixed": ("Progress with pauses", "An uneven patch", "Mixed signals", "Stay flexible"),
            }[kind][min(idx, 3)]
        bits = _scene_bits(scene)
        bit = bits[idx % len(bits)]
        fb = _phase_fb(kind, idx, topic, via, bit, _tone(planet), ADVICE[area], again,
                       prev_kind=(out[-1]["kind"] if out else None),
                       used_tips=used_tips)
        out.append({"start": c["start"], "end": c["end"], "kind": kind, "head": head, "planet": planet,
                    "lenses": lenses, "tally": tl, "fb": fb, "band": band, "scene": scene, "bit": bit, "via": via,
                    "again": again,
                    "nature": _tone(planet) if kind != "support" else "easier, with help turning up",
                    "advice": ADVICE[area]["support" if kind == "support" else "pressure"],
                    "source": c["kind"]})
    return out


def build_remedy(cx: Ctx, area: str, driver: Optional[dict], lenses: list[dict], tl: dict) -> list[dict]:
    pc = cx.pc
    planets: list[tuple[str, str]] = []
    if driver:
        if driver["planet"] in _PRESSURE and tl["direction"] != "support":
            planets.append((driver["planet"], "the pressure on this area, which asks for patience and consistency"))
        elif driver["planet"] == "Jupiter":
            planets.append(("Jupiter", "the support available to this area, which you want to use well"))
    house = AREAS[area]["houses"][0]
    lord = CL.lord_of(pc, house)
    if lord and CL.planet_grade(pc, lord) == "strained" and all(p != lord for p, _ in planets):
        planets.append((lord, "the ruler of this area, which is weak in your chart"))
    for p in (cx.ad, cx.md):
        if len(planets) >= 2:
            break
        if relevance(pc, p, area) >= 0.9 and all(p != q for q, _ in planets):
            planets.append((p, "the planet running your current life period"))
    if not planets:
        planets.append((AREAS[area]["karakas"][0], "the natural indicator of this area"))
    out = []
    for p, why in planets[:2]:
        day, mantra, act = PLANET_REMEDY.get(p, ("", "", ""))
        out.append({"planet": p, "why": why, "day": day, "mantra": mantra, "act": act})
    return out


def build_personality(pc: dict) -> list[dict]:
    from report_confluence import LAGNA_TRAIT, MOON_TRAIT

    lagna = str((pc.get("lagna") or {}).get("sign")
                or (pc.get("meta") or {}).get("lagna_sign") or "")
    moon = (pc.get("planets") or {}).get("Moon") or {}
    moon_sign = str(moon.get("sign") or "")
    nak = str(moon.get("nakshatra") or moon.get("nakshatra_name") or "")
    ak = str((pc.get("jaimini") or {}).get("atmakaraka") or "")
    if not ak:
        ak = next((str(k.get("planet") or "") for k in (pc.get("cara_karakas") or {}).get("karakas", [])
                   if k.get("role") == "Atmakarak"), "")
    out = []
    for source, value, table in (
        ("D1 rising sign", lagna, LAGNA_TRAIT),
        ("Moon sign", moon_sign, MOON_TRAIT),
        ("Birth star", nak, STAR_TRAIT),
    ):
        if value and table.get(value):
            out.append({"source": source, "value": value, "text": table[value]})
    if ak and AK_TRAIT.get(ak):
        out.append({"source": "Jaimini Atmakaraka", "value": ak, "text": AK_TRAIT[ak]})
    return out


# ---------------------------------------------------------------------------------------------
# assemble
# ---------------------------------------------------------------------------------------------
def build(pc: dict, today: Optional[date] = None, *, use_llm: bool = True) -> dict:
    today = today or date.today()
    cx = Ctx(pc, today)
    ranking = score_areas(cx)
    areas = []
    for i, row in enumerate(ranking[:2]):
        area, driver = row["area"], row["driver"]
        lenses = all_lenses(cx, area, driver)
        tl = tally(lenses)
        until = driver_until(cx, driver)
        areas.append({
            "area": area, "label": AREAS[area]["label"], "rank": i, "score": row, "driver": driver,
            "lenses": lenses, "tally": tl, "until": until,
            "now": build_now(cx, area, driver, lenses, tl, until),
            "risk": build_risk(cx, area, driver, lenses, tl),
            "phases": build_phases(cx, area),
            "remedy": build_remedy(cx, area, driver, lenses, tl),
        })
    from gemstone_remedy import build_remedy_report
    data = {"cx": cx, "areas": areas, "ranking": ranking, "by_model": False,
            "personality": build_personality(pc), "gemstones": build_remedy_report(pc)}
    if use_llm:
        _apply_llm(data)
    return data


# ---------------------------------------------------------------------------------------------
# the model: rewords facts, nothing else
# ---------------------------------------------------------------------------------------------
_SYSTEM = """You are an experienced Vedic astrologer talking to one client across a table: warm, plain-spoken, human.

For each numbered UNIT you get a KIND, the client's age, a TOPIC and plain FACTS that were computed from the chart. Write ONE short passage per unit in your own natural words, using ONLY those facts.

KINDS
- NOW: what is occupying the client at present and what it feels like. Present tense.
- RISK: where the client is most exposed or likely to slip, and why. Present tense.
- NEXT: what one coming stretch tends to feel like and one sensible thing to do in it. The units of a topic are consecutive stretches of the same story, in time order.

HOW IT SHOULD SOUND
- Like a kind, plain-spoken person talking to one client: short sentences, everyday words, no report language.
- Do not copy the facts' wording back; say it the way you would say it aloud. Do not list the examples as a list.
- Every passage must read differently from the others: different opening, different sentence shape, a different thing to dwell on. For NEXT units say how this stretch differs from the one before it (easier, heavier, a repeat, a pause) instead of re-describing the topic.
- Avoid reusing distinctive phrases from another passage; ordinary connecting words are fine.
- When a fact lists several associations, use only the one most relevant to the topic. Never recite the whole list.

HARD RULES
- Exactly one passage per unit, in the same order. 1-3 short sentences, 25-60 words.
- Speak to "you". Be honest and hedged: use may, might, tends to, chances are, likely. Never use the word "will" and never state anything as certain.
- Use ONLY the facts and examples given. Do not invent events, people, amounts or outcomes.
- Do NOT name any planet, sign, house, date, month, year or number. Do not say how long anything lasts.
- No jargon (dasha, nakshatra, house, aspect, transit, natal, Naadi, karma). No illness, accident, death, divorce or money-disaster words.
- Pitch the wording to the client's age and stage of life.
- No bullets, no markdown."""

_CACHE: dict[str, list[str]] = {}
_FUTURE = re.compile(r"\b(will|won't|going to|definitely|certainly|guarantee\w*|you'll|it'll)\b", re.I)
_EXPECT = re.compile(r"\b(?:should|ought to|is bound to|are bound to)\s+(?:feel|be|get|become|ease|improve|start|begin|"
                     r"turn|bring|help|open)\b", re.I)
_HEDGE_MORE = re.compile(r"\b(usually|typically|generally|expect|chance|try|worth|helps?|can|should|more easily|"
                         r"less likely|tend|prone|feels?|sometimes|somewhat|a bit|seem\w*|appear\w*)\b", re.I)
_LASTS = re.compile(r"\b(anytime soon|any time soon|for a long time|for good|forever|going away|for months|for years|"
                    r"won't last|will pass|for the next while)\b", re.I)
_EASY = re.compile(r"\b(relief|easier|easing|eases|ease up|help (?:starts|arrives|turns up|comes)|"
                   r"supportive|support comes|smooth\w*|fruit)\b", re.I)
_HARD = re.compile(r"\b(testing|harder|heavier|pressure|demanding|struggle\w*|obstacle\w*|difficult\w*|challenges?|"
                   r"don't rush|do not rush)\b", re.I)
_TIMING = re.compile(r"\b(in the coming (?:weeks?|days?|months?)|(?:next|coming) few (?:weeks?|days?|months?)|right now|"
                     r"soon|immediately|next stretch|coming phase|following period|following that|"
                     r"(?:first|second|third|fourth) (?:stretch|phase|period|one)|"
                     r"of (?:two|three|four|five)|the (?:first|second|third|fourth) of)\b", re.I)
_STILTED = re.compile(r"\b(snail's pace|turtle's pace|slow influence|lingering feeling|stay steady and mindful|"
                      r"keep moving forward with confidence|don't rush into decisions|do not rush into decisions|"
                      r"(?:helping|testing|mixed) stretch)\b", re.I)
_INSTRUCTION_LEAK = re.compile(
    r"\b(no new advice needed|no need for new advice|just (?:say|note|focus)|already written|as instructed|"
    r"this (?:unit|passage)|previous instructions|writing instructions)\b", re.I)
_WORD = re.compile(r"[a-z']+")
_BUDGET_SECS = 70.0
_DEADLINE = [0.0]


def _grams(text: str, n: int = 4) -> set:
    w = _WORD.findall(text.lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def _repeat_problem(text: str, others: list[str]) -> Optional[str]:
    """A passage must not reuse a run of five words from a passage already accepted."""
    mine = _grams(text, 5)
    for o in others:
        if o and mine & _grams(o, 5):
            return "repeats wording used in another passage; say it differently"
    return None


def _item_problems(x: str, kind: str, pk: str = "") -> list[str]:
    """Why one model passage is not acceptable (empty list: it is). pk: direction of a NEXT stretch."""
    bad: list[str] = []
    if _LASTS.search(x):
        bad.append("says how long it lasts")
    if _EXPECT.search(x):
        bad.append("states an outcome as expected; say it may or might happen")
    if _INSTRUCTION_LEAK.search(x):
        bad.append("echoes writing instructions instead of speaking to the reader")
    if _STILTED.search(x):
        bad.append("uses stock phrases or report language; speak naturally")
    if kind == "NEXT" and _TIMING.search(x):
        bad.append("gives timing or counts stretches; the dates are shown separately")
    if kind == "NEXT" and pk == "pressure" and _EASY.search(x):
        bad.append("sounds easy, but this stretch is a testing one")
    if kind == "NEXT" and pk == "support" and _HARD.search(x):
        bad.append("sounds heavy, but this stretch is a helping one")
    words = len(x.split())
    lo, hi = (18, 85) if kind == "NEXT" else (14, 75)
    if words < lo or words > hi:
        bad.append(f"between {lo + 6} and {hi - 20} words")
    m = NR._JARGON.search(x)
    if m:
        bad.append(f"jargon word '{m.group(0)}'")
    if NR._DANGER.search(x):
        bad.append("danger or guaranteed outcome")
    if any(ch in x for ch in ("*", "#", "<", ">", "\u2022")) or re.search(r"\d", x):
        bad.append("digits or symbols")
    if NR._MONTH_WORD.search(x):
        bad.append("names a month")
    if _FUTURE.search(x):
        bad.append("states an outcome as certain")
    for pl in NR._PLANET_NAMES:
        if re.search(rf"\b{pl}\b", x):
            bad.append(f"names {pl}")
    if not (NR._HEDGE.search(x) or _HEDGE_MORE.search(x)):
        bad.append("no hedge word (may, might, tends to, likely)")
    if re.search(r"\b(native|the client)\b", x, re.I):
        bad.append("not addressed to 'you'")
    if NR._ENDS.search(x) and kind != "NEXT":
        bad.append("says how long it lasts")
    return bad


def _units(data: dict, only: Optional[str] = None) -> list[dict]:
    cx: Ctx = data["cx"]
    units: list[dict] = []
    for a in data["areas"]:
        if only and a["area"] != only:
            continue
        f = a["now"]["facts"]
        units.append({"kind": "NOW", "ref": (a["area"], "now", None), "topic": AREAS[a["area"]]["topic"],
                      "facts": f"On the client's mind: {f['scene']}. It tends to feel: {f['nature']}. "
                               f"{'Their running life period points at the same area. ' if f['period_points_here'] else ''}"
                               f"The slow influence behind it moves slowly, so it lingers for a while."})
        r = a["risk"]["facts"]
        units.append({"kind": "RISK", "ref": (a["area"], "risk", None), "topic": AREAS[a["area"]]["topic"],
                      "facts": f"Where people slip: {r['slip']}. Why they are exposed: {'; '.join(r['exposed_because'])}."})
        nph = len(a["phases"])
        for j, ph in enumerate(a["phases"]):
            prev = a["phases"][j - 1] if j else None
            direction = {"support": "helping", "pressure": "testing", "mixed": "mixed"}
            if prev is None:
                place = "This is the next stretch to come."
            else:
                same = "the same kind of" if prev["kind"] == ph["kind"] else "a different kind of"
                place = (f"It follows a {direction[prev['kind']]} stretch and is {same} stretch"
                         + (", and the same influence is coming back." if ph.get("again") else "."))
            first_kind = all(p["kind"] != ph["kind"] for p in a["phases"][:j])
            step = f" Sensible step: {ph['advice']}" if first_kind or j == nph - 1 else ""
            units.append({"kind": "NEXT", "ref": (a["area"], "phase", j), "topic": AREAS[a["area"]]["topic"],
                          "pk": ph["kind"],
                          "facts": (f"{place} This one is a {direction[ph['kind']]} stretch. "
                                    f"What it touches in the client's life: {ph['via']}. "
                                    f"One thing that may be on the client's mind then: {ph['bit']}. "
                                    f"It tends to feel: {ph['nature']}.{step}")})
    return units


def _write(units: list[dict], age: int) -> list[Optional[str]]:
    """One passage per unit, or None for a unit the model could not write acceptably.

    Each passage is checked on its own; only the failures are asked for again, so one stubborn unit
    cannot throw away the good ones."""
    n = len(units)
    out: list[Optional[str]] = [None] * n
    try:
        from core.config import S
        if not S.llm_tab_enabled("full_report"):
            return out
        from core.llm_client import complete_model
        from pydantic import BaseModel, ConfigDict, Field
    except Exception:                                                  # noqa: BLE001
        return out
    if not units:
        return out

    class _Item(BaseModel):
        model_config = ConfigDict(extra="forbid")
        text: str = Field(default="", max_length=620)

    class _Out(BaseModel):
        model_config = ConfigDict(extra="forbid")
        items: list[_Item] = Field(default_factory=list, max_length=24)

    def _ask(idx: list[int], extra_notes: dict[int, list[str]]) -> Optional[list[str]]:
        """One model call for the units in idx. None: the endpoint is unusable, stop trying."""
        blocks = []
        for k, i in enumerate(idx, 1):
            u = units[i]
            fix = f"\nFix this: {'; '.join(extra_notes[i])}" if extra_notes.get(i) else ""
            blocks.append(f"UNIT {k} ({u['kind']})\nTopic: {u['topic']}\nFacts: {u['facts']}{fix}")
        done = [t for t in out if t]
        avoid = ("\n\nAlready written for this client (do not reuse any of their phrases):\n- "
                 + "\n- ".join(done)) if done else ""
        user = (f"The client is {age} years old.\n\n" + "\n\n".join(blocks) + avoid +
                f"\n\nWrite exactly {len(idx)} passages.")
        key = hashlib.sha1(user.encode()).hexdigest()
        texts = _CACHE.get(key)
        if texts is None:
            try:
                got = complete_model(_Out, _SYSTEM, user, temperature=0.7)
            except Exception as exc:                                   # noqa: BLE001
                print(f"[report_focus] model failed: {type(exc).__name__}: {exc}", flush=True)
                return None
            if got is None:
                return None
            texts = [i.text.strip().strip('"') for i in got.items]
        return texts

    def _take(i: int, t: str) -> bool:
        bad = _item_problems(t, units[i]["kind"], units[i].get("pk", ""))
        rep = _repeat_problem(t, [x for x in out if x])
        if rep:
            bad.append(rep)
        if bad:
            notes[i] = bad
            return False
        out[i] = t
        return True

    todo = list(range(n))
    notes: dict[int, list[str]] = {}
    for _attempt in range(3):
        if not todo or time.monotonic() > _DEADLINE[0]:
            break
        texts = _ask(todo, notes)
        if texts is None:
            return out
        if len(texts) != len(todo):
            # the model lost count: ask for these one at a time rather than lose them all
            still = []
            for i in todo:
                one = _ask([i], notes)
                if one is None:
                    return out
                if len(one) != 1 or not _take(i, one[0]):
                    still.append(i)
            todo = still
            continue
        todo = [i for i, t in zip(todo, texts) if not _take(i, t)]
    if todo:
        print(f"[report_focus] model gave up on {len(todo)} of {n} passages: "
              f"{ {units[i]['ref'][1]: notes.get(i) for i in todo} }"[:600], flush=True)
    return out


def _apply_llm(data: dict) -> None:
    """One model call per area; each passage is accepted or falls back to the deterministic wording."""
    _DEADLINE[0] = time.monotonic() + _BUDGET_SECS            # a report never waits on the model for long
    for a in data["areas"]:
        units = _units(data, only=a["area"])
        texts = _write(units, data["cx"].age)
        if not any(texts):
            continue
        data["by_model"] = True
        by_ref = {u["ref"]: t for u, t in zip(units, texts)}
        a["now"]["text"] = by_ref.get((a["area"], "now", None))
        a["risk"]["text"] = by_ref.get((a["area"], "risk", None))
        for j, ph in enumerate(a["phases"]):
            ph["text"] = by_ref.get((a["area"], "phase", j))


# ---------------------------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------------------------
_CSS = """
:root{--bg:#0f172a;--card:#1e293b;--text:#f8fafc;--muted:#94a3b8;--accent:#38bdf8;--border:#334155;
--warn:#f59e0b;--pos:#10b981;--crit:#ef4444;--info:#60a5fa}
*{box-sizing:border-box}
body{margin:0;padding:20px 14px;background:var(--bg);color:var(--text);
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;line-height:1.6;font-size:15px}
.wrap{max-width:760px;margin:0 auto}
.hero{background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);border:1px solid var(--border);border-radius:16px;
padding:22px 24px;margin-bottom:20px;box-shadow:0 8px 30px rgba(0,0,0,.3)}
.hero h1{margin:0 0 4px;font-size:22px;font-weight:700}
.hero .subtitle{color:var(--accent);font-size:13.5px;margin-bottom:14px}
.kicker{font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:var(--warn);font-weight:800;margin-bottom:6px}
.meta-chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{background:rgba(15,23,42,.8);border:1px solid var(--border);border-radius:999px;padding:4px 12px;font-size:12.5px;color:var(--muted)}
.chip b{color:var(--text)}
.hero p{margin:14px 0 0;color:#e2e8f0;font-size:14.5px}
.area{background:var(--card);border:1px solid var(--border);border-left:4px solid var(--accent);border-radius:14px;
padding:20px 22px;margin-bottom:18px}
.area.second{border-left-color:var(--info)}
.area h2{margin:0 0 2px;font-size:19px}
.area .tagline{color:var(--muted);font-size:12.5px;margin:0 0 14px}
.blk{margin:0 0 14px}
.blk h3{margin:0 0 4px;font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--accent)}
.blk.risk h3{color:var(--warn)}
.blk p{margin:0;color:#e2e8f0;font-size:15px}
.check{color:var(--muted);font-size:12.5px;margin:2px 0 10px}
details.proof{border:1px dashed var(--border);border-radius:10px;padding:8px 12px;margin-top:6px}
details.proof>summary{cursor:pointer;color:var(--muted);font-size:13px}
.lens{display:flex;gap:10px;align-items:flex-start;margin:10px 0 0;font-size:13.5px}
.lens .v{flex:0 0 74px;text-align:center;border-radius:999px;padding:2px 0;font-size:11.5px;font-weight:700;border:1px solid var(--border)}
.v.support{color:var(--pos);border-color:var(--pos)}.v.caution{color:var(--crit);border-color:var(--crit)}
.v.mixed{color:var(--warn);border-color:var(--warn)}.v.quiet{color:var(--muted)}
.lens b{color:var(--text)}.lens .tech{display:block;color:var(--muted);font-size:12.3px;margin-top:2px}
.rank{color:var(--muted);font-size:12.5px;margin:10px 0 0}
.buy-card{background:#16181d;border:1px solid #c9a227;border-radius:14px;padding:20px 22px;margin:20px 0}
.buy-card h3{margin:0 0 6px;font-size:18px;color:#f4d79b}
.buy-card p{margin:0 0 12px;color:#e2e8f0;font-size:14.5px}
.cta-btn{display:inline-block;background:#c9a227;color:#16181d;font-weight:700;text-decoration:none;border-radius:10px;padding:10px 18px}
.next{background:var(--card);border:1px solid var(--border);border-left:4px solid var(--pos);border-radius:14px;padding:20px 22px;margin-bottom:18px}
.next h2{margin:0 0 4px;font-size:19px}
.phase{border-top:1px solid var(--border);padding:12px 0 6px}
.phase:first-of-type{border-top:0}
.phase .when{font-weight:700}
.phase .tag{font-size:11.5px;font-weight:700;border-radius:999px;padding:1px 10px;margin-left:8px;border:1px solid var(--border)}
.tag.support{color:var(--pos);border-color:var(--pos)}.tag.pressure{color:var(--crit);border-color:var(--crit)}
.tag.mixed{color:var(--warn);border-color:var(--warn)}
.phase p{margin:4px 0 6px;color:#e2e8f0}
.remedy{background:var(--card);border:1px solid var(--border);border-left:4px solid var(--warn);border-radius:14px;padding:20px 22px;margin-bottom:18px}
.remedy h2{margin:0 0 8px;font-size:19px}
.remedy li{margin:0 0 10px;color:#e2e8f0}
.fine{color:var(--muted);font-size:12.3px;margin-top:18px}
details.workings{border:1px solid var(--border);border-radius:12px;padding:10px 14px;margin:18px 0;background:var(--card)}
details.workings>summary{cursor:pointer;color:var(--muted)}
"""


def _gender_word(pc: dict) -> str:
    g = (pc.get("meta") or {}).get("gender")
    return "Female" if g in (1, "female", "f", "F", "Female") else "Male"


def _hero(pc: dict, cx: Ctx, name: str, *, title: str = "Your Reading Right Now",
          subtitle: str = "Where you are in life's timing, and what it is touching",
          intro: bool = True) -> str:
    meta = pc.get("meta") or {}
    planets = pc.get("planets") or {}
    moon = planets.get("Moon") or {}
    lagna = str(meta.get("lagna_sign") or (pc.get("lagna") if isinstance(pc.get("lagna"), str) else (pc.get("lagna") or {}).get("sign")) or "")
    moon_sign = str(moon.get("sign") or "")
    nak = str(moon.get("nakshatra") or moon.get("nakshatra_name") or "")
    first = (name or "").split()[0] if name else ""
    chips = []
    if first:
        chips.append(f"Native: <b>{_e(first)}</b> ({_gender_word(pc)})")
    if meta.get("dob"):
        chips.append(f"DOB: <b>{_e(str(meta['dob']))}</b>")
    if lagna:
        chips.append(f"<b>{_e(lagna)} rising</b>")
    if moon_sign:
        chips.append(f"<b>Moon in {_e(moon_sign)}</b>")
    if nak:
        chips.append(f"<b>Nakshatra: {_e(nak)}</b>")
    chips.append(f"<b>{_e(cx.md)} Mahadasha</b>")
    if cx.ad:
        chips.append(f"<b>{_e(cx.ad)} Antardasha</b>")
    chips.append(f"Report Date: <b>{cx.today.strftime('%d %b %Y')}</b>")
    sent = ""
    if intro and lagna and moon_sign:
        sent = (f"This chart is read from {_e(lagna)} lagna, with the Moon in {_e(moon_sign)}"
                f"{f' ({_e(nak)})' if nak else ''}. You are in a {_e(cx.md)} mahadasha, "
                f"with {_e(cx.ad)} running the current antardasha." if cx.ad else
                f"This chart is read from {_e(lagna)} lagna. You are in a {_e(cx.md)} mahadasha.")
    return (f'<div class="hero"><h1>{_e(title)}{(" — " + _e(first)) if first else ""}</h1>'
            f'<div class="subtitle">{_e(subtitle)}</div>'
            f'<div class="kicker">YOUR CHART SIGNATURE</div>'
            f'<div class="meta-chips">' + "".join(f'<span class="chip">{c}</span>' for c in chips) + "</div>"
            + (f"<p>{sent}</p>" if sent else "") + "</div>")


def _lens_html(lenses: list[dict]) -> str:
    label = {"support": "supports", "caution": "cautions", "mixed": "mixed", "quiet": "quiet"}
    rows = []
    for i, l in enumerate(lenses):
        name = l["name"] + (" (primary)" if i == 0 else "")
        rows.append(f'<div class="lens"><span class="v {l["verdict"]}">{label[l["verdict"]]}</span>'
                    f'<span><b>{_e(name)}</b> - {_e(l["plain"])}<span class="tech">{_e(l["tech"])}</span></span></div>')
    return "".join(rows)


def _proof_html(a: dict, ranking: list[dict]) -> str:
    tl = a["tally"]
    prim = a["lenses"][0]["verdict"]
    if prim in ("support", "caution"):
        line = (f"Primary reading says <b>{'helping' if prim == 'support' else 'testing'}</b>. "
                f"{tl['agree']} of the other 5 checks {'agrees' if tl['agree'] == 1 else 'agree'}, "
                f"{tl['differ']} {'differs' if tl['differ'] == 1 else 'differ'}, "
                f"{5 - tl['agree'] - tl['differ']} {'is' if 5 - tl['agree'] - tl['differ'] == 1 else 'are'} neutral or quiet.")
    else:
        line = "The primary reading is mixed, so the other checks are shown as context."
    me = next((r for r in ranking if r["area"] == a["area"]), None)
    why = ""
    if me:
        why = (f'<div class="rank">Why this area was chosen: Chandra Naadi activity {me["naadi"]:.1f}, '
               f'running period {me["dasha"]:.1f}, life-stage weight {me["age"]:.1f} (total {me["total"]:.1f}).</div>')
    return (f'<details class="proof"><summary>How this was checked (tap to open)</summary>'
            f'<div data-astrology-facts="1"><p class="check">{line}</p>{_lens_html(a["lenses"])}{why}</div></details>')


def _personality_html(data: dict) -> str:
    traits = data.get("personality") or []
    if not traits:
        return ""
    blocks = "".join(f'<div class="blk"><p>{_e(t["text"])}</p></div>' for t in traits)
    facts = "".join(f'<p class="check"><b>{_e(t["source"])}:</b> {_e(t["value"])}</p>' for t in traits)
    return ('<section class="area personality"><h2>Your personality</h2>'
            '<p class="tagline">How you tend to act, respond under pressure and grow</p>'
            + blocks +
            '<details class="proof"><summary>Which chart factors shape these traits</summary>'
            '<div data-astrology-facts="1"><p class="check">These stable traits use the birth chart, '
            'Moon, birth star and Jaimini indicator rather than current transits.</p>'
            + facts + '</div></details></section>')


def _gem_proof(items: list[dict]) -> str:
    rows = []
    for item in items:
        snap = item.get("snap") or {}
        detail = "; ".join(item.get("reasons") or [])
        rows.append(f'<p class="check"><b>{_e(item["planet"])}</b> — {_e(item.get("role") or "")}. '
                    f'{_e(detail)} Placement: {_e(str(snap.get("sign") or ""))}, '
                    f'house {_e(str(snap.get("house") or ""))}.</p>')
    return ('<details class="proof"><summary>Why these gemstone rules apply to your chart</summary>'
            '<div data-astrology-facts="1">' + "".join(rows) + '</div></details>')


def _gemstone_free_html(data: dict) -> str:
    report = data.get("gemstones") or {}
    avoided = list(report.get("avoid") or []) + list(report.get("mantra_strict") or [])
    optional = list(report.get("sub_gem_optional") or [])
    rows = []
    for item in avoided:
        gem = item.get("gem") or {}
        primary, sub = gem.get("gem") or "", gem.get("sub") or ""
        names = f'{_e(primary)}</b> and <b>{_e(sub)}' if sub else _e(primary)
        rows.append(f'<li><b>{names}</b> — avoid {"both" if sub else "this stone"} for this chart.</li>')
    for item in optional:
        gem = (item.get("gem") or {}).get("gem") or ""
        rows.append(f'<li><b>{_e(gem)}</b> — avoid the primary stone; a substitute is not automatically suitable.</li>')
    if not rows:
        rows.append('<li>No hard avoidance flag came up. Still do not buy a gemstone without a personal check.</li>')
    return ('<section class="area"><h2>Gemstones not to wear</h2>'
            '<p class="tagline">Specific to your chart, not general gemstone rules</p><ul>'
            + "".join(rows) + '</ul>' + _gem_proof(avoided + optional) + '</section>')


def _gemstone_paid_html(data: dict) -> str:
    from gemstone_remedy import _customer_role_label

    report = data.get("gemstones") or {}
    wear = list(report.get("primary_wear") or [])
    strict = list(report.get("mantra_strict") or [])
    optional = list(report.get("sub_gem_optional") or [])
    avoided = list(report.get("avoid") or [])
    wear_rows = []
    for item in wear:
        gem = item.get("gem") or {}
        trial = ("A three-day trial is required before regular or permanent wear."
                 if item.get("verdict") == "test_required" else
                 "Use a three-day trial before regular wear.")
        window = ""
        w_from, w_until = _d(item.get("wear_from")), _d(item.get("wear_until"))
        if w_from and w_until:
            if (w_until - w_from).days > 6 * 365:       # a very long span is no timing advice at all
                window = f' Traditional timing: it may be started from {_e(_full_date(w_from))}.'
            else:
                window = (f' Traditional timing: {_e(_full_date(w_from))} to {_e(_full_date(w_until))}.')
        alternative = gem.get("sub") or ""
        alt_text = (f'Lower-cost alternative: {_e(alternative)} (the same trial applies).<br>'
                    if alternative else "")
        wear_rows.append(
            f'<li><b>{_e(gem.get("gem") or "")}</b> for {_e(item["planet"])} — '
            f'{_e(_customer_role_label(item.get("role") or ""))}.<br>{alt_text}'
            f'Traditional setting: {_e(str(gem.get("metal") or "").lower())}; '
            f'{_e(str(gem.get("finger") or "").lower())}; {_e(gem.get("day") or "")}. '
            f'{_e(trial)}{window}</li>')
    if not wear_rows:
        wear_rows.append('<li>No primary gemstone is advised now. Use the practices in What helps instead.</li>')
    caution_rows = []
    for item in strict:
        gem = item.get("gem") or {}
        caution_rows.append(
            f'<li><b>Avoid {_e(gem.get("gem") or "")} and {_e(gem.get("sub") or "")}.</b> '
            f'For {_e(item["planet"])}, use {_e(gem.get("mantra") or "")}; '
            f'charity: {_e(gem.get("charity") or "")}.</li>')
    for item in optional:
        gem = item.get("gem") or {}
        caution_rows.append(
            f'<li><b>Avoid {_e(gem.get("gem") or "")}.</b> '
            f'The optional substitute is {_e(gem.get("sub") or "")}, only after a three-day trial. '
            f'Preferred practice: {_e(gem.get("mantra") or "")}.</li>')
    for item in avoided:
        gem = item.get("gem") or {}
        caution_rows.append(
            f'<li><b>Avoid {_e(gem.get("gem") or "")} and {_e(gem.get("sub") or "")}.</b> '
            f'Use {_e(gem.get("mantra") or "")} instead.</li>')
    cautions = ('<h3>Avoid or use with caution</h3><ul>' + "".join(caution_rows) + '</ul>'
                if caution_rows else "")
    return ('<section class="remedy"><h2>Full gemstone guidance</h2>'
            '<h3>Suggested gemstones</h3><ul>' + "".join(wear_rows) + '</ul>' + cautions
            + _gem_proof(wear + strict + optional + avoided) +
            '<p class="fine">Traditional chart guidance only. A trial is a precaution, not a guarantee of suitability; '
            'stop if uncomfortable.</p></section>')


def _area_card(a: dict, ranking: list[dict], idx: int) -> str:
    now_txt = a["now"].get("text") or a["now"]["fb"]
    risk_txt = a["risk"].get("text") or (a["risk"]["fb"] if idx == 0 else a["risk"]["fb_short"])
    if idx > 0 and not a["risk"].get("text"):
        now_txt = a["now"]["fb"].split(" The influence behind")[0]
    tag = "Your main focus right now" if idx == 0 else "Also active right now"
    return (f'<section class="area{" second" if idx else ""}"><h2>{_e(a["label"])}</h2>'
            f'<p class="tagline">{tag}</p>'
            f'<div class="blk"><h3>What is occupying you</h3><p>{_e(now_txt)}</p></div>'
            f'<div class="blk risk"><h3>Where you are vulnerable</h3><p>{_e(risk_txt)}</p></div>'
            f'{_proof_html(a, ranking)}</section>')


def _unlock_card(data: dict, price: int) -> str:
    a1, a2 = data["areas"][0], data["areas"][1]
    n1, n2 = len(a1["phases"]), len(a2["phases"])
    horizon = f'{_mon(data["cx"].today)} to {_mon(data["cx"].horizon)}'
    return (f'<div class="buy-card" id="unlock"><h3>To see what happens next, the remedies and full gemstone guidance, unlock the full report</h3>'
            f'<p>We found {n1} dated turning stretches for {_e(a1["label"].lower())} and {n2} for {_e(a2["label"].lower())} '
            f'between {horizon}, each with the checks behind it, plus practical remedies and safe wearing instructions.</p>'
            f'<a class="cta-btn" href="#unlock" data-unlock="1">Unlock full report · ₹{_e(str(price))}</a></div>')


def _next_html(a: dict, cx: Ctx) -> str:
    if not a["phases"]:
        body = ('<p>No dated stretch in the next three years strongly touches this area, so expect steady, '
                'ordinary movement here rather than a turning point.</p>')
    else:
        rows = []
        prev_end: Optional[date] = None
        for ph in a["phases"]:
            txt = ph.get("text") or ph["fb"]
            start = _d(ph["start"])
            if prev_end and start and (start - prev_end).days > 120:
                rows.append(f'<p class="fine gap">Between {_e(_mon(prev_end))} and {_e(_mon(start))} nothing '
                            f'here stands out, so expect steady, ordinary movement.</p>')
            prev_end = _d(ph["end"]) or prev_end
            rows.append(
                f'<div class="phase"><div><span class="when">{_e(_span(ph["start"], ph["end"]))}</span>'
                f'<span class="tag {ph["kind"]}">{_e(ph["head"])}</span></div><p>{_e(txt)}</p>'
                f'<details class="proof"><summary>The checks behind this stretch</summary>'
                f'<div data-astrology-facts="1"><p class="check">{ph["tally"]["agree"]} of the other 5 checks '
                f'{"agrees" if ph["tally"]["agree"] == 1 else "agree"} with the primary reading.</p>'
                f'{_lens_html(ph["lenses"])}</div></details></div>')
        body = "".join(rows)
    return (f'<section class="next"><h2>{_e(a["label"])}: the next {HORIZON_YEARS} years</h2>{body}</section>')


def _remedy_html(data: dict) -> str:
    blocks = []
    for a in data["areas"]:
        items = "".join(
            f'<li><b>{_e(r["planet"])}</b> ({_e(r["why"])}). On {_e(r["day"])}: {_e(r["act"])}. '
            f'If you like a mantra: {_e(r["mantra"])}, 108 times.</li>' for r in a["remedy"])
        blocks.append(f'<h3 style="margin:10px 0 6px;font-size:15px">{_e(a["label"])}</h3><ul>{items}</ul>')
    return ('<section class="remedy"><h2>What helps</h2>' + "".join(blocks) +
            '<p class="fine">These are traditional supports and sensible habits, not substitutes for professional advice.</p></section>')


def render(pc: dict, data: dict, *, name: str = "", paid: bool = False, price: int = 298) -> str:
    cx: Ctx = data["cx"]
    parts = [_hero(pc, cx, name), _personality_html(data)]
    for i, a in enumerate(data["areas"]):
        parts.append(_area_card(a, data["ranking"], i))
    if paid:
        for a in data["areas"]:
            parts.append(_next_html(a, cx))
        parts.extend((_remedy_html(data), _gemstone_paid_html(data)))
    else:
        parts.extend((_gemstone_free_html(data), _unlock_card(data, price)))
    parts.append('<p class="fine">For guidance and self-reflection only.</p>')
    try:
        from report_shell import INTERACT
    except Exception:                                                  # noqa: BLE001
        INTERACT = ""
    first = (name or "").split()[0] if name else "Your"
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"/>'
            f'<title>{_e(first)} - Your Reading Right Now</title><style>{_CSS}</style></head>'
            f'<body><!-- secnav: this short report has no section rail --><div class="wrap">{"".join(parts)}</div>'
            f'{INTERACT}</body></html>')


def full_report(pc: dict, *, name: str = "", today: Optional[date] = None, price: int = 298,
                bundle_price: int = 298, lang: str = "en", use_llm: bool = True) -> tuple:
    """Same return shape as report_render.full_report: (free_html, paid_html, meta)."""
    import report_render as RD
    today = today or date.today()
    data = build(pc, today, use_llm=use_llm)
    free = RD._scrub(render(pc, data, name=name, paid=False, price=price))
    paid = RD._scrub(render(pc, data, name=name, paid=True, price=price))
    meta = {
        "design": "focus-v1", "freeDesign": "focus-v1", "language": "en", "price": price,
        "bundlePrice": bundle_price,
        "areas": [{"area": a["area"], "label": a["label"], "direction": a["tally"]["direction"],
                   "agree": a["tally"]["agree"], "differ": a["tally"]["differ"],
                   "phases": len(a["phases"])} for a in data["areas"]],
        "byModel": data["by_model"], "ageBand": data["cx"].band,
        "freeSections": ["Your chart signature and running period", "Your personality",
                         "Your main focus right now", "Also active right now", "Gemstones not to wear"],
        "paidSections": ["The next three years, area by area", "What helps", "Full gemstone guidance"],
        "llm": {"enabled": data["by_model"]},
        "teasers": {},
    }
    return free, paid, meta


_Q_LABELS = {
    "en": {
        "answer": "Your answer", "now": "What is happening now", "dates": "Dates and transition",
        "current": "Current sub-period", "next": "Next transition", "changes": "this sub-period changes",
        "remedy": "Remedy and what to do", "checked": "How this answer was checked",
        "unlock": "Unlock the exact transition, timing and remedy",
        "unlock_text": "See when your current sub-period changes, any window specific to your question, and the practical steps and remedy for your chart.",
        "unlock_gem": "Unlock the full wearing instructions",
        "unlock_gem_text": "See exactly how to use the recommended stone, or the safer mantra and donation alternative for your chart.",
    },
    "hi_en": {
        "answer": "Aapka jawab", "now": "Abhi kya chal raha hai", "dates": "Tareekh aur badlav",
        "current": "Chal rahi antardasha", "next": "Agla badlav", "changes": "yeh antardasha badlegi",
        "remedy": "Upay aur kya karein", "checked": "Yeh jawab kaise jaancha gaya",
        "unlock": "Sahi badlav, samay aur upay unlock karein",
        "unlock_text": "Apni antardasha kab badlegi, aapke prashna ka samay aur kundli ke anuroop kadam aur upay dekhein.",
        "unlock_gem": "Dharan karne ke poore niyam dekhein",
        "unlock_gem_text": "Ratna kaise dharan karein, ya aapki kundli ke liye surakshit mantra aur daan ka vikalp dekhein.",
    },
    "te_en": {
        "answer": "Mee samadhanam", "now": "Ippudu em jarugutundi", "dates": "Tedee mariyu marpu",
        "current": "Nadustunna antardasha", "next": "Tarvata marpu", "changes": "ee antardasha marutundi",
        "remedy": "Pariharam mariyu em cheyali", "checked": "Ee samadhanam ela parishilinchamu",
        "unlock": "Sariayina marpu, samayam mariyu pariharam unlock cheyandi",
        "unlock_text": "Mee antardasha eppudu marutundo, mee prashna samayam mariyu kundaliki tagina steps, pariharam chudandi.",
        "unlock_gem": "Dharimpa chese poorthi vivaranu chudandi",
        "unlock_gem_text": "Ratnam ela dharinchalo, leda mee kundaliki surakshitamaina mantra, daanam margam chudandi.",
    },
}


def _full_date(value: Any) -> str:
    d = _d(value)
    return d.strftime("%d %b %Y") if d else ""


def _question_period(pc: dict) -> dict:
    vim = pc.get("vimshottari") or {}
    ad = next((a for a in vim.get("current_md_antardashas") or [] if a.get("status") == "current"), {})
    return {"lord": str(ad.get("ad_lord") or ""), "from": _full_date(ad.get("start")),
            "until": _full_date(ad.get("end"))}


def _question_proof(reading: Any, facts: dict, *, paid: bool, lang: str) -> str:
    import question_reading as QR

    lk = QR._lang_key(lang)
    labels = QR._LABELS[lk]
    q = _Q_LABELS[lk]
    vote = {1: ("support", "supports"), 0: ("mixed", "mixed"), -1: ("caution", "cautions")}
    lenses = []
    for item in reading.lenses:
        try:
            kind, word = vote[int(item.get("vote", 0))]
        except (TypeError, ValueError, KeyError):
            continue
        name = labels.get("lens_" + str(item.get("key") or ""), str(item.get("key") or ""))
        lenses.append(f'<div class="lens"><span class="v {kind}">{word}</span><span><b>{_e(name)}</b></span></div>')
    if facts["domain_key"] == "gemstones_remedies":
        rows = list(reading.why) if paid else []
    elif facts["domain_key"] == "out_of_domain":
        rows = []
    else:
        rows = QR._facts_list(facts)
    if not paid:
        rows = [r for r in rows if not re.search(r"\b(?:19|20)\d{2}\b", r)]
    elif facts["domain_key"] not in ("gemstones_remedies", "out_of_domain"):
        have = {str(w).strip() for w in reading.why}
        rows += [t for _fid, _lens, t in QR._findings_full(facts, lang) if t.strip() not in have][:6]
    if not lenses and not rows:
        return ""
    facts_html = ('<ul>' + "".join(f'<li class="check">{_e(row)}</li>' for row in rows) + '</ul>'
                  if rows else "")
    return (f'<details class="proof"><summary>{_e(q["checked"])}</summary>'
            f'<div data-astrology-facts="1">{"".join(lenses)}{facts_html}</div></details>')


def _question_unlock(reading: Any, facts: dict, period: dict, *, lang: str, price: int) -> str:
    import question_reading as QR

    q = _Q_LABELS[QR._lang_key(lang)]
    gem = facts["domain_key"] == "gemstones_remedies"
    has_more = bool(reading.timing.strip() or reading.steps or (period["until"] and not gem))
    if not has_more or reading.stance == "not_astrological":
        return ""
    title = q["unlock_gem"] if gem else q["unlock"]
    text = q["unlock_gem_text"] if gem else q["unlock_text"]
    return (f'<div class="buy-card" id="unlock"><h3>{_e(title)}</h3><p>{_e(text)}</p>'
            f'<a class="cta-btn" href="#unlock" data-unlock="1">Unlock full answer · ₹{_e(str(price))}</a></div>')


def render_question(pc: dict, reading: Any, facts: dict, *, name: str = "", paid: bool = False,
                    price: int = 298, lang: str = "en", today: Optional[date] = None) -> str:
    import question_reading as QR

    today = today or date.today()
    cx = Ctx(pc, today)
    lk = QR._lang_key(lang)
    labels = QR._LABELS[lk]
    q = _Q_LABELS[lk]
    period = _question_period(pc)
    out_of_scope = reading.stance == "not_astrological"
    parts = [_hero(pc, cx, name, title=q["answer"],
                   subtitle="One question, one direct answer, checked against your chart", intro=False)]
    parts.append(
        f'<section class="area"><h2>&ldquo;{_e(facts["question"])}&rdquo;</h2>'
        f'<p class="tagline">{_e(labels[reading.stance])}</p>'
        f'<div class="blk"><h3>{_e(q["answer"])}</h3><p>{_e(reading.answer)}</p></div></section>')
    answer_words = set(re.findall(r"[a-z']+", reading.answer.lower()))

    def _already_said(reason: str) -> bool:           # the answer's reason sentence is often a plain fact
        words = re.findall(r"[a-z']+", reason.lower())
        return bool(words) and sum(w in answer_words for w in words) / len(words) >= 0.5

    visible_reasons = [r for r in QR.plain_reasons(facts, lang) if not _already_said(r)]
    if visible_reasons:
        shown = visible_reasons if paid else visible_reasons[:2]
        items = "".join(f'<li>{_e(reason)}</li>' for reason in shown)
        parts.append(f'<section class="area second"><h2>{_e(q["now"])}</h2><ul>{items}</ul></section>')
    if paid and not out_of_scope and facts["domain_key"] != "gemstones_remedies":
        rows = []
        if period["lord"]:
            span = " to ".join(x for x in (period["from"], period["until"]) if x)
            rows.append(f'<p><b>{_e(q["current"])}:</b> {_e(period["lord"])}'
                        + (f' · {_e(span)}' if span else "") + '</p>')
        if period["until"]:
            rows.append(f'<p><b>{_e(q["next"])}:</b> {_e(period["until"])}, {_e(q["changes"])}.</p>')
        if reading.timing.strip():
            rows.append(f'<p><b>{_e(labels["when"])}:</b> {_e(reading.timing)}</p>')
        if rows:
            parts.append(f'<section class="next"><h2>{_e(q["dates"])}</h2>{"".join(rows)}</section>')
    if paid and not out_of_scope and reading.steps:
        items = "".join(f'<li>{_e(step)}</li>' for step in reading.steps)
        fine = ("A three-day trial is a precaution, not a guarantee of suitability; stop wearing the stone if you feel "
                "uncomfortable." if facts["domain_key"] == "gemstones_remedies" else
                "Traditional supports and sensible habits, not substitutes for professional advice.")
        parts.append(f'<section class="remedy"><h2>{_e(q["remedy"])}</h2><ul>{items}</ul>'
                     f'<p class="fine">{_e(fine)}</p></section>')
    if not out_of_scope:
        parts.append(_question_proof(reading, facts, paid=paid, lang=lang))
    if not paid:
        parts.append(_question_unlock(reading, facts, period, lang=lang, price=price))
    parts.append('<p class="fine">For guidance and self-reflection only.</p>')
    try:
        from report_shell import INTERACT
    except Exception:                                                  # noqa: BLE001
        INTERACT = ""
    first = (name or "").split()[0] if name else "Your"
    return (f'<!DOCTYPE html><html lang="{_e(lk)}"><head><meta charset="utf-8"/>'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"/>'
            f'<title>{_e(first)} - {_e(q["answer"])}</title><style>{_CSS}</style></head>'
            f'<body><!-- secnav: this short report has no section rail --><div class="wrap">{"".join(parts)}</div>'
            f'{INTERACT}</body></html>')


def question_report(pc: dict, conf: Any, reading: Any, facts: dict, *, by_model: bool,
                    name: str = "", price: int = 298, lang: str = "en",
                    today: Optional[date] = None) -> tuple:
    import question_reading as QR
    import report_render as RD

    today = today or date.today()
    free = RD._scrub(render_question(pc, reading, facts, name=name, paid=False,
                                     price=price, lang=lang, today=today))
    paid = RD._scrub(render_question(pc, reading, facts, name=name, paid=True,
                                     price=price, lang=lang, today=today))
    specialist = getattr(conf, "specialist_readings", None) or {}
    meta = {
        "design": "focus-v1", "freeDesign": "focus-v1", "language": lang,
        "answer": {
            "label": QR.headline(reading.answer), "confidence": reading.confidence or "moderate",
            "direction": "support" if reading.stance == "favourable" else "caution",
            "breakthrough": facts.get("next_window") or conf.breakthrough_period,
        },
        "question": facts["question"], "area": conf.domain_title, "price": price,
        "llm": {"enabled": bool(by_model)}, "reading": reading.model_dump(),
        "_facts": {
            "question": facts["question"], "domain": conf.domain_title, "lagna": conf.lagna,
            "primary_house": conf.primary_house, "primary_lord": conf.primary_house_lord,
            "breakthrough_period": conf.breakthrough_period,
            "specialist_readings": {
                key: {"status": value.get("status", "unavailable"),
                      "count": len(value.get("findings") or [])}
                for key, value in specialist.items()
                if isinstance(value, dict) and key != "evaluation_date"
            },
        },
        "freeSections": ["Your answer", "What is happening now", "Collapsed chart checks"],
        "paidSections": ["Exact period transition", "Question-specific timing", "Remedy and what to do"],
        "teasers": {},
    }
    return free, paid, meta
