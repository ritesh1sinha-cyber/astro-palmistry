#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Curate Goel Predict with Saptamsha rules (rules14) into goel_saptamsha_book_data.json."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "goel_saptamsha_book_data.json"

DATA = {
    "source": "Predict with Saptamsha (V.P. Goel) - rules14.md + OCR",
    "disclaimer": "Educational astrology only - not medical or fertility advice.",
    "d7_final_say": "D7 confirms or denies D1 fifth-house promise for progeny.",
    "child_house_sequences": {
        "odd_lagna": [5, 7, 9, 11, 1, 3, 4, 6, 8, 10, 12],
        "even_lagna": [9, 7, 5, 3, 1, 11, 10, 8, 6, 4, 2],
    },
    "timing_houses_d7": [1, 2, 5, 9, 10],
    "timing_karakas_d1": ["5th lord", "Jupiter", "5th occupants"],
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(DATA, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"written -> {OUT}")
