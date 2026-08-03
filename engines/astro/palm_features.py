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
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# MediaPipe (optional but recommended)
# ---------------------------------------------------------------------------


def _get_mediapipe_hands():
    try:
        import mediapipe as mp

        return mp.solutions.hands
    except ImportError:
        return None


def _landmarks_to_array(landmarks, w: int, h: int) -> np.ndarray:
    pts = np.zeros((21, 2), dtype=np.float32)
    for i, lm in enumerate(landmarks.landmark):
        pts[i, 0] = lm.x * w
        pts[i, 1] = lm.y * h
    return pts


def detect_hand_landmarks(bgr: np.ndarray) -> tuple[np.ndarray | None, str]:
    """Returns (21,2) pixel coords or None."""
    hands_module = _get_mediapipe_hands()
    if hands_module is None:
        return None, "mediapipe_not_installed"
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = bgr.shape[:2]
    with hands_module.Hands(
        static_image_mode=True,
        max_num_hands=1,
        model_complexity=1,
        min_detection_confidence=0.5,
    ) as hands:
        res = hands.process(rgb)
    if not res.multi_hand_landmarks:
        return None, "no_hand_detected"
    # Use largest hand if multiple
    best = res.multi_hand_landmarks[0]
    if len(res.multi_hand_landmarks) > 1:
        areas = []
        for hl in res.multi_hand_landmarks:
            pts = _landmarks_to_array(hl, w, h)
            areas.append(cv2.contourArea(cv2.convexHull(pts.astype(np.int32))))
        idx = int(np.argmax(areas))
        best = res.multi_hand_landmarks[idx]
    return _landmarks_to_array(best, w, h), "ok"


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
    return warped, wpts, {"size": size}


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


def _extract_segments(ridge_bin: np.ndarray, min_len: int = 25) -> list[dict[str, Any]]:
    edges = cv2.Canny(ridge_bin, 50, 150)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=35,
        minLineLength=min_len,
        maxLineGap=12,
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


def _classify_segments(segs: list[dict[str, Any]], size: int) -> dict[str, Any]:
    """Map segments to line types using normalized palm zones (heuristic)."""
    life, head, heart, fate = [], [], [], []
    for s in segs:
        mx, my = s["mx"] / size, s["my"] / size
        ang = abs(s["angle"])
        length = s["length"]
        # Heart: upper palm, roughly horizontal
        if my < 0.38 and ang < 35 or ang > 145:
            if length > 30:
                heart.append(s)
        # Head: middle band, horizontal
        if 0.32 < my < 0.58 and (ang < 30 or ang > 150):
            if length > 35:
                head.append(s)
        # Life: left side, curved / diagonal
        if mx < 0.45 and 0.25 < my < 0.85 and 25 < ang < 75:
            if length > 40:
                life.append(s)
        # Fate: center vertical
        if 0.38 < mx < 0.62 and 0.35 < my < 0.9 and 65 < ang < 115:
            if length > 30:
                fate.append(s)

    def _line_props(group: list[dict], kind: str) -> dict[str, Any]:
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
            if avg_x < 0.35:
                out["start_zone"] = "jupiter"
            elif avg_x < 0.48:
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
        "life": _line_props(life, "life"),
        "head": _line_props(head, "head"),
        "heart": _line_props(heart, "heart"),
        "fate": _line_props(fate, "fate"),
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


def _mount_zones(wpts: np.ndarray, size: int) -> dict[str, tuple[int, int, int, int]]:
    """Axis-aligned ROIs (x0,y0,x1,y1) in normalized palm space."""
    return {
        "jupiter": (int(size * 0.55), int(size * 0.30), int(size * 0.78), int(size * 0.48)),
        "saturn": (int(size * 0.42), int(size * 0.28), int(size * 0.58), int(size * 0.46)),
        "apollo": (int(size * 0.28), int(size * 0.26), int(size * 0.44), int(size * 0.44)),
        "mercury": (int(size * 0.08), int(size * 0.30), int(size * 0.28), int(size * 0.50)),
        "venus": (int(size * 0.62), int(size * 0.48), int(size * 0.92), int(size * 0.88)),
        "moon": (int(size * 0.02), int(size * 0.48), int(size * 0.35), int(size * 0.88)),
    }


def _score_mounts(gray: np.ndarray, mask: np.ndarray, wpts: np.ndarray, size: int) -> dict[str, str]:
    zones = _mount_zones(wpts, size)
    scores: dict[str, float] = {}
    for name, (x0, y0, x1, y1) in zones.items():
        roi = gray[y0:y1, x0:x1]
        mroi = mask[y0:y1, x0:x1]
        if roi.size < 50:
            scores[name] = 0.0
            continue
        vals = roi[mroi > 0] if np.any(mroi > 0) else roi.reshape(-1)
        # Higher local std ≈ more raised / lined mount (very rough)
        scores[name] = float(np.std(vals))
    if not scores:
        return {k: "unknown" for k in zones}

    vals = list(scores.values())
    med = float(np.median(vals))
    out = {}
    for k, v in scores.items():
        if v < med * 0.85:
            out[k] = "flat"
        elif v > med * 1.15:
            out[k] = "prominent"
        else:
            out[k] = "moderate"
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


# ---------------------------------------------------------------------------
# Overlay for human verification
# ---------------------------------------------------------------------------


def draw_overlay(
    warped: np.ndarray,
    segs: list[dict[str, Any]],
    lines: dict[str, Any],
    wpts: np.ndarray,
) -> np.ndarray:
    out = warped.copy()
    size = warped.shape[0]
    colors = {
        "life": (0, 200, 0),
        "head": (255, 180, 0),
        "heart": (0, 120, 255),
        "fate": (200, 0, 200),
    }
    for s in segs:
        cv2.line(out, (s["x1"], s["y1"]), (s["x2"], s["y2"]), (180, 180, 180), 1)
    for name, col in colors.items():
        if lines.get(name, {}).get("detected"):
            cv2.putText(
                out,
                name.upper(),
                (10, 25 + list(colors).index(name) * 22),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                col,
                2,
            )
    for i, pt in enumerate(wpts.astype(int)):
        cv2.circle(out, tuple(pt), 3, (0, 0, 255), -1)
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
        warped, wpts, _ = _normalize_palm(bgr, pts)
    else:
        mask = _skin_fallback_mask(bgr)
        warped = cv2.resize(bgr, (400, 400))
        wpts = np.zeros((21, 2), dtype=np.float32)
        lm_status = "fallback_skin_mask"

    h, w = warped.shape[:2]
    size = min(h, w)
    palm_mask = _palm_mask_from_landmarks(warped, wpts) if landmarks_ok else _skin_fallback_mask(warped)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    ridge = _enhance_ridges(gray, palm_mask)
    segs = _extract_segments(ridge)
    line_data = _classify_segments(segs, size)
    raw_counts = line_data.pop("_raw_counts", {})

    mounts = _score_mounts(gray, palm_mask, wpts, size) if landmarks_ok else {
        k: "unknown" for k in ("jupiter", "saturn", "apollo", "mercury", "venus", "moon")
    }

    quality = _quality_grade(warped, palm_mask, landmarks_ok)

    morphology = {
        "finger_palm_ratio": _finger_palm_ratio(wpts) if landmarks_ok else "unknown",
        "hand_type": _hand_type(wpts) if landmarks_ok else "unknown",
    }

    return {
        "source_image": str(image_path.resolve()),
        "hand": hand,
        "landmark_status": lm_status,
        "quality": quality,
        "morphology": morphology,
        "mounts": mounts,
        "lines": {
            "life": line_data["life"],
            "head": line_data["head"],
            "heart": line_data["heart"],
            "fate": line_data["fate"],
        },
        "debug": {
            "segment_counts": raw_counts,
            "total_segments": len(segs),
        },
        "_overlay_segments": segs,
        "_warped_shape": [int(warped.shape[0]), int(warped.shape[1])],
    }


def save_overlay(
    image_path: Path,
    features: dict[str, Any],
    out_path: Path,
) -> None:
    bgr = cv2.imread(str(image_path))
    pts, _ = detect_hand_landmarks(bgr)
    if pts is None:
        warped = cv2.resize(bgr, (400, 400))
        wpts = np.zeros((21, 2), np.float32)
    else:
        warped, wpts, _ = _normalize_palm(bgr, pts)
    segs = features.get("_overlay_segments", [])
    lines = features.get("lines", {})
    ov = draw_overlay(warped, segs, lines, wpts)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), ov)


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
