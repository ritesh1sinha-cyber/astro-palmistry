#!/usr/bin/env python3
"""Unit coverage for the early-path head/life join classifier."""

from __future__ import annotations

import sys
from pathlib import Path

_ENGINES = Path(__file__).resolve().parents[1]  # .../engines
sys.path.insert(0, str(_ENGINES))

from palm_api.analyzer import _head_life_relation  # noqa: E402


def _poly(points):
    return [(float(x), float(y)) for x, y in points]


def test_merged_when_early_path_rides_with_life() -> None:
    # Life curves down the thumb side; head starts on the same crease then
    # peels away — the classic joined origin that a single-endpoint check misses.
    life = _poly([(80, 40), (78, 70), (76, 100), (74, 140), (80, 200), (90, 260)])
    head = _poly([(81, 42), (79, 68), (90, 95), (130, 110), (200, 120), (280, 125)])
    assert _head_life_relation(head, life, 400) == "merged"


def test_separated_when_origin_gap_is_clear() -> None:
    life = _poly([(80, 40), (78, 70), (76, 100), (74, 140), (80, 200)])
    # ~24px from life at start (0.06 of 400) — clear gap, not a wide one.
    head = _poly([(104, 48), (140, 70), (200, 90), (260, 105), (320, 115)])
    assert _head_life_relation(head, life, 400) == "separated"


def test_separated_wide_for_large_gap() -> None:
    life = _poly([(80, 40), (78, 70), (76, 100), (74, 140)])
    head = _poly([(220, 60), (260, 75), (320, 90)])
    assert _head_life_relation(head, life, 400) == "separated_wide"


def test_orients_reversed_head_polyline() -> None:
    life = _poly([(80, 40), (78, 70), (76, 100), (74, 140), (80, 200)])
    head_forward = _poly([(81, 42), (79, 68), (90, 95), (130, 110), (200, 120)])
    head_reversed = list(reversed(head_forward))
    assert _head_life_relation(head_forward, life, 400) == "merged"
    assert _head_life_relation(head_reversed, life, 400) == "merged"


if __name__ == "__main__":
    test_merged_when_early_path_rides_with_life()
    test_separated_when_origin_gap_is_clear()
    test_separated_wide_for_large_gap()
    test_orients_reversed_head_polyline()
    print("OK — head/life relation tests passed")
