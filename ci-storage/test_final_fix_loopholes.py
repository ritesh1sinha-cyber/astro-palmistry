"""Final fix loophole closure — why safety, validators, chapter lines."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))


def test_saturn_why_note_safe() -> None:
    from report_recognition import health_claims
    from qa_checks.why_safety_check import why_is_safe

    pc = {"planets": {"Saturn": {"house": 6}}, "house_lords": {}}
    claims = health_claims(pc)
    saturn_whys = [w for t, w in claims if "Saturn" in (w or "")]
    assert saturn_whys, "expected Saturn health why"
    for w in saturn_whys:
        assert "slows illness" not in w.lower()
        assert "makes it recur" not in w.lower()
        assert why_is_safe(w)


def test_build_sanitizes_unsafe_why() -> None:
    from report_recognition import build
    from qa_checks.why_safety_check import why_is_safe

    pc = {
        "meta": {"dob": "1986-03-08"},
        "planets": {
            "Saturn": {"house": 6, "dignity": "own_sign"},
            "Mars": {"house": 1, "dignity": "own_sign"},
        },
        "house_lords": {
            "6": {"lord": "Saturn", "lord_house": 6, "lord_dignity": "own_sign"},
            "2": {"lord": "Mercury", "lord_house": 10, "lord_dignity": "mixed"},
        },
        "ashtakavarga": {"sav": [28] * 12},
    }
    blocks = build(pc, per_domain=2)
    html = __import__("report_recognition", fromlist=["render"]).render(blocks)
    assert "slows illness down and makes it recur" not in html.lower()
    for block in blocks:
        for claim in block.get("claims", []):
            why = claim[1] if len(claim) > 1 else ""
            if why:
                assert why_is_safe(why)


def test_chapter_line_varies_by_age() -> None:
    from report_language import chapter_area_line

    teen = chapter_area_line("career", age_band="teen")
    adult = chapter_area_line("career", age_band="adult")
    senior = chapter_area_line("career", age_band="senior")
    assert teen != adult
    assert senior != adult
    assert "study" in teen.lower() or "guidance" in teen.lower()
    assert "visibility, initiative and experienced support" not in teen


def test_specificity_gate_rejects_vague() -> None:
    from qa_checks.report_validator import ReportValidator
    from interpretation.prediction_meaning import PredictionMeaning

    v = ReportValidator()
    meaning = PredictionMeaning(
        area="money", direction="mixed", age_band="adult",
        manifestations=["income"], evidence_trace=["2nd house"],
    )
    ok = v.check_claim("You changed something important in your life.", band="adult", signature=("a",), meaning=meaning)
    assert not ok
    assert v.result.specificity_rejections >= 1


def test_semantic_dup_rejects_different_signatures() -> None:
    """Identical personalized claim across different evidence signatures must fail."""
    from qa_checks.report_validator import ReportValidator
    from interpretation.prediction_meaning import PredictionMeaning

    v = ReportValidator()
    m1 = PredictionMeaning(
        area="money", direction="mixed", age_band="adult",
        manifestations=["income"], evidence_trace=["2H"],
        evidence_signature=("money", "a", "adult"),
    )
    m2 = PredictionMeaning(
        area="money", direction="mixed", age_band="adult",
        manifestations=["savings"], evidence_trace=["11H"],
        evidence_signature=("money", "b", "adult"),
    )
    text = "Financial progress may have come in stages, with each improvement requiring persistence."
    assert v.check_claim(text, band="adult", signature=m1.evidence_signature, meaning=m1)
    ok2 = v.check_claim(text, band="adult", signature=m2.evidence_signature, meaning=m2)
    assert not ok2
    assert v.result.exact_duplicate_personalized_claims >= 1


def test_semantic_dup_allows_same_signature() -> None:
    from qa_checks.report_validator import ReportValidator
    from interpretation.prediction_meaning import PredictionMeaning

    v = ReportValidator()
    sig = ("money", "money_earn", "adult", "income", "")
    m = PredictionMeaning(
        area="money", direction="mixed", age_band="adult",
        manifestations=["income"], evidence_trace=["11th house"],
        evidence_signature=sig,
    )
    t1 = "Financial progress may have come in stages, with each improvement requiring persistence."
    t2 = "Financial progress may have come in stages, with persistence playing an important role."
    assert v.check_claim(t1, band="adult", signature=sig, meaning=m)
    assert v.check_claim(t2, band="adult", signature=sig, meaning=m)


def test_evidence_trace_empty_not_personalized() -> None:
    from interpretation.prediction_meaning import PredictionMeaning
    from qa_checks.claim_validator import validate_claim

    meaning = PredictionMeaning(
        area="career", direction="mixed", age_band="adult",
        manifestations=["visibility"], evidence_trace=[],
    )
    v = validate_claim(
        "Recognition may have started catching up with the work you were already doing.",
        meaning,
    )
    assert v["allowed"]
    assert not v["personalized_claim"]


def test_trajectory_contradiction() -> None:
    from qa_checks.trajectory_check import has_trajectory_contradiction

    assert has_trajectory_contradiction(
        "up",
        "Progress is building steadily.",
        "This area is likely to deteriorate quickly.",
    )


def test_free_paid_meaning_identity() -> None:
    from interpretation.prediction_meaning import build_recognition_meaning

    m = build_recognition_meaning("career", "career_stage", "teen")
    assert m
    m2 = build_recognition_meaning("career", "career_stage", "teen")
    assert m.primary == m2.primary
    assert m.secondary == m2.secondary
    assert m.caution == m2.caution


def run_all() -> None:
    tests = [
        test_saturn_why_note_safe,
        test_build_sanitizes_unsafe_why,
        test_chapter_line_varies_by_age,
        test_specificity_gate_rejects_vague,
        test_semantic_dup_rejects_different_signatures,
        test_semantic_dup_allows_same_signature,
        test_evidence_trace_empty_not_personalized,
        test_trajectory_contradiction,
        test_free_paid_meaning_identity,
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
    print(f"All {len(tests)} final-fix tests passed.")


if __name__ == "__main__":
    run_all()
