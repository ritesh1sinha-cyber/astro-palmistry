"""Unit tests for cross-chart interpretation layer (final targeted fixes)."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "engines" / "astro"
sys.path.insert(0, str(ROOT))

from interpretation.evidence_builder import build_evidence
from interpretation.life_stage import (
    age_band_at, get_age_band, is_minor, narrative_area,
)
from interpretation.prediction_meaning import build_meaning
from narration.human_renderer import render_headline, render_manifest_bullets
from qa_checks.age_context_check import age_violations
from qa_checks.duplicate_check import DuplicateTracker
from qa_checks.grammar_check import fix_grammar
from qa_checks.health_safety_check import health_violations
from qa_checks.report_diversity import ReportDiversityGate
from qa_checks.specificity import is_specific_enough, specificity_score
from qa_checks.unsupported_claims import unsupported_event_detected
from impact import period_impact


def _pc(dob: str, age: int = 0) -> dict:
    return {"meta": {"dob": dob, "age": age}}


def test_age_at_future_window() -> None:
    """TEST A — age at Sep 2030 for DOB 2012-01-01 is young_adult (18)."""
    dob = date(2012, 1, 1)
    assert get_age_band(dob, date(2030, 9, 1)) == "young_adult"
    pc = _pc("2012-01-01")
    assert age_band_at(pc, date(2030, 9, 1)) == "young_adult"
    assert age_band_at(pc, date(2026, 8, 10)) == "teen"


def test_teen_no_adult_language() -> None:
    """TEST A — teen career signal → education language."""
    ev = build_evidence(
        _pc("2012-01-01"), area="career", house=10, direction="up",
        row={"planet": "Jupiter", "house": 10, "bav": 6, "promise": "up",
             "start": date(2026, 3, 1)},
        dasha={"vim": {"md": "Mercury", "ad": "Jupiter"}, "direction": "up"},
        age_band="teen")
    meaning = build_meaning(ev)
    assert meaning.narrative_area == "education"
    headline = render_headline(meaning, past=True)
    assert not age_violations(headline, "teen")
    assert not unsupported_event_detected(headline, meaning.manifestations)


def test_adult_career_language() -> None:
    """TEST B — adult career language."""
    ev = build_evidence(
        _pc("1986-03-08"), area="career", house=10, direction="up",
        row={"planet": "Jupiter", "house": 10, "bav": 6, "promise": "up"},
        dasha={"vim": {"md": "Saturn", "ad": "Saturn"}, "direction": "up"},
        age_band="adult")
    meaning = build_meaning(ev)
    assert meaning.narrative_area == "career"
    headline = render_headline(meaning, past=True)
    assert any(w in headline.lower() for w in ("work", "effort", "recogn", "responsib", "guidance", "mentor"))


def test_10th_vs_11th_house() -> None:
    """TEST C — career 10th vs 11th produce different manifestation sets."""
    e10 = build_evidence(
        _pc("1990-01-12"), area="career", house=10, direction="up",
        row={"planet": "Jupiter", "house": 10, "bav": 6, "promise": "up"},
        dasha={"vim": {"md": "Saturn", "ad": "Mercury"}}, age_band="adult")
    e11 = build_evidence(
        _pc("1990-01-12"), area="career", house=11, direction="up",
        row={"planet": "Jupiter", "house": 11, "bav": 6, "promise": "up"},
        dasha={"vim": {"md": "Saturn", "ad": "Mercury"}}, age_band="adult")
    m10 = build_meaning(e10)
    m11 = build_meaning(e11)
    assert m10.manifestations != m11.manifestations
    assert "network_gain" in m11.manifestations or "opportunity" in m11.manifestations
    assert "visibility" in m10.manifestations or "responsibility" in m10.manifestations
    b10 = set(render_manifest_bullets(m10))
    b11 = set(render_manifest_bullets(m11))
    assert b10 != b11


def test_different_dashas() -> None:
    """TEST D — Saturn–Saturn vs Ketu–Mars weight differently."""
    e1 = build_evidence(
        _pc("1986-03-08"), area="career", house=10, direction="mixed",
        row={"planet": "Saturn", "house": 10, "bav": 4, "promise": "mixed"},
        dasha={"vim": {"md": "Saturn", "ad": "Saturn"}}, age_band="adult")
    e2 = build_evidence(
        _pc("1990-01-12"), area="career", house=10, direction="down",
        row={"planet": "Ketu", "house": 10, "bav": 2, "promise": "down"},
        dasha={"vim": {"md": "Ketu", "ad": "Mars"}}, age_band="adult")
    assert build_meaning(e1).manifestations != build_meaning(e2).manifestations or \
        build_meaning(e1).caution != build_meaning(e2).caution


def test_specificity() -> None:
    """TEST E — vague bullets rejected; concrete accepted."""
    assert specificity_score("a decision needed attention") < 3
    assert not is_specific_enough("a decision that needed attention")
    assert is_specific_enough(
        "a study project required more organization from teachers or mentors")


def test_unsupported_claim() -> None:
    """TEST F — promotion claim rejected without promotion manifestation."""
    hits = unsupported_event_detected(
        "You received a promotion.", ["visibility", "responsibility"])
    assert hits


def test_duplicate_tracker() -> None:
    """TEST G — exact duplicate across signatures flagged."""
    tr = DuplicateTracker()
    sig_a = ("career", "adult", "up", "Saturn", "Saturn", "Jupiter", 10)
    sig_b = ("career", "adult", "mixed", "Ketu", "Mars", "Saturn", 8)
    text = "Your work may have become easier to move forward."
    tr.register(text, sig_a)
    assert tr.check(text, sig_b)


def test_health_no_diagnosis() -> None:
    """TEST I — diagnosis / recovery claims rejected."""
    assert health_violations("You will recover from illness.")
    assert health_violations("You recovered from illness faster than average.")


def test_grammar_a_a() -> None:
    assert "a a" not in fix_grammar("This is a a mixed phase.").lower()
    assert fix_grammar("This is a a mixed phase.") == "This is a mixed phase."


def test_chapter_no_double_meaning() -> None:
    """Same MD/AD should not repeat identical parenthetical twice."""
    line = period_impact("Saturn", "Saturn")
    assert line.count("discipline, patience and completion") <= 1
    assert "sets the broader tone" in line
    assert "You may feel this as" in line


def test_no_generic_fallback_bullets() -> None:
    meaning = build_meaning(build_evidence(
        _pc("1986-03-08"), area="career", house=10, direction="up",
        row={"planet": "Jupiter", "house": 10, "bav": 6, "promise": "up"},
        dasha={"vim": {"md": "Saturn", "ad": "Saturn"}}, age_band="adult"))
    bullets = render_manifest_bullets(meaning)
    joined = " ".join(bullets).lower()
    assert "noticeable shift in focus" not in joined
    assert "a decision that needed attention" not in joined


def test_recognition_teen_no_income_biography() -> None:
    """Teen recognition must not contain adult income biography."""
    from narration.recognition_renderer import render_recognition_claim
    adult = "You earn from what you know rather than from what you own — your income is tied to your own head."
    teen = render_recognition_claim("money", "money_earn", "teen", adult)
    assert teen
    assert "earn" not in teen.lower()
    assert "income" not in teen.lower()
    assert not age_violations(teen, "teen")


def test_recognition_adult_still_has_content() -> None:
    """Adult band keeps adult-appropriate financial wording when appropriate."""
    from narration.recognition_renderer import render_recognition_claim
    adult = "You earn from what you know rather than from what you own."
    text = render_recognition_claim("money", "money_earn", "adult", adult)
    assert text
    assert any(w in text.lower() for w in ("financial", "income", "progress", "stages", "earn", "money"))
    teen = render_recognition_claim("money", "money_earn", "teen", adult)
    assert teen and "earn" not in teen.lower() and "income" not in teen.lower()


def test_stage_config_band_thresholds() -> None:
    from interpretation.stage_config import band_for_age
    assert band_for_age(8) == "child"
    assert band_for_age(14) == "teen"
    assert band_for_age(20) == "young_adult"
    assert band_for_age(35) == "adult"
    assert band_for_age(50) == "mature_adult"
    assert band_for_age(65) == "senior"


def test_filter_empty_uses_band_default() -> None:
    from interpretation.life_stage import filter_scores_for_stage
    out = filter_scores_for_stage(
        {"promotion": 5}, area="career", age_band="teen", narrative="education")
    assert "promotion" not in out
    assert list(out.keys())


def test_stage_action_teen_career() -> None:
    from narration.stage_actions import action_for_stage
    line = action_for_stage("career", "teen")
    assert "teacher" in line.lower() or "study" in line.lower() or "mentor" in line.lower()


def main() -> int:
    tests = [
        test_age_at_future_window,
        test_teen_no_adult_language,
        test_adult_career_language,
        test_10th_vs_11th_house,
        test_different_dashas,
        test_specificity,
        test_unsupported_claim,
        test_duplicate_tracker,
        test_health_no_diagnosis,
        test_grammar_a_a,
        test_chapter_no_double_meaning,
        test_no_generic_fallback_bullets,
        test_recognition_teen_no_income_biography,
        test_recognition_adult_still_has_content,
        test_stage_config_band_thresholds,
        test_filter_empty_uses_band_default,
        test_stage_action_teen_career,
    ]
    failed = []
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed.append((fn.__name__, exc))
            print(f"FAIL {fn.__name__}: {exc}")
    if failed:
        return 1
    print(f"All {len(tests)} tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
