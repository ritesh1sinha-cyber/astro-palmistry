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

HOUSE_LIFE = {
    1: "your own health and how you are seen",
    2: "money and family",
    3: "siblings, short travel, and your own initiative",
    4: "home, property and your mother",
    5: "children, creativity and risk",
    6: "work, competition and health",
    7: "your closest relationship and any partnership",
    8: "things under the surface. Money you did not earn, and endings",
    9: "luck, teachers and your father",
    10: "career and public standing",
    11: "income, networks and gains",
    12: "expense, rest, travel and what you are letting go of",
}


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def _pretty(d: Optional[date]) -> str:
    return f"{d:%B %Y}" if d else ""


def _area_for_house(house: int) -> str:
    """Map house → report_confluence area key (same as question_answer)."""
    return {10: "career", 2: "money", 7: "love", 4: "home", 5: "children",
            1: "health", 9: "learning", 12: "inner", 6: "health",
            3: "career", 11: "money", 8: "health"}.get(int(house), "")


def build(pc: dict, *, today: Optional[date] = None) -> dict:
    """The present and the last six months, from period plus live transit."""
    today = today or date.today()
    back = today - timedelta(days=182)
    import predict_voice as PV
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
    predictions = []

    if ad:
        period_pred = PV.compose_period(pc, today=today, direction=dasha.get("direction", "mixed"))
        predictions.append(period_pred)

    if changed and then.get("ad"):
        shift = PV.Prediction(
            scenario=PV.polish_prose(
                f"The subject shifted inside the last six months, from "
                f"{then['md']}–{then['ad']} to {md}–{ad}. "
                f"That usually feels like a change of topic, not a change of luck."
            ),
            backing=f"sub-period changed from {then.get('ad', '')} to {ad}",
            direction="mixed",
        )
        predictions.append(shift)

    for t in live[:3]:
        h = t.get("house")
        theme = HOUSE_LIFE.get(h, "")
        if not theme or not t.get("since"):
            continue
        predictions.append(PV.transit_sentence(
            t["planet"], int(h), t["since"], t["until"],
            t.get("bav", 0), theme))

    try:
        import deep_evidence as DE
        seen_areas: set = set()
        for h in (active or [])[:2]:
            area = _area_for_house(h)
            if not area or area in seen_areas:
                continue
            seen_areas.add(area)
            house_transits = [x for x in live if x.get("house") == h]
            pred = PV.compose_from_area(
                pc, area, int(h), today=today, transits=house_transits)
            predictions.append(pred)
    except Exception as exc:  # noqa: BLE001
        print(f"[present_read] predict_voice skipped: {exc}", flush=True)

    if yog_now.get("yogini"):
        yog_pred = PV.Prediction(
            scenario=PV.polish_prose(
                f"The shorter lunar rhythm runs through {yog_now.get('lord', '')} "
                f"until {_pretty(CF._d(yog_now.get('end')))}. "
                f"Week-to-week mood follows that tone."
            ),
            backing=f"lunar cycle on {yog_now.get('yogini', '')} ({yog_now.get('lord', '')})",
            direction="mixed",
        )
        predictions.append(yog_pred)

    return {"today": today, "since": back, "predictions": predictions,
            "direction": dasha["direction"], "agreement": dasha["agreement"],
            "period": f"{md}–{ad}", "live": live,
            "active_houses": active}


def render(block: dict, *, tab: str = "") -> str:
    """Always free. This is the part that has to earn the rest."""
    preds = block.get("predictions") or []
    if not block or not preds:
        return ""
    items = "".join(f"<li>{p.html()}</li>" for p in preds)
    return f"""
<section class="present">
  <div class="present-head">
    <span class="ev-label">Where you are right now, free and checkable</span>
    <h3>The last six months, and what you are inside of today</h3>
  </div>
  <p class="present-lede">Read this before anything else. It describes a period
  you have just lived through, so you can judge it immediately. That is the
  point of putting it first.</p>
  <ul class="present-list pred-list">{items}</ul>
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
    <b>twenty-minute error moves your rising sign</b>. Once that moves,
    every house shifts, so every prediction built on it shifts with it. A
    reading that does not sound like you is usually a chart that is not quite
    yours.</p>
    <p>Three ways forward, in order of how much they need from you:</p>
    <ol class="mm-routes">
      <li><b>Birth-time rectification</b>. Give us four or five dates from your
      life and we test hundreds of candidate minutes against them, then rebuild
      your chart on the one that fits. This is the real fix.</li>
      <li><b>Ask a question instead</b>. A horary reading is cast from the
      moment you ask, so it needs <b>no birth time at all</b>. If your birth
      data is unreliable, this is the most accurate thing we can do for you.</li>
      <li><b>Read your palms</b>. Needs no birth data whatsoever. Your hands
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
