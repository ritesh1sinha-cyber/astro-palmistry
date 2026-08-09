"""What the customer actually receives, per job kind.

The handlers used to call a report generator per kind and then hand the HTML to
`astro_split` to cut it into a free half and a paid half by looking for section
headings. That worked for the old long-form reports, where "free" and "paid"
were contiguous blocks of text.

The card design does not split that way. The paywall sits INSIDE each card — the
headline and the evidence are free, the dated window and the remedy are not — so
cutting the document in half would either give away the timing or hide the
headlines. Every renderer here already takes `paid: bool` and locks the right
parts in place, which means the honest way to produce two halves is to render
twice.

That also removes a whole class of bug: there is no longer any way for a section
to land on the wrong side of the paywall because a heading was renamed.

One module per screen, one function each, all returning `(free_html, paid_html,
meta)` so `core.handlers` stays thin and testable.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

import report_shell as RS


def clean(html: str) -> str:
    """Public wrapper so callers appending their own HTML can scrub it too.

    `core.handlers` bolts the old long-form document onto the paid half as an
    appendix. That append happened AFTER the render, so the appendix bypassed the
    chokepoint entirely and leaked a lane called "Longevity" into the paid
    report. Anything concatenated onto a rendered document has to come back
    through here.
    """
    return _scrub(html)


def _safe(fn, *a, **k) -> str:
    """A supporting block must never take the whole report down with it."""
    try:
        return fn(*a, **k) or ""
    except Exception as exc:                                         # noqa: BLE001
        print(f"[report_render] {getattr(fn, '__module__', '?')}."
              f"{getattr(fn, '__name__', '?')} failed: "
              f"{type(exc).__name__}: {exc}", flush=True)
        return ""


def _voice_polish(html: str) -> str:
    """Plain-English pass for customer fragments (no personal opening block)."""
    try:
        import os
        import astro_voice as V
        out = V.strip_leaks(html or "")
        out = V.strip_machinery(out)
        out = V.humanise(out)
        out = V.strip_citations(out, hide_system_names=True)
        if os.getenv("PLAIN_ENGLISH", "1") == "1":
            out = V.translate_jargon(V.rephrase(out), keep_original=False)
        return out
    except Exception:                                                # noqa: BLE001
        return html


def _scrub(html: str) -> str:
    """Last gate before a customer sees anything. Never bypass this.

    `no_longevity.scrub` was written for sentences. Run over a whole document it
    also rewrites the stylesheet — its whitespace and punctuation tidying is
    harmless there but pointless, and one of its numeric patterns could in
    principle eat a CSS value. So the <style> and <script> blocks are lifted out,
    the prose is scrubbed, and they are put back untouched.

    (The pass that found this also caught scrub turning "21.5 of 36" into
    "21. 5 of 36" — fixed in no_longevity itself, since that bug applied to any
    decimal anywhere.)
    """
    try:
        from no_longevity import scrub
    except Exception:                                                # noqa: BLE001
        return html
    out = scrub(html) if "<style" not in html and "<script" not in html \
        else _scrub_stashed(html, scrub)

    # Direct, concise voice — cut filler without touching a fact. The card
    # design skips `astro_voice.personalise` for most kinds, so this is the
    # only gate horary / daily / numerology / muhurat / BTR prose passes.
    try:
        from astro_voice import concise
        out = concise(out)
    except Exception:                                                # noqa: BLE001
        pass
    return out


def _scrub_stashed(html: str, scrub) -> str:
    import re as _re
    keep: list[str] = []

    def _stash(m: "_re.Match[str]") -> str:
        keep.append(m.group(0))
        return f"\x00KEEP{len(keep) - 1}\x00"

    stashed = _re.sub(r"<(style|script)\b.*?</\1>", _stash, html,
                      flags=_re.S | _re.I)
    out = scrub(stashed)
    for i, block in enumerate(keep):
        out = out.replace(f"\x00KEEP{i}\x00", block)
    return out


def _appendix_block(html: str, *, summary: str) -> str:
    """Long-form lane document — fragment only, no nested stylesheets."""
    if not html or not html.strip():
        return ""
    import astro_split as SP
    body = SP.as_fragment(clean(html))
    if not body.strip():
        return ""
    return (f'<details class="workings workings-main"><summary>{summary}</summary>'
            f'<div class="workings-wrap">{body}</div></details>')

# ---------------------------------------------------------------------------
# the flagship
# ---------------------------------------------------------------------------
def full_report(pc: dict, *, name: str = "", question: str = "",
                today: Optional[date] = None, price: int = 298,
                bundle_price: int = 298, lat: float = 0.0, lon: float = 0.0,
                tz: float = 5.5, daily: Any = None) -> tuple:
    """Present read, who you are, your past, the cards, timing, remedies.

    Order is deliberate and it is the commercial argument as much as the
    editorial one: the reader meets a claim about the six months they have just
    lived BEFORE anything is asked of them. If that lands, everything after it
    is credible; if it does not, they should close the page.
    """
    today = today or date.today()
    first = (name or "").split()[0] if name else ""

    import deep_evidence as DE
    DE.begin(pc, lat=lat, lon=lon, tz=tz, today=today)
    try:
        return _full_report_inner(
            pc, name=name, question=question, today=today, price=price,
            bundle_price=bundle_price, lat=lat, lon=lon, tz=tz, daily=daily,
            first=first)
    finally:
        DE.end()


def _full_report_inner(pc: dict, *, name: str = "", question: str = "",
                       today: date, price: int = 298, bundle_price: int = 298,
                       lat: float = 0.0, lon: float = 0.0, tz: float = 5.5,
                       daily: Any = None, first: str = "") -> tuple:
    present_html = ""
    try:
        import present_read as PR
        present_html = PR.render(PR.build(pc, today=today))
    except Exception as exc:                                         # noqa: BLE001
        print(f"[report_render] present read failed: {exc}", flush=True)

    past_html = ""
    try:
        import report_recognition as RR
        past_html = RR.render(RR.build(pc))
    except Exception as exc:                                         # noqa: BLE001
        print(f"[report_render] your-past failed: {exc}", flush=True)

    timing_html = ""
    timing_rows: list = []
    n_periods = 0
    try:
        import report_cards as RC
        import report_timing as RT
        areas = [(a.key, a.house) for a in RC.AREAS]
        labels = {a.key: a.label for a in RC.AREAS}
        timing_rows = RT.best_windows(pc, areas, years=5, limit=4,
                                      lat=lat, lon=lon, tz=tz)
        timing_html = RT.render(pc, timing_rows, labels)
        n_periods = len(RC.build_timeline(pc, today=today))
    except Exception as exc:                                         # noqa: BLE001
        print(f"[report_render] timing failed: {exc}", flush=True)
    n_windows = len(timing_rows)

    q_html = ""

    def build(paid: bool) -> str:
        import report_cards as RC
        remedy = _safe(_remedy, pc, name=first, paid=paid, price=price)
        if paid:
            tail = timing_html + remedy
        else:
            tail = (remedy
                    + _locked_preview(price=price, n_areas=len(RC.AREAS),
                                      n_windows=n_windows, n_periods=n_periods)
                    + _bundle(bundle_price))
        body = RC.render(
            pc, name=name, price=price, today=today, paid=paid,
            question_html="",
            proof_html=present_html + past_html,
            timing_html=tail)
        return _scrub(body)

    free_html, paid_html = build(False), build(True)
    meta = {
        "design": "cards-v2",
        "price": price, "bundlePrice": bundle_price,
        "freeSections": ["Where you are right now", "Who your chart says you are",
                         "Your past", "Every life area, and which way it leans"],
        "paidSections": ["Why each life area reads the way it does",
                         "Exact dates for every life area",
                         "When it actually happens — the five-year windows",
                         "The full period sequence",
                         "What helps, per area",
                         "Remedies and gemstones"],
        "teasers": {},
    }
    return free_html, paid_html, meta


def _remedy(pc: dict, *, name: str = "", paid: bool = False,
            price: int = 298) -> str:
    import remedy_block as RB
    return RB.render(
        RB.build(pc, domain="", name=name), paid=paid, price=price,
        lede="Your chart's difficult places all have a classical answer. Some of "
             "them say do NOT wear the obvious stone. That half is free, "
             "because nobody else will tell you.")


def _locked_preview(*, price: int, n_areas: int, n_windows: int,
                    n_periods: int) -> str:
    """Free view: locked rows for dates, working and remedies + unlock CTA."""
    import html as _html

    def _e(t: Any) -> str:
        return _html.escape(str(t or ""))

    windows_teaser = (
        f"{n_windows} dated window{'s' if n_windows != 1 else ''} "
        "across the next five years."
        if n_windows else
        "The strongest windows across the next five years.")
    periods_teaser = (
        f"{n_periods} period{'s' if n_periods != 1 else ''} with real dates."
        if n_periods else
        "Your own timing sequence, with real dates.")
    rows = [
        ("Why each area reads the way it does",
         f"The chart working behind all {n_areas} headlines."),
        ("The dated window for every life area",
         "When each part of your life actually moves."),
        ("When it actually happens", windows_teaser),
        ("The full period sequence", periods_teaser),
        ("What helps in each area",
         "The practical step and mantra where one applies."),
        ("Every gemstone that suits you",
         "Metal, finger and the day to begin."),
    ]
    items = "".join(
        f'<div class="when locked-inline" style="margin:8px 0">'
        f'<span class="lockicon">•</span> <strong>{_e(title)}</strong> — {_e(teaser)}'
        f'</div>'
        for title, teaser in rows)
    return f"""
<section class="section locked-preview">
  <h2 class="sec">What the full reading adds</h2>
  <div class="card">{items}</div>
  <div class="buy">
    <h3>The working and the dates</h3>
    <p>You have the verdict on each life area. Unlock why, when, and what to do.</p>
    <a class="cta" href="#unlock" data-unlock="1">Unlock full reading</a>
  </div>
</section>"""


def _bundle(bundle_price: int) -> str:
    """Shown only in the free view. Bundle unlock is quote-only via email."""
    _ = bundle_price  # fixed button pricing; bundle is hand-quoted
    return """
<section class="card" style="background:#16181d;color:#f7f5f1;border:0">
  <div class="ev-label" style="color:#c9a227">Everything, one package</div>
  <h3 style="font-family:Fraunces,serif;font-size:1.3rem;margin:8px 0 8px">
    Want the full bundle for your family?</h3>
  <p style="margin:0 0 10px;font-size:.9rem;opacity:.85">The complete set —
  full chart reading, birth-time rectification, kundali matching, palm reading,
  numerology, questions, daily readings and remedies — is arranged by hand.
  Write to us and we will set it up for you.</p>
  <p style="margin:0 0 14px;font-size:.9rem">
    <a href="mailto:admin@graharekha.co.in"
       style="color:#f4d79b;font-weight:600;text-decoration:underline">
      admin@graharekha.co.in</a></p>
  <p style="margin:0;font-size:.78rem;opacity:.6">If your birth time is
  uncertain, start with birth-time rectification — every other reading is built
  on it.</p>
</section>"""


# ---------------------------------------------------------------------------
# horary — one answer, not two engines arguing
# ---------------------------------------------------------------------------
def horary(*, question: str, verdicts: dict, western_judgment: dict,
           asked: str, name: str = "", horary_price: int = 298,
           full_report_price: int = 298,
           vedic_customer: Optional[dict] = None) -> tuple:
    from horary_answer import build_answer_html
    common = dict(question=question, verdicts=verdicts,
                  western_judgment=western_judgment, asked=asked, name=name,
                  horary_price=horary_price, full_report_price=full_report_price,
                  vedic_customer=vedic_customer)
    free_body, _ = build_answer_html(**common, paid=False)
    paid_body, answer = build_answer_html(**common, paid=True)

    # No shell heading: build_answer_html already opens with the question and
    # when it was asked. Passing them again printed the question twice.
    # Voice polish strips machinery (python paths, MiniLM, rebuild notes) and
    # keeps the tone consistent with every other customer report.
    free = RS.page(f"Your question — {question[:60]}",
                   _scrub(_voice_polish(free_body)))
    paid = RS.page(f"Your question — {question[:60]}",
                   _scrub(_voice_polish(paid_body)))
    meta = {"design": "cards-v2", "answer": answer, "question": question,
            "asked": asked, "price": horary_price,
            "paidSections": ["The verdict — all four methods combined",
                             "Which planets are in favour and which are working against you",
                             "The timing — dated windows",
                             "The remedy — what tips this your way"],
            "teasers": {}}
    return free, paid, meta


# ---------------------------------------------------------------------------
# user question — natal chart, half free (working) / paid (verdict + dates + remedy)
# ---------------------------------------------------------------------------
def user_question(pc: dict, *, question: str, route: Any = None, name: str = "",
                  price: int = 298, lat: float = 0.0, lon: float = 0.0,
                  tz: float = 5.5, today: Optional[date] = None,
                  area: str = "") -> tuple:
    import question_answer as QA
    today = today or date.today()
    first = (name or "").split()[0] if name else ""

    result = QA.answer(pc, question, lat=lat, lon=lon, tz=tz, route=route,
                       area=area)
    free_body = _voice_polish(QA.render(result, name=first, paid=False, price=price))
    paid_body = _voice_polish(QA.render(result, name=first, paid=True, price=price))
    try:
        import remedy_block as RB
        rb = RB.build(pc, domain=result.get("area_key", ""), question=question,
                      name=first)
        # Timing is already in the body; remedy closes the paid reading — the
        # two things a person asking a life question actually wants to act on.
        paid_body += RB.render(
            rb, paid=True, price=price,
            heading="The remedy — what tips the timing your way",
            lede="Practical first, then the classical support for the planets "
                 "that own this question.")
    except Exception:                                                # noqa: BLE001
        pass

    title = f"Your question — {question[:60]}"
    free = RS.page(title, _scrub(free_body))
    paid = RS.page(title, _scrub(paid_body))
    answer = QA.answer_meta(result)
    meta = {"design": "cards-v2", "answer": answer, "question": question,
            "area": area or result.get("area") or "",
            "price": price,
            "paidSections": ["The verdict — what your chart actually says",
                             "Timing — dated windows when to move",
                             "Watch-out rules for this question",
                             "Chart-targeted remedy"],
            "teasers": {}}
    return free, paid, meta


# ---------------------------------------------------------------------------
# numerology — every number and its verdict free, the working behind them paid
# ---------------------------------------------------------------------------
def _as_date(v) -> date:
    """Handlers pass dob as an ISO string; the numerology maths needs a date."""
    if isinstance(v, date):
        return v
    y, m, d = (int(x) for x in str(v)[:10].split("-"))
    return date(y, m, d)


NUMEROLOGY_FREE_SECTIONS = (
    "Your six numbers, and what each one says",
    "Your Lo Shu grid, and which cells are empty",
    "Where you are in the cycle right now",
    "Whether your name and your birth date agree",
)
NUMEROLOGY_PAID_SECTIONS = (
    "The working — every number derived letter by letter",
    "Your chapters, dated, and this year cut into nine slices",
    "The next three birthday years",
    "What to do about each empty Lo Shu cell",
    "The remedy for the period you are running now",
    "Name corrections that move your number",
)


def _numerology_teaser(c: dict, pos: dict, h: dict, n_missing: int) -> str:
    """Shown on the site's pay card, so it has to stand on its own."""
    bits = [f"how each of your six numbers was built",
            f"your {pos['maha']['planet']} chapter with dates"]
    if n_missing:
        bits.append(f"a remedy for each of your {n_missing} empty Lo Shu cells")
    else:
        bits.append("the remedy for the period you are running")
    bits.append("spellings that would fix your name number"
                if h.get("needs_remedy") else "the name-correction working")
    return ("Every number and its meaning is free. The full reading adds "
            + ", ".join(bits[:-1]) + " and " + bits[-1] + ".")


def numerology(name: str, dob, *, today: Optional[date] = None,
               price: int = 298) -> tuple:
    import numerology_cards as NC
    import numerology_report as NR
    dob = _as_date(dob)
    today = today or date.today()

    pre = NC.build(name, dob, today=today)
    c, pos, h = pre
    missing, _raw, _pillar = NR._effective_grid_missing(c)

    def render(paid: bool) -> str:
        return _scrub(NC.render(name, dob, paid=paid, price=price,
                                today=today, precomputed=pre))

    free, paid = render(False), render(True)
    meta = {"design": "cards-v2", "price": price,
            "teaser": _numerology_teaser(c, pos, h, len(missing)),
            "freeSections": list(NUMEROLOGY_FREE_SECTIONS),
            "paidSections": list(NUMEROLOGY_PAID_SECTIONS),
            "emptyCells": len(missing),
            "nameAlignment": h["alignment"],
            "teasers": {}}
    return free, paid, meta


# ---------------------------------------------------------------------------
# kundali matching
# ---------------------------------------------------------------------------
def kundali_match(match_meta: dict, *, groom: str = "", bride: str = "",
                  price: int = 298) -> tuple:
    import tab_renderers as TR

    def build(paid: bool) -> str:
        body = TR.render_match(match_meta, groom=groom, bride=bride, paid=paid,
                               price=price)
        # render_match prints its own couple header and score hero.
        return _scrub(RS.page(f"{groom} & {bride} — compatibility", body))

    free, paid = build(False), build(True)
    meta = {"design": "cards-v2", "price": price,
            "paidSections": ["Each dosha and what waives it",
                             "The Navamsha (D9) synastry",
                             "Remedies for the blocking doshas"],
            "teasers": {}}
    return free, paid, meta


# ---------------------------------------------------------------------------
# daily — verdict free every morning, the working behind it on subscription
# ---------------------------------------------------------------------------
DAILY_FREE_SECTIONS = (
    "Today's verdict, and how many methods agree with it",
    "Where the reading comes from, in your own chart",
    "Your lucky number and colour",
    "One thing to do and one to avoid",
)
DAILY_PAID_SECTIONS = (
    "Every lane that voted on today, with its signal",
    "The dasha you are running, down to pratyantar, with dates",
    "Ashtakavarga on today's transits, including your dasha lords",
    "The houses today's sky is lighting up",
    "What helps while this period runs",
    "Rahu Kaal, choghadiya and Abhijit for your birth place",
)


def _daily_teaser(reading: dict, n_lanes: int) -> str:
    """Shown on the site's subscribe card, so it has to stand on its own."""
    d = (reading or {}).get("dasha") or {}
    stack = "-".join(x for x in (d.get("md"), d.get("ad"), d.get("pd")) if x)
    parts = []
    if n_lanes:
        parts.append(f"all {n_lanes} lanes that voted on today")
    if stack:
        parts.append(f"the {stack} period you are running, with its dates")
    parts.append("the Ashtakavarga bindus under your dasha lords")
    parts.append("today's Rahu Kaal and choghadiya")
    return ("Today's verdict is yours free. The subscription opens "
            + ", ".join(parts[:-1]) + " and " + parts[-1] + " — every morning.")


def daily(reading: dict, *, lat: float = 25.6, lon: float = 85.1,
          tz: float = 5.5, day: Optional[date] = None, name: str = "",
          price: int = 298, pc: Optional[dict] = None) -> tuple:
    import daily_card as DC
    day = day or date.today()
    reading = reading or {}

    def build(paid: bool) -> str:
        return _scrub(DC.render(reading, name=name, day=day, lat=lat, lon=lon,
                                tz=tz, paid=paid, price=price, pc=pc))

    free, paid_html = build(False), build(True)
    lanes = [x for x in ((reading.get("vedic_confluence") or {}).get("lanes") or [])
             if x.get("signal")]
    meta = {"design": "cards-v2", "price": price, "date": day.isoformat(),
            "teaser": _daily_teaser(reading, len(lanes)),
            "freeSections": list(DAILY_FREE_SECTIONS),
            "paidSections": list(DAILY_PAID_SECTIONS),
            "laneCount": len(lanes),
            "teasers": {}}
    return free, paid_html, meta


# ---------------------------------------------------------------------------
# birth-time check
# ---------------------------------------------------------------------------
def btr(res: dict, *, price: int = 298) -> tuple:
    import tab_renderers as TR

    def build(paid: bool) -> str:
        body = TR.render_btr(res, paid=paid, price=price)
        return _scrub(RS.page("Birth-time check", body))

    free, paid_html = build(False), build(True)
    meta = {"design": "cards-v2", "price": price,
            "skipped": bool(res.get("skipped")),
            "reason": res.get("reason"),
            "paidSections": ["The exact rectified time, to the second",
                             "Your corrected rising sign and divisional charts",
                             "How each life event scored against it",
                             "The full ±90 minute scan and the fine refinement"],
            "teasers": {}}
    return free, paid_html, meta


# ---------------------------------------------------------------------------
# muhurat — day verdict free; checks, hours, alternatives paid
# ---------------------------------------------------------------------------
def muhurat(summary: dict, detail: Optional[dict] = None, *,
            price: int = 298, event_id: str = "", date_str: str = "") -> tuple:
    import tab_renderers as TR
    detail = detail or {}
    summary = summary or {}

    def build(paid: bool) -> str:
        body = TR.render_muhurat(
            summary, detail if paid else {},
            paid=paid, price=price, event_id=event_id, date_str=date_str)
        label = summary.get("event_label") or event_id or "Muhurat"
        return _scrub(RS.page(f"{label} — {date_str or summary.get('target_date') or ''}",
                              body))

    free, paid_html = build(False), build(True)
    n_alt = summary.get("alternativeCount")
    if n_alt is None:
        n_alt = len(detail.get("alternatives") or [])
    meta = {"design": "cards-v2", "price": price,
            "verdict": summary.get("verdict"),
            "eventId": event_id,
            "date": date_str or summary.get("target_date"),
            "paidSections": ["Every panchang check on the day, pass or fail",
                             "The strong hours — choghadiya, Abhijit, and what to avoid",
                             "Chart-specific notes for this occasion",
                             f"{n_alt} better dates near yours"],
            "teasers": {}}
    return free, paid_html, meta
