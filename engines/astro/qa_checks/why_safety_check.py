"""Sanitize recognition 'Why' evidence lines — no medical/legacy leaks."""

from __future__ import annotations

from typing import Optional

from qa_checks.age_context_check import age_violations
from qa_checks.claim_validator import legacy_archetype_banned
from qa_checks.customer_text_sanitizer import is_customer_safe, sanitize_why_text
from qa_checks.health_safety_check import health_violations


def why_is_safe(text: str, *, band: str = "adult") -> bool:
    """Return True if why text may ship in recog-why."""
    if not (text or "").strip():
        return False
    if legacy_archetype_banned(text):
        return False
    if health_violations(text):
        return False
    if band and age_violations(text, band):
        return False
    if not is_customer_safe(text, age_band=band):
        return False
    return True


def safe_why_text(
    why: str,
    *,
    band: str = "adult",
    meaning=None,
) -> str:
    """Return sanitized why text or evidence-trace fallback; empty if none safe."""
    from report_language import client_prose

    candidate = client_prose(why or "")
    if why_is_safe(candidate, band=band):
        return candidate

    if meaning and getattr(meaning, "evidence_trace", None):
        safe_bits = []
        area = getattr(meaning, "area", "") or getattr(meaning, "narrative_area", "")
        for bit in meaning.evidence_trace[:4]:
            cleaned = sanitize_why_text(str(bit), band=band, area=area)
            if cleaned and why_is_safe(cleaned, band=band):
                safe_bits.append(cleaned)
        if safe_bits:
            trace = "; ".join(safe_bits)
            if why_is_safe(trace, band=band):
                return client_prose(trace)

    return ""
