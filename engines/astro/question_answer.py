"""Answering "when will X happen?" from the birth chart.

This is the highest-value question the product gets asked, and it is a
different problem from horary. Horary reads the moment of asking and returns
yes or no. A natal timing question has to return a **date range**, which means
it needs everything at once:

    the promise    does the chart offer this at all, and how strongly
    the period     which dasha owns it — checked in all three systems
    the trigger    is a slow planet crossing the relevant house
    the strength   does that transit carry the Ashtakavarga points to deliver

The discipline that matters here is refusing to answer when the chart does not
support one. "Sometime in the next ten years" is not an answer, and inventing a
date to seem confident is how this category earned its reputation. So a window
is only offered when promise, period and trigger coincide; otherwise the reader
is told plainly that the chart shows no clear window in the horizon, and what
that actually means.

Question → chart mapping is explicit rather than clever. A job change is not
just the 10th house: leaving is the 3rd and 12th, arriving is the 10th and 11th,
and the work itself is the 6th. Reading only the 10th is the usual mistake.
"""

from __future__ import annotations

import html as _html
import re
from datetime import date, timedelta
from typing import Any, Optional


class Topic:
    """One kind of question, and the parts of the chart that answer it."""

    def __init__(self, key: str, label: str, subject: str, houses: tuple,
                 significators: tuple, patterns: tuple, note: str = ""):
        self.key = key
        self.label = label
        self.subject = subject
        self.houses = houses            # (primary, *supporting)
        self.significators = significators
        self.patterns = patterns
        self.note = note


TOPICS = (
    Topic("job_change", "A change of job", "a job change",
          houses=(10, 6, 3, 11),
          significators=("Saturn", "Sun", "Mercury"),
          patterns=(r"\bjob\b.*\bchange\b", r"\bchange\b.*\bjob\b",
                    r"\bnew job\b", r"\bswitch\b.*\b(job|company|role)\b",
                    r"\bresign", r"\bquit\b.*\bjob\b", r"\bnaukri\b"),
          note="Leaving is read from the 3rd and 12th, arriving from the 10th "
               "and 11th, and the work itself from the 6th. A change needs "
               "movement in both halves, not just a strong 10th."),
    Topic("promotion", "Promotion or a step up", "a promotion",
          houses=(10, 11, 1),
          significators=("Sun", "Jupiter", "Saturn"),
          patterns=(r"\bpromot", r"\bsenior", r"\braise\b", r"\bincrement\b")),
    Topic("business", "Starting on your own", "starting your own work",
          houses=(7, 10, 11),
          significators=("Mercury", "Rahu", "Jupiter"),
          patterns=(r"\bbusiness\b", r"\bstartup\b", r"\bown\b.*\bwork\b",
                    r"\bventure\b")),
    Topic("money", "A real rise in income", "a rise in income",
          houses=(2, 11, 9),
          significators=("Jupiter", "Venus", "Mercury"),
          patterns=(r"\bmoney\b", r"\bincome\b", r"\bsalary\b", r"\bwealth\b",
                    r"\brich\b", r"\bfinancial", r"\bpaisa\b")),
    Topic("property", "Property or a home", "buying property",
          houses=(4, 2, 11),
          significators=("Mars", "Venus", "Saturn"),
          patterns=(r"\bhouse\b", r"\bproperty\b", r"\bflat\b", r"\bland\b",
                    r"\bhome loan\b")),
    Topic("foreign", "Going abroad", "a move abroad",
          houses=(12, 9, 3),
          significators=("Rahu", "Moon", "Jupiter"),
          patterns=(r"\babroad\b", r"\bforeign\b", r"\bvisa\b", r"\bonsite\b",
                    r"\brelocat", r"\bsettle\b.*\b(us|uk|canada|australia)\b")),
    Topic("study", "Study or a qualification", "further study",
          houses=(9, 5, 4),
          significators=("Jupiter", "Mercury"),
          patterns=(r"\bstudy\b", r"\bexam\b", r"\bmba\b", r"\bcourse\b",
                    r"\bdegree\b", r"\badmission\b")),
    Topic("health", "Health recovery", "your health improving",
          houses=(1, 6, 8),
          significators=("Sun", "Jupiter", "Mars"),
          patterns=(r"\bhealth\b", r"\billness\b", r"\brecover", r"\bsurgery\b",
                    r"\bdisease\b")),
)

FALLBACK = Topic("general", "Your question", "what you asked about",
                 houses=(1, 10, 11), significators=("Jupiter", "Saturn"),
                 patterns=())


def classify(question: str) -> Topic:
    q = re.sub(r"\s+", " ", (question or "").lower())
    for topic in TOPICS:
        for pat in topic.patterns:
            if re.search(pat, q):
                return topic
    return FALLBACK


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def _pretty(d: Optional[date]) -> str:
    return f"{d:%B %Y}" if d else ""


def _ord(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    return f"{n}" + ("th" if 10 <= n % 100 <= 20
                     else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


# ---------------------------------------------------------------------------

def answer(pc: dict, question: str, *, start: Optional[date] = None,
           years: int = 7) -> dict:
    """Find the windows where this specific thing can actually happen."""
    start = start or date.today()
    topic = classify(question)
    import report_confluence as CF
    import report_timing as RT

    primary = topic.houses[0]
    promise = CF.area_verdict(pc, _area_for(primary), primary)

    hl = pc.get("house_lords", {}) or {}
    planets = pc.get("planets", {}) or {}
    owners = {(hl.get(str(h)) or {}).get("lord") for h in topic.houses}
    owners.discard(None)
    keys = owners | set(topic.significators)

    segments = RT.transit_segments(pc, start=start, years=years)

    windows = []
    for planet, segs in segments.items():
        for seg in segs:
            if seg.get("house") not in topic.houses:
                continue
            when = max(seg.get("start"), start)
            if when > start + timedelta(days=365 * years):
                continue
            dasha = CF.dasha_confluence(pc, when)
            vim = CF.vimshottari_at(pc, when)
            yog = (CF.yogini_at(pc, when) or {}).get("lord", "")
            running = [x for x in (vim.get("md"), vim.get("ad"), yog) if x]
            # does the period itself own this question?
            period_hits = sorted({p for p in running if p in keys})
            bav = seg.get("bav", 0)

            score = (0.9 * len(period_hits)
                     + (1.2 if bav >= 5 else (-1.0 if bav <= 3 else 0))
                     + (0.8 if seg["house"] == primary else 0.3)
                     + 0.5 * promise["score"]
                     + (0.6 if dasha["direction"] == "up" else
                        -0.6 if dasha["direction"] == "down" else 0))
            windows.append({
                "start": when, "end": seg.get("end"),
                "planet": planet, "sign": seg.get("sign"), "house": seg["house"],
                "bav": bav, "period": f"{vim.get('md','')}–{vim.get('ad','')}",
                "yogini": yog, "period_hits": period_hits,
                "dasha_dir": dasha["direction"],
                "dasha_label": " · ".join(r["label"] for r in dasha["readings"]),
                "score": round(score, 2),
                "strong": bool(period_hits) and bav >= 5,
            })

    windows.sort(key=lambda w: -w["score"])
    best = windows[0] if windows else None

    # Someone asking "when" wants two different things and the strongest
    # window answers only one of them. On the test chart the best window is
    # three and a half years out — true, and useless to a person who wants to
    # move this year. So the nearest usable window is reported alongside it,
    # and if they are the same window that is stated rather than duplicated.
    soon = sorted((w for w in windows if w["score"] > 0),
                  key=lambda w: w["start"])
    nearest = soon[0] if soon else None
    if nearest and best and nearest["start"] == best["start"]:
        nearest = None

    # Lines for the free view: which planet owns each house of the question,
    # where it sits, in what condition. Facts, no conclusion drawn.
    chart_lines = []
    for h in topic.houses:
        info = hl.get(str(h)) or {}
        lord = info.get("lord", "")
        if not lord:
            continue
        dig = str(info.get("lord_dignity") or "").replace("_", " ")
        sits = info.get("lord_house")
        detail = dig
        if sits:
            detail += ", placed in your " + _ord(sits)
        if lord in topic.significators:
            detail += "; also a classical significator for this question"
        chart_lines.append((_ord(h) + " house — " + lord, detail))

    vim_now = CF.vimshottari_at(pc, start)
    yog_now = (CF.yogini_at(pc, start) or {}).get("lord", "")
    now_label = f"{vim_now.get('md','')}-{vim_now.get('ad','')}" + (
        f", lunar cycle on {yog_now}" if yog_now else "")

    strong = [w for w in windows if w["strong"]]
    return {"topic": topic, "question": question, "promise": promise,
            "chart_lines": chart_lines, "now_label": now_label,
            "windows": windows, "best": best, "nearest": nearest,
            "strong_count": len(strong), "horizon": years,
            "start": start}


def _area_for(house: int) -> str:
    return {10: "career", 2: "money", 7: "love", 4: "home", 5: "children",
            1: "health", 9: "learning", 12: "inner", 6: "health",
            3: "career", 11: "money", 8: "health"}.get(house, "career")


# ---------------------------------------------------------------------------

def render_free(result: dict, *, name: str = "", price: int = 1499) -> str:
    """The free view: the chart's working, with the verdict withheld.

    Operator's call, and commercially it is the right one — if the answer is
    free, nobody buys the reading. What keeps it from being a bait-and-switch is
    that the free half is genuinely substantial: the reader sees which planets
    rule the question, where they sit and in what condition, which periods are
    running, and what is crossing those houses today with what strength.
    Everything except the conclusion those facts point to.
    """
    topic = result["topic"]
    who = (name or "").split()[0] if name else ""
    windows = result["windows"]

    rows = "".join(
        "<li><b>{}</b> — {}</li>".format(_e(a), _e(b))
        for a, b in (result.get("chart_lines") or []))

    live = [w for w in windows if w["start"] <= result["start"]]
    transit_rows = "".join(
        "<li><b>{}</b> is crossing your {} house from {} right now, carrying "
        "<b>{} of 8</b> classical support points there.</li>".format(
            _e(w["planet"]), _ord(w["house"]), _e(w["sign"]), w["bav"])
        for w in live[:2])

    transit_block = ""
    if transit_rows:
        transit_block = (
            '<div class="evidence"><span class="ev-label">What is crossing '
            'those houses today</span><ul class="qa-why">'
            + transit_rows + "</ul></div>")

    return """
<section class="qa">
  <div class="qa-asked"><b>You asked:</b> {question}</div>
  <p class="qa-lede">{who}here is exactly what your chart is doing on this
  question. The dates and the answer are in the paid reading — everything below
  is the working, so you can see this is your chart being read and not a
  template.</p>

  <div class="qa-promise">
    <b>{label}</b> is read from your {houses} houses. {note}
  </div>

  <div class="evidence">
    <span class="ev-label">The planets that govern your question</span>
    <ul class="qa-why">{rows}</ul>
  </div>

  {transit_block}

  <div class="evidence">
    <span class="ev-label">Periods running right now</span>
    <ul class="qa-why">
      <li>{now_label}</li>
      <li>{agreement} on whether your chart favours this at all.</li>
    </ul>
  </div>

  <div class="qa-window locked">
    <div class="qa-wlabel">The answer itself</div>
    <p class="blurred">Yes — the strongest window falls between XXXXXXX XXXX and
    XXXXXXX XXXX, with a nearer partial window before it, because XXXXXXX
    crosses your XXth at N of 8 while the XXXXXXX period runs.</p>
    <p><b>{n} windows were found and scored across the next {horizon}
    years.</b> The unlock gives you every date, which of them your chart
    actually backs, and what to do inside each one — ₹{price}.</p>
  </div>
</section>""".format(
        question=_e(result["question"]),
        who=_e(who + ", ") if who else "",
        label=_e(topic.label),
        houses=_e(", ".join(_ord(h) for h in topic.houses)),
        note=_e(topic.note),
        rows=rows,
        transit_block=transit_block,
        now_label=_e(result.get("now_label", "")),
        agreement=_e(result["promise"]["agreement"]),
        n=len(windows), horizon=result["horizon"], price=price)


def render(result: dict, *, name: str = "", paid: bool = False,
           price: int = 1499) -> str:
    if not paid:
        return render_free(result, name=name, price=price)
    topic, best = result["topic"], result["best"]
    nearest = result.get("nearest")
    who = (name or "").split()[0] if name else ""
    promise = result["promise"]

    if not best:
        # Refusing is a real answer. Inventing a date is how this category
        # earned its reputation.
        return f"""
<section class="qa">
  <div class="qa-asked"><b>You asked:</b> {_e(result['question'])}</div>
  <h2 class="qa-verdict">Your chart does not show a clear window for
  {_e(topic.subject)} in the next {result['horizon']} years.</h2>
  <p>That is a real finding, not a dodge. The houses that govern this
  ({', '.join(_ord(h) for h in topic.houses)}) get no strong planetary trigger
  in that time. Anyone who gives you a date from this chart is guessing.</p>
</section>"""

    lead = ("Yes — and the chart is specific about when."
            if best["strong"] else
            "Yes, but the timing is narrower than you would like.")
    if promise["direction"] == "down" and not best["strong"]:
        lead = ("This is possible but your chart does not favour it. "
                "The window below is the best of a weak set.")

    def window_block(w: dict, label: str) -> str:
        hits = (", ".join(w["period_hits"]) if w["period_hits"]
                else "no period lord for this question")
        return f"""
  <div class="qa-window {'strong' if w['strong'] else 'weak'}">
    <div class="qa-wlabel">{_e(label)}</div>
    <div class="qa-when">{_e(_pretty(w['start']))} → {_e(_pretty(w['end']))}</div>
    <ul class="qa-why">
      <li><b>Period</b> — {_e(w['period'])}
        {f", with the lunar cycle on {_e(w['yogini'])}" if w['yogini'] else ""}.
        Active for this question: {_e(hits)}.</li>
      <li><b>Trigger</b> — {_e(w['planet'])} transits your
        {_ord(w['house'])} house from {_e(w['sign'])}, carrying
        <b>{w['bav']} of 8</b> support points
        {'— enough to actually deliver' if w['bav'] >= 5
         else '— thin, so expect an opening rather than a result'}.</li>
      <li><b>Agreement</b> — {_e(w['dasha_label'])}</li>
    </ul>
  </div>"""

    blocks = ""
    if nearest and nearest["start"] < best["start"]:
        blocks += window_block(nearest, "Soonest possible window")
    blocks += window_block(best, "Strongest window")
    if nearest and nearest["start"] > best["start"]:
        blocks += window_block(nearest, "Next window after that")

    later = [w for w in result["windows"][1:6]
             if w is not nearest
             and abs((w["start"] - best["start"]).days) > 200]
    if later and not paid:
        blocks += f"""
  <div class="qa-window locked">
    <div class="qa-wlabel">{len(later)} further windows</div>
    <p class="blurred">Additional windows fall inside the horizon, each with its
    own period, trigger and support score.</p>
  </div>"""
    elif later:
        blocks += "".join(window_block(w, "Also worth noting")
                          for w in later[:2])

    months_out = max(0, (best["start"] - result["start"]).days // 30)
    gap_note = ""
    if months_out >= 24:
        gap_note = (
            f'<p class="qa-gap"><b>That is {months_out // 12} years out, so here '
            f'is the honest near-term read.</b> Nothing in your chart blocks you '
            f'from moving before then — it simply will not have the wind behind '
            f'it. If you move sooner, treat it as a decision you are making '
            f'rather than a door opening, and expect to do more of the pushing '
            f'yourself.</p>')

    upsell = "" if paid else f"""
  <div class="qa-cta">
    <p>The full reading dates every window across the next
    {result['horizon']} years for this and the other eight areas of your life,
    with what to do in each — ₹{price}.</p>
  </div>"""

    return f"""
<section class="qa">
  <div class="qa-asked"><b>You asked:</b> {_e(result['question'])}</div>
  <p class="qa-lede">{_e(who + ', ' if who else '')}here is the straight answer,
  then the chart behind it.</p>
  <h2 class="qa-verdict">{_e(lead)}</h2>
  <p class="qa-promise"><b>Does your chart even offer this?</b>
  {_e(topic.label)} reads <b>{_e(promise['direction'])}</b> in your chart —
  {_e(promise['agreement'])}. {_e(topic.note)}</p>
  {blocks}
  {gap_note}
  <p class="qa-caveat">Timing is a window, not a date. What the chart says is
  <em>when the conditions are right</em> — you still have to apply, ask, and
  move inside it.</p>
  {upsell}
</section>"""
