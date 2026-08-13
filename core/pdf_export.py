"""HTML report → PDF for unlocked downloads."""
from __future__ import annotations

import base64
import logging
import re
from io import BytesIO
from typing import Optional

log = logging.getLogger("graharekha.pdf")

_PRINT_CSS = """
@media print {
  .mm-overlay, .present-ask, .recog-ask, .pillbtn, script { display: none !important; }
}
@page { size: A4; margin: 14mm 12mm; }
body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
img { max-width: 100% !important; height: auto !important; }
"""

_DATA_URI_JPEG = re.compile(
    r'(src\s*=\s*")(data:image/(?:jpeg|jpg|png);base64,)([A-Za-z0-9+/=\s]+)(")',
    flags=re.I,
)


def _shrink_embedded_image(b64: str, *, max_edge: int = 720, quality: int = 75) -> str:
    """Downscale a base64 image for PDF — palm overlays are otherwise huge."""
    raw = base64.b64decode(re.sub(r"\s+", "", b64), validate=False)
    if len(raw) < 40_000:
        return b64
    try:
        from PIL import Image

        with Image.open(BytesIO(raw)) as image:
            image = image.convert("RGB")
            image.thumbnail((max_edge, int(max_edge * 1.4)))
            out = BytesIO()
            image.save(out, format="JPEG", quality=quality, optimize=True)
            return base64.b64encode(out.getvalue()).decode("ascii")
    except Exception:  # noqa: BLE001
        return b64


def _prepare_html(html: str) -> str:
    doc = html or ""
    # Drop interactive script so the PDF is static.
    doc = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", doc, flags=re.I)
    doc = _DATA_URI_JPEG.sub(
        lambda m: m.group(1) + "data:image/jpeg;base64,"
        + _shrink_embedded_image(m.group(3)) + m.group(4),
        doc,
    )
    if "</head>" in doc.lower():
        doc = re.sub(
            r"</head>",
            f"<style>{_PRINT_CSS}</style></head>",
            doc,
            count=1,
            flags=re.I,
        )
    else:
        doc = f"<style>{_PRINT_CSS}</style>" + doc
    return doc


def html_to_pdf(html: str, *, base_url: Optional[str] = None) -> bytes:
    """Convert a self-contained report HTML document to PDF bytes."""
    try:
        from weasyprint import HTML  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "PDF export is not available on this server (WeasyPrint missing)."
        ) from e

    doc = _prepare_html(html)
    try:
        return HTML(string=doc, base_url=base_url or "").write_pdf()
    except OSError as e:
        msg = str(e).lower()
        if any(tok in msg for tok in ("pango", "cairo", "gobject", "libg", "cannot load")):
            raise RuntimeError(
                "PDF export is not available on this server "
                "(WeasyPrint system libraries missing)."
            ) from e
        log.exception("WeasyPrint OSError during PDF build")
        raise
    except Exception:
        log.exception("WeasyPrint failed during PDF build")
        raise


KIND_LABELS = {
    "palm": "Palm reading",
    "full_report": "Full report",
    "classical_report": "Classical Vedic report",
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
