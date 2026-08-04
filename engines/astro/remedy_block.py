"""Remedies and gemstones, wherever the reading turns difficult.

A prediction that closes on "this will be hard" and stops there is bad product
and worse ethics. Someone paying for a reading is usually paying because they
are worried, and the thing they actually want is something to *do*. That is
what a remedy is for.

Two rules keep this honest rather than exploitative:

1. **What not to wear is as important as what to wear.** The gemstone engine
   already refuses stones classically contraindicated for a chart — on the test
   chart it blocks Yellow Sapphire outright, because Jupiter rules the 8th and
   is debilitated there. Saying "do not wear this, here is a mantra instead" is
   the single most credible thing a remedy section can do, because it is the
   opposite of an upsell.

2. **Practical action comes before ritual.** Every block leads with something
   the reader can do on Monday morning that would help even if they believe
   none of this. The traditional remedy follows it, not the reverse.

Hope, not fear. No remedy here is framed as averting disaster — that is the
oldest trick in the trade and it is the reason people distrust astrologers.
"""

from __future__ import annotations

import html as _html
from typing import Any, Optional

PRACTICAL = {
    "Sun": "Take it to the person who can actually decide. This stalls one level below the authority.",
    "Moon": "Protect your sleep and the routine at home first — your judgement is downstream of both.",
    "Mars": "Stop escalating for one month and let the other side move first.",
    "Mercury": "Put it in writing, then re-read what you already sent.",
    "Jupiter": "Ask one senior person to speak for you. This opens through a sponsor, not through effort.",
    "Venus": "Repair the relationship before you press the request again.",
    "Saturn": "Finish the dull, verifiable part first. Saturn only blocks what is half-done.",
    "Rahu": "Verify the thing that looks too convenient.",
    "Ketu": "Loosen your grip for a fortnight. This one moves when you stop forcing it.",
}

WEAR_LABEL = {
    "recommended": ("Safe for you to wear", "up"),
    "test_required": ("Wear on trial first", "mixed"),
    "mantra_only": ("Do not wear the stone — mantra only", "mixed"),
    "avoid": ("Do not wear this stone", "down"),
}


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def build(pc: dict, *, domain: str = "", question: str = "",
          name: str = "") -> dict:
    """Gemstone safety plus the practical action, for one chart."""
    try:
        from gemstone_remedy import build_remedy_report
        rep = build_remedy_report(pc, client_name=name, domain=domain,
                                  question=question)
    except Exception:
        rep = {}

    wear = list(rep.get("primary_wear") or [])
    mantra_only = list(rep.get("mantra_only") or [])
    avoid = list(rep.get("avoid") or [])

    # The practical action follows the planet under most pressure, which is
    # normally the running period lord.
    dasha = rep.get("dasha") or {}
    lord = dasha.get("ad_lord") or dasha.get("md_lord") or ""
    return {"wear": wear, "mantra_only": mantra_only, "avoid": avoid,
            "practical_planet": lord,
            "practical": PRACTICAL.get(lord, ""),
            "lagna_lord": rep.get("lagna_lord", ""),
            "ok": bool(rep.get("ok", True))}


def _stone_row(item: dict) -> str:
    gem = item.get("gem") or {}
    verdict = str(item.get("verdict") or "")
    label, tone = WEAR_LABEL.get(verdict, ("Check with an astrologer", "mixed"))
    reasons = item.get("reasons") or []
    snap = item.get("snap") or {}
    detail = ""
    if verdict in ("recommended", "test_required"):
        detail = (f"{_e(gem.get('metal'))} · {_e(gem.get('finger'))} · "
                  f"first worn on a {_e(gem.get('day'))}")
    return f"""
  <li class="stone {tone}" data-verdict="{tone}">
    <div class="stone-top">
      <b>{_e(gem.get('gem'))}</b>
      <span class="stone-verdict">{_e(label)}</span>
    </div>
    <div class="stone-role">{_e(item.get('role', ''))}
      {f"— {_e(snap.get('planet'))} in your {_e(snap.get('house'))}th, {_e(snap.get('dignity','').replace('_',' '))}" if snap else ""}</div>
    {f'<div class="stone-detail">{detail}</div>' if detail else ''}
    {f'<div class="stone-why">{_e(reasons[0])}</div>' if reasons else ''}
    <div class="stone-alt"><b>Instead / alongside:</b>
      {_e(gem.get('mantra'))}{f" · {_e(gem.get('charity'))}" if gem.get('charity') else ""}</div>
  </li>"""


def render(block: dict, *, paid: bool = False, price: int = 0,
           heading: str = "What you can actually do about it",
           lede: str = "") -> str:
    """The remedy card. Leads with action, is explicit about what to avoid."""
    if not block:
        return ""
    practical = block.get("practical")
    stones = (block.get("wear") or []) + (block.get("mantra_only") or []) \
        + (block.get("avoid") or [])
    if not practical and not stones:
        return ""

    shown = stones if paid else stones[:1]
    hidden = max(0, len(stones) - len(shown))

    return f"""
<section class="remedy-card">
  <div class="ev-label">{_e(heading)}</div>
  {f'<p class="remedy-lede">{_e(lede)}</p>' if lede else ''}
  {f'''<div class="remedy-do">
    <div class="remedy-do-label">Start here — no belief required</div>
    <p>{_e(practical)}</p>
  </div>''' if practical else ''}
  {f'''<ul class="stones">{''.join(_stone_row(s) for s in shown)}</ul>''' if shown else ''}
  {f'''<div class="remedy-locked">
    <b>{hidden} more stone{'s' if hidden != 1 else ''} assessed for your chart</b>
    — including which ones are actively wrong for you, with metal, finger and
    the day to begin. {f'₹{price}' if price else ''}
  </div>''' if hidden and not paid else ''}
  <p class="fine">A remedy is not a lever that overrides the chart. It works the
  way preparation works — it changes what you are ready for when the timing
  turns.</p>
</section>"""
