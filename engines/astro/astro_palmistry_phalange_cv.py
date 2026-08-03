#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CV phalange line counter for Astro-Palmistry (Saraswati Ch. XVII).

Uses MediaPipe hand landmarks (same stack as palm_api) to crop each phalange,
count vertical lines, and flag blurry/small ROIs so the client can re-upload
close-up finger + thumb photos.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import cv2
import numpy as np

FINGERS = {
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
}
THUMB = (1, 2, 3, 4)

MIN_ROI_W, MIN_ROI_H = 14, 12
MIN_SHARPNESS = 90.0
MAX_LINES = 22
MIN_PEAK_SEP = 3

# Filename hints: left_index.jpg, right_thumb.jpg, left_palm.jpg, percussion_right.jpg
SLOT_RE = re.compile(
    r"(?:(left|right)[_\-]?(palm|index|middle|ring|pinky|thumb|percussion))|"
    r"(?:(index|middle|ring|pinky|thumb|percussion)[_\-]?(left|right))",
    re.I,
)


def _get_landmarks(bgr: np.ndarray) -> tuple[np.ndarray | None, str]:
    from palm_api.analyzer import detect_hand_landmarks
    return detect_hand_landmarks(bgr)


def _roi_sharpness(gray: np.ndarray) -> float:
    if gray.size < 16:
        return 0.0
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _phalange_box(pts: np.ndarray, a: int, b: int, img_w: int, img_h: int) -> tuple[int, int, int, int]:
    p1, p2 = pts[a], pts[b]
    cx, cy = (p1 + p2) / 2
    dx, dy = abs(p2[0] - p1[0]), abs(p2[1] - p1[1])
    hw = max(dx * 0.5, 14)
    hh = max(dy * 0.45, 12)
    x0 = int(max(0, cx - hw))
    x1 = int(min(img_w, cx + hw))
    y0 = int(max(0, min(p1[1], p2[1]) - hh * 0.15))
    y1 = int(min(img_h, max(p1[1], p2[1]) + hh * 0.15))
    return x0, y0, x1, y1


def _count_vertical_lines(roi_bgr: np.ndarray) -> tuple[int, float, str]:
    """Return (count, sharpness, quality). quality: good|fair|poor."""
    if roi_bgr is None or roi_bgr.size == 0:
        return 0, 0.0, "poor"
    h, w = roi_bgr.shape[:2]
    if h < MIN_ROI_H or w < MIN_ROI_W:
        return 0, 0.0, "poor"

    gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    sharp = _roi_sharpness(gray)
    if sharp < MIN_SHARPNESS * 0.5:
        return 0, sharp, "poor"

    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(4, 4))
    gray = clahe.apply(gray)
    sx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    vert = np.clip(np.abs(sx) - 0.4 * np.abs(sy), 0, None)
    vert = cv2.normalize(vert, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    _, bw = cv2.threshold(vert, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 1), np.uint8))
    col = bw.sum(axis=0).astype(float)
    if col.max() < 1:
        return 0, sharp, "poor" if sharp < MIN_SHARPNESS else "fair"

    thresh = max(col.mean() * 1.4, col.max() * 0.32)
    peaks: list[int] = []
    for x in range(2, w - 2):
        if col[x] >= thresh and col[x] >= col[x - 1] and col[x] >= col[x + 1]:
            if not peaks or x - peaks[-1] >= MIN_PEAK_SEP:
                peaks.append(x)

    count = min(len(peaks), MAX_LINES)
    if sharp < MIN_SHARPNESS or count >= MAX_LINES:
        q = "fair"
    else:
        q = "good"
    if sharp < MIN_SHARPNESS * 0.75 or h < MIN_ROI_H + 4:
        q = "poor"
    return count, sharp, q


def _draw_roi(img: np.ndarray, box: tuple[int, int, int, int], label: str, color: tuple[int, int, int]) -> None:
    x0, y0, x1, y1 = box
    cv2.rectangle(img, (x0, y0), (x1, y1), color, 2)
    cv2.putText(img, label, (x0, max(12, y0 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)


def count_phalanges_one_hand(
    bgr: np.ndarray,
    handedness: str = "right",
    overlay_path: Path | None = None,
) -> dict[str, Any]:
    pts, err = _get_landmarks(bgr)
    if pts is None:
        return {"error": err, "hand": handedness, "quality": "poor"}

    h, w = bgr.shape[:2]
    overlay = bgr.copy() if overlay_path else None
    rois: list[dict[str, Any]] = []
    out: dict[str, Any] = {
        "hand": handedness,
        "phalanges": {},
        "thumb": {},
        "percussion": {"count": 0, "quality": "poor"},
        "rois": rois,
    }

    for fname, (mcp, pip, dip, tip) in FINGERS.items():
        finger_data: dict[str, Any] = {}
        for key, (a, b) in (("phalange_2", (pip, dip)), ("phalange_3", (dip, tip))):
            box = _phalange_box(pts, a, b, w, h)
            x0, y0, x1, y1 = box
            roi = bgr[y0:y1, x0:x1]
            cnt, sharp, qual = _count_vertical_lines(roi)
            finger_data[key] = cnt
            rois.append({
                "hand": handedness,
                "finger": fname,
                "phalange": key,
                "count": cnt,
                "sharpness": round(sharp, 1),
                "quality": qual,
                "box": box,
            })
            if overlay is not None:
                col = (0, 200, 0) if qual == "good" else (0, 180, 255) if qual == "fair" else (0, 0, 255)
                _draw_roi(overlay, box, f"{fname[:3]}{key[-1]}:{cnt}", col)
        finger_data["total"] = finger_data["phalange_2"] + finger_data["phalange_3"]
        out["phalanges"][fname] = finger_data

    _, mcp, ip, tip = THUMB
    for key, (a, b) in (("phalange_3", (ip, tip)), ("area", (mcp, ip))):
        box = _phalange_box(pts, a, b, w, h)
        x0, y0, x1, y1 = box
        cnt, sharp, qual = _count_vertical_lines(bgr[y0:y1, x0:x1])
        out["thumb"][key] = cnt
        rois.append({
            "hand": handedness,
            "finger": "thumb",
            "phalange": key,
            "count": cnt,
            "sharpness": round(sharp, 1),
            "quality": qual,
            "box": box,
        })
        if overlay is not None:
            col = (0, 200, 0) if qual == "good" else (0, 180, 255) if qual == "fair" else (0, 0, 255)
            _draw_roi(overlay, box, f"th{key[-1]}:{cnt}", col)

    pinky_mcp = pts[17]
    box = (
        int(max(0, pinky_mcp[0] - 30)),
        int(max(0, pinky_mcp[1] - 15)),
        int(min(w, pinky_mcp[0] + 6)),
        int(min(h, pinky_mcp[1] + 70)),
    )
    x0, y0, x1, y1 = box
    cnt, sharp, qual = _count_vertical_lines(bgr[y0:y1, x0:x1])
    out["percussion"] = {"count": cnt, "quality": qual, "sharpness": round(sharp, 1)}
    rois.append({
        "hand": handedness,
        "finger": "percussion",
        "phalange": "edge",
        "count": cnt,
        "sharpness": round(sharp, 1),
        "quality": qual,
        "box": box,
    })
    if overlay is not None:
        col = (0, 200, 0) if qual == "good" else (0, 180, 255) if qual == "fair" else (0, 0, 255)
        _draw_roi(overlay, box, f"perc:{cnt}", col)
        overlay_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(overlay_path), overlay)

    poor = sum(1 for r in rois if r["quality"] == "poor")
    fair = sum(1 for r in rois if r["quality"] == "fair")
    if poor >= 4:
        out["quality"] = "poor"
    elif poor >= 1 or fair >= 5:
        out["quality"] = "fair"
    else:
        out["quality"] = "good"
    return out


def aggregate_for_engine(left: dict, right: dict) -> dict[str, int]:
    def g(hand: dict, finger: str, key: str) -> int:
        ph = (hand.get("phalanges") or {}).get(finger) or {}
        return int(ph.get(key, 0) or 0)

    def ft(hand: dict, finger: str) -> int:
        ph = (hand.get("phalanges") or {}).get(finger) or {}
        return int(ph.get("total", 0) or 0)

    thumb_l = int((left.get("thumb") or {}).get("area", 0) or 0)
    thumb_r = int((right.get("thumb") or {}).get("area", 0) or 0)
    perc_l = int((left.get("percussion") or {}).get("count", 0) or 0)
    perc_r = int((right.get("percussion") or {}).get("count", 0) or 0)

    return {
        "moon_a": g(left, "middle", "phalange_2") + g(left, "middle", "phalange_3"),
        "moon_b": g(right, "middle", "phalange_2") + g(right, "middle", "phalange_3"),
        "month_a": g(left, "index", "phalange_2") + g(left, "index", "phalange_3"),
        "month_b": g(right, "index", "phalange_2") + g(right, "index", "phalange_3"),
        "day_left": ft(left, "ring"),
        "day_right": ft(right, "ring"),
        "asc_a": g(left, "pinky", "phalange_2") + g(left, "pinky", "phalange_3"),
        "asc_b": g(right, "pinky", "phalange_2") + g(right, "pinky", "phalange_3"),
        "thumb_lines": thumb_l + thumb_r,
        "percussion_lines": perc_l + perc_r,
    }


def _retake_slots(left: dict, right: dict) -> list[dict[str, str]]:
    """List close-up photos needed when full-palm CV is unclear."""
    slots: list[dict[str, str]] = []
    for hand_label, data in (("left", left), ("right", right)):
        if data.get("error"):
            slots.append({
                "slot": f"{hand_label}_palm",
                "label": f"{hand_label.title()} full palm (fingers spread, flat, good light)",
                "reason": data.get("error", "hand not detected"),
            })
            for finger in ("index", "middle", "ring", "pinky", "thumb"):
                slots.append({
                    "slot": f"{hand_label}_{finger}",
                    "label": f"{hand_label.title()} {finger} close-up (phalanges visible)",
                    "reason": "full palm unusable",
                })
            continue
        for r in data.get("rois") or []:
            if r.get("quality") != "good":
                finger = r["finger"]
                ph = r.get("phalange", "")
                slot = f"{hand_label}_{finger}" if finger != "percussion" else f"{hand_label}_percussion"
                slots.append({
                    "slot": slot,
                    "label": f"{hand_label.title()} {finger} close-up ({ph})",
                    "reason": f"blurry or too small (sharp={r.get('sharpness')}, count={r.get('count')})",
                })
    # dedupe by slot
    seen: set[str] = set()
    uniq: list[dict[str, str]] = []
    for s in slots:
        if s["slot"] in seen:
            continue
        seen.add(s["slot"])
        uniq.append(s)
    return uniq


def analyze_from_paths(
    image_paths: list[Path],
    overlay_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Accept 2+ images. Detects left/right full palms from filenames or order.
    Returns aggregated counts + quality + needs_retake.
    """
    left_path: Path | None = None
    right_path: Path | None = None
    extras: list[Path] = []

    for p in image_paths:
        name = p.name.lower()
        m = SLOT_RE.search(name)
        if m:
            g = m.groups()
            hand = (g[0] or g[6] or "").lower()
            part = (g[1] or g[5] or "").lower()
            if part == "palm":
                if hand == "left":
                    left_path = p
                elif hand == "right":
                    right_path = p
            else:
                extras.append(p)
        elif "left" in name and "palm" in name:
            left_path = p
        elif "right" in name and "palm" in name:
            right_path = p
        elif left_path is None:
            left_path = p
        elif right_path is None:
            right_path = p
        else:
            extras.append(p)

    if left_path is None or right_path is None:
        return {
            "error": "need_two_palms",
            "message": "Upload left and right full palm photos (name files left_palm.jpg and right_palm.jpg).",
            "needs_retake": [
                {"slot": "left_palm", "label": "Left full palm", "reason": "missing"},
                {"slot": "right_palm", "label": "Right full palm", "reason": "missing"},
            ],
        }

    ov_l = overlay_dir / f"{left_path.stem}_phalanges.jpg" if overlay_dir else None
    ov_r = overlay_dir / f"{right_path.stem}_phalanges.jpg" if overlay_dir else None

    left_bgr = cv2.imread(str(left_path))
    right_bgr = cv2.imread(str(right_path))
    if left_bgr is None or right_bgr is None:
        return {"error": "could_not_read_images"}

    left = count_phalanges_one_hand(left_bgr, "left", ov_l)
    right = count_phalanges_one_hand(right_bgr, "right", ov_r)
    agg = aggregate_for_engine(left, right)
    needs = _retake_slots(left, right)

    overall = "good"
    for h in (left, right):
        q = h.get("quality", "poor")
        if q == "poor":
            overall = "poor"
            break
        if q == "fair":
            overall = "fair"

    return {
        "left": left,
        "right": right,
        "aggregated": agg,
        "quality": overall,
        "needs_retake": needs,
        "overlay_left": str(ov_l) if ov_l and ov_l.is_file() else None,
        "overlay_right": str(ov_r) if ov_r and ov_r.is_file() else None,
        "sources": {"left": str(left_path), "right": str(right_path)},
    }


def counts_from_cv_analysis(analysis: dict[str, Any], *, bright_half: bool = True) -> dict[str, int] | None:
    agg = analysis.get("aggregated")
    if not agg:
        return None
    return dict(agg)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--left", required=True)
    ap.add_argument("--right", required=True)
    ap.add_argument("--overlay-dir", default="")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    ov = Path(args.overlay_dir) if args.overlay_dir else None
    data = analyze_from_paths([Path(args.left), Path(args.right)], ov)
    text = json.dumps(data, indent=2, default=str)
    if args.json:
        Path(args.json).write_text(text, encoding="utf-8")
    print(text)
