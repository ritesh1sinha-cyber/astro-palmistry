"""
Classical-CV detection of special palmistry marks (signs) on the palm.

Detects, in the canonical (warped) ridge image:
  - cross        (+)  two creases crossing
  - star         (*)  3+ creases through one point
  - grille       (#)  dense cross-hatch of creases
  - triangle     (△)  small closed three-sided figure
  - square       (□)  small closed four-sided figure ("teacher's/protection square")
  - island       (◌)  small closed loop on/near a line
  - fish         (matsya) elongated loop with a tail — auspicious in Indian palmistry
  - trident      (trishul) three-pronged fork at a line ending — auspicious

These are heuristic detectors: thinning the crease map, counting skeleton
branches at junctions, and analysing small closed contours. Confidence is
reported so the report/engine can weight them. Each mark is assigned to the
nearest palmar zone (mount) so book rules can be matched by sign + location.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

# Display label per mount (apollo is read as the Sun mount).
ZONE_LABEL: dict[str, str] = {
    "jupiter": "Jupiter", "saturn": "Saturn", "apollo": "Sun", "mercury": "Mercury",
    "mars": "Mars", "venus": "Venus", "moon": "Moon",
}

# The concrete life-area each mount governs — so a mark on it reads about a real
# part of life, not a vague "depending on the mount".
MOUNT_DOMAIN: dict[str, str] = {
    "jupiter": "your ambition, confidence and standing in life",
    "saturn": "your career, responsibilities and long-term discipline",
    "apollo": "your creativity, reputation and chances of recognition",
    "mercury": "your business sense, communication and money-making",
    "mars": "your courage, drive and ability to bounce back",
    "venus": "your love life, family warmth and vitality",
    "moon": "your imagination, travel and intuition",
}

# Per-mark voice: (display name, concrete clause using {domain}, actionable tail).
MARK_READING: dict[str, tuple[str, str, str]] = {
    "star": ("a star", "a sudden, powerful surge in {domain}; a standout moment that arrives fast", ""),
    "cross": ("a cross", "a real test or obstacle to work through in {domain}",
              " Meet it with patience rather than force, and it turns in your favour."),
    "grille": ("a grille", "energy that scatters in {domain} when you spread yourself too thin",
               " Pick one focus and protect it, and this becomes drive instead of drain."),
    "triangle": ("a triangle", "a genuine talent and sharp judgement in {domain}",
                 " It is a constructive mark — lean on it."),
    "square": ("a square", "a protective shield around {domain} that keeps you safe through rough patches", ""),
    "island": ("an island", "a temporary dip or strain in {domain} for a period",
               " It passes — treat it as a season to rest and consolidate, not a lasting loss."),
    "fish": ("a fish (Matsya)", "a highly auspicious promise of prosperity and good fortune in {domain}", ""),
    "trident": ("a trident (Trishul)", "strongly amplified success and fortune in {domain}",
                " One of the luckiest marks you can carry here."),
}

# Specific (mark, mount) readings that override the generic tone with a concrete,
# book-aligned statement for that exact placement.
ZONE_OVERRIDE: dict[tuple[str, str], str] = {
    ("trident", "apollo"): "it points to lasting fame and real wealth, a standout mark for public success.",
    ("trident", "jupiter"): "it promises leadership honours and success in your ambitions.",
    ("star", "apollo"): "it signals brilliant success or sudden fame in your creative and public life.",
    ("star", "jupiter"): "it marks great ambition fulfilled, a real rise in your standing.",
    ("cross", "jupiter"): "in this position it is a fortunate sign of a meaningful union or marriage, not an obstacle.",
    ("fish", "venus"): "near the thumb it adds lasting family prosperity, comfort and warmth at home.",
    ("triangle", "saturn"): "it shows a sharp aptitude for science, research or the deeper, hidden subjects.",
    ("square", "saturn"): "it protects you against career setbacks, a safety net in your professional life.",
}


def _compose_mark_meaning(mtype: str, zone: str) -> str:
    """A concrete, mount-specific reading for a detected mark (no hedging)."""
    name, clause, tail = MARK_READING.get(
        mtype, (f"a {mtype} mark", "a distinct influence in {domain}", ""))
    mount_lbl = ZONE_LABEL.get(zone, zone.title())
    override = ZONE_OVERRIDE.get((mtype, zone))
    if override:
        return f"On your {mount_lbl} mount you have {name} — {override}"
    domain = MOUNT_DOMAIN.get(zone, "this area of your life")
    return f"On your {mount_lbl} mount you have {name} — {clause.format(domain=domain)}.{tail}"

# Synonyms used to match palmistry-book rules for each sign.
MARK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "cross": ("cross",),
    "star": ("star",),
    "grille": ("grille", "grill", "grid"),
    "triangle": ("triangle",),
    "square": ("square",),
    "island": ("island",),
    "fish": ("fish", "matsya"),
    "trident": ("trident", "trishul", "three-pronged", "tripod"),
}

MARK_TITLE: dict[str, str] = {
    "cross": "Cross sign",
    "star": "Star sign",
    "grille": "Grille sign",
    "triangle": "Triangle sign",
    "square": "Square sign",
    "island": "Island sign",
    "fish": "Fish (Matsya) sign",
    "trident": "Trident (Trishul) sign",
}


def _zone_centers(wpts: np.ndarray) -> dict[str, tuple[float, float]]:
    """Approximate mount centres in canonical pixel coords from landmarks."""
    wrist = wpts[0]

    def below(mcp_idx: int, frac: float = 0.24) -> tuple[float, float]:
        m = wpts[mcp_idx]
        return (float(m[0] + (wrist[0] - m[0]) * frac),
                float(m[1] + (wrist[1] - m[1]) * frac))

    idxs = [0, 5, 9, 13, 17]
    pc = (float(np.mean([wpts[i][0] for i in idxs])),
          float(np.mean([wpts[i][1] for i in idxs])))
    venus = (float((wpts[1][0] + wrist[0]) / 2.0),
             float((wpts[1][1] + wrist[1]) / 2.0))
    moon = (float(2 * pc[0] - venus[0]), venus[1])
    return {
        "jupiter": below(5),
        "saturn": below(9),
        "apollo": below(13),
        "mercury": below(17),
        "mars": pc,
        "venus": venus,
        "moon": moon,
    }


def _branch_count(skb: np.ndarray, cx: int, cy: int, r: int) -> int:
    h, w = skb.shape
    vals: list[int] = []
    for deg in range(0, 360, 6):
        a = np.deg2rad(deg)
        x = int(round(cx + r * np.cos(a)))
        y = int(round(cy + r * np.sin(a)))
        vals.append(1 if (0 <= x < w and 0 <= y < h and skb[y, x]) else 0)
    return sum(1 for i in range(len(vals)) if vals[i] == 1 and vals[i - 1] == 0)


def _cluster_points(pts: np.ndarray, radius: float) -> list[dict[str, Any]]:
    clusters: list[dict[str, Any]] = []
    used = np.zeros(len(pts), dtype=bool)
    for i in range(len(pts)):
        if used[i]:
            continue
        d = np.linalg.norm(pts - pts[i], axis=1)
        idx = np.where(d <= radius)[0]
        used[idx] = True
        c = pts[idx].mean(axis=0)
        clusters.append({"center": (float(c[0]), float(c[1])), "count": int(len(idx))})
    return clusters


def _classify_junction(branches: int, n_junc: int) -> tuple[str | None, float]:
    # A normal palm has many 4-way crease crossings; only flag a sign when the
    # evidence is strong, otherwise the report fills with spurious grilles.
    if n_junc >= 10 and branches >= 4:
        return "grille", 0.55
    if branches >= 6:
        return "star", 0.6
    if branches == 4 and n_junc <= 3:
        return "cross", 0.58
    return None, 0.0


def _assign_zone(
    x: float, y: float, centers: dict[str, tuple[float, float]], max_d: float
) -> str:
    best, bestd = "palm", float("inf")
    for name, (cx, cy) in centers.items():
        d = (x - cx) ** 2 + (y - cy) ** 2
        if d < bestd:
            bestd, best = d, name
    return best if bestd <= max_d * max_d else "palm"


def detect_special_marks(
    ridge_bin: np.ndarray,
    wpts: np.ndarray,
    size: int,
    *,
    max_marks: int = 6,
) -> list[dict[str, Any]]:
    """Return a list of detected special marks in canonical pixel coords."""
    if ridge_bin is None or ridge_bin.size == 0:
        return []
    rb = ridge_bin if ridge_bin.dtype == np.uint8 else ridge_bin.astype(np.uint8)

    try:
        sk = cv2.ximgproc.thinning(rb)
    except Exception:
        sk = rb
    skb = (sk > 0).astype(np.uint8)

    kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], np.uint8)
    nb = cv2.filter2D(skb, -1, kernel, borderType=cv2.BORDER_CONSTANT)
    junc = ((skb == 1) & (nb >= 3)).astype(np.uint8)

    centers = _zone_centers(wpts)
    max_d = size * 0.32
    marks: list[dict[str, Any]] = []

    ys, xs = np.where(junc > 0)
    if len(xs):
        pts = np.column_stack([xs, ys]).astype(np.float32)
        for cl in _cluster_points(pts, radius=max(6.0, size * 0.022)):
            cx, cy = cl["center"]
            branches = _branch_count(skb, int(cx), int(cy), r=max(5, int(size * 0.035)))
            mtype, conf = _classify_junction(branches, cl["count"])
            if mtype:
                marks.append({"type": mtype, "x": cx, "y": cy, "confidence": conf})

    # Closed-contour signs: triangle / square / island / fish.
    cnts, _ = cv2.findContours(rb, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    area_min = (size * size) * 0.0008
    area_max = (size * size) * 0.012
    for c in cnts:
        area = float(cv2.contourArea(c))
        if not (area_min <= area <= area_max):
            continue
        peri = float(cv2.arcLength(c, True))
        if peri <= 1:
            continue
        approx = cv2.approxPolyDP(c, 0.045 * peri, True)
        x, y, bw, bh = cv2.boundingRect(c)
        cx, cy = x + bw / 2.0, y + bh / 2.0
        aspect = max(bw, bh) / max(1.0, float(min(bw, bh)))
        circ = 4 * np.pi * area / (peri * peri)
        v = len(approx)
        mtype: str | None = None
        conf = 0.5
        if v == 3 and circ > 0.25:
            mtype, conf = "triangle", 0.55
        elif v == 4 and aspect < 1.7 and circ > 0.45:
            mtype, conf = "square", 0.5
        elif aspect >= 1.9 and 0.3 < circ < 0.85:
            mtype, conf = "fish", 0.42
        elif circ > 0.62 and aspect < 1.5:
            mtype, conf = "island", 0.5
        if mtype:
            marks.append({"type": mtype, "x": float(cx), "y": float(cy), "confidence": conf})

    # Trident: an endpoint that fans into three short prongs at a line tip.
    endpoints = ((skb == 1) & (nb == 1)).astype(np.uint8)
    eys, exs = np.where(endpoints > 0)
    if len(exs):
        epts = np.column_stack([exs, eys]).astype(np.float32)
        for cl in _cluster_points(epts, radius=max(6.0, size * 0.03)):
            if cl["count"] < 4:
                continue
            cx, cy = cl["center"]
            branches = _branch_count(skb, int(cx), int(cy), r=max(6, int(size * 0.045)))
            if branches == 3:
                marks.append({"type": "trident", "x": cx, "y": cy, "confidence": 0.45})

    for m in marks:
        m["zone"] = _assign_zone(m["x"], m["y"], centers, max_d)

    # Deduplicate: one sign per zone (highest confidence), and no two marks
    # on the same spot.
    marks.sort(key=lambda m: -m["confidence"])
    kept: list[dict[str, Any]] = []
    seen_type_zone: set[tuple[str, str]] = set()
    dedup_r = (size * 0.04) ** 2
    # These "soft" geometric signs are easy to over-detect on a richly-creased
    # palm, so we keep only the single strongest instance of each per hand.
    once_per_hand = {"grille", "trident", "star", "fish", "island"}
    type_count: dict[str, int] = {}
    for m in marks:
        # Marks not clearly seated on a named mount are too ambiguous to report.
        if m["zone"] == "palm":
            continue
        if m["type"] in once_per_hand and type_count.get(m["type"], 0) >= 1:
            continue
        tz = (m["type"], m["zone"])
        if tz in seen_type_zone:
            continue
        if any((m["x"] - k["x"]) ** 2 + (m["y"] - k["y"]) ** 2 < dedup_r for k in kept):
            continue
        type_count[m["type"]] = type_count.get(m["type"], 0) + 1
        seen_type_zone.add(tz)
        kept.append(m)
        if len(kept) >= max_marks:
            break

    for m in kept:
        m["title"] = MARK_TITLE.get(m["type"], m["type"].title())
        m["meaning"] = _compose_mark_meaning(m["type"], m["zone"])
        m["keywords"] = list(MARK_KEYWORDS.get(m["type"], (m["type"],)))
    return kept
