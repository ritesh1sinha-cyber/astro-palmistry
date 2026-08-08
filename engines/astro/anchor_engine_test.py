#!/usr/bin/env python3
"""Tests that the anchor engine is not fitted to any one chart.

Run:  PYJHORA_SRC=... python3 engines/astro/anchor_engine_test.py

The old version keyed its prose off a table of nine (planet, house) pairs that
happened to be one test subject's placements. It fired 9/9 for him and 5/108
across twelve random charts, and where it did fire for a stranger it asserted
the original chart's dignities and co-tenants as if they were theirs.

These tests encode the properties that failure violated:

  1. COVERAGE PARITY   — every chart gets fully composed readings, and no chart
                         is privileged over another.
  2. NO ASSERTED FACTS — a reading never claims a dignity, sign, or co-tenancy
                         the chart does not contain.
  3. DIFFERENTIATION   — two charts must not produce the same text.
  4. NO LONGEVITY      — lifespan language cannot appear.
  5. RELATIONS ARE TRUE — a derived "conjunct/opposite/trine" claim matches the
                         actual house geometry.

Test 2 is the one that matters most: it is the check the old design could not
have passed, and it is checked against every fired statement rather than a
sample.
"""
from __future__ import annotations

import os
import random
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import _py39_shim  # noqa: E402,F401

import astro_palmistry_anchor_engine as AE  # noqa: E402

PASS: list[str] = []
FAIL: list[str] = []

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
           "Rahu", "Ketu"]
DIGNITIES = list(AE.DIGNITY.keys())


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'} {name}"
          + (f"\n       {detail}" if detail and not cond else ""))


def synth_chart(rnd: random.Random) -> dict[str, dict]:
    """A synthetic chart. Synthetic is correct here: we are testing that the
    engine holds for ARBITRARY placements, including combinations an ephemeris
    would rarely produce."""
    return {
        p: {"house": rnd.randint(1, 12), "sign": rnd.choice(SIGNS),
            "dignity": rnd.choice(DIGNITIES)}
        for p in PLANETS
    }


def all_text(analysis: dict) -> list[str]:
    out: list[str] = []
    for a in analysis["anchors"]:
        out += [a["palm"], a["life"], a.get("chart_link", "")]
        for s in a["sub_planets"]:
            out += [s["palm"], s["life"], s.get("relative_to_anchor", "")]
    return [t for t in out if t]


# ---------------------------------------------------------------------------
print("\n— 1. the overfitted tables are gone —")
check("MAIN_LINE is empty", AE.MAIN_LINE == {})
check("SUB_PLANET is empty", AE.SUB_PLANET == {})
check("RELATIVE_SUB is empty", AE.RELATIVE_SUB == {})
src = open(os.path.join(_HERE, "astro_palmistry_anchor_engine.py")).read()
body = src.split('"""', 2)[-1]        # skip the module docstring
check("no hardcoded Jupiter@8 branch outside comments",
      not re.search(r'^\s*[^#\n]*"Jupiter".{0,12}==?.{0,6}8', body, re.M))
check("no hardcoded Ketu@5 branch",
      not re.search(r'^\s*[^#\n]*"Ketu".{0,12}==?.{0,6}5', body, re.M))

# ---------------------------------------------------------------------------
print("\n— 2. coverage parity across charts —")
rnd = random.Random(11)
charts = [synth_chart(rnd) for _ in range(40)]
REF_CHART = {  # reference chart the old tables were fitted to
    "Moon": {"house": 4, "sign": "Virgo", "dignity": "neutral_sign"},
    "Ketu": {"house": 5, "sign": "Libra", "dignity": "neutral_sign"},
    "Saturn": {"house": 6, "sign": "Scorpio", "dignity": "enemy_sign"},
    "Jupiter": {"house": 8, "sign": "Capricorn", "dignity": "debilitated"},
    "Sun": {"house": 9, "sign": "Aquarius", "dignity": "neutral_sign"},
    "Mercury": {"house": 10, "sign": "Pisces", "dignity": "debilitated"},
    "Venus": {"house": 10, "sign": "Pisces", "dignity": "exalted"},
    "Mars": {"house": 11, "sign": "Aries", "dignity": "moolatrikona"},
    "Rahu": {"house": 11, "sign": "Aries", "dignity": "neutral_sign"},
}

built = [AE.build_anchor_analysis(c, "Gemini") for c in charts]
r_built = AE.build_anchor_analysis(REF_CHART, "Gemini")

check("every chart yields one anchor per planet",
      all(len(b["anchors"]) == 9 for b in built))
check("every anchor has a composed palm reading",
      all(len(a["palm"]) > 40 for b in built for a in b["anchors"]))
check("every anchor has a composed life reading",
      all(len(a["life"]) > 60 for b in built for a in b["anchors"]))
check("every sub-planet has a derived relation",
      all(s.get("relative_to_anchor") for b in built for a in b["anchors"]
          for s in a["sub_planets"]))

# The old failure mode, restated as a test: the privileged chart must not get
# systematically more text than a random one.
r_len = sum(len(t) for t in all_text(r_built))
avg = sum(sum(len(t) for t in all_text(b)) for b in built) / len(built)
ratio = r_len / avg
check("the once-privileged chart gets no more text than average",
      0.8 <= ratio <= 1.25, f"ratio {ratio:.2f} (was effectively unbounded)")

# ---------------------------------------------------------------------------
print("\n— 3. no reading asserts a fact the chart lacks —")
DIG_WORDS = {
    "exalted": "exalted", "debilitated": "debilitated",
    "moolatrikona": "moolatrikona", "own sign": "own_sign",
}
bad: list[str] = []
for c, b in zip(charts + [REF_CHART], built + [r_built]):
    for a in b["anchors"]:
        blob = " ".join([a["palm"], a["life"], a.get("chart_link", "")])
        for word, dig in DIG_WORDS.items():
            if word in blob.lower() and a["dignity"] != dig:
                bad.append(f"{a['planet']}: text says '{word}' but dignity is "
                           f"{a['dignity']}")
        # A sign may only be named if it is this planet's sign.
        for sg in SIGNS:
            if re.search(rf"\bin {sg}\b", blob) and a["sign"] != sg:
                bad.append(f"{a['planet']}: names sign {sg}, actual {a['sign']}")
        # An ordinal house may only be named if some planet is really there.
        occupied = {int(v["house"]) for v in c.values()}
        for m in re.finditer(r"\b(\d{1,2})(?:st|nd|rd|th) house\b", blob):
            if int(m.group(1)) not in occupied:
                bad.append(f"{a['planet']}: names an empty house {m.group(1)}")
check("no false dignity / sign / house assertions in 41 charts", not bad,
      "; ".join(bad[:4]) + (f" (+{len(bad) - 4} more)" if len(bad) > 4 else ""))

# co-tenancy: text may only claim planets share a house if they do
cot: list[str] = []
for c, b in zip(charts, built):
    for a in b["anchors"]:
        for s in a["sub_planets"]:
            rel = s.get("relative_to_anchor", "")
            if "shares the" in rel and int(s["house"]) != int(a["house"]):
                cot.append(f"{a['planet']}/{s['planet']} claimed conjunct")
check("no false co-tenancy claims", not cot, "; ".join(cot[:3]))

# ---------------------------------------------------------------------------
print("\n— 4. relations match the real geometry —")
geo: list[str] = []
for c, b in zip(charts, built):
    for a in b["anchors"]:
        for s in a["sub_planets"]:
            rel = s.get("relative_to_anchor", "")
            gap = (int(s["house"]) - int(a["house"])) % 12
            if "opposite" in rel and gap != 6:
                geo.append(f"opposition claimed at gap {gap}")
            if "trine" in rel and gap not in (4, 8):
                geo.append(f"trine claimed at gap {gap}")
            if "shares the" in rel and gap != 0:
                geo.append(f"conjunction claimed at gap {gap}")
check("every derived aspect claim is geometrically true", not geo,
      "; ".join(sorted(set(geo))[:4]))

# ---------------------------------------------------------------------------
print("\n— 5. differentiation: charts must read differently —")


def sentences(analysis: dict) -> set[str]:
    out: set[str] = set()
    for t in all_text(analysis):
        for part in re.split(r"(?<=[.!?])\s+", t):
            part = part.strip()
            if len(part) > 30:
                out.add(part)
    return out


sets = [sentences(b) for b in built[:20]]
pairs, tot = 0, 0.0
for i in range(len(sets)):
    for j in range(i + 1, len(sets)):
        union = sets[i] | sets[j]
        if union:
            tot += len(sets[i] & sets[j]) / len(union)
            pairs += 1
overlap = tot / max(1, pairs)
check("mean pairwise sentence overlap stays low", overlap < 0.35,
      f"overlap {overlap:.3f}")
print(f"       mean pairwise overlap across 20 charts: {overlap:.3f}")

ident = sum(1 for i in range(len(sets)) for j in range(i + 1, len(sets))
            if sets[i] == sets[j])
check("no two charts produce identical text", ident == 0, f"{ident} identical pairs")

# ---------------------------------------------------------------------------
print("\n— 6. no longevity language anywhere —")
LIFESPAN = re.compile(
    r"\b(longevity|lifespan|life ?span|kalpayu|alpayu|madhyayu|purnayu|"
    r"years? of life|will live|death|die)\b", re.I)
hits: list[str] = []
for b in built + [r_built]:
    for t in all_text(b):
        if LIFESPAN.search(t):
            hits.append(t[:90])
check("no lifespan wording in any composed reading", not hits,
      "; ".join(hits[:3]))

# Assert the SOURCE DATA too, not only the output. no_longevity.scrub() is the
# last line of defence and it works — it rewrites "longevity" to "resilience" —
# which means a regression that put lifespan wording back into HOUSE_THEMES
# would be silently masked by the scrubber. Checking the table directly keeps
# the two layers independently verified.
check("HOUSE_THEMES itself contains no lifespan wording",
      not any(LIFESPAN.search(v) for v in AE.HOUSE_THEMES.values()),
      str({k: v for k, v in AE.HOUSE_THEMES.items() if LIFESPAN.search(v)}))
check("HOUSE_ZONE itself contains no lifespan wording",
      not any(LIFESPAN.search(" ".join(v)) for v in AE.HOUSE_ZONE.values()))
check("no HOUSE_DOMAIN maps to longevity",
      "longevity" not in AE.HOUSE_DOMAIN.values())
check("no longevity domain is emitted",
      all(a["domain"] != "longevity" for b in built for a in b["anchors"]))
check("longevity title removed", "longevity" not in AE.DOMAIN_TITLES)
check("8th-house palm zones still inspected under health",
      "h8" in AE.DOMAIN_ZONES["health"] and "life" in AE.DOMAIN_ZONES["health"])

# ---------------------------------------------------------------------------
print("\n— 7. the full pipeline still runs, with and without photos —")
zm = {"jupiter": {"readable": True, "line_count": 6, "sharpness": 71,
                  "quality": "good", "stress_lines": True, "sparse": False},
      "saturn": {"readable": False, "line_count": 0, "sharpness": 11,
                 "quality": "poor"},
      "venus": {"readable": True, "line_count": 2, "sharpness": 66,
                "quality": "fair", "stress_lines": False, "sparse": True}}
for label, metrics in (("with photos", zm), ("no photos", {})):
    a = AE.apply_cv_evidence(AE.build_anchor_analysis(charts[0], "Leo"), metrics)
    html = AE.anchor_analysis_html(a)
    ok = (len(html) > 1500 and "Line main:" in html
          and not LIFESPAN.search(html) and "Jupiter@8" not in html)
    check(f"HTML renders cleanly ({label})", ok, f"{len(html)} bytes")

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED: " + ", ".join(FAIL))
sys.exit(1 if FAIL else 0)
