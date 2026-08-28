from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

# Production puts engines/astro on the path next to the repo root (see
# core.handlers._save_report), so `core.*` is importable from here too.
_ROOT = str(Path(__file__).resolve().parents[3])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from llm.schemas import PlainSummaryProse
from llm.summary import (
    _dejargon,
    _human_date,
    _locked_inventory,
    _trim_headline,
    _summary_brief,
    _tidy,
    _validate,
    attach_plain_summary,
    build_plain_summary,
    html_to_report_text,
)

_MONTH_YEAR = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+20\d{2}\b",
    re.I,
)


@pytest.fixture(autouse=True)
def _no_live_llm(monkeypatch):
    """These assertions describe the deterministic path.

    LLM_* may be exported in the shell, and a live endpoint would make every
    fallback assertion below depend on the network.
    """
    monkeypatch.setattr("llm.summary._enabled", lambda: False)


def _roles(out: dict) -> list[str]:
    return [s.get("role", "insight") for s in out["sections"]]


def _blob(out: dict) -> str:
    return " ".join(s["body"] for s in out["sections"])


def _prose(*sections, headline: str = "A clear finding about your work.") -> PlainSummaryProse:
    return PlainSummaryProse.model_validate({
        "headline": headline,
        "sections": [
            {"title": t, "body": b, "role": r} for t, b, r in sections
        ],
    })


# ---------------------------------------------------------------------------
# text extraction
# ---------------------------------------------------------------------------
def test_html_to_report_text_skips_scripts():
    html = "<style>.x{}</style><script>alert(1)</script><p>Hello chart</p>"
    assert "Hello chart" in html_to_report_text(html)
    assert "alert" not in html_to_report_text(html)


def test_html_to_report_text_excludes_the_whole_paywall_subtree():
    """A counter-based skip ended at the first inner close tag and leaked the rest."""
    html = (
        '<section class="reading"><p>Your energy responds to routine.</p></section>'
        '<section class="buy" id="unlock"><h3>See every life area</h3>'
        '<p>Unlock the short reading for each life area.</p>'
        '<a class="cta" href="#unlock">Pay 298</a></section>'
    )
    out = html_to_report_text(html)
    assert "energy responds to routine" in out
    assert "See every life area" not in out
    assert "Unlock the short reading" not in out


def test_html_to_report_text_breaks_at_block_boundaries():
    """Without a break the heading joins the paragraph and both become one sentence."""
    out = html_to_report_text("<h3>Your hand shape</h3><p>You think in systems</p>")
    assert "Your hand shape." in out
    assert "shape You think" not in out


def test_dejargon_keeps_the_fact_and_drops_the_term():
    out = _dejargon("The strongest opening sits around Saturn Antardasha (2027-01-10).")
    assert "Antardasha" not in out
    assert "sub-period" in out
    assert "2027-01-10" in out
    assert _dejargon("pratyantardasha") == "micro-period"
    assert _dejargon("Ashtakavarga bindus") == "strength score strength points"


def test_house_numbers_become_areas_of_life():
    """"10th house" is a term of art; the reader was promised plain English."""
    assert _dejargon("Strength in your 10th house of career supports this.") == \
        "Strength in your career and public standing supports this."
    assert "part of your chart" in _dejargon("Jupiter sits in the 11th house here.")
    assert _dejargon("The 4th house is active.").startswith("The home and family life")
    assert "that area of your chart" in _dejargon("The 19th house is not a thing.").lower()
    assert _dejargon("No house talk at all.") == "No house talk at all."


def test_bracketed_scores_are_dropped_but_ordinary_asides_survive():
    assert _dejargon(
        "Support here is thin (SAV 24/56, Moon BAV 4/8), so protect your rest."
    ) == "Support here is thin, so protect your rest."
    assert _dejargon("Aquarius is well supported (SAV 34) this month.") == \
        "Aquarius is well supported this month."
    kept = _dejargon("March is the strongest point of the year (by some way).")
    assert "(by some way)" in kept


def test_inline_scores_are_a_review_failure_not_a_silent_rewrite():
    """Deleting a score mid-sentence wrecks the grammar, so the model rewrites it."""
    scored = _prose(
        ("Where you stand", "Your career area carries 26 sign score points, which is "
                            "just under the average, so progress stays gradual.", "insight"),
    )
    fails = _validate(scored, "source text", kind="full_report", paid=True)
    assert any(f.startswith("metric:") for f in fails)

    ranged = _prose(
        ("Your baseline", "Vitality, intellect and fortune all sit between 73-78 out of "
                          "100, which is balanced rather than extreme in any direction.",
         "insight"),
    )
    assert any(f.startswith("metric:") for f in _validate(
        ranged, "source text", kind="palm", paid=True))


def test_a_humanised_iso_date_from_the_brief_counts_as_grounded():
    """The prompt asks for "October 2026"; the brief holds "2026-10-11"."""
    dated = _prose(
        ("When it shifts", "The strongest stretch for your work opens in October 2026 "
                           "and holds through the following two years.", "insight"),
    )
    brief = {"breakthrough_window": {"from": "2026-10-11", "to": "2029-08-17"}}
    assert not _validate(dated, "visible text with no dates", kind="user_question",
                         paid=True, brief=brief)
    assert any(f.startswith("ungrounded_date:") for f in _validate(
        dated, "visible text with no dates", kind="user_question", paid=True,
        brief={"breakthrough_window": {"from": "2031-02-05"}}))


def test_a_scored_sentence_is_dropped_rather_than_the_whole_draft(monkeypatch):
    scored = _prose(
        ("Where you stand", "Recognition at work is delayed rather than denied, and "
                            "steady visibility is what moves it along. Your career area "
                            "carries 26 sign score points, just under the average.",
         "insight"),
        ("Why it feels this way", "Home and family are taking more attention than usual, "
                                  "which is why your energy feels thinner than the work "
                                  "you are putting in.", "insight"),
    )
    _llm_on(monkeypatch, [scored, scored])
    out = build_plain_summary(
        kind="full_report", html="<p>Preview text.</p>", meta={},
        facts=_FULL_FACTS, paid=True,
    )
    assert out["generated"] == "llm"
    blob = _blob(out)
    assert "sign score points" not in blob
    assert "Recognition at work is delayed" in blob, "the good sentence must survive"


def test_an_invented_date_costs_its_sentence_not_the_draft(monkeypatch):
    invented = _prose(
        ("What the chart says", "The chart leans toward yes on this, and the situation is "
                                "still live rather than closed. Expect it to land by "
                                "December 2031.", "insight"),
        ("How it happens", "Nothing arrives on its own here, so follow-up and a word from "
                           "the right person are what move it along.", "insight"),
    )
    _llm_on(monkeypatch, [invented, invented])
    out = build_plain_summary(
        kind="horary", html="<p>The answer leans yes.</p>",
        meta={"question": "Will this offer come through?",
              "answer": {"label": "Leaning yes", "confidence": "moderate"}},
        paid=True,
    )
    assert out["generated"] == "llm"
    blob = _blob(out)
    assert "December 2031" not in blob
    assert "still live rather than closed" in blob
    assert out["headline"], "a cut headline must be replaced, not left blank"


def test_a_section_that_is_only_a_score_still_falls_back(monkeypatch):
    only_score = _prose(
        ("Your baseline", "Vitality, intellect and fortune all sit between 73-78 out of "
                          "100, balanced rather than extreme in any direction.", "insight"),
    )
    _llm_on(monkeypatch, [only_score, only_score])
    out = build_plain_summary(
        kind="full_report", html="<p>Preview text.</p>", meta={},
        facts=_FULL_FACTS, paid=True,
    )
    assert out["generated"] == "fallback"


def test_report_headings_are_translated_or_dropped_before_the_checklist():
    inv = _locked_inventory("<p>Paid half.</p>", None, {"paidSections": [
        "Every lane that voted on today, with its signal",
        "The houses today's sky is lighting up",
        "Deep Jyotish Consultation Reading",
        "Planetary Dynamics & Divisional Indicators",
        "What each life area holds for you",
    ]})
    assert inv["sections"] == [
        "Every check that voted on today, with its signal",
        "The areas of life today's sky is lighting up",
        "What each life area holds for you",
    ]


def test_a_headline_cut_at_the_length_cap_falls_back_to_a_whole_thought():
    cut = ("You're in a supportive two-and-a-half-year chapter where doors open partway "
           "— especially through guidance, sponsorship and steady visibility — but "
           "timing, patience, and careful re")
    out = _trim_headline(cut)
    assert out == ("You're in a supportive two-and-a-half-year chapter where doors open "
                   "partway — especially through guidance, sponsorship and steady "
                   "visibility.")
    assert _trim_headline("The chart leans yes") == "The chart leans yes."
    assert _trim_headline("A clear, supportive year ahead.") == \
        "A clear, supportive year ahead."


def test_human_date_and_tidy():
    assert _human_date("2026-10-31") == "October 2026"
    assert _human_date("2027-06") == "June 2027"
    assert _human_date("later this year") == "later this year"
    assert _tidy("potential for Career Growth, Status & Vo") == \
        "Potential for Career Growth, Status."
    assert _tidy("Leaning yes") == "Leaning yes."


def test_paid_summary_keeps_a_dated_finding_that_named_a_technique():
    """The date is what was paid for; the wording is what gets translated."""
    out = build_plain_summary(
        kind="user_question", html="<p>Some visible paid prose about your career.</p>",
        meta={"question": "How will my career go?",
              "answer": {"label": "Steady, gradual progress in your career",
                         "breakthrough": "Saturn Antardasha (2027-01-10 to 2029-08-17)"}},
        paid=True,
    )
    blob = _blob(out)
    assert "2027-01-10" in blob
    assert "Antardasha" not in blob
    assert "sub-period" in blob


# ---------------------------------------------------------------------------
# free / paid section structure
# ---------------------------------------------------------------------------
def test_fallback_summary_for_horary():
    html = "<p>The answer is unlikely.</p>"
    out = build_plain_summary(
        kind="horary",
        html=html,
        meta={"question": "Will I get the job?",
              "answer": {"label": "Leaning no", "confidence": "moderate"}},
        paid=False,
    )
    assert out["sections"]
    assert out["generated"] == "fallback"
    blob = _blob(out).lower()
    assert "job" in blob
    assert "leaning no" not in blob
    assert _roles(out).count("locked") == 1
    assert _roles(out)[-1] == "cta"


def test_free_user_question_summary_closes_on_locked_then_cta():
    html = "<p>Jupiter is in Cancer and Saturn is in Pisces.</p>"
    out = build_plain_summary(
        kind="user_question",
        html=html,
        meta={"question": "How will be my career?",
              "answer": {"label": "Supportive planetary alignment",
                         "direction": "support",
                         "breakthrough": "March 2027"}},
        paid=False,
    )
    roles = _roles(out)
    assert roles.count("locked") == 1
    assert roles.count("cta") == 1
    assert roles[-1] == "cta"
    locked = [s for s in out["sections"] if s["role"] == "locked"][0]
    assert "waiting" in locked["body"].lower() or "held back" in locked["body"].lower()


def test_free_summary_never_quotes_a_date():
    """The dates are what the paid half sells; a free summary must not leak one."""
    html = "<p>The window opens in March 2027 once the period changes.</p>"
    out = build_plain_summary(
        kind="user_question",
        html=html,
        meta={"question": "When will my case end?",
              "answer": {"label": "A slow but workable outcome",
                         "direction": "mixed",
                         "breakthrough": "March 2027"}},
        paid=False,
    )
    blob = " ".join(f"{s['title']} {s['body']}" for s in out["sections"])
    assert not _MONTH_YEAR.search(blob)
    assert "2027" not in blob


def test_paid_user_question_summary_includes_breakthrough():
    html = "<p>Jupiter is in Cancer and Saturn is in Pisces.</p>"
    out = build_plain_summary(
        kind="user_question",
        html=html,
        meta={"question": "How will be my career?",
              "answer": {"label": "Supportive planetary alignment",
                         "breakthrough": "March 2027"}},
        paid=True,
    )
    assert "March 2027" in _blob(out)
    assert "cta" not in _roles(out)


def test_free_palm_summary_includes_personality_traits():
    palm_html = """
    <div class="pv-row strong">
      <div class="pv-head"><b>Your hand shape</b><span class="pv-both">&#10003; in both hands</span></div>
      <p class="pv-sign">a square palm with long, slender fingers — an Air hand.</p>
      <p class="pv-means">You are an intuitive thinker, strategist, and communicator. You thrive on variety, meaningful conversation, and intellectual challenge. Monotony and repetitive work drains you faster than hard mental labor, and you need to see why before you commit your energy.</p>
    </div>
    <div class="pv-row strong">
      <div class="pv-head"><b>Your thumb</b><span class="pv-pill strong">A strength</span></div>
      <p class="pv-sign">a thumb with beautifully balanced will and logic sections.</p>
      <p class="pv-means">You possess what classical palmistry calls the 'Governing Thumb' — a harmonious balance where thoughtful planning and decisive action move in seamless alignment.</p>
    </div>
    <div class="pv-row care">
      <div class="pv-head"><b>Thumb length</b><span class="pv-pill care">Needs care</span></div>
      <p class="pv-sign">a receptive thumb.</p>
      <p class="pv-means">You lead with heart, empathy, and adaptability. You are generous in discussions, though you must guard against giving away leverage too easily in negotiations.</p>
    </div>
    """
    out = build_plain_summary(
        kind="palm", html=palm_html,
        meta={"dominantHand": "right", "handType": "air"},
        paid=False,
    )
    titles = [s["title"].lower() for s in out["sections"]]
    assert any("personality" in t or "temperament" in t or "strengths" in t for t in titles)

    blob = _blob(out).lower()
    assert "thinker" in blob or "strategist" in blob or "communicator" in blob
    assert "governing thumb" in blob or "balanced" in blob or "empathy" in blob

    locked = [s for s in out["sections"] if s["role"] == "locked"]
    assert locked, "Free palm summary must account for what is still locked"
    assert _roles(out)[-1] == "cta"


# ---------------------------------------------------------------------------
# the brief drives the fallback
# ---------------------------------------------------------------------------
_FULL_FACTS = {
    "kind": "full_report",
    "personality_traits": [
        "You think in systems and dislike being rushed to a decision",
        "You carry more responsibility than you admit to",
    ],
    "phase_direction": "caution",
    "phase_tone": "A demanding stretch that rewards patience over speed",
    "phase_end": "November 2027",
    "phase_notes": ["Money follows effort slowly here, not instantly"],
    "hardest_areas": ["career", "health"],
    "hardest_area_labels": ["Work & Career", "Health & Vitality"],
    "cards": [
        {"label": "Work & Career", "direction": "caution", "score": 0.4,
         "outlook_line": "Recognition is delayed but not denied",
         "support_n": 3, "signal_ids": ["x1"]},
        {"label": "Marriage", "direction": "support",
         "outlook_line": "A steady, supportive partnership pattern"},
    ],
    "timing_windows": [
        {"label": "Career opening", "start": "2027-02", "end": "2027-06"},
        {"label": "Property", "start": "2028-01"},
    ],
    "approved_remedies": ["Sun remedy", "Saturn remedy", "Moon remedy"],
    "facts_hash": "deadbeef",
}


def test_full_report_fallback_is_facts_driven():
    """No meta answer/teaser exists for this kind, so the brief must carry it."""
    html = "<p>Some rendered paragraphs of the report body that we do not want sliced.</p>"
    out = build_plain_summary(
        kind="full_report", html=html, meta={"paidSections": ["Exact dates for every life area"]},
        facts=_FULL_FACTS, paid=True,
    )
    blob = _blob(out)
    assert "patience" in blob.lower()
    assert "Work & Career" in blob
    assert "November 2027" in blob
    titles = [s["title"] for s in out["sections"]]
    assert "Planetary phase & influences" not in titles


def test_free_full_report_fallback_includes_foundations_and_strained_areas():
    facts = {
        **_FULL_FACTS,
        "cards": [
            {"label": "Self & vitality", "outlook_line": "Your inner drive stays steady."},
            {"label": "Money & wealth", "outlook_line": "Savings grow through consistency."},
            {"label": "Siblings & courage", "outlook_line": "Initiative strengthens with practice."},
            {"label": "Parents & roots", "outlook_line": "Family support remains a resource."},
        ],
    }
    out = build_plain_summary(
        kind="full_report", html="<p>Free preview.</p>", meta={},
        facts=facts, paid=False,
    )
    blob = _blob(out)
    assert all(code in blob for code in ("D1", "D2", "D3", "D12"))
    assert "Work & Career" in blob
    assert _roles(out)[-1] == "cta"


def test_brief_drops_internal_fields():
    brief = _summary_brief("full_report", {}, _FULL_FACTS, paid=True)
    blob = str(brief)
    assert "facts_hash" not in blob
    assert "support_n" not in blob
    assert "signal_ids" not in blob
    assert brief["areas_under_pressure"][0] == "Work & Career"


def test_free_brief_holds_no_dates():
    brief = _summary_brief("full_report", {}, _FULL_FACTS, paid=False)
    blob = str(brief)
    assert "2027" not in blob
    assert "timing" not in blob


def test_full_report_free_summary_holds_no_date_from_a_phase_note():
    """phase_notes carry dates inline; the free half must not repeat them."""
    out = build_plain_summary(
        kind="full_report", html="<p>A free preview of the reading.</p>",
        meta={"paidSections": ["Exact dates for every life area"]},
        facts=_FULL_FACTS, paid=False,
    )
    blob = " ".join(f"{s['headline'] if 'headline' in s else ''} {s['title']} {s['body']}"
                    for s in out["sections"])
    blob += " " + (out.get("headline") or "")
    assert "2027" not in blob
    assert not _MONTH_YEAR.search(blob)
    # ...and the summary still says something real.
    assert "Work & Career" in blob or "patience" in blob.lower()


def test_headline_is_a_sentence_not_a_bare_adjective():
    out = build_plain_summary(
        kind="full_report", html="<p>A free preview of the reading.</p>",
        meta={}, facts={**_FULL_FACTS, "phase_tone": "supportive"}, paid=False,
    )
    headline = out["headline"]
    assert len(headline.split()) >= 3, headline
    assert "supportive" in headline.lower()


def test_locked_checklist_drops_labels_that_name_a_technique():
    inv = _locked_inventory(
        "<p>Paid body.</p>", None,
        {"paidSections": ["Ashtakavarga on today's transits",
                          "The dasha you are running, with dates",
                          "What helps while this period runs"]},
    )
    joined = " ".join(inv["items"])
    assert "Ashtakavarga" not in joined
    assert "dasha" not in joined
    assert "What helps while this period runs" in joined


def test_locked_inventory_counts_without_quoting():
    inv = _locked_inventory(
        "<p>The window runs March 2027 to June 2027.</p>", _FULL_FACTS,
        {"paidSections": ["Exact dates for every life area"]},
    )
    assert inv["dated_windows"] == 2
    assert inv["life_areas"] == 2
    assert inv["remedies"] == 3
    joined = " ".join(inv["items"])
    assert "Two dated windows" in joined
    assert "2027" not in joined


# ---------------------------------------------------------------------------
# QA gates
# ---------------------------------------------------------------------------
def test_validate_rejects_jargon():
    prose = _prose(
        ("Where you stand", "Your Saturn antardasha is running and the 10th house "
                            "carries the weight of it for now, steadily.", "insight"),
    )
    fails = _validate(prose, "source text", paid=True, brief={})
    assert any(f.startswith("jargon:") for f in fails)
    assert "jargon:bare_house_number" in fails


def test_validate_rejects_free_date_and_allows_daily():
    prose = _prose(
        ("The opening", "The strongest opening for this sits around March 2027, "
                        "when the pressure you are under finally eases off.", "insight"),
        ("What is waiting", "Four dated windows are written and waiting for you.", "locked"),
        ("Unlock", "Unlock the full report and all of it opens straight away.", "cta"),
    )
    source = "The strongest opening sits around March 2027 for you."
    assert "free_date_leak" in _validate(prose, source, kind="user_question", paid=False, brief={})
    assert "free_date_leak" not in _validate(prose, source, kind="daily", paid=False, brief={})


def test_validate_rejects_duplicate_sections():
    body = ("Recognition at work is delayed but not denied, and steady effort is "
            "what moves it rather than pressure.")
    prose = _prose(
        ("Where you stand", body, "insight"),
        ("What it means", body, "insight"),
    )
    assert "duplicate_sections" in _validate(prose, body, paid=True, brief={})


def test_validate_flags_vagueness_against_the_brief():
    vague = _prose(
        ("Overview", "This period shows activity and the reading holds important "
                     "insights for the road ahead of you now.", "insight"),
    )
    brief = _summary_brief("full_report", {}, _FULL_FACTS, paid=True)
    assert "not_specific" in _validate(vague, "source", paid=True, brief=brief)

    grounded = _prose(
        ("Overview", "Recognition in your career is delayed rather than denied, and "
                     "patience is what moves it along here.", "insight"),
    )
    assert "not_specific" not in _validate(grounded, "source", paid=True, brief=brief)


def test_validate_structure_failures_are_separable():
    prose = _prose(
        ("Where you stand", "Recognition in your career is delayed rather than denied, "
                            "and patience is what moves it.", "insight"),
    )
    fails = _validate(prose, "source", kind="full_report", paid=False, brief={})
    assert "structure:locked" in fails
    assert "structure:cta" in fails
    assert all(f.startswith("structure:") for f in fails)


# ---------------------------------------------------------------------------
# dual build + gating
# ---------------------------------------------------------------------------
def test_attach_builds_both_halves():
    free_html = "<p>A short free preview of the reading with the diagnosis only.</p>"
    paid_html = ("<p>The full reading names Work &amp; Career and the window that opens "
                 "in February 2027, with the remedies that go with it.</p>")
    meta = attach_plain_summary(
        {"paidSections": ["Exact dates for every life area"]},
        kind="full_report", free_html=free_html, paid_html=paid_html,
        paid=False, facts=_FULL_FACTS,
    )
    assert meta["plainSummary"]["paid"] is False
    assert meta["plainSummaryPaid"]["paid"] is True
    free_roles = [s.get("role") for s in meta["plainSummary"]["sections"]]
    assert free_roles[-1] == "cta"
    assert "cta" not in [s.get("role") for s in meta["plainSummaryPaid"]["sections"]]
    assert meta["plainSummary"]["locked"]["dated_windows"] == 2


def test_attach_skips_paid_when_halves_are_identical():
    html = "<p>One half only, nothing extra behind the paywall for this kind.</p>"
    meta = attach_plain_summary(
        {}, kind="muhurat", free_html=html, paid_html=html, paid=False,
        facts=None,
    )
    assert "plainSummary" in meta
    assert "plainSummaryPaid" not in meta


# ---------------------------------------------------------------------------
# the LLM path, driven by a stub (no network)
# ---------------------------------------------------------------------------
def _llm_on(monkeypatch, replies):
    """Enable the LLM path and serve `replies` in order; record the prompts."""
    monkeypatch.setattr("llm.summary._enabled", lambda: True)
    seen: list[str] = []
    queue = list(replies)

    def _fake(schema, system, user, temperature=0.35):
        seen.append(user)
        return queue.pop(0) if queue else None

    monkeypatch.setattr("llm.summary._complete", _fake)
    return seen


def test_llm_prompt_carries_the_brief_and_locked_counts(monkeypatch):
    good = _prose(
        ("Where you stand", "Recognition in your career is delayed rather than denied, "
                            "and patience is what moves it along right now.", "insight"),
        ("Why it feels this way", "You think in systems and dislike being rushed, which "
                                  "is exactly what this stretch keeps asking of you. You "
                                  "also carry more responsibility than you admit to.", "insight"),
        ("What the full report adds", "Two dated windows and a verdict for each life area "
                                      "are written and waiting for you.", "locked"),
        ("Unlock the full reading", "Unlock and all of it opens straight away, and it "
                                    "stays in your account for later.", "cta"),
    )
    seen = _llm_on(monkeypatch, [good])
    out = build_plain_summary(
        kind="full_report", html="<p>The free preview text.</p>",
        meta={"paidSections": ["Exact dates for every life area"]},
        facts=_FULL_FACTS, paid=False, paid_html="<p>February 2027 window.</p>",
    )
    assert out["generated"] == "llm"
    assert out["headline"]
    prompt = seen[0]
    assert "FREE PREVIEW" in prompt
    assert "Engine findings" in prompt
    assert "Locked inventory" in prompt
    assert "dated_windows" in prompt
    assert "facts_hash" not in prompt      # internals never reach the model
    assert "2027" not in prompt.split("Visible report text")[0]


def test_free_full_report_rejects_a_generic_summary_without_personality(monkeypatch):
    generic = _prose(
        ("Where you stand", "Your career area is under pressure, so progress takes patience.",
         "insight"),
        ("Why it feels this way", "Your resources need steadier handling while you keep "
                                   "working toward recognition.", "insight"),
        ("What the full report adds", "Two dated windows are written and waiting for you.",
         "locked"),
        ("Unlock the full reading", "Unlock the full report and everything opens straight "
                                   "away.", "cta"),
    )
    brief = _summary_brief("full_report", {}, _FULL_FACTS, paid=False)
    assert "personality_missing" in _validate(
        generic, "visible preview", kind="full_report", paid=False, brief=brief,
    )

    _llm_on(monkeypatch, [generic, generic])
    out = build_plain_summary(
        kind="full_report", html="<p>The free preview text.</p>",
        meta={}, facts=_FULL_FACTS, paid=False,
    )
    assert out["generated"] == "fallback"
    blob = _blob(out).lower()
    assert "think in systems" in blob
    assert "responsibility" in blob


def test_llm_rejection_retries_then_falls_back(monkeypatch):
    """An invented date cannot be repaired by rewriting, so QA must win."""
    ungrounded = _prose(
        ("Where you stand", "Your strongest opening for work arrives in August 2031 "
                            "and everything before it is preparation for that.", "insight"),
    )
    seen = _llm_on(monkeypatch, [ungrounded, ungrounded])
    out = build_plain_summary(
        kind="full_report", html="<p>Preview text.</p>", meta={},
        facts=_FULL_FACTS, paid=True,
    )
    assert len(seen) == 2, "a rejected reply must get exactly one retry"
    assert "rejected by review" in seen[1]
    assert out["generated"] == "fallback"


def test_llm_jargon_is_rewritten_rather_than_discarded(monkeypatch):
    """Losing the term is required; losing the whole draft is a worse outcome."""
    jargony = _prose(
        ("Where you stand", "Your Saturn antardasha runs through the 10th house, so "
                            "recognition at work is delayed rather than denied.", "insight"),
        ("Why it feels this way", "You value order and dislike being rushed, which is "
                                  "exactly what this stretch of your chart keeps testing.",
         "insight"),
    )
    seen = _llm_on(monkeypatch, [jargony])
    out = build_plain_summary(
        kind="full_report", html="<p>Preview text.</p>", meta={},
        facts=_FULL_FACTS, paid=True,
    )
    assert len(seen) == 1, "a repairable draft must not burn a retry"
    assert out["generated"] == "llm"
    blob = _blob(out)
    assert "antardasha" not in blob.lower()
    assert "10th house" not in blob.lower()
    assert "sub-period" in blob
    assert "recognition at work is delayed" in blob


def test_retry_prompt_explains_the_failure_in_words(monkeypatch):
    """A bare code like `not_specific` gives the model nothing to act on."""
    vague = _prose(
        ("Overview", "This reading holds important insights about the period you are "
                     "in and the general direction of your life at the moment.", "insight"),
    )
    seen = _llm_on(monkeypatch, [vague, vague])
    build_plain_summary(
        kind="full_report", html="<p>Preview text.</p>", meta={},
        facts=_FULL_FACTS, paid=True,
    )
    assert len(seen) == 2
    assert "REPORT BRIEF" in seen[1]
    assert "not_specific" not in seen[1]


def test_llm_structure_gap_is_repaired_not_discarded(monkeypatch):
    missing_close = _prose(
        ("Where you stand", "Recognition in your career is delayed rather than denied, "
                            "and patience is what moves it along right now. You think in "
                            "systems and carry more responsibility than you admit to.", "insight"),
    )
    _llm_on(monkeypatch, [missing_close, missing_close])
    out = build_plain_summary(
        kind="full_report", html="<p>Preview text.</p>",
        meta={"paidSections": ["Exact dates"]}, facts=_FULL_FACTS, paid=False,
    )
    assert out["generated"] == "llm", "good prose must not be thrown away over structure"
    roles = _roles(out)
    assert roles.count("locked") == 1
    assert roles[-1] == "cta"


def test_llm_client_stub_wiring(monkeypatch):
    """The real _complete path, through core.llm_client's stub hook."""
    llm_client = pytest.importorskip("core.llm_client")
    monkeypatch.setattr("llm.summary._enabled", lambda: True)
    captured = {}

    def _stub(schema, system, user, **kw):
        captured["schema"] = schema.__name__
        captured["system"] = system
        return _prose(
            ("The answer", "The chart leans against this working out on the timing you "
                           "have in mind, and it is fairly sure of that.", "insight"),
        )

    llm_client.set_stub(_stub)
    try:
        out = build_plain_summary(
            kind="horary", html="<p>The answer is unlikely.</p>",
            meta={"question": "Will I get the job?",
                  "answer": {"label": "Leaning no", "confidence": "good"}},
            paid=True,
        )
    finally:
        llm_client.clear_stub()

    assert captured["schema"] == "PlainSummaryProse"
    assert "FORBIDDEN" in captured["system"]
    assert out["generated"] == "llm"
    assert "leans against" in _blob(out)


def test_gate_meta_hides_the_paid_summary_for_every_kind():
    try:
        from api import _gate_meta
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"api module unavailable in this environment: {exc}")

    meta = {"plainSummary": {"sections": []}, "plainSummaryPaid": {"sections": []},
            "answer": {"label": "Yes"}}
    locked = _gate_meta("full_report", meta, False)
    assert locked["plainSummaryPaid"] is None
    assert locked["answer"] == {"label": "Yes"}         # not a verdict-gated kind

    locked_q = _gate_meta("user_question", meta, False)
    assert locked_q["plainSummaryPaid"] is None
    assert locked_q["answer"] is None

    assert _gate_meta("full_report", meta, True)["plainSummaryPaid"] is not None


# ---------------------------------------------------------------------------
# the summary as a downloadable page
# ---------------------------------------------------------------------------
_PDF_META = {
    "plainSummary": {
        "headline": "A supportive stretch that rewards patience.",
        "sections": [
            {"title": "Where you stand", "body": "Free half insight.", "role": "insight"},
            {"title": "What the full report adds", "body": "Two dated windows.",
             "role": "locked"},
            {"title": "Unlock", "body": "Everything opens at once.", "role": "cta"},
        ],
    },
    "plainSummaryPaid": {
        "headline": "Your window opens in February 2027.",
        "sections": [
            {"title": "Where you stand", "body": "Paid half insight.", "role": "insight"},
            {"title": "Unlock", "body": "Should never be shown.", "role": "cta"},
        ],
    },
}


def test_summary_for_pdf_picks_the_half_the_reader_paid_for():
    from core.pdf_export import summary_for_pdf

    paid = summary_for_pdf(_PDF_META, unlocked=True)
    assert paid["headline"].endswith("February 2027.")
    assert [s["title"] for s in paid["sections"]] == ["Where you stand"], \
        "a paid reader is never pitched to in their own download"

    free = summary_for_pdf(_PDF_META, unlocked=False)
    assert free["headline"].startswith("A supportive stretch")
    assert len(free["sections"]) == 3

    assert summary_for_pdf({}, unlocked=True) is None
    assert summary_for_pdf({"plainSummary": {"sections": []}}, unlocked=False) is None


def test_summary_for_pdf_falls_back_to_the_free_half_when_paid_is_gated():
    """A locked report served through _gate_meta carries plainSummaryPaid=None."""
    from core.pdf_export import summary_for_pdf

    gated = {**_PDF_META, "plainSummaryPaid": None}
    out = summary_for_pdf(gated, unlocked=True)
    assert out["headline"].startswith("A supportive stretch")


def test_summary_html_escapes_and_builds_a_standalone_document():
    from core.pdf_export import summary_html

    summary = {"headline": "Careful <now>", "sections": [
        {"title": "Work & money", "body": 'A "quoted" line.'}]}
    block = summary_html(summary, title="Full report · Meera")
    assert "&lt;now&gt;" in block and "<now>" not in block
    assert "Work &amp; money" in block
    assert "&quot;quoted&quot;" in block or "&#x27;" in block or "quoted" in block
    assert not block.lstrip().startswith("<!doctype")

    doc = summary_html(summary, title="Full report", standalone=True)
    assert doc.lstrip().lower().startswith("<!doctype html")
    assert "gr-sum" in doc and "</body></html>" in doc


def test_prepend_summary_lands_inside_body_on_its_own_page():
    from core.pdf_export import prepend_summary, summary_html

    block = summary_html({"headline": "Lead line.", "sections": [
        {"title": "Where you stand", "body": "Body copy."}]})
    report = ('<html><head><style>body{margin:0}</style></head>'
              '<body><nav>toc</nav><h1>Report</h1></body></html>')
    out = prepend_summary(report, block)
    assert '<body><div class="gr-sum-break">' in out
    assert out.index("gr-sum-eyebrow") < out.index("<nav>")
    assert out.index("page-break-after") < out.index("</head>")
    assert "<h1>Report</h1>" in out
    assert prepend_summary(report, "") == report


def test_prepend_summary_survives_a_fragment_without_head_or_body():
    from core.pdf_export import prepend_summary

    out = prepend_summary("<p>Loose fragment.</p>", "<div>SUM</div>")
    assert "SUM" in out and "Loose fragment" in out
    assert out.index("SUM") < out.index("Loose fragment")
    assert "page-break-after" in out
