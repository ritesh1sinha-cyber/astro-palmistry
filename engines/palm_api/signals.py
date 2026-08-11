"""Stable palm signal IDs derived from canonical measurements."""

from __future__ import annotations

from typing import Any


def _sig(signal_id: str, hand: str, *, strength: float, confidence: float, source: str) -> dict:
    return {
        "signal_id": signal_id,
        "hand": hand,
        "strength": round(strength, 3),
        "confidence": round(confidence, 3),
        "source": source,
    }


def build_signals(measurements: dict[str, Any]) -> list[dict]:
    hand = str(measurements.get("hand") or "unknown")
    signals: list[dict] = []

    ht = str(measurements.get("hand_type") or "")
    if ht and ht != "unknown":
        signals.append(_sig(f"HAND_{ht.upper()}", hand, strength=0.8, confidence=0.85, source="hand_type"))

    ratios = measurements.get("finger_ratios") or {}
    ivr = ratios.get("index_vs_ring")
    if ivr == "index_longer":
        signals.append(_sig("FINGER_INDEX_LONGER_RING", hand, strength=0.75, confidence=0.9, source="finger_ratios"))
    elif ivr == "ring_longer":
        signals.append(_sig("FINGER_RING_LONGER_INDEX", hand, strength=0.75, confidence=0.9, source="finger_ratios"))

    thumb = ratios.get("thumb_length")
    if thumb == "short":
        signals.append(_sig("THUMB_SHORT", hand, strength=0.65, confidence=0.8, source="thumb"))
    elif thumb == "long":
        signals.append(_sig("THUMB_LONG", hand, strength=0.65, confidence=0.8, source="thumb"))

    for key, props in (measurements.get("lines") or {}).items():
        strength = float(props.get("strength") or 0)
        if strength < 0.45:
            continue
        sid = f"{key.upper()}_LINE_STRONG"
        if props.get("start_relation") == "joined" and key == "head":
            signals.append(_sig("HEAD_LINE_JOINED_START", hand, strength=strength, confidence=0.88, source="head_line"))
        if props.get("continuity") in ("even", "clean", "clear") or props.get("quality") == "clear":
            sid = f"{key.upper()}_LINE_CLEAN"
        signals.append(_sig(sid, hand, strength=strength, confidence=0.85, source=f"{key}_line"))

    for mount, props in (measurements.get("mounts") or {}).items():
        level = str(props.get("level") or "")
        strength = float(props.get("strength") or 0)
        if level == "prominent" or strength >= 0.7:
            signals.append(_sig(
                f"{mount.upper()}_MOUNT_STRONG",
                hand,
                strength=max(strength, 0.7),
                confidence=0.82,
                source="mounts",
            ))

    for mark in measurements.get("marks") or []:
        mtype = str(mark.get("type") or "").upper()
        mount = str(mark.get("mount") or "unknown").upper()
        if not mtype:
            continue
        signals.append(_sig(
            f"{mtype}_ON_{mount}",
            hand,
            strength=float(mark.get("confidence") or 0.7),
            confidence=float(mark.get("confidence") or 0.7),
            source="special_marks",
        ))

    return signals
