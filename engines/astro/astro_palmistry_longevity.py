#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Saraswati Astro-Palmistry longevity (80-year scale).

Book rules (Jyotis Saraswati / Abayakoon):
- Saturn finger = 80-year life scale.
- Perpendicular between Jupiter and Saturn finger roots hits life line at age 20.
- Life line divided backward from start in 5-year sections.
- Heart / Head lines cross-check; deduct elapsed years from 80.
- Chart dignity in dusthana houses modifies the palm read.
"""
from __future__ import annotations

import math
from typing import Any

# BGR colours for drawn lines on overlay
LINE_DRAW_COLORS = {
    "life": (30, 180, 220),   # gold
    "heart": (40, 40, 220),   # red
    "head": (60, 170, 40),    # green
    "fate": (0, 140, 255),    # orange
}

LINE_DRAW_NAMES = {"life": "Life", "head": "Head", "heart": "Heart", "fate": "Fate"}

SPAN_YEARS = 80
TICK_INTERVAL = 5
ANCHOR_AGE_JUP_SAT = 20

# Chart palm modifiers (years) when line-main is afflicted / supported
CHART_YEAR_DELTA: dict[tuple[str, int, str], int] = {
    ("Jupiter", 8, "debilitated"): -10,
    ("Jupiter", 8, "neutral_sign"): -6,
    ("Saturn", 6, "neutral_sign"): -5,
    ("Saturn", 6, "debilitated"): -8,
    ("Ketu", 5, "neutral_sign"): -4,
    ("Mercury", 10, "debilitated"): -4,
    ("Venus", 10, "exalted"): +6,
    ("Mars", 11, "moolatrikona"): +3,
    ("Sun", 9, "neutral_sign"): +2,
}


def _arc_lengths(poly: list[tuple[float, float]]) -> tuple[list[float], float]:
    if len(poly) < 2:
        return [0.0], 0.0
    cum = [0.0]
    total = 0.0
    for i in range(1, len(poly)):
        dx = poly[i][0] - poly[i - 1][0]
        dy = poly[i][1] - poly[i - 1][1]
        total += math.hypot(dx, dy)
        cum.append(total)
    return cum, total


def _point_at_arc_fraction(poly: list[tuple[float, float]], frac: float) -> tuple[int, int]:
    if not poly:
        return (0, 0)
    frac = max(0.0, min(1.0, frac))
    cum, total = _arc_lengths(poly)
    if total < 1e-6:
        x, y = poly[0]
        return int(x), int(y)
    target = frac * total
    for i in range(1, len(poly)):
        if cum[i] >= target:
            seg = cum[i] - cum[i - 1]
            t = 0.0 if seg < 1e-6 else (target - cum[i - 1]) / seg
            x = poly[i - 1][0] + t * (poly[i][0] - poly[i - 1][0])
            y = poly[i - 1][1] + t * (poly[i][1] - poly[i - 1][1])
            return int(x), int(y)
    x, y = poly[-1]
    return int(x), int(y)


def _nearest_point_on_polyline(
    poly: list[tuple[float, float]], px: float, py: float
) -> tuple[float, float, float]:
    """Return (nx, ny, arc_fraction) for nearest point on polyline."""
    if len(poly) < 2:
        return (px, py, 0.0)
    cum, total = _arc_lengths(poly)
    best_d = 1e18
    best_arc = 0.0
    best_xy = poly[0]
    for i in range(1, len(poly)):
        ax, ay = poly[i - 1]
        bx, by = poly[i]
        abx, aby = bx - ax, by - ay
        ab2 = abx * abx + aby * aby
        if ab2 < 1e-6:
            continue
        t = max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / ab2))
        nx, ny = ax + t * abx, ay + t * aby
        d = (px - nx) ** 2 + (py - ny) ** 2
        if d < best_d:
            best_d = d
            best_xy = (nx, ny)
            best_arc = cum[i - 1] + t * math.sqrt(ab2)
    frac = best_arc / total if total > 1e-6 else 0.0
    return best_xy[0], best_xy[1], frac


def saraswati_age_fractions(
    life_poly: list[tuple[float, float]],
    jup_sat_mid: tuple[float, float] | None = None,
) -> dict[int, float]:
    """
    Map ages (0..80 step 5) to arc fraction along detected life line.
    Age 20 anchored at Jupiter-Saturn perpendicular contact when possible.
    """
    if len(life_poly) < 2:
        return {a: a / SPAN_YEARS for a in range(0, SPAN_YEARS + 1, TICK_INTERVAL)}

    anchor_frac = 0.25
    if jup_sat_mid:
        _, _, anchor_frac = _nearest_point_on_polyline(life_poly, jup_sat_mid[0], jup_sat_mid[1])
        anchor_frac = max(0.08, min(0.55, anchor_frac))

    out: dict[int, float] = {}
    for age in range(0, SPAN_YEARS + 1, TICK_INTERVAL):
        if age <= ANCHOR_AGE_JUP_SAT:
            out[age] = (age / ANCHOR_AGE_JUP_SAT) * anchor_frac if ANCHOR_AGE_JUP_SAT else 0.0
        else:
            tail = SPAN_YEARS - ANCHOR_AGE_JUP_SAT
            t = (age - ANCHOR_AGE_JUP_SAT) / tail if tail else 1.0
            out[age] = anchor_frac + t * (1.0 - anchor_frac)
    return out


def palm_longevity_from_life(
    life_props: dict[str, Any],
    life_poly: list[tuple[float, float]],
) -> dict[str, Any]:
    """Estimate years from life-line reach on 80-year Saraswati scale."""
    if not life_props.get("detected") or len(life_poly) < 2:
        return {
            "palm_years": None,
            "palm_range": None,
            "life_reach": "not_detected",
            "method": "Saraswati 80-year scale - life line not detected on print.",
        }

    length_ratio = float(life_props.get("length_ratio") or 0.0)
    reach = life_props.get("reach", "partial")
    quality = life_props.get("quality", "faint")
    depth = life_props.get("depth", "thin")

    # Endpoint age: full wrist reach ~80; partial scales by arc length
    endpoint_frac = min(1.0, max(0.35, length_ratio * 1.15))
    if reach == "wrist":
        endpoint_frac = max(endpoint_frac, 0.88)
    palm_years = int(round(SPAN_YEARS * endpoint_frac))

    if depth == "thin" or quality == "faint":
        palm_years -= 4
    if depth == "deep" and quality == "clear":
        palm_years += 3

    palm_years = max(45, min(SPAN_YEARS, palm_years))
    margin = 5 if quality == "clear" else 8
    return {
        "palm_years": palm_years,
        "palm_range": [max(40, palm_years - margin), min(SPAN_YEARS, palm_years + margin)],
        "life_reach": reach,
        "life_quality": quality,
        "length_ratio": length_ratio,
        "method": (
            f"Saraswati 80-year scale: life line covers ~{int(endpoint_frac * 100)}% of full arc "
            f"({depth}/{quality}); Jupiter-Saturn perpendicular = age {ANCHOR_AGE_JUP_SAT}."
        ),
    }


def chart_longevity_delta(planets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Sum book chart modifiers for longevity domain."""
    notes: list[str] = []
    total = 0
    for planet, info in planets.items():
        h = int(info.get("house", 0))
        dig = info.get("dignity", "neutral_sign")
        key = (planet, h, dig)
        if key in CHART_YEAR_DELTA:
            d = CHART_YEAR_DELTA[key]
            total += d
            notes.append(f"{planet}@{h} ({dig.replace('_', ' ')}): {d:+d} yr")
        elif planet == "Jupiter" and h == 8:
            total -= 8
            notes.append("Jupiter@8 (8th anchor): -8 yr kalpayu stress per book")
        elif planet == "Saturn" and h in (6, 8, 12):
            total -= 4
            notes.append(f"Saturn@{h} dusthana: -4 yr")

    return {"delta": total, "notes": notes}


def combine_longevity(
    palm: dict[str, Any],
    chart_delta: dict[str, Any],
) -> dict[str, Any]:
    palm_y = palm.get("palm_years")
    if palm_y is None:
        return {
            "estimate_years": None,
            "range_years": None,
            "verdict": "Life line not readable - upload a close-up of thumb base and wrist for Saraswati division.",
            "palm": palm,
            "chart_delta": chart_delta,
        }

    delta = int(chart_delta.get("delta", 0))
    est = max(40, min(SPAN_YEARS, palm_y + delta))
    lo = max(40, est - 7)
    hi = min(SPAN_YEARS, est + 7)
    stress = delta <= -8
    support = delta >= 5

    if stress and est < 68:
        verdict = (
            f"Palm life-line reach suggests ~{palm_y} years on the 80-year scale; "
            f"chart strain (Jupiter@8 debilitated, Saturn dusthana) pulls the confluence to "
            f"~{est} years ({lo}-{hi}). Inspect fate line bars and upper-Mars grille on print."
        )
    elif support:
        verdict = (
            f"Palm reach ~{palm_y} years; Venus exalted / strong Mars in chart adds support ? "
            f"confluence ~{est} years ({lo}-{hi})."
        )
    else:
        verdict = (
            f"Palm life-line division ? ~{palm_y} years; chart modifiers {delta:+d} yr ? "
            f"confluence ~{est} years ({lo}-{hi})."
        )

    return {
        "estimate_years": est,
        "range_years": [lo, hi],
        "palm_base": palm_y,
        "chart_delta": delta,
        "chart_notes": chart_delta.get("notes", []),
        "verdict": verdict,
        "palm": palm,
        "scale_years": SPAN_YEARS,
        "tick_interval": TICK_INTERVAL,
    }


# Head / Heart / Fate cross-check modifiers (years) on the life-line span.
# Book basis (Saraswati 80-year formula, this module's header): "Heart / Head
# lines cross-check; deduct elapsed years from 80." A deep, clear major line
# supports the span; a broken / faint one deducts from it.
LINE_CONFLUENCE_DELTA: dict[str, dict[str, int]] = {
    "head": {"strong": +3, "weak": -3},
    "heart": {"strong": +2, "weak": -2},
    "fate": {"strong": +2, "weak": -2},
}


def _poly_len(poly: list) -> float:
    """Pixel length of a polyline."""
    if not poly or len(poly) < 2:
        return 0.0
    _, total = _arc_lengths([(float(x), float(y)) for x, y in poly])
    return float(total)


def line_confluence_delta(lines: dict[str, Any]) -> dict[str, Any]:
    """
    Head / Heart / Fate cross-check on the life-line span (Saraswati 80-yr rule).
    Returns {"delta": int years, "notes": [...]} to feed into combine_longevity().
    """
    delta = 0
    notes: list[str] = []
    head = lines.get("head") or {}
    heart = lines.get("heart") or {}
    fate = lines.get("fate") or {}

    if head.get("detected"):
        if head.get("depth") == "deep" and head.get("quality") == "clear":
            delta += LINE_CONFLUENCE_DELTA["head"]["strong"]
            notes.append("Head line deep & clear — strong mental stamina supports the span (+3 yr).")
        elif head.get("quality") == "broken":
            delta += LINE_CONFLUENCE_DELTA["head"]["weak"]
            notes.append("Head line broken — spells of mental strain to manage (-3 yr).")
    if heart.get("detected"):
        if heart.get("depth") == "deep" and heart.get("quality") == "clear":
            delta += LINE_CONFLUENCE_DELTA["heart"]["strong"]
            notes.append("Heart line deep & clear — sound emotional and cardiac resilience (+2 yr).")
        elif heart.get("quality") in ("broken", "faint"):
            delta += LINE_CONFLUENCE_DELTA["heart"]["weak"]
            notes.append("Heart line faint or broken — guard the heart and emotional stress (-2 yr).")
    if fate.get("detected"):
        if fate.get("quality") == "clear":
            delta += LINE_CONFLUENCE_DELTA["fate"]["strong"]
            notes.append("Fate line clear & unbroken — a stable, well-supported life path (+2 yr).")
        elif fate.get("quality") == "broken":
            delta += LINE_CONFLUENCE_DELTA["fate"]["weak"]
            notes.append("Fate line broken — a disruptive change of direction to navigate (-2 yr).")
    else:
        notes.append("No strong fate line — a self-directed path rather than carried by circumstance.")

    return {"delta": delta, "notes": notes}


def longevity_confluence(
    feats: dict[str, Any],
    planets: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Full book confluence longevity:
      life-line 80-year base (palm_longevity_from_life)
      + Head/Heart/Fate cross-check (line_confluence_delta)
      + optional chart dignity modifiers (chart_longevity_delta)
      -> combine_longevity().

    `feats` is a palm_api features dict (uses feats['lines'][k] with 'points',
    'detected', 'depth', 'quality', 'reach', 'length_ratio'). Returns the
    combine_longevity() dict plus 'line_notes' and 'line_lengths' (px).
    """
    lines = feats.get("lines") or {}
    life = lines.get("life") or {}
    life_poly = life.get("points") or []

    palm = palm_longevity_from_life(life, life_poly)
    line_cc = line_confluence_delta(lines)
    chart_cc = chart_longevity_delta(planets) if planets else {"delta": 0, "notes": []}

    merged = {
        "delta": int(line_cc["delta"]) + int(chart_cc.get("delta", 0)),
        "notes": list(line_cc["notes"]) + list(chart_cc.get("notes", [])),
    }
    result = combine_longevity(palm, merged)
    result["line_notes"] = line_cc["notes"]
    result["line_lengths"] = {
        k: _poly_len((lines.get(k) or {}).get("points") or [])
        for k in ("life", "head", "heart", "fate")
    }
    return result


def longevity_html(longevity: dict[str, Any]) -> str:
    if not longevity or not longevity.get("estimate_years"):
        return (
            '<div class="section-h">Longevity (Saraswati 80-year formula)</div>'
            '<div class="card amber"><p class="body">'
            f"{longevity.get('verdict', 'Life line not detected - re-upload palm close-up.')}"
            "</p></div>"
        )

    notes = longevity.get("chart_notes") or []
    notes_html = "".join(f"<li>{n}</li>" for n in notes[:6])
    palm_m = longevity.get("palm", {}).get("method", "")
    return f"""
<div class="section-h">Longevity (Saraswati 80-year formula)</div>
<div class="card blue">
  <p class="body"><strong>Confluence estimate:</strong> ~{longevity['estimate_years']} years
  (range {longevity['range_years'][0]}-{longevity['range_years'][1]}).</p>
  <p class="body">{longevity['verdict']}</p>
  <p class="fine"><strong>Palm method:</strong> {palm_m}</p>
  <p class="fine"><strong>Chart modifiers ({longevity.get('chart_delta', 0):+d} yr total):</strong></p>
  <ul class="bullets">{notes_html or '<li>No extra chart delta beyond 8th-Jupiter anchor.</li>'}</ul>
  <p class="fine">Overlay marks: Life (gold) with 5-year ticks; Heart (red), Head (green), Fate (orange).
  Age 20 tick = Jupiter-Saturn perpendicular per book.</p>
</div>
"""
