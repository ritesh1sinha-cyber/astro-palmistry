#!/usr/bin/env python3
"""
Prashna Kundali Siddhanta engine - classical chart rules (rules39 / book OCR).

Whole-sign chart from natural Lagna at judgment time. Arudha from facing
direction when supplied; otherwise Lagna sign (book default).
"""
from __future__ import annotations

from horary_precompute import SIGN_LORDS, SIGNS, TOPIC_BHAVAS, house_lord, house_sign

NATURAL_BENEFIC = frozenset({"Jupiter", "Venus", "Mercury", "Moon"})
NATURAL_MALEFIC = frozenset({"Saturn", "Mars", "Rahu", "Ketu", "Sun"})
KENDRA = frozenset({1, 4, 7, 10})
TRIKONA = frozenset({1, 5, 9})
DUSTHANA = frozenset({6, 8, 12})
APOKLIMA = frozenset({3, 6, 9, 12})
UPACHAYA = frozenset({3, 6, 10, 11})
JUPITER_ASPECT_OFFSETS = frozenset({0, 1, 3, 4, 6, 8, 9, 11})  # 5th/7th/9th drishti + lagna offsets

# Book Chart 1 + OCR direction examples (Ch.2)
ARUDHA_BY_DIRECTION = {
    "east": "Aries", "e": "Aries",
    "east-southeast": "Taurus", "ese": "Taurus", "south-east": "Taurus", "southeast": "Taurus",
    "south": "Gemini", "s": "Gemini",
    "south-southwest": "Cancer", "ssw": "Cancer", "southwest": "Cancer",
    "west": "Leo", "w": "Leo",
    "west-northwest": "Virgo", "wnw": "Virgo",
    "northwest": "Sagittarius", "nw": "Sagittarius",
    "north": "Capricorn", "n": "Capricorn",
    "north-northeast": "Aquarius", "nne": "Aquarius",
    "northeast": "Pisces", "ne": "Pisces",
}

GANDANTA_SIGNS = frozenset({"Cancer", "Scorpio", "Pisces", "Aries", "Leo", "Sagittarius"})


def _si(sign: str) -> int:
    return SIGNS.index(sign)


def relative_house(from_house: int, to_house: int) -> int:
    """House `to_house` counted from `from_house` (1-based)."""
    return ((to_house - from_house) % 12) + 1


def house_of_sign(ref_sign: str, target_sign: str) -> int:
    return relative_house(1, ((_si(target_sign) - _si(ref_sign)) % 12) + 1)


def resolve_arudha(lagna_sign: str, moon_sign: str, direction: str | None = None) -> dict:
    if direction:
        key = direction.lower().strip().replace(" ", "-")
        arudha = ARUDHA_BY_DIRECTION.get(key)
        if arudha:
            return {"arudha_sign": arudha, "source": f"direction:{direction}"}
    return {"arudha_sign": lagna_sign, "source": "lagna_default"}


def jupiter_aspects_house(jupiter_house: int, target_house: int) -> bool:
    off = (jupiter_house - target_house) % 12
    return off in JUPITER_ASPECT_OFFSETS


def planets_in_house(houses: dict, h: int, pool: frozenset[str] | None = None) -> list[str]:
    out = [p for p, hh in houses.items() if hh == h]
    if pool:
        out = [p for p in out if p in pool]
    return sorted(out)


def lagna_lord_status(ll_house: int, houses: dict | None = None, lagna_lord: str = "") -> str:
    if houses and lagna_lord and ll_house == 1:
        co = planets_in_house(houses, 1, NATURAL_MALEFIC)
        if len(co) >= 2 or (co and lagna_lord in planets_in_house(houses, 1)):
            return "WEAK"
    if ll_house in KENDRA | TRIKONA | {2, 11}:
        return "GOOD"
    if ll_house in DUSTHANA:
        return "WEAK"
    return "NEUTRAL"


def is_gandanta_lagna(sign: str, degree: float) -> bool:
    if sign not in GANDANTA_SIGNS:
        return False
    if sign in {"Cancer", "Scorpio", "Pisces"}:
        return degree >= 27.0
    return degree <= 3.0


def compute_paksha(sun_lon: float, moon_lon: float) -> dict:
    elong = (moon_lon - sun_lon) % 360.0
    tithi = int(elong // 12.0) + 1
    tithi = min(max(tithi, 1), 30)
    return {
        "tithi": tithi,
        "paksha": "Krishna" if tithi > 15 else "Shukla",
        "bright_moon": tithi <= 15,
    }


def _score_to_label(score: float) -> str:
    if score >= 0.5:
        return "YES"
    if score <= -0.5:
        return "NO"
    if -0.15 < score < 0.15:
        return "NEUTRAL"
    return "CONDITIONAL"


def _apply_jupiter_mitigation(score: float, jup_aspects_lagna: bool, jup_aspects_moon: bool) -> float:
    if jup_aspects_lagna or jup_aspects_moon:
        score += 0.35
    return score


def score_general(
    ll_house: int, jup_house: int, moon_house: int, houses: dict,
    malefics_lagna: list[str], benefics_kendra: list[str], paksha: str,
    gandanta: bool, topic_tl_house: int, topic_tl_status: str,
    lagna_lord: str = "",
) -> tuple[float, list[str]]:
    notes: list[str] = []
    pts = 0.0
    ll_st = lagna_lord_status(ll_house, houses, lagna_lord)
    if ll_st == "GOOD":
        pts += 1.0
        notes.append("Lagna lord well placed")
    elif ll_st == "WEAK":
        pts -= 1.2
        if ll_house in DUSTHANA:
            notes.append("Lagna lord in dusthana")
        else:
            notes.append("Lagna lord afflicted or weak")

    if jupiter_aspects_house(jup_house, 1):
        pts += 1.0
        notes.append("Jupiter aspects Lagna")
    if jupiter_aspects_house(jup_house, moon_house):
        pts += 0.5
        notes.append("Jupiter aspects Moon")

    if benefics_kendra:
        pts += 0.5
        notes.append(f"Benefics in kendra: {', '.join(benefics_kendra)}")
    if malefics_lagna:
        pts -= 1.0
        notes.append(f"Malefics in Lagna: {', '.join(malefics_lagna)}")
    if paksha == "Krishna" and moon_house in DUSTHANA:
        pts -= 0.5
        notes.append("Waning Moon in dusthana")
    if gandanta:
        pts -= 0.4
        notes.append("Lagna in gandanta zone")

    if topic_tl_status == "FAVORABLE":
        pts += 1.5
    elif topic_tl_status == "DENYING":
        pts -= 1.5

    return pts, notes


def score_marriage(
    lagna_sign: str, arudha_sign: str, houses: dict, ll_house: int,
    jup_house: int, moon_house: int, paksha: str,
) -> tuple[float, list[str]]:
    notes: list[str] = []
    pts = 0.0
    h7 = relative_house(1, 7)
    seventh_lord = house_lord(lagna_sign, 7)
    ll = SIGN_LORDS[lagna_sign]
    sl_house = houses.get(seventh_lord, 0)
    malefics_7 = planets_in_house(houses, h7, NATURAL_MALEFIC)
    benefics_7 = planets_in_house(houses, h7, NATURAL_BENEFIC)

    if benefics_7 and not malefics_7:
        pts += 1.0
        notes.append("Benefics in 7th")
    elif not planets_in_house(houses, h7):
        pts += 0.3
        notes.append("7th house unoccupied (acceptable)")
    if malefics_7:
        pts -= 0.8
        notes.append(f"Malefics in 7th: {', '.join(malefics_7)}")

    if ll_house in DUSTHANA and sl_house in DUSTHANA:
        pts -= 1.0
        notes.append("Lagna lord and 7th lord both in dusthana")
    elif ll_house not in DUSTHANA and sl_house not in DUSTHANA:
        pts += 0.6
        notes.append("Lagna lord and 7th lord clear of dusthana")

    if moon_house in APOKLIMA:
        if jupiter_aspects_house(jup_house, moon_house) or houses.get("Mercury") == moon_house:
            pts += 0.5
            notes.append("Moon in apoklima but aspected by Jupiter/Mercury")
        else:
            pts -= 1.0
            notes.append("Moon in apoklima without Jupiter/Mercury support")

    if jupiter_aspects_house(jup_house, moon_house):
        pts += 0.8
        notes.append("Moon aspected by Jupiter (marriage verse)")

    mars_h = houses.get("Mars", 0)
    if mars_h and moon_house in {3, 6, 10, 11} and relative_house(moon_house, mars_h) in {3, 6, 10, 11}:
        pts -= 0.4
        notes.append("Mars-Moon delay marker")

    malefics_lagna = planets_in_house(houses, 1, NATURAL_MALEFIC)
    if len(malefics_lagna) >= 2:
        pts -= 1.0
        notes.append("Two or more malefics in Lagna (marriage stress)")
    if malefics_lagna and malefics_7:
        pts -= 0.8
        notes.append("Malefics in both Lagna and 7th - quarrel symbolism")

    malefics_8 = planets_in_house(houses, 8, NATURAL_MALEFIC)
    if malefics_8:
        pts -= 1.2
        notes.append(f"Malefics in 8th: {', '.join(malefics_8)} - alliance/marriage strain (book Chart 2)")

    sixth_lord = house_lord(lagna_sign, 6)
    sl6_h = houses.get(sixth_lord, 0)
    mars_h = houses.get("Mars", 0)
    if mars_h == 8 and sl6_h and sixth_lord == "Saturn":
        pts -= 0.8
        notes.append("6th lord Saturn stressed with Mars in 8th - gift/quarrel break (book Chart 2)")

    arudha_h = house_of_sign(lagna_sign, arudha_sign)
    if planets_in_house(houses, arudha_h, NATURAL_MALEFIC) and malefics_lagna:
        pts -= 0.3

    return pts, notes


def score_children(lagna_sign: str, houses: dict, jup_house: int) -> tuple[float, list[str]]:
    notes: list[str] = []
    pts = 0.0
    fifth_lord = house_lord(lagna_sign, 5)
    fl_h = houses.get(fifth_lord, 0)
    if fl_h in KENDRA | TRIKONA | {2, 11}:
        pts += 1.0
        notes.append("5th lord well placed")
    elif fl_h in DUSTHANA:
        pts -= 1.2
        notes.append("5th lord in dusthana")

    if jup_house in KENDRA | TRIKONA | {2, 11}:
        pts += 0.8
        notes.append("Jupiter (putrakaraka) well placed")
    elif jup_house in DUSTHANA:
        pts -= 0.6

    moon_h, mars_h = houses.get("Moon", 0), houses.get("Mars", 0)
    if moon_h == 5 and mars_h == 5:
        benefic_on_5 = any(houses.get(p) == 5 for p in ("Jupiter", "Venus", "Mercury"))
        if not benefic_on_5:
            pts -= 0.8
            notes.append("Moon and Mars in 5th without benefic aspect")

    return pts, notes


def score_disease_cure(lagna_sign: str, houses: dict, ll_house: int, jup_house: int, lagna_lord: str) -> tuple[float, list[str]]:
    notes: list[str] = []
    pts = 0.0
    sixth_lord = house_lord(lagna_sign, 6)
    eighth_lord = house_lord(lagna_sign, 8)
    eleventh_lord = house_lord(lagna_sign, 11)
    sl6, sl8, sl11 = houses.get(sixth_lord, 0), houses.get(eighth_lord, 0), houses.get(eleventh_lord, 0)

    malefics_lagna = planets_in_house(houses, 1, NATURAL_MALEFIC)
    benefics_lagna = planets_in_house(houses, 1, NATURAL_BENEFIC)
    if benefics_lagna or lagna_lord_status(ll_house, houses, lagna_lord) == "GOOD":
        pts += 0.8
        notes.append("Lagna / Lagna lord supported by benefics")
    if malefics_lagna:
        pts -= 0.8
        notes.append("Malefics on Lagna - prolonged illness symbolism")

    if sl6 in DUSTHANA:
        pts -= 0.6
        notes.append("6th lord in dusthana")
    if sl8 in KENDRA and malefics_lagna:
        pts -= 0.5
        notes.append("8th lord strong with afflicted Lagna")

    if sl11 in KENDRA | TRIKONA | {2} or planets_in_house(houses, 11, NATURAL_BENEFIC):
        pts += 1.0
        notes.append("11th house / lord supports relief")
    if jupiter_aspects_house(jup_house, 1) or jupiter_aspects_house(jup_house, 11):
        pts += 0.5
        notes.append("Jupiter grace on Lagna or 11th")

    return pts, notes


def score_career_job(lagna_sign: str, houses: dict) -> tuple[float, list[str]]:
    notes: list[str] = []
    pts = 0.0
    tenth_lord = house_lord(lagna_sign, 10)
    second_lord = house_lord(lagna_sign, 2)
    tl10, tl2 = houses.get(tenth_lord, 0), houses.get(second_lord, 0)
    if tl10 in KENDRA | TRIKONA | {2, 11}:
        pts += 1.0
        notes.append("10th lord well placed")
    elif tl10 in DUSTHANA:
        pts -= 0.8
    if tl2 in {2, 6, 10, 11}:
        pts += 0.5
    if houses.get("Sun") in {1, 10, 11} or houses.get("Jupiter") in {1, 10, 11}:
        pts += 0.5
        notes.append("Sun/Jupiter support career houses")
    return pts, notes


def score_travel(lagna_sign: str, houses: dict) -> tuple[float, list[str]]:
    notes: list[str] = []
    pts = 0.0
    for h, label in ((3, "3rd"), (9, "9th")):
        lord = house_lord(lagna_sign, h)
        lh = houses.get(lord, 0)
        if lh in DUSTHANA:
            pts -= 0.6
            notes.append(f"{label} lord in dusthana")
        elif lh in KENDRA | TRIKONA | {11}:
            pts += 0.6
            notes.append(f"{label} lord favorable")
    return pts, notes


TOPIC_SCORERS = {
    "marriage": lambda d, **kw: score_marriage(**kw),
    "children": lambda d, **kw: score_children(kw["lagna_sign"], kw["houses"], kw["jup_house"]),
    "disease_cure": lambda d, **kw: score_disease_cure(kw["lagna_sign"], kw["houses"], kw["ll_house"], kw["jup_house"], SIGN_LORDS[kw["lagna_sign"]]),
    "recovery": lambda d, **kw: score_disease_cure(kw["lagna_sign"], kw["houses"], kw["ll_house"], kw["jup_house"], SIGN_LORDS[kw["lagna_sign"]]),
    "disease": lambda d, **kw: score_disease_cure(kw["lagna_sign"], kw["houses"], kw["ll_house"], kw["jup_house"], SIGN_LORDS[kw["lagna_sign"]]),
    "health": lambda d, **kw: score_disease_cure(kw["lagna_sign"], kw["houses"], kw["ll_house"], kw["jup_house"], SIGN_LORDS[kw["lagna_sign"]]),
    "career": lambda d, **kw: score_career_job(kw["lagna_sign"], kw["houses"]),
    "job": lambda d, **kw: score_career_job(kw["lagna_sign"], kw["houses"]),
    "travel": lambda d, **kw: score_travel(kw["lagna_sign"], kw["houses"]),
}


def analyze_prashna(data: dict, arudha_direction: str | None = None) -> dict:
    lagna = data["lagna"]
    lagna_sign = lagna["sign"]
    lagna_lord = SIGN_LORDS[lagna_sign]
    houses = data["houses"]
    planets = data["planets"]
    topic = data["meta"]["detected_topic"]
    tb = TOPIC_BHAVAS.get(topic, TOPIC_BHAVAS["general"])

    moon_sign = planets["Moon"]["sign"]
    arudha = resolve_arudha(lagna_sign, moon_sign, arudha_direction)
    arudha_sign = arudha["arudha_sign"]

    ll_house = houses.get(lagna_lord, 0)
    jup_house = houses.get("Jupiter", 0)
    moon_house = houses.get("Moon", 0)
    topic_lord = house_lord(lagna_sign, tb["primary"])
    tl_house = houses.get(topic_lord, 0)
    tl_fav = tl_house in tb["favorable"]
    tl_den = tl_house in tb["denying"]
    topic_tl_status = "FAVORABLE" if tl_fav else ("DENYING" if tl_den else "NEUTRAL")

    malefics_lagna = planets_in_house(houses, 1, NATURAL_MALEFIC)
    benefics_kendra = []
    for h in KENDRA:
        benefics_kendra.extend(planets_in_house(houses, h, NATURAL_BENEFIC))
    benefics_kendra = sorted(set(benefics_kendra))

    sun_lon = planets["Sun"].get("sidereal_lon", 0)
    moon_lon = planets["Moon"].get("sidereal_lon", 0)
    paksha_info = data["meta"].get("paksha") or compute_paksha(sun_lon, moon_lon)
    if isinstance(paksha_info, dict):
        paksha = paksha_info.get("paksha", "Shukla")
    else:
        paksha = str(paksha_info)

    gandanta = is_gandanta_lagna(lagna_sign, float(lagna.get("degree", 15)))

    gen_pts, gen_notes = score_general(
        ll_house, jup_house, moon_house, houses, malefics_lagna, benefics_kendra,
        paksha, gandanta, tl_house, topic_tl_status, lagna_lord,
    )
    topic_pts, topic_notes = 0.0, []
    scorer = TOPIC_SCORERS.get(topic)
    kw = dict(
        lagna_sign=lagna_sign, arudha_sign=arudha_sign, houses=houses,
        ll_house=ll_house, jup_house=jup_house, moon_house=moon_house, paksha=paksha,
    )
    if scorer:
        topic_pts, topic_notes = scorer(data, **kw)

    total = gen_pts + topic_pts
    jup_lag = jupiter_aspects_house(jup_house, 1)
    jup_moon = jupiter_aspects_house(jup_house, moon_house)
    malefics_8 = planets_in_house(houses, 8, NATURAL_MALEFIC)
    # Jupiter mitigation only when chart is not heavily afflicted (book Chart 1 caveat).
    # Book Chart 2: malefic in 8th blocks Jupiter relief for marriage/alliance.
    skip_jup_mit = len(malefics_lagna) >= 2 or (topic == "marriage" and bool(malefics_8))
    if not skip_jup_mit:
        total = _apply_jupiter_mitigation(total, jup_lag, jup_moon)

    score = max(-1.0, min(1.0, total / 4.0))
    label = _score_to_label(score)

    return {
        "score": score,
        "label": label,
        "lagna_lord": lagna_lord,
        "ll_house": ll_house,
        "ll_status": lagna_lord_status(ll_house, houses, lagna_lord),
        "jup_house": jup_house,
        "jup_aspects_lagna": jup_lag,
        "jup_aspects_moon": jup_moon,
        "malefics_in_lagna": malefics_lagna,
        "benefics_in_kendra": benefics_kendra,
        "topic_lord": topic_lord,
        "tl_house": tl_house,
        "tl_status": topic_tl_status,
        "primary_bhava": tb["primary"],
        "arudha_sign": arudha_sign,
        "arudha_source": arudha["source"],
        "arudha_house_from_lagna": house_of_sign(lagna_sign, arudha_sign),
        "paksha": paksha,
        "gandanta_lagna": gandanta,
        "moon_house": moon_house,
        "notes": gen_notes + topic_notes,
        "seventh_lord": house_lord(lagna_sign, 7),
        "seventh_lord_house": houses.get(house_lord(lagna_sign, 7), 0),
    }


def book_chart1_fixture() -> dict:
    """OCR Chart 1 (marriage) - Virgo Lagna, Arudha Sagittarius, marriage unlikely."""
    return {
        "meta": {"detected_topic": "marriage", "paksha": {"paksha": "Shukla"}},
        "lagna": {"sign": "Virgo", "degree": 12.0},
        "planets": {
            "Sun": {"sign": "Gemini", "sidereal_lon": 60},
            "Moon": {"sign": "Scorpio", "sidereal_lon": 220},
            "Mercury": {"sign": "Virgo"},
            "Venus": {"sign": "Leo"},
            "Mars": {"sign": "Virgo"},
            "Jupiter": {"sign": "Capricorn"},
            "Saturn": {"sign": "Virgo"},
            "Rahu": {"sign": "Gemini"},
            "Ketu": {"sign": "Sagittarius"},
        },
        "houses": {
            "Sun": 10, "Rahu": 10,
            "Moon": 3,
            "Mercury": 1, "Mars": 1, "Saturn": 1,
            "Venus": 12,
            "Jupiter": 5,
            "Ketu": 4,
        },
    }
