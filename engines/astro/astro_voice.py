#!/usr/bin/env python3
"""
astro_voice.py — makes every report read as if it were written for one person.

Three jobs:

  1. STRIP  — remove developer leakage from user-facing HTML
              ("Rebuild: python3 build_jaimini_data.py", "Deterministic rule
              engine", debug notes). A paying customer should never see the
              machinery, and never be told the reading is mechanical.

  2. HUMANISE — third person → second person ("the native" → "you"), soften
              jargon, and open every report with a paragraph that names the
              reader and cites specifics only THEIR chart could produce.

  3. VARY   — phrasing variants are picked from a hash of the person's own
              chart, so two people never receive the same sentence shapes while
              the same person always gets a stable report.

Deterministic by default. If you want an extra layer of polish, set
ASTRO_LLM_KEY (any OpenAI-compatible endpoint) and each opening is rewritten
by the model with the chart facts supplied as grounding — see llm_polish().
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from datetime import date
from typing import Any, Optional

# ---------------------------------------------------------------------------
# 1. Developer leakage — never show the machinery
# ---------------------------------------------------------------------------
STRIP_PATTERNS = [
    r"<p class=['\"]fine['\"]>\s*Rebuild:.*?</p>",
    r"Rebuild:\s*<code>[^<]*</code>",
    r"<code>python3?[^<]*</code>",
    r"\bDeterministic rule engine\b",
    r"\bdeterministic rule engine\b",
    r"\bno[- ]LLM\b", r"\bNO[- ]LLM\b", r"\bwithout an LLM\b",
    r"\bMiniLM\b", r"\bminilm\b", r"\bsentence[- ]transformers?\b",
    r"\blexical fallback\b",
    r"\brule-based\b", r"\bhard-coded\b", r"\bheuristic(ally)?\b",
    r"\bfallback template\b", r"\btemplate line\b",
    r"\bDeterministic Python engine\b",
    r"\bComputed with Python\b[^.]*\.?",
    # internal calibration notes: honest engineering, but they read to a paying
    # customer as "we didn't really do the work"
    r"⚠\s*Uncalibrated[^<]*",
    r"<[^>]*>\s*⚠\s*Uncalibrated.*?</[^>]+>",
    r"\bfirst pass\b[^<]{0,120}",
    r"life-event dates were not supplied[^<]*",
]

# ---------------------------------------------------------------------------
# 1a. Leaks — machinery that escaped into the customer's copy
# ---------------------------------------------------------------------------
# Found by auditing the real report set, not imagined. Each entry is
# (pattern, replacement): a replacement rather than a deletion wherever the
# surrounding sentence still has something true to say, because a half-deleted
# sentence reads worse than the leak did.
#
# None of these carry a fact. They are paths, ids, build instructions and
# advice to go use somebody else's astrology software.
LEAK_STRIPS: list[tuple[str, str]] = [
    # <dt>Source</dt><dd><code>precomputed:/home/oppo/.../input/ritxx</code></dd>
    # — a full filesystem path and session UUID, printed in the header of the
    # KP and BNN reports where the customer reads it first.
    (r"<dt>\s*Source\s*</dt>\s*<dd>.*?</dd>", ""),
    (r"\bSource\s+precomputed:[^\s<]*", ""),
    (r"precomputed:(?:/[\w.\-]+)+/?", ""),
    (r"(?:^|(?<=[\s:=(\"']))/(?:[\w.\-]+/){2,}[\w.\-]+", ""),
    (r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", ""),

    # "Rebuild corpus: python3 build_bhardwaj_data.py" — build instructions for
    # a corpus the customer will never rebuild.
    (r"\s*(?:Rebuild(?:\s+corpus)?:\s*)?<code>\s*python3?[^<]*</code>\.?", ""),
    (r"\s*Rebuild(?:\s+corpus)?:\s*python3?\s+[\w.]+\.py\.?", ""),
    (r"\s*Engine:\s*\+?\s*[\w\s]*?\d*\.\s*(?=</p>|$)", ""),
    # Internal model / script names must never reach a paying customer.
    (r"\bWe read your question with MiniLM,?\s*", "We read your question, "),
    (r"\b(?:with\s+)?MiniLM\b,?\s*", ""),
    (r"\bminilm\b,?\s*", ""),
    (r"\bsentence[- ]transformers?\b,?\s*", ""),
    (r"\blexical fallback\b,?\s*", ""),
    (r"\bDeterministic Python engine(?:\s*\(no LLM\))?", ""),
    (r"Computed with Python\s+[\w.]+(?:\s*\([^)]*\))?(?:\s*[—\-]\s*)?",
     "Computed from the ephemeris"),
    (r"<code>\s*[\w./\-]+\.py\s*</code>", ""),
    (r"\bpython3?\s+[\w./\-]+\.py\b", ""),
    (r"\b[\w./\-]+\.py\b", ""),

    # "the plain-language version for the client is user_report_ritxx.html"
    (r"\s*This is the analyst view\s*—\s*the plain-language version for the "
     r"client is\s*<em>[^<]*</em>\.?", ""),
    (r"\s*the plain-language version for the client is[^.<]*\.?", ""),
    (r"\b\w+_(?:ritxx|ritz|sample|test)\w*\.(?:html|json|csv|png)\b", ""),

    # "cross-check in your software" — the customer has no software. They paid
    # for this to BE the software. Replaced, not deleted: the surrounding line
    # is telling them where the dates come from, which is worth keeping.
    (r"cross[- ]check\s+important\s+dates\s+in\s+your\s+software",
     "each date below is computed from your own chart"),
    (r"cross[- ]check\s+in\s+your\s+software",
     "computed directly from your own chart"),
    (r"cross[- ]check\s+(?:these|the)\s+[\w\s]{0,20}in\s+your\s+software",
     "computed directly from your own chart"),
    (r"from your extract\s*[-—]\s*", "— "),
    (r"\bfrom your (?:Vimshottari )?extract\b", "from your chart"),

    # placeholder identity: the internal handle used while testing
    (r"<dt>\s*Client\s*</dt>\s*<dd>\s*(?:ritxx|ritz|sample|test)\s*</dd>", ""),

    # 'The handbook tale "Intricacies of Karma: The Goldsmith's Journey" is
    # metaphorical folklore, not literal history.' — found in the KVS and KP
    # lanes on 7 of 7 charts in the lane sweep. It names a source book, quotes a
    # chapter title, and then apologises for it, all in the reader's own
    # reading. The sentences AFTER it carry the actual meaning ("the story turns
    # on trust and betrayal…"), so only the framing sentence goes.
    (r"\s*The\s+handbook\s+tale\s*“[^”]*”\s*is\s+metaphorical\s+"
     r"folklore,?\s*not\s+literal\s+history\.?", ""),
    (r"\s*The\s+handbook\s+tale\s*\"[^\"]*\"\s*is\s+metaphorical\s+folklore,?"
     r"\s*not\s+literal\s+history\.?", ""),
    (r"\s*The\s+handbook\s+(?:tale|story)\s*[“\"][^”\"]*[”\"]\s*",
     " The old story "),
    # Rewrite only the NOUN, leaving the article untouched, so the original
    # capitalisation survives: "The handbook says" -> "The tradition holds",
    # "the handbook" -> "the tradition". Matching "The handbook" as a unit does
    # not work here because these patterns are applied with re.I, so a
    # capitalised variant also matches lower-case text and forces a capital
    # into the middle of a sentence.
    (r"\bhandbook\s+(?:says|notes|states|records)\b", "tradition holds"),
    (r"\bhandbook\b", "tradition"),

    # "Book OCR longevity scan finds no strict…" — the customer does not need to
    # know a book was scanned, and strip_citations only removed the "OCR",
    # leaving the equally revealing "Book … scan".
    (r"\bBook\s+OCR\s+(\w+)\s+scan\b", r"chart \1 check"),
    (r"\bBook\s+OCR\b", "chart"),
    (r"\bOCR\s+(?:scan|pass|extract)\b", "chart check"),
]


def leak_removals(html: str) -> list[str]:
    """The fact tokens that stripping leaks legitimately takes with it.

    Deleting a session UUID deletes digits; deleting "Engine: Vedic Confluence
    2" deletes a 2. Those are machinery, not the customer's facts — but the
    guard cannot know that, and a guard you routinely override is a guard you
    have switched off.

    So the declaration is computed, not asserted: only tokens found *inside the
    spans the leak patterns actually matched* are exempt. Anything else that
    disappears is still a failure. On the first run over the real report set
    this caught a pattern of mine that was eating one digit too many.
    """
    try:
        from report_fact_guard import facts
    except ImportError:      # guard is a dev-time tool; never break a report
        return []
    # Patterns are applied in sequence and later ones match text the earlier
    # ones produced, so the declaration has to walk the same sequence. Scanning
    # all patterns against the original HTML misses exactly those cascades —
    # which is how the Bhardwaj "Engine: … 2." removal stayed undeclared.
    declared: list[str] = []
    stage = html
    for pat, rep in LEAK_STRIPS:
        for m in re.finditer(pat, stage, flags=re.S | re.I):
            before = facts(m.group(0), ignore_leaks=False).counts
            after = facts(re.sub(pat, rep, m.group(0), flags=re.S | re.I),
                          ignore_leaks=False).counts
            for key, n in (before - after).items():
                declared.extend([key] * n)
        stage = re.sub(pat, rep, stage, flags=re.S | re.I)
    return declared


def strip_leaks(html: str) -> str:
    """Remove machinery that escaped into the customer's copy.

    Runs before every other voice stage: there is no point polishing the tone
    of a paragraph that ends in a session UUID.
    """
    out = html
    for pat, rep in LEAK_STRIPS:
        out = re.sub(pat, rep, out, flags=re.S | re.I)
    # a <dl> or <p> emptied by the strips above should not leave a gap
    out = re.sub(r"<p[^>]*>\s*[.·—-]?\s*</p>", "", out)
    out = re.sub(r"<code>\s*</code>", "", out)
    # Empty () left after a leak deletion — never touch <script>/<style>, or
    # report interact JS becomes `function{` / `showMismatch;` and pills die.
    out = _outside_script_style(out, lambda t: re.sub(r"\(\s*\)", "", t))
    out = re.sub(r"[ \t]{2,}", " ", out)
    return out

# ---------------------------------------------------------------------------
# 1b. Jargon — say it in English, keep the Sanskrit as provenance
# ---------------------------------------------------------------------------
# The audit counted 2,266 untranslated terms across the report set: `lagna`
# 923 times, `antardasha` 274, `bindu` 148. Every one of them is a moment where
# the reader stops being told about themselves and starts reading someone
# else's shop-talk.
#
# The terms are translated, not deleted. Deleting them would cost the reading
# its authority — the Sanskrit is *why* this looks like real astrology rather
# than a horoscope column. So the plain word is what you read, and the original
# survives as a tooltip: "rising sign" that reveals "Lagna" on hover.
#
# Ordered longest-first: `antardasha` must be consumed before `dasha`, and
# `lagna lord` before `lagna`, or the short form eats the long one's stem.
JARGON_TERMS: list[tuple[str, str]] = [
    # timing vocabulary — the single biggest source of confusion
    ("md-ad", "main and sub-period"),
    ("mahadasa-antardasa", "main and sub-period"),
    ("pratyantardasha", "micro-period"),
    ("pratyantardasa", "micro-period"),
    ("pratyantar", "micro-period"),
    ("antardasha", "sub-period"),
    ("antardasa", "sub-period"),
    ("antar dasha", "sub-period"),
    ("mahadasha", "main period"),
    ("mahadasa", "main period"),
    ("maha dasha", "main period"),
    ("vimshottari", "the main timing cycle"),
    ("yogini dasha", "the lunar timing cycle"),
    ("chara dasha", "the sign-based timing cycle"),
    ("antar", "sub-period"),
    ("dasha", "period"),
    ("dasa", "period"),
    ("vargas", "divisional charts"),
    ("varga", "divisional chart"),
    ("neutral_sign", "neither strong nor weak"),
    ("own_sign", "in its own sign"),
    ("enemy_sign", "under strain"),
    ("friendly_sign", "comfortably placed"),
    ("moolatrikona", "in its best sign"),
    ("Maha-lord", "main period lord"),
    ("Antar-lord", "sub-period lord"),
    ("Chara-lord", "sign-based period lord"),
    ("Yogini-lord", "lunar cycle lord"),
    ("BAV", "transit score"),
    ("SAV", "house score"),
    ("bindu", "support point"),
    ("bindus", "support points"),

    # chart anatomy
    ("lagna lord", "ruler of your rising sign"),
    ("lagnesha", "ruler of your rising sign"),
    ("ascendant lord", "ruler of your rising sign"),
    ("lagna", "rising sign"),
    ("bhava", "house"),
    ("graha", "planet"),
    ("rashi", "sign"),
    ("rasi", "sign"),
    ("navamsha", "the marriage chart"),
    ("dashamsha", "the career chart"),
    ("saptamsha", "the children chart"),
    ("drekkana", "the siblings chart"),

    # house families
    ("kendra houses", "the four pillar houses"),
    ("trikona houses", "the three fortune houses"),
    ("dusthana houses", "the three pressure houses"),
    ("upachaya houses", "the growth houses"),
    ("trishadaya lords", "effort-house rulers"),
    ("trishadaya", "effort houses"),
    ("raja yoga", "power combination"),
    ("kendra", "pillar house"),
    ("trikona", "fortune house"),
    ("dusthana", "pressure house"),
    ("upachaya", "growth house"),

    # scoring vocabulary
    ("ashtakavarga", "the transit scoring system"),
    ("bindus", "points"),
    ("bindu", "point"),
    ("sav", "sign score"),
    ("bav", "planet score"),

    # the karakas
    ("atmakaraka", "your defining planet"),
    ("karaka", "natural significator"),
    ("argala", "planetary intervention"),
    ("bindu", "support point"),
    ("amatyakaraka", "your career indicator"),
    ("bhratrikaraka", "your sibling indicator"),
    ("matrikaraka", "your mother indicator"),
    ("putrakaraka", "your children indicator"),
    ("gnatikaraka", "your obstacle indicator"),
    ("darakaraka", "your spouse indicator"),

    # misc
    ("ayanamsa", "zodiac alignment"),
    ("ayanāṃśa", "zodiac alignment"),
    ("yoga", "combination"),
    ("swakshetra", "in its own sign"),
    ("moolatrikona", "in its best sign"),
    ("vakri", "retrograde"),
]

# Table headers use three-letter method tags the reader has no key for.
JARGON_TABLE = [
    ("Vim:", "Main cycle:"),
    ("Jai:", "Sign cycle:"),
    ("Yog:", "Lunar cycle:"),
    ("AK ", "Defining planet "),
    # the rest of the karaka shorthand, which the karaka lane writes inline
    ("AmK ", "Career indicator "),
    ("BK ", "Sibling indicator "),
    ("MK ", "Mother indicator "),
    ("PiK ", "Father indicator "),
    ("PK ", "Children indicator "),
    ("GK ", "Obstacle indicator "),
    ("DK ", "Spouse indicator "),
    ("CSL-", "Sub-lord "),
    ("CSL ", "cusp sub-lord "),
]

# Nodes whose text is markup, code or already-translated tooltip content.
_PROTECTED = re.compile(
    r"<(script|style|code|pre|abbr)\b[^>]*>.*?</\1>", re.S | re.I)


def _outside_script_style(html: str, fn) -> str:
    """Apply fn only outside <script> / <style> blocks (keep them byte-identical)."""
    guard = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.S | re.I)
    out: list[str] = []
    pos = 0
    for block in guard.finditer(html):
        out.append(fn(html[pos:block.start()]))
        out.append(block.group(0))
        pos = block.end()
    out.append(fn(html[pos:]))
    return "".join(out)


def _map_text_nodes(html: str, fn) -> str:
    """Apply `fn` to visible text only — never inside a tag or a code block.

    A blunt re.sub over the whole document would rewrite class names, `title`
    attributes and anything inside <code>, producing broken markup that looks
    fine until a specific report renders.
    """
    out: list[str] = []
    pos = 0
    for block in _PROTECTED.finditer(html):
        out.append(_map_outside_tags(html[pos:block.start()], fn))
        out.append(block.group(0))
        pos = block.end()
    out.append(_map_outside_tags(html[pos:], fn))
    return "".join(out)


def _map_outside_tags(chunk: str, fn) -> str:
    parts = re.split(r"(<[^>]+>)", chunk)
    return "".join(p if p.startswith("<") else fn(p) for p in parts)


_FAMILY = {"kendra": "pillar", "trikona": "fortune",
           "dusthana": "pressure", "upachaya": "growth"}
_FAMILY_RE = re.compile(
    r"\b(kendra|trikona|dusthana|upachaya)"
    r"(?:\s*/\s*(kendra|trikona|dusthana|upachaya))?\s+"
    r"(\d{1,2})(st|nd|rd|th)\b", re.I)


def _house_families(text: str) -> str:
    """"kendra/trikona 10th" → "the 10th house (a pillar and fortune house)".

    Word-for-word substitution produces "pillar house / fortune house 10th",
    which is not English. House families need the whole phrase rebuilt.
    """
    def sub(m: re.Match) -> str:
        names = [_FAMILY[m[1].lower()]]
        if m[2]:
            names.append(_FAMILY[m[2].lower()])
        joined = " and ".join(names)
        return f"the {m[3]}{m[4]} house (a {joined} house)"
    return _FAMILY_RE.sub(sub, text)


def translate_jargon(html: str, *, keep_original: bool = True) -> str:
    """Sanskrit and method shorthand → plain English, provenance preserved.

    One pass, one combined pattern. Applying the terms in a loop meant each
    substitution's output was re-scanned by every later term, so the <abbr>
    wrapper inserted for "varga" got chewed up by the rule for "vargas" and
    emitted `divisional chart ">divisional charts`. A single alternation,
    longest-first, makes replacement text untouchable by construction.
    """
    lookup = {term.lower(): plain for term, plain in JARGON_TERMS}
    alternation = "|".join(
        re.escape(term) for term, _ in
        sorted(JARGON_TERMS, key=lambda kv: -len(kv[0])))
    pattern = re.compile(rf"\b({alternation})(s?)\b", re.I)

    def convert(text: str) -> str:
        text = _house_families(text)

        def sub(m: re.Match) -> str:
            original = m.group(0)
            plain = lookup[m.group(1).lower()]
            # Capitalise from POSITION, not from the source term. Copying the
            # source's capital gave "lords in The marriage chart", because the
            # corpus writes "Navamsha" as a proper noun and the plain-English
            # rendering is not one.
            before = text[:m.start()].rstrip()
            if (not before) or before[-1] in ".!?:>":
                plain = plain[:1].upper() + plain[1:]
            if not keep_original:
                return plain
            return (f'<abbr class="jargon" title="{original.strip()}">'
                    f'{plain}</abbr>')

        text = pattern.sub(sub, text)
        for tag, plain in JARGON_TABLE:
            text = text.replace(tag, plain)
        return text

    return _map_text_nodes(html, convert)


# ---------------------------------------------------------------------------
# 1c. Analyst voice → customer voice
# ---------------------------------------------------------------------------
# These reports were built for an astrologer to read before a consultation, and
# the framing still says so: "Technical confluence", "Methods read: 15",
# "Running clock", "votes reconcile". None of it is wrong; all of it puts the
# reader outside the reading, looking at the apparatus.
#
# The benchmark cuts both ways. AstroSage never shows machinery — but its copy
# is undated and interchangeable ("As you are born on Wednesday, you'll have an
# attractive face and features"): every reader with that weekday gets the same
# sentence. Our advantage is specificity — real dates, real disagreement between
# methods, real confidence levels. So the goal is not to hide the rigour, it is
# to state it as something the reader OWNS rather than something we performed.
#
# Facts are untouched here: no number, date or verdict appears in any
# replacement that was not in the original.
REPHRASE: list[tuple[str, str]] = [
    (r"<strong>Technical confluence\.</strong>\s*(\d+) independent techniques "
     r"were read and cross-checked\.\s*Where several agree, confidence rises\.",
     r"<strong>Your chart, read \1 different ways.</strong> Each method works "
     r"from your birth details alone and reaches its own conclusion. Where "
     r"they land on the same answer, you can act on it — and this report "
     r"shows you exactly where they agree and where they do not."),
    (r"\bTechnical confluence\b", "How your chart was read"),
    (r"\bMethods read\b", "Ways your chart was read"),
    (r"\bAll systems cross-checked · one reconciled answer\b",
     "Every method, reconciled into one answer"),
    (r"Each specialist sub-report \(([^)]*)\) contributes statements about "
     r"your life\.\s*Statements that mean the same thing are grouped, and when "
     r"several independent methods agree the confluence verdict gains "
     r"confidence\.\s*Each life-area table below shows exactly which method "
     r"said what, and how the votes reconcile\.",
     r"Your chart was read separately by \1 — each one a complete method in "
     r"its own right. Where they say the same thing in different words, that "
     r"agreement is what makes a finding trustworthy. Every section below "
     r"shows you which methods spoke and whether they agreed."),
    (r"Live Chart Techniques \(Main Question Engine\)",
     "Your question, answered technique by technique"),
    (r"\bMain Question Engine\b", "your question"),
    (r"\bLive Chart Techniques\b", "What the live chart shows"),
    (r"\bthe confluence verdict\b", "the combined answer"),
    (r"\bConfluence verdict\b", "Combined answer"),
    (r"\bconfluence verdict\b", "combined answer"),
    (r"\bRunning clock:", "Where you are right now:"),
    (r"\bNext dasha windows\b", "What is coming next"),
    (r"\bChart activation\b", "What this period switches on"),
    (r"\bLinked houses:", "This also touches:"),
    (r"\bhow the votes reconcile\b", "how they compare"),
    (r"\bvote\b", "verdict"),
    (r"\bComputed independently from your birth chart\.",
     "Worked out from your birth details alone."),
    (r"\bFor guidance, not a substitute for a personal consultation\.",
     "Guidance, not a replacement for sitting down with someone."),
    (r"\bEducational astrology only\.", "Offered as guidance."),
    (r"\bthis division of life\b", "this part of your life"),
    (r"\bThis division of life\b", "This part of your life"),
    (r"\bindication\)", "sign)"),
    (r"\bconfirm with\b", "worth checking against"),
]


def rephrase(html: str) -> str:
    """Analyst framing → the reader's own reading."""
    def convert(text: str) -> str:
        for pat, rep in REPHRASE:
            text = re.sub(pat, rep, text)
        return text
    # applied to the whole document, not just text nodes: the first pattern
    # spans a <strong> boundary, which is exactly where the analyst framing sits
    out = html
    for pat, rep in REPHRASE[:1]:
        out = re.sub(pat, rep, out, flags=re.S)
    return _map_text_nodes(out, convert)


# third person / clinical → second person
HUMANISE = [
    (r"\bThe native's\b", "Your"), (r"\bthe native's\b", "your"),
    (r"\bThe native\b", "You"),    (r"\bthe native\b", "you"),
    (r"\bThe querent's\b", "Your"), (r"\bthe querent's\b", "your"),
    (r"\bThe querent\b", "You"),   (r"\bthe querent\b", "you"),
    (r"\byou's\b", "your"),        (r"\bYou's\b", "Your"),
    (r"\bquesited\b", "the matter"), (r"\bQuesited\b", "The matter"),
    (r"\bthe subject\b", "you"),   (r"\bThe subject\b", "You"),
    (r"\bthe client\b", "you"),    (r"\bThe client\b", "You"),
    (r"\bis indicated for the chart holder\b", "shows up for you"),
    (r"\bit is indicated\b", "it shows"),
    (r"\bas per the chart\b", "as your chart has it"),
]


def strip_machinery(html: str) -> str:
    out = html
    for pat in STRIP_PATTERNS:
        out = re.sub(pat, "", out, flags=re.S)
    # tidy empty leftovers
    out = re.sub(r"<p[^>]*>\s*</p>", "", out)
    out = re.sub(r"<details[^>]*>\s*</details>", "", out)
    return out


def humanise(html: str) -> str:
    out = html
    for pat, rep in HUMANISE:
        out = re.sub(pat, rep, out)
    return out


# ---------------------------------------------------------------------------
# 1d. Direct and concise — the reading says it once, in the shortest form
# ---------------------------------------------------------------------------
# The reports earn their length from facts, not from connective tissue. These
# substitutions cut the filler that makes generated prose feel padded — throat-
# clearing openers, wordy phrases, doubled hedging — without touching a number,
# date or verdict. Facts are never rewritten; only the language around them.
# Deterministic, idempotent, and off when CONCISE_REPORTS=0.

# Sentence-leading filler ("It is important to note that…"). Removing it must
# also repair the capital of the word that follows, so it is one pass that
# keeps the sentence-start (or nothing) and uppercases the next letter.
_LEADERS = (
    r"it is important to note that",
    r"it is worth noting that",
    r"it is worth mentioning that",
    r"it should be noted that",
    r"please note that",
    r"it is interesting to note that",
    r"it must be remembered that",
    r"needless to say",
    r"it goes without saying that",
    r"as we all know",
    r"first and foremost",
    r"last but not least",
    r"in conclusion",
    r"to summarize",
)
_LEADER = re.compile(
    r"(^|[.!?]\s+)(?:" + "|".join(_LEADERS) + r")[\s,]*([A-Za-z])", re.I)


def _drop_leader(m: "re.Match[str]") -> str:
    return m.group(1) + m.group(2).upper()


# The palm corpus leans on "there is a possibility of the person undergoing
# surgery". Once personalisation has turned "the person" into "you", the
# phrase can become a direct "you may …" instead of a construction site.
_PALM_GERUNDS = {
    "undergoing": "undergo", "having": "have", "being": "be",
    "getting": "get", "facing": "face", "suffering": "suffer",
    "developing": "develop", "meeting": "meet", "taking": "take",
    "making": "make", "going": "go", "losing": "lose",
    "experiencing": "experience", "falling": "fall",
}
_POSSIBILITY_OF = re.compile(
    r"\bthere is a (?:strong )?possibility of "
    r"(?:you|the person|the native|the subject|one)\s+(\w+)", re.I)

_CONCISE_SUBS: list[tuple["re.Pattern[str]", str]] = [
    # wordy phrases → the short form
    (re.compile(r"\bin order to\b", re.I), "to"),
    (re.compile(r"\bdue to the fact that\b", re.I), "because"),
    (re.compile(r"\bowing to the fact that\b", re.I), "because"),
    (re.compile(r"\bthe reason being that\b", re.I), "because"),
    (re.compile(r"\bin the event that\b", re.I), "if"),
    (re.compile(r"\bwith regard to\b", re.I), "about"),
    (re.compile(r"\bwith respect to\b", re.I), "about"),
    (re.compile(r"\bin relation to\b", re.I), "about"),
    (re.compile(r"\bat this point in time\b", re.I), "now"),
    (re.compile(r"\bat the present time\b", re.I), "now"),
    (re.compile(r"\bat this juncture\b", re.I), "now"),
    (re.compile(r"\bat the current moment\b", re.I), "now"),
    (re.compile(r"\bin the near future\b", re.I), "soon"),
    (re.compile(r"\bin the foreseeable future\b", re.I), "soon"),
    (re.compile(r"\bon a daily basis\b", re.I), "daily"),
    (re.compile(r"\bon a regular basis\b", re.I), "regularly"),
    (re.compile(r"\bon an ongoing basis\b", re.I), "ongoing"),
    (re.compile(r"\bin a timely manner\b", re.I), "on time"),
    (re.compile(r"\ba number of\b", re.I), "several"),
    (re.compile(r"\bfor the purpose of\b", re.I), "for"),
    (re.compile(r"\bas well as\b", re.I), "and"),
    # doubled hedging — one qualifier says it; two say nothing
    (re.compile(r"\bcould potentially\b", re.I), "could"),
    (re.compile(r"\bpotentially could\b", re.I), "could"),
    (re.compile(r"\bmay potentially\b", re.I), "may"),
    (re.compile(r"\bpossibly may\b", re.I), "may"),
    (re.compile(r"\bmight possibly\b", re.I), "might"),
    # Hedged verbs stay hedged: "indicates that" can be the assertive "shows",
    # but "suggests that" is a weaker claim and must not be upgraded to a
    # certainty. We cut the words, never the confidence — the corpus leans on
    # these ("This combination suggests that the native may have had...").
    (re.compile(r"\bpoints to the possibility that\b", re.I), "suggests that"),
    (re.compile(r"\bindicates that\b", re.I), "shows"),
    (re.compile(r"\bsuggests that\b", re.I), "suggests"),
    (re.compile(r"\bseems to indicate\b", re.I), "suggests"),
    (re.compile(r"\bappears to suggest\b", re.I), "suggests"),
    # long words when a short one means the same
    (re.compile(r"\butilize\b", re.I), "use"),
    (re.compile(r"\butilized\b", re.I), "used"),
    (re.compile(r"\butilizing\b", re.I), "using"),
    (re.compile(r"\butilises?\b", re.I), "uses"),
    (re.compile(r"\butili[sz]ation\b", re.I), "use"),
    # "approximately" is only the plain "about" when it quantifies a value
    # ("approximately 2 km"). "families remember approximately" must survive:
    # the word carries the meaning there, and "remember about" is not English.
    (re.compile(r"\bapproximately(?=\s+(?:\d|an? |the |[A-Z]\w*))", re.I), "about"),
    (re.compile(r"\bsubsequently\b", re.I), "then"),
    (re.compile(r"\badditionally\b", re.I), "also"),
    (re.compile(r"\bfurthermore\b", re.I), "also"),
    (re.compile(r"\bmoreover\b", re.I), "also"),
]


def _concise_text(text: str) -> str:
    text = _LEADER.sub(_drop_leader, text)

    def poss(m: "re.Match[str]") -> str:
        base = m.group(1).lower()
        inf = _PALM_GERUNDS.get(base)
        if inf is None:
            # unknown gerund — keep the original wording rather than emit
            # "may traveling". The corpus only emits a handful of gerunds;
            # a miss here must degrade to the safe original, not bad grammar.
            return m.group(0)
        before = text[: m.start()].rstrip()
        out = f"you may {inf}"
        if (not before) or before[-1] in ".!?:>":
            out = out[:1].upper() + out[1:]
        return out

    text = _POSSIBILITY_OF.sub(poss, text)

    for pat, rep in _CONCISE_SUBS:
        def sub(m: "re.Match[str]", r=rep) -> str:
            before = text[: m.start()].rstrip()
            if not r:
                return ""
            out = r
            if out and out[0].isalnum() and out[0].islower():
                if (not before) or before[-1] in ".!?:>":
                    out = out[0].upper() + out[1:]
            return out
        text = pat.sub(sub, text)

    # tidy what the deletions left behind. Deliberately no .strip(): text nodes
    # sit between tags, and stripping would eat the space around an inline
    # <b>/<em> and print "that<b>Venus</b>is".
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\.\s*\.", ".", text)
    return text


def concise(html: str, *, enabled: Optional[bool] = None) -> str:
    """Cut filler and wordiness from the visible prose. Facts untouched.

    Runs over text nodes only — never inside a tag, or <script>/<style>/<code>
    (the jargon tooltips stay intact). The deterministic text is the floor:
    set CONCISE_REPORTS=0 to go back to it without a code change.
    """
    if enabled is None:
        enabled = os.getenv("CONCISE_REPORTS", "1") == "1"
    if not enabled:
        return html
    return _map_text_nodes(html or "", _concise_text)


# ---------------------------------------------------------------------------
# 1b. Citations — the reading must stand on its own
# ---------------------------------------------------------------------------
# A customer is buying a reading of THEIR hand or chart, not a bibliography.
# Book titles, author names and page numbers all come out. Where a source name
# was doing real work (labelling which method spoke), it is replaced with a
# neutral description of the method so the sentence still reads.

# whole sections that exist only to cite sources
CITATION_SECTIONS = (
    "sources", "source", "references", "reference", "bibliography",
    "book precedent", "book reference", "book rule", "citations",
    "supporting book quotes", "developer reference", "audit note",
)

# every book title the palm and astro corpora can emit
BOOK_TITLES = (
    "Apprentice to Pro (24 readings)", "Apprentice to Pro",
    "Modern Case Studies (50)", "Modern Case Studies",
    "50 Case Studies in Modern Palmistry",
    "Easy Understanding of Samudrik", "Palmistry for All",
    "How to Master the Art of Palmistry", "All the Secrets of Palmistry",
    "Practical Handbook Vol. 2 (Marriage)", "Practical Handbook Vol. 1",
    "Practical Handbook Vol. 2", "Practical Handbook",
    "Principles of Self-Learning", "Secrets of Profession & Popularity",
    "Secrets of Profession and Popularity", "Succinct Palmistry",
    "Horary Astrology Plain and Simple",
    "Vedic Astrology - An Integrated Approach",
    "Vedic Astrology An Integrated Approach",
)

# author / commentator names
AUTHORS = (
    "Anthony Louis", "William Lilly", "Bonatus", "Bonatti", "Cheiro",
    "P.V.R. Narasimha Rao", "PVR Narasimha Rao", "Narasimha Rao",
    "B.V. Raman", "BV Raman", "Raman", "Bhardwaj", "Goel", "Mehta",
    "Avasthi", "Woods", "Manley", "Sanjay Rath", "Iranganti Rangacharya",
    "Rangacharya", "Santhanam", "Sharma", "Jha", "Ramachandra Pandey",
    "VP Jain", "V.P. Jain", "Louis", "Lilly",
    "Ravichandran",          # cited by name inside the sub-lord lane's prose
)

# method names that carry a person's name — replaced, not deleted, so the
# sentence still tells the reader which technique spoke
SYSTEM_RENAMES = (
    (r"\bBhrigu Nandi Nadi\b", "the nadi method"),
    (r"\bBNN\b", "the nadi method"),
    (r"\bKrishnamurti Paddhati\b", "the sub-lord method"),
    (r"\bKrishnamurti\b", "the sub-lord method"),
    (r"\bKP horary\b", "sub-lord horary"),
    (r"\bKP\b", "sub-lord"),
    (r"\bJaimini Chara Karakas?\b", "the karaka method"),
    (r"\bJaimini\b", "the karaka method"),
    (r"\bParashari\b", "the classical method"),
    (r"\bParashara\b", "the classical method"),
    (r"\bCheiro's System of Seven(?:\s+timing)?\b", "seven-year timing"),
    (r"\bSystem of Seven(?:\s+timing)?\b", "seven-year timing"),
    (r"\bTajaka\b", "the annual chart"),
    (r"\bLilly\s*/\s*Louis\b", "the Western method"),
    (r"\bLouis Chapter 2\b", "the classical checklist"),
    (r"\bLouis Ch\.? ?2\b", "the classical checklist"),
    (r"\bManley Precision Sandwich\b", "the precision scan"),
    (r"\bPrecision Sandwich\b", "the precision scan"),
    (r"\bGoel synastry\b", "navamsha synastry"),
    (r"\bAvasthi\b", "the classical numerology method"),
    (r"\bWoods\b", "the classical numerology method"),
)

CITE_PATTERNS = [
    # explicit citation markup the engines emit
    r"<div class=['\"]src['\"]>.*?</div>",
    r"<span class=['\"](?:cite|citation|book|source)['\"]>.*?</span>",
    r"<p class=['\"]cite['\"]>.*?</p>",
    r"<blockquote[^>]*class=['\"][^'\"]*quote[^'\"]*['\"].*?</blockquote>",
    # "(Some Book, p.124)" / "— Some Book p. 12" / ", p.93-94"
    r"\(\s*[A-Z][^()]{3,70},\s*p{1,2}\.?\s*\d+(?:\s*[-–]\s*\d+)?\s*\)",
    r"[—–-]\s*p{1,2}\.\s*\d+(?:\s*[-–]\s*\d+)?",
    r"\bp{1,2}\.\s?\d+(?:\s*[-–]\s*\d+)?\b",
    r"\bpage\s+\d+(?:\s*[-–]\s*\d+)?\b",
    # attribution phrasing
    r"\b(?:as )?per\s+(?:the\s+)?(?:book|text|classic|classical text)s?\b",
    r"\bbook-(?:backed|sourced|based)\b",
    r"\bbook rule\b", r"\bbook case\b", r"\bbook precedent\b",
    r"\bcited (?:in|from)\b", r"\bsource[sd]?\s*:\s*[^<.]{0,60}",
    r"\bverified against[^<.]{0,60}",
    r"\bfrom \d[\d,]*\+? rules?\b", r"\b\d[\d,]*\+? (?:book )?rules?\b",
    r"\bOCR\b", r"\bcorpus\b",
    # internal artefacts a customer should never see
    r"\b[\w./-]*user_report[\w./-]*\.html\b",
    r"\b[\w./-]*(?:Vedic|Summary|Predictive|Dasha)_[\w./-]*\.html\b",
    r"the plain-language version for you is\s*",
    r"\bThis is the analyst view[^<.]{0,80}",
    r"\breports?/[\w./-]+",
]


def strip_citations(html: str, *, hide_system_names: bool = True) -> str:
    """Remove bibliographic references; keep the reading itself intact."""
    out = html or ""

    # whole citation sections first
    for title in CITATION_SECTIONS:
        out = re.sub(
            r"<section[^>]*>\s*(?:<div[^>]*>.*?</div>\s*)?<h[23][^>]*>\s*"
            + re.escape(title) + r"[^<]{0,40}</h[23]>.*?</section>",
            "", out, flags=re.S | re.I)
        out = re.sub(r"<details[^>]*>\s*<summary[^>]*>[^<]{0,30}"
                     + re.escape(title) + r"[^<]{0,40}</summary>.*?</details>",
                     "", out, flags=re.S | re.I)

    if hide_system_names:
        for pat, rep in SYSTEM_RENAMES:
            out = re.sub(pat, rep, out)

    for title in BOOK_TITLES:                       # longest first
        out = out.replace(title, "the classical texts")
    for name in AUTHORS:
        out = re.sub(r"\b" + re.escape(name) + r"(?:'s)?\b", "", out)

    for pat in CITE_PATTERNS:
        out = re.sub(pat, "", out, flags=re.S | re.I)

    # CSS class names carry source names too ("bnn-rule"). Invisible to a
    # reader, but it shows in view-source, so rename those as well.
    for old, new in (("bnn", "nadi"), ("kp", "sublord"), ("jaimini", "karaka"),
                     ("cheiro", "timing"), ("bhardwaj", "semantic")):
        out = re.sub(r'(class=["\'][^"\']*?)\b' + old + r'\b',
                     lambda m, n=new: m.group(1) + n, out, flags=re.I)

    return tidy(out)


def tidy(out: str) -> str:
    """Repair the punctuation and duplication that removals leave behind."""
    out = re.sub(r"\(\s*[,;:]?\s*\)", "", out)          # ()  (,)
    # Author names stripped from "(Bonatus / Louis)" leave "( / )" — remove those.
    out = re.sub(r"\(\s*/\s*\)", "", out)
    out = re.sub(r"\(\s*[,;:&|/]+\s*\)", "", out)
    out = re.sub(r"\(\s*,\s*", "(", out)
    out = re.sub(r"\s+([,.;:!?])", r"\1", out)             # " ," → ","
    # the same, but where a tag sat between the word and the comma
    out = re.sub(r"(</[a-zA-Z]+>)\s+([,.;:!?])", r"\1\2", out)
    out = re.sub(r"([,.;:!?])\s*(</[a-zA-Z]+>)\s*\1", r"\1\2", out)
    out = re.sub(r"([,;:])\s*[,;:]+", r"\1", out)          # ",," → ","
    out = re.sub(r"\.{2,}", ".", out)                      # ".." → "."
    # an orphan period left where a removed sentence used to be
    out = re.sub(r"(>|^|\.\s)\s*\.\s+", r"\1 ", out)
    out = re.sub(r"([.!?])\s*\.(\s)", r"\1\2", out)
    out = re.sub(r",\s*\.", ".", out)                     # ",." → "."
    # Only a *dangling* connector counts — one left behind by a removed name or
    # citation, which always leaves a space before the stray punctuation
    # ("cited by ."). Without the `\s+` this also matched ordinary sentences
    # that legitimately end on one of these words ("...than you were born
    # with."), deleting the word and swallowing the full stop.
    out = re.sub(r"\b(and|or|but|per|from|in|of|with|by)\s+[,.]",
                 "", out, flags=re.I)                     # dangling "and ,"
    # a word repeated by a rename ("timing timing", "the the")
    out = re.sub(r"\b(\w+)(\s+\1\b)+", r"\1", out, flags=re.I)
    out = re.sub(r"\bthe classical texts(?:[,\s]*the classical texts)+\b",
                 "the classical texts", out)
    out = re.sub(r"\bthe (nadi|karaka|classical|sub-lord) method"
                 r"(?:[,\s]+and)?\s+the \1 method\b", r"the \1 method", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\s+</", "</", out)
    out = re.sub(r"<p[^>]*>\s*</p>", "", out)
    out = re.sub(r"<li[^>]*>\s*</li>", "", out)
    out = re.sub(r"<(section|div)[^>]*>\s*</\1>", "", out)
    return out


# ---------------------------------------------------------------------------
# 2. Deterministic variation, seeded by the person's own chart
# ---------------------------------------------------------------------------
def _seed(ctx: dict) -> int:
    key = "|".join(str(ctx.get(k, "")) for k in
                   ("name", "dob", "tob", "lagna", "nakshatra", "moon_sign"))
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)


def _pick(options: list[str], ctx: dict, salt: int = 0) -> str:
    return options[(_seed(ctx) + salt) % len(options)]


def first_name(name: str) -> str:
    n = (name or "").strip().split()
    return n[0] if n else "friend"


# ---------------------------------------------------------------------------
# 3. Personal openings — cite what only their chart can say
# ---------------------------------------------------------------------------
def chart_opening(ctx: dict) -> str:
    """A paragraph that could only have been written for this chart."""
    fn = first_name(ctx.get("name", ""))
    # No placeholder here: `... or "your rising sign"` fed the sentence
    # "your rising sign was rising". If the sign is unknown, the clause is
    # dropped instead (see `rising_clause` below).
    lag = ctx.get("lagna") or ""
    nak = ctx.get("nakshatra") or ""
    lord = ctx.get("lagna_lord") or ""
    moon = ctx.get("moon_sign") or ""
    moon_nak = ctx.get("moon_nakshatra") or ""
    md = ctx.get("dasha_md") or ""
    ad = ctx.get("dasha_ad") or ""
    age = ctx.get("age")
    place = ctx.get("place") or ""
    tob = ctx.get("tob") or ""

    if lag:
        openers = [
            f"{fn}, the sky over {place} at {tob} on the day you were born put "
            f"<b>{lag}</b> on the eastern horizon",
            f"{fn}, at the moment you drew your first breath in {place}, "
            f"<b>{lag}</b> was rising",
            f"{fn}, your chart begins where <b>{lag}</b> met the horizon over "
            f"{place} at {tob}",
        ]
    else:
        # The rising sign is unknown — so do not gesture at it. Every one of
        # these still says something only this chart could support.
        openers = [
            f"{fn}, your chart is set for {place} at {tob} on the day you "
            f"were born",
            f"{fn}, this reading starts from the sky over {place} at the hour "
            f"you arrived",
            f"{fn}, everything below is drawn from {place}, {tob}, on your "
            f"birth day",
        ]
    open_ = _pick(openers, ctx)

    if nak:
        open_ += f", in the quarter of <b>{nak}</b>"
    if lord:
        open_ += f", which hands the whole chart to <b>{lord}</b>"
    open_ += "."

    second = ""
    if moon:
        moon_lines = [
            f" Your Moon sits in <b>{moon}</b>{f' ({moon_nak})' if moon_nak else ''}. "
            f"That is the part of you that reacts before you have time to think, "
            f"and it is where this reading looks first for how life actually feels to you.",
            f" The Moon in <b>{moon}</b>{f' ({moon_nak})' if moon_nak else ''} carries your "
            f"instinct and your moods, and much of what follows is read from it.",
            f" With the Moon in <b>{moon}</b>{f' ({moon_nak})' if moon_nak else ''}, your inner "
            f"weather has its own pattern. One this reading takes seriously.",
        ]
        second = _pick(moon_lines, ctx, 7)

    third = ""
    if md:
        period = f"<b>{md}</b>" + (f"–<b>{ad}</b>" if ad else "")
        age_bit = f" at {age}" if age else ""
        third_lines = [
            f" Right now{age_bit} you are living through your {period} period. "
            f"Nothing here is generic advice about a sign; it is dated to the chapter you are actually in.",
            f" You are currently{age_bit} inside the {period} chapter of your life, and every "
            f"timing below is measured from there.",
            f" The period running now{age_bit} is {period}, and that is the lens the whole "
            f"reading is held up to.",
        ]
        third = _pick(third_lines, ctx, 13)

    from report_language import normalize_sentence_dashes
    body = normalize_sentence_dashes(f"{open_}{second}{third}")
    return f"<p>{body}</p>"


def palm_opening(ctx: dict) -> str:
    fn = first_name(ctx.get("name", ""))
    hand = ctx.get("hand_type") or ""
    dom = ctx.get("dominant") or "right"
    age = ctx.get("age")
    openers = [
        f"{fn}, I have looked at both of your palms — the {dom} one for the life you have "
        f"actually built, the other for what you started with.",
        f"{fn}, your two hands do not say the same thing, and that difference is where this "
        f"reading begins.",
        f"{fn}, both palms are in front of me: one holds your blueprint, the {dom} one holds "
        f"what you have made of it.",
    ]
    out = _pick(openers, ctx)
    if hand:
        out += (f" Yours is a <b>{hand}</b> hand, and that shapes everything that follows — "
                f"it is the difference between a life run on ideas and one run on instinct.")
    if age:
        out += (f" At {age}, a good part of your palm has already been written; "
                f"the rest is still forming, and that is the part worth talking about.")
    return f"<p>{out}</p>"


def horary_opening(ctx: dict) -> str:
    fn = first_name(ctx.get("name", ""))
    q = ctx.get("question") or "your question"
    when = ctx.get("asked") or ""
    openers = [
        f"{fn}, you asked — “{q}” — and the sky at {when} is the only chart that matters here. "
        f"Not your birth chart: the moment the question formed in you.",
        f"{fn}, the question “{q}” was put at {when}, and that instant has its own chart. "
        f"This is a reading of that instant.",
        f"{fn}, “{q}”. The moment you asked, {when}, froze a sky — and that sky answers.",
    ]
    return f"<p>{_pick(openers, ctx)}</p>"


def numerology_opening(ctx: dict) -> str:
    fn = first_name(ctx.get("name", ""))
    name = ctx.get("name") or ""
    dob = ctx.get("dob") or ""
    openers = [
        f"{fn}, two things were fixed the day you arrived: the date, {dob}, and the name you "
        f"answer to, <b>{name}</b>. Everything below comes out of those two.",
        f"{fn}, your numbers come from just two facts — <b>{name}</b>, and {dob}. "
        f"That is all it takes.",
        f"{fn}, the letters of <b>{name}</b> and the digits of {dob} are the whole raw material "
        f"of this reading.",
    ]
    return f"<p>{_pick(openers, ctx)}</p>"


def match_opening(ctx: dict) -> str:
    """For a two-person report. The natal opening addresses only one of them."""
    couple = ctx.get("name") or "You both"
    names = [n.strip() for n in re.split(r"\s*&\s*|\s+and\s+", couple) if n.strip()]
    a = names[0] if names else "You"
    b = names[1] if len(names) > 1 else "your partner"
    lead = _pick([
        f"{a} and {b} — two charts, read side by side.",
        f"This is {a} and {b}'s charts held up against each other.",
        f"{a} and {b}: what the two charts do when you put them together.",
    ], ctx)
    body = _pick([
        "Compatibility is not one number. The score below is the classical "
        "count, and everything after it explains what that count is actually "
        "made of — where the two of you fit easily, and where the effort will "
        "have to be deliberate.",
        "The guna score is the headline, but it is the detail underneath that "
        "tells you what married life would ask of each of you. Both are here.",
        "A score settles nothing on its own. What follows is which parts of "
        "the two charts agree, which pull against each other, and what that "
        "means in practice.",
    ], ctx, salt=3)
    return f"<p>{lead} {body}</p>"


OPENINGS = {
    "full_report": chart_opening,
    "kundali_match": match_opening,
    "match": match_opening,
    "chart": chart_opening,
    "daily": chart_opening,
    "palm": palm_opening,
    "horary": horary_opening,
    "numerology": numerology_opening,
}


# ---------------------------------------------------------------------------
# 4. Optional LLM polish (off unless configured)
# ---------------------------------------------------------------------------
def llm_polish(text: str, ctx: dict, *, max_words: int = 160) -> Optional[str]:
    """
    Rewrite an opening in warmer prose, grounded ONLY in the supplied facts.
    Returns None when unconfigured or on any failure — callers fall back to the
    deterministic text, so this can never break a paid report.
    """
    key = os.getenv("ASTRO_LLM_KEY")
    if not key:
        return None
    url = os.getenv("ASTRO_LLM_URL", "https://api.openai.com/v1/chat/completions")
    model = os.getenv("ASTRO_LLM_MODEL", "gpt-4o-mini")
    facts = {k: v for k, v in ctx.items() if v not in (None, "")}
    prompt = (
        "Rewrite the passage below as a warm, specific, second-person opening for an "
        "astrology/palmistry reading. Rules: keep every fact exactly as given, invent "
        f"nothing, no flattery, no horoscope clichés, under {max_words} words, address "
        "the person by first name once. Facts you may use:\n"
        + json.dumps(facts, default=str) + "\n\nPassage:\n" + re.sub(r"<[^>]+>", "", text)
    )
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps({"model": model, "temperature": 0.7,
                             "messages": [{"role": "user", "content": prompt}]}).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        )
        with urllib.request.urlopen(req, timeout=25) as r:
            out = json.load(r)["choices"][0]["message"]["content"].strip()
        return f"<p>{out}</p>" if out else None
    except Exception:                                                 # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# 5. The public entry point
# ---------------------------------------------------------------------------
BADGE = ("<div style=\"font-size:12px;letter-spacing:.14em;text-transform:uppercase;"
         "opacity:.65;margin-bottom:6px\">Prepared for {who} · {when}</div>")


def personalise(html: str, ctx: dict, kind: str = "full_report") -> str:
    """Strip machinery, humanise the voice, and lead with a personal opening."""
    # Order matters. Leaks go first — there is no point translating the jargon
    # in a paragraph that ends in a session UUID. Jargon is translated last of
    # the text passes so the citation stripper still sees the method names it
    # matches on ("BNN", "Jaimini") before they are renamed.
    out = strip_citations(humanise(strip_machinery(strip_leaks(html or ""))),
                          hide_system_names=os.getenv("HIDE_SYSTEM_NAMES", "1") == "1")
    if os.getenv("PLAIN_ENGLISH", "1") == "1":
        out = translate_jargon(rephrase(out))
    # Seams and repetition are the last passes: they clean up the prose that
    # the earlier stages produced, not just what the engine emitted.
    try:
        import astro_seams
        out = astro_seams.smooth(out, real_name=ctx.get("name") or "")
    except Exception:
        pass
    try:
        import astro_variation
        out = astro_variation.vary(out, ctx)
    except Exception:
        pass

    opener_fn = OPENINGS.get(kind, chart_opening)
    opening = opener_fn(ctx)
    polished = llm_polish(opening, dict(ctx, kind=kind))
    if polished:
        opening = polished

    badge = BADGE.format(
        who=ctx.get("name") or "you",
        when=(ctx.get("report_date") or date.today().strftime("%d %B %Y")),
    )
    # class "voice-lead" so astro_split can lift it out and keep it on BOTH
    # halves rather than mistaking it for the document's only section
    block = (f'<section class="section voice-lead" style="border-left:3px solid #c9a227;'
             f'padding-left:16px">{badge}{opening}</section>')

    # insert after <body ...> so it leads the document
    m = re.search(r"<body[^>]*>", out, re.I)
    if m:
        out = out[:m.end()] + block + out[m.end():]
    else:
        out = block + out
    # Concise is the last pass so it also cleans the opening it just inserted.
    return concise(out)


def context_from_pc(pc: dict, *, name: str = "", place: str = "",
                    tob: str = "", dominant: str = "right") -> dict:
    """Build a voice context from an astro_precompute payload."""
    meta = pc.get("meta") or {}
    planets = pc.get("planets") or {}
    moon = planets.get("Moon") or {}
    vim = pc.get("vimshottari") or {}
    cur = vim.get("current") or {}
    if not cur:
        today = date.today().isoformat()
        for row in vim.get("sequence") or []:
            if str(row.get("start") or "") <= today <= str(row.get("end") or ""):
                cur = row
                break
    return {
        "name": name or meta.get("client") or "",
        "dob": meta.get("dob"), "tob": tob or meta.get("birth_time"),
        "place": place or meta.get("birth_place") or "",
        "age": meta.get("age"),
        "lagna": meta.get("lagna_sign"), "nakshatra": meta.get("lagna_nakshatra"),
        "lagna_lord": meta.get("lagna_lord"),
        "moon_sign": moon.get("sign"), "moon_nakshatra": moon.get("nakshatra"),
        "dasha_md": cur.get("md_lord") or cur.get("lord"),
        "dasha_ad": cur.get("ad_lord"),
        "dominant": dominant,
        "report_date": date.today().strftime("%d %B %Y"),
    }
