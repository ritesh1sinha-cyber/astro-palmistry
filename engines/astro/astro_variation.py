"""Break template repetition without breaking determinism.

The divisional summary says this twenty times, once per chart:

    This division of life — your wealth — is mixed — its lagna lord Mercury is
    debilitated; the lord sits in a strong 7th; 1 planet(s) exalted/own here.

Every fact in it is correct and specific. It still reads as a form letter,
because by the third repetition the reader has stopped reading the sentence and
started reading the *slot values*. That is the moment a paid report becomes a
printout.

Two constraints pull against each other:

* **Vary the phrasing**, or the reader sees the template.
* **Never vary the output for the same chart**, or the report is not
  reproducible, cannot be cached, and a customer who reloads sees a different
  reading of the same chart — which destroys trust faster than repetition does.

Both are satisfied by seeding on the chart itself plus the occurrence index:
variant = f(chart_hash, skeleton, nth occurrence). The same chart always
produces the same words; consecutive lines differ; two different people with
the same chart shape get different prose.

Facts are never touched. Only the connective language around them varies —
the captured groups are re-emitted verbatim.
"""

from __future__ import annotations

import hashlib
import re
from typing import Callable, Iterable

# ---------------------------------------------------------------------------
# Templates observed in the real report set, with alternates.
# Each entry: (compiled pattern, [templates using \1 \2 ... for captures]).
# The FIRST template should read like the original so a chart that hashes to
# index 0 is unchanged.
# ---------------------------------------------------------------------------

VARIANTS: list[tuple[re.Pattern, list[str]]] = [
    # "This division of life — your wealth — is mixed —"
    (re.compile(
        r"This part of your life — (?P<area>[^—]{2,40}) — is (?P<verdict>[\w /-]{2,28}) —"),
     [
         "This part of your life — {area} — is {verdict} —",
         "Where {area} is concerned, the picture is {verdict} —",
         "On {area}, your chart reads {verdict} —",
         "{area}: {verdict}, and here is what sits behind that —",
         "Looking at {area}, the reading comes out {verdict} —",
     ]),

    # "its lagna lord Mercury is debilitated"
    (re.compile(
        r"its (?P<role>ruler of your rising sign|rising sign ruler|lord) "
        r"(?P<planet>Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu) "
        r"is (?P<state>debilitated|exalted|in a neutral sign|combust|retrograde)"),
     [
         "its {role} {planet} is {state}",
         "the planet running it, {planet}, is {state}",
         "{planet} governs this area, and it is {state}",
         "responsibility here falls to {planet}, which is {state}",
     ]),

    # "the lord sits in a strong 10th"
    (re.compile(r"the lord sits in a (?P<q>strong|weak|mixed) (?P<h>\d{1,2})(?P<o>st|nd|rd|th)"),
     [
         "the lord sits in a {q} {h}{o} house",
         "it is placed in the {h}{o} house, which is {q} ground for it",
         "you find it in the {h}{o} house — a {q} placement",
         "its seat is the {h}{o} house, and that is {q}",
     ]),

    # "1 planet exalted/own here"
    (re.compile(r"(?P<n>\d{1,2}) planets? exalted/own here"),
     [
         "{n} planets here are exalted or in their own sign",
         "{n} of the planets here are exalted or on home ground",
         "count of planets exalted or in own sign here: {n}",
         "{n} planets hold this ground, exalted or in own sign",
     ]),

    # "Honour the running Ketu antar until 7 Mar 2027"
    (re.compile(r"Honour the running (?P<planet>\w+) sub-period until (?P<when>[^.<]{4,24})"),
     [
         "Work with the {planet} sub-period while it runs, to {when}",
         "The {planet} sub-period holds until {when} — work with it, not against it",
         "Until {when} you are in {planet}'s sub-period; that sets the terms",
         "{planet} runs this sub-period to {when}",
     ]),

    # "Chapter II — Second house (wealth) Moon as 2nd lord in ..."
    (re.compile(r"(?P<planet>Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu) "
                r"as (?P<n>\d{1,2})(?P<o>st|nd|rd|th) lord"),
     [
         "{planet} as {n}{o} lord",
         "{planet}, which rules your {n}{o} house",
         "your {n}{o} house answers to {planet}",
         "{planet} carries the {n}{o} house",
     ]),
]

_PROTECTED = re.compile(r"<(script|style|code|pre)\b[^>]*>.*?</\1>", re.S | re.I)


def chart_seed(ctx: dict) -> int:
    """A stable integer for this chart — never the clock, never a counter."""
    key = "|".join(str(ctx.get(k, "")) for k in
                   ("dob", "tob", "place", "lagna", "moon_sign", "name"))
    if not key.strip("|"):
        key = str(sorted(ctx.items()))[:200]
    return int(hashlib.blake2b(key.encode(), digest_size=8).hexdigest(), 16)


def _choose(options: list[str], seed: int, skeleton_id: int, nth: int) -> str:
    """Pick a variant deterministically, and avoid repeating the last one.

    Mixing the occurrence index into the hash is what makes consecutive lines
    differ; mixing the chart seed is what makes the whole thing reproducible.
    """
    # Rotate rather than re-hash per occurrence. Hashing each occurrence
    # independently let the same variant land twice in a row (5 repeats only
    # dropped to 3 distinct); rotating guarantees consecutive lines differ,
    # while the chart-derived base keeps the whole sequence reproducible.
    base = int(hashlib.blake2b(f"{seed}:{skeleton_id}".encode(),
                               digest_size=8).hexdigest(), 16)
    return options[(base + nth) % len(options)]


def vary(html: str, ctx: dict | None = None) -> str:
    """Rewrite repeated skeletons so the reader stops seeing the template."""
    seed = chart_seed(ctx or {})
    counters: dict[int, int] = {}

    def convert(text: str) -> str:
        for skeleton_id, (pattern, options) in enumerate(VARIANTS):
            def sub(m: re.Match) -> str:
                nth = counters.get(skeleton_id, 0)
                counters[skeleton_id] = nth + 1
                # Only vary once the template has actually repeated — a single
                # occurrence is not a pattern the reader can notice, and
                # rewriting it gains nothing.
                if nth == 0:
                    return m.group(0)
                template = _choose(options, seed, skeleton_id, nth)
                try:
                    return template.format(**m.groupdict())
                except (KeyError, IndexError):
                    return m.group(0)
            text = pattern.sub(sub, text)
        return text

    out, pos = [], 0
    for block in _PROTECTED.finditer(html):
        out.append(_outside(html[pos:block.start()], convert))
        out.append(block.group(0))
        pos = block.end()
    out.append(_outside(html[pos:], convert))
    return "".join(out)


def _outside(chunk: str, fn: Callable[[str], str]) -> str:
    parts = re.split(r"(<[^>]+>)", chunk)
    return "".join(p if p.startswith("<") else fn(p) for p in parts)


def repetition_score(text: str) -> dict:
    """How template-y does this read? Used by the tests, not by the product."""
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) >= 6]
    skeletons: dict[str, int] = {}
    for s in sentences:
        k = re.sub(r"\d+", "#", s)
        k = re.sub(r"\b(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\b",
                   "P", k)
        k = re.sub(r"\s+", " ", k)[:80]
        skeletons[k] = skeletons.get(k, 0) + 1
    worst = max(skeletons.values(), default=0)
    return {"sentences": len(sentences), "distinct": len(skeletons),
            "worst_repeat": worst}
