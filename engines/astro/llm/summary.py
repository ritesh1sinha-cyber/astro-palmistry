"""Plain-English executive summary for finished customer reports.

Runs as the last pass after the final HTML is assembled. Two summaries are
built per report: one from the free half (what a locked reader sees, closing
on a concrete account of what the paid half holds) and one from the paid half
(the full reading in everyday language). The LLM reads the visible report text
plus a customer-safe brief assembled from the engine facts; when the LLM is off
or fails QA, a brief-driven fallback keeps the Summary button working.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from html.parser import HTMLParser
from typing import Any, Optional

from .rules import system_prompt_for
from .schemas import PlainSummaryProse

_MAX_INPUT_CHARS = 14000
_SKIP_CLASS_RE = re.compile(
    r"\b(blurred|lock-blur|lock-over|lock-wrap|locked-preview|fine|astro-proof-details|"
    # The paywall block sits in the same document as the reading (report_shell
    # buy_block). Its copy is a pitch, never a finding.
    r"buy|cta|cta-dark|cta-light|paycard|pay-card)\b",
    re.I,
)
_SKIP_ID_RE = re.compile(r"\b(unlock|paywall|buy)\b", re.I)

_MONTHS = (
    "January|February|March|April|May|June|July|August|September|"
    "October|November|December"
)
_MONTH_YEAR_RE = re.compile(rf"\b({_MONTHS})\s+20\d{{2}}\b", re.I)
_YEAR_RE = re.compile(r"\b20\d{2}\b")
_ISO_DATE_RE = re.compile(r"\b20\d{2}-\d{2}(?:-\d{2})?\b")


def _dates_free_may_keep(text: str) -> bool:
    """Whether a free summary sentence may keep the dates it carries.

    A date the reader has already lived through is evidence — it lets them
    check the reading against their own year. A date still ahead of them is
    the answer the full reading sells. Same rule as the report page, so the
    summary never withholds what the page it summarises has already shown.
    """
    dated = list(_MONTH_YEAR_RE.finditer(text)) + list(_ISO_DATE_RE.finditer(text))
    try:
        from free_dates import is_past
    except Exception:                                                # noqa: BLE001
        return not (dated or _YEAR_RE.search(text))
    if any(not is_past(m.group(0)) for m in dated):
        return False
    if not dated:
        this_year = date.today().year
        return not any(int(y) > this_year for y in _YEAR_RE.findall(text))
    return True

# Technical vocabulary the summary exists to translate away. The prompt asks
# for plain English; this is what holds it to the promise.
_JARGON_RE = re.compile(
    r"\b(dasha|dashas|antardasha|pratyantardasha|mahadasha|antar dasha|"
    r"nakshatra|nakshatras|ashtakavarga|bindu|bindus|varga|vargas|"
    r"dusthana|dusthanas|significator|significators|confluence|"
    r"vimshottari|chara dasha|yogini|jaimini|karaka|karakas|"
    r"applying aspect|lordship|prashna|jyotish|upaya|upayas|"
    r"sav|bav|paywall)\b",
    re.I,
)
_BARE_HOUSE_RE = re.compile(r"\b\d{1,2}(?:st|nd|rd|th)\s+house\b", re.I)

# Report headings are written for someone already reading a chart. A heading
# carrying any of these is dropped from the locked list rather than translated:
# the list is a sales checklist, and half-translated headings read worse than
# the plain counts we already have.
_LABEL_JARGON_RE = re.compile(
    r"\b(divisional|classical|transit|transits|graha|grahas|rashi|lagna|"
    r"navamsa|navamsha|d1|d9|d10|arudha|bhava|drishti|shad ?bala|"
    r"consultation reading|indicators)\b",
    re.I,
)

# Engine scores read as authority to whoever wrote them and as noise to the
# reader: "26 sign score points" and "SAV 24/56" mean nothing without the model
# behind them. The strength belongs in the summary; the number does not.
_METRIC_RES: tuple[re.Pattern, ...] = (
    re.compile(r"\b(?:SAV|BAV)\b\s*\d*", re.I),
    re.compile(r"\b\d+\s+(?:sign\s+)?(?:score|strength)\s+points?\b", re.I),
    re.compile(r"\bthreshold of\s+\d+\b", re.I),
    re.compile(r"\b\d+s?\s*(?:[-–—]|to)\s*\d+s?\s+out of\s+\d+\b", re.I),
    re.compile(r"\b\d+s?\s+out of\s+\d+\b", re.I),
)
# A metric tucked into brackets can be deleted whole without breaking the
# sentence around it, so that case is repaired rather than rejected. Both forms
# require a digit, so an ordinary aside like "(the strongest point of the year)"
# survives.
_METRIC_ASIDE_RES: tuple[re.Pattern, ...] = (
    re.compile(r"\s*[(\[][^()\[\]]*\b(?:SAV|BAV)\b[^()\[\]]*[)\]]", re.I),
    re.compile(
        r"\s*[(\[](?=[^()\[\]]*\d)[^()\[\]]*"
        r"(?:\b(?:score|scores|points?|rating|out of)\b|\d\s*/\s*\d)"
        r"[^()\[\]]*[)\]]",
        re.I,
    ),
)

# Never let engine bookkeeping cross into the brief we hand the model.
_INTERNAL_KEYS = frozenset({
    "score", "scores_raw", "support_n", "caution_n", "signal_ids", "point_ids",
    "facts_hash", "schema_version", "engine_version", "lane_scores", "lanes",
    "confluence_score", "semantic_tags", "chart_hash", "prompt_version",
    "model_name", "run_meta", "used_fact_ids",
})

_STOP = frozenset({
    "about", "after", "again", "their", "there", "these", "those", "which",
    "while", "would", "could", "should", "where", "being", "other", "under",
    "years", "months", "report", "reading", "chart", "value", "label", "title",
    "given", "shows", "still", "because", "through",
})

_NUM_WORDS = (
    "", "one", "two", "three", "four", "five", "six",
    "seven", "eight", "nine", "ten", "eleven", "twelve",
)


_BLOCK_TAGS = frozenset({
    "p", "div", "section", "article", "li", "ul", "ol", "table", "tr", "td", "th",
    "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "header", "footer", "br",
    "figcaption", "dt", "dd", "aside", "main",
})
_BREAK = "\x00"


_VOID_TAGS = frozenset({
    "br", "img", "hr", "input", "meta", "link", "source", "area", "col",
    "embed", "track", "wbr", "base", "param",
})


class _ReportText(HTMLParser):
    """Visible prose only, with locked and paywall subtrees excluded.

    Skipping is tracked by element depth. A plain counter ended the skip at the
    first nested closing tag, so everything after the heading inside a locked
    block was still collected.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._stack: list[str] = []
        self._skip_depths: list[int] = []
        self._raw = 0

    def _break(self) -> None:
        if self.parts and self.parts[-1] != _BREAK:
            self.parts.append(_BREAK)

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t in ("script", "style", "nav"):
            self._raw += 1
            return
        if t in _VOID_TAGS:
            if t in _BLOCK_TAGS:
                self._break()
            return
        self._stack.append(t)
        cls = ident = ""
        for k, v in attrs:
            key = k.lower()
            if key == "class":
                cls = str(v or "")
            elif key == "id":
                ident = str(v or "")
        if _SKIP_CLASS_RE.search(cls) or _SKIP_ID_RE.search(ident):
            self._skip_depths.append(len(self._stack))
        if t in _BLOCK_TAGS:
            self._break()

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in ("script", "style", "nav"):
            if self._raw:
                self._raw -= 1
            return
        if t in _VOID_TAGS:
            return
        if t in self._stack:
            idx = len(self._stack) - 1 - self._stack[::-1].index(t)
            del self._stack[idx:]
            while self._skip_depths and self._skip_depths[-1] > len(self._stack):
                self._skip_depths.pop()
        if t in _BLOCK_TAGS:
            self._break()

    def handle_data(self, data):
        if self._raw or self._skip_depths:
            return
        text = re.sub(r"\s+", " ", str(data or "")).strip()
        if text:
            self.parts.append(text)


def html_to_report_text(html: str) -> str:
    """Extract customer-visible prose from rendered report HTML.

    Block boundaries become sentence boundaries. Without that a heading runs
    straight into the paragraph under it, and every downstream sentence split
    inherits the join — which is how page furniture ends up quoted inside a
    summary sentence.
    """
    p = _ReportText()
    try:
        p.feed(html or "")
        p.close()
    except Exception:  # noqa: BLE001
        return re.sub(r"<[^>]+>", " ", html or "")
    chunks: list[str] = []
    for raw in " ".join(p.parts).split(_BREAK):
        chunk = re.sub(r"\s{2,}", " ", raw).strip()
        if not chunk:
            continue
        if not chunk.endswith((".", "!", "?", ":", ";", ",", "—", "-")):
            chunk += "."
        chunks.append(chunk)
    return re.sub(r"\s{2,}", " ", " ".join(chunks)).strip()[:_MAX_INPUT_CHARS]


# ---------------------------------------------------------------------------
# Sentence hygiene — furniture, jargon, and dates the reader must not see
# ---------------------------------------------------------------------------
# Prices, nav labels, table cells and unlock copy live in the same DOM as the
# reading. They are not findings and must never be quoted back as a summary.
_FURNITURE_RE = re.compile(
    r"(₹|\$\d|\bunlock\b|\bsubscribe\b|\bfree preview\b|\bpaywall\b|"
    r"\bFuture timeline is locked\b|\block(ed)?\b|"
    r"\bscroll\b|\bclick\b|\btap\b|\bread more\b|\bdownload\b|\bshare\b|"
    r"\bcontents\b|\bterms\b|\bprivacy\b|\brefund)",
    re.I,
)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", str(text or "")) if s.strip()]


# Plain equivalents, longest first so "pratyantardasha" is not eaten by "dasha".
_PLAIN_TERMS: tuple[tuple[str, str], ...] = (
    (r"pratyantardasha", "micro-period"),
    (r"pratyantar", "micro-period"),
    (r"antar[\s-]?dasha", "sub-period"),
    (r"antardasha", "sub-period"),
    (r"maha[\s-]?dasha", "main period"),
    (r"mahadasha", "main period"),
    (r"vimshottari|chara dasha|yogini|jaimini", "period cycle"),
    (r"dashas", "periods"),
    (r"dasha", "period"),
    (r"ashtakavarga", "strength score"),
    (r"bindus", "strength points"),
    (r"bindu", "strength point"),
    (r"nakshatras", "birth stars"),
    (r"nakshatra", "birth star"),
    (r"dusthanas", "difficult placements"),
    (r"dusthana", "difficult placement"),
    (r"significators", "ruling planets"),
    (r"significator", "ruling planet"),
    (r"karakas", "indicators"),
    (r"karaka", "indicator"),
    (r"vargas", "divisional charts"),
    (r"varga", "divisional chart"),
    (r"applying aspect", "closing aspect"),
    (r"lordship", "rulership"),
    (r"prashna", "question chart"),
    (r"confluence", "agreement"),
    (r"jyotish", "Vedic astrology"),
    (r"upayas", "remedies"),
    (r"upaya", "remedy"),
    (r"natal", "birth"),
    (r"behind the paywall", "in the full reading"),
    (r"paywall", "full reading"),
    (r"lanes", "checks"),
    (r"lane", "check"),
    (r"houses", "areas of life"),
)
_PLAIN_RES = tuple((re.compile(rf"\b{pat}\b", re.I), rep) for pat, rep in _PLAIN_TERMS)

# "10th house" means nothing to a reader who has not studied a chart. The short
# forms mirror the long significations used by the report engines.
_HOUSE_PLAIN: dict[int, str] = {
    1: "identity and vitality",
    2: "money and family",
    3: "communication and initiative",
    4: "home and family life",
    5: "children and creativity",
    6: "daily work and health",
    7: "partnership and marriage",
    8: "change and upheaval",
    9: "fortune and higher learning",
    10: "career and public standing",
    11: "gains and income",
    12: "expenses and letting go",
}
# Only a known area noun is swallowed after "of": a lazy catch-all here ate the
# rest of the sentence, because "10th house of career supports this" is all
# lowercase words up to the full stop.
_HOUSE_GLOSS = (
    r"(?:\s+of\s+(?:the\s+)?(?:career|profession|work|children|progeny|marriage|"
    r"partnership|partnerships|money|wealth|finance|finances|gains|income|health|"
    r"home|family|fortune|luck|learning|education|communication|siblings|"
    r"expenses|loss|losses|transformation|change|identity|self|status|dharma)"
    r"(?:\s+and\s+[a-z]+)?)?"
)
_HOUSE_PHRASE_RE = re.compile(
    r"\b(?:the\s+|your\s+|his\s+|her\s+|their\s+)?"
    r"(\d{1,2})(?:st|nd|rd|th)\s+house\b" + _HOUSE_GLOSS,
    re.I,
)


def _dehouse(text: str) -> str:
    """"your 10th house of career" -> "your career and public standing".

    Two forms, because one does not fit every sentence: "the 11th house" sits
    after a preposition and needs "the ... part of your chart" to stay readable,
    while "your 11th house" can take the possessive directly.
    """
    def sub(m: re.Match) -> str:
        whole = m.group(0)
        try:
            area = _HOUSE_PLAIN[int(m.group(1))]
        except (KeyError, ValueError):
            phrase = "that area of your chart"
        else:
            phrase = (f"the {area} part of your chart"
                      if re.match(r"the\s", whole, re.I) else f"your {area}")
        return phrase[:1].upper() + phrase[1:] if whole[:1].isupper() else phrase
    return _HOUSE_PHRASE_RE.sub(sub, text or "")


def _drop_metric_asides(text: str) -> str:
    """Delete bracketed score asides: "(SAV 24/56, Moon BAV 4/8)" and friends."""
    t = str(text or "")
    for rx in _METRIC_ASIDE_RES:
        t = rx.sub("", t)
    t = re.sub(r"\s+([,.;:])", r"\1", t)
    return re.sub(r"\s{2,}", " ", t).strip()


def _dejargon(text: str) -> str:
    """Swap technical vocabulary for its plain equivalent, keeping the fact.

    Dropping the sentence would also drop the date or verdict inside it, and a
    summary that loses the finding to protect the wording has failed twice.
    """
    t = _drop_metric_asides(text)
    for rx, rep in _PLAIN_RES:
        t = rx.sub(rep, t)
    return _dehouse(t)


def _is_furniture(sentence: str) -> bool:
    s = sentence.strip()
    if _FURNITURE_RE.search(s):
        return True
    if "·" in s or "•" in s or "✓" in s:
        return True
    if len(s.split()) < 5:
        return True
    return False


def _drop_bad_sentences(text: str, *, free: bool, allow_dates: bool = False) -> str:
    """Keep the sentences a customer should read, drop the rest whole.

    Whole sentences, because deleting a date or a technical word mid-clause
    leaves prose that reads worse than the jargon it removed.
    """
    kept: list[str] = []
    for s in _sentences(_dejargon(text)):
        if _is_furniture(s):
            continue
        if _JARGON_RE.search(s) or _BARE_HOUSE_RE.search(s):
            continue
        if free and not allow_dates and not _dates_free_may_keep(s):
            continue
        kept.append(s)
    return " ".join(kept)


def _tidy(text: str) -> str:
    """Close off a string that was cut to a character budget upstream.

    Report metadata truncates prose to fixed widths, so a verdict can arrive as
    "... Career Growth, Status & Vo". Dropping the stub word and the dangling
    conjunction is the difference between a summary and a visible defect.
    """
    t = re.sub(r"\s{2,}", " ", str(text or "")).strip()
    if not t:
        return ""
    if not t.endswith((".", "!", "?")):
        words = t.split(" ")
        if len(words) > 3 and words[-1].isalpha() and len(words[-1]) <= 2:
            words = words[:-1]
        t = " ".join(words).rstrip(" ,;:-—&") + "."
    return t[:1].upper() + t[1:]


def _trim_headline(text: str) -> str:
    """Close off a headline that ran into its length cap mid-clause.

    The schema caps the headline, and a model that writes past the cap gets cut
    there — "... but timing, patience, and careful re". Falling back to the last
    clause boundary keeps a whole thought instead of a stub.
    """
    t = re.sub(r"\s{2,}", " ", str(text or "")).strip()
    if not t or t.endswith((".", "!", "?")):
        return t
    if len(t) >= 140:
        for sep in (" — ", " – ", " -- ", "; ", ", "):
            cut = t.rfind(sep)
            if cut > 60:
                t = t[:cut]
                break
    return _tidy(t)


def _enabled() -> bool:
    try:
        from core.config import S
        return bool(S.llm_tab_enabled("summary"))
    except Exception:  # noqa: BLE001
        return False


def _complete(prose_schema, system: str, user: str):
    try:
        from core.llm_client import complete_model
        return complete_model(prose_schema, system, user, temperature=0.35)
    except Exception:  # noqa: BLE001
        return None


def _label(text: Any) -> str:
    """Human form of an engine label ("children_window" -> "Children window")."""
    t = re.sub(r"[_\-]+", " ", str(text or "")).strip()
    t = re.sub(r"\s{2,}", " ", t)
    return t[:1].upper() + t[1:] if t else ""


_MONTH_NAMES = (
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def _human_date(value: Any) -> str:
    """"2026-10-31" -> "October 2026". Engine dates are ISO; readers are not."""
    text = str(value or "").strip()
    m = re.match(r"^(20\d{2})-(\d{2})(?:-\d{2})?$", text)
    if not m:
        return text
    month = int(m.group(2))
    if 1 <= month <= 12:
        return f"{_MONTH_NAMES[month]} {m.group(1)}"
    return text


def _num_word(n: int) -> str:
    try:
        n = int(n)
    except Exception:  # noqa: BLE001
        return ""
    if 1 <= n < len(_NUM_WORDS):
        return _NUM_WORDS[n]
    return str(n)


def _clip(value: Any, limit: int = 240) -> str:
    text = re.sub(r"\s{2,}", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    # Cut at word boundary to avoid "restru." stubs; keep at least 70% of limit
    cut = text[:limit]
    space = cut.rfind(" ")
    if space > limit * 0.7:
        return cut[:space]
    return cut


def _str_list(value: Any, *, cap: int = 8, limit: int = 200) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, dict):
            item = item.get("text") or item.get("label") or item.get("note") or ""
        text = _clip(item, limit)
        if text:
            out.append(text)
        if len(out) >= cap:
            break
    return out


def _scrub(value: Any) -> Any:
    """Drop internal bookkeeping keys anywhere in a brief fragment."""
    if isinstance(value, dict):
        return {
            k: _scrub(v) for k, v in value.items()
            if k not in _INTERNAL_KEYS and v not in (None, "", [], {})
        }
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    return value


# ---------------------------------------------------------------------------
# The brief — customer-safe engine findings, per report kind
# ---------------------------------------------------------------------------
def _summary_brief(kind: str, meta: dict, facts: Any, *, paid: bool) -> dict:
    """Compact, customer-safe view of the engine findings for this report.

    Free briefs carry no dates: the dated material is the paid half, and a
    free summary that quotes a date has given away what it is selling.
    """
    meta = meta or {}
    f = facts if isinstance(facts, dict) else {}
    brief: dict[str, Any] = {}

    def put(key: str, value: Any) -> None:
        if value not in (None, "", [], {}):
            brief[key] = value

    if kind in ("full_report", "classical_report"):
        # Extract direct chart foundations from pc / facts
        lagna_sign = ""
        moon_sign = ""
        nakshatra = ""
        dasha_str = ""
        next_dasha_str = ""
        lord = ""
        ak = "Moon"
        amk = "Jupiter"
        
        if isinstance(f.get("lagna"), dict):
            lagna_sign = str(f["lagna"].get("sign") or "")
        elif isinstance(f.get("lagna"), str):
            lagna_sign = str(f["lagna"])
        if not lagna_sign and meta.get("lagna"):
            lagna_sign = str(meta["lagna"])
            
        planets = f.get("planets") if isinstance(f.get("planets"), dict) else {}
        if "Moon" in planets and isinstance(planets["Moon"], dict):
            moon_sign = str(planets["Moon"].get("sign") or "")
        elif meta.get("moonSign"):
            moon_sign = str(meta.get("moonSign"))
            
        nakshatra = str(f.get("nakshatra") or meta.get("nakshatra") or (f.get("meta") or {}).get("nakshatra") or "")
        
        try:
            from engines.astro.astro_precompute import SIGN_LORDS
        except ImportError:
            try:
                from astro_precompute import SIGN_LORDS
            except ImportError:
                SIGN_LORDS = {
                    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
                    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
                    "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
                    "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
                }
        if lagna_sign:
            lord = SIGN_LORDS.get(lagna_sign, "Sun")
            
        # Jaimini Karakas
        jai_raw = f.get("jaimini") if isinstance(f, dict) else None
        if isinstance(jai_raw, dict):
            karakas = jai_raw.get("karakas")
            if isinstance(karakas, dict):
                ak = str(karakas.get("AK") or "Moon")
                amk = str(karakas.get("AmK") or "Jupiter")
        
        vim = f.get("vimshottari") if isinstance(f.get("vimshottari"), dict) else {}
        cur_md_obj = vim.get("current_md") or {}
        cur_md = cur_md_obj.get("md_lord") if isinstance(cur_md_obj, dict) else str(cur_md_obj or "")
        ads = vim.get("current_md_antardashas") or []
        cur_ad = ""
        next_ad = ""
        if ads:
            cur_idx = next((i for i, a in enumerate(ads) if isinstance(a, dict) and a.get("status") == "current"), 0)
            cur_ad = str(ads[cur_idx].get("ad_lord") or "") if cur_idx < len(ads) else ""
            if cur_idx + 1 < len(ads):
                next_ad = str(ads[cur_idx + 1].get("ad_lord") or "")
                
        if cur_md and cur_ad:
            dasha_str = f"{cur_md} Mahadasha — {cur_ad} Antardasha"
        elif cur_md:
            dasha_str = f"{cur_md} Mahadasha"
            
        if cur_md and next_ad:
            next_dasha_str = f"{cur_md}—{next_ad}"

        put("classical_lagna", lagna_sign)
        put("classical_moon", moon_sign)
        put("classical_nakshatra", nakshatra)
        put("classical_lord", lord)
        put("classical_ak", ak)
        put("classical_amk", amk)
        put("classical_dasha", dasha_str)
        put("next_dasha", next_dasha_str)

        put("personality_traits", _str_list(f.get("personality_traits"), cap=8))
        put("current_phase_direction", _clip(f.get("phase_direction"), 40))
        put("current_phase_tone", _clip(f.get("phase_tone"), 300))
        put("current_phase_notes", _str_list(f.get("phase_notes"), cap=4, limit=240))
        put("areas_under_pressure", _str_list(
            f.get("hardest_area_labels") or f.get("hardest_areas"), cap=4, limit=60))
        cards = f.get("cards") if isinstance(f.get("cards"), list) else []
        area_lines = []
        for card in cards[:8]:
            if not isinstance(card, dict):
                continue
            entry = {
                "area": _clip(card.get("label") or card.get("area"), 60),
                "direction": _clip(card.get("direction"), 40),
                "outlook": _clip(card.get("outlook_line"), 240),
            }
            if entry["area"]:
                area_lines.append({k: v for k, v in entry.items() if v})
        put("life_areas", area_lines)
        foundation_terms = (
            ("D1", ("self", "vitality")),
            ("D2", ("money", "wealth", "savings")),
            ("D3", ("siblings", "courage")),
            ("D12", ("parents", "roots", "family")),
        )
        foundations = []
        for chart, terms in foundation_terms:
            for area in area_lines:
                label = str(area.get("area") or "").lower()
                if any(term in label for term in terms):
                    entry = {"chart": chart, **area}
                    foundations.append(entry)
                    break
        put("chart_foundations", foundations)
        specialist = f.get("specialist_readings")
        if isinstance(specialist, dict):
            specialist_brief: dict[str, Any] = {}
            for engine_key in ("chandra_naadi", "lal_kitab", "rahu_ketu", "transit_matrix"):
                block = specialist.get(engine_key)
                if not isinstance(block, dict):
                    continue
                findings = []
                for finding in (block.get("findings") or [])[:4]:
                    if not isinstance(finding, dict):
                        continue
                    row = {
                        "title": _clip(finding.get("title"), 120),
                        "summary": _clip(finding.get("summary"), 260),
                        "planet": _clip(finding.get("planet"), 30),
                        "house": finding.get("house") if paid else 0,
                    }
                    if row["title"] and row["summary"]:
                        findings.append({k: v for k, v in row.items() if v not in ("", 0, None)})
                if findings:
                    specialist_brief[engine_key] = findings
            put("specialist_readings", specialist_brief)
        if kind == "classical_report":
            put("classical_lagna", _clip(meta.get("lagna"), 40))
            put("classical_moon", _clip(meta.get("moonSign"), 40))
            put("classical_nakshatra", _clip(meta.get("nakshatra"), 80))
            put("classical_dasha", _clip(meta.get("mahadasha"), 40))
        if paid:
            put("current_phase_ends", _clip(f.get("phase_end"), 40))
            windows = f.get("timing_windows") if isinstance(f.get("timing_windows"), list) else []
            put("dated_windows", [
                {
                    "label": _clip(w.get("label") or w.get("area"), 60),
                    "start": _clip(w.get("start"), 24),
                    "end": _clip(w.get("end"), 24),
                }
                for w in windows[:6] if isinstance(w, dict)
            ])

    elif kind == "user_question":
        ans = meta.get("answer") if isinstance(meta.get("answer"), dict) else {}
        put("question", _clip(meta.get("question"), 300))
        put("life_area", _clip(meta.get("area") or f.get("domain"), 80))
        put("direction", _clip(ans.get("direction"), 40))
        rd = meta.get("reading") if isinstance(meta.get("reading"), dict) else {}
        put("finding", _clip(rd.get("answer") or ans.get("label"), 300))
        if paid:
            put("breakthrough_window", _clip(ans.get("breakthrough"), 240))

    elif kind == "horary":
        ans = meta.get("answer") if isinstance(meta.get("answer"), dict) else {}
        verdicts = meta.get("verdicts") if isinstance(meta.get("verdicts"), dict) else {}
        western = verdicts.get("western") if isinstance(verdicts.get("western"), dict) else {}
        put("question", _clip(meta.get("question"), 300))
        put("subject", _clip(ans.get("subject"), 120))
        if paid:
            put("verdict", _clip(ans.get("label") or western.get("verdict"), 120))
            put("confidence", _clip(ans.get("confidence") or western.get("confidence"), 40))
            if ans.get("favourable") is not None:
                put("favourable", bool(ans.get("favourable")))
        if paid:
            windows = f.get("timing_windows") if isinstance(f.get("timing_windows"), list) else []
            put("dated_windows", [
                {"label": _clip(w.get("label"), 60), "start": _clip(w.get("start"), 24),
                 "end": _clip(w.get("end"), 24)}
                for w in windows[:4] if isinstance(w, dict)
            ])

    elif kind == "palm":
        put("hand_shape", _clip(meta.get("handType"), 40))
        put("dominant_hand", _clip(meta.get("dominantHand"), 20))
        put("both_hands_summary", _clip(meta.get("summary"), 600))
        put("personality_traits", _str_list(f.get("personality_traits"), cap=8))
        scores = meta.get("scores") if isinstance(meta.get("scores"), list) else []
        put("strength_meters", [
            {"name": _clip(s.get("k"), 40), "out_of_100": s.get("v")}
            for s in scores[:6]
            if isinstance(s, dict) and s.get("k") and isinstance(s.get("v"), (int, float))
        ])
        aspects = f.get("aspects") if isinstance(f.get("aspects"), list) else []
        put("life_areas", [
            {
                "area": _clip(a.get("aspect"), 60),
                "direction": _clip(a.get("direction"), 40),
                "reading": _clip(a.get("semantic_summary"), 240),
            }
            for a in aspects[:8] if isinstance(a, dict) and a.get("aspect")
        ])
        consultation = f.get("consultation_sections")
        if isinstance(consultation, dict):
            measured_sections = []
            for key, section in consultation.items():
                if not isinstance(section, dict):
                    continue
                title = _clip(section.get("title"), 100)
                narrative = _clip(section.get("narrative"), 260)
                if title and narrative:
                    measured_sections.append({
                        "title": title,
                        "summary": narrative,
                    })
            put("measured_consultation", measured_sections[:6])

    elif kind == "numerology":
        put("empty_grid_cells", meta.get("emptyCells"))
        put("name_alignment", _clip(meta.get("nameAlignment"), 80))
        put("teaser", _clip(meta.get("teaser"), 300))

    elif kind == "daily":
        put("date", _clip(meta.get("date"), 24))
        put("teaser", _clip(meta.get("teaser"), 300))

    elif kind == "kundali_match":
        put("headline", _clip(meta.get("headline"), 300))
        put("verdict", _clip(meta.get("verdict"), 200))
        if meta.get("total") is not None:
            put("guna_points", f"{meta.get('total')} out of {meta.get('maxGuna') or 36}")
        put("band", _clip(meta.get("bandPlain") or meta.get("band"), 80))
        put("active_concerns", _str_list(meta.get("activeDoshas"), cap=4, limit=60))

    elif kind == "muhurat":
        put("verdict", _clip(meta.get("verdict"), 300))
        put("date", _clip(meta.get("date"), 24))

    elif kind == "btr":
        put("skipped", bool(meta.get("skipped")))
        put("reason", _clip(meta.get("reason"), 240))

    if not brief:
        put("teaser", _clip(meta.get("teaser") or meta.get("summary"), 400))

    brief = _deep_dejargon(_scrub(brief))
    if not paid and kind != "daily":
        brief = _free_safe(brief)
    return brief


def _deep_dejargon(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _deep_dejargon(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_deep_dejargon(v) for v in node]
    if isinstance(node, str):
        return _dejargon(node)
    return node


def _free_safe(node: Any) -> Any:
    """Drop future-dated material from a free brief, item by item.

    Engine notes carry dates inline ("the pressure eases after October 2026").
    A date still ahead of the reader belongs to the half they have not paid
    for, so the note goes rather than being quietly reworded. A date they have
    already lived through stays: it is what lets them check the reading
    against their own year, and the report page shows it too.
    """
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            cleaned = _free_safe(v)
            if cleaned not in (None, "", [], {}):
                out[k] = cleaned
        return out
    if isinstance(node, list):
        return [c for c in (_free_safe(v) for v in node) if c not in (None, "", [], {})]
    if isinstance(node, str):
        return " ".join(s for s in _sentences(node) if _dates_free_may_keep(s))
    return node


def _stems(text: str) -> set[str]:
    """Four-letter stems of the content words in `text`.

    Stems rather than whole words because a good summary paraphrases: the brief
    says "leaning no" and the summary says "the chart leans against it". That is
    the writing we asked for, so it has to count as grounded.
    """
    words = re.findall(r"[a-z]{5,}", (text or "").lower())
    return {w[:4] for w in words if w not in _STOP}


def _brief_values(node: Any, out: list[str]) -> None:
    """Collect the brief's values, never its keys.

    Field names would let a summary pass by saying "the verdict" or "your
    question" without naming anything the reading actually found.
    """
    if isinstance(node, dict):
        for v in node.values():
            _brief_values(v, out)
    elif isinstance(node, list):
        for v in node:
            _brief_values(v, out)
    elif isinstance(node, str):
        out.append(node)


def _brief_tokens(brief: dict) -> set[str]:
    """Content stems from the brief, used to check the summary says something."""
    values: list[str] = []
    _brief_values(brief, values)
    return _stems(" ".join(values))


# ---------------------------------------------------------------------------
# Locked inventory — what the paid half holds, counted but never quoted
# ---------------------------------------------------------------------------
def _count_deep(node: Any, keys: tuple[str, ...]) -> int:
    total = 0
    if isinstance(node, dict):
        for k, v in node.items():
            if k in keys:
                if isinstance(v, list):
                    total += len([x for x in v if x])
                elif v:
                    total += 1
            total += _count_deep(v, keys)
    elif isinstance(node, list):
        for item in node:
            total += _count_deep(item, keys)
    return total


def _locked_inventory(paid_html: str, facts: Any, meta: dict) -> dict:
    """Counts and section labels for the paid half. Never any values.

    This is what lets the free summary be specific about what is still behind
    the paywall without handing over a single date or verdict.
    """
    meta = meta or {}
    f = facts if isinstance(facts, dict) else {}
    paid_text = html_to_report_text(paid_html or "")

    windows = _count_deep(f, ("timing_windows", "future_windows", "dated_windows"))
    if not windows:
        windows = len(set(m.group(0) for m in _MONTH_YEAR_RE.finditer(paid_text)))

    areas = 0
    for key in ("cards", "life_area_judgements", "aspects"):
        node = f.get(key)
        if isinstance(node, list):
            areas = max(areas, len(node))
        elif isinstance(node, dict):
            areas = max(areas, len(node))

    remedies = _count_deep(f, ("approved_remedies", "remedies"))
    if not remedies:
        remedies = _count_deep(f, ("remedy_text",))

    # Section labels are written for the report's own rail and some of them name
    # the technique ("Ashtakavarga on today's transits"). Translate what has a
    # plain equivalent, drop what does not — this list is shown to the customer.
    sections: list[str] = []
    for raw in (meta.get("paidSections") or []):
        if not isinstance(raw, str) or not raw.strip():
            continue
        label = _dejargon(raw).strip()
        if (_JARGON_RE.search(label) or _BARE_HOUSE_RE.search(label)
                or _LABEL_JARGON_RE.search(label)):
            continue
        sections.append(label)
        if len(sections) >= 6:
            break

    inv: dict[str, Any] = {
        "dated_windows": windows,
        "life_areas": areas,
        "remedies": remedies,
        "sections": sections,
        "paid_words": len(paid_text.split()),
    }

    items: list[str] = []
    if windows:
        items.append(
            f"{_num_word(windows).capitalize()} dated window"
            f"{'s' if windows != 1 else ''} with the months named"
        )
    if areas:
        items.append(
            f"A verdict for each of {_num_word(areas)} life area"
            f"{'s' if areas != 1 else ''}, and the reasoning behind it"
        )
    if remedies:
        items.append(
            f"{_num_word(remedies).capitalize()} remed{'ies' if remedies != 1 else 'y'} "
            "chosen for your chart, not generic advice"
        )
    for s in sections:
        if len(items) >= 6:
            break
        items.append(s)
    inv["items"] = items[:6]
    return inv


# ---------------------------------------------------------------------------
# QA
# ---------------------------------------------------------------------------
def _norm_words(text: str) -> set[str]:
    return set(re.findall(r"[a-z']+", (text or "").lower()))


def _near_duplicate(a: str, b: str) -> bool:
    try:
        from qa_checks.duplicate_check import exact_duplicate
    except Exception:  # noqa: BLE001
        def exact_duplicate(x: str, y: str) -> bool:
            return (x or "").strip().lower() == (y or "").strip().lower()
    if exact_duplicate(a, b):
        return True
    wa, wb = _norm_words(a), _norm_words(b)
    if len(wa) < 6 or len(wb) < 6:
        return False
    overlap = len(wa & wb) / float(len(wa | wb))
    return overlap >= 0.75


def _plainify_prose(prose: PlainSummaryProse) -> PlainSummaryProse:
    """Translate technical wording in place rather than losing the whole draft.

    A model that writes "your 10th house" has broken the plain-English promise
    but not the finding. Rewriting the phrase keeps the reasoning; rejecting the
    draft drops us to the template fallback, which reads far worse.
    """
    prose.headline = _trim_headline(_dejargon(prose.headline or ""))
    for section in prose.sections or []:
        section.title = _dejargon(section.title)
        section.body = _dejargon(section.body)
    return prose


def _date_corpus(source: str, brief: Optional[dict]) -> str:
    """Everything the model was allowed to take a date from, lowercased.

    The brief carries ISO dates and the summary is asked to write them as
    "October 2026", so the human form of every ISO date counts as grounded —
    otherwise doing exactly as told reads as an invented date.
    """
    parts = [source or ""]
    if brief:
        parts.append(json.dumps(brief, ensure_ascii=False, default=str))
    blob = " ".join(parts)
    human = " ".join(_human_date(m.group(0)) for m in _ISO_DATE_RE.finditer(blob))
    return f"{blob} {human}".lower()


def _deletion_patterns(failures: list[str]) -> Optional[list[re.Pattern]]:
    """Patterns whose sentences can simply be cut, or None if any failure cannot.

    A score or an invented date lives in one sentence. Cutting that sentence
    keeps the rest of a good draft, where rejecting it costs every section.
    Anything else — a leak, vagueness, a duplicate — is about the whole draft.
    """
    patterns: list[re.Pattern] = []
    for fail in failures:
        head, _, detail = fail.partition(":")
        if head == "metric":
            patterns.extend(_METRIC_RES)
        elif head == "ungrounded_date" and detail:
            patterns.append(re.compile(re.escape(detail), re.I))
        elif fail == "free_date_leak":
            patterns.extend((_MONTH_YEAR_RE, _YEAR_RE, _ISO_DATE_RE))
        else:
            return None
    return patterns or None


def _strip_sentences(prose: PlainSummaryProse, patterns: list[re.Pattern]) -> bool:
    """Cut every sentence matching `patterns`. True if each section survived."""
    sections = list(prose.sections or [])
    bodies: list[str] = []
    for section in sections:
        kept = [s for s in _sentences(section.body)
                if not any(rx.search(s) for rx in patterns)]
        body = " ".join(kept).strip()
        if len(body.split()) < 10:
            return False            # nothing of substance left to keep
        bodies.append(body)
    for section, body in zip(sections, bodies):
        section.body = body
    if any(rx.search(prose.headline or "") for rx in patterns):
        prose.headline = ""
    return True


_QA_HINTS: dict[str, str] = {
    "free_date_leak": (
        "you named a month or a year — the free summary must contain no date or "
        "year at all; describe timing only as dated windows the full report names"
    ),
    "not_specific": (
        "you wrote generic astrology copy — quote the actual findings from the "
        "REPORT BRIEF (the named periods, areas, traits and verdicts)"
    ),
    "duplicate_sections": "two sections say the same thing — give each its own subject",
    "structure:locked": "include exactly one section with role 'locked'",
    "structure:cta": "include exactly one section with role 'cta'",
    "structure:cta_last": "the section with role 'cta' must come last",
    "personality_missing": (
        "for a full-chart preview, add a personal section using at least two distinct "
        "personality traits from the REPORT BRIEF before discussing the current phase"
    ),
    "empty_sections": "you returned no sections",
    "language:mismatch": "write the complete summary in the requested Roman Hindi or Roman Telugu language, not English",
}


def _qa_hint(error: str) -> str:
    """Turn a QA code into an instruction the model can actually act on."""
    if error in _QA_HINTS:
        return _QA_HINTS[error]
    head, _, detail = error.partition(":")
    if error == "jargon:bare_house_number":
        return ("you referred to a numbered house — name the area of life instead, "
                "so 'your career' rather than 'your 10th house'")
    if head == "jargon":
        return (f"you used the technical term '{detail}' — "
                "say the same thing in everyday English")
    if head == "metric":
        return (f"you quoted an internal score ('{detail}') — describe the strength "
                "in words such as strong, average or weak, and give no numbers "
                "except real dates")
    if head == "ungrounded_date":
        return (f"the date '{detail}' is not in the report — "
                "only use dates that appear in the report text")
    if head == "leak":
        return f"remove the internal term '{detail}'"
    return error


def _language_is_present(prose: PlainSummaryProse, lang: str) -> bool:
    code = str(lang or "").lower().strip()
    if code in ("hi_en", "hinglish", "hi", "hindi"):
        markers = ("aap", "aapka", "aapki", "kundli", "samay", "prashna", "sanket")
    elif code in ("te_en", "tenglish", "te", "telugu"):
        markers = ("mee", "meeku", "kundali", "samayam", "prashna", "sanket", "chupis")
    else:
        return True
    blob = " ".join(
        [prose.headline or ""]
        + [f"{s.title} {s.body}" for s in (prose.sections or [])]
    ).lower()
    return len({marker for marker in markers if re.search(rf"\b{re.escape(marker)}\b", blob)}) >= 2


def _validate(
    prose: PlainSummaryProse,
    source: str,
    *,
    kind: str = "",
    paid: bool = True,
    brief: Optional[dict] = None,
    lang: str = "en",
) -> list[str]:
    """Return QA failures. `structure:` failures are repairable, the rest are not."""
    errors: list[str] = []
    sections = list(prose.sections or [])
    bodies = [s.body for s in sections]
    blob = " ".join(f"{s.title} {s.body}" for s in sections)
    low = blob.lower()

    if not sections:
        errors.append("empty_sections")
        return errors

    if not _language_is_present(prose, lang):
        errors.append("language:mismatch")
    # Hinglish/Tenglish summaries must not leave English clauses untranslated — the
    # Friday prod gibberish "few moments of confusion" etc slipped through because
    # the marker check only required 2 Hindi words. Also catch palm fallback English
    # leak "Your right hand is read here" inside Hinglish.
    if str(lang or "").lower().strip() in ("hi_en", "hinglish", "hi", "hindi", "te_en", "tenglish", "te", "telugu"):
        gib = re.search(r"\b(few moments|losing interest|peace of mind|mental tiredness|decision fatigue|If mind|has been on your mind|may well be sitting|Your right hand is read here|Your left hand is treated)\b", low)
        if gib:
            errors.append(f"gibberish:{gib.group(0)}")

    for bad in (
        "minilm", "pyjhora", "confluence_score", "facts_hash", "schema_version",
        "internal rule", "deterministic engine", "[placeholder", "pending llm",
    ):
        if bad in low:
            errors.append(f"leak:{bad}")

    jargon = {m.group(0).lower() for m in _JARGON_RE.finditer(blob)}
    for word in sorted(jargon):
        errors.append(f"jargon:{word}")
    if _BARE_HOUSE_RE.search(blob):
        errors.append("jargon:bare_house_number")

    # An inline score cannot be deleted without wrecking the sentence, so the
    # model is asked to rewrite it rather than us patching the grammar.
    for rx in _METRIC_RES:
        m = rx.search(blob)
        if m:
            errors.append(f"metric:{m.group(0).strip()}")
            break

    # Dates in the summary must be traceable to the report or the brief.
    corpus = _date_corpus(source, brief)
    for m in _MONTH_YEAR_RE.finditer(blob):
        found = m.group(0)
        if found.lower() not in corpus:
            errors.append(f"ungrounded_date:{found}")

    # A free summary quoting a date has given away the paid half. The daily
    # reading is exempt: its own date is the subject of the page.
    if not paid and kind != "daily":
        if _MONTH_YEAR_RE.search(blob) or _YEAR_RE.search(blob):
            errors.append("free_date_leak")

    # A full-chart free preview must still feel personal. The phase and life
    # area findings are not a substitute for the reader's enduring traits.
    if not paid and kind in ("full_report", "classical_report"):
        traits = [
            str(t) for t in (brief or {}).get("personality_traits") or []
            if str(t).strip()
        ]
        if traits:
            insight_blob = " ".join(
                f"{s.title} {s.body}" for s in sections if s.role == "insight"
            )
            matched_traits = sum(
                1 for trait in traits
                if _stems(trait) & _stems(insight_blob)
            )
            if matched_traits < min(2, len(traits)):
                errors.append("personality_missing")

    tokens = _brief_tokens(brief or {})
    if tokens and not (tokens & _stems(blob)):
        errors.append("not_specific")

    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            if _near_duplicate(bodies[i], bodies[j]):
                errors.append("duplicate_sections")
                break
        else:
            continue
        break
    titles = [str(s.title or "").strip().lower() for s in sections if str(s.title or "").strip()]
    if len(titles) != len(set(titles)):
        errors.append("duplicate_sections")

    if not paid:
        roles = [s.role for s in sections]
        if roles.count("locked") != 1:
            errors.append("structure:locked")
        if roles.count("cta") != 1:
            errors.append("structure:cta")
        if roles and roles[-1] != "cta":
            errors.append("structure:cta_last")

    return errors


def _hard_failures(errors: list[str]) -> list[str]:
    return [e for e in errors if not e.startswith("structure:")]


# ---------------------------------------------------------------------------
# Locked / CTA copy
# ---------------------------------------------------------------------------
def _kind_label(kind: str) -> str:
    return {
        "full_report": "full birth-chart confluence reading",
        "classical_report": "classical Vedic reading",
        "horary": "horary question reading",
        "user_question": "natal-chart question reading",
        "palm": "palmistry reading",
        "daily": "daily personal reading",
        "numerology": "numerology reading",
        "kundali_match": "kundali compatibility reading",
        "muhurat": "muhurat day check",
        "btr": "birth-time rectification reading",
    }.get(kind or "", "astrology reading")


def _locked_headline(kind: str, lang: str = "en") -> str:
    lang_code = str(lang or "").lower().strip()
    if lang_code in ("hi_en", "hinglish", "hi", "hindi"):
        return "Poori Reading Mein Kya Shamil Hai"
    if lang_code in ("te_en", "tenglish", "te", "telugu"):
        return "Sampoorna Reading Lo Emi Untundi"
    if kind == "palm":
        return "What the full reading adds"
    if kind == "daily":
        return "What the full daily forecast adds"
    return "What the full report adds"


def _locked_section(kind: str, inventory: Optional[dict], lang: str = "en") -> dict:
    """Concrete account of the paid half, built from counts only."""
    inv = inventory or {}
    items = [i for i in (inv.get("items") or []) if isinstance(i, str)]
    lang_code = str(lang or "").lower().strip()
    # Translate inventory items for Hinglish/Tenglish — English "Two dated windows..." is gibberish in Roman Hindi
    def _hi_items(src: list[str]) -> list[str]:
        out: list[str] = []
        for it in src:
            low = it.lower()
            if "dated window" in low:
                # Extract number word
                m = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\b", low)
                num = m.group(1).capitalize() if m else "Kuch"
                hi_num = {"One":"Ek","Two":"Do","Three":"Teen","Four":"Chaar","Five":"Paanch","Six":"Cheh","Seven":"Saath","Eight":"Aath","Nine":"Nau","Ten":"Das"}.get(num, num)
                out.append(f"{hi_num} dated windows jismein mahine ke naam hain")
            elif "life area" in low:
                m = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|twelve)\b", low)
                num = m.group(1).capitalize() if m else "Kuch"
                hi_num = {"One":"Ek","Two":"Do","Three":"Teen","Four":"Chaar","Five":"Paanch","Six":"Cheh","Seven":"Saath","Eight":"Aath","Twelve":"Barah"}.get(num, num)
                out.append(f"{hi_num} life areas ke liye verdict aur uska karan")
            elif "remed" in low:
                m = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\b", low)
                num = m.group(1).capitalize() if m else "Kuch"
                hi_num = {"One":"Ek","Two":"Do","Three":"Teen","Four":"Chaar","Five":"Paanch","Six":"Cheh","Seven":"Saath","Eight":"Aath"}.get(num, num)
                out.append(f"{hi_num} upay jo aapki kundli ke liye chune gaye hain")
            else:
                out.append(_dejargon(it))
        return out
    def _te_items(src: list[str]) -> list[str]:
        out: list[str] = []
        for it in src:
            low = it.lower()
            if "dated window" in low:
                m = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\b", low)
                num = m.group(1).capitalize() if m else "Konni"
                te_num = {"One":"Oka","Two":"Rendu","Three":"Moodu","Four":"Nalugu","Five":"Aidu","Six":"Aaru","Seven":"Edu","Eight":"Enimidi"}.get(num, num)
                out.append(f"{te_num} dated windows lo nelala perlu unnai")
            elif "life area" in low:
                m = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|twelve)\b", low)
                num = m.group(1).capitalize() if m else "Konni"
                te_num = {"One":"Oka","Two":"Rendu","Eight":"Enimidi","Twelve":"Pannendu"}.get(num, num)
                out.append(f"{te_num} life areas kosam verdict mariyu karanam")
            elif "remed" in low:
                m = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\b", low)
                num = m.group(1).capitalize() if m else "Konni"
                te_num = {"One":"Oka","Two":"Rendu","Eight":"Enimidi"}.get(num, num)
                out.append(f"{te_num} upayamulu mee kundali kosam enchukobaddayi")
            else:
                out.append(_dejargon(it))
        return out
    if lang_code in ("hi_en", "hinglish", "hi", "hindi"):
        lead = {
            "palm": "Aapne apne haathon ka aakar aur swabhav padh liya hai. Baaki reading taiyar hai:",
            "horary": "Prashna kundli ka poora faisla taiyar hai. Abhi yeh hissa locked hai:",
            "user_question": "Is jawab ke peeche ka poora vishleshan taiyar hai. Abhi yeh hissa locked hai:",
            "daily": "Aaj ka poora forecast taiyar hai. Abhi yeh hissa locked hai:",
        }.get(kind, "Aapki kundli ka poora vishleshan taiyar hai. Abhi yeh hissa locked hai:")
        hi_items_list = _hi_items(items)
        body = lead + (" " + "; ".join(hi_items_list[:4]) + "." if hi_items_list else
                       " Ismein detailed timing, life-area analysis aur chart-specific upay shamil hain.")
        return {"title": _locked_headline(kind, lang), "body": body[:900], "role": "locked"}
    if lang_code in ("te_en", "tenglish", "te", "telugu"):
        lead = {
            "palm": "Mee chethula shape mariyu swabhavam gurinchi chusaru. Migilina reading siddham ga undi:",
            "horary": "Prashna kundali yokka sampoorna theerpu siddham ga undi. Ippudu ee bhaagam locked:",
            "user_question": "Ee samadhanam venuka unna poorthi vishleshana siddham ga undi. Ippudu ee bhaagam locked:",
            "daily": "Eeroju poorthi forecast siddham ga undi. Ippudu ee bhaagam locked:",
        }.get(kind, "Mee kundali yokka poorthi vishleshana siddham ga undi. Ippudu ee bhaagam locked:")
        te_items_list = _te_items(items)
        body = lead + (" " + "; ".join(te_items_list[:4]) + "." if te_items_list else
                       " Indulo detailed timing, life-area analysis mariyu chart-specific upayamulu unnai.")
        return {"title": _locked_headline(kind, lang), "body": body[:900], "role": "locked"}
    lead = {
        "palm": "You have read the shape of your hands and what they say about who you are. "
                "The rest of your reading is written and waiting:",
        "horary": "The chart has been judged in full. Held back for now:",
        "user_question": "The working behind this answer is complete. Held back for now:",
        "daily": "Today's full forecast is ready. Held back for now:",
    }.get(kind, "Your chart has already been read in full. Held back for now:")

    if items:
        body = lead + " " + "; ".join(items[:4]) + "."
    else:
        body = {
            "palm": "Your complete life timeline, the age chapters still ahead, every line "
                    "and mount marking, and the remedies drawn from them are written and waiting.",
            "horary": "The full judgment, the planetary working behind it, the dated timing "
                      "windows and the specific guidance are written and waiting.",
            "user_question": "The classical verdict, the dated opening windows, the milestone "
                             "timeline and the remedies chosen for your chart are written and waiting.",
            "daily": "Your full Moon-transit timing, the running period milestones and today's "
                     "remedies are written and waiting.",
        }.get(kind, "The complete life-area verdicts, the dated timeline and the remedies "
                    "chosen for your chart are written and waiting.")

    words = inv.get("paid_words")
    if isinstance(words, int) and words > 400:
        body += f" It runs to roughly {int(round(words / 100.0)) * 100:,} words."
    return {"title": _locked_headline(kind, lang), "body": body[:900], "role": "locked"}


def _cta_section(kind: str, lang: str = "en") -> dict:
    lang_code = str(lang or "").lower().strip()
    if lang_code in ("hi_en", "hinglish", "hi", "hindi"):
        body = {
            "palm": "Poori reading unlock karke age-by-age timeline, dono haathon ke nishaan aur unke upay dekhein. Yeh aapke account mein rahegi.",
            "daily": "Full daily access subscribe karein; aaj ka forecast aur har agle din ki reading turant khul jayegi.",
            "horary": "Poora report unlock karke faisla, timing windows aur margdarshan dekhein. Yeh aapke account mein rahega.",
        }.get(
            kind,
            "Poori report unlock karein aur dated windows, life-area faisle aur aapki kundli ke upay dekhein. Yeh aapke account mein rahegi.",
        )
        title = "Daily Access Subscribe Karein" if kind == "daily" else "Poori Reading Unlock Karein"
        return {"title": title, "body": body, "role": "cta"}
    if lang_code in ("te_en", "tenglish", "te", "telugu"):
        body = {
            "palm": "Sampoorna reading unlock chesi age-by-age timeline, rendu chethula markings mariyu vatiki sambandhinchina upayamulu chudandi. Idi mee account lo untundi.",
            "daily": "Full daily access subscribe cheyandi; eeroju forecast mariyu prati taruvatha roju reading ventane open avuthayi.",
            "horary": "Poorthi report unlock chesi theerpu, timing windows mariyu margadarshanam chudandi. Idi mee account lo untundi.",
        }.get(
            kind,
            "Sampoorna report unlock chesi dated windows, life-area theerpulu mariyu mee kundali upayamulu chudandi. Idi mee account lo untundi.",
        )
        title = "Daily Access Subscribe Cheyandi" if kind == "daily" else "Sampoorna Reading Unlock Cheyandi"
        return {"title": title, "body": body, "role": "cta"}
    body = {
        "palm": "Unlock the full reading to see your timeline age by age, every marking on "
                "both hands, and the remedies that go with them. It stays in your account.",
        "daily": "Subscribe for full daily access and today's forecast opens straight away, "
                 "along with every morning after it.",
        "horary": "Unlock the full report and the complete judgment, the timing windows and "
                  "the guidance open straight away. It stays in your account.",
        "user_question": "Unlock the full answer and the timing window and practical steps for "
                         "your question open straight away. It stays in your account.",
    }.get(
        kind,
        "Unlock the full report and everything above opens straight away — the dated windows, "
        "the area-by-area verdicts and the remedies chosen for your chart. It stays in your account.",
    )
    title = "Subscribe for full daily access" if kind == "daily" else "Unlock the full reading"
    return {"title": title, "body": body, "role": "cta"}


def _repair_free_sections(
    sections: list[dict], kind: str, inventory: Optional[dict], lang: str = "en"
) -> list[dict]:
    """Guarantee a free summary closes on a locked account and one CTA."""
    out = [s for s in sections if (s.get("role") or "insight") == "insight"]
    locked = [s for s in sections if s.get("role") == "locked"]
    cta = [s for s in sections if s.get("role") == "cta"]
    out.append(locked[0] if locked else _locked_section(kind, inventory, lang))
    out.append(cta[0] if cta else _cta_section(kind, lang))
    return out


# ---------------------------------------------------------------------------
# Fallback — brief-driven, LLM off or QA rejected
# ---------------------------------------------------------------------------
def _sec(title: str, body: str, role: str = "insight") -> Optional[dict]:
    body = re.sub(r"\s{2,}", " ", str(body or "")).strip()
    if len(body) < 20:
        return None
    return {"title": title, "body": body[:900], "role": role}


def _join_sentences(parts: list[str], *, min_words: int = 1) -> str:
    out: list[str] = []
    for p in parts:
        p = _tidy(_clip(p, 400))
        if not p or len(p.split()) < min_words:
            continue
        out.append(p)
    return " ".join(out)


def _polish(sections: list[dict], *, kind: str, paid: bool) -> list[dict]:
    """Last pass over deterministic prose.

    The locked and CTA sections are our own copy and are left alone; everything
    else came out of the report body and gets the same hygiene the LLM output is
    held to, so the two paths cannot disagree about what a reader may see.
    """
    out: list[dict] = []
    for s in sections:
        if s.get("role") in ("locked", "cta"):
            out.append(s)
            continue
        body = _drop_bad_sentences(
            s.get("body") or "", free=not paid, allow_dates=(kind == "daily"),
        )
        body = _tidy(body)
        if len(body) >= 20:
            out.append({**s, "body": body[:900]})
    return out


def _first_sentences(text: str, count: int, *, free: bool, allow_dates: bool = False) -> str:
    cleaned = _drop_bad_sentences(text, free=free, allow_dates=allow_dates)
    return " ".join(_sentences(cleaned)[:count])


def _fallback_from_palm_text(
    text: str, *, paid: bool = True, lang: str = "en"
) -> list[dict]:
    """Extract personalized personality traits, thumb decision style, and strengths for palmistry."""
    lang_code = str(lang or "").lower().strip()
    is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")
    # For Hinglish/Tenglish, English report sentences produce code-mixed gibberish
    # ("If mind & intellect has been on your mind..."). Use brief-driven Hindi
    # templates directly instead of slicing English report text.
    if is_hinglish or is_tenglish:
        # Callers pass brief via _fallback_sections; this helper only has text,
        # so return a minimal Hindi fallback that _fb_palm will enrich with brief.
        # Keep this path English-free; the Hindi palm fallback is built in _fb_palm.
        return []
    text = _drop_bad_sentences(text, free=not paid)
    if not text:
        return []
    sentences = [s for s in _sentences(text) if len(s) > 18]
    if not sentences:
        return []
    titles = (
        ("Swabhav Aur Core Temperament", "Mukhya Kshamta Aur Nirnay Shailee",
         "Mukhya Rekhaon Aur Jeevan Margdarshan")
        if is_hinglish else
        ("Swabhavam Mariyu Core Temperament", "Mukhya Kshamathalu Mariyu Nirnaya Shailee",
         "Mukhya Rekhalu Mariyu Jeevitha Margadarshanam")
        if is_tenglish else
        ("Personality & Core Temperament", "Innate Strengths & Decision Style",
         "Major Lines & Life Guidance")
    )

    shape_sentences: list[str] = []
    thumb_sentences: list[str] = []
    other_sentences: list[str] = []

    for s in sentences:
        low = s.lower()
        if any(w in low for w in ("hand shape", "air hand", "fire hand", "water hand", "earth hand", "thinker", "strategist", "communicator", "monotony", "receptive palm", "slender fingers", "square palm", "practical builder", "spontaneous", "intuitive")):
            shape_sentences.append(s)
        elif any(w in low for w in ("thumb", "governing thumb", "will and logic", "will section", "logic section", "receptive thumb", "commanding thumb", "decision", "negotiation", "phalanx", "open-set")):
            thumb_sentences.append(s)
        elif not any(w in low for w in ("unlock", "paywall", "upaya", "targeted remedies")):
            other_sentences.append(s)

    sections: list[dict] = []
    if shape_sentences:
        sections.append({
            "title": titles[0],
            "body": " ".join(shape_sentences[:4])[:900],
            "role": "insight",
        })

    if thumb_sentences:
        sections.append({
            "title": titles[1],
            "body": " ".join(thumb_sentences[:4])[:900],
            "role": "insight",
        })

    if paid and other_sentences:
        line_sentences = [s for s in other_sentences if any(w in s.lower() for w in ("line", "mount", "vitality", "head line", "heart line", "fate line", "career", "chapter"))]
        if line_sentences:
            sections.append({
                "title": titles[2],
                "body": " ".join(line_sentences[:4])[:900],
                "role": "insight",
            })

    if not sections:
        # The free palm summary earns its keep on who the reader is; a third
        # chunk of sliced body text only picks up the page around the reading.
        titles = (
            (titles[0], titles[1]) if not paid else
            (titles[0], titles[1], titles[2],
             "Urja Aur Vyavaharik Margdarshan" if is_hinglish
             else "Urja Mariyu Vyavaharik Margadarshanam" if is_tenglish
             else "Energy & Practical Focus")
        )
        limit = min(2 if not paid else 4, len(titles))
        per = max(2, min(4, (len(sentences) + limit - 1) // limit))
        idx = 0
        for title in titles:
            if idx >= len(sentences) or len(sections) >= limit:
                break
            chunk = sentences[idx:idx + per]
            idx += per
            if chunk:
                sections.append({"title": title, "body": " ".join(chunk)[:900], "role": "insight"})

    return sections


def _fallback_from_report_text(
    text: str, *, max_sections: int = 5, paid: bool = True, lang: str = "en"
) -> list[dict]:
    """Last resort when neither the LLM nor the brief gave us anything usable."""
    text = _drop_bad_sentences(text, free=not paid)
    if len(text) < 280:
        return []
    sentences = [s for s in _sentences(text) if len(s) > 24]
    if len(sentences) < 2:
        return []
    lang_code = str(lang or "").lower().strip()
    if lang_code in ("hi_en", "hinglish", "hi", "hindi"):
        titles = (
            ("Seedha Vishleshan", "Vartaman Grah Prabhav", "Mukhya Samay Sanket",
             "Urja Aur Vyaktigat Dhyan", "Margdarshan Aur Upay", "Agla Kadam")
            if paid else
            ("Prarambhik Sthiti Ka Vishleshan", "Vartaman Grah Prabhav",
             "Mukhya Jyotishiya Sanket")
        )
    elif lang_code in ("te_en", "tenglish", "te", "telugu"):
        titles = (
            ("Direct Vishleshana", "Prasthutha Graha Prabhavam", "Mukhya Timing Sankethalu",
             "Urja Mariyu Vyaktigatha Dhyanam", "Margadarshanam Mariyu Upayamulu", "Taruvatha Adugu")
            if paid else
            ("Prarambha Sthithi Vishleshana", "Prasthutha Graha Prabhavam",
             "Mukhya Jyotishya Sankethalu")
        )
    elif paid:
        titles = (
            "Direct answer & overview", "Planetary phase & influences", "Key milestone windows",
            "Energy & personal focus", "Guidance & remedies", "Recommended action",
        )
    else:
        titles = (
            "Initial situation assessment", "Current planetary influences", "Key astrological factors",
        )
    limit = min(max_sections, len(titles))
    per = max(2, min(4, (len(sentences) + limit - 1) // limit))
    sections: list[dict] = []
    idx = 0
    for title in titles:
        if idx >= len(sentences) or len(sections) >= limit:
            break
        chunk = sentences[idx:idx + per]
        idx += per
        if chunk:
            sections.append({"title": title, "body": " ".join(chunk)[:900], "role": "insight"})
    return sections


def _build_chart_grounded_full_report_sections(
    brief: dict, *, paid: bool, lang: str = "en"
) -> list[dict]:
    lang_code = str(lang or "").lower()
    is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")

    lagna = brief.get("classical_lagna") or "Aries"
    moon = brief.get("classical_moon") or "Moon"
    nakshatra = f" ({brief['classical_nakshatra']})" if brief.get("classical_nakshatra") else ""
    lord = brief.get("classical_lord") or "Sun"
    ak = brief.get("classical_ak") or "Moon"
    amk = brief.get("classical_amk") or "Jupiter"
    dasha = brief.get("classical_dasha") or "current planetary cycle"
    next_dasha = brief.get("next_dasha") or "upcoming cycle"

    out: list[dict] = []

    if is_hinglish:
        # 1. Archetype
        out.append(_sec(
            "1. Mool Swabhav Aur Jeevan Disha",
            f"Aapka {lagna} Lagna aur {moon} Chandra{nakshatra} hai. Lagnesh {lord} aur Atmakaraka {ak} aapko strategic vision, teekshna buddhi aur nischit lakshya ki disha mein aage badhate hain. Dhairya aur consistent mehnat aapki mukhya taakat hai."
        ))
        # 2. Current Chapter
        out.append(_sec(
            "2. Chalu Dasha Aur Vartaman Chapter",
            f"Vartaman mein aap {dasha} ke daur se guzar rahe hain. Yeh samay aantarik mazbooti, purani rukawaton ko suljhane aur aane wale vistar ke liye zameen tayyar karne ka hai."
        ))
        # 3. Career
        out.append(_sec(
            "3. Career, Rozgar Aur Pratishtha",
            f"10th house aur Amatyakaraka {amk} ke prabhav se aapko structured responsibilities, management aur executive roles mein vishesh safalta milti hai. Consistency aur credibility se sthir authority banti hai."
        ))
        # 4. Wealth
        out.append(_sec(
            "4. Dhan, Bachat Aur Aarthik Vriddhi",
            "Aapki aarthik sthirta anushasit bachat, structured investments aur strategic planning se majboot hoti hai. Speculative jaldbaazi ke bajay steady compounding labhkari hai."
        ))
        # 5. Relationships
        out.append(_sec(
            "5. Rishte, Vivah Aur Parivarik Santulan",
            "7th house aur Navamsha (D9) sambandhon mein aapsi samman, spasht communication aur bhavnatmak paripakvata ki maang karte hain. Understanding se parivarik jeevan mein santulan bana rehta hai."
        ))
        # 6. Health
        out.append(_sec(
            "6. Swasthya, Urja Aur Daily Routine",
            f"Sharirik urja Lagnesh {lord} dwara sanchalit hai. Workload ke dauran regular diet, hydration aur walking routine banaye rakhne se stamina mazboot rehta hai."
        ))
        # 7. Next Turning point
        if paid or next_dasha:
            out.append(_sec(
                "7. Aane Wala Turning Point Aur Disha",
                f"Agla mukhya breakthrough window {next_dasha} Antardasha mein khulta hai, jisme pichli mehnat ka uchit samman aur aarthik unnati ka yog banta hai."
            ))
    elif is_tenglish:
        # 1. Archetype
        out.append(_sec(
            "1. Moola Swabhavam Mariyu Jeevitha Disha",
            f"Mee {lagna} Lagnam mariyu {moon} Chandra{nakshatra} unnai. Lagnaadhipathi {lord} mariyu Atmakaraka {ak} meeku strategic vision mariyu lakshyam vaipu nadipisthundi. Patience mariyu regular effort mee mukhya balam."
        ))
        # 2. Current Chapter
        out.append(_sec(
            "2. Nadusthuna Dasha Mariyu Vartamana Chapter",
            f"Prasthutam meeru {dasha} phase lo unnar. Ee samayam lo internal consolidation, patha samasyalanu sari cheyadam mariyu future growth kosam foundation veyadam mukhyam."
        ))
        # 3. Career
        out.append(_sec(
            "3. Career, Udyogam Mariyu Gouravam",
            f"10th house mariyu Amatyakaraka {amk} prabhavam valla meeku structured responsibilities, management mariyu executive roles lo manchi vijayam labhisthundi."
        ))
        # 4. Wealth
        out.append(_sec(
            "4. Dhanam, Podupu Mariyu Aarthika Vriddhi",
            "Mee aarthika sthiratha regular savings mariyu structured financial planning valla peruguthundi. Sudden risks kante safe growth manchidi."
        ))
        # 5. Relationships
        out.append(_sec(
            "5. Sambandhalu, Vivaham Mariyu Kutumba Samathulyatha",
            "7th house mariyu Navamsha (D9) relationship lo mutual respect, spashthamaina communication mariyu emotional maturity ni korukuntundi."
        ))
        # 6. Health
        out.append(_sec(
            "6. Aarogyam, Urja Mariyu Daily Routine",
            f"Vitality Lagnaadhipathi {lord} aadharamga untundi. Regular routine, hydration mariyu mindful habits tho health balance ga untundi."
        ))
        # 7. Next Turning point
        if paid or next_dasha:
            out.append(_sec(
                "7. Munde Vache Turning Point Mariyu Margadarshanam",
                f"Mee next breakthrough window {next_dasha} Antardasha lo start avuthundi, ee phase lo progress kanipisthundi."
            ))
    else:
        # 1. Archetype
        out.append(_sec(
            "1. Core Constitutional Archetype & Life Drive",
            f"With {lagna} rising and Moon in {moon}{nakshatra}, governed by Lagna lord {lord} and Atmakaraka {ak}, your chart establishes an ambitious, intellectual, and principled constitutional archetype. Your natural path rewards strategic independence, analytical mastery, and self-reliance."
        ))
        # 2. Current Chapter
        out.append(_sec(
            "2. Active Operating Chapter & Planetary Dynamics",
            f"You are currently traversing the {dasha}. This is a foundational realignment phase dedicated to restructuring internal priorities, resolving legacy distractions, and preparing the structural runway for upcoming expansion."
        ))
        # 3. Career
        out.append(_sec(
            "3. Career, Authority & Vocational Growth",
            f"Your 10th house dynamics and Amatyakaraka {amk} indicate strong capabilities in specialized execution, organizational management, and executive responsibility. Sustained perseverance creates enduring institutional authority."
        ))
        # 4. Wealth
        out.append(_sec(
            "4. Wealth, Income & Material Expansion",
            "Financial accumulation in this chart thrives on disciplined compounding, strategic asset allocation, and structured enterprise rather than volatile speculation."
        ))
        # 5. Relationships
        out.append(_sec(
            "5. Relationships, Marriage & Alliances",
            "The 7th house and Navamsha (D9) framework emphasize partnerships built on mutual intellectual respect, transparent communication, and shared foundational values."
        ))
        # 6. Health
        out.append(_sec(
            "6. Vitality, Health & Energy Management",
            f"Constitutional stamina is sustained by Lagna lord {lord}. Maintaining balanced digestive rhythms, hydration, and proactive stress regulation provides optimal vitality during peak workloads."
        ))
        # 7. Next Turning point
        if paid or next_dasha:
            out.append(_sec(
                "7. Strategic Roadmap & Key Turning Points",
                f"The primary forward catalyst activates as you transition towards the {next_dasha} cycle, unlocking decisive professional recognition and material stabilization."
            ))

    return [s for s in out if s]


def _fb_full_report(brief: dict, *, paid: bool, lang: str = "en") -> list[dict]:
    if brief.get("classical_lagna"):
        return _build_chart_grounded_full_report_sections(brief, paid=paid, lang=lang)

    lang_code = str(lang or "").lower()
    is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")
    out: list[Optional[dict]] = []
    if brief.get("classical_lagna") and not any(
        brief.get(k) for k in ("current_phase_tone", "personality_traits", "chart_foundations")
    ):
        if is_hinglish:
            body = (
                f"Aapki kundli mein {brief['classical_lagna']} Lagna aur "
                f"{brief.get('classical_moon') or 'Chandra'} Chandra hai. "
                f"Vartaman dasha {brief.get('classical_dasha') or 'chal rahi dasha'} "
                "aapke jeevan ke vartaman adhyay ko prabhavit karti hai."
            )
            out.append(_sec("Aapki Classical Kundli Ka Saransh", body))
        elif is_tenglish:
            body = (
                f"Mee kundali lo {brief['classical_lagna']} Lagnam mariyu "
                f"{brief.get('classical_moon') or 'Chandra'} Chandra unnai. "
                f"Prasthutha dasha {brief.get('classical_dasha') or 'nadusthuna dasha'} "
                "mee jeevitha vartamana phase ni prabhavitham chesthondi."
            )
            out.append(_sec("Mee Classical Kundali Saramsam", body))
        else:
            body = (
                f"Your chart has {brief['classical_lagna']} rising with "
                f"{brief.get('classical_moon') or 'the Moon'} in focus. "
                f"The current {brief.get('classical_dasha') or 'planetary period'} "
                "sets the tone of the chapter you are living through."
            )
            out.append(_sec("Your classical chart in brief", body))
    tone = brief.get("current_phase_tone")
    notes = brief.get("current_phase_notes") or []
    direction = str(brief.get("current_phase_direction") or "").lower()
    if tone or notes:
        if is_hinglish:
            lead = {
                "support": "Aapka vartaman samay aapke paksh mein kaam kar raha hai.",
                "caution": "Vartaman samay aage badhne ke liye jaldbaazi ke bajay dhairya maangta hai.",
            }.get(direction, "")
        elif is_tenglish:
            lead = {
                "support": "Mee prasthutha samayam meeku anukulam ga pani chesthondi.",
                "caution": "Prasthutha samayam lo aathram kante patience tho munduki vellali.",
            }.get(direction, "")
        else:
            lead = {
                "support": "The stretch you are in is working with you rather than against you.",
                "caution": "The stretch you are in asks for patience more than push.",
            }.get(direction, "")
        # phase_tone is sometimes a bare adjective ("supportive"); on its own it
        # reads as a stray word, and the lead sentence already carries it.
        if tone and len(tone.split()) < 4:
            tone = ""
        parts = [lead, tone] + list(notes[:2])
        if paid and brief.get("current_phase_ends"):
            if is_hinglish:
                parts.append(f"Yeh adhyay {_human_date(brief['current_phase_ends'])} tak chalega.")
            elif is_tenglish:
                parts.append(f"Ee adhyayam {_human_date(brief['current_phase_ends'])} varaku untundi.")
            else:
                parts.append(f"This chapter runs to {_human_date(brief['current_phase_ends'])}")
        if is_hinglish:
            sec_title = "Aapka Vartaman Samay (Current Phase)"
        elif is_tenglish:
            sec_title = "Mee Vartamana Samayam (Current Phase)"
        else:
            sec_title = "Where you are right now"
        out.append(_sec(sec_title, _join_sentences(parts)))

    traits = brief.get("personality_traits") or []
    if traits:
        if is_hinglish:
            sec_title = "Aapke Swabhav Aur Kundli Ke Mukhya Lakshana"
        elif is_tenglish:
            sec_title = "Mee Swabhavam Mariyu Kundali Mukhya Lakshanalu"
        else:
            sec_title = "What your chart says about you"
        out.append(_sec(
            sec_title,
            _join_sentences(list(traits[:6] if paid else traits[:3])),
        ))

    foundations = [
        f"{item.get('chart')}: {_clip(item.get('outlook'), 180)}"
        for item in (brief.get("chart_foundations") or [])
        if isinstance(item, dict) and item.get("chart") and item.get("outlook")
    ]
    if foundations:
        if is_hinglish:
            sec_title = "Aapki Kundli Ke Mukhya Aadhar (Vargas)"
        elif is_tenglish:
            sec_title = "Mee Kundali Mukhya Aadharalu (Vargas)"
        else:
            sec_title = "What your key chart foundations say"
        out.append(_sec(
            sec_title,
            _join_sentences(foundations),
        ))

    areas = [a for a in (brief.get("life_areas") or []) if isinstance(a, dict)]
    if areas and paid:
        picked = areas[:5]
        lines = [f"{a.get('area')}: {a.get('outlook')}" for a in picked if a.get("outlook")]
        if lines:
            if is_hinglish:
                sec_title = "Jeevan Ke Mukhya Kshetra"
            elif is_tenglish:
                sec_title = "Jeevitha Mukhya Rangalu"
            else:
                sec_title = "How each part of life reads"
            out.append(_sec(sec_title, _join_sentences(lines)))

    pressure = brief.get("areas_under_pressure") or []
    if pressure:
        if is_hinglish:
            sec_title = "Chunauti Aur Dabav Wale Kshetra"
            body = ("Kundli in kshetron par vishesh dabav darshati hai: " + ", ".join(pressure[:3])
                    + ". In kshetron mein dhairya aur niyamit prayas se hi behtar parinam milenge.")
        elif is_tenglish:
            sec_title = "Prathyeka Dhyanam Pettalsina Rangalu"
            body = ("Kundali ee vishayala meeda prathyeka pressure chupisthondi: " + ", ".join(pressure[:3])
                    + ". Ee vishayallo patience mariyu regular effort tho manchi results vasthayi.")
        else:
            sec_title = "Where the pressure sits"
            body = ("The chart puts the most strain on " + ", ".join(pressure[:3])
                    + ". That is where steady effort pays back the most, and where "
                      "pushing hard for a fast result tends to cost you.")
        out.append(_sec(sec_title, body))

    if paid:
        windows = [w for w in (brief.get("dated_windows") or []) if isinstance(w, dict)]
        if is_hinglish:
            lines = [
                f"{_label(w.get('label')) or 'Ek window'} {_human_date(w.get('start'))} ko shuru hota hai"
                + (f" aur {_human_date(w.get('end'))} tak chalta hai" if w.get("end") else "")
                for w in windows[:4] if w.get("start")
            ]
            sec_title = "Mahatvapurna Dates Aur Samay Chakra"
        elif is_tenglish:
            lines = [
                f"{_label(w.get('label')) or 'Oka timing window'} {_human_date(w.get('start'))} lo start avuthundi"
                + (f" mariyu {_human_date(w.get('end'))} varaku untundi" if w.get("end") else "")
                for w in windows[:4] if w.get("start")
            ]
            sec_title = "Mukhya Dates Mariyu Timing Windows"
        else:
            lines = [
                f"{_label(w.get('label')) or 'A window'} opens {_human_date(w.get('start'))}"
                + (f" and runs to {_human_date(w.get('end'))}" if w.get("end") else "")
                for w in windows[:4] if w.get("start")
            ]
            sec_title = "The dates that matter"
        if lines:
            out.append(_sec(sec_title, _join_sentences(lines)))

    return [s for s in out if s]


def _fb_user_question(brief: dict, meta: dict, *, paid: bool, lang: str = "en") -> list[dict]:
    lang_code = str(lang or "").lower().strip()
    is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")
    out: list[Optional[dict]] = []
    q = _tidy(_clip(brief.get("question") or meta.get("question") or meta.get("area"), 200))
    q = q.rstrip(".?!")
    finding = _tidy(_clip(brief.get("finding"), 400))
    area = _clip(brief.get("life_area"), 80)
    direction = str(brief.get("direction") or "").lower()

    if is_hinglish:
        if q:
            body = f"Aapke prashna ({q}) par kundli spasht sanket deti hai: {finding}"
        else:
            body = f"Aapke prashna par kundli ka vishleshan: {finding}"
        if paid and brief.get("breakthrough_window"):
            body += f" Sabse majboot anukool samay {_tidy(brief['breakthrough_window'])} ke aas-paas banta hai."
        out.append(_sec("Seedha Uttar", body))

        if direction in ("support", "caution", "mixed"):
            note = {
                "support": "Kundli ka bal is disha mein aapke saath hai, jisse kiye gaye prayas safal hone ke aache asar hain.",
                "caution": "Kundli saavdhani baratne ka sanket deti hai. Parinam sambhav hai par thoda samay aur dhairya lag sakta hai.",
                "mixed": "Kundli is par mili-juli sthiti darshati hai. Santulit kadam uthana zaroori hai.",
            }[direction]
            if area:
                note = f"Yeh aapke {area} kshetra se juda hai. " + note
            out.append(_sec("Vyavaharik Margdarshan", note))
    elif is_tenglish:
        if q:
            body = f"Mee prashna ({q}) meeda kundali spashtamaina sankethalu isthondi: {finding}"
        else:
            body = f"Mee prashnaku kundali vishleshana: {finding}"
        if paid and brief.get("breakthrough_window"):
            body += f" Mukhya anukoolamaina breakthrough window {_tidy(brief['breakthrough_window'])} daggara untundi."
        out.append(_sec("Direct Samadhanam", body))

        if direction in ("support", "caution", "mixed"):
            note = {
                "support": "Kundali balam meeku anukulam ga undi, meeru chese prayathnalu manchi phalithalanu isthayi.",
                "caution": "Kundali jagratthaga undalsindi ga chupisthondi. Time mariyu patience tho results vasthayi.",
                "mixed": "Kundali ee vishayam lo mixed current chupisthondi. Balanced ga decisions thesukondi.",
            }[direction]
            if area:
                note = f"Idi mee {area} vishayaniki sambandhinchindi. " + note
            out.append(_sec("Mee Kosam Margadarshanam", note))
    else:
        low = finding.lower()
        if low.startswith(("the chart", "your chart", "regarding", "on your question")):
            body = finding
        elif q:
            body = f"On your question about {q}, the chart reads: {finding}"
        else:
            body = f"On the question you asked, the chart reads: {finding}"
        if paid and brief.get("breakthrough_window"):
            body += f" The strongest opening sits around {_tidy(brief['breakthrough_window'])}"
        out.append(_sec("The direct answer", body))

        if direction in ("support", "caution", "mixed"):
            note = {
                "support": "The weight of the chart is behind this, which means effort you put in "
                           "now tends to land rather than stall.",
                "caution": "The chart asks for care here. The result is reachable, but not on the "
                           "timeline you would pick, and pushing early tends to cost you.",
                "mixed": "The chart is genuinely split on this. Part of it supports you and part "
                         "of it holds you back, so the outcome turns on how you play it.",
            }[direction]
            if area:
                note = f"This sits in your {area.lower()} area. " + note
            out.append(_sec("What that means in practice", note))

    return [s for s in out if s]


def _fb_horary(brief: dict, meta: dict, *, paid: bool, lang: str = "en") -> list[dict]:
    lang_code = str(lang or "").lower().strip()
    is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")
    out: list[Optional[dict]] = []
    q = _clip(brief.get("question") or meta.get("question"), 200).rstrip(".?!")
    subject = _clip(brief.get("subject"), 120)

    if not paid:
        if is_hinglish:
            body = f"Aapka prashna{(' ' + q) if q else ''} ke baare mein hai."
            if subject:
                body += f" Prashna kundli {subject} par kendrit hai."
            body += " Poora prashna kundli faisla report mein taiyar hai."
            out.append(_sec("Prashna Ka Vishleshan", body))
        elif is_tenglish:
            body = f"Mee prashna{(' ' + q) if q else ''} gurinchi."
            if subject:
                body += f" Prashna kundali {subject} meeda focus chesthondi."
            body += " Sampoorna theerpu report lo siddham ga undi."
            out.append(_sec("Prashna Vishleshana", body))
        else:
            body = f"Your question is{(' about ' + q) if q else ''}."
            if subject:
                body += f" The reading is focused on {subject.lower()}."
            body += " The full horary judgment is prepared in the report."
            out.append(_sec("What the chart is examining", body))
        return [s for s in out if s]

    verdict = _clip(brief.get("verdict") or "Open", 120)
    conf = _clip(brief.get("confidence") or "moderate", 40)
    if is_hinglish:
        body = f"Aapke prashna{(' — ' + q) if q else ''} par prashna kundli ka faisla: {verdict}."
        if conf:
            body += f" Is faisle par vishwas level {conf} hai."
        out.append(_sec("Prashna Ka Faisla", body))
    elif is_tenglish:
        body = f"Mee prashna{(' — ' + q) if q else ''} meeda prashna kundali theerpu: {verdict}."
        if conf:
            body += f" Ee theerpuku nambakam {conf} ga undi."
        out.append(_sec("Prashna Theerpu", body))
    else:
        body = f"On your question{(' — ' + q) if q else ''}, the moment chart reads: {verdict}."
        if conf:
            body += f" The chart is {conf} in saying so."
        if subject:
            body += f" It is reading {subject}."
        out.append(_sec("The answer", body))

    fav = brief.get("favourable")
    if is_hinglish:
        if fav is True:
            out.append(_sec(
                "Kaise Aage Badhein",
                "Samay aapke anukool hai, isliye turant thos kadam uthana faydemand rahega.",
            ))
        elif fav is False:
            out.append(_sec(
                "Kaise Aage Badhein",
                "Vartaman kshan mein chunautiyan hain. Jaldbaazi ke bajay sahi samay ka intezar karein aur grah shanti ke upay karein.",
            ))
    elif is_tenglish:
        if fav is True:
            out.append(_sec(
                "Mundhuku Ela Vellali",
                "Samayam meeku anukulam ga undi, ippude drudhamaina adugulu veyadam manchidi.",
            ))
        elif fav is False:
            out.append(_sec(
                "Mundhuku Ela Vellali",
                "Prasthutha kshanam lo challenges unnai. Aathram padakunda anukoolamaina samayam kosam aagi graha shanti upayam cheyandi.",
            ))
    else:
        if fav is True:
            out.append(_sec(
                "How to play it",
                "The moment is with you, so acting sooner reads better than waiting for a "
                "cleaner signal. The chart was cast for the moment you asked, and that is "
                "the window it answers for.",
            ))
        elif fav is False:
            out.append(_sec(
                "How to play it",
                "The moment is not with you on this. That is not the same as never — it means "
                "this particular attempt, asked at this particular moment, is working against "
                "the current rather than with it.",
            ))

    if paid:
        windows = [w for w in (brief.get("dated_windows") or []) if isinstance(w, dict)]
        if is_hinglish:
            lines = [
                f"{_label(w.get('label')) or 'Ek timing window'} {_human_date(w.get('start'))} ko shuru hota hai"
                + (f" aur {_human_date(w.get('end'))} tak chalta hai" if w.get("end") else "")
                for w in windows[:3] if w.get("start")
            ]
            sec_title = "Dates Aur Samay Chakra"
        elif is_tenglish:
            lines = [
                f"{_label(w.get('label')) or 'Oka timing window'} {_human_date(w.get('start'))} lo start avuthundi"
                + (f" mariyu {_human_date(w.get('end'))} varaku untundi" if w.get("end") else "")
                for w in windows[:3] if w.get("start")
            ]
            sec_title = "Dates Mariyu Timing Windows"
        else:
            lines = [
                f"{_label(w.get('label')) or 'A window'} opens {_human_date(w.get('start'))}"
                + (f" and runs to {_human_date(w.get('end'))}" if w.get("end") else "")
                for w in windows[:3] if w.get("start")
            ]
            sec_title = "When it moves"
        if lines:
            out.append(_sec(sec_title, _join_sentences(lines)))

    return [s for s in out if s]


def _fb_palm(brief: dict, meta: dict, text: str, *, paid: bool, lang: str = "en") -> list[dict]:
    lang_code = str(lang or "").lower().strip()
    is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")
    out = _fallback_from_palm_text(text, paid=paid, lang=lang)
    measured = [
        x for x in (brief.get("measured_consultation") or [])
        if isinstance(x, dict) and x.get("title")
    ]
    if measured:
        if is_hinglish:
            out.append(_sec(
                "Photo Se Mile Sanket",
                "Aapke palm photo mein kuch measured rekha-sanket mile hain. "
                "Yeh observation-based guidance hai, pakka bhavishya-vachan nahi.",
            ))
        elif is_tenglish:
            out.append(_sec(
                "Photo Nunchi Dorikina Sankethalu",
                "Mee palm photo lo konni measured rekha sankethalu dorikayi. "
                "Ivi observation-based guidance, khachchitamaina bhavishyavani kaadu.",
            ))
        else:
            out.append(_sec(
                "Measured photo findings",
                "The palm photo contains measured line or morphology signals. "
                "They support reflective guidance, not guaranteed outcomes.",
            ))
        if out:
            return [s for s in out if s]
    if out:
        return out
    sections: list[Optional[dict]] = []
    shape = _clip(brief.get("hand_shape"), 40)
    traits = brief.get("personality_traits") or []
    if shape or traits:
        if is_hinglish:
            lead = f"Aapka haath {shape.title()} archetype darshata hai. " if shape else ""
            sections.append(_sec(
                "Swabhav Aur Core Archetype",
                lead + _join_sentences(list(traits[:4])),
            ))
        elif is_tenglish:
            lead = f"Mee cheyi {shape.title()} archetype ni chupisthondi. " if shape else ""
            sections.append(_sec(
                "Swabhavam Mariyu Core Archetype",
                lead + _join_sentences(list(traits[:4])),
            ))
        else:
            lead = f"Your hands read as an {shape.title()} hand. " if shape else ""
            sections.append(_sec(
                "Personality & Core Temperament",
                lead + _join_sentences(list(traits[:4])),
            ))
    areas = [a for a in (brief.get("life_areas") or []) if isinstance(a, dict)]
    if areas:
        if is_hinglish or is_tenglish:
            # For Hinglish/Tenglish, English palm readings produce gibberish when copied verbatim
            # ("Character: Your Air-dominant hand architecture..."). Use Hindi area names only.
            hi_area_map = {"character":"Swabhav","mind":"Mansikta","love":"Prem","career":"Career","wealth":"Dhan","health":"Swasthya","travel":"Yatra","fortune":"Bhagya"}
            te_area_map = {"character":"Swabhavam","mind":"Manasika","love":"Prema","career":"Career","wealth":"Dhanam","health":"Aarogyam"}
            amap = hi_area_map if is_hinglish else te_area_map
            lines = [f"{amap.get(str(a.get('area') or '').lower(), str(a.get('area') or ''))} kshetra mein vishesh sanket hain" for a in areas[:4] if a.get("area")]
        else:
            lines = [f"{a.get('area')}: {a.get('reading')}" for a in areas[:4] if a.get("reading")]
        if lines:
            if is_hinglish:
                sec_title = "Hatho Ke Mukhya Kshetra"
            elif is_tenglish:
                sec_title = "Chethula Mukhya Rangalu"
            else:
                sec_title = "What your hands say about your life"
            sections.append(_sec(sec_title, _join_sentences(lines)))
    if brief.get("both_hands_summary"):
        if is_hinglish:
            sec_title = "Dono Hatho Ka Tulnatmak Vishleshan"
            # English both_hands_summary produces code-mixed gibberish in Hinglish
            body = "Aapke dono haathon ka tulanatmak vishleshan darshata hai ki daayein haath mein vartaman abhivyakti aur baayein haath mein antarnihit pravritti hai."
        elif is_tenglish:
            sec_title = "Rendu Chethula Thulanathmaka Vishleshana"
            body = "Mee rendu chethula thulanathmaka vishleshana daayina chethilo prastutha abhivyakthi mariyu edama chethilo antarnihitha pravruthi ni chupisthundi."
        else:
            sec_title = "Both hands together"
            body = str(brief["both_hands_summary"])
        sections.append(_sec(sec_title, body))
    return [s for s in sections if s]


def _fallback_sections(
    kind: str,
    meta: dict,
    facts: Any,
    text: str,
    *,
    paid: bool = True,
    brief: Optional[dict] = None,
    inventory: Optional[dict] = None,
    lang: str = "en",
) -> list[dict]:
    meta = meta or {}
    brief = brief if brief is not None else _summary_brief(kind, meta, facts, paid=paid)
    sections: list[dict] = []

    if kind in ("full_report", "classical_report"):
        sections = _fb_full_report(brief, paid=paid, lang=lang)
    elif kind == "user_question":
        sections = _fb_user_question(brief, meta, paid=paid, lang=lang)
    elif kind == "horary":
        sections = _fb_horary(brief, meta, paid=paid, lang=lang)
    elif kind == "palm":
        sections = _fb_palm(brief, meta, text, paid=paid, lang=lang)
    elif kind == "kundali_match":
        body = _join_sentences([
            brief.get("headline"), brief.get("verdict"),
            f"The match scores {brief['guna_points']}" if brief.get("guna_points") else "",
        ])
        one = _sec("Compatibility verdict", body)
        sections = [one] if one else []
        if brief.get("active_concerns"):
            two = _sec(
                "What needs attention",
                "The chart flags " + ", ".join(brief["active_concerns"][:3])
                + ". These are worth understanding before a date is fixed.",
            )
            if two:
                sections.append(two)
    elif kind == "muhurat":
        one = _sec("Day verdict", _join_sentences([brief.get("verdict")]))
        sections = [one] if one else []
    elif kind in ("daily", "numerology"):
        # meta.teaser is subscribe copy, not a finding — the reading itself is
        # the better source, and the CTA section now carries the pitch.
        body = _first_sentences(text, 3, free=not paid, allow_dates=(kind == "daily"))
        one = _sec("Today in plain terms" if kind == "daily" else "Your numbers", body)
        if not one:
            one = _sec(
                "Today in plain terms" if kind == "daily" else "Your numbers",
                _join_sentences([brief.get("teaser")]),
            )
        sections = [one] if one else []
    elif kind == "btr":
        if brief.get("skipped"):
            one = _sec("Birth-time check", _clip(brief.get("reason"), 400)
                       or "The rectification scan could not run on the details supplied.")
            sections = [one] if one else []

    if not sections:
        sections = _fallback_from_report_text(text, paid=paid, lang=lang)

    if not sections and text:
        snippet = re.sub(r"\s{2,}", " ", text)[:1200].strip()
        one = _sec("Overview", snippet + ("…" if len(text) > len(snippet) else ""))
        if one:
            sections = [one]

    sections = _polish(sections, kind=kind, paid=paid)

    if not sections:
        lang_code = str(lang or "").lower().strip()
        if lang_code in ("hi_en", "hinglish", "hi", "hindi"):
            title = "Saransh"
            body = "Neeche di gayi report mein aapki kundli ka vistaar se vishleshan diya gaya hai."
        elif lang_code in ("te_en", "tenglish", "te", "telugu"):
            title = "Saransham"
            body = "Kindha unna report lo mee kundali yokka vivaranga vishleshana ivvabadindi."
        else:
            title = "Overview"
            body = ("Open the full report below for the detailed reading. "
                    "A plain-English summary could not be generated for this version.")
        sections = [{
            "title": title,
            "body": body,
            "role": "insight",
        }]

    if not paid:
        sections = _repair_free_sections(sections[:8], kind, inventory, lang)

    return sections[:10]


def _fallback_headline(kind: str, brief: dict, meta: dict, *, paid: bool,
                       text: str = "", lang: str = "en") -> str:
    """One clean sentence. A bare adjective or a page of teaser copy is not one."""
    lang_code = str(lang or "").lower().strip()
    is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")
    candidates: list[str] = []
    if kind in ("horary", "user_question"):
        if kind == "horary" and not paid:
            q = _clip(brief.get("question") or meta.get("question"), 130).rstrip(".?!")
            if is_hinglish:
                candidates.append(
                    f"Prashna kundli aapke prashna ({q}) ka vishleshan karti hai." if q
                    else "Prashna kundli aapke prashna ka vishleshan karti hai."
                )
            elif is_tenglish:
                candidates.append(
                    f"Prashna kundali mee prashna ({q}) vishleshana chesthondi." if q
                    else "Prashna kundali mee prashna vishleshana chesthondi."
                )
            else:
                candidates.append(
                    f"The chart is examining your question about {q}" if q
                    else "The chart is examining the question you asked"
                )
        verdict = _tidy(_clip(brief.get("verdict") or brief.get("finding"), 130)).rstrip(".")
        if verdict and len(verdict.split()) < 5 and not (kind == "horary" and not paid):
            if is_hinglish:
                candidates.append(f"Aapke prashna par kundli ka faisla: {verdict}")
            elif is_tenglish:
                candidates.append(f"Mee prashnaku kundali theerpu: {verdict}")
            else:
                candidates.append(f"On the question you asked, the chart reads: {verdict}")
        if not (kind == "horary" and not paid):
            candidates += [brief.get("finding"), brief.get("verdict")]
    elif kind in ("full_report", "classical_report"):
        tone = _clip(brief.get("current_phase_tone"), 90).rstrip(".").lower()
        pressure = [p for p in (brief.get("areas_under_pressure") or []) if p][:2]
        # Translate pressure area labels for Hinglish/Tenglish — brief carries English labels
        hi_map = {"career":"Career","wealth":"Dhan","marriage":"Vivah","relationships":"Rishte","health":"Swasthya","children":"Santan","property":"Sampatti","foreign":"Videsh Yatra","fortune & higher learning":"Bhagya aur Uccha Shiksha","work & career":"Karya aur Career","home & family":"Ghar aur Parivar","money & savings":"Dhan aur Bachat"}
        te_map = {"career":"Career","wealth":"Dhanam","marriage":"Vivaham","health":"Aarogyam","fortune & higher learning":"Bhagyam mariyu Higher Learning","work & career":"Pani mariyu Career"}
        if is_hinglish:
            hi_pressure = [hi_map.get(p.lower(), p) for p in pressure]
            if tone and hi_pressure:
                candidates.append(
                    f"Aapka vartaman daur sahayak hai, jabki vishesh dabav "
                    + " aur ".join(hi_pressure) + " par hai."
                )
            elif tone:
                candidates.append("Aapki kundli ka vartaman daur anukool aur sahayak hai.")
            candidates.append("Aapke vyaktitva aur current phase ke sanket anukool hain.")
        elif is_tenglish:
            te_pressure = [te_map.get(p.lower(), p) for p in pressure]
            if tone and te_pressure:
                candidates.append(
                    f"Mee vartamana dasha anukulam ga undi, konni visheshalu "
                    + " mariyu ".join(te_pressure) + " meeda unnai."
                )
            elif tone:
                candidates.append("Mee kundali vartamana dasha anukulam ga undi.")
            candidates.append("Mee vyaktithvam mariyu current phase sankethalu anukulam ga unnai.")
        else:
            if tone and pressure:
                candidates.append(
                    f"A {tone} chapter overall, with the pressure sitting on "
                    + " and ".join(p.lower() for p in pressure)
                )
            elif tone:
                candidates.append(f"This reads as a {tone} chapter of your life")
        candidates += list((brief.get("current_phase_notes") or [])[:1])
    elif kind == "palm":
        shape = _clip(brief.get("hand_shape"), 40)
        if shape:
            if is_hinglish:
                candidates.append(f"Aapke haath {shape.title()} archetype darshate hain.")
            elif is_tenglish:
                candidates.append(f"Mee cheyi {shape.title()} archetype ni chupisthondi.")
            else:
                candidates.append(f"Your hands read as an {shape.title()} hand")
        candidates += list((brief.get("personality_traits") or [])[:1])
    elif kind == "kundali_match":
        candidates += [brief.get("headline"), brief.get("verdict")]
    elif kind == "muhurat":
        candidates += [brief.get("verdict")]

    # Kinds with no structured verdict (daily, numerology) still deserve a lead
    # line, and their opening sentence is usually the verdict in prose.
    if not (kind == "horary" and not paid):
        opener = _first_sentences(text, 1, free=not paid, allow_dates=(kind == "daily"))
        if opener:
            candidates.append(opener)

    for raw in candidates:
        line = _tidy(_clip(raw, 170))
        if not line:
            continue
        first = _sentences(line)[0] if _sentences(line) else line
        if len(first.split()) < 3:
            continue
        if _JARGON_RE.search(first) or _BARE_HOUSE_RE.search(first):
            continue
        if not paid and not _dates_free_may_keep(first):
            continue
        return first[:170]
    return ""


# ---------------------------------------------------------------------------
# LLM path
# ---------------------------------------------------------------------------
def _user_prompt(
    kind: str, meta: dict, text: str, *, paid: bool, brief: dict, inventory: Optional[dict], lang: str = "en",
) -> str:
    report_label = _kind_label(kind)
    question = str(meta.get("question") or "").strip()
    lines = [
        f"Report kind: {kind} ({report_label}).",
        "Report status: FULL UNLOCKED READING." if paid
        else "Report status: FREE PREVIEW — the paid half is locked and the reader has not paid.",
    ]
    if question:
        lines.append(f"Customer question: {question}")
    if kind in ("full_report", "classical_report"):
        if paid:
            lines.append(
                "Writing order: begin with the current life chapter, then include a "
                "personal section about who this chart says the reader is."
            )
        else:
            lines.append(
                "FREE PREVIEW REQUIREMENT: the first two insight sections must include "
                "the reader's personality. Use at least two distinct entries from "
                "`personality_traits` in the Engine findings, with a clear title such as "
                "'What your chart says about you'. Do this before discussing the current "
                "phase or life areas. Do not replace personal traits with generic words "
                "such as supportive, creative or careful. When present, also cover the "
                "free-visible D1 self baseline, D2 money and savings, D3 courage and "
                "initiative, and D12 family and parental findings. End the insight "
                "sections with the current strained areas from the brief."
            )
    lines.append(
        "Engine findings (authoritative — this is what the reading actually says; "
        "translate it, never contradict or extend it):"
    )
    lines.append(json.dumps(brief, ensure_ascii=False, default=str))
    if not paid:
        inv = inventory or {}
        lines.append(
            "Locked inventory — COUNTS ONLY of what the paid half holds. Use these numbers "
            "in the `locked` section to be specific about what is waiting. You do NOT have "
            "the values behind them, so never state a date, a verdict or a remedy from here. "
            "`sections` are the report's own headings: turn them into what the reader gets, "
            "never copy them out as a list:"
        )
        lines.append(json.dumps({
            k: v for k, v in inv.items() if k in
            ("dated_windows", "life_areas", "remedies", "sections")
        }, ensure_ascii=False, default=str))
    lines.append("Visible report text (the only prose the reader has already seen):")
    lines.append(text)
    if str(lang or "").lower() in ("hi_en", "hinglish", "hi", "hindi"):
        lines.append(
            "LANGUAGE REQUIREMENT: Write the headline and all section titles and bodies in natural, conversational Hindi "
            "using the English/Latin alphabet (Hinglish / Roman Hindi). DO NOT use Devanagari script. "
            "Example headline: 'Aapki kundli mein career growth aur stability ke strong sanket hain.' "
            "Example body: 'Aapka Lagna aur dasha period yeh dikhata hai ki aane wale samay mein professional progression ke acche avsar milenge.'"
        )
    elif str(lang or "").lower() in ("te_en", "tenglish", "te", "telugu"):
        lines.append(
            "LANGUAGE REQUIREMENT: Write the headline and all section titles and bodies in natural, conversational Telugu "
            "using the English/Latin alphabet (Tenglish / Roman Telugu). DO NOT use Telugu script. "
            "Example headline: 'Mee kundali lo career growth mariyu stability kosam strong sankethalu unnai.' "
            "Example body: 'Mee Lagna mariyu dasha period prakaram mundu rojullo professional growth ki manchi avakashalu unnai.'"
        )
    return "\n".join(lines)


def _llm_sections(
    kind: str,
    meta: dict,
    text: str,
    *,
    paid: bool = True,
    brief: Optional[dict] = None,
    inventory: Optional[dict] = None,
    lang: str = "en",
) -> Optional[dict]:
    if not _enabled() or not text.strip():
        return None
    brief = brief or {}
    system = system_prompt_for("plain_summary", lang=lang)
    user = _user_prompt(kind, meta, text, paid=paid, brief=brief, inventory=inventory, lang=lang)

    prose = _complete(PlainSummaryProse, system, user)
    if prose is None:
        return None
    prose = _plainify_prose(prose)
    fails = _validate(prose, text, kind=kind, paid=paid, brief=brief, lang=lang)
    if fails:
        retry_user = (
            user
            + "\n\nYour previous attempt was rejected by review because "
            + "; ".join(_qa_hint(f) for f in fails[:6])
            + ". Fix every one of those and return the corrected JSON."
        )
        retried = _complete(PlainSummaryProse, system, retry_user)
        if retried is not None:
            retried = _plainify_prose(retried)
            retry_fails = _validate(
                retried, text, kind=kind, paid=paid, brief=brief, lang=lang
            )
            if len(_hard_failures(retry_fails)) <= len(_hard_failures(fails)):
                prose, fails = retried, retry_fails

    # A score or a date the model would not give up costs one sentence, not the
    # whole draft.
    hard = _hard_failures(fails)
    patterns = _deletion_patterns(hard) if hard else None
    if patterns and _strip_sentences(prose, patterns):
        fails = _validate(prose, text, kind=kind, paid=paid, brief=brief, lang=lang)
        hard = _hard_failures(fails)
        if not hard:
            print(f"[plain_summary] cut a sentence to pass review ({kind}, "
                  f"paid={paid})", flush=True)
    if hard:
        print(f"[plain_summary] QA rejected ({kind}, paid={paid}): "
              f"{hard[:4]}", flush=True)
        return None
    if fails:
        print(f"[plain_summary] repaired structure ({kind}): {fails[:4]}", flush=True)

    sections = [
        {"title": s.title.strip(), "body": s.body.strip(), "role": s.role}
        for s in prose.sections
    ]
    if not paid:
        sections = _repair_free_sections(sections, kind, inventory, lang)
    else:
        sections = [s for s in sections if s["role"] != "cta"] or sections
    return {"sections": sections[:10], "headline": (prose.headline or "").strip()}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
_UQ_TITLES = {
    "en": ("The short answer", "The main reasons", "When", "What to do", "Timing and next steps"),
    "hi_en": ("Seedha jawab", "Mukhya karan", "Kab", "Kya karein", "Samay aur agle kadam"),
    "te_en": ("Chinna samadhanam", "Mukhya karanalu", "Eppudu", "Em cheyali", "Samayam mariyu next steps"),
}


def _summary_from_question_reading(meta: dict, *, paid: bool, lang: str) -> Optional[dict]:
    """Summary of a question report, written from the reading itself.

    The report is already one short answer, so the summary is that answer plus
    its reasons (and, once paid, the timing and steps). It used to be rebuilt
    from a truncated one-line label, which cut sentences mid-word.
    """
    rd = meta.get("reading")
    if not isinstance(rd, dict) or not str(rd.get("answer") or "").strip():
        return None
    key = _lang_key_for_summary(lang)
    t_answer, t_why, t_when, t_do, t_next = _UQ_TITLES[key]
    answer = str(rd["answer"]).strip()
    why = [str(x).strip() for x in (rd.get("why") or []) if str(x).strip()]
    timing = str(rd.get("timing") or "").strip()
    steps = [str(x).strip() for x in (rd.get("steps") or []) if str(x).strip()]

    sections: list[dict] = [{"title": t_answer, "body": answer, "role": "insight"}]
    if why:
        sections.append({"title": t_why, "body": " ".join(why[:3]), "role": "insight"})
    has_more = bool(timing or steps)
    if paid:
        if timing:
            sections.append({"title": t_when, "body": timing, "role": "insight"})
        if steps:
            sections.append({"title": t_do, "body": " ".join(steps[:3]), "role": "insight"})
    elif has_more:
        if key == "en":
            body = ("The timing window and the practical steps for this question are written and "
                    "waiting in the full answer.")
            sections.append({"title": t_next, "body": body, "role": "locked"})
        else:
            sections.append(_locked_section("user_question", None, lang))
        sections.append(_cta_section("user_question", lang))
    first = _sentences(answer)
    headline = (first[0] if first else answer)[:170]
    return {"sections": sections, "headline": headline}


def _lang_key_for_summary(lang: str) -> str:
    low = str(lang or "").lower().strip()
    if low in ("hi_en", "hinglish", "hi", "hindi"):
        return "hi_en"
    if low in ("te_en", "tenglish", "te", "telugu"):
        return "te_en"
    return "en"


def build_plain_summary(
    *,
    kind: str,
    html: str,
    meta: Optional[dict] = None,
    facts: Any = None,
    paid: bool = True,
    paid_html: str = "",
    lang: str = "",
) -> dict:
    """Return {headline, sections: [{title, body, role}], generated, ...}."""
    meta = dict(meta or {})
    if not lang:
        lang = str(meta.get("language") or (facts.get("language") if isinstance(facts, dict) else getattr(facts, "language", "en")) or "en")
    text = html_to_report_text(html)
    brief = _summary_brief(kind, meta, facts, paid=paid)
    inventory = None if paid else _locked_inventory(paid_html or html, facts, meta)
    cache_key = hashlib.sha256(
        f"{kind}:{paid}:{lang}:{text[:4000]}:{json.dumps(meta, sort_keys=True, default=str)[:800]}".encode()
    ).hexdigest()[:24]

    out = None
    if kind in ("user_question", "horary"):      # both are one card with the same reading
        out = _summary_from_question_reading(meta, paid=paid, lang=lang)
    generated = "reading" if out else "llm"
    if out is None:
        out = _llm_sections(kind, meta, text, paid=paid, brief=brief, inventory=inventory, lang=lang)
    if not out or not out.get("sections"):
        out = {
            "sections": _fallback_sections(
                kind, meta, facts, text, paid=paid, brief=brief, inventory=inventory, lang=lang
            ),
            "headline": _fallback_headline(kind, brief, meta, paid=paid, text=text, lang=lang),
        }
        generated = "fallback"
    elif not out.get("headline"):
        # QA may have cut the model's headline; the panel leads with this line.
        out["headline"] = _fallback_headline(kind, brief, meta, paid=paid, text=text, lang=lang)

    result = {
        "headline": out.get("headline") or "",
        "sections": out["sections"],
        "generated": generated,
        "cache_key": cache_key,
        "paid": bool(paid),
    }
    if not paid and inventory:
        result["locked"] = {
            "dated_windows": inventory.get("dated_windows", 0),
            "life_areas": inventory.get("life_areas", 0),
            "remedies": inventory.get("remedies", 0),
            "items": inventory.get("items", []),
        }
    return result


def attach_plain_summary(
    meta: dict,
    *,
    kind: str,
    free_html: str,
    paid_html: str = "",
    paid: bool = True,
    facts: Any = None,
    lang: str = "",
) -> dict:
    """Mutate meta in place with plainSummary (free) and plainSummaryPaid.

    Both halves are rendered and stored at creation time, so both summaries are
    built here. A report is created unpaid; without the paid half built now, a
    customer who pays would keep reading a summary of the preview they already
    saw.
    """
    meta = dict(meta or {})
    if not lang:
        lang = str(meta.get("language") or (facts.get("language") if isinstance(facts, dict) else getattr(facts, "language", "en")) or "en")
    free_src = free_html or ""
    paid_src = paid_html or ""

    def _build(source: str, is_paid: bool) -> Optional[dict]:
        try:
            summary = build_plain_summary(
                kind=kind, html=source, meta=meta, facts=facts,
                paid=is_paid, paid_html=paid_src, lang=lang,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[plain_summary] {kind} paid={is_paid} skipped: {exc}", flush=True)
            return None
        if not summary.get("sections"):
            return None
        out = {
            "headline": summary.get("headline") or "",
            "sections": summary["sections"],
            "generated": summary.get("generated", "fallback"),
            "paid": bool(is_paid),
        }
        if summary.get("locked"):
            out["locked"] = summary["locked"]
        return out

    if free_src.strip():
        free_summary = _build(free_src, False)
        if free_summary:
            meta["plainSummary"] = free_summary
        if paid_src.strip() and paid_src != free_src:
            paid_summary = _build(paid_src, True)
            if paid_summary:
                meta["plainSummaryPaid"] = paid_summary
    elif paid_src.strip():
        only = _build(paid_src, bool(paid))
        if only:
            meta["plainSummary"] = only

    return meta
