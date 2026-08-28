"""Answering "when will X happen?" from the birth chart.

This is the highest-value question the product gets asked, and it is a
different problem from horary. Horary reads the moment of asking and returns
yes or no. A natal timing question has to return a **date range**, which means
it needs everything at once:

    the promise    does the chart offer this at all, and how strongly
    the period     which dasha owns it — checked in all three systems
    the trigger    is a slow planet crossing the relevant house
    the strength   does that transit carry the Ashtakavarga points to deliver

The discipline that matters here is refusing to answer when the chart does not
support one. "Sometime in the next ten years" is not an answer, and inventing a
date to seem confident is how this category earned its reputation. So a window
is only offered when promise, period and trigger coincide; otherwise the reader
is told plainly that the chart shows no clear window in the horizon, and what
that actually means.

Question → chart mapping is explicit rather than clever. A job change is not
just the 10th house: leaving is the 3rd and 12th, arriving is the 10th and 11th,
and the work itself is the 6th. Reading only the 10th is the usual mistake.
"""

from __future__ import annotations

import html as _html
import re
from datetime import date, timedelta
from typing import Any, Optional


class Topic:
    """One kind of question, and the parts of the chart that answer it."""

    def __init__(self, key: str, label: str, subject: str, houses: tuple,
                 significators: tuple, patterns: tuple, note: str = ""):
        self.key = key
        self.label = label
        self.subject = subject
        self.houses = houses            # (primary, *supporting)
        self.significators = significators
        self.patterns = patterns
        self.note = note


TOPICS = (
    Topic("career", "Career growth and direction", "your career improving",
          houses=(10, 11, 6),
          significators=("Sun", "Saturn", "Jupiter"),
          patterns=(r"\bcareer\b", r"\bprofessional\b", r"\bwork\b.*\b(improv|grow|progress|better)\b",
                    r"\bcareer\b.*\b(improv|grow|progress|better|future)\b"),
          note="The reading focuses on professional growth, responsibility, recognition and direction rather than assuming a specific job change."),
    Topic("job_change", "A change of job", "a job change",
          houses=(10, 6, 3, 11),
          significators=("Saturn", "Sun", "Mercury"),
          patterns=(r"\bjob\b.*\bchange\b", r"\bchange\b.*\bjob\b",
                    r"\bnew job\b", r"\bswitch\b.*\b(job|company|role)\b",
                    r"\bresign", r"\bquit\b.*\bjob\b", r"\bnaukri\b"),
          note="Leaving is read from the 3rd and 12th, arriving from the 10th "
               "and 11th, and the work itself from the 6th. A change needs "
               "movement in both halves, not just a strong 10th."),
    Topic("promotion", "Promotion or a step up", "a promotion",
          houses=(10, 11, 1),
          significators=("Sun", "Jupiter", "Saturn"),
          patterns=(r"\bpromot", r"\bsenior", r"\braise\b", r"\bincrement\b")),
    Topic("business", "Starting on your own", "starting your own work",
          houses=(7, 10, 11),
          significators=("Mercury", "Rahu", "Jupiter"),
          patterns=(r"\bbusiness\b", r"\bstartup\b", r"\bown\b.*\bwork\b",
                    r"\bventure\b")),
    Topic("money", "A real rise in income", "a rise in income",
          houses=(2, 11, 9),
          significators=("Jupiter", "Venus", "Mercury"),
          patterns=(r"\bmoney\b", r"\bincome\b", r"\bsalary\b", r"\bwealth\b",
                    r"\brich\b", r"\bfinancial", r"\bpaisa\b")),
    Topic("property", "Property or a home", "buying property",
          houses=(4, 2, 11),
          significators=("Mars", "Venus", "Saturn"),
          # Never match bare "house" — "5th house" / "house of children" must
          # not be stolen into the 4th. Require property context.
          patterns=(r"\bproperty\b", r"\bflat\b", r"\bland\b", r"\bhome loan\b",
                    r"\breal\s*estate\b", r"\bapartment\b",
                    r"\b(buy|buying|bought|own|owning|sell|selling)\b.{0,24}\b"
                    r"(house|home|flat|plot)\b",
                    r"\b(house|home|flat|plot)\b.{0,24}\b"
                    r"(buy|buying|bought|loan|emi|mortgage)\b",
                    r"\b(my|a|new|own)\s+house\b", r"\b(my|a|new)\s+home\b")),
    Topic("foreign", "Going abroad", "a move abroad",
          houses=(12, 9, 3),
          significators=("Rahu", "Moon", "Jupiter"),
          patterns=(r"\babroad\b", r"\bforeign\b", r"\bvisa\b", r"\bonsite\b",
                    r"\brelocat", r"\bsettle\b.*\b(us|uk|canada|australia)\b")),
    Topic("study", "Study or a qualification", "further study",
          houses=(9, 5, 4),
          significators=("Jupiter", "Mercury"),
          patterns=(r"\bstudy\b", r"\bexam\b", r"\bmba\b", r"\bcourse\b",
                    r"\bdegree\b", r"\badmission\b")),
    Topic("health", "Health recovery", "your health improving",
          houses=(1, 6, 8),
          significators=("Sun", "Jupiter", "Mars"),
          patterns=(r"\bhealth\b", r"\billness\b", r"\brecover", r"\bsurgery\b",
                    r"\bdisease\b")),
    Topic("children", "Children & family", "children",
          houses=(5, 9, 11),
          significators=("Jupiter",),
          patterns=(r"\bkids?\b", r"\bchild", r"\bchildren\b", r"\bprogeny\b",
                    r"\bson\b", r"\bdaughter\b", r"\bbaby\b", r"\bpregnant\b",
                    r"\bhow many\b.*\b(kids?|child)")),
    Topic("marriage", "Marriage or a relationship", "your marriage or relationship",
          houses=(7, 2, 11),
          significators=("Venus", "Jupiter", "Mars"),
          patterns=(r"\bmarry\b", r"\bmarriage\b", r"\bwedding\b", r"\bhusband\b",
                    r"\bwife\b", r"\bspouse\b", r"\bfianc", r"\bpartner\b",
                    r"\brelationship\b", r"\bgirlfriend\b", r"\bboyfriend\b",
                    r"\bengagement\b", r"\bdivorce\b", r"\bbreak ?up\b")),
    Topic("legal", "A legal matter or dispute", "your legal matter",
          houses=(6, 9, 12),
          significators=("Mars", "Saturn", "Mercury"),
          patterns=(r"\bcourt\b", r"\blawsuit\b", r"\blegal\b", r"\bcase\b",
                    r"\bdispute\b", r"\blitigation\b", r"\bbail\b")),
    Topic("gemstone", "Gemstone and remedies", "your gemstone and remedies",
          houses=(1, 9, 5),
          significators=("Jupiter", "Sun", "Venus"),
          patterns=(r"\bgemstone\b", r"\bgemstones\b", r"\bratt?na\b", r"\brashi ratna\b",
                    r"\bremedy\b", r"\bremedies\b", r"\bupay\b",
                    r"\bupayam\b", r"\bmantra\b", r"\brudraksha\b", r"\bpanna\b",
                    r"\bmanik\b", r"\bmoti\b", r"\bmoonga\b", r"\bpukhraj\b",
                    r"\bheera\b", r"\bneelam\b", r"\bgomed\b", r"\bcat'?s eye\b",
                    r"\blahsuniya\b"),
          note="Gemstone and remedial guidance based on your chart's benefic lords and sensitive houses."),
)

FALLBACK = Topic("general", "Your question", "what you asked about",
                 houses=(1, 10, 11), significators=("Jupiter", "Saturn"),
                 patterns=())

# Someone who names a house directly ("my 5th house", "house number 5",
# "fifth house") is telling us exactly which chart to read. Trusting that
# over keyword guesses is what stops "how is my 5th house" from being
# hijacked by the property topic's bare "house" keyword and answered as a
# 4th-house (property) question instead.
_WORD_HOUSE_NUM = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
    "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11,
    "twelfth": 12,
}
_HOUSE_RE = re.compile(
    r"\b(\d{1,2})\s*(?:st|nd|rd|th)?\s*house\b"
    r"|\bhouse\s*(?:no\.?|number|#)?\s*(\d{1,2})\b"
    r"|\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|"
    r"tenth|eleventh|twelfth)\s+house\b", re.I)

_HOUSE_LABEL = {
    1: "Self and vitality", 2: "Wealth and family",
    3: "Courage and effort", 4: "Home and inner peace",
    5: "Children, creativity and intelligence",
    6: "Health, debts and daily struggle", 7: "Marriage and partnership",
    8: "Transformation and longevity", 9: "Luck, dharma and higher learning",
    10: "Career and public standing", 11: "Gains and larger networks",
    12: "Loss, foreign lands and release",
}
_HOUSE_SUBJECT = {
    1: "your health and vitality", 2: "your wealth and family",
    3: "your courage and effort", 4: "your home and inner peace",
    5: "your children, creativity and intelligence",
    6: "your health, debts and daily struggle",
    7: "your marriage and partnerships", 8: "transformation and longevity",
    9: "your luck, dharma and higher learning",
    10: "your career and public standing", 11: "your gains and networks",
    12: "loss, foreign lands and release",
}
_HOUSE_KARAKA = {
    1: ("Sun",), 2: ("Jupiter", "Mercury"), 3: ("Mars", "Mercury"),
    4: ("Moon", "Mars", "Venus"), 5: ("Jupiter",), 6: ("Mars", "Saturn"),
    7: ("Venus",), 8: ("Saturn",), 9: ("Jupiter", "Sun"),
    10: ("Sun", "Mercury", "Saturn"), 11: ("Jupiter",), 12: ("Saturn", "Ketu"),
}


def _house_from_text(q: str) -> Optional[int]:
    m = _HOUSE_RE.search(q)
    if not m:
        return None
    if m.group(1):
        n = int(m.group(1))
    elif m.group(2):
        n = int(m.group(2))
    else:
        n = _WORD_HOUSE_NUM.get((m.group(3) or "").lower())
    return n if n and 1 <= n <= 12 else None


def _topic_for_house(house: int) -> Topic:
    """A named house wins outright — reuse a matching Topic if one exists
    (so "5th house" still gets the children topic's dasha/significator
    logic), otherwise build one from classical significations."""
    for t in TOPICS:
        if t.houses and t.houses[0] == house:
            return t
    return Topic(
        f"house{house}", f"Your {_ord(house)} house — {_HOUSE_LABEL.get(house, '')}",
        _HOUSE_SUBJECT.get(house, f"your {_ord(house)} house"),
        houses=(house,), significators=_HOUSE_KARAKA.get(house, ()),
        patterns=())


def _topic_by_key(key: str) -> Optional[Topic]:
    for t in TOPICS:
        if t.key == key:
            return t
    return None


# When the reader picks an area, only let free-text refine *within* that area
# (career + "promotion" → promotion). Never let an unrelated keyword steal
# the read (children area + bare "house" must not become property).
_AREA_COMPAT: dict[str, frozenset[str]] = {
    "career": frozenset({"career", "job_change", "promotion", "business"}),
    "promotion": frozenset({"promotion", "job_change"}),
    "business": frozenset({"business", "job_change"}),
    "finance": frozenset({"money"}),
    "property": frozenset({"property"}),
    "marriage": frozenset({"marriage"}),
    "children": frozenset({"children"}),
    "education": frozenset({"study"}),
    "health": frozenset({"health"}),
    "travel": frozenset({"foreign"}),
    "legal": frozenset({"legal"}),
}


def classify(question: str, area: str = "") -> Topic:
    """Map free-text (+ optional life-area dropdown) → Topic.

    Order: explicit house number → wording refined inside the chosen area →
    the area itself → wording with no area → semantic guess.
    """
    raw = (question or "").strip()
    q = re.sub(r"\s+", " ", raw.lower())
    house_n = _house_from_text(q)
    if house_n:
        return _topic_for_house(house_n)

    try:
        import semantic_question as SQ
        area = SQ.normalize_area(area)
    except Exception:  # noqa: BLE001
        area = (area or "").strip().lower()

    if area:
        allowed = _AREA_COMPAT.get(area)
        if allowed:
            for topic in TOPICS:
                if topic.key not in allowed:
                    continue
                for pat in topic.patterns:
                    if re.search(pat, q):
                        return topic
        try:
            import semantic_question as SQ
            t = _topic_by_key(SQ.AREA_TO_QA_TOPIC.get(area, ""))
            if t:
                return t
            house = SQ.AREA_TO_HOUSE.get(area)
            if house:
                return _topic_for_house(house)
        except Exception:  # noqa: BLE001
            pass

    for topic in TOPICS:
        for pat in topic.patterns:
            if re.search(pat, q):
                return topic

    try:
        import semantic_question as SQ
        routed = SQ.route(raw, area=area)
        dom = routed.domain
        house = routed.primary_house
        by_house = [t for t in TOPICS if t.houses and t.houses[0] == house]
        if by_house:
            return by_house[0]
        key = {
            "career": "career", "finance": "money", "property": "property",
            "travel": "foreign", "health": "health", "education": "study",
            "children": "children", "family": "children",
            "marriage": "marriage", "legal": "legal",
        }.get(dom)
        t = _topic_by_key(key) if key else None
        if t:
            return t
    except Exception:
        pass
    return FALLBACK


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def _pretty(d: Optional[date]) -> str:
    return f"{d:%B %Y}" if d else ""


def _ord(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    return f"{n}" + ("th" if 10 <= n % 100 <= 20
                     else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


_DIGNITY = {
    "exalted": "very strong",
    "moolatrikona": "very strong",
    "own_sign": "in its own sign",
    "friendly_sign": "comfortable",
    "neutral_sign": "neither strong nor weak",
    "enemy_sign": "under strain",
    "debilitated": "very weak",
    "neutral": "neither strong nor weak",
}

_ROUTE_METHOD = {
    "minilm": "your wording",
    "semantic": "your wording",
    "regex": "the question pattern",
}


def _human_dignity(code: str) -> str:
    key = (code or "").strip().lower().replace(" ", "_")
    return _DIGNITY.get(key, key.replace("_", " ") if key else "mixed")


def _plain_line(text: str) -> str:
    """Customer-facing one-liner — no method tags or book citations."""
    raw = (text or "").strip()
    if not raw:
        return ""
    for code, human in _DIGNITY.items():
        raw = re.sub(rf"\b{re.escape(code)}\b", human, raw, flags=re.I)
    try:
        import report_confluence as CF
        return CF._plain(raw)  # noqa: SLF001
    except Exception:  # noqa: BLE001
        return raw


_INTENT_RE = {
    "amount": re.compile(r"\bhow\s+(much|many)\b", re.I),
    "when": re.compile(r"\bwhen\b|\bhow\s+long\b|\btiming\b|"
                        r"\bwhich\s+(year|month)\b", re.I),
    "yesno": re.compile(r"\b(will|can|shall|should|is\s+it\s+possible|"
                         r"going\s+to)\b", re.I),
    "how": re.compile(r"^\s*how\b|\bhow\s+is\b|\bhow\s+does\b|\bhow\s+about\b|"
                       r"\btell\s+me\s+about\b|\bdescribe\b|\banalys|\bwhat\s+about\b|"
                       r"\bwhat\s+does\b|\bhow\s+will\b", re.I),
}


def _intent(question: str) -> str:
    """"When will X" wants a yes/no-shaped answer with a date. "How is my
    5th house" wants an explanation — forcing it through the yes/no template
    ("Does your chart even offer this?") reads as a non sequitur."""
    q = (question or "").strip()
    if _INTENT_RE["amount"].search(q):
        return "amount"
    if _INTENT_RE["when"].search(q):
        return "when"
    if _INTENT_RE["how"].search(q):
        return "how"
    if _INTENT_RE["yesno"].search(q):
        return "yesno"
    return "general"


def _plain_agreement(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return "the methods have not settled on one side yet"
    low = raw.lower()
    if "align · moderate" in low or "align · mod" in low:
        return raw.split("·")[0].strip() + " — a moderate read, not unanimous"
    if "align · high" in low:
        return raw.split("·")[0].strip() + " — a strong agreement"
    if "align · low" in low:
        return raw.split("·")[0].strip() + " — most methods push back"
    return _plain_line(raw)


# ---------------------------------------------------------------------------

# The question tab is a consumer of the full-report confluence, not a second
# astrology engine. These are the full-report life areas available for lookup.
_CANONICAL_AREA_HOUSES = {
    "career": 10,
    "money": 2,
    "love": 7,
    "home": 4,
    "children": 5,
    "health": 1,
    "learning": 9,
    "inner": 12,
}


def _canonical_area_for_topic(topic_key: str, area_key: str = "") -> tuple[str, int]:
    explicit = (area_key or "").strip().lower()
    if explicit in _CANONICAL_AREA_HOUSES:
        return explicit, _CANONICAL_AREA_HOUSES[explicit]
    topic_area = {
        "career": "career",
        "job_change": "career",
        "promotion": "career",
        "business": "career",
        "money": "money",
        "property": "home",
        "foreign": "inner",
        "study": "learning",
        "health": "health",
        "children": "children",
        "marriage": "love",
    }.get(topic_key, "")
    if topic_area:
        return topic_area, _CANONICAL_AREA_HOUSES[topic_area]
    return "", 0


def _build_canonical_question_result(
    pc: dict,
    *,
    topic_key: str,
    area_key: str,
    today: date,
) -> Optional[dict]:
    """Fetch the same CanonicalAreaResult used by full-report cards.

    No question-specific confluence score is allowed to overwrite this object.
    """
    canonical_area, house = _canonical_area_for_topic(topic_key, area_key)
    if not canonical_area or not house:
        return None
    try:
        from canonical_result import build_area_result
        return build_area_result(pc, canonical_area, house, today=today)
    except Exception as exc:  # noqa: BLE001
        print(f"[question_answer] canonical lookup failed: {exc}", flush=True)
        return None


def _question_windows_from_canonical(canonical: dict, start: date, years: int = 7) -> list[dict]:
    timing = canonical.get("timing") or {}
    # Do not let an out-of-horizon strong window suppress a validated or
    # opportunity window that actually falls inside the user's requested period.
    rows: list[dict] = []
    seen: set[tuple] = set()
    for bucket in ("featured_windows", "strong_windows", "validated_windows", "opportunity_windows", "windows"):
        for w in list(timing.get(bucket) or []):
            if not isinstance(w, dict):
                continue
            key = (str(w.get("start") or ""), str(w.get("end") or ""), str(w.get("event_type") or ""))
            if key not in seen:
                seen.add(key)
                rows.append(w)
    out: list[dict] = []
    for w in rows:
        if not isinstance(w, dict) or not w.get("start"):
            continue
        try:
            if w["start"] < start:
                continue
            try:
                cutoff = start.replace(year=start.year + years)
            except ValueError:
                cutoff = start.replace(month=2, day=28, year=start.year + years)
            if w["start"] > cutoff:
                continue
        except TypeError:
            pass
        promise_status = str(
            w.get("promise_status")
            or (canonical.get("promise") or {}).get("status")
            or "insufficient_evidence"
        )
        strong = bool(
            w.get("aligned")
            and promise_status in ("strongly_supported", "supported")
            and w.get("confidence") in ("high", "very high")
        )
        out.append({
            **w,
            "strong": strong,
            "period_hits": ["validated_confluence"] if w.get("period_owns_area") else [],
            "dasha_dir": w.get("dasha", "mixed"),
            "period": w.get("dasha_label", ""),
        })
    out.sort(key=lambda x: (-float(x.get("score") or 0), x.get("start")))
    return out



# ---------------------------------------------------------------------------

def _requested_horizon_years(question: str, default: int = 7) -> int:
    """Read an explicit user horizon such as 'next 2 years'."""
    q = re.sub(r"\s+", " ", (question or "").lower())
    m = re.search(r"(?:next|coming|within)\s+(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\s+years?", q)
    if m:
        raw = m.group(1)
        words = {"one":1, "two":2, "three":3, "four":4, "five":5,
                 "six":6, "seven":7, "eight":8, "nine":9, "ten":10}
        return max(1, min(10, int(raw) if raw.isdigit() else words[raw]))
    if re.search(r"(?:next|coming|within)\s+(?:one|a)\s+year", q):
        return 1
    return max(1, min(10, int(default or 7)))


def answer(pc: dict, question: str, *, start: Optional[date] = None,
           years: int = 7, lat: Optional[float] = None,
           lon: Optional[float] = None, tz: float = 5.5,
           route: Any = None, area: str = "") -> dict:
    """Find the windows where this specific thing can actually happen."""
    start = start or date.today()
    years = _requested_horizon_years(question, years)
    topic = classify(question, area=area)
    import report_confluence as CF
    import report_timing as RT

    primary = topic.houses[0]
    # Prefer the topic's life area over the primary-house default — otherwise
    # a legal question (6th house) is mis-tagged as "health" for deep evidence
    # and the remedy block.
    _TOPIC_AREA = {
        "job_change": "career", "promotion": "career", "business": "career",
        "money": "money", "property": "home", "foreign": "inner",
        "study": "learning", "health": "health", "children": "children",
        "marriage": "love", "legal": "legal",
    }
    area_key = _TOPIC_AREA.get(topic.key) or _area_for(primary)

    # IMPORTANT: for all life areas represented in the full report, the
    # question tab reads the exact same canonical confluence/promise/activation
    # result. The question router may refine wording, but it cannot create a
    # second promise or timing truth.
    canonical = _build_canonical_question_result(
        pc, topic_key=topic.key, area_key=area_key, today=start)
    if canonical:
        area_key = str(canonical.get("area") or area_key)
        promise = dict(canonical.get("promise") or {})
        activation = dict(canonical.get("activation") or {})
        windows = _question_windows_from_canonical(canonical, start, years=years)
    else:
        promise = CF.area_verdict(pc, area_key, primary)
        promise = CF.merge_semantic_verdict(area_key, promise)
        activation = {}
        windows = []

    deep: dict = {}
    if not canonical:
        try:
            import deep_evidence as DE
            deep = DE.for_area(area_key, house=primary)
        except Exception:  # noqa: BLE001
            deep = {}

    hl = pc.get("house_lords", {}) or {}
    planets = pc.get("planets", {}) or {}
    owners = {(hl.get(str(h)) or {}).get("lord") for h in topic.houses}
    owners.discard(None)
    keys = owners | set(topic.significators)

    if not canonical:
        segments = RT.transit_segments(pc, start=start, years=years)
        for planet, segs in segments.items():
            for seg in segs:
                if seg.get("house") not in topic.houses:
                    continue
                when = max(seg.get("start"), start)
                if when > start + timedelta(days=365 * years):
                    continue
                dasha = CF.dasha_confluence(pc, when)
                vim = CF.vimshottari_at(pc, when)
                yog = (CF.yogini_at(pc, when) or {}).get("lord", "")
                running = [x for x in (vim.get("md"), vim.get("ad"), yog) if x]
                period_hits = sorted({p for p in running if p in keys})
                bav = seg.get("bav", 0)
                score = (0.9 * len(period_hits)
                         + (1.2 if bav >= 5 else (-1.0 if bav <= 3 else 0))
                         + (0.8 if seg["house"] == primary else 0.3)
                         + 0.5 * promise["score"]
                         + (0.6 if dasha["direction"] == "up" else
                            -0.6 if dasha["direction"] == "down" else 0))
                windows.append({
                    "start": when, "end": seg.get("end"),
                    "planet": planet, "sign": seg.get("sign"), "house": seg["house"],
                    "bav": bav, "period": f"{vim.get('md','')}–{vim.get('ad','')}",
                    "yogini": yog, "period_hits": period_hits,
                    "dasha_dir": dasha["direction"],
                    "dasha_label": " · ".join(r["label"] for r in dasha["readings"]),
                    "score": round(score, 2),
                    "strong": bool(period_hits) and bav >= 5,
                })
        windows.sort(key=lambda w: -w["score"])
    best = windows[0] if windows else None

    # Someone asking "when" wants two different things and the strongest
    # window answers only one of them. On the test chart the best window is
    # three and a half years out — true, and useless to a person who wants to
    # move this year. So the nearest usable window is reported alongside it,
    # and if they are the same window that is stated rather than duplicated.
    soon = sorted((w for w in windows if w["score"] > 0),
                  key=lambda w: w["start"])
    nearest = soon[0] if soon else None
    if nearest and best and nearest["start"] == best["start"]:
        nearest = None

    # Customer evidence comes from the canonical result whenever available.
    # Never expose raw house/rule/classical working merely because the question
    # engine calculated it for internal routing.
    chart_lines = []
    if canonical:
        why = canonical.get("why") or {}
        for text in list(why.get("supporting") or [])[:2]:
            chart_lines.append(("Support", str(text)[:220]))
        for text in list(why.get("caution") or [])[:1]:
            chart_lines.append(("Watch", str(text)[:220]))
    else:
        # Fail closed when a canonical area cannot be built. Do not expose the
        # legacy house-by-house/classical evidence path to the customer.
        direction = str(promise.get("direction") or "mixed")
        chart_lines = [
            ("Chart evidence",
             "The chart provides supportive evidence around this area." if direction in ("support", "up")
             else "The chart shows pressure around this area." if direction in ("caution", "down")
             else "The chart evidence is mixed around this area.")
        ]

    vim_now = CF.vimshottari_at(pc, start)
    yog_now = (CF.yogini_at(pc, start) or {}).get("lord", "")
    now_label = f"{vim_now.get('md','')}-{vim_now.get('ad','')}" + (
        f", lunar cycle on {yog_now}" if yog_now else "")

    strong = [w for w in windows if w.get("strong")]

    route_info: dict = {}
    if route is not None:
        route_info = {
            "domain": getattr(route, "domain", "") or "",
            "primary_house": getattr(route, "primary_house", 0) or 0,
            "topic": getattr(route, "topic", "") or "",
            "method": getattr(route, "method", "") or "",
        }
    else:
        try:
            import semantic_question as SQ
            r = SQ.route(question, area=area)
            route_info = {
                "domain": r.domain, "primary_house": r.primary_house,
                "topic": r.topic, "method": r.method,
            }
        except Exception:  # noqa: BLE001
            route_info = {}

    if canonical:
        why = canonical.get("why") or {}
        rows = list(why.get("rows") or [])
        n_methods = len(rows)
        n_up = int(why.get("support") or sum(1 for r in rows if r.get("direction") == "support"))
        n_down = int(why.get("caution_count") or sum(1 for r in rows if r.get("direction") == "caution"))
    else:
        votes = promise.get("votes") or []
        n_methods = len(votes)
        n_up = sum(1 for v in votes if getattr(v, "value", 0) > 0.3)
        n_down = sum(1 for v in votes if getattr(v, "value", 0) < -0.3)

    area_report = None
    if not canonical:
        try:
            import area_report as AR
            area_report = AR.build_area(
                pc, area_key, primary, today=start, question=question)
        except Exception:  # noqa: BLE001
            area_report = None

    prediction = None
    if canonical:
        # Canonical result is already the report's prediction truth. Never
        # calculate a second area prose path for the same question.
        area_report = None
    elif area_report:
        import predict_voice as PV
        prediction = PV.Prediction(
            scenario=area_report.prediction,
            backing=area_report.proof,
            direction=area_report.direction,
        )
    else:
        try:
            import predict_voice as PV
            now = CF.vimshottari_at(pc, start)
            hl_info = hl.get(str(primary)) or {}
            live = [w for w in windows if w["start"] <= start][:2]
            transits = [{"planet": w["planet"], "house": w["house"], "bav": w["bav"]}
                        for w in live]
            prediction = PV.compose(
                area_key, direction=promise.get("direction", "mixed"),
                md_lord=now.get("md", ""), ad_lord=now.get("ad", ""),
                house=primary, lord=hl_info.get("lord", ""),
                dignity=str(hl_info.get("lord_dignity") or ""),
                lord_house=hl_info.get("lord_house"), transits=transits,
                varga=deep.get("varga") or {},
                varga_strength=(deep.get("varga") or {}).get("strength", "mixed"),
                window_rating=deep.get("current_rating", "mix"),
                include_period_lord=False,
            )
        except Exception:  # noqa: BLE001
            prediction = None

    return {"topic": topic, "question": question, "promise": promise,
            "chart_lines": chart_lines, "now_label": now_label,
            "windows": windows, "best": best, "nearest": nearest,
            "strong_count": len(strong), "horizon": years,
            "start": start, "deep": deep,
            "deep_verdict": (deep.get("overall") or {}).get("text", ""),
            "route": route_info, "area_key": area_key, "area": area or "",
            "n_methods": n_methods, "n_up": n_up, "n_down": n_down,
            "prediction": prediction, "area_report": area_report,
            "activation": activation,
            "canonical_result": canonical,
            "truth_source": "full_report_canonical" if canonical else "question_specific_fallback"}


def _area_for(house: int) -> str:
    # House 6 is only a Topic's primary house for the legal topic today (health's
    # primary is 1), so repointing it away from "health" does not affect anything
    # else — it just stops a court-case question from getting sleep-and-energy prose.
    return {10: "career", 2: "money", 7: "love", 4: "home", 5: "children",
            1: "health", 9: "learning", 12: "inner", 6: "legal",
            3: "career", 11: "money", 8: "health"}.get(house, "career")


def answer_meta(result: dict) -> dict:
    """Compact verdict for JSON meta (frontend card when unlocked)."""
    promise = result.get("promise") or {}
    best = result.get("best")
    topic = result.get("topic")
    if not best:
        return {
            "label": f"No clear window for {getattr(topic, 'subject', 'this')} "
                     f"in the next {result.get('horizon', 7)} years",
            "confidence": "moderate",
            "direction": promise.get("direction", "mixed"),
        }
    lead = ("Yes — and the chart is specific about when."
            if best.get("strong") else
            "Yes, but the timing is narrower than you would like.")
    if promise.get("direction") == "down" and not best.get("strong"):
        lead = "Possible, but your chart does not strongly favour this."
    conf = promise.get("confidence", "moderate")
    if result.get("n_methods", 0) >= 5 and promise.get("direction") in ("up", "down"):
        conf = "high" if promise["direction"] == "up" else "low"
    return {"label": lead, "confidence": conf,
            "direction": promise.get("direction", "mixed"),
            "best_from": _pretty(best.get("start")),
            "best_to": _pretty(best.get("end"))}


# ---------------------------------------------------------------------------

def _human_question_evidence(result: dict) -> list[str]:
    """Return only canonical, customer-safe reasons for a question.

    When a full-report CanonicalAreaResult exists, the question tab must not
    expose the legacy deep-evidence/house-by-house path. That path remains an
    internal diagnostic only.
    """
    canonical = result.get("canonical_result") or {}
    if isinstance(canonical, dict) and canonical:
        why = canonical.get("why") or {}
        rows = list(why.get("rows") or [])
        out: list[str] = []
        for row in rows[:4]:
            if not isinstance(row, dict):
                continue
            reasons = row.get("reasons") or []
            reason = str(row.get("reason") or (reasons[0] if reasons else "")).strip()
            if not reason:
                continue
            try:
                from qa_checks.customer_text_sanitizer import sanitize_customer_text
                reason = sanitize_customer_text(
                    reason, area=str(canonical.get("area") or result.get("area_key") or ""),
                    direction=str(row.get("direction") or canonical.get("direction") or "mixed"),
                    method_label=str(row.get("label") or "Chart evidence"),
                    seed=reason[:48],
                )
            except Exception:  # noqa: BLE001
                pass
            if reason and reason not in out:
                out.append(reason)
        if out:
            return out[:3]
        direction = str(canonical.get("direction") or "mixed")
        area = str(canonical.get("area") or result.get("area_key") or "this area").replace("_", " ")
        if direction in ("support", "up"):
            return [f"The chart provides supportive evidence around {area}."]
        if direction in ("caution", "down"):
            return [f"The chart shows pressure around {area}."]
        return [f"The chart is mixed around {area}."]

    # No canonical area exists (for genuinely unsupported topics): retain the
    # question-specific semantic summary, but never expose raw house/rule text.
    promise = result.get("promise") or {}
    direction = str(promise.get("direction") or "mixed")
    area = str(result.get("area_key") or "this area").replace("_", " ")
    out = []
    if direction in ("up", "support"):
        out.append(f"The chart provides supportive evidence around {area}.")
    elif direction in ("down", "caution"):
        out.append(f"The chart shows pressure around {area}.")
    else:
        out.append(f"The chart is mixed around {area}.")
    # Unsupported questions fail closed. Never expose legacy deep verdict text.
    return out[:3]


def _topic_customer_note(topic_key: str) -> str:
    notes = {
        "job_change": "The reading considers both the conditions around your current work and the possibility of moving into a different role.",
        "promotion": "The reading focuses on professional growth, responsibility and recognition rather than assuming a promotion title.",
        "business": "The reading focuses on the chart's support for independent work, commercial activity and professional growth.",
        "money": "The reading focuses on income, financial stability and gains rather than treating one lucky event as guaranteed.",
        "property": "The reading focuses on home and property-related potential and the timing around it.",
        "foreign": "The reading focuses on movement, distance and opportunities connected with a different place.",
        "study": "The reading focuses on learning, qualifications, guidance and the ability to apply what you learn.",
        "health": "The reading focuses on wellbeing, routine and recovery rather than diagnosis.",
        "children": "The reading focuses on child- and family-related potential, adjusted to your life stage.",
        "marriage": "The reading focuses on relationships, partnership and commitment without assuming your current relationship status.",
        "legal": "The reading focuses on the practical direction of the matter and the periods that require more care.",
    }
    return notes.get(topic_key, "The reading focuses on the part of life most relevant to your question.")


TOPIC_TO_VARGA = {
    "career": "D10",
    "job_change": "D10",
    "promotion": "D10",
    "business": "D10",
    "money": "D2",
    "property": "D4",
    "foreign": "D9",
    "study": "D24",
    "health": "D30",
    "children": "D7",
    "marriage": "D9",
    "legal": "D30",
    "general": "D1",
}


def _build_static_promise_section(result: dict, pc: Optional[dict], *, paid: bool = True) -> str:
    if not isinstance(pc, dict):
        return ""
    try:
        from divisional_profile import build_divisional_insights
        topic = result.get("topic")
        topic_key = getattr(topic, "key", "general")
        v_code = TOPIC_TO_VARGA.get(topic_key, "D1")

        insights = {ins.code: ins for ins in build_divisional_insights(pc)}
        v_ins = insights.get(v_code) or insights.get("D1")
        if not v_ins:
            return ""

        pill_cls = "up" if v_ins.strength == "strong" else "down" if v_ins.strength == "weak" else "mixed"
        pill_lbl = "Well Supported" if v_ins.strength == "strong" else "Needs Care" if v_ins.strength == "weak" else "Mixed / Active"
        border_color = "#1c6b45" if v_ins.strength == "strong" else "#a3341f" if v_ins.strength == "weak" else "#8a6a1f"

        if not paid:
            return f"""
<section class="section static-promise" style="margin:20px 0;">
  <div style="font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:700;color:#7a4b18;margin-bottom:6px;">Static Promise &amp; Foundational Potential</div>
  <h2 style="font-family:Georgia,serif;font-size:1.15rem;margin:0 0 10px;color:#1f2430;">Static Promise &amp; {_e(v_ins.name)}</h2>
  <div class="card" style="border-left:4px solid {border_color};padding:16px 18px;background:#fff;border-radius:12px;">
    <p style="margin:0 0 8px;font-size:0.9rem;line-height:1.55;color:#2c3140;">
      In classical Vedic astrology, predicting exact timing windows requires first confirming the <b>Static Promise</b> in your birth chart (D1) and specialized division (<b>{_e(v_ins.code)}</b>). 
      Your chart indicates an active <b>{pill_lbl}</b> baseline for this matter.
    </p>
    <div style="background:#fcfbf9;border:1px dashed #d5cfc4;border-radius:8px;padding:10px 14px;margin-top:10px;font-size:0.82rem;color:#6a7080;">
      🔒 <b>Full Divisional Chart ({_e(v_ins.code)}) Breakdown:</b> Complete analysis of ascendant lord dignity, house placements, and foundational yogas available in the full consultation.
    </div>
  </div>
</section>"""

        return f"""
<section class="section static-promise" style="margin:24px 0;">
  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;">
    <span style="font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:700;color:#7a4b18;">Foundational Vedic Analysis</span>
    <span class="pill {pill_cls}" style="font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:99px;">{pill_lbl}</span>
  </div>
  <h2 style="font-family:Georgia,serif;font-size:1.25rem;margin:0 0 8px;color:#1f2430;">Static Promise &amp; {_e(v_ins.name)}</h2>
  <p style="font-size:0.86rem;color:#5a554c;margin:0 0 14px;line-height:1.45;">
    Before evaluating exact dates and timing windows, Vedic astrology examines the <b>Static Promise</b> — verifying whether the foundational birth chart (D1) and the dedicated specialized divisional chart ({_e(v_ins.code)}) carry the innate capacity to deliver on this question:
  </p>
  <div class="card" style="border-left:4px solid {border_color};padding:18px 20px;background:#fff;border-radius:12px;margin-bottom:14px;">
    <div style="font-size:0.75rem;letter-spacing:0.1em;text-transform:uppercase;font-weight:700;color:#6a7080;margin-bottom:4px;">{_e(v_ins.code)} Analysis · {_e(v_ins.governs)}</div>
    <h3 style="font-family:Georgia,serif;font-size:1.05rem;margin:4px 0 8px;color:#1f2430;font-weight:600;">{_e(v_ins.headline)}</h3>
    <p style="margin:0 0 12px;font-size:0.92rem;line-height:1.6;color:#2c3140;">{v_ins.prediction}</p>
    <div style="background:#f9f8f5;border-left:3px solid #8a6a1f;padding:10px 14px;border-radius:6px;margin:10px 0 12px;font-size:0.84rem;line-height:1.45;color:#4a453c;">
      <div style="font-weight:700;color:#7a4b18;margin-bottom:4px;">Remedial &amp; Strategic Key:</div>
      {v_ins.remedy}
    </div>
    <div style="border-top:1px solid #eeeae3;padding-top:8px;font-size:0.75rem;color:#7a756c;line-height:1.4;">
      <b>Astrological Basis ({_e(v_ins.name)}):</b> {v_ins.evidence}
    </div>
  </div>
</section>"""
    except Exception as exc:
        print(f"[question_answer] static promise block error: {exc}", flush=True)
        return ""


def render_free(result: dict, *, name: str = "", price: int = 1499,
                prose: Optional[dict] = None, pc: Optional[dict] = None) -> str:
    """Free half: question acknowledgment & domain framing; verdict, timeline and remedies locked."""
    topic = result["topic"]
    who = (name or "").split()[0] if name else ""
    windows = result["windows"]
    promise = result["promise"]
    route = result.get("route") or {}
    prose = prose or {}

    domain = route.get("domain") or topic.label or topic.key
    houses_str = ", ".join(_ord(h) for h in topic.houses) if topic.houses else "governing house"

    lede = (prose.get("opening") or "").strip()
    who_prefix = _e(who + ", ") if who else ""
    lede_html = (
        f'<p class="qa-lede">{_e(lede)}</p>' if lede else
        f'<p class="qa-lede">{who_prefix}we have analyzed your birth chart for this question. '
        f'Here is how the chart frames this life area, while the full verdict, exact timing windows, '
        f'and targeted remedies are available in the full reading.</p>'
    )

    n_windows = len(windows)
    window_plural = "" if n_windows == 1 else "s"
    timing_text = (
        f"<b>{n_windows} validated timing window{window_plural}</b> were detected across your {result['horizon']}-year horizon."
        if n_windows else
        "No single automatic window appears; the full reading dates the subtle movement points."
    )

    static_promise_html = _build_static_promise_section(result, pc, paid=False)

    html = f"""
<section class="qa">
  <div class="qa-asked"><b>You asked:</b> {_e(result['question'])}</div>
  {lede_html}

  <div class="card" style="margin:16px 0;">
    <p style="margin:0 0 6px 0;"><strong>Astrological focus:</strong> We read this primarily as a <b>{_e(domain)}</b> matter, governed by the <b>{_e(houses_str)} house</b> and active planetary periods.</p>
    <p style="margin:0;font-size:0.88rem;color:#656a74;">{_e(_topic_customer_note(topic.key))}</p>
  </div>

  {static_promise_html}

  <div class="qa-window locked" style="margin:14px 0;">
    <div class="qa-wlabel">The Verdict — what your chart actually says</div>
    <p class="blurred">Your birth chart reveals the core strength of this life area, whether the governing planets provide constructive momentum or require steady patience, and the precise conditions under which this matter progresses.</p>
    <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>The consultation verdict is locked.</b> Unlock to read the complete astrological reasoning, house ruler analysis, and actionable steps.</p>
  </div>

  <div class="qa-window locked" style="margin:14px 0;">
    <div class="qa-wlabel">Key timing & dated windows</div>
    <p class="blurred">A primary window of opportunity opens when the active planetary period and key transits align to touch this house, alongside secondary milestones for consolidation.</p>
    <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;">{timing_text} Unlock for the exact calendar dates, milestones, and preparation guidance.</p>
  </div>

  <div class="qa-window locked" style="margin:14px 0;">
    <div class="qa-wlabel">Targeted remedies & immediate relief</div>
    <p class="blurred">Practical first steps to navigate current friction, mantra jaap (108x) for obstructing planets, and auspicious strengthening gemstone rules.</p>
    <p style="margin:6px 0 0 0;font-size:0.85rem;color:#5a554c;"><b>Chart-targeted remedies are locked.</b> Unlock to see the exact gemstone specifications (metal, finger, day to begin) and classical mantra rituals.</p>
  </div>

  <div class="buy">
    <h3>Unlock the full answer</h3>
    <p>Get the complete consultation verdict, all dated timing windows, and the chart-specific remedies for this question.</p>
    <a class="cta" href="#unlock" data-unlock="1">Unlock full reading</a>
  </div>
</section>"""
    from qa_checks.final_customer_boundary import finalize_customer_html
    return finalize_customer_html(html, strict=True)


#: The best-scoring window is not always a good one. Calling it "Strongest
#: window" directly above a map that draws the same months as pressure made
#: the page argue with itself, and the reader believes the picture.
_BEST_WINDOW_LABEL = {
    "up": "Strongest window",
    "down": "Best window available",
    "mixed": "Best window available",
}


def _window_tone(w: dict) -> str:
    """The tone the transition map will give this window, decided once here.

    Mirrors the direction rule in ``life_area_transition.build_transition_map``
    so the heading above the map and the bands inside it cannot disagree.
    """
    if w.get("strong") or w.get("aligned"):
        return "up"
    try:
        bav = int(float(w.get("bav") or 0))
    except (TypeError, ValueError):
        bav = 0
    if (w.get("dasha_dir") == "down" or w.get("dasha") == "down"
            or w.get("promise") == "down" or bav <= 3):
        return "down"
    return "mixed"


def _question_transition_html(result: dict, pc: Optional[dict]) -> str:
    """The same dated transition map the life-area cards use, for a question.

    A question answer that only names one window hides the shape of the
    period around it — when the tone changes, and which ruler or period lord
    is behind each change.
    """
    if not isinstance(pc, dict) or not pc:
        return ""
    rows = []
    for w in list(result.get("windows") or [])[:6]:
        if not isinstance(w, dict) or not (w.get("start") or w.get("end")):
            continue
        row = dict(w)
        row.setdefault("aligned", bool(w.get("strong")))
        row.setdefault("dasha", w.get("dasha_dir") or "mixed")
        rows.append(row)
    if not rows:
        return ""
    try:
        from life_area_transition import build_context_transits, build_transition_map
        from report_conversational import render_transition_map
    except Exception:  # noqa: BLE001
        return ""
    area_key = str(result.get("area_key") or "")
    topic = result.get("topic")
    house = 0
    houses = list(getattr(topic, "houses", None) or [])
    if houses:
        house = int(houses[0] or 0)
    start = result.get("start") or date.today()
    nodes = build_transition_map(pc, area_key, rows, limit=6)
    if not nodes:
        return ""
    context = []
    try:
        import report_confluence as CF
        vim = CF.vimshottari_at(pc, start) or {}
        context = build_context_transits(
            pc, house, today=start, years=3,
            md_lord=str(vim.get("md") or ""), ad_lord=str(vim.get("ad") or ""))
    except Exception:  # noqa: BLE001
        context = []
    return render_transition_map(
        pc, nodes, area=area_key, context=context, today=start, with_css=True,
        kicker="Transition map for this question",
        heading="How the answer changes across the window",
        intro=(
            "The answer is not one flat stretch. Each marker below is a dated "
            "change of tone, taken from the same period and transit evidence "
            "used above."
        ),
    )


def render(result: dict, *, name: str = "", paid: bool = False,
           price: int = 1499, prose: Optional[dict] = None,
           pc: Optional[dict] = None) -> str:
    if not paid:
        return render_free(result, name=name, price=price, prose=prose, pc=pc)
    prose = prose or {}
    topic, best = result["topic"], result["best"]
    nearest = result.get("nearest")
    who = (name or "").split()[0] if name else ""
    promise = result["promise"]

    if not best:
        # Refusing is a real answer. Inventing a date is how this category
        # earned its reputation.
        evidence_rows = _human_question_evidence(result)
        house_rows = "".join(f"<li>{_e(x)}</li>" for x in evidence_rows)
        house_block = (
            f'<div class="evidence"><span class="ev-label">What the chart supports</span><ul>{house_rows}</ul></div>'
            if house_rows else "")
        html = f"""
<section class="qa">
  <div class="qa-asked"><b>You asked:</b> {_e(result['question'])}</div>
  <h2 class="qa-verdict">No sufficiently strong validated window appears for {_e(topic.subject)} in the next {result['horizon']} years.</h2>
  <p>This does not mean the life area is blocked. It means the canonical timing evidence does not provide a strong window inside the period you asked about.</p>
  {house_block}
</section>"""
        from qa_checks.final_customer_boundary import finalize_customer_html
        return finalize_customer_html(html, strict=True)

    intent = _intent(result.get("question", ""))
    # A canonical promise does not always carry a direction key; the answer
    # must not 500 because of it.
    promise_direction = str(promise.get("direction") or "mixed")
    direction_word = {"up": "supports", "down": "does not favour",
                      "mixed": "is mixed on"}.get(promise_direction, "is mixed on")

    if intent in ("how", "general"):
        # "How is my 5th house" is not a yes/no question — answering it with
        # "Yes — and the chart is specific about when" is a non sequitur.
        # Lead with what the chart actually shows, timing stays below as
        # supporting evidence rather than the headline.
        lead = (f"Your chart {direction_word} {topic.subject}.")
        promise_heading = "What your chart shows"
    else:
        lead = ("Yes — and the chart is specific about when."
                if best["strong"] else
                "Yes, but the timing is narrower than you would like.")
        promise_heading = "Does your chart even offer this?"
        if promise_direction == "down" and not best["strong"]:
            lead = ("This is possible but your chart does not favour it. "
                    "The window below is the best of a weak set.")
    # Never splice legacy deep_verdict prose into customer output. Canonical
    # evidence/QuestionFacts are the only permitted source for explanation.
    deep_txt = ""
    if not result.get("canonical_result") and not lead:
        lead = "The question is being answered from the available life-area evidence."

    def _window_scenario(w: dict) -> str:
        if w.get("strong"):
            return (f"This is the window where your chart actually backs "
                    f"{topic.subject} — between {_pretty(w['start'])} and "
                    f"{_pretty(w['end'])}.")
        if (w.get("bav") or 0) >= 5:
            return (f"An opening appears between {_pretty(w['start'])} and "
                    f"{_pretty(w['end'])}, but this remains an opportunity rather "
                    f"than a confirmed outcome.")
        return (f"A partial window runs from {_pretty(w['start'])} to "
                f"{_pretty(w['end'])} — expect movement, not a finished result.")

    def _window_backing(w: dict) -> str:
        parts = []
        if (w.get("bav") or 0) >= 5:
            parts.append("The current timing is supportive for this question.")
        elif (w.get("bav") or 0) <= 3:
            parts.append("The timing offers movement but needs more effort and care.")
        else:
            parts.append("The timing is mixed and should be treated as an opportunity rather than a guarantee.")
        if w.get("period_hits"):
            parts.append("The active period also connects with the matter being asked about.")
        if _window_tone(w) == "down":
            parts.append("The map below draws these same months as pressure: "
                         "this is the best window on offer, not an easy one.")
        return " ".join(parts)


    def window_block(w: dict, label: str) -> str:
        return f"""
  <div class="qa-window {'strong' if w['strong'] else 'weak'}">
    <div class="qa-wlabel">{_e(label)}</div>
    <div class="qa-when">{_e(_pretty(w['start']))} → {_e(_pretty(w['end']))}</div>
    <p class="pred-scenario">{_e(_window_scenario(w))}</p>
    <p class="pred-why"><b>Why:</b> {_e(_window_backing(w))}</p>
  </div>"""

    blocks = ""
    if nearest and nearest["start"] < best["start"]:
        blocks += window_block(nearest, "Soonest possible window")
    blocks += window_block(best, _BEST_WINDOW_LABEL[_window_tone(best)])
    if nearest and nearest["start"] > best["start"]:
        blocks += window_block(nearest, "Next window after that")

    later = [w for w in result["windows"][1:6]
             if w is not nearest
             and abs((w["start"] - best["start"]).days) > 200]
    if later and not paid:
        blocks += f"""
  <div class="qa-window locked">
    <div class="qa-wlabel">{len(later)} further windows</div>
    <p class="blurred">Additional windows fall inside the horizon, each with its
    own period, trigger and support score.</p>
  </div>"""
    elif later:
        blocks += "".join(window_block(w, "Also worth noting")
                          for w in later[:2])

    months_out = max(0, (best["start"] - result["start"]).days // 30)
    gap_note = ""
    if months_out >= 24:
        gap_note = (
            f'<p class="qa-gap"><b>That is {months_out // 12} years out, so here '
            f'is the honest near-term read.</b> Nothing in your chart blocks you '
            f'from moving before then — it simply will not have the wind behind '
            f'it. If you move sooner, treat it as a decision you are making '
            f'rather than a door opening, and expect to do more of the pushing '
            f'yourself.</p>')

    upsell = "" if paid else f"""
  <div class="qa-cta">
    <p>The full reading dates every window across the next
    {result['horizon']} years for this and the other eight areas of your life,
    with what to do in each. Use the unlock button below the report.</p>
  </div>"""

    try:
        import report_confluence as CF
        promise_conf = CF.customer_confidence(promise) or promise.get("agreement", "")
    except Exception:  # noqa: BLE001
        promise_conf = promise.get("agreement", "")

    main_pred = ""
    # Never render the legacy prediction object's raw HTML. CanonicalResult is
    # the only authoritative prediction surface; unsupported topics get a
    # semantic fallback instead of a second astrology renderer.
    if isinstance(result.get("canonical_result"), dict):
        cr = result.get("canonical_result") or {}
        backing = str(cr.get("backing") or "").strip()
        if backing:
            main_pred = (
                f'<div class="prediction"><p class="pred-scenario">'
                f'{_e(backing)}</p></div>')

    # The house-by-house, planet-by-planet reasoning was always computed in
    # answer() but never shown — the reader only saw a verdict and dates,
    # never the chart that produced them. Surfacing it here is what makes
    # this a chart reading rather than a fortune-cookie yes/no.
    evidence_rows = _human_question_evidence(result)
    house_rows = "".join(f"<li>{_e(x)}</li>" for x in evidence_rows)
    house_block = (
        f'<div class="evidence"><span class="ev-label">Why this reading points this way</span>'
        f'<ul>{house_rows}</ul></div>') if house_rows else ""

    now_label = (result.get("now_label") or "").strip()
    now_line = (f'<p class="qa-now">Right now the broader timing is active around this question.</p>'
               if now_label else "")

    # Prefer validated LLM prose when present (facts→prose layer).
    llm_opening = (prose.get("opening") or "").strip()
    llm_answer = (prose.get("answer") or "").strip()
    llm_why = (prose.get("why") or "").strip()
    llm_timing = (prose.get("timing") or "").strip()
    llm_action = (prose.get("action") or "").strip()
    if llm_answer:
        lead = llm_answer
    lede_txt = llm_opening or (
        f"{who + ', ' if who else ''}here is the straight answer, then the chart behind it."
    )

    action_note = (
        f'<p class="qa-action">{_e(llm_action)}</p>' if llm_action else ""
    )

    why_txt = llm_why
    if not why_txt:
        if evidence_rows:
            why_txt = f"{'; '.join(evidence_rows[:3])}."
        else:
            why_txt = f"Your birth chart reflects a {promise_direction} indication across the governing planetary periods for {topic.subject}."

    # Identify supportive and friction planets for the question
    favour_planets: list[str] = []
    against_planets: list[str] = []
    if isinstance(pc, dict):
        try:
            import report_confluence as CF
            vim = CF.vimshottari_at(pc, result.get("start") or date.today()) or {}
            md = str(vim.get("md") or "")
            ad = str(vim.get("ad") or "")
            for p in (md, ad):
                if p in ("Saturn", "Rahu", "Ketu", "Mars") and p not in against_planets:
                    against_planets.append(p)
                elif p and p not in favour_planets and p not in ("Saturn", "Rahu", "Ketu", "Mars"):
                    favour_planets.append(p)
            hl = pc.get("house_lords", {}) or {}
            houses = list(getattr(topic, "houses", None) or [])
            for h in houses:
                lord = (hl.get(str(h)) or {}).get("lord") or ""
                if lord:
                    if lord in ("Saturn", "Rahu", "Ketu", "Mars") and lord not in against_planets:
                        against_planets.append(lord)
                    elif lord not in favour_planets and lord not in ("Saturn", "Rahu", "Ketu", "Mars"):
                        favour_planets.append(lord)
        except Exception:
            pass

    planets_html = ""
    if favour_planets or against_planets:
        planets_html = (
            f"<div style='margin-top:12px;padding-top:10px;border-top:1px solid var(--line);'>"
            f"<p style='margin:4px 0'><strong>Planets supporting you:</strong> {_e(', '.join(favour_planets)) if favour_planets else 'None stand out strongly'}</p>"
            f"<p style='margin:4px 0'><strong>Planets creating friction:</strong> {_e(', '.join(against_planets)) if against_planets else 'None stand out strongly'}</p>"
            f"</div>"
        )

    dynamics_summary = (
        "Your birth chart indicates active planetary periods across the governing houses for this matter — "
        + ("the planetary currents show mixed influences that require strategic timing and proactive effort."
           if promise_direction == "mixed" else
           "the planetary alignments provide supportive momentum for progress." if promise_direction == "up" else
           "the planetary influences create temporary friction that calls for careful navigation.")
    )

    timing_items = []
    if nearest and nearest["start"] < best["start"]:
        timing_items.append(
            f"<li><b>{_pretty(nearest['start'])} → {_pretty(nearest['end'])}</b> — "
            f"<b>Soonest opening:</b> Good for early preparation, preliminary discussions, and setting groundwork before major shifts.</li>"
        )
    best_desc = (
        "Strongest astrological opening — active planetary periods and transits align to back meaningful progress and initiative."
        if best.get("strong") else
        "Primary window of opportunity — supportive planetary currents create favorable conditions for growth."
    )
    timing_items.append(
        f"<li><b>{_pretty(best['start'])} → {_pretty(best['end'])}</b> — "
        f"<b>Best window:</b> {best_desc}</li>"
    )
    if nearest and nearest["start"] > best["start"]:
        timing_items.append(
            f"<li><b>{_pretty(nearest['start'])} → {_pretty(nearest['end'])}</b> — "
            f"<b>Secondary window:</b> Follow-up opening to consolidate gains and build on previous milestones.</li>"
        )
    for w in later[:2]:
        timing_items.append(
            f"<li><b>{_pretty(w['start'])} → {_pretty(w['end'])}</b> — "
            f"<b>Later window:</b> Long-term period for consolidation, stabilization, and continuing growth.</li>"
        )

    verdict_flag = ("up" if promise_direction == "up" else
                    "down" if promise_direction == "down" else "mixed")

    # Sanitize technical leaks in timing prose
    if llm_timing and any(t in llm_timing.lower() for t in ("ulka", "chara", "dasha", "amber", "validated window note", "saturn-saturn")):
        llm_timing = "These are the validated windows where planetary transits and active periods align to create meaningful momentum."

    timing_note_text = llm_timing or "These are the validated windows where planetary transits and active periods align to create meaningful momentum."

    static_promise_html = _build_static_promise_section(result, pc, paid=True)

    html = f"""
<section class="qa" data-verdict="{verdict_flag}">
  <div class="qa-asked"><b>You asked:</b> {_e(result['question'])}</div>
  <p class="qa-lede">{_e(lede_txt)}</p>
  <h1 class="verdict-line">{_e(lead)}</h1>
  <p class="pred-why"><b>Why:</b> {_e(why_txt)}</p>
  {action_note}
</section>

{static_promise_html}

<section class="section planetary-dynamics">
  <h2>Planetary dynamics & supporting influences</h2>
  <div class="card">
    <p style="margin:0 0 0.6rem 0;">{_e(dynamics_summary)}</p>
    {planets_html}
  </div>
</section>

<section class="section timing-windows">
  <h2>Key timing & dated windows</h2>
  <div class="card">
    <p class="sec-note" style="margin-top:0;">{_e(timing_note_text)}</p>
    <ul class="windows">
      {''.join(timing_items)}
    </ul>
  </div>
</section>"""
    from qa_checks.final_customer_boundary import finalize_customer_html
    return finalize_customer_html(html, strict=True)
