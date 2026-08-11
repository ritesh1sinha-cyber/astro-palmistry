"""Single-source-of-truth result for one Graharekha life area.

This module does not add astrology mathematics. It composes the already tested
confluence, promise, timing, manifestation and remedy engines into one stable
object. Dashboard, Free, Paid, Why and Timing consumers should read this object
rather than recomputing a life-area verdict independently.

Contract:
    evidence -> confluence -> promise + activation -> timing -> manifestation
              -> action/remedy -> rendering

Timing can never create a promise. D1/natal promise remains the baseline;
D9/D7/D10/D30 refine the meaning already produced by the promise engine.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional


_STRONG_PROMISE = {"strongly_supported", "supported"}
_WEAK_PROMISE = {"weak", "insufficient_evidence"}


def _age_band(pc: dict, today: date) -> str:
    try:
        from interpretation.life_stage import age_band
        return age_band(pc, today=today)
    except Exception:  # noqa: BLE001
        return "adult"


def _manifestations(pc: dict, area: str, promise: dict, activation: dict,
                     today: date, limit: int = 3) -> list[str]:
    try:
        import area_modules as AM
        return AM.manifestations_for(
            area,
            promise_status=str(promise.get("status") or ""),
            activation_status=str(activation.get("status") or ""),
            age_band=_age_band(pc, today),
            limit=limit,
            pc=pc,
        )
    except Exception:  # noqa: BLE001
        return []


def _action(pc: dict, area: str, direction: str, today: date) -> str:
    try:
        from narration.stage_actions import action_for_stage
        return action_for_stage(area, _age_band(pc, today), direction=direction)
    except Exception:  # noqa: BLE001
        return ""


def _remedy(pc: dict, area: str, house: int, direction: str,
            promise_status: str) -> str:
    # Existing remedy engine remains the sole authority for traditional support
    # and gemstone eligibility. The canonical layer only consumes its result.
    try:
        import area_report as AR
        return AR.classical_area_remedy(
            pc, area, house, direction, promise_status=promise_status) or ""
    except Exception:  # noqa: BLE001
        return ""


def _timing_windows(pc: dict, area: str, house: int, today: date,
                    supplied: Optional[list[dict]] = None) -> list[dict]:
    if supplied is not None:
        return list(supplied)
    try:
        import report_timing as RT
        return RT.windows_for_area(pc, area, house, start=today, years=5)
    except Exception:  # noqa: BLE001
        return []


def _timing_summary(windows: list[dict], promise: dict) -> dict[str, Any]:
    status = str(promise.get("status") or "insufficient_evidence")
    strong_promise = status in _STRONG_PROMISE
    validated = [
        w for w in windows
        if w.get("source") and w.get("confidence") in ("high", "very high")
    ]
    strong = [w for w in windows if w.get("aligned") and strong_promise]
    opportunities = [
        w for w in windows
        if w.get("aligned") and not strong_promise
    ]
    return {
        "windows": windows,
        "validated_windows": validated,
        "strong_windows": strong,
        "opportunity_windows": opportunities,
        "promise_allows_strong_timing": strong_promise,
        "timing_can_create_promise": False,
        "best_window": strong[0] if strong else (opportunities[0] if opportunities else None),
    }


def _normalized_why(confluence: dict, area: str) -> dict[str, Any]:
    """Build customer-safe evidence once from the canonical votes.

    Legacy confluence rows can still contain technical rule prose. The
    canonical object must never expose that raw layer to ReportFacts or HTML.
    """
    rows: list[dict[str, Any]] = []
    supporting: list[str] = []
    caution: list[str] = []
    try:
        from evidence_normalizer import normalize_vote
        for vote in list(confluence.get("votes") or []):
            norm = normalize_vote(vote, area=area)
            reason = str(norm.normalized_reason or "").strip()
            direction = str(norm.direction or "neutral")
            label = str(norm.method_label or "Chart evidence")
            if not reason:
                reason = f"{label} contributes to this reading."
            row = {
                "label": label,
                "direction": "support" if direction == "support" else
                             ("caution" if direction == "caution" else "neutral"),
                "value": float(getattr(vote, "value", 0) or 0),
                "reasons": [reason],
            }
            rows.append(row)
            if row["direction"] == "support":
                supporting.append(reason)
            elif row["direction"] == "caution":
                caution.append(reason)
    except Exception:
        pass

    # Fallback: never copy raw evidence blindly. Use only a safe summary.
    if not rows:
        direction = str(confluence.get("direction") or "mixed")
        label = "Chart evidence"
        reason = (
            "Several independent chart factors support this area."
            if direction == "support" else
            "Several independent chart factors add caution to this area."
            if direction == "caution" else
            "The chart evidence is mixed in this area."
        )
        rows = [{"label": label, "direction": direction if direction in
                 ("support", "caution") else "neutral", "value": 0.0,
                 "reasons": [reason]}]
        if direction == "support":
            supporting.append(reason)
        elif direction == "caution":
            caution.append(reason)

    return {
        "supporting": supporting[:6],
        "caution": caution[:6],
        "families": list(confluence.get("families") or []),
        "rows": rows[:8],
        "support": int(confluence.get("support") or
                       sum(1 for r in rows if r["direction"] == "support")),
        "caution_count": int(confluence.get("caution") or
                             sum(1 for r in rows if r["direction"] == "caution")),
        "neutral": int(confluence.get("neutral") or
                       sum(1 for r in rows if r["direction"] == "neutral")),
        "summary": ("The evidence is broadly supportive of this area." if str(confluence.get("direction") or "") == "support" else
                   "The evidence adds caution in this area." if str(confluence.get("direction") or "") == "caution" else
                   "The evidence is mixed in this area."),
        "secondary_confirmations": [
            {
                "method": str(x.get("method") or ""),
                "direction": str(x.get("direction") or ""),
                "strength": str(x.get("strength") or ""),
            }
            for x in list(confluence.get("secondary_confirmations") or [])[:6]
            if isinstance(x, dict)
        ],
    }


def build_area_result(
    pc: dict,
    area: str,
    house: int,
    *,
    today: Optional[date] = None,
    timing_windows: Optional[list[dict]] = None,
    featured_timing: Optional[list[dict]] = None,
    current_headline: str = "",
    current_backing: str = "",
) -> dict[str, Any]:
    """Build the canonical result consumed by every report surface."""
    today = today or date.today()
    import report_confluence as CF

    confluence = CF.build_confluence(pc, area, house, today=today)
    promise = dict(confluence.get("promise") or {})
    activation = dict(confluence.get("activation") or {})
    direction = str(confluence.get("direction") or "mixed")

    windows = _timing_windows(pc, area, house, today, supplied=timing_windows)
    timing = _timing_summary(windows, promise)
    if featured_timing is not None:
        timing["featured_windows"] = [
            w for w in featured_timing if str(w.get("area") or "") == area
        ]
    else:
        timing["featured_windows"] = []

    manifestations = _manifestations(pc, area, promise, activation, today)
    action = _action(pc, area, direction, today)
    remedy = _remedy(
        pc, area, house, direction, str(promise.get("status") or ""))

    # One normalized evidence object for Why, Paid evidence and ReportFacts.
    why = _normalized_why(confluence, area)

    result = {
        "schema": "graharekha.canonical_area_result.v1",
        "area": area,
        "house": house,
        "today": today.isoformat(),
        "direction": direction,
        "score": confluence.get("score", 0),
        "confidence": confluence.get("confidence", "low"),
        "agreement": confluence.get("agreement", "weak"),
        "promise": promise,
        "activation": activation,
        "timing": timing,
        "manifestation": manifestations,
        "action": action,
        "remedy": remedy,
        "why": why,
        "headline": current_headline,
        "backing": current_backing,
        # The renderer may use this object for diagnostics, but no downstream
        # consumer is allowed to mutate the prediction fields.
        "immutable_prediction": True,
    }
    return result


def attach_result_to_confluence(confluence: dict, result: dict) -> dict:
    """Return a presentation-compatible confluence dict backed by one result."""
    out = dict(confluence or {})
    out["canonical_result"] = result
    # Mirror the canonical fields for legacy renderers. Values come from the
    # same object, never a second calculation.
    for key in (
        "direction", "score", "confidence", "agreement", "promise", "activation",
        "timing", "manifestation", "action", "remedy", "why", "headline", "backing",
    ):
        if key in result:
            out[key] = result[key]
    return out
