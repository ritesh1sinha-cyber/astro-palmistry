"""
Extract rule-like statements from palmistry OCR full-text files.
No LLM — heuristic extraction from all pages in palmistry_ocr/.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from palm_api.paths import OCR_DIR, RULES_CORPUS

PAGE_RE = re.compile(r"={5,}\s*PAGE\s+(\d+)\s*={5,}", re.I)

# Palmistry vocabulary for filtering noise
PALM_TERMS = re.compile(
    r"\b("
    r"life\s*line|head\s*line|heart\s*line|fate\s*line|sun\s*line|apollo|mercury|"
    r"jupiter|saturn|venus|mars|moon\s*mount|mount|palm|finger|thumb|nail|"
    r"marriage|career|health|vitality|line|creas|hand|wrist|bracelet|grille|"
    r"island|break|fork|trident|cross|star|dot|ring|phalanx|knotty|supple"
    r")\b",
    re.I,
)

NOISE_RE = re.compile(
    r"\b("
    r"all rights reserved|copyright|no part of this|isbn|published by|"
    r"permission|reproduced|library of congress|www\.|https?://|"
    r"printed in|publisher|first edition|second edition|distributor|"
    r"acknowledg|preface only|table of contents|index page"
    r")\b",
    re.I,
)

RULE_VERBS = re.compile(
    r"\b("
    r"indicates?|means?|denotes?|shows?|suggests?|signifies?|represents?|"
    r"if\s+the|when\s+the|when\s+a|one\s+may|may\s+be|will\s+be|should\s+be|"
    r"person\s+who|individual|tendency|character|nature|likely|often|always|"
    r"never|must\s+be|can\s+be|predict|indication|symbol"
    r")\b",
    re.I,
)

CATEGORY_MAP = [
    (re.compile(r"life\s*line|vitality|health|constitution", re.I), "vitality"),
    (re.compile(r"head\s*line|mind|intellect|mental|concentration", re.I), "mind"),
    (re.compile(r"heart\s*line|love|marriage|relationship|affection", re.I), "heart"),
    (re.compile(r"fate\s*line|career|profession|business|employment|success", re.I), "career"),
    (re.compile(r"sun\s*line|fame|name|respect|apollo", re.I), "fame"),
    (re.compile(r"finger|phalanx|knotty|supple|length", re.I), "fingers"),
    (re.compile(r"mount|jupiter|saturn|venus|mercury|mars|moon", re.I), "mounts"),
    (re.compile(r"remedy|remedies|upaya|mantra|gem", re.I), "remedies"),
    (re.compile(r"travel|foreign|linea", re.I), "travel"),
]


def _clean_line(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[^\w\s\-',.;:()%/&]", "", s)
    return s


def _categorize(text: str) -> str:
    for pat, cat in CATEGORY_MAP:
        if pat.search(text):
            return cat
    return "general"


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[a-z]{4,}", text.lower())
    stop = {
        "that", "this", "with", "from", "have", "been", "will", "they",
        "their", "which", "when", "what", "than", "then", "also", "into",
        "only", "such", "more", "very", "some", "other", "about", "would",
        "could", "should", "there", "these", "those", "being", "through",
    }
    return sorted({w for w in words if w not in stop})[:40]


def _is_rule_candidate(line: str) -> bool:
    if len(line) < 35 or len(line) > 900:
        return False
    if line.isupper() and len(line) < 80:
        return False  # headers
    if NOISE_RE.search(line):
        return False
    if not PALM_TERMS.search(line):
        return False
    if not RULE_VERBS.search(line):
        return False
    # Skip obvious OCR garbage
    if sum(c.isalpha() for c in line) / max(len(line), 1) < 0.5:
        return False
    return True


def _split_sentences(block: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", block)
    out = []
    for p in parts:
        p = _clean_line(p)
        if _is_rule_candidate(p):
            out.append(p)
    return out


def extract_from_ocr_text(text: str, book_id: str) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    pages: list[tuple[int, str]] = []
    matches = list(PAGE_RE.finditer(text))
    if not matches:
        pages = [(0, text)]
    else:
        for idx, m in enumerate(matches):
            pnum = int(m.group(1))
            start = m.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            pages.append((pnum, text[start:end]))

    for page, body in pages:
        paragraphs = re.split(r"\n\s*\n", body)
        for para in paragraphs:
            para = _clean_line(para.replace("\n", " "))
            if not para:
                continue
            if _is_rule_candidate(para):
                rid = f"{book_id}_p{page}_{len(rules)}"
                rules.append(
                    {
                        "id": rid,
                        "book": book_id,
                        "page": page,
                        "category": _categorize(para),
                        "text": para,
                        "keywords": _keywords(para),
                    }
                )
            else:
                for sent in _split_sentences(para):
                    rid = f"{book_id}_p{page}_{len(rules)}"
                    rules.append(
                        {
                            "id": rid,
                            "book": book_id,
                            "page": page,
                            "category": _categorize(sent),
                            "text": sent,
                            "keywords": _keywords(sent),
                        }
                    )
    return rules


def _book_id_from_path(path: Path) -> str:
    return path.parent.name


def build_corpus(ocr_root: Path | None = None) -> dict[str, Any]:
    ocr_root = ocr_root or OCR_DIR
    all_rules: list[dict[str, Any]] = []
    books: list[str] = []
    for txt in sorted(ocr_root.glob("*/*_ocr_full.txt")):
        book_id = _book_id_from_path(txt)
        books.append(book_id)
        text = txt.read_text(encoding="utf-8", errors="replace")
        extracted = extract_from_ocr_text(text, book_id)
        all_rules.extend(extracted)
        print(f"  {book_id}: {len(extracted)} candidates", flush=True)

    # Dedupe near-identical text
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for r in all_rules:
        key = re.sub(r"\W+", "", r["text"].lower())[:200]
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)

    return {
        "version": 2,
        "books": books,
        "rule_count": len(unique),
        "rules": unique,
    }


def save_corpus(path: Path | None = None) -> dict[str, Any]:
    path = path or RULES_CORPUS
    print("Building palmistry rules corpus from OCR…", flush=True)
    corpus = build_corpus()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(corpus, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"Saved {corpus['rule_count']} rules -> {path}")
    return corpus


def load_corpus(path: Path | None = None) -> dict[str, Any]:
    path = path or RULES_CORPUS
    if not path.is_file():
        return save_corpus(path)
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    save_corpus()
