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
    if "<style" not in html and "<script" not in html:
        return scrub(html)

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


def _scrub_workings(html: str) -> str:
    """Horary paid appendix embeds ship full engine HTML — scrub jargon first."""
    if not html:
        return html
    try:
        from astro_voice import strip_leaks, strip_machinery
        out = strip_leaks(strip_machinery(html))
    except Exception:                                                # noqa: BLE001
        out = html
    import re as _re
    for pat, rep in (
        (r"<strong>Method:</strong>[^<]*deterministic[^<]*<br\s*/?>",
         "<strong>Method:</strong> Traditional Western horary (Tropical), "
         "Anthony Louis / Lilly-style.<br />"),
        (r"deterministic engine[^<.]*", "classical horary rules"),
        (r"deterministic rule engine\b", "classical rules"),
        (r"§\s*2b\s+checklist[^<.]*", "the standard horary checklist"),
        (r"<code>western_horary[^<]*</code>", ""),
        (r"Computed with Python pyswisseph[^<.]*",
         "Computed with standard ephemeris data"),
    ):
        out = _re.sub(pat, rep, out, flags=_re.I | _re.S)
    return _scrub(out)


# ---------------------------------------------------------------------------
# the flagship
# ---------------------------------------------------------------------------
def full_report(pc: dict, *, name: str = "", question: str = "",
                today: Optional[date] = None, price: int = 1499,
                bundle_price: int = 2100, lat: float = 0.0, lon: float = 0.0,
                tz: float = 5.5, daily: Any = None) -> tuple:
    """Present read, who you are, your past, the cards, timing, remedies.

    Order is deliberate and it is the commercial argument as much as the
    editorial one: the reader meets a claim about the six months they have just
    lived BEFORE anything is asked of them. If that lands, everything after it
    is credible; if it does not, they should close the page.
    """
    today = today or date.today()
    first = (name or "").split()[0] if name else ""

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
    try:
        import report_cards as RC
        import report_timing as RT
        areas = [(a.key, a.house) for a in RC.AREAS]
        labels = {a.key: a.label for a in RC.AREAS}
        timing_html = RT.render(pc, RT.best_windows(pc, areas, years=5, limit=4),
                                labels)
    except Exception as exc:                                         # noqa: BLE001
        print(f"[report_render] timing failed: {exc}", flush=True)

    q_html = ""
    if question:
        try:
            import question_answer as QA
            q_html = QA.render(QA.answer(pc, question, years=7), name=first,
                               paid=False)
        except Exception as exc:                                     # noqa: BLE001
            print(f"[report_render] question failed: {exc}", flush=True)

    def build(paid: bool) -> str:
        import report_cards as RC
        remedy = _safe(_remedy, pc, name=first, paid=paid, price=price)
        qh = q_html
        if question and paid:
            try:
                import question_answer as QA
                qh = QA.render(QA.answer(pc, question, years=7), name=first,
                               paid=True)
            except Exception:                                        # noqa: BLE001
                pass
        body = RC.render(
            pc, name=name, price=price, today=today, paid=paid,
            question_html=qh,
            proof_html=present_html + past_html,
            timing_html=timing_html + remedy
                        + ("" if paid else _bundle(bundle_price)))
        return _scrub(body)

    free_html, paid_html = build(False), build(True)
    meta = {
        "design": "cards-v2",
        "price": price, "bundlePrice": bundle_price,
        "freeSections": ["Where you are right now", "Who your chart says you are",
                         "Your past", "Every life area", "The period sequence"],
        "paidSections": ["Exact dates for every life area",
                         "What helps, per area", "Remedies and gemstones",
                         "The five-year window list"],
        "teasers": {},
    }
    return free_html, paid_html, meta


def _remedy(pc: dict, *, name: str = "", paid: bool = False,
            price: int = 1499) -> str:
    import remedy_block as RB
    return RB.render(
        RB.build(pc, domain="", name=name), paid=paid, price=price,
        lede="Your chart's difficult places all have a classical answer. Some of "
             "them say do NOT wear the obvious stone — that half is free, "
             "because nobody else will tell you.")


def _bundle(bundle_price: int) -> str:
    """Shown only in the free view. In the paid view it is already bought."""
    return f"""
<section class="card" style="background:#16181d;color:#f7f5f1;border:0">
  <div class="ev-label" style="color:#c9a227">Everything, one price</div>
  <h3 style="font-family:Fraunces,serif;font-size:1.3rem;margin:8px 0 8px">
    Unlock the whole thing — ₹{bundle_price:,}</h3>
  <p style="margin:0 0 10px;font-size:.9rem;opacity:.85">Bought separately these
  come to ₹4,544. The bundle is every reading on this page, one payment, kept
  for good — the full chart reading, birth-time rectification, matching, the
  palm reading, numerology, your questions, daily readings for a year, event
  timing and every remedy.</p>
  <p style="margin:0;font-size:.78rem;opacity:.6">If your birth time is
  uncertain, spend on rectification first — every other reading is built on
  it.</p>
</section>"""


# ---------------------------------------------------------------------------
# horary — one answer, not two engines arguing
# ---------------------------------------------------------------------------
def horary(*, question: str, verdicts: dict, western_judgment: dict,
           asked: str, name: str = "", price: int = 99,
           workings: Optional[dict] = None) -> tuple:
    from horary_answer import build_answer_html
    answer_html, answer = build_answer_html(
        question=question, verdicts=verdicts,
        western_judgment=western_judgment, asked=asked, name=name,
        full_report_price=price)

    workings = workings or {}
    detail = ""
    for tag in ("western", "vedic"):
        raw = workings.get(tag) or ""
        if raw:
            detail += (f'<h3 class="sec">{tag.title()} working</h3>'
                       f'<div class="card">{_scrub_workings(raw)}</div>')

    # No shell heading: build_answer_html already opens with the question and
    # when it was asked. Passing them again printed the question twice.
    free = RS.page(f"Your question — {question[:60]}", _scrub(answer_html))
    paid = RS.page(f"Your question — {question[:60]}",
                   _scrub(answer_html + detail))
    meta = {"design": "cards-v2", "answer": answer, "question": question,
            "asked": asked, "price": price,
            "paidSections": ["The full planetary working, both methods"],
            "teasers": {}}
    return free, paid, meta


# ---------------------------------------------------------------------------
# numerology — six numbers, the Lo Shu grid, this year free, the rest locked
# ---------------------------------------------------------------------------
def _as_date(v) -> date:
    """Handlers pass dob as an ISO string; the numerology maths needs a date."""
    if isinstance(v, date):
        return v
    y, m, d = (int(x) for x in str(v)[:10].split("-"))
    return date(y, m, d)


def numerology(name: str, dob, *, today: Optional[date] = None,
               price: int = 199) -> tuple:
    import tab_renderers as TR
    dob = _as_date(dob)

    def build(paid: bool) -> str:
        body = TR.render_numerology(name, dob, paid=paid, price=price,
                                    today=today or date.today())
        # render_numerology prints its own header block.
        return _scrub(RS.page(f"{name} — your numbers", body))

    free, paid = build(False), build(True)
    meta = {"design": "cards-v2", "price": price,
            "paidSections": ["The next three years of your numerology cycle",
                             "What to do about each empty Lo Shu cell"],
            "teasers": {}}
    return free, paid, meta


# ---------------------------------------------------------------------------
# kundali matching
# ---------------------------------------------------------------------------
def kundali_match(match_meta: dict, *, groom: str = "", bride: str = "",
                  price: int = 299) -> tuple:
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
# daily — headline, do/don't, hora windows (subscription-gated, not section-paywalled)
# ---------------------------------------------------------------------------
def daily(reading: dict, *, lat: float = 25.6, lon: float = 85.1,
          tz: float = 5.5, day: Optional[date] = None, name: str = "",
          price: int = 199) -> tuple:
    import daily_card as DC
    day = day or date.today()
    card = DC.build(reading or {}, lat=lat, lon=lon, tz=tz, day=day)
    body = DC.render(card)
    who = (name or "").split()[0] if name else "Your"
    html = _scrub(RS.page(f"{who} — today", body,
                          eyebrow="Daily reading",
                          heading=f"{day:%A %d %B}",
                          sub="Built from your Moon, rising sign and today's star."))
    # Same document on both halves: access is subscription/quota, not a blur.
    meta = {"design": "cards-v2", "price": price, "date": day.isoformat(),
            "paidSections": ["Personalised reading every morning",
                             "3 horary questions a month",
                             "Unlimited muhurat checks"],
            "teasers": {}}
    return html, html, meta


# ---------------------------------------------------------------------------
# birth-time check
# ---------------------------------------------------------------------------
def btr(res: dict, *, price: int = 999) -> tuple:
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
            price: int = 49, event_id: str = "", date_str: str = "") -> tuple:
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
