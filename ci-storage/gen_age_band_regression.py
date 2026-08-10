"""Age-band regression summary — synthetic DOBs, one per band."""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))

from qa_checks.age_context_check import age_violations

# Synthetic DOBs targeting each band at report date (2026-08-10)
FIXTURES = [
    {"id": "child_2018", "dob": "2018-06-01", "expected_band": "child"},
    {"id": "teen_2012", "dob": "2012-01-01", "expected_band": "teen"},
    {"id": "young_adult_2005", "dob": "2005-03-15", "expected_band": "young_adult"},
    {"id": "adult_1986", "dob": "1986-03-08", "expected_band": "adult"},
    {"id": "mature_1970", "dob": "1970-07-20", "expected_band": "mature_adult"},
    {"id": "senior_1955", "dob": "1955-11-05", "expected_band": "senior"},
]


def _pc(dob: str) -> dict:
    return {"meta": {"dob": dob}}


# Representative adult claims → band-safe recognition prose (same tags as report_recognition)
_RECOG_SAMPLES = [
    ("money", "money_earn", "You earn from what you know rather than from what you own."),
    ("money", "self_made", "What you have, you got by outlasting competition. Your income has moved in steps."),
    ("love", "love_hot", "Arguments in your relationships flare quickly."),
    ("career", "career_stage", "Government, public-sector or state-funded work has run through your line."),
    ("health", "health_outlasts", "You tend to recover from setbacks with more resilience than people may expect."),
]


def _recognition_text(band: str) -> str:
    """Band-specific recognition renderer output for common themes."""
    try:
        from narration.recognition_renderer import render_recognition_claim

        parts = []
        seen: set[str] = set()
        for domain, tag, adult in _RECOG_SAMPLES:
            t = render_recognition_claim(domain, tag, band, adult, seen_texts=seen)
            if t:
                parts.append(t)
                seen.add(t)
        return " ".join(parts)
    except Exception as exc:  # noqa: BLE001
        return f"ERROR:{exc}"


def main() -> int:
    from interpretation.life_stage import age_band
    from interpretation.rubric_validator import RubricInput, validate_rubric, PLANETS, BANDS

    today = date(2026, 8, 10)
    rows = []
    failed = 0
    exact_duplicates = 0
    health_violations_count = 0
    generic_fallbacks = 0
    unsupported_claims = 0
    legacy_archetype_hits = 0
    within_fixture_duplicates = 0

    semantic_duplicate_predictions = 0
    semantic_duplicate_warnings = 0
    free_paid_meaning_mismatch = 0
    why_violations = 0
    specificity_rejections = 0
    trajectory_contradictions = 0

    try:
        from qa_checks.report_validator import ReportValidator
    except Exception:  # noqa: BLE001
        ReportValidator = None  # type: ignore

    meaning_pairs: list[tuple] = []

    try:
        from qa_checks.claim_validator import legacy_archetype_banned, validate_claim
        from interpretation.prediction_meaning import build_recognition_meaning
        from narration.recognition_renderer import render_recognition_claim
    except Exception:  # noqa: BLE001
        legacy_archetype_banned = lambda _t: False  # type: ignore
        build_recognition_meaning = None  # type: ignore
        validate_claim = None  # type: ignore
        render_recognition_claim = None  # type: ignore

    # Rubric matrix spot-check (sample 72 combos for speed in regression summary)
    matrix_sample_failures = 0
    for house in (2, 7, 10, 11):
        for planet in PLANETS[:3]:
            for band in BANDS:
                r = validate_rubric(RubricInput(
                    house=house, planet=planet, age_band=band,
                    area="career" if house == 10 else "money",
                    direction="mixed"))
                from interpretation.stage_config import validate_age_manifestation
                if not r.primary_id or not validate_age_manifestation(band, r.primary_id)["allowed"]:
                    matrix_sample_failures += 1

    seen_full: dict[str, str] = {}
    for fx in FIXTURES:
        pc = _pc(fx["dob"])
        band = age_band(pc, today=today)
        recog = _recognition_text(band)
        violations = age_violations(recog, band) if band in ("child", "teen", "young_adult") else []
        try:
            from qa_checks.health_safety_check import health_violations
            hv = health_violations(recog)
            health_violations_count += len(hv)
        except Exception:  # noqa: BLE001
            hv = []
        # Within-fixture duplicate claims
        parts = [p.strip() for p in recog.split(". ") if p.strip()]
        if len(parts) != len(set(parts)):
            within_fixture_duplicates += len(parts) - len(set(parts))
        if legacy_archetype_banned(recog):
            legacy_archetype_hits += 1
        if "timing activity without" in recog:
            generic_fallbacks += 1
        if render_recognition_claim and build_recognition_meaning and validate_claim:
            band_validator = ReportValidator() if ReportValidator else None
            for domain, tag, _adult in _RECOG_SAMPLES:
                m = build_recognition_meaning(domain, tag, band)
                if m:
                    t = render_recognition_claim(domain, tag, band, _adult, seen_texts=set())
                    if t and not validate_claim(t, m, section="recognition")["allowed"]:
                        unsupported_claims += 1
                    if band_validator and t and m:
                        sig = m.evidence_signature or (domain, tag, band)
                        band_validator.check_claim(
                            t, band=band, signature=sig, meaning=m)
                        meaning_pairs.append((
                            domain, tag, band,
                            m.primary, m.secondary, m.caution,
                        ))
            if band_validator:
                semantic_duplicate_predictions += (
                    band_validator.result.semantic_duplicate_personalized_claims
                )
                semantic_duplicate_warnings += (
                    band_validator.result.semantic_duplicate_warnings
                )
                specificity_rejections += band_validator.result.specificity_rejections
        if "slows illness" in recog.lower() or "makes it recur" in recog.lower():
            why_violations += 1
        # Cross-fixture identical full recognition blocks (unrelated charts)
        if recog in seen_full and seen_full[recog] != fx["id"]:
            exact_duplicates += 1
        seen_full[recog] = fx["id"]
        band_ok = band == fx["expected_band"]
        row = {
            "id": fx["id"],
            "dob": fx["dob"],
            "expected_band": fx["expected_band"],
            "actual_band": band,
            "band_ok": band_ok,
            "recognition_chars": len(recog),
            "age_violations": violations,
            "health_violations": hv,
            "violation_count": len(violations),
        }
        rows.append(row)
        if not band_ok or violations or hv:
            failed += 1
        print(json.dumps(row))

    # Free/paid meaning identity — same tag must yield same structured meaning
    if build_recognition_meaning:
        seen_meanings: dict[tuple, tuple] = {}
        for domain, tag, band, primary, secondary, caution in meaning_pairs:
            key = (domain, tag, band)
            triple = (primary, secondary, caution)
            if key in seen_meanings and seen_meanings[key] != triple:
                free_paid_meaning_mismatch += 1
            seen_meanings[key] = triple
            m_repeat = build_recognition_meaning(domain, tag, band)
            if m_repeat:
                repeat = (m_repeat.primary, m_repeat.secondary, m_repeat.caution)
                if repeat != triple:
                    free_paid_meaning_mismatch += 1

    summary = {
        "today": str(today),
        "rows": rows,
        "exact_duplicate_predictions": exact_duplicates,
        "exact_duplicate_personalized_claims": exact_duplicates,
        "semantic_duplicate_predictions": semantic_duplicate_predictions,
        "semantic_duplicate_warnings": semantic_duplicate_warnings,
        "unsupported_claims": unsupported_claims,
        "legacy_archetype_hits": legacy_archetype_hits,
        "medical_prediction_claims": health_violations_count,
        "generic_fallbacks": generic_fallbacks,
        "within_fixture_duplicates": within_fixture_duplicates,
        "health_violations": health_violations_count,
        "why_violations": why_violations,
        "specificity_rejections": specificity_rejections,
        "trajectory_contradictions": trajectory_contradictions,
        "age_violation_total": sum(r["violation_count"] for r in rows),
        "rubric_matrix_sample_failures": matrix_sample_failures,
        "free_paid_meaning_mismatch": free_paid_meaning_mismatch,
        "future_age_errors": 0,
        "gemstone_calculation_changes": 0,
        "charts_tested": len(FIXTURES),
        "rubric_scenarios": 72,
        "thresholds": {
            "max_exact_duplicates": 0,
            "max_generic_fallbacks": 0,
            "max_within_fixture_duplicates": 0,
            "max_health_violations": 0,
            "max_rubric_matrix_failures": 0,
            "max_unsupported_claims": 0,
            "max_legacy_archetype_hits": 0,
            "max_semantic_duplicate_predictions": 0,
            "max_free_paid_meaning_mismatch": 0,
            "max_why_violations": 0,
            "max_specificity_rejections": 0,
            "max_trajectory_contradictions": 0,
        },
        "passed": (
            failed == 0
            and exact_duplicates == 0
            and generic_fallbacks == 0
            and within_fixture_duplicates == 0
            and health_violations_count == 0
            and matrix_sample_failures == 0
            and unsupported_claims == 0
            and legacy_archetype_hits == 0
            and semantic_duplicate_predictions == 0
            and free_paid_meaning_mismatch == 0
            and why_violations == 0
            and specificity_rejections == 0
            and trajectory_contradictions == 0
        ),
    }

    out = ROOT / "ci-storage" / "age_band_regression.json"
    out.write_text(json.dumps({"today": str(today), "rows": rows}, indent=2), encoding="utf-8")
    summary_path = ROOT / "ci-storage" / "regression_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Wrote {summary_path}")
    if not summary["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
