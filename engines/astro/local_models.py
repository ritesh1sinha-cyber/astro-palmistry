#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resolve sentence-transformer models from project-local models/ only.

Set HF_HUB_OFFLINE=1 when a complete local copy exists so runs never hit the Hub.

Preferred encoder (Phase 1): paraphrase-multilingual-MiniLM-L12-v2
  — better cross-language / paraphrase matching for question → house routing
    and multi-technique confluence. Falls back to all-MiniLM-L6-v2 if present.
"""
from __future__ import annotations

import os
from pathlib import Path

BASE = Path(__file__).resolve().parent
MODELS_DIR = BASE / "models"

# Prefer the multilingual paraphrase MiniLM the project ships / copies in.
MINILM_MULTILINGUAL_DIR = MODELS_DIR / "paraphrase-multilingual-MiniLM-L12-v2"
MINILM_MULTILINGUAL_HF_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

MINILM_DIR = MODELS_DIR / "all-MiniLM-L6-v2"  # legacy fallback path name
MINILM_HF_ID = "sentence-transformers/all-MiniLM-L6-v2"

CROSS_ENCODER_DIR = MODELS_DIR / "cross-encoder-stsb-roberta-base"
CROSS_ENCODER_HF_ID = "cross-encoder/stsb-roberta-base"

_WEIGHT_NAMES = (
    "model.safetensors",
    "pytorch_model.bin",
    "model.bin",
)


def is_model_ready(path: Path) -> bool:
    if not path.is_dir():
        return False
    if not any((path / name).is_file() for name in _WEIGHT_NAMES):
        return False
    # Cross-encoder / transformer repos need tokenizer assets for offline load.
    return (
        (path / "tokenizer.json").is_file()
        or (path / "vocab.json").is_file()
        or (path / "sentencepiece.bpe.model").is_file()
    )


def _enable_offline() -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


def resolve_minilm() -> str:
    """Return local MiniLM path; prefer multilingual L12, then L6."""
    for path in (MINILM_MULTILINGUAL_DIR, MINILM_DIR):
        if is_model_ready(path):
            _enable_offline()
            return str(path)
    raise FileNotFoundError(
        f"Local MiniLM not found. Expected one of:\n"
        f"  {MINILM_MULTILINGUAL_DIR}\n"
        f"  {MINILM_DIR}\n"
        f"Copy paraphrase-multilingual-MiniLM-L12-v2 into models/, "
        f"or run: python download_models.py"
    )


def resolve_cross_encoder() -> str | None:
    """Return local cross-encoder path, or None if not downloaded."""
    if is_model_ready(CROSS_ENCODER_DIR):
        _enable_offline()
        return str(CROSS_ENCODER_DIR)
    return None


def load_sentence_transformer():
    """Load local MiniLM on CPU. Survives Windows paging-file / low-RAM errors."""
    from sentence_transformers import SentenceTransformer

    path = resolve_minilm()
    # Force CPU — GPU init on Windows often blows the page file for ~450 MB models.
    try:
        import torch
        torch.set_num_threads(max(1, min(4, (os.cpu_count() or 2))))
    except Exception:
        pass
    try:
        return SentenceTransformer(path, local_files_only=True, device="cpu")
    except OSError as exc:
        # "paging file is too small" / out of memory — try the smaller L6 if present
        if is_model_ready(MINILM_DIR) and Path(path).resolve() != MINILM_DIR.resolve():
            print(f"[local_models] {exc} — falling back to {MINILM_DIR.name}", flush=True)
            _enable_offline()
            return SentenceTransformer(str(MINILM_DIR), local_files_only=True, device="cpu")
        raise


def load_cross_encoder():
    from sentence_transformers import CrossEncoder

    path = resolve_cross_encoder()
    if not path:
        return None
    return CrossEncoder(path, local_files_only=True)


def active_minilm_name() -> str:
    try:
        p = Path(resolve_minilm())
        return p.name
    except FileNotFoundError:
        return ""


def model_status() -> dict[str, bool]:
    return {
        "minilm": is_model_ready(MINILM_MULTILINGUAL_DIR) or is_model_ready(MINILM_DIR),
        "minilm_multilingual": is_model_ready(MINILM_MULTILINGUAL_DIR),
        "minilm_l6": is_model_ready(MINILM_DIR),
        "cross_encoder": is_model_ready(CROSS_ENCODER_DIR),
        "active": active_minilm_name(),
    }
