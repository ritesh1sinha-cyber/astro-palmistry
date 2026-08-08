#!/usr/bin/env python3
"""Traditional Western horary judgment engine (Lilly / Anthony Louis) — no LLM.

Pure-Python application of the documented rules in
``.cursor/skills/western-horary/SKILL.md``: essential dignities, significators,
aspects & perfection, reception, the Moon's condition, Pars Fortuna and a
testimony tally → verdict. Timing and Moon void-of-course reuse Swiss Ephemeris
(MOSEPH), matching ``western_horary_precompute.py`` /
``validate_rules_v6_ephemeris.py``.
"""
from __future__ import annotations

import json
import math
import re
from datetime import date, timedelta
from pathlib import Path

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_IDX = {s: i for i, s in enumerate(SIGNS)}
ELEMENT = {0: "Fire", 1: "Earth", 2: "Air", 3: "Water"}  # sign_idx % 4

# Traditional domicile rulers by sign index.
DOMICILE = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
            "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
MODERN_CORULER = {"Aquarius": "Uranus", "Pisces": "Neptune", "Scorpio": "Pluto"}
# Exaltation: sign -> (planet, degree).
EXALT = {"Aries": ("Sun", 19), "Taurus": ("Moon", 3), "Cancer": ("Jupiter", 15),
         "Virgo": ("Mercury", 15), "Libra": ("Saturn", 21), "Capricorn": ("Mars", 28),
         "Pisces": ("Venus", 27)}
# Triplicity rulers (Lilly): element -> (day, night).
TRIPLICITY = {"Fire": ("Sun", "Jupiter"), "Earth": ("Venus", "Moon"),
              "Air": ("Saturn", "Mercury"), "Water": ("Mars", "Mars")}
# Egyptian terms: sign -> list of (planet, upper_bound_degree).
TERMS = {
    "Aries": [("Jupiter", 6), ("Venus", 12), ("Mercury", 20), ("Mars", 25), ("Saturn", 30)],
    "Taurus": [("Venus", 8), ("Mercury", 14), ("Jupiter", 22), ("Saturn", 27), ("Mars", 30)],
    "Gemini": [("Mercury", 6), ("Jupiter", 12), ("Venus", 17), ("Mars", 24), ("Saturn", 30)],
    "Cancer": [("Mars", 7), ("Venus", 13), ("Mercury", 19), ("Jupiter", 26), ("Saturn", 30)],
    "Leo": [("Jupiter", 6), ("Venus", 11), ("Saturn", 18), ("Mercury", 24), ("Mars", 30)],
    "Virgo": [("Mercury", 7), ("Venus", 17), ("Jupiter", 21), ("Mars", 28), ("Saturn", 30)],
    "Libra": [("Saturn", 6), ("Mercury", 14), ("Jupiter", 21), ("Venus", 28), ("Mars", 30)],
    "Scorpio": [("Mars", 7), ("Venus", 11), ("Mercury", 19), ("Jupiter", 24), ("Saturn", 30)],
    "Sagittarius": [("Jupiter", 12), ("Venus", 17), ("Mercury", 21), ("Saturn", 26), ("Mars", 30)],
    "Capricorn": [("Mercury", 7), ("Jupiter", 14), ("Venus", 22), ("Saturn", 26), ("Mars", 30)],
    "Aquarius": [("Mercury", 7), ("Venus", 13), ("Jupiter", 20), ("Mars", 25), ("Saturn", 30)],
    "Pisces": [("Venus", 12), ("Jupiter", 16), ("Mercury", 19), ("Mars", 28), ("Saturn", 30)],
}
# Faces / decans (Chaldean order): sign -> [planet, planet, planet] for 0-10,10-20,20-30.
FACES = {
    "Aries": ["Mars", "Sun", "Venus"], "Taurus": ["Mercury", "Moon", "Saturn"],
    "Gemini": ["Jupiter", "Mars", "Sun"], "Cancer": ["Venus", "Mercury", "Moon"],
    "Leo": ["Saturn", "Jupiter", "Mars"], "Virgo": ["Sun", "Venus", "Mercury"],
    "Libra": ["Moon", "Saturn", "Jupiter"], "Scorpio": ["Mars", "Sun", "Venus"],
    "Sagittarius": ["Mercury", "Moon", "Saturn"], "Capricorn": ["Jupiter", "Mars", "Sun"],
    "Aquarius": ["Venus", "Mercury", "Moon"], "Pisces": ["Saturn", "Jupiter", "Mars"],
}
# Moieties (half-orbs) for orb-sum aspects.
MOIETY = {"Sun": 7.5, "Moon": 6.0, "Mercury": 3.5, "Venus": 4.0, "Mars": 3.75,
          "Jupiter": 4.5, "Saturn": 4.5, "Uranus": 2.5, "Neptune": 2.5, "Pluto": 2.5}
ASPECTS = {0: "conjunction", 60: "sextile", 90: "square", 120: "trine", 180: "opposition"}
BENEFIC = {"Venus", "Jupiter"}
MALEFIC = {"Mars", "Saturn"}
# Natural (universal) significators by house topic — Lilly/Louis.
NATURAL_SIGNIFICATOR = {
    1: [], 2: ["Jupiter", "Venus"], 3: ["Mercury"], 4: ["Saturn", "Moon"],
    5: ["Jupiter", "Venus"], 6: ["Mars", "Mercury"], 7: ["Venus", "Mars"],
    8: ["Saturn"], 9: ["Jupiter"], 10: ["Sun", "Jupiter"], 11: ["Jupiter"], 12: ["Saturn"],
}

# Quesited house by topic keyword (Louis Table 2 themes).
HOUSE_TOPICS = {
    1: "the querent / their body & life",
    2: "money, movable possessions, self-earned income",
    3: "siblings, neighbours, short trips, communication, documents",
    4: "home, land, property, father, the end of the matter",
    5: "children, pregnancy, romance, creativity, pleasure, speculation",
    6: "health & illness, work & service, small animals",
    7: "marriage, the partner, open enemies, the other party",
    8: "death, inheritance, the partner's money, surgery, fear",
    9: "long journeys, religion, law, higher study, the foreign",
    10: "career, status, the employer, promotion, reputation, mother",
    11: "hopes & wishes, friends, gains from career, groups",
    12: "secret enemies, confinement, loss, self-undoing, large animals",
}
KEYWORD_HOUSE = [
    (("bonus", "promotion", "raise", "salary", "job", "career", "employer", "boss", "work", "position", "reputation"), 10),
    (("money", "loan", "pay", "income", "afford", "buy", "wealth", "earn", "funds"), 2),
    (("marry", "marriage", "spouse", "partner", "relationship", "wife", "husband", "lover", "divorce", "ex"), 7),
    (("child", "children", "son", "daughter", "pregnan", "baby", "speak", "conceive"), 5),
    (("health", "ill", "illness", "disease", "sick", "recover", "surgery", "operation"), 6),
    (("travel", "abroad", "foreign", "visa", "journey", "immigration", "study", "exam", "court", "law", "legal", "lawsuit"), 9),
    (("house", "home", "property", "land", "real estate", "father", "flat", "apartment"), 4),
    (("inherit", "legacy", "death", "will ", "insurance", "debt"), 8),
    (("friend", "hope", "wish", "gain"), 11),
    (("enemy", "enemies", "prison", "jail", "hidden", "secret", "fear", "loss"), 12),
    (("sibling", "brother", "sister", "neighbour", "neighbor", "letter", "message", "email"), 3),
    (("lost", "find", "missing", "theft", "stolen", "where is"), 2),
]


def norm360(x: float) -> float:
    return x % 360.0


def ang_sep(a: float, b: float) -> float:
    d = abs(norm360(a) - norm360(b))
    return min(d, 360.0 - d)


def sign_of(lon: float) -> str:
    return SIGNS[int(norm360(lon) // 30)]


def deg_in_sign(lon: float) -> float:
    return norm360(lon) % 30.0


def detriment_signs(planet: str) -> set[str]:
    out = set()
    for i, ruler in enumerate(DOMICILE):
        if ruler == planet:
            out.add(SIGNS[(i + 6) % 12])
    return out


def fall_sign(planet: str) -> str | None:
    for sign, (p, _deg) in EXALT.items():
        if p == planet:
            return SIGNS[(SIGN_IDX[sign] + 6) % 12]
    return None


def essential_dignities(planet: str, lon: float, is_day: bool) -> dict:
    """Return dignities/debilities + Lilly-style score for a planet at a longitude."""
    sign = sign_of(lon)
    deg = deg_in_sign(lon)
    score = 0
    digs: list[str] = []
    debs: list[str] = []
    if DOMICILE[SIGN_IDX[sign]] == planet:
        digs.append("domicile"); score += 5
    if sign in EXALT and EXALT[sign][0] == planet:
        digs.append("exaltation"); score += 4
    trip = TRIPLICITY[ELEMENT[SIGN_IDX[sign] % 4]]
    if planet == (trip[0] if is_day else trip[1]):
        digs.append("triplicity"); score += 3
    for p, ub in TERMS[sign]:
        if deg < ub:
            if p == planet:
                digs.append("term"); score += 2
            break
    if FACES[sign][min(2, int(deg // 10))] == planet:
        digs.append("face"); score += 1
    if sign in detriment_signs(planet):
        debs.append("detriment"); score -= 5
    if fall_sign(planet) == sign:
        debs.append("fall"); score -= 4
    peregrine = not digs and not debs
    if peregrine:
        debs.append("peregrine"); score -= 5
    return {"sign": sign, "deg": deg, "dignities": digs, "debilities": debs,
            "score": score, "peregrine": peregrine}


def dignity_phrase(planet: str, ed: dict) -> str:
    if "domicile" in ed["dignities"]:
        return f"in its own sign ({ed['sign']}) — strong, comfortable, acting freely"
    if "exaltation" in ed["dignities"]:
        return f"exalted in {ed['sign']} — dignified, well-regarded, doing well"
    if "detriment" in ed["debilities"] and "fall" in ed["debilities"]:
        return f"in both detriment and fall ({ed['sign']}) — severely weakened, the matter struggles through this planet"
    if "detriment" in ed["debilities"]:
        return f"in detriment ({ed['sign']}) — weakened, uncomfortable, working against itself"
    if "fall" in ed["debilities"]:
        return f"in fall ({ed['sign']}) — undermined, low resources, effort-heavy"
    if ed["peregrine"]:
        return f"peregrine in {ed['sign']} — no essential strength, a bit rudderless"
    minor = ed["dignities"][0] if ed["dignities"] else "minor dignity"
    return f"in {ed['sign']} with {minor} dignity — modest, mixed strength"


# ───────────────────────── aspects & perfection ─────────────────────────
def aspect_between(p1: dict, p2: dict, names: tuple[str, str]) -> dict | None:
    """Detect a Ptolemaic aspect; classify applying/separating using speeds."""
    lon1, lon2 = p1["longitude"], p2["longitude"]
    sp1, sp2 = p1.get("speed_deg_per_day", 0.0), p2.get("speed_deg_per_day", 0.0)
    sep = ang_sep(lon1, lon2)
    orb_allow = (MOIETY.get(names[0], 4) + MOIETY.get(names[1], 4))
    best = None
    for ang, label in ASPECTS.items():
        delta = abs(sep - ang)
        if delta <= orb_allow and (best is None or delta < best[1]):
            best = (label, delta, ang)
    if not best:
        return None
    label, delta, ang = best
    # Applying if |separation| moves toward the exact aspect angle over time.
    res0 = abs(ang_sep(lon1, lon2) - ang)
    res1 = abs(ang_sep(lon1 + sp1 * 0.05, lon2 + sp2 * 0.05) - ang)
    applying = res1 < res0
    # Mutual application: one planet direct, the other retrograde, both moving toward
    # the aspect — Louis calls this "a potent force in bringing an event to pass."
    mutual_app = applying and ((sp1 < 0) != (sp2 < 0))
    return {"aspect": label, "angle": ang, "orb": round(delta, 2),
            "applying": applying, "exact": delta < 0.5, "mutual_application": mutual_app}


# Minor aspects (Louis uses the semi-sextile as a "financial" 2nd/12th-house contact and
# the quincunx as an awkward 6th/8th contact). These are NOT perfection — they are weak,
# awkward links that usually confirm a qualified or negative reading.
MINOR_ASPECTS = {30: "semi-sextile", 150: "quincunx", 45: "semi-square", 135: "sesquiquadrate"}


def minor_aspect_between(p1: dict, p2: dict, orb: float = 2.0) -> dict | None:
    """Detect a minor aspect within a tight orb; classify applying/separating."""
    lon1, lon2 = p1["longitude"], p2["longitude"]
    sp1, sp2 = p1.get("speed_deg_per_day", 0.0), p2.get("speed_deg_per_day", 0.0)
    sep = ang_sep(lon1, lon2)
    best = None
    for ang, label in MINOR_ASPECTS.items():
        delta = abs(sep - ang)
        if delta <= orb and (best is None or delta < best[1]):
            best = (label, delta, ang)
    if not best:
        return None
    label, delta, ang = best
    res0 = abs(ang_sep(lon1, lon2) - ang)
    res1 = abs(ang_sep(lon1 + sp1 * 0.05, lon2 + sp2 * 0.05) - ang)
    return {"aspect": label, "angle": ang, "orb": round(delta, 2), "applying": res1 < res0}


def applies_to_angle(planet: dict, angle_lon: float, orb: float = 5.0) -> dict | None:
    """Is the planet applying to a major aspect with an angle (Asc/MC/Desc/IC)?
    A significator coming to the Ascendant brings the matter/person to the querent."""
    sep = ang_sep(planet["longitude"], angle_lon)
    sp = planet.get("speed_deg_per_day", 0.0)
    best = None
    for ang, label in ASPECTS.items():
        delta = abs(sep - ang)
        if delta <= orb and (best is None or delta < best[1]):
            best = (label, delta, ang)
    if not best:
        return None
    label, delta, ang = best
    res0 = abs(ang_sep(planet["longitude"], angle_lon) - ang)
    res1 = abs(ang_sep(planet["longitude"] + sp * 0.05, angle_lon) - ang)
    return {"aspect": label, "orb": round(delta, 2), "applying": res1 < res0}


TRAD_PLANETS = ("Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon")


def almuten_at(lon: float, is_day: bool) -> str:
    """Almuten of a degree: the planet with the most essential dignity there (Lilly)."""
    best, best_score = None, -99
    for p in TRAD_PLANETS:
        s = essential_dignities(p, lon, is_day)["score"]
        if s > best_score:
            best, best_score = p, s
    return best


def reception(planet_lon: float, by_lon: float, planet_name: str, by_name: str,
              is_day: bool) -> list[str]:
    """Ways `by_name` receives `planet_name` (dignities `by` has at `planet`'s place)."""
    ed = essential_dignities(by_name, planet_lon, is_day)
    return ed["dignities"]


# Strong receptions = domicile or exaltation; minor = triplicity/term/face.
_STRONG_DIG = {"domicile", "exaltation"}


def mutual_reception(planets: dict, n1: str, n2: str, is_day: bool) -> str | None:
    """Return 'strong' (mutual by domicile/exaltation), 'minor' (mutual by lesser
    dignity), 'oneway', or None for the reception between two significators."""
    if n1 == n2:
        return None
    r1 = essential_dignities(n2, planets[n1]["longitude"], is_day)["dignities"]  # n2 receives n1
    r2 = essential_dignities(n1, planets[n2]["longitude"], is_day)["dignities"]  # n1 receives n2
    if r1 and r2:
        if (set(r1) & _STRONG_DIG) and (set(r2) & _STRONG_DIG):
            return "strong"
        return "minor"
    if r1 or r2:
        return "oneway"
    return None


def translation_of_light(planets: dict, n1: str, n2: str) -> str | None:
    """A faster planet that has just separated from one significator and now applies
    to the other carries (translates) the light, perfecting the matter."""
    if n1 == n2:
        return None
    for t, tp in planets.items():
        if t in (n1, n2):
            continue
        sp_t = abs(tp.get("speed_deg_per_day", 0.0))
        if sp_t < abs(planets[n1].get("speed_deg_per_day", 0.0)) and \
           sp_t < abs(planets[n2].get("speed_deg_per_day", 0.0)):
            continue  # translator must be faster than both
        a1 = aspect_between(tp, planets[n1], (t, n1))
        a2 = aspect_between(tp, planets[n2], (t, n2))
        if a1 and a2 and (a1["applying"] != a2["applying"]):
            return t
    return None


def collection_of_light(planets: dict, n1: str, n2: str) -> str | None:
    """A heavier (slower) planet that both significators apply to collects their light."""
    if n1 == n2:
        return None
    for c, cp in planets.items():
        if c in (n1, n2):
            continue
        sp_c = abs(cp.get("speed_deg_per_day", 0.0))
        if sp_c > abs(planets[n1].get("speed_deg_per_day", 0.0)) or \
           sp_c > abs(planets[n2].get("speed_deg_per_day", 0.0)):
            continue  # collector must be slower than both
        a1 = aspect_between(planets[n1], cp, (n1, c))
        a2 = aspect_between(planets[n2], cp, (n2, c))
        if a1 and a2 and a1["applying"] and a2["applying"]:
            return c
    return None


# Fertile / barren signs (Lilly) for 5th-house / children judgments.
FRUITFUL_SIGNS = {"Cancer", "Scorpio", "Pisces"}
BARREN_SIGNS = {"Gemini", "Leo", "Virgo"}

# Void-of-course Moon sign modulation (Lilly/Bonatus, Louis Ch. 2):
# the Moon "still performs" when void in her own sign, exaltation, or Jupiter's signs;
# void in the opposite signs is "especially negative."
VOID_PERFORMS_SIGNS = {"Taurus", "Cancer", "Sagittarius", "Pisces"}
VOID_WORSE_SIGNS = {"Gemini", "Scorpio", "Capricorn"}

# ───────────────────── natural-language question parsing ─────────────────────
# Deterministic, offline intent extraction. Each rule is (regex, house, weight).
# Word-boundary matching avoids substring false hits; weight encodes specificity so
# a precise phrase ("real estate", "get the job") beats a generic token ("buy", "money").
# The house with the highest summed weight wins; PRIORITY breaks ties.
_INTENT_RULES: list[tuple[str, int, int]] = [
    # 4 — home / property / land / father (the *thing* bought in real-estate questions)
    (r"real estate|\bproperty\b|\bproperties\b|\bhouses?\b|\bhome\b|\bland\b|\bflats?\b|"
     r"\bapartments?\b|\bresidence\b|\bfather\b|\bfarm\b|\blandlord\b|\btenan", 4, 3),
    # 10 — career / business / employer / reputation / honour
    (r"\bbusiness\b|\bcompany\b|\bcareer\b|\bpromotion\b|\bpromoted\b|\bjobs?\b|\bemployer\b|"
     r"\bboss\b|\breputation\b|\bstatus\b|\bhonou?r\b|\belection\b|\bposition\b|\bappointment\b|"
     r"get the job|\bappointed\b|\bmanager\b|\bcontract\b.*\bwork\b", 10, 3),
    # 2 — money / movable possessions / loan / lost objects
    (r"\bmoney\b|\bloan\b|\bsalary\b|\bwages?\b|\bincome\b|\bafford\b|\bcash\b|\bfunds?\b|"
     r"\bpayment\b|\brepaid?\b|\bwealth\b|\bsavings?\b|\bpossessions?\b|\bwallet\b|\bpurse\b", 2, 2),
    # 7 — marriage / partner / the other party / removals / return of a partner
    (r"\bmarry\b|\bmarriage\b|\bwed\b|\bwedding\b|\bspouse\b|\bhusband\b|\bwife\b|\bfianc|"
     r"\bpartner\b|\brelationship\b|\bdivorce\b|\bboyfriend\b|\bgirlfriend\b|\blover\b|"
     r"\bmove\b|\bmoving\b|\brelocat|\bremoval\b|\bopponent\b", 7, 3),
    # 5 — children / pregnancy / romance / speculation
    (r"\bchild\b|\bchildren\b|\bson\b|\bdaughter\b|\bpregnan\w*|\bconceive\b|\bbaby\b|"
     r"\bromance\b|\bdating\b|\bgambl\w*|\bspeculat\w*|\btoilet train", 5, 3),
    # 6 — health / illness / work-service / employees / small animals & pets
    (r"\bhealth\b|\bill\b|\billness\b|\bdisease\b|\bsick\b|\bdiagnos\w*|\bsecretary\b|"
     r"\bemployee\b|\bservant\b|\bpet\b|\bcat\b|\bkitten\b|\bdog\b|\bpuppy\b", 6, 3),
    # 9 — travel abroad / foreign / law / higher study / publishing
    (r"\babroad\b|\bforeign\b|\boverseas\b|\bvisa\b|\bimmigrat\w*|\blong journey\b|\bpilgrim\w*|"
     r"\breligion\b|\bchurch\b|\bcourt\b|\blawsuit\b|\blegal\b|\buniversity\b|\bpublish\w*", 9, 3),
    # 8 — death / inheritance / other's money / surgery / insurance
    (r"\binherit\w*|\blegacy\b|\bdeath\b|\bdying\b|\bsurgery\b|\boperation\b|\binsurance\b|"
     r"\bestate of\b|\btaxes?\b", 8, 3),
    # 11 — friends / hopes & wishes / gains / groups
    (r"\bfriend\b|\bfriends\b|\bhope\b|\bwish\b|\bgroup\b|\bclub\b|\bsociety\b", 11, 2),
    # 12 — secret enemies / prison / confinement / loss / large animals / witchcraft
    (r"\benem\w*|\bprison\b|\bjail\b|\bimprison\w*|\bconfine\w*|\bhidden\b|\bsecret\b|"
     r"\bbewitch\w*|\bwitch\w*|\baddict\w*|\bself-undoing\b", 12, 3),
    # 3 — siblings / neighbours / short trips / communication
    (r"\bsiblings?\b|\bbrothers?\b|\bsisters?\b|\bneighbou?rs?\b|\bletter\b|\bemail\b|"
     r"\bmessage\b|\bdocuments?\b|\bshort trip\b|\bcommute\b", 3, 3),
]
# Generic acquisition / loss verbs that only set a house when no specific noun matched.
_BUY_RE = re.compile(r"\b(buy|purchase|acquire|get|obtain)\b", re.I)
_LOST_RE = re.compile(r"\blost\b|\bmissing\b|\bmisplac\w*|\bfind\b|\bfound\b|\bwhere\s+(is|are|did|"
                      r"can|might)\b|\bstolen\b|\btheft\b|\bthief\b|\brecover\w*|can'?t find", re.I)
_RETURN_RE = re.compile(r"\breturns?\b|\breturning\b|\bcome back\b|\bcomes? back\b|\bcoming back\b|"
                        r"\bdelivered?\b|\breleased?\b|\bfreed\b|\bset free\b", re.I)
_WHEN_RE = re.compile(r"\bwhen\b", re.I)
_AMOUNT_RE = re.compile(
    r"\bhow\s+much\b|\bhow\s+many\b|\bwhat\s+(?:percent|percentage|%)\b|"
    r"\bwhat\s+amount\b|\bby\s+how\s+much\b|\bquantum\b|\bmagnitude\b",
    re.I,
)
# Third-party: a named person ("Will Luis…", "Sara's…") or a relative the querent asks about.
_NAME_RE = re.compile(r"\b[Ww]ill\s+([A-Z][a-z]{2,})\b|\b([A-Z][a-z]{2,})['\u2019]s\b")
# Words that look like names but aren't third parties (sentence starts, etc.).
_NAME_STOP = {"Will", "Should", "Where", "When", "What", "Does", "The", "Are", "Can", "Is", "Do"}
_RELATIVE_RE = re.compile(r"\bmy\s+(friend|brother|sister|mother|father|son|daughter|husband|"
                          r"wife|colleague|boss|neighbou?r|cousin|aunt|uncle|client)\b", re.I)
_PRIORITY = [5, 7, 4, 10, 6, 9, 8, 12, 3, 11, 2, 1]  # specificity tie-break


def parse_question(question: str, area: str = "") -> dict:
    """Extract (quesited house, mode flags, third-party) from free text.

    Optional life-area dropdown pins the house. Otherwise semantic routing
    maps meaning → house; keyword/_INTENT_RULES assist when scores are close
    or the encoder is unavailable.
    """
    q = question.strip()
    scores: dict[int, int] = {}
    for pattern, house, weight in _INTENT_RULES:
        n = len(re.findall(pattern, q, re.I))
        if n:
            scores[house] = scores.get(house, 0) + weight * n

    lost = bool(_LOST_RE.search(q))
    if lost and 2 not in scores and not any(h in scores for h in (5, 6, 7)):
        scores[2] = scores.get(2, 0) + 2  # a lost *object* defaults to the 2nd

    # Semantic house (+ optional area dropdown)
    sem_house = None
    sem_score = 0.0
    area_house = None
    try:
        import semantic_question as SQ
        area = SQ.normalize_area(area)
        if area:
            area_house = SQ.AREA_TO_HOUSE.get(area)
        routed = SQ.route(q, area=area)
        sem_house = int(routed.primary_house)
        sem_score = float(routed.house_score or 0)
        if (routed.method == "minilm" or area) and sem_house:
            # Blend: give semantic / area house a strong vote
            scores[sem_house] = scores.get(sem_house, 0) + max(3, int(round(sem_score * 8)))
    except Exception:
        pass

    # Dropdown area is an explicit reader choice — prefer it over keyword noise.
    if area_house:
        house = area_house
    elif scores:
        best = max(scores.values())
        tied = [h for h, s in scores.items() if s == best]
        house = min(tied, key=lambda h: _PRIORITY.index(h)) if len(tied) > 1 else tied[0]
    elif sem_house:
        house = sem_house
    elif _BUY_RE.search(q):
        house = 2  # acquiring an unspecified movable
    else:
        house = 7  # generic "the other party / the matter"

    # Prefer semantic house when keyword path collapsed to generic 7
    if (not area_house and house == 7 and sem_house and sem_house != 7
            and sem_score >= 0.32 and not scores.get(7)):
        house = sem_house

    # Third-party: a named person ("Will Luis…", "Sara's…") or a relative the querent asks about.
    name_hit = None
    for m in _NAME_RE.finditer(q):
        nm = m.group(1) or m.group(2)
        if nm and nm not in _NAME_STOP:
            name_hit = nm
            break
    third_party = bool(name_hit or _RELATIVE_RE.search(q))
    return {
        "house": house,
        "lost": lost,
        "return": bool(_RETURN_RE.search(q)),
        "when": bool(_WHEN_RE.search(q)),
        "amount": bool(_AMOUNT_RE.search(q)),
        "third_party": third_party,
        "scores": scores,
        "semantic_house": sem_house,
        "semantic_score": sem_score,
    }


def is_lost_question(q: str) -> bool:
    return bool(_LOST_RE.search(q))


def is_return_question(q: str) -> bool:
    return bool(_RETURN_RE.search(q))


# ───────────────────────── timing (ephemeris) ─────────────────────────
def _swe():
    import swisseph as swe
    return swe


def perfection_date(jd_start: float, name1: str, name2: str, angle: float,
                    max_days: int = 365) -> date | None:
    """First date the two bodies reach the given aspect angle, scanning forward."""
    swe = _swe()
    ids = {"Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS,
           "Mars": swe.MARS, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN,
           "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO}
    flg = swe.FLG_MOSEPH | swe.FLG_SPEED

    def resid(jd):
        l1 = swe.calc_ut(jd, ids[name1], flg)[0][0]
        l2 = swe.calc_ut(jd, ids[name2], flg)[0][0]
        return ang_sep(l1, l2) - angle

    prev = resid(jd_start)
    step = 0.5
    jd = jd_start
    for _ in range(int(max_days / step)):
        jd += step
        cur = resid(jd)
        if prev == 0 or (prev < 0) != (cur < 0):
            lo, hi = jd - step, jd
            for _ in range(40):
                mid = (lo + hi) / 2
                if (resid(lo) < 0) != (resid(mid) < 0):
                    hi = mid
                else:
                    lo = mid
            y, m, d, _h = swe.revjul((lo + hi) / 2, swe.GREG_CAL)
            return date(int(y), int(m), int(d))
        prev = cur
    return None


def ingress_date(jd_start: float, name: str, max_days: int = 400) -> tuple[date, str] | None:
    """Next sign ingress of a (usually outer) planet after jd_start."""
    swe = _swe()
    ids = {"Jupiter": swe.JUPITER, "Saturn": swe.SATURN, "Mars": swe.MARS,
           "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO}
    if name not in ids:
        return None
    flg = swe.FLG_MOSEPH
    s0 = int(swe.calc_ut(jd_start, ids[name], flg)[0][0] // 30)
    step = 1.0
    jd = jd_start
    for _ in range(int(max_days / step)):
        jd += step
        s = int(swe.calc_ut(jd, ids[name], flg)[0][0] // 30)
        if s != s0:
            y, m, d, _h = swe.revjul(jd, swe.GREG_CAL)
            return date(int(y), int(m), int(d)), SIGNS[s % 12]
    return None


def moon_void_of_course(jd_start: float) -> tuple[bool, str]:
    """Reuse the stepped MOSEPH check (same family as validate_rules_v6_ephemeris.py)."""
    swe = _swe()
    flg = swe.FLG_MOSEPH | swe.FLG_SPEED
    pids = [swe.SUN, swe.MERCURY, swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN,
            swe.URANUS, swe.NEPTUNE, swe.PLUTO]

    def lon_speed(jd, pid):
        xx, _ = swe.calc_ut(jd, pid, flg)
        return xx[0], xx[3]

    lm0, sp = lon_speed(jd_start, swe.MOON)
    if sp <= 0:
        return False, "Moon speed unavailable"
    deg_in = lm0 % 30.0
    jd_end = jd_start + (30.0 - deg_in) / sp * 0.997
    n = max(80, int((jd_end - jd_start) * 48))
    for i in range(n + 1):
        t = jd_start + (jd_end - jd_start) * (i / max(1, n))
        lm, _ = lon_speed(t, swe.MOON)
        for pid in pids:
            lp, _ = lon_speed(t, pid)
            d = ang_sep(lm, lp)
            res = min(abs(d - a) for a in (0, 60, 90, 120, 180))
            if res <= 3.0 and t + 0.02 < jd_end:
                lm2, _ = lon_speed(t + 0.02, swe.MOON)
                lp2, _ = lon_speed(t + 0.02, pid)
                d2 = ang_sep(lm2, lp2)
                res2 = min(abs(d2 - a) for a in (0, 60, 90, 120, 180))
                if res2 < res - 0.01:
                    return False, "Moon applies to a major aspect before leaving its sign"
    return True, "No applying major aspect to Sun–Pluto before the Moon leaves its sign"


def moon_aspects(planets: dict) -> tuple[dict | None, dict | None]:
    """Nearest separating (last) and applying (next) major aspect of the Moon."""
    moon = planets["Moon"]
    last = next_ = None
    last_orb = next_orb = 999.0
    for name, p in planets.items():
        if name == "Moon":
            continue
        asp = aspect_between(moon, p, ("Moon", name))
        if not asp:
            continue
        rec = {"planet": name, **asp}
        if asp["applying"] and asp["orb"] < next_orb:
            next_, next_orb = rec, asp["orb"]
        if not asp["applying"] and asp["orb"] < last_orb:
            last, last_orb = rec, asp["orb"]
    return last, next_


# ───────────────────────── book precedent ─────────────────────────
def match_book_case(conditions: set[str], result_lean: str) -> dict | None:
    path = Path(__file__).resolve().parent / "western-horary-data" / "rules_v6.json"
    if not path.exists():
        return None
    cases = json.loads(path.read_text(encoding="utf-8"))
    best, best_score = None, -1
    for case in cases:
        cset = set(case.get("conditions") or [])
        overlap = len(conditions & cset)
        score = overlap + (1 if case.get("result") == result_lean else 0)
        if score > best_score and (overlap or case.get("result") == result_lean):
            best, best_score = case, score
    return best
