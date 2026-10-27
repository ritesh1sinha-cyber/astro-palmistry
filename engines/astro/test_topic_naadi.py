"""Career and health Chandra Naadi readings, and Sade Sati."""
import re
from datetime import date

import sade_sati as SS
import topic_naadi as TN


def test_intent_career_and_health():
    career = {
        "will i get promotion this year": "promotion",
        "when will i get a salary hike": "promotion",
        "should i change my job": "jobchange",
        "will i get a job offer": "jobchange",
        "will i be laid off from my company": "layoff",
        "i am scared of being fired": "layoff",
        "will my startup succeed": "business",
        "how is my career": "other",
    }
    for q, kind in career.items():
        assert TN.intent("career", q)["kind"] == kind, q
    health = {
        "will my surgery be successful": "surgery",
        "i have anxiety and cannot sleep": "mind",
        "when will i recover": "recovery",
        "i have diabetes, what will happen": "disease",
        "how is my health": "disease",
    }
    for q, kind in health.items():
        assert TN.intent("health", q)["kind"] == kind, q


def _b(topic="health", lean="mixed", kind="surgery", question="will my surgery go well"):
    return {"topic": topic, "kind": kind, "lean": lean, "asks": "yes_no", "pattern": "p", "question": question,
            "facts": ["F1: Mercury (rules your rising sign) sits in Aries, house 8.",
                      "F2: The Sun (vitality) sits in Aries, house 8."],
            "days": {"open": ["Fri 30 Oct"], "hold": ["Sun 01 Nov"], "n_open": 3, "n_hold": 2, "ok": True},
            "next_window": ""}


def _w(**kw):
    base = {"headline": "h", "happening": "Your body is under some strain in your chart.", "why": ["Mercury is in Aries."],
            "do": ["Rest well."], "avoid": ["Hard exertion."]}
    base.update(kw)
    return base


def test_health_validator_never_scares_or_gives_medical_orders():
    b = _b()
    assert TN._problems(_w(), b) == []
    for bad in ("You may not survive this.",                 # death
                "You should stop taking your medicine.",      # treatment
                "You have cancer risk in your chart.",        # names an illness
                "You should postpone the surgery.",           # medical decision
                "Your recovery will be quick.",               # guaranteed good outcome while mixed
                "Your diet is the cause."):                   # invented cause
        assert TN._problems(_w(happening=bad), b), bad
    # an illness the reader named themselves is allowed
    assert TN._problems(_w(happening="Your diabetes needs steady care."), _b(question="my diabetes")) == []


def test_career_validator():
    b = _b("career", "closed", "layoff", "will i be laid off")
    assert TN._problems(_w(happening="You will be fired soon."), b)
    assert TN._problems(_w(happening="You will lose your job."), b)
    assert TN._problems(_w(happening="A recession is hurting you."), b)
    assert TN._problems(_w(happening="Your work is under pressure now."), b) == []


def test_every_headline_label_and_fallback_exists():
    for topic, kinds in TN._HEADLINE.items():
        for kind in kinds:
            for lean in ("open", "mixed", "closed"):
                assert TN._LABEL[topic][kind][lean]
                b = _b(topic, lean, kind)
                fb = TN._fallback(b)
                assert fb["headline"] and fb["happening"] and fb["do"] and fb["avoid"]
                assert not TN._DEATH.search(" ".join(fb["do"] + fb["avoid"] + [fb["headline"], fb["happening"]]))


def test_health_card_always_carries_the_doctor_line():
    blk = TN.compose({**_b(), "by_model": False})
    assert any("doctor" in x.lower() or "surgeon" in x.lower() for x in blk["do"])
    for paid in (False, True):
        assert "not medical advice" in TN.render_html(blk, paid=paid)


def test_free_card_has_counts_but_no_dates():
    blk = TN.compose({**_b("career", "mixed", "promotion"), "by_model": False})
    free = TN.render_html(blk, paid=False)
    paid = TN.render_html(blk, paid=True)
    assert not re.search(r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun) \d{2} \w{3}", free)
    assert "3 days" in free and "2 days" in free
    assert "Fri 30 Oct" in paid and "Sun 01 Nov" in paid


# ---- Sade Sati -----------------------------------------------------------------------------
TODAY = date(2026, 10, 27)


def _pc(moon_sign, house=1):
    return {"planets": {"Moon": {"sign": moon_sign, "house": house}, "Saturn": {"sign": "Pisces"}}}


def test_sade_sati_running_phases_do_not_overlap_and_are_ordered():
    blk = SS.build(_pc("Pisces", 4), TODAY)              # Saturn is in Pisces: the Moon's own sign, the peak
    assert blk["status"] == "in" and blk["phase"] == 1
    names = [p["name"] for p in blk["phases"]]
    assert names == ["Rising phase", "Peak phase", "Setting phase"]
    for a, b in zip(blk["phases"], blk["phases"][1:]):
        assert a["start"] < b["start"] and a["end"] < b["end"]      # in order; retrograde turns may overlap them
    assert all((p["end"] - p["start"]).days > 365 for p in blk["phases"])   # no half-year slivers
    assert blk["cycle_start"] <= TODAY <= blk["cycle_end"]


def test_sade_sati_retrograde_loop_does_not_split_a_cycle():
    blk = SS.build(_pc("Sagittarius", 11), TODAY)         # next cycle is in the 2040s
    assert blk["status"] == "next" and blk["years_to_start"] > 10
    assert (blk["cycle_end"] - blk["cycle_start"]).days > 365 * 6      # a whole cycle, not one short dip
    assert blk["minor"] and blk["minor"]["name"] == "Dhaiya"           # Saturn is 4th from this Moon now


def test_sade_sati_pages():
    running = SS.build(_pc("Aries", 5), TODAY)
    free, paid = SS.render(running, paid=False), SS.render(running, paid=True)
    assert not re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December) \d{4}", free)
    assert "Hanuman" not in free and "lock-wrap" in free
    assert "Hanuman Chalisa" in paid and "blue sapphire" in paid and "When it begins and ends" in paid
    assert re.search(r"[A-Z][a-z]+ \d{4}", paid)
    far = SS.build(_pc("Capricorn", 2), TODAY)            # about twenty years away: nothing to do now
    far_paid = SS.render(far, paid=True)
    assert "Remedies" not in far_paid and "nothing to do about it now" in far_paid
    assert SS.window_dates(running) and all(isinstance(w["start"], date) for w in SS.window_dates(running))
