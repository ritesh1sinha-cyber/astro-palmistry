"""Compact conversational palm report — LLM-on path only.

Leaves ``palm_cards.render`` untouched. Chosen by ``palm_report`` when the
LLM layer is enabled and produced an accepted conversational overlay.
"""

from __future__ import annotations

import html as _html
from typing import Any


def _e(value: Any) -> str:
    return _html.escape(str(value or ""), quote=True)


_TITLE = {
    "character": "Character & Temperament",
    "mind": "Mind & Intellect",
    "love": "Relationships & Emotions",
    "career": "Career & Direction",
    "wealth": "Money & Resources",
    "health": "Health & Vitality",
}


def render(
    raw: dict,
    *,
    name: str = "Seeker",
    age: int = 30,
    gender: str = "other",
    dominant: str = "right",
    paid: bool = False,
    price: int = 298,
    prose: dict | None = None,
) -> str:
    del gender  # reserved for future gendered phrasing
    import report_shell as RS

    prose = prose if isinstance(prose, dict) else {}
    first = (name or "Seeker").split()[0]
    conf = raw.get("confluence") or {}
    dom_key = conf.get("dominant_hand") or dominant
    aspects = conf.get("life_aspects") or []
    aspect_by_key = {
        str(a.get("key") or ""): a for a in aspects if isinstance(a, dict)
    }

    personality = str(prose.get("personality") or "").strip()
    current_phase = str(prose.get("current_phase") or "").strip()
    hardest = str(prose.get("hardest_area_note") or "").strip()
    mind_now = [str(x).strip() for x in (prose.get("mind_now") or []) if str(x).strip()]
    why_now = str(prose.get("why_now") or "").strip()
    hand_note = str(prose.get("hand_contrast_note") or "").strip()
    areas = prose.get("areas") if isinstance(prose.get("areas"), dict) else {}

    blocks = []
    if personality:
        blocks.append(
            f'<section class="conv-block"><h2>Who you are</h2>'
            f"<p>{_e(personality)}</p></section>"
        )
    if current_phase or hardest:
        body = ""
        if current_phase:
            body += f"<p>{_e(current_phase)}</p>"
        if hardest:
            body += f'<p class="hardest">{_e(hardest)}</p>'
        blocks.append(
            f'<section class="conv-block"><h2>Where you are now</h2>{body}</section>'
        )

    if mind_now or why_now:
        bits = ""
        if mind_now:
            items = "".join(f"<li>{_e(line)}</li>" for line in mind_now[:3])
            bits += (
                '<p class="sec-note">These are the themes your hands make likely '
                "right now — not things we know about your life.</p>"
                f'<ul class="conv-mind">{items}</ul>'
            )
        if why_now:
            bits += f"<p>{_e(why_now)}</p>"
        blocks.append(
            f'<section class="conv-block">'
            f"<h2>What may be on your mind right now</h2>{bits}</section>"
        )

    if hand_note:
        blocks.append(
            f'<section class="conv-block"><h2>What you started with, and what you '
            f"have made of it</h2><p>{_e(hand_note)}</p></section>"
        )

    if paid and areas:
        rows = []
        order = [str(a.get("key") or "") for a in aspects if isinstance(a, dict)]
        for key in order:
            block = areas.get(key) or {}
            if not isinstance(block, dict):
                continue
            outlook = str(block.get("outlook") or "").strip()
            if not outlook:
                continue
            title = _TITLE.get(key) or str(
                (aspect_by_key.get(key) or {}).get("title") or key
            )
            strength = str((aspect_by_key.get(key) or {}).get("strength") or "moderate")
            timing = str(block.get("timing") or "").strip()
            manifestation = str(block.get("manifestation") or "").strip()
            remedy = str(block.get("remedy") or "").strip()
            passage = " ".join(x for x in (outlook, timing, manifestation) if x)
            bits = [f"<p>{_e(passage)}</p>"]
            if remedy:
                bits.append(
                    f'<p class="conv-help"><span class="ev-label">What helps</span> '
                    f"{_e(remedy)}</p>"
                )
            rows.append(
                f'<article class="card conv-area">'
                f'<div class="card-top"><span class="area">{_e(title)}</span>'
                f'<span class="pill mixed">{_e(strength.title())}</span></div>'
                f'{"".join(bits)}</article>'
            )
        if rows:
            blocks.append(
                '<section class="conv-block"><h2>Each part of your life</h2>'
                '<p class="sec-note">What your hands say, the life-stage window, '
                "and what helps when an area needs care.</p>"
                f'{"".join(rows)}</section>'
            )

    if not paid:
        blocks.append(f"""
<section class="buy" id="unlock">
  <h3>See every life area, with age windows and what helps</h3>
  <p>You have who you are and where your hands place you now. Unlock the
  short reading for each life area.</p>
  <a class="cta" href="#unlock" data-unlock="1">Unlock full reading · ₹{_e(price)}</a>
</section>""")

    body = "".join(blocks)
    extra = """
.conv-block{margin:22px 0}
.conv-block h2{font-size:1.15rem;margin:0 0 10px;color:#1f2430}
.conv-block p{margin:0 0 10px;line-height:1.55;color:#2c3140;font-size:.95rem}
.conv-block .hardest{font-weight:600}
.conv-block .sec-note{font-size:.86rem;color:#6b7280;margin:0 0 8px}
.conv-mind{margin:0 0 12px;padding-left:18px}
.conv-mind li{margin:0 0 7px;line-height:1.5;color:#2c3140;font-size:.95rem}
.conv-area{margin:14px 0}
.conv-timing,.conv-show,.conv-help{font-size:.88rem;color:#3d4250}
.conv-timing .ev-label,.conv-show .ev-label,.conv-help .ev-label{
  display:inline;margin-right:6px;font-weight:600;color:#6b7280;text-transform:uppercase;
  font-size:.72rem;letter-spacing:.04em}
"""
    return RS.page(
        f"{first} — your hands",
        body + f"<style>{extra}</style>",
        eyebrow=("Palm reading · unlocked" if paid else "Palm reading"),
        heading=f"{first}, here is what your hands are carrying.",
        sub=f"{age} years · {dom_key}-dominant · conversational reading",
    )
