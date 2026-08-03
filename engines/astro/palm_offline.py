#!/usr/bin/env python3
"""
One-shot offline palm pipeline: photo → features → rules → report (no LLM).

  python3 palm_offline.py right.jpg left.jpg --name "Ritz" --active-hand right
  python3 palm_offline.py palm.jpg -o reports/Palm_offline_test.html --format html
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from palm_features import extract_features, features_for_json, save_overlay
from palm_interpret import interpret_features, load_rules, render_html, render_markdown


def main() -> None:
    ap = argparse.ArgumentParser(description="Offline palm: CV features + YAML rules")
    ap.add_argument("images", nargs="+", help="Palm photos (tag with :right or :left)")
    ap.add_argument("-o", "--output", default="reports/Palm_offline_report.md")
    ap.add_argument("--format", choices=("md", "html"), default="md")
    ap.add_argument("--name", default="Client")
    ap.add_argument("--active-hand", default="right", choices=("left", "right"))
    ap.add_argument("--work-dir", type=Path, default=Path("palm_offline_out"))
    args = ap.parse_args()

    work = args.work_dir
    work.mkdir(parents=True, exist_ok=True)
    rules = load_rules()
    results = []
    overlay_paths: dict[str, str] = {}

    for spec in args.images:
        hand = "unknown"
        path_str = spec
        if ":" in spec:
            path_str, hand = spec.rsplit(":", 1)
            if hand not in ("left", "right"):
                path_str, hand = spec, "unknown"
        img = Path(path_str)
        if not img.is_file():
            raise SystemExit(f"Not found: {img}")

        print(f"Analyzing {img} ({hand})…")
        feats = extract_features(img, hand=hand)
        stem = f"{hand}_{img.stem}"
        feat_path = work / f"{stem}_features.json"
        feat_path.write_text(
            json.dumps(features_for_json(feats), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        ov_path = work / f"{stem}_overlay.jpg"
        save_overlay(img, feats, ov_path)
        print(f"  features -> {feat_path}")
        print(f"  overlay  -> {ov_path}  (verify detections here)")

        clean = json.loads(feat_path.read_text(encoding="utf-8"))
        results.append(interpret_features(clean, rules))
        if hand in ("left", "right"):
            overlay_paths[hand] = str(ov_path.resolve())

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "html":
        # Use file:// paths for local viewing
        urls = {h: Path(p).as_uri() for h, p in overlay_paths.items()}
        text = render_html(
            results,
            client_name=args.name,
            active_hand=args.active_hand,
            overlay_urls=urls,
        )
    else:
        text = render_markdown(results, client_name=args.name, active_hand=args.active_hand)
        if overlay_paths:
            text += "\n\n## Overlay images (verify detections)\n"
            for h, p in overlay_paths.items():
                text += f"- **{h}:** `{p}`\n"

    out.write_text(text, encoding="utf-8")
    hits = sum(r["matched_count"] for r in results)
    print(f"\nReport -> {out} ({hits} rule matches, no LLM)")


if __name__ == "__main__":
    main()
