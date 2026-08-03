#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Saraswati book CV extensions:
- Finger tip shape (spatulate / square / conic)
- Nail colour from fingertip ROI
- 5-year timing ticks on head / heart / fate lines
- 12-sector zodiac grid on palm
- Yav (thumb base) and Diksha (under Jupiter) detectors
"""
from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np

from astro_palmistry_longevity import (
    LINE_DRAW_COLORS,
    SPAN_YEARS,
    TICK_INTERVAL,
    saraswati_age_fractions,
)

FINGER_CHAINS: dict[str, tuple[int, ...]] = {
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
}

TIP_SHAPE_BOOK: dict[str, str] = {
    "spatulate": "Spatulate (action, cardinal energy - book)",
    "square": "Square (earth, discipline, fixed signs)",
    "conic": "Conic / pointed (impulse, mutable, artistic)",
    "mixed": "Mixed tip - between types",
}

NAIL_BOOK: dict[str, str] = {
    "pink_sun": "Pink/white nails - Sun influence; vitality and confidence",
    "pale_moon": "Pale nails - Moon / mixed temperament",
    "yellow_saturn": "Yellow nails - Saturn influence; caution, discipline",
    "dark_rahu": "Dark nails - Saturn/Rahu stress; watch health periods",
}

# Book zodiac sectors (labels for overlay)
ZODIAC_SECTORS: list[tuple[str, str]] = [
    ("Aries", "Plain of Mars"),
    ("Taurus", "Lower Venus / Jupiter"),
    ("Gemini", "Mercury finger above heart"),
    ("Cancer", "Moon + Mars plain"),
    ("Leo", "Sun finger above heart"),
    ("Virgo", "Quadrangle Saturn-Sun (Ketu)"),
    ("Libra", "Thumb-Life sector"),
    ("Scorpio", "Upper Mars outer (Ketu)"),
    ("Sagittarius", "Jupiter to head line"),
    ("Capricorn", "Saturn upper"),
    ("Aquarius", "Saturn lower"),
    ("Pisces", "Moon upper / life end"),
]

ZODIAC_COLORS = [
    (80, 80, 200), (80, 160, 200), (80, 200, 80), (200, 160, 80),
    (80, 200, 200), (200, 80, 200), (200, 200, 80), (200, 80, 80),
    (160, 200, 80), (80, 120, 200), (120, 80, 200), (200, 120, 160),
]


def _perp_width(pts: np.ndarray, a: int, b: int) -> float:
    """Segment length as proxy for phalange width."""
    return float(np.linalg.norm(pts[b] - pts[a]))


def classify_finger_tips(pts: np.ndarray, bgr: np.ndarray | None = None) -> dict[str, dict[str, Any]]:
    """Tip shape from landmark taper + optional tip ROI contour."""
    out: dict[str, dict[str, Any]] = {}
    for fname, chain in FINGER_CHAINS.items():
        pip_w = _perp_width(pts, chain[1], chain[2])
        dip_w = _perp_width(pts, chain[2], chain[3])
        tip_w = dip_w * 0.95 + pip_w * 0.05
        base_w = max(pip_w, 1e-6)
        ratio = tip_w / base_w

        # Optional image refinement at fingertip
        contour_ratio = ratio
        if bgr is not None:
            tip = pts[chain[3]].astype(int)
            x, y = int(tip[0]), int(tip[1])
            h, w = bgr.shape[:2]
            r = 14
            roi = bgr[max(0, y - r):min(h, y + r), max(0, x - r):min(w, x + r)]
            if roi.size > 100:
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if cnts:
                    c = max(cnts, key=cv2.contourArea)
                    bx, by, bw2, bh2 = cv2.boundingRect(c)
                    if min(bw2, bh2) > 2:
                        contour_ratio = max(bw2, bh2) / max(min(bw2, bh2), 1)

        if ratio > 1.06 or contour_ratio > 1.35:
            shape = "spatulate"
        elif ratio < 0.88 or contour_ratio < 0.75:
            shape = "conic"
        elif 0.92 <= ratio <= 1.05:
            shape = "square"
        else:
            shape = "mixed"

        out[fname] = {
            "shape": shape,
            "label": TIP_SHAPE_BOOK.get(shape, shape),
            "tip_to_pip_ratio": round(ratio, 2),
            "contour_aspect": round(contour_ratio, 2),
        }
    return out


def classify_nail_colours(pts: np.ndarray, bgr: np.ndarray) -> dict[str, dict[str, Any]]:
    """Nail colour from fingertip + thumb tip ROIs (HSV)."""
    out: dict[str, dict[str, Any]] = {}
    rois = {**FINGER_CHAINS, "thumb": (2, 3, 4)}

    for fname, chain in rois.items():
        tip_idx = chain[-1]
        tip = pts[tip_idx].astype(int)
        x, y = int(tip[0]), int(tip[1])
        h, w = bgr.shape[:2]
        # Nail plate above tip landmark
        y0, y1 = max(0, y - 22), max(0, y - 4)
        x0, x1 = max(0, x - 10), min(w, x + 10)
        roi = bgr[y0:y1, x0:x1]
        if roi.size < 30:
            out[fname] = {"colour": "unknown", "label": "Nail not visible - finger close-up needed"}
            continue
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        v = float(hsv[:, :, 2].mean())
        s = float(hsv[:, :, 1].mean())
        hue = float(hsv[:, :, 0].mean())
        lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
        l_chan = float(lab[:, :, 0].mean())

        if l_chan < 45 or v < 50:
            key = "dark_rahu"
        elif hue < 25 and s > 60 and v > 100:
            key = "yellow_saturn"
        elif l_chan > 175 or (s < 50 and v > 140):
            key = "pink_sun"
        else:
            key = "pale_moon"

        out[fname] = {
            "colour": key,
            "label": NAIL_BOOK.get(key, key),
            "hsv": (round(hue, 1), round(s, 1), round(v, 1)),
            "readable": v > 40,
        }
    return out


def _point_at_arc_fraction(poly: list[tuple[float, float]], frac: float) -> tuple[int, int]:
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


def _line_age_fractions(line_key: str, poly: list[tuple[float, float]], jup_sat_mid: tuple[float, float] | None) -> dict[int, float]:
    if line_key == "life":
        return saraswati_age_fractions(poly, jup_sat_mid)
    # Book: divide head, heart, fate in 5-year sections on 80-year scale
    n_steps = SPAN_YEARS // TICK_INTERVAL
    return {age: age / SPAN_YEARS for age in range(0, SPAN_YEARS + 1, TICK_INTERVAL)}


def draw_line_timing_ticks(
    overlay: np.ndarray,
    line_key: str,
    poly: list[tuple[int, int]],
    jup_sat_mid: tuple[float, float] | None = None,
) -> list[dict[str, Any]]:
    """Draw 5-year age ticks on a major line (Saraswati 80-yr scale)."""
    if len(poly) < 2:
        return []
    poly_f = [(float(x), float(y)) for x, y in poly]
    fracs = _line_age_fractions(line_key, poly_f, jup_sat_mid)
    color = LINE_DRAW_COLORS.get(line_key, (200, 200, 200))
    marks: list[dict[str, Any]] = []
    for age in range(0, SPAN_YEARS + 1, TICK_INTERVAL):
        frac = fracs.get(age, age / SPAN_YEARS)
        x, y = _point_at_arc_fraction(poly_f, frac)
        r = 4 if age % 10 else 3
        cv2.circle(overlay, (x, y), r, color, -1, cv2.LINE_AA)
        if age % 20 == 0 and line_key == "life":
            cv2.putText(overlay, str(age), (x + 3, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)
        marks.append({"line": line_key, "age": age, "x": x, "y": y})
    return marks


def zodiac_sectors_from_landmarks(pts: np.ndarray, w: int, h: int) -> list[dict[str, Any]]:
    """12 book zodiac sectors as labelled boxes."""
    wrist = pts[0]
    idx, mid, ring, pinky = pts[5], pts[9], pts[13], pts[17]
    thumb = pts[2]
    cx = int((idx[0] + ring[0]) / 2)
    heart_y = int((idx[1] + mid[1]) / 2 + 8)
    head_y = int((idx[1] + mid[1]) / 2 - 22)

    sectors: list[tuple[str, str, tuple[int, int, int, int]]] = [
        ("Aries", "Plain of Mars", (cx - 48, heart_y + 10, cx + 48, int(wrist[1] + 40))),
        ("Taurus", "Venus/Jupiter", (int(min(thumb[0], idx[0]) - 10), heart_y, int(idx[0] + 30), int(wrist[1] + 30))),
        ("Gemini", "Mercury above heart", (int(pinky[0] - 40), head_y, int(pinky[0] + 10), heart_y)),
        ("Cancer", "Moon+Mars", (int(pinky[0] - 8), heart_y + 20, int(pinky[0] + 32), int(wrist[1] + 50))),
        ("Leo", "Sun above heart", (int(ring[0] - 28), head_y - 10, int(ring[0] + 28), heart_y)),
        ("Virgo", "Quadrangle", (int(idx[0] - 20), head_y, int(ring[0] + 20), heart_y)),
        ("Libra", "Life-thumb", (int(thumb[0] - 5), int(wrist[1] - 10), int(idx[0] + 15), heart_y + 15)),
        ("Scorpio", "Upper Mars", (int(pinky[0] - 4), head_y, int(pinky[0] + 34), heart_y)),
        ("Sagittarius", "Jupiter to head", (int(idx[0] - 30), int(idx[1] - 30), int(idx[0] + 30), head_y)),
        ("Capricorn", "Saturn upper", (int(mid[0] - 26), head_y - 8, int(mid[0] + 26), heart_y - 2)),
        ("Aquarius", "Saturn lower", (int(mid[0] - 26), heart_y - 2, int(mid[0] + 26), heart_y + 12)),
        ("Pisces", "Moon upper", (int(pinky[0] - 6), heart_y + 12, int(pinky[0] + 30), int(mid[1] + 50))),
    ]

    out: list[dict[str, Any]] = []
    for i, (sign, desc, box) in enumerate(sectors):
        x0, y0, x1, y1 = box
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        out.append({
            "sign": sign,
            "description": desc,
            "box": (x0, y0, x1, y1),
            "color": ZODIAC_COLORS[i % len(ZODIAC_COLORS)],
        })
    return out


def draw_zodiac_grid(overlay: np.ndarray, sectors: list[dict[str, Any]]) -> None:
    for s in sectors:
        x0, y0, x1, y1 = s["box"]
        col = s["color"]
        for i in range(x0, x1, 8):
            cv2.line(overlay, (i, y0), (min(i + 4, x1), y0), col, 1)
            cv2.line(overlay, (i, y1), (min(i + 4, x1), y1), col, 1)
        cv2.putText(
            overlay, s["sign"][:3], (x0 + 2, max(12, y0 + 10)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.32, col, 1, cv2.LINE_AA,
        )


def _ridge_in_roi(bgr: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = box
    roi = bgr[y0:y1, x0:x1]
    if roi.size == 0:
        return np.zeros((1, 1), dtype=np.uint8)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    bh = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
    _, bw = cv2.threshold(bh, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return bw


def detect_yav_diksha(bgr: np.ndarray, pts: np.ndarray) -> dict[str, Any]:
    """
    Yav: mark at thumb base / rascette (scholar sign).
    Diksha: horizontal line under Jupiter (index) finger - renunciation line.
    """
    h, w = bgr.shape[:2]
    thumb_mcp, thumb_ip = pts[2], pts[3]
    idx_mcp, idx_pip = pts[5], pts[6]
    wrist = pts[0]

    # Yav ROI: thumb base near rascette
    yx0 = int(max(0, min(thumb_mcp[0], wrist[0]) - 15))
    yx1 = int(min(w, max(thumb_mcp[0], idx_mcp[0]) + 20))
    yy0 = int(max(0, wrist[1] - 15))
    yy1 = int(min(h, thumb_mcp[1] + 25))
    yav_bw = _ridge_in_roi(bgr, (yx0, yy0, yx1, yy1))

    yav_found = False
    yav_conf = 0.0
    yav_xy = (int((yx0 + yx1) / 2), int((yy0 + yy1) / 2))
    cnts, _ = cv2.findContours(yav_bw, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts:
        area = cv2.contourArea(c)
        if area < 20 or area > 800:
            continue
        peri = cv2.arcLength(c, True)
        if peri < 10:
            continue
        approx = cv2.approxPolyDP(c, 0.08 * peri, True)
        circ = 4 * np.pi * area / (peri * peri)
        # Yav ~ small bar, triangle, or island at thumb base
        if len(approx) in (3, 4) or (0.35 < circ < 0.85):
            M = cv2.moments(c)
            if M["m00"] > 0:
                yav_xy = (int(M["m10"] / M["m00"]) + yx0, int(M["m01"] / M["m00"]) + yy0)
            yav_found = True
            yav_conf = 0.55 if len(approx) == 3 else 0.48
            break

    # Diksha ROI: under index finger (Jupiter)
    dx0 = int(max(0, idx_mcp[0] - 25))
    dx1 = int(min(w, idx_mcp[0] + 25))
    dy0 = int(max(0, idx_mcp[1] - 5))
    dy1 = int(min(h, idx_pip[1] + 15))
    dik_bw = _ridge_in_roi(bgr, (dx0, dy0, dx1, dy1))

    dik_found = False
    dik_conf = 0.0
    dik_xy = (int((dx0 + dx1) / 2), int((dy0 + dy1) / 2))
    # Horizontal line: strong row projection
    row_sum = dik_bw.sum(axis=1).astype(float)
    if row_sum.max() > 0:
        thresh = row_sum.max() * 0.55
        rows = np.where(row_sum >= thresh)[0]
        if len(rows) >= 1:
            # cluster of consecutive rows = horizontal crease
            run = 1
            best_run = 1
            for i in range(1, len(rows)):
                if rows[i] - rows[i - 1] <= 2:
                    run += 1
                    best_run = max(best_run, run)
                else:
                    run = 1
            if best_run >= 2 and (dx1 - dx0) > 20:
                r = int(rows[len(rows) // 2])
                dik_xy = (int((dx0 + dx1) / 2), dy0 + r)
                dik_found = True
                dik_conf = min(0.7, 0.4 + best_run * 0.08)

    return {
        "yav": {
            "detected": yav_found,
            "confidence": round(yav_conf, 2),
            "position": yav_xy,
            "meaning": "Yav at thumb base - scholar, wealth, happy sustenance (book); bright/dark half birth clue",
            "roi": (yx0, yy0, yx1, yy1),
        },
        "diksha": {
            "detected": dik_found,
            "confidence": round(dik_conf, 2),
            "position": dik_xy,
            "meaning": "Diksha line under Jupiter finger - renunciation, occult wealth, high intellect (book)",
            "roi": (dx0, dy0, dx1, dy1),
        },
    }


def draw_yav_diksha(overlay: np.ndarray, det: dict[str, Any]) -> None:
    if det.get("yav", {}).get("detected"):
        x, y = det["yav"]["position"]
        cv2.circle(overlay, (x, y), 8, (0, 255, 255), 2)
        cv2.putText(overlay, "YAV", (x + 6, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    if det.get("diksha", {}).get("detected"):
        x, y = det["diksha"]["position"]
        cv2.circle(overlay, (x, y), 6, (255, 200, 0), 2)
        cv2.putText(overlay, "DIKSHA", (x + 6, y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 200, 0), 1)


def analyze_book_extensions(bgr: np.ndarray, pts: np.ndarray) -> dict[str, Any]:
    """Run all 5 book CV extensions on one palm image."""
    h, w = bgr.shape[:2]
    tips = classify_finger_tips(pts, bgr)
    nails = classify_nail_colours(pts, bgr)
    zodiac = zodiac_sectors_from_landmarks(pts, w, h)
    sacred = detect_yav_diksha(bgr, pts)
    return {
        "finger_tips": tips,
        "nails": nails,
        "zodiac_sectors": zodiac,
        "yav_diksha": sacred,
    }


def line_timing_html(timing_marks: list[dict] | None, lines_summary: dict | None = None) -> str:
    """Saraswati 5-year timing on life / head / heart / fate lines."""
    if not timing_marks:
        return ""
    by_line: dict[str, list[int]] = {}
    for m in timing_marks:
        lk = m.get("line", "?")
        by_line.setdefault(lk, []).append(int(m.get("age", 0)))

    rows = []
    for lk in ("life", "head", "heart", "fate"):
        ages = sorted(set(by_line.get(lk, [])))
        if not ages:
            det = "not detected"
            if lines_summary:
                for hand, ls in lines_summary.items():
                    if (ls or {}).get(lk, {}).get("detected"):
                        det = f"detected on {hand} hand (ticks not drawn)"
            rows.append(f"<li><strong>{lk.title()} line:</strong> {det}</li>")
            continue
        sample = ", ".join(str(a) for a in ages[:9])
        if len(ages) > 9:
            sample += f", ... ({len(ages)} ticks, every 5 yr to age 80)"
        rows.append(
            f"<li><strong>{lk.title()} line:</strong> 5-year age marks at {sample}. "
            f"Life line uses Jupiter-Saturn perpendicular anchor at age 20.</li>"
        )

    return f"""
<div class="section-h">Line timing (Saraswati 80-year scale)</div>
<div class="card">
  <p class="body">Major lines are divided into 5-year sections on the overlay (coloured dots).
  Cross-check chart dasha with the age band where a line breaks, island, or mount stress appears.</p>
  <ul class="bullets">{''.join(rows)}</ul>
</div>
"""


def book_extensions_html(ext: dict[str, Any] | None, timing_marks: list[dict] | None = None) -> str:
    """Per-hand tips, nails, zodiac note, Yav/Diksha."""
    if not ext:
        return ""

    # Support {"left": {...}, "right": {...}} or flat single-hand dict
    hands = ext if "left" in ext or "right" in ext else {"palm": ext}
    blocks: list[str] = []

    for hand_label, hand_ext in hands.items():
        if not hand_ext:
            continue
        tips = hand_ext.get("finger_tips") or {}
        nails = hand_ext.get("nails") or {}
        sacred = hand_ext.get("yav_diksha") or {}

        tip_ul = "".join(
            f"<li>{k.title()}: <strong>{v.get('shape')}</strong> - {v.get('label', '')}</li>"
            for k, v in tips.items()
        )
        nail_ul = "".join(
            f"<li>{k.title()}: {v.get('label', 'not visible')}</li>"
            for k, v in nails.items()
        )

        yav = sacred.get("yav") or {}
        dik = sacred.get("diksha") or {}
        sacred_txt = []
        if yav.get("detected"):
            sacred_txt.append(
                f"<li><strong>Yav</strong> at thumb base (conf {yav.get('confidence')}) - "
                f"{yav.get('meaning', '')}</li>"
            )
        else:
            sacred_txt.append(
                "<li><strong>Yav</strong> not detected - thumb-base close-up improves scholar-mark read.</li>"
            )
        if dik.get("detected"):
            sacred_txt.append(
                f"<li><strong>Diksha line</strong> under Jupiter finger (conf {dik.get('confidence')}) - "
                f"{dik.get('meaning', '')}</li>"
            )
        else:
            sacred_txt.append(
                "<li><strong>Diksha line</strong> not seen - index-finger root close-up needed.</li>"
            )

        blocks.append(f"""
<div class="card">
  <h4>{hand_label.title()} hand - book CV extensions</h4>
  <p class="body"><strong>Finger tip shapes:</strong></p><ul class="bullets">{tip_ul}</ul>
  <p class="body"><strong>Nail colour (book):</strong></p><ul class="bullets">{nail_ul}</ul>
  <p class="body"><strong>12-sector zodiac grid</strong> on overlay (Ari, Tau, Gem, Can, Leo, Vir, Lib, Sco, Sag, Cap, Aqu, Pis).</p>
  <p class="body"><strong>Sacred marks:</strong></p><ul class="bullets">{''.join(sacred_txt)}</ul>
</div>
""")

    return f'<div class="section-h">Tips, nails, zodiac sectors &amp; sacred marks</div>{"".join(blocks)}'
