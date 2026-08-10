"""Graharekha v3 feedback — regression locks for duplicates, age diversity, legacy bans."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))

# Item 43 — personalized claims that must fail when duplicated across signatures
V3_DUPLICATE_SENTENCES = [
    "What you managed to keep may have mattered as much as what arrived.",
    "Responsibility may have increased before recognition fully caught up with your effort.",
    "Financial progress may have come in stages, with each improvement requiring persistence.",
]

# Opening-section legacy marketing copy from v3 spec (must stay banned)
V3_LEGACY_PHRASES = [
    "You were built by difficulty rather than by encouragement",
    "You have come through a stretch that visibly changed the people who went through it with you",
    "You tend to recover from setbacks with more resilience than people may expect",
    "Money has reached you at least once from a source you did not earn week by week",
    "You are better at earning than at holding",
    "People notice you before you have said anything",
    "Government, public-sector or state-funded work has run through your line",
    "Your openings have come through your reputation rather than through applications",
]


def _meaning(**kwargs):
    from interpretation.prediction_meaning import PredictionMeaning

    defaults = dict(
        area="career",
        direction="mixed",
        age_band="adult",
        manifestations=["responsibility", "recognition"],
        evidence_trace=["10th house", "Saturn"],
    )
    defaults.update(kwargs)
    return PredictionMeaning(**defaults)


def test_item43_duplicate_across_signatures() -> None:
    """Tests A/B/C — same sentence, different evidence signatures → FAIL on second."""
    from qa_checks.report_validator import ReportValidator

    for text in V3_DUPLICATE_SENTENCES:
        v = ReportValidator()
        m1 = _meaning(evidence_signature=("career", "tag_a", "adult", "a", "b"))
        m2 = _meaning(evidence_signature=("career", "tag_b", "adult", "c", "d"))
        assert v.check_claim(text, band="adult", signature=m1.evidence_signature, meaning=m1)
        ok2 = v.check_claim(text, band="adult", signature=m2.evidence_signature, meaning=m2)
        assert not ok2, f"expected duplicate fail for: {text[:50]}"
        assert v.result.exact_duplicate_personalized_claims >= 1


def test_item43_same_signature_reworded_passes() -> None:
    """Test D — same signature, different wording → PASS."""
    from qa_checks.report_validator import ReportValidator

    sig = ("career", "career_stage", "adult", "responsibility", "authority")
    v = ReportValidator()
    m = _meaning(
        manifestations=["responsibility", "authority"],
        evidence_signature=sig,
    )
    t1 = "Responsibility may have increased before recognition fully caught up with your effort."
    t2 = "Recognition may have followed sustained responsibility."
    assert v.check_claim(t1, band="adult", signature=sig, meaning=m)
    assert v.check_claim(t2, band="adult", signature=sig, meaning=m)


def test_item38_same_astrology_different_age() -> None:
    """10H + Saturn — ages 15/19/35/68 must not all share the same primary."""
    from interpretation.rubric_validator import RubricInput, validate_rubric

    primaries = []
    for age, band in [(15, "teen"), (19, "young_adult"), (35, "adult"), (68, "senior")]:
        r = validate_rubric(
            RubricInput(
                house=10,
                planet="Saturn",
                age=age,
                age_band=band,
                area="career",
                direction="mixed",
                dasha_planet="Saturn",
                divisional_support="strong",
                divisional_chart="D10",
            )
        )
        primaries.append(r.primary_id)
    assert len(set(primaries)) >= 3, f"expected age-diverse primaries, got {primaries}"


def test_v3_legacy_phrases_banned() -> None:
    from qa_checks.claim_validator import legacy_archetype_banned

    missing = [p for p in V3_LEGACY_PHRASES if not legacy_archetype_banned(p)]
    assert not missing, f"legacy_archetype_banned must cover: {missing[:3]}"


def test_transit_planet_changes_manifestation() -> None:
    """Transit planet must influence primary/secondary selection."""
    from interpretation.evidence_builder import EvidenceBundle
    from interpretation.rubric_validator import rubric_from_evidence

    def ev(transit: str) -> EvidenceBundle:
        return EvidenceBundle(
            area="career",
            direction="mixed",
            age_band="adult",
            age_at_period=35,
            primary_dasha="Saturn",
            birth_house=10,
            transit_house=10,
            transit_planet=transit,
            divisional_chart="D10",
            divisional_support="mixed",
        )

    r_j = rubric_from_evidence(ev("Jupiter"))
    r_m = rubric_from_evidence(ev("Mars"))
    assert (r_j.primary_id, r_j.secondary_id) != (r_m.primary_id, r_m.secondary_id), (
        f"Jupiter vs Mars transit should differ: {r_j.secondary_id} vs {r_m.secondary_id}"
    )


def test_divisional_support_influences_selection() -> None:
    """Strong divisional support must change ranking or confidence vs weak."""
    from interpretation.evidence_builder import EvidenceBundle
    from interpretation.rubric_validator import rubric_from_evidence

    def ev(support: str) -> EvidenceBundle:
        return EvidenceBundle(
            area="career",
            direction="mixed",
            age_band="adult",
            age_at_period=35,
            primary_dasha="Saturn",
            birth_house=10,
            transit_house=10,
            transit_planet="Saturn",
            divisional_chart="D10",
            divisional_support=support,
        )

    r_strong = rubric_from_evidence(ev("strong"))
    r_weak = rubric_from_evidence(ev("weak"))
    changed = (
        r_strong.primary_id != r_weak.primary_id
        or r_strong.secondary_id != r_weak.secondary_id
        or r_strong.confidence != r_weak.confidence
        or (r_strong.primary.score if r_strong.primary else 0)
        != (r_weak.primary.score if r_weak.primary else 0)
    )
    assert changed, "divisional strong vs weak must affect rubric output"


def test_v3_legacy_resilience_phrase_banned() -> None:
    """Exact v3 problem sentence must be blocked as legacy archetype."""
    from qa_checks.claim_validator import legacy_archetype_banned

    assert legacy_archetype_banned(
        "You tend to recover from setbacks with more resilience than people may expect."
    )


def test_build_output_has_no_v3_legacy_phrases() -> None:
    """Current recognition build must not emit v3 legacy marketing copy."""
    from report_recognition import build, render

    pc = {
        "meta": {"dob": "1986-03-08"},
        "planets": {
            "Saturn": {"house": 10, "dignity": "own_sign"},
            "Mars": {"house": 6, "dignity": "own_sign"},
            "Venus": {"house": 7, "dignity": "exalted"},
            "Jupiter": {"house": 2, "dignity": "mixed"},
            "Moon": {"house": 4, "dignity": "mixed"},
            "Mercury": {"house": 10, "dignity": "mixed"},
            "Sun": {"house": 11, "dignity": "mixed"},
            "Rahu": {"house": 6, "dignity": "mixed"},
        },
        "house_lords": {
            "10": {"lord": "Mercury", "lord_house": 10, "lord_dignity": "mixed"},
            "2": {"lord": "Jupiter", "lord_house": 2, "lord_dignity": "mixed"},
            "6": {"lord": "Mars", "lord_house": 6, "lord_dignity": "own_sign"},
            "7": {"lord": "Venus", "lord_house": 7, "lord_dignity": "exalted"},
            "4": {"lord": "Moon", "lord_house": 4, "lord_dignity": "mixed"},
        },
        "ashtakavarga": {"sav": [28] * 12},
    }
    html = render(build(pc, per_domain=3))
    low = html.lower()
    for phrase in V3_LEGACY_PHRASES:
        assert phrase.lower() not in low, f"build output contains banned: {phrase[:40]}"


def test_v3_phrases_absent_from_ci_storage_reports() -> None:
    """Smoke HTML on disk must not contain v3 legacy phrases."""
    html_paths = [
        ROOT / "ci-storage" / "astro_full_report_free.html",
        ROOT / "ci-storage" / "astro_full_report_paid.html",
    ]
    oversample = ROOT / "ci-storage" / "oversample"
    if oversample.is_dir():
        html_paths.extend(oversample.glob("*.html"))

    checked = 0
    for path in html_paths:
        if not path.is_file():
            continue
        checked += 1
        body = path.read_text(encoding="utf-8", errors="replace").lower()
        for phrase in V3_LEGACY_PHRASES:
            assert phrase.lower() not in body, f"{path.name} contains banned: {phrase[:40]}"

    assert checked >= 2, "expected at least ci-storage free/paid HTML fixtures"


def run_all() -> None:
    tests = [
        test_item43_duplicate_across_signatures,
        test_item43_same_signature_reworded_passes,
        test_item38_same_astrology_different_age,
        test_v3_legacy_phrases_banned,
        test_v3_legacy_resilience_phrase_banned,
        test_build_output_has_no_v3_legacy_phrases,
        test_transit_planet_changes_manifestation,
        test_divisional_support_influences_selection,
        test_v3_phrases_absent_from_ci_storage_reports,
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
    print(f"All {len(tests)} v3 regression tests passed.")


if __name__ == "__main__":
    run_all()
