#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-time download of confluence embedding models into models/ (offline thereafter)."""
from __future__ import annotations

import sys
from pathlib import Path

from local_models import (
    CROSS_ENCODER_DIR,
    CROSS_ENCODER_HF_ID,
    MINILM_DIR,
    MINILM_HF_ID,
    is_model_ready,
    model_status,
)


def _download(repo_id: str, dest: Path, *, ignore_patterns: list[str] | None = None) -> None:
    if is_model_ready(dest) and _has_tokenizer(dest):
        print(f"skip (ready): {dest}")
        return
    print(f"downloading {repo_id} -> {dest}")
    dest.mkdir(parents=True, exist_ok=True)
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("huggingface_hub required for first download: pip install huggingface_hub", file=sys.stderr)
        raise
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(dest),
        ignore_patterns=ignore_patterns or ["onnx/**", "*.onnx", "*.msgpack"],
    )
    if not is_model_ready(dest):
        raise RuntimeError(f"download incomplete (weights): {dest}")
    if not _has_tokenizer(dest):
        raise RuntimeError(f"download incomplete (tokenizer): {dest}")


def _has_tokenizer(path: Path) -> bool:
    return (path / "tokenizer.json").is_file() or (path / "vocab.json").is_file()


def main() -> None:
    _download(MINILM_HF_ID, MINILM_DIR)
    _download(
        CROSS_ENCODER_HF_ID,
        CROSS_ENCODER_DIR,
        ignore_patterns=["onnx/**", "openvino/**", "*.onnx", "*.msgpack"],
    )
    st = model_status()
    print("model_status:", st)
    if not all(st.values()):
        raise SystemExit("One or more models failed to download.")
    print("All models local. Future runs use HF_HUB_OFFLINE=1.")


if __name__ == "__main__":
    main()
