"""The daily reading, as something you can act on before breakfast.

Co-Star built a habit out of one line plus a do/don't list — short enough to
read on a lock screen, specific enough to quote to a friend. That is the
engagement mechanic, and it is why people open the app daily. But a one-liner
is also the easiest thing in the world to dismiss as a horoscope column.

What the Indian market pays for, and what Co-Star does not have, is **timing**
and **working**. `compute_daily_moon_guide` already produces both: a six-to-nine
lane confluence, the running Vimshottari stack down to pratyantar, Ashtakavarga
bindus on the signs today's planets are crossing, gochar flags, the Jaimini
clock, and real Rahu Kaal / choghadiya / Abhijit windows from PyJHora. The old
card read five keys out of twenty-five and threw the rest away, which is how a
multi-lane engine ended up looking like a Moon-sign column.

So this renders the same reading twice, branching on `paid`:

    free, every morning, forever
        the verdict, the Moon proof block, lucky number and colour,
        one Do and one Don't

    paid, on subscription
        more direct do/don't guidance, the few timing windows worth using,
        and one compact Moon-transit/dasha basis line

The hora helpers below (`sunrise_local`, `horas`, `pick_windows`) stay because
they are the only dependency-free timing fallback in the codebase, used when
PyJHora cannot produce a panchang for the birth place.
"""

from __future__ import annotations

import html as _html
import math
from datetime import date, datetime, time, timedelta
from typing import Any, Iterable, List, Optional

# Chaldean order — the fixed sequence planetary hours run in.
CHALDEAN = ("Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon")
#: the planet that rules the first hora after sunrise, by weekday
DAY_LORD = {0: "Moon", 1: "Mars", 2: "Mercury", 3: "Jupiter",
            4: "Venus", 5: "Saturn", 6: "Sun"}      # Monday = 0

# Don't-column items are noun phrases under a "Don't" label — keep them short
# and grammatical as stand-alone avoid-lines (not "Don't cutting…").
HORA_USE = {
    "Sun": ("dealing with authority, applications, anything official",
            "Asking favours from people who owe you nothing"),
    "Moon": ("family, home matters, anything that needs someone to feel safe",
             "Signing anything binding"),
    "Mars": ("hard physical work, pushing a stalled task, exercise",
             "Arguments, negotiations, firing off that message"),
    "Mercury": ("email, paperwork, negotiation, numbers, study",
                "Emotional conversations"),
    "Jupiter": ("money talk, advice, teachers, anything you want blessed",
                "Cutting corners"),
    "Venus": ("relationships, buying, design, asking nicely",
              "Confrontation"),
    "Saturn": ("finishing the boring, unglamorous, necessary thing",
               "Starting something brand new"),
}

TONE_LINE = {
    ("auspicious", "auspicious"): "Today is genuinely on your side. Use it for the thing you have been putting off.",
    ("auspicious", "caution"): "The day supports your work but not your patience. Push the task, not the person.",
    ("caution", "auspicious"): "Slow start, better finish. Do not judge today before the afternoon.",
    ("caution", "caution"): "A day to protect rather than push. Nothing here needs deciding today.",
    ("neutral", "auspicious"): "Quietly favourable. Small moves land better than big ones.",
    ("auspicious", "neutral"): "Effort converts today. Keep the scope narrow and finish something.",
}
DEFAULT_LINE = "A workable, unremarkable day. Spend it on the boring thing that keeps paying."

HOUSE_FROM_MOON_NOTE = {
    1: "You are the subject today whether you want to be or not.",
    2: "Money and family talk both surface today.",
    3: "Good day to ask, pitch or travel short distances.",
    4: "Home pulls at your attention.",
    5: "Children, creativity and risk all light up.",
    6: "Work and health compete for the same energy.",
    7: "Other people set today's terms, not you.",
    8: "Something under the surface moves. Do not force it.",
    9: "Luck runs slightly warmer than usual.",
    10: "You are visible today. Behave accordingly.",
    11: "Gains come through people, not effort.",
    12: "A day that rewards rest and costs you if you ignore that.",
}

#: engine tone -> (pill class, badge text). `_score_tone` emits exactly these.
TONE_PILL = {
    "bright": ("up", "Bright"),
    "mixed-positive": ("up", "Leaning good"),
    "steady": ("faint", "Steady"),
    "mixed-caution": ("mixed", "Mixed — pace it"),
    "sensitive": ("down", "Sensitive"),
}

#: lane weight -> pill class, the same mapping palm uses for signal strength.
WEIGHT_PILL = {"high": "up", "medium": "mixed"}


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def _first(name: str) -> str:
    n = (name or "").strip().split()
    return n[0] if n else "friend"


def _suffix(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _txt(item: Any) -> str:
    """dos/donts arrive as {"text","source"} dicts; older callers pass strings."""
    if isinstance(item, dict):
        return str(item.get("text") or "")
    return str(item or "")


def _src(item: Any) -> str:
    return str(item.get("source") or "") if isinstance(item, dict) else ""


def _nice_date(value: Any) -> str:
    """ISO dates read as machine output in a sentence about your life."""
    s = str(value or "")[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%d %b %Y")
    except ValueError:
        return s


# ---------------------------------------------------------------------------
# hora fallback — kept for places PyJHora cannot build a panchang for
# ---------------------------------------------------------------------------
def sunrise_local(day: date, lat: float, lon: float, tz: float) -> datetime:
    """Rough local sunrise. Minutes-accurate is plenty for hora guidance."""
    n = day.timetuple().tm_yday
    decl = 23.44 * math.sin(math.radians(360 / 365 * (n - 81)))
    try:
        cos_h = -math.tan(math.radians(lat)) * math.tan(math.radians(decl))
        cos_h = max(-1.0, min(1.0, cos_h))
        hour_angle = math.degrees(math.acos(cos_h))
    except ValueError:                                   # polar edge cases
        hour_angle = 90.0
    # solar noon in local clock time, then step back half the day length
    noon = 12 - (lon / 15.0 - tz)
    rise = noon - hour_angle / 15.0
    rise = max(0.0, min(23.99, rise))
    h = int(rise)
    m = int(round((rise - h) * 60))
    if m == 60:
        h, m = h + 1, 0
    return datetime.combine(day, time(h % 24, m))


def horas(day: date, lat: float, lon: float, tz: float) -> list:
    """The 12 daylight planetary hours, with their real clock times."""
    rise = sunrise_local(day, lat, lon, tz)
    next_rise = sunrise_local(day + timedelta(days=1), lat, lon, tz)
    span = (next_rise - rise).total_seconds()
    if span <= 0:
        span = 24 * 3600
    # Daylight horas are the classical equal-hour division of sunrise→sunset;
    # using a 12-hour daylight approximation keeps this dependency-free.
    step = span / 24.0
    start_lord = DAY_LORD.get(day.weekday(), "Sun")
    idx = CHALDEAN.index(start_lord)
    out = []
    for i in range(12):
        lord = CHALDEAN[(idx + i) % 7]
        a = rise + timedelta(seconds=step * i)
        b = rise + timedelta(seconds=step * (i + 1))
        out.append({"lord": lord, "start": a, "end": b})
    return out


def pick_windows(day: date, lat: float, lon: float, tz: float,
                 *, wanted: tuple = ("Jupiter", "Mercury", "Venus"),
                 avoid: tuple = ("Mars", "Saturn"), limit: int = 3) -> list:
    """The two or three hours worth naming, inside waking hours."""
    rows = []
    for h in horas(day, lat, lon, tz):
        if not (6 <= h["start"].hour <= 21):
            continue
        good = h["lord"] in wanted
        bad = h["lord"] in avoid
        if not (good or bad):
            continue
        use, dont = HORA_USE.get(h["lord"], ("", ""))
        rows.append({
            "when": f"{h['start']:%H:%M}–{h['end']:%H:%M}",
            "lord": h["lord"], "good": good,
            "text": (f"Best window for {use}" if good
                     else f"Avoid {dont} in this hour"),
        })
    rows.sort(key=lambda r: (not r["good"], r["when"]))
    return rows[:limit]


# ---------------------------------------------------------------------------
# free blocks
# ---------------------------------------------------------------------------
def _hero(reading: dict, day: date, n_lanes: int) -> str:
    """The verdict. Lead with the prediction and Moonology emotional climate."""
    vc = reading.get("vedic_confluence") or {}
    verdict = (vc.get("verdict_plain") or vc.get("verdict")
               or reading.get("opening") or DEFAULT_LINE)
    tone = str(reading.get("tone") or "steady")
    pill_cls, pill_txt = TONE_PILL.get(tone, ("faint", tone.title()))

    moon = reading.get("moon_transit") or {}
    h_moon = moon.get("house_from_moon")
    h_lagna = moon.get("house_from_lagna")
    sign = moon.get("sign") or ""
    
    # Moonology emotional vibe
    moonology = reading.get("moonology") or {}
    phase = moonology.get("phase") or moonology.get("phase_astronomical") or "Waxing"
    
    try:
        from moonology_daily_narrative import SIGN_DAY_FEEL, PHASE_DAY_FEEL, HOUSE_DAY_FEEL
        sign_feel = SIGN_DAY_FEEL.get(sign, "")
        phase_feel = PHASE_DAY_FEEL.get(phase, "")
        house_feel = HOUSE_DAY_FEEL.get(h_lagna if isinstance(h_lagna, int) else (h_moon if isinstance(h_moon, int) else 1), "")
    except Exception:  # noqa: BLE001
        sign_feel, phase_feel, house_feel = "", "", ""

    climate_parts = []
    if sign_feel:
        climate_parts.append(f"With Moon in {sign}, {sign_feel}.")
    if phase_feel and phase:
        climate_parts.append(f"Under the {phase}, {phase_feel}.")
    climate_text = " ".join(climate_parts)

    from ashtakavarga_analysis import HOUSE_LIFE_THEME
    theme = HOUSE_LIFE_THEME.get(h_lagna if isinstance(h_lagna, int) else h_moon, "daily priorities and personal focus")
    house_note = HOUSE_FROM_MOON_NOTE.get(h_moon, "")

    focus_line = f"House {h_lagna or h_moon or 1} activated ({theme}) — {house_note}" if (theme or house_note) else ""

    return f"""
<section class="daily">
  <div class="lbl">Today · {day:%A %d %B}</div>
  <span class="pill {pill_cls}">{_e(pill_txt)}</span>
  <h3 style="margin:10px 0 8px 0;">{_e(verdict)}</h3>
  {f'<p class="moon-feel" style="margin:6px 0;font-size:0.92rem;color:#374151;line-height:1.45;"><strong>Today’s emotional climate:</strong> {_e(climate_text)}</p>' if climate_text else ''}
  {f'<p style="font-size:0.86rem;margin:4px 0 0 0;color:#6b7280;"><strong>Personal focus:</strong> {_e(focus_line)}</p>' if focus_line else ''}
</section>"""


def _moon_proof(reading: dict, first: str) -> str:
    """One compact technical basis line tying today to your birth chart."""
    moon = reading.get("moon_transit") or {}
    natal = reading.get("natal_moon") or {}
    tara = reading.get("tarabala") or {}
    chandra = reading.get("chandrabal") or {}
    bits = []
    if moon.get("sign"):
        nak = f" ({moon.get('nakshatra')})" if moon.get('nakshatra') else ""
        bits.append(f"Moon in {_e(moon.get('sign'))}{nak}")
    if moon.get("house_from_lagna"):
        h_l = moon["house_from_lagna"]
        bits.append(f"{h_l}{_suffix(h_l)} from Ascendant")
    if moon.get("house_from_moon"):
        h = moon["house_from_moon"]
        bits.append(f"{h}{_suffix(h)} from birth Moon")
    if tara.get("name"):
        bits.append(f"{_e(tara.get('name'))} Tarabala")
    if chandra.get("name"):
        bits.append(f"{_e(chandra.get('name'))} Chandrabala")
    if not bits:
        return ""
    return f"""
<div class="proof">
  <p class="pred-scenario"><b>{_e(first)}:</b> today is calculated specifically for your birth chart, not generic sun signs.</p>
  <p class="pred-why"><b>Astrological basis:</b> {" · ".join(bits)}</p>
</div>"""


def _lucky(reading: dict, *, paid: bool) -> str:
    """Small, changes daily, and the reason to open the page every morning."""
    nums = reading.get("lucky_numbers") or {}
    cols = reading.get("lucky_colors") or []
    if not nums and not cols:
        return ""

    primary = nums.get("primary")
    others = [n for n in (nums.get("secondary"), nums.get("tertiary"))
              if n is not None and n != primary]
    num_block = ""
    if primary is not None:
        extra = (f'<div class="num-src">Also running for you today: '
                 f'{_e(", ".join(str(n) for n in others))}</div>' if others else "")
        num_block = f"""
  <div class="num-card">
    <div class="num-big">{_e(primary)}</div>
    <div>
      <div class="num-label">Your number today</div>
      <div>Use it for anything you get to choose — a seat, a time, an amount.</div>
      {extra}
    </div>
  </div>"""

    col_rows = "".join(
        f'<li><b>{_e(c.get("name"))}</b></li>'
        for c in cols[:2] if c.get("name"))
    col_block = (f'<div class="ev-label" style="margin-top:14px">Your colours today</div>'
                 f'<ul class="palm-list">{col_rows}</ul>') if col_rows else ""

    return f"""
<h3 class="sec">Your number and colour for today</h3>
<div class="card">{num_block}{col_block}</div>"""


def _dodont(reading: dict, *, paid: bool) -> str:
    dos = list(reading.get("dos") or [])
    donts = list(reading.get("donts") or [])
    if not dos and not donts:
        return ""

    if paid:
        do_rows = "".join(
            f'<div>{_e(_txt(x))}</div>' for x in dos[:3])
        dont_rows = "".join(
            f'<div>{_e(_txt(x))}</div>' for x in donts[:3])
        note = ""
        more = ""
    else:
        do_rows = "".join(f"<div>{_e(_txt(x))}</div>" for x in dos[:1])
        dont_rows = "".join(f"<div>{_e(_txt(x))}</div>" for x in donts[:1])
        note = ""
        rest = max(0, len(dos) - 1) + max(0, len(donts) - 1)
        more = (f'<div class="when locked-inline"><span class="lockicon">&bull;</span> '
                f'{rest} more, each written off a different lane of your chart '
                f'and carrying the rule it came from.</div>' if rest else "")

    return f"""
<h3 class="sec">What to do with today</h3>
{note}
<div class="dodont">
  <div class="do"><div class="t">Do</div>{do_rows}</div>
  <div class="dont"><div class="t">Don't</div>{dont_rows}</div>
</div>
{more}"""


# ---------------------------------------------------------------------------
# paid blocks
# ---------------------------------------------------------------------------
def _personal_moon_focus(reading: dict) -> str:
    """The subscription-grade daily card: Moon -> houses -> AV -> significator.

    This is deliberately a factual bridge, not a new prediction engine. It
    exposes the already-computed Moon transit, SAV/BAV and house-lord context
    in one human-readable block so the daily reading is visibly personal.
    """
    moon = reading.get("moon_transit") or {}
    av = reading.get("ashtakavarga") or {}
    mav = av.get("moon") or {}
    if not moon.get("sign"):
        return ""

    sign = moon.get("sign")
    h_lagna = moon.get("house_from_lagna")
    h_moon = moon.get("house_from_moon")
    sav = mav.get("sav")
    bav = mav.get("bav")
    try:
        sav_i = int(sav) if sav is not None else None
    except (TypeError, ValueError):
        sav_i = None
    try:
        bav_i = int(bav) if bav is not None else None
    except (TypeError, ValueError):
        bav_i = None

    from astro_precompute import SIGN_LORDS, SIGNS
    from ashtakavarga_analysis import HOUSE_LIFE_THEME

    theme = HOUSE_LIFE_THEME.get(h_lagna, "the life area activated today")
    lord = ""
    lord_sign = ""
    lord_house = ""
    lord_dignity = ""
    if isinstance(h_lagna, int) and 1 <= h_lagna <= 12 and sign:
        try:
            lagna_sign = str(reading.get("lagna") or "")
            if lagna_sign and lagna_sign in SIGNS:
                house_sign = SIGNS[(SIGNS.index(lagna_sign) + h_lagna - 1) % 12]
                lord = SIGN_LORDS.get(house_sign, "")
                natal_planet = (reading.get("natal_planets") or {}).get(lord) or {}
                lord_sign = str(natal_planet.get("sign") or "")
                lord_house = str(natal_planet.get("house") or "")
                lord_dignity = str(natal_planet.get("dignity") or "")
        except Exception:
            pass

    if sav_i is None:
        support = "Structural support could not be scored today."
    elif sav_i < 25:
        support = "Lower structural support today — treat this area as a watchpoint rather than forcing an outcome."
    elif sav_i >= 32:
        support = "Strong structural support today — a small, visible move in this area is easier to carry through."
    else:
        support = "Moderate structural support today — steady effort is more useful than forcing a result."

    if bav_i is not None:
        if bav_i <= 3:
            moon_signal = f"Moon BAV is {bav_i}/8, so emotional momentum may need more patience."
        elif bav_i >= 5:
            moon_signal = f"Moon BAV is {bav_i}/8, giving the Moon a stronger-than-usual channel today."
        else:
            moon_signal = f"Moon BAV is {bav_i}/8, giving a mixed but workable signal."
    else:
        moon_signal = ""

    lord_line = ""
    if lord:
        context = []
        if lord_sign:
            context.append(f"natal {lord} in {lord_sign}")
        if lord_house:
            context.append(f"{lord_house}{_suffix(lord_house)} house")
        if lord_dignity:
            context.append(lord_dignity)
        detail = " · ".join(context)
        lord_line = (
            f'<div class="evidence" style="margin-top:12px">'
            f'<span class="ev-label">The significator behind this house</span>'
            f'<p><strong>{_e(lord)}</strong> governs this area'
            f'{f" ({_e(detail)})" if detail else ""}.</p>'
            f'<p class="fine">The house signal is refined by the natal condition of its lord; '
            f'this is why the same Moon transit can feel different for different people.</p>'
            f'</div>'
        )

    score_line = " · ".join(
        x for x in (
            f"SAV {sav_i}/56" if sav_i is not None else "",
            f"Moon BAV {bav_i}/8" if bav_i is not None else "",
        ) if x
    )
    from_lagna = f"{h_lagna}{_suffix(h_lagna)} from Ascendant" if isinstance(h_lagna, int) else ""
    from_moon = f"{h_moon}{_suffix(h_moon)} from natal Moon" if isinstance(h_moon, int) else ""

    return f"""
<h3 class="sec">Your most personal Moon transit today</h3>
<p class="sec-note">This is the part generic Moonology cannot see: today's Moon is
being read against your own houses and Ashtakavarga, then refined by the natal
lord of the activated house.</p>
<div class="card" style="border-left:4px solid #7e57c2">
  <p class="claim"><strong>Moon in {_e(sign)}</strong>
    {f"· {_e(moon.get('nakshatra'))}" if moon.get('nakshatra') else ""}</p>
  <p class="fine">{_e(" · ".join(x for x in (from_lagna, from_moon) if x))}</p>
  <p><strong>Life area:</strong> {_e(theme)}</p>
  {f'<p class="when"><strong>{_e(score_line)}</strong></p>' if score_line else ''}
  <p>{_e(support)}</p>
  {f'<p>{_e(moon_signal)}</p>' if moon_signal else ''}
  {lord_line}
</div>"""


def _lanes(lanes: List[dict]) -> str:
    """The answer to "why does today read this way"."""
    if not lanes:
        return ""
    rows = ""
    for ln in lanes:
        if not ln.get("signal"):
            continue
        cls = WEIGHT_PILL.get(str(ln.get("weight")), "faint")
        rows += (f'<li><span>{_e(ln.get("lane"))}</span>'
                 f'<span>{_e(ln.get("signal"))}</span>'
                 f'<span class="pill {cls}">{_e(ln.get("weight"))}</span></li>')
    if not rows:
        return ""
    return f"""
<h3 class="sec">Every lane that voted on today</h3>
<p class="sec-note">Each of these was computed separately from your chart. The
verdict at the top is where they agree; a day where they disagree is a day to
move carefully, and you can now see which is which.</p>
<div class="card"><ul class="lanes">{rows}</ul></div>"""


def _dasha(reading: dict) -> str:
    """The running Vimshottari stack with real dates."""
    d = reading.get("dasha") or {}
    vc = reading.get("vedic_confluence") or {}
    vim = vc.get("dasha") or {}
    if not d.get("md"):
        return ""

    rows = []
    for label, lord, start, end, note in (
        ("Mahadasha", d.get("md"), vim.get("md_start"), vim.get("md_end"), vc.get("md_note")),
        ("Antardasha", d.get("ad"), vim.get("ad_start"), vim.get("ad_end"), vc.get("ad_note")),
        ("Pratyantardasha", d.get("pd"), d.get("pd_start") or vim.get("pd_start"),
         d.get("pd_end") or vim.get("pd_end"), vc.get("pd_note")),
    ):
        if not lord:
            continue
        span = (f"{_nice_date(start)} — {_nice_date(end)}"
                if start and end else "")
        impact = note
        if not impact:
            try:
                import impact as IMP
                end_p = _nice_date(end) if end else ""
                impact = IMP.dasha_impact(lord, end_pretty=end_p).rstrip(".")
            except Exception:  # noqa: BLE001
                impact = ""
        rows.append(
            f'<li><b>{_e(label)}: {_e(lord)}</b>'
            + (f'<span class="pt-when">{_e(span)}</span>' if span else "")
            + (f"<p>{_e(impact)}</p>" if impact else "") + "</li>")

    karmic = vc.get("karmic_dasha")
    karmic_line = ('<p class="fine">This is a karmic pairing — the two lords are '
                   'natural enemies, so the period asks for more patience than '
                   'its dates alone suggest.</p>' if karmic else "")
    note = d.get("note") or ""
    return f"""
<h3 class="sec">The clock you are actually running on</h3>
<p class="sec-note">Vimshottari, from the exact position of the Moon at your
birth. Today sits inside all three of these at once, which is why two people
with the same Moon sign can have completely different weeks.</p>
<div class="card">
  <ul class="palm-points">{''.join(rows)}</ul>
  {f'<p class="fine">{_e(note)}</p>' if note else ''}
  {karmic_line}
</div>"""


def _ashtakavarga(reading: dict) -> str:
    """Bindus on the signs today's planets are crossing — including the lords
    of the running dasha, which is the number that ties the clock to the sky."""
    av = reading.get("ashtakavarga") or {}
    if not av:
        return ""
    moon = av.get("moon") or {}

    lord_rows = ""
    for row in (av.get("dasha_lords") or []):
        span = (f'{row.get("sign")} ({("well supported" if (row.get("bav") or 0) >= 5 else "weakly supported")})'
                if row.get("bav") is not None
                else f'{row.get("sign")}, house total {row.get("sav")}')
        lord_rows += (
            f'<li><b>{_e(row.get("role"))} lord {_e(row.get("planet"))}</b>'
            f'<span class="pt-when">{_e(span)}</span>'
            f'<p>{_e(row.get("meaning"))}</p></li>')

    general = ""
    for key, label in (("sun", "Sun"), ("mercury", "Mercury")):
        row = av.get(key) or {}
        if row.get("bav") is None:
            continue
        general += (f'<li>{_e(label)}: '
                    f'{"well supported" if (row.get("bav") or 0) >= 5 else "weakly supported"} '
                    f'in {_e(row.get("sign"))}</li>')

    lords_block = ""
    if lord_rows:
        lords_block = f"""
  <div class="ev-label" style="margin-top:14px">Your dasha lords, where they are today</div>
  <p class="fine">This is the number that matters most: how well supported the
  planet actually running your life is in the sign it is currently crossing. A
  dasha lord in a thin sign is where the remedy below is aimed.</p>
  <ul class="palm-points">{lord_rows}</ul>"""

    return f"""
<h3 class="sec">How well today's sky is supported on your chart</h3>
<p class="sec-note">Each sign in your chart was scored at birth. A planet crossing
a well-scored sign delivers; the same planet on a thin sign has to work for it.</p>
<div class="card">
  {f'<p class="claim">{_e(moon.get("sav_line"))}</p>' if moon.get("sav_line") else ''}
  {f'<p>{_e(moon.get("bav_line"))}</p>' if moon.get("bav_line") else ''}
  {f'<div class="evidence"><span class="ev-label">The other fast movers</span><ul>{general}</ul></div>' if general else ''}
  {lords_block}
</div>"""


def _houses(reading: dict) -> str:
    """Which parts of your life today's sky is actually pointing at."""
    from ashtakavarga_analysis import HOUSE_LIFE_THEME

    seen: set = set()
    rows = ""

    def add(house: Any, who: str) -> None:
        nonlocal rows
        try:
            h = int(house)
        except (TypeError, ValueError):
            return
        if h in seen or h not in HOUSE_LIFE_THEME:
            return
        seen.add(h)
        rows += (f'<li><b>{h}{_suffix(h)} house — {who}</b>'
                 f'<p>{_e(HOUSE_LIFE_THEME[h])}</p></li>')

    moon = reading.get("moon_transit") or {}
    add(moon.get("house_from_lagna"), "transit Moon")
    for row in (reading.get("ashtakavarga") or {}).get("dasha_lords") or []:
        add(row.get("house_from_lagna"),
            f'{row.get("role", "").lower()} lord {row.get("planet", "")}'.strip())
    sun = reading.get("sun_transit") or {}
    add(sun.get("house_from_lagna"), "transit Sun")

    if not rows:
        return ""
    return f"""
<h3 class="sec">The houses that are lit today</h3>
<p class="sec-note">Counted from your rising sign. These are the departments of
your life the day is pointing at — everything else is background.</p>
<div class="card"><ul class="palm-points">{rows}</ul></div>"""


def _remedy(pc: Optional[dict], reading: dict) -> str:
    """Keyed to the running dasha lords, with the safety gates intact.

    `build_remedy_report` is used rather than a flat planet-to-gem table because
    it already refuses to recommend a stone for a debilitated or dusthana-placed
    lord — the case where a naive table does actual harm.
    """
    if not pc:
        return ""
    try:
        from gemstone_remedy import build_remedy_report
        rep = build_remedy_report(pc, domain="daily")
    except Exception:
        return ""
    if not rep.get("ok"):
        return ""

    d = reading.get("dasha") or {}
    md, ad = d.get("md", ""), d.get("ad", "")
    # The section promises the lords in charge right now, so a gemstone whose
    # window opens in 2036 does not belong in a reading about today.
    running = {x for x in (md, ad, d.get("pd", "")) if x}

    def mine(items: list) -> list:
        return [i for i in items if i.get("planet") in running] if running else items

    rows = ""
    for item in mine(rep.get("primary_wear") or [])[:2]:
        gem = item.get("gem") or {}
        rows += (
            f'<li><b>{_e(item.get("planet"))} — {_e(gem.get("gem"))}</b>'
            f'<span class="pt-when">{_e(item.get("role"))}</span>'
            f'<p>{_e(gem.get("metal"))}, {_e(gem.get("finger"))}, first worn on a '
            f'{_e(gem.get("day"))}. {_e(item.get("timing_note"))}</p></li>')
    for item in mine(rep.get("mantra_only") or [])[:2]:
        gem = item.get("gem") or {}
        rows += (
            f'<li><b>{_e(item.get("planet"))} — mantra and charity only</b>'
            f'<span class="pt-when">{_e(item.get("role"))}</span>'
            f'<p>{_e(gem.get("mantra"))}. {_e(gem.get("charity"))}. '
            f'{_e((item.get("reasons") or [""])[0])}</p></li>')
    avoid_rows = "".join(
        f'<li>{_e(item.get("planet"))}: {_e((item.get("reasons") or [""])[0])}</li>'
        for item in (rep.get("avoid") or [])[:3])

    if not rows and not avoid_rows:
        return ""
    lords = " and ".join(x for x in (md, ad) if x)
    return f"""
<h3 class="sec">What actually helps, while this period runs</h3>
<p class="sec-note">Keyed to {_e(lords) or 'your running period'} — the lords in
charge right now — and checked against their placement in your chart before
anything is recommended.</p>
<div class="card">
  <ul class="palm-points">{rows}</ul>
  {f'<div class="evidence"><span class="ev-label">Do not wear</span><ul>{avoid_rows}</ul></div>' if avoid_rows else ''}
  <p class="fine">A stone for a badly placed planet amplifies the problem, which
  is why two of these may say mantra only. That is the honest answer, not an
  upsell to something else.</p>
</div>"""


def _clock(value: Any) -> str:
    """PyJHora returns HH:MM:SS; nobody plans a morning to the second."""
    s = str(value or "")
    return s[:5] if len(s) >= 5 and s[2:3] == ":" else s


def _windows_why(reading: dict) -> str:
    """Explain why today's windows were chosen — must survive customer sanitizers."""
    muh = reading.get("muhurat") or {}
    why = str(muh.get("day_summary") or muh.get("explanation") or "").strip()
    if not why:
        bits: list[str] = []
        weekday = reading.get("weekday") or "today"
        lord = reading.get("weekday_lord") or ""
        if lord:
            bits.append(f"{lord} is the weekday lord for {weekday}")
        tara = (reading.get("tarabala") or {}).get("name") or ""
        if tara:
            bits.append(f"{tara} Tarabala sets the day's caution level")
        chandra = (reading.get("chandrabal") or {}).get("name") or ""
        if chandra:
            bits.append(f"{chandra} Chandrabala shapes emotional rhythm")
        bits.append(
            "Labh and Amrit choghadiya are the classical gain and all-purpose "
            "windows; Rahu Kaal is the weekday-fixed slot to avoid new starts"
        )
        why = ". ".join(bits) + "."
    return f'<p class="pred-why"><b>Why:</b> {_e(why)}</p>'


def _windows(reading: dict, day: date, lat: float, lon: float, tz: float) -> str:
    """Only the few time windows a person can realistically use today."""
    muh = reading.get("muhurat") or {}
    win = muh.get("windows") or {}
    rows = ""

    for slot in (win.get("good_choghadiya") or [])[:2]:
        rows += (f'<li class="w-up"><b>{_clock(slot.get("start"))}–{_clock(slot.get("end"))}</b>'
                 f'<span><b>{_e(slot.get("label"))}</b> — {_e(slot.get("plain"))}</span></li>')
    ab = win.get("abhijit") or {}
    if ab.get("start") and not rows:
        rows += (f'<li class="w-up"><b>{_clock(ab.get("start"))}–{_clock(ab.get("end"))}</b>'
                 f'<span><b>Abhijit</b> — {_e(ab.get("plain"))}</span></li>')
    for slot in (win.get("tri_kaal") or [])[:1]:
        rows += (f'<li class="w-down"><b>{_clock(slot.get("start"))}–{_clock(slot.get("end"))}</b>'
                 f'<span><b>{_e(slot.get("label"))}</b> — {_e(slot.get("plain"))}</span></li>')

    if not rows:
        # No panchang for this location — fall back to the hora approximation.
        tara = (reading.get("tarabala") or {}).get("tone", "neutral")
        wanted = ("Jupiter", "Mercury", "Venus")
        avoid = ("Mars", "Saturn", "Rahu")
        if tara == "caution":
            wanted, avoid = ("Jupiter", "Venus"), ("Mars", "Saturn", "Sun")
        for w in pick_windows(day, lat, lon, tz, wanted=wanted, avoid=avoid):
            cls = "w-up" if w["good"] else "w-down"
            rows += (f'<li class="{cls}"><b>{_e(w["when"])}</b>'
                     f'<span>{_e(w["text"])}</span></li>')
    if not rows:
        return ""

    return f"""
<h3 class="sec">Best and avoid times</h3>
<div class="card">
  <ul class="windows">{rows}</ul>
  {_windows_why(reading)}
</div>"""


def _technical_snapshot(reading: dict, n_lanes: int) -> str:
    """A single audit line for readers who want to know why, without a lecture."""
    d = reading.get("dasha") or {}
    moon = reading.get("moon_transit") or {}
    parts = []
    stack = "–".join(x for x in (d.get("md"), d.get("ad"), d.get("pd")) if x)
    if stack:
        parts.append(f"Vimshottari {stack}")
    if moon.get("sign"):
        moon_line = f"transit Moon in {moon.get('sign')}"
        if moon.get("house_from_moon"):
            moon_line += f", {moon.get('house_from_moon')}{_suffix(moon.get('house_from_moon'))} from natal Moon"
        parts.append(moon_line)
    if n_lanes:
        parts.append(f"{n_lanes} independent checks")
    if not parts:
        return ""
    return f"""
<p class="pred-why" style="margin:18px 0"><b>Why:</b> {_e(" · ".join(parts))}.</p>"""


def _extras(reading: dict) -> str:
    """The second clock, the slow planets, and the lunar month — the working
    that belongs under a fold rather than in the main flow."""
    vc = reading.get("vedic_confluence") or {}
    jai = reading.get("jaimini") or {}
    blocks = ""

    if jai.get("stack"):
        notes = "".join(
            f"<li>{_e(x)}</li>" for x in
            (vc.get("jaimini_md_note"), vc.get("jaimini_ad_note"),
             vc.get("jaimini_pd_note")) if x)
        blocks += (f"<h4>The Jaimini clock</h4>"
                   f"<p>A second, sign-based dasha system running in parallel with "
                   f"Vimshottari: <b>{_e(jai.get('stack'))}</b>. Where the two agree, "
                   f"the day is unambiguous.</p>"
                   + (f"<ul>{notes}</ul>" if notes else ""))

    slow = reading.get("slow_planet_notes") or []
    if slow:
        blocks += ("<h4>The slow planets against today's Moon</h4><ul>"
                   + "".join(f"<li>{_e(x)}</li>" for x in slow) + "</ul>")

    for key, label in (("sun_narrative", "The Sun today"),
                       ("mercury_narrative", "Mercury today")):
        if reading.get(key):
            blocks += f"<h4>{label}</h4><p>{_e(reading[key])}</p>"

    moonology = reading.get("moonology") or {}
    if moonology.get("phase"):
        blocks += (f"<h4>The lunar month</h4><p><b>{_e(moonology['phase'])}</b>"
                   + (f" — {_e(moonology.get('phase_summary'))}"
                      if moonology.get("phase_summary") else "") + "</p>"
                   + (f"<p>{_e(moonology.get('sign_summary'))}</p>"
                      if moonology.get("sign_summary") else ""))

    srcs = reading.get("sources") or []
    if srcs:
        blocks += ("<h4>Everything this was built from</h4><ul>"
                   + "".join(f"<li>{_e(s)}</li>" for s in srcs) + "</ul>")

    if not blocks:
        return ""
    return f"""
<details class="workings workings-main">
  <summary>The rest of the working — the second clock, the slow planets, the sources</summary>
  <div class="workings-body">{blocks}</div>
</details>"""


def _locked_preview(*, price: int, n_lanes: int, md: str, ad: str, pd: str) -> str:
    return f"""
<div class="qa-window locked" style="margin:14px 0;">
  <div class="qa-wlabel">Precision Auspicious Hours & Timing Windows</div>
  <p class="blurred">Exact daylight planetary hours (Jupiter, Mercury, Venus horas) for commercial decisions, applications, negotiations, and exact Rahu Kaal window to avoid.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Daily clock windows are locked.</b> Unlock to view exact clock times for today's highest-converting windows.</p>
</div>

<div class="qa-window locked" style="margin:14px 0;">
  <div class="qa-wlabel">Personal Moon Transit & Strength Score</div>
  <p class="blurred">Sarvashtakavarga score (/56) and Moon BAV (/8) on today's activated house, refined by the natal condition of your governing house lord.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Personalized transit working is locked.</b> Unlock to see the exact astrological strength behind today's climate.</p>
</div>

<div class="qa-window locked" style="margin:14px 0;">
  <div class="qa-wlabel">Full Action Guide — 3 Personalized Dos & 3 Don'ts</div>
  <p class="blurred">Complete tactical guidance grounded in today's active Tarabala, Chandrabala, and planetary weekday lord.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Full action guide is locked.</b> Unlock for all 6 rule-backed actions for today.</p>
</div>

<div class="qa-window locked" style="margin:14px 0;">
  <div class="qa-wlabel">Active Timing Clock & Life Phase Sub-Periods</div>
  <p class="blurred">The exact three-tier Dasha clock running today with transition dates and energy impact analysis.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Dasha timing stack is locked.</b> Unlock to see the active planetary periods governing today.</p>
</div>

<div class="buy" style="margin-top:20px;">
  <h3>Unlock full daily guidance</h3>
  <p>Your daily verdict, emotional climate, and lucky numbers remain free every morning. Subscribe to unlock precision clock windows, complete dos/donts, and deep chart workings every day.</p>
  <a class="cta" href="#unlock" data-unlock="1">Unlock full reading</a>
</div>"""


# ---------------------------------------------------------------------------
# the document
# ---------------------------------------------------------------------------
def render(reading: dict, *, name: str = "", day: Optional[date] = None,
           lat: float = 25.6, lon: float = 85.1, tz: float = 5.5,
           paid: bool = False, price: int = 298,
           pc: Optional[dict] = None) -> str:
    """One daily reading, gated. Returns a standalone HTML document."""
    import report_shell as RS

    reading = reading or {}
    day = day or date.today()
    first = _first(name or reading.get("client") or "")
    vc = reading.get("vedic_confluence") or {}
    lanes = [ln for ln in (vc.get("lanes") or []) if ln.get("signal")]
    d = reading.get("dasha") or {}

    body = (_hero(reading, day, len(lanes))
            + _moon_proof(reading, first)
            + _lucky(reading, paid=paid)
            + _dodont(reading, paid=paid))

    if paid:
        # Paid daily is the full personalization layer: the Moon transit is
        # tied to the natal house, exact SAV/BAV, house significator, running
        # dasha and the independent lanes. These are already computed by the
        # deterministic engine; this renderer does not recalculate them.
        body += (
            _personal_moon_focus(reading)
            + _dasha(reading)
            + _ashtakavarga(reading)
            + _houses(reading)
            + _windows(reading, day, lat, lon, tz)
            + _extras(reading)
        )
    else:
        body += _locked_preview(price=price, n_lanes=len(lanes),
                                md=d.get("md", ""), ad=d.get("ad", ""),
                                pd=d.get("pd", ""))

    moon = reading.get("moon_transit") or {}
    natal = reading.get("natal_moon") or {}
    sub_bits = [f"Moon in {moon['sign']}" if moon.get("sign") else "",
                f"{moon['nakshatra']}" if moon.get("nakshatra") else "",
                f"read against your birth Moon in {natal['sign']}"
                if natal.get("sign") else ""]
    sub = " · ".join(b for b in sub_bits if b)

    return RS.page(
        f"{first} — today" if first != "friend" else "Today",
        body,
        eyebrow=("Daily reading · unlocked" if paid
                 else "Daily reading · today's verdict, free"),
        heading=f"{day:%A %d %B}",
        sub=sub)


# ---------------------------------------------------------------------------
# legacy shim
# ---------------------------------------------------------------------------
def build(reading: dict, *, lat: float = 25.6, lon: float = 85.1,
          tz: float = 5.5, day: Optional[date] = None) -> dict:
    """The pre-gating card dict.

    Nothing in the served path uses this any more — `render()` consumes the
    engine output directly. It is kept because the standalone daily scripts in
    ci-storage still build a card before printing it.
    """
    day = day or date.today()
    moon = reading.get("moon_transit") or {}
    tara = (reading.get("tarabala") or {}).get("tone", "neutral")
    chandra_tone = (reading.get("chandrabal") or {}).get("tone", "neutral")
    chandra = reading.get("chandrabal") or {}

    wanted = ("Jupiter", "Mercury", "Venus")
    avoid = ("Mars", "Saturn", "Rahu")
    if tara == "caution":
        wanted, avoid = ("Jupiter", "Venus"), ("Mars", "Saturn", "Sun")

    do_use, dont_use = HORA_USE.get(reading.get("weekday_lord", ""), ("", ""))
    return {
        "date": day,
        "headline": TONE_LINE.get((tara, chandra_tone), DEFAULT_LINE),
        "house_note": HOUSE_FROM_MOON_NOTE.get(moon.get("house_from_moon"), ""),
        "moon": f"{moon.get('sign','')} · {moon.get('nakshatra','')}",
        "dos": [x for x in (do_use, (reading.get("tarabala") or {}).get("note"),
                            chandra.get("do_note")) if x],
        "donts": [x for x in (dont_use, chandra.get("note")) if x],
        "windows": pick_windows(day, lat, lon, tz, wanted=wanted, avoid=avoid),
    }
