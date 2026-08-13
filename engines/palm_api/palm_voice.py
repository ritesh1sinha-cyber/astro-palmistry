"""Palm prediction voice — real-life scenario + one compressed backing line."""

from __future__ import annotations

import html as _html
import re
from dataclasses import dataclass
from typing import Any, Optional

# The mount keeps its own name, with the place on the hand attached so the
# reader can put a finger on it without already knowing palmistry.
MOUNT_PLAIN = {
    "jupiter": "the Mount of Jupiter, under your index finger",
    "saturn": "the Mount of Saturn, under your middle finger",
    "apollo": "the Mount of Apollo, under your ring finger",
    "sun": "the Mount of Apollo, under your ring finger",
    "mercury": "the Mount of Mercury, under your little finger",
    "venus": "the Mount of Venus, the ball of your thumb",
    "moon": "the Mount of Luna, the outer edge of your palm",
    "mars": "the Mars pads, either side of your palm at thumb height",
}

LINE_PLAIN = {
    "life": "your life line",
    "head": "your head line",
    "heart": "your heart line",
    "fate": "your fate line",
    "sun": "your talent line",
    "mercury": "your health or business line",
}

BANNED_PREFIXES = (
    r"As per your ",
    r"Reading for you:\s*",
    r"Looking inside this specific chart:\s*",
)

# Mount and girdle names used to be stripped here. They are the palmist's own
# vocabulary, and deleting them left holes mid-sentence ("On your you have a
# trident") while making the reading sound like a machine describing pads of
# skin. What stays banned is the astrology lane bleeding into a palm reading:
# a hand has no ascendant, and a reader who came for their palm should not be
# told about triplicities.
BANNED_PHRASES = (
    "triplicity",
    "weekday-born",
    "lunar half",
    "ascendant",
    "chart-from-palm",
)


@dataclass
class PalmPrediction:
    scenario: str
    backing: str
    direction: str = "mixed"

    def html(self) -> str:
        s = _html.escape(self.scenario)
        b = _html.escape(self.backing)
        return (
            f'<div class="prediction" data-verdict="{_html.escape(self.direction)}">'
            f'<p class="pred-scenario">{s}</p>'
            f'<p class="pred-why"><b>Why:</b> {b}</p></div>'
        )

    def text_block(self) -> str:
        return f"{self.scenario}\nWhy: {self.backing}"


def _line_name(key: str) -> str:
    return LINE_PLAIN.get(key, f"your {key} line")


def _mount_name(key: str) -> str:
    return MOUNT_PLAIN.get((key or "").lower(), f"the {key} area of your palm")


def compose(*, scenario: str, backing: str, direction: str = "mixed") -> PalmPrediction:
    return PalmPrediction(
        scenario=polish_prose(scenario),
        backing=polish_prose(backing),
        direction=direction,
    )


def polish_prose(text: str) -> str:
    out = (text or "").strip()
    for pat in BANNED_PREFIXES:
        out = re.sub(pat, "", out, flags=re.I)
    for phrase in BANNED_PHRASES:
        out = out.replace(phrase, "")
    out = re.sub(r"\s+", " ", out).strip()
    try:
        from report_language import normalize_sentence_dashes
        out = normalize_sentence_dashes(out)
    except Exception:  # noqa: BLE001
        out = re.sub(r"\s+—\s+", ". ", out)
    return out


def polish_html(html: str) -> str:
    """Strip banned palm jargon from customer HTML."""
    out = html or ""
    for phrase in BANNED_PHRASES:
        out = out.replace(phrase, "")
    for pat in BANNED_PREFIXES:
        out = re.sub(pat, "", out, flags=re.I)
    return out


def format_line_verdict(key: str, age: Optional[int], props: dict) -> PalmPrediction:
    """Prediction-first line reading at an age."""
    props = props or {}
    if key == "life":
        scenario = (
            f"Around age {age}, your vitality and direction enter a meaningful chapter — "
            f"recovery and endurance matter more than speed."
            if age else
            "Your vitality line runs deep — you recover faster than you expect when you rest."
        )
        backing = f"{_line_name(key)} deep" if props.get("depth") == "deep" else _line_name(key)
    elif key == "head":
        scenario = (
            f"Around age {age}, caution or family influence may hold your choices back — "
            f"speak up for what you need."
            if props.get("start_relation") == "merged" and age else
            f"Around age {age}, mental focus and decisions come to the fore."
            if age else
            "You think independently — your mind leads before your circumstances catch up."
        )
        backing = f"{_line_name(key)} merged at start" if props.get("start_relation") == "merged" else _line_name(key)
    elif key == "heart":
        reserved = props.get("start_zone") == "saturn"
        scenario = (
            f"Around age {age}, you lean toward reserved, serious attachment."
            if reserved and age else
            f"Around age {age}, relationship and emotional decisions come to the fore."
            if age else
            "You love with your whole chest when you trust someone."
        )
        backing = _line_name(key)
    elif key == "fate":
        broken = props.get("quality") == "broken"
        scenario = (
            f"Around age {age}, expect a career or life-role change — plan for transition."
            if broken and age else
            f"Around age {age}, your vocation and public life are in focus."
            if age else
            "Your calling line runs clear — steady effort converts into position."
        )
        backing = f"{_line_name(key)} {'broken' if broken else 'clear'}"
    else:
        scenario = f"Around age {age}, an important shift lands in this part of your life." if age else "This line marks a stable pattern in your life."
        backing = _line_name(key)
    return compose(scenario=scenario, backing=backing)


def format_mount_verdict(key: str, level: str, meaning: str) -> PalmPrediction:
    plain = _mount_name(key)
    # .capitalize() would lowercase the mount's own name; only the first letter
    # of the sentence should move.
    opening = plain[:1].upper() + plain[1:]
    scenario = meaning or f"{opening} reads as {level or 'average'}."
    scenario = polish_prose(scenario)
    if not scenario.endswith("."):
        scenario += "."
    backing = f"{plain} {level or 'average'}"
    return compose(scenario=scenario, backing=backing)


def format_mark_verdict(title: str, meaning: str, zone: str = "") -> PalmPrediction:
    loc = _mount_name(zone) if zone else "your palm"
    scenario = meaning or f"A special mark on {loc} modifies how this area plays out in your life."
    backing = f"mark on {loc}"
    return compose(scenario=scenario, backing=backing)


def line_confluence_statement(line_key: str, hand: str, theme: str, pattern: str) -> PalmPrediction:
    line = _line_name(line_key)
    if pattern == "reinforced":
        scenario = f"{line.capitalize()} is consistent on both hands — a stable pattern in your {theme}."
        backing = f"{line} reinforced both hands"
    elif pattern == "developed":
        scenario = (
            f"You have built up your {theme} beyond what you were born with — "
            f"the {hand} hand shows active growth."
        )
        backing = f"{line} stronger on {hand} hand"
    elif pattern == "latent":
        scenario = (
            f"Natural {theme} is there but under-used — reclaim it rather than waiting."
        )
        backing = f"{line} stronger on innate hand"
    else:
        scenario = f"{line.capitalize()} reads clearly on one hand — {theme} is actively expressed now."
        backing = f"{line} one-hand signal"
    return compose(scenario=scenario, backing=backing)


def saraswati_signal(domain: str, scenario: str, backing: str) -> dict[str, Any]:
    """Return a life_aspects point dict with prediction-first text."""
    pred = compose(scenario=scenario, backing=backing)
    return {
        "text": pred.text_block(),
        "direction": "mixed",
        "method": "photo",
    }
