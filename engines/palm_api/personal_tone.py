"""Second-person phrasing for palm readings (your line, your mount)."""

from __future__ import annotations

import re

MOUNT_LABELS: dict[str, str] = {
    "jupiter": "your Mount of Jupiter",
    "saturn": "your Mount of Saturn",
    "apollo": "your Mount of Sun (Apollo)",
    "mercury": "your Mount of Mercury",
    "mars": "your Mount of Mars",
    "venus": "your Mount of Venus",
    "moon": "your Mount of Moon",
}

LINE_LABELS: dict[str, str] = {
    "life": "your life line",
    "head": "your head line",
    "heart": "your heart line",
    "fate": "your fate line",
    "sun": "your Sun (Apollo) line",
    "mercury": "your Mercury (health) line",
    "marriage": "your marriage / affection line",
    "girdle_of_venus": "your Girdle of Venus",
    "ring_of_solomon": "your Ring of Solomon",
    "children": "your children line(s)",
    "travel": "your travel / restlessness line(s)",
}

FINGER_LABELS: dict[str, str] = {
    "index": "your index finger (Jupiter finger)",
    "middle": "your middle finger (Saturn finger)",
    "ring": "your ring finger (Apollo finger)",
    "pinky": "your little finger (Mercury finger)",
}


def personalize_book_excerpt(text: str) -> str:
    """Shift generic third-person book lines toward the reader where safe."""
    t = re.sub(r"\s+", " ", (text or "")).strip()
    t = re.sub(r"\bthe person\b", "you", t, flags=re.I)
    t = re.sub(r"\ba person\b", "you", t, flags=re.I)
    t = re.sub(r"\bthe individual\b", "you", t, flags=re.I)
    t = re.sub(r"\bhe or she\b", "you", t, flags=re.I)
    t = re.sub(r"\bhis or her\b", "your", t, flags=re.I)
    t = re.sub(r"\btheir\b", "your", t, flags=re.I)
    t = re.sub(r"\bthey\b", "you", t, flags=re.I)
    t = re.sub(r"\bthem\b", "you", t, flags=re.I)
    t = re.sub(r"\bhe\b", "you", t, flags=re.I)
    t = re.sub(r"\bshe\b", "you", t, flags=re.I)
    t = re.sub(r"\bhis\b", "your", t, flags=re.I)
    t = re.sub(r"\bher\b", "your", t, flags=re.I)
    t = re.sub(r"\bhim\b", "you", t, flags=re.I)
    return t


def line_phrase(key: str) -> str:
    return LINE_LABELS.get(key, f"your {key} line")


def mount_phrase(key: str) -> str:
    return MOUNT_LABELS.get(key, f"your Mount of {key.title()}")


def finger_phrase(key: str) -> str:
    return FINGER_LABELS.get(key, f"your {key} finger")
