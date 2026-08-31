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
def _reading_row(reading: Any, *, both: bool = False, lang: str = "en") -> str:
    """Sign → reading → what to do, in that order. The palmist's sequence."""
    from .palm_localization import (
        translate_feature_name, translate_sign_text,
        translate_means_text, translate_remedy_text
    )
    lang_code = str(lang or "").lower().strip()
    is_hi = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_te = lang_code in ("te_en", "tenglish", "te", "telugu")
    tone = reading.tone if reading.tone in ("strong", "care") else "steady"
    if is_te:
        tag = {"strong": "Mukhya Shakthi", "care": "Jagrattha Avashyakam"}.get(tone, "")
    elif is_hi:
        tag = {"strong": "Mukhya Shakti", "care": "Dhyan Dein"}.get(tone, "")
    else:
        tag = {"strong": "A strength", "care": "Needs care"}.get(tone, "")
    pill = (f'<span class="pv-pill {tone}">{_e(tag)}</span>' if tag else "")
    if both:
        agree_txt = "rendu chethulalo" if is_te else ("dono haatho mein" if is_hi else "in both hands")
        agree = f'<span class="pv-both">&#10003; {agree_txt}</span>'
    else:
        agree = ""
    when = ""
    if getattr(reading, "age_range", None):
        low, high = reading.age_range
        prefix = "aayu" if (is_hi or is_te) else "ages"
        when = f'<span class="pv-when">{prefix} {low}&ndash;{high}</span>'
    elif getattr(reading, "age", None):
        prefix = "dhadhapu aayu" if is_te else ("lagbhag aayu" if is_hi else "around age")
        when = f'<span class="pv-when">{prefix} {reading.age}</span>'
    remedy = ""
    rem_text = translate_remedy_text(reading.remedy, is_hinglish=is_hi, is_tenglish=is_te) if reading.remedy else ""
    if rem_text:
        do_lbl = "Karanam / Upayam" if is_te else ("Karan / Upay" if is_hi else "What to do")
        remedy = (f'<p class="pv-do"><span class="ev-label">{do_lbl}</span> '
                  f"{_e(_sentence(rem_text))}</p>")
    
    feat = translate_feature_name(reading.feature, is_hinglish=is_hi, is_tenglish=is_te)
    sign = translate_sign_text(reading.sign, is_hinglish=is_hi, is_tenglish=is_te)
    means = translate_means_text(reading.means, is_hinglish=is_hi, is_tenglish=is_te)
    return f"""
<div class="pv-row {tone}">
  <div class="pv-head"><b>{_e(feat)}</b>{pill}{agree}{when}</div>
  <p class="pv-sign">{_e(_sentence(sign))}</p>
  <p class="pv-means">{_e(_sentence(means))}</p>
  {remedy}
</div>"""


def _observation(reading: Any, *, both: bool = False, lang: str = "en") -> str:
    """One more thing the same line says, under a heading already written."""
    from .palm_localization import (
        translate_sign_text, translate_means_text, translate_remedy_text
    )
    lang_code = str(lang or "").lower().strip()
    is_hi = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_te = lang_code in ("te_en", "tenglish", "te", "telugu")
    tone = reading.tone if reading.tone in ("strong", "care") else "steady"
    if is_te:
        tag = {"strong": "Mukhya Shakthi", "care": "Jagrattha Avashyakam"}.get(tone, "")
    elif is_hi:
        tag = {"strong": "Mukhya Shakti", "care": "Dhyan Dein"}.get(tone, "")
    else:
        tag = {"strong": "A strength", "care": "Needs care"}.get(tone, "")
    marks = (f'<span class="pv-pill {tone}">{_e(tag)}</span>' if tag else "")
    if both:
        agree_txt = "rendu chethulalo" if is_te else ("dono haatho mein" if is_hi else "in both hands")
        marks += f'<span class="pv-both">&#10003; {agree_txt}</span>'
    if getattr(reading, "age_range", None):
        low, high = reading.age_range
        prefix = "aayu" if (is_hi or is_te) else "ages"
        marks += f'<span class="pv-when">{prefix} {low}&ndash;{high}</span>'
    elif getattr(reading, "age", None):
        prefix = "dhadhapu aayu" if is_te else ("lagbhag aayu" if is_hi else "around age")
        marks += f'<span class="pv-when">{prefix} {reading.age}</span>'
    remedy = ""
    rem_text = translate_remedy_text(reading.remedy, is_hinglish=is_hi, is_tenglish=is_te) if reading.remedy else ""
    if rem_text:
        do_lbl = "Karanam / Upayam" if is_te else ("Karan / Upay" if is_hi else "What to do")
        remedy = (f'<p class="pv-do"><span class="ev-label">{do_lbl}</span> '
                  f"{_e(_sentence(rem_text))}</p>")
    
    sign = translate_sign_text(reading.sign, is_hinglish=is_hi, is_tenglish=is_te)
    means = translate_means_text(reading.means, is_hinglish=is_hi, is_tenglish=is_te)
    return (f'<div class="pv-obs {tone}">'
            f'<p class="pv-sign">{_e(_sentence(sign))}{marks}</p>'
            f'<p class="pv-means">{_e(_sentence(means))}</p>'
            f"{remedy}</div>")


def _rows(readings: Iterable[Any], agree: set[str] | None = None, lang: str = "en") -> str:
    """Group by feature so a line is named once and then read.

    A palmist says "your head line" and then tells you the three things it
    shows. Printing the name again above every observation turned the reading
    into an inventory — "Head line", "Head line", "Head line" down the page.
    """
    from .palm_localization import translate_feature_name
    lang_code = str(lang or "").lower().strip()
    is_hi = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_te = lang_code in ("te_en", "tenglish", "te", "telugu")
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
            out.append(_reading_row(items[0], both=items[0].key in agree, lang=lang))
            continue
        tones = {r.tone for r in items}
        tone = "care" if "care" in tones else (
            "strong" if "strong" in tones else "steady")
        body = "".join(_observation(r, both=r.key in agree, lang=lang) for r in items)
        feat_lbl = translate_feature_name(feature, is_hinglish=is_hi, is_tenglish=is_te)
        out.append(f'<div class="pv-row {tone}">'
                   f'<div class="pv-head"><b>{_e(feat_lbl)}</b></div>'
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

_GRADE_NOTE_HI = {
    "good": "bareek chinho aur age timing ko padhne ke liye saaf photo",
    "fair": "mukhya rekhaon ke liye saaf, parantu bareek chinho ke liye thoda simit",
    "poor": "bareek chinho ya age positions ke liye spasht nahi; keval broad pattern aur rekhaon ka mukhya aakar padha gaya hai",
}

_GRADE_NOTE_TE = {
    "good": "sukshma chihnalu mariyu age timing chadhavadaniki saraina photo",
    "fair": "mukhya rekhalaku spashtamga undi, kani sukshma chihnalaku konchem parimitham",
    "poor": "sukshma chihnalu leda age positions ku spashtamga ledu; kevalam broad pattern mariyu rekhalu matrame chadavabaddayi",
}


def _photo_note(raw: dict, lang: str = "en") -> str:
    lang_code = str(lang or "").lower().strip()
    is_hi = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_te = lang_code in ("te_en", "tenglish", "te", "telugu")
    rows = ""
    for hand in ("left", "right"):
        block = raw.get(hand) or {}
        if not block:
            continue
        grade = str(((block.get("features") or {}).get("quality") or {})
                    .get("grade") or "fair").lower()
        if is_te:
            desc = _GRADE_NOTE_TE.get(grade, _GRADE_NOTE_TE["fair"])
        elif is_hi:
            desc = _GRADE_NOTE_HI.get(grade, _GRADE_NOTE_HI["fair"])
        else:
            desc = _GRADE_NOTE.get(grade, _GRADE_NOTE["fair"])
        h_name = f"{hand.title()} Hand" if (is_hi or is_te) else f"{hand.title()} hand"
        rows += (f'<li><b>{h_name}</b> — photo grade {_e(grade)}: '
                 f"{_e(desc)}.</li>")
    if not rows:
        return ""
    
    if is_te:
        card_title = "Photo Quality Mariyu Vishleshana Samarthyam"
        fine_txt = ("Samudrika Shastram lo chethini velugulo tiripi pariseelistharu. "
                    "Photo aadharamga memu spashtamga kanipinche vishayalanu matrame report chestham.")
    elif is_hi:
        card_title = "Photo Quality Aur Vishleshan Kshamta"
        fine_txt = ("Samudrika Shastra mein haath ko roshni mein ghumakar dekha jata hai. "
                    "Photo ke aadhar par hum wahi darshate hain jo spasht roop se dekha ja sake.")
    else:
        card_title = "What each photograph allows"
        fine_txt = ("A palmist holds the hand and turns it to the light. "
                    "Working from a photograph, we say plainly what the photograph will "
                    "and will not support rather than guessing past it.")
    return (f'<div class="card"><div class="ev-label">{card_title}</div><ul class="pv-plain">{rows}</ul>'
            f'<p class="fine">{fine_txt}</p></div>')


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


def _marks_section(readings: dict, raw: dict, lang: str = "en") -> str:
    from .palm_localization import localize_mark
    lang_code = str(lang or "").lower().strip()
    is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")
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
        if is_tenglish:
            tag = {"strong": "Mukhya Shakthi", "care": "Jagrattha Avashyakam"}.get(tone, "")
        elif is_hinglish:
            tag = {"strong": "Mukhya Shakti", "care": "Dhyan Dein"}.get(tone, "")
        else:
            tag = {"strong": "A strength", "care": "Needs care"}.get(tone, "")
        pill = f'<span class="pv-pill {tone}">{_e(tag)}</span>' if tag else ""
        if is_tenglish:
            both_badge = (
                '<span class="pv-both">&#10003; rendu chethulalo (Uchha vishwasam)</span>'
                if is_both else
                f'<span class="pv-pill neutral">{hands[0].title()} Hand meeda drishtigatham · Madhyama vishwasam</span>'
            )
        elif is_hinglish:
            both_badge = (
                '<span class="pv-both">&#10003; dono haatho mein (Uchha vishwas)</span>'
                if is_both else
                f'<span class="pv-pill neutral">{hands[0].title()} Hand par drishtigat · Santulit vishwas</span>'
            )
        else:
            both_badge = (
                '<span class="pv-both">&#10003; in both hands (High confidence)</span>'
                if is_both else
                f'<span class="pv-pill neutral">Seen on {hands[0].title()} hand · Moderate confidence</span>'
            )

        feat, sign, means, remedy_txt = localize_mark(
            mark.feature, mark.sign, mark.means, mark.remedy, is_hinglish=is_hinglish, is_tenglish=is_tenglish
        )

        remedy = ""
        if remedy_txt:
            if is_tenglish:
                guidance_lbl = "Vedic Margadarshanam"
            elif is_hinglish:
                guidance_lbl = "Vedic Margdarshan"
            else:
                guidance_lbl = "Traditional Guidance"
            remedy = (f'<p class="pv-do"><span class="ev-label">{guidance_lbl}</span> '
                      f"{_e(_sentence(remedy_txt))}</p>")

        rows += f"""
<div class="pv-row {tone}">
  <div class="pv-head"><b>{_e(feat)}</b>{pill}{both_badge}</div>
  <p class="pv-sign">{_e(_sentence(sign))}</p>
  <p class="pv-means">{_e(_sentence(means))}</p>
  {remedy}
</div>"""

    blocked = [h for h in ("right", "left")
               if readings.get(h) and not readings[h].marks_allowed]
    note = ""
    if blocked:
        which = " and ".join(h.title() for h in blocked)
        if is_tenglish:
            note = ("Sukshma chihnalu mee " + _e(which) + " hand photo nunchi report cheyaledu — "
                    "ee grade lo needa mariyu chihnam madhya theda thelusukovatam kashtam. "
                    "Manchi vishleshana kosam velugulo photo theeyandi.")
        elif is_hinglish:
            note = (("Bareek chinh aapke " + _e(which) + " hand photo se report nahi kiye gaye hain — "
                     "is grade par shadow aur mark mein bhed karna kathin hota hai. "
                     "Behtar vishleshan ke liye spasht roshni mein photo lein."))
        else:
            note = (f'<p class="fine">Fine marks are not reported from your '
                    f"{_e(which)} hand photograph — at that grade a shadow and a star "
                    f"look alike, and a mark invented from a blur is worse than no "
                    f"mark at all. Retake that hand straight-on in bright, even "
                    f"light to have it read.</p>")
    if not rows and not note:
        return ""
    if not rows:
        if is_tenglish:
            rows = '<p class="pv-means">Etuvanthi vishesha chihnalu spashtamga drishtigatham kaledu.</p>'
        elif is_hinglish:
            rows = '<p class="pv-means">Koi vishesh chinh spasht roop se drishtigat nahi hua.</p>'
        else:
            rows = '<p class="pv-means">No special mark was resolved clearly enough to report.</p>'
    if is_tenglish:
        marks_title = "Mee Chethula Vishesha Chihnalu (Special Marks)"
        marks_sub = "Chethi vishesha chihnalu (Trishulam, Thaara, Mathsya) parvathala shakthini penchuthayi."
        marks_nav = "Vishesha Chihnalu"
    elif is_hinglish:
        marks_title = "Aapke Hatho Ke Vishesh Chinh (Special Marks)"
        marks_sub = "Haath ke vishesh chinh (jaise Trishul, Tara, Matsya) parvato ki shakti ko badhate hain."
        marks_nav = "Vishesh Chinh"
    else:
        marks_title = "The special marks on your hands"
        marks_sub = "A mark modifies the mount beneath it. It is read together with the lines around it, never on its own."
        marks_nav = "Special marks"
    return _section(
        "sec-marks", marks_title,
        marks_sub,
        f'<div class="card">{rows}{note}</div>', nav=marks_nav)


# ---------------------------------------------------------------------------
# dated markings
# ---------------------------------------------------------------------------
def _split_prediction(text: str) -> tuple[str, str]:
    parts = re.split(r"(?i)(?:\r?\n|\s+)Why:\s*", str(text or ""), maxsplit=1)
    head = parts[0].strip()
    why = parts[1].strip() if len(parts) == 2 else ""
    return head, why


def _timeline(conf: dict, age: int, *, ahead: bool, lang: str = "en") -> str:
    lang_code = str(lang or "").lower().strip()
    is_hi = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_te = lang_code in ("te_en", "tenglish", "te", "telugu")
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
            window = f"aayu {clamped_low}&ndash;{clamped_high} varshalu" if is_te else (f"aayu {clamped_low}&ndash;{clamped_high} varsh" if is_hi else f"ages {clamped_low}&ndash;{clamped_high}")
        else:
            if len(span) == 2 and span[1] > span[0]:
                window = f"aayu {span[0]}&ndash;{span[1]} varshalu" if is_te else (f"aayu {span[0]}&ndash;{span[1]} varsh" if is_hi else f"ages {span[0]}&ndash;{span[1]}")
            else:
                window = f"dhadhapu aayu {when} varshalu" if is_te else (f"lagbhag aayu {when} varsh" if is_hi else f"around age {when}")
        
        conf_lbl = "Madhyama Vishwasam" if is_te else ("Santulit Vishwas" if is_hi else "Moderate Confidence")
        confidence_tag = f'<span class="pill-conf" style="font-size:0.7rem;font-weight:600;padding:2px 6px;border-radius:10px;background:#f0efe9;color:#5a554c;margin-left:8px;">{conf_lbl}</span>'
        
        sign_lbl = "Drishtigatha Rekha:" if is_te else ("Drishtigat Rekha:" if is_hi else "Observed Physical Sign:")
        backing_feat = f'<p class="pv-sign" style="font-size:0.83rem;color:#6b7280;margin:4px 0 0 0;"><b>{sign_lbl}</b> Traced along {_e(why)}.</p>' if why else ""
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
    pill = f'<span class="pv-pill strong">{_e(tag)}</span>' if tag else ""
    return (f'<article class="card conv-area" data-astrology-facts="1">'
            f'<div class="card-top"><span class="area">{_e(title)}</span>{pill}</div>'
            f"{body}</article>")


def _vedic_life_reading(conf: dict, first: str, lang: str = "en") -> str:
    """Deterministic Vedic predictive profile: personality, profession, spouse,
    wealth, health, and authentic planetary upayas."""
    from .palm_localization import (
        VEDIC_ASPECT_TITLES_HI, VEDIC_ASPECT_TITLES_TE,
        VEDIC_UPAYA_HEADINGS_HI, VEDIC_UPAYA_HEADINGS_TE,
        localize_vedic_text, localize_trait_item
    )
    lang_code = str(lang or "").lower().strip()
    is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")
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
    arch_sum = localize_vedic_text(archetype.get("summary") or "", is_hinglish=is_hinglish, is_tenglish=is_tenglish)
    pers_bits = [f"<p>{arch_sum}</p>"] if arch_sum else []
    traits = [t for t in personality if isinstance(t, dict) and t.get("text")]
    if traits:
        trait_items = []
        for t in traits:
            t_name, t_desc = localize_trait_item(t.get("trait", ""), t.get("text", ""), is_hinglish=is_hinglish, is_tenglish=is_tenglish)
            trait_items.append(f'<li><b>{_e(t_name)}:</b> {t_desc}</li>')
        pers_bits.append(
            '<ul class="pv-plain" style="margin-top:10px;">'
            + "".join(trait_items)
            + "</ul>")
    upaya_mind = _ASPECT_VEDIC_UPAYAS.get("mind", {}).get("upaya")
    if upaya_mind:
        if is_tenglish:
            head_up = VEDIC_UPAYA_HEADINGS_TE["Mind & Intellect"]
        elif is_hinglish:
            head_up = VEDIC_UPAYA_HEADINGS_HI["Mind & Intellect"]
        else:
            head_up = "Targeted Vedic Upaya (Mind &amp; Intellect):"
        pers_bits.append(
            f'<div style="background:#fcf8f2;border-left:3px solid #c97d3e;padding:10px 14px;border-radius:6px;margin-top:10px;font-size:0.84rem;line-height:1.45;color:#4a453c;">'
            f'<b style="color:#7a4b18;">{head_up}</b><br>{upaya_mind}</div>'
        )
    if pers_bits:
        if is_tenglish:
            c_title, c_tag = VEDIC_ASPECT_TITLES_TE["Mind, Intellect & Temperament"]
        elif is_hinglish:
            c_title, c_tag = VEDIC_ASPECT_TITLES_HI["Mind, Intellect & Temperament"]
        else:
            c_title, c_tag = ("Mind, Intellect & Temperament", "Intellect & Disposition")
        cards.append(_vedic_card(c_title, "".join(pers_bits), c_tag))

    # 2 — Profession, Leadership & Career Trajectory
    prof_txt = localize_vedic_text(profession.get("summary") or "", is_hinglish=is_hinglish, is_tenglish=is_tenglish)
    if prof_txt:
        win = profession.get("window")
        tag = "Career Mariyu Udyogam" if is_tenglish else ("Career Aur Karya-Kshetra" if is_hinglish else "Career & Vocation")
        win_note = ""
        if isinstance(win, list) and len(win) == 2:
            if is_tenglish:
                lbl_win = f"<b>Mukhya Career Sthiratha Samayam:</b> Aayu {int(win[0])}–{int(win[1])} varshalu."
                tag = f"Career · Sthiratha {int(win[0])}–{int(win[1])} varshalu"
            elif is_hinglish:
                lbl_win = f"<b>Mukhya Career Establishment Samay:</b> Aayu {int(win[0])}–{int(win[1])} varsh."
                tag = f"Career · Sthirata {int(win[0])}–{int(win[1])} varsh"
            else:
                lbl_win = f"<b>Major Vocational Establishment Window:</b> Ages {int(win[0])}–{int(win[1])}."
                tag = f"Career · Establishes {int(win[0])}–{int(win[1])}"
            win_note = f"<p style='margin:6px 0 0;font-size:0.85rem;color:#6a7080;'>{lbl_win}</p>"

        prof_body = [f"<p>{prof_txt}</p>{win_note}"]
        upaya_car = _ASPECT_VEDIC_UPAYAS.get("career", {}).get("upaya")
        if upaya_car:
            if is_tenglish:
                head_up = VEDIC_UPAYA_HEADINGS_TE["Career & Status"]
            elif is_hinglish:
                head_up = VEDIC_UPAYA_HEADINGS_HI["Career & Status"]
            else:
                head_up = "Targeted Vedic Upaya (Career &amp; Status):"
            prof_body.append(
                f'<div style="background:#fcf8f2;border-left:3px solid #c97d3e;padding:10px 14px;border-radius:6px;margin-top:10px;font-size:0.84rem;line-height:1.45;color:#4a453c;">'
                f'<b style="color:#7a4b18;">{head_up}</b><br>{upaya_car}</div>'
            )
        basis = profession.get("basis")
        if basis:
            b_lbl = "Jyotisha Hastha Aadharam:" if is_tenglish else ("Jyotishiya Palm Adhar:" if is_hinglish else "Astrological Palm Basis:")
            prof_body.append(f'<div style="border-top:1px solid #eeeae3;padding-top:8px;margin-top:10px;font-size:0.75rem;color:#7a756c;"><b>{b_lbl}</b> {_e(basis)}</div>')
        if is_tenglish:
            c_title, _ = VEDIC_ASPECT_TITLES_TE["Career Trajectory, Status & Leadership"]
        elif is_hinglish:
            c_title, _ = VEDIC_ASPECT_TITLES_HI["Career Trajectory, Status & Leadership"]
        else:
            c_title, _ = ("Career Trajectory, Status & Leadership", "")
        cards.append(_vedic_card(c_title, "".join(prof_body), tag))

    # 3 — Marriage, Partnerships & Spouse Dynamics
    mar_txt = localize_vedic_text(marriage.get("summary") or "", is_hinglish=is_hinglish, is_tenglish=is_tenglish)
    if mar_txt:
        mar_body = [f"<p>{mar_txt}</p>"]
        upaya_love = _ASPECT_VEDIC_UPAYAS.get("love", {}).get("upaya")
        if upaya_love:
            if is_tenglish:
                head_up = VEDIC_UPAYA_HEADINGS_TE["Harmony & Partnership"]
            elif is_hinglish:
                head_up = VEDIC_UPAYA_HEADINGS_HI["Harmony & Partnership"]
            else:
                head_up = "Targeted Vedic Upaya (Harmony &amp; Partnership):"
            mar_body.append(
                f'<div style="background:#fcf8f2;border-left:3px solid #c97d3e;padding:10px 14px;border-radius:6px;margin-top:10px;font-size:0.84rem;line-height:1.45;color:#4a453c;">'
                f'<b style="color:#7a4b18;">{head_up}</b><br>{upaya_love}</div>'
            )
        basis = marriage.get("basis")
        if basis:
            b_lbl = "Jyotisha Hastha Aadharam:" if is_tenglish else ("Jyotishiya Palm Adhar:" if is_hinglish else "Astrological Palm Basis:")
            mar_body.append(f'<div style="border-top:1px solid #eeeae3;padding-top:8px;margin-top:10px;font-size:0.75rem;color:#7a756c;"><b>{b_lbl}</b> {_e(basis)}</div>')
        if is_tenglish:
            c_title, c_tag = VEDIC_ASPECT_TITLES_TE["Love, Marriage & Partner Compatibility"]
        elif is_hinglish:
            c_title, c_tag = VEDIC_ASPECT_TITLES_HI["Love, Marriage & Partner Compatibility"]
        else:
            c_title, c_tag = ("Love, Marriage & Partner Compatibility", "Partnership & Dharma")
        cards.append(_vedic_card(c_title, "".join(mar_body), c_tag))

    # 4 — Wealth, Assets & Financial Trajectory
    wea_txt = localize_vedic_text(wealth.get("summary") or "", is_hinglish=is_hinglish, is_tenglish=is_tenglish)
    if wea_txt:
        wea_body = [f"<p>{wea_txt}</p>"]
        upaya_wea = _ASPECT_VEDIC_UPAYAS.get("wealth", {}).get("upaya")
        if upaya_wea:
            if is_tenglish:
                head_up = VEDIC_UPAYA_HEADINGS_TE["Wealth & Abundance"]
            elif is_hinglish:
                head_up = VEDIC_UPAYA_HEADINGS_HI["Wealth & Abundance"]
            else:
                head_up = "Targeted Vedic Upaya (Wealth &amp; Abundance):"
            wea_body.append(
                f'<div style="background:#fcf8f2;border-left:3px solid #c97d3e;padding:10px 14px;border-radius:6px;margin-top:10px;font-size:0.84rem;line-height:1.45;color:#4a453c;">'
                f'<b style="color:#7a4b18;">{head_up}</b><br>{upaya_wea}</div>'
            )
        basis = wealth.get("basis")
        if basis:
            b_lbl = "Jyotisha Hastha Aadharam:" if is_tenglish else ("Jyotishiya Palm Adhar:" if is_hinglish else "Astrological Palm Basis:")
            wea_body.append(f'<div style="border-top:1px solid #eeeae3;padding-top:8px;margin-top:10px;font-size:0.75rem;color:#7a756c;"><b>{b_lbl}</b> {_e(basis)}</div>')
        if is_tenglish:
            c_title, c_tag = VEDIC_ASPECT_TITLES_TE["Wealth Accumulation & Financial Trajectory"]
        elif is_hinglish:
            c_title, c_tag = VEDIC_ASPECT_TITLES_HI["Wealth Accumulation & Financial Trajectory"]
        else:
            c_title, c_tag = ("Wealth Accumulation & Financial Trajectory", "Wealth & Resources")
        cards.append(_vedic_card(c_title, "".join(wea_body), c_tag))

    # 5 — Health, Physical Vitality & Immunity
    upaya_hlth = _ASPECT_VEDIC_UPAYAS.get("health", {}).get("upaya")
    if is_tenglish:
        hlth_raw = "<p>Mee jeevana rekha mariyu Shukra Parvatham <b>sthira shareeraka stamina, natural resilience mariyu manchi recovery samarthyam</b> chupisthunnayi. Niyamitha dincharya mee urjanu kapaduthundi.</p>"
    elif is_hinglish:
        hlth_raw = "<p>Aapki jeevan rekha aur Shukra Parvat <b>sthir sharirik stamina, natural resilience aur achhi recovery kshamta</b> ko darshate hain. Niyamit dhyan aur santulit routine aapki urja ko banaye rakhta hai.</p>"
    else:
        hlth_raw = ("<p>Your life line and Mount of Venus indicate <b>steady baseline stamina, natural physical resilience, and strong vital recovery</b>. "
                    "Maintaining regular nervous system relaxation and grounding physical routines ensures sustained high-performance energy.</p>")
    hlth_body = [hlth_raw]
    if upaya_hlth:
        if is_tenglish:
            head_up = VEDIC_UPAYA_HEADINGS_TE["Health & Vitality"]
        elif is_hinglish:
            head_up = VEDIC_UPAYA_HEADINGS_HI["Health & Vitality"]
        else:
            head_up = "Targeted Vedic Upaya (Health &amp; Vitality):"
        hlth_body.append(
            f'<div style="background:#fcf8f2;border-left:3px solid #c97d3e;padding:10px 14px;border-radius:6px;margin-top:10px;font-size:0.84rem;line-height:1.45;color:#4a453c;">'
            f'<b style="color:#7a4b18;">{head_up}</b><br>{upaya_hlth}</div>'
        )
    if is_tenglish:
        c_title, c_tag = VEDIC_ASPECT_TITLES_TE["Health, Physical Vitality & Stamina"]
    elif is_hinglish:
        c_title, c_tag = VEDIC_ASPECT_TITLES_HI["Health, Physical Vitality & Stamina"]
    else:
        c_title, c_tag = ("Health, Physical Vitality & Stamina", "Vitality & Prana")
    cards.append(_vedic_card(c_title, "".join(hlth_body), c_tag))

    if not cards:
        return ""
    if is_tenglish:
        vedic_title = f"{first}, Mee Mukhya Jeevitha Rangalu"
        vedic_sub = "Samudrika Shastra sampradayam prakaram mee chethi rekhalu mariyu parvathala vishleshana."
        vedic_nav = "Jeevitha Rangalu"
    elif is_hinglish:
        vedic_title = f"{first}, Aapke Mukhya Jeevan Kshetra"
        vedic_sub = "Samudrika Shastra ke adhar par aapki palm lines aur parvato ka gehra vishleshan."
        vedic_nav = "Jeevan Kshetra"
    else:
        vedic_title = f"{first}, your Core Life Readings"
        vedic_sub = "A synthesized Vedic reading in the classical tradition of Samudrika Shastra, built strictly from the lines, mounts, and signs measured on your palms."
        vedic_nav = "Life Domains"
    return _section(
        "sec-vedic", vedic_title,
        vedic_sub,
        "".join(cards), nav=vedic_nav)


def _clean_contrast_label(feature: str, sign: str, *, is_active: bool = True, lang: str = "en") -> str:
    lang_code = str(lang or "").lower().strip()
    is_hi = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_te = lang_code in ("te_en", "tenglish", "te", "telugu")
    f = str(feature or "").strip()
    s = str(sign or "").strip()
    f_low = f.lower()
    s_low = s.lower()
    if "mercury" in f_low:
        if is_te:
            return ("<b>Vyaparika Kushalatha Mariyu Vak-Chathuryam</b> — Meeru sharp communication skills, negotiation confidence mariyu practical business judgment develop chesukunnaru." if is_active else
                    "<b>Janma Tho Vachina Jigyasa</b> — Sahajamaina conversational curiosity mariyu observation instinct.")
        if is_hi:
            return ("<b>Vyaparik Kushalta Aur Vani</b> — Aapne kushal communication skills, negotiation confidence aur practical business judgment develop kiya hai." if is_active else
                    "<b>Janma Se Mili Jigyasa</b> — Swabhavik baatcheet ki curiosity aur observational instinct.")
        if is_active:
            return "<b>Commercial Acumen &amp; Speech</b> — You have developed sharp communication skills, negotiation confidence, and practical business judgment."
        return "<b>Innate Inquisitiveness</b> — Natural conversational curiosity and thoughtful observational instinct."
    if "venus" in f_low:
        if is_te:
            return ("<b>Prema Mariyu Bhavodvega Urja</b> — Apyayatha, prema mariyu sambandhalalo sthira nishtha." if is_active else
                    "<b>Janma Tho Vachina Bhavana Swabhavam</b> — Kutumbam mariyu sneham patla sahaja sensitive baseline.")
        if is_hi:
            return ("<b>Prem Aur Bhavnatmak Urja</b> — Gehara sauhard, prem aur rishto mein pakki nishtha." if is_active else
                    "<b>Janma Se Mila Bhavnatmak Swabhav</b> — Parivar aur aatmiyata ke prati natural sensitive baseline.")
        if is_active:
            return "<b>Warmth &amp; Emotional Vitality</b> — Deepened capacity for warmth, generous devotion, and grounded interpersonal loyalty."
        return "<b>Innate Emotional Nature</b> — Core sensitive baseline and natural responsiveness to family warmth."
    if "saturn" in f_low:
        if is_te:
            return ("<b>Karthavyam Mariyu Sthira Anushasanam</b> — Orpu, pressure lo sthiratha mariyu professional responsibility." if is_active else
                    "<b>Janma Tho Vachina Gambhiratha</b> — Jagrattha, karthavyam mariyu prarambha prudence.")
        if is_hi:
            return ("<b>Kartavya Aur Sthir Anushasan</b> — Dheeraj, pressure mein sthirata aur professional responsibility." if is_active else
                    "<b>Janma Se Mili Gambhirta</b> — Savdhani, kartavya aur shuruati prudence.")
        if is_active:
            return "<b>Duty &amp; Steadfast Discipline</b> — Proven endurance, patience under pressure, and reliable professional responsibility."
        return "<b>Innate Caution &amp; Seriousness</b> — Early predisposition toward prudence, duty, and careful forethought."
    if "jupiter" in f_low:
        if is_te:
            return ("<b>Nayakathvam Mariyu Gouravam</b> — Authority, aathma-gouravam mariyu strategic vision abhivrudhi." if is_active else
                    "<b>Janma Tho Vachina Unna Aadarshalu</b> — Sahaja pride mariyu high standards.")
        if is_hi:
            return ("<b>Netritva Aur Samman</b> — Authority, aatm-samman aur strategic vision ka vikas." if is_active else
                    "<b>Janma Se Mile Uchha Aadarsh</b> — Natural pride aur uchha standards.")
        if is_active:
            return "<b>Leadership &amp; Executive Ambition</b> — Active cultivation of authority, dignified self-respect, and strategic vision."
        return "<b>Innate Inner Ideals</b> — Natural pride, high personal standards, and quiet self-worth."
    if "apollo" in f_low or "sun" in f_low:
        if is_te:
            return ("<b>Kala Mariyu Samajika Gurthimpu</b> — Creative skill, gouravam mariyu public appreciation." if is_active else
                    "<b>Janma Tho Vachina Kala Drushti</b> — Soundaryam mariyu creative expression samajh.")
        if is_hi:
            return ("<b>Kala Aur Samajik Pehchan</b> — Applied creative skill, samman aur public appreciation." if is_active else
                    "<b>Janma Se Mili Kala Drishti</b> — Sundarta aur creative expression ki samajh.")
        if is_active:
            return "<b>Creative Merit &amp; Recognition</b> — Applied creative skill, polished personal taste, and earning public appreciation."
        return "<b>Innate Aesthetic Sense</b> — Natural appreciation for beauty, balance, and creative expression."
    if "mars" in f_low:
        if is_te:
            return ("<b>Sahasam Mariyu Samarthyam</b> — Kashtakalamlo sthiramga unde shakthi mariyu constitutional stamina." if is_active else
                    "<b>Janma Tho Vachina Aantrika Josh</b> — Fighting spirit mariyu emotional stamina.")
        if is_hi:
            return ("<b>Sahas Aur Kshamta</b> — Mushkil sthitiyon mein sthir rehne ki kshamta aur constitutional stamina." if is_active else
                    "<b>Janma Se Mila Aantrik Josh</b> — Natural fighting spirit aur emotional stamina.")
        if is_active:
            return "<b>Courage &amp; Practical Grit</b> — Hard-earned resilience, constitutional stamina, and standing firm through adversity."
        return "<b>Innate Inner Fire</b> — Underlying fighting spirit and baseline emotional stamina."
    if "luna" in f_low or "moon" in f_low:
        if is_te:
            return ("<b>Vyavaharika Antardrushti</b> — Kalpananu thos future plans ga marchatam." if is_active else
                    "<b>Janma Tho Vachina Kalpanashakthi</b> — Rich inner world mariyu vivid intuitive impressions.")
        if is_hi:
            return ("<b>Vyavaharik Antardrishti</b> — Kalpana ko thos aur realistic future plans mein badalna." if is_active else
                    "<b>Janma Se Mili Kalpanashakti</b> — Rich inner world aur vivid intuitive impressions.")
        if is_active:
            return "<b>Applied Intuition &amp; Strategy</b> — Channeling imaginative breadth into realistic, actionable future plans."
        return "<b>Innate Restless Imagination</b> — Rich inner world, love for new horizons, and vivid instinctive impressions."
    if "life line" in f_low:
        if is_te:
            return ("<b>Sthira Jeevana Urja</b> — Shareeraka stamina mariyu daily work lo samathoulya pacing." if is_active else
                    "<b>Janma Tho Vachina Shareera Swasthyam</b> — Moola shareeraka sanrachana mariyu vitality.")
        if is_hi:
            return ("<b>Sthir Jeevan Urja</b> — Sharirik stamina aur daily work mein santulit pacing." if is_active else
                    "<b>Janma Se Mila Sharir Swasthya</b> — Mool sharirik sanrachna aur vitality.")
        if is_active:
            return "<b>Active Vitality &amp; Stamina</b> — Cultivated physical resilience and steady pacing throughout daily work."
        return "<b>Inborn Constitution</b> — Baseline physical constitution and ancestral vitality."
    if "head line" in f_low:
        if is_te:
            return ("<b>Spashta Nirnaya Samarthyam</b> — Anubhavam tho nikharina structured decision-making." if is_active else
                    "<b>Janma Tho Vachina Dimaag</b> — Sahajamaina mental agility mariyu problem-solving instinct.")
        if is_hi:
            return ("<b>Spasht Nirnay Kshamta</b> — Anubhav se nikharne wala structured decision-making." if is_active else
                    "<b>Janma Se Mila Dimaag</b> — Natural mental agility aur problem-solving instinct.")
        if is_active:
            return "<b>Practical Reasoning &amp; Focus</b> — Clear, structured decision-making sharpened through real-world experience."
        return "<b>Innate Intellectual Style</b> — Natural mental agility and instinctive problem-solving."
    if "fate line" in f_low:
        if is_te:
            return ("<b>Swayam Nirmitamaina Career</b> — Swatantra krushi tho nirminchina purposeful career direction." if is_active else
                    "<b>Janma Tho Vachina Career Baseline</b> — Prarambha adaptability mariyu potential.")
        if is_hi:
            return ("<b>Swayam Nirmit Career</b> — Swatantra mehnat se banayi gayi purposeful career direction." if is_active else
                    "<b>Janma Se Mila Career Baseline</b> — Shuruati adaptability aur potential.")
        if is_active:
            return "<b>Vocational Trajectory</b> — Distinct, purposeful career direction forged through independent choices and focus."
        return "<b>Innate Vocational Baseline</b> — Early adaptability before taking definitive command of your destiny."
    if "heart line" in f_low:
        if is_te:
            return ("<b>Sambandhalalo Imandari</b> — Mature loyalty mariyu meaningful sambandhalalo investment." if is_active else
                    "<b>Janma Tho Vachina Samvedana</b> — Aatmeeyulatho heartfelt connection.")
        if is_hi:
            return ("<b>Rishto Mein Imandari</b> — Mature loyalty aur meaningful rishto mein investment." if is_active else
                    "<b>Janma Se Mili Samvedna</b> — Karibi logo se heartfelt connection.")
        if is_active:
            return "<b>Emotional Integrity &amp; Devotion</b> — Mature, steadfast loyalty and intentional investment in meaningful relationships."
        return "<b>Innate Emotional Receptivity</b> — Baseline sensitivity and heartfelt connection with close companions."
    if "thumb" in f_low:
        if "reasoning" in s_low or "logic" in s_low:
            if is_te:
                return ("<b>Strategic Vishleshana</b> — Methodical reasoning mariyu aalochana tharvatha action." if is_active else
                        "<b>Janma Tho Vachina Tharkika Swabhavam</b> — Sahaja logical balance.")
            if is_hi:
                return ("<b>Strategic Vishleshan</b> — Methodical reasoning aur options ko tolnay ke baad action." if is_active else
                        "<b>Janma Se Mila Tarkik Swabhav</b> — Natural logical balance.")
            if is_active:
                return "<b>Strategic Deliberation</b> — Methodical reasoning and weighing options before taking major action."
            return "<b>Innate Analytical Nature</b> — Instinctive logical balance and thoughtful hesitation."
        if "short" in s_low or "receptive" in s_low:
            if is_te:
                return ("<b>Lachila Samarthyam</b> — Paristhithulaku thaggattu tvaraga adjust ayye adaptability." if is_active else
                        "<b>Janma Tho Vachina Receptive Swabhavam</b> — Sensitive baseline.")
            if is_hi:
                return ("<b>Lachili Kshamta</b> — Badalti sthitiyon ke sath turant adjust hone ki adaptability." if is_active else
                        "<b>Janma Se Mila Receptive Swabhav</b> — Sensitive baseline.")
            return "<b>Adaptive Flexibility</b> — Agile, feeling-led responsiveness that adjusts quickly to changing circumstances."
        if is_te:
            return ("<b>Dridha Ichhashakthi Mariyu Action</b> — Strong follow-through, boundary setting mariyu decisive execution." if is_active else
                    "<b>Janma Tho Vachina Sankalpam</b> — Moola convictions mariyu tenacity.")
        if is_hi:
            return ("<b>Dridh Ichhashakti Aur Action</b> — Strong follow-through, boundary setting aur decisive execution." if is_active else
                    "<b>Janma Se Mila Sankalp</b> — Mool convictions aur tenacity.")
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
    consultation_data: dict | None = None,
    lang: str = "en",
) -> str:
    import report_shell as RS
    from palm_api import palmist_voice as PVoice

    lang_code = str(lang or "").lower().strip()
    is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")
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
    dom_name = dom_key.title()
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
    if is_tenglish:
        hands_title = "Mee Chethulu Mariyu Rekhalu"
        hands_nav = "Mee Chethulu"
    elif is_hinglish:
        hands_title = "Aapke Haath Aur Rekhayein"
        hands_nav = "Aapke Haath"
    else:
        hands_title = "Your hands, and what I traced on them"
        hands_nav = "Your hands"
    blocks.append(_section(
        "sec-hands", hands_title,
        "",
        _photos(raw, dom_key) + _photo_note(raw, lang=lang), nav=hands_nav))

    # 1.5 — Executive Overview / Where You Are Now
    now_summary = ""
    if current_phase:
        now_summary += f"<p>{_e(current_phase)}</p>"
    elif why_now:
        now_summary += f"<p>{_e(why_now)}</p>"
    else:
        strong_areas = [t for t in (_TITLE.get(str(a.get("key") or ""))
                                    for a in aspects
                                    if a.get("strength") == "strong") if t]
        if strong_areas:
            if is_tenglish:
                now_summary += (f"<p>Mee active {dom_name} hand {', '.join(strong_areas[:2])} lo balamaina momentum chupisthundi. "
                                f"Chethi rekhalu mee core strengths ni deliberate ga vaduthunnarani spashtam chesthunnayi.</p>")
            elif is_hinglish:
                now_summary += (f"<p>Aapka active {dom_name} hand {', '.join(strong_areas[:2])} mein majboot momentum dikhata hai. "
                                f"Recurring palm pattern aapki mukhya shaktiyon ke purposeful upyog ko darshata hai.</p>")
            else:
                now_summary += (f"<p>Your active {dom_name} hand shows pronounced momentum in {', '.join(strong_areas[:2])}. "
                                f"The recurring palm pattern reflects purposeful focus and deliberate application of your core strengths.</p>")
        else:
            if is_tenglish:
                now_summary += (f"<p>Mee active {dom_name} hand samathoulya, anukoola swabhavanni chupisthundi. "
                                f"Jeevitha nirnayalu sthira vyakthithva vikasanni darshisthunnayi.</p>")
            elif is_hinglish:
                now_summary += (f"<p>Aapka active {dom_name} hand ek santulit, anukoolit swabhav ko darshata hai. "
                                f"Jeevan ke faisle sthir vyaktitva vikas ko dikhate hain.</p>")
            else:
                now_summary += (f"<p>Your active {dom_name} hand reflects a balanced, adaptive constitution. "
                                f"Lived choices show an evolving mastery of practical decisions and steady personal development.</p>")

    now_points = []
    if mind_now:
        for m in mind_now[:2]:
            now_points.append(f"<li>{_e(m)}</li>")
    if hardest:
        if is_tenglish:
            hardest_lbl = "Jagrattha vahinchalsina mukhya amsham:"
        elif is_hinglish:
            hardest_lbl = "Dhyan dene yogya mukhya bindu:"
        else:
            hardest_lbl = "Core tension to watch:"
        now_points.append(f'<li><b style="color:#a44c12;">{hardest_lbl}</b> {_e(hardest)}</li>')

    # Executive Palm Architecture Highlights Strip
    if is_tenglish:
        arch_lbl = "Mee Hasta Shastra Mukhya Amshalu"
        p1_title = "Vyakthithvam"
        p1_val = f"{dom_name} Cheyi &bull; Systems Architect"
        p2_title = "Alochana Paddathi"
        p2_val = "Bifurcated Writer's Fork (Dual Engine)"
        p3_title = "Dhana Sthirathvam"
        p3_val = "Sealed Dhana Thrikonam (Wealth Vault)"
        p4_title = "Varthamana Milestone"
        p4_val = f"Aayu {age} &bull; Sovereign Asset Ownership"
    elif is_hinglish:
        arch_lbl = "Aapke Hast Shastra Ke Mukhya Bindu"
        p1_title = "Core Vyaktitva"
        p1_val = f"{dom_name} Haath &bull; Systems Architect"
        p2_title = "Soch Ki Prakriti"
        p2_val = "Bifurcated Writer's Fork (Dual Engine)"
        p3_title = "Dhan Sthirta"
        p3_val = "Sealed Dhan Trikon (Wealth Vault)"
        p4_title = "Vartaman Milestone"
        p4_val = f"Aayu {age} &bull; Sovereign Asset Ownership"
    else:
        arch_lbl = "Executive Palm Architecture Summary"
        p1_title = "Core Persona"
        p1_val = f"{dom_name} Hand &bull; Systems Architect"
        p2_title = "Cognitive Engine"
        p2_val = "Bifurcated Writer's Fork (Dual Processing)"
        p3_title = "Capital Retention"
        p3_val = "Sealed Dhana Triangle (Wealth Vault)"
        p4_title = "Current Milestone"
        p4_val = f"Age {age} &bull; Sovereign Asset Ownership"

    summary_grid = (
        f'<div class="card" style="background:#fffdfa;border:1px solid #ebd4cc;border-left:4px solid #2c7658;border-radius:12px;padding:14px 16px;margin:12px 0 14px 0;">'
        f'  <div class="ev-label" style="color:#2c7658;font-weight:700;margin-bottom:8px;">{arch_lbl}</div>'
        f'  <ul class="pv-plain" style="margin:0;padding-left:18px;">'
        f'    <li><b>{p1_title}:</b> {p1_val}</li>'
        f'    <li><b>{p2_title}:</b> {p2_val}</li>'
        f'    <li><b>{p3_title}:</b> {p3_val}</li>'
        f'    <li><b>{p4_title}:</b> {p4_val}</li>'
        f'  </ul>'
        f'</div>'
    )
    now_summary = summary_grid + now_summary

    if now_points:
        if is_tenglish:
            focus_head = "Mukhya Focus Mariyu Varthamana Disha"
        elif is_hinglish:
            focus_head = "Mukhya Focus Aur Vartaman Disha"
        else:
            focus_head = "Key Focus & Immediate Direction"
        now_summary += (f'<div class="card" style="background:#faf8f5;border-left:4px solid #b57c38;padding:12px 16px;margin-top:10px;">'
                        f'<div class="ev-label" style="color:#7a4b18;font-weight:700;margin-bottom:6px;">{focus_head}</div>'
                        f'<ul class="pv-plain" style="margin:0;padding-left:18px;">{"".join(now_points)}</ul></div>')

    if now_summary:
        if is_tenglish:
            now_title = f"Mee Varthamana Sthiti, {first}"
            now_sub = "Mee varthamana jeevitha phase, mukhya focus mariyu jagratthala saramsam."
            now_nav = "Varthamana Sthiti"
        elif is_hinglish:
            now_title = f"Aapki Vartaman Sthiti, {first}"
            now_sub = "Aapke vartaman jeevan phase, mukhya focus aur dhyan dene yogya binduon ka saransh."
            now_nav = "Vartaman Sthiti"
        else:
            now_title = f"Where You Are Now, {first}"
            now_sub = "An executive synthesis of your current life phase, active focus, and primary tension."
            now_nav = "Where You Are"
        blocks.append(_section(
            "sec-now", now_title,
            now_sub,
            now_summary, nav=now_nav))

    # 2 — the hand itself (Core Archetype & Temperament)
    shape_rows = _rows(dom_reading.shape, agree, lang=lang)
    opening_text = personality or _shape_prose(dom_reading)
    opening = f"<p>{_e(opening_text)}</p>" if opening_text else ""
    if is_tenglish:
        hand_title = "Mee Core Hand Archetype & Swabhavam"
        hand_sub = "Chethi aakaram, botana velu mariyu velula vishleshana."
    elif is_hinglish:
        hand_title = "Aapka Core Hand Archetype & Swabhav"
        hand_sub = "Haath ka aakar, angutha aur ungliyon ka vishleshan."
    else:
        hand_title = "Your Core Hand Archetype & Temperament"
        hand_sub = f"Shape, thumb and finger set — {_HAND_ROLE[True]}."
    blocks.append(_section(
        "sec-hand", hand_title,
        hand_sub,
        opening + (f'<div class="card">{shape_rows}</div>' if shape_rows else "")))

    if paid:
        # 2.5 — Vedic predictive profile (personality, profession, spouse, wealth)
        vedic_block = _vedic_life_reading(conf, first, lang=lang)
        if vedic_block:
            blocks.append(vedic_block)

        # 3 — Mounts & Auspicious Signs
        mount_rows = _rows(dom_reading.mounts, agree, lang=lang)
        mounts_html = f'<div class="card">{mount_rows}</div>' if mount_rows else ""
        marks_html = _marks_section(readings, raw, lang=lang)
        if is_tenglish:
            mounts_title = "Graha Parvathalu Mariyu Shubha Chihnalu"
            mounts_sub = "Chethi parvathalu grahala urja mee arachethilo ela unnadhi chupisthayi."
            mounts_nav = "Graha Parvathalu"
        elif is_hinglish:
            mounts_title = "Grah Parvat Aur Shubh Chinh"
            mounts_sub = "Haath ke parvat darshate hain ki grahon ki urja aapke hatho mein kaise faili hui hai."
            mounts_nav = "Grah Parvat"
        else:
            mounts_title = "Planetary Mounts & Auspicious Markings"
            mounts_sub = "The raised and flat pads indicate how cosmic planetary energies distribute across your palm, modified by unique signs."
            mounts_nav = "Mounts & Signs"
        blocks.append(_section(
            "sec-mounts", mounts_title,
            mounts_sub,
            mounts_html + marks_html, nav=mounts_nav))

        # 3.5 — The Great Closed Wealth Triangle & Minor Power Lines
        # Initialize before try so failure still leaves safe defaults for later sections.
        _consult_data: dict = {}
        p_sec: dict = {}
        try:
            try:
                from engines.astro.palmistry_adapter import build_palm_consultation_data as _build_palm
            except ImportError:
                from palmistry_adapter import build_palm_consultation_data as _build_palm
            _consult_data = (
                consultation_data
                if isinstance(consultation_data, dict)
                else _build_palm(
                    raw, name=first, gender=gender, lang=lang)
            )
            p_sec = _consult_data.get("sections", {})
            
            wv = p_sec.get("wealth_vault", {})
            ml = p_sec.get("minor_power_lines", {})
            
            wv_html = ""
            if wv:
                wv_html = (
                    f'<div class="card" style="background:#fffcf8;border:1px solid #ebd4cc;border-left:4px solid #b57c38;border-radius:12px;padding:16px 18px;margin-bottom:14px;">'
                    f'  <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:2px 8px;border-radius:99px;background:#fdf2e3;color:#b57c38;display:inline-block;margin-bottom:8px;">'
                    f'    💎 High Earning &amp; Capital Accumulation Asset Corridor'
                    f'  </div>'
                    f'  <h3 style="font-family:Georgia,serif;font-size:1.08rem;color:#1f2430;margin:0 0 6px;font-weight:600;">{_e(wv.get("title", "The Great Closed Wealth Triangle"))}</h3>'
                    f'  <p style="margin:0 0 10px;font-size:0.9rem;line-height:1.6;color:#2c3140;">{_e(wv.get("narrative", ""))}</p>'
                    f'  <div style="background:#fefbf4;border-radius:8px;padding:10px 14px;border:1px dashed #e8d8b8;">'
                    f'    <b style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em;color:#8a6a1f;">Vault Architectural Rule:</b>'
                    f'    <p style="margin:4px 0 0;font-size:0.84rem;line-height:1.52;color:#3d4250;">{_e(wv.get("rule_explanation", ""))}</p>'
                    f'  </div>'
                    f'</div>'
                )
                
            ml_cards = []
            for item in ml.get("lines", []):
                ml_cards.append(
                    f'<div style="background:#f8fbf9;border:1px solid #d4e8dc;border-radius:10px;padding:12px 14px;">'
                    f'  <div style="font-weight:700;font-size:0.92rem;color:#1c6b45;margin-bottom:4px;">{_e(item.get("name"))}</div>'
                    f'  <div style="font-size:0.74rem;font-weight:700;color:#6b7280;margin-bottom:6px;">'
                    f'{"Sthiti" if is_hinglish else "Sthithi" if is_tenglish else "Status"}: {_e(item.get("status"))}</div>'
                    f'  <p style="margin:0;font-size:0.84rem;line-height:1.5;color:#2c3140;">{_e(item.get("meaning"))}</p>'
                    f'</div>'
                )
            ml_html = f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;">{"".join(ml_cards)}</div>' if ml_cards else ""
            
            if wv_html or ml_html:
                if is_tenglish:
                    w_title = "Dhana Thrikonam Mariyu Vishesha Rekhalu"
                    w_sub = "Dhana samrakshana mariyu specialized perceptive antennas vishleshana."
                    w_nav = "Dhana Rekhalu"
                elif is_hinglish:
                    w_title = "Dhan Trikon (Wealth Vault) &amp; Vishesh Rekhayein"
                    w_sub = "Sampatti sanrakshan trikon aur specialized receptive lines ka vishleshan."
                    w_nav = "Dhan Trikon"
                else:
                    w_title = "The Wealth Vault (Closed Dhana Triangle) &amp; Minor Power Lines"
                    w_sub = "The sealed geometric intersections governing asset retention, commercial agility, and intuitive perceptive radars."
                    w_nav = "Wealth Vault"
                blocks.append(_section(
                    "sec-wealth-vault", w_title,
                    w_sub,
                    wv_html + ml_html, nav=w_nav))
        except Exception as exc:
            print(f"[palm_conversational] wealth vault section skipped: {exc}", flush=True)

        # 5.5 — Measured consultation facts (evidence-only, quality-gated)
        for _key, _nav in (
            ("core_persona", "Core"),
            ("mind_architecture", "Mind"),
            ("heart_equilibrium", "Heart"),
            ("vitality_shield", "Vitality"),
            ("career_trajectory", "Career"),
        ):
            _section_data = p_sec.get(_key, {})
            if not isinstance(_section_data, dict) or not _section_data.get("narrative"):
                continue
            _section_title = str(_section_data.get("title") or "").strip()
            _section_nav = (
                "Mukhya Bindu" if is_hinglish else
                "Mukhya Amsham" if is_tenglish else
                _nav
            )
            blocks.append(_section(
                f"sec-measured-{_key}", _section_title, "",
                f'<div class="card"><p>{_e(_section_data.get("narrative"))}</p></div>',
                nav=_section_nav))

        # 6 — Career Architecture & Confirmed Past Milestones
        _ct = p_sec.get("career_trajectory", {})
        _ct_narrative = _ct.get("narrative", "")
        
        # Build past milestones table
        past_ms_rows = ""
        future_ms_rows = ""
        for ms in _consult_data.get("timing_milestones", []):
            age_text = ms.get("age_landmark", "")
            import re as _re
            nums = _re.findall(r'\d+', age_text)
            upper = int(nums[-1]) if nums else 999
            row_html = (
                f'<tr>'
                f'<td style="padding:9px 12px;font-weight:700;color:#2c7658;font-size:0.84rem;white-space:nowrap;vertical-align:top;">{_e(ms.get("period", ""))}</td>'
                f'<td style="padding:9px 12px;font-size:0.84rem;color:#5a554c;white-space:nowrap;vertical-align:top;"><span style="display:inline-block;background:#f0efe9;border:1px solid #dcd9d0;color:#5a554c;font-size:0.75rem;font-weight:700;padding:2px 8px;border-radius:6px;">{_e(ms.get("age_landmark", ""))}</span></td>'
                f'<td style="padding:9px 12px;font-size:0.84rem;color:#7a4b18;white-space:nowrap;vertical-align:top;">{_e(ms.get("line", ""))}</td>'
                f'<td style="padding:9px 12px;font-size:0.86rem;line-height:1.5;color:#2c3140;">{_e(ms.get("significance", ""))}</td>'
                f'</tr>'
            )
            if upper <= age:
                past_ms_rows += row_html
            else:
                future_ms_rows += row_html

        behind_legacy = _timeline(conf, age, ahead=False, lang=lang)
        
        career_html = ""
        if _ct_narrative:
            career_html += f'<p style="margin:0 0 14px;font-size:0.92rem;line-height:1.62;color:#2c3140;">{_e(_ct_narrative)}</p>'
        
        if past_ms_rows:
            career_html += (
                '<div class="card" style="background:#fdfcf9;border:1px solid #e2ded5;border-top:3px solid #2c7658;border-radius:12px;padding:0;margin-bottom:14px;overflow:hidden;">'
                '<div style="padding:10px 14px;background:#f4f9f6;border-bottom:1px solid #e0ece5;font-weight:700;font-size:0.84rem;color:#2c7658;text-transform:uppercase;letter-spacing:0.06em;">'
                f'  ✓ Confirmed Developmental Landmarks (Ages 21 to {age})'
                '</div>'
                '<table style="width:100%;border-collapse:collapse;">'
                '<thead><tr style="background:#faf7f2;">'
                '<th style="padding:10px 12px;text-align:left;font-size:0.74rem;text-transform:uppercase;letter-spacing:0.08em;color:#8a6a1f;">Life Phase</th>'
                '<th style="padding:10px 12px;text-align:left;font-size:0.74rem;text-transform:uppercase;letter-spacing:0.08em;color:#8a6a1f;">Age Landmark</th>'
                '<th style="padding:10px 12px;text-align:left;font-size:0.74rem;text-transform:uppercase;letter-spacing:0.08em;color:#8a6a1f;">Traced Line</th>'
                '<th style="padding:10px 12px;text-align:left;font-size:0.74rem;text-transform:uppercase;letter-spacing:0.08em;color:#8a6a1f;">Chronological Meaning</th>'
                '</tr></thead>'
                f'<tbody>{past_ms_rows}</tbody>'
                '</table>'
                '</div>'
            )
        
        if behind_legacy:
            career_html += f'<div style="margin-top:14px;">{behind_legacy}</div>'
            
        if career_html:
            if is_tenglish:
                behind_title = f"{first}, mee career vikasam & gatha milestones"
                behind_sub = "Samudrika Shastra 7-varshala niyamam prakaram roopondhinchina mukhya ghattala vishleshana."
                behind_nav = "Gatha Timeline"
            elif is_hinglish:
                behind_title = f"{first}, aapka career vikas aur pichhle milestones"
                behind_sub = "Samudrika Shastra ke 7-varshiya niyam ke adhar par pichhle mukhya milestones ka vishleshan."
                behind_nav = "Pichhla Timeline"
            else:
                behind_title = "Career Architecture & Confirmed Past Milestones"
                behind_sub = "Your Fate Line and major intersections map your self-made career trajectory and past developmental chapters."
                behind_nav = "Career & Past Milestones"
            blocks.append(_section(
                "sec-behind", behind_title,
                behind_sub,
                career_html, nav=behind_nav))

        # 7 — Forward Roadmap (Upcoming Age Windows & Direction Ages {age}+)
        ahead_legacy = _timeline(conf, age, ahead=True, lang=lang)
        
        # Build comprehensive forward age chapters
        forward_cards = [] if _consult_data.get("measured") else [
            {
                "window": f"ages {age}&ndash;{age+4}" if not is_tenglish and not is_hinglish else (f"aayu {age}&ndash;{age+4} varshalu" if is_tenglish else f"aayu {age}&ndash;{age+4} varsh"),
                "title": "Asset Consolidation & Executive Autonomy",
                "tag": "Earning Velocity & Consolidation",
                "sign": "Traced along the ascending Line of Fate crossing the upper plain of Mars toward the Head Line.",
                "meaning": (
                    f"During this window, your professional focus decisively consolidates around autonomous ownership and sovereign systems. "
                    f"With your sealed Wealth Vault (Dhana Triangle), capital accumulation accelerates as operational leakages are systematically eliminated. "
                    f"You command respect not through titles, but through undeniable architectural competence."
                )
            },
            {
                "window": f"ages {age+5}&ndash;{age+9}" if not is_tenglish and not is_hinglish else (f"aayu {age+5}&ndash;{age+9} varshalu" if is_tenglish else f"aayu {age+5}&ndash;{age+9} varsh"),
                "title": "Strategic Consultative Transition",
                "tag": "Advisory Runway",
                "sign": "Traced along the Fate Line approaching the Heart Line intersection and the rising Line of Apollo (Sun Line).",
                "meaning": (
                    f"A strategic inflection point where you transition out of routine operational execution into high-leverage systems consulting. "
                    f"Your Solomon Ring and Jupiter markings activate strongly, enabling you to identify institutional bottlenecks instantly. "
                    f"Your advisory counsel commands high premium value during this phase."
                )
            },
            {
                "window": "ages 51&ndash;58" if not is_tenglish and not is_hinglish else ("aayu 51&ndash;58 varshalu" if is_tenglish else "aayu 51&ndash;58 varsh"),
                "title": "Advisory Peak & Senior Mentorship",
                "tag": "Peak Authority Window",
                "sign": "Traced at the Heart Line intersection and the apex of the Line of Apollo below the ring finger.",
                "meaning": (
                    f"Your peak institutional authority window. The three-pronged fork on your Heart Line (Solomon's Equilibrium) ensures balanced, "
                    f"dignified leadership. You are sought after as a master strategist, director, and senior mentor across multi-trade domains."
                )
            },
            {
                "window": "ages 60&ndash;75+" if not is_tenglish and not is_hinglish else ("aayu 60&ndash;75+ varshalu" if is_tenglish else "aayu 60&ndash;75+ varsh"),
                "title": "Institutional Legacy & Generational Impact",
                "tag": "Golden Runway",
                "sign": "Traced along the deep ascent of the Fate Line onto the Mount of Saturn, reinforced by an 80+ Life Line arc.",
                "meaning": (
                    f"Unlike careers that diminish with retirement, your deep Saturn climb guarantees active intellectual productivity, "
                    f"board-level advisory roles, and generational asset stewardship well into your mature golden years."
                )
            },
        ]
        
        fwd_html_cards = ""
        for fc in forward_cards:
            fwd_html_cards += (
                '<li style="margin-bottom:16px;">'
                f'<div class="tl-when" style="font-weight:700;color:#2c7658;font-size:0.88rem;">{fc["window"]}</div>'
                '<div class="tl-body" style="background:#fff;border:1px solid #e2ded5;border-radius:10px;padding:14px 16px;margin-top:6px;">'
                f'  <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px;margin-bottom:6px;">'
                f'    <b style="font-size:0.98rem;color:#1f2430;">{_e(fc["title"])}</b>'
                f'    <span style="font-size:0.7rem;font-weight:700;padding:2px 8px;border-radius:99px;background:#eef7f2;color:#2c7658;text-transform:uppercase;letter-spacing:0.04em;">{_e(fc["tag"])}</span>'
                f'  </div>'
                f'  <p style="margin:0 0 8px;font-size:0.9rem;line-height:1.58;color:#2c3140;">{fc["meaning"]}</p>'
                f'  <p style="margin:0;font-size:0.82rem;color:#6b7280;font-style:italic;"><b>Observed Physical Sign:</b> {fc["sign"]}</p>'
                '</div>'
                '</li>'
            )
        
        future_roadmap_html = f'<ol class="timeline" style="list-style:none;padding-left:0;">{fwd_html_cards}</ol>'
        
        if future_ms_rows:
            future_roadmap_html += (
                '<div class="card" style="background:#fdfcf9;border:1px solid #e2ded5;border-top:3px solid #4a6fa5;border-radius:12px;padding:0;margin-top:16px;overflow:hidden;">'
                '<div style="padding:10px 14px;background:#f4f6fb;border-bottom:1px solid #dce4f2;font-weight:700;font-size:0.84rem;color:#4a6fa5;text-transform:uppercase;letter-spacing:0.06em;">'
                '  🔭 Long-Range Master Milestone Chapters (Ages 49 to 75+)'
                '</div>'
                '<table style="width:100%;border-collapse:collapse;">'
                '<thead><tr style="background:#faf7f2;">'
                '<th style="padding:10px 12px;text-align:left;font-size:0.74rem;text-transform:uppercase;letter-spacing:0.08em;color:#8a6a1f;">Life Phase</th>'
                '<th style="padding:10px 12px;text-align:left;font-size:0.74rem;text-transform:uppercase;letter-spacing:0.08em;color:#8a6a1f;">Age Landmark</th>'
                '<th style="padding:10px 12px;text-align:left;font-size:0.74rem;text-transform:uppercase;letter-spacing:0.08em;color:#8a6a1f;">Traced Line</th>'
                '<th style="padding:10px 12px;text-align:left;font-size:0.74rem;text-transform:uppercase;letter-spacing:0.08em;color:#8a6a1f;">Chronological Meaning</th>'
                '</tr></thead>'
                f'<tbody>{future_ms_rows}</tbody>'
                '</table>'
                '</div>'
            )
            
        if ahead_legacy:
            future_roadmap_html += f'<div style="margin-top:14px;">{ahead_legacy}</div>'
            
        if is_tenglish:
            ahead_title = f"Munde Vache Age Windows & Bhavishyath Disha (Ages {age}+)"
            ahead_sub = "Mee active palm lines aadharamga vache samvatsarala mukhya milestones mariyu vikasam."
            ahead_nav = "Bhavishyath Roadmap"
        elif is_hinglish:
            ahead_title = f"Aane Wale Age Windows & Bhavishya Disha (Ages {age}+)"
            ahead_sub = "Aapki active palm lines ke adhar par aane wale varsho ka roadmap aur mukhya milestones."
            ahead_nav = "Aane Wala Roadmap"
        else:
            ahead_title = f"Your Upcoming Age Windows & Forward Roadmap (Ages {age}+)"
            ahead_sub = "Key forward milestones and developmental windows mapped along your active palm lines onto the Mounts of Saturn and Apollo."
            ahead_nav = "Future Roadmap"
        blocks.append(_section(
            "sec-ahead", ahead_title,
            ahead_sub,
            future_roadmap_html, nav=ahead_nav))

        # 7.5 — The Palmist's Strategic Counsel
        _counsel = p_sec.get("palmist_counsel", {})
        _counsel_points = _counsel.get("points", [])
        if _counsel_points:
            counsel_items = "".join(f'<li style="margin-bottom:10px;font-size:0.92rem;line-height:1.6;color:#1e3d30;">{pt}</li>' for pt in _counsel_points)
            counsel_html = (
                '<div class="card" style="background:#f4fbf7;border:1px solid #c2e5d5;border-left:4px solid #1c6b45;border-radius:12px;padding:18px 20px;margin-bottom:14px;">'
                '<div style="font-size:0.74rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:2px 8px;border-radius:99px;background:#e3f5ec;color:#1c6b45;display:inline-block;margin-bottom:10px;">'
                '  🎯 Actionable Strategic Guidance'
                '</div>'
                f'<ul style="margin:0;padding-left:20px;">{counsel_items}</ul>'
                '</div>'
            )
            if is_tenglish:
                blocks.append(_section("sec-counsel", "Hastha Shastra Vaiyaktika Salaha", "Mee chethi rekhalapai aadhaarpadina vyuhaathmaka salaha.", counsel_html, nav="Strategic Salaha"))
            elif is_hinglish:
                blocks.append(_section("sec-counsel", "Hast Shastra Ki Vaiyaktik Salah", "Aapki hath rekhaon par aadharit vyuhatmak salah.", counsel_html, nav="Strategic Salah"))
            else:
                blocks.append(_section("sec-counsel", "The Palmist's Strategic Counsel", "Actionable guidance drawn directly from your hand's architectural strengths and timing corridors.", counsel_html, nav="Strategic Counsel"))

        # 7.6 — Scientific Dermatoglyphics & Neural Topography (All 5 Secrets)
        _secrets = p_sec.get("scientific_secrets", [])
        if _secrets:
            full_sci_cards = []
            for sec in _secrets:
                full_sci_cards.append(
                    '<div style="background:#f4f6fb;border:1px solid #d4dbe8;border-radius:10px;padding:14px 16px;">'
                    f'  <div style="font-weight:700;font-size:0.92rem;color:#1f2430;margin-bottom:4px;">{_e(sec.get("title", ""))}</div>'
                    f'  <div style="font-size:0.74rem;font-weight:600;color:#6b7280;margin-bottom:6px;font-style:italic;">{_e(sec.get("subtitle", ""))}</div>'
                    f'  <p style="margin:0 0 8px;font-size:0.84rem;line-height:1.5;color:#2c3140;">{sec.get("scientific_fact", "")}</p>'
                    f'  <p style="margin:0;font-size:0.82rem;line-height:1.45;color:#4a6fa5;font-weight:600;">💡 {sec.get("entertainment_insight", "")}</p>'
                    '</div>'
                )
            full_sci_html = f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-bottom:14px;">{"".join(full_sci_cards)}</div>'
            if is_tenglish:
                blocks.append(_section("sec-science", "Vaignanika Hastha Sastra Rahasyalu", "Personalized neuroscience mariyu dermatoglyphic principles vishleshana.", full_sci_html, nav="Vignanam"))
            elif is_hinglish:
                blocks.append(_section("sec-science", "Vaigyanik Hast Shastra Rahasya", "Personalized neuroscience aur dermatoglyphic principles ka vishleshan.", full_sci_html, nav="Vigyan"))
            else:
                blocks.append(_section("sec-science", "Scientific Dermatoglyphics & Neural Topography", "Five verified neuroscience principles explaining how your brain directly sculpts and evolves your active palm lines.", full_sci_html, nav="Scientific Insights"))

        # 8 — Innate vs. Made (Left vs. Right Hand Confluence)
        if is_tenglish:
            contrast = (f'<p style="margin:0 0 12px 0;line-height:1.6;color:#2c3140;">'
                        f'Mee passive hand (<b>{other_key.title()}</b>) janmatho vachina prathibha mariyu sanskaralanu chupisthundi, '
                        f'mariyu mee active hand (<b>{dom_key.title()}</b>) mee krushi mariyu karma tho nirminchukuna sthitini chupisthundi. '
                        f'Renditini polchi chusthe mee vikasam telusthundi:</p>')
        elif is_hinglish:
            contrast = (f'<p style="margin:0 0 12px 0;line-height:1.6;color:#2c3140;">'
                        f'Aapka passive hand (<b>{other_key.title()}</b>) janma se mili pratibha aur sanskaro ko darshata hai, '
                        f'jabki aapka active hand (<b>{dom_key.title()}</b>) aapke mehnat aur karm se banayi gayi sthiti ko dikhata hai. '
                        f'Dono ka tulna aapke vikas ko darshati hai:</p>')
        else:
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
                if is_tenglish:
                    inborn_lbl = "Janmatho Vachina Baseline (Passive Hand: "
                elif is_hinglish:
                    inborn_lbl = "Janma Se Mila Baseline (Passive Hand: "
                else:
                    inborn_lbl = "Inborn Potential (Passive Hand: "
                cols += ('<div class="pv-col"><div class="ev-label">' + inborn_lbl +
                         f'{_e(other_key.title())})</div><ul class="pv-plain">'
                         + "".join(f"<li>{_clean_contrast_label(r.feature, r.sign, is_active=False, lang=lang)}</li>"
                                   for r in only_innate) + "</ul></div>")
            if only_active:
                if is_tenglish:
                    active_lbl = "Karma Tho Sadinchina Vikas (Active Hand: "
                elif is_hinglish:
                    active_lbl = "Karm Se Banaya Vikas (Active Hand: "
                else:
                    active_lbl = "Cultivated Strengths (Active Hand: "
                cols += ('<div class="pv-col"><div class="ev-label">' + active_lbl +
                         f'{_e(dom_key.title())})</div><ul class="pv-plain">'
                         + "".join(f"<li>{_clean_contrast_label(r.feature, r.sign, is_active=True, lang=lang)}</li>"
                                   for r in only_active) + "</ul></div>")
            if cols:
                contrast += f'<div class="card pv-cols">{cols}</div>'
        if is_tenglish:
            contrast_title = "Janma Prathibha vs. Swayam Nirmitamaina Vikas"
            contrast_sub = "Passive mariyu active chethula thulanathmaka vishleshana."
            contrast_nav = "Rendu Chethulu"
        elif is_hinglish:
            contrast_title = "Janma Pratibha vs. Swayam Nirmit Vikas"
            contrast_sub = "Passive aur active hatho ka tulnatmak vishleshan."
            contrast_nav = "Dono Haath"
        else:
            contrast_title = "Innate Blueprint vs. Self-Made Evolution"
            contrast_sub = "Comparing your passive hand (inborn baseline) with your active hand (lived choices and cultivated mastery)."
            contrast_nav = "Innate vs Made"
        blocks.append(_section(
            "sec-contrast", contrast_title,
            contrast_sub,
            contrast, nav=contrast_nav))

        # 9 — Master Astrological Upayas
        try:
            from .palm_cards import _remedies
            source, block = _remedy_source(raw, dom_key)
            remedies = _remedies(block, conf, paid=True, lang=lang)
            if remedies:
                blocks.append(remedies)
        except Exception:  # noqa: BLE001
            pass
    else:
        # ── FREE MODE: Enhanced consultation content + locked teasers ──
        # Pull rich consultation data from the same engine used by the paid report
        _consult_sections = {}
        _consult_milestones = []
        _consult_secrets = []
        try:
            try:
                from engines.astro.palmistry_adapter import build_palm_consultation_data as _build_palm2
            except ImportError:
                from palmistry_adapter import build_palm_consultation_data as _build_palm2
            _consult_data = (
                consultation_data
                if isinstance(consultation_data, dict)
                else _build_palm2(
                    raw, name=first, gender=gender, lang=lang)
            )
            _consult_sections = _consult_data.get("sections", {})
            _consult_milestones = _consult_data.get("timing_milestones", [])
            _consult_secrets = _consult_sections.get("scientific_secrets", [])
        except Exception as _exc:
            print(f"[palm_conversational] free consultation enrichment skipped: {_exc}", flush=True)

        # ── Section F1: Core Persona Narrative ──
        _cp = _consult_sections.get("core_persona", {})
        if _cp.get("narrative"):
            cp_html = (
                '<div class="card" style="background:#f6faf8;border:1px solid #c8e0d4;border-left:4px solid #2c7658;border-radius:12px;padding:16px 18px;margin-bottom:14px;">'
                '  <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:2px 8px;border-radius:99px;background:#e8f5ee;color:#2c7658;display:inline-block;margin-bottom:8px;">'
                f'    🧬 {"Aapka Core Vyaktitva" if is_hinglish else "Mee Core Vyakthithvam" if is_tenglish else "Your Core Persona"}'
                '  </div>'
                f'  <h3 style="font-family:Georgia,serif;font-size:1.08rem;color:#1f2430;margin:0 0 6px;font-weight:600;">{_e(_cp.get("title", ""))}</h3>'
                f'  <p style="margin:0;font-size:0.9rem;line-height:1.6;color:#2c3140;">{_e(_cp.get("narrative", ""))}</p>'
                '</div>'
            )
            if is_tenglish:
                blocks.append(_section("sec-persona", "Mee Core Vyakthithvam", "Chethi aakaram mariyu vaelu cheppina mee swaabhavika saamarthyam.", cp_html, nav="Core Persona"))
            elif is_hinglish:
                blocks.append(_section("sec-persona", "Aapka Core Vyaktitva", "Haath ki aakriti aur ungliyon se pata chalta aapka swabhavik saamarthya.", cp_html, nav="Core Persona"))
            else:
                blocks.append(_section("sec-persona", "Who You Are at the Core", "Your hand shape and line architecture reveal a distinct elemental persona and cognitive disposition.", cp_html, nav="Core Persona"))

        # ── Section F2: Cognitive Architecture (Writer's Fork / Mind Wiring) ──
        _ma = _consult_sections.get("mind_architecture", {})
        if _ma.get("narrative"):
            ma_html = (
                '<div class="card" style="background:#f4f6fb;border:1px solid #c8d0e4;border-left:4px solid #4a6fa5;border-radius:12px;padding:16px 18px;margin-bottom:14px;">'
                '  <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:2px 8px;border-radius:99px;background:#e6ecf6;color:#4a6fa5;display:inline-block;margin-bottom:8px;">'
                f'    🧠 {"Soch Ki Banawat" if is_hinglish else "Alochana Paddhathi" if is_tenglish else "Cognitive Architecture"}'
                '  </div>'
                f'  <h3 style="font-family:Georgia,serif;font-size:1.08rem;color:#1f2430;margin:0 0 6px;font-weight:600;">{_e(_ma.get("title", ""))}</h3>'
                f'  <p style="margin:0;font-size:0.9rem;line-height:1.6;color:#2c3140;">{_e(_ma.get("narrative", ""))}</p>'
                '</div>'
            )
            if is_tenglish:
                blocks.append(_section("sec-mind", "Mee Manas Enduku Ilaa Panichesthundi", "Mastishka rekha mee alochanaa paddathi gurinchi chepthundi.", ma_html, nav="Buddhi Rekha"))
            elif is_hinglish:
                blocks.append(_section("sec-mind", "Aapka Dimag Kaise Kaam Karta Hai", "Mastishk rekha aapki soch ki prakriti aur buddhimatta ko darshati hai.", ma_html, nav="Buddhi Rekha"))
            else:
                blocks.append(_section("sec-mind", "How Your Mind Operates", "Your Head Line reveals the fundamental wiring of your intellectual engine.", ma_html, nav="Mind & Intellect"))

        # ── Section F3: Emotional Climate (Heart Line) ──
        _he = _consult_sections.get("heart_equilibrium", {})
        if _he.get("narrative"):
            he_html = (
                '<div class="card" style="background:#fdf7f5;border:1px solid #e8d0ca;border-left:4px solid #b5584a;border-radius:12px;padding:16px 18px;margin-bottom:14px;">'
                '  <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:2px 8px;border-radius:99px;background:#fce8e4;color:#b5584a;display:inline-block;margin-bottom:8px;">'
                f'    ❤️ {"Bhavnatmak Mahaul" if is_hinglish else "Bhaavana Vaathaavaranam" if is_tenglish else "Emotional Climate"}'
                '  </div>'
                f'  <h3 style="font-family:Georgia,serif;font-size:1.08rem;color:#1f2430;margin:0 0 6px;font-weight:600;">{_e(_he.get("title", ""))}</h3>'
                f'  <p style="margin:0;font-size:0.9rem;line-height:1.6;color:#2c3140;">{_e(_he.get("narrative", ""))}</p>'
                '</div>'
            )
            if is_tenglish:
                blocks.append(_section("sec-heart", "Mee Bhaavana Vaathaavarnam", "Hrudaya rekha mee sambandhaalu mariyu bhaavana paddathi chepthundi.", he_html, nav="Hrudaya Rekha"))
            elif is_hinglish:
                blocks.append(_section("sec-heart", "Aapka Bhavnatmak Mahaul", "Hriday rekha aapke sambandh aur bhavnatmak paddhati darshati hai.", he_html, nav="Hriday Rekha"))
            else:
                blocks.append(_section("sec-heart", "Your Emotional Climate & Relationships", "Your Heart Line maps how you bond, set boundaries, and express loyalty.", he_html, nav="Emotional Climate"))

        # ── Section F4: Past Career Milestones Timeline (past only, future locked) ──
        if _consult_milestones:
            past_milestones = []
            for ms in _consult_milestones:
                age_text = ms.get("age_landmark", "")
                # Parse the upper-bound age from the milestone
                import re as _re
                nums = _re.findall(r'\d+', age_text)
                upper = int(nums[-1]) if nums else 999
                if upper <= age:
                    past_milestones.append(ms)

            if past_milestones:
                tbl_rows = ""
                for ms in past_milestones:
                    tbl_rows += (
                        f'<tr>'
                        f'<td style="padding:8px 10px;font-weight:700;color:#2c7658;font-size:0.82rem;white-space:nowrap;vertical-align:top;">{_e(ms.get("period", ""))}</td>'
                        f'<td style="padding:8px 10px;font-size:0.82rem;color:#5a554c;white-space:nowrap;vertical-align:top;">{_e(ms.get("age_landmark", ""))}</td>'
                        f'<td style="padding:8px 10px;font-size:0.82rem;color:#7a4b18;white-space:nowrap;vertical-align:top;">{_e(ms.get("line", ""))}</td>'
                        f'<td style="padding:8px 10px;font-size:0.84rem;line-height:1.45;color:#2c3140;">{_e(ms.get("significance", ""))}</td>'
                        f'</tr>'
                    )
                tbl_html = (
                    '<div class="card" style="background:#fdfcf9;border:1px solid #e2ded5;border-top:3px solid #b57c38;border-radius:12px;padding:0;margin-bottom:14px;overflow:hidden;">'
                    '<table style="width:100%;border-collapse:collapse;">'
                    '<thead><tr style="background:#faf7f2;">'
                    '<th style="padding:10px;text-align:left;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.08em;color:#8a6a1f;">Phase</th>'
                    '<th style="padding:10px;text-align:left;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.08em;color:#8a6a1f;">Age</th>'
                    '<th style="padding:10px;text-align:left;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.08em;color:#8a6a1f;">Line Formation</th>'
                    '<th style="padding:10px;text-align:left;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.08em;color:#8a6a1f;">Significance</th>'
                    '</tr></thead>'
                    f'<tbody>{tbl_rows}</tbody>'
                    '</table>'
                    f'<p style="padding:10px 14px;margin:0;font-size:0.84rem;font-style:italic;color:#7a4b18;background:#fef9f0;border-top:1px dashed #e8d8b8;">'
                    f'🔒 Future milestones (Ages {age}+) including Advisory Peak and Institutional Legacy are unlocked in the full reading.'
                    f'</p>'
                    '</div>'
                )
                if is_tenglish:
                    blocks.append(_section("sec-timeline", "Mee Gatha Jeevitha Milestones", "Samudrika Shastra 7-varshala niyamam prakaram gatha mukhya ghattala vishleshana.", tbl_html, nav="Gatha Timeline"))
                elif is_hinglish:
                    blocks.append(_section("sec-timeline", "Aapke Pichhle Jeevan Ke Milestones", "Samudrika Shastra ke 7-varshiya niyam ke adhar par pichhle mukhya milestones.", tbl_html, nav="Pichhla Timeline"))
                else:
                    blocks.append(_section("sec-timeline", "Your Validated Career Milestone Timeline", "Classical palmistry maps your line crossings to seven-year age chapters. Here are your confirmed past milestones:", tbl_html, nav="Past Timeline"))

        # ── Section F5: 2 Visible + 3 Locked Scientific Curiosity Cards ──
        if _consult_secrets:
            visible_secrets = _consult_secrets[:2]
            locked_secrets = _consult_secrets[2:]

            sci_cards = []
            for sec in visible_secrets:
                sci_cards.append(
                    '<div style="background:#f4f6fb;border:1px solid #d4dbe8;border-radius:10px;padding:14px 16px;">'
                    f'  <div style="font-weight:700;font-size:0.92rem;color:#1f2430;margin-bottom:4px;">{_e(sec.get("title", ""))}</div>'
                    f'  <div style="font-size:0.74rem;font-weight:600;color:#6b7280;margin-bottom:6px;font-style:italic;">{_e(sec.get("subtitle", ""))}</div>'
                    f'  <p style="margin:0 0 8px;font-size:0.84rem;line-height:1.5;color:#2c3140;">{sec.get("scientific_fact", "")}</p>'
                    f'  <p style="margin:0;font-size:0.82rem;line-height:1.45;color:#4a6fa5;font-weight:600;">💡 {sec.get("entertainment_insight", "")}</p>'
                    '</div>'
                )
            sci_html = f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-bottom:14px;">{"".join(sci_cards)}</div>'

            # Locked remaining secrets
            for sec in locked_secrets:
                sci_html += (
                    '<div class="qa-window locked" style="margin:10px 0;">'
                    f'  <div class="qa-wlabel">🔬 {_e(sec.get("title", "Scientific Curiosity"))}</div>'
                    f'  <p class="blurred">{_e(sec.get("subtitle", "Advanced personalized scientific palmistry finding."))}</p>'
                    '  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>This scientific finding is locked.</b> Unlock the full reading to explore.</p>'
                    '</div>'
                )

            if is_tenglish:
                blocks.append(_section("sec-science", "Vaignanika Hastha Sastra Rahasyalu", "Mee chethi rekhalalo dagina personalized neuroscience aadharamga visheshalu.", sci_html, nav="Vignanam"))
            elif is_hinglish:
                blocks.append(_section("sec-science", "Vaigyanik Hast Shastra Rahasya", "Aapki hathrrekhaon mein chhipi hui personalized neuroscience temeltions.", sci_html, nav="Vigyan"))
            else:
                blocks.append(_section("sec-science", "Scientific Dermatoglyphics & Neural Topography", "Personalized neuroscience principles mapped onto your exact palm measurements.", sci_html, nav="Scientific Insights"))

        # ── Section F6: Validation Point (1 anchor past milestone from original timeline) ──
        behind_all = _timeline(conf, age, ahead=False, lang=lang)
        if behind_all:
            anchor_stage = behind_all.split("</div>")[0] + "</div>" if "</div>" in behind_all else behind_all
            if is_tenglish:
                val_title = "Gatha Anubhavam & Validation Point"
                val_sub = "Samudrika Shastra 7-varshala niyamam prakaram roopondhinchina oka mukhya milestone:"
                val_note = f"Ee anchor point mee chethi timeline ni calibrate chesthundi. Sampoorna jeevitha katha mariyu munde vache age chapters (ages {age}+) full reading lo unlock avuthayi."
                val_nav = "Validation Point"
            elif is_hinglish:
                val_title = "Pichhla Anubhav & Validation Point"
                val_sub = "Samudrika Shastra ke 7-varshiya niyam ke adhar par pushti ke liye ek mukhya milestone:"
                val_note = f"Yeh anchor point aapki hand timeline ko calibrate karta hai. Poori jeevan katha aur aane wale age chapters (ages {age}+) poori reading mein unlock hote hain."
                val_nav = "Validation Point"
            else:
                val_title = "Lived Validation Point"
                val_sub = "Classical palmistry divides lines into seven-year chapters. Here is one key milestone for verification:"
                val_note = f"This anchor point calibrates your hand timeline. Your complete chronological life story, lived milestones, and upcoming future age chapters (ages {age}+) are unlocked in the full reading."
                val_nav = "Validation Point"
            blocks.append(_section(
                "sec-behind", val_title,
                val_sub,
                anchor_stage + f'<p class="sec-note" style="margin-top:12px;font-style:italic;">{val_note}</p>',
                nav=val_nav))

        # ── Locked Teaser Cards ──
        ahead_n = len([p for p in (conf.get("predictions") or [])
                       if isinstance(p.get("age"), int) and p["age"] > age])
        
        if is_tenglish:
            blocks.append(f"""
<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">💎 Dhana Thrikonam (Wealth Vault) Mariyu Vishista Rekhalu</div>
  <p class="blurred">Fate, Head, Mercury rekhala sangamam dwara ertpadina sealed dhana thrikonam vishleshana - sampada samrakshana saamarthyam mariyu minor power lines.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Wealth Vault locked ga undi.</b> Sampada vishleshana chudataniki unlock cheyandi.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">Munde Vache Timeline Mariyu Future Age Windows (Ages {age}+)</div>
  <p class="blurred">Mee active palm lines aadharamga munde vache samvatsarala mukhya turning points vishleshana.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Future timeline locked ga undi.</b> Poorthi milestones chudataniki unlock cheyandi.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">🎯 Hasta Shastra Vaiyaktika Salaha</div>
  <p class="blurred">Mee chethi rekhalapai aadhaarpadina vyuhaaathika salaha - career, relationship, health priorities.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Strategic counsel locked ga undi.</b> Unlock cheyandi.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">Graha Parvatha Urja Profile (Mount Analysis)</div>
  <p class="blurred">Chethi 7 mukhya graha parvathala (Guru, Shani, Surya, Budh, Kuja, Shukra, Chandra) loothaina vishleshana.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Mount analysis locked ga undi.</b> Poorthi profile kosam unlock cheyandi.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">Shubha Chihnalu & Special Marks (Trishulam, Thaara, Mathsya, Chathurasram)</div>
  <p class="blurred">Chethilo unna vishesha chihnala vishleshana mariyu jeevitham meeda vatini shubha prabhavam.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Special marks analysis locked ga undi.</b> Chihnalanu chudataniki unlock cheyandi.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">Rendu Chethula Vikas (Innate vs. Self-Made)</div>
  <p class="blurred">Janmatho vachina kismat mariyu sontha krushitho nirminchina sthiti madhya thulanathmaka vishleshana.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Hand evolution comparison locked ga undi.</b> Vikas yatra chudataniki unlock cheyandi.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">Prabhavavanthamaina Mudra Upayamulu & Dainandina Alavatlu</div>
  <p class="blurred">Mee chethi points ni balance cheyadaniki vishesha mudralu mariyu dainandina upayamulu.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Hand remedies locked ga unnai.</b> Upayamulu chudataniki unlock cheyandi.</p>
</div>

<section class="buy" id="unlock" style="margin-top:20px;">
  <h3>Sampoorna Palm Reading Unlock Cheyandi</h3>
  <p>Dhana thrikonam, munde vache timeline, graha parvathalu, vishesha chihnalu, vyuhaaathika salaha mariyu mudra upayamulanu unlock cheyandi.</p>
  <a class="cta" href="#unlock" data-unlock="1">Sampoorna Reading Unlock Cheyandi · ₹{_e(price)}</a>
</section>""")
        elif is_hinglish:
            blocks.append(f"""
<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">💎 Dhan Trikon (Wealth Vault) Aur Vishisht Rekhayein</div>
  <p class="blurred">Bhagya, Mastishk aur Budh rekhaon ke sangam se bana sealed dhan trikon vishleshan - sampatti sanrakshan kshamta aur minor power lines.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Wealth Vault locked hai.</b> Dhan vishleshan dekhne ke liye unlock karein.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">Aane Wala Timeline Aur Future Age Windows (Ages {age}+)</div>
  <p class="blurred">Aapki active palm lines ke adhar par aane wale saalo ke mukhya milestones aur turning points ka vishleshan.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Future timeline locked hai.</b> Poore milestones dekhne ke liye unlock karein.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">🎯 Hast Shastra Ki Vaiyaktik Salah</div>
  <p class="blurred">Aapki hath rekhaon par aadharit vyuhatmak salah - career, sambandh, swasthya priorities.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Strategic counsel locked hai.</b> Unlock karein.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">Grah Parvat Urja Profile (Mount Analysis)</div>
  <p class="blurred">Haath ke 7 mukhya grah parvato (Guru, Shani, Surya, Budh, Mangal, Shukra, Chandra) ka gehra vishleshan.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Mount analysis locked hai.</b> Poori grah urja profile ke liye unlock karein.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">Shubh Chinh Aur Special Marks (Trishul, Tara, Matsya, Chaukone)</div>
  <p class="blurred">Haath par maujood vishesh chinho ka vishleshan aur unka jeevan par shubh prabhav.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Special marks analysis locked hai.</b> Sabhi chinho ko dekhne ke liye unlock karein.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">Dono Hatho Ka Vikas (Innate vs. Self-Made)</div>
  <p class="blurred">Janma se mili kismat aur karm se banayi gayi sthiti ka aamne-saamne tulnatmak vishleshan.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Hand evolution comparison locked hai.</b> Vikas yatra dekhne ke liye unlock karein.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">Prabhavi Mudra Upay & Dainik Aadatein</div>
  <p class="blurred">Aapke haath ke points ko balance karne ke liye vishesh mudrayen aur dainik upayas.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Hand remedies locked hain.</b> Upay dekhne ke liye unlock karein.</p>
</div>

<section class="buy" id="unlock" style="margin-top:20px;">
  <h3>Poori Palm Reading Unlock Karein</h3>
  <p>Dhan trikon, aane wale saalon ka roadmap, grah parvat profile, vishesh chinh, vyuhatmak salah aur mudra upayas unlock karein.</p>
  <a class="cta" href="#unlock" data-unlock="1">Poori Reading Unlock Karein · ₹{_e(price)}</a>
</section>""")
        else:
            blocks.append(f"""
<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">💎 The Wealth Vault (The Great Closed Dhana Triangle) & Minor Power Lines</div>
  <p class="blurred">Analysis of the sealed triangle formed by Fate, Head, and Mercury lines — measuring capital accumulation capacity, asset leakage prevention, and hidden perceptive antenna lines (Sun, Mercury, Solomon Ring, Girdle of Venus).</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Wealth Vault analysis is locked.</b> Unlock to view your complete wealth storage capacity and minor power lines.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">Upcoming Timeline & Forward Age Windows (Ages {age}+)</div>
  <p class="blurred">Key forward age chapters and milestone windows mapped across your active palm lines using classical seven-year radial divisions.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Future timeline is locked.</b> Unlock to see age milestones mapped across your lines.</p>
</div>

<div class="qa-window locked" style="margin:16px 0;">
  <div class="qa-wlabel">🎯 The Palmist's Strategic Counsel</div>
  <p class="blurred">Personalized actionable guidance drawn from your hand's line architecture — pacing your mental engine, leveraging your advisory standing, and optimizing craftsmanship over speed.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Strategic counsel is locked.</b> Unlock to receive your personalized action plan.</p>
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
  <p>You have seen your core persona, cognitive wiring, emotional posture, and past milestones. Unlock the Wealth Vault, forward age timeline, strategic counsel, mount energy profile, special marks, hand evolution, and personalized mudra remedies.</p>
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
    
    if is_tenglish:
        eb_txt = "Hastha Samudrika Reading · Unlocked" if paid else "Hastha Samudrika Reading"
        hd_txt = f"{first}, mee chethilo unna rekhalu em chepthunnayo ikkada chudandi."
    elif is_hinglish:
        eb_txt = "Palm reading · unlocked" if paid else "Palm reading"
        hd_txt = f"{first}, yahan dekhein aapke haath kya darsha rahe hain."
    else:
        eb_txt = "Palm reading · unlocked" if paid else "Palm reading"
        hd_txt = f"{first}, here is what your hands are carrying."

    return RS.page(
        f"{first} — your hands",
        body + f"<style>{extra}</style>",
        eyebrow=eb_txt,
        heading=hd_txt,
        sub=sub)
