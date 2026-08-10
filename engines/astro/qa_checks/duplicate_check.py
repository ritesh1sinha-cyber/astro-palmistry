"""Exact duplicate detection across unrelated evidence signatures."""

from __future__ import annotations

from typing import Optional


class DuplicateTracker:
    """Track headlines used per evidence signature within one report."""

    def __init__(self) -> None:
        self._by_text: dict[str, tuple] = {}
        self._by_sig: dict[tuple, str] = {}

    def check(self, text: str, signature: tuple) -> bool:
        """Return True if this exact text was already used for a different signature."""
        norm = (text or "").strip().lower()
        if not norm:
            return False
        prev_sig = self._by_text.get(norm)
        if prev_sig is not None and prev_sig != signature:
            return True
        return False

    def register(self, text: str, signature: tuple) -> None:
        norm = (text or "").strip().lower()
        if not norm:
            return
        self._by_text[norm] = signature
        self._by_sig[signature] = norm


def exact_duplicate(text: str, other_text: str) -> bool:
    return (text or "").strip().lower() == (other_text or "").strip().lower()
