"""Graharekha v8 — domain-correct bullets, tag semantics, Saturn delay gating."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))

from interpretation.stage_config import evidence_atoms, required_evidence_met
from interpretation.rubric_validator import RubricInput, validate_rubric
from interpretation.prediction_meaning import build_recognition_meaning
from narration.recognition_variants import bullets_for_meaning


def test_saturn_is_not_automatic_delay() -> None:
    assert "delay_indicator" not in evidence_atoms(10, "Saturn", direction="mixed")
    assert not required_evidence_met("delayed_recognition", 10, "Saturn", direction="mixed")
    assert required_evidence_met("delayed_recognition", 10, "Saturn", direction="challenging")


def test_money_bullets_do_not_use_career_language() -> None:
    m = build_recognition_meaning("money", "money_earn", "adult")
    assert m is not None
    bullets = bullets_for_meaning(m)
    assert "greater responsibility before reward" not in bullets
    assert any("income" in b or "financial" in b or "earning" in b for b in bullets)


def test_network_bullets_are_network_specific() -> None:
    m = build_recognition_meaning("career", "career_vouched", "adult")
    assert m is not None
    bullets = bullets_for_meaning(m)
    assert any(
        "contact" in b or "network" in b or "introduction" in b or "professional" in b
        for b in bullets
    )


def test_tag_changes_candidate_selection() -> None:
    a = validate_rubric(RubricInput(
        house=10, planet="Saturn", age=35, age_band="adult", area="career",
        direction="mixed", recognition_tag="career_vouched",
    ))
    assert a.primary_id in {
        "mentor_support", "support_from_contacts", "career_network", "recognition",
    }


def test_health_requires_health_house() -> None:
    assert not required_evidence_met("routine", 10, "Saturn")
    assert required_evidence_met("routine", 6, "Saturn")


def main() -> int:
    tests = [
        test_saturn_is_not_automatic_delay,
        test_money_bullets_do_not_use_career_language,
        test_network_bullets_are_network_specific,
        test_tag_changes_candidate_selection,
        test_health_requires_health_house,
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
