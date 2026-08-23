#!/usr/bin/env python3
"""
horary_precompute.py — Pre-compute ALL horary/prashna math before LLM interpretation.

Input:  question, date (YYYY-MM-DD), time (HH:MM 24-hr IST), location, kp_number (optional)
Output: horary_precomputed.json — all charts, parameters, verdicts, LLM instructions

Math covered:
  - Julian Day Number
  - Ascendant: **Swiss Ephemeris** sidereal Lahiri + Placidus when `pyswisseph` is installed;
    otherwise legacy GMST → LMST → hand formula (less reliable — install `pyswisseph`).
  - Approximate sidereal planet positions (Sun accurate; others via polynomial)
  - House placements (whole-sign from Lagna)
  - Nakshatra + sub-lord + star lord for Lagna and all planets
  - Jamakkol: Aarudam, Udhayam, Veedhi, Kavippu
  - KP Horary number → sign + sub-lord
  - Ruling Planets (day lord + Lagna + Moon)
  - Radicality check (8 indicators)
  - Gender aids (rāśi mnemonic + Navāṃśa Verse 100 + KP Chart A context when KP# given)
  - Topic bhava identification
  - House lordships
  - LLM instructions per system (Jamakkol, KP, Prashna)

Usage:
    python3 horary_precompute.py "Will child speak?" "2026-04-07" "03:12" "New Delhi" [kp_number] [output.json]
"""

import json, math, sys, re
from datetime import date as Date, datetime
from pathlib import Path
from typing import Optional

# ══════════════════════════════════════════════════════════════════
#  CONSTANTS & LOOKUP TABLES
# ══════════════════════════════════════════════════════════════════

AYANAMSA_2026 = 24.1167   # Lahiri ayanamsa in degrees for 2026 (~24°07')
# Increase ~0.0139°/year (50" per year)
AYANAMSA_J2000 = 23.8532  # at J2000.0 (Jan 1.5, 2000)
AYANAMSA_RATE  = 50.3 / 3600.0  # degrees per year

SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
         "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

# Odd signs = masculine (boy); Even signs = feminine (girl) — 1-indexed
ODD_SIGNS  = {"Aries","Gemini","Leo","Libra","Sagittarius","Aquarius"}
EVEN_SIGNS = {"Taurus","Cancer","Virgo","Scorpio","Capricorn","Pisces"}

SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}

NAKSHATRAS = [
    ("Ashwini", 0.0,       "Ketu"),
    ("Bharani", 13.3333,   "Venus"),
    ("Krittika",26.6667,   "Sun"),
    ("Rohini",  40.0,      "Moon"),
    ("Mrigashira",53.3333, "Mars"),
    ("Ardra",   66.6667,   "Rahu"),
    ("Punarvasu",80.0,     "Jupiter"),
    ("Pushya",  93.3333,   "Saturn"),
    ("Ashlesha",106.6667,  "Mercury"),
    ("Magha",   120.0,     "Ketu"),
    ("Purva Phalguni",133.3333,"Venus"),
    ("Uttara Phalguni",146.6667,"Sun"),
    ("Hasta",   160.0,     "Moon"),
    ("Chitra",  173.3333,  "Mars"),
    ("Swati",   186.6667,  "Rahu"),
    ("Vishakha",200.0,     "Jupiter"),
    ("Anuradha",213.3333,  "Saturn"),
    ("Jyeshtha",226.6667,  "Mercury"),
    ("Mula",    240.0,     "Ketu"),
    ("Purva Ashadha",253.3333,"Venus"),
    ("Uttara Ashadha",266.6667,"Sun"),
    ("Shravana",280.0,     "Moon"),
    ("Dhanishtha",293.3333,"Mars"),
    ("Shatabhisha",306.6667,"Rahu"),
    ("Purva Bhadrapada",320.0,"Jupiter"),
    ("Uttara Bhadrapada",333.3333,"Saturn"),
    ("Revati",  346.6667,  "Mercury"),
]

# Vimshottari sub-lord order within each nakshatra (9 sub-lords)
VIMSH_ORDER  = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]
VIMSH_YEARS  = {"Ketu":7,"Venus":20,"Sun":6,"Moon":10,"Mars":7,
                "Rahu":18,"Jupiter":16,"Saturn":19,"Mercury":17}  # total = 120

# KP number ranges (1–249) → sign
KP_RANGES = [
    (1,  21,  "Aries"),
    (22, 39,  "Taurus"),
    (40, 60,  "Gemini"),
    (61, 80,  "Cancer"),
    (81, 100, "Leo"),
    (101,121, "Virgo"),
    (122,142, "Libra"),
    (143,162, "Scorpio"),
    (163,183, "Sagittarius"),
    (184,203, "Capricorn"),
    (204,224, "Aquarius"),
    (225,249, "Pisces"),
]

# Location database (lat, lon) in degrees
LOCATIONS = {
    "hyderabad": (17.3850,  78.4867),
    "delhi":     (28.6139,  77.2090),
    "new delhi": (28.6139,  77.2090),
    "mumbai":    (19.0760,  72.8777),
    "bangalore": (12.9716,  77.5946),
    "chennai":   (13.0827,  80.2707),
    "thanjavur": (10.7867,  79.1378),
    "kolkata":   (22.5726,  88.3639),
    "pune":      (18.5204,  73.8567),
    "ahmedabad": (23.0225,  72.5714),
    "jaipur":    (26.9124,  75.7873),
    "lucknow":   (26.8467,  80.9462),
}

# Planet karakas / significations (for Jamakkol & Prashna)
PLANET_KARAKAS = {
    "Sun":     "authority, father, government, health",
    "Moon":    "mother, mind, emotions, domestic life",
    "Mars":    "land, property, brothers, surgery, courage",
    "Mercury": "education, communication, business, trade",
    "Jupiter": "children, wealth, guru, dharma, justice",
    "Venus":   "marriage, relationships, luxury, arts",
    "Saturn":  "longevity, karma, career, servants, delays",
    "Rahu":    "foreign matters, sudden events, deception, mass",
    "Ketu":    "spirituality, hidden matters, liberation, past karma",
}

# Topic → relevant bhavas (KP favorable = 2/6/10/11 or topic-specific)
TOPIC_BHAVAS = {
    "health":        {"primary":1, "favorable":[1,5,11],   "denying":[6,8,12]},
    "disease":       {"primary":6, "favorable":[6,12],     "denying":[5,11]},
    "disease_cure":  {"primary":6, "favorable":[5,6,11],  "denying":[1,8,12]},
    "recovery":      {"primary":6, "favorable":[5,6,11],  "denying":[1,8,12]},
    "job":         {"primary":10,"favorable":[2,6,10,11],"denying":[1,5,9]},
    "career":      {"primary":10,"favorable":[2,6,10,11],"denying":[1,5,9]},
    "marriage":    {"primary":7, "favorable":[2,7,11],  "denying":[1,6,10]},
    "children":    {"primary":5, "favorable":[2,5,11],  "denying":[1,4,10]},
    "finance":     {"primary":2, "favorable":[2,6,10,11],"denying":[1,5,9,12]},
    "travel":      {"primary":9, "favorable":[3,9,11,12],"denying":[2,8]},
    "property":    {"primary":4, "favorable":[4,11],    "denying":[3,8,10]},
    "education":   {"primary":9, "favorable":[4,9,11],  "denying":[1,6,12]},
    "litigation":  {"primary":6, "favorable":[6,11],    "denying":[5,7]},
    "loan":        {"primary":6, "favorable":[6,11],    "denying":[5,12]},
    "general":     {"primary":1, "favorable":[1,5,9,11],"denying":[6,8,12]},
}

# Kavippu house interpretation
KAVIPPU_MEANINGS = {
    1:  "Query about self — outcome for the questioner is negative or self-referential",
    2:  "Financial loss or family trouble — query involving wealth/family is obstructed",
    3:  "Communication or siblings issue — query in these areas faces obstacles",
    4:  "Property, mother, or heart matters — these areas troubled",
    5:  "Children, love, speculation — denied or delayed",
    6:  "Disease or enemies highlighted — ambiguous (can be cure OR setback)",
    7:  "Marriage or partnership query — fails or faces serious obstacles",
    8:  "Longevity, inheritance, secrets — unexpected trouble",
    9:  "Loss of fortune — foreign/spiritual matters obstructed",
    10: "Career stagnation — professional matters obstructed",
    11: "BEST placement — gains and wishes fulfilled despite other challenges",
    12: "Loss, expenses, confinement — query leads to expenditure or isolation",
}

# ══════════════════════════════════════════════════════════════════
#  JULIAN DAY & TIME UTILITIES
# ══════════════════════════════════════════════════════════════════

def julian_day(year: int, month: int, day: int,
               hour: float = 0.0) -> float:
    """Calculate Julian Day Number (UT)."""
    if month <= 2:
        year -= 1
        month += 12
    A = int(year / 100)
    B = 2 - A + int(A / 4)
    return int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + hour / 24.0 + B - 1524.5


def ist_to_ut(hour_ist: float, minute_ist: int) -> float:
    """Convert IST (UTC+5:30) to UT decimal hours."""
    return (hour_ist + minute_ist / 60.0) - 5.5


def parse_time(time_str: str) -> tuple:
    """Parse HH:MM → (hour_int, minute_int)."""
    parts = time_str.strip().split(":")
    return int(parts[0]), int(parts[1])


# ══════════════════════════════════════════════════════════════════
#  PLANET POSITION CALCULATIONS (simplified but accurate to ~0.5°)
# ══════════════════════════════════════════════════════════════════

def _rad(d): return math.radians(d)
def _deg(r): return math.degrees(r)
def _norm(d): return d % 360.0


def sun_tropical_longitude(jd: float) -> float:
    """Sun's tropical longitude — Jean Meeus simplified, accurate ~0.01°."""
    T = (jd - 2451545.0) / 36525.0
    L0 = _norm(280.46646 + 36000.76983 * T + 0.0003032 * T**2)
    M  = _norm(357.52911 + 35999.05029 * T - 0.0001537 * T**2)
    M_r = _rad(M)
    C = ((1.914602 - 0.004817*T - 0.000014*T**2) * math.sin(M_r)
         + (0.019993 - 0.000101*T) * math.sin(2*M_r)
         + 0.000289 * math.sin(3*M_r))
    return _norm(L0 + C)


def moon_tropical_longitude(jd: float) -> float:
    """Moon's tropical longitude — accurate to ~0.3° (Jean Meeus Ch. 47 simplified)."""
    T = (jd - 2451545.0) / 36525.0
    # Mean elements
    L  = _norm(218.3164477 + 481267.88123421*T - 0.0015786*T**2)
    M  = _rad(_norm(134.9633964 + 477198.8676313*T + 0.0089970*T**2))
    Ms = _rad(_norm(357.5291092 + 35999.0502909*T))
    D  = _rad(_norm(297.8501921 + 445267.1114034*T - 0.0018819*T**2))
    F  = _rad(_norm(93.2720950  + 483202.0175233*T - 0.0036539*T**2))
    # Main perturbations
    lon = (L
        + 6.288750 * math.sin(M)
        + 1.274018 * math.sin(2*D - M)
        + 0.658309 * math.sin(2*D)
        + 0.213616 * math.sin(2*M)
        - 0.185116 * math.sin(Ms)
        - 0.114332 * math.sin(2*F)
        + 0.058793 * math.sin(2*D - 2*M)
        + 0.057066 * math.sin(2*D - Ms - M)
        + 0.053322 * math.sin(2*D + M)
        + 0.045758 * math.sin(2*D - Ms)
        - 0.040923 * math.sin(Ms - M)
        - 0.034720 * math.sin(D)
        - 0.030383 * math.sin(Ms + M)
        + 0.015327 * math.sin(2*D - 2*F)
        - 0.012528 * math.sin(M + 2*F)
        - 0.010980 * math.sin(M - 2*F))
    return _norm(lon)


def mercury_tropical_longitude(jd: float) -> float:
    """Mercury approximate tropical longitude — accurate ~2-3°."""
    T = (jd - 2451545.0) / 36525.0
    L = _norm(252.2509 + 149472.6746 * T)
    M = _rad(_norm(102.2790 + 149472.5152 * T))
    # Simplified equation of centre for Mercury (large eccentricity 0.2056)
    e = 0.20563069 - 0.000020559 * T
    C = (_deg(2*e) * math.sin(M)
         + (5/4) * e**2 * math.sin(2*M)
         + (13/12) * e**3 * math.sin(3*M))
    return _norm(L + C)


def venus_tropical_longitude(jd: float) -> float:
    """Venus approximate tropical longitude — accurate ~1-2°."""
    T = (jd - 2451545.0) / 36525.0
    L = _norm(181.9798 + 58517.8157 * T)
    M = _rad(_norm(212.2794 + 58517.8091 * T))
    e = 0.00677323 - 0.00004938 * T
    C = (_deg(2*e) * math.sin(M)
         + (5/4) * e**2 * math.sin(2*M))
    return _norm(L + C)


def mars_tropical_longitude(jd: float) -> float:
    """Mars approximate tropical longitude — accurate ~2°."""
    T = (jd - 2451545.0) / 36525.0
    L = _norm(355.4333 + 19140.2993 * T)
    M = _rad(_norm(319.5294 + 19139.8585 * T))
    e = 0.09341233 - 0.00011411 * T
    C = (_deg(2*e) * math.sin(M)
         + (5/4) * e**2 * math.sin(2*M)
         + (13/12) * e**3 * math.sin(3*M))
    return _norm(L + C)


def jupiter_tropical_longitude(jd: float) -> float:
    """Jupiter approximate tropical longitude — accurate ~1°."""
    T = (jd - 2451545.0) / 36525.0
    # Mean longitude + perturbations
    L = _norm(34.3515 + 3034.9057 * T)
    M = _rad(_norm(14.3312 + 3034.9057 * T))
    e = 0.04849485 + 0.000163 * T
    C = (_deg(2*e) * math.sin(M)
         + (5/4) * e**2 * math.sin(2*M))
    # Saturn perturbation (~0.35° max)
    Mj = _rad(_norm(20.9 + 3034.9 * T))
    Ms = _rad(_norm(317.0 + 1222.1 * T))
    perturb = 0.3320 * math.sin(2*Mj - 5*Ms - 67.6*_rad(1)) + 0.1018 * math.sin(2*Mj - 6*Ms)
    return _norm(L + C + perturb)


def saturn_tropical_longitude(jd: float) -> float:
    """Saturn approximate tropical longitude — accurate ~1-2°."""
    T = (jd - 2451545.0) / 36525.0
    L = _norm(50.0774 + 1222.1138 * T)
    M = _rad(_norm(356.7470 + 1221.5515 * T))
    e = 0.05551825 - 0.0003466 * T
    C = (_deg(2*e) * math.sin(M)
         + (5/4) * e**2 * math.sin(2*M))
    # Jupiter perturbation
    Mj = _rad(_norm(20.9 + 3034.9 * T))
    Ms = _rad(_norm(317.0 + 1222.1 * T))
    perturb = 0.8123 * math.sin(2*Mj - 5*Ms - 67.6*_rad(1)) - 0.1906 * math.sin(2*Mj - 2*Ms)
    return _norm(L + C + perturb)


def rahu_tropical_longitude(jd: float) -> float:
    """Mean Rahu (North Node) tropical longitude — accurate ~0.5°."""
    T = (jd - 2451545.0) / 36525.0
    return _norm(125.0445 - 1934.1362 * T + 0.0020754 * T**2)


def get_ayanamsa(jd: float) -> float:
    """Lahiri ayanamsa for given JD (degrees)."""
    T_years = (jd - 2451545.0) / 365.25
    return AYANAMSA_J2000 + AYANAMSA_RATE * T_years


def tropical_to_sidereal(trop_deg: float, jd: float) -> float:
    """Convert tropical longitude to sidereal (Lahiri)."""
    return _norm(trop_deg - get_ayanamsa(jd))


# ══════════════════════════════════════════════════════════════════
#  REFERENCE POSITIONS + INTERPOLATION (more accurate for 2026+)
# ══════════════════════════════════════════════════════════════════
#
# Verified sidereal (Lahiri) positions from astrosage.com
# Reference epoch: April 6, 2026 ~10 PM IST = 16:30 UT = JD 2461137.187
#
JD_REF = 2461137.187

# Sidereal longitudes at JD_REF (degrees, 0=Aries 0°)
_REF_SID = {
    "Sun":     352.97,   # Pisces 22°58'
    "Moon":    213.83,   # Scorpio ~3°50' (at Apr 6 3:44 AM IST, but we use Moon from Moon formula)
    "Mercury": 325.42,   # Aquarius 25°25'
    "Venus":    13.58,   # Aries 13°35'
    "Mars":    333.10,   # Pisces 3°06'
    "Jupiter":  82.08,   # Gemini 22°05'  ← key correction for polynomial drift
    "Saturn":  342.15,   # Pisces 12°09'
    "Rahu":    312.97,   # Aquarius 12°58' (retrograde)
}

# Mean sidereal daily motions (degrees/day; negative = retrograde)
_DAILY_SID = {
    "Sun":      0.9856,
    "Moon":    13.1764,   # use direct formula instead; listed for reference
    "Mercury":  1.3830,
    "Venus":    1.2024,
    "Mars":     0.5240,
    "Jupiter":  0.0831,
    "Saturn":   0.0333,
    "Rahu":    -0.0530,
}

# Max days from JD_REF before falling back to polynomial (Moon always uses formula)
_REF_MAX_DAYS = 180  # ~6 months; polynomial used beyond this


def _planet_sidereal_lon(planet: str, jd: float) -> float:
    """
    Return sidereal longitude for a planet.
    Uses reference+interpolation within ±180 days of JD_REF;
    falls back to polynomial for Moon (always) and distant dates.
    """
    days = jd - JD_REF
    if planet == "Moon":
        # Always use the formula — Moon changes too fast for linear interpolation
        return tropical_to_sidereal(moon_tropical_longitude(jd), jd)
    if abs(days) <= _REF_MAX_DAYS and planet in _REF_SID:
        return _norm(_REF_SID[planet] + _DAILY_SID[planet] * days)
    # Polynomial fallback
    ayanamsa = get_ayanamsa(jd)
    if planet == "Sun":     return _norm(sun_tropical_longitude(jd) - ayanamsa)
    if planet == "Mercury": return _norm(mercury_tropical_longitude(jd) - ayanamsa)
    if planet == "Venus":   return _norm(venus_tropical_longitude(jd) - ayanamsa)
    if planet == "Mars":    return _norm(mars_tropical_longitude(jd) - ayanamsa)
    if planet == "Jupiter": return _norm(jupiter_tropical_longitude(jd) - ayanamsa)
    if planet == "Saturn":  return _norm(saturn_tropical_longitude(jd) - ayanamsa)
    if planet == "Rahu":    return _norm(rahu_tropical_longitude(jd) - ayanamsa)
    return 0.0


def longitude_to_sign_degree(lon: float) -> tuple:
    """Convert 0–360° longitude to (sign_name, degree_in_sign)."""
    sign_idx = int(lon // 30)
    deg_in_sign = lon - sign_idx * 30
    return SIGNS[sign_idx], round(deg_in_sign, 2)


def navamsa_lagna_sign(sidereal_asc_deg: float) -> str:
    """
    Navāṃśa sign of Ascendant (classical 9-fold division of the rāśi).
    Movable rāśi: navāṃśa-1 starts in same sign; fixed: from 9th; dual: from 5th.
    Used for *Prashna Kundali Siddhanta* Verse 100 (odd/even rāśi + navāṃśa parity).
    """
    lon = sidereal_asc_deg % 360.0
    s = int(lon // 30)
    d = lon - s * 30.0
    movable = {0, 3, 6, 9}
    fixed = {1, 4, 7, 10}
    if s in movable:
        start = s
    elif s in fixed:
        start = (s + 8) % 12
    else:
        start = (s + 4) % 12
    piece = int(d // (10.0 / 3.0))  # 3°20' each
    piece = min(piece, 8)
    return SIGNS[(start + piece) % 12]


# ══════════════════════════════════════════════════════════════════
#  NAKSHATRA & SUB-LORD
# ══════════════════════════════════════════════════════════════════

NAK_SPAN_DEG = 360.0 / 27  # 13.3333°

def get_nakshatra(sid_lon: float) -> dict:
    """Return nakshatra, star lord, pada, and sub-lord for a sidereal longitude."""
    idx = int(sid_lon / NAK_SPAN_DEG)
    idx = min(idx, 26)
    name, start_lon, star_lord = NAKSHATRAS[idx]
    # Pada (1-4)
    deg_in_nak = sid_lon - start_lon
    pada = int(deg_in_nak / (NAK_SPAN_DEG / 4)) + 1
    pada = min(pada, 4)
    # Sub-lord: divide nakshatra into 9 sub-divisions weighted by Vimshottari years
    total_years = 120
    sub_start = start_lon
    sl_start_idx = VIMSH_ORDER.index(star_lord)
    sub_lord = star_lord  # default
    running = sub_start
    for i in range(9):
        pl = VIMSH_ORDER[(sl_start_idx + i) % 9]
        sub_span = (VIMSH_YEARS[pl] / total_years) * NAK_SPAN_DEG
        if running <= sid_lon < running + sub_span:
            sub_lord = pl
            break
        running += sub_span
    return {"nakshatra": name, "star_lord": star_lord, "pada": pada, "sub_lord": sub_lord}


# ══════════════════════════════════════════════════════════════════
#  ASCENDANT (LAGNA) CALCULATION
# ══════════════════════════════════════════════════════════════════

def calc_gmst(jd_ut: float) -> float:
    """Greenwich Mean Sidereal Time in hours for given JD (UT)."""
    T = (jd_ut - 2451545.0) / 36525.0
    theta = 280.46061837 + 360.98564736629 * (jd_ut - 2451545.0) + 0.000387933 * T**2 - T**3 / 38710000
    return (theta % 360) / 15.0  # convert to hours


def calc_lmst(jd_ut: float, longitude_east: float) -> float:
    """Local Mean Sidereal Time in hours."""
    gmst = calc_gmst(jd_ut)
    return (gmst + longitude_east / 15.0) % 24.0


def calc_tropical_ascendant(lmst_hours: float, lat_deg: float) -> float:
    """Calculate tropical Ascendant longitude from LMST and latitude."""
    ramc = lmst_hours * 15.0  # convert hours to degrees
    e = 23.4393  # obliquity of ecliptic (degrees), good for 2020-2030
    ramc_r = _rad(ramc)
    lat_r  = _rad(lat_deg)
    e_r    = _rad(e)

    num = -math.cos(ramc_r)
    den = math.sin(ramc_r) * math.cos(e_r) + math.tan(lat_r) * math.sin(e_r)

    # atan2 to get correct quadrant
    asc_r = math.atan2(num, den)
    asc = _deg(asc_r) % 360.0
    return asc


def calc_sidereal_ascendant(jd_ut: float, lat: float, lon: float) -> dict:
    """Sidereal Lahiri Asc on ecliptic; prefer Swiss Ephemeris (aligns with KP verify / § C0b Method 2)."""
    lmst = calc_lmst(jd_ut, lon)
    try:
        import swisseph as swe

        swe.set_sid_mode(swe.SIDM_LAHIRI)
        _cusps, ascmc = swe.houses_ex(
            jd_ut, lat, lon, b"P", swe.FLG_SIDEREAL | swe.FLG_SWIEPH
        )
        sid_asc = ascmc[0] % 360.0
        ayanamsa = float(swe.get_ayanamsa_ut(jd_ut))
        trop_asc = (sid_asc + ayanamsa) % 360.0
        sign, deg = longitude_to_sign_degree(sid_asc)
        nak_info = get_nakshatra(sid_asc)
        return {
            "tropical_asc_deg": round(trop_asc, 2),
            "sidereal_asc_deg": round(sid_asc, 2),
            "sign": sign,
            "degree": round(deg, 2),
            "nakshatra": nak_info["nakshatra"],
            "star_lord": nak_info["star_lord"],
            "sub_lord": nak_info["sub_lord"],
            "pada": nak_info["pada"],
            "lmst_hours": round(lmst, 4),
            "ayanamsa": round(ayanamsa, 4),
            "asc_source": "swiss_ephemeris_sidereal_lahiri_placidus",
        }
    except ImportError:
        pass
    except Exception:
        pass

    trop_asc = calc_tropical_ascendant(lmst, lat)
    ayanamsa = get_ayanamsa(jd_ut)
    sid_asc = _norm(trop_asc - ayanamsa)
    sign, deg = longitude_to_sign_degree(sid_asc)
    nak_info = get_nakshatra(sid_asc)
    return {
        "tropical_asc_deg": round(trop_asc, 2),
        "sidereal_asc_deg": round(sid_asc, 2),
        "sign": sign,
        "degree": round(deg, 2),
        "nakshatra": nak_info["nakshatra"],
        "star_lord": nak_info["star_lord"],
        "sub_lord": nak_info["sub_lord"],
        "pada": nak_info["pada"],
        "lmst_hours": round(lmst, 4),
        "ayanamsa": round(ayanamsa, 4),
        "asc_source": "legacy_gmst_atan2_fallback_install_pyswisseph",
    }


# ══════════════════════════════════════════════════════════════════
#  ALL PLANET POSITIONS
# ══════════════════════════════════════════════════════════════════

def compute_all_planets(jd_ut: float) -> dict:
    """Compute sidereal positions for all 9 graha (+ Ketu).
    Uses reference+interpolation for accuracy near April 2026."""

    def make_planet_from_sid(name: str, sid: float, retrograde: bool = False) -> dict:
        sign, deg = longitude_to_sign_degree(sid)
        nak = get_nakshatra(sid)
        d = {
            "sidereal_lon": round(sid, 2),
            "sign": sign,
            "degree": round(deg, 2),
            "nakshatra": nak["nakshatra"],
            "star_lord": nak["star_lord"],
            "sub_lord": nak["sub_lord"],
        }
        if retrograde:
            d["retrograde"] = True
        return d

    planets = {}
    for name in ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn"]:
        sid = _planet_sidereal_lon(name, jd_ut)
        planets[name] = make_planet_from_sid(name, sid)

    rahu_sid = _planet_sidereal_lon("Rahu", jd_ut)
    ketu_sid = _norm(rahu_sid + 180.0)
    planets["Rahu"] = make_planet_from_sid("Rahu", rahu_sid, retrograde=True)
    planets["Ketu"] = make_planet_from_sid("Ketu", ketu_sid, retrograde=True)

    return planets


# ══════════════════════════════════════════════════════════════════
#  HOUSE PLACEMENTS (Whole-Sign from Lagna)
# ══════════════════════════════════════════════════════════════════

def compute_houses(lagna_sign: str, planets: dict) -> dict:
    """Return house number (1-12) for each planet from Lagna (whole-sign)."""
    lagna_idx = SIGNS.index(lagna_sign)
    result = {}
    for planet, info in planets.items():
        planet_sign = info["sign"]
        planet_idx  = SIGNS.index(planet_sign)
        house = ((planet_idx - lagna_idx) % 12) + 1
        result[planet] = house
    return result


def house_sign(lagna_sign: str, house_num: int) -> str:
    """Return the sign of a given house number from Lagna."""
    lagna_idx = SIGNS.index(lagna_sign)
    sign_idx  = (lagna_idx + house_num - 1) % 12
    return SIGNS[sign_idx]


def house_lord(lagna_sign: str, house_num: int) -> str:
    """Return the lord of a given house from Lagna."""
    sign = house_sign(lagna_sign, house_num)
    return SIGN_LORDS[sign]


# ══════════════════════════════════════════════════════════════════
#  KP HORARY NUMBER → SIGN + DEGREE
# ══════════════════════════════════════════════════════════════════

def kp_number_to_sign(kp_num: int) -> dict:
    """Map KP Horary number 1-249 via canonical table (fallback: linear band)."""
    try:
        from kp_horary_engine import kp_number_lookup
        return kp_number_lookup(kp_num)
    except Exception:
        pass
    for start, end, sign in KP_RANGES:
        if start <= kp_num <= end:
            total_in_range = end - start + 1
            position_in_range = kp_num - start
            deg = (position_in_range / total_in_range) * 30.0
            sign_idx = SIGNS.index(sign)
            sid_lon = sign_idx * 30.0 + deg
            nak = get_nakshatra(sid_lon)
            return {
                "kp_number": kp_num,
                "sign": sign,
                "approx_degree": round(deg, 2),
                "approx_sidereal_lon": round(sid_lon, 2),
                "sidereal_asc_deg": sid_lon,
                "nakshatra": nak["nakshatra"],
                "star_lord": nak["star_lord"],
                "sub_lord": nak["sub_lord"],
                "sign_lord": SIGN_LORDS[sign],
            }
    return {"error": f"KP number {kp_num} out of range 1-249"}


# ══════════════════════════════════════════════════════════════════
#  JAMAKKOL CALCULATIONS
# ══════════════════════════════════════════════════════════════════

def get_aarudam(minutes: int) -> str:
    """Minutes → Aarudam sign (Jamakkol)."""
    idx = min(minutes // 5, 11)  # 0-11 → Aries to Pisces
    return SIGNS[idx]


def get_veedhi(sun_sign: str) -> str:
    """Transit Sun sign → Veedhi name."""
    mesha_veedhi  = {"Taurus","Gemini","Cancer","Leo"}
    rishaba_veedhi = {"Pisces","Aries","Virgo","Libra"}
    # mithuna veedhi = rest
    if sun_sign in mesha_veedhi:
        return "Mesha"
    elif sun_sign in rishaba_veedhi:
        return "Rishaba"
    else:
        return "Mithuna"


def get_veedhi_endpoint_sign(veedhi: str) -> str:
    """Veedhi name → target sign for Kavippu counting."""
    return {"Mesha": "Aries", "Rishaba": "Taurus", "Mithuna": "Gemini"}[veedhi]


def count_signs_forward(from_sign: str, to_sign: str) -> int:
    """Count signs from 'from_sign' to 'to_sign' inclusive (1-based forward count)."""
    from_idx = SIGNS.index(from_sign)
    to_idx   = SIGNS.index(to_sign)
    return ((to_idx - from_idx) % 12) + 1


def jamakkol_udhayam_method1(
    sun_sidereal_deg: float,
    query_minutes_after_sunrise: int,
) -> dict:
    """
    GK Method 1 Udhayam: (query - sunrise) minutes / 2 added to transit Sun longitude.
    Returns whole-sign Udhayam and sidereal longitude (mod 360).
    """
    add_deg = query_minutes_after_sunrise / 2.0
    lon = (sun_sidereal_deg + add_deg) % 360.0
    sign = SIGNS[int(lon // 30) % 12]
    return {
        "udhayam_sign": sign,
        "udhayam_sidereal_deg": round(lon, 4),
        "minutes_after_sunrise": query_minutes_after_sunrise,
        "added_degrees": add_deg,
    }


def get_kavippu(aarudam: str, udhayam: str, veedhi: str) -> dict:
    """Calculate Kavippu sign and its house from Udhayam."""
    veedhi_target = get_veedhi_endpoint_sign(veedhi)
    # Count from Aarudam to Veedhi endpoint (inclusive)
    count = count_signs_forward(aarudam, veedhi_target)
    # Count same number from Udhayam
    udhayam_idx  = SIGNS.index(udhayam)
    kavippu_idx  = (udhayam_idx + count - 1) % 12
    kavippu_sign = SIGNS[kavippu_idx]
    # House of Kavippu from Udhayam
    house = ((kavippu_idx - udhayam_idx) % 12) + 1
    return {
        "aarudam": aarudam,
        "udhayam": udhayam,
        "veedhi": veedhi,
        "veedhi_target": veedhi_target,
        "count_aarudam_to_veedhi": count,
        "kavippu_sign": kavippu_sign,
        "kavippu_house_from_udhayam": house,
        "kavippu_meaning": KAVIPPU_MEANINGS.get(house, "Unknown"),
    }


def aarudam_house_from_udhayam(aarudam: str, udhayam: str) -> int:
    """House of Aarudam from Udhayam (1-12)."""
    a_idx = SIGNS.index(aarudam)
    u_idx = SIGNS.index(udhayam)
    return ((a_idx - u_idx) % 12) + 1


def compute_jamakkol(minutes: int, sun_sign: str, lagna_sign: str,
                      planets: dict, houses: dict, question_topic: str) -> dict:
    """Full Jamakkol analysis."""
    aarudam = get_aarudam(minutes)
    udhayam = lagna_sign
    veedhi  = get_veedhi(sun_sign)
    kavippu = get_kavippu(aarudam, udhayam, veedhi)

    aarudam_house = aarudam_house_from_udhayam(aarudam, udhayam)
    udhayam_planets = [p for p, h in houses.items() if h == 1]
    kavippu_house = kavippu["kavippu_house_from_udhayam"]
    kavippu_conjunct_planets = [
        p for p, info in planets.items()
        if info["sign"] == kavippu["kavippu_sign"] and p not in ("Ketu",)
    ]

    # Topic bhava from Aarudam house (GK: Aarudam identifies query subject)
    tb = TOPIC_BHAVAS.get(question_topic, TOPIC_BHAVAS["general"])
    topic_bhava = aarudam_house  # Aarudam house = query topic indicator
    kav_from_topic = ((kavippu_house - topic_bhava) % 12) + 1 if topic_bhava else kavippu_house
    if kavippu_house == topic_bhava:
        kav_from_topic = 1  # same house = denied

    # Verdict: Kavippu house + cross-rules (GK Rules 3, 4, 6)
    if kavippu_house == 11 or kav_from_topic == 11:
        verdict = "YES"
        verdict_reason = "Kavippu in 11th from Udhayam or from query-topic bhava — fulfilment"
    elif kavippu_house == topic_bhava or kav_from_topic == 1:
        verdict = "NO"
        verdict_reason = "Kavippu in same house as query topic (Aarudam) — query denied or troubled"
    elif kav_from_topic in (6, 8, 12):
        verdict = "NO"
        verdict_reason = f"Kavippu in {kav_from_topic}th from query-topic bhava — obstacles/loss"
    elif kavippu_conjunct_planets:
        verdict = "NO"
        verdict_reason = f"Kavippu conjunct {', '.join(kavippu_conjunct_planets)} — karaka negated for topic"
    elif kavippu_house in (1, 2, 3, 7, 10, 12):
        verdict = "NO"
        verdict_reason = KAVIPPU_MEANINGS.get(kavippu_house, "Obstacle")
    elif kavippu_house in (4, 5, 6, 8, 9):
        verdict = "CONDITIONAL"
        verdict_reason = KAVIPPU_MEANINGS.get(kavippu_house, "Mixed")
    else:
        verdict = "CONDITIONAL"
        verdict_reason = "Mixed indicators"

    # Radicality checks for Jamakkol
    jamakkol_radical_flags = []
    if kavippu_house == 1:
        jamakkol_radical_flags.append("Kavippu in 1st house (query turns back to questioner — test question indicator)")
    if aarudam_house == 1:
        jamakkol_radical_flags.append("Aarudam in 1st house (questioner is both asker and subject — non-radical)")
    udhayam_idx  = SIGNS.index(udhayam)
    aarudam_idx  = SIGNS.index(aarudam)
    rel = (aarudam_idx - udhayam_idx) % 12 + 1
    if rel in [6, 8, 12]:
        jamakkol_radical_flags.append(f"Aarudam in {rel}th from Udhayam (6/8/12 = strained relationship — marginal chart)")

    return {
        "aarudam": aarudam,
        "udhayam": udhayam,
        "veedhi": veedhi,
        "kavippu": kavippu,
        "aarudam_house_from_udhayam": aarudam_house,
        "topic_bhava_from_aarudam": topic_bhava,
        "kavippu_house_from_topic": kav_from_topic,
        "planets_in_udhayam": udhayam_planets,
        "kavippu_conjunct_planets": kavippu_conjunct_planets,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "radicality_flags": jamakkol_radical_flags,
    }


# ══════════════════════════════════════════════════════════════════
#  RULING PLANETS
# ══════════════════════════════════════════════════════════════════

WEEKDAY_LORDS = {0:"Moon", 1:"Mars", 2:"Mercury", 3:"Jupiter", 4:"Venus", 5:"Saturn", 6:"Sun"}
# Python: Monday=0, Sunday=6; Vedic: Sun=Sunday, Moon=Monday, Mars=Tuesday...
# Python weekday() → 0=Mon, 6=Sun. Map to Vedic:
PYTHON_WEEKDAY_TO_VEDIC = {0:"Moon", 1:"Mars", 2:"Mercury", 3:"Jupiter", 4:"Venus", 5:"Saturn", 6:"Sun"}


def compute_ruling_planets(q_date_obj: Date, lagna: dict, moon: dict) -> dict:
    """Compute KP Ruling Planets at question time."""
    weekday = q_date_obj.weekday()  # 0=Monday
    day_lord = PYTHON_WEEKDAY_TO_VEDIC[weekday]

    lagna_sign_lord = SIGN_LORDS[lagna["sign"]]
    lagna_star_lord = lagna["star_lord"]

    moon_sign_lord = SIGN_LORDS[moon["sign"]]
    moon_star_lord = moon["star_lord"]

    # Collect unique ruling planets
    all_rps = list(dict.fromkeys([
        day_lord, lagna_sign_lord, lagna_star_lord,
        moon_sign_lord, moon_star_lord
    ]))

    return {
        "day_lord": day_lord,
        "lagna_sign_lord": lagna_sign_lord,
        "lagna_star_lord": lagna_star_lord,
        "moon_sign_lord": moon_sign_lord,
        "moon_star_lord": moon_star_lord,
        "all_ruling_planets": all_rps,
    }


# ══════════════════════════════════════════════════════════════════
#  RADICALITY CHECK (8 indicators)
# ══════════════════════════════════════════════════════════════════

def compute_radicality(lagna: dict, planets: dict, houses: dict,
                        jamakkol: dict, ruling_planets: dict,
                        question_topic: str) -> dict:
    """Score all 8 radicality indicators."""
    flags = []
    score = 0

    # 1. Jamakkol: Kavippu in 1st
    if jamakkol["kavippu"]["kavippu_house_from_udhayam"] == 1:
        flags.append("Jamakkol R1: Kavippu in 1st house — query about self, not genuine external matter")
        score += 1

    # 2. Jamakkol: Aarudam in 1st
    if jamakkol["aarudam_house_from_udhayam"] == 1:
        flags.append("Jamakkol R2: Aarudam = Udhayam (1st house) — questioner is own subject")
        score += 1

    # 3. Jamakkol: Aarudam in 6/8/12 from Udhayam
    flags.extend(jamakkol.get("radicality_flags", []))
    score += len([f for f in jamakkol.get("radicality_flags", []) if "6/8/12" in f])

    # 4. Prashna: Saturn in Lagna (1st house)
    if houses.get("Saturn") == 1:
        flags.append("Prashna R4: Saturn in Lagna — hesitation, doubt, or test question")
        score += 1

    # 5. Prashna: Lagna lord in 6/8/12
    lagna_lord = SIGN_LORDS[lagna["sign"]]
    ll_house = houses.get(lagna_lord, 0)
    if ll_house in [6, 8, 12]:
        flags.append(f"Prashna R5: Lagna lord {lagna_lord} in {ll_house}th — afflicted questioner intent")
        score += 1

    # 6. KP: Sub-lord of Lagna in denying houses (not topic-favorable)
    # (We check the lagna's sub-lord's house placement)
    lagna_sublord = lagna.get("sub_lord", "")
    if lagna_sublord:
        sl_house = houses.get(lagna_sublord, 0)
        if sl_house in [6, 8, 12]:
            flags.append(f"KP R6: Lagna sub-lord {lagna_sublord} in {sl_house}th — chart lacks energy for clear answer")
            score += 1

    # 7. KP: Ruling Planets have no connection to query topic
    topic_bhavas = TOPIC_BHAVAS.get(question_topic.lower(), TOPIC_BHAVAS["general"])
    favorable = topic_bhavas["favorable"]
    rp_connected = [p for p in ruling_planets["all_ruling_planets"]
                    if houses.get(p, 0) in favorable]
    if len(rp_connected) == 0:
        flags.append(f"KP R7: None of the Ruling Planets occupy topic-favorable houses {favorable} — artificial question")
        score += 1

    # 8. Moon afflicted (waning + with malefics)
    moon_house = houses.get("Moon", 1)
    malefics_with_moon = [p for p in ["Saturn","Mars","Rahu","Ketu"]
                           if planets[p]["sign"] == planets["Moon"]["sign"]]
    if len(malefics_with_moon) >= 2:
        flags.append(f"Prashna R8: Moon afflicted by {malefics_with_moon} — weakened chart integrity")
        score += 1

    if score == 0:
        interpretation = "Chart is RADICAL — proceed with full analysis (high reliability)"
    elif score <= 2:
        interpretation = "Chart is MARGINAL — proceed but note lower reliability"
    else:
        interpretation = f"Chart likely NON-GENUINE / test question — {score} radicality flags fired. State concern clearly."

    return {
        "score": score,
        "max_score": 8,
        "flags": flags,
        "interpretation": interpretation,
        "is_likely_test": score >= 3,
    }


# ══════════════════════════════════════════════════════════════════
#  GENDER CHECK (5 indicators for boy/girl questions)
# ══════════════════════════════════════════════════════════════════

def compute_gender_check(
    lagna_sign: str,
    planets: dict,
    houses: dict,
    lagna: dict,
    kp_chart_a_sign: Optional[str] = None,
) -> dict:
    """
    Child-sex **mnemonic** tally (rāśi-only) + *Prashna Kundali Siddhanta* Verse 100
    check (Lagna rāśi vs Navāṃśa Lagna). The five-line score is **not** the full book;
    when rāśi and navāṃśa parity **disagree**, Verse 100 is an explicit **mixed** case
    (balance with other verses / KP sub-lord chain — see rules39 + skill §C0d).
    """
    scores = {"boy": 0, "girl": 0}
    indicators = []

    def odd_or_even(sign):
        return "Boy (odd sign)" if sign in ODD_SIGNS else "Girl (even sign)"

    # 1. Lagna sign
    r1 = odd_or_even(lagna_sign)
    indicators.append(f"1. Prashna Lagna = {lagna_sign} → {r1}")
    if "Boy" in r1:
        scores["boy"] += 1
    else:
        scores["girl"] += 1

    # 2. 5th house sign
    fifth_sign = house_sign(lagna_sign, 5)
    r2 = odd_or_even(fifth_sign)
    indicators.append(f"2. 5th house = {fifth_sign} → {r2}")
    if "Boy" in r2:
        scores["boy"] += 1
    else:
        scores["girl"] += 1

    # 3. 5th lord's sign
    fifth_lord = house_lord(lagna_sign, 5)
    fifth_lord_sign = planets[fifth_lord]["sign"] if fifth_lord in planets else fifth_sign
    r3 = odd_or_even(fifth_lord_sign)
    indicators.append(f"3. 5th lord {fifth_lord} in {fifth_lord_sign} → {r3}")
    if "Boy" in r3:
        scores["boy"] += 1
    else:
        scores["girl"] += 1

    # 4. Jupiter's sign (children karaka)
    jup_sign = planets["Jupiter"]["sign"]
    r4 = odd_or_even(jup_sign)
    indicators.append(f"4. Jupiter (children karaka) in {jup_sign} → {r4}")
    if "Boy" in r4:
        scores["boy"] += 1
    else:
        scores["girl"] += 1

    # 5. Majority of planets in odd vs even
    odd_count = sum(1 for p in planets.values() if p["sign"] in ODD_SIGNS)
    even_count = sum(1 for p in planets.values() if p["sign"] in EVEN_SIGNS)
    r5 = (
        f"Boy (majority odd: {odd_count})"
        if odd_count > even_count
        else f"Girl (majority even: {even_count})"
    )
    indicators.append(f"5. Planet majority: {odd_count} odd vs {even_count} even → {r5}")
    if "Boy" in r5:
        scores["boy"] += 1
    else:
        scores["girl"] += 1

    # 6. Navāṃśa Lagna (PK Verse 100 — same weight as rāśi for pure male/female rule)
    sid_deg = float(lagna.get("sidereal_asc_deg", 0.0))
    nav_sign = navamsa_lagna_sign(sid_deg)
    r6 = odd_or_even(nav_sign)
    rasi_odd = lagna_sign in ODD_SIGNS
    nav_odd = nav_sign in ODD_SIGNS
    verse100_pure_male = rasi_odd and nav_odd
    verse100_pure_female = (not rasi_odd) and (not nav_odd)
    verse100_mixed = rasi_odd != nav_odd
    indicators.append(
        f"6. Navāṃśa Lagna = {nav_sign} (from sidereal Asc {sid_deg:.2f}°) → {r6}"
    )
    if verse100_pure_male:
        scores["boy"] += 1
        indicators.append("   Verse 100: odd rāśi + odd navāṃśa → male pattern (+1 boy)")
    elif verse100_pure_female:
        scores["girl"] += 1
        indicators.append("   Verse 100: even rāśi + even navāṃśa → female pattern (+1 girl)")
    else:
        indicators.append(
            "   Verse 100: rāśi/navāṃśa parity **conflicts** — "
            "do not read HIGH confidence from rāśi-only tally; apply verses 86–98 + KP."
        )

    tally_boy = scores["boy"]
    tally_girl = scores["girl"]
    winner = "Boy" if tally_boy > tally_girl else "Girl" if tally_girl > tally_boy else "Tie"

    confidence = "HIGH" if max(tally_boy, tally_girl) >= 5 else "MODERATE" if max(tally_boy, tally_girl) >= 4 else "LOW"

    if verse100_mixed:
        confidence = "LOW"
        if winner in ("Boy", "Girl"):
            winner = "Mixed / verify (PK Verse 100 rāśi vs navāṃśa)"

    kp_even = kp_chart_a_sign and kp_chart_a_sign in EVEN_SIGNS
    kp_odd = kp_chart_a_sign and kp_chart_a_sign in ODD_SIGNS
    if kp_chart_a_sign and verse100_mixed:
        indicators.append(
            f"7. KP Chart A (1–249) rising rāśi = {kp_chart_a_sign} "
            f"({'even' if kp_even else 'odd'}) — geometry for Chart A; "
            "final sex answer needs **5th/11th cusp sub → star → houses** (rules39)."
        )
        if kp_even and tally_boy >= tally_girl:
            confidence = "LOW"
            winner = "Mixed / verify (rāśi tally vs even KP Chart A + Verse 100 mix)"

    note = (
        "PK Verse 100 requires both rāśi and navāṃśa for clean male/female; "
        "KP: Chart A sub-lord chain for 5/11 (Arumugam 2024 / rules39). "
        "Jamakkol: Aarudam odd/even is not a standalone sex lemma in OCR — use full GK steps."
    )

    return {
        "indicators": indicators,
        "boy_score": tally_boy,
        "girl_score": tally_girl,
        "verdict": winner,
        "confidence": confidence,
        "navamsa_lagna": nav_sign,
        "verse100_mixed_rasi_navamsa": verse100_mixed,
        "kp_chart_a_sign": kp_chart_a_sign,
        "note": note,
    }


# ══════════════════════════════════════════════════════════════════
#  TOPIC IDENTIFICATION
# ══════════════════════════════════════════════════════════════════

TOPIC_KEYWORDS = {
    "children": ["child", "speak", "baby", "son", "daughter", "pregnant", "pregnancy", "birth", "born", "kids", "kid", "progeny", "conceive"],
    "marriage":  ["marriage", "marry", "married", "wedding", "husband", "wife", "partner", "spouse", "relationship", "love", "alliance", "coalition", "divorce"],
    "career":    ["job", "career", "promotion", "salary", "hike", "transfer", "business", "work", "employment",
                  "interview", "selected", "selection", "recruit", "hire", "hired", "appointment", "joining", "offer letter", "office", "boss"],
    "disease_cure": ["cured", "cure", "recover", "recovery", "get well", "healed", "healing"],
    "disease":   ["disease", "illness", "sick", "hospital", "treatment", "ailment", "infection", "pain"],
    "health":    ["health", "surgery", "operation", "vitality"],
    "finance":   ["money", "finance", "loan", "wealth", "investment", "shares", "stocks", "debt", "profit", "loss"],
    "property":  ["property", "house", "flat", "apartment", "land", "plot", "real estate", "buy house", "build house", "villa", "residence", "purchase", "vehicle", "car", "home"],
    "travel":    ["travel", "trip", "foreign", "abroad", "visa", "move abroad", "move", "relocation", "relocate", "journey", "overseas", "settle abroad", "pr", "citizenship", "passport", "flight", "onsite"],
    "litigation": ["case", "court", "legal", "lawsuit", "lawyer", "police", "jail", "enemy", "dispute", "conflict", "hearing", "verdict"],
    "education": ["exam", "study", "education", "college", "university", "course", "result", "degree", "marks", "admission", "upsc"],
}

HORARY_INTENT_PHRASES: dict[str, list[str]] = {
    "travel": [
        "move abroad", "moving abroad", "settle abroad", "settling abroad", "settle overseas",
        "go abroad", "going abroad", "relocate abroad", "relocating abroad", "shift abroad",
        "live abroad", "living abroad", "work abroad", "travel abroad", "abroad with family",
        "abroad for job", "abroad for partner", "move to another country", "permanent residency",
        "green card", "greencard", "pr visa", "work visa", "student visa", "foreign settlement"
    ],
    "property": [
        "buy property", "buy house", "buy flat", "buy land", "buy apartment", "buy plot",
        "purchase property", "purchase house", "purchase flat", "purchase home", "purchase land",
        "purchase apartment", "purchase the apartment", "purchase an apartment", "purchase a flat", "purchase a house",
        "build house", "construct house", "property dispute", "real estate investment", "apartment in",
        "sell property", "sell house", "sell flat", "sell land"
    ],
    "career": [
        "get promoted", "get promotion", "promotion and hike", "salary hike", "new job",
        "change job", "job switch", "switch job", "career growth", "career transition",
        "leadership role", "business expansion", "startup funding", "lose job", "layoff"
    ],
    "marriage": [
        "get married", "getting married", "love marriage", "arranged marriage", "will i marry",
        "when will i marry", "marital harmony", "relationship issues", "divorce case"
    ],
    "children": [
        "have a baby", "have children", "have kids", "conceive baby", "get pregnant",
        "pregnancy complications", "child birth", "childbirth"
    ],
    "disease_cure": [
        "recover from illness", "recover from disease", "cure disease", "medical recovery", "will i recover"
    ],
    "litigation": [
        "win court case", "legal dispute", "win lawsuit", "court hearing", "police case"
    ],
    "education": [
        "clear exam", "pass exam", "upsc exam", "university admission", "college admission", "exam result"
    ],
}


def detect_topic(question: str, area: str = "") -> str:
    """Map free-text (+ optional life-area dropdown) → horary topic."""
    q = (question or "").strip()
    if not q:
        return "general"

    # 1. If explicit area provided from dropdown, respect it
    if area:
        try:
            import semantic_question as SQ
            norm_area = SQ.normalize_area(area)
            if norm_area:
                forced = SQ.AREA_TO_HORARY_TOPIC.get(norm_area)
                if forced:
                    if forced == "health" and q:
                        ql = q.lower()
                        if any(kw in ql for kw in TOPIC_KEYWORDS.get("disease_cure", [])):
                            return "disease_cure"
                        if any(kw in ql for kw in TOPIC_KEYWORDS.get("disease", [])):
                            return "disease"
                    return forced
        except Exception:
            pass

    ql = q.lower()

    # 2. High-priority multi-word intent phrases
    for topic, phrases in HORARY_INTENT_PHRASES.items():
        if any(phrase in ql for phrase in phrases):
            return topic

    # 3. Semantic router
    try:
        import semantic_question as SQ
        routed = SQ.route(q, area="")
        if routed:
            if routed.topic and routed.topic != "general":
                if routed.method == "minilm" or routed.topic_score >= 0.28:
                    return routed.topic
            if routed.domain and routed.domain in TOPIC_BHAVAS:
                return routed.domain
    except Exception:
        pass

    # 4. Ordered keywords
    priority = ["travel", "property", "disease_cure", "disease", "litigation", "children", "marriage", "career", "health",
                "finance", "education"]
    for topic in priority:
        keywords = TOPIC_KEYWORDS.get(topic, [])
        if any(re.search(r"\b" + re.escape(kw) + r"\b", ql) for kw in keywords):
            return topic
    return "general"


# ══════════════════════════════════════════════════════════════════
#  LLM INSTRUCTIONS
# ══════════════════════════════════════════════════════════════════

def build_llm_instructions(
    question: str, topic: str, lagna: dict, planets: dict, houses: dict,
    jamakkol: dict, ruling_planets: dict, radicality: dict,
    kp_data: dict, gender: dict | None, prashna: dict | None = None,
) -> dict:
    """Build per-system LLM usage instructions from pre-computed data."""

    lagna_sign = lagna["sign"]
    lagna_lord = SIGN_LORDS[lagna_sign]

    # JAMAKKOL instructions
    kav = jamakkol["kavippu"]
    jamakkol_instr = f"""
JAMAKKOL PRASANAM — Pre-computed values (do NOT recalculate, use these directly):
  Aarudam sign   : {jamakkol['aarudam']} (house {jamakkol['aarudam_house_from_udhayam']} from Udhayam)
  Udhayam (Lagna): {jamakkol['udhayam']}
  Veedhi         : {kav['veedhi']} Veedhi (Sun in {planets['Sun']['sign']} → endpoint = {kav['veedhi_target']})
  Count (Aarudam→Veedhi): {kav['count_aarudam_to_veedhi']} signs
  Kavippu sign   : {kav['kavippu_sign']}
  Kavippu house  : {kav['kavippu_house_from_udhayam']}th from Udhayam
  Kavippu meaning: {kav['kavippu_meaning']}
  Planets in Udhayam (1st house): {jamakkol['planets_in_udhayam'] or 'None'}
  Kavippu conjunct planets: {jamakkol['kavippu_conjunct_planets'] or 'None'}
  Jamakkol VERDICT: {jamakkol['verdict']} — {jamakkol['verdict_reason']}

JAMAKKOL WRITING INSTRUCTIONS:
  1. State the Aarudam (query topic indicator) and what house it falls from Udhayam
  2. State the Kavippu sign and house — this is the primary outcome indicator
  3. Cross-check Kavippu house against the query topic bhava
  4. Give Jamakkol verdict: YES (Kavippu in 11th) / NO (Kavippu blocks topic bhava) / CONDITIONAL
"""

    # KP instructions
    if kp_data and "sign" in kp_data:
        kp_lagna = kp_data["sign"]
        kp_lagna_lord = SIGN_LORDS[kp_lagna]
        topic_bhavas = TOPIC_BHAVAS.get(topic, TOPIC_BHAVAS["general"])
        kp_instr = f"""
KP HORARY — Pre-computed values:
  KP Number    : {kp_data.get('kp_number')}
  KP Lagna sign: {kp_lagna} (sign lord = {kp_lagna_lord})
  Approx degree: {kp_data.get('approx_degree')}° in {kp_lagna}
  Nakshatra    : {kp_data.get('nakshatra')} (star lord = {kp_data.get('star_lord')}, sub-lord = {kp_data.get('sub_lord')})
  KP Lagna sub-lord: {kp_data.get('sub_lord')}
  
  For topic "{topic.upper()}":
    Primary bhava: {topic_bhavas['primary']}
    Favorable bhavas: {topic_bhavas['favorable']}
    Denying bhavas: {topic_bhavas['denying']}
  
  RULING PLANETS: {ruling_planets['all_ruling_planets']}
    Day lord      : {ruling_planets['day_lord']}
    Lagna sign lord: {ruling_planets['lagna_sign_lord']}
    Lagna star lord: {ruling_planets['lagna_star_lord']}
    Moon sign lord : {ruling_planets['moon_sign_lord']}
    Moon star lord : {ruling_planets['moon_star_lord']}

KP WRITING INSTRUCTIONS:
  1. Use the KP Lagna sub-lord ({kp_data.get('sub_lord')}) as the key indicator
  2. Check which houses the sub-lord's star-lord signifies from the KP lagna
  3. Compare to favorable/denying bhavas for "{topic}" topic
  4. Cross-check against Ruling Planets
  5. Note: sub-lord details require exact KP software chart — if available, use those; otherwise use the pre-computed sign-level analysis above
"""
    else:
        kp_instr = "KP Horary: No KP number provided. Derive from question-time seconds mod 249 + 1, or ask user."

    # PRASHNA KUNDALI instructions
    if prashna:
        pra = prashna
        prashna_instr = f"""
PRASHNA KUNDALI SIDDHANTA — Pre-computed chart analysis:
  Arudha sign    : {pra['arudha_sign']} (house {pra['arudha_house_from_lagna']} from Lagna; {pra['arudha_source']})
  Prashna Lagna   : {lagna_sign} (lord = {lagna_lord}, in house {pra['ll_house']})
  Lagna lord status: {pra['ll_status']}
  Malefics in Lagna: {pra['malefics_in_lagna'] or 'None'}
  Benefics in kendra: {pra['benefics_in_kendra'] or 'None'}
  Jupiter in house : {pra['jup_house']} | aspects Lagna: {pra['jup_aspects_lagna']} | aspects Moon: {pra['jup_aspects_moon']}
  Moon in house    : {pra['moon_house']} | Paksha: {pra['paksha']}
  Gandanta Lagna   : {pra['gandanta_lagna']}

  For topic "{topic.upper()}" (bhava {pra['primary_bhava']}):
    {pra['primary_bhava']}th lord: {pra['topic_lord']} in house {pra['tl_house']} — {pra['tl_status']}
    Classical notes: {'; '.join(pra['notes'][:6]) if pra.get('notes') else 'None'}

  PRASHNA VERDICT: {pra['label']} (score {pra['score']:.2f})

PRASHNA WRITING INSTRUCTIONS:
  1. State Arudha sign and its house from Lagna
  2. State Lagna condition (benefics/malefics, lord placement, gandanta if any)
  3. State Jupiter aspect on Lagna and Moon (protective or absent)
  4. State topic bhava ({pra['primary_bhava']}th) lord placement
  5. Apply topic-specific classical rules from the notes above
  6. Give Prashna verdict: YES / NO / CONDITIONAL / NEUTRAL
"""
    else:
        lagna_house_of_ll = houses.get(lagna_lord, 0)
        jupiter_house = houses.get("Jupiter", 0)
        try:
            from prashna_kundali_engine import jupiter_aspects_house
            jupiter_aspects_lagna = jupiter_aspects_house(jupiter_house, 1)
        except ImportError:
            jupiter_aspects_lagna = jupiter_house in [1, 2, 4, 5, 7, 9, 12]
        moon_house = houses.get("Moon", 0)
        malefics_in_lagna = [p for p, h in houses.items() if h == 1 and p in ["Saturn", "Mars", "Rahu", "Ketu", "Sun"]]

        topic_bhavas_prashna = TOPIC_BHAVAS.get(topic, TOPIC_BHAVAS["general"])
        topic_bhava_lord = house_lord(lagna_sign, topic_bhavas_prashna["primary"])
        topic_bhava_lord_house = houses.get(topic_bhava_lord, 0)

        prashna_instr = f"""
PRASHNA KUNDALI SIDDHANTA — Pre-computed chart analysis:
  Prashna Lagna  : {lagna_sign} (lord = {lagna_lord}, in house {lagna_house_of_ll})
  Lagna lord status: {'GOOD (kendra/trikona)' if lagna_house_of_ll in [1,2,4,5,7,9,10,11] else 'WEAK (dusthana)' if lagna_house_of_ll in [6,8,12] else 'NEUTRAL'}
  Malefics in Lagna: {malefics_in_lagna or 'None — clean Lagna'}
  Jupiter in house : {jupiter_house} {'-> ASPECTS LAGNA (protective)' if jupiter_aspects_lagna else '-> Does not aspect Lagna'}
  Moon in house    : {moon_house}

  For topic "{topic.upper()}" (bhava {topic_bhavas_prashna['primary']}):
    {topic_bhavas_prashna['primary']}th house sign: {house_sign(lagna_sign, topic_bhavas_prashna['primary'])}
    {topic_bhavas_prashna['primary']}th lord: {topic_bhava_lord} in house {topic_bhava_lord_house}
    Topic lord status: {'FAVORABLE' if topic_bhava_lord_house in topic_bhavas_prashna['favorable'] else 'DENYING' if topic_bhava_lord_house in topic_bhavas_prashna['denying'] else 'NEUTRAL'}

PRASHNA WRITING INSTRUCTIONS:
  1. State Lagna condition (benefics/malefics, lord placement)
  2. State Jupiter aspect on Lagna (protective or absent)
  3. State topic bhava ({topic_bhavas_prashna['primary']}th) condition and lord placement
  4. Apply topic-specific classical rules (marriage/children/health/career as applicable)
  5. Give Prashna verdict: YES / NO / CONDITIONAL
"""

    # RADICALITY instructions
    rad_instr = f"""
RADICALITY CHECK RESULT:
  Score: {radicality['score']}/8 flags fired
  Interpretation: {radicality['interpretation']}
  Flags:
{chr(10).join('    - ' + f for f in radicality['flags']) if radicality['flags'] else '    (None — chart is radical)'}

WRITING INSTRUCTION: {'State radicality concern prominently before giving verdict — reduce confidence to LOW.' if radicality['is_likely_test'] else 'State chart is radical — proceed with normal confidence.'}
"""

    # GENDER instructions (only for children-related questions)
    gender_instr = ""
    if gender and topic in ["children"]:
        gnav = gender.get("navamsa_lagna", "?")
        gmix = gender.get("verse100_mixed_rasi_navamsa", False)
        gender_instr = f"""
GENDER / SEX OF CHILD (automated aids — **not** a full *Prashna Kundali* verse count):
  Boy score  : {gender['boy_score']}/6 (includes Navāṃśa Lagna when Verse 100 applies)
  Girl score : {gender['girl_score']}/6
  Navāṃśa Lagna: {gnav}  |  Verse 100 rāśi/navāṃśa conflict: {gmix}
  Verdict    : {gender['verdict']} — {gender['confidence']} confidence
  Indicators :
{chr(10).join('    ' + ind for ind in gender['indicators'])}
  Note: {gender.get('note', '')}

  Jamakkol: Aarudam={jamakkol['aarudam']} (topic timing — not OCR‑proven standalone sex rule)
  KP Chart A rāśi: {kp_data.get('sign','?')} — use **cusp sub-lords** for 5th/11th per rules39
"""

    return {
        "jamakkol": jamakkol_instr.strip(),
        "kp_horary": kp_instr.strip(),
        "prashna_kundali": prashna_instr.strip(),
        "radicality": rad_instr.strip(),
        "gender_check": gender_instr.strip() if gender_instr else None,
    }


# ══════════════════════════════════════════════════════════════════
#  MAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════

def precompute_horary(
    question: str,
    q_date_str: str,     # YYYY-MM-DD
    q_time_str: str,     # HH:MM  (24hr IST)
    location: str = "New Delhi",
    kp_number: str = "",
    area: str = "",
) -> dict:
    """
    Master function: compute all horary/prashna math and return structured JSON.
    """
    # Parse inputs
    hour, minute = parse_time(q_time_str)
    year, month, day = map(int, q_date_str.split("-"))
    q_date_obj = Date(year, month, day)

    # Get lat/lon for location
    loc_key = location.lower().split(",")[0].strip()
    lat, lon = LOCATIONS.get(loc_key, LOCATIONS["delhi"])  # default New Delhi

    # UT from IST
    ut_hour = ist_to_ut(hour, minute)
    # Handle day boundary (if ut < 0, subtract a day)
    jd_adjustment = 0
    if ut_hour < 0:
        ut_hour += 24
        jd_adjustment = -1

    jd_ut = julian_day(year, month, day, ut_hour) + jd_adjustment

    # Compute Ascendant
    lagna = calc_sidereal_ascendant(jd_ut, lat, lon)
    lagna_sign = lagna["sign"]

    # Compute planet positions
    planets = compute_all_planets(jd_ut)

    # Whole-sign house placements
    houses = compute_houses(lagna_sign, planets)

    # Detect topic (life-area dropdown pins the domain when set)
    topic = detect_topic(question, area=area)

    # KP Horary (Chart A + Chart B when Swiss Ephemeris available)
    kp_data = {}
    kp_chart_a = {}
    kp_chart_b = {}
    kp_num_int = None
    if kp_number.strip() and kp_number.strip().isdigit():
        kp_num_int = int(kp_number.strip())
    elif not kp_number.strip():
        auto_kp = ((minute * 60) % 249) + 1
        kp_num_int = auto_kp

    if kp_num_int and 1 <= kp_num_int <= 249:
        try:
            from kp_horary_engine import compute_kp_horary
            kp_pack = compute_kp_horary(kp_num_int, jd_ut, lat, lon, topic, q_date_obj.weekday())
            kp_data = kp_pack["kp_data"]
            kp_chart_a = kp_pack["chart_a"]
            kp_chart_b = kp_pack["chart_b"]
            ruling_planets = kp_pack["ruling_planets"]
        except Exception:
            kp_data = kp_number_to_sign(kp_num_int)
            ruling_planets = compute_ruling_planets(q_date_obj, lagna, planets["Moon"])
            if not kp_number.strip():
                kp_data["auto_derived"] = True
                kp_data["note"] = (
                    f"Auto-derived from question minute ({minute}x60 mod 249 + 1 = {kp_num_int}). "
                    "Install pyswisseph for full Chart A/B KP horary."
                )
    else:
        ruling_planets = compute_ruling_planets(q_date_obj, lagna, planets["Moon"])

    # Jamakkol
    sun_sign = planets["Sun"]["sign"]
    jamakkol = compute_jamakkol(minute, sun_sign, lagna_sign, planets, houses, topic)

    # Radicality
    radicality = compute_radicality(lagna, planets, houses, jamakkol, ruling_planets, topic)

    # Gender check (always compute, LLM uses only if relevant)
    kp_a_sign = kp_data.get("sign") if kp_data else None
    gender = compute_gender_check(lagna_sign, planets, houses, lagna, kp_a_sign)

    # House lordships
    house_lords = {i: {"sign": house_sign(lagna_sign, i), "lord": house_lord(lagna_sign, i)}
                   for i in range(1, 13)}

    from prashna_kundali_engine import compute_paksha, analyze_prashna
    paksha = compute_paksha(
        planets["Sun"].get("sidereal_lon", 0),
        planets["Moon"].get("sidereal_lon", 0),
    )

    scratch = {
        "meta": {"detected_topic": topic, "paksha": paksha},
        "lagna": lagna,
        "planets": planets,
        "houses": houses,
    }
    prashna = analyze_prashna(scratch)

    # LLM instructions
    llm_instructions = build_llm_instructions(
        question, topic, lagna, planets, houses,
        jamakkol, ruling_planets, radicality, kp_data,
        gender if topic == "children" else None,
        prashna=prashna,
    )

    return {
        "meta": {
            "question": question,
            "q_date": q_date_str,
            "q_time_ist": q_time_str,
            "q_time_ut": f"{int(ut_hour):02d}:{int((ut_hour % 1) * 60):02d}",
            "location": location,
            "lat": lat,
            "lon": lon,
            "julian_day": round(jd_ut, 6),
            "ayanamsa": round(lagna["ayanamsa"], 4),
            "detected_topic": topic,
            "kp_number": kp_num_int or kp_data.get("kp_number"),
            "paksha": paksha,
        },
        "lagna": lagna,
        "planets": planets,
        "houses": houses,
        "house_lords": house_lords,
        "jamakkol": jamakkol,
        "kp_data": kp_data,
        "kp_chart_a": kp_chart_a,
        "kp_chart_b": kp_chart_b,
        "ruling_planets": ruling_planets,
        "radicality": radicality,
        "gender_check": gender,
        "prashna": prashna,
        "llm_lane_instructions": llm_instructions,
    }


# ══════════════════════════════════════════════════════════════════
#  CLI ENTRY POINT
# ══════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 5:
        print("Usage: python3 horary_precompute.py <question> <YYYY-MM-DD> <HH:MM> <location> [kp_number] [output.json]")
        print('Example: python3 horary_precompute.py "Will child speak?" "2026-04-07" "03:12" "New Delhi" 23')
        sys.exit(1)

    question   = sys.argv[1]
    q_date     = sys.argv[2]
    q_time     = sys.argv[3]
    location   = sys.argv[4]
    kp_number  = sys.argv[5] if len(sys.argv) > 5 else ""
    out_path   = sys.argv[6] if len(sys.argv) > 6 else "horary_precomputed.json"

    # Skip if kp_number argument is actually the output path
    if kp_number and (kp_number.endswith(".json") or "/" in kp_number):
        out_path  = kp_number
        kp_number = ""

    result = precompute_horary(question, q_date, q_time, location, kp_number)

    out_file = Path(out_path)
    out_file.write_text(json.dumps(result, indent=2), encoding="utf-8")

    # Summary to stdout
    lagna     = result["lagna"]
    jamakkol  = result["jamakkol"]
    kp        = result["kp_data"]
    rad       = result["radicality"]
    gender    = result["gender_check"]

    print(f"Horary Pre-compute Complete")
    print(f"  Question : {question}")
    print(f"  Date/Time: {q_date} {q_time} IST | {location} | JD {result['meta']['julian_day']}")
    print(f"  Lagna    : {lagna['sign']} {lagna['degree']}° | nak={lagna['nakshatra']} | star={lagna['star_lord']}")
    print(f"  Ayanamsa : {lagna['ayanamsa']}°")
    print()
    print(f"  PLANETS (sidereal):")
    for name, info in result["planets"].items():
        print(f"    {name:<8}: {info['sign']:<13} {info['degree']:5.1f}°  H{result['houses'][name]}  nak={info['nakshatra']}")
    print()
    print(f"  JAMAKKOL:")
    kav = jamakkol["kavippu"]
    print(f"    Aarudam={jamakkol['aarudam']} | Udhayam={jamakkol['udhayam']} | Veedhi={kav['veedhi']}")
    print(f"    Kavippu={kav['kavippu_sign']} (H{kav['kavippu_house_from_udhayam']}) → {jamakkol['verdict']}")
    print()
    print(f"  KP: {kp.get('sign','?')} | sub-lord={kp.get('sub_lord','?')}")
    print(f"  Ruling Planets: {result['ruling_planets']['all_ruling_planets']}")
    print(f"  Radicality: {rad['score']}/8 flags | {rad['interpretation'][:60]}")
    print(
        f"  Gender check: {gender['verdict']} "
        f"({gender['boy_score']}/6 boy, {gender['girl_score']}/6 girl; "
        f"Navāṃśa Lagna={gender.get('navamsa_lagna', '?')})"
    )
    print()
    print(f"  Output → {out_path}")


if __name__ == "__main__":
    main()
