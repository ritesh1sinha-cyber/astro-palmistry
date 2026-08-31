"""HTML report → PDF for unlocked downloads."""
from __future__ import annotations

import base64
import html as _html
import logging
import re
from io import BytesIO
from typing import Any, Optional

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
    language = str(m.get("language") or "").lower().strip()
    if kind == "full_report" and language in ("hi_en", "hinglish", "hi", "hindi"):
        label = "Poori Kundli Reading"
    elif kind == "full_report" and language in ("te_en", "tenglish", "te", "telugu"):
        label = "Sampoorna Kundali Reading"
    elif kind == "palm" and language in ("hi_en", "hinglish", "hi", "hindi"):
        label = "Hast Rekha Reading"
    elif kind == "palm" and language in ("te_en", "tenglish", "te", "telugu"):
        label = "Hasta Rekha Reading"
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


# ---------------------------------------------------------------------------
# Plain-English summary → cover page / standalone document
# ---------------------------------------------------------------------------
_SUMMARY_CSS = """
.gr-sum{font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;
  color:#16181d;max-width:640px;margin:0 auto;padding:8mm 0 4mm;line-height:1.55}
.gr-sum .gr-sum-eyebrow{font-size:.68rem;letter-spacing:.16em;text-transform:uppercase;
  color:#8a6a1f;font-weight:600;margin:0 0 8px}
.gr-sum h1{font-family:Fraunces,Georgia,serif;font-size:1.7rem;line-height:1.15;
  font-weight:600;letter-spacing:-.015em;margin:0 0 6px;color:#16181d}
.gr-sum .gr-sum-sub{font-size:.82rem;color:#6a7080;margin:0 0 18px}
.gr-sum .gr-sum-lead{font-family:Fraunces,Georgia,serif;font-size:1.12rem;line-height:1.4;
  color:#16181d;border-left:3px solid #c8a44a;padding:2px 0 2px 14px;margin:0 0 20px}
.gr-sum section{margin:0 0 16px;page-break-inside:avoid}
.gr-sum section h2{font-family:Fraunces,Georgia,serif;font-size:1.02rem;font-weight:600;
  margin:0 0 5px;color:#16181d}
.gr-sum section p{margin:0;font-size:.92rem;color:#2a2e38}
.gr-sum .gr-sum-note{margin:20px 0 0;padding-top:12px;border-top:1px solid #e6e4df;
  font-size:.78rem;color:#6a7080}
.gr-sum-break{page-break-after:always;break-after:page}
"""


def summary_for_pdf(meta: Optional[dict], *, unlocked: bool = True) -> Optional[dict]:
    """Pick the summary half that matches what this reader is entitled to.

    Mirrors the app: a paid reader gets the summary written against the paid
    report, and never the upsell sections that belong to the free preview.
    """
    m = meta if isinstance(meta, dict) else {}
    candidates = ([m.get("plainSummaryPaid"), m.get("plainSummary")] if unlocked
                  else [m.get("plainSummary")])
    for cand in candidates:
        if not isinstance(cand, dict):
            continue
        sections = [s for s in (cand.get("sections") or []) if isinstance(s, dict)]
        if unlocked:
            insights = [s for s in sections if (s.get("role") or "insight") == "insight"]
            sections = insights or sections
        sections = [s for s in sections if str(s.get("body") or "").strip()]
        if sections:
            return {
                "headline": str(cand.get("headline") or "").strip(),
                "sections": sections,
                "language": str(m.get("language") or "en"),
            }
    return None


def summary_html(
    summary: dict,
    *,
    title: str = "",
    subtitle: str = "",
    standalone: bool = False,
    language: str = "en",
) -> str:
    """Render a plain summary as a print-ready block, or a whole document."""
    def esc(value: Any) -> str:
        return _html.escape(str(value or "").strip())

    code = str(language or "").lower().strip()
    if code in ("hi_en", "hinglish", "hi", "hindi"):
        eyebrow = "Aapki Reading Ka Saransh"
        note = ("Yeh aapki reading ka mukhya saransh hai. Har bindu ki poori detail "
                "ke liye neeche di gayi report dekhein.")
        default_title = "Aapki Reading Ka Saransh"
    elif code in ("te_en", "tenglish", "te", "telugu"):
        eyebrow = "Mee Reading Saramsam"
        note = ("Idi mee reading yokka mukhya saramsam. Prati amsham yokka poorthi "
                "vivarala kosam kindha report chudandi.")
        default_title = "Mee Reading Saramsam"
    else:
        eyebrow = "Your reading in plain language"
        note = ("This is the crux of your reading in everyday language. The full "
                "reading follows, with the detail behind every point.")
        default_title = "Your reading in plain language"
    parts = [
        '<div class="gr-sum">',
        f'<p class="gr-sum-eyebrow">{eyebrow}</p>',
    ]
    if title:
        parts.append(f"<h1>{esc(title)}</h1>")
    if subtitle:
        parts.append(f'<p class="gr-sum-sub">{esc(subtitle)}</p>')
    if summary.get("headline"):
        parts.append(f'<p class="gr-sum-lead">{esc(summary["headline"])}</p>')
    for section in summary.get("sections") or []:
        parts.append(
            "<section>"
            f'<h2>{esc(section.get("title") or "Overview")}</h2>'
            f'<p>{esc(section.get("body"))}</p>'
            "</section>"
        )
    if standalone:
        if code in ("hi_en", "hinglish", "hi", "hindi"):
            note = "Yeh aapki reading ka mukhya saransh hai. Poori detail ke liye neeche di gayi report dekhein."
        elif code in ("te_en", "tenglish", "te", "telugu"):
            note = "Idi mee reading yokka mukhya saramsam. Poorthi vivarala kosam neeche unna report chudandi."
        else:
            note = "This is the crux of your reading in everyday language. Open the full reading for the detail behind every point."
    parts.append(f'<p class="gr-sum-note">{note}</p>')
    parts.append("</div>")
    block = "".join(parts)
    if not standalone:
        return block
    return (
        f'<!doctype html><html lang="{"en" if code not in ("hi_en", "hinglish", "hi", "hindi", "te_en", "tenglish", "te", "telugu") else code}"><head><meta charset="utf-8"/>'
        f"<title>{esc(title or default_title)}</title>"
        f"<style>{_SUMMARY_CSS}</style></head><body>{block}</body></html>"
    )


def prepend_summary(report_html: str, summary_block: str) -> str:
    """Put the summary in front of the report as its own page."""
    if not summary_block:
        return report_html
    cover = f'<div class="gr-sum-break">{summary_block}</div>'
    doc = report_html or ""
    style = f"<style>{_SUMMARY_CSS}</style>"
    if re.search(r"</head>", doc, flags=re.I):
        doc = re.sub(r"</head>", style + "</head>", doc, count=1, flags=re.I)
    else:
        cover = style + cover
    m = re.search(r"<body\b[^>]*>", doc, flags=re.I)
    if m:
        return doc[:m.end()] + cover + doc[m.end():]
    return cover + doc


def entitlement_item_for_kind(kind: str) -> str:
    """Map stored report kind → billing entitlement item."""
    return {
        "palm": "palm_full",
        "numerology": "numerology_full",
        "daily": "daily",
    }.get(kind or "", kind or "")
