#!/usr/bin/env python3
"""Trim large-process working sets, then load bundled MiniLM (no Hub)."""
from __future__ import annotations

import ctypes
import gc
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "engines"), str(ROOT / "engines" / "astro")]

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


def trim_working_sets(names: set[str]) -> tuple[int, int]:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    access = 0x0100 | 0x0400 | 0x1000  # SET_QUOTA | QUERY | QUERY_LIMITED
    out = subprocess.check_output(["tasklist", "/fo", "csv", "/nh"], text=True, errors="ignore")
    ok_n = fail_n = 0
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) < 2:
            continue
        name, pid_s = parts[0].strip('"'), parts[1]
        if name not in names:
            continue
        try:
            pid = int(pid_s)
        except ValueError:
            continue
        h = kernel32.OpenProcess(access, False, pid)
        if not h:
            fail_n += 1
            continue
        if psapi.EmptyWorkingSet(h):
            ok_n += 1
        else:
            fail_n += 1
        kernel32.CloseHandle(h)
    return ok_n, fail_n


def main() -> int:
    ok, fail = trim_working_sets({"chrome.exe", "msedge.exe", "Cursor.exe"})
    print(f"[mem] EmptyWorkingSet ok={ok} fail={fail}", flush=True)
    gc.collect()

    from local_models import active_minilm_name, resolve_minilm

    print(f"[models] active={active_minilm_name()}", flush=True)
    print(f"[models] path={resolve_minilm()}", flush=True)

    import torch
    from sentence_transformers import SentenceTransformer

    torch.set_num_threads(1)
    print("[models] loading SentenceTransformer…", flush=True)
    model = SentenceTransformer(
        resolve_minilm(),
        local_files_only=True,
        device="cpu",
        model_kwargs={"low_cpu_mem_usage": True},
    )
    vecs = model.encode(
        [
            "Will I get a promotion this year?",
            "job growth at office",
            "last 6 months money stress",
        ],
        normalize_embeddings=True,
    )
    print(f"[models] encode ok shape={getattr(vecs, 'shape', type(vecs))}", flush=True)

    from semantic_question import route

    for q in (
        "Will I get a promotion this year?",
        "Is my career stuck at work?",
        "How was money flow in the last six months?",
    ):
        r = route(q)
        print(
            f"[route] {q!r} -> {r.domain} H{r.primary_house} "
            f"({r.method} score={r.house_score:.3f})",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OSError as exc:
        print(f"[fail] OSError: {exc}", flush=True)
        print(
            "[hint] Virtually all commit charge is used (Chrome/Cursor). "
            "Close Chrome tabs or raise the Windows page file, then re-run.",
            flush=True,
        )
        raise SystemExit(2)
    except Exception as exc:  # noqa: BLE001
        print(f"[fail] {type(exc).__name__}: {exc}", flush=True)
        raise SystemExit(1)
