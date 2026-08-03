#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resolve sentence-transformer models from project-local models/ only.

Set HF_HUB_OFFLINE=1 when a complete local copy exists so runs never hit the Hub.
"""
from __future__ import annotations

import os
from pathlib import Path

BASE = Path(__file__).resolve().parent
MODELS_DIR = BASE / "models"

MINILM_DIR = MODELS_DIR / "all-MiniLM-L6-v2"
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
    return (path / "tokenizer.json").is_file() or (path / "vocab.json").is_file()


def _enable_offline() -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


def resolve_minilm() -> str:
    """Return local MiniLM path; raise if missing."""
    if is_model_ready(MINILM_DIR):
        _enable_offline()
        return str(MINILM_DIR)
    raise FileNotFoundError(
        f"Local MiniLM not found at {MINILM_DIR}. "
        f"Run: python3 download_models.py"
    )


def resolve_cross_encoder() -> str | None:
    """Return local cross-encoder path, or None if not downloaded."""
    if is_model_ready(CROSS_ENCODER_DIR):
        _enable_offline()
        return str(CROSS_ENCODER_DIR)
    return None


def load_sentence_transformer():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(resolve_minilm(), local_files_only=True)


def load_cross_encoder():
    from sentence_transformers import CrossEncoder

    path = resolve_cross_encoder()
    if not path:
        return None
    return CrossEncoder(path, local_files_only=True)


def model_status() -> dict[str, bool]:
    return {
        "minilm": is_model_ready(MINILM_DIR),
        "cross_encoder": is_model_ready(CROSS_ENCODER_DIR),
    }
