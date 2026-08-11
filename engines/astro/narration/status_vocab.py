"""Single source for the promise / activation / challenge status vocabularies.

Every module that needs a customer-facing status word reads it from here so
"strongly supported" cannot drift into a different spelling in one renderer
while another still says "Strongly Supported". Three separate vocabularies
exist because they answer three separate questions:

    PROMISE    -- is this part of the person's underlying chart potential?
    ACTIVATION -- is that promise active in the current period?
    CHALLENGE  -- is a vulnerability/challenge pattern indicated? (D30 areas)

CHALLENGE deliberately never borrows PROMISE words ("supported") — a
strongly indicated challenge pattern must never read like a promised event.
"""

from __future__ import annotations

PROMISE_STATUS = (
    "strongly_supported", "supported", "mixed", "weak", "insufficient_evidence",
)
ACTIVATION_STATUS = (
    "strongly_active", "active", "mixed", "weak", "inactive", "insufficient_evidence",
)
CHALLENGE_STATUS = (
    "strongly_indicated", "indicated", "mixed", "weak", "insufficient_evidence",
)

_PROMISE_LABELS = {
    "strongly_supported": "Strongly supported",
    "supported": "Supported",
    "mixed": "Mixed",
    "weak": "Not strongly supported",
    "insufficient_evidence": "Not enough evidence for a strong conclusion",
}

_ACTIVATION_LABELS = {
    "strongly_active": "Strongly active",
    "active": "Active",
    "mixed": "Mixed",
    "weak": "Low activation",
    "inactive": "Not currently active",
    "insufficient_evidence": "Not enough evidence for a strong conclusion",
}

_CHALLENGE_LABELS = {
    "strongly_indicated": "Strongly indicated",
    "indicated": "Indicated",
    "mixed": "Mixed",
    "weak": "Not strongly indicated",
    "insufficient_evidence": "Not enough evidence for a strong conclusion",
}

_TABLES = {
    "promise": _PROMISE_LABELS,
    "activation": _ACTIVATION_LABELS,
    "challenge": _CHALLENGE_LABELS,
}


def status_label(status: str, kind: str = "promise") -> str:
    """Customer-facing label for one status word in one vocabulary."""
    table = _TABLES.get(kind, _PROMISE_LABELS)
    return table.get((status or "").lower(), table["insufficient_evidence"])


def promise_bucket(status: str) -> str:
    """Collapse any promise/challenge status into strong / mixed / weak."""
    s = (status or "").lower()
    if s in ("strongly_supported", "strongly_indicated"):
        return "strong"
    if s in ("supported", "indicated"):
        return "strong"
    if s == "mixed":
        return "mixed"
    return "weak"


def activation_bucket(status: str) -> str:
    """Collapse any activation status into strong / mixed / weak."""
    s = (status or "").lower()
    if s in ("strongly_active", "active"):
        return "strong"
    if s == "mixed":
        return "mixed"
    return "weak"
