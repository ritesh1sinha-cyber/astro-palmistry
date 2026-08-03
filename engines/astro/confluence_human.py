#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plain-English rewrite for confluence client text - no house/cusp jargon."""
from __future__ import annotations

import re

_DROP_SENT_RE = re.compile(
    r"(cusp|sub.?lord|CSL|significator|co-signify|from KL|Karaka|"
    r"Neecha Bhanga|viparita|dusthana|bindu|BAV|SAV|moolatrikona|"
    r"D27|D6|D3 band|kalaka|Goel flags|Step \d+|Mehta Step|"
    r"No planets in \d+(st|nd|rd|th) from KL|star/sub)",
    re.I,
)

_HOUSE_PLAIN = {
    1: "self and body",
    2: "money and family speech",
    3: "courage and siblings",
    4: "home and mother",
    5: "children and creativity",
    6: "health and daily work",
    7: "marriage and partners",
    8: "deep change and shared resources",
    9: "father, faith, and travel",
    10: "career and public name",
    11: "income and friends",
    12: "rest, expenses, and solitude",
}


def _repl_house(m: re.Match) -> str:
    return _HOUSE_PLAIN.get(int(m.group(1)), "that life area")


def _repl_house_from(m: re.Match) -> str:
    n = int(m.group(1))
    return f"from your {_HOUSE_PLAIN.get(n, 'life theme')}"


def _repl_in_house(m: re.Match) -> str:
    n = int(m.group(1))
    return f"in your {_HOUSE_PLAIN.get(n, 'life area')}"


_PHRASES: list[tuple[re.Pattern, str | callable]] = [
    (re.compile(r"\(\s*\d+(st|nd|rd|th)[^)]*\)", re.I), ""),
    (re.compile(r"\b(\d+)(st|nd|rd|th)\s+lord\b", re.I), "life-area ruler"),
    (re.compile(r"\brest, expenses, and solitude lord\b", re.I), "recovery cycles"),
    (re.compile(r"\bhealth and daily work lord\b", re.I), "health pattern"),
    (re.compile(r"\bdeep change and shared resources lord\b", re.I), "transformation pattern"),
    (re.compile(r"\b(\d+)(st|nd|rd|th)\s+house\b", re.I), _repl_house),
    (re.compile(r"\b(\d+)(st|nd|rd|th)\s+from\b", re.I), _repl_house_from),
    (re.compile(r"\bin the (\d+)(st|nd|rd|th)\b", re.I), _repl_in_house),
    (re.compile(r"\b(\d+)(st|nd|rd|th)\b", re.I), _repl_house),
    (re.compile(r"\blagna lord\b", re.I), "chart ruler"),
    (re.compile(r"\blagna\b", re.I), "rising sign"),
    (re.compile(r"\bmahadasha\b", re.I), "major life chapter"),
    (re.compile(r"\bantardasha\b", re.I), "sub-chapter"),
    (re.compile(r"\bdebilitated\b", re.I), "under pressure"),
    (re.compile(r"\bexalted\b", re.I), "very strong"),
    (re.compile(r"\bsignifies the rest, expenses, and solitude\b", re.I), "also links to hidden fatigue"),
    (re.compile(r"\(\s*see conjunction section\s*\)", re.I), ""),
    (re.compile(r"\bnot a diagnosis[^.]*\.?", re.I), ""),
    (re.compile(r"\bIf Dhanesh is a weak and afflicted[^.]*\.?", re.I), ""),
    (re.compile(r"\bstar/sub \([^)]+\)", re.I), ""),
    (re.compile(r"\bLagna star/sub \([^)]+\)", re.I), ""),
    (re.compile(r"\([^)]*cusp[^)]*\)", re.I), ""),
    (re.compile(r"\s{2,}"), " "),
]


def humanize_sentence(s: str) -> str:
    t = s.strip()
    if not t or _DROP_SENT_RE.search(t):
        return ""
    for pat, repl in _PHRASES:
        t = pat.sub(repl, t)
    t = re.sub(r"\(\s*\)", "", t)
    t = re.sub(r"\s+,", ",", t)
    t = re.sub(r"\s+\.", ".", t)
    t = t.strip(" ,;-")
    if len(t) < 25 or re.search(r"\blord - confinement\b", t, re.I):
        return ""
    if t and t[0].islower():
        t = t[0].upper() + t[1:]
    if t[-1] not in ".!?":
        t += "."
    return t


def humanize_prose(text: str, domain: str = "") -> str:
    sents = [humanize_sentence(s) for s in re.split(r"(?<=[.!?])\s+", text or "")]
    sents = [s for s in sents if s]
    if domain == "health" and sents:
        lead = (
            "Your body is not fragile, but it is not automatic either - regular care, sleep, and honest check-ups "
            "matter more than ignoring small signals."
        )
        if lead not in sents[0]:
            sents.insert(0, lead)
    return " ".join(sents)


def health_claim_from_goel(pc: dict) -> list[str]:
    """Build plain-English health/disease lines from Goel disease analysis."""
    try:
        from goel_disease_analysis import analyze_disease_chart
        d = analyze_disease_chart(pc)
    except Exception:
        return []
    if d.get("error"):
        return []

    lines: list[str] = []

    def add(raw: str) -> None:
        p = humanize_sentence(
            raw.replace("primary illness significator", "a recurring health trigger")
            .replace("chronic/crisis health theme", "on-and-off health tests and recovery cycles")
            .replace("constitutional health tension", "your body needs steady routine, not neglect")
            .replace("dusthana health theme", "health needs extra attention during this chapter")
            .replace("confinement/recovery theme", "rest and recovery become important")
        )
        if p and p not in lines:
            lines.append(p)

    for note in d.get("constitutional_baseline", [])[:2]:
        add(note)

    for z in d.get("d27_vulnerability_zones", [])[:2]:
        zone = z.get("zone", "").strip()
        if not zone:
            continue
        sev = "extra care" if z.get("severity") == "high" else "regular check-ups"
        add(
            f"Your constitution often speaks through the {zone.lower()} - "
            f"prevention and {sev} there pay off over time."
        )

    for loc in d.get("d3_localization", [])[:2]:
        ext = loc.get("body_external", "").strip()
        intr = loc.get("body_internal", "").strip()
        if ext or intr:
            parts = [p for p in (ext, intr) if p]
            add(f"When illness flares, {', '.join(parts).lower()} may feel it first.")

    for nc in d.get("nakshatra_clusters", [])[:1]:
        tend = nc.get("tendency", "").strip()
        if tend and len(tend) > 20:
            add(f"Birth-star health pattern: watch for {tend.lower()}.")

    for w in d.get("active_health_periods", [])[:2]:
        rng = w.get("range", w.get("period", ""))
        note = w.get("note", "")
        add(note)
        if rng and rng not in note:
            add(f"This health theme is active through {rng}.")

    for w in d.get("upcoming_health_windows", [])[:1]:
        rng = w.get("range", "")
        note = w.get("note", "")
        if note:
            add(note)
        if rng:
            add(f"A sensitive health window runs {rng}.")

    for item in d.get("d6_disease_type", [])[:1]:
        tone = item.get("tone", "")
        if tone == "chronic":
            add("Illness patterns lean chronic rather than one-day flukes - build habits early.")
        elif tone == "acute/curable":
            add("Acute flare-ups can come suddenly but usually respond when treated promptly.")

    return lines[:10]
