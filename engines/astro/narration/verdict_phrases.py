"""Canonical customer phrases for direction, confidence and agreement.

Renderers must not invent agreement language. Every headline and proof
Overall line reads from this module so they cannot contradict each other.
"""

from __future__ import annotations

from typing import Optional


def _norm_direction(direction: str) -> str:
    d = (direction or "mixed").lower()
    if d in ("up", "support"):
        return "up"
    if d in ("down", "caution"):
        return "down"
    return "mixed"


def _norm_confidence(confidence: str) -> str:
    c = (confidence or "low").lower()
    if c in ("very high", "very_high"):
        return "very high"
    if c in ("high", "moderate", "low"):
        return c
    return "low"


def _norm_agreement(agreement: str) -> str:
    a = (agreement or "weak").lower()
    if a in ("strong", "partial", "conflicting", "weak", "limited"):
        return a
    return "weak"


def overall_picture_phrase(
    *,
    direction: str,
    confidence: str = "",
    agreement: str = "",
    support: int = 0,
    caution: int = 0,
    kind: str = "promise",
    challenge_status: str = "",
) -> str:
    """Primary confluence headline — direction-aware, never inverted."""
    direction = _norm_direction(direction)
    confidence = _norm_confidence(confidence)
    agreement = _norm_agreement(agreement)
    kind = (kind or "promise").lower()
    challenge_status = (challenge_status or "").lower()

    # Challenge (D30 / health) cards must never read as "supportive" when
    # a vulnerability pattern is actually indicated.
    if kind == "challenge" and challenge_status in (
        "strongly_indicated", "indicated",
    ):
        if caution > support:
            return (
                "The stronger evidence leans toward caution, although some "
                "supportive signals remain."
            )
        return (
            "The overall picture is mixed: a challenge pattern is indicated, "
            "so consistency and preventive care matter more than optimism."
        )

    # Visible count majority must not silently contradict a supportive headline.
    if caution > support and direction == "up":
        if agreement in ("weak", "partial", "conflicting") or confidence in (
            "low", "moderate",
        ):
            return (
                "Although more systems show caution by count, the weighted "
                "evidence remains mixed — treat supportive windows carefully."
            )
        return (
            "Although more systems show caution by count, the stronger "
            "weighted evidence remains mixed/supportive."
        )

    if direction == "up":
        if support and caution:
            if agreement == "conflicting":
                return (
                    "The overall picture is supportive in places, although "
                    "several caution signals remain."
                )
            if confidence in ("very high", "high"):
                return "The overall picture leans supportive, with some caution."
            return (
                "The overall picture is supportive, although not all signals agree."
            )
        if confidence in ("very high", "high"):
            return "The overall picture is strongly supportive."
        return "The overall picture is supportive."

    if direction == "down":
        if support and caution:
            if confidence in ("very high", "high"):
                return "The overall picture leans demanding, with some caution."
            return (
                "The overall picture is more demanding, although a few "
                "supportive signals remain."
            )
        if confidence in ("very high", "high"):
            return "The overall picture carries strong caution signals."
        return "The overall picture is more demanding right now."

    if direction == "mixed":
        if support and caution:
            if agreement == "conflicting":
                return (
                    "The picture is mixed: some systems support progress while "
                    "others add pressure."
                )
            return (
                "The overall picture is mixed, with both supportive and "
                "caution signals present."
            )
        if support and not caution:
            return "The overall picture is broadly supportive, although the evidence is mixed."
        if caution and not support:
            return "The overall picture is broadly demanding, although the evidence is mixed."
        if agreement == "conflicting":
            return (
                "The picture is mixed: some systems support progress while "
                "others add pressure."
            )
        if confidence == "low" or agreement == "weak":
            return (
                "There is not enough directional evidence to make a strong call here."
            )
        return "The overall picture is broadly neutral."


def proof_overall_line(
    *,
    direction: str,
    confidence: str = "",
    agreement: str = "",
) -> str:
    """Single Overall sentence for the Why / proof block."""
    direction = _norm_direction(direction)
    agreement = _norm_agreement(agreement)

    if direction == "down":
        if agreement == "strong":
            return "Overall: Caution signals outweigh supportive signals."
        if agreement == "partial":
            return "Overall: The evidence leans toward caution."
        if agreement == "conflicting":
            return "Overall: Mixed evidence with caution in the lead."
        return "Overall: More caution than support in the evidence."

    if direction == "up":
        if agreement == "strong":
            return "Overall: Several independent signals support this area."
        if agreement == "partial":
            return "Overall: Partial agreement — supportive, with some caution."
        if agreement == "conflicting":
            return "Overall: Mixed evidence, although support is still present."
        return "Overall: Supportive evidence, although not unanimous."

    if agreement == "conflicting":
        return "Overall: Mixed evidence."
    if agreement == "weak" or _norm_confidence(confidence) == "low":
        return "Overall: Mixed evidence."
    return "Overall: Partial agreement."


def secondary_confirmation_lines(
    confirmations: list[dict],
    *,
    area_key: str = "",
) -> list[str]:
    """Narrate gated secondary confirmations or the empty fallback."""
    if not confirmations:
        return [
            "Secondary confirmation: No independent timing confirmation was "
            "strong enough to add weight."
        ]
    lines = []
    for entry in confirmations[:2]:
        # Refuse to name a planet unless this entry actually carries one —
        # a confirmation with no backing planet is not independent evidence.
        if not entry.get("planet"):
            continue
        reason = str(entry.get("reason") or "").strip()
        if not reason:
            continue
        strength = str(entry.get("strength") or "").strip()
        tail = f" ({strength} strength)" if strength else ""
        lines.append(f"Secondary confirmation: {reason.rstrip('.')}.{tail}")
    if not lines:
        return [
            "Secondary confirmation: No independent timing confirmation was "
            "strong enough to add weight."
        ]
    return lines


def health_framing(*, caution: int, support: int) -> str:
    """Health-specific overall framing when caution outweighs support."""
    if caution <= support:
        return ""
    return (
        "This is a period to take routine, rest and preventive care more "
        "seriously. The chart shows stronger caution signals than supportive "
        "ones, so the emphasis is on consistency rather than alarm."
    )


def promise_status_label(status: str, kind: str = "promise") -> str:
    """Short customer label for a promise/activation/challenge status.

    `kind` defaults to "promise" so every existing caller keeps its old
    behaviour; pass kind="activation" or kind="challenge" for the other two
    vocabularies (see narration.status_vocab).
    """
    from narration.status_vocab import status_label
    if kind == "promise":
        # Preserve the exact legacy wording used across existing renderers
        # and tests ("Mixed promise", "Limited evidence") rather than the
        # generic vocab strings, which read slightly differently.
        return {
            "strongly_supported": "Strongly supported",
            "supported": "Supported",
            "mixed": "Mixed promise",
            "weak": "Not strongly supported",
            "insufficient_evidence": "Limited evidence",
        }.get((status or "").lower(), "Limited evidence")
    return status_label(status, kind=kind)


def activation_status_label(status: str) -> str:
    """Short customer label for an activation status — never a promise word."""
    return promise_status_label(status, kind="activation")


def challenge_status_label(status: str) -> str:
    """Short customer label for a D30-style challenge-pattern status."""
    return promise_status_label(status, kind="challenge")


def promise_phrase(*, status: str, direction: str = "mixed") -> str:
    """Promise-aware line combining natal promise with current timing direction."""
    status = (status or "insufficient_evidence").lower()
    direction = _norm_direction(direction)

    strong = status in ("strongly_supported", "supported")
    weak = status in ("weak", "insufficient_evidence")

    if strong and direction in ("down", "mixed"):
        return (
            "The underlying promise is supported in your chart, but it is "
            "not strongly activated right now."
        )
    if weak and direction == "up":
        return (
            "There is an opening in timing, although the underlying promise "
            "for this area is limited."
        )

    return {
        "strongly_supported": "This area is strongly supported in your chart.",
        "supported": "This area is supported in your chart.",
        "mixed": "This area shows mixed underlying support.",
        "weak": "This area is not strongly promised; steady effort matters more.",
        "insufficient_evidence": "There is not enough evidence for a strong promise conclusion.",
    }.get(status, "Limited evidence for a strong promise conclusion.")


def promise_proof_line(*, status: str, label: str = "", kind: str = "promise") -> str:
    """One-line promise/challenge summary for the Why / proof block."""
    text = label or promise_status_label(status, kind=kind)
    lead = "Challenge pattern" if kind == "challenge" else "Underlying promise"
    return f"{lead}: {text.rstrip('.')}."


def activation_proof_line(*, status: str) -> str:
    """One-line activation summary for the Why / proof block — never a promise word."""
    return f"Current activation: {activation_status_label(status).rstrip('.')}."


# ---------------------------------------------------------------------------
# promise x activation matrix (P1-17) — one canonical sentence per combination
# ---------------------------------------------------------------------------

def promise_activation_line(*, promise_status: str, activation_status: str) -> str:
    """The single 'what this means' sentence for a promise x activation pair.

    Six buckets, exactly as specified: strong/strong, strong/weak,
    mixed/strong, mixed/weak, weak/strong, weak/weak (mixed/mixed folds into
    the nearest pair). Timing can never upgrade a weak promise into a
    guarantee, and a strong promise is never hidden just because the current
    period is quiet.
    """
    from narration.status_vocab import activation_bucket, promise_bucket

    p = promise_bucket(promise_status)
    a = activation_bucket(activation_status)

    if p == "strong" and a == "strong":
        return (
            "The area is part of your chart's real potential, and the current "
            "period is actively supporting it — this is a genuine opportunity "
            "window."
        )
    if p == "strong" and a == "weak":
        return (
            "The area is part of your chart's potential, but this is not the "
            "strongest phase to expect major results right now."
        )
    if p == "strong":  # mixed activation
        return (
            "The underlying promise is supported, but the current phase "
            "carries more caution than certainty."
        )
    if p == "mixed" and a == "strong":
        return (
            "An opportunity may become active now, but timing is stronger "
            "than the underlying promise — treat it as a chance to evaluate "
            "carefully rather than a guaranteed outcome."
        )
    if p == "mixed" and a == "weak":
        return (
            "Both the underlying promise and the current activation are "
            "modest here, so this is a lower-priority area for now."
        )
    if p == "mixed":  # mixed activation
        return (
            "Both the underlying chart and the current period are mixed on "
            "this area, so results are likely to be partial rather than "
            "one-sided."
        )
    if p == "weak" and a == "strong":
        return (
            "There is an opening in timing, although the underlying promise "
            "for this area is limited — treat this as a temporary window "
            "rather than a lasting pattern."
        )
    return (
        "Neither the underlying chart nor the current period give strong "
        "support here; steady, deliberate effort matters more than waiting "
        "for the right moment."
    )


def challenge_pattern_phrase(*, status: str) -> str:
    """Headline sentence for a D30-style challenge pattern — never promise language."""
    status = (status or "insufficient_evidence").lower()
    return {
        "strongly_indicated": "The chart shows a strongly indicated challenge pattern here.",
        "indicated": "The chart shows an indicated challenge pattern here.",
        "mixed": "The challenge pattern here is mixed.",
        "weak": "There is no strongly indicated challenge pattern here.",
        "insufficient_evidence": (
            "There is not enough evidence for a clear challenge-pattern "
            "conclusion."
        ),
    }.get(status, "There is not enough evidence for a clear challenge-pattern conclusion.")


def challenge_mechanism_line() -> str:
    """Generic, non-alarming mechanism sentence for a challenge-pattern card."""
    return (
        "The main vulnerability is rarely one guaranteed event. Pressure is "
        "more likely to build when responsibility, stress or avoidable "
        "complications accumulate faster than they are addressed."
    )
