"""KP horary judge: never ship an unsupported yes, and keep the answer plain."""
from __future__ import annotations

import re
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from llm.horary_judge import (  # noqa: E402
    _PLANET_NAMED,
    _contradicts_timing,
    _dasha_periods,
    _fallback_plain,
    _has_date,
    label_gloss,
    plain_remedy,
    _looks_yes_no,
    _majors,
    _sanitise,
    blocking_planet,
    classify_ask,
    judgement_as_verdict,
    kp_timing,
    quantity_answer,
    timing_sentence,
)
from llm.schemas import HoraryJudgement  # noqa: E402

# Moon at 213.83° sidereal = Anuradha (Saturn star), barely into the nakshatra.
_ASKED = "2026-09-14"
_DATA = {"planets": {"Moon": {"sidereal_lon": 213.83}},
         "meta": {"q_date": _ASKED}}
_EV = {"list_c": ["Jupiter", "Saturn"],
       "list_a": ["Jupiter", "Saturn", "Mars"],
       "ruling_planets": ["Saturn"]}


def test_when_question_is_not_yes_no():
    assert _looks_yes_no("when will I get the job") is False
    assert _looks_yes_no("will I get the job") is True


def test_sanitise_blocks_yes_on_a_when_question():
    plan = HoraryJudgement(
        restated_intent="timing of a job",
        in_scope=True,
        is_yes_no=False,
        label="yes",
        confidence="good",
        reason="ignored",
    )
    out = _sanitise(plan, {"fav_hits": ["10"], "den_hits": []},
                    "when will I get the job")
    assert out.label != "yes"
    assert out.label == "open"


def test_sanitise_blocks_yes_when_denying_and_no_favour():
    plan = HoraryJudgement(
        restated_intent="will I get it",
        in_scope=True,
        is_yes_no=True,
        label="yes",
        confidence="good",
        reason="ignored",
    )
    out = _sanitise(plan, {"fav_hits": [], "den_hits": ["6", "8"]},
                    "will I get the promotion")
    assert out.label == "no"


def test_verdict_maps_out_of_scope():
    plan = HoraryJudgement(
        restated_intent="python list",
        in_scope=False,
        is_yes_no=False,
        label="out_of_scope",
        confidence="low",
        reason="not astrology",
    )
    v = judgement_as_verdict(plan)
    assert v["out_of_domain"] is True
    assert v["verdict"] == "out_of_domain"


def test_dasha_periods_are_contiguous_and_start_before_the_question():
    ps = _dasha_periods(213.83, date.fromisoformat(_ASKED))
    assert ps, "expected a dasha chain"
    # The running period began before the question was asked.
    assert ps[0]["start"] < date.fromisoformat(_ASKED) < ps[0]["end"]
    for a, b in zip(ps, ps[1:]):
        assert a["end"] == b["start"]


def test_a_moon_late_in_its_nakshatra_does_not_restart_the_chain():
    # 224° is deep into Anuradha, so the first live sub-period must not be the
    # first one in the sequence.
    ps = _dasha_periods(224.0, date.fromisoformat(_ASKED))
    assert (ps[0]["md"], ps[0]["ad"]) != ("Saturn", "Saturn")


def test_timing_names_a_month():
    w = kp_timing(_DATA, _EV, horizon_years=40)
    assert w["window"][:3].isalpha() and w["window"][4:].isdigit()


def test_antara_durations_match_the_books_mars_rahu_table():
    """Book p.70 lists the antaras of the Mars dasa / Rahu bukti and their
    end dates. The lord order and each antara's length must reproduce them.

    53.4° is the start of Mrigashira, a Mars star, so Mars dasa runs first.
    """
    # Lengths are the gaps between consecutive end dates in the book's table:
    # Saturn 18/11/24, Mercury 12/01/25, Ketu 04/02/25, Venus 07/04/25,
    # Sun 26/04/25, Moon 27/05/25, Mars 19/06/25. Saturn's own length is not
    # derivable — the rows above it had already elapsed.
    book = [("Mercury", 55), ("Ketu", 23), ("Venus", 62), ("Sun", 19),
            ("Moon", 31), ("Mars", 23)]
    ps = [p for p in _dasha_periods(53.4, date.fromisoformat(_ASKED))
          if p["md"] == "Mars" and p["ad"] == "Rahu"]
    assert [p["pd"] for p in ps] == ["Rahu", "Jupiter", "Saturn", "Mercury",
                                     "Ketu", "Venus", "Sun", "Moon", "Mars"]
    by_lord = {p["pd"]: p for p in ps}
    for lord, days in book:
        got = (by_lord[lord]["end"] - by_lord[lord]["start"]).days
        assert abs(got - days) <= 2, f"{lord}: {got}d vs book {days}d"


def test_timing_follows_the_books_distinct_lord_rule():
    """Procedure 3.4: bukti lord differs from dasa lord, antara lord from
    both, and all three sit in List C."""
    every = {"list_c": ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                        "Saturn", "Rahu", "Ketu"]}
    w = kp_timing(_DATA, every)
    assert w["ad"] != w["md"]
    assert w["pd"] not in (w["md"], w["ad"])


def test_timing_uses_the_running_dasa_when_its_lord_is_in_list_c():
    # The book takes the current Mars dasa because Mars is a common planet;
    # it does not skip ahead to a later one.
    every = {"list_c": ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                        "Saturn", "Rahu", "Ketu"]}
    running = next(m for m in _majors(213.83, date.fromisoformat(_ASKED))
                   if m["start"] <= date.today() < m["end"])
    assert kp_timing(_DATA, every)["md"] == running["lord"]


_ALL = {"list_c": ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                   "Saturn", "Rahu", "Ketu"]}
_LONS = (5.0, 53.4, 100.0, 213.83, 224.0, 226.0, 300.0, 355.0)


def _chart(lon: float) -> dict:
    return {"planets": {"Moon": {"sidereal_lon": lon}},
            "meta": {"q_date": _ASKED}}


def test_exclude_running_never_dates_a_period_already_under_way():
    for lon in _LONS:
        w = kp_timing(_chart(lon), _ALL, exclude_running=True)
        assert w["starts"] > date.today(), f"moon {lon}: {w}"


def test_the_book_rule_by_contrast_will_date_the_running_period():
    live = [lon for lon in _LONS
            if kp_timing(_chart(lon), _ALL)["starts"] <= date.today()]
    assert live, "3.4 dates the period already running when its lords qualify"


def test_timing_skips_a_dasa_whose_lord_is_not_a_significator():
    # Anuradha Moon => Saturn dasa is running. Exclude Saturn and the window
    # must move into the next major, not stay inside Saturn's.
    w = kp_timing(_DATA, {"list_c": ["Mercury", "Ketu", "Venus"]},
                  horizon_years=40)
    assert w["md"] != "Saturn"


def test_timing_is_empty_without_a_moon():
    assert kp_timing({"meta": {"q_date": _ASKED}}, _EV) == {}


def test_timing_window_lords_are_all_in_list_c():
    w = kp_timing(_DATA, _EV, horizon_years=40)
    assert {w["md"], w["ad"], w["pd"]} - {""} <= set(_EV["list_c"])


def test_a_two_planet_list_c_widens_to_the_bukti_instead_of_refusing():
    # Three distinct lords cannot come out of a two-planet List C, so the
    # answer falls back to the wider period rather than giving no date.
    w = kp_timing(_DATA, {"list_c": ["Jupiter", "Saturn"]}, horizon_years=40)
    assert w["level"] == "bukti"
    assert w["pd"] == "" and w["ad"] and w["md"]


def test_blocking_planet_prefers_a_weak_significator_when_denied():
    ev = {"den_hits": ["6"], "list_a": ["Saturn", "Jupiter"],
          "list_c": ["Jupiter"], "cusp_sub_lord": "Sun"}
    assert blocking_planet(ev) == "Saturn"


def test_blocking_planet_falls_back_to_the_sub_lord():
    ev = {"den_hits": [], "list_a": ["Jupiter"], "list_c": ["Jupiter"],
          "cusp_sub_lord": "Sun"}
    assert blocking_planet(ev) == "Sun"


def test_fallback_answer_is_three_plain_sentences():
    out = _fallback_plain("when will I change jobs", "conditional",
                          {"window": "Jul-2027"}, "Put it in writing.")
    assert "Jul-2027" in out.timing
    assert out.remedy == "Put it in writing."
    body = f"{out.answer} {out.timing} {out.remedy}".lower()
    for jargon in ("sub-lord", "cusp", "significator", "dasha", "lagna",
                   "nakshatra", "house"):
        assert jargon not in body


def test_fallback_drops_timing_when_there_is_no_window():
    out = _fallback_plain("will I get it", "no", {}, "")
    assert out.timing == ""


def _soon(days: int) -> dict:
    start = date.today() + timedelta(days=days)
    return {"window": start.strftime("%b-%Y"), "until": "Oct-2026",
            "level": "antara", "starts": start,
            "ends": start + timedelta(days=20), "days_away": days}


def test_a_window_days_away_is_dated_to_the_day_not_the_month():
    text = timing_sentence(_soon(6))
    assert "Sep-2026" not in text
    assert re.search(r"\d{1,2} \w{3}", text), text
    assert " 0" not in text, f"zero-padded day: {text}"


def test_a_distant_window_still_reads_as_a_month():
    far = {"window": "Jul-2027", "until": "Sep-2027", "level": "antara",
           "starts": date(2027, 7, 1), "ends": date(2027, 9, 1),
           "days_away": 290}
    assert timing_sentence(far) == ("The next likely opening is around "
                                    "Jul-2027.")


def test_the_verdict_does_not_say_not_soon_above_a_window_next_week():
    gloss = label_gloss("conditional", _soon(6))
    assert "soon" not in gloss.lower()
    assert "no clear sign" not in gloss.lower()


def test_the_verdict_may_say_not_soon_when_the_window_really_is_far():
    far = {"window": "Jul-2029", "days_away": 1020, "level": "antara"}
    assert "soon" in label_gloss("conditional", far).lower()


def test_a_model_answer_that_fights_the_near_window_is_replaced():
    assert _contradicts_timing("There is no clear sign of this happening "
                               "soon.", _soon(6))
    assert not _contradicts_timing("You may well recover.", _soon(6))
    # Far window: the same sentence is honest, so leave it alone.
    assert not _contradicts_timing("There is no clear sign of this soon.",
                                   {"window": "Jul-2029", "days_away": 1020})


def test_a_window_past_the_horizon_is_reported_as_no_clear_opening():
    # Anuradha Moon: Saturn dasa runs, and List C here forces the walk into a
    # far-off major rather than a usable one.
    w = kp_timing(_DATA, {"list_c": ["Mercury", "Ketu", "Venus"]},
                  horizon_years=5)
    assert w["beyond_horizon"] is True
    assert "window" not in w
    text = timing_sentence(w)
    assert text == "The chart does not mark out a clear window for this."
    # No horizon count: "no opening in five years" alarms a health querent.
    assert "year" not in text


def test_a_generous_horizon_still_returns_the_real_window():
    w = kp_timing(_DATA, {"list_c": ["Mercury", "Ketu", "Venus"]},
                  horizon_years=40)
    assert not w.get("beyond_horizon")
    assert w["window"]


def test_a_wide_fallback_window_is_stated_as_a_span_not_a_month():
    narrow = timing_sentence({"window": "Jul-2027", "until": "Sep-2027",
                              "level": "antara"})
    wide = timing_sentence({"window": "Jul-2027", "until": "Mar-2030",
                            "level": "bukti"})
    assert narrow == "The next likely opening is around Jul-2027."
    assert "Jul-2027" in wide and "Mar-2030" in wide


def test_percentage_and_amount_questions_are_quantity():
    for q in ("how much percentage hike i will get this year",
              "how much hike will i get", "what percentage raise",
              "how many lakhs will i get", "what is the amount",
              "how big will the bonus be", "what salary can i expect"):
        assert classify_ask(q) == "quantity", q


def test_how_much_longer_is_timing_not_quantity():
    for q in ("how much longer will this take", "how much time is left",
              "how many months until it clears"):
        assert classify_ask(q) == "timing", q


def test_the_other_question_kinds_still_classify():
    assert classify_ask("when will i get married") == "timing"
    assert classify_ask("how soon can i move") == "timing"
    assert classify_ask("will i get the job") == "yes_no"
    assert classify_ask("who is behind this") == "other"


def test_a_quantity_question_refuses_the_number_and_says_what_it_can():
    text = quantity_answer("no")
    assert "cannot put a number" in text
    assert "not on the way" in text
    assert not re.search(r"\d", text)


def test_quantity_fallback_refuses_the_number_but_keeps_the_date():
    out = _fallback_plain("how much hike will i get", "conditional",
                          {"window": "Jul-2027", "level": "antara"},
                          "Put it in writing.", asks="quantity")
    assert "cannot put a number" in out.answer
    assert "Jul-2027" in out.timing
    assert out.remedy == "Put it in writing."


def test_sanitise_marks_a_percentage_question_as_quantity_not_yes_no():
    plan = HoraryJudgement(restated_intent="hike size", in_scope=True,
                           is_yes_no=True, asks="yes_no", label="yes",
                           confidence="good", reason="ignored")
    out = _sanitise(plan, {"fav_hits": ["11"], "den_hits": []},
                    "how much percentage hike i will get this year")
    assert out.asks == "quantity"
    assert out.is_yes_no is False
    assert out.label != "yes"


def test_no_remedy_names_a_planet():
    for planet in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                   "Saturn", "Rahu", "Ketu"):
        line = plain_remedy(planet)
        assert line, planet
        assert not _PLANET_NAMED.search(line), f"{planet}: {line}"


def test_blocking_planet_always_maps_to_a_remedy():
    ev = {"den_hits": [], "list_a": ["Jupiter"], "list_c": ["Jupiter"],
          "cusp_sub_lord": "Sun"}
    assert plain_remedy(blocking_planet(ev))


def test_date_detection_guards_the_free_view():
    assert _has_date("A job change is likely around November 2026.")
    assert _has_date("Expect movement by Jul-2027.")
    assert _has_date("This opens in 2029.")
    assert not _has_date("There is no clear sign of a job change soon.")
    assert not _has_date("Speak directly to the person who decides.")
