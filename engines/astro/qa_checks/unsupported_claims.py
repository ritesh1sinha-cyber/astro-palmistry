"""Reject invented events not supported by manifestation classes."""

from __future__ import annotations

import re
from typing import Iterable

# Claims that require an explicit manifestation class to be allowed.
CLAIM_REQUIRES: list[tuple[re.Pattern[str], frozenset[str]]] = [
    # Explicit event claims need an exact matching manifestation class.
    (re.compile(r"\b(promotion|promoted|pay raise|salary increase)\b", re.I),
     frozenset({"promotion"})),
    (re.compile(r"\b(married|marriage|wedding|spouse)\b", re.I),
     frozenset({"commitment", "marriage"})),
    (re.compile(r"\b(large payment|bonus|windfall)\b", re.I),
     frozenset({"gains", "income"})),
    (re.compile(r"\b(diagnosed|disease|medication|recover(?:ed|y)? from illness)\b", re.I),
     frozenset()),  # never allowed as event claim
]


def unsupported_event_detected(
    text: str,
    manifestations: Iterable[str],
) -> list[str]:
    """Return list of unsupported claim labels found in text."""
    mans = set(manifestations or ())
    hits: list[str] = []
    for pat, required in CLAIM_REQUIRES:
        m = pat.search(text or "")
        if not m:
            continue
        token = m.group(0)
        if not required or not (mans & required):
            # Health/disease patterns have empty required → always reject
            if not required or not (mans & required):
                hits.append(token)
    return hits
