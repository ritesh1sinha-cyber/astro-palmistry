"""Semantic similarity gate — MiniLM with lexical fallback."""

from __future__ import annotations

import re
from typing import Optional

_THRESHOLD = 0.90


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z']+", (text or "").lower()))


def jaccard_similarity(a: str, b: str) -> float:
    sa, sb = _token_set(a), _token_set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def semantic_too_similar(
    a: str,
    b: str,
    *,
    threshold: float = _THRESHOLD,
) -> bool:
    """True if texts are semantically too close (unrelated evidence should fail)."""
    if not a or not b:
        return False
    if a.strip().lower() == b.strip().lower():
        return True
    try:
        from local_models import load_sentence_transformer
        model = load_sentence_transformer()
        emb = model.encode([a, b], normalize_embeddings=True)
        sim = float(emb[0] @ emb[1])
        return sim >= threshold
    except Exception:  # noqa: BLE001
        return jaccard_similarity(a, b) >= 0.82
