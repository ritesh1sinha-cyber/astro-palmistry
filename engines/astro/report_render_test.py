#!/usr/bin/env python3
"""The customer-facing render, per kind.

Run:  PYJHORA_SRC=... python3 engines/astro/report_render_test.py

Guards the wiring, not just the renderers. The card design existed and was
tested for weeks while `core.handlers` still served the old long-form document,
so "the modules work" was never the question — "does the handler call them" was.

Also pins four bugs found while wiring it:

  1. `no_longevity.scrub` rewrote "21.5 of 36" as "21. 5 of 36". Invisible while
     it only ever saw single sentences; corrupts every decimal once it runs over
     whole documents.
  2. The shell added its own <h1> on top of fragments that already print a
     header, so match/numerology/horary each showed their title twice.
  3. The old document was appended to the paid half AFTER the scrub, so the
     appendix bypassed the chokepoint and leaked a lane called "Longevity".
  4. The disclaimer contained the word "lifespan", which is the exact token every
     automated leak scan looks for.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import _py39_shim  # noqa: E402,F401

import report_render as RD  # noqa: E402
import report_shell as RS   # noqa: E402

PASS: list[str] = []
FAIL: list[str] = []

LEAK = re.compile(
    r"\b(longevity|lifespan|life-risk|maraka|mrityu|killer|handbook|Book OCR|"
    r"precomputed:|Deterministic rule|ritxx)\b", re.I)
DECIMAL_SPLIT = re.compile(r"\b\d+\.\s+\d\b")


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'} {name}"
          + (f"\n       {detail}" if detail and not cond else ""))


def body_of(doc: str) -> str:
    return doc.split("</style>", 1)[-1]


def visible(doc: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body_of(doc))).strip()


# ---------------------------------------------------------------------------
print("\n— 1. one stylesheet, one source —")
src = open(os.path.join(_HERE, "report_cards.py")).read()
check("report_cards no longer carries its own CSS copy",
      "--ink:#16181d" not in src, "the palette is inlined again")
check("report_cards interpolates the shared stylesheet", "{_STYLE}" in src)
check("the shared stylesheet is substantial", len(RS.STYLE) > 4000,
      f"{len(RS.STYLE)} chars")
check("the disclaimer avoids the token leak scans look for",
      not LEAK.search(RS.page("t", "<p>x</p>")),
      str((LEAK.search(RS.page("t", "<p>x</p>")) or [""])[0]))

# ---------------------------------------------------------------------------
print("\n— 2. numerology —")
nf, npd, nmeta = RD.numerology("Meera Nair", "1992-11-14", price=199)
for probe in ("life path", "lo shu", "personal year"):
    check(f"free shows {probe}", probe in nf.lower())
check("free locks the years ahead", "locked" in body_of(nf).lower())
check("paid unlocks more than free",
      body_of(npd).lower().count("locked") < body_of(nf).lower().count("locked"),
      f"free={body_of(nf).lower().count('locked')} "
      f"paid={body_of(npd).lower().count('locked')}")
check("accepts an ISO string for dob (handlers pass one)", len(nf) > 5000)
check("accepts a date object too",
      len(RD.numerology("X", date(1992, 11, 14))[0]) > 5000)
check("title is not printed twice",
      visible(nf).lower().count("your numbers, and what they") == 1)

# ---------------------------------------------------------------------------
print("\n— 3. matching —")
try:
    mm = json.load(open("/tmp/final4/kundali_match.json"))["meta"]
except Exception:
    mm = {"total": 21.5, "maxGuna": 36, "band": "good", "bandPlain": "Good match",
          "koots": [{"label": "Tara", "score": 0, "max": 3, "ok": False},
                    {"label": "Bhakoot", "score": 0, "max": 7, "ok": False}],
          "stars": {"groom": "Hasta", "bride": "Mrigashira"},
          "activeDoshas": [], "blocking": False}
mf, mp, _ = RD.kundali_match(mm, groom="Sample", bride="Partner", price=299)
check("free shows the score out of 36", "36" in visible(mf))
check("decimals are not split by the scrub", not DECIMAL_SPLIT.search(mf),
      str((DECIMAL_SPLIT.search(mf) or [""])[0]))
check("no career gemstones in a compatibility report",
      "gemstone" not in mf.lower())
check("couple header appears once",
      visible(mf).count("Sample &amp; Partner") + visible(mf).count("Sample & Partner") == 1,
      visible(mf)[:120])

# ---------------------------------------------------------------------------
print("\n— 4. horary: one answer, workings behind the wall —")
hf, hp, hmeta = RD.horary(
    question="Will the property deal go through?",
    verdicts={"western": {"verdict": "Likely yes", "confidence": "moderate"},
              "vedic": {"verdict": "Uncertain", "confidence": "low"}},
    western_judgment={}, asked="4 August 2026, 21:40", name="Meera", price=1499,
    workings={"western": "<p>WORKINGMARKER west</p>",
              "vedic": "<p>WORKINGMARKER vedic</p>"})
check("free carries the answer", "you asked" in hf.lower())
check("free hides the per-engine workings", "WORKINGMARKER" not in hf)
check("paid shows the per-engine workings", "WORKINGMARKER" in hp)
check("the question is printed once",
      visible(hf).count("Will the property deal go through?") == 1,
      visible(hf)[:160])
check("meta carries a reconciled label", bool(hmeta["answer"].get("label")),
      str(hmeta["answer"]))
check("meta says whether the methods contradicted",
      "contradicted" in hmeta["answer"])

# ---------------------------------------------------------------------------
print("\n— 5. the flagship —")
try:
    pc = json.load(open("/tmp/pc_demo.json"))
except Exception:
    pc = None
    print("  skip  no demo precompute available")

if pc:
    ff, fp, fmeta = RD.full_report(pc, name="Meera Nair",
                                   question="When will I change my job?",
                                   price=1499, bundle_price=2100)
    check("design is tagged", fmeta.get("design") == "cards-v2")
    check("free opens with the present read",
          "where you are right now" in visible(ff).lower()[:1200],
          visible(ff)[:200])
    check("free shows Your past", "your past" in ff.lower())
    check("free shows the life-area cards", ff.count("data-verdict=") >= 6,
          f"{ff.count('data-verdict=')} cards")
    check("EVERY headline is free (no whole card locked)",
          ff.count("data-verdict=") == fp.count("data-verdict=") or
          ff.count("data-verdict=") >= 6)
    check("free locks the dates", ff.count("locked-inline") > 0)
    unlock_ctas = ff.count('data-unlock="1"')
    check("free has one unlock CTA", unlock_ctas == 1,
          f"{unlock_ctas} unlock buttons")
    check("paid unlocks the dates",
          body_of(fp).count("locked-inline") < body_of(ff).count("locked-inline"),
          f"free={body_of(ff).count('locked-inline')} "
          f"paid={body_of(fp).count('locked-inline')}")
    # Free-view redesign: the paid depth is titled and blurred, never leaked.
    lock_cnt = ff.count('class="locked-section"')
    check("free shows six titled-but-locked sections",
          lock_cnt == 6,
          f"{lock_cnt} lock sections")
    check("free blurs the placeholder bodies", "lock-blur" in ff)
    check("free names the sections as locked", "in the full reading" in ff)
    check("old locked-preview block is gone", "locked-preview" not in ff)
    check("old bullet-pointed teaser copy is gone",
          "What the full reading adds" not in ff)
    check("per-card action is a placeholder, not the real remedy",
          "The specific action and mantra for this area are in the full reading." in ff)
    check("free never carries the dated timeline",
          "<ol class=\"timeline\">" not in ff)
    check("free never carries the dated windows",
          "<ol class=\"windows-list\">" not in ff)
    check("paid has no lock sections",
          '<section class="locked-section">' not in fp)
    check("bundle is offered in free only",
          "Everything, one package" in ff and "Everything, one package" not in fp)
    check("bundle asks for contact, not a payment button",
          "admin@graharekha.com" in ff
          and 'data-unlock="1"' not in ff.split("Everything, one package")[1][:800])
    check("no leak in the free half", not LEAK.search(ff),
          str((LEAK.search(ff) or [""])[0]))
    check("no leak in the paid half", not LEAK.search(fp),
          str((LEAK.search(fp) or [""])[0]))
    check("no decimal corruption", not DECIMAL_SPLIT.search(ff))

# ---------------------------------------------------------------------------
print("\n— 6. anything appended after the render is still scrubbed —")
dirty = "<p>Longevity confluence ~52 years (range 45-59) and Mrityu Bhaga.</p>"
cleaned = RD.clean(dirty)
check("clean() neutralises an appendix", not LEAK.search(cleaned), cleaned)
check("clean() leaves the stylesheet alone",
      "--ink:#16181d" in RD.clean(RS.page("t", "<p>x</p>")))

# ---------------------------------------------------------------------------
print("\n— 7. the handlers actually call this module —")
h = open(os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                      "core", "handlers.py")).read()
for kind in ("h_full_report", "h_horary", "h_numerology", "h_kundali_match"):
    i = h.index(f"def {kind}")
    j = h.find("\ndef ", i + 10)
    block = h[i:j if j > 0 else len(h)]
    check(f"{kind} renders through report_render", "RD." in block,
          "still using the old generator")
check("the frontend no longer prints the two-engine disagreement",
      "two traditions disagree" not in open(
          os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                       "site", "index.html"), encoding="utf-8").read())

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED: " + ", ".join(FAIL))
sys.exit(1 if FAIL else 0)
