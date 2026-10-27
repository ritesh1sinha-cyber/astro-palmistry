from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

HERE = Path(__file__).resolve()
ENG = HERE.parents[1]
if str(ENG) not in sys.path:
    sys.path.insert(0, str(ENG))

from daily_card import _locked_preview, _personal_moon_focus


def _reading():
    return {
        "lagna": "Aries",
        "natal_planets": {
            "Venus": {"sign": "Taurus", "house": 2, "dignity": "domicile"},
        },
        "moon_transit": {
            "sign": "Libra",
            "nakshatra": "Swati",
            "house_from_lagna": 7,
            "house_from_moon": 4,
        },
        "ashtakavarga": {
            "moon": {"sav": 23, "bav": 3},
            "dasha_lords": [{
                "role": "Antardasha",
                "planet": "Venus",
                "sign": "Leo",
                "sav": 23,
                "bav": 3,
                "house_from_lagna": 5,
                "meaning": "Mixed support.",
            }],
        },
    }


def test_daily_personal_focus_exposes_exact_moon_av_and_significator():
    html = _personal_moon_focus(_reading())
    assert "Moon in Libra" in html
    assert "SAV 23/56" in html
    assert "Moon BAV 3/8" in html
    assert "Life area:" in html
    assert "Venus" in html
    assert "lower structural support" in html.lower()


def test_daily_free_teaser_sells_personal_facts_not_generic_technical_dump():
    """The locked teaser must name this reader's own periods.

    It receives the three running lords and used to ignore them, describing
    the paid feature in the abstract instead. Naming them is the whole
    difference between "we sell a timing clock" and "your clock says this".
    """
    html = _locked_preview(price=298, n_lanes=8, md="Saturn", ad="Venus", pd="Moon")
    for lord in ("Saturn", "Venus", "Moon"):
        assert lord in html, lord
    assert "three-tier" in html
    # Internal marketing vocabulary is not customer copy.
    assert "highest-converting" not in html


def test_palm_fair_photo_hides_special_marks_in_customer_workings():
    from palm_api.quality_gate import filter_special_mark_findings
    items = [
        {"num": 17, "title": "Trident (Trishul) sign", "kind": "mark"},
        {"num": 18, "title": "Heart line", "kind": "line"},
    ]
    out = filter_special_mark_findings(items, {"grade": "fair", "special_marks_allowed": False})
    assert [x["num"] for x in out] == [18]


def test_false_positive_boo_is_not_blocked_by_customer_boundary():
    from qa_checks.customer_text_sanitizer import validate_customer_text
    html = "<p>Several books on Wednesday can help.</p>"
    leaks = validate_customer_text(html)
    assert not any("boo" in x.lower() for x in leaks)


def test_paid_daily_render_contains_personalization_blocks():
    from daily_card import render
    r = _reading()
    r.update({
        "client": "Meera",
        "date": "2026-08-12",
        "tone": "steady",
        "opening": "A steady day.",
        "natal_moon": {"sign": "Cancer", "nakshatra": "Pushya"},
        "dasha": {"md": "Saturn", "ad": "Venus", "pd": "Moon"},
        "vedic_confluence": {
            "verdict_plain": "A steady day.",
            "lanes": [{"lane": "Moon", "signal": "support", "weight": "high"}],
            "dasha": {},
        },
        "dos": [{"text": "Finish one important task."}],
        "donts": [{"text": "Do not rush."}],
        "lucky_numbers": {"primary": 7},
        "lucky_colors": [{"name": "White"}],
        "muhurat": {
            "available": True,
            "day_summary": "Strongest day window: Labh choghadiya (05:31-07:06). Avoid Rahu Kaal 11:51-13:26.",
            "windows": {
                "good_choghadiya": [{
                    "start": "05:31", "end": "07:06",
                    "label": "Labh", "plain": "Gains and profit flavour.",
                }],
                "tri_kaal": [{
                    "start": "11:51", "end": "13:26",
                    "label": "Rahu Kaal", "plain": "Classic inauspicious window.",
                }],
            },
        },
    })
    html = render(r, name="Meera", paid=True, day=date(2026, 8, 12))
    assert "Your most personal Moon transit today" in html
    assert "SAV 23/56" in html
    assert "Moon BAV 3/8" in html
    assert "Every lane that voted on today" not in html
    assert "Best and avoid times" in html
    assert "Why today reads this way" in html
    assert "The clock you are actually running on" in html
