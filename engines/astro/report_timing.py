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

# Human focus phrases for paid window Why lines (no raw house/sector jargon).
AREA_FOCUS_PLAIN = {
    "career": "career and public standing",
    "money": "money and gains",
    "love": "relationship matters",
    "home": "home and family matters",
    "children": "children and creative matters",
    "health": "health and energy",
    "learning": "learning and guidance",
    "inner": "inner life and rest",
    "legal": "disputes and formal matters",
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


def _div_note_from_promise(promise: dict, area_key: str) -> str:
    """Surface the governing divisional vote in human-first wording."""
    try:
        from report_confluence import AREA_VARGA
    except Exception:  # noqa: BLE001
        return ""
    primary, _primary_name = AREA_VARGA.get(area_key, ("", ""))
    if not primary:
        return ""
    focus = AREA_FOCUS_PLAIN.get(area_key, "this part of life")
    direction = (promise or {}).get("direction", "mixed")
    if direction == "up":
        return (f"The {primary} chart provides additional support for {focus}")
    return (f"The {primary} chart provides additional context for {focus}")


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
    div_note = _div_note_from_promise(promise, area_key)
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
                "div_note": div_note,
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

def explain(row: dict, area_label: str, *, pc: Optional[dict] = None) -> str:
    """One sentence a reader can act on — manifestation-driven when evidence exists."""
    from report_language import trajectory_explain
    area = (row.get("area") or "").lower()
    strong = row["bav"] >= 5
    if row.get("aligned"):
        direction = "up"
    elif row.get("promise") == "down" and strong:
        direction = "down"
    elif not strong:
        direction = "mixed"
    else:
        direction = "mixed"

    # Preferred path: evidence → PredictionMeaning → age-at-window prose.
    if pc is not None:
        try:
            import report_confluence as CF
            from interpretation.evidence_builder import build_evidence
            from interpretation.life_stage import age_band_at
            from interpretation.prediction_meaning import build_meaning
            from narration.human_renderer import render_future_headline

            start = row.get("start")
            band = age_band_at(pc, start)
            dasha = CF.dasha_confluence(pc, start) if start else {}
            evidence = build_evidence(
                pc, area=area or "career",
                house=int(row.get("house") or 0),
                direction=direction, row=row, dasha=dasha,
                age_band=band, period_start=start, period_end=row.get("end"))
            meaning = build_meaning(evidence)
            line = render_future_headline(meaning)
            if line:
                return line
        except Exception:  # noqa: BLE001
            pass

    # Health stays lifestyle-oriented even on supportive windows.
    if area == "health" and direction == "up":
        return trajectory_explain(
            "up", "health", planet=row.get("planet") or "",
            variant=abs(hash((str(row.get("start")), row.get("planet")))) % 3)
    variant = abs(hash((str(row.get("start")), row.get("planet"), area))) % 9
    band = ""
    if pc is not None:
        try:
            from interpretation.life_stage import age_band_at
            band = age_band_at(pc, row.get("start"))
        except Exception:  # noqa: BLE001
            band = ""
    return trajectory_explain(
        direction, area or area_label, planet=row.get("planet") or "",
        variant=variant, age_band=band)


def _window_backing(row: dict) -> str:
    """Readable Why line for a timing window — human-first, still accurate."""
    from report_language import fix_house_ordinals
    area = row.get("area") or ""
    focus = AREA_FOCUS_PLAIN.get(area, "this part of life")
    promise = row.get("promise", "mixed")
    bits = [
        f"The birth chart reads {promise} on this area",
    ]
    div = (row.get("div_note") or "").strip()
    if div:
        bits.append(div[0].upper() + div[1:] if len(div) > 1 else div)
    planet = row.get("planet", "")
    if planet:
        strong = (row.get("bav") or 0) >= 5
        if strong:
            bits.append(
                f"{planet}'s movement gives additional support to {focus}")
        else:
            bits.append(
                f"{planet}'s movement gives some support to {focus}, "
                f"although the overall signal is more cautious")
    if row.get("period_owns_area"):
        bits.append("the running period also points here")
    return fix_house_ordinals(". ".join(bits).rstrip(".") + ".")


def render(pc: dict, rows: list, labels: dict) -> str:
    if not rows:
        return ""
    items = []
    for r in rows:
        # Age-aware label at window start (not only report today).
        label = labels.get(r["area"], r["area"].title())
        try:
            from interpretation.life_stage import age_band_at
            from narration.area_labels import area_label as _age_label
            band = age_band_at(pc, r.get("start"))
            label = _age_label(r["area"], band)
        except Exception:  # noqa: BLE001
            pass
        cls = "up" if r["aligned"] else ("down" if r["score"] < -0.4 else "mixed")
        items.append(f"""
  <li class="win {cls}">
    <div class="win-when">{_e(_pretty(r['start']))} → {_e(_pretty(r['end']))}</div>
    <div class="win-head">{_e(label)} · <span class="win-tag">{_e(
        'aligned' if r['aligned'] else 'partial')}</span></div>
    <p class="win-lead">{_e(explain(r, label, pc=pc))}</p>
    <p class="pred-why"><b>Why:</b> {_e(_window_backing(r))}</p>
  </li>""")
    return f"""
<h3 class="sec">Your strongest upcoming windows</h3>
<p class="sec-note">These are the windows where the birth promise
(including each area’s divisional chart), the running period, and a slow planet
crossing the right house all line up.</p>
<p class="sec-note"><b>Aligned</b> — birth chart, current timing and major planetary movement agree. <b>Partial</b> — some major factors agree, while others add caution or uncertainty.</p>
<ol class="windows-list">{''.join(items)}</ol>"""
