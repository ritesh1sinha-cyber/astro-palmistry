#!/usr/bin/env python3
"""Regression tests for the "Ask your chart" natal question engine.

Two real bugs drove this file:

1. A question naming a house directly ("how is my 5th house") was hijacked
   by the property topic's bare `\bhouse\b` pattern and silently answered as
   a 4th-house (property) question instead. `classify()` now checks for an
   explicit house number/ordinal before it ever looks at topic keywords.
2. `render()` always used a "yes/no + date" template built for "when will
   X happen" questions, even for "how is my Nth house" style questions —
   and it computed a rich house-by-house / planet-by-planet breakdown
   (`chart_lines`) that was never actually shown to the reader. Both are
   fixed here: the heading/lead adapt to question intent, and the house
   breakdown is now rendered.

Run:  PYJHORA_SRC=... python3 engines/astro/question_answer_test.py
Chart-dependent checks are skipped (not failed) if PyJHora is unavailable.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
for p in (_ROOT, _ROOT / "engines", _HERE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
if sys.version_info < (3, 10):
    import _py39_shim  # noqa: E402,F401

import question_answer as QA  # noqa: E402

PASS: list[str] = []
FAIL: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'} {name}"
          + (f"\n       {detail}" if detail and not cond else ""))


print("— 1. an explicit house number wins over keyword guesses —")
t = QA.classify("how is my 5th house")
check("'5th house' classifies as the children/5th topic, not property",
      t.houses[0] == 5, f"got houses={t.houses}, key={t.key}")

t = QA.classify("tell me about my 5th house")
check("'tell me about my 5th house' also resolves to house 5",
      t.houses[0] == 5, f"got houses={t.houses}, key={t.key}")

t = QA.classify("what about my 9th house")
check("'9th house' resolves to house 9 (study topic)",
      t.houses[0] == 9, f"got houses={t.houses}, key={t.key}")

t = QA.classify("house number 3")
check("'house number 3' resolves to house 3 (no Topic has 3 as primary, "
      "so a generic one is built)",
      t.houses == (3,), f"got houses={t.houses}, key={t.key}")

t = QA.classify("fourth house")
check("word-form ordinal 'fourth house' resolves to house 4",
      t.houses[0] == 4, f"got houses={t.houses}, key={t.key}")

print("\n— 2. bare property/home wording is unaffected —")
t = QA.classify("will I buy a house")
check("'will I buy a house' (no number) still classifies as property",
      t.key == "property", f"got key={t.key}")

t = QA.classify("when will I get a home loan")
check("'home loan' still classifies as property",
      t.key == "property", f"got key={t.key}")

print("\n— 2b. life-area dropdown pins the topic when wording is vague —")
t = QA.classify("how are things looking for me?", area="children")
check("area=children + vague question → children topic",
      t.key == "children" and t.houses[0] == 5,
      f"got key={t.key} houses={t.houses}")

t = QA.classify("how are things looking for me?", area="property")
check("area=property + vague question → property topic",
      t.key == "property" and t.houses[0] == 4,
      f"got key={t.key} houses={t.houses}")

t = QA.classify("will I get a promotion?", area="career")
check("area=career + 'promotion' refines to promotion topic",
      t.key == "promotion", f"got key={t.key}")

t = QA.classify("how is my 5th house", area="property")
check("explicit '5th house' still beats a mismatched area dropdown",
      t.houses[0] == 5, f"got houses={t.houses}")

print("\n— 3. question intent is detected —")
for q, expect in [
    ("how is my 5th house", "how"),
    ("when will I get promoted", "when"),
    ("will I buy a house", "yesno"),
    ("how many children will I have", "amount"),
    ("how will my career be", "how"),
]:
    got = QA._intent(q)  # noqa: SLF001
    check(f"intent({q!r}) == {expect!r}", got == expect, f"got {got!r}")

print("\n— 4. house-for-arbitrary-house-number topic is sane —")
# House 8 has no dedicated Topic primary (legal owns 6, foreign owns 12).
topic8 = QA._topic_for_house(8)  # noqa: SLF001
check("house 8 (no Topic primary) gets classical karakas, not empty",
      bool(topic8.significators), f"significators={topic8.significators}")
check("house 8 topic names the house in its label",
      "8th" in topic8.label, topic8.label)

# ---------------------------------------------------------------------------
# Chart-dependent checks: need a real precomputed chart via PyJHora. Skip
# cleanly (not a failure) when the ephemeris source is not on this machine.
# ---------------------------------------------------------------------------


def _pyjhora_available() -> bool:
    if not os.environ.get("PYJHORA_SRC"):
        try:
            spec = importlib.util.find_spec("jhora")
            if spec and spec.origin:
                os.environ["PYJHORA_SRC"] = str(Path(spec.origin).parent.parent)
        except Exception:                                             # noqa: BLE001
            return False
    return importlib.util.find_spec("jhora") is not None


if not _pyjhora_available():
    print("\n(skipping render()-level checks: PyJHora not available)")
else:
    print("\n— 5. render() reflects both fixes end to end —")
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("APP_SECRET", "test-only")
    os.environ.setdefault("ENV", "dev")

    from astro_precompute import resolve_precompute  # noqa: E402
    import deep_evidence as DE  # noqa: E402

    sample = {"name": "Meera Nair", "dob": "1990-01-15", "tob": "12:00",
              "place": "New Delhi, India", "lat": 28.6139, "lon": 77.2090,
              "tz": 5.5, "gender": 0}
    pc = resolve_precompute(
        sample["name"], sample["dob"], birth_time=sample["tob"],
        latitude=sample["lat"], longitude=sample["lon"],
        timezone=sample["tz"], place_name=sample["place"],
        gender=sample["gender"])

    DE.begin(pc, lat=sample["lat"], lon=sample["lon"], tz=sample["tz"])
    try:
        r_house = QA.answer(pc, "how is my 5th house", lat=sample["lat"],
                            lon=sample["lon"], tz=sample["tz"])
        check("'how is my 5th house' answer() picks house 5",
              r_house["topic"].houses[0] == 5)
        html_house = QA.render(r_house, name=sample["name"], paid=True, price=298)
        check("analytical intent drops the yes/no heading",
              "Does your chart even offer this?" not in html_house)
        check("analytical intent uses the 'what your chart shows' heading",
              "What your chart shows" in html_house)
        check("the house/planet breakdown is actually rendered",
              "The house and planet behind this" in html_house)

        r_when = QA.answer(pc, "when will I get promoted", lat=sample["lat"],
                           lon=sample["lon"], tz=sample["tz"])
        html_when = QA.render(r_when, name=sample["name"], paid=True, price=298)
        check("a genuine timing question keeps the yes/no heading",
              "Does your chart even offer this?" in html_when)
        check("timing question's house/planet breakdown is also rendered",
              "The house and planet behind this" in html_when)
    finally:
        DE.end()

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED: " + ", ".join(FAIL))
sys.exit(1 if FAIL else 0)
