"""Specificity scoring for past-validation claims."""

from __future__ import annotations

import re

# Vague / reject-level phrases (score 0–1).
LOW_SPEC_RE = re.compile(
    r"\b("
    r"noticeable shift in focus|"
    r"a decision that needed attention|"
    r"things were active|"
    r"something needed attention|"
    r"this part of life was active|"
    r"a noticeable shift|"
    r"decision that needed attention"
    r")\b",
    re.I,
)

# Concrete anchors that raise specificity.
HIGH_ANCHORS = re.compile(
    r"\b("
    r"teacher|mentor|sponsor|senior|network|contact|project|deadline|"
    r"responsibility|recognition|visibility|guidance|sleep|routine|"
    r"energy|study|school|internship|authority|leadership|savings|"
    r"cash.?flow|friendship|conversation|patience|follow-?up|"
    r"opportunity|connection|group|supervisor|classmate|organization|"
    r"persistence|ownership|review|evaluated|introduction|tangible|"
    r"progress|waiting|habit|wellbeing"
    r")\b",
    re.I,
)


def specificity_score(text: str) -> int:
    """0–5 score. Prefer >= 3 for published past events."""
    t = (text or "").strip()
    if not t:
        return 0
    if LOW_SPEC_RE.search(t):
        return 1
    score = 2
    anchors = HIGH_ANCHORS.findall(t)
    score += min(3, len(set(a.lower() for a in anchors)))
    if len(t) >= 60:
        score = min(5, score + 1)
    if "may have" in t.lower() or "may" in t.lower():
        score = min(5, score)  # soft language is fine
    return min(5, score)


def is_specific_enough(text: str, *, minimum: int = 3) -> bool:
    return specificity_score(text) >= minimum


TRANSPARENT_FREE = (
    "This period shows activity in this area. "
    "The full report explains the timing factors behind it."
)

TRANSPARENT_PAID = (
    "The timing is active, but the chart does not provide enough evidence "
    "to describe one specific event with confidence."
)

TRANSPARENT_BULLET_FREE = "activity in this area without a clear single event"

TRANSPARENT_BULLET_PAID = (
    "timing activity without a confidently specific real-world event"
)
