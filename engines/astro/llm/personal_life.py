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
                # Fixed script ("Your father reads as principled...", "you are the
                # youngest") that does not change with the chart: not evidence.
                continue
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


_CLASSIC_SKIP = re.compile(
    r"(?:"
    r"\bluckless\b"
    r"|\bdebt-ridden\b"
    r"|\bhurt by fire\b"
    r"|\birreligious\b"
    r"|\bsuffering from enemies\b"
    r"|\barrogant\b"
    r"|\bphlegm\b"
    r"|\bpainful for\b"
    r"|\bfree from enemies, wealthy, rich\b"
    r"|\bfamous, dreamer\b"
    r"|\bher mother suffers\b"
    r"|\bhis mother suffers\b"
    r"|\bobstructing children.s happiness\b"
    r"|\bcapable of destroying enemies\b"
    r"|\bFather.s happiness will be less\b"
    r"|\bin the \d+(?:st|nd|rd|th) year\b"
    r"|\bblessed with son\b"
    r"|\brenouncing ancestral property\b"
    r"|\bweak and afflicted\b"
    r"|\bspeaking of mind\b"
    r"|\bloss of above mentioned areas\b"
    r"|\btask contemplated in the mind\b"
    r"|\bcomplete the task contemplated\b"
    r"|\bwill trouble the mother\b"
    r"|\brise through a woman\b"
    r")",
    re.I,
)


def _clean_classical_line(raw_text: str, *, relation: str = "") -> list[str]:
    """Clean classical book predictions into coherent sentences for LLM rephrase.

    Fixes:
    - Sanskrit lord names -> plain English
    - Archaic gender pronouns ('he', 'his') -> neutral 'they'/'their'
    - 'the native' -> 'the person'
    - 'landlord' -> 'property owner'
    - 'more trips' -> 'more travels and journeys'
    - 'royal servant' -> 'respected in authority'
    - Bad grammar from naive substitution ('you is', 'fate of you') fixed
    - Negative/morbid predictions stripped
    """
    if not raw_text:
        return []
    clean = re.sub(r"<[^>]+>", " ", str(raw_text))
    # Sanskrit house lord names
    clean = re.sub(r"\bLagnesh\b", "First house lord", clean, flags=re.I)
    clean = re.sub(r"\bDhanesh\b", "Second house lord", clean, flags=re.I)
    clean = re.sub(r"\bSahajesh\b", "Third house lord", clean, flags=re.I)
    clean = re.sub(r"\bSukhesh\b", "Fourth house lord", clean, flags=re.I)
    clean = re.sub(r"\bPutresh\b", "Fifth house lord", clean, flags=re.I)
    clean = re.sub(r"\bRipuesh\b", "Sixth house lord", clean, flags=re.I)
    clean = re.sub(r"\bYuvatesh\b", "Seventh house lord", clean, flags=re.I)
    clean = re.sub(r"\bRandhresh\b", "Eighth house lord", clean, flags=re.I)
    clean = re.sub(r"\bNavmesh\b", "Ninth house lord", clean, flags=re.I)
    clean = re.sub(r"\bKarmesh\b", "Tenth house lord", clean, flags=re.I)
    clean = re.sub(r"\bLabhesh\b", "Eleventh house lord", clean, flags=re.I)
    clean = re.sub(r"\bVyayesh\b", "Twelfth house lord", clean, flags=re.I)
    # Archaic phrases
    clean = re.sub(r"\blandlord\b", "property owner", clean, flags=re.I)
    clean = re.sub(r"\broyal servant\b", "respected in authority", clean, flags=re.I)
    clean = re.sub(r"\bmore trips\b", "more travels and journeys", clean, flags=re.I)
    clean = re.sub(r"\bDiety\b|\bDeity\b", "elders", clean, flags=re.I)
    clean = re.sub(r"\bBrahmins\b", "learned people", clean, flags=re.I)
    clean = re.sub(r"\baquatic goods\b", "trade and commerce", clean, flags=re.I)
    clean = re.sub(r"\bphlegm\b", "health issues", clean, flags=re.I)
    # 'The native' / 'native'
    clean = re.sub(r"\bthe native\b", "the person", clean, flags=re.I)
    clean = re.sub(r"\bnative\b", "person", clean, flags=re.I)
    # Gendered pronouns from book text — replace with neutral
    # But only when relation context is clear; otherwise keep 'they'
    if relation in ("father", "siblings"):
        # 'He will' -> 'They will', 'His' -> 'Their', 'his' -> 'their'
        clean = re.sub(r"\bHe will\b", "They will", clean)
        clean = re.sub(r"\bhe will\b", "they will", clean)
        clean = re.sub(r"\bHe is\b", "They are", clean)
        clean = re.sub(r"\bhe is\b", "they are", clean)
        clean = re.sub(r"\bHis\b", "Their", clean)
        clean = re.sub(r"\bhis\b", "their", clean)
    elif relation == "mother":
        clean = re.sub(r"\bHe will\b", "She will", clean)
        clean = re.sub(r"\bhe will\b", "she will", clean)
        clean = re.sub(r"\bHis\b", "Her", clean)
        clean = re.sub(r"\bhis\b", "her", clean)
    else:
        clean = re.sub(r"\b[Hh]e will\b", "they will", clean)
        clean = re.sub(r"\b[Hh]is\b", "their", clean)
    # Fix bad grammar from 'you is' (when 'native' -> 'you' + 'is')
    clean = re.sub(r"\byou is\b", "you are", clean, flags=re.I)
    # Fix 'The fate of the person will' -> relation-appropriate phrase
    clean = re.sub(r"\bThe fate of the person will\b", "Their fortune will", clean, flags=re.I)
    clean = re.sub(r"\bfate of the person\b", "their fortune", clean, flags=re.I)
    # Fix 'The fate of you' -> 'Your fortune'
    clean = re.sub(r"\bThe fate of you will\b", "Your fortune will", clean, flags=re.I)
    clean = re.sub(r"\bfate of you\b", "your fortune", clean, flags=re.I)
    # Reframe native-centric predictions as relation-centric descriptions.
    # The classical book says 'The person will be a property owner...' about the
    # NATIVE; for the Mother/Father/Siblings slots we need the sentence to name
    # the relation so _family_prose doesn't prepend a duplicate opener and the
    # sanitizer doesn't then strip the whole block.
    _RELATION_LABELS_MAP = {
        "mother": "Your mother",
        "father": "Your father",
        "siblings": "Your siblings",
        "home": "The family home",
    }
    if relation in _RELATION_LABELS_MAP:
        label = _RELATION_LABELS_MAP[relation]
        clean = re.sub(r"\bThe person will be\b", f"{label} is", clean, flags=re.I)
        clean = re.sub(r"\bThe person is\b", f"{label} is", clean, flags=re.I)
        clean = re.sub(r"\bThe person\b", label, clean, flags=re.I)
        clean = re.sub(r"\bthe person\b", label.lower(), clean, flags=re.I)
        # Also replace pronouns that now refer to the relation
        if relation == "mother":
            clean = re.sub(r"\bshe will be\b", f"{label} is", clean, flags=re.I)
        elif relation in ("father", "siblings"):
            clean = re.sub(r"\bthey will be\b", f"{label} is", clean, flags=re.I)
    # Improve awkward phrases
    clean = re.sub(r"\bgentleman\b", "principled person", clean, flags=re.I)
    clean = re.sub(r"\bcultivator\b", "nurturing by nature", clean, flags=re.I)
    clean = re.sub(r"\bmerchant of trade and commerce\b", "connected to commerce and trade", clean, flags=re.I)
    clean = re.sub(r"\bself-acquired money\b", "self-made prosperity", clean, flags=re.I)
    clean = re.sub(r"\bvehicle and house\b", "comforts of home and travel", clean, flags=re.I)
    clean = re.sub(r"\bbest property and vehicles\b", "property and financial stability", clean, flags=re.I)
    clean = re.sub(r"\broyal favour\b", "recognition and favour from those in power", clean, flags=re.I)
    clean = re.sub(r"\bIf moon is in the variable sign[^.]*\.", "", clean, flags=re.I)
    # Remove parentheticals and normalise whitespace
    clean = _PARENTHETICAL.sub("", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    out: list[str] = []
    for s in _SENTENCE_SPLIT.split(clean):
        st = s.strip(" -\u2013\u2014|.,;")
        if len(st) < 20 or len(st) > 300 or len(st.split()) < 4:
            continue
        # Drop strongly negative / morbid lines
        if _CLASSIC_SKIP.search(st):
            continue
        if not st.endswith((".", "!", "?")):
            st += "."
        out.append(st[0].upper() + st[1:])
    return out



def _classical_report(pc: dict) -> tuple[list[str], dict[str, list[str]]]:
    """Rich classical predictions for personality (self), father, mother, siblings, and home/house."""
    traits: list[str] = []
    family: dict[str, list[str]] = _empty_family()
    if not isinstance(pc, dict):
        return traits, family
    try:
        from vedic_bhardwaj_report import BhardwajChart, _load_book
        from bhardwaj_prose import LAGNA_HUMAN, NAKSHATRA_SNIPPETS, YOGA_HUMAN
        book = _load_book()
    except Exception:
        return traits, family

    meta = dict(pc.get("meta") or {})
    lagna_sign = meta.get("lagna_sign") or (pc.get("lagna") or {}).get("sign") or "Aries"
    meta["lagna_sign"] = lagna_sign
    meta["client"] = meta.get("client") or "Seeker"
    if "age" not in meta:
        meta["age"] = 30

    pc_safe = dict(pc)
    pc_safe["meta"] = meta
    if "vimshottari" not in pc_safe:
        pc_safe["vimshottari"] = {"current_md": {}, "current_md_antardashas": []}

    try:
        chart = BhardwajChart(pc_safe, book)
    except Exception:
        return traits, family

    # 1. Personality / Self
    lagna_txt = LAGNA_HUMAN.get(chart.lagna, "")
    if lagna_txt:
        traits.extend(_clean_classical_line(lagna_txt))
    star_txt = NAKSHATRA_SNIPPETS.get(chart.moon_nak, "")
    if star_txt:
        traits.extend(_clean_classical_line(star_txt))
    for yoga in chart.detect_yogas():
        yname = yoga.get("name", "")
        if yname in YOGA_HUMAN:
            traits.extend(_clean_classical_line(YOGA_HUMAN[yname]))
        elif yoga.get("result"):
            traits.extend(_clean_classical_line(yoga["result"]))


    hlh = book.get("house_lord_in_house", {})
    # Family lines are built from the chart's own significators in
    # _divisional_family (chart_lines.family_notes); nothing canned lives here.

    return traits, family


def _divisional_family(pc: dict) -> tuple[list[str], dict[str, list[str]]]:
    """Family lines graded from the chart's significators (see chart_lines).

    This used to print the same claim for every chart ("a strong paternal
    heritage of discipline...") and vary only the house number. The claim now
    follows the strength of the indicators, so a strained chart reads strained.
    """
    traits: list[str] = []
    family: dict[str, list[str]] = _empty_family()
    if not isinstance(pc, dict):
        return traits, family
    try:
        import chart_lines as CL
        for relation, lines in CL.family_notes(pc).items():
            family[relation] += lines
    except Exception:  # noqa: BLE001
        pass
    return traits, family
    divisional = pc.get("divisional") or {}
    d12 = divisional.get("D12") or {}
    d3 = divisional.get("D3") or {}
    d4 = divisional.get("D4") or {}

    _ZODIAC = (
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    )

    def _varga_pos(vdata: dict, planet: str) -> tuple[str, int]:
        ls = vdata.get("Lagna") or ""
        ps = vdata.get(planet) or ""
        if ls not in _ZODIAC or ps not in _ZODIAC:
            return ps, 0
        return ps, ((_ZODIAC.index(ps) - _ZODIAC.index(ls)) % 12) + 1

    # D12 Father & Mother (Dwadashamsha)
    d12_sun_sign, d12_sun_h = _varga_pos(d12, "Sun")
    if d12_sun_h:
        family["father"].append(
            f"Dwadashamsha (D12) places the Sun in {d12_sun_sign} in the {d12_sun_h} house, indicating a strong paternal heritage of discipline, traditional values, and structured guidance."
        )
        family["father"].append(
            "Paternal lineage emphasizes duty, ethical principles, and respect for ancestral traditions."
        )

    d12_moon_sign, d12_moon_h = _varga_pos(d12, "Moon")
    if d12_moon_h:
        family["mother"].append(
            f"Dwadashamsha (D12) places the Moon in {d12_moon_sign} in the {d12_moon_h} house, reflecting maternal grounding, emotional resilience, and deep ancestral care."
        )
        family["mother"].append(
            "Maternal influence provides an emotional anchor and moral stability in early life."
        )

    # D3 Siblings (Drekkana)
    d3_mars_sign, d3_mars_h = _varga_pos(d3, "Mars")
    d3_jup_sign, d3_jup_h = _varga_pos(d3, "Jupiter")
    if d3_jup_h == 3:
        family["siblings"].append(
            f"Drekkana (D3) places Jupiter in the 3rd house in {d3_jup_sign}, indicating supportive co-born bonds, shared learning, and mutual respect."
        )
    elif d3_mars_h:
        family["siblings"].append(
            f"Drekkana (D3) shows active, independent siblings where mutual patience and clear communication keep relationships harmonious."
        )

    # D4 Home & Property (Chaturthamsha)
    d4_moon_sign, d4_moon_h = _varga_pos(d4, "Moon")
    if d4_moon_h:
        family["home"].append(
            f"Chaturthamsha (D4) places the Moon in {d4_moon_sign} in the {d4_moon_h} house, supporting long-term domestic comfort and steady property accumulation."
        )
    family["home"].append(
        "Domestic life is grounded in creating a peaceful, organized household environment."
    )

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
        lambda: _classical_report(pc),
        lambda: _divisional_family(pc),
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
    return _dedupe(traits, 8), notes[:4]

