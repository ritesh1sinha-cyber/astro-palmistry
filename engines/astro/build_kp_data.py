#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse KP OCR corpus into kp_book_data.json (rules19-21 + houses/events manual)."""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
HOUSES_OCR = BASE / (
    "book_ocr/kp_houses_events_research/"
    "HOUSES_AND_EVENTS_IN_KP_ASTROLOGY_A_RESEARCH-BASED_MANUAL_ocr_full.txt"
)
TIMING_OCR = BASE / (
    "book_ocr/kp_timing_life_events/"
    "MASTERING_KP_ASTROLOGY__TIMING_LIFE_EVENTS_WITH_PRECISION_ocr_full.txt"
)
OUT = BASE / "kp_book_data.json"


def _clean(t: str) -> str:
    t = re.sub(r"========== PAGE \d+ ==========", " ", t)
    t = re.sub(r"[\u00a9\u00ae@]\s*", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _is_valid(text: str) -> bool:
    if len(text) < 30 or len(text) > 520:
        return False
    letters = sum(c.isalpha() for c in text)
    return letters / max(len(text), 1) > 0.45


def _slice(text: str, start_pat: str, stop_pats: tuple[str, ...]) -> str:
    m = re.search(start_pat, text, re.I)
    if not m:
        return ""
    chunk = text[m.start():]
    best = len(chunk)
    for sp in stop_pats:
        sm = re.search(sp, chunk[80:], re.I)
        if sm:
            best = min(best, 80 + sm.start())
    return chunk[:best]


def parse_rules(chunk: str) -> list[dict]:
    if not chunk:
        return []
    rules: list[dict] = []
    parts = re.split(r"(?m)(Rule\s+\d+(?:\s*-\s*[^\n]+)?)\s*\n", chunk)
    i = 1
    while i < len(parts) - 1:
        header = parts[i].strip()
        body = parts[i + 1]
        i += 2
        hm = re.match(r"Rule\s+(\d+(?:\s*-\s*.+)?)", header, re.I)
        if not hm:
            continue
        title_m = re.match(r"Rule\s+\d+\s*-\s*(.+)", header, re.I)
        title = title_m.group(1).strip() if title_m else header
        body = re.split(r"(?m)(?:Quick Reference|========== PAGE|Chapter \d+)", body, maxsplit=1)[0]
        body = _clean(body)
        if _is_valid(body):
            rules.append({"id": hm.group(1).strip(), "title": title, "text": body})
    return rules


def parse_timing_concepts(text: str) -> dict:
    chunk = _slice(
        text,
        r"The Cuspal Sub Lord",
        (r"5\. Example - Understanding", r"Chapter \d+"),
    )
    bullets = []
    for pat in (
        r"The 7th cusp sub lord tells whether marriage will occur",
        r"The 10th cusp sub lord reveals the nature of profession",
        r"The 5th cusp sub lord speaks of childbirth and creativity",
        r"sub lord as the final authority on fulfillment",
        r"6th CSL.*?signifying.*?6, 8, 12.*?chronic",
        r"6th CSL.*?signifying.*?1, 5, 9.*?recovery",
    ):
        hit = re.search(pat, chunk, re.I | re.S)
        if hit:
            bullets.append(_clean(hit.group(0)))
    six_steps = []
    step_chunk = _slice(text, r"Step 1: Identify event-related houses", (r"5\. Example",))
    for n in range(1, 7):
        hit = re.search(rf"Step {n}:\s*([^\.]+\.)", step_chunk, re.I)
        if hit:
            six_steps.append(_clean(hit.group(1)))
    return {"csl_bullets": bullets[:6], "six_steps": six_steps}


def main() -> None:
    houses = HOUSES_OCR.read_text(encoding="utf-8", errors="ignore") if HOUSES_OCR.is_file() else ""
    timing = TIMING_OCR.read_text(encoding="utf-8", errors="ignore") if TIMING_OCR.is_file() else ""

    domains = {
        "health": (
            r"Chapter 1: Health",
            (r"Chapter 2:", r"Quick Reference Box"),
        ),
        "marriage": (
            r"Chapter 3: Marriage",
            (r"Chapter 4:", r"Quick Reference Box"),
        ),
        "children": (
            r"Childbirth",
            (r"Chapter \d+:", r"Quick Reference"),
        ),
        "education": (
            r"Chapter 5:",
            (r"Chapter 6:",),
        ),
        "travel": (
            r"Chapter 7:",
            (r"Chapter 8:",),
        ),
        "modern_career": (
            r"Modern Career",
            (r"Modern Health",),
        ),
        "modern_health": (
            r"Modern Health",
            (r"Modern Relationships",),
        ),
    }

    domain_rules: dict[str, list[dict]] = {}
    for key, (start, stops) in domains.items():
        chunk = _slice(houses, start, stops)
        domain_rules[key] = parse_rules(chunk)

    # Fallback curated rules if OCR parse thin
    if len(domain_rules.get("marriage", [])) < 3:
        domain_rules["marriage"] = [
            {"id": "1", "title": "Marriage Promise", "text": "Marriage is promised when the 7th house connects with the 2nd and 11th houses. Venus and Jupiter support this promise."},
            {"id": "4", "title": "Divorce or Separation", "text": "If the 7th house connects with the 6th and 12th, marriage suffers divorce or permanent separation."},
            {"id": "7", "title": "Happy Married Life", "text": "Benefics like Jupiter and Venus influencing the 7th, 2nd, and 11th ensure harmony and lasting happiness."},
        ]
    if len(domain_rules.get("children", [])) < 2:
        domain_rules["children"] = [
            {"id": "8", "title": "Childbirth Promise", "text": "The 5th house connecting 2nd and 11th assures childbirth. Jupiter and Venus as karakas bring blessings of children."},
            {"id": "9", "title": "Delay in Progeny", "text": "Saturn influencing the 5th delays childbirth. Rahu creates hurdles in conception."},
            {"id": "11", "title": "Adoption/IVF", "text": "5th house with Rahu and Mercury indicates unconventional childbirth like IVF or adoption."},
        ]
    if len(domain_rules.get("health", [])) < 3:
        domain_rules["health"] = [
            {"id": "1", "title": "Illness", "text": "The 6th house is primary for disease; CSL of 6th connecting 1st can bring illness. Malefics strengthen; benefics give relief."},
            {"id": "6", "title": "Recovery", "text": "Recovery is seen when the 6th connects with the 11th. Benefics like Jupiter or Mercury enhance healing."},
            {"id": "7", "title": "Chronic Diseases", "text": "6th linked with Saturn or Rahu brings long-term or hard-to-diagnose illness."},
        ]
    for key in list(domain_rules.keys()):
        domain_rules[key] = domain_rules[key][:12]

    data = {
        "event_groups": {
            "education": {"fav": [4, 9, 11], "unfav": [], "primary": 9},
            "career": {"fav": [2, 6, 10, 11], "unfav": [5, 9, 12], "primary": 10},
            "marriage": {"fav": [2, 7, 11], "unfav": [6, 10, 12], "primary": 7},
            "children": {"fav": [2, 5, 11], "unfav": [1, 4, 10], "primary": 5},
            "property": {"fav": [2, 4, 11], "unfav": [3, 8, 12], "primary": 4},
            "travel": {"fav": [3, 9, 12], "unfav": [2, 4, 10], "primary": 9},
            "health_bad": {"fav": [6, 8, 12], "unfav": [1, 5, 9], "primary": 6},
            "health_good": {"fav": [1, 5, 9], "unfav": [6, 8, 12], "primary": 1},
        },
        "career_house_nature": {
            "1": "Self-driven, entrepreneurial; career fused with identity.",
            "2": "Banking, family profession, speech and resource-based income.",
            "3": "Communication, IT, media, writing, technical trade, short-range skills.",
            "5": "Education, creative fields, coaching, investment-linked work.",
            "6": "Service sector, employment, healthcare, legal service roles.",
            "9": "Consulting, teaching, international links, advisory or legal authority.",
            "10": "Strong public role; career as central life theme.",
            "11": "Network-driven career, corporate gains, large-organisation work.",
            "12": "Foreign posting, institutions, behind-the-scenes or export work.",
        },
        "csl_planet": {
            "Sun": "Authority, visibility, government links, father-theme, leadership.",
            "Moon": "Public mood, nurture, food, data, travel cycles, caregiving industries.",
            "Mars": "Competition, engineering, surgery, property, acute events, courage.",
            "Mercury": "Commerce, writing, contracts, analytics, IT communication, trade.",
            "Jupiter": "Teaching, ethics, law, counsel, gradual expansion, dharma.",
            "Venus": "Arts, comfort, contracts, diplomacy, luxury, partnership grace.",
            "Saturn": "Slow proof, duty, delay, structure, chronic themes, discipline.",
            "Rahu": "Foreign, unconventional, tech, media, sudden swings, ambition.",
            "Ketu": "Detachment, research, spiritual refit, endings, specialist depth.",
        },
        "domain_rules": domain_rules,
        "timing": parse_timing_concepts(timing),
        "health_csl": {
            "chronic": "If the 6th cusp sub lord signifies houses 6, 8, and/or 12, chronic or serious illness tendency is indicated (Ravichandran).",
            "recovery": "If the 6th cusp sub lord signifies houses 1, 5, and/or 9, constitution tends toward quicker recovery.",
            "eighth_recovery": "8th cusp sub lord signifying 1, 5, 9 supports recovery after health scares.",
        },
    }
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    counts = {k: len(v) for k, v in domain_rules.items()}
    print(f"written -> {OUT}")
    print("rule counts:", counts)


if __name__ == "__main__":
    main()
