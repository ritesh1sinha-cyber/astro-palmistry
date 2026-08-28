"""Orchestrator: facts → LLM prose → QA → retry → deterministic fallback.

Python owns prediction truth. Qwen owns expression only. Any failure leaves
prediction facts unchanged and falls back to deterministic prose when the
LLM tab is enabled.
"""

from __future__ import annotations

import json
import threading
from typing import Any, Callable, Optional

from . import fallback as FB
from .facts import citable_fact_ids, facts_cache_key, project_for_access
from .rules import (
    GENERIC_FACT_IDS,
    OUT_OF_SCOPE_REFUSAL,
    chat_user_prompt,
    followup_is_on_asked_topic,
    prompt_version,
    system_prompt_for,
    user_prompt,
)
from .schemas import (
    SCHEMA_VERSION,
    ChatAnswer,
    ConversationalAreasProse,
    ConversationalPalmProse,
    ConversationalProse,
    HoraryFacts,
    HoraryProse,
    LlmRunMeta,
    PalmFacts,
    QuestionFacts,
    QuestionProse,
    ReportFacts,
)
from .validate import (
    mind_now_topic_index,
    validate_area_dates_grounded,
    validate_chat_answer,
    validate_conversational_area,
    validate_family_line,
    validate_hand_contrast_note,
    validate_horary_prose,
    validate_mind_now_line,
    validate_prose_against_facts,
    validate_question_prose,
    validate_retains_fact_terms,
    validate_why_now,
    area_fact_terms,
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
            "rejection_reasons": (value.get("stats") or {}).get("rejection_reasons", {}),
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
    keep_last_on_failure: bool = False,
) -> tuple[Any, int, list[str]]:
    """Return (prose|None, retry_count, last_errors).

    ``keep_last_on_failure`` is for whole-page schemas that are screened slot
    by slot afterwards: returning the object lets the caller keep the clean
    paragraphs instead of throwing the page away over one bad sentence.
    """
    last_errors: list[str] = []
    last_prose: Any = None
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
        last_prose = prose
        fails = validate_fn(prose, facts) or []
        if not fails:
            return prose, retries, []
        last_errors = list(fails)
    if keep_last_on_failure and last_prose is not None:
        return last_prose, retries, last_errors
    return None, retries, last_errors


def _clip_to_sentence(text: str) -> str:
    """Drop a trailing fragment left behind by the schema length limit.

    Guided decoding stops at ``max_length`` mid-word, which reaches the reader
    as a severed sentence. Better to end one sentence early than to publish
    "with particular emphasis on your".
    """
    t = (text or "").strip()
    if not t or t[-1] in ".!?":
        return t
    cut = max(t.rfind(". "), t.rfind("! "), t.rfind("? "))
    if cut > 40:
        return t[: cut + 1].strip()
    # Comma-joined lists ("A, B, C, you benefit when you slow down before
    # stress accumu") have no sentence break to fall back to, so close on the
    # last complete clause or word instead of shipping a severed one.
    cut = t.rfind(", ")
    if cut > 40:
        return t[:cut].strip() + "."
    cut = t.rfind(" ")
    return (t[:cut].strip() + ".") if cut > 40 else t


def _as_sentence(text: str) -> str:
    """Open and close a fragment so area passages read as prose when joined."""
    t = _clip_to_sentence(text)
    if not t:
        return ""
    t = t[0].upper() + t[1:]
    return t if t[-1] in ".!?" else f"{t}."


def _conversational_overlay(prose: ConversationalProse, *, access: str) -> dict[str, Any]:
    areas: dict[str, Any] = {}
    if access == "paid":
        for a in list(prose.areas or []):
            key = str(getattr(a, "area", "") or "").strip()
            if not key:
                continue
            areas[key] = {
                "conclusion": _as_sentence(getattr(a, "conclusion", "") or ""),
                "astrological_basis": _as_sentence(getattr(a, "astrological_basis", "") or ""),
                "interpretation": _as_sentence(getattr(a, "interpretation", "") or ""),
                "outlook": _as_sentence(getattr(a, "outlook", "") or ""),
                # Models tend to echo the raw window label ("2026-10-31 →
                # 2027-01-25"); normalise it to a sentence a reader can say.
                "timing": FB.timing_sentence(getattr(a, "timing", "") or ""),
                "manifestation": _as_sentence(getattr(a, "manifestation", "") or ""),
                "remedy": _as_sentence(getattr(a, "remedy", "") or ""),
                "transition_note": _as_sentence(getattr(a, "transition_note", "") or ""),
            }
    return {
        "conversational": True,
        "astrological_basis": _clip_to_sentence(prose.astrological_basis or ""),
        "interpretation": _clip_to_sentence(prose.interpretation or ""),
        "personality": _clip_to_sentence(prose.personality),
        "current_phase": _clip_to_sentence(prose.current_phase),
        "final_guidance": _clip_to_sentence(getattr(prose, "final_guidance", "") or ""),
        "recent_months": _clip_to_sentence(prose.recent_months or ""),
        "hardest_area_note": _clip_to_sentence(prose.hardest_area_note or ""),
        "mind_now": [_as_sentence(x) for x in list(prose.mind_now or []) if str(x).strip()],
        "why_now": _clip_to_sentence(prose.why_now or ""),
        "family_note": [_as_sentence(x) for x in list(prose.family_note or []) if str(x).strip()][:4],
        "areas": areas,
    }


def _conversational_palm_overlay(
    prose: ConversationalPalmProse, *, access: str,
) -> dict[str, Any]:
    areas: dict[str, Any] = {}
    if access == "paid":
        from palm_api.life_aspects import _ASPECT_VEDIC_UPAYAS
        for a in list(prose.areas or []):
            key = str(getattr(a, "aspect", "") or "").strip()
            if not key:
                continue
            rem = str(getattr(a, "remedy", "") or "")
            if not rem or "guru beej" in rem.lower():
                rem = _ASPECT_VEDIC_UPAYAS.get(key, {}).get("upaya", rem)
            areas[key] = {
                "outlook": _as_sentence(getattr(a, "outlook", "") or ""),
                "timing": _as_sentence(getattr(a, "timing", "") or ""),
                "manifestation": _as_sentence(getattr(a, "manifestation", "") or ""),
                "remedy": rem,
            }
    return {
        "conversational": True,
        "personality": _clip_to_sentence(prose.personality),
        "current_phase": _clip_to_sentence(prose.current_phase),
        "hardest_area_note": _clip_to_sentence(prose.hardest_area_note or ""),
        "mind_now": [_as_sentence(x) for x in list(prose.mind_now or []) if str(x).strip()],
        "why_now": _clip_to_sentence(prose.why_now or ""),
        "hand_contrast_note": _clip_to_sentence(prose.hand_contrast_note or ""),
        "areas": areas,
    }



# ---------------------------------------------------------------------------
# Per-tab humanizers
# ---------------------------------------------------------------------------
def _humanize_report(facts: ReportFacts) -> tuple[dict, dict, bool, int]:
    """Generate grounded prose from deterministic analytical facts.

    Qwen writes language only. Paid uses two small calls (opening/current chapter
    and life-area passages) because a 7B model is more reliable with bounded JSON.
    There is deliberately no second "rewrite the rewrite" pass.
    """
    stats = {"accepted": 0, "rejected": 0, "errors": 0, "rejection_reasons": {}}
    access = str(getattr(facts, "access", "free") or "free")
    paid = access == "paid"

    def reject(reason_list: list[str]) -> None:
        for reason in reason_list or ["unknown_rejection"]:
            key = str(reason).split(":", 1)[0][:80]
            stats["rejection_reasons"][key] = stats["rejection_reasons"].get(key, 0) + 1

    prose, retries, errs = _complete_validated(
        ConversationalProse,
        system_prompt_for("full_report"),
        user_prompt(facts, schema_name="ConversationalProse", section="page")
        + (
            "\nWrite in the voice of a practising Vedic astrologer. astrological_basis must name the supplied chart factors and briefly explain their astrological significance; interpretation must connect those factors to lived experience rather than philosophy. current_phase must be 2–4 sentences using "
            "phase_tone, phase_end and phase_notes — never a single word like "
            "'supportive'. recent_months must mention each supplied window. "
            "mind_now needs one hedged line per life_state.mind_now entry and "
            "why_now needs 2–4 sentences explaining the supplied astrological reason this stretch feels as it does and how that can manifest. "
            "family_note needs one line per family_notes entry, in order, each "
            "naming that relation and using only that entry's own notes. "
            "first_name is there so you know who you are talking to, not to "
            "write about them: every field says 'you' and 'your', never the "
            "reader's name and never she/he. "
        )
        + (
            "Leave areas empty — the life areas are requested separately."
            if paid else
            "When access=free, leave areas empty."
        ),
        facts,
        validate_prose_against_facts,
        keep_last_on_failure=True,
    )
    if prose is None:
        stats["rejected"] += 1
        reject(errs or ["empty_conversational_prose"])
        # Do not mark accepted — switch stays on the classic frozen renderer.
        return FB.conversational_fallback(facts), stats, True, retries

    # Free must never carry paid area detail even if the model returns it.
    overlay = _conversational_overlay(prose, access=access)
    overlay["areas"] = _humanize_report_areas(facts, stats) if paid else {}
    # Per-slot QA. One bad life area must not discard the whole page: drop the
    # offending slot and let deterministic fact prose fill it.
    overlay, kept, dropped = _screen_conversational_slots(overlay, facts, stats)
    overlay = _merge_conversational_facts(overlay, facts, access=access)

    # Deliberately no second LLM rephrase pass. Qwen 2.5 7B already receives
    # the deterministic analytical layer and is asked to express it once. A
    # second rewrite adds latency and is the easiest place for semantic drift.
    if not str(overlay.get("personality") or "").strip():
        stats["rejected"] += 1
        reject(["empty_conversational_prose"])
        return FB.conversational_fallback(facts), stats, True, retries
    stats["accepted"] = max(1, kept)
    stats["rejected"] += dropped
    return overlay, stats, dropped > 0 and kept == 0, retries


def _humanize_report_areas(facts: Any, stats: dict[str, Any]) -> dict[str, Any]:
    """The paid life-area passages, asked for on their own card facts.

    A failure here is not a failed page: the merge step fills every missing
    area from deterministic prose, so the worst case is the reading a reader
    would have got before the model was switched on.

    Eight conclusions plus their facts together exceed the endpoint's 8k
    context, so the cards are asked for in two chunks of four. Each chunk is
    validated against the full facts (the gate only inspects the areas present
    in the reply), and the accepted entries are merged into one overlay.
    """
    from .rules import areas_user_prompt

    card_areas = []
    try:
        for c in list(getattr(facts, "cards", None) or []):
            area = str(getattr(c, "area", "") or "").strip()
            if area:
                card_areas.append(area)
    except Exception:  # noqa: BLE001
        card_areas = []

    out: dict[str, Any] = {}
    chunk_size = 4
    for start in range(0, max(1, len(card_areas)), chunk_size):
        chunk_keys = card_areas[start:start + chunk_size]
        prose, _retries, errs = _complete_validated(
            ConversationalAreasProse,
            system_prompt_for("full_report_areas"),
            areas_user_prompt(facts, area_keys=chunk_keys),
            facts,
            validate_prose_against_facts,
            keep_last_on_failure=True,
        )
        if prose is None:
            stats["rejection_reasons"]["areas:empty_or_model_failure"] = (
                stats["rejection_reasons"].get(
                    "areas:empty_or_model_failure", 0) + 1
            )
            for reason in errs or []:
                key = f"areas:{str(reason).split(':', 1)[0]}"[:80]
                stats["rejection_reasons"][key] = (
                    stats["rejection_reasons"].get(key, 0) + 1
                )
            continue
        for a in list(prose.areas or []):
            key = str(getattr(a, "area", "") or "").strip()
            if not key or key in out:
                continue
            conclusion = _as_sentence(getattr(a, "conclusion", "") or "")
            if not conclusion or any(x.lower() in conclusion.lower() for x in (
                "this remedy is linked to a relevant chart factor",
                "the chart evidence is summarized in the life-area reading above",
                "timing evidence is included in the overall reading",
                "promised, not yet active",
            )):
                continue
            out[key] = {
                "conclusion": conclusion,
                "astrological_basis": _as_sentence(getattr(a, "astrological_basis", "") or ""),
                "interpretation": _as_sentence(getattr(a, "interpretation", "") or ""),
                "outlook": _as_sentence(getattr(a, "outlook", "") or ""),
                "timing": FB.timing_sentence(getattr(a, "timing", "") or ""),
                "manifestation": _as_sentence(getattr(a, "manifestation", "") or ""),
                "remedy": _as_sentence(getattr(a, "remedy", "") or ""),
            }
    return out


def _screen_conversational_slots(
    overlay: dict[str, Any], facts: Any, stats: dict[str, Any],
) -> tuple[dict[str, Any], int, int]:
    """Validate each prose slot on its own facts; blank the ones that fail."""
    from .rules import check_prose

    out = dict(overlay or {})
    kept = 0
    dropped = 0

    def note(reason: str) -> None:
        # Slot plus gate name, dropping any variable tail such as an area key:
        # "areas.outlook" alone cannot tell an overclaimed promise from leaked
        # jargon, and those two want opposite fixes.
        key = ":".join(str(reason).split(":")[:2])[:80]
        stats["rejection_reasons"][key] = stats["rejection_reasons"].get(key, 0) + 1

    for key in ("astrological_basis", "interpretation", "personality",
                "current_phase", "final_guidance", "recent_months", "hardest_area_note",
                "why_now"):
        text = str(out.get(key) or "").strip()
        if not text:
            continue
        problems = check_prose(text, facts)
        if key == "why_now":
            problems += validate_why_now(text)
        if problems:
            dropped += 1
            for p in problems:
                note(f"{key}:{p}")
            out[key] = ""
        else:
            kept += 1

    # One bad "on your mind" line must not cost the whole block, and a line
    # that names a topic the reading never flagged is worse than no line.
    mind_lines: list[str] = []
    for line in list(out.get("mind_now") or []):
        text = str(line or "").strip()
        if not text:
            continue
        problems = check_prose(text, facts)
        problems += validate_mind_now_line(text, facts)
        if problems:
            dropped += 1
            for p in problems:
                # Keep the gate name: "mind_now" alone cannot tell an invented
                # topic from a line that was merely stated too flatly.
                note(f"mind_now.{p}")
            continue
        kept += 1
        mind_lines.append(text)
    out["mind_now"] = mind_lines[:3]

    # A misattributed relative is the most checkable error on the page — the
    # reader knows these people — so a failing line is dropped, not repaired.
    family_lines: list[str] = []
    for line in list(out.get("family_note") or []):
        text = str(line or "").strip()
        if not text:
            continue
        problems = check_prose(text, facts)
        problems += validate_family_line(text, facts)
        if problems:
            dropped += 1
            for p in problems:
                note(f"family_note.{p}")
            continue
        kept += 1
        family_lines.append(text)
    out["family_note"] = family_lines[:4]

    cards = {getattr(c, "area", ""): c for c in (getattr(facts, "cards", None) or [])}
    areas = dict(out.get("areas") or {})
    for area, block in list(areas.items()):
        if not isinstance(block, dict):
            areas.pop(area, None)
            continue
        card = cards.get(area)
        if card is None:
            dropped += 1
            note(f"areas:unknown_area:{area}")
            areas.pop(area, None)
            continue
        mini = _single_card_facts(facts, card)
        cleaned = {}
        for field, value in block.items():
            text = str(value or "").strip()
            if not text:
                continue
            problems = check_prose(text, mini, area=area)
            problems += validate_conversational_area(field, text, card)
            if field in ("outlook", "manifestation"):
                problems += validate_retains_fact_terms(text, area_fact_terms(card))
            if field in ("conclusion", "outlook"):
                problems += validate_area_dates_grounded(text, mini)
            if problems:
                dropped += 1
                for p in problems:
                    note(f"areas.{field}:{p}")
                continue
            cleaned[field] = text
            kept += 1
        areas[area] = cleaned
    out["areas"] = areas
    return out, kept, dropped


def _single_card_facts(facts: Any, card: Any) -> Any:
    """Mini ReportFacts holding one card, for per-area grounding checks."""
    try:
        area_key = getattr(card, "area", "") or (card.get("area") if isinstance(card, dict) else "")
        all_aj = list(getattr(facts, "life_area_judgements", None) or [])
        matched_aj = [x for x in all_aj if getattr(x, "area", "") == area_key] or all_aj
        return ReportFacts(
            first_name=getattr(facts, "first_name", ""),
            age_band=getattr(facts, "age_band", "adult"),
            age_years=getattr(facts, "age_years", None),
            gender=getattr(facts, "gender", "unknown"),
            access=getattr(facts, "access", "free"),
            cards=[card],
            timing_windows=list(getattr(card, "timing_windows", None) or []),
            personality_traits=list(getattr(facts, "personality_traits", None) or []),
            phase_direction=getattr(facts, "phase_direction", "mixed"),
            phase_tone=getattr(facts, "phase_tone", ""),
            phase_end=getattr(facts, "phase_end", ""),
            phase_notes=list(getattr(facts, "phase_notes", None) or []),
            recent_months=list(getattr(facts, "recent_months", None) or []),
            hardest_areas=list(getattr(facts, "hardest_areas", None) or []),
            hardest_area_labels=list(getattr(facts, "hardest_area_labels", None) or []),
            schema_version=getattr(facts, "schema_version", SCHEMA_VERSION),
            engine_version=getattr(facts, "engine_version", ""),
            report_id=getattr(facts, "report_id", ""),
            facts_hash=getattr(facts, "facts_hash", ""),
            vedic_context=getattr(facts, "vedic_context", None),
            timing_systems=list(getattr(facts, "timing_systems", None) or []),
            crossover_points=list(getattr(facts, "crossover_points", None) or []),
            slow_transits=list(getattr(facts, "slow_transits", None) or []),
            jaimini=getattr(facts, "jaimini", None),
            dasha_planet_transits=list(getattr(facts, "dasha_planet_transits", None) or []),
            life_area_judgements=matched_aj,
        )
    except Exception:  # noqa: BLE001
        return facts


def _merge_conversational_facts(
    overlay: dict[str, Any], facts: Any, *, access: str,
) -> dict[str, Any]:
    """Fill thin LLM slots from Python facts so the page is never skeletal."""
    fb = FB.conversational_fallback(facts)
    out = dict(overlay or {})
    for key in ("astrological_basis", "interpretation", "personality",
                "current_phase", "final_guidance", "recent_months", "hardest_area_note",
                "why_now"):
        cur = str(out.get(key) or "").strip()
        # Bare tone words, bare label lists or empty slots → deterministic prose.
        looks_like_a_sentence = " is " in cur or " are " in cur or "." in cur
        if len(cur) < 40 or not looks_like_a_sentence or cur.lower() in {
            "supportive", "mixed", "demanding", "caution",
        }:
            if fb.get(key):
                out[key] = fb[key]
    # The block is either the model's or Python's, never half of each: a mix of
    # two voices in three consecutive lines is what reads as machine-written.
    kept_mind = [str(x).strip() for x in (out.get("mind_now") or []) if str(x).strip()]
    expected = len(list(getattr(getattr(facts, "life_state", None), "mind_now", None) or []))
    if len(kept_mind) < expected:
        kept_mind = list(fb.get("mind_now") or []) or kept_mind
    out["mind_now"] = kept_mind[:3]
    # Same rule for the background block, and for the same reason: a page that
    # covers the father and then goes quiet about the mother reads as an error.
    kept_family = [str(x).strip() for x in (out.get("family_note") or []) if str(x).strip()]
    expected_family = len(list(getattr(facts, "family_notes", None) or []))
    if access == "paid":
        if len(kept_family) < expected_family:
            kept_family = list(fb.get("family_note") or []) or kept_family
        out["family_note"] = kept_family[:4]
    else:
        # Free keeps a small family/home teaser. The deeper family reading is
        # still access-controlled by the renderer, but silently deleting the
        # whole block makes About You feel incomplete.
        if len(kept_family) < min(2, expected_family):
            kept_family = list(fb.get("family_note") or []) or kept_family
        out["family_note"] = kept_family[:2]
    if access == "paid":
        cards = {getattr(c, "area", ""): c for c in (getattr(facts, "cards", None) or [])}
        areas = dict(out.get("areas") or {})
        for area, block in (fb.get("areas") or {}).items():
            cur = areas.get(area) if isinstance(areas.get(area), dict) else {}
            merged = dict(block or {})
            for field in ("conclusion", "astrological_basis", "interpretation", "outlook",
                          "timing", "manifestation", "remedy", "transition_note"):
                if str(cur.get(field) or "").strip():
                    merged[field] = cur[field]
            # A difficulty must never be published without the step that helps.
            card = cards.get(area)
            if card is not None and not str(merged.get("remedy") or "").strip():
                if FB._area_needs_remedy(card):
                    merged["remedy"] = FB._area_remedy_sentence(
                        card, str(getattr(card, "label", "") or area.replace("_", " "))
                    )
            if card is not None:
                label, cls = FB.area_tone(card)
                merged["tone_label"], merged["tone_class"] = label, cls
            areas[area] = _drop_repeated_remedy(merged)
        out["areas"] = areas
    else:
        out["areas"] = {}
    out["conversational"] = True
    return out


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
    """One ConversationalPalmProse call for the whole palm page."""
    stats = {"accepted": 0, "rejected": 0, "errors": 0, "rejection_reasons": {}}
    access = str(getattr(facts, "access", "free") or "free")

    def reject(reason_list: list[str]) -> None:
        for reason in reason_list or ["unknown_rejection"]:
            key = str(reason)[:120]
            stats["rejection_reasons"][key] = stats["rejection_reasons"].get(key, 0) + 1

    prose, retries, errs = _complete_validated(
        ConversationalPalmProse,
        system_prompt_for("palm"),
        user_prompt(facts, schema_name="ConversationalPalmProse")
        + (
            "\nWrite full sentences. current_phase must combine life_stage_note "
            "with the demanding aspect. mind_now needs one hedged line per "
            "palm_state.mind_now entry, why_now needs 2–4 sentences on why the "
            "reading feels as it does, and hand_contrast_note needs 2–3 "
            "sentences built only from hand_contrast. When access=paid, return "
            "one areas[] entry for EVERY aspect with outlook, timing, "
            "manifestation and remedy (remedy only when remedies_allowed)."
        ),
        facts,
        validate_prose_against_facts,
        keep_last_on_failure=True,
    )
    if prose is None:
        stats["rejected"] += 1
        reject(errs or ["empty_conversational_palm_prose"])
        return FB.conversational_palm_fallback(facts), stats, True, retries

    overlay = _conversational_palm_overlay(prose, access=access)
    if access != "paid":
        overlay["areas"] = {}
    overlay, kept, dropped = _screen_palm_slots(overlay, facts, stats)
    overlay = _merge_conversational_palm_facts(overlay, facts, access=access)
    if not str(overlay.get("personality") or "").strip():
        stats["rejected"] += 1
        reject(["empty_conversational_palm_prose"])
        return FB.conversational_palm_fallback(facts), stats, True, retries
    stats["accepted"] = max(1, kept)
    stats["rejected"] += dropped
    return overlay, stats, dropped > 0 and kept == 0, retries


def _screen_palm_slots(
    overlay: dict[str, Any], facts: Any, stats: dict[str, Any],
) -> tuple[dict[str, Any], int, int]:
    from .rules import check_prose

    out = dict(overlay or {})
    kept = 0
    dropped = 0

    def note(reason: str) -> None:
        key = str(reason)[:120]
        stats["rejection_reasons"][key] = stats["rejection_reasons"].get(key, 0) + 1

    for key in ("personality", "current_phase", "hardest_area_note",
                "why_now", "hand_contrast_note"):
        text = str(out.get(key) or "").strip()
        if not text:
            continue
        problems = check_prose(text, facts)
        if key == "why_now":
            problems += validate_why_now(text)
        elif key == "hand_contrast_note":
            problems += validate_hand_contrast_note(text, facts)
        if problems:
            dropped += 1
            for p in problems:
                note(f"{key}:{p}")
            out[key] = ""
        else:
            kept += 1

    # One bad "on your mind" line must not cost the whole block, and a line
    # naming a theme the hands never showed is worse than no line.
    mind_lines: list[str] = []
    seen_topics: set[int] = set()
    for line in list(out.get("mind_now") or []):
        text = str(line or "").strip()
        if not text:
            continue
        problems = check_prose(text, facts)
        problems += validate_mind_now_line(text, facts)
        topic = mind_now_topic_index(text, facts)
        if topic is not None and topic in seen_topics:
            # Three lines about the same theme drop the area that is going
            # well, which is the half of the block that keeps it a reading
            # rather than a warning.
            problems.append("mind_now_repeats_one_topic")
        if problems:
            dropped += 1
            for p in problems:
                note(f"mind_now:{p}")
            continue
        if topic is not None:
            seen_topics.add(topic)
        kept += 1
        mind_lines.append(text)
    out["mind_now"] = mind_lines[:3]

    areas = dict(out.get("areas") or {})
    aspects = {
        str(getattr(a, "aspect", "") or ""): a
        for a in (getattr(facts, "aspects", None) or [])
    }
    for aspect, block in list(areas.items()):
        if not isinstance(block, dict):
            areas.pop(aspect, None)
            continue
        cleaned = {}
        card = aspects.get(aspect)
        for field, value in block.items():
            text = str(value or "").strip()
            if not text:
                continue
            problems = check_prose(text, facts, area=aspect)
            if field in ("outlook", "manifestation") and card is not None:
                problems += validate_retains_fact_terms(text, area_fact_terms(card))
            if problems:
                dropped += 1
                for p in problems:
                    note(f"areas.{field}:{p}")
                continue
            cleaned[field] = text
            kept += 1
        areas[aspect] = cleaned
    out["areas"] = areas
    return out, kept, dropped


# A paid palm page asks for four fields across eight aspects in one reply, and
# a model that runs short answers "Positive." — which passes every gate and
# says nothing. Below these lengths the deterministic line, built from the
# aspect's own summary, is the better sentence.
_PALM_AREA_FLOOR = {
    "outlook": 40, "timing": 20, "manifestation": 25, "remedy": 25,
}


def _drop_repeated_remedy(block: dict[str, Any]) -> dict[str, Any]:
    """If manifestation merely repeats the remedy, keep the remedy only."""
    out = dict(block or {})
    rem = str(out.get("remedy") or "").strip()
    man = str(out.get("manifestation") or "").strip()
    if rem and man:
        r_l = rem.lower().rstrip(".")
        m_l = man.lower().rstrip(".")
        if m_l == r_l or r_l in m_l or m_l in r_l:
            out["manifestation"] = ""
    return out


def _merge_conversational_palm_facts(
    overlay: dict[str, Any], facts: Any, *, access: str,
) -> dict[str, Any]:
    fb = FB.conversational_palm_fallback(facts)
    out = dict(overlay or {})
    for key in ("personality", "current_phase", "hardest_area_note",
                "why_now", "hand_contrast_note"):
        cur = str(out.get(key) or "").strip()
        if len(cur) < 40:
            if fb.get(key):
                out[key] = fb[key]
    # The block is either the model's or Python's, never half of each: two
    # voices across three consecutive lines is what reads as machine-written.
    kept_mind = [str(x).strip() for x in (out.get("mind_now") or []) if str(x).strip()]
    expected = len(list(getattr(getattr(facts, "palm_state", None), "mind_now", None) or []))
    if len(kept_mind) < expected:
        kept_mind = list(fb.get("mind_now") or []) or kept_mind
    out["mind_now"] = kept_mind[:3]
    # The care note sits directly under the phase paragraph and just above the
    # "on your mind" list; repeating either of them reads as a copy-paste slip.
    note = str(out.get("hardest_area_note") or "").strip()
    neighbours = [str(out.get("current_phase") or "").strip()]
    neighbours += [str(x) for x in (out.get("mind_now") or [])]
    if note and any(
        text and (note in text or note[:60] in text) for text in neighbours
    ):
        out["hardest_area_note"] = fb.get("hardest_area_note") or ""
    personality = str(out.get("personality") or "").strip()
    if access == "paid":
        areas = dict(out.get("areas") or {})
        for aspect, block in (fb.get("areas") or {}).items():
            cur = areas.get(aspect) if isinstance(areas.get(aspect), dict) else {}
            merged = dict(block or {})
            for field, floor in _PALM_AREA_FLOOR.items():
                text = str(cur.get(field) or "").strip()
                if len(text) >= floor:
                    merged[field] = text
            if aspect == "character":
                outlook = str(merged.get("outlook") or "").strip()
                if outlook and personality:
                    if outlook[:80].lower() in personality.lower() or personality[:80].lower() in outlook.lower():
                        fb_outlook = str((fb.get("areas") or {}).get("character", {}).get("outlook") or "")
                        if fb_outlook and fb_outlook[:80].lower() not in personality.lower():
                            merged["outlook"] = fb_outlook
            areas[aspect] = _drop_repeated_remedy(merged)
        out["areas"] = areas
    else:
        out["areas"] = {}
    out["conversational"] = True
    return out


def _deterministic_overlay(kind: str, facts: Any) -> dict[str, Any]:
    """Python's own prose for a kind — used when the model is off or unusable.

    Facts must already be projected for the tier being written: this writes the
    prose a customer reads, so free prose may never be composed from paid facts.
    """
    try:
        if kind == "full_report" and isinstance(facts, ReportFacts):
            return FB.conversational_fallback(facts)
        if kind == "user_question" and isinstance(facts, QuestionFacts):
            return FB.question_fallback(facts)
        if kind == "horary" and isinstance(facts, HoraryFacts):
            return FB.horary_fallback(facts)
        if kind == "palm" and isinstance(facts, PalmFacts):
            return FB.conversational_palm_fallback(facts)
    except Exception as exc:  # noqa: BLE001
        print(f"[llm] deterministic prose failed kind={kind}: "
              f"{type(exc).__name__}: {exc}", flush=True)
    return {}


def humanize(kind: str, facts: Any, *, access: str = "free") -> dict:
    """Public entry. Returns overlay + stats + run meta (never for customer HTML).

    The overlay is always deterministic prose at worst — never empty — so a
    model that is switched off, unreachable or failing QA costs the reader
    wording, not whole sections. ``enabled`` still reports the model's state.
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
        "stats": {"accepted": 0, "rejected": 0, "errors": 0, "rejection_reasons": {}},
        "enabled": False,
        "kind": kind,
        "access": access_n,
        "fallback_used": False,
        "run_meta": meta.model_dump(),
    }
    # Ensure access projection matches the requested tier. This runs before the
    # enabled check because the disabled path writes prose from these facts too.
    try:
        facts = project_for_access(facts, access_n)
    except Exception:  # noqa: BLE001
        pass
    if hasattr(facts, "access"):
        try:
            facts.access = access_n  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

    if not _enabled(kind):
        # A switched-off model must not thin the page out. Renderers read the
        # same overlay either way, so hand them Python's prose rather than
        # nothing — the state the enabled path already reaches when QA rejects
        # every draft.
        overlay = _deterministic_overlay(kind, facts)
        if overlay:
            meta.fallback_used = True
            out["overlay"] = overlay
            out["fallback_used"] = True
            out["run_meta"] = meta.model_dump()
        return out

    out["enabled"] = True
    meta.enabled = True

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
            "rejection_reasons": (cached.get("stats") or {}).get("rejection_reasons", {}),
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
        overlay = _deterministic_overlay(kind, facts)
        if overlay:
            meta.fallback_used = True
            meta.errors = 1
            out["overlay"] = overlay
            out["fallback_used"] = True
            out["run_meta"] = meta.model_dump()
        return out

    meta.retry_count = retries
    meta.fallback_used = fallback_used
    meta.accepted = int(stats.get("accepted") or 0)
    meta.rejected = int(stats.get("rejected") or 0)
    meta.errors = int(stats.get("errors") or 0)
    meta.rejection_reasons = dict(stats.get("rejection_reasons") or {})

    out["overlay"] = overlay
    out["stats"] = stats
    out["fallback_used"] = fallback_used
    out["run_meta"] = meta.model_dump()
    # Do not cache fallback/empty runs — a missing client or 429 would
    # otherwise pin template prose for the rest of the TTL.
    if overlay and not fallback_used and int(stats.get("accepted") or 0) > 0:
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
    available_fact_ids = set(GENERIC_FACT_IDS)
    try:
        available_fact_ids |= citable_fact_ids(facts)
    except Exception:  # noqa: BLE001
        pass
    prose, _retries, errs = _complete_validated(
        ChatAnswer,
        system_prompt_for("chat"),
        chat_user_prompt(
            facts,
            question,
            history=hist[-6:],
            available_fact_ids=sorted(available_fact_ids)[:80],
        ),
        facts,
        validate_chat_answer,
        temperature=0.3,
    )
    on_topic = followup_is_on_asked_topic(facts, question)
    is_palm = str(
        facts.get("kind") if isinstance(facts, dict) else getattr(facts, "kind", "")
    ) == "palm"
    if prose is None:
        result["stats"]["rejected"] = 1
        # Keep why it was rejected: a refusal the customer sees for a fair
        # question is a bug, and without the reasons it is invisible in logs.
        result["stats"]["rejection_reasons"] = list(errs or [])
        result["fallback_used"] = True
        if on_topic:
            if is_palm:
                result["answer"] = FB.palm_chat_fallback(facts, question)
            else:
                result["answer"] = FB.question_chat_fallback(facts)
            result["out_of_scope"] = False
            result["used_fact_ids"] = ["question", "direction", "timing"]
            return result
        result["answer"] = (
            "I can only speak from the facts already in your reading. "
            "Please ask about a life area or timing window shown there."
        )
        return result
    if prose.out_of_scope:
        # The model treats "the case / the verdict" as a new topic because
        # the prompt used to describe every non-palm/horary reading as a
        # life-area chart. This report is that question; answer from facts.
        if on_topic:
            if is_palm:
                result["answer"] = FB.palm_chat_fallback(facts, question)
            else:
                result["answer"] = FB.question_chat_fallback(facts)
            result["out_of_scope"] = False
            result["used_fact_ids"] = ["question", "direction", "timing"]
            result["fallback_used"] = True
            result["stats"]["rejected"] = 1
            result["stats"]["rejection_reasons"] = ["false_out_of_scope_on_asked_topic"]
            return result
        result["answer"] = OUT_OF_SCOPE_REFUSAL
        result["out_of_scope"] = True
        result["stats"]["accepted"] = 1
        return result
    result["answer"] = prose.answer
    result["out_of_scope"] = False
    result["used_fact_ids"] = list(prose.used_fact_ids or [])
    result["stats"]["accepted"] = 1
    return result
