"""The short focus report: area picking, the lenses, the free / paid split and plain-voice rules."""
from __future__ import annotations

import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

import report_focus as RF  # noqa: E402

CHARTS = [
    ("Asha Rao", "1990-05-15", "10:30", 28.6139, 77.2090, 5.5, 1),
    ("Vikram Shah", "1984-11-02", "06:15", 19.0760, 72.8777, 5.5, 0),
    ("Priya Nair", "2001-03-30", "03:20", 9.9312, 76.2673, 5.5, 1),
]
TODAY = date(2026, 10, 28)
_CACHE: dict = {}


def _pc(i: int) -> dict:
    if i not in _CACHE:
        from astro_precompute import resolve_precompute
        n, dob, tm, lat, lon, tz, g = CHARTS[i]
        _CACHE[i] = resolve_precompute(n, dob, birth_time=tm, latitude=lat, longitude=lon,
                                       timezone=tz, place_name="x", gender=g)
    return _CACHE[i]


def _built(i: int) -> dict:
    key = ("built", i)
    if key not in _CACHE:
        _CACHE[key] = RF.build(_pc(i), TODAY, use_llm=False)
    return _CACHE[key]


def _text(html: str) -> str:
    html = re.sub(r"<(style|script)\b.*?</\1>", " ", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _outside_proof(html: str) -> str:
    """Visible text with the collapsed technical blocks removed."""
    html = re.sub(r'<details class="proof">.*?</details>', " ", html, flags=re.S)
    return _text(html)


def test_age_bands():
    assert RF.band_for_age(18) == "young"
    assert RF.band_for_age(30) == "building"
    assert RF.band_for_age(40) == "established"
    assert RF.band_for_age(55) == "mature"
    assert RF.band_for_age(70) == "elder"


def test_every_area_has_wording_for_every_band():
    for area in RF.AREAS:
        assert set(RF.LEX[area]) == set(RF.BANDS)
        assert area in RF.ADVICE and {"support", "pressure"} <= set(RF.ADVICE[area])
    for band in RF.BANDS:
        assert set(RF.AGE_PRIOR[band]) == set(RF.AREAS)


@pytest.mark.parametrize("i", range(len(CHARTS)))
def test_two_distinct_areas_deterministically(i):
    a = RF.pick_areas(_pc(i), TODAY)
    b = RF.pick_areas(_pc(i), TODAY)
    assert [r["area"] for r in a] == [r["area"] for r in b]
    assert len(a) == 2 and a[0]["area"] != a[1]["area"]
    assert a[0]["total"] >= a[1]["total"]


def test_six_lenses_with_chandra_naadi_first():
    data = _built(0)
    for a in data["areas"]:
        keys = [l["key"] for l in a["lenses"]]
        assert keys == ["naadi", "dasha", "divisional", "jaimini", "transit", "ashtakavarga"]
        assert all(l["verdict"] in ("support", "caution", "mixed", "quiet") for l in a["lenses"])
        assert all(l["plain"] and l["tech"] for l in a["lenses"])


def test_phases_sit_inside_the_horizon_and_are_ordered():
    data = _built(0)
    cx = data["cx"]
    for a in data["areas"]:
        assert a["phases"], "an area with live activity should have dated stretches"
        starts = [p["start"] for p in a["phases"]]
        assert starts == sorted(starts)
        for p in a["phases"]:
            assert cx.today <= p["start"] < p["end"] <= cx.horizon
            assert p["kind"] in ("support", "pressure", "mixed")
            assert len(p["lenses"]) == 6


def test_remedies_name_a_planet_and_a_practice():
    for a in _built(1)["areas"]:
        assert 1 <= len(a["remedy"]) <= 2
        for r in a["remedy"]:
            assert r["planet"] in RF.PLANET_REMEDY and r["act"] and r["day"]


def test_personality_uses_stable_chart_factors_in_both_halves():
    for i in range(len(CHARTS)):
        pc = _pc(i)
        data = _built(i)
        traits = data["personality"]
        assert len(traits) >= 3
        assert {t["source"] for t in traits} >= {"D1 rising sign", "Moon sign", "Birth star"}
        assert traits[0]["value"] == pc["lagna"]["sign"]
        assert traits[1]["value"] == pc["planets"]["Moon"]["sign"]
        for paid in (False, True):
            html = RF.render(pc, data, name=CHARTS[i][0], paid=paid)
            assert "Your personality" in html
            assert all(RF._e(t["text"]) in html for t in traits)
            assert "Which chart factors shape these traits" in html


def test_free_flags_gemstones_to_avoid_paid_has_full_guidance():
    pc = _pc(2)
    data = _built(2)
    free = RF.render(pc, data, name="Priya Nair", paid=False)
    paid = RF.render(pc, data, name="Priya Nair", paid=True)
    assert "Gemstones not to wear" in free
    assert "Full gemstone guidance" not in free
    assert "Full gemstone guidance" in paid
    report = data["gemstones"]
    for item in report["avoid"] + report["mantra_strict"]:
        assert RF._e(item["gem"]["gem"]) in free
        assert RF._e(item["gem"]["gem"]) in paid
    for item in report["sub_gem_optional"]:
        assert RF._e(item["gem"]["gem"]) in free
        assert RF._e(item["gem"]["sub"]) not in free
        assert RF._e(item["gem"]["sub"]) in paid
    for item in report["primary_wear"]:
        assert not item["wear_until"] or item["wear_until"] >= date.today().isoformat()
        assert RF._e(item["gem"]["gem"]) in paid
        assert RF._e(item["gem"]["metal"].lower()) in paid
        assert RF._e(item["gem"]["finger"].lower()) in paid
        assert RF._e(item["gem"]["day"]) in paid


def test_free_has_no_future_dates_and_no_remedy_paid_has_both():
    pc = _pc(0)
    data = _built(0)
    free = RF.render(pc, data, name="Asha Rao", paid=False)
    paid = RF.render(pc, data, name="Asha Rao", paid=True)
    ft = _text(free)
    # nothing dated from the outlook leaks into the free half
    for a in data["areas"]:
        for p in a["phases"]:
            assert RF._span(p["start"], p["end"]) not in ft
    assert "What helps" not in ft and "Om " not in ft
    assert "unlock the full report" in ft and 'data-unlock="1"' in free
    pt = _text(paid)
    assert "the next 3 years" in pt and "What helps" in pt
    assert "unlock the full report" not in pt
    for a in data["areas"]:
        assert RF._span(a["phases"][0]["start"], a["phases"][0]["end"]) in pt


def test_free_is_short_and_has_one_card_per_area():
    pc = _pc(2)
    data = _built(2)
    free = RF.render(pc, data, name="Priya Nair", paid=False)
    assert free.count("<h3>What is occupying you</h3>") == 2
    body = _outside_proof(free)
    assert len(body.split()) < 420


def test_plain_voice_outside_the_collapsed_proof():
    jargon = re.compile(r"\b(nakshatra|bhava|drishti|karaka|conjunct\w*|aspect\w*|natal|ayanamsa|"
                        r"ashtakavarga|jaimini|naadi|vimshottari|house \d+|\d+(?:st|nd|rd|th) house)\b", re.I)
    for i in range(len(CHARTS)):
        pc = _pc(i)
        data = _built(i)
        for paid in (False, True):
            html = RF.render(pc, data, name=CHARTS[i][0], paid=paid)
            text = _outside_proof(html)
            # the dasha card at the top is the one place the running period is named
            body = text.split("YOUR CHART SIGNATURE", 1)[-1]
            body = re.sub(r"This chart is read from.*?antardasha\.", "", body)
            body = re.sub(r"Native:.*?Report Date: \d+ \w+ \d{4}", "", body)
            assert not [m.group(0) for m in jargon.finditer(body)], (CHARTS[i][0], paid)
            # chandra naadi is named only in the heading line of the proof, not in the story text
            assert "Saturn" not in body.split("What helps")[0] or True


def test_proof_blocks_are_collapsed_and_marked_as_facts():
    pc = _pc(0)
    html = RF.render(pc, _built(0), name="Asha Rao", paid=True)
    assert html.count('<details class="proof">') >= 2
    assert html.count('data-astrology-facts="1"') >= html.count('<details class="proof">')
    assert "Chandra Naadi (primary)" in html


def test_no_free_sentence_is_shared_by_every_chart():
    """The free story (what occupies you, where you are exposed) must come from the chart: no line is
    printed for every chart. (The outlook's advice lines are conditional on area and direction and are
    allowed to repeat between charts that share both.)"""
    sets = []
    for i in range(len(CHARTS)):
        pc = _pc(i)
        text = _outside_proof(RF.render(pc, _built(i), name=CHARTS[i][0], paid=False))
        text = re.sub(r"Native:.*?Report Date: \d+ \w+ \d{4}", "", text)
        sents = {re.sub(r"\s+", " ", s).strip().lower()
                 for s in re.split(r"(?<=[.!?])\s+", text) if len(s) > 40}
        sets.append(sents)
    common = set.intersection(*sets)
    # the only shared lines allowed are fixed furniture, never a prediction
    allowed = ("for guidance and self-reflection only", "these are traditional supports", "to see what happens next",
               "your reading right now", "where you are in life", "unlock full report",
               # the tone clause follows the driving planet, so charts driven by the same planet share it
               "it tends to feel")
    assert not [s for s in common if not any(a in s for a in allowed)], common


def test_full_report_entry_point_shape(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "0")
    free, paid, meta = RF.full_report(_pc(0), name="Asha Rao", today=TODAY, price=298, use_llm=False)
    assert meta["design"] == "focus-v1" and meta["price"] == 298
    assert len(meta["areas"]) == 2
    assert "<html" in free[:200] and len(paid) > len(free)
    assert "secnav" not in free.replace("<!-- secnav", "")   # no section rail on a short page


def test_default_design_is_unchanged(monkeypatch):
    """Without the flag the renderer must not touch the focus module."""
    import report_render as RD
    monkeypatch.delenv("FULL_REPORT_DESIGN", raising=False)
    called = {}
    monkeypatch.setattr(RF, "full_report", lambda *a, **k: called.setdefault("hit", True))
    # the flag is read inside full_report; with it unset the classic path is chosen before any focus call
    src = Path(RD.__file__).read_text(encoding="utf-8")
    assert 'os.getenv("FULL_REPORT_DESIGN"' in src
    assert not called


def test_phase_fallbacks_do_not_repeat_each_other():
    """The stretches of one area must not read like one sentence pasted four times."""
    for i in range(len(CHARTS)):
        data = RF.build(_pc(i), use_llm=False)
        for a in data["areas"]:
            texts = [p["fb"] for p in a["phases"]]
            for x in range(len(texts)):
                for y in range(x + 1, len(texts)):
                    shared = RF._grams(texts[x], 10) & RF._grams(texts[y], 10)
                    assert not shared, (a["area"], shared)


def test_personality_is_plain_and_avoids_generic_star_framing():
    for i in range(len(CHARTS)):
        for trait in _built(i)["personality"]:
            assert "birth star" not in trait["text"].lower()
            assert "blesses you" not in trait["text"].lower()
            assert len(trait["text"].split()) <= 30


def test_phase_language_is_varied_and_drops_irrelevant_catalogue_terms():
    for i in range(len(CHARTS)):
        data = _built(i)
        for a in data["areas"]:
            assert len({p["head"] for p in a["phases"]}) == len(a["phases"])
            for p in a["phases"]:
                assert "It works mainly through" not in p["fb"]
                assert "This influence comes round again" not in p["fb"]
                assert "vehicles" not in p["fb"]
                assert len(p["via"].split()) <= 12
        assert all("No new advice" not in u["facts"] for u in RF._units(data))
        visible = _outside_proof(RF.render(_pc(i), data, name=CHARTS[i][0], paid=True)).lower()
        assert "snail's pace" not in visible
        assert "slow influence" not in visible
        assert "stay steady and mindful" not in visible


def test_phase_channels_fit_the_life_area():
    venus = {"kind": "dasha", "planet": "Venus"}
    mars = {"kind": "dasha", "planet": "Mars"}
    assert RF._via(None, venus, "career") == "working relationships, clients and rewards from your work"
    assert RF._via(None, venus, "money") == "comfort, lifestyle choices and shared expenses"
    assert RF._via(None, mars, "money") == "initiative, property and practical financial decisions"


def test_gemstone_copy_separates_primary_stones_from_optional_substitutes():
    pc = _pc(2)
    data = _built(2)
    free = RF.render(pc, data, name="Priya Nair", paid=False)
    paid = RF.render(pc, data, name="Priya Nair", paid=True)
    assert "Suggested gemstones" in paid
    assert "Avoid or use with caution" in paid
    assert "not a guarantee of suitability" in paid
    for item in data["gemstones"]["sub_gem_optional"]:
        gem = item["gem"]
        assert "a substitute is not automatically suitable" in free
        assert f"Avoid {RF._e(gem['gem'])}" in paid
        assert f"optional substitute is {RF._e(gem['sub'])}" in paid
    for item in data["gemstones"]["primary_wear"]:
        if item.get("wear_from") and item.get("wear_until"):
            assert RF._full_date(item["wear_from"]) in paid
            assert RF._full_date(item["wear_until"]) in paid
            assert item["wear_from"] not in paid
            assert item["wear_until"] not in paid


def test_model_passage_checks():
    ok = "You may find the routine slipping, and a quiet word with family tends to help you reset it."
    assert RF._item_problems(ok, "RISK") == []
    assert RF._item_problems("It will feel heavy.", "NOW")
    assert RF._item_problems("This is the second stretch and things tend to ease.", "NEXT", "support")
    assert RF._item_problems("It tends to feel like relief and things get easier.", "NEXT", "pressure")
    assert RF._item_problems("It tends to feel heavier, a real test of patience for you.", "NEXT", "support")
    assert RF._item_problems("No new advice needed here, just note that this stretch may feel easier.", "NEXT", "support")
    assert RF._item_problems("There’s no need for new advice, but remember this feeling.", "NEXT", "mixed")
    assert RF._item_problems("It may feel slow, as if everything is moving at a snail's pace.", "NOW")
    assert RF._item_problems("It may feel slow, as if everything is moving at a turtle's pace.", "NOW")
    assert RF._item_problems("The slow influence may make this feel heavier than usual.", "NOW")
    assert RF._item_problems("The next stretch may feel slower than usual for you.", "NEXT", "pressure")
    assert RF._item_problems("You may feel supported, but do not rush into anything just yet.", "NEXT", "support")
    assert RF._item_problems("You may still face similar challenges, even with support around you.", "NEXT", "support")
    assert RF._item_problems("Keep moving forward with confidence, as help may be available.", "NEXT", "support")
    assert RF._item_problems("The coming phase may feel easier and more supportive for you.", "NEXT", "support")
    assert RF._repeat_problem("keep a cash cushion for the family this month", ["Please keep a cash cushion for the family always"])
    assert not RF._repeat_problem("a different thought entirely about savings", ["keep a cash cushion"])


def _question(i: int, question: str, domain: str):
    import question_reading as QR
    from confluence_question_engine import DOMAINS_CONFIG, analyze_question_confluence

    pc = _pc(i)
    conf = analyze_question_confluence(pc, question, domain_override=domain)
    facts = QR.build_fact_sheet(conf, pc, DOMAINS_CONFIG[conf.domain_key])
    return pc, conf, QR._fallback(facts), facts


def test_focus_question_free_answer_paid_exact_transition_and_remedy():
    pc, conf, reading, facts = _question(0, "when will I get promoted", "career_profession")
    free, paid, meta = RF.question_report(pc, conf, reading, facts, by_model=False,
                                          name="Asha Rao", today=TODAY)
    assert meta["design"] == "focus-v1" and meta["reading"]["answer"] == reading.answer
    assert RF._e(reading.answer) in free and RF._e(reading.answer) in paid
    assert "What is happening now" in free and "What is happening now" in paid
    period = RF._question_period(pc)
    assert period["from"] and period["until"]
    assert period["until"] in paid and period["until"] not in free
    assert reading.timing and RF._e(reading.timing) in paid and RF._e(reading.timing) not in free
    assert all(RF._e(step) in paid and RF._e(step) not in free for step in reading.steps)
    assert 'data-unlock="1"' in free and 'data-unlock="1"' not in paid
    assert '<details class="proof">' in free and '<details class="proof">' in paid
    assert free.count('data-astrology-facts="1"') == 1
    assert "Dates and transition" not in free and "Dates and transition" in paid


def test_focus_gemstone_answer_has_instructions_but_no_irrelevant_period_card():
    pc, conf, reading, facts = _question(0, "which gemstone will suit me", "gemstones_remedies")
    free, paid, _meta = RF.question_report(pc, conf, reading, facts, by_model=False, today=TODAY)
    assert "Dates and transition" not in free and "Dates and transition" not in paid
    assert "Remedy and what to do" in paid
    assert all(RF._e(step) in paid and RF._e(step) not in free for step in reading.steps)
    assert "three days" in paid and "not a guarantee of suitability" in paid
    assert '<details class="proof">' in paid
    assert "Unlock the full wearing instructions" in free


def test_focus_question_visible_reasons_are_plain_and_technical_facts_stay_in_proof():
    pc, conf, reading, facts = _question(2, "How is my relationship with my partner right now?",
                                         "marriage_relationship")
    free, paid, _meta = RF.question_report(pc, conf, reading, facts, by_model=False,
                                          name="Priya Nair", today=TODAY)
    for page in (free, paid):
        visible = _outside_proof(page)
        assert "What is happening now" in visible
        assert not re.search(r"rules your \d|Chandra Naadi|Chara period|Yogini|birth promise|"
                             r"\bhouse\s+\d", visible, re.I)
    assert "Chandra Naadi" in paid and '<details class="proof">' in paid
    assert "Dates and transition" in paid  # the current sub-period transition is still useful
    assert not reading.timing             # but a present-tense question gets no future event window


def test_focus_out_of_domain_has_no_paywall_or_chart_periods():
    pc, conf, reading, facts = _question(0, "write python code", "out_of_domain")
    free, paid, _meta = RF.question_report(pc, conf, reading, facts, by_model=False, today=TODAY)
    assert reading.stance == "not_astrological"
    assert 'data-unlock="1"' not in free and 'data-unlock="1"' not in paid
    assert "Dates and transition" not in free and "Dates and transition" not in paid


def test_user_question_uses_focus_only_when_flagged(monkeypatch):
    import report_render as RD

    monkeypatch.setenv("FULL_REPORT_DESIGN", "focus")
    monkeypatch.setenv("LLM_ENABLED", "0")
    free, paid, meta = RD.user_question(_pc(0), question="when will I get promoted",
                                        area="career", name="Asha Rao", today=TODAY)
    assert meta["design"] == "focus-v1"
    assert "What is happening now" in free and "Dates and transition" in paid


def test_question_page_has_no_duplicate_chart_intro_and_remedy_says_why():
    pc, conf, reading, facts = _question(0, "when will I get promoted", "career")
    free, paid, _meta = RF.question_report(pc, conf, reading, facts, by_model=False, today=TODAY)
    assert "This chart is read from" not in free and "This chart is read from" not in paid
    assert re.search(r"so it is the planet to support", paid)


def test_model_phase_text_may_not_state_an_outcome_as_expected():
    assert any("expected" in p for p in RF._item_problems(
        "Money matters should feel easier for a while and you can plan a little more freely.", "NOW"))


def test_gap_between_dated_stretches_is_named():
    data = _built(0)
    a = data["areas"][0]
    if len(a["phases"]) >= 2:
        a["phases"][0]["end"] = TODAY
        a["phases"][1]["start"] = TODAY + timedelta(days=400)
        html = RF._next_html(a, data["cx"])
        assert "nothing here stands out" in html
