from pathlib import Path

from qa_checks.customer_text_sanitizer import sanitize_html_document, validate_customer_text
from report_fact_guard import visible_text

ROOT = Path(__file__).resolve().parents[2]


def test_final_customer_boundary_removes_legacy_astro_evidence():
    src = """
    <html><body>
      <p>house strength 30 of 56 — above average</p>
      <p>4 classical rules support this area — the 10th lord is in the 8th.</p>
      <p>Gemini: Personality and Characteristics Appearance: Good height...</p>
      <p>Papa-Adhi Yoga: malefics (Rahu, Sun) occupy the 6th/7th/8th from the Moon.</p>
      <p>Sub-lord and case-book method confirm the result.</p>
    </body></html>
    """
    out = sanitize_html_document(src)
    text = visible_text(out).lower()
    assert not validate_customer_text(out)
    for leaked in (
        "house strength", "10th lord", "classical rules", "personality and characteristics",
        "papa-adhi yoga", "sub-lord", "case-book method",
    ):
        assert leaked not in text


def test_customer_boundary_preserves_plain_prediction():
    src = "<p>Your career is supported, but recognition may take time.</p>"
    out = sanitize_html_document(src)
    assert "Your career is supported" in visible_text(out)
    assert not validate_customer_text(out)


def test_canonical_result_does_not_carry_raw_proof():
    from canonical_result import build_area_result

    pc = {"planets": {}, "house_lords": {}}
    # We do not need a real chart to verify the boundary contract: a missing
    # confluence falls back to the safe summary instead of exposing raw proof.
    result = build_area_result(
        pc, "career", 10,
        current_headline="Career is supported",
        current_backing="The 10th lord is in the 8th house; 4 classical rules support this area.",
    )
    backing = str(result.get("backing") or "").lower()
    assert "10th lord" not in backing
    assert "classical rules" not in backing


def test_firewall_preserves_script_style_and_attributes():
    src = """<html><style>.x{content:'10th lord';}</style>
    <script>const x='8th lord';</script>
    <div data-note="10th lord">The 10th lord is in the 8th house.</div></html>"""
    out = sanitize_html_document(src)
    assert "content:'10th lord'" in out
    assert "const x='8th lord'" in out
    assert 'data-note="10th lord"' in out
    # Attribute text is preserved; only the element body must be cleaned.
    chunk = out.split("<div", 1)[1].split("</div>", 1)[0]
    visible = chunk.split(">", 1)[1] if ">" in chunk else chunk
    assert "10th lord" not in visible


def test_public_fact_projection_is_fail_closed():
    from llm.facts import public_fact_payload
    payload = {"cards": [{"manifestation_ids": ["income_growth"], "signal_ids": ["10TH_LORD"]}], "engine_version": "secret"}
    public = public_fact_payload(payload)
    assert "signal_ids" not in public["cards"][0]
    assert "engine_version" not in public

def test_question_fallback_never_exposes_deep_raw_verdict():
    from question_answer import _human_question_evidence
    rows = _human_question_evidence({"area_key":"career","promise":{"direction":"support"},
        "deep_verdict":"The 10th lord is in the 8th house; classical rule confirms promotion."})
    joined=" ".join(rows).lower()
    assert "10th lord" not in joined and "classical rule" not in joined

def test_final_customer_boundary_strict():
    from qa_checks.final_customer_boundary import (
        CustomerBoundaryError, assert_customer_html_safe, finalize_customer_html,
    )
    assert "Career is supported" in finalize_customer_html("<p>Career is supported.</p>")
    cleaned = finalize_customer_html("<p>10th lord</p>")
    assert "10th lord" not in cleaned.lower()
    # Dirty HTML that has not been finalized must still fail the assert helper.
    try:
        assert_customer_html_safe("<p>10th lord</p>")
    except CustomerBoundaryError:
        pass
    else:
        raise AssertionError("strict boundary must block residual visible leaks")


def test_canonical_vote_normalization_removes_technical_vote_prose():
    from evidence_normalizer import normalize_vote
    from report_confluence import Vote
    samples = [
        "Mercury rules it, friendly sign, placed in your 10th",
        "house strength 24 of 56 — below average",
        "Sun, Venus, Rahu sit here",
    ]
    for raw in samples:
        ev = normalize_vote(Vote("the classical method", 1.0, raw), area="career")
        low = ev.normalized_reason.lower()
        assert "rules it" not in low
        assert "house strength" not in low
        assert "sit here" not in low


def test_question_career_horizon_is_not_job_change_or_seven_years():
    import question_answer as QA
    q = "Will my career improve in the next two years?"
    assert QA.classify(q).key == "career"
    assert QA._requested_horizon_years(q) == 2


def test_palm_fair_photo_blocks_special_mark_provenance():
    from llm.facts import build_palm_facts
    raw = {
        "confluence": {"dominant_hand": "right", "life_aspects": [{
            "key": "career", "strength": "strong",
            "summary": "Career visibility can strengthen with experience.",
            "points": [{"rule_id": "TRIDENT_ON_JUPITER"}],
        }]},
        "reading_result": {
            "measurement_quality": {
                "photo_grade": "fair", "special_marks_allowed": False,
                "future_timing_allowed": True, "interpretation_confidence": "moderate",
            },
            "special_marks": [{"id": "TRIDENT_ON_JUPITER"}],
        },
    }
    facts = build_palm_facts(raw, access="paid")
    assert facts.special_mark_ids == []
    assert all("trident" not in x.lower() for a in facts.aspects for x in a.signal_ids + a.point_ids)
