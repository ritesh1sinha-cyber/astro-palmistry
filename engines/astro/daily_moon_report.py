#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTML report for personal daily prediction (Vedic confluence + Moonology moon lane)."""
from __future__ import annotations

import html
from datetime import date
from pathlib import Path
from typing import Any


def _ord(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    return f"{n}" + ("th" if 10 <= n % 100 <= 20
                     else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))

try:
    from client_report_html import client_css, floating_toc_html, finalize_report_html
except ImportError:
    client_css = lambda: ""  # noqa: E731
    floating_toc_html = lambda: ""  # noqa: E731
    finalize_report_html = lambda h, client_name="": h  # noqa: E731

from daily_reading_plain import plain_jaimini_karaka_bullets


def _e(s: Any) -> str:
    return html.escape(str(s))


def _tone_badge(tone: str) -> str:
    cls = {
        "bright": "light-green",
        "mixed-positive": "light-green",
        "steady": "light-amber",
        "mixed-caution": "light-amber",
        "sensitive": "light-red",
    }.get(tone, "light-amber")
    label = tone.replace("-", " ").title()
    return f'<span class="light {cls}">{_e(label)}</span>'


def _personal_li(item: dict) -> str:
    """Client-facing do/don't line without book citation clutter."""
    if isinstance(item, str):
        return f"<li>{_e(item)}</li>"
    return f"<li>{_e(item.get('text', ''))}</li>"


def _rule_li(item: dict) -> str:
    if isinstance(item, str):
        return f"<li>{_e(item)}</li>"
    src = item.get("source", "")
    tag = f' <span class="fine" style="display:block;margin-top:2px">[{_e(src)}]</span>' if src else ""
    return f"<li>{_e(item.get('text', ''))}{tag}</li>"


def _lunation_timing_card(mo: dict) -> str:
    """Structured start/end times for New Moon or Full Moon rituals."""
    lt = mo.get("lunation_timing") or {}
    kind = lt.get("kind") or mo.get("lunation_applicable", "")
    if not lt or not kind:
        return ""
    place = lt.get("place", "")
    tz = lt.get("timezone_label", "")
    loc = f"{place} ({tz})" if place else tz
    if kind == "new_moon":
        return f"""
  <div class="card" style="border:2px solid #e94560;margin-bottom:16px">
    <h3>New Moon timing - when to perform the ritual</h3>
    <p class="fine">Local times for <strong>{_e(loc)}</strong> (birth place). Swiss Ephemeris sidereal conjunction.</p>
    <table class="body" style="width:100%;border-collapse:collapse;margin-top:10px">
      <tr><td style="padding:6px 8px;border-bottom:1px solid #333"><strong>Exact New Moon</strong></td>
          <td style="padding:6px 8px;border-bottom:1px solid #333">{_e(lt.get('exact_display', ''))}</td></tr>
      <tr><td style="padding:6px 8px;border-bottom:1px solid #333"><strong>Best window starts</strong></td>
          <td style="padding:6px 8px;border-bottom:1px solid #333">{_e(lt.get('peak_window_start_display', ''))}</td></tr>
      <tr><td style="padding:6px 8px;border-bottom:1px solid #333"><strong>Best window ends</strong> <span class="fine">(+8 hrs)</span></td>
          <td style="padding:6px 8px;border-bottom:1px solid #333">{_e(lt.get('peak_window_end_display', ''))}</td></tr>
      <tr><td style="padding:6px 8px"><strong>Extended window ends</strong> <span class="fine">(+3 days)</span></td>
          <td style="padding:6px 8px">{_e(lt.get('extended_window_end_display', ''))}</td></tr>
    </table>
    <p class="fine" style="margin-top:10px">{_e(lt.get('note_peak', ''))}</p>
    <p class="fine">{_e(lt.get('note_extended', ''))}</p>
  </div>"""
    if kind == "full_moon":
        return f"""
  <div class="card" style="border:2px solid #c9b1ff;margin-bottom:16px">
    <h3>Full Moon timing - when to perform the ceremony</h3>
    <p class="fine">Local times for <strong>{_e(loc)}</strong> (birth place). Swiss Ephemeris sidereal opposition.</p>
    <table class="body" style="width:100%;border-collapse:collapse;margin-top:10px">
      <tr><td style="padding:6px 8px;border-bottom:1px solid #333"><strong>Exact Full Moon</strong></td>
          <td style="padding:6px 8px;border-bottom:1px solid #333">{_e(lt.get('exact_display', ''))}</td></tr>
      <tr><td style="padding:6px 8px;border-bottom:1px solid #333"><strong>Primary ceremony starts</strong></td>
          <td style="padding:6px 8px;border-bottom:1px solid #333">{_e(lt.get('ceremony_start_display', ''))}</td></tr>
      <tr><td style="padding:6px 8px;border-bottom:1px solid #333"><strong>Primary ceremony ends</strong></td>
          <td style="padding:6px 8px;border-bottom:1px solid #333">{_e(lt.get('ceremony_end_display', ''))}</td></tr>
      <tr><td style="padding:6px 8px;border-bottom:1px solid #333"><strong>Also good - night before starts</strong></td>
          <td style="padding:6px 8px;border-bottom:1px solid #333">{_e(lt.get('alt_ceremony_start_display', ''))}</td></tr>
      <tr><td style="padding:6px 8px"><strong>Also good - night before ends</strong></td>
          <td style="padding:6px 8px">{_e(lt.get('alt_ceremony_end_display', ''))}</td></tr>
    </table>
    <p class="fine" style="margin-top:10px">{_e(lt.get('note_ceremony', ''))}</p>
    <p class="fine">{_e(lt.get('note_alt', ''))}</p>
  </div>"""
    return ""


def _plain_li(text: str) -> str:
    return f"<li>{_e(text)}</li>"


def _jaimini_karaka_section(vc: dict[str, Any]) -> str:
    jc = vc.get("jaimini_confluence") or {}
    if not jc.get("available"):
        return ""
    bullets = plain_jaimini_karaka_bullets(jc)
    if not bullets:
        return ""
    items = ""
    for b in bullets:
        if b.get("detail"):
            items += f"<li><strong>{_e(b['head'])}</strong> - {_e(b['detail'])}</li>"
        else:
            items += f"<li><strong>{_e(b['head'])}</strong></li>"
    work = vc.get("work_hint", "")
    personal = vc.get("personal_hint", "")
    extra = ""
    if work:
        extra += f"<p class='body' style='margin-top:10px'><strong>Work today:</strong> {_e(work)}</p>"
    if personal:
        extra += f"<p class='body'><strong>Personal life:</strong> {_e(personal)}</p>"
    return f"""
  <div class="card" style="margin-bottom:16px;border-left:4px solid #7e57c2">
    <h3>What your parallel timing says about today</h3>
    <p class="fine">A second Vedic clock (sign-based) - how career, love, and creativity feel right now.</p>
    <ul class="body">{items}</ul>
    {extra}
  </div>"""


def _verdict_badge(verdict: str) -> str:
    cls = {"good": "light-green", "mixed": "light-amber", "avoid": "light-red"}.get(verdict, "light-amber")
    return f'<span class="light {cls}">{_e(verdict.title())}</span>'


def _muhurat_section(data: dict[str, Any]) -> str:
    mu = data.get("muhurat") or {}
    if not mu.get("available"):
        err = mu.get("error", "Muhurat unavailable")
        return f"""
  <h2 class="section-h">Muhurat today</h2>
  <div class="card"><p class="fine">{_e(err)}</p></div>"""

    win = mu.get("windows", {})
    good_rows = "".join(
        f"<tr><td style='padding:6px 8px;border-bottom:1px solid #333'>{_e(s['label'])}</td>"
        f"<td style='padding:6px 8px;border-bottom:1px solid #333'>{_e(s['start'])} - {_e(s['end'])}</td>"
        f"<td style='padding:6px 8px;border-bottom:1px solid #333'>{_e(s['plain'])}</td></tr>"
        for s in win.get("good_choghadiya", [])
    )
    avoid_rows = "".join(
        f"<li>{_e(s['label'])} ({_e(s['start'])}-{_e(s['end'])}): {_e(s['plain'])}</li>"
        for s in win.get("avoid_choghadiya", [])
    )
    durm = "".join(
        f"<li>{_e(d.get('start', ''))} - {_e(d.get('end', ''))}</li>"
        for d in win.get("durmuhurta", [])
    )
    tri_kaal = "".join(
        f"<li><strong>{_e(s.get('label', ''))}</strong> {_e(s.get('start', ''))} - {_e(s.get('end', ''))}: {_e(s.get('plain', ''))}</li>"
        for s in win.get("tri_kaal", [])
    )
    ab = win.get("abhijit", {})

    def _event_rows(events: list) -> str:
        return "".join(
            f"<tr><td style='padding:6px 8px;border-bottom:1px solid #333'>{_e(e['label'])}</td>"
            f"<td style='padding:6px 8px;border-bottom:1px solid #333'>{_verdict_badge(e['verdict'])}</td>"
            f"<td style='padding:6px 8px;border-bottom:1px solid #333'>{_e(e['summary'])}</td></tr>"
            for e in events
        )

    events = mu.get("events", [])
    chart_bits = ""
    for e in events:
        if e.get("chart_notes"):
            chart_bits += f"<p class='fine' style='margin:4px 0'><strong>{_e(e['label'])}:</strong> {_e(e['chart_notes'][0][:220])}</p>"

    return f"""
  <h2 class="section-h">Muhurat today</h2>
  <div class="note">{_e(mu.get('explanation', ''))}</div>
  <div class="card" style="margin-bottom:16px;border-left:4px solid #2e7d32">
    <h3>Day muhurat - best hours</h3>
    <p class="body">{_e(mu.get('intro', ''))}</p>
    <p class="body">{_e(mu.get('day_summary', ''))}</p>
    <p class="when">Abhijit: <strong>{_e(ab.get('start', ''))} - {_e(ab.get('end', ''))}</strong></p>
    <p class="fine">{_e(ab.get('plain', ''))}</p>
    <table class="body" style="width:100%;border-collapse:collapse;margin-top:10px">
      <tr><th style="text-align:left;padding:6px 8px;border-bottom:1px solid #444">Choghadiya</th>
          <th style="text-align:left;padding:6px 8px;border-bottom:1px solid #444">Time</th>
          <th style="text-align:left;padding:6px 8px;border-bottom:1px solid #444">Use for</th></tr>
      {good_rows}
    </table>
    <p class="fine" style="margin-top:10px"><strong>Avoid choghadiya:</strong></p>
    <ul class="body">{avoid_rows or '<li>None flagged strongly</li>'}</ul>
    <p class="fine"><strong>Durmuhurta (skip):</strong></p>
    <ul class="body">{durm or '<li>See panchang</li>'}</ul>
    <p class="fine"><strong>Tri-kaal (avoid):</strong> Rahu Kaal, Yamagandam, Gulikai</p>
    <ul class="body">{tri_kaal or '<li>See panchang</li>'}</ul>
    <p class="fine">{_e(win.get('tri_kaal_plain', ''))}</p>
    <p class="fine">{_e(win.get('hora_note', ''))}</p>
  </div>
  <div class="card" style="margin-bottom:16px;border-left:4px solid #1565c0">
    <h3>Event muhurat - is today good for…?</h3>
    <p class="fine">General panchang score at your birth place. Chart-specific notes appear where your natal chart matters (e.g. mundan odd-year, marriage needs both charts).</p>
    <table class="body" style="width:100%;border-collapse:collapse;margin-top:8px">
      <tr><th style="text-align:left;padding:6px 8px;border-bottom:1px solid #444">Event</th>
          <th style="text-align:left;padding:6px 8px;border-bottom:1px solid #444">Today</th>
          <th style="text-align:left;padding:6px 8px;border-bottom:1px solid #444">Reading</th></tr>
      {_event_rows(events)}
    </table>
    <div style="margin-top:12px">{chart_bits}</div>
  </div>"""


_TONE_WORDS = {
    "bright": "a genuinely good day — the wind is at your back",
    "mixed-positive": "a mostly favourable day, with a couple of small bumps to handle",
    "steady": "a steady, workable day — nothing dramatic pulling either way",
    "mixed-caution": "a day to step a little carefully — there's some friction in the air",
    "sensitive": "a tender, sensitive day — be gentle with yourself and with the people around you",
}


def _first_text(items: list[Any]) -> str:
    for x in items or []:
        t = x.get("text", "") if isinstance(x, dict) else x
        if t:
            return str(t)
    return ""


def _lc_first(text: str) -> str:
    return (text[:1].lower() + text[1:]) if text else text


def _humanize_daily_opening(text: str) -> str:
    """Drop technical clauses (Tarabala names, strengths, varga jargon) from the lead opening."""
    import re
    drop = ("strength:", "tarabala", "chandrabal", "ashtakavarga", " bav", " sav",
            "nakshatra", "pada", "vimshottari", "jaimini")
    parts = re.split(r"(?<=[.!?])\s+", text or "")
    kept = [p for p in parts if p and not any(d in p.lower() for d in drop)]
    return " ".join(kept).strip()


def _today_confluence_section(data: dict[str, Any]) -> str:
    """
    One warm, human lead that pulls every lane together: how the day feels,
    where life is taking you, whether the timing systems agree, your single
    best move and caution, and your golden hours. The lane-by-lane detail
    follows below.
    """
    vc = data.get("vedic_confluence") or {}
    mo = data.get("moonology") or {}
    dasha = data.get("dasha", {})
    mu = (data.get("muhurat") or {}).get("windows", {})

    tone = data.get("tone", "steady")
    tone_words = _TONE_WORDS.get(tone, "a workable day")
    opening = _humanize_daily_opening(data.get("opening", ""))

    # Mood: today's Moon in plain words.
    moon_sign = mo.get("moon_sign", "")
    moon_mood = mo.get("sign_summary", "") or mo.get("at_a_glance", "")
    mood_line = ""
    if moon_sign and moon_mood:
        mood_line = f"<p class='body'><strong>The feel of the day:</strong> it's {tone_words}. With the Moon in {_e(moon_sign)}, {_e(_lc_first(moon_mood.rstrip('. ')))}.</p>"
    else:
        mood_line = f"<p class='body'><strong>The feel of the day:</strong> it's {tone_words}.</p>"

    # Life chapter in plain language.
    chapter = dasha.get("stack", "")
    chapter_line = ""
    paras = vc.get("reading_paragraphs") or []
    plain_chapter = paras[0] if paras else (vc.get("verdict_plain") or vc.get("verdict", ""))
    if plain_chapter:
        chapter_line = f"<p class='body'><strong>Where life is taking you:</strong> {_e(plain_chapter.rstrip('. '))}.</p>"

    # Confluence: do the two timing clocks agree?
    dual = (vc.get("dual_agreement") or "").lower()
    agree_line = ""
    if "concur" in dual or "agree" in dual:
        agree_line = ("<p class='body'><strong>Both your inner clocks agree today.</strong> "
                      "Your life-timing and the parallel sign-based timing are pointing at the very "
                      "same theme — when that happens, trust the message and act on it.</p>")

    # One move, one caution — straight from your playbook.
    do_txt = _first_text(data.get("dos", []))
    dont_txt = _first_text(data.get("donts", []))
    move_line = ""
    if do_txt or dont_txt:
        move_line = "<p class='body'>"
        if do_txt:
            move_line += f"<strong>If you do one thing:</strong> {_e(do_txt.rstrip('. '))}. "
        if dont_txt:
            move_line += f"<strong>And steer clear of:</strong> {_e(dont_txt.rstrip('. '))}."
        move_line += "</p>"

    # Golden hours from the muhurat lane.
    ab = mu.get("abhijit", {})
    good = mu.get("good_choghadiya", [])
    hours_line = ""
    bits = []
    if ab.get("start") and ab.get("end"):
        bits.append(f"your strongest window is Abhijit, <strong>{_e(ab['start'])}–{_e(ab['end'])}</strong>")
    if good:
        g = good[0]
        bits.append(f"and {_e(g.get('start',''))}–{_e(g.get('end',''))} is good for {_e((g.get('plain','') or 'most work').rstrip('. ').lower())}")
    if bits:
        hours_line = f"<p class='body'><strong>Your golden hours:</strong> {'; '.join(bits)}.</p>"

    open_line = f"<p class='body' style='font-size:1.04rem'>{_e(opening)}</p>" if opening else ""

    return f"""
  <h2 class="section-h">Today, in one read</h2>
  <div class="card" style="border-left:4px solid var(--accent);margin-bottom:18px">
    {open_line}
    {mood_line}
    {chapter_line}
    {agree_line}
    {move_line}
    {hours_line}
    <p class="fine" style="margin-top:10px">Below, I break this down lane by lane — your life chapter, today's Moon,
    the day's good and difficult hours, and your full do/don't list. They all feed the read above.</p>
  </div>"""


def _vedic_confluence_section(data: dict[str, Any]) -> str:
    vc = data.get("vedic_confluence") or {}
    if not vc:
        return ""
    lanes = vc.get("lanes", [])
    lane_rows = "".join(
        f"<tr><td style='padding:6px 8px;border-bottom:1px solid #333'>{_e(l.get('lane', ''))}</td>"
        f"<td style='padding:6px 8px;border-bottom:1px solid #333'>{_e(l.get('signal', ''))}</td>"
        f"<td style='padding:6px 8px;border-bottom:1px solid #333'>{_e(l.get('weight', ''))}</td></tr>"
        for l in lanes
    )
    dasha = data.get("dasha", {})
    jai = data.get("jaimini", {}) or vc.get("jaimini", {})
    pd_end = dasha.get("pd_end", "")
    pd_line = ""
    if dasha.get("pd"):
        pd_line = f"<p class='when'>Today's slice: <strong>{_e(dasha.get('pd', ''))}</strong>"
        if pd_end:
            pd_line += f" until {_e(pd_end[:10])}"
        pd_line += "</p>"
    jai_line = ""
    if jai.get("stack"):
        jai_line = f"<p class='when'>Parallel timing: <strong>{_e(jai.get('stack', ''))}</strong>"
        if jai.get("pd_end"):
            jai_line += f" (sharp slice until {_e(jai['pd_end'][:10])})"
        jai_line += "</p>"
    dual = vc.get("dual_agreement", "")
    dual_block = ""
    if dual and "concur" in dual.lower():
        dual_block = "<p class='fine'>Both major timing systems point at the same life theme today.</p>"
    paras = vc.get("reading_paragraphs") or []
    if not paras and vc.get("reading"):
        paras = [p.strip() for p in vc["reading"].split("\n\n") if p.strip()]
    body_html = "".join(f"<p class='body' style='margin:0 0 12px'>{_e(p)}</p>" for p in paras)
    verdict_plain = vc.get("verdict_plain") or vc.get("verdict", "")
    tech = vc.get("reading_technical", "")
    tech_block = ""
    if tech:
        tech_block = f"""
    <details class="fine" style="margin-top:12px">
      <summary style="cursor:pointer;color:var(--muted)">Technical detail (for reference)</summary>
      <p class="fine" style="margin-top:8px">{_e(tech[:2000])}</p>
    </details>"""
    return f"""
  <h2 class="section-h">Vedic confluence today</h2>
  <div class="note">Your day read through life timing, today's Moon, and parallel sign-based timing - in plain language.</div>
  <div class="card" style="margin-bottom:16px;border-left:4px solid var(--accent)">
    <h3>Your Vedic reading for today</h3>
    <p class="when">Life chapter: {_e(dasha.get('stack', ''))}</p>
    {pd_line}
    {jai_line}
    {body_html}
    {dual_block}
    <p class="fine" style="margin-top:8px"><strong>Bottom line:</strong> {_e(verdict_plain)}</p>
    {tech_block}
  </div>
  {_jaimini_karaka_section(vc)}
  <div class="card">
    <h3>How the signals stack up</h3>
    <table class="body" style="width:100%;border-collapse:collapse">
      <tr><th style="text-align:left;padding:6px 8px;border-bottom:1px solid #444">Lane</th>
          <th style="text-align:left;padding:6px 8px;border-bottom:1px solid #444">Signal</th>
          <th style="text-align:left;padding:6px 8px;border-bottom:1px solid #444">Weight</th></tr>
      {lane_rows}
    </table>
  </div>"""


def _moonology_section(mo: dict) -> str:
    if not mo:
        return ""
    phase_dos = "".join(_plain_li(x.get("text", x) if isinstance(x, dict) else x) for x in mo.get("phase_dos", []))
    phase_donts = "".join(_plain_li(x.get("text", x) if isinstance(x, dict) else x) for x in mo.get("phase_donts", []))
    ritual = "".join(f"<li>{_e(s)}</li>" for s in mo.get("ritual_steps", []))
    lunation_focus = "".join(f"<li>{_e(x)}</li>" for x in mo.get("lunation_focus", []))
    things_to_do = "".join(f"<li>{_e(x)}</li>" for x in mo.get("things_to_do", []))
    affirmations = "".join(f"<li>{_e(a)}</li>" for a in mo.get("house_affirmations", []))
    src = mo.get("source", "rules44")
    golden = mo.get("golden_tip", {})
    personal = mo.get("personal_lunation", "")
    love_note = mo.get("love_zone_note", "")
    lunation_kind = mo.get("lunation_applicable", "")
    timing_card = _lunation_timing_card(mo)
    banner = ""
    lt = mo.get("lunation_timing") or {}
    if lunation_kind == "new_moon":
        exact_line = ""
        if lt.get("exact_display"):
            exact_line = f'<p class="body" style="margin:8px 0 0"><strong>Exact New Moon:</strong> {_e(lt["exact_display"])}</p>'
        banner = f"""
  <div class="card" style="background:linear-gradient(135deg,#1a1a2e,#16213e);border:2px solid #e94560;margin-bottom:16px">
    <h3 style="color:#e94560;margin:0 0 8px">NEW MOON TODAY - wishing ceremony applies</h3>
    <p class="body" style="margin:0">Perform the full New Moon ritual below. Best within 8 hours of exact New Moon; up to 3 days is fine.</p>
    {exact_line}
  </div>"""
    elif lunation_kind == "full_moon":
        exact_line = ""
        if lt.get("exact_display"):
            exact_line = f'<p class="body" style="margin:8px 0 0"><strong>Exact Full Moon:</strong> {_e(lt["exact_display"])}</p>'
        banner = f"""
  <div class="card" style="background:linear-gradient(135deg,#1a1a2e,#2d1b4e);border:2px solid #c9b1ff;margin-bottom:16px">
    <h3 style="color:#c9b1ff;margin:0 0 8px">FULL MOON TONIGHT - forgiveness &amp; gratitude ceremony</h3>
    <p class="body" style="margin:0">Perform the Full Moon ritual tonight (night before is also powerful).</p>
    {exact_line}
  </div>"""
    window_note = mo.get("lunation_window_note", "")
    lunation_block = ""
    if mo.get("lunation_title"):
        lunation_block = f"""
  <div class="card" style="border-left:4px solid var(--accent)">
    <h3>{_e(mo.get('lunation_title', ''))}</h3>"""
        if window_note:
            lunation_block += f'<p class="when">{_e(window_note)}</p>'
        if mo.get("lunation_energy"):
            lunation_block += f'<p class="when">Energy: {_e(mo["lunation_energy"])}</p>'
        if mo.get("lunation_message"):
            lunation_block += f'<p class="body"><strong>Message:</strong> {_e(mo["lunation_message"])}</p>'
        if mo.get("lunation_balance"):
            lunation_block += f'<p class="fine"><strong>Find balance:</strong> {_e(mo["lunation_balance"])}</p>'
        if things_to_do:
            lunation_block += f'<p class="body"><strong>Things to do today:</strong></p><ul class="body">{things_to_do}</ul>'
        elif lunation_focus:
            lunation_block += f'<p class="body"><strong>Focus themes (Ch.4):</strong></p><ul class="body">{lunation_focus}</ul>'
        if mo.get("reflection_question"):
            lunation_block += (
                f'<p class="body"><strong>Reflect:</strong> {_e(mo["reflection_question"])}</p>'
            )
        if golden.get("text"):
            lunation_block += f'<p class="fine"><strong>Golden rule:</strong> {_e(golden["text"])}</p>'
        lunation_block += "</div>"
    ritual_title = "New Moon wishing ceremony (full ritual)" if lunation_kind == "new_moon" else (
        "Full Moon forgiveness & gratitude ceremony" if lunation_kind == "full_moon" else "Today's ritual (phase-matched)"
    )
    ritual_block = ""
    if ritual:
        ritual_block = f"""
  <div class="card remedy">
    <h3>{_e(ritual_title)}</h3>
    <ol class="body">{ritual}</ol>
  </div>"""
    cosmic_block = ""
    if mo.get("house_oil") or mo.get("house_archangel") or mo.get("house_goddess"):
        cosmic_block = f"""
  <div class="card" style="border-left:4px solid #7ec8e3">
    <h3>Cosmic helpers - {_e(mo.get('house_zone', ''))} ({_ord(mo.get('house_from_asc', ''))} House)</h3>"""
        if mo.get("house_oil"):
            cosmic_block += (
                f'<p class="body"><strong>Essential oil:</strong> {_e(mo["house_oil"])} - '
                f'{_e(mo.get("house_oil_use", ""))}</p>'
            )
        if mo.get("house_archangel"):
            cosmic_block += (
                f'<p class="body"><strong>Archangel:</strong> {_e(mo["house_archangel"])} - '
                f'{_e(mo.get("house_archangel_note", ""))}</p>'
            )
        if mo.get("house_goddess"):
            cosmic_block += (
                f'<p class="body"><strong>Goddess:</strong> {_e(mo["house_goddess"])} - '
                f'{_e(mo.get("house_goddess_note", ""))}</p>'
            )
        if mo.get("house_ritual"):
            cosmic_block += f'<p class="body"><strong>House ritual:</strong> {_e(mo["house_ritual"])}</p>'
        if affirmations:
            cosmic_block += f'<p class="body"><strong>Affirmations:</strong></p><ul class="body">{affirmations}</ul>'
        cosmic_block += f'<p class="fine">Cosmic helpers for this house zone (Boland Ch.5).</p></div>'
    reading_block = ""
    if mo.get("daily_reading"):
        reading_block = f"""
  <div class="card" style="margin-bottom:16px;border-left:4px solid var(--accent)">
    <h3>Your Moonology reading for today</h3>
    <p class="fine" style="margin-bottom:10px">{_e(mo.get('at_a_glance', ''))}</p>
    <p class="body">{_e(mo.get('daily_reading', ''))}</p>
  </div>"""
    sign_dont = mo.get("sign_dont", "")
    sign_avoid = sign_dont.lower() if sign_dont else "pushing against the mood"
    return f"""
  <h2 class="section-h">Moonology (moon lane)</h2>
  <div class="note">Sidereal Moon sign matches the Vedic block. House counts from your natal Ascendant. Plain-English read from Boland Moonology (rules44).</div>
  {reading_block}
  {banner}
  {timing_card}
  {f'<p class="fine" style="margin-bottom:14px">{_e(mo.get("moon_governs", ""))}</p>' if mo.get("moon_governs") else ''}
  {f'<div class="note" style="margin-bottom:14px">{_e(personal)}</div>' if personal else ''}
  {f'<div class="note" style="margin-bottom:14px">{_e(love_note)}</div>' if love_note else ''}
  {lunation_block}
  {cosmic_block}
  <div class="daily-grid">
    <div class="card">
      <h3>Emotional tone - Moon in {_e(mo.get('moon_sign', ''))}</h3>
      <p class="when">{_e(mo.get('element', ''))} element</p>
      <p class="body">{_e(mo.get('sign_summary', ''))}</p>
      <p class="body">{_e(mo.get('sign_do', ''))} Avoid {_e(sign_avoid)}.</p>
    </div>
    <div class="card">
      <h3>Cycle - {_e(mo.get('phase', ''))}</h3>
      {f'<p class="when">{_e(mo.get("phase_note", ""))}</p>' if mo.get("phase_note") else ''}
      <p class="body">{_e(mo.get('phase_summary', ''))}</p>
      <ul class="body">{phase_dos}</ul>
      <ul class="body">{phase_donts}</ul>
    </div>
  </div>
  <div class="card">
    <h3>Your {_ord(mo.get('house_from_asc', ''))} House today - {_e(mo.get('house_zone', ''))}</h3>
    <p class="when">{_e(mo.get('natal_asc_sign', ''))} rising | {_e(mo.get('house_focus', ''))}</p>
    <p class="body">{_e(mo.get('house_summary', ''))}</p>
    <p class="body">{_e(mo.get('house_do', ''))}</p>
    <p class="fine">If you want a simple ritual: {_e(mo.get('house_remedy', ''))}</p>
  </div>
  {ritual_block}"""


def generate_daily_prediction_html(data: dict[str, Any]) -> str:
    dos = "".join(_personal_li(x) for x in data.get("dos", []))
    donts = "".join(_personal_li(x) for x in data.get("donts", []))
    dos_intro = data.get("dos_donts_intro", "")
    slow = "".join(f"<li>{_e(x)}</li>" for x in data.get("slow_planet_notes", []))
    ln = data.get("lucky_numbers", {})
    anchors = ln.get("anchors", [])
    num_lines = "".join(
        f"<li><strong>{_e(a.get('value', ''))}</strong> - {_e(a.get('reason', ''))} "
        f"<span class='fine'>[{_e(a.get('source', ''))}]</span></li>"
        for a in anchors
    ) or f"<li><strong>{_e(ln.get('primary', ''))}, {_e(ln.get('secondary', ''))}, {_e(ln.get('tertiary', ''))}</strong></li>"
    colors = "".join(
        f"<li><strong>{_e(c['name'])}</strong> - {_e(c.get('why', ''))} "
        f"<span class='fine'>[{_e(c.get('source', ''))}]</span></li>"
        for c in data.get("lucky_colors", [])
    )
    avoid = ", ".join(str(x) for x in ln.get("avoid", [18]))
    mt = data.get("moon_transit", {})
    av = data.get("ashtakavarga", {}).get("moon", {})
    tara = data.get("tarabala", {})
    chandra = data.get("chandrabal", {})
    nm = data.get("natal_moon", {})

    dasha = data.get("dasha", {})
    jai = data.get("jaimini", {})

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Daily Prediction - {_e(data.get('client', ''))} - {_e(data.get('date', ''))}</title>
<style>{client_css()}
.daily-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
@media(max-width:640px){{ .daily-grid {{ grid-template-columns:1fr; }} }}
</style>
</head><body><div class="wrap">
  <div class="hero">
    <h1>Daily Prediction</h1>
    <div class="tag">{_e(data.get('client', ''))} | {_e(data.get('weekday', ''))} {_e(data.get('date', ''))}</div>
    <div class="meta">
      <span>Weekday lord: {_e(data.get('weekday_lord', ''))}</span>
      <span>Natal Moon: {_e(nm.get('sign', ''))} / {_e(nm.get('nakshatra', ''))}</span>
      <span>Vimshottari: {_e(dasha.get('stack', ''))}</span>
      <span>Jaimini: {_e(jai.get('stack', ''))}</span>
    </div>
    <p style="margin:14px 0 0;opacity:.92;font-size:1.02rem">{_e(data.get('opening', ''))}</p>
    <p style="margin:10px 0 0">{_tone_badge(data.get('tone', 'steady'))}</p>
  </div>

  {_today_confluence_section(data)}

  <div class="note">Everything below is the detailed breakdown behind that read — in plain language, lane by lane.</div>

  {_vedic_confluence_section(data)}
  {_muhurat_section(data)}

  <h2 class="section-h">Transit detail (from your Moon)</h2>
  <div class="daily-grid">
    <div class="card">
      <h3>Moon - emotional weather</h3>
      <p class="when">{_e(mt.get('sign', ''))} | {_e(mt.get('nakshatra', ''))} pada {_e(mt.get('pada', ''))} | {_ord(mt.get('house_from_moon', ''))} from birth Moon</p>
      <p class="body">Tarabala: <strong>{_e(tara.get('name', ''))}</strong> ({_e(tara.get('tone', ''))}). {_e(tara.get('note', ''))}</p>
      <p class="body">Chandrabal: <strong>{_e(chandra.get('name', ''))}</strong> ({_e(chandra.get('tone', ''))}).</p>
      <p class="fine">{_e(av.get('sav_line', ''))}</p>
      <p class="fine">{_e(av.get('bav_line', ''))}</p>
    </div>
    <div class="card">
      <h3>Sun and Mercury - day tone</h3>
      <p class="body">{_e(data.get('sun_narrative', ''))}</p>
      <p class="body">{_e(data.get('mercury_narrative', ''))}</p>
    </div>
  </div>

  <h2 class="section-h">Slow-planet confluence</h2>
  <div class="card">
    <ul class="body">{slow or '<li>No sharp slow-graha contacts today.</li>'}</ul>
    <p class="fine">{_e(data.get('dasha', {}).get('note', ''))}</p>
  </div>

  {_moonology_section(data.get('moonology', {}))}

  <h2 class="section-h">Lucky anchors (rule-cited)</h2>
  <div class="daily-grid">
    <div class="card">
      <h3>Numbers</h3>
      <ul class="body">{num_lines}</ul>
      <p class="fine">{_e(ln.get('series_note', ''))}</p>
      <p class="fine">{_e(ln.get('avoid_note', 'Avoid 18 for relationship stakes'))}: {_e(avoid)}</p>
    </div>
    <div class="card">
      <h3>Colours</h3>
      <ul class="body">{colors}</ul>
    </div>
  </div>

  <h2 class="section-h">Your personal playbook today</h2>
  {f'<p class="note" style="margin-bottom:14px">{_e(dos_intro)}</p>' if dos_intro else ''}
  <div class="daily-grid">
    <div class="card" style="border-left:4px solid var(--green)">
      <h3>Do</h3>
      <ul class="body">{dos}</ul>
    </div>
    <div class="card" style="border-left:4px solid var(--red)">
      <h3>Don't</h3>
      <ul class="body">{donts}</ul>
    </div>
  </div>
  <p class="fine" style="margin-top:8px">Suggestions weave your natal chart, Vimshottari MD/AD/PD, today&apos;s Moon transit, Tarabala, Chandrabal, gochar, and Ashtakavarga.</p>

  <div class="card" style="font-size:.84rem;color:var(--muted)">
    <strong>Method:</strong> {' | '.join(_e(s) for s in data.get('sources', []))}
  </div>
</div>{floating_toc_html()}</body></html>"""


def write_daily_prediction_report(
    data: dict[str, Any],
    reports_dir: Path,
    slug: str,
) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    d = data.get("date", date.today().isoformat()).replace("-", "")
    path = reports_dir / f"Daily_Prediction_{slug}_{d}.html"
    path.write_text(finalize_report_html(generate_daily_prediction_html(data)), encoding="utf-8")
    return path


generate_daily_moon_html = generate_daily_prediction_html


def write_daily_moon_report(
    data: dict[str, Any],
    reports_dir: Path,
    slug: str,
) -> Path:
    return write_daily_prediction_report(data, reports_dir, slug)
