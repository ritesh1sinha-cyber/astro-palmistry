#!/usr/bin/env python3
"""Unit test for semantic_question routing without loading torch weights.

Uses a tiny fake encoder so CI / low-RAM Windows boxes can verify wiring.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "engines" / "astro"), str(ROOT / "engines"), str(ROOT)]


class _FakeModel:
    def encode(self, texts, normalize_embeddings=True, **_):
        import hashlib
        import numpy as np
        if isinstance(texts, str):
            texts = [texts]
        # Stable bag (not Python hash()) so CI is deterministic across processes
        out = []
        for t in texts:
            v = np.zeros(64, dtype="float32")
            for w in t.lower().split():
                dig = int(hashlib.md5(w.encode()).hexdigest(), 16)
                v[dig % 64] += 1.0
            n = float(np.linalg.norm(v)) or 1.0
            out.append(v / n)
        return np.stack(out)


def main() -> None:
    import local_models
    import semantic_question as SQ

    # Force fake encoder (no torch load)
    SQ._ENGINE = None
    SQ._ENGINE_FAILED = False
    local_models.load_sentence_transformer = lambda *a, **k: _FakeModel()
    SQ.have_minilm = lambda: True

    eng = SQ._model()
    assert eng is not None, "fake engine failed"

    r = SQ.route("Will I get the promotion this year?")
    print("promotion ->", r.domain, "H" + str(r.primary_house), r.method, round(r.house_score, 3))
    # Keyword assist must keep classic H10 for "promotion" even with a weak fake encoder
    assert r.primary_house == 10, r
    assert 10 in r.houses

    r2 = SQ.route("Profession feels stuck when does it open")
    print("paraphrase career ->", r2.domain, "H" + str(r2.primary_house), r2.method)
    # Without strong keywords, fake encoder is noisy — just ensure a house is chosen
    assert 1 <= r2.primary_house <= 12

    from western_horary_rules import parse_question
    wh = parse_question("Will I get the promotion this year?")
    print("western house", wh["house"], "semantic", wh.get("semantic_house"))
    assert wh["house"] == 10

    from client_question_engine import route_client_question
    cq = route_client_question("Will I relocate abroad for work?")
    print("client", cq.domain, "H" + str(cq.primary_house), cq.topic)
    assert cq.primary_house in (9, 12, 10, 3)

    from local_models import model_status
    print("weights on disk:", model_status())
    print("OK wiring test (fake encoder + keyword assist)")


if __name__ == "__main__":
    main()
