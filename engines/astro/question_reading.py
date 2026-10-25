"""A short, plain-language answer to ONE question the reader asked.

The older question report stacked every technique the engine owned (house
analysis, divisional charts, Lal Kitab, Chandra Naadi, transit lists, a dozen
remedies) under a verdict, so a simple "which gemstone suits me?" came back as
pages of unrelated lines. This module does the opposite:

1. ``build_fact_sheet`` keeps only what bears on the question: the house and
   lord that govern it, the natural indicator, the sign score, the running and
   next period, the transit of the two slow planets, and for gemstones the
   audited stone list. Lal Kitab and Chandra Naadi are left out on purpose.
2. A language model judges the question against that sheet and returns one
   small structured answer (verdict, short answer, a few reasons, timing,
   steps). Nothing it names is trusted until it passes ``_check``.
3. If the model is off, slow or fails the check, ``_fallback`` writes the same
   structure from the same facts, so the page never depends on the model.
4. ``render_html`` lays it out as one compact card.
"""
from __future__ import annotations

import html
import re
from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Stance = Literal["favourable", "mixed", "difficult", "not_astrological"]


class QuestionReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stance: Stance = Field(description="Overall outlook for what was asked.")
    answer: str = Field(description="Direct answer, 2-3 plain sentences, at most 60 words.")
    why: list[str] = Field(description="2-4 short reasons, each citing one chart fact that bears on the question.")
    timing: str = Field(description="One sentence on when, or empty if the question has no timing aspect.")
    steps: list[str] = Field(description="1-3 concrete things to do, at most 20 words each.")


_GOOD_DIGNITY = ("exalted", "moolatrikona", "own_sign", "friendly_sign")
_BAD_DIGNITY = ("debilitated", "enemy_sign")
_WEEKDAY = {"Sun": "Sunday", "Moon": "Monday", "Mars": "Tuesday", "Mercury": "Wednesday",
            "Jupiter": "Thursday", "Venus": "Friday", "Saturn": "Saturday",
            "Rahu": "Saturday", "Ketu": "Tuesday"}
# Questions where picking the moment for an action is meaningful advice.
_MOVE_DOMAINS = {"career_profession", "marriage_relationship", "children_progeny", "wealth_finances",
                 "property_assets", "foreign_relocation", "education_learning", "litigation_disputes"}
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


# --------------------------------------------------------------------------- facts
def _ord(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _and_join(items: list[str]) -> str:
    items = [str(i) for i in items if str(i)]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _month_year(iso: str) -> str:
    m = re.match(r"(\d{4})-(\d{2})", str(iso or ""))
    if not m:
        return str(iso or "")
    return f"{_MONTHS[int(m.group(2)) - 1]} {m.group(1)}"


def _pretty_window(text: str) -> str:
    """'Mercury Antardasha (2027-02-09 to 2029-06-14)' -> 'Mercury sub-period, Feb 2027 to Jun 2029'."""
    out = re.sub(r"\d{4}-\d{2}-\d{2}", lambda m: _month_year(m.group(0)), str(text or ""))
    out = out.replace("Antardasha", "sub-period").replace("Sub-Period", "sub-period")
    out = out.replace("Mahadasha", "main period")
    out = re.sub(r"\s*\((.*?)\)", r", \1", out, count=1)
    return re.sub(r"\s+", " ", out).strip(" ,")


def _planet_state(pc: dict, name: str) -> dict:
    from astro_precompute import get_dignity
    p = (pc.get("planets") or {}).get(name) or {}
    sign = p.get("sign", "")
    dig = p.get("dignity") or (get_dignity(name, sign) if sign else "unknown")
    house = int(p.get("house") or 0)
    return {"planet": name, "sign": sign, "house": house, "dignity": str(dig),
            "retro": bool(p.get("retrograde")), "combust": bool(p.get("combust")),
            "hard_house": house in (6, 8, 12)}


def _dignity_words(dig: str) -> str:
    d = str(dig or "")
    if d == "exalted":
        return "exalted (at its strongest)"
    if d in ("own_sign", "moolatrikona"):
        return "in its own sign (strong)"
    if d == "friendly_sign":
        return "in a friendly sign"
    if d == "debilitated":
        return "debilitated (weak)"
    if d == "enemy_sign":
        return "in an unfriendly sign"
    return ""


def _periods(pc: dict) -> dict:
    vim = pc.get("vimshottari") or {}
    md = vim.get("current_md") or {}
    ad = next((a for a in (vim.get("current_md_antardashas") or []) if a.get("status") == "current"), {})
    return {
        "main": md.get("md_lord", ""),
        "main_until": _month_year(md.get("end", "")),
        "sub": ad.get("ad_lord", ""),
        "sub_from": _month_year(ad.get("start", "")),
        "sub_until": _month_year(ad.get("end", "")),
    }


def _slow_transits(conf: Any) -> str:
    """Jupiter and Saturn only, in a sentence; the full transit list is noise here."""
    parts = re.findall(r"Transit (Jupiter|Saturn) in House (\d+) \((\w+)", conf.transit_finding or "")
    return "; ".join(f"{p} is crossing your {_ord(int(h))} house ({s})" for p, h, s in parts)


def build_fact_sheet(conf: Any, pc: dict, cfg: dict) -> dict:
    """Only the facts that can bear on the question. No Lal Kitab, no Chandra Naadi."""
    from confluence_question_engine import audit_chart_gemstones
    facts: dict[str, Any] = {
        "question": conf.question,
        "domain_key": conf.domain_key,
        "domain": cfg.get("title", conf.domain_title),
        "lagna": conf.lagna,
        "lagna_lord": conf.lagna_lord,
        "moon_sign": conf.moon_sign,
    }
    house = int(conf.primary_house)
    lord = _planet_state(pc, conf.primary_house_lord)
    karakas = [_planet_state(pc, k) for k in (cfg.get("karakas") or [])[:2]]
    sav = re.search(r"holds (\d+)", conf.ashtakavarga_finding or "")
    sav_n = int(sav.group(1)) if sav else 0
    facts["house"] = {"number": house, "sign": conf.primary_house_sign, "sav": sav_n, "lord": lord}
    facts["karakas"] = karakas
    facts["periods"] = _periods(pc)
    facts["next_window"] = _pretty_window(conf.breakthrough_period)
    facts["transits"] = _slow_transits(conf)

    signals_for, signals_against = [], []
    if conf.domain_key not in ("gemstones_remedies", "general_destiny", "out_of_domain"):
        (signals_against if lord["hard_house"] else signals_for).append("ruling planet placement")
        if lord["dignity"] in _GOOD_DIGNITY:
            signals_for.append("ruling planet dignity")
        elif lord["dignity"] in _BAD_DIGNITY:
            signals_against.append("ruling planet dignity")
        if karakas:
            k = karakas[0]
            bad = k["hard_house"] or k["dignity"] in _BAD_DIGNITY or k["combust"]
            (signals_against if bad else signals_for).append("natural indicator")
        if sav_n:
            (signals_for if sav_n >= 28 else signals_against).append("sign score")
        sub = facts["periods"]["sub"]
        helpers = set((cfg.get("karakas") or [])[:2]) | {conf.lagna_lord, conf.primary_house_lord}
        if sub in helpers:
            signals_for.append("running sub-period")
    facts["signals_for"], facts["signals_against"] = signals_for, signals_against

    if conf.domain_key == "gemstones_remedies":
        audit = (audit_chart_gemstones(pc) or {}).get("audit", {})
        rec, avoid = [], []
        for planet, inf in audit.items():
            row = {"planet": planet, "gem": inf["gem"], "metal": inf["metal"],
                   "finger": inf["finger"], "day": inf["day"], "mantra": inf["mantra"],
                   "houses": inf.get("owned_houses", []), "in_house": inf.get("house")}
            if inf["status"] == "RECOMMENDED":
                rec.append(row)
            elif inf["status"] in ("AVOID", "STRICTLY_AVOID"):
                row["reason"] = _short_avoid_reason(inf)
                avoid.append(row)
        facts["gems"] = {"recommended": rec, "avoid": avoid}
    return facts


def _short_avoid_reason(inf: dict) -> str:
    text = " ".join(inf.get("reasons") or [])
    if "8th house" in text and "placed in the 8th" in text:
        return "it sits in your 8th house, which stirs up sudden trouble"
    if "Dusthana" in text:
        return "it rules a difficult house (6th, 8th or 12th) and could magnify those problems"
    if "Kendradhipati" in text or "Maraka" in text:
        return "it rules a house of loss or obstruction for your rising sign"
    return "it is not a safe stone for your chart"


def _stance_hint(facts: dict) -> str:
    n_for, n_against = len(facts["signals_for"]), len(facts["signals_against"])
    if facts["domain_key"] == "gemstones_remedies":
        return "favourable" if facts["gems"]["recommended"] else "mixed"
    if facts["domain_key"] == "out_of_domain":
        return "not_astrological"
    if n_for - n_against >= 2:
        return "favourable"
    if n_against - n_for >= 2:
        return "difficult"
    return "mixed"


# ------------------------------------------------------------------------- the model
_SYSTEM = (
    "You are an experienced Vedic astrologer answering ONE question for one person. "
    "Judge the question yourself: work out what it is really asking, pick the few chart facts "
    "that bear on it, and ignore the rest. Use ONLY the facts supplied; never invent a placement, "
    "date, planet position or gemstone. Speak to the reader as 'you'. Plain, warm language, no "
    "headings, no jargon without a plain-word gloss. Keep it short: answer is 2-3 sentences "
    "(at most 60 words); why is 2-4 bullets (at most 22 words each), each tied to one supplied "
    "fact that matters for THIS question; timing is one sentence, or empty when the question has "
    "no 'when' to it; steps are 1-3 concrete actions (at most 20 words each). Do not repeat the "
    "question, do not mention Lal Kitab or Chandra Naadi, and do not pad. "
    "stance: favourable, mixed or difficult. For a gemstone question use favourable when a stone "
    "is recommended. If the question has nothing to do with life or astrology, use not_astrological "
    "and politely say what you can help with."
)

_LANG_NOTE = {
    "hi_en": "Write every text field in natural Hindi using English letters (Roman Hindi), not Devanagari.",
    "te_en": "Write every text field in natural Telugu using English letters (Roman Telugu), not Telugu script.",
}


def _lang_key(lang: str) -> str:
    low = str(lang or "").lower().strip()
    if low in ("hi_en", "hinglish", "hi", "hindi"):
        return "hi_en"
    if low in ("te_en", "tenglish", "te", "telugu"):
        return "te_en"
    return "en"


def _facts_for_prompt(facts: dict) -> str:
    h = facts["house"]
    lord = h["lord"]
    lines = [
        f"QUESTION: {facts['question']}",
        f"AREA: {facts['domain']}",
        f"Rising sign: {facts['lagna']} (ruled by {facts['lagna_lord']}). Moon sign: {facts['moon_sign']}.",
    ]
    if facts["domain_key"] not in ("gemstones_remedies", "out_of_domain"):
        lines.append(
            f"Governing house: {_ord(h['number'])} house ({h['sign']}), ruled by {lord['planet']}, "
            f"which sits in house {lord['house']} in {lord['sign']}"
            + (f", {_dignity_words(lord['dignity'])}" if _dignity_words(lord['dignity']) else "")
            + (" (a difficult house: 6/8/12)." if lord["hard_house"] else "."))
        for k in facts["karakas"]:
            state = []
            if _dignity_words(k["dignity"]):
                state.append(_dignity_words(k["dignity"]))
            if k["hard_house"]:
                state.append("in a difficult house")
            if k["combust"]:
                state.append("too close to the Sun")
            lines.append(f"Natural indicator {k['planet']}: house {k['house']} in {k['sign']}"
                         f"{', ' + ', '.join(state) if state else ', no affliction'}.")
        if h["sav"]:
            lines.append(f"Sign score of the {_ord(h['number'])} house: {h['sav']} (28 is average).")
        p = facts["periods"]
        if p["main"]:
            lines.append(f"Running: {p['main']} main period until {p['main_until']}; "
                         f"{p['sub']} sub-period {p['sub_from']} to {p['sub_until']}.")
        if facts["next_window"]:
            lines.append(f"Next period that supports this: {facts['next_window']}.")
        if facts["transits"]:
            lines.append(f"Slow transits now: {facts['transits']}.")
        lines.append(f"Agreeing signals: {', '.join(facts['signals_for']) or 'none'}. "
                     f"Against: {', '.join(facts['signals_against']) or 'none'}.")
    if "gems" in facts:
        for r in facts["gems"]["recommended"]:
            lines.append(f"SUITS: {r['gem']} ({r['planet']}, rules houses {r['houses']}) - {r['metal']}, "
                         f"{r['finger']}, {r['day']} morning, bright half of the month.")
        for r in facts["gems"]["avoid"]:
            lines.append(f"AVOID: {r['gem']} ({r['planet']}) - {r['reason']}.")
        lines.append("Other stones are not advised; use that planet's mantra and charity instead.")
    return "\n".join(lines)


def _allowed_years(facts: dict) -> set[str]:
    blob = " ".join(str(v) for v in (facts.get("periods") or {}).values()) + " " + str(facts.get("next_window"))
    return set(re.findall(r"20\d\d", blob)) | {str(date.today().year)}


_GEM_NAMES = ("ruby", "pearl", "red coral", "coral", "emerald", "yellow sapphire", "blue sapphire",
              "diamond", "white zircon", "hessonite", "gomed", "cat's eye", "cats eye")


def _check(reading: QuestionReading, facts: dict) -> list[str]:
    from llm.validate import enforce_user_voice
    text = " ".join([reading.answer, reading.timing, *reading.why, *reading.steps])
    problems = list(enforce_user_voice(text))
    if not reading.answer.strip():
        problems.append("answer is empty")
    if len(reading.answer.split()) > 90:
        problems.append("answer is too long")
    if len(reading.why) > 4 or len(reading.steps) > 3:
        problems.append("too many bullets")
    if re.search(r"lal\s*kitab|chandra\s*naadi", text, re.I):
        problems.append("mentions a technique that is not part of this answer")
    bad_years = set(re.findall(r"20\d\d", text)) - _allowed_years(facts)
    if bad_years:
        problems.append("names a year that is not in the facts: " + ", ".join(sorted(bad_years)))
    if "gems" in facts:
        allowed = " ".join(r["gem"].lower() for r in facts["gems"]["recommended"] + facts["gems"]["avoid"])
        low = text.lower()
        for name in _GEM_NAMES:
            if name in low and name not in allowed:
                problems.append(f"names a gemstone ({name}) that is not in the supplied list")
                break
    return problems


def _llm_allowed() -> bool:
    try:
        from core.config import S
        return bool(S.llm_tab_enabled("user_question"))
    except Exception:  # noqa: BLE001
        return False


def _ask_model(facts: dict, lang: str) -> Optional[QuestionReading]:
    if not _llm_allowed():
        return None
    try:
        from core.llm_client import complete_model
    except Exception:  # noqa: BLE001
        return None
    system = _SYSTEM
    note = _LANG_NOTE.get(_lang_key(lang))
    if note:
        system += " " + note
    user = _facts_for_prompt(facts)
    user += f"\n\nSuggested stance from the signals (override only with a reason): {_stance_hint(facts)}."
    try:
        reading = complete_model(QuestionReading, system, user, temperature=0.3)
    except Exception as exc:  # noqa: BLE001
        print(f"[question_reading] model call failed: {type(exc).__name__}: {exc}", flush=True)
        return None
    if reading is None:
        return None
    problems = _check(reading, facts)
    if not problems:
        return reading
    try:
        retry = complete_model(
            QuestionReading, system,
            user + "\n\nYour previous answer was rejected: " + "; ".join(problems[:4])
            + ". Rewrite it using only the facts above.", temperature=0.2)
    except Exception:  # noqa: BLE001
        retry = None
    if retry is not None and not _check(retry, facts):
        return retry
    print(f"[question_reading] model answer rejected: {problems[:3]}", flush=True)
    return None


# ----------------------------------------------------------------------- the fallback
def _gem_fallback(facts: dict) -> QuestionReading:
    rec, avoid = facts["gems"]["recommended"], facts["gems"]["avoid"]
    why: list[str] = []
    steps: list[str] = []
    if rec:
        names = " and ".join(r["gem"] for r in rec)
        answer = (f"For your {facts['lagna']} rising sign, {names} "
                  f"{'suits' if len(rec) == 1 else 'suit'} you best.")
        for r in rec:
            hs = _and_join([_ord(int(h)) for h in r["houses"]])
            why.append(f"{r['planet']} rules your {hs} house{'s' if len(r['houses']) > 1 else ''}, "
                       f"which makes {r['gem']} a supportive stone for you.")
            steps.append(f"Wear {r['gem']} in {r['metal'].lower()} on the {r['finger'].lower()}, "
                         f"on a {r['day']} morning in the bright half of the month.")
    else:
        answer = ("No gemstone is clearly safe for your chart right now, so the better route is "
                  "mantra and charity rather than wearing a stone.")
    if avoid:
        shown = avoid[:3]
        answer += " Avoid " + ", ".join(r["gem"] for r in shown) + "."
        for r in shown[:2]:
            why.append(f"{r['gem']} is best avoided because {r['reason']}.")
    if not steps:
        lord = facts["lagna_lord"]
        steps.append(f"Chant {lord}'s mantra on {_WEEKDAY.get(lord, 'its day')}s and give a small donation.")
    return QuestionReading(stance="favourable" if rec else "mixed", answer=answer,
                           why=why[:4], timing="", steps=steps[:3])


def _fallback(facts: dict) -> QuestionReading:
    key = facts["domain_key"]
    if key == "out_of_domain":
        return QuestionReading(
            stance="not_astrological",
            answer=("This looks like a question outside what a birth chart can answer. Ask about your "
                    "career, relationships, money, health, family, travel or timing and your chart "
                    "will answer it."),
            why=[], timing="", steps=[])
    if key == "gemstones_remedies":
        return _gem_fallback(facts)

    stance = _stance_hint(facts)
    h = facts["house"]
    lord = h["lord"]
    dw = _dignity_words(lord["dignity"])
    place = (f"{lord['planet']}, the planet that rules this area, sits in house {lord['house']} "
             f"in {lord['sign']}" + (f" and is {dw}" if dw else ""))
    opener = {"favourable": "Your chart supports this.",
              "mixed": "This is possible, but expect some effort and delay.",
              "difficult": "This is not easy right now, though it is not closed."}[stance]
    window = facts["next_window"]
    answer = f"{opener} {place}."
    if lord["hard_house"]:
        answer += " That house tends to slow things down."
    why = [f"{_ord(h['number'])} house is ruled by {lord['planet']}, placed in house {lord['house']}"
           + (" - a hard house that brings delay." if lord["hard_house"] else " - a supportive placement.")]
    if facts["karakas"]:
        k = facts["karakas"][0]
        bad = k["hard_house"] or k["dignity"] in _BAD_DIGNITY or k["combust"]
        why.append(f"{k['planet']}, the natural indicator for this, is in house {k['house']} "
                   f"({k['sign']}) and is {'under strain' if bad else 'well placed'}.")
    if h["sav"]:
        why.append(f"The {_ord(h['number'])} house scores {h['sav']} "
                   f"({'above' if h['sav'] >= 28 else 'below'} the average of 28).")
    p = facts["periods"]
    if p["sub"]:
        why.append(f"You are running {p['main']} main period and {p['sub']} sub-period "
                   f"(until {p['sub_until']}).")
    timing = f"The period that supports this most is {window}." if window else ""
    steps = []
    if facts["karakas"]:
        k = facts["karakas"][0]["planet"]
        steps.append(f"Strengthen {k}: chant its mantra and offer a small donation on {_WEEKDAY.get(k, 'its day')}s.")
    if window and key in _MOVE_DOMAINS:
        steps.append(f"Time the key move for the {window} window where you can, and prepare before it.")
    return QuestionReading(stance=stance, answer=answer, why=why[:4], timing=timing, steps=steps[:3])


def build_reading(conf: Any, pc: dict, cfg: dict, *, lang: str = "en") -> tuple[QuestionReading, dict, bool]:
    """Returns (reading, fact sheet, written_by_model)."""
    facts = build_fact_sheet(conf, pc, cfg)
    reading = _ask_model(facts, lang)
    if reading is not None:
        return reading, facts, True
    return _fallback(facts), facts, False


# ------------------------------------------------------------------------- rendering
_LABELS = {
    "en": {
        "kicker": "Your question", "why": "What your chart shows", "when": "When",
        "do": "What to do", "facts": "Chart facts behind this answer",
        "favourable": "Looks favourable", "mixed": "Mixed", "difficult": "Needs care",
        "not_astrological": "Outside astrology",
        "lock": "Timing and next steps are in the full reading",
        "lockchip": "Unlock timing and steps",
        "cta": "Unlock full answer", "sub": "Timing window and practical steps for this question.",
    },
    "hi_en": {
        "kicker": "Aapka prashna", "why": "Aapki kundli kya dikhati hai", "when": "Kab",
        "do": "Kya karein", "facts": "Is jawab ke peeche kundli ke tathya",
        "favourable": "Anukool", "mixed": "Milajula", "difficult": "Savdhani zaroori",
        "not_astrological": "Jyotish se bahar",
        "lock": "Samay aur agle kadam poori reading mein hain",
        "lockchip": "Samay aur kadam unlock karein",
        "cta": "Poora jawab unlock karein", "sub": "Is prashna ka samay aur vyavaharik kadam.",
    },
    "te_en": {
        "kicker": "Mee prashna", "why": "Mee kundali emi chupisthundi", "when": "Eppudu",
        "do": "Em cheyali", "facts": "Ee samadhanam venuka kundali vivaralu",
        "favourable": "Anukoolam", "mixed": "Mishramam", "difficult": "Jagrattha avasaram",
        "not_astrological": "Jyotishyam bayata",
        "lock": "Samayam mariyu tarvata chese pani poorthi reading lo unnayi",
        "lockchip": "Samayam mariyu steps unlock cheyandi",
        "cta": "Poorthi samadhanam unlock cheyandi", "sub": "Ee prashnaku samayam mariyu practical steps.",
    },
}
_STANCE_COLOR = {"favourable": "#1c6b45", "mixed": "#8a6a1f", "difficult": "#a3341f",
                 "not_astrological": "#6a7080"}


def _esc(text: str) -> str:
    return html.escape(str(text or "").strip())


def _facts_list(facts: dict) -> list[str]:
    rows = [f"Rising sign {facts['lagna']}, Moon in {facts['moon_sign']}."]
    h = facts["house"]
    if facts["domain_key"] not in ("gemstones_remedies", "out_of_domain"):
        lord = h["lord"]
        rows.append(f"{_ord(h['number'])} house ({h['sign']}), ruled by {lord['planet']} in house "
                    f"{lord['house']} ({lord['sign']}).")
        for k in facts["karakas"]:
            rows.append(f"{k['planet']} (natural indicator): house {k['house']}, {k['sign']}.")
        if h["sav"]:
            rows.append(f"Sign score of the {_ord(h['number'])} house: {h['sav']} (average 28).")
        p = facts["periods"]
        if p["main"]:
            rows.append(f"{p['main']} main period until {p['main_until']}; {p['sub']} sub-period "
                        f"{p['sub_from']} to {p['sub_until']}.")
        if facts["transits"]:
            rows.append(facts["transits"][0].upper() + facts["transits"][1:] + ".")
    return rows


def render_html(reading: QuestionReading, facts: dict, *, paid: bool, lang: str = "en",
                price: int = 298) -> str:
    L = _LABELS[_lang_key(lang)]
    color = _STANCE_COLOR[reading.stance]
    out_of_scope = reading.stance == "not_astrological"
    meta_line = f"{html.escape(facts['lagna'])} rising &middot; Moon in {html.escape(facts['moon_sign'])}"

    parts = [
        '<div class="uq-reading" style="margin:10px 0 24px;">',
        f'<article class="card" style="border-left:4px solid {color};background:#fff;border-radius:12px;'
        f'padding:18px 22px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,.03);">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin-bottom:6px;">'
        f'<span style="font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;font-weight:700;color:#6a7080;">'
        f'{L["kicker"]}</span>'
        f'<span class="pill" style="font-size:.68rem;font-weight:700;padding:3px 10px;border-radius:99px;'
        f'background:#fbf6e4;color:{color};">{L[reading.stance]}</span></div>'
        f'<h2 style="font-family:Georgia,serif;font-size:1.2rem;margin:4px 0 10px;color:#1f2430;font-weight:600;'
        f'line-height:1.35;">&ldquo;{_esc(facts["question"])}&rdquo;</h2>'
        f'<p style="font-size:1rem;line-height:1.6;color:#2c3140;margin:0 0 6px;">{_esc(reading.answer)}</p>'
        f'<p style="font-size:.78rem;color:#6a7080;margin:8px 0 0;">{meta_line}</p>'
        '</article>',
    ]

    if reading.why:
        items = "".join(f'<li style="margin-bottom:6px;">{_esc(w)}</li>' for w in reading.why)
        parts.append(
            '<article class="card" style="background:#fff;border:1px solid #e8e4dc;border-radius:12px;'
            'padding:16px 20px;margin-bottom:14px;">'
            f'<div style="font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;font-weight:800;'
            f'color:#7a4b18;margin-bottom:8px;">{L["why"]}</div>'
            f'<ul style="margin:0;padding-left:18px;font-size:.92rem;line-height:1.55;color:#2c3140;">{items}</ul>'
            '</article>')

    has_more = bool(reading.timing.strip() or reading.steps)
    if has_more and (paid or out_of_scope):
        block = ""
        if reading.timing.strip():
            block += (f'<p style="margin:0 0 10px;font-size:.92rem;line-height:1.55;color:#2c3140;">'
                      f'<b>{L["when"]}:</b> {_esc(reading.timing)}</p>')
        if reading.steps:
            li = "".join(f'<li style="margin-bottom:6px;">{_esc(s)}</li>' for s in reading.steps)
            block += (f'<div style="font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;font-weight:800;'
                      f'color:#1c6b45;margin:4px 0 6px;">{L["do"]}</div>'
                      f'<ul style="margin:0;padding-left:18px;font-size:.92rem;line-height:1.55;color:#2c3140;">{li}</ul>')
        parts.append('<article class="card" style="background:#f9fbf9;border:1px solid #d4e8dc;'
                     'border-left:4px solid #1c6b45;border-radius:12px;padding:16px 20px;margin-bottom:14px;">'
                     + block + '</article>')
    elif has_more:
        parts.append(
            '<div class="lock-wrap" data-unlock="1" role="button" tabindex="0" '
            'style="margin:16px 0;border-radius:12px;cursor:pointer;">'
            f'<div class="lock-blur" style="padding:16px 20px;font-size:.88rem;line-height:1.55;">'
            f'<b>{L["when"]}:</b> {L["lock"]}.</div>'
            f'<div class="lock-over" data-unlock="1"><span class="lock-chip" data-unlock="1" '
            f'style="font-size:.72rem;padding:7px 18px;cursor:pointer;">&#128274; {L["lockchip"]}</span></div></div>'
            '<div class="buy" style="margin:16px 0;background:linear-gradient(135deg,#1f2430 0%,#141720 100%);'
            'border:1px solid #c9a227;border-radius:14px;padding:20px;text-align:center;color:#fff;">'
            f'<p style="font-size:.88rem;color:#b8bdcc;margin:0 0 14px;line-height:1.5;">{L["sub"]}</p>'
            '<a class="cta" href="#unlock" data-unlock="1" style="cursor:pointer;display:inline-flex;'
            'align-items:center;justify-content:center;background:linear-gradient(135deg,#e8b75b 0%,#c9a227 100%);'
            'color:#16181d;font-weight:700;font-size:.95rem;padding:12px 26px;border-radius:99px;'
            f'text-decoration:none;width:100%;max-width:320px;">&#128274; {L["cta"]} &mdash; &#8377;{int(price)}</a>'
            '</div>')

    fact_rows = _facts_list(facts)
    if paid and not out_of_scope and len(fact_rows) >= 3:
        rows = "".join(f'<li style="margin-bottom:4px;">{_esc(r)}</li>' for r in fact_rows)
        parts.append(
            '<details class="astro-proof-details" style="background:#fcfbf8;border:1px solid #e8e4dc;'
            'border-radius:10px;padding:12px 16px;margin:14px 0;">'
            f'<summary style="cursor:pointer;font-size:.82rem;font-weight:700;color:#7a4b18;">{L["facts"]}</summary>'
            f'<ul style="margin:10px 0 0;padding-left:18px;font-size:.84rem;line-height:1.55;color:#444;">{rows}</ul>'
            '</details>')
    parts.append("</div>")
    return "\n".join(parts)
