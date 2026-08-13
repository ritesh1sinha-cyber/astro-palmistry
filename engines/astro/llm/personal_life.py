"""Personal-life evidence: who they are, and the family around them.

Several specialist engines already describe personality and the parent/sibling
story — BNN, the blind chart, Bhardwaj, Mehta and the confluence personality
block. Each writes for a different reader, and each mixes a genuinely human
observation with the chart reasoning behind it in the same paragraph.

This module consolidates them for the LLM layer and keeps only the human half.
Filtering happens sentence by sentence rather than paragraph by paragraph on
purpose: "Your mother is practical and emotionally grounding — care shown
through service and quiet competence. (Moon in Virgo; 2nd-from-Moon Libra.)"
is one paragraph where the first sentence is exactly what the reader wants and
the rest is jargon the customer boundary forbids. Dropping the paragraph loses
the reading; dropping the sentence keeps it.

No new astrological judgement is made here. Nothing that leaves this module
names a planet, a sign, a house or a classical source.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Iterable

from .schemas import FamilyNoteFact

_RELATION_LABELS = {
    "father": "Father",
    "mother": "Mother",
    "siblings": "Siblings",
    "home": "The home you come from",
}

_PLANETS = (
    "sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn",
    "rahu", "ketu", "uranus", "neptune", "pluto",
)
_SIGNS = (
    "aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra",
    "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
)
_TECHNICAL = re.compile(
    r"\b(?:" + "|".join(_PLANETS) + r"|" + "|".join(_SIGNS) + r"|"
    r"lagna|nakshatra|dasha|bhukti|varga|bhava|graha|yoga|dosha|"
    r"atmakaraka|karakamsa|cusp|sub-?lord|chain|cluster|zodiac|"
    r"exalted|debilitat\w*|dignity|retrograde|conjunct\w*|aspect(?:s|ed|ing)?|"
    r"house|book|chart|progression|transit|natal|ascendant|"
    r"\d(?:st|nd|rd|th))\b",
    re.I,
)
_PARENTHETICAL = re.compile(r"\s*\([^)]*\)")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_DIGIT = re.compile(r"\d")
# A trait has to be about the reader, in the present. The specialist engines
# also emit coaching imperatives ("Channel the fire into clean ambition") and
# past-tense narrative ("These years were restless"), which read as filler in
# a personality paragraph and as an unsourced claim about their history.
_ADDRESSES_READER = re.compile(r"\byou\b|\byour\b", re.I)
_PAST_TENSE = re.compile(r"\b(?:was|were|had|used to|earlier|those years)\b", re.I)
# Fragments and list rows from the source books: neither is a sentence.
_LIST_ROW = re.compile(r":|;\s*[A-Z]|\bfields? of (?:study|work)\b", re.I)

_RELATION_WORDS = {
    "father": ("father", "dad", "paternal"),
    "mother": ("mother", "mum", "maternal"),
    "siblings": ("sibling", "brother", "sister", "birth order", "youngest",
                 "last-born", "eldest", "elder"),
}

# The household is claimed last and only by a sentence that named no relative,
# because most lines about the home also name the person who ran it, and one
# sentence appearing under both the mother and the home reads as padding.
_HOME_WORDS = (
    "home", "household", "domestic", "family life", "upbringing",
    "childhood", "property", "roof",
)

# Neutral family themes. Keeping the vocabulary closed means the tags stay
# customer-safe and comparable across sources, which is what lets the prose
# layer say two methods agreed.
_FAMILY_TAGS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("duty_and_responsibility", ("duty", "responsib", "obligation", "burden")),
    ("authority_and_discipline", ("authority", "strict", "discipline", "rules",
                                 "principled", "institution")),
    ("practical_support", ("practical", "grounding", "steady", "provider",
                           "competence", "service")),
    ("warmth_and_care", ("nurtur", "warm", "affection", "caring", "protective")),
    ("distance_or_separation", ("distance", "separation", "apart", "absent",
                               "estrange", "non-linear")),
    ("quiet_sacrifice", ("sacrifice", "behind-the-scenes", "unseen", "quietly")),
    ("elder_influence", ("elder", "older", "first-born", "senior")),
    ("independent_streak", ("non-conformist", "independent", "bold", "rebel")),
    ("health_attention", ("health", "wellbeing", "frail", "recovery", "care of")),
)


_RELATIONS: tuple[str, ...] = ("father", "mother", "siblings", "home")


def _empty_family() -> dict[str, list[str]]:
    return {relation: [] for relation in _RELATIONS}


def _tags_for(text: str) -> list[str]:
    low = (text or "").lower()
    return [tag for tag, needles in _FAMILY_TAGS if any(n in low for n in needles)]


def _safe_sentences(text: Any, *, trait: bool = False) -> list[str]:
    """Human sentences only — technical ones and chart asides are dropped."""
    raw = _PARENTHETICAL.sub("", re.sub(r"\s+", " ", str(text or ""))).strip()
    if not raw:
        return []
    out: list[str] = []
    for sentence in _SENTENCE_SPLIT.split(raw):
        s = sentence.strip(" -\u2013\u2014")
        if len(s) < 30 or len(s) > 240 or len(s.split()) < 6:
            continue
        if _TECHNICAL.search(s) or _DIGIT.search(s) or _LIST_ROW.search(s):
            continue
        if trait and (not _ADDRESSES_READER.search(s) or _PAST_TENSE.search(s)):
            continue
        try:
            from qa_checks.customer_text_sanitizer import is_customer_safe
            if not is_customer_safe(s):
                continue
        except Exception:  # noqa: BLE001
            pass
        if not s.endswith((".", "!", "?")):
            s += "."
        out.append(s[0].upper() + s[1:])
    return out


def _route_family(text: Any) -> dict[str, list[str]]:
    """Assign each sentence to the relation it actually talks about.

    Routing by the source's own idea of which relation it was describing put
    "The mother is authoritative" under the father, because the engines answer
    about parents as a pair and the book lines wander. A sentence that names no
    relation is dropped: for the family block, a line that could be about
    anyone is worse than nothing.
    """
    out: dict[str, list[str]] = {"father": [], "mother": [], "siblings": [],
                                 "home": []}
    for sentence in _safe_sentences(text):
        low = sentence.lower()
        claimed = False
        for relation, words in _RELATION_WORDS.items():
            if any(w in low for w in words):
                out[relation].append(sentence)
                claimed = True
        if not claimed and any(w in low for w in _HOME_WORDS):
            out["home"].append(sentence)
    return out


def _merge_family(into: dict[str, list[str]], new: dict[str, list[str]]) -> int:
    """Merge routed sentences; return 1 when this source said anything."""
    said = 0
    for relation, lines in new.items():
        if lines:
            said = 1
            into[relation] += lines
    return said


def _dedupe(lines: Iterable[str], limit: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        key = re.sub(r"[^a-z]", "", line.lower())[:60]
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(line)
        if len(out) >= limit:
            break
    return out


def _blind(pc: dict, dob: date | None, female: bool) -> tuple[list[str], dict[str, list[str]]]:
    traits: list[str] = []
    family: dict[str, list[str]] = _empty_family()
    if not dob:
        return traits, family
    try:
        from vedic_blindchart_report import Blind
        import blind_chart_analysis as BA
        import blind_chart_narrative as BN
    except Exception:  # noqa: BLE001
        return traits, family
    try:
        b = Blind(pc, dob)
    except Exception:  # noqa: BLE001
        return traits, family

    for reader in ("_father_read", "_mother_read", "_sibling_read"):
        fn = getattr(BA, reader, None)
        if fn is None:
            continue
        try:
            _merge_family(family, _route_family((fn(b) or {}).get("text", "")))
        except Exception:  # noqa: BLE001
            continue

    try:
        for section in BN.build_blind_narratives(b, female=female) or []:
            title = str(section.get("title") or "").lower()
            paragraphs = list(section.get("paragraphs") or [])
            if "parent" in title or "sibling" in title or "birth order" in title:
                for para in paragraphs:
                    _merge_family(family, _route_family(para))
            elif "core nature" in title or "personality" in title or title.startswith("you"):
                for para in paragraphs:
                    traits += _safe_sentences(para, trait=True)
                # The life-history section is also where the book says what the
                # household was like — "home and identity were shaped early".
                # Routing keeps only the sentences that name the home, so the
                # decade narrative itself never leaks in as a claim.
                if "life so far" in title or "so far" in title:
                    for para in paragraphs:
                        _merge_family(family, _route_family(para))
    except Exception:  # noqa: BLE001
        pass
    return traits, family


def _bnn(pc: dict) -> tuple[list[str], dict[str, list[str]]]:
    traits: list[str] = []
    family: dict[str, list[str]] = _empty_family()
    try:
        from bnn_chart import BnnChart, BnnTiming
        import bnn_human as BH
    except Exception:  # noqa: BLE001
        return traits, family
    try:
        ch = BnnChart(pc)
        bt = BnnTiming(ch, pc)
    except Exception:  # noqa: BLE001
        return traits, family
    try:
        traits += _safe_sentences((BH.human_personality(ch, bt) or ("", ""))[0], trait=True)
    except Exception:  # noqa: BLE001
        pass
    for reader in ("human_parents", "human_siblings"):
        fn = getattr(BH, reader, None)
        if fn is None:
            continue
        try:
            _merge_family(family, _route_family((fn(ch) or ("", ""))[0]))
        except Exception:  # noqa: BLE001
            continue
    return traits, family


def _signals(pc: dict, which: str) -> tuple[list[str], dict[str, list[str]]]:
    """Personality and family lines from the Bhardwaj / Mehta signal sets."""
    traits: list[str] = []
    family: dict[str, list[str]] = _empty_family()
    try:
        if which == "bhardwaj":
            from vedic_bhardwaj_report import BhardwajChart, _load_book
            from bhardwaj_semantic import build_chart_signals as build
            chart = BhardwajChart(pc, _load_book())
        else:
            from vedic_mehta_report import _load_book
            from mehta_chart import MehtaChart
            from mehta_semantic import build_mehta_signals as build
            chart = MehtaChart(pc, _load_book())
        signals = build(chart, pc) or []
    except Exception:  # noqa: BLE001
        return traits, family

    for sig in signals:
        text = str(getattr(sig, "text", "") or getattr(sig, "anchor", "") or "")
        if not text:
            continue
        if str(getattr(sig, "domain", "") or "").lower() == "personality":
            traits += _safe_sentences(text, trait=True)
        _merge_family(family, _route_family(text))
    return traits, family


def build_personal_life(
    pc: dict,
    *,
    dob: Any = None,
    gender: str = "",
) -> tuple[list[str], list[FamilyNoteFact]]:
    """Return extra personality trait lines plus per-relation family notes.

    ``method_count`` on each note records how many independent engines said
    something usable about that relation. It is the only confluence claim this
    module makes, and the prose layer needs it to know when a family line is
    worth stating with any confidence.
    """
    if not isinstance(pc, dict):
        return [], []
    dob_date: date | None = None
    if isinstance(dob, date):
        dob_date = dob
    else:
        raw = str(dob or (pc.get("meta") or {}).get("dob") or "")[:10]
        try:
            dob_date = date.fromisoformat(raw)
        except ValueError:
            dob_date = None
    female = str(gender or "").strip().lower().startswith("f")

    traits: list[str] = []
    family: dict[str, list[str]] = _empty_family()
    counts: dict[str, int] = {relation: 0 for relation in _RELATIONS}

    for collect in (
        lambda: _blind(pc, dob_date, female),
        lambda: _bnn(pc),
        lambda: _signals(pc, "bhardwaj"),
        lambda: _signals(pc, "mehta"),
    ):
        try:
            t, f = collect()
        except Exception:  # noqa: BLE001
            continue
        traits += t
        for relation, lines in f.items():
            if lines:
                counts[relation] += 1
                family[relation] += lines

    notes: list[FamilyNoteFact] = []
    for relation in _RELATIONS:
        lines = _dedupe(family[relation], 3)
        tags = sorted({tag for line in family[relation] for tag in _tags_for(line)})
        if not lines and not tags:
            continue
        notes.append(FamilyNoteFact(
            relation=relation,                               # type: ignore[arg-type]
            label=_RELATION_LABELS[relation],
            tags=tags[:6],
            notes=lines,
            method_count=counts[relation],
        ))
    return _dedupe(traits, 6), notes[:4]
