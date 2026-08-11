"""Confluence presentation v10 — qualitative headlines and confidence source."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))

FORBIDDEN_HTML = [
    re.compile(r"recognition_tag_", re.I),
    re.compile(r"Combination\s+\d+", re.I),
    re.compile(r"\blandlord\b", re.I),
    re.compile(r"successful in politics", re.I),
    re.compile(r"chronic or serious illness", re.I),
    re.compile(r"cusp sub lord", re.I),
    re.compile(r"when illness flares", re.I),
    re.compile(r"reproductive and excretory", re.I),
]

REVIEW_DIRS = (
    ROOT / "ci-storage" / "review_html",
    ROOT / "ci-storage" / "oversample",
)


def _minimal_pc() -> dict:
    return {
        "meta": {"dob": "1986-03-08", "tob": "13:00"},
        "planets": {
            "Mercury": {"house": 10, "sign": "Pisces"},
            "Mars": {"house": 6, "sign": "Scorpio"},
            "Saturn": {"house": 6, "sign": "Scorpio"},
            "Jupiter": {"house": 2, "sign": "Gemini"},
        },
        "house_lords": {
            "1": {"lord": "Mars", "lord_house": 1},
            "2": {"lord": "Mercury", "lord_house": 10},
            "4": {"lord": "Mercury", "lord_house": 10},
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
        "ashtakavarga": {
            "sav": [28] * 12,
            "bav": {p: [4] * 12 for p in [
                "Sun", "Moon", "Mars", "Mercury", "Jupiter",
                "Venus", "Saturn", "Rahu", "Ketu",
            ]},
        },
    }


def _overall_picture_phrase(cf: dict) -> str:
    from narration.verdict_phrases import overall_picture_phrase
    return overall_picture_phrase(
        direction=str(cf.get("direction") or "mixed"),
        confidence=str(cf.get("verdict") or cf.get("confidence") or ""),
        agreement=str(cf.get("agreement") or ""),
        support=int(cf.get("support") or 0),
        caution=int(cf.get("caution") or 0),
    )


def test_overall_picture_not_raw_count_headline() -> None:
    from report_cards import _build_confluence

    cf = _build_confluence("health", 1, _minimal_pc())
    assert cf.get("rows"), "expected confluence rows"
    headline = _overall_picture_phrase(cf)
    assert headline.startswith("The overall picture")
    assert "systems support this" not in headline


def test_build_confluence_confidence_not_from_row_counts() -> None:
    import report_confluence as CF
    from report_cards import _build_confluence

    pc = _minimal_pc()
    verdict = CF.area_verdict(pc, "health", 1)
    presentation = _build_confluence("health", 1, pc)
    assert verdict.get("confidence") in ("very high", "high", "moderate", "low")
    assert isinstance(verdict.get("families") or [], list)
    assert verdict.get("confidence") != str(presentation.get("total") or "")


def test_confluence_headline_is_qualitative() -> None:
    from report_cards import _build_confluence

    cf = _build_confluence("money", 2, _minimal_pc())
    cf["direction"] = "up"
    cf["verdict"] = "high"
    cf["support"] = 3
    cf["caution"] = 1
    headline = _overall_picture_phrase(cf)
    assert "The overall picture" in headline
    assert "3 support" not in headline


def test_generated_html_has_no_raw_leaks() -> None:
    """Scan checked-in review HTML when present (Docker CI output)."""
    files = []
    for d in REVIEW_DIRS:
        if d.is_dir():
            files.extend(sorted(d.glob("*_paid.html")))
    # Ignore generic template reports; focus on named oversample charts.
    files = [p for p in files if not p.name.startswith("astro_full_report")]
    if not files:
        return
    for path in files:
        body = re.sub(r"<style>.*?</style>", "", path.read_text(encoding="utf-8"), flags=re.S)
        for pat in FORBIDDEN_HTML:
            assert not pat.search(body), f"{path.name}: forbidden leak {pat.pattern}"


def test_saturn_delay_requires_delay_indicator() -> None:
    from interpretation.stage_config import evidence_atoms

    atoms_mixed = evidence_atoms(10, "Saturn", direction="mixed")
    assert "Saturn_influence" in atoms_mixed
    assert "delay_indicator" not in atoms_mixed

    atoms_down = evidence_atoms(10, "Saturn", direction="down")
    assert "delay_indicator" in atoms_down


def test_canonical_confidence_uses_families_not_method_rows() -> None:
    from report_confluence import Vote, build_confluence

    votes = [
        Vote("the classical method", 2.0, "strong"),
        Vote("the nadi method", 1.5, "support"),
        Vote("the sub-lord method", 1.5, "support"),
        Vote("the karaka method", 1.5, "support"),
        Vote("the sky right now", -1.2, "pressure"),
    ]
    r = build_confluence({}, "career", 10, raw_votes=votes)
    assert len(r["families"]) < len(votes)
    assert r["confidence"] in ("very high", "high", "moderate", "low")
