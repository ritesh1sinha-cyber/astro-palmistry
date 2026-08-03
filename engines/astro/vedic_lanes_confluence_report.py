#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vedic_lanes_confluence_report.py - NEW multi-lane confluence (does not use vedic_confluence_report.py).

Pulls live predictions from today's pipelines:
  BNN, KP, Mehta, Jaimini (books), Bhardwaj, KVS nakshatra tales

Semantic agreement: MiniLM + cross-encoder (BERT-family).
Headline verdicts require >= 75% lane agreement + semantic score.

Usage:
    python3 vedic_lanes_confluence_report.py reports/VedicReport_ritz_extracted.txt Ritz 1985-03-08
    python3 vedic_lanes_confluence_report.py <extract> <name> <dob> -o reports/Lanes_Confluence_Ritz.html
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from astro_precompute import precompute
from lane_collectors import LANE_COLLECTORS, collect_all_lanes
from lanes_confluence_engine import LanesConfluenceEngine
from lanes_confluence_html import render_lanes_confluence

BASE = Path(__file__).resolve().parent


def generate_lanes_confluence(
    extracted: str,
    name: str,
    dob: str,
) -> tuple[str, dict]:
    pc = precompute(extracted, name, dob)
    claims, lane_meta = collect_all_lanes(extracted, name, dob, pc)
    lanes_present = sum(1 for k, v in lane_meta.items() if isinstance(v, int) and v > 0 and k in {x[0] for x in LANE_COLLECTORS} | {"KVS"})
    engine = LanesConfluenceEngine()
    verdicts = engine.analyze(claims, max(lanes_present, 1))
    html_doc = render_lanes_confluence(pc, verdicts, lane_meta, lanes_present)
    summary = {
        "claims": len(claims),
        "lanes_present": lanes_present,
        "lane_meta": lane_meta,
        "domains": len(verdicts),
        "firm_domains": [v.domain for v in verdicts if v.meets_threshold],
    }
    return html_doc, summary


def main() -> None:
    ap = argparse.ArgumentParser(description="New multi-lane semantic confluence")
    ap.add_argument("extracted")
    ap.add_argument("name")
    ap.add_argument("dob")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    doc, summary = generate_lanes_confluence(args.extracted, args.name, args.dob)
    slug = args.name.replace(" ", "_")
    out = Path(args.out) if args.out else BASE / "reports" / f"Lanes_Confluence_{slug}_{date.today().strftime('%Y%m%d')}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(f"claims={summary['claims']} lanes={summary['lanes_present']} domains={summary['domains']}")
    print(f"firm (75%+): {', '.join(summary['firm_domains']) or 'none'}")
    print("lane counts:", json.dumps({k: v for k, v in summary["lane_meta"].items() if not str(k).endswith("_error")}))
    print(f"written -> {out}")


if __name__ == "__main__":
    main()
