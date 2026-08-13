"""The redesigned palm report: photographs, named signs, timing, and a rail."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT, ROOT / "engines", ROOT / "engines" / "astro"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from core import palm_conversational as PC  # noqa: E402

PROSE = {
    "conversational": True,
    "personality": "You think out loud and decide in company.",
    "current_phase": "You are in the stretch where the quiet work gets noticed.",
    "hardest_area_note": "Money asks for the most attention.",
    "mind_now": ["whether to make the move you keep postponing"],
    "why_now": "Both hands put the turn in the same place.",
    "hand_contrast_note": "Your left hand is the more patient of the two.",
    "areas": {"wealth": {"outlook": "Money arrives in bursts.",
                         "timing": "The next widening is in your thirties.",
                         "remedy": "Keep six months of costs aside."}},
}


def _hand(grade="good", marks=True):
    return {
        "overlay_path": "",
        "features": {
            "morphology": {"hand_type": "air", "index_vs_ring": "ring_longer",
                           "thumb": {"length": "short",
                                     "will_vs_logic": "will_dominant",
                                     "opening": "wide"}},
            "lines": {
                "life": {"detected": True, "depth": "deep", "sweep": "wide",
                         "quality": "clear"},
                "head": {"detected": True, "depth": "deep",
                         "start_relation": "merged", "quality": "clear"},
                "heart": {"detected": True, "depth": "deep",
                          "start_zone": "saturn", "quality": "clear"},
                "fate": {"detected": True, "depth": "deep",
                         "start_zone": "mid_palm", "quality": "clear",
                         "shape": "wavy"},
            },
            "minor_lines": {"sun": {"detected": True, "strength": "strong"}},
            "mounts": {"mars": "prominent", "venus": "prominent"},
            "special_marks": ([{"type": "trident", "title": "Trident (Trishul) sign",
                                "zone": "jupiter",
                                "meaning": "A trident on your Jupiter mount."}]
                              if marks else []),
            "quality": {"grade": grade, "special_marks_allowed": marks},
        },
        "numbered_checklist": [],
    }


def _raw():
    return {
        "left": _hand("good", marks=True),
        "right": _hand("fair", marks=False),
        "confluence": {
            "dominant_hand": "right",
            "life_aspects": [{"key": "wealth", "title": "Money & Resources",
                              "strength": "moderate",
                              "points": [{"text": "You earn through skill."}]}],
            "predictions": [
                {"title": "Your life line", "age": 24, "age_range": [20, 28],
                 "text": "Around age 24, your direction settled.\nWhy: your life line"},
                {"title": "Your fate line", "age": 41, "age_range": [38, 45],
                 "text": "Around age 41, the work changes shape.\nWhy: your fate line"},
            ],
        },
    }


def _render(paid=True):
    return PC.render(_raw(), name="Meera", age=30, dominant="right",
                     paid=paid, price=499, prose=PROSE)


def test_the_report_shows_the_customers_own_photographs():
    """The prose-only page dropped them, which is what made it feel generic."""
    html = _render(paid=False)
    assert "palm-shots" in html
    assert "Left hand" in html and "Right hand" in html


def test_the_reading_names_lines_and_mounts_rather_than_describing_pads():
    html = _render()
    assert "Head line" in html
    assert "Mount of Venus" in html
    assert "Mount of Mars" in html


def test_a_difficult_sign_is_stated_with_what_to_do_about_it():
    html = _render()
    assert "What needs care" in html
    assert html.count("What to do") >= 2
    # The warning and its answer travel together, never a warning alone.
    care = re.findall(r'<div class="pv-obs care">.*?</div>', html, re.S)
    for row in care:
        assert "pv-do" in row, "a 'needs care' observation shipped without a step"


def test_a_line_is_named_once_and_then_read():
    """Every observation used to repeat the heading, so the page read "Head
    line, Head line, Head line" instead of sounding like a palmist talking.
    """
    html = _render()
    lines = html.split('id="sec-lines"')[1].split("</section>")[0]
    for name in ("Head line", "Heart line", "Fate line"):
        assert lines.count(f"<b>{name}</b>") == 1, name
    grouped = re.search(r'<div class="pv-row [a-z]+"><div class="pv-head">'
                        r"<b>Head line</b></div>(.*?)$", lines, re.S)
    assert grouped and grouped.group(1).count('class="pv-obs') >= 2


def test_marks_follow_the_hand_that_was_photographed_well():
    html = _render()
    assert "Trident" in html, "the clear hand's mark must be reported"
    assert "Right hand photograph" in html, "the blurred hand must say why it is silent"


def test_timing_is_split_at_the_readers_own_age():
    html = _render()
    behind = html.split('id="sec-behind"')[1].split("</section>")[0]
    ahead = html.split('id="sec-ahead"')[1].split("</section>")[0]
    assert "ages 20&ndash;28" in behind
    assert "ages 20&ndash;28" not in ahead
    assert "ages 38&ndash;45" in ahead


def test_the_free_half_withholds_the_paid_sections_but_not_the_hand():
    free = _render(paid=False)
    assert "Mount by mount" not in free
    assert "Your four major lines" in free
    assert "data-unlock" in free


def test_every_report_carries_a_section_rail():
    html = _render()
    assert '<nav class="secnav"' in html
    assert 'href="#sec-' in html
    # The rail must survive a print/PDF pass by hiding, not by breaking layout.
    assert "@media print{.secnav{display:none}}" in html.replace("\n", "")


def test_the_rail_lists_the_sections_that_are_actually_present():
    html = _render(paid=False)
    rail = html.split("</nav>")[0]
    assert "Mount by mount" not in rail, "free has no mounts section to jump to"
    assert "Your four major lines" in rail
