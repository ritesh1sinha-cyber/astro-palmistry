#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Structured D1 (Rashi / birth chart) rules from divisional_chart-tillD10.pdf OCR.

Primary source: Comprehensive Prediction by Divisional Charts (OCR under
book_ocr/divisional_chart-tillD10/). Where a scan line broke, wording is
completed in the same book style — never generic guess text in reports.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
OCR_DIR = BASE_DIR / "book_ocr" / "divisional_chart-tillD10"
D1_OCR = OCR_DIR / "D1_chapter_ocr.txt"

# ── Birth chart intro (pdf pages 6–7, OCR) ───────────────────────────────
D1_INTRO = (
    "The birth chart (Rashi, D1) is the main chart. Each sign is divided into finer "
    "divisions for special themes, but every divisional chart is read against the "
    "promise shown in D1. Thousands may share the same lagna within two hours — "
    "outcomes differ because planet longitudes, dasha, and transits activate different "
    "parts of the same skeleton."
)

# ── House significations (pdf page 18 + book-standard completion where OCR broke) ──
D1_HOUSE_SIGNIFICATIONS: dict[int, str] = {
    1: "Body, fame, place of birth, self, honour, self-respect, peace of mind, present life, "
       "complexion, health, longevity, head, brain, hair and stamina.",
    2: "Wealth, family, speech, eating habits, taste, status or self-esteem, face, eyes, "
       "nose, nails, teeth, tongue.",
    3: "Courage and valour, hobbies, younger co-born, communication, neighbours, short "
       "journeys, ear, neck, throat, shoulders, upper limbs, physical growth.",
    4: "Mother, happiness or unhappiness, lands, houses, vehicles, education, own family, "
       "chest, lungs, heart, breast.",
    5: "Progeny, intelligence, poorva punya, mantra, devotion, speculation, stomach, liver.",
    6: "Enemies, debt, disease, accident, injury, surgical operations, service, maternal "
       "uncle, urinary tract.",
    7: "Spouse, partnership, marriage, trade, foreign travel, sexual pleasure, lower abdomen.",
    8: "Longevity, death, obstacles, inheritance, chronic disease, hidden matters, genitals.",
    9: "Father, fortune, dharma, religion, guru, long journeys, hips, thighs.",
    10: "Career, profession, karma, honour, status, knees, command.",
    11: "Gains, income, elder siblings, friends, fulfilment of desires, calves.",
    12: "Loss, expenditure, moksha, foreign lands, confinement, sleep, feet, left eye.",
}

# ── Lagna-wise key planets (pdf pages 49–50, Key Planets table) ───────────
D1_KEY_PLANETS: dict[str, dict[str, Any]] = {
    "Aries": {"yogkaraka": "—", "benefic": "Sun, Jupiter", "malefic": "Mercury, Venus, Saturn", "maraka": "Venus",
              "note": "Mars behaves as a benefic if not afflicted."},
    "Taurus": {"yogkaraka": "Saturn", "benefic": "Sun", "malefic": "Moon, Jupiter, Venus", "maraka": "Mars",
               "note": "Mercury is benefic if well associated."},
    "Gemini": {"yogkaraka": "—", "benefic": "Venus", "malefic": "Sun, Mars, Jupiter", "maraka": "Moon",
               "note": "Mercury is benefic if well associated (lagna lord)."},
    "Cancer": {"yogkaraka": "Mars", "benefic": "Moon, Jupiter", "malefic": "Mercury, Venus", "maraka": "Saturn",
               "note": "Sun is malefic or benefic as per association."},
    "Leo": {"yogkaraka": "Mars", "benefic": "Sun, Jupiter", "malefic": "Saturn, Mercury, Venus", "maraka": "Saturn",
            "note": "Moon is malefic or benefic as per association."},
    "Virgo": {"yogkaraka": "—", "benefic": "Mercury, Venus", "malefic": "Moon, Mars, Jupiter", "maraka": "Venus",
              "note": "Sun is malefic or benefic as per association."},
    "Libra": {"yogkaraka": "Saturn", "benefic": "Mercury", "malefic": "Sun, Mars, Jupiter", "maraka": "Mars",
              "note": "Venus gives results as per association."},
    "Scorpio": {"yogkaraka": "—", "benefic": "Moon, Jupiter", "malefic": "Mercury, Venus, Saturn", "maraka": "Venus",
                "note": "Mars gives results as per association."},
    "Sagittarius": {"yogkaraka": "—", "benefic": "Sun, Mars", "malefic": "Venus, Saturn", "maraka": "Venus",
                    "note": "Jupiter and Moon are neutral."},
    "Capricorn": {"yogkaraka": "Venus", "benefic": "Mercury", "malefic": "Moon, Mars, Jupiter", "maraka": "Mars",
                  "note": "Sun is neutral."},
    "Aquarius": {"yogkaraka": "Venus", "benefic": "Saturn", "malefic": "Moon, Mars, Jupiter", "maraka": "Jupiter",
                 "note": "Mercury is benefic if not afflicted."},
    "Pisces": {"yogkaraka": "—", "benefic": "Moon, Mars", "malefic": "Sun, Mercury, Venus", "maraka": "Mercury",
               "note": "Jupiter and Saturn are neutral."},
}

# ── Sign notes for lagna (OCR Gemini section + pillar traits for others) ───
D1_SIGN_PHYSICAL: dict[str, str] = {
    "Gemini": "Tall and well-formed body, usually above average height, long arms, clear speech, "
              "full face, curly hair, thick neck.",
    "Aries": "Medium height, bushy eyebrows, round eyes, lean muscular body, ruddy complexion, "
             "square face, long neck.",
    "Taurus": "Medium stature, well-developed neck and shoulders, strong build.",
}

D1_SIGN_MENTAL: dict[str, str] = {
    "Gemini": "Intellectual, restless, communicative — Mercury's sign. Health suffers through worry "
              "and anxiety if the mind is overworked.",
    "Aries": "Rash, combative, springy and hardy — Mars-ruled initiative.",
    "Taurus": "Determined, patient, strong retentive power — values stability.",
}

# ── Examination rules (pdf pages 47–48, Rules for Examination) ───────────
D1_EXAMINATION_RULES: list[str] = [
    "Read the birth chart first — divisional charts modify, they do not replace D1 promise.",
    "Raj yoga: connection between lords of kendras (1, 4, 7, 10) and trikonas (1, 5, 9) lifts status.",
    "Dhana yoga: exchange or mutual relation between lords of wealth houses (2, 11) and lagna/kendra/trikona.",
    "Khala yoga: 3rd lord exchanging with lagna or benefic-house lords can show sharp or contentious skill.",
    "Maha yoga: lagna lord exchanging with lords of 2, 4, 5, 7, 9, 10, or 11 expands life potential.",
    "A strong lagna and lagna lord are required before any house promise delivers fully.",
    "Planets in lagna colour the whole chart; afflicted lagna lord delays even good yogas.",
]

# ── General divisional inspection (Goel / Comprehensive Prediction, ch. General Rules) ──
GOEL_VARGA_INSPECTION_RULES: list[str] = [
    "Before reading any house, check: birth-chart lagna lord, divisional lagna lord, and karaka — all well placed in that varga.",
    "Best houses in a varga: kendra (1, 4, 7, 10) and trikona (5, 9); next best: 2 and 11.",
    "3rd, 6th, 8th, 12th in a varga are weak placements even when a planet is exalted (with stated exceptions).",
    "Karaka in divisional lagna is unfavourable; other planets in divisional lagna strengthen it.",
    "A strong divisional lagna is required for that varga's results to deliver fully (e.g. strong D7 lagna for progeny).",
    "Exceptions: Mars in 6th (any varga); Mercury in 8th (any varga); Mercury in 8th in D4.",
]

# ── Confluence cross-checks (other lanes — not the primary PDF) ───────────
D1_CONFLUENCE_LANES: list[tuple[str, str]] = [
    ("Lagna pillar", "Central life pillar — lagna + lagna lord strength (Pillar of Life method)."),
    ("Aṣṭakavarga SAV", "Bindu score on each house sign — quantitative support per bhava."),
    ("Vimśottarī Daśā", "Which houses and karakas the running MD/AD activate now."),
    ("Navāṁśa (D9) link", "D9 lagna / vargottama — inner strength backing the Rashi promise."),
    ("Jaimini kārakas", "Atmakaraka and chara kāraka roles in D1 houses."),
    ("KP cusp sub-lords", "Sub-lord on lagna and house cusps — event-level promise."),
    ("Chara / Yoginī Daśā", "Goel timing cross-check on house lords."),
]


def load_d1_ocr_text() -> str:
    if D1_OCR.is_file():
        return D1_OCR.read_text(encoding="utf-8", errors="ignore")
    return ""


def lagna_key_planet_row(lagna: str) -> dict[str, Any]:
    return D1_KEY_PLANETS.get(lagna, {"yogkaraka": "—", "benefic": "—", "malefic": "—", "maraka": "—", "note": ""})


def lagna_sign_reading(lagna: str) -> dict[str, str]:
    from vedic_pillar_report import LAGNA_TRAIT

    return {
        "trait": LAGNA_TRAIT.get(lagna, lagna),
        "physical": D1_SIGN_PHYSICAL.get(lagna, "See the rising sign's element and lord for build and complexion."),
        "mental": D1_SIGN_MENTAL.get(lagna, LAGNA_TRAIT.get(lagna, "")),
    }


# ═══════════════════════════════════════════════════════════════════════════
# D2 — Hora (Parashari Cancer / Leo), pdf pages 50–67 OCR
# ═══════════════════════════════════════════════════════════════════════════

D2_OCR = OCR_DIR / "D2_chapter_ocr.txt"

D2_INTRO = (
    "Hora (D2) is the primary wealth division. In Parashari hora only Cancer and Leo appear: "
    "Sun hora maps to Leo (wealth by self-effort, Devtas), Moon hora to Cancer (wealth through "
    "forefathers and blessings, Pitris). Odd signs — first 15° Sun hora, second 15° Moon hora; "
    "even signs reverse. Jupiter is karaka for family prosperity in hora analysis."
)

D2_HOUSE_SIGNIFICATIONS: dict[int, str] = {
    1: "General strength and nature to acquire wealth; overall financial constitution.",
    2: "Accumulated money, savings, family wealth, speech about money, food and taste.",
    3: "Courage and initiative in earning; trade skill and self-effort.",
    4: "Property, vehicles, comfort, happiness derived from wealth.",
    5: "Speculation, intelligence applied to money, poorva punya showing as financial luck.",
    6: "Debts, financial enemies, disease affecting earning capacity.",
    7: "Business partnerships, trade contracts, wealth through others.",
    8: "Inheritance, sudden financial rise or fall, obstacles to retained wealth.",
    9: "Fortune, father, dharma — ease of earning; strong 9th and lagna ease money flow.",
    10: "Status and profession as seen through the wealth lens.",
    11: "Gains, income streams, fulfilment of financial wishes.",
    12: "Expenditure, losses, charity; malefic 12th shows spend on illegitimate items.",
}

D2_EXAMINATION_RULES: list[str] = [
    "Analyse the hora chart independently for wealth — gains, losses, and source of money.",
    "Dhana yogas in D2 promote wealth and help retain it when placed in good houses.",
    "Strong D2 lagna and 9th house support easy earning; weak lagna needs hard work.",
    "2nd house shows eating/drinking habits tied to wealth; malefic influence on 2nd disturbs balance.",
    "12th house shows expenditure — malefic signs/planets/lords there spend on forbidden or wasteful items.",
    "Planets in Sun hora (Leo) earn through self-effort; Moon hora (Cancer) through ancestral blessing.",
    "Compare D1 and D2 — D1 promise must support what D2 refines on wealth.",
]

D2_MANSAGRI_HORA: dict[str, str] = {
    "Leo": "Sun hora (Leo): comforts and wealth acquired by own effort; dignified bearing; "
           "active earning capacity.",
    "Cancer": "Moon hora (Cancer): softer disposition; wealth through forefathers and family "
              "blessings; politeness in money matters when lagna or Moon occupy this hora.",
}

D2_CONFLUENCE_LANES: list[tuple[str, str]] = [
    ("D1 2nd & 11th houses", "Birth-chart wealth and gains houses — trunk promise for D2."),
    ("Lagna pillar", "Strong D1 lagna/lagna lord needed before D2 wealth delivers."),
    ("Vimśottarī Daśā", "2nd/11th lords and Jupiter periods activate hora themes."),
    ("Navāṁśa (D9)", "Inner strength of wealth lords — D9 of 2nd lord."),
    ("Aṣṭakavarga", "SAV on D1 houses 2, 11, 9 — quantitative wealth support."),
    ("KP cusp sub-lords", "2nd and 11th cusp sub-lords for event-level money promise."),
    ("Chara / Yoginī Daśā", "Goel timing on finance houses."),
]


def load_d2_ocr_text() -> str:
    if D2_OCR.is_file():
        return D2_OCR.read_text(encoding="utf-8", errors="ignore")
    return ""


# ═══════════════════════════════════════════════════════════════════════════
# D3 — Drekkana (Parashari), pdf pages 68–106 OCR
# ═══════════════════════════════════════════════════════════════════════════

D3_OCR = OCR_DIR / "D3_chapter_ocr.txt"

D3_INTRO = (
    "Drekkana (D3) divides each sign into three 10° segments. Parashari Drekkana — "
    "the first decanate stays in the same sign, the second shifts to the 5th from it, "
    "the third to the 9th — giving a chart wholly in the same trine element. "
    "D3 governs: co-born (siblings), personal inclinations and nature (Satwik/Rajsik/Tamsik), "
    "karma and its fruits (vs D10 which shows the action itself), courage, initiative, "
    "and communication. Lagna is ātma, 5th is jīvātma, 9th is paramātma — when these "
    "connect in D3 the life is happy. The 22nd Drekkana (8th house, degrees of lagna) "
    "is an important malefic marker for longevity stress."
)

D3_HOUSE_SIGNIFICATIONS: dict[int, str] = {
    1:  "Body, self, overall nature and inclinations; ātma (soul). Strong lagna promises siblings.",
    2:  "Accumulated resources from effort; family communication.",
    3:  "Immediate younger co-born; courage, initiative, short journeys; self-effort karma.",
    4:  "Happiness of and from co-born; emotional foundation of actions.",
    5:  "Planning and thinking toward co-born; second younger sibling; jīvātma.",
    6:  "Hindrances in getting fruits of karma; obstacles, enemies in effort.",
    7:  "Sexual inclinations and desires; partnerships formed through initiative.",
    8:  "Longevity; Khara (22nd drekkana); obstacles to fulfilment; transformation.",
    9:  "Luck factor in accomplishing goals; paramātma; elder siblings; fortune.",
    10: "Action undertaken to achieve desires; profession seen through karma lens.",
    11: "Fulfilment, getting desired objects; elder co-born; gains from effort.",
    12: "Loss of action; losses and separation from co-born; end of karma cycle.",
}

D3_EXAMINATION_RULES: list[str] = [
    "D3 shows the fruits of karma; D10 shows the karma action itself — read together.",
    "Lagna is ātma, 5th is jīvātma, 9th is paramātma; their connection = a happy life.",
    "Planets involved with the 3rd house or 3rd lord show failure or success in activity.",
    "A planet aspected by its D3 sign lord in D1 is powerful and gives auspicious results.",
    "22nd Drekkana (sign of D1 8th house, same degree as lagna) is the Kharesh — a malefic marker.",
    "Lagna lord, 8th lord, or Saturn in Kharesh/serpent drekkana can indicate severe obstacles.",
    "Strong D3 lagna promises siblings; afflicted lagna or 3rd lord denies younger co-born.",
    "Dhana yoga in D3 indicates many co-born; Raj yoga indicates highly-placed siblings.",
    "Laxmi drekkana (female decanates) for lagna/planets = wealth, pleasing personality, high society.",
    "3rd house should have malefics for true courage; benefics soften initiative.",
]

D3_NATURE_GUNA: dict[str, str] = {
    "movable_first":  "Narad drekkana — fond of travel, communicative, messenger-type; Satwik quality.",
    "movable_second": "Middle drekkana of movable — Rajsik quality; active, driven.",
    "movable_third":  "Third decanate of movable — Tamsik quality.",
    "fixed_first":    "First decanate of fixed — Satwik, stable, principled.",
    "fixed_second":   "Second decanate of fixed — Rajsik.",
    "fixed_third":    "Third decanate of fixed — Tamsik; likes to remain at one place, enemy of traditions.",
    "dual_first":     "First decanate of dual (mutable) — Satwik.",
    "dual_second":    "Second decanate of dual — Rajsik.",
    "dual_third":     "Third decanate of dual — Tamsik.",
}

D3_CONFLUENCE_LANES: list[tuple[str, str]] = [
    ("D1 3rd house", "Siblings, courage and initiative from the birth chart — trunk promise."),
    ("D1 11th house", "Elder co-born and gains from D1 — elder sibling theme."),
    ("Lagna pillar", "Strong D3 lagna needed for all D3 promises to deliver."),
    ("Vimśottarī Daśā", "3rd/11th lords and Mars periods activate D3 themes."),
    ("Aṣṭakavarga", "SAV on D1 house 3 — sibling and courage strength."),
    ("KP cusp sub-lords", "3rd cusp sub-lord for co-born promise."),
    ("Chara / Yoginī Daśā", "Goel timing on 3rd / courage themes."),
]


def load_d3_ocr_text() -> str:
    if D3_OCR.is_file():
        return D3_OCR.read_text(encoding="utf-8", errors="ignore")
    return ""


# ═══════════════════════════════════════════════════════════════════════════
# D4 — Chaturthamsha (Parashari), pdf pages 97–106 OCR (+ examples to 145)
# ═══════════════════════════════════════════════════════════════════════════

D4_OCR = OCR_DIR / "D4_chapter_ocr.txt"

D4_INTRO = (
    "Chaturthamsha (D4) — also called Turyamsha or Padamamsha — divides each sign into four "
    "parts of 7°30′ each. Parashari rule: 1st part stays in the same sign, 2nd moves to the 4th "
    "from it, 3rd to the 7th, 4th to the 10th. D4 is the chart of destiny, fixed and movable "
    "property, home, mother, contentment, and happiness derived from wealth. The four parts are "
    "ruled by Sanaka, Sananda, Sanatana Kumar, and Sanatana — governing how enduring your "
    "happiness is and whether it comes easily or after struggle."
)

D4_HOUSE_SIGNIFICATIONS: dict[int, str] = {
    1:  "Self, constitution, and overall capacity for happiness and property ownership.",
    2:  "Wealth accumulated for comfort; family speech; food and domestic resources.",
    3:  "Courage in property matters; siblings' share; short moves related to home.",
    4:  "Mother, home, land, immovable property, vehicles, inner peace — the core D4 house.",
    5:  "Pleasures from property; children; creative enjoyment of what you own.",
    6:  "Obstacles to happiness; debts on property; disputes over land or home.",
    7:  "Spouse's role in property; partnerships in land and domestic life.",
    8:  "Sudden changes to property; inheritance stress; longevity of home happiness.",
    9:  "Fortune in property; father; dharma; change of residence; foreign settlement.",
    10: "Career linked to property; government land; Mars here strongly grants fixed assets.",
    11: "Gains from property; elder siblings' share; fulfilment of domestic wishes.",
    12: "Loss of property; expenditure on home; exile from birthplace; foreign residence.",
}

D4_EXAMINATION_RULES: list[str] = [
    "D4 is read for all types of wealth, fate, destiny, and happiness through property.",
    "Jupiter is karaka for happiness; Mars for built-up fixed assets; Venus for mother and comfort.",
    "Relation of D1 2nd and 11th lords with Jupiter in D4 assures wealth-linked happiness.",
    "Dhana yoga in D4 promotes wealth and happiness; Raj yoga gives enjoyment of property.",
    "Strong Mars is essential for owning land/buildings; Mars in D4 10th is best for fixed assets.",
    "4th lord in upachaya houses (3,6,10,11) can give multiple properties over life.",
    "4th lord debilitated or in trik houses (6,8,12) indicates property loss or instability.",
    "Malefics in D4 lagna with Moon in 4th and malefics in 11th can break family continuity.",
    "9th lord in trik houses or afflicted 9th — displacement from birthplace or settlement abroad.",
    "Happiness is not only property — it can flow from passion, children, or spiritual contentment.",
]

D4_PART_DEITY: dict[int, str] = {
    1: "Sanaka — happiness pursued through unconventional or eccentric paths.",
    2: "Sananda — joy through delight, pleasure, and creative enjoyment.",
    3: "Sanatana Kumar — happiness tested, lost, and regained through effort.",
    4: "Sanatana — permanent, enduring happiness that stays through life.",
}

D4_CONFLUENCE_LANES: list[tuple[str, str]] = [
    ("D1 4th house", "Mother, home and property promise from the birth chart — trunk for D4."),
    ("D1 2nd & 11th houses", "Wealth and gains houses linking to Jupiter in D4 for happiness."),
    ("Lagna pillar", "Strong D1 lagna needed before D4 property promises deliver."),
    ("Vimśottarī Daśā", "4th lord, Moon, Venus, Mars periods activate D4 themes."),
    ("Aṣṭakavarga", "SAV on D1 house 4 — home and property strength."),
    ("KP cusp sub-lords", "4th cusp sub-lord for property and mother events."),
    ("Chara / Yoginī Daśā", "Goel timing on 4th / home themes."),
]


def load_d4_ocr_text() -> str:
    if D4_OCR.is_file():
        return D4_OCR.read_text(encoding="utf-8", errors="ignore")
    return ""


# ═══════════════════════════════════════════════════════════════════════════
# D7 — Saptamsha (Parashari), pdf pages 112–126 within D4 OCR file
# ═══════════════════════════════════════════════════════════════════════════

D7_INTRO = (
    "Saptamsha (D7) divides each sign into seven parts of 4°17′ each. Parashari rule: "
    "for odd signs the 1st part starts from the sign itself, counting forward; for even signs "
    "the 1st part starts from the 7th sign, counting forward. D7 is the primary chart for "
    "children, progeny, and future lineage. It shows the capacity to conceive, the number and "
    "nature of children, and the continuation or end of the family line. Jupiter is the karaka "
    "for children; the 5th house of D7 is the most critical. The seven Saptamsha lords are "
    "named: Kshar, Kshira, Dadhi, Ajyam, Ikshu, Madhya, Suddha Jal — indicating the quality "
    "of the path of life for the children born in each part."
)

D7_HOUSE_SIGNIFICATIONS: dict[int, str] = {
    1:  "Constitution and overall capacity for progeny; the native as a parent.",
    2:  "Wealth and speech of children; family's financial continuation through progeny.",
    3:  "Courage and initiative of children; their siblings and communication.",
    4:  "Happiness, education, and emotional security of children; the mother's role.",
    5:  "Primary house for children — their birth, nature, and bond with the parent.",
    6:  "Obstacles to conceiving; health challenges of children; their rivals and debts.",
    7:  "Marriage prospects of children; children from second marriage.",
    8:  "Longevity of children; sudden changes; hidden challenges in progeny matters.",
    9:  "Grandchildren; luck and fortune of children; dharma passed to the next generation.",
    10: "Children's career and public standing; the legacy they carry forward.",
    11: "Fulfilment of progeny wishes; gains and success of children.",
    12: "Loss, separation from children; children settled abroad; spiritual liberation through lineage.",
}

D7_SAPTAMSHA_LORDS: dict[str, str] = {
    "Kshar":      "Kshar — the ordinary, material path; worldly and practical nature.",
    "Kshira":     "Kshira (milk) — nourishing, gentle, and caring nature.",
    "Dadhi":      "Dadhi (curd) — steadiness in effort; persevering nature.",
    "Ajyam":      "Ajyam (ghee) — fruitful and refined; productive realisation.",
    "Ikshu":      "Ikshu (sugarcane) — enjoyment and sweetness; pleasure-seeking.",
    "Madhya":     "Madhya (wine) — intoxicating bliss; intense experiences.",
    "Suddha Jal": "Suddha Jal (pure water) — the ever-blissful, spiritually clear stage.",
}

D7_EXAMINATION_RULES: list[str] = [
    "Strong D7 lagna assures progeny; its lord well-placed gives healthy children.",
    "Jupiter is the karaka for children; its placement in D7 (especially 1st, 5th, 9th) is critical.",
    "5th house and 5th lord of D7 are the primary indicators for birth of children.",
    "Afflicted 5th house by malefics or 6th/8th/12th lord can deny or delay children.",
    "9th house in D7 shows grandchildren and the fortune carried by children.",
    "Saptamsha shows future lineage; Dwadamsha (D12) shows past lineage (parents).",
    "Children from second marriage are seen from the 7th house of D7.",
    "Multiple benefics in D7 lagna or 5th house indicate many children.",
    "A debilitated planet in D7 indicates that theme will require effort but eventually rises.",
    "Mars and Moon of the child must connect with 5th or 9th house/lord of parent's D7 for genetic link.",
]

D7_CONFLUENCE_LANES: list[tuple[str, str]] = [
    ("D1 5th house", "Children promise from the birth chart — the trunk of D7."),
    ("D1 9th house", "Fortune and dharma — supports children and grandchildren."),
    ("Lagna pillar", "Strong D1 lagna needed before D7 children promises deliver."),
    ("Vimśottarī Daśā", "5th lord, Jupiter, Moon periods activate D7 themes."),
    ("Aṣṭakavarga", "SAV on D1 house 5 — quantitative children strength."),
    ("KP cusp sub-lords", "5th cusp sub-lord for children event promise."),
    ("Chara / Yoginī Daśā", "Goel timing on 5th / children themes."),
]


def load_d7_ocr_text() -> str:
    d7_ocr = OCR_DIR / "D4_chapter_ocr.txt"
    if d7_ocr.is_file():
        return d7_ocr.read_text(encoding="utf-8", errors="ignore")
    return ""


# ═══════════════════════════════════════════════════════════════════════════
# D9 — Navamsha (Parashari), pdf pages 127–145 in divisional_chart-tillD10 OCR
# ═══════════════════════════════════════════════════════════════════════════

D9_OCR = OCR_DIR / "D4_chapter_ocr.txt"

D9_INTRO = (
    "Navamsha (D9) divides each sign into nine parts of 3°20′ each. Parashari rule: "
    "for movable signs the first navamsha starts in the same sign; for fixed signs in the "
    "9th sign; for dual signs in the 5th sign — then counting forward in order. "
    "D9 is the primary chart for marriage, spouse, and how the birth-chart promise matures "
    "over time — especially the second half of life. A planet strong in D1 but weak in D9 "
    "may disappoint early; weak in D1 but strong in D9 often improves with age. "
    "Vargottama (same sign in D1 and D9) strengthens the theme. Pushkar navamsha padas "
    "enhance benefic results; vish navamsha padas need caution in their dasha periods."
)

D9_HOUSE_SIGNIFICATIONS: dict[int, str] = {
    1:  "Lagnamsha — inner self in partnership; constitution for marriage.",
    2:  "Vittamsha — wealth, family speech, and values in the union.",
    3:  "Vikramsha — courage, initiative, and communication in marriage.",
    4:  "Sukhamsha — marital happiness, home peace, and emotional comfort.",
    5:  "Putramsha — romance, children after marriage, and creative bond.",
    6:  "Shastamsha — obstacles, health rivals, and daily stress on marriage.",
    7:  "Bharyamsha — spouse, marriage itself, and partnership quality.",
    8:  "Nidhanamsha — mangalya, longevity, inheritance, and hidden marital themes.",
    9:  "Bhagyamsha — fortune through spouse, dharma, and spiritual path in union.",
    10: "Karmamsha — spouse's career, couple's public image, and karma through marriage.",
    11: "Labhamsha — gains and fulfilment of wishes through partnership.",
    12: "Vyamsha — bed pleasure, foreign spouse, expenses, and moksha in marriage.",
}

D9_EXAMINATION_RULES: list[str] = [
    "Strong D9 lagna and lagna lord are required before marriage promise delivers fully.",
    "D9 7th house and 7th lord are primary for spouse and marriage quality.",
    "Venus (marriage karaka for males) and Jupiter (for females) must be well placed in D9 — not in D9 lagna alone.",
    "Benefics on D9 7th enhance marriage; malefics without relief strain partnership.",
    "D9 4th house shows marital happiness and home peace after wedding.",
    "D9 8th house is studied for mangalya and longevity themes — confluence only, not alarm alone.",
    "Vargottama planets and lagna strengthen results; pushkar navamsha enhances the planet's signification.",
    "Planet debilitated in D1 but exalted in D9 — results improve in second half of life.",
    "Three afflictions on 7th in both D1 and D9 with no benefic relief can deny or severely strain marriage.",
    "Venus in D9 12th is a classical favourable exception for marital comfort.",
]

D9_CONFLUENCE_LANES: list[tuple[str, str]] = [
    ("D1 7th house", "Marriage trunk promise from birth chart — read with D9 7th."),
    ("D1 Venus / Jupiter", "Marriage karaka dignity in D1 vs D9 — long-term tone."),
    ("Lagna pillar", "Strong D1 lagna needed before D9 marriage fruits deliver."),
    ("Vimśottarī Daśā", "7th lord, Venus, Jupiter, D9 lagna lord periods activate marriage."),
    ("Aṣṭakavarga", "SAV on D1 house 7 — quantitative marriage support."),
    ("KP cusp sub-lords", "7th cusp sub-lord for marriage event timing."),
    ("Darakaraka / Jaimini", "DK and chara karakas for spouse significator cross-check."),
]


def load_d9_ocr_text() -> str:
    if D9_OCR.is_file():
        return D9_OCR.read_text(encoding="utf-8", errors="ignore")
    return ""


# ─────────────────────────────────────────────────────────────────────────
# Higher divisional charts (D10–D60) — canonical Shodasavarga significations.
# Source themes: Comprehensive Prediction by Divisional Charts (D10–D60 OCR)
# and standard Parashari Shodasavarga. Each chart re-reads the 12 houses
# through its own theme. Used by the data-driven generic report generator.
# ─────────────────────────────────────────────────────────────────────────
HIGHER_VARGA_CORPUS: dict[str, dict[str, Any]] = {
    "D5": {
        "factor": 5, "title": "Panchamsha Chart (D5)", "tag": "Panchamsha",
        "subtitle": "Spiritual inclination, worship & chosen deity (viveka)",
        "theme": "faith, worship and spiritual discernment",
        "karaka": "Jupiter", "karaka_topic": "faith and worship",
        "signature_house": 9, "key_houses": [1, 5, 9, 12],
        "intro": (
            "Panchamsha (D5) divides each sign into five parts of 6° each — the chart "
            "of faith, worship and viveka (the power of discernment). It shows your "
            "natural pull toward the divine, the style of worship that suits you "
            "(devotional, ritual, tantric or knowledge-based), the form of deity you "
            "relate to (ishta), and how steady the spiritual life becomes. A strong "
            "lagna gives a balanced mind and genuine inclination; the 5th, 9th and 12th "
            "and Jupiter/Ketu are read closely."
        ),
        "house_sigs": {
            1: "Your spiritual temperament — how naturally faith and discernment come to you.",
            2: "Mantra, chanting, scripture, and the faith spoken and held in the family.",
            3: "Effort in worship, short pilgrimage, devotional singing, and initiative in practice.",
            4: "Inner peace from faith, a home shrine, and emotional grounding in worship.",
            5: "Mantra-merit, past-life devotion (purva punya), and worship from the heart.",
            6: "Obstacles on the spiritual path and the discipline that overcomes them.",
            7: "Worship in a group (satsang), the deity you relate to, and shared practice.",
            8: "Occult and transformative practice, hidden worship, and tantric leanings.",
            9: "Guru, dharma, the chosen deity, and the strongest house of faith and grace.",
            10: "The standing and depth of your worship, and devotion expressed in the world.",
            11: "Gains desired from worship, spiritual community, and fulfilment through grace.",
            12: "Distraction or loss of interest, but also surrender, meditation and moksha.",
        },
        "rules": [
            "A strong, unafflicted D5 lagna is the pre-requisite for genuine faith and a balanced mind.",
            "Rahu/Ketu or Saturn with the D5 lagna lean the worship toward demigods or tantric ritual.",
            "Male signs/planets on the lagna point to a male deity; female signs/planets to a goddess.",
            "Jupiter and Ketu well placed (esp. 9th/12th) deepen devotion and discernment.",
            "When the significator planet repeats across lagna, 5th and 9th, the spiritual path is best.",
            "Vargottama planets strengthen the devotional themes they carry.",
        ],
    },
    "D6": {
        "factor": 6, "title": "Shashthamsha Chart (D6)", "tag": "Shashthamsha",
        "subtitle": "Health vulnerabilities, disease & enemies",
        "theme": "health, disease and enemies",
        "karaka": "Saturn", "karaka_topic": "disease and resilience",
        "signature_house": 6, "key_houses": [1, 6, 8],
        "intro": (
            "Shashthamsha (D6, also Shashtamsha) divides each sign into six parts of 5° "
            "each — the chart of health troubles, the onset of disease, and enemies. "
            "Where the saptavimshamsha (D27) shows the body's general strength and "
            "resistance, D6 shows when and how illness actually surfaces and who works "
            "against you. The lagna, 6th and 8th houses and their lords are central."
        ),
        "house_sigs": {
            1: "General proneness to disease and self-acquired health problems.",
            2: "Health of the face/throat, diet-related trouble, and disputes within family.",
            3: "Ailments of arms/chest, and rivalry or strain with co-borns.",
            4: "Chest and heart vulnerabilities, and trouble through home or vehicles.",
            5: "Stomach and digestive health, and worry over children's wellbeing.",
            6: "The core house — disease, debts, daily enemies; a benefic here is welcome.",
            7: "Health of the partner, ailments below the navel, and open opponents.",
            8: "Chronic and lingering illness, surgery, and the depth of a disease.",
            9: "Health linked to fortune and faith; relief or aggravation through luck.",
            10: "Work-related strain, and fame won by overcoming disease or enemies.",
            11: "Recovery and gains over illness, and the easing of enmity.",
            12: "Hospitalisation, expenses on treatment, and hidden or foreign ailments.",
        },
        "rules": [
            "A benefic on the D6 6th house or lagna safeguards against disease and enemies.",
            "Malefics in the 6th, the 6th lord in an angle, and PAC of malefics bring illness and rivals.",
            "A strong 6th house (11th from the 8th) lends longevity and a disease-free life.",
            "If the 10th lord of the birth chart relates to the 6th house/lord of D6, one earns fame in work.",
            "The relation of D1 lagna lord, D3 lagna lord and Ketu in D6 is read for the cure of disease.",
            "Vargottama planets reinforce the health themes — for good or ill — that they carry.",
        ],
    },
    "D8": {
        "factor": 8, "title": "Ashtamsha Chart (D8)", "tag": "Ashtamsha",
        "subtitle": "Sudden events, accidents, chronic illness & longevity",
        "theme": "sudden events, longevity and calamity",
        "karaka": "Saturn", "karaka_topic": "longevity and sudden events",
        "signature_house": 8, "key_houses": [1, 6, 8, 12],
        "intro": (
            "Ashtamsha (D8) divides each sign into eight parts of 3°45′ each — the chart "
            "of sudden and unexpected events, accidents, chronic disease, confinement "
            "and longevity. It is the fine lens on the 8th-house themes: how mishaps "
            "arrive, how the body withstands shock, and where life turns abruptly. The "
            "lagna, 8th house and their lords, with Saturn, Mars and the nodes, are key."
        ),
        "house_sigs": {
            1: "Resilience to shock — how the body and life withstand sudden blows.",
            2: "Sudden gains or losses of wealth, and abrupt shifts in family fortune.",
            3: "Accidents in travel, courage tested by crisis, and sudden initiative.",
            4: "Upheavals at home, property shocks, and disturbance of peace of mind.",
            5: "Sudden turns regarding children, speculation, and reversals of plans.",
            6: "Onset of disease, debts that surface suddenly, and conflict with enemies.",
            7: "Health and longevity of the spouse, and abrupt partnership events.",
            8: "The core house — chronic illness, surgery, claims, death and longevity.",
            9: "Sudden loss of money and reputation, and abrupt turns of fortune.",
            10: "Obstacles or harm to siblings, legacy gained, and the trend of events.",
            11: "Inheritance from mother, family disputes, and vehicular accidents.",
            12: "Confinement (hospital/prison), problems to children, and sudden speculative gains or career loss.",
        },
        "rules": [
            "A weak or afflicted D8 8th lord is a classical indication of a short or fragile life.",
            "Severe affliction of the D8 lagna/8th can mean a crippling chronic disease (e.g. cancer).",
            "Mars or the nodes with Ketu/Saturn on the 8th give serious physical accidents.",
            "An afflicted 12th lord of the birth chart, read in D8, shows confinement — hospital, prison or kidnapping.",
            "Benefics on the D8 lagna or 8th cushion sudden events and grant pleasant, gentler turns.",
            "Vargottama planets steady (or, if afflicted, deepen) the sudden-event themes they carry.",
        ],
    },
    "D10": {
        "factor": 10, "title": "Dashamsha Chart (D10)", "tag": "Dashamsha",
        "subtitle": "Career, profession, status & achievement",
        "theme": "career, profession and public standing",
        "karaka": "Sun", "karaka_topic": "career and status",
        "signature_house": 10, "key_houses": [1, 2, 7, 10, 11],
        "intro": (
            "Dashamsha (D10) divides each sign into ten parts of 3° each — the karma "
            "chart of meaningful work. The birth 10th house opens the story of "
            "profession; D10 confirms the kind of work, independence vs service, fame, "
            "rise and fall, and the timing of career turns. A strong D10 lagna, its "
            "lord, and the 10th house make a career promise actually deliver."
        ),
        "house_sigs": {
            1: "Your work identity — how you show up professionally and your drive to achieve.",
            2: "Earnings from work, professional speech, and the resources your career builds.",
            3: "Effort, initiative, short courses, and colleagues you work alongside.",
            4: "Workplace comfort, the organisation you belong to, and peace within the job.",
            5: "Skill, intelligence applied to work, advisory roles, and creative profession.",
            6: "Competition, service, daily duties, problem-solving, and workplace rivals.",
            7: "Business partnerships, dealings with the public, and clients or markets.",
            8: "Sudden changes, research, inheritance of position, and career upheavals.",
            9: "Luck in career, mentors and bosses, ethics at work, and long-distance work.",
            10: "The profession itself — status, authority, fame, and your karmic work.",
            11: "Gains, promotions, fulfilment of ambitions, and professional network.",
            12: "Foreign work, expenses for career, exit/retirement, and behind-scenes roles.",
        },
        "rules": [
            "A strong D10 lagna and lagna lord are needed before the career promise delivers.",
            "The D10 10th house and its lord show the actual profession and authority.",
            "Sun and Saturn (work, duty) and Mercury (skill) carry career — note their D10 dignity.",
            "Benefics on the D10 10th or 1st raise status; malefics without relief bring struggle and falls.",
            "Planets in upachaya houses (3, 6, 10, 11) of D10 grow stronger with time and effort.",
            "Vargottama planets and a vargottama lagna make the career line steady and reliable.",
        ],
    },
    "D11": {
        "factor": 11, "title": "Ekadashamsha Chart (D11)", "tag": "Ekadashamsha",
        "subtitle": "Gains, income & fulfilment of desires (Rudramsha/Labhamsha)",
        "theme": "gains, income and fulfilment of desires",
        "karaka": "Jupiter", "karaka_topic": "expansion and gains",
        "signature_house": 11, "key_houses": [1, 2, 5, 9, 10, 11],
        "intro": (
            "Ekadashamsha (D11, also Rudramsha or Labhamsha) divides each sign into "
            "eleven parts of 2°43′38″ — the chart of gains, income and the fulfilment "
            "of desires. Where the 11th house of the birth chart opens the theme of "
            "profit, D11 fine-tunes the source, scale and steadiness of what flows in. "
            "A strong Jupiter (expansion), the 11th house/lord and any Dhana yoga are key."
        ),
        "house_sigs": {
            1: "Personal gains and losses of every kind, and your own drive to acquire.",
            2: "Gains through speech, family wealth, and resources you accumulate.",
            3: "Gains through communication, writing, effort and short ventures.",
            4: "Gains from property, vehicles and home comforts, and the joy or strain from them.",
            5: "Gains through children, speculation, investments and creative intelligence.",
            6: "Gains through service, competition, loans and resolving disputes.",
            7: "Gains from spouse or the public at large; income that grows after marriage.",
            8: "Gains through inheritance, inventions, insurance, and unexpected sources.",
            9: "Gains through father, fortune, religion or guru; income blessed by luck.",
            10: "Gains from authority and profession — reward (and sometimes penalty) from the 'king'.",
            11: "Gains of all types, from any source — the core house of fulfilled desires.",
            12: "Gains from abroad, foreign sources and luxury, but also the outflow of money.",
        },
        "rules": [
            "A well-placed, strong Jupiter (significator of expansion) is essential for steady gains.",
            "A Dhana yoga together with a strong D11 lagna ensures an inflow of all kinds of wealth.",
            "The Indu Lagna of the birth chart, taken as the D11 lagna, is read for the wealth picture.",
            "The placement and lordship of the 11th lord in D11 reveal the main source of income.",
            "Benefics on the D11 1st/2nd/11th strengthen and steady the flow of gains.",
            "Vargottama planets reinforce the gain-themes they carry.",
        ],
    },
    "D12": {
        "factor": 12, "title": "Dwadashamsha Chart (D12)", "tag": "Dwadashamsha",
        "subtitle": "Parents, ancestry & inherited karma",
        "theme": "parents, ancestry and inherited blessings",
        "karaka": "Sun", "karaka_topic": "parents and lineage",
        "signature_house": 4, "key_houses": [1, 4, 5, 9],
        "intro": (
            "Dwadashamsha (D12) divides each sign into twelve parts of 2°30′ — the chart "
            "of parents and ancestry. It shows the well-being of mother and father, what "
            "you inherit from them in body, fortune and karma, and the quality of your "
            "early roots. The 4th (mother) and 9th (father) axis is read closely."
        ),
        "house_sigs": {
            1: "What you carry forward from your bloodline — inherited constitution and traits.",
            2: "Family wealth handed down, ancestral values, and what the lineage preserves.",
            3: "Siblings of parents (uncles/aunts) and the courage inherited from family.",
            4: "Mother — her well-being, your bond, and emotional roots from the home.",
            5: "Inherited intelligence, ancestral merit (purva punya), and family creativity.",
            6: "Family debts and disputes, inherited health tendencies, and ancestral strain.",
            7: "Grandparents and the partnerships/agreements that shape the wider family.",
            8: "Inheritance, ancestral secrets, longevity patterns, and karmic baggage.",
            9: "Father — his fortune, your bond, and the dharma and luck passed down.",
            10: "The family's standing, parents' work, and the reputation you inherit.",
            11: "Gains through family, elder relatives, and fulfilment of ancestral hopes.",
            12: "Ancestral losses, family abroad, and the spiritual debts of the lineage.",
        },
        "rules": [
            "A strong D12 lagna and lagna lord show a sound inheritance of body and fortune.",
            "The 4th house/lord and Moon read the mother; the 9th house/lord and Sun read the father.",
            "Benefics on the parental axis (4th/9th) protect parents and ease the bond.",
            "Malefics afflicting the 4th or 9th can mean early separation or strain with a parent.",
            "Vargottama planets reinforce strong inherited karma in their significations.",
        ],
    },
    "D16": {
        "factor": 16, "title": "Shodashamsha Chart (D16)", "tag": "Shodashamsha",
        "subtitle": "Vehicles, luxuries, comforts & happiness from them",
        "theme": "vehicles, comforts and material happiness",
        "karaka": "Venus", "karaka_topic": "vehicles and comforts",
        "signature_house": 4, "key_houses": [1, 4, 11, 12],
        "intro": (
            "Shodashamsha (D16, also Kalamsha) divides each sign into sixteen parts of "
            "1°52′30″ — the chart of conveyances, luxuries and the comforts of life, and "
            "the happiness or trouble you get from them. The 4th house (vehicles, "
            "comfort) and Venus are central."
        ),
        "house_sigs": {
            1: "Your appetite for comfort and how luxuries shape your lifestyle.",
            2: "Money spent and saved on comforts, and possessions that hold value.",
            3: "Short travels, two-wheelers, gadgets, and everyday conveniences.",
            4: "The main seat — vehicles, home comforts, and overall material happiness.",
            5: "Pleasures, entertainment, and the joy you take from luxuries.",
            6: "Repairs, loans for vehicles/assets, and troubles arising from possessions.",
            7: "Comforts shared with a partner and luxury through business or marriage.",
            8: "Sudden loss or accidents involving vehicles; insurance and hidden costs.",
            9: "Long journeys, fortunate acquisitions, and comfort through good luck.",
            10: "Status symbols, prestige vehicles, and comfort tied to your standing.",
            11: "Acquisition of vehicles and luxuries, and fulfilment of material wishes.",
            12: "Expenses on comforts, foreign vehicles, and letting go of possessions.",
        },
        "rules": [
            "A strong D16 lagna and 4th house show steady comfort and good conveyances.",
            "Venus (luxury) and the 4th lord well placed bring easy enjoyment of comforts.",
            "Malefics on the 4th/12th can mean vehicle trouble, accidents, or comfort that drains money.",
            "Benefics in the 4th or 11th confirm pleasant acquisitions with little stress.",
            "Vargottama planets steady the comforts they signify.",
        ],
    },
    "D20": {
        "factor": 20, "title": "Vimshamsha Chart (D20)", "tag": "Vimshamsha",
        "subtitle": "Devotion, worship & spiritual progress",
        "theme": "devotion and spiritual progress",
        "karaka": "Jupiter", "karaka_topic": "devotion and wisdom",
        "signature_house": 9, "key_houses": [1, 5, 9, 12],
        "intro": (
            "Vimshamsha (D20) divides each sign into twenty parts of 1°30′ — the chart of "
            "spiritual progress, worship and devotion. It shows your inner inclination "
            "toward the divine, the form of practice that suits you, and how far the "
            "spiritual path matures. The 5th, 9th and 12th and Jupiter/Ketu are key."
        ),
        "house_sigs": {
            1: "Your spiritual temperament and how naturally devotion comes to you.",
            2: "Mantra, chanting, scripture, and the faith spoken in the family.",
            3: "Effort in practice, pilgrimage on foot, and courage in spiritual matters.",
            4: "Inner peace from devotion, a home altar, and emotional grounding in faith.",
            5: "Mantra-siddhi, past-life merit, devotion from the heart, and a guru's grace.",
            6: "Discipline and obstacles on the path; conquering inner enemies through practice.",
            7: "Worship with a partner, the deity you relate to, and public spiritual life.",
            8: "Occult, kundalini, transformative practices, and hidden spiritual research.",
            9: "Guru, dharma, higher worship, and the strongest house of devotion.",
            10: "Spiritual work in the world, teaching, and dharma expressed publicly.",
            11: "Spiritual community, fulfilment through practice, and gains of grace.",
            12: "Meditation, moksha, retreat, and surrender — the liberation house.",
        },
        "rules": [
            "A strong D20 lagna and 9th house show genuine, maturing devotion.",
            "Jupiter (wisdom) and Ketu (moksha) well placed deepen spiritual progress.",
            "Benefics in the 5th, 9th or 12th of D20 bless practice with grace and steadiness.",
            "A weak or afflicted 9th can mean inconsistent faith or a late spiritual turn.",
            "Vargottama planets strengthen the devotional themes they carry.",
        ],
    },
    "D24": {
        "factor": 24, "title": "Chaturvimshamsha Chart (D24)", "tag": "Chaturvimshamsha",
        "subtitle": "Education, learning & academic success",
        "theme": "education and learning",
        "karaka": "Mercury", "karaka_topic": "learning and intellect",
        "signature_house": 4, "key_houses": [1, 2, 4, 5, 9],
        "intro": (
            "Chaturvimshamsha (D24, also Siddhamsha) divides each sign into twenty-four "
            "parts of 1°15′ — the chart of education and learning. It shows academic "
            "aptitude, the subjects that come easily, success in exams, and lifelong "
            "ability to learn. Mercury, the 4th and 5th houses, and Jupiter are key."
        ),
        "house_sigs": {
            1: "Your natural intelligence and how readily you take to study.",
            2: "Memory, accumulated knowledge, and learning that earns a living.",
            3: "Skill-learning, writing, hands-on training, and curiosity.",
            4: "Formal education, schooling, degrees, and the comfort of a learning base.",
            5: "Sharp intellect, higher reasoning, competitive exams, and brilliance.",
            6: "Effort against difficulty in study, competitive struggle, and discipline.",
            7: "Learning with peers, partnerships in study, and knowledge shared publicly.",
            8: "Research, deep or occult knowledge, and breakthroughs after struggle.",
            9: "Higher education, wisdom, teachers, and learning that shapes your philosophy.",
            10: "Knowledge applied to career, qualifications, and academic reputation.",
            11: "Gains from education, fulfilment of academic goals, and learned circles.",
            12: "Study abroad, secluded research, and knowledge that turns inward.",
        },
        "rules": [
            "A strong D24 lagna and 4th/5th houses show steady educational success.",
            "Mercury (intellect) and Jupiter (wisdom) well placed sharpen learning.",
            "Benefics in the 4th, 5th or 9th of D24 support degrees and higher study.",
            "Malefics afflicting the 4th/5th can mean interrupted study or exam stress.",
            "Vargottama Mercury or Jupiter is a strong sign of lasting intellectual ability.",
        ],
    },
    "D27": {
        "factor": 27, "title": "Bhamsha Chart (D27)", "tag": "Bhamsha",
        "subtitle": "Physical & mental strength, stamina, resilience",
        "theme": "strength, stamina and resilience",
        "karaka": "Mars", "karaka_topic": "strength and stamina",
        "signature_house": 1, "key_houses": [1, 3, 6, 8],
        "intro": (
            "Bhamsha (D27, also Nakshatramsha) divides each sign into twenty-seven parts "
            "of 1°6′40″ — the chart of underlying strengths and weaknesses, physical and "
            "mental stamina, and the resilience behind everything else. It shows where "
            "you are robust and where you tire or break under pressure."
        ),
        "house_sigs": {
            1: "Core vitality — your overall physical and mental robustness.",
            2: "Stamina behind family and finances; endurance in sustaining resources.",
            3: "Raw courage, willpower, and the strength to keep initiating.",
            4: "Emotional steadiness and the inner reserves that keep you calm.",
            5: "Mental sharpness under load and the strength of your judgement.",
            6: "Power to fight illness and adversity — immunity and stress tolerance.",
            7: "Strength in relationships and the stamina to sustain partnerships.",
            8: "Recuperative power, crisis endurance, and deep reserves of resilience.",
            9: "Strength of conviction, fortune's backing, and moral fortitude.",
            10: "Capacity for sustained effort in work and carrying responsibility.",
            11: "Endurance in pursuing goals and the strength of your support network.",
            12: "Hidden drains on energy and where rest and recovery are needed.",
        },
        "rules": [
            "A strong D27 lagna and lagna lord show robust constitution and stamina.",
            "Mars (physical strength) and the Sun (vitality) well placed confirm resilience.",
            "Malefics clustered in 6/8/12 of D27 point to where energy is drained or tested.",
            "Benefics on the 1st protect vitality and steady the mind under pressure.",
            "Vargottama planets mark genuinely durable strengths in their significations.",
        ],
    },
    "D30": {
        "factor": 30, "title": "Trimshamsha Chart (D30)", "tag": "Trimshamsha",
        "subtitle": "Misfortunes, evils, health & character tests",
        "theme": "misfortunes, health and inner character",
        "karaka": "Saturn", "karaka_topic": "protection from misfortune",
        "signature_house": 6, "key_houses": [1, 6, 8, 12],
        "intro": (
            "Trimshamsha (D30) divides each sign into thirty parts — the chart of "
            "misfortunes, evils, diseases and character tests. Read carefully and never "
            "alarmingly, it shows where vulnerabilities sit — health, habits, and moral "
            "trials — so they can be managed early. Malefic rulerships (Mars, Saturn, "
            "Rahu) are weighed against benefic relief."
        ),
        "house_sigs": {
            1: "Constitutional weak points and the temperament that invites trouble.",
            2: "Risks to wealth and speech, and habits that can erode resources.",
            3: "Rash impulses, conflicts, and the courage that can turn reckless.",
            4: "Emotional unrest, troubles at home, and threats to peace of mind.",
            5: "Mental strain, risks to children or romance, and errors of judgement.",
            6: "Disease, debts, enemies, and the daily battles of body and circumstance.",
            7: "Strain in partnership, disputes, and trouble through others.",
            8: "Chronic ailments, accidents, crises, and the deepest tests of endurance.",
            9: "Tests of faith, setbacks in fortune, and moral or ethical trials.",
            10: "Obstacles in work, loss of reputation, and stress from responsibility.",
            11: "Disappointed hopes, bad company, and gains that come with strain.",
            12: "Hidden losses, sleep and mental troubles, and self-undoing tendencies.",
        },
        "rules": [
            "A strong D30 lagna and lagna lord give resilience that contains misfortune.",
            "Benefic (Mercury, Jupiter, Venus) trimshamsha rulerships soften the house's troubles.",
            "Malefic (Mars, Saturn) rulerships and afflictions mark where care and remedy matter most.",
            "The 6th, 8th and 12th of D30 are read for health and crisis — as study, not alarm.",
            "Benefic relief on a stressed house shows the trouble is manageable with effort.",
        ],
    },
    "D40": {
        "factor": 40, "title": "Khavedamsha Chart (D40)", "tag": "Khavedamsha",
        "subtitle": "Maternal legacy; auspicious & inauspicious effects",
        "theme": "maternal legacy and life's auspicious effects",
        "karaka": "Moon", "karaka_topic": "maternal blessings",
        "signature_house": 4, "key_houses": [1, 4, 9],
        "intro": (
            "Khavedamsha (D40, also Swavedamsha) divides each sign into forty parts — the "
            "chart of effects inherited through the maternal line, and the broad "
            "auspicious or inauspicious tone of life events. The Moon and the 4th house "
            "are central; it fine-tunes blessings carried from the mother's side."
        ),
        "house_sigs": {
            1: "What you carry from the maternal line in body and temperament.",
            2: "Maternal family values, and resources or speech inherited from that side.",
            3: "Courage and kin from the mother's family.",
            4: "Mother's blessings, emotional inheritance, and auspicious home foundations.",
            5: "Inherited merit and creativity from the maternal line.",
            6: "Inherited health tendencies and disputes from the mother's side.",
            7: "Maternal influence on partnerships and family alliances.",
            8: "Maternal inheritance, longevity patterns, and hidden family karma.",
            9: "Fortune and dharma blessed through the maternal line.",
            10: "Standing and conduct shaped by maternal upbringing.",
            11: "Gains and fulfilment through the mother's family and elders.",
            12: "Losses, distance, or spiritual debts carried from that lineage.",
        },
        "rules": [
            "A strong D40 lagna and 4th house show rich maternal blessings.",
            "The Moon and 4th lord well placed confirm auspicious effects through the mother's line.",
            "Benefics on the 4th or 9th broadly tilt life toward auspicious outcomes.",
            "Malefic affliction of the 4th can mean strain or loss tied to the maternal side.",
            "Vargottama planets reinforce the inherited blessings they signify.",
        ],
    },
    "D45": {
        "factor": 45, "title": "Akshavedamsha Chart (D45)", "tag": "Akshavedamsha",
        "subtitle": "Paternal legacy, character & overall conduct",
        "theme": "paternal legacy, character and conduct",
        "karaka": "Sun", "karaka_topic": "paternal blessings and character",
        "signature_house": 9, "key_houses": [1, 9, 10],
        "intro": (
            "Akshavedamsha (D45) divides each sign into forty-five parts — the chart of "
            "the paternal line, your essential character and conduct, and the moral grain "
            "of the personality. The Sun and the 9th house are central; it fine-tunes the "
            "dignity and values carried from the father's side."
        ),
        "house_sigs": {
            1: "Your essential character and the conduct you inherit from the paternal line.",
            2: "Family values, integrity in speech, and resources from the father's side.",
            3: "Willpower and the ethical courage passed down.",
            4: "Inner conscience and the moral grounding of the personality.",
            5: "Inherited wisdom, judgement, and the ethics applied to choices.",
            6: "Moral tests, disputes, and the discipline to hold to principle.",
            7: "Conduct in relationships and fairness toward others.",
            8: "Hidden character, integrity under crisis, and inherited karma from the father.",
            9: "Father's blessings, dharma, higher values, and the strongest house of character.",
            10: "Reputation, ethics in work, and the conduct the world sees.",
            11: "Gains through good character and the company of principled people.",
            12: "Private conscience, moral retreat, and where character is refined in solitude.",
        },
        "rules": [
            "A strong D45 lagna and 9th house show sound character and paternal blessings.",
            "The Sun and 9th lord well placed confirm dignity and a strong moral grain.",
            "Benefics on the 1st or 9th refine conduct and steady the personality.",
            "Malefic affliction of the 9th can mean character tests or strain with the father.",
            "Vargottama planets reinforce the values and conduct they signify.",
        ],
    },
    "D60": {
        "factor": 60, "title": "Shashtiamsha Chart (D60)", "tag": "Shashtiamsha",
        "subtitle": "Past-life karma; the master fine-tuning chart",
        "theme": "past-life karma and the fine grain of destiny",
        "karaka": "Saturn", "karaka_topic": "the fruit of past karma",
        "signature_house": 1, "key_houses": [1, 5, 9, 10],
        "intro": (
            "Shashtiamsha (D60) divides each sign into sixty parts — the most refined "
            "chart, given great weight by the classics for the fruit of past-life karma. "
            "It fine-tunes every theme of the birth chart: where the deepest merit and "
            "the deepest debts lie. Read as the karmic backdrop behind all other charts."
        ),
        "house_sigs": {
            1: "The karmic self you are born with — merit and debt carried into this life.",
            2: "Karma around wealth and family, and speech earned from past deeds.",
            3: "Inherited courage, efforts, and the karma of self-driven action.",
            4: "Karmic comfort or unrest at the emotional root, and the mother's karma.",
            5: "Past-life merit (purva punya), children, and the karma of the intellect.",
            6: "Karmic debts, enemies, and the service owed from past actions.",
            7: "Relationship karma and the partners drawn by past bonds.",
            8: "The deepest karmic accounts — longevity, crises, and hidden settlements.",
            9: "Stored merit, dharma, fortune, and the grace earned over lifetimes.",
            10: "Karma of action in the world — the work destiny brings to completion.",
            11: "Fulfilment owed by past merit and the gains destiny releases.",
            12: "Final settlements, liberation, and the karma resolved through letting go.",
        },
        "rules": [
            "A strong D60 lagna and lagna lord show favourable past-life merit behind this life.",
            "Benefics in trines (1, 5, 9) of D60 point to stored merit ripening into ease.",
            "Malefics in 6/8/12 of D60 mark karmic debts that ask to be worked through.",
            "The classics weight D60 heavily — it confirms or qualifies the whole birth chart.",
            "Vargottama planets show karma that repeats and matures consistently across lives.",
        ],
    },
}
