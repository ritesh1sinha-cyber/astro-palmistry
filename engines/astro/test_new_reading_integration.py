from datetime import date

from palmistry_consultation_reading import generate_palm_consultation_sections
from report_conversational import _specialist_readings_html
from specialist_readings import build_specialist_readings


def test_specialist_bundle_is_date_aware_and_fail_closed():
    pc = {"meta": {"dob": "1990-01-01", "lagna_sign": "Aries"}}
    bundle = build_specialist_readings(pc, today=date(2024, 2, 3))

    assert bundle["evaluation_date"] == "2024-02-03"
    for block in bundle.values():
        if isinstance(block, dict):
            for finding in block.get("findings", []):
                text = f"{finding.get('category')} {finding.get('title')} {finding.get('summary')}".lower()
                assert not any(term in text for term in ("death", "medical", "fertility", "ivf"))


def test_palm_consultation_does_not_invent_findings_for_poor_photo():
    result = generate_palm_consultation_sections({
        "meta": {"client_name": "Test"},
        "cv_raw_features": {"quality": {"grade": "poor"}, "lines": {}},
    }, client_name="Test")

    assert result["measured"] is True
    assert result["sections"] == {}
    assert result["timing_milestones"] == []


def test_localized_specialist_render_does_not_use_engine_english_body():
    html = _specialist_readings_html({
        "specialist_readings": {
            "chandra_naadi": {
                "findings": [{
                    "planet": "Moon",
                    "title": "English internal title",
                    "summary": "English internal prediction",
                }]
            }
        }
    }, paid=True, lang="hi_en")

    assert "Aapke" not in html
    assert "Chandra se juda ek chart pattern active" in html
    assert "English internal prediction" not in html
