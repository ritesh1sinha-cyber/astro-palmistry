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
    assert any(v.startswith("invented_astrology_term:") for v in check_prose(
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


GOOD_CONV = {
    "personality": "Meera, you tend to act when an opportunity is clear.",
    "current_phase": "Right now the chapter you are in reads as mixed.",
    "recent_months": "Home has been mostly workable in the recent months.",
    "hardest_area_note": "The area asking for more care right now is Work & Career.",
    "areas": [{
        "area": "profession",
        "outlook": "Your career theme is supported and currently active.",
        "timing": "Validated timing windows favour steady effort.",
        "manifestation": "recognition for steady work",
        "remedy": "Keep a weekly review habit and move on the openings that fit.",
    }],
}


def test_humanize_happy_path(llm_on):
    from core.llm_client import set_stub
    from llm.humanize import humanize
    from llm.schemas import ConversationalProse

    def stub(schema, system, user, **kw):
        if schema is ConversationalProse:
            return ConversationalProse.model_validate(GOOD_CONV)
        return None

    set_stub(stub)
    facts = _card_facts()
    out = humanize("full_report", facts, access="paid")
    assert out["enabled"] is True
    assert out["overlay"].get("conversational") is True
    assert "act when an opportunity" in out["overlay"].get("personality", "")
    assert "profession" in out["overlay"].get("areas", {})
    assert out["stats"]["accepted"] >= 1
    assert out.get("fallback_used") is False


def test_humanize_schema_violation_falls_back(llm_on):
    from core.llm_client import set_stub
    from llm.humanize import humanize

    def stub(schema, system, user, **kw):
        return None

    set_stub(stub)
    out = humanize("full_report", _card_facts(), access="paid")
    # Deterministic conversational fallback — accepted stays 0 so the
    # renderer switch keeps the classic frozen report.
    assert out["overlay"].get("conversational") is True
    assert out["overlay"].get("personality")
    assert out["fallback_used"] is True
    assert out["stats"]["rejected"] >= 1
    assert out["stats"]["accepted"] == 0


def test_humanize_fact_drift_rejected(llm_on):
    """Invented planet/date language must fail QA and use deterministic fallback."""
    from core.llm_client import set_stub
    from llm.humanize import humanize
    from llm.schemas import ConversationalProse

    drifted = dict(
        GOOD_CONV,
        personality="Jupiter in your 10th house in March 2027 brings promotion.",
        current_phase="Saturn mahadasha guarantees wealth.",
    )

    def stub(schema, system, user, **kw):
        if schema is ConversationalProse:
            return ConversationalProse.model_validate(drifted)
        return None

    set_stub(stub)
    out = humanize("full_report", _card_facts(), access="paid")
    # Bad slots are replaced with deterministic fact prose; clean slots survive.
    assert out["stats"]["rejected"] >= 1
    blob = " ".join([
        out["overlay"].get("personality", ""),
        out["overlay"].get("current_phase", ""),
    ])
    assert "Jupiter" not in blob
    assert "guarantees" not in blob.lower()


def test_humanize_health_unsafe_rejected(llm_on):
    from core.llm_client import set_stub
    from llm.humanize import humanize
    from llm.schemas import ConversationalProse

    unsafe = dict(
        GOOD_CONV,
        personality="You may face diabetes and heart disease soon.",
        current_phase="The chart shows organ failure risk.",
        areas=[{
            "area": "health",
            "outlook": "You may face diabetes soon.",
            "timing": "",
            "manifestation": "recurring illness",
            "remedy": "See a doctor for cancer screening.",
        }],
    )

    def stub(schema, system, user, **kw):
        if schema is ConversationalProse:
            return ConversationalProse.model_validate(unsafe)
        return None

    set_stub(stub)
    facts = _card_facts(area="health", status="strongly_indicated", direction="caution")
    facts.cards[0].kind = "challenge"
    out = humanize("full_report", facts, access="paid")
    assert out["stats"]["rejected"] >= 1
    blob = " ".join([
        out["overlay"].get("personality", ""),
        out["overlay"].get("current_phase", ""),
        str((out["overlay"].get("areas") or {}).get("health") or {}),
    ]).lower()
    assert "diabetes" not in blob
    assert "cancer" not in blob


@pytest.mark.parametrize("bad_line,label", [
    ("Your spouse will leave in 2028.", "spouse"),
    ("Wear a ruby and chant daily for results.", "remedy"),
    ("You will be debt-ridden and hurt by fire.", "classical"),
    ("Relocate overseas as CEO next year.", "life_event"),
    ("Career success is guaranteed now.", "certainty"),
])
def test_failure_injection_uses_fallback(llm_on, bad_line, label):
    from core.llm_client import set_stub
    from llm.humanize import humanize
    from llm.schemas import ConversationalProse

    bad = dict(GOOD_CONV, personality=bad_line, current_phase=bad_line)

    def stub(schema, system, user, **kw):
        if schema is ConversationalProse:
            return ConversationalProse.model_validate(bad)
        return None

    set_stub(stub)
    out = humanize("full_report", _card_facts(), access="paid")
    assert out["stats"]["rejected"] >= 1, label
    blob = " ".join([
        out["overlay"].get("personality") or "",
        out["overlay"].get("current_phase") or "",
    ]).lower()
    assert bad_line[:20].lower() not in blob, label


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


def test_palm_chat_job_change_is_not_refused(llm_on):
    """A palm follow-up naming a life area the reading shows is that reading.

    The old gate only accepted user_question / horary, so a valid career
    question on a palm report fell through to the canned refusal whenever the
    model answer failed QA.
    """
    from core.llm_client import set_stub
    from llm.humanize import humanize_chat
    from llm.schemas import ChatAnswer

    def stub(schema, system, user, **kw):
        return ChatAnswer(
            answer="You will definitely change jobs in June for sure.",
            used_fact_ids=["semantic_summary"],
        )

    set_stub(stub)
    out = humanize_chat(_palm_chat_facts(), "is there a job change seen in near future")
    assert out["out_of_scope"] is False
    assert "life area" not in out["answer"].lower()
    assert "fate line" in out["answer"].lower()


def test_palm_chat_thumb_question_is_on_topic():
    from llm.rules import followup_is_on_asked_topic

    assert followup_is_on_asked_topic(
        _palm_chat_facts(), "what is seen from my thumb length"
    ) is True


def test_palm_chat_out_of_scope_stays_refused(llm_on):
    """A palm follow-up about something the hand can't show stays refused."""
    from core.llm_client import set_stub
    from llm.humanize import humanize_chat
    from llm.schemas import ChatAnswer

    def stub(schema, system, user, **kw):
        return ChatAnswer(
            answer="The stars align for a lottery win.",
            used_fact_ids=[],
            out_of_scope=True,
        )

    set_stub(stub)
    out = humanize_chat(_palm_chat_facts(), "what is my lottery number")
    assert out["out_of_scope"] is True


def _question_case_facts():
    from llm.schemas import QuestionFacts, WindowFact

    return QuestionFacts(
        first_name="Meera",
        access="paid",
        question="will i win the case",
        area_key="legal",
        direction="support",
        confidence="low",
        promise_status="mixed",
        route={"domain": "legal", "topic": "litigation"},
        best=WindowFact(start="April 2030", end="May 2032", confidence="low"),
        windows=[WindowFact(start="April 2030", end="May 2032", confidence="low")],
        allowed_dates=["April 2030", "May 2032"],
    )


def test_chat_legal_followup_is_not_refused_as_a_new_life_area(llm_on):
    """Ask-your-chart already answered the case; 'when is the verdict' is that reading."""
    from core.llm_client import set_stub
    from llm.humanize import humanize_chat
    from llm.schemas import ChatAnswer

    def stub(schema, system, user, **kw):
        return ChatAnswer(
            answer="You will win the case in 2031 for sure.",
            used_fact_ids=["timing"],
        )

    set_stub(stub)
    out = humanize_chat(_question_case_facts(), "when i can expect verdict")
    assert out["out_of_scope"] is False
    assert "April 2030" in out["answer"]
    assert "May 2032" in out["answer"]
    assert "life area" not in out["answer"].lower()


def test_chat_cannot_mark_the_asked_case_out_of_scope(llm_on):
    from core.llm_client import set_stub
    from llm.humanize import humanize_chat
    from llm.schemas import ChatAnswer

    def stub(schema, system, user, **kw):
        return ChatAnswer(
            answer="That is not in this reading.",
            used_fact_ids=[],
            out_of_scope=True,
        )

    set_stub(stub)
    out = humanize_chat(_question_case_facts(), "am asking about case only")
    assert out["out_of_scope"] is False
    assert "April 2030" in out["answer"]


def test_chat_prompt_actually_carries_the_report_facts(llm_on):
    """Regression: the chat message used to reach the model as {"question": …}.

    The wrapper dict was passed through the fact allowlist, which dropped
    facts/history/ids, so every answer was ungrounded model knowledge.
    """
    from core.llm_client import set_stub
    from llm.humanize import humanize_chat
    from llm.schemas import ChatAnswer

    seen = {}

    def stub(schema, system, user, **kw):
        seen["user"] = user
        return ChatAnswer(
            answer="Your work and career reads as mixed for now.",
            used_fact_ids=["promise"],
        )

    set_stub(stub)
    facts = _card_facts(area="career", status="mixed")
    facts.cards[0].label = "Work & Career"
    humanize_chat(
        facts,
        "What about my career?",
        history=[{"role": "user", "content": "Tell me about work"}],
    )
    sent = seen["user"]
    assert "Work & Career" in sent
    assert "mixed" in sent
    assert "What about my career?" in sent
    assert "Tell me about work" in sent


def test_chat_answer_cannot_overclaim_a_weak_area():
    from llm.schemas import ChatAnswer
    from llm.validate import validate_chat_answer

    facts = _card_facts(area="career", status="insufficient_evidence")
    facts.cards[0].label = "Work & Career"
    bad = ChatAnswer(
        answer="Your Work & Career is strongly supported and success is guaranteed.",
        used_fact_ids=["promise"],
    )
    assert any(e.startswith("chat_overclaim_status") for e in
               validate_chat_answer(bad, facts))
    ok = ChatAnswer(
        answer="Your Work & Career reads as mixed, so steady effort matters most.",
        used_fact_ids=["promise"],
    )
    assert validate_chat_answer(ok, facts) == []


def _horary_facts(label="no", favourable=False, contradicted=False):
    from llm.schemas import HoraryFacts, HoraryLaneFact

    return HoraryFacts(
        first_name="Meera",
        access="paid",
        question="Will I get the job I interviewed for?",
        subject="job offer",
        label=label,
        confidence="moderate",
        favourable=favourable,
        contradicted=contradicted,
        lanes=[HoraryLaneFact(lane="vedic", verdict=label, confidence="moderate")],
    )


def _palm_chat_facts(direction="caution", strength="tentative"):
    from llm.schemas import PalmAspectFacts, PalmFacts

    return PalmFacts(
        first_name="Meera",
        access="paid",
        age_years=36,
        aspects=[PalmAspectFacts(
            aspect="career",
            title="Work and direction",
            direction=direction,
            strength=strength,
            confidence="low",
            semantic_summary="The fate line runs light through this stretch.",
            recognize=["work that changes shape more than once"],
        )],
    )


def test_chat_grounding_runs_on_facts_loaded_from_storage():
    """Regression: chat reloads facts.json, so grounding must read dicts.

    Every gate used getattr, which returns nothing for a dict — so on the one
    path that matters in production, an answer could overclaim freely.
    """
    from llm.schemas import ChatAnswer
    from llm.validate import validate_chat_answer

    facts = _card_facts(area="career", status="insufficient_evidence")
    facts.cards[0].label = "Work & Career"
    as_dict = facts.model_dump(mode="json")

    bad = ChatAnswer(
        answer="Your Work & Career is strongly supported and success is guaranteed.",
        used_fact_ids=["promise"],
    )
    assert any(e.startswith("chat_overclaim_status") for e in
               validate_chat_answer(bad, as_dict))


def test_chat_cannot_reverse_a_horary_verdict():
    from llm.schemas import ChatAnswer
    from llm.validate import validate_chat_answer

    facts = _horary_facts(label="no", favourable=False)
    bad = ChatAnswer(
        answer="Yes, the job is very likely to come through.",
        used_fact_ids=["verdict"],
    )
    assert "chat_horary_verdict_flip" in validate_chat_answer(bad, facts)

    ok = ChatAnswer(
        answer="The reading does not favour this one, so keep other options open.",
        used_fact_ids=["verdict"],
    )
    assert validate_chat_answer(ok, facts) == []


def test_horary_chat_may_use_the_words_yes_and_no_in_passing():
    """The flip gate matched a bare yes/no, which refused fair answers."""
    from llm.schemas import ChatAnswer
    from llm.validate import validate_chat_answer

    facts = _horary_facts(label="Leaning yes", favourable=True)
    ok = ChatAnswer(
        answer=("The reading leans towards a yes on this one. There is no fixed "
                "date in your reading, so treat it as a lean rather than a promise."),
        used_fact_ids=["verdict"],
    )
    assert validate_chat_answer(ok, facts) == []


def test_chat_may_cite_any_field_the_facts_actually_contain():
    """Live horary answers were refused for citing `favourable`.

    The citable list was hand-written around chart reports, so real fields on
    a horary or palm reading counted as unknown ids and the whole answer was
    thrown away.
    """
    from llm.schemas import ChatAnswer
    from llm.validate import validate_chat_answer

    facts = _horary_facts(label="Leaning yes", favourable=True)
    ok = ChatAnswer(
        answer="The reading leans towards a yes, with moderate confidence.",
        used_fact_ids=["favourable", "label", "confidence"],
    )
    assert validate_chat_answer(ok, facts) == []

    palm = _palm_chat_facts()
    ok_palm = ChatAnswer(
        answer="Your work and direction reads light, so steady effort is the ask.",
        used_fact_ids=["semantic_summary", "strength"],
    )
    assert validate_chat_answer(ok_palm, palm) == []

    bad = ChatAnswer(
        answer="The reading leans towards a yes.",
        used_fact_ids=["spouse_promise"],
    )
    assert any(e.startswith("chat_unknown_fact_id") for e in
               validate_chat_answer(bad, facts))


def test_chat_speaks_to_the_person_not_about_them_by_name():
    """A live palm answer said "the aspects of Meera's hand reading".

    The pronoun gate caught she/he but not the reader's own name, which is
    sitting right there in the facts the model was handed.
    """
    from llm.schemas import ChatAnswer
    from llm.validate import validate_chat_answer

    facts = _palm_chat_facts()
    bad = ChatAnswer(
        answer="The mixed strengths in Meera's hand reading point to steady effort.",
        used_fact_ids=["aspect"],
    )
    assert any("third_person_reader" in e for e in validate_chat_answer(bad, facts))

    ok = ChatAnswer(
        answer="The mixed strengths in your hand reading point to steady effort.",
        used_fact_ids=["aspect"],
    )
    assert validate_chat_answer(ok, facts) == []


def test_chat_stays_cautious_when_the_horary_methods_disagreed():
    from llm.schemas import ChatAnswer
    from llm.validate import validate_chat_answer

    facts = _horary_facts(label="yes", favourable=True, contradicted=True)
    bad = ChatAnswer(
        answer="This is guaranteed to work out for you.",
        used_fact_ids=["verdict"],
    )
    assert "chat_horary_certainty_on_contradicted" in validate_chat_answer(bad, facts)


def test_chat_cannot_overclaim_a_tentative_palm_aspect():
    from llm.schemas import ChatAnswer
    from llm.validate import validate_chat_answer

    facts = _palm_chat_facts()
    bad = ChatAnswer(
        answer="Your work and direction is strongly supported — excellent prospects.",
        used_fact_ids=["aspect"],
    )
    assert any(e.startswith("chat_palm_overclaim") for e in
               validate_chat_answer(bad, facts))

    ok = ChatAnswer(
        answer="Your work and direction reads light here, so steady effort is the ask.",
        used_fact_ids=["aspect"],
    )
    assert validate_chat_answer(ok, facts) == []


def test_chat_cannot_invent_an_age_from_a_palm_reading():
    from llm.schemas import ChatAnswer
    from llm.validate import validate_chat_answer

    facts = _palm_chat_facts()
    bad = ChatAnswer(
        answer="This shift arrives at age 42 for you.",
        used_fact_ids=["aspect"],
    )
    assert "palm_unvalidated_age" in validate_chat_answer(bad, facts)


def test_palm_facts_persisted_for_chat_carry_no_internal_fields():
    """Palm stored a raw model dump while every other kind stored the
    allowlisted payload, so internal engine fields reached facts.json."""
    from llm.facts import public_fact_payload

    payload = public_fact_payload(_palm_chat_facts())
    assert payload["kind"] == "palm"
    assert payload["aspects"][0]["aspect"] == "career"
    for internal in ("facts_hash", "engine_version", "schema_version", "report_id"):
        assert internal not in payload


def test_facts_builders_roundtrip():
    from llm.facts import build_horary_facts, build_question_facts, build_report_facts
    from llm.schemas import SCHEMA_VERSION

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
    assert rf.schema_version == SCHEMA_VERSION
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


def _facts_with_period(lord="Jupiter", sub="Saturn"):
    from llm.schemas import VedicContext
    facts = _card_facts()
    return facts.model_copy(update={
        "vedic_context": VedicContext(
            period_lord=lord,
            sub_period_lord=sub,
            mahadasha=lord,
            antardasha=sub,
            lagna="Aries",
            start="2024-01-01",
            end="2026-10-01",
            rising_sign="Aries",
            moon_sign="Leo",
        ),
    })


def test_check_prose_allows_grounded_vedic_terms():
    from llm.rules import check_prose
    facts = _facts_with_period()
    text = (
        "You are in a Jupiter mahadasha, with Saturn running the current antardasha. "
        "This stretch runs through October 2026."
    )
    assert check_prose(text, facts) == []


def test_check_prose_allows_grounded_planet_and_house():
    from llm.rules import check_prose
    from llm.schemas import CardFacts
    facts = _facts_with_period(lord="Saturn", sub="Jupiter")
    facts = facts.model_copy(update={
        "cards": [CardFacts(
            area="profession", label="Career", status="supported",
            activation_status="active", house=10,
            allowed_planets=["Saturn"],
        )],
    })
    text = (
        "Saturn's influence on the 10th house is making progress more "
        "responsibility-driven in this period."
    )
    assert check_prose(text, facts) == []


def test_check_prose_blocks_ungrounded_navamsha():
    from llm.rules import check_prose
    facts = _facts_with_period()
    fails = check_prose("Your Navamsha supports marriage now.", facts)
    assert any(v.startswith("invented_astrology_term:") for v in fails)


def test_check_prose_blocks_wrong_planet():
    from llm.rules import check_prose
    facts = _facts_with_period(lord="Jupiter", sub="Moon")
    fails = check_prose(
        "You are running a Saturn mahadasha in this period.",
        facts,
    )
    assert "unexpected_planet:saturn" in fails


def test_timing_sentence_drops_internal_window_keys():
    from llm.fallback import timing_sentence
    assert timing_sentence("children_window") == ""
    assert timing_sentence("learning_window") == ""
    assert "May 2024" in timing_sentence("May 2024 to October 2026")


def test_area_outlook_keeps_manifestation_words():
    from llm.fallback import _area_outlook_sentence
    from llm.schemas import CardFacts
    card = CardFacts(
        area="money", label="Money", status="mixed",
        activation_status="mixed",
        manifestations=["savings quietly leaking away"],
    )
    text = _area_outlook_sentence(card, "Money")
    assert "leaking" in text.lower() or "savings" in text.lower()
    assert "neither the chart nor the current phase" not in text.lower()


def test_validate_retains_fact_terms_rejects_generic_rewrite():
    from llm.validate import validate_retains_fact_terms
    sources = ["savings quietly leaking away", "role expansion"]
    assert validate_retains_fact_terms(
        "Steady deliberate effort matters more than waiting for a perfect moment.",
        sources,
    ) == ["generic_rewrite_drops_facts"]
    assert validate_retains_fact_terms(
        "Money leaks away unless you strengthen savings.",
        sources,
    ) == []


def test_palm_fallback_scrubs_bodily_claims_and_character_repeat():
    from llm.fallback import conversational_palm_fallback
    from llm.schemas import PalmAspectFacts, PalmFacts
    facts = PalmFacts(
        first_name="Meera", access="paid",
        personality_traits=[
            "Your energy is strongly tied to thinking, conversation and interaction; "
            "repetitive isolation can leave you mentally flat."
        ],
        aspects=[
            PalmAspectFacts(
                aspect="character", title="Character & Temperament",
                semantic_summary=(
                    "Your energy is strongly tied to thinking, conversation and interaction; "
                    "repetitive isolation can leave you mentally flat."
                ),
                recognize=["you think better by talking things through"],
            ),
            PalmAspectFacts(
                aspect="health", title="Health & Vitality",
                direction="caution", strength="tentative",
                semantic_summary=(
                    "Stress may show up first as changes in digestion, tension or "
                    "nervous energy, so noticing your body's early signals can be useful."
                ),
                recognize=["more attention to routine"],
            ),
        ],
        demanding_aspect="health",
        demanding_aspect_label="Health & Vitality",
    )
    fb = conversational_palm_fallback(facts)
    char = (fb.get("areas") or {}).get("character") or {}
    health = (fb.get("areas") or {}).get("health") or {}
    assert "digestion" not in str(health.get("outlook") or "").lower()
    personality = str(fb.get("personality") or "")
    outlook = str(char.get("outlook") or "")
    assert outlook
    assert outlook[:80].lower() not in personality.lower()


def test_merge_drops_manifestation_that_repeats_remedy():
    from llm.humanize import _merge_conversational_facts
    from llm.schemas import CardFacts, ReportFacts
    card = CardFacts(
        area="money", label="Money", status="mixed",
        activation_status="mixed",
        remedy_text="Use the easier phase to strengthen savings.",
        manifestations=["savings quietly leaking away"],
    )
    facts = ReportFacts(access="paid", cards=[card])
    overlay = {
        "personality": "Your nature is consistent across work and home decisions.",
        "current_phase": "This period pulls two ways at once and asks for patience here.",
        "areas": {
            "money": {
                "outlook": "Money is mixed.",
                "manifestation": "Use the easier phase to strengthen savings.",
                "remedy": "Use the easier phase to strengthen savings.",
            }
        },
    }
    merged = _merge_conversational_facts(overlay, facts, access="paid")
    money = (merged.get("areas") or {}).get("money") or {}
    assert money.get("remedy")
    assert str(money.get("manifestation") or "").strip() == ""


def test_confluence_classical_reprise_merges(llm_on):
    """The classical rephrase pass must overwrite the page prose from a valid
    ReportConfluenceProse reply, and inject a classical interpretation per area,
    while the conversational fallback supplies the area shell."""
    from core.llm_client import set_stub
    from llm.humanize import humanize
    from llm.schemas import ConversationalProse, ReportConfluenceProse

    classical = ReportConfluenceProse(
        astrological_basis=(
            "Your chart runs under Jupiter's main period with Mercury as the "
            "sub-period lord, and the Moon placed in Gemini."
        ),
        interpretation="This chapter reads as mentally active and communication-led.",
        personality="Your mind leads the way most weeks; you think better by talking things through.",
        current_phase="Momentum is gathering in creative and professional directions.",
        hardest_area_note="The area asking for more care right now is Health & Vitality.",
        mind_now=["if recognition feels a little slow just now"],
        why_now="Jupiter supports reflection while Mercury shapes how ideas take shape.",
        family_note=["your father comes across as steady and measured"],
        areas={"profession": "Work moves ahead with steady visibility under the current period."},
    )

    def stub(schema, system, user, **kw):
        if schema is ConversationalProse:
            return ConversationalProse.model_validate(GOOD_CONV)
        if schema is ReportConfluenceProse:
            return classical
        return None

    set_stub(stub)
    out = humanize("full_report", _card_facts(), access="paid")
    assert out["enabled"] is True
    ov = out["overlay"]
    # The whole astrological_basis line is taken from the classical reprise.
    assert ov.get("astrological_basis") == classical.astrological_basis
    assert "Jupiter's main period" in ov.get("astrological_basis", "")
    assert "Mercury as the sub-period lord" in ov.get("astrological_basis", "")
    # The classical per-area interpretation lands in the existing area shell.
    assert "profession" in (ov.get("areas") or {})
    prof = (ov.get("areas") or {}).get("profession") or {}
    assert "Work moves ahead with steady visibility" in prof.get("interpretation", "")


def test_validate_dasha_lords_catches_misattributed_periods():
    from llm.schemas import ReportFacts, VedicContext
    from llm.validate import validate_dasha_lords

    facts = ReportFacts(
        first_name="Ritesh",
        access="paid",
        vedic_context=VedicContext(
            period_lord="Jupiter",
            sub_period_lord="Ketu",
            mahadasha="Jupiter",
            antardasha="Ketu",
            rising_sign="Gemini",
            moon_sign="Virgo",
        ),
    )

    # 1. Hallucinated Venus main period and Saturn sub period must be flagged
    bad_prose = (
        "The weak Venus main period suggests challenges in relationships and partnerships, "
        "while Saturn's influence in the sub period adds pressure, making progress feel slower."
    )
    errs = validate_dasha_lords(bad_prose, facts)
    assert any("dasha_lord_mismatch:main_period:Venus" in e for e in errs)
    assert any("dasha_lord_mismatch:sub_period:Saturn" in e for e in errs)

    # 2. Correct Jupiter main period and Ketu sub period must pass with zero errors
    good_prose = (
        "Running Jupiter main period with Ketu sub period brings reflection, "
        "while Venus in the 10th house and Saturn in the 6th house govern specific areas."
    )
    assert validate_dasha_lords(good_prose, facts) == []

    # 3. Mismatched compound dasha must be flagged
    compound_bad = "Under the Venus-Saturn dasha sequence, changes unfold slowly."
    errs_compound = validate_dasha_lords(compound_bad, facts)
    assert any("dasha_sequence_mismatch:Venus-Saturn" in e for e in errs_compound)


def test_build_personal_life_extracts_classical_predictions():
    from llm.personal_life import build_personal_life

    # Chart with Sun in 5th (positive father signal), Moon in 4th (positive mother),
    # 3rd lord well placed. Jupiter lagna for positive classical lines.
    pc = {
        "lagna": {"sign": "Gemini", "deg": 15.0},
        "planets": {
            "Sun": {"sign": "Libra", "house": 5, "dignity": "enemy_sign"},
            "Moon": {"sign": "Virgo", "house": 4, "dignity": "neutral", "nakshatra": "Hasta"},
            "Mars": {"sign": "Scorpio", "house": 6, "dignity": "own_sign"},
            "Mercury": {"sign": "Pisces", "house": 10, "dignity": "debilitated"},
            "Jupiter": {"sign": "Cancer", "house": 2, "dignity": "exalted"},
            "Venus": {"sign": "Pisces", "house": 10, "dignity": "exalted"},
            "Saturn": {"sign": "Scorpio", "house": 6, "dignity": "enemy_sign"},
            "Rahu": {"sign": "Aries", "house": 11, "dignity": "neutral"},
            "Ketu": {"sign": "Libra", "house": 5, "dignity": "neutral"},
        },
        "vimshottari": {
            "current_md": {"lord": "Jupiter", "name": "Jupiter"},
            "current_md_antardashas": [{"lord": "Ketu", "name": "Ketu", "status": "current"}],
        },
        "meta": {"client": "Ritesh", "dob": "1986-03-08"},
    }

    traits, family_notes = build_personal_life(pc)
    assert len(traits) > 0, "Should extract at least some personality traits"
    assert len(family_notes) > 0, "Should extract at least some family notes"
    relations = {fn.relation for fn in family_notes}
    # Mother (Moon in 4th) always produces positive classical text
    assert "mother" in relations, f"Should have mother note, got: {relations}"
    # At least 2 relations should appear — classical filter legitimately drops negative-only placements
    assert len(relations) >= 2, f"Should have at least 2 family relations, got: {relations}"



