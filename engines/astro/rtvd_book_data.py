#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RTVD book corpus loader (rules16 / Guru Rajesh OCR)."""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "rtvd_book_data.json"


def load_rtvd_book() -> dict:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Run build_rtvd_data.py first - missing {DATA_PATH}")
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def topic_spec(book: dict, domain: str) -> dict:
    return book.get("topic_houses", {}).get(domain, {})


def topic_rules(book: dict, domain: str, max_n: int = 3) -> list[str]:
    return book.get("topic_rules", {}).get(domain, [])[:max_n]
