"""Divisional profile engine for the About You & Life Foundations section.

Provides a warm, highly specific, and accessible Vedic analysis of all key divisional charts
(D1, D2, D3, D4, D7, D9, D10, D12, D24, D30), delivering:
1. Chart-Specific Life Insights:
   - D10: Tailored career fields, executive archetype, and optimal work style based on 10th lords, D10 Lagna/10th house & Amatyakaraka.
   - D9: Specific life partner characteristics, marital dynamics, and Bhagyodaya path based on 7th lords & D9 Lagna.
   - D2: Practical wealth generation streams and asset retention instincts.
   - D3: Everyday initiative & drive (or early speech/motor development roadmap for children).
   - D7: Progeny promise, parenting style, and family expansion timeline.
   - D24: Ideal academic disciplines, intellectual strengths, and skill mastery.
   - D30: Physical stress points, vitality preservation, and inner resilience.
2. Domain-Specific Timelines (Non-repeating, tailored impact of running dasha on that specific life area).
3. Actionable Vedic Upaya (Practical, compassionate remedies).
4. Collapsible Technical Astrological Proof (<details> drawer for houses, lords, degrees, and dignities).
5. Gating: Remedies and deeper divisional charts unlocked in Paid tier, previewed in Free tier.
"""
from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Optional

from astro_precompute import (
    SIGN_LORDS,
    SIGNS,
    get_dignity,
    house_from_lagna,
    sign_index,
)


def house_sign(lagna: str, h: int) -> str:
    if not lagna or lagna not in SIGNS:
        return ""
    idx = (SIGNS.index(lagna) + (h - 1)) % 12
    return SIGNS[idx]


PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
DUSTHANA = {6, 8, 12}
GOOD_HOUSES = {1, 2, 4, 5, 7, 9, 10, 11}
NAT_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
NAT_MALEFIC = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}

# D2 (money & wealth) is deliberately NOT free: it is one of the most-wanted answers,
# and the free half shows what the chart is *activating*, not the wealth verdict.
FREE_ALLOWED_VARGAS = {"D1", "D3", "D12"}
LOCKED_TEASER_VARGAS = ["D7", "D9", "D10", "D24", "D30"]

ORDINALS = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", 6: "6th", 7: "7th", 8: "8th", 9: "9th", 10: "10th", 11: "11th", 12: "12th"}


@dataclass
class DivisionalInsight:
    code: str
    name: str
    governs: str
    domain_id: str
    lagna_sign: str
    lord: str
    lord_sign: str
    lord_house: int
    lord_dignity: str
    strength: str  # strong | mixed | weak
    headline: str
    prediction: str
    timeline: str
    remedy: str
    evidence: str


#: ``nav`` is the label this varga gets in the report's contents rail. The rail
#: is a narrow column read at a glance, so it carries the life area the reader
#: is looking for — "Career", not "Career Growth, Status & Public Respect".
VARGA_META: dict[str, dict[str, str]] = {
    "D1": {
        "name": "Your Personal Nature & Vitality",
        "governs": "Core Character, Mindset & Innate Strengths",
        "nav": "Self & vitality",
        "desc": "Your foundational personality, physical vitality, and natural approach to life.",
    },
    "D2": {
        "name": "Money, Savings & Wealth Growth",
        "governs": "Wealth Accumulation, Income Flow & Financial Stability",
        "nav": "Money & wealth",
        "desc": "Your financial instincts, asset retention power, and wealth building capacity.",
    },
    "D3": {
        "name": "Initiative, Courage & Everyday Drive",
        "governs": "Courage, Communication & Execution Stamina",
        "nav": "Drive & initiative",
        "desc": "Your courage, everyday initiative, sibling relationships, and execution stamina.",
    },
    "D4": {
        "name": "Home, Property & Domestic Peace",
        "governs": "Real Estate, Vehicles & Living Environment",
        "nav": "Home & property",
        "desc": "Fixed property ownership, residential peace, and relocation prospects.",
    },
    "D7": {
        "name": "Children, Family Continuity & Legacy",
        "governs": "Children, Creative Progeny & Family Future",
        "nav": "Children & legacy",
        "desc": "Your progeny prospects, parenting dynamics, and family continuity.",
    },
    "D9": {
        "name": "Marriage, Life Partner & Harmony",
        "governs": "Spouse Compatibility, Marital Bliss & Inner Growth",
        "nav": "Marriage & partner",
        "desc": "Your inner spiritual maturity, spouse compatibility, and lifelong partnership harmony.",
    },
    "D10": {
        "name": "Career, Business & Public Standing",
        "governs": "Professional Trajectory, Authority & Work Success",
        "nav": "Career & status",
        "desc": "Your professional trajectory, executive authority, public respect, and career breakthroughs.",
    },
    "D12": {
        "name": "Parents, Lineage & Family Roots",
        "governs": "Parental Heritage & Ancestral Blessings",
        "nav": "Parents & roots",
        "desc": "Your ancestral foundation, parental heritage, and inherited moral grounding.",
    },
    "D24": {
        "name": "Education, Knowledge & Skill Mastery",
        "governs": "Learning Potential, Memory & Strategic Acumen",
        "nav": "Learning & skills",
        "desc": "Your higher learning potential, analytical skills, and capacity to master complex disciplines.",
    },
    "D30": {
        "name": "Health, Energy & Inner Resilience",
        "governs": "Physical Stamina, Immunity & Stress Management",
        "nav": "Health & stamina",
        "desc": "Your bodily stamina, anatomical sensitivities, and inner resilience to overcome stress.",
    },
}

VARGA_META_HINGLISH: dict[str, dict[str, str]] = {
    "D1": {
        "name": "Janm Kundli (D1)",
        "governs": "Mool Swabhav Aur Sharirik Urja",
        "nav": "Aapka vyaktitva aur urja",
        "desc": "Aapka mool vyaktitva, physical vitality aur jeevan ka general orientation.",
    },
    "D2": {
        "name": "Dhan Varga (D2 · Hora)",
        "governs": "Dhan, Bachat Aur Aarthik Sthirta",
        "nav": "Dhan aur aarthik sthiti",
        "desc": "Dhan sanchay, asset building aur liquid resources ki sthirta.",
    },
    "D3": {
        "name": "Sahas, Bhai-Behen (D3 · Drekkana)",
        "governs": "Bhai-Behen, Sahas Aur Initiative",
        "nav": "Bhai-behen aur sahas",
        "desc": "Aapka sahas, dainik initiative, bhai-beheno se sambandh aur execution drive.",
    },
    "D4": {
        "name": "Sampatti, Nivas (D4 · Chaturthamsha)",
        "governs": "Ghar, Zameen, Vahan Aur Sthirta",
        "nav": "Ghar aur sampatti",
        "desc": "Property ownership, ghar ki sthirta aur sthan parivartan ke yog.",
    },
    "D7": {
        "name": "Santan Varga (D7 · Saptamsha)",
        "governs": "Santan, Parivar Aur Bhavishya",
        "nav": "Santan aur parivar",
        "desc": "Santan sukh, parivarik vistar aur legacy.",
    },
    "D9": {
        "name": "Vivah Aur Navamsha (D9)",
        "governs": "Jeevansathi, Vivah Aur Aantrik Vikas",
        "nav": "Vivah aur jeevansathi",
        "desc": "Aapka aadhyaatmik vikas, jeevansathi compatibility aur vaivahik sukh.",
    },
    "D10": {
        "name": "Career Aur Karyakshetra (D10 · Dasamsha)",
        "governs": "Career Growth, Pratishtha Aur Samman",
        "nav": "Career aur pratishtha",
        "desc": "Aapka professional karma, public recognition, authority aur career trajectory.",
    },
    "D12": {
        "name": "Vansh Aur Mata-Pita (D12 · Dwadashamsha)",
        "governs": "Mata-Pita Aur Vansh Ka Aashirwad",
        "nav": "Mata-pita aur vansh",
        "desc": "Parivarik jadh, mata-pita ka sahyog aur sanskar.",
    },
    "D24": {
        "name": "Uchha Shiksha (D24 · Chaturvimshamsha)",
        "governs": "Shiksha, Memory Aur Boudhik Shamta",
        "nav": "Shiksha aur gyan",
        "desc": "Uchha shiksha, analytical skills aur gyan astitva.",
    },
    "D30": {
        "name": "Swasthya Aur Immunity (D30 & D27)",
        "governs": "Sharirik Stamina Aur Swasthya Savdhani",
        "nav": "Swasthya aur stamina",
        "desc": "Sharirik immunity, sensitive health patterns aur mushkilo se ubharne ki shakti.",
    },
}

VARGA_META_TENGLISH: dict[str, dict[str, str]] = {
    "D1": {
        "name": "Janma Kundali (D1)",
        "governs": "Moola Swabhavam Mariyu Sharirika Balam",
        "nav": "Mee vyakthithvam mariyu urja",
        "desc": "Mee moola vyakthithvam, physical vitality mariyu jeevitha orientation.",
    },
    "D2": {
        "name": "Dhana Vargamu (D2 · Hora)",
        "governs": "Dhanam, Podupu Mariyu Aarthika Sthiratha",
        "nav": "Dhanam mariyu aarthika sthiti",
        "desc": "Dhana sanchayam, aasthula vikasam mariyu aarthika sthiratha.",
    },
    "D3": {
        "name": "Dhairyam, Sahodharulu (D3 · Drekkana)",
        "governs": "Sahodharulu, Dhairyam Mariyu Initiative",
        "nav": "Sahodharulu mariyu dhairyam",
        "desc": "Mee sahasam, dainandina initiative, sahodharulatho sambandham.",
    },
    "D4": {
        "name": "Aasthi, Nivasam (D4 · Chaturthamsha)",
        "governs": "Illu, Bhoomi, Vahanam Mariyu Sthiratha",
        "nav": "Illu mariyu aasthi",
        "desc": "Property ownership, illu sthiratha mariyu sthana maarpu yogalu.",
    },
    "D7": {
        "name": "Santhana Vargamu (D7 · Saptamsha)",
        "governs": "Pillalu, Kutumbam Mariyu Bhavishyathu",
        "nav": "Pillalu mariyu kutumbam",
        "desc": "Santhana soukhyam, kutumba vikasam mariyu legacy.",
    },
    "D9": {
        "name": "Vivaham Mariyu Navamsha (D9)",
        "governs": "Jeevithabhagswami, Vivaham Mariyu Aantrika Vikasamu",
        "nav": "Vivaham mariyu jeevithabhagswami",
        "desc": "Mee aadhyaathmika vikasam, jeevithabhagswami anukoolatha mariyu vaivahika soukhyam.",
    },
    "D10": {
        "name": "Career Mariyu Profession (D10 · Dasamsha)",
        "governs": "Career Growth, Gouravam Mariyu Status",
        "nav": "Career mariyu gouravam",
        "desc": "Mee professional karma, gouravam, adhikaaram mariyu career trajectory.",
    },
    "D12": {
        "name": "Vamsham Mariyu Thallidandrulu (D12 · Dwadashamsha)",
        "governs": "Thallidandrulu Mariyu Poorveekula Aashirwadam",
        "nav": "Thallidandrulu mariyu vamsham",
        "desc": "Kutumba moolalu, thallidandrula sahakaram mariyu samskaralu.",
    },
    "D24": {
        "name": "Uchha Vidya (D24 · Chaturvimshamsha)",
        "governs": "Chaduvu, Memory Mariyu Telivi",
        "nav": "Chaduvu mariyu gyanam",
        "desc": "Uchha vidya, analytical skills mariyu vidya samardhyam.",
    },
    "D30": {
        "name": "Aarogyam Mariyu Immunity (D30 & D27)",
        "governs": "Sharirika Stamina Mariyu Aarogya Jagratthalu",
        "nav": "Aarogyam mariyu stamina",
        "desc": "Sharirika immunity, health sensitivities mariyu kashtalanu edurkonedi shakti.",
    },
}

PLANET_REMEDIES: dict[str, dict[str, str]] = {
    "Sun": {
        "strengthen": "Offer fresh water to the morning sun daily (Surya Arghya) with a calm mind; nurture respect for elders and father figures.",
        "dusthana": "Recite the Aditya Hridaya Stotram on Sundays; donate copper, wheat, or jaggery to support those in need.",
        "debilitated": "Chant 'Om Hram Hreem Hroum Sah Suryaya Namah' at sunrise; practice daily acts of kindness without seeking validation.",
    },
    "Moon": {
        "strengthen": "Perform Monday Jal Abhishek with clean water on Shiva Lingam; practice mindful hydration, calm breathing, and love for mother.",
        "dusthana": "Chant the Chandra Gayatri Mantra on Monday evenings; keep living spaces clean, well-lit, and peaceful.",
        "debilitated": "Chant 'Om Shram Shreem Shroum Sah Chandraya Namah'; offer milk or food to cows on Mondays to soothe emotional stress.",
    },
    "Mars": {
        "strengthen": "Read the Hanuman Chalisa on Tuesdays; channel physical energy into regular outdoor sports, yoga, or martial discipline.",
        "dusthana": "Chant the Mangal Gayatri Mantra; practice deep breathing before speaking in heated moments; donate red lentils (masoor dal).",
        "debilitated": "Chant 'Om Kram Kreem Kroum Sah Bhaumaya Namah'; practice patience, gentleness, and supporting siblings.",
    },
    "Mercury": {
        "strengthen": "Offer fresh green grass or spinach to cows on Wednesdays; chant the Budha Gayatri Mantra or practice daily reading aloud.",
        "dusthana": "Chant 'Om Bram Breem Broum Sah Budhaya Namah' on Wednesdays; engage in structured speech practice, vocal recitation, and puzzles.",
        "debilitated": "Wear green shades on Wednesdays; practice attentive listening; donate educational books or notebooks to young students.",
    },
    "Jupiter": {
        "strengthen": "Honor teachers and mentors on Thursdays; chant the Brihaspati Gayatri Mantra; maintain truthfulness and moral kindness.",
        "dusthana": "Chant 'Om Gram Greem Groum Sah Gurave Namah' on Thursdays; donate yellow fruits (bananas) or turmeric at a spiritual place.",
        "debilitated": "Offer yellow food to elders on Thursdays; maintain steady humility, wisdom, and lifelong learning.",
    },
    "Venus": {
        "strengthen": "Chant the Shukra Gayatri Mantra; cultivate artistic appreciation, clean surroundings, and harmony in the home.",
        "dusthana": "Chant 'Om Dram Dreem Droum Sah Shukraya Namah' on Fridays; support women's welfare initiatives or donate sweets.",
        "debilitated": "Practice genuine devotion and self-respect; avoid impulsive emotional attachments; donate white grains on Fridays.",
    },
    "Saturn": {
        "strengthen": "Light a sesame oil lamp on Saturday evenings; cultivate patience, humility, and steady, disciplined effort.",
        "dusthana": "Recite the Dasharatha Shani Stotram on Saturdays; feed stray animals or support elderly and working-class people.",
        "debilitated": "Chant 'Om Pram Preem Proum Sah Shanaischaraya Namah'; stay physically active; avoid procrastination.",
    },
    "Rahu": {
        "strengthen": "Chant the Saraswati Vandana daily; avoid speculative rumors; maintain clean, uncluttered living spaces.",
        "dusthana": "Chant 'Om Bhram Bhreem Bhroum Sah Rahave Namah' during twilight; donate dark blankets or mustard seeds to those in need.",
        "debilitated": "Practice daily meditation to still an overactive imagination; limit excessive screen time and digital stimulation.",
    },
    "Ketu": {
        "strengthen": "Chant the Ganesha Atharvashirsha on Tuesdays; cultivate inner reflection, pranayama, and simple, peaceful living.",
        "dusthana": "Chant 'Om Stram Streem Stroum Sah Ketave Namah'; feed multi-colored dogs; donate warm clothes in winter.",
        "debilitated": "Practice deep diaphragmatic breathing (Pranayama) daily; offer grains to birds in the morning.",
    },
}


def _sign_of(value: Any) -> str:
    """``pc["lagna"]`` is a sign string on some precomputes and ``{"sign": …}``
    on others. Returning the dict made every varga lookup raise on an
    unhashable key, which the caller swallowed — the whole divisional half of
    the reading vanished without an error anyone would see."""
    if isinstance(value, dict):
        return str(value.get("sign") or "")
    return str(value or "")


def _get_varga_lagna(pc: dict, code: str) -> str:
    div_entry = pc.get("divisional", {}).get(code, {}) or {}
    if code == "D1":
        return (
            _sign_of(pc.get("meta", {}).get("lagna_sign", ""))
            or _sign_of(pc.get("lagna", ""))
            or _sign_of(pc.get("planets", {}).get("Lagna", {}).get("sign", ""))
            or _sign_of(pc.get("planets", {}).get("lagna", {}).get("sign", ""))
            or _sign_of(div_entry.get("Lagna", ""))
            or _sign_of(div_entry.get("lagna", ""))
        )
    return _sign_of(div_entry.get("Lagna", "")) or _sign_of(div_entry.get("lagna", ""))


def _get_varga_planet_sign(pc: dict, code: str, planet: str) -> str:
    if code == "D1":
        return (pc.get("planets", {}).get(planet, {}) or {}).get("sign", "")
    return (pc.get("divisional", {}).get(code, {}) or {}).get(planet, "")


def _graded(pc: dict, planets: list, strong: str, mixed: str, strained: str) -> str:
    """Pick the sentence that matches how strong the relevant planets really are.

    The divisional text used to carry one flattering default per life area
    ("You carry strong moral grounding and blessings from parents") that printed
    for every chart. Now the outcome follows the planets that govern the area.
    """
    import chart_lines as CL
    names = [x for x in planets if x]
    if not names:
        return mixed
    avg = sum(CL.score_planet(pc, x) for x in names) / len(names)
    g = CL.grade(round(avg))
    return {"strong": strong, "mixed": mixed, "strained": strained}[g]


def _lagna_sentence(lagna: str) -> str:
    """The rising sign's own description, not one sentence for every chart."""
    try:
        from bhardwaj_prose import LAGNA_HUMAN
        txt = str(LAGNA_HUMAN.get(lagna) or "").strip()
    except Exception:  # noqa: BLE001
        txt = ""
    if txt:
        return txt.rstrip(".")
    return f"Your rising sign shapes how you come across to others"


def _a_an(phrase: str) -> str:
    """'a' or 'an' for the phrase that follows ("a intellectually" read wrong)."""
    word = (str(phrase or "").strip().split() or [""])[0].lower()
    if not word:
        return "a"
    if word.startswith(("uni", "use", "usu", "uti", "one", "eu")):
        return "a"
    if word.startswith(("hour", "honest", "honou", "honor", "heir")):
        return "an"
    return "an" if word[0] in "aeiou" else "a"


def _format_month_year(date_str: str) -> str:
    if not date_str or len(date_str) < 7:
        return date_str
    try:
        y, m = int(date_str[:4]), int(date_str[5:7])
        month_names = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        if 1 <= m <= 12:
            return f"{month_names[m]} {y}"
    except Exception:
        pass
    return date_str[:7]


def _to_date(v) -> date | None:
    if not v:
        return None
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


# ── Classical Parāśarī Ashtakavarga Benefic-Point Tables (SAV Total = 337) ──
AV_SEVEN = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
AV_TABLE = {
    "Sun": {
        "Sun": [1, 2, 4, 7, 8, 9, 10, 11], "Moon": [3, 6, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11], "Mercury": [3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [5, 6, 9, 11], "Venus": [6, 7, 12],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11], "Lagna": [3, 4, 6, 10, 11, 12]},
    "Moon": {
        "Sun": [3, 6, 7, 8, 10, 11], "Moon": [1, 3, 6, 7, 10, 11],
        "Mars": [2, 3, 5, 6, 9, 10, 11], "Mercury": [1, 3, 4, 5, 7, 8, 10, 11],
        "Jupiter": [1, 2, 4, 7, 8, 10, 11], "Venus": [3, 4, 5, 7, 9, 10, 11],
        "Saturn": [3, 5, 6, 11], "Lagna": [3, 6, 10, 11]},
    "Mars": {
        "Sun": [3, 5, 6, 10, 11], "Moon": [3, 6, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11], "Mercury": [3, 5, 6, 11],
        "Jupiter": [6, 10, 11, 12], "Venus": [6, 8, 11, 12],
        "Saturn": [1, 4, 7, 8, 9, 10, 11], "Lagna": [1, 3, 6, 10, 11]},
    "Mercury": {
        "Sun": [5, 6, 9, 11, 12], "Moon": [2, 4, 6, 8, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11], "Mercury": [1, 3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [6, 8, 11, 12], "Venus": [1, 2, 3, 4, 5, 8, 9, 11],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11], "Lagna": [1, 2, 4, 6, 8, 10, 11]},
    "Jupiter": {
        "Sun": [1, 2, 3, 4, 7, 8, 9, 10, 11], "Moon": [2, 5, 7, 9, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11], "Mercury": [1, 2, 4, 5, 6, 9, 10, 11],
        "Jupiter": [1, 2, 3, 4, 7, 8, 10, 11], "Venus": [2, 5, 6, 9, 10, 11],
        "Saturn": [3, 5, 6, 12], "Lagna": [1, 2, 4, 5, 6, 7, 9, 10, 11]},
    "Venus": {
        "Sun": [8, 11, 12], "Moon": [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "Mars": [3, 5, 6, 9, 11, 12], "Mercury": [3, 5, 6, 9, 11],
        "Jupiter": [5, 8, 9, 10, 11], "Venus": [1, 2, 3, 4, 5, 8, 9, 10, 11],
        "Saturn": [3, 4, 5, 8, 9, 10, 11], "Lagna": [1, 2, 3, 4, 5, 8, 9, 11]},
    "Saturn": {
        "Sun": [1, 2, 4, 7, 8, 10, 11], "Moon": [3, 6, 11],
        "Mars": [3, 5, 6, 10, 11, 12], "Mercury": [6, 8, 9, 10, 11, 12],
        "Jupiter": [5, 6, 11, 12], "Venus": [6, 11, 12],
        "Saturn": [3, 5, 6, 11], "Lagna": [1, 3, 4, 6, 10, 11]},
}


def compute_chart_ashtakavarga(pc: dict) -> dict[str, Any]:
    planets = pc.get("planets", {})
    raw_l = pc.get("lagna")
    lagna_sign = (
        pc.get("meta", {}).get("lagna_sign", "")
        or (raw_l if isinstance(raw_l, str) else (raw_l or {}).get("sign", ""))
    )
    if not lagna_sign or lagna_sign not in SIGNS:
        return {}
    pos = {}
    for p in AV_SEVEN:
        s = planets.get(p, {}).get("sign", "")
        if s in SIGNS:
            pos[p] = SIGNS.index(s)
    if lagna_sign in SIGNS:
        pos["Lagna"] = SIGNS.index(lagna_sign)

    bav = {p: [0] * 12 for p in AV_SEVEN}
    for planet in AV_SEVEN:
        for contrib, houses in AV_TABLE[planet].items():
            if contrib in pos:
                base_idx = pos[contrib]
                for h in houses:
                    sign_idx = (base_idx + h - 1) % 12
                    bav[planet][sign_idx] += 1

    sav = [0] * 12
    for s_idx in range(12):
        sav[s_idx] = sum(bav[p][s_idx] for p in AV_SEVEN)

    return {
        "sav": {SIGNS[i]: sav[i] for i in range(12)},
        "bav": {p: {SIGNS[i]: bav[p][i] for i in range(12)} for p in AV_SEVEN},
    }


def get_live_transit_positions(target_date: date) -> dict[str, str]:
    try:
        import swisseph as swe
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        jd = swe.julday(target_date.year, target_date.month, target_date.day, 12.0)
        bodies = {
            "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
            "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE,
        }
        out = {}
        for name, pid in bodies.items():
            lon = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)[0][0]
            out[name] = SIGNS[int(lon // 30) % 12]
        out["Ketu"] = SIGNS[(SIGNS.index(out["Rahu"]) + 6) % 12]
        return out
    except Exception:
        return {}


def get_transit_ashtakavarga_domain_note(
    domain_code: str,
    target_start: date | None,
    target_end: date | None,
    pc: dict,
    av_data: dict,
) -> str:
    if not target_start or not target_end or not av_data:
        return ""
    raw_l = pc.get("lagna")
    d1_lagna = (
        pc.get("meta", {}).get("lagna_sign", "")
        or (raw_l if isinstance(raw_l, str) else (raw_l or {}).get("sign", ""))
    )
    if not d1_lagna or d1_lagna not in SIGNS:
        return ""

    def h_sign(h: int) -> str:
        return SIGNS[(SIGNS.index(d1_lagna) + h - 1) % 12]

    sav = av_data.get("sav", {})
    t_mid = target_start + (target_end - target_start) // 2
    transits = get_live_transit_positions(t_mid)
    if not transits:
        return ""
    
    jup_sign = transits.get("Jupiter", "")
    sat_sign = transits.get("Saturn", "")
    notes = []

    if domain_code == "D10":
        h10_s = h_sign(10)
        h1_s = h_sign(1)
        h11_s = h_sign(11)
        if jup_sign in (h10_s, h1_s, h11_s):
            b = sav.get(jup_sign, 28)
            b_eval = "amplified traction" if b >= 30 else "favorable support" if b >= 28 else "steady progress"
            notes.append(f"Transit Jupiter crossing your {jup_sign} ({b} SAV Bindus · {b_eval})")
        if sat_sign in (h10_s, h1_s, h11_s):
            b = sav.get(sat_sign, 28)
            notes.append(f"Transit Saturn structuring {sat_sign} ({b} SAV Bindus)")

    elif domain_code == "D9":
        h7_s = h_sign(7)
        v_sign = pc.get("planets", {}).get("Venus", {}).get("sign", "")
        if jup_sign in (h7_s, v_sign, h_sign(1), h_sign(5)):
            b = sav.get(jup_sign, 28)
            b_eval = "high relationship harmony" if b >= 28 else "conscious patience"
            notes.append(f"Transit Jupiter activating {jup_sign} ({b} SAV Bindus · {b_eval})")

    elif domain_code == "D4":
        h4_s = h_sign(4)
        h12_s = h_sign(12)
        if jup_sign in (h4_s, h12_s, h_sign(9)):
            b = sav.get(jup_sign, 28)
            b_eval = "fruitful property/relocation traction" if b >= 28 else "steady timing"
            notes.append(f"Transit Jupiter supporting {jup_sign} ({b} SAV Bindus · {b_eval})")

    elif domain_code == "D2":
        h2_s = h_sign(2)
        h11_s = h_sign(11)
        if jup_sign in (h2_s, h11_s, h_sign(9), h_sign(1)):
            b = sav.get(jup_sign, 28)
            b_eval = "strong compounding capacity" if b >= 30 else "positive cashflow support" if b >= 28 else "disciplined budgeting"
            notes.append(f"Transit Jupiter backing {jup_sign} ({b} SAV Bindus · {b_eval})")

    elif domain_code == "D30":
        h1_s = h_sign(1)
        h6_s = h_sign(6)
        h8_s = h_sign(8)
        if sat_sign in (h1_s, h6_s, h8_s):
            b = sav.get(sat_sign, 28)
            b_eval = "strong natural protective buffer" if b >= 28 else "conscious vitality pacing recommended"
            notes.append(f"Transit Saturn crossing {sat_sign} ({b} SAV Bindus · {b_eval})")
        if jup_sign in (h1_s, h6_s, h8_s, h_sign(5), h_sign(9)):
            b = sav.get(jup_sign, 28)
            notes.append(f"Transit Jupiter protective aspect over {jup_sign} ({b} SAV Bindus)")

    if notes:
        return f" · <b>Gochar & Ashtakavarga Confluence:</b> {'; '.join(notes)}"
    return ""


def _build_domain_specific_timeline(
    pc: dict,
    code: str,
    current_age: int,
    curr_md: str,
    curr_ad_name: str,
    curr_ad_end: str,
    adulthood_md: str,
    adulthood_start_yr: int,
    lang: str = "en",
) -> str:
    """Builds distinct, domain-specific multi-clock confluence timeline guidance (Vimshottari + Jaimini Chara + Yogini Antardashas + Transits)."""
    lang_code = str(lang or "").lower().strip()
    is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")
    is_child = current_age < 18
    this_yr = date.today().year
    t_now = date.today()

    # 1. Vimshottari Data
    vim = pc.get("vimshottari", {})
    curr_ad_list = vim.get("current_md_antardashas", [])

    curr_ad = None
    future_ads = []
    for ad in curr_ad_list:
        st = ad.get("status") or ("current" if ad.get("is_current") else "")
        if st == "current" or ad.get("is_current"):
            curr_ad = ad
        elif st == "future":
            future_ads.append(ad)

    if not curr_ad and curr_ad_list:
        curr_ad = curr_ad_list[0]
    # A chart can arrive with no dasha table at all (a partial precompute, or
    # a caller that only wants the varga blocks). That is not a reason to lose
    # the whole divisional half of the page.
    curr_ad = curr_ad or {}

    curr_ad_lord = curr_ad.get("ad_lord") or curr_ad.get("antardasha") or curr_ad_name or "Sub-period"
    curr_ad_end_fmt = _format_month_year(str(curr_ad.get("end") or "")) or curr_ad_end

    # 2. Jaimini Chara Dasha Data
    jaimini = pc.get("jaimini", {})
    chara = jaimini.get("chara_dasha", {})
    curr_chara_m = chara.get("current_maha", {}) if isinstance(chara, dict) else {}
    curr_chara_a = chara.get("current_antar", {}) if isinstance(chara, dict) else {}
    chara_m_sign = curr_chara_m.get("sign", "")
    chara_a_sign = curr_chara_a.get("sign", "")
    chara_maha_list = chara.get("maha", []) if isinstance(chara, dict) else []

    # 3. Yogini Dasha Data (Progressive Antardashas)
    dob_raw = pc.get("meta", {}).get("birth_date") or pc.get("meta", {}).get("dob") or pc.get("dob")
    dob_d = date.fromisoformat(str(dob_raw)[:10]) if dob_raw else date(this_yr - current_age, 1, 1)
    moon_nak = str((pc.get("planets", {}).get("Moon", {}) or {}).get("nakshatra", "Hasta"))
    moon_deg = float((pc.get("planets", {}).get("Moon", {}) or {}).get("degree_in_sign", 0.0) or 0.0) % 13.333333

    active_yog_antar = None
    all_yog_antars = []
    try:
        from chara_yogini_timing import build_progressive_yogini_periods
        all_yog_antars = build_progressive_yogini_periods(dob_d, moon_nak, moon_deg)
        for p in all_yog_antars:
            p_st = _to_date(p.get("start"))
            p_en = _to_date(p.get("end"))
            if p_st and p_en and p_st <= t_now <= p_en:
                active_yog_antar = p
                break
    except Exception:
        pass

    if active_yog_antar:
        yog_display = f"{active_yog_antar['maha_yogini']}-{active_yog_antar['yogini']} ({active_yog_antar['lord']})"
    else:
        yogini = pc.get("yogini", {})
        curr_yog = yogini.get("current_yogini", {}) if isinstance(yogini, dict) else {}
        yog_display = f"{curr_yog.get('yogini', 'Ulka')} ({curr_yog.get('lord', 'Saturn')})"

    # 4. Karakas & Lords
    k_list = jaimini.get("karakas", [])
    k_map = {}
    if isinstance(k_list, list):
        for k_obj in k_list:
            r = str(k_obj.get("role", "")).upper()
            p = str(k_obj.get("planet", ""))
            if "ATMA" in r: k_map["AK"] = p
            elif "AMATYA" in r: k_map["AmK"] = p
            elif "BHRATRU" in r: k_map["BK"] = p
            elif "MATRU" in r: k_map["MK"] = p
            elif "PUTRA" in r: k_map["PK"] = p
            elif "GNATI" in r: k_map["GK"] = p
            elif "DARA" in r: k_map["DK"] = p
    elif isinstance(k_list, dict):
        k_map = k_list

    ak = k_map.get("AK", "Sun")
    amk = k_map.get("AmK", "Sun")
    bk = k_map.get("BK", "Mars")
    mk = k_map.get("MK", "Moon")
    pk = k_map.get("PK", "Jupiter")
    gk = k_map.get("GK", "Saturn")
    dk = k_map.get("DK", "Venus")

    d1_lagna = pc.get("meta", {}).get("lagna_sign", "")
    if not d1_lagna:
        raw_lagna = pc.get("lagna")
        if isinstance(raw_lagna, dict):
            d1_lagna = raw_lagna.get("sign", "Gemini")
        elif isinstance(raw_lagna, str) and raw_lagna:
            d1_lagna = raw_lagna
        else:
            d1_lagna = "Gemini"

    def get_h_lord(h: int) -> str:
        if not d1_lagna or d1_lagna not in SIGNS:
            return ""
        s = SIGNS[(SIGNS.index(d1_lagna) + h - 1) % 12]
        return SIGN_LORDS.get(s, "")

    h10_lord = get_h_lord(10)
    h7_lord = get_h_lord(7)
    h2_lord = get_h_lord(2)
    h11_lord = get_h_lord(11)
    h5_lord = get_h_lord(5)
    h4_lord = get_h_lord(4)
    h3_lord = get_h_lord(3)
    h9_lord = get_h_lord(9)

    def find_target_ad(target_lords: list[str]) -> tuple[str, str, str, date | None, date | None]:
        for t in target_lords:
            for ad in future_ads:
                l = ad.get("ad_lord") or ad.get("antardasha") or ""
                if l == t:
                    st_d = _to_date(ad.get("start"))
                    en_d = _to_date(ad.get("end"))
                    st = _format_month_year(str(ad.get("start") or ""))
                    en = _format_month_year(str(ad.get("end") or ""))
                    return l, st, en, st_d, en_d
        if future_ads:
            ad = future_ads[0]
            l = ad.get("ad_lord") or ad.get("antardasha") or ""
            st_d = _to_date(ad.get("start"))
            en_d = _to_date(ad.get("end"))
            st = _format_month_year(str(ad.get("start") or ""))
            en = _format_month_year(str(ad.get("end") or ""))
            return l, st, en, st_d, en_d
        return "", "", "", None, None

    def get_overlapping_confluence_notes(st_d: date | None, en_d: date | None, target_karakas: list[str]) -> tuple[str, str]:
        if not st_d or not en_d:
            return "", ""
        # 1. Overlapping Chara sign (primary)
        overlapping_chara = []
        for cm in chara_maha_list:
            c_st = _to_date(cm.get("start"))
            c_en = _to_date(cm.get("end"))
            if c_st and c_en and c_en > st_d and c_st < en_d:
                s_name = str(cm.get("sign", ""))
                if s_name and s_name not in overlapping_chara:
                    overlapping_chara.append(s_name)
        chara_note = ""
        if overlapping_chara:
            chara_signs_str = " → ".join(overlapping_chara[:2])
            chara_note = f" Aligned with the <b>{chara_signs_str} Chara Dasha</b>."

        # 2. Overlapping Yogini Antardashas
        yog_note = ""
        matching_yogs = []
        for yp in all_yog_antars:
            y_st = _to_date(yp.get("start"))
            y_en = _to_date(yp.get("end"))
            if y_st and y_en and y_en > st_d and y_st < en_d:
                if yp.get("lord") in target_karakas or yp.get("yogini") in target_karakas:
                    y_st_fmt = _format_month_year(str(yp.get("start") or ""))
                    y_en_fmt = _format_month_year(str(yp.get("end") or ""))
                    if y_st_fmt and y_en_fmt:
                        matching_yogs.append(f"<b>Yogini {yp['maha_yogini']}-{yp['yogini']} ({yp['lord']})</b> from {y_st_fmt} to {y_en_fmt}")
        if matching_yogs:
            yog_note = f" (coinciding with {'; '.join(matching_yogs[:2])})"
        return chara_note, yog_note

    # Multi-Clock Status Line
    chara_str = f" · Chara Dasha: <b>{chara_m_sign}{f'-{chara_a_sign}' if chara_a_sign else ''}</b>" if chara_m_sign else ""
    yog_str = f" · Yogini: <b>{yog_display}</b>" if yog_display else ""
    if is_hinglish:
        active_clocks = f"<b>Chalu Dasha Aur Grah Alignment:</b> Vimshottari <b>{curr_md}-{curr_ad_lord}</b> ({curr_ad_end_fmt} tak){chara_str}{yog_str}."
    elif is_tenglish:
        active_clocks = f"<b>Chalu Dasha Mariyu Graha Alignment:</b> Vimshottari <b>{curr_md}-{curr_ad_lord}</b> ({curr_ad_end_fmt} varaku){chara_str}{yog_str}."
    else:
        active_clocks = f"<b>Active Multi-Clock Alignment:</b> Vimshottari <b>{curr_md}-{curr_ad_lord}</b> (until {curr_ad_end_fmt}){chara_str}{yog_str}."

    # Compute Ashtakavarga SAV & BAV Data for Chart
    av_data = compute_chart_ashtakavarga(pc)

    if code == "D10":
        # Career
        if is_child:
            launch_yr = this_yr + (22 - current_age)
            peak_yr = this_yr + (28 - current_age)
            return (
                f"<b>Current Foundation Phase ({curr_md}–{curr_ad_lord}):</b> Building curiosity, academic focus, and early discipline.<br>"
                f"<b>Key Career Launch Window:</b> <span style='color:var(--positive,#1c6b45);font-weight:700;'>{launch_yr}–{launch_yr+4} (Ages 22–26)</span> | "
                f"<b>Executive Leadership Window:</b> <span style='color:var(--positive,#1c6b45);font-weight:700;'>{peak_yr}–{peak_yr+6} (Ages 28–34)</span>."
            )
        else:
            c_lord, c_st, c_en, c_st_d, c_en_d = find_target_ad(["Venus", amk, "Sun", h10_lord, "Jupiter", "Mars"])
            return (
                f"<b>Current Phase ({curr_md}–{curr_ad_lord}, until {curr_ad_end_fmt}):</b> "
                f"Quiet consolidation, refining specialized skills, and establishing solid internal systems without forcing hasty career pivots.<br>"
                f"<b>Upcoming Major Breakthrough:</b> <span style='color:var(--positive,#1c6b45);font-weight:700;'>{c_st} – {c_en} ({curr_md}–{c_lord})</span> — "
                f"Major executive recognition, leadership promotion, and substantial career elevation."
            )

    elif code == "D9":
        # Marriage
        if is_child:
            m_yr = this_yr + (26 - current_age)
            return (
                f"<b>Partnership Horizon:</b> <span style='color:var(--positive,#1c6b45);font-weight:700;'>{m_yr}–{m_yr+5} (Ages 26–31)</span> — "
                f"Auspicious timing for marriage, life partnership, and mutual emotional maturity."
            )
        else:
            m_lord, m_st, m_en, m_st_d, m_en_d = find_target_ad(["Venus", dk, h7_lord, "Jupiter"])
            return (
                f"<b>Current Phase ({curr_md}–{curr_ad_lord}, until {curr_ad_end_fmt}):</b> "
                f"Deepening mutual emotional grounding, patience, and clear communication in relationships.<br>"
                f"<b>Relational Harmony & Partnership Window:</b> <span style='color:var(--positive,#1c6b45);font-weight:700;'>{m_st} – {m_en} ({curr_md}–{m_lord})</span> — "
                f"Warm emotional alignment, shared happiness, and elevated domestic harmony."
            )

    elif code == "D2":
        # Wealth
        w_lord, w_st, w_en, w_st_d, w_en_d = find_target_ad(["Venus", "Jupiter", h2_lord, h11_lord, "Mercury"])
        return (
            f"<b>Current Phase ({curr_md}–{curr_ad_lord}, until {curr_ad_end_fmt}):</b> "
            f"Disciplined budgeting, capital preservation, and avoiding unvetted speculative risks.<br>"
            f"<b>Major Wealth Surge & Asset Accumulation:</b> <span style='color:var(--positive,#1c6b45);font-weight:700;'>{w_st} – {w_en} ({curr_md}–{w_lord})</span> — "
            f"Accelerated savings, lucrative income flow, and strong financial stability."
        )

    elif code == "D7":
        # Children
        if is_child:
            p_yr = this_yr + (28 - current_age)
            return (
                f"<b>Family Continuation Window:</b> <span style='color:var(--positive,#1c6b45);font-weight:700;'>{p_yr}–{p_yr+5} (Ages 28–33)</span> — "
                f"Supportive period for parenthood and family continuation."
            )
        else:
            p_lord, p_st, p_en, p_st_d, p_en_d = find_target_ad([pk, h5_lord, "Jupiter", "Moon", "Venus"])
            return (
                f"<b>Current Phase ({curr_md}–{curr_ad_lord}, until {curr_ad_end_fmt}):</b> "
                f"Supportive family foundation and patient, attentive parenting.<br>"
                f"<b>Family Expansion & Joyful Milestones:</b> <span style='color:var(--positive,#1c6b45);font-weight:700;'>{p_st} – {p_en} ({curr_md}–{p_lord})</span> — "
                f"Auspicious family milestones, children's accomplishments, and domestic happiness."
            )

    elif code == "D24":
        # Learning
        l_lord, l_st, l_en, l_st_d, l_en_d = find_target_ad(["Mercury", "Jupiter", h5_lord, h4_lord, "Sun"])
        return (
            f"<b>Current Phase ({curr_md}–{curr_ad_lord}, until {curr_ad_end_fmt}):</b> "
            f"Focused self-study, mastering specialized knowledge, and refining technical expertise.<br>"
            f"<b>Academic Distinction & Professional Certification:</b> <span style='color:var(--positive,#1c6b45);font-weight:700;'>{l_st} – {l_en} ({curr_md}–{l_lord})</span> — "
            f"Major certifications, published research, and intellectual accolades."
        )

    elif code == "D4":
        # Home & Property
        h12_lord = get_h_lord(12)
        prop_lord, prop_st, prop_en, prop_st_d, prop_en_d = find_target_ad(["Mars", "Venus", h4_lord, "Jupiter", h12_lord, "Rahu"])
        return (
            f"<b>Current Phase ({curr_md}–{curr_ad_lord}, until {curr_ad_end_fmt}):</b> "
            f"Domestic organizing, researching properties, and maintaining residential peace.<br>"
            f"<b>Prime Property Acquisition & Upgrades:</b> <span style='color:var(--positive,#1c6b45);font-weight:700;'>{prop_st} – {prop_en} ({curr_md}–{prop_lord})</span> — "
            f"Highly favorable window for acquiring residential property, vehicles, or upgrading home comforts."
        )

    elif code == "D30":
        # Health
        if is_child:
            rec_lord, rec_st, rec_en, rec_st_d, rec_en_d = find_target_ad(["Mercury", "Jupiter", "Venus", "Moon"])
            return (
                f"<b>Current Phase ({curr_md}–{curr_ad_lord}):</b> Establishing robust immunity, steady nutrition, and regular rest rhythms.<br>"
                f"<b>Peak Vitality & Growth Window:</b> <span style='color:var(--positive,#1c6b45);font-weight:700;'>{rec_st} – {rec_en} ({curr_md}–{rec_lord})</span> — "
                f"Strong physical stamina and energetic balance."
            )
        else:
            rec_lord, rec_st, rec_en, rec_st_d, rec_en_d = find_target_ad(["Jupiter", "Venus", "Sun", "Mercury", "Moon"])
            return (
                f"<b>Current Phase ({curr_md}–{curr_ad_lord}, until {curr_ad_end_fmt}):</b> "
                f"Prioritizing restorative sleep, digestive wellness, and conscious stress-relief.<br>"
                f"<b>Peak Vitality & Rejuvenation Window:</b> <span style='color:var(--positive,#1c6b45);font-weight:700;'>{rec_st} – {rec_en} ({curr_md}–{rec_lord})</span> — "
                f"Rejuvenated energy, high physical stamina, and deep bodily renewal."
            )

    elif code == "D3":
        # Siblings & Initiative
        if is_child:
            sp_lord, sp_st, sp_en, sp_st_d, sp_en_d = find_target_ad(["Mercury", "Jupiter", "Venus", "Moon"])
            return (
                f"<b>Current Phase ({curr_md}–{curr_ad_lord}):</b> Encouraging creative play, communication, and motor coordination.<br>"
                f"<b>Expressive Breakthrough Window:</b> <span style='color:var(--positive,#1c6b45);font-weight:700;'>{sp_st} – {sp_en} ({curr_md}–{sp_lord})</span> — "
                f"Confident self-expression and clear communication."
            )
        else:
            dr_lord, dr_st, dr_en, dr_st_d, dr_en_d = find_target_ad([bk, "Mars", h3_lord, "Mercury", "Venus"])
            return (
                f"<b>Current Phase ({curr_md}–{curr_ad_lord}, until {curr_ad_end_fmt}):</b> "
                f"Steady, deliberate execution on personal projects and supportive relationships with close peers.<br>"
                f"<b>High-Impact Enterprise & Collaborative Venture:</b> <span style='color:var(--positive,#1c6b45);font-weight:700;'>{dr_st} – {dr_en} ({curr_md}–{dr_lord})</span> — "
                f"Bold initiatives, expanding enterprise, and successful ventures."
            )

    elif code == "D12":
        # Parents
        par_lord, par_st, par_en, par_st_d, par_en_d = find_target_ad(["Sun", "Moon", h9_lord, h4_lord, "Jupiter"])
        return (
            f"<b>Current Phase ({curr_md}–{curr_ad_lord}, until {curr_ad_end_fmt}):</b> "
            f"Honoring ancestral values, respecting family elders, and maintaining peaceful family ties.<br>"
            f"<b>Family Milestone & Parental Blessings:</b> <span style='color:var(--positive,#1c6b45);font-weight:700;'>{par_st} – {par_en} ({curr_md}–{par_lord})</span> — "
            f"Auspicious family celebrations, parental backing, and shared domestic milestones."
        )

    else:
        # D1 Core
        core_lord, core_st, core_en, core_st_d, core_en_d = find_target_ad([ak, "Sun", "Jupiter", "Moon", "Mercury"])
        return (
            f"<b>Current Phase ({curr_md}–{curr_ad_lord}, until {curr_ad_end_fmt}):</b> "
            f"Grounded self-realization, inner clarity, and steady personal growth.<br>"
            f"<b>Personal Evolution & Clarity Window:</b> <span style='color:var(--positive,#1c6b45);font-weight:700;'>{core_st} – {core_en} ({curr_md}–{core_lord})</span> — "
            f"Expanding personal confidence, charismatic presence, and decisive life breakthroughs."
        )


def _determine_career_profile(
    d1_lagna: str,
    d1_h10_lord: str,
    d1_h10_lord_house: int,
    d10_lagna: str,
    d10_lord: str,
    d10_lord_house: int,
    strong_planets: list[str],
    amk: str,
) -> tuple[str, list[str], str]:
    """Computes chart-specific suited professional fields, executive archetype, and optimal work style."""
    prominent_planets = set()
    if d1_h10_lord:
        prominent_planets.add(d1_h10_lord)
    if d10_lord:
        prominent_planets.add(d10_lord)
    if amk:
        prominent_planets.add(amk)
    for sp in strong_planets:
        pname = sp.split()[0]
        prominent_planets.add(pname)

    suited_fields: list[str] = []
    archetype = "Strategic Professional & Advisory Specialist"
    work_style = "High-leverage analytical problem-solving and institutional guidance"

    # Identify fields by planetary confluence
    if any(p in prominent_planets for p in ("Mercury", "Rahu", "Saturn")):
        suited_fields.extend([
            "Technology & Software Engineering",
            "Data Analytics, AI & Advanced Systems",
            "Financial Technologies, Quantitative Research & Auditing",
        ])
    if any(p in prominent_planets for p in ("Jupiter", "Sun")):
        suited_fields.extend([
            "Strategic Consulting & Corporate Advisory",
            "Higher Education, Research & Policy Formulation",
            "Institutional Governance, Legal & Ethical Leadership",
        ])
    if any(p in prominent_planets for p in ("Mars", "Saturn")):
        suited_fields.extend([
            "Complex Infrastructure, Supply Chain & Operations",
            "Engineering, Real Estate Architecture & Project Leadership",
            "Defense, Energy & High-Stakes Operations",
        ])
    if any(p in prominent_planets for p in ("Venus", "Moon")):
        suited_fields.extend([
            "Design Architecture, Creative Direction & Media",
            "Healthcare Systems, Public Relations & Human Capital",
            "Luxury Goods, Brand Strategy & Client Experience",
        ])

    # Fallback to ensure distinct high-value fields
    if not suited_fields:
        suited_fields = [
            "Technology & Strategic Data Systems",
            "Executive Advisory & Management Consulting",
            "Financial Analysis, Auditing & Corporate Strategy",
            "Higher Academic Research & Applied Science",
        ]

    # De-duplicate while preserving order
    unique_fields = list(dict.fromkeys(suited_fields))[:4]

    # Archetype determination
    if d1_h10_lord_house in DUSTHANA or d10_lord_house in DUSTHANA:
        archetype = "Specialized Research, Advisory & Deep Technical Authority"
        work_style = "thrives in specialized research, advisory consulting, or deep technical architecture rather than routine bureaucratic desk work"
    elif "Sun" in prominent_planets or "Mars" in prominent_planets:
        archetype = "Executive Leadership, Operations & Institutional Direction"
        work_style = "commands executive accountability, organizational leadership, and high-impact operational strategy"
    elif "Jupiter" in prominent_planets or "Mercury" in prominent_planets:
        archetype = "Strategic Consultant, Knowledge Architect & Advisory Director"
        work_style = "excels in intellectual strategy, mentorship, policy analysis, and complex problem resolution"
    else:
        archetype = "Systems Architect & Strategic Implementation Specialist"
        work_style = "drives systematic execution, structured growth, and long-term institutional value creation"

    return archetype, unique_fields, work_style


def _determine_marriage_profile(
    d1_lagna: str,
    d1_h7_lord: str,
    d1_h7_lord_house: int,
    d9_lagna: str,
    d9_lord: str,
    d9_lord_house: int,
    dk: str,
) -> tuple[str, str, str]:
    """Computes chart-specific marriage partner nature, professional realm, and relationship dynamics."""
    key_ruler = d9_lord or d1_h7_lord or "Venus"

    partner_nature = "supportive, educated, and sensible"
    partner_realm = "professional, analytical, or educational domain"
    dynamics = "mutual intellectual respect and domestic stability"

    if key_ruler in ("Mercury", "Rahu"):
        partner_nature = "intellectually curious, articulate, adaptable, and business-savvy"
        partner_realm = "technology, finance, media, communications, or corporate consulting"
        dynamics = "stimulating intellectual companionship, active dialogue, and shared problem-solving"
    elif key_ruler in ("Jupiter", "Sun"):
        partner_nature = "principled, wise, mature, values-driven, and supportive of higher ideals"
        partner_realm = "education, legal, advisory, executive leadership, or public service"
        dynamics = "deep mutual trust, moral grounding, and shared life purpose (Bhagyodaya)"
    elif key_ruler in ("Venus", "Moon"):
        partner_nature = "gentle, culturally refined, empathetic, and aesthetically oriented"
        partner_realm = "creative arts, design, healthcare, hospitality, or client relations"
        dynamics = "warm emotional security, artistic appreciation, and a harmonious domestic sanctuary"
    elif key_ruler in ("Mars", "Saturn"):
        partner_nature = "pragmatic, hardworking, disciplined, loyal, and action-oriented"
        partner_realm = "engineering, operations, finance, real estate, or administrative governance"
        dynamics = "practical life building, enduring loyalty, and steady"

    return partner_nature, partner_realm, dynamics


def build_divisional_insights(pc: dict, lang: str = "en") -> list[DivisionalInsight]:
    """Generates warm, highly specific, predictive observations for all 9 key vargas with collapsible proof and domain-specific dasha timing."""
    this_yr = date.today().year

    dob_str = str(pc.get("meta", {}).get("birth_date") or pc.get("meta", {}).get("dob") or "")
    birth_year = int(dob_str[:4]) if (len(dob_str) >= 4 and dob_str[:4].isdigit()) else 2000
    current_age = this_yr - birth_year

    DOMAIN_ID_MAP = {
        "D1": "domain-self",
        "D10": "domain-career",
        "D9": "domain-marriage",
        "D2": "domain-wealth",
        "D7": "domain-children",
        "D24": "domain-learning",
        "D4": "domain-home",
        "D30": "domain-health",
        "D3": "domain-siblings",
        "D12": "domain-parents",
    }
    codes = ["D1", "D10", "D9", "D2", "D7", "D24", "D4", "D30", "D3", "D12"]
    insights: list[DivisionalInsight] = []

    d1_lagna = _get_varga_lagna(pc, "D1")
    moon_sign = _get_varga_planet_sign(pc, "D1", "Moon")
    nakshatra = (pc.get("planets", {}).get("Moon", {}) or {}).get("nakshatra", "")

    # Jaimini Karakas
    jaimini = pc.get("jaimini", {})
    amk = jaimini.get("amk", "")
    dk = jaimini.get("dk", "")
    pk = jaimini.get("pk", "")

    # D1 placements for contextual cross-reference
    d1_planets = pc.get("planets", {})
    d1_h2_lord = SIGN_LORDS.get(house_sign(d1_lagna, 2), "") if d1_lagna else ""
    d1_h2_lord_house = d1_planets.get(d1_h2_lord, {}).get("house", 0) if d1_h2_lord else 0
    d1_h7_lord = SIGN_LORDS.get(house_sign(d1_lagna, 7), "") if d1_lagna else ""
    d1_h7_lord_house = d1_planets.get(d1_h7_lord, {}).get("house", 0) if d1_h7_lord else 0
    d1_h10_lord = SIGN_LORDS.get(house_sign(d1_lagna, 10), "") if d1_lagna else ""
    d1_h10_lord_house = d1_planets.get(d1_h10_lord, {}).get("house", 0) if d1_h10_lord else 0
    d1_h5_lord = SIGN_LORDS.get(house_sign(d1_lagna, 5), "") if d1_lagna else ""
    d1_h5_lord_house = d1_planets.get(d1_h5_lord, {}).get("house", 0) if d1_h5_lord else 0

    # Dasha context
    vim = pc.get("vimshottari", {})
    curr_md_obj = vim.get("current_md", {})
    curr_md = curr_md_obj.get("md_lord", "") if isinstance(curr_md_obj, dict) else str(curr_md_obj or "")
    md_seq = vim.get("sequence", [])
    if not curr_md:
        for s in md_seq:
            if s.get("status") == "current":
                curr_md = s.get("md_lord", "") or s.get("planet", "")
                break

    curr_ad_list = vim.get("current_md_antardashas", [])
    curr_ad_name = ""
    curr_ad_end = ""
    for a in curr_ad_list:
        if a.get("status") == "current":
            curr_ad_name = a.get("ad_lord", "")
            raw_end = a.get("end", "")
            curr_ad_end = _format_month_year(raw_end)
            break

    # Adulthood Mahadasha for milestones
    adulthood_md = ""
    adulthood_start_yr = 2036
    adulthood_end_yr = 2052
    for item in md_seq:
        s_date = str(item.get("start") or "")
        e_date = str(item.get("end") or "")
        lord_name = item.get("md_lord") or item.get("planet") or "Jupiter"
        if s_date and len(s_date) >= 4:
            s_yr = int(s_date[:4])
            if (s_yr - (this_yr - current_age)) >= 18 and not adulthood_md:
                adulthood_md = lord_name
                adulthood_start_yr = s_yr
                adulthood_end_yr = int(e_date[:4]) if (e_date and len(e_date) >= 4) else (s_yr + 16)
                break
    if not adulthood_md:
        adulthood_md = "Jupiter"

    lang_code = str(lang or "").lower().strip()
    is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")
    v_meta_dict = VARGA_META_TENGLISH if is_tenglish else (VARGA_META_HINGLISH if is_hinglish else VARGA_META)

    for code in codes:
        meta = v_meta_dict.get(code, {})
        v_lagna = _get_varga_lagna(pc, code)
        if not v_lagna:
            continue

        lagna_idx = sign_index(v_lagna)
        lord = SIGN_LORDS.get(v_lagna, "")
        lord_sign = _get_varga_planet_sign(pc, code, lord)
        lord_dig = get_dignity(lord, lord_sign) if (lord and lord_sign) else ""
        lord_house = ((sign_index(lord_sign) - lagna_idx) % 12 + 1) if (lord_sign and v_lagna) else 1

        strong_planets = []
        debilitated_planets = []
        trik_planets = []
        all_placements = []

        for p in PLANETS:
            ps = _get_varga_planet_sign(pc, code, p)
            if not ps:
                continue
            h = ((sign_index(ps) - lagna_idx) % 12 + 1)
            dig = get_dignity(p, ps)
            dig_label = dig.replace('_', ' ').title() if dig else "Neutral"
            all_placements.append(f"{p} in {ps} (House {h}, {dig_label})")

            if dig in ("exalted", "moolatrikona", "own_sign"):
                strong_planets.append(f"{p} ({dig.replace('_', ' ').title()})")
            elif dig == "debilitated":
                debilitated_planets.append(f"{p} (Debilitated)")
            if h in DUSTHANA:
                trik_planets.append(f"{p} (House {h})")

        is_lord_in_trik = lord_house in DUSTHANA
        is_lord_debilitated = lord_dig == "debilitated"

        if is_lord_in_trik or is_lord_debilitated or len(debilitated_planets) >= 2 or len(trik_planets) >= 3:
            strength = "weak" if (is_lord_in_trik and is_lord_debilitated) else "mixed"
        elif lord_dig in ("exalted", "moolatrikona", "own_sign") and not is_lord_in_trik and len(strong_planets) >= 2:
            strength = "strong"
        else:
            strength = "mixed"

        timeline_str = _build_domain_specific_timeline(
            pc=pc,
            code=code,
            current_age=current_age,
            curr_md=curr_md,
            curr_ad_name=curr_ad_name,
            curr_ad_end=curr_ad_end,
            adulthood_md=adulthood_md,
            adulthood_start_yr=adulthood_start_yr,
            lang=lang,
        )

        headline, prediction, remedy = _interpret_varga_concrete(
            code=code,
            v_lagna=v_lagna,
            lord=lord,
            lord_sign=lord_sign,
            lord_house=lord_house,
            lord_dig=lord_dig,
            strong_planets=strong_planets,
            debilitated_planets=debilitated_planets,
            trik_planets=trik_planets,
            strength=strength,
            d1_lagna=d1_lagna,
            moon_sign=moon_sign,
            nakshatra=nakshatra,
            pc=pc,
            current_age=current_age,
            d1_h2_lord_house=d1_h2_lord_house,
            d1_h7_lord_house=d1_h7_lord_house,
            d1_h10_lord=d1_h10_lord,
            d1_h10_lord_house=d1_h10_lord_house,
            d1_h5_lord_house=d1_h5_lord_house,
            amk=amk,
            dk=dk,
            lang=lang,
        )

        # Build collapsible technical proof string
        proof_parts = [f"Ascendant (Lagna): <b>{v_lagna}</b>"]
        if lord and lord_sign:
            dig_str = f" ({lord_dig.replace('_', ' ').title()})" if lord_dig else ""
            proof_parts.append(f"Ruler: <b>{lord}</b> in {lord_sign} (House {lord_house}){dig_str}")
        if strong_planets:
            proof_parts.append(f"Dignified: <b>{', '.join(strong_planets)}</b>")
        if debilitated_planets:
            proof_parts.append(f"Debilitated: <b>{', '.join(debilitated_planets)}</b>")
        if trik_planets:
            proof_parts.append(f"Dusthana: <b>{', '.join(trik_planets)}</b>")

        evidence_str = " &nbsp;|&nbsp; ".join(proof_parts[:4]) + f"<br><span style='color:var(--text-muted,#6a7080);font-size:0.74rem;'>All Placements: {'; '.join(all_placements)}</span>"

        insights.append(
            DivisionalInsight(
                code=code,
                name=meta.get("name", code),
                governs=meta.get("governs", ""),
                domain_id=DOMAIN_ID_MAP.get(code, f"domain-{code.lower()}"),
                lagna_sign=v_lagna,
                lord=lord,
                lord_sign=lord_sign,
                lord_house=lord_house,
                lord_dignity=lord_dig,
                strength=strength,
                headline=headline,
                prediction=prediction,
                timeline=timeline_str,
                remedy=remedy,
                evidence=evidence_str,
            )
        )

    return insights


def _interpret_varga_concrete(
    code: str,
    v_lagna: str,
    lord: str,
    lord_sign: str,
    lord_house: int,
    lord_dig: str,
    strong_planets: list[str],
    debilitated_planets: list[str],
    trik_planets: list[str],
    strength: str,
    d1_lagna: str,
    moon_sign: str,
    nakshatra: str,
    pc: dict,
    current_age: int,
    d1_h2_lord_house: int,
    d1_h7_lord_house: int,
    d1_h10_lord: str,
    d1_h10_lord_house: int,
    d1_h5_lord_house: int,
    amk: str,
    dk: str,
    lang: str = "en",
) -> tuple[str, str, str]:
    """Generates rich, highly specific, practical life interpretations for each divisional chart."""
    div_dict = pc.get("divisional", {})
    d1_planets = pc.get("planets", {})
    # The Hinglish / Telugu branches below are fixed positive scripts that do not
    # change with the chart. This block is rendered from the chart-derived English
    # text for every language; the model-written prose carries the language.
    is_hinglish = False
    is_tenglish = False
    import chart_lines as CL

    reading_parts: list[str] = []
    remedy_planet = lord
    remedy_type = "strengthen"
    remedy_reason = f"To Harmonize {lord}"

    if code == "D1":
        if is_hinglish:
            headline = f"Mool Swabhav Aur Vyaktigat Urja ({v_lagna} Rising)"
            reading_parts.append(
                f"Aapki janma kundli ek gambhir, samajhdar aur vyavaharik vyaktitva (<b>{v_lagna} Rising</b>) darshati hai. "
                f"Moon in <b>{moon_sign} under {nakshatra}</b> ke sath, aapka alert mind har cheez ko jaldi samajhta hai."
            )
            if lord_house in DUSTHANA:
                reading_parts.append(
                    f"Aapka lagnesh (<b>{lord}</b>) {ORDINALS.get(lord_house, '8th')} bhav mein sthit hone ke karan, aapki safalta aantarik patience aur deep research se banti hai."
                )
                remedy_type = "dusthana"
                remedy_reason = f"To Support Your Ruling Planet ({lord})"
            else:
                reading_parts.append(
                    f"Aapka lagnesh (<b>{lord}</b>) {ORDINALS.get(lord_house, '1st')} bhav mein sthit hokar aapko physical stamina, aatmavishwas aur svatantrata pradan karta hai."
                )
        elif is_tenglish:
            headline = f"Moola Swabhavam Mariyu Vyakthigatha Balam ({v_lagna} Rising)"
            reading_parts.append(
                f"Mee janma kundali oka vivekamaina, chulakana mariyu vyavaharamaina vyakthithvam (<b>{v_lagna} Rising</b>) chupisthondi. "
                f"Moon in <b>{moon_sign} under {nakshatra}</b> tho, mee alert mind vishayalani thondaraga grahisthundi."
            )
            if lord_house in DUSTHANA:
                reading_parts.append(
                    f"Mee lagnaadhipathi (<b>{lord}</b>) {ORDINALS.get(lord_house, '8th')} bhavam lo undadam valla, mee vijayam deep research mariyu patience tho sadhistharu."
                )
                remedy_type = "dusthana"
                remedy_reason = f"To Support Your Ruling Planet ({lord})"
            else:
                reading_parts.append(
                    f"Mee lagnaadhipathi (<b>{lord}</b>) {ORDINALS.get(lord_house, '1st')} bhavam lo undi meeku physical stamina, aathmavishwasam mariyu independence istharu."
                )
        else:
            headline = f"Core Nature & Personal Vitality ({v_lagna} Rising)"
            reading_parts.append(
                f"{_lagna_sentence(v_lagna)} (<b>{v_lagna} Rising</b>). "
                f"Your Moon is in <b>{moon_sign} under {nakshatra}</b>, which sets the tone of your mind and moods."
            )
            if lord_house in DUSTHANA:
                reading_parts.append(
                    f"Because your ruling planet (<b>{lord}</b>) is placed in the {ORDINALS.get(lord_house, '8th')} house, your journey builds deep resilience, research capability, and inner patience over time rather than instant outer results."
                )
                remedy_type = "dusthana"
                remedy_reason = f"To Support Your Ruling Planet ({lord})"
            else:
                reading_parts.append(_graded(
                    pc, [lord],
                    f"Your ruling planet (<b>{lord}</b>) sits well in the {ORDINALS.get(lord_house, '1st')} house, giving you steady physical vitality, natural independence, and self-confidence.",
                    f"Your ruling planet (<b>{lord}</b>) sits in the {ORDINALS.get(lord_house, '1st')} house with mixed support, so energy and self-confidence come in good stretches and drained ones.",
                    f"Your ruling planet (<b>{lord}</b>) is under strain in the {ORDINALS.get(lord_house, '1st')} house, so energy and confidence need deliberate protection."))

    elif code == "D2":
        if is_hinglish:
            headline = f"Dhan, Bachat Aur Aarthik Sthirta (Hora · D2)"
            reading_parts.append(
                f"Yeh varga aapki aarthik sthirta, dhan bachat aur asset accumulation ko darshata hai. "
                f"Aapki kundli sanket deti hai ki dhan bina kisi short-cut ke vyavasthit roop se compound hota hai."
            )
            if strong_planets:
                reading_parts.append(
                    f"Kundli mein shubh grah ({', '.join(strong_planets)}) ke sahyog se aapki financial holding capacity aur bachat samay ke sath majboot hoti hai."
                )
        elif is_tenglish:
            headline = f"Dhanam, Podupu Mariyu Aarthika Sthiratha (Hora · D2)"
            reading_parts.append(
                f"Ee vargamu mee aarthika sthiratha, podupu mariyu aasthi vikasam chupisthondi. "
                f"Kundali short-cuts lekunda kramamga wealth compound avuthundani sanketham isthondi."
            )
            if strong_planets:
                reading_parts.append(
                    f"Shubha grahala ({', '.join(strong_planets)}) sahayatho mee financial holding capacity mariyu savings samayam tho paatu balapadathayi."
                )
        else:
            headline = f"Wealth, Savings & Financial Stability"
            hora_nature = "strategic asset accumulation and compounding investments"
            if v_lagna in ("Leo", "Aries", "Sagittarius", "Gemini", "Libra", "Aquarius"):
                hora_nature = "active enterprise, self-made initiatives, leadership authority, and bold professional ventures"
            else:
                hora_nature = "resource preservation, liquid savings, real estate assets, and steady wealth compounding"

            reading_parts.append(
                f"This division maps your money instincts, asset retention, and long-term capital stability. "
                + _graded(
                    pc, [CL.lord_of(pc, 2), CL.lord_of(pc, 11)],
                    f"Your chart indicates that wealth compounds most reliably through <b>{hora_nature}</b> rather than speculative shortcuts.",
                    f"Your chart indicates that wealth builds best, though unevenly, through <b>{hora_nature}</b> rather than speculative shortcuts.",
                    f"Your chart indicates that money needs careful pacing, and is best built through <b>{hora_nature}</b> rather than speculative shortcuts.")
            )
            if strong_planets:
                reading_parts.append(
                    f"With favorable planetary backing ({', '.join(strong_planets)}) in this division, your capacity to hold resources, manage liquidity, and secure family independence strengthens steadily across your career years."
                )
        remedy_planet = "Jupiter"
        remedy_reason = "To Boost Wealth & Prosperity (Guru Upaya)"

    elif code == "D3":
        if is_hinglish:
            headline = f"Sahas, Initiative Aur Bhai-Behen (Drekkana · D3)"
            reading_parts.append(
                f"Drekkana chart (D3) <b>vyaktigat sahas (*Parakrama*), bhai-behen sambandh (*Bhratru*) aur dainik initiative</b> ko darshata hai. "
                f"Aapke andar kisi bhi karya ko shuru karne aur use poora karne ka dridh sankalp hai."
            )
        elif is_tenglish:
            headline = f"Dhairyam, Initiative Mariyu Sahodharulu (Drekkana · D3)"
            reading_parts.append(
                f"Drekkana chart (D3) <b>vyakthigatha dhairyam (*Parakrama*), sahodharula sambandhalu (*Bhratru*) mariyu initiative</b> chupisthondi. "
                f"Mee loni sankalpa balam tho panulanu vijayavanthamga poorthi cheyagalaru."
            )
        else:
            headline = f"Courage, Siblings & Everyday Initiative"
            courage_str = _graded(
                pc, ["Mars", CL.lord_of(pc, 3)],
                "Your chart shows strong natural courage, decisive execution, and the ability to take self-directed initiative on ambitious goals.",
                "Your courage and initiative are real but uneven: bold when you are sure, hesitant when the stakes feel unclear.",
                "Courage and initiative do not come easily in your chart; you act best after careful preparation rather than on impulse.")
            if lord_house in (3, 6, 10, 11):
                courage_str = "Your chart confirms powerful upachaya drive (*Parakrama*), indicating that your determination and ability to overcome resistance grow stronger with every challenge."
            elif lord_house in DUSTHANA:
                courage_str = "Your personal enterprise develops through thoughtful strategy, research, and patient effort rather than hasty actions."

            sibling_str = _graded(
                pc, [CL.lord_of(pc, 3), "Mars"],
                "The ruler of your siblings area is well placed, which points to mutual backing, loyalty and a collaborative spirit with siblings and close peers.",
                "The ruler of your siblings area is placed with mixed support, so ties with siblings and peers are warm at times and distant at others.",
                "The ruler of your siblings area is under strain, so these ties ask for patience and clear communication, and self-reliance serves you well.")

            motor_str = _graded(
                pc, ["Mars"],
                "Mars is well placed in your chart, which favours good physical coordination and the stamina to carry projects through.",
                "Mars gives you stamina in bursts; steady routines work better than sprints.",
                "Mars is under strain in your chart, so physical pacing, warm-ups and avoiding overexertion matter.")
            if "Saturn" in [tp.split()[0] for tp in trik_planets] or "Rahu" in [tp.split()[0] for tp in trik_planets]:
                motor_str = "Physical pacing and manual stamina benefit from steady warmups, regular physical exercise, and avoiding erratic overexertion."

            reading_parts.extend([
                f"The Drekkana division maps <b>personal courage (*Parakrama*), sibling relationships (*Bhratru*), everyday enterprise, and physical motor coordination</b>.",
                courage_str,
                sibling_str,
                motor_str
            ])
        remedy_planet = "Mars"
        remedy_reason = "To Boost Initiative & Courage (Mangal Upaya)"

    elif code == "D4":
        if is_hinglish:
            headline = f"Ghar, Sampatti, Vahan Aur Sthirta (Chaturthamsha · D4)"
            reading_parts.append(
                "Chaturthamsha (D4) <b>manasik shanti (*Griha Sukha*), fixed property, bhumi labh aur videsh ya sthan parivartan</b> ko darshata hai. "
                "Aapki kundli mein aage chal kar sthayi nivas aur residential property banane ke anukool yog hain."
            )
        elif is_tenglish:
            headline = f"Illu, Aasthi, Vahanam Mariyu Sthiratha (Chaturthamsha · D4)"
            reading_parts.append(
                "Chaturthamsha (D4) <b>manasika prasanthatha (*Griha Sukha*), fixed property, sthala labham mariyu sthana maarpu</b> chupisthondi. "
                "Mee kundali lo sthiramaina illu mariyu residential property pondadaniki anukoolamaina yogalu unnai."
            )
        else:
            headline = f"Home, Land, Vehicles & Relocation"
            reading_parts.append(
                "The Chaturthamsha division maps <b>domestic peace (*Griha Sukha*), fixed property, land acquisition, conveyances (*Vahana*), and geographical relocation / foreign settlement (*Videsh Vasa*)</b>. "
                + _graded(
                    pc, [CL.lord_of(pc, 4), "Venus"],
                    "The ruler of your home area is well placed, which supports a solid promise of owning a home, comfortable conveyances and an enduring personal sanctuary.",
                    "The ruler of your home area has mixed support, so a home and conveyances come through steady effort, with some delays or compromises.",
                    "The ruler of your home area is under strain, so property and a settled home take longer and need careful, well-checked decisions.")
            )
            if strong_planets:
                reading_parts.append(
                    f"<br><br><b>Property & Asset Fortification:</b> Well-placed indicators ({', '.join(strong_planets)}) support significant land appreciation, smooth property transactions, and domestic comfort."
                )

            d1_h4_lord = SIGN_LORDS.get(house_sign(d1_lagna, 4), "") if d1_lagna else ""
            d1_h4_lord_house = d1_planets.get(d1_h4_lord, {}).get("house", 0) if d1_h4_lord else 0
            d1_h9_lord = SIGN_LORDS.get(house_sign(d1_lagna, 9), "") if d1_lagna else ""
            d1_h9_lord_house = d1_planets.get(d1_h9_lord, {}).get("house", 0) if d1_h9_lord else 0
            d1_h12_lord = SIGN_LORDS.get(house_sign(d1_lagna, 12), "") if d1_lagna else ""
            d1_h12_lord_house = d1_planets.get(d1_h12_lord, {}).get("house", 0) if d1_h12_lord else 0
            rahu_h = d1_planets.get("Rahu", {}).get("house", 0)
            moon_h = d1_planets.get("Moon", {}).get("house", 0)
            moon_s = d1_planets.get("Moon", {}).get("sign", "")

            MOVABLE = {"Aries", "Cancer", "Libra", "Capricorn"}
            WATERY = {"Cancer", "Scorpio", "Pisces"}

            has_foreign_settlement = (
                d1_h4_lord_house in (9, 12, 8, 3) or
                d1_h12_lord_house in (4, 9, 1) or
                rahu_h in (9, 12, 7, 4) or
                (d1_h4_lord_house in (1, 10) and d1_h12_lord_house in (10, 11))
            )
            has_frequent_travel = (
                d1_h9_lord_house in (9, 10, 12, 1, 3) or
                moon_h in (3, 7, 9, 12) or
                moon_s in (MOVABLE | WATERY) or
                rahu_h in (3, 11)
            )

            if has_foreign_settlement:
                reading_parts.append(
                    f"<br><br><b>Geographical Relocation & Foreign Settlement Potential:</b> "
                    f"Strong classical connections between 4th house roots and 9th/12th house indicators confirm <b>favorable promise for living away from your birthplace, multi-city living, or foreign settlement</b>. "
                    f"Your fortune expands significantly when engaging with distant markets, international projects, or establishing residency across regions during supportive dasha phases."
                )
            elif has_frequent_travel:
                reading_parts.append(
                    f"<br><br><b>Travel, Mobility & Professional Expansion:</b> "
                    f"Active 9th and 3rd house indicators indicate frequent long-distance travel, dynamic mobility, and business/educational journeys. "
                    f"Your chart favors maintaining a stable domestic base while undertaking purposeful international or inter-city travel."
                )
            else:
                reading_parts.append(
                    f"<br><br><b>Home Foundation & Asset Anchoring:</b> "
                    f"Your chart reflects deep rootedness in your native region with strong domestic peace. "
                    f"Property acquisitions bring maximum stability when invested in well-established residential locations."
                )

        remedy_planet = "Mars"
        remedy_reason = "To Energize Land & Property Assets (Bhoomi Upaya)"

    elif code == "D7":
        if is_hinglish:
            headline = f"Santan, Parivar Aur Vansh (Saptamsha · D7)"
            reading_parts.append(
                f"Yeh varga santan sukh, parivarik vistar aur vansh vriddhi ka sanket deta hai. "
                f"Kundli mein santan se santushti, sneh aur parivarik anand ke shubh sanket hain."
            )
        elif is_tenglish:
            headline = f"Pillalu, Kutumbam Mariyu Vamsham (Saptamsha · D7)"
            reading_parts.append(
                f"Ee vargamu santhana soukhyam, kutumba vikasam mariyu vamsha vriddhi sankethalu isthondi. "
                f"Kundali lo santhanam tho santhosham mariyu kutumba aanandam anukoolanga unnai."
            )
        else:
            headline = f"Children, Family Lineage & Progeny"
            d7_moon = div_dict.get("D7", {}).get("Moon", "")
            d7_jup = div_dict.get("D7", {}).get("Jupiter", "")
            d7_ven = div_dict.get("D7", {}).get("Venus", "")

            d7_strong_list = []
            if d7_moon in ("Cancer", "Taurus"):
                d7_strong_list.append(f"Moon in {d7_moon}")
            if d7_jup in ("Sagittarius", "Pisces", "Cancer"):
                d7_strong_list.append(f"Jupiter in {d7_jup}")
            if d7_ven in ("Taurus", "Libra", "Pisces"):
                d7_strong_list.append(f"Venus in {d7_ven}")
            if "own_sign" in lord_dig or "exalted" in lord_dig:
                d7_strong_list.append(f"{lord} in {lord_sign} ({lord_dig.replace('_', ' ').title()})")

            if d7_strong_list:
                guardians_str = f"The key guardians of progeny ({', '.join(d7_strong_list)}) are deeply fortified in this chart."
                reading_parts.append(
                    f"This division reveals an <b>exceptionally fertile, blessed, and strong foundational promise for children and family continuation</b>. "
                    f"{guardians_str} "
                    f"Classical confirmation affirms joyful, healthy children and family happiness that unfolds naturally after marriage in adulthood."
                )
            else:
                reading_parts.append(_graded(
                    pc, [CL.lord_of(pc, 5), "Jupiter"],
                    "The indicators for children are well placed, which supports joy and fulfilment through children and family continuation.",
                    "The indicators for children have mixed support, so family growth comes with both joy and some waiting or adjustment.",
                    "The indicators for children are under strain, so this area asks for patience and good health care, and timing matters more than speed."))
        remedy_planet = "Jupiter"
        remedy_reason = "To Bless Progeny & Family Growth (Santan Gopal Upaya)"

    elif code == "D9":
        if is_hinglish:
            headline = f"Vivah, Jeevansathi Aur Bhagyodaya (Navamsha · D9)"
            reading_parts.append(
                f"Navamsha kundli jeevansathi, vaivahik sukh aur bhagyodaya ko darshati hai. "
                f"Aapki kundli ek samajhdar, supportive jeevansathi aur vivah ke baad aarthik v manasik sthirta ka sanket deti hai."
            )
        elif is_tenglish:
            headline = f"Vivaham, Jeevithabhagswami Mariyu Bhagyodayam (Navamsha · D9)"
            reading_parts.append(
                f"Navamsha kundali jeevithabhagswami, vaivahika soukhyam mariyu bhagyodayam chupisthondi. "
                f"Mee kundali vivekamaina jeevithabhagswami mariyu vivaham tharuvatha aarthika, manasika sthiratha sankethalu isthondi."
            )
        else:
            headline = f"Marriage, Life Partner & Soul Purpose"
            partner_nature, partner_realm, dynamics = _determine_marriage_profile(
                d1_lagna=d1_lagna,
                d1_h7_lord=SIGN_LORDS.get(house_sign(d1_lagna, 7), ""),
                d1_h7_lord_house=d1_h7_lord_house,
                d9_lagna=v_lagna,
                d9_lord=lord,
                d9_lord_house=lord_house,
                dk=dk,
            )
            reading_parts.append(
                f"The Navamsha division maps life partnership, marital harmony, and inner destiny (Bhagyodaya). "
                f"Your chart indicates {_a_an(partner_nature)} <b>{partner_nature}</b> life partner, likely connected with <b>{partner_realm}</b>. "
                f"The relationship provides {dynamics}. "
                + _graded(
                    pc, [CL.lord_of(pc, 7), "Venus"],
                    "Your partnership indicators are well placed, which supports emotional stability and shared values.",
                    "Your partnership indicators have mixed support, so the relationship brings closeness along with adjustments to make.",
                    "Your partnership indicators are under strain, so patience, clear communication and timing matter in this area.")
            )
        remedy_planet = "Venus"
        remedy_reason = "To Foster Harmony in Relationships (Shukra Upaya)"

    elif code == "D10":
        if is_hinglish:
            headline = f"Karyakshetra, Safalta Aur Pratishtha (Dashamsha · D10)"
            reading_parts.append(
                f"Yeh varga aapke career, professional status aur leadership abilities ko darshata hai.<br><br>"
                f"<b>Anukool Karyakshetra:</b> Grah sthiti ke anusar aapko specialized mastery, structured execution aur executive responsibility mein safalta milti hai."
            )
        elif is_tenglish:
            headline = f"Karyakshetram, Vijayam Mariyu Gouravam (Dashamsha · D10)"
            reading_parts.append(
                f"Ee vargamu mee career, professional status mariyu leadership abilities chupisthondi.<br><br>"
                f"<b>Anukoolamaina Rangamu:</b> Graha sthiti prakaram meeku specialized mastery, structured execution mariyu executive responsibility lo manchi vijayam vasthundi."
            )
        else:
            headline = f"Career, Leadership & Professional Status"
            archetype, suited_fields, work_style = _determine_career_profile(
                d1_lagna=d1_lagna,
                d1_h10_lord=d1_h10_lord,
                d1_h10_lord_house=d1_h10_lord_house,
                d10_lagna=v_lagna,
                d10_lord=lord,
                d10_lord_house=lord_house,
                strong_planets=strong_planets,
                amk=amk,
            )
            fields_bullet = ", ".join([f"<b>{f}</b>" for f in suited_fields])
            reading_parts.append(
                f"Your professional karma operates as {_a_an(archetype)} <b>{archetype}</b>. Your natural work style {work_style}.<br><br>"
                f"<b>Career Fields Your Chart Points To:</b> {fields_bullet}. "
                + _graded(
                    pc, [CL.lord_of(pc, 10), "Sun"],
                    "Your career indicators are well placed, so building expertise early tends to bring respect and responsibility.",
                    "Your career indicators have mixed support, so progress comes in steps with some slow stretches.",
                    "Your career indicators are under strain, so progress asks for patience, and steady skill-building matters more than quick promotion.")
            )
        remedy_planet = "Sun"
        remedy_type = "dusthana" if d1_h10_lord_house in DUSTHANA else "strengthen"
        remedy_reason = "To Strengthen Professional Authority (Surya Upaya)"

    elif code == "D12":
        if is_hinglish:
            headline = f"Mata-Pita Aur Parivarik Ashirwad (Dwadashamsha · D12)"
            reading_parts.append(
                f"Yeh kundli parivarik sanskar, mata-pita ka sahyog aur ancestral blessings ko darshati hai. "
                f"Buzurgo ka samman aur parivarik mulya aapko jeevan mein sakaratmak urja aur shanti dete hain."
            )
        elif is_tenglish:
            headline = f"Thallidandrulu Mariyu Poorveekula Ashirwadam (Dwadashamsha · D12)"
            reading_parts.append(
                f"Ee kundali kutumba sanskaralu, thallidandrula sahakaram mariyu ancestral blessings chupisthondi. "
                f"Peddala gouravam mariyu parivara moolalu meeku jeevitham lo shantini, positivity ni isthayi."
            )
        else:
            headline = f"Family Roots & Parental Blessings"
            reading_parts.append(
                _graded(
                    pc, ["Sun", "Moon", CL.lord_of(pc, 9)],
                    "The indicators for parents and family roots are well placed, which classically points to support and good grounding from your family.",
                    "The indicators for parents and family roots have mixed support, which classically points to a family bond with both warmth and friction.",
                    "The indicators for parents and family roots are under strain, which classically points to a harder road with family, where you build your own footing.")
            )
            if strong_planets:
                reading_parts.append(
                    f"Fortified placements ({', '.join(strong_planets)}) in D12 indicate noble lineage and deep parental blessings."
                )
        remedy_planet = "Sun"
        remedy_reason = "To Honor Ancestral Blessings (Pitru Upaya)"

    elif code == "D24":
        if is_hinglish:
            headline = f"Shiksha, Gyan Aur Intellectual Growth (Chaturvimshamsha · D24)"
            reading_parts.append(
                f"D24 chart aapki conceptual grasping power, analytical thinking aur complex vishayon ko sikhne ki shamta darshata hai. "
                f"Niyamit abhyas se aap technical, management ya professional certifications mein utkrisht safalta pa sakte hain."
            )
        elif is_tenglish:
            headline = f"Chaduvu, Gyanam Mariyu Intellectual Growth (Chaturvimshamsha · D24)"
            reading_parts.append(
                f"D24 chart mee conceptual grasping power, analytical thinking mariyu kottha vishayalanu nerchukune shaktini chupisthondi. "
                f"Regular practice tho technical, management leda professional certifications lo goppa safalatha pondavachu."
            )
        else:
            headline = f"Education, Memory & Intellectual Mastery"
            reading_parts.append(
                _graded(
                    pc, ["Mercury", CL.lord_of(pc, 5)],
                    "Your learning indicators are well placed, which supports strong grasp, analytical thinking and mastery of complex subjects.",
                    "Your learning indicators have mixed support, so you learn well when the subject interests you and the routine is steady.",
                    "Your learning indicators are under strain, so learning comes through patient repetition and structure rather than speed.")
            )
            if strong_planets:
                reading_parts.append(
                    f"Fortified planets ({', '.join(strong_planets)}) in D24 indicate exceptional memory retention, academic distinction, and intellectual authority."
                )
        remedy_planet = "Mercury"
        remedy_reason = "To Sharpen Memory & Academic Focus (Saraswati Upaya)"

    elif code == "D30":
        disease_res = {}
        conf = {}
        try:
            from goel_disease_analysis import analyze_disease_chart
            from goel_disease_confluence import build_health_confluence
            disease_res = analyze_disease_chart(pc)
            conf = build_health_confluence(disease_res, pc)
        except Exception:
            pass

        d30_dict = div_dict.get("D30", {})
        d30_merc_sign = d30_dict.get("Mercury", "")
        d30_malefics = [m for m in ("Rahu", "Ketu", "Saturn", "Mars", "Sun") if d30_dict.get(m) == d30_merc_sign and d30_merc_sign]

        if is_hinglish:
            headline = f"Swasthya, Rog Pratirodhak Shamta Aur Upay (Trimshamsha · D30)"
            reading_parts.append(
                "Trimshamsha (D30) aur Saptavimshamsha (D27) aapki physical stamina, aantarik rog pratirodhak shamta aur preventive wellness rhythms ko darshata hai."
            )
            reading_parts.append(
                "<br><br><b>Aantarik Shamta Aur Swasthya Prabandhan:</b> "
                "Aapki kundli niyamit dainik routine, pachan ka dhyan aur swasth aahar se achhi vitality aur physical balance banaye rakhne ka sanket deti hai."
            )
        else:
            headline = f"Health Sensitivities, Physical Stamina & Resilience"
            reading_parts.append(
                "Classical Trimsamsha (D30) and Saptavimshamsha (D27) analysis maps your cellular stamina, "
                "constitutional resilience, latent anatomical sensitivities, and preventive wellness rhythms."
            )
            d30_lagna_lord = lord
            d30_lagna_lord_house = lord_house
            d30_lagna_lord_dig = lord_dig
            
            if d30_lagna_lord_dig in ("exalted", "moolatrikona", "own_sign") or d30_lagna_lord_house in (1, 4, 5, 7, 9, 10, 11):
                dig_txt = f" ({d30_lagna_lord_dig.replace('_', ' ').title()})" if d30_lagna_lord_dig else ""
                resilience_str = (
                    f"<b>Inherent Capacity to Overcome Adversities & Physical Resilience:</b> "
                    f"Your chart reflects strong inner recuperative vitality (D30 ruling planet <b>{d30_lagna_lord}</b> sitting in {lord_sign}, house {d30_lagna_lord_house}{dig_txt}). "
                    f"This confers the cellular stamina and psychological fortitude to rebound quickly from physical fatigue, neutralize latent health sensitivities, and successfully overcome crises and bodily strain."
                )
            elif d30_lagna_lord_house in DUSTHANA:
                resilience_str = (
                    f"<b>Inherent Vitality & Preventive Health Management:</b> "
                    f"With the D30 ruling planet (<b>{d30_lagna_lord}</b>) placed in the {ORDINALS.get(d30_lagna_lord_house, '8th')} house, your chart indicates that vitality builds through patient physical pacing, structured rest cycles, and early preventive care rather than pushing through extreme exhaustion."
                )
            else:
                resilience_str = (
                    f"<b>Inherent Capacity to Overcome Adversities:</b> "
                    f"Your chart demonstrates steady constitutional stamina (D30 Lagna ruled by <b>{d30_lagna_lord}</b> in {lord_sign}), giving you the resilience to restore physical balance through wholesome daily routines and active stress management."
                )
            reading_parts.append(f"<br><br>{resilience_str}")

            if d30_malefics:
                malefics_str = ", ".join(d30_malefics)
                reading_parts.append(
                    f"<br><br><b>Sensory, Nervous & Expressive Coordination (Mercury with {malefics_str} in D30 {d30_merc_sign}):</b> "
                    f"Classical principles indicate heightened nervous system sensitivity, sensory fatigue, and transient expressive/speech pacing latency when under pressure. "
                    f"Maintaining consistent sleep rhythms, vocal clarity exercises, and structured daily routines brings robust natural recovery and mental resilience."
                )

            preds = conf.get("predictions", []) if isinstance(conf, dict) else []
            if preds:
                zone_bullets = []
                for p in preds:
                    zone_bullets.append(
                        f"• <b>{p['title']} ({p['match_pct']}% Chart Alignment):</b> {p['prediction']} "
                        f"<br><i>Preventive Protocol:</i> {p['preventive']}"
                    )
                reading_parts.append(
                    "<br><br><b>Key Anatomical Vulnerability Zones:</b><br>" + "<br>".join(zone_bullets)
                )
            else:
                baseline = disease_res.get("constitutional_baseline", []) if isinstance(disease_res, dict) else []
                base_str = " ".join(baseline[:2]) if baseline else "Your chart shows steady natural vitality and good recuperative capacity."
                reading_parts.append(
                    f"<br><br><b>Constitutional Baseline:</b> {base_str} "
                    f"No single localized organ vulnerability shows extreme affliction; balanced nutrition, hydration, and regular sleep provide robust health preservation."
                )

        # High-Threshold Critical Mishappening & Near-Death Precaution Engine
        # Requires severe multi-clock confluence (Score >= 8) across Mrityu Bhaga, 8th Lord, Yogini Sankata/Ulka & Chara 8th Sign
        t_now = date.today()
        h6_lord = SIGN_LORDS.get(house_sign(d1_lagna, 6), "") if d1_lagna else ""
        h8_lord = SIGN_LORDS.get(house_sign(d1_lagna, 8), "") if d1_lagna else ""
        h12_lord = SIGN_LORDS.get(house_sign(d1_lagna, 12), "") if d1_lagna else ""
        h2_lord = SIGN_LORDS.get(house_sign(d1_lagna, 2), "") if d1_lagna else ""
        h7_lord = SIGN_LORDS.get(house_sign(d1_lagna, 7), "") if d1_lagna else ""

        # 1. Mrityu Bhaga (MB) fatal/vulnerable degrees
        mb_exact = []
        try:
            from astro_precompute import check_mrityu_bhaga
            mb_list = check_mrityu_bhaga(pc.get("planets", {}))
            mb_exact = [mb["planet"] for mb in mb_list if mb.get("within_one_deg") or mb.get("diff_deg", 99) <= 1.5]
        except Exception:
            pass

        # 2. Jaimini Gnathikaraka (GK)
        jaimini = pc.get("jaimini", {})
        k_list = jaimini.get("karakas", [])
        gk = ""
        if isinstance(k_list, list):
            for k_obj in k_list:
                if "GNATI" in str(k_obj.get("role", "")).upper():
                    gk = str(k_obj.get("planet", ""))
        elif isinstance(k_list, dict):
            gk = k_list.get("GK", "")

        # 3. D30 Dusthana placements
        d30_lagna = d30_dict.get("Lagna", "")
        d30_dusthana_planets = set()
        if d30_lagna and d30_lagna in SIGNS:
            for p, s in d30_dict.items():
                if p != "Lagna" and s in SIGNS:
                    h = (SIGNS.index(s) - SIGNS.index(d30_lagna)) % 12 + 1
                    if h in (6, 8, 12):
                        d30_dusthana_planets.add(p)

        # 4. Yogini timeline
        dob_raw = pc.get("meta", {}).get("birth_date") or pc.get("meta", {}).get("dob") or pc.get("dob")
        dob_d = _to_date(dob_raw) or date(2000, 1, 1)
        moon_nak = str((pc.get("planets", {}).get("Moon", {}) or {}).get("nakshatra", "Hasta"))
        moon_deg = float((pc.get("planets", {}).get("Moon", {}) or {}).get("degree_in_sign", 0.0) or 0.0) % 13.333333
        all_yogs = []
        try:
            from chara_yogini_timing import build_progressive_yogini_periods
            all_yogs = build_progressive_yogini_periods(dob_d, moon_nak, moon_deg)
        except Exception:
            pass

        # 5. Chara Dasha signs
        chara_maha = jaimini.get("chara_dasha", {}).get("maha", [])

        # 6. Vimshottari Hierarchy
        vim = pc.get("vimshottari", {})
        curr_md = vim.get("current_md", {}).get("md_lord", "")
        ad_list = vim.get("current_md_antardashas", [])

        critical_candidates = []
        try:
            from daily_vedic_confluence import compute_pratyantars
            for ad in ad_list:
                ad_lord = ad.get("ad_lord") or ad.get("antardasha") or ""
                st_d = _to_date(ad.get("start"))
                en_d = _to_date(ad.get("end"))
                if not st_d or not en_d: continue
                if en_d < t_now or st_d > t_now + timedelta(days=365*7): continue

                pds = compute_pratyantars(ad_lord, st_d, en_d)
                for pd in pds:
                    pd_lord = pd["lord"]
                    pd_st = pd["start"]
                    pd_en = pd["end"]
                    if pd_en < t_now: continue

                    score = 0
                    proofs = []

                    # Condition A: Mrityu Bhaga Activation
                    if pd_lord in mb_exact:
                        score += 5
                        proofs.append(f"Pratyantar {pd_lord} in exact Mrityu Bhaga sensitive degree")
                    if ad_lord in mb_exact:
                        score += 4
                        proofs.append(f"Antardasha {ad_lord} in Mrityu Bhaga degree")

                    # Condition B: 8th Lord (Randhresh) & Maraka (2nd/7th) & 12th Lord
                    is_8th_combo = False
                    if pd_lord == h8_lord:
                        score += 3
                        proofs.append(f"Pratyantar 8th lord {pd_lord} (Randhresh vitality pacing)")
                        is_8th_combo = True
                    elif pd_lord in (h2_lord, h7_lord) and ad_lord in (h8_lord, h6_lord, h12_lord):
                        score += 3
                        proofs.append(f"Pratyantar Maraka {pd_lord} under {ad_lord} Dusthana")
                        is_8th_combo = True
                    elif pd_lord in (h6_lord, h12_lord) and ad_lord == h8_lord:
                        score += 3
                        proofs.append(f"Pratyantar {pd_lord} under 8th lord {ad_lord}")
                        is_8th_combo = True

                    # Condition C: Gnathikaraka (GK)
                    if gk and (pd_lord == gk or ad_lord == gk):
                        score += 2
                        proofs.append(f"Gnathikaraka ({gk}) resistance cycle")

                    # Condition D: D30 Dusthana placement
                    if pd_lord in d30_dusthana_planets and is_8th_combo:
                        score += 2
                        proofs.append(f"{pd_lord} afflicted in D30 Trimsamsha")

                    # Condition E: Severe Yogini (Sankata/Ulka/Bhramari)
                    for yp in all_yogs:
                        y_st = _to_date(yp.get("start"))
                        y_en = _to_date(yp.get("end"))
                        if y_st and y_en and y_en > pd_st and y_st < pd_en:
                            y_name = yp.get("yogini", "")
                            y_lord = yp.get("lord", "")
                            if y_name in ("Sankata", "Ulka") or y_lord in (h8_lord, h6_lord, h12_lord):
                                score += 2
                                proofs.append(f"Yogini {yp['maha_yogini']}-{y_name} ({y_lord})")
                                break

                    # Condition F: Difficult Chara sign (8th or 6th from Lagna)
                    for cm in chara_maha:
                        c_st = _to_date(cm.get("start"))
                        c_en = _to_date(cm.get("end"))
                        if c_st and c_en and c_en > pd_st and c_st < pd_en:
                            s = cm.get("sign", "")
                            if s and d1_lagna:
                                h = (SIGNS.index(s) - SIGNS.index(d1_lagna)) % 12 + 1
                                if h == 8:
                                    score += 2
                                    proofs.append(f"Chara 8th sign ({s})")
                                    break
                                elif h == 6:
                                    score += 1
                                    proofs.append(f"Chara 6th sign ({s})")
                                    break

                    # Only flag if reaching genuine high-severity threshold
                    if score >= 9:
                        critical_candidates.append({
                            "md": curr_md,
                            "ad": ad_lord,
                            "pd": pd_lord,
                            "start": pd_st,
                            "end": pd_en,
                            "score": score,
                            "proofs": proofs,
                            "is_current": pd_st <= t_now <= pd_en,
                        })
        except Exception:
            pass

        critical_candidates.sort(key=lambda x: (0 if x["is_current"] else 1, x["start"]))

        # Format Critical Precaution Advisory (Zero panic for normal charts)
        if critical_candidates:
            primary_c = critical_candidates[0]
            st_fmt = _format_month_year(str(primary_c["start"]))
            en_fmt = _format_month_year(str(primary_c["end"]))
            conf_str = "; ".join(primary_c["proofs"][:3])
            if is_hinglish:
                hdr = "Sakriya Savdhani Phase" if primary_c["is_current"] else "Aage Aane Wala Savdhani Window"
                reading_parts.append(
                    f"<br><br><b>Aavashyak Swasthya Savdhani:</b><br>"
                    f"• <b>{hdr} ({primary_c['md']}-{primary_c['ad']}-{primary_c['pd']} · {st_fmt} – {en_fmt}):</b> "
                    f"Is samay physical pacing aur swasthya ka dhyan rakhein. "
                    f"Niyamit routine follow karein, bhari thakan aur rash driving se bachein aur dainik suraksha upay karein.<br>"
                    f"<i>Astrological Confluence:</i> {conf_str}."
                )
            else:
                hdr = "Active High-Precaution Phase" if primary_c["is_current"] else "Upcoming Critical Precaution Window"
                reading_parts.append(
                    f"<br><br><b>Critical Vitality & Precaution Advisory:</b><br>"
                    f"• <b>{hdr} ({primary_c['md']}-{primary_c['ad']}-{primary_c['pd']} · {st_fmt} – {en_fmt}):</b> "
                    f"High-confluence sensitivity window activating foundational vitality pacing. "
                    f"Prioritize routine medical wellness evaluations, practice mindful driving, avoid reckless physical exhaustion or high-risk adventure sports, and observe daily protective Upayas. <br>"
                    f"<i>Astrological Confluence:</i> {conf_str}."
                )
        else:
            if is_hinglish:
                reading_parts.append(
                    f"<br><br><b>Aantarik Suraksha Aur Santulan:</b><br>"
                    f"• <b>Suraksha Kavach:</b> Aapki kundli mein sthir aantarik endurance aur vitality hai. "
                    f"Niyamit poshtik aahar, paryaapt paani aur sahi sleep routine se swasthya achha bana rehta hai."
                )
            else:
                reading_parts.append(
                    f"<br><br><b>Constitutional Resilience & Preventive Balance:</b><br>"
                    f"• <b>Protected Vitality Shield:</b> Your chart reflects steady constitutional endurance with no critical vitality collapse or severe mishappening confluence indicated in the active forecast horizon. "
                    f"Maintaining balanced daily nutrition, hydration, and regular sleep rhythms ensures continued robust health."
                )

        # Remedy
        rems = [r for r in (disease_res.get("remedies", []) if isinstance(disease_res, dict) else []) if r.get("planet") != "General"]
        top_rem = rems[0] if rems else {}
        rem_lines = []
        if is_hinglish:
            if top_rem:
                rem_lines.append(f"<b>Mukhya Upay ({top_rem.get('planet')}):</b> {top_rem.get('mantra')} ka jaap karein; daan: {top_rem.get('charity')}.")
            rem_lines.append("<b>Sarva Swasthya Suraksha (Maha Mrityunjaya):</b> Niyamit Maha Mrityunjaya Mantra ka jaap ya shravan karein, shant vatavaran banayein aur swasth dainik dincharya apnayein.")
        else:
            if top_rem:
                rem_lines.append(f"<b>Primary Upaya ({top_rem.get('planet')}):</b> Chant {top_rem.get('mantra')}; perform charity: {top_rem.get('charity')}.")
            rem_lines.append("<b>Universal Health Protection (Maha Mrityunjaya):</b> Recite the Maha Mrityunjaya Mantra (108 times daily) during sensitive planetary transitions; cultivate calm breathing, wholesome nutrition, and steady restorative routines.")
        
        prediction = "".join(reading_parts)
        remedy = "<br>".join(rem_lines)
        return headline, prediction, remedy

    else:
        headline = f"Life Focus Area ({code})"
        prediction = " ".join(reading_parts) if reading_parts else f"Fortified placements in this division support positive life focus."
        remedy = "Maintain regular spiritual grounding and mindful daily habits."
        return headline, prediction, remedy

    prediction = " ".join(reading_parts)

    # Targeted Remedy Text
    if remedy_planet and remedy_planet in PLANET_REMEDIES:
        rem_text = PLANET_REMEDIES[remedy_planet].get(remedy_type, PLANET_REMEDIES[remedy_planet]["strengthen"])
        remedy = f"<b>{remedy_reason}:</b> {rem_text}"
    else:
        remedy = "Maintain regular spiritual grounding, meditation, and mindful daily habits."

    return headline, prediction, remedy


def get_108_snapshot_summary_paragraph(pc: dict) -> str:
    """Synthesizes the active classical rules into a single cohesive, flowing natural paragraph without author/book names."""
    try:
        from prediction108_rules import evaluate_all
        verdicts = evaluate_all(pc)
        hits = [v for v in verdicts if v.verdict == "HIT" and v.prediction and len(v.finding.strip()) > 15]

        key_hits = []
        priority_rule_nos = [1, 2, 3, 4, 15, 17, 21, 11]
        for r_no in priority_rule_nos:
            for v in hits:
                if v.no == r_no and v not in key_hits:
                    key_hits.append(v)
                    break

        if not key_hits:
            key_hits = hits[:4]

        sentences = []
        for v in key_hits:
            p = v.prediction.strip()
            if p:
                if not p.endswith(('.', '!', '?')):
                    p += '.'
                sentences.append(p)

        if not sentences:
            return (
                "The classical checks did not single out a standout strength or weakness in the foundation of your chart; "
                "the detail below is what the chart itself shows."
            )

        merged = " ".join(sentences[:4])
        return merged
    except Exception as exc:
        print(f"[divisional_profile] 108 summary error: {exc}", flush=True)
        return ""


def render_divisional_blocks(pc: dict, *, paid: bool = False,
                            today: Optional[date] = None,
                            lang: str = "en") -> tuple[str, str]:
    """Build the divisional block as two independently placeable pieces.

    Returns ``(baseline_html, areas_html)``. The report puts the foundational
    baseline card next to the personality reading, well above the timing
    sections, and keeps the per-varga life-area cards below them.

    Free tier:
      - Full cards for D1 (Self), D2 (Wealth), D3 (Speech/Motor/Drive), D12 (Parents).
      - Remedy boxes blurred with lock overlay.
      - Locked teaser preview for D7 (Kids), D9 (Marriage), D10 (Career), D24 (Education), D30 (Hardships).
    Paid tier:
      - All 9 divisional cards rendered in full depth with strengths, domain-specific timelines, unblurred remedies, and collapsible proof.
    """
    lang_code = str(lang or "").lower().strip()
    is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")
    insights = build_divisional_insights(pc, lang=lang)
    summary_108 = get_108_snapshot_summary_paragraph(pc)
    if is_hinglish:
        summary_108 = (
            "Aapki janma kundli mein mool classical strengths hain: aapke vyaktigat prayas aur anushasan se "
            "jeevan ke mukhya kshetro mein naye avsar aur sthirta prapt hoti hai. Supportive dasha aur transits "
            "ke dauran sahi disha mein uthaye gaye kadam lambe samay tak safalta aur santushti dete hain."
        )
    elif is_tenglish:
        summary_108 = (
            "Mee janma kundali lo moola classical balam undi: mee vyakthigatha prayathnam mariyu anushasanam tho "
            "jeevitha mukhya rangalalo kottha avakashalu mariyu sthiratha labhisthayi. Supportive dasha mariyu transits "
            "samayam lo theesukunna decisions deergha kaalam lo manchi vijayam mariyu santhrupthi isthayi."
        )

    div_cards_html = []
    teaser_items = []

    def _free_timeline(text: str) -> str:
        from free_dates import strip_future_sentences
        kept = strip_future_sentences(text, today)
        if is_hinglish:
            locked_msg = "🔒 Is kshetra ka dated window poori reading mein shamil hai."
        elif is_tenglish:
            locked_msg = "🔒 Ee kshetram yokka dated window sampoorna reading lo undi."
        else:
            locked_msg = "🔒 The dated window for this area is in the full reading."
        locked = (
            f'<span style="display:block;margin-top:6px;font-size:0.78rem;'
            f'font-weight:700;color:#8a6a1f;">{locked_msg}</span>')
        return (kept + locked) if kept else locked.strip()

    v_meta_dict = VARGA_META_TENGLISH if is_tenglish else (VARGA_META_HINGLISH if is_hinglish else VARGA_META)

    for ins in insights:
        pill_cls = "up" if ins.strength == "strong" else "down" if ins.strength == "weak" else "mixed"
        if is_hinglish:
            pill_lbl = "Anukool" if ins.strength == "strong" else "Savdhan" if ins.strength == "weak" else "Sakriya"
        elif is_tenglish:
            pill_lbl = "Anukoolam" if ins.strength == "strong" else "Jagratha" if ins.strength == "weak" else "Sakriyam"
        else:
            pill_lbl = "Well Supported" if ins.strength == "strong" else "Needs Care" if ins.strength == "weak" else "Active / Mixed"
        
        card_class = "pos" if ins.strength == "strong" else "warn" if ins.strength == "weak" else "accent"
        pill_status_class = "positive" if ins.strength == "strong" else "warning" if ins.strength == "weak" else "info"

        is_free_allowed = ins.code in FREE_ALLOWED_VARGAS

        if paid or is_free_allowed:
            # Dasha Timeline Box (Domain Specific).
            timeline_box = ""
            timeline_text = ins.timeline
            if timeline_text and not paid:
                timeline_text = _free_timeline(timeline_text)
            if timeline_text:
                timeline_box = (
                    f'  <div style="background:rgba(56,189,248,0.08);border-left:3px solid var(--accent);border-radius:0 8px 8px 0;padding:10px 14px;margin:12px 0;font-size:13.5px;color:#e2e8f0;line-height:1.55;">\n'
                    f'    {timeline_text}\n'
                    f'  </div>\n'
                )

            # Remedy display: Clear if paid, blurred with lock overlay if free
            if is_hinglish:
                upaya_lbl = "Vedic Upay:"
            elif is_tenglish:
                upaya_lbl = "Vedic Upayam:"
            else:
                upaya_lbl = "Prescribed Astrological Upaya:"
            if paid:
                remedy_box = (
                    f'  <div style="background:rgba(16,185,129,0.08);border-left:3px solid var(--positive);border-radius:0 8px 8px 0;padding:10px 14px;margin:10px 0;font-size:13.5px;color:#a7f3d0;line-height:1.5;">\n'
                    f'    <b>{upaya_lbl}</b> {ins.remedy}\n'
                    f'  </div>\n'
                )
            else:
                if is_hinglish:
                    teaser_remedy = f'Mantra, daan aur dainik abhyas jo {html.escape(ins.lord or "grahadhipati")} se mel khate hain.'
                    lock_text = "🔒 Complete Reading Mein Upay Shamil"
                elif is_tenglish:
                    teaser_remedy = f'Mantra japam, daanam mariyu daily pariharam jo {html.escape(ins.lord or "grahadhipati")} ki anukoolanga untundi.'
                    lock_text = "🔒 Sampoorna Reading Lo Upayamulu Unnai"
                else:
                    teaser_remedy = (
                        f'Mantra, charity and daily practice matched to '
                        f'{html.escape(ins.lord or "your chart ruler")} for this area of life.'
                    )
                    lock_text = "🔒 Upaya Unlocked in Full Reading"
                remedy_box = (
                    f'  <div class="lock-wrap" style="margin:10px 0;">\n'
                    f'    <div class="lock-blur" style="padding:10px 14px;font-size:13.5px;color:#94a3b8;">\n'
                    f'      <b>{upaya_lbl}</b> {teaser_remedy}\n'
                    f'    </div>\n'
                    f'    <div class="lock-over">\n'
                    f'      <span class="lock-chip">{lock_text}</span>\n'
                    f'    </div>\n'
                    f'  </div>\n'
                )

            # Collapsible Proof Drawer
            if is_hinglish:
                proof_title = f"Jyotishiya Praman ({html.escape(ins.name)})"
            elif is_tenglish:
                proof_title = f"Jyotisha Pramanam ({html.escape(ins.name)})"
            else:
                proof_title = f"Technical Astrological Basis ({html.escape(ins.name)})"
            proof_drawer = (
                f'  <details style="margin-top:12px;border-top:1px solid var(--border);padding-top:8px;font-size:12.5px;color:var(--text-muted);line-height:1.45;">\n'
                f'    <summary style="cursor:pointer;font-weight:600;color:var(--text-muted);">{proof_title}</summary>\n'
                f'    <div style="padding-top:6px;color:#cbd5e1;">\n'
                f'      {ins.evidence}\n'
                f'    </div>\n'
                f'  </details>\n'
            )

            # The kicker doubles as this card's entry in the contents rail.
            meta_entry = v_meta_dict.get(ins.code, {})
            area = meta_entry.get("nav") or meta_entry.get("governs") or ins.governs
            card = (
                f'<div class="summary-card {card_class}" id="{ins.domain_id}">\n'
                f'  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">\n'
                f'    <span class="tag">{html.escape(area)}</span>\n'
                f'    <span class="phase-pill {pill_status_class}">{pill_lbl}</span>\n'
                f'  </div>\n'
                f'  <h2>{html.escape(ins.headline)}</h2>\n'
                f'  <div style="margin:0 0 12px;font-size:14.5px;line-height:1.6;color:#e2e8f0;">{ins.prediction}</div>\n'
                f'{timeline_box}'
                f'{remedy_box}'
                f'{proof_drawer}'
                f'</div>\n'
            )
            div_cards_html.append(card)
        else:
            meta = v_meta_dict.get(ins.code, {})
            pill_status_class = "positive" if ins.strength == "strong" else "warning" if ins.strength == "weak" else "info"
            if is_hinglish:
                verdict_said = ("anukool sthiti" if ins.strength == "strong"
                                else "savdhani aavashyak" if ins.strength == "weak"
                                else "sakriya aur mixed")
                teaser_chart_msg = f'Aapki kundli mein yahan <b>{verdict_said}</b> hai{" — dated window already calculated hai" if ins.timeline else ""}.'
            elif is_tenglish:
                verdict_said = ("anukoolamaina sthiti" if ins.strength == "strong"
                                else "jagratha avasaram" if ins.strength == "weak"
                                else "sakriyam mariyu mixed")
                teaser_chart_msg = f'Mee kundali lo ikkada <b>{verdict_said}</b> undi{" — dated window already calculated ayyindi" if ins.timeline else ""}.'
            else:
                verdict_said = ("well supported" if ins.strength == "strong"
                                else "needing care" if ins.strength == "weak"
                                else "active but mixed")
                teaser_chart_msg = f'Your chart reads as <b>{verdict_said}</b> here{" — with an exact dated window already calculated" if ins.timeline else ""}.'
            
            teaser_items.append(
                f'<li style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid var(--border);gap:10px;">'
                f'  <div>'
                f'    <b style="font-size:14.5px;color:var(--text-main);">{html.escape(meta.get("governs", ins.governs))}</b><br>'
                f'    <span style="font-size:13px;color:var(--text-muted);">{html.escape(meta.get("desc", ""))}</span><br>'
                f'    <span style="font-size:12.5px;color:var(--accent);">{teaser_chart_msg}</span>'
                f'  </div>'
                f'  <span class="phase-pill {pill_status_class}">{pill_lbl}</span>'
                f'</li>'
            )

    teaser_html = ""
    if not paid and teaser_items:
        if is_hinglish:
            t_area = "Baki 6 Jeevan Kshetra"
            t_avail = "Full Reading Mein Uplabdh"
            t_desc = "Aapke baki divisional charts dhan aur sampatti (D2), career karma (D10), vivah aur jeevansathi (D9), santan (D7), uccha shiksha (D24), aur swasthya/immunity (D30) ko map karte hain:"
            t_cta = "Complete Divisional Breakdown Unlock Karein"
        elif is_tenglish:
            t_area = "Migilina 6 Jeevitha Rangalu"
            t_avail = "Full Reading Lo Labhisthundi"
            t_desc = "Mee migilina divisional charts dhanam mariyu sampada (D2), career karma (D10), vivaham mariyu jeevithabhagswami (D9), santhanam (D7), uccha vidya (D24), mariyu aarogyam/immunity (D30) ni map chesthayi:"
            t_cta = "Complete Divisional Breakdown Unlock Cheyandi"
        else:
            t_area = "Remaining Key Life Areas"
            t_avail = "Available in Full Reading"
            t_desc = "Your full reading unlocks in-depth consultations for your Money & Wealth, Career & Leadership, Marriage & Partner, Children & Legacy, Higher Learning & Skills, and Physical Stamina & Resilience:"
            t_cta = "Unlock Complete Life Consultations · ₹298"
        teaser_html = (
            f'<div class="summary-card" id="domain-locked" style="background:#1e293b;border:1px dashed var(--border);border-radius:14px;padding:22px 24px;margin-bottom:20px;">\n'
            f'  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">\n'
            f'    <span class="tag">{t_area}</span>\n'
            f'    <span class="phase-pill warning">{t_avail}</span>\n'
            f'  </div>\n'
            f'  <p style="font-size:14px;color:var(--text-muted);margin:0 0 14px;line-height:1.5;">\n'
            f'    {t_desc}\n'
            f'  </p>\n'
            f'  <ul style="list-style:none;margin:0;padding:0;">\n'
            f'    {"".join(teaser_items)}\n'
            f'  </ul>\n'
            f'  <div style="text-align:center;margin-top:18px;">\n'
            f'    <a href="#unlock" data-unlock="1" style="display:inline-block;background:var(--accent);color:#0f172a;font-weight:700;font-size:13.5px;padding:9px 24px;border-radius:999px;text-decoration:none;">{t_cta}</a>\n'
            f'  </div>\n'
            f'</div>\n'
        )

    # 108 Rule Snapshot Card
    if is_hinglish:
        base_kicker = "Mool adhar"
        base_chip = "Janm Kundli Mool Vaada"
        base_heading = "Mool Jyotishiya Adhar"
    elif is_tenglish:
        base_kicker = "Moola aadharam"
        base_chip = "Janma Kundali Moola Prathigna"
        base_heading = "Moola Jyotisha Aadharam"
    else:
        base_kicker = "Foundational baseline"
        base_chip = "Static Promise"
        base_heading = "Foundational Astrological Baseline"

    snapshot_108_html = (
        f'<div class="summary-card accent" id="domain-baseline">\n'
        f'  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">\n'
        f'    <span class="tag">{base_kicker}</span>\n'
        f'    <span class="phase-pill info">{base_chip}</span>\n'
        f'  </div>\n'
        f'  <h2>{base_heading}</h2>\n'
        f'  <p style="margin:0;font-size:14.5px;line-height:1.6;color:#e2e8f0;">{summary_108}</p>\n'
        f'</div>\n'
    )

    return snapshot_108_html, f"{''.join(div_cards_html)}\n{teaser_html}"


def render_divisional_about_you_html(pc: dict, *, paid: bool = False,
                                    today: Optional[date] = None) -> str:
    """Baseline card and life-area cards as one contiguous block."""
    baseline_html, areas_html = render_divisional_blocks(pc, paid=paid, today=today)
    return f"{baseline_html}\n{areas_html}"
