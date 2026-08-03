#!/usr/bin/env python3
"""
Extract PDF content for reading / LLM workflows: metadata, text layer, page images, optional OCR.

Requires (Debian/Ubuntu): poppler-utils (pdfinfo, pdftotext, pdftoppm)
Optional OCR: tesseract-ocr

Example:
  ./extract_pdf_for_reading.py "book.pdf"
  ./extract_pdf_for_reading.py "book.pdf" --preview-pages 10 --ocr --ocr-pages 1-20
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def require_tools(*names: str) -> None:
    missing = [n for n in names if shutil.which(n) is None]
    if missing:
        sys.stderr.write(
            "Missing tools: %s\nInstall poppler-utils (pdfinfo, pdftotext, pdftoppm).\n"
            % ", ".join(missing)
        )
        sys.exit(1)


def parse_page_range(spec: str | None, default_first: int, default_last: int) -> tuple[int, int]:
    if not spec:
        return default_first, default_last
    m = re.match(r"^(\d+)\s*-\s*(\d+)$", spec.strip())
    if not m:
        raise ValueError("Page range must look like 1-10")
    a, b = int(m.group(1)), int(m.group(2))
    if a < 1 or b < a:
        raise ValueError("Invalid page range")
    return a, b


def pdf_page_count(pdf: Path) -> int:
    cp = run(["pdfinfo", str(pdf)])
    if cp.returncode != 0:
        sys.stderr.write(cp.stderr or cp.stdout or "pdfinfo failed\n")
        sys.exit(1)
    for line in (cp.stdout or "").splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    sys.stderr.write("Could not parse page count from pdfinfo\n")
    sys.exit(1)


def extract_pdfinfo(pdf: Path, dest: Path) -> None:
    cp = run(["pdfinfo", str(pdf)])
    dest.write_text(cp.stdout or "", encoding="utf-8")
    if cp.returncode != 0:
        sys.stderr.write(cp.stderr or "pdfinfo failed\n")


def extract_pdftotext(pdf: Path, dest: Path) -> str:
    cp = run(["pdftotext", "-layout", str(pdf), str(dest)])
    if cp.returncode != 0:
        sys.stderr.write(cp.stderr or "pdftotext failed\n")
        return ""
    try:
        return dest.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def render_pages_png(pdf: Path, out_dir: Path, first: int, last: int, prefix: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(out_dir / f"{prefix}-%03d.png")
    cp = run(
        [
            "pdftoppm",
            "-png",
            "-f",
            str(first),
            "-l",
            str(last),
            str(pdf),
            str(out_dir / prefix),
        ]
    )
    if cp.returncode != 0:
        sys.stderr.write(cp.stderr or cp.stdout or "pdftoppm failed\n")
        sys.exit(1)
    # pdftoppm names: prefix-01.png or prefix-001.png depending on version; glob sort
    paths = sorted(out_dir.glob(f"{prefix}-*.png"))
    return paths


def ocr_image(png: Path, lang: str) -> str:
    cp = run(["tesseract", str(png), "stdout", "-l", lang])
    if cp.returncode != 0:
        return ""
    return (cp.stdout or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract PDF metadata, text, preview images, and optional OCR for image-only PDFs."
    )
    parser.add_argument("pdf", type=Path, help="Path to PDF file")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: ./pdf_extractions/<pdf_stem>/)",
    )
    parser.add_argument(
        "--preview-pages",
        type=int,
        default=5,
        metavar="N",
        help="Number of pages from the start to render as PNG (default: 5)",
    )
    parser.add_argument(
        "--preview-all",
        action="store_true",
        help="Render every page as PNG (can be large/slow)",
    )
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Run Tesseract OCR on rendered preview images",
    )
    parser.add_argument(
        "--ocr-pages",
        type=str,
        default=None,
        metavar="F-L",
        help="Page range for OCR only, e.g. 1-30 (default: same as preview range)",
    )
    parser.add_argument(
        "--tesseract-lang",
        type=str,
        default="eng",
        help="Tesseract language(s), e.g. eng or eng+san (default: eng)",
    )
    parser.add_argument(
        "--text-threshold",
        type=int,
        default=500,
        metavar="CHARS",
        help="If extracted text has fewer non-space chars, mark as likely image-only (default: 500)",
    )
    args = parser.parse_args()

    pdf = args.pdf.resolve()
    if not pdf.is_file():
        sys.stderr.write("File not found: %s\n" % pdf)
        sys.exit(1)

    require_tools("pdfinfo", "pdftotext", "pdftoppm")

    stem = pdf.stem
    out = (args.output_dir or (Path.cwd() / "pdf_extractions" / stem)).resolve()
    out.mkdir(parents=True, exist_ok=True)

    pages = pdf_page_count(pdf)

    info_path = out / "pdfinfo.txt"
    text_path = out / "extracted_text.txt"
    manifest_path = out / "manifest.json"
    preview_dir = out / "preview_png"

    extract_pdfinfo(pdf, info_path)
    text = extract_pdftotext(pdf, text_path)
    non_space = len(re.sub(r"\s+", "", text))
    likely_image_only = non_space < args.text_threshold

    if args.preview_all:
        p_first, p_last = 1, pages
    else:
        p_first, p_last = 1, min(args.preview_pages, pages)

    render_pages_png(pdf, preview_dir, p_first, p_last, "page")
    preview_files = sorted(preview_dir.glob("page-*.png"))

    ocr_dir = out / "ocr_text"
    ocr_combined_path = out / "ocr_combined.txt"
    ocr_png_dir = out / "ocr_png"
    ocr_ran = False
    ocr_pages_written = 0
    o_first = p_first
    o_last = p_last

    if args.ocr:
        if shutil.which("tesseract") is None:
            sys.stderr.write("Tesseract not found; install tesseract-ocr or omit --ocr.\n")
            sys.exit(1)
        if args.ocr_pages:
            o_first, o_last = parse_page_range(args.ocr_pages, 1, pages)
        o_first = max(1, min(o_first, pages))
        o_last = max(o_first, min(o_last, pages))

        render_pages_png(pdf, ocr_png_dir, o_first, o_last, "ocr")
        ocr_pngs = sorted(ocr_png_dir.glob("ocr-*.png"))

        ocr_dir.mkdir(parents=True, exist_ok=True)
        parts: list[str] = []
        for i, png in enumerate(ocr_pngs):
            page_num = o_first + i
            body = ocr_image(png, args.tesseract_lang)
            chunk_path = ocr_dir / ("page_%04d.txt" % page_num)
            chunk_path.write_text(body + "\n", encoding="utf-8")
            ocr_pages_written += 1
            parts.append("--- Page %d ---\n%s\n" % (page_num, body))
        ocr_combined_path.write_text("\n".join(parts), encoding="utf-8")
        ocr_ran = True

    manifest = {
        "source_pdf": str(pdf),
        "page_count": pages,
        "output_dir": str(out),
        "files": {
            "pdfinfo": str(info_path),
            "extracted_text": str(text_path),
            "preview_png_dir": str(preview_dir),
            "ocr_png_dir": str(ocr_png_dir) if ocr_ran else None,
            "ocr_combined": str(ocr_combined_path) if ocr_ran else None,
            "ocr_per_page_dir": str(ocr_dir) if ocr_ran else None,
        },
        "stats": {
            "extracted_text_non_space_chars": non_space,
            "likely_image_only_pdf": likely_image_only,
            "preview_pages_rendered": len(preview_files),
            "preview_range": [p_first, p_last],
            "ocr_range": ([o_first, o_last] if ocr_ran else None),
        },
        "ocr": {
            "ran": ocr_ran,
            "lang": args.tesseract_lang if ocr_ran else None,
            "pages_written": ocr_pages_written if ocr_ran else 0,
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("Wrote: %s" % out)
    print("  pdfinfo:     %s" % info_path)
    print("  text:        %s  (%d non-space chars)%s" % (
        text_path,
        non_space,
        "  [likely image-only]" if likely_image_only else "",
    ))
    print("  previews:    %s  (%d files)" % (preview_dir, len(preview_files)))
    if ocr_ran:
        print("  OCR:         %s" % ocr_combined_path)
    elif likely_image_only:
        print("  Tip: add --ocr (needs tesseract) to build searchable text from pages.")


if __name__ == "__main__":
    main()
