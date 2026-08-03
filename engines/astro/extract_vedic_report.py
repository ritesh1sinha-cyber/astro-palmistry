#!/usr/bin/env python3
"""
Extract machine-friendly data from AstroSage-style Vedic PDF reports.

  python3 extract_vedic_report.py chart.pdf              # dump text + section index + parse planets
  python3 extract_vedic_report.py chart.pdf --text-only  # only pdftotext to <stem>_extracted.txt

Requires: poppler-utils (pdftotext)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SECTION_SUBSTRINGS = [
    "|| ",
    "Planetary Positions",
    "Planetary Degree And Their Positions",
    "Vimshottari Dasha",
    "Ashtakvarga Table",
    "Chalit Table",
    "Lal Kitab Dasha",
    "Shodashvarga Table",
    "KP System / Nakshatra Nadi",
    "Friendship Table",
    "Shadbala and Bhavabala",
    "Yogini Dasha",
    "Char Dasha",
    "Jamini System",
    "Varshaphal",
    "Lal Kitab Prediction",
]

def run_pdftotext(pdf: Path, out_txt: Path) -> None:
    if not pdf.is_file():
        sys.stderr.write("Not found: %s\n" % pdf)
        sys.exit(1)
    cp = subprocess.run(
        ["pdftotext", "-layout", str(pdf), str(out_txt)],
        capture_output=True,
        text=True,
    )
    if cp.returncode != 0:
        sys.stderr.write(cp.stderr or "pdftotext failed\n")
        sys.exit(1)


def index_sections(lines: list[str]) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for i, line in enumerate(lines, start=1):
        s = line.lstrip("\f").strip()
        for sub in SECTION_SUBSTRINGS:
            if sub in s:
                hits.append((i, s[:120]))
                break
    return hits


# AstroSage -layout lines often contain full row on one line
_PLANET_ROW = re.compile(
    r"(?P<pid>ASC|Sun|Moon|Mars|Merc|Jupt|Venu|Satn|Rahu\s*\[R\]|Ketu\s*\[R\]|Uran\s*\[R\]|Nept|Plut)\s+"
    r"(?P<sign>[A-Za-z]+)\s+"
    r"(?P<dms>\d{2}-\d{2}-\d{2})\s+"
    r"(?P<nak>[^\d]+?)\s+"
    r"(?P<pada>\d+)"
)


def parse_planetary_rows_layout(lines: list[str]) -> list[dict[str, object]]:
    start = 0
    for i, line in enumerate(lines):
        if "Planetary Positions" in line:
            start = i
            break
    end = min(len(lines), start + 40)
    window = lines[start:end]
    out: list[dict[str, object]] = []
    seen: set[str] = set()
    for line in window:
        if "Ashtakvarga Table" in line:
            break
        m = _PLANET_ROW.search(line)
        if not m:
            continue
        raw = m.group("pid").strip()
        retro = "[R]" in raw
        pid = re.sub(r"\s*\[R\]\s*", "", raw).strip()
        if pid in seen:
            continue
        seen.add(pid)
        sign = m.group("sign")
        if sign == "Scorpion":
            sign = "Scorpio"
        nak = " ".join(m.group("nak").split())
        out.append(
            {
                "id": pid,
                "sign": sign,
                "degree_dms": m.group("dms"),
                "nakshatra": nak,
                "pada": int(m.group("pada")),
                "retrograde": retro,
            }
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract section index + D-1 planets from Vedic PDF.")
    ap.add_argument("pdf", type=Path, help="Path to PDF report")
    ap.add_argument("--text-only", action="store_true", help="Only write pdftotext output")
    ap.add_argument("-o", "--out-dir", type=Path, default=None, help="Output directory")
    args = ap.parse_args()

    pdf = args.pdf.resolve()
    out_dir = (args.out_dir or pdf.parent).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = pdf.stem
    txt_path = out_dir / ("%s_extracted.txt" % stem)

    run_pdftotext(pdf, txt_path)
    print("Wrote: %s" % txt_path)

    if args.text_only:
        return

    lines = txt_path.read_text(encoding="utf-8", errors="replace").splitlines()
    hits = index_sections(lines)
    index_path = out_dir / ("%s_section_index.txt" % stem)
    index_path.write_text(
        "\n".join("%5d  %s" % (n, t) for n, t in hits),
        encoding="utf-8",
    )
    print("Wrote: %s  (%d markers)" % (index_path, len(hits)))

    planets = parse_planetary_rows_layout(lines)
    if planets:
        json_path = out_dir / ("%s_planets_d1.json" % stem)
        json_path.write_text(json.dumps(planets, indent=2), encoding="utf-8")
        print("Wrote: %s" % json_path)
    else:
        sys.stderr.write("Could not auto-parse Planetary Positions; fill YAML by hand.\n")


if __name__ == "__main__":
    main()
