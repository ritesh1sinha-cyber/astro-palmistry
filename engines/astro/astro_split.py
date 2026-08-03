#!/usr/bin/env python3
"""
astro_split.py — free / paid partitioning for generated astrology reports.

The engine's reports are self-contained HTML built from `<section class="section">`
blocks, each introduced by an `<h2>`. This module splits a generated report into
a FREE document and a PAID document, preserving the original `<head>` (so both
halves render standalone with the engine's own styling).

Policy (see PLAN doc):
  FREE  — orientation + identity + present state  ("read up to today")
  PAID  — the decision domains, the forward timeline, remedies

Nothing here modifies the engine; it post-processes its HTML output.
"""

from __future__ import annotations

import re
from typing import Iterable

# ---------------------------------------------------------------------------
# Policy — edit these lists to move a section across the paywall
# ---------------------------------------------------------------------------
CONFLUENCE_FREE = (
    "how to read this report",
    "character & personality",
    "where you stand now",
    "confidence dashboard",
)

USER_REPORT_FREE = (
    "your life, in plain words",
    "what i can see about you",
    "where life stands today",
    "\u092e\u0948\u0902 \u0906\u092a\u0915\u0947 \u092c\u093e\u0930\u0947 \u092e\u0947\u0902",   # Hindi: "what I can see about you"
)

HORARY_FREE = (
    "short answer in plain words",
    "prashna chart details",
    "significators",
    "judgment",          # the verdict itself is the hook
)

SECTION_RE = re.compile(
    r'(<section\b[^>]*>)(.*?)(</section>)', re.S | re.I
)
H2_RE = re.compile(r'<h[23][^>]*>(.*?)</h[23]>', re.S | re.I)


def _text(raw: str) -> str:
    s = re.sub(r"<[^>]+>", " ", raw or "")
    s = (s.replace("&amp;", "&").replace("&nbsp;", " ")
          .replace("&#39;", "'").replace("&quot;", '"'))
    return re.sub(r"\s+", " ", s).strip().lower()


def _title_of(block: str) -> str:
    m = H2_RE.search(block)
    return _text(m.group(1)) if m else ""


def _matches(title: str, needles: Iterable[str]) -> bool:
    return any(n in title for n in needles)


def _blocks(html: str) -> list[tuple[int, int]]:
    """
    Section spans as (start, end) offsets.

    Two report shapes exist in the engine:
      1. `<section class="section">` wrappers   (confluence, horary, lanes)
      2. flat `<h2 class="section-h">` headings (user_report / personal reading)
    For shape 2 a section runs from one h2 to the next.
    """
    secs = [(m.start(), m.end()) for m in SECTION_RE.finditer(html)
            if "voice-lead" not in html[m.start():m.start() + 120]]
    if len(secs) >= 2:
        return secs
    heads = [m.start() for m in re.finditer(r'<h2\b', html, re.I)]
    if len(heads) < 3:
        # user_report puts its life-area cards under h3 with a single h2
        heads = [m.start() for m in re.finditer(r'<h[23]\b', html, re.I)]
    if not heads:
        return []
    # stop before the closing wrapper so the tail keeps </body></html>
    stop = len(html)
    for pat in (r'</body>', r'<footer\b'):
        m = re.search(pat, html, re.I)
        if m:
            stop = min(stop, m.start())
    bounds = heads + [stop]
    return [(bounds[i], bounds[i + 1]) for i in range(len(heads))]


def split_report(html: str, free_titles: Iterable[str], *,
                 locked_note: str = "") -> dict:
    """
    Returns:
      {
        "free_html":  standalone HTML with only the free sections,
        "paid_html":  standalone HTML with only the paid sections,
        "free_sections": [titles...],
        "paid_sections": [titles...],
        "teasers": {title: first ~25 words} for paid sections,
      }
    """
    # the personal opening belongs on both halves, so pull it out first
    lead = ""
    m_lead = re.search(r'<section[^>]*voice-lead[^>]*>.*?</section>', html, re.S | re.I)
    if m_lead:
        lead = m_lead.group(0)
        html = html[:m_lead.start()] + html[m_lead.end():]

    blocks = _blocks(html)
    if not blocks:
        # No recognisable structure — safest default is to treat it all as paid.
        return {"free_html": lead, "paid_html": lead + html,
                "free_sections": [], "paid_sections": [], "teasers": {}}

    head = html[: blocks[0][0]]
    tail = html[blocks[-1][1]:]

    free_parts, paid_parts = [], []
    free_titles_out, paid_titles_out, teasers = [], [], {}

    for start, end in blocks:
        block = html[start:end]
        title = _title_of(block)
        display = re.sub(r"\s+", " ", (H2_RE.search(block).group(1) if H2_RE.search(block) else "")).strip()
        display = re.sub(r"<[^>]+>", "", display).replace("&amp;", "&")
        if _matches(title, free_titles):
            free_parts.append(block)
            free_titles_out.append(display)
        else:
            paid_parts.append(block)
            paid_titles_out.append(display)
            body = _text(re.sub(r'<h[23].*?</h[23]>', '', block, flags=re.S | re.I))
            words = body.split()
            teasers[display] = " ".join(words[:25]) + ("…" if len(words) > 25 else "")

    note = ""
    if locked_note and paid_parts:
        note = (
            '<section class="section" style="border:1px dashed #c9a227;'
            'background:rgba(201,162,39,.07);border-radius:14px">'
            f'<h2>🔒 {len(paid_parts)} more sections in the full report</h2>'
            f'<p>{locked_note}</p><ul>'
            + "".join(f"<li><b>{t}</b></li>" for t in paid_titles_out)
            + "</ul></section>"
        )

    return {
        "free_html": head + lead + "".join(free_parts) + note + tail,
        "paid_html": head + lead + "".join(paid_parts) + tail,
        "free_sections": free_titles_out,
        "paid_sections": paid_titles_out,
        "teasers": teasers,
    }


def split_confluence(html: str) -> dict:
    return split_report(
        html, CONFLUENCE_FREE,
        locked_note=("Your present-day reading is above. The full report opens every "
                     "life domain with its cross-system vote tables, the year-by-year "
                     "road map of your sub-periods, the challenge-preparation guide "
                     "and chart-targeted remedies."),
    )


def split_user_report(html: str) -> dict:
    return split_report(
        html, USER_REPORT_FREE,
        locked_note="Unlock to read every life area, with timing and remedies.",
    )


def split_horary(html: str) -> dict:
    return split_report(
        html, HORARY_FREE,
        locked_note=("You have the verdict. Unlock the reasoning: each technique's "
                     "testimony, the timing windows and the remedies."),
    )


def summarise(html: str) -> dict:
    """Structured peek at a report: verdict, confidence, section list."""
    out = {"sections": [], "verdict": None, "confidence": None}
    for m in SECTION_RE.finditer(html):
        t = H2_RE.search(m.group(0))
        if t:
            out["sections"].append(re.sub(r"<[^>]+>", "", t.group(1)).strip())
    v = re.search(r'\b(YES|LIKELY|UNCERTAIN|UNLIKELY|NO)\b', html)
    if v:
        out["verdict"] = v.group(1)
    c = re.search(r'confidence[^A-Za-z]{0,12}(HIGH|MEDIUM|LOW|VERY HIGH)', html, re.I)
    if c:
        out["confidence"] = c.group(1).upper()
    return out
