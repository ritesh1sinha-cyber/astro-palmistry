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
    r"\brule-based\b", r"\bhard-coded\b", r"\bheuristic(ally)?\b",
    r"\bfallback template\b", r"\btemplate line\b",
    # internal calibration notes: honest engineering, but they read to a paying
    # customer as "we didn't really do the work"
    r"⚠\s*Uncalibrated[^<]*",
    r"<[^>]*>\s*⚠\s*Uncalibrated.*?</[^>]+>",
    r"\bfirst pass\b[^<]{0,120}",
    r"life-event dates were not supplied[^<]*",
]

# third person / clinical → second person
HUMANISE = [
    (r"\bThe native's\b", "Your"), (r"\bthe native's\b", "your"),
    (r"\bThe native\b", "You"),    (r"\bthe native\b", "you"),
    (r"\bThe querent's\b", "Your"), (r"\bthe querent's\b", "your"),
    (r"\bThe querent\b", "You"),   (r"\bthe querent\b", "you"),
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
    out = re.sub(r"\b(and|or|but|per|from|in|of|with|by)\s*[,.]",
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
    lag = ctx.get("lagna") or "your rising sign"
    nak = ctx.get("nakshatra") or ""
    lord = ctx.get("lagna_lord") or ""
    moon = ctx.get("moon_sign") or ""
    moon_nak = ctx.get("moon_nakshatra") or ""
    md = ctx.get("dasha_md") or ""
    ad = ctx.get("dasha_ad") or ""
    age = ctx.get("age")
    place = ctx.get("place") or ""
    tob = ctx.get("tob") or ""

    openers = [
        f"{fn}, the sky over {place} at {tob} on the day you were born put "
        f"<b>{lag}</b> on the eastern horizon",
        f"{fn}, at the moment you drew your first breath in {place}, "
        f"<b>{lag}</b> was rising",
        f"{fn}, your chart begins where <b>{lag}</b> met the horizon over {place} at {tob}",
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
            f" Your Moon sits in <b>{moon}</b>{f' ({moon_nak})' if moon_nak else ''} — "
            f"that is the part of you that reacts before you have time to think, "
            f"and it is where this reading looks first for how life actually feels to you.",
            f" The Moon in <b>{moon}</b>{f' ({moon_nak})' if moon_nak else ''} carries your "
            f"instinct and your moods, and much of what follows is read from it.",
            f" With the Moon in <b>{moon}</b>{f' ({moon_nak})' if moon_nak else ''}, your inner "
            f"weather has its own pattern — one this reading takes seriously.",
        ]
        second = _pick(moon_lines, ctx, 7)

    third = ""
    if md:
        period = f"<b>{md}</b>" + (f"–<b>{ad}</b>" if ad else "")
        age_bit = f" at {age}" if age else ""
        third_lines = [
            f" Right now{age_bit} you are living through your {period} period — so nothing here "
            f"is generic advice about a sign; it is dated to the chapter you are actually in.",
            f" You are currently{age_bit} inside the {period} chapter of your life, and every "
            f"timing below is measured from there.",
            f" The period running now{age_bit} is {period}, and that is the lens the whole "
            f"reading is held up to.",
        ]
        third = _pick(third_lines, ctx, 13)

    return f"<p>{open_}{second}{third}</p>"


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


OPENINGS = {
    "full_report": chart_opening,
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
    out = strip_citations(humanise(strip_machinery(html or "")),
                          hide_system_names=os.getenv("HIDE_SYSTEM_NAMES", "1") == "1")

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
        return out[:m.end()] + block + out[m.end():]
    return block + out


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
