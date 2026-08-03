#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse Goel Locate Disease Astrologically OCR into goel_disease_book_data.json."""
from __future__ import annotations

import json
import re
from pathlib import Path

OCR = Path(__file__).resolve().parent / (
    "book_ocr/locate_disease_astro/LOCATE_DISEASE_ASTROLOGICALLY_(1)_ocr_full.txt"
)
OUT = Path(__file__).resolve().parent / "goel_disease_book_data.json"

# rules7 + OCR table p.15  -  sign ? body zones
SIGN_BODY = {
    "Aries": {"external": "Head", "internal": "Brain", "structural": "Cranium bones"},
    "Taurus": {"external": "Face", "internal": "Larynx", "structural": "Facial bones"},
    "Gemini": {"external": "Neck, shoulders, upper arms, upper chest", "internal": "Wind pipe, food pipe", "structural": "Collar, neck, shoulder bones"},
    "Cancer": {"external": "Breast, chest", "internal": "Lungs, ribs, heart", "structural": "Chest cage"},
    "Leo": {"external": "Upper abdomen", "internal": "Upper spine, liver, spleen, duodenum, small intestine", "structural": "Back bones, upper spine"},
    "Virgo": {"external": "Lower abdomen", "internal": "Bowels, large intestine", "structural": "Lower spine"},
    "Libra": {"external": "Region below navel, groins", "internal": "Uterus, ovary, testicles, kidney", "structural": "Pelvic bones"},
    "Scorpio": {"external": "Genital organs", "internal": "Genitals, anus, lower large intestine", "structural": "Lower back"},
    "Sagittarius": {"external": "Thighs, hips", "internal": "Hips, thighs, back", "structural": "Hip bones"},
    "Capricorn": {"external": "Knees", "internal": "Knees, joints", "structural": "Knee bones"},
    "Aquarius": {"external": "Calves, lower legs", "internal": "Calves, lower legs", "structural": "Lower leg bones"},
    "Pisces": {"external": "Soles of feet", "internal": "Feet, lymph", "structural": "Foot bones"},
}

D27_ZONE = {
    "Aries": "Head",
    "Taurus": "Face, eyes, mouth",
    "Gemini": "Neck, upper chest, shoulders",
    "Cancer": "Lungs, heart area",
    "Leo": "Area below chest",
    "Virgo": "Navel area, bowels",
    "Libra": "Area below navel",
    "Scorpio": "Genitals, intestines, excretory/urinary",
    "Sagittarius": "Hips, thighs, back",
    "Capricorn": "Knees",
    "Aquarius": "Calves, lower legs",
    "Pisces": "Soles of feet",
}

D6_HOUSE = {
    1: "General proneness; self-generated health patterns",
    2: "Eating habits and their effect on health",
    3: "Capacity to fight disease; recovery will",
    4: "Family support during illness",
    5: "Mental attitude toward illness; congenital tone",
    6: "Curable / acute outward disease",
    7: "Helpers or troublemakers during illness",
    8: "Chronic or hard-to-shift disease",
    9: "Luck factor in recovery",
    10: "Illness linked to one's own actions",
    11: "Prolongation or spread of disease",
    12: "Hospitalization / confinement (benefic here aids recovery)",
}

# OCR p.24-25 disease tendency table (curated from book; grep Nakshatra + Disease)
NAKSHATRA_DISEASE = {
    "Ashwini": "Head, brain, migraine, mental restlessness",
    "Bharani": "Feet injury, reproductive stress, blood disorders",
    "Krittika": "Head, eyes, fever, bile, inflammation",
    "Rohini": "Chest, cough, throat, menstrual irregularity",
    "Mrigashira": "Eyes, throat, nervous tension",
    "Ardra": "Lungs, breathing, dental, circulation",
    "Punarvasu": "ENT, asthma, bronchitis, liver, constipation, high BP",
    "Pushya": "Digestive trouble, skin, dental, hands and arms",
    "Ashlesha": "Nervous system, circulation, dental, spine pain",
    "Magha": "Heart, back, spinal pain, anemia",
    "Purva Phalguni": "Heart, spine, circulation, dental",
    "Uttara Phalguni": "Stomach, intestines, liver, constipation",
    "Hasta": "Bowels, colon, cold allergies, water-related sensitivity, blood pressure, arteries/veins",
    "Chitra": "Ulcers, kidney, stomach, intestine worms, brain fever",
    "Swati": "Urinary tract, skin, eczema, appendicitis",
    "Vishakha": "Prostate, piles, colon, diabetes, paralysis",
    "Anuradha": "Constipation, piles, womb, breast, cough and cold",
    "Jyeshtha": "Neck pain, gout, fertility, fistula, high BP",
    "Mula": "Mental stress, obesity, foot problems, joint pains, low BP",
    "Purva Ashadha": "Bladder, kidney, rheumatism, lungs, diabetes",
    "Uttara Ashadha": "Stomach, eczema, arthritis, skin dryness, weak digestion",
    "Shravana": "Hearing, reproductive organs, sensitive skin, knees",
    "Dhanishtha": "Arthritis, back, hypertension, piles, heart",
    "Shatabhisha": "Jaw, fractures, rheumatism, heart disease",
    "Purva Bhadrapada": "Feet, intestinal gas, hernia",
    "Uttara Bhadrapada": "Feet, intestinal gas, hernia",
    "Revati": "Feet, intestinal gas, hernia, digestive sensitivity",
}

PLANET_HEALTH = {
    "Sun": "Vitality, heart, bones, stomach, eyes; weak Sun ? head/heart strain",
    "Moon": "Fluids, lungs, mind-mood, blood; afflicted Moon ? chest, water retention, mental stress",
    "Mars": "Blood, accidents, surgery, bile; afflicted Mars ? inflammation, injury, piles",
    "Mercury": "Nervous system, skin, digestion; afflicted Mercury ? anxiety, skin, speech/throat",
    "Jupiter": "Liver, fat, growth; weak Jupiter ? metabolic and weight patterns",
    "Venus": "Reproductive, urinary, kidneys, sugar balance",
    "Saturn": "Chronic illness, joints, teeth, wind, depression, lameness",
    "Rahu": "Lungs, breathing, phobias, ulcers, poisoning, anxiety",
    "Ketu": "Ulcers, fever, stomach, eyes, surgery, mysterious or hard-to-diagnose complaints",
}

# OCR remedies chapter  -  planet-day upaya (rules40/41 aligned)
PLANET_REMEDY = {
    "Sun": {"mantra": "Aditya Hridayam or Om Hrim Suryaya Namah (108x Sunday)", "charity": "Wheat and jaggery on Sunday", "gem": "Ruby / garnet (only if suitable)"},
    "Moon": {"mantra": "Chandra Gayatri or Om Som Somaya Namah (108x Monday)", "charity": "Rice, milk, white items on Monday", "gem": "Pearl / moonstone (only if suitable)"},
    "Mars": {"mantra": "Hanuman Chalisa (Tuesday); Maha Mrityunjaya if surgery risk", "charity": "Red lentils on Tuesday", "gem": "Red coral (only if suitable)"},
    "Mercury": {"mantra": "Vishnu Sahasranama (Wednesday)", "charity": "Green items, books on Wednesday", "gem": "Emerald / green onyx (only if suitable)"},
    "Jupiter": {"mantra": "Guru mantra Om Gram Grim Graum Sah Gurave Namah (108x Thursday)", "charity": "Yellow items, support teachers Thursday", "gem": "Yellow sapphire / topaz (only if suitable)"},
    "Venus": {"mantra": "Om Shrim Mahalakshmyai Namah (Friday)", "charity": "White sweets, ghee Friday", "gem": "Diamond / opal (only if suitable)"},
    "Saturn": {"mantra": "Hanuman Chalisa (Saturday); Shani mantra with guidance", "charity": "Mustard oil, black sesame, serve elderly Saturday", "gem": "Blue sapphire - test 3 days only if advised"},
    "Rahu": {"mantra": "Durga Saptashati or Om Durgayai Namah", "charity": "Urad dal on Saturday/Amavasya", "gem": "Hessonite (only if suitable)"},
    "Ketu": {"mantra": "Ganesha mantra; Ketu Gayatri (108x Tuesday)", "charity": "Blankets to poor on Tuesday", "gem": "Cat's eye (only if suitable)"},
}

YOGINI_HEALTH = {
    "Ulka": "Saturn-ruled - classic health watch: ears, feet, teeth, chronic strain",
    "Pingala": "Sun-ruled - bilious heat, blood, inflammation watch",
    "Bhramari": "Mars-ruled - accident, surgery, blood-injury tone",
    "Sankata": "Rahu-ruled - anxiety, mysterious complaints, sudden flare-ups",
    "Dhanya": "Jupiter-ruled - generally protective; recovery tone",
    "Siddha": "Venus-ruled - comfort and healing tone when Venus is not afflicted",
}


def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def parse_planet_health_ocr(text: str) -> dict[str, str]:
    """Supplement planet health blurbs from OCR if present."""
    out = dict(PLANET_HEALTH)
    blocks = {
        "Saturn": r"Saturn:\s*(.+?)(?=Rahu:|Ketu:|Gulika:|Houses)",
        "Rahu": r"Rahu:\s*(.+?)(?=Ketu:|Gulika:|Houses)",
        "Ketu": r"Ketu:\s*(.+?)(?=Gulika:|Houses)",
    }
    for pl, pat in blocks.items():
        m = re.search(pat, text, re.S | re.I)
        if m:
            out[pl] = _clean(m.group(1))[:420]
    return out


def main() -> None:
    text = OCR.read_text(encoding="utf-8", errors="ignore") if OCR.is_file() else ""
    data = {
        "source": "Locate Disease Astrologically - V.P. Goel (Sagar Publications, 2016)",
        "ocr_path": str(OCR),
        "sign_body_parts": SIGN_BODY,
        "d27_body_zones": D27_ZONE,
        "d6_house_meanings": {str(k): v for k, v in D6_HOUSE.items()},
        "nakshatra_disease_tendency": NAKSHATRA_DISEASE,
        "planet_health": parse_planet_health_ocr(text),
        "planet_remedy": PLANET_REMEDY,
        "yogini_health_tone": YOGINI_HEALTH,
        "kalaka_rules": {
            "internal": "0-5, 10-15, 20-25 degrees of sign (1st kalaka) - lifestyle, internal imbalance",
            "external": "5-10, 15-20, 25-30 degrees (2nd kalaka) - food, environment, accident, infection",
        },
        "severity_combinations": [
            {"id": "saturn_rahu_d27", "rule": "Saturn and Rahu in same D27 sign", "meaning": "Chronic or serious vulnerability in that body zone (Goel)"},
            {"id": "mars_aspect", "rule": "Mars linked to disease planet or afflicted D27 zone", "meaning": "Surgical or invasive intervention possible"},
            {"id": "lord8_in6", "rule": "8th lord in 6th (opposite Raja Yoga)", "meaning": "Can turn illness into recovery through service and discipline"},
            {"id": "lord1_in8", "rule": "Lagna lord in 8th", "meaning": "Constitutional health tension through life"},
        ],
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"nakshatras={len(data['nakshatra_disease_tendency'])} signs={len(data['sign_body_parts'])}")
    print(f"written -> {OUT}")


if __name__ == "__main__":
    main()
