"""
Pre-Delivery Automated Palmistry Report Validator.

Enforces production acceptance criteria from Graharekha_Palmistry_Production_Readiness.md:
- No duplicate marks.
- No guaranteed or deterministic claims.
- No pseudo-medical or physiological claims.
- Proper source attribution (no raw 'the classical texts:').
- Inclusion of the healthcare and legal disclaimer.
- Presence of the 'Where You Are Now' executive synthesis.
"""

from __future__ import annotations

import re
from typing import Tuple, List

# Forbidden deterministic phrases
_DETERMINISTIC_PATTERNS = [
    r"\bwill yield outsized\b",
    r"\bguarantees\b",
    r"\bensures that\b",
    r"\bwill definitively\b",
    r"\bwill certainly\b",
]

# Forbidden medical / physiological claims
_MEDICAL_PATTERNS = [
    r"\bmetabolic fire\b",
    r"\bcardiovascular disease\b",
    r"\bdiagnos(?:is|e|ed|ing)\b",
    r"\bcure[s]?\b",
    r"\bmedical treatment\b",
]

# Prohibited legacy source phrasing
_FORBIDDEN_SOURCE_LABELS = [
    r"\bthe classical texts:\b",
]


def validate_report_html(html: str) -> Tuple[bool, List[str]]:
    """Runs all acceptance criteria checks on the generated HTML report."""
    errors: List[str] = []
    
    # 1. Deterministic Language Check
    for pat in _DETERMINISTIC_PATTERNS:
        if re.search(pat, html, re.I):
            errors.append(f"Forbidden deterministic phrase found: '{pat}'")

    # 2. Medical / Health Safety Boundary Check (tested on narrative body outside disclaimer)
    body_content = re.sub(r'<div class="card"[^>]*>.*?Healthcare & Professional Disclaimer.*?</div>', '', html, flags=re.DOTALL | re.IGNORECASE)
    for pat in _MEDICAL_PATTERNS:
        if re.search(pat, body_content, re.I):
            errors.append(f"Forbidden medical/physiological phrase found: '{pat}'")

    # 3. Source Attribution Check
    for pat in _FORBIDDEN_SOURCE_LABELS:
        if re.search(pat, html, re.I):
            errors.append(f"Legacy source label found: '{pat}' (use 'Traditional interpretation' instead)")

    # 4. Duplicate Mark Check
    trident_jupiter_count = len(re.findall(r"trident\s+(?:sign|on\s+your\s+Mount\s+of\s+Jupiter)", html, re.I))
    if trident_jupiter_count > 3:  # 1 in marks, 1 in life areas is normal; >3 indicates duplication across hands
        errors.append(f"Possible duplicate trident markings detected (count: {trident_jupiter_count})")

    # 5. Disclaimer Check
    if "Healthcare & Professional Disclaimer" not in html and "Health & Financial Disclaimer" not in html:
        errors.append("Mandatory healthcare and professional disclaimer is missing.")

    # 6. Executive Overview Check (for paid reports)
    if "data-unlock" not in html and "id=\"sec-now\"" not in html:
        errors.append("Executive overview section 'sec-now' is missing.")

    return len(errors) == 0, errors
