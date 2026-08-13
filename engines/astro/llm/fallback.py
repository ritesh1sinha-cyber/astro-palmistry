"""Deterministic prose fallbacks when the LLM is unavailable or fails QA.

Prediction facts never change. These templates only express CardFacts /
QuestionFacts / HoraryFacts / PalmFacts in plain English.
"""

from __future__ import annotations

import re
from typing import Any


def _status_phrase(status: str, *, kind: str = "promise") -> str:
    s = (status or "").lower()
    if kind == "challenge":
        return {
            "strongly_indicated": "strongly indicated",
            "indicated": "indicated",
            "mixed": "mixed",
            "weak": "not strongly indicated",
            "insufficient_evidence": "not strongly indicated from the available evidence",
        }.get(s, "mixed")
    return {
        "strongly_supported": "strongly supported",
        "supported": "supported",
        "mixed": "mixed",
        "weak": "not strongly supported",
        "insufficient_evidence": "not strongly established from the available evidence",
    }.get(s, "mixed")


def _activation_phrase(status: str) -> str:
    return {
        "strongly_active": "strongly active",
        "active": "active",
        "mixed": "mixed",
        "weak": "only lightly active",
        "inactive": "not strongly active right now",
        "insufficient_evidence": "unclear in the current phase",
    }.get((status or "").lower(), "mixed")


def card_fallback(card: Any) -> dict[str, Any]:
    """Conversational deterministic fallback; never exposes technical mechanics."""
    area = getattr(card, "area", "") or (card.get("area") if isinstance(card, dict) else "")
    kind = getattr(card, "kind", "promise") if not isinstance(card, dict) else card.get("kind", "promise")
    status = getattr(card, "status", "") if not isinstance(card, dict) else card.get("status", "")
    activation = getattr(card, "activation_status", "") if not isinstance(card, dict) else card.get("activation_status", "")
    label = getattr(card, "label", area) if not isinstance(card, dict) else card.get("label", area)
    manifests = list(getattr(card, "manifestation_ids", None) if not isinstance(card, dict) else card.get("manifestation_ids") or [])
    tags = list(getattr(card, "semantic_tags", None) if not isinstance(card, dict) else card.get("semantic_tags") or [])
    is_challenge = kind == "challenge" or area in ("health", "troubles")
    area_name = label or area or "this part of life"
    if is_challenge:
        headline = f"This is an area where protecting your energy can make a real difference."
        summary = f"For {area_name.lower()}, the current phase is {_activation_phrase(activation)}. The useful response is consistency rather than alarm."
        show = manifests[:3] or tags[:3] or ["periods when routine and recovery matter more", "small issues becoming easier when addressed early"]
        watch = ["Letting pressure accumulate or repeatedly ignoring recovery needs."]
        helps = ["Keep your routine simple, protect recovery time and respond early when something needs attention."]
    else:
        headline = f"Your {area_name.lower()} story is about how steady effort turns into visible progress."
        summary = f"The underlying promise here is {_status_phrase(status)} and the current phase is {_activation_phrase(activation)}. Stronger timing can help, but it cannot create something the chart does not support."
        show = manifests[:3] or tags[:3] or ["progress becoming more visible when the timing is supportive", "results building through consistent effort"]
        watch = ["Expecting one good period to do all the work for you."]
        helps = ["Prepare in advance, then act when the stronger validated window arrives."]
    timing_summary = ""
    tws = list(getattr(card, "timing_windows", None) or [])
    if tws:
        labels = [getattr(w, "label", "") for w in tws if getattr(w, "label", "")]
        timing_summary = "Stronger validated periods: " + "; ".join(labels[:3])
    else:
        window = getattr(card, "window", None)
        label_w = getattr(window, "label", "") if window is not None else ""
        if label_w:
            timing_summary = f"A stronger validated period is associated with {label_w}."
    return {
        "question_lens": getattr(card, "question_lens", "") or "",
        "headline": headline[:140],
        "why": summary[:220], "meaning": summary[:280], "summary": summary[:280],
        "manifestations": [str(x)[:120] for x in show][:3],
        "how_this_may_show_up": [str(x)[:120] for x in show][:3],
        "what_to_watch": [str(x)[:120] for x in watch][:2],
        "what_helps": [str(x)[:120] for x in helps][:2],
        "pressure": (watch[0] if watch else "")[:180],
        "action": (helps[0] if helps else "")[:180],
        "timing_summary": timing_summary[:180],
    }


def report_fallback(facts: Any) -> dict[str, Any]:
    cards = getattr(facts, "cards", None) or []
    overlay_cards = {}
    for c in cards:
        area = getattr(c, "area", "") or ""
        if area:
            overlay_cards[area] = card_fallback(c)
    name = getattr(facts, "first_name", "") or ""
    age_band = getattr(facts, "age_band", "adult") or "adult"
    stage = {
        "young_adult": "You are in a stage where choices can still reshape the direction of several parts of life.",
        "adult": "Your chart is best read as a set of different clocks: some areas move now while others need more patience.",
        "midlife": "At this stage, the important question is less about doing everything and more about where your effort has the strongest return.",
        "mature": "At this stage, the chart is more useful for showing what deserves attention, consolidation and meaning.",
    }.get(age_band, "Your chart is best read as a set of different clocks: some areas move now while others need more patience.")
    opening = (f"{name}, this reading is about how the different parts of your life fit together." if name else "This reading is about how the different parts of your life fit together.")
    master = stage
    return {"opening": opening, "master_narrative": master, "cards": overlay_cards}


_MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def _month_year(value: Any) -> str:
    """ISO / loose date → 'November 2027' (the form date_guard allows)."""
    text = str(value or "").strip()
    if not text:
        return ""
    m = re.match(r"^(\d{4})-(\d{1,2})", text)
    if m:
        month = int(m.group(2))
        if 1 <= month <= 12:
            return f"{_MONTH_NAMES[month - 1]} {m.group(1)}"
    return text


def _readable_window_label(label: str) -> str:
    """'May 2024 → Oct 2026' → 'May 2024 to October 2026'."""
    text = str(label or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s*(?:→|->|–|—)\s*", " to ", text)
    abbrev = {name[:3].lower(): name for name in _MONTH_NAMES}

    def expand(match: re.Match) -> str:
        return f"{abbrev[match.group(1).lower()]} {match.group(2)}"

    return re.sub(
        r"\b(" + "|".join(abbrev) + r")[a-z]*\.?\s+((?:19|20)\d{2})\b",
        expand,
        text,
        flags=re.I,
    )


def _window_phrase(card: Any) -> str:
    """'November 2027 to February 2028' from the card's own validated windows."""
    windows = list(getattr(card, "timing_windows", None) or [])
    start = end = label = ""
    if windows:
        w = windows[0]
        start = _month_year(getattr(w, "start", ""))
        end = _month_year(getattr(w, "end", ""))
        label = str(getattr(w, "label", "") or "")
    else:
        w = getattr(card, "window", None)
        if w is not None:
            start = _month_year(getattr(w, "start", ""))
            end = _month_year(getattr(w, "end", ""))
            label = str(getattr(w, "label", "") or "")
    if start and end and start != end:
        return f"{start} to {end}"
    if start or end:
        return start or end
    return _readable_window_label(label)


def timing_sentence(text: Any) -> str:
    """Any window form → one readable English sentence about when it lands."""
    raw = str(text or "").strip()
    if not raw:
        return ""
    # Already a sentence written by the model.
    if raw.endswith(".") and " " in raw and not re.match(r"^[\d A-Za-z]+ to ", raw):
        return _readable_window_label(raw)
    body = _readable_window_label(raw)
    body = re.sub(
        r"\b(\d{4})-(\d{1,2})(?:-\d{1,2})?\b",
        lambda m: (
            f"{_MONTH_NAMES[int(m.group(2)) - 1]} {m.group(1)}"
            if 1 <= int(m.group(2)) <= 12 else m.group(0)
        ),
        body,
    )
    body = body.strip(" .")
    if not body:
        return ""
    low = body.lower()
    if low.startswith("now to "):
        return f"This runs from now through {body[7:]}."
    if " to " in low:
        return f"The stronger stretch runs from {body}."
    return f"The stronger stretch is associated with {body}."


def clip_sentences(text: Any, limit: int) -> str:
    """Trim to a budget on a sentence boundary rather than mid-word."""
    t = str(text or "").strip()
    if len(t) <= limit:
        return t
    parts = re.split(r"(?<=[.!?])\s+", t)
    joined = _join_within(parts, limit)
    if joined and len(joined) <= limit:
        return joined
    # A single oversized sentence: end on a word, never inside one.
    return t[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def clean_palm_summary(summary: Any) -> str:
    """Drop the engine's grouping preamble; the reader wants the reading."""
    t = str(summary or "").strip()
    t = re.sub(
        r"^together,?\s+these signs point to [^:]{0,80}:\s*", "", t, flags=re.I,
    )
    return t[0].upper() + t[1:] if t else ""


def _join_within(sentences: list[str], limit: int) -> str:
    """Join whole sentences under a budget — never cut a word in half."""
    out: list[str] = []
    used = 0
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        cost = len(s) + (1 if out else 0)
        if out and used + cost > limit:
            break
        out.append(s)
        used += cost
    return " ".join(out)


def area_tone(card: Any) -> tuple[str, str]:
    """Chip label + css class from the same facts the sentence is built on.

    Kept next to the sentence builders on purpose: a chip that says
    "Improving" above a paragraph that says "mixed" reads as a contradiction.
    """
    status = str(getattr(card, "status", "") or "").lower()
    activation = str(getattr(card, "activation_status", "") or "").lower()
    kind = str(getattr(card, "kind", "promise") or "promise").lower()
    supported = status in ("strongly_supported", "supported")
    active = activation in ("strongly_active", "active")
    if kind == "challenge":
        return ("Needs care", "down") if active else ("Steady for now", "mixed")
    if supported and active:
        return ("Supported now", "up")
    if supported:
        return ("Promised, not yet active", "mixed")
    if status in ("weak", "insufficient_evidence"):
        return ("Limited support", "down")
    return ("Mixed", "mixed")


def _area_outlook_sentence(card: Any, area_name: str) -> str:
    """Plain-language situation line, graded by promise and activation."""
    status = str(getattr(card, "status", "") or "").lower()
    activation = str(getattr(card, "activation_status", "") or "").lower()
    kind = str(getattr(card, "kind", "promise") or "promise").lower()
    subject = area_name.lower()
    supported = status in ("strongly_supported", "supported")
    active = activation in ("strongly_active", "active")

    if kind == "challenge" or subject.startswith("health"):
        if active:
            return (
                f"Your {subject} is the part of the reading that asks for attention now — "
                f"the current phase keeps this theme live, so the useful response is "
                f"consistency rather than worry."
            )
        return (
            f"Your {subject} is steady enough at the moment, and the sensible aim is to "
            f"protect that rather than test it."
        )
    if supported and active:
        return (
            f"Your {subject} has real backing in the chart, and the current phase is "
            f"actively supporting it — this is a genuine opening rather than a hope."
        )
    if supported and not active:
        return (
            f"Your {subject} carries genuine promise, but the current phase is not yet "
            f"lighting it up, so this is a stretch for preparation rather than a push."
        )
    if status in ("weak", "insufficient_evidence"):
        return (
            f"Your {subject} is not strongly established in the chart, so treat progress "
            f"here as something you build steadily rather than something that arrives."
        )
    return (
        f"Your {subject} reads as mixed: neither the chart nor the current phase gives "
        f"strong backing, so steady, deliberate effort matters more than waiting for a "
        f"perfect moment."
    )


def _area_needs_remedy(card: Any) -> bool:
    status = str(getattr(card, "status", "") or "").lower()
    activation = str(getattr(card, "activation_status", "") or "").lower()
    direction = str(getattr(card, "direction", "") or "").lower()
    kind = str(getattr(card, "kind", "promise") or "promise").lower()
    return (
        kind == "challenge"
        or direction in ("caution", "down", "mixed")
        or status in ("mixed", "weak", "insufficient_evidence")
        or activation in ("mixed", "weak", "inactive", "insufficient_evidence")
    )


def _area_remedy_sentence(card: Any, area_name: str) -> str:
    """Approved per-area step, or a plain practical one when none is supplied."""
    for candidate in (
        getattr(card, "remedy_text", ""),
        *(list(getattr(card, "approved_remedies", None) or [])[:1]),
    ):
        text = str(candidate or "").strip()
        if text:
            return text if text.endswith(".") else f"{text}."
    subject = area_name.lower()
    if str(getattr(card, "kind", "") or "").lower() == "challenge" or subject.startswith("health"):
        return (
            "Keep your routine simple, protect recovery time, and respond early when "
            "something needs attention rather than waiting for it to build."
        )
    return (
        f"Do the groundwork for {subject} now — small, consistent steps put you in "
        f"position when the stronger stretch arrives."
    )


def conversational_fallback(facts: Any) -> dict[str, Any]:
    """Deterministic whole-page prose for the compact conversational template."""
    name = getattr(facts, "first_name", "") or ""
    traits = [str(t).strip() for t in (getattr(facts, "personality_traits", None) or []) if str(t).strip()]
    if traits:
        personality = " ".join(traits[:4])
    else:
        personality = (
            f"{name}, your chart describes a clear personal style that shows up across work, "
            f"relationships and the way you make decisions."
            if name else
            "Your chart describes a clear personal style that shows up across work, "
            "relationships and the way you make decisions."
        )
    tone = str(getattr(facts, "phase_tone", "") or "mixed")
    phase_end = str(getattr(facts, "phase_end", "") or "").strip()
    notes = [str(n).strip() for n in (getattr(facts, "phase_notes", None) or []) if str(n).strip()]
    tone_line = {
        "supportive": "Right now the chapter you are in is broadly supportive — effort tends to land more cleanly than it has in tougher stretches.",
        "demanding": "Right now the chapter you are in is more demanding — progress still comes, but it asks for steadier effort and fewer shortcuts.",
        "mixed": "Right now the chapter you are in is mixed — some parts of life open more easily while others need patience.",
    }.get(tone, "Right now the chapter you are in is mixed — some parts of life open more easily while others need patience.")
    current_phase = tone_line
    # An ISO date here reaches the page as "through 2026-" once the date scrub
    # has taken the day and month it could not vouch for.
    phase_end_said = _month_year(phase_end)
    if phase_end_said:
        current_phase += f" This stretch runs through {phase_end_said}."
    if notes:
        current_phase = (current_phase + " " + " ".join(notes[:2])).strip()

    recent_bits = []
    for i, ev in enumerate(list(getattr(facts, "recent_months", None) or [])[:3]):
        label = str(getattr(ev, "label", "") or getattr(ev, "area", "") or "life")
        headline = str(getattr(ev, "headline", "") or "").strip()
        start = _month_year(getattr(ev, "start", ""))
        end = _month_year(getattr(ev, "end", ""))
        if start and end and start != end:
            when = f"Between {start} and {end}"
        elif start or end:
            when = f"Around {start or end}"
        else:
            when = "In the last few months"
        lead = "" if i else "Looking back, "
        # Only the opening word loses its capital — "april 2026" is a typo to
        # a reader, not a lower-cased sentence.
        opener = (when[0].lower() + when[1:]) if lead else when
        sentence = f"{lead}{opener}, {label.lower()} has been the thread to watch."
        if headline:
            body = headline if headline.endswith(".") else f"{headline}."
            sentence = f"{sentence} {body}"
        recent_bits.append(sentence)
    recent_months = _join_within(recent_bits, 600) if recent_bits else (
        "The recent months have been more about settling into the current chapter than a single dramatic turn."
    )

    hardest = [str(x) for x in (getattr(facts, "hardest_area_labels", None) or []) if str(x).strip()]
    if len(hardest) > 1:
        hardest_note = (
            f"The areas asking for more care right now are {hardest[0]} "
            f"and {hardest[1]}."
        )
    elif hardest:
        hardest_note = f"The area asking for more care right now is {hardest[0]}."
    else:
        hardest_note = ""

    areas = {}
    access = getattr(facts, "access", "free") or "free"
    if access == "paid":
        for c in list(getattr(facts, "cards", None) or []):
            area = getattr(c, "area", "") or ""
            if not area:
                continue
            area_name = str(getattr(c, "label", "") or area.replace("_", " "))
            outlook = _area_outlook_sentence(c, area_name)
            timing = timing_sentence(_window_phrase(c))
            manifests = list(
                getattr(c, "manifestations", None)
                or getattr(c, "manifestation_ids", None)
                or []
            )
            manifestation = ""
            if manifests:
                first = str(manifests[0]).strip().rstrip(".")
                manifestation = f"In practice this tends to show up as {first[0].lower() + first[1:]}."
            remedy = ""
            if _area_needs_remedy(c) or getattr(c, "remedy_text", ""):
                remedy = _area_remedy_sentence(c, area_name)
            tone_label, tone_class = area_tone(c)
            areas[area] = {
                "outlook": outlook[:280],
                "timing": timing[:160],
                "manifestation": manifestation[:160],
                "remedy": remedy[:180],
                "tone_label": tone_label,
                "tone_class": tone_class,
            }
    mind_now, why_now = _life_state_prose(getattr(facts, "life_state", None))
    return {
        "conversational": True,
        "personality": clip_sentences(personality, 900),
        "current_phase": current_phase[:320],
        "recent_months": recent_months,
        "hardest_area_note": hardest_note[:180],
        "mind_now": mind_now,
        "why_now": why_now,
        "family_note": _family_prose(getattr(facts, "family_notes", None)),
        "areas": areas,
    }


_FAMILY_OPENER = {
    "father": "Your father — ",
    "mother": "Your mother — ",
    "siblings": "Brothers and sisters — ",
    "home": "The home you come from — ",
}
_FAMILY_RELATION_WORDS = {
    "father": ("father", "dad", "paternal"),
    "mother": ("mother", "mum", "maternal"),
    "siblings": ("sibling", "brother", "sister", "elder", "youngest", "last-born"),
    "home": ("home", "household", "domestic", "childhood", "upbringing"),
}
_FAMILY_HEDGED = re.compile(
    r"\b(?:reads? as|comes? across|seems?|appears?|usually|often|tends?|may|"
    r"might|likely)\b", re.I,
)


def _family_prose(family_notes: Any) -> list[str]:
    """One deterministic line per relation, from the engines' own sentences.

    The source sentences are already customer-safe and already addressed to
    the reader, so the work here is framing rather than rewriting: a relation
    only one method saw has to arrive as a leaning, and one two methods agreed
    on can say so, because that agreement is the reason to believe it.
    """
    lines: list[str] = []
    for note in list(family_notes or [])[:4]:
        notes = [str(n).strip() for n in (getattr(note, "notes", None) or []) if str(n).strip()]
        if not notes:
            continue
        relation = str(getattr(note, "relation", "") or "")
        try:
            methods = int(getattr(note, "method_count", 0) or 0)
        except (TypeError, ValueError):
            methods = 0
        # The source engines answer about parents in the third person; the
        # page is addressed to the reader.
        body = " ".join(notes[:2])
        body = re.sub(r"\bThe (father|mother)\b", r"Your \1", body)
        body = re.sub(r"\bthe (father|mother)\b", r"your \1", body)
        low = body.lower()
        if not any(w in low for w in _FAMILY_RELATION_WORDS.get(relation, ())):
            body = _FAMILY_OPENER.get(relation, "") + body[0].lower() + body[1:]
        # The qualifier belongs at the end. Leading with it turns every line
        # into a disclaimer and buries the thing the reader came to check.
        if methods <= 1 and not _FAMILY_HEDGED.search(body):
            body += " That is one method's reading rather than a settled fact."
        elif methods > 1:
            body += " More than one method reads it the same way."
        lines.append(clip_sentences(body, 280))
    return lines[:4]


_CHAPTER_TONE_LINE = {
    "supported": (
        "This stretch reads as more supportive than not, which is usually why "
        "it feels like the moment to move rather than wait."
    ),
    "pressured": (
        "This stretch asks more of you than it gives back straight away, which "
        "is usually why it feels heavier than the work alone would explain."
    ),
    "mixed": (
        "This stretch pulls in two directions at once — part of life opens "
        "while another part asks for patience — which is usually why it feels "
        "harder to read than a simple good or bad phase."
    ),
    "steady": (
        "This stretch is steadier than it is dramatic, which is usually why it "
        "feels more like gradual adjustment than a turning point."
    ),
}


def _life_state_prose(life_state: Any) -> tuple[list[str], str]:
    """Deterministic 'what may be on your mind' lines and the why behind them.

    Every line stays a possibility. The block is about what the chart makes
    likely to be occupying them, and the reading has no way to know what is
    actually happening in their life.
    """
    if life_state is None:
        return [], ""
    lines: list[str] = []
    for i, topic in enumerate(list(getattr(life_state, "mind_now", None) or [])[:3]):
        label = str(getattr(topic, "label", "") or "").strip()
        experience = [str(x).strip() for x in (getattr(topic, "experience", None) or []) if str(x).strip()]
        if not label and not experience:
            continue
        likely = str(getattr(topic, "likelihood", "") or "") == "likely"
        head = label or "This part of life"
        lead = "may well" if likely else "may"
        if len(experience) > 1:
            subject = f"{experience[0]} and {experience[1]}"
        elif experience:
            subject = experience[0]
        else:
            subject = ""
        if not subject:
            lines.append(f"{head}: this {lead} be taking more of your attention than usual.")
        elif i == 0:
            lines.append(f"{head}: {subject} {lead} be part of your days right now.")
        elif i == 1:
            lines.append(f"{head}: you {lead} also be sitting with {subject}.")
        else:
            lines.append(f"{head}: {subject} {lead} be somewhere in the background too.")

    tone = str(getattr(life_state, "chapter_tone", "") or "mixed")
    why = _CHAPTER_TONE_LINE.get(tone, _CHAPTER_TONE_LINE["mixed"])
    pressure = str(getattr(life_state, "emotional_pressure", "") or "low")
    decision = str(getattr(life_state, "decision_pressure", "") or "low")
    if pressure in ("high", "very_high"):
        why += (
            " More than one part of life is live at the same time, so the load "
            "is spread thin rather than concentrated in one place."
        )
    if decision in ("high", "very_high"):
        why += (
            " Practical decisions are carrying more weight than usual, which "
            "is tiring in a way that rest alone does not fix."
        )
    if str(getattr(life_state, "uncertainty", "") or "") == "high":
        why += (
            " The methods behind your reading do not all point the same way "
            "here, so treat this as a period to reassess rather than commit."
        )
    return lines[:3], why[:380]


def conversational_palm_fallback(facts: Any) -> dict[str, Any]:
    name = getattr(facts, "first_name", "") or ""
    traits = [str(t).strip() for t in (getattr(facts, "personality_traits", None) or []) if str(t).strip()]
    personality = " ".join(traits[:3]) if traits else (
        f"{name}, your hands show a consistent personal style across temperament, mind and work."
        if name else
        "Your hands show a consistent personal style across temperament, mind and work."
    )
    stage = str(getattr(facts, "life_stage_note", "") or "").strip()
    demanding = str(getattr(facts, "demanding_aspect_label", "") or "").strip()
    current_phase = stage or "Your hands point to a life stage that rewards steadiness over haste."
    hardest = f"The area asking for more care right now is {demanding}." if demanding else ""

    areas = {}
    access = getattr(facts, "access", "free") or "free"
    remedies = list(getattr(facts, "remedies", None) or [])
    remedy_ok = bool(getattr(facts, "remedies_allowed", False))
    if access == "paid":
        for a in list(getattr(facts, "aspects", None) or []):
            key = getattr(a, "aspect", "") or ""
            if not key:
                continue
            title = str(getattr(a, "title", "") or key.replace("_", " "))
            summary = str(getattr(a, "semantic_summary", "") or "").strip()
            strength = str(getattr(a, "strength", "") or "").lower()
            direction = str(getattr(a, "direction", "") or "").lower()
            demanding = (
                direction == "caution"
                or strength in ("weak", "tentative", "challenged")
                or key == str(getattr(facts, "demanding_aspect", "") or "")
            )
            outlook = clean_palm_summary(summary) or (
                f"Your hands read as steady on {title.lower()}."
            )
            if demanding:
                outlook = (
                    f"{outlook} This is one of the areas your hands ask you to look after "
                    f"rather than push."
                )
            recognize = list(getattr(a, "recognize", None) or [])
            manifestation = ""
            if recognize:
                first = str(recognize[0]).strip().rstrip(".")
                manifestation = f"In daily life this shows up as {first[0].lower() + first[1:]}."
            aw = list(getattr(a, "age_window", None) or [])
            timing = ""
            if len(aw) >= 2:
                timing = f"This theme is most noticeable around ages {aw[0]} to {aw[1]}."
            remedy = ""
            if remedy_ok and remedies:
                remedy = remedies[0]
                remedy = remedy if remedy.endswith(".") else f"{remedy}."
            elif demanding:
                remedy = (
                    "Keep your rest, food and working rhythm regular — this area responds "
                    "more to steady habits than to sudden effort."
                )
            areas[key] = {
                "outlook": clip_sentences(outlook, 320),
                "timing": timing[:140],
                "manifestation": clip_sentences(manifestation, 180),
                "remedy": clip_sentences(remedy, 200),
            }
    mind_now, why_now = _palm_state_prose(getattr(facts, "palm_state", None))
    return {
        "conversational": True,
        # Sentence-aware, not sliced: the life-stage note the palm engine
        # supplies runs long, and a hard slice ended the page mid-word.
        "personality": clip_sentences(personality, 360),
        "current_phase": clip_sentences(current_phase, 280),
        "hardest_area_note": clip_sentences(hardest, 160),
        "mind_now": mind_now,
        "why_now": why_now,
        "hand_contrast_note": _hand_contrast_prose(
            getattr(facts, "hand_contrast", None)),
        "areas": areas,
    }


_PALM_TONE_LINE = {
    "supported": (
        "Taken together your hands read as more supportive than not, which is "
        "usually why this feels like a time to act rather than wait."
    ),
    "pressured": (
        "Taken together your hands read as asking more of you than they give "
        "back straight away, which is usually why it feels heavier than the "
        "work alone would explain."
    ),
    "mixed": (
        "Your hands pull in two directions at once — part of life reads open "
        "while another part asks for patience — which is usually why this "
        "stretch is harder to read than a simple good or bad phase."
    ),
    "steady": (
        "Your hands read as steadier than they are dramatic, which is usually "
        "why this feels like gradual adjustment rather than a turning point."
    ),
}


def _palm_state_prose(palm_state: Any) -> tuple[list[str], str]:
    """Deterministic 'what may be on your mind' lines for a palm reading.

    Every line stays a possibility. A hand can show a tendency or an unmet
    need; it cannot know what is actually happening in someone's life.
    """
    if palm_state is None:
        return [], ""
    lines: list[str] = []
    for i, topic in enumerate(list(getattr(palm_state, "mind_now", None) or [])[:3]):
        label = str(getattr(topic, "label", "") or "").strip()
        experience = [str(x).strip() for x in (getattr(topic, "experience", None) or []) if str(x).strip()]
        if not label and not experience:
            continue
        likely = str(getattr(topic, "likelihood", "") or "") == "likely"
        head = label or "This part of life"
        lead = "may well" if likely else "may"
        if len(experience) > 1:
            subject = f"{experience[0]} and {experience[1]}"
        elif experience:
            subject = experience[0]
        else:
            subject = ""
        if not subject:
            lines.append(f"{head}: this {lead} be taking more of your attention than usual.")
        elif i == 0:
            lines.append(f"{head}: {subject} {lead} be part of your days right now.")
        elif i == 1:
            lines.append(f"{head}: you {lead} also be sitting with {subject}.")
        else:
            lines.append(f"{head}: {subject} {lead} be somewhere in the background too.")

    tone = str(getattr(palm_state, "chapter_tone", "") or "mixed")
    why = _PALM_TONE_LINE.get(tone, _PALM_TONE_LINE["mixed"])
    note = str(getattr(palm_state, "confidence_note", "") or "").strip()
    if str(getattr(palm_state, "uncertainty", "") or "") == "high":
        why += (
            " Your two hands do not tell quite the same story here, so treat "
            "this as a period to reassess rather than commit."
        )
    if note:
        why = f"{why} {note}"
    return lines[:3], clip_sentences(why, 380)


def _hand_contrast_prose(contrast: Any) -> str:
    """The two-hand story, in the reader's own terms.

    This is the most persuasive paragraph on a palm page, so it says only what
    the comparison found: which parts are long-standing, which were grown into,
    and which are there with less room than they want.
    """
    if contrast is None:
        return ""
    dominant = str(getattr(contrast, "dominant_hand", "") or "right").lower()
    other = "left" if dominant == "right" else "right"
    steady = [str(x) for x in (getattr(contrast, "steady", None) or [])]
    developed = [str(x) for x in (getattr(contrast, "developed", None) or [])]
    latent = [str(x) for x in (getattr(contrast, "latent", None) or [])]
    traits = [str(x) for x in (getattr(contrast, "developed_traits", None) or [])]
    latent_traits = [str(x) for x in (getattr(contrast, "latent_traits", None) or [])]
    if not (steady or developed or latent or traits or latent_traits):
        return ""

    parts = [
        f"Your {other} hand reads as what you started with, and your "
        f"{dominant} hand as what you have made of it."
    ]
    if steady:
        parts.append(
            f"{_join(steady).capitalize()} read much the same on both, so that "
            "part of you looks long-standing rather than recent."
        )
    if developed:
        parts.append(
            f"{_join(developed).capitalize()} reads stronger on your "
            f"{dominant} hand, which usually means you grew into it through "
            "experience rather than starting there."
        )
    if latent:
        parts.append(
            f"{_join(latent).capitalize()} reads stronger on your {other} "
            "hand, which tends to mean it is there underneath with less room "
            "than it wants."
        )
    if traits and not developed:
        parts.append(
            f"Your lived hand also suggests more {_join(traits)} than you "
            "may have had earlier on."
        )
    if latent_traits and not latent:
        # The most recognisable line on the page for many readers: a strength
        # the underlying hand carries but daily life gives no room to.
        parts.append(
            f"There may also be more {_join(latent_traits)} in you than your "
            "routine currently asks for."
        )
    return clip_sentences(" ".join(parts), 380)


def _join(items: list[str]) -> str:
    # Three is where a list still reads as a sentence; four themes joined with
    # commas turned the two-hand paragraph into an inventory.
    items = [x for x in items if x][:3]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def question_fallback(facts: Any) -> dict[str, Any]:
    status = getattr(facts, "promise_status", "") or ""
    direction = getattr(facts, "direction", "mixed") or "mixed"
    area = getattr(facts, "area_key", "this question") or "this question"
    conf = getattr(facts, "confidence", "moderate") or "moderate"
    dir_word = {
        "support": "supports", "up": "supports",
        "caution": "does not strongly favour", "down": "does not strongly favour",
        "mixed": "is mixed on", "neutral": "is mixed on",
    }.get(direction, "is mixed on")
    answer = (
        f"Your chart {dir_word} {area}. "
        f"Confidence from the available methods is {conf}."
    )
    if status in ("weak", "insufficient_evidence"):
        answer = (
            f"The available chart facts do not support a high-confidence claim "
            f"for {area}."
        )
    timing = ""
    best = getattr(facts, "best", None)
    if best is not None:
        label = getattr(best, "label", "") or ""
        if label:
            timing = f"The strongest validated window note is: {label}."
        else:
            timing = "Validated timing windows are listed in the reading below."
    return {
        "opening": "Here is the straight answer from your chart facts.",
        "answer": answer[:420],
        "timing": timing[:220],
        "action": "Prepare within the validated windows rather than forcing a date.",
    }


def horary_fallback(facts: Any) -> dict[str, Any]:
    label = getattr(facts, "label", "Genuinely open") or "Genuinely open"
    conf = getattr(facts, "confidence", "moderate") or "moderate"
    subject = getattr(facts, "subject", "this") or "this"
    return {
        "lead": f"You asked about {subject}. Here is the combined reading.",
        "verdict_line": f"The reading reads as: {label} (confidence {conf}).",
        "why": "The moment-chart methods were combined under the product's weighting rules.",
        "action": "Act on the answer as framed — a horary chart speaks to this question only.",
    }


def palm_fallback(facts: Any) -> dict[str, Any]:
    aspects = {}
    for a in getattr(facts, "aspects", None) or []:
        key = getattr(a, "aspect", "") or ""
        if not key:
            continue
        direction = getattr(a, "direction", "mixed") or "mixed"
        tags = list(getattr(a, "semantic_tags", None) or [])
        summary = str(getattr(a, "semantic_summary", "") or "").strip()
        headline = (
            summary[:140] if summary else
            f"Your {key.replace('_', ' ')} pattern reads as {direction}."
        )
        aspects[key] = {
            "headline": headline,
            "why": "Based on the measured palm signals for this life theme.",
            "points": [str(t)[:120] for t in tags[:3]],
        }
    name = getattr(facts, "first_name", "") or ""
    opening = (
        f"{name}, here is what both hands show together."
        if name else
        "Here is what both hands show together."
    )
    return {"opening": opening, "aspects": aspects}
