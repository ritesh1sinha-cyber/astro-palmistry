"""
Classical, landmark-anchored curved palm-line tracing (no deep learning).

Works in the canonical warped frame produced by analyzer._prepare_warped_palm
(wrist at bottom ~y=0.92, fingers at top, thumb/Venus mount on the RIGHT).

Strategy per major line:
  1. Build a curved template from MediaPipe landmarks -> guarantees the line is
     always placed in the correct anatomical zone.
  2. Densify + locally pull each template sample onto the nearest real crease
     ridge (search along the local normal, bounded window) -> follows real lines.
  3. Robustly smooth -> curved polyline.

All coordinates here are in canonical pixel space (0..size).
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

# --------------------------------------------------------------------------
# Curve maths
# --------------------------------------------------------------------------


def catmull_rom(points: list[tuple[float, float]], samples: int = 20) -> list[tuple[float, float]]:
    """Smooth polyline through control points (centripetal-ish Catmull-Rom)."""
    if len(points) < 2:
        return list(points)
    pts = [points[0]] + list(points) + [points[-1]]
    out: list[tuple[float, float]] = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for t in range(samples):
            s = t / samples
            s2, s3 = s * s, s * s * s
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * s +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * s2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * s3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * s +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * s2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * s3)
            out.append((float(x), float(y)))
    out.append((float(points[-1][0]), float(points[-1][1])))
    return out


def _polyline_length(poly: list[tuple[float, float]]) -> float:
    if len(poly) < 2:
        return 0.0
    arr = np.asarray(poly, dtype=np.float64)
    return float(np.sum(np.linalg.norm(np.diff(arr, axis=0), axis=1)))


def _resample(poly: list[tuple[float, float]], n: int) -> list[tuple[float, float]]:
    """Resample a polyline to n evenly spaced points by arc length."""
    if len(poly) < 2 or n < 2:
        return list(poly)
    arr = np.asarray(poly, dtype=np.float64)
    seg = np.linalg.norm(np.diff(arr, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = cum[-1]
    if total <= 1e-6:
        return list(poly)
    targets = np.linspace(0.0, total, n)
    out: list[tuple[float, float]] = []
    j = 0
    for d in targets:
        while j < len(cum) - 2 and cum[j + 1] < d:
            j += 1
        span = cum[j + 1] - cum[j]
        t = 0.0 if span <= 1e-9 else (d - cum[j]) / span
        x = arr[j, 0] + t * (arr[j + 1, 0] - arr[j, 0])
        y = arr[j, 1] + t * (arr[j + 1, 1] - arr[j, 1])
        out.append((float(x), float(y)))
    return out


# --------------------------------------------------------------------------
# Landmark-anchored templates (canonical normalized 0..1)
# --------------------------------------------------------------------------

# Vertical offsets (added to a finger MCP y) and other constants, calibrated
# against the user-confirmed reference markings (data/markers/..._correct.json).
# Tunable. Canonical frame pins wrist=(0.5,0.92), middle_mcp=(0.5,0.35),
# index_mcp=(0.72,0.38); pinky/ring/thumb vary per hand.
TEMPLATE_PARAMS: dict[str, float] = {
    "heart_dy": 0.075,
    "head_web_dy": 0.090,
    "head_dy": 0.170,
    "life_top_dy": 0.135,
}


def _finger_xy(lm: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "wrist": lm[0],
        "thumb_cmc": lm[1],
        "thumb_mcp": lm[2],
        "index": lm[5],
        "middle": lm[9],
        "ring": lm[13],
        "pinky": lm[17],
    }


def line_templates(lm: np.ndarray) -> dict[str, list[tuple[float, float]]]:
    """Return control points (normalized 0..1) for each major line.

    lm: (21,2) landmarks normalized to the canonical frame (0..1).
    Canonical frame: fingers top, wrist bottom, thumb/Venus mount on the right.
    """
    p = _finger_xy(lm)
    wrist, idx, mid, ring, pink = (
        p["wrist"], p["index"], p["middle"], p["ring"], p["pinky"]
    )
    P = TEMPLATE_PARAMS
    hd = P["heart_dy"]

    # Heart line: upper arc below the finger bases, pinky side (left) -> middle.
    heart = [
        (float(pink[0] - 0.06), float(pink[1] + hd)),
        (float(ring[0]), float(ring[1] + hd + 0.01)),
        (float(mid[0] - 0.06), float(mid[1] + hd + 0.005)),
        (float(mid[0]), float(mid[1] + hd)),
    ]

    # Head line: from the index-thumb web across the palm, sloping gently down
    # toward the pinky (Moon) side.
    head = [
        (float(idx[0] - 0.04), float(idx[1] + P["head_web_dy"])),
        (float(mid[0]), float(mid[1] + P["head_dy"])),
        (float(ring[0]), float(ring[1] + P["head_dy"] + 0.03)),
        (float(pink[0] - 0.05), float(pink[1] + P["head_dy"] + 0.02)),
    ]

    # Life line: starts below the index, arcs around the Venus mount bulging
    # INTO the palm (away from the thumb, i.e. leftward in canonical) and curves
    # down to the wrist centre.
    life = [
        (float((idx[0] + mid[0]) / 2 - 0.05), float(idx[1] + P["life_top_dy"])),
        (float(mid[0] - 0.03), 0.64),
        (float(ring[0] + 0.10), 0.76),
        (float(wrist[0] - 0.03), 0.84),
        (float(wrist[0] + 0.047), float(wrist[1] - 0.03)),
    ]

    # Fate line: rises from the lower-central palm up to the middle-finger base.
    fate = [
        (0.39, 0.66),
        (0.44, 0.54),
        (0.48, 0.44),
        (float(mid[0]), float(mid[1] - 0.005)),
    ]

    return {"heart": heart, "head": head, "life": life, "fate": fate}


# --------------------------------------------------------------------------
# Crease refinement
# --------------------------------------------------------------------------


def _normals(poly: np.ndarray) -> np.ndarray:
    """Unit normals for each point of a polyline."""
    n = len(poly)
    tang = np.zeros_like(poly)
    tang[1:-1] = poly[2:] - poly[:-2]
    tang[0] = poly[1] - poly[0]
    tang[-1] = poly[-1] - poly[-2]
    norm = np.linalg.norm(tang, axis=1, keepdims=True)
    norm[norm < 1e-6] = 1.0
    tang = tang / norm
    # rotate tangent by 90 deg -> normal
    normals = np.stack([-tang[:, 1], tang[:, 0]], axis=1)
    return normals


def refine_to_creases(
    control_pts_norm: list[tuple[float, float]],
    ridge_bin: np.ndarray,
    size: int,
    *,
    search_frac: float = 0.05,
    samples: int = 90,
    max_dev_frac: float = 0.06,
) -> list[tuple[float, float]]:
    """Pull a template curve onto nearby crease ridges.

    control_pts_norm: control points in normalized (0..1) canonical coords.
    ridge_bin: binary ridge image (uint8, 0/255) in canonical pixel space.
    Returns refined polyline in canonical PIXEL coords.
    """
    ctrl_px = [(x * size, y * size) for x, y in control_pts_norm]
    dense = catmull_rom(ctrl_px, samples=max(8, samples // max(1, len(ctrl_px))))
    dense = _resample(dense, samples)
    poly = np.asarray(dense, dtype=np.float64)
    normals = _normals(poly)

    h, w = ridge_bin.shape[:2]
    win = max(4, int(search_frac * size))
    max_dev = max_dev_frac * size

    offsets = np.zeros(len(poly), dtype=np.float64)
    found = np.zeros(len(poly), dtype=bool)
    for i, (px, py) in enumerate(poly):
        nx, ny = normals[i]
        best_t = 0.0
        best_score = -1.0
        for t in range(-win, win + 1):
            sx = int(round(px + t * nx))
            sy = int(round(py + t * ny))
            if sx < 0 or sy < 0 or sx >= w or sy >= h:
                continue
            if ridge_bin[sy, sx] > 0:
                # prefer the crease closest to the template point
                score = 1.0 - abs(t) / (win + 1)
                if score > best_score:
                    best_score = score
                    best_t = float(t)
        if best_score >= 0:
            offsets[i] = best_t
            found[i] = True

    # Smooth the offset signal; only trust runs of found ridge, clamp deviation.
    offsets = np.clip(offsets, -max_dev, max_dev)
    if found.any():
        offsets = _smooth_offsets(offsets, found)
    refined = poly + normals * offsets[:, None]

    # Final smoothing pass through a few resampled control points.
    refined_list = [(float(x), float(y)) for x, y in refined]
    reduced = _resample(refined_list, 8)
    return catmull_rom(reduced, samples=18)


def _smooth_offsets(offsets: np.ndarray, found: np.ndarray) -> np.ndarray:
    """Interpolate offsets across gaps and moving-average smooth."""
    n = len(offsets)
    idx = np.arange(n)
    if found.sum() >= 2:
        offsets = np.interp(idx, idx[found], offsets[found])
    else:
        offsets = offsets.copy()
    k = max(3, n // 12)
    if k % 2 == 0:
        k += 1
    pad = k // 2
    padded = np.pad(offsets, pad, mode="edge")
    kernel = np.ones(k) / k
    return np.convolve(padded, kernel, mode="valid")


# --------------------------------------------------------------------------
# Per-line descriptive properties (for book matching)
# --------------------------------------------------------------------------


def _curvature(poly: list[tuple[float, float]]) -> float:
    """Max perpendicular deviation from the chord, normalized by chord length."""
    if len(poly) < 3:
        return 0.0
    a = np.asarray(poly[0], float)
    b = np.asarray(poly[-1], float)
    chord = b - a
    clen = np.linalg.norm(chord)
    if clen < 1e-6:
        return 0.0
    chord_u = chord / clen
    maxd = 0.0
    for px, py in poly[1:-1]:
        v = np.asarray([px, py], float) - a
        perp = abs(v[0] * chord_u[1] - v[1] * chord_u[0])
        maxd = max(maxd, perp)
    return float(maxd / clen)


def _ridge_coverage(
    poly: list[tuple[float, float]], ridge_bin: np.ndarray, size: int
) -> float:
    """Fraction of polyline samples lying on (or beside) a crease ridge."""
    if not poly:
        return 0.0
    h, w = ridge_bin.shape[:2]
    tol = max(2, int(0.012 * size))
    hit = 0
    for px, py in poly:
        x0, x1 = max(0, int(px) - tol), min(w, int(px) + tol + 1)
        y0, y1 = max(0, int(py) - tol), min(h, int(py) + tol + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        if np.any(ridge_bin[y0:y1, x0:x1] > 0):
            hit += 1
    return hit / len(poly)


def line_props_from_polyline(
    key: str,
    poly: list[tuple[float, float]],
    ridge_bin: np.ndarray,
    size: int,
) -> dict[str, Any]:
    if not poly or len(poly) < 2:
        return {"detected": False}
    length = _polyline_length(poly)
    length_ratio = length / float(size)
    coverage = _ridge_coverage(poly, ridge_bin, size)
    curv = _curvature(poly)

    if coverage > 0.6:
        depth = "deep"
    elif coverage > 0.32:
        depth = "medium"
    else:
        depth = "thin"

    out: dict[str, Any] = {
        "detected": True,
        "depth": depth,
        "length_ratio": round(length_ratio, 3),
        "curvature": round(curv, 3),
        "ridge_coverage": round(coverage, 3),
        "segment_count": max(1, int(round(coverage * 6))),
        "quality": "clear" if coverage > 0.45 else "faint",
    }

    nrm = [(x / size, y / size) for x, y in poly]
    xs = [q[0] for q in nrm]
    ys = [q[1] for q in nrm]

    if key == "life":
        out["start_zone"] = "jupiter" if ys[0] < 0.46 else "mars"
        out["reach"] = "wrist" if ys[-1] > 0.80 else "partial"
        out["sweep"] = "wide" if curv > 0.12 else "close_to_thumb"
    elif key == "head":
        slope = ys[-1] - ys[0]
        out["direction"] = "moon" if slope > 0.06 else "straight"
        out["length"] = "long" if length_ratio > 0.62 else "short"
    elif key == "heart":
        out["height"] = "high" if min(ys) < 0.34 else "normal"
        end_x = xs[-1]
        out["start_zone"] = "jupiter" if end_x > 0.58 else (
            "saturn" if end_x > 0.42 else "mercury_side"
        )
        out["length"] = "long" if length_ratio > 0.55 else "short"
    elif key == "fate":
        out["start_zone"] = "wrist" if ys[0] > 0.78 else "mid_palm"
        out["reach"] = "saturn" if ys[-1] < 0.46 else "partial"
        out["quality"] = "clear" if coverage > 0.4 else "broken"
    return out


# --------------------------------------------------------------------------
# Orchestration: major lines
# --------------------------------------------------------------------------


def detect_major_lines(
    ridge_bin: np.ndarray,
    lm_norm: np.ndarray,
    size: int,
) -> dict[str, dict[str, Any]]:
    """Return {key: {"points": [(x,y)...], "props": {...}}} in canonical pixels."""
    templates = line_templates(lm_norm)
    # Connect creases a little so the normal search finds them reliably.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    ridge_search = cv2.dilate(ridge_bin, kernel, iterations=1)

    search_cfg = {
        "heart": 0.055,
        "head": 0.06,
        "life": 0.07,
        "fate": 0.05,
    }
    out: dict[str, dict[str, Any]] = {}
    for key, ctrl in templates.items():
        poly = refine_to_creases(
            ctrl, ridge_search, size, search_frac=search_cfg.get(key, 0.05)
        )
        props = line_props_from_polyline(key, poly, ridge_bin, size)
        out[key] = {"points": poly, "props": props}
    return out


# --------------------------------------------------------------------------
# Minor lines
# --------------------------------------------------------------------------

# Each minor line: a normalized zone (x0, y0, x1, y1) plus normalized control
# points for a representative curve, in the canonical frame (thumb on right).
# Detection = ridge density inside the zone above a threshold.
MINOR_LINE_DEFS: dict[str, dict[str, Any]] = {
    "sun": {  # Apollo / success line: vertical under the ring finger
        "title": "Sun (Apollo) line",
        "zone": (0.20, 0.42, 0.46, 0.74),
        "threshold": 0.045,
    },
    "mercury": {  # Health / Mercury line: lower palm up toward the pinky base
        "title": "Mercury (Health) line",
        "zone": (0.10, 0.50, 0.46, 0.82),
        "threshold": 0.045,
    },
    "marriage": {  # Affection lines on the percussion edge below the pinky
        "title": "Marriage / affection line(s)",
        "zone": (0.06, 0.26, 0.24, 0.42),
        "threshold": 0.04,
    },
    "girdle_of_venus": {  # Arc above the heart line under middle/ring fingers
        "title": "Girdle of Venus",
        "zone": (0.28, 0.26, 0.62, 0.38),
        "threshold": 0.045,
    },
    "ring_of_solomon": {  # Arc around the base of the index (Jupiter mount)
        "title": "Ring of Solomon",
        "zone": (0.58, 0.34, 0.82, 0.48),
        "threshold": 0.05,
    },
    "children": {  # Small vertical lines above the marriage lines (percussion)
        "title": "Children line(s)",
        "zone": (0.06, 0.20, 0.22, 0.30),
        "threshold": 0.045,
    },
    "travel": {  # Restlessness/travel lines on the Moon/percussion edge (lower)
        "title": "Travel / restlessness line(s)",
        "zone": (0.05, 0.58, 0.24, 0.82),
        "threshold": 0.04,
    },
}


def _minor_curve(key: str, lm: np.ndarray) -> list[tuple[float, float]]:
    """Representative normalized control points for drawing a detected minor line."""
    p = _finger_xy(lm)
    ring, pink, mid, idx, wrist = (
        p["ring"], p["pinky"], p["middle"], p["index"], p["wrist"]
    )
    if key == "sun":
        rx = float(ring[0])
        return [(rx, 0.72), (rx - 0.01, 0.60), (rx, 0.48)]
    if key == "mercury":
        return [(0.42, 0.80), (0.30, 0.66), (float(pink[0]) + 0.02, 0.54)]
    if key == "marriage":
        return [(0.04, 0.36), (0.16, 0.36)]
    if key == "girdle_of_venus":
        return [(0.34, 0.36), (0.45, 0.32), (0.58, 0.36)]
    if key == "ring_of_solomon":
        return [(0.62, 0.46), (0.70, 0.40), (0.79, 0.45)]
    if key == "children":
        return [(0.08, 0.30), (0.08, 0.22)]
    if key == "travel":
        return [(0.04, 0.72), (0.16, 0.70)]
    return []


def _zone_ridge_density(ridge_bin: np.ndarray, zone: tuple, size: int) -> float:
    x0, y0, x1, y1 = zone
    h, w = ridge_bin.shape[:2]
    xa, xb = int(x0 * w), int(x1 * w)
    ya, yb = int(y0 * h), int(y1 * h)
    roi = ridge_bin[ya:yb, xa:xb]
    if roi.size == 0:
        return 0.0
    return float(np.count_nonzero(roi)) / roi.size


def detect_minor_lines(
    ridge_bin: np.ndarray,
    lm_norm: np.ndarray,
    size: int,
) -> dict[str, dict[str, Any]]:
    """Detect minor lines by ridge density in their anatomical zones."""
    out: dict[str, dict[str, Any]] = {}
    for key, spec in MINOR_LINE_DEFS.items():
        density = _zone_ridge_density(ridge_bin, spec["zone"], size)
        detected = density >= spec["threshold"]
        entry: dict[str, Any] = {
            "title": spec["title"],
            "detected": bool(detected),
            "density": round(density, 4),
        }
        if detected:
            ctrl = _minor_curve(key, lm_norm)
            ctrl_px = [(x * size, y * size) for x, y in ctrl]
            entry["points"] = catmull_rom(ctrl_px, samples=16) if len(ctrl_px) > 2 else ctrl_px
            if key == "marriage":
                entry["count"] = 1 if density < spec["threshold"] * 2 else 2
                entry["strength"] = "strong" if density > spec["threshold"] * 2.4 else "moderate"
            else:
                entry["strength"] = "strong" if density > spec["threshold"] * 2 else "faint"
        out[key] = entry
    return out

