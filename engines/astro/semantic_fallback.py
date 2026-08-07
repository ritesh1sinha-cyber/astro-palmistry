"""A stand-in encoder for when sentence-transformers is not installed.

The confluence report — the ₹1,499 flagship — groups statements from fifteen
techniques by meaning, so that "work feels blocked" and "career progress is
slow" count as one finding rather than two. That grouping runs on
SentenceTransformer embeddings.

`requirements.worker.txt` leaves torch and sentence-transformers out by default:
they add ~2 GB to the image, and the first deploy targets a small box. The
consequence was not degradation — it was `ModuleNotFoundError` at report time.
The most expensive product in the catalogue failed outright on the default
build, and only end-to-end testing surfaced it, because nothing else imports
that module.

This provides a lexical encoder with the same interface, so `SemanticEngine`
runs unchanged and the report is produced either way.

**It is genuinely worse.** Hashed word overlap groups "work feels blocked" with
"career progress is slow" only if they share vocabulary — and they barely do.
Expect more clusters, each thinner, and occasional near-duplicates that real
embeddings would have merged. It is the difference between a good report and a
complete one; install the real dependency before charging for this at scale.

`degraded()` reports which mode is active so the operator can tell.
"""

from __future__ import annotations

import hashlib
import math
import re

try:
    import numpy as np
except ImportError:                                  # pragma: no cover
    np = None                                        # type: ignore

DIM = 512
_WORD = re.compile(r"[a-z]{3,}")

# Words that appear in nearly every astrological sentence carry no signal for
# grouping and actively pull unrelated statements together.
_STOP = frozenset("""
the and for with your you this that from are was were has have had will would
can could should its it's their there here when where which who whom whose
about into onto over under above below than then them they she her his him
not but all any some more most much many few own same such only just very
house houses planet planets chart charts sign signs period periods lord lords
year years month months day days time times life reading report indicates
indicated shows show suggests suggest means meaning gives give
""".split())


def _tokens(text: str) -> list[str]:
    words = [w for w in _WORD.findall(text.lower()) if w not in _STOP]
    # bigrams keep a little word order, which pure bag-of-words throws away
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:])]


def _hash(token: str) -> int:
    return int.from_bytes(hashlib.blake2b(token.encode(), digest_size=4).digest(),
                          "little") % DIM


class LexicalEncoder:
    """Duck-types the slice of SentenceTransformer that SemanticEngine uses."""

    #: so callers can tell which encoder they got
    is_fallback = True

    def encode(self, sentences, normalize_embeddings: bool = True, **_kw):
        if isinstance(sentences, str):
            sentences = [sentences]
        vectors = []
        for text in sentences:
            vec = [0.0] * DIM
            counts: dict[str, int] = {}
            for tok in _tokens(text or ""):
                counts[tok] = counts.get(tok, 0) + 1
            for tok, n in counts.items():
                # sublinear term frequency: a word repeated six times is not
                # six times as important
                vec[_hash(tok)] += 1.0 + math.log(n)
            if normalize_embeddings:
                norm = math.sqrt(sum(v * v for v in vec)) or 1.0
                vec = [v / norm for v in vec]
            vectors.append(vec)
        if np is None:                               # pragma: no cover
            return vectors
        return np.asarray(vectors, dtype="float32")


def have_real_encoder() -> bool:
    try:
        import sentence_transformers  # noqa: F401
    except Exception:
        return False
    try:
        from local_models import (
            is_model_ready, MINILM_DIR, MINILM_MULTILINGUAL_DIR,
        )
        return bool(
            is_model_ready(MINILM_MULTILINGUAL_DIR) or is_model_ready(MINILM_DIR)
        )
    except Exception:
        # library present but weights unverifiable — let the real loader try
        return True


def install() -> bool:
    """Point local_models at the fallback when the real encoder is absent.

    Returns True when the fallback was installed. Patching the *loader* rather
    than SemanticEngine keeps the upstream engine file untouched, which is the
    same rule the rest of this integration follows.
    """
    if have_real_encoder():
        return False
    try:
        import local_models
    except ImportError:
        return False

    encoder = LexicalEncoder()
    local_models.load_sentence_transformer = lambda *a, **k: encoder
    local_models.load_cross_encoder = lambda *a, **k: None
    print("[astro] sentence-transformers not installed — confluence grouping "
          "is running on the lexical fallback (lower quality, still complete)",
          flush=True)
    return True


def degraded() -> bool:
    return not have_real_encoder()
