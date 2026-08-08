"""When it actually happens: the promise, the period, and the trigger.

The classical rule this implements — and the reason the old timeline was weak —
is that **a dasha does not produce an event on its own.** Three things have to
line up:

  1. **The promise (static).** Does the birth chart offer this at all? Read
     from the house, its lord, the governing divisional chart and Ashtakavarga.
     A chart that does not promise wealth will not manufacture it in a good
     period; the period only delivers what the chart holds.

  2. **The period (dynamic).** Is a dasha running that owns this area? Checked
     across all three systems — Vimshottari, Yogini and Jaimini — because one
     system alone is one opinion.

  3. **The trigger (dynamic).** Is a slow planet actually transiting the
     relevant house right now? Jupiter and Saturn are the ones that matter for
     life events; the Moon moves too fast to mark anything lasting.

And the filter most reports skip: **Ashtakavarga decides whether a transit
delivers.** Jupiter crossing a sign where it holds 7 bindus and Jupiter
crossing a sign where it holds 2 are not the same transit — the first opens
doors, the second is Jupiter making promises it cannot keep. Reading "Jupiter
transits your 10th" without the bindu count is the single most common way an
otherwise correct prediction goes wrong.

So a window is only reported as strong when the promise exists, at least two
timing systems agree, and a transit with real Ashtakavarga backing is over the
house. That intersection is rare, which is exactly the point: it is what makes
a dated prediction worth something.
"""

from __future__ import annotations

import html as _html
from datetime import date, timedelta
from typing import Any, Optional

SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")

#: The slow planets. Fast ones do not mark events that last.
TRIGGERS = ("Jupiter", "Saturn")

TRANSIT_VOICE = {
    "Jupiter": ("opens", "expansion, sponsorship and permission"),
    "Saturn": ("tests", "delay, weight and what you must earn"),
}


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def _pretty(d: Optional[date]) -> str:
    return f"{d:%b %Y}".replace(" 0", " ") if d else ""


def _ord(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    return f"{n}" + ("th" if 10 <= n % 100 <= 20
                     else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


# ---------------------------------------------------------------------------

def transit_segments(pc: dict, *, start: Optional[date] = None,
                     years: int = 5) -> dict:
    """Jupiter and Saturn sign-by-sign, with the bindu score for each stay."""
    start = start or date.today()
    end = start + timedelta(days=365 * years)
    out: dict = {}
    try:
        from vedic_ashtakavarga_report import AV, transit_timeline
        av = AV(pc)
    except Exception:
        return out
    for planet in TRIGGERS:
        try:
            out[planet] = transit_timeline(av, planet, start, end)
        except Exception:
            out[planet] = []
    return out


def windows_for_area(pc: dict, area_key: str, house: int, *,
                     start: Optional[date] = None, years: int = 5,
                     segments: Optional[dict] = None) -> list:
    """Every window in which promise, period and trigger line up on one area."""
    start = start or date.today()
    try:
        import report_confluence as CF
    except Exception:
        return []

    promise = CF.area_verdict(pc, area_key, house)
    segments = segments if segments is not None else transit_segments(
        pc, start=start, years=years)

    hl = (pc.get("house_lords", {}) or {}).get(str(house)) or {}
    lord = hl.get("lord", "")
    planets = pc.get("planets", {}) or {}

    rows = []
    for planet, segs in segments.items():
        for seg in segs:
            if seg.get("house") != house:
                continue
            when = seg.get("start")
            if not when or when > start + timedelta(days=365 * years):
                continue

            # the period, across all three systems
            probe = max(when, start)
            dasha = CF.dasha_confluence(pc, probe)
            vim = CF.vimshottari_at(pc, probe)
            lords = [vim.get("md"), vim.get("ad")]
            owns = any(
                p and (p == lord or (planets.get(p) or {}).get("house") == house)
                for p in lords)

            bav = seg.get("bav", 0)
            # Ashtakavarga is the filter: the same transit is a different event
            # at 7 bindus and at 2.
            trigger = 1.0 if bav >= 5 else (-1.0 if bav <= 3 else 0.0)
            if planet == "Saturn":
                trigger -= 0.3          # Saturn asks for work even when supported

            score = (promise["score"] * 0.4
                     + dasha["score"] * 0.3
                     + trigger * 0.3
                     + (0.4 if owns else 0.0))

            rows.append({
                "area": area_key, "house": house,
                "start": when, "end": seg.get("end"),
                "planet": planet, "sign": seg.get("sign", ""),
                "bav": bav, "sav": seg.get("sav"),
                "promise": promise["direction"], "promise_score": promise["score"],
                "dasha": dasha["direction"],
                "dasha_label": " · ".join(r["label"] for r in dasha["readings"]),
                "period_owns_area": owns,
                "score": round(score, 2),
                "aligned": (promise["direction"] != "down"
                            and dasha["direction"] != "down"
                            and bav >= 5),
            })
    rows.sort(key=lambda r: r["start"])
    return rows


def best_windows(pc: dict, areas: list, *, start: Optional[date] = None,
                 years: int = 5, limit: int = 5,
                 lat: Optional[float] = None, lon: Optional[float] = None,
                 tz: float = 5.5) -> list:
    """The handful of windows worth naming, across every life area."""
    start = start or date.today()
    segments = transit_segments(pc, start=start, years=years)
    allrows = []
    for key, house in areas:
        allrows += windows_for_area(pc, key, house, start=start,
                                    years=years, segments=segments)
    # Boost scores with deep-evidence period-clock rating when cache is active
    try:
        import deep_evidence as DE
        de_ctx = DE.current()
        if de_ctx:
            for r in allrows:
                de = de_ctx.for_area(r["area"], house=r.get("house", 0))
                rating = de.get("current_rating", "mix")
                boost = {"fav": 0.4, "mix": 0.0, "chal": -0.4}.get(rating, 0)
                r["score"] = round(r.get("score", 0) + boost, 2)
                if de.get("evidence_lines"):
                    r["deep_note"] = de["evidence_lines"][0][:120]
    except Exception:  # noqa: BLE001
        pass
    # strongest first, but never two of the same area back to back
    allrows.sort(key=lambda r: -abs(r["score"]))
    picked, seen = [], set()
    for r in allrows:
        if r["area"] in seen and len(picked) < limit:
            continue
        picked.append(r)
        seen.add(r["area"])
        if len(picked) >= limit:
            break
    picked.sort(key=lambda r: r["start"])
    return picked


# ---------------------------------------------------------------------------

def explain(row: dict, area_label: str) -> str:
    """One sentence a reader can act on, with the reasoning underneath."""
    if row.get("deep_note"):
        return row["deep_note"]
    verb, theme = TRANSIT_VOICE.get(row["planet"], ("moves through", ""))
    strong = row["bav"] >= 5
    if row["aligned"]:
        lead = (f"{area_label} is the thing to push in this window.")
    elif row["promise"] == "down" and strong:
        lead = (f"A real opening in {area_label.lower()}, but your chart does "
                f"not promise much here — take it, do not bet on it.")
    elif not strong:
        lead = (f"{row['planet']} reaches {area_label.lower()} in this window "
                f"but arrives weak. Expect the offer without the delivery.")
    else:
        lead = f"A mixed window for {area_label.lower()}."
    return lead


def render(pc: dict, rows: list, labels: dict) -> str:
    if not rows:
        return ""
    items = []
    for r in rows:
        label = labels.get(r["area"], r["area"].title())
        verb, theme = TRANSIT_VOICE.get(r["planet"], ("moves through", ""))
        cls = "up" if r["aligned"] else ("down" if r["score"] < -0.4 else "mixed")
        items.append(f"""
  <li class="win {cls}">
    <div class="win-when">{_e(_pretty(r['start']))} → {_e(_pretty(r['end']))}</div>
    <div class="win-head">{_e(label)} · <span class="win-tag">{_e(
        'aligned' if r['aligned'] else 'partial')}</span></div>
    <p class="win-lead">{_e(explain(r, label))}</p>
    <ul class="win-why">
      <li><b>Promise</b> — your chart reads {_e(r['promise'])} on this area</li>
      <li><b>Period</b> — {_e(r['dasha_label'])}
          {'· and it activates this area directly' if r['period_owns_area'] else ''}</li>
      <li><b>Trigger</b> — {_e(r['planet'])} {_e(verb)} your {_ord(r['house'])}
          house from {_e(r['sign'])}, carrying <b>{r['bav']} of 8</b> support
          points there{' — strong enough to deliver' if r['bav'] >= 5
                       else ' — too weak to deliver on its own'}</li>
    </ul>
  </li>""")
    return f"""
<h3 class="sec">When it actually happens</h3>
<p class="sec-note">A period on its own does not make an event. These are the
windows where your chart's promise, the running period, and a slow planet
crossing the right house all line up — and where that planet has the classical
support points to deliver.</p>
<ol class="windows-list">{''.join(items)}</ol>"""
