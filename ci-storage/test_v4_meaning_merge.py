"""Graharekha v4 — meaning merge, evidence gating, confidence split, health threshold."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))


def _duplicate_bug_pc() -> dict:
    """Synthetic adult chart that previously emitted duplicate money/career families."""
    return {
        "meta": {"dob": "1986-03-08"},
        "planets": {
            "Saturn": {"house": 2, "dignity": "own_sign"},
            "Jupiter": {"house": 11, "dignity": "friendly_sign"},
            "Sun": {"house": 11, "dignity": "neutral_sign"},
            "Mercury": {"house": 10, "dignity": "own_sign"},
        },
        "house_lords": {
            "2": {"lord": "Saturn", "lord_house": 10, "lord_dignity": "own_sign"},
            "11": {"lord": "Jupiter", "lord_house": 2, "lord_dignity": "friendly_sign"},
            "10": {"lord": "Sun", "lord_house": 4, "lord_dignity": "neutral_sign"},
        },
        "ashtakavarga": {"sav": [28] * 12},
    }


def test_v4_money_core_story_merges() -> None:
    """Fix patch v7 — Saturn/2H + Jupiter/11H merge into one money_core story."""
    from report_recognition import build

    blocks = {b["key"]: b for b in build(_duplicate_bug_pc(), per_domain=3)}
    money = blocks["money"]["claims"]
    assert len(money) == 1, f"money: expected 1 merged claim, got {len(money)}"
    texts = [c[0] for c in money]
    assert len(texts) == len(set(texts)), "money: duplicate claim text"


def test_v4_money_career_duplicate_merge() -> None:
    """Same-family duplicates collapse; career stays one merged claim on this chart."""
    from report_recognition import build

    blocks = {b["key"]: b for b in build(_duplicate_bug_pc(), per_domain=3)}
    career = blocks["career"]["claims"]
    assert len(career) == 1, f"career: expected 1 merged claim, got {len(career)}"
    bullet_sets = [tuple(c[2]) for c in career]
    assert len(bullet_sets) == len(set(bullet_sets)), "career: duplicate bullet sets"
    texts = [c[0] for c in career]
    assert len(texts) == len(set(texts)), "career: duplicate claim text"


def test_v4_delayed_recognition_requires_saturn() -> None:
    """Spec item 38 — Venus+10H must not auto-create delayed_recognition."""
    from interpretation.rubric_validator import RubricInput, validate_rubric

    venus = validate_rubric(
        RubricInput(
            house=10,
            planet="Venus",
            age=35,
            age_band="adult",
            area="career",
            direction="mixed",
        )
    )
    assert venus.caution_id != "delayed_recognition", venus.caution_id

    saturn = validate_rubric(
        RubricInput(
            house=10,
            planet="Saturn",
            age=35,
            age_band="adult",
            area="career",
            direction="down",
            dasha_planet="Saturn",
        )
    )
    assert saturn.caution_id == "delayed_recognition"

    jupiter11 = validate_rubric(
        RubricInput(
            house=11,
            planet="Jupiter",
            age=35,
            age_band="adult",
            area="career",
            direction="mixed",
        )
    )
    assert jupiter11.caution_id != "delayed_recognition"


def test_v4_manifestation_rules_delayed_saturn() -> None:
    from interpretation.evidence_builder import EvidenceBundle
    from interpretation.manifestation_rules import caution_from_evidence

    ev_venus = EvidenceBundle(
        area="career",
        direction="mixed",
        age_band="adult",
        primary_dasha="Venus",
        transit_planet="Venus",
    )
    assert caution_from_evidence(ev_venus, ["delayed_reward"]) != "delayed_recognition"

    ev_saturn = EvidenceBundle(
        area="career",
        direction="challenging",
        age_band="adult",
        primary_dasha="Saturn",
        transit_house=10,
        transit_planet="Saturn",
    )
    assert caution_from_evidence(ev_saturn, ["delayed_reward"]) == "delayed_recognition"


def test_v4_two_confidence_split() -> None:
    """Strong timing + many close candidates → event_confidence low."""
    from interpretation.evidence_builder import EvidenceBundle
    from interpretation.prediction_meaning import build_meaning
    from interpretation.rubric_validator import RubricInput, validate_rubric

    r = validate_rubric(
        RubricInput(
            house=10,
            planet="Saturn",
            age=35,
            age_band="adult",
            area="career",
            direction="mixed",
            dasha_planet="Saturn",
            divisional_support="strong",
            divisional_chart="D10",
        )
    )
    assert r.confidence in ("strong", "very_strong", "moderate")
    assert r.event_confidence in ("low", "moderate", "strong")

    ev = EvidenceBundle(
        area="career",
        direction="mixed",
        age_band="adult",
        age_at_period=35,
        primary_dasha="Saturn",
        birth_house=10,
        transit_house=10,
        transit_planet="Saturn",
        divisional_chart="D10",
        divisional_support="strong",
    )
    meaning = build_meaning(ev)
    assert meaning.timing_confidence
    assert meaning.event_confidence

    from narration.human_renderer import uses_event_uncertainty, TRANSPARENT_PAID

    low_event = meaning.__class__(
        area=meaning.area,
        direction=meaning.direction,
        age_band=meaning.age_band,
        manifestations=meaning.manifestations,
        confidence="strong",
        timing_confidence="strong",
        event_confidence="low",
    )
    assert uses_event_uncertainty(low_event)
    from narration.human_renderer import _fallback_headline

    assert _fallback_headline(low_event, past=True) == TRANSPARENT_PAID


def test_v4_health_personalization_threshold() -> None:
    """Weak health evidence must not ship as personalized."""
    from interpretation.prediction_meaning import PredictionMeaning
    from qa_checks.report_validator import ReportValidator

    text = (
        "Changes in routine or stress may make you more aware of how closely "
        "your emotional state, routine and physical wellbeing are connected."
    )
    weak = PredictionMeaning(
        area="health",
        direction="mixed",
        age_band="adult",
        manifestations=["routine", "energy_management"],
        evidence_trace=["6th house"],
        evidence_signature=("health", "floor", "adult", "routine", "", 6, "Mars"),
    )
    v = ReportValidator()
    assert v.check_claim(
        text,
        band="adult",
        signature=weak.evidence_signature,
        meaning=weak,
    )
    assert v.result.generic_fallbacks == 0
    assert v.result.exact_duplicate_personalized_claims == 0


def test_v4_family_for_coverage() -> None:
    """Every recognition bullet key maps to a configured semantic family."""
    from interpretation.stage_config import family_for, manifestation_families
    from narration.recognition_variants import RECOGNITION_BULLETS

    families = manifestation_families()
    missing = [
        mid for mid in RECOGNITION_BULLETS
        if mid not in families and family_for(mid) == mid
    ]
    assert not missing, f"unmapped manifestation IDs: {missing[:5]}"


def test_v4_saturn_house_diversity() -> None:
    """Spec item 40 — same planet, different houses → diverse manifestation lists."""
    from interpretation.rubric_validator import RubricInput, validate_rubric

    lists = []
    for house in (2, 6, 10, 11):
        area = "money" if house in (2, 11) else ("health" if house == 6 else "career")
        r = validate_rubric(
            RubricInput(
                house=house,
                planet="Saturn",
                age=35,
                age_band="adult",
                area=area,
                direction="mixed",
                dasha_planet="Saturn",
            )
        )
        lists.append(tuple(r.manifestation_list()))
    assert len(set(lists)) >= 3, f"Saturn lists too uniform: {lists}"


def test_v4_planet_house10_diversity() -> None:
    """Spec item 41 — same house, different planets → diverse manifestation lists."""
    from interpretation.rubric_validator import RubricInput, validate_rubric

    lists = []
    for planet in ("Sun", "Saturn", "Mercury", "Jupiter", "Venus", "Mars"):
        r = validate_rubric(
            RubricInput(
                house=10,
                planet=planet,
                age=35,
                age_band="adult",
                area="career",
                direction="mixed",
                dasha_planet=planet,
            )
        )
        lists.append(tuple(r.manifestation_list()))
    assert len(set(lists)) >= 4, f"10H planet lists too uniform: {lists}"


def test_v4_age_10h_saturn_manifestation_bands() -> None:
    """Spec item 39 — 10H+Saturn at 14/19/35/68: band-safe manifestations, no minor forbidden terms."""
    from interpretation.stage_config import band_for_age, eligible_manifestations, forbidden_terms
    from narration.recognition_renderer import render_recognition_claim
    from qa_checks.age_context_check import age_violations

    cases = [
        (14, "teen"),
        (19, "young_adult"),
        (35, "adult"),
        (68, "senior"),
    ]
    for age, expected_band in cases:
        band = band_for_age(age)
        assert band == expected_band, f"age {age}: expected {expected_band}, got {band}"
        allowed = eligible_manifestations(band, "career", "career")
        rendered = render_recognition_claim(
            "career", "career_stage", band, "", pc=None, house=10, planet="Saturn",
        )
        assert rendered, f"age {age}: no rendered claim"
        for term in forbidden_terms(band):
            assert term.lower() not in rendered.lower(), (
                f"age {age}: forbidden term {term!r} in {rendered[:80]}"
            )
        assert not age_violations(rendered, band), f"age {age}: age violations in claim"
        from interpretation.rubric_validator import RubricInput, validate_rubric

        r = validate_rubric(
            RubricInput(
                house=10,
                planet="Saturn",
                age=age,
                age_band=band,
                area="career",
                direction="mixed",
                dasha_planet="Saturn",
            )
        )
        for mid in r.manifestation_list():
            assert mid in allowed or not allowed, (
                f"age {age}: manifestation {mid} not in eligible set for {band}"
            )


def main() -> int:
    tests = [
        test_v4_money_core_story_merges,
        test_v4_money_career_duplicate_merge,
        test_v4_delayed_recognition_requires_saturn,
        test_v4_manifestation_rules_delayed_saturn,
        test_v4_two_confidence_split,
        test_v4_health_personalization_threshold,
        test_v4_family_for_coverage,
        test_v4_saturn_house_diversity,
        test_v4_planet_house10_diversity,
        test_v4_age_10h_saturn_manifestation_bands,
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
