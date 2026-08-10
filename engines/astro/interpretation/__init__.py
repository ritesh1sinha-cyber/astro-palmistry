"""Evidence-first interpretation layer — no customer-facing prose here."""

from interpretation.life_stage import (
    age_band, age_band_at, age_years, get_age_band, is_minor, is_pre_adult,
)
from interpretation.evidence_builder import EvidenceBundle, build_evidence
from interpretation.manifestation_rules import score_manifestations, top_manifestations
from interpretation.prediction_meaning import PredictionMeaning, build_meaning

__all__ = [
    "EvidenceBundle",
    "PredictionMeaning",
    "age_band",
    "age_band_at",
    "age_years",
    "build_evidence",
    "build_meaning",
    "get_age_band",
    "is_minor",
    "is_pre_adult",
    "score_manifestations",
    "top_manifestations",
]
