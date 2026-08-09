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
still ahead, the mounts, what the marks mean, hand-specific remedies (do/don't),
and the numbered points.
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
    # A pair of full-resolution overlays can make an iframe document several
    # megabytes long. Some phone browsers then paint the first image and silently
    # abandon the second. Embed a display-sized JPEG instead; the original stays
    # in object storage for the archive.
    data = p.read_bytes()
    try:
        from io import BytesIO
        from PIL import Image

        with Image.open(BytesIO(data)) as image:
            image = image.convert("RGB")
            image.thumbnail((900, 1200))
            out = BytesIO()
            image.save(out, format="JPEG", quality=82, optimize=True)
            data = out.getvalue()
    except Exception:  # Pillow is optional; a valid original still renders.
        pass
    import base64
    return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")


def _photos(raw: dict, dom_key: str) -> str:
    figs = ""
    for hand in ("left", "right"):
        src = _data_uri((raw.get(hand) or {}).get("overlay_path"))
        role = "dominant — what you have made of it" if hand == dom_key \
            else "innate — what you were handed"
        if src:
            visual = (f'<img src="{src}" alt="{hand} palm with the '
                      f'detected lines drawn on"/>')
        else:
            # Do not make a missing overlay look like a missing upload. The
            # reader needs a visible explanation and a retake path, not a
            # mysteriously incomplete two-hand report.
            visual = (f'<div class="palm-img-missing" role="img" aria-label="'
                      f'{hand} palm overlay could not be prepared">Annotated '
                      f'{hand} palm image unavailable. Please retake this hand '
                      f'in bright, even light.</div>')
        figs += (f'<figure>{visual}'
                 f'<figcaption>{hand.title()} hand · {role}</figcaption></figure>')
    return f"""
<div class="palm-shots">
  <div class="ev-label">Your palms, as the engine read them</div>
  <div class="palm-imgs">{figs}</div>
  <p class="fine">These are your own photographs with the lines this reading is
  built from drawn on top. If a hand is unavailable or a line looks wrong,
  retake that photo in bright, even light and run the reading again.</p>
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
        # The life-area cards already state the stable traits. This comparison
        # earns its place only where the innate and developed hands differ.
        if not li.get("statement") or li.get("agreement") == "reinforced":
            continue
        rows += (f'<li><b>{_e(li.get("title"))}</b>'
                 f'{_scenario_why_html(li.get("statement") or "")}</li>')
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


def _scenario_why_html(text: str, *, title: str = "") -> str:
    """Turn 'scenario\\nWhy: backing' (or '… Why: …') into styled HTML chips."""
    raw = (text or "").strip()
    if not raw:
        return ""
    # Split on Why even mid-paragraph ("…now. Why: mark on …") — common in
    # palm confluence statements that were never HTML-formatted.
    m = re.split(r"(?i)(?:\r?\n|\s+)Why:\s*", raw, maxsplit=1)
    if len(m) == 2:
        scenario, why = m[0].strip(), m[1].strip()
    elif re.match(r"(?i)^Why:\s*", raw):
        scenario, why = "", re.sub(r"(?i)^Why:\s*", "", raw).strip()
    else:
        scenario, why = raw, ""
    # Drop a trailing period dangling before Why was chopped off.
    scenario = scenario.rstrip()
    head = ""
    if title and scenario:
        head = f'<p class="pred-scenario"><b>{_e(title)}</b> — {_e(scenario)}</p>'
    elif title and not scenario:
        head = f'<p class="pred-scenario"><b>{_e(title)}</b></p>'
    elif scenario:
        head = f'<p class="pred-scenario">{_e(scenario)}</p>'
    why_html = (f'<p class="pred-why"><b>Why:</b> {_e(why)}</p>' if why else "")
    return head + why_html


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

    rows = "".join(
        f'<li><span class="tick">&#10003;</span>'
        f'<div><b>{_e(i.get("title"))}</b>{_scenario_why_html(_verdict(i))}</div></li>'
        for i in shape)
    rows += "".join(
        f'<li><span class="tick">&#10003;</span>'
        f'<div><b>{_e(i.get("title"))}, around age {_e(_est_age(i))}</b>'
        f'{_scenario_why_html(_verdict(i))}</div></li>'
        for i in behind)

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
        from palm_api import palm_voice as PV
        return PV._mount_name((zone or "palm").lower())
    except Exception:  # noqa: BLE001
        return "your palm"


def _marks(dom: dict, conf: dict, *, paid: bool) -> str:
    raw_marks = (dom.get("features") or {}).get("special_marks") or []
    if not raw_marks and not (conf.get("marks") or []):
        return ""
    if paid:
        mark_rows = [m for m in (conf.get("marks") or []) if m.get("statement")]
        if mark_rows:
            rows = "".join(
                f'<li>{_scenario_why_html(m.get("statement") or "")}</li>'
                for m in mark_rows)
        else:
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
<div class="card"><ul class="palm-list">{rows}</ul></div>"""

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
  <div class="tl-body"><b>{_e(i.get('title'))}</b>
  {_scenario_why_html(_verdict(i))}</div>
</li>""" for i in ahead)
    return f"""
<h3 class="sec">What is still ahead of you</h3>
<p class="sec-note">Dated by where the marking falls on the line, not by a
calendar. Treat the age as a window, not a day.</p>
<ol class="timeline">{rows}</ol>"""


def _mounts(conf: dict, items: List[dict]) -> str:
    rows = ""
    seen: set[str] = set()

    def add(text: str) -> bool:
        key = re.sub(r"\W+", " ", text.lower()).strip()
        if not key or key in seen:
            return False
        seen.add(key)
        return True

    for i in items:
        if i.get("kind") != "mount" or not _verdict(i):
            continue
        verdict = _verdict(i)
        if not add(verdict):
            continue
        rows += f'<li>{_scenario_why_html(verdict)}</li>'
    for mount in conf.get("mounts") or []:
        statement = str(mount.get("statement") or "")
        if add(statement):
            rows += f'<li>{_scenario_why_html(statement)}</li>'
    if not rows:
        return ""
    return f"""
<h3 class="sec">Mount by mount</h3>
<p class="sec-note">The raised and flat parts of the palm say where your energy
actually goes, independently of the lines crossing them.</p>
<div class="card"><ul class="palm-list">{rows}</ul></div>"""


# Classical palm upaya keyed to detected mounts / marks (no birth chart needed).
_MOUNT_LABEL = {
    "jupiter": "ambition / authority (Jupiter mount)",
    "saturn": "discipline / solitude (Saturn mount)",
    "apollo": "recognition / creative work (Sun mount)",
    "sun": "recognition / creative work (Sun mount)",
    "mercury": "communication / business (Mercury mount)",
    "mars": "courage / temper (Mars mount)",
    "venus": "affection / vitality (Venus mount)",
    "moon": "imagination / travel (Moon mount)",
    "luna": "imagination / travel (Moon mount)",
}

_STRENGTHEN = {
    "jupiter": ("Topaz (or yellow sapphire) on the index finger, first worn on a Thursday",
                "Speak one ambition out loud this week instead of waiting to be invited."),
    "saturn": ("A simple iron ring on the middle finger, Saturdays",
               "Finish one dull, deferred duty before noon for seven days."),
    "apollo": ("Ruby or citrine on the ring finger, Sundays",
               "Show one piece of unfinished creative work to someone who will tell you the truth."),
    "sun": ("Ruby or citrine on the ring finger, Sundays",
            "Show one piece of unfinished creative work to someone who will tell you the truth."),
    "mercury": ("Emerald (or green glass trial) on the little finger, Wednesdays",
                "Put the next important deal in writing before you discuss it again."),
    "mars": ("Red coral on the ring finger, Tuesdays — trial for three days",
             "Move hard physical energy before hard words; let the other side speak first once."),
    "venus": ("Diamond or clear zircon on the middle finger, Fridays",
              "Initiate one warm gesture you have been postponing."),
    "moon": ("Pearl (or moonstone) on Monday mornings",
             "Protect sleep and water the week before any travel decision."),
    "luna": ("Pearl (or moonstone) on Monday mornings",
             "Protect sleep and water the week before any travel decision."),
}

_TEMPER = {
    "jupiter": "Do not run every room this month — ask before you direct.",
    "saturn": "Do not take on another solitary burden; hand one duty off.",
    "apollo": "Do not chase praise at the cost of finishing the work.",
    "sun": "Do not chase praise at the cost of finishing the work.",
    "mercury": "Do not talk your way into a commitment you have not written down.",
    "mars": "Do not start the fight. Wear iron if temper keeps rising — use it to cool, not to win.",
    "venus": "Do not overspend on comfort or romance while other lines are under strain.",
    "moon": "Do not relocate or travel on impulse for the next fortnight.",
    "luna": "Do not relocate or travel on impulse for the next fortnight.",
}

_AUSPICIOUS_MARKS = frozenset({"fish", "trident", "triangle", "square", "temple"})
_HARD_MARKS = frozenset({"cross", "island", "grille"})


def _remedies(dom: dict, conf: dict, *, paid: bool = False) -> str:
    """Do / don't remedies from mounts + special marks — paid detail, free tease."""
    feats = dom.get("features") or {}
    mounts = feats.get("mounts") or {}
    raw_marks = feats.get("special_marks") or []
    if not raw_marks and conf.get("marks"):
        # conf marks are statements; keep titles for free teaser count only
        pass

    dos: List[str] = []
    donts: List[str] = []
    seen: set[str] = set()

    def _push(bucket: List[str], line: str) -> None:
        key = re.sub(r"\W+", " ", line.lower()).strip()
        if not key or key in seen:
            return
        seen.add(key)
        bucket.append(line)

    for mount, level in mounts.items():
        m = str(mount).lower()
        lv = str(level or "").lower()
        label = _MOUNT_LABEL.get(m, m)
        if lv == "flat" and m in _STRENGTHEN:
            gem, act = _STRENGTHEN[m]
            _push(dos, f"Strengthen {label}: {gem}. Practical: {act}")
        elif lv == "prominent" and m in _TEMPER:
            _push(donts, f"{_TEMPER[m]} (your {label} already runs high.)")
            if m in ("mars",):
                gem, _ = _STRENGTHEN.get(m, ("", ""))
                if gem:
                    _push(dos, f"If temper keeps rising: {gem} — to cool the mount, not to sharpen it.")

    for mark in raw_marks:
        kind = str(mark.get("type") or mark.get("kind") or "").lower()
        zone = str(mark.get("zone") or mark.get("mount") or "palm").lower()
        title = mark.get("title") or kind.title() or "Mark"
        area = _MOUNT_LABEL.get(zone, _mark_zone_plain(zone))
        if kind in _AUSPICIOUS_MARKS:
            _push(dos,
                  f"Protect the {title} on {area}: keep that part of life steady — "
                  f"do not disrupt it for a short-term gain.")
            if zone in _STRENGTHEN:
                gem, _ = _STRENGTHEN[zone]
                _push(dos, f"Optional support for that mount: {gem}.")
        elif kind in _HARD_MARKS:
            _push(donts,
                  f"Do not force the area of the {title} on {area} — reduce load there "
                  f"for a season rather than pushing through.")
        elif kind == "star":
            _push(dos, f"A star on {area} can open suddenly — accept clean offers you can verify.")
            _push(donts, f"Do not rush the first glittering offer near the star on {area}; verify before you commit.")
        elif kind == "circle":
            _push(dos, f"Honour a quiet daily practice — the circle on {area} prefers consistency over display.")
            _push(donts, "Do not turn the spiritual thread into a public performance.")

    # Cap so the section stays readable
    dos, donts = dos[:6], donts[:6]
    n = len(dos) + len(donts)
    if n == 0:
        if paid:
            return ""
        return """
<h3 class="sec">Remedies for your hand</h3>
<p class="sec-note">Matched to mounts and marks — not to a generic sign.</p>
<div class="card"><div class="when locked-inline"><span class="lockicon">&bull;</span>
What to strengthen, what to temper, and any gem or metal tied to your own mounts
are in the full reading.</div></div>"""

    if not paid:
        return f"""
<h3 class="sec">Remedies for your hand</h3>
<p class="sec-note">Matched to mounts and marks — not to a generic sign.</p>
<div class="card"><div class="when locked-inline"><span class="lockicon">&bull;</span>
{n} hand-specific step{'s' if n != 1 else ''} (what to do, what to avoid, and any
stone or metal keyed to your mounts) sit in the full reading.</div></div>"""

    do_html = "".join(f"<li class=\"stone up\"><div class=\"stone-top\"><b>Do</b>"
                      f"<span class=\"stone-verdict\">Wear / practise</span></div>"
                      f"<div class=\"stone-detail\">{_e(x)}</div></li>" for x in dos)
    dont_html = "".join(f"<li class=\"stone down\"><div class=\"stone-top\"><b>Don't</b>"
                        f"<span class=\"stone-verdict\">Avoid</span></div>"
                        f"<div class=\"stone-detail\">{_e(x)}</div></li>" for x in donts)
    return f"""
<section class="remedy-card">
  <h3 class="sec">Remedies for your hand</h3>
  <p class="sec-note">Built from what your mounts and marks actually show — green to
  strengthen, red to hold back.</p>
  {f'''<div class="stones-group up">
    <div class="stones-group-label">Do · strengthen and wear</div>
    <ul class="stones">{do_html}</ul>
  </div>''' if do_html else ''}
  {f'''<div class="stones-group down">
    <div class="stones-group-label">Don't · temper and avoid</div>
    <ul class="stones">{dont_html}</ul>
  </div>''' if dont_html else ''}
  <p class="fine">Educational palmistry only. Stones and metals are traditional
  suggestions — trial any gem for a few days and remove it if you feel off.</p>
</section>"""


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
            body = _scenario_why_html(str(verdict))
            if not body:
                body = f'<p>{_e(verdict)}</p>'
            rows += (f'<li><b>Point {_e(num)} — {_e(it.get("title"))}</b>{when}'
                     f'{body}</li>')
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
    <h3>See the pattern beneath the first reading</h3>
    <p>You have the part you can check against your own hands. Unlock the
    supporting signs, forward age windows, marks and hand-specific guidance.</p>
    <a class="cta" href="#unlock" data-unlock="1">Unlock full reading</a>
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
                + _remedies(dom, conf, paid=True)
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
                + _remedies(dom, conf, paid=False)
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
