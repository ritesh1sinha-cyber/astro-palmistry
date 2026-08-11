"""Tests for the LLM facts→prose layer (feedback correction plan).

No network: uses core.llm_client.set_stub. With LLM_ENABLED=0 the overlay
must be empty so renderers keep deterministic templates. When enabled and
QA fails after retries, deterministic fallback prose is used — prediction
facts never change.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
ASTRO = ROOT / "engines" / "astro"
for p in (str(ROOT), str(ASTRO)):
    if p not in sys.path:
        sys.path.insert(0, p)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _card_facts(area="profession", status="supported", direction="support"):
    from llm.schemas import CardFacts, EvidenceFact, ReportFacts
    return ReportFacts(
        first_name="Meera",
        age_band="adult",
        access="paid",
        cards=[CardFacts(
            area=area,
            label="Career",
            kind="promise",
            status=status,
            activation_status="active",
            confidence="moderate",
            direction=direction,
            score=0.8,
            support_n=2,
            caution_n=1,
            house=10,
            evidence=[
                EvidenceFact(family="natal", polarity="support",
                             text_id="n1", text="lord gives solid support"),
                EvidenceFact(family="divisional", polarity="caution",
                             text_id="d1", text="divisional chart adds caution"),
            ],
            manifestation_ids=["role expansion", "professional recognition"],
            semantic_tags=["career", "recognition"],
        )],
        schema_version="1.0",
        engine_version="astro-2026.08.11",
        facts_hash="testhash",
    )


GOOD_CARD = {
    "area": "profession",
    "headline": "Your career theme is supported and currently active.",
    "summary": "The chart gives solid support to this life theme with a note of caution.",
    "how_this_may_show_up": [
        "recognition for steady work",
        "a clear step in responsibility",
    ],
    "what_to_watch": ["Rushing decisions can create avoidable friction here."],
    "what_helps": ["Keep a weekly review habit and move on the openings that fit."],
    "timing_summary": "Validated timing windows favour steady effort.",
}

# Legacy-shaped payload still accepted via CardProse alias mapping
GOOD_CARD_LEGACY = {
    "area": "profession",
    "headline": "Your career theme is supported and currently active.",
    "why": "The chart gives solid support to this life theme with a note of caution.",
    "meaning": "The underlying promise is there, and timing is lighting it up now.",
    "manifestations": [
        "recognition for steady work",
        "a clear step in responsibility",
    ],
    "pressure": "Rushing decisions can create avoidable friction here.",
    "action": "Keep a weekly review habit and move on the openings that fit.",
}


# ---------------------------------------------------------------------------
# schema + rules
# ---------------------------------------------------------------------------
def test_card_prose_schema_accepts_good():
    from llm.schemas import CardProse
    p = CardProse.model_validate(GOOD_CARD)
    assert p.area == "profession"
    assert len(p.manifestations) == 2
    assert p.why == p.summary


def test_card_prose_accepts_legacy_keys():
    from llm.schemas import CardProse
    p = CardProse.model_validate(GOOD_CARD_LEGACY)
    assert p.summary
    assert p.how_this_may_show_up


def test_card_prose_schema_rejects_overlong():
    from llm.schemas import CardProse
    from pydantic import ValidationError
    bad = dict(GOOD_CARD, headline="x" * 200)
    with pytest.raises(ValidationError):
        CardProse.model_validate(bad)


def test_check_prose_blocks_guarantee_and_sanskrit():
    from llm.rules import check_prose
    facts = _card_facts()
    fails = check_prose("You will get a promotion next year.", facts)
    assert "certainty_escalation" in fails
    assert any(v.startswith("sanskrit:") for v in check_prose(
        "Your mahadasha supports this now.", facts))


def test_check_prose_allows_grounded_text():
    from llm.rules import check_prose
    facts = _card_facts()
    fails = check_prose(
        "Your career theme is supported and timing favours steady effort.",
        facts, area="profession")
    assert fails == []


def test_project_for_access_strips_paid_depth():
    from llm.facts import project_for_access
    from llm.schemas import CardFacts, ReportFacts, WindowFact
    paid = ReportFacts(
        access="paid",
        cards=[CardFacts(
            area="money",
            status="supported",
            wealth_sub=[{"key": "salary", "status": "supported"}],
            approved_remedies=["pearl"],
            remedy_eligible=True,
            window=WindowFact(start="2028-06", end="2029-02", label="career"),
            evidence=[],
        )],
        timing_windows=[WindowFact(start="2028-06", end="2029-02", label="career")],
    )
    free = project_for_access(paid, "free")
    assert free.access == "free"
    assert free.cards[0].wealth_sub == []
    assert free.cards[0].approved_remedies == []
    assert free.cards[0].window is not None
    assert free.cards[0].window.start == ""
    assert free.facts_hash  # resealed


# ---------------------------------------------------------------------------
# humanize with stubs
# ---------------------------------------------------------------------------
@pytest.fixture
def llm_on(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("LLM_TABS", "full_report,user_question,horary,palm,chat")
    from core import config as C
    C.S.llm_enabled = True
    C.S.llm_api_key = "test-key"
    C.S.llm_base_url = "http://127.0.0.1:9/v1"
    C.S.llm_tabs = "full_report,user_question,horary,palm,chat"
    yield
    from core.llm_client import clear_stub
    clear_stub()
    C.S.llm_enabled = False


@pytest.fixture
def llm_off(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "0")
    from core import config as C
    C.S.llm_enabled = False
    yield
    from core.llm_client import clear_stub
    clear_stub()


def test_humanize_disabled_returns_empty(llm_off):
    from llm.humanize import humanize
    facts = _card_facts()
    out = humanize("full_report", facts, access="paid")
    assert out["enabled"] is False
    assert out["overlay"] == {}


def test_humanize_happy_path(llm_on):
    from core.llm_client import set_stub
    from llm.humanize import humanize
    from llm.schemas import CardProse, ReportProse

    def stub(schema, system, user, **kw):
        if schema is CardProse:
            return CardProse.model_validate(GOOD_CARD)
        if schema is ReportProse:
            return ReportProse(opening="Meera, here is a clear read of your chart.")
        return None

    set_stub(stub)
    facts = _card_facts()
    out = humanize("full_report", facts, access="paid")
    assert out["enabled"] is True
    assert "profession" in out["overlay"].get("cards", {})
    assert out["stats"]["accepted"] >= 1
    assert out.get("fallback_used") is False


def test_humanize_schema_violation_falls_back(llm_on):
    from core.llm_client import set_stub
    from llm.humanize import humanize

    def stub(schema, system, user, **kw):
        return None

    set_stub(stub)
    out = humanize("full_report", _card_facts(), access="paid")
    # Deterministic fallback — prediction path still produces language
    assert "profession" in out["overlay"].get("cards", {})
    assert out["fallback_used"] is True
    assert out["stats"]["rejected"] >= 1


def test_humanize_fact_drift_rejected(llm_on):
    """Invented planet/date language must fail QA and use deterministic fallback."""
    from core.llm_client import set_stub
    from llm.humanize import humanize
    from llm.schemas import CardProse

    drifted = dict(
        GOOD_CARD,
        headline="Jupiter in your 10th house in March 2027 brings promotion.",
        summary="Saturn mahadasha guarantees wealth.",
    )

    def stub(schema, system, user, **kw):
        if schema is CardProse:
            return CardProse.model_validate(drifted)
        return None

    set_stub(stub)
    out = humanize("full_report", _card_facts(), access="paid")
    card = out["overlay"].get("cards", {}).get("profession") or {}
    assert card  # fallback present
    assert "Jupiter" not in (card.get("headline") or "")
    assert "guarantees" not in (card.get("summary") or card.get("why") or "").lower()
    assert out["fallback_used"] is True


def test_humanize_health_unsafe_rejected(llm_on):
    from core.llm_client import set_stub
    from llm.humanize import humanize
    from llm.schemas import CardProse

    unsafe = dict(
        GOOD_CARD,
        area="health",
        headline="You may face diabetes and heart disease soon.",
        summary="The chart shows organ failure risk.",
        how_this_may_show_up=["recurring illness"],
        what_to_watch=[],
        what_helps=["See a doctor for cancer screening."],
    )

    def stub(schema, system, user, **kw):
        if schema is CardProse:
            return CardProse.model_validate(unsafe)
        return None

    set_stub(stub)
    facts = _card_facts(area="health", status="strongly_indicated", direction="caution")
    facts.cards[0].kind = "challenge"
    out = humanize("full_report", facts, access="paid")
    card = out["overlay"].get("cards", {}).get("health") or {}
    assert card  # deterministic health-safe fallback
    blob = " ".join([
        card.get("headline", ""),
        card.get("summary", ""),
        " ".join(card.get("how_this_may_show_up") or []),
    ]).lower()
    assert "diabetes" not in blob
    assert "cancer" not in blob


@pytest.mark.parametrize("bad_headline,label", [
    ("Your spouse will leave in 2028.", "spouse"),
    ("Wear a ruby and chant daily for results.", "remedy"),
    ("You will be debt-ridden and hurt by fire.", "classical"),
    ("Relocate overseas as CEO next year.", "life_event"),
    ("Career success is guaranteed now.", "certainty"),
])
def test_failure_injection_uses_fallback(llm_on, bad_headline, label):
    from core.llm_client import set_stub
    from llm.humanize import humanize
    from llm.schemas import CardProse

    bad = dict(GOOD_CARD, headline=bad_headline, summary=bad_headline)

    def stub(schema, system, user, **kw):
        if schema is CardProse:
            return CardProse.model_validate(bad)
        return None

    set_stub(stub)
    out = humanize("full_report", _card_facts(), access="paid")
    card = out["overlay"]["cards"]["profession"]
    assert out["fallback_used"] is True, label
    assert bad_headline[:20].lower() not in (card.get("headline") or "").lower()


def test_question_and_horary_schemas():
    from llm.schemas import HoraryProse, QuestionProse
    q = QuestionProse(
        opening="Here is the straight read on your question.",
        answer="Your chart supports this move, with a narrower timing window.",
        timing="The strongest window is the one already dated in the facts.",
        action="Prepare quietly and move when the window opens.",
    )
    assert q.answer
    h = HoraryProse(
        lead="You asked about a decision in the moment.",
        verdict_line="The reading leans yes, with moderate confidence.",
        why="Both lanes favour the same direction.",
        action="Act inside the window the chart already shows.",
    )
    assert h.verdict_line


def test_chat_out_of_scope(llm_on):
    from core.llm_client import set_stub
    from llm.humanize import humanize_chat
    from llm.rules import OUT_OF_SCOPE_REFUSAL
    from llm.schemas import ChatAnswer

    def stub(schema, system, user, **kw):
        return ChatAnswer(
            answer="You will marry a foreigner in 2029.",
            used_fact_ids=[],
            out_of_scope=True,
        )

    set_stub(stub)
    out = humanize_chat(_card_facts(), "When will I marry a celebrity?")
    assert out["out_of_scope"] is True
    assert out["answer"] == OUT_OF_SCOPE_REFUSAL


def test_facts_builders_roundtrip():
    from llm.facts import build_horary_facts, build_question_facts, build_report_facts

    card = SimpleNamespace(
        area="money", label="Money", direction="up", house=2,
        window="later in the cycle", confluence={
            "promise": {
                "status": "supported", "score": 0.5, "confidence": "moderate",
                "supporting_evidence": ["natal support"],
                "caution_evidence": [],
            },
            "activation": {"status": "active"},
        },
        trajectory=[],
    )
    rf = build_report_facts({}, [card], name="Ramesh Kumar", access="paid")
    assert rf.cards[0].area == "money"
    assert rf.first_name == "Ramesh"
    assert rf.facts_hash
    assert rf.schema_version == "1.0"
    assert rf.cards[0].direction == "support"  # up → support
    assert "dob" not in rf.model_dump_json().lower()

    qf = build_question_facts({
        "question": "When will I change jobs?",
        "promise": {"direction": "up", "confidence": "moderate", "status": "supported"},
        "windows": [], "best": None, "nearest": None,
        "n_methods": 3, "n_up": 2, "n_down": 1,
        "route": {"domain": "career", "primary_house": 10},
        "area_key": "profession",
    }, name="Suresh", access="free")
    assert qf.kind == "user_question"
    assert qf.direction == "support"

    hf = build_horary_facts(
        question="Will this deal close?",
        verdicts={
            "vedic": {"verdict": "yes", "confidence": "good", "score": 0.6},
            "western": {"verdict": "yes", "confidence": "moderate", "score": 0.5},
        },
        summary={"label": "Yes", "confidence": "good", "score": 0.55,
                 "contradicted": False, "favourable": True, "subject": "this deal"},
        name="Meera",
    )
    assert hf.confidence == "high"  # "good" mapped
    assert len(hf.lanes) == 2


def test_report_cards_render_accepts_prose_kwarg():
    """Smoke: render signature accepts prose without requiring a full pc."""
    import inspect
    import report_cards as RC
    sig = inspect.signature(RC.render)
    assert "prose" in sig.parameters


def test_fallback_never_invents_dates():
    from llm.fallback import card_fallback
    from llm.schemas import CardFacts
    fb = card_fallback(CardFacts(
        area="profession", label="Career", status="strongly_supported",
        activation_status="mixed",
    ))
    assert "202" not in fb.get("headline", "")
    assert "guaranteed" not in fb.get("summary", "").lower()
