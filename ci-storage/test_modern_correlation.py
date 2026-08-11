"""Graharekha Palm Human-Correlation v1 — modern meaning layer."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines"))
sys.path.insert(0, str(ROOT))

from palm_api.life_aspects import build_life_aspects
from palm_api.pipeline import _render_life_aspects


def _features():
    return {
        "morphology": {
            "hand_type": "air",
            "thumb": {"length": "short", "opening": "narrow"},
            "index_vs_ring": "ring_longer",
        },
        "lines": {
            "life": {"detected": True, "depth": "deep", "sweep": "wide"},
            "head": {"detected": True, "start_relation": "merged", "direction": "straight", "depth": "deep"},
            "heart": {"detected": True, "depth": "medium", "start_zone": "saturn"},
            "fate": {"detected": True, "quality": "clear", "reach": "saturn"},
        },
        "mounts": {
            "jupiter": "moderate", "saturn": "prominent", "apollo": "moderate",
            "mercury": "prominent", "venus": "prominent", "mars": "moderate", "moon": "prominent",
        },
        "minor_lines": {
            "sun": {"detected": True}, "mercury": {"detected": True},
            "travel": {"detected": True}, "ring_of_solomon": {"detected": True},
            "marriage": {"detected": True},
        },
        "special_marks": [
            {"type": "trident", "zone": "venus"},
            {"type": "star", "zone": "saturn"},
        ],
    }


def _analysis():
    f = _features()
    return {"right": {"features": f}, "left": {"features": f}}


def test_modern_layer_has_life_recognition():
    rows = build_life_aspects(_analysis(), "right")
    assert rows
    career = next(r for r in rows if r["key"] == "career")
    assert career["recognize"]
    assert any("responsibility" in x.lower() or "experience" in x.lower() for x in career["recognize"])


def test_health_uses_non_medical_human_language():
    rows = build_life_aspects(_analysis(), "right")
    health = next(r for r in rows if r["key"] == "health")
    text = health["what_it_means"].lower()
    assert "illness has a hard time" not in text
    assert "routine" in text or "energy" in text or "recovery" in text


def test_same_family_is_not_rendered_twice():
    rows = build_life_aspects(_analysis(), "right")
    love = next(r for r in rows if r["key"] == "love")
    families = [p["family"] for p in love["points"]]
    assert len(families) == len(set(families))


def test_html_contains_recognition_and_collapsed_evidence():
    rows = build_life_aspects(_analysis(), "right")
    html = _render_life_aspects(rows)
    assert "Does this sound like you?" in html
    assert "You may recognize this as" in html
    assert "Why Graharekha says this" in html
    assert "technical-evidence" in html
