#!/usr/bin/env python3
"""
astro_hotfix.py — in-memory patches for upstream bugs. DELETE ME once fixed.

Each entry documents a real defect found while integrating, the one-line fix,
and why it matters. Nothing on disk is modified: the module source is rewritten
as it is imported, so your repo stays clean and the patch is reversible by
simply not importing this module (set ASTRO_HOTFIX=0).

--------------------------------------------------------------------------
1. vedic_horary_report._prashna_card — IndexError: string index out of range
--------------------------------------------------------------------------
   Line ~494:
       f"<li><span class='step-icon'>{'①②③④⑤⑥⑦'[i]}</span>…"

   The step list is built conditionally and reaches EIGHT entries whenever
   `benefics_in_kendra` is non-empty (plus all other steps present), but the
   glyph string holds only seven characters — so `[7]` raises IndexError and
   the whole Vedic horary report fails to render. Western still returns, so the
   symptom is "one tradition silently missing", which is easy to miss in
   testing and would ship as a broken ₹99 product.

   Reproduce: question "Will I get the promotion this year?",
              2026-08-03 21:30, New Delhi — crashes before this patch.

   Recommended real fix (one line, in your repo):
       -  {'①②③④⑤⑥⑦'[i]}
       +  {chr(9312 + i) if i < 20 else i + 1}

   ⑳ is U+2473, so chr(9312+i) covers 20 steps — ample headroom.
"""

from __future__ import annotations

import os
import sys
import types

APPLIED: list[str] = []


def _locate(module_name: str) -> str:
    """Find a module's source file without importing it (cwd-independent)."""
    import importlib.util
    spec = importlib.util.find_spec(module_name)
    if spec and spec.origin:
        return spec.origin
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), module_name + ".py")
    if os.path.isfile(here):
        return here
    raise RuntimeError(f"cannot locate {module_name}.py")


def _patch_module(name: str, path: str, replacements: list[tuple[str, str]]) -> types.ModuleType:
    src = open(path, encoding="utf-8").read()
    hits = 0
    for old, new in replacements:
        if old in src:
            src = src.replace(old, new)
            hits += 1
    if not hits:
        raise RuntimeError(f"{name}: no patch target found — upstream may already be fixed")
    if "from __future__ import annotations" not in src:
        src = "from __future__ import annotations\n" + src
    mod = types.ModuleType(name)
    mod.__file__ = path
    sys.modules[name] = mod
    exec(compile(src, path, "exec"), mod.__dict__)
    APPLIED.append(name)
    return mod


def horary_glyph_fix():
    """Return a patched vedic_horary_report module (see docstring, item 1)."""
    glyphs = "".join(chr(9312 + i) for i in range(7))          # ①..⑦
    return _patch_module(
        "vedic_horary_report_patched", _locate("vedic_horary_report"),
        [(f"'{glyphs}'[i]", "(chr(9312 + i) if i < 20 else str(i + 1))")],
    )


def confluence_remedy_fix():
    """Return a confluence module that keeps remedies on the question answer.

    The full report answers the customer's question through the main-question
    engine and calls it with `skip_remedy=True`. So the one place a worried
    person reads a direct answer about their own question was also the one
    place with the "what to do about it" removed.

    Product rule from the operator: an unfavourable answer always carries a
    remedy. Patched in memory, like the glyph fix, so the engine file stays
    untouched.
    """
    return _patch_module(
        "vedic_confluence_report_remedied", _locate("vedic_confluence_report"),
        [("render_main_question_embed_html(main_q_result, skip_remedy=True)",
          "render_main_question_embed_html(main_q_result, skip_remedy=False)")],
    )
