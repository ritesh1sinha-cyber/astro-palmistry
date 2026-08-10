"""Human-language renderer from PredictionMeaning."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from interpretation.prediction_meaning import PredictionMeaning

from narration.sentence_variants import (
    CURRENT_HEADLINES,
    FUTURE_HEADLINES,
    PAST_HEADLINES,
    PAST_MANIFESTS,
    headline_key,
    manifest_keys,
    pick_variant,
)
from qa_checks.grammar_check import fix_grammar
from qa_checks.specificity import (
    TRANSPARENT_BULLET_FREE,
    TRANSPARENT_BULLET_PAID,
    TRANSPARENT_FREE,
    TRANSPARENT_PAID,
    is_specific_enough,
)


# Primary + secondary composites when both present.
_COMPOSITE: dict[tuple[str, str], str] = {
    ("visibility", "responsibility"): (
        "Your work can become more visible during this phase, although "
        "recognition may take longer than the effort itself."
    ),
    ("visibility", "delayed_reward"): (
        "Your work can become more visible during this phase, but recognition "
        "may follow only after you have taken on the responsibility that comes with it."
    ),
    ("network_gain", "opportunity"): (
        "Useful opportunities can come through people already in your network, "
        "especially when you stay open to practical collaboration."
    ),
    ("network_gain", "gains"): (
        "Useful opportunities can come through people already in your network, "
        "especially when you stay open to practical collaboration."
    ),
}


def uses_event_uncertainty(meaning: "PredictionMeaning") -> bool:
    """Strong timing + ambiguous event → transparent uncertainty headline."""
    timing = getattr(meaning, "timing_confidence", "") or meaning.confidence or ""
    event = getattr(meaning, "event_confidence", "") or "moderate"
    return timing in ("strong", "very_strong") and event == "low"


def _fallback_headline(meaning: "PredictionMeaning", *, past: bool) -> str:
    if uses_event_uncertainty(meaning):
        return TRANSPARENT_PAID
    # Prefer age-aware trajectory lines over "mixed phase for X".
    try:
        from report_language import trajectory_explain
        line = trajectory_explain(
            meaning.direction, meaning.area,
            age_band=meaning.age_band, variant=meaning.variant_index)
        if line:
            return line
    except Exception:  # noqa: BLE001
        pass
    area = meaning.narrative_area.replace("_", " ")
    if meaning.direction == "up":
        return f"This is a more supportive stretch for {area}."
    if meaning.direction == "down":
        return f"This stretch asks more patience around {area}."
    return f"This is a mixed phase for {area}."


def _composite_future(meaning: "PredictionMeaning") -> str:
    if not meaning.primary or not meaning.secondary:
        return ""
    key = (meaning.primary, meaning.secondary)
    text = _COMPOSITE.get(key, "")
    if not text:
        return ""
    if meaning.narrative_area == "early_career" and "work" in text.lower():
        return (
            "Your studies, first professional responsibilities or developing "
            "career direction can become more visible during this phase."
        )
    if meaning.narrative_area == "education":
        return (
            "Your effort may be noticed more by teachers, mentors or people "
            "guiding your studies during this phase."
        )
    return text


def render_headline(meaning: "PredictionMeaning", *, past: bool = True) -> str:
    table = PAST_HEADLINES if past else CURRENT_HEADLINES
    key = headline_key(meaning, past=past)
    text = pick_variant(key, table, meaning.variant_index)
    if not text and not past:
        text = _composite_future(meaning)
    if not text and len(meaning.manifestations) > 1:
        alt_key = (meaning.narrative_area, meaning.manifestations[1], meaning.direction)
        text = pick_variant(alt_key, table, meaning.variant_index)
    if not text:
        text = _fallback_headline(meaning, past=past)
    return fix_grammar(text)


def render_future_headline(meaning: "PredictionMeaning") -> str:
    key = headline_key(meaning, past=False)
    text = pick_variant(key, FUTURE_HEADLINES, meaning.variant_index)
    if not text:
        text = _composite_future(meaning)
    if not text:
        text = pick_variant(key, CURRENT_HEADLINES, meaning.variant_index)
    if not text and len(meaning.manifestations) > 1:
        alt = (meaning.narrative_area, meaning.manifestations[1], meaning.direction)
        text = pick_variant(alt, FUTURE_HEADLINES, meaning.variant_index)
    if not text:
        text = render_headline(meaning, past=False)
    return fix_grammar(text)


def render_manifest_bullets(
    meaning: "PredictionMeaning",
    *,
    n: int = 4,
    paid: bool = True,
) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for key in manifest_keys(meaning):
        pool = PAST_MANIFESTS.get(key) or []
        start = meaning.variant_index % max(1, len(pool)) if pool else 0
        for i in range(len(pool)):
            item = pool[(start + i) % len(pool)]
            low = item.lower()
            if low in seen:
                continue
            if not is_specific_enough(item, minimum=3):
                continue
            out.append(item)
            seen.add(low)
            if len(out) >= n:
                return out
    if not out:
        # Transparent — never invent "noticeable shift" filler.
        out = [TRANSPARENT_BULLET_PAID if paid else TRANSPARENT_BULLET_FREE]
    return out[:n]


def transparent_headline(*, paid: bool = True) -> str:
    return TRANSPARENT_PAID if paid else TRANSPARENT_FREE


def render_current_scene(
    area: str,
    direction: str,
    meaning: Optional["PredictionMeaning"] = None,
) -> str:
    if meaning:
        return render_headline(meaning, past=False)
    from predict_voice import AREA_SCENE
    return AREA_SCENE.get((area, direction), "")
