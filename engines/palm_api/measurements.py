"""Canonical palm measurements — single source of truth per hand."""

from __future__ import annotations

from typing import Any


def _line_strength_score(props: dict[str, Any]) -> float:
    if not props or not props.get("detected"):
        return 0.0
    depth = str(props.get("depth") or "medium")
    quality = str(props.get("quality") or "clear")
    depth_map = {"thin": 0.35, "faint": 0.35, "medium": 0.6, "deep": 0.85}
    qual_map = {"broken": 0.3, "faint": 0.4, "clear": 0.75, "even": 0.8}
    return round(min(1.0, depth_map.get(depth, 0.5) * 0.6 + qual_map.get(quality, 0.5) * 0.4), 3)


def _mount_strength_score(level: str) -> float:
    return {"flat": 0.3, "moderate": 0.55, "prominent": 0.85, "unknown": 0.0}.get(
        str(level or "unknown"), 0.0)


def _derive_index_vs_ring(fingers: dict[str, dict[str, Any]]) -> str:
    idx = (fingers.get("index") or {}).get("ratio_to_middle")
    ring = (fingers.get("ring") or {}).get("ratio_to_middle")
    if idx is None or ring is None:
        return "unknown"
    if idx > ring * 1.03:
        return "index_longer"
    if ring > idx * 1.03:
        return "ring_longer"
    return "equal"


def _consistent_finger_classes(
    fingers: dict[str, dict[str, Any]],
    index_vs_ring: str,
) -> dict[str, dict[str, Any]]:
    """Ensure index/ring prose cannot contradict index_vs_ring."""
    out: dict[str, dict[str, Any]] = {}
    for name, data in (fingers or {}).items():
        row = dict(data or {})
        if name in ("index", "ring"):
            if index_vs_ring == "index_longer":
                row["comparison_role"] = "index_leads" if name == "index" else "ring_follows"
            elif index_vs_ring == "ring_longer":
                row["comparison_role"] = "ring_leads" if name == "ring" else "index_follows"
            else:
                row["comparison_role"] = "balanced"
            # Do not emit standalone short/long for index/ring when comparison exists.
            row["length_class"] = row.get("length_class") or "average"
            row["describe_by"] = "index_vs_ring"
        else:
            row["describe_by"] = "middle_ratio"
        out[name] = row
    return out


def build_measurements(features: dict[str, Any], hand: str) -> dict[str, Any]:
    """Build canonical measurement object from analyzer features."""
    morph = dict(features.get("morphology") or {})
    fingers_raw = dict(morph.get("fingers") or features.get("fingers") or {})
    index_vs_ring = morph.get("index_vs_ring") or _derive_index_vs_ring(fingers_raw)
    if index_vs_ring == "unknown":
        index_vs_ring = _derive_index_vs_ring(fingers_raw)

    fingers = _consistent_finger_classes(fingers_raw, str(index_vs_ring))

    lines: dict[str, Any] = {}
    for key in ("life", "head", "heart", "fate"):
        props = dict((features.get("lines") or {}).get(key) or {})
        lines[key] = {
            **props,
            "strength": _line_strength_score(props),
        }

    mounts: dict[str, Any] = {}
    for key, level in (features.get("mounts") or {}).items():
        mounts[key] = {
            "strength": _mount_strength_score(str(level)),
            "level": str(level),
        }

    marks = []
    seen = set()
    for mark in features.get("special_marks") or []:
        mtype = str(mark.get("type") or "")
        zone = str(mark.get("zone") or mark.get("mount") or "")
        key = (mtype, zone)
        if key in seen:
            continue
        seen.add(key)
        marks.append({
            "type": mtype,
            "mount": zone,
            "confidence": float(mark.get("confidence") or 0.7),
        })

    return {
        "hand": hand,
        "hand_type": morph.get("hand_type") or "unknown",
        "dominant": bool(features.get("dominant")),
        "finger_ratios": {
            "index_vs_ring": index_vs_ring,
            "middle_vs_ring": _finger_vs_middle(fingers_raw, "ring"),
            "thumb_length": (morph.get("thumb") or {}).get("length") or "medium",
        },
        "fingers": fingers,
        "lines": lines,
        "mounts": mounts,
        "marks": marks,
        "quality": dict(features.get("quality") or {}),
    }


def _finger_vs_middle(fingers: dict, name: str) -> str:
    data = fingers.get(name) or {}
    lc = str(data.get("length_class") or "average")
    if lc in ("long", "short", "average"):
        return f"{name}_{lc}_vs_middle"
    return "unknown"


def line_strength_score(props: dict[str, Any]) -> int:
    """Shared int rank for confluence and UI bars."""
    score = _line_strength_score(props)
    if score >= 0.75:
        return 3
    if score >= 0.5:
        return 2
    if score > 0:
        return 1
    return 0


def mount_strength_rank(level: str) -> int:
    return {"flat": 1, "moderate": 2, "prominent": 3, "unknown": 0}.get(str(level), 0)
