"""A Chandra Naadi relationship reading for the questions people actually bring.

"Will she come back?", "will we break up?", "will my divorce go through?", "when will
I get a girlfriend?" are the questions most readers ask. The general question page
answers them with one verdict and a list of lenses. This module adds a section built
for them, from Chandra Naadi alone:

    karaka         the planet that stands for the partner in the chart (Venus for a man,
                   Mars for a woman, per the book's marriage chapter), its dignity, house
                   and whether Saturn, Rahu, Ketu or Mars sit on it.
    pattern        how the book reads Mercury (the way two people talk) with that planet:
                   whether love tends to start well and settle well.
    now            where the transit Moon is touching the birth chart today and whether
                   it is a sensitive moment (Chandrashtama, Manthi, Badhaka, Punarpoo).
    days           the same Moon reading for each of the next 30 days: the days that favour
                   reaching out and the days to hold back. This is the dated, practical
                   part the reader pays for.
    lean           one of "open" / "mixed" / "closed", from the chart only.

Python computes all of it. The model only phrases it, from the numbered facts, and
whatever it writes is checked: no promise of an outcome, no dates, no planet that is not
in the facts. If the model is off or rejected, deterministic wording is used.
"""
from __future__ import annotations

import html
import re
from datetime import date, datetime, time, timedelta
from typing import Any, Optional

_GOOD = ("exalted", "moolatrikona", "own_sign", "friendly_sign", "great_friend_sign")
_BAD = ("debilitated", "enemy_sign", "great_enemy_sign")
_PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
SCAN_DAYS = 30

# ------------------------------------------------------------------ what was asked
_KINDS: tuple[tuple[str, re.Pattern], ...] = tuple(
    (k, re.compile(p, re.I)) for k, p in (
        ("divorce", r"\b(divorce|separat\w*|annul\w*|alimony|custody)\b"),
        ("return", r"\b(come\s+back|comes\s+back|coming\s+back|came\s+back|return\w*|get\s+back|"
                   r"back\s+together|reconcil\w*|patch\s*-?\s*up|talk\s+(?:to\s+me\s+)?again|"
                   r"text\s+me|call\s+me|miss(?:es)?\s+me|reach\s+out|forgive\w*|wapas|wapis|vapas|"
                   r"laut\w*|thirigi|tirigi)\b"),
        ("breakup", r"\b(break\s*-?\s*up|broke\s+up|leave\s+me|left\s+me|leaving\s+me|dump\w*|ghost\w*|"
                    r"ignor\w+|cheat\w*|quarrel\w*|fights?|stay\s+together|last\s+long|survive|ending|"
                    r"toot\w*|chhod\w*|vadili\w*)\b"),
        ("crush", r"\b(crush|say\s+yes|propos\w*|accept\s+me|like\s+me|love\s+me|feel\s+for\s+me)\b"),
        ("find", r"\b(girl\s*friend|boy\s*friend|gf|bf|find\s+love|meet\s+someone|find\s+a\s+partner|"
                r"soul\s*mate|single|dating|true\s+love|premika|premikudu)\b"),
        ("marriage", r"\b(get\s+married|marriage|marry|shaadi|shadi|vivah|pelli|wedding)\b"),
    ))
_TIMING = re.compile(r"\b(when|how\s+long|how\s+soon|by\s+when|kab|eppudu|how\s+many\s+(?:days|months))\b", re.I)


def intent(question: str) -> dict[str, str]:
    q = " ".join((question or "").lower().split())
    kind = next((k for k, rx in _KINDS if rx.search(q)), "other")
    pron = ("she" if re.search(r"\b(she|her|girlfriend|girl\s*friend|wife|gf|premika)\b", q)
            else "he" if re.search(r"\b(he|him|his|boyfriend|boy\s*friend|husband|bf|premikudu)\b", q)
            else "they")
    return {"kind": kind, "asks": "timing" if _TIMING.search(q) else "yes_no", "pron": pron}


# ------------------------------------------------------------------ chart facts
def _state(pc: dict, name: str) -> dict:
    p = (pc.get("planets") or {}).get(name) or {}
    try:
        from astro_precompute import get_dignity
        dig = p.get("dignity") or (get_dignity(name, p.get("sign", "")) if p.get("sign") else "")
    except Exception:                                                 # noqa: BLE001
        dig = p.get("dignity") or ""
    house = int(p.get("house") or 0)
    return {"planet": name, "sign": p.get("sign", ""), "house": house, "dignity": str(dig),
            "combust": bool(p.get("combust")), "hard": house in (6, 8, 12)}


def _strained(st: dict) -> bool:
    return bool(st["hard"] or st["dignity"] in _BAD or st["combust"])


def _strong(st: dict) -> bool:
    return st["dignity"] in _GOOD and not st["combust"]


def _sitting_on(pc: dict, name: str) -> list[str]:
    """Saturn, Rahu, Ketu or Mars in the same sign as ``name``."""
    planets = pc.get("planets") or {}
    sign = (planets.get(name) or {}).get("sign")
    if not sign:
        return []
    return [p for p in ("Saturn", "Rahu", "Ketu", "Mars")
            if p != name and (planets.get(p) or {}).get("sign") == sign]


_PATTERN_EN = {
    (True, True): "Love tends to begin warmly and to settle well once it is steady.",
    (True, False): "Love tends to begin pleasantly, but the early charm needs deliberate care to last.",
    (False, True): "The early stretch of a relationship can feel bumpy; it tends to settle well once trust is built.",
    (False, False): "Relationships ask more patience and clearer talk from you than most; slow, honest steps work best.",
}


def _moon_day(pc: dict, day: date) -> Optional[dict]:
    """Where the Moon touches the chart at noon on ``day``, and whether it is a sensitive day."""
    from chandra_naadi_analysis import (analyze_badhaka, analyze_chandrashtama, analyze_core_methodology,
                                        analyze_manthi_deep, analyze_punarpoo_deep, get_transit_positions)
    transit = get_transit_positions(datetime.combine(day, time(12, 0)))
    if not transit or not (transit.get("Moon") or {}).get("sign"):
        return None
    _r, touched = analyze_core_methodology(pc, transit)
    cautions: list[str] = []
    if analyze_chandrashtama(pc, transit):
        cautions.append("chandrashtama")
    if any(r.rule_id == "V2_TRANSIT_MOON_OVER_MANTHI" for r in analyze_manthi_deep(pc, transit)):
        cautions.append("manthi")
    if any(r.severity == "caution" for r in analyze_badhaka(pc, transit)):
        cautions.append("badhaka")
    if any(r.severity == "caution" for r in analyze_punarpoo_deep(pc, transit)):
        cautions.append("punarpoo")
    return {"touched": list(dict.fromkeys(touched)), "cautions": cautions,
            "moon_sign": transit["Moon"]["sign"]}


def _runs(days: list[date]) -> list[tuple[date, date]]:
    out: list[tuple[date, date]] = []
    for d in sorted(days):
        if out and d - out[-1][1] <= timedelta(days=1):
            out[-1] = (out[-1][0], d)
        else:
            out.append((d, d))
    return out


def _label(a: date, b: date) -> str:
    if a == b:
        return f"{a:%a %d %b}"
    return f"{a:%a %d %b} to {b:%a %d %b}"


def scan_days(pc: dict, love: set[str], strained: dict[str, bool], today: date) -> dict[str, Any]:
    """Which of the next SCAN_DAYS days favour reaching out, and which to hold back."""
    open_days: list[tuple[int, date]] = []
    hold_days: list[date] = []
    for i in range(1, SCAN_DAYS + 1):
        day = today + timedelta(days=i)
        try:
            d = _moon_day(pc, day)
        except Exception as exc:                                      # noqa: BLE001
            print(f"[relationship_naadi] day scan failed: {type(exc).__name__}: {exc}", flush=True)
            return {"open": [], "hold": [], "ok": False, "n_open": 0, "n_hold": 0}
        if d is None:
            continue
        touched = set(d["touched"])
        mine = touched & love
        steady = {p for p in mine if not strained.get(p)}
        if d["cautions"] or (mine and not steady):
            hold_days.append(day)
            continue
        score = (2 if "Jupiter" in touched else 0) + 2 * bool(steady) + (1 if "Venus" in touched else 0)
        if score >= 3:
            open_days.append((score, day))
    best = sorted(open_days, key=lambda t: (-t[0], t[1]))[:6]
    chosen = sorted(d for _s, d in best)
    hold_runs = _runs(hold_days)[:4]
    # The counts are exactly the days the paid page lists, so the teaser never promises more than it shows.
    return {
        "open": [_label(a, b) for a, b in _runs(chosen)],
        "hold": [_label(a, b) for a, b in hold_runs],
        "n_open": len(chosen), "n_hold": sum((b - a).days + 1 for a, b in hold_runs), "ok": True,
    }


# ------------------------------------------------------------------ the reading
def build(pc: dict, question: str, qfacts: dict, *, stance: str, gender: Any = None,
          today: Optional[date] = None, lang: str = "en") -> Optional[dict]:
    """Facts, lean and days for one relationship question, or ``None`` when Naadi cannot run."""
    today = today or date.today()
    try:
        from chandra_naadi_analysis import is_strong, is_weak                 # noqa: F401
    except Exception as exc:                                                  # noqa: BLE001
        print(f"[relationship_naadi] unavailable: {type(exc).__name__}: {exc}", flush=True)
        return None

    ask = intent(question)
    code = None
    if gender not in (None, ""):
        try:
            from core.errors import gender_code
            code = gender_code(gender)
        except Exception:                                                     # noqa: BLE001
            code = None
    karaka_name = "Mars" if code == 1 else "Venus"
    karaka = _state(pc, karaka_name)
    venus = _state(pc, "Venus")
    mercury = _state(pc, "Mercury")
    lord = ((qfacts.get("house") or {}).get("lord") or {})
    lord7 = _state(pc, lord["planet"]) if lord.get("planet") else None

    on_karaka = _sitting_on(pc, karaka_name)
    on_venus = _sitting_on(pc, "Venus") if karaka_name != "Venus" else []
    thaara = (((pc.get("planets") or {}).get("Mars") or {}).get("sign")
              and ((pc.get("planets") or {}).get("Mars") or {}).get("sign")
              == ((pc.get("planets") or {}).get("Saturn") or {}).get("sign"))
    separation = list(dict.fromkeys(on_karaka + on_venus))

    naadi = (qfacts.get("lenses") or {}).get("naadi") or {}
    love = {karaka_name, "Venus"} | ({lord7["planet"]} if lord7 else set())
    strained = {p: _strained(_state(pc, p)) for p in love}
    days = scan_days(pc, love, strained, today)

    # lean: chart only
    stance_pts = {"favourable": 1, "mixed": 0, "difficult": -1}.get(stance, 0)
    score = stance_pts + int(naadi.get("vote", 0))
    score += 1 if _strong(karaka) else -1 if karaka["dignity"] in _BAD or karaka["combust"] else 0
    score -= 1 if separation else 0
    if days["ok"]:
        score += 1 if days["n_open"] >= 3 else -1 if days["n_open"] == 0 else 0
    lean = "open" if score >= 2 else "closed" if score <= -2 else "mixed"

    pattern = _PATTERN_EN[(_strong(mercury), _strong(karaka) or _strong(venus))]

    facts: list[str] = []

    def _fact(text: str) -> None:
        facts.append(f"F{len(facts) + 1}: {text}")

    nm = "the planet of partnership for a man" if karaka_name == "Venus" else "Mars, the planet of the partner for a woman"
    _fact(f"{karaka_name} ({nm}) sits in {karaka['sign']}, house {karaka['house']}"
          + (f", {_dig_words(karaka['dignity'])}" if _dig_words(karaka["dignity"]) else "")
          + (" and is scorched by the Sun (combust)" if karaka["combust"] else "") + ".")
    if separation:
        _fact(f"{' and '.join(separation)} sits with your partnership planet, which brings distance, "
              "delay or misunderstanding in love.")
    if thaara:
        _fact("Mars and Saturn sit together in your chart, so early mistakes in love can be held against "
              "you later; the remedy is to keep disputes private and forgive small things.")
    _fact(pattern)
    if naadi:
        if naadi.get("touched"):
            _fact("Today the Moon is touching your natal " + ", ".join(naadi["touched"]) + ".")
        if naadi.get("good") or naadi.get("bad"):
            if naadi.get("good"):
                _fact(f"{', '.join(naadi['good'])} carries love questions and is well placed, which helps now.")
            if naadi.get("bad"):
                _fact(f"{', '.join(naadi['bad'])} carries love questions but is under strain, so feelings run "
                      "high and decisions made today can be hasty.")
        if naadi.get("cautions"):
            _fact("Today is a sensitive day for the Moon in your chart, so it is a day for listening, "
                  "not for ultimatums.")
    if days["ok"]:
        _fact(f"Over the next {SCAN_DAYS} days the Moon favours reaching out on {days['n_open']} days and "
              f"asks for restraint on {days['n_hold']}.")
    per = qfacts.get("periods") or {}
    if per.get("main") and per.get("sub"):
        _fact(f"You are in the {per['main']} main period with {per['sub']} running as the sub-period.")

    return {
        "kind": ask["kind"], "asks": ask["asks"], "pron": ask["pron"], "lean": lean,
        "karaka": karaka_name, "karaka_state": karaka, "separation": separation, "thaara": bool(thaara),
        "pattern": pattern, "days": days, "facts": facts,
        "next_window": qfacts.get("next_window") or "",
        "now_caution": bool(naadi.get("cautions")),
        "question": " ".join(str(question or "").split())[:240],
    }


def _dig_words(dig: str) -> str:
    return {"exalted": "exalted, at its strongest", "own_sign": "in its own sign, strong",
            "moolatrikona": "in its own sign, strong", "friendly_sign": "in a friendly sign",
            "great_friend_sign": "in a very friendly sign", "debilitated": "debilitated, weak",
            "enemy_sign": "in an unfriendly sign", "great_enemy_sign": "in a very unfriendly sign"}.get(dig, "")


# ------------------------------------------------------------------ wording
_LEAN = {
    "en": {
        "return": {"open": "The door looks open", "mixed": "Mixed signals", "closed": "Needs time and space"},
        "breakup": {"open": "The bond has support", "mixed": "A rough patch", "closed": "Strain is showing"},
        "divorce": {"open": "Room to repair", "mixed": "Unsettled", "closed": "Strain is high"},
        "find": {"open": "Love is coming into view", "mixed": "A slow build", "closed": "Needs patience"},
        "crush": {"open": "Looks receptive", "mixed": "Unclear yet", "closed": "Hold back for now"},
        "marriage": {"open": "Supportive", "mixed": "Mixed", "closed": "Needs patience"},
        "other": {"open": "Supportive", "mixed": "Mixed", "closed": "Needs patience"},
    },
    "hi_en": {k: {"open": "Rasta khula dikhta hai", "mixed": "Milajula sanket", "closed": "Samay aur jagah chahiye"}
              for k in ("return", "breakup", "divorce", "find", "crush", "marriage", "other")},
    "te_en": {k: {"open": "Daari teruchukuntondi", "mixed": "Mishrama sanketalu", "closed": "Samayam, spandana kavali"}
              for k in ("return", "breakup", "divorce", "find", "crush", "marriage", "other")},
}

_UI = {
    "en": {
        "kicker": "Relationship reading · Chandra Naadi", "now": "What is happening",
        "why": "What the Moon and your chart show", "reach": "Days the Moon favours reaching out",
        "hold": "Days to hold back", "do": "What helps", "avoid": "What to avoid",
        "pattern": "How love tends to go for you", "longer": "The longer window",
        "teaser": "We read the Moon's path over your chart for the next {n} days: {o} days that favour reaching "
                  "out and {h} days to hold back. The dates, and what to say and not say, are in the full reading.",
        "lockchip": "See the days and what to say", "cta": "Unlock the dated days",
        "sub": "The days the Moon favours you, the days to hold back, and what to do on each.",
        "no_days": "No day in the next {n} days stands out; steady, kind contact matters more than timing.",
    },
    "hi_en": {
        "kicker": "Rishte ki reading · Chandra Naadi", "now": "Abhi kya ho raha hai",
        "why": "Chandra aur aapki kundli kya dikhate hain", "reach": "Chandra jab baat karne ke liye anukool hai",
        "hold": "Ruk jaane ke din", "do": "Kya madad karega", "avoid": "Kya na karein",
        "pattern": "Aapke liye pyaar aam taur par kaisa chalta hai", "longer": "Lambi avadhi",
        "teaser": "Humne agle {n} din aapki kundli par Chandra ka raasta padha: {o} din baat karne ke liye anukool "
                  "aur {h} din ruk jaane ke. Tarikhen, aur kya kehna hai aur kya nahi, poori reading mein hain.",
        "lockchip": "Din aur kya kehna hai, dekhein", "cta": "Tarikh wale din unlock karein",
        "sub": "Chandra ke anukool din, ruk jaane ke din, aur har din kya karna hai.",
        "no_days": "Agle {n} din mein koi din khaas nahi; samay se zyada narm, steady sampark zaroori hai.",
    },
    "te_en": {
        "kicker": "Bandham reading · Chandra Naadi", "now": "Ippudu emi jarugutondi",
        "why": "Chandrudu mariyu mee kundali emi chupistunnayi", "reach": "Chandrudu maatladataniki anukoolamga unna roju",
        "hold": "Aagalsina roju", "do": "Emi sahayapadutundi", "avoid": "Emi cheyakudadu",
        "pattern": "Mee premalo sadharanamga ela untundi", "longer": "Pedda kaalaparimiti",
        "teaser": "Mee kundali meeda Chandrudi daarini rabone {n} rojulu chadivam: {o} rojulu maatladataniki anukoolam, "
                  "{h} rojulu aagalsinavi. Tedeelu, emi cheppali emi cheppakudadu, poorthi reading lo unnayi.",
        "lockchip": "Rojulu, emi cheppalo chudandi", "cta": "Tedee rojulu unlock cheyandi",
        "sub": "Chandrudu anukoolamga unna rojulu, aagalsina rojulu, prathi roju em cheyali.",
        "no_days": "Rabone {n} rojullo pratyekamaina roju ledu; samayam kante manchi, sthiramaina sambandham mukhyam.",
    },
}

_LEAN_SENT = {
    "open": "Your chart leaves the door open: the signs that decide this lean in your favour.",
    "mixed": "Your chart gives mixed signals: some signs help and some hold it back, so timing and tone matter.",
    "closed": "Your chart asks for time and space: the signs that decide this are under strain right now.",
}
_LEAN_SENT_LOCAL = {
    "hi_en": {"open": "Aapki kundli rasta khula rakhti hai: is baat ko tay karne wale sanket aapke paksh mein hain.",
              "mixed": "Aapki kundli milajula sanket deti hai: kuch madad karte hain, kuch rokte hain, isliye samay aur lehja matter karte hain.",
              "closed": "Aapki kundli samay aur jagah maangti hai: is baat ko tay karne wale sanket abhi dabav mein hain."},
    "te_en": {"open": "Mee kundali daarini teruchi unchutundi: deenini nirnayinche sanketalu mee vaipu unnayi.",
              "mixed": "Mee kundali mishrama sanketalu istundi: konni sahayapadatayi, konni aapatayi, kabatti samayam, maata teeru mukhyam.",
              "closed": "Mee kundali samayam, spandana adugutundi: deenini nirnayinche sanketalu ippudu ottidilo unnayi."},
}
_KIND_OPEN = {
    "return": "About {pron} coming back: ",
    "breakup": "About this relationship holding together: ",
    "divorce": "About the separation: ",
    "find": "About love finding you: ",
    "crush": "About how {pron} feels: ",
    "marriage": "About marriage: ",
    "other": "",
}


_HEADLINE = {
    "return": {"open": "The chart leaves the door open for {pron} to return.",
               "mixed": "The signs are mixed on {obj} returning; your timing and tone will decide a lot.",
               "closed": "The chart asks for time and space before {pron} could return."},
    "breakup": {"open": "This bond has support, and the rough patch can be repaired.",
                "mixed": "This is a rough patch, and what you do in the next days matters.",
                "closed": "The strain is real right now; it needs gentleness more than answers."},
    "divorce": {"open": "There is room to repair this, if both of you want it.",
                "mixed": "Things are unsettled, and they can still move either way.",
                "closed": "The strain is high; slow, calm steps will serve you better than quick ones."},
    "find": {"open": "Love is coming into view for you, and the next weeks matter.",
             "mixed": "Love builds slowly for you; it is not blocked, it is gathering.",
             "closed": "Love needs patience right now; it asks for steadiness, not force."},
    "crush": {"open": "{Pron} may well be receptive to you.",
              "mixed": "It is too early to read how {pron} feels; let it unfold.",
              "closed": "Hold back for now and give {obj} space."},
    "marriage": {"open": "The chart supports this.", "mixed": "The signs are mixed; timing matters.",
                 "closed": "This needs patience for now."},
    "other": {"open": "The chart supports this.", "mixed": "The signs are mixed; timing matters.",
              "closed": "This needs patience for now."},
}


def _headline(b: dict) -> str:
    pron = {"she": "she", "he": "he"}.get(b["pron"], "they")
    obj = {"she": "her", "he": "him"}.get(pron, "them")
    return _HEADLINE[b["kind"]][b["lean"]].format(pron=pron, Pron=pron.capitalize(), obj=obj)


def _fallback_write(b: dict) -> dict[str, Any]:
    pron = b["pron"] if b["pron"] != "they" else "they"
    lead = _KIND_OPEN.get(b["kind"], "").format(pron=pron)
    head = _headline(b)
    happening = (lead + _LEAN_SENT[b["lean"]]).strip()
    why = [re.sub(r"^F\d+:\s*", "", f) for f in b["facts"][:3]]
    do = ["Keep contact calm and short; say one honest thing and leave room for a reply.",
          "Use the favourable days for the conversation that matters."]
    avoid = ["Do not send long messages or ultimatums on the days marked to hold back."]
    if b["kind"] == "divorce":
        avoid.append("Do not make legal decisions on a chart alone; take proper legal advice.")
    return {"headline": head, "happening": happening, "why": why, "do": do, "avoid": avoid}


_SITUATION = {
    "return": "The reader has parted from someone, or lost contact, and hopes they will come back.",
    "breakup": "The reader is in a relationship that is shaky and wonders if it will last.",
    "divorce": "The reader is married and is going through, or fearing, a separation. The other person is the spouse.",
    "find": "The reader is single and wants to know when love will arrive. There is no relationship yet; do not "
            "describe one.",
    "crush": "The reader likes someone and wants to know how they feel. Nothing is settled yet.",
    "marriage": "The reader asks about marriage.",
    "other": "The reader asks about love or partnership.",
}

_SYSTEM = """You are a warm, honest Chandra Naadi astrologer talking to someone worried about a relationship.
Write for the reader directly, using "you" and "your". The reader is hurting or hopeful: be kind, never cold,
never dramatic. You do not promise outcomes.

Use ONLY the FACTS lines. Never name a planet, house, sign or period that is not in them. Never write a month,
a year or a date (dates are shown elsewhere). Never offer rituals, remedies, stones or tricks to win someone back,
and never suggest contacting someone who has asked for distance. Do not blame the other person.
Do not invent causes or events (trust, communication, cheating, family, money, ego, an "ex"); say only what the
facts say. In a divorce the other person is the spouse, not an ex.

Speak to the reader's own situation (use their question). Name the real drivers from the facts in plain words,
for example that the planet of partnership is under strain, or that the Moon is passing over a sensitive point
today. Avoid vague filler like "smoother waters" or "things may improve".

Fields:
- headline: leave as an empty string (it is written elsewhere).
- happening: 2-3 sentences, at most 60 words, saying what seems to be going on between you two, from the facts.
- why: up to 3 short reasons, each from one fact, plain words.
- do: up to 3 short, concrete things that help (about tone, timing, listening).
- avoid: up to 2 short things to avoid.

LEAN is the chart's verdict: "open" = the signs lean in the reader's favour, "mixed" = both ways,
"closed" = the signs are under strain for now. Your wording must match the lean. When the lean is "mixed" or
"closed", never write that someone "will" come back or return; use "may" or "could" or "not yet".
Reply with JSON only."""

_BANNED = re.compile(
    r"\b(guarantee\w*|definitely|certainly|for\s+sure|100\s*%|vashikaran|black\s+magic|tantra|revenge|stalk\w*|"
    r"spy\s+on|love\s+spell|win\s+(?:him|her|them)\s+back|manipulat\w*)\b", re.I)
# Causes the model likes to invent; allowed only when the facts themselves say them.
_INVENTED = ("trust", "communication", "cheat", "cheating", "affair", "infidelity", "ex-partner", "ex partner",
             "third party", "in-laws", "family pressure", "jealous", "jealousy", "ego", "money problems",
             "career pressure", "misunderstanding")
_YEAR = re.compile(r"\b(?:19|20)\d\d\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}\b", re.I)
_SURE_BACK = re.compile(r"\bwill\s+(?:\w+\s+)?(?:come|return|be|get)\s+back\b|\bwill\s+(?:surely\s+)?return\b", re.I)
_DOOMED = re.compile(r"\b(no\s+chance|never\s+(?:come|return|be)|hopeless|it'?s\s+over|doomed|will\s+not\s+return)\b", re.I)


def _problems(w: dict[str, Any], b: dict) -> list[str]:
    text = " ".join([w["headline"], w["happening"], *w["why"], *w["do"], *w["avoid"]])
    out: list[str] = []
    try:
        from llm.validate import enforce_user_voice
        out += [p for p in enforce_user_voice(text) if "you" in p or "third" in p or "empty" in p]
    except Exception:                                                     # noqa: BLE001
        pass
    if _BANNED.search(text):
        out.append("promises or sells an outcome, or suggests a trick or ritual")
    if _YEAR.search(text):
        out.append("names a date or year; dates are shown separately")
    allowed = " ".join(b["facts"])
    for pl in _PLANETS:
        if re.search(rf"\b{pl}\b", text) and not re.search(rf"\b{pl}\b", allowed):
            out.append(f"names {pl}, which the facts do not mention")
            break
    low_text, low_facts = text.lower(), allowed.lower()
    for word in _INVENTED:
        if re.search(rf"\b{re.escape(word)}\b", low_text) and not re.search(rf"\b{re.escape(word)}\b", low_facts):
            out.append(f"mentions {word}, which the facts do not say; do not invent causes")
            break
    if b["kind"] in ("find", "crush") and re.search(r"\byour (?:relationship|partner|marriage|spouse)\b", low_text):
        out.append("the reader is not in a relationship; do not describe one")
    if b["kind"] == "divorce" and re.search(r"\bex[- ]?(?:partner|wife|husband)\b|\breach(?:ing)? out to your ex", low_text):
        out.append("the reader is still married; do not call the spouse an ex")
    if b["lean"] != "open" and _SURE_BACK.search(text):
        out.append("says someone will come back, but the lean is not open; use may or could")
    if b["lean"] == "open" and _DOOMED.search(text):
        out.append("sounds hopeless, but the lean is open")
    if len(w["headline"].split()) > 26 or len(w["happening"].split()) > 80:
        out.append("too long")
    return out


def write(b: dict, *, lang: str = "en") -> dict[str, Any]:
    """The reader-facing prose. Model first, deterministic wording if it fails the checks."""
    fb = _fallback_write(b)
    b["by_model"] = False
    if lang not in ("en", "") and str(lang).lower() not in ("english",):
        return fb               # non-English wording comes from templates
    try:
        from core.config import S
        if not S.llm_tab_enabled("user_question"):
            return fb
        from core.llm_client import complete_model
        from pydantic import BaseModel, ConfigDict, Field
    except Exception:                                                     # noqa: BLE001
        return fb

    class _Write(BaseModel):
        model_config = ConfigDict(extra="forbid")
        headline: str = Field(default="", max_length=200)
        happening: str = Field(default="", max_length=520)
        why: list[str] = Field(default_factory=list, max_length=3)
        do: list[str] = Field(default_factory=list, max_length=3)
        avoid: list[str] = Field(default_factory=list, max_length=2)

    user = "\n".join([
        f"QUESTION KIND: {b['kind']} (the reader asks about {b['pron']}; they want "
        f"{'a time' if b['asks'] == 'timing' else 'a yes or no'}).",
        f"READER'S QUESTION: {b.get('question', '')}",
        "SITUATION: " + _SITUATION.get(b["kind"], _SITUATION["other"]),
        f"LEAN: {b['lean']}", "FACTS:", *b["facts"]])
    problems: list[str] = []
    for _attempt in range(3):
        try:
            got = complete_model(
                _Write, _SYSTEM,
                user if not problems else user + "\n\nYour previous answer was rejected: "
                + "; ".join(problems[:3]) + ". Rewrite it using only the facts.",
                temperature=0.3)
        except Exception as exc:                                          # noqa: BLE001
            print(f"[relationship_naadi] model failed: {type(exc).__name__}: {exc}", flush=True)
            return fb
        if got is None:
            return fb
        w = {"headline": fb["headline"], "happening": got.happening.strip(),
             "why": [x.strip() for x in got.why if x.strip()][:3],
             "do": [x.strip() for x in got.do if x.strip()][:3],
             "avoid": [x.strip() for x in got.avoid if x.strip()][:2]}
        if not w["happening"] or not w["why"]:
            problems = ["a required field is empty"]
            continue
        problems = _problems(w, b)
        if not problems:
            b["by_model"] = True
            w["do"] = w["do"] or fb["do"]
            w["avoid"] = w["avoid"] or fb["avoid"]
            if b["kind"] == "divorce" and not any("legal" in a.lower() for a in w["avoid"]):
                w["avoid"] = (w["avoid"] + fb["avoid"][-1:])[:3]
            return w
    print(f"[relationship_naadi] model rejected: {problems[:3]}", flush=True)
    return fb


def compose(b: dict, *, lang: str = "en") -> dict[str, Any]:
    """The stored, renderable block: wording + days + labels (no raw internals)."""
    lk = lang if lang in ("hi_en", "te_en") else "en"
    prose = write(b, lang=lk)
    if lk != "en":
        prose["headline"] = _LEAN[lk][b["kind"]][b["lean"]]
        prose["happening"] = _LEAN_SENT_LOCAL[lk][b["lean"]]
        prose["why"] = []
        prose["do"], prose["avoid"] = [], []
    return {"kind": b["kind"], "lean": b["lean"], "label": _LEAN[lk][b["kind"]][b["lean"]],
            "headline": prose["headline"], "happening": prose["happening"], "why": prose["why"],
            "do": prose["do"], "avoid": prose["avoid"], "pattern": b["pattern"] if lk == "en" else "",
            "open": b["days"]["open"], "hold": b["days"]["hold"],
            "n_open": b["days"]["n_open"], "n_hold": b["days"]["n_hold"], "days_ok": b["days"]["ok"],
            "scan_days": SCAN_DAYS,
            "next_window": b["next_window"] if b["kind"] in ("find", "marriage", "other") else "",
            "by_model": bool(b.get("by_model")),
            "lang": lk}


# ------------------------------------------------------------------ page
_COLOR = {"open": "#1c6b45", "mixed": "#8a6a1f", "closed": "#a3341f"}
_BG = {"open": "#e9f5ee", "mixed": "#fbf6e4", "closed": "#fbeae6"}


def _e(x: Any) -> str:
    return html.escape(str(x or "").strip())


def _list(items: list[str], style: str = "") -> str:
    return ('<ul style="margin:0;padding-left:18px;font-size:.92rem;line-height:1.55;color:#2c3140;' + style + '">'
            + "".join(f'<li style="margin-bottom:6px;">{_e(i)}</li>' for i in items) + "</ul>")


def _head(text: str, color: str = "#7a4b18") -> str:
    return (f'<div style="font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;font-weight:800;'
            f'color:{color};margin:12px 0 6px;">{_e(text)}</div>')


def render_html(blk: dict, *, paid: bool, price: int = 298) -> str:
    """One card. Free: what is happening and a count. Paid: the dated days and what to do."""
    U = _UI[blk.get("lang") if blk.get("lang") in _UI else "en"]
    color, bg = _COLOR[blk["lean"]], _BG[blk["lean"]]
    out = ['<article class="card rel-naadi" style="background:#fff;border:1px solid #e8e4dc;'
           f'border-left:4px solid {color};border-radius:12px;padding:18px 22px;margin-bottom:14px;'
           'box-shadow:0 2px 8px rgba(0,0,0,.03);">',
           '<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin-bottom:6px;">'
           f'<span style="font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;font-weight:700;'
           f'color:#6a7080;">{_e(U["kicker"])}</span>'
           f'<span class="pill" style="font-size:.68rem;font-weight:700;padding:3px 10px;border-radius:99px;'
           f'background:{bg};color:{color};">{_e(blk["label"])}</span></div>',
           f'<h3 style="font-family:Georgia,serif;font-size:1.15rem;margin:4px 0 8px;color:#1f2430;'
           f'font-weight:600;line-height:1.35;">{_e(blk["headline"])}</h3>',
           _head(U["now"]),
           f'<p style="font-size:.95rem;line-height:1.6;color:#2c3140;margin:0 0 6px;">{_e(blk["happening"])}</p>']
    why = blk.get("why") or []
    if paid and why:
        out += [_head(U["why"]), _list(why)]
    elif why:
        out += [_head(U["why"]), _list(why[:1])]

    if paid:
        if blk.get("days_ok"):
            if blk["open"]:
                out += [_head(U["reach"], "#1c6b45"), _list(blk["open"])]
            else:
                out.append(f'<p style="font-size:.9rem;color:#4a5160;margin:10px 0 0;">'
                           f'{_e(U["no_days"].format(n=blk["scan_days"]))}</p>')
            if blk["hold"]:
                out += [_head(U["hold"], "#a3341f"), _list(blk["hold"])]
        if blk.get("next_window"):
            out += [_head(U["longer"]), f'<p style="font-size:.92rem;line-height:1.55;color:#2c3140;margin:0;">'
                    f'{_e(blk["next_window"])}</p>']
        if blk.get("do"):
            out += [_head(U["do"], "#1c6b45"), _list(blk["do"])]
        if blk.get("avoid"):
            out += [_head(U["avoid"], "#a3341f"), _list(blk["avoid"])]
        if blk.get("pattern"):
            out += [_head(U["pattern"]), f'<p style="font-size:.92rem;line-height:1.55;color:#2c3140;margin:0;">'
                    f'{_e(blk["pattern"])}</p>']
        out.append("</article>")
        return "\n".join(out)

    if blk.get("days_ok"):
        teaser = U["teaser"].format(n=blk["scan_days"], o=blk["n_open"], h=blk["n_hold"])
        out.append(
            '<div class="lock-wrap" data-unlock="1" role="button" tabindex="0" '
            'style="margin:14px 0 4px;border-radius:12px;cursor:pointer;">'
            f'<div class="lock-blur" style="padding:14px 18px;font-size:.88rem;line-height:1.55;">'
            f'<b>{_e(U["reach"])}:</b> the best days are marked here, with what to say on each one. '
            f'<b>{_e(U["hold"])}:</b> the days to stay quiet are marked here too.</div>'
            f'<div class="lock-over" data-unlock="1"><span class="lock-chip" data-unlock="1" '
            f'style="font-size:.72rem;padding:7px 18px;cursor:pointer;">&#128274; {_e(U["lockchip"])}</span></div></div>'
            f'<p style="font-size:.84rem;line-height:1.5;color:#4a5160;margin:8px 0 0;">&#127769; {_e(teaser)}</p>')
    out.append("</article>")
    return "\n".join(out)


def public(blk: dict) -> dict:
    """What goes into report meta: enough for the plain summary, nothing internal."""
    keep = ("kind", "lean", "label", "headline", "happening", "n_open", "n_hold", "scan_days", "days_ok",
            "by_model", "lang")
    out = {k: blk.get(k) for k in keep}
    out["open"] = list(blk.get("open") or [])
    out["hold"] = list(blk.get("hold") or [])
    return out
