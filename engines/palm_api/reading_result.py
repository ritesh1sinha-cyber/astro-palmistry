"""Build the canonical palm reading_result object."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from palm_api.measurements import build_measurements
from palm_api.signals import build_signals

_LOOKUP_PATH = Path(__file__).resolve().parent / "data" / "palm_master_lookup.json"

_SIGNAL_FAMILIES: dict[str, str] = {
    "HAND_AIR": "COMMUNICATION_FAMILY",
    "HAND_WATER": "EMOTION_FAMILY",
    "HAND_FIRE": "CREATIVITY_FAMILY",
    "HAND_EARTH": "DISCIPLINE_FAMILY",
    "MERCURY_MOUNT_STRONG": "COMMUNICATION_FAMILY",
    "HEAD_LINE_STRONG": "COMMUNICATION_FAMILY",
    "HEAD_LINE_CLEAN": "COMMUNICATION_FAMILY",
    "HEAD_LINE_JOINED_START": "DISCIPLINE_FAMILY",
    "FATE_LINE_CLEAR": "CAREER_FAMILY",
    "FATE_LINE_STRONG": "CAREER_FAMILY",
    "APOLLO_MOUNT_STRONG": "CREATIVITY_FAMILY",
    "JUPITER_MOUNT_STRONG": "CAREER_FAMILY",
    "FINGER_INDEX_LONGER_RING": "CAREER_FAMILY",
    "FINGER_RING_LONGER_INDEX": "CREATIVITY_FAMILY",
    "GRILLE_ON_JUPITER": "CAREER_FAMILY",
}


def _load_lookup() -> list[dict]:
    if not _LOOKUP_PATH.is_file():
        return []
    return json.loads(_LOOKUP_PATH.read_text(encoding="utf-8"))


def _signal_ids(all_signals: list[dict]) -> set[str]:
    return {str(s.get("signal_id") or "") for s in all_signals}


def _score_entry(entry: dict, present: set[str], *, both_hands: set[str]) -> tuple[int, list[str]]:
    score = 0
    matched: list[str] = []
    for sid in entry.get("required_signals") or []:
        if sid not in present:
            return 0, []
        score += 3
        matched.append(sid)
    for sid in entry.get("supporting_signals") or []:
        if sid in present:
            score += 2 if sid in both_hands else 1
            matched.append(sid)
    for sid in entry.get("contradicting_signals") or []:
        if sid in present:
            score -= 2
    families_seen: set[str] = set()
    effective = 0
    for sid in matched:
        fam = _SIGNAL_FAMILIES.get(sid, sid)
        if fam in families_seen:
            continue
        families_seen.add(fam)
        effective += 3 if sid in (entry.get("required_signals") or []) else 1
    return max(score, effective), matched


def _strength_label(score: int, minimum: int) -> str:
    if score < minimum:
        return "weak"
    if score <= 6:
        return "emerging"
    if score <= 9:
        return "moderate"
    if score <= 12:
        return "strong"
    return "very strong"


def build_domain_confluences(all_signals: list[dict]) -> list[dict]:
    present = _signal_ids(all_signals)
    both = {
        sid for sid in present
        if sum(1 for s in all_signals if s.get("signal_id") == sid) >= 2
    }
    out: list[dict] = []
    for entry in _load_lookup():
        score, evidence = _score_entry(entry, present, both_hands=both)
        minimum = int(entry.get("minimum_score") or 7)
        if score < minimum:
            continue
        templates = entry.get("templates") or []
        text = templates[0] if templates else entry.get("modern_meaning", "")
        out.append({
            "id": entry.get("confluence_id"),
            "domain": entry.get("domain"),
            "strength": _strength_label(score, minimum),
            "confidence": min(0.95, 0.55 + score * 0.03),
            "human_interpretation": text,
            "manifestations": list(entry.get("modern_manifestations") or [])[:4],
            "evidence": evidence,
            "score": score,
        })
    out.sort(key=lambda x: x.get("score", 0), reverse=True)
    return out[:8]


def build_reading_result(
    raw: dict[str, Any],
    *,
    person: Optional[dict] = None,
    active_hand: str = "right",
) -> dict[str, Any]:
    """Canonical result consumed by free and paid renderers."""
    measurements_by_hand: dict[str, Any] = {}
    all_signals: list[dict] = []
    for side in ("left", "right"):
        block = raw.get(side) or {}
        feats = block.get("features") or {}
        if not feats:
            continue
        meas = build_measurements(feats, side)
        measurements_by_hand[side] = meas
        all_signals.extend(build_signals(meas))

    confluences = build_domain_confluences(all_signals)
    conf_block = raw.get("confluence") or {}

    past_validation = []
    present = []
    future_windows = []
    for item in (conf_block.get("predictions") or [])[:6]:
        age = item.get("age")
        if age is None:
            present.append(item)
            continue
        future_windows.append({
            "age_window": item.get("age_range") or [max(1, int(age) - 3), int(age) + 3],
            "domain": item.get("domain", "life"),
            "pattern": item.get("text", ""),
            "confidence": "moderate",
        })

    return {
        "person": person or {},
        "measurement_quality": {
            "photo_grade": (measurements_by_hand.get(active_hand) or {})
            .get("quality", {}).get("grade", "fair"),
            "confidence": 0.78,
        },
        "measurements": measurements_by_hand,
        "canonical_signals": all_signals,
        "confluences": confluences,
        "past_validation": past_validation,
        "present": present or (conf_block.get("life_aspects") or [])[:3],
        "future_windows": future_windows,
        "special_marks": [
            m for meas in measurements_by_hand.values()
            for m in (meas.get("marks") or [])
        ],
        "remedies": raw.get("remedies") or [],
        "legacy_confluence": conf_block,
    }
