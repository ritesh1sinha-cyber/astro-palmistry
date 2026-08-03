#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Longevity book corpus loader."""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "longevity_book_data.json"


def load_longevity_book() -> dict:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Run build_longevity_data.py first - missing {DATA_PATH}")
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))
