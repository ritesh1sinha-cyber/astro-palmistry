"""The daily reading, as something you can act on before breakfast.

You left the shape to me, so here is the reasoning.

Co-Star built a habit out of one line plus a do/don't list — short enough to
read on a lock screen, specific enough to quote to a friend. That is the
engagement mechanic, and it is why people open the app daily. But a one-liner
is also the easiest thing in the world to dismiss as a horoscope column.

What the Indian market pays for, and what Co-Star does not have, is **timing**.
Hora — the planetary hour — is the oldest to-the-point timing tool in the
tradition: each hour of the day is ruled by a planet, in a fixed sequence from
sunrise. It is computable, it is checkable, and it converts "today is good for
money talk" into "between 11:42 and 12:39, today".

So the daily card is both:

    a headline line          ← the hook, one sentence
    do / don't               ← the habit, scannable
    2-3 timed windows        ← the reason to come back at 11:40

The reading itself comes from the real day chart: the Moon's sign and house
from your own Moon and rising sign, tarabala (how the day's star sits against
your birth star), chandrabala, and the weekday lord.
"""

from __future__ import annotations

import html as _html
import math
from datetime import date, datetime, time, timedelta
from typing import Any, Optional

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


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def _suffix(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


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


def build(reading: dict, *, lat: float = 25.6, lon: float = 85.1,
          tz: float = 5.5, day: Optional[date] = None) -> dict:
    """Turn the engine's daily reading into one headline, do/don't, windows."""
    day = day or date.today()
    moon = reading.get("moon_transit") or {}
    tara = (reading.get("tarabala") or {}).get("tone", "neutral")
    chandra = (reading.get("chandrabal") or {}).get("tone", "neutral")
    weekday_lord = reading.get("weekday_lord", "")

    headline = TONE_LINE.get((tara, chandra), DEFAULT_LINE)
    house_note = HOUSE_FROM_MOON_NOTE.get(moon.get("house_from_moon"), "")

    do_use, dont_use = HORA_USE.get(weekday_lord, ("", ""))
    chandra = reading.get("chandrabal") or {}
    dos = [x for x in (
        do_use,
        (reading.get("tarabala") or {}).get("note"),
        chandra.get("do_note"),
    ) if x]
    donts = [x for x in (dont_use, chandra.get("note")) if x]

    wanted = ("Jupiter", "Mercury", "Venus")
    avoid = ("Mars", "Saturn", "Rahu")
    if tara == "caution":
        wanted, avoid = ("Jupiter", "Venus"), ("Mars", "Saturn", "Sun")

    # The personalisation IS the product, so say it out loud. A sun-sign column
    # gives the same line to a twelfth of India. This is the Moon measured
    # against THIS person's birth Moon and rising sign: house_from_moon,
    # tarabala (today's star counted from their birth star) and chandrabala
    # are all functions of their chart, not of the calendar.
    natal = reading.get("natal_moon") or {}
    tara_name = (reading.get("tarabala") or {}).get("name", "")
    personal = []
    if moon.get("house_from_moon"):
        personal.append(
            f"The Moon is in your <b>{moon['house_from_moon']}"
            f"{_suffix(moon['house_from_moon'])} house counted from your own "
            f"birth Moon</b> in {natal.get('sign', '')} — not from a sun sign.")
    if tara_name and natal.get("nakshatra"):
        personal.append(
            f"Today's star is <b>{tara_name}</b> counted from your birth star "
            f"{natal.get('nakshatra')}. Someone born a day either side of you "
            f"gets a different reading.")
    if moon.get("house_from_lagna"):
        personal.append(
            f"From your rising sign it falls in the "
            f"<b>{moon['house_from_lagna']}"
            f"{_suffix(moon['house_from_lagna'])}</b>, which is the part of "
            f"life today actually lands on.")

    return {
        "date": day,
        "headline": headline,
        "house_note": house_note,
        "moon": f"{moon.get('sign','')} · {moon.get('nakshatra','')}",
        "personal": personal,
        "dos": dos, "donts": donts,
        "windows": pick_windows(day, lat, lon, tz, wanted=wanted, avoid=avoid),
    }


def render(card: dict) -> str:
    personal = "".join(f"<p>{x}</p>" for x in card.get("personal", []))
    dos = "".join(f"<div>{_e(x)}</div>" for x in card["dos"])
    donts = "".join(f"<div>{_e(x)}</div>" for x in card["donts"])
    wins = "".join(
        f'<li><b>{_e(w["when"])}</b><span>{_e(w["text"])}</span></li>'
        for w in card["windows"])
    return f"""
<section class="daily">
  <div class="lbl">Today · {card['date']:%A %d %B}</div>
  <h3>{_e(card['headline'])}</h3>
  <p style="font-size:.86rem;margin:0 0 4px">{_e(card['house_note'])}</p>
  <p style="font-size:.78rem;color:#6a7080;margin:0">Moon today: {_e(card['moon'])}</p>
  <div class="personal">{personal}</div>
  <div class="dodont">
    <div class="do"><div class="t">Do</div>{dos}</div>
    <div class="dont"><div class="t">Don't</div>{donts}</div>
  </div>
  <ul class="windows">{wins}</ul>
</section>"""
