#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared client helpers for PyJHora-backed report lanes."""
from __future__ import annotations

import re
from typing import Any


def female_from_pc(pc: dict, extract_text: str = "") -> bool:
    """Female flag from precompute meta.gender, else optional extract Sex line."""
    g = pc.get("meta", {}).get("gender", pc.get("gender"))
    if g is not None:
        return g == 1 or str(g).lower() in ("female", "f", "1")
    if extract_text:
        return bool(re.search(r"\bSex\s+Female\b", extract_text, re.I))
    return False


def source_label(
    *,
    precomputed_path: str | None = None,
    birth_time: str | None = None,
    extracted_path: str | None = None,
) -> str:
    if precomputed_path:
        return f"precomputed:{precomputed_path}"
    if birth_time:
        return "pyjhora:birth_flags"
    if extracted_path:
        return f"extract:{extracted_path}"
    return "pyjhora"
