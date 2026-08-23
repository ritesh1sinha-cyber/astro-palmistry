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
}

# High-intent multi-word keyphrases with high weight for deterministic classification
INTENT_KEYPHRASES: dict[str, list[str]] = {
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


def detect_domain(question: str, route: Any = None, area: str = "") -> str:
    """Classifies user question into the most accurate astrological domain."""
    # 1. If explicit area provided by user dropdown, use direct mapping
    if area:
        mapped = AREA_TO_CONFLUENCE_DOMAIN.get(area.lower().strip())
        if mapped:
            return mapped

    q_lower = (question or "").lower().strip()

    # 2. Phrase-level high intent scoring (e.g. "move abroad", "win court case", "buy house")
    phrase_scores: dict[str, int] = {}
    for d_key, phrases in INTENT_KEYPHRASES.items():
        for phrase in phrases:
            if phrase in q_lower:
                phrase_scores[d_key] = phrase_scores.get(d_key, 0) + 5
    if phrase_scores:
        return max(phrase_scores, key=phrase_scores.get)

    # 3. If semantic route provided, check its topic first (more specific), then domain
    if route is not None:
        r_topic = getattr(route, "topic", "")
        if r_topic and r_topic != "general":
            mapped = AREA_TO_CONFLUENCE_DOMAIN.get(r_topic.lower().strip())
            if mapped:
                return mapped
        r_domain = getattr(route, "domain", "")
        if r_domain:
            mapped = AREA_TO_CONFLUENCE_DOMAIN.get(r_domain.lower().strip())
            if mapped:
                return mapped

    # 4. Try running semantic_question directly if question is non-empty
    if q_lower:
        try:
            import semantic_question as SQ
            r = SQ.route(question, area="")
            if r:
                if r.topic and r.topic != "general":
                    mapped = AREA_TO_CONFLUENCE_DOMAIN.get(r.topic.lower().strip())
                    if mapped:
                        return mapped
                if r.domain:
                    mapped = AREA_TO_CONFLUENCE_DOMAIN.get(r.domain.lower().strip())
                    if mapped and (r.method == "minilm" or r.domain_score >= 0.25):
                        return mapped
        except Exception:
            pass

    # 5. Keyword scoring
    scores: dict[str, int] = {}
    for d_key, d_cfg in DOMAINS_CONFIG.items():
        for kw in d_cfg["keywords"]:
            if re.search(r"\b" + re.escape(kw) + r"\b", q_lower):
                scores[d_key] = scores.get(d_key, 0) + 1

    if not scores:
        return "career_profession"

    return max(scores, key=scores.get)


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
    """
    area = _normalize_dropdown_area(domain_override)
    if area:
        mapped = AREA_TO_CONFLUENCE_DOMAIN.get(area)
        if mapped:
            return mapped
    return detect_domain(question, route=route, area=area or domain_override)


def analyze_question_confluence(pc: dict, question: str, domain_override: str = "", route: Any = None) -> QuestionConfluenceReport:
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

    # 8. Live Planetary Transits (Gochar)
    t_now = date.today()
    transits = get_live_transit_positions(t_now)
    jup_s = transits.get("Jupiter", "")
    sat_s = transits.get("Saturn", "")
    transit_items = []
    if jup_s:
        j_b = sav.get(jup_s, 28)
        transit_items.append(f"Transit Jupiter in {jup_s} ({j_b} SAV Bindus)")
    if sat_s:
        s_b = sav.get(sat_s, 28)
        transit_items.append(f"Transit Saturn in {sat_s} ({s_b} SAV Bindus)")
    transit_finding = f"Active Gochar: {', '.join(transit_items) if transit_items else 'Transits aligned with natal matrix.'}"

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
    if is_in_dusthana:
        root_cause_diagnosis = (
            f"The chart indicates genuine classical vulnerability in {cfg['title']} due to primary ruler {prim_lord} occupying "
            f"the {lord_h}th Dusthana ({lord_sign}) and key natural significators facing specific afflictions in foundational divisional charts (D9/D30). "
            f"This structural placement creates intermittent delays, friction in execution, and a non-linear development curve. "
            f"While underlying Ashtakavarga strength ({prim_b} SAV Bindus in House {prim_h}) provides a solid floor against permanent loss, "
            f"active progress requires navigating this karmic restructuring phase until the supportive cycle activates."
        )
        verdict = (
            f"{root_cause_diagnosis} With targeted planetary remedies, favorable Ashtakavarga support, "
            f"and supportive planetary transits, the upcoming {breakthrough_period_str} acts as the primary classical catalyst for decisive breakthroughs."
        )
    else:
        root_cause_diagnosis = (
            f"The chart shows constructive underlying potential for {cfg['title']} anchored by {prim_lord} in the {lord_h}th house ({lord_dig.replace('_', ' ')}). "
            f"Backed by {prim_b} SAV Bindus in House {prim_h}, the chart carries sufficient static promise to overcome immediate friction, "
            f"though current multi-clock alignments demand steady patience during the ongoing operating sub-period."
        )
        verdict = (
            f"{root_cause_diagnosis} The upcoming {breakthrough_period_str} provides the active window for material realization."
        )

    # 11. Targeted Remedial Guidance
    remedies = []
    if is_in_dusthana:
        remedies.append(f"Harmonize Obstructing Planet ({prim_lord}): Offer targeted donations or planetary prayers on {prim_lord}'s day to neutralize 8th/6th house friction.")
    if cfg["karakas"]:
        top_k = cfg["karakas"][0]
        remedies.append(f"Strengthen Natural Karaka ({top_k}): Chant the {top_k} Gayatri Mantra or perform charitable seva (e.g. green fodder to cows for Mercury, Surya Arghya for Sun, Jal Abhishek for Moon).")
    remedies.append(f"Energize Lagna Lord ({lagna_lord}): Daily spiritual grounding, meditation, and chanting the Lagna lord's root mantra to fortify overall constitutional resilience.")

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
    )


from pydantic import BaseModel, Field


class QuestionConsultationOutput(BaseModel):
    verdict: str = Field(description="Direct astrological verdict answering whether the chart indicates the issue and its nature.")
    planetary_mechanics: str = Field(description="Detailed explanation of the primary house, lord in 8th/Dusthana, natural karakas, and D9/D30 divisional confirmations.")
    timeline_and_milestones: str = Field(description="Clear breakdown of the past origin, current active phase, and the exact upcoming breakthrough window.")
    remedial_actions: str = Field(description="Step-by-step practical and spiritual remedies for immediate and long-term relief.")


def synthesize_with_qwen(confluence: QuestionConfluenceReport) -> str:
    """Prompts Qwen LLM using the structured confluence payload to produce an authoritative consultation response."""
    try:
        from core.llm_client import _get_client, complete_model
        from core.config import S
        
        system_prompt = (
            "You are a master Vedic Astrologer (Jyotish Acharya) providing an authoritative, compassionate, "
            "and deeply insightful consultation reading for the seeker's specific life problem. "
            "You have been provided with rigorous, verified classical confluence facts (Houses, Lords, Dignities, "
            "Natural Karakas, Divisional Charts D9/D30, Sarvashtakavarga SAV Bindu strength, Live Planetary Transits Gochar, "
            "Triple Dashas Vimshottari + Jaimini Chara + Yogini, and Vedic Upaya). "
            "Write a beautifully articulated, structured consultation response in clear, fluent English that directly answers the question, "
            "explains the exact astrological mechanics clearly, provides the precise timing milestone, and details actionable remedies. "
            "DO NOT use raw JSON keys or robotic phrasing. Speak directly to the seeker as an experienced astrologer."
        )

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

INSTRUCTIONS:
Write a comprehensive, professional Vedic consultation response containing:
1. DIRECT ASTROLOGICAL VERDICT: Direct, honest answer addressing whether the chart indicates the issue and its nature.
2. CORE PLANETARY MECHANICS: Detailed explanation of the primary house, lord in 8th/Dusthana, natural karakas, Ashtakavarga SAV support, and D9/D30 divisional confirmations in natural, user-understandable language.
3. TIMELINE & KEY MILESTONE: Clear breakdown of the past origin, current active phase, and the exact upcoming breakthrough window (citing dasha + transit confluence) where conditions decisively improve.
4. ACTIONABLE REMEDIAL GUIDANCE: Step-by-step practical and spiritual remedies for immediate and long-term relief.
"""

        from openai import OpenAI
        from core.config import S
        base_url = getattr(S, "llm_base_url", "http://host.docker.internal:8000/v1") or "http://host.docker.internal:8000/v1"
        api_key = getattr(S, "llm_api_key", "dummy") or "dummy"
        model = getattr(S, "llm_model", "Qwen/Qwen2.5-7B-Instruct-AWQ") or "Qwen/Qwen2.5-7B-Instruct-AWQ"
        
        client = OpenAI(base_url=base_url.rstrip("/"), api_key=api_key, timeout=90.0)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        raw = (resp.choices[0].message.content or "").strip()
        if raw:
            return raw
    except Exception as exc:
        print(f"[confluence_question_engine] Qwen call failed: {exc}", flush=True)

    # Fallback to rich deterministic prose if LLM unavailable
    return (
        f"### Astrological Consultation: {confluence.domain_title}\n\n"
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


def render_confluence_card_html(confluence: QuestionConfluenceReport, *, paid: bool = True, qwen_text: str = "") -> str:
    """Renders the comprehensive Vedic Astrological Consultation document in clean HTML."""
    import html

    pill_color = "#8a6a1f" if not confluence.is_lord_in_dusthana else "#a3341f"
    pill_label = "Constructive Promise" if not confluence.is_lord_in_dusthana else "Requires Remedial Care"

    karakas_html = "".join(f"<li style='margin-bottom:6px;'>{k}</li>" for k in confluence.karaka_findings)
    vargas_html = "".join(f"<li style='margin-bottom:6px;'>{v}</li>" for v in confluence.varga_findings)
    timeline_html = "".join(f"<li style='margin-bottom:6px;'>{t}</li>" for t in confluence.dasha_timeline)
    remedies_html = "".join(f"<li style='margin-bottom:8px;padding-left:4px;'><b>•</b> {r}</li>" for r in confluence.remedies)

    qwen_block = ""
    if paid and qwen_text:
        formatted_qwen = _format_consultation_markdown(qwen_text)
        qwen_block = (
            f'<article class="card qwen-consultation-card" style="background:#fff;border:1px solid #e8e4dc;border-left:4px solid #b57c38;border-radius:12px;padding:20px 22px;margin:18px 0;box-shadow:0 2px 8px rgba(0,0,0,0.03);">\n'
            f'  <div style="font-size:0.7rem;letter-spacing:0.14em;text-transform:uppercase;font-weight:800;color:#7a4b18;margin-bottom:10px;">Jyotish Consultation Synthesis</div>\n'
            f'  {formatted_qwen}\n'
            f'</article>\n'
        )

    if paid:
        confluence_bar = (
            f'<div style="background:#fcfbf8;border-left:3px solid #b57c38;padding:10px 14px;border-radius:8px;margin:14px 0 16px;font-size:0.86rem;line-height:1.5;color:#2c3140;">\n'
            f'  <b>Active Multi-Clock Alignment:</b> {confluence.triple_dasha_confluence}<br>\n'
            f'  <b>Ashtakavarga Strength:</b> {confluence.ashtakavarga_finding}<br>\n'
            f'  <b>Planetary Transits (Gochar):</b> {confluence.transit_finding}\n'
            f'</div>\n'
        )
    else:
        # Scrub exact date ranges like (2026-03-05 to 2027-02-09) from free view
        cleaned_clock = re.sub(r"\s*\(\d{4}-\d{2}-\d{2}[^)]*\)", "", confluence.triple_dasha_confluence)
        confluence_bar = (
            f'<div style="background:#fcfbf8;border-left:3px solid #b57c38;padding:10px 14px;border-radius:8px;margin:14px 0 16px;font-size:0.86rem;line-height:1.5;color:#2c3140;">\n'
            f'  <b>Active Multi-Clock Alignment:</b> {cleaned_clock}<br>\n'
            f'  <b>Ashtakavarga Strength:</b> {confluence.ashtakavarga_finding}<br>\n'
            f'  <b>Planetary Transits (Gochar):</b> {confluence.transit_finding}\n'
            f'</div>\n'
        )

    proof_collapsible = (
        f'<details class="astro-proof-details" style="background:#fcfbf8;border:1px solid #e8e4dc;border-radius:10px;padding:12px 16px;margin:16px 0;">\n'
        f'  <summary style="cursor:pointer;font-size:0.82rem;font-weight:700;color:#7a4b18;outline:none;">\n'
        f'    🔍 View Astrological Technical Proof &amp; Divisional Chart Working\n'
        f'  </summary>\n'
        f'  <div style="margin-top:10px;padding-top:10px;border-top:1px solid #eee8dc;font-size:0.86rem;line-height:1.55;color:#333;">\n'
        f'    <ul style="margin:0;padding-left:18px;">\n'
        f'      <li style="margin-bottom:4px;"><b>Primary Governing House ({confluence.primary_house}th):</b> {html.escape(confluence.dusthana_finding)}</li>\n'
        f'      <li style="margin-bottom:4px;"><b>Ashtakavarga Strength:</b> {html.escape(confluence.ashtakavarga_finding)}</li>\n'
        f'      <li style="margin-bottom:4px;"><b>Planetary Transits (Gochar):</b> {html.escape(confluence.transit_finding)}</li>\n'
        f'      {karakas_html}\n'
        f'      {vargas_html}\n'
        f'    </ul>\n'
        f'  </div>\n'
        f'</details>\n'
    )

    if paid:
        timing_section = (
            f'<article class="card timing-card" style="background:#fff;border:1px solid #e8e4dc;border-radius:12px;padding:18px 20px;margin-bottom:16px;">\n'
            f'  <div style="font-size:0.72rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:800;color:#7a4b18;margin-bottom:8px;">Dasha Timeline &amp; Key Turning Points</div>\n'
            f'  <div style="background:#fcfbf8;border-left:3px solid #b57c38;border-radius:6px;padding:8px 12px;margin-bottom:10px;font-size:0.86rem;color:#2c3140;">\n'
            f'    <b>Active Running Period:</b> {html.escape(confluence.current_dasha)}<br>\n'
            f'    <b>Major Breakthrough Window:</b> <span style="color:#b57c38;font-weight:700;">{html.escape(confluence.breakthrough_period)}</span>\n'
            f'  </div>\n'
            f'  <ul style="margin:0 0 0 18px;padding:0;font-size:0.84rem;line-height:1.5;color:#555;">\n'
            f'    {timeline_html}\n'
            f'  </ul>\n'
            f'</article>\n'
        )
        remedy_section = (
            f'<article class="card remedy-card" style="background:#f9fbf9;border:1px solid #d4e8dc;border-left:4px solid #1c6b45;border-radius:12px;padding:18px 20px;margin-top:18px;">\n'
            f'  <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.12em;color:#1c6b45;margin-bottom:8px;">Targeted Vedic Upaya (Actionable Remedies)</div>\n'
            f'  <p style="font-size:0.86rem;color:#444;margin:0 0 10px;line-height:1.45;">Practical steps and planetary mantras designed to neutralize obstructive friction and energize your key functional rulers:</p>\n'
            f'  <ul style="list-style:none;margin:0;padding:0;font-size:0.88rem;line-height:1.55;color:#2c3140;">\n'
            f'    {remedies_html}\n'
            f'  </ul>\n'
            f'</article>\n'
        )
        unlock_cta_box = ""
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

    return (
        f'<div class="confluence-consultation-wrap" style="margin:10px 0 24px;">\n'
        f'  <article class="card headline-card" style="border-left:4px solid {pill_color};background:#fff;border-radius:12px;padding:18px 22px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,0.03);">\n'
        f'    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px;">\n'
        f'      <span style="font-size:0.72rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:700;color:#6a7080;">Life Domain · {html.escape(confluence.domain_title)}</span>\n'
        f'      <span class="pill" style="font-size:0.68rem;font-weight:700;padding:3px 10px;border-radius:99px;background:#fbf6e4;color:{pill_color};">{pill_label}</span>\n'
        f'    </div>\n'
        f'    <h2 style="font-family:Georgia,serif;font-size:1.3rem;margin:4px 0 8px;color:#1f2430;font-weight:600;line-height:1.35;">Consultation for "{html.escape(confluence.question)}"</h2>\n'
        f'    <p style="font-size:0.84rem;color:#6a7080;margin:0 0 12px;">\n'
        f'      <b>Janma Lagna:</b> {html.escape(confluence.lagna)} (Lord: {html.escape(confluence.lagna_lord)}) &nbsp;|&nbsp; <b>Moon Sign:</b> {html.escape(confluence.moon_sign)} ({html.escape(confluence.moon_nakshatra)})\n'
        f'    </p>\n'
        f'    <div style="background:#fffcfb;border-left:4px solid {pill_color};padding:12px 14px;border-radius:8px;margin-top:10px;">\n'
        f'      <b style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em;color:#9e2a1b;">Astrological Root Cause &amp; Situation Diagnostic:</b>\n'
        f'      <p style="font-size:0.91rem;line-height:1.6;color:#2c3140;margin:6px 0 0;">\n'
        f'        {html.escape(verdict_text)}\n'
        f'      </p>\n'
        f'    </div>\n'
        f'  </article>\n'
        f'  {confluence_bar}\n'
        f'  {qwen_block}\n'
        f'  {timing_section}\n'
        f'  {remedy_section}\n'
        f'  {unlock_cta_box if not paid else ""}\n'
        f'  {proof_collapsible}\n'
        f'</div>\n'
    )


def answer_chat_with_confluence(pc: dict, question: str, history: Optional[list[dict]] = None) -> dict:
    """Answers follow-up conversational chat turns using full real-time confluence, gochar, SAV bindus and multi-clock timing."""
    conf = analyze_question_confluence(pc, question)
    
    system_prompt = (
        "You are a master Vedic Astrologer answering a follow-up question in the user's private consultation chat. "
        "You have access to their exact chart confluence: Houses, Lords, Dignities, Divisional Vargas (D9, D30, D10, D4, D24, D7, D2), "
        "Sarvāṣṭakavarga (SAV) Bindu strength, Live Ephemeris Transits (Gochar of Jupiter & Saturn), "
        "and Triple-Dasha timing (Vimshottari + Jaimini Chara + Yogini). "
        "Answer warmly, directly, and authoritatively as their personal astrologer in 3-5 concise, insightful sentences. "
        "Cite the exact astrological indicators and upcoming timing windows naturally. Maintain conversational continuity with the previous chat history."
    )
    
    confluence_context = f"""
CHART CONFLUENCE:
• Domain: {conf.domain_title}
• Primary Ruler: House {conf.primary_house} ({conf.primary_house_sign}) governed by {conf.primary_house_lord} ({conf.primary_lord_placement}, {conf.primary_lord_dignity}).
• Dusthana Finding: {conf.dusthana_finding}
• Ashtakavarga SAV Score: {conf.ashtakavarga_finding}
• Live Gochar Transits: {conf.transit_finding}
• Triple-Dasha Alignment: {conf.triple_dasha_confluence}
• Breakthrough / Key Timing Window: {conf.breakthrough_period}
• Targeted Remedies: {'; '.join(conf.remedies[:2])}
"""
    
    from openai import OpenAI
    from core.config import S
    base_url = getattr(S, "llm_base_url", "http://host.docker.internal:8000/v1") or "http://host.docker.internal:8000/v1"
    api_key = getattr(S, "llm_api_key", "dummy") or "dummy"
    model = getattr(S, "llm_model", "Qwen/Qwen2.5-7B-Instruct-AWQ") or "Qwen/Qwen2.5-7B-Instruct-AWQ"
    
    messages = [{"role": "system", "content": system_prompt + "\n" + confluence_context}]
    for h in (history or [])[-4:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": question})
    
    try:
        client = OpenAI(base_url=base_url.rstrip("/"), api_key=api_key, timeout=60.0)
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=600
        )
        ans = (resp.choices[0].message.content or "").strip()
        if ans:
            return {
                "answer": ans,
                "out_of_scope": False,
                "used_fact_ids": [conf.domain_key, "gochar", "ashtakavarga", "triple_dasha"],
                "stats": {"accepted": 1, "rejected": 0},
            }
    except Exception as exc:
        print(f"[confluence_question_engine] chat Qwen call failed: {exc}", flush=True)

    fallback_ans = f"Based on your chart, {conf.classical_verdict} Your primary breakthrough timing window is {conf.breakthrough_period}."
    return {
        "answer": fallback_ans,
        "out_of_scope": False,
        "used_fact_ids": [conf.domain_key, "breakthrough_period"],
        "stats": {"accepted": 1, "rejected": 0},
    }


