"""Fact-preservation guard for the report voice rewrite.

The rewrite changes how a report *reads*. It must not change what the report
*says*. This module makes that testable instead of trustable.

It extracts every fact-bearing token from a report — dates, numbers, planets,
signs, nakshatras, houses, dignities, verdict directions — canonicalises each
one, and compares the multiset before and after a rewrite. A dropped date, an
invented house number, a verdict flipped from weak to strong: all of them fail
here, and the failure names the token and the file.

Three deliberate design decisions, because each one is a place this could go
wrong quietly:

1. **Canonicalisation, not string equality.** `2027-03-07` and `7 Mar 2027` are
   the same fact, and unifying date formats is part of the rewrite. Both
   normalise to `date:2027-03-07`. But `8 Mar 2027` does not, so a typo during
   rewriting still fails.

2. **Verdicts compare by direction, not by wording.** `△ Weak / afflicted` may
   legitimately become "this is where you will feel friction" — that is the
   whole point of the rewrite. Both carry `verdict:down`. Turning it into
   "this area is well supported" carries `verdict:up` and fails.

3. **Fact numbers stay as digits.** House style, enforced here: never spell a
   fact number out in prose. `1 planet(s)` may become `1 planet`, never `one
   planet`. Without this rule "one" in ordinary prose is indistinguishable from
   a spelled-out count, and the guard would be full of false alarms — which is
   how a guard ends up switched off.

Removals must be *declared*. The sanitiser legitimately deletes leaked
filesystem paths and session UUIDs, and those contain digits. A caller says so
explicitly via `allow_removed`; anything undeclared is a failure.

Usage:
    from report_fact_guard import facts, diff, assert_preserved

    before = open("Vedic_KP.html").read()
    after  = voice.rewrite(before)
    assert_preserved(before, after)          # raises FactDrift with details

CLI:
    python report_fact_guard.py selftest
    python report_fact_guard.py show <file.html>
    python report_fact_guard.py compare <before.html> <after.html>
"""

from __future__ import annotations

import html as _html
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Sequence

# ---------------------------------------------------------------------------
# vocabulary
# ---------------------------------------------------------------------------

# Sanskrit / English aliases collapse to one canonical name, so translating
# "Surya" to "the Sun" is a voice change, not a fact change.
PLANET_ALIASES = {
    "sun": "Sun", "surya": "Sun", "ravi": "Sun",
    "moon": "Moon", "chandra": "Moon", "soma": "Moon",
    "mars": "Mars", "mangal": "Mars", "kuja": "Mars", "angaraka": "Mars",
    "mercury": "Mercury", "budha": "Mercury", "budh": "Mercury",
    "jupiter": "Jupiter", "guru": "Jupiter", "brihaspati": "Jupiter",
    "venus": "Venus", "shukra": "Venus", "sukra": "Venus",
    "saturn": "Saturn", "shani": "Saturn", "sani": "Saturn",
    "rahu": "Rahu", "ketu": "Ketu",
    "uranus": "Uranus", "neptune": "Neptune", "pluto": "Pluto",
}

SIGN_ALIASES = {
    "aries": "Aries", "mesha": "Aries", "mesa": "Aries",
    "taurus": "Taurus", "vrishabha": "Taurus", "vrsabha": "Taurus",
    "gemini": "Gemini", "mithuna": "Gemini",
    "cancer": "Cancer", "karka": "Cancer", "kataka": "Cancer",
    "leo": "Leo", "simha": "Leo",
    "virgo": "Virgo", "kanya": "Virgo",
    "libra": "Libra", "tula": "Libra", "thula": "Libra",
    "scorpio": "Scorpio", "vrischika": "Scorpio", "vrscika": "Scorpio",
    "sagittarius": "Sagittarius", "dhanu": "Sagittarius", "dhanus": "Sagittarius",
    "capricorn": "Capricorn", "makara": "Capricorn", "makar": "Capricorn",
    "aquarius": "Aquarius", "kumbha": "Aquarius",
    "pisces": "Pisces", "meena": "Pisces", "mina": "Pisces",
}

NAKSHATRAS = (
    "ashwini", "aswini", "bharani", "krittika", "kritika", "rohini",
    "mrigashira", "mrigashirsha", "ardra", "punarvasu", "pushya", "ashlesha",
    "aslesha", "magha", "purva phalguni", "uttara phalguni", "hasta", "chitra",
    "swati", "swathi", "vishakha", "visakha", "anuradha", "jyeshtha", "jyestha",
    "mula", "moola", "purva ashadha", "uttara ashadha", "shravana", "sravana",
    "dhanishta", "dhanishtha", "shatabhisha", "satabhisha",
    "purva bhadrapada", "uttara bhadrapada", "revati",
)
_NAK_CANON = {
    "aswini": "ashwini", "kritika": "krittika", "mrigashirsha": "mrigashira",
    "aslesha": "ashlesha", "swathi": "swati", "visakha": "vishakha",
    "jyestha": "jyeshtha", "moola": "mula", "sravana": "shravana",
    "dhanishtha": "dhanishta", "satabhisha": "shatabhisha",
}

# Dignity is a hard fact — "debilitated" must never soften into "challenged"
# without the guard noticing, because dignity drives the entire reading.
DIGNITY_TERMS = {
    "exalted": "exalted", "exaltation": "exalted", "uccha": "exalted",
    "debilitated": "debilitated", "debilitation": "debilitated",
    "neecha": "debilitated", "nicha": "debilitated", "fallen": "debilitated",
    "own sign": "own", "own house": "own", "swakshetra": "own",
    "moolatrikona": "moolatrikona", "mooltrikona": "moolatrikona",
    "combust": "combust", "astangata": "combust",
    "retrograde": "retrograde", "vakri": "retrograde",
    "digbala": "digbala", "directional strength": "digbala",
    # Approved plain-English renderings from astro_voice.JARGON_TERMS. Without
    # these the guard reads a correct translation as a deleted fact, and the
    # first thing anyone does with a guard that cries wolf is disable it.
    "in its best sign": "moolatrikona",
    "in its own sign": "own",
    "too close to the sun to act freely": "combust",
}

# Verdict *direction*. Wording is free to change; direction is not.
VERDICT_UP = (
    "▲", "⊕", "★", "✓", "✦",
    "strong", "well supported", "favourable", "favorable", "auspicious",
    "benefic", "supported", "hits your chart", "excellent", "good results",
)
VERDICT_DOWN = (
    "▼", "⊖", "△", "✗", "✘",
    "weak", "afflicted", "under strain", "malefic", "challenging",
    "difficult", "adverse", "not present", "stressed",
)
VERDICT_MIXED = ("◆", "◐", "mixed", "partly hit", "neutral", "moderate")

# Leaks that the sanitiser is *expected* to delete. Their tokens are exempt
# from the "nothing may disappear" rule, so a caller does not have to enumerate
# the digits inside a session UUID by hand.
LEAK_PATTERNS = (
    r"(?:/[\w.\-]+){2,}/?",                      # unix filesystem paths
    r"[A-Za-z]:\\[\w\\.\-]+",                    # windows paths
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",  # uuid
    r"\b[0-9a-f]{12,}\b",                        # bare hex ids
)

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

# ---------------------------------------------------------------------------
# text extraction
# ---------------------------------------------------------------------------

_TAG = re.compile(r"<[^>]+>")
_DROP = re.compile(r"<(script|style|svg)\b[^>]*>.*?</\1>", re.S | re.I)
# Nav chrome and jump menus repeat every heading; counting them would make the
# guard sensitive to navigation changes that carry no facts.
_NAV = re.compile(r"<(nav|aside)\b[^>]*>.*?</\1>", re.S | re.I)


def visible_text(source: str) -> str:
    """HTML (or plain text) to the words a reader actually sees."""
    if "<" not in source:
        return re.sub(r"\s+", " ", source).strip()
    s = _DROP.sub(" ", source)
    s = _NAV.sub(" ", s)
    # keep glyphs in title/alt attributes out; they are decoration
    s = _TAG.sub(" ", s)
    return re.sub(r"\s+", " ", _html.unescape(s)).strip()


# ---------------------------------------------------------------------------
# fact extraction
# ---------------------------------------------------------------------------

_TIME = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?\b")
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DMY = re.compile(
    r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})\b")
_MDY = re.compile(
    r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})\b")
_MY = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{4})\b")
_YEAR = re.compile(r"\b(1[89]\d{2}|20\d{2}|21\d{2})\b")

_HOUSE_ORD = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)\s+(?:house|bhava)\b", re.I)
_HOUSE_H = re.compile(r"\b(\d{1,2})H\b")
_HOUSE_WORD = re.compile(
    r"\bhouses?(?:\(s\))?\s+"
    r"((?:\d{1,2}(?:st|nd|rd|th)?)(?:\s*(?:,|&|and)\s*\d{1,2}(?:st|nd|rd|th)?)*)",
    re.I)
_HOUSE_PAREN = re.compile(r"\((\d{1,2})(?:st|nd|rd|th)\)")
# Houses are also written as bare ordinals when the context makes it obvious:
# "Moon as 2nd lord", "it rules your 5th and 12th". The guard could not see
# those, so rephrasing them into an explicit "house" read as an invented fact.
_HOUSE_LORD = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\s+lord\b", re.I)
_HOUSE_RULES = re.compile(
    r"\brules?\s+(?:your\s+|the\s+)?"
    r"((?:\d{1,2}(?:st|nd|rd|th))(?:\s*(?:,|&|and)\s*\d{1,2}(?:st|nd|rd|th))*)",
    re.I)

_VARGA = re.compile(r"\bD-?(\d{1,3})\b")
_FRACTION = re.compile(r"\b(\d{1,4})\s*/\s*(\d{1,4})\b")
# "6 of the 8 factors" and "6 out of 8" are the same fact as "6/8"; unifying
# them here is what lets the rewrite say it in words without tripping the guard.
_FRACTION_PROSE = re.compile(
    r"\b(\d{1,4})\s+(?:of|out\s+of)\s+(?:the\s+)?(\d{1,4})\b", re.I)
_PERCENT = re.compile(r"\b(\d{1,3}(?:\.\d+)?)\s*%")
_DEGREE = re.compile(r"\b(\d{1,3}(?:\.\d+)?)\s*°")
_NUM = re.compile(r"\b(\d+(?:\.\d+)?)\b")

_WORD_NUM = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b", re.I)
_WORD_NUM_VALUES = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}


def _month(token: str) -> int | None:
    return MONTHS.get(token.strip(".").lower())


@dataclass
class FactSet:
    """Canonical facts found in one report, as a multiset."""
    counts: Counter = field(default_factory=Counter)

    def add(self, category: str, value) -> None:
        self.counts[f"{category}:{value}"] += 1

    def __len__(self) -> int:
        return sum(self.counts.values())

    def by_category(self) -> dict:
        out: dict = {}
        for key, n in self.counts.items():
            cat = key.split(":", 1)[0]
            out.setdefault(cat, Counter())[key.split(":", 1)[1]] = n
        return out


_VERDICT_ATTR = re.compile(r"""data-verdict\s*=\s*["\']?(up|down|mixed)""", re.I)


def facts(source: str, *, ignore_leaks: bool = True) -> FactSet:
    """Extract the canonical fact multiset from a report."""
    # Read verdict markers off the raw markup before tags are stripped. Prose
    # like "this is where you will feel friction" carries a verdict no
    # vocabulary list can reliably detect, so the voice layer is required to
    # tag the block with data-verdict when it replaces a glyph with a sentence.
    # The guard then checks the marker, not the wording.
    attr_verdicts = [m[1].lower() for m in _VERDICT_ATTR.finditer(source)]
    text = visible_text(source)
    if ignore_leaks:
        for pat in LEAK_PATTERNS:
            text = re.sub(pat, " ", text)

    fs = FactSet()

    # --- dates first, then blank them out so their digits are not recounted
    def _eat(pattern: re.Pattern, handler) -> None:
        nonlocal text
        out, last, chunks = [], 0, []
        for m in pattern.finditer(text):
            if handler(m):
                chunks.append((m.start(), m.end()))
        for a, b in chunks:
            out.append(text[last:a])
            out.append(" ")
            last = b
        out.append(text[last:])
        text = "".join(out)

    def iso(m):
        y, mo, d = int(m[1]), int(m[2]), int(m[3])
        if 1 <= mo <= 12 and 1 <= d <= 31:
            fs.add("date", f"{y:04d}-{mo:02d}-{d:02d}")
            return True
        return False

    def dmy(m):
        mo = _month(m[2])
        if mo:
            fs.add("date", f"{int(m[3]):04d}-{mo:02d}-{int(m[1]):02d}")
            return True
        return False

    def mdy(m):
        mo = _month(m[1])
        if mo:
            fs.add("date", f"{int(m[3]):04d}-{mo:02d}-{int(m[2]):02d}")
            return True
        return False

    def my(m):
        mo = _month(m[1])
        if mo:
            fs.add("month", f"{int(m[2]):04d}-{mo:02d}")
            return True
        return False

    def clock(m):
        # Seconds are noise on a birth time; normalise so "12:56:00" and
        # "12:56" are one fact and dropping ":00" is not a lost number.
        fs.add("time", f"{int(m[1]):02d}:{m[2]}")
        return True

    _eat(_TIME, clock)
    _eat(_ISO, iso)
    _eat(_DMY, dmy)
    _eat(_MDY, mdy)
    _eat(_MY, my)

    # --- houses, before generic numbers eat the digits
    def house(m):
        n = int(m[1])
        if 1 <= n <= 12:
            fs.add("house", n)
            return True
        return False

    def houses(m):
        found = re.findall(r"\d{1,2}", m[1])
        ok = False
        for raw in found:
            n = int(raw)
            if 1 <= n <= 12:
                fs.add("house", n)
                ok = True
        return ok

    _eat(_HOUSE_ORD, house)
    _eat(_HOUSE_H, house)
    _eat(_HOUSE_WORD, houses)
    _eat(_HOUSE_PAREN, house)
    _eat(_HOUSE_LORD, house)
    _eat(_HOUSE_RULES, houses)

    def varga(m):
        fs.add("varga", f"D{int(m[1])}")
        return True

    _eat(_VARGA, varga)

    # --- structured numerics
    def frac(m):
        fs.add("fraction", f"{int(m[1])}/{int(m[2])}")
        return True

    def pct(m):
        fs.add("percent", float(m[1]))
        return True

    def deg(m):
        fs.add("degree", float(m[1]))
        return True

    _eat(_FRACTION, frac)
    _eat(_FRACTION_PROSE, frac)
    _eat(_PERCENT, pct)
    _eat(_DEGREE, deg)

    def year(m):
        fs.add("year", int(m[1]))
        return True

    _eat(_YEAR, year)

    for m in _NUM.finditer(text):
        v = float(m[1])
        fs.add("number", int(v) if v.is_integer() else v)

    # Spelled-out numerals are recorded separately: they are *style* under the
    # digits-stay-digits rule, and reporting them lets the linter flag a
    # rewrite that spelled a count out instead of failing mysteriously.
    for m in _WORD_NUM.finditer(text):
        fs.add("wordnum", _WORD_NUM_VALUES[m[1].lower()])

    low = text.lower()

    for alias, canon in PLANET_ALIASES.items():
        for _ in re.finditer(rf"\b{re.escape(alias)}\b", low):
            fs.add("planet", canon)

    for alias, canon in SIGN_ALIASES.items():
        for _ in re.finditer(rf"\b{re.escape(alias)}\b", low):
            fs.add("sign", canon)

    for nak in NAKSHATRAS:
        for _ in re.finditer(rf"\b{re.escape(nak)}\b", low):
            fs.add("nakshatra", _NAK_CANON.get(nak, nak))

    for term, canon in DIGNITY_TERMS.items():
        for _ in re.finditer(rf"\b{re.escape(term)}\b", low):
            fs.add("dignity", canon)

    for name in attr_verdicts:
        fs.add("verdict", name)

    for group, name in ((VERDICT_UP, "up"), (VERDICT_DOWN, "down"),
                        (VERDICT_MIXED, "mixed")):
        for token in group:
            if token.isalpha() or " " in token:
                hits = len(re.findall(rf"\b{re.escape(token)}\b", low))
            else:
                hits = low.count(token)
            for _ in range(hits):
                fs.add("verdict", name)

    return fs


# ---------------------------------------------------------------------------
# comparison
# ---------------------------------------------------------------------------

class FactDrift(AssertionError):
    """Raised when a rewrite changed what the report says."""


@dataclass
class Diff:
    missing: Counter = field(default_factory=Counter)   # in before, not after
    added: Counter = field(default_factory=Counter)     # in after, not before

    @property
    def clean(self) -> bool:
        return not self.missing and not self.added

    def report(self, limit: int = 25) -> str:
        lines = []
        if self.missing:
            lines.append("  LOST (present before the rewrite, gone after):")
            for k, n in self.missing.most_common(limit):
                lines.append(f"    -{n:<3} {k}")
        if self.added:
            lines.append("  INVENTED (not present before the rewrite):")
            for k, n in self.added.most_common(limit):
                lines.append(f"    +{n:<3} {k}")
        return "\n".join(lines) or "  no drift"


# Categories where a change is a factual error. `wordnum` is excluded — it is a
# style signal — and `verdict` counts are compared as directions, which can
# legitimately shift in *count* when one glyph becomes one sentence. What may
# not happen is a direction appearing that was never there, or the only
# instance of a direction vanishing.
HARD = ("date", "month", "year", "time", "house", "varga", "fraction",
        "percent", "degree", "number", "planet", "sign", "nakshatra", "dignity")


def diff(before: str, after: str, *,
         allow_removed: Sequence[str] = (),
         allow_added: Sequence[str] = ()) -> Diff:
    """Compare two versions of a report. Empty diff means facts survived."""
    a, b = facts(before).counts, facts(after).counts
    d = Diff()

    for key in set(a) | set(b):
        cat = key.split(":", 1)[0]
        na, nb = a.get(key, 0), b.get(key, 0)
        if cat == "wordnum":
            continue
        if cat == "verdict":
            # presence, not count
            if na and not nb:
                d.missing[key] += 1
            elif nb and not na:
                d.added[key] += 1
            continue
        if cat not in HARD:
            continue
        if na > nb:
            d.missing[key] += na - nb
        elif nb > na and na == 0:
            # Strict on *new values*, relaxed on repetition.
            #
            # Translating "in kendra/trikona 10th" to "the 10th house, a pillar
            # house" makes an implicit house explicit: the fact was always in
            # the report, the guard simply could not see it in the original
            # phrasing. Failing that would push me to write worse English to
            # satisfy the tool.
            #
            # So: a value that appears NOWHERE in the original is a
            # fabrication and fails. A value already stated in the original,
            # now stated once more, is phrasing. Losing a fact stays
            # unconditionally forbidden — that asymmetry is the point.
            d.added[key] += nb - na

    for key in allow_removed:
        d.missing.pop(key, None)
    for key in allow_added:
        d.added.pop(key, None)
    return d


def assert_preserved(before: str, after: str, *, label: str = "report",
                     allow_removed: Sequence[str] = (),
                     allow_added: Sequence[str] = ()) -> None:
    d = diff(before, after, allow_removed=allow_removed, allow_added=allow_added)
    if not d.clean:
        raise FactDrift(f"fact drift in {label}:\n{d.report()}")


def spelled_out_numbers(after: str) -> Counter:
    """House-style lint: fact numbers must stay digits."""
    return Counter(k for k, _ in facts(after).counts.items()
                   if k.startswith("wordnum:"))


# ---------------------------------------------------------------------------
# self-test — the guard has to be able to fail, or it is decoration
# ---------------------------------------------------------------------------

_SAMPLE = """
<h2>Where You Stand Now</h2>
<p>Mercury (debilitated) sits in your 10th house. Running Jupiter mahadasha,
Ketu antar until 2027-03-07. Jupiter is in Cancer (BAV 6/8) and shifts into Leo
around Oct 2026. Confluence 44%. Houses 5, 7, 8, 10 are activated.
<span>△ Weak / afflicted</span> — D2 Hora. Moon in Hasta nakshatra.</p>
<script>var x = 99;</script>
"""


def _selftest() -> int:
    ok, bad = 0, 0

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal ok, bad
        if cond:
            ok += 1
            print(f"  pass  {name}")
        else:
            bad += 1
            print(f"  FAIL  {name} {detail}")

    f = facts(_SAMPLE).by_category()

    check("date parsed", f.get("date", {}).get("2027-03-07") == 1, f.get("date"))
    check("month-year parsed", f.get("month", {}).get("2026-10") == 1, f.get("month"))
    check("houses found", f.get("house", {}).get("10") == 2
          and f.get("house", {}).get("5") == 1, f.get("house"))
    check("fraction kept", f.get("fraction", {}).get("6/8") == 1, f.get("fraction"))
    check("percent kept", f.get("percent", {}).get("44.0") == 1, f.get("percent"))
    check("varga kept", f.get("varga", {}).get("D2") == 1, f.get("varga"))
    check("dignity kept", f.get("dignity", {}).get("debilitated") == 1,
          f.get("dignity"))
    check("nakshatra kept", f.get("nakshatra", {}).get("hasta") == 1,
          f.get("nakshatra"))
    check("script ignored", "99" not in f.get("number", {}), f.get("number"))

    # --- a pure voice rewrite must pass
    rewritten = """
    <h2>Where you stand right now</h2>
    <p>Your Mercury is debilitated in the 10th house — the part of your chart
    that governs work and public standing. You are in the Jupiter chapter, with
    the Ketu sub-period running to 7 Mar 2027. Jupiter sits in Cancer, where 6
    of the 8 factors back it, and steps into Leo around Oct 2026. Across the
    methods, agreement runs at 44%. Houses 5, 7, 8 and 10 are lit up. Your D2
    Hora is <span data-verdict="down">where you will feel friction</span>.
    Your Moon is in Hasta.</p>
    """
    d = diff(_SAMPLE, rewritten)
    check("clean rewrite passes", d.clean, "\n" + d.report())

    # --- the failures it exists to catch
    cases = [
        ("changed date", _SAMPLE.replace("2027-03-07", "2027-03-08")),
        ("changed dignity", _SAMPLE.replace("debilitated", "exalted")),
        ("dropped percentage", _SAMPLE.replace("Confluence 44%.", "")),
        ("changed house", _SAMPLE.replace("10th house", "11th house")),
        ("flipped verdict", _SAMPLE.replace("△ Weak / afflicted",
                                            "▲ strong and well supported")),
        ("invented number", _SAMPLE.replace("BAV 6/8", "BAV 6/8, score 7/8")),
        ("dropped planet", _SAMPLE.replace("Moon in Hasta nakshatra",
                                           "in Hasta nakshatra")),
    ]
    for name, mutated in cases:
        check(f"catches {name}", not diff(_SAMPLE, mutated).clean)

    # --- declared removals are allowed, undeclared ones are not
    leaky = _SAMPLE.replace(
        "<h2>", "<p>Source precomputed:/home/oppo/Desktop/_astro_sessions/"
                "d08f5275-9fe5-4f4c-8871-6824cefb4eeb/input/ritxx</p><h2>")
    check("leak text carries no facts either way", diff(leaky, _SAMPLE).clean,
          "\n" + diff(leaky, _SAMPLE).report())

    # --- style lint
    spelled = rewritten.replace("6\n    of the 8 factors", "six of the eight factors")
    check("lint sees spelled-out numbers",
          bool(spelled_out_numbers("six of the eight factors back it")))

    print(f"\n{ok} passed, {bad} failed")
    return 1 if bad else 0


def _main(argv: Sequence[str]) -> int:
    if len(argv) < 2 or argv[1] == "selftest":
        return _selftest()
    cmd = argv[1]
    if cmd == "show" and len(argv) > 2:
        f = facts(open(argv[2], errors="ignore").read())
        for cat, items in sorted(f.by_category().items()):
            total = sum(items.values())
            head = ", ".join(f"{k}×{v}" if v > 1 else str(k)
                             for k, v in list(items.items())[:12])
            print(f"{cat:>10} ({total:>3}): {head}")
        print(f"\n{len(f)} fact tokens")
        return 0
    if cmd == "compare" and len(argv) > 3:
        a = open(argv[2], errors="ignore").read()
        b = open(argv[3], errors="ignore").read()
        d = diff(a, b)
        print(d.report())
        return 0 if d.clean else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
