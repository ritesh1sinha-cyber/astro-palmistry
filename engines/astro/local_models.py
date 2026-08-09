#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resolve sentence-transformer models from project-local models/ only.

Set HF_HUB_OFFLINE=1 when a complete local copy exists so runs never hit the Hub.

Preferred encoder (Phase 1): paraphrase-multilingual-MiniLM-L12-v2
  — better cross-language / paraphrase matching for question → house routing
    and multi-technique confluence. Falls back to all-MiniLM-L6-v2 if present.

Models are loaded once per process and reused (confluence + question paths
used to construct a new SentenceTransformer per job, doubling peak RAM).
"""
from __future__ import annotations

import os
import threading
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

_ST_MODEL = None
_ST_PATH: str | None = None
_CROSS_MODEL = None
_CROSS_PATH: str | None = None
_ST_LOCK = threading.Lock()
_CROSS_LOCK = threading.Lock()


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


def _load_st_from_path(path: str):
    from sentence_transformers import SentenceTransformer

    try:
        import torch
        torch.set_num_threads(max(1, min(4, (os.cpu_count() or 2))))
    except Exception:
        pass
    try:
        return SentenceTransformer(path, local_files_only=True, device="cpu")
    except OSError as exc:
        if is_model_ready(MINILM_DIR) and Path(path).resolve() != MINILM_DIR.resolve():
            print(f"[local_models] {exc} — falling back to {MINILM_DIR.name}", flush=True)
            _enable_offline()
            return SentenceTransformer(str(MINILM_DIR), local_files_only=True, device="cpu")
        raise


def load_sentence_transformer():
    """Load local MiniLM on CPU once per process; reuse on later calls."""
    global _ST_MODEL, _ST_PATH
    if _ST_MODEL is not None:
        return _ST_MODEL
    with _ST_LOCK:
        if _ST_MODEL is not None:
            return _ST_MODEL
        path = resolve_minilm()
        _ST_MODEL = _load_st_from_path(path)
        _ST_PATH = path
        return _ST_MODEL


def load_cross_encoder():
    """Load cross-encoder once per process when weights exist."""
    global _CROSS_MODEL, _CROSS_PATH
    path = resolve_cross_encoder()
    if not path:
        return None
    if _CROSS_MODEL is not None and _CROSS_PATH == path:
        return _CROSS_MODEL
    with _CROSS_LOCK:
        if _CROSS_MODEL is not None and _CROSS_PATH == path:
            return _CROSS_MODEL
        from sentence_transformers import CrossEncoder
        _CROSS_MODEL = CrossEncoder(path, local_files_only=True)
        _CROSS_PATH = path
        return _CROSS_MODEL


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
