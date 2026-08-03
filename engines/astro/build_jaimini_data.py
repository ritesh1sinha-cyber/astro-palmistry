#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse Jaimini OCR (Goel rules6, Boney gems rules30, jewels rules31) into jaimini_book_data.json."""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
GOEL_OCR = BASE / "book_ocr/jaimini_predicting/PREDICTING_THROUGH_JAIMINI_ASTROLOGY_ocr_full.txt"
JEWELS_OCR = BASE / "book_ocr/jewels_jaimini/JEWELS_OF_JAIMINI_ocr_full.txt"
OUT = BASE / "jaimini_book_data.json"

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


def _gems_ocr_path() -> Path:
    hits = list((BASE / "book_ocr/gems_jaimini_karakamsha").glob("GEMS_OF_JAIMINI*_ocr_full.txt"))
    if not hits:
        raise FileNotFoundError("Gems Jaimini OCR not found under book_ocr/gems_jaimini_karakamsha/")
    return hits[0]


def _clean(t: str) -> str:
    t = re.sub(r"========== PAGE \d+ ==========", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_goel_basics(text: str) -> list[str]:
    m = re.search(r"Jaimini system of astrology is a unique", text, re.I)
    if not m:
        return []
    chunk = text[m.start(): m.start() + 3500]
    bullets = []
    for pat in (
        r"aspects are based on signs",
        r"significator or karakas are fixed",
        r"signs are synonymous with houses",
        r"dasha of Jaimini are not\s+based on moon",
        r"calculation of strength.*?simple in Jaimini",
        r"Concept of Karkamsha is unique",
        r"Effect of argala is important",
    ):
        hit = re.search(pat, chunk, re.I | re.S)
        if hit:
            line = _clean(hit.group(0))
            if len(line) > 20:
                bullets.append(line[0].upper() + line[1:] + ".")
    return bullets[:8]


def parse_goel_argala(text: str) -> list[str]:
    m = re.search(r"Argala in Prediction", text, re.I)
    if not m:
        return []
    chunk = text[m.start(): m.start() + 4500]
    rules = []
    for pat in (
        r"planets in 4th, 2nd, and 11th cause\s+Argala.*?planets in 10th, 12th and 3rd",
        r"Planets in 5th also cause Argala.*?countered by planets in 9th",
        r"three or more malefic.*?Vipreet Argala.*?favorable",
        r"planets causing Argala is stronger.*?prevail",
        r"There is no counter for the Argala caused by\s+three planets in third house",
        r"When there is an Argala on lagna, Arudha lagna.*?famous\s+and fortunate",
        r"unobstructed\s+Argala and aspecting lagna will make a person",
        r"unobstructed argala for lagna, 5th and.*?fame",
    ):
        hit = re.search(pat, chunk, re.I | re.S)
        if hit:
            rules.append(_clean(hit.group(0)))
    return rules


def _is_valid_clause(text: str) -> bool:
    if len(text) < 25 or len(text) > 400:
        return False
    bad = re.search(r"\b(?:Sag|Sco|Virg|Libr|Cap|Ari|Tau|Gem|Can|Leo|Aqu|Pis|ASz|Ra,|Me\d|chart|horoscope)\b", text, re.I)
    if bad:
        return False
    letters = sum(c.isalpha() for c in text)
    return letters / max(len(text), 1) > 0.55


def parse_gems_kl_occupation(text: str) -> dict[str, str]:
    """BPHS karakamsa-lagna occupation sutras plus Jaimini tatra/2nd series."""
    sutra = {
        "Sun": "Sun therein or in the 2nd from karakamsa: government official or royal assignments.",
        "Moon": "Full Moon and Venus therein or in the 2nd: enjoys life, scholar, educator.",
        "Mars": "Mars therein or in the 2nd: metals, fire work, spears, alchemist.",
        "Mercury": "Mercury therein or in the 2nd: commerce, weaving, craftsmanship, legal knowledge.",
        "Jupiter": "Jupiter therein or in the 2nd: higher wisdom, Vedas, spiritual knowledge.",
        "Venus": "Venus therein or in the 2nd: government liaison, amorous nature, longevity; state affairs.",
        "Saturn": "Saturn therein or in the 2nd: success in one's line of work; family profession.",
        "Rahu": "Rahu therein or in the 2nd: archer, thief, poisons/drugs, metal mechanic.",
        "Ketu": "Ketu therein or in the 2nd: elephant trade; thief (BPHS parallel).",
    }
    patterns = [
        (r'If the Sun is in the k\w*vakamsa[^"]+"([^"]+)"', "Sun"),
        (r'If the Full Moon be there[^"]+"([^"]+)"', "Moon"),
        (r"If strong Mars is in the karakam[^\"]+\"([^\"]+)\"", "Mars"),
        (r"If strong Mercury is in the karakam[^\"]+\"([^\"]+)\"", "Mercury"),
        (r'Should Jupiter be in the karakam[^"]+"([^"]+)"', "Jupiter"),
        (r"In case Venus be there in the karakamsa[^\"]+\"([^\"]+)\"", "Venus"),
        (r"If Saturn be there in the karakams[^\"]+\"([^\"]+)\"", "Saturn"),
        (r"In case Rahu be there[^\"]+\"([^\"]+)\"", "Rahu"),
        (r"if Ketu be there[^\"]+\"([^\"]+)\"", "Ketu"),
    ]
    out: dict[str, str] = dict(sutra)
    for pat, pl in patterns:
        m = re.search(pat, text, re.I | re.S)
        if m:
            parsed = _clean(m.group(1))
            if _is_valid_clause(parsed):
                out[pl] = parsed
    return out


def parse_gems_house_themes(text: str) -> dict[str, str]:
    themes: dict[str, str] = {}
    hits = [
        (
            "10",
            r"Mercury occupying or aspecting the\s+10th house - like Saturn",
            "Mercury in or aspecting 10th from KL: accomplished professional line (Saturn-like success).",
        ),
        (
            "10",
            r"If from the kdrakamSsa in the 10th house there is\s+conjunction or aspect of the Sun and Moon.*?kingdom",
            "Sun-Moon on 10th from KL with Jupiter: kingdom, high authority, protector of the earth.",
        ),
        (
            "4",
            r"The Moon and Venus conjoined or in\s+aspect to the 4th house - a palace",
            "Moon-Venus on 4th from KL: palatial home, status, luxury property.",
        ),
        (
            "5",
            r"The Moon and Jupiter in the 1st or\s+5th house - an author",
            "Moon and Jupiter in 1st or 5th from KL: authorship, knowledge, creative intelligence.",
        ),
        (
            "12",
            r"An exalted benefic in the 12.*?house\s+gives a blissful realm",
            "Exalted benefic in 12th from KL: blissful afterlife realm (not full moksha alone).",
        ),
        (
            "12",
            r"Ketu - spiritual liberation",
            "Ketu in 12th from KL with benefic: kaivalya / spiritual liberation potential.",
        ),
    ]
    for house, pat, fallback in hits:
        m = re.search(pat, text, re.I | re.S)
        raw = _clean(m.group(0)) if m else fallback
        themes[house] = raw if _is_valid_clause(raw) else fallback
    return themes


def parse_gems_planet_house_quotes(text: str) -> dict[str, dict[str, str]]:
    nested: dict[str, dict[str, str]] = {}
    curated = {
        "Mercury": {
            "10": "Mercury occupying or aspecting 10th from KL - like Saturn: very accomplished in one's line of work; benefic aspect sustains success.",
        },
        "Sun": {"10": "Sun in 10th from KL: directional strength; government authority and stardom karaka."},
        "Moon": {
            "4": "Moon influencing 4th from KL: emotional roots, mother, property comfort.",
            "5": "Moon in 5th from KL: authorship and knowledge themes.",
        },
        "Venus": {
            "4": "Venus on 4th from KL with Moon: palace, luxury home.",
            "2": "Venus in 2nd from KL: enjoyer, educator, sensual prosperity.",
        },
        "Jupiter": {
            "5": "Jupiter in 5th from KL: wisdom, Vedas, good acts.",
            "10": "Jupiter aspecting 10th from KL: dignified career elevation.",
        },
        "Mars": {
            "5": "Mars in 5th from KL: spears, technical precision, engineering inclination.",
            "2": "Mars in 2nd from KL: metals, fire trades, competitive earnings.",
        },
        "Saturn": {
            "10": "Saturn influencing 10th from KL: slow, enduring professional success.",
            "2": "Saturn in 2nd from KL: success is one's line of work.",
        },
        "Ketu": {
            "12": "Ketu in 12th from KL with benefic: spiritual liberation; moksha signs Cancer/Pisces strengthen.",
            "2": "Ketu in 2nd from KL: unusual trade, elephant/dealing themes in classical text.",
        },
        "Rahu": {
            "10": "Rahu on 10th from KL: machinery, technical fields, machinist.",
            "2": "Rahu in 2nd from KL: archer, poisons/drugs, metal devices.",
        },
    }
    for pl, houses in curated.items():
        for h, txt in houses.items():
            nested.setdefault(pl, {})[h] = txt
    return nested


def parse_jewels_argala_tiers(text: str) -> dict[str, list[str]]:
    m = re.search(r"Superior Argalas:", text, re.I)
    if not m:
        return {"superior": [], "above_average": [], "average": []}
    chunk = text[m.start(): m.start() + 2500]
    tiers: dict[str, list[str]] = {"superior": [], "above_average": [], "average": []}
    parts = re.split(r"(Superior Argalas:|Above Average Argalas:|Average Argalas:)", chunk, flags=re.I)
    key_map = {
        "superior argalas:": "superior",
        "above average argalas:": "above_average",
        "average argalas:": "average",
    }
    current = None
    for part in parts:
        low = part.strip().lower()
        if low in key_map:
            current = key_map[low]
            continue
        if current and part.strip():
            for bullet in re.findall(r"[\+\-\u2022]\s*(.+?)(?=[\+\-\u2022]|$)", part, re.S):
                b = _clean(bullet)
                if len(b) > 25:
                    tiers[current].append(b)
    return tiers


def parse_jewels_yogada(text: str) -> list[str]:
    m = re.search(
        r"It is good to have a planet conjoined or aspecting the\s+special ascendants",
        text,
        re.I,
    )
    if not m:
        return []
    chunk = text[m.start(): m.start() + 2200]
    rules = []
    for bullet in re.findall(r"[0-9]+\.\s*(.+?)(?=[0-9]+\.|To summarize|$)", chunk, re.S):
        b = _clean(bullet)
        if 30 < len(b) < 500:
            rules.append(b)
    summary = re.search(r"To summarize then:(.+?)Since a fully yogada", chunk, re.I | re.S)
    if summary:
        for bullet in re.findall(r"[\+\-\u2022]\s*(.+?)(?=[\+\-\u2022]|$)", summary.group(1), re.S):
            b = _clean(bullet)
            if len(b) > 25:
                rules.append(b)
    return rules[:12]


GOEL_RAJA_YOGA = [
    "AK + AmK conjunction or mutual sign aspect: raja yoga material.",
    "AK + PK, AK + DK, AK + 5th lord: soul-level status yogas.",
    "AmK + PK, AmK + DK, AmK + 5th lord: career-wealth yogas.",
    "PK + DK, PK + 5th lord, DK + 5th lord: progeny-partnership yogas.",
    "Benefics in 2nd, 4th, 5th from AmK: high status.",
    "AmK in 3 or 6 with malefics or their aspect: professional skill/success.",
    "AmK in kendra/trikona/11 from AK: easier success; trika from AK: success after struggle.",
    "Same raja yogas repeating in D9: fruits come easier.",
]

KARAKA_ROLES = {
    "Atmakarak": "Soul, self, vitality; AK sign activation marks marriage-level life events.",
    "Amatyakarak": "Prime minister karaka: career, wealth, public karma.",
    "Bhratrukaraka": "Siblings, father, courage, guru; 3rd/9th themes.",
    "Matrukaraka": "Mother, home, property, education; 4th house karaka.",
    "Putrakaraka": "Children, intelligence, creativity, students; 5th house karaka.",
    "Gnatikaraka": "Relatives, rivals, disease; 6th/8th/12th friction karaka.",
    "Darakaraka": "Spouse, partnerships; 7th house karaka.",
}

# Drives vedic_jaimini_books_report.py section order (structure chart, NOT dasha timing).
REPORT_SECTIONS = [
    {"id": "goel_mindset", "book": "goel", "title": "Part A - Jaimini vs Parashara mindset", "rules": "rules6"},
    {"id": "goel_sign_aspects", "book": "goel", "title": "Part B - Sign aspects from lagna", "rules": "rules6"},
    {"id": "goel_karakas", "book": "goel", "title": "Part C - Seven cara karakas", "rules": "rules6"},
    {"id": "goel_three_lagnas", "book": "goel", "title": "Part C - Three lagna lenses (KL / birth / Arudha)", "rules": "rules6"},
    {"id": "goel_arudha", "book": "goel", "title": "Part D - Arudha lagna and Upapada", "rules": "rules6"},
    {"id": "goel_raja_yoga", "book": "goel", "title": "Part E - Jaimini raja yoga", "rules": "rules6"},
    {"id": "goel_argala_lagna", "book": "goel", "title": "Part F - Argala on lagna", "rules": "rules6"},
    {"id": "gems_kl_intro", "book": "gems", "title": "Karakamsha / Svamsa methodology", "rules": "rules30"},
    {"id": "gems_kl_argala", "book": "gems", "title": "Argala from Karakamsha lagna", "rules": "rules30"},
    {"id": "gems_kl_occupation", "book": "gems", "title": "Occupations from KL (planet in/on KL)", "rules": "rules30"},
    {"id": "gems_kl_10th", "book": "gems", "title": "Planets influencing 10th from KL - career", "rules": "rules30"},
    {"id": "gems_kl_4th", "book": "gems", "title": "Planets influencing 4th from KL - home/property", "rules": "rules30"},
    {"id": "gems_kl_9th", "book": "gems", "title": "Planets influencing 9th from KL - dharma/guru", "rules": "rules30"},
    {"id": "gems_kl_5th", "book": "gems", "title": "Planets in 5th from KL - knowledge/creativity", "rules": "rules30"},
    {"id": "gems_kl_12th_moksha", "book": "gems", "title": "12th from KL - spiritual liberation", "rules": "rules30"},
    {"id": "gems_kl_12th_devotion", "book": "gems", "title": "12th from KL - Ista Devata devotion", "rules": "rules30"},
    {"id": "jewels_argala_quality", "book": "jewels", "title": "Argala quality tiers", "rules": "rules31"},
    {"id": "jewels_yogada", "book": "jewels", "title": "Yogada and special-lagna raja yoga", "rules": "rules31"},
]

GOEL_RAJA_YOGA_EXTRA = [
    "Conjunction or mutual sign aspect of Venus and Moon gives excellence.",
    "Same planet aspecting bhava, hora and ghatika lagna gives status and wealth.",
    "One planet aspecting the same house in D1, D3 and D9 gives prosperity.",
    "Mars, Venus, Ketu in 3/11 pattern with mutual aspect (Vaithanika yoga).",
    "Benefics in 2nd, 4th, 5th from AmK give high status.",
    "AmK in 3rd or 6th with Mars, Sun, Saturn, Rahu or Ketu (or their aspect) gives professional success.",
    "Equal number of planets in lagna and 4th gives happiness.",
    "Repeat yogas in navamsha - fruits come with less effort.",
]


def main() -> None:
    gems_path = _gems_ocr_path()
    goel = GOEL_OCR.read_text(encoding="utf-8", errors="ignore")
    gems = gems_path.read_text(encoding="utf-8", errors="ignore")
    jewels = JEWELS_OCR.read_text(encoding="utf-8", errors="ignore")

    basics = parse_goel_basics(goel)
    argala = parse_goel_argala(goel)
    kl_occ = parse_gems_kl_occupation(gems)
    house_themes = parse_gems_house_themes(gems)
    planet_kl = parse_gems_planet_house_quotes(gems)
    argala_tiers = parse_jewels_argala_tiers(jewels)
    yogada = parse_jewels_yogada(jewels)

    data = {
        "sources": [
            "Predicting through Jaimini Astrology - V.P. Goel (rules6)",
            "Gems of Jaimini - Marc Boney (rules30)",
            "Jewels of Jaimini - Marc Boney (rules31)",
        ],
        "ocr_paths": {"goel": str(GOEL_OCR), "gems": str(gems_path), "jewels": str(JEWELS_OCR)},
        "goel_basics": basics,
        "goel_argala_rules": argala,
        "goel_raja_yoga_pairs": GOEL_RAJA_YOGA,
        "karaka_roles": KARAKA_ROLES,
        "gems_kl_occupation": kl_occ,
        "gems_house_themes": house_themes,
        "gems_planet_in_kl_house": planet_kl,
        "jewels_argala_tiers": argala_tiers,
        "jewels_yogada_rules": yogada,
        "report_sections": REPORT_SECTIONS,
        "goel_raja_yoga_extra": GOEL_RAJA_YOGA_EXTRA,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"basics={len(basics)} argala={len(argala)} kl_occ={len(kl_occ)} "
        f"house_themes={len(house_themes)} planet_kl={sum(len(v) for v in planet_kl.values())} "
        f"argala_tiers={sum(len(v) for v in argala_tiers.values())} yogada={len(yogada)}"
    )
    print(f"written -> {OUT}")


if __name__ == "__main__":
    main()
