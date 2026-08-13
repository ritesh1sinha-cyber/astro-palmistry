"""Customer text sanitizer — raw evidence must not reach HTML."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))


def test_sanitize_rejects_internal_tags() -> None:
    from qa_checks.customer_text_sanitizer import sanitize_customer_text

    out = sanitize_customer_text(
        "recognition_tag_love_venus_strong",
        method_label="Recognition",
        direction="support",
        area="love",
    )
    assert "recognition_tag" not in out.lower()


def test_sanitize_rejects_combination_and_book_text() -> None:
    from qa_checks.customer_text_sanitizer import sanitize_customer_text

    combo = sanitize_customer_text(
        "Combination 37 (Mars-Saturn in Scorpio, house 6): book themes applied to your D1 chart.",
        method_label="Nadi method",
        direction="support",
        area="home",
    )
    assert "combination 37" not in combo.lower()
    assert "book themes" not in combo.lower()

    book = sanitize_customer_text(
        "You will be a landlord, successful in politics, popular among people.",
        method_label="Case-book method",
        direction="support",
        area="home",
    )
    assert "landlord" not in book.lower()
    assert "politics" not in book.lower()


def test_sanitize_health_uses_wellbeing_language() -> None:
    from qa_checks.customer_text_sanitizer import sanitize_customer_text

    out = sanitize_customer_text(
        "If the 6th cusp sub lord signifies houses 6, 8, and/or 12, "
        "chronic or serious illness tendency is indicated.",
        method_label="Sub-lord method",
        direction="caution",
        area="health",
    )
    assert "illness tendency" not in out.lower()
    assert "cusp sub lord" not in out.lower()
    assert "routine" in out.lower() or "wellbeing" in out.lower() or "rest" in out.lower()


def test_why_safety_strips_recognition_tags_from_trace() -> None:
    from qa_checks.why_safety_check import safe_why_text

    class _Meaning:
        area = "love"
        narrative_area = "love"
        evidence_trace = [
            "7th house",
            "Venus",
            "adult age band",
            "recognition_tag_love_venus_strong",
        ]

    why = safe_why_text("", band="adult", meaning=_Meaning())
    assert "recognition_tag" not in (why or "").lower()


def test_build_confluence_sanitizes_reasons() -> None:
    from report_cards import _build_confluence

    pc = {
        "meta": {"dob": "1986-03-08", "tob": "13:00"},
        "planets": {
            "Mercury": {"house": 10, "sign": "Pisces"},
            "Mars": {"house": 6, "sign": "Scorpio"},
            "Saturn": {"house": 6, "sign": "Scorpio"},
        },
        "house_lords": {
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
        "ashtakavarga": {"sav": [28] * 12, "bav": {p: [4] * 12 for p in [
            "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]}},
    }
    cf = _build_confluence("home", 4, pc)
    blob = " ".join(
        r["reasons"][0] for r in (cf.get("rows") or []) if r.get("reasons")
    ).lower()
    assert "landlord" not in blob
    assert "combination" not in blob
    assert "recognition_tag" not in blob


def test_grounded_astrology_survives_finalize_customer_html() -> None:
    from qa_checks.final_customer_boundary import finalize_customer_html
    from qa_checks.customer_text_sanitizer import validate_customer_text

    ok = (
        "<p>You are in a Jupiter mahadasha. Saturn's influence on the 10th "
        "house is making progress more responsibility-driven.</p>"
    )
    out = finalize_customer_html(ok)
    assert "mahadasha" in out.lower()
    assert "10th house" in out.lower()
    assert "saturn" in out.lower()
    assert not validate_customer_text(out)

    dirty = "<p>The sub-lord and karakamsa strongly support this.</p>"
    cleaned = finalize_customer_html(dirty)
    assert "sub-lord" not in cleaned.lower()
    assert "karakamsa" not in cleaned.lower()
