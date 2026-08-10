"""Evidence-weighted manifestation class selection.

Scorer uses transit house / dasha / divisional cues already present on the
evidence bundle — no new astrology math.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from interpretation.evidence_builder import EvidenceBundle

from interpretation.life_stage import (
    filter_scores_for_stage, is_minor, narrative_area,
)

# Manifestation classes per narrative domain.
AREA_CLASSES: dict[str, tuple[str, ...]] = {
    "career": (
        "visibility", "responsibility", "recognition", "delayed_reward",
        "mentor_support", "competition", "career_transition",
        "network_gain", "opportunity", "authority", "leadership",
        "support_from_contacts", "gains",
    ),
    "early_career": (
        "visibility", "responsibility", "recognition", "delayed_reward",
        "mentor_support", "network_gain", "opportunity", "skill_development",
        "study_progress", "competition",
    ),
    "education": (
        "teacher_recognition", "responsibility", "study_progress",
        "mentor_support", "effort", "concentration", "projects", "leadership",
    ),
    "money": (
        "income", "expense", "cash_flow", "savings", "paperwork",
        "financial_stability", "opportunity",
    ),
    "resources": (
        "allowance", "family_finances", "savings_habits", "resource_habits",
    ),
    "love": (
        "communication", "reconnection", "commitment", "expectation_management",
        "distance", "emotional_support",
    ),
    "friendships": (
        "communication", "emotional_support", "distance", "reconnection",
        "expectation_management",
    ),
    "home": (
        "family_responsibility", "property", "living_arrangement",
        "household_routine", "domestic_stability",
    ),
    "children": (
        "creativity", "parenting", "projects", "patience",
    ),
    "creativity": (
        "projects", "creativity", "patience", "mentor_support",
    ),
    "health": (
        "routine", "rest", "stress_management", "energy_management",
        "preventive_attention", "follow_up",
    ),
    "learning": (
        "study", "teacher_support", "skill_development", "concentration",
        "communication", "higher_education",
    ),
    "inner": (
        "rest", "space", "priorities", "withdrawal", "reflection",
    ),
}

# Pairs that should not co-appear unless mixed direction.
CONFLICTS: set[frozenset[str]] = {
    frozenset({"promotion", "career_exit"}),
    frozenset({"effortless_growth", "delayed_reward"}),
    frozenset({"commitment", "distance"}),
    frozenset({"network_gain", "visibility"}),  # prefer one primary house theme
}


def score_manifestations(evidence: "EvidenceBundle") -> dict[str, int]:
    """Weighted scores from evidence — rubric-first, then evidence bumps."""
    domain = narrative_area(evidence.area, evidence.age_band)
    scores: dict[str, int] = {}
    allowed = AREA_CLASSES.get(domain) or AREA_CLASSES.get(evidence.area, ())

    def bump(cls: str, n: int = 1) -> None:
        if cls in allowed:
            scores[cls] = scores.get(cls, 0) + n

    # Rubric validator — primary scoring path
    try:
        from interpretation.rubric_validator import rubric_from_evidence
        rubric = rubric_from_evidence(evidence)
        for rank, cls in enumerate(rubric.candidates[:6]):
            bump(cls, max(6 - rank, 1))
        for cls in rubric.manifestation_list():
            bump(cls, 4)
        if rubric.caution_id:
            bump(rubric.caution_id, 1)
    except Exception:  # noqa: BLE001
        pass

    direction = evidence.direction
    th = int(evidence.transit_house or evidence.birth_house or 0)
    planet = evidence.transit_planet
    factors = " ".join(evidence.support_factors + evidence.pressure_factors)

    if domain in ("career", "education", "early_career"):
        # 10th vs 11th must diverge — do NOT treat "area==career" as house 10.
        try:
            from interpretation.stage_config import house_manifestation_candidates
            primary_cfg, secondary_cfg, default_cls = house_manifestation_candidates(
                evidence.area if evidence.area == "career" else "career",
                th or evidence.birth_house or 10,
                evidence.age_band,
            )
            for cls in primary_cfg:
                bump(cls, 3)
            for cls in secondary_cfg:
                bump(cls, 2)
            if not scores and default_cls:
                bump(default_cls, 1)
        except Exception:  # noqa: BLE001
            pass
        if th == 10:
            bump("visibility", 3)
            bump("responsibility", 3)
            bump("authority", 2)
            bump("leadership", 1)
            bump("recognition", 1)
        elif th == 11:
            bump("network_gain", 3)
            bump("opportunity", 3)
            bump("gains", 2)
            bump("support_from_contacts", 2)
        elif evidence.area == "career":
            # Unknown house — mild generic career cues only
            bump("responsibility", 1)
            bump("visibility", 1)

        if "Jupiter" in factors or planet == "Jupiter" or evidence.primary_dasha == "Jupiter":
            bump("mentor_support", 2)
            bump("teacher_recognition", 2)
            bump("opportunity", 1)
        if ("Saturn" in factors
                or evidence.primary_dasha == "Saturn"
                or evidence.sub_dasha == "Saturn"):
            bump("delayed_reward", 2)

        if direction == "up":
            if th == 11:
                bump("opportunity", 2)
                bump("gains", 1)
            else:
                bump("recognition", 2)
                bump("study_progress", 2)
        if direction == "down":
            bump("competition", 2)
        if direction == "mixed":
            bump("delayed_reward", 1)
            bump("responsibility", 1)

        if domain == "education":
            # Prefer school language over career leadership
            scores.pop("authority", None)
            scores.pop("competition", None)

    elif domain in ("love", "friendships"):
        if direction == "up":
            bump("reconnection", 2)
            bump("emotional_support", 1)
        elif direction == "down":
            bump("distance", 2)
        else:
            bump("communication", 2)
            bump("expectation_management", 1)

    elif domain in ("money", "resources"):
        if domain == "resources":
            bump("resource_habits", 2)
            bump("family_finances", 1)
        elif direction == "up":
            bump("income", 2)
            bump("financial_stability", 1)
        elif direction == "down":
            bump("expense", 2)
            bump("cash_flow", 1)
        else:
            bump("cash_flow", 2)
            bump("paperwork", 1)

    elif evidence.area == "health":
        # Do not manufacture a generic wellbeing pattern for every chart.
        # Health manifestations must be tied to an actual health-relevant
        # house/timing witness. The old unconditional routine/rest bumps were
        # the main source of repeated "consistent routines" claims.
        health_house = th in (1, 6, 8, 12)
        if health_house:
            bump("routine", 2)
            bump("energy_management", 1)
        if th in (8, 12):
            bump("rest", 2)
        if direction == "down" and health_house:
            bump("stress_management", 2)
        elif health_house:
            bump("preventive_attention", 1)

    elif evidence.area == "learning":
        bump("study", 2)
        bump("teacher_support", 1)
        if direction == "up":
            bump("skill_development", 2)

    elif evidence.area == "home":
        bump("family_responsibility", 2)
        if direction == "mixed":
            bump("household_routine", 1)

    elif evidence.area == "inner":
        bump("space", 2)
        bump("priorities", 1)
        if th == 12:
            bump("withdrawal", 1)

    elif evidence.area == "children":
        bump("patience", 1)
        if is_minor(evidence.age_band):
            bump("projects", 2)
        else:
            bump("parenting", 2)

    if evidence.divisional_support in ("strong", "positive"):
        for cls in list(scores):
            scores[cls] = scores[cls] + 1
        if th == 10:
            bump("recognition", 1)

    scores = filter_scores_for_stage(
        scores, area=evidence.area, age_band=evidence.age_band, narrative=domain)

    if not scores:
        fallback = {
            "up": "study_progress" if domain == "education" else (
                "opportunity" if th == 11 else "recognition"),
            "down": "competition" if domain in ("career", "early_career") else "distance",
            "mixed": "responsibility",
        }
        fb = fallback.get(direction, "responsibility")
        if fb in allowed:
            scores[fb] = 1

    return scores


def top_manifestations(scores: dict[str, int], *, max_items: int = 2) -> list[str]:
    """Return top non-conflicting manifestation classes."""
    if not scores:
        return ["responsibility"]
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    picked: list[str] = []
    for cls, _ in ranked:
        if len(picked) >= max_items:
            break
        if any(frozenset({cls, p}) in CONFLICTS for p in picked):
            continue
        picked.append(cls)
    return picked or [ranked[0][0]]


def caution_from_evidence(evidence: "EvidenceBundle",
                          manifestations: list[str]) -> str:
    house = int(getattr(evidence, "transit_house", 0) or getattr(evidence, "birth_house", 0) or 0)
    planet = str(
        getattr(evidence, "transit_planet", "")
        or getattr(evidence, "primary_dasha", "")
        or "",
    )
    from interpretation.stage_config import required_evidence_met
    if "delayed_reward" in manifestations and required_evidence_met(
        "delayed_recognition", house, planet, direction=evidence.direction,
    ):
        return "delayed_recognition"
    if "distance" in manifestations and evidence.direction != "up":
        return "distance"
    if evidence.direction == "mixed":
        return "mixed_signal"
    return ""
