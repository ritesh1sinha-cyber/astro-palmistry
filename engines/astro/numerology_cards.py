"""numerology_cards.py — the numbers in the cards-v2 language, gated.

`tab_renderers.render_numerology` reimplemented a thin subset of numerology from
its own small tables and never imported `numerology_report`, which has been
sitting next to it the whole time with the Chaldean cipher, the 45-year
mahadasha ring, the birthday-year and pratyantar layers, the Avasthi name-harmony
assessment and a name-correction search. The served report therefore promised
"name-correction and compatibility notes" on its pay card and then had nothing
to deliver, because the code that produces them was never called.

So this renders the real engine, twice, branching on `paid`, in the same
dialect as the chart, horary and palm reports:

    free    name-harmony verdict first, then concise core numbers, the current
            cycle and the Lo Shu gaps

    paid    corrected spellings first, the next three birthday years and
            practical remedies for missing Lo Shu numbers

The split follows the same rule as everywhere else: naming a thing is free,
fixing it is not. The empty Lo Shu cells are the hook precisely because the
reader can see them and cannot act on them.
"""

from __future__ import annotations

import html as _html
from datetime import date
from typing import Any, List, Optional


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def _first(name: str) -> str:
    n = (name or "").strip().split()
    return n[0] if n else "friend"


def _fmt(d: date) -> str:
    return f"{d.day} {d:%b} {d.year}"


def _short(text: Any, limit: int = 180) -> str:
    """Keep the first useful sentence; this is a report, not a source dump."""
    s = " ".join(str(text or "").split())
    first = s.split(". ", 1)[0].rstrip(".")
    if len(first) > limit:
        first = first[:limit].rsplit(" ", 1)[0]
    return first + ("." if first else "")


# ---------------------------------------------------------------------------
# free blocks
# ---------------------------------------------------------------------------
def _numbers(c: dict) -> str:
    """The six results in scan-friendly form; calculations stay out of the way."""
    import numerology_report as NR

    lp = c["life_path"]
    lp_title, lp_meaning = NR.LIFE_PATH.get(lp, ("", ""))
    rows = [
        ("Life path", lp, lp_title,
         lp_meaning, "every digit of your birth date, reduced"),
        ("Birth day", c["birth_day"], NR.planet_name(c["birth_day"]),
         NR._birthday_money(c["birth_day"]),
         f"the day you were born, {c['day']}"
         + ("" if c["birth_day"] == c["day"] else ", reduced")),
        ("Expression", c["expression"], "how you land on others",
         NR.EXPRESSION.get(c["expression"], ""),
         "every letter of your full name"),
        ("Soul urge", c["soul_urge"], "what you actually want",
         NR.SOUL_URGE.get(c["soul_urge"], ""),
         "the vowels of your name only"),
        ("Outer personality", c["personality"], "what strangers meet first",
         NR.PERSONALITY.get(c["personality"], ""),
         "the consonants of your name only"),
        ("Chaldean name root", c["chaldean_root"],
         f"compound {c['chaldean_total']} · {NR.planet_name(c['chaldean_root'])}",
         NR.AVASTHI_THEME.get(NR.avasthi_group(c["chaldean_root"]), ""),
         "your name in the older Chaldean cipher — this is the one name "
         "correction moves"),
    ]

    cards = ""
    for label, n, title, meaning, _src in rows:
        cards += f"""
    <div class="num-card">
      <div class="num-big">{_e(n)}</div>
      <div class="num-body">
        <div class="num-label">{_e(label)}</div>
        <b>{_e(title)}</b>
        <p>{_e(_short(meaning))}</p>
      </div>
    </div>"""

    debts = ""
    if c.get("karmic_debts"):
        items = "".join(
            f'<li><b>{_e(label)} lands on {_e(total)}</b> — '
            f'{_e(NR.KARMIC_DEBT_TEXT.get(total, ""))}</li>'
            for label, total in c["karmic_debts"].items())
        debts = (f'<details class="workings"><summary>Karmic-debt note</summary>'
                 f'<div class="workings-body"><ul>{items}</ul></div></details>')

    return f"""
<h3 class="sec">Your core numbers</h3>
<div class="num-grid">{cards}</div>
{debts}"""


def _lo_shu(c: dict, *, paid: bool) -> str:
    """The grid, and the holes in it.

    Counts come from `numerology_report._effective_loshu_counts`, which places
    the birth-day and life-path pillars into the square, rather than from
    `lo_shu.build`, which counts the date alone. Showing one set of holes here
    and remedying a different set below is the sort of contradiction a reader
    notices immediately.
    """
    import lo_shu as LS
    import numerology_report as NR

    counts = NR._effective_loshu_counts(c)
    missing, _raw_missing, _pillar_only = NR._effective_grid_missing(c)

    cells = ""
    for row in LS.GRID:
        for n in row:
            cnt = counts.get(n, 0)
            label, _what = LS.MEANING.get(n, ("", ""))
            fill = "".join(str(n) for _ in range(cnt)) if cnt else "&mdash;"
            cells += (f'<div class="lo-cell {"has" if cnt else "empty"}">'
                      f'<span class="lo-n">{n}</span>'
                      f'<span class="lo-count">{fill}</span>'
                      f'<span class="lo-what">{_e(label)}</span></div>')

    notes = ""
    if missing:
        named = ", ".join(str(m) for m in missing)
        themes = ", ".join(
            _short(LS.MISSING.get(m, ""), 70).rstrip(".") for m in missing[:3])
        notes = (f'<p><b>Your missing numbers: {named}.</b>'
                 + (f' The main growth themes are {themes}.' if themes else "")
                 + '</p>')
    else:
        notes = "<p><b>Every cell is filled.</b> Your grid has no basic gap.</p>"

    if paid:
        remedies = NR._missing_remedy_lines(missing)
        tail = (f'<details class="workings"><summary>Simple remedies for the '
                f'missing numbers</summary><div class="workings-body">'
                f'<ul class="palm-list plain">{remedies}</ul></div></details>'
                if remedies else "")
    else:
        n = len(missing)
        tail = (f'<div class="when locked-inline"><span class="lockicon">&bull;</span> '
                f'Each empty cell has a named remedy — the colour, the habit, the '
                f'charity and the day it belongs on — and they are not equally '
                f'urgent. {"All " + str(n) + " are" if n else "They are"} in the '
                f'full reading.</div>' if n else "")

    return f"""
<h3 class="sec">Your Lo Shu grid</h3>
<div class="card">
  <div class="lo-grid">{cells}</div>
  {notes}
  {tail}
</div>"""


def _where_now(c: dict, pos: dict, *, paid: bool) -> str:
    """Current prediction first; only the next three useful turns are paid."""
    import numerology_report as NR

    maha = pos["maha"]
    antar = pos["antar_n"]
    praty = pos["praty_cur"]
    core = NR.DASHA_PREDICT.get(maha["num"], {}).get("core", "")

    current = f"""
<h3 class="sec">Where you are now</h3>
<div class="card">
  <p class="claim">Your current theme is <b>{_e(maha['planet'])}</b>, coloured
  this year by <b>{_e(NR.PLANET[antar])}</b> and right now by
  <b>{_e(praty['planet'])}</b>.</p>
  <p>{_e(_short(core))}</p>
</div>"""
    if not paid:
        return current

    ahead = ""
    for i in (1, 2, 3):
        year = pos["antar_year"] + i
        n, _wd, _lord = NR.antar_number(c["dob"], year)
        starts = date(year, c["dob"].month, c["dob"].day)
        ahead += (f'<li><b>{_e(NR.PLANET[n])} year ({n})</b>'
                  f'<span class="pt-when">from {_fmt(starts)}</span>'
                  f'<p>{_e(_short(NR._dasha_prediction(n, c, "antar")))}</p></li>')

    return current + f"""
<h3 class="sec">Your next three years</h3>
<div class="card"><ul class="palm-points">{ahead}</ul></div>"""


def _harmony(c: dict, h: dict, *, paid: bool) -> str:
    """Does the name pull with the birth date or against it."""
    import numerology_report as NR

    verdict = {
        "strong": "Your name and your birth date pull in the same direction.",
        "partial": "Your name agrees with one of your two pillars and not the other.",
        "discordant": "Your name and your birth date pull against each other.",
    }[h["alignment"]]
    pill = {"strong": "up", "partial": "mixed", "discordant": "down"}[h["alignment"]]
    pill_txt = {"strong": "In tune", "partial": "Half in tune",
                "discordant": "Out of tune"}[h["alignment"]]

    detail = (
        f"Name total {c['chaldean_total']} → root {h['ch_r']}; "
        f"birth-day root {h['bd_r']}; life-path root {h['lp_r']}.")
    if h["karmic_compound"]:
        detail += (f" The compound {c['chaldean_total']} is one of the four "
                   f"karmic-debt numbers, which the tradition treats as worth "
                   f"correcting on its own.")

    if not paid:
        body = (f'<div class="evidence locked-inline">'
                f'<span class="ev-label">Your corrected spellings</span>'
                f'<p><span class="lockicon">&bull;</span> '
                + ("Spellings of your own name that move the total onto a root "
                   "your birth date agrees with — using letters already in it, "
                   "not a new name. Unlock to see your suggestions."
                   if h["needs_remedy"] else
                   "The alternative spellings, and what each one would move, "
                   "without forcing a change.")
                + "</p></div>")
    else:
        targets = h.get("targets") or []
        suggestions = NR.suggest_name_corrections(c["name"], targets)
        if suggestions:
            rows = "".join(
                f'<li><b>{_e(s["spelling"])}</b>'
                f'<span class="pt-when">total {_e(s["compound"])} &rarr; root {_e(s["root"])}</span>'
                f'<p>{_e(s["added"])}. Chosen to {_e(s["reason"])}.</p></li>'
                for s in suggestions[:3])
            body = (f'<div class="evidence"><span class="ev-label">Your suggested '
                    f'name spellings</span><ul class="palm-points">{rows}</ul>'
                    f'<p class="fine">These reuse letters already in your name. '
                    f'You can test a spelling in everyday use; no legal name '
                    f'change is required.</p></div>')
        else:
            want = ", ".join(str(t[0]) for t in targets[:4])
            body = (f'<div class="evidence"><span class="ev-label">Your name '
                    f'correction result</span><p>No natural respelling of your name '
                    f'lands on a friendly root ({want}) within two letter changes. '
                    f'That is a real result, not a gap: your name is already close '
                    f'enough that forcing it would do more harm than the mismatch '
                    f'does.</p></div>')

    return f"""
<h3 class="sec">Name check &amp; correction</h3>
<p class="sec-note">Your birth date is fixed. Your everyday name is the one
part you can adjust.</p>
<article class="card">
  <div class="card-top"><span class="area">Name harmony</span>
    <span class="pill {pill}">{_e(pill_txt)}</span></div>
  <p class="claim">{_e(verdict)}</p>
  <p class="fine"><b>Technical basis:</b> {_e(detail)}</p>
  {body}
</article>"""


# ---------------------------------------------------------------------------
# paid working
# ---------------------------------------------------------------------------
def _letter_table(title: str, letters: List[tuple], total: int, note: str) -> str:
    if not letters:
        return ""
    head = "".join(f"<th>{_e(ch)}</th>" for ch, _v in letters)
    vals = "".join(f"<td>{_e(v)}</td>" for _ch, v in letters)
    return (f"<h5>{_e(title)}</h5><p>{_e(note)}</p>"
            f"<table><tr>{head}<th>=</th></tr>"
            f"<tr>{vals}<td><b>{_e(total)}</b></td></tr></table>")


def _workings(c: dict) -> str:
    """Every number derived in front of the reader, digit by digit."""
    import numerology_report as NR

    lp_digits = f"{c['day']:02d}{c['month']:02d}{c['year']}"
    bd_line = (f"Your birth day {c['day']} is a master number and is not "
               f"reduced further" if c["birth_day"] in NR.MASTERS
               else f"Your birth day {c['day']} reduces to {c['birth_day']}")
    lp_line = (f" — a master number, so it is not reduced to its root "
               f"{NR.reduce_num(c['life_path'], keep_master=False)}"
               if c["life_path"] in NR.MASTERS else "")
    body = (
        f"<h4>The birth-date numbers</h4>"
        f"<p>{' + '.join(lp_digits)} = {c['life_path_raw']}, reduced to "
        f"<b>{c['life_path']}</b>{lp_line}. {bd_line}.</p>"
        f"<h4>The name numbers</h4>"
        + _letter_table(
            "Chaldean — the cipher name correction works on",
            c["chaldean_letters"], c["chaldean_total"],
            "The Chaldean cipher has no 9 and assigns values by sound rather "
            "than alphabet order, which is why it disagrees with the "
            "Pythagorean total below.")
        + _letter_table(
            "Pythagorean — the cipher Expression is built on",
            c["pyth_letters"], c["expr_total"],
            f"Vowels alone total {c['soul_total']} (Soul urge "
            f"{c['soul_urge']}); consonants alone total {c['pers_total']} "
            f"(Outer personality {c['personality']}).")
    )

    if c.get("karmic_lessons"):
        rows = "".join(
            f"<li><b>{n}</b> — {_e(NR.KARMIC_LESSON_WOODS.get(n, ''))}</li>"
            for n in c["karmic_lessons"])
        body += (f"<h4>Digits your name never uses</h4>"
                 f"<p>{_e(NR._karmic_lesson_text(c))}</p><ul>{rows}</ul>")

    pins = ""
    for i, num in enumerate(c["pinnacle_nums"]):
        lo, hi = c["pinnacle_ages"][i]
        span = f"age {lo}–{hi}" if hi else f"age {lo} onward"
        pins += (f"<li><b>{span}: {num}</b> — "
                 f"{_e(NR._pinnacle_theme(num))}</li>")
    body += (f"<h4>Your four pinnacles</h4><p>The pivot age is "
             f"{c['pin_age1']}, which is 36 minus your life-path root.</p>"
             f"<ul>{pins}</ul>")

    chal = "".join(
        f"<li><b>Challenge {i + 1}: {n}</b> — "
        f"{_e(NR.CHALLENGE_THEME.get(n, ''))}</li>"
        for i, n in enumerate(c["challenges"]))
    # The source text derives the fourth challenge exactly as it derives the
    # first, so for most dates the two repeat. Saying so is better than letting
    # it read as an arithmetic slip.
    dupe = ""
    if c["challenges"][3] == c["challenges"][0]:
        std = c["challenge4_std"]
        dupe = (f'<p class="fine">The book builds the fourth challenge the same '
                f'way as the first, which is why yours repeat. The common modern '
                f'convention subtracts year from month instead and would give '
                f'<b>{std}</b> — {_e(NR.CHALLENGE_THEME.get(std, ""))}</p>')
    passion = ""
    if c.get("hidden_passion"):
        passion = (f"<p>Hidden passion <b>{c['hidden_passion']}</b> — the digit "
                   f"your name repeats more than any other, read as the talent "
                   f"you return to whether or not you planned to.</p>")
    body += (f"<h4>Your challenges</h4><ul>{chal}</ul>{dupe}"
             f"<p>Maturity number <b>{c['maturity']}</b> — "
             f"{_e(NR._maturity_text(c['maturity']))}</p>{passion}")

    return f"""
<details class="workings workings-main">
  <summary>The working — every number derived in front of you</summary>
  <div class="workings-body">{body}</div>
</details>"""


def _locked_preview(*, price: int, n_missing: int, maha: str,
                    needs_name_fix: bool) -> str:
    name_teaser = (
        "Spellings of your own name that move it onto a root your birth date "
        "agrees with, using letters already in it."
        if needs_name_fix else
        "What every alternative spelling of your name would move, and why "
        "yours is already close.")
    cell_teaser = (
        f"The colour, habit, charity and day for each of your {n_missing} empty "
        "cells, in the order they actually matter."
        if n_missing else
        "The remedy attached to each cell, and which of them you are running "
        "thin on this year.")
    rows = [
        ("Your name-correction suggestions", name_teaser),
        ("Your next three years",
         "The main theme of each birthday year, with its start date."),
        ("What to do about each empty Lo Shu cell", cell_teaser),
    ]
    items = "".join(
        f'<div class="when locked-inline" style="margin:8px 0">'
        f'<span class="lockicon">&bull;</span> <strong>{_e(t)}</strong> &mdash; {_e(s)}'
        f'</div>' for t, s in rows)
    return f"""
<section class="section locked-preview">
  <h3 class="sec">What the full reading adds</h3>
  <div class="card">{items}</div>
  <div class="buy">
    <h3>Put your numbers to work</h3>
    <p>Unlock your strongest name spellings, your next three years, and simple
    actions for the gaps in your grid.</p>
    <a class="cta" href="#unlock" data-unlock="1">Unlock &mdash; &#8377;{price}</a>
  </div>
</section>"""


# ---------------------------------------------------------------------------
# the document
# ---------------------------------------------------------------------------
def build(name: str, dob: date, *, today: Optional[date] = None) -> tuple:
    """Everything both halves need, computed once."""
    import numerology_report as NR

    c = NR.compute(name, dob)
    pos = NR.current_position(c, today or date.today())
    h = NR.assess_name_harmony(c)
    return c, pos, h


def render(name: str, dob: date, *, paid: bool = False, price: int = 298,
           today: Optional[date] = None,
           precomputed: Optional[tuple] = None) -> str:
    """One numerology reading, gated. Returns a standalone HTML document."""
    import report_shell as RS
    import numerology_report as NR

    c, pos, h = precomputed or build(name, dob, today=today)
    first = _first(name)
    missing, _raw, _pillar = NR._effective_grid_missing(c)

    body = (_harmony(c, h, paid=paid)
            + _numbers(c)
            + _where_now(c, pos, paid=paid)
            + _lo_shu(c, paid=paid))

    if not paid:
        body += _locked_preview(price=price, n_missing=len(missing),
                                maha=pos["maha"]["planet"],
                                needs_name_fix=bool(h.get("needs_remedy")))

    lp = c["life_path"]
    return RS.page(
        f"{first} — your numbers", body,
        eyebrow=("Numerology · unlocked" if paid
                 else "Numerology · every number, free"),
        heading=f"{first}, this is what your numbers add up to.",
        sub=f"Born {dob:%d %B %Y} · life path {lp} · "
            f"name root {c['chaldean_root']} · "
            f"{len(missing)} empty Lo Shu cell{'s' if len(missing) != 1 else ''}")
