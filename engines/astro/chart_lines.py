"""Plain sentences that are derived from the chart, never from a fixed script.

Several report blocks used to print one canned sentence for every customer
("You carry strong moral grounding and blessings from parents", "The primary
timing window where prior perseverance translates into public recognition").
A sentence like that is a prediction nobody computed. The helpers here replace
them: each line states a fact from the chart (where a planet sits, what it
rules, how strong it is) and, where it makes a claim, the claim follows from
that strength, with three honest outcomes (strong / mixed / strained) rather
than one flattering one.

Pure functions: precompute dict in, strings out. No model, no I/O.
"""
from __future__ import annotations

from typing import Any, Optional

_ORD = {1: "1st", 2: "2nd", 3: "3rd"}
GOOD_HOUSES = (1, 4, 5, 7, 9, 10, 11)
DUSTHANA = (6, 8, 12)
MALEFICS = ("Saturn", "Rahu", "Ketu", "Mars")

HOUSE_SHORT = {
    1: "yourself and your health", 2: "money and family", 3: "effort, communication and siblings",
    4: "home, mother and peace of mind", 5: "children, study and creativity",
    6: "daily work, health routine and debts", 7: "partners and marriage",
    8: "sudden change and shared money", 9: "luck, father and mentors",
    10: "career and public standing", 11: "income and gains", 12: "expenses, rest and time away",
}


def ordinal(n: int) -> str:
    return _ORD.get(n, f"{n}th")


def _planet(pc: dict, name: str) -> dict:
    return ((pc or {}).get("planets") or {}).get(name) or {}


def house_of(pc: dict, planet: str) -> int:
    try:
        return int(_planet(pc, planet).get("house") or 0)
    except (TypeError, ValueError):
        return 0


def dignity_of(pc: dict, planet: str) -> str:
    return str(_planet(pc, planet).get("dignity") or "").lower()


def owns(pc: dict, planet: str) -> list[int]:
    """Houses this planet rules, counted from the rising sign."""
    rows = (pc or {}).get("house_lords") or {}
    out = []
    for h, row in rows.items():
        if isinstance(row, dict) and row.get("lord") == planet:
            try:
                out.append(int(h))
            except (TypeError, ValueError):
                pass
    return sorted(out)


def lord_of(pc: dict, house: int) -> str:
    row = ((pc or {}).get("house_lords") or {}).get(str(house)) or \
          ((pc or {}).get("house_lords") or {}).get(house) or {}
    return str(row.get("lord") or "")


def with_planet(pc: dict, planet: str) -> list[str]:
    """Other planets sharing this planet's sign."""
    sign = _planet(pc, planet).get("sign")
    if not sign:
        return []
    return [p for p, d in ((pc or {}).get("planets") or {}).items()
            if p != planet and isinstance(d, dict) and d.get("sign") == sign]


def dignity_word(dig: str) -> str:
    d = (dig or "").lower()
    if "exalt" in d:
        return "exalted"
    if "debil" in d:
        return "debilitated"
    if "own" in d or "moola" in d:
        return "in its own sign"
    if "enemy" in d:
        return "in an unfriendly sign"
    if "friend" in d:
        return "in a friendly sign"
    return ""


def score_planet(pc: dict, planet: str, *, house: Optional[int] = None) -> int:
    """Rough strength: dignity, house type, and malefic company."""
    d = dignity_of(pc, planet)
    h = house if house is not None else house_of(pc, planet)
    s = 0
    if "exalt" in d or "own" in d or "moola" in d:
        s += 2
    elif "friend" in d:
        s += 1
    elif "debil" in d:
        s -= 2
    elif "enemy" in d:
        s -= 1
    if h in GOOD_HOUSES:
        s += 1
    elif h in DUSTHANA:
        s -= 1
    if planet not in ("Rahu", "Ketu"):
        s -= sum(1 for p in with_planet(pc, planet) if p in MALEFICS and p != planet) > 0
    return s


def grade(score: int) -> str:
    return "strong" if score >= 2 else ("strained" if score <= -1 else "mixed")


def planet_grade(pc: dict, planet: str) -> str:
    return grade(score_planet(pc, planet))


# ---- dasha sub-period lines ---------------------------------------------------------------

def period_line(pc: dict, lord: str, tense: str = "now") -> str:
    """What a running / past / coming sub-period is about, from where its lord sits.

    tense: "past" | "now" | "next".
    """
    if not lord:
        return ""
    h = house_of(pc, lord)
    ruled = owns(pc, lord)
    dig = dignity_word(dignity_of(pc, lord))
    bits: list[str] = []
    if h:
        bits.append(f"sits in your {ordinal(h)} house ({HOUSE_SHORT.get(h, '')})")
    if ruled:
        names = ", ".join(f"{ordinal(x)} ({HOUSE_SHORT.get(x, '')})" for x in ruled[:2])
        bits.append(f"rules your {names}")
    if not bits:
        return ""
    verb = {"past": ("sat", "ruled"), "now": ("sits", "rules"), "next": ("will sit", "will rule")}[tense]
    sit = f"{lord} {verb[0]} in your {ordinal(h)} house ({HOUSE_SHORT.get(h, '')})" if h else lord
    rule = ""
    if ruled:
        names = " and ".join(f"{ordinal(x)} ({HOUSE_SHORT.get(x, '')})" for x in ruled[:2])
        rule = f", and {verb[1]} your {names}" if h else f" {verb[1]} your {names}"
    strength = ""
    if dig in ("exalted", "in its own sign"):
        strength = f" It is {dig} there, so it works from strength."
    elif dig == "debilitated":
        strength = " It is debilitated there, so results come with effort."
    tail = {
        "past": " Those were the areas that period pulled forward.",
        "now": " Those are the areas this period pulls forward.",
        "next": " Those are the areas it is likely to pull forward.",
    }[tense]
    return f"{sit}{rule}.{strength}{tail}"


# ---- family: graded from the significators ---------------------------------------------------

_CLAIM = {
    # relation -> grade -> sentence tail (hedged, classical)
    "father": {
        "strong": "which classically points to a father who is a firm, respected presence in your life",
        "mixed": "which classically points to a father with real warmth and some friction or distance",
        "strained": "which classically points to a harder road with the father's side: strictness, distance or hardship",
    },
    "mother": {
        "strong": "which classically points to a nurturing, steadying mother and a settled early home",
        "mixed": "which classically points to a caring mother and a home with comfort and some strain",
        "strained": "which classically points to a more difficult emotional bond or unsettled early home",
    },
    "siblings": {
        "strong": "which classically points to supportive, loyal brothers and sisters",
        "mixed": "which classically points to siblings who are close at times and distant at others",
        "strained": "which classically points to rivalry, distance or few siblings",
    },
    "home": {
        "strong": "which classically points to a stable home and comfort that builds over time",
        "mixed": "which classically points to a home life with comfort and some unsettled stretches",
        "strained": "which classically points to a home life that asked for adjustment, moves or hardship",
    },
}


def _placed(pc: dict, planet: str, role: str) -> str:
    """One indicator, described in plain words from its real condition.

    No planet, sign or house is named: the family block is customer-facing
    text and every reason below is read straight off the chart.
    """
    h = house_of(pc, planet)
    if not h:
        return ""
    d = dignity_of(pc, planet)
    reasons: list[str] = []
    if "exalt" in d or "own" in d or "moola" in d:
        reasons.append("in a sign where it is strong")
    elif "debil" in d or "enemy" in d:
        reasons.append("in a sign where it is weak")
    if h in GOOD_HOUSES:
        reasons.append("in a supportive part of the chart")
    elif h in DUSTHANA:
        reasons.append("in a testing part of the chart")
    if [p for p in with_planet(pc, planet) if p in MALEFICS]:
        reasons.append("with hard company beside it")
    return f"{role} is {' and '.join(reasons) if reasons else 'placed neutrally'}"


def family_notes(pc: dict) -> dict[str, list[str]]:
    """Per relation, one or two sentences built from the actual significators.

    Father: Sun and the 9th lord. Mother: Moon and the 4th lord. Siblings: Mars
    and the 3rd lord. Home: the 4th lord and Venus. Strength decides the claim,
    so a strained chart reads as strained.
    """
    out: dict[str, list[str]] = {"father": [], "mother": [], "siblings": [], "home": []}
    if not isinstance(pc, dict) or not (pc.get("planets") or {}):
        return out
    spec = {
        "father": [("Sun", "your father's main indicator"), (lord_of(pc, 9), "the ruler of your luck-and-father area")],
        "mother": [("Moon", "your mother's main indicator"), (lord_of(pc, 4), "the ruler of your home-and-mother area")],
        "siblings": [("Mars", "the main indicator of siblings"), (lord_of(pc, 3), "the ruler of your siblings area")],
        "home": [(lord_of(pc, 4), "the ruler of your home area"), ("Venus", "the indicator of comforts")],
    }
    for rel, pairs in spec.items():
        seen: set[str] = set()
        scores: list[int] = []
        parts: list[str] = []
        for planet, role in pairs:
            if not planet or planet in seen:
                continue
            seen.add(planet)
            txt = _placed(pc, planet, role)
            if txt:
                parts.append(txt)
                scores.append(score_planet(pc, planet))
        if not parts:
            continue
        g = grade(round(sum(scores) / len(scores)))
        out[rel].append(f"In your chart, {'; '.join(parts)}, {_CLAIM[rel][g]}.")
    return out
