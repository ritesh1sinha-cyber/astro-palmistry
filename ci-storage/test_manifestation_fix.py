"""Graharekha Fix Patch v7 — cohesion merge, evidence gating, composite language."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))

from interpretation.stage_config import (
    cohesion_group_for,
    required_evidence_met,
)
from interpretation.prediction_meaning import PredictionMeaning
from interpretation.manifestation_merger import merge_recognition_candidates
from narration.recognition_renderer import render_from_meaning, recognition_bullets
from narration.recognition_variants import claim_for_manifestation


def meaning(area, manifestation, evidence):
    return PredictionMeaning(
        area=area,
        direction="mixed",
        age_band="adult",
        manifestations=[manifestation],
        narrative_area=area,
        evidence_signature=evidence,
        evidence_trace=[str(evidence)],
        source_engine="manifestation_engine",
        evidence_sources=[evidence],
    )


def test_required_evidence() -> None:
    assert not required_evidence_met("delayed_recognition", 10, "Venus")
    assert not required_evidence_met("delayed_recognition", 10, "Saturn", direction="mixed")
    assert required_evidence_met("delayed_recognition", 10, "Saturn", direction="challenging")
    assert not required_evidence_met("routine", 10, "Rahu")
    assert required_evidence_met("routine", 6, "Saturn")


def test_context_cohesion() -> None:
    assert cohesion_group_for("responsibility", "career") == cohesion_group_for("recognition", "career")
    assert cohesion_group_for("routine", "health") == cohesion_group_for("energy_management", "health")
    assert cohesion_group_for("income", "money") == cohesion_group_for("savings", "money")


def test_composite_language() -> None:
    text = claim_for_manifestation(
        "responsibility", "recognition", "adult", narrative_area="career"
    )
    assert "responsibility increased before recognition" in text

    text = claim_for_manifestation(
        "routine", "energy_management", "adult", narrative_area="health"
    )
    assert "rest, energy and overall wellbeing" in text


def test_same_story_merges() -> None:
    a = meaning("career", "responsibility", (10, "Jupiter"))
    b = meaning("career", "recognition", (10, "Saturn"))
    candidates = [
        {
            "rendered": render_from_meaning(a),
            "why": "evidence A",
            "bullets": recognition_bullets(a),
            "meaning": a,
            "tag": "a",
        },
        {
            "rendered": render_from_meaning(b),
            "why": "evidence B",
            "bullets": recognition_bullets(b),
            "meaning": b,
            "tag": "b",
        },
    ]
    out = merge_recognition_candidates(
        candidates,
        domain="career",
        band="adult",
        render_from_meaning=render_from_meaning,
        recognition_bullets=recognition_bullets,
        seen_text=set(),
        max_claims=2,
    )
    assert len(out) == 1
    assert "responsibility increased before recognition" in out[0][0]


def test_health_does_not_keep_two_wellbeing_claims() -> None:
    a = meaning("health", "routine", (6, "Saturn"))
    b = meaning("health", "energy_management", (1, "Moon"))
    candidates = [
        {
            "rendered": render_from_meaning(a),
            "why": "evidence A",
            "bullets": recognition_bullets(a),
            "meaning": a,
            "tag": "a",
        },
        {
            "rendered": render_from_meaning(b),
            "why": "evidence B",
            "bullets": recognition_bullets(b),
            "meaning": b,
            "tag": "b",
        },
    ]
    out = merge_recognition_candidates(
        candidates,
        domain="health",
        band="adult",
        render_from_meaning=render_from_meaning,
        recognition_bullets=recognition_bullets,
        seen_text=set(),
        max_claims=2,
    )
    assert len(out) == 1


def main() -> int:
    tests = [
        test_required_evidence,
        test_context_cohesion,
        test_composite_language,
        test_same_story_merges,
        test_health_does_not_keep_two_wellbeing_claims,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
