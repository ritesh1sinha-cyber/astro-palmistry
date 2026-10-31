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
    # the badge follows the same (birth promise, running now) pair that picks the sentence
    p, n = QL.promise_and_now(lenses)
    assert QR._stance_hint(facts) == ("favourable" if p > 0 and n > 0 else "difficult" if p < 0 else "mixed")
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
            stance=QR._stance_hint(facts), answer="Your job-change prospects look difficult right now.",
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
            answer="Your promotion looks hard to secure right now, so patience and preparation matter.",
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


def test_model_answer_rejects_certainty_vague_timing_directives_and_jargon():
    conf, pc, cfg, facts = _sheet("when will I get promoted", "career_profession")
    bad = [
        "Your promotion will happen.",
        "Your promotion may happen soon.",
        "You should consider changing your job.",
        "You should proceed with your property purchase.",
        "Your birth promise supports your career, but the running period is mixed.",
        "Your underlying pattern is supportive, but current conditions are difficult.",
        "Your exam prospects have supportive planetary placements.",
        "Your job security is mixed while your career base is strong. While your career base is strong, delays may affect stability.",
        "Chandra Naadi supports your promotion prospects.",
    ]
    for answer in bad:
        assert QR._check(answer, facts), answer
    assert not QR._check("A promotion looks possible, but your progress may be slower right now.", facts)


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
            stance=QR._stance_hint(facts), answer="Your marriage prospects look possible, but patience may be needed.",
            use=["F1", "F2"], needs_timing=True)):
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
    for q, dom, word in [("when will I get promoted", "career_profession", "promotion"),
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
            because="Your chart is most sensitive there and the present phase asks for extra care.",
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


def test_present_tense_question_does_not_get_an_irrelevant_future_window():
    for question in ("How is my relationship with my partner right now?", "Is my current relationship serious?"):
        conf, pc, cfg, facts = _sheet(question, "marriage_relationship")
        r = QR._fallback(facts)
        assert not r.timing
        assert "supportive window above" not in " ".join(r.steps)
        assert any("calm conversation" in s for s in r.steps)


def test_every_major_area_has_plain_reasons_and_question_specific_advice():
    rows = _AREAS + [("Is my job secure next year?", "career_profession"),
                     ("Should I change my job this year?", "career_profession"),
                     ("How is my relationship currently?", "marriage_relationship"),
                     ("Will I travel abroad for work?", "foreign_relocation")]
    expected = {"career_profession": ("results", "written offers", "cash cushion"),
                "marriage_relationship": ("introductions", "calm conversation"),
                "wealth_finances": ("Automate savings",), "children_progeny": ("clinician",),
                "education_learning": ("Prepare early",), "foreign_relocation": ("documents and funds",),
                "property_assets": ("Verify title",), "litigation_disputes": ("lawyer",),
                "speech_neurology": ("qualified speech",), "general_destiny": ("one practical priority",),
                "health_vitality": ("body pattern",)}
    jargon = re.compile(r"birth promise|running period|Chara|Yogini|Chandra Naadi|\bhouse\s*\d|\bplanet\b|"
                        r"\bwill\b|\bsoon\b|\beventually\b", re.I)
    for q, dom in rows:
        conf, pc, cfg, facts = _sheet(q, dom)
        r = QR._fallback(facts)
        assert not QR._check(r.answer, facts), (q, QR._check(r.answer, facts))
        assert not jargon.search(r.answer), (q, r.answer)
        reasons = QR.plain_reasons(facts)
        assert 2 <= len(reasons) <= 3, (q, reasons)
        assert not any(jargon.search(x) for x in reasons), (q, reasons)
        steps = " ".join(r.steps)
        assert any(word in steps for word in expected[dom]), (q, steps)
        assert "Aim to make the key move" not in steps and "Strengthen " not in steps


def test_gemstone_steps_include_a_trial_and_no_suitability_guarantee():
    conf, pc, cfg, facts = _sheet("which gemstone will suit me", "gemstones_remedies")
    r = QR._fallback(facts)
    assert any("three days" in s and "If comfortable" in s for s in r.steps)
    for stone in facts["gems"]["recommended"]:
        assert any(stone["gem"] in s and "three days" in s for s in r.steps), stone["gem"]
    reasons = " ".join(QR.plain_reasons(facts))
    assert "not a guarantee" in reasons and "stop if you feel uncomfortable" in reasons


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


def test_career_advice_matches_the_reader_situation_not_a_generic_manager_script():
    rows = [
        ("What career should I choose?", "career direction", "mentor"),
        ("When will I get my first job?", "first-job prospects", "practise interviews"),
        ("Should I start my own business?", "business plans", "Validate demand"),
        ("Should I retire from my job next year?", "retirement transition", "pension"),
        ("Is my job safe after the layoffs?", "job security", "cash cushion"),
    ]
    for question, answer_word, step_word in rows:
        conf, pc, cfg, facts = _sheet(question, "career_profession")
        r = QR._fallback(facts)
        assert answer_word in r.answer.lower(), (question, r.answer)
        assert step_word.lower() in " ".join(r.steps).lower(), (question, r.steps)
        assert "manager" not in r.steps[-1].lower(), (question, r.steps)
        assert not QR._check(r.answer, facts), (question, QR._check(r.answer, facts))
    for question in ("What career should I choose?", "When will I get my first job?"):
        conf, pc, cfg, facts = _sheet(question, "career_profession")
        assert "resignation" not in " ".join(QR.plain_reasons(facts)).lower()


def test_legal_scenarios_get_specific_safe_language_and_practical_steps():
    rows = [
        ("Will I win my property court case?", "property dispute", "ownership"),
        ("Can I settle my tenant dispute out of court?", "tenant dispute", "communication records"),
        ("How long will my divorce case continue?", "divorce proceedings", "financial records"),
        ("Will I get custody of my child?", "custody matter", "child-focused"),
        ("Can I resolve my family property dispute through mediation?", "settlement prospects", "mediation"),
        ("Will my inheritance dispute be resolved?", "inheritance dispute", "ownership"),
    ]
    for question, answer_word, step_word in rows:
        conf, pc, cfg, facts = _sheet(question, "litigation_disputes")
        r = QR._fallback(facts)
        assert answer_word in r.answer.lower(), (question, r.answer)
        assert step_word in " ".join(r.steps).lower(), (question, r.steps)
        assert "lawyer" in " ".join(r.steps).lower(), (question, r.steps)
        assert not QR._check(r.answer, facts), (question, QR._check(r.answer, facts))
    conf, pc, cfg, facts = _sheet("Can I resolve my family property dispute through mediation?", "litigation_disputes")
    wrong_area = "Mediation could help, but your career base is strong while delays continue."
    assert QR._check(wrong_area, facts), "a legal answer must not drift into career wording"
    technical = "Mediation may help, but Saturn and the Moon touching Mars create challenges."
    assert QR._check(technical, facts), "a plain legal answer must not expose natal-planet jargon"


def test_sale_transfer_and_named_avoid_stone_answers_are_consistent():
    for question, answer_word, step_word in [
            ("Can I sell my ancestral house this year?", "property sale prospects", "sale documents"),
            ("Should I transfer my property to my children?", "property transfer plans", "tax")]:
        conf, pc, cfg, facts = _sheet(question, "property_assets")
        r = QR._fallback(facts)
        assert answer_word in r.answer.lower() and step_word in " ".join(r.steps).lower(), (question, r.answer, r.steps)
        assert "loan terms" not in " ".join(r.steps).lower()
    conf, pc, cfg, facts = _sheet("Should I wear blue sapphire at my age?", "gemstones_remedies")
    facts["gems"]["asked"][0]["verdict"] = "avoid"
    r = QR._fallback(facts)
    assert "Blue Sapphire (Neelam) is not advised for you." in r.answer
    assert not QR._check(r.answer, facts), QR._check(r.answer, facts)
    technical = "You should avoid Blue Sapphire because Saturn rules your 2nd and 3rd houses and is in your 12th house."
    assert QR._check(technical, facts), "gemstone reasons must stay plain on the customer page"


_AGE_CHARTS = {
    "teen": ("Aarav Singh", "2012-06-18", "08:40", 28.6139, 77.2090, "Delhi", 0),
    "25": ("Priya Nair", "2001-03-30", "03:20", 9.9312, 76.2673, "Kochi", 1),
    "36": ("Asha Rao", "1990-05-15", "10:30", 28.6139, 77.2090, "Delhi", 1),
    "41": ("Vikram Shah", "1984-11-02", "06:15", 19.0760, 72.8777, "Mumbai", 0),
    "54": ("Meena Iyer", "1972-08-21", "17:45", 13.0827, 80.2707, "Chennai", 1),
    "68": ("Ramesh Gupta", "1958-01-09", "05:50", 26.9124, 75.7873, "Jaipur", 0),
}
_AGE_CASES = [
    ("teen", "Will I pass my board exams this year?", "education_learning"),
    ("teen", "Which stream is better for my future?", "education_learning"),
    ("teen", "What career should I choose?", "career_profession"),
    ("teen", "Can I study abroad after school?", "foreign_relocation"),
    ("teen", "How is my health and energy?", "health_vitality"),
    ("25", "When will I get my first job?", "career_profession"),
    ("25", "Should I switch jobs for a better salary?", "career_profession"),
    ("25", "Will my visa be approved this year?", "foreign_relocation"),
    ("25", "Is my current relationship serious?", "marriage_relationship"),
    ("25", "When will I get married?", "marriage_relationship"),
    ("25", "Can I save enough for a car next year?", "wealth_finances"),
    ("25", "Which gemstone should I wear?", "gemstones_remedies"),
    ("36", "Will I get promoted this year?", "career_profession"),
    ("36", "Should I start my own business?", "career_profession"),
    ("36", "When can we plan our first child?", "children_progeny"),
    ("36", "Should I buy a flat now or wait?", "property_assets"),
    ("36", "Will I win my property court case?", "litigation_disputes"),
    ("36", "How should I care for my health now?", "health_vitality"),
    ("41", "Is my job safe after the layoffs?", "career_profession"),
    ("41", "Can I settle my tenant dispute out of court?", "litigation_disputes"),
    ("41", "How long will my divorce case continue?", "litigation_disputes"),
    ("41", "Will I get custody of my child?", "litigation_disputes"),
    ("41", "Can I repay my business loan next year?", "wealth_finances"),
    ("54", "Should I retire from my job next year?", "career_profession"),
    ("54", "Can I sell my ancestral house this year?", "property_assets"),
    ("54", "Will my inheritance dispute be resolved?", "litigation_disputes"),
    ("54", "How are my finances for retirement?", "wealth_finances"),
    ("54", "Will my second marriage work out?", "marriage_relationship"),
    ("54", "How should I care for my health now?", "health_vitality"),
    ("68", "How can I maintain my health and energy?", "health_vitality"),
    ("68", "Will my pension and savings be enough?", "wealth_finances"),
    ("68", "Should I transfer my property to my children?", "property_assets"),
    ("68", "Can I resolve my family property dispute through mediation?", "litigation_disputes"),
    ("68", "How does my spiritual life look ahead?", "general_destiny"),
    ("68", "Should I wear blue sapphire at my age?", "gemstones_remedies"),
    ("25", "Will my stammering improve?", "speech_neurology"),
]


def test_age_diverse_real_life_questions_route_and_read_cleanly():
    from astro_precompute import resolve_precompute
    pcs = {}
    visible_jargon = re.compile(r"birth promise|running period|Chara|Yogini|Chandra Naadi|\bhouse\s*\d|"
                                r"\bwill\b|\bsoon\b|\beventually\b", re.I)
    for age, question, expected_domain in _AGE_CASES:
        if age not in pcs:
            name, dob, tm, lat, lon, place, gender = _AGE_CHARTS[age]
            pcs[age] = resolve_precompute(name, dob, birth_time=tm, latitude=lat, longitude=lon,
                                          timezone=5.5, place_name=place, gender=gender)
        pc = pcs[age]
        conf = analyze_question_confluence(pc, question)
        assert conf.domain_key == expected_domain, (age, question, conf.domain_key)
        facts = QR.build_fact_sheet(conf, pc, DOMAINS_CONFIG[expected_domain])
        r = QR._fallback(facts)
        assert not QR._check(r.answer, facts), (age, question, QR._check(r.answer, facts))
        assert not visible_jargon.search(r.answer), (age, question, r.answer)
        reasons = QR.plain_reasons(facts)
        assert 2 <= len(reasons) <= 3, (age, question, reasons)
        assert not any(visible_jargon.search(x) for x in reasons), (age, question, reasons)
        assert r.steps and "Aim to make the key move" not in " ".join(r.steps), (age, question, r.steps)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK ", name)
    print("ALL question_reading tests passed")

