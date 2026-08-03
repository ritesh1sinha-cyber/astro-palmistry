#!/usr/bin/env python3
"""
Calibrate / evaluate palm-line templates against labelme ground-truth markings.

Run from /home/oppo/Desktop/test8:
    python3 -m palm_api.tools.eval_lines
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

from palm_api import analyzer
from palm_api.palm_lines import detect_major_lines, _resample

SIZE = 400
IMAGE = Path("palm_api/data/uploads/01cec126c3c2.jpg")
MARKERS = Path("palm_api/data/markers/01cec126c3c2_correct.json")

# labelme label -> our key (use the curved life linestrip, the vertical fate line)
LABEL_KEY = {
    "heart_line": "heart",
    "head_line": "head",
    "life_line": "life",
    "fate_line": "fate",
}


def _warp_with_M(bgr, pts):
    flip = analyzer._thumb_on_image_left(pts)
    if flip:
        work_bgr, work_pts = analyzer._mirror_image_and_landmarks(bgr, pts)
    else:
        work_bgr, work_pts = bgr, pts
    wrist, mid_mcp, index_mcp = work_pts[0], work_pts[9], work_pts[5]
    src = np.float32([wrist, mid_mcp, index_mcp])
    dst = np.float32([
        [SIZE * 0.5, SIZE * 0.92],
        [SIZE * 0.5, SIZE * 0.35],
        [SIZE * 0.72, SIZE * 0.38],
    ])
    M = cv2.getAffineTransform(src, dst)
    warped = cv2.warpAffine(work_bgr, M, (SIZE, SIZE))
    ones = np.ones((21, 1), dtype=np.float32)
    pts_h = np.hstack([work_pts, ones])
    M3 = np.vstack([M, [0, 0, 1]])
    wpts = (M3 @ pts_h.T).T[:, :2]
    return warped, wpts, M, flip, bgr.shape


def _fwd_point(x, y, M, flip, shape):
    h, w = shape[:2]
    if flip:
        x = (w - 1) - x
    v = M @ np.array([x, y, 1.0])
    return float(v[0]), float(v[1])


def _load_gt(M, flip, shape):
    data = json.loads(MARKERS.read_text())
    gt: dict[str, list] = {}
    for shp in data["shapes"]:
        key = LABEL_KEY.get(shp["label"])
        if not key:
            continue
        pts = [_fwd_point(px, py, M, flip, shape) for px, py in shp["points"]]
        # keep the longest shape per key (the real curve)
        if key not in gt or len(pts) > len(gt[key]):
            gt[key] = pts
    return gt


def _mean_dist(a, b):
    ar = np.asarray(_resample(a, 40))
    br = np.asarray(_resample(b, 40))
    # align direction: try both orderings
    d1 = np.mean(np.linalg.norm(ar - br, axis=1))
    d2 = np.mean(np.linalg.norm(ar - br[::-1], axis=1))
    return float(min(d1, d2))


def main():
    bgr = cv2.imread(str(IMAGE))
    pts, status = analyzer.detect_hand_landmarks(bgr)
    if pts is None:
        print("No landmarks:", status)
        return 1
    warped, wpts, M, flip, shape = _warp_with_M(bgr, pts)
    mask = analyzer._palm_mask_from_landmarks(warped, wpts)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    ridge = analyzer._enhance_ridges(gray, mask)

    lm_norm = wpts.astype(np.float64) / float(SIZE)
    gt = _load_gt(M, flip, shape)

    names = {0: "wrist", 1: "thumb_cmc", 2: "thumb_mcp", 5: "index",
             9: "middle", 13: "ring", 17: "pinky"}
    print("=== Canonical landmark normalized positions ===")
    for i, nm in names.items():
        print(f"  {nm:10s}: ({lm_norm[i][0]:.3f}, {lm_norm[i][1]:.3f})")

    print("=== Ground-truth canonical normalized endpoints ===")
    for key, poly in gt.items():
        norm = [(round(x / SIZE, 3), round(y / SIZE, 3)) for x, y in poly]
        print(f"  {key:6s}: {norm}")

    detected = detect_major_lines(ridge, lm_norm, SIZE)
    print("=== Detected vs GT (canonical px mean distance) ===")
    total = 0.0
    for key in ("life", "head", "heart", "fate"):
        if key not in gt:
            continue
        dpoly = detected[key]["points"]
        d = _mean_dist(dpoly, gt[key])
        total += d
        dn = [(round(x / SIZE, 3), round(y / SIZE, 3)) for x, y in _resample(dpoly, 4)]
        print(f"  {key:6s}: dist={d:6.1f}px  props={detected[key]['props'].get('depth')},"
              f" cover={detected[key]['props'].get('ridge_coverage')}  pts={dn}")
    print(f"  TOTAL mean dist = {total:.1f}px (size={SIZE})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
