"""Customer-facing text boundary — raw technique evidence must not reach HTML."""

from __future__ import annotations

import hashlib
import re
from typing import Optional

from qa_checks.age_context_check import age_violations
from qa_checks.claim_validator import legacy_archetype_banned
from qa_checks.health_safety_check import health_violations, wellbeing_replacement

# Internal / debug / classical fear patterns that must never appear in
# customer copy. Classical case-book stock phrases are treated as leaks
# even when they are grammatically complete English.
_INTERNAL_PATTERNS = [
    re.compile(r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+house|8th lord|9th lord|10th lord|11th lord|12th lord)\b", re.I),
    re.compile(r"\b(?:sub[- ]lord|karakamsa|atmakaraka|cusp|nakshatra|varga|lagna|bhava)\b", re.I),
    re.compile(r"\b(?:jamakkol|prashna kundali|case-book method|classical rule|technical reason)\b", re.I),
    re.compile(r"\b(?:dasha|bhukti|daśā|vimshottari|yogini|chara)\b", re.I),
    re.compile(r"recognition_tag_\w+", re.I),
    re.compile(r"Combination\s+\d+", re.I),
    re.compile(r"\b[A-Z][A-Z_]{4,}_\d+\b"),
    re.compile(r"evidence_trace", re.I),
    re.compile(r"\{[^}]{0,80}\}"),
    re.compile(r"\[[^\]]{0,80}\]"),
    re.compile(r"\b\w+\.\w+\(", re.I),
    re.compile(r"book themes applied", re.I),
    re.compile(r"cusp sub lord", re.I),
    re.compile(r"chronic or serious illness", re.I),
    re.compile(r"\b(?:north|south|east|west)\s+direction\b", re.I),
    re.compile(
        r"\b(?:breast|chest|lungs|ribs|heart|stomach|liver|kidney|"
        r"reproductive|excretory|shoulders|arms)\b.*,"
        r".*\b(?:breast|chest|lungs|ribs|heart|stomach|liver|kidney|"
        r"reproductive|excretory|shoulders|arms)\b",
        re.I,
    ),
    re.compile(r"\b(?:landlord|successful in politics)\b", re.I),
    re.compile(r"\bboo\b", re.I),
    re.compile(r"\b(?:e\.g\.|e\.g)\s*$", re.I),
    re.compile(r"\b(?:house's results get|its house's results)\b", re.I),
    re.compile(r"\byou will be\b", re.I),
    re.compile(r"\byou are healthy, free from enemies\b", re.I),
    re.compile(r"\bdebt-ridden\b", re.I),
    re.compile(r"\bhurt by fire\b", re.I),
    re.compile(r"\bstrong appetite\b", re.I),
    re.compile(r"\bfree from enemies\b", re.I),
    re.compile(r"\baccident is certain\b", re.I),
    re.compile(r"\bExisting chart-rule\b", re.I),
    re.compile(r"\bthe classical rule-book\b", re.I),
    re.compile(r"\bpromised in the sub-lord sense\b", re.I),
    re.compile(r"\bYou are famous, dreamer\b", re.I),
    re.compile(r"\bfree from enemies, wealthy, rich\b", re.I),
    re.compile(r"Love, Marriage & Emotions", re.I),
    re.compile(r"Love & Marriage", re.I),
    re.compile(r"Spouse:\s*", re.I),
    re.compile(r"\b(?:spouse|husband|wife)\b", re.I),
    re.compile(r"Life-area promise", re.I),
    re.compile(r"\bD\d+\s+area ruler\b", re.I),
    re.compile(r"\barea ruler (?:occupies|falls)\b", re.I),
    re.compile(r"when illness flares", re.I),
]

_AREA_MANIFEST_FALLBACK: dict[str, dict[str, list[str]]] = {
    "home": {
        "support": ["domestic_stability", "family_responsibility"],
        "caution": ["family_responsibility", "domestic_stability"],
        "neutral": ["domestic_stability"],
    },
    "health": {
        "support": ["wellbeing", "routine", "energy_management"],
        "caution": ["preventive_attention", "stress_management", "routine"],
        "neutral": ["wellbeing", "routine"],
    },
    "career": {
        "support": ["visibility", "career_responsibility", "responsibility"],
        "caution": ["career_responsibility", "responsibility"],
        "neutral": ["career_responsibility"],
    },
    "money": {
        "support": ["financial_stability", "income", "financial_progress"],
        "caution": ["resource_discipline", "financial_stability"],
        "neutral": ["financial_stability"],
    },
}


def _internal_leak(text: str) -> bool:
    t = text or ""
    for pat in _INTERNAL_PATTERNS:
        if pat.search(t):
            return True
    return False


def _direction_bucket(direction: str) -> str:
    d = (direction or "").lower()
    if d in ("support", "up"):
        return "support"
    if d in ("caution", "down"):
        return "caution"
    return "neutral"


def _method_fallback(method_label: str, direction: str) -> str:
    label = (method_label or "This method").strip()
    bucket = _direction_bucket(direction)
    if bucket == "support":
        verb = "supports"
    elif bucket == "caution":
        verb = "adds caution to"
    else:
        verb = "is broadly neutral for"
    return f"{label} — {verb} this reading."


def _manifestation_sentence(manifest_id: str) -> str:
    try:
        from interpretation.stage_config import manifestation_metadata
        meta = manifestation_metadata(manifest_id) or {}
        meaning = str(meta.get("modern_meaning") or "").strip()
        if meaning:
            return meaning[0].upper() + meaning[1:] + "."
    except Exception:  # noqa: BLE001
        pass
    return ""


def _area_manifestation_fallback(area: str, direction: str, *, seed: str = "") -> str:
    bucket = _direction_bucket(direction)
    ids = (_AREA_MANIFEST_FALLBACK.get(area) or {}).get(bucket) or []
    if not ids:
        return ""
    idx = int(hashlib.md5((seed or area).encode()).hexdigest(), 16) % len(ids)
    for mid in ids[idx:] + ids[:idx]:
        sentence = _manifestation_sentence(mid)
        if sentence:
            return sentence
    return ""


def _health_wellbeing_fallback(*, seed: str = "") -> str:
    try:
        from interpretation.stage_config import health_language_rules
        reps = health_language_rules().get("wellbeing_replacements") or {}
        keys = list(reps.keys()) or ["medical"]
    except Exception:  # noqa: BLE001
        keys = ["medical"]
    idx = int(hashlib.md5((seed or "health").encode()).hexdigest(), 16) % len(keys)
    return wellbeing_replacement(keys[idx])


# Whole-document leak patterns (P0-5) — raw classical/case-book text, rule
# numbers, internal IDs or debug strings that must never reach an HTML page.
_DOCUMENT_LEAK_PATTERNS = [
    re.compile(r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+house|8th lord|9th lord|10th lord|11th lord|12th lord)\b", re.I),
    re.compile(r"\b(?:sub[- ]lord|karakamsa|atmakaraka|cusp|nakshatra|varga|lagna|bhava)\b", re.I),
    re.compile(r"\b(?:jamakkol|prashna kundali|case-book method|classical rule|technical reason)\b", re.I),
    re.compile(r"\b(?:dasha|bhukti|daśā|vimshottari|yogini|chara)\b", re.I),
    re.compile(r"recognition_tag_\w+", re.I),
    re.compile(r"\bCombination\s+\d+\b", re.I),
    re.compile(r"\b[A-Z][A-Z_]{4,}_\d+\b"),
    re.compile(r"\bRule\s*#?\d+\b", re.I),
    re.compile(r"\bevidence_trace\b", re.I),
    re.compile(r'"(?:method_id|rule_id|verdict_id|source_id)"\s*:', re.I),
    re.compile(r"\{'[A-Za-z_]+':"),
    re.compile(r"\bbecause:\s*['\"]"),
    re.compile(r"\bTraceback \(most recent call last\)"),
    re.compile(r"\b\w+Error:\s"),
    re.compile(r"cusp sub lord", re.I),
    re.compile(r"chronic or serious illness", re.I),
    re.compile(r"\blandlord\b", re.I),
    re.compile(r"\bboo\b", re.I),
    re.compile(r"\b(?:e\.g\.|e\.g)\s*$", re.I),
    re.compile(r"\b(?:house's results get|its house's results)\b", re.I),
    re.compile(r"\bdebt-ridden\b", re.I),
    re.compile(r"\bhurt by fire\b", re.I),
    re.compile(r"\bExisting chart-rule\b", re.I),
    re.compile(r"\bthe classical rule-book\b", re.I),
    re.compile(r"\bpromised in the sub-lord sense\b", re.I),
    re.compile(r"\bYou are famous, dreamer\b", re.I),
    re.compile(r"\bfree from enemies, wealthy, rich\b", re.I),
    re.compile(r"Love, Marriage & Emotions", re.I),
    re.compile(r"Love & Marriage", re.I),
    re.compile(r"Spouse:\s*", re.I),
    re.compile(r"\b(?:spouse|husband|wife)\b", re.I),
    re.compile(r"Life-area promise", re.I),
    re.compile(r"\bD\d+\s+area ruler\b", re.I),
]


def validate_customer_text(html_text: str) -> list[str]:
    """Whole-document scan for internal/debug/raw-classical leaks (P0-5).

    Unlike `is_customer_safe`, which gates one fragment before it is
    assembled, this runs on the final rendered HTML as a last-resort net —
    it returns the offending pattern strings rather than raising, so a
    caller can log or fail a build without this import creating a hard
    dependency loop.
    """
    text = html_text or ""
    hits: list[str] = []
    for pat in _DOCUMENT_LEAK_PATTERNS:
        if pat.search(text):
            hits.append(pat.pattern)
    return hits


def is_customer_safe(
    text: str,
    *,
    area: str = "",
    age_band: str = "adult",
) -> bool:
    """Return True if text may appear in customer-facing HTML."""
    if not (text or "").strip():
        return False
    if _internal_leak(text):
        return False
    if legacy_archetype_banned(text):
        return False
    if health_violations(text):
        return False
    if area == "health" and health_violations(text):
        return False
    if age_band and age_violations(text, age_band):
        return False
    return True


def sanitize_customer_text(
    text: str,
    *,
    method_label: str = "",
    direction: str = "",
    area: str = "",
    age_band: str = "adult",
    seed: str = "",
) -> str:
    """Normalize or replace raw evidence before it reaches HTML."""
    raw = (text or "").strip()
    if raw and is_customer_safe(raw, area=area, age_band=age_band):
        return raw

    if area == "health":
        fb = _health_wellbeing_fallback(seed=seed or method_label or raw[:40])
        if fb:
            return fb

    area_fb = _area_manifestation_fallback(area, direction, seed=seed or method_label or raw[:40])
    if area_fb:
        return area_fb

    return _method_fallback(method_label, direction)


def sanitize_why_text(
    text: str,
    *,
    band: str = "adult",
    area: str = "",
) -> str:
    """Sanitize recognition 'Why' lines — strip internal tags entirely."""
    cleaned = sanitize_customer_text(
        text,
        method_label="Chart evidence",
        direction="neutral",
        area=area,
        age_band=band,
        seed=text or "",
    )
    if "recognition_tag_" in cleaned.lower():
        return ""
    return cleaned


# Soft customer-label rewrites. Applied before the hard wipe so titles such as
# "Love, Marriage & Emotions" become "Relationships & Emotions" instead of
# being replaced by the generic summary sentence.
_SOFT_LABEL_REPLACEMENTS = [
    (re.compile(r"Love, Marriage &(?:amp;)? Emotions", re.I), "Relationships & Emotions"),
    (re.compile(r"Love &(?:amp;)? Marriage", re.I), "Relationships & Partnership"),
    (re.compile(r"Spouse:\s*", re.I), "Relationship dynamics: "),
    (re.compile(r"\b(?:spouse|husband|wife)\b", re.I), "partner"),
    (re.compile(r"Life-area promise", re.I), "Underlying promise"),
    (re.compile(r"\bTechnical detail\b", re.I), "Why this is supported"),
]


def sanitize_html_document(html_text: str) -> str:
    """Sanitize known raw rule-book/classical fragments in final HTML.

    Upstream evidence normalization is preferred. This is the final boundary
    for legacy/appendix renderers that can inject old prose after cards have
    already been built. Styles and scripts are preserved unchanged.
    """
    from html.parser import HTMLParser

    html = html_text or ""
    if not html or not validate_customer_text(html):
        return html

    # Rewrite soft labels first so the hard wipe does not erase them wholesale.
    for pat, repl in _SOFT_LABEL_REPLACEMENTS:
        html = pat.sub(repl, html)

    patterns = list(_DOCUMENT_LEAK_PATTERNS) + [
        re.compile(r"\b8th lord\b.*\boccup(?:ies|ied)\b", re.I),
        re.compile(r"\bYou are healthy, free from enemies\b", re.I),
    ]

    class _Boundary(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.out: list[str] = []
            self.raw_depth = 0

        def _unsafe(self, text: str) -> bool:
            return any(p.search(text or "") for p in patterns)

        def handle_starttag(self, tag, attrs):
            raw = self.get_starttag_text() or ""
            if tag.lower() in ("style", "script"):
                self.raw_depth += 1
            self.out.append(raw)

        def handle_endtag(self, tag):
            self.out.append(f"</{tag}>")
            if tag.lower() in ("style", "script") and self.raw_depth:
                self.raw_depth -= 1

        def handle_startendtag(self, tag, attrs):
            self.out.append(self.get_starttag_text() or f"<{tag}/>")

        def handle_data(self, data):
            if self.raw_depth or not self._unsafe(data):
                self.out.append(data)
            else:
                self.out.append(
                    "The chart evidence is summarized in the life-area reading above."
                )

        def handle_entityref(self, name):
            self.out.append(f"&{name};")

        def handle_charref(self, name):
            self.out.append(f"&#{name};")

        def handle_comment(self, data):
            self.out.append(f"<!--{data}-->")

    parser = _Boundary()
    try:
        parser.feed(html)
        parser.close()
        out = "".join(parser.out)
    except Exception:
        return html

    replacements = [
        (re.compile(r"\bthe classical rule-book\b", re.I), "Technical evidence"),
        (re.compile(r"\bTechnical detail\b", re.I), "Why this is supported"),
        (re.compile(r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+house|8th lord|9th lord|10th lord|11th lord|12th lord)\b[^<]{0,140}", re.I),
         "a chart factor connected with this area"),
        (re.compile(r"\b(?:sub[- ]lord|karakamsa|atmakaraka|cusp|nakshatra|varga|lagna|bhava)\b", re.I),
         "secondary chart factor"),
        (re.compile(r"\b(?:jamakkol|prashna kundali|case-book method|classical rule|technical reason)\b", re.I),
         "traditional chart check"),
        (re.compile(r"\b(?:dasha|bhukti|daśā|vimshottari|yogini|chara)\b", re.I),
         "timing period"),

        (re.compile(r"\bpromised in the sub-lord sense\b", re.I),
         "Specialist timing analysis supports this area."),
        (re.compile(r"\bdebt-ridden\b", re.I), "financial pressure"),
        (re.compile(r"\bhurt by fire(?: and accident)?\b", re.I), "avoidable risk"),
        (re.compile(r"\bstrong appetite\b", re.I), "steady routine"),
        (re.compile(r"\bfree from enemies\b", re.I), "fewer avoidable conflicts"),
        (re.compile(r"\bYou are famous, dreamer,\b", re.I),
         "Recognition themes are present."),
        (re.compile(r"Love, Marriage & Emotions", re.I), "Relationships & Emotions"),
        (re.compile(r"Love & Marriage", re.I), "Relationships & Partnership"),
        (re.compile(r"Spouse:\s*", re.I), "Relationship dynamics: "),
        (re.compile(r"\b(?:spouse|husband|wife)\b", re.I), "partner"),
        (re.compile(r"Life-area promise", re.I), "Underlying promise"),
    ]
    for pat, repl in replacements:
        out = pat.sub(repl, out)
    return out
