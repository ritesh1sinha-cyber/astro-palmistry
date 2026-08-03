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
    if not group or size <= 0:
        return None
    xs = [s["mx"] / size for s in group]
    ys = [s["my"] / size for s in group]
    px, py = x / size, y / size

    if line_key == "life":
        y0, y1 = min(ys), max(ys)
        if y1 - y0 < 0.08:
            return None
        return (py - y0) / (y1 - y0)
    if line_key == "fate":
        y0, y1 = max(ys), min(ys)  # wrist → finger
        if y0 - y1 < 0.08:
            return None
        return (y0 - py) / (y0 - y1)
    if line_key in ("head", "heart"):
        x0, x1 = min(xs), max(xs)
        if x1 - x0 < 0.08:
            return None
        return (px - x0) / (x1 - x0)
    return None


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
    lower, upper = 1, 98
    for _p, a in marks:
        if a <= age:
            lower = a
    for _p, a in marks:
        if a >= age:
            upper = a
            break
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
        "age_range": [max(1, lower), min(98, upper if upper >= lower else age + 7)],
        "progress_pct": float(round(progress * 100, 1)),
        "system": "cheiro_system_of_seven" if line_key in ("life", "fate") else "approximate_non_cheiro",
        "method": METHOD_NOTE.get(line_key, ""),
        "summary": (
            f"Your {line_key.replace('_', ' ')} line at this circle ≈ age {age} "
            f"(~{round(progress * 100)}% along your line).{seg_note}"
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
