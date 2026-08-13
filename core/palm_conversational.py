"""The palm reading, written the way a palmist gives it.

This renderer replaced a text-only prose page. That page read well and said
almost nothing: it never showed the customer's own photographs, never named a
single line or mark, and reached for temperament language where a palmist would
have pointed at the hand and said what was there.

So the shape here follows a reading given across a table. The photographs come
first, with the traced lines on them. Then the hand itself — shape, thumb, the
four major lines, the mounts, the marks — each one stated as a sign, a reading,
and where the sign is difficult, what to do about it. The dated markings come
next, split at the reader's own age. The life areas and the LLM's prose sit on
top of that evidence rather than in place of it.

Everything deterministic comes from `palm_api.palmist_voice`, which only speaks
about measurements the CV actually produced.
"""

from __future__ import annotations

import html as _html
import re
from typing import Any, Iterable

from .palm_cards import _photos, _hand_for_customer_filter, _filter_customer_numbered


def _e(value: Any) -> str:
    return _html.escape(str(value or ""), quote=True)


_TITLE = {
    "character": "Character & Temperament",
    "mind": "Mind & Intellect",
    "love": "Relationships & Emotions",
    "career": "Career & Direction",
    "wealth": "Money & Resources",
    "health": "Health & Vitality",
}

_HAND_ROLE = {
    True: "your active hand — what you have made of yourself",
    False: "your passive hand — what you were born with",
}


def _sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if text and text[-1] not in ".!?":
        text += "."
    return text


# ---------------------------------------------------------------------------
# one reading, as a row
# ---------------------------------------------------------------------------
def _reading_row(reading: Any, *, both: bool = False) -> str:
    """Sign → reading → what to do, in that order. The palmist's sequence."""
    tone = reading.tone if reading.tone in ("strong", "care") else "steady"
    tag = {"strong": "A strength", "care": "Needs care"}.get(tone, "")
    pill = (f'<span class="pv-pill {tone}">{_e(tag)}</span>' if tag else "")
    agree = ('<span class="pv-both">&#10003; in both hands</span>' if both else "")
    when = ""
    if getattr(reading, "age_range", None):
        low, high = reading.age_range
        when = f'<span class="pv-when">ages {low}&ndash;{high}</span>'
    elif getattr(reading, "age", None):
        when = f'<span class="pv-when">around age {reading.age}</span>'
    remedy = ""
    if reading.remedy:
        remedy = (f'<p class="pv-do"><span class="ev-label">What to do</span> '
                  f"{_e(_sentence(reading.remedy))}</p>")
    return f"""
<div class="pv-row {tone}">
  <div class="pv-head"><b>{_e(reading.feature)}</b>{pill}{agree}{when}</div>
  <p class="pv-sign">{_e(_sentence(reading.sign))}</p>
  <p class="pv-means">{_e(_sentence(reading.means))}</p>
  {remedy}
</div>"""


def _observation(reading: Any, *, both: bool = False) -> str:
    """One more thing the same line says, under a heading already written."""
    tone = reading.tone if reading.tone in ("strong", "care") else "steady"
    tag = {"strong": "A strength", "care": "Needs care"}.get(tone, "")
    marks = (f'<span class="pv-pill {tone}">{_e(tag)}</span>' if tag else "")
    if both:
        marks += '<span class="pv-both">&#10003; in both hands</span>'
    if getattr(reading, "age_range", None):
        low, high = reading.age_range
        marks += f'<span class="pv-when">ages {low}&ndash;{high}</span>'
    elif getattr(reading, "age", None):
        marks += f'<span class="pv-when">around age {reading.age}</span>'
    remedy = ""
    if reading.remedy:
        remedy = (f'<p class="pv-do"><span class="ev-label">What to do</span> '
                  f"{_e(_sentence(reading.remedy))}</p>")
    return (f'<div class="pv-obs {tone}">'
            f'<p class="pv-sign">{_e(_sentence(reading.sign))}{marks}</p>'
            f'<p class="pv-means">{_e(_sentence(reading.means))}</p>'
            f"{remedy}</div>")


def _rows(readings: Iterable[Any], agree: set[str] | None = None) -> str:
    """Group by feature so a line is named once and then read.

    A palmist says "your head line" and then tells you the three things it
    shows. Printing the name again above every observation turned the reading
    into an inventory — "Head line", "Head line", "Head line" down the page.
    """
    agree = agree or set()
    groups: list[tuple[str, list[Any]]] = []
    for reading in readings:
        if groups and groups[-1][0] == reading.feature:
            groups[-1][1].append(reading)
        else:
            groups.append((reading.feature, [reading]))

    out: list[str] = []
    for feature, items in groups:
        if len(items) == 1:
            out.append(_reading_row(items[0], both=items[0].key in agree))
            continue
        tones = {r.tone for r in items}
        tone = "care" if "care" in tones else (
            "strong" if "strong" in tones else "steady")
        body = "".join(_observation(r, both=r.key in agree) for r in items)
        out.append(f'<div class="pv-row {tone}">'
                   f'<div class="pv-head"><b>{_e(feature)}</b></div>'
                   f"{body}</div>")
    return "".join(out)


def _section(anchor: str, title: str, note: str, body: str,
             *, nav: str = "") -> str:
    if not body.strip():
        return ""
    note_html = f'<p class="sec-note">{_e(note)}</p>' if note else ""
    short = f' data-nav="{_e(nav)}"' if nav else ""
    return (f'<section class="conv-block" id="{_e(anchor)}">'
            f"<h2{short}>{_e(title)}</h2>{note_html}{body}</section>")


# ---------------------------------------------------------------------------
# photographs and photo honesty
# ---------------------------------------------------------------------------
_GRADE_NOTE = {
    "good": "clear enough to read the fine marks and to place ages on the lines",
    "fair": "clear enough for the main lines, but not for fine marks — the age "
            "windows on this hand are widened rather than sharpened",
    "poor": "too unclear for fine marks or for age positions; only the broad "
            "pattern is read from this hand",
}


def _photo_note(raw: dict) -> str:
    rows = ""
    for hand in ("left", "right"):
        block = raw.get(hand) or {}
        if not block:
            continue
        grade = str(((block.get("features") or {}).get("quality") or {})
                    .get("grade") or "fair").lower()
        rows += (f'<li><b>{hand.title()} hand</b> — photo grade {_e(grade)}: '
                 f"{_e(_GRADE_NOTE.get(grade, _GRADE_NOTE['fair']))}.</li>")
    if not rows:
        return ""
    return (f'<div class="card"><div class="ev-label">What each photograph '
            f'allows</div><ul class="pv-plain">{rows}</ul>'
            f'<p class="fine">A palmist holds the hand and turns it to the light. '
            f"Working from a photograph, we say plainly what the photograph will "
            f"and will not support rather than guessing past it.</p></div>")


# ---------------------------------------------------------------------------
# marks
# ---------------------------------------------------------------------------
def _hand_grade(raw: dict, hand: str) -> str:
    return str((((raw.get(hand) or {}).get("features") or {}).get("quality") or {})
               .get("grade") or "").lower()


def _remedy_source(raw: dict, dom_key: str) -> tuple[str, dict]:
    """Pick the hand a gemstone or practice may be prescribed from.

    A remedy reads off the mounts, and a mount can only be measured in a clear
    photograph. When the active hand is the blurred one, withholding every
    remedy is the wrong answer — but so is prescribing from the passive hand
    alone, which can contradict the reading the active hand just gave. The
    mounts that both hands agree on are the ones that survive.
    """
    if _hand_grade(raw, dom_key) == "good":
        return dom_key, dict(raw.get(dom_key) or {})
    other = next((h for h in ("right", "left")
                  if h != dom_key and _hand_grade(raw, h) == "good"), "")
    if not other:
        return dom_key, dict(raw.get(dom_key) or {})

    clear = dict(raw.get(other) or {})
    feats = dict(clear.get("features") or {})
    dom_mounts = (((raw.get(dom_key) or {}).get("features") or {}).get("mounts") or {})
    feats["mounts"] = {k: v for k, v in (feats.get("mounts") or {}).items()
                       if str(dom_mounts.get(k) or "").lower() == str(v or "").lower()}
    clear["features"] = feats
    return other, clear


def _marks_section(readings: dict, raw: dict) -> str:
    rows = ""
    for hand in ("right", "left"):
        hr = readings.get(hand)
        if not hr:
            continue
        for mark in hr.marks:
            rows += _reading_row(mark)
    blocked = [h for h in ("right", "left")
               if readings.get(h) and not readings[h].marks_allowed]
    note = ""
    if blocked:
        which = " and ".join(h.title() for h in blocked)
        note = (f'<p class="fine">Fine marks are not reported from your '
                f"{_e(which)} hand photograph — at that grade a shadow and a star "
                f"look alike, and a mark invented from a blur is worse than no "
                f"mark at all. Retake that hand straight-on in bright, even "
                f"light to have it read.</p>")
    if not rows and not note:
        return ""
    if not rows:
        rows = ('<p class="pv-means">No special mark was resolved clearly enough '
                "to report.</p>")
    return _section(
        "sec-marks", "The special marks on your hands",
        "A mark modifies the mount beneath it. It is read together with the "
        "lines around it, never on its own.",
        f'<div class="card">{rows}{note}</div>', nav="Special marks")


# ---------------------------------------------------------------------------
# dated markings
# ---------------------------------------------------------------------------
def _split_prediction(text: str) -> tuple[str, str]:
    parts = re.split(r"(?i)(?:\r?\n|\s+)Why:\s*", str(text or ""), maxsplit=1)
    head = parts[0].strip()
    why = parts[1].strip() if len(parts) == 2 else ""
    return head, why


def _timeline(conf: dict, age: int, *, ahead: bool) -> str:
    rows = ""
    for pred in conf.get("predictions") or []:
        when = pred.get("age")
        if not isinstance(when, int):
            continue
        if ahead != (when > age):
            continue
        head, why = _split_prediction(pred.get("text"))
        if not head:
            continue
        span = pred.get("age_range") or []
        window = (f"ages {span[0]}&ndash;{span[1]}"
                  if len(span) == 2 and span[1] > span[0] else f"around age {when}")
        rows += (f'<li><div class="tl-when">{window}</div>'
                 f'<div class="tl-body"><b>{_e(pred.get("title"))}</b>'
                 f'<p class="pv-means">{_e(_sentence(head))}</p>'
                 + (f'<p class="pv-sign">Read from {_e(why)}.</p>' if why else "")
                 + "</div></li>")
    if not rows:
        return ""
    return f'<ol class="timeline">{rows}</ol>'


# ---------------------------------------------------------------------------
# problems
# ---------------------------------------------------------------------------
def _problem_section(readings: dict, dom_key: str, *, paid: bool) -> str:
    hr = readings.get(dom_key)
    if not hr:
        return ""
    problems = hr.problems()
    if not problems:
        return _section(
            "sec-care", "What needs care", "",
            '<div class="card"><p class="pv-means">Nothing in your dominant hand '
            "reads as a warning. The lines that are marked in your hand are "
            "marked for strength, not for trouble.</p></div>")
    shown = problems if paid else problems[:1]
    rows = "".join(
        f'<li><b>{_e(p.feature)}</b> — {_e(_sentence(p.means))}'
        + (f'<p class="pv-do"><span class="ev-label">What to do</span> '
           f"{_e(_sentence(p.remedy))}</p>" if p.remedy else "")
        + "</li>" for p in shown)
    locked = ""
    if not paid and len(problems) > 1:
        rest = len(problems) - 1
        plural = (f"{rest} further signs in your hand each need an answer of "
                  f"their own" if rest != 1 else
                  "One further sign in your hand needs an answer of its own")
        locked = (f'<div class="when locked-inline"><span class="lockicon">'
                  f"&bull;</span> {plural}. Each is named with its remedy in the "
                  f"full reading.</div>")
    return _section(
        "sec-care", "What needs care, and what to do about it",
        "Every sign below is one your hand actually carries. None of it is fixed "
        "— a palmist points at the difficulty precisely so it can be worked on.",
        f'<div class="card"><ul class="pv-care">{rows}</ul>{locked}</div>',
        nav="What needs care")


# ---------------------------------------------------------------------------
# the document
# ---------------------------------------------------------------------------
def render(
    raw: dict,
    *,
    name: str = "Seeker",
    age: int = 30,
    gender: str = "other",
    dominant: str = "right",
    paid: bool = False,
    price: int = 298,
    prose: dict | None = None,
) -> str:
    del gender  # reserved for future gendered phrasing
    import report_shell as RS
    from palm_api import palmist_voice as PVoice

    prose = prose if isinstance(prose, dict) else {}
    first = (name or "Seeker").split()[0]
    conf = raw.get("confluence") or {}
    dom_key = conf.get("dominant_hand") or dominant
    other_key = "left" if dom_key == "right" else "right"
    aspects = conf.get("life_aspects") or []
    aspect_by_key = {str(a.get("key") or ""): a for a in aspects if isinstance(a, dict)}

    readings = {}
    for hand in ("left", "right"):
        if raw.get(hand):
            readings[hand] = PVoice.read_hand(raw[hand], hand=hand)
    dom_reading = readings.get(dom_key) or readings.get(other_key)
    if dom_reading is None:
        dom_reading = PVoice.HandReading(hand=dom_key)
    other_reading = readings.get(other_key)

    # A sign carried by both hands is the one worth trusting: the passive hand
    # says it was given, the active hand says it is still true. Hand shape and
    # the absence of a line are excluded — "in both hands" says nothing about a
    # feature that could hardly differ, or about something that is not there.
    agree: set[str] = set()
    if other_reading:
        shared = {r.key for r in dom_reading.all()} & {r.key for r in other_reading.all()}
        agree = {k for k in shared
                 if "_no_" not in k and not k.startswith(("hand_type", "thumb", "index", "ring"))}

    personality = str(prose.get("personality") or "").strip()
    current_phase = str(prose.get("current_phase") or "").strip()
    hardest = str(prose.get("hardest_area_note") or "").strip()
    mind_now = [str(x).strip() for x in (prose.get("mind_now") or []) if str(x).strip()]
    why_now = str(prose.get("why_now") or "").strip()
    hand_note = str(prose.get("hand_contrast_note") or "").strip()
    areas = prose.get("areas") if isinstance(prose.get("areas"), dict) else {}

    blocks: list[str] = []

    # 1 — the photographs
    blocks.append(_section(
        "sec-hands", "Your hands, and what I traced on them",
        "",
        _photos(raw, dom_key) + _photo_note(raw), nav="Your hands"))

    # 2 — the hand itself
    shape_rows = _rows(dom_reading.shape, agree)
    opening = f"<p>{_e(personality)}</p>" if personality else ""
    blocks.append(_section(
        "sec-hand", "The hand itself",
        f"Shape, thumb and finger set — {_HAND_ROLE[True]}.",
        opening + (f'<div class="card">{shape_rows}</div>' if shape_rows else "")))

    # 3 — the major lines
    line_rows = _rows(dom_reading.lines, agree)
    blocks.append(_section(
        "sec-lines", "Your four major lines",
        "Each line is stated as it appears in your palm, then read the way the "
        "classical texts read that appearance.",
        f'<div class="card">{line_rows}</div>' if line_rows else ""))

    # 4 — where the hands place you now
    now_body = ""
    if current_phase:
        now_body += f"<p>{_e(current_phase)}</p>"
    if hardest:
        now_body += f'<p class="hardest">{_e(hardest)}</p>'
    if mind_now:
        items = "".join(f"<li>{_e(line)}</li>" for line in mind_now[:3])
        now_body += (
            '<p class="sec-note">These are what your hands make likely right '
            "now. They are read from the palm, not known about your life.</p>"
            f'<ul class="conv-mind">{items}</ul>')
    if why_now:
        now_body += f"<p>{_e(why_now)}</p>"
    blocks.append(_section("sec-now", "Where your hands place you now", "", now_body))

    # 5 — read to today
    behind = _timeline(conf, age, ahead=False)
    if behind:
        blocks.append(_section(
            "sec-behind", f"{first}, check these against the years you have lived",
            "These ages come from where the marking falls along the line, using "
            "the seven-year division the classical texts time by. Treat each one "
            "as a life stage, not a date.",
            behind, nav="Read to today"))

    if paid:
        # 6 — the minor lines
        minor_rows = _rows(dom_reading.minor, agree)
        blocks.append(_section(
            "sec-minor", "The smaller lines",
            "The minor lines qualify the major ones. Their absence is read as "
            "carefully as their presence.",
            f'<div class="card">{minor_rows}</div>' if minor_rows else ""))

        # 7 — mounts
        mount_rows = _rows(dom_reading.mounts, agree)
        blocks.append(_section(
            "sec-mounts", "Mount by mount",
            "The raised and flat pads say where your energy actually goes, "
            "independently of the lines crossing them.",
            f'<div class="card">{mount_rows}</div>' if mount_rows else ""))

        # 8 — marks
        blocks.append(_marks_section(readings, raw))

        # 9 — still ahead
        ahead = _timeline(conf, age, ahead=True)
        if ahead:
            blocks.append(_section(
                "sec-ahead", "What is still ahead of you",
                "Same seven-year division, read forward. An age window is a "
                "stretch to prepare for, not an appointment.",
                ahead))

        # 10 — life areas
        rows = []
        for key in [str(a.get("key") or "") for a in aspects if isinstance(a, dict)]:
            block = areas.get(key) or {}
            if not isinstance(block, dict):
                continue
            outlook = str(block.get("outlook") or "").strip()
            if not outlook:
                continue
            title = _TITLE.get(key) or str(
                (aspect_by_key.get(key) or {}).get("title") or key)
            strength = str((aspect_by_key.get(key) or {}).get("strength") or "moderate")
            timing = str(block.get("timing") or "").strip()
            manifestation = str(block.get("manifestation") or "").strip()
            remedy = str(block.get("remedy") or "").strip()
            passage = " ".join(x for x in (outlook, timing, manifestation) if x)
            evidence = "".join(
                f"<li>{_e(str(p.get('text') or '').strip())}</li>"
                for p in ((aspect_by_key.get(key) or {}).get("points") or [])
                if str(p.get("text") or "").strip())
            bits = [f"<p>{_e(passage)}</p>"]
            if remedy:
                bits.append(
                    f'<p class="pv-do"><span class="ev-label">What to do</span> '
                    f"{_e(remedy)}</p>")
            if evidence:
                bits.append(
                    f'<details class="technical-evidence"><summary>The signs this '
                    f"reads from</summary><ul>{evidence}</ul></details>")
            rows.append(
                f'<article class="card conv-area">'
                f'<div class="card-top"><span class="area">{_e(title)}</span>'
                f'<span class="pill mixed">{_e(strength.title())}</span></div>'
                f'{"".join(bits)}</article>')
        if rows:
            blocks.append(_section(
                "sec-areas", "Each part of your life",
                "What the hand says for this area, when it moves, and what helps "
                "when it needs care.",
                "".join(rows)))

    # 11 — the two hands against each other
    contrast = ""
    if hand_note:
        contrast += f"<p>{_e(hand_note)}</p>"
    if other_reading:
        only_active = [r for r in dom_reading.all()
                       if r.key not in agree and r.tone != "neutral"][:4]
        only_innate = [r for r in other_reading.all()
                       if r.key not in agree and r.tone != "neutral"][:4]
        cols = ""
        if only_innate:
            cols += ('<div class="pv-col"><div class="ev-label">Born with, on your '
                     f'{_e(other_key)} hand</div><ul class="pv-plain">'
                     + "".join(f"<li>{_e(r.feature)} — {_e(r.sign)}</li>"
                               for r in only_innate) + "</ul></div>")
        if only_active:
            cols += ('<div class="pv-col"><div class="ev-label">Made yourself, on '
                     f'your {_e(dom_key)} hand</div><ul class="pv-plain">'
                     + "".join(f"<li>{_e(r.feature)} — {_e(r.sign)}</li>"
                               for r in only_active) + "</ul></div>")
        if cols:
            contrast += f'<div class="card pv-cols">{cols}</div>'
    blocks.append(_section(
        "sec-contrast", "What you were born with, and what you have made of it",
        "The passive hand is the hand you were given. The active hand is what you "
        "have done with it. Where they differ is the most personal part of any "
        "reading.",
        contrast, nav="Born with vs made"))

    # 12 — problems and remedies
    blocks.append(_problem_section(readings, dom_key, paid=paid))

    if paid:
        try:
            from .palm_cards import _remedies, _workings
            # A gemstone rule reads off the mounts, and a mount is only
            # measurable in a clear photograph. When the active hand is the
            # blurred one, the remedies come from the hand that can carry them
            # rather than being withheld from both.
            source, block = _remedy_source(raw, dom_key)
            note = ""
            if source != dom_key:
                note = (f'<p class="sec-note">Your {_e(dom_key)} hand photograph '
                        f"is not clear enough to prescribe from, so these are read "
                        f"from your {_e(source)} hand — and only where both hands "
                        f"show the same thing.</p>")
            remedies = _remedies(block, conf, paid=True)
            if remedies and note:
                remedies = remedies.replace("</h3>", "</h3>" + note, 1)
            if not remedies:
                # Silence here would read as an omission. A gem or a practice is
                # prescribed only where a classical rule fires on something
                # measured; when none does, saying so is the honest answer.
                remedies = (
                    '<h3 class="sec" data-nav="Remedies">Remedies for your hand'
                    "</h3>"
                    '<div class="card"><p class="pv-means">No classical gem or '
                    "practice is indicated for your hands. The rules that "
                    "prescribe one fire on a mount that is markedly flat or "
                    "markedly full, and yours read within the ordinary range. "
                    "What your hands do ask for is in the steps above, which "
                    "cost nothing.</p></div>")
            blocks.append(remedies)
            blocks.append(_workings(raw))
        except Exception:  # noqa: BLE001
            pass
    else:
        n_points = sum(
            len(_filter_customer_numbered(_hand_for_customer_filter(raw, h)))
            for h in ("left", "right"))
        ahead_n = len([p for p in (conf.get("predictions") or [])
                       if isinstance(p.get("age"), int) and p["age"] > age])
        blocks.append(f"""
<section class="buy" id="unlock">
  <h3>The rest of the hand</h3>
  <p>You have your photographs, your hand shape and your four major lines.
  The full reading adds the smaller lines, mount by mount, your special marks,
  {_e(ahead_n)} dated marking{'s' if ahead_n != 1 else ''} still ahead of you,
  every life area, the remedies keyed to your own hand, and the point-by-point
  working behind all {_e(n_points)} numbered findings.</p>
  <a class="cta" href="#unlock" data-unlock="1">Unlock full reading · ₹{_e(price)}</a>
</section>""")

    body = "".join(b for b in blocks if b)
    extra = """
.conv-block{margin:26px 0}
.conv-block h2{font-family:Fraunces,Georgia,serif;font-size:1.3rem;margin:0 0 6px;
color:#1f2430;font-weight:600}
.conv-block>p{margin:0 0 12px;line-height:1.58;color:#2c3140;font-size:.95rem}
.conv-block .hardest{font-weight:600}
.conv-block .sec-note{font-size:.83rem;color:#6b7280;margin:0 0 14px}
.conv-mind{margin:0 0 12px;padding-left:18px}
.conv-mind li{margin:0 0 7px;line-height:1.5;color:#2c3140;font-size:.95rem}
.conv-area{margin:14px 0}
.pv-row{padding:14px 0;border-top:1px solid var(--line)}
.pv-row:first-child{border-top:0;padding-top:2px}
.pv-head{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:6px}
.pv-head b{font-size:.95rem}
.pv-pill{font-size:.62rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
padding:2px 8px;border-radius:99px}
.pv-pill.strong{background:#e4f2ea;color:var(--up)}
.pv-pill.care{background:#fbf1de;color:var(--mixed)}
.pv-both{font-size:.66rem;font-weight:600;color:var(--muted);background:#f1efea;
border-radius:99px;padding:2px 9px}
.pv-when{font-size:.66rem;font-weight:600;color:var(--muted);letter-spacing:.04em;
text-transform:uppercase}
.pv-obs{margin:0 0 12px}
.pv-obs:last-child{margin-bottom:0}
.pv-obs .pv-sign{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.pv-sign{margin:0 0 6px;font-size:.86rem;color:#5d6373;font-style:italic}
.pv-means{margin:0;font-size:.93rem;line-height:1.55;color:#2c3140}
.pv-do{margin:8px 0 0;background:#f6f4ef;border-radius:10px;padding:10px 12px;
font-size:.88rem;line-height:1.5;color:#3d4250}
.pv-do .ev-label{display:block;margin-bottom:3px;color:var(--mixed)}
.pv-care{margin:0;padding-left:18px}
.pv-care li{margin:0 0 12px;font-size:.93rem;line-height:1.55}
.pv-plain{margin:0;padding-left:18px;font-size:.88rem;color:#3d4250}
.pv-plain li{margin:0 0 6px;line-height:1.5}
.pv-cols{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.pv-row.care{border-left:3px solid var(--mixed);padding-left:12px;margin-left:-15px}
@media(max-width:520px){.pv-cols{grid-template-columns:1fr}}
"""
    hand_type = ((( raw.get(dom_key) or {}).get("features") or {})
                 .get("morphology") or {}).get("hand_type")
    sub = f"{age} years · {dom_key}-dominant · both palms read"
    if hand_type:
        sub += f" · {hand_type} hand"
    return RS.page(
        f"{first} — your hands",
        body + f"<style>{extra}</style>",
        eyebrow=("Palm reading · unlocked" if paid else "Palm reading"),
        heading=f"{first}, here is what your hands are carrying.",
        sub=sub)
