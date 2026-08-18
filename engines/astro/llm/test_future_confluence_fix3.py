from datetime import date

from llm.facts import _future_transition_summary
from llm.schemas import FutureConfluenceFact
from report_conversational import _analytical_html


def _fc(d, change, judgement, prev="insufficient", lanes=None):
    return FutureConfluenceFact(
        date=d,
        change_type=change,
        previous_judgement=prev,
        judgement=judgement,
        agreement="good",
        vimshottari="Jupiter-Ketu",
        chara="Aquarius-Pisces",
        yogini="Bhadrika",
        lane_judgements=lanes or {
            "Vimshottari": "moderate",
            "Chara": "good",
            "Yogini": "good",
            "Slow transit": "challenging",
            "Dasha-planet transit": "mixed",
            "Jaimini": "good",
        },
    )


def test_no_automatic_good_from_dasha_change():
    rows = [
        _fc("2026-08-17", "baseline", "moderate"),
        _fc("2027-02-10", "continues", "moderate", "moderate"),
    ]
    easing, good, horizon = _future_transition_summary(rows, date(2026, 8, 17))
    assert easing == ""
    assert good == ""
    assert "remains Moderate" in horizon


def test_sustained_good_requires_two_checkpoints():
    rows = [
        _fc("2026-08-17", "baseline", "moderate"),
        _fc("2027-02-10", "improves", "good", "moderate"),
        _fc("2027-04-01", "worsens", "moderate", "good"),
    ]
    easing, good, _ = _future_transition_summary(rows, date(2026, 8, 17))
    assert easing == "2027-02-10"
    assert good == ""


def test_renderer_contains_future_complete_confluence_and_lanes():
    fc = _fc("2027-02-10", "eases_but_continues", "moderate", "moderate")
    data = {
        "timing_systems": [], "crossover_points": [], "slow_transits": [],
        "jaimini": {}, "dasha_planet_transits": [],
        "life_area_judgements": [{
            "area": "career", "label": "Work & Career", "house": 10,
            "natural_karakas": ["Sun"], "house_lord": "Mercury",
            "divisional_chart": "D10", "divisional_verdict": "Supported",
            "amk": "Jupiter", "final_judgement": "moderate",
            "confluence_score": 0.12, "confluence_agreement": "good",
            "lane_judgements": fc.lane_judgements,
            "current_summary": "Complete confluence is moderate.",
            "future_summary": "Future confluence is recalculated.",
            "future_confluence": [fc.model_dump()],
        }],
    }
    html = _analytical_html(data, paid=True, today=date(2026, 8, 17))
    assert "Future complete-confluence forecast" in html
    assert "February 2027" in html
    assert "Jaimini: good" in html


def test_free_projection_removes_future_paid_timing():
    from llm.facts import project_for_access
    from llm.schemas import LifeAreaJudgementFact, ReportFacts

    facts = ReportFacts(access="paid", life_area_judgements=[
        LifeAreaJudgementFact(
            area="career", final_judgement="moderate",
            relief_window="2027-02-10", stronger_window="2027-04-01",
            future_confluence=[_fc("2027-02-10", "improves", "good")],
        )
    ])
    free = project_for_access(facts, "free")
    area = free.life_area_judgements[0]
    assert area.future_confluence == []
    assert area.relief_window == ""
    assert area.stronger_window == ""


def _mini(judgement_fields=None, timing=None):
    from llm.schemas import LifeAreaJudgementFact, ReportFacts

    fields = {"area": "career", "final_judgement": "moderate"}
    if judgement_fields:
        fields.update(judgement_fields)
    return ReportFacts(life_area_judgements=[LifeAreaJudgementFact(**fields)],
                       timing_windows=timing or [])


def test_area_dates_grounded_allows_only_fact_dates():
    from llm.validate import validate_area_dates_grounded

    mini = _mini({"relief_window": "2027-11-11",
                  "stronger_window": "2028-02-29",
                  "future_confluence": [_fc("2027-11-11", "eases_but_continues", "moderate"),
                                        _fc("2028-02-29", "mixed_change", "moderate")]})
    assert validate_area_dates_grounded("Better by Nov 2027 after Feb 2028 eases.",
                                        mini) == []
    bad = validate_area_dates_grounded("Strain till Nov 2027, better by Jan 2030.",
                                       mini)
    assert any("Jan 2030" in p for p in bad)


def test_area_dates_grounded_rejects_any_date_with_no_window():
    from llm.validate import validate_area_dates_grounded

    mini = _mini()  # baseline-only / no dated window
    assert validate_area_dates_grounded("No clear relief window yet.", mini) == []
    assert validate_area_dates_grounded("Better by Jan 2030.", mini) == [
        "ungrounded_date_no_window"]


def test_area_dates_grounded_timing_window_falls_back():
    from llm.schemas import WindowFact
    from llm.validate import validate_area_dates_grounded

    mini = _mini(timing=[WindowFact(start="2027-06-01", end="2027-08-31", label="w")])
    assert validate_area_dates_grounded("June 2027", mini) == []
    assert validate_area_dates_grounded("Dec 2027", mini) != []
