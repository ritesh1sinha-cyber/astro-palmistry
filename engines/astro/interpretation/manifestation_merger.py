"""Merge redundant recognition manifestations within a life-area block."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from interpretation.prediction_meaning import PredictionMeaning

_DOMAIN_AREA = {
    "money": "money",
    "love": "love",
    "career": "career",
    "health": "health",
    "parents": "home",
}


def domain_matches_meaning(domain: str, meaning: "PredictionMeaning") -> bool:
    """Life-area validator — meaning must belong to the rendered domain."""
    expected = _DOMAIN_AREA.get(domain, domain)
    area = (meaning.area or "").lower()
    if area == expected:
        return True
    if domain == "parents" and area in ("home", "parents"):
        return True
    return False


def family_set_for_meaning(meaning: "PredictionMeaning") -> frozenset[str]:
    """Return context-aware semantic/cohesion groups for this meaning.

    The old implementation used only global manifestation families. That
    allowed two different wellbeing manifestations with different evidence
    to survive as separate claims, and it also treated career recognition and
    responsibility as independent when they were really one progression story.
    Cohesion is now life-area aware.
    """
    from interpretation.stage_config import cohesion_groups_for_manifestations

    ids = list(meaning.manifestations or [])
    if meaning.caution:
        ids.append(meaning.caution)
    area = getattr(meaning, "narrative_area", "") or getattr(meaning, "area", "")
    return cohesion_groups_for_manifestations(area, *ids)


def evidence_source_key(meaning: "PredictionMeaning", tag: str) -> tuple:
    sig = meaning.evidence_signature or ()
    house = meaning.transit_house or 0
    if len(sig) >= 7:
        return (sig[5], sig[6], sig[0], sig[1], sig[3], sig[4])
    if len(sig) >= 5:
        return (house, sig[0], sig[1], sig[3], sig[4])
    return (house, tag, meaning.primary, meaning.secondary)


def has_independent_evidence(
    meaning: "PredictionMeaning",
    tag: str,
    kept: list[dict[str, Any]],
) -> bool:
    key = evidence_source_key(meaning, tag)
    for item in kept:
        other = item.get("meaning")
        if not other:
            continue
        if evidence_source_key(other, item.get("tag", "")) == key:
            return False
    return True


def merge_two_meanings(
    base: "PredictionMeaning",
    extra: "PredictionMeaning",
) -> "PredictionMeaning":
    """Combine manifestations, traces, and cautions from two related meanings."""
    from interpretation.prediction_meaning import PredictionMeaning

    mans: list[str] = []
    for mid in list(base.manifestations or []) + list(extra.manifestations or []):
        if mid and mid not in mans:
            mans.append(mid)
    trace: list[str] = []
    for line in list(base.evidence_trace or []) + list(extra.evidence_trace or []):
        if line and line not in trace:
            trace.append(line)
    caution = base.caution or extra.caution
    if base.caution and extra.caution and base.caution != extra.caution:
        from interpretation.stage_config import family_for
        if family_for(base.caution) != family_for(extra.caution):
            caution = base.caution
    return PredictionMeaning(
        area=base.area,
        direction=base.direction,
        age_band=base.age_band,
        manifestations=mans[:3],
        caution=caution,
        narrative_area=base.narrative_area,
        evidence_signature=base.evidence_signature or extra.evidence_signature,
        variant_index=base.variant_index,
        age_at_period=base.age_at_period,
        transit_house=base.transit_house or extra.transit_house,
        intensity=base.intensity,
        claim_level=base.claim_level,
        personalized_claim=base.personalized_claim,
        confidence=base.confidence,
        timing_confidence=getattr(base, "timing_confidence", "") or getattr(extra, "timing_confidence", ""),
        event_confidence=getattr(base, "event_confidence", "") or getattr(extra, "event_confidence", ""),
        evidence_trace=trace[:6],
        specificity_score=max(base.specificity_score, extra.specificity_score),
        source_engine="manifestation_engine",
        evidence_sources=list(dict.fromkeys(
            list(getattr(base, "evidence_sources", []) or [])
            + list(getattr(extra, "evidence_sources", []) or [])
        )),
        modern_meaning="; ".join(
            x for x in [getattr(base, "modern_meaning", ""), getattr(extra, "modern_meaning", "")]
            if x
        ),
    )


def merge_recognition_candidates(
    candidates: list[dict[str, Any]],
    *,
    domain: str,
    band: str,
    render_from_meaning,
    recognition_bullets,
    seen_text: set[str],
    max_claims: int = 2,
) -> list[tuple[str, str, list[str]]]:
    """Collapse same-family meanings; allow at most one independent second family."""
    kept: list[dict[str, Any]] = []

    for cand in candidates:
        meaning: Optional["PredictionMeaning"] = cand.get("meaning")
        if not meaning:
            continue
        if not domain_matches_meaning(domain, meaning):
            continue

        families = family_set_for_meaning(meaning)
        merged_target = None
        for item in kept:
            item_families = family_set_for_meaning(item["meaning"])
            if not (families & item_families):
                continue
            # If two meanings belong to the same context-aware cohesion group,
            # they describe one user-facing story even when their technical
            # evidence comes from different witnesses. Combine the evidence;
            # do NOT print two versions of the same life pattern.
            #
            # Different cohesion groups may coexist, but only when their
            # evidence is genuinely independent.
            merged_target = item
            break

        if merged_target is not None:
            merged = merge_two_meanings(merged_target["meaning"], meaning)
            rendered = render_from_meaning(merged, seen_texts=seen_text)
            if rendered:
                merged_target["meaning"] = merged
                merged_target["rendered"] = rendered
                merged_target["bullets"] = recognition_bullets(merged)
                if cand.get("why") and not merged_target.get("why"):
                    merged_target["why"] = cand["why"]
            continue

        if len(kept) >= max_claims:
            continue
        if kept and not has_independent_evidence(meaning, cand.get("tag", ""), kept):
            continue
        if kept:
            existing_families = family_set_for_meaning(kept[0]["meaning"])
            if not (families - existing_families):
                continue

        kept.append(dict(cand))

    out: list[tuple[str, str, list[str]]] = []
    for item in kept[:max_claims]:
        rendered = item.get("rendered") or ""
        if not rendered or rendered in seen_text:
            continue
        seen_text.add(rendered)
        out.append((
            rendered,
            item.get("why") or "",
            list(item.get("bullets") or [])[:3],
        ))
    return out
