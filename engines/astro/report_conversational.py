"""Compact conversational astrology report — LLM-on path only.

Leaves ``report_cards.render`` untouched. Chosen by ``report_render`` when the
LLM layer is enabled and produced an accepted conversational overlay.
"""

from __future__ import annotations

import html as _html
from datetime import date
from typing import Any, Optional

from report_shell import EXTRA as _EXTRA
from report_shell import INTERACT as _INTERACT
from report_shell import STYLE as _STYLE

from llm.fallback import area_tone


def _e(value: Any) -> str:
    return _html.escape(str(value or ""), quote=True)


def _area_label(area: str, cards: list) -> str:
    for c in cards or []:
        if getattr(c, "area", "") == area:
            return str(getattr(c, "label", "") or area)
    return area.replace("_", " ").title()


def _pill(block: dict, card: Any) -> str:
    """Chip built from the same promise/activation facts as the paragraph."""
    label = str((block or {}).get("tone_label") or "").strip()
    cls = str((block or {}).get("tone_class") or "mixed").strip()
    if not label:
        if card is None:
            return ""
        label, cls = area_tone(card)
    return f'<span class="pill {cls}">{_e(label)}</span>'


def render(
    pc: dict,
    *,
    name: str = "",
    question_html: str = "",
    price: int = 298,
    today: Optional[date] = None,
    paid: bool = False,
    proof_html: str = "",
    daily_html: str = "",
    timing_html: str = "",
    cards: Optional[list] = None,
    prose: Optional[dict] = None,
    footer_unlock: bool = True,
    remedy_html: str = "",
) -> str:
    """Same call shape as ``report_cards.render``; ignores proof/timing HTML.

    ``remedy_html`` is the deterministic gemstone/remedy block the classic page
    also carries. It is Python's, not the model's — which is exactly why the
    conversational page keeps it rather than asking for the same advice in
    prose: a stone, a metal and a day to begin are facts, not tone.
    """
    del question_html, proof_html, daily_html, timing_html  # classic sections unused
    today = today or date.today()
    prose = prose if isinstance(prose, dict) else {}
    cards = list(cards or [])
    first = (name or "").split()[0] if name else "You"
    lagna = (pc.get("lagna") or {}).get("sign", "")
    moon = (pc.get("planets", {}) or {}).get("Moon") or {}

    personality = str(prose.get("personality") or "").strip()
    current_phase = str(prose.get("current_phase") or "").strip()
    recent_months = str(prose.get("recent_months") or "").strip()
    hardest = str(prose.get("hardest_area_note") or "").strip()
    mind_now = [str(x).strip() for x in (prose.get("mind_now") or []) if str(x).strip()]
    why_now = str(prose.get("why_now") or "").strip()
    family_note = [str(x).strip() for x in (prose.get("family_note") or []) if str(x).strip()]
    areas = prose.get("areas") if isinstance(prose.get("areas"), dict) else {}

    free_blocks = []
    if personality:
        # The people around them belong in the same breath as who they are:
        # a reader checks the father and the mother against a life they
        # already know, which is what makes the rest of the page credible.
        family_html = ""
        if paid and family_note:
            items = "".join(f"<li>{_e(line)}</li>" for line in family_note[:4])
            family_html = (
                "<h3>The family you come from</h3>"
                '<p class="sec-note">Read from your birth details alone — '
                "nothing here was told to us.</p>"
                f'<ul class="conv-family">{items}</ul>'
            )
        free_blocks.append(
            f'<section class="conv-block">'
            f'<h2>Who you are</h2><p>{_e(personality)}</p>'
            f"{family_html}</section>"
        )
    if current_phase:
        free_blocks.append(
            f'<section class="conv-block">'
            f'<h2>Where you are now</h2><p>{_e(current_phase)}</p></section>'
        )
    if mind_now or why_now:
        bits = ""
        if mind_now:
            items = "".join(f"<li>{_e(line)}</li>" for line in mind_now[:3])
            # The disclaimer is Python's, not the model's: the reading knows
            # what the chart makes likely, never what is actually happening.
            bits += (
                '<p class="sec-note">These are the themes your chart makes likely '
                "right now — not things we know about your life.</p>"
                f'<ul class="conv-mind">{items}</ul>'
            )
        if why_now:
            bits += f"<p>{_e(why_now)}</p>"
        free_blocks.append(
            f'<section class="conv-block">'
            f"<h2>What may be on your mind right now</h2>{bits}</section>"
        )
    if recent_months or hardest:
        body = ""
        if recent_months:
            body += f"<p>{_e(recent_months)}</p>"
        if hardest:
            body += f'<p class="hardest">{_e(hardest)}</p>'
        free_blocks.append(
            f'<section class="conv-block">'
            f'<h2>The last few months</h2>{body}</section>'
        )

    paid_blocks = []
    if paid and areas:
        rows = []
        # Preserve card order from the engine.
        ordered = [getattr(c, "area", "") for c in cards if getattr(c, "area", "")]
        for area in ordered:
            block = areas.get(area) or {}
            if not isinstance(block, dict):
                continue
            outlook = str(block.get("outlook") or "").strip()
            if not outlook:
                continue
            timing = str(block.get("timing") or "").strip()
            manifestation = str(block.get("manifestation") or "").strip()
            remedy = str(block.get("remedy") or "").strip()
            card = next((c for c in cards if getattr(c, "area", "") == area), None)
            # One flowing passage — situation, then when, then how it shows up.
            passage = " ".join(x for x in (outlook, timing, manifestation) if x)
            bits = [f"<p>{_e(passage)}</p>"]
            if remedy:
                bits.append(
                    f'<p class="conv-help"><span class="ev-label">What helps</span> '
                    f"{_e(remedy)}</p>"
                )
            rows.append(
                f'<article class="card conv-area">'
                f'<div class="card-top"><span class="area">{_e(_area_label(area, cards))}</span>'
                f"{_pill(block, card)}</div>"
                f'{"".join(bits)}</article>'
            )
        if rows:
            paid_blocks.append(
                '<section class="conv-block">'
                "<h2>Each part of your life</h2>"
                '<p class="sec-note">What is promised, when it tends to show, '
                "and what helps if pressure appears.</p>"
                f'{"".join(rows)}</section>'
            )

    unlock = ""
    if (not paid) and footer_unlock:
        unlock = f"""
<section class="buy" id="unlock">
  <h3>See every life area, with timing and what helps</h3>
  <p>You have who you are, the chapter you are in, and the recent months you
  can check. Unlock the short reading for each life area.</p>
  <a class="cta" href="#unlock" data-unlock="1">Unlock full reading · ₹{_e(price)}</a>
</section>"""

    body = "".join(free_blocks + paid_blocks) + (remedy_html or "") + unlock
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{_e(first)} — your reading</title>
<style>{_STYLE}{_EXTRA}
.conv-block{{margin:22px 0}}
.conv-block h2{{font-size:1.15rem;margin:0 0 10px;color:#1f2430}}
.conv-block h3{{font-size:.95rem;margin:18px 0 6px;color:#1f2430}}
.conv-block p{{margin:0 0 10px;line-height:1.55;color:#2c3140;font-size:.95rem}}
.conv-block .hardest{{font-weight:600}}
.conv-mind,.conv-family{{margin:0 0 12px;padding-left:18px}}
.conv-mind li,.conv-family li{{margin:0 0 7px;line-height:1.5;color:#2c3140;
  font-size:.95rem}}
.conv-area{{margin:14px 0}}
.conv-timing,.conv-show,.conv-help{{font-size:.88rem;color:#3d4250}}
.conv-timing .ev-label,.conv-show .ev-label,.conv-help .ev-label{{
  display:inline;margin-right:6px;font-weight:600;color:#6b7280;text-transform:uppercase;
  font-size:.72rem;letter-spacing:.04em}}
</style></head><body><div class="wrap">
<header>
  <div class="eyebrow">Your reading</div>
  <h1>{_e(first)}, here is what matters now.</h1>
  <div class="chartline">{_e(lagna)} rising · Moon in {_e(moon.get('sign', ''))}
  · read {today:%d %B %Y}</div>
</header>
{body}
<footer>Calculated from your birth details alone · guidance, not a substitute
for professional advice</footer>
</div>{_INTERACT}</body></html>"""
    from qa_checks.final_customer_boundary import finalize_customer_html
    return finalize_customer_html(html, strict=True)
