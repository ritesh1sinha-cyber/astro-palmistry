from __future__ import annotations

from llm.summary import build_plain_summary, html_to_report_text


def test_html_to_report_text_skips_scripts():
    html = "<style>.x{}</style><script>alert(1)</script><p>Hello chart</p>"
    assert "Hello chart" in html_to_report_text(html)
    assert "alert" not in html_to_report_text(html)


def test_fallback_summary_for_horary():
    html = "<p>The answer is unlikely.</p>"
    out = build_plain_summary(
        kind="horary",
        html=html,
        meta={"question": "Will I get the job?", "answer": {"label": "Leaning no", "confidence": "moderate"}},
        paid=False,
    )
    assert out["sections"]
    assert out["generated"] == "fallback"
    blob = " ".join(s["body"] for s in out["sections"]).lower()
    assert "leaning no" in blob or "job" in blob
    assert any("unlock" in s["title"].lower() or "unlock" in s["body"].lower() for s in out["sections"])


def test_free_user_question_summary_has_disclaimer():
    html = "<p>Jupiter is in Cancer and Saturn is in Pisces.</p>"
    out = build_plain_summary(
        kind="user_question",
        html=html,
        meta={"question": "How will be my career?", "answer": {"label": "Supportive planetary alignment", "breakthrough": "March 2027"}},
        paid=False,
    )
    assert out["sections"]
    # Check that disclaimer is present
    unlock_sec = [s for s in out["sections"] if "unlock" in s["title"].lower()]
    assert unlock_sec, "Free user question summary must have an Unlock section"
    assert "remedies" in unlock_sec[0]["body"].lower() or "verdict" in unlock_sec[0]["body"].lower()


def test_paid_user_question_summary_includes_breakthrough():
    html = "<p>Jupiter is in Cancer and Saturn is in Pisces.</p>"
    out = build_plain_summary(
        kind="user_question",
        html=html,
        meta={"question": "How will be my career?", "answer": {"label": "Supportive planetary alignment", "breakthrough": "March 2027"}},
        paid=True,
    )
    assert out["sections"]
    blob = " ".join(s["body"] for s in out["sections"])
    assert "March 2027" in blob


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
        kind="palm",
        html=palm_html,
        meta={"dominantHand": "right", "handType": "air"},
        paid=False,
    )
    assert out["sections"]
    titles = [s["title"].lower() for s in out["sections"]]
    assert any("personality" in t or "temperament" in t or "strengths" in t for t in titles)
    
    blob = " ".join(s["body"] for s in out["sections"]).lower()
    assert "thinker" in blob or "strategist" in blob or "communicator" in blob
    assert "governing thumb" in blob or "balanced" in blob or "empathy" in blob
    
    # Free summary must include the palm unlock disclaimer
    unlock_sec = [s for s in out["sections"] if "unlock" in s["title"].lower()]
    assert unlock_sec, "Free palm summary must include Unlock section"
    assert "timeline" in unlock_sec[0]["body"].lower() or "age" in unlock_sec[0]["body"].lower() or "line markings" in unlock_sec[0]["body"].lower()


