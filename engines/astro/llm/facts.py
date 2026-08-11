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

from .schemas import (
    SCHEMA_VERSION,
    CardFacts,
    EvidenceFact,
    HoraryFacts,
    HoraryLaneFact,
    PalmAspectFacts,
    PalmFacts,
    QuestionFacts,
    ReportFacts,
    WindowFact,
)

ENGINE_VERSION = "astro-2026.08.11"

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
    r"case-book|classical rule|technical reason)\b",
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
    """Strip raw classical/case-book wording; prefer short semantic tags."""
    t = (text or "").strip()
    if not t:
        return "", []
    if _CLASSICAL_RAW.search(t) or len(t) > 160:
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
    """Return only customer-semantic facts for the LLM/QA boundary.

    Versioning/report hashes are internal metadata and must never be used as
    grounding tokens. Keeping them in the payload previously allowed the model
    and validators to see engine years such as 2026 as if they were chart facts.
    """
    if hasattr(facts, "model_dump"):
        data = facts.model_dump(mode="json")
    else:
        data = facts
    if not isinstance(data, dict):
        return data
    data = dict(data)
    hidden = {
        "schema_version", "engine_version", "report_id", "facts_hash",
        "prompt_version", "model_name", "signal_ids", "point_ids",
        "text_id", "score", "house", "method_id", "allowed_planets",
    }
    def clean(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                k: clean(v) for k, v in obj.items()
                if k not in hidden
                and k not in ("method", "systems")  # technical method labels
            }
        if isinstance(obj, list):
            return [clean(v) for v in obj]
        return obj
    return clean(data)


def public_fact_payload(facts: Any) -> Any:
    """Public API used by prompts and validators."""
    return _public_fact_payload(facts)


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
        # Palm: drop future age windows on free
        if data.get("future_windows"):
            data["future_windows"] = []

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
    age_band = "adult"
    try:
        from interpretation.life_stage import age_band as _ab
        age_band = _ab(pc, today=today) or "adult"
    except Exception:  # noqa: BLE001
        pass

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
                elif re.fullmatch(r"[a-z0-9_\-]{3,80}", str(m).strip(), re.I):
                    safe_manifests.append(str(m).replace("_", " ")[:120])
        except Exception:  # noqa: BLE001
            safe_manifests = [
                str(m)[:120] for m in manifests
                if re.fullmatch(r"[a-z0-9_\-]{3,80}", str(m).strip(), re.I)
            ]
        manifests = safe_manifests[:6]
        semantic_tags = list(cr.get("semantic_tags") or [])[:8]
        if kind == "challenge" and not semantic_tags:
            semantic_tags = ["wellbeing_sensitivity", "routine", "recovery"]

        window = None
        w = getattr(c, "window", "") or ""
        if w:
            window = WindowFact(label=str(w)[:120])

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

        allowed_dates = _dates_from_windows(window)
        blob = " ".join(
            [str(t) for t in support_ev + caution_ev]
            + [str(x) for x in manifests]
        )
        allowed_planets = _planets_from_text(blob)

        card_facts.append(CardFacts(
            area=area,
            label=str(getattr(c, "label", "") or area),
            kind=kind,  # type: ignore[arg-type]
            status=status,
            activation_status=act_status,
            confidence=conf,  # type: ignore[arg-type]
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
            wealth_sub=wealth_sub,
            allowed_planets=allowed_planets,
            allowed_dates=allowed_dates,
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
    except Exception:  # noqa: BLE001
        buckets = {}

    facts = ReportFacts(
        first_name=_first_name(name),
        age_band=age_band,
        access="paid" if access == "paid" else "free",  # type: ignore[arg-type]
        cards=card_facts,
        dashboard_buckets=buckets,
        timing_windows=timing_windows,
    )
    return project_for_access(seal_facts(facts, report_id=report_id), access)


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
    topic = result.get("topic")
    question = ""
    if topic is not None:
        question = str(getattr(topic, "raw", None) or getattr(topic, "text", "") or "")
    if not question:
        question = str(result.get("question") or "")[:280]

    promise = result.get("promise") or {}
    if not isinstance(promise, dict):
        promise = {}

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

    windows = []
    for w in (result.get("windows") or [])[:6]:
        wf = _win(w)
        if wf:
            windows.append(wf)

    route = result.get("route") or {}
    if not isinstance(route, dict):
        route = {}
    route_clean = {
        k: route[k] for k in ("domain", "primary_house", "topic", "method")
        if k in route
    }

    best = _win(result.get("best"))
    nearest = _win(result.get("nearest"))
    allowed_dates = _dates_from_windows(best, nearest, *windows)

    facts = QuestionFacts(
        first_name=_first_name(name),
        access="paid" if access == "paid" else "free",  # type: ignore[arg-type]
        question=question[:280],
        area_key=str(result.get("area_key") or ""),
        direction=_dir(promise.get("direction") or "mixed"),  # type: ignore[arg-type]
        confidence=_conf(promise.get("confidence") or "low"),  # type: ignore[arg-type]
        n_methods=int(result.get("n_methods") or 0),
        n_up=int(result.get("n_up") or 0),
        n_down=int(result.get("n_down") or 0),
        route=route_clean,
        best=best,
        nearest=nearest,
        windows=windows,
        promise_status=str(promise.get("status") or ""),
        activation_status=str(
            (result.get("activation") or {}).get("status")
            if isinstance(result.get("activation"), dict) else ""
        ),
        support_n=int(result.get("n_up") or 0),
        caution_n=int(result.get("n_down") or 0),
        allowed_dates=allowed_dates,
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
def build_palm_facts(
    raw: dict,
    *,
    name: str = "",
    access: str = "free",
    age_band: str = "adult",
    report_id: str = "",
) -> PalmFacts:
    """Build PalmFacts from pipeline raw / reading_result — strip prose."""
    rr = raw.get("reading_result") or {}
    conf = raw.get("confluence") or {}
    dominant = str(conf.get("dominant_hand") or rr.get("dominant_hand") or "right")
    quality = (rr.get("measurement_quality") or {})
    photo_grade = str(quality.get("photo_grade") or "fair")

    aspects: list[PalmAspectFacts] = []
    life_aspects = conf.get("life_aspects") or rr.get("present") or []
    for row in life_aspects:
        if not isinstance(row, dict):
            continue
        key = str(row.get("key") or row.get("aspect") or "")
        if not key:
            continue
        strength = str(row.get("strength") or "").lower()
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
                    signal_ids.append(rid[:60])
                tag = str(p.get("semantic_tag") or p.get("tag") or "")
                if tag:
                    tags.append(tag[:60])
        for s in (rr.get("canonical_signals") or [])[:20]:
            if isinstance(s, dict) and s.get("signal_id"):
                sid = str(s["signal_id"])[:60]
                if sid not in signal_ids:
                    signal_ids.append(sid)
        raw_summary = str(row.get("summary") or row.get("what_it_means") or "").strip()
        summary, summary_tags = _normalize_evidence_text(raw_summary)
        aspects.append(PalmAspectFacts(
            aspect=key,
            direction=direction,  # type: ignore[arg-type]
            confidence=_conf(row.get("confidence") or "moderate"),  # type: ignore[arg-type]
            signal_ids=signal_ids[:12],
            point_ids=point_ids[:8],
            semantic_tags=(tags + summary_tags)[:6],
            semantic_summary=summary[:220],
            score=float(row.get("score") or row.get("reinforced_count") or 0.0),
        ))

    future = []
    for fw in (rr.get("future_windows") or [])[:6]:
        if not isinstance(fw, dict):
            continue
        future.append({
            "age_window": fw.get("age_window"),
            "domain": str(fw.get("domain") or "")[:40],
            "confidence": str(fw.get("confidence") or "moderate"),
        })

    mark_ids = []
    for m in (rr.get("special_marks") or [])[:8]:
        if isinstance(m, dict):
            mid = str(m.get("id") or m.get("kind") or m.get("name") or "")
            if mid:
                mark_ids.append(mid[:60])
        elif isinstance(m, str) and m.strip():
            mark_ids.append(m.strip()[:60])

    facts = PalmFacts(
        first_name=_first_name(name),
        age_band=age_band or "adult",
        access="paid" if access == "paid" else "free",  # type: ignore[arg-type]
        dominant_hand=dominant,
        photo_grade=photo_grade,
        aspects=aspects,
        future_windows=future,
        special_mark_ids=mark_ids,
    )
    return project_for_access(seal_facts(facts, report_id=report_id), access)
