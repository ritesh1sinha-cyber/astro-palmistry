"""House × planet × age rubric validator — deterministic manifestation selection.

Sits between astrology evidence and language generation. Does NOT compute
planetary positions; validates and ranks manifestation candidates only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from interpretation.stage_config import (
    areas_for_house,
    conflict_group_for,
    default_manifestation,
    eligible_manifestations,
    house_manifestation_candidates,
    intersection_candidates,
    narrative_area_for,
    validate_age_manifestation,
)


PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
BANDS = ("child", "teen", "young_adult", "adult", "mature_adult", "senior")
DIRECTIONS = ("up", "mixed", "down", "supportive", "challenging")


@dataclass
class RubricInput:
    house: int = 0
    planet: str = ""
    age: int = 0
    age_band: str = "adult"
    area: str = "career"
    direction: str = "mixed"
    role: str = "dasha"
    strength: float = 0.5
    transit_active: bool = False
    transit_strength: float = 0.0
    divisional_support: str = "mixed"
    divisional_chart: str = ""
    dasha_planet: str = ""
    sub_dasha: str = ""
    area_candidates: list[str] = field(default_factory=list)
    recognition_tag: str = ""


@dataclass
class ManifestationScore:
    id: str
    score: int
    evidence: list[str] = field(default_factory=list)


@dataclass
class RubricResult:
    house: int = 0
    planet: str = ""
    age: int = 0
    age_band: str = "adult"
    life_area: str = "career"
    primary: Optional[ManifestationScore] = None
    secondary: Optional[ManifestationScore] = None
    caution: Optional[ManifestationScore] = None
    confidence: str = "low"
    allowed: bool = True
    evidence_trace: list[str] = field(default_factory=list)
    candidates: list[str] = field(default_factory=list)
    event_confidence: str = "moderate"

    @property
    def primary_id(self) -> str:
        return self.primary.id if self.primary else ""

    @property
    def secondary_id(self) -> str:
        return self.secondary.id if self.secondary else ""

    @property
    def caution_id(self) -> str:
        return self.caution.id if self.caution else ""

    def manifestation_list(self) -> list[str]:
        out = []
        if self.primary:
            out.append(self.primary.id)
        if self.secondary and self.secondary.id not in out:
            out.append(self.secondary.id)
        return out or ["responsibility"]


def _norm_direction(direction: str) -> str:
    d = (direction or "mixed").lower()
    if d in ("supportive", "up"):
        return "up"
    if d in ("challenging", "down"):
        return "down"
    return "mixed"


def _confidence_label(score: int) -> str:
    if score <= 4:
        return "reject"
    if score <= 8:
        return "low"
    if score <= 12:
        return "moderate"
    if score <= 16:
        return "strong"
    return "very_strong"


def _event_confidence_label(ranked: list[tuple[str, int]]) -> str:
    """How distinct the top manifestation is among close candidates."""
    if not ranked:
        return "low"
    top = ranked[0][1]
    if top <= 0:
        return "low"
    margin = max(2, top // 4)
    close = sum(1 for _, sc in ranked[:8] if top - sc <= margin)
    if close >= 4:
        return "low"
    if close >= 2:
        return "moderate"
    return "strong"


def _collect_candidates(inp: RubricInput) -> tuple[dict[str, int], dict[str, list[str]]]:
    """Score manifestation candidates from house/planet/age/evidence."""
    area = inp.area or "career"
    band = inp.age_band or "adult"
    narrative = narrative_area_for(area, band)
    house = int(inp.house or 10)
    planet = inp.planet or inp.dasha_planet or "Saturn"
    direction = _norm_direction(inp.direction)

    scores: dict[str, int] = {}
    trace: dict[str, list[str]] = {}

    def add(cls: str, pts: int, reason: str) -> None:
        gate = validate_age_manifestation(band, cls)
        if not gate["allowed"]:
            repl = gate.get("replacement")
            if repl:
                cls = repl
            else:
                return
        allowed = eligible_manifestations(band, narrative, area)
        if allowed and cls not in allowed:
            return
        from interpretation.stage_config import required_evidence_met
        if not required_evidence_met(
            cls, house, planet, direction=direction,
            recognition_tag=inp.recognition_tag,
        ):
            return
        scores[cls] = scores.get(cls, 0) + pts
        trace.setdefault(cls, []).append(reason)

    # Recognition-tag semantics are evidence, not discarded metadata.
    # The 108/manual rule that produced the tag is allowed to bias the
    # manifestation selector toward its intended modern meaning.
    TAG_MANIFESTATIONS: dict[str, tuple[str, ...]] = {
        "career_state": ("career_responsibility", "career"),
        "career_vouched": ("mentor_support", "support_from_contacts"),
        "career_head": ("analysis", "career_responsibility"),
        "career_charge": ("career_responsibility", "leadership"),
        "career_initiative": ("career_responsibility", "opportunity"),
        "career_reader": ("analysis", "visibility"),
        "career_early_recognition": ("recognition", "visibility"),
        "career_straight": ("career_advancement", "career_responsibility"),
        "career_detour": ("career_transition", "delayed_recognition"),
        "adhi_respected": ("authority", "recognition"),
        "adhi_struggle": ("career_responsibility", "delayed_reward"),
        "money_earn": ("income", "financial_progress"),
        "money_hold": ("savings", "financial_retention"),
        "self_made": ("income", "career_responsibility"),
        "money_lord_exchange": ("financial_progress", "gains"),
        "money_rahu_11": ("gains", "network_gain"),
        "money_saturn_2": ("financial_retention", "resource_discipline"),
        "money_tight": ("resource_discipline", "financial_stability"),
        "money_jupiter_wealth": ("gains", "financial_progress"),
        "money_mercury_earn": ("income", "financial_progress"),
        "money_sav_earn_hold": ("income", "financial_retention"),
        "money_sav_hold": ("savings", "financial_retention"),
        "money_fought_for": ("income", "competition"),
        "money_started_behind": ("financial_progress", "delayed_reward"),
        "money_loss_absorbed": ("financial_stability", "financial_retention"),
        "money_floor": ("financial_stability", "family_finances"),
        "love_delayed": ("commitment", "distance"),
        "love_hot": ("commitment", "conflict"),
        "love_lord_dusthana": ("commitment", "distance"),
        "love_venus_debilitated": ("relationship_bond", "expectation_management"),
        "love_venus_strong": ("harmony", "commitment"),
        "love_saturn_7": ("commitment", "distance"),
        "love_mars_7": ("conflict", "communication"),
        "health_outlasts": ("energy_management", "wellbeing"),
        "health_hard": ("stress_management", "routine"),
        "health_saturn_6": ("routine", "stress_management"),
        "health_mars_6": ("energy_management", "stress_management"),
        "health_node_6": ("stress_management", "routine"),
        "health_moon_gut": ("routine", "wellbeing"),
        "health_sun_vitals": ("energy_management", "wellbeing"),
        "health_jupiter_weight": ("routine", "energy_management"),
        "health_sav_6": ("routine", "preventive_attention"),
        "health_lagna_weak": ("energy_management", "routine"),
        "health_lagna_strong": ("wellbeing", "energy_management"),
        "parents_sun_weak": ("family_responsibility", "domestic_stability"),
        "parents_sun_strong": ("family_support", "domestic_stability"),
        "parents_moon_4": ("domestic_stability", "emotional_security"),
        "parents_4th_dusthana": ("family_responsibility", "domestic_stability"),
        "parents_9th_dusthana": ("family_responsibility", "father_influence"),
        "parents_saturn_early": ("family_responsibility", "responsibility"),
        "parents_sav_4": ("domestic_stability", "emotional_security"),
    }
    tag_candidates = TAG_MANIFESTATIONS.get(inp.recognition_tag, ())
    if inp.recognition_tag:
        for cls in tag_candidates:
            add(cls, 20, f"recognition_tag_{inp.recognition_tag}")

    # House × band config (dense for major houses)
    if area in ("career", "education", "early_career", "money", "love"):
        try:
            primary_cfg, secondary_cfg, default_cls = house_manifestation_candidates(
                area if area in ("career", "money", "love") else "career",
                house,
                band,
            )
            for i, cls in enumerate(primary_cfg):
                add(cls, 5 if i == 0 else 3, f"{house}th_house_primary")
            for cls in secondary_cfg:
                add(cls, 2, f"{house}th_house_secondary")
            if default_cls:
                add(default_cls, 1, f"{house}th_house_default")
        except Exception:  # noqa: BLE001
            pass

    if band == "teen" and area in ("career", "education", "early_career"):
        for cls in ("study_progress", "teacher_recognition", "concentration", "academic_responsibility"):
            add(cls, 8, "teen_career_age_gate")
    elif band == "young_adult" and area in ("career", "education", "early_career"):
        for cls in ("visibility", "skill_development", "early_career_direction", "internship"):
            add(cls, 8, "young_adult_career_age_gate")

    # House base taxonomy
    for cls in intersection_candidates(house, planet)[:8]:
        add(cls, 2, f"house_{house}_planet_{planet}")

    # Planet role
    if planet:
        from interpretation.stage_config import planet_candidates
        for cls in planet_candidates(planet)[:5]:
            add(cls, 2, f"planet_{planet}")

    # Dasha / transit / divisional weights
    if inp.dasha_planet == planet or inp.role == "dasha":
        for cls in intersection_candidates(house, inp.dasha_planet or planet)[:3]:
            add(cls, 3, f"dasha_{inp.dasha_planet or planet}")
    transit_planet = planet
    if inp.transit_active and inp.planet and inp.dasha_planet and inp.planet != inp.dasha_planet:
        transit_planet = inp.planet
        for cls in intersection_candidates(house, transit_planet)[:4]:
            add(cls, 3, f"transit_{transit_planet}")
    elif inp.transit_active:
        for cls in intersection_candidates(house, planet)[:2]:
            add(cls, 2, "transit_active")
    div = (inp.divisional_support or "").lower()
    if div in ("strong", "positive", "excellent"):
        from interpretation.stage_config import house_planet_rules
        rule = house_planet_rules().get(f"{house}:{planet}") or {}
        for cls in (rule.get("boost") or [])[:4]:
            add(cls, 3, f"divisional_{inp.divisional_chart or 'support'}")
        for cls in list(scores):
            scores[cls] = scores.get(cls, 0) + 1
            trace.setdefault(cls, []).append(f"divisional_{inp.divisional_chart or 'support'}")

    # Age band exact match
    for cls in list(scores):
        scores[cls] = scores[cls] + 3
        trace.setdefault(cls, []).append(f"age_band_{band}")

    # Direction modifiers
    if direction == "up":
        for cls in ("recognition", "opportunity", "visibility", "gains", "study_progress"):
            add(cls, 2, "direction_up")
    elif direction == "down":
        for cls in ("competition", "distance", "stress_management", "delayed_reward"):
            add(cls, 2, "direction_down")
    else:
        for cls in ("responsibility", "communication", "mixed_signal"):
            add(cls, 1, "direction_mixed")

    if not scores:
        default = default_manifestation(band, narrative, area)
        add(default, 5, "band_safe_default")

    # A named recognition rule is already a semantic statement from the
    # upstream astrology layer. Do not let generic house/planet candidates
    # erase that semantic identity. Keep other candidates available for a
    # genuine secondary meaning, but make the tag-derived candidates primary.
    if tag_candidates:
        mapped = {mid: scores.get(mid, 0) for mid in tag_candidates if mid in scores}
        if mapped:
            floor = max(mapped.values())
            for cls in list(scores):
                if cls not in mapped:
                    scores[cls] = min(scores[cls], floor - 1)

    return scores, trace  # type: ignore[return-value]


def _pick_non_conflicting(
    ranked: list[tuple[str, int]],
    trace: dict[str, list[str]],
    max_items: int = 2,
) -> list[ManifestationScore]:
    picked: list[ManifestationScore] = []
    used_groups: set[str] = set()
    for cls, sc in ranked:
        if len(picked) >= max_items:
            break
        grp = conflict_group_for(cls)
        if grp and grp in used_groups:
            continue
        if grp:
            used_groups.add(grp)
        picked.append(ManifestationScore(id=cls, score=sc, evidence=trace.get(cls, [])))
    return picked


def validate_rubric(inp: RubricInput) -> RubricResult:
    """Main entry — house/planet/age rubric validation and ranking."""
    area = inp.area or "career"
    band = inp.age_band or "adult"
    house = int(inp.house or 10)
    planet = inp.planet or inp.dasha_planet or ""

    scores, trace = _collect_candidates(inp)
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))

    picked = _pick_non_conflicting(ranked, trace, max_items=2)
    primary = picked[0] if picked else ManifestationScore(
        id=default_manifestation(band, narrative_area_for(area, band), area),
        score=5,
        evidence=["fallback"],
    )
    secondary = picked[1] if len(picked) > 1 else None

    # Caution from intersection rules or direction
    caution_id = ""
    caution_score = 0
    if planet and house:
        from interpretation.stage_config import house_planet_rules
        rule = house_planet_rules().get(f"{house}:{planet}") or {}
        caution_id = str(rule.get("caution") or "")
    if not caution_id and _norm_direction(inp.direction) == "mixed":
        caution_id = "mixed_signal"
    if not caution_id and "delayed_reward" in scores:
        from interpretation.stage_config import required_evidence_met
        if required_evidence_met(
            "delayed_recognition", house, planet,
            direction=inp.direction, recognition_tag=inp.recognition_tag,
        ):
            caution_id = "delayed_recognition"
    caution = (
        ManifestationScore(id=caution_id, score=caution_score, evidence=["caution"])
        if caution_id else None
    )

    conf = _confidence_label(primary.score)
    evidence_trace = [
        f"{house}th house",
        planet or "unknown_planet",
        f"{band} age band",
    ]
    if inp.dasha_planet:
        evidence_trace.append(f"{inp.dasha_planet} timing")
    if inp.divisional_chart:
        evidence_trace.append(f"{inp.divisional_chart} support")
    evidence_trace.extend(primary.evidence[:3])

    eligible_areas = inp.area_candidates or areas_for_house(house)

    return RubricResult(
        house=house,
        planet=planet,
        age=inp.age,
        age_band=band,
        life_area=area,
        primary=primary,
        secondary=secondary,
        caution=caution,
        confidence=conf if conf != "reject" else "low",
        allowed=conf != "reject",
        evidence_trace=evidence_trace,
        candidates=[c for c, _ in ranked[:8]],
        event_confidence=_event_confidence_label(ranked),
    )


def rubric_from_evidence(evidence: Any) -> RubricResult:
    """Build rubric input from an EvidenceBundle."""
    div = getattr(evidence, "divisional_support", "mixed") or "mixed"
    strength_map = {"strong": 0.85, "positive": 0.75, "mixed": 0.5, "weak": 0.3}
    return validate_rubric(RubricInput(
        house=int(getattr(evidence, "transit_house", 0) or getattr(evidence, "birth_house", 0) or 10),
        planet=str(getattr(evidence, "transit_planet", "") or getattr(evidence, "primary_dasha", "")),
        age=int(getattr(evidence, "age_at_period", 0) or 0),
        age_band=str(getattr(evidence, "age_band", "adult")),
        area=str(getattr(evidence, "area", "career")),
        direction=str(getattr(evidence, "direction", "mixed")),
        dasha_planet=str(getattr(evidence, "primary_dasha", "")),
        sub_dasha=str(getattr(evidence, "sub_dasha", "")),
        transit_active=bool(getattr(evidence, "transit_planet", "")),
        transit_strength=0.6 if getattr(evidence, "transit_planet", "") else 0.0,
        divisional_support=str(div),
        divisional_chart=str(getattr(evidence, "divisional_chart", "")),
        strength=strength_map.get(str(div).lower(), 0.5),
        recognition_tag=str(getattr(evidence, "recognition_tag", "") or ""),
    ))


def rubric_for_recognition(
    *,
    domain: str,
    house: int,
    planet: str,
    band: str,
    age: int = 0,
    tag: str = "",
) -> RubricResult:
    """Recognition-specific rubric — map domain tag to house/planet."""
    area_map = {
        "money": "money",
        "love": "love",
        "career": "career",
        "health": "health",
        "parents": "home",
    }
    area = area_map.get(domain, domain)
    # Infer house from domain when not supplied
    default_houses = {
        "money": 2,
        "love": 7,
        "career": 10,
        "health": 6,
        "home": 4,
        "parents": 4,
    }
    h = house or default_houses.get(area, 10)
    return validate_rubric(RubricInput(
        house=h,
        planet=planet or "Saturn",
        age=age,
        age_band=band,
        area=area,
        direction="mixed",
        recognition_tag=tag,
    ))
