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
    verdict = str(res.get("trialVerdict", ""))

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
  {'' if paid else f'''
  <div class="tab-cta">
    <p><b>The corrected time itself is the paid part</b> — along with your
    rebuilt chart, and every event re-scored against it. ₹{price}.</p>
    <p class="fine">We show you the gap for free because you should be able to
    see there is a problem before paying anyone to fix it.</p>
  </div>'''}
</section>"""


# ---------------------------------------------------------------------------
# Numerology
# ---------------------------------------------------------------------------

NUMBER_MEANING = {
    1: ("The one who starts things", "You do better running your own thing than fitting into someone else's."),
    2: ("The one who holds it together", "You read a room faster than you decide in it."),
    3: ("The one who makes it appealing", "Expression is your lever — when you go quiet, things stall."),
    4: ("The one who builds it properly", "Slow, structural, and underestimated until the results are undeniable."),
    5: ("The one who needs room", "Restriction costs you more than risk does."),
    6: ("The one everyone leans on", "You carry other people's problems, and it is both your gift and your tax."),
    7: ("The one who needs to understand it", "You would rather be right in private than popular in public."),
    8: ("The one who deals in scale", "Money and authority are your themes whether you chose them or not."),
    9: ("The one who finishes things", "Endings keep finding you, and you are better at them than most."),
}


def _reduce(n: int) -> int:
    while n > 9:
        n = sum(int(c) for c in str(n))
    return n


VOWELS = set("aeiou")

#: Chaldean values — the system Indian numerology actually uses. 9 is never
#: assigned to a letter in Chaldean, which is why it differs from Pythagorean.
CHALDEAN = {**{c: 1 for c in "aij"}, **{c: 2 for c in "bkr"},
            **{c: 3 for c in "cgls"}, **{c: 4 for c in "dmt"},
            **{c: 5 for c in "ehnx"}, **{c: 6 for c in "uvw"},
            **{c: 7 for c in "oz"}, **{c: 8 for c in "fp"}}

PERSONAL_YEAR = {
    1: ("A starting year", "Begin things. What you start now sets the tone for eight more years."),
    2: ("A patience year", "Partnerships and waiting. Forcing anything this year costs double."),
    3: ("An expression year", "Being seen, speaking, creating. Visibility comes easily now."),
    4: ("A building year", "Unglamorous, structural work. The year that makes the next three possible."),
    5: ("A change year", "Movement, travel, disruption. Do not sign long leases you cannot exit."),
    6: ("A responsibility year", "Family and duty come first, whether you planned it or not."),
    7: ("A withdrawal year", "Study, reflection, health. A poor year to push, a good one to prepare."),
    8: ("A money and power year", "The harvest year of the cycle. Ask for what you are owed."),
    9: ("A clearing year", "Endings and letting go. Do not start something you want to keep."),
}

LUCKY = {
    1: ("Sunday", "gold, orange", "Sun"), 2: ("Monday", "white, cream", "Moon"),
    3: ("Thursday", "yellow", "Jupiter"), 4: ("Saturday", "grey, khaki", "Rahu"),
    5: ("Wednesday", "green", "Mercury"), 6: ("Friday", "white, pastels", "Venus"),
    7: ("Monday", "sea green", "Ketu"), 8: ("Saturday", "black, deep blue", "Saturn"),
    9: ("Tuesday", "red", "Mars"),
}

CHALLENGE = {
    1: "Being told what to do. You will quietly sabotage a role that has no autonomy.",
    2: "Saying no. You absorb other people's decisions and call it agreement.",
    3: "Finishing. Starting is easy for you and closing is not.",
    4: "Flexibility. You will defend a plan past the point it still makes sense.",
    5: "Staying. Boredom reads to you as a reason to leave.",
    6: "Boundaries. You will carry someone who could carry themselves.",
    7: "Letting people in. You solve things alone that would be faster shared.",
    8: "Scale creep. You take on the bigger version before the smaller one works.",
    9: "Holding on. You keep loyalties past their usefulness.",
}


def numerology_numbers(name: str, dob, *, today=None) -> dict:
    """Life path, expression, soul urge, personality, birthday, personal year."""
    from datetime import date as _date
    today = today or _date.today()
    letters = [c for c in name.lower() if c.isalpha()]
    life = _reduce(sum(int(c) for c in f"{dob:%Y%m%d}"))
    expr = _reduce(sum(CHALDEAN.get(c, 0) for c in letters))
    soul = _reduce(sum(CHALDEAN.get(c, 0) for c in letters if c in VOWELS))
    persona = _reduce(sum(CHALDEAN.get(c, 0) for c in letters if c not in VOWELS))
    birthday = _reduce(dob.day)
    # personal year runs birthday to birthday, not January to January
    year = today.year if (today.month, today.day) >= (dob.month, dob.day) \
        else today.year - 1
    p_year = _reduce(dob.day + dob.month + _reduce(year))
    return {"life_path": life, "expression": expr, "soul_urge": soul,
            "personality": persona, "birthday": birthday,
            "personal_year": p_year, "year_from": year}


def render_numerology(name: str, dob, *, paid: bool = False,
                      price: int = 199, today=None) -> str:
    nums = numerology_numbers(name, dob, today=today)
    # The Lo Shu grid is the only visual in numerology, and the empty cells are
    # what make people ask questions. It belongs in the free half.
    lo_shu_html = ""
    try:
        import lo_shu
        lo_shu_html = lo_shu.render(lo_shu.build(dob), dob, paid=paid, price=price)
    except Exception:
        pass
    cards = ""
    for key, label, note in (
        ("life_path", "Life path", "from your date of birth — the arc you are on"),
        ("expression", "Expression", "from your full name — how you land on others"),
        ("soul_urge", "Soul urge", "from the vowels — what you actually want"),
        ("personality", "Outer personality",
         "from the consonants — what strangers meet first"),
        ("birthday", "Birthday number", "from the day itself — your working style"),
    ):
        n = nums[key]
        title, meaning = NUMBER_MEANING.get(n, ("", ""))
        cards += f"""
    <div class="num-card">
      <div class="num-big">{n}</div>
      <div class="num-body">
        <div class="num-label">{_e(label)}</div>
        <b>{_e(title)}</b>
        <p>{_e(meaning)}</p>
        <span class="num-src">{_e(note)}</span>
      </div>
    </div>"""

    return f"""
<section class="tab" id="tab-numerology">
  <div class="tab-head">
    <span class="tab-kind">Numerology</span>
    <h2>Your numbers, and what they actually describe</h2>
  </div>
  <div class="num-grid">{cards}</div>
  <div class="evidence"><span class="ev-label">Where these come from</span>
    <ul>
      <li>Life path {nums['life_path']} — the digits of
        {dob:%d %B %Y} reduced.</li>
      <li>Expression {nums['expression']} — the letters of your full name
        reduced. Change the spelling and this changes, which is why name
        correction is a real technique rather than a superstition.</li>
    </ul>
  </div>
  <div class="num-year">
    <div class="ev-label">Your numerology period this year — free</div>
    <h4>{nums['personal_year']} · {_e(PERSONAL_YEAR.get(nums['personal_year'], ('',''))[0])}</h4>
    <p>{_e(PERSONAL_YEAR.get(nums['personal_year'], ('',''))[1])}</p>
    <p class="fine">This runs birthday to birthday, not January to January —
    it began on your {dob:%d %B} in {nums['year_from']} and turns over on the
    next one.</p>
  </div>

  <div class="num-future">
    <div class="ev-label">The years after this one</div>
    <ul class="num-seq">
      <li><span>{nums['year_from'] + 1}</span>
        <b class="blurred">Year {(nums['personal_year'] % 9) + 1} — locked</b></li>
      <li><span>{nums['year_from'] + 2}</span>
        <b class="blurred">Year {((nums['personal_year'] + 1) % 9) + 1} — locked</b></li>
      <li><span>{nums['year_from'] + 3}</span>
        <b class="blurred">Year {((nums['personal_year'] + 2) % 9) + 1} — locked</b></li>
    </ul>
    <p class="fine">The nine-year cycle is fixed, so these are already
    determined — including which of them is your money year and which one you
    should not start anything in.</p>
  </div>

  {lo_shu_html}

  <div class="num-extra">
    <div><span>Your day</span><b>{_e(LUCKY.get(nums['life_path'], ('',''))[0])}</b></div>
    <div><span>Your colours</span><b>{_e(LUCKY.get(nums['life_path'], ('','',''))[1])}</b></div>
    <div><span>Ruling planet</span><b>{_e(LUCKY.get(nums['life_path'], ('','',''))[2])}</b></div>
  </div>

  <div class="evidence"><span class="ev-label">The thing your numbers make hard
  for you</span>
    <p style="font-size:.88rem;margin:8px 0 0">{_e(CHALLENGE.get(nums['life_path'], ''))}</p>
  </div>

  {'' if paid else f'''
  <div class="tab-cta">
    <p><b>What the unlock adds:</b> your next three personal years dated in
    advance, favourable dates for signing, starting and travelling, a
    name-correction analysis with the exact spelling that balances your chart,
    and compatibility scoring against another person's numbers. ₹{price}.</p>
  </div>'''}
</section>"""


# ---------------------------------------------------------------------------
# Palmistry
# ---------------------------------------------------------------------------

def render_palm(public: dict, *, paid: bool = False, price: int = 499,
                overlays: Optional[dict] = None,
                raw: Optional[dict] = None) -> str:
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
