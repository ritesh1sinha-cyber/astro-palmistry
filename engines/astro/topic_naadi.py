"""Chandra Naadi readings for the two other questions people ask most: work and health.

Same design as ``relationship_naadi`` (and it reuses its day scan and page):

    * Python works out the chart facts, a lean ("open" / "mixed" / "closed") and the
      next 30 days from where the transit Moon touches the birth chart.
    * A model only phrases the numbered facts, and what it writes is checked; if it
      fails, deterministic wording is used.
    * Free page: what is happening, one reason, and the NUMBER of favourable and
      hold-back days. Paid page: the dated days, what helps, what to avoid.

Work: promotion or a raise, changing or finding a job, losing a job (layoffs, being
fired), business. Health: illness, surgery, recovery, the mind. The health card never
predicts death or illness by name, never advises against treatment, and always says to
follow the doctor.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any, Optional

import relationship_naadi as RN
from relationship_naadi import SCAN_DAYS, _BAD, _e, _label, _moon_day, _runs, _sitting_on, _state, _strained, _strong

_REAL = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")

# ------------------------------------------------------------------ what was asked
def _rx(items):
    return tuple((k, re.compile(p, re.I)) for k, p in items)


_KINDS = {
    "career": _rx((
        ("layoff", r"\b(fired|firing|laid\s*off|lay\s*offs?|layoffs?|terminat\w*|sacked|let\s+go|"
                   r"(?:lose|losing|lost)\s+(?:my|the)\s+job|job\s+loss|job\s+security|redundan\w*|pip)\b"),
        ("promotion", r"\b(promot\w*|appraisal|hike|raise|increments?|salary|pay\s*rise|designation|bonus|"
                      r"recogni\w*|senior\s+role|team\s*lead)\b"),
        ("business", r"\b(business|start\s*-?\s*up|venture|entrepreneur\w*|own\s+company|self[- ]employed|shop)\b"),
        ("jobchange", r"\b(jobs?|naukri|change\s+(?:my\s+)?(?:company|career|field)|switch\w*|resign\w*|quit\w*|"
                      r"offers?|interviews?|join\w*|placement|unemployed|jobless|transfer|relocat\w*|work\s+abroad)\b"),
    )),
    "health": _rx((
        ("surgery", r"\b(surger\w*|operation|operate|procedure|transplant|angioplasty|bypass|c\s*-?\s*section|"
                    r"biopsy|implant)\b"),
        ("mind", r"\b(anxi\w*|depress\w*|stress\w*|panic|mental|insomnia|sleep\w*|burn\s*out|overthink\w*|"
                 r"mood|trauma|therapy|worr\w+)\b"),
        ("recovery", r"\b(recover\w*|cure[sd]?|heal(?:ed|ing|s)?|get\s+better|well\s+again|treatment|relapse|chronic|"
                     r"long[- ]term|better)\b"),
        ("disease", r"\b(diseases?|illness\w*|sick\w*|ill|diagnos\w*|cancer|diabetes|thyroid|heart|bp|"
                    r"blood\s+pressure|pain|infection|fever|disorder|condition|tumou?r|asthma|migraine|"
                    r"arthritis|ulcer|kidney|liver|skin|allerg\w*|symptoms?)\b"),
    )),
}
_DEFAULT_KIND = {"career": "other", "health": "disease"}


def intent(topic: str, question: str) -> dict[str, str]:
    q = " ".join((question or "").lower().split())
    kind = next((k for k, rx in _KINDS[topic] if rx.search(q)), _DEFAULT_KIND[topic])
    return {"kind": kind, "asks": "timing" if RN._TIMING.search(q) else "yes_no"}


# ------------------------------------------------------------------ wording
_LABEL = {
    "career": {
        "promotion": {"open": "Recognition looks supported", "mixed": "A slow climb", "closed": "Build quietly for now"},
        "jobchange": {"open": "A move looks supported", "mixed": "A move needs care", "closed": "Prepare before you move"},
        "layoff": {"open": "Your position looks steady", "mixed": "Some pressure at work", "closed": "Pressure is high"},
        "business": {"open": "Supports your own venture", "mixed": "Possible, with care", "closed": "Build slowly first"},
        "other": {"open": "Supportive", "mixed": "Mixed", "closed": "Needs patience"},
    },
    "health": {
        "surgery": {"open": "Supports a smooth path", "mixed": "Go carefully", "closed": "Extra care advised"},
        "recovery": {"open": "Healing is supported", "mixed": "A gradual recovery", "closed": "Slow, steady recovery"},
        "disease": {"open": "Vitality looks supported", "mixed": "Care and routine matter", "closed": "Pressure on health"},
        "mind": {"open": "Your mind looks supported", "mixed": "Ups and downs", "closed": "Your mind needs rest"},
    },
}
_LABEL["health"]["other"] = _LABEL["health"]["disease"]

_HEADLINE = {
    "career": {
        "promotion": {"open": "The chart backs a rise in position or pay.",
                      "mixed": "A rise is possible but not clear-cut; timing and visibility decide it.",
                      "closed": "Recognition is slow right now; steady work now builds the case for later."},
        "jobchange": {"open": "A move looks supported, and the right offer can come.",
                      "mixed": "A move is possible but not smooth; compare offers carefully.",
                      "closed": "This is a time to prepare rather than jump; a hasty change could cost you."},
        "layoff": {"open": "Your position looks steady; the signs of a sudden exit are not strong.",
                   "mixed": "There is some pressure at work; keep your results visible and your options open.",
                   "closed": "Pressure at work is high right now; protect your savings and keep your skills ready."},
        "business": {"open": "The chart supports building work of your own.",
                     "mixed": "Your own venture is possible, with care over timing and money.",
                     "closed": "Build slowly and keep your risk small for now."},
        "other": {"open": "The chart supports your work.", "mixed": "The signs for work are mixed; timing matters.",
                  "closed": "Work needs patience for now."},
    },
    "health": {
        "surgery": {"open": "The chart supports a smooth procedure and good healing.",
                    "mixed": "The signs are mixed; follow your surgeon's plan closely and allow time to heal.",
                    "closed": "The chart asks for extra care around this; follow medical advice and do not rush recovery."},
        "recovery": {"open": "The chart supports steady recovery.",
                     "mixed": "Recovery looks gradual, with good stretches and slower ones.",
                     "closed": "Recovery looks slow right now; patience and steady care matter most."},
        "disease": {"open": "Your vitality looks supported.",
                    "mixed": "Your health picture is mixed; routine and care matter.",
                    "closed": "Your chart shows pressure on health; check-ups and rest matter."},
        "mind": {"open": "Your mind looks supported, and calmer stretches are coming.",
                 "mixed": "Your mind has ups and downs; routine and rest help.",
                 "closed": "Your mind is under strain right now; rest, sleep and talking to someone you trust help."},
    },
}
_HEADLINE["health"]["other"] = _HEADLINE["health"]["disease"]

_LEAN_SENT = {
    "career": {
        "open": "Your chart backs this: the signs that decide work matters lean in your favour.",
        "mixed": "Your chart gives mixed signals: some signs help and some hold things back, so timing and how "
                 "you present yourself matter.",
        "closed": "Your chart asks for patience: the signs that decide this are under strain right now.",
    },
    "health": {
        "open": "Your chart supports this: the signs that decide health matters lean in your favour.",
        "mixed": "Your chart gives mixed signals: some signs help and some strain you, so routine and care matter.",
        "closed": "Your chart asks for extra care: the signs that decide this are under strain right now, so rest "
                  "and following medical advice matter most.",
    },
}

_SITUATION = {
    "career": {
        "promotion": "The reader hopes for a promotion, a raise or recognition at work.",
        "jobchange": "The reader is thinking about changing jobs, or is looking for a job.",
        "layoff": "The reader fears losing their job (layoffs, being fired) and wants to know how safe it is.",
        "business": "The reader asks about running or starting their own business.",
        "other": "The reader asks about their work life.",
    },
    "health": {
        "surgery": "The reader faces, or is considering, a surgery or medical procedure.",
        "recovery": "The reader is unwell or recovering and wants to know how healing will go.",
        "disease": "The reader is worried about their health or an illness.",
        "mind": "The reader is worried about stress, anxiety or sleep.",
        "other": "The reader is worried about their health.",
    },
}
_SITUATION["health"]["other"] = _SITUATION["health"]["disease"]

_DO = {
    "career": {
        "promotion": ["Raise the conversation on a favourable day, with your results written down.",
                      "Make your work visible to the people who decide."],
        "jobchange": ["Apply, interview and negotiate on the favourable days.",
                      "Keep a short list of people who can speak for your work."],
        "layoff": ["Keep your results visible and your skills and contacts current.",
                   "Keep some savings aside so a surprise does not force a hasty decision."],
        "business": ["Start small and test before you commit money.", "Do the important meetings on favourable days."],
        "other": ["Put your best work in front of the people who decide, on the favourable days."],
    },
    "health": {
        "_": ["Keep your regular check-ups and follow your doctor's advice.",
              "Use the favourable days for rest, gentle routine and any visits whose date you can choose."],
    },
}
_AVOID = {
    "career": {
        "promotion": ["Do not push for a decision or argue with a senior on the days marked to hold back."],
        "jobchange": ["Do not accept, reject or resign in a rush on the days marked to hold back."],
        "layoff": ["Do not quit in anger or complain about the company on the days marked to hold back."],
        "business": ["Do not sign agreements or put in big money on the days marked to hold back."],
        "other": ["Do not resign, argue with a senior or sign anything big on the days marked to hold back."],
    },
    "health": {
        "surgery": ["Never change or delay a surgery plan because of a chart; the date is for you and your "
                    "surgeon to decide.", "Avoid hard exertion on the days marked to go easy."],
        "_": ["Do not skip treatment or medicine because of what a chart says.",
              "Avoid hard exertion or risk on the days marked to go easy."],
    },
}

_PATTERN = {
    "career": {
        (True, True): "Your chart rewards steady effort; recognition tends to arrive and to last.",
        (True, False): "Your work tends to progress well, though recognition from seniors can come later than "
                       "your effort deserves.",
        (False, True): "People in authority tend to notice you, but the path is uneven; consistent results smooth it.",
        (False, False): "Progress at work asks more patience and visible results from you than most; slow, steady "
                        "steps work best.",
    },
    "health": {
        (True, True): "Your constitution tends to recover well and keeps its balance.",
        (True, False): "Your body tends to be sturdy, but the mind absorbs stress; rest and routine protect you.",
        (False, True): "Your mind is steady, but the body needs regular care and sleep to keep its strength.",
        (False, False): "Your constitution needs regular care; steady routine, sleep and check-ups protect you "
                        "more than most.",
    },
}
_PATTERN_HEAD = {"career": "How work tends to go for you", "health": "How your body and mind tend to run"}

_UI = {
    "career": {
        "kicker": "Career reading · Chandra Naadi", "now": "What is happening",
        "why": "What the Moon and your chart show", "reach": "Best days to speak up, apply or interview",
        "hold": "Days to hold back from big moves", "do": "What helps", "avoid": "What to avoid",
        "pattern": _PATTERN_HEAD["career"], "longer": "The longer window",
        "teaser": "We read the Moon's path over your chart for the next {n} days: {o} days that favour speaking up "
                  "and acting, and {h} days to hold back from big moves. The dates, and what to do on each, are in "
                  "the full reading.",
        "lockchip": "See the days and what to do", "no_days": "No day in the next {n} days stands out; steady, "
        "visible work matters more than timing.",
        "ph_open": "the best days to raise it, apply or interview are marked here, with what to do on each.",
        "ph_hold": "the days to avoid resigning, arguing or signing are marked here too.", "note": "",
    },
    "health": {
        "kicker": "Health reading · Chandra Naadi", "now": "What is happening",
        "why": "What the Moon and your chart show", "reach": "Days that support rest, care and treatment",
        "hold": "Days to go easy", "do": "What helps", "avoid": "What to avoid",
        "pattern": _PATTERN_HEAD["health"], "longer": "The longer window",
        "teaser": "We read the Moon's path over your chart for the next {n} days: {o} days that support rest and "
                  "care, and {h} days to go easy. The dates, and what to do on each, are in the full reading.",
        "lockchip": "See the days and what to do", "no_days": "No day in the next {n} days stands out; steady "
        "routine and rest matter more than timing.",
        "ph_open": "the days that support rest, care and check-ups are marked here.",
        "ph_hold": "the days to go easy and avoid strain are marked here too.",
        "note": "Guidance for self-reflection only, not medical advice. Please follow your doctor's advice and "
                "keep your check-ups.",
    },
}
_PHRASE = {"career": ("that favour speaking up and acting", "to hold back from big moves"),
           "health": ("that support rest and care", "to go easy")}

# ------------------------------------------------------------------ chart facts
def _owners(qfacts: dict, houses: tuple[int, ...]) -> list[str]:
    pl = qfacts.get("placements") or {}
    return [p for p in _REAL if set((pl.get(p) or {}).get("owns") or []) & set(houses)]


def _plan(topic: str, qfacts: dict) -> dict[str, Any]:
    """Which planets decide this topic: ``weights`` (who helps when touched), ``anchors``, ``watch``."""
    lord_primary = ((qfacts.get("house") or {}).get("lord") or {}).get("planet")
    if topic == "career":
        owners10 = _owners(qfacts, (10,))
        lord = (owners10[0] if owners10 else lord_primary) or "Saturn"
        return {"weights": {lord: 3, "Jupiter": 3, "Sun": 2, "Saturn": 2}, "anchors": [lord, "Sun", "Saturn"],
                "watch": set(), "lord": lord, "lord_name": "10th house of work"}
    lagna_lord = qfacts.get("lagna_lord") or lord_primary or "Sun"
    watch = {p for p in _owners(qfacts, (6, 8)) if p not in (lagna_lord, "Jupiter", "Sun", "Moon")}
    return {"weights": {lagna_lord: 3, "Jupiter": 3, "Sun": 2, "Moon": 2}, "anchors": [lagna_lord, "Sun", "Moon"],
            "watch": watch, "lord": lagna_lord, "lord_name": "rising sign (your body and vitality)"}


def _scan(pc: dict, plan: dict, strained: dict[str, bool], today: date) -> dict[str, Any]:
    weights, watch = plan["weights"], plan["watch"]
    open_days: list[tuple[int, date]] = []
    hold_days: list[tuple[int, date]] = []
    for i in range(1, SCAN_DAYS + 1):
        day = today + timedelta(days=i)
        try:
            d = _moon_day(pc, day)
        except Exception as exc:                                      # noqa: BLE001
            print(f"[topic_naadi] day scan failed: {type(exc).__name__}: {exc}", flush=True)
            return {"open": [], "hold": [], "ok": False, "n_open": 0, "n_hold": 0}
        if d is None:
            continue
        touched = set(d["touched"])
        mine = touched & set(weights)
        steady = {p for p in mine if not strained.get(p)}
        if d["cautions"] or (mine - steady) or (touched & watch):
            # caution days weigh most, so when a chart is strained everywhere only the sharpest days are named
            hold_days.append((2 * len(d["cautions"]) + len(mine - steady) + len(touched & watch), day))
            continue
        score = sum(weights[p] for p in steady)
        if score >= 2:
            open_days.append((score, day))
    best = sorted(open_days, key=lambda t: (-t[0], t[1]))[:6]
    chosen = sorted(d for _s, d in best)
    worst = sorted(hold_days, key=lambda t: (-t[0], t[1]))[:8]
    hold_runs = _runs(sorted(d for _s, d in worst))[:4]
    return {"open": [_label(a, b) for a, b in _runs(chosen)], "hold": [_label(a, b) for a, b in hold_runs],
            "n_open": len(chosen), "n_hold": sum((b - a).days + 1 for a, b in hold_runs), "ok": True}


def _line(name: str, role: str, st: dict) -> str:
    dig = RN._dig_words(st["dignity"])
    return (f"{name} ({role}) sits in {st['sign']}, house {st['house']}"
            + (f", {dig}" if dig else "") + (" and is scorched by the Sun (combust)" if st["combust"] else "") + ".")


def build(topic: str, pc: dict, question: str, qfacts: dict, *, stance: str, today: Optional[date] = None,
          sade: Optional[dict] = None) -> Optional[dict]:
    today = today or date.today()
    if topic not in _KINDS:
        return None
    try:
        from chandra_naadi_analysis import is_strong, is_weak                 # noqa: F401
    except Exception as exc:                                                  # noqa: BLE001
        print(f"[topic_naadi] unavailable: {type(exc).__name__}: {exc}", flush=True)
        return None

    ask = intent(topic, question)
    plan = _plan(topic, qfacts)
    states = {p: _state(pc, p) for p in set(plan["weights"]) | set(plan["anchors"])}
    strained = {p: _strained(s) for p, s in states.items()}
    days = _scan(pc, plan, strained, today)
    anchors = [states[p] for p in plan["anchors"]]
    a0 = anchors[0]
    obstruct = list(dict.fromkeys(_sitting_on(pc, plan["anchors"][0]) + _sitting_on(pc, plan["anchors"][1])))
    obstruct = [p for p in obstruct if p not in plan["anchors"][:2]]

    naadi = (qfacts.get("lenses") or {}).get("naadi") or {}
    score = {"favourable": 1, "mixed": 0, "difficult": -1}.get(stance, 0) + int(naadi.get("vote", 0))
    strength = sum(1 if _strong(s) else -1 if (s["dignity"] in _BAD or s["combust"] or s["hard"]) else 0
                   for s in anchors)
    score += max(-2, min(2, strength))
    score -= 1 if obstruct else 0
    if sade and sade.get("status") == "in" and sade.get("phase") == 1:
        score -= 1
    if days["ok"]:
        score += 1 if days["n_open"] >= 3 else -1 if days["n_open"] == 0 else 0
    lean = "open" if score >= 2 else "closed" if score <= -2 else "mixed"

    facts: list[str] = []

    def _fact(text: str) -> None:
        facts.append(f"F{len(facts) + 1}: {text}")

    if topic == "career":
        lord, sun, sat = anchors
        _fact(_line(plan["lord"], f"rules your {plan['lord_name']}", lord))
        _fact(_line("The Sun", "authority and recognition", sun))
        _fact(_line("Saturn", "work, duty and job stability", sat))
        if obstruct:
            _fact(f"{' and '.join(obstruct)} sits with your work planets, which brings delay or friction with "
                  "people in authority.")
        pat = _PATTERN["career"][(_strong(lord), _strong(sun))]
    else:
        lord, sun, moon = anchors
        _fact(_line(plan["lord"], "rules your rising sign, the body", lord))
        _fact(_line("The Sun", "vitality", sun))
        _fact(_line("The Moon", "the mind and body fluids", moon))
        if obstruct:
            _fact(f"{' and '.join(obstruct)} sits with your vitality planets, which can bring strain and slower "
                  "recovery.")
        if plan["watch"]:
            _fact(f"{' and '.join(sorted(plan['watch']))} rules a house of illness or difficulty in your chart "
                  "(6th or 8th).")
        pat = _PATTERN["health"][(_strong(lord), not _strained(moon))]
    _fact(pat)
    if naadi:
        if naadi.get("touched"):
            _fact("Today the Moon is touching your natal " + ", ".join(naadi["touched"]) + ".")
        if naadi.get("good"):
            _fact(f"{', '.join(naadi['good'])} is well placed, which helps now.")
        if naadi.get("bad"):
            _fact(f"{', '.join(naadi['bad'])} is under strain, so decisions made today can be hasty.")
        if naadi.get("cautions"):
            _fact("Today is a sensitive day for the Moon in your chart, so it is a day for steady routine, "
                  "not big moves.")
    if days["ok"]:
        _fact(f"Over the next {SCAN_DAYS} days the Moon favours acting on {days['n_open']} days and asks for "
              f"restraint on {days['n_hold']}.")
    per = qfacts.get("periods") or {}
    if per.get("main") and per.get("sub"):
        _fact(f"You are in the {per['main']} main period with {per['sub']} running as the sub-period.")
    try:
        import sade_sati as SS
        line = SS.facts(sade)
        if line:
            _fact(line)
    except Exception:                                                         # noqa: BLE001
        pass

    return {"topic": topic, "kind": ask["kind"], "asks": ask["asks"], "lean": lean, "pattern": pat,
            "days": days, "facts": facts, "next_window": qfacts.get("next_window") or "",
            "question": " ".join(str(question or "").split())[:240], "a0": a0}


# ------------------------------------------------------------------ the writing
_DEATH = re.compile(r"\b(die|dies|died|dying|death|dead|fatal\w*|terminal\w*|life\s*span|lifespan|"
                    r"won'?t\s+survive|not\s+survive|survival|incurable|no\s+cure)\b", re.I)
_STOP_CARE = re.compile(r"\b(stop\s+(?:taking|your)|skip\s+(?:your\s+)?(?:medicine|medication|treatment|dose)|"
                        r"no\s+need\s+(?:for|of)\s+(?:a\s+)?(?:doctor|treatment)|avoid\s+(?:the\s+)?"
                        r"(?:doctor|surgery|surgeon|hospital)|cancel\s+(?:the\s+|your\s+)?(?:surgery|operation))\b",
                        re.I)
_DELAY = re.compile(r"\b(postpone\w*|delay\w*|put\s+off|re-?schedul\w*|defer\w*|hold\s+off|"
                    r"decisions?\s+(?:regarding|about|on|around)\s+(?:the\s+|your\s+)?"
                    r"(?:surgery|operation|treatment|procedure))\b", re.I)
_DISEASES = ("cancer", "tumour", "tumor", "diabetes", "diabetic", "stroke", "heart attack", "kidney", "liver",
             "hiv", "tuberculosis", "covid", "epilepsy", "paralysis", "dementia", "alzheimer", "thyroid", "asthma",
             "arthritis", "migraine", "hypertension", "infection", "depression", "anxiety")
_INVENTED = {
    "career": ("recession", "restructuring", "office politics", "jealous", "rival", "competitor", "toxic", "bad boss",
               "affair", "company losses", "market crash"),
    "health": ("diet", "lifestyle", "hormonal", "genetic", "vitamin", "deficiency", "digestion", "virus", "bacteria",
               "inflammation", "blood pressure", "cholesterol"),
}
_WILL_WIN = re.compile(r"\bwill\s+(?:definitely\s+|surely\s+|certainly\s+)?(?:be\s+promoted|get\s+(?:promoted|the\s+"
                       r"(?:job|raise|hike|promotion))|recover|be\s+cured|be\s+healed|heal|get\s+better|go\s+well|"
                       r"succeed|be\s+successful|be\s+smooth)\b|\brecovery\s+will\s+be\s+\w+", re.I)
_WILL_LOSE = re.compile(r"\bwill\s+(?:definitely\s+|surely\s+|certainly\s+)?(?:be\s+(?:fired|laid\s+off|sacked|"
                        r"terminated)|lose\s+(?:your|the)\s+job|not\s+recover|never\s+recover|need\s+surgery)\b", re.I)

_SYSTEM = """You are a warm, honest Chandra Naadi astrologer talking to someone worried about {area}.
Write for the reader directly, using "you" and "your". Be kind and calm, never dramatic. You do not promise outcomes.

Use ONLY the FACTS lines. Never name a planet, house, sign or period that is not in them. Never write a month,
a year or a date (dates are shown elsewhere). Never offer rituals, stones or tricks. Do not invent causes or events
(for example a recession, a rival, a diet, an infection); say only what the facts say.{extra}

Speak to the reader's own situation (use their question). Name the real drivers from the facts in plain words,
for example that a planet of work or vitality is under strain, or that the Moon is passing over a sensitive point
today. Avoid vague filler like "smoother waters" or "things may improve".

Fields:
- headline: leave as an empty string (it is written elsewhere).
- happening: 2-3 sentences, at most 60 words, saying what seems to be going on, from the facts.
- why: up to 3 short reasons, each from one fact, plain words.
- do: up to 3 short, concrete things that help (about timing, tone, routine).
- avoid: up to 2 short things to avoid.

LEAN is the chart's verdict: "open" = the signs lean in the reader's favour, "mixed" = both ways,
"closed" = the signs are under strain for now. Your wording must match the lean. When the lean is "mixed" or
"closed", never write that something "will" happen in the reader's favour; use "may" or "could" or "not yet".
Reply with JSON only."""
_EXTRA = {
    "career": " Never say the reader will be fired or will lose their job; speak of pressure and preparation.",
    "health": (" Never mention death, life span or survival, never name an illness the reader did not name, and "
               "never suggest skipping, delaying or replacing treatment. Always leave medical decisions to "
               "the reader's doctor."),
}
_AREA = {"career": "their work and career", "health": "their health"}


def _fallback(b: dict) -> dict[str, Any]:
    t, k = b["topic"], b["kind"]
    do = _DO[t].get(k) or _DO[t].get("_") or _DO[t]["other"]
    avoid = _AVOID[t].get(k) or _AVOID[t].get("_") or _AVOID[t]["other"]
    return {"headline": _HEADLINE[t][k][b["lean"]], "happening": _LEAN_SENT[t][b["lean"]],
            "why": [re.sub(r"^F\d+:\s*", "", f) for f in b["facts"][:3]], "do": list(do), "avoid": list(avoid)}


def _problems(w: dict, b: dict) -> list[str]:
    text = " ".join([w["headline"], w["happening"], *w["why"], *w["do"], *w["avoid"]])
    low, facts_low = text.lower(), " ".join(b["facts"]).lower()
    out: list[str] = []
    try:
        from llm.validate import enforce_user_voice
        out += [p for p in enforce_user_voice(text) if "you" in p or "third" in p or "empty" in p]
    except Exception:                                                     # noqa: BLE001
        pass
    if RN._BANNED.search(text):
        out.append("promises or sells an outcome, or suggests a trick or ritual")
    if RN._YEAR.search(text):
        out.append("names a date or year; dates are shown separately")
    for pl in RN._PLANETS:
        if re.search(rf"\b{pl}\b", text) and not re.search(rf"\b{pl}\b", " ".join(b["facts"])):
            out.append(f"names {pl}, which the facts do not mention")
            break
    for word in _INVENTED[b["topic"]]:
        if re.search(rf"\b{re.escape(word)}\b", low) and not re.search(rf"\b{re.escape(word)}\b", facts_low):
            out.append(f"mentions {word}, which the facts do not say; do not invent causes")
            break
    if _WILL_LOSE.search(text):
        out.append("predicts a loss or a failure to recover; use pressure and care instead")
    if b["lean"] != "open" and _WILL_WIN.search(text):
        out.append("says the good outcome will happen, but the lean is not open; use may or could")
    if b["topic"] == "health":
        if _DEATH.search(text):
            out.append("mentions death or survival; never do this")
        if _DELAY.search(text):
            out.append("tells the reader to delay or change a medical decision; that is for the doctor")
        if _STOP_CARE.search(text):
            out.append("advises against treatment or a doctor; never do this")
        asked = (b.get("question") or "").lower()
        for name in _DISEASES:
            if re.search(rf"\b{name}\b", low) and not re.search(rf"\b{name}\b", asked + " " + facts_low):
                out.append(f"names {name}, which the reader did not; never name an illness")
                break
    if len(w["happening"].split()) > 80:
        out.append("too long")
    return out


def write(b: dict) -> dict[str, Any]:
    fb = _fallback(b)
    b["by_model"] = False
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

    system = _SYSTEM.format(area=_AREA[b["topic"]], extra=_EXTRA[b["topic"]])
    user = "\n".join([
        f"READER'S QUESTION: {b['question']}",
        "SITUATION: " + _SITUATION[b["topic"]][b["kind"]],
        f"The reader wants {'a time' if b['asks'] == 'timing' else 'a yes or no'}.",
        f"LEAN: {b['lean']}", "FACTS:", *b["facts"]])
    problems: list[str] = []
    for _attempt in range(3):
        try:
            got = complete_model(
                _Write, system,
                user if not problems else user + "\n\nYour previous answer was rejected: "
                + "; ".join(problems[:3]) + ". Rewrite it using only the facts.",
                temperature=0.3)
        except Exception as exc:                                          # noqa: BLE001
            print(f"[topic_naadi] model failed: {type(exc).__name__}: {exc}", flush=True)
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
            return w
    print(f"[topic_naadi] model rejected: {problems[:3]}", flush=True)
    return fb


def compose(b: dict) -> dict[str, Any]:
    prose = write(b)
    t, k = b["topic"], b["kind"]
    if t == "health":                    # the doctor line is always present, whatever the model wrote
        if not any("doctor" in x.lower() or "surgeon" in x.lower() for x in prose["do"]):
            prose["do"] = ["Follow your doctor's advice and keep your check-ups."] + prose["do"][:2]
        if not any("treatment" in x.lower() or "medicine" in x.lower() or "surgery" in x.lower()
                   for x in prose["avoid"]):
            prose["avoid"] = ["Do not skip treatment or medicine because of what a chart says."] + prose["avoid"][:1]
    days = b["days"]
    return {"topic": t, "kind": k, "lean": b["lean"], "label": _LABEL[t][k][b["lean"]],
            "headline": prose["headline"], "happening": prose["happening"], "why": prose["why"],
            "do": prose["do"], "avoid": prose["avoid"], "pattern": b["pattern"],
            "open": days["open"], "hold": days["hold"], "n_open": days["n_open"], "n_hold": days["n_hold"],
            "days_ok": days["ok"], "scan_days": SCAN_DAYS,
            "next_window": b["next_window"] if t == "career" and k in ("jobchange", "promotion", "business") else "",
            "by_model": bool(b.get("by_model")), "lang": "en", "ui": _UI[t],
            "phrase_open": _PHRASE[t][0], "phrase_hold": _PHRASE[t][1]}


def render_html(blk: dict, *, paid: bool, price: int = 298) -> str:
    return RN.render_html(blk, paid=paid, price=price)


public = RN.public
