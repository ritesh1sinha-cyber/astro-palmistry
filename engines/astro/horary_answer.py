"""One answer to the question — Western horary only.

Vedic Prashna, KP, and Jamakkol are parked for now. The customer sees a
single Lilly/Louis-style Western horary judgment: one verdict, one confidence,
one explanation. Mixing traditions produced contradictory headlines ("No — low
confidence" at the top, a leaning-yes explanation below).

* **Western horary is the only active engine.** Significators, perfection,
  Moon condition, and the testimony tally drive the answer.
* **An unfavourable answer always carries a remedy.** Someone asking a horary
  question is usually anxious about something specific. Telling them "no" and
  stopping there is a bad product and worse psychology.

Writing principles, applied throughout — the reader is a person under some
pressure, not a query:

1. Answer in the first sentence. Never make them hunt for it.
2. Name the real question behind the question before explaining anything.
3. Never a bare "no". Every negative answer names what CAN move.
4. Uncertainty is stated as a fact about the chart, never as hedging.
5. The upsell is an honest offer of more, never a threat that they are
   missing something dangerous.
"""

from __future__ import annotations

import html as _html
import re
from copy import deepcopy
from datetime import date, datetime
from typing import Any

# --- policy ----------------------------------------------------------------

WEIGHTS = {"western": 1.0}

#: verdict text → direction in [-1, +1]
DIRECTION: dict[str, float] = {
    "yes": 1.0, "likely yes": 0.6, "likely": 0.6,
    "uncertain / qualified": 0.0, "uncertain": 0.0, "neutral": 0.0,
    "unlikely": -0.6, "no": -1.0,
}

#: stated confidence → how much of that direction we actually count
CONFIDENCE_FACTOR = {"good": 1.0, "high": 1.0, "moderate": 0.7, "medium": 0.7,
                     "low": 0.4, "speculative": 0.25}

CONF_RANK = {"low": 0, "moderate": 1, "good": 2}


def _dir(verdict: Any) -> float:
    return DIRECTION.get(str(verdict or "").strip().lower(), 0.0)


def _conf(confidence: Any) -> float:
    return CONFIDENCE_FACTOR.get(str(confidence or "").strip().lower(), 0.5)


# --- the planets, in English ------------------------------------------------

PLANET_ROLE = {
    "Sun": "your standing and the people in authority over the matter",
    "Moon": "how the situation is actually moving, day to day",
    "Mercury": "the talking, the paperwork, the negotiation",
    "Venus": "goodwill, money and whether people want to say yes to you",
    "Mars": "effort, conflict and how hard you will have to push",
    "Jupiter": "opportunity, sponsorship and the size of the opening",
    "Saturn": "delay, structure, and the price of doing it properly",
    "Uranus": "the disruption nobody has scheduled",
    "Neptune": "what is not being said plainly",
    "Pluto": "the power in the room that is not yours",
}

# Ordered worst-first ON PURPOSE. The engine returns a structured dict —
# {'dignities': ['triplicity'], 'debilities': ['fall'], 'score': -1} — and a
# planet can hold a minor dignity while being in fall. Scanning for the first
# match in dictionary order described Venus in fall as "reasonably supported",
# which is not a tone problem, it is a false statement about the chart.
# Debility outranks dignity, always.
DEBILITY_PLAIN = [
    ("fall", "at its weakest"),
    ("detriment", "out of its depth"),
    ("peregrine", "with nothing of its own to draw on"),
    ("combust", "hidden in the Sun's glare"),
    ("retrograde", "moving backwards on the matter"),
]
DIGNITY_PLAIN = [
    ("domicile", "on home ground"),
    ("rulership", "on home ground"),
    ("exaltation", "unusually well placed"),
    ("exalted", "unusually well placed"),
    ("triplicity", "reasonably supported"),
    ("term", "mildly supported"),
    ("face", "barely supported"),
]


def _plain_dignity(raw: Any) -> str:
    """Describe essential dignity honestly, worst news first."""
    if isinstance(raw, dict):
        debs = [str(d).lower() for d in (raw.get("debilities") or [])]
        digs = [str(d).lower() for d in (raw.get("dignities") or [])]
        if raw.get("peregrine") and "peregrine" not in debs:
            debs.append("peregrine")
    else:
        text = str(raw or "").lower()
        debs = [k for k, _ in DEBILITY_PLAIN if k in text]
        digs = [k for k, _ in DIGNITY_PLAIN if k in text]

    worst = next((plain for key, plain in DEBILITY_PLAIN if key in debs), "")
    best = next((plain for key, plain in DIGNITY_PLAIN if key in digs), "")

    if worst and best:
        # Both true. Say both — the mixture is the actual finding, and a
        # reader who is told only the bad half will not trust the good half
        # later.
        return f"{worst}, though not without one small support"
    if worst:
        return worst
    if best:
        return best
    return "in a mixed position"


# --- remedies ---------------------------------------------------------------
# Every unfavourable answer carries one. Practical action comes first: it is
# the part that actually changes an outcome, and psychologically it is the part
# that returns a sense of agency to someone who has just been told "not yet".

REMEDIES: dict[str, dict[str, str]] = {
    "Saturn": {
        "practical": "Do the boring, verifiable thing first — the document, the "
                     "written confirmation, the deadline in writing. Saturn only "
                     "obstructs what is half-finished.",
        "traditional": "Saturday is the day to act on this. Feeding or clothing "
                       "someone who works with their hands is the classical "
                       "offering, and giving black sesame or iron is traditional.",
        "mantra": "Om Sham Shanaishcharaya Namah, 108 times on a Saturday.",
    },
    "Mars": {
        "practical": "Take the heat out of it. One week of no arguing about this, "
                     "and let the other side move first — Mars rewards the person "
                     "who did not escalate.",
        "traditional": "Tuesday is the day. Giving red lentils or jaggery is the "
                       "classical offering.",
        "mantra": "Om Angarakaya Namah, 108 times on a Tuesday.",
    },
    "Sun": {
        "practical": "Go directly to the person who can actually decide. This "
                     "stalls when it is handled one level below the authority.",
        "traditional": "Offer water to the rising sun for a few mornings — the "
                       "classical remedy where standing is the obstacle.",
        "mantra": "Om Suryaya Namah at sunrise.",
    },
    "Moon": {
        "practical": "Do not decide this week. The Moon is moving the situation "
                     "and your reading of it will change within days — wait for "
                     "the picture to settle rather than forcing a choice now.",
        "traditional": "Monday is the day. Offering rice or milk is traditional.",
        "mantra": "Om Chandraya Namah, on a Monday evening.",
    },
    "Mercury": {
        "practical": "Put it in writing and re-read what you already sent. This "
                     "is a chart where the misunderstanding is in the wording.",
        "traditional": "Wednesday is the day. Giving green moong or helping a "
                       "student is the classical offering.",
        "mantra": "Om Budhaya Namah, 108 times on a Wednesday.",
    },
    "Venus": {
        "practical": "Repair the relationship before you push the request again. "
                     "This is a situation where people say yes to a person, not "
                     "to a proposal.",
        "traditional": "Friday is the day. Giving white cloth, curd or sugar is "
                       "traditional.",
        "mantra": "Om Shukraya Namah, 108 times on a Friday.",
    },
    "Jupiter": {
        "practical": "Ask someone senior to speak for you. This opens through a "
                     "sponsor rather than through your own effort.",
        "traditional": "Thursday is the day. Giving yellow items, turmeric or "
                       "chana dal is the classical offering.",
        "mantra": "Om Gurave Namah, 108 times on a Thursday.",
    },
    "Rahu": {
        "practical": "Check the thing that looks too convenient. This chart hides "
                     "a detail in whatever you have not personally verified.",
        "traditional": "Giving to those who are far from home is the traditional "
                       "offering here.",
        "mantra": "Om Rahave Namah, on a Saturday evening.",
    },
    "Ketu": {
        "practical": "Stop pursuing it for a fortnight. Ketu matters resolve when "
                     "you let go of the outcome, and re-approaching too soon is "
                     "what keeps this one stuck.",
        "traditional": "Feeding a dog, or giving a blanket, is the classical act.",
        "mantra": "Om Ketave Namah, on a Tuesday evening.",
    },
}

GENERAL_REMEDY = {
    "practical": "Give this a fixed review date rather than turning it over daily. "
                 "A question asked from anxiety gets re-asked; a question with a "
                 "review date gets answered.",
    "traditional": "Thursday is the general day for restarting a stalled matter.",
    "mantra": "Om Gurave Namah, 108 times on a Thursday.",
}


def _e(text: Any) -> str:
    return _html.escape(str(text or ""))


def _named(planet: str) -> str:
    """English takes an article before the luminaries: "the Moon", not "Moon"."""
    return f"the {planet}" if planet in ("Sun", "Moon") else planet


# --- the reconciliation ------------------------------------------------------

def _label_from_western(west: dict) -> tuple[str, bool | None, float]:
    """Map the Western engine verdict to the customer-facing label."""
    if west.get("out_of_domain"):
        return "Non-Astrological Inquiry", None, 0.0
    verdict = str(west.get("verdict") or "").strip().lower()
    if verdict in ("out_of_domain", "out of scope / non-horary query", "non-astrological inquiry"):
        return "Non-Astrological Inquiry", None, 0.0
    wd = _dir(verdict)
    try:
        tally = float(west.get("score", wd))
    except (TypeError, ValueError):
        tally = wd

    if verdict == "yes":
        return "Yes", True, max(wd, tally)
    if verdict in ("likely yes", "likely"):
        return "Leaning yes", True, max(wd, tally)
    if verdict in ("uncertain / qualified", "uncertain", "neutral"):
        return "Genuinely open", None, tally
    if verdict == "unlikely":
        return "Leaning no", False, min(wd, tally)
    if verdict == "no":
        return "No", False, min(wd, tally)

    score = wd * _conf(west.get("confidence"))
    if score >= 0.45:
        return "Yes", True, score
    if score >= 0.15:
        return "Leaning yes", True, score
    if score > -0.15:
        return "Genuinely open", None, score
    if score > -0.45:
        return "Leaning no", False, score
    return "No", False, score


def reconcile(verdicts: dict) -> dict:
    """Return the Western horary verdict as the single customer answer."""
    west = verdicts.get("western") or {}
    west_ok = "error" not in west and west.get("verdict")

    if not west_ok:
        return {"label": "Genuinely open", "score": 0.0, "confidence": "low",
                "favourable": None, "contradicted": False,
                "western": west, "vedic": {},
                "weights": dict(WEIGHTS), "usable": False}

    label, favourable, score = _label_from_western(west)
    conf_raw = str(west.get("confidence") or "moderate").strip().lower()
    confidence = conf_raw if conf_raw in ("good", "moderate", "low") else "moderate"

    return {"label": label, "score": round(float(score), 3), "confidence": confidence,
            "favourable": favourable, "contradicted": False,
            "western": west, "vedic": {},
            "weights": dict(WEIGHTS), "usable": True}


# --- the writing -------------------------------------------------------------

HEADLINE = {
    "Yes": "Yes — and the chart is not shy about it.",
    "Leaning yes": "Yes, more likely than not — with one condition attached.",
    "Genuinely open": "This one is genuinely still open.",
    "Leaning no": "Not on the current path — and the chart is specific about why.",
    "No": "No, not as things stand — but read the second half before you decide "
          "what that means.",
    "Non-Astrological Inquiry": "This inquiry falls outside the classical scope of horary astrology.",
}

CONFIDENCE_SENTENCE = {
    "good": "The methods agree, and they agree strongly. You can plan around this.",
    "moderate": "The methods agree on direction, with enough variation that I "
                "would treat this as a strong lean rather than a certainty.",
    "low": "Hold this one lightly. The chart is genuinely divided, and I would "
           "rather tell you that than dress up a coin-flip as an answer.",
}



def _parse_asked_date(asked: str) -> date:
    raw = str(asked or "").strip()
    for fmt in (
        "%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S",
        "%d %b %Y", "%d %B %Y", "%d-%m-%Y", "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(raw[:19], fmt).date()
        except ValueError:
            continue
    return date.today()


def _horary_requested_range(question: str, asked: str) -> tuple[date, date] | None:
    """Return an explicit question horizon; otherwise leave timing untouched."""
    q = re.sub(r"\s+", " ", str(question or "").lower())
    base = _parse_asked_date(asked)
    if re.search(r"\bthis year\b|\bwithin this year\b|\bby year[- ]end\b", q):
        return date(base.year, 1, 1), date(base.year, 12, 31)
    m = re.search(r"\bnext\s+(\d{1,2})\s+years?\b", q)
    if m:
        n = max(1, min(20, int(m.group(1))))
        try:
            end = base.replace(year=base.year + n)
        except ValueError:
            end = base.replace(year=base.year + n, month=2, day=28)
        return base, end
    if re.search(r"\bnext year\b", q):
        return base, base.replace(year=base.year + 1)
    return None


def filter_horary_timing_for_question(
    question: str,
    asked: str,
    verdicts: dict,
    western_judgment: dict,
    vedic_customer: dict | None = None,
) -> tuple[dict, dict, dict | None]:
    """Keep only dated horary triggers that fall inside an explicit question horizon.

    The verdict itself is not recalculated. Only timing candidates shown to the
    customer/LLM are filtered, so a 2026 question cannot display a 2027 trigger
    as if it answered the requested period.
    """
    horizon = _horary_requested_range(question, asked)
    if not horizon:
        return verdicts, western_judgment, vedic_customer

    start, end = horizon

    def as_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        raw = str(value or "").strip()
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d %b %Y", "%d %B %Y"):
            try:
                return datetime.strptime(raw[:19], fmt).date()
            except ValueError:
                continue
        return None

    def in_range(d: date | None) -> bool:
        return d is not None and start <= d <= end

    def filter_value(value, parent_key=""):
        if isinstance(value, dict):
            out = {}
            for k, v in value.items():
                kl = str(k).lower()
                if kl in {"timing", "timings", "windows", "timing_windows", "dated_windows", "triggers"} and isinstance(v, (list, tuple)):
                    out[k] = filter_timing_list(v)
                else:
                    out[k] = filter_value(v, kl)
            return out
        if isinstance(value, list):
            return [filter_value(v, parent_key) for v in value]
        return value

    def filter_timing_list(items):
        out = []
        for item in items or []:
            candidate = item[0] if isinstance(item, (tuple, list)) and item else (
                item.get("date") or item.get("start") or item.get("when") if isinstance(item, dict) else item
            )
            d = as_date(candidate)
            if d is None:
                # Keep undated explanatory entries; they are not false dates.
                out.append(item)
            elif in_range(d):
                out.append(item)
        return out

    filtered_verdicts = filter_value(deepcopy(verdicts))
    filtered_western = filter_value(deepcopy(western_judgment))
    filtered_vedic = filter_value(deepcopy(vedic_customer)) if vedic_customer is not None else None
    if isinstance(filtered_western, dict):
        timing_items = filtered_western.get("timing") or []
        if not timing_items:
            filtered_western["requested_horizon_note"] = (
                f"No strong dated trigger was identified between "
                f"{start.strftime('%d %b %Y')} and {end.strftime('%d %b %Y')}."
            )
        else:
            filtered_western["requested_horizon_note"] = (
                f"At least one dated trigger falls inside the period you asked about "
                f"({start.strftime('%d %b %Y')} to {end.strftime('%d %b %Y')})."
            )
    return filtered_verdicts, filtered_western, filtered_vedic


def _subject(question: str) -> str:
    """A short, human restatement so the reader feels heard before judged."""
    q = re.sub(r"\s+", " ", (question or "").strip().rstrip("?")).lower()
    if not q:
        return "your question"
    for pattern, phrasing in (
        (r"\bjob\b|\bwork\b|\bemploy", "your work situation"),
        (r"\bpromot", "the promotion"),
        (r"\bmarry|marriage|shaadi|wedding", "the marriage question"),
        (r"\bhouse|property|flat|land", "the property"),
        (r"\bmoney|loan|funding|salary", "the money side of this"),
        (r"\bhealth|illness|surgery", "your health question"),
        (r"\bvisa|abroad|foreign|relocat", "the move abroad"),
        (r"\bchild|pregnan|baby", "the question about a child"),
        (r"\bcase|court|legal", "the legal matter"),
        (r"\bexam|admission|study|course", "the studies"),
        (r"\bapp\b|\bmarket\b|\bsell\b|\bproduct\b|\bbusiness\b",
         "how this venture will fare"),
    ):
        if re.search(pattern, q):
            return phrasing
    raw = re.sub(r"\s+", " ", (question or "").strip().rstrip("?"))
    return raw[:80] + ("…" if len(raw) > 80 else "")


def _technical_lines(j: dict) -> list[str]:
    """The planets, explained — the part that makes the answer credible."""
    lines: list[str] = []
    asc_lord, q_lord = j.get("asc_lord"), j.get("q_lord")

    if asc_lord:
        role = PLANET_ROLE.get(asc_lord, "your side of this")
        lines.append(
            f"<strong>{_e(_named(asc_lord))} stands for you</strong> in this chart, and "
            f"it sits {_e(_plain_dignity(j.get('asc_ed')))} — which is a fair "
            f"description of {_e(role)} right now.")

    if q_lord and q_lord != asc_lord:
        lines.append(
            f"<strong>{_e(_named(q_lord))} stands for the thing you asked about</strong>, "
            f"{_e(_plain_dignity(j.get('q_ed')))}. That is the other half of the "
            f"picture: not how hard you are trying, but how ready the matter "
            f"itself is.")
    elif j.get("same_lord"):
        lines.append(
            "<strong>You and the matter share the same key indicator.</strong> "
            "That gives the question a more direct connection to you and reduces "
            "the sense that the outcome depends entirely on someone else's decision.")

    perfection = j.get("perfection")
    if isinstance(perfection, dict) and perfection.get("aspect"):
        applying = perfection.get("applying")
        lines.append(
            f"The two are connecting by {_e(perfection.get('aspect'))}"
            + (", and that connection is still forming — which is the classical "
               "signature of a matter that completes."
               if applying else
               ", but that connection has already passed its peak. In horary "
               "that usually means the moment for this particular approach has "
               "gone by, not that the door is shut."))
    elif j.get("moon_void"):
        lines.append(
            "<strong>The Moon is void of course</strong> — it makes no further "
            "connection before changing sign. The traditional reading is blunt: "
            "nothing much will come of the matter <em>in its present form</em>. "
            "It is one of the strongest arguments in the chart for changing the "
            "approach rather than repeating it.")
    else:
        lines.append(
            "There is no clean connection between your ruler and the matter's "
            "ruler. Left alone this drifts — it needs someone to force the "
            "meeting, and the chart is pointing at you.")

    if j.get("combust"):
        lines.append(
            "One of the main significators is combust — too close to the Sun to "
            "act freely. Read that as someone in this situation being "
            "overshadowed, or a position being weaker than it is presenting.")

    if j.get("moon_next") and isinstance(j["moon_next"], dict):
        nxt = j["moon_next"].get("planet")
        if nxt:
            lines.append(
                f"The Moon's next contact is with <strong>{_e(_named(nxt))}</strong>, "
                f"which is what colours the next development: "
                f"{_e(PLANET_ROLE.get(nxt, 'a change in the situation'))}.")
    return lines


def _score_of(ed: Any) -> float:
    if isinstance(ed, dict):
        try:
            return float(ed.get("score", 0))
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _blocking_planet(j: dict, vedic: dict | None = None) -> str:
    """The planet the remedy should address — the weakest significator."""
    del vedic  # Vedic/KP parked; Western significators only.
    candidates = [(j.get("asc_lord"), _score_of(j.get("asc_ed"))),
                  (j.get("q_lord"), _score_of(j.get("q_ed")))]
    candidates = [(n, sc) for n, sc in candidates if n]
    if candidates:
        name, score = min(candidates, key=lambda kv: kv[1])
        if score < 0:
            return name
    if j.get("combust") and j.get("asc_lord"):
        return j["asc_lord"]
    if j.get("moon_void"):
        return "Moon"
    if j.get("sat_house"):
        return "Saturn"
    return j.get("q_lord") or j.get("asc_lord") or ""


def _human_horary_timing_line(text: str) -> str:
    """Remove specialist period jargon from customer-facing horary timing."""
    raw = str(text or "").strip()
    raw = re.sub(r"\bdaśā/bhukti\b", "active periods", raw, flags=re.I)
    raw = re.sub(r"\bdasha/bhukti\b", "active periods", raw, flags=re.I)
    raw = re.sub(r"\bdaśā\b", "period", raw, flags=re.I)
    raw = re.sub(r"\bbhukti\b", "sub-period", raw, flags=re.I)
    raw = re.sub(r"\bRuling-Planet periods\b", "Timing periods", raw, flags=re.I)
    raw = re.sub(r"\bRuling Planets\b", "key timing indicators", raw, flags=re.I)
    raw = re.sub(r"\bsub-lord\b", "specialist timing factor", raw, flags=re.I)
    return raw


def _western_favour_against(j: dict) -> tuple[list[str], list[str]]:
    favour: list[str] = []
    against: list[str] = []
    asc_lord, q_lord = j.get("asc_lord"), j.get("q_lord")
    if asc_lord:
        (favour if _score_of(j.get("asc_ed")) >= 0 else against).append(asc_lord)
    if q_lord and q_lord != asc_lord:
        (favour if _score_of(j.get("q_ed")) >= 0 else against).append(q_lord)
    for name, _ in (j.get("combust") or []):
        if name not in against:
            against.append(name)
    if j.get("moon_void"):
        if "Moon" not in against:
            against.append("Moon")
    elif "Moon" not in favour and "Moon" not in against:
        favour.append("Moon")
    return favour, against


def _planetary_dynamics_block(r: dict, j: dict, vc: dict | None = None, *, lang: str = "en") -> str:
    """Planetary dynamics and supporting vs friction factors (Western horary)."""
    del vc  # Vedic timing/planet lists parked.
    is_hinglish = str(lang or "").lower() in ("hi_en", "hinglish", "hi", "hindi")
    from western_horary_report import plain_western_parts
    asc_lord, q_lord = j.get("asc_lord", ""), j.get("q_lord", "")
    p_parts = plain_western_parts(j, asc_lord, q_lord) if asc_lord else {}

    w_fav, w_against = _western_favour_against(j)
    favour = w_fav[:5]
    against = w_against[:5]

    if is_hinglish:
        agree_line = "Prashna kundli lagnesh aur karyesh ke bal, unki grah sthiti aur drishti sambandh ka vishleshan karti hai."
        sec_title = "Grah Sthiti Aur Sambandh"
        fav_lbl = "Aapke sahayak grah:"
        against_lbl = "Chunauti paida karne wale grah:"
    else:
        agree_line = (
            "The moment chart weighs the querent and quesited significators, "
            + ("their essential dignities, and whether a perfection is forming."
               if r["label"] != "Genuinely open" else
               "their essential dignities — the testimony is genuinely mixed rather than one-sided.")
        )
        sec_title = "Planetary dynamics & supporting influences"
        fav_lbl = "Planets supporting you:"
        against_lbl = "Planets creating friction:"

    planets_html = ""
    if favour or against:
        planets_html = (
            f"<div style='margin-top:12px;padding-top:10px;border-top:1px solid var(--line);'>"
            f"<p style='margin:4px 0'><strong>{fav_lbl}</strong> {_e(', '.join(favour)) if favour else 'None stand out strongly'}</p>"
            f"<p style='margin:4px 0'><strong>{against_lbl}</strong> {_e(', '.join(against)) if against else 'None stand out strongly'}</p>"
            f"</div>")

    parts_html = ""
    if p_parts:
        parts_html = (
            f"<p style='margin:0 0 0.5rem 0;'>{p_parts.get('opener', '')}</p>"
            f"<p style='margin:0 0 0.5rem 0;'>{p_parts.get('link', '')}</p>"
            f"<p style='margin:0 0 0.5rem 0;'>{p_parts.get('moon', '')}</p>"
        )

    return f"""
<section class="section planetary-dynamics">
  <h2>{sec_title}</h2>
  <div class="card">
    {parts_html}
    <p style="margin:0 0 0.6rem 0;">{agree_line}</p>
    {planets_html}
  </div>
</section>"""


def _timing_block(j: dict, vc: dict | None = None, *, paid: bool = True, lang: str = "en") -> str:
    """Consolidated dated windows from Western horary perfection timing."""
    del vc  # Vedic dasha timing lines parked.
    if not paid:
        return ""
    is_hinglish = str(lang or "").lower() in ("hi_en", "hinglish", "hi", "hindi")
    timing = j.get("timing") or []
    items = []
    if timing:
        for d, label, _plain in timing[:3]:
            items.append(f"<li><b>{d.strftime('%d %b %Y').lstrip('0')}</b> — {_e(label)}</li>")

    sec_title = "Mahatvapurna Dates Aur Timing Windows" if is_hinglish else "Key timing & dated windows"
    if not items:
        note = j.get("requested_horizon_note") or (
            "Koi ek nishchit date nahi hai; ise ek niyamit aur kramik prakriya ke roop mein samjhein." if is_hinglish else
            "No single dated window stands out; read this as a gradual process rather than one calendar day."
        )
        return f"""
<section class="section timing-windows">
  <h2>{sec_title}</h2>
  <div class="card">
    <p>{_e(note)}</p>
  </div>
</section>"""

    return f"""
<section class="section timing-windows">
  <h2>{sec_title}</h2>
  <div class="card">
    <ul class="windows">
      {''.join(items)}
    </ul>
  </div>
</section>"""


def _locked_block(*, price: int, n_windows: int, has_remedy: bool, lang: str = "en") -> str:
    """Free view: high-converting blurred preview cards and an unlock CTA."""
    is_hinglish = str(lang or "").lower() in ("hi_en", "hinglish", "hi", "hindi")
    if is_hinglish:
        return f"""
<div class="qa-window locked" data-unlock="1" role="button" tabindex="0" style="margin:14px 0;cursor:pointer;">
  <div class="qa-wlabel">Prashna Kundli Ka Faisla (The Verdict)</div>
  <p class="blurred">Prashna Kundli spasht faisla deti hai ki karya kab aur kaise safal hoga, aane wali rukawatein aur anukool dashaen kya hain.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Faisla locked hai.</b> Seedha uttar aur kundli ke tark dekhne ke liye unlock karein.</p>
</div>

<div class="qa-window locked" data-unlock="1" role="button" tabindex="0" style="margin:14px 0;cursor:pointer;">
  <div class="qa-wlabel">Grah Sthiti Aur Sahayak Urja</div>
  <p class="blurred">Aapke paksh mein kaun se grah hain aur kahan se rukawat aa sakti hai, iska poora vishleshan.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Grah vishleshan locked hai.</b> Sakriy grahon ki sthiti dekhne ke liye unlock karein.</p>
</div>

<div class="qa-window locked" data-unlock="1" role="button" tabindex="0" style="margin:14px 0;cursor:pointer;">
  <div class="qa-wlabel">Mahatvapurna Dates Aur Timing Windows</div>
  <p class="blurred">Karya safalta aur turning points ki nishchit dates aur mahatvapurna samay chakra.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Dates aur timing locked hain.</b> Nishchit dates aur milestone guidance ke liye unlock karein.</p>
</div>

<div class="qa-window locked" data-unlock="1" role="button" tabindex="0" style="margin:14px 0;cursor:pointer;">
  <div class="qa-wlabel">Prabhavi Grah Upay Aur Margdarshan</div>
  <p class="blurred">Badhak grah ko shant karne ke dainik upay, beej mantra jaap aur paramparik sujav.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Grah upay locked hain.</b> Badhak grah ke shanti upay aur mantra unlock karein.</p>
</div>

<div class="buy" style="margin-top:20px;">
  <h3>Poora Prashna Uttar Unlock Karein</h3>
  <p>Prashna kundli ban chuki hai. Poora faisla, dates aur grah upayas unlock karein.</p>
  <a class="cta" href="#unlock" data-unlock="1">Poori Reading Unlock Karein · ₹{price}</a>
</div>"""

    timing_teaser = (
        f"<b>{n_windows} dated window{'s' if n_windows != 1 else ''}</b> and planetary trigger periods identified across the requested horizon."
        if n_windows else
        "Exact turning-point timeline and culmination periods across the requested horizon.")

    return f"""
<div class="qa-window locked" data-unlock="1" role="button" tabindex="0" style="margin:14px 0;cursor:pointer;">
  <div class="qa-wlabel">The Verdict — moment-chart outcome & confidence</div>
  <p class="blurred">The Western horary chart delivers a direct verdict on whether this matter reaches completion, the strength of the opening, and the key obstacles to expect.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>The horary verdict is locked.</b> Unlock to read the direct answer, confidence assessment, and chart reasoning.</p>
</div>

<div class="qa-window locked" data-unlock="1" role="button" tabindex="0" style="margin:14px 0;cursor:pointer;">
  <div class="qa-wlabel">Planetary dynamics & supporting influences</div>
  <p class="blurred">Complete analysis of planets supporting your position versus planets creating friction or delay in the moment chart.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Planetary currents breakdown is locked.</b> Unlock to see the active forces driving or hindering this question.</p>
</div>

<div class="qa-window locked" data-unlock="1" role="button" tabindex="0" style="margin:14px 0;cursor:pointer;">
  <div class="qa-wlabel">Key timing & dated windows</div>
  <p class="blurred">Exact calendar dates when the applying planetary aspects culminate and when secondary developments unfold.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;">{timing_teaser} Unlock for the exact dates and milestone guidance.</p>
</div>

<div class="qa-window locked" data-unlock="1" role="button" tabindex="0" style="margin:14px 0;cursor:pointer;">
  <div class="qa-wlabel">Targeted remedies & immediate relief</div>
  <p class="blurred">Practical first steps to shift momentum, classical mantra jaap for the pressure planet, and traditional remedial actions.</p>
  <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Targeted remedies are locked.</b> Unlock to view the exact mantra rituals and practical steps to tip the timing your way.</p>
</div>

<div class="buy" style="margin-top:20px;">
  <h3>Unlock the full answer</h3>
  <p>The moment chart has been calculated. Unlock the complete verdict, exact timeline dates, and chart-targeted remedies.</p>
  <a class="cta" href="#unlock" data-unlock="1">Unlock full reading</a>
</div>"""


def build_answer_html(*, question: str, verdicts: dict, western_judgment: dict,
                      asked: str = "", name: str = "",
                      horary_price: int = 298,
                      full_report_price: int = 298,
                      vedic_customer: dict | None = None,
                      paid: bool = True,
                      prose: dict | None = None,
                      lang: str = "en") -> tuple[str, dict]:
    """The single answer the customer sees. Returns (html, summary).

    ``prose`` is an optional LLM overlay: lead, verdict_line, why, action.
    """
    prose = prose or {}
    is_hinglish = str(lang or "").lower() in ("hi_en", "hinglish", "hi", "hindi")
    # Enforce the requested horizon even when this renderer is called directly
    # (outside report_render). This keeps a "this year" question from showing
    # only a next-year trigger.
    verdicts, western_judgment, vedic_customer = filter_horary_timing_for_question(
        question, asked, verdicts, western_judgment, vedic_customer
    )
    r = reconcile(verdicts)
    j = western_judgment or {}
    subject = _subject(question)
    who = (name or "").split()[0] if name else ""
    greeting = f"{_e(who)}, " if who else ""

    headline = HEADLINE.get(r["label"], HEADLINE["Genuinely open"])
    conf_line = CONFIDENCE_SENTENCE[r["confidence"]]

    if r["contradicted"]:
        conf_line = CONFIDENCE_SENTENCE["low"]

    dynamics_html = _planetary_dynamics_block(r, j, lang=lang) if paid else ""
    timing_html = _timing_block(j, paid=paid, lang=lang) if paid else ""

    # An unfavourable answer ALWAYS carries a remedy (paid view only).
    remedy_html = ""
    remedy_planet = ""
    has_remedy = r["favourable"] is False or r["confidence"] == "low"
    if paid and has_remedy:
        planet = _blocking_planet(j)
        remedy_planet = planet
        rem = REMEDIES.get(planet, GENERAL_REMEDY)
        if is_hinglish:
            heading = "Sthiti Ko Sudharne Ke Prabhavi Grah Upay" if r["favourable"] is False else "Anukoolta Badhane Ke Upay"
            planet_note = f"Kundli mein mukhya dabav <strong>{_e(_named(planet))}</strong> par hai, isliye yeh upay nirdharit kiye gaye hain." if planet else ""
            do_first_lbl = "Pehle Yeh Karein:"
            trad_lbl = "Paramparik Sahayata:"
            rem_fine = "Upay kundli ke faisle ko badalte nahi hain, balki sthiti ko behtar dhang se sambhalne ki kshamta aur anukool samay aane par labh lene ki tayyari dete hain."
        else:
            heading = ("What actually moves this" if r["favourable"] is False
                       else "What tips a close chart your way")
            planet_note = (f"The pressure in this chart sits with "
                           f"<strong>{_e(_named(planet))}</strong>, so that is what these "
                           f"address." if planet else "")
            do_first_lbl = "Do this first."
            trad_lbl = "The traditional support."
            rem_fine = "Remedies are not a lever that overrides the chart. They work the way preparation works — they change what you are ready for when the timing does turn."
        remedy_html = f"""
<section class="section remedy" data-verdict="{'down' if r['favourable'] is False else 'mixed'}">
  <h2>{heading}</h2>
  <p>{planet_note}</p>
  <p><strong>{do_first_lbl}</strong> {rem['practical']}</p>
  <p><strong>{trad_lbl}</strong> {rem['traditional']}</p>
  <p class="mantra">{rem['mantra']}</p>
  <p class="fine">{rem_fine}</p>
</section>"""

    n_windows = len(j.get("timing") or [])
    if paid:
        if is_hinglish:
            tail_html = f"""
<section class="section upsell">
  <h2>Yeh ek prashna ka uttar tha. Aapki poori kundli aage ka margdarshan karti hai.</h2>
  <p>Prashna kundli vartaman kshan ka snapshot hai — yeh is prashna par spasht uttar deti hai. Aapki Janma Kundli doosra mukhya hissa hai: kab kaun sa daur shuru hoga, {_e(subject)} mein kab decisive turning point aayega aur baki jeevan kshetron mein grah kya prabhav de rahe hain.</p>
  <p>Poori reading aapki kundli par 15 alag-alag vidhiyon se vishleshan karti hai aur timeline dates deti hai — ₹{full_report_price}.</p>
</section>"""
        else:
            tail_html = f"""
<section class="section upsell">
  <h2>This answered one question. Your chart answers the rest.</h2>
  <p>A horary chart is a snapshot of one moment — it is very good at
  <em>this</em> question and says nothing about the year around it. Your birth
  chart is the other half: which periods open and close for you, when the
  pressure in {_e(subject)} actually lifts, and what the same planets are doing
  across work, money, health and relationships.</p>
  <p>The full reading crosses 15 independent methods over your own chart and
  gives you dated windows rather than one yes or no — ₹{full_report_price}.</p>
</section>"""
    else:
        tail_html = _locked_block(price=horary_price, n_windows=n_windows,
                                  has_remedy=has_remedy, lang=lang)

    llm_lead = (prose.get("lead") or "").strip()
    llm_verdict = (prose.get("verdict_line") or "").strip()
    llm_why = (prose.get("why") or "").strip()
    llm_action = (prose.get("action") or "").strip()

    sure_lbl = "Pramanikta / Vishwas Level:" if is_hinglish else "How sure is this?"
    is_ood = r.get("label") == "Non-Astrological Inquiry"
    if paid:
        if llm_lead:
            opening = f'<p class="lede">{_e(llm_lead)}</p>'
        elif is_ood:
            if is_hinglish:
                opening = (
                    f"<p class=\"lede\">Aapka yeh prashna ek technical ya non-astrological vishay par hai jo Prashna Kundli ke daayre se alag hai. "
                    f"Prashna (Horary) Jyotish aapke jeevan ke mukhya vishayon (jaise career, vivah, sampatti, court case, swasthya sudhar, yaatra, aur samay) par sateek margdarshan deta hai. "
                    f"Technical tasks ke liye specialized resources ka upyog karein. Yadi aapke jeevan se juda koi prashna ho, toh kripya bejhijhak poochhein.</p>")
            else:
                opening = (
                    f"<p class=\"lede\">Your question pertains to a technical, factual, or non-astrological topic outside the scope of classical horary chart analysis. "
                    f"Horary (Prashna) astrology specializes in human life inquiries — such as career developments, relationships, property, legal matters, travel, or health recovery. "
                    f"For technical tasks or general trivia, please refer to specialized resources. We invite you to ask any question regarding your personal life decisions or path.</p>")
        elif is_hinglish:
            opening = (
                f"<p class=\"lede\">{greeting}aapne {subject} ke baare mein prashna poocha hai. "
                f"Yahan seedha uttar aur uske pichhe ki grah sthiti ka vishleshan diya gaya hai.</p>")
        else:
            opening = (
                f"<p class=\"lede\">{greeting}you asked about {subject}. "
                f"Here is the straight answer, then exactly why the chart says it.</p>")
        if llm_verdict:
            why_line = (
                f'<p class="pred-why"><b>Why:</b> {_e(llm_why)}</p>'
                if llm_why else
                f"<p class=\"pred-why\"><b>Why:</b> Prashna kundli {_e(r.get('label','a mixed situation'))} darshati hai.</p>" if is_hinglish else
                f"<p class=\"pred-why\"><b>Why:</b> The moment chart reflects {_e(r.get('label','a mixed situation'))} with {_e(r.get('confidence','moderate'))} confidence.</p>"
            )
            action_line = (
                f'<p class="qa-action">{_e(llm_action)}</p>' if llm_action else ""
            )
            verdict_block = (
                f'<h1 class="verdict-line">{_e(llm_verdict)}</h1>'
                f"{why_line}"
                f"<p class=\"confidence\"><strong>{sure_lbl}</strong> {conf_line}</p>"
                f"{action_line}"
            )
        else:
            why_txt = "Prashna kundli human life aur decision-making par focus karti hai." if (is_ood and is_hinglish) else ("Horary chart analysis is designed for personal human life questions." if is_ood else f"The moment chart reflects {_e(r.get('label','a mixed situation'))} with {_e(r.get('confidence','moderate'))} confidence.")
            verdict_block = (
                f"<h1 class=\"verdict-line\">{headline}</h1>"
                f"<p class=\"pred-why\"><b>Why:</b> {why_txt}</p>"
                f"<p class=\"confidence\"><strong>{sure_lbl}</strong> {conf_line}</p>")
        verdict_flag = ("up" if r["favourable"] else
                        "down" if r["favourable"] is False else "mixed")
        lead_attrs = f'data-verdict="{verdict_flag}"'
    else:
        if llm_lead:
            opening = f'<p class="lede">{_e(llm_lead)}</p>'
        elif is_ood:
            if is_hinglish:
                opening = (
                    f"<p class=\"lede\">Aapka yeh prashna ek technical ya non-astrological vishay par hai jo Prashna Kundli ke daayre se alag hai. "
                    f"Prashna (Horary) Jyotish aapke jeevan ke mukhya vishayon (jaise career, vivah, sampatti, court case, swasthya sudhar, yaatra, aur samay) par sateek margdarshan deta hai.</p>")
            else:
                opening = (
                    f"<p class=\"lede\">Your question pertains to a technical, factual, or non-astrological topic outside the scope of classical horary chart analysis. "
                    f"Horary (Prashna) astrology specializes in human life inquiries — such as career developments, relationships, property, legal matters, travel, or health recovery.</p>")
        elif is_hinglish:
            opening = (
                f"<p class=\"lede\">{greeting}aapne {subject} ke baare mein prashna poocha hai. "
                f"Prashna kundli ka prarambhik vishleshan neeche diya gaya hai.</p>")
        else:
            opening = (
                f"<p class=\"lede\">{greeting}you asked about {subject}. "
                f"Here is the straight answer from the moment chart, then exactly why it says that.</p>")
        verdict_block = ""
        lead_attrs = ""

    asked_lbl = "Aapka Prashna:" if is_hinglish else "You asked:"
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<title>Your question — answered</title></head><body>
<article class="horary-answer">
<section class="section answer-lead" {lead_attrs}>
  <div class="asked"><strong>{asked_lbl}</strong> {_e(question)}
  {f'<span class="when">· {_e(asked)}</span>' if asked else ''}</div>
  {opening}
  {verdict_block}
</section>
{dynamics_html}
{timing_html}
{remedy_html}
{tail_html}
</article></body></html>"""

    summary = {"label": r["label"], "confidence": r["confidence"],
               "score": r["score"], "contradicted": r["contradicted"],
               "favourable": r["favourable"], "weights": r["weights"],
               "subject": subject}
    from qa_checks.final_customer_boundary import finalize_customer_html
    html = finalize_customer_html(html, strict=True)
    return html, summary
