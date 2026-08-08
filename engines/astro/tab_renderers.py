"""Every tab in the same card language.

The report redesign only helps if the whole product speaks one dialect. A
customer who reads a beautifully clear career card and then hits a guna table
with eight Sanskrit column headings has learned that the clarity was a veneer.

So each tab here follows the same four rules the report cards follow:

    1. the verdict first, in one sentence a person would say out loud
    2. one number that carries the weight, never eight competing ones
    3. the reasoning visible — planets and periods named, not hidden
    4. an action whenever the news is not good

The differences between tabs are only what the underlying technique actually
supports. Matching has a score out of 36 and doshas; birth-time checking has a
confidence and an offset; palmistry has photo quality as a real constraint.
Pretending they are the same shape would be worse than letting each be itself.
"""

from __future__ import annotations

import html as _html
from typing import Any, Optional

# ---------------------------------------------------------------------------


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def _bar(score: float, out_of: float, *, tone: str = "") -> str:
    pct = max(0.0, min(100.0, 100.0 * float(score) / float(out_of or 1)))
    return (f'<div class="bar"><span style="width:{pct:.0f}%" '
            f'class="{tone}"></span></div>')


# ---------------------------------------------------------------------------
# Kundali matching
# ---------------------------------------------------------------------------

#: Guna names mean nothing to most readers. What each one actually tests does.
KOOT_MEANING = {
    "Varna": "whether you approach life at the same level",
    "Vashya": "who tends to lead and whether the other minds",
    "Gana": "temperament — the day-to-day friction test",
    "Tara / Dina": "each other's luck and wellbeing",
    "Tara": "each other's luck and wellbeing",
    "Yoni": "physical compatibility",
    "Graha Maitri": "whether your minds actually like each other",
    "Bhakoot": "long-term prosperity and health together",
    "Nadi": "constitution — the heaviest single test in the system",
}

VERDICT_LINE = {
    "excellent": "This is a strong match on the classical count.",
    "good": "The count is acceptable — but two specific tests failed, and they "
            "are the ones that matter later rather than at the start.",
    "average": "A workable match that will need deliberate effort in named places.",
    "caution": "The count is acceptable; the failures are not cosmetic.",
    "poor": "The classical count does not support this match as it stands.",
}


def render_match(meta: dict, *, groom: str = "", bride: str = "",
                 paid: bool = False, price: int = 299) -> str:
    total, mx = meta.get("total", 0), meta.get("maxGuna", 36)
    band = str(meta.get("band", "")).lower()
    koots = meta.get("koots") or []
    stars = meta.get("stars") or {}
    doshas = meta.get("activeDoshas") or []
    blocking = meta.get("blocking")

    failed = [k for k in koots if not k.get("ok")]
    passed = [k for k in koots if k.get("ok")]

    lead = VERDICT_LINE.get(band, VERDICT_LINE["average"])
    if failed:
        names = " and ".join(k.get("label", "") for k in failed)
        lead = (f"{total} of {mx} — acceptable overall, but {names} scored zero, "
                f"and those are the two that decide the long run.")

    rows = "".join(f"""
    <li class="koot {'ok' if k.get('ok') else 'bad'}">
      <div class="koot-top"><b>{_e(k.get('label'))}</b>
        <span class="koot-score">{k.get('score')}/{k.get('max')}</span></div>
      <div class="koot-what">{_e(KOOT_MEANING.get(k.get('label'), ''))}</div>
      {_bar(k.get('score', 0), k.get('max', 1),
            tone='good' if k.get('ok') else 'bad')}
    </li>""" for k in koots)

    dosha_block = ""
    if doshas:
        dosha_block = f"""
  <div class="mm-dosha" data-verdict="down">
    <div class="ev-label">What needs handling first</div>
    <p><b>{_e(', '.join(doshas))}</b>{' — classically treated as blocking until remedied.' if blocking else '.'}</p>
    <p>{'Bhakoot scoring zero is about money and health over decades, not about whether you get along now. It is the one failure classical texts insist on treating before the wedding rather than after.' if any('bhakoot' in d.lower() for d in doshas) else 'Remedies for this are named in the full reading.'}</p>
    {'' if paid else f'<p class="locked-inline"><b>The remedies, the exemptions that may already apply to you, and the D9 cross-check are in the full report — ₹{price}.</b></p>'}
  </div>"""

    return f"""
<section class="tab" id="tab-match">
  <div class="tab-head">
    <span class="tab-kind">Kundali matching</span>
    <h2>{_e(groom)} &amp; {_e(bride)}</h2>
  </div>
  <div class="score-hero">
    <div class="score-num">{total}<span>/{mx}</span></div>
    <div class="score-side">
      <div class="score-band">{_e(meta.get('bandPlain', band.title()))}</div>
      {_bar(total, mx, tone='good' if total >= 21 else 'bad')}
    </div>
  </div>
  <p class="tab-lead">{_e(lead)}</p>
  <p class="tab-sub">Moon stars — {_e(groom)}: <b>{_e(stars.get('groom'))}</b>
  ({_e(stars.get('groomMoon'))}) · {_e(bride)}: <b>{_e(stars.get('bride'))}</b>
  ({_e(stars.get('brideMoon'))}). The whole 36-point system is computed from
  these two positions.</p>
  <div class="evidence"><span class="ev-label">All eight tests, and what each
  one is actually measuring</span>
    <ul class="koots">{rows}</ul></div>
  {dosha_block}
  <p class="tab-caveat">{len(passed)} of {len(koots)} tests passed. A score is a
  starting point for a conversation, not a verdict on two people.</p>
</section>"""


# ---------------------------------------------------------------------------
# Birth-time check (BTR)
# ---------------------------------------------------------------------------

def render_btr(res: dict, *, paid: bool = False, price: int = 999) -> str:
    trial = res.get("trialTime", "")
    conf = str(res.get("confidence", "")).lower()
    used = res.get("eventsUsed", 0)
    t_score, b_score = res.get("trialScore"), res.get("bestScore")
    changes = res.get("changesLagna")
    moves = res.get("movesBy", "")

    better = (b_score or 0) > (t_score or 0)
    if not better:
        lead = f"Your stated birth time of {trial[:5]} holds up. Nothing to change."
    elif changes:
        lead = (f"Your birth time is probably wrong by {moves} — and that is "
                f"enough to change your rising sign.")
    else:
        lead = (f"Your birth time looks off by {moves}, though not enough to "
                f"change your rising sign.")

    stakes = ("" if not changes else """
  <div class="btr-stakes" data-verdict="down">
    <div class="ev-label">Why this matters more than it sounds</div>
    <p>The rising sign decides which planet rules which part of your life.
    Change it and every house shifts: the planet that ruled your career now
    rules your health, and every dated prediction moves with it. This is the
    one input everything else is built on.</p>
  </div>""")

    if paid and res.get("suggestedTime"):
        off = res.get("offsetMinutes")
        off_bit = (f" · {_e(off)} minutes from the time you gave"
                   if off is not None else "")
        msg = (f"<p>{_e(res.get('message'))}</p>" if res.get("message") else "")
        paid_block = f"""
  <div class="btr-answer">
    <div class="ev-label">Your rectified time</div>
    <p class="btr-time">{_e(res.get("suggestedTime"))}</p>
    <p class="fine">{_e(res.get("lagnaBest") or "")}{off_bit}</p>
    {msg}
  </div>"""
    elif not paid:
        paid_block = f"""
  <div class="tab-cta">
    <p><b>The corrected time itself is the paid part</b> — along with your
    rebuilt chart, and every event re-scored against it. ₹{price}.</p>
    <p class="fine">We show you the gap for free because you should be able to
    see there is a problem before paying anyone to fix it.</p>
  </div>"""
    else:
        paid_block = ""

    return f"""
<section class="tab" id="tab-btr">
  <div class="tab-head">
    <span class="tab-kind">Birth-time check</span>
    <h2>{_e(lead)}</h2>
  </div>
  <div class="btr-grid">
    <div><span>Time you gave</span><b>{_e(trial[:5])}</b></div>
    <div><span>Fit against your life</span><b>{t_score}</b></div>
    <div><span>Best fit found</span><b>{b_score}</b></div>
    <div><span>Confidence</span><b>{_e(conf.title())}</b></div>
  </div>
  <div class="evidence"><span class="ev-label">How this was worked out</span>
    <ul>
      <li>{used} life events you supplied were scored against every candidate
        minute, checking whether the period running at the time is the one
        classically responsible for that kind of event.</li>
      <li>Your stated time scores <b>{t_score}</b>; the best candidate scores
        <b>{b_score}</b>. {'That gap is what says the time is off.' if better
          else 'No candidate beat your stated time.'}</li>
      <li>Rising sign on your stated time: <b>{_e(res.get('lagnaTrial'))}</b>
        {'— and it changes on the corrected time.' if changes else ''}</li>
    </ul>
  </div>
  {stakes}
  {paid_block}
</section>"""


# ---------------------------------------------------------------------------
# Muhurat (event timing for a chosen date)
# ---------------------------------------------------------------------------

MUHURAT_VERDICT = {
    "good": "This day clears the classical checks for the occasion.",
    "mixed": "Usable with caveats — some checks pass, some do not.",
    "poor": "The day is weak for this occasion on the classical count.",
    "avoid": "Classical texts treat this day as one to skip for this event.",
}


def render_muhurat(summary: dict, detail: Optional[dict] = None, *,
                   paid: bool = False, price: int = 49,
                   event_id: str = "", date_str: str = "") -> str:
    """Verdict-first muhurat card. Free = day call; paid = every check + alts."""
    detail = detail or {}
    verdict = str(summary.get("verdict") or "mixed").lower()
    lead = MUHURAT_VERDICT.get(verdict, MUHURAT_VERDICT["mixed"])
    headline = summary.get("headline") or summary.get("summary") or ""
    label = summary.get("event_label") or event_id or "this occasion"
    plain = summary.get("event_plain") or label
    when = summary.get("target_date") or date_str or ""

    def _as_list(v):
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            # some checkers return {"windows":[...]} or keyed maps
            if all(isinstance(x, dict) for x in v.values()):
                return list(v.values())
            for key in ("items", "windows", "list", "checks", "alternatives"):
                if isinstance(v.get(key), list):
                    return v[key]
            return [v]
        return []

    checks = _as_list(detail.get("checks"))
    alts = _as_list(detail.get("alternatives"))
    notes = detail.get("chart_notes") or []
    raw_windows = detail.get("day_windows") or {}

    check_rows = ""
    if paid and checks:
        items = "".join(
            f'<li class="{"ok" if (isinstance(c, dict) and c.get("ok")) else "bad"}">'
            f'<b>{_e((c or {}).get("name") if isinstance(c, dict) else c)}</b>'
            f' — {_e((c or {}).get("detail") or "") if isinstance(c, dict) else ""}</li>'
            for c in checks)
        check_rows = f"""
  <div class="evidence"><span class="ev-label">Every check on this day</span>
    <ul class="muh-checks">{items}</ul></div>"""
    elif not paid:
        n = summary.get("checkCount")
        if n is None:
            n = len(checks)
        a = summary.get("alternativeCount")
        if a is None:
            a = len(alts)
        check_rows = f"""
  <div class="tab-cta">
    <p><b>{n} checks</b> were run against this day, and
    <b>{a} better date{"s" if a != 1 else ""}</b> sit nearby.
    The pass/fail list, the strong hours, and those alternatives are in the
    full reading — ₹{price}.</p>
  </div>"""

    alt_block = ""
    if paid and alts:
        rows = "".join(
            f'<li><b>{_e(a.get("date") or a.get("target_date") or "")}</b>'
            f' — {_e(a.get("verdict") or a.get("headline") or "")}</li>'
            for a in alts[:6] if isinstance(a, dict))
        alt_block = f"""
  <div class="evidence"><span class="ev-label">Better days nearby</span>
    <ul>{rows}</ul></div>"""

    win_block = ""
    if paid and isinstance(raw_windows, dict) and raw_windows:
        bits: list[str] = []
        day_summary = raw_windows.get("day_summary")
        if isinstance(day_summary, str) and day_summary.strip():
            bits.append(f"<li>{_e(day_summary)}</li>")
        ab = raw_windows.get("abhijit") or {}
        if isinstance(ab, dict) and ab.get("start"):
            bits.append(
                f"<li><b>Abhijit</b> — {_e(ab.get('start'))}–{_e(ab.get('end'))}"
                f"{(' · ' + _e(ab.get('plain'))) if ab.get('plain') else ''}</li>")
        best = raw_windows.get("best_choghadiya") or {}
        if isinstance(best, dict) and (best.get("label") or best.get("start")):
            bits.append(
                f"<li><b>{_e(best.get('label') or 'Best hour')}</b> — "
                f"{_e(best.get('start'))}–{_e(best.get('end'))}"
                f"{(' · ' + _e(best.get('plain'))) if best.get('plain') else ''}</li>")
        for slot in (raw_windows.get("tri_kaal") or [])[:4]:
            if isinstance(slot, dict) and slot.get("start"):
                bits.append(
                    f"<li><b>Avoid {_e(slot.get('label'))}</b> — "
                    f"{_e(slot.get('start'))}–{_e(slot.get('end'))}</li>")
        if bits:
            win_block = f"""
  <div class="evidence"><span class="ev-label">Strong hours on the day</span>
    <ul>{''.join(bits)}</ul></div>"""
    elif paid:
        windows = _as_list(raw_windows)
        rows = "".join(
            f'<li><b>{_e(w.get("label") or w.get("name") or w.get("when") or "")}</b>'
            f' — {_e(w.get("detail") or w.get("note") or "")}</li>'
            for w in windows[:8] if isinstance(w, dict))
        if rows:
            win_block = f"""
  <div class="evidence"><span class="ev-label">Strong hours on the day</span>
    <ul>{rows}</ul></div>"""

    note_block = ""
    if paid and notes:
        if isinstance(notes, list):
            rows = "".join(
                f"<li>{_e(n if isinstance(n, str) else (n.get('text') if isinstance(n, dict) else n))}</li>"
                for n in notes[:6])
            note_block = f"""
  <div class="evidence"><span class="ev-label">Chart notes for this occasion</span>
    <ul>{rows}</ul></div>"""
        elif isinstance(notes, str) and notes.strip():
            note_block = f'<p class="tab-sub">{_e(notes)}</p>'

    partner = ""
    if summary.get("needs_partner_chart"):
        partner = ('<p class="tab-caveat">For a wedding, the sharpest reading '
                   "needs both charts — add them under Matching.</p>")

    tone = ("good" if verdict == "good"
            else "bad" if verdict in ("poor", "avoid") else "mixed")

    return f"""
<section class="tab" id="tab-muhurat">
  <div class="tab-head">
    <span class="tab-kind">Muhurat · {_e(label)}</span>
    <h2>{_e(when)} — {_e(plain)}</h2>
  </div>
  <div class="muh-hero" data-verdict="{tone}">
    <div class="muh-verdict">{_e(verdict.upper())}</div>
    <p class="tab-lead">{_e(lead)}</p>
  </div>
  {f'<p class="tab-sub">{_e(headline)}</p>' if headline else ""}
  {partner}
  {check_rows}
  {win_block}
  {note_block}
  {alt_block}
</section>"""


# ---------------------------------------------------------------------------
# Numerology now lives in engines/astro/numerology_cards.py, which drives
# the real numerology_report engine (Chaldean cipher, the 45-year dasha
# ring, name harmony and name correction) instead of the thin
# reimplementation that used to sit here and could not deliver what its
# own pay card promised.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Palmistry
# ---------------------------------------------------------------------------

def render_palm(public: dict, *, paid: bool = False, price: int = 499,
                overlays: Optional[dict] = None,
                raw: Optional[dict] = None,
                pc: Optional[dict] = None) -> str:
    meta = public.get("meta") or {}
    scores = public.get("scores") or {}
    past = public.get("past") or []
    future = public.get("future") or []
    quality = meta.get("photoQuality")
    advice = meta.get("photoAdvice") or []

    quality_note = ""
    if quality and str(quality).lower() not in ("a", "excellent", "good"):
        quality_note = f"""
  <div class="palm-quality" data-verdict="mixed">
    <div class="ev-label">About your photos</div>
    <p>Photo grade <b>{_e(quality)}</b>. A palm reading is only as good as the
    image — we would rather tell you than quietly read a blurred line.</p>
    {'<ul>' + ''.join(f'<li>{_e(a)}</li>' for a in advice[:3]) + '</ul>' if advice else ''}
  </div>"""

    # Showing the marked-up palms is the strongest trust signal in this tab:
    # the reader can see their own hand with the lines the engine actually
    # traced, which is not something a generic reading could fake.
    # Shape, fingers and the special marks are free: a reader can verify all
    # three by turning their own palm over, which is why they build more trust
    # than any prediction could.
    marks_html = ""
    try:
        import palm_marks
        marks_html = palm_marks.render(palm_marks.build(raw or {}),
                                       paid=paid, price=price)
    except Exception:
        pass

    # The astro-palmistry layer needs no photograph, so it renders whenever a
    # chart is available — including before any upload.
    astro_html = ""
    if pc:
        astro_html = render_palm_astro(
            pc, palm_features=(raw or {}).get("features"),
            paid=paid, price=price)

    ov = overlays or {}
    overlay_block = ""
    if ov:
        imgs = "".join(
            f'<figure><img src="{_e(u)}" alt="{_e(h)} palm with detected lines"/>'
            f'<figcaption>{_e(h.title())} hand — lines and mounts as detected</figcaption>'
            f'</figure>' for h, u in ov.items() if u)
        if imgs:
            overlay_block = (
                '<div class="palm-shots"><div class="ev-label">Your palms, as '
                'the engine read them</div><div class="palm-imgs">' + imgs
                + '</div><p class="fine">These are your own photographs with the '
                  'lines the reading is based on drawn on top. If a line looks '
                  'wrong to you, the reading of it will be wrong too — retake '
                  'and run it again.</p></div>')

    score_rows = "".join(f"""
      <li><span>{_e(k.replace('_', ' ').title())}</span>
        {_bar(v if isinstance(v, (int, float)) else 0, 10)}
        <b>{v}</b></li>""" for k, v in list(scores.items())[:6])

    past_rows = "".join(f"""
    <li><b>{_e(p.get('title', ''))}</b>
      {f"<span class='palm-age'>{_e(p.get('ageRange') or p.get('age'))}</span>"
       if p.get('ageRange') or p.get('age') else ''}
      <p>{_e(p.get('body', ''))}</p></li>""" for p in past[:3])

    future_rows = "".join(f"""
    <li class="{'' if paid else 'locked'}"><b>{_e(f.get('title', ''))}</b>
      {f"<span class='palm-age'>{_e(f.get('ageRange') or f.get('age'))}</span>"
       if f.get('ageRange') or f.get('age') else ''}
      <p class="{'' if paid else 'blurred'}">{_e(f.get('body', ''))}</p></li>"""
        for f in future[:4])

    return f"""
<section class="tab" id="tab-palm">
  <div class="tab-head">
    <span class="tab-kind">Palm reading</span>
    <h2>{_e(public.get('summary') or 'What your hands show')}</h2>
  </div>
  {overlay_block}
  {quality_note}
  {marks_html}
  {astro_html}
  <div class="evidence"><span class="ev-label">Measured from your palms</span>
    <ul class="palm-scores">{score_rows}</ul>
    <p class="fine">{meta.get('rulesSearched', 0)} classical rules were checked
    against the lines and mounts actually detected in your photos.
    Dominant hand read: <b>{_e(meta.get('dominantHand'))}</b>{
    f", hand type {_e(meta.get('handType'))}" if meta.get('handType') else ''}.</p>
  </div>
  <h3 class="tab-sec">What your hand says has already happened</h3>
  <ul class="palm-list">{past_rows}</ul>
  {'' if paid else '''<div class="remedy-locked">
    <b>The line-by-line analysis is the locked half</b> — every break, island,
    chain and crossing on each major line, dated by position, plus what the
    mounts add. That is where a palm reading stops being a personality sketch.
  </div>'''}
  <h3 class="tab-sec">What it says is ahead</h3>
  <ul class="palm-list">{future_rows}</ul>
  {'' if paid else f'''
  <div class="tab-cta">
    <p>{len(future)} dated sections ahead are in the full reading — ₹{price}.</p>
  </div>'''}
</section>"""

# ---------------------------------------------------------------------------
# Astro-palmistry: what the chart says the hand should show
# ---------------------------------------------------------------------------

def render_palm_astro(pc: dict, *, palm_features: Any = None,
                      paid: bool = False, price: int = 499) -> str:
    """The chart-driven half of palmistry — needs no photograph at all.

    This is the layer that makes the tab useful before any upload: the birth
    chart names which mount should be raised, which planet is line-lord of each
    life zone, and what a hand carrying this chart ought to look like. When palm
    features ARE supplied it also reports agreement, and agreement between two
    independent methods is the strongest evidence the product has.
    """
    try:
        import palm_astro_bridge as PB
    except Exception:
        return ""
    try:
        block = PB.build(pc, palm_features)
    except Exception:
        return ""
    if not block:
        return ""

    statements = block.get("statements") or []
    zones = block.get("zones") or []
    cross = block.get("cross_check") or []
    windows = block.get("health_windows") or []
    supplied = bool(block.get("palm_supplied"))

    # Free: the expectations, because the reader can check them on their own
    # hand in seconds and that is the whole trust argument for this tab.
    shown = statements if paid else statements[:3]
    hidden = max(0, len(statements) - len(shown))

    st_rows = "".join(f"""
    <li class="pa-row">
      <div class="pa-mount">{_e(st.get('mount') or st.get('zone_id'))}</div>
      <div class="pa-text">{_e(st.get('text') or '')}</div>
      {f'<div class="pa-why">{_e(st.get("because"))}</div>' if st.get("because") else ''}
    </li>""" for st in shown)

    zone_rows = "".join(f"""
    <li class="pa-zone">
      <span class="pa-area">{_e(str(z.get('area', '')).title())}</span>
      <span class="pa-anchor">{_e(z.get('anchor_planet'))} —
        {_e(z.get('mount'))}</span>
    </li>""" for z in zones[:8])

    cross_html = ""
    if supplied and cross:
        agree = [c for c in cross if c.get("agrees")]
        cross_html = f"""
  <div class="pa-cross" data-verdict="{'up' if agree else 'mixed'}">
    <div class="ev-label">Where your hand and your chart agree</div>
    <p>{len(agree)} of {len(cross)} zones checked out against your photographs.
    Two independent methods reaching the same finding is the strongest thing we
    can tell you.</p>
    <ul>{''.join(f"<li>{_e(c.get('text') or '')}</li>" for c in cross[:4])}</ul>
  </div>"""
    elif not supplied:
        cross_html = """
  <div class="pa-cross" data-verdict="mixed">
    <div class="ev-label">Upload your palms to cross-check this</div>
    <p>Everything above is what your <em>chart</em> says your hand should show.
    Send photographs and we check each one against what is actually there — and
    where the two agree independently, that finding is about as solid as
    astrology gets.</p>
  </div>"""

    # 8th-house material surfaces ONLY as a health-concern window with a remedy.
    # No lifespan, ever — see no_longevity.py.
    win_html = ""
    if windows:
        win_html = "".join(f"""
  <div class="pa-window" data-verdict="down">
    <div class="ev-label">A window worth being careful in</div>
    <p>{_e(w.get('text') or '')}</p>
    {f'<p class="fine">{_e(w.get("because"))}</p>' if w.get("because") else ''}
    <p class="pa-remedy"><b>What helps:</b> {_e(w.get('remedy') or '')}</p>
  </div>""" for w in windows[:2])

    locked = "" if paid or not hidden else f"""
  <div class="remedy-locked">
    <b>{hidden} more chart-to-hand readings</b> — every mount, the sub-planets
    sitting in each zone, and the marks your chart predicts you will find.
    ₹{price}
  </div>"""

    return f"""
<section class="palm-astro">
  <div class="ev-label">Astro-palmistry — your chart read onto your hand</div>
  <p class="pa-lede">{_e(block.get('note') or '')}</p>
  <ul class="pa-list">{st_rows}</ul>
  {locked}
  <div class="evidence">
    <span class="ev-label">Which planet governs which zone of your palm</span>
    <ul class="pa-zones">{zone_rows}</ul>
  </div>
  {cross_html}
  {win_html}
</section>"""
