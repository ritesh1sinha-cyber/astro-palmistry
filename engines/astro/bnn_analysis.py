#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BNN report sections - merged new book combinations + legacy foundation blocks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bnn_chart import lord_verdict
from bnn_combination import reset_claimed
from bnn_foundation import (
    education_html,
    foundation_html,
    personality_table_html,
    wealth_property_html,
)
from bnn_human import (
    human_career,
    human_children,
    human_conjunction_section,
    human_dasha,
    human_health,
    human_intro,
    human_marriage,
    human_parents,
    human_past_slice,
    human_past_themes_html,
    human_personality,
    human_remedies,
    human_siblings,
    human_travel,
)

if TYPE_CHECKING:
    from bnn_chart import BnnChart, BnnTiming


@dataclass
class BnnSection:
    id: str
    title: str
    prediction: str
    facts: str
    tone: str = "neutral"
    html_body: str = ""
    rules: list[str] = field(default_factory=list)


def analyze_all_chapters(ch: "BnnChart", bt: "BnnTiming", male: bool = True) -> list[BnnSection]:
    reset_claimed()
    sections: list[BnnSection] = []

    intro = human_intro(ch, bt)
    sections.append(BnnSection("intro", "Your chart at a glance", intro, f"Lagna {ch.lagna}, AK {ch.atmakaraka() or '-'}", "good"))

    sections.append(BnnSection(
        "foundation", "Chart foundation (lagna lord & stelliums)",
        "", f"Lagna {ch.lagna}", "good", html_body=foundation_html(ch),
    ))

    sections.append(BnnSection(
        "personality_table", "Core personality traits (BNN)",
        "", f"Moon {ch.sign('Moon')}", "good", html_body=personality_table_html(ch),
    ))

    pairs = []
    seen: set[tuple[str, str]] = set()
    for sign, ps in ch.conjunctions.items():
        if len(ps) < 2:
            continue
        a, b = ps[0], ps[1]
        key = tuple(sorted((a, b)))
        if key in seen:
            continue
        seen.add(key)
        pairs.append((a, b))

    for a, b in pairs:
        title, fact, html = human_conjunction_section(ch, a, b, male=male)
        tone = "amber" if frozenset((a, b)) == frozenset(("Mars", "Rahu")) else "good"
        sections.append(BnnSection(
            f"conj_{a}_{b}".lower(), title, "", fact, tone, html_body=html,
        ))

    pers_pred, pers_fact = human_personality(ch, bt)
    sections.append(BnnSection(
        "personality", "Personality synthesis",
        pers_pred, pers_fact, "good",
    ))

    past_html = human_past_slice(ch, bt)
    if past_html:
        sections.append(BnnSection(
            "past_slice", "Immediate past - recent Vimshottari slice",
            "", "Extract dates", "neutral", html_body=past_html,
        ))

    sections.append(BnnSection(
        "karmic", "BNN lens - recurring life themes (symbolic)",
        "", "Metaphorical only", "neutral", html_body=human_past_themes_html(ch),
    ))

    sections.append(BnnSection(
        "dasha", "Life chapter timeline",
        human_dasha(ch, bt), f"MD {bt.cur_md.get('md_lord', '-')}", "good",
    ))

    m_pred, m_fact, m_html = human_marriage(ch, bt)
    sections.append(BnnSection(
        "marriage", "Spouse & marriage", m_pred, m_fact,
        lord_verdict(ch, ch.lord_of_house(7)),
        html_body=m_html,
    ))

    h_pred, h_fact = human_health(ch)
    sections.append(BnnSection("health", "Health", h_pred, h_fact, "amber"))

    c_pred, c_fact = human_children(ch, bt)
    sections.append(BnnSection("children", "Children", c_pred, c_fact, "neutral"))

    p_pred, p_fact, p_html = human_career(ch, bt)
    sections.append(BnnSection(
        "profession", "Profession & status", p_pred, p_fact,
        "good" if ch.dig(ch.lord_of_house(10)) in ("exalted", "own_sign", "moolatrikona") else "neutral",
        html_body=p_html,
    ))

    sections.append(BnnSection(
        "education", "Education",
        "", lord_verdict(ch, ch.lord_of_house(5)), "neutral", html_body=education_html(ch),
    ))

    sections.append(BnnSection(
        "wealth", "Wealth & property",
        "", f"2nd lord {ch.lord_of_house(2)}", "good", html_body=wealth_property_html(ch),
    ))

    t_pred, t_fact = human_travel(ch)
    sections.append(BnnSection("travel", "Travel & distant horizons", t_pred, t_fact, "neutral"))

    s_pred, s_fact = human_siblings(ch)
    sections.append(BnnSection("siblings", "Siblings", s_pred, s_fact, "neutral"))

    par_pred, par_fact = human_parents(ch)
    sections.append(BnnSection("parents", "Parents", par_pred, par_fact, "neutral"))

    sections.append(BnnSection(
        "remedies", "Remedies & balance (practical first)",
        human_remedies(ch, bt), "Educational only", "neutral",
    ))

    return sections
