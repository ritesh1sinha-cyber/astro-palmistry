"""Regression: travel dropdown must not route user questions to health."""
from __future__ import annotations

import re

from confluence_question_engine import (
    DOMAINS_CONFIG,
    _resolve_confluence_domain,
    analyze_question_confluence,
)
import semantic_question as SQ


QUESTION = "will i shift to foreign country"


def test_dropdown_travel_maps_to_foreign_relocation():
    area = SQ.normalize_area("travel")
    assert area == "travel"
    key = _resolve_confluence_domain(QUESTION, domain_override=area)
    assert key == "foreign_relocation", key


def test_no_dropdown_still_detects_foreign():
    key = _resolve_confluence_domain(QUESTION, domain_override="")
    assert key == "foreign_relocation", key


def test_travel_not_used_as_raw_domains_config_key():
    """Old bug: domain_override='travel' hit DOMAINS_CONFIG default → health."""
    cfg = DOMAINS_CONFIG.get("travel")
    assert cfg is None
    key = _resolve_confluence_domain(QUESTION, domain_override="travel")
    assert key == "foreign_relocation"
    assert DOMAINS_CONFIG[key]["title"].startswith("Foreign Settlement")


def test_analyze_with_route_pins_foreign_title():
    route = SQ.route(QUESTION, area="travel")
    assert route.domain == "travel"
    assert route.primary_house == 9

    pc = {
        "lagna": {"sign": "Gemini"},
        "planets": {
            "Moon": {"sign": "Virgo", "nakshatra": "Hasta", "pada": 1, "house": 4},
            "Mars": {"sign": "Aries", "house": 11},
        },
        "meta": {},
    }
    conf = analyze_question_confluence(pc, QUESTION, domain_override="travel", route=route)
    assert conf.domain_key == "foreign_relocation"
    assert "Foreign Settlement" in conf.domain_title
    assert "Health, Physical Vitality" not in conf.domain_title


def test_rendered_life_domain_label():
    from report_render import user_question
    import deep_evidence as DE

    try:
        from astro_precompute import resolve_precompute
        pc = resolve_precompute(
            "Test", "1990-06-15", birth_time="10:30",
            latitude=28.6139, longitude=77.2090, timezone=5.5,
            place_name="New Delhi", gender=0,
        )
    except Exception as exc:
        raise RuntimeError(f"chart fixture unavailable: {exc}") from exc

    area = SQ.normalize_area("travel")
    route = SQ.route(QUESTION, area=area)
    DE.begin(pc, lat=28.61, lon=77.20, tz=5.5)
    try:
        _free, paid, meta = user_question(
            pc, question=QUESTION, route=route, area=area, name="Test",
            price=298, lat=28.61, lon=77.20, tz=5.5,
        )
    finally:
        DE.end()

    assert "Foreign Settlement" in meta["area"]
    assert 'class="uq-reading"' in paid, "missing the question answer card"
    reading = paid.split('class="uq-reading"', 1)[1]
    assert "Health, Physical Vitality" not in reading
    assert "Lal Kitab" not in reading and "Chandra Naadi" not in reading


if __name__ == "__main__":
    test_dropdown_travel_maps_to_foreign_relocation()
    print("OK  dropdown travel → foreign_relocation")
    test_no_dropdown_still_detects_foreign()
    print("OK  no dropdown still foreign")
    test_travel_not_used_as_raw_domains_config_key()
    print("OK  travel not raw DOMAINS_CONFIG key")
    test_analyze_with_route_pins_foreign_title()
    print("OK  analyze_question_confluence domain title")
    test_rendered_life_domain_label()
    print("OK  full user_question HTML Life Domain")
    print("ALL travel area routing tests passed")
