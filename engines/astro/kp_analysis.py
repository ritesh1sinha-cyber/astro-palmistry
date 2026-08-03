#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KP report sections - merged new book logic + legacy gold foundation blocks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from kp_book_data import links_verdict
from kp_foundation import (
    cusp_promise_grid_html,
    key_cusps_table_html,
    lahiri_warning_html,
    methodology_html,
    ruling_table_html,
)
from kp_human import (
    human_career,
    human_chart_wiring,
    human_children,
    human_dasha,
    human_health,
    human_intro,
    human_marriage,
    human_parents,
    human_personality,
    human_pratyantar,
    human_remedies,
    human_siblings,
    human_travel,
)
from nakshatra_human import human_birth_star_kp

if TYPE_CHECKING:
    from kp_chart import KPChart


@dataclass
class KPSection:
    id: str
    title: str
    prediction: str
    facts: str
    tone: str = "neutral"
    html_body: str = ""
    rules: list[str] = field(default_factory=list)


def _tone_from_csl(kp: "KPChart", house: int, domain: str) -> str:
    sub = kp.csl(house)
    v, _, _ = links_verdict(kp.links(sub), domain)
    if v == "promised":
        return "good"
    if v == "denied":
        return "amber"
    return "neutral"


def analyze_all_chapters(kp: "KPChart") -> list[KPSection]:
    sections: list[KPSection] = []

    sections.append(KPSection(
        "intro", "Your chart at a glance", human_intro(kp),
        f"Lagna {kp.lagna}, CSL-1 {kp.csl(1)}", "good",
    ))

    sections.append(KPSection(
        "methodology", "How KP reads your chart",
        "", "K.P. New block", "neutral",
        html_body=methodology_html() + lahiri_warning_html(),
    ))

    sections.append(KPSection(
        "ruling", "Ruling planets",
        "", "Extract ruling chain", "good",
        html_body=ruling_table_html(kp),
    ))

    sections.append(KPSection(
        "cusp_grid", "Cusp promise grid",
        "", "CSL link verdicts", "good",
        html_body=key_cusps_table_html(kp) + cusp_promise_grid_html(kp),
    ))

    sections.append(KPSection(
        "wiring", "KP wiring in plain English",
        "", "Cusp sub lords", "good",
        html_body=human_chart_wiring(kp),
    ))

    sections.append(KPSection(
        "dasha", "Life chapter timeline",
        human_dasha(kp), f"MD {kp.maha.get('lord', '-')}", "good",
    ))

    pr = human_pratyantar(kp)
    if pr:
        sections.append(KPSection(
            "pratyantar", "Right now - month-level clock",
            pr, f"{len(kp.pratyantars)} pratyantar slices", "neutral",
        ))

    p_pred, p_fact = human_personality(kp)
    sections.append(KPSection(
        "personality", "Personality & temperament",
        p_pred, p_fact, "good",
    ))

    nk_pred, nk_fact = human_birth_star_kp(kp)
    if nk_pred:
        sections.append(KPSection(
            "birth_star", "Birth-star karmic lesson",
            nk_pred, nk_fact, "neutral",
        ))

    h_pred, h_fact = human_health(kp)
    sections.append(KPSection("health", "Health & energy", h_pred, h_fact, "amber"))

    m_pred, m_fact = human_marriage(kp)
    sections.append(KPSection(
        "marriage", "Spouse & marriage", m_pred, m_fact, _tone_from_csl(kp, 7, "marriage"),
    ))

    c_pred, c_fact = human_children(kp)
    sections.append(KPSection("children", "Children & creativity", c_pred, c_fact, "neutral"))

    pr_pred, pr_fact, pr_html = human_career(kp)
    sections.append(KPSection(
        "profession", "Career & profession", pr_pred, pr_fact,
        _tone_from_csl(kp, 10, "career"),
        html_body=pr_html,
    ))

    t_pred, t_fact = human_travel(kp)
    sections.append(KPSection("travel", "Travel & distant horizons", t_pred, t_fact, "neutral"))

    s_pred, s_fact = human_siblings(kp)
    sections.append(KPSection("siblings", "Siblings & courage", s_pred, s_fact, "neutral"))

    par_pred, par_fact = human_parents(kp)
    sections.append(KPSection("parents", "Parents", par_pred, par_fact, "neutral"))

    sections.append(KPSection(
        "remedies", "Remedies & balance (practical first)",
        human_remedies(kp), "Educational only", "neutral",
    ))

    return sections
