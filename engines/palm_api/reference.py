"""
Developer-only reference export.

The user-facing report shows human predictions WITHOUT book references.
This module collects the underlying book/page citations for every numbered
point (per hand) plus the corpus-level matches, so developers can audit which
palmistry rule backs each prediction. Output is a plain reference.txt.
"""

from __future__ import annotations

from datetime import date
from typing import Any


def _hand_section(label: str, block: dict[str, Any]) -> list[str]:
    lines: list[str] = [f"=== {label.upper()} HAND ==="]
    checklist = block.get("numbered_checklist") or []
    if not checklist:
        lines.append("  (no numbered points)")
    for it in checklist:
        num = it.get("num")
        title = it.get("title", "Finding")
        conc = it.get("conclusive") or {}
        verdict = conc.get("verdict", "")
        age = (it.get("timing") or {}).get("estimated_age")
        lines.append(f"\nPoint {num} — {title}" + (f" (age ~{age})" if age is not None else ""))
        if verdict:
            lines.append(f"  Prediction: {verdict}")
        cit = conc.get("citation") or {}
        if cit.get("book_label"):
            lines.append(
                f"  Primary source: {cit.get('book_label')}, p.{cit.get('page', '?')}"
                f" (match {cit.get('score', '?')})"
            )
            if cit.get("excerpt"):
                lines.append(f"    Excerpt: {cit['excerpt']}")
        for q in it.get("book_quotes") or []:
            lines.append(
                f"  Supporting: {q.get('book_label') or q.get('book')}, p.{q.get('page', '?')}"
                f" (match {q.get('score', '?')})"
            )
            txt = (q.get("text") or "").strip()
            if txt:
                lines.append(f"    {txt[:400]}")
    # Corpus-level matches for this hand
    preds = (block.get("prediction") or {}).get("predictions") or []
    if preds:
        lines.append("\n  -- Corpus-level matches --")
        for p in preds:
            lines.append(
                f"  [{p.get('category')}] {p.get('book_label') or p.get('book')}, "
                f"p.{p.get('page', '?')} (match {p.get('score', '?')})"
            )
            txt = (p.get("text") or "").strip()
            if txt:
                lines.append(f"    {txt[:400]}")
    return lines


def build_reference_text(results: dict[str, Any]) -> str:
    """Produce the full developer reference document."""
    out: list[str] = [
        "PALMISTRY ANALYSIS — DEVELOPER REFERENCE",
        f"Generated: {date.today().isoformat()}",
        "Maps each human prediction in the report back to its source palmistry rule.",
        "(For developer/audit use only — not shown to the end user.)",
        "=" * 60,
    ]
    active = results.get("active_hand", "right")
    out.append(f"Dominant hand: {active}")
    for label in ("right", "left"):
        block = results.get(label)
        if not block:
            continue
        out.append("")
        out.extend(_hand_section(label, block))
    out.append("\n" + "=" * 60)
    out.append("END OF REFERENCE")
    return "\n".join(out)
