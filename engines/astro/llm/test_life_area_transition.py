from datetime import date
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from life_area_transition import (
    build_transition_lanes,
    build_transition_map,
    customer_list,
    easing_note,
    transit_caption,
    window_state,
)


def test_transition_map_builds_overlap_stack(monkeypatch):
    class CF:
        @staticmethod
        def dasha_confluence(pc, when):
            return {
                "direction": "up",
                "agreement": "3 of 3 timing systems agree",
                "readings": [
                    {"kind": "vimshottari", "label": "Rahu–Jupiter"},
                    {"kind": "yogini", "label": "Bhramari (Mars)"},
                    {"kind": "chara", "label": "Aquarius–Capricorn (Saturn–Saturn)"},
                    {"kind": "bnn", "label": "supportive nadi timing"},
                ],
            }
    monkeypatch.setitem(__import__("sys").modules, "report_confluence", CF)
    rows = [
        {"start": date(2026, 9, 1), "end": date(2026, 12, 1), "aligned": False,
         "dasha": "down", "promise": "down", "bav": 3,
         "planet": "Saturn", "dasha_label": "Rahu–Saturn", "event_type": "career_window",
         "source": "dasha_ashtakavarga_transit_confluence", "confidence": "moderate", "score": -1.0},
        {"start": date(2027, 1, 1), "end": date(2027, 4, 1), "aligned": True,
         "dasha": "up", "promise": "up", "bav": 6,
         "planet": "Jupiter", "dasha_label": "Rahu–Jupiter", "event_type": "career_window",
         "source": "dasha_ashtakavarga_transit_confluence", "confidence": "high", "score": 2.0},
    ]
    out = build_transition_map({}, "career", rows)
    assert len(out) == 2
    assert out[0]["phase"] == "Pressure"
    assert out[1]["phase"] == "Recognition"
    assert "Rahu–Jupiter" in out[1]["overlap"]
    assert "Jupiter transit" in out[1]["overlap"]
    assert "6 bindus" in out[1]["overlap"]


def test_customer_list_keeps_yogini_and_chara():
    labels = customer_list([
        "Rahu–Jupiter",
        "Yogini: Bhramari (Mars)",
        "Chara: Aquarius–Capricorn",
        "Vimshottari",
        "Nadi timing: supportive",
        "Ashtakavarga 6 bindus",
        "Timing evidence is included in the overall reading.",
    ])
    joined = " ".join(labels).lower()
    assert "vimshottari" not in joined
    assert "nadi" not in joined
    assert "Yogini: Bhramari (Mars)" in labels
    assert "Chara: Aquarius–Capricorn" in labels
    assert "Ashtakavarga 6 bindus" in labels
    assert "Rahu–Jupiter" in labels
    assert "Dasha period" in labels


def test_lane_geometry_stays_in_range_and_has_dasha_bars():
    nodes = [
        {"start": "2026-08-01", "end": "2026-11-01", "direction": "down",
         "phase": "Pressure / Restructuring", "planet": "Saturn", "score": 0.4, "area": "career"},
        {"start": "2026-11-01", "end": "2027-03-01", "direction": "up",
         "phase": "Pressure → Opening", "planet": "Jupiter", "score": 1.8, "area": "career"},
    ]
    pc = {
        "vimshottari": {
            "current_md": {"md_lord": "Rahu", "start": "2024-05-01", "end": "2042-05-01"},
            "current_md_antardashas": [
                {"ad_lord": "Rahu", "start": "2024-05-01", "end": "2026-10-01"},
                {"ad_lord": "Jupiter", "start": "2026-10-01", "end": "2029-03-01"},
            ],
        },
        "yogini": {
            "full_cycle": [
                {"yogini": "Bhramari", "lord": "Mars", "start": "2025-01-01", "end": "2027-01-01"},
            ],
        },
        "chara_dasha": {
            "maha": [
                {"sign": "Aquarius", "start": "2024-01-01", "end": "2028-01-01"},
            ],
        },
    }
    lanes = build_transition_lanes(pc, nodes, area="career")
    assert lanes["axis"]["ticks"]
    for row in lanes["phases"] + lanes["dasha"] + lanes["transits"] + lanes["yogini"] + lanes["chara"]:
        assert 0 <= row["left_pct"] <= 100
        assert 0 < row["width_pct"] <= 100
        assert row["left_pct"] + row["width_pct"] <= 100.01
    assert any(b.get("kind") == "md" and "Rahu" in b["label"] for b in lanes["dasha"])
    assert any(b.get("kind") == "ad" for b in lanes["dasha"])
    assert any("Yogini" in b["label"] for b in lanes["yogini"])
    assert any("Chara" in b["label"] for b in lanes["chara"])
    assert lanes["confluence"] is not None
    assert 0 <= lanes["confluence"]["left_pct"] <= 100


def _sample_nodes():
    return [
        {"start": "2026-09-01", "end": "2026-12-01", "direction": "down",
         "phase": "Pressure / Restructuring", "meaning": "Responsibility builds first.",
         "overlap": ["Rahu–Saturn", "Yogini: Bhramari (Mars)", "Saturn transit", "3 bindus"],
         "drivers": ["Rahu–Saturn", "Saturn transit", "Ashtakavarga 3 bindus", "Yogini: Bhramari (Mars)"]},
        {"start": "2027-01-01", "end": "2027-04-01", "direction": "up",
         "phase": "Pressure → Opening", "meaning": "The pressure phase gives way to an opening.",
         "overlap": ["Rahu–Jupiter", "Yogini: Bhramari (Mars)", "Jupiter transit", "6 bindus"],
         "drivers": ["Rahu–Jupiter", "Jupiter transit", "Ashtakavarga 6 bindus"]},
    ]


def test_the_page_is_built_from_divisional_sections_not_area_cards():
    """The reading is one consultation, not a grid of per-area verdicts.

    Per-area cards ("Work & Career" · pill · Astrologer's conclusion) were
    replaced by the divisional life-domain blocks, and the lane chart they
    carried never reached a customer page. This holds the page to the three
    sections it is actually made of, so a reader cannot lose one silently.
    """
    from report_cards import Card
    import report_conversational as RC

    card = Card(
        area="career", label="Work & Career", direction="up", headline="Career opens",
        house=10, transition_map=_sample_nodes(),
    )
    html = RC.render(
        {
            "lagna": {"sign": "Aries"},
            "planets": {"Moon": {"sign": "Leo"}},
            "vimshottari": {
                "current_md": {"md_lord": "Rahu", "start": "2024-05-01", "end": "2042-05-01"},
                "current_md_antardashas": [
                    {"status": "current", "ad_lord": "Jupiter", "start": "2026-10-01", "end": "2029-03-01"},
                ],
            },
        },
        name="Meera", paid=True, cards=[card], today=date(2026, 8, 13),
        prose={"personality": "Your chart shows an active temperament.",
               "areas": {"career": {"outlook": "The longer period is mixed but improves."}}},
        remedy_html="",
    )
    for anchor in ("sec-who-you-are", "sec-your-current-chapter", "sec-life-domains"):
        assert f'id="{anchor}"' in html, anchor
    # The retired card furniture must not come back.
    assert "Astrologer's conclusion" not in html
    assert "Life-area transition map" not in html
    assert "When the chart gives these themes more room to move" not in html


def test_a_card_without_a_transition_map_still_renders_a_page():
    from report_cards import Card
    import report_conversational as RC

    card = Card(area="career", label="Work & Career", direction="up",
                headline="Career opens", house=10)
    html = RC.render(
        {"lagna": {"sign": "Aries"}, "planets": {"Moon": {"sign": "Leo"}}},
        name="Meera", paid=True, cards=[card], today=date(2026, 8, 13),
        prose={"personality": "You act once a direction is clear.",
               "areas": {"career": {"outlook": "The career theme is supported.",
                                    "timing": "Jan 2027 → Apr 2027"}}},
    )
    assert 'id="sec-your-current-chapter"' in html
    assert "You act once a direction is clear." in html


def test_transition_fact_and_dict_produce_the_same_page():
    """A card carrying models and a card carrying dicts must not diverge."""
    import report_conversational as RC
    from llm.schemas import CardFacts, TransitionFact

    nodes = _sample_nodes()
    dict_card = CardFacts(area="career", label="Work & Career", transition_map=nodes)
    model_card = CardFacts(
        area="career",
        label="Work & Career",
        transition_map=[TransitionFact.model_validate(n) for n in nodes],
    )
    pc = {"lagna": {"sign": "Aries"}, "planets": {"Moon": {"sign": "Leo"}}}
    prose = {"personality": "You tend to act when a direction is clear.",
             "areas": {"career": {"outlook": "The career theme is supported.",
                                  "transition_note": "Pressure gives way to an opening."}}}
    html_a = RC.render(pc, name="Meera", paid=True, cards=[dict_card], prose=prose)
    html_b = RC.render(pc, name="Meera", paid=True, cards=[model_card], prose=prose)
    assert html_a == html_b
    assert "You tend to act when a direction is clear." in html_a


def test_window_state_calls_a_future_window_upcoming():
    nodes = [{"start": "2028-12-01", "end": "2029-03-01"}]
    state = window_state(nodes, today=date(2026, 8, 13))
    assert state["state"] == "upcoming"
    assert state["opens"] == "Dec 2028"
    running = window_state(
        [{"start": "2026-06-01", "end": "2027-01-01"}], today=date(2026, 8, 13))
    assert running["state"] == "running"


def test_future_window_is_not_reported_as_active_now():
    """Tested on the pill itself rather than through a page.

    The engine can mark an area "active" while its only window opens years
    out; saying "Active now" there is the one claim a reader can immediately
    disprove. The guard lives in _pill, so that is where it is held.
    """
    import report_conversational as RC
    from llm.schemas import CardFacts, WindowFact

    card = CardFacts(
        area="love", label="Relationships & Partnership", status="strongly_supported",
        activation_status="active", house=7,
        timing_windows=[WindowFact(start="2028-12-01", end="2029-03-01", label="love_window")],
    )
    pill = RC._pill({}, card, date(2026, 8, 13))
    assert "Supported but not yet active" in pill
    assert "Active now" not in pill


def test_a_weak_promise_is_never_called_promised():
    import report_conversational as RC
    from llm.schemas import CardFacts, WindowFact

    card = CardFacts(
        area="career", label="Work & Career", status="insufficient_evidence",
        activation_status="active", house=10,
        timing_windows=[WindowFact(start="2032-03-01", end="2032-08-01", label="career_window")],
    )
    pill = RC._pill({}, card, date(2026, 8, 13))
    # insufficient_evidence renders as "Limited support", never "promised".
    assert "Limited support" in pill
    assert "Promised" not in pill
    assert "Active now" not in pill


def test_a_far_off_map_says_what_happens_in_the_meantime():
    import report_conversational as RC

    nodes = [{"start": "2032-03-01", "end": "2032-08-01", "direction": "mixed",
              "phase": "Opportunity / Evaluation", "meaning": "An opening is present.",
              "overlap": ["Rahu–Ketu"], "drivers": []}]
    html = RC.render_transition_map(
        {"lagna": {"sign": "Aries"}}, nodes, area="career", today=date(2026, 8, 13))
    assert "No dated turn reaches this area before" in html
    assert "Mar 2032" in html

    near = [dict(nodes[0], start="2026-11-01", end="2027-02-01")]
    assert "No dated turn reaches this area before" not in RC.render_transition_map(
        {"lagna": {"sign": "Aries"}}, near, area="career", today=date(2026, 8, 13))


def test_context_transits_cover_ruler_and_period_lords():
    from life_area_transition import build_context_transits

    rows = build_context_transits(
        {"house_lords": {10: {"lord": "Saturn"}},
         "meta": {"lagna_sign": "Aries", "client": "Test"},
         "planets": {p: {"sign": "Aries"} for p in
                     ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")}},
        10, today=date(2026, 8, 13), years=2, md_lord="Rahu", ad_lord="Jupiter",
    )
    roles = " ".join(r["role"] for r in rows)
    assert "ruler of house 10" in roles
    assert "mahadasha lord" in roles
    assert "antardasha lord" in roles
    # Nodes carry no bindus, so they must never claim a score.
    for row in rows:
        assert row["tone"] in ("supportive", "testing", "steady", "onhouse", "background")
        if row["planet"] in ("Rahu", "Ketu"):
            assert "bindu" not in transit_caption(row)


def test_quiet_context_transits_are_listed_but_not_drawn():
    nodes = [
        {"start": "2026-09-01", "end": "2027-03-01", "direction": "up",
         "phase": "Opening / Expansion", "planet": "Jupiter", "score": 1.0, "area": "career"},
    ]
    context = [
        {"planet": "Saturn", "role": "ruler of house 10", "sign": "Pisces", "house": 12,
         "start": "2026-09-01", "end": "2027-01-01", "bav": 4, "tone": "background",
         "major": False, "in_house": False},
        {"planet": "Rahu", "role": "mahadasha lord", "sign": "Capricorn", "house": 10,
         "start": "2026-10-01", "end": "2027-02-01", "bav": 0, "tone": "onhouse",
         "major": True, "in_house": True},
    ]
    lanes = build_transition_lanes({}, nodes, area="career", context=context)
    assert len(lanes["context_rows"]) == 2
    assert [b["label"] for b in lanes["context_bars"]] == ["Rahu · house 10"]
    for bar in lanes["context_bars"]:
        assert 0 <= bar["left_pct"] <= 100
        assert bar["left_pct"] + bar["width_pct"] <= 100.01


def test_problem_stretch_carries_an_easing_line_and_a_step():
    from report_cards import Card
    import report_conversational as RC

    hard = [
        {"start": "2026-09-01", "end": "2027-02-01", "direction": "down", "bav": 2,
         "phase": "Pressure / Restructuring", "meaning": "Effort is asked for first.",
         "overlap": [], "drivers": []},
        {"start": "2027-02-01", "end": "2027-08-01", "direction": "up", "bav": 6,
         "phase": "Pressure → Opening", "meaning": "The pressure gives way.",
         "overlap": [], "drivers": []},
    ]
    assert "Feb 2027" in easing_note(hard, today=date(2026, 8, 13))
    card = Card(area="health", label="Health & Energy", direction="down",
                headline="Health needs care", house=1, transition_map=hard)
    # A hard stretch must come with the month it eases and something to do
    # about it. Both come from _fallback_help, which the page no longer calls
    # per area, so the pairing is checked at its source.
    help_text = RC._fallback_help(card, "Health & Energy")
    assert "This opens up from Feb 2027" in help_text
    assert len(help_text.split()) > 6


def test_question_answer_renders_the_same_transition_map():
    import question_answer as QA

    result = {
        "windows": [
            {"start": date(2026, 9, 1), "end": date(2026, 12, 1), "planet": "Saturn",
             "bav": 3, "strong": False, "dasha_dir": "down", "dasha_label": "Rahu–Saturn",
             "score": -0.5},
            {"start": date(2027, 1, 1), "end": date(2027, 5, 1), "planet": "Jupiter",
             "bav": 6, "strong": True, "dasha_dir": "up", "dasha_label": "Rahu–Jupiter",
             "score": 2.0},
        ],
        "area_key": "home",
        "start": date(2026, 8, 13),
        "topic": type("T", (), {"houses": [4]})(),
    }
    html = QA._question_transition_html(result, {"house_lords": {}, "planets": {}})
    assert "How the answer changes across the window" in html
    assert "Pressure" in html
    assert ".life-map{" in html  # the question shell needs its own stylesheet


def test_the_dashed_marker_says_what_it_is_and_when():
    """The marker sits at a different place on every card because each area
    has its own axis and its own strongest turn. Undated and unexplained, it
    read as a rendering artefact.
    """
    from life_area_transition import build_transition_lanes

    lanes = build_transition_lanes({}, _sample_nodes(), area="learning")
    conf = lanes["confluence"]
    assert conf["start"] and conf["end"], "the marker carries its own dates"
    assert conf["caption"].lower().endswith(("opens", "needs care"))

    from report_conversational import _conf_sentence
    line = _conf_sentence(conf)
    assert line.startswith("Dashed line:")
    assert conf["start"] in line and conf["end"] in line

    # Those dates come from the timing row, so the date guard keeps them.
    from qa_checks.date_guard import allowed_month_years, soften_unvalidated_dates
    allowed = allowed_month_years(
        [{"start": n["start"], "end": n["end"]} for n in _sample_nodes()])
    assert soften_unvalidated_dates(line, allowed=allowed) == line


def test_a_window_is_never_called_strongest_over_a_map_that_says_pressure():
    """The best-scoring window is not always a good one. The heading used to
    say "Strongest window" directly above bands the map drew as pressure, and
    a reader who sees the picture disbelieves the words.
    """
    import question_answer as QA

    pressured = {"start": date(2026, 8, 1), "end": date(2026, 10, 1),
                 "bav": 3, "strong": False, "dasha_dir": "down"}
    backed = {"start": date(2027, 1, 1), "end": date(2027, 5, 1),
              "bav": 6, "strong": True, "dasha_dir": "up"}

    assert QA._window_tone(pressured) == "down"
    assert QA._window_tone(backed) == "up"
    assert QA._BEST_WINDOW_LABEL["down"] == "Best window available"
    assert QA._BEST_WINDOW_LABEL["up"] == "Strongest window"

    # The same rule the map uses, so the two cannot drift apart.
    from life_area_transition import build_transition_map
    nodes = build_transition_map(
        {"house_lords": {}, "planets": {}}, "home",
        [dict(pressured, aligned=False, dasha="down")])
    assert nodes and nodes[0]["direction"] == "down"


def test_transition_dates_survive_date_guard():
    from qa_checks.date_guard import soften_unvalidated_dates
    html = "The shift in September 2026 opens into January 2027."
    allowed = {"September 2026", "January 2027"}
    assert "September 2026" in soften_unvalidated_dates(html, allowed=allowed)
    stripped = soften_unvalidated_dates(html, allowed={"January 2027"})
    assert "September 2026" not in stripped
    assert "later in the cycle" in stripped
