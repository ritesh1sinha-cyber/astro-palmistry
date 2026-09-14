"""Judge a KP horary question. Python computes the chart; the model decides.

The static YES/NO script is not the customer verdict. The model reads the
cuspal sub-lord, significators and ruling planets, then labels the question.
A thin Python veto still blocks an unsupported 'yes'.

``write_plain_answer`` then turns the judgement plus the dasha window into
three plain sentences: what the chart says, when it next opens, what to do.
Nothing else reaches the reader.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any, Optional

VIMSH_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
               "Jupiter", "Saturn", "Mercury"]
VIMSH_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
               "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
_TOTAL_YEARS = 120
_NAK_SPAN = 360.0 / 27

_JUDGE_SYSTEM = """You are judging a Krishnamurti (KP) horary question.

Do not write the customer answer. Decide only:

1. restated_intent — what they actually asked, in one plain sentence.
2. in_scope — true only for a human-life question (work, money, family,
   health, relationship, property, travel, legal, lost object, timing).
   False for programming, recipes, trivia or device repair.
3. is_yes_no — true only if a yes or no would be a fair answer.
   False for when / how / what / who / why / which, or any question that
   needs a description rather than a yes.
4. asks — what the reader wants back:
   - quantity if they asked how much, how many, or what percentage
   - timing if they asked when, by when, or how soon
   - yes_no if a yes or no settles it
   - other for anything else
5. label:
   - out_of_scope if in_scope is false
   - open if is_yes_no is false — NEVER use yes for those
   - yes only if it is a yes/no question AND favorable house significators
     clearly dominate AND denying houses do not AND ruling planets support
   - no if denying significators dominate
   - conditional if the testimony is mixed or thin
   When in doubt, choose open or conditional. Never default to yes.
   For a quantity question, label whether the thing itself is promised.
6. confidence — low unless the significators and ruling planets agree.
7. reason — one or two sentences citing only the evidence.

Reply with JSON only."""


def kp_evidence(data: dict[str, Any]) -> dict[str, Any]:
    """Flatten precompute / compute_kp_horary output for the judge and facts."""
    meta = data.get("meta") or {}
    kp = data.get("kp") or data.get("kp_data") or {}
    promise = kp.get("promise") or data.get("promise") or {}
    rp = data.get("ruling_planets") or {}
    if isinstance(rp, dict):
        ruling = list(rp.get("all_ruling_planets") or [])
    else:
        ruling = list(rp or [])
    cusp = {}
    chart_a = data.get("chart_a") or data.get("kp_chart_a") or {}
    primary = int(promise.get("primary_bhava") or 0)
    if primary and isinstance(chart_a.get("cusp_info"), dict):
        cusp = chart_a["cusp_info"].get(str(primary)) or {}
    return {
        "topic": meta.get("detected_topic") or data.get("topic") or "",
        "kp_number": int(kp.get("kp_number") or meta.get("kp_number") or 0),
        "kp_sign": kp.get("sign") or "",
        "primary_bhava": primary,
        "cusp_sub_lord": promise.get("cusp_sub_lord") or cusp.get("sub_lord") or "",
        "cusp_star_lord": promise.get("cusp_star_lord") or cusp.get("star_lord") or "",
        "star_lord": promise.get("star_lord") or "",
        "sub_lord_house": int(promise.get("sub_lord_house") or 0),
        "significations": [str(x) for x in (promise.get("significations") or [])],
        "fav_hits": [str(x) for x in (promise.get("fav_hits") or [])],
        "den_hits": [str(x) for x in (promise.get("den_hits") or [])],
        "list_a": [str(x) for x in (kp.get("list_a") or data.get("list_a") or [])],
        "list_c": [str(x) for x in (kp.get("list_c") or data.get("list_c") or [])],
        "ruling_planets": [str(x) for x in ruling[:12]],
    }


def _majors(moon_sid_lon: float, start: date,
            *, horizon_years: int = 40) -> list[dict[str, Any]]:
    """The horary chart's dasa / bukti / antara table, nested.

    KP times a horary from the querent's Moon at the moment asked, not from a
    birth chart — a horary has no birth data to work from. The antara level is
    what lets the answer name a month rather than a decade.
    """
    idx = min(int(moon_sid_lon / _NAK_SPAN), 26)
    star_lord = VIMSH_ORDER[idx % 9]
    used = (moon_sid_lon - idx * _NAK_SPAN) / _NAK_SPAN
    md_idx = VIMSH_ORDER.index(star_lord)

    # Offsets stay in float days and only become dates at the end. Adding a
    # timedelta to a date truncates the fraction, and nine of those per level
    # drift the chain by days.
    origin = start - timedelta(days=VIMSH_YEARS[star_lord] * used * 365.25)
    limit = (start - origin).days + horizon_years * 365.25

    def at(days: float) -> date:
        return origin + timedelta(days=days)

    out: list[dict[str, Any]] = []
    md_from = 0.0
    for i in range(9):
        if md_from > limit:
            break
        md = VIMSH_ORDER[(md_idx + i) % 9]
        md_days = VIMSH_YEARS[md] * 365.25
        subs = []
        ad_from = md_from
        for k in range(9):
            ad = VIMSH_ORDER[(VIMSH_ORDER.index(md) + k) % 9]
            ad_days = md_days * VIMSH_YEARS[ad] / _TOTAL_YEARS
            pds = []
            pd_from = ad_from
            for m in range(9):
                pd = VIMSH_ORDER[(VIMSH_ORDER.index(ad) + m) % 9]
                pd_to = pd_from + ad_days * VIMSH_YEARS[pd] / _TOTAL_YEARS
                pds.append({"lord": pd, "start": at(pd_from), "end": at(pd_to)})
                pd_from = pd_to
            subs.append({"lord": ad, "start": at(ad_from),
                         "end": at(ad_from + ad_days), "subs": pds})
            ad_from += ad_days
        out.append({"lord": md, "start": at(md_from),
                    "end": at(md_from + md_days), "subs": subs})
        md_from += md_days
    return out


def _dasha_periods(moon_sid_lon: float, start: date,
                   *, horizon_years: int = 25) -> list[dict[str, Any]]:
    """Flat, time-ordered antara list — the nested table walked end to end."""
    cutoff = start + timedelta(days=horizon_years * 365.25)
    out = []
    for md in _majors(moon_sid_lon, start, horizon_years=horizon_years):
        for ad in md["subs"]:
            for pd in ad["subs"]:
                if pd["end"] > start and pd["start"] <= cutoff:
                    out.append({"md": md["lord"], "ad": ad["lord"],
                                "pd": pd["lord"], "start": pd["start"],
                                "end": pd["end"]})
    return out


def _month_year(d: date) -> str:
    return d.strftime("%b-%Y")


def kp_timing(data: dict[str, Any], evidence: dict[str, Any], *,
              exclude_running: bool = False,
              horizon_years: int = 5) -> dict[str, Any]:
    """Date the event the way the KP horary text does (procedure 3.4).

    Take the dasa / bukti / antara table of the horary chart and walk it with
    List C — the planets common to the bhava significators and the ruling
    planets. Pick the first dasa in List C, then within it the first bukti in
    List C other than the dasa lord, then within that the first antara in
    List C other than either. The event lands inside that antara.

    ``exclude_running`` departs from the text deliberately. The book only dates
    an event once the cuspal sub-lord has promised it; when the promise is
    denied or unclear there is no date to give. We still owe the reader a
    "next possible" window, and the period already running cannot be it — the
    chart just said the event is not happening in it.

    ``horizon_years`` guards a case the book never meets. It assumes the
    running dasa lord is in List C. When it is not, the walk jumps to the next
    dasa that is, and a Rahu or Saturn dasa in between puts that two decades
    out. A date that far away is not an answer, so we report that there is no
    clear window instead of naming one.

    Returns ``{"window": "Jul-2027", "until": ..., "md"/"ad"/"pd": ...}``,
    ``{"beyond_horizon": True, ...}`` when the only match is too far out, or an
    empty dict when the Moon or List C is missing.
    """
    moon = ((data.get("planets") or {}).get("Moon") or {})
    lon = moon.get("sidereal_lon")
    if lon is None:
        return {}
    meta = data.get("meta") or {}
    try:
        asked = date.fromisoformat(str(meta.get("q_date"))[:10])
    except Exception:
        asked = date.today()

    # List C proper. Fall back only when the chart gave us nothing to work with.
    signif = {str(p) for p in (evidence.get("list_c") or [])}
    if not signif:
        weak = {str(p) for p in (evidence.get("list_a") or [])}
        ruling = {str(p) for p in (evidence.get("ruling_planets") or [])}
        signif = (weak & ruling) or weak
    if not signif:
        return {}

    today = date.today()
    majors = _majors(float(lon), asked)
    horizon = today + timedelta(days=horizon_years * 365.25)

    def usable(period: dict[str, Any]) -> bool:
        return period["start"] > today if exclude_running else True

    def hit(period: dict[str, Any], md: str, ad: str, pd: str,
            level: str) -> dict[str, Any]:
        opens = max(period["start"], today)
        return {"window": _month_year(opens),
                "until": _month_year(period["end"]),
                "md": md, "ad": ad, "pd": pd, "level": level,
                "starts": period["start"], "ends": period["end"],
                "days_away": (opens - today).days,
                "near": (opens - today).days <= 400}

    # A short List C cannot fill three distinct levels, so widen the window
    # rather than refuse a date: antara, else bukti, else the dasa itself.
    bukti_hit: dict[str, Any] = {}
    dasa_hit: dict[str, Any] = {}
    for md in majors:
        if md["end"] <= today or md["lord"] not in signif:
            continue
        if not dasa_hit and usable(md):
            dasa_hit = hit(md, md["lord"], "", "", "dasa")
        for ad in md["subs"]:
            if ad["end"] <= today or ad["lord"] not in signif:
                continue
            if ad["lord"] == md["lord"]:            # bukti must differ
                continue
            if not bukti_hit and usable(ad):
                bukti_hit = hit(ad, md["lord"], ad["lord"], "", "bukti")
            for pd in ad["subs"]:
                if pd["end"] <= today or pd["lord"] not in signif:
                    continue
                if pd["lord"] in (md["lord"], ad["lord"]):
                    continue
                if not usable(pd):
                    continue
                return _within(hit(pd, md["lord"], ad["lord"], pd["lord"],
                                   "antara"), horizon, horizon_years)
    return _within(bukti_hit or dasa_hit, horizon, horizon_years)


def _within(found: dict[str, Any], horizon: date,
            horizon_years: int) -> dict[str, Any]:
    if not found:
        return {}
    if found["starts"] > horizon:
        return {"beyond_horizon": True, "horizon_years": horizon_years}
    return found


def blocking_planet(evidence: dict[str, Any]) -> str:
    """Planet to remedy: the one holding the matter, not a random malefic."""
    den = evidence.get("den_hits") or []
    if den:
        for p in (evidence.get("list_a") or []):
            if p not in (evidence.get("list_c") or []):
                return str(p)
    sub = str(evidence.get("cusp_sub_lord") or "")
    return sub or str((evidence.get("list_a") or [""])[0])


def _looks_yes_no(question: str) -> bool:
    q = (question or "").strip().lower()
    if not q:
        return False
    if q.startswith(("when ", "what ", "how ", "who ", "why ", "which ",
                     "where ", "tell me", "describe", "explain")):
        return False
    return q.startswith((
        "will ", "can ", "could ", "should ", "shall ", "is ", "are ",
        "do ", "does ", "did ", "am i", "have ", "has ", "would ",
    )) or "?" in q and any(w in q.split()[:4] for w in (
        "will", "can", "should", "is", "are", "do", "does",
    ))


# "how much longer" is a timing question wearing a quantity word.
_HOW_MUCH_TIME = re.compile(r"how (?:much|many)\s+(?:more\s+)?"
                            r"(?:time|longer|long|days?|weeks?|months?|years?)")
_QUANTITY = re.compile(
    r"how (?:much|many|big|large|heavy|far)\b"
    r"|\bwhat(?:'s| is)?\s+(?:the\s+)?(?:percentage|percent|amount|figure|"
    r"sum|size|salary|package|price|rate)\b"
    r"|\bpercentage\b|\bpercent\b|%"
    r"|\bhow many (?:lakhs?|crores?|rupees|thousands?)\b")
_TIMING = re.compile(
    r"^\s*when\b|\bwhen will\b|\bby when\b|\bhow soon\b|\bhow long\b"
    r"|\bwhich (?:month|year|week|date)\b|\btime ?frame\b|\btimeline\b"
    r"|\bat what time\b")


def classify_ask(question: str) -> str:
    """What the reader wants back: a yes, a date, a quantity, or a account.

    A chart settles occurrence and timing. It does not return a quantity, so
    that has to be recognised up front and said rather than answered around.
    """
    q = (question or "").strip().lower()
    if not q:
        return "other"
    if _HOW_MUCH_TIME.search(q):
        return "timing"
    if _QUANTITY.search(q):
        return "quantity"
    if _TIMING.search(q):
        return "timing"
    if _looks_yes_no(q):
        return "yes_no"
    return "other"


def _sanitise(plan: Any, evidence: dict[str, Any], question: str) -> Any:
    # The wording decides what kind of answer is owed; trust the model only
    # where the wording itself is not decisive.
    kind = classify_ask(question)
    if kind != "other" or plan.asks not in ("yes_no", "timing", "quantity"):
        plan.asks = kind
    if not plan.in_scope:
        plan.label = "out_of_scope"
        plan.is_yes_no = False
        return plan
    if plan.asks == "quantity":
        plan.is_yes_no = False
    if not plan.is_yes_no or not _looks_yes_no(question):
        plan.is_yes_no = False
        if plan.label == "yes":
            plan.label = "open"
    fav = evidence.get("fav_hits") or []
    den = evidence.get("den_hits") or []
    support = evidence.get("list_c") or evidence.get("ruling_planets") or []
    if plan.label == "yes":
        if den and not fav:
            plan.label = "no"
        elif not fav or (den and not support):
            plan.label = "conditional"
            plan.confidence = "low"
    if not plan.restated_intent:
        plan.restated_intent = (question or "")[:300]
    return plan


def judge_kp_horary(question: str, data: dict[str, Any], *,
                    area: str = "") -> Any:
    """Return a HoraryJudgement. Falls back to open/low if the model is down."""
    from .schemas import HoraryJudgement

    evidence = kp_evidence(data)
    fallback = HoraryJudgement(
        restated_intent=(question or "")[:300],
        in_scope=True,
        is_yes_no=_looks_yes_no(question),
        label="open" if not _looks_yes_no(question) else "conditional",
        confidence="low",
        reason="The chart testimony is mixed or the judge was unavailable.",
    )
    q = (question or "").strip()
    if not q:
        fallback.in_scope = True
        fallback.is_yes_no = False
        fallback.label = "open"
        return fallback

    try:
        from core.llm_client import complete_model
    except Exception:
        return fallback

    user = ""
    if area:
        user += f"AREA THE READER PICKED: {area}\n"
    user += f'QUESTION: "{q}"\n\nKP EVIDENCE\n'
    for k, v in evidence.items():
        user += f"- {k}: {v}\n"

    plan = complete_model(HoraryJudgement, _JUDGE_SYSTEM, user, temperature=0.1)
    if plan is None:
        return fallback
    return _sanitise(plan, evidence, q)


_WRITE_SYSTEM = """You answer a horary question in plain language. The chart is
already judged — you only put it into words the reader understands.

Write three short fields:

answer  — one sentence, maybe two. Say what the chart says about the thing
          they asked. Speak to them as "you". Plain words only. Put NO date,
          month or year in here — the date belongs in timing and nowhere else.
          Say nothing about how near or far it is either: no "soon", no "not
          soon", no "near future", no "a long way off". The timing line owns
          that, and it will contradict you.
timing  — one sentence naming the month and year you are given, or "" if you
          are given no window. Never invent or round a date.
remedy  — one sentence. One concrete thing to do, tied to the planet named.
          "" if no planet is given.

Hard rules:
- No astrology words. No houses, cusps, sub-lords, significators, dasha,
  ruling planets, degrees, signs, KP, lagna.
- Never name a planet. No Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn,
  Rahu or Ketu — the remedy is an action, not an influence to describe.
- No greeting, no sign-off, no "the chart shows", no offer to explain more,
  no questions back to the reader, no headings, no bullets, no bold.
- Use only the month and planet you are given. Invent nothing.
- Say the honest verdict. If it is not a yes, do not sound like one.

Reply with JSON only."""

_MONTHS = ("january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december",
           "jan-", "feb-", "mar-", "apr-", "jun-", "jul-", "aug-",
           "sep-", "oct-", "nov-", "dec-")


def _has_date(text: str) -> bool:
    low = (text or "").lower()
    return bool(re.search(r"\b(19|20)\d{2}\b", low)) or any(
        m in low for m in _MONTHS)


_NOT_SOON = re.compile(
    r"\bnot\s+(?:happening\s+)?soon\b|\bno\s+clear\s+sign\b"
    r"|\bnear future\b|\bnot\s+\w+\s+(?:any\s+time|anytime)\s+soon\b"
    r"|\bfar off\b|\ba long way\b|\bnot for a (?:while|long time)\b")


def _contradicts_timing(answer: str, timing: dict[str, Any]) -> bool:
    """True when the verdict pushes the event away but the window is close."""
    if timing.get("beyond_horizon") or not timing.get("window"):
        return False
    if int(timing.get("days_away", 999)) > _SOON_DAYS:
        return False
    return bool(_NOT_SOON.search((answer or "").lower()))


_LABEL_GLOSS = {
    "yes": "The answer is yes — this is supported.",
    "no": "The answer is no — this is not supported.",
    "conditional": "There is no clear sign of this happening soon.",
    "open": "The chart does not settle this yet.",
}

# A chart settles whether and when. It has no rule that returns an amount, so
# a "how much" question gets told that plainly before it gets anything else.
_QUANTITY_LEAD = "This kind of chart cannot put a number on it."
_QUANTITY_GLOSS = {
    "yes": "What it can tell you is that the increase is on the way.",
    "no": "What it can tell you is that one is not on the way.",
    "conditional": "What it can tell you is that nothing is settled either way yet.",
    "open": "What it can tell you is that nothing is settled either way yet.",
}


def quantity_answer(label: str) -> str:
    return f"{_QUANTITY_LEAD} {_QUANTITY_GLOSS.get(label, _QUANTITY_GLOSS['open'])}"


# The remedy table in horary_answer keeps the planet in the prose ("the Moon
# is moving the situation"). The reader wants the action, not the actor.
_PLAIN_REMEDY = {
    "Saturn": "Do the slow, verifiable thing first — get it in writing and "
              "meet the deadline you keep pushing back.",
    "Mars": "Take the heat out of it. Stop arguing about this for a week and "
            "let the other side move first.",
    "Sun": "Go straight to the person who can actually decide. This stalls "
           "whenever it is handled one level below them.",
    "Moon": "Do not decide this week. How you read this will change within "
            "days, so let it settle before you choose.",
    "Mercury": "Put it in writing, and re-read what you already sent. The "
               "misunderstanding here is in the wording.",
    "Venus": "Repair the relationship before you push the request again. "
             "People say yes to a person, not to a proposal.",
    "Jupiter": "Ask someone senior to speak for you. This opens through a "
               "sponsor rather than through your own effort.",
    "Rahu": "Check whatever looks too convenient, and verify it yourself "
            "rather than taking it on trust.",
    "Ketu": "Stop pushing for a fortnight. This one comes back to you when "
            "you stop chasing it.",
}
_PLANET_NAMED = re.compile(
    r"\b(sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu)\b", re.I)


def plain_remedy(planet: str) -> str:
    return _PLAIN_REMEDY.get(str(planet or ""), "")


_NUMBER_WORD = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
                6: "six", 8: "eight", 10: "ten", 12: "twelve"}

# Inside this many days, a bare "Sep-2026" reads as "today" and the reader
# cannot tell whether it has already passed. Give them the days.
_SOON_DAYS = 75


def _format_window(timing: dict[str, Any]) -> str:
    starts, ends = timing.get("starts"), timing.get("ends")
    if starts and ends and int(timing.get("days_away", 999)) <= _SOON_DAYS:
        opens = max(starts, date.today())
        day = f"{opens.day} {opens:%b}"
        if opens.year != ends.year:
            day += f" {opens.year}"
        return f"{day} to {ends.day} {ends:%b} {ends.year}"
    window, until = timing.get("window") or "", timing.get("until") or ""
    if timing.get("level") == "antara" or not until or until == window:
        return window
    return f"{window} to {until}"


def timing_sentence(timing: dict[str, Any]) -> str:
    """Name the window the reader can act on, at a precision they can trust."""
    if timing.get("beyond_horizon"):
        # Naming the horizon here reads as a forecast of its own — "no opening
        # in five years" is a frightening thing to tell someone with a fever.
        return "The chart does not mark out a clear window for this."
    if not timing.get("window"):
        return ""
    span = _format_window(timing)
    if int(timing.get("days_away", 999)) <= _SOON_DAYS:
        return f"The nearest window is {span}."
    return f"The next likely opening is around {span}."


def label_gloss(label: str, timing: dict[str, Any]) -> str:
    """The verdict line must not date the event — the timing line does that.

    Saying "no clear sign of this happening soon" above a window that opens
    next week is a contradiction the reader will catch immediately.
    """
    if label in ("yes", "no"):
        return _LABEL_GLOSS[label]
    soon = (not timing.get("beyond_horizon")
            and int(timing.get("days_away", 999)) <= _SOON_DAYS)
    if soon:
        return ("There is no firm yes here, but the chart does not "
                "push it far out either.")
    return _LABEL_GLOSS.get(label, _LABEL_GLOSS["open"])


def _fallback_plain(question: str, label: str, timing: dict[str, Any],
                    remedy: str, asks: str = "other") -> Any:
    from .schemas import HoraryPlainAnswer
    return HoraryPlainAnswer(
        answer=(quantity_answer(label) if asks == "quantity"
                else label_gloss(label, timing)),
        timing=timing_sentence(timing),
        remedy=remedy,
    )


def write_plain_answer(question: str, plan: Any, evidence: dict[str, Any],
                       timing: dict[str, Any], *, lang: str = "en") -> Any:
    """Turn the judgement into the reader-facing verdict, date and remedy."""
    from .schemas import HoraryPlainAnswer

    label = str(getattr(plan, "label", "open") or "open")
    if label == "out_of_scope":
        return HoraryPlainAnswer(
            answer="This is not something a horary chart can answer.",
            timing="", remedy="")

    planet = blocking_planet(evidence)
    remedy_line = plain_remedy(planet)
    asks = str(getattr(plan, "asks", "other") or "other")

    try:
        from core.llm_client import complete_model
    except Exception:
        return _fallback_plain(question, label, timing, remedy_line, asks)

    user = (
        f'QUESTION: "{(question or "").strip()}"\n'
        f"WHAT THEY WANT BACK: {asks}\n"
        f"VERDICT THE CHART GAVE: {label}\n"
        f"HOW SURE: {getattr(plan, 'confidence', 'low')}\n"
        f"WINDOW YOU MAY NAME: {timing_sentence(timing) or 'none'}\n"
        f"PLANET TO REMEDY: {planet or 'none'}\n"
        f"REMEDY IDEA (rewrite in plain words): {remedy_line or 'none'}\n"
    )
    if asks == "quantity":
        user += (f"THE ANSWER FIELD IS FIXED, COPY IT EXACTLY: "
                 f"{quantity_answer(label)}\n")
    if lang and lang.lower() not in ("en", "english"):
        user += f"WRITE IN: {lang}\n"

    out = complete_model(HoraryPlainAnswer, _WRITE_SYSTEM, user,
                         temperature=0.3)
    if out is None:
        return _fallback_plain(question, label, timing, remedy_line, asks)

    # The date is computed, not written. Letting the model restate it only
    # ever lost precision or dropped half a span.
    out.timing = timing_sentence(timing)
    if asks == "quantity":
        # No sourced rule turns a chart into an amount, so the refusal is not
        # the model's to paraphrase — a hedged version reads like a number.
        out.answer = quantity_answer(label)
    elif _has_date(out.answer) or _contradicts_timing(out.answer, timing):
        # A date in the answer leaks paid content; "not soon" above a window
        # that opens next week just reads as broken.
        out.answer = label_gloss(label, timing)
    if not out.remedy or _PLANET_NAMED.search(out.remedy):
        # A named planet turns an action into an influence to explain.
        out.remedy = remedy_line
    return out


def judgement_as_verdict(plan: Any) -> dict[str, Any]:
    """Shape reconcile() / facts expect for the KP lane."""
    label = str(getattr(plan, "label", "open") or "open")
    conf = str(getattr(plan, "confidence", "low") or "low")
    mapping = {
        "yes": ("yes", True),
        "no": ("no", False),
        "conditional": ("uncertain / qualified", None),
        "open": ("uncertain / qualified", None),
        "out_of_scope": ("out_of_domain", None),
    }
    verdict, favourable = mapping.get(label, ("uncertain / qualified", None))
    return {
        "verdict": verdict,
        "confidence": conf if conf in ("good", "moderate", "low") else "low",
        "score": {"yes": 0.7, "no": -0.7}.get(label, 0.0),
        "favourable": favourable,
        "is_yes_no": bool(getattr(plan, "is_yes_no", True)),
        "restated_intent": getattr(plan, "restated_intent", "") or "",
        "reason": getattr(plan, "reason", "") or "",
        "out_of_domain": label == "out_of_scope",
    }
