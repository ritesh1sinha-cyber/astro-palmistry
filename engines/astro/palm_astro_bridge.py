#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The palm read the chart predicts — a second, independent method per life area.

Astro-Palmistry (Jyotis Saraswati) runs the correlation in both directions. The
subsystem in `astro_palmistry_*` was built for the photograph direction: detect
the mounts, count the lines, then reason. That direction is unusable for most
customers — the palm photos this product actually receives are phone snaps, and
`cv_finding_sentence` spends most of its life saying "photo not clear".

The other direction needs no photograph. Given the birth chart, the book states
what the hand *should* show: each planet owns a mount, its house decides which
palm sector that mount is read against, and its dignity decides the morphology
of the mount itself — a debilitated Venus is "much crossed and rayed", an
exalted one is "large, firm, with a normal girdle". That is a genuinely
falsifiable claim. The reader can look at their own hand and say yes or no,
which is the standard `report_recognition` sets: we make the statement, the
reader judges it. Nothing is asked of them first.

It also earns its place in `report_confluence` for a reason no other lane there
can claim. Every method already voting reads the same nine planets — they
disagree about interpretation, not about evidence. This lane's claims are
checkable against a physical object that was never used to build the chart, so
when chart-expected and palm-observed agree, that agreement is the strongest
evidence this product can offer. When no photo is supplied the lane still votes,
but only on the chart side, and says so.

Two things had to be worked around, and they are worth stating plainly because
they cap how good this lane can be:

* `astro_palmistry_anchor_engine.MAIN_LINE` and `SUB_PLANET` USED TO BE keyed by
  (planet, house), and their nine keys were exactly the nine placements of the
  primary test chart — Jupiter@8, Mercury@10, Venus@10, Ketu@5, Mars@11, Rahu@11,
  Saturn@6, Moon@4, Sun@9. Measured, they fired 9/9 for that chart and 5/108
  across twelve random ones, and when they did fire for a stranger they asserted
  the original chart's dignities and co-tenants as if they were the reader's.
  That has since been fixed at the source: those tables are now empty and the
  anchor engine composes every reading per chart from planet→mount,
  house→zone and dignity→tone, with anchor/sub relationships derived from the
  two real placements. See `anchor_engine_test.py`.

  This module still builds its own prose from `HOUSE_PALM` / `DIGNITY_PALM` /
  `NODE_PALM` rather than surfacing the anchor engine's strings — not because the
  engine's strings are untrustworthy now, but because this lane needs its own
  voice and its own vote. The anchor engine is used here for the *structure* it
  computes: which mount is line-lord of which zone, and the sub-planet ordering.
* `astro_palmistry_chart_lane.COMBO_RULES` — nine book-backed combination rules
  with predicates over the normalised chart — is dead code. It is defined and
  never evaluated by anything in the repo. It is wired here.

**Longevity is filtered out, in code.** `astro_palmistry_longevity` computes a
number of years on an 80-year scale and `combine_longevity` writes verdicts like
"confluence ~63 years (56-70)". No path in this module may emit that. Every
string that leaves here goes through `scrub_lifespan`, which is a single
chokepoint by design: a convention would be forgotten the first time someone
adds a field. The 8th house still carries real signal, so it is routed to health
and rendered as a window with a remedy — `health_window` — and never as a span.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Optional

from astro_palmistry_anchor_engine import PLANET_ZONE, build_anchor_analysis
from astro_palmistry_chart_lane import (
    DIGNITY_PALM,
    HOUSE_PALM,
    NODE_PALM,
    COMBO_RULES,
    _normalize_pc,
)
from astro_palmistry_zone_cv import DOMAIN_ZONES

METHOD_NAME = "the palm-correlation method"

# The book's house/mount mapping lands on twelve houses; this product sells the
# eight life areas of report_cards.AREAS. Houses are placed on the area that
# classically owns them, following report_confluence.DOMAIN_TO_AREAS rather than
# inventing a second routing table:
#   1  body and vitality      -> health (report_cards reads health off house 1)
#   3  siblings, the household -> home, as "family" is routed there
#   6  illness and service     -> health
#   8  hidden matters          -> health, with the lifespan scrub over the top
#   11 gains                   -> money
HOUSE_AREA: dict[int, str] = {
    1: "health", 2: "money", 3: "home", 4: "home", 5: "children", 6: "health",
    7: "love", 8: "health", 9: "learning", 10: "career", 11: "money", 12: "inner",
}

# Which mount the reader is being sent to look at, in words rather than zone ids.
MOUNT_NAME: dict[str, str] = {
    "sun": "the mount of the Sun, under your ring finger",
    "moon": "the mount of the Moon, on the outer edge below the little finger",
    "mars": "the Plain of Mars, the hollow at the centre of your palm",
    "mercury": "the mount of Mercury, at the root of your little finger",
    "jupiter": "the mount of Jupiter, under your index finger",
    "venus": "the mount of Venus, the ball of the thumb",
    "saturn": "the mount of Saturn, under your middle finger",
    "rahu": "the area above the heart line, in the centre of the upper palm",
    "ketu": "upper Mars, the outer edge between the head and heart lines",
}

# Dignity decides the morphology of the mount. DIGNITY_PALM only carries
# entries for the strong and the debilitated cases, which leaves the middle of
# the range with no claim to make. Moolatrikona is classically at least as
# strong as own sign, so it borrows that text; friendly sign borrows it softened.
# Neutral and enemy sign get no morphology text — inventing one would be exactly
# the Barnum failure this lane exists to avoid. They fall through to the
# comparative prominence claim in `_prominence_ranking` instead, which is
# checkable ("this mount should be one of the flattest on your hand") where a
# house-sector restatement is not.
DIGNITY_FALLBACK: dict[str, str] = {
    "moolatrikona": "own_sign",
    "friendly_sign": "own_sign",
}

# Two DIGNITY_PALM entries are written as instructions to the analyst rather
# than as claims about the hand ("Check Rahu zone ... for grille"). A reader
# cannot judge an instruction, so those two are restated as claims.
_MORPHOLOGY_REWRITE: dict[tuple[str, str], str] = {
    ("Rahu", "neutral_sign"):
        "the zone above the heart line carries visible cross-hatching, small "
        "islands, or a darker tone than the palm around it",
    ("Ketu", "neutral_sign"):
        "upper Mars carries a grille or lines that stop abruptly rather than "
        "running clean to the edge",
}
DIGNITY_EXPECTS_STRESS = {"debilitated": True, "enemy_sign": True,
                          "exalted": False, "moolatrikona": False, "own_sign": False}

DIGNITY_TONE = {"exalted": 2.0, "moolatrikona": 1.8, "own_sign": 1.4,
                "friendly_sign": 0.8, "neutral_sign": 0.0, "enemy_sign": -1.0,
                "debilitated": -1.8}

DUSTHANA = (6, 8, 12)
BENEFIC = ("Jupiter", "Venus", "Mercury", "Moon")

PLANET_ORDER = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                "Saturn", "Rahu", "Ketu")

SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

# The eight product areas and the house each is read from, mirroring
# report_cards.AREAS so a vote filed here lines up with the card it lands on.
AREA_HOUSE = {"career": 10, "money": 2, "love": 7, "home": 4,
              "children": 5, "health": 1, "learning": 9, "inner": 12}


# ---------------------------------------------------------------------------
# the longevity filter — the one hard constraint, enforced at a chokepoint
# ---------------------------------------------------------------------------

# Anything that reads as a span of remaining life, a death, or the 80-year scale
# the palm longevity module works on. Ordered so the longest phrases match
# first; every pattern is tested in `selftest`.
_LIFESPAN_PATTERNS: tuple[tuple[str, str], ...] = (
    # explicit spans and estimates. The general rule is last of this group and
    # deliberately blunt: in this product any two- or three-digit count of years
    # is a lifespan claim, and "for 3 years" is left alone by the digit bound.
    (r"\blife\s*(?:-|\s)?line\s+reach\w*\s+suggests?[^.;]*", ""),
    (r"\blife\s*(?:-|\s)?line\s+(?:ends?|stops?|breaks?|terminat\w*)\s*(?:at|around|near)?\s*(?:age)?\s*\d{1,3}\b", ""),
    (r"\b\d{2,3}\s*[-–]\s*year\s*(?:scale|formula|division)\b", ""),
    (r"\b(?:confluence|estimate|estimated|expectancy|span|reach)\s*(?:estimate)?\s*[:=]?\s*~?\s*\d{2,3}\s*years?\b", ""),
    (r"\(\s*(?:range\s*)?\d{2,3}\s*(?:[-–]|to)\s*\d{2,3}\s*(?:years?)?\s*\)", ""),
    (r"\b(?:range|between)\s*\d{2,3}\s*(?:[-–]|to)\s*\d{2,3}\s*years?\b", ""),
    (r"~?\s*\d{2,3}\s*years?\b", ""),
    (r"[-+]?\s?\d{1,3}\s*yrs?\b(?:\s*total)?", ""),
    # the vocabulary itself
    (r"\blife\s*expectancy\b", ""),
    (r"\blife\s*span\b|\blifespan\b", ""),
    (r"\blongevity\b", "resilience"),
    (r"\bkalpayu\b|\bpoornayu\b|\balpayu\b|\bmadhyayu\b", ""),
    (r"\bmaraka\b", ""),
    (r"\byears?\s+of\s+life\b", ""),
    (r"\bremaining\s+years?\b", ""),
    (r"\bdeath\s*timing\b|\btime\s+of\s+death\b|\bdeath\b|\bdying\b|\bdies\b|\bdie\b", ""),
    (r"\bmortality\b|\bfatal\b|\bterminal\b|\bend\s+of\s+life\b", ""),
    (r"\bpass(?:es|ing)?\s+away\b", ""),
)
_LIFESPAN_RE = tuple((re.compile(p, re.I), r) for p, r in _LIFESPAN_PATTERNS)

# If scrubbing gutted the sentence there is nothing left worth showing. A
# fragment like "chart strain pulls the confluence to ." is worse than silence.
_MIN_KEPT_CHARS = 24


def scrub_lifespan(text: str) -> str:
    """Remove every lifespan, death and 80-year-scale claim from one string.

    Returns "" when what remains is a fragment rather than a sentence, so the
    caller drops the statement instead of shipping wreckage. This is the only
    place in the module where prose becomes output; `_safe` routes through it.
    """
    if not text:
        return ""
    out = str(text)
    for rx, repl in _LIFESPAN_RE:
        out = rx.sub(repl, out)
    # Tidy the punctuation the substitutions left behind.
    out = re.sub(r"\(\s*[),;:]*\s*\)", "", out)
    out = re.sub(r"\s+([.,;:!?])", r"\1", out)
    out = re.sub(r"([.,;:])\s*(?=[.,;:])", "", out)
    out = re.sub(r"\s*[-–]\s*(?=[.,;:]|$)", "", out)
    out = re.sub(r"\s{2,}", " ", out).strip(" -–,;:")
    if len(re.sub(r"[^A-Za-z]", "", out)) < _MIN_KEPT_CHARS:
        return ""
    return out


def _safe(text: str) -> str:
    return scrub_lifespan(text)


# ---------------------------------------------------------------------------
# chart-expected palm statements
# ---------------------------------------------------------------------------

def _dignity_morphology(planet: str, dignity: str) -> str:
    """The book's mount morphology for this planet at this dignity, or ""."""
    rewrite = _MORPHOLOGY_REWRITE.get((planet, dignity))
    if rewrite:
        return rewrite
    table = DIGNITY_PALM.get(planet, {})
    key = dignity if dignity in table else DIGNITY_FALLBACK.get(dignity, "")
    text = table.get(key, "")
    if not text:
        return ""
    if dignity == "friendly_sign":
        # Borrowed from own_sign, so the strength claim is softened rather than
        # asserted at full force.
        text = "moderately so: " + text[0].lower() + text[1:]
    return text.strip()


def _placement_score(planet: str, info: dict) -> float:
    """How strong this planet is, for ranking its mount against the others."""
    house = int(info.get("house") or 0)
    score = DIGNITY_TONE.get(str(info.get("dignity") or "neutral_sign"), 0.0)
    if house in DUSTHANA:
        score -= 1.2 if planet in BENEFIC else 0.6
    elif house in (1, 4, 7, 10):
        score += 0.8
    elif house in (5, 9):
        score += 1.0
    elif house == 11:
        score += 0.6
    return score


def _prominence_ranking(planets: dict[str, dict]) -> dict[str, str]:
    """Which mounts this chart says should stand out, and which should be flat.

    The middle of the ranking gets no claim. A statement that a mount is
    "average" is unfalsifiable, and a lane whose statements cannot be wrong is
    the thing `report_recognition` was written to stop shipping. Only the two
    strongest and two weakest placements produce a comparative claim, and the
    claim names the comparison so the reader can hold their hand up and check it.
    """
    ranked = sorted(
        ((p, _placement_score(p, i)) for p, i in planets.items() if i.get("house")),
        key=lambda x: -x[1])
    out: dict[str, str] = {}
    if len(ranked) < 4:
        return out
    for p, s in ranked[:2]:
        if s > 0.5:
            out[p] = "high"
    for p, s in ranked[-2:]:
        if s < 0.0:
            out[p] = "low"
    return out


def _ord(n: int) -> str:
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _planet_statement(planet: str, info: dict,
                      rank: str = "") -> Optional[dict[str, Any]]:
    """One falsifiable "your hand should show X on mount Y" claim, or None.

    Returns None when the chart supports no checkable claim about this mount.
    An earlier version fell back to restating which house sector the mount is
    read against, which sounds like content and is not: it makes no prediction
    the reader can disagree with, and on a chart with seven neutral placements
    it was seven-tenths of the output.
    """
    house = int(info.get("house") or 0)
    sign = str(info.get("sign") or "")
    dignity = str(info.get("dignity") or "neutral_sign")
    if not house or not sign:
        return None

    zone = PLANET_ZONE.get(planet, "mars")
    mount = MOUNT_NAME.get(zone, f"the {zone} zone")
    house_sector = HOUSE_PALM.get(house, {}).get("palm", "")
    themes = HOUSE_PALM.get(house, {}).get("themes", "")
    morph = _dignity_morphology(planet, dignity)

    lead = (f"{planet} sits in {sign}, your {house}{_ord(house)} house "
            f"({themes.lower()}), {dignity.replace('_', ' ')}.")

    if morph:
        body = f"Your chart therefore says {mount} should read as: {morph}"
        if planet in NODE_PALM and (planet, dignity) not in _MORPHOLOGY_REWRITE:
            body += f" {NODE_PALM[planet]}"
        expects_stress = DIGNITY_EXPECTS_STRESS.get(dignity)
    elif rank == "high":
        body = (f"Your chart therefore says {mount} should be one of the two "
                f"best-developed mounts on your hand — visibly fuller and firmer "
                f"than the mount beside it — and the lines crossing the "
                f"{house}{_ord(house)}-house sector ({house_sector.rstrip('.')}) "
                f"should run clean rather than broken")
        expects_stress = False
    elif rank == "low":
        body = (f"Your chart therefore says {mount} should be one of the flattest "
                f"areas of your hand, or the most crossed — noticeably less "
                f"developed than the mounts either side of it")
        expects_stress = True
    else:
        return None

    tone = DIGNITY_TONE.get(dignity, 0.0)
    if house in DUSTHANA:
        tone -= 0.8 if planet in BENEFIC else 0.4
    elif house in (1, 4, 5, 7, 9, 10, 11):
        tone += 0.3
    if rank == "high":
        tone += 0.5
    elif rank == "low":
        tone -= 0.5
    # A claim that the hand should show crossing, grille or a flat mount is a
    # caution however benign the placement looks numerically — the node
    # rewrites above are exactly that case, and were filing positive votes.
    if expects_stress and tone > -0.3:
        tone = -0.3

    return {
        "kind": "planet",
        "planet": planet,
        "sign": sign,
        "house": house,
        "dignity": dignity,
        "zone_id": zone,
        "mount": mount,
        "area": HOUSE_AREA.get(house, "inner"),
        "expects_stress": expects_stress,
        "tone": round(max(-2.0, min(2.0, tone)), 2),
        "text": _safe(f"{lead} {body}."),
    }


def _lord_statement(area: str, house: int, pc: dict,
                    planets: dict[str, dict]) -> Optional[dict[str, Any]]:
    """The area's house lord, and the mount the reader checks it on.

    Only fired for areas where no planet sits in the house, which is four to six
    of the eight on a typical chart. Without it those areas produce no palm
    claim and the lane simply abstains from most of the report. The lord is
    what classical astrology reads for an empty house, so the lord's own mount
    is the one the hand is checked on — and where the lord has gone is the
    per-chart part of the claim.
    """
    hl = (pc.get("house_lords", {}) or {}).get(str(house)) or {}
    lord = hl.get("lord") or SIGN_LORD.get(
        str((pc.get("houses", {}) or {}).get(str(house), {}).get("sign", "")), "")
    if not lord or lord not in planets:
        return None
    info = planets[lord]
    lord_house = int(info.get("house") or 0)

    dignity = str(info.get("dignity") or "neutral_sign")
    zone = PLANET_ZONE.get(lord, "mars")
    mount = MOUNT_NAME.get(zone, f"the {zone} zone")
    morph = _dignity_morphology(lord, dignity)
    sector = HOUSE_PALM.get(house, {}).get("palm", "").rstrip(".")

    # A planet ruling the house its own mount is read against (Mars ruling the
    # 1st, whose sector is the Plain of Mars) would otherwise produce "runs from
    # the Plain of Mars across to the Plain of Mars".
    mount_head = re.sub(r"^the\s+", "", MOUNT_NAME.get(zone, "").split(",")[0]).lower()
    self_referential = bool(mount_head) and mount_head in sector.lower()

    lead = (f"Your {house}{_ord(house)} house is ruled by {lord}, which has gone "
            f"to your {lord_house}{_ord(lord_house)} in {info.get('sign', '')} "
            f"({dignity.replace('_', ' ')}).")
    if self_referential and not morph:
        return None                       # nothing to say that is not circular
    if morph:
        body = (f"So the line that carries this area runs from {mount} — which should "
                f"read as: {morph} — across to the {sector}")
        expects_stress = DIGNITY_EXPECTS_STRESS.get(dignity)
    elif lord_house in DUSTHANA:
        # A neutral lord in a difficult house still supports a checkable claim:
        # the mount carrying the area is the one under pressure.
        body = (f"So the line that carries this area runs from {mount}, and because "
                f"its lord has gone to a difficult house that mount should show "
                f"crossing or barring rather than a clean run to the {sector}")
        expects_stress = True
    else:
        body = (f"So the line that carries this area runs from {mount} across to "
                f"the {sector}, and should run unbroken between the two")
        expects_stress = False

    tone = DIGNITY_TONE.get(dignity, 0.0) * 0.7
    if lord_house in DUSTHANA:
        tone -= 0.8
        if expects_stress is None:
            expects_stress = True
    elif lord_house in (1, 4, 5, 7, 9, 10):
        tone += 0.3

    return {
        "kind": "house_lord",
        "planet": lord,
        "sign": info.get("sign", ""),
        "house": lord_house,
        "ruled_house": house,
        "dignity": dignity,
        "zone_id": zone,
        "mount": mount,
        "area": area,
        "expects_stress": expects_stress,
        "tone": round(max(-2.0, min(2.0, tone)), 2),
        "text": _safe(f"{lead} {body}."),
    }


# The combination rules carry no area of their own — they are written about a
# specific pair of placements. Route each by the houses it names.
_COMBO_AREA_HINT = (
    (("children", "5th"), "children"), (("career", "10th"), "career"),
    (("health", "6th", "service"), "health"), (("gains", "11th"), "money"),
    (("marriage", "7th"), "love"), (("home", "4th", "mother"), "home"),
    (("legacy", "8th", "in-law"), "health"),
)


# COMBO_RULES carries no direction field, and not every rule is a caution —
# "Venus exalted in 10th ... supports public career" is the opposite. Direction
# is read off the rule's own wording rather than assumed, because filing an
# exaltation as a negative vote is worse than not voting at all.
_COMBO_POSITIVE = ("supports", "strong ", "auspicious", "favourable", "benefic",
                   "clean girdle", "well developed")
_COMBO_NEGATIVE = ("debilitat", "weak", "stress", "afflict", "strain", "barred",
                   "grille", "twisted", "broken", "malefic", "depressed", "rayed")


def _combo_statements(planets: dict[str, dict]) -> list[dict[str, Any]]:
    """Evaluate COMBO_RULES, which nothing else in the repo does.

    The rule text is analyst-facing ("verify on close-up Mars zone photos"), so
    the instruction to the analyst is trimmed and only the claim is kept.
    """
    out: list[dict[str, Any]] = []
    for predicate, text in COMBO_RULES:
        if not predicate(planets):
            continue
        claim = re.sub(r"\s*[-–]+\s*(?:verify|inspect|check|watch)\b[^.]*\.?", ".", text,
                       flags=re.I)
        claim = re.sub(r"<[^>]+>", "", claim)
        area = "inner"
        low = claim.lower()
        for needles, target in _COMBO_AREA_HINT:
            if any(n in low for n in needles):
                area = target
                break
        pos = sum(1 for k in _COMBO_POSITIVE if k in low)
        neg = sum(1 for k in _COMBO_NEGATIVE if k in low)
        if pos == neg:
            continue                    # no direction to file: skip the rule
        safe = _safe(claim)
        if not safe:
            continue
        out.append({
            "kind": "combination",
            "planet": "",
            "area": area,
            "zone_id": "",
            "expects_stress": neg > pos,
            "tone": 0.9 if pos > neg else -0.9,
            "text": safe,
        })
    return out


# ---------------------------------------------------------------------------
# the 8th-house signal, rendered as a window and a remedy — never as a span
# ---------------------------------------------------------------------------

_PLANET_REMEDY_FALLBACK = {
    "Sun": "offer water to the rising Sun on Sundays",
    "Moon": "offer milk or water at a Shiva temple on Mondays",
    "Mars": "read the Hanuman Chalisa on Tuesdays",
    "Mercury": "feed green fodder to cows on Wednesdays",
    "Jupiter": "give turmeric or yellow items to a teacher on Thursdays",
    "Venus": "give white sweets or curd to young girls on Fridays",
    "Saturn": "light a mustard-oil lamp under a Peepal tree on Saturdays",
    "Rahu": "give mustard oil and blankets to the needy on Saturdays",
    "Ketu": "feed dogs and chant 'Om Ketave Namah' on Tuesdays",
}


def _remedy_for(planet: str) -> str:
    """The product's own remedy table, with a local copy as the fallback."""
    from final_user_report import REMEDY
    row = REMEDY.get(planet)
    if not row:
        return _PLANET_REMEDY_FALLBACK.get(planet, "keep to regular routine and rest")
    _deity, practice, day, charity = row[:4]
    return f"{practice}; best on {day}, and give {charity}"


def _month(iso: str) -> str:
    d = datetime.strptime(str(iso)[:10], "%Y-%m-%d").date()
    return d.strftime("%B %Y")


def _dasha_window(pc: dict, planet: str, today: date) -> Optional[str]:
    """Current or next Vimshottari window belonging to `planet`.

    A window that has already closed is not a prediction, so past periods are
    skipped. Antardashas are preferred where they exist because a two-year
    window is worth saying and a sixteen-year one is not.
    """
    vim = pc.get("vimshottari", {}) or {}
    cur = vim.get("current_md") or {}
    spans: list[tuple[date, date, str]] = []

    for ad in (vim.get("current_md_antardashas") or []):
        if ad.get("ad_lord") != planet:
            continue
        a, b = _iso(ad.get("start")), _iso(ad.get("end"))
        if a and b:
            spans.append((a, b, f"{_month(ad['start'])} to {_month(ad['end'])}"))

    if not spans:
        for md in list(vim.get("sequence") or []) + ([cur] if cur else []):
            if md.get("md_lord") != planet:
                continue
            a, b = _iso(md.get("start")), _iso(md.get("end"))
            if a and b:
                spans.append((a, b, f"{_month(md['start'])} to {_month(md['end'])}"))

    live = [s for s in spans if s[1] >= today]
    if not live:
        return None
    live.sort(key=lambda s: s[0])
    return live[0][2]


def _iso(v: Any) -> Optional[date]:
    if not v:
        return None
    return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()


def health_window(pc: dict, today: Optional[date] = None) -> list[dict[str, str]]:
    """Difficult-period signals from the 8th/6th house, as care windows.

    This is the only channel through which an 8th-house or Mrityu-Bhaga signal
    reaches the customer. The signal is real and worth acting on; the framing is
    "a health concern is indicated around <window>" with a remedy, and there is
    no arithmetic here that could be read back as a span of years.
    """
    today = today or date.today()
    _lagna, planets = _normalize_pc(pc)
    flagged: list[tuple[str, str]] = []

    for planet, info in planets.items():
        house = int(info.get("house") or 0)
        dignity = str(info.get("dignity") or "")
        if house == 8 and dignity in ("debilitated", "enemy_sign"):
            flagged.append((planet, f"{planet} is weak in your 8th house"))
        elif planet == "Saturn" and house in DUSTHANA:
            flagged.append((planet, f"Saturn sits in your {house}{_ord(house)} house"))
        elif house == 6 and dignity == "debilitated":
            flagged.append((planet, f"{planet} is weak in your 6th house"))

    for mb in ((pc.get("longevity") or {}).get("mrityu_bhaga_all") or []):
        if mb.get("critical") and mb.get("planet"):
            flagged.append((mb["planet"],
                            f"{mb['planet']} sits on a sensitive degree of "
                            f"{mb.get('sign', 'its sign')}"))

    out: list[dict[str, str]] = []
    seen: set = set()
    for planet, because in flagged:
        if planet in seen:
            continue
        window = _dasha_window(pc, planet, today)
        if not window:
            continue                     # no live window: nothing to time, say nothing
        seen.add(planet)
        out.append({
            "planet": planet,
            "window": window,
            "because": _safe(because) or because,
            "text": _safe(
                f"A health concern is indicated around {window}, because {because}. "
                f"Treat it as a period for check-ups and rest rather than pushing "
                f"harder. Remedy: {_remedy_for(planet)}."),
        })
    return out[:3]


# ---------------------------------------------------------------------------
# cross-check against observed palm features
# ---------------------------------------------------------------------------

def _normalize_features(palm_features: Any) -> dict[str, dict[str, Any]]:
    """Accept the three shapes the palm side actually produces.

    `astro_palmistry_zone_cv.inspect_roi` rows carry a `zone_id`; a whole run
    produces a list of them per hand, and `aggregate_zone_metrics` merges hands
    into {zone_id: metrics}. All three arrive here from different callers.
    """
    if not palm_features:
        return {}
    if isinstance(palm_features, dict):
        if "zones" in palm_features or "marked" in palm_features:
            rows = palm_features.get("zones") or palm_features.get("marked") or []
            return _normalize_features(rows)
        # already aggregated: values are metric dicts, not zone rows
        if all(isinstance(v, dict) and "line_count" in v for v in palm_features.values()):
            return dict(palm_features)
        return {}
    rows = list(palm_features)
    if rows and isinstance(rows[0], list):
        from astro_palmistry_zone_cv import aggregate_zone_metrics
        return aggregate_zone_metrics(rows)
    from astro_palmistry_zone_cv import aggregate_zone_metrics
    return aggregate_zone_metrics([rows])


def _cross_check(statements: list[dict], metrics: dict[str, dict]) -> dict[str, Any]:
    """Chart-expected against palm-observed, zone by zone.

    Only statements that carry a directional morphology expectation can be
    checked — a statement that says "read this mount against the 7th sector"
    makes no claim about line density, and scoring it either way would be
    manufacturing agreement.
    """
    agree: list[dict[str, str]] = []
    disagree: list[dict[str, str]] = []
    unreadable: list[str] = []
    # A mount can be named by both a planet statement and a house-lord
    # statement. Checking it twice would report the same physical observation as
    # two independent confirmations, which is the exact overcounting this lane
    # is supposed to protect against.
    done: set = set()

    for st in statements:
        zone = st.get("zone_id")
        expects = st.get("expects_stress")
        if not zone or expects is None or zone in done:
            continue
        m = metrics.get(zone)
        if not m:
            continue
        done.add(zone)
        if not m.get("readable"):
            unreadable.append(zone)
            continue
        observed_stress = bool(m.get("stress_lines"))
        observed_clear = bool(m.get("sparse")) or (not observed_stress)
        row = {
            "planet": st.get("planet", ""),
            "zone_id": zone,
            "expected": "a crossed, heavily rayed mount" if expects
                        else "a full, clean mount",
            "observed": (f"{m.get('line_count', 0)} "
                         f"line{'' if m.get('line_count') == 1 else 's'} "
                         f"(sharpness {m.get('sharpness', 0)}, "
                         f"{m.get('quality', 'fair')} quality)"),
        }
        if (expects and observed_stress) or (not expects and observed_clear
                                            and not observed_stress):
            row["text"] = _safe(
                f"Your chart predicted {row['expected']} at {st.get('mount', zone)} "
                f"and your palm shows {row['observed']} — the two methods agree, "
                f"which is the strongest confirmation this reading can carry.")
            agree.append(row)
        else:
            row["text"] = _safe(
                f"Your chart predicted {row['expected']} at {st.get('mount', zone)}, "
                f"but your palm shows {row['observed']} — the two methods disagree "
                f"here, so this area is read with less confidence.")
            disagree.append(row)

    return {
        "agreements": agree,
        "disagreements": disagree,
        "unreadable_zones": sorted(set(unreadable)),
        "checked": len(agree) + len(disagree),
    }


# ---------------------------------------------------------------------------
# the public surface
# ---------------------------------------------------------------------------

def build(pc: dict, palm_features: Any = None) -> dict[str, Any]:
    """Chart-driven palm expectations, anchor zones, and any palm cross-check.

    Runs from `pc` alone. `palm_features` is optional and may be raw
    `inspect_roi` rows, a per-hand list of those, or an already-aggregated
    {zone_id: metrics} map.
    """
    lagna, planets = _normalize_pc(pc)
    metrics = _normalize_features(palm_features)

    ranking = _prominence_ranking(planets)
    statements: list[dict[str, Any]] = []
    occupied: set = set()
    for planet in PLANET_ORDER:
        info = planets.get(planet)
        if not info:
            continue
        occupied.add(int(info.get("house") or 0))
        st = _planet_statement(planet, info, ranking.get(planet, ""))
        if st and st["text"]:
            statements.append(st)

    for area, house in sorted(AREA_HOUSE.items()):
        if house in occupied:
            continue                      # the occupant already spoke for it
        st = _lord_statement(area, house, pc, planets)
        if st and st["text"]:
            statements.append(st)

    statements.extend(_combo_statements(planets))

    # The anchor engine is used for structure only: which mount is line-lord of
    # which zone, and the sub-planets under it. Its interpretive strings are the
    # test chart's own reading (see module docstring) and are not surfaced.
    #
    # It emits one anchor per planet, which means nine anchors and several
    # duplicate life areas. The product sells eight areas, so the anchors are
    # resolved down to one per area: the occupant of that area's house if there
    # is one — the strongest, when several share it — and otherwise the house
    # lord, which is what classical astrology reads for an empty house.
    anchor = build_anchor_analysis(planets, lagna)
    by_planet = {a["planet"]: a for a in anchor["anchors"]}
    zones: list[dict[str, Any]] = []
    for area, house in sorted(AREA_HOUSE.items()):
        occupants = [p for p, i in planets.items() if int(i.get("house") or 0) == house]
        if occupants:
            lead_planet = max(occupants, key=lambda p: _placement_score(p, planets[p]))
            basis = f"sits in your {house}{_ord(house)}"
        else:
            hl = (pc.get("house_lords", {}) or {}).get(str(house)) or {}
            lead_planet = hl.get("lord", "")
            basis = f"rules your empty {house}{_ord(house)}"
        a = by_planet.get(lead_planet)
        if not a:
            continue
        zone = a["zone_id"]
        subs = [{"planet": p, "house": house, "sign": planets[p]["sign"],
                 "dignity": planets[p]["dignity"], "zone_id": PLANET_ZONE.get(p, "mars")}
                for p in occupants if p != lead_planet][:4]
        zones.append({
            "area": area,
            "house": house,
            "domain_zones": DOMAIN_ZONES.get(a["domain"], []),
            "anchor_planet": lead_planet,
            "anchor_house": int(a["house"]),
            "anchor_sign": a["sign"],
            "anchor_dignity": a["dignity"],
            "zone_id": zone,
            "mount": MOUNT_NAME.get(zone, zone),
            "sub_planets": subs,
            "text": _safe(
                f"For {area}, the line-lord of the palm zone is {lead_planet} "
                f"({a['sign']}, {a['dignity'].replace('_', ' ')}), which {basis}, "
                f"read on {MOUNT_NAME.get(zone, zone)}"
                + (", with " + ", ".join(
                    f"{s['planet']} ({s['dignity'].replace('_', ' ')}) on "
                    f"{MOUNT_NAME.get(s['zone_id'], s['zone_id']).split(',')[0]}"
                    for s in subs) + " as sub-planets in the same zone"
                   if subs else " with no sub-planet in that house")
                + "."),
        })

    cross = _cross_check(statements, metrics) if metrics else {
        "agreements": [], "disagreements": [], "unreadable_zones": [],
        "checked": 0,
    }

    by_area: dict[str, list[dict]] = {}
    for st in statements:
        by_area.setdefault(st["area"], []).append(st)

    return {
        "mode": "chart_driven" if not metrics else "chart_and_palm",
        "lagna": lagna,
        "statements": statements,
        "by_area": by_area,
        "zones": zones,
        "zones_resolved": len([z for z in zones if z["text"]]),
        "cross_check": cross,
        "health_windows": health_window(pc),
        "palm_supplied": bool(metrics),
        "note": ("Read from the birth chart alone — no palm photograph was used. "
                 "Every statement below is something you can check on your own hand."
                 if not metrics else
                 "Chart expectation checked against what the palm photo shows."),
    }


def palm_votes(pc: dict, area_key: str, palm_features: Any = None) -> list:
    """One vote for this area, per report_confluence's one-vote-per-method rule.

    The lane leans on the balance of its own statements for the area, the same
    shaping `lane_votes` uses, so an area with six mild claims does not outweigh
    another method's single strong one. An agreed cross-check with the palm is
    worth more than a chart-only claim and is scaled up; a disagreement pulls
    the vote towards neutral rather than flipping it, because a disagreement
    means we are less sure, not that the opposite is true.
    """
    from report_confluence import Vote        # at call time: no import cycle

    result = build(pc, palm_features)
    mine = result["by_area"].get(area_key) or []
    leaning = [s for s in mine if abs(s["tone"]) >= 0.4]
    if not leaning:
        return []                            # nothing directional — abstain

    depth = 0.8 if len(leaning) == 1 else 1.0
    value = 1.6 * depth * sum(s["tone"] for s in leaning) / len(leaning)

    zones_here = {s["zone_id"] for s in mine if s.get("zone_id")}
    cross = result["cross_check"]
    agreed = [a for a in cross["agreements"] if a["zone_id"] in zones_here]
    denied = [d for d in cross["disagreements"] if d["zone_id"] in zones_here]
    if agreed:
        value *= 1.25
    if denied:
        value *= 0.6

    # Quoting the loudest statement misrepresents a split lane: on the primary
    # test chart the 10th holds debilitated Mercury and exalted Venus, the vote
    # correctly comes out at zero, and the evidence line was showing only the
    # debilitated half. Where the lane is internally divided, both poles are
    # named; otherwise the strongest statement on the winning side speaks.
    ups = sorted((s for s in leaning if s["tone"] > 0), key=lambda s: -s["tone"])
    downs = sorted((s for s in leaning if s["tone"] < 0), key=lambda s: s["tone"])
    if ups and downs and abs(value) < 0.5:
        because = (f"{ups[0]['text']} Against that: {downs[0]['text']} "
                   f"The palm evidence for this area is genuinely divided.")
    elif value >= 0 and ups:
        because = ups[0]["text"]
    elif downs:
        because = downs[0]["text"]
    else:
        because = leaning[0]["text"]
    if agreed:
        because += " " + agreed[0]["text"]
    elif denied:
        because += " " + denied[0]["text"]
    if len(mine) > 1:
        because += f" [{len(mine)} readings from this method]"

    because = _safe(because)
    if not because:
        return []                            # scrubbed to nothing: file no vote
    return [Vote(METHOD_NAME, max(-2.0, min(2.0, value)), because)]


# ---------------------------------------------------------------------------

def selftest() -> int:
    """Proves the lifespan filter strips, and that the lane differentiates."""
    passed = failed = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if ok:
            passed += 1
            print("  pass  %s" % name)
        else:
            failed += 1
            print("  FAIL  %s  %s" % (name, detail))

    # Real strings out of astro_palmistry_longevity, which must never surface.
    leaks = [
        "Palm life-line reach suggests ~64 years on the 80-year scale; chart strain "
        "pulls the confluence to ~56 years (49-63). Inspect fate line bars.",
        "Confluence estimate: ~63 years (range 56-70).",
        "Jupiter@8 (8th anchor): -8 yr kalpayu stress per book",
        "Saraswati 80-year scale: life line covers ~72% of full arc.",
        "Life line ends at age 58 on this print.",
        "The 2nd and 7th are the maraka houses and set life expectancy.",
        "This indicates death timing in the Saturn period.",
        "Chart modifiers (-12 yr total): lifespan shortened.",
    ]
    for i, leak in enumerate(leaks):
        out = scrub_lifespan(leak)
        bad = re.search(r"\d{2,3}\s*years?|year\s*scale|lifespan|life expectancy|"
                        r"\bdeath\b|maraka|kalpayu|life line ends|\byr\b", out, re.I)
        check("scrub %d leaves no lifespan claim" % (i + 1), bad is None,
              "-> %r" % out)

    check("scrub keeps ordinary prose",
          "mount of Venus" in scrub_lifespan(
              "Your chart says the mount of Venus should read as much crossed and rayed."))
    check("scrub rewrites 'longevity' rather than deleting the sentence",
          "resilience" in scrub_lifespan(
              "The longevity zone of the palm carries the 8th house and its marks."))
    check("scrub drops a string that was nothing but a lifespan claim",
          scrub_lifespan("~63 years (range 56-70).") == "")

    # End to end: no field of a built result may carry lifespan language, on any
    # reference chart. A convention would not have caught the 8th-house theme
    # string, which reads "longevity, legacies, sudden events" straight out of
    # HOUSE_PALM and reaches the customer through every 8th-house statement.
    import json
    import os

    charts = [p for p in ("/tmp/pc.json", "/tmp/pc_aditi.json",
                          "/tmp/pc_modi.json", "/tmp/pc_sachin.json")
              if os.path.isfile(p)]
    banned = re.compile(r"\d{2,3}\s*years?|year\s*scale|lifespan|life expectancy|"
                        r"\bdeath\b|\bdies?\b|maraka|kalpayu|life line ends|\byr\b|"
                        r"\blongevity\b", re.I)

    def strings(node):
        if isinstance(node, str):
            yield node
        elif isinstance(node, dict):
            for v in node.values():
                yield from strings(v)
        elif isinstance(node, (list, tuple)):
            for v in node:
                yield from strings(v)

    builds = {}
    for path in charts:
        pc = json.load(open(path, encoding="utf-8"))
        result = build(pc)
        builds[pc.get("meta", {}).get("client", path)] = result
        hits = [s for s in strings(result) if banned.search(s)]
        check("no lifespan language anywhere in %s's result"
              % pc.get("meta", {}).get("client", path),
              not hits, "-> %r" % (hits[:1],))

    # Differentiation: the falsification standard report_recognition sets.
    if len(builds) >= 2:
        texts = {n: [s["text"] for s in r["statements"]] for n, r in builds.items()}
        allt = [t for v in texts.values() for t in v]
        check("statements are near-unique across charts",
              len(set(allt)) >= 0.9 * len(allt),
              "%d distinct of %d" % (len(set(allt)), len(allt)))
        anchors = {n: tuple(z["anchor_planet"] for z in r["zones"])
                   for n, r in builds.items()}
        check("anchor planet per area differs between charts",
              len(set(anchors.values())) == len(anchors), str(anchors))

    print("\n%d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        raise SystemExit(selftest())
