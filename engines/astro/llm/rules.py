"""System prompts and executable prose checks for the LLM layer.

Python owns truth. Qwen owns expression. These rules enforce that boundary
even when the model ignores the prompt.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable, Optional

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
# Line names ("life line", "head line") are the everyday nouns a reader
# expects and are already present in PalmFacts, so they are allowed. What
# stays blocked is source labelling, mount jargon and single-mark overclaim.
_PALM_BODILY = re.compile(
    r"\b(?:digestion|digestive|acidity|indigestion|blood pressure|blood sugar|"
    r"thyroid|insomnia|migraine|infection|inflammation|injury|surgery|"
    r"medication|prescription|immune system|nervous system|hormonal)\b",
    re.I,
)
_PALM_RAW = re.compile(
    r"\b(?:mount of (?:jupiter|saturn|sun|apollo|mercury|venus|moon|mars)|"
    r"traditional reading|classical text|classical rule|case[- ]?book|"
    r"special mark|"
    r"promises? leadership|promises? success|promises? fame|"
    r"sudden,? powerful surge|standout moment that arrives fast)\b",
    re.I,
)
# The report ships in English. A multilingual model occasionally answers in
# its pretraining majority language, which reaches the customer as a page
# they cannot read. Devanagari is left out: remedy text may legitimately
# carry a transliterated or original mantra.
_NON_ENGLISH_SCRIPT = re.compile(
    r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af"
    r"\u0400-\u04ff\u0600-\u06ff\u0e00-\u0e7f]"
)
# The reading is spoken to the person, not about them. A model that slips into
# "Meera tends to…" produces a case study rather than a consultation.
_THIRD_PERSON_READER = re.compile(r"\b(?:she|he|her|hers|his|him)\b", re.I)
# The reading knows what the chart makes likely, never what is actually
# happening in the person's life. "You may be carrying money pressure" is the
# reading; "you are dealing with a court case" is a claim about circumstances
# nobody told us, and it is the fastest way to lose a reader's trust.
_ASSERTED_CIRCUMSTANCE = re.compile(
    r"\byou (?:are|have been|were) (?:currently |now )?"
    r"(?:facing|dealing with|going through|struggling with|suffering from|"
    r"fighting|caught in|stuck in)\b|"
    r"\byou (?:have|had) (?:a|an) (?:court case|case|dispute|loan|debt|"
    r"illness|disease|separation|divorce)\b|"
    r"\byour (?:father|mother|child|son|daughter|brother|sister) "
    r"(?:is|has been|was) (?:ill|unwell|sick|suffering|hospitalised|hospitalized)\b",
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
10. Write every string in English, whatever language the facts appear in.
11. Speak to the person, never about them: "you tend to…", never
    "Meera tends to…" and never she/he/her/his.
"""


def prompt_version(kind: str) -> str:
    """Registry name plus a digest of the prompt text itself.

    The digest is what makes the response cache honest: editing a prompt and
    forgetting to bump the registry used to serve the previous wording for
    the rest of the cache TTL, which reads as "the change did nothing".
    """
    base = PROMPT_VERSIONS.get(kind, "REPORT_PROSE_PROMPT_V1")
    digest = hashlib.sha256(
        (SYSTEM_PROMPT + _prompt_extra(kind)).encode("utf-8")
    ).hexdigest()[:8]
    return f"{base}-{digest}"


def _prompt_extra(kind: str) -> str:
    return {
        "full_report": (
            "Return ConversationalProse for a short reading that sounds like an astrologer "
            "sitting across the table — not a 10-page technical report. "
            "Target length: free about 350–450 words; paid about 900–1200 words. "
            "Use ONLY the supplied facts. Do not invent personality traits, phase tone, "
            "recent months, life areas, dates, manifestations or remedies. "
            "Structure: "
            "(1) personality — one warm paragraph from personality_traits. Free gets "
            "3–4 sentences; paid gets 6–9 and must use EVERY trait supplied, each "
            "opened out into how it shows in ordinary life rather than listed; "
            "(2) current_phase — 2–4 full sentences using phase_tone, phase_end and "
            "phase_notes. Never answer with a single adjective like 'supportive'; "
            "(3) recent_months — summarise every recent_months window to build trust "
            "(what was happening and which life areas felt harder); "
            "(4) hardest_area_note — one short line from hardest_area_labels; "
            "(5) mind_now — one short line for EVERY life_state.mind_now entry, in the "
            "same order, using that entry's label and experience words. Every entry has "
            "is_fact=false, so each line must stay a possibility ('if money has been on "
            "your mind', 'you may be carrying'). Speak the way a person speaks, not the "
            "way a report describes them: 'growth at home is a likely experience' is a "
            "note about the data, 'things at home may be opening up a little' is a line "
            "to a reader. Never tell them they have a problem, an illness, a case or a "
            "loss; "
            "(6) why_now — 2–4 sentences on why this stretch feels the way it does, from "
            "life_state.chapter_tone, themes, emotional_pressure and decision_pressure. "
            "Explain the feeling, never the technique, and never read the levels out: "
            "'the decision pressure is high' is our own field spoken aloud. Say what it "
            "is like to live in this stretch and what it asks for; "
            "(7) family_note — one line for EVERY family_notes entry, in the order "
            "supplied, each written from that entry's own notes and tags only. Say "
            "what that person was like to grow up around, or for relation=home what "
            "the household itself was like; never predict anything about them, never "
            "mention their health, their death or their money, and never move a "
            "detail from one relation to another. An entry with method_count of 1 "
            "was seen by a single method, so keep it to a leaning ('your father "
            "comes across as'); at 2 or more you may say it plainly. Leave the list "
            "empty when family_notes is empty; "
            "(8) areas — ONLY when access=paid: one ConversationalAreaProse for EVERY card. "
            "Write each area the way an astrologer speaks it aloud: outlook is 1–2 plain "
            "sentences saying whether this part of life is backed or under strain; timing "
            "is one sentence naming the window from timing_windows/window; manifestation "
            "is one sentence on how it shows up day to day; remedy is one practical step "
            "from remedy_text/approved_remedies. Every area that reads mixed, weak or "
            "under strain MUST end with a remedy — never leave a difficulty without the "
            "step that helps. When access=free, leave areas empty. "
            "Never name planets, houses, dashas or Sanskrit terms. "
            "Never invent dates. Soft modality only. Health language stays at routine/recovery."
        ),
        "full_report_areas": (
            "Return ConversationalAreasProse: one entry for EVERY card in the "
            "facts, in the order supplied, and nothing else. Write each area "
            "the way an astrologer speaks it aloud: outlook is 1–2 plain "
            "sentences saying whether this part of life is backed or under "
            "strain, from status, activation_status, direction and "
            "outlook_line; timing is one sentence naming the window from "
            "window/timing_windows; manifestation is one sentence on how it "
            "shows up day to day; remedy is one practical step from "
            "remedy_text/approved_remedies. Every area that reads mixed, weak "
            "or under strain MUST end with a remedy — never leave a difficulty "
            "without the step that helps. Never name planets, houses, dashas "
            "or Sanskrit terms. Never invent dates. Soft modality only. Health "
            "language stays at routine/recovery."
        ),
        "user_question": (
            "Fields: opening, answer, timing, action. "
            "QuestionFacts are projected from the full-report CanonicalAreaResult "
            "whenever truth_source=full_report_canonical. Treat canonical promise, "
            "activation, direction and timing as immutable. Do not recalculate the "
            "chart or create a second timing/confluence interpretation. If no "
            "validated window supports the asked outcome, say the facts do not "
            "support a high-confidence claim."
        ),
        "horary": (
            "Fields: lead, verdict_line, why, action. "
            "Horary is a moment chart — do not invent natal promise or new dates."
        ),
        "palm": (
            "Return ConversationalPalmProse for a short palm reading that sounds like a "
            "palmist sitting across the table. Use ONLY PalmFacts. "
            "Speak to the person as 'you' in every field. first_name is there so you "
            "know who you are talking to, not to write about them: 'Meera's hands "
            "show' is a report over their shoulder, 'your hands show' is a reading. "
            "Structure: "
            "(1) personality — one paragraph from personality_traits; "
            "(2) current_phase — use life_stage_note and the demanding_aspect_label "
            "to say where they are now and which area needs more care; "
            "(3) hardest_area_note — one short line about the demanding aspect; "
            "(4) mind_now — one short line for EVERY palm_state.mind_now entry, in "
            "the same order, using that entry's label and experience words. Every "
            "entry has is_fact=false, so each line stays a possibility ('you may be "
            "carrying', 'if this is what brought you here'). A hand shows tendency "
            "and need, never an event: never tell them they have a problem, an "
            "illness, a case or a loss. Speak the way a person speaks, not the way "
            "a report describes them; "
            "(5) why_now — 2–4 sentences on why this reads the way it does, from "
            "palm_state.chapter_tone, themes and confidence_note. Explain how it "
            "feels to live in, never the technique, and never read the levels out: "
            "'the decision pressure is high' is our own field spoken aloud; "
            "(6) hand_contrast_note — 2–3 sentences on the two hands, ONLY from "
            "hand_contrast: steady means both hands agree and that part of them is "
            "long-standing, developed means they grew into it, latent means it is "
            "there underneath with less room than it wants. Say which hand is which "
            "in plain words — the hand named in hand_contrast.dominant_hand is what "
            "they have made of life, the other is what they started with. Claim no "
            "change the facts do not list, and leave this empty when hand_contrast "
            "is absent; "
            "(7) areas — ONLY when access=paid: one entry per aspect with outlook "
            "(from semantic_summary), timing (from age_window when present), "
            "manifestation (from recognize), and remedy (only if remedies_allowed and "
            "remedies are supplied; otherwise leave remedy empty). "
            "When access=free, leave areas empty. "
            "You may name life/head/heart/fate line in plain words. "
            "Never name mounts after planets, never invent ages or marks, "
            "never claim fame/leadership from one mark. Health stays at energy/routine."
        ),
        "chat": (
            "Answer a paid follow-up about THEIR report only. "
            "If the question asks for something not in the facts, set "
            "out_of_scope=true and give a short refusal. Never invent new "
            "predictions. List used_fact_ids of facts you relied on. "
            "The facts describe one of three readings, and `kind` tells you "
            "which. kind=palm is a hand reading: talk about the aspects and "
            "what they say, keep the strength the reading gave each one, and "
            "never state an age or a date that is not in the facts. "
            "kind=horary answers one question with one verdict: you may "
            "explain the verdict and its timing, never reverse it, and when "
            "the methods contradicted each other stay cautious. "
            "Otherwise the facts are a birth-chart reading of life areas."
        ),
    }.get(kind, "")


def system_prompt_for(kind: str) -> str:
    extra = _prompt_extra(kind)
    if not extra:
        return SYSTEM_PROMPT
    return f"{SYSTEM_PROMPT}\nPrompt version: {prompt_version(kind)}. {extra}"


def user_prompt(facts: Any, *, schema_name: str, section: str = "") -> str:
    payload = public_fact_payload(facts)
    if str((payload or {}).get("kind") or "") == "full_report":
        payload = _compact_report_payload(payload, section=section)
    return (
        f"Return a JSON object matching schema `{schema_name}`.\n"
        f"Facts (authoritative — do not contradict or expand):\n"
        f"{json.dumps(payload, ensure_ascii=False, default=str)}\n"
        # Repeated after the facts, not only in the system prompt: a 7B model
        # writing a long reply drifts out of English somewhere past the first
        # few hundred tokens, and the last instruction it read is the one it
        # keeps. The QA gate catches the drift, but catching it costs the page.
        "Write every string in English."
    )


# Fields a card carries for validation, storage or the classic page, which the
# conversational writer never uses. They are not secret — the boundary already
# cleared them — they are simply the difference between a prompt that leaves
# room to write and one that does not.
_PROMPT_ONLY_NOISE = ("evidence", "question_lens", "prediction_strength")
# Who reads what. The opening of the page is written from the person and the
# phase; the life-area passages are written from the cards. Sending both sets
# to both calls is what left the model no room to answer either properly.
_PAGE_ONLY = ("cards", "timing_windows", "dashboard_buckets")
_AREAS_KEEP = ("kind", "first_name", "age_band", "age_years", "gender",
               "access", "cards", "timing_windows")


def _compact_report_payload(payload: dict, *, section: str = "") -> dict:
    """Trim the report prompt to what the prose is actually written from.

    The endpoint's context is 8k. A paid page sends eight cards and asks for
    roughly 1,200 words back, and the method-level evidence rows alone were
    taking a third of the window — which the model then paid for by running
    out of room mid-JSON and dropping the whole page to the classic template.
    """
    out = dict(payload or {})
    if section == "page":
        return {k: v for k, v in out.items() if k not in _PAGE_ONLY}
    if section == "areas":
        out = {k: v for k, v in out.items() if k in _AREAS_KEEP}
    cards = []
    for card in list(out.get("cards") or []):
        if not isinstance(card, dict):
            continue
        slim = {k: v for k, v in card.items()
                if k not in _PROMPT_ONLY_NOISE and v not in ([], {}, "", None)}
        # remedy_text and approved_remedies are usually the same sentence.
        remedy = str(slim.get("remedy_text") or "").strip()
        approved = [str(x).strip() for x in (slim.get("approved_remedies") or [])]
        if remedy and approved and approved[0] == remedy:
            slim.pop("approved_remedies", None)
        cards.append(slim)
    if cards:
        out["cards"] = cards
    return out


def chat_user_prompt(
    facts: Any,
    question: str,
    *,
    history: Optional[list[dict]] = None,
    available_fact_ids: Optional[list[str]] = None,
) -> str:
    """Chat message with the report facts, the question and the thread.

    Chat cannot reuse ``user_prompt``: that helper runs its whole argument
    through the fact allowlist, which is right for a facts object but strips
    a wrapper carrying question/history/ids — leaving the model with nothing
    to ground on.
    """
    payload = public_fact_payload(facts)
    turns = [
        {"role": str(t.get("role") or "")[:12], "content": str(t.get("content") or "")[:400]}
        for t in (history or [])
        if isinstance(t, dict) and str(t.get("content") or "").strip()
    ]
    parts = [
        "Return a JSON object matching schema `ChatAnswer`.",
        "Report facts (authoritative — do not contradict or expand):",
        json.dumps(payload, ensure_ascii=False, default=str),
    ]
    if available_fact_ids:
        parts += [
            "Fact ids you may cite in used_fact_ids:",
            json.dumps(list(available_fact_ids)[:80], ensure_ascii=False),
        ]
    if turns:
        parts += [
            "Earlier turns in this conversation (context only — the facts above "
            "still govern every claim):",
            json.dumps(turns[-6:], ensure_ascii=False),
        ]
    parts += ["Their question:", str(question or "")[:400]]
    return "\n".join(parts)

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
    """Month names grounded by any date already present in the facts.

    Window labels such as ``"May 2024 → Oct 2026"`` ground a month just as
    much as an ISO ``start``/``end`` pair does, and an abbreviation grounds
    the full name — otherwise a model that writes "October" for a fact that
    says "Oct" is rejected for a month it did not invent.
    """
    months: set[str] = set()
    sources = {str(d).lower() for d in allowed_dates_from_facts(facts)}
    sources.add(_fact_raw(facts).lower())
    abbrevs = {name[:3]: name for name in _MONTHS}
    dated = re.compile(
        r"\b(" + "|".join(abbrevs) + r")[a-z]*\.?[\s,]+(?:19|20)\d{2}\b"
    )
    for low in sources:
        for m in dated.finditer(low):
            months.add(abbrevs[m.group(1)])
        for m in re.finditer(r"(?:19|20)\d{2}[-/](\d{1,2})", low):
            name = _MONTH_FROM_NUM.get(m.group(1).zfill(2))
            if name:
                months.add(name)
    return months


def allowed_planets_from_facts(facts: Any) -> set[str]:
    allowed = _fact_token_set(facts)
    return {p for p in _PLANETS if p in allowed}


_NAME_AS_SUBJECT = (
    "is", "was", "has", "had", "tends", "tend", "may", "might", "will",
    "should", "does", "seems", "appears", "needs", "can",
)


def _names_the_reader(text: str, facts: Any) -> bool:
    """Catch "Meera's chart" / "Meera tends to" — the reader is "you".

    The pronoun gate misses the person's own name, which a follow-up answer
    slips into more easily than report prose because the name sits in the
    facts it was handed. Direct address ("Meera, your…") stays allowed.
    """
    payload = public_fact_payload(facts) if facts is not None else {}
    if not isinstance(payload, dict):
        return False
    name = str(payload.get("first_name") or "").strip()
    if len(name) < 3:
        return False
    esc = re.escape(name)
    if re.search(rf"\b{esc}(?:'s|\u2019s)\b", text, re.I):
        return True
    verbs = "|".join(_NAME_AS_SUBJECT)
    return bool(re.search(rf"\b{esc}\s+(?:{verbs})\b", text, re.I))


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

    if _NON_ENGLISH_SCRIPT.search(t):
        fails.append("non_english_text")
    if _THIRD_PERSON_READER.search(t) or _names_the_reader(t, facts):
        fails.append("third_person_reader")
    if _GUARANTEE.search(t) or _CERTAINTY_ESCALATION.search(t):
        fails.append("certainty_escalation")
    if _ASSERTED_CIRCUMSTANCE.search(t):
        fails.append("asserted_circumstance")
    if _FLATTERY.search(t):
        fails.append("flattery")
    if _CLASSICAL_RAW.search(t):
        fails.append("classical_raw")
    if isinstance(facts, dict):
        palm_payload = facts
    else:
        try:
            palm_payload = public_fact_payload(facts) if facts is not None else {}
        except Exception:
            palm_payload = {}
    palm_kind = palm_payload.get("kind") if isinstance(palm_payload, dict) else getattr(facts, "kind", "")
    palm_grade = str(
        palm_payload.get("photo_grade") if isinstance(palm_payload, dict)
        else getattr(facts, "photo_grade", "") or ""
    ).lower()
    palm_marks_allowed = bool(
        palm_payload.get("special_marks_allowed") if isinstance(palm_payload, dict)
        else getattr(facts, "special_marks_allowed", False)
    )
    if palm_kind == "palm":
        if _PALM_RAW.search(t):
            fails.append("palm_technical_or_overclaim_language")
        mark_words = re.search(
            r"\b(?:trident|trishul|star|grille|fish|matsya|triangle|square|island|cross)\b",
            t, re.I,
        )
        if mark_words and not palm_marks_allowed:
            fails.append("palm_mark_not_supported_by_quality")
        if palm_grade == "poor":
            if re.search(r"\b(?:age|aged)\s+\d{1,3}\b", t, re.I):
                fails.append("palm_poor_photo_overreach")
        # A photograph of a hand cannot reach the body. "Stress that shows up
        # as changes in digestion" reads as a symptom the reading detected,
        # which is both unsupportable and the kind of line that sends someone
        # looking for a problem.
        if _PALM_BODILY.search(t):
            fails.append("palm_bodily_claim")
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

# Fact ids a chat answer may always cite. Chart reports speak in promise and
# activation, a palm reading in aspects and hand signs, and horary in a single
# verdict — one shared set keeps every kind citable by the same rules.
GENERIC_FACT_IDS = frozenset({
    "promise", "activation", "direction", "confidence", "timing",
    "manifestation", "action", "remedy", "why", "question",
    "aspect", "strength", "semantic_summary", "recognize", "life_stage",
    "personality", "phase", "verdict", "label", "lane", "subject",
})
