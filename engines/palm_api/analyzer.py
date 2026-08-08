#!/usr/bin/env python3
"""
Extract measurable palm features from a photo (no LLM).

Output: JSON facts only — lines, mounts, morphology, quality score.
Use palm_interpret.py to apply palm_rules.yaml.

  python3 palm_features.py right.jpg -o features.json --overlay overlay.jpg
  python3 palm_features.py left.jpg -o left.json --hand left
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from palm_api.palm_lines import (
    catmull_rom,
    detect_major_lines,
    detect_minor_lines,
)
from palm_api.special_marks import detect_special_marks

# ---------------------------------------------------------------------------
# MediaPipe (optional but recommended)
# ---------------------------------------------------------------------------


_landmarker = None


def _ensure_hand_model() -> None:
    from palm_api.paths import HAND_MODEL, HAND_MODEL_URL

    if HAND_MODEL.is_file():
        return
    import urllib.request

    HAND_MODEL.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(HAND_MODEL_URL, HAND_MODEL)


def _landmarks_to_array(landmarks, w: int, h: int) -> np.ndarray:
    pts = np.zeros((21, 2), dtype=np.float32)
    for i, lm in enumerate(landmarks):
        x = getattr(lm, "x", lm[0] if isinstance(lm, (list, tuple)) else 0)
        y = getattr(lm, "y", lm[1] if isinstance(lm, (list, tuple)) else 0)
        pts[i, 0] = float(x) * w
        pts[i, 1] = float(y) * h
    return pts


def _get_landmarker():
    global _landmarker
    if _landmarker is not None:
        return _landmarker
    _ensure_hand_model()
    mp = _import_mediapipe()

    from palm_api.paths import HAND_MODEL

    options = mp.tasks.vision.HandLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(HAND_MODEL)),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_hands=2,
        min_hand_detection_confidence=0.5,
    )
    _landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)
    return _landmarker


def _detect_legacy(rgb: np.ndarray, w: int, h: int) -> np.ndarray | None:
    mp = _import_mediapipe()

    if not hasattr(mp, "solutions"):
        return None
    hands_module = mp.solutions.hands
    with hands_module.Hands(
        static_image_mode=True,
        max_num_hands=2,
        model_complexity=1,
        min_detection_confidence=0.5,
    ) as hands:
        res = hands.process(rgb)
    if not res.multi_hand_landmarks:
        return None
    best_pts = None
    best_area = 0.0
    for hl in res.multi_hand_landmarks:
        pts = _landmarks_to_array(hl.landmark, w, h)
        area = cv2.contourArea(cv2.convexHull(pts.astype(np.int32)))
        if area > best_area:
            best_area = area
            best_pts = pts
    return best_pts


def _import_mediapipe():
    """Import MediaPipe without letting `core/queue.py` shadow stdlib `queue`.

    Several launchers put the project `core/` directory on PYTHONPATH. That makes
    `import queue` resolve to our Redis job queue module, which then crashes
    MediaPipe's own imports and silently kills landmark detection.
    """
    shadowed = [p for p in list(sys.path)
                if Path(p).resolve().name == "core"
                and (Path(p) / "queue.py").is_file()]
    for p in shadowed:
        sys.path.remove(p)
    try:
        # Drop a poisoned partial import if a previous attempt failed mid-way.
        for name in list(sys.modules):
            if name == "queue" or name.startswith("queue."):
                mod = sys.modules.get(name)
                origin = getattr(mod, "__file__", "") or ""
                if origin.replace("\\", "/").endswith("/core/queue.py"):
                    sys.modules.pop(name, None)
        import mediapipe as mp
        return mp
    finally:
        for p in reversed(shadowed):
            if p not in sys.path:
                sys.path.insert(0, p)


def detect_hand_landmarks(bgr: np.ndarray) -> tuple[np.ndarray | None, str]:
    """Returns (21,2) pixel coords or None."""
    try:
        mp = _import_mediapipe()
    except ImportError:
        return None, "mediapipe_not_installed"

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = bgr.shape[:2]

    pts = _detect_legacy(rgb, w, h)
    if pts is not None:
        return pts, "ok"

    try:
        landmarker = _get_landmarker()
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect(mp_image)
    except Exception as exc:
        return None, f"hand_model_error:{exc}"

    if not result.hand_landmarks:
        return None, "no_hand_detected"

    best_pts = None
    best_area = 0.0
    for hl in result.hand_landmarks:
        pts = _landmarks_to_array(hl, w, h)
        area = cv2.contourArea(cv2.convexHull(pts.astype(np.int32)))
        if area > best_area:
            best_area = area
            best_pts = pts
    return best_pts, "ok"


# ---------------------------------------------------------------------------
# Palm ROI & normalization
# ---------------------------------------------------------------------------


def _palm_mask_from_landmarks(bgr: np.ndarray, pts: np.ndarray) -> np.ndarray:
    h, w = bgr.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    # Palm hull: wrist + finger bases (exclude fingertips)
    palm_ids = [0, 1, 2, 5, 9, 13, 17]
    hull_pts = pts[palm_ids].astype(np.int32)
    cv2.fillConvexPoly(mask, hull_pts, 255)
    # Expand slightly
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    mask = cv2.dilate(mask, kernel, iterations=2)
    return mask


def _normalize_palm(bgr: np.ndarray, pts: np.ndarray, size: int = 400) -> tuple[np.ndarray, np.ndarray, Any]:
    """Warp palm to canonical frame; return warped BGR, warped landmarks, transform meta."""
    wrist = pts[0]
    mid_mcp = pts[9]
    index_mcp = pts[5]
    # Palm up: wrist bottom, fingers top
    src = np.float32([wrist, mid_mcp, index_mcp])
    dst = np.float32(
        [
            [size * 0.5, size * 0.92],
            [size * 0.5, size * 0.35],
            [size * 0.72, size * 0.38],
        ]
    )
    M = cv2.getAffineTransform(src, dst)
    warped = cv2.warpAffine(bgr, M, (size, size))
    ones = np.ones((21, 1), dtype=np.float32)
    pts_h = np.hstack([pts, ones])
    M3 = np.vstack([M, [0, 0, 1]])
    wpts = (M3 @ pts_h.T).T[:, :2]
    return warped, wpts, {"size": size, "M": M}


def _inverse_affine_points(
    points: list[tuple[float, float]],
    M: np.ndarray | None,
    flip: bool,
    orig_w: int,
) -> list[tuple[float, float]]:
    """Map canonical-frame points back to ORIGINAL image coordinates."""
    if M is None:
        return [(float(x), float(y)) for x, y in points]
    M3 = np.vstack([np.asarray(M, dtype=np.float64), [0, 0, 1]])
    inv = np.linalg.inv(M3)
    out: list[tuple[float, float]] = []
    for x, y in points:
        v = inv @ np.array([x, y, 1.0])
        wx, wy = float(v[0]), float(v[1])
        if flip:
            wx = float(orig_w - 1) - wx
        out.append((wx, wy))
    return out


def _thumb_on_image_left(pts: np.ndarray) -> bool:
    """True when the thumb is on the left side of the original photo (left-palm selfies)."""
    thumb_x = float(np.mean(pts[[1, 2, 3, 4], 0]))
    pinky_x = float(np.mean(pts[[17, 18, 19], 0]))
    return thumb_x < pinky_x


def _mirror_image_and_landmarks(
    bgr: np.ndarray,
    pts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Mirror photo + landmarks so thumb is on the same side as a right-palm shot."""
    h, w = bgr.shape[:2]
    flipped = cv2.flip(bgr, 1)
    out_pts = pts.copy()
    out_pts[:, 0] = float(w - 1) - out_pts[:, 0]
    return flipped, out_pts


def _prepare_warped_palm(
    bgr: np.ndarray,
    pts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """
    Normalize palm to canonical frame (thumb mound right, pinky left).
    Left-palm photos are mirrored before warp so the same line CV works for both hands.
    """
    flip = _thumb_on_image_left(pts)
    work_bgr, work_pts = (bgr, pts) if not flip else _mirror_image_and_landmarks(bgr, pts)
    warped, wpts, meta = _normalize_palm(work_bgr, work_pts)
    meta["canonical_flip"] = flip
    return warped, wpts, meta


def _skin_fallback_mask(bgr: np.ndarray) -> np.ndarray:
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    mask = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    return mask


# ---------------------------------------------------------------------------
# Line & ridge processing
# ---------------------------------------------------------------------------


def _enhance_ridges(gray: np.ndarray, mask: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    g = clahe.apply(gray)
    g = cv2.GaussianBlur(g, (3, 3), 0)
    # Blackhat emphasizes dark ridges on light palm
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    bh = cv2.morphologyEx(g, cv2.MORPH_BLACKHAT, kernel)
    bh = cv2.normalize(bh, None, 0, 255, cv2.NORM_MINMAX)
    _, bw = cv2.threshold(bh, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bw = cv2.bitwise_and(bw, mask)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    return bw


def _extract_segments(
    ridge_bin: np.ndarray,
    min_len: int = 25,
    *,
    hough_threshold: int = 35,
    max_line_gap: int = 12,
) -> list[dict[str, Any]]:
    edges = cv2.Canny(ridge_bin, 50, 150)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=hough_threshold,
        minLineLength=min_len,
        maxLineGap=max_line_gap,
    )
    segs: list[dict[str, Any]] = []
    if lines is None:
        return segs
    for x1, y1, x2, y2 in lines[:, 0]:
        dx, dy = x2 - x1, y2 - y1
        length = float(np.hypot(dx, dy))
        angle = float(np.degrees(np.arctan2(dy, dx)))  # -180..180
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        segs.append(
            {
                "x1": int(x1),
                "y1": int(y1),
                "x2": int(x2),
                "y2": int(y2),
                "mx": mx,
                "my": my,
                "length": length,
                "angle": angle,
            }
        )
    return segs


def _extract_heart_segments(ridge_bin: np.ndarray, size: int) -> list[dict[str, Any]]:
    """Second pass on upper palm — heart line is often faint vs life/head."""
    h = int(size * 0.46)
    roi = ridge_bin[:h, :].copy()
    if roi.size < 100:
        return []
    segs = _extract_segments(roi, min_len=18, hough_threshold=22, max_line_gap=18)
    heart: list[dict[str, Any]] = []
    for s in segs:
        my = s["my"] / size
        ang = abs(s["angle"])
        if my > 0.44:
            continue
        if ang < 40 or ang > 140:
            if s["length"] >= 20:
                heart.append(s)
    return heart


def _norm_landmarks(wpts: np.ndarray, size: int) -> np.ndarray:
    return wpts.astype(np.float64) / float(size)


def _palm_line_axes(lm: np.ndarray) -> dict[str, float]:
    """
    Canonical palm frame (see _normalize_palm): wrist bottom, fingers top.
    Thumb / life line sit on one lateral edge; fate runs vertically through centre.
    """
    wrist, thumb_mcp, index_mcp, middle_mcp = lm[0], lm[2], lm[5], lm[9]
    # Thumb chain is landmarks 1–4; do not mix in pinky (17) which is the opposite edge
    thumb_x = float(np.mean([lm[1][0], lm[2][0], lm[3][0], lm[4][0]]))
    pinky_x = float(np.mean([lm[17][0], lm[18][0], lm[19][0]]))
    index_x = float(index_mcp[0])
    life_on_left = thumb_x < pinky_x
    fate_x = float((wrist[0] + middle_mcp[0]) / 2.0)
    if life_on_left:
        life_x_max = fate_x - 0.07
        life_x_max = max(thumb_x - 0.05, min(life_x_max, fate_x - 0.04))
        life_x_min = thumb_x - 0.12
    else:
        # Thumb on right: life arc sits right of the fate column up to the thumb mound
        life_x_min = fate_x + 0.04
        life_x_max = min(0.98, thumb_x + 0.06)
    head_y = float((index_mcp[1] + middle_mcp[1]) / 2.0 + 0.06)
    heart_y_max = float(min(index_mcp[1], middle_mcp[1]) + 0.04)
    return {
        "fate_x": fate_x,
        "life_x_max": life_x_max,
        "life_x_min": life_x_min,
        "life_on_left": 1.0 if life_on_left else 0.0,
        "thumb_x": thumb_x,
        "head_y": head_y,
        "heart_y_max": heart_y_max,
    }


def _palm_line_anchors(
    lm: np.ndarray, axes: dict[str, float], size: int
) -> dict[str, tuple[float, float]]:
    """Normalized (x,y) targets for snapping numbered dots onto each major line."""
    index_mcp, wrist = lm[5], lm[0]
    fx, hy, head_y = axes["fate_x"], axes["heart_y_max"], axes["head_y"]
    life_on_left = axes.get("life_on_left", 1.0) >= 0.5
    # Life crease runs along the inner edge of the Venus mount (thumb ball)
    x0, y0, x1, y1 = _mount_zones((lm * float(size)).astype(np.float32), size)["venus"]
    if life_on_left:
        arc_x = (x0 * 0.45 + x1 * 0.55) / float(size)
    else:
        arc_x = (x0 * 0.55 + x1 * 0.45) / float(size)
    arc_y = (y0 * 0.32 + y1 * 0.68) / float(size)
    arc_x = max(0.05, min(0.95, float(arc_x)))
    arc_y = max(0.35, min(0.82, float(arc_y)))
    return {
        "life": (arc_x, arc_y),
        "life_on_left": life_on_left,
        "fate": (fx, 0.52),
        "head": (fx, head_y),
        "heart": (fx, max(0.18, hy - 0.04)),
    }


def _on_life_side(mx: float, axes: dict[str, float]) -> bool:
    if axes.get("life_on_left", 1.0) >= 0.5:
        return mx < axes["life_x_max"]
    return mx > axes["life_x_min"]


def _snap_marker_to_group(
    group: list[dict[str, Any]],
    anchor: tuple[float, float],
    size: int,
) -> tuple[int, int]:
    if not group:
        ax, ay = anchor
        return int(ax * size), int(ay * size)
    ax, ay = anchor

    def _dist(seg: dict[str, Any]) -> float:
        return (seg["mx"] / size - ax) ** 2 + (seg["my"] / size - ay) ** 2

    best = min(group, key=_dist)
    return int(best["mx"]), int(best["my"])


def _segment_type_scores(
    s: dict[str, Any],
    size: int,
    axes: dict[str, float] | None = None,
) -> dict[str, float]:
    """Score ridge segment vs major lines using position + angle (landmark-guided)."""
    mx, my = s["mx"] / size, s["my"] / size
    ang = abs(s["angle"])
    length = s["length"]
    horiz = ang < 32 or ang > 148
    vert = 72 < ang < 108
    diag = 8 < ang < 72

    scores: dict[str, float] = {"life": 0.0, "head": 0.0, "heart": 0.0, "fate": 0.0}
    if axes is None:
        # Fallback without landmarks
        if my < 0.42 and horiz and length > 18:
            scores["heart"] = 2.0 + length / 40.0
        if 0.34 < my < 0.58 and horiz and length > 22:
            scores["head"] = 2.0 + length / 45.0
        if mx < 0.40 and 0.28 < my < 0.92 and diag and length > 25:
            scores["life"] = 2.5 + length / 50.0
        if 0.44 < mx < 0.58 and 0.32 < my < 0.92 and vert and length > 20:
            scores["fate"] = 2.5 + length / 42.0
        return scores

    fate_x = axes["fate_x"]
    life_x_max = axes["life_x_max"]
    life_x_min = axes.get("life_x_min", 0.0)
    life_on_left = axes.get("life_on_left", 1.0) >= 0.5
    head_y = axes["head_y"]
    heart_y_max = axes["heart_y_max"]
    dx_fate = abs(mx - fate_x)
    on_life_side = _on_life_side(mx, axes)

    # Heart — upper horizontal arc only (not finger bases)
    if my < heart_y_max + 0.05 and horiz and length >= 16:
        scores["heart"] = 3.4 + length / 35.0 + (heart_y_max - my) * 6.0
    if my > heart_y_max + 0.10:
        scores["heart"] = 0.0

    # Head — horizontal across upper-mid palm
    if heart_y_max + 0.03 < my < head_y + 0.10 and horiz and length >= 20:
        scores["head"] = 3.2 + length / 40.0 - abs(my - head_y) * 4.0

    # Fate — narrow vertical column through palm centre
    if 0.34 < my < 0.88 and length >= 18 and dx_fate < 0.075:
        if vert or (68 < ang < 112):
            scores["fate"] = 5.0 + length / 36.0 - dx_fate * 18.0
    if dx_fate > 0.09:
        scores["fate"] = 0.0

    # Life — thumb-side curved arc; never horizontal bands or central vertical
    if on_life_side and 0.30 < my < 0.92 and length >= 20:
        side_bonus = (life_x_max - mx) * 9.0 if life_on_left else (mx - life_x_min) * 9.0
        if horiz:
            scores["life"] = min(scores["life"], 0.4)
        elif diag and not vert:
            scores["life"] = 4.5 + length / 40.0 + side_bonus
        elif not vert:
            scores["life"] = 2.2 + side_bonus * 0.5
    if vert and dx_fate < 0.10:
        scores["life"] = min(scores["life"], 0.3)
    if not on_life_side and dx_fate < 0.12:
        scores["life"] = min(scores["life"], 0.4)

    return scores


def _refine_line_groups(
    groups: dict[str, list[dict[str, Any]]],
    axes: dict[str, float],
    size: int,
) -> dict[str, list[dict[str, Any]]]:
    """Move misclassified segments between life (thumb side) and fate (centre vertical)."""
    fate_x = axes["fate_x"]
    refined: dict[str, list[dict[str, Any]]] = {k: [] for k in groups}

    for kind, segs in groups.items():
        for s in segs:
            mx, my = s["mx"] / size, s["my"] / size
            ang = abs(s["angle"])
            vert = 72 < ang < 108
            dx = abs(mx - fate_x)
            on_life = _on_life_side(mx, axes)

            target = kind
            if vert and dx < 0.085:
                target = "fate"
            elif on_life and not (vert and dx < 0.07):
                if kind == "fate":
                    target = "life"
            elif kind == "life" and not on_life and vert and dx < 0.11:
                target = "fate"
            elif kind == "fate" and on_life and dx > 0.07:
                target = "life"

            refined[target].append(s)

    return refined


def _swap_life_fate_if_markers_wrong(
    groups: dict[str, list[dict[str, Any]]],
    axes: dict[str, float],
    anchors: dict[str, tuple[float, float]],
    size: int,
) -> dict[str, list[dict[str, Any]]]:
    """If fate dot would land on thumb arc and life dot on centre, swap pools."""
    life_g = groups.get("life") or []
    fate_g = groups.get("fate") or []
    if not life_g or not fate_g:
        return groups
    lx, ly = _snap_marker_to_group(life_g, anchors["life"], size)
    fx, fy = _snap_marker_to_group(fate_g, anchors["fate"], size)
    fate_x = axes["fate_x"]
    life_nx, fate_nx = lx / size, fx / size
    # Fate marker must be near centre column; life marker on thumb side
    fate_on_centre = abs(fate_nx - fate_x) < 0.10
    life_on_thumb = _on_life_side(life_nx, axes)
    fate_on_thumb = _on_life_side(fate_nx, axes)
    if fate_on_thumb and not fate_on_centre and life_on_thumb:
        return {
            **groups,
            "life": fate_g,
            "fate": life_g,
        }
    return groups


def _filter_segments_by_angle(
    group: list[dict[str, Any]],
    *,
    horizontal: bool | None = None,
    vertical: bool | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in group:
        ang = abs(s["angle"])
        horiz = ang < 32 or ang > 148
        vert = 68 < ang < 112
        if horizontal is True and not horiz:
            continue
        if vertical is True and not vert:
            continue
        if horizontal is False and horiz:
            continue
        if vertical is False and vert:
            continue
        out.append(s)
    return out


def _snap_marker_filtered(
    group: list[dict[str, Any]],
    anchor: tuple[float, float],
    size: int,
    *,
    horizontal: bool | None = None,
    vertical: bool | None = None,
    y_range: tuple[float, float] | None = None,
) -> tuple[int, int]:
    ax, ay = anchor
    pool = _filter_segments_by_angle(group, horizontal=horizontal, vertical=vertical)
    if y_range is not None:
        y0, y1 = y_range
        pool = [s for s in pool if y0 <= s["my"] / size <= y1]
    if not pool:
        pool = group
    if pool:
        best = min(
            pool,
            key=lambda s: (s["mx"] / size - ax) ** 2 + (s["my"] / size - ay) ** 2,
        )
        return int(best["mx"]), int(best["my"])
    return int(ax * size), int(ay * size)


def _life_marker_from_landmarks(
    group: list[dict[str, Any]],
    anchors: dict[str, tuple[float, float]],
    size: int,
) -> tuple[int, int]:
    """
    Life line dot on the curved crease along the Venus mount (landmark anchor).
    Ridge Hough segments are too noisy here; only snap if a segment lies within ~5% of anchor.
    """
    arc = anchors.get("life") or (0.77, 0.68)
    ax, ay = arc
    curved = _filter_segments_by_angle(group, horizontal=False, vertical=False)
    pool = [s for s in (curved or group) if 0.48 < s["my"] / size < 0.78]

    def _dist2(seg: dict[str, Any]) -> float:
        return (seg["mx"] / size - ax) ** 2 + (seg["my"] / size - ay) ** 2

    if pool:
        best = min(pool, key=_dist2)
        if _dist2(best) < 0.028**2:
            return int(best["mx"]), int(best["my"])
    return int(ax * size), int(ay * size)


def _line_marker_position(
    group: list[dict[str, Any]],
    kind: str,
    size: int,
    anchors: dict[str, tuple[float, float]] | None = None,
) -> tuple[int, int]:
    """Snap numbered dot to ridge segment nearest anatomical anchor."""
    if anchors is None:
        return _group_centroid(group)
    if kind == "life":
        return _life_marker_from_landmarks(group, anchors, size)
    anchor = anchors.get(kind)
    if anchor is None:
        return _group_centroid(group)
    if kind == "head":
        return _snap_marker_filtered(
            group, anchor, size, horizontal=True, y_range=(0.40, 0.58)
        )
    if kind == "heart":
        return _snap_marker_filtered(
            group, anchor, size, horizontal=True, y_range=(0.18, 0.44)
        )
    if kind == "fate":
        return _snap_marker_filtered(
            group, anchor, size, vertical=True, y_range=(0.38, 0.78)
        )
    return _snap_marker_to_group(group, anchor, size)


def _classify_segments(
    segs: list[dict[str, Any]],
    size: int,
    wpts: np.ndarray | None = None,
) -> dict[str, Any]:
    """Map segments to line types — each segment assigned to at most one line."""
    lm = _norm_landmarks(wpts, size) if wpts is not None and len(wpts) >= 21 else None
    axes = _palm_line_axes(lm) if lm is not None else None

    groups: dict[str, list[dict[str, Any]]] = {
        "life": [],
        "head": [],
        "heart": [],
        "fate": [],
    }
    for s in segs:
        scores = _segment_type_scores(s, size, axes)
        best = max(scores, key=scores.get)
        if scores[best] < 1.5:
            continue
        groups[best].append(s)

    anchors: dict[str, tuple[float, float]] | None = None
    if axes is not None and lm is not None:
        groups = _refine_line_groups(groups, axes, size)
        anchors = _palm_line_anchors(lm, axes, size)
        groups = _swap_life_fate_if_markers_wrong(groups, axes, anchors, size)

    life, head, heart, fate = (
        groups["life"],
        groups["head"],
        groups["heart"],
        groups["fate"],
    )

    def _line_props(group: list[dict], kind: str, *, line_axes: dict[str, float] | None = None) -> dict[str, Any]:
        if not group:
            return {"detected": False}
        ys = [s["my"] for s in group]
        xs = [s["mx"] for s in group]
        lengths = [s["length"] for s in group]
        angles = [s["angle"] for s in group]
        avg_y = float(np.mean(ys)) / size
        avg_x = float(np.mean(xs)) / size
        depth = "deep" if np.mean(lengths) > 55 else ("thin" if np.mean(lengths) < 38 else "medium")
        out: dict[str, Any] = {"detected": True, "depth": depth, "segment_count": len(group)}

        if kind == "life":
            life_on_left = line_axes is not None and line_axes.get("life_on_left", 1.0) >= 0.5
            edge_x = avg_x if life_on_left else (1.0 - avg_x)
            if edge_x < 0.35:
                out["start_zone"] = "jupiter"
            elif edge_x < 0.48:
                out["start_zone"] = "mars"
            else:
                out["start_zone"] = "between"
        elif kind == "head":
            avg_ang = float(np.mean(angles))
            if avg_ang > 10 and avg_y > 0.4:
                out["direction"] = "moon"
            else:
                out["direction"] = "straight"
            # merged vs separated: life segments nearby at start
            life_low = [s for s in life if s["my"] / size > 0.55]
            head_high = [s for s in group if s["my"] / size < 0.52]
            if life_low and head_high:
                out["start_relation"] = "merged"
            else:
                out["start_relation"] = "separated"
        elif kind == "heart":
            out["height"] = "high" if avg_y < 0.32 else "normal"
            if avg_x < 0.4:
                out["start_zone"] = "jupiter"
            elif avg_x < 0.55:
                out["start_zone"] = "saturn"
            else:
                out["start_zone"] = "mercury_side"
        elif kind == "fate":
            if avg_y > 0.75:
                out["start_zone"] = "wrist"
            elif avg_y > 0.55:
                out["start_zone"] = "mid_palm"
            else:
                out["start_zone"] = "life_line"
            gaps = len(group) >= 3 and np.std(lengths) > 20
            out["quality"] = "broken" if gaps else "clear"
            out["reach"] = "saturn" if avg_y < 0.45 else "partial"
        return out

    return {
        "life": _line_props(life, "life", line_axes=axes),
        "head": _line_props(head, "head", line_axes=axes),
        "heart": _line_props(heart, "heart", line_axes=axes),
        "fate": _line_props(fate, "fate", line_axes=axes),
        "_groups": groups,
        "_anchors": anchors,
        "_axes": axes,
        "_raw_counts": {
            "life": len(life),
            "head": len(head),
            "heart": len(heart),
            "fate": len(fate),
        },
    }


# ---------------------------------------------------------------------------
# Mounts (rough prominence from texture variance in zones)
# ---------------------------------------------------------------------------


# Plain, jargon-free labels — the customer-facing report's finalize pass
# (see `palm_voice.polish_html`) strips literal "Mount of X" phrasing anywhere
# it appears, so these titles must already read in plain language rather than
# the formal palmistry name, or the heading is silently blanked out.
MOUNT_TITLES: dict[str, str] = {
    "jupiter": "The pad below your index finger",
    "saturn": "The pad below your middle finger",
    "apollo": "The pad below your ring finger",
    "mercury": "The pad below your little finger",
    "mars": "The pads at the base of your thumb",
    "venus": "The fleshy base of your thumb",
    "moon": "The lower outer edge of your palm",
}

# Order shown in numbered checklist and on overlay
MOUNT_CHECKLIST_ORDER = (
    "jupiter",
    "saturn",
    "apollo",
    "mercury",
    "mars",
    "venus",
    "moon",
)

FINGER_TITLES: dict[str, str] = {
    "index": "Index finger (Jupiter finger)",
    "middle": "Middle finger (Saturn finger)",
    "ring": "Ring finger (Apollo finger)",
    "pinky": "Little finger (Mercury finger)",
}


def _mount_zones(wpts: np.ndarray, size: int) -> dict[str, tuple[int, int, int, int]]:
    """Axis-aligned ROIs (x0,y0,x1,y1) in palm image pixels."""
    return {
        "jupiter": (int(size * 0.55), int(size * 0.30), int(size * 0.78), int(size * 0.48)),
        "saturn": (int(size * 0.42), int(size * 0.28), int(size * 0.58), int(size * 0.46)),
        "apollo": (int(size * 0.28), int(size * 0.26), int(size * 0.44), int(size * 0.44)),
        "mercury": (int(size * 0.08), int(size * 0.30), int(size * 0.28), int(size * 0.50)),
        "mars": (int(size * 0.50), int(size * 0.40), int(size * 0.68), int(size * 0.62)),
        "venus": (int(size * 0.62), int(size * 0.48), int(size * 0.92), int(size * 0.88)),
        "moon": (int(size * 0.02), int(size * 0.48), int(size * 0.35), int(size * 0.88)),
    }


def _score_mounts(gray: np.ndarray, mask: np.ndarray, wpts: np.ndarray, size: int) -> dict[str, str]:
    """Score mount fullness (prominent / moderate / flat).

    Older std-only scoring marked lined Venus as prominent but smooth fleshy
    Moon as flat. Combine (a) brightness vs palm mean (fuller pad is lighter
    on typical photos) with (b) mild texture, so a full Moon is not demoted
    just because Venus is busier with influence lines.
    """
    zones = _mount_zones(wpts, size)
    palm_vals = gray[mask > 0] if np.any(mask > 0) else gray.reshape(-1)
    palm_mean = float(np.mean(palm_vals)) if palm_vals.size else 128.0
    palm_std = float(np.std(palm_vals)) if palm_vals.size else 1.0
    palm_std = max(palm_std, 1.0)

    scores: dict[str, float] = {}
    for name, (x0, y0, x1, y1) in zones.items():
        roi = gray[y0:y1, x0:x1]
        mroi = mask[y0:y1, x0:x1]
        if roi.size < 50:
            scores[name] = 0.0
            continue
        vals = roi[mroi > 0] if np.any(mroi > 0) else roi.reshape(-1)
        mean_v = float(np.mean(vals))
        std_v = float(np.std(vals))
        # Fullness: brighter / softer pad relative to palm; texture secondary.
        fullness = (mean_v - palm_mean) / palm_std
        texture = std_v / palm_std
        score = 0.72 * fullness + 0.28 * texture
        # Venus grille / influence lines are a classical "full Venus" signal.
        if name == "venus" and texture > 1.05:
            score += 0.40
        scores[name] = score
    if not scores:
        return {k: "unknown" for k in zones}

    vals = list(scores.values())
    med = float(np.median(vals))
    # Absolute floors so a clearly full pad is never "flat" just because
    # another mount (e.g. heavily lined Venus) dominates the relative scale.
    out = {}
    for k, v in scores.items():
        if v >= med + 0.35 or v >= 0.55:
            out[k] = "prominent"
        elif v <= med - 0.45 and v < -0.15:
            out[k] = "flat"
        else:
            out[k] = "moderate"
    return out


def _count_proj_peaks(proj: np.ndarray, min_sep: int, frac: float = 0.35) -> int:
    """Count well-separated peaks in a 1-D projection profile."""
    if proj.size < 3 or float(proj.max()) <= 0:
        return 0
    thresh = max(float(proj.mean()) * 1.3, float(proj.max()) * frac)
    peaks: list[int] = []
    for i in range(1, len(proj) - 1):
        if proj[i] >= thresh and proj[i] >= proj[i - 1] and proj[i] >= proj[i + 1]:
            if not peaks or i - peaks[-1] >= min_sep:
                peaks.append(i)
    return len(peaks)


# Book-aligned reading of what the lines on each mount mean (Indian + Western
# consensus; e.g. a single deep vertical = the mount's gift is focused/strong,
# a grille = the energy is scattered/obstructed, a cross = a test or warning).
MOUNT_LINE_NOTE: dict[str, dict[str, str]] = {
    "jupiter": {
        "single": "a single strong line of ambition — leadership and honour realised",
        "multi": "several lines — restless ambition pulling in many directions",
        "grille": "a grille — pride or domineering tendencies that scatter the ambition",
        "cross": "a cross — a fortunate union or a decisive turning point",
    },
    "saturn": {
        "single": "a single line of good fortune in career and stability",
        "multi": "several lines — recurring obstacles and a serious, careworn nature",
        "grille": "a grille — misfortune or melancholy to guard against",
        "cross": "a cross — a warning of accident or setback; take care",
    },
    "apollo": {
        "single": "a single Sun line — talent and recognition crowned with success",
        "multi": "several lines — scattered artistic energy; focus brings fame",
        "grille": "a grille — vanity or a wish for fame that frustrates real success",
        "cross": "a cross — a disappointment in reputation or art",
    },
    "mercury": {
        "single": "a single line — sharp mind for business, science or healing",
        "multi": "several lines — quick, versatile, but restless in dealings",
        "grille": "a grille — cunning or nervous over-activity to channel well",
        "cross": "a cross — caution against dishonesty around you",
    },
    "venus": {
        "single": "a strong line — warm, loyal affections and vitality",
        "multi": "several influence lines — many attachments and strong passions",
        "grille": "a grille — passions that scatter; tendency to over-indulge",
        "cross": "a cross — an intense, fated attachment",
    },
    "moon": {
        "single": "a line of imagination and intuition guiding you",
        "multi": "several lines — vivid imagination, travel and restlessness",
        "grille": "a grille — anxiety or an over-active imagination to calm",
        "cross": "a cross — a significant journey or a vivid premonition",
    },
    "mars": {
        "single": "a line of steady courage and endurance",
        "multi": "several lines — combativeness and a quick temper",
        "grille": "a grille — irritability and conflict to master",
        "cross": "a cross — a quarrel or struggle that tests you",
    },
}


def _score_mount_lines(
    ridge_bin: np.ndarray, wpts: np.ndarray, size: int
) -> dict[str, dict[str, Any]]:
    """Detect and classify the fine lines sitting ON each mount.

    For every mount ROI we measure vertical-line count, horizontal-line count
    and overall crease density, then classify into the classic patterns the
    books describe: a single deep line, several lines, a grille (cross-hatch)
    or a cross. Returns a per-mount dict with a book-aligned meaning.
    """
    zones = _mount_zones(wpts, size)
    h, w = ridge_bin.shape[:2]
    min_sep = max(3, int(0.05 * size))

    # First pass: measure each mount so we can classify RELATIVE to this hand.
    # (A creased palm has some lines on every mount; we only want to call out a
    # mount whose marking clearly stands apart from the rest.)
    meas: dict[str, dict[str, Any]] = {}
    for name, (x0, y0, x1, y1) in zones.items():
        x0c, x1c = max(0, x0), min(w, x1)
        y0c, y1c = max(0, y0), min(h, y1)
        roi = ridge_bin[y0c:y1c, x0c:x1c]
        if roi.size < 64:
            meas[name] = {"density": 0.0, "v": 0, "h": 0}
            continue
        density = float(np.count_nonzero(roi)) / roi.size
        v = _count_proj_peaks(roi.sum(axis=0).astype(np.float64), min_sep)
        hl = _count_proj_peaks(roi.sum(axis=1).astype(np.float64), min_sep)
        meas[name] = {"density": density, "v": int(v), "h": int(hl)}

    dens = [m["density"] for m in meas.values() if m["density"] > 0]
    med = float(np.median(dens)) if dens else 0.0
    grille_cut = max(0.15, med * 1.5)

    out: dict[str, dict[str, Any]] = {}
    for name, m in meas.items():
        density, v_lines, h_lines = m["density"], m["v"], m["h"]
        pattern = "plain"
        if density >= grille_cut and v_lines >= 2 and h_lines >= 2:
            pattern = "grille"
        elif v_lines >= 3 and h_lines <= 1:
            pattern = "multi"
        elif v_lines == 1 and h_lines == 1 and density < med:
            pattern = "cross"
        elif v_lines in (1, 2) and h_lines <= 1 and density > 0:
            pattern = "single"

        entry: dict[str, Any] = {
            "detected": pattern not in ("plain",),
            "pattern": pattern,
            "vertical_lines": int(v_lines),
            "horizontal_lines": int(h_lines),
            "density": round(density, 4),
        }
        if entry["detected"]:
            note = (MOUNT_LINE_NOTE.get(name) or {}).get(pattern)
            if note:
                entry["meaning"] = f"On the {name.title()} mount: {note}."
        out[name] = entry
    return out


# ---------------------------------------------------------------------------
# Morphology
# ---------------------------------------------------------------------------


def _finger_palm_ratio(pts: np.ndarray) -> str:
    palm_w = float(np.linalg.norm(pts[5] - pts[17]))
    finger_len = float(
        np.linalg.norm(pts[9] - pts[12])
        + np.linalg.norm(pts[12] - pts[0])
    ) / 2.0
    if palm_w < 1:
        return "equal"
    r = finger_len / palm_w
    if r < 0.88:
        return "short"
    if r > 1.12:
        return "long"
    return "equal"


def _finger_chain_len(pts: np.ndarray, ids: tuple[int, ...]) -> float:
    total = 0.0
    for a, b in zip(ids[:-1], ids[1:]):
        total += float(np.linalg.norm(pts[b] - pts[a]))
    return total


def _head_life_relation(
    head_poly: list[tuple[float, float]],
    life_poly: list[tuple[float, float]],
    size: int,
) -> str | None:
    """Classify how the head line begins relative to the life line.

    Book basis (All the Secrets of Palmistry, Fig. 18-E/F): lines that
    *originate as one* and separate after a short travel = joined/merged
    (cautious / low childhood confidence). A true gap at the start =
    separated; a wide gap = independent / reckless.

    Template tracers often place the very first head sample a little off the
    life crease even when the next stretch rides with life — so we classify
    from the **early path**, not a single endpoint distance.
    """
    if not head_poly or not life_poly or size <= 0:
        return None

    def _d2(a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2

    def _min_dist(pt: tuple[float, float], poly: list[tuple[float, float]]) -> float:
        return min((_d2(pt, p) ** 0.5) for p in poly)

    # Orient head so index 0 is the radial origin (near life start / thumb-web).
    life_start = life_poly[0]
    head = list(head_poly)
    if _d2(head[-1], life_start) < _d2(head[0], life_start):
        head.reverse()

    # Life upper portion (origin side) — prefer matching against this.
    y0 = life_poly[0][1]
    upper_life = [p for p in life_poly if p[1] <= y0 + 0.28 * size] or life_poly

    early_n = max(8, min(len(head), max(len(head) // 5, 12)))
    early = head[:early_n]
    dists = [_min_dist(p, upper_life) / float(size) for p in early]
    d_min = float(min(dists))
    d_mean = float(sum(dists) / len(dists))
    # Share of early samples that still hug the life crease.
    close = sum(1 for d in dists if d < 0.055) / float(len(dists))
    # How soon they stay close: first half of early window.
    half = dists[: max(4, len(dists) // 2)]
    half_mean = float(sum(half) / len(half))

    # Joined / merged: early travel with life (book "rise as one then separate").
    if d_mean < 0.065 or half_mean < 0.055 or (d_min < 0.035 and close >= 0.30):
        return "merged"
    if d_mean < 0.105 or d_min < 0.07:
        return "separated"
    return "separated_wide"


def _analyze_thumb(pts: np.ndarray) -> dict[str, Any]:
    """Thumb length, will/logic phalange balance and opening angle.

    Landmarks: 1=CMC, 2=MCP, 3=IP, 4=tip; 0=wrist, 9=middle MCP.
    Book basis: 50 Case Studies in Modern Palmistry — long thumb = strong will;
    short = romantic; top (will) phalange bigger = acts first then thinks; lower
    (logic) phalange bigger = plans but may not act; thumb leaning away (open) =
    generous, tightly held = anxious.
    """
    cmc, mcp, ip, tip = pts[1], pts[2], pts[3], pts[4]
    # Thumb proper = its two phalanges (MCP->IP->tip); the CMC->MCP segment sits
    # in the palm. Compare against the index (Jupiter) finger: a long thumb
    # reaches well up the index, a short thumb falls short of it.
    thumb_len = float(np.linalg.norm(ip - mcp)) + float(np.linalg.norm(tip - ip))
    index_len = (
        float(np.linalg.norm(pts[6] - pts[5]))
        + float(np.linalg.norm(pts[7] - pts[6]))
        + float(np.linalg.norm(pts[8] - pts[7]))
    ) or 1.0
    ratio = thumb_len / index_len
    if ratio > 0.95:
        length = "long"
    elif ratio < 0.72:
        length = "short"
    else:
        length = "average"

    will = float(np.linalg.norm(tip - ip))       # top / nail phalange = will
    logic = float(np.linalg.norm(ip - mcp))       # second phalange = logic/reason
    wl = will / (logic or 1.0)
    if wl > 1.12:
        will_vs_logic = "will_dominant"
    elif wl < 0.88:
        will_vs_logic = "logic_dominant"
    else:
        will_vs_logic = "balanced"

    hand_axis = pts[9] - pts[0]
    thumb_vec = tip - cmc
    cosang = float(
        np.dot(hand_axis, thumb_vec)
        / ((np.linalg.norm(hand_axis) * np.linalg.norm(thumb_vec)) or 1.0)
    )
    angle = float(np.degrees(np.arccos(max(-1.0, min(1.0, cosang)))))
    if angle > 50:
        opening = "wide"
    elif angle < 30:
        opening = "narrow"
    else:
        opening = "moderate"

    return {
        "length": length,
        "will_vs_logic": will_vs_logic,
        "opening": opening,
        "length_ratio": round(ratio, 3),
        "angle_deg": round(angle, 1),
    }


def _index_vs_ring(fingers: dict[str, dict[str, Any]]) -> str:
    """Compare index (Jupiter) vs ring (Apollo) finger length.

    Book basis: All the Secrets of Palmistry — index longer than ring heightens
    Jupiter (ambition, ego, leadership); ring longer than index increases
    self-confidence, love of fame/success over money, zest for life.
    """
    idx = (fingers.get("index") or {}).get("ratio_to_middle")
    ring = (fingers.get("ring") or {}).get("ratio_to_middle")
    if idx is None or ring is None:
        return "unknown"
    if idx > ring * 1.03:
        return "index_longer"
    if ring > idx * 1.03:
        return "ring_longer"
    return "equal"


def _analyze_fingers(pts: np.ndarray) -> dict[str, dict[str, Any]]:
    """Per-finger length vs middle finger (palmistry finger length rules)."""
    chains = {
        "index": (5, 6, 7, 8),
        "middle": (9, 10, 11, 12),
        "ring": (13, 14, 15, 16),
        "pinky": (17, 18, 19, 20),
    }
    lengths = {name: _finger_chain_len(pts, ids) for name, ids in chains.items()}
    mid = lengths["middle"] or 1.0
    out: dict[str, dict[str, Any]] = {}
    for name, length in lengths.items():
        ratio = length / mid
        if name == "middle":
            length_class = "reference"
        elif ratio > 1.06:
            length_class = "long"
        elif ratio < 0.92:
            length_class = "short"
        else:
            length_class = "average"
        out[name] = {
            "length_class": length_class,
            "ratio_to_middle": round(ratio, 3),
            "setting": "low" if ratio < 0.88 and name in ("index", "ring") else "normal",
        }
    return out


def _finger_badge_positions(pts: np.ndarray) -> dict[str, tuple[int, int]]:
    """Circle on each finger base (MCP) for overlay numbering."""
    return {
        "index": (int(pts[5][0]), int(pts[5][1])),
        "middle": (int(pts[9][0]), int(pts[9][1])),
        "ring": (int(pts[13][0]), int(pts[13][1])),
        "pinky": (int(pts[17][0]), int(pts[17][1])),
    }


def _hand_type(pts: np.ndarray) -> str:
    palm_len = float(np.linalg.norm(pts[0] - pts[9]))
    palm_w = float(np.linalg.norm(pts[5] - pts[17]))
    finger_avg = float(
        np.linalg.norm(pts[5] - pts[8])
        + np.linalg.norm(pts[9] - pts[12])
        + np.linalg.norm(pts[13] - pts[16])
        + np.linalg.norm(pts[17] - pts[20])
    ) / 4.0
    long_palm = palm_len > palm_w * 1.05
    long_fingers = finger_avg > palm_w * 0.28
    if long_palm and long_fingers:
        return "water"
    if long_palm and not long_fingers:
        return "fire"
    if not long_palm and long_fingers:
        return "air"
    if not long_palm and not long_fingers:
        return "earth"
    return "mixed"


def _quality_grade(bgr: np.ndarray, mask: np.ndarray, landmarks_ok: bool) -> dict[str, Any]:
    h, w = bgr.shape[:2]
    coverage = float(np.count_nonzero(mask)) / (h * w)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    issues = []
    if not landmarks_ok:
        issues.append("hand_landmarks_missing")
    if coverage < 0.12:
        issues.append("palm_not_framed")
    if sharp < 80:
        issues.append("blurry")
    score = min(1.0, coverage * 2) * (1.0 if landmarks_ok else 0.5) * min(1.0, sharp / 200.0)
    if score >= 0.55 and landmarks_ok:
        grade = "good"
    elif score >= 0.35:
        grade = "fair"
    else:
        grade = "poor"
    return {"grade": grade, "score": round(score, 3), "issues": issues}


def _photo_guidance(
    quality: dict[str, Any],
    landmarks_ok: bool,
    line_data: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Decide whether to ask the user for a clearer / different-angle photo.

    Driven by image quality, hand detection and how well the major creases
    were actually picked up. Returns actionable, specific retake instructions.
    """
    reasons: list[str] = []
    tips: list[str] = []
    issues = set(quality.get("issues") or [])

    if not landmarks_ok:
        reasons.append("the hand could not be located in the photo")
        tips.append("Take the photo straight-on with the whole palm facing the "
                    "camera and all fingers spread.")

    if "blurry" in issues:
        reasons.append("the photo is blurry")
        tips.append("Hold the hand and camera steady and tap to focus on the palm.")
    if "palm_not_framed" in issues:
        reasons.append("the palm fills too little of the frame")
        tips.append("Move closer so the palm fills most of the frame.")

    # How many major creases came through clearly (low ridge coverage => the
    # crease was mostly inferred from the template, not actually seen).
    faint = [
        key for key in ("life", "head", "heart")
        if line_data.get(key, {}).get("detected")
        and float(line_data.get(key, {}).get("ridge_coverage", 0.0)) < 0.30
    ]
    missing = [
        key for key in ("life", "head", "heart")
        if not line_data.get(key, {}).get("detected")
    ]
    if missing:
        reasons.append(f"the {', '.join(missing)} line(s) were not visible")
    if len(faint) >= 2:
        reasons.append(f"the {', '.join(faint)} line(s) are faint/unclear")

    if missing or len(faint) >= 2:
        tips.append("Flatten the palm (don't cup it), spread the fingers, and use "
                    "soft, even light with no harsh shadow across the palm.")
        tips.append("If creases are still faint, send a second shot from a slightly "
                    "different angle / tilt so the lines catch the light.")

    needs = (
        not landmarks_ok
        or quality.get("grade") == "poor"
        or bool(missing)
        or len(faint) >= 2
    )
    return {
        "needs_better_photo": bool(needs),
        "reasons": reasons,
        "suggestions": list(dict.fromkeys(tips)),  # de-dup, keep order
    }


# ---------------------------------------------------------------------------
# Numbered findings overlay (user verification)
# ---------------------------------------------------------------------------


def _group_centroid(group: list[dict[str, Any]]) -> tuple[int, int]:
    if not group:
        return (0, 0)
    return int(np.mean([s["mx"] for s in group])), int(np.mean([s["my"] for s in group]))


def _mount_center(name: str, size: int) -> tuple[int, int]:
    zones = _mount_zones(np.zeros((21, 2)), size)
    x0, y0, x1, y1 = zones[name]
    return (x0 + x1) // 2, (y0 + y1) // 2


def _line_finding_text(name: str, props: dict[str, Any]) -> str:
    if not props.get("detected"):
        return "Not detected"
    hidden = {"detected", "points", "ridge_coverage", "segment_count",
              "length_ratio", "curvature"}
    parts = [
        f"{k.replace('_', ' ')}: {v}"
        for k, v in props.items()
        if k not in hidden
    ]
    return "; ".join(parts)


def _finger_finding_text(name: str, data: dict[str, Any]) -> str:
    lc = data.get("length_class", "?")
    ratio = data.get("ratio_to_middle", "?")
    setting = data.get("setting", "normal")
    parts = [f"length vs middle: {lc} (ratio {ratio})"]
    if setting == "low":
        parts.append("low setting at palm")
    return "; ".join(parts)


def build_numbered_checklist(
    lines: dict[str, Any],
    mounts: dict[str, str],
    line_groups: dict[str, list[dict[str, Any]]],
    morphology: dict[str, Any],
    size: int,
    *,
    fingers: dict[str, dict[str, Any]] | None = None,
    finger_positions: dict[str, tuple[int, int]] | None = None,
    line_anchors: dict[str, tuple[float, float]] | None = None,
    marks: list[dict[str, Any]] | None = None,
    thumb_pos: tuple[int, int] | None = None,
) -> list[dict[str, Any]]:
    """Numbered findings for lines, all major mounts, and finger-length points."""
    items: list[dict[str, Any]] = []
    n = 1
    fingers = fingers or {}
    finger_positions = finger_positions or {}
    marks = marks or []
    thumb = morphology.get("thumb") or {}

    for key, title in (
        ("life", "Your life line"),
        ("head", "Your head line"),
        ("heart", "Your heart line"),
        ("fate", "Your fate line"),
    ):
        props = lines.get(key) or {}
        if not props.get("detected"):
            continue
        group = line_groups.get(key) or []
        x, y = _line_marker_position(group, key, size, line_anchors)
        items.append(
            {
                "num": n,
                "kind": "line",
                "key": key,
                "title": title,
                "x": x,
                "y": y,
                "finding": _line_finding_text(key, props),
            }
        )
        n += 1

    for mount in MOUNT_CHECKLIST_ORDER:
        level = mounts.get(mount)
        if not level or level == "unknown":
            continue
        x, y = _mount_center(mount, size)
        items.append(
            {
                "num": n,
                "kind": "mount",
                "key": mount,
                "title": MOUNT_TITLES.get(mount, mount.title()),
                "x": x,
                "y": y,
                "finding": f"{level.title()} (developed)" if level == "prominent" else level.title(),
            }
        )
        n += 1

    for fname in ("index", "middle", "ring", "pinky"):
        fdata = fingers.get(fname)
        if not fdata:
            continue
        pos = finger_positions.get(fname)
        items.append(
            {
                "num": n,
                "kind": "finger",
                "key": fname,
                "title": FINGER_TITLES.get(fname, fname.title()),
                "x": pos[0] if pos else None,
                "y": pos[1] if pos else None,
                "finding": _finger_finding_text(fname, fdata),
            }
        )
        n += 1

    if thumb and thumb.get("length"):
        items.append(
            {
                "num": n,
                "kind": "thumb",
                "key": "thumb",
                "title": "Your thumb (will & logic)",
                "x": thumb_pos[0] if thumb_pos else None,
                "y": thumb_pos[1] if thumb_pos else None,
                "finding": (
                    f"{thumb.get('length','average')} thumb; "
                    f"{thumb.get('will_vs_logic','balanced').replace('_',' ')}; "
                    f"{thumb.get('opening','moderate')} angle"
                ),
            }
        )
        n += 1

    for mk in marks:
        items.append(
            {
                "num": n,
                "kind": "mark",
                "key": mk.get("type"),
                "title": mk.get("title", "Special mark"),
                "x": mk.get("x"),
                "y": mk.get("y"),
                "finding": f"{mk.get('title')} in the {str(mk.get('zone', 'palm')).title()} area",
                "mark_type": mk.get("type"),
                "zone": mk.get("zone"),
                "confidence": mk.get("confidence"),
                "meaning": mk.get("meaning"),
                "keywords": mk.get("keywords"),
            }
        )
        n += 1

    hand_t = morphology.get("hand_type")
    ratio = morphology.get("finger_palm_ratio")
    if hand_t and hand_t != "unknown":
        items.append(
            {
                "num": n,
                "kind": "morphology",
                "key": "hand_shape",
                "title": "Your overall hand shape",
                "x": None,
                "y": None,
                "finding": f"{str(hand_t).title()} hand; finger-to-palm ratio: {ratio}",
            }
        )

    return items


def _text_metrics(num: int) -> tuple[int, int, float]:
    label = str(num)
    scale = 0.5 if num < 10 else 0.45
    thickness = 1
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    return tw, th, scale


def _label_bbox(lx: int, ly: int, tw: int, th: int, pad: int = 5) -> tuple[int, int, int, int]:
    return lx - tw // 2 - pad, ly - th - pad, lx + tw // 2 + pad, ly + pad


def _boxes_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _palm_center(points: list[tuple[int, int]]) -> tuple[int, int]:
    if not points:
        return 200, 200
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return int(np.mean(xs)), int(np.mean(ys))


def _layout_external_labels(
    items: list[tuple[int, int, int]],
    w: int,
    h: int,
) -> list[tuple[int, int, int, int, int, float, int, int]]:
    """
    items: (x, y, num) palm points.
    Returns: (x, y, lx, ly, num, scale, tw, th) with label center outside the palm.
    """
    if not items:
        return []
    cx, cy = _palm_center([(x, y) for x, y, _ in items])
    base_r = min(w, h) * 0.44
    placed: list[tuple[int, int, int, int, int, float, int, int]] = []
    used_boxes: list[tuple[int, int, int, int]] = []

    for x, y, num in sorted(items, key=lambda p: math.atan2(p[1] - cy, p[0] - cx)):
        angle = math.atan2(y - cy, x - cx)
        tw, th, scale = _text_metrics(num)
        found = False
        for ring in range(5):
            for step in range(12):
                r = base_r + ring * 16
                a = angle + (step - 6) * 0.07
                lx = int(cx + r * math.cos(a))
                ly = int(cy + r * math.sin(a))
                lx = max(tw // 2 + 8, min(w - tw // 2 - 8, lx))
                ly = max(th + 8, min(h - 8, ly))
                box = _label_bbox(lx, ly, tw, th)
                if not any(_boxes_overlap(box, b) for b in used_boxes):
                    used_boxes.append(box)
                    placed.append((x, y, lx, ly, num, scale, tw, th))
                    found = True
                    break
            if found:
                break
        if not found:
            lx = max(tw // 2 + 8, min(w - tw // 2 - 8, int(x + (x - cx) * 0.35)))
            ly = max(th + 8, min(h - 8, int(y + (y - cy) * 0.35)))
            placed.append((x, y, lx, ly, num, scale, tw, th))

    return placed


def _leader_end_on_label(
    x: int, y: int, lx: int, ly: int, tw: int, th: int
) -> tuple[int, int]:
    """Point on label box edge closest to palm dot."""
    x0, y0, x1, y1 = _label_bbox(lx, ly, tw, th, pad=0)
    cx = max(x0, min(x1, x))
    cy = max(y0, min(y1, y))
    return cx, cy


def _draw_palm_dot(img: np.ndarray, x: int, y: int) -> None:
    x, y = int(x), int(y)
    cv2.circle(img, (x, y), 5, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(img, (x, y), 3, (13, 71, 161), -1, cv2.LINE_AA)


def _draw_external_label(
    img: np.ndarray, lx: int, ly: int, num: int, scale: float, tw: int, th: int
) -> None:
    x0, y0, x1, y1 = _label_bbox(lx, ly, tw, th, pad=4)
    cv2.rectangle(img, (x0, y0), (x1, y1), (255, 255, 255), -1, cv2.LINE_AA)
    cv2.rectangle(img, (x0, y0), (x1, y1), (13, 71, 161), 1, cv2.LINE_AA)
    label = str(num)
    cv2.putText(
        img,
        label,
        (lx - tw // 2, ly),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        (13, 71, 161),
        1,
        cv2.LINE_AA,
    )


def draw_overlay(warped: np.ndarray, checklist: list[dict[str, Any]]) -> np.ndarray:
    """Dot on palm + thin leader line to numbered label outside the hand."""
    out = warped.copy()
    h, w = out.shape[:2]

    on_palm = [
        (int(item["x"]), int(item["y"]), int(item["num"]))
        for item in checklist
        if item.get("x") is not None and item.get("y") is not None
    ]
    layout = _layout_external_labels(on_palm, w, h)

    for x, y, lx, ly, num, scale, tw, th in layout:
        ex, ey = _leader_end_on_label(x, y, lx, ly, tw, th)
        cv2.line(out, (x, y), (ex, ey), (13, 71, 161), 1, cv2.LINE_AA)

    for x, y, lx, ly, num, scale, tw, th in layout:
        _draw_palm_dot(out, x, y)

    for x, y, lx, ly, num, scale, tw, th in layout:
        _draw_external_label(out, lx, ly, num, scale, tw, th)

    if checklist:
        cv2.putText(
            out,
            "Dot on palm = point; number outside = same point in report",
            (8, h - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            (40, 40, 40),
            1,
            cv2.LINE_AA,
        )
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_features(
    image_path: Path,
    *,
    hand: str = "unknown",
) -> dict[str, Any]:
    bgr = cv2.imread(str(image_path))
    if bgr is None:
        raise ValueError(f"Cannot read image: {image_path}")

    pts, lm_status = detect_hand_landmarks(bgr)
    landmarks_ok = pts is not None

    if pts is not None:
        mask = _palm_mask_from_landmarks(bgr, pts)
        warped, wpts, warp_meta = _prepare_warped_palm(bgr, pts)
    else:
        warp_meta = {}
        mask = _skin_fallback_mask(bgr)
        warped = cv2.resize(bgr, (400, 400))
        wpts = np.zeros((21, 2), dtype=np.float32)
        lm_status = "fallback_skin_mask"

    h, w = warped.shape[:2]
    size = min(h, w)
    palm_mask = _palm_mask_from_landmarks(warped, wpts) if landmarks_ok else _skin_fallback_mask(warped)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    ridge = _enhance_ridges(gray, palm_mask)

    M = warp_meta.get("M")
    flip = bool(warp_meta.get("canonical_flip", False))
    orig_w = int(bgr.shape[1])

    # Landmark-anchored curved-line tracing (canonical frame).
    line_data: dict[str, dict[str, Any]] = {}
    canonical_polys: dict[str, list[tuple[float, float]]] = {}
    overlay_lines: dict[str, list[tuple[int, int]]] = {}
    minor_out: dict[str, dict[str, Any]] = {}
    overlay_minor: dict[str, list[tuple[int, int]]] = {}

    if landmarks_ok:
        lm_norm = wpts.astype(np.float64) / float(size)
        major = detect_major_lines(ridge, lm_norm, size)
        minor = detect_minor_lines(ridge, lm_norm, size)

        for key in ("life", "head", "heart", "fate"):
            entry = major.get(key) or {}
            props = dict(entry.get("props") or {"detected": False})
            if props.get("detected") and entry.get("points"):
                poly_c = entry["points"]
                canonical_polys[key] = poly_c
                poly_o = _inverse_affine_points(poly_c, M, flip, orig_w)
                overlay_lines[key] = [(int(x), int(y)) for x, y in poly_o]
                props["points"] = overlay_lines[key]
            line_data[key] = props

        # Head + Life start relationship (classic personality rule).
        # Book basis: All the Secrets of Palmistry, p.109 (Fig. 18-E/F) —
        # head & life rising as one then separating = low childhood confidence;
        # head set apart from life = independent / "has his way"; very wide =
        # careless/reckless. Succinct Palmistry, p.54 — not connected = caretaker,
        # independent thinker.
        if line_data.get("head", {}).get("detected") and "life" in canonical_polys:
            rel = _head_life_relation(canonical_polys["head"], canonical_polys["life"], size)
            if rel:
                line_data["head"]["start_relation"] = rel

        for key, entry in minor.items():
            e = dict(entry)
            if entry.get("detected") and entry.get("points"):
                poly_o = _inverse_affine_points(entry["points"], M, flip, orig_w)
                overlay_minor[key] = [(int(x), int(y)) for x, y in poly_o]
                e["points"] = overlay_minor[key]
            else:
                e.pop("points", None)
            minor_out[key] = e
    else:
        for key in ("life", "head", "heart", "fate"):
            line_data[key] = {"detected": False}

    # Synthesize pseudo-segment groups (canonical) so timing.py keeps working.
    line_groups: dict[str, list[dict[str, Any]]] = {}
    for key, poly in canonical_polys.items():
        line_groups[key] = [
            {"mx": float(x), "my": float(y), "length": 30.0, "angle": 0.0}
            for x, y in poly
        ]

    mounts = _score_mounts(gray, palm_mask, wpts, size) if landmarks_ok else {
        k: "unknown"
        for k in ("jupiter", "saturn", "apollo", "mercury", "mars", "venus", "moon")
    }
    mount_lines = _score_mount_lines(ridge, wpts, size) if landmarks_ok else {}

    quality = _quality_grade(warped, palm_mask, landmarks_ok)
    photo_guidance = _photo_guidance(quality, landmarks_ok, line_data)

    finger_analysis = _analyze_fingers(wpts) if landmarks_ok else {}
    finger_positions = _finger_badge_positions(wpts) if landmarks_ok else {}

    special_marks = detect_special_marks(ridge, wpts, size) if landmarks_ok else []

    morphology = {
        "finger_palm_ratio": _finger_palm_ratio(wpts) if landmarks_ok else "unknown",
        "hand_type": _hand_type(wpts) if landmarks_ok else "unknown",
        "index_vs_ring": _index_vs_ring(finger_analysis) if landmarks_ok else "unknown",
        "thumb": _analyze_thumb(wpts) if landmarks_ok else {},
        "fingers": finger_analysis,
    }

    numbered_checklist = build_numbered_checklist(
        {k: line_data[k] for k in ("life", "head", "heart", "fate")},
        mounts,
        line_groups,
        morphology,
        size,
        fingers=finger_analysis,
        finger_positions=finger_positions,
        line_anchors=None,
        marks=special_marks,
        thumb_pos=(int(wpts[2][0]), int(wpts[2][1])) if landmarks_ok else None,
    )
    # Attach original-image coordinates (ox, oy) for drawing on the source photo.
    for it in numbered_checklist:
        if it.get("x") is not None and it.get("y") is not None:
            ox, oy = _inverse_affine_points(
                [(it["x"], it["y"])], M, flip, orig_w
            )[0]
            it["ox"], it["oy"] = int(ox), int(oy)

    overlay_payload = {
        "lines": overlay_lines,
        "minor": overlay_minor,
        "checklist": [
            {
                "ox": it.get("ox"),
                "oy": it.get("oy"),
                "num": it.get("num"),
                "kind": it.get("kind"),
                "key": it.get("key"),
            }
            for it in numbered_checklist
        ],
    }

    return {
        "source_image": str(image_path.resolve()),
        "hand": hand,
        "landmark_status": lm_status,
        "quality": quality,
        "photo_guidance": photo_guidance,
        "morphology": morphology,
        "fingers": finger_analysis,
        "mounts": mounts,
        "mount_lines": mount_lines,
        "lines": {k: line_data[k] for k in ("life", "head", "heart", "fate")},
        "minor_lines": minor_out,
        "special_marks": [
            {
                "type": it.get("mark_type"),
                "title": it.get("title"),
                "zone": it.get("zone"),
                "confidence": it.get("confidence"),
                "meaning": it.get("meaning"),
                "num": it.get("num"),
                "ox": it.get("ox"),
                "oy": it.get("oy"),
            }
            for it in numbered_checklist
            if it.get("kind") == "mark"
        ],
        "numbered_checklist": numbered_checklist,
        "not_detected": [
            f"{title} line"
            for key, title in (
                ("life", "Life"),
                ("head", "Head"),
                ("heart", "Heart"),
                ("fate", "Fate"),
            )
            if not line_data[key].get("detected")
        ],
        "debug": {
            "canonical_flip": flip,
            "minor_density": {k: v.get("density") for k, v in minor_out.items()},
        },
        "_line_groups": line_groups,
        "_overlay": overlay_payload,
        "_warped_shape": [int(warped.shape[0]), int(warped.shape[1])],
    }


# BGR colors for the original-photo overlay.
MAJOR_LINE_COLORS: dict[str, tuple[int, int, int]] = {
    "heart": (40, 40, 220),
    "head": (50, 165, 45),
    "life": (20, 180, 225),
    "fate": (220, 95, 30),
}
MAJOR_LINE_NAMES: dict[str, str] = {
    "heart": "Heart line",
    "head": "Head line",
    "life": "Life line",
    "fate": "Fate line",
}
MINOR_LINE_COLORS: dict[str, tuple[int, int, int]] = {
    "sun": (0, 140, 255),
    "mercury": (180, 175, 0),
    "marriage": (190, 40, 190),
    "girdle_of_venus": (150, 70, 165),
    "ring_of_solomon": (140, 140, 0),
    "children": (110, 60, 200),
    "travel": (90, 160, 200),
}
MINOR_LINE_NAMES: dict[str, str] = {
    "sun": "Sun (Apollo) line",
    "mercury": "Mercury / Health line",
    "marriage": "Marriage line(s)",
    "girdle_of_venus": "Girdle of Venus",
    "ring_of_solomon": "Ring of Solomon",
    "children": "Children line(s)",
    "travel": "Travel / restlessness line(s)",
}


def _draw_curve(img: np.ndarray, pts, color, thickness) -> None:
    if not pts or len(pts) < 2:
        return
    arr = np.asarray(pts, dtype=np.int32).reshape(-1, 1, 2)
    cv2.polylines(img, [arr], False, color, thickness, cv2.LINE_AA)


def draw_overlay_original(bgr: np.ndarray, overlay: dict[str, Any]) -> np.ndarray:
    """Draw curved colored major + minor lines, mount labels, and a legend
    directly on the original full-resolution photo."""
    out = bgr.copy()
    h, w = out.shape[:2]
    t_major = max(3, w // 320)
    t_minor = max(2, w // 520)
    dot_r = max(5, w // 240)

    lines = overlay.get("lines") or {}
    minor = overlay.get("minor") or {}

    for key, pts in minor.items():
        _draw_curve(out, pts, MINOR_LINE_COLORS.get(key, (160, 160, 160)), t_minor)

    for key in ("life", "head", "heart", "fate"):
        pts = lines.get(key)
        if not pts:
            continue
        color = MAJOR_LINE_COLORS[key]
        _draw_curve(out, pts, color, t_major)
        for end in (pts[0], pts[-1]):
            cv2.circle(out, (int(end[0]), int(end[1])), dot_r, color, -1, cv2.LINE_AA)
            cv2.circle(out, (int(end[0]), int(end[1])), dot_r, (255, 255, 255),
                       max(1, dot_r // 4), cv2.LINE_AA)

    # Numbered markers for every located point: lines, mounts, fingers, marks.
    num_scale = max(0.5, w / 2600.0)
    num_th = max(1, w // 1100)
    for it in overlay.get("checklist") or []:
        kind = it.get("kind")
        ox, oy = it.get("ox"), it.get("oy")
        if ox is None or oy is None:
            continue
        ox, oy = int(ox), int(oy)
        if kind == "mark":
            # Special marks (cross/star/fish/…) drawn as a magenta diamond.
            mc = (200, 40, 200)
            r = max(5, dot_r)
            pts = np.array([[ox, oy - r], [ox + r, oy], [ox, oy + r], [ox - r, oy]], np.int32)
            cv2.fillPoly(out, [pts], (255, 255, 255), cv2.LINE_AA)
            cv2.polylines(out, [pts], True, mc, max(2, dot_r // 3), cv2.LINE_AA)
            cv2.putText(out, str(it.get("num")), (ox + r + 2, oy),
                        cv2.FONT_HERSHEY_SIMPLEX, num_scale, mc, num_th, cv2.LINE_AA)
            continue
        if kind in ("finger", "thumb"):
            fill = (210, 235, 255)
            edge = (60, 120, 30)
        else:  # line / mount
            fill = (245, 245, 245)
            edge = (90, 90, 90)
        cv2.circle(out, (ox, oy), max(4, dot_r // 2), fill, -1, cv2.LINE_AA)
        cv2.circle(out, (ox, oy), max(4, dot_r // 2), edge, max(1, dot_r // 5), cv2.LINE_AA)
        cv2.putText(out, str(it.get("num")), (ox + dot_r, oy),
                    cv2.FONT_HERSHEY_SIMPLEX, num_scale, (40, 40, 40), num_th, cv2.LINE_AA)

    _draw_legend(out, lines, minor)
    return out


def _draw_legend(
    out: np.ndarray,
    lines: dict[str, Any],
    minor: dict[str, Any],
) -> None:
    h, w = out.shape[:2]
    entries: list[tuple[tuple[int, int, int], str]] = []
    for key in ("heart", "head", "life", "fate"):
        if lines.get(key):
            entries.append((MAJOR_LINE_COLORS[key], MAJOR_LINE_NAMES[key]))
    for key, pts in minor.items():
        if pts:
            entries.append((MINOR_LINE_COLORS.get(key, (160, 160, 160)),
                            MINOR_LINE_NAMES.get(key, key)))
    if not entries:
        return

    scale = max(0.55, w / 2300.0)
    th = max(1, w // 1000)
    row = int(46 * scale) + 14
    sw = int(row * 0.55)
    pad = int(row * 0.5)
    box_w = int(w * 0.40)
    box_h = pad * 2 + row * len(entries)
    x0, y0 = pad, pad
    overlay_box = out.copy()
    cv2.rectangle(overlay_box, (x0, y0), (x0 + box_w, y0 + box_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay_box, 0.55, out, 0.45, 0, out)

    y = y0 + pad
    for color, name in entries:
        cv2.rectangle(out, (x0 + pad // 2, y + row // 4),
                      (x0 + pad // 2 + sw, y + row // 4 + sw // 2), color, -1, cv2.LINE_AA)
        cv2.putText(out, name, (x0 + pad // 2 + sw + pad // 2, y + row // 2 + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), th, cv2.LINE_AA)
        y += row


def save_overlay(
    image_path: Path,
    features: dict[str, Any],
    out_path: Path,
) -> None:
    """Render curved colored palm-line overlay on the original photo."""
    bgr = cv2.imread(str(image_path))
    if bgr is None:
        raise ValueError(f"Cannot read image: {image_path}")
    overlay = features.get("_overlay") or {}
    ov = draw_overlay_original(bgr, overlay)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), ov, [int(cv2.IMWRITE_JPEG_QUALITY), 92])


def features_for_json(features: dict[str, Any]) -> dict[str, Any]:
    """Strip internal keys before saving."""
    return {k: v for k, v in features.items() if not k.startswith("_")}


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract palm features (no LLM)")
    ap.add_argument("image")
    ap.add_argument("-o", "--output", default="palm_features.json")
    ap.add_argument("--hand", choices=("left", "right", "unknown"), default="unknown")
    ap.add_argument("--overlay", help="Save debug overlay JPG")
    args = ap.parse_args()
    path = Path(args.image)
    feats = extract_features(path, hand=args.hand)
    if args.overlay:
        save_overlay(path, feats, Path(args.overlay))
    out = features_for_json(feats)
    Path(args.output).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {args.output} (quality={out['quality']['grade']})")
    if args.overlay:
        print(f"Overlay -> {args.overlay}")


if __name__ == "__main__":
    main()
