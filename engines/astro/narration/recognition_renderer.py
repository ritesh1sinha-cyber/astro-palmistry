"""Age-band recognition — rubric → PredictionMeaning → claim-validated prose only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from qa_checks.age_context_check import age_violations
from qa_checks.claim_validator import legacy_archetype_banned, validate_claim
from qa_checks.health_safety_check import health_violations

if TYPE_CHECKING:
    from interpretation.prediction_meaning import PredictionMeaning

_DOMAIN_HOUSE = {"health": 6, "money": 2, "love": 7, "parents": 4, "career": 10}


def _qa_gate(text: str, band: str) -> bool:
    if not text:
        return False
    if legacy_archetype_banned(text):
        return False
    if age_violations(text, band):
        return False
    if health_violations(text):
        return False
    return True


def build_meaning_for_tag(
    domain: str,
    tag: str,
    band: str,
    *,
    pc: Optional[dict] = None,
    house: Optional[int] = None,
    planet: Optional[str] = None,
) -> Optional["PredictionMeaning"]:
    from interpretation.prediction_meaning import build_recognition_meaning
    return build_recognition_meaning(
        domain, tag, band, pc=pc, house=house, planet=planet,
    )


def render_from_meaning(
    meaning: "PredictionMeaning",
    *,
    variant_index: int = 0,
    seen_texts: Optional[set] = None,
) -> Optional[str]:
    """Render claim text from PredictionMeaning; claim-validated; no legacy fallback."""
    from narration.recognition_variants import claim_for_manifestation

    seen = seen_texts or set()
    for attempt in range(4):
        idx = variant_index + attempt
        text = claim_for_manifestation(
            meaning.primary,
            meaning.secondary,
            meaning.age_band,
            variant_index=idx,
            narrative_area=getattr(meaning, "narrative_area", "") or getattr(meaning, "area", ""),
        )
        if not text or text in seen:
            continue
        if not _qa_gate(text, meaning.age_band):
            continue
        v = validate_claim(text, meaning, section="recognition")
        if not v["allowed"]:
            text = v.get("replacement")
            if not text or not _qa_gate(text, meaning.age_band):
                continue
            v = validate_claim(text, meaning, section="recognition")
            if not v["allowed"]:
                continue
        if text in seen:
            continue
        return text
    return None


def recognition_bullets(meaning: "PredictionMeaning") -> list[str]:
    from narration.recognition_variants import bullets_for_meaning
    return bullets_for_meaning(meaning)


def render_recognition_claim(
    domain: str,
    tag: str,
    band: str,
    adult_text: str,
    *,
    variant_index: int = 0,
    seen_texts: Optional[set] = None,
    pc: Optional[dict] = None,
    house: Optional[int] = None,
    planet: Optional[str] = None,
) -> Optional[str]:
    """Return age-appropriate claim — rubric/meaning path only; never legacy adult prose."""
    meaning = build_meaning_for_tag(
        domain, tag or "floor", band, pc=pc, house=house, planet=planet,
    )
    if not meaning:
        return None
    return render_from_meaning(
        meaning,
        variant_index=variant_index,
        seen_texts=seen_texts,
    )


def recognition_domain_label(domain: str, band: str) -> str:
    from narration.area_labels import area_label
    area_map = {
        "money": "money",
        "love": "love",
        "career": "career",
        "health": "health",
        "parents": "home",
    }
    area = area_map.get(domain, domain)
    labels = {
        "health": {"child": "Your health", "teen": "Your health", "young_adult": "Your health",
                   "adult": "Your health", "mature_adult": "Your health", "senior": "Your health"},
        "money": {"child": "Resources & habits", "teen": "Resources & money habits",
                  "young_adult": "Money & independence", "adult": "Money, historically",
                  "mature_adult": "Money, historically", "senior": "Money & preservation"},
        "love": {"child": "Friendships & close bonds", "teen": "Friendships & close bonds",
                 "young_adult": "Relationships", "adult": "How you are in love",
                 "mature_adult": "How you are in love", "senior": "Companionship & bonds"},
        "career": {"child": "Studies & recognition", "teen": "Studies & recognition",
                   "young_adult": "Education & early direction", "adult": "Your work",
                   "mature_adult": "Your work", "senior": "Legacy & mentoring"},
        "parents": {"child": "Your family", "teen": "Your family", "young_adult": "Your family",
                    "adult": "Your parents", "mature_adult": "Your parents", "senior": "Your family"},
    }
    return labels.get(domain, {}).get(band) or area_label(area, band)
