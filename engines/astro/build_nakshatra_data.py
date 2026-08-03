#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse 108 Nakshatra Stories OCR into nakshatra_karmic_data.json."""
from __future__ import annotations

import json
import re
from pathlib import Path

from astro_precompute import NAKSHATRAS, normalize_nakshatra

BASE = Path(__file__).resolve().parent
OCR = BASE / (
    "book_ocr/nakshatra_karmic_stories/"
    "THE_108_NAKSHATRA_STORIES__A_HANDBOOK_OF_KARMIC_TALES__KARMIC_STORIES_FROM_KARAM_VIPAK_SAMHITA_ocr_full.txt"
)
OUT = BASE / "nakshatra_karmic_data.json"

PADA_ORD = {"1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "ist": 1}

HEADER = re.compile(
    r"^([A-Za-z]+(?:\s+[A-Za-z]+)?)\s*(?:Nakshatra\s+)?"
    r"((?:1st|2nd|3rd|4th|Ist)\s+pada)\s*$",
    re.I | re.M,
)

OCR_ALIASES = {
    "Kritika": "Krittika",
    "Krittika": "Krittika",
    "Jyestha": "Jyeshtha",
    "Mrigashira": "Mrigashira",
    "Purva Phalguni": "Purva Phalguni",
    "Uttara Phalguni": "Uttara Phalguni",
    "Purva Ashadha": "Purva Ashadha",
    "Uttara Ashadha": "Uttara Ashadha",
    "Purva Bhadrapada": "Purva Bhadrapada",
    "Uttara Bhadrapada": "Uttara Bhadrapada",
}


def _canonical_nak(name: str) -> str:
    raw = re.sub(r"\s+", " ", name.strip())
    raw = re.sub(r"\s+Nakshatra\s*$", "", raw, flags=re.I)
    if raw in OCR_ALIASES:
        return OCR_ALIASES[raw]
    if raw == "Dhanishta":
        return "Dhanishtha"
    return normalize_nakshatra(raw)


def _pada_num(token: str) -> int:
    t = token.lower().replace("pada", "").strip()
    if t in PADA_ORD:
        return PADA_ORD[t]
    m = re.match(r"(\d)", t)
    return int(m.group(1)) if m else 1


def _clean_body(text: str) -> str:
    text = re.sub(r"========== PAGE \d+ ==========", "\n", text)
    text = re.sub(
        r"THE 108 NAKSHATRA STORIES:.*?SAMHITA\s*",
        " ",
        text,
        flags=re.I | re.S,
    )
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_story(block: str) -> dict:
    block = _clean_body(block)
    sm = re.search(r"\bStory\b", block, re.I)
    if not sm:
        return {"title": "", "body": block, "moral": ""}
    tail = block[sm.end():].strip()
    lines = [ln.strip() for ln in tail.splitlines() if ln.strip()]
    title = ""
    body_lines: list[str] = []
    for ln in lines:
        if re.match(r"^\d+(st|nd|rd|th)\s+Pada:", ln, re.I):
            continue
        if not title and len(ln) < 120 and not ln.lower().startswith("in the"):
            title = ln
            continue
        body_lines.append(ln)
    body = " ".join(body_lines)
    body = re.sub(r"\s+", " ", body).strip()
    moral = ""
    for sent in re.split(r"(?<=[.!?])\s+", body):
        low = sent.lower()
        if any(k in low for k in ("karma", "lesson", "reminder", "consequence", "redemption", "testament")):
            moral = sent
    if not moral and body:
        moral = body[-280:] if len(body) > 280 else body
    return {"title": title, "body": body, "moral": moral}


def parse_ocr(text: str) -> list[dict]:
    matches = list(HEADER.finditer(text))
    tales: list[dict] = []
    for i, m in enumerate(matches):
        nak_raw = m.group(1).strip()
        pada_tok = m.group(2)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[m.end():end]
        story = _extract_story(chunk)
        nak = _canonical_nak(nak_raw)
        pada = _pada_num(pada_tok)
        if nak not in NAKSHATRAS:
            continue
        idx = NAKSHATRAS.index(nak) + 1
        tales.append({
            "nakshatra": nak,
            "pada": pada,
            "story_id": (idx - 1) * 4 + pada,
            "header": m.group(0).strip(),
            "title": story["title"],
            "body": story["body"],
            "moral": story["moral"],
        })
    return tales


def main() -> None:
    if not OCR.is_file():
        raise FileNotFoundError(f"Missing OCR: {OCR}")
    text = OCR.read_text(encoding="utf-8", errors="replace")
    tales = parse_ocr(text)
    by_key = {f"{t['nakshatra']}|{t['pada']}": t for t in tales}
    payload = {
        "source": str(OCR.relative_to(BASE)),
        "count": len(tales),
        "expected": 108,
        "tales": tales,
        "by_key": by_key,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    missing = []
    for nak in NAKSHATRAS:
        for p in range(1, 5):
            if f"{nak}|{p}" not in by_key:
                missing.append(f"{nak} {p}")
    print(f"parsed {len(tales)} tales -> {OUT}")
    if missing:
        print(f"missing ({len(missing)}): {', '.join(missing[:12])}{'...' if len(missing) > 12 else ''}")


if __name__ == "__main__":
    main()
