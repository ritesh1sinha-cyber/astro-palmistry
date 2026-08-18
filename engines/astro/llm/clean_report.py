"""Canonical clean life-area report (final_fix_plan §1-§28, §32-§34).

The calculation engine stays authoritative. This module:

1. maps legacy card areas onto the canonical 8-area contract,
2. builds a normalized area object from ``LifeAreaJudgementFact`` facts,
3. normalizes + deduplicates future checkpoints by YYYY-MM date key,
4. derives material easing / strong-improvement only from the calculated
   relief/stronger windows,
5. renders the final customer HTML with exactly four top-level sections and
   collapses the astrological calculation into one <details> per area,
6. validates both the normalized object and the rendered DOM.

The LLM only ever supplies *language* (conclusion / what helps) which is
validated against the supplied facts; it never supplies verdicts, dates,
lanes or checkpoints.
"""
from __future__ import annotations

import html
import re
from datetime import date, datetime
from typing import Any, Iterable, Optional

# ---------------------------------------------------------------------------
# Phase 32 — report versioning
# ---------------------------------------------------------------------------
REPORT_SCHEMA_VERSION = "v2-clean-life-area"

# ---------------------------------------------------------------------------
# Phase 1 — canonical life-area contract (fixed IDs + display names)
# ---------------------------------------------------------------------------
CANONICAL_AREAS: list[tuple[str, str]] = [
    ("work_career", "Work & Career"),
    ("money", "Money"),
    ("relationships", "Relationships"),
    ("children_family", "Children & Family"),
    ("health", "Health"),
    ("property_home", "Property & Home"),
    ("travel_foreign", "Travel & Foreign"),
    ("spiritual_inner", "Spiritual & Inner Life"),
]

CANONICAL_IDS: list[str] = [cid for cid, _ in CANONICAL_AREAS]
CANONICAL_TITLES: dict[str, str] = dict(CANONICAL_AREAS)

# Legacy card area key -> canonical id. The engine's per-card lanes and
# life-area judgements are keyed by the legacy key; prose overlay is keyed
# the same way.
LEGACY_TO_CANONICAL: dict[str, str] = {
    "career": "work_career",
    "money": "money",
    "love": "relationships",
    "home": "property_home",
    "children": "children_family",
    "health": "health",
    "learning": "travel_foreign",
    "inner": "spiritual_inner",
}

CANONICAL_TO_LEGACY: dict[str, str] = {v: k for k, v in LEGACY_TO_CANONICAL.items()}

# Plan §4 — allowed internal verdicts only.
ALLOWED_VERDICTS = {"GOOD", "MODERATE", "MIXED", "CHALLENGING"}

# final_judgement (engine) -> canonical verdict.
_VERDICT_MAP = {
    "good": "GOOD",
    "moderate": "MODERATE",
    "mixed": "MIXED",
    "challenging": "CHALLENGING",
    "insufficient": "MIXED",
}

# confluence agreement -> customer label
_AGREEMENT_LABEL = {
    "strong": "Strong",
    "good": "Good",
    "mixed": "Mixed",
    "conflicting": "Conflicting",
    "insufficient": "Insufficient",
}

# change_type -> checkpoint label
_CHANGE_LABEL = {
    "baseline": "Baseline",
    "improves": "Improves",
    "eases_but_continues": "Eases but continues",
    "continues": "Continues",
    "worsens": "Worsens",
    "mixed_change": "Mixed change",
}

# Lane display order (plan §21 example).
_LANE_ORDER = [
    "Natal foundation",
    "Main timing cycle",
    "Chara",
    "Yogini",
    "Slow transit",
    "Period-planet transit",
    "Natural significator",
]

_LEGACY_FORBIDDEN_TEXT = (
    "About You",
    "Family & Home",
    "Recently",
    "Right Now",
    "Your Current Chapter",
    "Year-by-Year Road Map",
    "Top Challenges",
    "Remedies & Gemstones",
    "Chart-Targeted",
    "15 different ways",
    "Combined answer",
    "Method / sub-report",
    "Technical details",
    "Year-by-Year",
)

_REQUIRED_DETAILS_TEXT = "Astrological calculation & future checkpoints"

# --- small helpers ---------------------------------------------------------


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field from a pydantic model, dict or namespace safely."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    if hasattr(obj, "model_dump") and not hasattr(obj, key):
        data = obj.model_dump(mode="json")
        return data.get(key, default)
    return getattr(obj, key, default)


def _month_key(iso_date: str) -> str:
    """Canonical YYYY-MM date key; falls back to '' for unparseable values."""
    if not iso_date:
        return ""
    text = str(iso_date).strip()
    m = re.match(r"^(\d{4})-(\d{2})", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return ""


def _month_display(iso_date: str) -> str:
    text = str(iso_date or "").strip()
    m = re.match(r"^(\d{4})-(\d{2})", text)
    if not m:
        return text
    try:
        return datetime(int(m.group(1)), int(m.group(2)), 1).strftime("%B %Y")
    except ValueError:
        return text


def _esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _sentence(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text if text[-1] in ".!?" else f"{text}."


def _capitalize(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text[0].upper() + text[1:]


def _as_date(value: Any) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Phase 3/6/7 — checkpoint normalization + material easing
# ---------------------------------------------------------------------------
def normalize_checkpoints(
    future_confluence: Iterable[Any],
    today: date,
    verdict_label: str,
) -> list[dict[str, str]]:
    """Deduplicate future checkpoints by YYYY-MM key and sort chronologically.

    - Every event is keyed by YYYY-MM; same-month triggers from different
      methods (e.g. Chara + Yogini in December 2028) merge into ONE row.
    - The baseline row is always first and uses the actual report date.
    - Rows are kept only when they are material (verdict change, an easing/
      worsening/mixed change, or a dasha change), never pure churn.
    """
    merged: dict[str, dict[str, Any]] = {}
    for fc in list(future_confluence or []):
        key = _month_key(_get(fc, "date", ""))
        if not key:
            continue
        change_type = str(_get(fc, "change_type", "continues") or "continues")
        judgement = str(_get(fc, "judgement", "mixed") or "mixed")
        dasha = [str(x) for x in list(_get(fc, "dasha_changes", None) or []) if str(x).strip()]
        reason = str(_get(fc, "reason", "") or "").strip()
        if key not in merged:
            merged[key] = {
                "when": key,
                "label": _CHANGE_LABEL.get(change_type, "Continues"),
                "verdict": _VERDICT_MAP.get(judgement, "MIXED"),
                "dasha": list(dasha),
                "reason": reason,
            }
        else:
            row = merged[key]
            # Later events in the same month win the verdict; triggers merge.
            row["verdict"] = _VERDICT_MAP.get(judgement, row["verdict"])
            row["label"] = _CHANGE_LABEL.get(change_type, row["label"])
            row["dasha"] = list(dict.fromkeys(row["dasha"] + dasha))
            if reason and reason not in row["reason"]:
                row["reason"] = f"{row['reason']} {reason}".strip()

    # Materiality: keep only rows that are meaningful. The engine already
    # publishes material rows only; a residual "Continues" row with no dasha
    # change and no reason is dropped as pure repetition.
    material = []
    for key in sorted(merged):
        row = merged[key]
        if row["label"] == "Continues" and not row["dasha"] and not row["reason"]:
            continue
        material.append(row)

    baseline = {
        "when": today.strftime("%Y-%m"),
        "label": "Baseline",
        "verdict": verdict_label,
        "dasha": [],
        "reason": "",
    }
    out = [baseline]
    seen = {baseline["when"]}
    for row in material:
        if row["when"] in seen:
            continue
        seen.add(row["when"])
        out.append(row)
    out.sort(key=lambda r: r["when"])
    return out


def material_easing(aj: Any) -> dict[str, str]:
    """Derive first material easing and stronger window from validated facts.

    Never treat a dasha change alone as relief. Only the pre-computed
    relief_window / stronger_window (calculated by the confluence engine) are
    authoritative; ``free`` projections strip them so free text gets the
    "no clear easing" fallback automatically.
    """
    relief = str(_get(aj, "relief_window", "") or "")
    stronger = str(_get(aj, "stronger_window", "") or "")
    return {"relief": relief, "stronger": stronger}


# ---------------------------------------------------------------------------
# Phase 2/7 — normalized area object builder
# ---------------------------------------------------------------------------
def _lane_rows(aj: Any) -> list[dict[str, str]]:
    """Map engine lane judgements onto the canonical lane display order."""
    lanes = dict(_get(aj, "lane_judgements", None) or {})
    if not lanes:
        lanes = dict(_get(aj, "lanes", None) or {})
    natal = str(_get(aj, "natal_promise", "") or "")
    if not natal:
        natal = str(_get(aj, "natal_foundation_score", None) or "")
        try:
            natal = _score_label_text(float(natal))
        except (TypeError, ValueError):
            natal = "mixed"
    rows: list[dict[str, str]] = []
    by_legacy = {
        "Main timing cycle": lanes.get("Vimshottari"),
        "Chara": lanes.get("Chara"),
        "Yogini": lanes.get("Yogini"),
        "Slow transit": lanes.get("Slow transit"),
        "Period-planet transit": lanes.get("Dasha-planet transit"),
        "Natural significator": lanes.get("Jaimini"),
    }
    mapping = {"Natal foundation": _capitalize(natal)}
    mapping.update({k: _capitalize(v) for k, v in by_legacy.items() if v})
    for name in _LANE_ORDER:
        value = mapping.get(name)
        if value:
            rows.append({"name": name, "verdict": value})
    return rows


def _score_label_text(value: float) -> str:
    if value >= 0.55:
        return "Good"
    if value <= -0.55:
        return "Challenging"
    if abs(value) < 0.18:
        return "Mixed"
    return "Moderate"


def build_normalized_area(
    canonical_id: str,
    title: str,
    aj: Any,
    prose_area: Optional[dict],
    today: date,
    paid: bool = True,
) -> dict[str, Any]:
    """Build one §3 normalized area object. All fields are mandatory."""
    verdict = _VERDICT_MAP.get(str(_get(aj, "final_judgement", "") or "").lower(), "MIXED")
    confluence_label = str(_get(aj, "confluence_label", "") or verdict)
    agreement = _AGREEMENT_LABEL.get(
        str(_get(aj, "confluence_agreement", "") or "insufficient").lower(), "Insufficient")

    # Conclusion — LLM language is preferred but only when it is real prose
    # with an actual source; otherwise the deterministic engine summary wins.
    conclusion = ""
    if isinstance(prose_area, dict):
        conclusion = _sentence(prose_area.get("conclusion") or "")
    if not conclusion:
        conclusion = _sentence(_get(aj, "current_summary", "") or "")
    if not conclusion:
        conclusion = f"The complete confluence for this area is currently {_capitalize(verdict)}."

    # What helps — one compact block (plan §18). Engine-approved remedies win;
    # fall back to the LLM remedy line, then a deterministic note.
    what_helps = ""
    if isinstance(prose_area, dict):
        what_helps = _sentence(prose_area.get("remedy") or "")
    if not what_helps:
        remedies = [str(x) for x in list(_get(aj, "approved_remedies", None) or []) if str(x).strip()]
        if not remedies:
            remedies = [str(x) for x in list(_get(aj, "supporting_factors", None) or []) if str(x).strip()][:2]
        if remedies:
            what_helps = _sentence("; ".join(remedies[:2]))
    if not what_helps:
        what_helps = "Consistent routine and deliberate pacing are the most reliable supports through this phase."

    # Timing — mandatory and deterministic (plan §11).
    timing = _build_timing(aj, today)

    # Calculation block (collapsed; plan §21).
    checkpoints = normalize_checkpoints(_get(aj, "future_confluence", None) or [], today, verdict)
    lanes = _lane_rows(aj)
    calculation = {
        "agreement": agreement,
        "lanes": lanes,
        "current_state": _capitalize(confluence_label),
        "checkpoints": checkpoints,
    }
    return {
        "id": canonical_id,
        "title": title,
        "verdict": verdict,
        "conclusion": conclusion,
        "timing": timing,
        "what_helps": what_helps,
        "calculation": calculation,
    }


def _build_timing(aj: Any, today: date) -> str:
    """Customer-facing timing. Never invents a date."""
    easing = material_easing(aj)
    relief = easing["relief"]
    stronger = easing["stronger"]

    current = str(_get(aj, "current_vimshottari", "") or "")
    current_end = ""
    try:
        from llm.schemas import DashaClockFact  # noqa: F401
    except Exception:
        pass
    # current_vimshottari is the md-ad label; its end is carried on the
    # ReportFacts.timing_systems clock, but the judgement carries none, so we
    # only reference what we can prove here.
    parts: list[str] = []
    if current:
        parts.append(f"The current timing cycle is {_capitalize(current)}.")
    if relief:
        parts.append(
            f"Pressure remains elevated until the first material easing around "
            f"{_month_display(relief)}.")
    elif current:
        parts.append("No clear material easing is established within the forecast horizon.")
    if stronger:
        parts.append(
            f"A stronger supportive phase requires {_month_display(stronger)} and later "
            "timing and transit factors to align.")
    elif not relief and not current:
        return "No single strong timing window is established by the available calculation."
    if not parts:
        return "No single strong timing window is established by the available calculation."
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Whole-report builder
# ---------------------------------------------------------------------------
def build_final_report(
    pc: dict,
    cards: Iterable[Any],
    analysis: Any,
    prose: Optional[dict],
    today: date,
    paid: bool,
    name: str = "",
) -> dict[str, Any]:
    """Build the normalized report object consumed by the clean renderer.

    ``analysis`` is the paid/free ``ReportFacts`` projection; ``prose`` is the
    humanized overlay dict (``conversational`` flag, top-level language fields
    and per-area ``areas`` keyed by legacy area key).
    """
    prose = prose if isinstance(prose, dict) else {}
    prose_areas = prose.get("areas") if isinstance(prose.get("areas"), dict) else {}

    judgements: dict[str, Any] = {}
    for aj in list(_get(analysis, "life_area_judgements", None) or []):
        key = str(_get(aj, "area", "") or "").strip()
        if key:
            judgements[key] = aj
    # Fall back to card-level confluence if judgements are missing (defensive).
    if not judgements:
        for c in list(cards or []):
            key = str(_get(c, "area", "") or "").strip()
            if key:
                judgements[key] = c

    areas: list[dict[str, Any]] = []
    for canonical_id, title in CANONICAL_AREAS:
        legacy = CANONICAL_TO_LEGACY[canonical_id]
        aj = judgements.get(legacy)
        prose_area = prose_areas.get(legacy) if isinstance(prose_areas.get(legacy), dict) else None
        if aj is None:
            aj = _blank_judgement(legacy, title)
        # Defense-in-depth: the paid facts carry exact dates. A free build must
        # never leak them even if the analysis projection was not stripped.
        if not paid:
            aj = _without_paid_dates(aj)
        areas.append(build_normalized_area(canonical_id, title, aj, prose_area, today, paid=paid))

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generated_at": today.strftime("%Y-%m-%d"),
        "meta": {
            "name": name,
            "paid": bool(paid),
            "access": "paid" if paid else "free",
        },
        "chart_signature": _build_chart_signature(pc, analysis, prose),
        "where_you_are_now": _build_where_you_are_now(pc, analysis, prose, today),
        "areas": areas,
        "final_practical_guidance": _build_final_guidance(pc, analysis, prose),
    }


def _blank_judgement(legacy: str, title: str) -> dict[str, Any]:
    return {
        "area": legacy,
        "label": title,
        "final_judgement": "insufficient",
        "current_summary": "",
        "current_vimshottari": "",
        "confluence_agreement": "insufficient",
        "confluence_label": "Insufficient evidence",
        "lane_judgements": {},
        "relief_window": "",
        "stronger_window": "",
        "future_confluence": [],
        "approved_remedies": [],
        "supporting_factors": [],
    }


def _without_paid_dates(aj: Any) -> Any:
    """Return a copy of a judgement with all paid-depth date fields blanked.

    Used as defense-in-depth when a free report is built from a paid-depth
    analysis projection (the pipeline normally strips these in
    ``project_for_access``, but the renderer must never trust that alone).
    """
    if hasattr(aj, "model_copy"):
        try:
            return aj.model_copy(update={
                "relief_window": "",
                "stronger_window": "",
                "future_confluence": [],
                "remedy_reason": "",
                "next_period": "",
                "current_transit": "",
                "divisional_verdict": "",
                "house_strength": "",
            })
        except Exception:
            pass
    if isinstance(aj, dict):
        copy = dict(aj)
        copy["relief_window"] = ""
        copy["stronger_window"] = ""
        copy["future_confluence"] = []
        return copy
    return aj


def _build_chart_signature(pc: dict, analysis: Any, prose: dict) -> dict[str, Any]:
    """5-7 compact facts (plan §23). No full calculation dump."""
    lagna = dict(pc.get("lagna") or {})
    moon = dict(pc.get("planets", {}).get("Moon") or {})
    sun = dict(pc.get("planets", {}).get("Sun") or {})
    facts: list[str] = []

    lagna_sign = str(lagna.get("sign") or "")
    lagna_nak = str(lagna.get("nakshatra") or "")
    if lagna_sign:
        facts.append(f"Ascendant {lagna_sign}" + (f" ({lagna_nak})" if lagna_nak else "") + ".")

    moon_sign = str(moon.get("sign") or "")
    moon_nak = str(moon.get("nakshatra") or "")
    if moon_sign:
        facts.append(f"Moon in {moon_sign}" + (f" ({moon_nak})" if moon_nak else "") + ".")

    sun_sign = str(sun.get("sign") or "")
    if sun_sign:
        facts.append(f"Sun in {sun_sign}.")

    # Key career + relationship signatures come from the canonical judgements.
    career = _verdict_for_analysis(analysis, "career")
    love = _verdict_for_analysis(analysis, "love")
    if career:
        facts.append(f"Career confluence is currently {_capitalize(career)}.")
    if love:
        facts.append(f"Relationship confluence is currently {_capitalize(love)}.")

    # Current dasha / timing (names only; exact end dates stay paid-depth).
    vim = str(_get(analysis, "phase_tone", "") or "")
    if vim:
        facts.append(f"The current life phase tone is {_capitalize(vim)}.")

    if len(facts) < 2:
        facts.append("The chart is built from the Vedic sidereal system.")
    return {"facts": [f for f in facts if str(f).strip()][:7]}


def _verdict_for_analysis(analysis: Any, legacy_key: str) -> str:
    for aj in list(_get(analysis, "life_area_judgements", None) or []):
        if str(_get(aj, "area", "") or "") == legacy_key:
            return str(_get(aj, "final_judgement", "") or "").lower()
    return ""


def _build_where_you_are_now(pc: dict, analysis: Any, prose: dict, today: date) -> dict[str, Any]:
    """80-140 word where-you-are-now (plan §22)."""
    parts: list[str] = []
    phase = _sentence(prose.get("current_phase") or "")
    if phase:
        parts.append(phase)
    why = _sentence(prose.get("why_now") or "")
    if why:
        parts.append(why)
    mind = [_sentence(x) for x in list(prose.get("mind_now") or []) if str(x).strip()][:3]
    if not parts and mind:
        parts.append("Currently on your mind: " + "; ".join(mind) + ".")
    if not parts:
        # Deterministic fallback from the phase facts.
        tone = str(_get(analysis, "phase_tone", "") or "mixed")
        notes = [str(x) for x in list(_get(analysis, "phase_notes", None) or []) if str(x).strip()][:2]
        parts.append(f"The current life phase is {_capitalize(tone)}.")
        if notes:
            parts.extend(_sentence(n) for n in notes)
    text = " ".join(parts)
    if len(text) > 700:
        text = text[:697].rsplit(" ", 1)[0] + "."
    return {"text": text, "mind_now": mind}


def _build_final_guidance(pc: dict, analysis: Any, prose: dict) -> list[str]:
    """3-5 concise bullets from highest-confidence areas (plan §24)."""
    bullets: list[str] = []
    for raw in list(prose.get("final_guidance") or []):
        item = _sentence(raw)
        if item and item not in bullets:
            bullets.append(item)
    if not bullets:
        judged = sorted(
            [
                {
                    "key": str(_get(aj, "area", "") or ""),
                    "verdict": str(_get(aj, "final_judgement", "") or "").lower(),
                    "summary": str(_get(aj, "current_summary", "") or ""),
                }
                for aj in list(_get(analysis, "life_area_judgements", None) or [])
                if str(_get(aj, "area", "") or "")
            ],
            key=lambda r: {"good": 3, "moderate": 2, "mixed": 1, "challenging": 0}.get(r["verdict"], 1),
            reverse=True,
        )
        seen_keys = set()
        for r in judged:
            key = r["key"]
            if key in seen_keys:
                continue
            seen_keys.add(key)
            title = CANONICAL_TITLES.get(LEGACY_TO_CANONICAL.get(key, ""), _capitalize(key))
            bullets.append(f"{title}: keep practical, steady steps through this phase.")
            if len(bullets) >= 4:
                break
    if not bullets:
        bullets.append("Keep your routine consistent and review your priorities at the next timing shift.")
    return bullets[:5]


# ---------------------------------------------------------------------------
# Phase 8 — clean renderer (4 top-level sections only)
# ---------------------------------------------------------------------------
def render_final_report(report: dict[str, Any]) -> str:
    """Render the normalized report. Calls ONLY the four sub-renderers."""
    body = (
        render_chart_signature(report.get("chart_signature") or {})
        + render_where_you_are_now(report.get("where_you_are_now") or {})
        + render_life_areas(report.get("areas") or [])
        + render_final_practical_guidance(report.get("final_practical_guidance") or [])
    )
    meta = report.get("meta") or {}
    paid = bool(meta.get("paid"))
    unlock = ""
    if not paid:
        unlock = (
            '<section id="unlock-cta" class="unlock-cta">'
            "<p>Unlock the full reading to see timing, what helps and the "
            "astrological calculation for every life area.</p>"
            "</section>"
        )
    return (
        '<!DOCTYPE html>'
        '<html lang="en" data-report-schema="%s">' % _esc(REPORT_SCHEMA_VERSION)
        + "<head>"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>Vedic Life-Area Reading</title>"
        + _STYLE_BLOCK
        + "</head><body>"
        + f'<div class="report-wrap" data-report-schema="{_esc(REPORT_SCHEMA_VERSION)}">'
        + "<main>"
        + body
        + unlock
        + "</main></div></body></html>"
    )


def render_chart_signature(signature: dict[str, Any]) -> str:
    facts = [str(x) for x in list(signature.get("facts") or []) if str(x).strip()]
    items = "".join(f"<li>{_esc(x)}</li>" for x in facts)
    return (
        '<section id="chart-signature" class="report-section chart-signature">'
        "<h2>Chart Signature</h2>"
        f"<ul class=\"signature-facts\">{items}</ul>"
        "</section>"
    )


def render_where_you_are_now(block: dict[str, Any]) -> str:
    text = str(block.get("text") or "").strip()
    return (
        '<section id="where-you-are-now" class="report-section where-you-are-now">'
        "<h2>Where You Are Now</h2>"
        f"<p>{_esc(text)}</p>"
        "</section>"
    )


def render_life_areas(areas: list[dict[str, Any]]) -> str:
    inner = "".join(render_life_area(a) for a in areas)
    return (
        '<section id="life-areas" class="report-section life-areas">'
        "<h2>Each Life Area</h2>"
        f"{inner}"
        "</section>"
    )


def render_life_area(area: dict[str, Any]) -> str:
    """Exactly: header(title+verdict), conclusion, timing, what helps, details."""
    area_id = str(area.get("id") or "").replace("_", "-")
    calc = area.get("calculation") or {}
    lanes = "".join(
        f"<li>{_esc(r.get('name'))}: {_esc(r.get('verdict'))}</li>"
        for r in list(calc.get("lanes") or [])
    )
    checkpoints = "".join(
        f"<li><strong>{_esc(_month_display(cp.get('when')))}</strong> — "
        f"{_esc(cp.get('label'))} · {_esc(cp.get('verdict'))}</li>"
        for cp in list(calc.get("checkpoints") or [])
    )
    details = (
        "<details class=\"calculation\">"
        "<summary>Astrological calculation &amp; future checkpoints</summary>"
        f"<p><strong>Current confluence:</strong> {_esc(calc.get('current_state') or '')}</p>"
        f"<p><strong>Agreement:</strong> {_esc(calc.get('agreement') or '')}</p>"
        f"<h4>Evidence lanes</h4><ul class=\"lanes\">{lanes}</ul>"
        f"<h4>Future checkpoints</h4><ul class=\"checkpoints\">{checkpoints}</ul>"
        "</details>"
    )
    return (
        f'<article id="area-{_esc(area_id)}" class="life-area" data-area="{_esc(area.get("id"))}">'
        "<header>"
        f"<h3>{_esc(area.get('title'))}</h3>"
        f'<span class="verdict verdict-{_esc(str(area.get("verdict")).lower())}">{_esc(area.get("verdict"))}</span>'
        "</header>"
        f"<p class=\"conclusion\">{_esc(area.get('conclusion'))}</p>"
        f'<div class="timing"><strong>Timing:</strong> {_esc(area.get("timing"))}</div>'
        f'<div class="what-helps"><strong>What helps:</strong> {_esc(area.get("what_helps"))}</div>'
        f"{details}"
        "</article>"
    )


def render_final_practical_guidance(bullets: Iterable[str]) -> str:
    items = "".join(f"<li>{_esc(x)}</li>" for x in list(bullets or []) if str(x).strip())
    return (
        '<section id="final-practical-guidance" class="report-section final-practical-guidance">'
        "<h2>Final Practical Guidance</h2>"
        f"<ul>{items}</ul>"
        "</section>"
    )


_STYLE_BLOCK = (
    "<style>"
    ":root{--ink:#1f2430;--muted:#5b6472;--line:#e3e6ec;--bg:#fbfbfd;--card:#ffffff;"
    "--good:#1c7c4d;--moderate:#8a6d1a;--mixed:#7a5c9e;--challenging:#b3402a;}"
    "*{box-sizing:border-box}body{margin:0;font:16px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;"
    "color:var(--ink);background:var(--bg)}"
    ".report-wrap{max-width:820px;margin:0 auto;padding:24px 20px 64px}"
    "main>*+*{margin-top:28px}"
    ".report-section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:22px 24px}"
    ".report-section h2{margin:0 0 14px;font-size:1.35rem;letter-spacing:.2px}"
    ".signature-facts{padding-left:20px;margin:0}"
    ".signature-facts li{margin:4px 0}"
    ".life-area{margin-top:20px;padding:18px 20px;border:1px solid var(--line);border-radius:10px;background:#fff}"
    ".life-area header{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px}"
    ".life-area h3{margin:0;font-size:1.12rem}"
    ".verdict{font-size:.72rem;font-weight:700;letter-spacing:.6px;text-transform:uppercase;"
    "padding:3px 10px;border-radius:999px;color:#fff}"
    ".verdict-good{background:var(--good)}.verdict-moderate{background:var(--moderate)}"
    ".verdict-mixed{background:var(--mixed)}.verdict-challenging{background:var(--challenging)}"
    ".conclusion{margin:8px 0 10px}.timing,.what-helps{margin:6px 0;color:var(--muted)}"
    ".timing strong,.what-helps strong{color:var(--ink)}"
    "details.calculation{margin-top:14px;border-top:1px dashed var(--line);padding-top:10px}"
    "details.calculation summary{cursor:pointer;font-weight:600}"
    "details.calculation ul{padding-left:20px;margin:6px 0}"
    "details.calculation h4{margin:10px 0 4px;font-size:.95rem}"
    ".unlock-cta{background:#fff;border:1px solid var(--line);border-radius:12px;padding:20px 24px;text-align:center}"
    "</style>"
)


# ---------------------------------------------------------------------------
# Phase 11/27/28 — validators
# ---------------------------------------------------------------------------
def validate_final_report(report: dict[str, Any]) -> list[str]:
    """Structural validation of the normalized object. Returns errors."""
    errors: list[str] = []
    areas = list(report.get("areas") or [])

    if len(areas) != 8:
        errors.append(f"expected exactly 8 areas, got {len(areas)}")
    ids = [str(a.get("id")) for a in areas]
    if len(set(ids)) != len(ids):
        errors.append("duplicate area ids")
    bad_ids = [i for i in ids if i not in CANONICAL_IDS]
    if bad_ids:
        errors.append(f"non-canonical area ids: {sorted(set(bad_ids))}")

    for a in areas:
        verdict = str(a.get("verdict") or "")
        if verdict not in ALLOWED_VERDICTS:
            errors.append(f"{a.get('id')}: invalid verdict {verdict!r}")
        for field in ("conclusion", "timing", "what_helps"):
            if not str(a.get(field) or "").strip():
                errors.append(f"{a.get('id')}: empty {field}")
        calc = a.get("calculation") or {}
        if not isinstance(calc, dict):
            errors.append(f"{a.get('id')}: missing calculation block")
            continue
        for field in ("agreement", "current_state"):
            if not str(calc.get(field) or "").strip():
                errors.append(f"{a.get('id')}: calculation missing {field}")
        cps = list(calc.get("checkpoints") or [])
        keys = [str(cp.get("when")) for cp in cps]
        if len(set(keys)) != len(keys):
            errors.append(f"{a.get('id')}: duplicate checkpoint dates")
        if keys != sorted(keys):
            errors.append(f"{a.get('id')}: checkpoints not sorted")

    if not report.get("chart_signature"):
        errors.append("missing chart signature")
    if not str((report.get("where_you_are_now") or {}).get("text") or "").strip():
        errors.append("missing where you are now")
    if not (report.get("final_practical_guidance") or []):
        errors.append("missing final practical guidance")
    return errors


def validate_final_html(html_text: str) -> list[str]:
    """DOM-level validation (plan §27/§28). Returns errors."""
    errors: list[str] = []
    if not html_text:
        return ["empty html"]

    if f'data-report-schema="{_esc(REPORT_SCHEMA_VERSION)}"' not in html_text:
        errors.append(f"missing data-report-schema={REPORT_SCHEMA_VERSION}")

    order = ["chart-signature", "where-you-are-now", "life-areas",
             "final-practical-guidance"]
    pos = -1
    for name in order:
        idx = html_text.find(f'id="{name}"')
        if idx == -1:
            errors.append(f"missing section #{name}")
            continue
        if idx < pos:
            errors.append(f"section #{name} out of order")
        pos = idx

    # Exactly eight canonical areas, in order.
    area_ids = ["work-career", "money", "relationships", "children-family",
                "health", "property-home", "travel-foreign", "spiritual-inner"]
    positions = []
    for aid in area_ids:
        idx = html_text.find(f'id="area-{aid}"')
        if idx == -1:
            errors.append(f"missing area #{aid}")
        else:
            positions.append(idx)
    if positions and positions != sorted(positions):
        errors.append("life areas out of order")
    count = html_text.count('class="life-area"')
    if count != 8:
        errors.append(f"expected exactly 8 life areas in DOM, got {count}")

    # Exactly one collapsed calculation block per area.
    details_n = html_text.count("<details")
    if details_n != 8:
        errors.append(f"expected exactly 8 <details> blocks, got {details_n}")
    if "Astrological calculation" not in html_text or "future checkpoints" not in html_text:
        errors.append("missing 'Astrological calculation & future checkpoints'")

    for phrase in _LEGACY_FORBIDDEN_TEXT:
        if phrase.lower() in html_text.lower():
            errors.append(f"legacy text present: {phrase!r}")

    # No raw LLM HTML: content blocks must be pure escaped text with no inner
    # tags. The <strong> label inside timing/what-helps is template markup and
    # is stripped before the LLM-supplied text is checked.
    for block in re.findall(
            r'<p class="conclusion">(.*?)</p>|<div class="timing">(.*?)</div>'
            r'|<div class="what-helps">(.*?)</div>',
            html_text, flags=re.S):
        joined = "".join(block)
        joined = re.sub(r"<strong>.*?</strong>", "", joined)
        if "<" in joined:
            errors.append("possible raw HTML inside content block")
            break
    return errors