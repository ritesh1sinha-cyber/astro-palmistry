#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mark chart-derived palm zones on photos (mounts, Plain of Mars, node areas)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from astro_palmistry_book_cv import (
    analyze_book_extensions,
    draw_line_timing_ticks,
    draw_yav_diksha,
    draw_zodiac_grid,
    zodiac_sectors_from_landmarks,
)
from astro_palmistry_longevity import (
    LINE_DRAW_COLORS,
    SPAN_YEARS,
    TICK_INTERVAL,
    chart_longevity_delta,
    combine_longevity,
    palm_longevity_from_life,
    saraswati_age_fractions,
)

# MediaPipe landmark indices
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP = 5, 6
MIDDLE_MCP = 9
RING_MCP = 13
PINKY_MCP = 17

ZONE_COLORS = {
    "jupiter": (60, 180, 60),
    "saturn": (180, 120, 40),
    "sun": (40, 140, 220),
    "mercury": (200, 60, 200),
    "venus": (60, 60, 220),
    "moon": (220, 180, 60),
    "mars": (40, 40, 220),
    "rahu": (40, 220, 220),
    "ketu": (220, 40, 180),
    "heart": (180, 180, 40),
    "fate": (120, 120, 120),
    "h5": (200, 120, 255),
    "h6": (140, 140, 200),
    "h8": (120, 200, 120),
    "h10": (200, 200, 80),
}

# Book: house palm zones for longevity / children / career review
HOUSE_ZONES: dict[str, list[str]] = {
    "h5": ["venus", "moon", "ketu", "heart"],
    "h6": ["saturn", "ketu", "moon", "jupiter"],
    "h8": ["mars", "moon", "saturn", "jupiter", "fate", "life"],
    "h10": ["jupiter", "sun", "mercury", "fate"],
}


def _lm_box(pts: np.ndarray, indices: list[int], pad: float, w: int, h: int) -> tuple[int, int, int, int]:
    sel = pts[indices]
    x0, y0 = sel.min(axis=0)
    x1, y1 = sel.max(axis=0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hw = max((x1 - x0) / 2 + pad, 18)
    hh = max((y1 - y0) / 2 + pad, 16)
    return (
        int(max(0, cx - hw)),
        int(max(0, cy - hh)),
        int(min(w, cx + hw)),
        int(min(h, cy + hh)),
    )


def _box_from_centre(cx: float, cy: float, hw: float, hh: float, w: int, h: int) -> tuple[int, int, int, int]:
    return (
        int(max(0, cx - hw)),
        int(max(0, cy - hh)),
        int(min(w, cx + hw)),
        int(min(h, cy + hh)),
    )


def mount_zones_from_landmarks(pts: np.ndarray, w: int, h: int) -> dict[str, tuple[int, int, int, int]]:
    """
    Book-aligned mount / node zones (Saraswati / Abayakoon).
    Jupiter-Saturn-Sun-Mercury at finger roots; Venus thenar; Moon lower percussion;
    Ketu = upper Mars on outer edge between Head & Heart; Rahu = above Heart line.
    """
    wrist = pts[WRIST]
    idx, mid, ring, pinky = pts[INDEX_MCP], pts[MIDDLE_MCP], pts[RING_MCP], pts[PINKY_MCP]
    thumb_mcp = pts[THUMB_MCP]

    zones: dict[str, tuple[int, int, int, int]] = {}

    # Classical mounts under finger roots
    zones["jupiter"] = _lm_box(pts, [INDEX_MCP, INDEX_PIP, 5], 20, w, h)
    zones["saturn"] = _lm_box(pts, [MIDDLE_MCP, 9, 10], 20, w, h)
    zones["sun"] = _lm_box(pts, [RING_MCP, 13, 14], 20, w, h)

    # Mercury: little-finger ROOT toward palm centre (not outer percussion)
    merc_cx = float(pinky[0] + ring[0]) / 2 - 8
    merc_cy = float(pinky[1]) + 18
    zones["mercury"] = _box_from_centre(merc_cx, merc_cy, 28, 24, w, h)

    # Venus: thenar / thumb ball (Taurus + Libra sectors)
    vx0 = int(max(0, min(thumb_mcp[0], idx[0]) - 25))
    vy0 = int(max(0, wrist[1] - 15))
    vx1 = int(min(w, max(thumb_mcp[0], idx[0]) + 35))
    vy1 = int(min(h, idx[1] + 55))
    zones["venus"] = (vx0, vy0, vx1, vy1)

    # Heart line band (Rahu boundary below)
    heart_y = int((idx[1] + mid[1]) / 2 + 8)
    zones["heart"] = (int(idx[0] - 35), heart_y - 14, int(ring[0] + 45), heart_y + 14)

    # Head line band (Ketu upper boundary)
    head_y = int((idx[1] + mid[1]) / 2 - 22)

    # Moon: lower percussion ONLY (Cancer sector)
    moon_x0 = int(max(0, pinky[0] - 6))
    moon_x1 = int(min(w, pinky[0] + 30))
    moon_y0 = int(min(h, heart_y + 25))
    moon_y1 = int(min(h, wrist[1] + 70))
    zones["moon"] = (moon_x0, moon_y0, moon_x1, moon_y1)

    # Ketu / upper Mars (negative Mars): percussion between Head & Heart
    ketu_x0 = int(max(0, pinky[0] - 4))
    ketu_x1 = int(min(w, pinky[0] + 34))
    zones["ketu"] = (ketu_x0, head_y, ketu_x1, heart_y)

    # Rahu: Great Triangle - area ABOVE heart line (central + upper)
    rahu_y0 = int(max(0, min(idx[1], mid[1]) - 75))
    rahu_y1 = heart_y - 4
    cx = int((idx[0] + ring[0]) / 2)
    zones["rahu"] = (cx - 55, rahu_y0, cx + 55, rahu_y1)

    # Plain of Mars (Aries battlefield) - centre palm
    cx_m = int((idx[0] + ring[0]) / 2)
    cy_m = int((idx[1] + mid[1]) / 2 + 30)
    zones["mars"] = (cx_m - 48, cy_m - 38, cx_m + 48, cy_m + 38)

    # Fate line: vertical mid-palm toward Saturn
    zones["fate"] = (cx_m - 20, int(idx[1] + 10), cx_m + 20, int(wrist[1] + 55))

    return zones


def _union_boxes(boxes: list[tuple[int, int, int, int]], w: int, h: int) -> tuple[int, int, int, int]:
    if not boxes:
        return (0, 0, w, h)
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes)
    y1 = max(b[3] for b in boxes)
    return (max(0, x0), max(0, y0), min(w, x1), min(h, y1))


def house_overlay_zones(mounts: dict[str, tuple[int, int, int, int]], w: int, h: int) -> dict[str, tuple[int, int, int, int]]:
    """Larger dashed house-sector boxes for 5th / 6th / 8th / 10th review."""
    out: dict[str, tuple[int, int, int, int]] = {}
    for hid, parts in HOUSE_ZONES.items():
        boxes = [mounts[p] for p in parts if p in mounts]
        if boxes:
            out[hid] = _union_boxes(boxes, w, h)
    return out


MIN_SHARPNESS = 90.0

DOMAIN_ZONES: dict[str, list[str]] = {
    "children": ["ketu", "venus", "heart", "h5"],
    "career": ["mercury", "sun", "fate", "jupiter", "h10"],
    "longevity": ["jupiter", "fate", "saturn", "mars", "h8", "life"],
    "health": ["saturn", "mars", "ketu", "h6"],
    "gains": ["mars", "rahu", "sun", "venus"],
    "home": ["moon", "venus", "heart"],
    "luck": ["sun", "jupiter", "moon"],
}


def _roi_sharpness(gray: np.ndarray) -> float:
    if gray.size < 16:
        return 0.0
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def inspect_roi(roi: np.ndarray) -> dict[str, Any]:
    """CV inspect one palm zone: line count, sharpness, quality, stress flag."""
    if roi is None or roi.size == 0 or roi.shape[0] < 8 or roi.shape[1] < 8:
        return {
            "line_count": 0,
            "sharpness": 0.0,
            "quality": "poor",
            "stress_lines": False,
            "sparse": True,
            "readable": False,
        }
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    sharp = _roi_sharpness(gray)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    sx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    vert = np.clip(np.abs(sx), 0, None)
    vert = cv2.normalize(vert, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    _, bw = cv2.threshold(vert, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    col = bw.sum(axis=0).astype(float)
    line_count = 0
    if col.max() >= 1:
        thresh = max(col.mean() * 1.3, col.max() * 0.3)
        peaks: list[int] = []
        for x in range(2, bw.shape[1] - 2):
            if col[x] >= thresh and col[x] >= col[x - 1] and col[x] >= col[x + 1]:
                if not peaks or x - peaks[-1] >= 3:
                    peaks.append(x)
        line_count = min(len(peaks), 20)

    if sharp < MIN_SHARPNESS * 0.5:
        quality = "poor"
    elif sharp < MIN_SHARPNESS:
        quality = "fair"
    else:
        quality = "good"

    return {
        "line_count": line_count,
        "sharpness": round(sharp, 1),
        "quality": quality,
        "stress_lines": line_count >= 7,
        "sparse": line_count <= 2,
        "readable": quality != "poor",
    }


def cv_finding_sentence(zone_id: str, metrics: dict[str, Any], chart_expects_stress: bool) -> str:
    """Plain sentence from CV metrics - no 'check' or 'likely'."""
    if not metrics:
        return f"No palm photo was analysed for the {zone_id} zone."
    q = metrics.get("quality", "poor")
    sharp = metrics.get("sharpness", 0)
    lc = metrics.get("line_count", 0)
    if q == "poor":
        return (
            f"Photo not clear in {zone_id} zone (sharpness {sharp}) - "
            f"lines cannot be read reliably on this print. Re-upload a close-up."
        )
    if metrics.get("stress_lines") and chart_expects_stress:
        return (
            f"On your print: {lc} vertical lines in {zone_id} zone (sharpness {sharp}) - "
            f"dense cross-line pattern matches chart stress for this area."
        )
    if metrics.get("sparse"):
        return (
            f"On your print: only {lc} line(s) in {zone_id} zone (sharpness {sharp}) - "
            f"sparse marking; chart stress is not mirrored as a heavy grille here."
        )
    return (
        f"On your print: {lc} vertical lines in {zone_id} zone (sharpness {sharp}, {q} quality)."
    )


def _detect_major_lines_on_image(bgr: np.ndarray, pts: np.ndarray) -> dict[str, Any]:
    """Run palm line CV; return polylines in original image coordinates."""
    from palm_api.analyzer import _enhance_ridges, _inverse_affine_points, _palm_mask_from_landmarks, _prepare_warped_palm
    from palm_api.palm_lines import detect_major_lines

    warped, wpts, meta = _prepare_warped_palm(bgr, pts)
    h, w = warped.shape[:2]
    size = min(h, w)
    mask = _palm_mask_from_landmarks(warped, wpts)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    ridge = _enhance_ridges(gray, mask)
    lm_norm = wpts.astype(np.float64) / float(size)
    major = detect_major_lines(ridge, lm_norm, size)

    M = meta.get("M")
    flip = bool(meta.get("canonical_flip", False))
    orig_w = int(bgr.shape[1])

    out: dict[str, Any] = {}
    for key in ("life", "head", "heart", "fate"):
        entry = major.get(key) or {}
        props = dict(entry.get("props") or {"detected": False})
        poly_o: list[tuple[int, int]] = []
        if props.get("detected") and entry.get("points"):
            poly_o = [
                (int(x), int(y))
                for x, y in _inverse_affine_points(entry["points"], M, flip, orig_w)
            ]
            props["points"] = poly_o
        out[key] = props
    return out


def _draw_polyline(overlay: np.ndarray, pts: list[tuple[int, int]], color: tuple[int, int, int], thickness: int = 2) -> None:
    if len(pts) < 2:
        return
    arr = np.array(pts, dtype=np.int32)
    cv2.polylines(overlay, [arr], False, color, thickness, cv2.LINE_AA)


def _draw_age_ticks_on_life(
    overlay: np.ndarray,
    life_poly: list[tuple[int, int]],
    jup_sat_mid: tuple[float, float],
) -> list[dict[str, Any]]:
    """Mark 5-year ticks on life line; highlight age 20 (Jupiter-Saturn perpendicular)."""
    if len(life_poly) < 2:
        return []
    poly_f = [(float(x), float(y)) for x, y in life_poly]
    fracs = saraswati_age_fractions(poly_f, jup_sat_mid)
    marks: list[dict[str, Any]] = []
    color = LINE_DRAW_COLORS["life"]
    for age in range(0, SPAN_YEARS + 1, TICK_INTERVAL):
        frac = fracs.get(age, age / SPAN_YEARS)
        x, y = _point_at_arc_fraction_local(poly_f, frac)
        r = 5 if age % 10 == 0 else 3
        tick_color = (0, 255, 255) if age == 20 else color
        cv2.circle(overlay, (x, y), r, tick_color, -1, cv2.LINE_AA)
        if age % 10 == 0 or age == 20:
            cv2.putText(
                overlay, str(age), (x + 4, y - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, tick_color, 1, cv2.LINE_AA,
            )
        marks.append({"age": age, "x": x, "y": y, "fraction": round(frac, 3)})
    return marks


def _point_at_arc_fraction_local(poly: list[tuple[float, float]], frac: float) -> tuple[int, int]:
    import math
    if not poly:
        return (0, 0)
    frac = max(0.0, min(1.0, frac))
    cum = [0.0]
    total = 0.0
    for i in range(1, len(poly)):
        dx = poly[i][0] - poly[i - 1][0]
        dy = poly[i][1] - poly[i - 1][1]
        total += math.hypot(dx, dy)
        cum.append(total)
    if total < 1e-6:
        return int(poly[0][0]), int(poly[0][1])
    target = frac * total
    for i in range(1, len(poly)):
        if cum[i] >= target:
            seg = cum[i] - cum[i - 1]
            t = 0.0 if seg < 1e-6 else (target - cum[i - 1]) / seg
            x = poly[i - 1][0] + t * (poly[i][0] - poly[i - 1][0])
            y = poly[i - 1][1] + t * (poly[i][1] - poly[i - 1][1])
            return int(x), int(y)
    return int(poly[-1][0]), int(poly[-1][1])


def mark_chart_zones_on_palm(
    bgr: np.ndarray,
    zone_plan: list[dict[str, Any]],
    out_path: Path | None = None,
    *,
    chart_planets: dict[str, dict[str, Any]] | None = None,
    draw_house_zones: bool = True,
    draw_longevity_lines: bool = True,
    show_zodiac_grid: bool = True,
    draw_sacred_marks: bool = True,
) -> dict[str, Any]:
    """
    Draw book-aligned mount boxes, house sectors, zodiac grid, major lines + 5-yr ticks,
    Yav/Diksha markers, and mount boxes.
    """
    from palm_api.analyzer import detect_hand_landmarks

    pts, err = detect_hand_landmarks(bgr)
    if pts is None:
        return {"error": err, "quality": "poor"}

    h, w = bgr.shape[:2]
    mounts = mount_zones_from_landmarks(pts, w, h)
    overlay = bgr.copy()
    marked: list[dict[str, Any]] = []

    # House sector outlines (dashed) for longevity review
    if draw_house_zones:
        house_boxes = house_overlay_zones(mounts, w, h)
        house_labels = {"h5": "5th", "h6": "6th", "h8": "8th-LONG", "h10": "10th"}
        for hid, box in house_boxes.items():
            x0, y0, x1, y1 = box
            col = ZONE_COLORS.get(hid, (180, 180, 180))
            for i in range(x0, x1, 10):
                cv2.line(overlay, (i, y0), (min(i + 5, x1), y0), col, 1)
                cv2.line(overlay, (i, y1), (min(i + 5, x1), y1), col, 1)
            for j in range(y0, y1, 10):
                cv2.line(overlay, (x0, j), (x0, min(j + 5, y1)), col, 1)
                cv2.line(overlay, (x1, j), (x1, min(j + 5, y1)), col, 1)
            cv2.putText(
                overlay, house_labels.get(hid, hid), (x0 + 4, max(16, y0 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA,
            )

    # 12-sector zodiac grid (book pp. 88-89)
    zodiac_sectors: list[dict[str, Any]] = []
    if show_zodiac_grid:
        zodiac_sectors = zodiac_sectors_from_landmarks(pts, w, h)
        draw_zodiac_grid(overlay, zodiac_sectors)

    # Book extensions: tips, nails, Yav/Diksha
    book_ext = analyze_book_extensions(bgr, pts)
    if draw_sacred_marks:
        draw_yav_diksha(overlay, book_ext.get("yav_diksha") or {})

    # Major lines + Saraswati 5-year age ticks (life, head, heart, fate)
    line_data: dict[str, Any] = {}
    age_marks: list[dict[str, Any]] = []
    longevity_result: dict[str, Any] | None = None

    if draw_longevity_lines:
        line_data = _detect_major_lines_on_image(bgr, pts)
        idx, mid = pts[INDEX_MCP], pts[MIDDLE_MCP]
        jup_sat_mid = (float(idx[0] + mid[0]) / 2, float(idx[1] + mid[1]) / 2)

        for key in ("heart", "head", "fate", "life"):
            props = line_data.get(key) or {}
            poly = props.get("points") or []
            if props.get("detected") and len(poly) >= 2:
                col = LINE_DRAW_COLORS.get(key, (200, 200, 200))
                thick = 3 if key == "life" else 2
                _draw_polyline(overlay, poly, col, thick)
                cv2.putText(
                    overlay, key.upper(), poly[0],
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, col, 1, cv2.LINE_AA,
                )
                ticks = draw_line_timing_ticks(overlay, key, poly, jup_sat_mid)
                age_marks.extend(ticks)

        life_poly = (line_data.get("life") or {}).get("points") or []
        if life_poly:
            # Re-draw life ticks with Saraswati anchor at Jupiter-Saturn (age 20)
            age_marks = [m for m in age_marks if m.get("line") != "life"]
            age_marks.extend(_draw_age_ticks_on_life(overlay, life_poly, jup_sat_mid))
            jx, jy = int(jup_sat_mid[0]), int(jup_sat_mid[1])
            cv2.line(overlay, (jx, jy - 30), (jx, jy + 30), (0, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(overlay, "J-S age20", (jx + 4, jy - 32), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)

        if chart_planets:
            palm_est = palm_longevity_from_life(line_data.get("life") or {}, life_poly)
            chart_d = chart_longevity_delta(chart_planets)
            longevity_result = combine_longevity(palm_est, chart_d)

    # Planet mount boxes (dedupe by zone_id - keep first label)
    seen_zones: set[str] = set()
    for item in zone_plan:
        zid = item.get("zone_id", "mars")
        if zid in seen_zones:
            continue
        seen_zones.add(zid)
        box = mounts.get(zid)
        if not box:
            continue
        x0, y0, x1, y1 = box
        color = ZONE_COLORS.get(zid, (200, 200, 200))
        roi = bgr[y0:y1, x0:x1]
        metrics = inspect_roi(roi)
        line_count = metrics["line_count"]
        qtag = metrics["quality"][0].upper()
        cv2.rectangle(overlay, (x0, y0), (x1, y1), color, 2)
        txt = f"{zid}:{line_count}L/{qtag}"
        cv2.putText(overlay, txt, (x0, max(14, y0 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
        marked.append({
            "planet": item.get("planet"),
            "zone_id": zid,
            "role": item.get("role", "sub"),
            "box": box,
            "line_count": line_count,
            "sharpness": metrics["sharpness"],
            "quality": metrics["quality"],
            "stress_lines": metrics["stress_lines"],
            "sparse": metrics["sparse"],
            "readable": metrics["readable"],
            "label": item.get("label", item.get("planet", zid)),
        })

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_path), overlay)

    poor_n = sum(1 for m in marked if m.get("quality") == "poor")
    overall = "poor" if poor_n >= len(marked) // 2 else ("fair" if poor_n else "good")
    return {
        "quality": overall,
        "marked_zones": marked,
        "overlay_path": str(out_path) if out_path else None,
        "lines": line_data,
        "age_marks": age_marks,
        "longevity": longevity_result,
        "book_extensions": book_ext,
        "zodiac_sectors": zodiac_sectors,
    }


def aggregate_zone_metrics(marked_lists: list[list[dict]]) -> dict[str, dict[str, Any]]:
    """Merge CV from multiple hand photos - keep best sharpness per zone."""
    best: dict[str, dict[str, Any]] = {}
    for marked in marked_lists:
        for m in marked:
            zid = m.get("zone_id", "")
            if not zid:
                continue
            prev = best.get(zid)
            if prev is None or m.get("sharpness", 0) > prev.get("sharpness", 0):
                best[zid] = m
    return best
