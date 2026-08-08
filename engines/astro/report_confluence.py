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
its own tone, and Jaimini's sign-based periods move independently. Where all
three agree, we say so and the confidence is high. Where they split, the reader
is told it is a mixed window rather than being handed false certainty.

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
    "Goel": "the disease-indication method",
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
    votes.append(Vote(
        "the classical method",
        base,
        f"{lord} rules it, {dignity.replace('_', ' ')}"
        + (f", placed in your {_ord(lord_house)}" if lord_house else "")))

    # 2. Ashtakavarga
    sav = (pc.get("ashtakavarga", {}) or {}).get("sav") or []
    if len(sav) >= house:
        score = sav[house - 1]
        votes.append(Vote(
            "the strength-scoring method",
            1.2 if score >= 30 else (-1.2 if score <= 25 else 0),
            f"house strength {score} of 56"
            + (" — above average" if score >= 30
               else " — below average" if score <= 25 else " — average")))

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
    """Combine the votes into one verdict plus an honest confidence."""
    votes = area_votes(pc, area_key, house)
    if not votes:
        return {"direction": "mixed", "score": 0.0, "votes": [],
                "agreement": "", "confidence": "low"}

    score = sum(v.value for v in votes) / len(votes)
    direction = "up" if score >= 0.5 else ("down" if score <= -0.5 else "mixed")

    # Agreement is measured over the methods that actually took a side. With
    # a dozen methods voting, counting abstentions against the majority made
    # every area read "low confidence" — and a confidence chip that always says
    # low tells the customer nothing. A method with no opinion is not a
    # dissenter. (It also fixed the inverse bug: three neutral votes used to
    # score "3 of 3 agree, high" on a verdict of mixed.)
    total = len(votes)
    decided = [v for v in votes if v.direction != "mixed"]
    ups = sum(1 for v in decided if v.direction == "up")
    downs = sum(1 for v in decided if v.direction == "down")
    same = sum(1 for v in decided if v.direction == direction)
    ratio = same / len(decided) if decided else 0.0
    if direction == "mixed":
        confidence = "low"                  # we are not confident, by definition
    elif ratio >= 0.75 and len(decided) >= 4:
        confidence = "high"
    elif ratio >= 0.6:
        confidence = "moderate"
    else:
        confidence = "low"
    if direction == "mixed":
        # A genuine split is a finding, not a failure — and reporting it as
        # "0 of 5 methods agree" made a real result look like a broken one.
        if ups and downs:
            agreement = f"the methods split {ups}–{downs} here"
        elif ups or downs:
            # Everything that leans, leans one way, but not hard enough to call.
            agreement = (f"{ups or downs} of {total} methods lean "
                         f"{'positive' if ups else 'negative'}, the rest are neutral")
        else:
            agreement = f"none of the {total} methods takes a side"
    else:
        agreement = f"{same} of {len(decided)} methods with a view agree"
    result = {"direction": direction, "score": round(score, 2), "votes": votes,
              "agreement": agreement, "confidence": confidence}
    try:
        result["agreement"] = customer_confidence(result) or agreement
    except Exception:  # noqa: BLE001
        pass
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
        years = md.get("md_years") or ((b - a).days / 365.2425)
        for ad in antardashas_for(lord, a, float(years)):
            if ad["start"] <= when <= ad["end"]:
                return {"md": lord, "ad": ad["ad_lord"]}
        return {"md": lord, "ad": ""}
    return {"md": "", "ad": ""}


def yogini_at(pc: dict, when: date) -> dict:
    for y in (pc.get("yogini", {}) or {}).get("full_cycle") or []:
        a, b = _d(y.get("start")), _d(y.get("end"))
        if a and b and a <= when <= b:
            return y
    return (pc.get("yogini", {}) or {}).get("current_yogini") or {}


def jaimini_at(pc: dict, when: date) -> dict:
    ch = pc.get("chara_dasha", {}) or {}
    for m in (ch.get("maha") or []):
        a, b = _d(m.get("start")), _d(m.get("end"))
        if a and b and a <= when <= b:
            return m
    return ch.get("current_maha") or {}


def dasha_confluence(pc: dict, when: Optional[date] = None) -> dict:
    """What all three timing systems say about the same moment."""
    when = when or date.today()
    vim = vimshottari_at(pc, when)
    yog = yogini_at(pc, when)
    jai = jaimini_at(pc, when)

    planets = pc.get("planets", {}) or {}
    hl = pc.get("house_lords", {}) or {}

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
    })

    y_tone = {"auspicious": 1.2, "inauspicious": -1.2}.get(
        str(yog.get("tone") or "").lower(), 0.0)
    readings.append({
        "system": "the lunar cycle",
        "label": (f"{yog.get('yogini','')} ({yog.get('lord','')})"
                  if yog.get("yogini") and yog.get("lord")
                  else (yog.get("yogini") or "")),
        "tone": y_tone,
    })

    sign = jai.get("sign", "")
    j_lord = SIGN_LORD.get(sign, "")
    readings.append({
        "system": "the sign-based cycle",
        "label": f"{sign} ({j_lord})" if sign and j_lord else (sign or ""),
        "tone": planet_tone(j_lord),
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
            "unanimous": same == len(live) and len(live) >= 3}


# ---------------------------------------------------------------------------
# personality — the part that makes a reader trust the rest
# ---------------------------------------------------------------------------

LAGNA_TRAIT = {
    "Aries": "You move first and think about it afterwards, usually faster than the people around you are comfortable with.",
    "Taurus": "You are slow to start and almost impossible to stop once you have.",
    "Gemini": "You think in several directions at once, which reads as restlessness to people who only think in one.",
    "Cancer": "You feel the room before anyone speaks, and you carry more of other people's weather than you admit.",
    "Leo": "You need your work to be seen. Not praised. Seen. There is a difference and you know it.",
    "Virgo": "You notice the flaw first. It makes you excellent and it makes you tired.",
    "Libra": "You weigh both sides so fairly that deciding costs you more than it costs most people.",
    "Scorpio": "You keep more back than you let on, and you read other people faster than they read you.",
    "Sagittarius": "You need room. Anything that fences you in gets left behind eventually.",
    "Capricorn": "You are building something long, and you are quietly contemptuous of shortcuts.",
    "Aquarius": "You are in the group without ever quite being of it.",
    "Pisces": "You absorb everything, which is your gift and the reason you need to be alone so often.",
}

MOON_TRAIT = {
    "Aries": "Under pressure you get sharp and want it settled today.",
    "Taurus": "Under pressure you go still and wait it out.",
    "Gemini": "Under pressure you talk it through with anyone available.",
    "Cancer": "Under pressure you retreat to whoever feels like home.",
    "Leo": "Under pressure you need someone to tell you the work mattered.",
    "Virgo": "Under pressure you organise something. It is how you take back control.",
    "Libra": "Under pressure you smooth things over, sometimes at your own cost.",
    "Scorpio": "Under pressure you go quiet and deep, and people mistake it for anger.",
    "Sagittarius": "Under pressure you look for the exit, or a plane ticket.",
    "Capricorn": "Under pressure you work. Rest feels like losing.",
    "Aquarius": "Under pressure you detach and analyse yourself from the outside.",
    "Pisces": "Under pressure you drift, and need someone to bring you back.",
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
    if ak:
        traits.append(client_prose(
            f"The thread running through your whole life is {AK_TRAIT.get(ak, 'your own path')}. "
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
    """Rule votes supply direction and evidence; semantic cluster adjusts confidence only."""
    cl = semantic_cluster_for_area(area_key)
    if not cl:
        return verdict
    systems = _cluster_field(cl, "systems", []) or []
    conf = str(_cluster_field(cl, "confidence", "MODERATE") or "MODERATE")
    direction = _dir_from_cluster(cl)
    texts = [str(t).strip() for t in (_cluster_field(cl, "texts", []) or []) if t]
    out = dict(verdict)
    # Keep rule-vote direction unless semantic cluster is unanimous and strong
    if systems and len(systems) >= 2:
        out["direction"] = direction
    out["semantic"] = True
    out["semantic_mode"] = _semantic_mode
    # Do NOT replace headline with BOOK_LINES affirmation — keep concrete CLAIMS
    n = len(systems)
    out["confidence"] = conf.lower()
    out["agreement"] = customer_confidence(out) or (
        f"{n} methods align · {conf}" if n else f"semantic cluster · {conf}")
    # Keep structured votes for scoring; do not attach raw because strings
    # or deep_evidence prose to customer-facing evidence lists.
    out["evidence"] = []
    return out


def customer_confidence(verdict: dict) -> str:
    """Plain confidence chip — never 'N of M methods with a view agree'."""
    try:
        import predict_voice as PV
        votes = verdict.get("votes") or []
        direction = verdict.get("direction", "mixed")
        decided = [v for v in votes if getattr(v, "direction", "mixed") != "mixed"]
        same = sum(1 for v in decided if getattr(v, "direction", "mixed") == direction)
        return PV.confidence_word(same, len(decided) or len(votes), direction)
    except Exception:  # noqa: BLE001
        return ""


def headline_from_verdict(area_key: str, direction: str, verdict: dict) -> str:
    """Plain scenario headline — never raw vote because strings."""
    try:
        import predict_voice as PV
        return PV.AREA_SCENE.get((area_key, direction), "")
    except Exception:  # noqa: BLE001
        return ""
