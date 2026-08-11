"""System prompts and executable prose checks for the LLM layer.

Python owns truth. Qwen owns expression. These rules enforce that boundary
even when the model ignores the prompt.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable

from .schemas import PROMPT_VERSIONS
from .facts import public_fact_payload

# Months that must not appear unless listed in the facts payload.
_MONTHS = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)
_PLANETS = (
    "sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn",
    "rahu", "ketu", "uranus", "neptune", "pluto",
)
_SIGNS = (
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
)
_SANSKRIT = (
    "mahadasha", "antardasha", "dashas?", "bhukti", "nakshatra", "varga", "lagna",
    "bhava", "graha", "yoga", "dosha", "manglik", "shadbala", "ashtakavarga",
    "sub-lord", "sublord", "karakamsa", "atmakaraka", "jamakkol",
    "prashna kundali", "kp", "bnn", "chara", "vimshottari", "yogini",
    "house lord", "area ruler", "classical rule", "case-book", "technical detail",
)
_GUARANTEE = re.compile(
    r"\b(you will|guaranteed|certain to|definitely will|must happen|"
    r"inevitably|without fail|without doubt|certainly|definitely|"
    r"you will never|cannot become|will fail|will never)\b",
    re.I,
)
_CERTAINTY_ESCALATION = re.compile(
    r"\b(definitely|certainly|guaranteed|inevitable|without doubt|"
    r"assured|bound to|sure to)\b",
    re.I,
)
_SPOUSE_ASSUME = re.compile(
    r"\b(your (?:spouse|husband|wife)|my (?:spouse|husband|wife))\b",
    re.I,
)
_REMEDY_INVENT = re.compile(
    r"\b(wear (?:a |an )?(?:ruby|emerald|pearl|coral|sapphire|diamond|topaz|"
    r"cat'?s eye|hessonite)|chant|mantra|donate|ritual|puja|homam|"
    r"yantra|gemstone)\b",
    re.I,
)
_LIFE_EVENTS = re.compile(
    r"\b(relocat(?:e|ion)|overseas|ceo|divorce|inheritance|"
    r"business launch|childbirth|pregnant|widow(?:ed)?|"
    r"accident is certain|heart (?:attack|problem)|diabetes|stroke|"
    r"cancer(?!\s+sign))\b",
    re.I,
)
_DIGIT = re.compile(r"\d")
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_HOUSE = re.compile(r"\b\d{1,2}(st|nd|rd|th)?\s*-?\s*house\b", re.I)
_FLATTERY = re.compile(
    r"\b(destined for greatness|born lucky|chosen one|superhuman|"
    r"unmatched brilliance)\b",
    re.I,
)
_CLASSICAL_RAW = re.compile(
    r"debt-ridden|hurt by fire|free from enemies|strong appetite|"
    r"you will be|bereaved|inauspicious deeds|classical rule-book|"
    r"sub-lord sense|recognition_tag_|Existing chart-rule|"
    r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+house|"
    r"8th lord|9th lord|10th lord|11th lord|12th lord|"
    r"sub[- ]lord|karakamsa|atmakaraka|cusp|"
    r"jamakkol|prashna kundali|case-book|technical reason)\b",
    re.I,
)

SYSTEM_PROMPT = """\
You are a report-language generator, not an astrology calculator.

Use ONLY the supplied facts JSON. Do not add facts. Do not change promise,
activation, confidence, agreement, direction or timing. Do not invent dates,
planets, remedies, life events, spouse/child status, or diagnoses. Do not
increase certainty beyond the supplied confidence. If the facts are
insufficient, say so plainly.

Hard rules (violations are rejected by QA):
1. Second person ("you" / "your"). No flattery, no horoscope clichés.
2. Soft modality only ("favours", "points to", "may show up as").
   Never "you will", "guaranteed", "certainly", "definitely".
3. No diagnosis, disease names, lifespan, death.
4. No Sanskrit technical terms (dasha, nakshatra, varga, lagna, yoga…).
5. No digits / years / month names unless they already appear in the facts.
6. Do not assume marital status ("your spouse/husband/wife") unless supplied.
7. Do not invent gemstones, mantras, rituals, or donations.
8. Reply with ONLY a JSON object matching the requested schema. No markdown.
9. Prefer everyday wording. Keep every string within its max_length.
"""


def prompt_version(kind: str) -> str:
    return PROMPT_VERSIONS.get(kind, "REPORT_PROSE_PROMPT_V1")


def system_prompt_for(kind: str) -> str:
    extra = {
        "full_report": (
            f"Prompt version: {prompt_version('full_report')}. "
            "Write language-only card prose: headline, summary, "
            "how_this_may_show_up (≤3), what_to_watch (≤2), what_helps (≤2), "
            "timing_summary. Never restate numeric scores or invent dates. "
            "If promise is mixed/weak, do not escalate timing into a guaranteed event. "
            "For health/challenge areas use sensitivity/routine language, never disease."
        ),
        "user_question": (
            f"Prompt version: {prompt_version('user_question')}. "
            "Fields: opening, answer, timing, action. "
            "Answer only from QuestionFacts. If no validated window supports the "
            "asked outcome, say the facts do not support a high-confidence claim."
        ),
        "horary": (
            f"Prompt version: {prompt_version('horary')}. "
            "Fields: lead, verdict_line, why, action. "
            "Horary is a moment chart — do not invent natal promise or new dates."
        ),
        "palm": (
            f"Prompt version: {prompt_version('palm')}. "
            "Fields: opening plus per-aspect headline/why/points. "
            "Do not invent ages, titles, or life events not in PalmFacts."
        ),
        "chat": (
            f"Prompt version: {prompt_version('chat')}. "
            "Answer a paid follow-up about THEIR report only. "
            "If the question asks for something not in the facts, set "
            "out_of_scope=true and give a short refusal. Never invent new "
            "predictions. List used_fact_ids of facts you relied on."
        ),
    }.get(kind, "")
    return SYSTEM_PROMPT + ("\n" + extra if extra else "")


def user_prompt(facts: Any, *, schema_name: str) -> str:
    payload = public_fact_payload(facts)
    return (
        f"Return a JSON object matching schema `{schema_name}`.\n"
        f"Facts (authoritative — do not contradict or expand):\n"
        f"{json.dumps(payload, ensure_ascii=False, default=str)}"
    )

def _fact_token_set(facts: Any) -> set[str]:
    raw = json.dumps(public_fact_payload(facts), default=str)
    tokens = set(re.findall(r"[a-zA-Z]{3,}", raw.lower()))
    tokens.update({
        "you", "your", "the", "and", "with", "this", "that", "here", "now",
        "may", "might", "could", "tend", "tends", "points", "favours", "shows",
        "life", "theme", "period", "phase", "effort", "care", "routine",
        "support", "caution", "mixed", "strong", "weak", "active", "promise",
        "pattern", "challenge", "timing", "window", "work", "home", "family",
        "relationship", "partnership", "recovery", "preventive", "sensitivity",
    })
    return tokens

def _fact_raw(facts: Any) -> str:
    return json.dumps(public_fact_payload(facts or {}), default=str)


_MONTH_FROM_NUM = {
    "01": "january", "02": "february", "03": "march", "04": "april",
    "05": "may", "06": "june", "07": "july", "08": "august",
    "09": "september", "10": "october", "11": "november", "12": "december",
}


def allowed_dates_from_facts(facts: Any) -> set[str]:
    raw = _fact_raw(facts)
    years = set(_YEAR.findall(raw))
    # Also collect ISO / Month YYYY fragments from window fields
    dates: set[str] = set(years)
    if hasattr(facts, "model_dump"):
        data = facts.model_dump(mode="json")
    else:
        data = facts or {}
    stack = [data]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                if k in ("start", "end", "allowed_dates") and v:
                    if isinstance(v, list):
                        dates.update(str(x) for x in v if x)
                    else:
                        dates.add(str(v))
                elif isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(cur, list):
            stack.extend(cur)
    return {d for d in dates if d}


def allowed_months_from_facts(facts: Any) -> set[str]:
    """Month names grounded by ISO/window dates already in the facts."""
    months: set[str] = set()
    for d in allowed_dates_from_facts(facts):
        low = str(d).lower()
        for name in _MONTHS:
            if name in low:
                months.add(name)
        m = re.search(r"(?:19|20)\d{2}[-/](\d{1,2})", low)
        if m:
            num = m.group(1).zfill(2)
            name = _MONTH_FROM_NUM.get(num)
            if name:
                months.add(name)
    return months


def allowed_planets_from_facts(facts: Any) -> set[str]:
    allowed = _fact_token_set(facts)
    return {p for p in _PLANETS if p in allowed}


def check_prose(text: str, facts: Any = None, *, area: str = "") -> list[str]:
    """Return a list of rule violations for one prose string (empty = ok)."""
    t = (text or "").strip()
    if not t:
        return []
    fails: list[str] = []
    low = t.lower()
    fact_raw = _fact_raw(facts) if facts is not None else ""
    allowed = _fact_token_set(facts) if facts is not None else set()
    allowed_dates = allowed_dates_from_facts(facts) if facts is not None else set()
    allowed_planets = allowed_planets_from_facts(facts) if facts is not None else set()

    if _GUARANTEE.search(t) or _CERTAINTY_ESCALATION.search(t):
        fails.append("certainty_escalation")
    if _FLATTERY.search(t):
        fails.append("flattery")
    if _CLASSICAL_RAW.search(t):
        fails.append("classical_raw")
    for term in _SANSKRIT:
        if re.search(rf"\b{term}\b", low):
            fails.append(f"sanskrit:{term}")
            break

    if _SPOUSE_ASSUME.search(t):
        if not re.search(r"\b(spouse|husband|wife|married|marital)\b", fact_raw, re.I):
            fails.append("assumed_spouse")

    if _REMEDY_INVENT.search(t):
        # Only allowed if the exact remedy token appears in approved_remedies
        if "approved_remedies" not in fact_raw and "remedy" not in fact_raw.lower():
            fails.append("invented_remedy")
        else:
            # still fail if gemstone/mantra words aren't in facts
            for m in _REMEDY_INVENT.finditer(t):
                token = m.group(0).lower()
                if token not in fact_raw.lower():
                    fails.append("invented_remedy")
                    break

    if _LIFE_EVENTS.search(t):
        for m in _LIFE_EVENTS.finditer(t):
            token = m.group(0).lower()
            if token not in fact_raw.lower() and token not in allowed:
                fails.append(f"invented_event:{token}")
                break

    for m in _YEAR.findall(t):
        if m not in allowed_dates and m not in fact_raw:
            fails.append(f"unexpected_year:{m}")
            break

    if _DIGIT.search(t):
        for ch in _DIGIT.findall(t):
            if ch not in fact_raw:
                fails.append("unexpected_digit")
                break

    allowed_months = allowed_months_from_facts(facts) if facts is not None else set()
    for month in _MONTHS:
        if month in low and month not in allowed and month not in allowed_months:
            fails.append(f"unexpected_month:{month}")
            break

    for planet in _PLANETS:
        if re.search(rf"\b{planet}\b", low):
            payload = public_fact_payload(facts) if facts is not None else {}
            kind = str(payload.get("kind") or "") if isinstance(payload, dict) else ""
            question_text = str(payload.get("question") or "").lower() if isinstance(payload, dict) else ""
            # Strict customer-facing kinds: planet names are technical jargon.
            if kind in ("full_report", "palm", "horary") or (
                kind == "user_question" and planet not in question_text
            ):
                fails.append(f"technical_planet:{planet}")
                break
            # Remaining kinds (e.g. chat with an allowed planet set): only
            # reject planets that are not grounded in the facts payload.
            if planet not in allowed_planets and planet not in allowed:
                fails.append(f"unexpected_planet:{planet}")
                break


    for sign in _SIGNS:
        if re.search(rf"\b{sign}\b", low) and sign not in allowed:
            fails.append(f"unexpected_sign:{sign}")
            break

    if _HOUSE.search(t) and "house" not in fact_raw.lower():
        fails.append("unexpected_house")

    if (area or "").lower() in ("health", "troubles", "wellbeing"):
        if re.search(r"\b(disease|diagnosis|cancer|diabetes|stroke|heart attack)\b", low):
            fails.append("health_diagnosis")

    return fails


def check_prose_fields(
    fields: Iterable[tuple[str, str]],
    facts: Any = None,
    *,
    area: str = "",
) -> list[str]:
    out: list[str] = []
    for name, text in fields:
        for v in check_prose(text, facts, area=area):
            out.append(f"{name}:{v}")
    return out


OUT_OF_SCOPE_REFUSAL = (
    "I can only talk about what is already in your reading. "
    "That question goes beyond the facts we have here — ask about a "
    "life area or timing window that appears in the report."
)
