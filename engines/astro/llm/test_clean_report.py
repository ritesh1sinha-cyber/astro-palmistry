"""Golden structural tests for the clean v2 life-area report (plan §33/§34).

Covers: exactly 8 canonical areas, no duplicate ids/checkpoints, sorted
checkpoints, no legacy section names, mandatory per-area fields, no raw LLM
HTML, exactly one collapsed calculation per area, same-date timing merged,
non-diagnostic health, fixed titles, final practical guidance present, and
the exact top-level DOM order.
"""
from __future__ import annotations

import re
from datetime import date

from llm.clean_report import (
    REPORT_SCHEMA_VERSION,
    ALLOWED_VERDICTS,
    CANONICAL_AREAS,
    CANONICAL_IDS,
    build_final_report,
    normalize_checkpoints,
    render_final_report,
    validate_final_html,
    validate_final_report,
)
from llm.schemas import LifeAreaJudgementFact, ReportFacts


def _judgement(area: str, final: str = "moderate", **kw) -> LifeAreaJudgementFact:
    fields = {
        "area": area,
        "label": area.title(),
        "house": 1,
        "final_judgement": final,
        "confluence_agreement": "good",
        "confluence_label": "Moderately supportive",
        "lane_judgements": {
            "Vimshottari": "mixed", "Chara": "moderate", "Yogini": "good",
            "Slow transit": "challenging", "Dasha-planet transit": "mixed",
            "Jaimini": "good",
        },
        "current_summary": (
            "Complete confluence for this area is currently moderate; natal "
            "foundation is mixed while timing cycles and slow transits are "
            "mixed. The final judgement remains moderate.")
    }
    fields.update(kw)
    return LifeAreaJudgementFact(**fields)


def _sample_analysis() -> ReportFacts:
    judgements = [
        _judgement("career", "mixed", house=10),
        _judgement("money", "moderate", house=2),
        _judgement("love", "challenging", house=7),
        _judgement("home", "moderate", house=4),
        _judgement("children", "good", house=5),
        _judgement("health", "mixed", house=6),
        _judgement("learning", "moderate", house=9),
        _judgement("inner", "mixed", house=8),
    ]
    # Same-month triggers (Chara + Yogini in December 2028) must merge.
    judgements[0].future_confluence = [
        _fc("2028-12-05", "continues", "mixed", dasha=["Chara: Moon"]),
        _fc("2028-12-19", "continues", "mixed", dasha=["Yogini: Venus"]),
        _fc("2027-06-12", "eases_but_continues", "moderate"),
    ]
    judgements[0].relief_window = "2027-06-12"
    judgements[0].stronger_window = "2030-04-01"
    return ReportFacts(access="paid", life_area_judgements=judgements)


def _fc(when, change_type, judgement, dasha=None):
    from llm.schemas import FutureConfluenceFact

    return FutureConfluenceFact(
        date=when, change_type=change_type, judgement=judgement,
        lane_judgements={}, dasha_changes=dasha or [],
        reason="complete confluence recalculation")


def _sample_prose() -> dict:
    return {
        "conversational": True,
        "current_phase": "A period of steady groundwork where several areas "
                         "are preparing to shift.",
        "why_now": "Timing cycles are turning over together.",
        "mind_now": ["Career direction", "Family plans"],
        "areas": {
            "career": {"conclusion": "The career situation is settling after "
                                     "a demanding stretch, with more support "
                                     "arriving gradually.", "remedy": "Keep "
                                     "focused on one clear goal at a time."},
            "money": {"conclusion": "Finances respond best to cautious, "
                                    "step-by-step planning at this time.",
                      "remedy": "Track spending and avoid major new debt."},
        },
        "final_guidance": [
            "Prioritise steady, visible progress in your career.",
            "Keep financial decisions conservative for now.",
            "Use the supportive windows for relationship work.",
        ],
    }


def _sample_report() -> dict:
    return build_final_report(
        pc={"lagna": {"sign": "Libra", "nakshatra": "Swati"},
            "planets": {"Moon": {"sign": "Taurus", "nakshatra": "Rohini"},
                        "Sun": {"sign": "Libra"}}},
        cards=[],
        analysis=_sample_analysis(),
        prose=_sample_prose(),
        today=date(2026, 8, 17),
        paid=True,
        name="Test")


def test_exactly_eight_canonical_areas():
    report = _sample_report()
    assert [a["id"] for a in report["areas"]] == CANONICAL_IDS
    assert len(report["areas"]) == 8


def test_no_duplicate_area_ids():
    report = _sample_report()
    ids = [a["id"] for a in report["areas"]]
    assert len(ids) == len(set(ids))


def test_no_duplicate_checkpoint_dates():
    report = _sample_report()
    for area in report["areas"]:
        keys = [c["when"] for c in area["calculation"]["checkpoints"]]
        assert len(keys) == len(set(keys)), area["id"]


def test_checkpoints_sorted_chronologically():
    report = _sample_report()
    for area in report["areas"]:
        keys = [c["when"] for c in area["calculation"]["checkpoints"]]
        assert keys == sorted(keys), area["id"]


def test_same_month_events_merged():
    report = _sample_report()
    career = next(a for a in report["areas"] if a["id"] == "work_career")
    decs = [c for c in career["calculation"]["checkpoints"] if c["when"] == "2028-12"]
    assert len(decs) == 1
    assert len(decs[0]["dasha"]) == 2  # Chara + Yogini merged into one row


def test_baseline_uses_actual_date():
    report = _sample_report()
    first = report["areas"][0]["calculation"]["checkpoints"][0]
    assert first["when"] == "2026-08"
    assert first["label"] == "Baseline"


def test_no_legacy_section_names_in_html():
    html = render_final_report(_sample_report())
    forbidden = ["About You", "Family & Home", "Recently", "Right Now",
                 "Your Current Chapter", "Year-by-Year Road Map",
                 "Top Challenges", "Remedies & Gemstones", "Chart-Targeted",
                 "15 different ways", "Combined answer",
                 "Method / sub-report", "Technical details"]
    low = html.lower()
    for phrase in forbidden:
        assert phrase.lower() not in low, phrase


def test_every_area_has_required_fields():
    report = _sample_report()
    for area in report["areas"]:
        assert area["id"] in CANONICAL_IDS
        assert area["verdict"] in ALLOWED_VERDICTS
        assert area["conclusion"].strip()
        assert area["timing"].strip()
        assert area["what_helps"].strip()
        calc = area["calculation"]
        assert calc["agreement"].strip()
        assert calc["current_state"].strip()
        assert isinstance(calc["lanes"], list)
        assert isinstance(calc["checkpoints"], list)


def test_no_unsupported_dates():
    # Free projection strips dates -> free timing must not invent any.
    report = build_final_report(
        pc={}, cards=[], analysis=_sample_analysis(), prose={},
        today=date(2026, 8, 17), paid=False, name="")
    for area in report["areas"]:
        assert "20" not in area["timing"].replace("2026", "").replace("now", "")


def test_no_raw_llm_html():
    report = _sample_report()
    for area in report["areas"]:
        for field in ("conclusion", "timing", "what_helps"):
            text = area[field]
            assert "<" not in text and ">" not in text, (area["id"], field)


def test_exactly_one_collapsed_calculation_per_area():
    html = render_final_report(_sample_report())
    assert html.count("<details") == 8
    assert "Astrological calculation &amp; future checkpoints" in html


def test_health_is_non_diagnostic():
    html = render_final_report(_sample_report())
    low = html.lower()
    for word in ("diagnosis", "cure", "medicine", "treatment", "recover"):
        assert word not in low


def test_no_arbitrary_life_area_titles():
    report = _sample_report()
    titles = [t for _, t in CANONICAL_AREAS]
    for area in report["areas"]:
        assert area["title"] in titles


def test_final_practical_guidance_exists():
    html = render_final_report(_sample_report())
    assert 'id="final-practical-guidance"' in html


def test_golden_dom_sequence():
    html = render_final_report(_sample_report())
    order = [
        'id="chart-signature"',
        'id="where-you-are-now"',
        'id="life-areas"',
        'id="area-work-career"',
        'id="area-money"',
        'id="area-relationships"',
        'id="area-children-family"',
        'id="area-health"',
        'id="area-property-home"',
        'id="area-travel-foreign"',
        'id="area-spiritual-inner"',
        'id="final-practical-guidance"',
    ]
    pos = -1
    for token in order:
        idx = html.find(token)
        assert idx != -1, token
        assert idx > pos, f"{token} out of order"
        pos = idx


def test_report_schema_version_attribute():
    html = render_final_report(_sample_report())
    assert f'data-report-schema="{REPORT_SCHEMA_VERSION}"' in html


def test_validate_final_report_passes():
    assert validate_final_report(_sample_report()) == []


def test_validate_final_html_passes():
    assert validate_final_html(render_final_report(_sample_report())) == []


def test_validate_catches_legacy_and_bad_order():
    html = render_final_report(_sample_report())
    # Move the where-you-are-now section ahead of chart-signature.
    wy = re.search(r'<section id="where-you-are-now".*?</section>', html, re.S)
    cs = re.search(r'<section id="chart-signature".*?</section>', html, re.S)
    assert wy and cs
    rest = html.replace(wy.group(0), "").replace(cs.group(0), "")
    html_bad = rest.replace('<section id="life-areas"', wy.group(0) + cs.group(0) + '<section id="life-areas"', 1)
    errors = validate_final_html(html_bad)
    assert errors  # reordering detected


def test_validate_report_catches_duplicate_ids():
    report = _sample_report()
    report["areas"] = [dict(report["areas"][0]) for _ in range(8)]
    assert validate_final_report(report) != []


def test_normalize_checkpoints_baseline_and_sort():
    rows = [
        _fc("2028-12-05", "continues", "mixed", dasha=["Chara: Moon"]),
        _fc("2027-06-12", "eases_but_continues", "moderate"),
    ]
    out = normalize_checkpoints(rows, date(2026, 8, 17), "MIXED")
    assert out[0]["when"] == "2026-08"
    assert [r["when"] for r in out] == ["2026-08", "2027-06", "2028-12"]


def test_timing_fallback_when_no_data():
    report = build_final_report(
        pc={}, cards=[], analysis=_sample_analysis(), prose={},
        today=date(2026, 8, 17), paid=False, name="")
    assert report["areas"][0]["timing"]


def test_free_report_has_unlock_cta():
    html = render_final_report(build_final_report(
        pc={}, cards=[], analysis=_sample_analysis(), prose={},
        today=date(2026, 8, 17), paid=False, name=""))
    assert "unlock" in html.lower()