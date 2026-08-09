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


def _ord(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    return f"{n}" + ("th" if 10 <= n % 100 <= 20
                     else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


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

_DIGNITY_PLAIN = {
    "exalted": "very strong",
    "moolatrikona": "on its best ground",
    "own_sign": "in its own sign",
    "friendly_sign": "comfortably placed",
    "neutral_sign": "neither strong nor weak",
    "enemy_sign": "under strain",
    "debilitated": "very weak",
}


def _dig_plain(code: str) -> str:
    key = (code or "").strip().lower()
    return _DIGNITY_PLAIN.get(key, key.replace("_", " "))


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
      {f". {_e(snap.get('planet'))} in your {_e(_ord(snap.get('house')))} house, {_e(_dig_plain(snap.get('dignity','')))}" if snap else ""}</div>
    {f'<div class="stone-detail">{detail}</div>' if detail else ''}
    {f'<div class="stone-why">{_e(reasons[0])}</div>' if reasons else ''}
    <div class="stone-alt"><b>Instead / alongside:</b>
      {_e(gem.get('mantra'))}{f" · {_e(gem.get('charity'))}" if gem.get('charity') else ""}</div>
  </li>"""


def _stones_group(items: list, *, tone: str, label: str) -> str:
    if not items:
        return ""
    return f"""
  <div class="stones-group {tone}">
    <div class="stones-group-label">{_e(label)}</div>
    <ul class="stones">{''.join(_stone_row(st) for st in items)}</ul>
  </div>"""


def render(block: dict, *, paid: bool = False, price: int = 0,
           heading: str = "What you can actually do about it",
           lede: str = "") -> str:
    """Remedies are paid. The refusals are free, and they do the selling.

    Operator's call and it is the sharper play: telling someone which stone is
    *wrong* for them costs us nothing and proves we are not just moving
    inventory. Every jeweller in the country will sell a Gemini a yellow
    sapphire; being the one who says "not you, not this stone, and here is the
    classical reason" is the whole trust argument in one paragraph.

    So the free view shows only the avoid list. The stones that would help, the
    metal, the finger, the day to begin, and the practical action all sit behind
    the paywall.

    Wear / do items are always in a green block; avoid / do-not-wear items in a
    red block — never interleaved in one list.
    """
    if not block:
        return ""
    avoid = block.get("avoid") or []
    mantra_only = block.get("mantra_only") or []
    wear = block.get("wear") or []
    practical = block.get("practical")

    if paid:
        do_block = ""
        if practical:
            do_block = f"""
  <div class="remedy-do">
    <div class="remedy-do-label">Do this first · no belief required</div>
    <p>{_e(practical)}</p>
  </div>"""
        wear_group = _stones_group(
            wear, tone="up",
            label="Gemstones · safe to wear")
        avoid_group = _stones_group(
            list(mantra_only) + list(avoid), tone="down",
            label="Do not wear · mantra and charity instead")
        return f"""
<section class="remedy-card">
  <div class="ev-label">{_e(heading)}</div>
  {f'<p class="remedy-lede">{_e(lede)}</p>' if lede else ''}
  {do_block}
  {wear_group}
  {avoid_group}
  <p class="fine">A remedy is not a lever that overrides the chart. It works the
  way preparation works — it changes what you are ready for when the timing
  turns.</p>
</section>"""

    # --- free view: refusals only ------------------------------------------
    refused = avoid + mantra_only
    helpful_count = len(wear)

    if not refused:
        # Nothing is contraindicated, which is itself worth saying.
        body = f"""
  <p class="remedy-lede">Nothing in your chart is actively harmed by a
  gemstone — which is less common than you would think, and good news.</p>
  <div class="remedy-locked">
    <b>{helpful_count} stone{'s' if helpful_count != 1 else ''} assessed as
    suitable for you</b>, with metal, finger and the day to begin, plus the
    practical steps that matter more than any of them.
  </div>"""
    else:
        body = f"""
  <p class="remedy-lede">Before anything we would sell you, here is what you
  should <b>not</b> wear. This is free because it is the part most people are
  never told.</p>
  {_stones_group(refused, tone="down",
                 label="Do not wear · already clear from your chart")}
  <div class="remedy-locked">
    <b>What you should wear is the other half.</b>
    {helpful_count} stone{'s' if helpful_count != 1 else ''} came back suitable
    for your chart — with the metal, the finger, the day to begin and the trial
    period — alongside the mantras, the charity, and the practical action that
    matters more than any stone.
  </div>"""

    return f"""
<section class="remedy-card">
  <div class="ev-label">Gemstones — what is wrong for you, free</div>
  {body}
  <p class="fine">Any jeweller will sell you the stone for your sign. Almost
  none will check whether your chart can carry it.</p>
</section>"""
