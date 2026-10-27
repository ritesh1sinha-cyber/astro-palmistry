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


def test_prompt_has_no_lal_kitab_filler():
    for q, dom in [("which gemstone will suit me", "gemstones_remedies"),
                   ("when will I get promoted", "career_profession")]:
        conf, pc, cfg, facts = _sheet(q, dom)
        prompt = QR._prompt(facts)
        assert "Lal Kitab" not in prompt and "Soya" not in prompt and "Pakka" not in prompt
        assert len(prompt) < 3600, len(prompt)


def test_prompt_carries_every_lens_and_their_votes():
    conf, pc, cfg, facts = _sheet("is job change seen in near future", "career_profession")
    prompt = QR._prompt(facts)
    for tag in ("[birth promise]", "[running period]", "[Chara period]", "[Yogini]", "[transit]", "[Chandra Naadi]"):
        assert tag in prompt, tag
    assert "How the lenses line up:" in prompt


def test_rashi_drishti_follows_the_jaimini_rule():
    import question_lenses as QL
    assert {"Aquarius", "Aries", "Cancer", "Libra"} == QL.rashi_drishti("Aquarius")      # fixed -> movable, not Capricorn
    assert {"Gemini", "Virgo", "Sagittarius", "Pisces"} == QL.rashi_drishti("Gemini")    # dual -> other duals
    assert "Taurus" not in QL.rashi_drishti("Aries") and "Leo" in QL.rashi_drishti("Aries")


def test_each_lens_votes_from_the_chart_and_the_verdict_uses_them():
    import question_lenses as QL
    conf, pc, cfg, facts = _sheet("is job change seen in near future", "career_profession")
    lenses = facts["lenses"]
    assert set(lenses) == set(QL.LENS_ORDER) - {"vulnerability"}, lenses.keys()    # health-only lens
    assert all(v["vote"] in (-1, 0, 1) for v in lenses.values())
    # the stance is the weighted vote, nothing else
    assert QR._stance_hint(facts) == QL.stance(lenses)
    # promise vs now picks the sentence; flipping the live votes changes the verdict
    for k in lenses:
        if k != "promise":
            lenses[k]["vote"] = 1
    lenses["promise"]["vote"] = -1
    weak_but_helped = QR._fallback(facts).answer
    for k in lenses:
        if k != "promise":
            lenses[k]["vote"] = -1
    weak_and_blocked = QR._fallback(facts).answer
    assert weak_but_helped != weak_and_blocked and QR._stance_hint(facts) == "difficult"


def test_chandra_naadi_is_in_the_reasons_and_the_page():
    conf, pc, cfg, facts = _sheet("is job change seen in near future", "career_profession")
    r = QR._fallback(facts)
    assert any(w.startswith("Chandra Naadi:") for w in r.why), r.why
    assert {l["key"] for l in r.lenses} == {"promise", "vimshottari", "jaimini", "yogini", "transit", "naadi"}
    page = QR.render_html(r, facts, paid=True)
    assert "Chandra Naadi" in page and "Chara period" in page and "Yogini" in page and "uq-lenses" in page
    # the free half only counts the lenses; what each one found stays behind the lock
    free = QR.render_html(r, facts, paid=False)
    assert "more perspectives were checked" in free and "Chara period" not in free and "Yogini" not in free
    assert free.count("<li") <= 3


def test_model_reasons_always_cover_the_promise_and_something_running_now():
    conf, pc, cfg, facts = _sheet("is job change seen in near future", "career_profession")
    lens_of = {fid: lens for fid, lens, _t in QR._findings_full(facts)}
    with _Model(lambda *a, **k: QR.QuestionJudgement(
            stance=QR._stance_hint(facts), answer="Your career planet is weak right now.",
            use=["F2"], needs_timing=False)):
        got = QR._ask_model(facts, "en")
    table = {t: lens_of[i] for i, t in QR._findings(facts)}
    lenses = {table[w] for w in got.why}
    assert "promise" in lenses and len(lenses - {"promise"}) >= 1 and len(got.why) <= 6


def test_headline_is_one_whole_sentence():
    a = "Job change is seen as difficult in the near future. Jupiter, ruling your career, is weak."
    assert QR.headline(a) == "Job change is seen as difficult in the near future."
    long = "Your chart " + "really " * 40 + "supports this."
    h = QR.headline(long, 60)
    assert h.endswith("...") and len(h) <= 64 and not h[:-3].endswith(" ")


def test_fallback_is_short_and_plain():
    for q, dom in [("which gemstone will suit me", "gemstones_remedies"),
                   ("when will I get promoted", "career_profession"),
                   ("will I move abroad", "foreign_relocation"),
                   ("how is my health", "health_vitality")]:
        conf, pc, cfg, facts = _sheet(q, dom)
        r = QR._fallback(facts)
        words = len(" ".join([r.answer, r.timing, *r.why, *r.steps]).split())
        # health also carries the body-pattern reason, the care window and one preventive habit
        assert words < (290 if dom == "health_vitality" else 235), (q, words)
        assert 1 <= len(r.why) <= 6 and len(r.steps) <= 3
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
    import html as _html
    assert _html.escape(r.answer) in free and _html.escape(r.answer) in paid
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


def test_a_named_stone_is_answered_first():
    assert QR.asked_planets("Is blue sapphire suited for me") == ["Saturn"]
    assert QR.asked_planets("is neelam good for me") == ["Saturn"]
    assert set(QR.asked_planets("should I wear a sapphire")) == {"Saturn", "Jupiter"}
    assert QR.asked_planets("which gemstone will suit me") == []
    conf, pc, cfg, facts = _sheet("Is blue sapphire suited for me", "gemstones_remedies")
    asked = facts["gems"]["asked"]
    assert [a["gem"] for a in asked] == ["Blue Sapphire (Neelam)"] and asked[0]["verdict"] == "mantra"
    r = QR._fallback(facts)
    assert r.answer.startswith("Blue Sapphire (Neelam) is not advised"), r.answer
    assert "Emerald" in r.answer, "then name the stones that do suit the reader"
    assert r.stance == "difficult" and "Saturn rules your 8th and 9th houses" in r.why[0], r.why[0]
    assert r.steps[0].startswith("Skip Blue Sapphire") and len(r.steps) <= 3
    # a stone the audit says suits the reader is answered as a yes
    conf, pc, cfg, facts = _sheet("is emerald good for me", "gemstones_remedies")
    r = QR._fallback(facts)
    assert r.answer.startswith("Emerald (Panna) suits you") and r.stance == "favourable", r.answer


def test_model_must_answer_about_the_named_stone_and_match_the_audit():
    conf, pc, cfg, facts = _sheet("Is blue sapphire suited for me", "gemstones_remedies")
    assert QR._check("Emerald and Diamond suit you best for your Gemini rising sign.", facts), \
        "an answer that never mentions Blue Sapphire must fail"
    assert QR._check("Blue Sapphire (Neelam) suits you well, so wear it.", facts), \
        "saying yes when the audit says no must fail"
    assert not QR._check("Blue Sapphire (Neelam) is not advised for you; use Saturn's mantra instead. "
                         "Emerald (Panna) suits you.", facts)
    seen = {}

    def stub(schema, system, user, **kw):
        seen["user"] = user
        return QR.QuestionJudgement(
            stance="favourable", answer="Blue Sapphire (Neelam) is not advised for you.",
            because="Your Saturn is not a safe stone planet, so mantra and charity work better.",
            use=[], needs_timing=False)

    with _Model(stub):
        got = QR._ask_model(facts, "en")
    assert "ASKED STONE: Blue Sapphire (Neelam)" in seen["user"]
    assert got is not None and got.stance == "difficult", "the audit, not the model, sets the outlook"
    assert "Saturn rules your 8th and 9th houses" in got.why[0]


def test_named_stone_answer_is_localised():
    conf, pc, cfg, facts = _sheet("Is blue sapphire suited for me", "gemstones_remedies")
    for lang in ("hi_en", "te_en"):
        r = QR._fallback(facts, lang)
        text = " ".join([r.answer, *r.why, *r.steps])
        assert "Blue Sapphire (Neelam)" in r.answer and not _ENGLISH_FILLER.search(text), (lang, text)
        assert not re.search(r"[\u0900-\u097F\u0C00-\u0C7F]", text)


def test_wrong_planet_house_claim_is_caught():
    conf, pc, cfg, facts = _sheet("when will I get promoted", "career_profession")
    lord = facts["house"]["lord"]["planet"]
    wrong = (facts["house"]["lord"]["house"] % 12) + 1
    if (lord, wrong) in QR._true_claims(facts):
        return
    assert QR._check(f"You will be fine because {lord} sits in house {wrong}.", facts)


# ----------------------------------------------------------------------------- health & page filter
_HPC = None


def _health_pc() -> dict:
    """Gemini rising, Mars (6th lord) debilitated in the 2nd, Ketu-Venus running: the chart that lost bullets."""
    global _HPC
    if _HPC is None:
        from astro_precompute import resolve_precompute
        _HPC = resolve_precompute("Test", "1992-11-15", birth_time="20:00", latitude=28.6, longitude=77.2,
                                  timezone=5.5, place_name="Delhi", gender=1)
    return _HPC


def _health_sheet(question: str = "how is the health in coming time"):
    pc = _health_pc()
    conf = analyze_question_confluence(pc, question, domain_override="health_vitality")
    cfg = DOMAINS_CONFIG[conf.domain_key]
    return conf, pc, cfg, QR.build_fact_sheet(conf, pc, cfg)


def _through_the_page_filters(html_text: str) -> str:
    import report_render as RR
    return RR._scrub(RR._voice_polish(html_text))


def _li_texts(html_text: str) -> list[str]:
    return [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<li[^>]*>(.*?)</li>", html_text, re.S)]


def test_no_reason_is_blanked_by_the_page_filter():
    """The customer-text filter deletes a whole sentence that says '<Planet> sits'; none of ours may."""
    for lang in ("en", "hi_en", "te_en"):
        conf, pc, cfg, facts = _health_sheet()
        r = QR._fallback(facts, lang)
        page = QR.render_html(r, facts, paid=True, lang=lang)
        out = _through_the_page_filters(page)
        before, after = _li_texts(page), _li_texts(out)
        assert len(before) == len(after) and all(after), (lang, [b for b, a in zip(before, after) if not a])


def test_every_lens_sentence_survives_the_page_filter():
    import itertools
    import question_lenses as QL
    facts = {"house": {"number": 6}}
    planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    texts = []
    for main, sub, rel in itertools.product(planets, planets, ("helper", "hard", "none")):
        texts.append(QL.text_en("vimshottari", {"main": main, "sub": sub, "who": sub, "rel": rel}, facts))
    for hit, hard in (("primary", False), ("lord", False), ("", True), ("", False)):
        texts.append(QL.text_en("jaimini", {"maha": "Aries", "antar": "Leo", "hit": hit, "hard": hard,
                                            "primary_sign": "Scorpio", "lord_sign": "Cancer"}, facts))
    for nodes in (True, False):
        texts.append(QL.text_en("transit", {"primary": 6, "nodes": nodes, "jup": {"mode": "aspects", "house": 2},
                                            "sat": {"mode": "in", "house": 6}}, facts))
    page = "<ul>" + "".join(f"<li>{t}</li>" for t in texts) + "</ul>"
    out = _through_the_page_filters(page)
    assert all(_li_texts(out)), "a lens sentence is wiped by the page filter"


def test_model_answer_the_page_filter_would_delete_is_rejected():
    conf, pc, cfg, facts = _health_sheet()
    assert QR._check("Your health is fine because Mars sits in your second house.", facts)


def test_health_gets_a_body_vulnerability_lens_from_naadi_and_the_disease_pattern():
    conf, pc, cfg, facts = _health_sheet()
    v = facts["lenses"].get("vulnerability")
    assert v and v["vote"] in (-1, 0, 1)
    assert v["themes"], "the disease-pattern confluence found no body zone"
    assert v["sensitive"], "Chandra Naadi found no planet in the 6th or 8th"
    text = QR._lens_findings(facts, "en", 1)
    body = next(t for _i, lens, t in text if lens == "vulnerability")
    assert "Chandra Naadi marks" in body and "body pattern" in body
    # the other areas never get this lens
    _c, _p, _cfg, career = _sheet("when will I get promoted", "career_profession")
    assert "vulnerability" not in career["lenses"]


def test_health_answer_names_the_area_and_where_to_take_care():
    conf, pc, cfg, facts = _health_sheet()
    r = QR._fallback(facts, "en")
    assert "your health" in r.answer.lower(), r.answer
    assert "Look after" in r.answer, r.answer
    assert any("vulnerability" == v["key"] for v in r.lenses)
    assert any(re.search(r"Chandra Naadi marks", w) for w in r.why), "the vulnerability reason must be shown"
    assert any(s.startswith("For your body pattern") for s in r.steps), r.steps
    assert "sub-period" in r.timing and re.search(r"\b20\d\d\b", r.timing)
    vuln_reason = next(w for w in r.why if "Chandra Naadi marks" in w)
    low = " ".join([r.answer, vuln_reason, *r.steps, r.timing]).lower()      # (the sign Cancer is not a disease)
    assert not re.search(r"\b(cancer|diabet\w*|surgery|death|die|lifespan|longevity)\b", low)
    page = QR.render_html(r, facts, paid=True)
    assert "Body vulnerability" in page
    free = QR.render_html(r, facts, paid=False)
    assert "Body vulnerability" not in free and "Unlock" in free


def test_every_domain_answer_names_its_area():
    for q, dom, word in [("when will I get promoted", "career_profession", "career"),
                         ("will I be rich", "wealth_finances", "finances")]:
        conf, pc, cfg, facts = _sheet(q, dom)
        assert word in QR._fallback(facts, "en").answer.lower(), (dom, QR._fallback(facts, "en").answer)


def test_model_cannot_name_an_illness_on_a_health_question():
    conf, pc, cfg, facts = _health_sheet()
    assert QR._check("You may develop diabetes, so take care of your health.", facts)
    assert QR._check("Your chart is full of strain.", facts) == []
    assert QR._check("Nothing to say.", facts), "a health answer must say how the health outlook looks"


def test_health_reasons_survive_model_picks_and_hinglish_tenglish_are_localised():
    conf, pc, cfg, facts = _health_sheet()

    def stub(schema, system, user, **kw):
        assert "HEALTH QUESTION" in user and "body vulnerability" in user
        return QR.QuestionJudgement(
            stance="mixed", answer="Your health needs steady care, mainly for the skin, nerves and face.",
            because="Your chart is most sensitive there and the running period asks for extra care.",
            use=["F1", "F2"], needs_timing=False)

    with _Model(stub):
        got = QR._ask_model(facts, "en")
    assert got is not None and any("Chandra Naadi marks" in w for w in got.why), "vulnerability must be kept"
    assert len(got.why) <= 6
    for lang in ("hi_en", "te_en"):
        r = QR._fallback(facts, lang)
        text = " ".join([r.answer, *r.why, *r.steps, r.timing])
        assert "Chandra Naadi" in text and not _ENGLISH_FILLER.search(text), (lang, text)
        assert not re.search(r"[\u0900-\u097F\u0C00-\u0C7F]", text)


_AREAS = [("when will I get promoted", "career_profession"), ("when will I get married", "marriage_relationship"),
          ("will my finances improve", "wealth_finances"), ("will I have a child", "children_progeny"),
          ("will I clear my exams", "education_learning"), ("will I settle abroad", "foreign_relocation"),
          ("should I buy a house now", "property_assets"), ("will I win my court case", "litigation_disputes"),
          ("will my stammering improve", "speech_neurology"), ("how will my life go", "general_destiny"),
          ("how is my health", "health_vitality")]


def test_chandra_naadi_is_reviewed_and_shown_for_every_life_area():
    for q, dom in _AREAS:
        conf, pc, cfg, facts = _sheet(q, dom)
        naadi = facts["lenses"].get("naadi")
        assert naadi, (dom, "no Chandra Naadi reading")
        assert {"touched", "relevant", "cautions", "moon_sign"} <= set(naadi), dom
        assert any(w.startswith("Chandra Naadi:") for w in QR._fallback(facts).why), dom

        def stub(schema, system, user, **kw):          # a model that picks only the lead finding
            return QR.QuestionJudgement(stance="mixed", answer="You may see progress with care.",
                                        because="Your chart is mixed right now.", use=["F1"], needs_timing=False)

        with _Model(stub):
            got = QR._ask_model(facts, "en")
        assert got is not None and any(w.startswith("Chandra Naadi:") for w in got.why), (dom, got and got.why)
        assert len(got.why) <= 6, dom


def test_general_life_question_is_a_confluence_of_every_lens():
    conf, pc, cfg, facts = _sheet("how will my life go", "general_destiny")
    assert {"promise", "vimshottari", "jaimini", "yogini", "transit", "naadi"} <= set(facts["lenses"])
    assert QR._fallback(facts).confidence


def test_naadi_present_moment_wording_survives_filters_and_is_localised():
    import question_naadi as QN
    base = {"vote": -1, "touched": ["Moon", "Mercury"], "relevant": ["Mercury"], "good": [], "bad": ["Mercury"],
            "moon_sign": "Aries", "cautions": ["chandrashtama", "manthi", "badhaka", "punarpoo"],
            "mars_in": True, "sat_over": ["Mercury", "Venus"], "primary": 7}
    facts = {"domain_key": "marriage_relationship", "house": {"number": 7}}
    en = QN.text_en(base, facts)
    assert "sensitive moment" in en and "avoid hasty commitments" in en
    assert "Transit Saturn is over your natal Mercury and Venus" in en and "Transit Mars" not in en
    mars_only = QN.text_en(dict(base, sat_over=[]), facts)
    assert "Transit Mars is in your 7th house" in mars_only
    out = _through_the_page_filters(f"<ul><li>{en}</li></ul>")
    assert _li_texts(out) and all(_li_texts(out)), "the Chandra Naadi sentence was wiped by the page filter"
    health = QN.text_en(base, {"domain_key": "health_vitality", "house": {"number": 6}})
    assert "so go easy" in health
    for lk in ("hi_en", "te_en"):
        text = QN.text_local(base, facts, lk)
        assert "Chandra Naadi" in text and "Manthi" in text and not _ENGLISH_FILLER.search(text), (lk, text)
        assert not re.search(r"[\u0900-\u097F\u0C00-\u0C7F]", text)
    calm = dict(base, cautions=[], mars_in=False, sat_over=[])
    assert "sensitive moment" not in QN.text_en(calm, facts)


def test_health_answer_cannot_say_no_care_is_needed_while_the_chart_shows_strain():
    conf, pc, cfg, facts = _health_sheet()
    assert QR._care_now(facts)
    assert QR._check("Your health is fine; the running period does not indicate a need for extra care.", facts)
    assert "ADVISED" in QR._prompt(facts)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK ", name)
    print("ALL question_reading tests passed")

