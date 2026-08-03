#!/usr/bin/env python3
"""Regression: major line dots must sit on correct palm regions (ritz test palms)."""
from __future__ import annotations

from pathlib import Path

from palm_api.analyzer import extract_features

ROOT = Path(__file__).resolve().parents[1]
RIGHT = ROOT / "palmistry" / "ritz_rightpalm.jpg"
LEFT = ROOT / "palmistry" / "ritz_leftpalm.jpg"


def _line_dots(feats: dict) -> dict[str, tuple[float, float]]:
    out: dict[str, tuple[float, float]] = {}
    size = 400.0
    for it in feats["numbered_checklist"]:
        if it.get("kind") == "line":
            out[it["key"]] = (it["x"] / size, it["y"] / size)
    return out


def _assert_line_anatomy(dots: dict[str, tuple[float, float]], fate_x: float = 0.5) -> None:
    """Canonical frame: fingers top, wrist bottom, thumb/Venus mount on the right.

    The life line is the crease bounding the Venus mount: it starts near the
    index web, bulges INTO the palm (toward centre) and curves to the wrist, so
    its midpoint sits near mid-palm (not on the far thumb edge).
    """
    lx, ly = dots["life"]
    fx, fy = dots["fate"]
    hx, hy = dots["head"]
    rx, ry = dots["heart"]
    # Fate runs up the central column.
    assert abs(fx - fate_x) < 0.14, f"fate x={fx:.2f} should be near centre column"
    # Life midpoint sits mid-palm, below the head line, above the wrist.
    assert 0.38 < lx < 0.62, f"life x={lx:.2f} should be mid-palm (Venus boundary)"
    assert 0.55 < ly < 0.80, f"life y={ly:.2f} should be on the thumb-curve (mid palm)"
    # Vertical ordering: heart above head, head above life midpoint.
    assert ry < hy, f"heart ({ry:.2f}) should be above head ({hy:.2f})"
    assert hy < ly, f"head ({hy:.2f}) should be above life midpoint ({ly:.2f})"


def test_ritz_right_palm_lines() -> None:
    feats = extract_features(RIGHT, hand="right")
    dots = _line_dots(feats)
    assert set(dots) >= {"life", "head", "heart", "fate"}
    _assert_line_anatomy(dots)


def test_ritz_left_palm_lines() -> None:
    feats = extract_features(LEFT, hand="left")
    dots = _line_dots(feats)
    assert set(dots) >= {"life", "head", "heart", "fate"}
    _assert_line_anatomy(dots)


if __name__ == "__main__":
    test_ritz_right_palm_lines()
    test_ritz_left_palm_lines()
    print("OK — line markers passed ritz regression checks")
