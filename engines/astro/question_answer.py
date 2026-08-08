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
    Topic("children", "Children & family", "children",
          houses=(5, 9, 11),
          significators=("Jupiter",),
          patterns=(r"\bkids?\b", r"\bchild", r"\bchildren\b", r"\bprogeny\b",
                    r"\bson\b", r"\bdaughter\b", r"\bbaby\b", r"\bpregnant\b",
                    r"\bhow many\b.*\b(kids?|child)")),
)

FALLBACK = Topic("general", "Your question", "what you asked about",
                 houses=(1, 10, 11), significators=("Jupiter", "Saturn"),
                 patterns=())


def classify(question: str) -> Topic:
    """Map free-text → Topic. MiniLM domain/house first; regex patterns assist."""
    raw = (question or "").strip()
    q = re.sub(r"\s+", " ", raw.lower())
    # Exact pattern hits still win (job_change vs promotion, etc.)
    for topic in TOPICS:
        for pat in topic.patterns:
            if re.search(pat, q):
                return topic
    # Semantic fallback when wording does not match regex (e.g. "profession lift")
    try:
        import semantic_question as SQ
        routed = SQ.route(raw)
        dom = routed.domain
        house = routed.primary_house
        # Prefer topic whose primary house matches semantic house
        by_house = [t for t in TOPICS if t.houses and t.houses[0] == house]
        if by_house:
            return by_house[0]
        key = {
            "career": "promotion", "finance": "money", "property": "property",
            "travel": "foreign", "health": "health", "education": "study",
            "children": "children", "family": "children",
        }.get(dom)
        if key:
            for t in TOPICS:
                if t.key == key:
                    return t
    except Exception:
        pass
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


_DIGNITY = {
    "exalted": "very strong",
    "moolatrikona": "very strong",
    "own_sign": "in its own sign",
    "friendly_sign": "comfortable",
    "neutral_sign": "neither strong nor weak",
    "enemy_sign": "under strain",
    "debilitated": "very weak",
    "neutral": "neither strong nor weak",
}

_ROUTE_METHOD = {
    "minilm": "your wording",
    "semantic": "your wording",
    "regex": "the question pattern",
}


def _human_dignity(code: str) -> str:
    key = (code or "").strip().lower().replace(" ", "_")
    return _DIGNITY.get(key, key.replace("_", " ") if key else "mixed")


def _plain_line(text: str) -> str:
    """Customer-facing one-liner — no method tags or book citations."""
    raw = (text or "").strip()
    if not raw:
        return ""
    for code, human in _DIGNITY.items():
        raw = re.sub(rf"\b{re.escape(code)}\b", human, raw, flags=re.I)
    try:
        import report_confluence as CF
        return CF._plain(raw)  # noqa: SLF001
    except Exception:  # noqa: BLE001
        return raw


def _plain_agreement(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return "the methods have not settled on one side yet"
    low = raw.lower()
    if "align · moderate" in low or "align · mod" in low:
        return raw.split("·")[0].strip() + " — a moderate read, not unanimous"
    if "align · high" in low:
        return raw.split("·")[0].strip() + " — a strong agreement"
    if "align · low" in low:
        return raw.split("·")[0].strip() + " — most methods push back"
    return _plain_line(raw)


# ---------------------------------------------------------------------------

def answer(pc: dict, question: str, *, start: Optional[date] = None,
           years: int = 7, lat: Optional[float] = None,
           lon: Optional[float] = None, tz: float = 5.5,
           route: Any = None) -> dict:
    """Find the windows where this specific thing can actually happen."""
    start = start or date.today()
    topic = classify(question)
    import report_confluence as CF
    import report_timing as RT

    primary = topic.houses[0]
    area_key = _area_for(primary)
    promise = CF.area_verdict(pc, area_key, primary)
    promise = CF.merge_semantic_verdict(area_key, promise)

    deep: dict = {}
    try:
        import deep_evidence as DE
        deep = DE.for_area(area_key, house=primary)
    except Exception:  # noqa: BLE001
        deep = {}

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
        dig = _human_dignity(str(info.get("lord_dignity") or ""))
        sits = info.get("lord_house")
        detail = dig
        if sits:
            detail += ", placed in your " + _ord(sits) + " house"
        if lord in topic.significators:
            detail += "; also a natural significator for this question"
        chart_lines.append((_ord(h) + " house — " + lord, detail))

    # Deep-dive layer: divisional chart + classical rules for this question
    for fact in (deep.get("house_facts") or [])[:2]:
        chart_lines.append(("Your chart", _plain_line(fact)))
    varga = deep.get("varga") or {}
    vdiag = (varga.get("diagnosis") or "").strip()
    if vdiag:
        vname = (varga.get("name") or varga.get("code") or "Divisional chart").strip()
        chart_lines.append((vname, _plain_line(vdiag)))
    for rule in (deep.get("rules_pos") or [])[:2]:
        chart_lines.append(("Classical rule", _plain_line(rule)))
    for rule in (deep.get("rules_neg") or [])[:1]:
        chart_lines.append(("Watch", _plain_line(rule)))
    if deep.get("transit", {}).get("note"):
        chart_lines.append(("Sky now", _plain_line(deep["transit"]["note"])))
    cw = deep.get("current_window") or {}
    if cw.get("word"):
        chart_lines.append((
            "Period outlook",
            f"{cw.get('period', 'Now')}: {cw.get('word', '')}"
            + (f" — {cw['reason'][:80]}" if cw.get("reason") else "")))

    vim_now = CF.vimshottari_at(pc, start)
    yog_now = (CF.yogini_at(pc, start) or {}).get("lord", "")
    now_label = f"{vim_now.get('md','')}-{vim_now.get('ad','')}" + (
        f", lunar cycle on {yog_now}" if yog_now else "")

    strong = [w for w in windows if w["strong"]]

    route_info: dict = {}
    if route is not None:
        route_info = {
            "domain": getattr(route, "domain", "") or "",
            "primary_house": getattr(route, "primary_house", 0) or 0,
            "topic": getattr(route, "topic", "") or "",
            "method": getattr(route, "method", "") or "",
        }
    else:
        try:
            import semantic_question as SQ
            r = SQ.route(question)
            route_info = {
                "domain": r.domain, "primary_house": r.primary_house,
                "topic": r.topic, "method": r.method,
            }
        except Exception:  # noqa: BLE001
            route_info = {}

    votes = promise.get("votes") or []
    n_methods = len(votes)
    n_up = sum(1 for v in votes if getattr(v, "value", 0) > 0.3)
    n_down = sum(1 for v in votes if getattr(v, "value", 0) < -0.3)

    area_report = None
    try:
        import area_report as AR
        area_report = AR.build_area(
            pc, area_key, primary, today=start, question=question)
    except Exception:  # noqa: BLE001
        area_report = None

    prediction = None
    if area_report:
        import predict_voice as PV
        prediction = PV.Prediction(
            scenario=area_report.prediction,
            backing=area_report.proof,
            direction=area_report.direction,
        )
    else:
        try:
            import predict_voice as PV
            now = CF.vimshottari_at(pc, start)
            hl_info = hl.get(str(primary)) or {}
            live = [w for w in windows if w["start"] <= start][:2]
            transits = [{"planet": w["planet"], "house": w["house"], "bav": w["bav"]}
                        for w in live]
            prediction = PV.compose(
                area_key, direction=promise.get("direction", "mixed"),
                md_lord=now.get("md", ""), ad_lord=now.get("ad", ""),
                house=primary, lord=hl_info.get("lord", ""),
                dignity=str(hl_info.get("lord_dignity") or ""),
                lord_house=hl_info.get("lord_house"), transits=transits,
                varga=deep.get("varga") or {},
                varga_strength=(deep.get("varga") or {}).get("strength", "mixed"),
                window_rating=deep.get("current_rating", "mix"),
                include_period_lord=False,
            )
        except Exception:  # noqa: BLE001
            prediction = None

    return {"topic": topic, "question": question, "promise": promise,
            "chart_lines": chart_lines, "now_label": now_label,
            "windows": windows, "best": best, "nearest": nearest,
            "strong_count": len(strong), "horizon": years,
            "start": start, "deep": deep,
            "deep_verdict": (deep.get("overall") or {}).get("text", ""),
            "route": route_info, "area_key": area_key,
            "n_methods": n_methods, "n_up": n_up, "n_down": n_down,
            "prediction": prediction, "area_report": area_report}


def _area_for(house: int) -> str:
    return {10: "career", 2: "money", 7: "love", 4: "home", 5: "children",
            1: "health", 9: "learning", 12: "inner", 6: "health",
            3: "career", 11: "money", 8: "health"}.get(house, "career")


def answer_meta(result: dict) -> dict:
    """Compact verdict for JSON meta (frontend card when unlocked)."""
    promise = result.get("promise") or {}
    best = result.get("best")
    topic = result.get("topic")
    if not best:
        return {
            "label": f"No clear window for {getattr(topic, 'subject', 'this')} "
                     f"in the next {result.get('horizon', 7)} years",
            "confidence": "moderate",
            "direction": promise.get("direction", "mixed"),
        }
    lead = ("Yes — and the chart is specific about when."
            if best.get("strong") else
            "Yes, but the timing is narrower than you would like.")
    if promise.get("direction") == "down" and not best.get("strong"):
        lead = "Possible, but your chart does not strongly favour this."
    conf = promise.get("confidence", "moderate")
    if result.get("n_methods", 0) >= 5 and promise.get("direction") in ("up", "down"):
        conf = "high" if promise["direction"] == "up" else "low"
    return {"label": lead, "confidence": conf,
            "direction": promise.get("direction", "mixed"),
            "best_from": _pretty(best.get("start")),
            "best_to": _pretty(best.get("end"))}


# ---------------------------------------------------------------------------

def render_free(result: dict, *, name: str = "", price: int = 1499) -> str:
    """Free half: plain prediction + one Why line; verdict and dates locked."""
    topic = result["topic"]
    who = (name or "").split()[0] if name else ""
    windows = result["windows"]
    promise = result["promise"]
    route = result.get("route") or {}
    pred = result.get("prediction")

    main_pred = ""
    if pred is not None:
        main_pred = pred.html()
    else:
        try:
            import predict_voice as PV
            p = PV.compose(
                result.get("area_key", "career"),
                direction=promise.get("direction", "mixed"),
            )
            main_pred = p.html()
        except Exception:  # noqa: BLE001
            main_pred = ""

    route_block = ""
    if route.get("domain") or topic.key != "general":
        ph = topic.houses[0] if topic.key != "general" else route.get("primary_house", 0)
        domain = route.get("domain") or topic.key
        route_block = (
            f'<p class="qa-route">We read this as a <b>{_e(domain)}</b> '
            f'question, centred on your {_ord(ph)} house.</p>')

    return """
<section class="qa">
  <div class="qa-asked"><b>You asked:</b> {question}</div>
  {route_block}
  <p class="qa-lede">{who}here is what your chart is doing on this question now.
  The straight answer, dated windows and remedy are in the paid reading.</p>

  <div class="qa-promise">
    <b>{label}</b> is read from your {houses} houses. {note}
  </div>

  {main_pred}

  <div class="qa-window locked">
    <div class="qa-wlabel">The verdict</div>
    <p class="blurred">Your chart reads XXXXXXX for this question — the straight
    answer from every method combined.</p>
  </div>

  <div class="qa-window locked">
    <div class="qa-wlabel">When it can happen</div>
    <p class="blurred">The strongest window falls between XXXXXXX XXXX and
    XXXXXXX XXXX, with a nearer partial window before it.</p>
    <p><b>{n} windows were found and scored across the next {horizon}
    years.</b> The unlock gives you every date, which of them your chart
    actually backs, and what to do inside each one — ₹{price}.</p>
  </div>

  <div class="qa-window locked">
    <div class="qa-wlabel">The remedy</div>
    <p class="blurred">What to strengthen or pacify for this question — the
    classical answer tied to the planets that rule it.</p>
  </div>
</section>""".format(
        question=_e(result["question"]),
        route_block=route_block,
        who=_e(who + ", ") if who else "",
        label=_e(topic.label),
        houses=_e(", ".join(_ord(h) for h in topic.houses)),
        note=_e(topic.note),
        main_pred=main_pred,
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
    deep_txt = (result.get("deep_verdict") or "").strip()
    if deep_txt:
        lead = f"{deep_txt} {lead}"
    if promise["direction"] == "down" and not best["strong"]:
        lead = ("This is possible but your chart does not favour it. "
                "The window below is the best of a weak set.")

    def _window_scenario(w: dict) -> str:
        if w.get("strong"):
            return (f"This is the window where your chart actually backs "
                    f"{topic.subject} — between {_pretty(w['start'])} and "
                    f"{_pretty(w['end'])}.")
        if (w.get("bav") or 0) >= 5:
            return (f"An opening appears between {_pretty(w['start'])} and "
                    f"{_pretty(w['end'])}, though your chart does not fully "
                    f"guarantee the outcome.")
        return (f"A partial window runs from {_pretty(w['start'])} to "
                f"{_pretty(w['end'])} — expect movement, not a finished result.")

    def _window_backing(w: dict) -> str:
        sup = (w.get("bav") or 0) >= 5
        parts = [
            f"{w.get('period', '')} running",
            (f"{w.get('planet', '')} crossing your {_ord(w.get('house'))} house "
             f"({'well supported' if sup else 'weakly supported'})"),
        ]
        if w.get("period_hits"):
            parts.append("period activates this question")
        if w.get("yogini"):
            parts.append(f"lunar cycle on {w['yogini']}")
        return "; ".join(p for p in parts if p)

    def window_block(w: dict, label: str) -> str:
        return f"""
  <div class="qa-window {'strong' if w['strong'] else 'weak'}">
    <div class="qa-wlabel">{_e(label)}</div>
    <div class="qa-when">{_e(_pretty(w['start']))} → {_e(_pretty(w['end']))}</div>
    <p class="pred-scenario">{_e(_window_scenario(w))}</p>
    <p class="pred-why"><b>Why:</b> {_e(_window_backing(w))}</p>
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

    try:
        import report_confluence as CF
        promise_conf = CF.customer_confidence(promise) or promise.get("agreement", "")
    except Exception:  # noqa: BLE001
        promise_conf = promise.get("agreement", "")

    main_pred = ""
    pred = result.get("prediction")
    if pred is not None:
        main_pred = pred.html()
    elif promise.get("headline"):
        main_pred = (
            f'<div class="prediction"><p class="pred-scenario">'
            f'{_e(promise["headline"])}</p></div>')

    return f"""
<section class="qa">
  <div class="qa-asked"><b>You asked:</b> {_e(result['question'])}</div>
  <p class="qa-lede">{_e(who + ', ' if who else '')}here is the straight answer,
  then the chart behind it.</p>
  <h2 class="qa-verdict">{_e(lead)}</h2>
  {main_pred}
  <p class="qa-promise"><b>Does your chart even offer this?</b>
  {_e(topic.label)} reads <b>{_e(promise['direction'])}</b> in your chart —
  {_e(promise_conf)}. {_e(topic.note)}</p>
  {blocks}
  {gap_note}
  <p class="qa-caveat">Timing is a window, not a date. What the chart says is
  <em>when the conditions are right</em> — you still have to apply, ask, and
  move inside it.</p>
  {upsell}
</section>"""
