"""Post-v10 report consistency regression tests."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))

import report_confluence as CF
from narration.verdict_phrases import overall_picture_phrase, proof_overall_line
from qa_checks.grammar_check import fix_grammar
from qa_checks.report_consistency import validate_report_consistency


def test_agreement_field_on_verdict():
    pc = {
        "meta": {"dob": "1986-03-08"},
        "planets": {"Mercury": {"house": 10, "sign": "Pisces", "dignity": "debilitated"}},
        "house_lords": {
            "1": {"lord": "Mars", "lord_house": 1},
            "6": {"lord": "Saturn", "lord_house": 6},
            "10": {"lord": "Mercury", "lord_house": 10},
        },
        "vimshottari": {
            "current_md": {"md_lord": "Saturn", "start": "2020-01-01", "end": "2039-01-01"},
            "current_md_antardashas": [
                {"ad_lord": "Mercury", "status": "current",
                 "start": "2024-01-01", "end": "2026-10-01"},
            ],
        },
        "ashtakavarga": {"sav": [28] * 12},
    }
    verdict = CF.build_confluence(pc, "health", 1)
    assert "agreement" in verdict
    assert verdict["agreement"] in ("weak", "partial", "strong", "conflicting")
    assert isinstance(verdict.get("secondary_confirmations"), list)


def test_down_direction_never_leans_supportive_headline():
    headline = overall_picture_phrase(
        direction="down",
        confidence="moderate",
        agreement="partial",
        support=2,
        caution=5,
    )
    assert "leans supportive" not in headline.lower()
    assert "mixed but leans supportive" not in headline.lower()
    assert "is strongly supportive" not in headline.lower()


def test_proof_overall_not_strong_agreement_on_down():
    line = proof_overall_line(direction="down", confidence="high", agreement="strong")
    assert "Strong agreement" not in line


def test_grammar_fix_mixed_phase():
    broken = "This is a a mixed phase."
    fixed = fix_grammar(broken)
    assert "a a" not in fixed


def test_secondary_confirmations_gated():
    pc = {
        "meta": {"dob": "1990-01-12"},
        "planets": {
            "Venus": {"house": 7, "sign": "Pisces", "dignity": "exalted"},
            "Moon": {"house": 4, "sign": "Cancer", "dignity": "own_sign"},
        },
        "house_lords": {
            "7": {"lord": "Venus", "lord_house": 7},
            "4": {"lord": "Moon", "lord_house": 4},
        },
        "vimshottari": {
            "current_md": {"md_lord": "Venus", "start": "2020-01-01", "end": "2040-01-01"},
            "current_md_antardashas": [
                {"ad_lord": "Moon", "status": "current",
                 "start": "2024-01-01", "end": "2026-10-01"},
            ],
        },
        "yogini": {
            "current_yogini": {
                "yogini": "Siddhi",
                "lord": "Venus",
                "tone": "auspicious",
                "start": "2024-01-01",
                "end": "2026-10-01",
            }
        },
        "ashtakavarga": {"sav": [28] * 12},
    }
    verdict = CF.build_confluence(pc, "love", 7)
    for entry in verdict.get("secondary_confirmations") or []:
        assert entry.get("planet")
        assert entry.get("method")


def test_no_raw_leaks_in_review_html():
    review = ROOT / "ci-storage" / "review_html"
    if not review.exists():
        return
    forbidden = [
        re.compile(r"recognition_tag_", re.I),
        re.compile(r"Combination\s+\d+", re.I),
        re.compile(r"\blandlord\b", re.I),
    ]
    for path in review.glob("*_paid.html"):
        if path.name.startswith("astro_full_report"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pat in forbidden:
            assert not pat.search(text), f"{path.name}: {pat.pattern}"


def test_consistency_linter_runs():
    html = "<p>The overall picture is more demanding right now.</p>"
    result = validate_report_consistency(html, verdicts=[{"direction": "down"}])
    assert "ok" in result
