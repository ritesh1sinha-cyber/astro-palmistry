"""Graharekha Palm Core Human-Correlation v2 — production renderer."""
from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "core" / "palm_cards.py"


def test_palm_cards_compiles():
    py_compile.compile(str(MODULE), doraise=True)


def test_human_correlation_renderer_present():
    text = MODULE.read_text(encoding="utf-8")
    assert "You may recognize this as" in text
    assert "Why Graharekha says this" in text
    assert "5 things you may recognize about yourself" in text
    assert "What these signs may look like in your life" in text
    assert "What may have changed with age" in text
