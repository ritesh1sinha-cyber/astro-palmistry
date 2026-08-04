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
from typing import Any

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


def numerology_numbers(name: str, dob) -> dict:
    """Life path from the date, expression from the name."""
    digits = [int(c) for c in f"{dob:%Y%m%d}"]
    life = _reduce(sum(digits))
    letters = {c: (i % 9) + 1 for i, c in enumerate("abcdefghijklmnopqrstuvwxyz")}
    expr = _reduce(sum(letters.get(c, 0) for c in name.lower() if c.isalpha()))
    birthday = _reduce(dob.day)
    return {"life_path": life, "expression": expr, "birthday": birthday}


def render_numerology(name: str, dob, *, paid: bool = False,
                      price: int = 199) -> str:
    nums = numerology_numbers(name, dob)
    cards = ""
    for key, label, note in (
        ("life_path", "Life path", "from your date of birth — the arc you are on"),
        ("expression", "Expression", "from your full name — how you land on others"),
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
  {'' if paid else f'''
  <div class="tab-cta">
    <p>Your numbers also carry a <b>personal year</b> that changes every
    birthday, favourable dates for signing and starting, and a name-correction
    analysis. ₹{price}.</p>
  </div>'''}
</section>"""


# ---------------------------------------------------------------------------
# Palmistry
# ---------------------------------------------------------------------------

def render_palm(public: dict, *, paid: bool = False, price: int = 499) -> str:
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
  {quality_note}
  <div class="evidence"><span class="ev-label">Measured from your palms</span>
    <ul class="palm-scores">{score_rows}</ul>
    <p class="fine">{meta.get('rulesSearched', 0)} classical rules were checked
    against the lines and mounts actually detected in your photos.
    Dominant hand read: <b>{_e(meta.get('dominantHand'))}</b>{
    f", hand type {_e(meta.get('handType'))}" if meta.get('handType') else ''}.</p>
  </div>
  <h3 class="tab-sec">What your hand says has already happened</h3>
  <ul class="palm-list">{past_rows}</ul>
  <h3 class="tab-sec">What it says is ahead</h3>
  <ul class="palm-list">{future_rows}</ul>
  {'' if paid else f'''
  <div class="tab-cta">
    <p>{len(future)} dated sections ahead are in the full reading — ₹{price}.</p>
  </div>'''}
</section>"""
