"""The section rail: what a reader can jump to, and what stays out of it."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE)]

import report_shell as RS  # noqa: E402
import vedic_horary_report as VH  # noqa: E402


def _body(*sections: str) -> str:
    return "".join(sections)


def test_a_rail_needs_three_places_to_go():
    body, nav = RS.build_section_nav(
        '<h2>Your money year</h2><h2>Your work year</h2>')
    assert nav == "", "two links is a heading, not a table of contents"
    assert "id=" not in body


def test_headings_and_life_areas_both_become_destinations():
    body, nav = RS.build_section_nav(_body(
        "<h2>Who your chart says you are</h2>",
        '<article class="card"><div class="card-top">'
        '<span class="area">Work &amp; Career</span></div></article>',
        '<article class="card"><div class="card-top">'
        '<span class="area">Health &amp; Energy</span></div></article>',
    ))
    assert "Work &amp; Career" in nav
    assert "Health &amp; Energy" in nav
    for anchor in ("sec-who-your-chart-says-you-are",
                   "sec-work-career", "sec-health-energy"):
        assert f'id="{anchor}"' in body, anchor
        assert f'href="#{anchor}"' in nav, anchor


def test_a_life_area_is_indented_under_its_section():
    _, nav = RS.build_section_nav(_body(
        "<h2>Each part of your life</h2>",
        '<article class="card"><div class="card-top">'
        '<span class="area">Money</span></div></article>',
        '<article class="card"><div class="card-top">'
        '<span class="area">Children</span></div></article>',
    ))
    assert 'class="lvl1"' in nav and 'class="lvl2"' in nav


def test_workings_a_reader_expands_in_place_are_not_destinations():
    body, nav = RS.build_section_nav(_body(
        "<h2>The answer</h2><h2>The timing</h2><h2>The remedy</h2>",
        "<details><summary>Workings</summary>"
        "<h2>Ashtakavarga table</h2></details>",
    ))
    assert "Ashtakavarga" not in nav
    assert 'id="sec-ashtakavarga-table"' not in body


def test_a_section_and_the_heading_inside_it_are_one_destination():
    _, nav = RS.build_section_nav(_body(
        "<h2>The answer</h2><h2>The timing</h2>",
        '<section class="section locked-preview">'
        "<h2>What the subscription adds</h2></section>",
    ))
    assert nav.count("What the subscription adds") == 1


def test_a_long_heading_is_shortened_for_the_rail_but_not_in_the_page():
    long = "How well today&#x27;s sky is supported on your chart"
    body, nav = RS.build_section_nav(_body(
        f"<h2>{long}</h2><h2>Second</h2><h2>Third</h2>"))
    assert long in body, "the page keeps the heading the writer wrote"
    first = nav.split('href="#sec-how-well-today-s-sky-is-supported">')[1].split("</a>")[0]
    assert first.endswith("…") and len(first) < 40


def test_a_heading_may_name_its_own_rail_entry():
    _, nav = RS.build_section_nav(_body(
        '<h2 data-nav="Special marks">The marks your palm carries, '
        "and what a reader makes of them</h2>",
        "<h2>Second</h2><h2>Third</h2>"))
    assert ">Special marks<" in nav


def test_the_rail_disappears_when_the_reading_is_printed():
    assert "@media print" in RS.SECTION_NAV_CSS
    _, nav = RS.build_section_nav("<h2>A</h2><h2>B</h2><h2>C</h2>")
    assert 'class="secnav"' in nav


def test_injecting_the_rail_twice_leaves_one_rail():
    doc = RS.page("Reading", "<h2>A</h2><h2>B</h2><h2>C</h2>")
    assert doc.count('class="secnav"') == 1
    again = RS.inject_section_nav(doc)
    assert again.count('class="secnav"') == 1


def test_a_horary_step_list_survives_past_the_seventh_step():
    """The step list grows an eighth entry whenever the chart has classical
    notes to add. A fixed seven-glyph string used to take the Vedic half of a
    paid horary report down with it, leaving the customer a Western-only answer.
    """
    icons = [VH._step_icon(i) for i in range(9)]
    assert icons[:3] == ["\u2460", "\u2461", "\u2462"]
    assert len(set(icons)) == 9, "every step is numbered distinctly"
    assert VH._step_icon(25) == "26", "and it degrades to plain digits"
