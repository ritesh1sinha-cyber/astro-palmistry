"""Paid-only Promise Dashboard — one glance across all eight product cards.

Four groupings (P3), computed purely from the promise/activation objects
each card already carries. No new scoring happens here; this is a different
view of the same canonical result, which is why free and paid never
disagree about what a card actually says (P2-6).
"""

from __future__ import annotations

import html as _html
from typing import Any


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def _bucket_for(card: Any) -> str:
    cf = getattr(card, "confluence", None) or {}
    promise = cf.get("promise") or {}
    activation = cf.get("activation") or {}
    from narration.status_vocab import activation_bucket, promise_bucket

    p = promise_bucket(str(promise.get("status") or ""))
    a = activation_bucket(str(activation.get("status") or ""))
    kind = str(promise.get("kind") or "promise")

    if kind == "challenge":
        # A weak/absent challenge is good news — never call it "strongest".
        # An indicated challenge always needs care, whether or not timing
        # is currently lighting it up.
        if p == "strong":
            return "needs_care"
        if p == "mixed":
            return "needs_care" if a in ("strong", "mixed") else "promised_not_active"
        return "promised_not_active"

    if p == "strong" and a == "strong":
        return "strongest"
    if a == "strong" and p in ("mixed", "weak"):
        return "currently_activated"
    if p in ("strong", "mixed") and a == "weak":
        return "promised_not_active"
    if p == "weak":
        return "needs_care"
    return "promised_not_active"


_GROUP_META = {
    "strongest": (
        "Strongest promises",
        "The underlying chart and the current period both support these.",
    ),
    "currently_activated": (
        "Currently activated",
        "The current period is favourable, even though the underlying "
        "promise here is more modest.",
    ),
    "promised_not_active": (
        "Promised, but not active yet",
        "The chart genuinely supports these — the right period has not "
        "arrived, so patience matters more than doubt.",
    ),
    "needs_care": (
        "Areas needing care",
        "Weaker underlying support, or an indicated challenge pattern — "
        "steady effort and any applicable remedy matter more than waiting "
        "for timing alone.",
    ),
}

_ORDER = ("strongest", "currently_activated", "promised_not_active", "needs_care")


def build(cards: list) -> dict[str, list]:
    """Group up to eight product cards into the four dashboard buckets."""
    groups: dict[str, list] = {k: [] for k in _ORDER}
    for c in cards:
        if not (getattr(c, "confluence", None) or {}).get("promise"):
            continue
        groups.setdefault(_bucket_for(c), []).append(c)
    return groups


def render(cards: list) -> str:
    """Paid-only dashboard HTML, or '' if there is nothing to group."""
    if not cards:
        return ""
    groups = build(list(cards)[:8])
    if not any(groups.values()):
        return ""
    sections = []
    for key in _ORDER:
        items = groups.get(key) or []
        if not items:
            continue
        title, note = _GROUP_META[key]
        li = "".join(f"<li>{_e(getattr(c, 'label', ''))}</li>" for c in items)
        sections.append(
            f'<div class="dash-group"><h4>{_e(title)}</h4>'
            f'<p class="dash-note">{_e(note)}</p><ul>{li}</ul></div>'
        )
    if not sections:
        return ""
    return (
        '<h3 class="sec">Your life promises</h3>'
        '<p class="sec-note">One glance across every life area — where your '
        'chart is strongest, where it is active right now, and where more '
        'care helps.</p>'
        f'<div class="dashboard-grid">{"".join(sections)}</div>'
    )
