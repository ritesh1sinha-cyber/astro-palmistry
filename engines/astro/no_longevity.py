"""No lifespan claims reach a customer. Ever.

The engines can compute longevity — `astro_palmistry_longevity` puts a life
line on an 80-year scale, `longevity_analysis` produces a maraka-based span, and
the 8th-house material is threaded through the divisional and Ashtakavarga
lanes. All of it is classically legitimate and none of it is ours to say.

Two reasons, and the commercial one is not the important one:

* A person who reads "~52 years (range 45-59)" about themselves cannot unread
  it. We have no way to follow up, no clinician in the loop, and no legitimate
  claim to that kind of authority over someone's fear.
* It is also indefensible on the numbers. The same engines disagree with each
  other about a span by a decade, which is fine for an analyst weighing
  testimony and unacceptable as a sentence handed to a stranger.

The 8th-house signal is not discarded, because it is real. It is converted:
a difficult period becomes **"a health concern is indicated around <window>"**
paired with a remedy and a suggestion to get checked. That keeps the useful
information — a window worth being careful in — and drops the part nobody should
be told by software.

This module is a chokepoint, not a convention. `scrub()` runs over every string
that leaves a renderer, and `selftest()` proves it strips the real output of the
longevity engines rather than a mock-up of it.
"""

from __future__ import annotations

import re
from typing import Any

#: The tradition's own death vocabulary, reworded rather than deleted.
#:
#: A lane sweep across seven lanes and seven charts found 24 claims carrying
#: death vocabulary that this module was blind to, because it only knew the
#: English word "longevity". Three phrases reached the reader intact:
#:
#:     "The Moon is the prime killer but will give these results..."
#:     "The strongest life-risk lords for your rising sign are..."
#:     "...no strict Mrityu Bhaga degree hits at birth"
#:
#: And where the old `\bmaraka\b[^.;]*` rule DID fire it deleted to the end of
#: the clause, so "Peak maraka configuration - maximum health vigilance and
#: upaya" became "Peak." — the warning gone and the useful advice with it. That
#: is the opposite of the instruction, which was to convert an 8th-house signal
#: into a health-awareness window plus a remedy.
#:
#: So: reword the vocabulary, and reserve deletion for claims that are
#: genuinely about a span (numbers, ages, "will die"). Order matters — these run
#: before BANNED, so a reworded sentence is no longer a candidate for deletion.
#: "Sensitive degree" is the standard neutral rendering of Mrityu Bhaga, and is
#: already the wording the longevity lane uses elsewhere.
REWORD = [
    (r"\bmaraka[-\s]awareness\b", "health-awareness"),
    (r"\bmaraka\s+configuration\b", "health-sensitive configuration"),
    (r"\bmaraka\s+(lords?|planets?|periods?)\b", r"health-sensitive \1"),
    (r"\bmaraka\b", "health-sensitive"),
    (r"\bmarana[-\s]karaka\b", "health-sensitive indicator"),
    (r"\bmarana\b", "health-sensitive"),
    # Match the trailing noun too, or "Mrityu Bhaga degree hits" rewrites to
    # "sensitive degree degree hits".
    (r"\bmrityu\s+bhaga\s+degrees?\b", "sensitive degree"),
    (r"\bmrityu\s+bhaga\b", "sensitive degree"),
    (r"\bmrityu\b", "sensitive-degree"),
    (r"\blife[-\s]risk\s+(lords?|planets?|periods?)\b", r"health-sensitive \1"),
    (r"\blife[-\s]risk\b", "health-sensitive"),
    (r"\bprime\s+killers?\b", "prime health-sensitive lord"),
    (r"\bthe\s+killers?\b", "the health-sensitive lord"),
    (r"\bkiller\s+(lords?|planets?)\b", r"health-sensitive \1"),
    (r"\bkillers?\b", "health-sensitive lord"),
    (r"\bbadhaka(sthana)?\b", "obstruction point"),
    (r"\bkhara\b", "difficult"),
]
_REWORD = [(re.compile(p, re.I), r) for p, r in REWORD]

#: Phrases that must never survive. Ordered longest-first so the specific
#: patterns win before the general ones widen.
BANNED = [
    # explicit spans
    r"\b(?:approximately\s+|about\s+|~\s*)?\d{2,3}\s*(?:-|–|to)\s*\d{2,3}\s*years?\b(?=[^a-z]|$)",
    r"\b(?:life\s*(?:span|expectancy)|lifespan)\b[^.;]*",
    r"\blongevity\s*(?:estimate|confluence|span|range|verdict)?\b[^.;]*",
    r"\bkalpayu\b[^.;]*", r"\bpoornayu\b[^.;]*", r"\bmadhyayu\b[^.;]*",
    r"\balpayu\b[^.;]*",
    # NOTE: `maraka` is handled by REWORD above, which keeps the window and the
    # remedy. Deleting to the end of the clause here destroyed both.
    r"\b(?:expected|estimated|probable)\s+(?:age|years)\s+(?:of\s+)?(?:death|passing|end)\b[^.;]*",
    r"\b(?:date|time|year)\s+of\s+death\b[^.;]*",
    r"\bwill\s+(?:die|pass\s+away|not\s+survive)\b[^.;]*",
    r"\bdeath\b[^.;]*",
    r"\blife\s*line\s+(?:ends|terminates|stops|reaches)\b[^.;]*",
    r"\bfatal\b[^.;]*", r"\bmortal(?:ity)?\b[^.;]*",
    r"\bsurviv(?:al|es|e)\s+(?:to|until|past)\b[^.;]*",
    r"~\s*\d{2,3}\s*years?\b",
    # A bare range in this context is still a lifespan claim. My first pass
    # left "Confluence estimate: (range 45-59)." standing, because the digit
    # check only looked for a number next to the word "years".
    r"\(?\s*range\s*:?\s*\d{2,3}\s*(?:-|–|to)\s*\d{2,3}\s*\)?",
    r"\b\d{2,3}\s*(?:-|–)\s*\d{2,3}\b(?=\s*(?:\)|\.|,|$))",
    r"\b(?:confluence\s+)?estimate\b\s*:?\s*(?=[.,)]|$)",
    r"\b-?\s*\d{1,3}\s*yr\b",
    r"\b\d{2,3}\s*-?\s*year\s+(?:scale|span|life)\b",
    # softer leaks
    r"\bhow\s+long\s+you\s+(?:will\s+)?live\b[^.;]*",
    r"\bend\s+of\s+life\b[^.;]*",
]
_BANNED = [re.compile(p, re.I) for p in BANNED]

#: Words that are fine on their own but must not be used to imply a span.
SOFTEN = [
    (re.compile(r"\bLongevity\b"), "Resilience"),
    (re.compile(r"\blongevity\b"), "resilience"),
]


def _match_case(m: "re.Match[str]", replacement: str) -> str:
    """Expand a REWORD replacement, preserving the original's capitalisation.

    Without this, "Maraka lord Saturn activates..." at the start of a sentence
    becomes "health-sensitive lord Saturn activates..." — lower-case mid-report,
    which reads as a bug to anyone paying attention.
    """
    out = m.expand(replacement)
    original = m.group(0)
    if original[:1].isupper() and out[:1].islower():
        out = out[:1].upper() + out[1:]
    return out


def scrub(text: Any) -> str:
    """Remove any lifespan claim, then tidy what the removal left behind."""
    if text is None:
        return ""
    out = str(text)
    # Reword the tradition's death vocabulary BEFORE the deleting patterns run,
    # so a sentence that can be saved is saved.
    for pat, rep in _REWORD:
        out = pat.sub(lambda m, _r=rep: _match_case(m, _r), out)
    for pat, rep in SOFTEN:
        out = pat.sub(rep, out)
    for pat in _BANNED:
        out = pat.sub("", out)
    # a removal mid-sentence leaves debris; a half-sentence reads worse than
    # the claim did, so collapse it rather than shipping the wreckage
    out = re.sub(r"\s*\(\s*\)", "", out)
    out = re.sub(r"\s*\[\s*\]", "", out)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+([,.;:])", r"\1", out)
    out = re.sub(r"(?:[,;:]\s*){2,}", ", ", out)
    out = re.sub(r"^\s*[,;:.\-–—]\s*", "", out)
    out = re.sub(r"\.\s*\.", ".", out)
    # A reworded phrase can abut the noun it replaced. Only collapse the words
    # this module introduces — a blanket dedup would eat legitimate English.
    out = re.sub(r"\b(degree|lord|health-sensitive)(\s+\1)+\b", r"\1", out,
                 flags=re.I)
    # Sentences that lost their subject. Must not touch a decimal point: this
    # rule used to rewrite "21.5 of 36" as "21. 5 of 36" and "1.5x" as "1. 5x",
    # which only showed up once scrub() started running over whole documents
    # rather than single sentences. Require a non-digit on BOTH sides.
    out = re.sub(r"(?<![A-Za-z0-9])\.(?!\d)\s*", ". ", out)
    return out.strip()


def concerns_to_windows(rows: list) -> list:
    """Turn a longevity/8th-house finding into a health-concern window.

    The information worth keeping is "be careful in this window and get
    checked". The information to drop is any number of years. Each row needs
    `start`, `end` and optionally `because`; the caller supplies the remedy.
    """
    out = []
    for r in rows or []:
        start, end = r.get("start"), r.get("end")
        if not (start and end):
            continue
        because = scrub(r.get("because") or "")
        out.append({
            "start": start, "end": end,
            "text": ("A health concern is indicated in this window. "
                     "Treat it as a period for check-ups and rest rather than "
                     "pushing harder."),
            "because": because,
            "remedy": r.get("remedy") or
                      "Keep the routine boring: sleep, food at fixed hours, and "
                      "one medical check you have been postponing.",
        })
    return out


def selftest() -> int:
    """Prove it strips the real output shape of the longevity engines."""
    cases = [
        "Confluence estimate: ~52 years (range 45-59).",
        "Palm life-line reach suggests ~64 years on the 80-year scale.",
        "Jupiter@8 (8th anchor): -8 yr kalpayu stress per book",
        "Maraka lord Saturn activates in the 2035 window.",
        "Longevity: madhyayu, 56-72 years.",
        "The life line ends at age 61 with a fork.",
        "Expected age of death 74.",
        "Longevity, legacies, sudden events",
    ]
    bad = 0
    print("longevity scrub")
    for c in cases:
        got = scrub(c)
        leak = any(p.search(got) for p in _BANNED)
        # a bare number surviving is also a leak in this context
        # Stricter: ANY two- or three-digit number surviving in a scrubbed
        # longevity string is a leak, whatever word follows it.
        digits = re.search(r"\b\d{2,3}\b", got)
        ok = not leak and not digits
        print(f"  {'pass' if ok else 'FAIL'}  {c[:52]!r:<56} -> {got[:46]!r}")
        bad += 0 if ok else 1

    keep = "A health concern is indicated around July 2030 to November 2031."
    if scrub(keep) != keep:
        print(f"  FAIL  health-concern wording was altered: {scrub(keep)!r}")
        bad += 1
    else:
        print("  pass  health-concern wording survives untouched")

    print(f"\n{len(cases) + 1 - bad} passed, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    import sys
    sys.exit(selftest())
