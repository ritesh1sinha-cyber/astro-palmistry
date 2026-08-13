"""Multiple methods, voting — the confluence, used as an engine not as prose.

The old confluence report showed the customer the voting. That was backwards:
the reader does not want to watch six techniques argue, they want the verdict
and how sure we are. So the methods still all run, and all vote, but what
surfaces is one line and a confidence chip.

Six independent reads per life area:

  1. **Parashari** — the house lord's dignity, its placement, benefic/malefic
  2. **Ashtakavarga** — the classical numeric strength of the house (SAV)
  3. **Divisional chart** — the varga that governs that area (D10 for career,
     D9 for marriage, D2 for money, D4 for home, D24 for learning…)
  4. **Occupancy** — which planets actually sit in the house
  5. **Structural yogas** — raja yogas, upachaya placements, and crucially
     *neecha bhanga*, the cancellation of debilitation
  6. **Running period** — whether Vimshottari, Yogini and Jaimini currently
     point at this area, and whether they agree

Neecha bhanga is why this module exists. On the test chart Mercury rules career
and is debilitated — so a single-method read says "recognition lags". But that
debilitation is *cancelled* by exalted Venus, which classically inverts it into
strength. Reading dignity alone would have shipped a confident, wrong, and
demoralising prediction to a paying customer. Six methods voting catches it;
one does not.

Dasha works the same way. Vimshottari alone is a single opinion. Yogini carries
its own tone, Jaimini's Chara (sign-based) periods move independently, and BNN
casts a fourth vote on the current Vimshottari MD/AD lords via nadi dignity —
not a separate dasha clock. Where those lenses agree, confidence is high.
Where they split, the reader is told it is a mixed window rather than being
handed false certainty.

On top of those six, every **specialist lane** the codebase already runs now
votes as well — the nadi lane, the sub-lord lane, the karaka lane, the
modern-technique lane, the disease lane, the lifespan lane, the birth-star lane
and the point-score lane. They were computing full readings for other reports
and contributing nothing here, which meant the verdict a customer sees was
built from a fraction of what we actually know about the chart.

Two rules keep that from turning into noise:

* **One vote per lane, per area.** A lane that files twelve claims about career
  does not get twelve votes; it gets one, whose strength is the balance of its
  own claims. Otherwise the loudest pipeline decides the verdict.
* **A lane that has nothing directional to say abstains.** Lanes emit a lot of
  descriptive, tone-neutral material. Counting that as a zero vote would drag
  every area towards "mixed" — which destroys the signal rather than adding to
  it — so a lane only votes when it actually leans.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional


def _ord(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    return f"{n}" + ("th" if 10 <= n % 100 <= 20
                     else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


# Which divisional chart owns which life area, classically.
AREA_VARGA = {
    "career": ("D10", "the career chart"),
    "money": ("D2", "the wealth chart"),
    "love": ("D9", "the marriage chart"),
    "home": ("D4", "the home chart"),
    "children": ("D7", "the children chart"),
    "health": ("D30", "the health chart"),
    "learning": ("D24", "the learning chart"),
    "inner": ("D20", "the spiritual chart"),
    "legal": ("D6", "the dispute chart"),
}

# A single varga is one opinion too. Each area gets a second, classically
# related division to cross-examine the first, and D9 checks every area
# (below) because navamsha confirms or denies whatever D1 promised.
#   D5  standing, authority, fame — and the merit (purva punya) behind children
#   D6  illness, debts, enemies            D7  progeny
#   D11 gains                              D16 vehicles, comforts
#   D45 paternal line and character — the 9th-house matters this product files
#       under "learning and luck"
#   D60 the sum of past karma
AREA_VARGA_CROSS = {
    "career": "D5", "money": "D11", "love": "D7", "home": "D16",
    "children": "D5", "health": "D6", "learning": "D45", "inner": "D60",
    "legal": "D9",
}

VARGA_PHRASE = {
    "D2": "the wealth division", "D4": "the home division",
    "D5": "the standing division", "D6": "the illness division",
    "D7": "the children division", "D9": "the ninth-part chart",
    "D10": "the career division", "D11": "the gains division",
    "D16": "the comforts division", "D20": "the spiritual division",
    "D24": "the learning division", "D30": "the health division",
    "D45": "the paternal-line division", "D60": "the past-karma division",
}

# The lanes speak for themselves in the evidence, but never under their own
# names — same convention as SYSTEM_RENAMES in astro_voice: the customer is
# told which technique spoke, in words they can read.
LANE_METHOD = {
    "BNN": "the nadi method",
    "KP": "the sub-lord method",
    "Jaimini": "the karaka method",
    "Mehta": "the modern-technique method",
    "Bhardwaj": "the case-book method",
    "Goel": "the vulnerability-indication method",
    "KVS": "the birth-star method",
    "Longevity": "the lifespan method",
    "Ashtakavarga": "the point-score method",
}
LANE_METHOD_FALLBACK = "a further classical method"

# The lanes speak in the eleven domains of lane_claim.SECTION_TO_DOMAIN; this
# product sells eight life areas. Most map one-to-one. The rest are placed on
# the house that classically owns them rather than being thrown away:
#   father  -> 9th house, which is also this product's "learning and luck"
#   mother  -> 4th house, which is this product's "home"
#   family  -> siblings and household, read with home
#   personality -> temperament, which is what the inner-life card is about
DOMAIN_TO_AREAS = {
    "career": ("career",),
    "finance": ("money",),
    "marriage": ("love",),
    "property": ("home",),
    "children": ("children",),
    "health": ("health",),
    "mother": ("home",),
    "family": ("home",),
    "father": ("learning",),
    "personality": ("inner",),
}

# "future" and "travel" are grab-bags — 9th-house fortune, 12th-house moksha,
# and pure dasha commentary all land there. Route them by the section that
# produced them; a claim that is only about timing belongs to no life area and
# is counted as unrouted rather than smeared across all eight.
FUTURE_SECTION_AREAS = {
    "travel": ("learning",), "gems_kl_9th": ("learning",), "ch09": ("learning",),
    "spiritual": ("inner",), "gems_kl_12th_moksha": ("inner",),
    "gems_kl_12th_devotion": ("inner",), "remedies": ("inner",),
    "ch13": ("inner",),
}

BENEFIC = ("Jupiter", "Venus", "Mercury", "Moon")
MALEFIC = ("Saturn", "Mars", "Sun", "Rahu", "Ketu")

SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}
EXALTED = {"Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
           "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces",
           "Saturn": "Libra"}
DEBILITATED = {p: {"Aries": "Libra", "Taurus": "Scorpio", "Capricorn": "Cancer",
                   "Virgo": "Pisces", "Cancer": "Capricorn", "Pisces": "Virgo",
                   "Libra": "Aries"}.get(s, "")
               for p, s in EXALTED.items()}

VIM_YEARS = (("Ketu", 7), ("Venus", 20), ("Sun", 6), ("Moon", 10), ("Mars", 7),
             ("Rahu", 18), ("Jupiter", 16), ("Saturn", 19), ("Mercury", 17))
VIM_TOTAL = 120


def _d(v: Any) -> Optional[date]:
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# a vote
# ---------------------------------------------------------------------------

class Vote:
    __slots__ = ("method", "value", "because")

    def __init__(self, method: str, value: float, because: str):
        self.method = method
        self.value = value              # -2 .. +2
        self.because = because

    @property
    def direction(self) -> str:
        return "up" if self.value > 0.4 else ("down" if self.value < -0.4 else "mixed")


def _d9_sign(pc: dict, planet: str) -> str:
    """D9 is not in the divisional block; it lives on each planet."""
    return (pc.get("planets", {}).get(planet) or {}).get("navamsha_sign", "")


def _varga_sign(pc: dict, varga: str, planet: str) -> str:
    if varga == "D9":
        return _d9_sign(pc, planet)
    return (pc.get("divisional", {}).get(varga) or {}).get(planet, "")


def _sign_in(pc: dict, planet: str) -> str:
    return (pc.get("planets", {}).get(planet) or {}).get("sign", "")


def _dignity_in(planet: str, sign: str) -> float:
    if not sign:
        return 0.0
    if EXALTED.get(planet) == sign:
        return 2.0
    if DEBILITATED.get(planet) == sign:
        return -2.0
    if SIGN_LORD.get(sign) == planet:
        return 1.5
    return 0.0


# ---------------------------------------------------------------------------
# canonical confluence engine
# ---------------------------------------------------------------------------

_METHOD_FAMILY = {
    "the classical method": "natal_structure",
    "the strength-scoring method": "natal_structure",
    "occupancy": "natal_structure",
    "the cancellation rule": "natal_structure",
    "chart combinations": "natal_structure",

    "the confirmation chart": "divisional",
    "the cross-check chart": "divisional",

    "the nadi method": "specialist",
    "the sub-lord method": "specialist",
    "the karaka method": "specialist",
    "the modern-technique method": "specialist",
    "the case-book method": "specialist",
    "the vulnerability-indication method": "specialist",
    "the birth-star method": "specialist",
    "the lifespan method": "specialist",
    "the point-score method": "specialist",
    "a further classical method": "specialist",

    "the classical rule-book": "rules",
    "the sky right now": "transit",
    "the period clock": "timing",
    "dasha timing": "timing",
    "palmistry": "independent",
    "palm": "independent",
    "numerology": "independent",
}

_FAMILY_NAMES = {
    "natal_structure": "Birth-chart structure",
    "divisional": "Divisional-chart confirmation",
    "specialist": "Independent specialist methods",
    "timing": "Dasha timing",
    "transit": "Current transits",
    "rules": "Classical rule checks",
    "independent": "Independent cross-checks",
}

# Every family gets one bounded contribution. This prevents ten statements
# from one technique, or several correlated readings of the same planet, from
# drowning out a genuinely conflicting family.
_FAMILY_CAP = {
    "natal_structure": 1.00,
    "divisional": 1.00,
    "specialist": 1.00,
    "timing": 1.00,
    "transit": 1.00,
    "rules": 0.75,
    "independent": 0.75,
}

def _family_for_method(method: str) -> str:
    raw = str(method or "").strip()
    if raw in _METHOD_FAMILY:
        return _METHOD_FAMILY[raw]
    low = raw.lower()
    if "transit" in low or "sky" in low:
        return "transit"
    if "period" in low or "dasha" in low or "yogini" in low or "chara" in low:
        return "timing"
    if "rule" in low:
        return "rules"
    if "palm" in low:
        return "independent"
    if "numer" in low:
        return "independent"
    if "varga" in low or "chart" in low or "d9" in low:
        return "divisional"
    return "specialist"

def _side(value: float) -> str:
    return "up" if value > 0.4 else ("down" if value < -0.4 else "mixed")

def _touches_area(pc: dict, area_key: str, house: int, planet: str) -> bool:
    """Whether a planet has a defensible natal connection to this area."""
    if not planet:
        return False
    support = {
        "career": (10, 6, 11), "money": (2, 11), "love": (7, 5),
        "home": (4, 2), "children": (5, 9), "health": (1, 6, 8),
        "learning": (9, 5), "inner": (12, 9),
    }.get(area_key, (house,))
    hl = pc.get("house_lords") or {}
    planets = pc.get("planets") or {}
    if any((hl.get(str(h)) or {}).get("lord") == planet for h in support):
        return True
    return (planets.get(planet) or {}).get("house") in support

def _dasha_area_vote(pc: dict, area_key: str, house: int,
                     when: Optional[date] = None) -> Optional[Vote]:
    """One bounded timing vote built from Vimshottari + Yogini + Chara + BNN.

    These clocks are related systems, so they are intentionally combined into
    one timing-family vote instead of pretending they are four independent
    proofs. Their component readings remain available for audit/debugging.
    """
    when = when or date.today()
    try:
        dc = dasha_confluence(pc, when)
    except Exception:
        return None
    readings = [r for r in (dc.get("readings") or []) if r.get("label")]
    if not readings:
        return None

    relevant = []
    for r in readings:
        planets = r.get("planets") or []
        if any(_touches_area(pc, area_key, house, p) for p in planets):
            relevant.append(r)

    # If no dasha planet directly touches the area, timing is not allowed to
    # manufacture a prediction for it. It can remain neutral.
    if not relevant:
        return Vote("dasha timing", 0.0,
                    "The current dasha clocks do not directly activate this area")

    vals = [float(r.get("tone") or 0) for r in relevant]
    score = sum(vals) / len(vals)
    # Require actual directional agreement before allowing timing to be strong.
    up = sum(v > 0.2 for v in vals)
    down = sum(v < -0.2 for v in vals)
    if up and down:
        score *= 0.55
    score = max(-1.6, min(1.6, score))
    names = []
    for r in relevant:
        n = str(r.get("system") or "")
        label = str(r.get("label") or "")
        if n and label:
            names.append(f"{n}: {label}")
    because = " · ".join(names[:4])
    if up and down:
        because += " — the timing clocks disagree, so this is treated cautiously"
    elif because:
        because += " — the active clocks broadly point the same way"
    return Vote("dasha timing", score, because)

def _aggregate_family(votes: list[Vote]) -> dict:
    """Collapse related evidence into one bounded family signal."""
    decided = [v for v in votes if v.direction != "mixed"]
    if not decided:
        return {"score": 0.0, "direction": "mixed", "n": 0,
                "up": 0, "down": 0, "methods": []}

    # Diminishing returns: the first two independent methods in a family
    # carry most information; further agreement increases confidence but not
    # linearly increases the final score.
    vals = sorted((float(v.value) for v in decided), key=abs, reverse=True)
    weights = [1.0, 0.75, 0.55, 0.40, 0.30]
    num = sum(v * weights[min(i, len(weights)-1)] for i, v in enumerate(vals))
    den = sum(weights[min(i, len(weights)-1)] for i in range(len(vals)))
    score = num / den if den else 0.0
    up = sum(v.direction == "up" for v in decided)
    down = sum(v.direction == "down" for v in decided)
    return {
        "score": max(-2.0, min(2.0, score)),
        "direction": _side(score),
        "n": len(decided), "up": up, "down": down,
        "methods": [v.method for v in decided],
    }

def _promise_for(pc: dict, area_key: str) -> dict:
    """Natal/divisional promise gate — lazy import keeps tests lightweight."""
    try:
        from personalized_confluence import resolve_promise
    except Exception:  # noqa: BLE001
        return {}
    return resolve_promise(pc, area_key)


def _activation_for(*, direction: str, score: float, confidence: str,
                    agreement: str, promise_status: str) -> dict:
    """Timing-only activation gate (P0-8) — separate object, never merged into promise."""
    try:
        from personalized_confluence import resolve_activation
    except Exception:  # noqa: BLE001
        return {}
    return resolve_activation(
        direction=direction, score=score, confidence=confidence,
        agreement=agreement, promise_status=promise_status,
    )


def build_confluence(pc: dict, area_key: str, house: int,
                     *, today: Optional[date] = None,
                     raw_votes: Optional[list[Vote]] = None) -> dict:
    """Canonical promise × timing × manifestation confluence.

    The engine first gathers all existing evidence, then prevents correlated
    evidence from being counted as independent proof. The final direction is
    determined here. Semantic language is never allowed to override it.
    """
    today = today or date.today()
    votes = list(raw_votes if raw_votes is not None else area_votes(pc, area_key, house))
    dv = _dasha_area_vote(pc, area_key, house, today)
    if dv is not None:
        votes.append(dv)

    # Palm/numerology may arrive through specialist collectors under a different
    # method name; family detection keeps them independent without changing
    # their underlying vote.
    families: dict[str, list[Vote]] = {}
    for v in votes:
        families.setdefault(_family_for_method(v.method), []).append(v)

    family_rows = []
    weighted = 0.0
    total_weight = 0.0
    for family, fvotes in families.items():
        agg = _aggregate_family(fvotes)
        cap = _FAMILY_CAP.get(family, 0.75)
        if agg["n"] == 0:
            continue
        weighted += agg["score"] * cap
        total_weight += cap
        family_rows.append({
            "family": family,
            "label": _FAMILY_NAMES.get(family, family.replace("_", " ").title()),
            "score": round(agg["score"], 3),
            "direction": agg["direction"],
            "methods": list(dict.fromkeys(agg["methods"])),
            "up": agg["up"], "down": agg["down"], "n": agg["n"],
        })

    final_score = weighted / total_weight if total_weight else 0.0
    direction = _side(final_score)

    supporting = [f for f in family_rows if f["direction"] == direction and direction != "mixed"]
    opposing = [f for f in family_rows
                if f["direction"] not in ("mixed", direction)]
    decided_families = [f for f in family_rows if f["direction"] != "mixed"]

    # Confidence requires both breadth and strength. A pile of related
    # techniques is not enough; at least two families must independently agree.
    same = len(supporting)
    breadth = same / len(decided_families) if decided_families else 0.0
    if direction == "mixed":
        confidence = "low"
    elif same >= 4 and breadth >= 0.70 and abs(final_score) >= 0.65:
        confidence = "very high"
    elif same >= 3 and breadth >= 0.65 and abs(final_score) >= 0.50:
        confidence = "high"
    elif same >= 2 and breadth >= 0.60:
        confidence = "moderate"
    else:
        confidence = "low"

    # A conflict penalty is recorded separately so later calibration can use
    # it without changing the directional score.
    conflict = sum(min(1.0, abs(f["score"])) for f in opposing)
    conflict_ratio = conflict / max(1.0, sum(abs(f["score"]) for f in family_rows))

    agreement = _derive_agreement(
        same, len(decided_families), breadth, conflict_ratio)
    secondary_confirmations = _build_secondary_confirmations(
        pc, area_key, house, direction, today)

    promise = _promise_for(pc, area_key)
    activation = _activation_for(
        direction=direction, score=final_score, confidence=confidence,
        agreement=agreement, promise_status=str(promise.get("status") or ""),
    )

    return {
        "direction": direction,
        "score": round(final_score, 3),
        "confidence": confidence,
        "promise": promise,
        "activation": activation,
        "agreement": agreement,
        "votes": votes,
        "families": family_rows,
        "supporting_families": [f["label"] for f in supporting],
        "opposing_families": [f["label"] for f in opposing],
        "family_agreement": f"{same} of {len(decided_families)} evidence families align"
                             if decided_families else "",
        "conflict_ratio": round(conflict_ratio, 3),
        "secondary_confirmations": secondary_confirmations,
        "timing": {
            "method": "Vimshottari + Yogini + Jaimini Chara + BNN",
            "vote": {"direction": dv.direction if dv else "mixed",
                     "score": round(dv.value, 3) if dv else 0.0,
                     "because": dv.because if dv else ""},
        },
    }


def _derive_agreement(
    same: int,
    decided_count: int,
    breadth: float,
    conflict_ratio: float,
) -> str:
    """Agreement among evidence families — separate from direction/confidence."""
    if decided_count == 0:
        return "weak"
    if conflict_ratio >= 0.45 and decided_count >= 2:
        return "conflicting"
    if breadth >= 0.75 and same >= 3:
        return "strong"
    if breadth >= 0.50 or same >= 2:
        return "partial"
    return "weak"


def _build_secondary_confirmations(
    pc: dict,
    area_key: str,
    house: int,
    direction: str,
    when: date,
) -> list[dict]:
    """Independent timing confirmations that align with the area direction."""
    if direction == "mixed":
        return []
    try:
        dc = dasha_confluence(pc, when)
    except Exception:  # noqa: BLE001
        return []

    _METHOD_LABELS = {
        "yogini": "Yogini",
        "chara": "Jaimini Chara",
        "bnn": "BNN",
    }
    out: list[dict] = []
    for reading in dc.get("readings") or []:
        kind = str(reading.get("kind") or "")
        if kind == "vimshottari":
            continue
        planets = [p for p in (reading.get("planets") or []) if p]
        if not planets:
            continue
        if not any(_touches_area(pc, area_key, house, p) for p in planets):
            continue
        tone = float(reading.get("tone") or 0)
        r_dir = "up" if tone > 0.2 else ("down" if tone < -0.2 else "mixed")
        if r_dir != direction:
            continue
        method = _METHOD_LABELS.get(kind, str(reading.get("system") or "Timing"))
        planet = planets[0]
        if direction == "up":
            reason = (
                f"{method} timing also supports this {area_key} window "
                f"through {planet}."
            )
        else:
            reason = (
                f"{method} timing also adds caution in this {area_key} window "
                f"through {planet}."
            )
        strength = "strong" if abs(tone) >= 1.0 else ("moderate" if abs(tone) >= 0.5 else "low")
        out.append({
            "method": method,
            "planet": planet,
            "direction": "support" if direction == "up" else "caution",
            "area": area_key,
            "reason": reason,
            "strength": strength,
        })
    return out


# ---------------------------------------------------------------------------
# the specialist lanes
# ---------------------------------------------------------------------------

# Running every lane costs a full pass over the book pipelines, so it happens
# once per chart and every area reads the same result.
_LANE_CACHE: dict[tuple, tuple] = {}


def _chart_key(pc: dict) -> tuple:
    m = pc.get("meta", {}) or {}
    return (m.get("client", ""), m.get("dob", ""), m.get("birth_time", ""),
            m.get("birth_place", ""), m.get("ayanamsa", ""))


def _areas_for_claim(claim) -> tuple:
    """Which of the eight product areas a lane claim speaks to."""
    if claim.domain in ("future", "travel"):
        return FUTURE_SECTION_AREAS.get(str(claim.section_id).lower(), ())
    return DOMAIN_TO_AREAS.get(claim.domain, ())


def lane_readings(pc: dict) -> tuple:
    """Every specialist lane's claims, bucketed by area then lane, cached.

    Returns ({area: {lane: [claim, ...]}}, meta) where meta carries each lane's
    claim count, any collector that failed, and the claims that belong to no
    life area — kept visible so a routing gap shows up as a number instead of
    quietly shrinking the evidence.
    """
    key = _chart_key(pc)
    if key in _LANE_CACHE:
        return _LANE_CACHE[key]

    meta: dict = {}
    claims: list = []
    m = pc.get("meta", {}) or {}
    if m.get("client") and m.get("dob"):
        try:
            from lane_collectors import collect_all_lanes
            # The collectors only touch the extracted source when they have no
            # precompute; we always have one, so the path is not needed.
            claims, meta = collect_all_lanes("", m["client"], m["dob"], pc)
        except Exception as exc:            # a broken import must not kill a report
            meta = {"lanes_error": f"{type(exc).__name__}: {exc}"[:160]}
    else:
        meta = {"lanes_error": "precompute carries no client/dob"}

    buckets: dict = {}
    unrouted: dict = {}
    for c in claims:
        areas = _areas_for_claim(c)
        if not areas:
            unrouted[c.domain] = unrouted.get(c.domain, 0) + 1
            continue
        for area in areas:
            buckets.setdefault(area, {}).setdefault(c.lane, []).append(c)
    meta["unrouted"] = unrouted
    meta["claims_routed"] = sum(len(v) for a in buckets.values() for v in a.values())

    _LANE_CACHE[key] = (buckets, meta)
    return buckets, meta


def _plain(text: str) -> str:
    """Lane prose as the customer may see it: no acronyms, no book citations.

    The lanes write for an analyst — "6th CSL", "SAV 23", "(Ravichandran)".
    That is fine in their own reports, which run this same cleanup on the way
    out; the evidence line under a card has to go through it too.
    """
    from astro_voice import strip_citations, translate_jargon
    # keep_original=False: the <abbr> tooltip form is for body prose, and an
    # evidence line is already a one-liner squeezed under a verdict.
    return " ".join(translate_jargon(
        strip_citations(text, hide_system_names=True),
        keep_original=False).split())


def _clip(text: str, limit: int = 240) -> str:
    """Trim on a sentence boundary — a claim cut mid-word reads as a bug."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    stop = max(cut.rfind(". "), cut.rfind("; "), cut.rfind(" — "))
    return (cut[:stop + 1] if stop > 80 else cut.rsplit(" ", 1)[0]) + "…"


def lane_votes(pc: dict, area_key: str) -> list:
    """One vote per specialist lane for this area.

    A lane's strength is the balance of its own claims over everything it said
    about the area, so twelve mildly positive claims do not outweigh one strong
    one from another lane, and a lane that is mostly descriptive votes softly.
    """
    buckets, _meta = lane_readings(pc)
    votes: list = []
    for lane, claims in sorted(buckets.get(area_key, {}).items()):
        pos = [c for c in claims if c.direction == "positive"]
        cau = [c for c in claims if c.direction == "caution"]
        if not pos and not cau:
            continue                         # nothing to lean on — abstain
        # A lane that reaches the same conclusion across several of its own
        # sections is surer than one that mentions the area once in passing —
        # and several lanes carry exactly one permanently amber section
        # (the illness rule in the sub-lord lane fires on every chart), which
        # at full strength was a constant negative rather than a reading.
        depth = 0.8 if len(claims) == 1 else 1.0
        value = 1.6 * depth * (len(pos) - len(cau)) / len(claims)
        lead = (pos if len(pos) >= len(cau) else cau)[0]
        because = _clip(_plain(lead.text))
        if lead.timing:
            because += f" ({_plain(lead.timing)})"
        if len(claims) > 1:
            because += f" [{len(claims)} readings from this method]"
        votes.append(Vote(LANE_METHOD.get(lane, LANE_METHOD_FALLBACK),
                          max(-2.0, min(2.0, value)), because))
    return votes


# ---------------------------------------------------------------------------

def _varga_vote(pc: dict, lord: str, varga: str, method: str) -> Optional[Vote]:
    """How the house lord fares in one division."""
    vsign = _varga_sign(pc, varga, lord)
    if not vsign:
        return None
    v = _dignity_in(lord, vsign)
    return Vote(method, v,
                f"in {VARGA_PHRASE.get(varga, varga)}, {lord} sits in {vsign}"
                + (" — exalted there" if v >= 2 else
                   " — debilitated there" if v <= -2 else
                   " — in its own sign" if v > 0 else " — neither strong nor weak there"))


def divisional_votes(pc: dict, area_key: str, lord: str) -> list:
    """The governing division, a classical cross-check, and D9 over the top.

    One varga was never enough: a lord can look strong in D10 and collapse in
    navamsha, and the classical rule is that D9 confirms or denies whatever D1
    promised. Vargottama — the same sign in D1 and D9 — is the strongest single
    confirmation there is, and it is invisible to a dignity read alone.
    """
    votes: list = []
    if not lord:
        return votes
    primary, primary_name = AREA_VARGA.get(area_key, ("", ""))
    if primary:
        v = _varga_vote(pc, lord, primary, primary_name)
        if v:
            votes.append(v)

    cross = AREA_VARGA_CROSS.get(area_key, "")
    if cross and cross != primary:
        v = _varga_vote(pc, lord, cross, "the cross-check chart")
        if v:
            votes.append(v)

    if primary != "D9":
        d9, d1 = _d9_sign(pc, lord), _sign_in(pc, lord)
        if d9:
            if d9 == d1:
                votes.append(Vote(
                    "the confirmation chart", 1.8,
                    f"{lord} holds {d9} in both the birth chart and the "
                    f"ninth-part chart — the classics treat that repetition as "
                    f"the strongest single sign that the promise here is real"))
            else:
                dig = _dignity_in(lord, d9)
                votes.append(Vote(
                    "the confirmation chart", dig,
                    f"the ninth-part chart puts {lord} in {d9}"
                    + (" — the birth-chart promise is confirmed and strengthened"
                       if dig >= 2 else
                       " — the ninth-part chart does not back the birth chart here"
                       if dig <= -2 else
                       " — its own sign there, so the promise holds" if dig > 0
                       else " — neither confirming nor denying")))
    return votes


def area_votes(pc: dict, area_key: str, house: int) -> list:
    """Every method's independent read of one life area."""
    votes: list = []
    hl = (pc.get("house_lords", {}) or {}).get(str(house)) or {}
    lord = hl.get("lord", "")
    planets = pc.get("planets", {}) or {}
    dignity = str(hl.get("lord_dignity") or "").lower()

    # 1. Parashari — lord dignity and placement
    base = {"exalted": 2, "moolatrikona": 2, "own_sign": 1.5,
            "friendly_sign": 1, "neutral_sign": 0, "enemy_sign": -1,
            "debilitated": -2}.get(dignity, 0)
    lord_house = hl.get("lord_house")
    if lord_house in (1, 4, 5, 7, 9, 10):
        base += 0.5
    elif lord_house in (6, 8, 12):
        base -= 1
    classical_direction = "supports" if base > 0.25 else "adds caution to" if base < -0.25 else "gives mixed support to"
    votes.append(Vote(
        "the classical method",
        base,
        f"Independent chart structure {classical_direction} this area."))

    # 2. Ashtakavarga
    sav = (pc.get("ashtakavarga", {}) or {}).get("sav") or []
    if len(sav) >= house:
        score = sav[house - 1]
        av_score = 1.2 if score >= 30 else (-1.2 if score <= 25 else 0)
        av_text = (
            "Structural support is strong for this life area."
            if score >= 30 else
            "Structural support is limited for this life area."
            if score <= 25 else
            "Structural support is moderate for this life area."
        )
        votes.append(Vote(
            "the strength-scoring method",
            av_score,
            av_text))

    # 3. The divisional charts — governing varga, cross-check, and D9
    votes.extend(divisional_votes(pc, area_key, lord))

    # 4. Who actually sits in the house
    occupants = [p for p, d in planets.items() if d.get("house") == house]
    if occupants:
        val = sum(0.8 if p in BENEFIC else -0.8 for p in occupants)
        votes.append(Vote(
            "occupancy",
            max(-2, min(2, val)),
            f"{', '.join(occupants)} sit{'s' if len(occupants) == 1 else ''} here"))

    # 5. Structural yogas — including the cancellation that changes everything
    pillar = pc.get("pillar", {}) or {}
    nb = pillar.get("neecha_bhanga") or {}
    if nb.get("neecha_bhanga_present") and nb.get("planet") == lord:
        votes.append(Vote(
            "the cancellation rule",
            2.5,
            f"{lord} is debilitated but that debilitation is cancelled by "
            f"{nb.get('cancelling_planet', 'another planet')} — classically "
            f"this inverts into unusual strength, often after a slow start"))
    yogas = [y for y in (pillar.get("special_yogas") or [])
             if f"house {house}" in str(y) or f"in {house}th" in str(y)]
    if yogas:
        good = sum(1 for y in yogas if "raja yoga" in y.lower()
                   or "strength" in y.lower())
        votes.append(Vote("chart combinations",
                          1.5 if good else -0.5, yogas[0]))

    # 6. The specialist lanes — everything else the engines already know
    votes.extend(lane_votes(pc, area_key))

    # 7. The palm correlation. Every method above reads the same nine planets,
    # so they disagree about interpretation and never about evidence. This one
    # states what the hand should physically show and can be checked against an
    # object that took no part in building the chart, which is why it is worth
    # a vote of its own even when no photograph was supplied.
    votes.extend(palm_votes(pc, area_key))

    # 8–10. Deep-dive evidence: 108 rules, slow transits, period-clock rating
    try:
        import deep_evidence as DE
        ctx = DE.current()
        if ctx:
            for method, val, because in ctx.vote_triplet(area_key, house):
                votes.append(Vote(method, val, because))
    except Exception:  # noqa: BLE001
        pass
    return votes


def palm_votes(pc: dict, area_key: str, palm_features: Any = None,
               bridge_result: Any = None) -> list:
    """The palm-correlation lane's single vote, or none.

    Imported at call time and only for ImportError: the bridge pulls in OpenCV
    through the palmistry zone module, and a machine without it should lose this
    one lane rather than every confluence verdict in the product. Any other
    exception is a real bug and is left to surface.
    """
    try:
        from palm_astro_bridge import palm_votes as _pv
    except ImportError:
        return []
    bridge = bridge_result
    if bridge is None:
        try:
            import deep_evidence as DE
            ctx = DE.current()
            if ctx is not None:
                bridge = ctx.palm_bridge()
        except Exception:  # noqa: BLE001
            bridge = None
    return _pv(pc, area_key, palm_features, bridge_result=bridge)


def area_verdict(pc: dict, area_key: str, house: int) -> dict:
    """Canonical area verdict. All final direction/confidence decisions happen here."""
    result = build_confluence(pc, area_key, house)
    return result


# ---------------------------------------------------------------------------
# dasha confluence: Vimshottari + Yogini + Jaimini
# ---------------------------------------------------------------------------

def antardashas_for(md_lord: str, start: Optional[date],
                    md_years: float) -> list:
    """Sub-periods of any mahadasha — the precompute only stores the current one."""
    names = [n for n, _ in VIM_YEARS]
    if md_lord not in names or not start:
        return []
    i = names.index(md_lord)
    order = [VIM_YEARS[(i + k) % 9] for k in range(9)]
    out, cursor = [], start
    for lord, years in order:
        end = cursor + timedelta(days=md_years * years / VIM_TOTAL * 365.2425)
        out.append({"ad_lord": lord, "start": cursor, "end": end})
        cursor = end
    return out


def vimshottari_at(pc: dict, when: date) -> dict:
    vim = pc.get("vimshottari", {}) or {}
    seq = list(vim.get("sequence") or [])
    cur = vim.get("current_md") or {}
    if cur:
        seq.append(cur)
    for md in seq:
        a, b = _d(md.get("start")), _d(md.get("end"))
        if not (a and b and a <= when <= b):
            continue
        lord = md.get("md_lord", "")
        for ad in (vim.get("current_md_antardashas") or []):
            x, y = _d(ad.get("start")), _d(ad.get("end"))
            if x and y and x <= when <= y:
                return {"md": lord, "ad": ad.get("ad_lord", "")}
            if ad.get("status") == "current" and not (x and y):
                return {"md": lord, "ad": ad.get("ad_lord", "")}
        years = md.get("md_years") or ((b - a).days / 365.2425)
        for ad in antardashas_for(lord, a, float(years)):
            if ad["start"] <= when <= ad["end"]:
                return {"md": lord, "ad": ad["ad_lord"]}
        return {"md": lord, "ad": ""}
    # Fall back to stamped current when the sequence lacks dated envelopes
    if cur.get("md_lord"):
        ad = ""
        for row in vim.get("current_md_antardashas") or []:
            if row.get("status") == "current":
                ad = row.get("ad_lord") or ""
                break
        return {"md": cur.get("md_lord", ""), "ad": ad}
    return {"md": "", "ad": ""}


def yogini_at(pc: dict, when: date) -> dict:
    for y in (pc.get("yogini", {}) or {}).get("full_cycle") or []:
        a, b = _d(y.get("start")), _d(y.get("end"))
        if a and b and a <= when <= b:
            return y
    return (pc.get("yogini", {}) or {}).get("current_yogini") or {}


def jaimini_at(pc: dict, when: date) -> dict:
    """Current Chara major (maha) and minor (antar) signs with their lords.

    Prefers `active_jaimini_chara` so top-level and nested `jaimini.chara_dasha`
    both resolve — the older path missed nested data whenever a stub top-level
    block existed. Extends short one-cycle tables past their last maha so
    older charts still show a current sign major/minor.
    """
    try:
        from jaimini_chara_dasha import ensure_chara_covers
        ensure_chara_covers(pc, when)
    except Exception:  # noqa: BLE001
        pass

    sign = antar = ""
    maha_start = maha_end = antar_start = antar_end = ""
    try:
        from jaimini_chara_dasha import active_jaimini_chara, get_chara_dasha
        act = active_jaimini_chara(pc, when) or {}
        sign = act.get("maha") or ""
        antar = act.get("antar") or ""
        maha_start, maha_end = act.get("maha_start") or "", act.get("maha_end") or ""
        antar_start, antar_end = act.get("antar_start") or "", act.get("antar_end") or ""
        if not sign or not antar:
            block = get_chara_dasha(pc) or {}
            if not sign:
                cm = block.get("current_maha") or {}
                sign = cm.get("sign") or ""
                maha_start = maha_start or str(cm.get("start") or "")[:10]
                maha_end = maha_end or str(cm.get("end") or "")[:10]
            if not antar:
                ca = block.get("current_antar") or {}
                antar = ca.get("sign") or ""
                antar_start = antar_start or str(ca.get("start") or "")[:10]
                antar_end = antar_end or str(ca.get("end") or "")[:10]
                if not sign:
                    sign = ca.get("maha_sign") or sign
    except Exception:  # noqa: BLE001
        # Last-resort walk of either top-level or nested maha list
        try:
            from jaimini_chara_dasha import get_chara_dasha
            block = get_chara_dasha(pc) or {}
        except Exception:  # noqa: BLE001
            block = pc.get("chara_dasha") or (pc.get("jaimini") or {}).get("chara_dasha") or {}
        for m in (block.get("maha") or []):
            a, b = _d(m.get("start")), _d(m.get("end"))
            if a and b and a <= when <= b:
                sign = m.get("sign") or ""
                maha_start, maha_end = str(a), str(b)
                break
        for an in (block.get("antar") or []):
            a, b = _d(an.get("start")), _d(an.get("end"))
            if a and b and a <= when <= b:
                antar = an.get("sign") or ""
                antar_start, antar_end = str(a), str(b)
                if not sign:
                    sign = an.get("maha_sign") or sign
                break
        if not sign:
            cm = block.get("current_maha") or {}
            sign = cm.get("sign") or ""

    if not sign and not antar:
        return {}
    return {
        "sign": sign,
        "antar": antar,
        "lord": SIGN_LORD.get(sign, ""),
        "antar_lord": SIGN_LORD.get(antar, ""),
        "maha_start": maha_start,
        "maha_end": maha_end,
        "antar_start": antar_start,
        "antar_end": antar_end,
        "stack": "-".join(x for x in (sign, antar) if x),
    }


def bnn_period_vote(pc: dict, md: str, ad: str) -> dict:
    """BNN vote on the running Vimshottari lords (not a separate dasha clock).

    Uses `lord_verdict` from the BNN chart lane — good / neutral / amber —
    so a strong D1 lord that BNN rates amber surfaces as disagreement.
    """
    try:
        from bnn_chart import load_bnn_chart, lord_verdict
        meta = dict(pc.get("meta") or {})
        if not meta.get("lagna_sign"):
            meta["lagna_sign"] = ((pc.get("lagna") or {}).get("sign")
                                  or meta.get("ascendant") or "")
        if not meta.get("client"):
            meta["client"] = meta.get("name") or "Client"
        pc_bnn = dict(pc)
        pc_bnn["meta"] = meta
        if not meta.get("lagna_sign"):
            return {"label": "", "tone": 0.0, "detail": {}}
        ch, _bt = load_bnn_chart(pc=pc_bnn, client_name=str(meta["client"]))
    except Exception:  # noqa: BLE001
        return {"label": "", "tone": 0.0, "detail": {}}

    parts: list[str] = []
    tones: list[float] = []
    detail: dict[str, str] = {}
    for pl in (md, ad):
        if not pl:
            continue
        try:
            v = lord_verdict(ch, pl) or "neutral"
        except Exception:  # noqa: BLE001
            v = "neutral"
        detail[pl] = v
        tones.append({"good": 1.0, "neutral": 0.0, "amber": -1.0}.get(v, 0.0))
        parts.append(f"{pl} {v}")
    if not parts:
        return {"label": "", "tone": 0.0, "detail": {}}
    return {
        "label": " · ".join(parts),
        "tone": sum(tones) / len(tones),
        "detail": detail,
    }


def dasha_confluence(pc: dict, when: Optional[date] = None) -> dict:
    """What Vimshottari, Yogini, Chara, and BNN say about the same moment."""
    when = when or date.today()
    vim = vimshottari_at(pc, when)
    yog = yogini_at(pc, when)
    jai = jaimini_at(pc, when)

    planets = pc.get("planets", {}) or {}

    def planet_tone(name: str) -> float:
        if not name:
            return 0.0
        info = planets.get(name) or {}
        dig = str(info.get("dignity") or "").lower()
        v = {"exalted": 1.5, "moolatrikona": 1.5, "own_sign": 1.0,
             "friendly_sign": 0.5, "neutral_sign": 0.0, "enemy_sign": -0.75,
             "debilitated": -1.5}.get(dig, 0.0)
        if str(info.get("functional_status") or "").endswith("benefic"):
            v += 0.5
        elif str(info.get("functional_status") or "").endswith("malefic"):
            v -= 0.5
        return v

    readings = []
    v_tone = (planet_tone(vim.get("md")) + planet_tone(vim.get("ad"))) / 2
    readings.append({
        "system": "the main cycle",
        "label": f"{vim.get('md','')}–{vim.get('ad','')}".strip("–"),
        "tone": v_tone,
        "kind": "vimshottari",
        "planets": [p for p in (vim.get("md"), vim.get("ad")) if p],
    })

    y_tone = {"auspicious": 1.2, "inauspicious": -1.2}.get(
        str(yog.get("tone") or "").lower(), 0.0)
    readings.append({
        "system": "the lunar cycle",
        "label": (f"{yog.get('yogini','')} ({yog.get('lord','')})"
                  if yog.get("yogini") and yog.get("lord")
                  else (yog.get("yogini") or "")),
        "tone": y_tone if yog.get("tone") else planet_tone(yog.get("lord") or ""),
        "kind": "yogini",
        "planets": [yog.get("lord")] if yog.get("lord") else [],
    })

    sign = jai.get("sign", "")
    antar = jai.get("antar", "")
    j_lord = jai.get("lord") or SIGN_LORD.get(sign, "")
    a_lord = jai.get("antar_lord") or SIGN_LORD.get(antar, "")
    if sign and antar:
        label = f"{sign}–{antar} ({j_lord}–{a_lord})" if j_lord or a_lord else f"{sign}–{antar}"
    elif sign:
        label = f"{sign} ({j_lord})" if j_lord else sign
    else:
        label = ""
    j_tone_parts = [planet_tone(p) for p in (j_lord, a_lord) if p]
    j_tone = sum(j_tone_parts) / len(j_tone_parts) if j_tone_parts else 0.0
    readings.append({
        "system": "the sign-based cycle",
        "label": label,
        "tone": j_tone,
        "kind": "chara",
        "planets": [p for p in (j_lord, a_lord) if p],
        "maha": sign,
        "antar": antar,
    })

    bnn = bnn_period_vote(pc, vim.get("md") or "", vim.get("ad") or "")
    if bnn.get("label"):
        readings.append({
            "system": "the nadi read",
            "label": bnn["label"],
            "tone": bnn["tone"],
            "kind": "bnn",
            "planets": list((bnn.get("detail") or {}).keys()),
            "detail": bnn.get("detail") or {},
        })

    live = [r for r in readings if r["label"]]
    score = sum(r["tone"] for r in live) / len(live) if live else 0.0
    direction = "up" if score >= 0.4 else ("down" if score <= -0.4 else "mixed")
    same = sum(1 for r in live
               if ("up" if r["tone"] > 0.2 else
                   "down" if r["tone"] < -0.2 else "mixed") == direction)

    return {"when": when, "readings": live, "direction": direction,
            "score": round(score, 2),
            "agreement": f"{same} of {len(live)} timing systems agree" if live else "",
            "unanimous": same == len(live) and len(live) >= 3,
            "vim": vim, "yogini": yog, "chara": jai, "bnn": bnn}


# ---------------------------------------------------------------------------
# personality — the part that makes a reader trust the rest
# ---------------------------------------------------------------------------

LAGNA_TRAIT = {
    "Aries": "You tend to act quickly when you see an opportunity, sometimes before everyone around you is ready.",
    "Taurus": "You are careful about starting, and unusually steady once you have committed.",
    "Gemini": "You often hold several possibilities at once, which can look restless to people who prefer one track.",
    "Cancer": "You usually sense the mood of a room early, and you can carry more of other people's feelings than you show.",
    "Leo": "Being seen for your work matters to you — not only praise, but genuine recognition.",
    "Virgo": "You often notice what needs improving first. That precision is a strength, and it can also tire you.",
    "Libra": "You tend to weigh both sides carefully, so decisions can take more from you than they take from others.",
    "Scorpio": "You keep some things private, and you often read people a little sooner than they read you.",
    "Sagittarius": "You need room to move. Anything that feels too confining tends not to last with you.",
    "Capricorn": "You are usually building for the long term, and shortcuts rarely impress you.",
    "Aquarius": "You can be part of a group without fully merging into it.",
    "Pisces": "You absorb a lot from your surroundings — a gift that also makes quiet time important.",
}

MOON_TRAIT = {
    "Aries": "When pressure rises, you prefer a clear decision sooner rather than later.",
    "Taurus": "When pressure rises, you tend to steady yourself and wait it out.",
    "Gemini": "When pressure rises, talking it through with someone usually helps.",
    "Cancer": "When pressure rises, you lean toward familiar people and familiar places.",
    "Leo": "Recognition matters to you, especially when you've carried a difficult responsibility for a long time.",
    "Virgo": "When pressure rises, organising something concrete often helps you regain your footing.",
    "Libra": "When pressure rises, you may smooth things over — sometimes at a personal cost.",
    "Scorpio": "When pressure rises, you can go quiet and inward; people sometimes misread that as anger.",
    "Sagittarius": "When pressure rises, you look for space — perspective, movement, or a change of scene.",
    "Capricorn": "When pressure rises, you tend to work harder. Rest can feel unproductive even when it is needed.",
    "Aquarius": "When pressure rises, you often step back and analyse the situation from the outside.",
    "Pisces": "When pressure rises, focus can drift; a steady person nearby helps you come back.",
}

AK_TRAIT = {
    "Sun": "your standing in the world",
    "Moon": "your emotional life and the people you care for",
    "Mars": "your fights, the ones worth having and the ones not",
    "Mercury": "your mind and how you use it",
    "Jupiter": "what you believe and who you teach",
    "Venus": "love, beauty, and what you are willing to give for them",
    "Saturn": "endurance, and what you build slowly",
    "Rahu": "the hunger that does not switch off",
}


def _human_yoga(line: str) -> str:
    """Cached precomputes may still carry Sanskrit labels — never show those raw."""
    import re
    s = line or ""
    s = re.sub(
        r"\bin\s+(\d+)(?:st|nd|rd|th)\s*\(upachaya/trishadaya\)\s*—\s*competitive strength",
        r"in the \1th house — a growth placement that builds competitive strength over time",
        s,
        flags=re.I,
    )
    s = re.sub(
        r"\((house\s+\d+),\s*kendra\)\s*—\s*potential raja yoga",
        r"(\1) — a classic power combination",
        s,
        flags=re.I,
    )
    s = re.sub(r"\bupachaya/trishadaya\b", "growth house", s, flags=re.I)
    s = re.sub(r"\braja yoga\b", "power combination", s, flags=re.I)
    s = re.sub(r"\bkendra\b", "angular house", s, flags=re.I)
    return s


def personality(pc: dict) -> dict:
    from report_language import client_prose
    lagna = (pc.get("lagna") or {}).get("sign", "")
    moon = pc.get("planets", {}).get("Moon") or {}
    ak = (pc.get("jaimini") or {}).get("atmakaraka", "")
    pillar = pc.get("pillar", {}) or {}
    traits = [client_prose(t) for t in (LAGNA_TRAIT.get(lagna), MOON_TRAIT.get(moon.get("sign"))) if t]
    if ak == "Mars":
        traits.append(client_prose(
            "A recurring theme in your life is learning which battles deserve "
            "your energy — and which ones are better left alone."))
        traits.append(client_prose(
            "Mars is the main astrological influence behind this theme."))
    elif ak:
        traits.append(client_prose(
            f"The thread running through your whole life is "
            f"{AK_TRAIT.get(ak, 'your own path')}. "
            f"{ak} carries that in your chart."))
    nb = pillar.get("neecha_bhanga") or {}
    if nb.get("neecha_bhanga_present"):
        traits.append(
            f"There is a reversal built into your chart: {nb.get('planet')} starts "
            f"from a weak position and is rescued by {nb.get('cancelling_planet')}. "
            f"People with this pattern usually under-perform early and are "
            f"badly underestimated as a result.")
    yogas = [_human_yoga(y) for y in (pillar.get("special_yogas") or [])[:4]]
    return {"lagna": lagna, "moon_sign": moon.get("sign", ""),
            "nakshatra": moon.get("nakshatra", ""), "atmakaraka": ak,
            "traits": traits,
            "yogas": yogas}


# ---------------------------------------------------------------------------
# MiniLM semantic overlay — vedic_confluence_report clusters → card verdicts
# ---------------------------------------------------------------------------
# The long-form confluence already groups lane signals with SentenceTransformer
# (paraphrase-multilingual-MiniLM-L12-v2). The card report used rule votes only.
# This bridge lets both share the same semantic clusters.

_AREA_DOMAIN = {
    "career": "career", "money": "finance", "love": "marriage",
    "home": "property", "children": "children", "health": "health",
    "learning": "travel", "inner": "personality",
}

_semantic_by_domain: dict = {}
_semantic_mode: str = "rules"


def set_semantic_clusters(clusters) -> None:
    """Register MiniLM domain clusters before report_cards renders."""
    global _semantic_by_domain, _semantic_mode
    _semantic_by_domain = {}
    for cl in clusters or []:
        dom = _cluster_field(cl, "domain")
        if not dom:
            continue
        prev = _semantic_by_domain.get(dom)
        sc = float(_cluster_field(cl, "score", 0) or 0)
        if prev is None or sc > float(_cluster_field(prev, "score", 0) or 0):
            _semantic_by_domain[dom] = cl
    try:
        import semantic_fallback
        _semantic_mode = "degraded_lexical" if semantic_fallback.degraded() else "minilm"
    except Exception:
        _semantic_mode = "minilm"


def clear_semantic_clusters() -> None:
    _semantic_by_domain.clear()


def semantic_mode() -> str:
    return _semantic_mode


def _cluster_field(cl, name: str, default=None):
    if isinstance(cl, dict):
        return cl.get(name, default)
    return getattr(cl, name, default)


def semantic_cluster_for_area(area_key: str):
    dom = _AREA_DOMAIN.get(area_key)
    return _semantic_by_domain.get(dom) if dom else None


def _dir_from_cluster(cl) -> str:
    return {"positive": "up", "caution": "down"}.get(
        _cluster_field(cl, "direction", "neutral"), "mixed")


def merge_semantic_verdict(area_key: str, verdict: dict) -> dict:
    """Add semantic/language context without changing the canonical verdict.

    Semantic clustering is allowed to help wording and explanatory confidence,
    but it must never turn a mixed or cautionary chart into a supportive one.
    """
    cl = semantic_cluster_for_area(area_key)
    if not cl:
        return verdict
    out = dict(verdict)
    systems = _cluster_field(cl, "systems", []) or []
    conf = str(_cluster_field(cl, "confidence", "MODERATE") or "MODERATE")
    texts = [str(t).strip() for t in (_cluster_field(cl, "texts", []) or []) if t]
    out["semantic"] = True
    out["semantic_mode"] = _semantic_mode
    out["semantic_systems"] = systems
    out["semantic_texts"] = texts[:3]
    # Preserve canonical score, direction, family agreement and confidence.
    # Semantic confidence is retained only as metadata for diagnostics.
    out["semantic_confidence"] = conf.lower()
    out["agreement"] = out.get("family_agreement") or customer_confidence(out)
    return out


def customer_confidence(verdict: dict) -> str:
    """Human confidence derived from canonical evidence families."""
    try:
        conf = str(verdict.get("confidence") or "").lower()
        return {
            "very high": "Very strong confluence",
            "high": "Strong confluence",
            "moderate": "Moderate confluence",
            "low": "Mixed evidence",
        }.get(conf, "")
    except Exception:  # noqa: BLE001
        return ""


def headline_from_verdict(area_key: str, direction: str, verdict: dict) -> str:
    """Plain scenario headline — never raw vote because strings."""
    try:
        import predict_voice as PV
        return PV.AREA_SCENE.get((area_key, direction), "")
    except Exception:  # noqa: BLE001
        return ""
