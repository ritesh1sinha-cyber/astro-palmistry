"""Relationship (breakup / come back / divorce / find love) reading: wording rules and the free/paid split."""
import re

import relationship_naadi as RN


def test_intent_kinds():
    cases = {
        "will she come back to me? we broke up last week": ("return", "she"),
        "when will my boyfriend talk to me again": ("return", "he"),
        "will my divorce go through or can we fix it": ("divorce", "they"),
        "will we break up": ("breakup", "they"),
        "when will i get girlfriend": ("find", "she"),
        "does she like me": ("crush", "she"),
        "when will i get married": ("marriage", "they"),
        "how is my career": ("other", "they"),
    }
    for q, (kind, pron) in cases.items():
        got = RN.intent(q)
        assert (got["kind"], got["pron"]) == (kind, pron), (q, got)
    assert RN.intent("when will she come back")["asks"] == "timing"
    assert RN.intent("will she come back")["asks"] == "yes_no"


def _b(lean="mixed", kind="return"):
    return {
        "kind": kind, "asks": "yes_no", "pron": "she", "lean": lean, "pattern": "p",
        "facts": ["F1: Venus sits in Pisces, house 7.", "F2: Saturn sits with your partnership planet, which brings distance."],
        "days": {"open": ["Fri 30 Oct"], "hold": ["Sun 01 Nov"], "n_open": 3, "n_hold": 2, "ok": True},
        "next_window": "", "question": "will she come back",
    }


def _w(**kw):
    base = {"headline": "h", "happening": "Distance is showing in your chart.", "why": ["Saturn sits with Venus."],
            "do": ["Keep it calm."], "avoid": ["Long messages."]}
    base.update(kw)
    return base


def test_validator_rejects_promises_dates_and_invented_things():
    b = _b("mixed")
    assert RN._problems(_w(), b) == []
    assert RN._problems(_w(happening="You should know she will come back soon."), b)          # promise while not open
    assert RN._problems(_w(happening="You may expect news in March 2027."), b)               # date
    assert RN._problems(_w(happening="Jupiter blesses you."), b)                     # planet not in facts
    assert RN._problems(_w(happening="Trust has broken between you two."), b)           # invented cause
    assert RN._problems(_w(do=["Do a love spell tonight."]), b)                      # trick
    assert RN._problems(_w(happening="You will see her come back."), _b("open")) == []       # allowed only when open
    assert RN._problems(_w(happening="You have no chance, it's over."), _b("open"))           # doom when open


def test_divorce_spouse_is_not_an_ex():
    assert RN._problems(_w(do=["Reach out to your ex-partner."]), _b("mixed", "divorce"))


def test_every_headline_exists_and_makes_no_promise():
    for kind, leans in RN._HEADLINE.items():
        for lean in ("open", "mixed", "closed"):
            text = RN._headline({"kind": kind, "lean": lean, "pron": "she"})
            assert text and not RN._BANNED.search(text)
            if lean != "open":
                assert not RN._SURE_BACK.search(text)


def test_free_page_has_no_dates_and_paid_page_has_them():
    blk = RN.compose({**_b("mixed"), "by_model": False}, lang="en")
    free = RN.render_html(blk, paid=False, price=298)
    paid = RN.render_html(blk, paid=True, price=298)
    assert "Fri 30 Oct" not in free and "Sun 01 Nov" not in free
    assert not re.search(r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun) \d{2} \w{3}", free)
    assert "3 days" in free and "2 days" in free                     # counts only
    assert "Fri 30 Oct" in paid and "Sun 01 Nov" in paid
    assert "Fri 30 Oct" not in str(RN.public(blk).get("happening", ""))


def test_non_english_uses_templates():
    blk = RN.compose({**_b("open"), "by_model": False}, lang="hi_en")
    assert blk["label"] == RN._LEAN["hi_en"]["return"]["open"]
    assert RN.render_html(blk, paid=False)
