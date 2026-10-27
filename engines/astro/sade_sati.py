"""Sade Sati: the seven-and-a-half-year stretch when Saturn crosses the sign before the
birth Moon, the Moon's own sign, and the sign after it.

It is the best-known timing event in Vedic astrology, and readers worry about it, so the full
report always says whether it is running, which phase, when each phase begins and ends, and
what to do about it. Saturn's sign changes are computed from the ephemeris (not estimated);
the wording is fixed text, so nothing here depends on a model.

Free page: where you are in it and how to carry it (no dates, no remedies).
Paid page: the dated phases, the hardest stretch, the cautions and the remedies.
"""
from __future__ import annotations

import html
from datetime import date, timedelta
from typing import Any, Optional

_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
           "October", "November", "December")
_PHASE = {12: "Rising phase", 1: "Peak phase", 2: "Setting phase"}
_PHASE_TEXT = {
    12: ("Saturn is in the sign before your Moon. Expenses tend to climb, sleep and peace of mind get "
         "disturbed, and old habits and routines are questioned. Slow down spending and keep your routine steady."),
    1: ("Saturn is over your Moon itself, the heaviest stretch for mood and self-image. Responsibility feels "
        "large, and health, work or close relationships ask for patience. Avoid big irreversible decisions "
        "when you are low or angry."),
    2: ("Saturn is in the sign after your Moon. The pressure eases, but money and family matters get "
        "reorganised. Be careful with loans and promises; things settle as the phase ends."),
}
_SEV = {
    "gentle": "Saturn is a friendly planet for your rising sign, so this period tends to be firm but fair.",
    "steady": "Saturn's pressure will be felt, but your chart can carry it with steady effort.",
    "pressing": "Saturn is a more demanding planet for your chart, so this period asks for extra care.",
}
CAUTIONS = [
    "Do not make big, irreversible moves such as resigning, lending money or signing guarantees while you are "
    "angry or low.",
    "Keep an emergency fund, and stay away from speculation and borrowing to chase quick gains.",
    "Protect your sleep and routine, and keep your regular health check-ups.",
    "Be honest and keep your promises; Saturn rewards the long, straight road and tests shortcuts.",
    "Treat elders, staff and people in service with respect and pay people fairly.",
]
REMEDIES = [
    "Saturdays: read the Hanuman Chalisa, or chant \"Om Sham Shanaishcharaya Namah\" (11 or 108 times).",
    "Saturday evening: light a sesame-oil lamp near a peepal tree or at a Shani temple.",
    "Saturdays: give black sesame, urad dal, mustard oil, a blanket or footwear to someone in need.",
    "Feed crows or street dogs regularly.",
    "Mondays: offer water to Shiva and chant \"Om Namah Shivaya\" to steady the Moon; keep a calm routine and "
    "stay close to your mother.",
    "The real remedy is service: help elders and working people, and keep your word.",
]
GEM_CAUTION = ("Do not buy a blue sapphire (Neelam) only because of Sade Sati. Worn wrongly it can do harm; "
               "consider it only if a qualified astrologer tests it on your own chart.")
NOTE = "These are traditional practices. They give discipline and calm; they are not a guarantee."


def _month_year(d: date) -> str:
    return f"{_MONTHS[d.month - 1]} {d.year}"


def _segments(moon_idx: int, today: date) -> list[dict]:
    from astro_precompute import SIGNS
    from vedic_ashtakavarga_report import transit_ingresses
    start, end = today - timedelta(days=365 * 9), today + timedelta(days=365 * 32)
    ings = transit_ingresses("Saturn", start, end)
    out: list[dict] = []
    for i, (d, sign_idx) in enumerate(ings):
        nxt = ings[i + 1][0] if i + 1 < len(ings) else end
        out.append({"start": d, "end": nxt, "house": (sign_idx - moon_idx) % 12 + 1,
                    "sign": SIGNS[sign_idx]})
    return out


def _cycles(segs: list[dict]) -> list[list[dict]]:
    """Group the Saturn stretches over the Moon's three signs into cycles. A retrograde loop can carry Saturn
    out of the zone for a year or so and back in, so stretches less than four years apart are one cycle
    (real cycles are about thirty years apart)."""
    cycles: list[list[dict]] = []
    for s in segs:
        if s["house"] not in (12, 1, 2):
            continue
        if cycles and (s["start"] - cycles[-1][-1]["end"]).days <= 365 * 4:
            cycles[-1].append(s)
        else:
            cycles.append([s])
    return cycles


def _severity(pc: dict, moon_idx: int) -> str:
    from astro_precompute import SIGNS
    planets = pc.get("planets") or {}
    moon = planets.get("Moon") or {}
    lagna_idx = (moon_idx - (int(moon.get("house") or 1) - 1)) % 12
    sat_sign = (planets.get("Saturn") or {}).get("sign", "")
    if lagna_idx in (1, 6, 9, 10):                    # Taurus, Libra, Capricorn, Aquarius
        return "gentle"
    if lagna_idx in (3, 4) or sat_sign == "Aries" or moon.get("sign") == "Scorpio":
        return "pressing"
    return "steady"


def build(pc: dict, today: Optional[date] = None) -> Optional[dict[str, Any]]:
    today = today or date.today()
    try:
        from astro_precompute import SIGNS
        moon_sign = ((pc.get("planets") or {}).get("Moon") or {}).get("sign")
        if not moon_sign:
            return None
        moon_idx = SIGNS.index(moon_sign)
        segs = _segments(moon_idx, today)
        if not segs:
            return None
    except Exception as exc:                                              # noqa: BLE001
        print(f"[sade_sati] unavailable: {type(exc).__name__}: {exc}", flush=True)
        return None

    now_seg = next((s for s in segs if s["start"] <= today < s["end"]), None)
    cycles = _cycles(segs)
    cur = next((c for c in cycles if c[0]["start"] <= today < c[-1]["end"]), None)
    nxt = next((c for c in cycles if c[0]["start"] > today), None)
    cycle = cur or nxt
    if not cycle:
        return None

    phases: list[dict] = []
    for house in (12, 1, 2):
        parts = [s for s in cycle if s["house"] == house]
        if parts:
            # Saturn's retrograde loops can bring it back into a phase later; the phase is dated by its first
            # unbroken stretch and the return is shown separately, so the windows never overlap.
            phases.append({"house": house, "name": _PHASE[house], "start": parts[0]["start"],
                           "end": parts[0]["end"],
                           "back": ({"start": parts[1]["start"], "end": parts[-1]["end"]}
                                    if len(parts) > 1 else None)})
    minor = None
    if now_seg and now_seg["house"] in (4, 8):
        minor = {"house": now_seg["house"],
                 "name": "Ashtama Shani" if now_seg["house"] == 8 else "Dhaiya",
                 "start": now_seg["start"], "end": now_seg["end"]}
    return {
        "status": "in" if cur else "next",
        "phase": now_seg["house"] if (cur and now_seg and now_seg["house"] in (12, 1, 2)) else None,
        "phases": phases,
        "cycle_start": cycle[0]["start"], "cycle_end": cycle[-1]["end"],
        "severity": _severity(pc, moon_idx), "minor": minor, "moon_sign": moon_sign,
        "years_to_start": round((cycle[0]["start"] - today).days / 365.25, 1) if not cur else 0,
        "relevant": bool(cur or minor or (cycle[0]["start"] - today).days <= 365 * 3),
    }


def window_dates(blk: Optional[dict]) -> list[dict]:
    """Every date the paid block prints, in the shape the report's date guard takes."""
    if not blk:
        return []
    out = [{"start": blk["cycle_start"], "end": blk["cycle_end"]}]
    for p in blk["phases"]:
        out.append({"start": p["start"], "end": p["end"]})
        if p.get("back"):
            out.append(p["back"])
    if blk.get("minor"):
        out.append({"start": blk["minor"]["start"], "end": blk["minor"]["end"]})
    return out


def facts(blk: Optional[dict]) -> str:
    """One plain sentence for the question readings (no dates)."""
    if not blk:
        return ""
    if blk["status"] == "in" and blk.get("phase"):
        return f"Saturn is in the {_PHASE[blk['phase']].lower()} of Sade Sati over your Moon."
    return ""


# ------------------------------------------------------------------ page
def _e(x: Any) -> str:
    return html.escape(str(x or "").strip())


def _head(text: str, color: str = "#7a4b18") -> str:
    return (f'<div style="font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;font-weight:800;'
            f'color:{color};margin:12px 0 6px;">{_e(text)}</div>')


def _list(items: list[str]) -> str:
    return ('<ul style="margin:0;padding-left:18px;font-size:.92rem;line-height:1.55;color:#2c3140;">'
            + "".join(f'<li style="margin-bottom:6px;">{_e(i)}</li>' for i in items) + "</ul>")


def _p(text: str, extra: str = "") -> str:
    return (f'<p style="font-size:.95rem;line-height:1.6;color:#2c3140;margin:0 0 6px;{extra}">{_e(text)}</p>')


def render(blk: Optional[dict], *, paid: bool, price: int = 298) -> str:
    if not blk:
        return ""
    in_it = blk["status"] == "in"
    color = {"in": "#8a4a1f", "next": "#4a5a7a"}[blk["status"]]
    bg = {"in": "#fbeee4", "next": "#eaeef6"}[blk["status"]]
    pill = (f'Running now · {_PHASE[blk["phase"]]}' if in_it and blk.get("phase") else
            "Running now" if in_it else "Not running now")
    if in_it and blk.get("phase"):
        head = f"You are in the {_PHASE[blk['phase']].lower()} of Sade Sati."
    elif in_it:
        head = "Sade Sati is on a short pause."
    else:
        yrs = blk["years_to_start"]
        head = ("Sade Sati is not running now." if yrs >= 1 else
                "Sade Sati is not running now, but it begins soon.")
    out = ['<section class="card sade-sati" style="background:#fff;border:1px solid #e8e4dc;'
           f'border-left:4px solid {color};border-radius:12px;padding:18px 22px;margin:18px 0;'
           'box-shadow:0 2px 8px rgba(0,0,0,.03);">',
           '<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin-bottom:6px;">'
           '<span style="font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;font-weight:700;'
           'color:#6a7080;">Sade Sati · Saturn and your Moon</span>'
           f'<span class="pill" style="font-size:.68rem;font-weight:700;padding:3px 10px;border-radius:99px;'
           f'background:{bg};color:{color};">{_e(pill)}</span></div>',
           f'<h3 style="font-family:Georgia,serif;font-size:1.15rem;margin:4px 0 8px;color:#1f2430;'
           f'font-weight:600;line-height:1.35;">{_e(head)}</h3>']
    if in_it:
        if blk.get("phase"):
            out.append(_p(_PHASE_TEXT[blk["phase"]]))
        else:
            out.append(_p("Saturn has stepped back out of the zone for its retrograde turn and returns to it later "
                          "in this cycle."))
        out.append(_p(_SEV[blk["severity"]]))
        out.append(_p("Sade Sati is a period of discipline, not doom. Many people build their firmest "
                      "foundations during it."))
    else:
        out.append(_p("Sade Sati happens when Saturn crosses the sign before your Moon, your Moon's own sign "
                      "and the sign after it, about once in thirty years."))
        if blk.get("relevant"):
            out.append(_p(_SEV[blk["severity"]]))
        else:
            out.append(_p(f"Your next one is about {round(blk['years_to_start'])} years away, so there is nothing "
                          "to do about it now."))
    if blk.get("minor"):
        m = blk["minor"]
        out.append(_p(f"Saturn is also in the {m['house']}th house from your Moon ({m['name']}), a smaller "
                      "Saturn stretch that asks for extra care with health, money and travel."))

    if paid:
        out.append(_head("When it begins and ends" if blk.get("relevant") else "When it comes"))
        rows = [f"Whole period: {_month_year(blk['cycle_start'])} to {_month_year(blk['cycle_end'])}."]
        for p in blk["phases"]:
            row = f"{p['name']}: {_month_year(p['start'])} to {_month_year(p['end'])}."
            if p.get("back"):
                row += (f" Saturn's retrograde turn brings it back into this phase from "
                        f"{_month_year(p['back']['start'])} to {_month_year(p['back']['end'])}.")
            rows.append(row)
        if blk.get("minor"):
            m = blk["minor"]
            rows.append(f"{m['name']}: {_month_year(m['start'])} to {_month_year(m['end'])}.")
        out.append(_list(rows))
        if in_it:
            peak = next((p for p in blk["phases"] if p["house"] == 1), None)
            if peak:
                out += [_head("The hardest stretch", "#a3341f"),
                        _p(f"The peak phase, {_month_year(peak['start'])} to {_month_year(peak['end'])}, "
                           "is when the pressure is usually felt most.")]
        if blk.get("relevant"):
            out += [_head("Cautions for this time", "#a3341f"), _list(CAUTIONS),
                    _head("Remedies", "#1c6b45"), _list(REMEDIES),
                    _p(GEM_CAUTION, "margin-top:8px;"),
                    _p(NOTE, "font-size:.82rem;color:#5a6070;")]
    elif blk.get("relevant"):
        out += [_head("What to keep in mind", "#a3341f"), _list(CAUTIONS[:2])]
        out.append(
            '<div class="lock-wrap" data-unlock="1" role="button" tabindex="0" '
            'style="margin:14px 0 4px;border-radius:12px;cursor:pointer;">'
            '<div class="lock-blur" style="padding:14px 18px;font-size:.88rem;line-height:1.55;">'
            '<b>When it begins and ends:</b> each phase is dated here. <b>Remedies:</b> the prayers, offerings and '
            'habits that suit this period are listed here, with what to avoid.</div>'
            '<div class="lock-over" data-unlock="1"><span class="lock-chip" data-unlock="1" '
            'style="font-size:.72rem;padding:7px 18px;cursor:pointer;">&#128274; See the dates and the remedies'
            '</span></div></div>'
            '<p style="font-size:.84rem;line-height:1.5;color:#4a5160;margin:8px 0 0;">&#129680; The start and end '
            'of each phase, the hardest stretch, five cautions and the remedies are in the full reading.</p>')
    out.append("</section>")
    return "\n".join(out)
