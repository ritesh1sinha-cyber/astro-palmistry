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
    seen_marks: dict[tuple[str, str], dict] = {}
    for hand in ("right", "left"):
        hr = readings.get(hand)
        if not hr:
            continue
        for mark in hr.marks:
            parts = mark.key.split("_")
            kind = parts[1] if len(parts) > 1 else "mark"
            zone = parts[2] if len(parts) > 2 else "palm"
            k = (kind, zone)
            if k not in seen_marks:
                seen_marks[k] = {"mark": mark, "hands": [hand]}
            else:
                if hand not in seen_marks[k]["hands"]:
                    seen_marks[k]["hands"].append(hand)

    rows = ""
    for (kind, zone), item in seen_marks.items():
        mark = item["mark"]
        hands = item["hands"]
        is_both = len(hands) > 1
        tone = mark.tone if mark.tone in ("strong", "care") else "steady"
        tag = {"strong": "A strength", "care": "Needs care"}.get(tone, "")
        pill = f'<span class="pv-pill {tone}">{_e(tag)}</span>' if tag else ""
        both_badge = (
            '<span class="pv-both">&#10003; in both hands (High confidence)</span>'
            if is_both else f'<span class="pv-pill neutral">Seen on {hands[0].title()} hand · Moderate confidence</span>'
        )

        remedy = ""
        if mark.remedy:
            remedy = (f'<p class="pv-do"><span class="ev-label">Traditional Guidance</span> '
                      f"{_e(_sentence(mark.remedy))}</p>")

        rows += f"""
<div class="pv-row {tone}">
  <div class="pv-head"><b>{_e(mark.feature)}</b>{pill}{both_badge}</div>
  <p class="pv-sign">{_e(_sentence(mark.sign))}</p>
  <p class="pv-means">{_e(_sentence(mark.means))}</p>
  {remedy}
</div>"""

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
        if ahead:
            # Future windows strictly up to 10 years ahead (age to age + 10)
            if when <= age or when > age + 10:
                continue
        else:
            # Past milestones up to current age
            if when > age:
                continue
        head, why = _split_prediction(pred.get("text"))
        if not head:
            continue
        span = pred.get("age_range") or []
        if ahead and len(span) == 2 and span[1] > span[0]:
            if span[0] > age + 10:
                continue
            clamped_low = max(age, span[0])
            clamped_high = min(age + 10, span[1])
            if clamped_high <= clamped_low:
                clamped_high = min(age + 10, clamped_low + 3)
            window = f"ages {clamped_low}&ndash;{clamped_high}"
        else:
            window = (f"ages {span[0]}&ndash;{span[1]}"
                      if len(span) == 2 and span[1] > span[0] else f"around age {when}")
        confidence_tag = '<span class="pill-conf" style="font-size:0.7rem;font-weight:600;padding:2px 6px;border-radius:10px;background:#f0efe9;color:#5a554c;margin-left:8px;">Moderate Confidence</span>'
        backing_feat = f'<p class="pv-sign" style="font-size:0.83rem;color:#6b7280;margin:4px 0 0 0;"><b>Observed Physical Sign:</b> Traced along {_e(why)}.</p>' if why else ""
        rows += (f'<li><div class="tl-when">{window}</div>'
                 f'<div class="tl-body"><b>{_e(pred.get("title"))}</b>{confidence_tag}'
                 f'<p class="pv-means">{_e(_sentence(head))}</p>'
                 + backing_feat
                 + "</div></li>")
    if not rows:
        return ""
    return f'<ol class="timeline">{rows}</ol>'


# ---------------------------------------------------------------------------
# Vedic life reading (paid predictive profile)
# ---------------------------------------------------------------------------
def _vedic_card(title: str, body: str, tag: str = "") -> str:
    """A Vedic profile card. `body` is raw HTML — callers escape their own text.

    The article is marked `data-astrology-facts` so the customer-boundary scrub
    (customer_text_sanitizer) treats it as typed Python facts and does not
    rewrite vocabulary or wipe a node whose prose mentions a body part twice
    ("heart line … , … heart line" otherwise matches an internal leak pattern).
    """
    pill = f'<span class="pv-pill strong">{_e(tag)}</span>' if tag else ""
    return (f'<article class="card conv-area" data-astrology-facts="1">'
            f'<div class="card-top"><span class="area">{_e(title)}</span>{pill}</div>'
            f"{body}</article>")


def _vedic_life_reading(conf: dict, first: str) -> str:
    """Deterministic Vedic predictive profile: personality, profession, spouse,
    wealth, health, and authentic planetary upayas."""
    vp = conf.get("vedic_profile") if isinstance(conf.get("vedic_profile"), dict) else {}
    if not vp:
        return ""

    from palm_api.life_aspects import _ASPECT_VEDIC_UPAYAS

    cards: list[str] = []

    archetype = vp.get("archetype") or {}
    personality = vp.get("personality") or []
    profession = vp.get("profession") or {}
    marriage = vp.get("marriage") or {}
    wealth = vp.get("wealth") or {}

    # 1 — Mind & Intellectual Temperament
    pers_bits = [f"<p>{archetype.get('summary') or ''}</p>"] if archetype.get("summary") else []
    traits = [t for t in personality if isinstance(t, dict) and t.get("text")]
    if traits:
        pers_bits.append(
            '<ul class="pv-plain" style="margin-top:10px;">'
            + "".join(f'<li><b>{_e(t.get("trait", "").title())}:</b> {t.get("text", "")}</li>'
                      for t in traits)
            + "</ul>")
    upaya_mind = _ASPECT_VEDIC_UPAYAS.get("mind", {}).get("upaya")
    if upaya_mind:
        pers_bits.append(
            f'<div style="background:#fcf8f2;border-left:3px solid #c97d3e;padding:10px 14px;border-radius:6px;margin-top:10px;font-size:0.84rem;line-height:1.45;color:#4a453c;">'
            f'<b style="color:#7a4b18;">Targeted Vedic Upaya (Mind &amp; Intellect):</b><br>{upaya_mind}</div>'
        )
    if pers_bits:
        cards.append(_vedic_card(
            "Mind, Intellect & Temperament",
            "".join(pers_bits), "Intellect & Disposition"))

    # 2 — Profession, Leadership & Career Trajectory
    prof_txt = profession.get("summary") or ""
    if prof_txt:
        win = profession.get("window")
        tag = "Career & Vocation"
        win_note = ""
        if isinstance(win, list) and len(win) == 2:
            win_note = f"<p style='margin:6px 0 0;font-size:0.85rem;color:#6a7080;'><b>Major Vocational Establishment Window:</b> Ages {int(win[0])}–{int(win[1])}.</p>"
            tag = f"Career · Establishes {int(win[0])}–{int(win[1])}"

        prof_body = [f"<p>{prof_txt}</p>{win_note}"]
        upaya_car = _ASPECT_VEDIC_UPAYAS.get("career", {}).get("upaya")
        if upaya_car:
            prof_body.append(
                f'<div style="background:#fcf8f2;border-left:3px solid #c97d3e;padding:10px 14px;border-radius:6px;margin-top:10px;font-size:0.84rem;line-height:1.45;color:#4a453c;">'
                f'<b style="color:#7a4b18;">Targeted Vedic Upaya (Career &amp; Status):</b><br>{upaya_car}</div>'
            )
        basis = profession.get("basis")
        if basis:
            prof_body.append(f'<div style="border-top:1px solid #eeeae3;padding-top:8px;margin-top:10px;font-size:0.75rem;color:#7a756c;"><b>Astrological Palm Basis:</b> {_e(basis)}</div>')
        cards.append(_vedic_card("Career Trajectory, Status & Leadership",
                                 "".join(prof_body), tag))

    # 3 — Marriage, Partnerships & Spouse Dynamics
    mar_txt = marriage.get("summary") or ""
    if mar_txt:
        mar_body = [f"<p>{mar_txt}</p>"]
        upaya_love = _ASPECT_VEDIC_UPAYAS.get("love", {}).get("upaya")
        if upaya_love:
            mar_body.append(
                f'<div style="background:#fcf8f2;border-left:3px solid #c97d3e;padding:10px 14px;border-radius:6px;margin-top:10px;font-size:0.84rem;line-height:1.45;color:#4a453c;">'
                f'<b style="color:#7a4b18;">Targeted Vedic Upaya (Harmony &amp; Partnership):</b><br>{upaya_love}</div>'
            )
        basis = marriage.get("basis")
        if basis:
            mar_body.append(f'<div style="border-top:1px solid #eeeae3;padding-top:8px;margin-top:10px;font-size:0.75rem;color:#7a756c;"><b>Astrological Palm Basis:</b> {_e(basis)}</div>')
        cards.append(_vedic_card("Love, Marriage & Partner Compatibility",
                                 "".join(mar_body), "Partnership & Dharma"))

    # 4 — Wealth, Assets & Financial Trajectory
    wea_txt = wealth.get("summary") or ""
    if wea_txt:
        wea_body = [f"<p>{wea_txt}</p>"]
        upaya_wea = _ASPECT_VEDIC_UPAYAS.get("wealth", {}).get("upaya")
        if upaya_wea:
            wea_body.append(
                f'<div style="background:#fcf8f2;border-left:3px solid #c97d3e;padding:10px 14px;border-radius:6px;margin-top:10px;font-size:0.84rem;line-height:1.45;color:#4a453c;">'
                f'<b style="color:#7a4b18;">Targeted Vedic Upaya (Wealth &amp; Abundance):</b><br>{upaya_wea}</div>'
            )
        basis = wealth.get("basis")
        if basis:
            wea_body.append(f'<div style="border-top:1px solid #eeeae3;padding-top:8px;margin-top:10px;font-size:0.75rem;color:#7a756c;"><b>Astrological Palm Basis:</b> {_e(basis)}</div>')
        cards.append(_vedic_card("Wealth Accumulation & Financial Trajectory",
                                 "".join(wea_body), "Wealth & Resources"))

    # 5 — Health, Physical Vitality & Immunity
    upaya_hlth = _ASPECT_VEDIC_UPAYAS.get("health", {}).get("upaya")
    hlth_body = [
        "<p>Your life line and Mount of Venus indicate <b>steady baseline stamina, natural physical resilience, and strong vital recovery</b>. "
        "Maintaining regular nervous system relaxation and grounding physical routines ensures sustained high-performance energy.</p>"
    ]
    if upaya_hlth:
        hlth_body.append(
            f'<div style="background:#fcf8f2;border-left:3px solid #c97d3e;padding:10px 14px;border-radius:6px;margin-top:10px;font-size:0.84rem;line-height:1.45;color:#4a453c;">'
            f'<b style="color:#7a4b18;">Targeted Vedic Upaya (Health &amp; Vitality):</b><br>{upaya_hlth}</div>'
        )
    cards.append(_vedic_card("Health, Physical Vitality & Stamina", "".join(hlth_body), "Vitality & Prana"))

    if not cards:
        return ""
    return _section(
        "sec-vedic", f"{first}, your Core Life Readings",
        "A synthesized Vedic reading in the classical tradition of Samudrika Shastra, "
        "built strictly from the lines, mounts, and signs measured on your palms.",
        "".join(cards), nav="Life Domains")


def _clean_contrast_label(feature: str, sign: str, *, is_active: bool = True) -> str:
    f = str(feature or "").strip()
    s = str(sign or "").strip()
    f_low = f.lower()
    s_low = s.lower()
    if "mercury" in f_low:
        if is_active:
            return "<b>Commercial Acumen &amp; Speech</b> — You have developed sharp communication skills, negotiation confidence, and practical business judgment."
        return "<b>Innate Inquisitiveness</b> — Natural conversational curiosity and thoughtful observational instinct."
    if "venus" in f_low:
        if is_active:
            return "<b>Warmth &amp; Emotional Vitality</b> — Deepened capacity for warmth, generous devotion, and grounded interpersonal loyalty."
        return "<b>Innate Emotional Nature</b> — Core sensitive baseline and natural responsiveness to family warmth."
    if "saturn" in f_low:
        if is_active:
            return "<b>Duty &amp; Steadfast Discipline</b> — Proven endurance, patience under pressure, and reliable professional responsibility."
        return "<b>Innate Caution &amp; Seriousness</b> — Early predisposition toward prudence, duty, and careful forethought."
    if "jupiter" in f_low:
        if is_active:
            return "<b>Leadership &amp; Executive Ambition</b> — Active cultivation of authority, dignified self-respect, and strategic vision."
        return "<b>Innate Inner Ideals</b> — Natural pride, high personal standards, and quiet self-worth."
    if "apollo" in f_low or "sun" in f_low:
        if is_active:
            return "<b>Creative Merit &amp; Recognition</b> — Applied creative skill, polished personal taste, and earning public appreciation."
        return "<b>Innate Aesthetic Sense</b> — Natural appreciation for beauty, balance, and creative expression."
    if "mars" in f_low:
        if is_active:
            return "<b>Courage &amp; Practical Grit</b> — Hard-earned resilience, constitutional stamina, and standing firm through adversity."
        return "<b>Innate Inner Fire</b> — Underlying fighting spirit and baseline emotional stamina."
    if "luna" in f_low or "moon" in f_low:
        if is_active:
            return "<b>Applied Intuition &amp; Strategy</b> — Channeling imaginative breadth into realistic, actionable future plans."
        return "<b>Innate Restless Imagination</b> — Rich inner world, love for new horizons, and vivid instinctive impressions."
    if "life line" in f_low:
        if is_active:
            return "<b>Active Vitality &amp; Stamina</b> — Cultivated physical resilience and steady pacing throughout daily work."
        return "<b>Inborn Constitution</b> — Baseline physical constitution and ancestral vitality."
    if "head line" in f_low:
        if is_active:
            return "<b>Practical Reasoning &amp; Focus</b> — Clear, structured decision-making sharpened through real-world experience."
        return "<b>Innate Intellectual Style</b> — Natural mental agility and instinctive problem-solving."
    if "fate line" in f_low:
        if is_active:
            return "<b>Vocational Trajectory</b> — Distinct, purposeful career direction forged through independent choices and focus."
        return "<b>Innate Vocational Baseline</b> — Early adaptability before taking definitive command of your destiny."
    if "heart line" in f_low:
        if is_active:
            return "<b>Emotional Integrity &amp; Devotion</b> — Mature, steadfast loyalty and intentional investment in meaningful relationships."
        return "<b>Innate Emotional Receptivity</b> — Baseline sensitivity and heartfelt connection with close companions."
    if "thumb" in f_low:
        if "reasoning" in s_low or "logic" in s_low:
            if is_active:
                return "<b>Strategic Deliberation</b> — Methodical reasoning and weighing options before taking major action."
            return "<b>Innate Analytical Nature</b> — Instinctive logical balance and thoughtful hesitation."
        if "short" in s_low or "receptive" in s_low:
            return "<b>Adaptive Flexibility</b> — Agile, feeling-led responsiveness that adjusts quickly to changing circumstances."
        if is_active:
            return "<b>Executive Willpower &amp; Drive</b> — Strong follow-through, boundary setting, and decisive execution."
        return "<b>Innate Determination</b> — Inborn tenacity that anchors your core convictions."
    return f"<b>{_e(f)}</b> — {_e(s)}"


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
def _shape_prose(reading: Any) -> str:
    """Temperament in prose, taken from the hand shape the CV measured.

    The opening paragraph of the archetype section normally comes from the
    prose overlay. When there is no overlay at all — facts could not be built —
    the section would otherwise open with a bare table, so speak from the
    measurements instead of saying nothing.
    """
    seen: list[str] = []
    for r in getattr(reading, "shape", None) or []:
        text = str(getattr(r, "means", "") or "").strip()
        if text and text not in seen:
            seen.append(text)
    if not seen:
        return ""
    return " ".join(t if t[-1] in ".!?" else f"{t}." for t in seen[:3])


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
    rr = raw.get("reading_result") if isinstance(raw.get("reading_result"), dict) else {}
    if rr:
        raw_flat = dict(rr)
        for k, v in raw.items():
            if k not in raw_flat:
                raw_flat[k] = v
        raw = raw_flat

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
        agree = {k for k in shared if "_no_" not in k}

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

    # 1.5 — Executive Overview / Where You Are Now
    now_summary = ""
    if current_phase:
        now_summary += f"<p>{_e(current_phase)}</p>"
    elif why_now:
        now_summary += f"<p>{_e(why_now)}</p>"
    else:
        # An aspect key with no title would put None into the join below.
        strong_areas = [t for t in (_TITLE.get(str(a.get("key") or ""))
                                    for a in aspects
                                    if a.get("strength") == "strong") if t]
        dom_name = dom_key.title()
        if strong_areas:
            now_summary += (f"<p>Your active {dom_name} hand shows pronounced momentum in {', '.join(strong_areas[:2])}. "
                            f"The recurring palm pattern reflects purposeful focus and deliberate application of your core strengths.</p>")
        else:
            now_summary += (f"<p>Your active {dom_name} hand reflects a balanced, adaptive constitution. "
                            f"Lived choices show an evolving mastery of practical decisions and steady personal development.</p>")

    now_points = []
    if mind_now:
        for m in mind_now[:2]:
            now_points.append(f"<li>{_e(m)}</li>")
    if hardest:
        now_points.append(f'<li><b style="color:#a44c12;">Core tension to watch:</b> {_e(hardest)}</li>')

    if now_points:
        now_summary += (f'<div class="card" style="background:#faf8f5;border-left:4px solid #b57c38;padding:12px 16px;margin-top:10px;">'
                        f'<div class="ev-label" style="color:#7a4b18;font-weight:700;margin-bottom:6px;">Key Focus & Immediate Direction</div>'
                        f'<ul class="pv-plain" style="margin:0;padding-left:18px;">{"".join(now_points)}</ul></div>')

    if now_summary:
        blocks.append(_section(
            "sec-now", f"Where You Are Now, {first}",
            "An executive synthesis of your current life phase, active focus, and primary tension.",
            now_summary, nav="Where You Are"))

    # 2 — the hand itself (Core Archetype & Temperament)
    shape_rows = _rows(dom_reading.shape, agree)
    opening_text = personality or _shape_prose(dom_reading)
    opening = f"<p>{_e(opening_text)}</p>" if opening_text else ""
    blocks.append(_section(
        "sec-hand", "Your Core Hand Archetype & Temperament",
        f"Shape, thumb and finger set — {_HAND_ROLE[True]}.",
        opening + (f'<div class="card">{shape_rows}</div>' if shape_rows else "")))

    if paid:
        # 2.5 — Vedic predictive profile (personality, profession, spouse, wealth)
        vedic_block = _vedic_life_reading(conf, first)
        if vedic_block:
            blocks.append(vedic_block)

        # 3 — Mounts & Auspicious Signs
        mount_rows = _rows(dom_reading.mounts, agree)
        mounts_html = f'<div class="card">{mount_rows}</div>' if mount_rows else ""
        marks_html = _marks_section(readings, raw)
        blocks.append(_section(
            "sec-mounts", "Planetary Mounts & Auspicious Markings",
            "The raised and flat pads indicate how cosmic planetary energies distribute across your palm, modified by unique signs.",
            mounts_html + marks_html, nav="Mounts & Signs"))

        # 6 — Chronological Timeline (Past Milestones)
        behind = _timeline(conf, age, ahead=False)
        if behind:
            blocks.append(_section(
                "sec-behind", f"{first}, your past life milestones",
                "Calculated using the classical seven-year division across your major lines to map key developmental chapters.",
                behind, nav="Past Timeline"))

        # 7 — Forward Roadmap (Upcoming Age Windows)
        ahead = _timeline(conf, age, ahead=True)
        if ahead:
            blocks.append(_section(
                "sec-ahead", "Your Upcoming Age Windows & Direction",
                "Upcoming developmental windows read forward along your active palm lines.",
                ahead, nav="Future Roadmap"))

        # 8 — Innate vs. Made (Left vs. Right Hand Confluence)
        contrast = (f'<p style="margin:0 0 12px 0;line-height:1.6;color:#2c3140;">'
                    f'Your passive hand (<b>{other_key.title()}</b>) represents your inborn baseline and ancestral potential, '
                    f'while your active hand (<b>{dom_key.title()}</b>) reflects what you have achieved and cultivated through conscious choices. '
                    f'Comparing both reveals your personal evolution:</p>')
        if hand_note:
            contrast += f"<p>{_e(hand_note)}</p>"
        if other_reading:
            only_active = [r for r in dom_reading.all()
                           if r.key not in agree and r.tone != "neutral"][:4]
            only_innate = [r for r in other_reading.all()
                           if r.key not in agree and r.tone != "neutral"][:4]
            cols = ""
            if only_innate:
                cols += ('<div class="pv-col"><div class="ev-label">Inborn Potential (Passive Hand: '
                         f'{_e(other_key.title())})</div><ul class="pv-plain">'
                         + "".join(f"<li>{_clean_contrast_label(r.feature, r.sign, is_active=False)}</li>"
                                   for r in only_innate) + "</ul></div>")
            if only_active:
                cols += ('<div class="pv-col"><div class="ev-label">Cultivated Strengths (Active Hand: '
                         f'{_e(dom_key.title())})</div><ul class="pv-plain">'
                         + "".join(f"<li>{_clean_contrast_label(r.feature, r.sign, is_active=True)}</li>"
                                   for r in only_active) + "</ul></div>")
            if cols:
                contrast += f'<div class="card pv-cols">{cols}</div>'
        blocks.append(_section(
            "sec-contrast", "Innate Blueprint vs. Self-Made Evolution",
            "Comparing your passive hand (inborn baseline) with your active hand (lived choices and cultivated mastery).",
            contrast, nav="Innate vs Made"))

        # 9 — Master Astrological Upayas
        try:
            from .palm_cards import _remedies
            source, block = _remedy_source(raw, dom_key)
            remedies = _remedies(block, conf, paid=True)
            if remedies:
                blocks.append(remedies)
        except Exception:  # noqa: BLE001
            pass
    else:
        # Free mode: show 1 anchor past milestone to prove accuracy, then lock forward roadmap
        behind_all = _timeline(conf, age, ahead=False)
        if behind_all:
            anchor_stage = behind_all.split("</div>")[0] + "</div>" if "</div>" in behind_all else behind_all
            blocks.append(_section(
                "sec-behind", f"Lived Validation Point",
                "Classical palmistry divides lines into seven-year chapters. Here is one key milestone for verification:",
                anchor_stage + f'<p class="sec-note" style="margin-top:12px;font-style:italic;">This anchor point calibrates your hand timeline. Your complete chronological life story, lived milestones, and upcoming future age chapters (ages {age}+) are unlocked in the full reading.</p>',
                nav="Validation Point"))

        ahead_n = len([p for p in (conf.get("predictions") or [])
                       if isinstance(p.get("age"), int) and p["age"] > age])
        blocks.append(f"""
<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">Upcoming Timeline & Forward Age Windows (Ages {age}+)</div>
  <p class="blurred">Key forward age chapters and milestone windows mapped across your active palm lines using classical seven-year radial divisions.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Future timeline is locked.</b> Unlock to see age milestones mapped across your lines.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">Mount by Mount Planetary Energy Profile</div>
  <p class="blurred">Analysis of the 7 planetary mounts (Jupiter, Saturn, Sun, Mercury, Mars, Venus, Moon) revealing where your energy naturally pools.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Mount analysis is locked.</b> Unlock for deep planetary energy breakdown.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">Special Marks & Auspicious Signs (Trishul, Stars, Squares)</div>
  <p class="blurred">Analysis of special marks (Trishul, Matsya, Stars, Squares, Triangles) and how they modify each mount.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Special marks analysis is locked.</b> Unlock to view all detected palm signs.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">Left vs. Right Hand Evolution (Innate vs. Self-Made)</div>
  <p class="blurred">Side-by-side comparison of the destiny you were born with on your passive hand versus the strength and career position you have built with your active hand.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Hand evolution comparison is locked.</b> Unlock to explore how you have evolved beyond your blueprint.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">Actionable Hand Remedies (Mudras & Daily Habits)</div>
  <p class="blurred">Targeted supportive practices, mudras, and habit shifts keyed to your hand's specific care points.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Hand remedies are locked.</b> Unlock for practical supportive habits tailored to your lines.</p>
</div>

<section class="buy" id="unlock" style="margin-top:20px;">
  <h3>Unlock your complete palm reading</h3>
  <p>You have your core hand shape and major line blueprint. Unlock the full forward age timeline, mount energy breakdown, special marks, life area verdicts, and personalized mudra remedies.</p>
  <a class="cta" href="#unlock" data-unlock="1">Unlock full reading · ₹{_e(price)}</a>
</section>""")

    # Mandatory Health & Legal Disclaimer (both free and paid)
    disclaimer_html = (
        '<div class="card" style="background:#fdfcf9;border:1px solid #e2ded5;border-top:3px solid #b57c38;margin-top:24px;padding:16px 20px;">'
        '<div class="ev-label" style="color:#7a4b18;font-weight:bold;margin-bottom:6px;">Traditional Context & Consultation Boundaries</div>'
        '<p class="fine" style="color:#5a554c;line-height:1.55;margin:0 0 8px 0;">'
        'This reading reflects the traditional interpretive heritage of classical palmistry (Samudrika Shastra) synthesized with morphological measurements. '
        'Palm markings reflect current tendencies and naturally evolve over time with conscious choice, lifestyle changes, and disciplined intention.'
        '</p>'
        '<p class="fine" style="color:#5a554c;line-height:1.55;margin:0;">'
        '<b>Healthcare & Professional Disclaimer:</b> Palmistry is strictly an interpretive and reflective discipline. It does not provide medical, clinical, psychological, legal, or licensed financial advisory services. '
        'It cannot evaluate, prevent, or treat any health condition. Always consult licensed healthcare professionals for health concerns and qualified advisors for major financial decisions.'
        '</p>'
        '</div>'
    )
    blocks.append(_section("sec-disclaimer", "Traditional Heritage & Consultation Boundaries", "", disclaimer_html, nav="Disclaimer"))

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
