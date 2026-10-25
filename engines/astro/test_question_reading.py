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


class _Model:
    """Install a fake model for one block."""

    def __init__(self, fn):
        self.fn = fn

    def __enter__(self):
        import core.llm_client as LC
        self.LC, self.old = LC, QR._llm_allowed
        LC.set_stub(self.fn)
        QR._llm_allowed = lambda: True

    def __exit__(self, *exc):
        self.LC.clear_stub()
        QR._llm_allowed = self.old


def test_prompt_has_no_specialist_lenses():
    for q, dom in [("which gemstone will suit me", "gemstones_remedies"),
                   ("when will I get promoted", "career_profession")]:
        conf, pc, cfg, facts = _sheet(q, dom)
        prompt = QR._prompt(facts)
        assert "Lal Kitab" not in prompt and "Chandra Naadi" not in prompt
        assert "Soya" not in prompt and "Pakka" not in prompt
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
        assert not QR._check(r.answer, facts), (q, QR._check(r.answer, facts))
        assert not re.search(r"lal kitab|naadi|trikona|kendradhipati|dusthana", r.answer, re.I)


def test_out_of_domain_never_reaches_the_model():
    conf, pc, cfg, facts = _sheet("write python code", "out_of_domain")

    def boom(*a, **k):
        raise AssertionError("model must not be called for an out-of-scope question")

    with _Model(boom):
        assert QR._ask_model(facts, "en") is None
    r = QR._fallback(facts)
    assert r.stance == "not_astrological"
    assert "data-unlock" not in QR.render_html(r, facts, paid=False)


def test_free_locks_timing_paid_shows_it():
    conf, pc, cfg, facts = _sheet("when will I get promoted", "career_profession")
    r = QR._fallback(facts)
    free = QR.render_html(r, facts, paid=False)
    paid = QR.render_html(r, facts, paid=True)
    assert r.timing and "data-unlock" in free and r.timing not in free
    assert "data-unlock" not in paid and "What to do" in paid
    assert r.answer in free and r.answer in paid
    assert not re.search(r"\b20\d\d\b", free.split('class="uq-reading"')[1]), "free half must carry no dates"


def test_model_judges_and_picks_reasons():
    conf, pc, cfg, facts = _sheet("when will I get promoted", "career_profession")
    seen = {}

    def stub(schema, system, user, **kw):
        seen["user"] = user
        return QR.QuestionJudgement(
            stance="difficult",
            answer="A promotion is hard to force right now because your career planet is weak.",
            use=["F1", "F3", "F99"], needs_timing=True)

    with _Model(stub):
        got = QR._ask_model(facts, "en")
    assert got is not None and got.stance == "difficult"
    table = dict(QR._findings(facts))
    assert got.why == [table["F1"], table["F3"]] or len(got.why) >= 2
    assert got.timing and "Lal Kitab" not in seen["user"]


def test_model_cannot_flip_the_chart_outlook():
    conf, pc, cfg, facts = _sheet("when will I get promoted", "career_profession")
    hint = QR._stance_hint(facts)
    flipped = "favourable" if hint == "difficult" else "difficult"
    if hint == "mixed":
        return
    with _Model(lambda *a, **k: QR.QuestionJudgement(
            stance=flipped, answer="Things look settled for you.", use=["F1", "F2"], needs_timing=False)):
        got = QR._ask_model(facts, "en")
    assert got.stance == hint


def test_model_answer_rejected_when_it_invents():
    conf, pc, cfg, facts = _sheet("which gemstone will suit me", "gemstones_remedies")
    bad = QR.QuestionJudgement(
        stance="favourable", answer="Wear Blue Sapphire. Lal Kitab says House 7 is Soya in 2031.",
        use=[], needs_timing=False)
    with _Model(lambda *a, **k: bad):
        assert QR._ask_model(facts, "en") is None


def test_gem_answer_must_name_every_stone():
    conf, pc, cfg, facts = _sheet("which gemstone will suit me", "gemstones_remedies")
    assert QR._check("Emerald is recommended for you.", facts), "dropping Diamond/avoid stones must fail"
    full = QR._fallback(facts).answer
    assert not QR._check(full, facts)


def test_stone_questions_are_routed_to_the_stone_audit():
    assert QR.is_gem_question("which stone should I wear for money")
    assert QR.is_gem_question("suggest the gemstone for this chart")
    assert not QR.is_gem_question("when will I get promoted")
    # A model that names a stone where the sheet has no stone list is rejected.
    conf, pc, cfg, facts = _sheet("how is my money", "wealth_finances")
    assert QR._check("You should wear a Hessonite for money.", facts)


_ENGLISH_FILLER = re.compile(
    r"\b(the|which|this|are|of|and|with|because|will|from|that|your|you|rules|sits|running)\b", re.I)


def test_hinglish_and_tenglish_are_fully_localised_and_keep_the_facts():
    for q, dom in [("meri shaadi kab hogi", "marriage_relationship"),
                   ("which stone should I wear", "gemstones_remedies"),
                   ("mera career kaisa rahega", "career_profession")]:
        conf, pc, cfg, facts = _sheet(q, dom)
        en = QR._fallback(facts, "en")
        for lang in ("hi_en", "te_en"):
            r = QR._fallback(facts, lang)
            lines = [r.answer, *r.why, r.timing, *r.steps]
            text = " ".join(lines)
            assert len(r.why) == len(en.why) and len(r.steps) == len(en.steps), (q, lang)
            assert not re.search(r"[\u0900-\u097F\u0C00-\u0C7F]", text), lang
            # prose is translated: English function words are gone (planet/stone names may stay)
            assert not _ENGLISH_FILLER.search(text), (q, lang, _ENGLISH_FILLER.search(text).group(0))
            # every number from the English reading survives (houses, scores, years)
            want = sorted(re.findall(r"\d+", " ".join([*en.why, en.timing])))
            got = sorted(re.findall(r"\d+", " ".join([*r.why, r.timing])))
            assert want == got, (q, lang, want, got)

def test_model_path_localises_the_answer_without_trusting_model_text():
    conf, pc, cfg, facts = _sheet("meri shaadi kab hogi", "marriage_relationship")
    with _Model(lambda *a, **k: QR.QuestionJudgement(
            stance=QR._stance_hint(facts), answer="You will marry soon.", use=["F1", "F2"],
            needs_timing=True)):
        got = QR._ask_model(facts, "hi_en")
    assert got is not None and "marry" not in got.answer and not _ENGLISH_FILLER.search(got.answer)


def test_wrong_planet_house_claim_is_caught():
    conf, pc, cfg, facts = _sheet("when will I get promoted", "career_profession")
    lord = facts["house"]["lord"]["planet"]
    wrong = (facts["house"]["lord"]["house"] % 12) + 1
    if (lord, wrong) in QR._true_claims(facts):
        return
    assert QR._check(f"You will be fine because {lord} sits in house {wrong}.", facts)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK ", name)
    print("ALL question_reading tests passed")
