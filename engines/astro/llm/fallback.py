"""Deterministic prose fallbacks when the LLM is unavailable or fails QA.

Prediction facts never change. These templates only express CardFacts /
QuestionFacts / HoraryFacts / PalmFacts in plain English.
"""

from __future__ import annotations

from typing import Any


def _status_phrase(status: str, *, kind: str = "promise") -> str:
    s = (status or "").lower()
    if kind == "challenge":
        return {
            "strongly_indicated": "strongly indicated",
            "indicated": "indicated",
            "mixed": "mixed",
            "weak": "not strongly indicated",
            "insufficient_evidence": "not strongly indicated from the available evidence",
        }.get(s, "mixed")
    return {
        "strongly_supported": "strongly supported",
        "supported": "supported",
        "mixed": "mixed",
        "weak": "not strongly supported",
        "insufficient_evidence": "not strongly established from the available evidence",
    }.get(s, "mixed")


def _activation_phrase(status: str) -> str:
    return {
        "strongly_active": "strongly active",
        "active": "active",
        "mixed": "mixed",
        "weak": "only lightly active",
        "inactive": "not strongly active right now",
        "insufficient_evidence": "unclear in the current phase",
    }.get((status or "").lower(), "mixed")


def card_fallback(card: Any) -> dict[str, Any]:
    """Language-only overlay dict for one life-area card."""
    area = getattr(card, "area", "") or (card.get("area") if isinstance(card, dict) else "")
    kind = getattr(card, "kind", "promise") if not isinstance(card, dict) else card.get("kind", "promise")
    status = getattr(card, "status", "") if not isinstance(card, dict) else card.get("status", "")
    activation = (
        getattr(card, "activation_status", "")
        if not isinstance(card, dict) else card.get("activation_status", "")
    )
    label = getattr(card, "label", area) if not isinstance(card, dict) else card.get("label", area)
    manifests = list(
        getattr(card, "manifestation_ids", None)
        if not isinstance(card, dict) else card.get("manifestation_ids") or []
    )
    tags = list(
        getattr(card, "semantic_tags", None)
        if not isinstance(card, dict) else card.get("semantic_tags") or []
    )
    is_challenge = kind == "challenge" or area in ("health", "troubles")

    if is_challenge:
        headline = (
            f"The challenge pattern for {label or 'this area'} is "
            f"{_status_phrase(status, kind='challenge')}."
        )
        summary = (
            f"Current sensitivity is {_activation_phrase(activation)}. "
            f"Routine and early attention matter more than alarm."
        )
        show = manifests[:3] or tags[:3] or [
            "routine and recovery mattering more than usual",
            "pacing responsibility to avoid accumulated strain",
        ]
        watch = ["Skipping rest or preventive care can increase avoidable pressure."]
        helps = ["Keep a simple daily routine and address small issues early."]
    else:
        headline = (
            f"The underlying promise for {label or 'this area'} is "
            f"{_status_phrase(status)}."
        )
        summary = (
            f"The current phase is {_activation_phrase(activation)}. "
            f"Timing may open doors, but it cannot create a promise the chart "
            f"does not already support."
        )
        show = manifests[:3] or tags[:3] or [
            "steady progress through consistent effort",
            "clearer opportunities when timing aligns",
        ]
        watch = ["Rushing ahead of the validated window can create friction."]
        helps = ["Prepare quietly and move when the stronger windows open."]

    timing_summary = ""
    window = getattr(card, "window", None) if not isinstance(card, dict) else card.get("window")
    if window is not None:
        label_w = getattr(window, "label", "") if not isinstance(window, dict) else window.get("label", "")
        if label_w:
            timing_summary = f"A validated timing note for this area: {label_w}."

    return {
        "headline": headline[:140],
        "why": summary[:220],
        "meaning": summary[:280],
        "summary": summary[:280],
        "manifestations": [str(x)[:120] for x in show][:3],
        "how_this_may_show_up": [str(x)[:120] for x in show][:3],
        "what_to_watch": [str(x)[:120] for x in watch][:2],
        "what_helps": [str(x)[:120] for x in helps][:2],
        "pressure": (watch[0] if watch else "")[:180],
        "action": (helps[0] if helps else "")[:180],
        "timing_summary": timing_summary[:180],
    }


def report_fallback(facts: Any) -> dict[str, Any]:
    cards = getattr(facts, "cards", None) or []
    overlay_cards = {}
    for c in cards:
        area = getattr(c, "area", "") or ""
        if area:
            overlay_cards[area] = card_fallback(c)
    name = getattr(facts, "first_name", "") or ""
    opening = (
        f"{name}, here is a clear reading of your chart's life areas."
        if name else
        "Here is a clear reading of the chart's life areas."
    )
    return {"opening": opening, "cards": overlay_cards}


def question_fallback(facts: Any) -> dict[str, Any]:
    status = getattr(facts, "promise_status", "") or ""
    direction = getattr(facts, "direction", "mixed") or "mixed"
    area = getattr(facts, "area_key", "this question") or "this question"
    conf = getattr(facts, "confidence", "moderate") or "moderate"
    dir_word = {
        "support": "supports", "up": "supports",
        "caution": "does not strongly favour", "down": "does not strongly favour",
        "mixed": "is mixed on", "neutral": "is mixed on",
    }.get(direction, "is mixed on")
    answer = (
        f"Your chart {dir_word} {area}. "
        f"Confidence from the available methods is {conf}."
    )
    if status in ("weak", "insufficient_evidence"):
        answer = (
            f"The available chart facts do not support a high-confidence claim "
            f"for {area}."
        )
    timing = ""
    best = getattr(facts, "best", None)
    if best is not None:
        label = getattr(best, "label", "") or ""
        if label:
            timing = f"The strongest validated window note is: {label}."
        else:
            timing = "Validated timing windows are listed in the reading below."
    return {
        "opening": "Here is the straight answer from your chart facts.",
        "answer": answer[:420],
        "timing": timing[:220],
        "action": "Prepare within the validated windows rather than forcing a date.",
    }


def horary_fallback(facts: Any) -> dict[str, Any]:
    label = getattr(facts, "label", "Genuinely open") or "Genuinely open"
    conf = getattr(facts, "confidence", "moderate") or "moderate"
    subject = getattr(facts, "subject", "this") or "this"
    return {
        "lead": f"You asked about {subject}. Here is the combined reading.",
        "verdict_line": f"The reading reads as: {label} (confidence {conf}).",
        "why": "The moment-chart methods were combined under the product's weighting rules.",
        "action": "Act on the answer as framed — a horary chart speaks to this question only.",
    }


def palm_fallback(facts: Any) -> dict[str, Any]:
    aspects = {}
    for a in getattr(facts, "aspects", None) or []:
        key = getattr(a, "aspect", "") or ""
        if not key:
            continue
        direction = getattr(a, "direction", "mixed") or "mixed"
        tags = list(getattr(a, "semantic_tags", None) or [])
        summary = str(getattr(a, "semantic_summary", "") or "").strip()
        headline = (
            summary[:140] if summary else
            f"Your {key.replace('_', ' ')} pattern reads as {direction}."
        )
        aspects[key] = {
            "headline": headline,
            "why": "Based on the measured palm signals for this life theme.",
            "points": [str(t)[:120] for t in tags[:3]],
        }
    name = getattr(facts, "first_name", "") or ""
    opening = (
        f"{name}, here is what both hands show together."
        if name else
        "Here is what both hands show together."
    )
    return {"opening": opening, "aspects": aspects}
