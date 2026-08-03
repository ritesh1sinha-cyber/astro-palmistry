#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR divisional chart PDFs (Comprehensive Prediction by Divisional Charts).

Uses PyMuPDF + RapidOCR (no system Tesseract required). Writes per-page text under
book_ocr/<pdf-stem>/pages/ and optional combined chapter files.

Example:
  python ocr_divisional_book.py --pdf divisional_chart-tillD10.pdf --pages 18-50 --out D1_chapter_ocr.txt
  python ocr_divisional_book.py --pdf divisional-D10toD60.pdf --pages all --out full_book_ocr.txt
"""
from __future__ import annotations

import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PDF = BASE_DIR / "divisional_chart-tillD10.pdf"
DEFAULT_WORK = BASE_DIR / "book_ocr" / "divisional_chart-tillD10"


def _parse_page_range(spec: str, max_page: int) -> tuple[int, int]:
    if spec.strip().lower() in ("all", "full", "*"):
        return 1, max_page
    if "-" in spec:
        a, b = spec.split("-", 1)
        start, end = int(a), int(b)
    else:
        start = end = int(spec)
    start = max(1, start)
    end = min(max_page, max(end, start))
    return start, end


def _default_work_dir(pdf: Path) -> Path:
    return BASE_DIR / "book_ocr" / pdf.stem


def ocr_pdf_pages(
    pdf_path: Path,
    start: int,
    end: int,
    *,
    work_dir: Path,
    dpi: int = 150,
    force: bool = False,
) -> list[str]:
    import fitz
    from rapidocr_onnxruntime import RapidOCR

    work_dir.mkdir(parents=True, exist_ok=True)
    page_dir = work_dir / "pages"
    page_dir.mkdir(parents=True, exist_ok=True)
    engine = RapidOCR()
    doc = fitz.open(pdf_path)
    parts: list[str] = []
    for i in range(start - 1, end):
        n = i + 1
        txt_path = page_dir / f"page_{n:03d}.txt"
        if txt_path.exists() and not force and txt_path.stat().st_size > 40:
            text = txt_path.read_text(encoding="utf-8")
        else:
            img_path = page_dir / f"page_{n:03d}.png"
            if force or not img_path.exists():
                pix = doc[i].get_pixmap(dpi=dpi)
                pix.save(str(img_path))
            result, _ = engine(str(img_path))
            lines = [r[1] for r in (result or [])]
            text = "\n".join(lines)
            txt_path.write_text(text, encoding="utf-8")
        parts.append(f"--- pdf_page {n} ---\n{text}")
        print(f"page {n}: {len(text)} chars")
    return parts


def main() -> None:
    ap = argparse.ArgumentParser(description="OCR divisional chart PDF(s)")
    ap.add_argument("--pdf", default=str(DEFAULT_PDF))
    ap.add_argument("--pages", default="all", help="Page range e.g. 18-50, or 'all' for full book")
    ap.add_argument("--work-dir", default="", help="Default: book_ocr/<pdf-stem>/")
    ap.add_argument("--out", default="full_book_ocr.txt", help="Combined output filename inside work-dir")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    pdf = Path(args.pdf)
    if not pdf.is_file():
        raise SystemExit(f"PDF not found: {pdf}")

    import fitz
    doc = fitz.open(pdf)
    start, end = _parse_page_range(args.pages, doc.page_count)
    work = Path(args.work_dir) if args.work_dir else _default_work_dir(pdf)
    print(f"OCR {pdf.name}: pages {start}-{end} of {doc.page_count} -> {work}")
    parts = ocr_pdf_pages(pdf, start, end, work_dir=work, dpi=args.dpi, force=args.force)
    out_name = args.out or f"pages_{start}_{end}_ocr.txt"
    out_path = work / out_name
    out_path.write_text("\n\n".join(parts), encoding="utf-8")
    print(f"Wrote {out_path} ({len(parts)} pages, {out_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
