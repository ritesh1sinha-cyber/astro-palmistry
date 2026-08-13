from __future__ import annotations

from pathlib import Path
import sys

_HERE = Path(__file__).resolve()
_ASTRO = _HERE.parents[1]
_ROOT = _HERE.parents[3]
for p in (_ROOT, _ASTRO, _ROOT / "engines"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from core.palm_cards import _filter_customer_numbered
from daily_moon_prediction import _ordinal_suffix


def test_fair_photo_hard_blocks_special_mark_numbered_points():
    hand = {
        "features": {"quality": {"grade": "good", "special_marks_allowed": True}},
        "measurement_quality": {"photo_grade": "fair", "special_marks_allowed": False},
        "numbered_checklist": [
            {"num": 17, "title": "Trident (Trishul) sign", "finding": "leadership"},
            {"num": 18, "title": "Your overall hand shape", "finding": "Air type"},
        ],
    }
    out = _filter_customer_numbered(hand)
    assert [x["num"] for x in out] == [18]


def test_workings_respects_reading_level_measurement_gate():
    from core.palm_cards import _workings
    raw = {
        "reading_result": {
            "measurement_quality": {"photo_grade": "fair", "special_marks_allowed": False},
        },
        "right": {
            "features": {"quality": {"grade": "good", "special_marks_allowed": True}},
            "numbered_checklist": [
                {"num": 17, "title": "Trident (Trishul) sign",
                 "finding": "leadership", "conclusive": {"verdict": "leadership"}},
                {"num": 18, "title": "Your overall hand shape",
                 "finding": "Air type", "conclusive": {"verdict": "Air type"}},
            ],
        },
        "left": {},
    }
    html = _workings(raw)
    assert "Trident" not in html and "Trishul" not in html
    assert "Point 18" in html


def test_ordinal_suffix_is_correct():
    assert _ordinal_suffix(1) == "st"
    assert _ordinal_suffix(2) == "nd"
    assert _ordinal_suffix(3) == "rd"
    assert _ordinal_suffix(4) == "th"
    assert _ordinal_suffix(12) == "th"
    assert _ordinal_suffix(22) == "nd"
