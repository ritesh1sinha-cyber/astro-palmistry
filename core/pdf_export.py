"""HTML report → PDF for unlocked downloads."""
from __future__ import annotations

import re
from typing import Optional


_PRINT_CSS = """
@media print {
  .mm-overlay, .present-ask, .recog-ask, .pillbtn, script { display: none !important; }
}
@page { size: A4; margin: 14mm 12mm; }
body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
"""


def html_to_pdf(html: str, *, base_url: Optional[str] = None) -> bytes:
    """Convert a self-contained report HTML document to PDF bytes."""
    try:
        from weasyprint import HTML  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "PDF export is not available on this server (WeasyPrint missing)."
        ) from e

    doc = html or ""
    # Drop interactive script so the PDF is static.
    doc = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", doc, flags=re.I)
    if "</head>" in doc.lower():
        # Case-insensitive inject before </head>
        doc = re.sub(
            r"</head>",
            f"<style>{_PRINT_CSS}</style></head>",
            doc,
            count=1,
            flags=re.I,
        )
    else:
        doc = f"<style>{_PRINT_CSS}</style>" + doc
    return HTML(string=doc, base_url=base_url or "").write_pdf()


KIND_LABELS = {
    "palm": "Palm reading",
    "full_report": "Full report",
    "horary": "Horary",
    "user_question": "Ask your chart",
    "numerology": "Numerology",
    "daily": "Daily reading",
    "kundali_match": "Kundali matching",
    "muhurat": "Muhurat",
    "btr": "Birth time rectification",
}


def report_title(kind: str, meta: Optional[dict] = None) -> str:
    """Short human title for My Reports list."""
    m = meta if isinstance(meta, dict) else {}
    label = KIND_LABELS.get(kind or "", (kind or "Report").replace("_", " ").title())
    name = (m.get("name") or m.get("personName")
            or (m.get("couple") or {}).get("groom") or "")
    q = (m.get("question") or m.get("q") or "")[:80]
    if kind == "daily" and m.get("date"):
        return f"{label} · {m.get('date')}"
    if kind == "kundali_match":
        couple = m.get("couple") or {}
        g, b = couple.get("groom") or "", couple.get("bride") or ""
        if g and b:
            return f"{label} · {g} & {b}"
    if q:
        return f"{label} · {q}"
    if name:
        return f"{label} · {name}"
    return label


def entitlement_item_for_kind(kind: str) -> str:
    """Map stored report kind → billing entitlement item."""
    return {
        "palm": "palm_full",
        "numerology": "numerology_full",
        "daily": "daily",
    }.get(kind or "", kind or "")
