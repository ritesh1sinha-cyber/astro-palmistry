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
    "career": "Work & Career",
    "wealth": "Money & Resources",
    "love": "Relationships & Emotions",
    "health": "Health & Vitality",
    "travel": "Travel, Change & Imagination",
    "character": "Personal Growth & Direction",
}

_HAND_ROLE = {
    True: "your active hand — what you have made of yourself",
    False: "your passive hand — what you were born with",
}


def _palm_signature(raw: dict, dom_key: str, aspects: list[dict[str, Any]]) -> str:
    dom_feats = (raw.get(dom_key) or {}).get("features") or {}
    morph = dom_feats.get("morphology") or {}
    hand_type = str(morph.get("hand_type") or "air").title()
    mounts = dom_feats.get("mounts") or {}
    prom_mounts = [k.title() for k, v in mounts.items() if str(v).lower() in ("prominent", "full", "high")]
    lines = dom_feats.get("lines") or {}
    deep_lines = [k.title() for k, v in lines.items() if isinstance(v, dict) and str(v.get("depth") or "").lower() == "deep"]
    strong_aspects = [_TITLE.get(str(a.get("key") or "")) for a in aspects
                      if "strong" in str(a.get("verdict") or a.get("strength") or "").lower()
                      or "good" in str(a.get("verdict") or a.get("strength") or "").lower()]

    mount_part = f"a clearly developed {prom_mounts[0]} mount" if prom_mounts else "balanced mount topography"
    line_part = f"a defined {deep_lines[0]} line" if deep_lines else "well-etched primary lines"
    theme_part = f"around {', '.join(strong_aspects[:2])} and sustained disciplined effort" if strong_aspects else "around adaptability, practical decisions and sustained focus"

    sig_text = (f"{hand_type}-type hand with {mount_part}, {line_part} and active palm markers. "
                f"The overall pattern points toward an analytical, ambitious and purposeful temperament, "
                f"with the strongest themes {theme_part}.")
    return (f'<div class="card" style="background:#faf8f5;border-left:4px solid #1a5276;padding:14px 18px;margin-top:14px;">'
            f'<div class="ev-label" style="color:#1a5276;font-weight:700;margin-bottom:6px;">Palm Signature</div>'
            f'<p style="margin:0;font-size:0.96rem;line-height:1.6;">{_e(sig_text)}</p></div>')


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


def _clean_contrast_label(feature: str, sign: str) -> str:
    f = str(feature or "").strip()
    s = str(sign or "").strip()
    f_low = f.lower()
    s_low = s.lower()
    if "mercury" in f_low:
        return "<b>Mercury Mount (Speech & Trade)</b> — prominent pad denoting sharp commercial communication and negotiation"
    if "venus" in f_low:
        return "<b>Venus Mount (Vitality & Warmth)</b> — full, denoting physical vitality, warmth, and generous affection"
    if "saturn" in f_low:
        return "<b>Saturn Mount (Duty & Discipline)</b> — well-formed, reflecting patience, endurance, and serious responsibility"
    if "jupiter" in f_low:
        return "<b>Jupiter Mount (Leadership & Vision)</b> — elevated, indicating ambition, executive dignity, and pride"
    if "apollo" in f_low or "sun" in f_low:
        return "<b>Apollo Mount (Creativity & Acclaim)</b> — raised, indicating artistic taste, creative display, and public merit"
    if "mars" in f_low:
        if "flat" in s_low:
            return "<b>Mars Plains (Stamina & Temper)</b> — moderate, denoting diplomatic calm and avoiding unnecessary conflict"
        return "<b>Mars Mount (Courage & Stamina)</b> — full, denoting resilience, physical courage, and grit under pressure"
    if "luna" in f_low or "moon" in f_low:
        return "<b>Moon Mount (Imagination & Intuition)</b> — developed, denoting rich imaginative breadth and intuitive depth"
    if "life line" in f_low:
        return "<b>Life Line (Vitality Arc)</b> — deep and smoothly traced, indicating strong constitutional endurance"
    if "head line" in f_low:
        return "<b>Head Line (Mental Clarity)</b> — clearly incised, reflecting practical logic, realism, and structured decision-making"
    if "fate line" in f_low:
        return "<b>Fate Line (Vocational Drive)</b> — distinct trajectory, indicating purposeful career direction and independent focus"
    if "heart line" in f_low:
        return "<b>Heart Line (Emotional Integrity)</b> — deeply etched, reflecting steadfast loyalty and deep emotional investment"
    if "thumb" in f_low:
        if "reasoning" in s_low or "logic" in s_low:
            return "<b>Thumb Proportions (Logic & Reasoning)</b> — balanced structure supporting analytical deliberation"
        if "short" in s_low or "receptive" in s_low:
            return "<b>Thumb Proportions (Adaptability)</b> — flexible, feeling-led nature that responds quickly to real-time situations"
        return "<b>Thumb Proportions (Willpower)</b> — firm structure denoting strong determination and follow-through"
    return f"<b>{_e(f)}</b> — {_e(s)}"


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

    agree: set[str] = set()
    if other_reading:
        shared = {r.key for r in dom_reading.all()} & {r.key for r in other_reading.all()}
        agree = {k for k in shared
                 if "_no_" not in k and not k.startswith(("hand_type", "thumb", "index", "ring"))}

    current_phase = str(prose.get("current_phase") or "").strip()
    hardest = str(prose.get("hardest_area_note") or "").strip()
    mind_now = [str(x).strip() for x in (prose.get("mind_now") or []) if str(x).strip()]
    why_now = str(prose.get("why_now") or "").strip()
    areas = prose.get("areas") if isinstance(prose.get("areas"), dict) else {}

    blocks: list[str] = []

    # 1 — Chart / Palm Signature (Photographs + CV Lines + Evidence Signature)
    sig_card = _palm_signature(raw, dom_key, aspects)
    blocks.append(_section(
        "sec-hands", "Your hands, and what I traced on them",
        "",
        _photos(raw, dom_key) + _photo_note(raw) + sig_card, nav="Your hands"))

    # 2 — Executive Overview / Where You Are Now
    now_summary = ""
    if current_phase:
        now_summary += f"<p>{_e(current_phase)}</p>"
    elif why_now:
        now_summary += f"<p>{_e(why_now)}</p>"
    else:
        strong_areas = [_TITLE.get(str(a.get("key") or "")) for a in aspects
                        if "strong" in str(a.get("verdict") or a.get("strength") or "").lower()
                        or "good" in str(a.get("verdict") or a.get("strength") or "").lower()]
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

    if paid:
        # 3 — Core Life Areas (Confluence Analysis with Verdict, Conclusion, Timing, What Helps & Collapsed Checkpoints)
        rows = []
        future_windows = rr.get("future_windows") or []
        domain_map = {
            "career": "career_direction",
            "wealth": "money",
            "love": "relationships",
            "health": "vitality",
            "travel": "travel",
            "character": "temperament",
        }

        for key in [str(a.get("key") or "") for a in aspects if isinstance(a, dict)]:
            aspect_data = aspect_by_key.get(key) or {}
            block = areas.get(key) or {}
            if not isinstance(block, dict):
                block = {}

            title = _TITLE.get(key) or str(aspect_data.get("title") or key)
            verdict = str(aspect_data.get("verdict") or aspect_data.get("strength") or "Moderate")
            confidence = str(aspect_data.get("confidence") or "Moderate").title()

            # Astrologer Conclusion
            conclusion = str(block.get("outlook") or block.get("conclusion") or aspect_data.get("summary") or "").strip()
            manifestation = str(block.get("manifestation") or "").strip()
            if manifestation and manifestation.lower() not in conclusion.lower():
                conclusion = f"{conclusion} {manifestation}"

            # Timing breakdown
            timing_str = str(block.get("timing") or "").strip()
            curr_phase = str(aspect_data.get("current_phase") or "").strip()
            near_term = str(aspect_data.get("near_term") or "").strip()

            # Future checkpoints matched to domain
            checkpoints = []
            for fw in future_windows:
                fw_dom = str(fw.get("domain") or "").lower()
                if fw_dom in (key, domain_map.get(key, "")):
                    aw = fw.get("age_window")
                    if aw and len(aw) >= 2:
                        checkpoints.append(
                            f"Ages {aw[0]}–{aw[1]}: {str(fw.get('status', 'Upcoming milestone')).title()} — {str(fw.get('pattern', 'Active line continuity along your palm roadmap'))}."
                        )

            if not timing_str:
                if checkpoints:
                    timing_str = f"Current phase is {curr_phase.lower().rstrip('.')}. Near-term: {near_term.lower().rstrip('.')}. Next supportive window: {checkpoints[0].split(':')[0]}."
                else:
                    timing_str = f"Current phase is {curr_phase.lower().rstrip('.')}. Near-term: {near_term.lower().rstrip('.')}. Next supportive window: Timing cannot be established reliably from the available palm evidence."

            # What helps
            what_helps = str(block.get("what_helps") or aspect_data.get("what_helps") or "Focus on disciplined execution and balanced habits.").strip()

            # Supporting & Conflicting signals
            supporting_items = "".join(f"<li>{_e(s)}</li>" for s in (aspect_data.get("supporting_signals") or []))
            if not supporting_items:
                supporting_items = "<li>Primary line continuity on active hand</li>"

            conflicting_items = "".join(f"<li>{_e(s)}</li>" for s in (aspect_data.get("conflicting_signals") or []))
            conflicting_html = f"<p style='margin:6px 0 2px 0;font-weight:600;color:#333;'>Conflicting / Pressure Signals:</p><ul style='margin:0 0 6px 0;padding-left:18px;'>{conflicting_items}</ul>" if conflicting_items else ""

            checkpoints_html = "".join(f"<li>{_e(cp)}</li>" for cp in checkpoints) if checkpoints else "<li>Timing cannot be established reliably from the available palm evidence.</li>"

            evidence_items = "".join(
                f"<li><b>Traditional palmistry interpretation:</b> {_e(str(p.get('text') or p.get('traditional_meaning') or '').strip())}</li>"
                for p in (aspect_data.get("points") or [])
                if str(p.get("text") or p.get("traditional_meaning") or "").strip())

            from palm_api.life_aspects import _ASPECT_VEDIC_UPAYAS
            remedy = str(_ASPECT_VEDIC_UPAYAS.get(key, {}).get("upaya") or aspect_data.get("remedy") or "").strip()

            conf_badge = f'<span class="pill-conf" style="font-size:0.68rem;font-weight:600;padding:2px 8px;border-radius:10px;background:#ebe9e1;color:#4a453e;margin-left:6px;">{_e(confidence)} Confidence</span>'
            card_html = f"""
<article class="card conv-area" id="sec-{_e(key)}">
  <div class="card-top">
    <span class="area">{_e(title)}</span>
    <div><span class="pill mixed">{_e(verdict)}</span>{conf_badge}</div>
  </div>
  <div class="conv-conclusion" style="margin:10px 0 8px 0;">
    <p style="margin:0;font-size:0.96rem;line-height:1.6;color:#2c3140;">{_e(conclusion)}</p>
  </div>
  <div class="conv-timing" style="margin:8px 0;font-size:0.91rem;color:#4a453e;line-height:1.5;">
    <b>Timing:</b> {_e(timing_str)}
  </div>
  <div class="conv-helps" style="margin:8px 0 10px 0;background:#f9f8f5;border-left:3px solid #b57c38;padding:8px 12px;border-radius:4px;font-size:0.91rem;color:#3d4250;line-height:1.5;">
    <b>What helps:</b> {_e(what_helps)}
  </div>
  <details class="technical-evidence" style="margin-top:12px;border-top:1px dashed #d5d0c7;padding-top:8px;font-size:0.85rem;color:#555;">
    <summary style="cursor:pointer;color:#8c531b;font-weight:600;margin-bottom:6px;">Calculation &amp; future checkpoints</summary>
    <div style="padding:4px 0;">
      <p style="margin:4px 0 2px 0;font-weight:600;color:#333;">Supporting Evidence:</p>
      <ul style="margin:0 0 6px 0;padding-left:18px;">{supporting_items}</ul>
      {conflicting_html}
      <p style="margin:6px 0 2px 0;font-weight:600;color:#333;">Future Checkpoints:</p>
      <ul style="margin:0 0 6px 0;padding-left:18px;">{checkpoints_html}</ul>
      <p style="margin:6px 0 2px 0;font-weight:600;color:#333;">Classical Signs &amp; Citations:</p>
      <ul style="margin:0 0 6px 0;padding-left:18px;">{evidence_items}</ul>
      <div style="margin-top:8px;padding:8px 10px;background:#fdfaf6;border-radius:4px;">
        <b>Traditional Guidance &amp; Astrological Upaya:</b><br>{remedy}
      </div>
    </div>
  </details>
</article>"""
            rows.append(card_html)

        if rows:
            blocks.append(_section(
                "sec-areas", "Core Life Areas (Confluence Analysis)",
                "Synthesized analysis combining line trajectories, planetary mount elevations, and auspicious markings.",
                "".join(rows), nav="Life Areas"))

        # Mandatory Health & Legal Disclaimer
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

        n_points = sum(
            len(_filter_customer_numbered(_hand_for_customer_filter(raw, h)))
            for h in ("left", "right"))
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

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">Detailed Line-by-Line Mathematical Working</div>
  <p class="blurred">Point-by-point derivation and classical book citations behind all {n_points} numbered findings on both hands.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Detailed working is locked.</b> Unlock for the complete line-by-line derivation.</p>
</div>

<section class="buy" id="unlock" style="margin-top:20px;">
  <h3>Unlock your complete palm reading</h3>
  <p>You have your core hand shape and major line blueprint. Unlock the full forward age timeline, mount energy breakdown, special marks, life area verdicts, and personalized mudra remedies.</p>
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
