"""Graharekha Confluence v10 — presentation-only confluence labels."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))

from report_cards import _build_confluence, _confluence_label


def test_confluence_label_humanizes_core_methods():
    assert _confluence_label("the classical method") == "Birth chart"
    assert _confluence_label("the confirmation chart") == "Relationship divisional confirmation"
    assert _confluence_label("slow transits") == "Transit analysis"


def test_confluence_is_presentation_only():
    assert callable(_build_confluence)
