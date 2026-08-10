"""Rubric matrix tests — 12×9×6 base combos × 3 directions (structured, no HTML)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))

from interpretation.rubric_validator import RubricInput, validate_rubric, PLANETS, BANDS
from interpretation.stage_config import adult_only_manifestations, validate_age_manifestation

HOUSES = list(range(1, 13))
DIRECTIONS = ("up", "mixed", "down")
MAJOR_AREAS = {2: "money", 4: "home", 5: "children", 7: "love", 10: "career", 11: "money", 12: "inner"}


def _area_for_house(h: int) -> str:
    return MAJOR_AREAS.get(h, "career")


def test_matrix_primary_age_compatible() -> None:
    """Every combo produces an age-compatible primary manifestation."""
    failures = []
    for house in HOUSES:
        for planet in PLANETS:
            for band in BANDS:
                for direction in DIRECTIONS:
                    inp = RubricInput(
                        house=house,
                        planet=planet,
                        age_band=band,
                        area=_area_for_house(house),
                        direction=direction,
                        dasha_planet=planet,
                    )
                    result = validate_rubric(inp)
                    if not result.primary_id:
                        failures.append(f"{house}:{planet}:{band}:{direction}:no_primary")
                        continue
                    gate = validate_age_manifestation(band, result.primary_id)
                    if not gate["allowed"]:
                        failures.append(
                            f"{house}:{planet}:{band}:{direction}:blocked_{result.primary_id}")
    assert not failures, f"Age incompatible primaries: {failures[:10]} (total {len(failures)})"


def test_matrix_has_trace_and_confidence() -> None:
    """Validator returns evidence trace and confidence label."""
    result = validate_rubric(RubricInput(
        house=10, planet="Saturn", age_band="adult", area="career", direction="mixed"))
    assert result.evidence_trace
    assert result.confidence in ("low", "moderate", "strong", "very_strong", "reject")
    assert result.primary is not None


def test_teen_blocks_adult_only() -> None:
    """Hard age gate rejects adult-only manifestations for teen band."""
    adult_only = adult_only_manifestations()
    for manifest in list(adult_only)[:5]:
        gate = validate_age_manifestation("teen", manifest)
        assert not gate["allowed"], manifest
        assert gate.get("replacement")


def test_10h_vs_11h_differ() -> None:
    """Same planet/age — 10H vs 11H should not always pick identical primary."""
    r10 = validate_rubric(RubricInput(
        house=10, planet="Jupiter", age_band="adult", area="career", direction="up"))
    r11 = validate_rubric(RubricInput(
        house=11, planet="Jupiter", age_band="adult", area="money", direction="up"))
    assert r10.primary_id or r11.primary_id
    # At least one should differ OR candidates differ
    assert r10.candidates != r11.candidates or r10.primary_id != r11.primary_id


def test_golden_teen_10h_career() -> None:
    """Golden fixture: teen + 10H → study/teacher language, not salary."""
    result = validate_rubric(RubricInput(
        house=10, planet="Saturn", age_band="teen", area="career", direction="up"))
    assert result.primary_id not in adult_only_manifestations()
    forbidden = {"income", "promotion", "salary_increase", "marriage", "parenting"}
    assert result.primary_id not in forbidden


def test_golden_adult_10h_career() -> None:
    """Golden fixture: adult + 10H → career-compatible manifestation."""
    result = validate_rubric(RubricInput(
        house=10, planet="Saturn", age_band="adult", area="career", direction="up"))
    assert result.primary_id
    assert result.confidence != "reject"


def test_health_non_diagnostic_recognition() -> None:
    """Health recognition variants must pass health safety check."""
    from qa_checks.health_safety_check import health_violations
    from narration.recognition_variants import RECOGNITION_CLAIMS
    for (manifest, band), text in RECOGNITION_CLAIMS.items():
        if "health" in manifest or manifest in (
                "energy_management", "routine", "rest", "stress_management",
                "preventive_attention", "wellbeing"):
            assert not health_violations(text), f"{manifest}/{band}: {text[:60]}"


def test_property_same_evidence_different_age() -> None:
    """Changing age band can change manifestation while astrology facts stay same."""
    base = dict(house=10, planet="Sun", area="career", direction="up", dasha_planet="Sun")
    teen = validate_rubric(RubricInput(**base, age_band="teen"))
    adult = validate_rubric(RubricInput(**base, age_band="adult"))
    assert validate_age_manifestation("teen", teen.primary_id)["allowed"]


def test_claim_level_promotion_blocked() -> None:
    """Level-3 promotion claim rejected without advancement manifestation."""
    from interpretation.prediction_meaning import PredictionMeaning
    from qa_checks.claim_validator import validate_claim
    meaning = PredictionMeaning(
        area="career", direction="up", age_band="adult",
        manifestations=["visibility", "responsibility"],
    )
    assert not validate_claim("You got promoted.", meaning, section="recognition")["allowed"]


def run_all() -> None:
    tests = [
        test_matrix_primary_age_compatible,
        test_matrix_has_trace_and_confidence,
        test_teen_blocks_adult_only,
        test_10h_vs_11h_differ,
        test_golden_teen_10h_career,
        test_golden_adult_10h_career,
        test_health_non_diagnostic_recognition,
        test_property_same_evidence_different_age,
        test_claim_level_promotion_blocked,
    ]
    failed = []
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {fn.__name__}: {exc}")
            failed.append(fn.__name__)
    if failed:
        raise SystemExit(f"{len(failed)} failed: {', '.join(failed)}")
    print(f"All {len(tests)} rubric tests passed.")


if __name__ == "__main__":
    run_all()
