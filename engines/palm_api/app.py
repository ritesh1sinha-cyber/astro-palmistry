#!/usr/bin/env python3
"""
FastAPI palm reading — upload image → features → book-backed predictions.

  cd /home/oppo/Desktop/test8
  pip install -r palm_api/requirements.txt
  python3 -m palm_api.build_corpus   # first time: extract rules from PDF OCR
  uvicorn palm_api.app:app --host 127.0.0.1 --port 8010
"""

from __future__ import annotations

import asyncio
import functools
import json
import uuid
from pathlib import Path
from typing import Any

import cv2
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from palm_api.confluence import build_confluence
from palm_api.engine import features_to_narrative, features_to_rows
from palm_api.paths import DATA_DIR, RULES_CORPUS, UPLOAD_DIR
from palm_api.pipeline import analyze_one, ensure_corpus
from palm_api.reference import build_reference_text
from palm_api.rules_builder import save_corpus

APP_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = APP_DIR / "templates" / "index.html"

app = FastAPI(title="Palmistry Reader", version="1.0")
app.mount("/files", StaticFiles(directory=str(DATA_DIR)), name="files")

_corpus: dict[str, Any] | None = None


def _run_sync(fn, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, functools.partial(fn, *args, **kwargs))


def _file_url(subpath: str) -> str:
    return f"/files/{subpath.replace(chr(92), '/')}"


@app.on_event("startup")
async def startup():
    global _corpus

    def init():
        global _corpus
        _corpus = ensure_corpus()
        return _corpus.get("rule_count", 0)

    n = await _run_sync(init)
    print(f"Palm corpus loaded: {n} rules from palmistry PDFs", flush=True)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "rules_loaded": _corpus.get("rule_count", 0) if _corpus else 0,
        "corpus_path": str(RULES_CORPUS),
    }


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(
        TEMPLATE_PATH.read_text(encoding="utf-8"),
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@app.post("/api/rebuild-corpus")
async def rebuild_corpus():
    """Re-extract all rules from palmistry_ocr/*.txt (slow, ~1–2 min)."""
    corpus = await _run_sync(save_corpus)
    global _corpus
    _corpus = corpus
    return {"rule_count": corpus["rule_count"], "books": corpus["books"]}


def _analyze_image(
    path: Path,
    hand: str,
    exclude_rule_ids: set[str] | None = None,
) -> dict[str, Any]:
    fid = uuid.uuid4().hex[:10]
    overlay_name = f"outputs/{fid}_overlay.jpg"
    overlay_path = DATA_DIR / overlay_name
    block = analyze_one(
        path, hand,
        corpus=_corpus or ensure_corpus(),
        exclude_rule_ids=exclude_rule_ids,
        overlay_path=overlay_path,
    )
    return {
        **block,
        "facts_narrative": features_to_narrative(block["features"]),
        "facts_rows": features_to_rows(block["features"]),
        "overlay_url": _file_url(overlay_name),
    }


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    hand: str = Form("unknown"),
):
    if hand not in ("left", "right", "unknown"):
        raise HTTPException(400, "hand must be left, right, or unknown")
    suffix = Path(file.filename or "palm.jpg").suffix.lower()
    if suffix not in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
        raise HTTPException(400, "Use JPG or PNG palm photo")
    fid = uuid.uuid4().hex[:12]
    dest = UPLOAD_DIR / f"{fid}{suffix}"
    dest.write_bytes(await file.read())
    try:
        result = await _run_sync(_analyze_image, dest, hand)
    except Exception as e:
        raise HTTPException(500, str(e)) from e
    result["upload_url"] = _file_url(f"uploads/{dest.name}")
    return JSONResponse(result)


@app.post("/api/analyze/both")
async def analyze_both(
    right: UploadFile | None = File(None),
    left: UploadFile | None = File(None),
    active_hand: str = Form("right"),
):
    if not right and not left:
        raise HTTPException(400, "Upload at least one palm image")
    results: dict[str, Any] = {"active_hand": active_hand}
    used_rule_ids: set[str] = set()
    for label, upload in (("right", right), ("left", left)):
        if upload is None:
            continue
        suffix = Path(upload.filename or f"{label}.jpg").suffix.lower()
        fid = uuid.uuid4().hex[:12]
        dest = UPLOAD_DIR / f"{fid}{suffix}"
        dest.write_bytes(await upload.read())
        block = await _run_sync(_analyze_image, dest, label, used_rule_ids)
        for p in block.get("prediction", {}).get("predictions", []):
            if p.get("id"):
                used_rule_ids.add(p["id"])
        results[label] = block

    if results.get("right") and results.get("left"):
        results["confluence"] = build_confluence(results, active_hand)

    # Developer-only reference: maps each human prediction to its book rule.
    ref_name = f"outputs/{uuid.uuid4().hex[:12]}_reference.txt"
    (DATA_DIR / ref_name).write_text(build_reference_text(results), encoding="utf-8")
    results["reference_url"] = _file_url(ref_name)

    return JSONResponse(results)
