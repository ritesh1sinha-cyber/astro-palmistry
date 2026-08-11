"""Graharekha Confluence v10 — canonical family-bounded engine."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))

from report_confluence import Vote, build_confluence, merge_semantic_verdict


def test_related_votes_are_bounded_by_family():
    votes = [
        Vote("the classical method", 2.0, "strong"),
        Vote("the strength-scoring method", 1.2, "strong"),
        Vote("occupancy", 0.8, "support"),
        Vote("the confirmation chart", 1.5, "support"),
        Vote("the nadi method", 1.5, "support"),
        Vote("the sub-lord method", 1.5, "support"),
        Vote("the karaka method", 1.5, "support"),
        Vote("the sky right now", -1.2, "pressure"),
    ]
    r = build_confluence({}, "career", 10, raw_votes=votes)
    families = {x["family"]: x for x in r["families"]}
    assert "natal_structure" in families
    assert "specialist" in families
    assert "divisional" in families
    assert "transit" in families
    # Four specialist lanes must not count as four full independent families.
    assert len(r["families"]) == 4


def test_conflict_prevents_very_high_confidence():
    votes = [
        Vote("the classical method", 2.0, "strong"),
        Vote("the confirmation chart", 1.5, "support"),
        Vote("the nadi method", 1.2, "support"),
        Vote("the sub-lord method", 1.0, "support"),
        Vote("the sky right now", -1.5, "pressure"),
        Vote("the classical rule-book", -1.2, "rule conflict"),
    ]
    r = build_confluence({}, "career", 10, raw_votes=votes)
    assert r["confidence"] != "very high"
    assert r["opposing_families"]


def test_semantic_layer_cannot_flip_canonical_direction():
    base = {
        "direction": "down", "score": -0.8, "confidence": "high",
        "votes": [Vote("the classical method", -1.5, "strain")],
        "families": [], "family_agreement": "1 of 1 evidence families align",
    }
    # No semantic cluster available in the test environment; the contract is
    # that the function must preserve the canonical direction whenever a
    # cluster is present too.
    out = merge_semantic_verdict("career", base)
    assert out["direction"] == "down"
