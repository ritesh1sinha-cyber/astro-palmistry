#!/usr/bin/env python3
"""Lane-level regression tests from the overfitting sweep.

Run:  PYJHORA_SRC=... python3 engines/astro/lane_sweep_test.py

Sweeping every lane collector on the development chart and on random charts
found no lane fitted the way the anchor engine's tables were — counts and
differentiation held up. It found four other things instead, and these tests
pin each of them:

  1. The Bhardwaj lane returned ZERO claims for every chart, including the
     development chart, because sentence-transformers is absent and the lexical
     fallback was installed on the HTML path but not on the confluence path. The
     nine-method vote had been running with eight.
  2. `no_longevity` knew the English word "longevity" but none of the
     tradition's death vocabulary, so "The Moon is the prime killer",
     "life-risk lords" and "Mrityu Bhaga" reached the reader intact. And where
     it did fire it deleted to the end of the clause, destroying the health
     window it was supposed to preserve.
  3. Two lanes named their source book to the reader ("The handbook tale ... is
     metaphorical folklore", "Book OCR longevity scan").
  4. The birth-star lane appended a clause written for one specific tale —
     "skilled hands and comfort do not excuse broken trust or hidden debt" — to
     7 of 7 charts, and dropped a third-person male moral into the reading as
     if it described the reader.

These run on synthetic text where possible so the suite stays fast; the two
that need a real chart are marked and skip cleanly without an ephemeris.
"""
from __future__ import annotations

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import _py39_shim  # noqa: E402,F401

PASS: list[str] = []
FAIL: list[str] = []
SKIP: list[str] = []

DEATH = re.compile(
    r"\b(longevity|lifespan|life ?span|life-risk|maraka|marana|kalpayu|alpayu|"
    r"madhyayu|purnayu|mrityu|killer|fatal|death|dying|dies)\b", re.I)
SOURCE = re.compile(
    r"\b(handbook|book ocr|per book|book says|metaphorical folklore|"
    r"not literal history|OCR)\b", re.I)


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'} {name}"
          + (f"\n       {detail}" if detail and not cond else ""))


def shown(text: str) -> str:
    """What the reader actually sees: leak strip, then the longevity chokepoint."""
    import astro_voice as AV
    from no_longevity import scrub
    out = scrub(AV.strip_leaks(text or ""))
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", out)).strip()


# ---------------------------------------------------------------------------
print("\n— 1. the tradition's death vocabulary never reaches the reader —")
# These are verbatim from the lane sweep, not invented.
REAL_LEAKS = [
    "Classical note for your rising sign: The Moon is the prime killer but will "
    "give these results by association.",
    "The strongest life-risk lords for your rising sign are the rulers of the "
    "second and seventh life areas (Saturn and Moon in the technical map).",
    "Peak maraka configuration - maximum health vigilance and upaya.",
    "Moderate maraka-awareness window (Jul 2030 - Nov 2031 onward) when Rahu "
    "leads the sub-chapter - keep health routines firm; this is prudence.",
    "Book OCR longevity scan finds no strict Mrityu Bhaga degree hits at birth.",
    "Maraka lord Saturn activates in the 2035 window.",
    "Confluence estimate: ~52 years (range 45-59).",
    "Expected age of death 74.",
]
for i, raw in enumerate(REAL_LEAKS):
    out = shown(raw)
    m = DEATH.search(out)
    check(f"leak {i + 1} neutralised", not m,
          f"{m.group(0) if m else ''} survived in: {out[:90]}")

print("\n— 2. rewording preserves the window and the advice —")
w = shown("Moderate maraka-awareness window (Jul 2030 - Nov 2031 onward) when "
          "Rahu leads the sub-chapter - keep health routines firm; this is "
          "prudence, not a crisis.")
check("the dated window survives the scrub", "2030" in w and "2031" in w, w[:110])
check("the advice survives the scrub", "health routines" in w, w[:110])
check("it now reads as health awareness", "health-awareness" in w.lower(), w[:110])
adv = shown("Peak maraka configuration - maximum health vigilance and upaya.")
check("advice is not deleted with the banned word",
      "health vigilance" in adv, adv[:110])
check("capitalisation is preserved at sentence start",
      shown("Maraka lord Saturn activates in the 2035 window.").startswith("Health"),
      shown("Maraka lord Saturn activates in the 2035 window."))
check("no duplicated word artefact",
      "degree degree" not in shown(
          "Mrityu Bhaga degree hits at birth.").lower())

print("\n— 3. no source book is named to the reader —")
for i, raw in enumerate([
    'Your birth star is Hasta (1st pada). The handbook tale "Intricacies of '
    'Karma: The Goldsmith\'s Journey" is metaphorical folklore, not literal '
    'history. The story turns on trust.',
    "Book OCR longevity scan finds no strict degree hits at birth.",
    "The handbook says Saturn rules the 10th here.",
]):
    out = shown(raw)
    m = SOURCE.search(out)
    check(f"source reference {i + 1} removed", not m,
          f"{m.group(0) if m else ''} in: {out[:90]}")
check("the fact survives the source strip",
      "Hasta (1st pada)" in shown(
          'Your birth star is Hasta (1st pada). The handbook tale "X" is '
          'metaphorical folklore, not literal history.'))
check("article capitalisation is not corrupted mid-sentence",
      "As the tradition holds" in shown("As the handbook says, Saturn rules."),
      shown("As the handbook says, Saturn rules."))

print("\n— 4. the birth-star lesson is derived, not one tale's moral —")
import nakshatra_human as NH  # noqa: E402

src = open(os.path.join(_HERE, "nakshatra_human.py")).read()
# Strip comment lines before grepping: the clause is deliberately quoted in a
# comment explaining why it was removed, and that documentation is worth more
# than the convenience of a naive substring check.
code = "\n".join(ln for ln in src.splitlines()
                 if not ln.lstrip().startswith("#"))
check("the goldsmith clause is gone from emitted prose",
      "skilled hands and comfort do not excuse" not in code)
check("it survives only as a comment explaining the removal",
      "skilled hands and comfort do not excuse" in src)
check("a per-theme lesson table exists", hasattr(NH, "_LESSON"))
check("every theme tag has its own lesson",
      set(NH._LESSON) == set(NH._HABITS),
      f"lesson-only={set(NH._LESSON) - set(NH._HABITS)} "
      f"habit-only={set(NH._HABITS) - set(NH._LESSON)}")
check("the lessons are all distinct",
      len(set(NH._LESSON.values())) == len(NH._LESSON))
check("the tale's moral is framed as the tale's, not the reader's",
      "In the tale itself:" in src)
check("no OCR wording in the pada note", "OCR gap" not in src)

# ---------------------------------------------------------------------------
print("\n— 5. every lane votes (needs an ephemeris) —")
try:
    import astro_precompute
    import lane_collectors as LC
    sys.path[:0] = [os.path.dirname(os.path.dirname(_HERE)),
                    os.path.dirname(_HERE)]
    pc = astro_precompute.resolve_precompute(
        "T", "1991-06-23", birth_time="04:40", latitude=19.0760,
        longitude=72.8777, timezone=5.5, place_name="Mumbai", gender=1)
except Exception as e:                                               # noqa: BLE001
    SKIP.append("lane counts")
    print(f"  skip  lane counts — no ephemeris available ({type(e).__name__})")
    pc = None

if pc:
    claims, meta = LC.collect_all_lanes("", "T", "1991-06-23", pc)
    # The Bhardwaj lane returning 0 was invisible for exactly this reason: an
    # empty lane looks like "nothing to say" rather than "never ran".
    check("Bhardwaj lane produces claims", meta.get("Bhardwaj", 0) > 0,
          f"meta={meta}")
    for lane in ("BNN", "KP", "Mehta", "Jaimini", "Bhardwaj"):
        check(f"{lane} lane is non-empty", meta.get(lane, 0) > 0,
              f"{lane}={meta.get(lane)} err={meta.get(lane + '_error', '')}")
    check("no lane raised", not [k for k in meta if k.endswith("_error")],
          str({k: v for k, v in meta.items() if k.endswith("_error")}))
    bad = [c.text[:70] for c in claims if DEATH.search(shown(c.text))]
    check("no death vocabulary in any lane claim as shown", not bad,
          f"{len(bad)}: {bad[:2]}")
    bad2 = [c.text[:70] for c in claims if SOURCE.search(shown(c.text))]
    check("no source reference in any lane claim as shown", not bad2,
          f"{len(bad2)}: {bad2[:2]}")

print(f"\n{len(PASS)} passed, {len(FAIL)} failed, {len(SKIP)} skipped")
if FAIL:
    print("FAILED: " + ", ".join(FAIL))
sys.exit(1 if FAIL else 0)
