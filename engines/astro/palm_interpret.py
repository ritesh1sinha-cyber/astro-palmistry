#!/usr/bin/env python3
"""
Apply palm_rules.yaml to palm_features.json — deterministic, no LLM.

  python3 palm_interpret.py features.json -o report.md
  python3 palm_interpret.py right.json left.json -o combined.md --hand right active
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import yaml

RULES_PATH = Path(__file__).resolve().parent / "palm_rules.yaml"


def _get_nested(data: dict[str, Any], dotted: str) -> Any:
    cur: Any = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _match_requires(features: dict[str, Any], requires: dict[str, Any]) -> bool:
    for key, expected in requires.items():
        actual = _get_nested(features, key)
        if actual is None:
            return False
        if str(actual).lower() != str(expected).lower():
            return False
    return True


def load_rules(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or RULES_PATH
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return list(data.get("rules", []))


def interpret_features(
    features: dict[str, Any],
    rules: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rules = rules or load_rules()
    matched: list[dict[str, Any]] = []
    for rule in rules:
        req = rule.get("requires") or {}
        if _match_requires(features, req):
            matched.append(
                {
                    "id": rule["id"],
                    "source": rule.get("source", ""),
                    "category": rule.get("category", "general"),
                    "text": rule["text"].strip(),
                }
            )
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for m in matched:
        by_cat.setdefault(m["category"], []).append(m)
    return {
        "hand": features.get("hand", "unknown"),
        "quality": features.get("quality", {}),
        "matched_count": len(matched),
        "matched": matched,
        "by_category": by_cat,
        "facts": {
            "morphology": features.get("morphology", {}),
            "lines": features.get("lines", {}),
            "mounts": features.get("mounts", {}),
        },
    }


def render_markdown(
    results: list[dict[str, Any]],
    *,
    client_name: str = "Client",
    active_hand: str = "right",
) -> str:
    lines: list[str] = []
    lines.append(f"# Palm reading (offline / rule-based)\n")
    lines.append(f"**{client_name}** · generated {date.today().isoformat()}\n")
    lines.append(
        "*No LLM used. Interpretations fire only when measured features match "
        "`palm_rules.yaml`. Verify the overlay image against your palm.*\n"
    )
    lines.append(f"**Active hand for lived life:** {active_hand}\n")

    for res in results:
        hand = res.get("hand", "?")
        q = res.get("quality", {})
        lines.append(f"\n## {'Right' if hand == 'right' else 'Left' if hand == 'left' else hand} palm\n")
        lines.append(
            f"- **Image quality:** {q.get('grade', '?')} (score {q.get('score', '?')})"
        )
        if q.get("issues"):
            lines.append(f"- **Issues:** {', '.join(q['issues'])}")
        lines.append("\n### Measured features (facts only)\n")
        lines.append("```json")
        lines.append(json.dumps(res.get("facts", {}), indent=2))
        lines.append("```\n")
        lines.append("### Rule-based interpretations\n")
        if not res.get("matched"):
            lines.append("*No rules matched — improve photo or extend `palm_rules.yaml`.*\n")
            continue
        by_cat = res.get("by_category", {})
        for cat in sorted(by_cat.keys()):
            lines.append(f"\n#### {cat.replace('_', ' ').title()}\n")
            for m in by_cat[cat]:
                lines.append(f"- **[{m['id']}]** ({m['source']}) {m['text']}\n")

    lines.append("\n---\n")
    lines.append(
        "*Educational only. Lines change over time. For disputes, trust the "
        "feature JSON + overlay, not memory.*\n"
    )
    return "\n".join(lines)


def render_html(
    results: list[dict[str, Any]],
    *,
    client_name: str = "Client",
    active_hand: str = "right",
    overlay_urls: dict[str, str] | None = None,
) -> str:
    overlay_urls = overlay_urls or {}
    body_parts = []
    for res in results:
        hand = res.get("hand", "?")
        title = {"right": "Right palm", "left": "Left palm"}.get(hand, hand)
        q = res.get("quality", {})
        body_parts.append(f"<h2>{title}</h2>")
        body_parts.append(
            f'<p class="meta">Quality: <strong>{q.get("grade", "?")}</strong> '
            f'(score {q.get("score", "?")})</p>'
        )
        if hand in overlay_urls:
            body_parts.append(
                f'<p><img src="{overlay_urls[hand]}" alt="overlay" '
                f'style="max-width:100%;border-radius:8px;" /></p>'
            )
        body_parts.append("<h3>Measured features</h3><pre>")
        body_parts.append(json.dumps(res.get("facts", {}), indent=2))
        body_parts.append("</pre><h3>Interpretations (rule-matched)</h3><ul>")
        for m in res.get("matched", []):
            body_parts.append(
                f'<li><code>{m["id"]}</code> <em>({m["source"]})</em> {m["text"]}</li>'
            )
        body_parts.append("</ul>")
    inner = "\n".join(body_parts)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<title>Palm — {client_name}</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem;
  background: #0f1117; color: #e8ecf4; }}
h1 {{ color: #c9a0ff; }} h2 {{ color: #5b9cff; margin-top: 2rem; }}
.meta {{ color: #8b95a8; }} pre {{ background: #1a1d27; padding: 1rem; border-radius: 8px; overflow: auto; }}
li {{ margin: 0.5rem 0; }} code {{ color: #3dd68c; }}
</style></head><body>
<h1>Palm reading (offline)</h1>
<p class="meta">{client_name} · {date.today().isoformat()} · active hand: {active_hand}</p>
{inner}
<p class="meta"><em>Educational only. Not medical advice.</em></p>
</body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description="Interpret palm features via YAML rules")
    ap.add_argument("features", nargs="+", help="palm_features.json file(s)")
    ap.add_argument("-o", "--output", default="palm_report.md")
    ap.add_argument("--format", choices=("md", "html"), default="md")
    ap.add_argument("--name", default="Client")
    ap.add_argument("--active-hand", default="right", choices=("left", "right"))
    ap.add_argument("--rules", type=Path, help="Custom palm_rules.yaml")
    args = ap.parse_args()

    rules = load_rules(args.rules) if args.rules else None
    all_results: list[dict[str, Any]] = []
    for fp in args.features:
        feats = json.loads(Path(fp).read_text(encoding="utf-8"))
        all_results.append(interpret_features(feats, rules))

    out = Path(args.output)
    if args.format == "html":
        text = render_html(all_results, client_name=args.name, active_hand=args.active_hand)
        try:
            from client_report_html import finalize_report_html
            text = finalize_report_html(text, args.name)
        except Exception:
            pass
    else:
        text = render_markdown(all_results, client_name=args.name, active_hand=args.active_hand)
    out.write_text(text, encoding="utf-8")
    total = sum(r["matched_count"] for r in all_results)
    print(f"Saved {out} ({total} rule hits across {len(all_results)} palm(s))")


if __name__ == "__main__":
    main()
