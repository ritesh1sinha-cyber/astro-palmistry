#!/usr/bin/env python3
"""Ensure MiniLM weights are present — prefer repo-bundled models, no Hub download.

Docker / Railway ship `engines/astro/models/paraphrase-multilingual-MiniLM-L12-v2`
via Git LFS. This script only verifies they landed; it does NOT download unless
ALLOW_MODEL_DOWNLOAD=1 (emergency offline recovery).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _enabled() -> bool:
    return os.getenv("WITH_CONFLUENCE", "1").strip().lower() in ("1", "true", "yes", "on")


def _allow_download() -> bool:
    return os.getenv("ALLOW_MODEL_DOWNLOAD", "0").strip().lower() in ("1", "true", "yes", "on")


def main() -> int:
    if not _enabled():
        print("[models] WITH_CONFLUENCE off — semantic encoder skipped", flush=True)
        return 0

    root = Path(__file__).resolve().parents[1]
    astro = root / "engines" / "astro"
    for p in (str(root / "engines"), str(astro), str(root)):
        if p not in sys.path:
            sys.path.insert(0, p)

    from local_models import resolve_minilm, model_status

    st = model_status()
    if st.get("minilm"):
        try:
            path = resolve_minilm()
        except FileNotFoundError:
            path = "(unresolved)"
        # Prove the stack can import ST (catches torch/transformers DTensor breaks).
        try:
            import sentence_transformers  # noqa: F401
            from sentence_transformers import SentenceTransformer  # noqa: F401
        except Exception as exc:  # noqa: BLE001
            print(
                f"[models] MiniLM weights present but sentence-transformers cannot "
                f"import ({type(exc).__name__}: {exc}). "
                f"Need torch>=2.5 (2.4.x lacks DTensor expected by recent transformers).",
                flush=True,
            )
            return 1
        print(f"[models] ready · bundled MiniLM={st.get('active') or path}", flush=True)
        print(f"[models] sentence-transformers import OK", flush=True)
        if not st.get("cross_encoder"):
            print("[models] cross-encoder optional — MiniLM alone is enough for Phase 1",
                  flush=True)
        return 0

    # Missing from image / checkout
    msg = (
        "[models] MiniLM weights missing under engines/astro/models/. "
        "Expected paraphrase-multilingual-MiniLM-L12-v2 (Git LFS). "
        "Commit the models folder and rebuild — Docker must not depend on Hub download."
    )
    if not _allow_download():
        print(msg, flush=True)
        return 1

    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        print("[models] sentence-transformers not installed", flush=True)
        return 1

    print("[models] ALLOW_MODEL_DOWNLOAD=1 — fetching from Hugging Face…", flush=True)
    try:
        import download_models
        download_models.main()
    except Exception as exc:  # noqa: BLE001
        print(f"[models] download failed: {type(exc).__name__}: {exc}", flush=True)
        return 1

    st = model_status()
    if not st.get("minilm"):
        print("[models] MiniLM still missing after download", flush=True)
        return 1
    print("[models] download complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
