"""Report consistency linter — catch contradictions before HTML ships."""

from __future__ import annotations

import re
from typing import Any

_FORBIDDEN_LEAKS = [
    # Naming the house a reading rests on is part of the grounded voice; naming
    # a house *lord* is still internal grammar and stays blocked.
    re.compile(r"\b\d{1,2}(?:st|nd|rd|th)\s+lord\b", re.I),
    # "nakshatra" and "lagna" are named on purpose now that the reports ground
    # their Vedic vocabulary; the internal-only terms below stay blocked.
    re.compile(r"\b(?:sub[- ]lord|karakamsa|atmakaraka|cusp)\b", re.I),
    re.compile(r"\b(?:jamakkol|prashna kundali|case-book method|technical reason)\b", re.I),
    re.compile(r"recognition_tag_", re.I),
    re.compile(r"Combination\s+\d+", re.I),
    re.compile(r"\blandlord\b", re.I),
    re.compile(r"chronic or serious illness", re.I),
    re.compile(r"cusp sub lord", re.I),
    re.compile(r"\bdebt-ridden\b", re.I),
    re.compile(r"\bhurt by fire\b", re.I),
    re.compile(r"\bExisting chart-rule\b", re.I),
    re.compile(r"\bthe classical rule-book\b", re.I),
    re.compile(r"\bpromised in the sub-lord sense\b", re.I),
    re.compile(r"\bYou are famous, dreamer\b", re.I),
    re.compile(r"\bfree from enemies, wealthy, rich\b", re.I),
    re.compile(r"\bD\d+\s+area ruler\b", re.I),
    re.compile(r"\bLife-area promise\b", re.I),
]

_GRAMMAR = [
    re.compile(r"\ba a\b", re.I),
    re.compile(r"\ban an\b", re.I),
    re.compile(r"\bthe the\b", re.I),
]

_HEALTH_FORBIDDEN = [
    re.compile(r"you will have\b", re.I),
    re.compile(r"heart disease", re.I),
    re.compile(r"serious illness is indicated", re.I),
]

# P0-3: the D30 / troubles area must speak in challenge-pattern vocabulary,
# never in promise vocabulary — "strongly supported" there literally reads
# as "illness is strongly promised".
_CHALLENGE_LEAK = re.compile(r"strongly supported in your chart", re.I)
_HEALTH_CARD = re.compile(r'<article class="card"[^>]*data-verdict="[^"]*"[^>]*>.*?</article>', re.S)

# P0-1: "Underlying promise" / "Challenge pattern" and "Overall picture"
# describe different questions and must not silently contradict.
_PROMISE_LINE = re.compile(
    r"(?:Underlying promise|Challenge pattern|Life-area promise):\s*([^<]{0,80})",
    re.I,
)
_OVERALL_LINE = re.compile(r"<strong>([^<]{0,120})</strong>", re.I)
_RECONCILE_CLAUSE = re.compile(
    r"although more systems show caution|stronger evidence leans toward caution|"
    r"weighted evidence remains mixed",
    re.I,
)
_SUPPORTIVE_HEADLINE = re.compile(
    r"overall picture (?:is|leans)(?:\s+strongly)?\s+supportive",
    re.I,
)


def _card_blocks(html: str) -> list[str]:
    return re.findall(r'<article class="card"[^>]*>.*?</article>', html or "", re.S)


_STYLE_SCRIPT = re.compile(r"<(style|script)\b.*?</\1>", re.S | re.I)


def validate_report_consistency(
    html: str,
    verdicts: list[dict] | None = None,
) -> dict[str, Any]:
    """Run pre-publish checks. Returns {ok, failures, warnings}."""
    failures: list[str] = []
    warnings: list[str] = []
    # <style>/<script> blocks are stripped first — CSS words like "stroke"
    # (SVG stroke-width) or "organ" (organic-*) are not customer prose and
    # must never trip the health/leak checks below.
    text = _STYLE_SCRIPT.sub(" ", html or "")

    for pat in _FORBIDDEN_LEAKS:
        if pat.search(text):
            failures.append(f"raw leak: {pat.pattern}")

    for pat in _GRAMMAR:
        if pat.search(text):
            failures.append(f"grammar defect: {pat.pattern}")

    for pat in _HEALTH_FORBIDDEN:
        if pat.search(text):
            failures.append(f"health unsafe: {pat.pattern}")

    try:
        from qa_checks.health_safety_check import health_violations
        hv = health_violations(text)
        if hv:
            failures.append(f"health unsafe: {hv[0]}")
    except Exception:  # noqa: BLE001
        pass

    try:
        from qa_checks.customer_text_sanitizer import validate_customer_text
        for leak in validate_customer_text(text):
            failures.append(f"customer leak: {leak}")
    except Exception:  # noqa: BLE001
        pass

    if "Overall: Strong agreement." in text:
        warnings.append("legacy Overall: Strong agreement still present")

    if re.search(r"Another timing method also points toward", text, re.I):
        warnings.append("ungated secondary confirmation phrasing")

    for verdict in verdicts or []:
        direction = str(verdict.get("direction") or "")
        if direction == "down":
            if "leans supportive" in text.lower() and "health" in text.lower():
                failures.append("health direction contradicts supportive headline")

    for block in _card_blocks(text):
        is_health_card = ">Health &amp; Energy<" in block or ">Health & Energy<" in block
        if is_health_card and _CHALLENGE_LEAK.search(block):
            failures.append(
                "health card uses promise vocabulary ('strongly supported') "
                "instead of a challenge pattern"
            )
        if is_health_card and re.search(
            r"health is strongly promised|disease is promised", block, re.I
        ):
            failures.append("health card uses deterministic disease-promise language")

        # caution_count > support_count must not pair with a bare supportive
        # headline unless a reconciliation clause is present.
        count_m = re.search(
            r"(\d+)\s+support\s*[·•]\s*(\d+)\s+caution", block, re.I,
        )
        overall_m = _OVERALL_LINE.search(block)
        if count_m and overall_m:
            support_n, caution_n = int(count_m.group(1)), int(count_m.group(2))
            o_word = overall_m.group(1)
            # Only flag headlines that *lead* with supportive — not
            # demanding/caution headlines that mention residual support.
            if (
                caution_n > support_n
                and _SUPPORTIVE_HEADLINE.search(o_word)
                and not _RECONCILE_CLAUSE.search(block)
            ):
                failures.append(
                    "caution count exceeds support but overall picture is "
                    "supportive without a reconciliation clause"
                )

        promise_m = _PROMISE_LINE.search(block)
        if promise_m and overall_m:
            p_word = promise_m.group(1).lower()
            o_word = overall_m.group(1).lower()
            if (
                "mixed" in p_word
                and "leans supportive" in o_word
                and "Current activation" not in block
            ):
                warnings.append(
                    "promise and overall-picture read differently in the same "
                    "card without an explanatory activation line between them"
                )
        if is_health_card and promise_m:
            if "challenge pattern" not in block.lower() and "strongly indicated" in (
                promise_m.group(1).lower()
            ):
                failures.append("health card missing Challenge pattern label")

    # Canonical-result contract checks: when callers provide the canonical
    # object, all report surfaces must have the same prediction layers.
    for verdict in verdicts or []:
        cr = verdict.get("canonical_result") if isinstance(verdict, dict) else None
        if cr:
            required = (
                "promise", "activation", "timing", "manifestation",
                "action", "remedy", "why",
            )
            missing = [k for k in required if k not in cr]
            if missing:
                failures.append("canonical result missing: " + ", ".join(missing))
            if (cr.get("timing") or {}).get("timing_can_create_promise") is not False:
                failures.append("canonical timing is allowed to create promise")

    dupes = _duplicate_predictions(text)
    if dupes:
        warnings.extend(f"duplicate prediction: {d}" for d in dupes[:3])

    return {
        "ok": not failures,
        "failures": failures,
        "warnings": warnings,
    }


def _duplicate_predictions(text: str) -> list[str]:
    """Find repeated major sentences (simple exact dup check)."""
    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"<[^>]+>", " ", text))
    seen: dict[str, int] = {}
    dupes: list[str] = []
    for s in sentences:
        key = re.sub(r"\s+", " ", s.strip().lower())
        if len(key) < 40:
            continue
        seen[key] = seen.get(key, 0) + 1
        if seen[key] == 2:
            dupes.append(s.strip()[:80])
    return dupes
