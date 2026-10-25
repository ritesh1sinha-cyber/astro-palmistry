"""The question answer is short, judged by the model against a trimmed fact
sheet, and falls back to the same shape when the model is off or wrong."""
from __future__ import annotations

import re

import question_reading as QR
from confluence_question_engine import DOMAINS_CONFIG, analyze_question_confluence

_PC = None


def _pc() -> dict:
    global _PC
    if _PC is None:
        from astro_precompute import resolve_precompute
        _PC = resolve_precompute("Test", "1985-03-08", birth_time="13:05",
                                 latitude=25.5941, longitude=85.1376, timezone=5.5,
                                 place_name="Patna", gender=1)
    return _PC


def _sheet(question: str, domain: str):
    pc = _pc()
    conf = analyze_question_confluence(pc, question, domain_override=domain)
    cfg = DOMAINS_CONFIG[conf.domain_key]
    return conf, pc, cfg, QR.build_fact_sheet(conf, pc, cfg)


def test_fact_sheet_has_no_specialist_lenses():
    conf, pc, cfg, facts = _sheet("which gemstone will suit me", "gemstones_remedies")
    prompt = QR._facts_for_prompt(facts)
    assert "Lal Kitab" not in prompt and "Chandra Naadi" not in prompt
    assert "Soya" not in prompt and "Pakka" not in prompt
    assert facts["gems"]["recommended"], "this chart has stones that suit it"
    assert len(prompt) < 2500, len(prompt)


def test_fallback_is_short_and_plain():
    for q, dom in [("which gemstone will suit me", "gemstones_remedies"),
                   ("when will I get promoted", "career_profession"),
                   ("will I move abroad", "foreign_relocation"),
                   ("how is my health", "health_vitality")]:
        conf, pc, cfg, facts = _sheet(q, dom)
        r = QR._fallback(facts)
        words = len(" ".join([r.answer, r.timing, *r.why, *r.steps]).split())
        assert words < 220, (q, words)
        assert 1 <= len(r.why) <= 4 and len(r.steps) <= 3
        assert not QR._check(r, facts), (q, QR._check(r, facts))
        assert not re.search(r"lal kitab|naadi|trikona|kendradhipati|dusthana", r.answer, re.I)


def test_out_of_domain_has_no_paywall():
    conf, pc, cfg, facts = _sheet("write python code", "out_of_domain")
    r = QR._fallback(facts)
    assert r.stance == "not_astrological"
    free = QR.render_html(r, facts, paid=False)
    assert "data-unlock" not in free


def test_free_locks_timing_paid_shows_it():
    conf, pc, cfg, facts = _sheet("when will I get promoted", "career_profession")
    r = QR._fallback(facts)
    free = QR.render_html(r, facts, paid=False)
    paid = QR.render_html(r, facts, paid=True)
    assert "data-unlock" in free and r.timing not in free
    assert "data-unlock" not in paid and "What to do" in paid
    assert r.answer in free and r.answer in paid


def test_model_answer_used_when_it_passes(monkeypatch=None):
    import core.llm_client as LC
    conf, pc, cfg, facts = _sheet("which gemstone will suit me", "gemstones_remedies")
    good = QR.QuestionReading(
        stance="favourable",
        answer="Emerald and Diamond suit your Gemini rising sign; avoid Red Coral.",
        why=["Mercury, your sign's ruler, makes Emerald a natural fit."],
        timing="", steps=["Wear Emerald on the little finger on a Wednesday morning."])
    seen = {}

    def stub(schema, system, user, **kw):
        seen["user"] = user
        return good

    LC.set_stub(stub)
    old = QR._llm_allowed
    QR._llm_allowed = lambda: True
    try:
        got = QR._ask_model(facts, "en")
    finally:
        LC.clear_stub()
        QR._llm_allowed = old
    assert got is good
    assert "Lal Kitab" not in seen["user"]


def test_model_answer_rejected_when_it_invents():
    import core.llm_client as LC
    conf, pc, cfg, facts = _sheet("which gemstone will suit me", "gemstones_remedies")
    bad = QR.QuestionReading(
        stance="favourable",
        answer="Wear Blue Sapphire. Lal Kitab says House 7 is Soya.",
        why=["Saturn rules luck."], timing="By March 2031.", steps=["Wear it daily."])
    LC.set_stub(lambda *a, **k: bad)
    old = QR._llm_allowed
    QR._llm_allowed = lambda: True
    try:
        assert QR._ask_model(facts, "en") is None
    finally:
        LC.clear_stub()
        QR._llm_allowed = old


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK ", name)
    print("ALL question_reading tests passed")
