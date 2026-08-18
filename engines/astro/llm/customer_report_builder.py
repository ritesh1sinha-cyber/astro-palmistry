"""Build a CustomerReport from internal analysis data.

This is the SINGLE bridge between the analysis pipeline and the customer-facing output.
Internal data (lane HTML, anchor logs, scoring artefacts) never leaks into the schema.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any

from . import fallback as FB
from .report_schema import (
    ClosingGuidance,
    CurrentPeriod,
    CustomerReport,
    FutureOutlook,
    LifeArea,
    LifeAreaMeta,
    LifeState,
    SubjectMeta,
    SummaryBlock,
    Tone,
)


def _safe_str(val: Any) -> str:
    """Coerce any value to a clean string; never return None."""
    if val is None:
        return ""
    return str(val).strip()


def _clip_sentences(text: str, n: int = 3) -> str:
    """Keep at most *n* sentences."""
    if not text:
        return ""
    parts = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    return ". ".join(parts[:n]) + ("." if parts else "")


def _build_meta(facts: Any, *, access: str, generated_at: str | None = None) -> SubjectMeta:
    birth = getattr(facts, "birth_data", None) or {}
    return SubjectMeta(
        name=_safe_str(getattr(facts, "subject_name", "") or getattr(birth, "name", "")),
        birth_date=_safe_str(getattr(birth, "date", "") if birth else ""),
        birth_time=_safe_str(getattr(birth, "time", "") if birth else ""),
        birth_place=_safe_str(getattr(birth, "place", "") if birth else ""),
        language=_safe_str(getattr(facts, "language", "en")),
        access=access,
        generated_at=generated_at or _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    )


def _build_summary(facts: Any, prose: dict[str, Any], *, access: str) -> SummaryBlock:
    headline = _safe_str(prose.get("astrological_basis"))
    opening = _safe_str(prose.get("interpretation"))
    strengths: list[str] = []
    watch: list[str] = []
    if access == "paid":
        for card in getattr(facts, "cards", []) or []:
            label = _safe_str(getattr(card, "label", ""))
            direction = _safe_str(getattr(card, "direction", ""))
            if direction == "support" and label:
                strengths.append(label)
            elif direction == "caution" and label:
                watch.append(label)
    return SummaryBlock(
        headline=_clip_sentences(headline, 2),
        opening=_clip_sentences(opening, 3),
        strengths=strengths[:5],
        watch=watch[:5],
    )


def _build_tone(facts: Any, prose: dict[str, Any]) -> Tone:
    tone_label = _safe_str(prose.get("tone_label"))
    tone_class = _safe_str(prose.get("tone_class"))
    if not tone_label:
        # Derive from first card
        cards = getattr(facts, "cards", []) or []
        if cards:
            label, cls = FB.area_tone(cards[0])
            tone_label = label
            tone_class = cls
    return Tone(
        style="vedic",
        chip=tone_label,
        tone_label=tone_label,
        tone_class=tone_class,
    )


def _build_life_areas(facts: Any, prose: dict[str, Any]) -> list[LifeArea]:
    """Build per-area blocks from prose overlay + card facts."""
    if not isinstance(prose.get("areas"), dict):
        return []
    cards_map = {getattr(c, "area", ""): c for c in (getattr(facts, "cards", []) or [])}
    areas: list[LifeArea] = []
    for area_key, area_prose in prose["areas"].items():
        if not isinstance(area_prose, dict):
            continue
        card = cards_map.get(area_key)
        chip, tone_cls = FB.area_tone(card) if card else ("", "")
        label = _safe_str(getattr(card, "label", "") or area_key.replace("_", " ").title()) if card else area_key.replace("_", " ").title()
        la = LifeArea(
            key=area_key,
            label=label,
            chip=area_prose.get("tone_label") or chip,
            tone_class=area_prose.get("tone_class") or tone_cls,
            conclusion=_safe_str(area_prose.get("conclusion")),
            astrological_basis=_safe_str(area_prose.get("astrological_basis")),
            interpretation=_safe_str(area_prose.get("interpretation")),
            outlook=_safe_str(area_prose.get("outlook")),
            timing=_safe_str(area_prose.get("timing")),
            manifestation=_safe_str(area_prose.get("manifestation")),
            remedy=_safe_str(area_prose.get("remedy")),
            transition_note=_safe_str(area_prose.get("transition_note")),
        )
        areas.append(la)
    return areas


def _build_life_state(facts: Any, prose: dict[str, Any]) -> LifeState:
    mind_now = prose.get("mind_now") or []
    if isinstance(mind_now, str):
        mind_now = [mind_now]
    family_note = prose.get("family_note") or []
    if isinstance(family_note, str):
        family_note = [family_note]
    return LifeState(
        what_is_on_your_mind=[_safe_str(x) for x in mind_now if _safe_str(x)][:3],
        why_this_period_feels_this_way=_safe_str(prose.get("why_now")),
        family_note=[_safe_str(x) for x in family_note if _safe_str(x)][:4],
    )


def _build_current_period(facts: Any, prose: dict[str, Any]) -> CurrentPeriod:
    vedic_period = _safe_str(prose.get("vedic_period"))
    if not vedic_period:
        vedic_period = FB._vedic_period_line(facts) if hasattr(FB, "_vedic_period_line") else ""
    phase_label = _safe_str(prose.get("current_phase"))
    phase_description = _safe_str(prose.get("personality"))
    return CurrentPeriod(
        vedic_period=_clip_sentences(vedic_period, 1),
        phase_label=_clip_sentences(phase_label, 1),
        phase_description=_clip_sentences(phase_description, 2),
    )


def _build_future_outlook(facts: Any, prose: dict[str, Any]) -> FutureOutlook:
    recent = _safe_str(prose.get("recent_months"))
    # near_term and longer_term can come from dasha timing if available
    return FutureOutlook(
        recent_months=_clip_sentences(recent, 2),
        near_term="",
        longer_term="",
    )


def _build_closing(prose: dict[str, Any]) -> ClosingGuidance:
    return ClosingGuidance(
        final_guidance=_safe_str(prose.get("final_guidance")),
    )


def build_customer_report(
    facts: Any,
    prose: dict[str, Any],
    *,
    access: str = "paid",
    generated_at: str | None = None,
) -> CustomerReport:
    """Build the CustomerReport from internal analysis facts + prose overlay.

    This is the SINGLE entry point for separating internal vs customer data.
    Internal artefacts (lane HTML, anchor logs, scoring) stay out of this schema.
    """
    meta = _build_meta(facts, access=access, generated_at=generated_at)
    summary = _build_summary(facts, prose, access=access)
    tone = _build_tone(facts, prose)
    life_areas = _build_life_areas(facts, prose) if access == "paid" else []
    life_state = _build_life_state(facts, prose) if access == "paid" else LifeState()
    current_period = _build_current_period(facts, prose)
    future_outlook = _build_future_outlook(facts, prose)
    closing = _build_closing(prose) if access == "paid" else ClosingGuidance()

    return CustomerReport(
        meta=meta,
        summary=summary,
        tone=tone,
        life_areas=life_areas,
        life_state=life_state,
        current_period=current_period,
        future_outlook=future_outlook,
        closing_guidance=closing,
    )
