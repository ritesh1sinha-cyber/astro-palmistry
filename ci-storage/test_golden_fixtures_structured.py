"""Golden fixture structured regression — compare PredictionMeaning fields, not HTML."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))

from interpretation.life_stage import age_band  # noqa: E402
from narration.recognition_renderer import build_meaning_for_tag  # noqa: E402
from narration.recognition_variants import TAG_EVIDENCE  # noqa: E402
from qa_checks.claim_validator import default_claim_level  # noqa: E402

# Representative tags exercised across domains (not DOB-specific branches in prod code)
DOMAIN_TAGS = [
    ("money", "money_earn"),
    ("money", "money_hold"),
    ("love", "love_hot"),
    ("career", "career_stage"),
    ("health", "health_outlasts"),
    ("parents", "floor"),
]

FIXTURES = [
    {"id": "meera", "dob": "1992-11-14"},
    {"id": "ramesh", "dob": "1986-03-08"},
    {"id": "gyanesh", "dob": "2012-01-01"},
    {"id": "suresh", "dob": "1990-01-12"},
]

# Snapshot oracle — structured fields only (update intentionally when rubric changes)
EXPECTED: dict[str, list[dict]] = {
    "meera": [
        {"domain": "money", "tag": "money_earn", "life_area": "money", "primary": "income", "secondary": ""},
        {"domain": "money", "tag": "money_hold", "life_area": "money", "primary": "savings", "secondary": "income"},
        {"domain": "love", "tag": "love_hot", "life_area": "love", "primary": "commitment", "secondary": ""},
        {"domain": "career", "tag": "career_stage", "life_area": "career", "primary": "responsibility", "secondary": "visibility"},
        {"domain": "health", "tag": "health_outlasts", "life_area": "health", "primary": "energy_management", "secondary": ""},
        {"domain": "parents", "tag": "floor", "life_area": "home", "primary": "domestic_stability", "secondary": ""},
    ],
    "ramesh": [
        {"domain": "money", "tag": "money_earn", "life_area": "money", "primary": "income", "secondary": ""},
        {"domain": "money", "tag": "money_hold", "life_area": "money", "primary": "savings", "secondary": "income"},
        {"domain": "love", "tag": "love_hot", "life_area": "love", "primary": "commitment", "secondary": ""},
        {"domain": "career", "tag": "career_stage", "life_area": "career", "primary": "responsibility", "secondary": "visibility"},
        {"domain": "health", "tag": "health_outlasts", "life_area": "health", "primary": "energy_management", "secondary": ""},
        {"domain": "parents", "tag": "floor", "life_area": "home", "primary": "domestic_stability", "secondary": ""},
    ],
    "gyanesh": [
        {"domain": "money", "tag": "money_earn", "life_area": "money", "primary": "resource_habits", "secondary": "allowance"},
        {"domain": "money", "tag": "money_hold", "life_area": "money", "primary": "resource_habits", "secondary": "savings_habits"},
        {"domain": "love", "tag": "love_hot", "life_area": "love", "primary": "communication", "secondary": ""},
        {"domain": "career", "tag": "career_stage", "life_area": "career", "primary": "study_progress", "secondary": "concentration"},
        {"domain": "health", "tag": "health_outlasts", "life_area": "health", "primary": "energy_management", "secondary": ""},
        {"domain": "parents", "tag": "floor", "life_area": "home", "primary": "family_responsibility", "secondary": ""},
    ],
    "suresh": [
        {"domain": "money", "tag": "money_earn", "life_area": "money", "primary": "income", "secondary": ""},
        {"domain": "money", "tag": "money_hold", "life_area": "money", "primary": "savings", "secondary": "income"},
        {"domain": "love", "tag": "love_hot", "life_area": "love", "primary": "commitment", "secondary": ""},
        {"domain": "career", "tag": "career_stage", "life_area": "career", "primary": "responsibility", "secondary": "visibility"},
        {"domain": "health", "tag": "health_outlasts", "life_area": "health", "primary": "energy_management", "secondary": ""},
        {"domain": "parents", "tag": "floor", "life_area": "home", "primary": "domestic_stability", "secondary": ""},
    ],
}


def _pc(dob: str) -> dict:
    return {"meta": {"dob": dob}}


def structured_rows(fixture_id: str, dob: str) -> list[dict]:
    pc = _pc(dob)
    band = age_band(pc)
    rows: list[dict] = []
    for domain, tag in DOMAIN_TAGS:
        meaning = build_meaning_for_tag(domain, tag, band, pc=pc)
        assert meaning, f"{fixture_id}/{domain}/{tag}: no meaning"
        rows.append({
            "fixture": fixture_id,
            "domain": domain,
            "tag": tag,
            "age_band": meaning.age_band,
            "life_area": meaning.area,
            "primary": meaning.primary,
            "secondary": meaning.secondary,
            "caution": meaning.caution,
            "direction": meaning.direction,
            "confidence": meaning.confidence,
            "claim_level": meaning.claim_level or default_claim_level("recognition"),
            "evidence_signature": list(meaning.evidence_signature),
        })
    return rows


def test_golden_fixtures_match_snapshot() -> None:
    for fx in FIXTURES:
        fid = fx["id"]
        expected = EXPECTED[fid]
        actual_rows = structured_rows(fid, fx["dob"])
        assert len(actual_rows) == len(expected)
        for act, exp in zip(actual_rows, expected):
            for key in ("domain", "tag", "life_area", "primary", "secondary"):
                assert act[key] == exp[key], (
                    f"{fid}/{exp['domain']}/{exp['tag']}: {key} "
                    f"expected {exp[key]!r} got {act[key]!r}"
                )
            assert act["age_band"] == age_band(_pc(fx["dob"]))
            assert act["claim_level"] >= 1
            assert act["evidence_signature"]


def test_teen_differs_from_adult_career() -> None:
    teen = build_meaning_for_tag("career", "career_stage", "teen", pc=_pc("2012-01-01"))
    adult = build_meaning_for_tag("career", "career_stage", "adult", pc=_pc("1986-03-08"))
    assert teen and adult
    assert teen.primary != adult.primary or teen.secondary != adult.secondary


def test_tag_evidence_coverage() -> None:
    for domain, tag in DOMAIN_TAGS:
        if tag != "floor":
            assert tag in TAG_EVIDENCE or tag == "floor", tag


def dump_snapshot() -> None:
    out = {}
    for fx in FIXTURES:
        rows = structured_rows(fx["id"], fx["dob"])
        out[fx["id"]] = [
            {k: r[k] for k in ("domain", "tag", "life_area", "primary", "secondary")}
            for r in rows
        ]
    print(json.dumps(out, indent=2))


def run_all() -> None:
    tests = [
        test_golden_fixtures_match_snapshot,
        test_teen_differs_from_adult_career,
        test_tag_evidence_coverage,
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
    print(f"All {len(tests)} golden structured tests passed.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--dump":
        dump_snapshot()
    else:
        run_all()
