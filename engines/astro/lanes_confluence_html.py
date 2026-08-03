#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Client-facing HTML for multi-lane confluence - predictions only, no method names."""
from __future__ import annotations

import html
import re
from datetime import date, datetime

from client_report_html import (
    client_css,
    health_section_html,
    remedies_html,
    traffic_light_html,
    transition_calendar_html,
)
from confluence_longevity_lane import build_longevity_context
from lane_claim import DOMAIN_TITLE, DOMAINS
from lanes_confluence_engine import DomainVerdict


def _e(s) -> str:
    return html.escape(str(s))


def _confidence_pill(v: DomainVerdict) -> str:
    if v.meets_threshold:
        cls, label = "hi", "Strong agreement"
    elif v.lane_pct >= 0.5:
        cls, label = "mid", "Moderate agreement"
    else:
        cls, label = "lo", "Mixed signals"
    return f'<span class="pill {cls}">{label}</span>'


def _card_tone(v: DomainVerdict) -> str:
    if v.direction == "positive" and v.meets_threshold:
        return "green"
    if v.direction == "caution":
        return "red" if v.meets_threshold else "amber"
    return "amber"


def _trim_prose(text: str, max_sents: int = 4) -> str:
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if len(s.strip()) > 15]
    return " ".join(sents[:max_sents]) if sents else text.strip()


def _opening_summary(by_dom: dict[str, DomainVerdict], pc: dict) -> str:
    bits: list[str] = []
    lagna = pc.get("meta", {}).get("lagna_sign", "")
    if lagna:
        bits.append(f"You were born with {lagna} rising.")
    for dom in ("personality", "career", "future"):
        v = by_dom.get(dom)
        if v and v.synthesis:
            bits.append(_trim_prose(v.synthesis, 1))
    return " ".join(bits[:3]) if bits else "This reading weaves together the major life themes visible in your chart."


def render_lanes_confluence(
    pc: dict,
    verdicts: list[DomainVerdict],
    lane_meta: dict,
    lanes_present: int,
) -> str:
    meta = pc["meta"]
    nm = _e(meta["client"])
    today = date.today()
    vim = pc.get("vimshottari", {})
    md = vim.get("current_md", {}).get("md_lord", "")
    ad = next((a for a in vim.get("current_md_antardashas", []) if a.get("status") == "current"), {})
    ad_rng = ""
    if ad:
        try:
            s = datetime.strptime(ad["start"][:10], "%Y-%m-%d").date().strftime("%b %Y")
            e = datetime.strptime(ad["end"][:10], "%Y-%m-%d").date().strftime("%b %Y")
            ad_rng = f"{s} - {e}"
        except ValueError:
            pass

    by_dom = {v.domain: v for v in verdicts}
    opening = _opening_summary(by_dom, pc)
    lctx = build_longevity_context(pc)

    domain_cards = ""
    for dom in DOMAINS:
        if dom == "health":
            continue
        v = by_dom.get(dom)
        if not v or not (v.synthesis or v.headline):
            continue
        body = _trim_prose(v.synthesis or v.headline, 4)
        when = v.timing or (ad_rng if dom == "future" else "")
        split = ""
        if v.split_note:
            split = f'<p class="fine">{_e(v.split_note)}</p>'
        domain_cards += f"""
<div class="card {_card_tone(v)}">
  <div class="when">{_e(when) if when else DOMAIN_TITLE[dom]}</div>
  <h3>{DOMAIN_TITLE[dom]}</h3>
  <p class="body">{_e(body)}</p>
  {_confidence_pill(v)}
  {split}
</div>"""

    health_block = health_section_html(
        pc, lctx,
        cluster_text=_trim_prose(by_dom["health"].synthesis, 2) if by_dom.get("health") else "",
    )

    firm = sum(1 for v in verdicts if v.meets_threshold)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Life Reading - {nm}</title>
<style>{client_css()}</style></head><body>
<div class="wrap">
<div class="hero">
  <h1>Your Life Reading</h1>
  <div class="tag">Integrated view from {lanes_present} specialist methods  -  {firm} domains with strong agreement</div>
  <div class="meta">
    <span>{nm}</span>
    <span>DOB: {_e(meta.get('dob',''))}</span>
    <span>{_e(meta.get('lagna_sign',''))} rising</span>
    <span>Current chapter: {_e(md)}-{_e(ad.get('ad_lord',''))} ({ad_rng})</span>
    <span>{today.strftime('%d %B %Y').lstrip('0')}</span>
  </div>
</div>

<div class="note"><strong>How to read this.</strong> Each card below is a life domain - not a planet list. Coloured borders show tone (green supportive, amber mixed, red caution). Educational reflection only.</div>

<div class="card blue">
  <h3>Overview</h3>
  <p class="body">{_e(opening)}</p>
</div>

{domain_cards}

{health_block}

{transition_calendar_html(pc)}

{traffic_light_html(pc, lctx)}

{remedies_html(pc, lctx)}

<div class="footer">
  <p>Chart-based life reading  -  {lanes_present} lanes  -  Longevity uses Marc Boney book OCR (maraka + sensitive degrees).</p>
  <p>Confirm timelines against your lived dates when possible.</p>
</div>
</div></body></html>"""
