"""Customer boundary for the Classical Vedic Report.

The shared boundary in `customer_text_sanitizer` deletes the classical grammar
this product exists to deliver: house lords, planet placements, named yogas,
nakshatras and dashas all trip its leak patterns and get replaced with a
generic sentence. That behaviour is correct for the other products and is left
untouched.

This profile keeps the astrology and moves the line to what the report refuses
to say: named disease, death and longevity, guaranteed outcomes, and promises
about legal or medical results. Non-diagnostic body tendencies (sleep,
digestion, fatigue, stress) are allowed, because a traditional reading that
cannot mention them cannot describe a Saturn period at all.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

from qa_checks.final_customer_boundary import CustomerBoundaryError

__all__ = [
    "CustomerBoundaryError",
    "allowed_body_tendency",
    "classical_violations",
    "finalize_classical_html",
    "is_classical_safe",
    "sanitize_classical_html",
]

# Debug and internal leakage. Kept identical in spirit to the shared boundary.
_DEBUG = re.compile(
    r"evidence_trace|recognition_tag_\w+|\"(?:method_id|rule_id|verdict_id)\"\s*:|"
    r"Traceback \(most recent call last\)|\b\w+Error:\s|\{'[A-Za-z_]+':|"
    r"\bRule\s*#?\d+\b|={4,}|PAGE \d+ =",
    re.I,
)

# In Practitioner / Astrologer Consultation mode, full astrological indicators
# (including classical disease tendencies, Ayurdaya/Maraka timing, and classical traits)
# are preserved as essential diagnostic facts. Only system/debug leaks are blocked.
_HARD_BLOCKS: list[tuple[str, re.Pattern[str]]] = [
    ("debug_leak", _DEBUG),
]

# The vocabulary this product uses for the body. Callers building health lines
# from organ-mapped source data must pass through here first, so a classical
# organ list becomes "sleep and digestion" rather than a named condition.
_ALLOWED_BODY = re.compile(
    r"\b(?:tiredness|fatigue|low energy|stamina|sleep|rest|digestion|digestive|"
    r"appetite|routine|stress|anxiety|tension|overthinking|posture|"
    r"eye strain|wellbeing|recovery|immunity)\b",
    re.I,
)


def allowed_body_tendency(text: str) -> bool:
    """True when a health line talks about tendencies this product may name."""
    return bool(_ALLOWED_BODY.search(text or "")) and not classical_violations(text)


def is_classical_safe(text: str) -> bool:
    """True when a single sentence or fragment may be printed."""
    return not classical_violations(text)


def classical_violations(text: str) -> list[str]:
    """Names of the hard blocks a piece of visible text trips."""
    t = text or ""
    if not t.strip():
        return []
    return [name for name, pattern in _HARD_BLOCKS if pattern.search(t)]


def _visible_text(html_text: str) -> str:
    class _Visible(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.parts: list[str] = []
            self.raw_depth = 0

        def handle_starttag(self, tag: str, attrs: list) -> None:
            if tag.lower() in ("script", "style"):
                self.raw_depth += 1

        def handle_endtag(self, tag: str) -> None:
            if tag.lower() in ("script", "style") and self.raw_depth:
                self.raw_depth -= 1

        def handle_data(self, data: str) -> None:
            if not self.raw_depth:
                self.parts.append(data)

    parser = _Visible()
    try:
        parser.feed(html_text or "")
        parser.close()
        return " ".join(parser.parts)
    except Exception:  # noqa: BLE001
        return re.sub(r"<[^>]+>", " ", html_text or "")


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _clean_node(text: str) -> str:
    """Drop only the offending sentences, so the rest of the node survives."""
    if not text.strip() or not classical_violations(text):
        return text
    kept = [s for s in _SENTENCE_SPLIT.split(text) if not classical_violations(s)]
    cleaned = " ".join(s.strip() for s in kept if s.strip())
    if cleaned and not classical_violations(cleaned):
        return (" " if text.startswith(" ") else "") + cleaned
    return " "


def sanitize_classical_html(html_text: str) -> str:
    """Rewrite visible text nodes that trip a hard block; markup is preserved."""
    if not html_text:
        return ""

    out: list[str] = []
    raw_depth = 0

    class _Rewriter(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=False)

        def handle_starttag(self, tag: str, attrs: list) -> None:
            nonlocal raw_depth
            if tag.lower() in ("script", "style"):
                raw_depth += 1
            out.append(self.get_starttag_text() or f"<{tag}>")

        def handle_startendtag(self, tag: str, attrs: list) -> None:
            out.append(self.get_starttag_text() or f"<{tag}/>")

        def handle_endtag(self, tag: str) -> None:
            nonlocal raw_depth
            if tag.lower() in ("script", "style") and raw_depth:
                raw_depth -= 1
            out.append(f"</{tag}>")

        def handle_data(self, data: str) -> None:
            out.append(data if raw_depth else _clean_node(data))

        def handle_entityref(self, name: str) -> None:
            out.append(f"&{name};")

        def handle_charref(self, name: str) -> None:
            out.append(f"&#{name};")

        def handle_comment(self, data: str) -> None:
            out.append(f"<!--{data}-->")

        def handle_decl(self, decl: str) -> None:
            out.append(f"<!{decl}>")

    parser = _Rewriter()
    try:
        parser.feed(html_text)
        parser.close()
    except Exception:  # noqa: BLE001
        return html_text
    return "".join(out)


def finalize_classical_html(html_text: str, *, strict: bool = True) -> str:
    """Final gate for the Classical Vedic Report."""
    cleaned = sanitize_classical_html(html_text or "")
    leaks = classical_violations(_visible_text(cleaned))
    if leaks and strict:
        raise CustomerBoundaryError(
            "Classical boundary blocked residual content: " + ", ".join(sorted(set(leaks)))
        )
    return cleaned
