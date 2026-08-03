#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-report clause registry - avoid repeating the same book line."""
from __future__ import annotations

import re
from typing import Iterable


def _fp(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower().strip())[:120]


class ClauseRegistry:
    def __init__(self) -> None:
        self._used: set[str] = set()

    def claim(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""
        key = _fp(text)
        if key in self._used:
            return ""
        self._used.add(key)
        return text

    def claim_many(self, texts: Iterable[str], max_n: int = 4) -> list[str]:
        out: list[str] = []
        for t in texts:
            c = self.claim(t)
            if c:
                out.append(c)
            if len(out) >= max_n:
                break
        return out


_REGISTRY: ClauseRegistry | None = None


def reset_registry() -> ClauseRegistry:
    global _REGISTRY
    _REGISTRY = ClauseRegistry()
    return _REGISTRY


def registry() -> ClauseRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ClauseRegistry()
    return _REGISTRY
