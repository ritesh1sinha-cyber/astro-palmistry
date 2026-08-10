"""Centralized age/life-stage configuration loader — single source of truth."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_CONFIG_DIR = Path(__file__).resolve().parent / "config"


def _load_json(name: str) -> dict:
    path = _CONFIG_DIR / name
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def age_bands() -> dict[str, dict[str, int]]:
    return _load_json("age_bands.json")


@lru_cache(maxsize=1)
def life_stage_profiles() -> dict[str, dict[str, list[str]]]:
    return _load_json("life_stage_profiles.json")


@lru_cache(maxsize=1)
def life_area_rules() -> dict[str, dict[str, dict[str, str]]]:
    return _load_json("life_area_rules.json")


@lru_cache(maxsize=1)
def manifestation_by_house() -> dict[str, Any]:
    return _load_json("manifestation_by_house.json")


@lru_cache(maxsize=1)
def age_forbidden_terms() -> dict[str, list[str]]:
    return _load_json("age_forbidden.json")


@lru_cache(maxsize=1)
def stage_eligible() -> dict[str, dict[str, list[str]]]:
    return _load_json("stage_eligible.json")


@lru_cache(maxsize=1)
def house_significance() -> dict[str, list[str]]:
    return _load_json("house_significance.json")


@lru_cache(maxsize=1)
def planet_significance() -> dict[str, list[str]]:
    return _load_json("planet_significance.json")


@lru_cache(maxsize=1)
def house_planet_rules() -> dict[str, dict[str, Any]]:
    return _load_json("house_planet_rules.json")


@lru_cache(maxsize=1)
def age_manifestation_rules() -> dict[str, Any]:
    return _load_json("age_manifestation_rules.json")


@lru_cache(maxsize=1)
def conflict_groups() -> dict[str, list[str]]:
    return _load_json("conflict_groups.json")


@lru_cache(maxsize=1)
def health_language_rules() -> dict[str, Any]:
    return _load_json("health_language_rules.json")


@lru_cache(maxsize=1)
def event_claim_rules() -> dict[str, Any]:
    return _load_json("event_claim_rules.json")


@lru_cache(maxsize=1)
def manifestation_families() -> dict[str, str]:
    return _load_json("manifestation_families.json")


def family_for(manifestation_id: str) -> str:
    """Semantic family for intra-report meaning deduplication."""
    mid = (manifestation_id or "").strip()
    if not mid:
        return ""
    return manifestation_families().get(mid, mid)


def families_for_manifestations(*manifestation_ids: str) -> frozenset[str]:
    """Unique semantic families for a list of manifestation IDs."""
    out: set[str] = set()
    for mid in manifestation_ids:
        if mid:
            fam = family_for(mid)
            if fam:
                out.add(fam)
    return frozenset(out)


@lru_cache(maxsize=1)
def manifestation_requirements() -> dict[str, list[str]]:
    """Canonical manifestation requirements.

    The master lookup is authoritative when it declares non-empty
    required_evidence; the older requirements file remains a compatibility
    fallback for legacy manifestations not yet migrated into the master table.
    """
    legacy = _load_json("manifestation_requirements.json")
    try:
        master = _load_json("master_manifestation_lookup.json")
        for mid, meta in (master.get("manifestations") or {}).items():
            req = meta.get("required_evidence")
            if req:
                legacy[mid] = list(req)
    except Exception:  # noqa: BLE001
        pass
    return legacy


@lru_cache(maxsize=1)
def manifestation_cohesion() -> dict[str, dict[str, list[str]]]:
    """Context-aware semantic groups used to merge overlapping meanings.

    Unlike manifestation_families.json, cohesion is life-area aware. This
    matters because the same ID (for example delayed_reward) can mean
    career delay in one context and money progression in another.
    """
    return _load_json("manifestation_cohesion.json")


@lru_cache(maxsize=1)
def master_manifestation_lookup() -> dict[str, Any]:
    """Canonical modern-life meaning metadata for validated manifestations."""
    return _load_json("master_manifestation_lookup.json")


def manifestation_metadata(manifestation_id: str) -> dict[str, Any]:
    return dict((master_manifestation_lookup().get("manifestations") or {}).get(
        manifestation_id or "", {}
    ))


def cohesion_group_for(manifestation_id: str, narrative_area: str = "") -> str:
    """Return the context-aware semantic/cohesion group for a manifestation."""
    mid = (manifestation_id or "").strip()
    area = (narrative_area or "").strip()
    groups = manifestation_cohesion().get(area) or {}
    for group, ids in groups.items():
        if mid in ids:
            return group
    return family_for(mid)


def cohesion_groups_for_manifestations(
    narrative_area: str, *manifestation_ids: str
) -> frozenset[str]:
    return frozenset(
        g for g in (
            cohesion_group_for(mid, narrative_area)
            for mid in manifestation_ids
            if mid
        ) if g
    )


def evidence_atoms(
    house: int,
    planet: str,
    *,
    direction: str = "mixed",
    recognition_tag: str = "",
) -> frozenset[str]:
    """Evidence atoms available from house/planet/direction/tag context.

    Saturn is a structural/delay amplifier, not proof of delay by itself.
    Explicit delay atoms are only added when the direction or the originating
    recognition rule actually carries delay semantics.
    """
    atoms: set[str] = set()
    h = int(house or 0)
    if h:
        atoms.add(f"{h}H_activation")
    if planet:
        atoms.add(f"{planet}_influence")

    # Context atoms: these prevent a manifestation from being inferred from
    # an unrelated house simply because the language layer has a generic
    # wellbeing/money/career fallback.
    if h in (1, 6, 8, 12):
        atoms.add("health_house_activation")
    if h in (2, 8, 11, 12):
        atoms.add("money_house_activation")
    if h in (6, 10, 11):
        atoms.add("career_house_activation")
    if h in (5, 7, 8, 12):
        atoms.add("relationship_house_activation")
    if h in (4, 10):
        atoms.add("home_house_activation")

    if planet == "Saturn":
        atoms.add("Saturn_influence")

    # Saturn alone must NOT satisfy a delay claim. Delay requires an
    # independent signal (challenging direction, an explicitly delay-bearing
    # recognition tag, or another validated timing signal).
    delay_tags = {
        "career_detour", "love_delayed", "delayed_recognition",
        "delayed_reward", "money_started_behind", "repeat_delay",
        "upheaval_delay",
    }
    if direction in ("down", "challenging") or recognition_tag in delay_tags:
        atoms.add("delay_indicator")
    if h == 11 and planet in ("Jupiter", "Mercury", "Venus", "Rahu"):
        atoms.add("network_indicator")
    if direction in ("down", "challenging"):
        atoms.add("delay_indicator")
    return frozenset(atoms)


def required_evidence_met(
    manifestation_id: str,
    house: int,
    planet: str,
    *,
    direction: str = "mixed",
    recognition_tag: str = "",
) -> bool:
    """Return True when every declared evidence atom is actually present."""
    reqs = manifestation_requirements().get(manifestation_id or "")
    if not reqs:
        return True
    available = evidence_atoms(
        house, planet, direction=direction, recognition_tag=recognition_tag
    )
    return all(atom in available for atom in reqs)


def band_for_age(age: int) -> str:
    """Resolve age band from centralized thresholds."""
    for band, spec in age_bands().items():
        lo = int(spec.get("min_age", 0))
        hi = int(spec.get("max_age", 120))
        if lo <= age <= hi:
            return band
    return "adult"


def area_rule(area: str, band: str) -> dict[str, str]:
    """Life-area rule for area × band (translate, not hide)."""
    rules = life_area_rules().get(area) or {}
    return dict(rules.get(band) or rules.get("adult") or {
        "mode": area,
        "narrative_area": area,
        "label_key": area,
    })


def narrative_area_for(area: str, band: str) -> str:
    return area_rule(area, band).get("narrative_area", area)


def eligible_manifestations(band: str, narrative: str, area: str = "") -> frozenset[str]:
    """Allowed manifestation classes for band × narrative domain."""
    stage_map = stage_eligible().get(band) or {}
    classes = stage_map.get(narrative) or stage_map.get(area) or []
    return frozenset(classes)


def default_manifestation(band: str, narrative: str, area: str = "") -> str:
    """Band-safe default when scoring/filtering yields nothing."""
    allowed = eligible_manifestations(band, narrative, area)
    if allowed:
        return sorted(allowed)[0]
    # Last resort by band
    defaults = {
        "child": "study_progress",
        "teen": "study_progress",
        "young_adult": "visibility",
        "adult": "responsibility",
        "mature_adult": "leadership",
        "senior": "mentor_support",
    }
    return defaults.get(band, "responsibility")


def house_manifestation_candidates(
    area: str, house: int, band: str,
) -> tuple[list[str], list[str], str]:
    """Primary/secondary/default candidates from config for area×house×band."""
    area_cfg = manifestation_by_house().get(area) or {}
    house_cfg = area_cfg.get(str(house)) or area_cfg.get("10") or {}
    band_cfg = house_cfg.get(band) or house_cfg.get("adult") or {}
    primary = list(band_cfg.get("primary") or [])
    secondary = list(band_cfg.get("secondary") or [])
    default = str(band_cfg.get("default") or default_manifestation(band, narrative_area_for(area, band), area))
    return primary, secondary, default


def avoid_context_pattern(band: str) -> re.Pattern[str] | None:
    """Regex for avoid-context terms for a band (child/teen/young_adult)."""
    profile = life_stage_profiles().get(band) or {}
    avoid = profile.get("avoid_context") or []
    extra = age_forbidden_terms().get(band) or []
    terms = list(dict.fromkeys(list(avoid) + list(extra)))
    if not terms:
        return None
    escaped = "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True))
    return re.compile(rf"\b({escaped})\b", re.I)


def forbidden_terms(band: str) -> list[str]:
    """Flat forbidden term list for a band."""
    profile = life_stage_profiles().get(band) or {}
    avoid = profile.get("avoid_context") or []
    extra = age_forbidden_terms().get(band) or []
    return list(dict.fromkeys(list(avoid) + list(extra)))


def house_candidates(house: int) -> list[str]:
    """Manifestation taxonomy for a house."""
    return list(house_significance().get(str(house)) or [])


def planet_candidates(planet: str) -> list[str]:
    """Manifestation taxonomy for a planet."""
    return list(planet_significance().get(planet) or [])


def intersection_candidates(house: int, planet: str) -> list[str]:
    """House × planet intersection boosts from config."""
    key = f"{house}:{planet}"
    rule = house_planet_rules().get(key) or {}
    boosts = list(rule.get("boost") or [])
    if boosts:
        return boosts
    # Fallback: overlap of house + planet taxonomies
    hset = set(house_candidates(house))
    pset = set(planet_candidates(planet))
    overlap = sorted(hset & pset)
    if overlap:
        return overlap
    return sorted(hset | pset)[:6]


def adult_only_manifestations() -> frozenset[str]:
    rules = age_manifestation_rules()
    return frozenset(rules.get("adult_only") or [])


def age_replacement(manifestation: str, band: str) -> str | None:
    """Band-specific replacement for an adult-only or mismatched manifestation."""
    replacements = (age_manifestation_rules().get("replacements") or {}).get(manifestation) or {}
    return replacements.get(band)


def validate_age_manifestation(band: str, manifestation: str) -> dict[str, Any]:
    """Hard age gate — reject adult-only IDs for minors."""
    adult_only = adult_only_manifestations()
    if band in ("child", "teen") and manifestation in adult_only:
        repl = age_replacement(manifestation, band)
        if not repl:
            narrative = "career" if manifestation in ("leadership", "authority", "promotion") else "money"
            repl = default_manifestation(band, narrative, narrative)
        return {"allowed": False, "reason": "adult_only_manifestation", "replacement": repl}
    if band == "young_adult" and manifestation in frozenset({"parenting", "retirement", "asset_building"}):
        repl = age_replacement(manifestation, band) or default_manifestation(band, "career", "career")
        return {"allowed": False, "reason": "premature_life_stage", "replacement": repl}
    return {"allowed": True, "reason": "appropriate_life_stage", "replacement": None}


def conflict_group_for(manifestation: str) -> str | None:
    """Return conflict group name if manifestation belongs to one."""
    for group, members in conflict_groups().items():
        if manifestation in members:
            return group
    return None


def areas_for_house(house: int) -> list[str]:
    """Life areas associated with a house (major houses only)."""
    major = age_manifestation_rules().get("major_houses") or {}
    return list(major.get(str(house)) or ["career"])
