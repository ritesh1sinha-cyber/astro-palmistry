"""Palm canonical architecture regression tests."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "palm_api"))
sys.path.insert(0, str(ROOT / "engines"))
sys.path.insert(0, str(ROOT))

from palm_api.measurements import build_measurements
from palm_api.reading_result import build_reading_result
from palm_api.signals import build_signals
from palm_api.validate_palm_result import validate_palm_result


def _sample_features(index_vs_ring: str = "index_longer") -> dict:
    return {
        "morphology": {
            "hand_type": "air",
            "index_vs_ring": index_vs_ring,
            "fingers": {
                "index": {"length_class": "long", "ratio_to_middle": 1.08},
                "middle": {"length_class": "reference", "ratio_to_middle": 1.0},
                "ring": {"length_class": "short", "ratio_to_middle": 0.88},
                "pinky": {"length_class": "average", "ratio_to_middle": 0.95},
            },
            "thumb": {"length": "medium"},
        },
        "lines": {
            "life": {"detected": True, "depth": "medium", "quality": "clear"},
            "head": {"detected": True, "depth": "deep", "quality": "clear", "start_relation": "joined"},
            "heart": {"detected": True, "depth": "medium", "quality": "clear"},
            "fate": {"detected": True, "depth": "deep", "quality": "clear"},
        },
        "mounts": {
            "jupiter": "moderate",
            "saturn": "moderate",
            "apollo": "prominent",
            "mercury": "prominent",
        },
        "special_marks": [
            {"type": "grille", "zone": "jupiter", "confidence": 0.88},
        ],
        "quality": {"grade": "fair"},
    }


def test_measurements_single_index_vs_ring():
    meas = build_measurements(_sample_features("index_longer"), "right")
    assert meas["finger_ratios"]["index_vs_ring"] == "index_longer"


def test_signals_have_stable_ids():
    meas = build_measurements(_sample_features(), "right")
    signals = build_signals(meas)
    ids = {s["signal_id"] for s in signals}
    assert "HAND_AIR" in ids
    assert "FINGER_INDEX_LONGER_RING" in ids


def test_finger_contradiction_regression():
    html = (
        "Your index (Jupiter) finger is longer than your ring finger — ambition."
    )
    result = build_reading_result({
        "right": {"features": _sample_features("index_longer")},
        "left": {"features": _sample_features("index_longer")},
        "confluence": {"life_aspects": [], "predictions": []},
    })
    bad = validate_palm_result(result, html=(
        html + " Your ring (Apollo) finger is longer than your index finger."
    ))
    assert not bad["ok"]


def test_reading_result_schema():
    raw = {
        "right": {"features": _sample_features()},
        "left": {"features": _sample_features()},
        "confluence": {"life_aspects": [], "predictions": []},
    }
    result = build_reading_result(raw)
    assert "canonical_signals" in result
    assert "confluences" in result
    assert isinstance(result["measurements"], dict)
