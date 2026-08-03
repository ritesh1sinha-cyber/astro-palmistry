#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse Ashtakavarga OCR (rules10 / Marc Boney) into ashtakavarga_book_data.json."""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
OCR = BASE / "book_ocr/ashtakavarga_simplified/ASHTAKAVARGA_SIMPLIFIED_ocr_full.txt"
OUT = BASE / "ashtakavarga_book_data.json"

SIGN_ABBR = ["Ar", "Ta", "Ge", "Ca", "Le", "Vi", "Li", "Sc", "Sa", "Cp", "Aq", "Pi"]


def _clean(t: str) -> str:
    t = re.sub(r"========== PAGE \d+ ==========", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_general_rules(text: str) -> list[str]:
    patterns = [
        r"judging the effects of transits without the use of Ashtakavarga is a crime",
        r"Each of the grahas has a certain number of bindus",
        r"Total 337",
        r"337 divided by 12",
        r"greater than 30.*?favorable",
        r"less than 25.*?unfavorable",
        r"greater than 35.*?especially strong",
        r"Never judge a house.*?solely by.*?SAV",
        r"kakshaya.*?3\.75 degrees",
        r"integrate.*?Vimshottari",
        r"sade sati",
    ]
    rules = []
    for pat in patterns:
        hit = re.search(pat, text, re.I | re.S)
        if hit:
            line = _clean(hit.group(0))
            if 25 < len(line) < 280:
                rules.append(line[0].upper() + line[1:] + ("" if line.endswith(".") else "."))
    return rules[:14]


def curated_data() -> dict:
    return {
        "source": "Marc Boney - Ashtakavarga Simplified (2018) / rules10.md",
        "mantreswara_quote": (
            "To judge the effects of transits without the use of Ashtakavarga is a crime."
        ),
        "general_rules": [
            "Eight donors: Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, and Lagna. Rahu/Ketu excluded.",
            "BAV = bindus a planet collects in each sign; SAV = sum of seven planets per sign (total 337).",
            "Average SAV per sign is 28 (337/12). Above 30 favourable; below 25 unfavourable; above 35 especially strong.",
            "Never judge a house solely by SAV - confluence with lord, yogas, and divisional charts is mandatory.",
            "Transit quality: higher BAV in the transiting sign lifts results even through difficult houses.",
            "Hierarchy: natal promise first, dasha second, transits third (K.N. Rao teaching in book).",
            "Big Three donors (Lagna, Lagnesh, Moon) outweigh raw score when all three agree or all withhold.",
            "2nd and 11th lords donating bindus support wealth; withholding signals financial friction.",
            "6th lord donating with Lagna/Lagnesh support = competitive success; without = health vulnerability.",
            "Kakshaya: each sign has 8 sectors of 3d45m; switched-on sectors refine month-level timing.",
            "Sade Sati must be read with Saturn BAV in Moon sign and simultaneous Jupiter transit quality.",
            "Always triangulate with Vimshottari antardasha before pronouncing event timing.",
        ],
        "bav_quality": [
            {"score": 8, "label": "Outstanding"},
            {"score": 7, "label": "Excellent"},
            {"score": 6, "label": "Very Good"},
            {"score": 5, "label": "Good"},
            {"score": 4, "label": "Average"},
            {"score": 3, "label": "Poor"},
            {"score": 2, "label": "Unfortunate"},
            {"score": 1, "label": "Very Unfortunate"},
            {"score": 0, "label": "Calamitous"},
        ],
        "sav_bands": [
            {"min": 36, "label": "Especially strong", "class": "strong"},
            {"min": 30, "label": "Favourable", "class": "strong"},
            {"min": 25, "label": "Near average", "class": "avg"},
            {"min": 0, "label": "Weak", "class": "weak"},
        ],
        "kakshaya_rulers": [
            {"sector": 1, "ruler": "Saturn", "start_deg": 0, "end_deg": 3.75},
            {"sector": 2, "ruler": "Jupiter", "start_deg": 3.75, "end_deg": 7.5},
            {"sector": 3, "ruler": "Mars", "start_deg": 7.5, "end_deg": 11.25},
            {"sector": 4, "ruler": "Sun", "start_deg": 11.25, "end_deg": 15.0},
            {"sector": 5, "ruler": "Venus", "start_deg": 15.0, "end_deg": 18.75},
            {"sector": 6, "ruler": "Mercury", "start_deg": 18.75, "end_deg": 22.5},
            {"sector": 7, "ruler": "Moon", "start_deg": 22.5, "end_deg": 26.25},
            {"sector": 8, "ruler": "Lagna", "start_deg": 26.25, "end_deg": 30.0},
        ],
        "donor_checks": [
            "Big Three: Lagna, Lagnesh (ascendant lord), Moon",
            "Auspicious lords: 1st, 5th, 9th, 10th house lords",
            "Wealth lords: 2nd and 11th house lords",
            "Transiting planet donating to itself protects houses it rules",
            "6th lord + Big Three pattern distinguishes health vs competitive success",
        ],
        "methodology_lead": (
            "Ashtakavarga scores how many of eight cosmic factors approve each transit sign. "
            "Use SAV for structural house strength and the mahadasha lord's BAV for chapter quality."
        ),
    }


def main() -> None:
    text = OCR.read_text(encoding="utf-8", errors="ignore") if OCR.is_file() else ""
    data = curated_data()
    ocr_rules = parse_general_rules(text) if text else []
    if ocr_rules:
        data["ocr_snippets"] = ocr_rules
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"written {OUT} rules={len(data['general_rules'])}")


if __name__ == "__main__":
    main()
