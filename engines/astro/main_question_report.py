#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic Main Question report  -  plain-English HTML from chart math + templates.

No LLM. Optional MiniLM domain cross-check via vedic_confluence_report.detect_focus_domain.
Supports dual-chart overlap (e.g. parent + child) for timing questions.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from astro_precompute import (
    house_from_lagna,
    house_sign,
    resolve_precompute,
    SIGN_LORDS,
)
from client_question_engine import (
    GATE_PCT,
    QuestionContext,
    answer_client_question,
    route_client_question,
)

try:
    from client_report_html import client_css, finalize_report_html
except ImportError:
    client_css = lambda: ""  # noqa: E731
    finalize_report_html = lambda h, client_name="": h  # noqa: E731


def _esc(s: Any) -> str:
    return html.escape(str(s))


def _parse_ymd(s: str) -> date:
    s = (s or "")[:10]
    return datetime.strptime(s, "%Y-%m-%d").date()


def _age_on(dob: str, on: date) -> int:
    d = _parse_ymd(dob)
    return on.year - d.year - ((on.month, on.day) < (d.month, d.day))


def _fmt_range(start: str, end: str) -> str:
    return f"{start[:10]} to {end[:10]}"


@dataclass
class SubjectInput:
    name: str
    dob: str
    birth_time: str
    latitude: float
    longitude: float
    timezone: float = 5.5
    place_name: str = ""
    gender: int = 0
    role: str = "client"
    extracted_path: str = ""
    precomputed_path: str = ""


# Lords / houses relevant per domain (natal timing scan)
DOMAIN_TIMING: dict[str, dict[str, Any]] = {
    "speech": {
        "lords": {"Mercury", "Jupiter", "Moon", "Mars", "Venus"},
        "houses": {2, 3, 10, 11},
        "karakas": ("Mercury", "Jupiter"),
    },
    "children": {
        "lords": {"Jupiter", "Venus", "Moon", "Mercury"},
        "houses": {2, 5, 10, 11},
        "karakas": ("Jupiter", "Venus"),
    },
    "health": {
        "lords": {"Sun", "Moon", "Mars", "Saturn", "Jupiter"},
        "houses": {1, 5, 6, 11},
        "karakas": ("Sun", "Moon"),
    },
    "marriage": {
        "lords": {"Venus", "Jupiter", "Moon", "Mercury"},
        "houses": {2, 7, 11},
        "karakas": ("Venus",),
    },
    "legal": {
        "lords": {"Mars", "Saturn", "Sun", "Mercury"},
        "houses": {6, 7, 11},
        "karakas": ("Mars", "Saturn"),
    },
    "career": {
        "lords": {"Sun", "Mercury", "Saturn", "Jupiter"},
        "houses": {2, 6, 10, 11},
        "karakas": ("Sun", "Mercury"),
    },
    "finance": {
        "lords": {"Jupiter", "Venus", "Mercury", "Moon"},
        "houses": {2, 11},
        "karakas": ("Jupiter", "Venus"),
    },
    "general": {
        "lords": set(),
        "houses": set(range(1, 13)),
        "karakas": (),
    },
}


def minilm_domain_hint(question: str) -> Optional[str]:
    """MiniLM + keyword domain cross-check (offline, no LLM prose)."""
    try:
        from vedic_confluence_report import SemanticEngine, detect_focus_domain
        eng = SemanticEngine()
        return detect_focus_domain(question, eng)
    except Exception:
        return None


def extract_chart_snapshot(pc: dict, ctx: QuestionContext, *, display_name: str = "") -> dict[str, Any]:
    lagna = pc.get("lagna", {}).get("sign") or pc.get("meta", {}).get("lagna_sign", "")
    planets = pc.get("planets", {})
    meta = pc.get("meta", {})
    h = ctx.primary_house
    h2l = SIGN_LORDS.get(house_sign(2, lagna), "")
    hpl = SIGN_LORDS.get(house_sign(h, lagna), "")
    rows = []
    seen_lords: set[str] = set()
    for label, lord in [(f"H{h} lord", hpl), ("H2 lord", h2l)]:
        if not lord or lord not in planets or lord in seen_lords:
            continue
        seen_lords.add(lord)
        p = planets[lord]
        rows.append({
            "label": label,
            "lord": lord,
            "house": p.get("house"),
            "sign": p.get("sign"),
            "dignity": p.get("dignity", ""),
        })
    for k in ("Mercury", "Jupiter", "Moon", "Venus"):
        if k in planets:
            p = planets[k]
            rows.append({
                "label": f"{k} (karaka)",
                "lord": k,
                "house": p.get("house"),
                "sign": p.get("sign"),
                "dignity": p.get("dignity", ""),
            })
    vim = pc.get("vimshottari", {})
    ad = next((a for a in vim.get("current_md_antardashas", []) if a.get("status") == "current"), {})
    try:
        from client_question_engine import pillar_overall_score
        pillar_score = pillar_overall_score(pc)
    except Exception:
        pillar_score = 0
    return {
        "name": display_name or meta.get("client", "Client"),
        "dob": meta.get("dob", ""),
        "lagna": lagna,
        "lagna_degree": round(float(meta.get("lagna_degree") or 0), 1),
        "pillar_score": pillar_score,
        "current_md": vim.get("current_md", {}).get("md_lord", ""),
        "current_ad": ad.get("ad_lord", ""),
        "current_ad_range": _fmt_range(ad.get("start", ""), ad.get("end", "")) if ad else "",
        "facts": rows,
    }


def scan_timing_windows(
    pc: dict,
    ctx: QuestionContext,
    *,
    years_ahead: int = 18,
) -> list[dict[str, Any]]:
    """Upcoming Vimshottari antardashas scored for this question domain."""
    cfg = DOMAIN_TIMING.get(ctx.domain, DOMAIN_TIMING["general"])
    lords_set = set(cfg.get("lords") or [])
    houses_set = set(cfg.get("houses") or set())
    lagna = pc.get("lagna", {}).get("sign") or pc.get("meta", {}).get("lagna_sign", "")
    planets = pc.get("planets", {})
    h_lords = {
        SIGN_LORDS.get(house_sign(h, lagna), "")
        for h in ctx.houses
    }
    today = date.today()
    cutoff = today.replace(year=today.year + years_ahead)
    out: list[dict[str, Any]] = []
    for a in pc.get("vimshottari", {}).get("current_md_antardashas", []):
        try:
            end = _parse_ymd(a.get("end", ""))
            start = _parse_ymd(a.get("start", ""))
        except ValueError:
            continue
        if end < today:
            continue
        if start > cutoff:
            continue
        lord = a.get("ad_lord", "")
        ph = house_from_lagna(planets.get(lord, {}).get("sign", ""), lagna) if planets.get(lord) else 0
        score = 0
        tags: list[str] = []
        if lord in lords_set:
            score += 2
            tags.append("domain-lord")
        if lord in h_lords:
            score += 3
            tags.append("house-lord")
        if lord in cfg.get("karakas", ()):
            score += 2
            tags.append("karaka")
        if ph in houses_set:
            score += 1
            tags.append(f"on-H{ph}")
        if a.get("status") == "current":
            score += 1
            tags.append("current")
        if score < 1:
            continue
        dob = pc.get("meta", {}).get("dob", "")
        out.append({
            "lord": lord,
            "start": a.get("start", "")[:10],
            "end": a.get("end", "")[:10],
            "range_label": _fmt_range(a.get("start", ""), a.get("end", "")),
            "planet_house": ph,
            "score": score,
            "tags": tags,
            "age_start": _age_on(dob, start) if dob else None,
            "age_end": _age_on(dob, end) if dob else None,
            "is_current": a.get("status") == "current",
        })
    out.sort(key=lambda x: (-x["score"], x["start"]))
    return out


def find_dasha_overlaps(
    windows_a: list[dict],
    windows_b: list[dict],
    *,
    min_score: int = 2,
) -> list[dict[str, Any]]:
    """Date-range overlap between two charts' scored windows."""
    overlaps: list[dict[str, Any]] = []
    for wa in windows_a:
        for wb in windows_b:
            start = max(wa["start"], wb["start"])
            end = min(wa["end"], wb["end"])
            if start >= end:
                continue
            score = wa["score"] + wb["score"]
            if score < min_score:
                continue
            overlaps.append({
                "start": start,
                "end": end,
                "range_label": _fmt_range(start, end),
                "score": score,
                "a_lord": wa["lord"],
                "a_house": wa.get("planet_house"),
                "b_lord": wb["lord"],
                "b_house": wb.get("planet_house"),
                "a_tags": wa.get("tags", []),
                "b_tags": wb.get("tags", []),
            })
    overlaps.sort(key=lambda x: (-x["score"], -(_parse_ymd(x["end"]) - _parse_ymd(x["start"])).days))
    return overlaps


def _dignity_phrase(dig: str) -> str:
    m = {
        "exalted": "exalted  -  very supportive",
        "own_sign": "own sign  -  strong",
        "moolatrikona": "moolatrikona  -  strong",
        "debilitated": "debilitated  -  needs extra effort",
        "enemy_sign": "enemy sign  -  headwind",
        "friend_sign": "friend sign  -  moderate support",
        "neutral_sign": "neutral",
    }
    return m.get(dig, dig or "unknown")


def _action_steps(ctx: QuestionContext, snap: dict, peak: Optional[dict], dual: bool) -> list[str]:
    steps: list[str] = []
    intent = ctx.intent
    domain = ctx.domain
    ps = snap.get("pillar_score", 0)
    if intent == "when" and domain in ("speech", "children"):
        steps.append("Do not wait passively  -  improvement comes through regular therapy and daily home practice, not one lucky month alone.")
        if peak:
            steps.append(f"Primary window to watch: {peak.get('range_label', '')}  -  increase session consistency when this band opens.")
        cur = snap.get("current_ad_range")
        if cur:
            steps.append(f"Now through {cur.split(' to ')[-1]}: build routine, school support, and therapist rapport (prep phase).")
        if ps <= 1:
            steps.append("Chart delivery is modest (low Pillar score)  -  results arrive slower than promise; patience is part of the remedy.")
    elif intent == "recovery":
        steps.append("Follow medical advice steadily; astrology supports recovery windows, not replacement of care.")
        if peak:
            steps.append(f"Strongest support band: {peak.get('range_label', '')}.")
    elif intent == "legal_outcome":
        steps.append("Document everything, meet deadlines, and align major filings with the favourable dasha band below.")
    else:
        steps.append("Read the technique table  -  majority positive methods outweigh a single dasha guess.")
    if dual:
        steps.append("Dual-chart overlap (parent + child) raises practical confidence even when each chart alone is below 75%.")
    return steps[:5]


def compose_dual_verdict(
    ctx: QuestionContext,
    primary: dict,
    related: Optional[dict],
    overlaps: list[dict],
) -> dict[str, Any]:
    """Merge single-chart synthesis + overlap into client-facing verdict."""
    syn = primary["synthesis"]
    p_pct = syn["confluence_pct"]
    r_pct = related["synthesis"]["confluence_pct"] if related else 0
    peak = overlaps[0] if overlaps else None
    if not peak and primary.get("windows"):
        w = primary["windows"][0]
        peak = {"range_label": w["range_label"], "start": w["start"], "end": w["end"], "score": w["score"], "single_chart": True}

    practical = "LOW"
    if related and overlaps and peak:
        if peak["score"] >= 6 and p_pct >= 35 and r_pct >= 15:
            practical = "MODERATE-HIGH"
        elif peak["score"] >= 4:
            practical = "MODERATE"
    elif syn.get("confirmed"):
        practical = syn["confidence"]
    elif p_pct >= 60:
        practical = "MODERATE"
    elif peak and peak.get("score", 0) >= 4:
        practical = "MODERATE"

    if ctx.intent == "when":
        if related and peak and not peak.get("single_chart"):
            headline = (
                f"Most likely window: {peak['range_label']} "
                f"({related['snapshot']['role'].title()} {peak['b_lord']} + "
                f"{primary['snapshot']['role'].title()} {peak['a_lord']})"
            )
            sub = "Dual-chart dasha overlap  -  neither chart alone hit 75%, but both point to the same period."
        elif peak:
            headline = f"Best single-chart window: {peak['range_label']} ({peak.get('a_lord') or peak.get('lord', '')} antardasha)"
            sub = syn["headline"]
        else:
            headline = syn["headline"]
            sub = "No strong dasha window scored for this domain in the next 18 years."
    else:
        headline = syn["headline"]
        sub = f"Technique confluence: {p_pct}% positive ({syn['positive_votes']}/{syn['total_techniques']} methods)."

    bullets: list[str] = []
    if peak:
        bullets.append(f"Peak timing band: {peak['range_label']}.")
    if related:
        bullets.append(
            f"{primary['snapshot']['name']}: {p_pct}% methods positive  -  "
            f"{related['snapshot']['name']}: {r_pct}% methods positive."
        )
        if overlaps:
            bullets.append(f"{len(overlaps)} dual-chart overlap band(s) found  -  best score {overlaps[0]['score']}.")
    else:
        bullets.append(f"Confidence label: {syn['confidence']}  -  confirmed gate: {'yes' if syn.get('confirmed') else 'no'}.")

    return {
        "headline": headline,
        "subhead": sub,
        "practical_confidence": practical,
        "peak_window": peak,
        "bullets": bullets,
        "confirmed_gate": bool(syn.get("confirmed")),
        "primary_pct": p_pct,
        "related_pct": r_pct if related else None,
    }


def _subject_block(result: dict, label: str) -> str:
    snap = result["snapshot"]
    syn = result["synthesis"]
    route = syn["routing"]
    rows = ""
    for f in snap["facts"][:6]:
        rows += (
            f"<tr><td>{_esc(f['label'])}</td><td>{_esc(f['lord'])}</td>"
            f"<td>H{f.get('house','?')}</td><td>{_esc(_dignity_phrase(f.get('dignity','')))}</td></tr>"
        )
    tech_rows = ""
    for t in result.get("techniques", []):
        mark = {"positive": "+", "caution": "-", "neutral": "="}.get(t["direction"], "?")
        cls = {"positive": "dot-g", "caution": "dot-r", "neutral": ""}.get(t["direction"], "")
        tech_rows += (
            f"<tr><td class='{cls}'>{mark}</td><td>{_esc(t['label'])}</td>"
            f"<td>{_esc(t['note'][:120])}</td></tr>"
        )
    win_rows = ""
    for w in result.get("windows", [])[:6]:
        age = ""
        if w.get("age_start") is not None:
            age = f" (age {w['age_start']} - {w['age_end']})"
        cur = " * current" if w.get("is_current") else ""
        win_rows += (
            f"<tr><td><strong>{_esc(w['lord'])}</strong>{cur}</td>"
            f"<td>{_esc(w['range_label'])}{age}</td>"
            f"<td>H{w.get('planet_house','?')}</td><td>{', '.join(w.get('tags',[]))}</td></tr>"
        )
    return f"""
<div class="card">
  <h3>{_esc(label)}  -  {_esc(snap['name'])}</h3>
  <p class="when">Born {_esc(snap['dob'])} | {_esc(snap.get('place',''))} | Lagna {_esc(snap['lagna'])} ({snap['lagna_degree']} deg)</p>
  <p class="body">Mapped: <strong>{_esc(route['title'])}</strong>  -  H{route['primary_house']} focus  -  intent {route['intent']}
   -  {syn['positive_votes']}/{syn['total_techniques']} methods positive ({syn['confluence_pct']}%)</p>
  <p class="body">Current dasha: <strong>{_esc(snap['current_md'])} - {_esc(snap['current_ad'])}</strong> ({_esc(snap['current_ad_range'])})</p>
  <table class="tl"><thead><tr><th>Factor</th><th>Planet</th><th>House</th><th>Strength</th></tr></thead><tbody>{rows}</tbody></table>
  <h4 style="margin:16px 0 8px;font-size:.95rem">Timing windows (Vimshottari)</h4>
  <table class="tl"><thead><tr><th>AD Lord</th><th>Period</th><th>Placement</th><th>Tags</th></tr></thead><tbody>{win_rows or '<tr><td colspan=4>No scored windows in range</td></tr>'}</tbody></table>
  <h4 style="margin:16px 0 8px;font-size:.95rem">Technique votes</h4>
  <table class="tl"><thead><tr><th></th><th>Method</th><th>Finding</th></tr></thead><tbody>{tech_rows}</tbody></table>
</div>"""


def _remedy_sections_html(report: dict[str, Any]) -> str:
    try:
        from gemstone_remedy import render_remedy_section_html
    except ImportError:
        return ""
    parts: list[str] = []
    primary = report.get("remedy")
    if primary and primary.get("ok"):
        name = report.get("primary", {}).get("snapshot", {}).get("name", "Primary chart")
        parts.append(
            f'<h3 class="section-h" style="margin-top:28px">Remedies — — {_esc(name)}</h3>'
            + render_remedy_section_html(primary, compact=False)
        )
    related = report.get("remedy_related")
    if related and related.get("ok"):
        rname = report.get("related", {}).get("snapshot", {}).get("name", "Related chart")
        parts.append(
            f'<h3 class="section-h" style="margin-top:28px">Remedies — — {_esc(rname)}</h3>'
            + render_remedy_section_html(related, compact=False)
        )
    return "\n".join(parts)


def render_main_question_embed_html(report: dict[str, Any], *, skip_remedy: bool = True) -> str:
    """Slim fragment for focus/confluence embeds — no duplicate hero, CSS, verdict, or gemstone blocks."""
    if not report.get("ok"):
        return f"<p class='warn'>{_esc(report.get('error', 'Failed'))}</p>"
    parts: list[str] = []
    dd = report.get("deepdive_html") or ""
    if skip_remedy and dd:
        dd = re.sub(
            r"<div class='card blue'><h3>Remedy for.*?</div>\s*",
            "",
            dd,
            count=1,
            flags=re.S,
        )
    if dd.strip():
        parts.append(dd.strip())
    parts.append(_subject_block(report["primary"], "Live technique engine"))
    return "\n".join(parts)


def render_main_question_report_html(report: dict[str, Any], *, inline: bool = False) -> str:
    if not report.get("ok"):
        return f"<p class='warn'>{_esc(report.get('error', 'Failed'))}</p>"

    v = report["verdict"]
    steps = "".join(f"<li>{_esc(s)}</li>" for s in report.get("action_steps", []))
    bullets = "".join(f"<li>{_esc(b)}</li>" for b in v.get("bullets", []))
    pill_cls = {"VERY HIGH": "hi", "HIGH": "hi", "MODERATE-HIGH": "hi", "MODERATE": "mid"}.get(v["practical_confidence"], "lo")

    overlap_html = ""
    for o in report.get("overlaps", [])[:8]:
        overlap_html += (
            f"<tr><td>{_esc(o['range_label'])}</td>"
            f"<td>{_esc(report['primary']['snapshot']['name'])}: {o['a_lord']} (H{o.get('a_house','?')})</td>"
            f"<td>{_esc(report['related']['snapshot']['name'])}: {o['b_lord']} (H{o.get('b_house','?')})</td>"
            f"<td>{o['score']}</td></tr>"
        )
    dual_section = ""
    if report.get("related") and overlap_html:
        dual_section = f"""
<h2 class="section-h">Dual-Chart Overlap</h2>
<div class="card green">
  <p class="body">Parent + child (or two related charts)  -  overlapping antardashas raise practical confidence.</p>
  <table class="tl"><thead><tr><th>Overlap period</th><th>Chart A</th><th>Chart B</th><th>Score</th></tr></thead>
  <tbody>{overlap_html}</tbody></table>
</div>"""

    minilm_note = ""

    body = f"""
<div class="{'wrap' if not inline else ''}">
  <div class="hero">
    <h1>Main Question Report</h1>
    <div class="tag">&ldquo;{_esc(report['question'])}&rdquo;</div>
    <div class="meta">
      <span>{datetime.now().strftime('%d %B %Y').lstrip('0')}</span>
    </div>
  </div>
  {minilm_note}
  <h2 class="section-h">Final Answer</h2>
  <div class="card {'green' if v.get('confirmed_gate') else 'amber'}">
    <h3>{_esc(v['headline'])}</h3>
    <p class="body">{_esc(v['subhead'])}</p>
    <span class="pill {pill_cls}">Practical confidence: {_esc(v['practical_confidence'])}</span>
    <ul class="bullets">{bullets}</ul>
  </div>
  <h2 class="section-h">What To Do</h2>
  <div class="card blue"><ul class="bullets">{steps}</ul></div>
  {report.get('deepdive_html', '')}
  {dual_section}
  <h2 class="section-h">Chart Analysis</h2>
  {_subject_block(report['primary'], 'Primary chart')}
  {(_subject_block(report['related'], 'Related chart') if report.get('related') else '')}
  {_remedy_sections_html(report)}
  <p style="font-size:.78rem;color:#64647a;margin-top:24px">
    Deterministic report  -  technique votes from natal chart math only.
    Confirmed date gate requires &gt;75% positive + mandatory pillars (Vim, KP, varga, Goel/Chara).
  </p>
</div>"""

    if inline:
        return f"<style>{client_css()}</style>{body}"
    return (
        f"<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'/>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'/>"
        f"<title>Main Question  -  {_esc(report['primary']['snapshot']['name'])}</title>"
        f"<style>{client_css()}</style></head><body>{body}</body></html>"
    )


def _analyze_subject(question: str, subject: SubjectInput, ctx: QuestionContext) -> dict[str, Any]:
    from client_question_engine import evaluate_question_techniques, synthesize_answer

    if not question.strip():
        return {"ok": False, "error": "Question is empty."}
    pc = resolve_precompute(
        subject.name, subject.dob,
        extracted_path=subject.extracted_path or None,
        precomputed_path=subject.precomputed_path or None,
        birth_time=subject.birth_time or None,
        latitude=subject.latitude,
        longitude=subject.longitude,
        timezone=subject.timezone,
        place_name=subject.place_name,
    )
    parsed = {"lagna": pc.get("lagna", {}), "planets": pc.get("planets", {})}
    birth_kw = {
        "client_name": subject.name,
        "dob": subject.dob,
        "birth_time": subject.birth_time,
        "rectified_time": subject.birth_time,
        "latitude": subject.latitude,
        "longitude": subject.longitude,
        "timezone": subject.timezone,
        "place_name": subject.place_name,
        "gender": subject.gender,
    }
    verdicts = evaluate_question_techniques(ctx, pc, parsed, birth_kw=birth_kw)
    synthesis = synthesize_answer(ctx, verdicts)
    raw = {
        "ok": True,
        "question": question,
        "synthesis": synthesis,
        "techniques": [
            {
                "id": v.technique_id,
                "label": v.label,
                "source": v.source,
                "direction": v.direction,
                "note": v.note,
                "timing": v.timing,
            }
            for v in verdicts if v.applicable
        ],
    }
    snap = extract_chart_snapshot(pc, ctx, display_name=subject.name)
    snap["role"] = subject.role
    snap["place"] = subject.place_name
    windows = scan_timing_windows(pc, ctx)
    return {**raw, "snapshot": snap, "windows": windows, "pc": pc}


def build_main_question_report(
    question: str,
    subject: SubjectInput,
    related: Optional[SubjectInput] = None,
    *,
    related_question: Optional[str] = None,
) -> dict[str, Any]:
    """
    Full deterministic Main Question pipeline ? structured dict + HTML.
    """
    if not question.strip():
        return {"ok": False, "error": "Question is empty."}

    ctx = route_client_question(question)
    md_hint = minilm_domain_hint(question)

    primary = _analyze_subject(question, subject, ctx)
    if not primary.get("ok"):
        return primary

    rel_result = None
    overlaps: list[dict] = []
    rctx = None
    if related and related.dob and related.birth_time:
        rq = related_question or question
        rctx = route_client_question(rq)
        if re.search(r"\b(child|son|daughter|kid|baby)\b", question.lower()):
            rctx = route_client_question("when will speech improve")
        rel_result = _analyze_subject(rq, related, rctx)
        if rel_result.get("ok"):
            overlaps = find_dasha_overlaps(primary.get("windows", []), rel_result.get("windows", []))

    verdict = compose_dual_verdict(ctx, primary, rel_result, overlaps)
    snap = primary["snapshot"]
    action_steps = _action_steps(ctx, snap, verdict.get("peak_window"), bool(rel_result))

    # House + divisional + dasha/transit confluence + 108-rule deep-dive for the asked area
    deepdive_html = ""
    try:
        from question_house_deepdive import build_deepdive
        deepdive_html = build_deepdive(
            primary["pc"], ctx,
            lat=subject.latitude, lon=subject.longitude, tz=subject.timezone,
            gender=subject.gender,
        )
    except Exception:
        deepdive_html = ""

    remedy_primary = None
    remedy_related = None
    try:
        from gemstone_remedy import build_remedy_report
        remedy_primary = build_remedy_report(
            primary["pc"], question=question, domain=ctx.domain, intent=ctx.intent,
            client_name=subject.name, question_scoped=True,
        )
        if rel_result and related and rctx:
            remedy_related = build_remedy_report(
                rel_result["pc"],
                question=related_question or "when will speech improve",
                domain=rctx.domain,
                client_name=related.name,
            )
    except Exception:
        remedy_primary = None

    report = {
        "ok": True,
        "question": question,
        "minilm_domain": md_hint,
        "routing": primary["synthesis"]["routing"],
        "primary": primary,
        "related": rel_result,
        "overlaps": overlaps,
        "verdict": verdict,
        "action_steps": action_steps,
        "remedy": remedy_primary,
        "remedy_related": remedy_related,
        "synthesis": primary["synthesis"],
        "techniques": primary.get("techniques", []),
        "deepdive_html": deepdive_html,
    }
    report["html"] = render_main_question_report_html(report, inline=False)
    report["html_inline"] = render_main_question_report_html(report, inline=True)
    return report


def save_main_question_report(
    report: dict[str, Any],
    out_dir: str | Path,
    slug: str,
) -> Optional[Path]:
    if not report.get("ok") or not report.get("html"):
        return None
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y%m%d")
    domain = report.get("routing", {}).get("domain", "Question").replace(" ", "_").title()
    path = out / f"MainQuestion_{domain}_{slug}_{today}.html"
    path.write_text(finalize_report_html(report["html"]), encoding="utf-8")
    report["report_path"] = str(path)
    try:
        from gemstone_remedy import save_remedy_report
        if report.get("remedy"):
            rp = save_remedy_report(report["remedy"], out, slug)
            if rp:
                report["remedy_path"] = rp
        if report.get("remedy_related"):
            rslug = f"{slug}_Related"
            rr = save_remedy_report(report["remedy_related"], out, rslug)
            if rr:
                report["remedy_related_path"] = rr
    except Exception:
        pass
    return path
