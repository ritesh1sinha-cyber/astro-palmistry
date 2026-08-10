"""Trajectory / direction tone consistency — flag contradictory polarity."""

from __future__ import annotations

import re

_POSITIVE = re.compile(
    r"\b("
    r"improv(?:e|ing|es)|strengthen(?:ing|s)?|build(?:ing|s)?|"
    r"easier|smooth(?:er|ly)?|favour(?:able|ed|s)?|"
    r"opens?|progress(?:es|ing)?|supportive|"
    r"everything is easy|all is well|no problem"
    r")\b",
    re.I,
)

_NEGATIVE = re.compile(
    r"\b("
    r"deteriorat(?:e|ing|es)|worsen(?:ing|s)?|declin(?:e|ing|es)|"
    r"likely to fail|break down|collapse|"
    r"everything is easy|unlikely to improve|"
    r"more demanding|requires caution|slower|harder|"
    r"pressure|strain|delay(?:ed|s)?"
    r")\b",
    re.I,
)


def _polarity(text: str) -> str:
    """Return positive, negative, or neutral tone bucket."""
    t = text or ""
    pos = len(_POSITIVE.findall(t))
    neg = len(_NEGATIVE.findall(t))
    if pos > neg and pos >= 1:
        return "positive"
    if neg > pos and neg >= 1:
        return "negative"
    return "neutral"


def trajectory_contradiction(
    direction: str,
    *texts: str,
) -> list[str]:
    """Return list of contradiction labels for direction vs rendered strings."""
    d = (direction or "mixed").lower()
    if d not in ("up", "mixed", "down", "supportive", "challenging"):
        d = "mixed"
    if d in ("supportive", "up"):
        expected = "positive"
        forbidden = "negative"
    elif d in ("challenging", "down"):
        expected = "negative"
        forbidden = "positive"
    else:
        return []

    hits: list[str] = []
    for i, text in enumerate(texts):
        if not text:
            continue
        pol = _polarity(text)
        if d in ("supportive", "up") and pol == forbidden:
            hits.append(f"text_{i}:positive_direction_negative_tone")
        elif d in ("challenging", "down") and pol == forbidden:
            hits.append(f"text_{i}:negative_direction_positive_tone")
    return hits


def has_trajectory_contradiction(direction: str, *texts: str) -> bool:
    return bool(trajectory_contradiction(direction, *texts))
