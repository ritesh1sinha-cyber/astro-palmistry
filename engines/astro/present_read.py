"""What is happening to you right now, and what the last six months were.

This is the conversion engine, and it works for one reason: it is the only
claim in the product the reader can check instantly. A prediction about 2030
cannot be judged today. "The last six months have been about X" either lands or
it does not, and the reader knows which within two seconds.

So every tab opens with it, and it is always free. Withholding this would be
strategically stupid as well as unkind — it is the evidence that the rest is
worth paying for.

The mismatch path matters as much as the match. If someone reads this and it is
simply wrong, the most likely explanation is not that astrology failed; it is
that the birth time is wrong by enough to move the ascendant. A twenty-minute
error rotates every house. So a "this does not sound like me" response routes
to birth-time rectification, to a horary question (which needs no birth time at
all), or to palmistry (which needs no birth data whatsoever).

That is honest — it is genuinely the most likely cause — and it happens to be
the most commercially useful thing we can say at that moment. Both being true
at once is the ideal case, not a coincidence to hide.
"""

from __future__ import annotations

import html as _html
from datetime import date, timedelta
from typing import Any, Optional

# What the running period lord does to the six months a person just lived.
PERIOD_FEELING = {
    "Sun": "visibility — being judged, seen, or measured by someone senior",
    "Moon": "emotional weather at home, and how much of it you were carrying",
    "Mars": "friction and effort — pushing against something that would not move",
    "Mercury": "conversations, paperwork, and negotiation that would not settle",
    "Jupiter": "expansion, advice, and doors that opened partway",
    "Venus": "relationships, comfort, and what you were willing to spend for both",
    "Saturn": "weight, delay, and doing the unglamorous work with no applause",
    "Rahu": "restlessness, and wanting something that is not quite in reach",
    "Ketu": "detachment — losing interest in something you used to care about",
}

HOUSE_LIFE = {
    1: "your own health and how you are seen",
    2: "money and family",
    3: "siblings, short travel, and your own initiative",
    4: "home, property and your mother",
    5: "children, creativity and risk",
    6: "work, competition and health",
    7: "your closest relationship and any partnership",
    8: "things under the surface — money you did not earn, and endings",
    9: "luck, teachers and your father",
    10: "career and public standing",
    11: "income, networks and gains",
    12: "expense, rest, travel and what you are letting go of",
}


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def _pretty(d: Optional[date]) -> str:
    return f"{d:%B %Y}" if d else ""


def _ord(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    return f"{n}" + ("th" if 10 <= n % 100 <= 20
                     else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def _area_for_house(house: int) -> str:
    """Map house → report_confluence area key (same as question_answer)."""
    return {10: "career", 2: "money", 7: "love", 4: "home", 5: "children",
            1: "health", 9: "learning", 12: "inner", 6: "health",
            3: "career", 11: "money", 8: "health"}.get(int(house), "")


def build(pc: dict, *, today: Optional[date] = None) -> dict:
    """The present and the last six months, from period plus live transit."""
    today = today or date.today()
    back = today - timedelta(days=182)
    import report_confluence as CF
    import report_timing as RT

    now = CF.vimshottari_at(pc, today)
    then = CF.vimshottari_at(pc, back)
    yog_now = CF.yogini_at(pc, today) or {}
    dasha = CF.dasha_confluence(pc, today)

    planets = pc.get("planets", {}) or {}
    hl = pc.get("house_lords", {}) or {}

    def houses_of(lord: str) -> list:
        if not lord:
            return []
        out = [int(h) for h, v in hl.items() if v.get("lord") == lord]
        sits = (planets.get(lord) or {}).get("house")
        if sits:
            out.append(int(sits))
        return sorted(set(out))

    ad = now.get("ad", "")
    md = now.get("md", "")
    active = houses_of(ad) or houses_of(md)

    # what is actually crossing a house right now
    segments = RT.transit_segments(pc, start=today - timedelta(days=200), years=1)
    live = []
    for planet, segs in segments.items():
        for seg in segs:
            s, e = seg.get("start"), seg.get("end")
            if s and e and s <= today <= e:
                live.append({"planet": planet, "house": seg.get("house"),
                             "sign": seg.get("sign"), "bav": seg.get("bav"),
                             "since": s, "until": e})

    changed = (then.get("ad") != ad)
    lines = []
    if ad:
        lines.append(
            f"You are in the <b>{_e(md)}–{_e(ad)}</b> period. In practice that "
            f"has meant <b>{_e(PERIOD_FEELING.get(ad, 'a shift in emphasis'))}</b>.")
    if changed and then.get("ad"):
        lines.append(
            f"It changed over from {_e(then['md'])}–{_e(then['ad'])} inside the "
            f"last six months, which is usually felt as a change of subject "
            f"rather than a change of luck.")
    if active:
        named = " and ".join(HOUSE_LIFE.get(h, "") for h in active[:2] if HOUSE_LIFE.get(h))
        if named:
            lines.append(f"The part of life it points at is <b>{named}</b>.")
    for t in live:
        if t["house"] and HOUSE_LIFE.get(t["house"]):
            lines.append(
                f"<b>{_e(t['planet'])}</b> has been crossing your "
                f"{_ord(t['house'])} house since {_e(_pretty(t['since']))} — "
                f"{_e(HOUSE_LIFE[t['house']])} — and stays there until "
                f"{_e(_pretty(t['until']))}. It carries {t['bav']} of 8 support "
                f"points there, so it is "
                f"{'delivering rather than just promising' if (t['bav'] or 0) >= 5 else 'more pressure than payoff'}.")
    if yog_now.get("yogini"):
        lines.append(
            f"The lunar cycle is on <b>{_e(yog_now.get('yogini'))}</b> "
            f"({_e(yog_now.get('lord'))}) until "
            f"{_e(_pretty(__import__('report_confluence')._d(yog_now.get('end'))))}.")

    # Multi-technique confluence for the houses this period activates —
    # clubs Parashari / SAV / dasha agreement even when systems word themes differently.
    conf_bits = []
    try:
        for h in (active or [])[:2]:
            area = _area_for_house(h)
            if not area:
                continue
            v = CF.area_verdict(pc, area, h)
            label = HOUSE_LIFE.get(h, area)
            tone = {"up": "supportive", "down": "demanding", "mixed": "mixed"}.get(
                v.get("direction"), "mixed")
            conf_bits.append(
                f"Across methods, <b>{_e(label)}</b> reads as <b>{tone}</b> "
                f"({_e(v.get('agreement') or v.get('label') or '')}).")
        if conf_bits:
            lines.extend(conf_bits)
    except Exception as exc:  # noqa: BLE001
        print(f"[present_read] area confluence skipped: {exc}", flush=True)

    # Deep-dive evidence for the houses this period activates
    try:
        import deep_evidence as DE
        seen_areas: set = set()
        for h in (active or [])[:2]:
            area = _area_for_house(h)
            if not area or area in seen_areas:
                continue
            seen_areas.add(area)
            de = DE.for_area(area, house=h)
            if de.get("varga", {}).get("diagnosis"):
                lines.append(f"<b>{_e(HOUSE_LIFE.get(h, area))}</b>: "
                             f"{_e(de['varga']['diagnosis'])}")
            cw = de.get("current_window") or {}
            if cw.get("word"):
                lines.append(
                    f"For this area, the running period is "
                    f"<b>{_e(cw.get('word', ''))}</b>"
                    + (f" — {_e(cw['reason'][:90])}" if cw.get("reason") else ""))
            if de.get("transit", {}).get("note"):
                lines.append(f"In the sky now: {_e(de['transit']['note'])}")
    except Exception as exc:  # noqa: BLE001
        print(f"[present_read] deep evidence skipped: {exc}", flush=True)

    return {"today": today, "since": back, "lines": lines,
            "direction": dasha["direction"], "agreement": dasha["agreement"],
            "period": f"{md}–{ad}", "live": live,
            "active_houses": active}


def render(block: dict, *, tab: str = "") -> str:
    """Always free. This is the part that has to earn the rest."""
    if not block or not block.get("lines"):
        return ""
    items = "".join(f"<li>{line}</li>" for line in block["lines"])
    return f"""
<section class="present">
  <div class="present-head">
    <span class="ev-label">Where you are right now — free, and checkable</span>
    <h3>The last six months, and what you are inside of today</h3>
  </div>
  <p class="present-lede">Read this before anything else. It describes a period
  you have just lived through, so you can judge it immediately — that is the
  point of putting it first.</p>
  <ul class="present-list">{items}</ul>
  <div class="present-ask">
    <span>Does this describe your last six months?</span>
    <button type="button" class="pillbtn" data-mm="yes">Yes, closely</button>
    <button type="button" class="pillbtn" data-mm="partly">Partly</button>
    <button type="button" class="pillbtn" data-mm="no">Not at all</button>
  </div>
  {mismatch_modal(tab)}
</section>"""


def mismatch_modal(tab: str = "") -> str:
    """Shown when the reader says the present reading is wrong.

    A wrong reading here is diagnostic, not a dead end: a birth time off by
    twenty minutes rotates every house, which changes every prediction
    downstream. So the honest answer and the useful answer are the same one.
    """
    return """
<div class="mm-overlay" id="mismatch" hidden>
  <div class="mm-box">
    <div class="ev-label">Then something upstream is wrong</div>
    <h3>Most likely, your birth time is not accurate.</h3>
    <p>This is the common case, not a rare one. Hospital records round to the
    nearest five or ten minutes, and families remember approximately. A
    <b>twenty-minute error moves your rising sign</b> — and once that moves,
    every house shifts, so every prediction built on it shifts with it. A
    reading that does not sound like you is usually a chart that is not quite
    yours.</p>
    <p>Three ways forward, in order of how much they need from you:</p>
    <ol class="mm-routes">
      <li><b>Birth-time rectification</b> — give us four or five dates from your
      life and we test hundreds of candidate minutes against them, then rebuild
      your chart on the one that fits. This is the real fix.</li>
      <li><b>Ask a question instead</b> — a horary reading is cast from the
      moment you ask, so it needs <b>no birth time at all</b>. If your birth
      data is unreliable, this is the most accurate thing we can do for you.</li>
      <li><b>Read your palms</b> — needs no birth data whatsoever. Your hands
      are their own record.</li>
    </ol>
    <div class="mm-actions">
      <a class="cta-dark" href="#" data-nav="btr">Fix my birth time</a>
      <a class="cta-light" href="#" data-nav="horary">Ask a question instead</a>
      <a class="cta-light" href="#" data-nav="read">Read my palms</a>
    </div>
    <button type="button" class="mm-close" data-close="1">Close</button>
  </div>
</div>"""
