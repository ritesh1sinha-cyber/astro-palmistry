"""Promise / personalized confluence regression tests."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))

import deep_evidence as DE
import report_confluence as CF
from personalized_confluence import (
    canonical_area,
    clear_promise_cache,
    resolve_all_promises,
    resolve_promise,
)
from prediction108_rules import RuleVerdict


def _synthetic_pc() -> dict:
    planets = {
        "Sun": {"sign": "Aries", "house": 10, "navamsha_sign": "Aries"},
        "Moon": {"sign": "Taurus", "house": 2, "navamsha_sign": "Taurus"},
        "Mars": {"sign": "Capricorn", "house": 7, "navamsha_sign": "Capricorn"},
        "Mercury": {"sign": "Virgo", "house": 10, "navamsha_sign": "Virgo"},
        "Jupiter": {"sign": "Cancer", "house": 5, "navamsha_sign": "Cancer"},
        "Venus": {"sign": "Pisces", "house": 7, "navamsha_sign": "Pisces"},
        "Saturn": {"sign": "Libra", "house": 10, "navamsha_sign": "Libra"},
        "Rahu": {"sign": "Gemini", "house": 3, "navamsha_sign": "Gemini"},
        "Ketu": {"sign": "Sagittarius", "house": 9, "navamsha_sign": "Sagittarius"},
    }
    signs = [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    ]
    lord = {
        "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
        "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
        "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
        "Pisces": "Jupiter",
    }
    house_lords = {str(i): {"lord": lord[signs[i - 1]]} for i in range(1, 13)}
    divisional = {}
    for code in ("D2", "D3", "D4", "D7", "D9", "D10", "D12", "D20", "D24", "D27", "D30"):
        divisional[code] = {"Lagna": "Aries", **{p: d["sign"] for p, d in planets.items()}}
    return {
        "chart_hash": "promise-test",
        "planets": planets,
        "house_lords": house_lords,
        "divisional": divisional,
        "lagna": {"sign": "Aries"},
        "meta": {"lagna_sign": "Aries", "dob": "1990-01-15"},
    }


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_promise_cache()
    DE.end()
    yield
    clear_promise_cache()
    DE.end()


def test_all_core_areas_return_promise_object():
    pc = _synthetic_pc()
    out = resolve_all_promises(pc)
    for key in ("spouse", "children", "profession", "wealth"):
        assert key in out
        assert out[key]["status"] in {
            "strongly_supported", "supported", "mixed", "weak", "insufficient_evidence",
        }
        assert "timing_allowed" in out[key]
    # troubles is a challenge-pattern area (D30): it must never use promise
    # vocabulary such as "strongly_supported" — that would read as illness
    # being promised.
    assert "troubles" in out
    assert out["troubles"]["kind"] == "challenge"
    assert out["troubles"]["status"] in {
        "strongly_indicated", "indicated", "mixed", "weak", "insufficient_evidence",
    }
    assert "timing_allowed" in out["troubles"]


def test_product_area_aliases_map():
    pc = _synthetic_pc()
    for product_key in ("career", "money", "love", "home", "children", "health", "learning", "inner"):
        p = resolve_promise(pc, product_key)
        assert p["area"] == canonical_area(product_key)
        assert p["area"] in {
            "profession", "wealth", "spouse", "home", "children",
            "troubles", "education", "spiritual",
        }
        assert "timing_allowed" in p


def test_promise_has_no_timing_dependency():
    pc = _synthetic_pc()
    a = resolve_promise(pc, "profession")
    pc["vimshottari"] = {"current_md": {"md_lord": "Saturn"}}
    pc["transits"] = {"Jupiter": {"house": 10}}
    b = resolve_promise(pc, "profession")
    assert a["status"] == b["status"]
    assert a["score"] == b["score"]


def test_unknown_area_fallback_has_timing_allowed():
    p = resolve_promise(_synthetic_pc(), "nonexistent_area_xyz")
    assert p["status"] == "insufficient_evidence"
    assert p["timing_allowed"] is False
    assert p["promise_only"] is True


def test_neutral_rules_not_scored_as_caution():
    pc = _synthetic_pc()
    neutral = RuleVerdict(
        1, "Neutral career rule", "career", "test",
        "HIT", "Mercury in the tenth house", "A neutral career observation",
    )

    def fake_verdicts(_pc):
        return [neutral]

    with patch("personalized_confluence._cached_rule_verdicts", fake_verdicts):
        with patch("final_user_report._classify_rule", return_value=None):
            score, support, caution = __import__(
                "personalized_confluence", fromlist=["_rule_family"]
            )._rule_family(pc, "profession")
    assert score == 0.0
    assert support == []
    assert caution == []


def test_build_confluence_includes_promise():
    pc = _synthetic_pc()
    verdict = CF.build_confluence(pc, "love", 7)
    promise = verdict.get("promise") or {}
    assert promise.get("area") == "spouse"
    assert promise.get("status")
    assert "timing_allowed" in promise


def test_evaluate_all_runs_once_with_deep_evidence_cache():
    pc = _synthetic_pc()
    calls = {"n": 0}

    def counting_eval(_pc):
        calls["n"] += 1
        return []

    DE.begin(pc)
    with patch("prediction108_rules.evaluate_all", side_effect=counting_eval):
        resolve_promise(pc, "career")
        resolve_promise(pc, "money")
        resolve_promise(pc, "love")
    assert calls["n"] == 1


def test_promise_phrase_cross_cases():
    from narration.verdict_phrases import promise_phrase

    assert "not strongly activated" in promise_phrase(
        status="supported", direction="down")
    assert "underlying promise" in promise_phrase(
        status="weak", direction="up")


def test_promise_memoized_per_chart():
    pc = _synthetic_pc()
    calls = {"n": 0}
    original = resolve_promise.__wrapped__ if hasattr(resolve_promise, "__wrapped__") else None

    def counting_rule(pc_in, key, kind="promise"):
        calls["n"] += 1
        return 0.0, [], []

    with patch("personalized_confluence._rule_family", side_effect=counting_rule):
        resolve_promise(pc, "career")
        resolve_promise(pc, "career")
    assert calls["n"] == 1
