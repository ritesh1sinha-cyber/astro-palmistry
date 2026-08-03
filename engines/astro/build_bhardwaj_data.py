#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse Bhardwaj OCR into bhardwaj_book_data.json (standalone corpus)."""
from __future__ import annotations

import json
import re
from pathlib import Path

OCR = Path(__file__).resolve().parent / (
    "book_ocr/complete_indian_predictive/"
    "THE_COMPLETE_BOOK_OF_INDIAN_PREDICTIVE_ASTROLOGY_ocr_full.txt"
)
OUT = Path(__file__).resolve().parent / "bhardwaj_book_data.json"

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
HOUSE_NAMES = {
    1: "FIRST HOUSE", 2: "SECOND HOUSE", 3: "THIRD HOUSE", 4: "FOURTH HOUSE",
    5: "FIFTH HOUSE", 6: "SIXTH HOUSE", 7: "SEVENTH HOUSE", 8: "EIGHTH HOUSE",
    9: "NINTH HOUSE", 10: "TENTH HOUSE", 11: "ELEVENTH HOUSE", 12: "TWELFTH HOUSE",
}
ORDINAL = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
    "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12,
    "lagna": 1, "ascendant": 1, "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5,
    "6th": 6, "7th": 7, "8th": 8, "9th": 9, "10th": 10, "11th": 11, "12th": 12,
}
MANUAL_PLANET_IN_HOUSE: dict[int, dict[str, str]] = {
    5: {
        "Sun": "If Sun is strong, the person will be a worshiper of Shiva and Surya, with sharp intellect, "
               "with a son and will get higher education. If there is a weak Sun, he will suffer from stomach disease.",
        "Moon": "The native is of pure mind, meritorious, happy, interested in art and literature, truthful, "
                "careful in everything, benefited from worship of the female deity, scholar; blessed with son in odd sign/navamsha and daughter in even.",
        "Mars": "Native has troubles related to children, stomach ailments, habit of backbiting and stubbornness. "
                "If Mars is strong in own, friendly or exaltation sign he will be blessed with a son and have strong digestive power.",
        "Mercury": "The native is skilled in Tantra-Mantra, knowledgeable, author, clever, practical, rational, blessed with son and efficient.",
        "Jupiter": "Meritorious, knowledgeable in assembly, rich, virtuous, minister-type, humble, patriotic; "
                   "obstacles related to child if in enemy or debilitated sign and navamsha.",
        "Venus": "Blessed with son in odd sign/navamsha and daughter in even; happy, rich, artist, intelligent, higher education, brilliant, sensual thinking.",
        "Saturn": "If weak: anxious about children, stomach sickness, moneyless, devious, female and financial problems. "
                  "If strong: blessed with son, intelligent, well educated and wealthy.",
        "Rahu": "Crooked, misleading, anxious about progeny, stomach trouble, obstruction in education.",
        "Ketu": "Afraid of water, deprived of knowledge, suspicious, abdominal pain and little progeny.",
    },
}
GANDMOOL = ["Ashwini", "Magha", "Mool", "Mula", "Ashlesha", "Jyeshtha", "Revati"]

GOCHAR_AUSPICIOUS = {
    "Sun": [3, 6, 10, 11], "Moon": [1, 3, 6, 7, 10, 11],
    "Mars": [3, 6, 11], "Saturn": [3, 6, 11], "Rahu": [3, 6, 11], "Ketu": [3, 6, 11],
    "Mercury": [2, 4, 6, 8, 10, 11], "Jupiter": [2, 5, 7, 9, 11],
    "Venus": [1, 2, 3, 4, 5, 8, 9, 11, 12],
}
GOCHAR_INAUSPICIOUS = {
    "Sun": [4, 5, 9, 12], "Moon": [5, 9, 12, 2, 4, 8],
    "Mars": [12, 9, 5], "Saturn": [12, 9, 5], "Rahu": [12, 9, 5], "Ketu": [12, 9, 5],
    "Mercury": [5, 3, 9, 1, 8, 12], "Jupiter": [12, 4, 3, 10, 8],
    "Venus": [6, 7, 10],
}

DASHA_PRINCIPLES = [
    "The planet gives prominent results according to its strength, the house it occupies, "
    "houses it aspects, houses it rules, and its natural karakatwa during its dasha.",
    "Planets in Sheershodya signs (3, 5, 6, 7, 8, 11) give results at the beginning of dasha; "
    "Prishtodya signs (1, 2, 4, 9, 10) at the end; Ubhayodaya (12th) throughout.",
    "Retrograde planets reverse the early/middle/late delivery sequence (Parashar dreshkana rule).",
    "Mixed auspicious and inauspicious causes produce mixed dasha results; whichever side is "
    "stronger dominates.",
    "When the Sun transits the sign of the antardasha lord, that lord's results manifest clearly.",
    "Coordinate gochar with the running dasha; transit alone does not override birth-chart strength.",
]

PANCHMAHAPURUSHA = {
    "Ruchaka": {"planet": "Mars", "signs": ["Aries", "Scorpio", "Capricorn"], "houses": [1, 4, 7, 10],
                "result": "Brave, commander, conqueror of enemies, wealthy king-like native."},
    "Bhadra": {"planet": "Mercury", "signs": ["Gemini", "Virgo"], "houses": [1, 4, 7, 10],
               "result": "Long-lived, learned, eloquent, honoured, blessed with land and comforts."},
    "Hamsa": {"planet": "Jupiter", "signs": ["Sagittarius", "Pisces", "Cancer"], "houses": [1, 4, 7, 10],
              "result": "Virtuous, wise, fair, king-like, blessed with good wife and progeny."},
    "Malavya": {"planet": "Venus", "signs": ["Taurus", "Libra", "Pisces"], "houses": [1, 4, 7, 10],
                "result": "Luxurious, fond of pleasures, vehicles, gems, and a beautiful spouse."},
    "Sasa": {"planet": "Saturn", "signs": ["Capricorn", "Aquarius", "Libra"], "houses": [1, 4, 7, 10],
             "result": "Command over servants, authority over villages/towns, disciplined ruler type."},
}


def _clean(t: str) -> str:
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^THE COMPLETE BOOK OF INDIAN PREDICTIVE ASTROLOGY\s*", "", t, flags=re.I)
    t = re.sub(r"========== PAGE \d+ ==========.*?ASTROLOGY\s*", " ", t, flags=re.I)
    return t


def _sanitize_planet_text(txt: str, planet: str) -> str:
    """Drop OCR bleed (lord-in-house TOC, wrong planet concatenation)."""
    txt = _clean(txt)
    txt = re.split(
        r"Ekadshesh Position|Position In Various Houses|\s-------+\s|Impact Of Lord Of",
        txt,
        maxsplit=1,
        flags=re.I,
    )[0]
    for other in PLANETS:
        if other == planet:
            continue
        parts = re.split(rf"\b{re.escape(other)}\s*-\s*", txt, maxsplit=1)
        if len(parts) > 1 and parts[0].strip():
            txt = parts[0]
    return _clean(txt)


def parse_lagna_signs(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    pat = re.compile(
        r"(Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|Capricorn|Aquarius|Pisces)"
        r"\s+[Aa]scendant\s*/\s*birth\s*sign\s*(.*?)(?="
        r"(?:Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|Capricorn|Aquarius|Pisces)"
        r"\s+[Aa]scendant\s*/\s*birth\s*sign|Ghaat chakr\s*\n\nFor natives of Pisces|========== PAGE 8)",
        re.S | re.I,
    )
    for m in pat.finditer(text):
        sign = m.group(1).title()
        body = _clean(m.group(2))
        body = re.sub(r"========== PAGE \d+ ==========.*?ASTROLOGY\s*", " ", body)
        body = re.split(r"Ghaat chakr", body, maxsplit=1, flags=re.I)[0].strip()
        if len(body) > 120:
            out[sign] = body
    return out


def parse_planet_in_house(text: str) -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {h: {} for h in range(1, 13)}
    impact_pats = [
        r"The Impact Of Planets Located In The (\w+)",
        r"Impact Of The Planets In The (\w+) House",
        r"Results Of Planets Placed In The (\w+) House",
    ]
    for h, label in HOUSE_NAMES.items():
        header = f"{label} OF HOROSCOPE"
        candidates = list(re.finditer(rf"^{re.escape(header)}\s*$", text, re.I | re.M))
        if not candidates:
            candidates = list(re.finditer(rf"\b{re.escape(header)}\b", text, re.I))
        start = None
        for m in reversed(candidates):
            snippet = text[m.start(): m.start() + 6000]
            if re.search(r"Impact Of Planets|The Impact Of Planets", snippet, re.I):
                start = m.start()
                break
        if start is None and candidates:
            start = candidates[-1].start()
        if start is None:
            continue
        chunk_end = start + len(header)
        if h < 12:
            nxt_label = f"{HOUSE_NAMES[h + 1]} OF HOROSCOPE"
            nxt = re.search(
                rf"^{re.escape(nxt_label)}\s*$",
                text[chunk_end:],
                re.I | re.M,
            )
        else:
            nxt = re.search(r"IMPORTANT AUSPICIOUS", text[chunk_end:], re.I)
        chunk = text[start: chunk_end + (nxt.start() if nxt else 14000)]
        sub = chunk
        for pat in impact_pats:
            imp = re.search(pat, chunk, re.I)
            if imp:
                sub = chunk[imp.end():]
                break
        else:
            continue
        lord_sec = re.search(
            r"Impact Of Lord Of|Impact Of Lagnesh|Dwadshesh Position|Relation Of \w+esh",
            sub,
            re.I,
        )
        if lord_sec:
            sub = sub[: lord_sec.start()]
        for pl in PLANETS:
            others = "|".join(re.escape(p) for p in PLANETS if p != pl)
            pm = re.search(rf"^{pl}\s*-\s*(.+?)(?=^(?:{others})\s*-|\Z)", sub, re.S | re.M | re.I)
            if pm:
                out[h][pl] = _sanitize_planet_text(pm.group(1), pl)
    return out


def _ord_word(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", 6: "6th",
            7: "7th", 8: "8th", 9: "9th", 10: "10th", 11: "11th", 12: "12th"}[n]


def _house_occ_from_key(key: str) -> int | None:
    key = key.lower().strip()
    key = re.sub(r"^inthe\s+", "", key)
    if key in ("ascendant", "lagna"):
        return 1
    if key.startswith("twel"):
        return 12
    w = key.split()[0]
    return ORDINAL.get(w, ORDINAL.get(key.replace(" house", "")))


def parse_house_lord_in_house(text: str) -> dict[int, dict[int, str]]:
    out: dict[int, dict[int, str]] = {}
    lord_pats = [
        (1, r"Impact Of Lagnesh In Different Houses"),
        (2, r"Impact Of Lord Of 2nd House In Different\s*Houses"),
        (3, r"Impact Of Lord Of 3rd House In Different\s*Houses"),
        (4, r"The general result of Sukhesh being situated"),
        (5, r"The general result of Panchamesh being situated"),
        (6, r"Impact Of Lord Of 6th House In Different\s*Houses"),
        (7, r"Impact Of Lord Of 7th House In Different\s*Houses"),
        (8, r"Impact Of Lord Of 8th House In Different\s*Houses"),
        (9, r"Impact Of Lord Of 9th House In Different\s*Houses"),
        (10, r"Impact Of Lord Of 10th House In Different\s*Houses"),
        (11, r"lord of eleventh house in\s*various houses|Ekadshesh Position In Various Houses"),
        (12, r"Dwadshesh Position In Various Houses"),
    ]
    stop_pats = [
        r"Relation Of \w+esh",
        r"Impact Of Lord Of \d",
        r"Impact Of Lord Of Fourth",
        r"Impact Of Lord Of Eighth",
        r"Impact Of Lagnesh",
        r"Dwadshesh Position",
        r"^[A-Z][A-Z ]+HOUSE OF HOROSCOPE",
    ]

    def _parse_chunk(chunk: str) -> dict[int, str]:
        entries: dict[int, str] = {}
        chunk = re.sub(r"========== PAGE \d+ ==========.*?ASTROLOGY\s*", " ", chunk, flags=re.I)
        patterns = [
            r"In the ([a-z0-9]+(?:\s+[a-z]+)?)\s*-\s*(?:then\s+)?(.+?)(?=In the [a-z0-9]|Inthe [a-z0-9]|In tenth|The eleventh|$)",
            r"In tenth house\s*-\s*(?:then\s+)?(.+?)(?=In the [a-z0-9]|Inthe [a-z0-9]|Relation Of|The eleventh|$)",
            r"Inthe ([a-z0-9]+(?:\s+[a-z]+)?)\s*-\s*(?:then\s+)?(.+?)(?=Inthe [a-z0-9]|In the [a-z0-9]|in the [a-z0-9]|$)",
            r"In the ascendant\s*-\s*(?:then\s+)?(.+?)(?=In the |In second|Inthe |Relation Of|$)",
            r"In the lagna\s*-\s*(?:then\s+)?(.+?)(?=In the |In second|Inthe |Relation Of|$)",
            r"The eleventh house\s*-\s*(?:then\s+)?(.+?)(?=In the twelfth|In the |Relation Of|$)",
            r"in the ([a-z0-9]+(?:\s+[a-z]+)?)\s*-\s*(?:then\s+)?(.+?)(?=In the |Inthe |in the [a-z0-9]|Relation Of|$)",
        ]
        for pat in patterns:
            for em in re.finditer(pat, chunk, re.S | re.I):
                if em.lastindex == 2:
                    occ = _house_occ_from_key(em.group(1))
                    body = em.group(2)
                elif "eleventh" in pat:
                    occ = 11
                    body = em.group(1)
                elif "tenth house" in pat:
                    occ = 10
                    body = em.group(1)
                elif "ascendant" in pat or "lagna" in pat:
                    occ = 1
                    body = em.group(1)
                else:
                    continue
                if occ and body.strip():
                    entries[occ] = _clean(body)
        return entries

    for lord_h, pat in lord_pats:
        candidates = list(re.finditer(pat, text, re.I))
        best_entries: dict[int, str] = {}
        for m in reversed(candidates):
            tail = text[m.end(): m.end() + 12000]
            nxt = None
            for sp in stop_pats:
                nm = re.search(sp, tail, re.I | re.M)
                if nm and (nxt is None or nm.start() < nxt.start()):
                    nxt = nm
            chunk = tail[: nxt.start() if nxt else 12000]
            entries = _parse_chunk(chunk)
            if len(entries) >= len(best_entries):
                best_entries = entries
            if len(entries) >= 8:
                break
        if best_entries:
            out[lord_h] = best_entries
    return out


def parse_yogas(text: str) -> list[dict]:
    yogas: list[dict] = []
    candidates = list(re.finditer(r"IMPORTANT AUSPICIOUS\s+COMBINATIONS", text, re.I | re.M))
    if not candidates:
        return yogas
    chunk_m = candidates[-1]
    tail = text[chunk_m.end():]
    end_m = re.search(r"Panchmahapurusha|PANCHMAHAPURUSHA|VIMSHOTTARI DASHA", tail, re.I)
    chunk = text[chunk_m.start(): chunk_m.end() + (end_m.start() if end_m else 90000)]
    for ym in re.finditer(
        r"([A-Za-z][A-Za-z \-~]+?\s+Yoga)\s*[~-]\s*(If .+?)(?=\n[A-Za-z][A-Za-z \-~]{1,20}\s+Yoga\s*[~-]|Panchmahapurusha|$)",
        chunk,
        re.S,
    ):
        name = _clean(ym.group(1))
        rule = _clean(ym.group(2))
        res_m = re.search(r"due to which the person (.+?)(?=\.|$)", rule, re.I)
        result = res_m.group(1).strip() if res_m else ""
        yogas.append({"name": name, "rule": rule, "result": result})
    return yogas


def parse_nakshatra_effects(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    candidates = list(re.finditer(r"Effects Of Birth Nakshtra|Effects of birth Nakshtra", text, re.I))
    if not candidates:
        return out
    m = candidates[-1]
    chunk = text[m.start(): m.start() + 18000]
    aliases = [
        ("Ashwini", r"Ashwani|Ashwini"),
        ("Bharani", r"Bharani"),
        ("Krittika", r"Kritika|Krittika"),
        ("Rohini", r"Rohini"),
        ("Mrigashira", r"Mrigashira|Mrigshira"),
        ("Ardra", r"Ardra"),
        ("Punarvasu", r"Punarvasu"),
        ("Pushya", r"Pushya"),
        ("Ashlesha", r"Aashalesha|Ashlesha"),
        ("Magha", r"Magha"),
        ("Purva Phalguni", r"Purva Phalguni"),
        ("Uttara Phalguni", r"Uttara Phalguni"),
        ("Hasta", r"Hasta"),
        ("Chitra", r"Chitra"),
        ("Swati", r"Swati"),
        ("Vishakha", r"Visakha|Vishakha"),
        ("Anuradha", r"Anuradha"),
        ("Jyeshtha", r"Jyestha|Jyeshtha"),
        ("Mula", r"Mool|Mula"),
        ("Purva Ashadha", r"Purvashaadh|Purva Ashadha"),
        ("Uttara Ashadha", r"Uttarashad|Uttara Ashadha|Uttar Ashadha"),
        ("Shravana", r"Shravan|Shravana"),
        ("Dhanishtha", r"Dhanishtha|Dhanishta"),
        ("Shatabhisha", r"Shatabhisha|Shatbhisha"),
        ("Purva Bhadrapada", r"Purva Bhadrapada|Purva Bhadrapad"),
        ("Uttara Bhadrapada", r"Uttara Bhadrapada|Uttar Bhadrapad"),
        ("Revati", r"Revathi|Revati"),
    ]
    for canon, alt in aliases:
        pm = re.search(
            rf"(?:{alt})\s*-\s*(.+?)(?=(?:Ashwani|Ashwini|Bharani|Kritika|Krittika|Rohini|Mrig|Ardra|Punarvasu|Pushya|Aash|Ashlesha|Magha|Hasta|Chitra|Swati|Visakha|Vishakha|Anuradha|Jyestha|Jyeshtha|Mool|Mula|Purvashaadh|Uttarashad|Revathi|Revati|Shravan|Shravana|Dhanishtha|Shatabhisha|Purva Bhad|Uttara Bhad|Uttar Bhad)\s*-|If the lord planet|========== PAGE)",
            chunk, re.S | re.I,
        )
        if pm:
            out[canon] = _clean(pm.group(1))
    return out


def main() -> None:
    text = OCR.read_text(encoding="utf-8", errors="ignore")
    pih = parse_planet_in_house(text)
    for h, pls in MANUAL_PLANET_IN_HOUSE.items():
        pih.setdefault(h, {}).update(pls)
    data = {
        "source": "The Complete Book of Indian Predictive Astrology - Krishan Kant Bhardwaj (2021)",
        "ocr_path": str(OCR),
        "lagna_signs": parse_lagna_signs(text),
        "planet_in_house": {str(k): v for k, v in pih.items()},
        "house_lord_in_house": {str(k): {str(a): b for a, b in v.items()} for k, v in parse_house_lord_in_house(text).items()},
        "yogas": parse_yogas(text),
        "nakshatra_effects": parse_nakshatra_effects(text),
        "gandmool_nakshatras": GANDMOOL,
        "gochar_auspicious": GOCHAR_AUSPICIOUS,
        "gochar_inauspicious": GOCHAR_INAUSPICIOUS,
        "dasha_principles": DASHA_PRINCIPLES,
        "panchmahapurusha": PANCHMAHAPURUSHA,
        "transit_rules": [
            "Weak birth planets fail to give special auspicious transit results even in good gochar houses.",
            "Strong birth planets resist special inauspicious transit results even in bad gochar houses.",
            "Exalted/own/friendly sign planets resist bad transit houses; debilitated/enemy/combust fail in good houses.",
            "No vedha between Sun-Saturn and Moon-Mercury pairs.",
            "Retrograde/direct station intensifies transit results.",
        ],
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    filled = sum(1 for h in data["planet_in_house"].values() if h)
    print(f"lagna_signs={len(data['lagna_signs'])} planet_in_house_houses={filled} "
          f"house_lord_maps={len(data['house_lord_in_house'])} yogas={len(data['yogas'])} "
          f"nakshatras={len(data['nakshatra_effects'])}")
    print(f"written -> {OUT}")


if __name__ == "__main__":
    main()
