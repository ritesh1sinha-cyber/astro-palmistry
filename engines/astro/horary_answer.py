"""One answer to the question — not two engines arguing in front of the customer.

Before this, someone who asked "Will I change my job?" was handed both
judgments side by side:

    Vedic:    LIKELY    (confidence LOW)
    Western:  Unlikely  (confidence moderate)

Two contradictory answers, no reconciliation, ₹99 paid. Nobody asks a question
in order to receive a disagreement.

The policy here is the operator's, and it is deliberate:

* **Western carries 60%, Vedic 40%.** Not because Western is "more true" —
  because horary is a Western technique at its core, its judgment rules are
  tighter, and its confidence scoring is better calibrated in our own testing.
* **When they contradict, Western's direction wins and the confidence drops to
  low.** Following the heavier weight while admitting the disagreement is
  honest. Averaging two opposite answers into a shrug is not.
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
from typing import Any

# --- policy ----------------------------------------------------------------

WEIGHTS = {"western": 0.60, "vedic": 0.40}

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

def reconcile(verdicts: dict) -> dict:
    """Combine the two judgments under the 60/40 policy."""
    west = verdicts.get("western") or {}
    ved = verdicts.get("vedic") or {}
    west_ok = "error" not in west and west.get("verdict")
    ved_ok = "error" not in ved and ved.get("verdict")

    wd, vd = _dir(west.get("verdict")), _dir(ved.get("verdict"))
    parts, total = 0.0, 0.0
    if west_ok:
        parts += WEIGHTS["western"] * wd * _conf(west.get("confidence"))
        total += WEIGHTS["western"]
    if ved_ok:
        parts += WEIGHTS["vedic"] * vd * _conf(ved.get("confidence"))
        total += WEIGHTS["vedic"]
    score = parts / total if total else 0.0

    # Do the two engines point opposite ways? A neutral reading is not a
    # contradiction — only a genuine sign flip is.
    contradicted = bool(west_ok and ved_ok and wd * vd < 0)

    if contradicted:
        # Policy: follow the heavier weight, and say plainly that it was close.
        # The 0.4 factor is a cap, not a fudge: it keeps a contradicted chart
        # inside the "leaning" bands so the copy can never print a flat "Yes"
        # or "No" over two methods that disagreed. Direction is Western's;
        # certainty is nobody's.
        score = wd * _conf(west.get("confidence")) * 0.4
        confidence = "low"
    else:
        base = max((c for c in (
            CONF_RANK.get(str(west.get("confidence", "")).lower(), 0) if west_ok else None,
            CONF_RANK.get(str(ved.get("confidence", "")).lower(), 0) if ved_ok else None,
        ) if c is not None), default=0)
        strength = abs(score)
        rank = min(base, 2 if strength >= 0.55 else 1 if strength >= 0.25 else 0)
        confidence = {0: "low", 1: "moderate", 2: "good"}[rank]

    if score >= 0.45:
        label, favourable = "Yes", True
    elif score >= 0.15:
        label, favourable = "Leaning yes", True
    elif score > -0.15:
        label, favourable = "Genuinely open", None
    elif score > -0.45:
        label, favourable = "Leaning no", False
    else:
        label, favourable = "No", False

    return {"label": label, "score": round(score, 3), "confidence": confidence,
            "favourable": favourable, "contradicted": contradicted,
            "western": west, "vedic": ved,
            "weights": dict(WEIGHTS), "usable": bool(west_ok or ved_ok)}


# --- the writing -------------------------------------------------------------

HEADLINE = {
    "Yes": "Yes — and the chart is not shy about it.",
    "Leaning yes": "Yes, more likely than not — with one condition attached.",
    "Genuinely open": "This one is genuinely still open.",
    "Leaning no": "Not on the current path — and the chart is specific about why.",
    "No": "No, not as things stand — but read the second half before you decide "
          "what that means.",
}

CONFIDENCE_SENTENCE = {
    "good": "The methods agree, and they agree strongly. You can plan around this.",
    "moderate": "The methods agree on direction, with enough variation that I "
                "would treat this as a strong lean rather than a certainty.",
    "low": "Hold this one lightly. The chart is genuinely divided, and I would "
           "rather tell you that than dress up a coin-flip as an answer.",
}


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
            "<strong>You and the matter share the same ruling planet.</strong> "
            "Classically that is a favourable sign on its own — it means the "
            "outcome is tied to you rather than to somebody else's decision.")

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


def _blocking_planet(j: dict, vedic: dict) -> str:
    """The planet the remedy should address — the weakest significator.

    The engine gives a numeric dignity score, so use it rather than hunting
    for the word "fall" in a stringified dict.
    """
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
    systems = (vedic or {}).get("systems") or {}
    for planet in ("Saturn", "Rahu", "Ketu", "Mars"):
        if planet.lower() in str(systems).lower():
            return planet
    return j.get("q_lord") or j.get("asc_lord") or ""


def _western_plain_block(j: dict, *, paid: bool = True) -> str:
    """Western — in plain words, plus a short timing line when paid."""
    from western_horary_report import plain_western_parts
    asc_lord, q_lord = j.get("asc_lord", ""), j.get("q_lord", "")
    if not asc_lord:
        return ""
    p = plain_western_parts(j, asc_lord, q_lord)
    timing_html = ""
    if paid:
        timing = j.get("timing") or []
        if timing:
            items = "".join(
                f"<li><b>{d.strftime('%d %b %Y').lstrip('0')}</b> — {_e(label)}</li>"
                for d, label, _plain in timing[:2])
            timing_html = (f"<p class=\"eyebrow\" style=\"margin:10px 0 4px\">Timing</p>"
                           f"<ul class=\"windows\">{items}</ul>")
        else:
            timing_html = ("<p class=\"eyebrow\" style=\"margin:10px 0 4px\">Timing</p>"
                           "<p>No single dated window stands out; read this as a "
                           "process rather than one calendar day.</p>")
    return f"""
<section class="section western-plain">
  <h2>Western — in plain words</h2>
  <div class="card">
    <p style="margin:0 0 0.5rem 0;">{p['opener']}</p>
    <p style="margin:0 0 0.5rem 0;">{p['link']}</p>
    <p style="margin:0 0 0.5rem 0;">{p['moon']}</p>
    <p style="margin:0 0 0.7rem 0;color:var(--muted);">{p['confline']}</p>
    {timing_html}
  </div>
</section>"""


def _human_horary_timing_line(text: str) -> str:
    """Remove specialist period jargon from customer-facing horary timing."""
    raw = str(text or "").strip()
    raw = re.sub(r"\bdaśā/bhukti\b", "active periods", raw, flags=re.I)
    raw = re.sub(r"\bdasha/bhukti\b", "active periods", raw, flags=re.I)
    raw = re.sub(r"\bdaśā\b", "period", raw, flags=re.I)
    raw = re.sub(r"\bbhukti\b", "sub-period", raw, flags=re.I)
    raw = re.sub(r"\bRuling-Planet periods\b", "Timing periods", raw, flags=re.I)
    raw = re.sub(r"\bsub-lord\b", "specialist timing factor", raw, flags=re.I)
    return raw


def _vedic_plain_block(vedic_customer: dict, *, paid: bool = True) -> str:
    """Vedic — the three classical systems, each in one line; timing and remedy
    only when paid."""
    vc = vedic_customer or {}
    systems = [("Jamakkol Prasanam", vc.get("jamakkol")),
               ("Prashna Kundali", vc.get("prashna")),
               ("Specialist timing check", vc.get("kp"))]
    cls_for = {"YES": "up", "CONDITIONAL": "mixed", "NEUTRAL": "mixed", "NO": "down"}
    word_for = {"YES": "Favourable", "CONDITIONAL": "Conditional", "NEUTRAL": "Neutral", "NO": "Challenging"}
    cards = []
    for name, sub in systems:
        if not sub:
            continue
        if name == "Specialist timing check" and not sub.get("available", True):
            continue
        label = sub.get("label", "NEUTRAL")
        cards.append(
            f"<div class=\"card\" style=\"margin-bottom:8px;\">"
            f"<span class=\"pill {cls_for.get(label,'mixed')}\">{word_for.get(label,'Conditional')}</span> "
            f"<strong>{_e(name)}</strong> — {sub.get('plain','')}</div>")
    if not cards:
        return ""
    timing_html = ""
    remedy_html = ""
    if paid:
        timing_lines = vc.get("timing_lines") or []
        if timing_lines:
            timing_html = (
                "<p class=\"eyebrow\" style=\"margin:10px 0 4px\">Timing (all three systems)</p>"
                f"<ul class=\"windows\">{''.join(f'<li>{_e(_human_horary_timing_line(t))}</li>' for t in timing_lines)}</ul>")
        strengthen = vc.get("strengthen_planets") or []
        pacify = vc.get("pacify_planets") or []
        if strengthen or pacify:
            remedy_html = (
                "<p class=\"eyebrow\" style=\"margin:10px 0 4px\">Remedy</p>"
                f"<p><strong>Strengthen:</strong> {_e(', '.join(strengthen)) or '—'}"
                + (f" &nbsp;·&nbsp; <strong>Pacify:</strong> {_e(', '.join(pacify))}"
                   if pacify else "")
                + "</p>")
    return f"""
<section class="section vedic-plain">
  <h2>Vedic — three classical systems</h2>
  {''.join(cards)}
  {timing_html}
  {remedy_html}
</section>"""


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


def _locked_block(*, price: int, n_windows: int, has_remedy: bool) -> str:
    """Free view: section headings with one-line teasers and an unlock CTA."""
    timing_teaser = (
        f"{n_windows} dated window{'s' if n_windows != 1 else ''} "
        "from the Western chart, plus the Vedic trigger periods."
        if n_windows else
        "When this moves, and when it does not.")
    rows = [
        ("The verdict",
         "Where Western and all three Vedic systems land together — one answer, "
         "and how sure it is."),
        ("Planets in favour, planets against",
         "Which planets are carrying this question and which are blocking it."),
        ("Timing", timing_teaser),
    ]
    if has_remedy:
        rows.append(("The remedy",
                     "The one planet the pressure sits with, and what settles it."))
    items = "".join(
        f'<div class="when locked-inline" style="margin:8px 0">'
        f'<span class="lockicon">•</span> <strong>{_e(title)}</strong> — {_e(teaser)}'
        f'</div>'
        for title, teaser in rows)
    return f"""
<section class="section locked-preview">
  <h2>In the full reading</h2>
  <div class="card">{items}</div>
  <div class="buy">
    <h3>The answer itself</h3>
    <p>Three methods have read your question. Unlock what they add up to.</p>
    <a class="cta" href="#unlock" data-unlock="1">Unlock full reading</a>
  </div>
</section>"""


def _confluence_block(r: dict, j: dict, vedic_customer: dict, remedy_html: str,
                      remedy_planet: str = "") -> str:
    vc = vedic_customer or {}
    w_fav, w_against = _western_favour_against(j)
    net: dict[str, int] = {}
    for p in w_fav:
        net[p] = net.get(p, 0) + 1
    for p in vc.get("favour_planets") or []:
        net[p] = net.get(p, 0) + 1
    for p in w_against:
        net[p] = net.get(p, 0) - 1
    for p in vc.get("against_planets") or []:
        net[p] = net.get(p, 0) - 1
    # The remedy names one planet as where the pressure sits — never show that
    # same planet as "in favour" a few lines above the remedy that targets it.
    if remedy_planet:
        net[remedy_planet] = min(net.get(remedy_planet, 0), -1)
    favour = [p for p, v in net.items() if v > 0][:5]
    against = [p for p, v in net.items() if v < 0][:5]

    agree_line = (
        "Western and all three Vedic systems were weighed together for this verdict; "
        + ("they pointed in opposite directions, so the confidence below is deliberately capped."
           if r["contradicted"] else
           "they broadly agreed on direction.")
    )
    planets_html = ""
    if favour or against:
        planets_html = (
            f"<p><strong>Planets in favour:</strong> {_e(', '.join(favour)) if favour else 'none stand out clearly'}</p>"
            f"<p><strong>Planets working against:</strong> {_e(', '.join(against)) if against else 'none stand out clearly'}</p>")
    return f"""
<section class="section final-confluence">
  <h2>Final verdict — Western + Vedic together</h2>
  <div class="card">
    <p style="margin:0 0 0.6rem 0;">{agree_line}</p>
    {planets_html}
  </div>
</section>
{remedy_html}"""


def build_answer_html(*, question: str, verdicts: dict, western_judgment: dict,
                      asked: str = "", name: str = "",
                      horary_price: int = 298,
                      full_report_price: int = 298,
                      vedic_customer: dict | None = None,
                      paid: bool = True,
                      prose: dict | None = None) -> tuple[str, dict]:
    """The single answer the customer sees. Returns (html, summary).

    ``prose`` is an optional LLM overlay: lead, verdict_line, why, action.
    """
    prose = prose or {}
    r = reconcile(verdicts)
    j = western_judgment or {}
    vc = vedic_customer or (r["vedic"] or {}).get("customer") or {}
    subject = _subject(question)
    who = (name or "").split()[0] if name else ""
    greeting = f"{_e(who)}, " if who else ""

    headline = HEADLINE.get(r["label"], HEADLINE["Genuinely open"])
    conf_line = CONFIDENCE_SENTENCE[r["confidence"]]

    if r["contradicted"]:
        conf_line = (
            "The two methods I use came out on opposite sides of this one. "
            "I have gone with the reading that carries more weight for a "
            "question asked in the moment, and dropped the confidence to match "
            "— because a split chart is a real finding, not something to paper "
            "over.")

    western_html = _western_plain_block(j, paid=paid)
    vedic_html = _vedic_plain_block(vc, paid=paid)

    # An unfavourable answer ALWAYS carries a remedy (paid view only).
    remedy_html = ""
    remedy_planet = ""
    has_remedy = r["favourable"] is False or r["confidence"] == "low"
    if paid and has_remedy:
        planet = _blocking_planet(j, r["vedic"])
        remedy_planet = planet
        rem = REMEDIES.get(planet, GENERAL_REMEDY)
        heading = ("What actually moves this" if r["favourable"] is False
                   else "What tips a close chart your way")
        planet_note = (f"The pressure in this chart sits with "
                       f"<strong>{_e(_named(planet))}</strong>, so that is what these "
                       f"address." if planet else "")
        remedy_html = f"""
<section class="section remedy" data-verdict="{'down' if r['favourable'] is False else 'mixed'}">
  <h2>{heading}</h2>
  <p>{planet_note}</p>
  <p><strong>Do this first.</strong> {rem['practical']}</p>
  <p><strong>The traditional support.</strong> {rem['traditional']}</p>
  <p class="mantra">{rem['mantra']}</p>
  <p class="fine">Remedies are not a lever that overrides the chart. They work
  the way preparation works — they change what you are ready for when the
  timing does turn.</p>
</section>"""

    n_windows = len(j.get("timing") or [])
    if paid:
        confluence_html = _confluence_block(r, j, vc, remedy_html, remedy_planet)
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
        confluence_html = ""
        tail_html = _locked_block(price=horary_price, n_windows=n_windows,
                                  has_remedy=has_remedy)

    llm_lead = (prose.get("lead") or "").strip()
    llm_verdict = (prose.get("verdict_line") or "").strip()
    llm_why = (prose.get("why") or "").strip()
    llm_action = (prose.get("action") or "").strip()

    if paid:
        if llm_lead:
            opening = f'<p class="lede">{_e(llm_lead)}</p>'
        else:
            opening = (
                f"<p class=\"lede\">{greeting}you asked about {subject}. "
                f"Here is the straight answer, then exactly why the chart says it.</p>")
        if llm_verdict:
            why_line = (
                f'<p class="pred-why"><b>Why:</b> {_e(llm_why)}</p>'
                if llm_why else
                f"<p class=\"pred-why\"><b>Why:</b> Western read {_e(j.get('verdict','mixed'))}; "
                f"Vedic {_e(r.get('label','mixed'))}; confidence {_e(r.get('confidence','moderate'))}.</p>"
            )
            action_line = (
                f'<p class="qa-action">{_e(llm_action)}</p>' if llm_action else ""
            )
            verdict_block = (
                f'<h1 class="verdict-line">{_e(llm_verdict)}</h1>'
                f"{why_line}"
                f"<p class=\"confidence\"><strong>How sure is this?</strong> {conf_line}</p>"
                f"{action_line}"
            )
        else:
            verdict_block = (
                f"<h1 class=\"verdict-line\">{headline}</h1>"
                f"<p class=\"pred-why\"><b>Why:</b> Western read {_e(j.get('verdict','mixed'))}; "
                f"Vedic {_e(r.get('label','mixed'))}; confidence {_e(r.get('confidence','moderate'))}.</p>"
                f"<p class=\"confidence\"><strong>How sure is this?</strong> {conf_line}</p>")
        verdict_flag = ("up" if r["favourable"] else
                        "down" if r["favourable"] is False else "mixed")
        lead_attrs = f'data-verdict="{verdict_flag}"'
    else:
        if llm_lead:
            opening = f'<p class="lede">{_e(llm_lead)}</p>'
        else:
            opening = (
                f"<p class=\"lede\">{greeting}you asked about {subject}. "
                f"Four classical methods read this chart independently — Western horary "
                f"and three Vedic systems. Here is what each one found on its own.</p>")
        verdict_block = ""
        lead_attrs = ""

    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<title>Your question — answered</title></head><body>
<article class="horary-answer">
<section class="section answer-lead" {lead_attrs}>
  <div class="asked"><strong>You asked:</strong> {_e(question)}
  {f'<span class="when">· {_e(asked)}</span>' if asked else ''}</div>
  {opening}
  {verdict_block}
</section>
{western_html}
{vedic_html}
{confluence_html}
{tail_html}
</article></body></html>"""

    summary = {"label": r["label"], "confidence": r["confidence"],
               "score": r["score"], "contradicted": r["contradicted"],
               "favourable": r["favourable"], "weights": r["weights"],
               "subject": subject}
    return html, summary
