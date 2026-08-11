"""Reject LLM prose that invents facts, dates, planets, or certainty."""

from __future__ import annotations

import re
import json
from typing import Any, Iterable, Optional

from .rules import check_prose, check_prose_fields
from .facts import public_fact_payload
from .schemas import QuestionFacts


def _walk_strings(obj: Any) -> Iterable[str]:
    if obj is None:
        return
    if isinstance(obj, str):
        yield obj
        return
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
        return
    if isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _walk_strings(v)
        return
    if hasattr(obj, "model_dump"):
        yield from _walk_strings(obj.model_dump())


def _collect_text(obj: Any) -> str:
    return " ".join(_walk_strings(obj))


def _field_pairs(prose: Any) -> list[tuple[str, str]]:
    if prose is None:
        return []
    if hasattr(prose, "model_dump"):
        data = prose.model_dump()
    elif isinstance(prose, dict):
        data = prose
    else:
        return [("text", str(prose))]
    pairs: list[tuple[str, str]] = []
    for k, v in data.items():
        if isinstance(v, str) and v.strip():
            pairs.append((k, v))
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, str) and item.strip():
                    pairs.append((f"{k}[{i}]", item))
                elif isinstance(item, dict):
                    for sk, sv in item.items():
                        if isinstance(sv, str) and sv.strip():
                            pairs.append((f"{k}[{i}].{sk}", sv))
                        elif isinstance(sv, list):
                            for j, x in enumerate(sv):
                                if isinstance(x, str) and x.strip():
                                    pairs.append((f"{k}[{i}].{sk}[{j}]", x))
    return pairs


def validate_slot(
    text: str,
    facts: Any,
    *,
    age_band: str = "",
    area: str = "",
) -> list[str]:
    """Return violations for one prose string (empty = accept)."""
    del age_band  # reserved for future age-stage gates
    return check_prose(text or "", facts, area=area)


def validate_prose_against_facts(prose: Any, facts: Any, *, area: str = "") -> list[str]:
    """Primary QA gate from the correction plan. Empty list = accept."""
    errors: list[str] = []
    text = _collect_text(prose)
    if not text.strip():
        return ["empty_prose"]

    area_hint = area
    if not area_hint and hasattr(prose, "area"):
        area_hint = getattr(prose, "area", "") or ""

    errors.extend(check_prose_fields(_field_pairs(prose), facts, area=area_hint))

    # User-question truth contract: when QuestionFacts came from the full
    # report, the question prose must be grounded in that same canonical
    # promise/activation/timing source. This is a validation invariant, not a
    # prompt instruction.
    if isinstance(facts, QuestionFacts):
        if getattr(facts, "truth_source", "") == "full_report_canonical":
            if getattr(facts, "promise_status", "") != getattr(facts, "canonical_promise_status", ""):
                errors.append("question_canonical_promise_mismatch")
            if getattr(facts, "activation_status", "") != getattr(facts, "canonical_activation_status", ""):
                errors.append("question_canonical_activation_mismatch")
            if getattr(facts, "timing_can_create_promise", False):
                errors.append("question_timing_can_create_promise")

    # Promise / activation consistency for report cards
    cards_facts = getattr(facts, "cards", None)
    if cards_facts is not None and hasattr(prose, "area"):
        fact_by_area = {
            getattr(c, "area", ""): c for c in cards_facts if getattr(c, "area", "")
        }
        cf = fact_by_area.get(getattr(prose, "area", ""))
        if cf is None and getattr(prose, "area", ""):
            # Allow single-card mini facts where cards=[that card]
            if len(list(cards_facts)) == 1:
                cf = cards_facts[0]
            else:
                errors.append(f"unknown_area:{getattr(prose, 'area', '')}")
        if cf is not None:
            status = (getattr(cf, "status", "") or "").lower()
            act = (getattr(cf, "activation_status", "") or "").lower()
            blob = text.lower()
            if status in ("weak", "insufficient_evidence", "mixed"):
                if re.search(
                    r"\b(strongly supported|highly favoured|guaranteed|career success is guaranteed)\b",
                    blob,
                ):
                    errors.append(f"overclaim_status:{getattr(cf, 'area', '')}")
            if act in ("inactive", "weak", "insufficient_evidence"):
                if re.search(
                    r"\b(now is the time|peak window|strongly active now)\b", blob
                ):
                    errors.append(f"overclaim_activation:{getattr(cf, 'area', '')}")

    # Question direction consistency
    if hasattr(facts, "direction") and hasattr(prose, "answer"):
        direction = (getattr(facts, "direction", "") or "").lower()
        answer = (getattr(prose, "answer", "") or "").lower()
        if direction in ("caution", "down") and re.search(
            r"\b(strongly favours|highly supportive|excellent prospects)\b", answer
        ):
            errors.append("question_direction_mismatch")
        if direction in ("support", "up") and re.search(
            r"\b(does not support|unlikely|poor prospects)\b", answer
        ):
            errors.append("question_direction_mismatch")
        if (getattr(facts, "promise_status", "") or "").lower() in (
            "weak",
            "insufficient_evidence",
        ):
            if re.search(r"\b(definitely|guaranteed|will happen)\b", answer):
                errors.append("question_overclaim")

    # Horary: verdict label should remain grounded
    if hasattr(facts, "label") and hasattr(prose, "verdict_line"):
        label = (getattr(facts, "label", "") or "").strip().lower()
        vl = (getattr(prose, "verdict_line", "") or "").lower()
        if label:
            if "yes" in label and not re.search(r"\b(yes|support|favour|favor|lean|open)\b", vl):
                errors.append("horary_label_mismatch")
            elif "no" in label and not re.search(r"\b(no|caution|unlikely|does not favour|does not favor)\b", vl):
                errors.append("horary_label_mismatch")

    # Stronger status grounding. The old gate only rejected words such as
    # "guaranteed", allowing "moderate chance of positive developments" even
    # when the canonical promise was limited/insufficient.
    payload = public_fact_payload(facts) if facts is not None else {}
    if isinstance(payload, dict):
        promise_status = str(payload.get("promise_status") or "").lower()
        if not promise_status and isinstance(payload.get("cards"), list) and hasattr(prose, "area"):
            area = str(getattr(prose, "area", "") or "")
            for card in payload.get("cards") or []:
                if isinstance(card, dict) and str(card.get("area") or "") == area:
                    promise_status = str(card.get("status") or "").lower()
                    break
        if promise_status in ("weak", "insufficient_evidence"):
            if re.search(
                r"\b(moderate chance|good chance|positive developments|strong prospects|"
                r"strong improvement|highly supportive|very favourable|very favorable|"
                r"likely to improve|clear improvement)\b",
                text, re.I,
            ):
                errors.append("weak_promise_positive_escalation")
        elif promise_status == "mixed":
            if re.search(
                r"\b(guaranteed|definitely|certainly|clear improvement|strong prospects)\b",
                text, re.I,
            ):
                errors.append("mixed_promise_escalation")

        # Relationship/parenthood status must never be inferred from a generic
        # area fact.
        if re.search(r"\b(your spouse|your husband|your wife|your children|your child)\b", text, re.I):
            raw = json.dumps(payload, default=str).lower()
            if not any(x in raw for x in ("married", "spouse", "husband", "wife", "existing_child",
                                          "existing children", "parent")):
                errors.append("assumed_relationship_or_parent_status")

    # Palm facts have no dates unless explicitly supplied. Do not let a model
    # manufacture an age window from signal IDs or internal engine metadata.
    if isinstance(payload, dict) and payload.get("kind") == "palm":
        if re.search(r"\b(?:age|aged)\s+\d{1,3}\b", text, re.I):
            allowed = " ".join(str(x) for x in (payload.get("future_windows") or []))
            if not re.search(r"\b\d{1,3}\b", allowed):
                errors.append("palm_unvalidated_age")

    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for e in errors:
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out


def validate_card_prose(
    prose: Any,
    facts: Any,
    *,
    age_band: str = "",
) -> list[str]:
    del age_band
    return validate_prose_against_facts(prose, facts, area=getattr(prose, "area", ""))


def validate_question_prose(prose: Any, facts: Any) -> list[str]:
    return validate_prose_against_facts(prose, facts)


def validate_horary_prose(prose: Any, facts: Any) -> list[str]:
    return validate_prose_against_facts(prose, facts)


def validate_palm_prose(prose: Any, facts: Any) -> list[str]:
    return validate_prose_against_facts(prose, facts)


def validate_chat_answer(prose: Any, facts: Any) -> list[str]:
    if getattr(prose, "out_of_scope", False):
        return []
    errors = validate_prose_against_facts(prose, facts)
    used = list(getattr(prose, "used_fact_ids", None) or [])
    if not used:
        errors.append("chat_missing_used_fact_ids")
    else:
        payload = public_fact_payload(facts)
        raw = json.dumps(payload, default=str)
        allowed_ids = {
            "promise", "activation", "direction", "confidence", "timing",
            "manifestation", "action", "remedy", "why", "question",
        }
        def _collect_ids(obj: Any):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in ("text_id", "signal_id", "point_id", "id") and v:
                        allowed_ids.add(str(v))
                    _collect_ids(v)
            elif isinstance(obj, list):
                for v in obj:
                    _collect_ids(v)
        _collect_ids(payload)
        for fid in used:
            if str(fid) not in allowed_ids:
                errors.append(f"chat_unknown_fact_id:{fid}")
                break
    return list(dict.fromkeys(errors))


# Back-compat alias
def validate_overlay(prose: Any, facts: Any) -> list[str]:
    return validate_prose_against_facts(prose, facts)
