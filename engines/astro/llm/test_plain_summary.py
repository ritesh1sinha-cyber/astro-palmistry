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
    )
    assert out["sections"]
    assert out["generated"] == "fallback"
    blob = " ".join(s["body"] for s in out["sections"]).lower()
    assert "leaning no" in blob or "job" in blob
