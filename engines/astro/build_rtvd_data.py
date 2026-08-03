#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse RTVD book OCR (rules16) into rtvd_book_data.json."""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
OCR = BASE / "book_ocr/rasi_tulya_vatsara_dasa/RASI_TULYA_VATSARA_DASA__A_SIMPLE_AND_UNIQUE_METHOD_OF_TIMING_EVENTS_ocr_full.txt"
OUT = BASE / "rtvd_book_data.json"


def _clean(t: str) -> str:
    t = re.sub(r"========== PAGE \d+ ==========", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_general_rules(text: str) -> list[str]:
    m = re.search(r"General rules", text, re.I)
    if not m:
        return []
    chunk = text[m.start(): m.start() + 6000]
    rules = []
    patterns = [
        r"Prominence is given to the Rasi chart",
        r"Karakatvas attributed to the signs, houses and planets",
        r"consider the house where the lord of the sign is placed",
        r"Nakshatra in which the lord of the concerned sign is placed",
        r"Position of the sign with reference to the Chandra Lagna",
        r"lord has ownership over two signs",
        r"decreasing order of certainty",
        r"influence of two or more natural benefics",
        r"lords of the 6.*?12.*?and afflicted by malefics",
        r"lords of Trikonas.*?Kendras.*?aspected by benefic",
        r"Cancellation of debility.*?does not apply",
        r"overlap with the following year",
        r"integrate.*?Vimshottari.*?transits",
    ]
    for pat in patterns:
        hit = re.search(pat, chunk, re.I | re.S)
        if hit:
            line = _clean(hit.group(0))
            if 30 < len(line) < 320:
                rules.append(line[0].upper() + line[1:] + ("" if line.endswith(".") else "."))
    return rules[:18]


def parse_topic_rules(text: str) -> dict:
    curated = {
        "marriage": [
            "Marriage can take place in the year indicated by the 7th house like 19, 31, 43 etc.",
            "Years whose Rasi lord is placed in the 7th house or with the 7th lord may give marriage.",
            "Years whose Rasi lords are joined with Venus, Jupiter and Moon may also materialize the event.",
        ],
        "career": [
            "Year whose Rasi lord placed in the 10th may prove beneficial for career.",
            "Years indicated by the 1st, 4th and 10th houses may fructify career events.",
        ],
        "children": [
            "Years indicated by the 2nd, 5th, 9th and 11th houses may bestow children.",
            "When Sun is in the year sign, some manuals read male-child symbolism.",
        ],
        "wealth": [
            "Years indicated by the 2nd, 9th and 11th houses favour financial gains.",
            "Year-lord in 2nd or 11th strengthens income themes.",
        ],
        "health": [
            "Years of 6th, 8th and 12th houses need extra care for accidents and disease.",
            "Cancellation of debility may be ignored for health reads in this system.",
        ],
        "parents": [
            "Father themes: years of 4th, 8th and 9th houses.",
            "Mother themes: years of 3rd, 4th and 11th houses.",
        ],
        "siblings": [
            "Sibling events favour years of the 3rd and 11th houses.",
        ],
    }
    topics: dict[str, list[str]] = {k: list(v) for k, v in curated.items()}
    blocks = [
        ("marriage", r"Timing of Marriage", r"Timing of Divorce"),
        ("career", r"Beginning of Career", r"Promotion in Career"),
        ("children", r"Timing of Birth of Children", r"Timing of Miscarriage"),
    ]
    for key, start, end in blocks:
        s = re.search(start, text, re.I)
        if not s:
            continue
        e = re.search(end, text[s.end():], re.I)
        chunk = text[s.start(): s.end() + (e.start() if e else 2000)]
        for line in re.split(r"\d+\.\s+", chunk):
            line = _clean(line)
            if (
                45 < len(line) < 220
                and re.search(r"\b(year|house|lord|marriage|career|child)\b", line, re.I)
                and "Chart II" not in line
                and "cancellation of debility" not in line.lower()
            ):
                topics[key].append(line)
        topics[key] = list(dict.fromkeys(topics[key]))[:6]
    return topics


def curated_general_rules() -> list[str]:
    return [
        "Prominence is given to the Rasi chart - whole-sign houses from lagna.",
        "Karakatvas of signs, houses and planets have greater significance.",
        "While judging a year, consider where the lord of the sign is placed first.",
        "Next: nakshatra of the year-sign lord and its nakshatra lord's karakatva.",
        "Then the sign itself - karakatvas of the house represented by the sign.",
        "Position of the sign with reference to Chandra Lagna should also be considered.",
        "When the year-lord owns two signs, events of the other house may surface strongly.",
        "Certainty decreases: lord in bhava > lord in nakshatra of bhava lord > lord joins bhava lord > year sign is the bhava.",
        "Two or more natural benefics on year sign or lord favour the year; two or more malefics stress it.",
        "Year-lord with lords of 6th, 8th or 12th and malefics afflicts significations of lord's house.",
        "Year-lord with trikona and kendra lords aspected by benefics favours significations.",
        "Cancellation of debility often ignored for health, accident and death in this system.",
        "Consider overlap with the following year; about one month at year boundary.",
        "Always integrate Vimshottari Dasa and transits for precise forward dating.",
    ]


def main() -> None:
    text = OCR.read_text(encoding="utf-8", errors="ignore") if OCR.is_file() else ""
    data = {
        "source": "Dr. K. Guru Rajesh - Rasi Tulya Vatsara Dasa (2016) / rules16.md",
        "general_rules": parse_general_rules(text) if text else curated_general_rules(),
        "topic_rules": parse_topic_rules(text) if text else {},
        "topic_houses": {
            "marriage": {"primary": [7], "also": [1, 4, 12], "ages_note": "7, 19, 31, 43..."},
            "career": {"primary": [10], "also": [1, 4], "ages_note": "10, 22, 34, 46..."},
            "children": {"primary": [2, 5], "also": [1, 9, 11], "ages_note": "2, 5, 14, 17, 26, 29..."},
            "wealth": {"primary": [2, 9, 11], "also": [1, 4, 5, 10, 8], "ages_note": "2, 9, 11 house years"},
            "health": {"primary": [6, 8, 12], "also": [], "ages_note": "6, 8, 12, 18, 20, 24..."},
            "parents": {"father": [4, 8, 9], "mother": [3, 4, 11], "ages_note": "4/8/9 father; 3/11 mother"},
            "siblings": {"primary": [3, 11], "also": [], "ages_note": "3, 15, 27 and 11, 23, 35..."},
            "travel": {"primary": [9, 12], "also": [3, 7], "ages_note": "9th and 12th house years"},
        },
        "certainty_levels": [
            "Level 1: year-lord occupies the target house",
            "Level 2: year-lord in nakshatra of planet owning/occupying target house",
            "Level 3: year-lord joins the target house lord",
            "Level 4: active year-sign IS the target house from lagna",
        ],
        "methodology_lead": (
            "Each calendar year activates one whole-sign house from your Ascendant. "
            "Judge the year-lord's placement, nakshatra, dual lordship, benefic/malefic mass, "
            "and Moon-lagna view - then triangulate Vimshottari and transits for dating."
        ),
    }
    if len(data["general_rules"]) < 8:
        data["general_rules"] = curated_general_rules()
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"written {OUT} rules={len(data['general_rules'])} topics={list(data['topic_houses'])}")


if __name__ == "__main__":
    main()
