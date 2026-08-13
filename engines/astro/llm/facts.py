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
    EvidenceFact,
    HoraryFacts,
    HoraryLaneFact,
    PalmAspectFacts,
    PalmFacts,
    QuestionFacts,
    RecentMonthFact,
    ReportFacts,
    WindowFact,
)

ENGINE_VERSION = "astro-2026.08.11-qcanonical-v2"

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
        # phase they are in before they decide to unlock. Family notes are the
        # depth behind the paid parents/siblings areas, so they stay paid.
        if "family_notes" in data:
            data["family_notes"] = []
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
            if _PLANET_TOKEN.search(text) or _CLASSICAL_RAW.search(text):
                continue
            remedy_text = text[:220]
            break
        if not remedy_text and approved:
            remedy_text = approved[0][:220]

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
    )
    return project_for_access(seal_facts(facts, report_id=report_id), access)


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
            # Strip planet / Sanskrit tokens before they reach the LLM.
            if _PLANET_TOKEN.search(scenario) or _CLASSICAL_RAW.search(scenario):
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
