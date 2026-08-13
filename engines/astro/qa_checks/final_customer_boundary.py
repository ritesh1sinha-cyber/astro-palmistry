"""Mandatory final customer/LLM evidence firewall."""
from __future__ import annotations
from .customer_text_sanitizer import sanitize_html_document, validate_customer_text

class CustomerBoundaryError(RuntimeError):
    pass

def finalize_customer_html(html: str, *, strict: bool = True) -> str:
    cleaned = sanitize_html_document(html or "")
    leaks = validate_customer_text(cleaned)
    if leaks and strict:
        raise CustomerBoundaryError(f"Customer evidence firewall blocked {len(leaks)} residual leak pattern(s).")
    return cleaned

def assert_customer_html_safe(html: str) -> None:
    leaks = validate_customer_text(html or "")
    if leaks:
        raise CustomerBoundaryError(f"Customer evidence firewall found {len(leaks)} residual leak pattern(s).")
