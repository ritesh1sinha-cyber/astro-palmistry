"""Strict output validator for the customer report.

Runs BOTH before HTML rendering (on the CustomerReport JSON) AND after
HTML generation (on the rendered string). Catches internal-data leakage,
placeholder text, sentence corruption, duplicate sections, and more.
"""
from __future__ import annotations

import re
from typing import Any

from .report_schema import CustomerReport


# ---------------------------------------------------------------------------
# Internal data that must NEVER appear in customer HTML
# ---------------------------------------------------------------------------
_INTERNAL_DATA_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"raw_score", re.I),
    re.compile(r"weighted_score", re.I),
    re.compile(r"lane_html", re.I),
    re.compile(r"anchor_log", re.I),
    re.compile(r"confluence_score", re.I),
    re.compile(r"certainty_score", re.I),
    re.compile(r"fact_id[:\s]", re.I),
    re.compile(r"status_enum", re.I),
    re.compile(r"activation_status", re.I),
    re.compile(r"dasha_factor", re.I),
    re.compile(r"varga_factor", re.I),
]

# ---------------------------------------------------------------------------
# Placeholder / fallback text that must NEVER appear in customer HTML
# ---------------------------------------------------------------------------
_PLACEHOLDER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"pending LLM prose", re.I),
    re.compile(r"awaiting humanization", re.I),
    re.compile(r"awaiting llm", re.I),
    re.compile(r"[Tt]his remedy is linked to a relevant chart factor"),
    re.compile(r"[Tt]he chart evidence is summarized in the life-area reading above"),
    re.compile(r"[Tt]iming evidence is included in the overall reading"),
    re.compile(r"[Pp]romised, not yet active"),
    re.compile(r"Raw classical wording", re.I),
    re.compile(r"Existing chart-rule", re.I),
    re.compile(r"internal rule id", re.I),
    re.compile(r"Full analyst working", re.I),
    re.compile(r"\[pending", re.I),
    re.compile(r"\[placeholder", re.I),
    re.compile(r"\[TODO", re.I),
    re.compile(r"\[FIXME", re.I),
    re.compile(r"\[INTERNAL", re.I),
]

# ---------------------------------------------------------------------------
# Sentence corruption patterns
# ---------------------------------------------------------------------------
_CORRUPTION_PATTERNS: list[re.Pattern[str]] = [
    # "Word.word" without a space (true concatenation). A period-space-capital
    # is a normal sentence boundary and must NOT be flagged.
    re.compile(r"[a-z]\.[A-Z]"),
    # Double periods
    re.compile(r"\.\.+"),
    # Period followed by lowercase without space (except common abbreviations)
    re.compile(r"\.\s+[a-z](?!\s*(?:e\.g|i\.e|etc|viz|vs|al|dr|mr|mrs|ms))\b"),
    # Sentence starts with "And" or "But"
    re.compile(r"(?:^|\.\s+)(?:And|But|Or|So|Yet)\s", re.I),
    # "as as" or "the the" type repetition
    re.compile(r"\b(\w+)\s+\1\b", re.I),
]

# Negation / hedging tokens: a guarantee word that appears near one of these
# is compliance language ("rather than a guaranteed outcome", "not a guaranteed
# negative event", "rarely one guaranteed event") and must NOT be flagged.
_NEGATION_PREFIX = re.compile(
    r"\b(not|no|never|rarely|seldom|hardly|scarcely|unlikely|"
    r"without|avoid|rather\s+than|cannot|can't|won't|doesn't|isn't|"
    r"aren't|wasn't|weren't|didn't)\b",
    re.I,
)

# A future-only phrase is only worth flagging when it is not grounded in a
# date or a natal factor. "things will improve by June 2027" is a timed claim,
# not a dangling promise; "things will improve" with nothing after it is.
_DATE_GROUND_RE = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\s+(?:19|20)\d{2}\b",
    re.I,
)

# Duplicate sentence within same text block
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# Future confluence patterns (time-only without evidence)
_FUTURE_ONLY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"will\s+(?:likely|probably|possibly|may)\s+(?:improve|increase|grow|strengthen|decline|decrease|worsen)", re.I),
    re.compile(r"expect\s+(?:a\s+)?(?:improvement|increase|growth|decline|decrease|worsening)", re.I),
    re.compile(r"(?:good|better|excellent|great)\s+(?:year|period|time)\s+ahead\s*$", re.I),
    re.compile(r"things\s+will\s+(?:get|improve|change|better)", re.I),
]

# Banned guarantee patterns for customer output
_GUARANTEE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bwill definitely\b", re.I),
    re.compile(r"\bguaranteed\b", re.I),
    re.compile(r"\bcertain to\b", re.I),
    re.compile(r"\bwill certainly\b", re.I),
    re.compile(r"\byou will\b", re.I),
    re.compile(r"\byou shall\b", re.I),
    re.compile(r"\byou must\b", re.I),
    re.compile(r"\binevitably\b", re.I),
    re.compile(r"\bwithout fail\b", re.I),
]


class ValidationError:
    """Single validation issue."""

    def __init__(self, code: str, message: str, *, section: str = "", severity: str = "error") -> None:
        self.code = code
        self.message = message
        self.section = section
        self.severity = severity  # "error" | "warning"

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "section": self.section,
            "severity": self.severity,
        }

    def __repr__(self) -> str:
        return f"<{self.severity.upper()} {self.code}: {self.message}>"


class ValidationReport:
    """Collects all validation issues."""

    def __init__(self) -> None:
        self.errors: list[ValidationError] = []
        self.warnings: list[ValidationError] = []

    def add(self, err: ValidationError) -> None:
        if err.severity == "warning":
            self.warnings.append(err)
        else:
            self.errors.append(err)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        lines = [f"Errors: {len(self.errors)}, Warnings: {len(self.warnings)}"]
        for e in self.errors:
            lines.append(f"  ERROR [{e.code}] {e.message}")
        for w in self.warnings:
            lines.append(f"  WARN  [{w.code}] {w.message}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }


# ---------------------------------------------------------------------------
# Pre-render validation (on CustomerReport)
# ---------------------------------------------------------------------------

def validate_customer_report(report: CustomerReport) -> ValidationReport:
    """Validate the CustomerReport before HTML rendering."""
    vr = ValidationReport()

    # --- Section A: Meta ---
    if not report.meta.name.strip():
        vr.add(ValidationError("META_NO_NAME", "Subject name is empty", section="meta"))
    if not report.meta.birth_date.strip():
        vr.add(ValidationError("META_NO_BIRTH_DATE", "Birth date is empty", section="meta", severity="warning"))
    if report.meta.access not in ("free", "paid"):
        vr.add(ValidationError("META_BAD_ACCESS", f"Unknown access: {report.meta.access}", section="meta"))

    # --- Section B: Summary ---
    if not report.summary.headline.strip():
        vr.add(ValidationError("SUMMARY_NO_HEADLINE", "Summary headline is empty", section="summary", severity="warning"))
    if not report.summary.opening.strip():
        vr.add(ValidationError("SUMMARY_NO_OPENING", "Summary opening is empty", section="summary", severity="warning"))
    if report.summary.headline:
        _check_text(vr, report.summary.headline, "summary.headline")
    if report.summary.opening:
        _check_text(vr, report.summary.opening, "summary.opening")

    # --- Section C: Life Areas (paid only) ---
    if report.meta.access == "paid":
        if not report.life_areas:
            vr.add(ValidationError("AREAS_EMPTY", "No life areas in paid report", section="life_areas"))

        seen_keys: set[str] = set()
        for i, area in enumerate(report.life_areas):
            prefix = f"area[{i}].{area.key}"
            if area.key in seen_keys:
                vr.add(ValidationError("AREA_DUPLICATE", f"Duplicate area key: {area.key}", section=prefix))
            seen_keys.add(area.key)

            if not area.conclusion.strip():
                vr.add(ValidationError("AREA_NO_CONCLUSION", f"Empty conclusion in {area.key}", section=prefix))
            if not area.interpretation.strip():
                vr.add(ValidationError("AREA_NO_INTERPRETATION", f"Empty interpretation in {area.key}", section=prefix))

            # Check for placeholder text in area prose
            for field_name in ("conclusion", "astrological_basis", "interpretation",
                               "outlook", "timing", "manifestation", "remedy", "transition_note"):
                val = getattr(area, field_name, "")
                if val:
                    _check_text(vr, val, f"{prefix}.{field_name}")

    # --- Section D: Life State ---
    if report.meta.access == "paid":
        if not report.life_state.what_is_on_your_mind:
            vr.add(ValidationError("MIND_NOW_EMPTY", "No 'what is on your mind' items", section="life_state", severity="warning"))
        for i, line in enumerate(report.life_state.what_is_on_your_mind):
            _check_text(vr, line, f"life_state.mind_now[{i}]")

        if not report.life_state.why_this_period_feels_this_way.strip():
            vr.add(ValidationError("WHY_NOW_EMPTY", "Empty why_this_period_feels_this_way", section="life_state", severity="warning"))
        else:
            _check_text(vr, report.life_state.why_this_period_feels_this_way, "life_state.why_now")

        for i, line in enumerate(report.life_state.family_note):
            _check_text(vr, line, f"life_state.family_note[{i}]")

    # --- Section E: Timing ---
    if not report.current_period.vedic_period.strip():
        vr.add(ValidationError("PERIOD_NO_VEDIC", "Empty vedic period", section="current_period", severity="warning"))

    # --- Section F: Closing (paid) ---
    if report.meta.access == "paid":
        if not report.closing_guidance.final_guidance.strip():
            vr.add(ValidationError("CLOSING_NO_GUIDANCE", "Empty final guidance", section="closing_guidance", severity="warning"))
        else:
            _check_text(vr, report.closing_guidance.final_guidance, "closing_guidance")

    return vr


# ---------------------------------------------------------------------------
# Post-render validation (on HTML string)
# ---------------------------------------------------------------------------

def _customer_text(html: str) -> str:
    """Visible customer content: HTML with style/script/tags removed.

    The validator must never scan the stylesheet or script blocks — CSS class
    names like `li.pchip` and values like `flex:1 1` trip sentence-corruption
    heuristics that are only meaningful for prose.

    Block-level tags become sentence boundaries: the change label div
    ``<div class="future-conf-change baseline">baseline</div>`` immediately
    followed by a reason div that also begins "baseline" must not collapse
    into the fake duplicate word "baseline baseline".
    """
    html = re.sub(r"<(?:style|script)\b[^>]*>.*?</(?:style|script)>",
                  " ", html, flags=re.I | re.S)
    html = re.sub(
        r"</?(?:div|p|li|ul|ol|h[1-6]|tr|td|th|section|article|details|"
        r"summary|blockquote|table|br)[^>]*>",
        " \x00 ", html, flags=re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html)


def _flag_guarantee(text: str) -> str | None:
    """First un-negated guarantee phrase in text, or None."""
    for pat in _GUARANTEE_PATTERNS:
        for m in pat.finditer(text):
            # Skip negation/hedging context like "rather than a guaranteed
            # outcome", "not a guaranteed negative event", "rarely one
            # guaranteed event".
            prefix = text[max(0, m.start() - 60):m.start()]
            if _NEGATION_PREFIX.search(prefix):
                continue
            return m.group()
    return None


def validate_rendered_html(html: str) -> ValidationReport:
    """Validate the final HTML string for leakage, placeholders, corruption."""
    vr = ValidationReport()

    if not html or len(html.strip()) < 200:
        vr.add(ValidationError("HTML_TOO_SHORT", f"HTML too short: {len(html)} chars", section="html"))
        return vr

    # Visible customer text only — never scan CSS/JS or tags.
    text = _customer_text(html)

    # Internal data leakage
    for pat in _INTERNAL_DATA_PATTERNS:
        m = pat.search(text)
        if m:
            vr.add(ValidationError(
                "INTERNAL_DATA_LEAK",
                f"Internal data leaked into HTML: {m.group()!r}",
                section="html",
            ))

    # Placeholder / fallback text
    for pat in _PLACEHOLDER_PATTERNS:
        m = pat.search(text)
        if m:
            vr.add(ValidationError(
                "PLACEHOLDER_LEAK",
                f"Placeholder/fallback text in HTML: {m.group()!r}",
                section="html",
            ))

    # Guarantee patterns
    flagged = _flag_guarantee(text)
    if flagged is not None:
        vr.add(ValidationError(
            "GUARANTEE_LEAKED",
            f"Guarantee/certainty language: {flagged!r}",
            section="html",
        ))

    # Future-only time predictions
    for pat in _FUTURE_ONLY_PATTERNS:
        m = pat.search(text)
        if m and not _grounded_future(text, m):
            vr.add(ValidationError(
                "FUTURE_ONLY_PREDICTION",
                f"Time-only prediction without evidence: {m.group()!r}",
                section="html",
                severity="warning",
            ))

    # Duplicate section detection
    _check_duplicate_sections(html, vr)

    # Sentence corruption
    _check_sentence_corruption(html, vr)

    return vr


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _grounded_future(text: str, m: re.Match) -> bool:
    """A future-only phrase is grounded when a date or natal factor appears
    before the next sentence boundary after the match."""
    tail = text[m.end():]
    sentence = _SENTENCE_SPLIT_RE.split(tail, maxsplit=1)[0]
    window = sentence[:120]
    return bool(_DATE_GROUND_RE.search(window))


def _check_text(vr: ValidationReport, text: str, section: str) -> None:
    """Run all text-level checks on a prose string."""
    if not text:
        return

    # Internal data leakage
    for pat in _INTERNAL_DATA_PATTERNS:
        m = pat.search(text)
        if m:
            vr.add(ValidationError(
                "INTERNAL_DATA_LEAK",
                f"Internal data in prose: {m.group()!r}",
                section=section,
            ))

    # Placeholder text
    for pat in _PLACEHOLDER_PATTERNS:
        m = pat.search(text)
        if m:
            vr.add(ValidationError(
                "PLACEHOLDER_LEAK",
                f"Placeholder text in prose: {m.group()!r}",
                section=section,
            ))

    # Guarantee language
    for pat in _GUARANTEE_PATTERNS:
        m = pat.search(text)
        if m:
            vr.add(ValidationError(
                "GUARANTEE_LEAKED",
                f"Guarantee language in prose: {m.group()!r}",
                section=section,
            ))

    # Sentence corruption: check for double periods, missing spaces after periods
    if ".." in text:
        vr.add(ValidationError("SENTENCE_CORRUPTION", "Double period found", section=section))
    # Check for concatenated sentences (period immediately followed by uppercase without space)
    if re.search(r"[a-z]\.[A-Z]", text):
        vr.add(ValidationError("SENTENCE_CORRUPTION", "Missing space after period", section=section))


def _check_duplicate_sections(html: str, vr: ValidationReport) -> None:
    """Detect duplicate major sections in the rendered HTML."""
    # Look for repeated h2/h3 headers
    headers = re.findall(r"<h[23][^>]*>(.*?)</h[23]>", html, re.I | re.S)
    seen: dict[str, int] = {}
    for h in headers:
        clean = re.sub(r"<[^>]+>", "", h).strip()
        if not clean:
            continue
        seen[clean] = seen.get(clean, 0) + 1
    for header, count in seen.items():
        if count > 1:
            vr.add(ValidationError(
                "DUPLICATE_SECTION",
                f"Section '{header}' appears {count} times in HTML",
                section="html",
            ))


def _check_sentence_corruption(html: str, vr: ValidationReport) -> None:
    """Detect sentence corruption in visible text (strip tags first)."""
    text = _customer_text(html)

    for pat in _CORRUPTION_PATTERNS:
        m = pat.search(text)
        if m:
            vr.add(ValidationError(
                "SENTENCE_CORRUPTION",
                f"Sentence corruption: {m.group()!r}",
                section="html",
                severity="warning",
            ))
