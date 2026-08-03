#!/usr/bin/env python3
"""
Chunked JPEG rasterization + full-book Tesseract OCR (see skill.md §1b).

Example:
  python3 ocr_pdf_jpg_chunks.py "JYOTISHA FOR BEGINNERS.pdf" \\
    --work-dir book_ocr/jyotisha_vol1 --chunk 50
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def pdf_page_count(pdf: Path) -> int:
    cp = subprocess.run(
        ["pdfinfo", str(pdf)], capture_output=True, text=True, check=False
    )
    if cp.returncode != 0:
        print(cp.stderr or cp.stdout, file=sys.stderr)
        raise SystemExit("pdfinfo failed")
    for line in (cp.stdout or "").splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise SystemExit("Could not parse Pages: from pdfinfo")


def render_jpeg_chunks(
    pdf: Path, jpg_dir: Path, *, chunk: int, dpi: int, quality: int
) -> int:
    jpg_dir.mkdir(parents=True, exist_ok=True)
    pages = pdf_page_count(pdf)
    opt = f"quality={quality}"
    for start in range(1, pages + 1, chunk):
        end = min(start + chunk - 1, pages)
        cname = f"chunk_{start:03d}_{end:03d}"
        prefix = jpg_dir / cname
        cp = subprocess.run(
            [
                "pdftoppm",
                "-jpeg",
                "-jpegopt",
                opt,
                "-r",
                str(dpi),
                "-f",
                str(start),
                "-l",
                str(end),
                str(pdf),
                str(prefix),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if cp.returncode != 0:
            print(cp.stderr or cp.stdout or "pdftoppm failed", file=sys.stderr)
            raise SystemExit(f"pdftoppm failed for pages {start}-{end}")
        print(f"Rasterized pages {start}-{end}/{pages}", flush=True)
    return pages


def page_key(p: Path) -> int:
    m = re.search(r"-(\d+)$", p.stem)
    if not m:
        return 0
    return int(m.group(1))


def ocr_jpg_folder(jpg_dir: Path, out_txt: Path, *, lang: str) -> None:
    files = sorted(jpg_dir.glob("*.jpg"), key=page_key)
    if not files:
        raise SystemExit(f"No JPG files in {jpg_dir}")
    parts: list[str] = []
    for i, img in enumerate(files):
        n = page_key(img)
        cp = subprocess.run(
            ["tesseract", str(img), "stdout", "-l", lang],
            capture_output=True,
            text=True,
            check=False,
        )
        body = (cp.stdout or "").strip()
        if cp.returncode != 0:
            body = f"[OCR failed rc={cp.returncode} stderr={cp.stderr!r}]"
        parts.append(f"\n\n========== PAGE {n} ==========\n\n{body}")
        if (i + 1) % 25 == 0:
            print(f"OCR {i + 1}/{len(files)}", flush=True)
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text("".join(parts), encoding="utf-8", errors="replace")
    print(f"Wrote {out_txt} ({len(''.join(parts))} chars)", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="PDF → chunked JPEGs → OCR text")
    ap.add_argument("pdf", type=Path, help="Input PDF path")
    ap.add_argument(
        "--work-dir",
        type=Path,
        required=True,
        help="Output folder (will contain jpg/ and <stem>_ocr_full.txt)",
    )
    ap.add_argument("--chunk", type=int, default=50, help="Pages per pdftoppm batch")
    ap.add_argument("--dpi", type=int, default=144)
    ap.add_argument("--quality", type=int, default=85)
    ap.add_argument("--lang", default="eng", help="Tesseract language(s)")
    ap.add_argument(
        "--skip-raster",
        action="store_true",
        help="Only run OCR (JPGs already in work-dir/jpg)",
    )
    args = ap.parse_args()
    pdf = args.pdf.resolve()
    if not pdf.is_file():
        print("Not found:", pdf, file=sys.stderr)
        return 1
    work = args.work_dir.resolve()
    jpg_dir = work / "jpg"
    stem = pdf.stem.replace(" ", "_").replace("/", "_")
    out_txt = work / f"{stem}_ocr_full.txt"

    if not args.skip_raster:
        render_jpeg_chunks(
            pdf, jpg_dir, chunk=args.chunk, dpi=args.dpi, quality=args.quality
        )
    ocr_jpg_folder(jpg_dir, out_txt, lang=args.lang)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
