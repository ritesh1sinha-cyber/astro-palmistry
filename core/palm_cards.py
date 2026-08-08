"""palm_cards.py — the palm reading in the cards-v2 language.

The palm report used to render through `palm_api.pipeline.render_lane_html`,
which carries its own Georgia/blue stylesheet and has no `paid` flag: the two
halves were produced by deep-copying the analysis and deleting fields from each
copy. That approach put the whole numbered-point list — every finding with its
estimated age — on the free side, and took the customer's own annotated
photographs off the paid side.

So this module renders the same analysis twice, branching on `paid`, in the
shared dialect from `report_shell`. Free carries the photographs, the four
scores, the eight life-area verdicts and every dated marking the reader has
already lived through; paid adds the working behind each verdict, the markings
still ahead, the mounts, what the marks mean, and the numbered points.
"""

from __future__ import annotations

import html as _html
import re
from typing import Any, List, Optional

# Palmistry strength is a confidence level, not a direction, so it maps onto the
# pill colours differently from the chart report's up/down/mixed verdicts.
STRENGTH_PILL = {"strong": "up", "moderate": "mixed", "tentative": "faint"}
STRENGTH_LABEL = {"strong": "Strong signal", "moderate": "Moderate",
                  "tentative": "Tentative"}


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def _first(name: str) -> str:
    n = (name or "").strip().split()
    return n[0] if n else "friend"


def _bar(value: Any) -> str:
    try:
        pct = max(0, min(100, int(value)))
    except (TypeError, ValueError):
        pct = 0
    return f'<div class="bar"><span style="width:{pct}%"></span></div>'


# ---------------------------------------------------------------------------
# blocks
# ---------------------------------------------------------------------------
def _data_uri(overlay_path: Optional[str]) -> str:
    """Overlays are embedded, not linked: each half is served as a standalone
    document through /api/file/{token}, so a storage key would not resolve."""
    if not overlay_path:
        return ""
    from pathlib import Path
    p = Path(overlay_path)
    if not p.is_file():
        return ""
    import base64
    return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode("ascii")


def _photos(raw: dict, dom_key: str) -> str:
    figs = ""
    for hand in ("left", "right"):
        src = _data_uri((raw.get(hand) or {}).get("overlay_path"))
        if not src:
            continue
        role = "dominant — what you have made of it" if hand == dom_key \
            else "innate — what you were handed"
        figs += (f'<figure><img src="{src}" alt="{hand} palm with the '
                 f'detected lines drawn on"/>'
                 f'<figcaption>{hand.title()} hand · {role}</figcaption></figure>')
    if not figs:
        return ""
    return f"""
<div class="palm-shots">
  <div class="ev-label">Your palms, as the engine read them</div>
  <div class="palm-imgs">{figs}</div>
  <p class="fine">These are your own photographs with the lines this reading is
  built from drawn on top. If a line looks wrong to you, the reading of it will
  be wrong too — retake the photo and run it again.</p>
</div>"""


def _quality(dom: dict) -> str:
    feats = dom.get("features") or {}
    q = feats.get("quality") or {}
    grade = q.get("grade")
    if not grade or str(grade).lower() in ("a", "excellent", "good"):
        return ""
    advice = ((feats.get("photo_guidance") or {}).get("suggestions") or [])[:3]
    tips = ("<ul>" + "".join(f"<li>{_e(a)}</li>" for a in advice) + "</ul>") if advice else ""
    return f"""
<div class="card">
  <div class="ev-label">About your photos</div>
  <p class="claim">Photo grade {_e(grade)}.</p>
  <p class="fine">A palm reading is only as good as the image. We would rather
  tell you than quietly read a blurred line.</p>
  {tips}
</div>"""


def _scores(scores: List[dict]) -> str:
    if not scores:
        return ""
    rows = "".join(f"""
    <li><span>{_e(s.get('k'))}</span>{_bar(s.get('v'))}<b>{_e(s.get('v'))}</b></li>"""
                   for s in scores)
    return f"""
<div class="card">
  <div class="ev-label">Measured from your palms</div>
  <ul class="palm-scores">{rows}</ul>
</div>"""


def _opening(text: str) -> str:
    if not text:
        return ""
    # palm_opening() emits its own <b> emphasis, so this one is not escaped.
    return f"""
<div class="card persona">
  <div class="ev-label">What your hands say you are</div>
  <p class="claim">{text}</p>
</div>"""


def _aspect_card(a: dict, *, paid: bool) -> str:
    pts = [p for p in (a.get("points") or []) if (p.get("text") or "").strip()]
    head = pts[0]["text"] if pts else (a.get("summary") or "")
    rest = pts[1:]
    both = sum(1 for p in pts if p.get("reinforced"))
    strength = str(a.get("strength") or "")
    pill_cls = STRENGTH_PILL.get(strength, "faint")
    pill_txt = STRENGTH_LABEL.get(strength, strength.title() or "Read")
    agree = f'<span class="agree">{both} on both hands</span>' if both else ""

    if paid:
        ev = "".join(
            f"<li>{_e(p['text'])}"
            + (' <b class="both">&#10003; both hands</b>' if p.get("reinforced") else "")
            + "</li>" for p in rest)
        body = (f'<div class="evidence"><span class="ev-label">What your hands show</span>'
                f'{agree}<ul>{ev}</ul>'
                + (f'<p class="fine">{_e(a.get("strength_note"))}</p>'
                   if a.get("strength_note") else "")
                + "</div>")
    else:
        n = len(rest)
        body = (f'<div class="evidence locked-inline">'
                f'<span class="ev-label">What your hands show</span>{agree}'
                f'<p><span class="lockicon">&bull;</span> {n} further '
                f'sign{"s" if n != 1 else ""} in your hands land on this. '
                f'The working is in the full reading.</p></div>')

    return f"""
<article class="card" data-verdict="{_e(strength)}">
  <div class="card-top"><span class="area">{_e(a.get('title'))}</span>
    <span class="pill {pill_cls}">{_e(pill_txt)}</span></div>
  <p class="claim">{_e(head)}</p>
  {body}
</article>"""


def _hands_compare(conf: dict) -> str:
    rows = ""
    for li in conf.get("lines") or []:
        if not li.get("statement"):
            continue
        rows += (f'<li><b>{_e(li.get("title"))}</b>'
                 f'<p>{_e(li.get("statement"))}</p></li>')
    if not rows:
        return ""
    return f"""
<h3 class="sec">Left hand against right hand</h3>
<p class="sec-note">One hand is what you were handed. The other is what you have
made of it. Where they differ is the interesting part.</p>
<div class="card"><ul class="palm-list">{rows}</ul></div>"""


def _verdict(item: dict) -> str:
    conc = item.get("conclusive") or {}
    txt = (conc.get("verdict") or conc.get("conclusion")
           or item.get("finding") or "").strip()
    # conclusive.py labels every non-line verdict "Reading for you: ...", which
    # reads as a form field once the sentence sits under its own heading.
    txt = re.sub(r"^Reading for you:\s*", "", txt, flags=re.I)
    return txt[:1].upper() + txt[1:] if txt else ""


def _est_age(item: dict) -> Optional[int]:
    age = (item.get("timing") or {}).get("estimated_age")
    return age if isinstance(age, int) else None


def _read_to_today(items: List[dict], *, first: str, age: int) -> str:
    """The credibility block.

    Two kinds of proof, and it deliberately does not depend on the dated ones.
    The engine only dates points on the four major lines — typically four in a
    whole hand — so a reader younger than their first dated marking would get an
    empty block, losing the one argument that earns the click. Hand shape, thumb
    and fingers are always there and the reader can check every one of them by
    looking down.
    """
    shape = [i for i in items if i.get("kind") in ("morphology", "thumb", "finger")]
    behind = sorted([i for i in items
                     if i.get("kind") == "line" and (_est_age(i) or 10**6) <= age],
                    key=lambda i: _est_age(i) or 0)
    if not shape and not behind:
        return ""

    rows = "".join(f"""
    <li><span class="tick">&#10003;</span>
      <div><b>{_e(i.get('title'))}</b> — {_e(_verdict(i))}</div></li>"""
                   for i in shape)
    rows += "".join(f"""
    <li><span class="tick">&#10003;</span>
      <div><b>{_e(i.get('title'))}, around age {_e(_est_age(i))}</b>
      — {_e(_verdict(i))}</div></li>""" for i in behind)

    dated_note = (f" The last {len(behind)} sit at points on your lines that map "
                  f"to years you have already lived." if behind else "")
    return f"""
<div class="proof">
  <div class="ev-label">Your hand, read to today</div>
  <h3>{_e(first)}, check these against your own hand</h3>
  <p>You have told us nothing except your age, and shown us two photographs.
  Everything below was measured off them.{dated_note} If most of it is wrong,
  close this page and keep your money. If most of it is right, the same
  measurements are what the rest of the reading is built on.</p>
  <ul class="hits">{rows}</ul>
</div>"""


def _mark_zone_plain(zone: str) -> str:
    try:
        import palm_voice as PV
        return PV._mount_name((zone or "palm").lower())
    except Exception:  # noqa: BLE001
        return "your palm"


def _marks(dom: dict, conf: dict, *, paid: bool) -> str:
    raw_marks = (dom.get("features") or {}).get("special_marks") or []
    if not raw_marks and not (conf.get("marks") or []):
        return ""
    if paid:
        rows = "".join(f'<li>{_e(m.get("statement"))}</li>'
                       for m in (conf.get("marks") or []) if m.get("statement"))
        if not rows:
            rows = "".join(
                f'<li><p class="pred-scenario"><b>{_e(m.get("title"))}</b> — '
                f'{_e(m.get("meaning"))}</p>'
                f'<p class="pred-why"><b>Why:</b> mark on '
                f'{_e(_mark_zone_plain(str(m.get("zone", "palm"))))}</p></li>'
                for m in raw_marks)
        return f"""
<h3 class="sec">Your special marks, and what each one means</h3>
<p class="sec-note">Rarer than the lines, and read differently: a mark modifies
whatever it sits on.</p>
<div class="card"><ul class="palm-list plain">{rows}</ul></div>"""

    named = "".join(
        f'<li><b>{_e(m.get("title"))}</b> on '
        f'{_e(_mark_zone_plain(str(m.get("zone", "palm"))))}</li>'
        for m in raw_marks)
    if not named:
        return ""
    n = len(raw_marks)
    return f"""
<h3 class="sec">Your special marks</h3>
<p class="sec-note">Turn your hand over and look — these are on it. What they
mean is the part you have to unlock.</p>
<div class="card">
  <ul class="palm-list plain">{named}</ul>
  <div class="when locked-inline"><span class="lockicon">&bull;</span>
  {n} mark{'s' if n != 1 else ''} found. What each one does to the area it sits
  on, and the remedy attached to it, are in the full reading.</div>
</div>"""


def _ahead(items: List[dict], age: int) -> List[dict]:
    return sorted([i for i in items
                   if i.get("kind") == "line" and (_est_age(i) or -1) > age],
                  key=lambda i: _est_age(i) or 0)


def _timeline_ahead(ahead: List[dict]) -> str:
    if not ahead:
        return ""
    rows = "".join(f"""
<li>
  <div class="tl-when">Around age {_e(_est_age(i))}</div>
  <div class="tl-body"><b>{_e(i.get('title'))}</b> — {_e(_verdict(i))}</div>
</li>""" for i in ahead)
    return f"""
<h3 class="sec">What is still ahead of you</h3>
<p class="sec-note">Dated by where the marking falls on the line, not by a
calendar. Treat the age as a window, not a day.</p>
<ol class="timeline">{rows}</ol>"""


def _mounts(conf: dict, items: List[dict]) -> str:
    rows = ""
    for i in items:
        if i.get("kind") != "mount" or not _verdict(i):
            continue
        verdict = _verdict(i)
        if "Why:" in verdict:
            rows += f'<li>{_e(verdict).replace(chr(10), "<br/>")}</li>'
        else:
            rows += (f'<li><p class="pred-scenario"><b>{_e(i.get("title"))}</b> — '
                     f'{_e(verdict)}</p>'
                     f'<p class="pred-why"><b>Why:</b> {_e(i.get("title", "mount"))} area</p></li>')
    rows += "".join(f'<li><p>{_e(m.get("statement"))}</p></li>'
                    for m in (conf.get("mounts") or []) if m.get("statement"))
    if not rows:
        return ""
    return f"""
<h3 class="sec">Mount by mount</h3>
<p class="sec-note">The raised and flat parts of the palm say where your energy
actually goes, independently of the lines crossing them.</p>
<div class="card"><ul class="palm-list">{rows}</ul></div>"""


def _workings(raw: dict) -> str:
    """Every numbered point on both hands — the working the dots refer to."""
    blocks = ""
    for hand in ("right", "left"):
        hd = raw.get(hand)
        if not hd:
            continue
        items = hd.get("numbered_checklist") or []
        if not items:
            continue
        rows = ""
        for it in items:
            num = it.get("num", "?")
            conc = it.get("conclusive") or {}
            timing = it.get("timing") or {}
            when = ""
            if timing.get("estimated_age") is not None:
                rng = timing.get("age_range") or []
                age = timing["estimated_age"]
                when = (f'<span class="pt-when">approximately {_e(rng[0])}&ndash;{_e(rng[1])}</span>'
                        if len(rng) == 2 and rng[1] > rng[0] else
                        f'<span class="pt-when">around age {_e(age)}</span>')
            verdict = conc.get("verdict") or conc.get("conclusion") or it.get("finding", "")
            rows += (f'<li><b>Point {_e(num)} — {_e(it.get("title"))}</b>{when}'
                     f'<p>{_e(verdict)}</p></li>')
        missing = hd.get("not_detected") or []
        note = (f'<p class="fine">Not visible on this photo: {_e(", ".join(missing))}.</p>'
                if missing else "")
        blocks += (f'<h4>{hand.title()} hand</h4>'
                   f'<ul class="palm-points">{rows}</ul>{note}')
    if not blocks:
        return ""
    return f"""
<details class="workings workings-main">
  <summary>The line-by-line working — every numbered point on both hands</summary>
  <div class="workings-body">
    <p>Each dot on the photographs above carries a number. This is what was
    read at each one.</p>
    {blocks}
  </div>
</details>"""


def _locked_preview(*, price: int, n_areas: int, n_ahead: int, n_marks: int,
                    n_points: int) -> str:
    ahead_teaser = (
        f"{n_ahead} dated marking{'s' if n_ahead != 1 else ''} on your major lines."
        if n_ahead else
        "Where your lines still change, and roughly when.")
    points_teaser = (
        f"{n_points} numbered point{'s' if n_points != 1 else ''} across both "
        "hands, each with its own verdict, keyed to the dots on your photographs."
        if n_points else
        "Every line, mount, finger and mark, read one at a time.")
    marks_teaser = (
        f"What each of your {n_marks} mark{'s' if n_marks != 1 else ''} does to "
        "the mount it sits on."
        if n_marks else
        "Any mark on your palm, and what it does to the mount it sits on.")
    rows = [
        ("Why each area reads the way it does",
         f"The working behind all {n_areas} verdict{'s' if n_areas != 1 else ''} above."),
        ("Every dated marking still ahead of you", ahead_teaser),
        ("The line-by-line analysis", points_teaser),
        ("Mount by mount",
         "What the raised and flat mounts add, beyond the lines crossing them."),
        ("Your special marks, explained", marks_teaser),
        ("Remedies keyed to your own hand",
         "Matched to what your palm actually shows, not to your sign."),
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
    <h3>The working and the dates</h3>
    <p>You have the verdict on every area of your life. Unlock why your hands
    say it, and when it happens.</p>
    <a class="cta" href="#unlock" data-unlock="1">Unlock &mdash; &#8377;{price}</a>
  </div>
</section>"""


# ---------------------------------------------------------------------------
# the document
# ---------------------------------------------------------------------------
def render(raw: dict, *, name: str = "Seeker", age: int = 30,
           gender: str = "other", dominant: str = "right",
           paid: bool = False, price: int = 298) -> str:
    """One palm reading, gated. Returns a standalone HTML document."""
    import report_shell as RS

    from .palm_report import _Req, build_scores, palm_opening

    req = _Req({"name": name, "age": age, "gender": gender, "dominant": dominant})
    first = _first(name)

    conf = raw.get("confluence") or {}
    dom_key = conf.get("dominant_hand") or dominant
    dom = raw.get(dom_key) or raw.get("right") or raw.get("left") or {}

    aspects = conf.get("life_aspects") or []
    aspects_by_key = {a.get("key"): a for a in aspects}

    # Driven off the dominant hand's checklist rather than confluence
    # `predictions`, which drops the `kind` — without it the mounts, fingers,
    # thumb and hand shape have nowhere to go and fall out of both halves.
    dom_items = dom.get("numbered_checklist") or []
    ahead = _ahead(dom_items, age)
    n_points = sum(len((raw.get(h) or {}).get("numbered_checklist") or [])
                   for h in ("left", "right"))
    n_marks = len((dom.get("features") or {}).get("special_marks") or [])

    cards = "".join(_aspect_card(a, paid=paid) for a in aspects
                    if (a.get("points") or a.get("summary")))

    scores = build_scores(dom, aspects_by_key)
    opening = palm_opening(req, dom)

    if paid:
        tail = (_timeline_ahead(ahead) + _mounts(conf, dom_items)
                + _marks(dom, conf, paid=True)
                + _workings(raw))
    else:
        locked_ahead = ""
        if ahead:
            locked_ahead = (
                f'<div class="card"><div class="when locked-inline">'
                f'<span class="lockicon">&bull;</span> {len(ahead)} further dated '
                f'marking{"s" if len(ahead) != 1 else ""} sit ahead of age {age} on '
                f'your lines. They are in the full reading.</div></div>')
        tail = (locked_ahead + _marks(dom, conf, paid=False)
                + _locked_preview(price=price, n_areas=len(aspects),
                                  n_ahead=len(ahead), n_marks=n_marks,
                                  n_points=n_points))

    hand_type = ((dom.get("features") or {}).get("morphology") or {}).get("hand_type")
    sub = f"{age} years · {dom_key}-dominant · both palms analysed"
    if hand_type:
        sub += f" · {hand_type} hand"

    body = (_photos(raw, dom_key)
            + _quality(dom)
            + _scores(scores)
            + _opening(opening)
            + '<h3 class="sec">Every area of your life, and which way it leans</h3>'
              '<p class="sec-note">Ordered as the classical texts order them. The '
              'strength badge is how many independent signs in your hands agree.</p>'
            + cards
            + _hands_compare(conf)
            + _read_to_today(dom_items, first=first, age=age)
            + tail)

    return RS.page(
        f"{first} — your hands", body,
        eyebrow=("Palm reading · unlocked" if paid
                 else "Palm reading · your hands, and what each area says"),
        heading=f"{first}, here is what your hands are carrying.",
        sub=sub)
