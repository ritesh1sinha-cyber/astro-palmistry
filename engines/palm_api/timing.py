"""
Age / event timing on palm lines.

Sources verified against palmistry_ocr/ (book, page):
- Palmistry for All (Cheiro), p.104: "the most correct way ... is to divide the
  Line of Life into periods of seven years, and also the Line of Fate."
  -> the 7-year (Cheiro) division used for both Life and Fate marks below.
- All the Secrets of Palmistry, p.93-94 (and How to Master, p.33): Life-line age
  landmarks by rays from the Mount of Venus — 63 (Venus->wrist bracelet), 49
  (Venus->percussion), 35 (Venus->little-finger base AND the MIDDLE of the Life
  line), 28, 21; start = age 1, end near wrist = 98. The book's recommended
  expedient: "the middle of the Life Line ... is 35 years" with "more space to
  two spans of seven years each between 21 and 35 ... and less to the rest."
  -> LIFE_AGE_MARKS now anchors 35 at 0.50 (middle), 63 at ~0.72, 98 at 1.0.
- Palmistry: How to Master, p.34: Saturn/Fate line "originates from the wrist
  (Zero) and ends at the base of the middle finger"; landmarks 21 and 35 years.
  -> FATE_AGE_MARKS direction (wrist -> middle finger) and early anchors.
- Easy Understanding of Samudrik, p.270: "Divide the lifeline into 14 equal
  parts ... each part equal to 7 years, last part 9 years, total ~100 years."
  -> the 14-step Life scale ending near 98-100.
- Apprentice to Pro, p.78 & 50 Case Studies, p.20: Vitality line read in
  ten-year sections; breaks "timed chronologically" -> per-segment age hints.
- All the Secrets of Palmistry, p.91: only an APPROXIMATE age can be stated
  (e.g. "between 30 to 32") -> we always return an age_range, never an exact date.

CAVEATS documented in code (not over-claimed):
- Head line timing is debated: Principles of Palmistry, p.56 — "the Head line
  does not follow any time"; How to Master, p.34 — "some palmists mark the Head
  Line at 35 years". HEAD_AGE_MARKS is therefore APPROXIMATE/optional.
- Heart line has no standard age table in these books (marriage is usually timed
  on the marriage/fate line). HEART_AGE_MARKS is a rough affection-timing guide.
"""

from __future__ import annotations

from typing import Any

# (fraction along line from origin → age in years)
# Life: origin = between thumb & index (age 1, upper), end = wrist (age 98).
# CORRECTED to the book-explicit Cheiro expedient — All the Secrets of Palmistry,
# p.93-94: "the middle of the Life Line ... is supposed to be 35 years"; the start
# is age 1 and the end near the wrist is 98; and "more space [is allotted] to two
# spans of seven years each between 21 and 35 ... and less to the rest." So age 35
# sits at the MIDDLE (~0.50), youth (1-35) is stretched, and 35-98 is compressed.
# Venus-ray anchors on the Life line (same pages): 21, 28, 35, 49, 63.
LIFE_AGE_MARKS: tuple[tuple[float, int], ...] = (
    (0.0, 1),
    (0.16, 14),
    (0.34, 21),   # 21–35 given more space (two seven-year spans, book p.94)
    (0.42, 28),
    (0.50, 35),   # middle of the Life line = age 35 (All the Secrets, p.93-94)
    (0.61, 49),
    (0.72, 63),   # Venus→wrist-bracelet ray = 63 (book p.92)
    (0.80, 70),
    (0.87, 77),
    (0.93, 84),
    (0.97, 91),
    (1.0, 98),    # end near wrist = 98 (five 7-yr segments after 63, Cheiro)
)

# Fate / Saturn: origin = wrist (age 1, lower), end = middle-finger base.
# Cheiro's System of Seven (corpus: Secrets of Profession, "Cheiro divides the
# line from 56 ... till the base of the middle finger into 5 equal segments ...
# the last segment ends at age 91"; "the middle of the Line of Saturn represents
# an age of 35 years"). The important phase 21–56 is given more space; the line
# ENDS AT 91 (not 98), and 56→91 are five equal segments near the finger base.
FATE_AGE_MARKS: tuple[tuple[float, int], ...] = (
    (0.0, 1),
    (0.16, 14),
    (0.30, 21),
    (0.42, 28),
    (0.50, 35),   # middle of the Saturn line = age 35 (Cheiro)
    (0.62, 42),
    (0.74, 49),
    (0.86, 56),   # after 56: five equal 7-year segments to the finger base
    (0.888, 63),
    (0.916, 70),
    (0.944, 77),
    (0.972, 84),
    (1.0, 91),    # Saturn line ends at age 91 (Cheiro), not 98
)

# Head: origin = life junction (inner), end = outer palm / Mercury side.
HEAD_AGE_MARKS: tuple[tuple[float, int], ...] = (
    (0.0, 7),
    (0.15, 14),
    (0.28, 21),
    (0.40, 28),
    (0.52, 35),
    (0.64, 42),
    (0.76, 49),
    (0.88, 56),
    (1.0, 63),
)

# Heart: upper edge; timing often for marriage (Venus / heart line intersection).
HEART_AGE_MARKS: tuple[tuple[float, int], ...] = (
    (0.0, 18),
    (0.20, 25),
    (0.40, 32),
    (0.55, 38),
    (0.70, 45),
    (0.85, 52),
    (1.0, 60),
)

LINE_MARKS: dict[str, tuple[tuple[float, int], ...]] = {
    "life": LIFE_AGE_MARKS,
    "fate": FATE_AGE_MARKS,
    "head": HEAD_AGE_MARKS,
    "heart": HEART_AGE_MARKS,
}

METHOD_NOTE: dict[str, str] = {
    "life": (
        "Life line timed start (age 1, between Jupiter and Mars) to wrist (age 98), "
        "with the MIDDLE of the line = age 35 and youth (21–35) given more space "
        "(All the Secrets of Palmistry, p.93–94). Venus-ray anchors 21/28/35/49/63 "
        "(same pages); 7-year division (Palmistry for All / Cheiro, p.104)."
    ),
    "fate": (
        "Saturn/Fate line from the wrist (age 0) up to the middle-finger base; "
        "landmarks 21 & 35 years (How to Master, p.34), 7-year division "
        "(Palmistry for All / Cheiro, p.104)."
    ),
    "head": (
        "APPROXIMATE: head-line timing is debated — Principles of Palmistry, p.56 "
        "('the Head line does not follow any time'); How to Master, p.34 ('some "
        "palmists mark the Head Line at 35 years'). Read here from the life-junction "
        "end outward as a rough guide only."
    ),
    "heart": (
        "APPROXIMATE: no standard heart-line age table in these books (marriage is "
        "usually timed on the marriage/fate line). Used here only as a rough "
        "affection-timing guide along the line."
    ),
}


def _interp_age(progress: float, marks: tuple[tuple[float, int], ...]) -> int:
    p = max(0.0, min(1.0, progress))
    for i in range(len(marks) - 1):
        p0, a0 = marks[i]
        p1, a1 = marks[i + 1]
        if p0 <= p <= p1:
            if p1 <= p0:
                return a0
            t = (p - p0) / (p1 - p0)
            return int(round(a0 + t * (a1 - a0)))
    return marks[-1][1]


def _line_progress(
    line_key: str,
    x: int,
    y: int,
    group: list[dict[str, Any]],
    size: int,
) -> float | None:
    """Calculate true arc-length progress (0.0 to 1.0) along the curved line trajectory."""
    if not group or size <= 0:
        return None
    pts = []
    for s in group:
        mx = float(s.get("mx", 0)) / size
        my = float(s.get("my", 0)) / size
        pts.append((mx, my))

    if len(pts) < 2:
        return None

    # Sort points along the line's natural anatomical direction
    if line_key == "life":
        # Origin = top-inner palm between thumb & index (min y), sweeping around Venus down to wrist (max y)
        pts = sorted(pts, key=lambda p: (p[1], -p[0]))
    elif line_key == "fate":
        # Origin = wrist bottom (max y), moving upward to Saturn mount (min y)
        pts = sorted(pts, key=lambda p: -p[1])
    elif line_key == "head":
        # Origin = inner thumb/index junction (min x if right hand canonical), moving across palm
        pts = sorted(pts, key=lambda p: p[0])
    elif line_key == "heart":
        # Origin = outer percussion beneath pinky, moving inward toward Jupiter/Saturn
        pts = sorted(pts, key=lambda p: p[0])

    # Compute cumulative arc-length distances
    import math
    cum_dist = [0.0]
    for i in range(1, len(pts)):
        d = math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
        cum_dist.append(cum_dist[-1] + d)

    total_len = cum_dist[-1]
    if total_len < 0.04:
        return None

    px, py = float(x) / size, float(y) / size

    # Find the closest projection point onto any line segment
    best_dist_along = 0.0
    min_perp_dist = float("inf")

    for i in range(len(pts) - 1):
        p1, p2 = pts[i], pts[i + 1]
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq < 1e-7:
            t = 0.0
        else:
            t = max(0.0, min(1.0, ((px - p1[0]) * dx + (py - p1[1]) * dy) / seg_len_sq))

        proj_x = p1[0] + t * dx
        proj_y = p1[1] + t * dy
        perp_dist = math.hypot(px - proj_x, py - proj_y)

        if perp_dist < min_perp_dist:
            min_perp_dist = perp_dist
            seg_len = math.sqrt(seg_len_sq)
            best_dist_along = cum_dist[i] + t * seg_len

    progress = best_dist_along / total_len
    return max(0.0, min(1.0, progress))


def _segment_ages(
    line_key: str,
    group: list[dict[str, Any]],
    size: int,
    marks: tuple[tuple[float, int], ...],
) -> list[int]:
    """Approximate age at each ridge segment midpoint (for break / event hints)."""
    if len(group) < 2:
        return []
    keyed = sorted(group, key=lambda s: s["my"] if line_key in ("life", "fate") else s["mx"])
    if line_key == "fate":
        keyed = list(reversed(keyed))
    ages: list[int] = []
    for s in keyed:
        prog = _line_progress(line_key, int(s["mx"]), int(s["my"]), group, size)
        if prog is not None:
            ages.append(_interp_age(prog, marks))
    return ages


def estimate_point_timing(
    line_key: str,
    x: int | None,
    y: int | None,
    group: list[dict[str, Any]],
    size: int,
    *,
    segment_count: int | None = None,
) -> dict[str, Any] | None:
    marks = LINE_MARKS.get(line_key)
    if not marks or x is None or y is None:
        return None
    progress = _line_progress(line_key, x, y, group, size)
    if progress is None:
        return None
    age = _interp_age(progress, marks)
    
    # 3-5 year window representing life chapter
    window_low = max(1, age - 2)
    window_high = min(90, age + 2)

    seg_ages = _segment_ages(line_key, group, size, marks)
    seg_note = ""
    if seg_ages and segment_count and segment_count > 1:
        lo, hi = min(seg_ages), max(seg_ages)
        seg_note = (
            f" Ridge analysis shows ~{segment_count} segments along this line "
            f"(approx. ages {lo}–{hi} by position)."
        )

    return {
        "estimated_age": age,
        "age_range": [window_low, window_high],
        "progress_pct": float(round(progress * 100, 1)),
        "system": "cheiro_system_of_seven" if line_key in ("life", "fate") else "approximate_non_cheiro",
        "method": METHOD_NOTE.get(line_key, ""),
        "summary": (
            f"Your {line_key.replace('_', ' ')} line in this sector ≈ ages {window_low}–{window_high} "
            f"(~{round(progress * 100)}% along the line arc).{seg_note}"
        ),
    }


def timing_rules_from_corpus(
    corpus: dict[str, Any],
    line_key: str,
    *,
    limit: int = 2,
) -> list[dict[str, Any]]:
    """Book passages that mention timing on this line type."""
    cat_map = {"life": "vitality", "fate": "career", "head": "mind", "heart": "heart"}
    cat = cat_map.get(line_key)
    if not cat:
        return []
    line_words = {
        "life": ("life line", "vitality line", "line of life"),
        "fate": ("fate line", "saturn", "line of saturn", "luck line"),
        "head": ("head line", "mental line"),
        "heart": ("heart line", "marriage"),
    }
    words = line_words.get(line_key, ())
    out: list[tuple[float, dict[str, Any]]] = []
    for rule in corpus.get("rules", []):
        if rule.get("category") != cat and line_key != "fate":
            continue
        kws = rule.get("keywords") or []
        text = (rule.get("text") or "").lower()
        if "timing" not in kws and "timing" not in text and "year" not in text:
            if not any(w in text for w in ("age", "seven", "segment", "ten-year", "chronolog")):
                continue
        if words and not any(w in text for w in words):
            if line_key == "fate" and "saturn" not in text and "fate" not in text:
                continue
        score = 1.0
        if "timing" in kws:
            score += 2.0
        if "seven" in text or "7 year" in text or "7-year" in text:
            score += 1.0
        out.append((score, rule))
    out.sort(key=lambda x: -x[0])
    result = []
    for _, rule in out[:limit]:
        result.append(
            {
                "text": rule.get("text", ""),
                "book": rule.get("book"),
                "page": rule.get("page"),
                "score": round(rule.get("score", 0) or 0, 2),
            }
        )
    return result
