"""Fact-only builders for the four LLM-humanized tabs.

Pure functions: no astrology re-run, no prose generation. Strip already-written
English where the engine still embeds it (e.g. palm human_interpretation).
Access projection keeps Free/Paid on the same truth with different depth.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from typing import Any, Optional, TypeVar

from .fallback import clean_palm_summary, clip_sentences
from .schemas import (
    SCHEMA_VERSION,
    CardFacts,
    CrossoverFact,
    DashaClockFact,
    DashaPlanetTransitFact,
    JaiminiFact,
    LifeAreaJudgementFact,
    FutureConfluenceFact,
    SlowTransitFact,
    EvidenceFact,
    HoraryFacts,
    HoraryLaneFact,
    PalmAspectFacts,
    PalmFacts,
    QuestionFacts,
    RecentMonthFact,
    ReportFacts,
    TransitContextFact,
    TransitionFact,
    VedicContext,
    WindowFact,
)

ENGINE_VERSION = "astro-2026.08.17-qwen7b-analytical-v4.5-consultation-conclusion-production"

_ID_RE = re.compile(r"[^a-z0-9]+")
_CLASSICAL_RAW = re.compile(
    r"debt-ridden|hurt by fire|free from enemies|strong appetite|"
    r"you will be|bereaved|inauspicious deeds|classical rule-book|"
    r"sub-lord sense|recognition_tag_|Existing chart-rule|"
    r"widow(?:ed)?|accident is certain|"
    r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+house|"
    r"8th lord|9th lord|10th lord|11th lord|12th lord|"
    r"sub[- ]lord|karakamsa|atmakaraka|"
    r"cusp|bhava|nakshatra|varga|lagna|"
    r"jamakkol|prashna kundali|dasha|bhukti|"
    r"case-book|classical rule|technical reason|"
    r"\b(?:spouse|husband|wife)\s*:" 
    r"|\b(?:watch|vulnerability|sensitive)\b.{0,40}\b(?:brain|head|heart|"
    r"gut|intestine|kidney|liver|lungs|circulation|reproductive|"
    r"stomach|calves|ankles)\b)",
    re.I,
)
_PLANET_TOKEN = re.compile(
    r"\b(Sun|Moon|Mercury|Venus|Mars|Jupiter|Saturn|Rahu|Ketu|"
    r"Uranus|Neptune|Pluto)\b",
    re.I,
)

T = TypeVar("T")


def _eid(family: str, polarity: str, text: str) -> str:
    h = hashlib.sha1((text or "").encode("utf-8", "ignore")).hexdigest()[:8]
    return f"{family}:{polarity}:{h}"


def _as_date(v: Any) -> Optional[date]:
    if isinstance(v, date):
        return v
    text = str(v or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _pretty_date(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, date):
        return v.isoformat()
    return str(v).strip()


def _first_name(name: str) -> str:
    return (name or "").strip().split()[0][:40] if (name or "").strip() else ""


def _profile_context(pc: dict, today: date) -> tuple[str, Optional[int], str]:
    meta = pc.get("meta") or {} if isinstance(pc, dict) else {}
    gender = meta.get("gender", pc.get("gender") if isinstance(pc, dict) else "")
    g = str(gender or "").strip().lower()
    if g in ("m", "male", "man", "1"):
        gender = "male"
    elif g in ("f", "female", "woman", "2"):
        gender = "female"
    else:
        gender = "unknown"
    dob = str(meta.get("dob") or "").strip()
    age_years: Optional[int] = None
    if dob:
        try:
            d = date.fromisoformat(dob[:10])
            age_years = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
            if age_years < 0 or age_years > 120:
                age_years = None
        except Exception:
            age_years = None
    band = "adult"
    try:
        from interpretation.life_stage import age_band as _ab
        band = _ab(pc, today=today) or "adult"
    except Exception:
        pass
    return str(gender), age_years, str(band)


QUESTION_LENS = {
    "profession": "Will my career grow, and when will recognition or a meaningful professional shift become easier?",
    "money": "Will my financial security improve, and what kind of progress is more realistic for me?",
    "love": "What does my relationship life look like, and when does it become easier or more settled?",
    "children": "What does my chart say about children, parenthood and the experience of raising them?",
    "home": "Will home, family and living circumstances become more settled or change meaningfully?",
    "health": "Where should I protect my energy and routine, and when are demanding periods more likely?",
    "learning": "Where can learning, study or skill-building create meaningful growth?",
    "parents": "What role do parents and family responsibilities play in my life?",
    "siblings": "What does my relationship with siblings and close family connections look like?",
    "self": "What is the deeper pattern shaping how I approach life and decisions?",
    "inner": "What is changing inside me, and where is this period pushing personal growth?",
    "strengths": "What are the qualities I can rely on most strongly in life?",
}

# Sentences the sanitizer emits when it has nothing specific to say. They
# carry no information, and repeating them crowds the real evidence out of
# the prompt.
_FILLER_EVIDENCE = re.compile(
    r"^(?:the chart evidence is summarized|timing evidence is included|"
    r"(?:birth-chart structure|case-based confirmation|current transit|"
    r"astrology method|life-pattern cross-check|specialist timing cross-check|"
    r"modern technique|chart evidence|remedy evidence)\s*[—-]\s*"
    r"(?:supports|adds caution to|is broadly neutral for) this reading)",
    re.I,
)


def _dedupe_evidence(items: list[EvidenceFact]) -> list[EvidenceFact]:
    """Collapse repeats and drop content-free filler.

    The same sentence arriving as both support and caution cancels itself out
    and crowds the card, so it is kept once under the polarity it appeared
    with first. The disagreement is not thrown away: the surviving entry is
    tagged ``contested`` so the model can say the methods differ here.
    """
    out: list[EvidenceFact] = []
    by_key: dict[tuple[str, tuple[str, ...]], EvidenceFact] = {}
    for ev in items:
        text = re.sub(r"\s+", " ", (ev.text or "").strip())
        if text and _FILLER_EVIDENCE.match(text):
            continue
        tags = tuple(sorted(set(ev.semantic_tags or [])))
        if not text and not tags:
            continue
        key = (text.lower(), tags)
        kept = by_key.get(key)
        if kept is None:
            by_key[key] = ev
            out.append(ev)
            continue
        if kept.polarity != ev.polarity and "contested" not in kept.semantic_tags:
            kept.semantic_tags = [*kept.semantic_tags, "contested"][:6]
    return out


def _conf(value: str) -> str:
    v = (value or "").lower().strip()
    if v in ("high", "moderate", "low"):
        return v
    if v in ("strong", "clear", "good"):
        return "high"
    if v in ("medium", "fair"):
        return "moderate"
    return "low"


def _dir(value: str) -> str:
    """Map engine aliases to controlled Direction enum (support/caution/…)."""
    v = (value or "").lower().strip()
    if v in ("support", "caution", "mixed", "neutral"):
        return v
    if v in ("up", "favourable", "favorable", "yes", "supportive"):
        return "support"
    if v in ("down", "unfavourable", "unfavorable", "no", "demanding"):
        return "caution"
    return "mixed"


def _agreement(value: str) -> str:
    v = (value or "").lower().strip()
    if v in ("strong", "partial", "weak", "insufficient"):
        return v
    if v in ("high", "full", "clear"):
        return "strong"
    if v in ("moderate", "medium", "mixed"):
        return "partial"
    if v in ("low",):
        return "weak"
    return "weak"


def _normalize_evidence_text(text: str) -> tuple[str, list[str]]:
    """Return semantic evidence only; raw technique prose is never LLM input."""
    t = (text or "").strip()
    if not t:
        return "", []
    try:
        from qa_checks.customer_text_sanitizer import is_customer_safe
        unsafe = not is_customer_safe(t)
    except Exception:  # noqa: BLE001
        unsafe = False
    if _CLASSICAL_RAW.search(t) or unsafe or len(t) > 160:
        tags: list[str] = []
        low = t.lower()
        if any(x in low for x in ("debt", "money", "financial", "wealth")):
            tags.append("financial_pressure")
        if any(x in low for x in ("fire", "accident", "risk", "hurt")):
            tags.append("risk_awareness")
        if any(x in low for x in ("enemy", "opponent", "conflict")):
            tags.append("conflict_sensitivity")
        if any(x in low for x in ("health", "illness", "body", "recovery")):
            tags.append("wellbeing_sensitivity")
        if not tags:
            tags.append("caution_theme")
        return "", tags[:4]
    return t[:160], []


def _planets_from_text(*parts: str) -> list[str]:
    found: list[str] = []
    for p in parts:
        for m in _PLANET_TOKEN.finditer(p or ""):
            name = m.group(1).title()
            if name == "Rahu" or name == "Ketu":
                pass
            else:
                name = name.title()
            # Normalize casing
            canon = m.group(1)[0].upper() + m.group(1)[1:].lower()
            if m.group(1).lower() in ("rahu", "ketu"):
                canon = m.group(1).title()
            if canon not in found:
                found.append(canon)
    return found[:8]


def _dates_from_windows(*windows: Optional[WindowFact]) -> list[str]:
    out: list[str] = []
    for w in windows:
        if w is None:
            continue
        for v in (w.start, w.end, w.label):
            if v and str(v) not in out:
                out.append(str(v)[:40])
    return out[:12]


def _public_fact_payload(facts: Any) -> Any:
    """Fail-closed allowlist projection for LLM/customer grounding."""
    if hasattr(facts, "model_dump"):
        data = facts.model_dump(mode="json")
    else:
        data = facts
    if not isinstance(data, dict):
        return data

    allowed_root = {
        "kind", "first_name", "age_band", "age_years", "gender", "access", "dominant_hand", "photo_grade",
        "photo_confidence", "special_marks_allowed", "future_timing_allowed",
        "age_precision", "quality_note", "cards", "dashboard_buckets",
        "timing_windows", "question", "area", "area_key", "area_label", "intent",
        "answer_mode", "promise", "activation", "direction", "confidence",
        "agreement", "evidence", "manifestations", "manifestation_ids",
        "semantic_tags", "semantic_summary", "windows", "timing",
        "timing_agreement", "timing_can_create_promise", "action", "remedy", "why",
        "headline", "backing", "lanes", "primary_lane", "outcome", "conditions",
        "future_windows", "aspects", "life_stage", "horary", "question_context",
        "relevant_facts", "status", "activation_status", "promise_status",
        "best", "nearest", "n_methods", "n_up", "n_down", "support_n", "caution_n",
        "route", "subject", "label", "contradicted", "favourable",
        "special_mark_ids", "allowed_dates",
        "truth_source", "canonical_area_key", "canonical_promise_status",
        "canonical_activation_status", "canonical_direction", "canonical_confidence",
        "canonical_agreement", "canonical_evidence", "canonical_manifestations",
        "canonical_timing",
        "personality_traits", "phase_direction", "phase_tone", "phase_end",
        "phase_notes", "recent_months", "hardest_areas", "hardest_area_labels",
        "life_stage_note", "life_stage_age", "demanding_aspect",
        "demanding_aspect_label", "remedies_allowed", "remedies",
        "life_state", "family_notes", "palm_state", "hand_contrast",
        "vedic_context", "timing_systems", "crossover_points", "slow_transits",
        "jaimini", "dasha_planet_transits", "life_area_judgements",
    }
    allowed_nested = {
        "area", "label", "kind", "status", "activation_status", "confidence",
        "agreement", "direction", "evidence", "manifestation_ids", "semantic_tags",
        "semantic_summary", "window", "wealth_sub", "start", "end", "event_type",
        "source", "score", "support_n", "caution_n", "timing_agreement", "promise",
        "activation", "timing", "manifestation", "manifestations", "action", "remedy",
        "remedy_text", "why", "headline", "backing", "summary", "rows", "reason",
        "reasons", "family", "polarity", "strength", "age_window", "domain", "line",
        "hand", "meaning", "text", "lanes", "primary_lane", "outcome", "conditions",
        "relevant_facts", "aspect", "title", "lane", "verdict", "systems",
        "approved_remedies", "remedy_eligible", "domain", "topic",
        "question_lens", "prediction_strength", "timing_windows", "outlook_line",
        "direction_label", "manifests", "recognize",
        # Current-life-state block and family notes.
        "chapter_tone", "strongest_theme", "strongest_theme_label", "themes",
        "emotional_pressure", "decision_pressure", "responsibility",
        "uncertainty", "domains", "mind_now", "pressure", "support",
        "contradiction", "experience", "outcome_language_restricted",
        "likelihood", "is_fact", "relation", "tags", "notes", "method_count",
        # Current-palm-state block and the two-hand contrast.
        "confidence_note", "dominant_hand", "steady", "developed", "latent",
        "developed_traits", "latent_traits",
        "period_lord", "sub_period_lord", "rising_sign", "moon_sign",
        "mahadasha", "antardasha", "lagna", "nakshatra",
        "house", "allowed_planets", "system", "current", "current_start", "current_end",
        "next", "next_start", "next_end", "judgement", "activated_houses", "date", "significance",
        "functional_role", "from_natal_house", "ashtakavarga", "argala_judgement",
        "ak", "amk", "gk", "pk", "current_maha_sign", "current_antar_sign", "basis",
        "planet", "role", "from_natal_planet", "natural_karakas", "house_lord", "house_lord_role",
        "depositor", "house_strength", "divisional_chart", "divisional_verdict", "natal_promise",
        "current_vimshottari", "current_chara", "current_yogini", "current_transit", "next_period",
        "final_judgement", "current_summary", "future_summary", "remedy_reason",
        "natal_foundation_score", "confluence_score", "confluence_agreement",
        "lane_judgements", "lane_scores", "supporting_factors", "caution_factors",
        "activated_houses", "current_verdict", "relief_window", "stronger_window",
        "future_confluence", "change_type", "previous_judgement", "transit_events", "dasha_changes",
    }

    def clean(obj: Any, root: bool = False) -> Any:
        if isinstance(obj, dict):
            allow = allowed_root if root else allowed_nested
            return {k: clean(v) for k, v in obj.items() if k in allow}
        if isinstance(obj, list):
            return [clean(v) for v in obj]
        if isinstance(obj, str):
            return obj[:600]
        if isinstance(obj, (int, float, bool)) or obj is None:
            return obj
        return str(obj)[:600]

    return clean(data, root=True)


def public_fact_payload(facts: Any) -> Any:
    """Public API used by prompts and validators."""
    return _public_fact_payload(facts)


def citable_fact_ids(facts: Any) -> set[str]:
    """Ids a follow-up answer is allowed to cite for this reading.

    Every field name in the payload counts, plus the explicit ids carried by
    evidence rows and palm signals. Hand-listing the names meant a chart
    report and a horary verdict needed different lists, and citing a real
    field that happened to be missing from the list refused a good answer.
    """
    payload = _public_fact_payload(facts)
    out: set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                out.add(str(k))
                if k in ("text_id", "signal_id", "point_id", "id") and v:
                    out.add(str(v))
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    walk(payload)
    return out


def facts_cache_key(facts: Any) -> str:
    if hasattr(facts, "model_dump_json"):
        payload = facts.model_dump_json()
    else:
        payload = json.dumps(facts, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def seal_facts(facts: T, *, report_id: str = "") -> T:
    """Fill schema/engine/report_id/facts_hash on a facts model."""
    if not hasattr(facts, "model_copy"):
        return facts
    data = facts.model_dump(mode="json")  # type: ignore[attr-defined]
    data["schema_version"] = SCHEMA_VERSION
    data["engine_version"] = ENGINE_VERSION
    if report_id:
        data["report_id"] = report_id
    data["facts_hash"] = ""
    digest = hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:24]
    return facts.model_copy(update={  # type: ignore[attr-defined]
        "schema_version": SCHEMA_VERSION,
        "engine_version": ENGINE_VERSION,
        "report_id": report_id or getattr(facts, "report_id", "") or "",
        "facts_hash": digest,
    })


def project_for_access(facts: T, access: str) -> T:
    """Return FreeFacts or PaidFacts projection (same truth, different depth).

    Free strips exact timing dates, remedies, wealth sub-detail, and deep
    evidence so the LLM cannot leak paid content even if it tries.
    """
    access_n = "paid" if access == "paid" else "free"
    if not hasattr(facts, "model_dump"):
        return facts
    data = facts.model_dump(mode="json")  # type: ignore[attr-defined]
    data["access"] = access_n

    if access_n == "free":
        for c in data.get("cards") or []:
            if not isinstance(c, dict):
                continue
            c["wealth_sub"] = []
            c["approved_remedies"] = []
            c["remedy_eligible"] = False
            c["remedy_text"] = ""
            c["evidence"] = list(c.get("evidence") or [])[:2]
            # Teaser timing — keep direction, drop exact dates
            w = c.get("window")
            if isinstance(w, dict) and (w.get("start") or w.get("end")):
                c["window"] = {
                    "start": "",
                    "end": "",
                    "label": "a later validated window",
                    "event_type": w.get("event_type") or "",
                    "confidence": w.get("confidence") or "low",
                    "source": "teaser",
                    "score": float(w.get("score") or 0.0),
                }
            c["allowed_dates"] = []
            c["transition_map"] = []
            c["transit_context"] = []
        # Analytical timing is paid-depth. Free keeps only the current clock names
        # and judgement, not exact crossover dates, transit positions or houses.
        for c in data.get("timing_systems") or []:
            if isinstance(c, dict):
                c["current_start"] = ""; c["current_end"] = ""; c["next_start"] = ""; c["next_end"] = ""; c["activated_houses"] = []
        if "crossover_points" in data:
            data["crossover_points"] = []
        if "slow_transits" in data:
            data["slow_transits"] = []
        if "dasha_planet_transits" in data:
            data["dasha_planet_transits"] = []
        j = data.get("jaimini")
        if isinstance(j, dict):
            j["activated_houses"] = []
        for a in data.get("life_area_judgements") or []:
            if isinstance(a, dict):
                a["house_lord"] = ""; a["depositor"] = ""; a["house_strength"] = ""; a["divisional_chart"] = ""; a["divisional_verdict"] = ""
                a["current_transit"] = ""; a["next_period"] = ""; a["remedy_reason"] = ""
                # Future complete-confluence is paid-depth because it contains
                # exact dates and technical lane judgements. Never expose it in
                # the Free fact projection.
                a["relief_window"] = ""; a["stronger_window"] = ""; a["future_confluence"] = []
        # Report-level windows: labels only
        teased = []
        for w in data.get("timing_windows") or []:
            if not isinstance(w, dict):
                continue
            teased.append({
                "start": "",
                "end": "",
                "label": "upcoming validated window" if (w.get("start") or w.get("end")) else (w.get("label") or ""),
                "event_type": w.get("event_type") or "",
                "confidence": w.get("confidence") or "low",
                "source": "teaser",
                "score": float(w.get("score") or 0.0),
            })
        if "timing_windows" in data:
            data["timing_windows"] = teased[:3]
        # Question / horary paid windows
        for key in ("best", "nearest"):
            w = data.get(key)
            if isinstance(w, dict) and (w.get("start") or w.get("end")):
                data[key] = {
                    **w,
                    "start": "",
                    "end": "",
                    "label": w.get("label") or "a validated window",
                    "source": "teaser",
                }
        if data.get("windows"):
            data["windows"] = [
                {
                    **w,
                    "start": "",
                    "end": "",
                    "label": w.get("label") or "a validated window",
                    "source": "teaser",
                }
                for w in data["windows"]
                if isinstance(w, dict)
            ][:2]
        # Question/Horary/Palm may carry allowed_dates — clear on free
        if "allowed_dates" in data:
            data["allowed_dates"] = []
        # Canonical question timing is also paid data. Strip exact dates from
        # the canonical projection, otherwise the LLM could leak a paid window
        # through QuestionFacts.canonical_timing even though best/windows were
        # already redacted.
        if data.get("canonical_timing"):
            data["canonical_timing"] = [
                {
                    **w,
                    "start": "",
                    "end": "",
                    "label": w.get("label") or "a validated window",
                    "source": "teaser",
                }
                for w in data["canonical_timing"]
                if isinstance(w, dict)
            ][:2]
        # Only QuestionFacts carries canonical_evidence — do not inject the
        # key into ReportFacts/HoraryFacts/PalmFacts (extra=forbid).
        if "canonical_evidence" in data:
            data["canonical_evidence"] = list(data.get("canonical_evidence") or [])[:2]

        # Palm: drop future age windows and remedies on free
        if data.get("future_windows"):
            data["future_windows"] = []
        if "remedies" in data:
            data["remedies"] = []
        if "remedies_allowed" in data:
            data["remedies_allowed"] = False
        for a in data.get("aspects") or []:
            if isinstance(a, dict):
                a["age_window"] = []
        # Personality, current phase and recent months are free-section content
        # (same as the classic free report). Paid depth is per-area timing and
        # remedies, already stripped from cards above.
        #
        # The life-state block is deliberately free: it carries no dates and no
        # evidence, and it is what shows the reader the reading recognises the
        # phase they are in before they decide to unlock. Father and mother
        # stay as a free teaser; siblings and home stay paid depth.
        if "family_notes" in data:
            teaser = []
            for note in list(data.get("family_notes") or []):
                rel = (
                    str(note.get("relation") or "")
                    if isinstance(note, dict)
                    else str(getattr(note, "relation", "") or "")
                )
                if rel in ("father", "mother") and len(teaser) < 2:
                    teaser.append(note)
            data["family_notes"] = teaser
        ls = data.get("life_state")
        if isinstance(ls, dict):
            # Free names the themes; the per-area breakdown stays paid.
            ls["domains"] = list(ls.get("domains") or [])[:3]
        # The palm block is free for the same reason, and the two-hand contrast
        # is already part of the free card page.
        ps = data.get("palm_state")
        if isinstance(ps, dict):
            ps["domains"] = list(ps.get("domains") or [])[:3]

    cls = type(facts)
    projected = cls.model_validate(data)
    return seal_facts(projected, report_id=getattr(facts, "report_id", "") or "")


# ---------------------------------------------------------------------------
# Full report
# ---------------------------------------------------------------------------


def _house_from_sign(lagna_sign: str, sign: str) -> int:
    try:
        from astro_precompute import SIGNS
        if lagna_sign in SIGNS and sign in SIGNS:
            return ((SIGNS.index(sign) - SIGNS.index(lagna_sign)) % 12) + 1
    except Exception:
        pass
    return 0


def _functional_role(pc: dict, planet: str) -> str:
    row = (pc.get("planets") or {}).get(planet) or {}
    raw = str(row.get("functional_status") or "").strip().lower()
    return {
        "functional_benefic": "benefic",
        "functional_malefic": "malefic",
        "yogakaraka": "yogakaraka",
        "maraka": "maraka",
        "neutral": "neutral",
    }.get(raw, raw or "unknown")


def _next_future(rows: list[dict], *, current_end: str = "") -> dict:
    cur_end = _as_date(current_end)
    for row in rows:
        if not isinstance(row, dict):
            continue
        start = _as_date(row.get("start"))
        if start and (cur_end is None or start > cur_end):
            return row
    return {}


def _dasha_clock_facts(pc: dict, today: date) -> list[DashaClockFact]:
    """Return one authoritative, date-aware clock for each requested dasha system.

    The report must never mix a stale precomputed ``current_*`` label with a
    different date-aware result.  For the current date we therefore resolve the
    active Vimshottari/Yogini/Chara state first, then derive its exact boundaries
    from the same underlying schedules.  The next period is the first actual
    period after the active one, never a guessed label.
    """
    out: list[DashaClockFact] = []
    # ------------------------------------------------------------------
    # Vimshottari: use the date-aware engine as the source of truth.
    # ------------------------------------------------------------------
    try:
        from report_confluence import vimshottari_at, antardashas_for
        v = vimshottari_at(pc, today) or {}
        md_lord, ad_lord = str(v.get("md") or ""), str(v.get("ad") or "")
    except Exception:
        v = {}
        md_lord = ad_lord = ""

    vim = pc.get("vimshottari") or {}
    if not md_lord and isinstance(vim, dict):
        md = vim.get("current_md") or {}
        md_lord = str(md.get("md_lord") or md.get("lord") or "")
    if not ad_lord and isinstance(vim, dict):
        cur_ads = [x for x in (vim.get("current_md_antardashas") or []) if isinstance(x, dict)]
        cur_ad = next((x for x in cur_ads if x.get("status") == "current"), cur_ads[0] if cur_ads else {})
        ad_lord = str(cur_ad.get("ad_lord") or cur_ad.get("lord") or "")

    md_row = None
    if isinstance(vim, dict):
        seq = [x for x in (vim.get("sequence") or []) if isinstance(x, dict)]
        for row in seq:
            a, b = _as_date(row.get("start")), _as_date(row.get("end"))
            if md_lord and str(row.get("md_lord") or row.get("lord") or "") == md_lord and a and b and a <= today <= b:
                md_row = row
                break
        if md_row is None:
            md = vim.get("current_md") or {}
            if md_lord and str(md.get("md_lord") or md.get("lord") or "") == md_lord:
                md_row = md

    md_start = _as_date(md_row.get("start")) if md_row else None
    md_end = _as_date(md_row.get("end")) if md_row else None
    ads = []
    if md_row:
        try:
            yrs = float(md_row.get("md_years") or ((md_end - md_start).days / 365.2425 if md_start and md_end else 0.0))
            ads = antardashas_for(md_lord, md_start, yrs) if md_start and yrs else []
        except Exception:
            ads = []
    if not ads:
        ads = [x for x in (vim.get("current_md_antardashas") or []) if isinstance(x, dict)] if isinstance(vim, dict) else []

    ad_row = None
    for row in ads:
        a, b = _as_date(row.get("start")), _as_date(row.get("end"))
        lord = str(row.get("ad_lord") or row.get("lord") or "")
        if lord == ad_lord and a and b and a <= today <= b:
            ad_row = row
            break
    if ad_row is None:
        ad_row = next((x for x in ads if x.get("status") == "current"), None)

    current = "-".join(x for x in (md_lord, ad_lord) if x)
    current_start = str(_as_date(ad_row.get("start")) or md_start or "") if ad_row else str(md_start or "")
    current_end = str(_as_date(ad_row.get("end")) or md_end or "") if ad_row else str(md_end or "")

    # First AD after the current AD, then next MD if current MD is exhausted.
    next_ad = None
    for row in sorted(ads, key=lambda x: str(x.get("start") or "")):
        a = _as_date(row.get("start"))
        if a and a > today:
            next_ad = row
            break
    next_name = next_start = next_end = ""
    if next_ad:
        next_name = "-".join(x for x in (md_lord, str(next_ad.get("ad_lord") or next_ad.get("lord") or "")) if x)
        next_start, next_end = str(_as_date(next_ad.get("start")) or ""), str(_as_date(next_ad.get("end")) or "")
    else:
        next_md = None
        for row in sorted([x for x in (vim.get("sequence") or []) if isinstance(x, dict)], key=lambda x: str(x.get("start") or "")):
            a = _as_date(row.get("start"))
            if a and a > today:
                next_md = row
                break
        if next_md:
            nmd = str(next_md.get("md_lord") or next_md.get("lord") or "")
            next_name = nmd
            next_start, next_end = str(_as_date(next_md.get("start")) or ""), str(_as_date(next_md.get("end")) or "")

    houses=[]
    for pl in (md_lord, ad_lord):
        h=int(((pc.get("planets") or {}).get(pl) or {}).get("house") or 0)
        if h and h not in houses: houses.append(h)
    vim_tone = 0.0
    try:
        from report_confluence import dasha_confluence
        dc=dasha_confluence(pc,today) or {}
        r=next((x for x in (dc.get("readings") or []) if x.get("kind")=="vimshottari"),{})
        vim_tone=float(r.get("tone") or 0.0)
    except Exception: pass
    out.append(DashaClockFact(system="vimshottari", current=current, current_start=current_start,
                              current_end=current_end, next=next_name, next_start=next_start,
                              next_end=next_end, activated_houses=houses,
                              judgement="good" if vim_tone >= .35 else "challenging" if vim_tone <= -.35 else "moderate"))

    # ------------------------------------------------------------------
    # Chara: use jaimini_at() for the exact current maha/antar and the full
    # precomputed maha/antar lists for exact future boundaries.
    # ------------------------------------------------------------------
    try:
        try:
            from report_confluence import jaimini_at
            jai=jaimini_at(pc,today) or {}
        except Exception:
            jai={}
        maha=str(jai.get("sign") or "")
        antar=str(jai.get("antar") or "")
        maha_start=str(jai.get("maha_start") or "")
        maha_end=str(jai.get("maha_end") or "")
        antar_start=str(jai.get("antar_start") or "")
        antar_end=str(jai.get("antar_end") or "")
        block={}
        try:
            from jaimini_chara_dasha import get_chara_dasha
            block=get_chara_dasha(pc) or {}
        except Exception:
            block=pc.get("chara_dasha") or (pc.get("jaimini") or {}).get("chara_dasha") or {}
        # Some precompute versions do not expose jaimini_at(); resolve the
        # active Chara Maha/Antar directly from the dated tables instead of
        # returning an empty clock. This keeps one authoritative date-aware
        # clock for the analytical report.
        if not maha:
            for m in (block.get("maha") or []):
                a,b=_as_date(m.get("start")),_as_date(m.get("end"))
                if a and b and a <= today <= b:
                    maha=str(m.get("sign") or "")
                    maha_start,maha_end=str(a),str(b)
                    break
        if not antar:
            for arow in (block.get("antar") or []):
                a,b=_as_date(arow.get("start")),_as_date(arow.get("end"))
                if a and b and a <= today <= b:
                    antar=str(arow.get("sign") or "")
                    antar_start,antar_end=str(a),str(b)
                    if not maha:
                        maha=str(arow.get("maha_sign") or "")
                    break
        # If jaimini_at has no boundaries, resolve them from full tables.
        if not maha_start or not maha_end:
            for m in (block.get("maha") or []):
                a,b=_as_date(m.get("start")),_as_date(m.get("end"))
                if str(m.get("sign") or "") == maha and a and b and a <= today <= b:
                    maha_start,maha_end=str(a),str(b); break
        if not antar_start or not antar_end:
            for arow in (block.get("antar") or []):
                a,b=_as_date(arow.get("start")),_as_date(arow.get("end"))
                if str(arow.get("sign") or "") == antar and a and b and a <= today <= b:
                    antar_start,antar_end=str(a),str(b); break
        # Next actual Chara antar, otherwise next maha.
        next_name=next_start=next_end=""
        candidates=[]
        for arow in (block.get("antar") or []):
            a=_as_date(arow.get("start"))
            if a and a>today: candidates.append(arow)
        if candidates:
            n=min(candidates,key=lambda x:_as_date(x.get("start")) or date.max)
            ns=str(n.get("maha_sign") or maha)
            na=str(n.get("sign") or "")
            next_name="-".join(x for x in (ns,na) if x)
            next_start=str(_as_date(n.get("start")) or ""); next_end=str(_as_date(n.get("end")) or "")
        else:
            candidates=[m for m in (block.get("maha") or []) if (_as_date(m.get("start")) and _as_date(m.get("start"))>today)]
            if candidates:
                n=min(candidates,key=lambda x:_as_date(x.get("start")) or date.max)
                next_name=str(n.get("sign") or ""); next_start=str(_as_date(n.get("start")) or ""); next_end=str(_as_date(n.get("end")) or "")
        lagna=str(((pc.get("lagna") or {}).get("sign")) or "")
        houses=[]
        for sign in (maha,antar):
            h=_house_from_sign(lagna,sign)
            if h and h not in houses: houses.append(h)
        tone=0.0
        try:
            dc=__import__("report_confluence").dasha_confluence(pc,today) or {}
            r=next((x for x in (dc.get("readings") or []) if x.get("kind")=="chara"),{})
            tone=float(r.get("tone") or 0.0)
        except Exception: pass
        out.append(DashaClockFact(system="chara", current="-".join(x for x in (maha,antar) if x),
                                  current_start=antar_start or maha_start,current_end=antar_end or maha_end,
                                  next=next_name,next_start=next_start,next_end=next_end,activated_houses=houses,
                                  judgement="good" if tone >= .35 else "challenging" if tone <= -.35 else "moderate"))
    except Exception:
        out.append(DashaClockFact(system="chara"))

    # ------------------------------------------------------------------
    # Yogini: use the full dated cycle, not only the stamped current/next rows.
    # ------------------------------------------------------------------
    yog=pc.get("yogini") or {}
    if isinstance(yog,dict):
        cur={}
        try:
            from report_confluence import yogini_at
            cur=yogini_at(pc,today) or {}
        except Exception: cur=yog.get("current_yogini") or {}
        cycle=[x for x in (yog.get("full_cycle") or []) if isinstance(x,dict)]
        nxt=None
        for row in sorted(cycle,key=lambda x:str(x.get("start") or "")):
            a=_as_date(row.get("start"))
            if a and a>today: nxt=row; break
        lord=str(cur.get("lord") or "")
        h=int(((pc.get("planets") or {}).get(lord) or {}).get("house") or 0)
        houses=[h] if h else []
        tone=str(cur.get("tone") or "").lower()
        yscore=1.0 if tone in ("auspicious","good","supportive") else -1.0 if tone in ("inauspicious","bad","challenging") else 0.0
        out.append(DashaClockFact(system="yogini",current=str(cur.get("yogini") or ""),
                                  current_start=str(_as_date(cur.get("start")) or ""),current_end=str(_as_date(cur.get("end")) or ""),
                                  next=str((nxt or {}).get("yogini") or ""),next_start=str(_as_date((nxt or {}).get("start")) or ""),next_end=str(_as_date((nxt or {}).get("end")) or ""),
                                  activated_houses=houses,judgement="good" if yscore>.35 else "challenging" if yscore<-.35 else "moderate"))
    return out

def _crossover_points(clocks: list[DashaClockFact], today: date) -> list[CrossoverFact]:
    dates: dict[str, list[str]] = {}
    for c in clocks:
        for d in (c.current_end, c.next_start):
            if not d:
                continue
            ds = str(d)[:10]
            if _as_date(ds) and _as_date(ds) >= today:
                dates.setdefault(ds, []).append(c.system)
    out: list[CrossoverFact] = []
    for ds, systems in sorted(dates.items())[:8]:
        uniq = list(dict.fromkeys(systems))
        significance = "One timing clock changes." if len(uniq) == 1 else "Multiple timing clocks change or converge here."
        out.append(CrossoverFact(date=ds, systems=uniq, significance=significance))
    return out


def _current_transit(pc: dict, planet: str, today: date) -> Optional[dict]:
    try:
        from report_timing import transit_segments
        segs = (transit_segments(pc, start=today - __import__('datetime').timedelta(days=60), years=1) or {}).get(planet) or []
        for row in segs:
            a, b = _as_date(row.get("start")), _as_date(row.get("end"))
            if a and b and a <= today <= b:
                return row
    except Exception:
        pass
    if planet in ("Rahu", "Ketu"):
        try:
            from life_area_transition import _node_segments
            for row in _node_segments(pc, planet, today, 1):
                a, b = _as_date(row.get("start")), _as_date(row.get("end"))
                if a and b and a <= today <= b:
                    return row
        except Exception:
            pass
    return None


def _transit_fact(pc: dict, planet: str, today: date) -> Optional[SlowTransitFact]:
    row = _current_transit(pc, planet, today)
    if not row:
        return None
    sign = str(row.get("sign") or "")
    lagna = str(((pc.get("lagna") or {}).get("sign")) or "")
    natal_sign = str((((pc.get("planets") or {}).get(planet) or {}).get("sign")) or "")
    bav = row.get("bav")
    try:
        bav = int(bav) if bav is not None else None
    except Exception:
        bav = None
    if bav is None:
        judgement = "neutral"
    elif bav >= 5:
        judgement = "supportive"
    elif bav <= 3:
        judgement = "testing"
    else:
        judgement = "mixed"
    return SlowTransitFact(planet=planet, functional_role=_functional_role(pc, planet), sign=sign,
                           house=_house_from_sign(lagna, sign), from_natal_house=_house_from_sign(natal_sign, sign),
                           ashtakavarga=bav, start=str(row.get("start") or ""), end=str(row.get("end") or ""),
                           judgement=judgement)


def _dasha_planet_transits(pc: dict, clocks: list[DashaClockFact], today: date) -> list[DashaPlanetTransitFact]:
    planets: list[tuple[str, str]] = []
    vim = next((c for c in clocks if c.system == "vimshottari"), None)
    if vim and vim.current:
        parts = vim.current.split("-")
        if parts:
            planets.append((parts[0], "mahadasha"))
        if len(parts) > 1:
            planets.append((parts[1], "antardasha"))
    out = []
    seen = set()
    for planet, role in planets:
        if planet in seen:
            continue
        seen.add(planet)
        row = _current_transit(pc, planet, today)
        if not row:
            continue
        sign = str(row.get("sign") or "")
        natal_sign = str((((pc.get("planets") or {}).get(planet) or {}).get("sign")) or "")
        bav = row.get("bav")
        try:
            bav = int(bav) if bav is not None else None
        except Exception:
            bav = None
        judgement = "neutral" if bav is None else ("supportive" if bav >= 5 else "testing" if bav <= 3 else "mixed")
        out.append(DashaPlanetTransitFact(planet=planet, role=role, functional_role=_functional_role(pc, planet),
                                          sign=sign, house=_house_from_sign(str(((pc.get("lagna") or {}).get("sign")) or ""), sign),
                                          from_natal_planet=_house_from_sign(natal_sign, sign), ashtakavarga=bav, judgement=judgement))
    return out


def _jaimini_fact(pc: dict, today: date) -> JaiminiFact:
    """Return Jaimini facts without making availability depend on one helper.

    The analytical report must not collapse to "data not available" merely
    because a deployment's jaimini_at helper is absent. Karaka assignments and
    dated Chara signs are deterministic inputs already present in the chart
    payload, so they are a valid fallback. No judgement is invented when the
    actual Argala/tone calculation is unavailable.
    """
    try:
        from report_confluence import jaimini_at
        act = jaimini_at(pc, today) or {}
    except Exception:
        act = {}
    try:
        clocks = _dasha_clock_facts(pc, today)
        chara = next((c for c in clocks if c.system == "chara"), None)
    except Exception:
        chara = None
    maha = str(act.get("sign") or (str(chara.current).split("-")[0] if chara and chara.current else ""))
    antar = str(act.get("antar") or (str(chara.current).split("-")[1] if chara and "-" in str(chara.current) else ""))
    karaka_rows = [x for x in ((pc.get("jaimini") or {}).get("karakas") or []) if isinstance(x, dict)]
    if not karaka_rows:
        karaka_rows = [x for x in ((pc.get("cara_karakas") or {}).get("karakas") or []) if isinstance(x, dict)]
    role_map = {"AK":"Atmakarak", "AmK":"Amatyakarak", "GK":"Gnatikaraka", "PK":"Putrakaraka"}
    roles = {short: str(next((r.get("planet") for r in karaka_rows if str(r.get("role") or "") == role), ""))
             for short, role in role_map.items()}
    lagna = str(((pc.get("lagna") or {}).get("sign")) or "")
    houses=[]
    for sign in (maha, antar):
        h=_house_from_sign(lagna, sign)
        if h and h not in houses: houses.append(h)
    try:
        from jaimini_daily_confluence import build_jaimini_daily_confluence
        jc = build_jaimini_daily_confluence(pc=pc, birth_lagna=lagna, jaimini={"maha":maha,"antar":antar}) or {}
    except Exception:
        jc = {}
    tone = str(jc.get("tone") or "").lower()
    judgement={"supportive":"good","caution":"challenging","mixed":"moderate"}.get(tone, "insufficient")
    basis=[str(x)[:160] for x in (jc.get("highlights") or [])[:5]]
    if not basis and (maha or antar):
        basis.append("Chara timing is available from the dated Chara Dasha schedule.")
    if karaka_rows and not basis:
        basis.append("AK, AmK, GK and PK assignments are available from the chart's deterministic Jaimini karaka table.")
    available = bool(karaka_rows or maha or antar)
    argala = str(jc.get("reading") or "").strip()[:220]
    if not argala and available:
        argala = "Jaimini karaka and Chara timing data are available; detailed Argala tone is not available from this chart payload."
    return JaiminiFact(available=available, ak=roles["AK"], amk=roles["AmK"], gk=roles["GK"], pk=roles["PK"],
                       current_maha_sign=maha, current_antar_sign=antar, activated_houses=houses,
                       argala_judgement=argala, judgement=judgement, basis=basis)


def _score_label(score: float) -> str:
    if score >= 0.55:
        return "good"
    if score <= -0.55:
        return "challenging"
    if abs(score) < 0.18:
        return "mixed"
    return "moderate"


def _status_score(value: str) -> float:
    v = str(value or "").lower().replace("-", "_").replace(" ", "_")
    if "strongly_supported" in v or v in {"strong", "supported", "good", "supportive"}:
        return 1.0
    if "supported" in v:
        return 0.75
    if v in {"weak", "challenging", "caution", "testing", "down"}:
        return -0.75
    if "insufficient" in v or not v:
        return 0.0
    return 0.0


def _planet_tone(pc: dict, planet: str) -> float:
    if not planet:
        return 0.0
    info = (pc.get("planets") or {}).get(planet) or {}
    dignity = str(info.get("dignity") or "").lower()
    role = _functional_role(pc, planet)
    score = {
        "exalted": 1.0, "moolatrikona": .9, "own_sign": .75,
        "friendly_sign": .35, "neutral_sign": 0.0,
        "enemy_sign": -.45, "debilitated": -1.0,
    }.get(dignity, 0.0)
    score += {"benefic": .45, "yogakaraka": .65, "malefic": -.45,
              "maraka": -.30, "neutral": 0.0}.get(role, 0.0)
    return max(-1.5, min(1.5, score))


def _area_touches_planet(pc: dict, area: str, house: int, planet: str) -> bool:
    try:
        from report_confluence import _touches_area
        return bool(_touches_area(pc, area, house, planet))
    except Exception:
        if not planet:
            return False
        support = {"career": (10, 6, 11), "money": (2, 11), "love": (7, 5),
                   "home": (4, 2), "children": (5, 9), "health": (1, 6, 8),
                   "learning": (9, 5), "inner": (12, 9)}.get(area, (house,))
        info = (pc.get("planets") or {}).get(planet) or {}
        ph = int(info.get("house") or 0)
        lords = pc.get("house_lords") or {}
        return ph in support or any((lords.get(str(h)) or {}).get("lord") == planet for h in support)


def _dasha_system_scores(pc: dict, area: str, house: int, today: date) -> dict[str, float]:
    """Area-specific scores for the three requested dasha clocks.

    Each clock gets one bounded vote. The clocks are related timing systems, so
    they are kept as separate lanes for auditability but are capped together
    when the final life-area confluence is calculated.
    """
    scores = {"vimshottari": 0.0, "chara": 0.0, "yogini": 0.0}
    try:
        from report_confluence import dasha_confluence
        dc = dasha_confluence(pc, today) or {}
        for r in dc.get("readings") or []:
            kind = str(r.get("kind") or "")
            if kind not in scores or not r.get("label"):
                continue
            planets = [str(x) for x in (r.get("planets") or []) if x]
            relevant = any(_area_touches_planet(pc, area, house, pl) for pl in planets)
            # Chara signs are themselves area activators even if neither sign
            # lord nor resident planet is a direct house lord.
            if kind == "chara":
                lagna = str(((pc.get("lagna") or {}).get("sign")) or "")
                signs = [str(r.get("maha") or ""), str(r.get("antar") or "")]
                relevant = relevant or any(_house_from_sign(lagna, sg) in (house,) for sg in signs)
                # AmK/AK/DK/PK/GK relevance is added by the Jaimini lane below;
                # do not double count it here.
            scores[kind] = float(r.get("tone") or 0.0) if relevant else 0.0
    except Exception:
        pass
    return {k: max(-1.0, min(1.0, v)) for k, v in scores.items()}


def _jaimini_area_score(pc: dict, area: str, house: int, today: date) -> tuple[float, list[str]]:
    """Area-specific Jaimini score from Chara signs, karakas, SAV/BAV and Argala.

    This consumes the existing deterministic Jaimini engine. It does not ask
    Qwen to decide whether AK/AmK/etc. are supportive.
    """
    try:
        from report_confluence import jaimini_at
        from jaimini_daily_confluence import build_jaimini_daily_confluence
        lagna = str(((pc.get("lagna") or {}).get("sign")) or "")
        act = jaimini_at(pc, today) or {}
        jm = {"maha": act.get("sign"), "antar": act.get("antar")}
        data = build_jaimini_daily_confluence(pc=pc, birth_lagna=lagna, jaimini=jm) or {}
        if not data.get("available"):
            return 0.0, []
        role_map = {
            "career": {"Amatyakarak": 2.0, "Atmakarak": .5},
            "love": {"Darakaraka": 2.0, "Atmakarak": .5},
            "children": {"Putrakaraka": 2.0, "Atmakarak": .5},
            "home": {"Matrukaraka": 2.0, "Atmakarak": .5},
            "health": {"Gnatikaraka": 1.5, "Atmakarak": .25},
            "learning": {"Putrakaraka": 1.0, "Atmakarak": 1.0, "Amatyakarak": .5},
            "inner": {"Atmakarak": 1.5},
            "money": {"Amatyakarak": .75, "Atmakarak": .25},
        }.get(area, {"Atmakarak": .5})
        total = 0.0
        weight = 0.0
        reasons: list[str] = []
        for level in data.get("levels") or []:
            sign_house = _house_from_sign(lagna, str(level.get("sign") or ""))
            if sign_house not in (house, 0):
                # A Chara sign elsewhere can still matter through karaka sign
                # aspect, but the strongest area activation is the house match.
                house_factor = .5
            else:
                house_factor = 1.0
            for row in level.get("karakas") or []:
                role = str(row.get("role") or "")
                if role not in role_map:
                    continue
                raw = float(row.get("score") or 0.0)
                if raw == 0:
                    continue
                w = role_map[role] * house_factor
                # Existing rules6 score is roughly -2..4; normalize conservatively.
                tone = max(-1.0, min(1.0, raw / 3.0))
                total += tone * w
                weight += w
                if abs(tone) >= .25:
                    direction = "supports" if tone > 0 else "adds caution to"
                    reasons.append(f"{role} {row.get('planet','')} {direction} {area} in Chara {level.get('sign','')}")
        # Include the existing Argala/tone as one bounded Jaimini signal.
        overall = {"supportive": .75, "mixed": 0.0, "caution": -.75}.get(str(data.get("tone") or "mixed"), 0.0)
        if weight:
            score = .75 * (total / weight) + .25 * overall
        else:
            score = overall
        return max(-1.0, min(1.0, score)), reasons[:5]
    except Exception:
        return 0.0, []


def _divisional_score(verdict: str) -> float:
    v = str(verdict or "").lower()
    if any(x in v for x in ("strong", "support", "favour", "positive")):
        return .75
    if any(x in v for x in ("weak", "caution", "challenge", "negative")):
        return -.75
    return 0.0


def _slow_transits_at(pc: dict, when: date) -> list[SlowTransitFact]:
    """Return the slow-planet transit facts valid on an arbitrary future date."""
    out = []
    for planet in ("Jupiter", "Saturn"):
        row = _transit_fact(pc, planet, when)
        if row:
            out.append(row)
    return out


def _future_transit_event_dates(pc: dict, start: date, years: int = 4) -> set[date]:
    """Collect deterministic future transit boundaries from the existing timing engine.

    No transit date is guessed here. The report_timing engine owns the ephemeris;
    this function only turns its returned segment boundaries into evaluation dates.
    """
    dates: set[date] = set()
    try:
        from report_timing import transit_segments
        segs_by_planet = transit_segments(pc, start=start, years=years) or {}
        for planet, rows in segs_by_planet.items():
            for row in rows or []:
                for key in ("start", "end"):
                    d = _as_date(row.get(key))
                    if d and d >= start:
                        dates.add(d)
    except Exception:
        pass
    try:
        from life_area_transition import _node_segments
        for planet in ("Rahu", "Ketu"):
            for row in _node_segments(pc, planet, start, years) or []:
                for key in ("start", "end"):
                    d = _as_date(row.get(key))
                    if d and d >= start:
                        dates.add(d)
    except Exception:
        pass
    return dates


def _collect_schedule_dates(obj: Any, dates: set[date], start: date, horizon: date, depth: int = 0) -> None:
    """Extract only explicit start/end dates from known dasha schedule structures."""
    if depth > 5:
        return
    if isinstance(obj, dict):
        for key, value in obj.items():
            k = str(key).lower()
            if k in {"start", "end", "maha_start", "maha_end", "antar_start", "antar_end"}:
                d = _as_date(value)
                if d and start <= d <= horizon:
                    dates.add(d)
            # Timing schedules can be nested under these keys. Avoid walking
            # arbitrary chart metadata so unrelated dates do not become events.
            if k in {"sequence", "current_md_antardashas", "maha", "antar", "antardasha", "periods", "schedule", "yogini", "current_yogini", "next_yogini", "chara_dasha"}:
                _collect_schedule_dates(value, dates, start, horizon, depth + 1)
            elif isinstance(value, (dict, list)) and k in {"vimshottari", "chara_dasha", "yogini"}:
                _collect_schedule_dates(value, dates, start, horizon, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _collect_schedule_dates(item, dates, start, horizon, depth + 1)


def _future_dasha_event_dates(pc: dict, start: date, years: int = 4) -> set[date]:
    """Return every actual dasha boundary that can change a future confluence.

    Vimshottari antardashas are generated for every future Mahadasha because the
    precompute intentionally stores only the current MD's AD table. Chara uses
    its full maha + antar tables and Yogini uses its full dated cycle.
    """
    from datetime import timedelta
    horizon = start + timedelta(days=365 * years + 5)
    dates: set[date] = set()
    vim = pc.get("vimshottari") or {}
    try:
        from report_confluence import antardashas_for
        for md in (vim.get("sequence") or []):
            if not isinstance(md,dict): continue
            ms,me=_as_date(md.get("start")),_as_date(md.get("end"))
            if not ms or not me or me < start or ms > horizon: continue
            dates.update(d for d in (_as_date(md.get("start")),_as_date(md.get("end"))) if d and start <= d <= horizon)
            yrs=float(md.get("md_years") or ((me-ms).days/365.2425))
            for ad in antardashas_for(str(md.get("md_lord") or md.get("lord") or ""),ms,yrs):
                for key in ("start","end"):
                    d=_as_date(ad.get(key))
                    if d and start <= d <= horizon: dates.add(d)
    except Exception:
        _collect_schedule_dates(vim,dates,start,horizon)

    # Chara full schedule.
    try:
        from jaimini_chara_dasha import get_chara_dasha
        block=get_chara_dasha(pc) or {}
    except Exception:
        block=pc.get("chara_dasha") or (pc.get("jaimini") or {}).get("chara_dasha") or {}
    for row in list(block.get("maha") or []) + list(block.get("antar") or []):
        if isinstance(row,dict):
            for key in ("start","end"):
                d=_as_date(row.get(key))
                if d and start <= d <= horizon: dates.add(d)

    # Yogini full dated cycle.
    for row in ((pc.get("yogini") or {}).get("full_cycle") or []):
        if isinstance(row,dict):
            for key in ("start","end"):
                d=_as_date(row.get(key))
                if d and start <= d <= horizon: dates.add(d)
    return dates

def _timing_state_at(pc: dict, when: date, fallback: list[DashaClockFact]) -> list[DashaClockFact]:
    """Build timing clocks for a future date using the existing deterministic engines."""
    clocks = _dasha_clock_facts(pc, when)
    try:
        from report_confluence import dasha_confluence
        dc = dasha_confluence(pc, when) or {}
        by_kind = {str(r.get("kind") or ""): r for r in (dc.get("readings") or []) if isinstance(r, dict)}
        for clock in clocks:
            r = by_kind.get(clock.system)
            if not r:
                continue
            label = str(r.get("label") or "")
            if clock.system == "vimshottari":
                # dasha_confluence is the authoritative date-aware Vimshottari reader.
                if label:
                    clock.current = label
                clock.current_start = str(r.get("start") or r.get("current_start") or clock.current_start)
                clock.current_end = str(r.get("end") or r.get("current_end") or clock.current_end)
            elif clock.system == "chara":
                maha = str(r.get("maha") or "")
                antar = str(r.get("antar") or "")
                clock.current = "-".join(x for x in (maha, antar) if x) or label or clock.current
                clock.current_start = str(r.get("maha_start") or r.get("start") or clock.current_start)
                clock.current_end = str(r.get("maha_end") or r.get("end") or clock.current_end)
            elif clock.system == "yogini":
                if label:
                    clock.current = label
                clock.current_start = str(r.get("start") or clock.current_start)
                clock.current_end = str(r.get("end") or clock.current_end)
            tone = r.get("tone")
            if tone is not None:
                clock.judgement = "good" if float(tone) >= .35 else "challenging" if float(tone) <= -.35 else "moderate"
    except Exception:
        # Fall back to the best schedule data already available; never invent a date.
        return clocks or fallback
    return clocks or fallback


def _area_confluence_snapshot(pc: dict, card: Any, when: date, clocks: list[DashaClockFact], slow: list[SlowTransitFact]) -> dict[str, Any]:
    """Recalculate every life-area lane at *when* using the same current rules."""
    try:
        from client_question_engine import HOUSE_KARAKAS
    except Exception:
        HOUSE_KARAKAS = {}
    try:
        from report_confluence import AREA_VARGA, build_confluence
    except Exception:
        AREA_VARGA, build_confluence = {}, None
    try:
        from interpretation.evidence_builder import build_evidence
    except Exception:
        build_evidence = None

    area = str(getattr(card, "area", "") or "")
    house = int(getattr(card, "house", 0) or 0)
    lords = pc.get("house_lords") or {}
    planets = pc.get("planets") or {}
    hl = lords.get(house) or lords.get(str(house)) or {}
    lord = str(hl.get("lord") or "")
    lord_sign = str((planets.get(lord) or {}).get("sign") or "")
    depositor = ""
    try:
        from astro_precompute import SIGN_LORDS
        depositor = SIGN_LORDS.get(lord_sign, "")
    except Exception:
        pass

    cr = ((getattr(card, "confluence", None) or {}).get("canonical_result") or {})
    promise = ((cr.get("promise") or {}).get("status") or getattr(card, "status", "") or "mixed")
    natal_score = _status_score(promise)
    house_strength = "moderate"
    div = ""
    div_verdict = ""
    if build_evidence:
        try:
            ev = build_evidence(pc, area=area, house=house, direction=str(getattr(card, "direction", "") or "mixed"), row=None,
                                dasha={"md": "", "ad": "", "promise": promise, "bav": 0})
            div_verdict = str(getattr(ev, "divisional_support", "mixed") or "mixed")
            house_strength = str(getattr(ev, "house_strength", house_strength) or house_strength)
        except Exception:
            pass
    div, _ = AREA_VARGA.get(area, ("", ""))
    if not div_verdict:
        div_verdict = "available for cross-check" if div and div in (pc.get("divisional") or {}) else "not available"
    natal_score += {"strong": .45, "moderate": 0.0, "weak": -.45}.get(str(house_strength).lower(), 0.0)
    natal_score += _divisional_score(div_verdict) * .55
    lord_role = _functional_role(pc, lord)
    natal_score += {"benefic": .20, "yogakaraka": .30, "malefic": -.20, "maraka": -.15}.get(lord_role, 0.0)
    natal_score = max(-1.5, min(1.5, natal_score))

    dasha_scores = _dasha_system_scores(pc, area, house, when)
    slow_score = 0.0; slow_hits: list[str] = []
    for t in slow:
        if int(t.house or 0) == house:
            v = {"supportive": 1.0, "testing": -1.0, "mixed": 0.0, "neutral": 0.0}.get(t.judgement, 0.0)
            slow_score += v
            slow_hits.append(f"{t.planet} {t.sign} in H{t.house} ({t.functional_role})")
    slow_score = max(-1.0, min(1.0, slow_score / max(1, len(slow_hits)))) if slow_hits else 0.0

    dpt_score = 0.0; dpt_hits: list[str] = []
    vim = next((x for x in clocks if x.system == "vimshottari"), None)
    for planet in [x for x in str(vim.current if vim else "").split("-") if x]:
        row = _current_transit(pc, planet, when)
        if not row:
            continue
        sign = str(row.get("sign") or "")
        lagna = str(((pc.get("lagna") or {}).get("sign")) or "")
        h = int(_house_from_sign(lagna, sign) or 0)
        if h == house:
            bav = row.get("bav")
            tone = 1.0 if bav is not None and int(bav) >= 5 else -1.0 if bav is not None and int(bav) <= 3 else 0.0
            dpt_score += tone
            dpt_hits.append(f"{planet} in H{h}")
    dpt_score = max(-1.0, min(1.0, dpt_score / max(1, len(dpt_hits)))) if dpt_hits else 0.0

    ja_score, ja_reasons = _jaimini_area_score(pc, area, house, when)
    timing_raw = sum(dasha_scores.values()) / 3.0
    weights = {"natal": 1.35, "dasha": 1.15, "slow_transit": .90, "dasha_planet_transit": .65, "jaimini": .95}
    components = {"natal": natal_score, "dasha": timing_raw, "slow_transit": slow_score, "dasha_planet_transit": dpt_score, "jaimini": ja_score}
    final_score = max(-1.0, min(1.0, sum(components[k] * weights[k] for k in components) / sum(weights.values())))
    final = _score_label(final_score)
    decided = [v for v in components.values() if abs(v) >= .18]
    pos = sum(v > .18 for v in decided); neg = sum(v < -.18 for v in decided)
    agreement = "insufficient" if not decided else "conflicting" if pos and neg and abs(final_score) < .25 else "strong" if min(pos, neg) == 0 and len(decided) >= 3 else "good" if pos >= 2 or neg >= 2 else "mixed"
    lanes = {
        "Vimshottari": dasha_scores["vimshottari"], "Chara": dasha_scores["chara"], "Yogini": dasha_scores["yogini"],
        "Slow transit": slow_score, "Dasha-planet transit": dpt_score, "Jaimini": ja_score,
    }
    supporting=[]; caution=[]
    if natal_score > .25: supporting.append("Natal chart provides underlying support for this area.")
    if natal_score < -.25: caution.append("Natal foundation is comparatively weak for this area.")
    for name, sc in lanes.items():
        if sc > .35: supporting.append(f"{name} is supportive for this area at this date.")
        elif sc < -.35: caution.append(f"{name} adds pressure to this area at this date.")
    supporting.extend(ja_reasons[:3]); caution.extend(slow_hits[:2])
    return {
        "score": round(final_score, 3), "judgement": final, "agreement": agreement,
        "lanes": {k: _score_label(v) for k, v in lanes.items()}, "lane_scores": {k: round(v,3) for k,v in lanes.items()},
        "natal_score": round(natal_score,3), "supporting": list(dict.fromkeys([_canonical_astro_text(x) for x in supporting]))[:6],
        "caution": list(dict.fromkeys([_canonical_astro_text(x) for x in caution]))[:6], "slow_hits": slow_hits, "dpt_hits": dpt_hits,
        "clocks": clocks,
    }



def _date_iso(value: Any) -> str:
    """Return a strict YYYY-MM-DD date or an empty string.

    Future timing must never leak partial dates such as ``2027-`` into the
    customer report.  A partial/invalid value is treated as unavailable and
    is never presented as a forecast date.
    """
    d = _as_date(value)
    return d.isoformat() if d else ""


def _canonical_astro_text(text: str) -> str:
    """Preserve exact astrology terminology in the deterministic report."""
    repl = {
        "natural significator method": "Jaimini Karaka judgement",
        "natural significator": "Natural Karaka",
        "the main timing cycle": "Vimshottari",
        "Period-planet transit": "Dasha-planet transit",
        "period-planet transit": "Dasha-planet transit",
        "Atmakarak": "AK",
        "Amatyakarak": "AmK",
        "Gnatikaraka": "GK",
        "Putrakaraka": "PK",
        "AMK": "AmK",
    }
    out = str(text or "")
    for old, new in repl.items():
        out = out.replace(old, new)
    return out

def _future_transition_summary(future: list[FutureConfluenceFact], today: date) -> tuple[str, str, str]:
    """Return deterministic easing, sustained-Good and horizon conclusions.

    Easing is based on the calculated change_type. A dasha boundary alone is
    never sufficient. Sustained Good requires two consecutive published Good
    checkpoints; a single Good spike is deliberately not promoted to a
    sustained improvement claim.
    """
    valid = sorted(
        [x for x in future if _as_date(x.date) and _as_date(x.date) >= today],
        key=lambda x: _as_date(x.date),
    )
    if not valid:
        return "", "", ""

    easing = next(
        (x for x in valid if x.change_type in ("improves", "eases_but_continues")),
        None,
    )

    first_good = None
    # "Sustained" means the Good state survives at least two subsequent
    # published checkpoints. A one-checkpoint spike is never labelled sustained.
    for i, x in enumerate(valid):
        if x.judgement != "good" or _as_date(x.date) == today:
            continue
        later = valid[i + 1:]
        good_run = 0
        for nxt in later:
            if nxt.judgement == "good":
                good_run += 1
                if good_run >= 2:
                    first_good = x
                    break
            else:
                break
        if first_good:
            break

    horizon = valid[-1]
    horizon_date = _date_iso(horizon.date)
    if horizon.judgement == "good":
        horizon_text = (
            f"At the end of the forecast horizon ({horizon_date}), "
            "the complete confluence remains Good."
        )
    else:
        horizon_text = (
            f"At the end of the forecast horizon ({horizon_date}), "
            f"the complete confluence remains {horizon.judgement.title()}; "
            "no automatic relief is assumed."
        )

    return (
        _date_iso(easing.date) if easing else "",
        _date_iso(first_good.date) if first_good else "",
        horizon_text,
    )


def _future_confluence_for_area(pc: dict, card: Any, today: date, years: int = 4) -> list[FutureConfluenceFact]:
    """Evaluate the COMPLETE confluence at every meaningful future dasha/transit event.

    A dasha change is never treated as an automatic improvement. Every event date
    re-runs all lanes: natal baseline, all three dasha systems, slow transits,
    dasha-planet transit and Jaimini. Only material changes are surfaced.
    """
    from datetime import timedelta
    horizon = today + timedelta(days=365 * years + 5)
    event_dates = {today}
    event_dates.update(d for d in _future_dasha_event_dates(pc, today, years) if today <= d <= horizon)
    event_dates.update(d for d in _future_transit_event_dates(pc, today, years) if today <= d <= horizon)
    # Add the current crossover dates already calculated by the timing layer.
    try:
        for clock in _dasha_clock_facts(pc, today):
            for d in (clock.current_end, clock.next_start):
                x = _as_date(d)
                if x and today <= x <= horizon: event_dates.add(x)
    except Exception:
        pass

    # Evaluation dates can be numerous because every planetary segment boundary
    # is an event. Keep all calculations, but publish only baseline + material
    # judgement changes + explicitly meaningful dasha/transit dates.
    ordered = sorted(event_dates)
    previous = None
    published: list[FutureConfluenceFact] = []
    last_published_date = None
    for when in ordered:
        clocks = _timing_state_at(pc, when, _dasha_clock_facts(pc, today))
        slow = _slow_transits_at(pc, when)
        snap = _area_confluence_snapshot(pc, card, when, clocks, slow)
        score = float(snap["score"])
        judgement = str(snap["judgement"])
        change_type = "baseline" if previous is None else "continues"
        delta = 0.0 if previous is None else score - float(previous["score"])
        if previous is not None:
            if delta >= .22 and judgement in ("good", "moderate"):
                change_type = "improves"
            elif delta >= .12 and float(previous["score"]) < .35:
                change_type = "eases_but_continues"
            elif delta <= -.22:
                change_type = "worsens"
            elif abs(delta) >= .12:
                change_type = "mixed_change"
        prev_j = str(previous["judgement"]) if previous else "insufficient"
        dasha_changes=[]
        for system, key in (("vimshottari","current"),("chara","current"),("yogini","current")):
            cur = next((c for c in clocks if c.system == system), None)
            prev_clock = next((c for c in (previous.get("clocks") if previous else []) if c.system == system), None)
            if cur and (not prev_clock or cur.current != prev_clock.current):
                dasha_changes.append(f"{system.title()}: {cur.current or 'changed'}")
        transit_events=[]
        for t in slow:
            transit_events.append(f"{t.planet}: {t.sign} / H{t.house} / {t.judgement}")
        for planet in ("Rahu","Ketu"):
            row=_current_transit(pc,planet,when)
            if row:
                sign=str(row.get("sign") or "")
                lagna=str(((pc.get("lagna") or {}).get("sign")) or "")
                transit_events.append(f"{planet}: {sign} / H{_house_from_sign(lagna,sign)}")
        meaningful = previous is None or change_type != "continues" or bool(dasha_changes)
        # Avoid duplicate same-day rows and compress pure transit churn that does
        # not alter the life-area judgement.
        if meaningful and (last_published_date != when):
            reason_parts=[]
            if change_type == "improves": reason_parts.append("the complete confluence becomes materially more supportive")
            elif change_type == "eases_but_continues": reason_parts.append("pressure reduces but the overall judgement remains below good")
            elif change_type == "worsens": reason_parts.append("the complete confluence becomes more challenging")
            elif change_type == "mixed_change": reason_parts.append("supportive and cautionary factors change together")
            elif previous is not None: reason_parts.append("the timing changes without a material change in the final judgement")
            else: reason_parts.append("baseline evaluation from the current chart and timing")
            if dasha_changes: reason_parts.append("; ".join(dasha_changes[:3]))
            reason=_canonical_astro_text("; ".join(reason_parts)[:280])
            published.append(FutureConfluenceFact(
                date=when.isoformat(), change_type=change_type, previous_judgement=prev_j,
                judgement=judgement, score=score, agreement=snap["agreement"],
                vimshottari=next((c.current for c in clocks if c.system=="vimshottari"),""),
                chara=next((c.current for c in clocks if c.system=="chara"),""),
                yogini=next((c.current for c in clocks if c.system=="yogini"),""),
                transit_events=list(dict.fromkeys(transit_events))[:8], dasha_changes=dasha_changes[:6],
                lane_judgements=dict(snap["lanes"]), lane_scores=dict(snap["lane_scores"]),
                supporting_factors=[_canonical_astro_text(x) for x in snap["supporting"]], caution_factors=[_canonical_astro_text(x) for x in snap["caution"]], reason=reason,
            ))
            last_published_date=when
        previous={"score":score,"judgement":judgement,"clocks":clocks}

    # Always include the first material improvement/worsening and the last known
    # state in the horizon, so the prose can say firmly whether pressure eases,
    # continues, or worsens instead of assuming the next dasha is beneficial.
    if published:
        final_date = max(ordered)
        if published[-1].date != final_date.isoformat():
            clocks = _timing_state_at(pc, final_date, _dasha_clock_facts(pc, today))
            slow = _slow_transits_at(pc, final_date)
            snap = _area_confluence_snapshot(pc, card, final_date, clocks, slow)
            published.append(FutureConfluenceFact(date=final_date.isoformat(), change_type="continues",
                previous_judgement=published[-1].judgement, judgement=snap["judgement"], score=snap["score"], agreement=snap["agreement"],
                vimshottari=next((c.current for c in clocks if c.system=="vimshottari"),""),
                chara=next((c.current for c in clocks if c.system=="chara"),""),
                yogini=next((c.current for c in clocks if c.system=="yogini"),""),
                transit_events=[], dasha_changes=[], lane_judgements=dict(snap["lanes"]), lane_scores=dict(snap["lane_scores"]),
                supporting_factors=[_canonical_astro_text(x) for x in snap["supporting"]], caution_factors=[_canonical_astro_text(x) for x in snap["caution"]],
                reason="End-of-horizon complete confluence check; no automatic improvement is assumed."))
    # Do not truncate blindly at the first 16 events: doing so can hide the
    # first genuine relief point late in the horizon. Keep baseline, all
    # material judgement changes, dasha changes, first Good checkpoint, and
    # the horizon endpoint, then fill remaining slots chronologically.
    if not published:
        return []
    horizon_event = published[-1]
    selected=[]
    for ev in published:
        if ev.change_type != "continues" or ev is published[0]:
            selected.append(ev)
    good_idx = next((i for i, ev in enumerate(published) if ev.judgement == "good" and i > 0), None)
    if good_idx is not None:
        selected.append(published[good_idx])
    selected.append(horizon_event)
    # Deduplicate by date while preserving chronology.
    uniq={ev.date: ev for ev in selected if _as_date(ev.date)}
    remaining=[ev for ev in published if ev.date not in uniq]
    for ev in remaining:
        if len(uniq) >= 16: break
        uniq[ev.date]=ev
    return [uniq[k] for k in sorted(uniq, key=lambda x: _as_date(x))]


def _confluence_customer_labels(judgement: str, natal_promise: str, score: float) -> tuple[str, str]:
    """Stable customer-facing labels; raw confluence scores stay internal."""
    j = str(judgement or "insufficient").lower()
    if j == "good":
        confluence = "Favourable"
        activation = "Strongly active"
    elif j == "moderate":
        confluence = "Moderately supportive"
        activation = "Moderately active"
    elif j == "challenging":
        confluence = "Needs care"
        activation = "Active but demanding"
    elif j == "mixed":
        confluence = "Mixed"
        activation = "Developing / mixed"
    else:
        confluence = "Insufficient evidence"
        activation = "Not clearly active"
    return activation, confluence


def _life_area_judgements(pc: dict, cards: list, clocks: list[DashaClockFact], slow: list[SlowTransitFact], today: date) -> list[LifeAreaJudgementFact]:
    """Calculate current and future life-area judgements from complete confluence.

    Current and future verdicts use the same deterministic lane weights. A dasha
    change never implies relief by itself; future transit/dasha/Jaimini state is
    recalculated at every meaningful event date.
    """
    try:
        from client_question_engine import HOUSE_KARAKAS
    except Exception:
        HOUSE_KARAKAS = {}
    try:
        from report_confluence import AREA_VARGA
    except Exception:
        AREA_VARGA = {}
    try:
        from interpretation.evidence_builder import build_evidence
    except Exception:
        build_evidence = None
    out=[]
    lords=pc.get("house_lords") or {}; planets=pc.get("planets") or {}
    labels={str(getattr(c,"area", "")): str(getattr(c,"label", "")) for c in cards}
    for c in cards:
        area=str(getattr(c,"area","") or ""); house=int(getattr(c,"house",0) or 0)
        if not area: continue
        hl=lords.get(house) or lords.get(str(house)) or {}; lord=str(hl.get("lord") or "")
        lord_sign=str((planets.get(lord) or {}).get("sign") or ""); depositor=""
        try:
            from astro_precompute import SIGN_LORDS
            depositor=SIGN_LORDS.get(lord_sign,"")
        except Exception: pass
        cr=((getattr(c,"confluence",None) or {}).get("canonical_result") or {})
        promise=((cr.get("promise") or {}).get("status") or getattr(c,"status","") or "mixed")
        natal_score=_area_confluence_snapshot(pc,c,today,clocks,slow)["natal_score"]
        house_strength="moderate"; div=""; div_verdict=""
        if build_evidence:
            try:
                ev=build_evidence(pc,area=area,house=house,direction=str(getattr(c,"direction","") or "mixed"),row=None,dasha={"md":"","ad":"","promise":promise,"bav":0})
                div_verdict=str(getattr(ev,"divisional_support","mixed") or "mixed"); house_strength=str(getattr(ev,"house_strength",house_strength) or house_strength)
            except Exception: pass
        div,_=AREA_VARGA.get(area,("", ""))
        if not div_verdict: div_verdict="available for cross-check" if div and div in (pc.get("divisional") or {}) else "not available"
        snap=_area_confluence_snapshot(pc,c,today,clocks,slow)
        lanes=snap["lanes"]
        current_vim=next((x.current for x in clocks if x.system=="vimshottari"),"")
        current_chara=next((x.current for x in clocks if x.system=="chara"),"")
        current_yog=next((x.current for x in clocks if x.system=="yogini"),"")
        next_vim=next((x.next for x in clocks if x.system=="vimshottari"),"")
        future=_future_confluence_for_area(pc,c,today)
        relief, stronger, horizon_text = _future_transition_summary(future, today)
        future_summary=""
        if future:
            first=next((x for x in future if x.change_type in ("improves","eases_but_continues","worsens","mixed_change")),future[0])
            first_date=_date_iso(first.date)
            if first_date:
                future_summary=f"Future confluence is recalculated at every material dasha/transit change. First material change: {first.change_type.replace('_',' ')} on {first_date}; judgement {first.judgement}."
            if horizon_text:
                future_summary += " " + horizon_text
        current_summary=_canonical_astro_text(f"Final life-area confluence is {snap['judgement']}; natal foundation is {_score_label(snap['natal_score'])}, "
                         f"while Vimshottari is {lanes['Vimshottari']}, Chara is {lanes['Chara']}, Yogini is {lanes['Yogini']}, "
                         f"slow transits are {lanes['Slow transit']}, dasha-planet transit is {lanes['Dasha-planet transit']}, and Jaimini is {lanes['Jaimini']}.")
        activation_label, confluence_label = _confluence_customer_labels(snap["judgement"], promise, snap["score"])
        out.append(LifeAreaJudgementFact(
            area=area,label=labels.get(area) or area.title(),house=house,
            natural_karakas=[str(x) for x in HOUSE_KARAKAS.get(house,[])[:4]],house_lord=lord,house_lord_role=_functional_role(pc,lord),depositor=depositor,
            house_strength=house_strength,divisional_chart=div,divisional_verdict=div_verdict,amk=next((str(x.get("planet")) for x in ((pc.get("jaimini") or {}).get("karakas") or []) if isinstance(x,dict) and x.get("role")=="Amatyakarak"),""),
            natal_promise=str(promise),current_vimshottari=current_vim,current_chara=current_chara,current_yogini=current_yog,current_transit="; ".join(snap["slow_hits"][:4]),next_period=next_vim,
            final_judgement=snap["judgement"],current_summary=current_summary,future_summary=future_summary,remedy_reason=(snap["caution"][0] if snap["caution"] else ""),
            natal_foundation_score=round(snap["natal_score"],3),confluence_score=snap["score"],confluence_agreement=snap["agreement"],
            activation_label=activation_label,confluence_label=confluence_label,lane_judgements=lanes,
            lane_scores=snap["lane_scores"],supporting_factors=snap["supporting"],caution_factors=snap["caution"],activated_houses=sorted(set([house]+[int(x) for x in (next((z.activated_houses for z in clocks if z.system=="vimshottari"),[]) or []) if x])),current_verdict=snap["judgement"],relief_window=relief,stronger_window=stronger,future_confluence=future,
        ))
    return out

def _validate_authoritative_dasha_context(vedic: VedicContext, clocks: list[DashaClockFact]) -> None:
    """Fail closed if the report has two different current Vimshottari clocks."""
    vim = next((c for c in clocks if c.system == "vimshottari"), None)
    if not vim:
        return
    parts = [x for x in str(vim.current or "").split("-") if x]
    md = parts[0] if parts else ""
    ad = parts[1] if len(parts) > 1 else ""
    if vedic.mahadasha and md and vedic.mahadasha != md:
        raise ValueError(f"Vimshottari MD mismatch: context={vedic.mahadasha} clock={md}")
    if vedic.antardasha and ad and vedic.antardasha != ad:
        raise ValueError(f"Vimshottari AD mismatch: context={vedic.antardasha} clock={ad}")


def build_report_facts(
    pc: dict,
    cards: list,
    *,
    name: str = "",
    access: str = "free",
    today: Optional[date] = None,
    report_id: str = "",
) -> ReportFacts:
    """Build ReportFacts from precomputed chart + already-built Card list."""
    today = today or date.today()
    gender, age_years, age_band = _profile_context(pc, today)

    card_facts: list[CardFacts] = []
    for c in cards or []:
        area = getattr(c, "area", "") or ""
        kind = "challenge" if area in ("health", "troubles") else "promise"
        cf = getattr(c, "confluence", None) or {}
        if not isinstance(cf, dict):
            cf = {}
        cr = cf.get("canonical_result") or {}
        promise = (cr.get("promise") or cf.get("promise") or {})
        activation = (cr.get("activation") or cf.get("activation") or {})
        why = cr.get("why") or {}
        status = str(promise.get("status") or "").strip() or "insufficient_evidence"
        act_status = str(activation.get("status") or "").strip() or "inactive"
        if cr.get("kind") == "challenge" or promise.get("kind") == "challenge":
            kind = "challenge"

        # Canonical why.rows are already normalized method-level evidence.
        # Prefer those over raw legacy promise text. If a legacy result has no
        # normalized rows, convert its raw evidence through the same sanitizer.
        support_ev = list(why.get("supporting") or [])[:6]
        caution_ev = list(why.get("caution") or [])[:6]
        evidence: list[EvidenceFact] = []
        rows = list(why.get("rows") or [])
        if rows:
            for row in rows[:8]:
                if not isinstance(row, dict):
                    continue
                pol = str(row.get("direction") or "neutral").lower()
                polarity = "support" if pol in ("support", "up") else "caution"
                reasons = row.get("reasons") or []
                if not isinstance(reasons, list):
                    reasons = [reasons]
                reason = str(row.get("reason") or (reasons[0] if reasons else "")).strip()
                text, tags = _normalize_evidence_text(reason)
                if text or tags:
                    evidence.append(EvidenceFact(
                        family="other", polarity=polarity,
                        text_id=_eid("row", polarity, reason or str(row)),
                        text=text,
                        semantic_tags=tags,
                    ))
        else:
            for t in support_ev:
                text, tags = _normalize_evidence_text(str(t))
                if text or tags:
                    evidence.append(EvidenceFact(
                        family="other", polarity="support",
                        text_id=_eid("sup", "support", str(t)),
                        text=text,
                        semantic_tags=tags,
                    ))
            for t in caution_ev:
                text, tags = _normalize_evidence_text(str(t))
                if text or tags:
                    evidence.append(EvidenceFact(
                        family="other", polarity="caution",
                        text_id=_eid("cau", "caution", str(t)),
                        text=text,
                        semantic_tags=tags,
                    ))

        manifests = list(cr.get("manifestation") or cr.get("manifestations") or [])[:6]
        # Manifestations are canonical IDs/phrases. Resolve known IDs to their
        # modern meaning before sending them to Qwen; unknown raw classical
        # strings are discarded rather than paraphrased by the model.
        safe_manifests: list[str] = []
        try:
            from interpretation.stage_config import manifestation_metadata
            for m in manifests:
                meta = manifestation_metadata(str(m)) or {}
                modern = str(meta.get("modern_meaning") or "").strip()
                if modern:
                    safe_manifests.append(modern[:120])
                # Unknown IDs are deliberately discarded. They are not safe
                # customer language and must not be paraphrased by the model.
        except Exception:  # noqa: BLE001
            safe_manifests = []
        if not safe_manifests:
            # Same catalog the renderer falls back to, so the model describes
            # the manifestations the reader is going to see anyway.
            try:
                import area_modules as AM
                safe_manifests = [
                    str(m)[:120]
                    for m in AM.manifestations_for(
                        area,
                        promise_status=status,
                        activation_status=act_status,
                        age_band=age_band,
                        limit=3,
                        pc=pc,
                    )
                    or []
                ]
            except Exception:  # noqa: BLE001
                safe_manifests = []
        manifests = safe_manifests[:6]
        semantic_tags = list(cr.get("semantic_tags") or [])[:8]
        if kind == "challenge" and not semantic_tags:
            semantic_tags = ["wellbeing_sensitivity", "routine", "recovery"]

        window = None
        w = getattr(c, "window", "") or ""
        if w:
            window = WindowFact(label=str(w)[:120])

        evidence = _dedupe_evidence(evidence)[:6]

        score = float(cr.get("score") or promise.get("score") or 0.0)
        conf = _conf(
            cr.get("confidence")
            or promise.get("confidence")
            or getattr(c, "agreement", "")
            or "low"
        )
        direction = _dir(cr.get("direction") or getattr(c, "direction", "mixed"))
        agreement = _agreement(
            cr.get("agreement") or getattr(c, "agreement", "") or conf
        )
        best_win = (cr.get("timing") or {}).get("best_window") if cr else None
        if not isinstance(best_win, dict):
            featured = list((cr.get("timing") or {}).get("featured_windows") or [])
            strong = list((cr.get("timing") or {}).get("strong_windows") or [])
            validated = list((cr.get("timing") or {}).get("validated_windows") or [])
            candidates = featured or strong or validated
            best_win = candidates[0] if candidates else None
        if isinstance(best_win, dict):
            window = WindowFact(
                start=_pretty_date(best_win.get("start")),
                end=_pretty_date(best_win.get("end")),
                label=str(best_win.get("event_type") or best_win.get("label") or area)[:120],
                event_type=str(best_win.get("event_type") or "")[:80],
                confidence=_conf(best_win.get("confidence") or conf),  # type: ignore[arg-type]
                source=str(best_win.get("source") or "validated_confluence")[:80],
                score=float(best_win.get("score") or 0.0),
            )

        wealth_sub: list[dict] = []
        if area == "money":
            try:
                from personalized_confluence import resolve_wealth_subareas
                subs = resolve_wealth_subareas(pc) or {}
                for k, v in (subs.items() if isinstance(subs, dict) else []):
                    if isinstance(v, dict):
                        wealth_sub.append({
                            "key": k,
                            "status": v.get("status", ""),
                            "score": v.get("score", 0.0),
                            "label": (v.get("label") or "")[:120],
                        })
            except Exception:  # noqa: BLE001
                wealth_sub = []

        card_timing: list[WindowFact] = []
        timing_rows = list((cr.get("timing") or {}).get("featured_windows") or [])
        if not timing_rows:
            timing_rows = list((cr.get("timing") or {}).get("strong_windows") or [])
        if not timing_rows:
            timing_rows = list((cr.get("timing") or {}).get("validated_windows") or [])
        seen_card_windows: set[tuple[str, str, str]] = set()
        for tw in timing_rows[:4]:
            if not isinstance(tw, dict):
                continue
            wk = (str(tw.get("start") or ""), str(tw.get("end") or ""), str(tw.get("event_type") or tw.get("label") or area))
            if wk in seen_card_windows:
                continue
            seen_card_windows.add(wk)
            card_timing.append(WindowFact(
                start=_pretty_date(tw.get("start")), end=_pretty_date(tw.get("end")),
                label=str(tw.get("event_type") or tw.get("label") or area)[:120],
                event_type=str(tw.get("event_type") or area)[:80],
                confidence=_conf(tw.get("confidence") or conf),
                source=str(tw.get("source") or "validated_confluence")[:80],
                score=float(tw.get("score") or 0.0),
            ))
        # An area can read "active" from the running period while every dated
        # window on the card still sits years out. When that happens the dates
        # decide the wording: "Active now" printed above "Dec 2028" is the
        # fastest way to lose a reader.
        if act_status in ("active", "strongly_active"):
            dated: list[Any] = list(getattr(c, "transition_map", None) or [])
            if not dated:
                dated = [tw for tw in timing_rows[:6] if isinstance(tw, dict)]
            try:
                from life_area_transition import window_state
                if window_state(dated, today=today).get("state") == "upcoming":
                    act_status = "inactive"
            except Exception:  # noqa: BLE001
                pass

        allowed_dates = _dates_from_windows(window)
        for tw in card_timing:
            allowed_dates.extend(_dates_from_windows(tw))
        allowed_dates = list(dict.fromkeys(allowed_dates))[:12]
        blob = " ".join(
            [str(t) for t in support_ev + caution_ev]
            + [str(x) for x in manifests]
        )
        allowed_planets = _planets_from_text(blob)

        # The practical step already approved for this area. Passing it lets a
        # card carry its own "what helps" line instead of pushing every reader
        # to one remedy block at the end of the report.
        approved: list[str] = []
        for candidate in (getattr(c, "action", ""), getattr(c, "mantra", "")):
            text = str(candidate or "").strip()
            if text and text not in approved:
                try:
                    from qa_checks.customer_text_sanitizer import is_customer_safe
                    if not is_customer_safe(text, area=area):
                        continue
                except Exception:  # noqa: BLE001
                    pass
                approved.append(text[:160])

        outlook_line = ""
        try:
            from narration.verdict_phrases import promise_activation_line
            outlook_line = promise_activation_line(
                promise_status=status, activation_status=act_status,
            )[:220]
        except Exception:  # noqa: BLE001
            outlook_line = str(getattr(c, "headline", "") or "")[:220]
        if not outlook_line:
            outlook_line = str(getattr(c, "headline", "") or "")[:220]

        remedy_text = ""
        for candidate in (
            cr.get("remedy"),
            (cf.get("remedy") if isinstance(cf, dict) else None),
        ):
            text = str(candidate or "").strip()
            if not text:
                continue
            try:
                from qa_checks.customer_text_sanitizer import is_customer_safe
                if not is_customer_safe(text, area=area):
                    continue
            except Exception:  # noqa: BLE001
                pass
            # Planet names are legitimate in a remedy (for example, a Saturn remedy).
            # Only classical/internal leakage is rejected here.
            if _CLASSICAL_RAW.search(text):
                continue
            remedy_text = text[:220]
            break
        if not remedy_text and approved:
            remedy_text = approved[0][:220]

        transition_map = []
        raw_map = list(getattr(c, "transition_map", None) or [])
        for row in raw_map[:6]:
            if hasattr(row, "model_dump"):
                row = row.model_dump()
            if isinstance(row, dict):
                payload = dict(row)
                conf = str(payload.get("confidence") or "low").lower()
                if conf not in ("high", "moderate", "low"):
                    payload["confidence"] = "high" if "high" in conf else "low"
                direction = str(payload.get("direction") or "mixed")
                if direction not in ("support", "caution", "mixed", "neutral", "up", "down"):
                    payload["direction"] = "mixed"
                try:
                    transition_map.append(TransitionFact.model_validate(payload))
                except Exception:
                    continue

        transit_context = []
        for row in list(getattr(c, "transit_context", None) or [])[:14]:
            if hasattr(row, "model_dump"):
                row = row.model_dump()
            if not isinstance(row, dict):
                continue
            try:
                transit_context.append(TransitContextFact.model_validate(dict(row)))
            except Exception:
                continue

        card_facts.append(CardFacts(
            area=area,
            label=str(getattr(c, "label", "") or area),
            kind=kind,  # type: ignore[arg-type]
            status=status,
            activation_status=act_status,
            confidence=conf,  # type: ignore[arg-type]
            prediction_strength=status,
            agreement=agreement,  # type: ignore[arg-type]
            direction=direction,  # type: ignore[arg-type]
            score=round(score, 3),
            support_n=len(support_ev),
            caution_n=len(caution_ev),
            house=int(getattr(c, "house", 0) or 0),
            evidence=evidence[:6],
            manifestation_ids=[str(m)[:80] for m in manifests if m][:6],
            semantic_tags=[str(t)[:60] for t in semantic_tags if t][:8],
            window=window,
            timing_windows=card_timing,
            question_lens=QUESTION_LENS.get(area, f"What does your chart say about {getattr(c, 'label', area)}?"),
            remedy_eligible=bool(approved or remedy_text),
            approved_remedies=approved[:3],
            wealth_sub=wealth_sub,
            allowed_planets=allowed_planets,
            allowed_dates=allowed_dates,
            outlook_line=outlook_line,
            manifestations=[str(m)[:120] for m in manifests if m][:4],
            remedy_text=remedy_text,
            transition_map=transition_map,
            transit_context=transit_context,
        ))

    # IMPORTANT: timing facts must come from the same canonical area results
    # used by cards/dashboard/Why. Never call RT.best_windows here a second time.
    timing_windows: list[WindowFact] = []
    seen_timing: set[tuple[str, str, str]] = set()
    for c in (cards or []):
        cf = getattr(c, "confluence", None) or {}
        if not isinstance(cf, dict):
            continue
        cr = cf.get("canonical_result") or {}
        t = cr.get("timing") or {}
        rows = list(t.get("featured_windows") or t.get("strong_windows")
                    or t.get("validated_windows") or [])
        for r in rows[:4]:
            if not isinstance(r, dict):
                continue
            key = (
                str(r.get("start") or ""),
                str(r.get("end") or ""),
                str(r.get("event_type") or r.get("label") or getattr(c, "area", "")),
            )
            if key in seen_timing:
                continue
            seen_timing.add(key)
            timing_windows.append(WindowFact(
                start=_pretty_date(r.get("start")),
                end=_pretty_date(r.get("end")),
                label=str(r.get("event_type") or r.get("label")
                          or getattr(c, "area", ""))[:120],
                event_type=str(r.get("event_type") or getattr(c, "area", ""))[:80],
                confidence=_conf(r.get("confidence") or "moderate"),  # type: ignore[arg-type]
                source=str(r.get("source") or "validated_confluence")[:80],
                score=float(r.get("score") or 0.0),
            ))
        if len(timing_windows) >= 8:
            break

    buckets: dict[str, list[str]] = {}
    hardest_areas: list[str] = []
    hardest_labels: list[str] = []
    try:
        import promise_dashboard as PD
        dash = PD.build(list(cards or [])) or {}
        for key, items in (dash.items() if isinstance(dash, dict) else []):
            out_list = []
            for i in (items or []):
                if isinstance(i, dict):
                    out_list.append(str(i.get("area") or i.get("key") or ""))
                else:
                    out_list.append(str(getattr(i, "area", "") or ""))
            buckets[str(key)] = [x for x in out_list if x]
        for i in (dash.get("needs_care") or []):
            area_key = str(getattr(i, "area", "") or (i.get("area") if isinstance(i, dict) else "") or "")
            label = str(getattr(i, "label", "") or (i.get("label") if isinstance(i, dict) else "") or area_key)
            if area_key and area_key not in hardest_areas:
                hardest_areas.append(area_key)
                hardest_labels.append(label)
    except Exception:  # noqa: BLE001
        buckets = {}

    personality_traits = _personality_traits(pc)
    phase_direction, phase_tone, phase_end, phase_notes = _phase_facts(pc, today)
    recent_months = _recent_month_facts(pc, today)
    # Personality reads thin when it comes from one source. The specialist
    # engines already describe the same person; personal_life keeps only the
    # sentences that survive the customer boundary.
    family_notes: list = []
    try:
        from .personal_life import build_personal_life
        extra_traits, family_notes = build_personal_life(pc, gender=gender)
        for t in extra_traits:
            if t not in personality_traits:
                personality_traits.append(t)
        personality_traits = personality_traits[:6]
    except Exception as exc:  # noqa: BLE001
        print(f"[llm.facts] personal life evidence skipped: {exc}", flush=True)
    # What may be occupying them now, read off the same canonical cards the
    # paid areas use, so the two halves of the page cannot disagree.
    life_state = None
    try:
        from .life_state import build_life_state
        life_state = build_life_state(
            card_facts, phase_tone=phase_tone, needs_care=hardest_areas)
    except Exception as exc:  # noqa: BLE001
        print(f"[llm.facts] life state skipped: {exc}", flush=True)
    # Ground month/year tokens used in phase and recent-months prose.
    for ev in recent_months:
        for d in (ev.start, ev.end):
            if d and d not in [w.label for w in timing_windows]:
                pass
    extra_dates: list[str] = []
    if phase_end:
        extra_dates.append(phase_end)
    for ev in recent_months:
        for d in (ev.start, ev.end):
            if d:
                extra_dates.append(d)
    # Attach allowed dates onto cards that have none so month validation works
    # for the whole-report conversational prompt.
    if extra_dates and card_facts:
        seed = list(dict.fromkeys(extra_dates))[:12]
        for cf in card_facts:
            if not cf.allowed_dates:
                cf.allowed_dates = list(seed)

    # New analytical layer: all values are calculated here, never by Qwen.
    _today = today or date.today()
    vedic = _vedic_context(pc, _today)
    timing_systems=[]; crossover_points=[]; slow_transits=[]; jaimini_fact=JaiminiFact(); dasha_planet_transits=[]; life_area_judgements=[]
    try:
        timing_systems = _dasha_clock_facts(pc, _today)
        for clock in timing_systems:
            dirs=[]
            for cf in card_facts:
                if int(getattr(cf, "house", 0) or 0) not in list(clock.activated_houses or []):
                    continue
                d=str(getattr(cf, "direction", "") or "mixed").lower()
                dirs.append(d)
            support=sum(1 for d in dirs if d in ("support","up")); caution=sum(1 for d in dirs if d in ("caution","down"))
            if support and caution: clock.judgement="mixed"
            elif support > caution: clock.judgement="good"
            elif caution > support: clock.judgement="challenging"
            elif dirs: clock.judgement="moderate"
    except Exception as exc:
        print(f"[llm.facts] timing clocks unavailable: {exc}", flush=True)
    try:
        crossover_points = _crossover_points(timing_systems, _today)
        slow_transits = [x for x in (_transit_fact(pc, "Jupiter", _today), _transit_fact(pc, "Saturn", _today)) if x]
    except Exception as exc:
        print(f"[llm.facts] transit/crossover layer unavailable: {exc}", flush=True)
    try:
        jaimini_fact = _jaimini_fact(pc, _today)
    except Exception as exc:
        print(f"[llm.facts] Jaimini layer unavailable: {exc}", flush=True)
    try:
        dasha_planet_transits = _dasha_planet_transits(pc, timing_systems, _today)
    except Exception as exc:
        print(f"[llm.facts] dasha-planet transit layer unavailable: {exc}", flush=True)
    try:
        _validate_authoritative_dasha_context(vedic, timing_systems)
    except Exception as exc:
        # Do not emit a report with contradictory current dasha facts. The
        # date-aware timing engine is authoritative; a mismatch is a build
        # error, not something Qwen should reconcile.
        raise
    try:
        life_area_judgements = _life_area_judgements(pc, card_facts, timing_systems, slow_transits, _today)
    except Exception as exc:
        print(f"[llm.facts] life-area confluence layer unavailable: {exc}", flush=True)
    lords = [x for x in (vedic.period_lord, vedic.sub_period_lord) if x]
    for cf in card_facts:
        planets = list(cf.allowed_planets or [])
        for lord in lords:
            if lord not in planets:
                planets.append(lord)
        cf.allowed_planets = planets[:8]

    facts = ReportFacts(
        first_name=_first_name(name),
        age_band=age_band,
        age_years=age_years,
        gender=gender,
        access="paid" if access == "paid" else "free",  # type: ignore[arg-type]
        cards=card_facts,
        dashboard_buckets=buckets,
        timing_windows=timing_windows,
        personality_traits=personality_traits,
        phase_direction=_dir(phase_direction),  # type: ignore[arg-type]
        phase_tone=phase_tone,
        phase_end=phase_end,
        phase_notes=phase_notes,
        recent_months=recent_months,
        hardest_areas=hardest_areas[:4],
        hardest_area_labels=hardest_labels[:4],
        life_state=life_state,
        family_notes=list(family_notes or []),
        timing_systems=timing_systems,
        crossover_points=crossover_points,
        slow_transits=slow_transits,
        jaimini=jaimini_fact,
        dasha_planet_transits=dasha_planet_transits,
        life_area_judgements=life_area_judgements,
        vedic_context=vedic,
    )
    return project_for_access(seal_facts(facts, report_id=report_id), access)


def _vedic_context(pc: dict, today: Optional[date] = None) -> VedicContext:
    """Running Vimshottari context from the same date-aware clock used everywhere.

    ``current_md`` / ``current_md_antardashas`` are legacy snapshots and may be
    stale. The customer report, analytical block and Qwen prompt must therefore
    all consume the exact MD/AD resolved for ``today`` by ``vimshottari_at``.
    """
    today = today or date.today()
    vim = pc.get("vimshottari") or {} if isinstance(pc, dict) else {}
    if not isinstance(vim, dict):
        vim = {}
    md: dict = {}
    ad: dict = {}
    try:
        from report_confluence import vimshottari_at, antardashas_for
        state = vimshottari_at(pc, today) or {}
        md_lord = str(state.get("md") or "").strip()
        ad_lord = str(state.get("ad") or "").strip()
        seq = [x for x in (vim.get("sequence") or []) if isinstance(x, dict)]
        for row in seq:
            a, b = _as_date(row.get("start")), _as_date(row.get("end"))
            lord = str(row.get("md_lord") or row.get("lord") or "")
            if md_lord and lord == md_lord and a and b and a <= today <= b:
                md = row
                break
        if md and md_lord:
            start = _as_date(md.get("start"))
            end = _as_date(md.get("end"))
            try:
                years = float(md.get("md_years") or ((end-start).days/365.2425 if start and end else 0.0))
                ads = antardashas_for(md_lord, start, years) if start and years else []
            except Exception:
                ads = []
            for row in ads:
                a, b = _as_date(row.get("start")), _as_date(row.get("end"))
                lord = str(row.get("ad_lord") or row.get("lord") or "")
                if ad_lord and lord == ad_lord and a and b and a <= today <= b:
                    ad = row
                    break
    except Exception:
        md = ad = {}

    # Only if the date-aware engine truly cannot resolve the clock do we use the
    # legacy snapshot as a compatibility fallback.
    if not md:
        raw = vim.get("current_md") or {}
        md = raw if isinstance(raw, dict) else {}
    if not ad:
        rows = vim.get("current_md_antardashas") or []
        if isinstance(rows, list):
            ad = next((x for x in rows if isinstance(x, dict) and str(x.get("status") or "") == "current"), {})
            if not ad and rows:
                # Compatibility fallback only when the date-aware engine did
                # not expose a usable dated AD row. Never manufacture an AD
                # from the MD lord itself.
                ad = rows[0] if isinstance(rows[0], dict) else {}
    lagna = pc.get("lagna") or {} if isinstance(pc, dict) else {}
    rising = ""
    if isinstance(lagna, dict):
        rising = str(lagna.get("sign") or "").strip()
    moon = (pc.get("planets") or {}).get("Moon") if isinstance(pc, dict) else None
    moon_sign = ""
    nakshatra = ""
    if isinstance(moon, dict):
        moon_sign = str(moon.get("sign") or "").strip()
        nakshatra = str(
            moon.get("nakshatra") or moon.get("nak") or moon.get("naksatra") or ""
        ).strip()
    lord = str(md.get("md_lord") or md.get("lord") or md.get("name") or "").strip()[:20]
    sub = str(ad.get("ad_lord") or ad.get("lord") or ad.get("name") or "").strip()[:20]
    return VedicContext(
        period_lord=lord,
        sub_period_lord=sub,
        mahadasha=lord,
        antardasha=sub,
        lagna=rising[:20],
        nakshatra=nakshatra[:40],
        start=_pretty_date(ad.get("start") or md.get("start")),
        end=_pretty_date(ad.get("end") or md.get("end")),
        rising_sign=rising[:20],
        moon_sign=moon_sign[:20],
    )


def _personality_traits(pc: dict) -> list[str]:
    """Trait sentences from confluence.personality — drop planet-name lines."""
    traits: list[str] = []
    try:
        import report_confluence as CF
        pers = CF.personality(pc) or {}
        for t in list(pers.get("traits") or [])[:6]:
            text = str(t or "").strip()
            if not text:
                continue
            # Planet-name lines are blocked by QA; keep only human trait lines.
            if _PLANET_TOKEN.search(text):
                continue
            if re.search(r"\b(?:main astrological influence|carries that in your chart)\b", text, re.I):
                continue
            traits.append(text[:180])
    except Exception:  # noqa: BLE001
        traits = []
    return traits[:6]


def _phase_facts(pc: dict, today: date) -> tuple[str, str, str, list[str]]:
    """Current-phase direction, plain tone, end date, and short notes."""
    direction = "mixed"
    tone = "mixed"
    phase_end = ""
    notes: list[str] = []
    try:
        import present_read as PR
        block = PR.build(pc, today=today) or {}
        direction = str(block.get("direction") or "mixed")
        for pred in list(block.get("predictions") or [])[:4]:
            scenario = str(getattr(pred, "scenario", "") or "").strip()
            if not scenario:
                continue
            if _CLASSICAL_RAW.search(scenario):
                continue
            notes.append(scenario[:160])
    except Exception:  # noqa: BLE001
        pass
    tone = {
        "up": "supportive", "support": "supportive",
        "down": "demanding", "caution": "demanding",
    }.get(direction, "mixed")
    try:
        from report_cards import current_ad
        ad = current_ad(pc) or {}
        phase_end = _pretty_date(ad.get("end"))
    except Exception:  # noqa: BLE001
        phase_end = ""
    return direction, tone, phase_end, notes[:4]


def _recent_month_facts(pc: dict, today: date) -> list[RecentMonthFact]:
    """Last ~4 months of checkable past windows for the free trust section."""
    out: list[RecentMonthFact] = []
    try:
        import past_validation as PVH
        hist = PVH.build(pc, today=today, months=4, max_events=4) or {}
        for ev in list(hist.get("events") or [])[:4]:
            if not isinstance(ev, dict):
                continue
            headline = str(ev.get("headline") or ev.get("why") or "").strip()
            if _PLANET_TOKEN.search(headline) or _CLASSICAL_RAW.search(headline):
                headline = str(ev.get("direction_label") or "A mixed period")[:160]
            manifests = [
                str(m)[:120] for m in list(ev.get("manifests") or [])[:3]
                if str(m).strip() and not _PLANET_TOKEN.search(str(m))
            ]
            out.append(RecentMonthFact(
                start=_pretty_date(ev.get("start")),
                end=_pretty_date(ev.get("end")),
                area=str(ev.get("area") or "")[:40],
                label=str(ev.get("label") or ev.get("area") or "")[:80],
                direction=str(ev.get("direction") or "mixed")[:20],
                direction_label=str(ev.get("direction_label") or "")[:40],
                headline=headline[:220],
                manifests=manifests,
            ))
    except Exception:  # noqa: BLE001
        out = []
    return out


# ---------------------------------------------------------------------------
# User question
# ---------------------------------------------------------------------------
def build_question_facts(
    result: dict,
    *,
    name: str = "",
    access: str = "free",
    report_id: str = "",
) -> QuestionFacts:
    """Project one user question from the canonical full-report result.

    ``result['canonical_result']`` is authoritative whenever the requested
    topic maps to one of the full-report life areas. The question engine may
    still supply question-specific routing/context, but it must not replace
    the canonical promise, activation, direction or validated timing.
    """
    topic = result.get("topic")
    question = ""
    if topic is not None:
        question = str(getattr(topic, "raw", None) or getattr(topic, "text", "") or "")
    if not question:
        question = str(result.get("question") or "")[:280]

    promise = result.get("promise") or {}
    if not isinstance(promise, dict):
        promise = {}

    canonical = result.get("canonical_result") or {}
    if not isinstance(canonical, dict):
        canonical = {}

    if canonical:
        promise = canonical.get("promise") or promise
        direction = canonical.get("direction") or promise.get("direction") or "mixed"
        confidence = canonical.get("confidence") or promise.get("confidence") or "low"
        activation_status = str(
            (canonical.get("activation") or {}).get("status") or ""
        )
        truth_source = "full_report_canonical"
        canonical_area_key = str(canonical.get("area") or result.get("area_key") or "")
    else:
        direction = promise.get("direction") or "mixed"
        confidence = promise.get("confidence") or "low"
        activation_status = str(
            (result.get("activation") or {}).get("status")
            if isinstance(result.get("activation"), dict) else ""
        )
        truth_source = "question_specific_fallback"
        canonical_area_key = ""

    def _win(w: Any) -> Optional[WindowFact]:
        if not w or not isinstance(w, dict):
            return None
        return WindowFact(
            start=_pretty_date(w.get("start")),
            end=_pretty_date(w.get("end")),
            label=str(w.get("period") or w.get("planet") or w.get("label") or "")[:120],
            event_type=str(w.get("event_type") or "")[:80],
            confidence=_conf(w.get("confidence") or "moderate"),  # type: ignore[arg-type]
            source=str(w.get("source") or "validated_confluence")[:80],
            score=float(w.get("score") or 0.0),
        )

    # Prefer the canonical timing windows. The legacy question windows are only
    # used when the topic has no corresponding full-report life area.
    canonical_timing = []
    if canonical:
        # `answer()` has already filtered canonical timing to the user's
        # requested horizon. Reuse that filtered set; never resurrect the
        # full-report best window outside the question's timeframe.
        source_rows = list(result.get("windows") or [])[:6]
        for w in source_rows:
            wf = _win(w)
            if wf:
                canonical_timing.append(wf)

    raw_windows = canonical_timing if canonical else []
    if not raw_windows:
        raw_windows = []
        for w in (result.get("windows") or [])[:6]:
            wf = _win(w)
            if wf:
                raw_windows.append(wf)

    windows = raw_windows[:6]
    best = _win(result.get("best")) if canonical else None
    nearest = _win(result.get("nearest")) if canonical else None

    if canonical and best is None and windows:
        best = windows[0]
    if canonical and best is not None and nearest is None:
        earlier = [w for w in windows if w.start and best.start and w.start < best.start]
        nearest = earlier[-1] if earlier else None

    route = result.get("route") or {}
    if not isinstance(route, dict):
        route = {}
    route_clean = {
        k: route[k] for k in ("domain", "primary_house", "topic")
        if k in route
    }

    canonical_evidence: list[EvidenceFact] = []
    canonical_manifests: list[str] = []
    if canonical:
        why = canonical.get("why") or {}
        for row in list(why.get("rows") or [])[:8]:
            if not isinstance(row, dict):
                continue
            pol = str(row.get("direction") or "neutral").lower()
            polarity = "support" if pol in ("support", "up") else "caution"
            reasons = row.get("reasons") or []
            reason = str(row.get("reason") or (reasons[0] if reasons else "")).strip()
            text, tags = _normalize_evidence_text(reason)
            if text or tags:
                fam_raw = str(row.get("family") or "").lower()
                fam_map = {
                    "birth_chart": "natal",
                    "natal": "natal",
                    "natal_structure": "natal",
                    "divisional_confirmation": "divisional",
                    "divisional": "divisional",
                    "challenge_confirmation": "divisional",
                    "traditional_cross_check": "rules",
                    "classical": "rules",
                    "rules": "rules",
                    "palm": "palm",
                    "horary": "horary",
                }
                family = fam_map.get(fam_raw, "other")
                canonical_evidence.append(EvidenceFact(
                    family=family,  # type: ignore[arg-type]
                    polarity=polarity,
                    text=text,
                    semantic_tags=tags,
                    text_id=_eid("question-canonical", polarity, reason or str(row)),
                ))
        canonical_evidence = _dedupe_evidence(canonical_evidence)[:8]
        try:
            from interpretation.stage_config import manifestation_metadata
            canonical_manifests = []
            for x in (canonical.get("manifestation") or [])[:6]:
                meta = manifestation_metadata(str(x)) or {}
                modern = str(meta.get("modern_meaning") or "").strip()
                if modern:
                    canonical_manifests.append(modern[:120])
        except Exception:  # noqa: BLE001
            canonical_manifests = []

    allowed_dates = _dates_from_windows(best, nearest, *windows)
    facts = QuestionFacts(
        first_name=_first_name(name),
        access="paid" if access == "paid" else "free",  # type: ignore[arg-type]
        question=question[:280],
        area_key=str(result.get("area_key") or canonical_area_key),
        direction=_dir(direction),  # type: ignore[arg-type]
        confidence=_conf(confidence),  # type: ignore[arg-type]
        n_methods=int(result.get("n_methods") or 0),
        n_up=int(result.get("n_up") or 0),
        n_down=int(result.get("n_down") or 0),
        route=route_clean,
        best=best,
        nearest=nearest,
        windows=windows,
        promise_status=str(promise.get("status") or ""),
        activation_status=activation_status,
        support_n=int(result.get("n_up") or 0),
        caution_n=int(result.get("n_down") or 0),
        allowed_dates=allowed_dates,
        truth_source=truth_source,  # type: ignore[arg-type]
        canonical_area_key=canonical_area_key,
        canonical_promise_status=str(promise.get("status") or ""),
        canonical_activation_status=activation_status,
        canonical_direction=_dir(direction),  # type: ignore[arg-type]
        canonical_confidence=_conf(confidence),  # type: ignore[arg-type]
        canonical_agreement=_agreement(
            canonical.get("agreement") if canonical else promise.get("agreement")
        ),  # type: ignore[arg-type]
        canonical_evidence=canonical_evidence,
        canonical_manifestations=canonical_manifests,
        canonical_timing=canonical_timing,
        timing_can_create_promise=False,
        manifestation_ids=canonical_manifests[:6],
    )
    return project_for_access(seal_facts(facts, report_id=report_id), access)


# ---------------------------------------------------------------------------
# Horary
# ---------------------------------------------------------------------------
def build_horary_facts(
    *,
    question: str,
    verdicts: dict,
    summary: Optional[dict] = None,
    name: str = "",
    access: str = "free",
    report_id: str = "",
) -> HoraryFacts:
    summary = summary or {}
    lanes: list[HoraryLaneFact] = []
    for lane in ("vedic", "western"):
        block = (verdicts or {}).get(lane) or {}
        if not isinstance(block, dict):
            continue
        systems = block.get("systems") or []
        if isinstance(systems, dict):
            systems = list(systems.keys())
        lanes.append(HoraryLaneFact(
            lane=lane,  # type: ignore[arg-type]
            verdict=str(block.get("verdict") or block.get("label") or "")[:40],
            confidence=_conf(block.get("confidence") or "low"),  # type: ignore[arg-type]
            score=float(block.get("score") or 0.0),
            systems=[str(s)[:40] for s in list(systems)[:8]],
        ))

    facts = HoraryFacts(
        first_name=_first_name(name),
        access="paid" if access == "paid" else "free",  # type: ignore[arg-type]
        question=(question or "")[:280],
        subject=str(summary.get("subject") or "")[:80],
        label=str(summary.get("label") or "")[:80],
        confidence=_conf(summary.get("confidence") or "low"),  # type: ignore[arg-type]
        score=float(summary.get("score") or 0.0),
        contradicted=bool(summary.get("contradicted")),
        favourable=bool(summary.get("favourable")),
        lanes=lanes,
    )
    return project_for_access(seal_facts(facts, report_id=report_id), access)


# ---------------------------------------------------------------------------
# Palm
# ---------------------------------------------------------------------------
_PALM_STRENGTH_SCORE = {"strong": 86, "moderate": 72, "tentative": 58, "weak": 52}
_PALM_TITLE = {
    "character": "Character & Temperament",
    "mind": "Mind & Intellect",
    "love": "Relationships & Emotions",
    "career": "Career & Direction",
    "wealth": "Money & Resources",
    "health": "Health & Vitality",
}


def build_palm_facts(
    raw: dict,
    *,
    name: str = "",
    access: str = "free",
    age_band: str = "adult",
    age_years: Optional[int] = None,
    report_id: str = "",
) -> PalmFacts:
    """Build PalmFacts from pipeline raw / reading_result — strip prose."""
    rr = raw.get("reading_result") or {}
    conf = raw.get("confluence") or {}
    dominant = str(conf.get("dominant_hand") or rr.get("dominant_hand") or "right")
    quality = (rr.get("measurement_quality") or {})
    photo_grade = str(quality.get("photo_grade") or "fair").lower()
    photo_confidence = str(quality.get("interpretation_confidence") or (
        "high" if photo_grade == "good" else "low" if photo_grade == "poor" else "moderate"
    )).lower()
    if photo_confidence not in {"high", "moderate", "low"}:
        photo_confidence = "moderate"
    special_marks_allowed = bool(quality.get("special_marks_allowed", photo_grade == "good"))
    future_timing_allowed = bool(quality.get("future_timing_allowed", photo_grade != "poor"))
    age_precision = str(quality.get("age_precision") or (
        "withheld" if photo_grade == "poor"
        else "wider_window" if photo_grade == "fair"
        else "window"
    ))
    person = rr.get("person") or {}
    if age_years is None:
        try:
            age_years = int(person.get("age")) if person.get("age") is not None else None
        except (TypeError, ValueError):
            age_years = None

    aspects: list[PalmAspectFacts] = []
    life_aspects = conf.get("life_aspects") or rr.get("present") or []
    personality_traits: list[str] = []
    for row in life_aspects:
        if not isinstance(row, dict):
            continue
        key = str(row.get("key") or row.get("aspect") or "")
        if not key:
            continue
        strength = str(row.get("strength") or "").lower()
        if photo_grade == "poor":
            strength = "tentative"
        elif photo_grade == "fair" and strength in ("strong", "very strong"):
            strength = "moderate"
        direction = (
            "support" if strength in ("strong", "reinforced") else
            "caution" if strength in ("weak", "challenged") else
            "mixed"
        )
        points = row.get("points") or []
        signal_ids = []
        point_ids = []
        tags: list[str] = []
        for p in points[:8]:
            if isinstance(p, dict):
                rid = str(p.get("rule_id") or p.get("signal_id") or "")
                if rid:
                    point_ids.append(rid[:60])
                    # Rule IDs are provenance only. Do NOT expose raw detector
                    # morphology/special-mark signal IDs to the LLM.
                    signal_ids.append(rid[:60])
                tag = str(p.get("semantic_tag") or p.get("tag") or "")
                if tag:
                    tags.append(tag[:60])

        # IMPORTANT: canonical_signals are detector-level inputs (e.g.
        # HAND_AIR, TRIDENT_ON_JUPITER). They are not semantic facts and must
        # never be appended to PalmFacts.signal_ids.
        raw_summary = str(
            row.get("semantic_summary")
            or row.get("what_it_means")
            or row.get("summary")
            or ""
        ).strip()

        # `life_aspects` summary is already customer-safe modern meaning.
        # Do not run it through the evidence sanitizer: that sanitizer is
        # intentionally lossy and was previously turning valid summaries into
        # empty strings + generic tags. The grouping preamble ("Together,
        # these signs point to…") is engine bookkeeping, not a reading.
        summary = clip_sentences(clean_palm_summary(raw_summary), 220)
        if summary and len(personality_traits) < 5 and key in (
            "character", "mind", "love", "career", "wealth",
        ):
            personality_traits.append(clip_sentences(summary, 180))
        recognize = [
            str(x)[:120] for x in list(row.get("recognize") or [])[:4]
            if str(x).strip()
        ]
        age_window: list[int] = []
        title = str(row.get("title") or _PALM_TITLE.get(key, key))[:80]
        aspects.append(PalmAspectFacts(
            aspect=key,
            title=title,
            direction=direction,  # type: ignore[arg-type]
            strength=strength or "tentative",
            confidence=_conf(row.get("confidence") or "moderate"),  # type: ignore[arg-type]
            signal_ids=signal_ids[:12],
            point_ids=point_ids[:8],
            semantic_tags=tags[:6],
            semantic_summary=summary,
            recognize=recognize,
            age_window=age_window,
            score=float(row.get("score") or row.get("reinforced_count") or 0.0),
        ))

    future = []
    if future_timing_allowed:
        for fw in (rr.get("future_windows") or [])[:6]:
            if not isinstance(fw, dict):
                continue
            future.append({
                "age_window": fw.get("age_window"),
                "domain": str(fw.get("domain") or "")[:40],
                "confidence": str(fw.get("confidence") or "moderate"),
            })
        # Attach nearest future age window to matching aspects by domain.
        domain_to_aspect = {
            "vitality": "health", "mind_decision": "mind",
            "relationships": "love", "career_direction": "career",
        }
        by_key = {a.aspect: a for a in aspects}
        for fw in future:
            asp = by_key.get(domain_to_aspect.get(str(fw.get("domain") or ""), ""))
            if asp is None or asp.age_window:
                continue
            aw = fw.get("age_window") or []
            if isinstance(aw, (list, tuple)) and len(aw) >= 2:
                try:
                    asp.age_window = [int(aw[0]), int(aw[1])]
                except (TypeError, ValueError):
                    pass

    mark_ids = []
    if special_marks_allowed:
        for m in (rr.get("special_marks") or [])[:8]:
            if isinstance(m, dict):
                mid = str(m.get("id") or m.get("kind") or m.get("name") or "")
                if mid:
                    mark_ids.append(mid[:60])
            elif isinstance(m, str) and m.strip():
                mark_ids.append(m.strip()[:60])

    # A blocked photo-quality feature must be removed from every semantic
    # aspect, not only from the top-level special_mark_ids. Keep detector
    # output internal, but never expose special-mark provenance to the LLM.
    if not special_marks_allowed:
        blocked_tokens = ("trident", "star", "grille", "fish", "triangle", "yav", "special_mark", "mark_")
        for aspect in aspects:
            aspect.signal_ids = [sid for sid in aspect.signal_ids
                                 if not any(tok in sid.lower() for tok in blocked_tokens)]
            aspect.point_ids = [pid for pid in aspect.point_ids
                                if not any(tok in pid.lower() for tok in blocked_tokens)]

    # Life stage at current age + demanding aspect (lowest strength).
    life_stage_note, life_stage_age = _palm_life_stage(raw, dominant, age_years)
    demanding_aspect = ""
    demanding_label = ""
    if aspects:
        weakest = min(
            aspects,
            key=lambda a: (
                _PALM_STRENGTH_SCORE.get(str(a.strength).lower(), 70),
                -float(a.score or 0),
            ),
        )
        demanding_aspect = weakest.aspect
        demanding_label = weakest.title or _PALM_TITLE.get(weakest.aspect, weakest.aspect)

    remedies_allowed = photo_grade == "good"
    remedies: list[str] = []
    if remedies_allowed:
        try:
            from palm_api.palm_remedies import build_palm_remedies, format_remedy_line
            dom = raw.get(dominant) or raw.get("right") or raw.get("left") or {}
            feats = (dom.get("features") or {})
            for r in (build_palm_remedies(feats) or [])[:4]:
                line = format_remedy_line(r) if not isinstance(r, str) else str(r)
                line = str(line or "").strip()
                if line and not _PLANET_TOKEN.search(line):
                    remedies.append(line[:160])
        except Exception:  # noqa: BLE001
            remedies = []

    # The two-hand contrast and the current-state block are both derived from
    # material the palm engine already produced, so they cannot disagree with
    # the life-area cards on the same page.
    from .palm_state import build_hand_contrast, build_palm_state
    hand_contrast = build_hand_contrast(conf, dominant_hand=dominant)
    palm_state = build_palm_state(
        aspects,
        contrast=hand_contrast,
        demanding_aspect=demanding_aspect,
        photo_grade=photo_grade,
    )

    facts = PalmFacts(
        first_name=_first_name(name),
        age_band=age_band or "adult",
        age_years=age_years,
        access="paid" if access == "paid" else "free",  # type: ignore[arg-type]
        dominant_hand=dominant,
        photo_grade=photo_grade,
        photo_confidence=photo_confidence,  # type: ignore[arg-type]
        special_marks_allowed=special_marks_allowed,
        future_timing_allowed=future_timing_allowed,
        age_precision=age_precision,
        quality_note=str(quality.get("quality_note") or "")[:180],
        aspects=aspects,
        future_windows=future,
        special_mark_ids=mark_ids,
        personality_traits=personality_traits[:6],
        life_stage_note=life_stage_note,
        life_stage_age=life_stage_age,
        demanding_aspect=demanding_aspect,
        demanding_aspect_label=demanding_label,
        remedies_allowed=remedies_allowed,
        remedies=remedies[:4],
        hand_contrast=hand_contrast,
        palm_state=palm_state,
    )
    return project_for_access(seal_facts(facts, report_id=report_id), access)


def _palm_life_stage(
    raw: dict, dominant: str, age_years: Optional[int],
) -> tuple[str, Optional[int]]:
    """Nearest dated line marking at the person's current age."""
    if age_years is None:
        return "", None
    dom = raw.get(dominant) or raw.get("right") or raw.get("left") or {}
    items = dom.get("numbered_checklist") or []
    best = None
    best_dist = 10**9
    for it in items:
        if not isinstance(it, dict) or it.get("kind") != "line":
            continue
        timing = it.get("timing") or {}
        age = timing.get("estimated_age")
        if not isinstance(age, int):
            continue
        dist = abs(age - age_years)
        if dist < best_dist:
            best_dist = dist
            best = it
    if best is None:
        return "", None
    timing = best.get("timing") or {}
    age = timing.get("estimated_age")
    conclusive = best.get("conclusive") or {}
    text = str(
        conclusive.get("conclusion")
        or conclusive.get("verdict")
        or best.get("title")
        or ""
    ).strip()
    if _PLANET_TOKEN.search(text) or _CLASSICAL_RAW.search(text):
        title = str(best.get("title") or "your hand").lower()
        text = f"Around age {age}, {title} enters a meaningful chapter."
    elif age is not None and "age" not in text.lower():
        text = f"Around age {age}, {text}"
    return text[:220], int(age) if isinstance(age, int) else None
