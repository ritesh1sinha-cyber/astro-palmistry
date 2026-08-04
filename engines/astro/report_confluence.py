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
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional

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
        + (f", placed in your {lord_house}th" if lord_house else "")))

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

    # 3. The divisional chart that governs this area
    varga, varga_name = AREA_VARGA.get(area_key, ("", ""))
    if varga and lord:
        vsign = _varga_sign(pc, varga, lord)
        if vsign:
            v = _dignity_in(lord, vsign)
            votes.append(Vote(
                varga_name,
                v,
                f"in {varga_name}, {lord} sits in {vsign}"
                + (" — exalted there" if v >= 2 else
                   " — debilitated there" if v <= -2 else
                   " — in its own sign" if v > 0 else "")))

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
    return votes


def area_verdict(pc: dict, area_key: str, house: int) -> dict:
    """Combine the votes into one verdict plus an honest confidence."""
    votes = area_votes(pc, area_key, house)
    if not votes:
        return {"direction": "mixed", "score": 0.0, "votes": [],
                "agreement": "", "confidence": "low"}

    score = sum(v.value for v in votes) / len(votes)
    direction = "up" if score >= 0.5 else ("down" if score <= -0.5 else "mixed")

    total = len(votes)
    ups = sum(1 for v in votes if v.direction == "up")
    downs = sum(1 for v in votes if v.direction == "down")
    same = sum(1 for v in votes if v.direction == direction)
    ratio = same / total
    confidence = "high" if ratio >= 0.8 else ("moderate" if ratio >= 0.6 else "low")
    if direction == "mixed" and ups and downs:
        # A genuine split is a finding, not a failure — and reporting it as
        # "0 of 5 methods agree" made a real result look like a broken one.
        agreement = f"the methods split {ups}–{downs} here"
    else:
        agreement = f"{same} of {total} methods agree"
    return {"direction": direction, "score": round(score, 2), "votes": votes,
            "agreement": agreement, "confidence": confidence}


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
    "Aries": "You move first and think about it afterwards — usually faster than the people around you are comfortable with.",
    "Taurus": "You are slow to start and almost impossible to stop once you have.",
    "Gemini": "You think in several directions at once, which reads as restlessness to people who only think in one.",
    "Cancer": "You feel the room before anyone speaks, and you carry more of other people's weather than you admit.",
    "Leo": "You need your work to be seen. Not praised — seen. There is a difference and you know it.",
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
    "Gemini": "Under pressure you talk it through — with anyone available.",
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
    "Mars": "your fights — the ones worth having and the ones not",
    "Mercury": "your mind and how you use it",
    "Jupiter": "what you believe and who you teach",
    "Venus": "love, beauty, and what you are willing to give for them",
    "Saturn": "endurance, and what you build slowly",
    "Rahu": "the hunger that does not switch off",
}


def personality(pc: dict) -> dict:
    lagna = (pc.get("lagna") or {}).get("sign", "")
    moon = pc.get("planets", {}).get("Moon") or {}
    ak = (pc.get("jaimini") or {}).get("atmakaraka", "")
    pillar = pc.get("pillar", {}) or {}
    traits = [t for t in (LAGNA_TRAIT.get(lagna), MOON_TRAIT.get(moon.get("sign"))) if t]
    if ak:
        traits.append(
            f"The thread running through your whole life is {AK_TRAIT.get(ak, 'your own path')} "
            f"— {ak} carries that in your chart.")
    nb = pillar.get("neecha_bhanga") or {}
    if nb.get("neecha_bhanga_present"):
        traits.append(
            f"There is a reversal built into your chart: {nb.get('planet')} starts "
            f"from a weak position and is rescued by {nb.get('cancelling_planet')}. "
            f"People with this pattern usually under-perform early and are "
            f"badly underestimated as a result.")
    return {"lagna": lagna, "moon_sign": moon.get("sign", ""),
            "nakshatra": moon.get("nakshatra", ""), "atmakaraka": ak,
            "traits": traits,
            "yogas": (pillar.get("special_yogas") or [])[:4]}
