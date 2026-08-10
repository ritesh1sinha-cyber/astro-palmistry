"""Recognition semantic tests — no legacy archetypes; claim-level gates."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))

LEGACY_BANNED = [
    "once money reaches you it tends to stay",
    "not a person who loses what they have built",
    "you know most of it was stubbornness",
    "people bring you their problems, including strangers",
    "people ring when it has gone wrong, not when it is going well",
    "government, public-sector or state-funded work has run through your line",
]

GOLDEN_FIXTURES = [
    {
        "id": "teen_10H_saturn",
        "domain": "career",
        "tag": "career_stage",
        "band": "teen",
        "forbidden": ["salary", "promotion", "mortgage", "retirement", "income has moved"],
    },
    {
        "id": "teen_money",
        "domain": "money",
        "tag": "money_earn",
        "band": "teen",
        "forbidden": ["your income", "you earn", "salary", "promotion"],
    },
    {
        "id": "adult_money",
        "domain": "money",
        "tag": "money_earn",
        "band": "adult",
        "forbidden": ["once money reaches you", "not a person who loses"],
        "required_any": ["financial", "progress", "stages", "persistence", "money", "resources"],
    },
]


def test_no_legacy_archetypes_in_renderer() -> None:
    from narration.recognition_renderer import render_recognition_claim
    adult_samples = [
        ("money", "money_hold", "Once money reaches you it tends to stay. You are not a person who loses what they have built."),
        ("career", "career_stage", "You have come through a stretch. They call it strength; you know most of it was stubbornness."),
        ("love", "love_hot", "People bring you their problems, including strangers."),
        ("career", "career_stage", "Government, public-sector or state-funded work has run through your line."),
    ]
    for domain, tag, adult in adult_samples:
        for band in ("teen", "adult", "mature_adult"):
            text = render_recognition_claim(domain, tag, band, adult, seen_texts=set())
            if not text:
                continue
            low = text.lower()
            for bad in LEGACY_BANNED:
                assert bad not in low, f"{band}/{tag}: {bad} in {text}"


def test_claim_validator_rejects_level3_promotion() -> None:
    from interpretation.prediction_meaning import PredictionMeaning
    from qa_checks.claim_validator import validate_claim
    meaning = PredictionMeaning(
        area="career", direction="mixed", age_band="adult",
        manifestations=["visibility", "responsibility"],
    )
    v = validate_claim("You received a promotion.", meaning, section="recognition")
    assert not v["allowed"]
    assert v["replacement"]


def test_teen_money_level2_only() -> None:
    from narration.recognition_renderer import render_recognition_claim
    from qa_checks.claim_validator import classify_claim_level
    adult = "You earn from what you know rather than from what you own."
    text = render_recognition_claim("money", "money_earn", "teen", adult, seen_texts=set())
    assert text
    assert classify_claim_level(text) <= 2
    low = text.lower()
    assert "earn" not in low
    assert "income" not in low or "independence" in low


def test_meaning_has_evidence_trace() -> None:
    from interpretation.prediction_meaning import build_recognition_meaning
    m = build_recognition_meaning("career", "career_stage", "teen")
    assert m
    assert m.primary
    assert m.evidence_trace
    assert m.claim_level == 2


def test_golden_fixtures() -> None:
    from narration.recognition_renderer import render_recognition_claim
    for fx in GOLDEN_FIXTURES:
        adult = "Legacy adult biography text for testing."
        text = render_recognition_claim(
            fx["domain"], fx["tag"], fx["band"], adult, seen_texts=set())
        assert text, fx["id"]
        low = text.lower()
        for forbidden in fx.get("forbidden", []):
            assert forbidden.lower() not in low, f"{fx['id']}: {forbidden}"
        if fx.get("required_any"):
            assert any(r in low for r in fx["required_any"]), fx["id"]


def test_recognition_bullets_not_empty_for_career() -> None:
    from interpretation.prediction_meaning import build_recognition_meaning
    from narration.recognition_renderer import recognition_bullets
    m = build_recognition_meaning("career", "career_stage", "teen")
    assert m
    bullets = recognition_bullets(m)
    assert bullets
    assert len(bullets) <= 3


def run_all() -> None:
    tests = [
        test_no_legacy_archetypes_in_renderer,
        test_claim_validator_rejects_level3_promotion,
        test_teen_money_level2_only,
        test_meaning_has_evidence_trace,
        test_golden_fixtures,
        test_recognition_bullets_not_empty_for_career,
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
    print(f"All {len(tests)} recognition semantic tests passed.")


if __name__ == "__main__":
    run_all()
