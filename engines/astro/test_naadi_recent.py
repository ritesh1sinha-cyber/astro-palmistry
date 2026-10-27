"""Chandra Naadi 'on your mind now' and 'last six months' paragraphs."""
from __future__ import annotations

import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import naadi_recent as NR  # noqa: E402

TODAY = date(2026, 10, 27)
NOW = datetime(2026, 10, 27, 6, 30)


def _pc():
    sign_house = {"Sun": ("Taurus", 11), "Moon": ("Sagittarius", 6), "Mars": ("Aquarius", 8),
                  "Mercury": ("Capricorn", 7), "Jupiter": ("Cancer", 1), "Venus": ("Pisces", 9),
                  "Saturn": ("Capricorn", 7), "Rahu": ("Capricorn", 7), "Ketu": ("Cancer", 1)}
    return {
        "meta": {"lagna_sign": "Cancer"},
        "planets": {p: {"sign": s, "house": h} for p, (s, h) in sign_house.items()},
        "vimshottari": {
            "current_md": {"md_lord": "Rahu"},
            "current_md_antardashas": [
                {"ad_lord": "Venus", "start": "2025-06-01", "end": "2026-06-28", "status": "past"},
                {"ad_lord": "Sun", "start": "2026-06-28", "end": "2027-05-23", "status": "current"},
            ],
        },
    }


def test_mind_facts_use_the_moon_trigger_on_natal_planets():
    f = NR.mind_facts(_pc(), TODAY, NOW)
    assert f["moon_sign"] in NR.SIGNS and 1 <= f["moon_house"] <= 12
    assert f["moon_leaves"] >= TODAY
    assert all(c["kind"] in ("sits on", "looks at") for c in f["contacts"])
    assert f["md"] == "Rahu" and f["ad"] == "Sun"
    units = NR.mind_units(f)
    assert 2 <= len(units) <= 3 and all(u["a"] and u["fb"] for u in units)


def test_past_facts_are_inside_the_window_and_dated():
    facts = NR.past_facts(_pc(), TODAY)
    assert facts and len(facts) <= 4
    assert any(x["kind"] == "period" and x["date"] == date(2026, 6, 28) for x in facts)
    for x in facts:
        if x["kind"] == "slow":
            assert x["planet"] in NR.SLOW and 1 <= x["house"] <= 12
            if x.get("began"):
                assert (TODAY - x["began"]).days <= NR.WINDOW_DAYS
    units = NR.past_units(facts)
    text = " ".join(u["a"] + " " + u["b"] for u in units)
    assert re.search(r"\b\d{1,2} [A-Z][a-z]{2} 2026\b", text)


def test_without_the_model_the_paragraphs_are_plain_and_complete(monkeypatch):
    monkeypatch.setattr(NR, "_write_feel", lambda kind, units: None)
    out = NR.build(_pc(), TODAY)
    assert out["by_model"] == {"mind": False, "past": False}
    assert out["mind"] and out["past"]
    for it in out["mind"] + out["past"]:
        assert not NR._JARGON.search(it["title"] + " " + it["text"])
        assert len(it["text"].split()) >= 15
    html = NR.render_items(out["past"])
    assert html.count("<li>") == len(out["past"]) and "<b>" in html


def test_feel_validator_rejects_invention():
    ok = ["You may be turning over a remark from your boss and wondering where you stand with him."]
    assert NR._feel_problems(ok, 1, "mind") == []
    for bad in (
        "You may think about Saturn and your boss a lot these days, wondering where you stand.",     # planet
        "You may have felt this most around 14 Sep when the talk at home got tense and sharp.",        # digits
        "You may be thinking about money in October and wondering where it all went these days.",       # month
        "You will soon get a call that settles the matter you have been turning over in your head.",    # future
        "Your boss is on your mind and you keep replaying the conversation from this morning again.",   # no hedge
        "You may feel this heavy weight until the matter is finally settled in your own head today.",   # ends/future
    ):
        assert NR._feel_problems([bad], 1, "mind"), bad
    assert NR._feel_problems(ok + ok, 1, "mind")             # wrong count
    assert NR._feel_problems(["You may have felt things were tense at work and tiring at home for weeks."], 1, "mind")  # past tense for NOW


def test_model_feelings_are_inserted_between_the_facts(monkeypatch):
    def fake(kind, units):
        return [f"You may be turning thoughts over about {u['title'].lower()}, quietly and without much noise." for u in units]
    monkeypatch.setattr(NR, "_write_feel", fake)
    out = NR.build(_pc(), TODAY)
    assert out["by_model"] == {"mind": True, "past": True}
    first = out["past"][0]["text"]
    assert first.index("sat over") < first.index("You may be turning") < len(first)
