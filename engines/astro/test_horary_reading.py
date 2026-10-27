"""A horary is answered in the same one-card format as the natal question report.

Run: python test_horary_reading.py   (or pytest)
"""
from __future__ import annotations

import re
import sys
from types import SimpleNamespace

sys.path.insert(0, ".")

import horary_reading as HR  # noqa: E402
import question_reading as QR  # noqa: E402

EV = {"topic": "career", "kp_number": 57, "primary_bhava": 10, "cusp_sub_lord": "Sun",
      "fav_hits": ["2", "6", "11"], "den_hits": [], "list_c": ["Jupiter", "Ketu", "Mars", "Mercury", "Moon"],
      "list_a": ["Jupiter", "Ketu", "Mars", "Mercury", "Moon", "Rahu", "Saturn", "Venus"],
      "ruling_planets": ["Moon", "Jupiter", "Mercury", "Mars", "Ketu", "Sun"]}
DATA = {"lagna": {"sign": "Scorpio"}, "planets": {"Moon": {"sign": "Aries", "nakshatra": "Ashwini",
                                                          "star_lord": "Ketu"}},
        "houses": {"Moon": 6}, "meta": {"paksha": {"bright_moon": False}},
        "prashna": {"label": "CONDITIONAL", "score": -0.26}, "jamakkol": {"verdict": "NO"},
        "radicality": {"score": 2}}
NEAR = {"window": "Oct-2026", "until": "Nov-2026", "starts": None, "ends": None, "days_away": 5, "near": True,
        "level": "antara"}
PLAIN = SimpleNamespace(answer="You might get it, but it is uncertain.", timing="The nearest window is soon.",
                        remedy="Speak directly to the decision-maker.")


def _votes(**kw):
    return {k: {"vote": v} for k, v in kw.items()}


def test_kp_vote_follows_helping_vs_denying_houses():
    assert HR._kp({"fav_hits": ["2", "11"], "den_hits": []})["vote"] == 1
    assert HR._kp({"fav_hits": ["7"], "den_hits": ["1", "6"]})["vote"] == -1
    assert HR._kp({"fav_hits": ["11"], "den_hits": ["5"]})["vote"] == 0
    assert HR._kp({"fav_hits": [], "den_hits": []})["vote"] == 0


def test_every_lens_votes_for_a_full_chart():
    lenses = HR.build_lenses(DATA, EV, NEAR)
    assert set(lenses) == set(HR.LENS_ORDER)
    assert all(v["vote"] in (-1, 0, 1) for v in lenses.values())
    assert lenses["kp"]["vote"] == 1 and lenses["period"]["vote"] == 1
    assert lenses["jamakkol"]["vote"] == -1
    assert lenses["moon"]["vote"] == -1          # waning, in a hard house


def test_a_missing_source_drops_its_lens_rather_than_guessing():
    lenses = HR.build_lenses(None, EV, {"beyond_horizon": True})
    assert set(lenses) == {"kp", "ruling", "period"}
    assert lenses["period"]["vote"] == -1


def test_no_clear_window_votes_against_and_a_distant_one_is_neutral():
    assert HR._period({})["vote"] == -1
    assert HR._period({"window": "Jan-2028", "days_away": 500, "near": False})["vote"] == 0


def test_stance_softens_the_label_but_never_flips_it():
    for_all = _votes(kp=1, ruling=1, period=1, moment=1, jamakkol=1, moon=1)
    against = _votes(kp=-1, ruling=-1, period=-1, moment=-1, jamakkol=-1, moon=-1)
    assert HR.stance("yes", for_all) == "favourable"
    assert HR.stance("yes", against) == "mixed"            # a yes the lenses reject is softened
    assert HR.stance("no", against) == "difficult"
    assert HR.stance("no", for_all) == "mixed"             # a no is never turned into favourable
    assert HR.stance("conditional", for_all) == "favourable"
    assert HR.stance("conditional", against) == "difficult"
    assert HR.stance("out_of_scope", for_all) == "not_astrological"


def test_outlook_and_the_wording_may_not_pull_the_other_way():
    from llm.horary_judge import contradicts_outlook, label_gloss
    assert HR.outlook(_votes(kp=-1, ruling=-1, period=-1, moon=-1)) == "against"
    assert HR.outlook(_votes(kp=1, ruling=1, period=1)) == "for"
    assert HR.outlook(_votes(kp=0, ruling=1)) == ""
    assert contradicts_outlook("You might get the job.", "against")
    assert not contradicts_outlook("This is unlikely, and it might not happen.", "against")
    assert contradicts_outlook("This is unlikely.", "for")
    assert not contradicts_outlook("You might get the job.", "")
    assert "not look likely" in label_gloss("conditional", {}, "against")
    assert "possible" in label_gloss("conditional", {}, "for")


def test_the_reading_has_the_natal_card_shape():
    r, rows, meta = HR.build(question="Will I get the job?", data=DATA, evidence=EV, timing=NEAR,
                             plain=PLAIN, label="conditional", asked="26 Oct 2026, 10:30")
    assert r.stance in ("favourable", "mixed", "difficult")
    assert r.answer.startswith(PLAIN.answer) and "promise" in r.answer
    assert len(r.why) == len(HR.LENS_ORDER) and all(w.strip() for w in r.why)
    assert [x["key"] for x in r.lenses] == list(HR.LENS_ORDER)
    assert r.timing == PLAIN.timing and r.steps and r.steps[0] == PLAIN.remedy
    assert r.confidence in ("high", "moderate", "low")
    assert rows and "Scorpio" in meta


def test_out_of_scope_gets_the_answer_and_nothing_else():
    plain = SimpleNamespace(answer="This is not something a horary chart can answer.", timing="", remedy="")
    r, rows, _ = HR.build(question="Write a script", data=DATA, evidence=EV, timing={}, plain=plain,
                          label="out_of_scope")
    assert r.stance == "not_astrological" and not r.why and not r.steps and not rows and not r.lenses


def test_a_test_question_lowers_confidence():
    data = {**DATA, "radicality": {"score": 3}}
    lenses = HR.build_lenses(data, EV, NEAR)
    assert HR.confidence(lenses, data) == "low"


def test_non_english_is_fixed_wording_not_the_models_english():
    for lang in ("hi_en", "te_en"):
        for label in ("yes", "no", "conditional", "open"):
            r, _rows, _m = HR.build(question="q", data=DATA, evidence=EV, timing=NEAR, plain=PLAIN,
                                    label=label, lang=lang, asks="yes_no")
            assert not re.search(r"\b(might|uncertain|chart's promise)\b", r.answer, re.I), (lang, label, r.answer)
            assert all(w.strip() for w in r.why)
        r, *_ = HR.build(question="q", data=DATA, evidence=EV, timing={"beyond_horizon": True}, plain=PLAIN,
                         label="no", lang=lang)
        assert "window" not in r.timing.lower()


def _rendered(lang: str, label: str, paid: bool) -> str:
    import report_render as RR
    r, rows, meta = HR.build(question="Will it work?", data=DATA, evidence=EV, timing=NEAR, plain=PLAIN,
                             label=label, lang=lang, asked="26 Oct 2026, 10:30", asks="yes_no")
    body = QR.render_html(r, {"question": "Will it work?"}, paid=paid, lang=lang, price=298,
                          fact_rows=rows, meta_line=meta)
    return RR._scrub(RR._voice_polish(body))


def test_nothing_is_blanked_by_the_page_filter_in_any_language():
    """The last filter deletes whole sentences it dislikes; a blank bullet or chip is a shipped bug."""
    for lang in ("en", "hi_en", "te_en"):
        for label in ("yes", "no", "conditional", "open"):
            for paid in (False, True):
                page = _rendered(lang, label, paid)
                assert not re.search(r"<li[^>]*>\s*</li>", page), (lang, label, paid)
                if not paid:        # free: headline, two reasons and a count - no chips, no full list
                    assert "uq-lenses" in page and page.count("<li") <= 3, (lang, label)
                    continue
                chips = re.findall(r'border-radius:99px;background:#\w+;color:#\w+;">([^<]*)</span>', page)
                assert chips and all(re.sub(r"&#\d+;|&bull;", "", c).strip() for c in chips), (lang, chips)
                assert page.count("<li") >= len(HR.LENS_ORDER), (lang, label, paid)


def test_free_shows_the_answer_and_locks_timing_and_steps():
    free, paid = _rendered("en", "conditional", False), _rendered("en", "conditional", True)
    assert "How the lenses line up" in paid and "How the lenses line up" not in free
    assert "more perspectives were checked" in free and PLAIN.answer in free
    assert "Unlock" in free and PLAIN.remedy not in free and PLAIN.timing not in free
    assert PLAIN.remedy in paid and PLAIN.timing in paid and "Unlock" not in paid


def test_the_plain_summary_is_written_from_the_reading():
    import llm.summary as SM
    r, rows, _ = HR.build(question="Will I get the job?", data=DATA, evidence=EV, timing=NEAR, plain=PLAIN,
                          label="conditional")
    meta = {"language": "en", "reading": r.model_dump(), "question": "Will I get the job?"}
    out = SM.build_plain_summary(kind="horary", html="<p>x</p>", meta=meta, paid=True)
    assert out["generated"] == "reading"
    assert r.answer.split(".")[0] in out["headline"]


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("  ok  ", name)
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print("  FAIL", name, type(exc).__name__, exc)
    print(f"\n{'FAILED' if failed else 'all passed'}: {failed} failing")
    sys.exit(1 if failed else 0)
