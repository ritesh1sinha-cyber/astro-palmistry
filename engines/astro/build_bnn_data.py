#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse Avasthi Bhrigu Nandi Nadi OCR into bnn_book_data.json (rules24)."""
from __future__ import annotations

import json
import re
from pathlib import Path

OCR = Path(__file__).resolve().parent / (
    "book_ocr/bhrigu_nandi_nadi/BHRIGU_NANDI_NADI__ASTROLOGY_SIMPLIFIED_ocr_full.txt"
)
OUT = Path(__file__).resolve().parent / "bnn_book_data.json"

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

CONTAMINATION = (
    r"========== PAGE",
    r"BHRIGU NANDI NADI: ASTROLOGY SIMPLIFIED",
    r"Example \d+:",
    r"Querent picks number",
    r"Practical Application:",
)


def _clean(t: str) -> str:
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^:\s*", "", t)
    return t


def _is_valid_clause(text: str) -> bool:
    if len(text) < 24:
        return False
    if re.search(r"PAGE\s+\d+", text, re.I):
        return False
    letters = sum(c.isalpha() for c in text)
    if letters / max(len(text), 1) < 0.42:
        return False
    return True


def _sanitize_bnn_clause(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"={3,}\s*PAGE\s+\d+\s*={3,}.*?(?:BHRIGU NANDI|$)", " ", text, flags=re.I | re.S)
    text = re.sub(r"BHRIGU NANDI NADI:\s*ASTROLOGY SIMPLIFIED", " ", text, flags=re.I)
    text = re.sub(r"NADI:\s*ASTROLOGY SIMPLIFIED", " ", text, flags=re.I)
    for stop in CONTAMINATION:
        text = re.split(stop, text, maxsplit=1, flags=re.I)[0]
    text = re.sub(r"[\u00a9\u00ae@]\s*", " ", text)
    text = re.sub(r"\be\s+", " ", text)
    text = _clean(text)
    if not _is_valid_clause(text):
        return ""
    return text


def _norm_pair(a: str, b: str) -> str:
    x, y = sorted([a.title(), b.title()], key=str.lower)
    return f"{x}|{y}"


def _parse_sign_blocks(chunk: str) -> dict[str, str]:
    """Split a section into sign -> text using sign-specific headers only."""
    out: dict[str, str] = {}
    markers: list[tuple[int, str]] = []
    for sign in SIGNS:
        pats = [
            rf"(?m)^{re.escape(sign)}\s*:\s*$",
            rf"(?m)^{re.escape(sign)}\s*:\s*Personality",
            rf"(?m)^\w+\s+in\s+{re.escape(sign)}\b",
            rf"(?m)^\w+\s+Is\s+in\s+{re.escape(sign)}\b",
        ]
        for pat in pats:
            m = re.search(pat, chunk, re.I)
            if m:
                markers.append((m.start(), sign))
                break
    markers.sort(key=lambda x: x[0])
    dedup: list[tuple[int, str]] = []
    seen: set[str] = set()
    for pos, sign in markers:
        if sign in seen:
            continue
        seen.add(sign)
        dedup.append((pos, sign))
    for i, (pos, sign) in enumerate(dedup):
        nxt = dedup[i + 1][0] if i + 1 < len(dedup) else len(chunk)
        body = _sanitize_bnn_clause(chunk[pos:nxt])
        if body:
            out[sign] = body
    return out


def parse_combinations(text: str) -> dict[str, dict]:
    m = re.search(r"Combination\s+1\s*:", text, re.I)
    if not m:
        return {}
    chunk = text[m.start():]
    end = re.search(r"The Radiant Source:|Practical Application:", chunk, re.I)
    chunk = chunk[: end.start() if end else 120000]
    out: dict[str, dict] = {}
    parts = re.split(r"(?m)(Combination\s+\d+[\.\:]?\s*[^\n]+)", chunk)
    i = 1
    while i < len(parts) - 1:
        header = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        i += 2
        hm = re.match(r"Combination\s+(\d+)[\.\:]?\s*(.+)", header, re.I)
        if not hm:
            continue
        num = hm.group(1)
        label = hm.group(2).strip().rstrip(":")
        pls = re.findall(r"(Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)", label, re.I)
        if len(pls) < 2:
            continue
        a, b = pls[0].title(), pls[1].title()
        cleaned = _sanitize_bnn_clause(body)
        if not cleaned:
            continue
        key = _norm_pair(a, b)
        entry = {"num": num, "label": label, "a": a, "b": b, "text": cleaned}
        out.setdefault(key, []).append(entry)
        dir_key = f"{a}-{b}"
        out.setdefault(dir_key, []).append(entry)
    return out


def parse_pairs_159(text: str) -> dict[str, str]:
    """Planet pairs irrespective of degrees (1,5,9) and Venus/Mercury combo chapters."""
    out: dict[str, str] = {}
    sections = [
        (r"Moon Combination \(1,5,9\)", r"Mars in Different Houses from Jupiter|Understanding Mars"),
        (r"Venus Combination with Other Planets", r"Mars in 2nd from Venus|Jupiter \+ Venus"),
        (r"Mercury Combinations with Planets \(1,5,9", r"Mercury in Different Houses from Jupiter"),
        (r"Key Jupiter Combination \(1,5,9\)", r"Jupiter \+ Venus"),
    ]
    for start, end_pat in sections:
        m = re.search(start, text, re.I)
        if not m:
            continue
        chunk = text[m.end(): m.end() + 12000]
        end = re.search(end_pat, chunk, re.I)
        chunk = chunk[: end.start() if end else 12000]
        for pm in re.finditer(
            r"(?m)^(Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\s*[\-+\u2014]\s*"
            r"(Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\b",
            chunk,
            re.I,
        ):
            a, b = pm.group(1).title(), pm.group(2).title()
            nxt = re.search(
                r"(?m)^(Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\s*[\-+\u2014]\s*",
                chunk[pm.end():],
                re.I,
            )
            body = chunk[pm.end(): pm.end() + (nxt.start() if nxt else 2500)]
            cleaned = _sanitize_bnn_clause(body)
            if cleaned:
                out[_norm_pair(a, b)] = cleaned
        for tm in re.finditer(
            r"(?m)^(Jupiter|Venus|Mercury|Saturn)\s*\+\s*(Jupiter|Venus|Mercury|Saturn|Moon|Mars)\b",
            chunk,
            re.I,
        ):
            a, b = tm.group(1).title(), tm.group(2).title()
            nxt = re.search(r"(?m)^(?:Jupiter|Venus|Mercury|Saturn|\u00a9)\s", chunk[tm.end():], re.I)
            body = chunk[tm.end(): tm.end() + (nxt.start() if nxt else 2000)]
            cleaned = _sanitize_bnn_clause(body)
            if cleaned:
                out[_norm_pair(a, b)] = cleaned
    return out


def parse_planet_in_sign(text: str, planet: str, start_pat: str, end_pat: str) -> dict[str, str]:
    m = re.search(start_pat, text, re.I)
    if not m:
        return {}
    chunk = text[m.end(): m.end() + 25000]
    end = re.search(end_pat, chunk, re.I)
    chunk = chunk[: end.start() if end else 25000]
    if planet in ("Mars", "Jupiter", "Sun"):
        if planet == "Sun":
            chunk = re.split(r"Rashi impact can be seen", chunk, maxsplit=1, flags=re.I)[-1]
        return _parse_sign_blocks(chunk)
    out: dict[str, str] = {}
    for sign in SIGNS:
        for pat in (
            rf"(?m)^{planet}\s+in\s+{sign}\b",
            rf"(?m)^{planet}\s+Is\s+in\s+{sign}\b",
            rf"(?m)^Jupiter in {sign}\b" if planet == "Jupiter" else rf"(?m)^$",
        ):
            sm = re.search(pat, chunk, re.I)
            if not sm:
                continue
            nxt_sign = None
            for ns in SIGNS:
                if ns == sign:
                    continue
                nm = re.search(
                    rf"(?m)^(?:{planet}\s+in\s+{ns}|{planet}\s+Is\s+in\s+{ns}|{ns}\s*:\s*Personality|{ns}\s*:\s*$)",
                    chunk[sm.end():],
                    re.I,
                )
                if nm and (nxt_sign is None or nm.start() < nxt_sign):
                    nxt_sign = nm.start()
            body = chunk[sm.end(): sm.end() + (nxt_sign if nxt_sign else 3500)]
            cleaned = _sanitize_bnn_clause(body)
            if cleaned:
                out[sign] = cleaned
            break
    return out


def parse_house_from_jupiter(text: str, planet: str) -> dict[int, str]:
    pat = rf"{planet}\s+in\s+Different\s+Houses\s+from\s+Jupiter"
    m = re.search(pat, text, re.I)
    if not m:
        return {}
    chunk = text[m.end(): m.end() + 14000]
    end = re.search(
        rf"{planet}\s+Combinations|{planet}\s+in\s+Different\s+Signs|Understanding ",
        chunk,
        re.I,
    )
    chunk = chunk[: end.start() if end else 14000]
    out: dict[int, str] = {}
    for h in range(1, 13):
        ord_words = {
            1: r"1st", 2: r"2nd", 3: r"3rd", 4: r"4th", 5: r"5th", 6: r"6th",
            7: r"7th", 8: r"8th", 9: r"9th", 10: r"10th", 11: r"11th", 12: r"12th",
        }
        hm = re.search(rf"(?m)^{ord_words[h]}\s+House\s*[:\-]", chunk, re.I)
        if not hm:
            continue
        nxt = re.search(r"(?m)^(?:1st|2nd|3rd|\d+th)\s+House\s*[:\-]", chunk[hm.end():], re.I)
        body = chunk[hm.end(): hm.end() + (nxt.start() if nxt else 2000)]
        cleaned = _sanitize_bnn_clause(body)
        if cleaned:
            out[h] = cleaned
    return out


def parse_rahu_ketu_in_house(text: str, node: str) -> dict[int, str]:
    pat = rf"{node}\s+in\s+Different\s+Houses\s+from\s+Jupiter"
    m = re.search(pat, text, re.I)
    if not m:
        # Rahu section uses "4th House:" under Rahu in Different Houses from Jupiter area
        m = re.search(rf"{node}\s+in\s+Different\s+Houses", text, re.I)
    if not m:
        return {}
    chunk = text[m.end(): m.end() + 12000]
    end = re.search(rf"{node}\s+in\s+Different\s+Signs|Transit of Rahu", chunk, re.I)
    chunk = chunk[: end.start() if end else 12000]
    out: dict[int, str] = {}
    for h in range(1, 13):
        hm = re.search(rf"(?m)^{h}(?:st|nd|rd|th)\s+House\s*:", chunk, re.I)
        if not hm:
            continue
        nxt = re.search(r"(?m)^\d+(?:st|nd|rd|th)\s+House\s*:", chunk[hm.end():], re.I)
        body = chunk[hm.end(): hm.end() + (nxt.start() if nxt else 1800)]
        cleaned = _sanitize_bnn_clause(body)
        if cleaned:
            out[h] = cleaned
    return out


def parse_fourth_house_tenants(text: str) -> dict[str, str]:
    m = re.search(r"4th House: House, Mother,\s*Happiness, Academics", text, re.I)
    if not m:
        return {}
    chunk = text[m.end(): m.end() + 8000]
    end = re.search(r"5th House - Purva Punya|Happiness and Comfort of Home", chunk, re.I)
    chunk = chunk[: end.start() if end else 8000]
    out: dict[str, str] = {}
    for pl in PLANETS:
        pm = re.search(rf"(?m)^\s*{pl}\s*:\s*(.+?)(?=^(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\s*:|$)",
                       chunk, re.S | re.I)
        if pm:
            cleaned = _sanitize_bnn_clause(pm.group(1))
            if cleaned:
                out[pl] = cleaned
    return out


def parse_profession_signs(text: str) -> dict[str, str]:
    m = re.search(r"Saturn in Different Signs\s*:\s*Profession", text, re.I)
    if not m:
        return {}
    chunk = text[m.end(): m.end() + 12000]
    end = re.search(r"Professions by Ketu", chunk, re.I)
    chunk = chunk[: end.start() if end else 12000]
    out: dict[str, str] = {}
    for sign in SIGNS:
        sm = re.search(
            rf"(?m)^[^\n]*\b{re.escape(sign)}\s*:\s*(.+?)(?=(?:^|\n)[^\n]*\b(?:{'|'.join(SIGNS)})\s*:|Professions Related|\Z)",
            chunk,
            re.S | re.I,
        )
        if sm:
            cleaned = _sanitize_bnn_clause(sm.group(1))
            if cleaned:
                out[sign] = cleaned
    return out


def parse_node_in_sign(text: str, node: str) -> dict[str, str]:
    m = re.search(rf"{node}\s+in\s+Different\s+Signs", text, re.I)
    if not m:
        return {}
    chunk = text[m.end(): m.end() + 8000]
    end = re.search(r"Transit of Rahu|Rahu Transit|Professions by Ketu", chunk, re.I)
    chunk = chunk[: end.start() if end else 8000]
    out: dict[str, str] = {}
    for sign in SIGNS:
        sm = re.search(rf"(?m)^{sign}\s*:\s*", chunk, re.I)
        if not sm:
            continue
        nxt = re.search(rf"(?m)^(?:{'|'.join(SIGNS)})\s*:\s*", chunk[sm.end():], re.I)
        body = _sanitize_bnn_clause(chunk[sm.end(): sm.end() + (nxt.start() if nxt else 1200)])
        if body:
            out[sign] = body
    return out


def parse_jupiter_special(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for sign, label in (
        ("Capricorn", r"Jupiter in Capricorn \(Mars Exalted, Jupiter Debilitated\)"),
        ("Pisces", r"Jupiter in Pisces \(Venus Exalted, Mercury Debilitated\)"),
        ("Scorpio", r"Jupiter in Scorpio:"),
    ):
        m = re.search(label, text, re.I)
        if not m:
            continue
        nxt = re.search(r"Jupiter in (?:Pisces|Capricorn|Aries|Taurus|Scorpio):", text[m.end():], re.I)
        body = text[m.end(): m.end() + (nxt.start() if nxt else 1200)]
        cleaned = _sanitize_bnn_clause(body)
        if cleaned:
            out[sign] = cleaned
    return out


def main() -> None:
    text = OCR.read_text(encoding="utf-8", errors="ignore")
    planet_in_sign: dict[str, dict[str, str]] = {}
    sign_sections = [
        ("Moon", r"Moon in Different Signs", r"Moon Combination \(1,5,9\)"),
        ("Venus", r"Venus in Different Signs", r"Venus Combination with Other Planets"),
        ("Mars", r"Mars in Different Signs", r"Mars in Female Chart"),
        ("Jupiter", r"Jupiter in Different Signs", r"Jupiter's Influence: Understanding"),
        ("Mercury", r"Mercury in Different Signs & Education", r"Mercury in Different Houses from Jupiter"),
        ("Sun", r"Sun in Different Rashis: Effects", r"Understanding Moon"),
    ]
    for planet, start, end in sign_sections:
        block = parse_planet_in_sign(text, planet, start, end)
        if block:
            planet_in_sign[planet] = block

    jup_special = parse_jupiter_special(text)
    if jup_special:
        planet_in_sign.setdefault("Jupiter", {}).update(jup_special)

    house_from_jupiter: dict[str, dict[int, str]] = {}
    for pl in ("Mercury", "Mars", "Moon", "Sun"):
        block = parse_house_from_jupiter(text, pl)
        if block:
            house_from_jupiter[pl] = {str(k): v for k, v in block.items()}

    data = {
        "source": "Bhrigu Nandi Nadi: Astrology Simplified - Saurabh Avasthi (rules24)",
        "ocr_path": str(OCR),
        "combinations": parse_combinations(text),
        "pairs_159": parse_pairs_159(text),
        "planet_in_sign": planet_in_sign,
        "planet_in_house_from_jupiter": house_from_jupiter,
        "rahu_in_house": {str(k): v for k, v in parse_rahu_ketu_in_house(text, "Rahu").items()},
        "ketu_in_house": {str(k): v for k, v in parse_rahu_ketu_in_house(text, "Ketu").items()},
        "fourth_house_planet": parse_fourth_house_tenants(text),
        "profession_by_sign": parse_profession_signs(text),
        "rahu_in_sign": parse_node_in_sign(text, "Rahu"),
        "ketu_in_sign": parse_node_in_sign(text, "Ketu"),
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    combo_keys = len(data["combinations"])
    pairs = len(data["pairs_159"])
    signs = sum(len(v) for v in data["planet_in_sign"].values())
    print(f"combinations={combo_keys} pairs_159={pairs} planet_signs={signs} jup_houses={len(house_from_jupiter)}")
    print(f"written -> {OUT}")


if __name__ == "__main__":
    main()
