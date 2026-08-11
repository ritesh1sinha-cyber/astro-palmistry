"""Orchestrator: facts → LLM prose → QA → retry → deterministic fallback.

Python owns prediction truth. Qwen owns expression only. Any failure leaves
prediction facts unchanged and falls back to deterministic prose when the
LLM tab is enabled.
"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Optional

from . import fallback as FB
from .facts import facts_cache_key, project_for_access
from .rules import OUT_OF_SCOPE_REFUSAL, prompt_version, system_prompt_for, user_prompt
from .schemas import (
    SCHEMA_VERSION,
    CardProse,
    ChatAnswer,
    HoraryFacts,
    HoraryProse,
    LlmRunMeta,
    PalmAspectProse,
    PalmFacts,
    PalmProse,
    QuestionFacts,
    QuestionProse,
    ReportFacts,
    ReportProse,
)
from .validate import (
    validate_card_prose,
    validate_chat_answer,
    validate_horary_prose,
    validate_palm_prose,
    validate_question_prose,
    validate_slot,
)

MAX_LLM_RETRIES = 2  # Attempt 1 + 1 retry; then deterministic fallback

_redis = None
_redis_lock = threading.Lock()
_redis_checked = False


def _settings():
    try:
        from core.config import S
        return S
    except Exception:  # noqa: BLE001
        return None


def _redis_client():
    global _redis, _redis_checked
    if _redis_checked:
        return _redis
    with _redis_lock:
        if _redis_checked:
            return _redis
        _redis_checked = True
        S = _settings()
        if S is None or not getattr(S, "redis_url", ""):
            return None
        try:
            import redis
            _redis = redis.Redis.from_url(S.redis_url, decode_responses=True)
            _redis.ping()
        except Exception:  # noqa: BLE001
            _redis = None
        return _redis


def _model_name() -> str:
    S = _settings()
    return str(getattr(S, "llm_model", "") or "") if S else ""


def _cache_key(facts: Any, kind: str, access: str) -> str:
    fh = getattr(facts, "facts_hash", "") or facts_cache_key(facts)
    return f"{fh}:{prompt_version(kind)}:{_model_name()}:{kind}:{access}"


def _cache_get(key: str) -> Optional[dict]:
    r = _redis_client()
    if r is None:
        return None
    try:
        raw = r.get(f"llm:v2:{key}")
        if raw:
            return json.loads(raw)
    except Exception:  # noqa: BLE001
        pass
    return None


def _cache_set(key: str, value: dict) -> None:
    r = _redis_client()
    if r is None:
        return
    S = _settings()
    ttl = int(getattr(S, "llm_cache_ttl", 86400) or 86400)
    try:
        # Never cache internal run meta noise beyond stats
        payload = {
            "overlay": value.get("overlay") or {},
            "stats": value.get("stats") or {},
            "enabled": value.get("enabled"),
            "kind": value.get("kind"),
            "access": value.get("access"),
            "fallback_used": value.get("fallback_used", False),
        }
        r.setex(f"llm:v2:{key}", ttl, json.dumps(payload, ensure_ascii=False))
    except Exception:  # noqa: BLE001
        pass


def _complete(schema, system: str, user: str, *, temperature: float = 0.4):
    try:
        from core.llm_client import complete_model
    except Exception:  # noqa: BLE001
        return None
    return complete_model(schema, system, user, temperature=temperature)


def _enabled(kind: str) -> bool:
    S = _settings()
    if S is None:
        return False
    return bool(S.llm_tab_enabled(kind))


def _concurrency() -> int:
    S = _settings()
    return max(1, int(getattr(S, "llm_concurrency", 4) or 4))


def _complete_validated(
    schema,
    system: str,
    base_user: str,
    facts: Any,
    validate_fn: Callable[[Any, Any], list[str]],
    *,
    temperature: float = 0.4,
) -> tuple[Any, int, list[str]]:
    """Return (prose|None, retry_count, last_errors)."""
    last_errors: list[str] = []
    retries = 0
    for attempt in range(MAX_LLM_RETRIES):
        user = base_user
        if attempt and last_errors:
            retries = attempt
            user = (
                base_user
                + "\n\nPrevious output failed QA. Fix ONLY these issues and "
                + "do not invent facts:\n"
                + json.dumps(last_errors[:12], ensure_ascii=False)
            )
        prose = _complete(schema, system, user, temperature=temperature)
        if prose is None:
            last_errors = ["empty_or_model_failure"]
            continue
        fails = validate_fn(prose, facts) or []
        if not fails:
            return prose, retries, []
        last_errors = list(fails)
    return None, retries, last_errors


def _card_overlay_dict(prose: CardProse) -> dict[str, Any]:
    return {
        "headline": prose.headline,
        "summary": prose.summary,
        "why": prose.summary,
        "meaning": prose.summary,
        "how_this_may_show_up": list(prose.how_this_may_show_up or []),
        "manifestations": list(prose.how_this_may_show_up or []),
        "what_to_watch": list(prose.what_to_watch or []),
        "what_helps": list(prose.what_helps or []),
        "pressure": prose.pressure,
        "action": prose.action,
        "timing_summary": prose.timing_summary or "",
    }


# ---------------------------------------------------------------------------
# Per-tab humanizers
# ---------------------------------------------------------------------------
def _humanize_report(facts: ReportFacts) -> tuple[dict, dict, bool, int]:
    overlay: dict[str, Any] = {"cards": {}}
    stats = {"accepted": 0, "rejected": 0, "errors": 0}
    fallback_used = False
    retries_total = 0
    sys = system_prompt_for("full_report")

    def one_card(cf):
        mini = ReportFacts(
            first_name=facts.first_name,
            age_band=facts.age_band,
            access=facts.access,
            cards=[cf],
            dashboard_buckets={},
            timing_windows=[],
            schema_version=facts.schema_version,
            engine_version=facts.engine_version,
            report_id=facts.report_id,
            facts_hash=facts.facts_hash,
        )
        prose, retries, errs = _complete_validated(
            CardProse, sys,
            user_prompt(mini, schema_name="CardProse"),
            mini,
            lambda p, f: validate_card_prose(p, f),
        )
        return cf.area, prose, retries, errs, cf

    cards = list(facts.cards or [])
    results = []
    if cards:
        with ThreadPoolExecutor(max_workers=min(_concurrency(), len(cards))) as pool:
            futs = {pool.submit(one_card, cf): cf.area for cf in cards}
            for fut in as_completed(futs):
                try:
                    results.append(fut.result())
                except Exception as exc:  # noqa: BLE001
                    print(f"[llm] card future failed: {exc}", flush=True)
                    stats["errors"] += 1

    for area, prose, retries, errs, cf in results:
        retries_total = max(retries_total, retries)
        if prose is None:
            stats["rejected"] += 1
            overlay["cards"][area] = FB.card_fallback(cf)
            fallback_used = True
            if errs:
                print(f"[llm] card {area} fallback after: {errs[:4]}", flush=True)
            continue
        if getattr(prose, "area", "") != area:
            try:
                prose.area = area
            except Exception:  # noqa: BLE001
                overlay["cards"][area] = FB.card_fallback(cf)
                fallback_used = True
                stats["rejected"] += 1
                continue
        overlay["cards"][area] = _card_overlay_dict(prose)
        stats["accepted"] += 1

    # Opening
    if facts.cards:
        try:
            full, r, errs = _complete_validated(
                ReportProse, sys,
                user_prompt(facts, schema_name="ReportProse")
                + "\nFill opening only; cards may be empty.",
                facts,
                lambda p, f: validate_slot(getattr(p, "opening", "") or "", f),
            )
            retries_total = max(retries_total, r)
            if full and (full.opening or "").strip() and not errs:
                overlay["opening"] = full.opening.strip()
                stats["accepted"] += 1
            else:
                fb = FB.report_fallback(facts)
                overlay["opening"] = fb.get("opening") or ""
                fallback_used = True
                stats["rejected"] += 1
        except Exception:  # noqa: BLE001
            stats["errors"] += 1
            fb = FB.report_fallback(facts)
            overlay.setdefault("opening", fb.get("opening") or "")
            fallback_used = True

    if not overlay.get("opening"):
        overlay["opening"] = FB.report_fallback(facts).get("opening") or ""

    return overlay, stats, fallback_used, retries_total


def _humanize_question(facts: QuestionFacts) -> tuple[dict, dict, bool, int]:
    stats = {"accepted": 0, "rejected": 0, "errors": 0}
    prose, retries, errs = _complete_validated(
        QuestionProse,
        system_prompt_for("user_question"),
        user_prompt(facts, schema_name="QuestionProse"),
        facts,
        validate_question_prose,
    )
    if prose is None:
        stats["rejected"] += 1
        return FB.question_fallback(facts), stats, True, retries
    stats["accepted"] += 1
    return {
        "opening": prose.opening,
        "answer": prose.answer,
        "timing": prose.timing,
        "action": prose.action,
    }, stats, False, retries


def _humanize_horary(facts: HoraryFacts) -> tuple[dict, dict, bool, int]:
    stats = {"accepted": 0, "rejected": 0, "errors": 0}
    prose, retries, errs = _complete_validated(
        HoraryProse,
        system_prompt_for("horary"),
        user_prompt(facts, schema_name="HoraryProse"),
        facts,
        validate_horary_prose,
    )
    if prose is None:
        stats["rejected"] += 1
        return FB.horary_fallback(facts), stats, True, retries
    stats["accepted"] += 1
    return {
        "lead": prose.lead,
        "verdict_line": prose.verdict_line,
        "why": prose.why,
        "action": prose.action,
    }, stats, False, retries


def _humanize_palm(facts: PalmFacts) -> tuple[dict, dict, bool, int]:
    overlay: dict[str, Any] = {"aspects": {}}
    stats = {"accepted": 0, "rejected": 0, "errors": 0}
    fallback_used = False
    retries_total = 0
    sys = system_prompt_for("palm")

    def one(asp):
        mini = PalmFacts(
            first_name=facts.first_name,
            age_band=facts.age_band,
            access=facts.access,
            dominant_hand=facts.dominant_hand,
            photo_grade=facts.photo_grade,
            aspects=[asp],
            schema_version=facts.schema_version,
            engine_version=facts.engine_version,
            report_id=facts.report_id,
            facts_hash=facts.facts_hash,
        )
        prose, retries, errs = _complete_validated(
            PalmAspectProse, sys,
            user_prompt(mini, schema_name="PalmAspectProse"),
            mini,
            lambda p, f: validate_palm_prose(
                type("S", (), {"opening": "", "aspects": [p]})(), f
            ),
        )
        return asp.aspect, prose, retries, errs, asp

    aspects = list(facts.aspects or [])
    results = []
    if aspects:
        with ThreadPoolExecutor(max_workers=min(_concurrency(), len(aspects))) as pool:
            futs = [pool.submit(one, a) for a in aspects]
            for fut in as_completed(futs):
                try:
                    results.append(fut.result())
                except Exception:  # noqa: BLE001
                    stats["errors"] += 1

    for aspect, prose, retries, errs, asp in results:
        retries_total = max(retries_total, retries)
        if prose is None:
            stats["rejected"] += 1
            fb = FB.palm_fallback(
                type("F", (), {
                    "first_name": facts.first_name,
                    "aspects": [asp],
                })()
            )
            overlay["aspects"][aspect] = (fb.get("aspects") or {}).get(aspect) or {
                "headline": f"Your {aspect.replace('_', ' ')} pattern is noted.",
                "why": "Based on the measured palm signals for this life theme.",
                "points": [],
            }
            fallback_used = True
            continue
        overlay["aspects"][aspect] = {
            "headline": prose.headline,
            "why": prose.why,
            "points": list(prose.points or []),
        }
        stats["accepted"] += 1

    try:
        full, r, errs = _complete_validated(
            PalmProse, sys,
            user_prompt(facts, schema_name="PalmProse")
            + "\nFill opening; aspects may be empty.",
            facts,
            lambda p, f: validate_slot(getattr(p, "opening", "") or "", f),
        )
        retries_total = max(retries_total, r)
        if full and (full.opening or "").strip() and not errs:
            overlay["opening"] = full.opening.strip()
            stats["accepted"] += 1
        else:
            overlay["opening"] = FB.palm_fallback(facts).get("opening") or ""
            fallback_used = True
    except Exception:  # noqa: BLE001
        stats["errors"] += 1
        overlay["opening"] = FB.palm_fallback(facts).get("opening") or ""
        fallback_used = True

    return overlay, stats, fallback_used, retries_total


def humanize(kind: str, facts: Any, *, access: str = "free") -> dict:
    """Public entry. Returns overlay + stats + run meta (never for customer HTML).

    When LLM is disabled, overlay is empty so renderers keep template prose.
    When enabled and QA fails after retries, overlay uses deterministic fallback.
    """
    kind = (kind or "").strip()
    access_n = "paid" if access == "paid" else "free"
    meta = LlmRunMeta(
        enabled=False,
        model_name=_model_name(),
        prompt_version=prompt_version(kind),
        facts_hash=getattr(facts, "facts_hash", "") or "",
        schema_version=SCHEMA_VERSION,
    )
    out: dict[str, Any] = {
        "overlay": {},
        "stats": {"accepted": 0, "rejected": 0, "errors": 0},
        "enabled": False,
        "kind": kind,
        "access": access_n,
        "fallback_used": False,
        "run_meta": meta.model_dump(),
    }
    if not _enabled(kind):
        return out

    out["enabled"] = True
    meta.enabled = True

    # Ensure access projection matches the requested tier
    try:
        facts = project_for_access(facts, access_n)
    except Exception:  # noqa: BLE001
        pass
    if hasattr(facts, "access"):
        try:
            facts.access = access_n  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

    meta.facts_hash = getattr(facts, "facts_hash", "") or facts_cache_key(facts)
    cache_key = _cache_key(facts, kind, access_n)
    cached = _cache_get(cache_key)
    if cached and isinstance(cached, dict) and "overlay" in cached:
        cached = dict(cached)
        cached["run_meta"] = {
            **meta.model_dump(),
            "accepted": (cached.get("stats") or {}).get("accepted", 0),
            "rejected": (cached.get("stats") or {}).get("rejected", 0),
            "fallback_used": bool(cached.get("fallback_used")),
        }
        return cached

    fallback_used = False
    retries = 0
    try:
        if kind == "full_report" and isinstance(facts, ReportFacts):
            overlay, stats, fallback_used, retries = _humanize_report(facts)
        elif kind == "user_question" and isinstance(facts, QuestionFacts):
            overlay, stats, fallback_used, retries = _humanize_question(facts)
        elif kind == "horary" and isinstance(facts, HoraryFacts):
            overlay, stats, fallback_used, retries = _humanize_horary(facts)
        elif kind == "palm" and isinstance(facts, PalmFacts):
            overlay, stats, fallback_used, retries = _humanize_palm(facts)
        else:
            print(f"[llm] unknown kind/facts: {kind}/{type(facts)}", flush=True)
            return out
    except Exception as exc:  # noqa: BLE001
        print(f"[llm] humanize failed: {type(exc).__name__}: {exc}", flush=True)
        out["stats"]["errors"] += 1
        # Last-resort deterministic fallback so enabled path never blanks
        try:
            if kind == "full_report" and isinstance(facts, ReportFacts):
                overlay = FB.report_fallback(facts)
            elif kind == "user_question" and isinstance(facts, QuestionFacts):
                overlay = FB.question_fallback(facts)
            elif kind == "horary" and isinstance(facts, HoraryFacts):
                overlay = FB.horary_fallback(facts)
            elif kind == "palm" and isinstance(facts, PalmFacts):
                overlay = FB.palm_fallback(facts)
            else:
                overlay = {}
            out["overlay"] = overlay
            out["fallback_used"] = True
            meta.fallback_used = True
            meta.errors = 1
            out["run_meta"] = meta.model_dump()
        except Exception:  # noqa: BLE001
            pass
        return out

    meta.retry_count = retries
    meta.fallback_used = fallback_used
    meta.accepted = int(stats.get("accepted") or 0)
    meta.rejected = int(stats.get("rejected") or 0)
    meta.errors = int(stats.get("errors") or 0)

    out["overlay"] = overlay
    out["stats"] = stats
    out["fallback_used"] = fallback_used
    out["run_meta"] = meta.model_dump()
    if overlay:
        _cache_set(cache_key, out)
    # Log internal meta only — never render into HTML
    print(
        f"[llm] run kind={kind} access={access_n} "
        f"accepted={meta.accepted} rejected={meta.rejected} "
        f"retries={meta.retry_count} fallback={meta.fallback_used} "
        f"hash={meta.facts_hash}",
        flush=True,
    )
    return out


def humanize_chat(
    facts: Any,
    question: str,
    history: Optional[list] = None,
) -> dict:
    """Phase-2 follow-up. Returns ``{answer, out_of_scope, used_fact_ids, stats}``."""
    result = {
        "answer": OUT_OF_SCOPE_REFUSAL,
        "out_of_scope": True,
        "used_fact_ids": [],
        "stats": {"accepted": 0, "rejected": 0},
        "fallback_used": False,
    }
    S = _settings()
    if not _enabled("chat"):
        if S is None or not getattr(S, "llm_enabled", False):
            return result

    hist = history or []
    # Chat always uses paid-depth facts; never invent beyond them.
    try:
        facts = project_for_access(facts, "paid")
    except Exception:  # noqa: BLE001
        pass
    # Give the model a compact, explicit list of fact IDs it may cite. The
    # detailed internal IDs stay out of normal prose, but follow-up chat needs
    # traceability for the facts it used.
    available_fact_ids = {"promise", "activation", "direction", "confidence",
                          "timing", "manifestation", "action", "remedy", "why"}
    try:
        raw_facts = facts.model_dump(mode="json") if hasattr(facts, "model_dump") else facts
        def _ids(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in ("text_id", "signal_id", "point_id", "id") and v:
                        available_fact_ids.add(str(v))
                    _ids(v)
            elif isinstance(obj, list):
                for v in obj:
                    _ids(v)
        _ids(raw_facts)
    except Exception:
        pass
    payload = {
        "facts": facts.model_dump(mode="json") if hasattr(facts, "model_dump") else facts,
        "available_fact_ids": sorted(available_fact_ids)[:80],
        "question": (question or "")[:400],
        "history": hist[-6:],
    }
    prose, _retries, errs = _complete_validated(
        ChatAnswer,
        system_prompt_for("chat"),
        user_prompt(payload, schema_name="ChatAnswer"),
        facts,
        validate_chat_answer,
        temperature=0.3,
    )
    if prose is None:
        result["stats"]["rejected"] = 1
        result["fallback_used"] = True
        result["answer"] = (
            "I can only speak from the facts already in your reading. "
            "Please ask about a life area or timing window shown there."
        )
        return result
    if prose.out_of_scope:
        result["answer"] = OUT_OF_SCOPE_REFUSAL
        result["out_of_scope"] = True
        result["stats"]["accepted"] = 1
        return result
    result["answer"] = prose.answer
    result["out_of_scope"] = False
    result["used_fact_ids"] = list(prose.used_fact_ids or [])
    result["stats"]["accepted"] = 1
    return result
