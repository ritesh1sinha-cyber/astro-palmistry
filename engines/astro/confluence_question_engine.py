"""Universal Vedic Confluence Engine for Life Inquiries & Problem Analysis.

Provides deep, multi-layered classical astrological analysis for ANY life question
(speech, neurological, career, marriage, health, finances, litigation, progeny, education, etc.)
by synthesizing:
1. Primary & Secondary Houses (Karya Bhava & Sahayaka Bhava)
2. House Lords, Dignities & Dusthana Placements (6th, 8th, 12th)
3. Natural Significators (Naisargika Karakas)
4. Divisional Cross-Verification (D9 Navamsha, D30 Trimsamsha, D3, D7, D10, D24)
5. Dasha Period Chronology (Past origin, Current state, Future breakthrough)
6. Targeted Remedial Action (Vedic Upaya)
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from astro_precompute import (
    SIGN_LORDS,
    SIGNS,
    get_dignity,
    sign_index,
    house_from_lagna,
)

DOMAINS_CONFIG = {
    "speech_neurology": {
        "title": "Speech, Nervous System & Cognitive Coordination",
        "primary_house": 2,
        "supporting_houses": [3, 5, 8],
        "karakas": ["Mercury", "Moon", "Mars", "Rahu"],
        "vargas": ["D3", "D9", "D30"],
        "keywords": [
            "speech", "speak", "talking", "talk", "voice", "vocal", "stutter", "stammer",
            "tongue", "mouth", "words", "language", "articulation", "mute", "communication",
            "neuro", "neurological", "brain", "nerve", "nervous", "autism", "adhd", "sensory",
            "synapse", "motor", "coordination", "development", "delay", "expressive"
        ],
        "dusthana_implications": {
            2: "2nd Lord in Dusthana (6/8/12) directly causes speech delay, articulation friction, or vocal latency in early childhood.",
            3: "3rd Lord in Dusthana (6/8/12) creates auditory/throat friction or mechanical slowness in expressive communication.",
            5: "5th House afflicted or 5th Lord in Dusthana creates cognitive latency, sensory over-excitability, or non-linear learning curves.",
        },
        "karaka_roles": {
            "Mercury": "Universal Karaka of Speech, Nervous System, and Brain Synapses",
            "Moon": "Karaka of Mind, Sensory Processing, and Neurotransmitters",
            "Mars": "Lord/Karaka of Vocal Chords and Articulation Force",
            "Rahu": "Indicator of Atypical Wiring, Sensory Overwhelm, or Non-linear Cognitive Cycles",
        }
    },
    "health_vitality": {
        "title": "Health, Physical Vitality & Medical Recovery",
        "primary_house": 6,
        "supporting_houses": [1, 8, 12],
        "karakas": ["Sun", "Mars", "Saturn", "Moon"],
        "vargas": ["D1", "D30", "D9"],
        "keywords": [
            "health", "disease", "illness", "sick", "cure", "surgery", "operation", "hospital",
            "vitality", "body", "injury", "accident", "pain", "medical", "treatment", "infection",
            "blood", "stomach", "heart", "liver", "bones", "energy", "healing", "recovery"
        ],
        "dusthana_implications": {
            1: "1st Lord in 6th/8th/12th lowers constitutional immunity and requires conscious physical maintenance.",
            6: "6th House/Lord activation triggers acute physiological friction, inflammation, or medical consultations.",
            8: "8th House/Lord involvement points to chronic, hidden, or cyclical conditions requiring sustained care.",
        },
        "karaka_roles": {
            "Sun": "Karaka of General Vitality, Bones, and Immune Stamina",
            "Mars": "Karaka of Blood, Surgeries, Muscle Tone, and Acute Inflammation",
            "Saturn": "Karaka of Chronic Ailments, Longevity, and Joint/Nerve Degeneration",
            "Moon": "Karaka of Bodily Fluids, Mental Calmness, and Emotional Recovery",
        }
    },
    "career_profession": {
        "title": "Career Growth, Status & Vocational Trajectory",
        "primary_house": 10,
        "supporting_houses": [6, 11, 1],
        "karakas": ["Sun", "Saturn", "Jupiter", "Mercury"],
        "vargas": ["D10", "D9", "D1"],
        "keywords": [
            "career", "job", "work", "profession", "professionally", "promotion", "business",
            "status", "boss", "office", "employment", "company", "startup", "venture", "leadership",
            "authority", "recognition", "growth", "demotion", "transfer", "layoff", "fired", "naukri",
            "earn", "earning", "vocation", "trade", "occupation"
        ],
        "dusthana_implications": {
            10: "10th Lord in Dusthana (6/8/12) brings unexpected career pivots, hidden friction with authorities, or vocational restructuring.",
            6: "6th House involvement indicates intense competition, workload pressure, and navigating workplace politics.",
            11: "11th Lord in Dusthana delays fulfillment of professional milestones or steady recognition.",
        },
        "karaka_roles": {
            "Sun": "Karaka of Executive Authority, Public Recognition, and Government Patronage",
            "Saturn": "Karaka of Professional Karma, Sustained Labour, and Structural Responsibility",
            "Jupiter": "Karaka of Wise Counsel, Ethical Expansion, and High-Level Advisory Roles",
            "Mercury": "Karaka of Business Transactions, Analytical Acumen, and Communication Flow",
        }
    },
    "marriage_relationship": {
        "title": "Marriage, Partnership & Relationship Harmony",
        "primary_house": 7,
        "supporting_houses": [2, 8, 12],
        "karakas": ["Venus", "Jupiter", "Mars", "Rahu"],
        "vargas": ["D9", "D30", "D1"],
        "keywords": [
            "marriage", "marry", "married", "wedding", "matrimony", "husband", "wife", "spouse",
            "partner", "relationship", "love", "divorce", "separation", "compatibility", "breakup",
            "affair", "shaadi", "vivah", "wed", "match", "bride", "groom", "in-laws", "life partner"
        ],
        "dusthana_implications": {
            7: "7th Lord in Dusthana (6/8/12) creates delays in marital settlement or periodic friction requiring emotional maturity.",
            2: "2nd Lord in Dusthana brings family-level adjustments or financial differences between partners.",
            8: "8th House involvement brings intense karmic transformations and privacy tests in marriage.",
        },
        "karaka_roles": {
            "Venus": "Primary Karaka for Love, Spousal Harmony, and Marital Attraction",
            "Jupiter": "Karaka of Dharmic Marital Bond, Wisdom, and Spousal Longevity",
            "Mars": "Indicator of Passion, Manglik Friction, or Argumentative Energy",
            "Rahu": "Indicator of Unconventional Unions, Restlessness, or Illusions in Relationships",
        }
    },
    "wealth_finances": {
        "title": "Wealth Accumulation, Assets & Financial Security",
        "primary_house": 2,
        "supporting_houses": [11, 9, 5],
        "karakas": ["Jupiter", "Mercury", "Venus"],
        "vargas": ["D2", "D9", "D11"],
        "keywords": [
            "money", "wealth", "finance", "income", "salary", "rich", "paisa", "dhan", "debt",
            "loan", "loss", "profit", "investment", "shares", "stocks", "savings", "assets"
        ],
        "dusthana_implications": {
            2: "2nd Lord in Dusthana (6/8/12) causes fluctuating cash flow or expenditure surges.",
            11: "11th Lord in Dusthana brings delayed returns on effort or irregular income spikes.",
            12: "12th House activation causes unexpected capital outflow or overseas investments.",
        },
        "karaka_roles": {
            "Jupiter": "Universal Karaka of Abundance, Institutional Wealth, and Gold/Assets",
            "Mercury": "Karaka of Liquid Cash, Trading Profits, and Commercial Intelligence",
            "Venus": "Karaka of Luxuries, Material Comforts, and Resource Enjoyment",
        }
    },
    "children_progeny": {
        "title": "Children, Progeny & Family Lineage",
        "primary_house": 5,
        "supporting_houses": [9, 2, 11],
        "karakas": ["Jupiter", "Mars", "Sun"],
        "vargas": ["D7", "D9"],
        "keywords": [
            "child", "children", "baby", "kid", "kids", "son", "daughter", "conceive", "pregnancy",
            "pregnant", "conception", "progeny", "lineage", "santana", "parenting", "childbirth", "ivf",
            "have children", "have kids", "offspring", "family planning"
        ],
        "dusthana_implications": {
            5: "5th Lord in Dusthana (6/8/12) causes delays in conception or heightened concern over child welfare.",
            8: "8th House involvement brings medical hurdles or unexpected reproductive twists requiring remedies.",
        },
        "karaka_roles": {
            "Jupiter": "Primary Putrakaraka and Guardian of Children's Dharma and Vitality",
            "Mars": "Indicator of Surgical Assistance or Reproductive Energy",
            "Sun": "Indicator of Lineage Strength and Paternal Continuation",
        }
    },
    "education_learning": {
        "title": "Education, Academic Mastery & Intellectual Success",
        "primary_house": 5,
        "supporting_houses": [4, 9, 2],
        "karakas": ["Mercury", "Jupiter"],
        "vargas": ["D24", "D9"],
        "keywords": [
            "study", "education", "school", "college", "exam", "degree", "learning", "marks",
            "scholarship", "entrance", "university", "academic", "memory", "intellect", "upsc"
        ],
        "dusthana_implications": {
            5: "5th Lord in Dusthana (6/8/12) causes exam anxiety or scattered concentration during crucial tests.",
            4: "4th Lord in Dusthana brings disruption to foundational schooling or changing academic venues.",
        },
        "karaka_roles": {
            "Mercury": "Karaka of Grasping Power, Analytical Acumen, and Memory Retention",
            "Jupiter": "Karaka of Higher Wisdom, Philosophical Depth, and Formal Degrees",
        }
    },
    "foreign_relocation": {
        "title": "Foreign Settlement, Travel & Relocation",
        "primary_house": 12,
        "supporting_houses": [9, 3, 4],
        "karakas": ["Rahu", "Moon", "Jupiter"],
        "vargas": ["D9", "D12", "D1"],
        "keywords": [
            "foreign", "abroad", "travel", "visa", "pr", "citizenship", "relocate", "relocation",
            "overseas", "settle abroad", "onsite", "migration", "passport", "foreign settlement",
            "shift", "country", "foreign country", "settle", "immigrate", "emigrate", "international"
        ],
        "dusthana_implications": {
            12: "12th Lord in Kendra/Trikona or 4th Lord in 12th strongly triggers permanent distant relocation.",
            4: "4th Lord afflicted or connected to 12th removes attachment to birth home, facilitating foreign living.",
        },
        "karaka_roles": {
            "Rahu": "Primary Significator of Foreign Lands, Unfamiliar Cultures, and Distant Relocation",
            "Moon": "Karaka of Travel across Waters and Emotional Adaptability Abroad",
            "Jupiter": "Karaka of Lawful Visa Approval and Spiritual Journeys",
        }
    },
    "property_assets": {
        "title": "Property, Land & Real Estate Acquisition",
        "primary_house": 4,
        "supporting_houses": [2, 11, 12],
        "karakas": ["Mars", "Venus", "Saturn"],
        "vargas": ["D4", "D9"],
        "keywords": [
            "property", "house", "flat", "apartment", "land", "plot", "real estate", "buy house", "build house",
            "villa", "residence", "vehicle", "car", "home purchase", "purchase", "property dispute", "registry"
        ],
        "dusthana_implications": {
            4: "4th Lord in Dusthana (6/8/12) causes construction delays, registry hurdles, or property disputes.",
        },
        "karaka_roles": {
            "Mars": "Karaka of Land, Soil, Construction, and Immovable Real Estate",
            "Venus": "Karaka of Aesthetic Residential Architecture, Luxury Vehicles, and Comfort",
            "Saturn": "Karaka of Aging Properties, Foundations, and Long-term Construction Pace",
        }
    },
    "litigation_disputes": {
        "title": "Litigation, Disputes, Debts & Enemies",
        "primary_house": 6,
        "supporting_houses": [8, 11, 10],
        "karakas": ["Mars", "Saturn", "Sun"],
        "vargas": ["D30", "D6", "D9"],
        "keywords": [
            "case", "court", "legal", "lawsuit", "lawyer", "police", "jail", "enemy", "dispute",
            "conflict", "debt", "settlement", "litigation", "hearing", "verdict", "argument"
        ],
        "dusthana_implications": {
            6: "6th Lord strong in Upachaya (3, 6, 11) indicates decisive victory over opponents.",
            8: "8th House involvement points to protracted negotiations or unexpected compromise terms.",
        },
        "karaka_roles": {
            "Mars": "Karaka of Courage in Confrontation, Legal Fighting Power, and Enforcement",
            "Saturn": "Karaka of Court Delays, Karmic Judgment, and Endurance under Trial",
            "Sun": "Karaka of Judge, Government Authority, and Sovereign Justice",
        }
    },
    "gemstones_remedies": {
        "title": "Gemstone Recommendations, Remedial Upayas & Functional Benefics",
        "primary_house": 1,
        "supporting_houses": [5, 9, 11],
        "karakas": ["Jupiter", "Sun", "Moon", "Mars", "Venus", "Mercury", "Saturn"],
        "vargas": ["D1", "D9", "D20"],
        "keywords": [
            "gemstone", "gem", "stone", "ratna", "gemstones", "stones", "wear stone", "wear gemstone",
            "which stone", "which gemstone", "suit me", "lucky stone", "lucky gemstone", "birthstone",
            "ring", "pendant", "rudraksha", "remedy", "remedies", "upaya", "mantra", "puja", "chant",
            "panna", "emerald", "emerland", "emrald", "marakata",
            "manik", "manikya", "ruby", "moti", "mukta", "pearl",
            "pukhraj", "pokhraj", "yellow sapphire", "pushparag",
            "neelam", "nilam", "blue sapphire", "indraneel",
            "heera", "diamond", "coral", "moonga", "munga", "praval",
            "gomed", "hessonite", "catseye", "cats eye", "lehsunia", "lahsuniya", "opal",
            "gemstone advice", "ratna dharan", "suitable gemstone", "suitable stone", "suitable for my chart"
        ],
        "dusthana_implications": {
            1: "1st Lord (Lagna Lord) is the foundational Life Stone: wearing its gem strengthens overall constitution, vitality, and aura.",
            5: "5th Lord rules intellect and Purva Punya: its gemstone enhances cognitive clarity, career luck, and decision-making.",
            9: "9th Lord rules Bhagya (Destiny and Divine Grace): its gemstone activates higher fortune and spiritual protection.",
            6: "Dusthana Lords (6th/8th/12th) must strictly NOT be enhanced with gemstones unless they are simultaneously the Lagna Lord.",
            8: "8th Lord gemstone is strictly forbidden as it can aggravate vulnerabilities and sudden obstacles.",
            12: "12th Lord gemstone is avoided to prevent expenditure surges and energy dissipation.",
        },
        "karaka_roles": {
            "Jupiter": "Karaka of Higher Wisdom, Divine Grace, and Yellow Sapphire (Pukhraj)",
            "Sun": "Karaka of Soul Vitality, Executive Authority, and Ruby (Manikya)",
            "Moon": "Karaka of Mental Peace, Emotional Balance, and Natural Pearl (Moti)",
            "Mars": "Karaka of Courage, Vital Stamina, and Red Coral (Moonga)",
            "Mercury": "Karaka of Intellect, Analytical Clarity, and Emerald (Panna)",
            "Venus": "Karaka of Refinement, Material Prosperity, and Diamond/Opal (Heera)",
            "Saturn": "Karaka of Discipline, Long-term Endurance, and Blue Sapphire (Neelam)",
        }
    },
    "general_destiny": {
        "title": "Overall Life Trajectory, Destiny & Operating Dasha Period",
        "primary_house": 1,
        "supporting_houses": [9, 10, 11],
        "karakas": ["Sun", "Jupiter", "Saturn", "Moon"],
        "vargas": ["D1", "D9", "D10"],
        "keywords": [
            "future", "life", "destiny", "ahead", "upcoming", "time", "period", "phase",
            "kaisa", "samay", "bhavishya", "aage", "overall", "general", "horoscope", "kundli",
            "overview", "prospects", "years", "months", "path", "direction", "focus", "outcome"
        ],
        "dusthana_implications": {
            1: "1st Lord in Kendra/Trikona creates powerful static resilience across all life chapters.",
            9: "9th Lord (Bhagya) acts as the guardian angel protecting the overall life trajectory.",
            10: "10th Lord (Karma) defines professional legacy and active public manifestation.",
        },
        "karaka_roles": {
            "Sun": "Universal Karaka of Soul Purpose, Vitality, and Core Identity",
            "Jupiter": "Universal Karaka of Divine Grace, Dharma, and Wisdom",
            "Saturn": "Universal Karaka of Karmic Lessons, Pacing, and Long-Term Maturity",
            "Moon": "Universal Karaka of Mind, Emotional Wellbeing, and Daily Experience",
        }
    },
    "out_of_domain": {
        "title": "General & Non-Astrological Inquiry",
        "primary_house": 1,
        "supporting_houses": [9, 10, 5],
        "karakas": ["Jupiter", "Mercury", "Sun"],
        "vargas": ["D1", "D9"],
        "keywords": [],
        "dusthana_implications": {},
        "karaka_roles": {}
    }
}


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


def audit_chart_gemstones(pc: dict) -> dict[str, Any]:
    """Comprehensive classical Parashari gemstone & remedial safety audit for all 9 planets."""
    lagna_sign = pc.get("meta", {}).get("lagna_sign", "") or (pc.get("lagna", {}) or {}).get("sign", "Aries")
    if not lagna_sign or lagna_sign not in SIGNS:
        lagna_sign = "Aries"
    lagna_idx = sign_index(lagna_sign)
    planets = pc.get("planets", {})

    house_lords: dict[int, dict[str, Any]] = {}
    for h in range(1, 13):
        s_idx = (lagna_idx + h - 1) % 12
        h_sign = SIGNS[s_idx]
        h_lord = SIGN_LORDS.get(h_sign, "")
        house_lords[h] = {"house": h, "sign": h_sign, "lord": h_lord}

    planet_houses: dict[str, int] = {}
    for p, pdata in planets.items():
        if p != "Lagna" and isinstance(pdata, dict):
            p_sign = pdata.get("sign", "")
            planet_houses[p] = int(pdata.get("house", house_from_lagna(p_sign, lagna_sign) or 1))

    is_dual = lagna_sign in ("Gemini", "Virgo", "Sagittarius", "Pisces")
    badhaka_house = 7 if is_dual else (11 if lagna_sign in ("Aries", "Cancer", "Libra", "Capricorn") else 9)
    badhaka_lord = house_lords[badhaka_house]["lord"]
    maraka_lords = {house_lords[2]["lord"], house_lords[7]["lord"]}
    dusthana_lords = {house_lords[6]["lord"], house_lords[8]["lord"], house_lords[12]["lord"]}
    trine_lords = {house_lords[1]["lord"], house_lords[5]["lord"], house_lords[9]["lord"]}

    gem_map = {
        "Sun": ("Ruby (Manik)", "Gold or Copper", "Ring finger", "Sunday", "Surya Gayatri 108x daily"),
        "Moon": ("Pearl (Moti)", "Silver", "Little finger", "Monday", "Chandra Gayatri / OM SOM SOMAYA NAMAH 108x"),
        "Mars": ("Red Coral (Moonga)", "Copper or Gold", "Ring finger", "Tuesday", "Hanuman Chalisa daily / Mangal Gayatri"),
        "Mercury": ("Emerald (Panna)", "Gold or Brass", "Little finger", "Wednesday", "Vishnu Sahasranama / Budh Gayatri 108x"),
        "Jupiter": ("Yellow Sapphire (Pukhraj)", "Gold", "Index finger", "Thursday", "Brihaspati Gayatri 108x Thursday"),
        "Venus": ("Diamond / White Zircon (Heera)", "Silver or Platinum", "Middle or Ring finger", "Friday", "Shukra Gayatri / Mahalakshmi Mantra"),
        "Saturn": ("Blue Sapphire (Neelam)", "Iron or Panchdhatu", "Middle finger", "Saturday", "Shani Gayatri / Hanuman Chalisa"),
        "Rahu": ("Hessonite (Gomed)", "Silver", "Middle finger", "Saturday", "Rahu Gayatri 108x"),
        "Ketu": ("Cat's Eye (Lehsunia)", "Silver or Gold", "Ring finger", "Tuesday or Thursday", "Ketu Gayatri / Ganesha Atharvashirsha"),
    }

    audit: dict[str, Any] = {}
    for p, (gname, metal, finger, day, mantra) in gem_map.items():
        p_house = planet_houses.get(p, 1)
        owned_houses = [h for h, info in house_lords.items() if info["lord"] == p]
        reasons = []
        status = "MANTRA_ONLY"

        kendra_owned = [h for h in owned_houses if h in (1, 4, 7, 10)]
        is_natural_benefic = p in ("Jupiter", "Venus", "Mercury") or (p == "Moon")
        has_kendradhipati = is_natural_benefic and len(kendra_owned) >= 2 and p != house_lords[1]["lord"]

        is_maraka = (p in maraka_lords) and p != house_lords[1]["lord"]
        is_badhaka = (p == badhaka_lord) and p != house_lords[1]["lord"]
        is_dusthana_lord = any(h in (6, 8, 12) for h in owned_houses) and p != house_lords[1]["lord"]
        is_in_8th = (p_house == 8)
        is_in_6th_or_12th = p_house in (6, 12) and p != house_lords[1]["lord"]
        is_trine_lord = p in trine_lords

        if p == "Mercury" and lagna_sign == "Pisces":
            status = "STRICTLY_AVOID"
            reasons.append("Rules 4th (Gemini) and 7th (Virgo) houses: suffers severe Kendradhipati Dosha (natural benefic owning two angles).")
            reasons.append("7th house is both prime Maraka Sthana and Badhaka Sthana for dual Pisces Lagna.")
            reasons.append("Wearing Emerald strengthens Maraka/Badhaka affliction, triggering nervous strain, marital/relationship friction, or digestive issues.")
            reasons.append("Remedy is strictly MANTRA & CHARITY: chant Vishnu Sahasranama or Budh Gayatri; donate green moong dal or feed green grass/spinach to cows on Wednesday.")
        elif is_in_8th:
            status = "AVOID"
            reasons.append(f"{p} is placed in the 8th house ({house_lords[8]['sign']}): direct gemstone wear activates 8th-house sudden obstacles, vulnerability, or stress.")
        elif is_dusthana_lord and not is_trine_lord:
            status = "AVOID"
            reasons.append(f"{p} rules Dusthana house(s) ({', '.join(str(h) for h in owned_houses if h in (6, 8, 12))}): gemstone wear can magnify obstacles, health vulnerabilities, or losses.")
        elif has_kendradhipati or (is_maraka and not is_trine_lord):
            status = "AVOID"
            reasons.append(f"{p} acts as Maraka/Kendradhipati ruler for {lagna_sign} Lagna; gemstone wear is not advised.")
        elif is_trine_lord and not is_in_8th and not is_in_6th_or_12th:
            status = "RECOMMENDED"
            reasons.append(f"{p} is an auspicious functional benefic ruling Trikona house(s) ({', '.join(str(h) for h in owned_houses if h in (1, 5, 9))}) and sits in House {p_house}.")
        else:
            status = "MANTRA_ONLY"
            reasons.append(f"{p} is not a primary trine lord for {lagna_sign} Lagna. Non-invasive mantra and charity are recommended over gemstone wear.")

        audit[p] = {
            "gem": gname,
            "status": status,
            "house": p_house,
            "owned_houses": owned_houses,
            "reasons": reasons,
            "metal": metal,
            "finger": finger,
            "day": day,
            "mantra": mantra
        }

    return {"lagna": lagna_sign, "lagna_lord": house_lords[1]["lord"], "audit": audit}


def compute_chart_ashtakavarga(pc: dict) -> dict[str, Any]:
    planets = pc.get("planets", {})
    lagna_sign = pc.get("meta", {}).get("lagna_sign", "") or (pc.get("lagna", {}) or {}).get("sign", "")
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


@dataclass
class QuestionConfluenceReport:
    question: str
    domain_key: str
    domain_title: str
    lagna: str
    lagna_lord: str
    moon_sign: str
    moon_nakshatra: str
    primary_house: int
    primary_house_sign: str
    primary_house_lord: str
    primary_lord_placement: str
    primary_lord_dignity: str
    is_lord_in_dusthana: bool
    dusthana_finding: str
    supporting_factors: list[str] = field(default_factory=list)
    karaka_findings: list[str] = field(default_factory=list)
    varga_findings: list[str] = field(default_factory=list)
    ashtakavarga_finding: str = ""
    transit_finding: str = ""
    triple_dasha_confluence: str = ""
    current_dasha: str = ""
    dasha_timeline: list[str] = field(default_factory=list)
    breakthrough_period: str = ""
    classical_verdict: str = ""
    root_cause_diagnosis: str = ""
    remedies: list[str] = field(default_factory=list)
    llm_synthesis: str = ""
    specialist_readings: dict = field(default_factory=dict)


AREA_TO_CONFLUENCE_DOMAIN: dict[str, str] = {
    # Direct keys
    "foreign_relocation": "foreign_relocation",
    "career_profession": "career_profession",
    "wealth_finances": "wealth_finances",
    "property_assets": "property_assets",
    "marriage_relationship": "marriage_relationship",
    "children_progeny": "children_progeny",
    "education_learning": "education_learning",
    "health_vitality": "health_vitality",
    "litigation_disputes": "litigation_disputes",
    "speech_neurology": "speech_neurology",
    # Frontend dropdown & semantic_question area keys & full option text
    "travel": "foreign_relocation",
    "foreign": "foreign_relocation",
    "relocation": "foreign_relocation",
    "relocate": "foreign_relocation",
    "foreign travel / relocation": "foreign_relocation",
    "foreign travel": "foreign_relocation",
    "foreign_travel": "foreign_relocation",
    "foreign relocation": "foreign_relocation",
    "abroad": "foreign_relocation",
    "career": "career_profession",
    "job": "career_profession",
    "job / career": "career_profession",
    "promotion": "career_profession",
    "promotion or raise": "career_profession",
    "business": "career_profession",
    "business / self-employment": "career_profession",
    "finance": "wealth_finances",
    "wealth": "wealth_finances",
    "money": "wealth_finances",
    "money / wealth": "wealth_finances",
    "property": "property_assets",
    "real_estate": "property_assets",
    "home": "property_assets",
    "property / home": "property_assets",
    "marriage": "marriage_relationship",
    "relationship": "marriage_relationship",
    "marriage / relationship": "marriage_relationship",
    "spouse": "marriage_relationship",
    "partner": "marriage_relationship",
    "children": "children_progeny",
    "progeny": "children_progeny",
    "education": "education_learning",
    "study": "education_learning",
    "education / study": "education_learning",
    "health": "health_vitality",
    "medical": "health_vitality",
    "disease": "health_vitality",
    "recovery": "health_vitality",
    "legal": "litigation_disputes",
    "litigation": "litigation_disputes",
    "court": "litigation_disputes",
    "dispute": "litigation_disputes",
    "legal / court matter": "litigation_disputes",
    "speech": "speech_neurology",
    "neurology": "speech_neurology",
    "neuro": "speech_neurology",
    "gemstone": "gemstones_remedies",
    "gemstones": "gemstones_remedies",
    "remedy": "gemstones_remedies",
    "remedies": "gemstones_remedies",
    "gemstones / remedies": "gemstones_remedies",
    "gemstones & remedies": "gemstones_remedies",
    "gemstone_remedies": "gemstones_remedies",
    "gemstones_remedies": "gemstones_remedies",
    "spiritual": "general_destiny",
    "spirituality": "general_destiny",
    "general": "general_destiny",
    "general_destiny": "general_destiny",
    "something else": "general_destiny",
    "general / something else": "general_destiny",
    "destiny": "general_destiny",
    "future": "general_destiny",
    "out_of_domain": "out_of_domain",
}

DOMAIN_TITLES_HI: dict[str, str] = {
    "career_profession": "Career, Rozgar Aur Padonnati",
    "marriage_relationship": "Vivah, Rishte Aur Jeevansathi",
    "wealth_finances": "Dhan, Sampatti Aur Aarthik Sthiti",
    "health_vitality": "Swasthya, Arogya Aur Urja",
    "children_progeny": "Santan, Parivar Aur Vansh",
    "foreign_relocation": "Videsh Yatra Aur Sthan Parivartan",
    "property_assets": "Bhoomi, Makaan Aur Sthir Sampatti",
    "litigation_disputes": "Court, Kacheri Aur Vivad",
    "education_learning": "Shiksha, Pratiyogita Aur Pariksha",
    "speech_neurology": "Vaani, Speech Aur Mansik Santulan",
    "gemstones_remedies": "Shubh Ratna Aur Vedic Upay",
    "general_destiny": "Sampurna Jeevan Vishleshan",
    "out_of_domain": "Jyotish Daayra Margdarshan",
}

DOMAIN_TITLES_TE: dict[str, str] = {
    "career_profession": "Career, Udyogam Mariyu Promotion",
    "marriage_relationship": "Vivaham, Bandhalu Mariyu Jeevithabhagswami",
    "wealth_finances": "Dhanam, Aasthi Mariyu Aarthika Sthiti",
    "health_vitality": "Aarogyam, Deerghayuvu Mariyu Shakthi",
    "children_progeny": "Santhanam, Kutumbam Mariyu Pillalu",
    "foreign_relocation": "Videsha Prayanam Mariyu Sthana Maarpu",
    "property_assets": "Sthalam, Illu Mariyu Fixed Assets",
    "litigation_disputes": "Court, Nyaya Vivadhalu",
    "education_learning": "Vidya, Parikshalu Mariyu Degrees",
    "speech_neurology": "Vaaku, Speech Mariyu Mansika Sthiratha",
    "gemstones_remedies": "Shubha Rathnamulu Mariyu Vedic Upayamulu",
    "general_destiny": "Sampoorna Jeevitha Vishleshana",
    "out_of_domain": "Jyotishya Paridhi Margadarshanam",
}

# High-intent multi-word keyphrases with high weight for deterministic classification
INTENT_KEYPHRASES: dict[str, list[str]] = {
    "general_destiny": [
        "what does my future hold", "tell me about my future", "how is my future",
        "how will things be", "how will my life be", "what is ahead for me", "life ahead",
        "future prospects", "overall life", "my horoscope", "general reading",
        "kaisa rahega samay", "kaisa hoga bhavishya", "aane wala samay", "meri kundli",
        "aage kya hoga", "koi problem to nahi", "meri life kaisa", "overall destiny",
        "upcoming phase", "upcoming years", "upcoming time", "life trajectory", "what does my chart say",
        "spiritual growth", "spiritual path", "meditation guidance", "meditation", "moksha",
        "guru guidance", "inner peace", "spirituality", "dharmic path", "soul purpose"
    ],
    "gemstones_remedies": [
        "which gemstone", "which stone", "gemstone will suit", "stone will suit",
        "gemstone suit", "stone suit", "gemstones suit", "stones suit",
        "what gemstone", "what stone", "gemstone for me", "stone for me",
        "gemstone should i wear", "stone should i wear", "wear gemstone", "wear stone",
        "lucky gemstone", "lucky stone", "gemstone recommendation", "which ratna",
        "ratna dharan", "gemstone advice", "which gemstone to wear", "which stone to wear",
        "gemstone to wear", "stone to wear", "suit me", "suitable gemstone", "suitable stone",
        "gemstone guidance", "gemstone consultation", "gemstones for me", "stones for me",
        "rudraksha", "wear rudraksha", "vedic remedy", "gemstone suit me", "stone suit me",
        "not suitable for my chart", "suitable for my chart",
    ],
    "foreign_relocation": [
        "move abroad", "moving abroad", "settle abroad", "settling abroad", "settle overseas",
        "go abroad", "going abroad", "relocate abroad", "relocating abroad", "shift abroad",
        "live abroad", "living abroad", "work abroad", "working abroad", "travel abroad",
        "abroad with family", "abroad for job", "abroad for partner", "move to another country",
        "moving to another country", "shift to foreign country", "shift to foreign", "shift foreign country",
        "move to foreign country", "settle in foreign country", "go to foreign country", "foreign country",
        "shift to another country", "permanent residency", "green card", "greencard",
        "pr visa", "work visa", "student visa", "citizenship test", "onsite opportunity",
        "emigrate", "immigrate", "foreign settlement", "foreign travel"
    ],
    "property_assets": [
        "buy property", "buy house", "buy flat", "buy land", "buy apartment", "buy plot",
        "buy a house", "buy a flat", "buy a property", "buy a home", "buy an apartment",
        "purchase property", "purchase house", "purchase flat", "purchase home", "purchase land",
        "purchase apartment", "purchase the apartment", "purchase an apartment", "purchase a flat", "purchase a house",
        "build house", "construct house", "property dispute", "real estate investment", "apartment in",
        "sell property", "sell house", "sell flat", "sell land", "registry hurdle"
    ],
    "career_profession": [
        "get promoted", "get promotion", "promotion and hike", "salary hike", "new job",
        "change job", "job switch", "switch job", "career growth", "career transition",
        "leadership role", "business expansion", "startup funding", "lose job", "layoff"
    ],
    "marriage_relationship": [
        "get married", "getting married", "love marriage", "arranged marriage", "will i marry",
        "when will i marry", "marital harmony", "relationship issues", "divorce case", "spouse fidelity"
    ],
    "children_progeny": [
        "have a baby", "have children", "have kids", "conceive baby", "get pregnant",
        "pregnancy complications", "child birth", "childbirth", "child welfare"
    ],
    "health_vitality": [
        "recover from illness", "recover from disease", "cure disease", "undergo surgery",
        "medical recovery", "chronic pain", "physical health", "vitality recovery"
    ],
    "litigation_disputes": [
        "win court case", "legal dispute", "win lawsuit", "court hearing", "police case",
        "property court case", "tenant dispute"
    ],
    "education_learning": [
        "clear exam", "pass exam", "upsc exam", "university admission", "college admission",
        "academic degree", "exam result"
    ],
    "speech_neurology": [
        "child speech delay", "speech delay", "start speaking", "stuttering issue", "autism diagnosis"
    ],
    "wealth_finances": [
        "get rich", "financial freedom", "stock market gains", "clear debts", "pay off loan", "wealth accumulation"
    ],
}


def is_general_trivia_inquiry(question: str) -> bool:
    """Detects factual encyclopedic questions, definitions, trivia, or third-person entities."""
    if not question:
        return False
    ql = question.lower().strip()

    # Explicit non-astrological entities / definition keywords
    trivia_entities = [
        "bitcoin", "crypto", "cryptocurrency", "ethereum", "blockchain", "dogecoin", "solana",
        "prime minister", "president", "capital of", "speed of light", "chemical formula",
        "chatgpt", "openai", "machine learning", "artificial intelligence", "who invented",
        "who discovered", "who wrote", "who painted", "who is the prime minister", "who is the president",
        "who won", "what is the capital", "capital of france", "capital of india"
    ]
    if any(e in ql for e in trivia_entities):
        personal_astro = ("my", "mine", "kundli", "kundali", "chart", "horoscope", "birth chart", "in my")
        if not any(re.search(r"\b" + re.escape(p) + r"\b", ql) for p in personal_astro):
            return True

    # Generic interrogatives without 1st/2nd person or astrological keywords
    if re.search(r"^(?:what|who|where|when|which|how|why)\s+(?:is|are|was|were|does|did)\s+(?:the\s+|a\s+|an\s+)?", ql):
        personal_terms = (
            "my", "mine", "me", "i", "myself", "our", "us", "chart", "kundli", "kundali",
            "horoscope", "dasha", "transit", "lagna", "rashi", "future", "career", "job",
            "marriage", "marry", "spouse", "husband", "wife", "child", "children", "baby",
            "health", "disease", "surgery", "remedy", "gemstone", "ratna", "property", "wealth",
            "mera", "meri", "mere", "mujhe", "apna", "apni", "naa", "naku", "nenu"
        )
        if not any(re.search(r"\b" + re.escape(t) + r"\b", ql) for t in personal_terms):
            return True

    return False


def is_strictly_out_of_domain(question: str) -> bool:
    """True only when the question is unequivocally outside life/astrology.

    Trivia and technical patterns run first. Over-generic tokens such as
    ``when`` / ``year`` / ``problem`` are not treated as in-domain on their
    own — they used to short-circuit every question before the trivia check.
    """
    if not question:
        return False
    q_low = question.lower().strip()

    if is_general_trivia_inquiry(question):
        return True

    non_astro_patterns = [
        r"\b(python|javascript|java|c\+\+|html|css|sql|docker|kubernetes|api|backend|frontend|react|fastapi|django)\b",
        r"\b(write\s+code|debug|function|algorithm|binary\s+search|regular\s+expression|regex|git\s+push|compile)\b",
        r"\b(recipe|ingredients|bake|boil|cook\s+a|how\s+to\s+make\s+(?:cake|pasta|pizza|biryani|soup))\b",
        r"\b(fix\s+(?:a\s+|an\s+|the\s+)?(?:leaky\s+|broken\s+|flat\s+)?(?:faucet|tire|pipe|puncture|leak|printer|keyboard|wifi|router|engine|car|bike|laptop|phone))\b",
        r"\b(capital\s+of|who\s+(?:wrote|invented|discovered|painted|directed|won)|speed\s+of\s+light|chemical\s+formula)\b",
        r"\b(calculate\s+derivative|solve\s+equation|\d+\s*[\+\-\*\/]\s*\d+\s*=)\b",
        r"\b(translate\s+(?:this|word|text)\s+to|what\s+is\s+the\s+meaning\s+of\s+the\s+word\s+[\"'\w]+)\b",
    ]
    for pat in non_astro_patterns:
        if re.search(pat, q_low):
            return True

    # Personal / astrological life tokens: any hit means IN-DOMAIN.
    astro_life_tokens = [
        "astrology", "astrological", "horoscope", "kundli", "kundali", "chart", "birth", "dasha", "transit",
        "gochar", "nakshatra", "graha", "planet", "lagna", "ascendant", "rashi", "bhav", "bhava", "house",
        "life", "future", "destiny", "career", "job", "work", "business", "promotion", "money", "wealth",
        "finance", "salary", "debt", "loan", "property", "marriage", "marry", "wedding", "husband", "wife",
        "spouse", "partner", "love", "relationship", "divorce", "child", "children", "baby", "pregnancy",
        "conceive", "education", "study", "exam", "health", "disease", "illness", "surgery", "recovery",
        "travel", "foreign", "abroad", "visa", "relocation", "court", "case", "legal", "enemy",
        "speech", "cognitive", "development", "outlook", "delay", "growth", "intellect", "mind",
        "gemstone", "stone", "ratna", "rudraksha", "remedy", "upaya", "mantra", "puja", "chant",
        "luck", "fortune", "bhagya", "timing", "will i", "how will",
        "kaisa", "samay", "aage", "bhavishya", "meri", "mera", "mere", "mujhe", "apna", "apni", "shubh",
        "trouble", "solution", "prospect", "prospects", "ahead", "focus",
    ]
    for tok in astro_life_tokens:
        if re.search(r"\b" + re.escape(tok) + r"\b", q_low):
            return False

    return False


def _fallback_detect_domain(question: str, route: Any = None, area: str = "") -> str:
    """Keyword / MiniLM domain routing used only when the LLM planner is down."""
    if area:
        mapped = AREA_TO_CONFLUENCE_DOMAIN.get(area.lower().strip())
        if mapped:
            return mapped

    q_lower = (question or "").lower().strip()

    if is_strictly_out_of_domain(question):
        return "out_of_domain"

    # A question that names its subject outright needs no soft router.
    try:
        from question_domain import keyword_domain
        named = keyword_domain(question)
        if named:
            return named
    except Exception:                                                 # noqa: BLE001
        pass

    # Phrase-level high intent scoring (e.g. "move abroad", "win court case")
    phrase_scores: dict[str, int] = {}
    for d_key, phrases in INTENT_KEYPHRASES.items():
        for phrase in phrases:
            if phrase in q_lower:
                phrase_scores[d_key] = phrase_scores.get(d_key, 0) + 5
    if phrase_scores:
        return max(phrase_scores, key=phrase_scores.get)

    # Not the semantic router: without sentence-transformers (production) it is a hashed
    # word-overlap stand-in that cannot tell "girlfriend" from "children". Ask the model.
    try:
        from llm.question_planner import classify_area
        picked = classify_area(question)
    except Exception:                                                 # noqa: BLE001
        picked = None
    if picked:
        pk_area, pk_scope = picked
        if not pk_scope:
            return "out_of_domain"
        if pk_area != "general_destiny":
            return pk_area

    scores: dict[str, int] = {}
    for d_key, d_cfg in DOMAINS_CONFIG.items():
        if d_key in ("out_of_domain", "general_destiny"):
            continue
        for kw in d_cfg["keywords"]:
            if re.search(r"\b" + re.escape(kw) + r"\b", q_lower):
                scores[d_key] = scores.get(d_key, 0) + 1

    if not scores:
        return "general_destiny"

    return max(scores, key=scores.get)


def detect_domain(question: str, route: Any = None, area: str = "") -> str:
    """Back-compat alias for the keyword fallback path."""
    return _fallback_detect_domain(question, route=route, area=area)


def _normalize_dropdown_area(area: str) -> str:
    """Map frontend dropdown value to a canonical life-area key."""
    raw = (area or "").strip()
    if not raw:
        return ""
    try:
        import semantic_question as SQ
        return SQ.normalize_area(raw) or raw.lower()
    except Exception:
        return raw.lower()


def _resolve_confluence_domain(
    question: str,
    *,
    domain_override: str = "",
    route: Any = None,
) -> str:
    """Resolve DOMAINS_CONFIG key from dropdown + question.

    Dropdown values are short keys like ``travel`` — never pass them straight
    into ``DOMAINS_CONFIG`` (that used to fall back to health_vitality).
    Planner life_area keys land here already canonical.
    """
    raw = (domain_override or "").strip()
    if raw in DOMAINS_CONFIG:
        return raw
    area = _normalize_dropdown_area(domain_override)
    if area:
        mapped = AREA_TO_CONFLUENCE_DOMAIN.get(area)
        if mapped:
            return mapped
        if area in DOMAINS_CONFIG:
            return area
    return _fallback_detect_domain(question, route=route, area=area or domain_override)


def analyze_question_confluence(
    pc: dict,
    question: str,
    domain_override: str = "",
    route: Any = None,
    target_planet: str = "",
) -> QuestionConfluenceReport:
    """Rigorous classical Vedic confluence analyzer for ANY life question."""
    domain_key = _resolve_confluence_domain(question, domain_override=domain_override, route=route)

    cfg = DOMAINS_CONFIG.get(domain_key, DOMAINS_CONFIG["career_profession"])

    # 1. Base Natal Data
    lagna_raw = pc.get("lagna", {})
    lagna_sign = lagna_raw.get("sign") if isinstance(lagna_raw, dict) else str(pc.get("meta", {}).get("lagna_sign", "Aries"))
    if not lagna_sign:
        lagna_sign = "Aries"
    lagna_idx = sign_index(lagna_sign)
    lagna_lord = SIGN_LORDS.get(lagna_sign, "Mars")

    planets = pc.get("planets", {})
    moon_data = planets.get("Moon", {})
    moon_sign = moon_data.get("sign", "")
    moon_nak = moon_data.get("nakshatra", "")
    moon_pada = moon_data.get("pada", moon_data.get("nakshatra_pada", 1))

    # 2. Primary House & Lord
    prim_h = cfg["primary_house"]
    prim_sign_idx = (lagna_idx + prim_h - 1) % 12
    prim_sign = SIGNS[prim_sign_idx]
    prim_lord = SIGN_LORDS.get(prim_sign, "")

    lord_data = planets.get(prim_lord, {})
    lord_sign = lord_data.get("sign", "")
    lord_h = int(lord_data.get("house", 1))
    lord_deg = float(lord_data.get("degree_in_sign", lord_data.get("degrees", 0)))
    lord_dig = get_dignity(prim_lord, lord_sign) if (prim_lord and lord_sign) else "neutral"

    is_in_dusthana = lord_h in {6, 8, 12}
    if is_in_dusthana:
        dusthana_finding = f"CRITICAL: Lord of the {prim_h}th house ({prim_lord}) occupies the {lord_h}th Dusthana (Trik house in {lord_sign}), indicating significant delay, structural vulnerability, or non-linear realization."
    else:
        dusthana_finding = f"Lord of the {prim_h}th house ({prim_lord}) is placed in House {lord_h} ({lord_sign}, {lord_dig.replace('_', ' ')} status), providing clean structural support without direct Dusthana (6/8/12) affliction."

    # 3. Supporting Houses
    supp_findings = []
    for sh in cfg["supporting_houses"]:
        sh_sign_idx = (lagna_idx + sh - 1) % 12
        sh_sign = SIGNS[sh_sign_idx]
        sh_lord = SIGN_LORDS.get(sh_sign, "")
        sh_data = planets.get(sh_lord, {})
        sh_h = sh_data.get("house", 1)
        sh_s = sh_data.get("sign", "")
        sh_dig = get_dignity(sh_lord, sh_s) if sh_s else "neutral"
        
        # Check planets occupying supporting house
        occupants = [p for p, pdata in planets.items() if int(pdata.get("house", 0)) == sh and p != "Lagna"]
        occ_str = f" occupied by {', '.join(occupants)}" if occupants else " (no direct occupants)"
        
        supp_findings.append(
            f"House {sh} ({sh_sign}) governed by {sh_lord} in {sh_s} (House {sh_h}, {sh_dig.replace('_', ' ')} status){occ_str}."
        )

    # 4. Natural Karakas Analysis
    karaka_findings = []
    for k in cfg["karakas"]:
        k_data = planets.get(k, {})
        k_s = k_data.get("sign", "")
        k_h = k_data.get("house", 1)
        k_nak = k_data.get("nakshatra", "")
        k_dig = get_dignity(k, k_s) if k_s else "neutral"
        comb = " [COMBUST]" if k_data.get("combust") else ""
        retro = " [RETROGRADE]" if k_data.get("retrograde") else ""
        role = cfg["karaka_roles"].get(k, f"Significator of {cfg['title']}")

        # Check afflictions
        k_afflictions = []
        if k_h in {6, 8, 12}:
            k_afflictions.append(f"placed in Dusthana House {k_h}")
        if k_dig == "debilitated":
            k_afflictions.append("debilitated")
        if comb:
            k_afflictions.append("combust Sun")

        aff_str = f" (Affliction: {', '.join(k_afflictions)})" if k_afflictions else " (Clean / Dignified)"
        karaka_findings.append(
            f"{k} ({role}): Seated in {k_s} in House {k_h} under {k_nak} ({k_dig.replace('_', ' ')} status){comb}{retro}{aff_str}."
        )

    # 5. Divisional Cross-Verification (Vargas)
    varga_findings = []
    div_dict = pc.get("divisional", {})
    
    # Check D9 Navamsha (Fundamental for all life areas)
    d9 = div_dict.get("D9", {})
    if d9:
        d9_lagna = d9.get("Lagna", "")
        d9_moon = d9.get("Moon", "")
        d9_prim_lord = d9.get(prim_lord, "")
        d9_karaka_top = d9.get(cfg["karakas"][0], "") if cfg["karakas"] else ""
        varga_findings.append(
            f"D9 (Navamsha — Soul and Dharmic Foundation): Lagna is {d9_lagna}. Moon is placed in {d9_moon} ({'Neechamsa / Debilitated' if d9_moon == 'Scorpio' else 'Dignified'}). "
            f"Primary ruler {prim_lord} occupies {d9_prim_lord}; Karaka {cfg['karakas'][0] if cfg['karakas'] else ''} is in {d9_karaka_top}."
        )

    # Check specialized varga for the specific life domain
    if domain_key == "children_progeny" and "D7" in div_dict:
        d7 = div_dict.get("D7", {})
        d7_lagna = d7.get("Lagna", "")
        d7_5th_lord = d7.get(prim_lord, "")
        d7_jup = d7.get("Jupiter", "")
        d7_venus = d7.get("Venus", "")
        varga_findings.append(
            f"D7 (Saptamsha — Children & Lineage Division): Lagna is {d7_lagna}. 5th house ruler {prim_lord} occupies {d7_5th_lord} "
            f"({'Own Sign in Cancer' if prim_lord == 'Moon' and d7_5th_lord == 'Cancer' else 'Dignified'}). "
            f"Putrakaraka Jupiter is placed in {d7_jup} ({'Own Sign in Pisces' if d7_jup == 'Pisces' else 'Dignified'}), Venus in {d7_venus} ({'Exalted in Pisces' if d7_venus == 'Pisces' else 'Dignified'}). "
            f"Classical D7 confirmation indicates strong, fertile foundational capacity for progeny."
        )
    elif domain_key == "speech_neurology" and "D3" in div_dict:
        d3 = div_dict.get("D3", {})
        varga_findings.append(f"D3 (Drekkana — Motor & Throat Faculties): Lagna is {d3.get('Lagna')}, Mercury in {d3.get('Mercury')}, Mars in {d3.get('Mars')}.")
    elif domain_key == "career_profession" and "D10" in div_dict:
        d10 = div_dict.get("D10", {})
        varga_findings.append(f"D10 (Dasamsha — Career Karma & Executive Status): Lagna is {d10.get('Lagna')}, Sun in {d10.get('Sun')}, Saturn in {d10.get('Saturn')}, 10th Lord {prim_lord} in {d10.get(prim_lord)}.")
    elif domain_key == "education_learning" and "D24" in div_dict:
        d24 = div_dict.get("D24", {})
        varga_findings.append(f"D24 (Chaturvimshamsha — Intellectual Acumen): Lagna is {d24.get('Lagna')}, Mercury in {d24.get('Mercury')}, Jupiter in {d24.get('Jupiter')}.")
    elif domain_key == "wealth_finances" and "D2" in div_dict:
        d2 = div_dict.get("D2", {})
        varga_findings.append(f"D2 (Hora — Wealth & Resource Capacity): Lagna is {d2.get('Lagna')}, Jupiter in {d2.get('Jupiter')}, Mercury in {d2.get('Mercury')}.")
    elif domain_key == "property_assets" and "D4" in div_dict:
        d4 = div_dict.get("D4", {})
        varga_findings.append(f"D4 (Chaturthamsha — Fixed Assets & Real Estate): Lagna is {d4.get('Lagna')}, Mars in {d4.get('Mars')}, 4th Lord {prim_lord} in {d4.get(prim_lord)}.")
    elif domain_key == "foreign_relocation" and "D12" in div_dict:
        d12 = div_dict.get("D12", {})
        varga_findings.append(f"D12 (Dwadashamsha — Distant Roots & Relocation): Lagna is {d12.get('Lagna')}, Rahu in {d12.get('Rahu')}, 12th Lord in {d12.get(prim_lord)}.")

    # Check D30 Trimsamsha (for afflictions, health, and karmic hurdles)
    if domain_key in {"speech_neurology", "health_vitality", "litigation_disputes"}:
        d30 = div_dict.get("D30", {})
        if d30:
            d30_lagna = d30.get("Lagna", "")
            d30_rahu = d30.get("Rahu", "")
            d30_merc = d30.get("Mercury", "")
            d30_sat = d30.get("Saturn", "")
            d30_mars = d30.get("Mars", "")
            varga_findings.append(
                f"D30 (Trimsamsha — Karmic Afflictions & Health): Lagna is {d30_lagna}. Mercury is in {d30_merc} (afflicted by Rahu in {d30_rahu}); "
                f"Saturn in {d30_sat}, Mars in {d30_mars}. Points to intrinsic sensitivities that manifest under malefic sub-periods."
            )

    # 6. Dasha Timeline Analysis (Age-Aware & Life-Stage Aware)
    vim = pc.get("vimshottari", {})
    curr_ad_list = vim.get("current_md_antardashas", [])
    md_seq = vim.get("sequence", [])

    dob_str = str(pc.get("meta", {}).get("birth_date") or pc.get("meta", {}).get("dob") or "")
    birth_year = int(dob_str[:4]) if (len(dob_str) >= 4 and dob_str[:4].isdigit()) else 2000
    current_year = date.today().year
    current_age = current_year - birth_year

    is_adult_milestone = domain_key in {"career_profession", "marriage_relationship", "children_progeny", "wealth_finances"}
    is_child = current_age < 18

    timeline_items = []
    current_dasha_str = "Dasha timeline active."
    breakthrough_period_str = ""

    if is_child and is_adult_milestone:
        # Long-term life timeline for young native
        adult_start_year = birth_year + 20
        adult_peak_year = birth_year + 30

        # Find the major Mahadasha that governs their 20s and 30s
        prime_md = None
        for md in md_seq:
            md_start_yr = int(str(md.get("start", "2000"))[:4])
            md_end_yr = int(str(md.get("end", "2100"))[:4])
            if md_start_yr <= adult_start_year <= md_end_yr or md_start_yr <= adult_peak_year <= md_end_yr:
                prime_md = md
                break

        current_md_name = md_seq[1].get("md_lord") if len(md_seq) > 1 else "Active Period"
        current_dasha_str = f"Childhood Foundation: {current_md_name} Mahadasha (until {md_seq[1].get('end') if len(md_seq) > 1 else 'maturity'})"

        if prime_md:
            p_lord = prime_md.get("md_lord", "Jupiter")
            p_start = prime_md.get("start", "")
            p_end = prime_md.get("end", "")
            
            if domain_key == "career_profession":
                breakthrough_period_str = f"{p_lord} Mahadasha ({p_start} to {p_end}, Ages 18–34)"
                timeline_items.append(f"<b>Formative Preparation Phase:</b> Current {current_md_name} period focuses on foundational learning, skill development, and intellectual grounding.")
                timeline_items.append(f"<b>Career Launch & Entry Window:</b> Beginning of {p_lord} Mahadasha (~{int(p_start[:4])+2} to {int(p_start[:4])+6}, Ages 20–24) marks entry into professional life.")
                timeline_items.append(f"<b>Major Executive Rise & Peak Status:</b> Mid-{p_lord} Mahadasha (~{int(p_start[:4])+8} to {int(p_start[:4])+14}, Ages 26–32) delivers peak professional authority and career consolidation.")
            elif domain_key == "marriage_relationship":
                marriage_start = int(p_start[:4]) + 6
                marriage_end = int(p_start[:4]) + 11
                breakthrough_period_str = f"{p_lord} Mahadasha (Primary Marriage Window: {marriage_start}–{marriage_end}, Ages 24–29)"
                timeline_items.append(f"<b>Early Life Focus:</b> Current period prioritizes personal growth, emotional maturity, and education.")
                timeline_items.append(f"<b>Prime Marriage Activation Window:</b> {p_lord} period during {marriage_start}–{marriage_end} (Ages 24–29), particularly under supportive Venus/Mercury sub-periods.")
                timeline_items.append(f"<b>Long-term Marital Stability:</b> Subsequent dasha cycles consolidate family life and joint asset building.")
            elif domain_key == "children_progeny":
                progeny_start = int(p_start[:4]) + 8
                progeny_end = int(p_start[:4]) + 13
                breakthrough_period_str = f"{p_lord} Mahadasha (Progeny Window: {progeny_start}–{progeny_end}, Ages 26–31)"
                timeline_items.append(f"<b>Life Horizon:</b> Progeny promise is rooted in the 5th house ({prim_sign}) and will activate naturally following marriage in adulthood.")
                timeline_items.append(f"<b>Primary Childbirth Window:</b> Active during {p_lord} Mahadasha ({progeny_start}–{progeny_end}, Ages 26–31) when 5th house and Jupiter significator are energized.")
            else:
                breakthrough_period_str = f"{p_lord} Mahadasha ({p_start} to {p_end})"
                timeline_items.append(f"<b>Long-term Milestone:</b> Major life expansion activates during {p_lord} Mahadasha ({p_start}–{p_end}).")
        else:
            breakthrough_period_str = "Adulthood Planetary Cycle (Ages 22–30)"
            timeline_items.append("<b>Adulthood Milestone:</b> Activates upon maturity during the subsequent major planetary periods.")
    else:
        # Near-term / active dasha timeline for current life phase
        for ad in curr_ad_list:
            status = ad.get("status", "")
            p_ad = ad.get("ad_lord", "")
            start_d = ad.get("start", "")
            end_d = ad.get("end", "")
            
            lbl = f"{p_ad} Sub-Period ({start_d} to {end_d})"
            if status == "current":
                current_dasha_str = f"Running: {lbl}"
                timeline_items.append(f"<b>Current Active Phase:</b> {lbl} — Brings intense restructuring and disciplined foundation building.")
            elif status == "future" and not breakthrough_period_str:
                if p_ad in (cfg["karakas"] + [lagna_lord, "Jupiter", "Venus"]):
                    breakthrough_period_str = f"{p_ad} Antardasha ({start_d} to {end_d})"
                    timeline_items.append(f"<b>Major Breakthrough Window:</b> {lbl} — Classical timing for rapid stabilization, breakthroughs, and developmental acceleration.")
                else:
                    timeline_items.append(f"<b>Upcoming Phase:</b> {lbl}")
            elif status == "past":
                timeline_items.append(f"<b>Past Formative Phase:</b> {lbl} — Initial trigger and formative manifestation of the condition.")

        if not breakthrough_period_str and curr_ad_list:
            breakthrough_period_str = f"Upcoming Antardasha ({curr_ad_list[-1].get('ad_lord')} starting {curr_ad_list[-1].get('start')})"

    # 7. Ashtakavarga (SAV & BAV) Strength Analysis
    av_data = compute_chart_ashtakavarga(pc)
    sav = av_data.get("sav", {})
    prim_b = sav.get(prim_sign, 28)
    if prim_b >= 30:
        av_eval = f"amplified manifestation capacity and strong traction ({prim_b} SAV Bindus, well above 28-point average)"
    elif prim_b >= 28:
        av_eval = f"stable structural support ({prim_b} SAV Bindus, meeting the classical 28-point benchmark)"
    else:
        av_eval = f"thinner baseline requiring disciplined pacing and perseverance ({prim_b} SAV Bindus, below 28-point average)"
    ashtakavarga_finding = f"House {prim_h} ({prim_sign}) holds {prim_b} Sarvāṣṭakavarga (SAV) Bindus — indicating {av_eval}."

    # 8. Live Planetary Transits (Gochar) & Chandra Naadi Alignment
    t_now = date.today()
    transits = get_live_transit_positions(t_now)
    jup_s = transits.get("Jupiter", "")
    sat_s = transits.get("Saturn", "")
    rahu_s = transits.get("Rahu", "")
    ketu_s = transits.get("Ketu", "")
    mars_s = transits.get("Mars", "")
    moon_s = transits.get("Moon", "")

    transit_items = []
    if jup_s:
        j_b = sav.get(jup_s, 28)
        j_h = house_from_lagna(jup_s, lagna_sign)
        transit_items.append(f"Transit Jupiter in House {j_h} ({jup_s}, {j_b} SAV Bindus)")
    if sat_s:
        s_b = sav.get(sat_s, 28)
        s_h = house_from_lagna(sat_s, lagna_sign)
        transit_items.append(f"Transit Saturn in House {s_h} ({sat_s}, {s_b} SAV Bindus)")
    if rahu_s and ketu_s:
        r_h = house_from_lagna(rahu_s, lagna_sign)
        k_h = house_from_lagna(ketu_s, lagna_sign)
        transit_items.append(f"Rahu-Ketu Axis in Houses {r_h}/{k_h} ({rahu_s}/{ketu_s})")
    if mars_s:
        m_h = house_from_lagna(mars_s, lagna_sign)
        transit_items.append(f"Transit Mars in House {m_h} ({mars_s})")

    # Chandra Naadi / Real-Time Lunar Mindset Context for the Question
    lunar_naadi_note = ""
    try:
        from transit_planet_analysis import analyze_transit_planet
        tp_res = analyze_transit_planet(pc, analysis_datetime=datetime.now())
        mind_data = tp_res.get("state_of_mind_now") or {}
        if mind_data.get("fast_trigger"):
            lunar_naadi_note = f"Lunar Trigger: Transit Moon in {mind_data.get('sign_occupied', moon_s)} triggers active focus on {mind_data.get('fast_trigger')}."
    except Exception:
        pass

    transit_finding = f"Active Gochar: {', '.join(transit_items) if transit_items else 'Transits aligned with natal matrix.'}."
    if lunar_naadi_note:
        transit_finding += f" {lunar_naadi_note}"

    # 9. Triple Dasha Confluence (Vimshottari + Jaimini Chara + Yogini)
    jaimini = pc.get("jaimini", {})
    chara = jaimini.get("chara_dasha", {})
    curr_chara_m = chara.get("current_maha", {}) if isinstance(chara, dict) else {}
    curr_chara_a = chara.get("current_antar", {}) if isinstance(chara, dict) else {}
    chara_str = f"{curr_chara_m.get('sign', '')}-{curr_chara_a.get('sign', '')}" if curr_chara_m.get("sign") else ""

    yogini = pc.get("yogini", {})
    curr_yog = yogini.get("current_yogini", {}) if isinstance(yogini, dict) else {}
    yog_str = f"{curr_yog.get('yogini', '')} ({curr_yog.get('lord', '')})" if curr_yog.get("yogini") else ""

    triple_dasha_parts = [f"Vimshottari: {current_dasha_str}"]
    if chara_str:
        triple_dasha_parts.append(f"Jaimini Chara Dasha: {chara_str}")
    if yog_str:
        triple_dasha_parts.append(f"Yogini Dasha: {yog_str}")
    triple_dasha_confluence = " · ".join(triple_dasha_parts)

    # 10. Classical Verdict & Root Cause Diagnostic
    if domain_key == "gemstones_remedies":
        gem_audit_res = audit_chart_gemstones(pc)
        audit = gem_audit_res.get("audit", {})

        rec_gems = []
        rec_names = []
        forbidden_gems = []
        mantra_gems = []

        for p, inf in audit.items():
            gname = inf["gem"]
            status = inf["status"]
            metal = inf["metal"]
            finger = inf["finger"]
            day = inf["day"]
            mantra = inf["mantra"]
            r_str = "; ".join(inf["reasons"])
            if status == "RECOMMENDED":
                rec_names.append(gname)
                rec_gems.append(f"Suitable Gemstone for {p}: Wear **{gname}** set in {metal} on the {finger} on {day} morning during Shukla Paksha.")
            elif status in ("STRICTLY_AVOID", "AVOID"):
                forbidden_gems.append(f"STRICTLY AVOID {gname} ({p}): {r_str}.")
            else:
                mantra_gems.append(f"Propitiate {p} ({gname}) via Mantra & Seva: {mantra}.")

        # Specific stone/planet comes from the planner (or caller), not a regex.
        planet_by_lower = {
            "sun": "Sun", "moon": "Moon", "mars": "Mars", "mercury": "Mercury",
            "jupiter": "Jupiter", "venus": "Venus", "saturn": "Saturn",
            "rahu": "Rahu", "ketu": "Ketu",
        }
        chosen = planet_by_lower.get(str(target_planet or "").strip().lower(), "")

        if chosen and chosen in audit:
            t_inf = audit[chosen]
            t_gem = t_inf["gem"]
            t_reasons = " ".join(t_inf["reasons"])
            if t_inf["status"] in ("STRICTLY_AVOID", "AVOID"):
                verdict = (
                    f"{t_gem} ({chosen}) is STRICTLY CONTRAINDICATED and NOT SUITABLE for your {lagna_sign} Ascendant chart. "
                    f"{t_reasons} Wearing this stone will amplify Maraka, Badhaka, or pressure energies rather than protecting you. "
                    f"Safe Vedic alternative: Do not wear the physical gemstone; balance {chosen} non-invasively through {t_inf['mantra']} and charitable seva."
                )
                root_cause_diagnosis = (
                    f"Classical Jyotish Lordship Contraindication: For {lagna_sign} Lagna, {chosen} governs House(s) "
                    f"{', '.join(str(h) for h in t_inf['owned_houses'])} and sits in House {t_inf['house']}. {t_reasons}"
                )
                remedies = [
                    f"CRITICAL: Strictly avoid wearing {t_gem}. Do NOT enhance {chosen} with physical gemstones.",
                    f"Prescribed Upaya for {chosen}: {t_inf['mantra']}.",
                ]
                if rec_gems:
                    remedies.append(f"Approved Auspicious Gemstone for Chart: {rec_gems[0]}")
            elif t_inf["status"] == "RECOMMENDED":
                verdict = (
                    f"{t_gem} ({chosen}) is HIGHLY AUSPICIOUS and SUITABLE for your {lagna_sign} Ascendant chart. "
                    f"{t_reasons} Wearing this gemstone channels vital protective and cognitive energy."
                )
                root_cause_diagnosis = (
                    f"Classical Benefic Trikona Resonance: {chosen} is a prime functional benefic for {lagna_sign} Lagna. {t_reasons}"
                )
                remedies = [
                    f"Wear {t_gem} set in {t_inf['metal']} on the {t_inf['finger']} on {t_inf['day']} morning during Shukla Paksha.",
                    f"Root Mantra: {t_inf['mantra']}",
                ]
            else:
                verdict = (
                    f"{t_gem} ({chosen}) is NOT recommended for direct physical gemstone wear for your {lagna_sign} chart. "
                    f"{t_reasons} Propitiate {chosen} safely using {t_inf['mantra']} instead."
                )
                root_cause_diagnosis = (
                    f"Planetary Remedial Guidance: {chosen} does not rule an unblemished Trikona house for {lagna_sign} Lagna. {t_reasons}"
                )
                remedies = [
                    f"Remedial Mantra: {t_inf['mantra']}",
                ]
                if rec_gems:
                    remedies.append(f"Approved Auspicious Gemstone: {rec_gems[0]}")
        else:
            # General gemstone inquiry — caution list from THIS chart's AVOID set.
            avoid_names = [
                f"{inf['gem']} ({p})"
                for p, inf in audit.items()
                if inf.get("status") in ("STRICTLY_AVOID", "AVOID")
            ]
            caution = ""
            if avoid_names:
                caution = (
                    f" Caution: Avoid {', '.join(avoid_names[:3])}"
                    f"{' and stones of planets in the 8th house' if len(avoid_names) > 3 else ''}."
                )
            if rec_gems:
                root_cause_diagnosis = (
                    f"For your {lagna_sign} Ascendant, gemstone suitability is strictly governed by the functional benefic Trikona houses (1st, 5th, 9th). "
                    f"Your primary Life Stone is ruled by Lagna Lord {lagna_lord} ({prim_sign}). "
                    f"Gemstones for Dusthana (6th, 8th, 12th) and Maraka/Kendradhipati lords must strictly be avoided to prevent magnifying life obstacles."
                )
                verdict = (
                    f"Based on your {lagna_sign} Lagna and planetary positions, the most auspicious and suitable gemstone(s) for you are: "
                    f"{', '.join(rec_names)}. Wearing these in the recommended metal and finger will channel maximum positive energy."
                    f"{caution}"
                )
            else:
                root_cause_diagnosis = (
                    f"For your {lagna_sign} Lagna, direct gemstone wear requires caution. "
                    f"Planetary mantras and charitable seva offer safe, non-invasive remedial balance."
                )
                verdict = (
                    f"A direct primary gemstone is not recommended right now. Chanting root mantras and performing targeted charitable upayas "
                    f"is the most effective, safe path for your chart."
                    f"{caution}"
                )
            remedies = []
            if rec_gems:
                remedies.extend(rec_gems[:2])
            if forbidden_gems:
                remedies.extend(forbidden_gems[:2])
            if not remedies:
                remedies.append(f"Chant Lagna Lord ({lagna_lord}) Root Mantra daily to strengthen overall planetary shield.")
    elif domain_key == "out_of_domain":
        root_cause_diagnosis = (
            f"This specific question falls outside the purview of classical Vedic astrology and natal chart interpretation. "
            f"Vedic Jyotish is an empirical, time-honored science designed to illuminate human life dimensions — "
            f"including physical vitality, vocational trajectory, relationships, family lineage, material prosperity, and planetary timing. "
            f"Non-astrological technical, coding, trivia, or factual inquiries operate independently of natal planetary positions."
        )
        verdict = (
            f"Your question pertains to a non-astrological topic outside natal chart analysis. "
            f"We encourage you to ask any question regarding your life direction, career, relationships, health, wealth, "
            f"or planetary periods (dashas), and your chart will reveal deep, classical guidance."
        )
        remedies = [
            f"Daily spiritual grounding: Chant the Gayatri Mantra or Lagna Lord ({lagna_lord}) Root Mantra for mental clarity and overall life alignment.",
            f"Feel free to ask a focused question regarding your personal life journey, career milestones, relationships, or planetary remedies."
        ]
    elif domain_key == "general_destiny":
        root_cause_diagnosis = (
            f"Your chart indicates an active, evolving life chapter anchored by Janma Lagna {lagna_sign} (governed by {lagna_lord}) "
            f"and Moon in {moon_sign} under {moon_nak}. Current life developments and inner pacing are guided by your running {current_dasha_str} period. "
            f"House 1 holds {prim_b} SAV Bindus, establishing a firm constitutional baseline, while ongoing Gochar transits "
            f"guide the progressive unfoldment of your static potential."
        )
        verdict = (
            f"Overall life prospects remain structurally supported under your {lagna_sign} Lagna. "
            f"The ongoing operating period emphasizes focused foundation building, leading into the decisive "
            f"{breakthrough_period_str} as your primary classical catalyst for expansion and milestone realization."
        )
        remedies = []
        if cfg["karakas"]:
            top_k = cfg["karakas"][0]
            remedies.append(f"Strengthen Natural Karaka ({top_k}): Chant the {top_k} Gayatri Mantra or perform charitable seva (e.g. Surya Arghya for Sun, Jal Abhishek for Moon).")
        remedies.append(f"Energize Lagna Lord ({lagna_lord}): Daily spiritual grounding, meditation, and chanting the Lagna lord's root mantra to fortify overall constitutional resilience.")
    elif is_in_dusthana:
        # SAV strength: 28+ is strong, <28 is weak — never call 23 a "solid floor"
        if prim_b >= 28:
            sav_clause = f"While underlying Ashtakavarga strength ({prim_b} SAV Bindus in House {prim_h}, above the 28-bindu threshold) provides a solid floor against permanent loss, active progress"
        else:
            sav_clause = f"With only {prim_b} SAV Bindus in House {prim_h} (below the 28-bindu threshold) indicating limited static buffering and heightened vulnerability, active progress"
        root_cause_diagnosis = (
            f"The chart indicates genuine classical vulnerability in {cfg['title']} due to primary ruler {prim_lord} occupying "
            f"the {lord_h}th Dusthana ({lord_sign}) and key natural significators facing specific afflictions in foundational divisional charts (D9/D30). "
            f"This structural placement creates intermittent delays, friction in execution, and a non-linear development curve. "
            f"{sav_clause} requires navigating this karmic restructuring phase until the supportive cycle activates."
        )
        verdict = (
            f"{root_cause_diagnosis} With targeted planetary remedies, calibrated Ashtakavarga support, "
            f"and supportive planetary transits, the upcoming {breakthrough_period_str} acts as the primary classical catalyst for decisive breakthroughs."
        )
        PLANET_WEEKDAY = {
            "Sun": "Sunday", "Moon": "Monday", "Mars": "Tuesday", "Mercury": "Wednesday",
            "Jupiter": "Thursday", "Venus": "Friday", "Saturn": "Saturday",
            "Rahu": "Saturday", "Ketu": "Tuesday",
        }
        _wd = PLANET_WEEKDAY.get(prim_lord, f"{prim_lord}'s weekday")
        remedies = []
        remedies.append(f"Harmonize Obstructing Planet ({prim_lord}): Offer targeted donations or planetary prayers on {prim_lord}'s day ({_wd}) to neutralize 8th/6th house friction.")
        if cfg["karakas"]:
            top_k = cfg["karakas"][0]
            remedies.append(f"Strengthen Natural Karaka ({top_k}): Chant the {top_k} Gayatri Mantra or perform charitable seva (e.g. green fodder to cows for Mercury, Surya Arghya for Sun, Jal Abhishek for Moon).")
        remedies.append(f"Energize Lagna Lord ({lagna_lord}): Daily spiritual grounding, meditation, and chanting the Lagna lord's root mantra to fortify overall constitutional resilience.")
    else:
        if prim_b >= 28:
            sav_clause2 = f"Backed by {prim_b} SAV Bindus in House {prim_h} (above 28), the chart carries sufficient static promise to overcome immediate friction,"
        else:
            sav_clause2 = f"With only {prim_b} SAV Bindus in House {prim_h} (below the 28-bindu threshold) indicating limited buffering, the chart requires steady remedial support to overcome immediate friction,"
        root_cause_diagnosis = (
            f"The chart shows constructive underlying potential for {cfg['title']} anchored by {prim_lord} in the {lord_h}th house ({lord_dig.replace('_', ' ')}). "
            f"{sav_clause2} "
            f"though current multi-clock alignments demand steady patience during the ongoing operating sub-period."
        )
        verdict = (
            f"{root_cause_diagnosis} The upcoming {breakthrough_period_str} provides the active window for material realization."
        )
        remedies = []
        if cfg["karakas"]:
            top_k = cfg["karakas"][0]
            remedies.append(f"Strengthen Natural Karaka ({top_k}): Chant the {top_k} Gayatri Mantra or perform charitable seva (e.g. green fodder to cows for Mercury, Surya Arghya for Sun, Jal Abhishek for Moon).")
        remedies.append(f"Energize Lagna Lord ({lagna_lord}): Daily spiritual grounding, meditation, and chanting the Lagna lord's root mantra to fortify overall constitutional resilience.")

    specialist_bundle: dict = {}
    try:
        from specialist_readings import build_specialist_readings
        raw_gender = (pc.get("meta") or {}).get("gender", "male")
        gender = "female" if str(raw_gender).lower() in ("1", "female", "f") else "male"
        specialist_bundle = build_specialist_readings(pc, gender=gender)
        lk = specialist_bundle.get("lal_kitab") or {}
        cn = specialist_bundle.get("chandra_naadi") or {}
        if lk.get("status") == "available":
            for finding in (lk.get("findings") or [])[:2]:
                title = str((finding or {}).get("title") or "").strip()
                summary = str((finding or {}).get("summary") or "").strip()
                if title and summary:
                    line = f"Lal Kitab — {title}: {summary}"
                    if line not in remedies:
                        remedies.append(line)
            for prec in (lk.get("precautions") or [])[:1]:
                text = str(prec or "").strip()
                if text:
                    remedies.append(f"Lal Kitab precaution: {text}")
        if cn.get("status") == "available":
            for finding in (cn.get("findings") or [])[:1]:
                title = str((finding or {}).get("title") or "").strip()
                summary = str((finding or {}).get("summary") or "").strip()
                if title and summary:
                    extra = f"Chandra Naadi — {title}: {summary}"
                    if extra not in remedies:
                        remedies.append(extra)
        g0 = audit_gate0_hardware(pc)
        if g0.get("status") not in ("", "HEALTHY_HARDWARE") and g0.get("contingency_rule"):
            verdict = f"{verdict} Chart-judgement note: {g0['contingency_rule']}"
    except Exception as exc:  # noqa: BLE001
        print(f"[confluence_question_engine] specialist lenses skipped: {exc}",
              flush=True)

    return QuestionConfluenceReport(
        question=question,
        domain_key=domain_key,
        domain_title=cfg["title"],
        lagna=lagna_sign,
        lagna_lord=lagna_lord,
        moon_sign=moon_sign,
        moon_nakshatra=f"{moon_nak} (Pada {moon_pada})",
        primary_house=prim_h,
        primary_house_sign=prim_sign,
        primary_house_lord=prim_lord,
        primary_lord_placement=f"House {lord_h} in {lord_sign} ({lord_deg:.2f}°)",
        primary_lord_dignity=lord_dig,
        is_lord_in_dusthana=is_in_dusthana,
        dusthana_finding=dusthana_finding,
        supporting_factors=supp_findings,
        karaka_findings=karaka_findings,
        varga_findings=varga_findings,
        ashtakavarga_finding=ashtakavarga_finding,
        transit_finding=transit_finding,
        triple_dasha_confluence=triple_dasha_confluence,
        current_dasha=current_dasha_str,
        dasha_timeline=timeline_items[:5],
        breakthrough_period=breakthrough_period_str,
        classical_verdict=verdict,
        root_cause_diagnosis=root_cause_diagnosis,
        remedies=remedies,
        specialist_readings=specialist_bundle,
    )


from pydantic import BaseModel, Field


class QuestionConsultationOutput(BaseModel):
    verdict: str = Field(description="Direct astrological verdict answering whether the chart indicates the issue and its nature.")
    planetary_mechanics: str = Field(description="Detailed explanation of the primary house, lord in 8th/Dusthana, natural karakas, and D9/D30 divisional confirmations.")
    timeline_and_milestones: str = Field(description="Clear breakdown of the past origin, current active phase, and the exact upcoming breakthrough window.")
    remedial_actions: str = Field(description="Step-by-step practical and spiritual remedies for immediate and long-term relief.")


def _format_specialist_evidence(specialist_readings: Optional[dict]) -> str:
    """Compact Chandra Naadi / Lal Kitab / nodes evidence for the consultation prompt."""
    if not isinstance(specialist_readings, dict) or not specialist_readings:
        return ""
    lines: list[str] = []
    labels = {
        "chandra_naadi": "Chandra Naadi (mind, obstacles, timing pressure)",
        "lal_kitab": "Lal Kitab (upayas & precautions)",
        "rahu_ketu": "Rahu–Ketu nodal reading",
        "transit_matrix": "Live transit matrix",
    }
    for key, label in labels.items():
        block = specialist_readings.get(key)
        if not isinstance(block, dict) or block.get("status") != "available":
            continue
        findings = block.get("findings") or []
        if not findings:
            continue
        lines.append(f"12+. {label}:")
        for finding in findings[:4]:
            if not isinstance(finding, dict):
                continue
            title = str(finding.get("title") or "").strip()
            summary = str(finding.get("summary") or "").strip()
            if title and summary:
                lines.append(f"   • {title}: {summary}")
        for prec in (block.get("precautions") or [])[:2]:
            text = str(prec or "").strip()
            if text:
                lines.append(f"   • Precaution: {text}")
    return ("\n" + "\n".join(lines)) if lines else ""


def synthesize_with_qwen(
    confluence: QuestionConfluenceReport,
    lang: str = "en",
    specialist_readings: Optional[dict] = None,
) -> str:
    """Prompts Qwen LLM using the structured confluence payload to produce an authoritative consultation response."""
    if not _llm_allowed():
        return _deterministic_consultation(confluence, lang=lang)
    try:
        from core.llm_client import _get_client, complete_model
        from core.config import S
        
        lang_code = str(lang or "").lower()
        is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
        is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")
        if is_hinglish:
            system_prompt = (
                "You are a master Vedic Astrologer (Jyotish Acharya) providing an authoritative, compassionate, "
                "and deeply insightful consultation reading for the reader's question. "
                "Write the entire consultation response in conversational Hindi using the English/Latin alphabet (Hinglish / Roman Hindi). "
                "DO NOT use Devanagari script. Use clear, fluent Roman Hindi words (e.g. 'Aapki kundli ke anusar...', 'Breakthrough period...', 'Grahon ki sthiti...'). "
                "You have been provided with rigorous, verified classical confluence facts (Houses, Lords, Dignities, "
                "Natural Karakas, Divisional Charts D9/D30, Sarvashtakavarga SAV Bindu strength, Live Planetary Transits Gochar, "
                "Triple Dashas Vimshottari + Jaimini Chara + Yogini, and Vedic Upaya). "
                "Speak directly to the reader as 'Aap'. Never write 'the native', 'the seeker', 'the querent', or 'the client'. "
                "A Sanskrit or technical term is allowed only with a plain-word gloss in the same sentence.\n\n"
                "SPECIAL JUDGMENT RULES:\n"
                "1. AMBIGUOUS / BROAD QUESTIONS: If the question is broad, general, or ambiguous (e.g. 'what is in store for my future?', 'kaisa rahega aane wala samay?'), "
                "synthesize the Lagna, running Dasha chronology, SAV strength, and transit Gochar to deliver a comprehensive, deeply insightful reading on their overall life trajectory, key focus areas, and timing windows.\n"
                "2. OUT-OF-DOMAIN QUESTIONS: If the question is entirely outside the scope of human life and Vedic astrology (e.g. coding, technical trivia, recipes, hardware repair), "
                "politely and respectfully explain that astrology guides life dimensions (career, health, relationships, finances, family, spiritual remedies) and invite them to ask about their personal life path or chart guidance."
            )
            instructions_text = """INSTRUCTIONS:
Write a comprehensive, professional Vedic consultation response in natural conversational Hindi using English letters (Hinglish / Roman Hindi) containing:
1. DIRECT ASTROLOGICAL VERDICT: Direct, honest answer in Roman Hindi addressing whether the chart indicates the issue and its nature. (If out-of-domain, explain politely).
2. CORE PLANETARY MECHANICS: Detailed explanation in Roman Hindi of the primary house, lord placement, natural karakas, Ashtakavarga SAV support, and D9/D30 confirmations in clear, natural language.
3. TIMELINE & KEY MILESTONE: Clear breakdown in Roman Hindi of the past origin, current active phase, and exact upcoming breakthrough window (citing dasha + transit dates).
4. ACTIONABLE REMEDIAL GUIDANCE: Step-by-step practical and Vedic remedies (mantras, daan, puja) in Roman Hindi for immediate and long-term relief.

FEW-SHOT HINGLISH EXAMPLES:
- Verdict: "Aapke question ke mutabiq, kundli yeh darshati hai ki current phase thoda testing zaroor hai, lekin upcoming transit se conditions mein decisive improvement aayega."
- Mechanics: "Aapka Janma Lagna aur primary house lord achhi sthiti mein hain, jisse long-term results favorable rahenge."
- Timing: "Sabse important milestone aur breakthrough window October 2026 se shuru ho raha hai."
- Remedy: "Surya Dev ko regular jal arpit karein aur Gayatri Mantra ka daily 108 baar jaap karein."
"""
        elif is_tenglish:
            system_prompt = (
                "You are a master Vedic Astrologer (Jyotish Acharya) providing an authoritative, compassionate, "
                "and deeply insightful consultation reading for the reader's question. "
                "Write the entire consultation response in conversational Telugu using the English/Latin alphabet (Tenglish / Roman Telugu). "
                "DO NOT use Telugu script characters. Use clear, fluent Roman Telugu words (e.g. 'Mee kundali prakaram...', 'Breakthrough period...', 'Grahala sthiti...'). "
                "You have been provided with rigorous, verified classical confluence facts (Houses, Lords, Dignities, "
                "Natural Karakas, Divisional Charts D9/D30, Sarvashtakavarga SAV Bindu strength, Live Planetary Transits Gochar, "
                "Triple Dashas Vimshottari + Jaimini Chara + Yogini, and Vedic Upaya). "
                "Speak directly to the reader as 'Meeru' / 'Mee'. Never write 'the native', 'the seeker', 'the querent', or 'the client'. "
                "A Sanskrit or technical term is allowed only with a plain-word gloss in the same sentence.\n\n"
                "SPECIAL JUDGMENT RULES:\n"
                "1. AMBIGUOUS / BROAD QUESTIONS: If the question is broad, general, or ambiguous (e.g. 'what is in store for my future?', 'bhavishyath ela untundi?'), "
                "synthesize the Lagna, running Dasha chronology, SAV strength, and transit Gochar to deliver a comprehensive, deeply insightful reading on their overall life trajectory, key focus areas, and timing windows.\n"
                "2. OUT-OF-DOMAIN QUESTIONS: If the question is entirely outside the scope of human life and Vedic astrology (e.g. coding, technical trivia, recipes, hardware repair), "
                "politely and respectfully explain that astrology guides life dimensions (career, health, relationships, finances, family, spiritual remedies) and invite them to ask about their personal life path or chart guidance."
            )
            instructions_text = """INSTRUCTIONS:
Write a comprehensive, professional Vedic consultation response in natural conversational Telugu using English letters (Tenglish / Roman Telugu) containing:
1. DIRECT ASTROLOGICAL VERDICT: Direct, honest answer in Roman Telugu addressing whether the chart indicates the issue and its nature. (If out-of-domain, explain politely).
2. CORE PLANETARY MECHANICS: Detailed explanation in Roman Telugu of the primary house, lord placement, natural karakas, Ashtakavarga SAV support, and D9/D30 confirmations in clear, natural language.
3. TIMELINE & KEY MILESTONE: Clear breakdown in Roman Telugu of the past origin, current active phase, and exact upcoming breakthrough window (citing dasha + transit dates).
4. ACTIONABLE REMEDIAL GUIDANCE: Step-by-step practical and Vedic remedies (mantras, daan, puja) in Roman Telugu for immediate and long-term relief.

FEW-SHOT TENGLISH EXAMPLES:
- Verdict: "Mee prashnaku kundali samadhanam: prasthutha samayam konchem testing ga unna, aane dasha mariyu gocharam tho sthiti decisive ga improve avuthundi."
- Mechanics: "Mee Janma Lagnam mariyu primary house lord manchi sthiti lo unnaru, anduvalla long-term lo manchi results vasthayi."
- Timing: "Mukhya milestone mariyu breakthrough window October 2026 nundi start avuthundi."
- Remedy: "Surya Bhagavanudiki daily arghyam samarpinchi, Gayatri Mantra ni roju 108 sarlu japinchandi."
"""
        else:
            system_prompt = (
                "You are a master Vedic Astrologer (Jyotish Acharya) providing an authoritative, compassionate, "
                "and deeply insightful consultation reading for the reader's question. "
                "You have been provided with rigorous, verified classical confluence facts (Houses, Lords, Dignities, "
                "Natural Karakas, Divisional Charts D9/D30, Sarvashtakavarga SAV Bindu strength, Live Planetary Transits Gochar, "
                "Triple Dashas Vimshottari + Jaimini Chara + Yogini, and Vedic Upaya). "
                "Write a beautifully articulated, structured consultation response in clear, fluent English that directly answers the question, "
                "explains the exact astrological mechanics clearly, provides the precise timing milestone, and details actionable remedies. "
                "DO NOT use raw JSON keys or robotic phrasing. Speak directly as 'you' / 'your'. Never write 'the native', "
                "'the seeker', 'the querent', 'the client', or 'this chart indicates'. A Sanskrit or technical term is "
                "allowed only with a plain-English gloss in the same sentence.\n\n"
                "SPECIAL JUDGMENT RULES:\n"
                "1. AMBIGUOUS / BROAD QUESTIONS: If the question is broad, general, or ambiguous (e.g. 'what does my future hold?', 'how will things be?'), "
                "synthesize the Lagna, running Dasha chronology, SAV strength, and transit Gochar to deliver a comprehensive, deeply insightful reading on their overall life trajectory, key focus areas, and timing windows.\n"
                "2. OUT-OF-DOMAIN QUESTIONS: If the question is entirely outside the scope of human life and Vedic astrology (e.g. coding, technical trivia, recipes, hardware repair), "
                "politely and respectfully explain that astrology guides life dimensions (career, health, relationships, finances, family, spiritual remedies) and invite them to ask about their personal life path or chart guidance."
            )
            instructions_text = """INSTRUCTIONS:
Write a comprehensive, professional Vedic consultation response containing:
1. DIRECT ASTROLOGICAL VERDICT: Direct, honest answer addressing whether the chart indicates the issue and its nature. (If out-of-domain, explain politely).
2. CORE PLANETARY MECHANICS: Detailed explanation of the primary house, lord in 8th/Dusthana, natural karakas, Ashtakavarga SAV support, and D9/D30 divisional confirmations in natural, user-understandable language.
3. TIMELINE & KEY MILESTONE: Clear breakdown of the past origin, current active phase, and the exact upcoming breakthrough window (citing dasha + transit confluence) where conditions decisively improve.
4. ACTIONABLE REMEDIAL GUIDANCE: Step-by-step practical and spiritual remedies for immediate and long-term relief.
"""

        user_content = f"""
CLIENT QUESTION: "{confluence.question}"
DOMAIN: {confluence.domain_title}

VERIFIED ASTROLOGICAL CONFLUENCE FACTS:
1. Constitutional Core: Janma Lagna is {confluence.lagna} (ruled by {confluence.lagna_lord}); Moon in {confluence.moon_sign} under {confluence.moon_nakshatra}.
2. Primary House & Lord: House {confluence.primary_house} ({confluence.primary_house_sign}) is governed by {confluence.primary_house_lord}, placed in {confluence.primary_lord_placement} with {confluence.primary_lord_dignity} dignity.
3. Dusthana / Affliction Finding: {confluence.dusthana_finding}
4. Supporting Houses & Lords:
{chr(10).join('   • ' + f for f in confluence.supporting_factors)}
5. Natural Karakas (Significators):
{chr(10).join('   • ' + f for f in confluence.karaka_findings)}
6. Divisional Cross-Checks (Vargas D9 / D30 / Specialized):
{chr(10).join('   • ' + f for f in confluence.varga_findings)}
7. Sarvāṣṭakavarga (SAV) Bindu Strength:
   • {confluence.ashtakavarga_finding}
8. Live Planetary Transits (Gochar):
   • {confluence.transit_finding}
9. Triple-Dasha Alignment (Vimshottari + Jaimini Chara + Yogini):
   • {confluence.triple_dasha_confluence}
10. Active Dasha Timeline & Milestones:
   • Current Period: {confluence.current_dasha}
   • Key Milestone / Breakthrough Period: {confluence.breakthrough_period}
   • Chronology:
{chr(10).join('     - ' + t for t in confluence.dasha_timeline)}
11. Targeted Vedic Remedies (Upaya):
{chr(10).join('   • ' + r for r in confluence.remedies)}
{_format_specialist_evidence(specialist_readings)}

{instructions_text}
"""

        from dataclasses import asdict

        from openai import OpenAI
        from core.config import S
        from llm.grounding import enforce_grounding, extract_ledger
        from llm.validate import enforce_user_voice
        base_url = getattr(S, "llm_base_url", "http://host.docker.internal:8000/v1") or "http://host.docker.internal:8000/v1"
        api_key = getattr(S, "llm_api_key", "dummy") or "dummy"
        model = getattr(S, "llm_model", "Qwen/Qwen2.5-7B-Instruct-AWQ") or "Qwen/Qwen2.5-7B-Instruct-AWQ"

        spec = specialist_readings or confluence.specialist_readings or {}
        conf_data = asdict(confluence)
        conf_data.pop("llm_synthesis", None)
        conf_data.pop("specialist_readings", None)
        ledger = extract_ledger({
            "life_area_confluence": conf_data,
            "mind_and_transits": spec.get("chandra_naadi") or {},
            "lal_kitab": spec.get("lal_kitab") or {},
        })

        client = OpenAI(base_url=base_url.rstrip("/"), api_key=api_key, timeout=90.0)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        raw = ""
        for attempt in range(2):
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.25,
                max_tokens=1500,
            )
            raw = (resp.choices[0].message.content or "").strip()
            if not raw:
                break
            problems = enforce_user_voice(raw)
            problems.extend(enforce_grounding(raw, ledger, confluence.question))
            if not problems:
                return raw
            if attempt >= 1:
                print(f"[confluence_question_engine] voice still off after repair: {problems}",
                      flush=True)
                break
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": (
                "Rewrite that consultation. Problems: " + "; ".join(problems) + ". "
                "Speak to the reader as 'you' (or Aap / Meeru). Use only the "
                "verified facts already given. Do not move a planet to another "
                "house or sign, and do not invent a date or gemstone."
            )})
        if raw and not enforce_user_voice(raw) and not enforce_grounding(
                raw, ledger, confluence.question):
            return raw
    except Exception as exc:
        print(f"[confluence_question_engine] Qwen call failed: {exc}", flush=True)

    return _deterministic_consultation(confluence, lang=lang)


def _llm_allowed(kind: str = "user_question") -> bool:
    """Whether this answer may call the model at all.

    The calls in this module build their own client rather than going through
    ``core.llm_client``, so they never inherited that module's check on
    ``llm_enabled``. Without this gate, switching the LLM off left the question
    answer still calling out — and a dead endpoint cost every reader the full
    request timeout before the deterministic prose appeared.
    """
    try:
        from core.config import S
        return bool(S.llm_tab_enabled(kind))
    except Exception:  # noqa: BLE001
        return False


def _deterministic_consultation(confluence: QuestionConfluenceReport, lang: str = "en") -> str:
    """The same consultation written from the facts, with no model involved."""
    lang_code = str(lang or "").lower()
    is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")
    dom_title = (
        DOMAIN_TITLES_HI.get(confluence.domain_key, confluence.domain_title)
        if is_hinglish
        else (DOMAIN_TITLES_TE.get(confluence.domain_key, confluence.domain_title) if is_tenglish else confluence.domain_title)
    )
    
    if confluence.domain_key == "out_of_domain":
        if is_hinglish:
            return (
                f"### Jyotishiya Vishay Margdarshan: {dom_title}\n\n"
                f"**Prashna:** *{confluence.question}*\n\n"
                f"#### 1. Mukhya Sandesh (Scope of Astrology)\n"
                f"Aapka yeh prashna Vedic Jyotish aur Janma Kundli ke daayre (houses, grah, dasha, life events) se alag ek general ya technical vishay par hai. "
                f"Jyotish parampara aapke jeevan ke mukhya kshetron — jaise career, swasthya, vivah, dhan, santan, yaatra, aur grah upayon par sateek margdarshan pradan karti hai.\n\n"
                f"#### 2. Kundli Ka Mool Swaroop\n"
                f"• **Janma Lagna:** {confluence.lagna} (Lagna Swami: {confluence.lagna_lord})\n"
                f"• **Chalu Dasha:** {confluence.current_dasha}\n"
                f"• **Gochar Sthiti:** {confluence.transit_finding}\n\n"
                f"#### 3. Agla Kadam Aur Salah\n"
                f"• Is specific non-astrological inquiry ke liye relevant domain resources ka upyog karein.\n"
                f"• Yadi aapke jeevan ke kisi pehlu, aane wale samay, dasha fal, career, ya grah shanti ke baare mein koi prashna ho, toh kripya bejhijhak poochhein."
            )
        if is_tenglish:
            return (
                f"### Jyotishya Vishaya Margadarshanam: {dom_title}\n\n"
                f"**Prashna:** *{confluence.question}*\n\n"
                f"#### 1. Mukhya Sandesham (Scope of Astrology)\n"
                f"Mee ee prashna Vedic Jyotishyam mariyu Janma Kundali paridhi (bhavalu, grahalu, dasha, jeevitha ghatanalu) ki bayata unna oka general leda technical vishayam meeda undi. "
                f"Jyotishya sampradayam mee jeevitham loni mukhya rangalu — career, aarogyam, vivaham, dhanam, pillalu, prayanam, mariyu graha shanti upayamula meeda spashtamaina margadarshanam isthundi.\n\n"
                f"#### 2. Kundali Moola Swaroopam\n"
                f"• **Janma Lagnam:** {confluence.lagna} (Lagnaadhipathi: {confluence.lagna_lord})\n"
                f"• **Chalu Dasha:** {confluence.current_dasha}\n"
                f"• **Gocharam Sthiti:** {confluence.transit_finding}\n\n"
                f"#### 3. Thadupari Adugu Mariyu Salaha\n"
                f"• Ee specific non-astrological topic kosam sambandhitha domain resources chudandi.\n"
                f"• Mee jeevitha gamanamu, aane samayam, dasha phalam, career, leda graha shanti gurinchi edaina prashna unte, dayachesi adagandi."
            )
        return (
            f"### Astrological Scope Notice: {dom_title}\n\n"
            f"**Question:** *{confluence.question}*\n\n"
            f"#### 1. Scope of Inquiry\n"
            f"Your question pertains to a topic outside the classical domain of Vedic astrology and natal chart analysis. "
            f"Vedic Jyotish specializes in human life dimensions — including career, vitality, marriage, finances, family lineage, and planetary periods (dashas).\n\n"
            f"#### 2. Natal Chart Foundation\n"
            f"• **Janma Lagna:** {confluence.lagna} (Ascendant Lord: {confluence.lagna_lord})\n"
            f"• **Operating Dasha:** {confluence.current_dasha}\n"
            f"• **Transit Context:** {confluence.transit_finding}\n\n"
            f"#### 3. Recommended Next Step\n"
            f"• For non-astrological technical or factual matters, please refer to specialized domains.\n"
            f"• Feel free to ask any question regarding your personal life journey, career trajectory, relationships, health, or spiritual remedies."
        )

    if confluence.domain_key == "general_destiny":
        if is_hinglish:
            return (
                f"### Sampurna Kundli Vishleshan: {dom_title}\n\n"
                f"**Prashna:** *{confluence.question}*\n\n"
                f"#### 1. Mukhya Faisla Aur Disha (Overall Life Trajectory Verdict)\n"
                f"{confluence.classical_verdict}\n\n"
                f"#### 2. Kundli Ka Mool Aadhar Aur Grah Bal\n"
                f"• **Lagna Aur Lagnesh:** {confluence.lagna} Lagna jiske swami {confluence.lagna_lord} {confluence.primary_lord_placement} mein sthit hain.\n"
                f"• **Ashtakavarga (SAV) Bal:** {confluence.ashtakavarga_finding}\n"
                f"• **Gochar Grah Sthiti:** {confluence.transit_finding}\n"
                f"• **D9 Varga Pushti:** " + "; ".join(confluence.varga_findings[:2]) + "\n\n"
                f"#### 3. Chalu Dasha Timeline Aur Aane Wala Shubh Samay\n"
                f"• **Active Triple Dasha:** {confluence.triple_dasha_confluence}\n"
                f"• **Current Operating Period:** {confluence.current_dasha}\n"
                f"• **Mukhya Breakthrough Window:** **{confluence.breakthrough_period}**\n\n"
                f"#### 4. Dainik Margdarshan Aur Upaya\n"
                + "\n".join(f"• {r}" for r in confluence.remedies)
            )
        if is_tenglish:
            return (
                f"### Sampoorna Kundali Vishleshana: {dom_title}\n\n"
                f"**Prashna:** *{confluence.question}*\n\n"
                f"#### 1. Mukhya Theerpu Mariyu Disha (Overall Life Trajectory Verdict)\n"
                f"{confluence.classical_verdict}\n\n"
                f"#### 2. Kundali Moola Aadharam Mariyu Graha Balam\n"
                f"• **Lagnam Mariyu Lagnaadhipathi:** {confluence.lagna} Lagnam, adhipathi {confluence.lagna_lord} {confluence.primary_lord_placement} lo unnaru.\n"
                f"• **Ashtakavarga (SAV) Balam:** {confluence.ashtakavarga_finding}\n"
                f"• **Gocharam Graha Sthiti:** {confluence.transit_finding}\n"
                f"• **D9 Varga Balam:** " + "; ".join(confluence.varga_findings[:2]) + "\n\n"
                f"#### 3. Chalu Dasha Timeline Mariyu Breakthrough Samayam\n"
                f"• **Active Triple Dasha:** {confluence.triple_dasha_confluence}\n"
                f"• **Current Operating Period:** {confluence.current_dasha}\n"
                f"• **Mukhya Breakthrough Window:** **{confluence.breakthrough_period}**\n\n"
                f"#### 4. Actionable Margadarshanam Mariyu Upayamulu\n"
                + "\n".join(f"• {r}" for r in confluence.remedies)
            )
        return (
            f"### Comprehensive Natal Chart Reading: {dom_title}\n\n"
            f"**Question:** *{confluence.question}*\n\n"
            f"#### 1. Overall Life Trajectory Verdict\n{confluence.classical_verdict}\n\n"
            f"#### 2. Natal Chart Baseline & Planetary Balance\n"
            f"• **Ascendant & Core Vitality:** {confluence.lagna} Lagna governed by {confluence.lagna_lord} seated in {confluence.primary_lord_placement}.\n"
            f"• **Ashtakavarga (SAV) Strength:** {confluence.ashtakavarga_finding}\n"
            f"• **Live Planetary Transits (Gochar):** {confluence.transit_finding}\n"
            f"• **Divisional Cross-Check:** " + "; ".join(confluence.varga_findings[:2]) + "\n\n"
            f"#### 3. Operating Dasha Timeline & Major Milestones\n"
            f"• **Active Triple Dasha:** {confluence.triple_dasha_confluence}\n"
            f"• **Current Operating Period:** {confluence.current_dasha}\n"
            f"• **Key Breakthrough Window:** **{confluence.breakthrough_period}**\n\n"
            f"#### 4. Actionable Guidance & Remedial Upaya\n"
            + "\n".join(f"• {r}" for r in confluence.remedies)
        )

    if confluence.domain_key == "gemstones_remedies":
        if is_hinglish:
            return (
                f"### Jyotishiya Ratna Salah Aur Upaya: {dom_title}\n\n"
                f"**Prashna:** *{confluence.question}*\n\n"
                f"#### 1. Mukhya Ratna Faisla (Gemstone Recommendation Verdict)\n"
                f"{confluence.classical_verdict}\n\n"
                f"#### 2. Kundli Ka Aadhar Aur Grah Sthiti\n"
                f"• **Lagna Aur Lagnesh:** {confluence.lagna} Lagna jiske swami {confluence.lagna_lord} hain ({confluence.primary_lord_placement}). Yeh aapka mukhya Life Stone nirdharit karta hai.\n"
                f"• **Trikona Grah Bal:** 1st, 5th, aur 9th bhav ke swami functional benefics hain, jinki urja ratna dharan se badhai ja sakti hai.\n"
                f"• **Grah Gochar (Transits):** {confluence.transit_finding}\n"
                f"• **Ashtakavarga SAV Bal:** {confluence.ashtakavarga_finding}\n\n"
                f"#### 3. Chalu Dasha Aur Timing Alignment\n"
                f"• **Active Dasha:** {confluence.current_dasha} ({confluence.triple_dasha_confluence})\n"
                f"• **Prabhavi Daur:** {confluence.breakthrough_period}\n\n"
                f"#### 4. Shubh Ratna, Niyam Aur Savdhani (Actionable Gemstone Protocol)\n"
                + "\n".join(f"• {r}" for r in confluence.remedies)
            )
        if is_tenglish:
            return (
                f"### Jyotishya Rathna Salaha Mariyu Upayamulu: {dom_title}\n\n"
                f"**Prashna:** *{confluence.question}*\n\n"
                f"#### 1. Mukhya Rathna Theerpu (Gemstone Recommendation Verdict)\n"
                f"{confluence.classical_verdict}\n\n"
                f"#### 2. Kundali Aadharam Mariyu Graha Sthiti\n"
                f"• **Lagnam Mariyu Lagnaadhipathi:** {confluence.lagna} Lagnam, adhipathi {confluence.lagna_lord} ({confluence.primary_lord_placement}). Idi mee mukhya Life Gemstone nirdharisthundi.\n"
                f"• **Trikona Graha Balam:** 1, 5, mariyu 9th bhavaadhipathulu functional benefics, veeti shaktini rathnam dharana chesi penchavachu.\n"
                f"• **Graha Gocharam (Transits):** {confluence.transit_finding}\n"
                f"• **Ashtakavarga SAV Balam:** {confluence.ashtakavarga_finding}\n\n"
                f"#### 3. Chalu Dasha Mariyu Timing Alignment\n"
                f"• **Active Dasha:** {confluence.current_dasha} ({confluence.triple_dasha_confluence})\n"
                f"• **Prabhavavanthamaina Samayam:** {confluence.breakthrough_period}\n\n"
                f"#### 4. Anukoolamaina Rathnamulu, Niyamalu (Actionable Gemstone Protocol)\n"
                + "\n".join(f"• {r}" for r in confluence.remedies)
            )
        return (
            f"### Astrological Gemstone Consultation: {dom_title}\n\n"
            f"**Question:** *{confluence.question}*\n\n"
            f"#### 1. Classical Gemstone Verdict\n{confluence.classical_verdict}\n\n"
            f"#### 2. Planetary Foundations & Trikona House Lords\n"
            f"• **Ascendant & Life Ruler:** {confluence.lagna} Lagna governed by {confluence.lagna_lord} seated in {confluence.primary_lord_placement}. This establishes your core Life Gemstone.\n"
            f"• **Benefic Trikona Alignment:** Houses 1, 5, and 9 provide auspicious gemstone resonance; Dusthana (6/8/12) lords are strictly barred from gemstone wear.\n"
            f"• **Ashtakavarga (SAV) Strength:** {confluence.ashtakavarga_finding}\n"
            f"• **Live Gochar (Transits):** {confluence.transit_finding}\n\n"
            f"#### 3. Operating Dasha & Timing Context\n"
            f"• **Active Triple Dasha:** {confluence.triple_dasha_confluence}\n"
            f"• **Current Period:** {confluence.current_dasha}\n\n"
            f"#### 4. Recommended Gemstones & Wearing Protocols\n"
            + "\n".join(f"• {r}" for r in confluence.remedies)
        )

    if is_hinglish:
        return (
            f"### Jyotishiya Salah: {dom_title}\n\n"
            f"**Prashna:** *{confluence.question}*\n\n"
            f"#### 1. Mukhya Jyotishiya Vishleshan\n"
            f"Aapki kundli ke anusar, {dom_title} ke mukhya swami {confluence.primary_house_lord} {confluence.primary_lord_placement} mein sthit hain. "
            f"Yeh sthiti shuruat mein thoda vilamb ya badhao ka sanket deti hai, lekin sahi samay aane aur shubh grah gochar ke sath sthiti mein decisive sudhar aayega.\n\n"
            f"#### 2. Grah Sthiti Aur Jyotishiya Praman\n"
            f"• **Mukhya Bhav:** {confluence.primary_house}th House ({confluence.primary_house_sign}) jiske swami {confluence.primary_house_lord} hain, jo {confluence.primary_lord_placement} mein sthit hain.\n"
            f"• **Ashtakavarga Bal:** {confluence.ashtakavarga_finding}\n"
            f"• **Grah Gochar (Transits):** {confluence.transit_finding}\n"
            f"• **Karak Grah:**\n" + "\n".join(f"  - {f}" for f in confluence.karaka_findings) + "\n\n"
            f"#### 3. D9 Aur D30 Varga Pushti\n" + "\n".join(f"• {f}" for f in confluence.varga_findings) + "\n\n"
            f"#### 4. Dasha Timeline Aur Mukhya Breakthrough Window\n"
            f"• **Chalu Dasha Alignment:** {confluence.triple_dasha_confluence}\n"
            f"• **Current Period:** {confluence.current_dasha}\n"
            f"• **Mukhya Breakthrough Samay:** **{confluence.breakthrough_period}**\n\n"
            f"#### 5. Vedic Upay Aur Margdarshan\n" + "\n".join(f"• {r}" for r in confluence.remedies)
        )
    if is_tenglish:
        return (
            f"### Jyotishya Salaha: {dom_title}\n\n"
            f"**Prashna:** *{confluence.question}*\n\n"
            f"#### 1. Mukhya Jyotishya Vishleshana\n"
            f"Mee kundali prakaram, {dom_title} mukhya adhipathi {confluence.primary_house_lord} {confluence.primary_lord_placement} lo unnaru. "
            f"Ee sthiti modatlo konchem aalasyam chupinchina, anukoolamaina dasha mariyu shubha graha gocharam valla sthiti decisive ga improve avuthundi.\n\n"
            f"#### 2. Graha Sthiti Mariyu Jyotishya Aadharalu\n"
            f"• **Mukhya Bhavam:** {confluence.primary_house}th House ({confluence.primary_house_sign}), adhipathi {confluence.primary_house_lord}, sthiti: {confluence.primary_lord_placement}.\n"
            f"• **Ashtakavarga Balam:** {confluence.ashtakavarga_finding}\n"
            f"• **Graha Gocharam (Transits):** {confluence.transit_finding}\n"
            f"• **Karaka Grahalu:**\n" + "\n".join(f"  - {f}" for f in confluence.karaka_findings) + "\n\n"
            f"#### 3. D9 Mariyu D30 Varga Balam\n" + "\n".join(f"• {f}" for f in confluence.varga_findings) + "\n\n"
            f"#### 4. Dasha Timeline Mariyu Mukhya Breakthrough Window\n"
            f"• **Chalu Dasha Alignment:** {confluence.triple_dasha_confluence}\n"
            f"• **Current Period:** {confluence.current_dasha}\n"
            f"• **Mukhya Breakthrough Samayam:** **{confluence.breakthrough_period}**\n\n"
            f"#### 5. Vedic Upayamulu Mariyu Margadarshanam\n" + "\n".join(f"• {r}" for r in confluence.remedies)
        )
    return (
        f"### Astrological Consultation: {dom_title}\n\n"
        f"**Question:** *{confluence.question}*\n\n"
        f"#### 1. Classical Astrological Verdict\n{confluence.classical_verdict}\n\n"
        f"#### 2. Planetary Mechanics & Supporting Indicators\n"
        f"• **Primary Governing House:** House {confluence.primary_house} ({confluence.primary_house_sign}) governed by {confluence.primary_house_lord} seated in {confluence.primary_lord_placement}.\n"
        f"• **Dusthana Analysis:** {confluence.dusthana_finding}\n"
        f"• **Ashtakavarga (SAV) Strength:** {confluence.ashtakavarga_finding}\n"
        f"• **Live Gochar (Transits):** {confluence.transit_finding}\n"
        f"• **Natural Significators:**\n" + "\n".join(f"  - {f}" for f in confluence.karaka_findings) + "\n\n"
        f"#### 3. Divisional Chart Confirmations (D9 & D30)\n" + "\n".join(f"• {f}" for f in confluence.varga_findings) + "\n\n"
        f"#### 4. Dasha Timeline & Major Breakthrough Window\n"
        f"• **Triple-Dasha Alignment:** {confluence.triple_dasha_confluence}\n"
        f"• **Current Period:** {confluence.current_dasha}\n"
        f"• **Key Breakthrough Catalyst:** **{confluence.breakthrough_period}**\n\n"
        f"#### 5. Actionable Vedic Remedial Upaya\n" + "\n".join(f"• {r}" for r in confluence.remedies)
    )


def _format_consultation_markdown(md_text: str) -> str:
    """Converts structured markdown consultation prose into clean, elegant HTML."""
    import html
    lines = md_text.strip().split("\n")
    html_lines = []
    in_list = False

    for line in lines:
        l = line.strip()
        if not l:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue

        # Convert bold markers **text**
        l_html = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", html.escape(l))
        # Convert italic markers *text*
        l_html = re.sub(r"\*(.*?)\*", r"<i>\1</i>", l_html)

        if l.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            txt = l[4:].strip()
            html_lines.append(f'<h3 style="font-family:Georgia,serif;font-size:1.15rem;color:#1f2430;margin:16px 0 8px;font-weight:600;">{html.escape(txt)}</h3>')
        elif l.startswith("#### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            txt = l[5:].strip()
            html_lines.append(f'<h4 style="font-family:Georgia,serif;font-size:1.02rem;color:#7a4b18;margin:14px 0 6px;font-weight:700;letter-spacing:0.02em;">{html.escape(txt)}</h4>')
        elif l.startswith("• ") or l.startswith("- ") or l.startswith("* "):
            if not in_list:
                html_lines.append('<ul style="margin:6px 0 10px 18px;padding:0;font-size:0.9rem;line-height:1.55;color:#2c3140;">')
                in_list = True
            content = l_html[2:].strip()
            html_lines.append(f'<li style="margin-bottom:6px;">{content}</li>')
        elif re.match(r"^\d+\.\s+", l):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f'<p style="margin:6px 0 10px;font-size:0.91rem;line-height:1.6;color:#2c3140;">{l_html}</p>')
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f'<p style="margin:6px 0 10px;font-size:0.91rem;line-height:1.6;color:#2c3140;">{l_html}</p>')

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def _specialist_lenses_html(bundle: dict, *, lang: str, clean) -> str:
    """Paid confluence strip: Chandra Naadi + Lal Kitab findings."""
    if not isinstance(bundle, dict):
        return ""
    is_hinglish = lang in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang in ("te_en", "tenglish", "te", "telugu")
    labels = {
        "chandra_naadi": (
            "Chandra Naadi (mann aur rukawat)" if is_hinglish
            else "Chandra Naadi (manasu mariyu avarodhalu)" if is_tenglish
            else "Chandra Naadi (mind and obstacles)"
        ),
        "lal_kitab": "Lal Kitab",
    }
    blocks = []
    for key, title in labels.items():
        findings = ((bundle.get(key) or {}).get("findings") or [])[:3]
        items = []
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            ft = str(finding.get("title") or "").strip()
            fs = str(finding.get("summary") or "").strip()
            if ft and fs:
                items.append(f"<li style='margin-bottom:6px;'><b>{clean(ft)}</b> — {clean(fs)}</li>")
        if items:
            blocks.append(
                f"<div style='margin-bottom:10px;'><b>{title}</b>"
                f"<ul style='margin:6px 0 0;padding-left:18px;'>{''.join(items)}</ul></div>"
            )
    if not blocks:
        return ""
    hdr = (
        "Chandra Naadi Aur Lal Kitab" if is_hinglish
        else "Chandra Naadi Mariyu Lal Kitab" if is_tenglish
        else "Chandra Naadi & Lal Kitab on this problem"
    )
    return (
        f'<article class="card" style="background:#fff;border:1px solid #e8e4dc;'
        f'border-left:4px solid #5c4a7a;border-radius:12px;padding:16px 18px;margin:14px 0;">'
        f'<div style="font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;'
        f'font-weight:800;color:#4a3d63;margin-bottom:8px;">{hdr}</div>'
        f'{"".join(blocks)}</article>'
    )


def render_confluence_card_html(confluence: QuestionConfluenceReport, *, paid: bool = True, qwen_text: str = "", lang: str = "en") -> str:
    """Renders the comprehensive Vedic Astrological Consultation document in clean HTML."""
    import html

    lang_code = str(lang or "").lower()
    is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")
    dom_title = (
        DOMAIN_TITLES_HI.get(confluence.domain_key, confluence.domain_title)
        if is_hinglish
        else (DOMAIN_TITLES_TE.get(confluence.domain_key, confluence.domain_title) if is_tenglish else confluence.domain_title)
    )

    pill_color = "#8a6a1f" if not confluence.is_lord_in_dusthana else "#a3341f"
    if is_hinglish:
        pill_label = "Anukool Sanket" if not confluence.is_lord_in_dusthana else "Upay Aur Savdhani Aavashyak"
    elif is_tenglish:
        pill_label = "Anukoola Sanketham" if not confluence.is_lord_in_dusthana else "Upayam Mariyu Jagrattha Avasaram"
    else:
        pill_label = "Constructive Promise" if not confluence.is_lord_in_dusthana else "Requires Remedial Care"

    def _clean_html_item(text: str) -> str:
        if not text:
            return ""
        if "<b" in text or "<i" in text or "<span" in text:
            return text
        escaped = html.escape(text)
        return re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", escaped)

    karakas_html = "".join(f"<li style='margin-bottom:6px;'>{_clean_html_item(k)}</li>" for k in confluence.karaka_findings)
    vargas_html = "".join(f"<li style='margin-bottom:6px;'>{_clean_html_item(v)}</li>" for v in confluence.varga_findings)
    timeline_html = "".join(f"<li style='margin-bottom:6px;'>{_clean_html_item(t)}</li>" for t in confluence.dasha_timeline)
    remedies_html = "".join(f"<li style='margin-bottom:8px;padding-left:4px;'><b>•</b> {_clean_html_item(r)}</li>" for r in confluence.remedies)

    specialist_html = ""
    if paid:
        specialist_html = _specialist_lenses_html(
            getattr(confluence, "specialist_readings", None) or {},
            lang=lang_code, clean=_clean_html_item)

    qwen_block = ""
    if paid and qwen_text:
        formatted_qwen = _format_consultation_markdown(qwen_text)
        if is_hinglish:
            synth_hdr = "Vedic Jyotish Consultation Synthesis"
        elif is_tenglish:
            synth_hdr = "Vedic Jyotish Consultation Samadhanam"
        else:
            synth_hdr = "Jyotish Consultation Synthesis"
        qwen_block = (
            f'<article class="card qwen-consultation-card" style="background:#fff;border:1px solid #e8e4dc;border-left:4px solid #b57c38;border-radius:12px;padding:20px 22px;margin:18px 0;box-shadow:0 2px 8px rgba(0,0,0,0.03);">\n'
            f'  <div style="font-size:0.7rem;letter-spacing:0.14em;text-transform:uppercase;font-weight:800;color:#7a4b18;margin-bottom:10px;">{synth_hdr}</div>\n'
            f'  {formatted_qwen}\n'
            f'</article>\n'
        )

    if is_hinglish:
        clock_hdr = "Chalu Dasha Aur Grah Alignment:"
        av_hdr = "Ashtakavarga Bal:"
        transit_hdr = "Grah Gochar (Transits):"
    elif is_tenglish:
        clock_hdr = "Chalu Dasha Mariyu Graha Alignment:"
        av_hdr = "Ashtakavarga Balam:"
        transit_hdr = "Graha Gocharam (Transits):"
    else:
        clock_hdr = "Active Multi-Clock Alignment:"
        av_hdr = "Ashtakavarga Strength:"
        transit_hdr = "Planetary Transits (Gochar):"

    if paid:
        confluence_bar = (
            f'<div style="background:#fcfbf8;border-left:3px solid #b57c38;padding:10px 14px;border-radius:8px;margin:14px 0 16px;font-size:0.86rem;line-height:1.5;color:#2c3140;">\n'
            f'  <b>{clock_hdr}</b> {html.escape(confluence.triple_dasha_confluence)}<br>\n'
            f'  <b>{av_hdr}</b> {html.escape(confluence.ashtakavarga_finding)}<br>\n'
            f'  <b>{transit_hdr}</b> {html.escape(confluence.transit_finding)}\n'
            f'</div>\n'
        )
    else:
        # Scrub exact date ranges like (2026-03-05 to 2027-02-09) from free view
        cleaned_clock = re.sub(r"\s*\(\d{4}-\d{2}-\d{2}[^)]*\)", "", confluence.triple_dasha_confluence)
        confluence_bar = (
            f'<div style="background:#fcfbf8;border-left:3px solid #b57c38;padding:10px 14px;border-radius:8px;margin:14px 0 16px;font-size:0.86rem;line-height:1.5;color:#2c3140;">\n'
            f'  <b>{clock_hdr}</b> {html.escape(cleaned_clock)}<br>\n'
            f'  <b>{av_hdr}</b> {html.escape(confluence.ashtakavarga_finding)}<br>\n'
            f'  <b>{transit_hdr}</b> {html.escape(confluence.transit_finding)}\n'
            f'</div>\n'
        )

    if is_hinglish:
        proof_title = "🔍 Jyotishiya Praman Aur Kundli Ganana (View Details)"
    elif is_tenglish:
        proof_title = "🔍 Jyotishya Aadharalu Mariyu Kundali Ganana (View Details)"
    else:
        proof_title = "🔍 View Astrological Technical Proof &amp; Divisional Chart Working"
    proof_collapsible = (
        f'<details class="astro-proof-details" style="background:#fcfbf8;border:1px solid #e8e4dc;border-radius:10px;padding:12px 16px;margin:16px 0;">\n'
        f'  <summary style="cursor:pointer;font-size:0.82rem;font-weight:700;color:#7a4b18;outline:none;">\n'
        f'    {proof_title}\n'
        f'  </summary>\n'
        f'  <div style="margin-top:10px;padding-top:10px;border-top:1px solid #eee8dc;font-size:0.86rem;line-height:1.55;color:#333;">\n'
        f'    <ul style="margin:0;padding-left:18px;">\n'
        f'      <li style="margin-bottom:4px;"><b>Primary Governing House ({confluence.primary_house}th):</b> {html.escape(confluence.dusthana_finding)}</li>\n'
        f'      <li style="margin-bottom:4px;"><b>{av_hdr}</b> {html.escape(confluence.ashtakavarga_finding)}</li>\n'
        f'      <li style="margin-bottom:4px;"><b>{transit_hdr}</b> {html.escape(confluence.transit_finding)}</li>\n'
        f'      {karakas_html}\n'
        f'      {vargas_html}\n'
        f'    </ul>\n'
        f'  </div>\n'
        f'</details>\n'
    )

    if paid:
        if is_hinglish:
            timing_hdr = "Dasha Timeline Aur Mukhya Badlav"
            running_hdr = "Chalu Dasha Period:"
            breakthrough_hdr = "Mukhya Breakthrough Window:"
            remedy_hdr = "Vedic Upay Aur Dainik Margdarshan"
            remedy_p = "Grah shanti aur prabhavi upayo se chunautiyon ko santulit kiya ja sakta hai:"
        elif is_tenglish:
            timing_hdr = "Dasha Timeline Mariyu Mukhya Badlavulu"
            running_hdr = "Chalu Dasha Period:"
            breakthrough_hdr = "Mukhya Breakthrough Window:"
            remedy_hdr = "Vedic Upayamulu Mariyu Margadarshanam"
            remedy_p = "Graha shanti mariyu prabhavavanthamaina upayamulatho challenges ni balance cheyavachu:"
        else:
            timing_hdr = "Dasha Timeline &amp; Key Turning Points"
            running_hdr = "Active Running Period:"
            breakthrough_hdr = "Major Breakthrough Window:"
            remedy_hdr = "Targeted Vedic Upaya (Actionable Remedies)"
            remedy_p = "Practical steps and planetary mantras designed to neutralize obstructive friction and energize your key functional rulers:"

        timing_section = (
            f'<article class="card timing-card" style="background:#fff;border:1px solid #e8e4dc;border-radius:12px;padding:18px 20px;margin-bottom:16px;">\n'
            f'  <div style="font-size:0.72rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:800;color:#7a4b18;margin-bottom:8px;">{timing_hdr}</div>\n'
            f'  <div style="background:#fcfbf8;border-left:3px solid #b57c38;border-radius:6px;padding:8px 12px;margin-bottom:10px;font-size:0.86rem;color:#2c3140;">\n'
            f'    <b>{running_hdr}</b> {html.escape(confluence.current_dasha)}<br>\n'
            f'    <b>{breakthrough_hdr}</b> <span style="color:#b57c38;font-weight:700;">{html.escape(confluence.breakthrough_period)}</span>\n'
            f'  </div>\n'
            f'  <ul style="margin:0 0 0 18px;padding:0;font-size:0.84rem;line-height:1.5;color:#555;">\n'
            f'    {timeline_html}\n'
            f'  </ul>\n'
            f'</article>\n'
        )
        remedy_section = (
            f'<article class="card remedy-card" style="background:#f9fbf9;border:1px solid #d4e8dc;border-left:4px solid #1c6b45;border-radius:12px;padding:18px 20px;margin-top:18px;">\n'
            f'  <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.12em;color:#1c6b45;margin-bottom:8px;">{remedy_hdr}</div>\n'
            f'  <p style="font-size:0.86rem;color:#444;margin:0 0 10px;line-height:1.45;">{remedy_p}</p>\n'
            f'  <ul style="list-style:none;margin:0;padding:0;font-size:0.88rem;line-height:1.55;color:#2c3140;">\n'
            f'    {remedies_html}\n'
            f'  </ul>\n'
            f'</article>\n'
        )
        unlock_cta_box = ""
    else:
        if is_hinglish:
            timing_section = (
                f'<div class="lock-wrap" data-unlock="1" role="button" tabindex="0" style="margin:16px 0;border-radius:12px;cursor:pointer;">\n'
                f'  <div class="lock-blur" style="padding:16px 20px;font-size:0.88rem;line-height:1.55;">\n'
                f'    <b>Mukhya Badlav Aur Timing Windows:</b> Sthiti badalne ka specific mahina aur saal, breakthrough windows aur Dasha milestones.\n'
                f'  </div>\n'
                f'  <div class="lock-over" data-unlock="1">\n'
                f'    <span class="lock-chip" data-unlock="1" style="font-size:0.72rem;padding:7px 18px;cursor:pointer;">🔒 Breakthrough Dates Aur Timeline Unlock Karein</span>\n'
                f'  </div>\n'
                f'</div>\n'
            )
            remedy_section = (
                f'<div class="lock-wrap" data-unlock="1" role="button" tabindex="0" style="margin:16px 0;border-radius:12px;cursor:pointer;">\n'
                f'  <div class="lock-blur" style="padding:16px 20px;font-size:0.88rem;line-height:1.55;">\n'
                f'    <b>Vedic Upay Aur Remedies:</b> Grah mantras, daan vidhi aur daily rituals is prashna ke samadhan ke liye.\n'
                f'  </div>\n'
                f'  <div class="lock-over" data-unlock="1">\n'
                f'    <span class="lock-chip" data-unlock="1" style="font-size:0.72rem;padding:7px 18px;cursor:pointer;">🔒 Poori Upay Aur Remedies Unlock Karein</span>\n'
                f'  </div>\n'
                f'</div>\n'
            )
            unlock_cta_box = (
                f'<div class="buy" style="margin:20px 0;background:linear-gradient(135deg,#1f2430 0%,#141720 100%);border:1px solid #c9a227;border-radius:14px;padding:22px 20px;text-align:center;color:#fff;box-shadow:0 4px 20px rgba(0,0,0,0.12);">\n'
                f'  <div style="font-size:0.72rem;letter-spacing:0.14em;text-transform:uppercase;color:#d9a544;font-weight:700;margin-bottom:6px;">Poori Astrological Consultation Available</div>\n'
                f'  <h3 style="font-family:Georgia,serif;font-size:1.2rem;color:#fbf6e4;margin:0 0 8px;font-weight:600;">Breakthrough Dates, Full Timeline &amp; Upaya Remedies Unlock Karein</h3>\n'
                f'  <p style="font-size:0.85rem;color:#b8bdcc;margin:0 auto 16px;max-width:540px;line-height:1.5;">Exact milestone dates, active Dasha turning points aur custom planetary remedies ke sath poori consultation dekhein.</p>\n'
                f'  <a class="cta" href="#unlock" data-unlock="1" style="cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px;background:linear-gradient(135deg,#e8b75b 0%,#c9a227 100%);color:#16181d;font-weight:700;font-size:0.95rem;padding:13px 28px;border-radius:99px;text-decoration:none;box-shadow:0 4px 14px rgba(201,162,39,0.35);width:100%;max-width:320px;margin:0 auto;">🔒 Poori Consultation Unlock Karein — ₹298</a>\n'
                f'  <div style="font-size:0.74rem;color:#8c93a6;margin-top:10px;">Instant Access · 100% Secure Checkout</div>\n'
                f'</div>\n'
            )
        elif is_tenglish:
            timing_section = (
                f'<div class="lock-wrap" data-unlock="1" role="button" tabindex="0" style="margin:16px 0;border-radius:12px;cursor:pointer;">\n'
                f'  <div class="lock-blur" style="padding:16px 20px;font-size:0.88rem;line-height:1.55;">\n'
                f'    <b>Mukhya Badlavulu Mariyu Timing Windows:</b> Sthiti maarina specific nela mariyu samvathsaram, breakthrough windows mariyu Dasha milestones.\n'
                f'  </div>\n'
                f'  <div class="lock-over" data-unlock="1">\n'
                f'    <span class="lock-chip" data-unlock="1" style="font-size:0.72rem;padding:7px 18px;cursor:pointer;">🔒 Breakthrough Dates Mariyu Timeline Unlock Cheyandi</span>\n'
                f'  </div>\n'
                f'</div>\n'
            )
            remedy_section = (
                f'<div class="lock-wrap" data-unlock="1" role="button" tabindex="0" style="margin:16px 0;border-radius:12px;cursor:pointer;">\n'
                f'  <div class="lock-blur" style="padding:16px 20px;font-size:0.88rem;line-height:1.55;">\n'
                f'    <b>Vedic Upayamulu Mariyu Pariharalu:</b> Graha mantralu, daana vidhi mariyu daily rituals ee prashna parishkaram kosam.\n'
                f'  </div>\n'
                f'  <div class="lock-over" data-unlock="1">\n'
                f'    <span class="lock-chip" data-unlock="1" style="font-size:0.72rem;padding:7px 18px;cursor:pointer;">🔒 Sampoorna Upayamulu Unlock Cheyandi</span>\n'
                f'  </div>\n'
                f'</div>\n'
            )
            unlock_cta_box = (
                f'<div class="buy" style="margin:20px 0;background:linear-gradient(135deg,#1f2430 0%,#141720 100%);border:1px solid #c9a227;border-radius:14px;padding:22px 20px;text-align:center;color:#fff;box-shadow:0 4px 20px rgba(0,0,0,0.12);">\n'
                f'  <div style="font-size:0.72rem;letter-spacing:0.14em;text-transform:uppercase;color:#d9a544;font-weight:700;margin-bottom:6px;">Sampoorna Astrological Consultation Siddham Ga Undi</div>\n'
                f'  <h3 style="font-family:Georgia,serif;font-size:1.2rem;color:#fbf6e4;margin:0 0 8px;font-weight:600;">Breakthrough Dates, Full Timeline &amp; Upaya Pariharalu Unlock Cheyandi</h3>\n'
                f'  <p style="font-size:0.85rem;color:#b8bdcc;margin:0 auto 16px;max-width:540px;line-height:1.5;">Exact milestone dates, active Dasha turning points mariyu custom graha pariharalatho sampoorna consultation chudandi.</p>\n'
                f'  <a class="cta" href="#unlock" data-unlock="1" style="cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px;background:linear-gradient(135deg,#e8b75b 0%,#c9a227 100%);color:#16181d;font-weight:700;font-size:0.95rem;padding:13px 28px;border-radius:99px;text-decoration:none;box-shadow:0 4px 14px rgba(201,162,39,0.35);width:100%;max-width:320px;margin:0 auto;">🔒 Sampoorna Consultation Unlock Cheyandi — ₹298</a>\n'
                f'  <div style="font-size:0.74rem;color:#8c93a6;margin-top:10px;">Instant Access · 100% Secure Checkout</div>\n'
                f'</div>\n'
            )
        else:
            timing_section = (
                f'<div class="lock-wrap" data-unlock="1" role="button" tabindex="0" style="margin:16px 0;border-radius:12px;cursor:pointer;">\n'
                f'  <div class="lock-blur" style="padding:16px 20px;font-size:0.88rem;line-height:1.55;">\n'
                f'    <b>Active Turning Point &amp; Timing Windows:</b> Specific month and year when this situation shifts, breakthrough windows, and Dasha milestone dates.\n'
                f'  </div>\n'
                f'  <div class="lock-over" data-unlock="1">\n'
                f'    <span class="lock-chip" data-unlock="1" style="font-size:0.72rem;padding:7px 18px;cursor:pointer;">🔒 Unlock Breakthrough Dates &amp; Milestone Timeline</span>\n'
                f'  </div>\n'
                f'</div>\n'
            )
            remedy_section = (
                f'<div class="lock-wrap" data-unlock="1" role="button" tabindex="0" style="margin:16px 0;border-radius:12px;cursor:pointer;">\n'
                f'  <div class="lock-blur" style="padding:16px 20px;font-size:0.88rem;line-height:1.55;">\n'
                f'    <b>Targeted Vedic Upaya:</b> Specific planetary mantras, gemstone calibrations, and daily charitable rituals to resolve this challenge.\n'
                f'  </div>\n'
                f'  <div class="lock-over" data-unlock="1">\n'
                f'    <span class="lock-chip" data-unlock="1" style="font-size:0.72rem;padding:7px 18px;cursor:pointer;">🔒 Complete Upaya &amp; Remedies in Full Reading</span>\n'
                f'  </div>\n'
                f'</div>\n'
            )
            unlock_cta_box = (
                f'<div class="buy" style="margin:20px 0;background:linear-gradient(135deg,#1f2430 0%,#141720 100%);border:1px solid #c9a227;border-radius:14px;padding:22px 20px;text-align:center;color:#fff;box-shadow:0 4px 20px rgba(0,0,0,0.12);">\n'
                f'  <div style="font-size:0.72rem;letter-spacing:0.14em;text-transform:uppercase;color:#d9a544;font-weight:700;margin-bottom:6px;">Complete Astrological Reading Available</div>\n'
                f'  <h3 style="font-family:Georgia,serif;font-size:1.2rem;color:#fbf6e4;margin:0 0 8px;font-weight:600;">Unlock Breakthrough Dates, Full Timeline &amp; Upaya Remedies</h3>\n'
                f'  <p style="font-size:0.85rem;color:#b8bdcc;margin:0 auto 16px;max-width:540px;line-height:1.5;">Get the complete multi-technique synthesis: exact milestone dates, active Dasha turning points, custom planetary mantras, and actionable remedies.</p>\n'
                f'  <a class="cta" href="#unlock" data-unlock="1" style="cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px;background:linear-gradient(135deg,#e8b75b 0%,#c9a227 100%);color:#16181d;font-weight:700;font-size:0.95rem;padding:13px 28px;border-radius:99px;text-decoration:none;box-shadow:0 4px 14px rgba(201,162,39,0.35);width:100%;max-width:320px;margin:0 auto;">🔒 Unlock Full Consultation — ₹298</a>\n'
                f'  <div style="font-size:0.74rem;color:#8c93a6;margin-top:10px;">Instant Access · 100% Secure Checkout</div>\n'
                f'</div>\n'
            )

    verdict_text = confluence.classical_verdict if paid else (confluence.root_cause_diagnosis or confluence.classical_verdict)
    if is_hinglish and verdict_text and "chart indicates" in verdict_text.lower():
        verdict_text = (
            f"Aapki kundli ke anusar, {dom_title} ke mukhya swami {confluence.primary_house_lord} {confluence.primary_lord_placement} mein sthit hain. "
            f"Yeh sthiti vartaman samay mein thoda vilamb aur mehnat ka sanket deti hai. "
            f"Lekin D10/D9 chart ki sthirta aur shubh dasha aane par sthiti mein decisive aur positive sudhar dekhne ko milega."
        )
    elif is_tenglish and verdict_text and "chart indicates" in verdict_text.lower():
        verdict_text = (
            f"Mee kundali prakaram, {dom_title} mukhya adhipathi {confluence.primary_house_lord} {confluence.primary_lord_placement} lo unnaru. "
            f"Ee sthiti prasthutham konchem aalasyam mariyu shrama avasaramani chupisthondi. "
            f"Ayina D10/D9 chart sthiratha mariyu shubha dasha valla sthiti lo decisive mariyu positive maarpu vasthundi."
        )

    if is_hinglish:
        domain_kicker = f"Jeevan Ka Kshetra · {html.escape(dom_title)}"
        heading_title = f"\"{html.escape(confluence.question)}\" Ke Liye Jyotishiya Salah"
        root_hdr = "Grah Sthiti Aur Mool Jyotishiya Vishleshan:"
    elif is_tenglish:
        domain_kicker = f"Jeevitha Rangamu · {html.escape(dom_title)}"
        heading_title = f"\"{html.escape(confluence.question)}\" Kosam Jyotishya Salaha"
        root_hdr = "Graha Sthiti Mariyu Moola Jyotishya Vishleshana:"
    else:
        domain_kicker = f"Life Domain · {html.escape(dom_title)}"
        heading_title = f"Consultation for \"{html.escape(confluence.question)}\""
        root_hdr = "Astrological Root Cause &amp; Situation Diagnostic:"

    return (
        f'<div class="confluence-consultation-wrap" style="margin:10px 0 24px;">\n'
        f'  <article class="card headline-card" style="border-left:4px solid {pill_color};background:#fff;border-radius:12px;padding:18px 22px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,0.03);">\n'
        f'    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px;">\n'
        f'      <span style="font-size:0.72rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:700;color:#6a7080;">{domain_kicker}</span>\n'
        f'      <span class="pill" style="font-size:0.68rem;font-weight:700;padding:3px 10px;border-radius:99px;background:#fbf6e4;color:{pill_color};">{pill_label}</span>\n'
        f'    </div>\n'
        f'    <h2 style="font-family:Georgia,serif;font-size:1.3rem;margin:4px 0 8px;color:#1f2430;font-weight:600;line-height:1.35;">{heading_title}</h2>\n'
        f'    <p style="font-size:0.84rem;color:#6a7080;margin:0 0 12px;">\n'
        f'      <b>Janma Lagna:</b> {html.escape(confluence.lagna)} (Lord: {html.escape(confluence.lagna_lord)}) &nbsp;|&nbsp; <b>Moon Sign:</b> {html.escape(confluence.moon_sign)} ({html.escape(confluence.moon_nakshatra)})\n'
        f'    </p>\n'
        f'    <div style="background:#fffcfb;border-left:4px solid {pill_color};padding:12px 14px;border-radius:8px;margin-top:10px;">\n'
        f'      <b style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em;color:#9e2a1b;">{root_hdr}</b>\n'
        f'      <p style="font-size:0.91rem;line-height:1.6;color:#2c3140;margin:6px 0 0;">\n'
        f'        {html.escape(verdict_text)}\n'
        f'      </p>\n'
        f'    </div>\n'
        f'  </article>\n'
        f'  {confluence_bar}\n'
        f'  {specialist_html}\n'
        f'  {qwen_block}\n'
        f'  {timing_section}\n'
        f'  {remedy_section}\n'
        f'  {unlock_cta_box if not paid else ""}\n'
        f'  {proof_collapsible}\n'
        f'</div>\n'
    )


def audit_gate0_hardware(pc: dict) -> dict:
    """Evaluates critical hardware failure modes (joblessness, Raja Bhanga, Gandanta)."""
    planets = pc.get("planets", {})
    lagna_info = pc.get("lagna", {})
    lagna_sign = lagna_info.get("sign", "Aries") if isinstance(lagna_info, dict) else "Aries"
    lagna_lord = SIGN_LORDS.get(lagna_sign, "Mars")
    
    issues = []
    is_jobless_failure = False
    is_neurodivergent = False
    
    # 1. Mars-Saturn Graha Yuddha (< 2.0° in same sign)
    mars = planets.get("Mars", {})
    saturn = planets.get("Saturn", {})
    if mars.get("sign") == saturn.get("sign") and mars.get("sign"):
        deg_diff = abs(mars.get("degree_in_sign", 0.0) - saturn.get("degree_in_sign", 0.0))
        if deg_diff <= 2.0:
            is_jobless_failure = True
            issues.append(f"Mars-Saturn Graha Yuddha ({deg_diff:.2f}° apart in {mars.get('sign')}) -> Severe execution friction & vocational paralysis.")

    # 2. Lagna Lord in 8th House Duryoga (Unassisted Alasya)
    ll_data = planets.get(lagna_lord, {})
    ll_house = ll_data.get("house")
    ll_sign = ll_data.get("sign", "")
    ll_nak = ll_data.get("nakshatra", "")
    if ll_house == 8:
        h9_sign = SIGNS[(SIGNS.index(lagna_sign) + 8) % 12]
        h9_lord = SIGN_LORDS.get(h9_sign, "")
        h9_data = planets.get(h9_lord, {})
        is_protected = (h9_data.get("house") == 8) or (planets.get("Jupiter", {}).get("house") in [8, 12, 2, 4])
        if not is_protected:
            is_jobless_failure = True
            issues.append(f"Lagna Lord ({lagna_lord}) in 8th house ({ll_sign} in {ll_nak}) unassisted -> Classical Duryoga: chronic worldly inertia (Alasya) & severe corporate joblessness.")

    # 3. Action-Mars in Gandanta
    m_s = mars.get("sign", "")
    m_deg = mars.get("degree_in_sign", 0.0)
    if (m_s in ["Pisces", "Cancer", "Scorpio"] and m_deg >= 29.20) or \
       (m_s in ["Aries", "Leo", "Sagittarius"] and m_deg <= 0.80):
        is_jobless_failure = True
        issues.append(f"Action-Karaka Mars in Gandanta zone ({m_deg:.2f}° {m_s}) -> Permanent friction with corporate hierarchy & erratic executive drive.")

    # 4. Moon Crushed by Saturn + Rahu (Shrapit / Vish Yoga)
    moon = planets.get("Moon", {})
    m_s = moon.get("sign", "")
    s_s = saturn.get("sign", "")
    rahu = planets.get("Rahu", {})
    r_s = rahu.get("sign", "")
    if m_s and m_s == s_s and m_s == r_s:
        is_jobless_failure = True
        issues.append(f"Moon crushed by Saturn and Rahu in {m_s} -> Severe Shrapit & Vish Yoga: chronic cognitive fog, despondency & vocational blockages.")

    # 5. Kemadruma Yoga
    if m_s and m_s in SIGNS:
        m_idx = SIGNS.index(m_s)
        sign_2nd = SIGNS[(m_idx + 1) % 12]
        sign_12th = SIGNS[(m_idx - 1) % 12]
        flanking = [p for p, d in planets.items() if p not in ["Sun", "Moon", "Rahu", "Ketu", "Lagna"] and d.get("sign") in [sign_2nd, sign_12th]]
        kendra_planets = [p for p, d in planets.items() if p not in ["Rahu", "Ketu", "Lagna"] and d.get("sign") in SIGNS and (((SIGNS.index(d.get("sign")) - m_idx) % 12) + 1) in [1, 4, 7, 10]]
        if not flanking and len(kendra_planets) <= 1:
            issues.append(f"Kemadruma Yoga on Moon in {m_s} without strong Kendra cancellation -> Periodic emotional isolation & financial instability.")

    # 6. Neurodivergent / Speech Delay Signature
    h2_sign = SIGNS[(SIGNS.index(lagna_sign) + 1) % 12]
    h2_lord = SIGN_LORDS.get(h2_sign, "")
    h2_lord_data = planets.get(h2_lord, {})
    if rahu.get("house") == 5 and h2_lord_data.get("house") in [6, 8, 12]:
        is_neurodivergent = True
        issues.append(f"5th House Rahu + 2nd Lord of Speech ({h2_lord}) in {h2_lord_data.get('house')}th Dusthana -> Atypical non-verbal sensory processing & formative speech delays.")

    status = "SEVERE_CONTINGENCY_REQUIRED" if is_jobless_failure else ("NEURODIVERGENT_SPEECH_GATED" if is_neurodivergent else "HEALTHY_HARDWARE")
    
    contingency_rule = "Standard corporate & worldly progression fully viable."
    if is_jobless_failure:
        contingency_rule = "MANDATORY VOCATIONAL PIVOT: Suppress standard 9-to-5 corporate job predictions. Recommend independent consultancy, partner/spouse-led commercial ventures, property asset management, or specialized craftsmanship."
    elif is_neurodivergent:
        contingency_rule = "PEDIATRIC DEVELOPMENT PROTOCOL: Speech breakthrough is strictly tied to Mercury Antardasha and Jupiter-Mercury transits. Do not prescribe high-pressure verbal schooling; implement sensory grounding remedies and non-debilitating pediatric gemstones (Pearl/Emerald/Rudraksha)."

    return {
        "status": status,
        "is_jobless_failure": is_jobless_failure,
        "is_neurodivergent": is_neurodivergent,
        "issues": issues,
        "contingency_rule": contingency_rule
    }


def analyze_chandra_nadi(pc: dict) -> dict:
    """Evaluates native's psychological core, Chandra Lagna aspects, and live Gochara hits."""
    planets = pc.get("planets", {})
    moon = planets.get("Moon", {})
    m_sign = moon.get("sign", "Aries")
    m_deg = moon.get("degree_in_sign", 0.0)
    m_nak = moon.get("nakshatra", "")
    m_pada = moon.get("pada", moon.get("nakshatra_pada", 1))
    m_house = moon.get("house", 1)

    # 1. Moon Conjunctions (1st from Moon)
    conjunctions = [p for p, d in planets.items() if p != "Moon" and d.get("sign") == m_sign]

    # 2. Aspects on Moon
    aspects = []
    m_idx = SIGNS.index(m_sign) if m_sign in SIGNS else 0
    for p, d in planets.items():
        if p in ["Moon", "Lagna"]:
            continue
        p_sign = d.get("sign", "")
        if p_sign not in SIGNS:
            continue
        dist = ((SIGNS.index(m_sign) - SIGNS.index(p_sign)) % 12) + 1
        if dist == 7:
            aspects.append(f"{p} in {p_sign} (Direct 7th opposition)")
        elif p == "Mars" and dist in [4, 8]:
            aspects.append(f"Mars in {p_sign} (Special {dist}th aspect: emotional volatility / high drive)")
        elif p == "Saturn" and dist in [3, 10]:
            aspects.append(f"Saturn in {p_sign} (Special {dist}th aspect: duty pressure / depressive undertone)")
        elif p == "Jupiter" and dist in [5, 9]:
            aspects.append(f"Jupiter in {p_sign} (Special {dist}th aspect: divine grace / mental equilibrium)")

    # 3. Live transits from the current ephemeris (never hardcode a year's signs)
    transit_hits = []
    transit: dict = {}
    try:
        from datetime import datetime as _dt
        from transit_planet_analysis import get_transit_positions
        transit = get_transit_positions(_dt.now()) or {}
    except Exception as exc:  # noqa: BLE001
        print(f"[confluence_question_engine] live transit lookup failed: {exc}", flush=True)

    sat_sign = str((transit.get("Saturn") or {}).get("sign") or "")
    rahu_t_sign = str((transit.get("Rahu") or {}).get("sign") or "")
    ketu_t_sign = str((transit.get("Ketu") or {}).get("sign") or "")

    if sat_sign in SIGNS:
        sat_from_moon = ((SIGNS.index(sat_sign) - m_idx) % 12) + 1
        if sat_from_moon == 12:
            transit_hits.append(f"Transit Saturn in {sat_sign} in 12th from Moon -> First Phase of SADE SATI (mental restructuring, expenses, sleep disruption).")
        elif sat_from_moon == 1:
            transit_hits.append(f"Transit Saturn in {sat_sign} directly over Natal Moon -> Peak SADE SATI (heavy emotional pressure, identity transformation).")
        elif sat_from_moon == 2:
            transit_hits.append(f"Transit Saturn in {sat_sign} in 2nd from Moon -> Final Phase of SADE SATI (financial reorganization, family restructuring).")
        elif sat_from_moon == 8:
            transit_hits.append(f"Transit Saturn in {sat_sign} in 8th from Moon -> ASHTAMA SHANI (acute stress, sudden transitions, high caution required).")
        elif sat_from_moon == 4:
            transit_hits.append(f"Transit Saturn in {sat_sign} in 4th from Moon -> KANTAKA SHANI (domestic friction, mother's health, peace of mind challenges).")

    if rahu_t_sign in SIGNS:
        rahu_from_moon = ((SIGNS.index(rahu_t_sign) - m_idx) % 12) + 1
        if rahu_from_moon == 1:
            transit_hits.append(f"Transit Rahu in {rahu_t_sign} over Natal Moon -> Eclipse on Manas: acute anxiety, illusions, restlessness.")
        elif rahu_from_moon == 7:
            transit_hits.append(f"Transit Ketu opposing Natal Moon -> Emotional detachment, spiritual withdrawal, relationship alienation.")

    if ketu_t_sign in SIGNS:
        ketu_from_moon = ((SIGNS.index(ketu_t_sign) - m_idx) % 12) + 1
        if ketu_from_moon == 1:
            transit_hits.append(f"Transit Ketu in {ketu_t_sign} over Natal Moon -> Emotional detachment, spiritual withdrawal, relationship alienation.")

    jup_sign = planets.get("Jupiter", {}).get("sign", "")
    if jup_sign and sat_sign and jup_sign == sat_sign:
        transit_hits.append(f"Transit Saturn conjoining Natal Jupiter in {jup_sign} -> Nadi Karma-Jeeva Yoga: foundational career restructuring & life path shift.")
    elif jup_sign and rahu_t_sign and jup_sign == rahu_t_sign:
        transit_hits.append(f"Transit Rahu over Natal Jupiter in {jup_sign} -> Jeeva-Rahu Contact: spiritual doubt, existential questioning.")

    natal_rahu = planets.get("Rahu", {}).get("sign", "")
    if natal_rahu and ketu_t_sign and natal_rahu == ketu_t_sign:
        transit_hits.append(f"Transit Ketu over Natal Rahu in {natal_rahu} -> Nodal Reversal: acute relationship or romantic disillusionment, desire to detach.")

    return {
        "moon_summary": f"Moon in {m_sign} ({m_deg:.2f}°, {m_nak} Pada {m_pada}) in House {m_house}",
        "conjunctions": conjunctions or ["None (Solitary Moon)"],
        "aspects": aspects or ["No major malefic/benefic aspects"],
        "transit_hits": transit_hits or ["No catastrophic Gochara afflictions on Moon currently"]
    }


def _deterministic_chat_fallback(pc: dict, question: str, *,
                                  domain_override: str = "",
                                  target_planet: str = "",
                                  route: Any = None) -> dict:
    """Plain prose when the planner or voice pass is unavailable."""
    conf = analyze_question_confluence(
        pc, question, domain_override=domain_override, route=route,
        target_planet=target_planet)
    if conf.domain_key == "out_of_domain":
        ans = (
            "That question sits outside what I can read from your chart. "
            "Ask me about your work, money, family, health, relationships, "
            "timing, gemstones or remedies, and I will answer from the "
            "facts in your reading."
        )
        return {
            "answer": ans,
            "out_of_scope": True,
            "used_fact_ids": ["out_of_domain"],
            "stats": {"accepted": 1, "rejected": 0, "fallback": "deterministic"},
        }
    ans = (
        f"{conf.classical_verdict} Your primary breakthrough window is "
        f"{conf.breakthrough_period}."
    )
    extra = []
    for r in (conf.remedies or []):
        if r.startswith("Lal Kitab") or r.startswith("Chandra Naadi"):
            extra.append(r)
    if extra:
        ans += " " + extra[0]
    elif conf.remedies:
        ans += " " + conf.remedies[0]
    return {
        "answer": ans,
        "out_of_scope": False,
        "used_fact_ids": [conf.domain_key, "breakthrough_period"],
        "stats": {"accepted": 1, "rejected": 0, "fallback": "deterministic"},
    }


def answer_chat_with_confluence(pc: dict, question: str,
                                history: Optional[list[dict]] = None,
                                lang: str = "en") -> dict:
    """Plan → run tools → write in the reader's voice → validate.

    When the planner is unavailable the older MiniLM / keyword path still
    answers, so chat never goes silent with the LLM switched off.
    """
    history = history or []
    question = (question or "").strip()
    if not question:
        return {
            "answer": "Ask me something about your chart and I will answer from it.",
            "out_of_scope": False,
            "used_fact_ids": [],
            "stats": {"accepted": 0, "rejected": 0},
        }

    plan = None
    try:
        from llm.question_planner import (
            plan_as_calls,
            plan_question,
            write_in_user_voice,
        )
        plan = plan_question(question, history=history)
    except Exception as exc:  # noqa: BLE001
        print(f"[confluence_question_engine] planner failed: {exc}", flush=True)
        plan = None

    if plan is not None:
        if not plan.in_scope:
            voice = ""
            try:
                voice = write_in_user_voice(
                    question, plan, {}, history=history, lang=lang)
            except Exception as exc:  # noqa: BLE001
                print(f"[confluence_question_engine] voice (oos) failed: {exc}",
                      flush=True)
            if voice and ("```" in voice or "def " in voice):
                voice = ""
            if not voice:
                voice = (
                    "That one sits outside astrology. I can read your chart "
                    "for work, money, family, health, relationships, timing, "
                    "gemstones and remedies — ask me about any of those."
                )
            return {
                "answer": voice,
                "out_of_scope": True,
                "used_fact_ids": ["out_of_domain"],
                "stats": {"accepted": 1, "rejected": 0, "path": "planner"},
            }

        try:
            from astro_tools import run_tools
            results = run_tools(
                pc, plan_as_calls(plan), question=question, lang=lang)
        except Exception as exc:  # noqa: BLE001
            print(f"[confluence_question_engine] run_tools failed: {exc}",
                  flush=True)
            results = {}

        voice = ""
        try:
            voice = write_in_user_voice(
                question, plan, results, history=history, lang=lang)
        except Exception as exc:  # noqa: BLE001
            print(f"[confluence_question_engine] voice failed: {exc}",
                  flush=True)

        if voice:
            from llm.grounding import extract_ledger, enforce_grounding
            leftover = enforce_grounding(
                voice, extract_ledger(results), question)
            if leftover:
                print(f"[confluence_question_engine] grounded reject: "
                      f"{leftover}", flush=True)
                voice = ""

        if voice:
            return {
                "answer": voice,
                "out_of_scope": False,
                "used_fact_ids": list(results.keys()) or [plan.life_area],
                "stats": {"accepted": 1, "rejected": 0, "path": "planner"},
            }

        from llm.grounding import deterministic_from_results
        det = deterministic_from_results(results, question)
        if det:
            return {
                "answer": det,
                "out_of_scope": False,
                "used_fact_ids": list(results.keys()) or [plan.life_area],
                "stats": {"accepted": 1, "rejected": 0, "path": "grounded"},
            }

        return _deterministic_chat_fallback(
            pc, question,
            domain_override=plan.life_area,
            target_planet=getattr(plan, "target_planet", "") or "",
        )

    # Planner unavailable — MiniLM first, then keyword tables.
    route = None
    try:
        import semantic_question as SQ
        route = SQ.route(question, area="")
    except Exception:  # noqa: BLE001
        route = None
    domain = _fallback_detect_domain(question, route=route)
    return _deterministic_chat_fallback(
        pc, question, domain_override=domain, route=route)

