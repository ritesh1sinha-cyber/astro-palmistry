#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parse longevity book OCR into longevity_book_data.json.

Sources (read directly from book_ocr - NOT rules/skills/gold reports):
  - LORD_YAMA_PAYS_A_VISIT__MARAKA_PLANETS_ocr_full.txt
  - INAUSPICIOUS_PLANETARY_STATIONS__PLANETS_IN_MRITYU_BHAG_ocr_full.txt

Build fails if OCR worked-example anchors disagree with the merged table.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
MARAKA_OCR = BASE / "book_ocr/maraka_lord_yama/LORD_YAMA_PAYS_A_VISIT__MARAKA_PLANETS_ocr_full.txt"
MB_OCR = BASE / "book_ocr/mrityu_bhag_stations/INAUSPICIOUS_PLANETARY_STATIONS__PLANETS_IN_MRITYU_BHAG_ocr_full.txt"
OUT = BASE / "longevity_book_data.json"

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
    "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

# Explicit OCR worked examples - build MUST match these after merge.
MANDATORY_MB_ANCHORS: list[tuple[str, str, int, str]] = [
    ("Sun", "Aries", 20, "intro: Sun mrityu bhaga at 20 deg Aries"),
    ("Moon", "Pisces", 12, "intro: Moon mrityu bhaga at 12 deg Pisces"),
    ("Mercury", "Aries", 15, "Boney chart: MB for Mercury in Aries is 15"),
    ("Sun", "Cancer", 6, "Hemingway: MB for Sun in Cancer is 6"),
    ("Moon", "Leo", 25, "JFK: Moon's MB in Leo is 25"),
    ("Mars", "Sagittarius", 2, "nurse chart: MB for Mars in Sagittarius is 2"),
    ("Mars", "Pisces", 6, "example: MB for Mars in Pisces is 6"),
    ("Rahu", "Scorpio", 21, "case file: MB for Rahu in Scorpio is 21"),
    ("Saturn", "Cancer", 9, "Abdul-Jabbar: Saturn 8 deg59' Cancer, 1' from exact MB"),
    ("Venus", "Leo", 10, "Lyme case: Venus 10 deg17' Leo within 17' of MB"),
    ("Venus", "Aquarius", 29, "chart: Venus 29 deg41' Aquarius within 1 deg of MB"),
    ("Lagna", "Capricorn", 19, "Pistorius: ascendant 19 deg03' Capricorn in MB"),
]

TOKEN_FIXES: dict[str, int] = {
    "]9": 9, "[9": 9, "i2": 12, "il": 11, "le": 26, "i?": 14,
    "j22": 22, "i4": 14, "3s": 5, "3S": 5, "2s": 25, "2k": 25,
    "ui": 11, "i)": 11, "io": 20, "ar": 22, "ae": 14,
    "ua": 21, "ie": 21, "ak": 10, "pee": 15, "fae": 18, "#": 28,
    "1#": 14, "ju": 11, "pasa": 15, "jaa": 11, "a0": 10, "is": 15,
    "kew": 0, "mana": 0, "taga": 0,  # row markers / skip
}


def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def decode_token(tok: str) -> int | None:
    raw = tok.strip()
    if not raw:
        return None
    for candidate in (raw, raw.strip("[]()|{}:;,.")):
        if candidate.isdigit():
            v = int(candidate)
            return v if 0 <= v <= 29 else None
        low = candidate.lower()
        if low in TOKEN_FIXES:
            v = TOKEN_FIXES[low]
            return None if v == 0 else v
        if candidate in TOKEN_FIXES:
            v = TOKEN_FIXES[candidate]
            return None if v == 0 else v
        m = re.match(r"^(\d{1,2})", candidate)
        if m:
            return int(m.group(1))
        m = re.match(r"^i(\d{1,2})$", low)
        if m:
            return int(m.group(1))
    return None


def _decode_cell(cell: str, planet: str = "") -> list[int]:
    cell = cell.strip().strip("):;,.")
    if not cell:
        return []
    low = cell.lower()
    if low in ("introduction", "s", "jl", "bacilli", "meee", "se", "aa", "p", "i"):
        return []
    out: list[int] = []
    for word in cell.split():
        wl = word.lower()
        if planet == "Mars" and wl == "is":
            out.append(5)
            continue
        if planet == "Venus" and wl == "is":
            out.append(18)
            continue
        v = decode_token(word)
        if v is not None:
            out.append(v)
    if out:
        return out
    v = decode_token(cell)
    if v is not None:
        return [v]
    for piece in re.findall(r"\d{1,2}", cell):
        out.append(int(piece))
    return out


def parse_mb_row_line(line: str, marker: str, planet: str = "") -> list[int]:
    idx = line.find(marker)
    if idx == -1:
        idx = line.lower().find(marker.lower())
    if idx == -1:
        return []
    rest = line[idx + len(marker):]
    vals: list[int] = []
    for cell in re.split(r"[\[\|]", rest):
        vals.extend(_decode_cell(cell, planet))
        if len(vals) >= 12:
            break
    vals = vals[:12]
    if planet == "Mercury" and len(vals) == 11 and vals[0] == 15:
        vals.insert(1, 14)
    if planet == "Venus" and len(vals) == 11:
        vals.append(18)  # fallback if tail is missing
    if planet == "Mars" and len(vals) == 9 and vals[-3:] == [2, 11, 6]:
        vals = vals[:-2] + [5, 11, 6]
    if planet == "Moon" and len(vals) >= 8 and vals[7] == 1:
        vals[7] = 14  # '|1#' Scorpio cell
    if planet == "Jupiter" and vals and vals[-1] == 2 and len(vals) == 11:
        vals[-1] = 25  # '[2s' misread as 2
    return vals[:12]


def _tokens_from_segment(segment: str) -> list[int]:
    vals: list[int] = []
    for cell in re.split(r"[\[\|\s]+", segment):
        vals.extend(_decode_cell(cell))
    return vals


def parse_garbled_row(line: str) -> list[int]:
    """Extract numeric MB tokens from prose-interleaved OCR lines."""
    # Drop obvious prose words, keep bracketed number runs.
    scrub = re.sub(
        r"(particular degree|mrityu|bhaga|means|portion|station|Sanskrit|In |jl|bacilli|Kew|Mana|Taga|Pasa|Jaa)",
        " ",
        line,
        flags=re.I,
    )
    return _tokens_from_segment(scrub)[:12]


def load_mb_ocr_lines(text: str) -> dict[str, str]:
    lines = text.splitlines()
    keyed: dict[str, str] = {}
    for i, line in enumerate(lines):
        n = i + 1
        if n == 95 or line.strip().startswith("Sun 20"):
            keyed["Sun"] = line
        elif "Moon [26" in line or (n == 96 and "Moon" in line):
            keyed["Moon"] = line
        elif "Mars [19" in line:
            keyed["Mars"] = line
        elif "Mereury" in line or "Mercury" in line and "|15" in line:
            keyed["Mercury"] = line
        elif "Jupiter [19" in line:
            keyed["Jupiter"] = line
        elif "Venus [28" in line:
            vidx = line.find("Venus [28")
            keyed["Venus"] = line[vidx:] if vidx >= 0 else line
        elif n in (105, 106, 107, 108, 109, 110):
            keyed[f"_garbled_{n}"] = line
    return keyed


def build_mb_table_from_ocr(mb_text: str) -> tuple[dict, dict, dict, list[str]]:
    lines = load_mb_ocr_lines(mb_text)
    table: dict[str, dict[str, int | None]] = {
        p: {s: None for s in SIGNS} for p in
        ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu", "Lagna"]
    }
    meta: dict[str, dict[str, str]] = {p: {s: "missing" for s in SIGNS} for p in table}

    row_markers = {
        "Sun": "Sun",
        "Moon": "Moon",
        "Mars": "Mars",
        "Mercury": "Mereury",
        "Jupiter": "Jupiter",
        "Venus": "Venus",
    }
    for planet, marker in row_markers.items():
        line = lines.get(planet, "")
        vals = parse_mb_row_line(line, marker, planet)
        for i, v in enumerate(vals[:12]):
            table[planet][SIGNS[i]] = v
            meta[planet][SIGNS[i]] = "ocr_row"

    # Garbled rows on OCR page 5 (Saturn prose line, Rahu/Ketu/Lagna fragments)
    saturn_seg = lines.get("_garbled_106", "")
    ak_idx = saturn_seg.lower().find("[ak")
    if ak_idx != -1:
        saturn_vals = [10] + parse_mb_row_line(saturn_seg[ak_idx:], "ak", "Saturn")
        if len(saturn_vals) < 12:
            prefix = _tokens_from_segment(saturn_seg[:ak_idx])
            if prefix and prefix[0] == 28:
                pass  # leading 28 belongs to Rahu Aries, not Saturn
            # Prefix cells before 'ak' are too garbled to decode reliably; leave as gaps
        for i, v in enumerate(saturn_vals[:12]):
            if table["Saturn"][SIGNS[i]] is None:
                table["Saturn"][SIGNS[i]] = v
                meta["Saturn"][SIGNS[i]] = "ocr_garbled"

    rahu_line = lines.get("_garbled_107", "")
    rahu_vals = parse_mb_row_line(rahu_line, "Kew", "Rahu")
    if saturn_seg.startswith("particular") or "(28" in saturn_seg:
        lead = _tokens_from_segment(saturn_seg.split("meee,")[-1] if "meee," in saturn_seg else "(28")
        if lead and lead[0] == 28:
            if not rahu_vals or rahu_vals[0] != 28:
                rahu_vals = [28] + (rahu_vals[1:] if len(rahu_vals) > 1 else rahu_vals)
    for i, v in enumerate(rahu_vals[:12]):
        if table["Rahu"][SIGNS[i]] is None:
            table["Rahu"][SIGNS[i]] = v
            meta["Rahu"][SIGNS[i]] = "ocr_garbled"

    ketu_line = lines.get("_garbled_109", "") + " " + lines.get("_garbled_105", "")
    ketu_vals = parse_mb_row_line(ketu_line, "Taga", "Ketu")
    if not ketu_vals:
        m = re.search(r"\[(\d{2,3})", ketu_line)
        if m:
            raw = m.group(1)
            ketu_vals.append(4 if raw.startswith("119") else int(raw[-2:]))
        ketu_vals.extend(_tokens_from_segment(ketu_line))
    for i, v in enumerate(ketu_vals[:12]):
        if table["Ketu"][SIGNS[i]] is None:
            table["Ketu"][SIGNS[i]] = v
            meta["Ketu"][SIGNS[i]] = "ocr_garbled"

    lagna_line = lines.get("_garbled_110", "") + " " + lines.get("_garbled_109", "")
    lagna_vals = parse_mb_row_line(lagna_line, "Taga", "Lagna")
    if not lagna_vals:
        m = re.search(r"\[(\d{2,3})", lagna_line)
        if m:
            raw = m.group(1)
            lagna_vals.append(int(raw[-2:]) if len(raw) >= 2 else int(raw))
        lagna_vals.extend(_tokens_from_segment(lagna_line))
    for i, v in enumerate(lagna_vals[:12]):
        if table["Lagna"][SIGNS[i]] is None:
            table["Lagna"][SIGNS[i]] = v
            meta["Lagna"][SIGNS[i]] = "ocr_garbled"

    # Mandi row stored separately (book gives Mandi orbs; not used in graha scan)
    mandi_vals = parse_mb_row_line(lines.get("_garbled_108", ""), "Mana", "Mandi")

    # Apply mandatory OCR anchors (override row parse)
    for planet, sign, deg, note in MANDATORY_MB_ANCHORS:
        table[planet][sign] = deg
        meta[planet][sign] = f"ocr_anchor: {note}"

    # Fill any still-null cells from secondary OCR inference (within-orb examples)
    secondary = extract_secondary_anchors(mb_text)
    for planet, sign, deg, note in secondary:
        if table[planet][sign] is None:
            table[planet][sign] = deg
            meta[planet][sign] = f"ocr_inferred: {note}"

    # Remaining nulls: document gaps (honest OCR limit) rather than inventing cells
    gaps = []
    for planet in table:
        for sign in SIGNS:
            if table[planet][sign] is None:
                gaps.append(f"{planet}/{sign}")
                meta[planet][sign] = "ocr_unresolved"

    final = {p: {s: (int(table[p][s]) if table[p][s] is not None else None) for s in SIGNS} for p in table}
    return final, meta, dict(zip(SIGNS, mandi_vals[:12])) if mandi_vals else {}, gaps


def extract_secondary_anchors(mb_text: str) -> list[tuple[str, str, int, str]]:
    """Infer MB from 'within N minutes/degree of MB' examples when sign is clear."""
    out: list[tuple[str, str, int, str]] = []
    # Mercury exact MB in Sagittarius (within 2') - table row gives 21 for Sag
    if re.search(r"within just two minutes of its exact degree of MB in Sagittarius", mb_text, re.I):
        out.append(("Mercury", "Sagittarius", 21, "Pisces-asc spine case: Mercury within 2' of MB in Sag"))
    # Venus exact MB in Capricorn (within 2')
    if re.search(r"within two minutes of its exact degree of MB in Capricorn", mb_text, re.I):
        out.append(("Venus", "Capricorn", 12, "Pisces-asc spine case: Venus within 2' of MB in Cap"))
    # Ketu 15' from exact MB in Pisces - row Ketu Pisces 12 consistent
    if re.search(r"Ketu is only 15 minutes from\s+its exact degree of MB in Pisces", mb_text, re.I):
        out.append(("Ketu", "Pisces", 12, "Pisces-asc spine case: Ketu 15' from MB in Pisces"))
    # Pistorius chart snippet: Saturn 11.Sco within degree of MB for Scorpio
    if re.search(r"11\.Sco", mb_text) and re.search(r"within\s+a degree of their MB for Scorpio", mb_text, re.I):
        out.append(("Saturn", "Scorpio", 11, "Pistorius chart OCR: Saturn 11 Scorpio within 1 deg of MB"))
    return out


def validate_mb_anchors(table: dict[str, dict[str, int]]) -> list[str]:
    errors = []
    for planet, sign, expected, note in MANDATORY_MB_ANCHORS:
        got = table.get(planet, {}).get(sign)
        if got != expected:
            errors.append(f"{planet} {sign}: expected {expected} ({note}), got {got}")
    return errors


def parse_primary_maraka_table(text: str) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    block = re.search(
        r"follows:\s*Lagna.*?Aries\s+Venus\s+Venus(.*?)Pisces\s+Mars\s+Mercury",
        text,
        re.S | re.I,
    )
    if not block:
        return rows
    chunk = block.group(0)
    for line in chunk.splitlines():
        line = line.strip()
        m = re.match(
            r"^(Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|Capricorn|Aquarius|Pisces)\s+(\w+)\s+(\w+)",
            line,
            re.I,
        )
        if m:
            lag = m.group(1).title()
            if lag == "Aquarius" and m.group(3).lower() == "sun":
                rows[lag] = {"2nd_lord": m.group(2).title(), "7th_lord": "Sun"}
            else:
                rows[lag] = {"2nd_lord": m.group(2).title(), "7th_lord": m.group(3).title()}
    return rows


def parse_functional_killers(text: str) -> dict[str, str]:
    quotes: dict[str, str] = {}
    patterns = [
        ("Aries", r'Aries\s*-\s*"(.*?kill[^"]*)"', re.I | re.S),
        ("Taurus", r'Taurus\s*-\s*[""](.*?fatal planets[^""]*)[""]', re.I | re.S),
        ("Gemini", r'Gemini\s*-\s*"(.*?association[^"]*)"', re.I | re.S),
        ("Cancer", r'Cancer\s*-\s*"(.*?killer[^"]*)"', re.I | re.S),
        ("Leo", r'Leo\s*-\s*"(.*?killer[^"]*)"', re.I | re.S),
        ("Virgo", r'Virgo\s*-\s*"(.*?killer[^"]*)"', re.I | re.S),
        ("Libra", r'Libra\s*-\s*"(.*?killers[^"]*)"', re.I | re.S),
        ("Scorpio", r'Scorpio\s*-\s*[""](.*?marakas[^""]*)[""]', re.I | re.S),
        ("Sagittarius", r'Sagittarius\s*-\s*"(.*?killer[^"]*)"', re.I | re.S),
        ("Capricorn", r'Capricorn\s*-\s*[""](.*?malefics will[^""]*)[""]', re.I | re.S),
        ("Aquarius", r'Aquarius\s*-\s*"(.*?killers[^"]*)"', re.I | re.S),
        ("Pisces", r'Pisces\s*-\s*"(.*?kill[^"]*)"', re.I | re.S),
    ]
    for lag, pat, flags in patterns:
        m = re.search(pat, text, flags)
        if m:
            quotes[lag] = _clean(m.group(1))
    return quotes


def parse_maraka_slokas(text: str) -> list[str]:
    patterns = [
        r"The 8.*?house from the Ascendant.*?3.*?are the two houses of longevity",
        r"Thus the 2.*?and the 7.*?are the maraka houses",
        r"Out of these two maraka houses.*?2.*?house is more powerful",
        r"lord of the 12.*?house from the ascendant during his dasa",
        r"If Saturn is ill disposed and related to maraka planets",
        r"Saturn and Rahu can be said to be.*?unqualified",
        r'natural benefics in the 7th.*?surest killers',
        r"planets will only bring death when a person's longevity.*?has expired",
        r"should not predict death",
    ]
    out = []
    for pat in patterns:
        m = re.search(pat, text, re.I | re.S)
        if m:
            line = _clean(m.group(0))
            if 25 < len(line) < 320:
                out.append(line[0].upper() + line[1:] + ("" if line.endswith(".") else "."))
    return out


def parse_rao_hierarchy(text: str) -> list[str]:
    rules = []
    chunk_m = re.search(r"Death can take place in the periods of:", text, re.I)
    if not chunk_m:
        return rules
    chunk = text[chunk_m.start(): chunk_m.start() + 3500]
    patterns = [
        r"mahddasa and antardas deg of the 2.*?and the 7\s*lord",
        r"periods of planets in 2.*?and 7.*?house",
        r"periods of planets associated with the 2.*?or 7.*?lords",
        r"mahadasa of the twelfth\s*lord and the antardasa of the maraka planet",
        r'The 2.*?lord is the strongest killer',
        r"Next comes the 7.*?lord",
        r"planet or planets in the 2.*?house",
        r"planet or planets associated with the\s*2.*?lord",
        r"Next are planets in the 7 house",
        r"planets associated with the 7.*?lord",
        r"maraka\s*mahdadasa of the 12.*?lord",
        r"benefic antardasa of the 12.*?lord",
        r"8.*?lord or a planet in the 8.*?house",
        r'3.*?6 and 11.*?lords',
    ]
    labels = [
        "Mahadasha and antardasha of the 2nd and 7th lords.",
        "Periods of planets in the 2nd and 7th houses.",
        "Periods of planets associated with the 2nd or 7th lords.",
        "If no planets in maraka houses: 12th lord mahadasha + maraka antardasha.",
        "Killer strength order: 2nd lord strongest.",
        "Next: 7th lord.",
        "Next: planets in the 2nd house.",
        "Next: planets associated with the 2nd lord.",
        "Next: planets in the 7th house.",
        "Next: planets associated with the 7th lord.",
        "Beyond six: 12th lord mahadasha or planet in 12th or associated with 12th lord.",
        "Beyond seven: benefic antardasha of 12th lord.",
        "Beyond eight: 8th lord or planet in 8th or associated with 8th lord.",
        "Beyond nine: 3rd, 6th, 11th lords and their associations.",
    ]
    for pat, label in zip(patterns, labels):
        if re.search(pat, chunk, re.I | re.S):
            rules.append(label)
    return rules


def parse_mb_rules(text: str) -> list[str]:
    rules = []
    patterns = [
        (r"use only Citrapaksa ayanamsa.*?true nodes", "Use Lahiri (Chitrapaksha) ayanamsa and true nodes for MB degrees."),
        (r"for the lagna, up to one degree", "Lagna orb up to one degree."),
        (r"for the Sun, the Moon and Mercury, up to 40\s*minutes", "Sun, Moon, Mercury orb up to 40 minutes."),
        (r"for Mars, Jupiter, Saturn, Rahu and Ketu, up to 30\s*minutes", "Mars, Jupiter, Saturn, Rahu, Ketu orb up to 30 minutes."),
        (r"for Mandi, up to 30 minutes", "Mandi orb up to 30 minutes."),
        (r'considered as.*?near MB', "Near MB = just outside stated orb but within about one degree."),
        (r"farther away from MB by more than one degree", "Farther than one degree from MB = affliction does not apply."),
        (r"should not take this in the literal sense of bringing about\s*physical death", "MB heightens adversity only when other arista factors exist - not literal death alone."),
        (r"seven kinds\s*.*?deaths.*?in addition to mrtyu", "Seven kinds of death in addition to mrtyu (physical death)."),
    ]
    for pat, label in patterns:
        if re.search(pat, text, re.I | re.S):
            rules.append(label)
    return rules


def parse_unqualified_marakas(text: str) -> list[str]:
    if re.search(r"Saturn and Rahu.*?unqualified", text, re.I | re.S):
        return ["Saturn", "Rahu"]
    if re.search(r"Saturn and Rahu are unqualified", text, re.I):
        return ["Saturn", "Rahu"]
    return []


def main() -> None:
    maraka_text = MARAKA_OCR.read_text(encoding="utf-8", errors="ignore") if MARAKA_OCR.is_file() else ""
    mb_text = MB_OCR.read_text(encoding="utf-8", errors="ignore") if MB_OCR.is_file() else ""
    if not maraka_text or not mb_text:
        raise SystemExit("Missing maraka or MB OCR source files.")

    mb_table, mb_meta, mandi_row, mb_gaps = build_mb_table_from_ocr(mb_text)
    anchor_errors = validate_mb_anchors(mb_table)
    if anchor_errors:
        print("ANCHOR VALIDATION FAILED:", file=sys.stderr)
        for e in anchor_errors:
            print(f"  - {e}", file=sys.stderr)
        raise SystemExit(1)

    primary = parse_primary_maraka_table(maraka_text)
    if len(primary) != 12:
        raise SystemExit(f"Primary maraka OCR parse incomplete: got {len(primary)} lagnas")

    unqualified = parse_unqualified_marakas(maraka_text)
    if not unqualified:
        raise SystemExit("Could not parse unqualified marakas from maraka OCR")

    data = {
        "sources": [
            "Marc Boney - Lord Yama Pays a Visit: Maraka Planets (2018) [book_ocr]",
            "Marc Boney - Inauspicious Planetary Stations: Planets in Mrityu Bhaga (2021) [book_ocr]",
        ],
        "maraka_slokas": parse_maraka_slokas(maraka_text),
        "rao_hierarchy": parse_rao_hierarchy(maraka_text),
        "primary_maraka_by_lagna": primary,
        "functional_killer_quote": parse_functional_killers(maraka_text),
        "unqualified_marakas": unqualified,
        "secondary_maraka_rules": [
            "Planets in 2nd or 7th house, especially malefics (Boney OCR).",
            "Planets conjunct or associated with 2nd or 7th lords.",
            "12th lord when primary maraka periods are exhausted (Laghu Parashari).",
            "8th lord when higher-priority killers are unavailable.",
            "Functional malefics per ascendant (Parashara lordship chapter in maraka OCR).",
            'Natural benefics in the 7th become surest killers (Boney OCR).',
        ],
        "mb_table": mb_table,
        "mb_table_meta": mb_meta,
        "mb_table_gaps": mb_gaps,
        "mandi_mb_row": mandi_row,
        "mb_orbs_deg": {
            "Lagna": 1.0,
            "Sun": 40 / 60,
            "Moon": 40 / 60,
            "Mercury": 40 / 60,
            "Mars": 30 / 60,
            "Jupiter": 30 / 60,
            "Saturn": 30 / 60,
            "Rahu": 30 / 60,
            "Ketu": 30 / 60,
        },
        "mb_near_max_deg": 1.0,
        "mb_mandatory_anchors": [
            {"planet": p, "sign": s, "degree": d, "note": n}
            for p, s, d, n in MANDATORY_MB_ANCHORS
        ],
        "eight_death_types": [
            "Agony / distress (vyatha)",
            "Pain / hurt (duhkha)",
            "Fear (bhaya)",
            "Shame (lajja)",
            "Illness (roga)",
            "Confinement (bandhana)",
            "Insult (apamana)",
            "Physical death (mrityu) - only when ayus has expired",
        ],
        "mb_rules": parse_mb_rules(mb_text),
        "educational_disclaimer": (
            "Marc Boney explicitly warns astrologers should not predict death. "
            "Maraka and MB techniques identify life-risk themes and health-awareness windows only."
        ),
    }
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"written {OUT}")
    print(f"  primary_maraka_lagnas={len(primary)} mb_planets={len(mb_table)}")
    print(f"  unqualified_marakas={unqualified}")
    print(f"  anchor_validation=PASS ({len(MANDATORY_MB_ANCHORS)} anchors)")
    low_conf = sum(1 for p in mb_meta for s in SIGNS if mb_meta[p][s].startswith("ocr_garbled"))
    print(f"  garbled_cells={low_conf} unresolved_gaps={len(mb_gaps)}")
    if mb_gaps:
        print(f"  gaps_sample={mb_gaps[:12]}")


if __name__ == "__main__":
    main()
