#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse Mehta Modern Techniques OCR into mehta_book_data.json (rules4)."""
from __future__ import annotations

import json
import re
from pathlib import Path

OCR = Path(__file__).resolve().parent / (
    "book_ocr/modern_techniques/MODERN_TECHNIQUES_ocr_full.txt"
)
OUT = Path(__file__).resolve().parent / "mehta_book_data.json"

HOUSE_WORDS = {
    1: r"First|1st|Ascendant|Lagna",
    2: r"Second|2nd",
    3: r"Third|3rd",
    4: r"Fourth|4th",
    5: r"Fifth|5th",
    6: r"Sixth|6th",
    7: r"Seventh|7th",
    8: r"Eighth|8th",
    9: r"Ninth|9th",
    10: r"Tenth|10th",
    11: r"Eleventh|11th",
    12: r"Twelfth|12th",
}

CONTAMINATION = (
    r"Horoscope of\b",
    r"Dr\.\s+\w",
    r"Gandhiji\b",
    r"Mahatma Gandhi\b",
    r"Nargis Dutt\b",
    r"Tagore\b",
    r"Yogas of the\b",
    r"Planets in the \d",
    r"Matching of Horoscopes\b",
    r"Chapter II\b",
    r"Chapter VIII\b",
    r"ANALYSING HOROSCOPE THROUGH MODERN TECHNIQUES",
)


def _clean(t: str) -> str:
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _sanitize_mehta_clause(text: str) -> str:
    """Remove OCR junk before storing or serving book lines."""
    if not text:
        return ""
    text = re.sub(
        r"={3,}\s*PAGE\s+\d+\s*={3,}.*?MODERN TECHNIQUES\s*",
        " ",
        text,
        flags=re.I | re.S,
    )
    for stop in CONTAMINATION:
        text = re.split(stop, text, maxsplit=1, flags=re.I)[0]
    text = re.sub(r"\b(Lag|Lagna|Mer|Ven|Jup|Sat|Ket|Rahu)\s*[\|\d].*", " ", text)
    text = re.sub(r"\b\d{1,2}:\d{2}\s*am\b.*", " ", text, flags=re.I)
    text = re.sub(r"\b(Porbandar|Calcutta|Mumbai|Long|Lat)\b.*", " ", text, flags=re.I)
    text = re.sub(r"\s+In the\s*$", "", text, flags=re.I)
    text = re.sub(r"\bd\?ridra\b", "daridra", text, flags=re.I)
    text = _clean(text)
    if not _is_valid_clause(text):
        return ""
    return text


def _is_valid_clause(text: str) -> bool:
    if len(text) < 28:
        return False
    if re.search(r"PAGE\s+\d+", text, re.I):
        return False
    if re.search(r"Horoscope of|Gandhiji|Nargis Dutt|Tagore", text, re.I):
        return False
    letters = sum(c.isalpha() for c in text)
    if letters / max(len(text), 1) < 0.45:
        return False
    if text.count("In the ") >= 3:
        return False
    return True


def _strip_chart_noise(t: str) -> str:
    t = re.sub(
        r"\b(?:Sun|Moon|Mars|Mer|Mercury|Jup|Jupiter|Ven|Venus|Sat|Saturn|Rahu|Ketu)\b.*?(?:House|Chapter)",
        " ",
        t,
        flags=re.I,
    )
    t = re.sub(r"\b\d{1,2}\s*(?:May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Jan|Feb|Mar|Apr)\s+\d{4}\b.*", " ", t)
    return _sanitize_mehta_clause(t)


def _house_from_header_line(line: str) -> int | None:
    line = line.strip()
    for h, words in HOUSE_WORDS.items():
        if re.search(rf"\b({words})\b", line, re.I):
            return h
    m = re.search(r"(?:In\s*the|Inthe)\s*(\d+)", line, re.I)
    if not m:
        return None
    digits = m.group(1)
    if digits in ("64", "6"):
        return 6
    if digits in ("34", "3"):
        return 3
    if digits in ("104", "10"):
        return 10
    if digits in ("108", "118", "11"):
        return 11
    if digits in ("24", "2"):
        return 2
    if digits in ("74", "7"):
        return 7
    if digits in ("84", "8"):
        return 8
    if digits in ("94", "9"):
        return 9
    if digits in ("124", "12"):
        return 12
    if len(digits) == 1:
        return int(digits)
    if digits.startswith("10"):
        return 10
    if digits.startswith("11"):
        return 11
    return None


def _split_by_house_headers(chunk: str, min_len: int = 28) -> dict[int, str]:
    out: dict[int, str] = {}
    markers: list[tuple[int, int, int]] = []
    for m in re.finditer(r"(?m)^(.{0,40}House)\s*,?\s*$", chunk):
        h = _house_from_header_line(m.group(1))
        if h is None:
            continue
        markers.append((m.start(), m.end(), h))
    for h, words in HOUSE_WORDS.items():
        for pat in (
            rf"(?m)^(?:In the |Inthe )?({words})\s+House\s*,?\s*$",
            rf"(?m)^({words})\s+House\s*,?\s*$",
        ):
            for m in re.finditer(pat, chunk, re.I):
                if not any(abs(m.start() - st) < 8 for st, _, _ in markers):
                    markers.append((m.start(), m.end(), h))
                break
    markers.sort(key=lambda x: x[0])
    dedup: list[tuple[int, int, int]] = []
    seen_h: set[int] = set()
    for st, en, h in markers:
        if h in seen_h:
            continue
        seen_h.add(h)
        dedup.append((st, en, h))
    for i, (st, en, h) in enumerate(dedup):
        nxt = dedup[i + 1][0] if i + 1 < len(dedup) else len(chunk)
        body = chunk[en:nxt]
        body = re.split(
            r"Planets in the|Chapter [IVX]+|Horoscope of|Yogas of the",
            body,
            maxsplit=1,
            flags=re.I,
        )[0]
        body = _strip_chart_noise(body)
        if len(body) >= min_len:
            out[h] = body
    return out


def parse_second_lord_in_house(text: str) -> dict[int, str]:
    m = re.search(r"Lord of two in different Houses", text, re.I)
    if not m:
        return {}
    chunk = text[m.end():]
    end = re.search(r"Planets in the 2|Chapter III|Third House", chunk, re.I)
    chunk = chunk[: end.start() if end else 12000]
    return _split_by_house_headers(chunk)


def _parse_planets_block(chunk: str) -> dict[str, str]:
    planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    out: dict[str, str] = {}
    for pl in planets:
        others = "|".join(re.escape(p) for p in planets if p != pl)
        pm = re.search(
            rf"(?m)^{pl}\s*(?:\n\n|:-\s*)(.+?)(?=^(?:{others})\s*(?:\n\n|:-)|\Z)",
            chunk,
            re.S | re.I,
        )
        if pm:
            cleaned = _strip_chart_noise(pm.group(1))
            if cleaned:
                out[pl] = cleaned
    return out


def parse_planets_in_house_section(text: str, start_pat: str, end_pat: str) -> dict[str, str]:
    m = re.search(start_pat, text, re.I)
    if not m:
        return {}
    chunk = text[m.end(): m.end() + 14000]
    end = re.search(end_pat, chunk, re.I)
    chunk = chunk[: end.start() if end else 14000]
    return _parse_planets_block(chunk)


PLANET_HOUSE_SECTIONS = [
    (1, r"Planets in the First House", r"Chapter II|Second House of|The Second House"),
    (2, r"Planets in the 2.{0,4} House", r"Chapter III|Third House|The Third House"),
    (3, r"Planets in the 3.{0,4} House", r"Chapter IV|Fourth House|The Fourth House"),
    (5, r"Planets in the 5.{0,4} House", r"Chapter VI|Sixth House|The Sixth"),
    (6, r"Planets in the Sixth", r"Chapter VII|Seventh House|The Seventh"),
    (7, r"Planets in the 7.{0,4} house", r"Chapter VIII|Eighth House|Matching of Horoscopes"),
    (9, r"Planets in the Ninth House", r"Chapter X|Tenth House|The Tenth"),
    (10, r'Planets in the 10.{0,4} House', r"Chapter XI|Eleventh House|The Eleventh"),
    (11, r'Planets in the 11.{0,4} House', r"Chapter XII|Twelfth House|The Twelfth"),
]


def parse_all_planets_in_houses(text: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for house, start, end in PLANET_HOUSE_SECTIONS:
        block = parse_planets_in_house_section(text, start, end)
        if block:
            out[str(house)] = block
    return out


def parse_lagna_lord_in_house(text: str) -> dict[int, str]:
    m = re.search(r"Results of Lagna Lord in different Houses", text, re.I)
    if not m:
        return {}
    chunk = text[m.end():]
    end = re.search(r"Planets in the First House", chunk, re.I)
    chunk = chunk[: end.start() if end else 18000]
    return _split_by_house_headers(chunk)


def parse_seventh_lord_in_house(text: str) -> dict[int, str]:
    m = re.search(r"Result of 7.? Lord in Different Houses", text, re.I)
    if not m:
        return {}
    chunk = text[m.end():]
    end = re.search(r"Planets in the 7|Matching of Horoscopes|Chapter VIII", chunk, re.I)
    chunk = chunk[: end.start() if end else 14000]
    return _split_by_house_headers(chunk, min_len=28)


def parse_tenth_lord_in_house(text: str) -> dict[int, str]:
    """10th lord placed in houses 1-12 (single lord, many placements)."""
    m = re.search(r"Lord of ten in various houses\s*:", text, re.I)
    if not m:
        return {}
    chunk = text[m.end():]
    end = re.search(
        r"Planets in the 10|Dasha of the Lord of Tenth|Lord of \d+\s+in",
        chunk,
        re.I,
    )
    chunk = chunk[: end.start() if end else 16000]
    return _split_by_house_headers(chunk)


def parse_planets_in_first_house(text: str) -> dict[str, str]:
    m = re.search(r"Planets in the First House", text, re.I)
    if not m:
        return {}
    chunk = text[m.end(): m.end() + 12000]
    end = re.search(r"Chapter II|SECOND HOUSE|Second House of", chunk, re.I)
    chunk = chunk[: end.start() if end else 12000]
    planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    out: dict[str, str] = {}
    for i, pl in enumerate(planets):
        others = "|".join(re.escape(p) for p in planets if p != pl)
        pm = re.search(
            rf"(?m)^{pl}\s*\n\n(.+?)(?=^(?:{others})\s*\n\n|\Z)",
            chunk,
            re.S | re.I,
        )
        if pm:
            cleaned = _strip_chart_noise(pm.group(1))
            if cleaned:
                out[pl] = cleaned
    return out


INTRO_STEPS = [
    "Step 1: Judge from lagna, Moon, and Sun; no prediction without Navamsha and dasha.",
    "Step 2: Count exalted planets and own-sign aspects; read lagna and Moon sign temperament.",
    "Step 3: Benefics favour kendras and trikonas; malefics work best in 3rd, 6th, and 11th.",
    "Step 4: Kendra-trikona lord links are among the strongest raja yogas.",
    "Step 5: Strong planets deliver opposite results to weak ones (dignity, house, AV bindus).",
    "Step 6: Dusthana lords (6, 8, 12) and their occupants strain material ease when afflicted.",
    "Step 7: Nakshatra of planet and dasha lord colours event quality.",
    "Step 8: Early benefic dashas (lagna lord, 9th lord, exalted planet) help education and start.",
    "Step 9: Group I lords (1,4,7,10,5,9,2,11) mixing with Group II (3,6,8,12) stress wealth.",
    "Step 10: Planet in own house or aspecting own sign helps even if debilitated (Phala Dipika).",
    "Step 11: Dual lordship resolves by moolatrikona house placement.",
    "Step 12: Judge any bhava by house, lord+dispositor, and karaka; check 6/8/12 from that house.",
]

GROUP_I = [1, 2, 4, 5, 7, 9, 10, 11]
GROUP_II = [3, 6, 8, 12]


def main() -> None:
    text = OCR.read_text(encoding="utf-8", errors="ignore")
    lagna_lord = parse_lagna_lord_in_house(text)
    second_lord = parse_second_lord_in_house(text)
    seventh_lord = parse_seventh_lord_in_house(text)
    first_house_planets = parse_planets_in_first_house(text)
    tenth_lord = parse_tenth_lord_in_house(text)
    planet_in_house = parse_all_planets_in_houses(text)
    if "1" not in planet_in_house and first_house_planets:
        planet_in_house["1"] = first_house_planets

    hlh: dict[str, dict[str, str]] = {
        "1": {str(k): v for k, v in lagna_lord.items()},
        "2": {str(k): v for k, v in second_lord.items()},
        "7": {str(k): v for k, v in seventh_lord.items()},
        "10": {str(k): v for k, v in tenth_lord.items()},
    }

    data = {
        "source": "Analysing Horoscope Through Modern Techniques - M.S. Mehta (rules4)",
        "ocr_path": str(OCR),
        "intro_steps": INTRO_STEPS,
        "group_i_houses": GROUP_I,
        "group_ii_houses": GROUP_II,
        "lagna_lord_in_house": {str(k): v for k, v in lagna_lord.items()},
        "second_lord_in_house": {str(k): v for k, v in second_lord.items()},
        "seventh_lord_in_house": {str(k): v for k, v in seventh_lord.items()},
        "tenth_lord_in_house": {str(k): v for k, v in tenth_lord.items()},
        "planet_in_first_house": first_house_planets,
        "planet_in_house": planet_in_house,
        "house_lord_in_house": hlh,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"lagna_lord={len(lagna_lord)} second_lord={len(second_lord)} "
        f"seventh_lord={len(seventh_lord)} tenth_lord={len(tenth_lord)} "
        f"planet_houses={len(planet_in_house)}"
    )
    junk = 0
    for section in (lagna_lord, seventh_lord, tenth_lord):
        for v in section.values():
            if "PAGE" in v or "Horoscope" in v:
                junk += 1
    print(f"junk_clauses_remaining={junk}")
    print(f"written -> {OUT}")


if __name__ == "__main__":
    main()
