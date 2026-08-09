"""RETIRED AS A PROOF DEVICE — see report_recognition.py.

    This asked the customer for four dates and then announced which planetary
    period each fell in. It scored 4/4 on the test chart and looked superb.

    It was worthless, and measurably so: feeding it FABRICATED dates scored 76%
    on average and a perfect 4/4 in 35% of random trials. The customer supplies
    the fact, we supply the rationalisation. That is cold reading.

    What survives here is the event-collection form, which BTR genuinely needs
    as input for birth-time rectification. It is no longer presented to anyone
    as evidence that the method works.

Original docstring follows.

Prove the method on the customer's past before predicting their future.

Every paid competitor at the top of this market does one thing we did not:
they test the technique against events that have already happened. Kamal Kapoor
(₹6,600) leads with it — *"Before your future is mapped, your past is
verified."* It is the single strongest trust device in the category, and it
is the one claim in astrology that can actually be checked.

We already had the engine. `btr_rectify` scores candidate birth times by how
well each one lines up the customer's real life events against their dasha
periods. That scoring was only ever used to suggest a corrected birth time.
The same numbers answer a far more valuable question: **did your chart already
predict the things that happened to you?**

On the marketing, a deliberate position. The honest version of this claim is
stronger than the inflated one, because it is falsifiable:

    "Give us four dates from your life. We will tell you which planetary
     period was running for each one — before we say a word about your
     future. If the past does not line up, do not buy the future."

That invites the reader to test us, which is exactly what a sceptical Indian
buyer with ₹1,499 in hand wants to do. Nothing here overstates: a weak match
is reported as a weak match. The confidence of the offer comes from the engine
being good, not from the copy being loud.

The events themselves are also the input BTR needs, so asking for them serves
the customer twice — the free proof block, and a sharper chart from a
corrected birth time.
"""

from __future__ import annotations

import html as _html
from datetime import date, datetime
from typing import Any, Optional

# What we ask for. Four to five is the sweet spot: enough for the dasha match
# to be meaningful, few enough that people finish the form.
ASK_EVENTS = [
    ("first_job", "Your first job", "The month you started earning."),
    ("marriage", "Marriage", "Or the start of your longest relationship."),
    ("child", "A child arrived", "Skip if it does not apply."),
    ("higher_education", "College or a big course", "When you started."),
    ("relocation", "A move that mattered", "New city, or abroad."),
    ("loss", "A hard year", "Illness, a loss, or a job that ended badly."),
]

# Which planets classically own which event. Used to say WHY a period matched.
EVENT_SIGNIFICATORS = {
    "first_job": ("Saturn", "Sun", "Mercury"),
    "marriage": ("Venus", "Jupiter", "Moon"),
    "child": ("Jupiter", "Venus", "Moon"),
    "higher_education": ("Jupiter", "Mercury"),
    "relocation": ("Rahu", "Moon", "Mercury"),
    "loss": ("Saturn", "Ketu", "Mars"),
}

EVENT_LABEL = {k: v for k, v, _ in ASK_EVENTS}


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def _d(v: Any) -> Optional[date]:
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _period_at(pc: dict, when: date) -> dict:
    """Which periods were running on that date — all three systems.

    The precompute only stores antardashas for the CURRENT mahadasha, so a
    naive lookup returned a bare "Rahu" for every past event and the proof
    block scored 0 of 4 on a chart whose life events actually fit. Sub-periods
    are pure arithmetic; report_confluence computes them for any mahadasha.
    """
    from report_confluence import vimshottari_at, yogini_at, jaimini_at
    vim = vimshottari_at(pc, when)
    return {
        "md": vim.get("md", ""),
        "ad": vim.get("ad", ""),
        "yogini": (yogini_at(pc, when) or {}).get("lord", ""),
        "jaimini": (jaimini_at(pc, when) or {}).get("sign", ""),
    }


def check_event(pc: dict, key: str, when: date) -> dict:
    """Did the period running then actually own this kind of event?"""
    period = _period_at(pc, when)
    sig = EVENT_SIGNIFICATORS.get(key, ())
    # All three timing systems get a say, exactly as they do for a forward
    # prediction. Checking only Vimshottari would test one third of the method.
    lords = [p for p in (period.get("md"), period.get("ad"),
                         period.get("yogini")) if p]
    matched = sorted({p for p in lords if p in sig})

    hl = pc.get("house_lords", {}) or {}
    planets = pc.get("planets", {}) or {}
    house_for = {"first_job": 10, "marriage": 7, "child": 5,
                 "higher_education": 9, "relocation": 12, "loss": 8}.get(key)
    house_link = []
    if house_for:
        owner = (hl.get(str(house_for)) or {}).get("lord")
        for p in lords:
            if p == owner:
                house_link.append(f"{p} rules your {house_for}th")
            elif (planets.get(p) or {}).get("house") == house_for:
                house_link.append(f"{p} sits in your {house_for}th")

    strength = len(matched) + len(house_link)
    return {
        "key": key, "label": EVENT_LABEL.get(key, key), "date": when,
        "md": period.get("md", ""), "ad": period.get("ad", ""),
        "yogini": period.get("yogini", ""), "jaimini": period.get("jaimini", ""),
        "matched": matched, "house_link": house_link,
        "hit": strength >= 1, "strength": strength,
    }


def verify(pc: dict, events: dict) -> dict:
    """Score every supplied event. Honest about misses."""
    rows = []
    for key, value in (events or {}).items():
        when = _d(value)
        if not when:
            continue
        rows.append(check_event(pc, key.replace("btr_", ""), when))
    hits = sum(1 for r in rows if r["hit"])
    return {"rows": rows, "hits": hits, "total": len(rows),
            "rate": round(100 * hits / len(rows)) if rows else 0}


# ---------------------------------------------------------------------------

def render_ask(*, price: int = 999) -> str:
    """The invitation, shown before any dates are given."""
    fields = "".join(f"""
    <label class="ev"><span class="ev-name">{_e(label)}</span>
      <span class="ev-hint">{_e(hint)}</span>
      <input type="month" name="{_e(key)}" /></label>"""
                     for key, label, hint in ASK_EVENTS[:5])
    return f"""
<section class="proof">
  <h3>Before we tell you your future, let us prove it on your past</h3>
  <p>Give us four dates you already know. We will tell you which planetary
  period was running for each one, and whether that period is the one
  classical astrology says should have carried it — <b>before</b> you read a
  single prediction.</p>
  <p><b>If your past does not line up, do not buy the future.</b> That is the
  whole point of putting this first.</p>
  <form class="ev-form">{fields}
    <button type="submit" class="cta-dark">Check my past — free</button>
  </form>
  <p class="fine">Your dates also sharpen the reading itself: they let us
  correct your birth time to the minute, which every prediction downstream
  depends on. That correction is part of the full reading.</p>
</section>"""


def render_result(result: dict, *, price: int = 999, paid: bool = False) -> str:
    """What the check found. A miss is shown as a miss."""
    rows = result.get("rows") or []
    if not rows:
        return render_ask(price=price)

    items = []
    for r in rows:
        period = f"{r['md']}–{r['ad']}" if r["ad"] else r["md"]
        why = ""
        if r["matched"]:
            names = " and ".join(r["matched"])
            why = f"{names} is a classical significator for this."
        if r["house_link"]:
            why += (" " if why else "") + r["house_link"][0] + "."
        if not r["hit"]:
            why = ("The period running then is not the one classically "
                   "associated with this event.")
        items.append(f"""
    <li><span class="{'tick' if r['hit'] else 'miss'}">{'✓' if r['hit'] else '—'}</span>
      <span><b>{_e(r['label'])}</b>, {r['date']:%B %Y} — you were in the
      <b>{_e(period)}</b> period. {_e(why)}</span></li>""")

    hits, total, rate = result["hits"], result["total"], result["rate"]
    if rate >= 75:
        verdict = (f"<b>{hits} of {total} matched.</b> Your chart's timing "
                   f"describes your actual life. That is the basis on which "
                   f"everything below is calculated.")
    elif rate >= 50:
        verdict = (f"<b>{hits} of {total} matched.</b> A solid but imperfect "
                   f"fit — which usually means your recorded birth time is a "
                   f"little off. Correcting it tightens every prediction below.")
    else:
        verdict = (f"<b>Only {hits} of {total} matched.</b> Said plainly: on "
                   f"your stated birth time, the timing does not line up well. "
                   f"That almost always means the birth time is wrong rather "
                   f"than the method — which is exactly what the birth-time "
                   f"correction fixes.")

    upsell = "" if paid else f"""
  <div class="proof-cta">
    <p>The full birth-time correction tests hundreds of candidate minutes
    against these same events and returns the one that fits best — then
    rebuilds your chart on it.</p>
  </div>"""

    return f"""
<section class="proof">
  <h3>We checked your past first</h3>
  <p>{verdict}</p>
  <ul class="hits">{''.join(items)}</ul>
  {upsell}
</section>"""
