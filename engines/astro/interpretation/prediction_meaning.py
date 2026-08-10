"""PredictionMeaning — semantic intent before human language."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from interpretation.evidence_builder import EvidenceBundle

from interpretation.manifestation_rules import (
    caution_from_evidence, score_manifestations, top_manifestations,
)


@dataclass
class PredictionMeaning:
    area: str
    direction: str
    age_band: str
    manifestations: list[str] = field(default_factory=list)
    caution: str = ""
    narrative_area: str = ""
    evidence_signature: tuple = field(default_factory=tuple)
    variant_index: int = 0
    age_at_period: int = 0
    transit_house: int = 0
    intensity: str = "moderate"
    claim_level: int = 2
    personalized_claim: bool = True
    confidence: str = "moderate"
    timing_confidence: str = ""
    event_confidence: str = ""
    evidence_trace: list[str] = field(default_factory=list)
    specificity_score: int = 0
    source_engine: str = "manifestation_engine"
    evidence_sources: list[tuple] = field(default_factory=list)
    modern_meaning: str = ""

    @property
    def primary(self) -> str:
        return self.manifestations[0] if self.manifestations else ""

    @property
    def secondary(self) -> str:
        return self.manifestations[1] if len(self.manifestations) > 1 else ""

    def bump_variant(self) -> "PredictionMeaning":
        return PredictionMeaning(
            area=self.area,
            direction=self.direction,
            age_band=self.age_band,
            manifestations=list(self.manifestations),
            caution=self.caution,
            narrative_area=self.narrative_area,
            evidence_signature=self.evidence_signature,
            variant_index=self.variant_index + 1,
            age_at_period=self.age_at_period,
            transit_house=self.transit_house,
            intensity=self.intensity,
            claim_level=self.claim_level,
            personalized_claim=self.personalized_claim,
            confidence=self.confidence,
            timing_confidence=self.timing_confidence,
            event_confidence=self.event_confidence,
            evidence_trace=list(self.evidence_trace),
            specificity_score=self.specificity_score,
            source_engine=self.source_engine,
            evidence_sources=list(self.evidence_sources),
            modern_meaning=self.modern_meaning,
        )


def build_meaning(evidence: "EvidenceBundle") -> PredictionMeaning:
    from interpretation.life_stage import narrative_area as _narr_area

    scores = score_manifestations(evidence)
    manifestations = top_manifestations(scores, max_items=2)
    confidence = "moderate"
    timing_confidence = "moderate"
    event_confidence = "moderate"
    evidence_trace: list[str] = []

    try:
        from interpretation.rubric_validator import rubric_from_evidence
        rubric = rubric_from_evidence(evidence)
        if rubric.primary_id:
            manifestations = rubric.manifestation_list()
        confidence = rubric.confidence or confidence
        timing_confidence = confidence
        event_confidence = getattr(rubric, "event_confidence", "") or "moderate"
        evidence_trace = list(rubric.evidence_trace or [])
    except Exception:  # noqa: BLE001
        pass

    evidence.manifestation_candidates = list(scores.keys())
    caution = caution_from_evidence(evidence, manifestations)
    try:
        from interpretation.rubric_validator import rubric_from_evidence
        rubric = rubric_from_evidence(evidence)
        if rubric.caution_id:
            caution = rubric.caution_id
    except Exception:  # noqa: BLE001
        pass

    from qa_checks.claim_validator import default_claim_level
    try:
        from interpretation.stage_config import manifestation_metadata
        modern_meaning = manifestation_metadata(manifestations[0]).get("modern_meaning", "") if manifestations else ""
    except Exception:
        modern_meaning = ""
    return PredictionMeaning(
        area=evidence.area,
        direction=evidence.direction,
        age_band=evidence.age_band,
        manifestations=manifestations,
        caution=caution,
        narrative_area=_narr_area(evidence.area, evidence.age_band),
        evidence_signature=evidence.signature(),
        age_at_period=evidence.age_at_period,
        transit_house=evidence.transit_house,
        intensity=evidence.confidence or "moderate",
        claim_level=default_claim_level("recognition"),
        personalized_claim=True,
        confidence=confidence,
        timing_confidence=timing_confidence,
        event_confidence=event_confidence,
        evidence_trace=evidence_trace,
        specificity_score=0,
        source_engine="manifestation_engine",
        evidence_sources=[evidence.signature()],
        modern_meaning=modern_meaning,
    )


def build_recognition_meaning(
    domain: str,
    tag: str,
    band: str,
    *,
    pc: Optional[dict] = None,
    house: Optional[int] = None,
    planet: Optional[str] = None,
) -> Optional[PredictionMeaning]:
    """Build PredictionMeaning for a recognition tag — rubric-only path."""
    from interpretation.life_stage import age_band as _age_band, narrative_area as _narr_area
    from interpretation.rubric_validator import rubric_for_recognition
    from narration.recognition_variants import TAG_EVIDENCE, _DOMAIN_DEFAULTS, tag_evidence_house_planet

    area_map = {
        "money": "money",
        "love": "love",
        "career": "career",
        "health": "health",
        "parents": "home",
    }
    area = area_map.get(domain, domain)
    if not band and pc:
        band = _age_band(pc)

    default_house, default_planet = _DOMAIN_DEFAULTS.get(domain, _DOMAIN_DEFAULTS.get(area, (10, "Saturn")))
    resolved_house = default_house
    resolved_planet = default_planet

    if house and planet:
        resolved_house, resolved_planet = int(house), planet
    elif tag == "floor":
        floor_tags = {
            "money": ("money", 2, "Saturn"),
            "love": ("love", 7, "Venus"),
            "career": ("career", 10, "Saturn"),
            "health": ("health", 6, "Mars"),
            "home": ("parents", 4, "Moon"),
            "parents": ("parents", 4, "Moon"),
        }
        ft = floor_tags.get(area, floor_tags.get(domain, ("career", 10, "Saturn")))
        domain, resolved_house, resolved_planet = ft[0], ft[1], ft[2]
    elif tag in TAG_EVIDENCE:
        _, resolved_house, resolved_planet = TAG_EVIDENCE[tag]
    else:
        ev = tag_evidence_house_planet(tag)
        if ev:
            resolved_house, resolved_planet = ev

    rubric = rubric_for_recognition(
        domain=domain,
        house=resolved_house,
        planet=resolved_planet,
        band=band,
        tag=tag,
    )
    if not rubric.primary_id:
        return None

    from qa_checks.claim_validator import default_claim_level
    return PredictionMeaning(
        area=area,
        direction="mixed",
        age_band=band,
        manifestations=rubric.manifestation_list(),
        caution=rubric.caution_id or "",
        narrative_area=_narr_area(area, band),
        evidence_signature=(domain, tag, band, rubric.primary_id, rubric.secondary_id, resolved_house, resolved_planet),
        transit_house=resolved_house,
        claim_level=default_claim_level("recognition"),
        personalized_claim=bool(rubric.evidence_trace),
        confidence=rubric.confidence or "moderate",
        timing_confidence=rubric.confidence or "moderate",
        event_confidence=getattr(rubric, "event_confidence", "") or "moderate",
        evidence_trace=list(rubric.evidence_trace or []),
        specificity_score=0,
        source_engine="manifestation_engine",
        evidence_sources=[(domain, tag, band, resolved_house, resolved_planet)],
        modern_meaning=(
            __import__("interpretation.stage_config", fromlist=["manifestation_metadata"])
            .manifestation_metadata(rubric.primary_id).get("modern_meaning", "")
            if rubric.primary_id else ""
        ),
    )
