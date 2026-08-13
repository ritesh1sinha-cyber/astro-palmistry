"""Customer-facing text boundary — raw technique evidence must not reach HTML."""

from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from typing import Optional

from qa_checks.age_context_check import age_violations
from qa_checks.claim_validator import legacy_archetype_banned
from qa_checks.health_safety_check import health_violations, wellbeing_replacement

# Internal / debug / classical fear patterns that must never appear in
# customer copy. Classical case-book stock phrases are treated as leaks
# even when they are grammatically complete English.
_INTERNAL_PATTERNS = [
    re.compile(r"\b(?:(?:\d{1,2}(?:st|nd|rd|th)|1st|2nd|3rd|[4-9]th|1[0-2]th)\s+lord)\b", re.I),
    # "sits" alone is ordinary English — "the mount it sits on", "the window
    # sits in your thirties" — and matching it bare replaced whole customer
    # sentences with the generic fallback. A chart-placement leak has its own
    # grammar: something is doing the sitting, or it is sitting *here*.
    re.compile(
        r"\b(?:rules?\s+it"
        r"|house\s+strength\s+\d+(?:\.\d+)?\s+of\s+\d+"
        r"|(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu|lords?|rulers?)"
        r"\s+sits?\b"
        r"|sits?\s+here\b"
        r"|placed\s+in\s+your\s+\d+(?:st|nd|rd|th))\b",
        re.I,
    ),
    re.compile(r"\b(?:sub[- ]lord|karakamsa|atmakaraka?|cusp)\b", re.I),
    re.compile(r"\b(?:jamakkol|prashna kundali|case-book method|classical rule|technical reason)\b", re.I),
    re.compile(r"\b(?:ninth-part chart|birth-chart promise|confirmation chart|cross-check chart)\b", re.I),
    re.compile(r"\b(?:vimshottari|pratyantardasha)\b", re.I),
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
    re.compile(r"\btraditional\s+chart\s+check(?:\s+check)+\b", re.I),
    re.compile(r"\byour\s+a\s+chart\s+factor\b", re.I),
    re.compile(r"\b(?:in|during)\s+the\s+a\s+chart\s+factor\b", re.I),
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


# Glossed whitelist spans a full-report is allowed to print. Scrubbed from a
# *copy* of the text before leak patterns run, so an ungossed "dasha" still
# replaces the whole node and every other leak pattern keeps full force.
_APPROVED_VEDIC_GLOSS = re.compile(
    r"\b(?:mahadasha|antardasha|dasha|lagna)\s*\(([^)]+)\)",
    re.I,
)


def _scrub_approved_vedic_gloss(text: str) -> str:
    """Replace approved glossed Sanskrit spans with spaces; leave the rest."""

    def repl(m: re.Match) -> str:
        words = re.findall(r"[A-Za-z]{2,}", m.group(1) or "")
        return " " if len(words) >= 3 else m.group(0)

    return _APPROVED_VEDIC_GLOSS.sub(repl, text or "")


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
# Customer-facing technical evidence patterns. These are intentionally broader
# than the upstream rule patterns because legacy appendix renderers may inject
# complete case-book / scoring sentences after canonical facts were built.
# They are presentation leaks, not prediction facts.
_EXTRA_CUSTOMER_LEAK_PATTERNS = [
    re.compile(r"\b(?:[A-Z][a-z]+\s+rules?\s+it|(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)(?:\s*,\s*(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)){0,6}\s+sit(?:s)?\s+here)\b", re.I),
    re.compile(r"\bhouse\s+strength\s+\d+(?:\.\d+)?\s+of\s+\d+(?:\.\d+)?(?:\s*[—-]\s*[^.<>]{0,80})?", re.I),
    re.compile(r"\b\d+\s+classical\s+rules?\s+(?:support|oppose|confirm|reinforce|apply)", re.I),
    re.compile(r"\bclassical\s+rules?\s+(?:support|oppose|confirm|reinforce)", re.I),
    re.compile(r"\b(?:case[- ]book|casebook)\s+(?:confirmation|evidence|reading|example|analysis)\b", re.I),
    re.compile(r"\b(?:personality|characteristics)\s+and\s+(?:characteristics|personality)\b", re.I),
    re.compile(r"\bappearance\s*:\s*[^.<>]{0,180}", re.I),
    re.compile(r"\b(?:technical|classical)\s+(?:detail|rule|rules|count|tests?)\b", re.I),
    re.compile(r"\b(?:Papa[- ]Adhi|Kemadruma|Neecha[- ]Bhanga|Gaja[- ]Kesari|Dhana|Raja|Vipareeta)\s+Yoga\b[^.<>]{0,240}", re.I),
    re.compile(r"\bmalefics?\s*\([^)]{0,80}\)\s+(?:occupy|aspect|sit|fall)\b[^.<>]{0,220}", re.I),
    re.compile(r"\b(?:[A-Z][a-z]+)\s+(?:as|is)\s+the\s+\d+(?:st|nd|rd|th)\s+lord\b[^.<>]{0,180}", re.I),
    re.compile(r"\b(?:from|8th from|7th from|6th from|5th from)\s+the\s+(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\b[^.<>]{0,180}", re.I),
    re.compile(r"\b(?:point[- ]score|strength[- ]score)\s+(?:method|score|count)\b", re.I),
    # Organ-specific astrological health mapping is not customer-safe even when
    # it does not make a diagnosis. Keep the life-area guidance at wellbeing,
    # routine and recovery level.
    re.compile(r"\b(?:watch|focus on|pay attention to|attention to)\s+(?:the\s+)?(?:head|brain|nervous tension|intestines?|gut|assimilation|calves|ankles|circulation|stomach|liver|kidneys?)\b[^.<>]{0,180}", re.I),
    re.compile(r"\b(?:structural|house)\s+strength\b", re.I),
    re.compile(r"\b(?:rule|rules)\s*#?\s*\d+\b", re.I),
    re.compile(r"\b(?:method|technique)\s*[:=-]\s*[A-Za-z][^<]{0,120}", re.I),
    re.compile(r"\btraditional\s+chart\s+check(?:\s+check)+\b", re.I),
    re.compile(r"\byour\s+a\s+chart\s+factor\b", re.I),
]

_DOCUMENT_LEAK_PATTERNS = [
    re.compile(r"\b(?:(?:\d{1,2}(?:st|nd|rd|th)|1st|2nd|3rd|[4-9]th|1[0-2]th)\s+lord)\b", re.I),
    re.compile(r"\b(?:sub[- ]lord|karakamsa|atmakaraka?|cusp)\b", re.I),
    re.compile(r"\b(?:jamakkol|prashna kundali|case-book method|classical rule|technical reason)\b", re.I),
    re.compile(r"\b(?:vimshottari|pratyantardasha|daśā)\b", re.I),
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
    re.compile(r"\btraditional\s+chart\s+check(?:\s+check)+\b", re.I),
    re.compile(r"\byour\s+a\s+chart\s+factor\b", re.I),
    re.compile(r"\b(?:in|during)\s+the\s+a\s+chart\s+factor\b", re.I),
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


def _visible_text_only(html_text: str) -> str:
    """Extract visible text only; ignore scripts, styles and attributes."""
    class _Visible(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.parts = []
            self.raw_depth = 0
        def handle_starttag(self, tag, attrs):
            if tag.lower() in ("script", "style"):
                self.raw_depth += 1
        def handle_endtag(self, tag):
            if tag.lower() in ("script", "style") and self.raw_depth:
                self.raw_depth -= 1
        def handle_data(self, data):
            if not self.raw_depth:
                self.parts.append(data)
    p = _Visible()
    try:
        p.feed(html_text or ""); p.close()
        return " ".join(p.parts)
    except Exception:
        return re.sub(r"<[^>]+>", " ", html_text or "")

def validate_customer_text(html_text: str) -> list[str]:
    """Find raw/internal evidence only in customer-visible text."""
    text = _scrub_approved_vedic_gloss(_visible_text_only(html_text or ""))
    return [pat.pattern for pat in
            [*_DOCUMENT_LEAK_PATTERNS, *_EXTRA_CUSTOMER_LEAK_PATTERNS]
            if pat.search(text)]

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


def _safe_replacement_for_leak(text: str) -> str:
    """Return a complete semantic sentence for a contaminated visible node."""
    t = (text or "").lower()
    if any(k in t for k in ("sub-lord", "sublord", "karakamsa", "atmakaraka", "vimshottari")):
        return "Timing evidence is included in the overall reading."
    if any(k in t for k in ("spouse", "husband", "wife")):
        return "Relationship evidence is expressed without assuming relationship status."
    if any(k in t for k in (
        "health", "stomach", "liver", "kidney", "nervous", "illness",
        "head", "brain", "intestine", "gut", "assimilation", "calves",
        "ankles", "circulation",
    )):
        return "Wellbeing guidance is expressed as general routine and recovery support."
    if any(k in t for k in ("gem", "gemstone", "atmakarak", "5th lord", "9th lord", "lagna lord")):
        return "This remedy is linked to a relevant chart factor."
    return "The chart evidence is summarized in the life-area reading above."


def sanitize_html_document(html_text: str) -> str:
    """Final customer boundary.

    Only visible text nodes are inspected/rewritten.  CSS, JavaScript,
    attributes, embedded JSON and data-* values are left untouched.  If a
    visible node contains raw technical evidence, the whole node is replaced
    with a short semantic sentence rather than attempting fragile partial
    surgery (which previously produced phrases such as "your a chart factor").
    """
    html = html_text or ""
    if not html:
        return html

    # Soft labels first on the full document so HTML entities like &amp; still
    # match across parser text/entity splits (e.g. "Love, Marriage &amp; Emotions").
    for pat, repl in _SOFT_LABEL_REPLACEMENTS:
        html = pat.sub(repl, html)

    class _Boundary(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.out = []
            self.raw_depth = 0

        def handle_starttag(self, tag, attrs):
            if tag.lower() in ("script", "style"):
                self.raw_depth += 1
            self.out.append(self.get_starttag_text() or "")

        def handle_endtag(self, tag):
            self.out.append(f"</{tag}>")
            if tag.lower() in ("script", "style") and self.raw_depth:
                self.raw_depth -= 1

        def handle_startendtag(self, tag, attrs):
            self.out.append(self.get_starttag_text() or f"<{tag}/>")

        def handle_data(self, data):
            if self.raw_depth:
                self.out.append(data)
                return

            value = data
            # Soft customer labels are applied only to visible text nodes.
            for pat, repl in _SOFT_LABEL_REPLACEMENTS:
                value = pat.sub(repl, value)

            # Any raw/internal pattern in a visible node is replaced as a
            # complete semantic node. This prevents malformed hybrid prose.
            # Glossed mahadasha/antardasha/dasha/lagna spans are ignored so a
            # Vedic register can name the running period; ungossed uses still
            # replace the whole node.
            scrubbed = _scrub_approved_vedic_gloss(value)
            if _internal_leak(scrubbed) or any(
                p.search(scrubbed or "") for p in _DOCUMENT_LEAK_PATTERNS + _EXTRA_CUSTOMER_LEAK_PATTERNS
            ):
                value = _safe_replacement_for_leak(value)

            # Remove accidental placeholder tokens even when they originate
            # in an old free teaser template.
            if re.search(r"\bX{3,}\b|XXXX+", value, re.I):
                value = re.sub(
                    r"Your chart reads X{3,} for this question",
                    "Your chart's overall direction is summarized in the full reading",
                    value,
                    flags=re.I,
                )
                value = re.sub(
                    r"The strongest window falls between X{3,} XXXX and X{3,} XXXX[^.]*\.",
                    "The detailed timing windows are available in the full reading.",
                    value,
                    flags=re.I,
                )
                value = re.sub(r"X{3,}\s+XXXX", "the detailed timing window", value)

            self.out.append(value)

        def handle_entityref(self, name):
            self.out.append(f"&{name};")

        def handle_charref(self, name):
            self.out.append(f"&#{name};")

        def handle_comment(self, data):
            self.out.append(f"<!--{data}-->")

    p = _Boundary()
    try:
        p.feed(html)
        p.close()
        return "".join(p.out)
    except Exception:
        return html

