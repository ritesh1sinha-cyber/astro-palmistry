#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reading_palms_analysis.py — Practical Palmistry Analysis & Astro-Palm Confluence Engine

Synthesizes classical palm reading principles from 'READING PALMS: A Practical Course'
(The Aether Library) and maps them with Computer Vision (CV) detection from palm images.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Legacy rulebook imports retained only for historical reference; the
# measured path no longer fabricates from defaults.
try:
    from reading_palms_book_data import HAND_SHAPES, MAJOR_LINES_RULES, MOUNTS_DATA, THUMB_RULES  # noqa: F401
except Exception:  # pragma: no cover
    HAND_SHAPES = MAJOR_LINES_RULES = MOUNTS_DATA = THUMB_RULES = {}  # type: ignore


@dataclass
class PalmReadingCard:
    category: str  # "hand_shape" | "life_line" | "head_line" | "heart_line" | "fate_line" | "mounts" | "thumb" | "astro_confluence"
    feature_name: str
    title: str
    assessment: str
    prediction: str
    timing_milestone: str = ""
    severity: str = "info"  # "positive" | "info" | "warning" | "caution"
    astro_link: str = ""


def _measured_analysis(palm_data: dict[str, Any], *, name: str, gender: str,
                       hand: str) -> dict[str, Any]:
    """Return cards only for quality-gated features present in the CV output."""
    features = palm_data.get("features") if isinstance(palm_data.get("features"), dict) else palm_data
    quality = features.get("quality") or {}
    if str(quality.get("grade") or "poor").lower() == "poor":
        return {
            "meta": {"client_name": name, "gender": gender, "hand": hand},
            "cards": [],
            "cv_raw_features": features,
        }
    cards: list[PalmReadingCard] = []
    morphology = features.get("morphology") or {}
    hand_type = str(morphology.get("hand_type") or "").strip()
    if hand_type and hand_type.lower() != "unknown":
        cards.append(PalmReadingCard(
            category="hand_shape",
            feature_name=f"{hand_type.title()} hand morphology",
            title="Measured hand morphology",
            assessment="Classified from the supplied palm photograph.",
            prediction=f"The visible hand proportions are classified as {hand_type.title()}.",
        ))
    lines = features.get("lines") or {}
    for key, label in (
        ("life", "Life line"), ("head", "Head line"),
        ("heart", "Heart line"), ("fate", "Fate line"),
    ):
        row = lines.get(key) if isinstance(lines, dict) else None
        if not isinstance(row, dict) or not row.get("detected"):
            continue
        attrs = ", ".join(
            str(row[k]).replace("_", " ")
            for k in ("depth", "direction", "start_zone", "height", "start_relation")
            if row.get(k)
        )
        cards.append(PalmReadingCard(
            category=f"{key}_line",
            feature_name=label,
            title=f"Measured {label}",
            assessment=attrs or "Visible line detected.",
            prediction=f"{label} is visible in the supplied photograph; interpretation is tentative.",
        ))
    minor = features.get("minor_lines") or {}
    if isinstance(minor, dict):
        for key, row in minor.items():
            if isinstance(row, dict) and row.get("detected"):
                cards.append(PalmReadingCard(
                    category="minor_lines",
                    feature_name=str(row.get("title") or key),
                    title="Measured minor-line signal",
                    assessment="Detected in the supplied photograph.",
                    prediction="A visible minor-line signal is present; interpretation remains tentative.",
                ))
    return {
        "meta": {"client_name": name, "gender": gender, "hand": hand},
        "cards": cards,
        "cv_raw_features": features,
    }


def extract_features_from_image(img_path: str | Path, hand: str = "right") -> dict:
    """Extracts palm features using the Computer Vision (MediaPipe/OpenCV) analyzer."""
    path = Path(img_path)
    if not path.is_file():
        return {}

    try:
        from palm_api.analyzer import extract_features, features_for_json
        raw = extract_features(path, hand=hand)
        clean = features_for_json(raw)
        return clean
    except Exception as e:
        print(f"Warning: CV extraction failed on {path}: {e}")
        return {}


def analyze_palm(
    palm_data_or_image: dict | str | Path | None = None,
    pc: dict | None = None,
    *,
    name: str = "Native",
    gender: str = "male",
    hand: str = "right",
) -> dict:
    """
    Analyzes palm features against the complete Reading Palms rulebase.
    Supports either:
      1. Direct image path (runs Computer Vision palm analyzer on handprint).
      2. Feature dictionary.
    Optionally cross-correlates with natal chart (pc) for Astro-Palmistry confluence.
    """
    cv_data = {}
    if isinstance(palm_data_or_image, (str, Path)):
        img_p = Path(palm_data_or_image)
        if img_p.is_file():
            cv_data = extract_features_from_image(img_p, hand=hand)
            palm_data = cv_data
        else:
            palm_data = {}
    elif isinstance(palm_data_or_image, dict):
        palm_data = palm_data_or_image
    else:
        palm_data = {}

    # The served pipeline provides nested CV facts. Do not infer missing lines
    # or marks from defaults in the legacy rulebook below.
    if isinstance(palm_data, dict) and (
        "quality" in palm_data or "features" in palm_data or "lines" in palm_data
    ):
        return _measured_analysis(
            palm_data, name=name, gender=gender, hand=hand)

    # No measured pipeline payload — do not fabricate lines, mounts, or fixed
    # age milestones. Preserve quality gate: return empty, evidence-only result.
    return {
        "meta": {
            "client_name": name,
            "gender": gender,
            "hand": hand,
            "hand_analyzed": hand,
            "analysis_datetime": str(datetime.now()),
            "cv_features_detected": False,
        },
        "cards": [],
        "cv_raw_features": {},
        "summary": {
            "total_features_evaluated": 0,
            "dominant_element": "Unknown",
            "cv_marks_found": 0,
            "key_strengths": [],
        },
    }
