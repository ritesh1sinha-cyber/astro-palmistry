"""The report, rebuilt as prediction cards instead of prose.

The old report was 68 documents of continuous text. Cleaning its language
helped, but the structure was still an analyst's working file: everything the
engine knew, in the order the engine computed it. A customer does not want the
working. They want to know what happens, when, and what to do about it.

So this does not touch the old HTML at all. It reads the precompute directly
and builds one thing repeatedly:

    ┌──────────────────────────────────────────────┐
    │ WORK & CAREER                    under strain │   ← area + direction
    │ Recognition lags behind the work you're       │   ← the claim, plain
    │ actually doing.                               │
    │ Now → March 2027                              │   ← dated window
    │ Mercury rules your 10th and sits there        │   ← the evidence:
    │ debilitated · Jupiter–Ketu period · score 32  │     planet + dasha
    │ ▸ What helps                                  │   ← remedy, if needed
    └──────────────────────────────────────────────┘

Four rules the card format enforces, which prose did not:

1. **Every claim is dated.** A prediction without a window is a horoscope.
2. **Every claim shows its planet and its period.** That is what separates
   this from "you will have an attractive face"; the reader can see the
   reasoning is specific to their chart.
3. **Nothing runs longer than a few lines.** If it cannot be said in three
   sentences, the reader was going to skim it anyway.
4. **An unfavourable card always carries an action.**

The confluence stays in the engine. It decides the verdict and supplies a
confidence chip — it is not something the customer should have to read.
"""

from __future__ import annotations

import html as _html
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Optional

# The stylesheet moved to report_shell so horary, numerology, matching and the
# palm tab render in the same visual language from ONE source. Interpolated
# below as {_STYLE}, so this report is byte-identical to before the move.
from report_shell import STYLE as _STYLE, EXTRA as _EXTRA, INTERACT as _INTERACT

# ---------------------------------------------------------------------------
# life areas — named the way people think about their lives, not by house
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Area:
    key: str
    label: str
    house: int               # primary house
    support: tuple            # supporting houses
    subject: str              # how the claim refers to it


AREAS: tuple[Area, ...] = (
    Area("career", "Work & Career", 10, (6, 11), "your work"),
    Area("money", "Money", 2, (11,), "money"),
    Area("love", "Love & Marriage", 7, (5,), "your closest relationship"),
    Area("home", "Home & Family", 4, (2,), "home and family"),
    Area("children", "Children", 5, (9,), "children"),
    Area("health", "Health & Energy", 1, (6, 8), "your health"),
    Area("learning", "Learning & Luck", 9, (5,), "study and good fortune"),
    Area("inner", "Inner Life", 12, (9,), "your inner life"),
)

PLANET_VOICE = {
    "Sun": "recognition and authority",
    "Moon": "mood and the people close to you",
    "Mars": "drive, conflict and how hard you push",
    "Mercury": "communication, paperwork and negotiation",
    "Jupiter": "opportunity, teachers and expansion",
    "Venus": "goodwill, comfort and what you enjoy",
    "Saturn": "delay, discipline and what you earn slowly",
    "Rahu": "ambition and the unfamiliar",
    "Ketu": "detachment and what quietly falls away",
}

DIGNITY_WEIGHT = {
    "exalted": 2, "moolatrikona": 2, "own_sign": 1.5, "own sign": 1.5,
    "friendly_sign": 1, "friend": 1, "neutral_sign": 0, "neutral": 0,
    "enemy_sign": -1, "enemy": -1, "debilitated": -2,
}
DIGNITY_PLAIN = {
    "exalted": "at its strongest", "moolatrikona": "on its best ground",
    "own_sign": "in its own sign", "own sign": "in its own sign",
    "friendly_sign": "comfortably placed", "friend": "comfortably placed",
    "neutral_sign": "neutrally placed", "neutral": "neutrally placed",
    "enemy_sign": "on difficult ground", "enemy": "on difficult ground",
    "debilitated": "at its weakest",
}

# Canonical prediction copy lives in predict_voice.AREA_SCENE
try:
    import predict_voice as _PV
    CLAIMS = _PV.AREA_SCENE
except Exception:  # noqa: BLE001
    CLAIMS = {}

ACTIONS: dict[str, str] = {
    "Sun": "Deal directly with whoever actually decides. This stalls one level below the authority.",
    "Moon": "Protect your sleep and your home routine. Your focus is downstream of both.",
    "Mars": "Do not escalate this month. Let the other side move first.",
    "Mercury": "Put it in writing. The misunderstanding here is in the wording, not the intent.",
    "Jupiter": "Ask someone senior to speak for you. This opens through a sponsor.",
    "Venus": "Repair the relationship before pressing the request again.",
    "Saturn": "Finish the boring, verifiable part first. Saturn only blocks what is half-done.",
    "Rahu": "Verify the thing that looks too convenient.",
    "Ketu": "Step back for a fortnight. This one loosens when you stop gripping it.",
}

SUPPORT_ACTIONS: dict[str, str] = {
    "career": "Use this window to show your work, ask for the responsibility you want, and follow important conversations in writing.",
    "money": "Use the easier phase to strengthen savings and reduce money that quietly leaks away.",
    "love": "Use the warmer phase to have the conversation you have been postponing and make time for the relationship.",
    "home": "Use the stable phase to settle recurring home matters and strengthen your family routine.",
    "children": "Encourage progress without rushing it. Consistency will help more than pressure.",
    "health": "Use the stronger phase to build the routines that keep your energy steady, rather than assuming you can always push harder.",
    "learning": "Use the opening to learn something useful and apply it immediately instead of only collecting information.",
    "inner": "Use the quieter phase for reflection, learning or spiritual practice instead of forcing every answer.",
}

MANTRA = {
    "Sun": "Om Suryaya Namah at sunrise", "Moon": "Om Chandraya Namah on Mondays",
    "Mars": "Om Angarakaya Namah on Tuesdays", "Mercury": "Om Budhaya Namah on Wednesdays",
    "Jupiter": "Om Gurave Namah on Thursdays", "Venus": "Om Shukraya Namah on Fridays",
    "Saturn": "Om Sham Shanaishcharaya Namah on Saturdays",
    "Rahu": "Om Rahave Namah on Saturday evenings",
    "Ketu": "Om Ketave Namah on Tuesday evenings",
}


def _stage_action(area: str, band: str) -> str:
    try:
        from narration.stage_actions import action_for_stage
        line = action_for_stage(area, band)
        if line:
            return line
    except Exception:  # noqa: BLE001
        pass
    return SUPPORT_ACTIONS.get(
        area, "Use the supportive phase deliberately rather than waiting for it to pass.")


# ---------------------------------------------------------------------------

@dataclass
class Card:
    area: str
    label: str
    direction: str                 # up | mixed | down
    headline: str                  # scenario (plain prediction)
    backing: str = ""              # one-line Why
    window: str = ""
    evidence: list = field(default_factory=list)  # legacy; use backing
    action: str = ""
    mantra: str = ""
    agreement: str = ""            # confidence chip, not method counts
    planets: list = field(default_factory=list)
    trajectory: list = field(default_factory=list)
    locked: bool = False           # kept for callers that still gate whole cards


def _d(value: Any) -> Optional[date]:
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _pretty(d: Optional[date]) -> str:
    return f"{d:%b %Y}".replace(" 0", " ") if d else ""


def _pretty_long(d: Optional[date]) -> str:
    return f"{d:%B %Y}".replace(" 0", " ") if d else ""


def free_confidence_label(agreement: str, direction: str) -> str:
    """Customer-facing Free chip — no technical 'agreement' vocabulary."""
    if direction == "down":
        return "Needs care"
    text = (agreement or "").lower()
    if "strong" in text:
        return "strong support"
    return "mixed support"


def _window(start: Any, end: Any, today: Optional[date] = None) -> str:
    today = today or date.today()
    a, b = _d(start), _d(end)
    if not b:
        return ""
    if a and a <= today <= b:
        return f"Now → {_pretty(b)}"
    return f"{_pretty(a)} → {_pretty(b)}"


def current_ad(pc: dict) -> dict:
    for ad in (pc.get("vimshottari", {}).get("current_md_antardashas") or []):
        if ad.get("status") == "current":
            return ad
    return {}


def _dasha_touches(pc: dict, house: int, lords: list) -> bool:
    """Is the running period pointed at this house?"""
    hl = pc.get("house_lords", {})
    info = hl.get(str(house)) or {}
    planets = pc.get("planets", {})
    for lord in lords:
        if not lord:
            continue
        if info.get("lord") == lord:
            return True
        if (planets.get(lord) or {}).get("house") == house:
            return True
    return False


def score_area(pc: dict, area: Area, *, today: Optional[date] = None) -> tuple:
    """Verdict for one life area — unified confluence report."""
    today = today or date.today()
    try:
        import area_report as AR
        report = AR.build_area(pc, area.key, area.house, today=today)
        verdict = {
            "direction": report.direction,
            "headline": report.prediction,
            "backing": report.proof,
            "confidence": report.confidence,
            "score": report.score,
            "when": report.when,
            "remedy": report.remedy,
        }
        return (report.direction, [report.proof], report.score, verdict)
    except Exception:
        pass

    # fall back to the single-method read rather than failing a report
    hl = pc.get("house_lords", {})
    info = hl.get(str(area.house)) or {}
    dignity = str(info.get("lord_dignity") or "").lower()
    score = DIGNITY_WEIGHT.get(dignity, 0.0)
    direction = "up" if score >= 1.5 else ("down" if score <= -1 else "mixed")
    lord = info.get("lord") or ""
    return direction, [f"<b>{lord}</b> rules this area"], score, {}


def _ord(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def build_cards(pc: dict, *, today: Optional[date] = None,
                free_areas: int = 0,
                gate: Optional[Any] = None) -> list:
    """One card per life area, ordered so the sharpest reading leads."""
    today = today or date.today()
    from interpretation.life_stage import age_band
    from narration.area_labels import area_label as _age_area_label
    from qa_checks.report_diversity import ReportDiversityGate

    if gate is None:
        gate = ReportDiversityGate()
    band = age_band(pc, today=today)
    vim = pc.get("vimshottari", {}) or {}
    md = vim.get("current_md", {}) or {}
    ad = current_ad(pc)
    md_lord, ad_lord = md.get("md_lord", ""), ad.get("ad_lord", "")

    cards = []
    for area in AREAS:
        direction, evidence, score, verdict = score_area(pc, area, today=today)
        live = _dasha_touches(pc, area.house, [md_lord, ad_lord])
        headline = _manifest_card_headline(
            pc, area, direction, today=today, gate=gate)
        if not headline:
            headline = (verdict or {}).get("headline") or CLAIMS.get(
                (area.key, direction), "")
        backing = (verdict or {}).get("backing") or (evidence[0] if evidence else "")
        window = (verdict or {}).get("when") or ""
        remedy = (verdict or {}).get("remedy") or ""
        if not remedy:
            try:
                import area_report as AR
                remedy = AR.classical_area_remedy(pc, area.key, area.house, direction)
            except Exception:  # noqa: BLE001
                remedy = ""

        # Current MD/AD plus any Jupiter/Saturn transit on this area's house.
        planets_involved = []
        for p in (md_lord, ad_lord):
            if p and p not in planets_involved:
                planets_involved.append(p)
        try:
            import report_timing as RT
            transit_segments = RT.transit_segments(
                pc, start=today - timedelta(days=30), years=1)
            for planet, segs in transit_segments.items():
                for seg in segs:
                    if (seg.get("house") == area.house
                            and seg.get("start") <= today <= seg.get("end")):
                        if planet not in planets_involved:
                            planets_involved.append(planet)
                        break
        except Exception:  # noqa: BLE001
            pass

        trajectory = []
        try:
            import report_timing as RT
            rows = RT.windows_for_area(
                pc, area.key, area.house, start=today, years=5)
            for r in rows:
                if not r.get("start"):
                    continue
                rd = ("up" if r.get("aligned")
                      else ("down" if r.get("dasha") == "down"
                            or r.get("promise") == "down"
                            or int(r.get("bav", 0) or 0) <= 3
                            else "mixed"))
                trajectory.append({
                    "start": r.get("start"), "end": r.get("end"),
                    "direction": rd, "planet": r.get("planet", ""),
                    "dasha": r.get("dasha_label", ""),
                })
            trajectory.sort(key=lambda x: x.get("start"))
            trajectory = trajectory[:4]
        except Exception:  # noqa: BLE001
            trajectory = []

        card = Card(
            area=area.key, label=_age_area_label(area.key, band), direction=direction,
            headline=headline, backing=backing, window=window, evidence=[],
            action=remedy or _stage_action(area.key, band),
            mantra="",
            agreement=(verdict or {}).get("confidence")
            or (verdict or {}).get("agreement", ""),
            planets=planets_involved, trajectory=trajectory,
        )
        cards.append((abs(score) + (1 if live else 0), card))

    # sharpest and most active first — a reader should meet the strongest
    # statement about their life on line one, not the 1st house by convention
    cards.sort(key=lambda kv: -kv[0])
    ordered = [c for _, c in cards]
    # free_areas=0 is the default now: EVERY headline is free, and the paywall
    # sits on the dated window and the remedy inside each card. Locking whole
    # cards hid whichever areas the chart happened to speak loudest about —
    # on a test chart that meant Career was hidden and Children was free.
    # Seeing the whole picture and paying for "when" and "what to do" is both
    # a better hook and an honest one.
    for c in ordered[free_areas:] if free_areas else []:
        c.locked = True
    return ordered


def _manifest_card_headline(
    pc: dict,
    area: Area,
    direction: str,
    *,
    today: date,
    gate: Any,
) -> str:
    """Evidence-weighted current-situation headline for a life-area card."""
    try:
        import report_confluence as CF
        from interpretation.evidence_builder import build_evidence
        from interpretation.life_stage import age_band
        from interpretation.prediction_meaning import build_meaning

        band = age_band(pc, today=today)
        dasha = CF.dasha_confluence(pc, today)
        row = {"promise": direction, "dasha": direction, "house": area.house}
        evidence = build_evidence(
            pc, area=area.key, house=area.house, direction=direction,
            row=row, dasha=dasha, age_band=band)
        meaning = build_meaning(evidence)
        line, _ = gate.validate_current("", meaning)
        return line
    except Exception:  # noqa: BLE001
        return ""


def build_timeline(pc: dict, *, today: Optional[date] = None,
                   limit: int = 6) -> list:
    """The next few chapters, one line each, with real dates."""
    today = today or date.today()
    vim = pc.get("vimshottari", {}) or {}
    hl = pc.get("house_lords", {}) or {}
    planets = pc.get("planets", {}) or {}
    rows = []
    for ad in (vim.get("current_md_antardashas") or []):
        end = _d(ad.get("end"))
        if not end or end < today:
            continue
        lord = ad.get("ad_lord", "")
        houses = [int(h) for h, v in hl.items() if v.get("lord") == lord]
        sits = (planets.get(lord) or {}).get("house")
        try:
            from interpretation.life_stage import age_band as _band
            from narration.area_labels import area_label as _alabel
            _b = _band(pc, today=today)
            areas = sorted({_alabel(a.key, _b) for a in AREAS
                            if a.house in houses or a.house == sits
                            or any(h in a.support for h in houses)
                            or sits in a.support})
        except Exception:  # noqa: BLE001
            areas = sorted({a.label for a in AREAS
                            if a.house in houses or a.house == sits
                            or any(h in a.support for h in houses)
                            or sits in a.support})
        end_p = _pretty(_d(ad.get("end")))
        try:
            import impact as IMP
            impact_line = IMP.dasha_impact(lord, end_pretty=end_p)
        except Exception:  # noqa: BLE001
            impact_line = PLANET_VOICE.get(lord, "")
        rows.append({
            "window": _window(ad.get("start"), ad.get("end"), today),
            "lord": lord,
            "theme": impact_line or PLANET_VOICE.get(lord, ""),
            "areas": areas[:3],
            "current": ad.get("status") == "current",
        })
        if len(rows) >= limit:
            break
    return rows


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


DIRECTION_LABEL = {
    "up": "supportive",
    "mixed": "mixed",
    "down": "more demanding",
}
EXPECT_LABEL = {
    "up": "Improving",
    "mixed": "Mixed",
    "down": "More demanding",
}


def render(pc: dict, *, name: str = "", question_html: str = "",
           price: int = 298, today: Optional[date] = None,
           paid: bool = False, proof_html: str = "",
           daily_html: str = "", timing_html: str = "") -> str:
    today = today or date.today()
    from qa_checks.report_diversity import ReportDiversityGate
    gate = ReportDiversityGate()
    cards = build_cards(pc, today=today, gate=gate)
    timeline = build_timeline(pc, today=today)
    vim = pc.get("vimshottari", {}) or {}
    md, ad = vim.get("current_md", {}) or {}, current_ad(pc)
    lagna = (pc.get("lagna") or {}).get("sign", "")
    moon = (pc.get("planets", {}).get("Moon") or {})
    first = (name or "").split()[0] if name else "You"

    # Four timing lenses, not one. Vimshottari + Yogini + Chara (Jaimini)
    # clocks, plus BNN as a nadi vote on the current Vim MD/AD lords.
    # Agreement is the honest confidence signal.
    dasha_html = personality_html = ""
    try:
        import report_confluence as CF
        dc = CF.dasha_confluence(pc, today)
        rows = "".join(
            f'<div class="dsys"><span>{_e(r["system"])}</span>'
            f'<b>{_e(r["label"])}</b></div>' for r in dc["readings"])
        n_read = len(dc.get("readings") or [])
        n_word = {2: "two", 3: "three", 4: "four"}.get(n_read, str(n_read) or "these")

        def _dir_of(r: dict) -> str:
            t = float(r.get("tone") or 0)
            if t > 0.2:
                return "up"
            if t < -0.2:
                return "down"
            return "mixed"

        n_same = sum(1 for r in (dc.get("readings") or [])
                     if _dir_of(r) == dc.get("direction"))
        direction = dc.get("direction", "mixed")

        # One coherent agreement statement from actual counts — never both
        # "strong/all agree" and "3 of 4 mixed" at once.
        # Use words for "all four..."; digits for "3 of 4...".
        if n_read > 0 and n_same == n_read:
            if direction == "up":
                conf = "Strong agreement"
                verdict = (f"all {n_word} timing methods point in the same "
                           f"supportive direction.")
            elif direction == "down":
                conf = "Strong agreement"
                verdict = (f"all {n_word} timing methods point toward a more "
                           f"demanding period.")
            else:
                conf = "Mixed agreement"
                verdict = (f"all {n_word} timing methods are active, but the "
                           f"overall picture stays mixed.")
        elif n_read >= 3 and n_same == n_read - 1:
            if direction == "up":
                conf = "Good agreement"
                verdict = (f"{n_same} of {n_read} timing methods point toward a "
                           f"supportive period, with one method adding caution.")
            elif direction == "down":
                conf = "Mixed agreement"
                verdict = (f"{n_same} of {n_read} timing methods point toward a "
                           f"more demanding period, while one adds a note of caution.")
            else:
                conf = "Mixed agreement"
                verdict = (f"{n_same} of {n_read} timing methods point in the same "
                           f"direction, while one adds a note of caution.")
        else:
            conf = "Mixed evidence"
            verdict = ("the timing methods do not point consistently in the "
                       "same direction.")

        dasha_html = (f'<div class="dasha-conf">{rows}'
                      f'<div class="dagree">{_e(conf)} — {_e(verdict)}</div>'
                      f'</div>')

        pers = CF.personality(pc)
        traits = "".join(f"<li>{_e(t)}</li>" for t in pers["traits"])
        yogas = "".join(f"<li>{_e(y)}</li>" for y in pers["yogas"])
        personality_html = f"""
<h3 class="sec">Who your chart says you are</h3>
<p class="sec-note">Read this first. If this feels familiar, the detailed timing ahead will
make much more sense.</p>
<div class="card persona">
  <ul class="traits">{traits}</ul>
  {f'<div class="yogas"><span class="ev-label">Standing combinations in your chart</span><ul>{yogas}</ul></div>' if yogas else ''}
</div>"""
    except Exception:
        pass

    def card_html(c: Card) -> str:
        if paid:
            agree = (f'<span class="agree">{_e(c.agreement)}</span>'
                     if c.agreement else "")
        else:
            label = free_confidence_label(c.agreement, c.direction)
            agree = f'<span class="agree">{_e(label)}</span>'
        why_line = c.backing or (c.evidence[0] if c.evidence else "")
        expect = EXPECT_LABEL.get(c.direction, "Mixed")

        try:
            from report_language import (
                trajectory_explain, expect_explain, chapter_area_line)
            from interpretation.life_stage import age_band as _age_band_fn
        except Exception:  # noqa: BLE001
            def trajectory_explain(d, area="", *, planet="", variant=0, age_band=""):  # type: ignore
                return ""

            def expect_explain(d, area="", *, age_band=""):  # type: ignore
                return ""

            def chapter_area_line(area="", *, age_band="adult"):  # type: ignore
                return ""

            def _age_band_fn(pc, today=None):  # type: ignore
                return "adult"

        act_label = ("What helps" if c.direction != "up"
                     else "How to use this period")
        card_band = _age_band_fn(pc, today=today)
        try:
            from narration.stage_actions import expect_for_stage
            expect_note = expect_for_stage(c.area, card_band, c.direction)
        except Exception:  # noqa: BLE001
            expect_note = ""
        if not expect_note:
            expect_note = expect_explain(c.direction, c.area, age_band=card_band)
        ch_line = chapter_area_line(c.area, age_band=card_band)

        if paid:
            lords = " · ".join(
                p for p in (md.get("md_lord", ""), ad.get("ad_lord", "")) if p)
            # Global chapter dates live in the now-box above. Cards only
            # explain how that same chapter touches this life area.
            phase = ""
            if ch_line:
                phase = (
                    f'<div class="when"><span class="ev-label">'
                    f'How this chapter affects this area</span>'
                    f'<p class="chapter-area-note">{_e(ch_line)}</p></div>')
            elif lords:
                phase = (
                    f'<div class="when"><span class="ev-label">'
                    f'How this chapter affects this area</span>'
                    f'{_e(lords)}</div>')
            planet_html = ""
            if c.planets:
                chips = " · ".join(_e(p) for p in c.planets)
                planet_html = (
                    '<div class="card-planets"><span class="ev-label">Planets involved</span>'
                    f'<div class="planet-names">{chips}</div></div>')

            trajectory_html = ""
            if c.trajectory:
                rows = []
                used_lines: set[str] = set()
                for i, tr in enumerate(c.trajectory):
                    a = _d(tr.get("start")); b = _d(tr.get("end"))
                    if not a or not b:
                        continue
                    if a.year == b.year and a.month == b.month:
                        ds = f"{a.day}–{b.day} {a:%b %Y}"
                    elif a.year == b.year:
                        ds = f"{a.day} {a:%b} – {b.day} {b:%b %Y}"
                    else:
                        ds = f"{a:%d %b %Y} – {b:%d %b %Y}"
                    explain = ""
                    for bump in range(6):
                        try:
                            from interpretation.evidence_builder import build_evidence
                            from interpretation.life_stage import age_band_at
                            from interpretation.prediction_meaning import build_meaning
                            from narration.human_renderer import render_future_headline
                            import report_confluence as CF

                            win_start = a
                            band = age_band_at(pc, win_start)
                            dasha = CF.dasha_confluence(pc, win_start)
                            row = {
                                "planet": tr.get("planet") or "",
                                "house": c.house,
                                "start": win_start,
                                "end": b,
                                "promise": tr.get("direction", "mixed"),
                                "bav": 5,
                            }
                            evidence = build_evidence(
                                pc, area=c.area, house=c.house,
                                direction=tr.get("direction", "mixed"),
                                row=row, dasha=dasha, age_band=band,
                                period_start=win_start, period_end=b)
                            meaning = build_meaning(evidence)
                            meaning.variant_index = i + bump
                            candidate = render_future_headline(meaning)
                        except Exception:  # noqa: BLE001
                            win_band = ""
                            try:
                                from interpretation.life_stage import age_band_at
                                win_band = age_band_at(pc, a)
                            except Exception:  # noqa: BLE001
                                win_band = card_band
                            candidate = trajectory_explain(
                                tr.get("direction", "mixed"), c.area,
                                planet=tr.get("planet") or "",
                                variant=i + bump, age_band=win_band)
                        if candidate and candidate not in used_lines:
                            explain = candidate
                            break
                    if not explain:
                        try:
                            from interpretation.life_stage import age_band_at
                            win_band = age_band_at(pc, a)
                        except Exception:  # noqa: BLE001
                            win_band = card_band
                        explain = trajectory_explain(
                            tr.get("direction", "mixed"), c.area,
                            planet=tr.get("planet") or "", variant=i,
                            age_band=win_band)
                    used_lines.add(explain)
                    rows.append(
                        f'<div class="trajectory-row">'
                        f'<div class="traj-when">{_e(ds)}</div>'
                        f'<b class="traj-{tr["direction"]}">{_e(EXPECT_LABEL.get(tr["direction"], "Mixed"))}</b>'
                        f'<p class="traj-note">{_e(explain)}</p>'
                        f'<small>Influence: {_e(tr.get("planet") or "timing")}</small></div>')
                if rows:
                    trajectory_html = (
                        '<div class="trajectory">'
                        '<span class="ev-label">How this area changes over time</span>'
                        + ''.join(rows) + '</div>')

            act = (f'<div class="action"><span class="act-label">{act_label}</span>'
                   f'<p>{_e(c.action)}</p>'
                   + (f'<p class="mantra">{_e(c.mantra)}</p>' if c.mantra else "")
                   + "</div>") if c.action else ""
            try:
                from report_language import why_block_html
                why_body = why_block_html(why_line, "")
            except Exception:  # noqa: BLE001
                why_body = f'<p class="pred-why">{_e(why_line)}</p>'
            why = (
                f'<details class="evidence-astro"><summary>Why does Graharekha say this?</summary>'
                f'{why_body}</details>')
            body = (
                f'<div class="expect"><span class="ev-label">What to expect</span>'
                f'<b class="traj-{c.direction}">{_e(expect)}</b>'
                + (f'<p class="expect-note">{_e(expect_note)}</p>'
                   if expect_note else "")
                + f'</div>{phase}{planet_html}{trajectory_html}{act}{why}')
        else:
            phase = ('<div class="when locked-inline">'
                     '<span class="lockicon">•</span> Exact dates in the full reading</div>')
            act = ('<div class="action locked-inline">'
                   f'<span class="act-label">{act_label}</span>'
                   '<p class="blurred">{}</p></div>'.format(_e(c.action))
                   ) if c.action else ""
            body = (
                f'<div class="expect"><span class="ev-label">What to expect</span>'
                f'<b class="traj-{c.direction}">{_e(expect)}</b>'
                + (f'<p class="expect-note">{_e(expect_note)}</p>'
                   if expect_note else "")
                + f'</div>{phase}'
                f'<div class="evidence"><span class="ev-label">Why this reads this way</span>'
                f'{agree}<p class="pred-why locked-inline"><span class="lockicon">•</span> '
                f'The full report shows the planets, timing and chart factors '
                f'behind this reading.</p></div>'
                f'{act}')

        return f"""
<article class="card" data-verdict="{c.direction}">
  <div class="card-top"><span class="area">{_e(c.label)}</span>
    <span class="pill {c.direction}">{DIRECTION_LABEL[c.direction]}</span></div>
  <div class="ev-label">Current situation</div>
  <p class="claim">{_e(c.headline)}</p>
  {body}
</article>"""

    tl = "".join(f"""
<li class="{'now' if r['current'] else ''}">
  <div class="tl-when">{_e(r['window'])}</div>
  <div class="tl-body"><b>{_e(r['theme'])}</b>
  <span class="tl-period">{_e(r['lord'])} period</span>
  {f'<span class="tl-areas">{_e(" · ".join(r["areas"]))}</span>' if r['areas'] else ''}</div>
</li>""" for r in timeline)

    cards_html = "".join(card_html(c) for c in cards)

    def _chapter_planet_block(*lords: str) -> str:
        try:
            from report_language import planet_influence_line
        except Exception:  # noqa: BLE001
            def planet_influence_line(p):  # type: ignore
                return f"{p} is active in this period."
        seen: list[str] = []
        for p in lords:
            if p and p not in seen:
                seen.append(p)
        if not seen:
            return ""
        rows = "".join(
            f'<div class="planet-theme"><b>{_e(p)}</b>'
            f'<p>{_e(planet_influence_line(p))}</p></div>'
            for p in seen)
        return f'<div class="chapter-planets">{rows}</div>'

    md_l = md.get("md_lord", "")
    ad_l = ad.get("ad_lord", "")
    if paid:
        start_src = _d(ad.get("start")) or _d(md.get("start"))
        end_src = _d(ad.get("end")) or _d(md.get("end"))
        start_p = _pretty_long(start_src)
        end_p = _pretty_long(end_src)
        try:
            import impact as IMP
            chapter_impact = IMP.period_impact(
                md_l, ad_l, end_pretty=end_p or _pretty(end_src))
        except Exception:  # noqa: BLE001
            chapter_impact = (
                f"You are in a {md_l}–{ad_l} period. Opportunities and effort "
                f"both matter here; the best results usually come through steady "
                f"action and the right support"
                + (f" until {end_p}." if end_p else "."))
        try:
            from report_language import humanise_client_language
            chapter_impact = humanise_client_language(chapter_impact)
        except Exception:  # noqa: BLE001
            pass
        if start_p and end_p:
            chapter_h2 = (f"{_e(md_l)}–{_e(ad_l)}<br/>"
                          f"{_e(start_p)} → {_e(end_p)}")
        elif end_p:
            chapter_h2 = f"{_e(md_l)}–{_e(ad_l)}, to {_e(end_p)}"
        else:
            chapter_h2 = f"{_e(md_l)}–{_e(ad_l)}"
        chapter_planets = _chapter_planet_block(md_l, ad_l)
        chapter_dasha = dasha_html
    else:
        chapter_h2 = f"{_e(md_l)}–{_e(ad_l)}"
        try:
            import impact as IMP
            chapter_impact = IMP.period_impact(md_l, ad_l, end_pretty="")
        except Exception:  # noqa: BLE001
            chapter_impact = (
                f"You are in a {md_l}–{ad_l} period. This combination is "
                f"shaping the background of daily life right now.")
        try:
            from report_language import humanise_client_language
            chapter_impact = humanise_client_language(chapter_impact)
        except Exception:  # noqa: BLE001
            pass
        chapter_planets = _chapter_planet_block(md_l, ad_l)
        chapter_dasha = ""

    timeline_section = ""
    if paid:
        timeline_section = f"""
<h3 class="sec">The full period sequence</h3>
<p class="sec-note">Your own timing sequence, with real dates.</p>
<ol class="timeline">{tl}</ol>"""

    buy_block = ""
    if not paid:
        buy_block = f"""
<div class="buy">
  <h3>Unlock the full reading</h3>
  <p>Why every headline above reads the way it does, the dated window for
  each, the five-year windows, the period sequence and your gemstones.</p>
  <a class="cta" href="#unlock" data-unlock="1">Unlock full reading</a>
</div>"""

    period_strip_html = ""
    try:
        from period_planet_status import render_period_strip
        period_strip_html = render_period_strip(pc, paid=paid, today=today)
    except Exception:  # noqa: BLE001
        period_strip_html = ""

    d1_chart_html = ""
    try:
        from north_indian_chart import svg_d1
        d1_chart_html = svg_d1(pc)
    except Exception:  # noqa: BLE001
        d1_chart_html = ""

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{_e(first)} — your reading</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet"/>
<style>{_STYLE}{_EXTRA}</style></head><body><div class="wrap">
<header>
  <div class="eyebrow">Your reading</div>
  <h1>{_e(first)}, here is what your chart<br/>is doing right now.</h1>
  <div class="chartline">{_e(lagna)} rising · Moon in {_e(moon.get('sign',''))}
  ({_e(moon.get('nakshatra',''))}) · read {today:%d %B %Y}</div>
</header>

{period_strip_html}
{d1_chart_html}

<div class="now-box">
  <div class="lbl">The chapter you are in</div>
  <h2>{chapter_h2}</h2>
  <p>{_e(chapter_impact)}</p>
  {chapter_planets}
  {chapter_dasha}
</div>

{personality_html}

{proof_html}
{daily_html}
<h3 class="sec">What this period is doing to each part of your life</h3>
<p class="sec-note">Ordered by how strongly your chart speaks, not by convention.</p>
{cards_html}

{timing_html}

{timeline_section}

{question_html}

{buy_block}
<footer>Calculated from your birth details alone · guidance, not a substitute
for professional advice</footer>
</div>{_INTERACT}</body></html>"""
