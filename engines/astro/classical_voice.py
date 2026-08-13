#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sample-style bullets for the Classical Vedic Report.

The book corpora are OCR'd from print, so a raw clause can arrive with page
furniture, broken words, or the fatalistic register the classical texts are
written in. Every clause is graded here before it is allowed near a customer,
then framed the way a practising astrologer speaks: named chart cause first,
plain human effect second.
"""
from __future__ import annotations

import html
import re

from bhardwaj_prose import (
    PLANET_ROLE,
    _fix_fragmented_periods,
    dignity_plain,
    house_plain,
    humanize_book_line,
)
from bhardwaj_semantic import STRONG, WEAK, _clean_ocr, pick_book_clause
from qa_checks.classical_boundary import classical_violations

__all__ = [
    "book_clause",
    "bullet",
    "bullets",
    "label_for",
    "lord_cause",
    "placement_cause",
    "sentence_ok",
]

# Sentences carrying these are dropped whole. Death, named disease, widowhood
# and defamation are outside what this product is willing to say, however
# plainly the source book states them.
_FATAL = re.compile(
    r"\b("
    r"die|dies|died|death|dead|corpse|funeral|cremat|mortal|fatal|"
    r"widow|widower|bereave|issueless|barren|abort|miscarr|"
    r"leprosy|cancer|tuberculosis|epilep|paralys|insane|insanity|lunatic|"
    r"rheumat|arthrit|asthma|diabet|piles|tumou?r|ulcer|jaundice|typhoid|gout|"
    r"hernia|fistula|venereal|syphil|gonorrh|"
    r"blind|deaf|dumb|lame|crippl|impoten|eunuch|"
    r"murder|suicide|imprison|jail|poison|"
    r"adulter|prostitut|immoral|sinful|wicked|characterless|"
    r"loss of (?:wife|husband|son|daughter|child)"
    r")\b",
    re.I,
)

# Harsh but usable. The classical judgement survives; the register is modernised.
_SOFTEN: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bimpoverishment\b", re.I), "financial strain"),
    (re.compile(r"\bpoverty\b", re.I), "periods of financial pressure"),
    (re.compile(r"\bdebt-?ridden\b", re.I), "carrying heavier borrowing than is comfortable"),
    (re.compile(r"\bhurt by fire\b", re.I), "prone to burns or accidents around heat"),
    (re.compile(r"\bmiserable\b", re.I), "low in spirits"),
    (re.compile(r"\bcruel\b", re.I), "blunt"),
    (re.compile(r"\bquarrelsome\b", re.I), "argumentative"),
    (re.compile(r"\bfurious\b", re.I), "quick-tempered"),
    (re.compile(r"\bgreedy\b", re.I), "acquisitive"),
    (re.compile(r"\bcheat(?:ed|s)?\b", re.I), "let down"),
    (re.compile(r"\benemies\b", re.I), "opponents"),
    (re.compile(r"\benemy\b", re.I), "opposition"),
    (re.compile(r"\bSatoguni\b", re.I), "principled"),
    (re.compile(r"\bindepandant\b", re.I), "independent"),
    (re.compile(r"\bluckless\b", re.I), "slow to catch a break"),
    (re.compile(r"\binauspicious\b", re.I), "unconventional"),
    # Classical idiom for property and public life, which reads as a claim
    # about the reader's actual occupation if left as the book states it.
    (re.compile(r"\ba landlord\b", re.I), "an owner of land or property"),
    (re.compile(r"\bsuccessful in politics\b", re.I), "suited to public life"),
    (re.compile(r"\barrogant\b", re.I), "self-assured"),
    (re.compile(r"\bOne who does\b"), "someone who does"),
    (re.compile(r"\bYou are someone who\b"), "You are the kind of person who"),
    (re.compile(r"\bsuffering from\b", re.I), "prone to"),
    (re.compile(r"\bsuffers from\b", re.I), "is prone to"),
    (re.compile(r"\bsuffer from\b", re.I), "are prone to"),
    # Cleanups for phrases the replacements above can leave behind.
    (re.compile(r"\bprone to (?:opponents|opposition)\b", re.I), "likely to face opposition"),
    # The books end a trait list with a bare noun phrase. Reattach it to the
    # sentence instead of printing the fragment.
    (re.compile(r",\s*government or official work\b", re.I),
     ", and suited to government or official work"),
    (re.compile(r",\s*rich\b(?!\s+(?:in|with))", re.I), ", and well-provided for"),
    (re.compile(r"\bYou['\u2019]s\b"), "Your"),
]

# OCR artefacts that mark a clause as unusable rather than merely harsh.
_JUNK = re.compile(r"={4,}|-{4,}|PAGE \d+|\balpetic\b|\bJatak\b\s*$", re.I)

_SIGNS = (
    "Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|"
    "Sagittarius|Capricorn|Aquarius|Pisces"
)
# The books list every sign branch for a placement in one paragraph. Only the
# caller knows which branch is this chart, so branch sentences are dropped and
# the real placement is stated by placement_cause() instead.
_SIGN_BRANCH = re.compile(
    rf"\b(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\s+in\s+(?:{_SIGNS})\b",
    re.I,
)

# OCR frequently drops the subject, leaving a bare predicate.
_HEADLESS = re.compile(
    r"^(will|would|shall|may|can|is|are|has|have|gets?|becomes?|makes?|gives?)\b", re.I,
)

# "with weak Saturn in lagna ... will be sick" is the book's other branch, not
# this chart. Strength is decided from the precompute, never from the prose.
_CONDITIONAL = re.compile(
    r"\b(?:weak|afflicted|strong|exalted|debilitated)\s+(?:Sun|Moon|Mars|Mercury|Jupiter|"
    r"Venus|Saturn|Rahu|Ketu|lord|lagna)\b|\bof weak\b|\bif afflicted\b|\bin case\b|"
    r"\bdebilitated or\b|\bwhen weak\b",
    re.I,
)

# Chapter preamble describing the sign itself rather than predicting anything.
_PREAMBLE = re.compile(
    r"\bsign of (?:the )?Zodiac\b|\bbelongs to .{0,30}in our body\b|\bIts lord is\b|"
    r"\bthe constellation of\b.{0,20}\bis ruled\b",
    re.I,
)

# Definite event claims about relatives are outside what this product asserts.
_THIRD_PARTY_EVENT = re.compile(
    r"\b(?:father|mother|brother|sister|spouse|wife|husband|son|daughter|children|"
    r"uncle|aunt|relatives?|friends?|in-laws?|grand(?:father|mother)|"
    r"brothers|sisters|sons|daughters)\s+(?:will|shall)\b",
    re.I,
)

# The books state family discord as fact. A prediction that the reader is at
# odds with their own household is not something this product will assert,
# however plainly the source says it.
_RELATIONAL = re.compile(
    r"\b(?:little|no) (?:pleasure|happiness|comfort) from\b|"
    r"\bdivide (?:your|the|his|her) family\b|"
    r"\benmity\b|\bhate[sd]?\b|\bdisobedient\b|\bdevoid of\b|"
    r"\bseparated from (?:your|his|her|the) (?:family|wife|husband|children)\b|"
    r"\btrouble[sd]? (?:from|with) (?:your |his |her )?"
    r"(?:wife|husband|children|father|mother|brother|sister)\b",
    re.I,
)

# The books predict in the future tense throughout. The sample report states
# standing traits in the present, so standing traits are re-tensed.
_TENSE: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bYou will be\b"), "You are"),
    (re.compile(r"\byou will be\b"), "you are"),
    (re.compile(r"\bYou will have\b"), "You have"),
    (re.compile(r"\byou will have\b"), "you have"),
    (re.compile(r"\bYou will not\b"), "You do not"),
    (re.compile(r"\byou will not\b"), "you do not"),
    (re.compile(r"\bYou will\b"), "You tend to"),
    (re.compile(r"\byou will\b"), "you tend to"),
    # A book sentence often continues with bare "will ..." after a comma, where
    # the subject is still the reader.
    (re.compile(r",\s*will be\b"), ", are"),
    (re.compile(r",\s*will have\b"), ", have"),
    (re.compile(r",\s*will\b"), ", tend to"),
]

_NAKSHATRA_LEAD = re.compile(r"^(?:A|The) child born in (.+?),? will (be|have)\s*", re.I)

# OCR splices two predicates together ("Will be A child born in X will be tall").
_SPLICE_HEAD = re.compile(r"^(?:will|would|shall)\s+be\s+(?=A child born|The native|You)", re.I)
_WILL_BE = re.compile(r"\bwill be\b", re.I)


def _esc(text: object) -> str:
    return html.escape(str(text or ""))


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def sentence_ok(sentence: str) -> bool:
    """True when a book sentence is clean enough and mild enough to print."""
    s = (sentence or "").strip()
    if len(s) < 20 or _JUNK.search(s) or _FATAL.search(s) or _SIGN_BRANCH.search(s):
        return False
    if _CONDITIONAL.search(s) or _PREAMBLE.search(s) or _THIRD_PARTY_EVENT.search(s):
        return False
    if _RELATIONAL.search(s):
        return False
    if not s[0].isupper() or len(_WILL_BE.findall(_SPLICE_HEAD.sub("", s))) > 1:
        return False
    words = s.split()
    if len(words) < 4 or any(len(w) > 24 for w in words):
        return False
    letters = sum(c.isalpha() or c.isspace() for c in s)
    return letters / len(s) >= 0.85


def _soften(text: str) -> str:
    text = _SPLICE_HEAD.sub("", text)
    text = _NAKSHATRA_LEAD.sub(
        lambda m: f"Born under {m.group(1)}, you {'have' if m.group(2).lower() == 'have' else 'are'} ",
        text,
    )
    for pattern, replacement in _SOFTEN:
        text = pattern.sub(replacement, text)
    if _HEADLESS.match(text):
        text = "You " + text[0].lower() + text[1:]
    for pattern, replacement in _TENSE:
        text = pattern.sub(replacement, text)
    return text


def book_clause(raw: str, *, dignity: str = "", direction: str = "neutral",
                domain: str = "", max_sentences: int = 2) -> str:
    """Return printable book prose for a placement, or "" if nothing survives.

    Callers must treat "" as "fall back to the modern catalog" rather than
    printing whatever the OCR happened to contain.
    """
    if not raw or not raw.strip():
        return ""
    picked = pick_book_clause(_clean_ocr(raw), dignity, direction)
    if not picked:
        return ""
    picked = humanize_book_line(picked, domain, direction) or picked

    kept = [_soften(s) for s in _sentences(picked) if sentence_ok(s)]
    # The final boundary drops offending sentences from the rendered page. If a
    # clause would be emptied there it must be rejected here instead, so the
    # caller falls back to its own wording rather than printing a stub.
    kept = [s for s in kept if not classical_violations(s)]
    if not kept:
        return ""
    out = " ".join(kept[:max_sentences])
    out = _fix_fragmented_periods(re.sub(r"\s+", " ", out)).strip()
    if out and out[-1] not in ".!?":
        out += "."
    return "" if classical_violations(out) else out


def _ord(n: int) -> str:
    n = int(n)
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}" + {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def placement_cause(planet: str, house: int, sign: str = "", dignity: str = "") -> str:
    """'Mercury sits in your 10th house in Gemini, strong in its own sign'."""
    where = f"{planet} sits in your {_ord(house)} house"
    if sign:
        where += f" in {sign}"
    if dignity and dignity != "neutral_sign":
        where += f", {dignity_plain(dignity)}"
    return where


def lord_cause(lord: str, lord_of: int, lord_in: int) -> str:
    """'your 7th lord Venus is placed in the 8th house of long-term change'."""
    return (
        f"your {_ord(lord_of)} lord {lord} is placed in the "
        f"{_ord(lord_in)} house of {house_plain(lord_in)}"
    )


def role_cause(planet: str) -> str:
    role = PLANET_ROLE.get(planet, "")
    return f"{planet}, which governs {role}" if role else planet


def strength_word(dignity: str) -> str:
    if dignity in STRONG:
        return "strong"
    if dignity in WEAK:
        return "under strain"
    return "steady"


# Sample-style bullet headings. Index-addressed so a section can label as many
# bullets as it actually produced without inventing claims to fill a fixed list.
_SECTION_LABELS: dict[str, list[str]] = {
    "personality": [
        "Core temperament", "Intelligence and approach", "Working style",
        "Emotional nature", "Communication", "Practical outlook", "What you are drawn to",
    ],
    "family": [
        "Family values", "Connection with mother", "Father and authority figures",
        "Family responsibilities", "Speech and family karma", "Financial background",
        "Cultural grounding",
    ],
    "career": [
        "Career mindset", "Professional strengths", "Work environment",
        "Career changes", "Income growth", "Competition", "Best career path",
    ],
    "marriage": [
        "Marriage potential", "Partner nature", "Relationship expectations",
        "Challenges", "Timing", "Advice", "Marriage quality",
    ],
    "current": [
        "Career pressure", "Mental activity", "Financial planning",
        "Health and stress", "Emotional tone", "Transformation phase", "Need for discipline",
    ],
    "future": [
        "Career", "Finances", "Relationships", "Health", "Personal growth",
        "Family matters", "Travel or relocation",
    ],
}

# Where a bullet is clearly owned by one planet, name it the way the sample does.
_PLANET_LABELS: dict[str, str] = {
    "Sun": "Confidence and authority",
    "Moon": "Emotional nature",
    "Mars": "Drive and temper",
    "Mercury": "Communication and analysis",
    "Jupiter": "Wisdom and growth",
    "Venus": "Comfort and relationships",
    "Saturn": "Discipline and endurance",
    "Rahu": "Ambition and restlessness",
    "Ketu": "Detachment and old patterns",
}


def label_for(section: str, index: int = 0, planet: str = "") -> str:
    if planet and planet in _PLANET_LABELS:
        return _PLANET_LABELS[planet]
    pool = _SECTION_LABELS.get(section) or []
    if not pool:
        return "Chart indication"
    return pool[index % len(pool)]


def bullet(label: str, cause: str, effect: str = "") -> str:
    """One sample-style line: bold heading, chart cause, then plain meaning."""
    text = (cause or "").strip()
    effect = (effect or "").strip()
    if effect:
        if text:
            text = text.rstrip(" .,;") + ". " + effect[0].upper() + effect[1:]
        else:
            text = effect
    if not text:
        return ""
    text = _fix_fragmented_periods(re.sub(r"\s+", " ", text)).strip()
    if text[-1] not in ".!?":
        text += "."
    if text[0].islower():
        text = text[0].upper() + text[1:]
    return f"<li><b>{_esc(label)}</b>: {_esc(text)}</li>"


def bullets(items: list[str], *, css: str = "cv-bullets") -> str:
    rows = "".join(i for i in items if i)
    return f'<ul class="{css}">{rows}</ul>' if rows else ""
