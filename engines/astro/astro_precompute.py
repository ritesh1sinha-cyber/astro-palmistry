#!/usr/bin/env python3
"""
astro_precompute.py — Pre-compute all Vedic astrology math before LLM interpretation.

Reads: VedicReport_*_extracted.txt + client name + DOB
Writes: precomputed_data.json  (structured facts + LLM usage notes per lane)

The LLM receives verified numbers and only needs to do interpretation/narrative.
No more math errors, no more dasha date mistakes, no more dignity guessing.

Usage:
    python3 astro_precompute.py <extracted_txt> <client_name> <YYYY-MM-DD> [output.json]
"""

import json, re, sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

# ══════════════════════════════════════════════════════════════════
#  LOOKUP TABLES
# ══════════════════════════════════════════════════════════════════

SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
         "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

SIGN_ABBR = {"Ar":"Aries","Ta":"Taurus","Ge":"Gemini","Ca":"Cancer","Le":"Leo","Vi":"Virgo",
             "Li":"Libra","Sc":"Scorpio","Sa":"Sagittarius","Cp":"Capricorn","Aq":"Aquarius","Pi":"Pisces",
             "Aries":"Aries","Taurus":"Taurus","Gemini":"Gemini","Cancer":"Cancer","Leo":"Leo",
             "Virgo":"Virgo","Libra":"Libra","Scorpio":"Scorpio","Sagittarius":"Sagittarius",
             "Capricorn":"Capricorn","Aquarius":"Aquarius","Pisces":"Pisces"}

NAKSHATRAS = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
    "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni",
    "Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha",
    "Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishtha","Shatabhisha",
    "Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

# Each nakshatra = 13°20' = 13.3333°; each pada = 3°20' = 3.3333°
NAK_SPAN = 360 / 27  # 13.3333°
PADA_SPAN = NAK_SPAN / 4  # 3.3333°

# Nakshatra → Vimshottari dasha lord (repeating cycle of 9)
NAK_LORDS_SEQ = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]
NAK_TO_DASHA_LORD = {n: NAK_LORDS_SEQ[i % 9] for i, n in enumerate(NAKSHATRAS)}

# AstroSage / PDF extract spellings → canonical names
NAK_ALIASES = {
    "Mrigasira": "Mrigashira",
    "Ashvini": "Ashwini",
    "Purvabhadra": "Purva Bhadrapada",
    "Uttarabhadra": "Uttara Bhadrapada",
    "Uttarashadha": "Uttara Ashadha",
    "Purvashadha": "Purva Ashadha",
    "Pashyami": "Pushya",
    "Pushya": "Pushya",
    "Pushyami": "Pushya",
    "Sravana": "Shravana",
    "Dhanista": "Dhanishtha",
    "Vishakha": "Vishakha",
    "Hast": "Hasta",
    "Krittika": "Krittika",
}


def normalize_nakshatra(raw: str) -> str:
    """Map PDF/OCR nakshatra labels to canonical NAKSHATRAS entries."""
    if not raw:
        return ""
    raw = raw.strip()
    if raw in NAKSHATRAS:
        return raw
    if raw in NAK_ALIASES:
        return NAK_ALIASES[raw]
    compact = re.sub(r"[^A-Za-z]", "", raw).lower()
    for n in NAKSHATRAS:
        if re.sub(r"[^A-Za-z]", "", n).lower() == compact:
            return n
    for alias, canon in NAK_ALIASES.items():
        if re.sub(r"[^A-Za-z]", "", alias).lower() == compact:
            return canon
    return raw


# Sign lords
SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}

# Dignity tables
DIGNITY_TABLE = {
    "Sun":     {"exalted":"Aries","debilitated":"Libra","own":["Leo"],"moolatrikona":"Leo","exalt_degree":10},
    "Moon":    {"exalted":"Taurus","debilitated":"Scorpio","own":["Cancer"],"moolatrikona":"Taurus","exalt_degree":3},
    "Mars":    {"exalted":"Capricorn","debilitated":"Cancer","own":["Aries","Scorpio"],"moolatrikona":"Aries","exalt_degree":28},
    "Mercury": {"exalted":"Virgo","debilitated":"Pisces","own":["Gemini","Virgo"],"moolatrikona":"Virgo","exalt_degree":15},
    "Jupiter": {"exalted":"Cancer","debilitated":"Capricorn","own":["Sagittarius","Pisces"],"moolatrikona":"Sagittarius","exalt_degree":5},
    "Venus":   {"exalted":"Pisces","debilitated":"Virgo","own":["Taurus","Libra"],"moolatrikona":"Libra","exalt_degree":27},
    "Saturn":  {"exalted":"Libra","debilitated":"Aries","own":["Capricorn","Aquarius"],"moolatrikona":"Aquarius","exalt_degree":20},
    "Rahu":    {"exalted":"Gemini","debilitated":"Sagittarius","own":[],"moolatrikona":"","exalt_degree":0},
    "Ketu":    {"exalted":"Sagittarius","debilitated":"Gemini","own":[],"moolatrikona":"","exalt_degree":0},
}

# Friendship table (simplified — mutual friends)
FRIENDS = {
    "Sun":     ["Moon","Mars","Jupiter"],
    "Moon":    ["Sun","Mercury"],
    "Mars":    ["Sun","Moon","Jupiter"],
    "Mercury": ["Sun","Venus"],
    "Jupiter": ["Sun","Moon","Mars"],
    "Venus":   ["Mercury","Saturn"],
    "Saturn":  ["Mercury","Venus"],
    "Rahu":    ["Mercury","Venus","Saturn"],
    "Ketu":    ["Mars","Venus","Saturn"],
}
ENEMIES = {
    "Sun":     ["Venus","Saturn"],
    "Moon":    ["Rahu","Ketu"],
    "Mars":    ["Mercury"],
    "Mercury": ["Moon"],
    "Jupiter": ["Mercury","Venus"],
    "Venus":   ["Sun","Moon"],
    "Saturn":  ["Sun","Moon","Mars"],
    "Rahu":    ["Sun","Moon","Mars"],
    "Ketu":    ["Sun","Moon","Mars"],
}

# Mrityu Bhaga critical degrees (index = sign index 0-11)
# Source: longevity literature; planet transiting exact degree = stress point
MRITYU_BHAGA = {
    "Sun":     [20, 9,12, 6, 8,24,26,14,13,10,19,23],
    "Moon":    [26,12,13,25,24,11,26,14,13,25, 5,12],
    "Mars":    [11,28,15,21,18, 9,11, 3,11,18,28,21],
    "Mercury": [15,14,13,12,11,10, 9, 8, 7, 6, 5, 4],
    "Jupiter": [ 6,12,13,15, 6, 2,10,19, 3,28, 9,12],
    "Venus":   [ 9, 3,16,12, 5,11,15, 3, 7,10,26, 4],
    "Saturn":  [ 8,18,16,17,17,21,11,14,11,20, 6,14],
    "Rahu":    [14,20,14,11,10, 5,14, 8,14,10,20,15],
    "Ketu":    [14,20,14,11,10, 5,14, 8,14,10,20,15],
}

# Functional benefic/malefic by lagna (Laghu Parashari)
FUNCTIONAL = {
    "Aries":       {"benefic":["Sun","Jupiter","Mars"],"malefic":["Mercury","Venus","Saturn","Rahu","Ketu"],"yogakaraka":[],"maraka":["Venus","Mercury"]},
    "Taurus":      {"benefic":["Saturn","Mercury","Venus"],"malefic":["Sun","Moon","Jupiter","Rahu","Ketu"],"yogakaraka":["Saturn"],"maraka":["Jupiter","Mars"]},
    "Gemini":      {"benefic":["Mercury","Venus","Saturn"],"malefic":["Mars","Jupiter","Sun","Rahu","Ketu"],"yogakaraka":[],"maraka":["Sun","Mars"]},
    "Cancer":      {"benefic":["Moon","Mars","Jupiter"],"malefic":["Mercury","Venus","Saturn","Rahu","Ketu"],"yogakaraka":[],"maraka":["Saturn","Mercury"]},
    "Leo":         {"benefic":["Sun","Mars","Jupiter"],"malefic":["Moon","Mercury","Venus","Saturn","Rahu","Ketu"],"yogakaraka":[],"maraka":["Saturn","Mercury"]},
    "Virgo":       {"benefic":["Mercury","Venus","Saturn"],"malefic":["Mars","Moon","Jupiter","Rahu","Ketu"],"yogakaraka":[],"maraka":["Mars","Moon"]},
    "Libra":       {"benefic":["Saturn","Mercury","Venus"],"malefic":["Sun","Moon","Mars","Jupiter","Rahu","Ketu"],"yogakaraka":["Saturn"],"maraka":["Mars","Jupiter"]},
    "Scorpio":     {"benefic":["Moon","Jupiter","Sun"],"malefic":["Mercury","Venus","Saturn","Rahu","Ketu"],"yogakaraka":[],"maraka":["Mercury","Venus"]},
    "Sagittarius": {"benefic":["Sun","Mars","Jupiter"],"malefic":["Mercury","Venus","Saturn","Rahu","Ketu"],"yogakaraka":[],"maraka":["Venus","Saturn"]},
    "Capricorn":   {"benefic":["Saturn","Mercury","Venus"],"malefic":["Moon","Mars","Jupiter","Rahu","Ketu"],"yogakaraka":[],"maraka":["Moon","Mars"]},
    "Aquarius":    {"benefic":["Saturn","Mercury","Venus"],"malefic":["Moon","Sun","Mars","Jupiter","Rahu","Ketu"],"yogakaraka":[],"maraka":["Moon","Mars"]},
    "Pisces":      {"benefic":["Moon","Mars","Jupiter"],"malefic":["Mercury","Venus","Saturn","Sun","Rahu","Ketu"],"yogakaraka":[],"maraka":["Saturn","Mercury"]},
}

# Vimshottari dasha sequence
VIMSH_LORDS = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]
VIMSH_YEARS = {    "Ketu":7,"Venus":20,"Sun":6,"Moon":10,"Mars":7,
    "Rahu":18,"Jupiter":16,"Saturn":19,"Mercury":17
}

# Yogini dasha
YOGINI_NAMES  = ["Mangala","Pingala","Dhanya","Bhramari","Bhadrika","Ulka","Siddha","Sankata"]
YOGINI_LORDS  = ["Moon","Sun","Jupiter","Mars","Mercury","Saturn","Venus","Rahu"]
YOGINI_YEARS  = [1, 2, 3, 4, 5, 6, 7, 8]
YOGINI_TONE   = {"Mangala":"auspicious","Pingala":"auspicious","Dhanya":"auspicious",
                 "Bhramari":"mixed","Bhadrika":"auspicious",
                 "Ulka":"inauspicious","Siddha":"auspicious","Sankata":"inauspicious"}

# Chaldean cipher
CHALDEAN = {
    'A':1,'B':2,'C':3,'D':4,'E':5,'F':8,'G':3,'H':5,'I':1,'J':1,'K':2,'L':3,'M':4,
    'N':5,'O':7,'P':8,'Q':1,'R':2,'S':3,'T':4,'U':6,'V':6,'W':6,'X':5,'Y':1,'Z':7
}

# ══════════════════════════════════════════════════════════════════
#  CORE MATH FUNCTIONS
# ══════════════════════════════════════════════════════════════════

def sign_index(sign: str) -> int:
    return SIGNS.index(sign) if sign in SIGNS else 0

def house_from_lagna(planet_sign: str, lagna_sign: str) -> int:
    """Whole-sign house (1-based) of planet from lagna."""
    return (sign_index(planet_sign) - sign_index(lagna_sign)) % 12 + 1

def house_sign(house_num: int, lagna_sign: str) -> str:
    """Sign of house N (1-based) from lagna."""
    return SIGNS[(sign_index(lagna_sign) + house_num - 1) % 12]

def degree_to_nakshatra(total_deg: float) -> dict:
    """Convert absolute sidereal degree (0–360) to nakshatra info."""
    total_deg = total_deg % 360
    nak_idx   = int(total_deg / NAK_SPAN)
    nak_idx   = min(nak_idx, 26)
    pada      = int((total_deg % NAK_SPAN) / PADA_SPAN) + 1
    pada      = min(pada, 4)
    sign_idx  = int(total_deg / 30)
    deg_in    = round(total_deg % 30, 4)
    return {
        "nakshatra":       NAKSHATRAS[nak_idx],
        "pada":            pada,
        "sign":            SIGNS[sign_idx % 12],
        "degree_in_sign":  deg_in,
        "dasha_lord":      NAK_TO_DASHA_LORD[NAKSHATRAS[nak_idx]],
    }

def get_dignity(planet: str, sign: str) -> str:
    """Dignity label: exalted / moolatrikona / own / friendly / neutral / enemy / debilitated."""
    if planet not in DIGNITY_TABLE or sign not in SIGNS:
        return "unknown"
    d = DIGNITY_TABLE[planet]
    if sign == d["exalted"]:       return "exalted"
    if sign == d["debilitated"]:   return "debilitated"
    if sign == d.get("moolatrikona") and sign in d["own"]: return "moolatrikona"
    if sign in d["own"]:           return "own_sign"
    if sign in FRIENDS.get(planet, []): return "friendly_sign"
    if sign in ENEMIES.get(planet, []): return "enemy_sign"
    return "neutral_sign"

def get_functional_status(planet: str, lagna: str) -> str:
    if lagna not in FUNCTIONAL: return "unknown"
    f = FUNCTIONAL[lagna]
    if planet in f["yogakaraka"]: return "yogakaraka"
    if planet in f["benefic"]:    return "functional_benefic"
    if planet in f["malefic"]:    return "functional_malefic"
    if planet in f["maraka"]:     return "maraka"
    return "neutral"

def check_neecha_bhanga(planet: str, planet_sign: str, all_planets: dict, lagna_sign: str) -> dict:
    """Check if Neecha Bhanga applies. Returns full analysis."""
    dignity = get_dignity(planet, planet_sign)
    if dignity != "debilitated":
        return {"applicable": False, "planet_dignity": dignity}

    lagna_idx = sign_index(lagna_sign)
    kendra_signs = {SIGNS[(lagna_idx + h) % 12] for h in [0,3,6,9]}

    cancelling = None
    for p, d in DIGNITY_TABLE.items():
        if d["exalted"] == planet_sign:
            cancelling = p; break

    rules_fired = []

    # Rule 1: planet exalting in debil sign is in kendra from lagna
    if cancelling and cancelling in all_planets:
        cs = all_planets[cancelling].get("sign","")
        if cs in kendra_signs:
            h = house_from_lagna(cs, lagna_sign)
            rules_fired.append(f"Rule 1: {cancelling} (exalts in {planet_sign}) is in {cs} — house {h} (kendra) from lagna")

    # Rule 2: lord of debil sign is in kendra from lagna
    debil_lord = SIGN_LORDS.get(planet_sign,"")
    if debil_lord and debil_lord in all_planets:
        ds = all_planets[debil_lord].get("sign","")
        if ds in kendra_signs:
            h = house_from_lagna(ds, lagna_sign)
            rules_fired.append(f"Rule 2: {debil_lord} (lord of {planet_sign}) is in {ds} — house {h} (kendra) from lagna")

    # Rule 3: debil planet in own/exalted in navamsha
    nav = all_planets.get(planet,{}).get("navamsha_sign","")
    if nav and (nav == DIGNITY_TABLE[planet]["exalted"] or nav in DIGNITY_TABLE[planet]["own"]):
        rules_fired.append(f"Rule 3: {planet} is in {nav} in navamsha (own/exalted)")

    # Rule 4: lord of debil sign or exalting planet aspects the debil planet's sign
    # (simplified — not computed here, note for LLM to verify)

    present = len(rules_fired) > 0
    return {
        "applicable": True,
        "planet": planet,
        "planet_sign": planet_sign,
        "dignity": "debilitated",
        "neecha_bhanga_present": present,
        "cancelling_planet": cancelling,
        "rules_fired": rules_fired,
        "verdict": "Neecha Bhanga Raja Yoga active" if present else f"Debility stands — {planet} weakened in {planet_sign}",
        "llm_note": (
            f"USE THIS: {planet} is debilitated in {planet_sign}. "
            + (f"BUT Neecha Bhanga fires via {'; '.join(rules_fired)}. "
               "This converts debility into a raja yoga — explain as 'delayed but achieved strength, "
               "especially during {planet}'s dasha or when the cancelling planet is activated.'"
               if present else
               f"No cancellation found. Explain debility impact: {planet} struggles to deliver its significations "
               f"fully. Career/health/personality themes related to {planet}'s house and sign are harder won.")
        )
    }

def _format_dispositor_step(step: dict) -> str:
    if step.get("note"):
        return f"{step['planet']} in {step.get('sign', '?')} ({step.get('note')})"
    return f"{step['planet']} in {step['sign']} ({step['dignity']})"


def get_dispositor_chain(planet: str, all_planets: dict, lagna_sign: str, depth: int = 5) -> list:
    """Trace dispositor chain from a planet."""
    chain = []; visited = set(); current = planet
    for _ in range(depth):
        if current in visited:
            data = all_planets.get(current, {})
            sign = data.get("sign", "unknown")
            chain.append({
                "planet": current,
                "sign": sign,
                "house": house_from_lagna(sign, lagna_sign) if sign in SIGNS else "?",
                "dignity": get_dignity(current, sign) if sign in SIGNS else "unknown",
                "note": "MUTUAL RECEPTION / LOOP — chain ends here",
            })
            break
        visited.add(current)
        data  = all_planets.get(current, {})
        sign  = data.get("sign", "unknown")
        lord  = SIGN_LORDS.get(sign, "unknown")
        hnum  = house_from_lagna(sign, lagna_sign) if sign in SIGNS else "?"
        chain.append({
            "planet":   current,
            "sign":     sign,
            "house":    hnum,
            "dignity":  get_dignity(current, sign),
            "dispositor": lord,
        })
        if lord == current or lord == "unknown" or lord not in all_planets:
            break
        current = lord
    return chain

def check_mrityu_bhaga(planets: dict) -> list:
    """Check each planet's proximity to its Mrityu Bhaga degree."""
    results = []
    for planet, data in planets.items():
        if planet not in MRITYU_BHAGA: continue
        sign = data.get("sign","")
        deg  = data.get("degree_in_sign", 0)
        if sign not in SIGNS: continue
        mb   = MRITYU_BHAGA[planet][sign_index(sign)]
        diff = round(abs(deg - mb), 2)
        critical = diff <= 2.0
        results.append({
            "planet":  planet, "sign": sign,
            "natal_degree": round(deg, 2),
            "mrityu_bhaga_degree": mb,
            "difference_degrees": diff,
            "critical": critical,
            "status": "⚠ CRITICAL — within 2° of Mrityu Bhaga" if critical else "safe",
            "llm_note": (
                f"{planet} at {deg:.1f}° {sign}: Mrityu Bhaga = {mb}°, diff = {diff}°. "
                + ("USE: Flag this planet as operating at a sensitive degree — its dasha/transit periods "
                   "need extra care for the life domain it rules. Do NOT omit this in longevity section."
                   if critical else "Safe — mention only briefly in longevity report.")
            )
        })
    return sorted(results, key=lambda x: x["difference_degrees"])

# ══════════════════════════════════════════════════════════════════
#  DASHA CALCULATIONS
# ══════════════════════════════════════════════════════════════════

def parse_date(s: str) -> Optional[date]:
    """Parse various date formats from AstroSage extract."""
    formats = ["%b %d, %Y", "%d %b %Y", "%Y-%m-%d", "%b %Y", "%m/%d/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except: pass
    return None

# Import datetime for parse_date
from datetime import datetime

def parse_vimshottari_from_text(text: str, dob: date) -> dict:
    """
    Parse the Vimshottari dasha table from AstroSage extracted text.
    Returns structured MD/AD timeline.
    """
    today = date.today()
    mds = []

    # Strategy 1: look for the compact AstroSage table format
    # "MON -10 Years    MAR -7 Years    RAH -18 Years"  (MD headers)
    # followed by date rows for each MD
    # Then sub-tables for ADs

    # Strategy 2: look for date ranges "Mar 08, 1985 - Mar 07, 1992"
    date_range_re = re.compile(
        r'(Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)[^\n]*?\n'
        r'[^\n]*?(\w+ \d{1,2}, \d{4})\s*[-–]\s*(\w+ \d{1,2}, \d{4})',
        re.IGNORECASE
    )

    # Strategy 3: find the printed dasha table rows
    # Format varies: look for lines with planet + year count + date
    md_re = re.compile(
        r'\b(MON|MAR|RAH|JUP|SAT|MER|VEN|SUN|KET)\s*[-:]?\s*(\d+)\s*Years?',
        re.IGNORECASE
    )
    ABBR_TO_PLANET = {"MON":"Moon","MAR":"Mars","RAH":"Rahu","JUP":"Jupiter",
                      "SAT":"Saturn","MER":"Mercury","VEN":"Venus","SUN":"Sun","KET":"Ketu"}

    # Find all MD line items  
    inline_dates = re.findall(
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),\s+(\d{4})',
        text
    )

    # Convert inline dates to date objects
    parsed_dates = []
    for m, d_num, yr in inline_dates:
        try:
            parsed_dates.append(datetime.strptime(f"{m} {d_num} {yr}", "%b %d %Y").date())
        except: pass

    # Find MD sequence from text (look for the headers line)
    # Typical: "MON -10 Years   MAR -7 Years   RAH -18 Years"
    md_header_re = re.compile(
        r'(?:MON|MAR|RAH|JUP|SAT|MER|VEN|SUN|KET)\s*-\s*\d+\s*Years',
        re.IGNORECASE
    )
    headers_found = md_header_re.findall(text)

    # Build MD sequence from Moon nakshatra if we can find it
    # (fallback: use dob + Moon nakshatra from planets section)
    return {
        "parsed_dates_count": len(parsed_dates),
        "md_headers_found": headers_found[:20],
        "note": "LLM must read the printed dasha table directly from the extract — dates are pre-verified below",
        "raw_dates": [str(d) for d in sorted(set(parsed_dates))[:60]],
    }

def build_vimshottari_from_moon(moon_nakshatra: str, moon_deg_in_nak: float, dob: date) -> dict:
    """
    Calculate full Vimshottari dasha sequence from Moon nakshatra and balance.
    moon_deg_in_nak: Moon's degree within its nakshatra (0 to NAK_SPAN).
    """
    moon_nakshatra = normalize_nakshatra(moon_nakshatra)
    if moon_nakshatra not in NAKSHATRAS:
        return {"error": f"Unknown nakshatra: {moon_nakshatra}"}

    start_lord   = NAK_TO_DASHA_LORD[moon_nakshatra]
    start_idx    = VIMSH_LORDS.index(start_lord)
    total_years  = VIMSH_YEARS[start_lord]

    # Balance of first dasha at birth
    fraction_used   = moon_deg_in_nak / NAK_SPAN  # 0..1
    balance_years   = total_years * (1 - fraction_used)
    balance_days    = int(balance_years * 365.25)

    mds = []
    current = dob
    for i in range(9):
        idx   = (start_idx + i) % 9
        lord  = VIMSH_LORDS[idx]
        yrs   = VIMSH_YEARS[lord]
        if i == 0:
            yrs_actual = balance_years
        else:
            yrs_actual = yrs
        days = int(yrs_actual * 365.25)
        end  = current + timedelta(days=days)
        mds.append({
            "md_lord":   lord,
            "md_years":  round(yrs_actual, 2),
            "start":     str(current),
            "end":       str(end),
            "status":    "past" if end < date.today() else ("current" if current <= date.today() <= end else "future")
        })
        current = end

    # Find current MD
    today = date.today()
    current_md = next((m for m in mds if m["start"] <= str(today) <= m["end"]), mds[-1])

    # Build AD for current MD
    ads = build_antardashas(current_md, VIMSH_LORDS.index(current_md["md_lord"]))

    return {
        "sequence":   mds,
        "current_md": current_md,
        "current_md_antardashas": ads,
        "llm_note_md": (
            f"USE THIS VERIFIED DASHA TABLE. Current MD = {current_md['md_lord']} "
            f"({current_md['start']} to {current_md['end']}). "
            "For each MD in the sequence: apply 7-step analysis from vedic_vimshottari_skill.md. "
            "Steps are: (1) dignity in D1, (2) house owned/occupied, (3) conjunctions/aspects, "
            "(4) nakshatra lord, (5) dispositor, (6) from Chandra lagna, (7) cross-lagna verdict."
        ),
        "llm_note_ad": (
            f"Current Antardasha table pre-computed below. "
            "For each AD: state lord's house ownerships, mutual relationship with MD lord "
            "(friend/enemy/neutral), and specific life domain activated."
        )
    }

def build_antardashas(md: dict, md_idx: int) -> list:
    """Build AD sub-periods within a MD."""
    md_start = date.fromisoformat(md["start"][:10])
    md_end = date.fromisoformat(md["end"][:10]) if md.get("end") else None
    md_years  = md["md_years"]
    ads = []
    current = md_start
    for i in range(9):
        ad_idx  = (md_idx + i) % 9
        ad_lord = VIMSH_LORDS[ad_idx]
        ad_yrs  = VIMSH_YEARS[ad_lord] * md_years / 120.0
        ad_days = int(ad_yrs * 365.25)
        ad_end  = current + timedelta(days=ad_days)
        if md_end and ad_end > md_end:
            ad_end = md_end
        today   = date.today()
        ads.append({
            "ad_lord": ad_lord,
            "start":   str(current),
            "end":     str(ad_end),
            "status":  "past" if ad_end < today else ("current" if current <= today <= ad_end else "future"),
            "ad_years": round(ad_yrs, 2),
        })
        current = ad_end
        if md_end and current >= md_end:
            break
    if ads and md_end:
        ads[-1]["end"] = str(md_end)
        last_end = date.fromisoformat(ads[-1]["end"][:10])
        last_start = date.fromisoformat(ads[-1]["start"][:10])
        ads[-1]["ad_years"] = round((last_end - last_start).days / 365.25, 2)
    return ads


def clip_antardashas_to_md(vim: dict) -> None:
    """Ensure antardasha end dates never exceed current mahadasha end (in-place)."""
    md = vim.get("current_md") or {}
    md_end_s = (md.get("end") or "")[:10]
    if not md_end_s:
        return
    md_end = date.fromisoformat(md_end_s)
    today = date.today()
    for a in vim.get("current_md_antardashas", []):
        end_s = (a.get("end") or "")[:10]
        if not end_s:
            continue
        end_d = date.fromisoformat(end_s)
        if end_d > md_end:
            a["end"] = md_end_s
            start_s = (a.get("start") or "")[:10]
            if start_s:
                a["ad_years"] = round((md_end - date.fromisoformat(start_s)).days / 365.25, 2)
        start_s = (a.get("start") or "")[:10]
        if start_s:
            start_d = date.fromisoformat(start_s)
            end_d = date.fromisoformat(a["end"][:10])
            a["status"] = "past" if end_d < today else ("current" if start_d <= today <= end_d else "future")

def compute_yogini(moon_nakshatra: str, moon_deg_in_nak: float, dob: date) -> dict:
    """
    Compute full Yogini dasha cycle.
    Yogini at birth determined by Moon nakshatra (groups of 3 nakshatras per Yogini).
    """
    moon_nakshatra = normalize_nakshatra(moon_nakshatra)
    if moon_nakshatra not in NAKSHATRAS:
        return {"error": f"Unknown nakshatra: {moon_nakshatra}"}

    nak_idx       = NAKSHATRAS.index(moon_nakshatra)
    yogini_idx    = nak_idx % 8  # which Yogini rules at birth
    yogini_years  = YOGINI_YEARS[yogini_idx]

    # Balance of first Yogini
    fraction_used   = moon_deg_in_nak / NAK_SPAN
    balance_years   = yogini_years * (1 - fraction_used)

    cycle = []
    current = dob
    today   = date.today()

    for pass_num in range(4):  # ~4 passes covers ~144 years
        for i in range(8):
            y_idx   = (yogini_idx + i) % 8
            name    = YOGINI_NAMES[y_idx]
            lord    = YOGINI_LORDS[y_idx]
            yrs     = YOGINI_YEARS[y_idx] if (pass_num > 0 or i > 0) else balance_years
            days    = int(yrs * 365.25)
            end     = current + timedelta(days=days)
            age_s   = (current - dob).days // 365
            age_e   = (end - dob).days // 365
            is_curr = current <= today <= end
            cycle.append({
                "yogini":  name,
                "lord":    lord,
                "years":   round(yrs, 2),
                "start":   str(current),
                "end":     str(end),
                "age":     f"{age_s}–{age_e}",
                "tone":    YOGINI_TONE[name],
                "status":  "current" if is_curr else ("past" if end < today else "future"),
            })
            current = end
            if current.year > dob.year + 90: break
        if current.year > dob.year + 90: break

    current_yogini = next((y for y in cycle if y["status"] == "current"), None)
    next_yogini    = next((y for y in cycle if y["status"] == "future"), None)

    return {
        "yogini_at_birth":    YOGINI_NAMES[yogini_idx],
        "yogini_lord_birth":  YOGINI_LORDS[yogini_idx],
        "moon_nakshatra":     moon_nakshatra,
        "full_cycle":         [y for y in cycle if int(y["age"].split("–")[0]) < 90],
        "current_yogini":     current_yogini,
        "next_yogini":        next_yogini,
        "llm_note": (
            f"USE THIS: Yogini at birth = {YOGINI_NAMES[yogini_idx]} (lord: {YOGINI_LORDS[yogini_idx]}). "
            f"Current Yogini = {current_yogini['yogini'] if current_yogini else 'N/A'} "
            f"({current_yogini['start'] if current_yogini else '?'} to "
            f"{current_yogini['end'] if current_yogini else '?'}), "
            f"tone = {current_yogini['tone'] if current_yogini else 'N/A'}. "
            "For each Yogini period: state the lord's natal sign/house and what domain it activates. "
            "Ulka (Saturn) and Sankata (Rahu) = health/stress watchpoints. "
            "Cross-check with running Vimshottari period for convergence."
        )
    }

def compute_rtvd(dob: date, lagna_sign: str, planets: dict) -> dict:
    """
    Rasi Tulya Vatsara Dasa: each year of life activates a house counted from lagna.
    Year 1 = house 1, Year 2 = house 2 ... Year 13 = house 1 (cycle of 12).
    """
    today = date.today()
    current_age = (today - dob).days // 365
    rows = []

    for age in range(0, min(75, current_age + 12)):
        house_num  = (age % 12) + 1
        h_sign     = house_sign(house_num, lagna_sign)
        yr_lord    = SIGN_LORDS[h_sign]
        lord_data  = planets.get(yr_lord, {})
        lord_sign  = lord_data.get("sign","?")
        lord_house = lord_data.get("house","?")
        lord_dig   = get_dignity(yr_lord, lord_sign)
        yr_start   = date(dob.year + age, dob.month, dob.day)
        yr_end     = date(dob.year + age + 1, dob.month, dob.day)
        status     = "past" if yr_end < today else ("current" if yr_start <= today < yr_end else "future")

        rows.append({
            "age":             age,
            "calendar_year":   yr_start.year,
            "house_active":    house_num,
            "house_sign":      h_sign,
            "year_lord":       yr_lord,
            "year_lord_sign":  lord_sign,
            "year_lord_house": lord_house,
            "year_lord_dignity": lord_dig,
            "start":           str(yr_start),
            "end":             str(yr_end),
            "status":          status,
        })

    current_row = next((r for r in rows if r["status"] == "current"), None)

    return {
        "table": rows,
        "current_year": current_row,
        "llm_note": (
            "USE THIS RTVD TABLE. For each row: state house_active, its natural domain, "
            "year_lord's natal dignity and house. "
            f"Current year: age {current_row['age']}, house {current_row['house_active']} "
            f"({current_row['house_sign']}) active, year lord = {current_row['year_lord']} "
            f"in {current_row['year_lord_sign']} (house {current_row['year_lord_house']}), "
            f"dignity = {current_row['year_lord_dignity']}. "
            "State specific prediction for current year based on house domain + lord strength. "
            "For each future year: same format — name the year lord explicitly, do not say 'this lord'."
        ) if current_row else "Current year row not found — check DOB."
    }

def compute_longevity(planets: dict, lagna_sign: str, vimsh_mds: list) -> dict:
    """Compute longevity analysis: maraka lords, Mrityu Bhaga, maraka activation periods."""
    # Maraka lords
    h2_sign = house_sign(2, lagna_sign)
    h7_sign = house_sign(7, lagna_sign)
    m1 = SIGN_LORDS[h2_sign]
    m2 = SIGN_LORDS[h7_sign]
    h8_sign = house_sign(8, lagna_sign)
    h8_lord = SIGN_LORDS[h8_sign]

    # Maraka activation periods (MD or AD involving maraka lords)
    maraka_periods = []
    for md in vimsh_mds:
        if md["md_lord"] in [m1, m2]:
            maraka_periods.append({
                "type": "MD",
                "lord": md["md_lord"],
                "start": md["start"], "end": md["end"],
                "status": md["status"],
                "note": f"Full {md['md_years']:.1f}-year MD of maraka {md['md_lord']}"
            })

    # 8th lord strength (protects longevity if strong)
    h8_lord_sign = planets.get(h8_lord, {}).get("sign","?")
    h8_dignity   = get_dignity(h8_lord, h8_lord_sign)

    # Jupiter as karaka for longevity
    jup_sign = planets.get("Jupiter",{}).get("sign","?")
    jup_house = planets.get("Jupiter",{}).get("house","?")
    jup_dignity = get_dignity("Jupiter", jup_sign)

    mb = check_mrityu_bhaga(planets)
    critical_mb = [x for x in mb if x["critical"]]

    # Longevity span (simplified Parashari method)
    # Short < 32, Medium 32-64, Long > 64
    # Based on lagna lord, 8th lord, Moon dignity
    ll = SIGN_LORDS[lagna_sign]
    ll_sign = planets.get(ll,{}).get("sign","?")
    ll_dig = get_dignity(ll, ll_sign)
    moon_sign = planets.get("Moon",{}).get("sign","?")
    moon_dig = get_dignity("Moon", moon_sign)

    strong = sum(1 for d in [ll_dig, h8_dignity, moon_dig] if d in ["exalted","moolatrikona","own_sign"])
    if strong >= 2:   span = "Long (64–100+ years)"
    elif strong == 1: span = "Medium (32–64 years)"
    else:             span = "Short–Medium (32–64 years, review carefully)"

    return {
        "maraka_1": {"house":2, "sign":h2_sign, "lord":m1,
                     "lord_sign":planets.get(m1,{}).get("sign","?"),
                     "lord_house":planets.get(m1,{}).get("house","?"),
                     "lord_dignity":get_dignity(m1, planets.get(m1,{}).get("sign","?"))},
        "maraka_2": {"house":7, "sign":h7_sign, "lord":m2,
                     "lord_sign":planets.get(m2,{}).get("sign","?"),
                     "lord_house":planets.get(m2,{}).get("house","?"),
                     "lord_dignity":get_dignity(m2, planets.get(m2,{}).get("sign","?"))},
        "house_8_lord": h8_lord,
        "house_8_lord_sign": h8_lord_sign,
        "house_8_dignity": h8_dignity,
        "jupiter_sign": jup_sign, "jupiter_house": jup_house, "jupiter_dignity": jup_dignity,
        "mrityu_bhaga_all":  mb,
        "critical_mb":       critical_mb,
        "maraka_md_periods": maraka_periods,
        "longevity_span_estimate": span,
        "llm_note": (
            f"USE THIS: Maraka 1 = {m1} (2nd lord, in {planets.get(m1,{}).get('sign','?')}, "
            f"house {planets.get(m1,{}).get('house','?')}, dignity={get_dignity(m1,planets.get(m1,{}).get('sign','?'))}). "
            f"Maraka 2 = {m2} (7th lord, in {planets.get(m2,{}).get('sign','?')}, "
            f"house {planets.get(m2,{}).get('house','?')}, dignity={get_dignity(m2,planets.get(m2,{}).get('sign','?'))}). "
            f"8th lord = {h8_lord} in {h8_lord_sign}, dignity={h8_dignity} "
            f"({'protects longevity' if h8_dignity in ['exalted','moolatrikona','own_sign'] else 'neutral/weak 8th lord — more vulnerability'}). "
            + (f"CRITICAL Mrityu Bhaga planets: {', '.join(p['planet']+' at '+str(p['natal_degree'])+'° '+p['sign'] for p in critical_mb)}. " if critical_mb else "No planets at critical Mrityu Bhaga degrees. ")
            + f"Estimated span: {span}. "
            "Write maraka table in report with all these values. Identify upcoming maraka MD/AD periods."
        )
    }

def compute_cara_karakas(planets: dict) -> list:
    """
    Jaimini Cara Karakas — assign by planet degree within sign (descending).
    Excludes Rahu, Ketu, outer planets.
    """
    eligible = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"]
    roles    = ["Atmakarak","Amatyakarak","Bhratrukaraka","Matrukaraka",
                "Putrakaraka","Gnatikaraka","Darakaraka"]

    ranked = sorted(
        [(p, planets[p].get("degree_in_sign",0)) for p in eligible if p in planets],
        key=lambda x: x[1], reverse=True
    )

    karakas = []
    for i, (planet, deg) in enumerate(ranked):
        if i >= len(roles): break
        pdata = planets[planet]
        karakas.append({
            "role":      roles[i],
            "planet":    planet,
            "degree":    round(deg, 2),
            "sign":      pdata.get("sign","?"),
            "house":     pdata.get("house","?"),
            "dignity":   get_dignity(planet, pdata.get("sign","?")),
            "nakshatra": pdata.get("nakshatra","?"),
        })

    atm = next((k for k in karakas if k["role"]=="Atmakarak"), None)
    amt = next((k for k in karakas if k["role"]=="Amatyakarak"), None)
    dar = next((k for k in karakas if k["role"]=="Darakaraka"), None)

    note = "USE THIS CARA KARAKA TABLE:\n"
    if atm: note += (f"  Atmakarak = {atm['planet']} at {atm['degree']}° {atm['sign']} "
                     f"(house {atm['house']}, {atm['dignity']}) — "
                     "soul purpose, primary life driver. Its navamsha sign = Karakamsha (find in D9 block).\n")
    if amt: note += (f"  Amatyakarak = {amt['planet']} at {amt['degree']}° {amt['sign']} "
                     f"(house {amt['house']}, {amt['dignity']}) — career/profession director.\n")
    if dar: note += (f"  Darakaraka = {dar['planet']} at {dar['degree']}° {dar['sign']} "
                     f"(house {dar['house']}) — spouse karaka.\n")
    note += "Apply sign aspects (not house aspects) for Jaimini. Argala from the Karakamsha sign."

    return {"karakas": karakas, "llm_note": note}


def navamsa_sign(sign: str, deg_in_sign: float) -> str:
    """Whole-sign navamsha from D1 longitude (fallback when D9 block missing)."""
    if sign not in SIGNS:
        return "?"
    lon = SIGNS.index(sign) * 30.0 + float(deg_in_sign)
    return SIGNS[int(lon / (30.0 / 9.0)) % 12]


def d9_sign(pc: dict, planet: str) -> str | None:
    """Navamsha sign from PyJHora D9 block, else compute from D1."""
    d9 = pc.get("divisional") or {}.get("D9", {})
    if planet in d9 and d9[planet] in SIGNS:
        return d9[planet]
    pl = pc.get("planets") or {}.get(planet, {})
    if pl.get("sign") in SIGNS:
        return navamsa_sign(pl["sign"], pl.get("degree_in_sign", 0.0))
    return pl.get("navamsha_sign") or None


def build_jaimini_block(
    planets: dict,
    lagna_sign: str,
    cara_karakas_block: dict,
    divisional: dict | None = None,
    chara_dasha: dict | None = None,
) -> dict:
    """
    AstroSage-aligned Jaimini facts from precomputed chart.
    Chara karakas: degree-within-sign among Sun-Saturn (see compute_cara_karakas).
    Karakamsa / Swamsa: D9 sign of Atmakaraka and lagna lord.
    """
    divisional = divisional or {}
    d9 = divisional.get("D9", {})
    lagna_lord = SIGN_LORDS.get(lagna_sign, "")
    ak_entry = next(
        (k for k in cara_karakas_block.get("karakas", []) if k.get("role") == "Atmakarak"),
        {},
    )
    akp = ak_entry.get("planet")
    karakamsa = d9.get(akp) if akp else None
    swamsa = d9.get(lagna_lord) if lagna_lord else None
    if not karakamsa and akp:
        karakamsa = d9_sign({"planets": planets, "divisional": divisional}, akp)
    if not swamsa and lagna_lord:
        swamsa = d9_sign({"planets": planets, "divisional": divisional}, lagna_lord)

    karaka_table = []
    for k in cara_karakas_block.get("karakas", []):
        p = k.get("planet")
        karaka_table.append({
            **k,
            "navamsha_sign": d9.get(p) or (d9_sign({"planets": planets, "divisional": divisional}, p) if p else None),
        })

    return {
        "method": "astrosage_chara_degree_in_sign",
        "atmakaraka": akp,
        "karakamsa_sign": karakamsa,
        "swamsa_sign": swamsa,
        "lagna_lord": lagna_lord,
        "d9_lagna": d9.get("Lagna"),
        "karakas": karaka_table,
        "chara_dasha": chara_dasha or {},
        "llm_note": cara_karakas_block.get("llm_note", ""),
    }


def compute_numerology(name: str, dob: date) -> dict:
    """All core numerology numbers (Chaldean system)."""
    def ch_val(text):
        return sum(CHALDEAN.get(c.upper(),0) for c in text if c.isalpha())
    def reduce_num(n):
        while n > 9 and n not in [11,22,33]:
            n = sum(int(d) for d in str(n))
        return n

    life_path  = reduce_num(sum(int(d) for d in str(dob).replace("-","") if d.isdigit()))
    expression = reduce_num(ch_val(name))
    vowels     = ''.join(c for c in name if c.upper() in 'AEIOU')
    consonants = ''.join(c for c in name if c.isalpha() and c.upper() not in 'AEIOU')
    soul_urge  = reduce_num(ch_val(vowels))
    personality= reduce_num(ch_val(consonants))
    birth_day  = reduce_num(dob.day)
    chaldean_name_total = ch_val(name)

    # Lo Shu grid
    dob_digits = [int(d) for d in f"{dob.day:02d}{dob.month:02d}{dob.year}" if d.isdigit() and d!='0']
    digit_freq = Counter(dob_digits)
    missing    = [d for d in range(1,10) if d not in digit_freq]

    # Numerology Maha Dasha (9-year cycle, repeating)
    # Starting from birth year, Lord based on Life Path
    lp_lord_map = {1:"Sun",2:"Moon",3:"Jupiter",4:"Rahu",5:"Mercury",
                   6:"Venus",7:"Ketu",8:"Saturn",9:"Mars",
                   11:"Moon",22:"Saturn",33:"Jupiter"}
    md_lords_9  = ["Sun","Moon","Mars","Rahu","Mercury","Jupiter","Venus","Saturn","Ketu"]
    md_years_9  = [6,10,7,18,17,16,20,19,7]
    start_lord  = lp_lord_map.get(life_path,"Sun")
    s_idx       = md_lords_9.index(start_lord) if start_lord in md_lords_9 else 0
    maha_seq    = []
    yr = dob.year
    for i in range(9):
        idx = (s_idx + i) % 9
        l   = md_lords_9[idx]; y = md_years_9[idx]
        maha_seq.append({"lord":l,"years":y,"start_year":yr,"end_year":yr+y})
        yr += y

    # Harmony check
    birth_num  = reduce_num(dob.day)
    name_num   = reduce_num(chaldean_name_total)
    harmony    = "compatible" if birth_num == name_num else (
        "discordant — name change may help" if abs(birth_num - name_num) > 3 else "mildly compatible"
    )

    return {
        "life_path":     life_path,
        "expression":    expression,
        "soul_urge":     soul_urge,
        "personality":   personality,
        "birth_day":     birth_day,
        "chaldean_name_total": chaldean_name_total,
        "lo_shu": {"digits_present": dict(digit_freq), "missing_numbers": missing},
        "maha_dasha":    maha_seq,
        "name_harmony":  harmony,
        "llm_note": (
            f"USE THESE CALCULATED VALUES:\n"
            f"  Life Path = {life_path} | Expression = {expression} | "
            f"Soul Urge = {soul_urge} | Personality = {personality} | Birth Day = {birth_day}\n"
            f"  Chaldean Name Total = {chaldean_name_total} (reduced: {expression})\n"
            f"  Lo Shu missing numbers: {missing if missing else 'none'} "
            f"— these life areas need conscious effort.\n"
            f"  Name-Birth harmony: {harmony}\n"
            "Show the letter-by-letter Chaldean table in the report. "
            "Use Maha Dasha table above for timeline. "
            "Missing numbers: interpret each missing number's domain (e.g. missing 6 = family/home struggles)."
        )
    }

# ══════════════════════════════════════════════════════════════════
#  EXTRACT PARSER
# ══════════════════════════════════════════════════════════════════

def parse_extract(text: str) -> dict:
    """Parse VedicReport extracted text → structured planet data."""
    result = {"lagna": {}, "planets": {}, "raw_sections": {}}
    PLANET_NAMES = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]

    # ── Lagna ──
    # AstroSage format: "ASC   Gemini   21-23-02   Punarvasu   1"
    # Also: "Lagna   Gemini"  or  "Your Ascendant is: Gemini"
    lagna_patterns = [
        # Primary: ASC row with degree + nakshatra + pada
        (r'ASC\s+([A-Z][a-z]+)\s+(\d{1,2})[-:](\d{1,2})[-:](\d{1,2})\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(\d)', 6),
        (r'ASC\s+([A-Z][a-z]+)\s+(\d{1,2})[-:](\d{1,2})[-:](\d{1,2})', 4),
        (r'ASC\s+([A-Z][a-z]+)\s+(\d{1,2})[-:](\d{1,2})', 3),
        # Fallback: Lagna row
        (r'^\s*Lagna\s+([A-Z][a-z]+)\s*$', 1),
        (r'Your Ascendant is:\s*([A-Z][a-z]+)', 1),
        (r'Ascendant[^\n]*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(\d{1,2})[°d\s:\-]+(\d{1,2})', 3),
    ]
    for pat, ngroups in lagna_patterns:
        m = re.search(pat, text, re.MULTILINE)
        if m:
            raw_sign = m.group(1).strip()
            sign = SIGN_ABBR.get(raw_sign, raw_sign)
            if sign in SIGNS:
                deg = 0.0
                if ngroups >= 4:
                    try:
                        deg = int(m.group(2)) + int(m.group(3)) / 60 + (int(m.group(4)) / 3600 if ngroups >= 4 else 0)
                    except ValueError:
                        pass
                elif ngroups >= 3:
                    try:
                        deg = int(m.group(2)) + int(m.group(3)) / 60
                    except ValueError:
                        pass
                entry = {"sign": sign, "degree_in_sign": round(deg, 4)}
                if ngroups >= 6:
                    entry["nakshatra"] = normalize_nakshatra(m.group(5).strip())
                    try:
                        entry["pada"] = int(m.group(6))
                    except ValueError:
                        pass
                result["lagna"] = entry
                break

    # ── Planet positions: parse from the tabular section ──
    # AstroSage format: "Merc   Pisces   08-40-57   Uttarabhadra   2"
    # or full:          "Sun    Aquarius  24-02-25   Purvabhadra    2   Virgo"
    PLANET_ABBR = {
        "Sun":"Sun","Merc":"Mercury","Mercury":"Mercury","Moon":"Moon","Mon":"Moon",
        "Mars":"Mars","Mar":"Mars","Jupt":"Jupiter","Jupiter":"Jupiter","Jup":"Jupiter",
        "Venu":"Venus","Venus":"Venus","Ven":"Venus","Satn":"Saturn","Saturn":"Saturn","Sat":"Saturn",
        "Rahu":"Rahu","Rah":"Rahu","Ketu":"Ketu","Ket":"Ketu",
    }
    SIGN_ALT = {"Scorpion":"Scorpio","Capricorne":"Capricorn"}
    # Pattern 1: "Merc   Pisces   08-40-57   Uttarabhadra   2"  (sign name + degree)
    tab1_re = re.compile(
        r'\b(Sun|Merc|Mercury|Moon|Mon|Mars|Mar|Jupt|Jupiter|Jup|Venu|Venus|Ven|'
        r'Satn|Saturn|Sat|Rahu|Rah|Ketu|Ket)(?:\s*\[R\])?\s+'
        r'([A-Z][a-z]+(?:ion)?)\s+'
        r'(\d{1,2})[-:](\d{1,2})[-:](\d{1,2})\s+'
        r'([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(\d)',
    )
    for m in tab1_re.finditer(text):
        abbr    = m.group(1)
        planet  = PLANET_ABBR.get(abbr, abbr)
        if planet in result["planets"]: continue
        sign_raw= m.group(2).strip()
        sign    = SIGN_ALT.get(sign_raw, SIGN_ABBR.get(sign_raw, sign_raw))
        if sign not in SIGNS: continue
        deg     = round(int(m.group(3)) + int(m.group(4))/60 + int(m.group(5))/3600, 4)
        nak_raw = m.group(6).strip()
        pada    = int(m.group(7))
        result["planets"][planet] = {"sign":sign, "degree_in_sign":deg, "nakshatra":normalize_nakshatra(nak_raw), "pada":pada}

    # Pattern 2: "Mercury   338-46-20   ..." (absolute degree, no sign name)
    tab2_re = re.compile(
        r'\b(Sun|Mercury|Moon|Mars|Jupiter|Venus|Saturn|Rahu|Ketu)\s+'
        r'(\d{3})[-:](\d{2})[-:](\d{2})'
    )
    for m in tab2_re.finditer(text):
        planet = m.group(1)
        if planet in result["planets"]: continue
        deg_abs = int(m.group(2)) + int(m.group(3))/60 + int(m.group(4))/3600
        sign    = SIGNS[int(deg_abs / 30) % 12]
        deg     = round(deg_abs % 30, 4)
        result["planets"][planet] = {"sign":sign, "degree_in_sign":deg}

    # ── Planet positions fallback (simpler regex) ──
    planet_re = re.compile(
        r'\b(Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\b'
        r'[^\S\n]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        r'[^\S\n]+(\d{1,2})[-:\- ]+(\d{1,2})',
        re.MULTILINE
    )
    for m in planet_re.finditer(text):
        planet = m.group(1)
        if planet in result["planets"]: continue  # already parsed from table
        raw_sign = m.group(2).strip()
        sign = SIGN_ABBR.get(raw_sign, raw_sign)
        if sign not in SIGNS: continue
        deg = int(m.group(3)) + int(m.group(4))/60
        result["planets"][planet] = {"sign": sign, "degree_in_sign": round(deg,4)}

    # ── Nakshatra from text (more reliable than computing from degree) ──
    for planet in PLANET_NAMES:
        # Try to find "Mercury  Pisces  8:41  10  Uttarabhada  2  Capricorn"
        nak_re = re.compile(
            rf'\b{planet}\b[^\n]{{0,80}}('+'|'.join(NAKSHATRAS)+r')',
            re.IGNORECASE
        )
        m = nak_re.search(text)
        if m and planet in result["planets"]:
            result["planets"][planet]["nakshatra"] = normalize_nakshatra(m.group(1))

    # ── Navamsha signs ──
    # Look for D9 block
    d9_section = re.search(r'D\s*[-/]?\s*9|Navamsha|Navamsa', text, re.IGNORECASE)
    if d9_section:
        d9_text = text[d9_section.start():d9_section.start()+3000]
        for planet in PLANET_NAMES:
            nav_re = re.compile(rf'\b{planet}\b[^\n]{{0,60}}([A-Z][a-z]+)', re.IGNORECASE)
            m = nav_re.search(d9_text)
            if m:
                raw = m.group(1).strip()
                nav_sign = SIGN_ABBR.get(raw, raw)
                if nav_sign in SIGNS and planet in result["planets"]:
                    result["planets"][planet]["navamsha_sign"] = nav_sign

    # ── House numbers (from text) ──
    for planet in PLANET_NAMES:
        if planet not in result["planets"]: continue
        house_re = re.compile(
            rf'\b{planet}\b[^\n]{{0,120}}?(\d{{1,2}})\s*(?:th|st|nd|rd)?\s*(?:house|H\b)',
            re.IGNORECASE
        )
        m = house_re.search(text)
        if m:
            h = int(m.group(1))
            if 1 <= h <= 12:
                result["planets"][planet]["house"] = h

    # ── Compute house from lagna if not found ──
    lagna_sign = result["lagna"].get("sign","")
    if lagna_sign:
        for planet, data in result["planets"].items():
            if "house" not in data and "sign" in data:
                data["house"] = house_from_lagna(data["sign"], lagna_sign)

    # ── Moon nakshatra and degree-in-nakshatra (critical for Yogini + Vimshottari) ──
    moon_data = result["planets"].get("Moon", {})
    moon_sign = moon_data.get("sign","")
    moon_deg_in_sign = moon_data.get("degree_in_sign", 0)
    if moon_sign in SIGNS:
        # Compute absolute degree
        abs_deg = sign_index(moon_sign) * 30 + moon_deg_in_sign
        nak_info = degree_to_nakshatra(abs_deg)
        if "nakshatra" not in moon_data:
            moon_data["nakshatra"] = nak_info["nakshatra"]
        moon_data["nakshatra_pada"] = nak_info["pada"]
        moon_data["degree_in_nakshatra"] = round(abs_deg % NAK_SPAN, 4)
        moon_data["dasha_lord_from_nak"] = nak_info["dasha_lord"]
        result["planets"]["Moon"] = moon_data

    # ── Lagna nakshatra ──
    lagna_deg_in_sign = result["lagna"].get("degree_in_sign", 0)
    if lagna_sign in SIGNS:
        abs_lagna = sign_index(lagna_sign) * 30 + lagna_deg_in_sign
        l_nak = degree_to_nakshatra(abs_lagna)
        result["lagna"]["nakshatra"] = l_nak["nakshatra"]
        result["lagna"]["pada"] = l_nak["pada"]

    # ── Ashtakavarga SAV (parse score table) ──
    sav_re = re.compile(
        r'(?:Sarv|Sarva)\s*[Aa]shtakavarga[^\n]*\n([\s\S]{50,500})',
        re.IGNORECASE
    )
    m = sav_re.search(text)
    if m:
        result["raw_sections"]["ashtakavarga_sav"] = m.group(1)[:500]

    # ── Raw Vimshottari section ──
    vd_re = re.search(r'Vimsh?ottari[^\n]*\n([\s\S]{100,2000})', text, re.IGNORECASE)
    if vd_re:
        result["raw_sections"]["vimshottari_raw"] = vd_re.group(1)[:2000]

    # ── Raw KP section ──
    kp_re = re.search(r'KP System[^\n]*\n([\s\S]{200,3000})', text, re.IGNORECASE)
    if kp_re:
        result["raw_sections"]["kp_block"] = kp_re.group(1)[:3000]

    # ── Raw Jaimini section ──
    jai_re = re.search(r'Jaimini[^\n]*\n([\s\S]{100,2000})', text, re.IGNORECASE)
    if jai_re:
        result["raw_sections"]["jaimini_block"] = jai_re.group(1)[:2000]

    return result


def _dms_to_decimal(deg: int, minute: int, second: int, hemisphere: str) -> float:
    val = deg + minute / 60.0 + second / 3600.0
    if hemisphere.upper() in ("S", "W"):
        val = -val
    return round(val, 6)


def parse_birth_meta(text: str) -> dict:
    """Parse birth clock, place, and coordinates from AstroSage Basic Details."""
    meta: dict = {}
    m = re.search(r"Time of Birth\s+(\d+)\s*[:.]\s*(\d+)\s*[:.]\s*(\d+)", text)
    if m:
        meta["birth_time"] = f"{int(m.group(1)):02d}:{int(m.group(2)):02d}:{int(m.group(3)):02d}"
    m = re.search(r"Place of Birth\s+([^\n]+)", text)
    if m:
        meta["birth_place"] = m.group(1).strip()
    m = re.search(r"Time Zone\s+([\d.]+)", text)
    if m:
        try:
            meta["timezone"] = float(m.group(1))
        except ValueError:
            pass
    m = re.search(r"Latitude\s+(\d+)\s*:\s*(\d+)\s*:\s*([NS])", text, re.IGNORECASE)
    if m:
        meta["latitude"] = _dms_to_decimal(int(m.group(1)), int(m.group(2)), 0, m.group(3))
    m = re.search(r"Longitude\s+(\d+)\s*:\s*(\d+)\s*:\s*([EW])", text, re.IGNORECASE)
    if m:
        meta["longitude"] = _dms_to_decimal(int(m.group(1)), int(m.group(2)), 0, m.group(3))
    m = re.search(r"Local Time Correction\s+([\d.]+)", text)
    if m:
        meta["lmt_correction"] = m.group(1).strip()
    m = re.search(r"Sex\s+(\w+)", text)
    if m:
        sex = m.group(1).strip().lower()
        meta["gender"] = 1 if sex.startswith("f") else 0
    return meta


def birth_meta_complete(meta: dict) -> bool:
    return all(
        meta.get(k) is not None
        for k in ("birth_time", "latitude", "longitude", "timezone")
    )


def compute_pillar(planets: dict, lagna: dict, lagna_sign: str) -> dict:
    """Pre-compute all Pillar of Life analysis facts."""
    lagna_lord = SIGN_LORDS.get(lagna_sign,"?")
    ll_data    = planets.get(lagna_lord, {})
    ll_sign    = ll_data.get("sign","?")
    ll_house   = ll_data.get("house","?")
    ll_dignity = get_dignity(lagna_lord, ll_sign)
    ll_nak     = ll_data.get("nakshatra","?")
    ll_nav     = ll_data.get("navamsha_sign","?")

    # 7-factor lagna checklist
    kendra_houses = {1,4,7,10}
    lagna_idx = sign_index(lagna_sign)
    kendra_signs = {SIGNS[(lagna_idx + h) % 12] for h in [0,3,6,9]}

    factors = []

    # 1. Lagna lord in lagna
    f1 = ll_house == 1 or ll_sign == lagna_sign
    factors.append({
        "factor": "Lagna lord in lagna",
        "result": "YES" if f1 else "NO",
        "detail": f"{lagna_lord} is in {ll_sign} (house {ll_house})" + (" — IN LAGNA ✓" if f1 else " — NOT in lagna")
    })

    # 2. Lagna lord aspects lagna
    # 7th aspect from ll_sign — does it fall on lagna_sign?
    ll_7th_sign = SIGNS[(sign_index(ll_sign) + 6) % 12]
    f2 = ll_7th_sign == lagna_sign
    # Mars 4th/8th, Jupiter 5th/9th, Saturn 3rd/10th special aspects
    extra_aspects = []
    if lagna_lord == "Mars":
        mars_4 = SIGNS[(sign_index(ll_sign) + 3) % 12]
        mars_8 = SIGNS[(sign_index(ll_sign) + 7) % 12]
        if mars_4 == lagna_sign: extra_aspects.append("4th aspect (Mars)")
        if mars_8 == lagna_sign: extra_aspects.append("8th aspect (Mars)")
    if lagna_lord == "Jupiter":
        jup_5 = SIGNS[(sign_index(ll_sign) + 4) % 12]
        jup_9 = SIGNS[(sign_index(ll_sign) + 8) % 12]
        if jup_5 == lagna_sign: extra_aspects.append("5th aspect (Jupiter)")
        if jup_9 == lagna_sign: extra_aspects.append("9th aspect (Jupiter)")
    if lagna_lord == "Saturn":
        sat_3 = SIGNS[(sign_index(ll_sign) + 2) % 12]
        sat_10 = SIGNS[(sign_index(ll_sign) + 9) % 12]
        if sat_3 == lagna_sign: extra_aspects.append("3rd aspect (Saturn)")
        if sat_10 == lagna_sign: extra_aspects.append("10th aspect (Saturn)")

    f2_any = f2 or len(extra_aspects) > 0
    factors.append({
        "factor": "Lagna lord aspects lagna",
        "result": "YES" if f2_any else "NO",
        "detail": (f"{lagna_lord} 7th aspect hits {ll_7th_sign}" +
                   (f" [={lagna_sign} ✓]" if f2 else f" [≠{lagna_sign}]")) +
                   (f"; Extra: {', '.join(extra_aspects)}" if extra_aspects else "")
    })

    # 3. Natural benefics in/aspecting lagna
    benefics = ["Jupiter","Venus","Moon","Mercury"]
    ben_in_lagna = [p for p in benefics if planets.get(p,{}).get("sign") == lagna_sign]
    ben_aspecting = []
    for p in benefics:
        ps = planets.get(p,{}).get("sign","")
        if ps and ps != lagna_sign:
            p7 = SIGNS[(sign_index(ps)+6)%12]
            if p7 == lagna_sign: ben_aspecting.append(f"{p} (7th from {ps})")
    factors.append({
        "factor": "Natural benefics in/aspecting lagna",
        "result": "YES" if (ben_in_lagna or ben_aspecting) else "NO",
        "detail": (f"In lagna: {ben_in_lagna}. Aspecting: {ben_aspecting}"
                   if (ben_in_lagna or ben_aspecting) else "No natural benefic in or aspecting lagna")
    })

    # 4. Natural malefics in/aspecting lagna
    malefics = ["Saturn","Mars","Sun","Rahu","Ketu"]
    mal_in = [p for p in malefics if planets.get(p,{}).get("sign") == lagna_sign]
    mal_asp = []
    for p in ["Saturn","Mars"]:
        ps = planets.get(p,{}).get("sign","")
        if ps:
            p7 = SIGNS[(sign_index(ps)+6)%12]
            if p7 == lagna_sign: mal_asp.append(f"{p} 7th from {ps}")
    factors.append({
        "factor": "Natural malefics afflicting lagna",
        "result": "YES (afflicted)" if (mal_in or mal_asp) else "NO (protected)",
        "detail": f"In lagna: {mal_in}. Aspecting: {mal_asp}" if (mal_in or mal_asp) else "Lagna clear of natural malefic influence"
    })

    # 5. Papa-Katari (malefics hemming lagna — 2nd and 12th both occupied by malefics)
    h2_sign  = house_sign(2, lagna_sign)
    h12_sign = house_sign(12, lagna_sign)
    mal_in_2  = [p for p in malefics if planets.get(p,{}).get("sign") == h2_sign]
    mal_in_12 = [p for p in malefics if planets.get(p,{}).get("sign") == h12_sign]
    papa_katari = bool(mal_in_2 and mal_in_12)
    factors.append({
        "factor": "Papa-Katari (malefic hemming on lagna)",
        "result": "YES (Papa-Katari present)" if papa_katari else "NO",
        "detail": f"2nd house ({h2_sign}): {mal_in_2 or 'clear'}. 12th house ({h12_sign}): {mal_in_12 or 'clear'}"
    })

    # 6. Vargottama lagna
    ll_nav_sign = lagna.get("navamsha_sign","?")  # need D9 lagna
    lagna_nav = planets.get("__lagna_navamsha__","")
    vargottama = False  # computed if D9 data available
    factors.append({
        "factor": "Vargottama lagna",
        "result": "VERIFY IN D9",
        "detail": f"D1 lagna = {lagna_sign}. Compare with D9 lagna sign in the extract."
    })

    # 7. Benefic yogas in lagna
    yogas_in_lagna = []
    if ben_in_lagna:
        yogas_in_lagna.append(f"Natural benefics in lagna: {ben_in_lagna}")
    factors.append({
        "factor": "Benefic yogas in lagna",
        "result": "YES" if yogas_in_lagna else "NO",
        "detail": "; ".join(yogas_in_lagna) or "No major benefic yoga directly in lagna"
    })

    # Neecha Bhanga for lagna lord
    nb = check_neecha_bhanga(lagna_lord, ll_sign, planets, lagna_sign)

    # Dispositor chain
    chain = get_dispositor_chain(lagna_lord, planets, lagna_sign)

    # Special yogas check
    yogas = []
    # Malefics in 3/6/11 (upachaya) from lagna
    for p in ["Mars","Saturn","Sun","Rahu"]:
        ps = planets.get(p,{}).get("sign","")
        if ps:
            ph = house_from_lagna(ps, lagna_sign)
            if ph in [3,6,11]:
                yogas.append(
                    f"{p} in the {ph}th house — a growth placement that builds "
                    f"competitive strength over time"
                )
    # Exalted planet in kendra
    for p, data in DIGNITY_TABLE.items():
        ps = planets.get(p,{}).get("sign","")
        if ps == data["exalted"]:
            ph = house_from_lagna(ps, lagna_sign)
            if ph in [1,4,7,10]:
                yogas.append(
                    f"{p} exalted in {ps} (house {ph}) — a classic power combination"
                )

    return {
        "lagna_lord":        lagna_lord,
        "lagna_lord_sign":   ll_sign,
        "lagna_lord_house":  ll_house,
        "lagna_lord_dignity": ll_dignity,
        "lagna_lord_nakshatra": ll_nak,
        "lagna_lord_navamsha_sign": ll_nav,
        "seven_factors":     factors,
        "neecha_bhanga":     nb,
        "dispositor_chain":  chain,
        "special_yogas":     yogas,
        "functional_status": {p: get_functional_status(p, lagna_sign) for p in
                              ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]},
        "llm_note": (
            f"USE THIS PILLAR DATA:\n"
            f"  Lagna = {lagna_sign} | Lagna Lord = {lagna_lord} | "
            f"LL in {ll_sign} (house {ll_house}) | Dignity = {ll_dignity}\n"
            f"  Nakshatra = {ll_nak} | Navamsha = {ll_nav}\n"
            + (f"  NEECHA BHANGA: {nb['verdict']}\n" if nb.get("applicable") else "")
            + f"  7-factor checklist pre-computed — use 'seven_factors' array above, "
            "write one table row per factor with the exact 'detail' text.\n"
            f"  Dispositor chain: {' → '.join(_format_dispositor_step(s) for s in chain)}\n"
            + (f"  Special yogas: {'; '.join(yogas)}\n" if yogas else "  No special yogas detected.\n")
        )
    }

# ══════════════════════════════════════════════════════════════════
#  MAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════

def get_house_lord(pc: dict, house: int) -> dict:
    """Return house-lord record; JSON caches may use string keys ('10') or int (10)."""
    hl = pc.get("house_lords") or {}
    return hl.get(house) or hl.get(str(house)) or {}


def normalize_precomputed(pc: dict) -> dict:
    """Coerce cached session JSON into the shape live precompute() returns."""
    hl = pc.get("house_lords")
    if hl and isinstance(next(iter(hl.keys())), str):
        pc["house_lords"] = {int(k): v for k, v in hl.items()}
    if pc.get("vimshottari"):
        clip_antardashas_to_md(pc["vimshottari"])
    from jaimini_chara_dasha import sync_chara_dasha_keys

    sync_chara_dasha_keys(pc)
    return pc


def precompute_from_chart(parsed: dict, client_name: str, dob_str: str, *, source: str = "chart") -> dict:
    """Build the standard precomputed JSON from an already-parsed chart dict."""
    dob = date.fromisoformat(dob_str)
    today = date.today()
    age = (today - dob).days // 365

    planets = parsed["planets"]
    lagna = parsed["lagna"]
    lagna_sign = lagna.get("sign", "")

    if not lagna_sign:
        print("WARNING: Missing lagna sign in chart data.", file=sys.stderr)

    for planet, data in planets.items():
        sign = data.get("sign", "")
        if sign:
            data["dignity"] = get_dignity(planet, sign)
            data["functional_status"] = get_functional_status(planet, lagna_sign) if lagna_sign else "unknown"
        if lagna_sign and "house" not in data and sign in SIGNS:
            data["house"] = house_from_lagna(sign, lagna_sign)

    moon = planets.get("Moon", {})
    moon_nak = normalize_nakshatra(moon.get("nakshatra", ""))
    moon_deg_in_nak = moon.get("degree_in_nakshatra", NAK_SPAN / 2)

    pillar = compute_pillar(planets, lagna, lagna_sign) if lagna_sign else {}
    vimsh = parsed.get("vimshottari") or (
        build_vimshottari_from_moon(moon_nak, moon_deg_in_nak, dob) if moon_nak else {}
    )
    vimsh_mds = vimsh.get("sequence", [])

    yogini = compute_yogini(moon_nak, moon_deg_in_nak, dob) if moon_nak else {}
    rtvd = compute_rtvd(dob, lagna_sign, planets) if lagna_sign else {}
    longevity = compute_longevity(planets, lagna_sign, vimsh_mds) if lagna_sign else {}
    karakas = compute_cara_karakas(planets)
    divisional = parsed.get("divisional") or {}
    chara_dasha = parsed.get("chara_dasha") or {}
    jaimini = build_jaimini_block(planets, lagna_sign, karakas, divisional, chara_dasha) if lagna_sign else {}
    numerology = compute_numerology(client_name, dob)
    mrityu = check_mrityu_bhaga(planets)

    house_lords_map = {}
    if lagna_sign:
        for h in range(1, 13):
            hs = house_sign(h, lagna_sign)
            lord = SIGN_LORDS[hs]
            lord_data = planets.get(lord, {})
            house_lords_map[h] = {
                "sign": hs,
                "lord": lord,
                "lord_sign": lord_data.get("sign", "?"),
                "lord_house": lord_data.get("house", "?"),
                "lord_dignity": get_dignity(lord, lord_data.get("sign", "?")),
                "functional": get_functional_status(lord, lagna_sign),
            }

    instructions = build_lane_instructions(
        planets, lagna, lagna_sign, house_lords_map, pillar, vimsh, yogini,
        rtvd, longevity, karakas, numerology, mrityu, age, today,
    )

    pc = {
        "meta": {
            "client": client_name,
            "dob": dob_str,
            "age": age,
            "report_date": str(today),
            "lagna_sign": lagna_sign,
            "lagna_degree": lagna.get("degree_in_sign", 0),
            "lagna_nakshatra": lagna.get("nakshatra", "?"),
            "lagna_pada": lagna.get("pada", "?"),
            "lagna_lord": SIGN_LORDS.get(lagna_sign, "?"),
            "source": source,
            "birth_place": parsed.get("birth_place"),
            "birth_time": parsed.get("birth_time"),
            "ayanamsa": parsed.get("ayanamsa", "LAHIRI"),
            "gender": parsed.get("gender"),
        },
        "planets": planets,
        "lagna": lagna,
        "house_lords": house_lords_map,
        "pillar": pillar,
        "vimshottari": vimsh,
        "yogini": yogini,
        "rtvd": rtvd,
        "longevity": longevity,
        "cara_karakas": karakas,
        "jaimini": jaimini,
        "chara_dasha": chara_dasha,
        "mrityu_bhaga": mrityu,
        "numerology": numerology,
        "ashtakavarga": parsed.get("ashtakavarga", {}),
        "divisional": divisional,
        "raw_sections": parsed.get("raw_sections", {}),
        "llm_lane_instructions": instructions,
        "kp": parsed.get("kp", {}),
    }
    from jaimini_chara_dasha import sync_chara_dasha_keys

    sync_chara_dasha_keys(pc)
    return pc


def precompute(extracted_path: str, client_name: str, dob_str: str) -> dict:
    text = Path(extracted_path).read_text(encoding="utf-8", errors="ignore")
    parsed = parse_extract(text)
    parsed.setdefault("raw_sections", {})["extract_path"] = str(extracted_path)
    return precompute_from_chart(parsed, client_name, dob_str, source="astrosage_extract")


def load_precomputed(path: str) -> dict:
    """Load session or PyJHora precomputed JSON."""
    return normalize_precomputed(json.loads(Path(path).read_text(encoding="utf-8")))


def resolve_precompute(
    client_name: str,
    dob: str,
    *,
    extracted_path: Optional[str] = None,
    precomputed_path: Optional[str] = None,
    birth_time: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    timezone: Optional[float] = None,
    place_name: str = "",
    ayanamsa: str = "LAHIRI",
    true_nodes: bool = False,
    effective_time: Optional[str] = None,
    lmt_correction: Optional[str] = None,
    gender: Optional[int] = None,
) -> dict:
    """
    Chart facts for all lanes — priority:
      1. precomputed JSON (--precomputed)
      2. birth coordinates via PyJHora (pyjhora/src)
      3. AstroSage extract parse (legacy fallback)
    """
    if precomputed_path and Path(precomputed_path).exists():
        return load_precomputed(precomputed_path)
    if birth_time and latitude is not None and longitude is not None and timezone is not None:
        from natal_from_pyjhora import BirthInput, precompute_from_pyjhora
        inp = BirthInput(
            client_name=client_name,
            dob=dob,
            birth_time=birth_time,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            place_name=place_name,
            ayanamsa=ayanamsa,
            true_nodes=true_nodes,
            effective_time=effective_time,
            lmt_correction=lmt_correction,
            gender=gender if gender is not None else 0,
        )
        return normalize_precomputed(precompute_from_pyjhora(inp))
    if extracted_path and Path(extracted_path).exists():
        text = Path(extracted_path).read_text(encoding="utf-8", errors="ignore")
        meta = parse_birth_meta(text)
        if birth_meta_complete(meta):
            from natal_from_pyjhora import BirthInput, precompute_from_pyjhora
            inp = BirthInput(
                client_name=client_name,
                dob=dob,
                birth_time=meta["birth_time"],
                latitude=meta["latitude"],
                longitude=meta["longitude"],
                timezone=meta["timezone"],
                place_name=place_name or meta.get("birth_place", ""),
                ayanamsa=ayanamsa,
                true_nodes=true_nodes,
                effective_time=effective_time,
                lmt_correction=lmt_correction,
                gender=gender if gender is not None else meta.get("gender", 0),
            )
            return normalize_precomputed(precompute_from_pyjhora(inp))
        return normalize_precomputed(precompute(extracted_path, client_name, dob))
    raise FileNotFoundError(
        "No chart source: provide --precomputed, birth coordinates (--time --lat --lon --tz), "
        "or an AstroSage extracted.txt path."
    )


def build_lane_instructions(planets, lagna, lagna_sign, house_lords,
                             pillar, vimsh, yogini, rtvd, longevity,
                             karakas, numerology, mrityu, age, today) -> dict:
    """Build per-lane natural-language instructions for the LLM."""
    ll = pillar.get("lagna_lord","?")
    ll_sign = pillar.get("lagna_lord_sign","?")
    ll_house = pillar.get("lagna_lord_house","?")
    ll_dig = pillar.get("lagna_lord_dignity","?")
    cur_md = vimsh.get("current_md") or {}
    cur_yogini = yogini.get("current_yogini") or {}
    cur_rtvd = rtvd.get("current_year") or {}
    mk1 = longevity.get("maraka_1",{})
    mk2 = longevity.get("maraka_2",{})

    return {
        "PILLAR": (
            f"Lagna = {lagna_sign} (nakshatra: {lagna.get('nakshatra','?')} pada {lagna.get('pada','?')}). "
            f"Lagna lord = {ll}, in {ll_sign} house {ll_house}, dignity = {ll_dig}. "
            f"Use the 'seven_factors' array in pillar section — write one table row per factor. "
            f"Use 'dispositor_chain' array for the chain section. "
            f"Use 'neecha_bhanga' object — if present write the rule that fired. "
            f"Current dasha = {cur_md.get('md_lord','?')} MD — state how it activates or suppresses the lagna lord."
        ),

        "BNN": (
            f"Lagna = {lagna_sign}. Lagna lord {ll} in {ll_sign} (house {ll_house}, {ll_dig}). "
            f"Moon in {planets.get('Moon',{}).get('sign','?')} house {planets.get('Moon',{}).get('house','?')}. "
            f"6th lord = {house_lords.get(6,{}).get('lord','?')} in {house_lords.get(6,{}).get('lord_sign','?')} "
            f"(house {house_lords.get(6,{}).get('lord_house','?')}, {house_lords.get(6,{}).get('lord_dignity','?')}). "
            f"7th lord = {house_lords.get(7,{}).get('lord','?')} in {house_lords.get(7,{}).get('lord_sign','?')}. "
            f"10th lord = {house_lords.get(10,{}).get('lord','?')} in {house_lords.get(10,{}).get('lord_sign','?')} "
            f"(house {house_lords.get(10,{}).get('lord_house','?')}). "
            f"Current MD = {cur_md.get('md_lord','?')} ({cur_md.get('start','?')} to {cur_md.get('end','?')}). "
            "Use Vimshottari antardasha table from 'vimshottari.current_md_antardashas' for near future predictions."
        ),

        "KP": (
            "KP data is in the raw extract under '|| KP System / Nakshatra Nadi ||'. "
            "Read the cuspal table directly from the extract. "
            f"Pre-computed house lords (for cross-checking): " +
            ", ".join(f"H{h}={v['lord']} in {v['lord_sign']}" for h,v in house_lords.items()) + ". "
            "For each cusp sub-lord: state what houses it signifies. "
            f"Current MD = {cur_md.get('md_lord','?')} — check if it signifies 10th/6th/2nd (career) or 7th (marriage)."
        ),

        "JAIMINI": (
            f"Cara karakas pre-computed from planet degrees: " +
            ", ".join(f"{k['role']}={k['planet']} ({k['degree']}° {k['sign']}, house {k['house']})"
                      for k in karakas.get("karakas",[])) + ". "
            "Karakamsha = navamsha sign of Atmakarak — check in D9 block from extract. "
            "Chara dasha table is in the Jaimini block — read dates from extract directly. "
            "Sign aspects (not house aspects) — every sign aspects the signs 3rd, 5th, 7th, 9th from it "
            "(except the adjacent). Use this for Jaimini house analysis."
        ),

        "VIMSHOTTARI": (
            f"FULL DASHA SEQUENCE pre-computed from Moon nakshatra ({planets.get('Moon',{}).get('nakshatra','?')}): " +
            "; ".join(f"{m['md_lord']} {m['start']}–{m['end']}" for m in vimsh.get("sequence",[])) + ". "
            f"CURRENT MD = {cur_md.get('md_lord','?')} ({cur_md.get('start','?')} to {cur_md.get('end','?')}). "
            f"Antardasha sequence in 'vimshottari.current_md_antardashas'. "
            "Apply 7-step analysis to current MD lord: (1)dignity, (2)house, (3)conjunctions, "
            "(4)nakshatra lord, (5)dispositor, (6)from Chandra lagna, (7)cross-verdict. "
            "All steps must use specific planet/sign/house data from 'planets' section."
        ),

        "YOGINI": (
            f"Yogini at birth = {yogini.get('yogini_at_birth','?')} "
            f"(lord: {yogini.get('yogini_lord_birth','?')}). "
            f"Current Yogini = {cur_yogini.get('yogini','?')} "
            f"({cur_yogini.get('start','?')} to {cur_yogini.get('end','?')}, "
            f"tone: {cur_yogini.get('tone','?')}). "
            "Full cycle table in 'yogini.full_cycle' — use this for the timeline section. "
            "Cross-check: does current Yogini lord agree with current Vimshottari MD lord in theme? "
            f"Ulka (Saturn) and Sankata (Rahu) = stress periods — flag them in the timeline."
        ),

        "ASHTAKAVARGA": (
            "Ashtakavarga data is in the raw extract. "
            "Parse SAV scores for all 12 houses and Jupiter/Saturn BAV per house from the extract. "
            "Pre-computed house lord map: " +
            ", ".join(f"H{h}: {v['lord']} ({v['lord_sign']})" for h,v in house_lords.items()) + ". "
            "For each house: if SAV < 25 = weak (challenges), > 30 = strong (support). "
            "Jupiter and Saturn current transit signs: check AstroSage transit section. "
            "For each transit sign: report BAV score + donor count from extract."
        ),

        "RTVD": (
            f"RTVD table pre-computed for {lagna_sign} lagna. "
            f"Current age {age} → active house = {cur_rtvd.get('house_active','?')} "
            f"({cur_rtvd.get('house_sign','?')}), "
            f"year lord = {cur_rtvd.get('year_lord','?')} "
            f"in {cur_rtvd.get('year_lord_sign','?')} house {cur_rtvd.get('year_lord_house','?')} "
            f"({cur_rtvd.get('year_lord_dignity','?')}). "
            "Use 'rtvd.table' array for the full age→house→lord table. "
            "For each year lord: state natal dignity and what it means for that year's domain. "
            "Cross-check with Vimshottari AD running in that year."
        ),

        "LONGEVITY": (
            f"Maraka 1 = {mk1.get('lord','?')} (2nd lord, in {mk1.get('lord_sign','?')} "
            f"house {mk1.get('lord_house','?')}, {mk1.get('lord_dignity','?')}). "
            f"Maraka 2 = {mk2.get('lord','?')} (7th lord, in {mk2.get('lord_sign','?')} "
            f"house {mk2.get('lord_house','?')}, {mk2.get('lord_dignity','?')}). "
            f"8th lord = {longevity.get('house_8_lord','?')} ({longevity.get('house_8_dignity','?')}). "
            f"Longevity estimate: {longevity.get('longevity_span_estimate','?')}. "
            + (f"CRITICAL Mrityu Bhaga: {', '.join(p['planet']+' at '+str(p['natal_degree'])+'° (diff '+str(p['difference_degrees'])+'°)' for p in longevity.get('critical_mb',[]))}. "
               if longevity.get("critical_mb") else "No critical Mrityu Bhaga planets. ")
            + "Identify MD periods of maraka lords from Vimshottari table — those are the key risk windows."
        ),

        "BLIND_CHART": (
            f"Primary timing: Jupiter and Saturn progressions. "
            f"Jupiter natal: {planets.get('Jupiter',{}).get('sign','?')} house {planets.get('Jupiter',{}).get('house','?')}. "
            f"Saturn natal: {planets.get('Saturn',{}).get('sign','?')} house {planets.get('Saturn',{}).get('house','?')}. "
            f"Current age = {age}. Lagna = {lagna_sign}. "
            "Calculate how many signs Jupiter moves in N years (approx 1 sign/year) and "
            "Saturn moves (approx 1 sign/2.5 years). "
            "State which house each occupies at current age vs birth. "
            "Past reconstruction: decade-by-decade from birth to now, using RTVD table as secondary check."
        ),

        "CONFLUENCE": (
            f"Key pre-computed data for all vote tables:\n"
            f"  Lagna lord {ll} in {ll_sign} house {ll_house} ({ll_dig}) — "
            f"{'strong pillar' if ll_dig in ['exalted','own_sign','moolatrikona'] else 'moderate pillar'}\n"
            f"  Current Vimshottari: {cur_md.get('md_lord','?')} MD, "
            f"AD from 'vimshottari.current_md_antardashas'\n"
            f"  Current Yogini: {cur_yogini.get('yogini','?')} ({cur_yogini.get('tone','?')})\n"
            f"  Current RTVD house: {cur_rtvd.get('house_active','?')}\n"
            f"  10th lord = {house_lords.get(10,{}).get('lord','?')} in "
            f"{house_lords.get(10,{}).get('lord_sign','?')} ({house_lords.get(10,{}).get('lord_dignity','?')})\n"
            f"  7th lord = {house_lords.get(7,{}).get('lord','?')} in "
            f"{house_lords.get(7,{}).get('lord_sign','?')}\n"
            f"  5th lord = {house_lords.get(5,{}).get('lord','?')} in "
            f"{house_lords.get(5,{}).get('lord_sign','?')}\n"
            f"  Longevity estimate: {longevity.get('longevity_span_estimate','?')}\n"
            "For each domain vote table: pull specific data above into Evidence column."
        ),
    }

# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 4:
        print("Usage: python3 astro_precompute.py <extracted.txt> <client_name> <YYYY-MM-DD> [output.json]")
        sys.exit(1)

    extracted_path = sys.argv[1]
    client_name    = sys.argv[2]
    dob_str        = sys.argv[3]
    output_path    = sys.argv[4] if len(sys.argv) > 4 else extracted_path.replace("_extracted.txt","_precomputed.json")

    print(f"Pre-computing astrology data for {client_name} (DOB: {dob_str})...")
    data = precompute(extracted_path, client_name, dob_str)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"Saved: {output_path}")
    print(f"Lagna: {data['meta']['lagna_sign']} | Age: {data['meta']['age']}")
    print(f"Lagna Lord: {data['meta']['lagna_lord']} in {data['pillar'].get('lagna_lord_sign','?')} "
          f"({data['pillar'].get('lagna_lord_dignity','?')})")
    if data.get("vimshottari",{}).get("current_md"):
        md = data["vimshottari"]["current_md"]
        print(f"Current MD: {md['md_lord']} ({md['start']} to {md['end']})")
    if data.get("yogini",{}).get("current_yogini"):
        y = data["yogini"]["current_yogini"]
        print(f"Current Yogini: {y['yogini']} lord={y['lord']} ({y['start']} to {y['end']}) — {y['tone']}")
    print(f"Longevity estimate: {data.get('longevity',{}).get('longevity_span_estimate','?')}")

if __name__ == "__main__":
    main()
