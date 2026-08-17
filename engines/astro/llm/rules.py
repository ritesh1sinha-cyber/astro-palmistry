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

# Astrology vocabulary is allowed in customer prose when the same term is
# grounded in the authoritative facts. This replaces the old blanket ban,
# which made Qwen sound like a philosopher instead of an astrologer.
_RAW_ASTRO_TERMS = {
    "sub-lord", "sublord", "karakamsa", "atmakaraka", "jamakkol", "prashna kundali",
}
_ASTRO_TECHNICAL_TERMS = (
    "mahadasha", "antardasha", "pratyantardasha", "dasha", "bhukti",
    "nakshatra", "varga", "lagna", "ascendant", "bhava", "graha", "yoga",
    "dosha", "manglik", "shadbala", "ashtakavarga", "sub-lord", "sublord",
    "karakamsa", "atmakaraka", "chara", "vimshottari", "yogini",
    "house lord", "lordship", "drishti", "aspect", "transit", "retrograde",
    "navamsha", "dashamsha", "saptamsha", "dvadasamsha", "d9", "d10", "d7",
    "d12", "d24", "d60",
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
    r"jamakkol|prashna kundali|case-book|technical reason|"
    r"raw classical wording|source rule text|internal rule id",
    re.I,
)
# Line names ("life line", "head line") are the everyday nouns a reader
# expects and are already present in PalmFacts, so they are allowed. The mounts
# are named too: they are the palmist's own vocabulary, and stripping them was
# what made the reading sound like a machine describing pads of skin. What
# stays blocked is source labelling and single-mark overclaim.
_PALM_BODILY = re.compile(
    r"\b(?:digestion|digestive|acidity|indigestion|blood pressure|blood sugar|"
    r"thyroid|insomnia|migraine|infection|inflammation|injury|surgery|"
    r"medication|prescription|immune system|nervous system|hormonal)\b",
    re.I,
)
_PALM_RAW = re.compile(
    r"\b(?:traditional reading|classical text|classical rule|case[- ]?book|"
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
You are an experienced Vedic astrologer writing a private consultation for the client.

Python owns the astrological truth. You own the interpretation and expression.
Use ONLY the supplied facts JSON. Do not add or change promise, activation,
confidence, agreement, direction, timing, planets, houses, remedies or events.
Never calculate a new chart factor. Never invent a date.

ASTROLOGER VOICE V3 — CHART READING, NOT PHILOSOPHY
1. Sound like a practicing astrologer speaking across the table, not a
   therapist, motivational speaker, philosopher, life coach or generic horoscope.
2. Explain the astrological reason AND the human manifestation. Do not hide the
   astrology behind vague phrases such as "this phase asks you to grow".
3. Use astrological terminology naturally when it is present in the facts:
   Lagna, Moon sign, Nakshatra, Mahadasha, Antardasha, Pratyantardasha, transit,
   house, lord, drishti, yoga, D9/D10/D7/D12, Ashtakavarga and similar terms.
   A technical term is allowed only when the same term/factor is grounded in facts.
4. Never dump calculations. Translate them: "Saturn's influence on the 10th
   house increases responsibility" is good; a list of raw degrees is not.
5. Confluence matters. When multiple supplied factors agree, say so naturally:
   "The stronger point here is that the dasha and transit are reinforcing the
   same career theme." Do not count methods aloud unless the facts provide that
   interpretation.
6. Do not turn one isolated planet or rule into a life verdict.
7. Use calibrated astrologer certainty: "the chart supports", "this is a strong
   indication", "the period favours", "there is a clear tendency", "this can
   manifest as". Reserve "may" for genuinely uncertain/private circumstances.
   Do not weaken every sentence into vague possibility language.
8. Do not claim a private circumstance is known unless the facts explicitly say
   it is known. For likely current-life topics, say "If this is what brought you
   here..." or "This may be the area taking more attention."
9. Never diagnose disease, predict death/lifespan, or guarantee a legal/medical
   outcome. Health stays at wellbeing/routine/preventive-care language.
10. Do not invent gemstones, mantras, rituals, donations or remedies.
11. Second person: "you/your". No third-person case-study prose.
12. No horoscope clichés, motivational filler or philosophical conclusions. Every
    paragraph must either name a supplied astrological factor and explain its
    meaning, or describe a supplied manifestation in ordinary life. Do not write
    generic statements such as "this is a time of growth", "trust the process",
    "you are entering a new chapter" or "balance is important" unless the supplied
    facts make that specific statement meaningful.
13. The reader should feel that you have actually opened the chart. Prefer:
    chart factor → astrological meaning → lived consequence. Do not produce a
    sequence of motivational statements with astrology hidden underneath.
14. Do not repeat the same fact in different wording. If Rahu/Jupiter/10th-house
    evidence is already used to explain career, do not repeat it as a second
    generic career paragraph. Add the next layer: promise, activation, timing,
    manifestation or practical response.
15. Use "this chart", "your chart", "this period" and "in your case" naturally.
    Avoid the voice of a generic horoscope addressed to millions of people.
16. No horoscope clichés or empty philosophy. Every paragraph should contain a
    concrete astrological interpretation or a concrete manifestation grounded in
    the supplied facts.
17. Return ONLY the requested JSON object. No markdown.
18. Keep every string within its schema max_length and write in English.

A good sentence pattern is:
ASTROLOGICAL FACT → WHY IT MATTERS → HOW IT MAY SHOW UP → TIMING/ACTION IF SUPPLIED.

Example of the desired voice:
"Saturn is putting pressure on the career axis in the present period. That can
make progress feel slower than the effort you are putting in, but it is also a
classic consolidation pattern: responsibility increases first, recognition
follows after the structure is established."

Do NOT copy this example into the report unless the supplied facts support it.
"""

#: A palm reading used to be written on top of the Vedic astrologer prompt, so
#: the model read six thousand characters of "name the Lagna, the Nakshatra, the
#: Mahadasha" and a few hundred of "you are a palmist, never name a dasha". It
#: obeyed the longer half: the prose came back as third-person horoscope filler
#: with the hand nowhere in it. A palmist gets their own instructions.
PALM_SYSTEM_PROMPT = """\
You are an experienced palmist reading a person's hands with them sitting in
front of you. You have already examined both palms; the findings are supplied
to you as facts.

Python owns what the hands show. You own the reading and the words.
Use ONLY the supplied facts JSON. Never invent a line, a mark, a mount, an age
or a remedy, and never sharpen a possibility into a fact.

PALMIST VOICE — THE HAND, THEN THE LIFE
1. Address the person as "you" in every single sentence. They are sitting with
   you. "Meera's hand shows" and "she tends to" are notes written about someone
   who left the room — never write them. first_name is there so you know whose
   hands you are holding, not to write about them in the third person.
2. Name the hand feature you are reading from, the way a palmist does out loud:
   the life, head, heart and fate lines; the mounts by name (Jupiter, Saturn,
   Apollo, Mercury, Venus, Luna, Mars); the girdle of Venus; the ring of
   Solomon; the shape of the palm and fingers. Only the features in the facts.
3. Then say what it means for an ordinary week — money, work, a partner, sleep,
   temper, a decision they keep postponing. Hand feature → what it means →
   how it shows up.
4. You are a palmist, not a philosopher, a coach or a horoscope column. Banned:
   journey, path, universe, energy as a force, embrace, transformation, growth
   as a noun, "this phase asks you to", "trust the process", and any sentence
   that would fit any reader with any hands.
5. Astrology is a different consultation. Never name a dasha, a lagna, a house,
   a nakshatra, a transit or a planet as a body in the sky. Jupiter and Saturn
   appear here only as mounts on the palm.
6. A hand shows tendency, capacity and need — never an event that has happened.
   Never tell them they have an illness, a court case, a loss or a debt. Where
   the facts mark something as a possibility, keep it one: "you may be
   carrying", "if this is what brought you here".
7. Never diagnose disease and never predict death or lifespan. A short or
   broken life line is about vitality and pace, never about length of life.
   Health stays at energy, sleep, appetite and routine.
8. Calibrated palmist certainty: "your hand reads as", "this is a strong sign
   of", "on this line that usually shows as", "you may find". Do not weaken
   every sentence into vagueness and do not guarantee anything.
9. Do not claim fame, wealth or leadership from a single mark, and do not
   flatter. A difficult sign is said plainly, with what to do about it.
10. Do not repeat one finding in different words. Each paragraph adds the next
    thing the hands say.
11. Return ONLY the requested JSON object. No markdown. English only. Keep
    every string within its schema max_length.

A good sentence pattern is:
HAND FEATURE → WHAT THAT SIGN MEANS → HOW IT SHOWS IN AN ORDINARY WEEK →
TIMING OR WHAT TO DO, IF SUPPLIED.

Example of the desired voice:
"Your head line runs long and dips towards the Mount of Luna, which is the
hand of someone who thinks in pictures and needs to sleep on a decision before
it feels right. It reads as indecision to people who want an answer today, so
say plainly that you will come back tomorrow rather than going quiet."

Do NOT copy this example into the reading unless the supplied facts support it.
"""


def _base_prompt(kind: str) -> str:
    return PALM_SYSTEM_PROMPT if kind == "palm" else SYSTEM_PROMPT


def prompt_version(kind: str) -> str:
    """Registry name plus a digest of the prompt text itself.

    The digest is what makes the response cache honest: editing a prompt and
    forgetting to bump the registry used to serve the previous wording for
    the rest of the cache TTL, which reads as "the change did nothing".
    """
    base = PROMPT_VERSIONS.get(kind, "REPORT_PROSE_PROMPT_V1")
    digest = hashlib.sha256(
        (_base_prompt(kind) + _prompt_extra(kind)).encode("utf-8")
    ).hexdigest()[:8]
    return f"{base}-{digest}"


def _prompt_extra(kind: str) -> str:
    return {
        "full_report": (
            "Return ConversationalProse for a short reading that sounds like an astrologer "
            "sitting across the table — not a 10-page technical report. "
            "Target length: free about 350–450 words; paid about 1000–1400 words. "
            "Use ONLY the supplied facts. Do not invent personality traits, phase tone, "
            "recent months, life areas, dates, manifestations or remedies. "
            "Structure: "
            "(1) astrological_basis — 2–4 sentences naming the supplied chart factors "
            "that govern this reading: vedic_context.lagna / rising_sign, moon_sign, "
            "nakshatra, mahadasha/period_lord and antardasha/sub_period_lord. Name them "
            "the way an astrologer would: 'You are in a Rahu mahadasha, with Jupiter "
            "running the current antardasha.' Do not hide them behind a gloss; "
            "(2) interpretation — 2–4 sentences translating those factors into how this "
            "stretch of life actually feels, from phase_tone and phase_notes; "
            "(3) personality — one warm paragraph from personality_traits. Free gets "
            "3–4 sentences; paid gets 6–9 and must use EVERY trait supplied, each "
            "opened out into how it shows in ordinary life rather than listed; "
            "(4) current_phase — 2–4 full sentences using phase_tone, phase_end and "
            "phase_notes. Never answer with a single adjective like 'supportive'; "
            "(5) recent_months — summarise every recent_months window to build trust "
            "(what was happening and which life areas felt harder); "
            "(6) hardest_area_note — one short line from hardest_area_labels; "
            "(7) mind_now — one short line for EVERY life_state.mind_now entry, in the "
            "same order, using that entry's label and experience words. Every entry has "
            "is_fact=false, so each line must stay a possibility ('if money has been on "
            "your mind', 'you may be carrying'). Speak the way a person speaks, not the "
            "way a report describes them: 'growth at home is a likely experience' is a "
            "note about the data, 'things at home may be opening up a little' is a line "
            "to a reader. Never tell them they have a problem, an illness, a case or a "
            "loss; "
            "(8) why_now — 2–4 sentences on why this stretch feels the way it does, from "
            "life_state.chapter_tone, themes, emotional_pressure and decision_pressure. "
            "Explain the astrological reason and the lived manifestation; do not dump raw calculations or internal levels. "
            "'the decision pressure is high' is our own field spoken aloud. Say what it "
            "is like to live in this stretch and what it asks for; "
            "(9) family_note — one line for EVERY family_notes entry, in the order "
            "supplied, each written from that entry's own notes and tags only. Say "
            "what that person was like to grow up around, or for relation=home what "
            "the household itself was like; never predict anything about them, never "
            "mention their health, their death or their money, and never move a "
            "detail from one relation to another. An entry with method_count of 1 "
            "was seen by a single method, so keep it to a leaning ('your father "
            "comes across as'); at 2 or more you may say it plainly. Leave the list "
            "empty when family_notes is empty; "
            "(10) areas — ONLY when access=paid: one ConversationalAreaProse for EVERY card, in card order. Each area is a mini consultation, not a template dump. "
            "Write each area as if you are explaining the chart across the table. First astrological_basis: 1–2 sentences naming only the supplied planetary/house/dasha/transit/yoga/divisional factors that actually support the area. Then interpretation: 2–4 sentences that connect those factors to the persons lived experience. Do not merely restate the basis. Then outlook: 1–2 sentences that make the promise-versus-activation distinction clear. "
            "Timing is one concise sentence; the renderer will print authoritative exact dates separately. Do not invent or repeat dates. Manifestation "
            "is one sentence on how the supplied pattern can show up in ordinary life; transition_note is 1–2 sentences "
            "explaining the most important change inside the longer forecast using transition_map. "
            "Use only the supplied overlap stack; never invent a trigger or date. Remedy is one practical step "
            "from remedy_text/approved_remedies. Every area that reads mixed, weak or "
            "under strain MUST end with a remedy — never leave a difficulty without the "
            "step that helps. When access=free, leave areas empty. "
            "Name planets, houses, dashas, nakshatras, yogas and divisional charts when they are explicitly grounded in the supplied facts. Never invent them. "
            "Never invent dates. Soft modality only. Health language stays at routine/recovery."
        ),
        "full_report_areas": (
            "Return ConversationalAreasProse: one entry for EVERY card in the "
            "facts, in the order supplied, and nothing else. Write each area "
            "the way an experienced Vedic astrologer speaks it aloud. First "
            "astrological_basis: 1–2 sentences naming the supplied planetary, house, "
            "dasha, transit, nakshatra, yoga or divisional-chart factors that support "
            "the area — allowed_planets, house, vedic_context. Then interpretation: "
            "1–2 sentences explaining what the combined factors mean in practical life. "
            "Then outlook is 1–2 sentences saying whether "
            "this part of life is backed or under strain, from status, activation_status, "
            "direction and outlook_line; timing is one sentence naming the window from "
            "window/timing_windows; manifestation is one sentence on how it shows up day "
            "to day; transition_note is 1–2 sentences explaining the transition inside the "
            "longer forecast using only transition_map. Never invent a trigger or date. "
            "remedy is one practical step from "
            "remedy_text/approved_remedies. Every area that reads mixed, weak "
            "or under strain MUST end with a remedy — never leave a difficulty "
            "without the step that helps. Name planets, houses, dashas, nakshatras, "
            "yogas and divisional charts when explicitly grounded in the supplied facts. "
            "Never invent them or dates. Soft modality only. Health language stays at "
            "routine/recovery."
        ),
        "full_report_confluence": (
            "Write the classical Vedic reading for this page. Python owns ALL "
            "prediction truth — areas, phases, timing windows, status, activation, "
            "direction, planets, houses, dashas, nakshatras, yogas. You only rephrase "
            "the supplied facts into the authoritative, concrete voice of a practising "
            "Jyotish astrologer; you must not invent, calculate, or imply any astrological "
            "factor not already in the facts.\n"
            "RULES:\n"
            "1. Every claim traces to the supplied facts. No invented planets, houses, "
            "dashas, aspects or dates. Omit anything not in the input.\n"
            "2. Name the running mahadasha and sub-period STRICTLY from vedic_context "
            "(period_lord and sub_period_lord). NEVER call any other planet the main "
            "period or sub period lord. Other planets (e.g. Venus, Saturn) only govern "
            "specific houses or life areas, not the running dasha clock.\n"
            "3. No guaranteed/certain/destined language. No 'you will', 'guaranteed', "
            "'certain to', 'definitely will'. Use 'may indicate', 'suggests', 'is "
            "highlighted by'.\n"
            "4. Health language stays at routine/recovery. Never diagnose or predict "
            "conditions.\n"
            "5. Remedies only from the approved list in the facts.\n"
            "6. Use the 'you' perspective, never the reader's name and never she/he.\n"
            "7. Only use months that appear in the factual timing windows.\n"
            "8. Areas: use the short_phase labels and the area names from the facts.\n\n"
            "FIELDS OUTPUT (one object matching ReportConfluenceProse exactly):\n"
            "- astrological_basis: 2-4 sentences naming the supplied chart factors "
            "that govern this reading (lagna, moon sign, nakshatra, mahadasha and "
            "sub-period lord) in classical terms\n"
            "- interpretation: 2-4 sentences connecting those factors to how this "
            "stretch of life actually feels, from phase_tone and phase_notes\n"
            "- personality: one warm paragraph from personality_traits in the "
            "classical voice; 3-4 sentences free, 6-9 paid\n"
            "- current_phase: 2-4 full sentences using phase_tone, phase_end and "
            "phase_notes; never a single adjective\n"
            "- hardest_area_note: one short line from hardest_area_labels\n"
            "- mind_now: one hedged line per life_state.mind_now entry, in order\n"
            "- why_now: 2-4 sentences on the supplied astrological reason this stretch "
            "feels as it does and how it can manifest\n"
            "- family_note: one line per family_notes entry, in order, each naming "
            "that relation and using only that entry's own notes\n"
            "- areas: dict keyed by area key; each value is a 1-2 sentence classical "
            "interpretation for that area\n\n"
            "DO NOT INCLUDE: astrological calculations, new planets/houses/dashas not "
            "in the facts, guaranteed predictions, diagnoses, remedies not in the "
            "approved list, or dates not in the timing windows."
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
            "Return ConversationalPalmProse for a short palm reading. Use ONLY "
            "PalmFacts. Keep the specific words from semantic_summary and "
            "recognize — do not flatten them into generic advice. "
            "Every field is written to the person as 'you'; a sentence with "
            "'she', 'he' or their name as the subject is a failed field. "
            "Structure: "
            "(1) personality — one paragraph from personality_traits that sounds like "
            "nature read from the hands; "
            "(2) current_phase — use life_stage_note and the demanding_aspect_label "
            "to say where they are now and which area needs more care; "
            "(3) hardest_area_note — one short line about the demanding aspect; "
            "(4) mind_now — one short line for EVERY palm_state.mind_now entry, in "
            "the same order, using that entry's label and experience words. Every "
            "entry has is_fact=false, so each line stays a possibility ('you may be "
            "carrying', 'if this is what brought you here'). A hand shows tendency "
            "and need, never an event: never tell them they have a problem, an "
            "illness, a case or a loss; "
            "(5) why_now — 2–4 sentences on why this reads the way it does, from "
            "palm_state.chapter_tone, themes and confidence_note. Explain how it "
            "feels to live in, never the technique, and never read the levels out; "
            "(6) hand_contrast_note — 2–3 sentences on the two hands, ONLY from "
            "hand_contrast: steady means both hands agree and that part of them is "
            "long-standing, developed means they grew into it, latent means it is "
            "there underneath with less room than it wants. Say which hand is which "
            "in plain words — the hand named in hand_contrast.dominant_hand is what "
            "they have made of life, the other is what they started with. Claim no "
            "change the facts do not list, and leave this empty when hand_contrast "
            "is absent; "
            "(7) areas — ONLY when access=paid: one entry per aspect with outlook "
            "(from semantic_summary — keep those words), timing (from age_window when "
            "present), manifestation (from recognize), and remedy (only if "
            "remedies_allowed and remedies are supplied; otherwise leave remedy empty). "
            "When access=free, leave areas empty. "
            "Name the life, head, heart and fate lines directly. "
            "Never invent ages or marks, never claim fame/leadership from one mark. "
            "Health stays at energy/routine."
        ),
        "chat": (
            "Answer a paid follow-up about THEIR report only. "
            "If the question asks for something not in the facts, set "
            "out_of_scope=true and give a short refusal. Never invent new "
            "predictions. List used_fact_ids of facts you relied on. "
            "The facts describe one of four readings, and `kind` tells you "
            "which. kind=palm is a hand reading: talk about the aspects and "
            "what they say, keep the strength the reading gave each one, and "
            "never state an age or a date that is not in the facts. "
            "kind=horary answers one question with one verdict: you may "
            "explain the verdict and its timing, never reverse it, and when "
            "the methods contradicted each other stay cautious. "
            "kind=user_question is a reading of ONE question the reader "
            "already asked (the `question` field). Follow-ups about that "
            "same matter are in scope, including ordinary words for it — "
            "for a case: court, legal, lawsuit, verdict, hearing, result, "
            "outcome. Restate the direction, confidence and the timing "
            "windows already in the facts. Never invent a new date. Never "
            "set out_of_scope for a follow-up about that same question. "
            "kind=full_report is a birth-chart reading of life areas."
        ),
    }.get(kind, "")


def system_prompt_for(kind: str) -> str:
    base = _base_prompt(kind)
    extra = _prompt_extra(kind)
    if not extra:
        return base
    return f"{base}\nPrompt version: {prompt_version(kind)}. {extra}"


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
               "access", "cards", "timing_windows", "vedic_context")


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
        "result", "outcome", "expect",
    })
    tokens.update(asked_topic_terms(facts))
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


# Palm aspect keys to the everyday words that name them. A palm follow-up is
# still about the reading when it points at one of the life areas the hand
# shows, so these feed both the on-topic gate and the deterministic chat
# fallback.
_PALM_ASPECT_WORDS = {
    "character": frozenset({
        "character", "temperament", "nature", "personality", "self", "will",
    }),
    "mind": frozenset({
        "mind", "intellect", "thinking", "thought", "decision", "decisions",
        "focus", "memory",
    }),
    "love": frozenset({
        "love", "marriage", "marry", "married", "wedding", "spouse", "husband",
        "wife", "partner", "relationship",
    }),
    "career": frozenset({
        "career", "job", "work", "promotion", "business", "profession",
        "office", "job change",
    }),
    "wealth": frozenset({
        "money", "wealth", "income", "salary", "finance", "financial", "loan",
        "debt", "rich",
    }),
    "health": frozenset({
        "health", "energy", "vitality", "wellbeing", "illness", "routine",
        "recovery", "fitness",
    }),
    "travel": frozenset({
        "travel", "change", "move", "moving", "imagination", "shift", "journey",
    }),
    "fortune": frozenset({
        "fortune", "luck", "opportunity", "success", "destiny", "direction",
    }),
}

# Words that point at the hand itself, not a life area. The palm reading is
# the whole hand, so these are always about the reading.
_PALM_FEATURE_WORDS = frozenset({
    "thumb", "finger", "fingers", "fingertip", "fingernail", "palm", "hand",
    "hands", "line", "lines", "life line", "head line", "heart line",
    "fate line", "mount", "mounts", "crease", "creases", "nails", "wrist",
    "fingerprint",
})


def palm_aspect_for_question(payload: Any, q: str) -> Optional[dict]:
    """Which palm aspect a follow-up question asks about, or None.

    ``payload`` is the projected public facts (the ``aspects`` list), and
    ``q`` is the lowercased question. Matching runs on the aspect keys actually
    present so an aspect the reading never reported can't be cited. When the
    question could name two areas ("job change" touches work and change), the
    aspect with the most word matches wins.
    """
    aspects = payload.get("aspects") if isinstance(payload, dict) else None
    if not isinstance(aspects, list):
        return None
    best: Optional[dict] = None
    best_score = 0
    for a in aspects:
        if not isinstance(a, dict):
            continue
        key = str(a.get("aspect") or "").lower()
        title = str(a.get("title") or "").lower()
        words = set(_PALM_ASPECT_WORDS.get(key, frozenset()))
        words.add(key)
        words.add(key.replace("_", " "))
        if title:
            words.add(title)
        score = sum(1 for w in words if len(w) >= 3 and w in q)
        if score > best_score:
            best = a
            best_score = score
    return best


# A user-question / horary report is about one asked matter. Everyday words
# for that matter are restatement, not invention — "verdict" on a case
# question, "hearing" on a lawsuit. Full-report and palm stay empty so the
# asserted-circumstance gate still catches claims nobody asked about.
_TOPIC_SYNONYMS = {
    "legal": frozenset({
        "case", "court", "legal", "lawsuit", "litigation", "dispute",
        "verdict", "hearing", "trial", "judgment", "judgement", "bail",
    }),
    "litigation": frozenset({
        "case", "court", "legal", "lawsuit", "litigation", "dispute",
        "verdict", "hearing", "trial", "judgment", "judgement", "bail",
    }),
    "marriage": frozenset({
        "marriage", "marry", "married", "wedding", "spouse", "husband",
        "wife", "partner", "relationship",
    }),
    "love": frozenset({
        "marriage", "marry", "married", "wedding", "spouse", "husband",
        "wife", "partner", "relationship", "love",
    }),
    "health": frozenset({
        "health", "illness", "recovery", "heal", "wellbeing",
    }),
    "career": frozenset({
        "career", "job", "work", "promotion", "business",
    }),
    "money": frozenset({
        "money", "income", "salary", "finance", "wealth", "loan", "debt",
    }),
}
_ASKED_STOPWORDS = frozenset({
    "will", "the", "and", "you", "your", "can", "when", "what", "how",
    "this", "that", "with", "from", "have", "has", "for", "about",
    "only", "asking", "please", "just", "does", "did", "are", "was",
    "win", "get", "got", "may", "might", "into", "over",
})
_FOLLOWUP_TIMING = re.compile(
    r"\b(when|timing|window|expect|result|outcome|verdict|date|month|"
    r"year|period|how long)\b",
    re.I,
)


def asked_topic_terms(facts: Any) -> set[str]:
    """Words the reader already used, plus ordinary synonyms for that topic."""
    payload = public_fact_payload(facts) if facts is not None else {}
    if not isinstance(payload, dict):
        return set()
    kind = str(payload.get("kind") or "")
    if kind not in ("user_question", "horary"):
        return set()
    route = payload.get("route") if isinstance(payload.get("route"), dict) else {}
    blob = " ".join([
        str(payload.get("question") or ""),
        str(payload.get("area_key") or ""),
        str(payload.get("subject") or ""),
        str(route.get("domain") or ""),
        str(route.get("topic") or ""),
    ]).lower()
    terms = {t for t in re.findall(r"[a-z]{3,}", blob) if t not in _ASKED_STOPWORDS}
    keys = {
        str(payload.get("area_key") or "").lower(),
        str(route.get("domain") or "").lower(),
        str(route.get("topic") or "").lower(),
    }
    for key, extra in _TOPIC_SYNONYMS.items():
        if key in keys or (terms & extra):
            terms.update(extra)
    return terms


def followup_is_on_asked_topic(facts: Any, question: str) -> bool:
    """True when a follow-up is still about this reading."""
    payload = public_fact_payload(facts) if facts is not None else {}
    if not isinstance(payload, dict):
        return False
    kind = str(payload.get("kind") or "")
    q = (question or "").strip().lower()
    if not q:
        return False
    if kind == "palm":
        # The palm reading is the whole hand: a follow-up about a life area
        # it shows, about the hand itself, or about a timing window is still
        # this reading, never a new matter.
        if _FOLLOWUP_TIMING.search(q):
            return True
        if any(re.search(rf"\b{re.escape(w)}\b", q) for w in _PALM_FEATURE_WORDS if len(w) >= 4):
            return True
        return palm_aspect_for_question(payload, q) is not None
    if kind not in ("user_question", "horary"):
        return False
    asked = asked_topic_terms(facts)
    if any(re.search(rf"\b{re.escape(term)}\b", q) for term in asked if len(term) >= 4):
        return True
    if not _FOLLOWUP_TIMING.search(q):
        return False
    # "when next year?" on a case reading is still the case. "when will I
    # get married?" names a different matter and stays out of scope.
    other = {t for t in re.findall(r"[a-z]{3,}", q) if t not in _ASKED_STOPWORDS}
    for extra in _TOPIC_SYNONYMS.values():
        if not (asked & extra) and (other & extra):
            return False
    return True


def _restates_asked_circumstance(text: str, facts: Any) -> bool:
    """The reader named this matter; repeating it is not a new claim."""
    asked = asked_topic_terms(facts)
    if not asked:
        return False
    m = _ASSERTED_CIRCUMSTANCE.search(text or "")
    if not m:
        return False
    window = (text or "").lower()[m.start(): m.end() + 48]
    return any(term in window for term in asked if len(term) >= 4)


def scrub_palm_bodily(text: str) -> str:
    """Drop sentences that claim a bodily symptom from a photograph of a hand."""
    t = (text or "").strip()
    if not t or not _PALM_BODILY.search(t):
        return t
    parts = re.split(r"(?<=[.!?])\s+", t)
    kept = [p.strip() for p in parts if p.strip() and not _PALM_BODILY.search(p)]
    return " ".join(kept).strip()


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
    if _ASSERTED_CIRCUMSTANCE.search(t) and not _restates_asked_circumstance(t, facts):
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
    # Technical astrology is permitted only when the exact factor is grounded
    # in the authoritative facts. This keeps the report sounding like an
    # astrologer without allowing Qwen to invent a dasha, yoga or nakshatra.
    for term in _ASTRO_TECHNICAL_TERMS:
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", low):
            if term not in fact_raw.lower():
                if term in _RAW_ASTRO_TERMS:
                    fails.append("classical_raw")
                else:
                    fails.append(f"invented_astrology_term:{term}")
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
            # Customer-facing astrology may name a planet when the same
            # planet is present in authoritative facts.
            if planet not in allowed_planets and planet not in allowed and planet not in question_text:
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

    if facts is not None:
        try:
            from .validate import validate_dasha_lords
            fails.extend(validate_dasha_lords(t, facts))
        except Exception:
            pass

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
