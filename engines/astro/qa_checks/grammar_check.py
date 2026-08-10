"""Light post-render grammar cleanup for known artifacts."""

from __future__ import annotations

import re

_REPLACEMENTS = (
    (re.compile(r"\ba a\b", re.I), "a"),
    (re.compile(r"\ban a\b", re.I), "a"),
    (re.compile(r"\ba an\b", re.I), "an"),
    (re.compile(r"\bthe the\b", re.I), "the"),
    (re.compile(r"\.\s+the\b"), ". The"),
    (re.compile(r"\.\s+and\b"), ". And"),
)


def fix_grammar(text: str) -> str:
    out = text or ""
    for pat, repl in _REPLACEMENTS:
        out = pat.sub(repl, out)
    # Collapse doubled spaces introduced by replacements
    out = re.sub(r" {2,}", " ", out)
    return out
