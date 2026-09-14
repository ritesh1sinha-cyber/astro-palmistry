"""Pydantic contracts for the LLM prose layer.

Fact models are built by us (engine output, no prose).
Prose models are LANGUAGE-ONLY — the LLM must not author promise,
activation, confidence, direction, dates, planets, or remedies.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Controlled enums (Python owns these; Qwen may express them, never change them)
# ---------------------------------------------------------------------------
SCHEMA_VERSION = "1.7"
PROMPT_VERSIONS = {
    "full_report": "REPORT_CONVERSATIONAL_PROMPT_V8_CONSULTATION_CONCLUSION",
    "full_report_areas": "REPORT_AREAS_PROMPT_V8_CONSULTATION_CONCLUSION",
    "user_question": "QUESTION_PROSE_PROMPT_V1",
    "horary": "HORARY_PROSE_PROMPT_V1",
    "palm": "PALM_CONVERSATIONAL_PROMPT_V5",
    "chat": "CHAT_PROSE_PROMPT_V1",
    "plain_summary": "PLAIN_SUMMARY_PROMPT_V2",
}

PromiseStatus = Literal[
    "strongly_supported", "supported", "mixed", "weak", "insufficient_evidence",
]
ChallengeStatus = Literal[
    "strongly_indicated", "indicated", "mixed", "weak", "insufficient_evidence",
]
ActivationStatus = Literal[
    "strongly_active", "active", "mixed", "weak", "inactive", "insufficient_evidence",
]
# Feedback enums + legacy engine aliases (up/down map to support/caution).
Direction = Literal["support", "caution", "mixed", "neutral", "up", "down"]
Confidence = Literal["high", "moderate", "low"]
Agreement = Literal["strong", "partial", "weak", "insufficient"]
Kind = Literal["promise", "challenge"]
Polarity = Literal["support", "caution"]
Family = Literal["natal", "divisional", "rules", "palm", "horary", "other"]
# Banded levels. The life-state block reports bands rather than scores on
# purpose: a float in the facts grounds its digits for the whole page, which
# would let prose print numbers the date gate is meant to catch.
Level = Literal["none", "low", "moderate", "high", "very_high"]
# "home" is the household itself — the roof they grew up under and the one
# they keep now. The classical sources describe it alongside the people, and a
# background block that names three relatives but never the home reads partial.
Relation = Literal["father", "mother", "siblings", "home"]

AREA_KEYS = (
    "self", "parents", "siblings", "love", "children", "profession",
    "learning", "money", "home", "strengths", "health", "inner",
)


# ---------------------------------------------------------------------------
# Fact models (input — built by the engine, never by the LLM)
# ---------------------------------------------------------------------------
class EvidenceFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    family: Family = "other"
    polarity: Polarity = "support"
    text_id: str = ""
    # Prefer short normalized tags; long classical text is stripped upstream.
    text: str = Field(default="", max_length=160)
    semantic_tags: list[str] = Field(default_factory=list, max_length=6)


class WindowFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: str = ""          # ISO / Month YYYY — Python-validated only
    end: str = ""
    label: str = Field(default="", max_length=120)
    event_type: str = Field(default="", max_length=80)
    confidence: Confidence = "low"
    source: str = Field(default="", max_length=80)
    score: float = 0.0


class TransitionFact(BaseModel):
    """One dated life-area transition produced from canonical timing overlap."""
    model_config = ConfigDict(extra="forbid")
    start: str = ""
    end: str = ""
    area: str = ""
    direction: Direction = "mixed"
    phase: str = Field(default="", max_length=100)
    meaning: str = Field(default="", max_length=220)
    event_type: str = Field(default="", max_length=100)
    planet: str = Field(default="", max_length=30)
    dasha: str = Field(default="", max_length=100)
    bav: int = 0
    score: float = 0.0
    confidence: Confidence = "low"
    source: str = Field(default="", max_length=100)
    overlap: list[str] = Field(default_factory=list, max_length=7)
    drivers: list[str] = Field(default_factory=list, max_length=7)
    timing_systems: dict[str, Any] = Field(default_factory=dict)


class TransitContextFact(BaseModel):
    """One dated stay of the house ruler or a running dasha lord."""
    model_config = ConfigDict(extra="forbid")
    planet: str = Field(default="", max_length=30)
    role: str = Field(default="", max_length=80)
    sign: str = Field(default="", max_length=20)
    house: int = 0
    start: str = ""
    end: str = ""
    bav: int = 0
    tone: str = Field(default="steady", max_length=20)
    major: bool = False
    in_house: bool = False


class CardFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    area: str
    label: str = ""
    kind: Kind = "promise"
    status: str = "insufficient_evidence"
    activation_status: str = "inactive"
    confidence: Confidence = "low"
    prediction_strength: str = "insufficient_evidence"
    agreement: Agreement = "weak"
    direction: Direction = "mixed"
    score: float = 0.0
    support_n: int = 0
    caution_n: int = 0
    house: int = 0
    evidence: list[EvidenceFact] = Field(default_factory=list, max_length=6)
    manifestation_ids: list[str] = Field(default_factory=list, max_length=6)
    semantic_tags: list[str] = Field(default_factory=list, max_length=8)
    window: Optional[WindowFact] = None
    timing_windows: list[WindowFact] = Field(default_factory=list, max_length=4)
    question_lens: str = ""
    # Paid-only fields — stripped by project_for_access("free")
    wealth_sub: list[dict[str, Any]] = Field(default_factory=list)
    remedy_eligible: bool = False
    approved_remedies: list[str] = Field(default_factory=list, max_length=3)
    allowed_planets: list[str] = Field(default_factory=list, max_length=8)
    allowed_dates: list[str] = Field(default_factory=list, max_length=12)
    # Conversational template — precomputed by Python, expressed by the LLM.
    outlook_line: str = Field(default="", max_length=220)
    manifestations: list[str] = Field(default_factory=list, max_length=4)
    remedy_text: str = Field(default="", max_length=220)
    transition_map: list["TransitionFact"] = Field(default_factory=list, max_length=6)
    transit_context: list["TransitContextFact"] = Field(default_factory=list, max_length=14)


class RecentMonthFact(BaseModel):
    """One dated past window used to build trust in the free section."""
    model_config = ConfigDict(extra="forbid")
    start: str = ""
    end: str = ""
    area: str = ""
    label: str = ""
    direction: str = "mixed"
    direction_label: str = ""
    headline: str = Field(default="", max_length=220)
    manifests: list[str] = Field(default_factory=list, max_length=3)
    # Complete confluence as it stood at the start of this window. Same lane
    # weights as the current and future judgements, evaluated backwards, so a
    # reader can check the claim about the past against the same calculation.
    judgement: Literal["good", "moderate", "challenging", "mixed", "insufficient"] = "insufficient"
    agreement: Literal["strong", "good", "mixed", "conflicting", "insufficient"] = "insufficient"
    lane_judgements: dict[str, str] = Field(default_factory=dict, max_length=10)
    supporting_factors: list[str] = Field(default_factory=list, max_length=4)
    caution_factors: list[str] = Field(default_factory=list, max_length=4)
    divisional_chart: str = ""
    divisional_verdict: str = ""


class DomainStateFact(BaseModel):
    """How live one life area is right now, read off its canonical card."""
    model_config = ConfigDict(extra="forbid")
    area: str
    label: str = ""
    activation: Level = "none"
    pressure: Level = "none"
    support: Level = "none"
    confidence: Confidence = "low"
    agreement: Agreement = "weak"
    contradiction: bool = False
    # Controlled vocabulary the LLM may express; it must not invent its own.
    experience: list[str] = Field(default_factory=list, max_length=3)
    outcome_language_restricted: bool = False


class MindTopicFact(BaseModel):
    """A subject that may be occupying the person — never a stated fact.

    ``is_fact`` stays false so the prose layer and its QA gate both know this
    is what the chart makes likely to be on their mind, not something the
    reading knows about their circumstances.
    """
    model_config = ConfigDict(extra="forbid")
    area: str
    label: str = ""
    likelihood: Literal["likely", "possible"] = "possible"
    experience: list[str] = Field(default_factory=list, max_length=3)
    is_fact: Literal[False] = False


class LifeStateFacts(BaseModel):
    """Current-life-state block for the free trust section."""
    model_config = ConfigDict(extra="forbid")
    chapter_tone: Literal["supported", "pressured", "mixed", "steady"] = "mixed"
    strongest_theme: str = ""
    strongest_theme_label: str = ""
    themes: list[str] = Field(default_factory=list, max_length=6)
    emotional_pressure: Level = "low"
    decision_pressure: Level = "low"
    responsibility: Level = "low"
    uncertainty: Level = "low"
    domains: list[DomainStateFact] = Field(default_factory=list, max_length=12)
    mind_now: list[MindTopicFact] = Field(default_factory=list, max_length=3)


class HandContrastFacts(BaseModel):
    """What the two hands say against each other.

    Palmistry's own convention is the trust material here: the non-dominant
    hand is read as what someone started with and the dominant hand as what
    they have made of it. Only plain theme and trait words cross this boundary
    — the engine's mount keys are planet names and stay behind it.
    """
    model_config = ConfigDict(extra="forbid")
    dominant_hand: str = "right"
    agreement: Literal["high", "partial", "low"] = "partial"
    steady: list[str] = Field(default_factory=list, max_length=4)
    developed: list[str] = Field(default_factory=list, max_length=4)
    latent: list[str] = Field(default_factory=list, max_length=4)
    developed_traits: list[str] = Field(default_factory=list, max_length=4)
    latent_traits: list[str] = Field(default_factory=list, max_length=4)


class PalmStateFacts(BaseModel):
    """Current-palm-state block for the free trust section.

    Palmistry has no dasha or transit clock, so nothing here is a period. It
    describes what the dominant hand expresses now, and every age stays in
    ``future_windows`` where the existing age gate can see it.
    """
    model_config = ConfigDict(extra="forbid")
    chapter_tone: Literal["supported", "pressured", "mixed", "steady"] = "mixed"
    themes: list[str] = Field(default_factory=list, max_length=6)
    emotional_pressure: Level = "low"
    decision_pressure: Level = "low"
    uncertainty: Level = "low"
    domains: list[DomainStateFact] = Field(default_factory=list, max_length=10)
    mind_now: list[MindTopicFact] = Field(default_factory=list, max_length=3)
    confidence_note: str = Field(default="", max_length=200)


class FamilyNoteFact(BaseModel):
    """Family texture agreed by more than one classical method.

    Only normalized tags and already-sanitized lines survive here; the raw
    case-book wording the source engines carry never reaches the LLM.
    """
    model_config = ConfigDict(extra="forbid")
    relation: Relation
    label: str = ""
    tags: list[str] = Field(default_factory=list, max_length=6)
    notes: list[str] = Field(default_factory=list, max_length=3)
    method_count: int = 0


class DashaClockFact(BaseModel):
    """One deterministic timing clock. Qwen may describe it, never calculate it."""
    model_config = ConfigDict(extra="forbid")
    system: Literal["vimshottari", "chara", "yogini"]
    current: str = ""
    current_start: str = ""
    current_end: str = ""
    next: str = ""
    next_start: str = ""
    next_end: str = ""
    judgement: Literal["good", "moderate", "challenging", "mixed", "insufficient"] = "insufficient"
    activated_houses: list[int] = Field(default_factory=list, max_length=6)


class CrossoverFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: str = ""
    systems: list[str] = Field(default_factory=list, max_length=4)
    significance: str = Field(default="", max_length=180)


class SlowTransitFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    planet: str = Field(default="", max_length=20)
    functional_role: str = Field(default="", max_length=40)
    sign: str = Field(default="", max_length=20)
    house: int = 0
    from_natal_house: int = 0
    ashtakavarga: Optional[int] = None
    start: str = ""
    end: str = ""
    judgement: Literal["supportive", "testing", "mixed", "neutral", "insufficient"] = "insufficient"


class JaiminiFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    available: bool = False
    ak: str = ""
    amk: str = ""
    gk: str = ""
    pk: str = ""
    current_maha_sign: str = ""
    current_antar_sign: str = ""
    activated_houses: list[int] = Field(default_factory=list, max_length=6)
    argala_judgement: str = Field(default="", max_length=220)
    judgement: Literal["good", "moderate", "challenging", "mixed", "insufficient"] = "insufficient"
    basis: list[str] = Field(default_factory=list, max_length=5)


class DashaPlanetTransitFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    planet: str = Field(default="", max_length=20)
    role: str = Field(default="", max_length=30)
    functional_role: str = Field(default="", max_length=40)
    sign: str = Field(default="", max_length=20)
    house: int = 0
    from_natal_planet: int = 0
    ashtakavarga: Optional[int] = None
    judgement: Literal["supportive", "testing", "mixed", "neutral", "insufficient"] = "insufficient"


class FutureConfluenceFact(BaseModel):
    """One future event at which the complete life-area confluence is recalculated.

    The date is generated by deterministic dasha/transit engines. The change
    label is also deterministic: Qwen may explain it but may not infer it.
    """
    model_config = ConfigDict(extra="forbid")
    date: str = ""
    change_type: Literal["baseline", "improves", "eases_but_continues", "continues", "worsens", "mixed_change"] = "continues"
    previous_judgement: Literal["good", "moderate", "challenging", "mixed", "insufficient"] = "insufficient"
    judgement: Literal["good", "moderate", "challenging", "mixed", "insufficient"] = "insufficient"
    score: float = 0.0
    agreement: Literal["strong", "good", "mixed", "conflicting", "insufficient"] = "insufficient"
    vimshottari: str = ""
    chara: str = ""
    yogini: str = ""
    transit_events: list[str] = Field(default_factory=list, max_length=8)
    dasha_changes: list[str] = Field(default_factory=list, max_length=6)
    # The complete confluence is authoritative. Keep the lane result attached
    # to every future checkpoint so the renderer/LLM cannot infer improvement
    # from a single dasha change.
    lane_judgements: dict[str, str] = Field(default_factory=dict, max_length=8)
    lane_scores: dict[str, float] = Field(default_factory=dict, max_length=8)
    supporting_factors: list[str] = Field(default_factory=list, max_length=6)
    caution_factors: list[str] = Field(default_factory=list, max_length=6)
    reason: str = Field(default="", max_length=280)


class LifeAreaJudgementFact(BaseModel):
    """Deterministic evidence matrix for one life area."""
    model_config = ConfigDict(extra="forbid")
    area: str
    label: str = ""
    house: int = 0
    natural_karakas: list[str] = Field(default_factory=list, max_length=4)
    house_lord: str = ""
    house_lord_role: str = ""
    depositor: str = ""
    house_strength: str = ""
    divisional_chart: str = ""
    divisional_verdict: str = ""
    amk: str = ""
    natal_promise: str = ""
    current_vimshottari: str = ""
    current_chara: str = ""
    current_yogini: str = ""
    current_transit: str = ""
    next_period: str = ""
    final_judgement: Literal["good", "moderate", "challenging", "mixed", "insufficient"] = "insufficient"
    current_summary: str = Field(default="", max_length=400)
    future_summary: str = Field(default="", max_length=400)
    remedy_reason: str = Field(default="", max_length=240)
    # Deterministic confluence — this is the actual life-area judgement, not a
    # copy of the legacy card direction. Qwen may explain these fields but may
    # never recalculate or override them.
    natal_foundation_score: float = 0.0
    confluence_score: float = 0.0
    confluence_agreement: Literal["strong", "good", "mixed", "conflicting", "insufficient"] = "insufficient"
    lane_judgements: dict[str, str] = Field(default_factory=dict, max_length=10)
    lane_scores: dict[str, float] = Field(default_factory=dict, max_length=10)
    supporting_factors: list[str] = Field(default_factory=list, max_length=8)
    caution_factors: list[str] = Field(default_factory=list, max_length=8)
    activated_houses: list[int] = Field(default_factory=list, max_length=8)
    current_verdict: Literal["good", "moderate", "challenging", "mixed", "insufficient"] = "insufficient"
    # Customer-safe deterministic labels. These are derived from the complete
    # confluence; Qwen may explain them but may not invent alternatives.
    activation_label: str = ""
    confluence_label: str = ""
    relief_window: str = ""
    stronger_window: str = ""
    future_confluence: list[FutureConfluenceFact] = Field(default_factory=list, max_length=16)


class VedicContext(BaseModel):
    """Running period and chart identity the prose is allowed to name.

    Dates are ``start``/``end`` on purpose so ``allowed_dates_from_facts``
    grounds month and year tokens automatically. The ``mahadasha`` /
    ``antardasha`` / ``lagna`` field *names* ground those words in the
    facts payload so QA can accept them when the model uses them.
    """
    model_config = ConfigDict(extra="forbid")
    period_lord: str = Field(default="", max_length=20)
    sub_period_lord: str = Field(default="", max_length=20)
    mahadasha: str = Field(default="", max_length=20)
    antardasha: str = Field(default="", max_length=20)
    lagna: str = Field(default="", max_length=20)
    nakshatra: str = Field(default="", max_length=40)
    start: str = ""
    end: str = ""
    rising_sign: str = Field(default="", max_length=20)
    moon_sign: str = Field(default="", max_length=20)


class FactsMeta(BaseModel):
    """Versioning / traceability — never rendered into customer HTML."""
    model_config = ConfigDict(extra="forbid", protected_namespaces=())
    schema_version: str = SCHEMA_VERSION
    engine_version: str = ""
    report_id: str = ""
    facts_hash: str = ""
    prompt_version: str = ""
    model_name: str = ""
    access: Literal["free", "paid"] = "free"


class ReportFacts(BaseModel):
    """Fact payload for a full astrology report (normalized, access-projected)."""
    model_config = ConfigDict(extra="forbid")
    kind: Literal["full_report"] = "full_report"
    schema_version: str = SCHEMA_VERSION
    engine_version: str = ""
    report_id: str = ""
    facts_hash: str = ""
    first_name: str = Field(default="", max_length=40)
    age_band: str = "adult"
    age_years: Optional[int] = None
    gender: str = "unknown"
    access: Literal["free", "paid"] = "free"
    cards: list[CardFacts] = Field(default_factory=list)
    dashboard_buckets: dict[str, list[str]] = Field(default_factory=dict)
    timing_windows: list[WindowFact] = Field(default_factory=list, max_length=8)
    # Free-section conversational facts (Python-owned, never re-derived by LLM).
    personality_traits: list[str] = Field(default_factory=list, max_length=12)
    phase_direction: Direction = "mixed"
    phase_tone: str = Field(default="", max_length=40)  # supportive / mixed / demanding
    phase_end: str = ""
    phase_notes: list[str] = Field(default_factory=list, max_length=6)
    recent_months: list[RecentMonthFact] = Field(default_factory=list, max_length=4)
    hardest_areas: list[str] = Field(default_factory=list, max_length=4)
    hardest_area_labels: list[str] = Field(default_factory=list, max_length=4)
    life_state: Optional[LifeStateFacts] = None
    family_notes: list[FamilyNoteFact] = Field(default_factory=list, max_length=4)
    # Deterministic analytical layer for the paid consultation report. Qwen only
    # turns these findings into readable prose.
    timing_systems: list[DashaClockFact] = Field(default_factory=list, max_length=3)
    crossover_points: list[CrossoverFact] = Field(default_factory=list, max_length=8)
    slow_transits: list[SlowTransitFact] = Field(default_factory=list, max_length=4)
    jaimini: Optional[JaiminiFact] = None
    dasha_planet_transits: list[DashaPlanetTransitFact] = Field(default_factory=list, max_length=4)
    life_area_judgements: list[LifeAreaJudgementFact] = Field(default_factory=list, max_length=12)
    vedic_context: Optional[VedicContext] = None
    # One orchestration-time projection shared by the visible report and its
    # summaries.  It contains only fired, customer-safe specialist findings.
    specialist_readings: dict[str, Any] = Field(default_factory=dict)


class QuestionFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["user_question"] = "user_question"
    schema_version: str = SCHEMA_VERSION
    engine_version: str = ""
    report_id: str = ""
    facts_hash: str = ""
    first_name: str = Field(default="", max_length=40)
    age_band: str = "adult"
    access: Literal["free", "paid"] = "free"
    question: str = Field(default="", max_length=280)
    area_key: str = ""
    direction: Direction = "mixed"
    confidence: Confidence = "low"
    promise_status: str = ""
    activation_status: str = ""
    n_methods: int = 0
    n_up: int = 0
    n_down: int = 0
    route: dict[str, Any] = Field(default_factory=dict)
    best: Optional[WindowFact] = None
    nearest: Optional[WindowFact] = None
    windows: list[WindowFact] = Field(default_factory=list, max_length=6)
    support_n: int = 0
    caution_n: int = 0
    manifestation_ids: list[str] = Field(default_factory=list, max_length=6)
    allowed_planets: list[str] = Field(default_factory=list, max_length=12)
    allowed_dates: list[str] = Field(default_factory=list, max_length=36)
    remedy_text: str = Field(default="", max_length=400)
    hindering_planet: str = Field(default="", max_length=40)
    supportive_planet: str = Field(default="", max_length=40)
    hindering_remedy: str = Field(default="", max_length=250)
    supportive_remedy: str = Field(default="", max_length=250)

    # Canonical full-report truth. These are a projection of the same
    # CanonicalAreaResult used by the full report; QuestionFacts must not
    # become a second prediction engine.
    truth_source: Literal["full_report_canonical", "question_specific_fallback"] = "question_specific_fallback"
    canonical_area_key: str = ""
    canonical_promise_status: str = ""
    canonical_activation_status: str = ""
    canonical_direction: Direction = "mixed"
    canonical_confidence: Confidence = "low"
    canonical_agreement: Agreement = "weak"
    canonical_evidence: list[EvidenceFact] = Field(default_factory=list, max_length=8)
    canonical_manifestations: list[str] = Field(default_factory=list, max_length=6)
    canonical_timing: list[WindowFact] = Field(default_factory=list, max_length=6)
    timing_can_create_promise: bool = False


class HoraryLaneFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lane: Literal["vedic", "western", "kp"] = "vedic"
    verdict: str = ""
    confidence: Confidence = "low"
    score: float = 0.0
    systems: list[str] = Field(default_factory=list, max_length=8)


class HoraryFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["horary"] = "horary"
    schema_version: str = SCHEMA_VERSION
    engine_version: str = ""
    report_id: str = ""
    facts_hash: str = ""
    first_name: str = Field(default="", max_length=40)
    access: Literal["free", "paid"] = "free"
    question: str = Field(default="", max_length=280)
    subject: str = ""
    area: str = ""
    house: int = 0
    label: str = ""
    confidence: Confidence = "low"
    score: float = 0.0
    contradicted: bool = False
    favourable: bool = False
    querent_planet: str = ""
    quesited_planet: str = ""
    aspect_description: str = ""
    moon_description: str = ""
    lanes: list[HoraryLaneFact] = Field(default_factory=list)
    allowed_planets: list[str] = Field(default_factory=list, max_length=12)
    allowed_dates: list[str] = Field(default_factory=list, max_length=24)
    timing_windows: list[str] = Field(default_factory=list, max_length=6)
    remedy_text: str = Field(default="", max_length=400)
    hindering_planet: str = Field(default="", max_length=40)
    supportive_planet: str = Field(default="", max_length=40)
    hindering_remedy: str = Field(default="", max_length=250)
    supportive_remedy: str = Field(default="", max_length=250)
    language: str = "en"
    kp_number: int = 0
    cusp_sub_lord: str = Field(default="", max_length=20)
    star_lord: str = Field(default="", max_length=20)
    ruling_planets: list[str] = Field(default_factory=list, max_length=12)
    significations: list[str] = Field(default_factory=list, max_length=16)
    is_yes_no: bool = True
    # The three lines the reader actually saw. Follow-up chat has to answer
    # from these or it drifts away from the page it is sitting under.
    plain_answer: str = Field(default="", max_length=400)
    plain_timing: str = Field(default="", max_length=300)
    plain_remedy: str = Field(default="", max_length=300)
    window_open: str = Field(default="", max_length=40)
    window_close: str = Field(default="", max_length=40)
    window_known: bool = False


class PalmAspectFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aspect: str
    title: str = ""
    direction: Direction = "mixed"
    strength: str = "tentative"
    confidence: Confidence = "low"
    signal_ids: list[str] = Field(default_factory=list, max_length=12)
    point_ids: list[str] = Field(default_factory=list, max_length=8)
    semantic_tags: list[str] = Field(default_factory=list, max_length=6)
    semantic_summary: str = Field(default="", max_length=600)
    recognize: list[str] = Field(default_factory=list, max_length=6)
    age_window: list[int] = Field(default_factory=list, max_length=2)
    score: float = 0.0


class PalmFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["palm"] = "palm"
    schema_version: str = SCHEMA_VERSION
    engine_version: str = ""
    report_id: str = ""
    facts_hash: str = ""
    first_name: str = Field(default="", max_length=40)
    age_band: str = "adult"
    age_years: Optional[int] = None
    access: Literal["free", "paid"] = "free"
    dominant_hand: str = "right"
    photo_grade: str = "fair"
    photo_confidence: Confidence = "moderate"
    special_marks_allowed: bool = False
    future_timing_allowed: bool = True
    age_precision: str = "window"
    quality_note: str = Field(default="", max_length=180)
    aspects: list[PalmAspectFacts] = Field(default_factory=list)
    future_windows: list[dict[str, Any]] = Field(default_factory=list, max_length=6)
    special_mark_ids: list[str] = Field(default_factory=list, max_length=8)
    # Conversational free-section facts.
    personality_traits: list[str] = Field(default_factory=list, max_length=12)
    life_stage_note: str = Field(default="", max_length=220)
    life_stage_age: Optional[int] = None
    demanding_aspect: str = ""
    demanding_aspect_label: str = ""
    remedies_allowed: bool = False
    remedies: list[str] = Field(default_factory=list, max_length=4)
    hand_contrast: Optional[HandContrastFacts] = None
    palm_state: Optional[PalmStateFacts] = None
    consultation_sections: dict[str, Any] = Field(default_factory=dict)
    language: str = "en"


# ---------------------------------------------------------------------------
# Prose models (LLM output — language only, no prediction authority)
# ---------------------------------------------------------------------------
class CardProse(BaseModel):
    """Conversational life-question prose. Authoritative truth stays in CardFacts."""
    model_config = ConfigDict(extra="forbid")
    area: str
    question_lens: str = Field(default="", max_length=120)
    headline: str = Field(..., min_length=8, max_length=140)
    summary: str = Field(default="", max_length=280)
    how_this_may_show_up: list[str] = Field(default_factory=list, max_length=3)
    what_to_watch: list[str] = Field(default_factory=list, max_length=2)
    what_helps: list[str] = Field(default_factory=list, max_length=2)
    timing_summary: str = Field(default="", max_length=180)

    @model_validator(mode="before")
    @classmethod
    def _accept_legacy_keys(cls, data: Any) -> Any:
        """Map older why/meaning/manifestations/pressure/action keys."""
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if not (d.get("summary") or "").strip():
            d["summary"] = (d.get("why") or d.get("meaning") or "")[:280]
        if not d.get("how_this_may_show_up") and d.get("manifestations"):
            d["how_this_may_show_up"] = list(d.get("manifestations") or [])[:3]
        if not d.get("what_to_watch") and d.get("pressure"):
            d["what_to_watch"] = [str(d["pressure"])][:2]
        if not d.get("what_helps") and d.get("action"):
            d["what_helps"] = [str(d["action"])][:2]
        for k in ("why", "meaning", "manifestations", "pressure", "action"):
            d.pop(k, None)
        return d

    @field_validator("headline", "summary", "timing_summary")
    @classmethod
    def _strip(cls, v: str) -> str:
        return (v or "").strip()

    @field_validator("how_this_may_show_up", "what_to_watch", "what_helps")
    @classmethod
    def _strip_list(cls, v: list[str]) -> list[str]:
        return [str(x).strip() for x in (v or []) if str(x).strip()][:3]

    # Renderer-compat aliases
    @property
    def why(self) -> str:
        return self.summary

    @property
    def meaning(self) -> str:
        return self.summary

    @property
    def manifestations(self) -> list[str]:
        return list(self.how_this_may_show_up or [])

    @property
    def pressure(self) -> str:
        return (self.what_to_watch or [""])[0] if self.what_to_watch else ""

    @property
    def action(self) -> str:
        return (self.what_helps or [""])[0] if self.what_helps else ""


class ReportProse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    opening: str = Field(default="", max_length=320)
    master_narrative: str = Field(default="", max_length=520)
    cards: list[CardProse] = Field(default_factory=list, max_length=12)


class ConversationalAreaProse(BaseModel):
    """One compact life-area consultation; deterministic evidence stays collapsible."""
    model_config = ConfigDict(extra="forbid")
    area: str
    # Customer-facing paragraph: current cause -> duration/easing -> complete
    # confluence -> natal support -> longer-term outcome.
    conclusion: str = Field(default="", max_length=620)
    @field_validator("conclusion")
    @classmethod
    def _valid_conclusion(cls, v: str) -> str:
        text = (v or "").strip()
        banned = (
            "This remedy is linked to a relevant chart factor",
            "The chart evidence is summarized in the life-area reading above",
            "Timing evidence is included in the overall reading",
            "Promised, not yet active",
        )
        if any(x.lower() in text.lower() for x in banned):
            raise ValueError("customer-facing placeholder is not allowed")
        # A real consultation conclusion needs at least two sentences; a 7B
        # one-line generic answer is not acceptable for production.
        if text and sum(text.count(x) for x in (".", "!", "?")) < 2:
            raise ValueError("life-area conclusion must contain at least two sentences")
        return text[:620]

    # One practical remedy, sourced only from approved deterministic remedies.
    remedy: str = Field(default="", max_length=220)
    # Legacy fields are retained for compatibility with older cached/model output,
    # but the renderer no longer prints them as separate redundant paragraphs.
    astrological_basis: str = Field(default="", max_length=320)
    interpretation: str = Field(default="", max_length=360)
    outlook: str = Field(default="", max_length=280)
    timing: str = Field(default="", max_length=160)
    manifestation: str = Field(default="", max_length=180)
    transition_note: str = Field(default="", max_length=260)


class ConversationalProse(BaseModel):
    """Whole-page astrologer-style report — one LLM call per access tier."""
    model_config = ConfigDict(extra="forbid")
    # These two fields force the model to expose the reasoning layer instead
    # of turning every reading into generic motivational prose.
    astrological_basis: str = Field(default="", max_length=520)
    interpretation: str = Field(default="", max_length=520)
    # Paid pays for depth here: every trait the engines agreed on gets a line,
    # so the ceiling is a paragraph rather than three sentences.
    personality: str = Field(..., min_length=8, max_length=900)
    current_phase: str = Field(..., min_length=8, max_length=360)
    final_guidance: str = Field(default="", max_length=420)
    recent_months: str = Field(default="", max_length=420)
    hardest_area_note: str = Field(default="", max_length=180)
    # Free-section trust block: what may be on their mind, and why now.
    mind_now: list[str] = Field(default_factory=list, max_length=3)
    why_now: str = Field(default="", max_length=380)
    # One line per family_notes entry — father, mother, siblings, home.
    family_note: list[str] = Field(default_factory=list, max_length=4)
    areas: list[ConversationalAreaProse] = Field(default_factory=list, max_length=10)

    @field_validator("mind_now")
    @classmethod
    def _strip_mind_now(cls, v: list[str]) -> list[str]:
        return [str(x).strip()[:220] for x in (v or []) if str(x).strip()][:3]

    @field_validator("family_note")
    @classmethod
    def _strip_family_note(cls, v: list[str]) -> list[str]:
        return [str(x).strip()[:280] for x in (v or []) if str(x).strip()][:4]


class ConversationalAreasProse(BaseModel):
    """Only the life-area passages — the paid page's second call.

    A paid page is a long reply against an 8k context. Asked for the whole
    thing at once the model spends its budget on the opening and returns three
    of eight areas, so the areas are requested on their own with only the card
    facts in front of them.
    """
    model_config = ConfigDict(extra="forbid")
    areas: list[ConversationalAreaProse] = Field(default_factory=list, max_length=12)


class ReportConfluenceProse(BaseModel):
    """LLM-generated prose for the full report — expression only, no new facts.

    Python owns all prediction truth (areas, phases, timing, status, planets,
    houses, dashas). This model is language-only: the LLM may cite facts that
    appear in the input but must not invent, calculate, or imply any astrological
    factor not already supplied. Every sentence must trace to the supplied facts.

    Use the classical report tone: authoritative, specific where grounded, general
    otherwise. No guaranteed/certain/destined language. Health language stays at
    routine/recovery. Remedies only from approved_remedies list. Soft modality only.
    """
    model_config = ConfigDict(extra="forbid")
    astrological_basis: str = Field(default="", max_length=700)
    interpretation: str = Field(default="", max_length=700)
    personality: str = Field(default="", max_length=720)
    current_phase: str = Field(default="", max_length=520)
    hardest_area_note: str = Field(default="", max_length=200)
    mind_now: list[str] = Field(default_factory=list, max_length=3)
    why_now: str = Field(default="", max_length=520)
    family_note: list[str] = Field(default_factory=list, max_length=6)
    areas: dict[str, str] = Field(default_factory=dict)


class ConversationalPalmAreaProse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aspect: str
    outlook: str = Field(..., min_length=8, max_length=240)
    timing: str = Field(default="", max_length=140)
    manifestation: str = Field(default="", max_length=140)
    remedy: str = Field(default="", max_length=160)


class ConversationalPalmProse(BaseModel):
    """Whole-page conversational palm report — one LLM call per access tier."""
    model_config = ConfigDict(extra="forbid")
    personality: str = Field(..., min_length=8, max_length=360)
    current_phase: str = Field(..., min_length=8, max_length=280)
    hardest_area_note: str = Field(default="", max_length=160)
    mind_now: list[str] = Field(default_factory=list, max_length=3)
    why_now: str = Field(default="", max_length=380)
    hand_contrast_note: str = Field(default="", max_length=380)
    areas: list[ConversationalPalmAreaProse] = Field(default_factory=list, max_length=8)


class QuestionProse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    opening: str = Field(..., min_length=8, max_length=350)
    answer: str = Field(..., min_length=8, max_length=550)
    why: str = Field(default="", max_length=450)
    timing: str = Field(default="", max_length=350)
    action: str = Field(default="", max_length=450)


class HoraryProse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lead: str = Field(..., min_length=8, max_length=350)
    verdict_line: str = Field(..., min_length=8, max_length=550)
    why: str = Field(default="", max_length=350)
    action: str = Field(default="", max_length=450)


class PalmAspectProse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aspect: str
    headline: str = Field(..., min_length=8, max_length=140)
    why: str = Field(default="", max_length=220)
    points: list[str] = Field(default_factory=list, max_length=3)


class PalmProse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    opening: str = Field(default="", max_length=320)
    aspects: list[PalmAspectProse] = Field(default_factory=list, max_length=12)


class ChatAnswer(BaseModel):
    """Phase-2 paid follow-up chat response."""
    model_config = ConfigDict(extra="forbid")
    # The chat prompt asks for up to 800 words, which overruns 4000 characters
    # and used to fail validation on exactly the longest, most useful answers.
    answer: str = Field(..., min_length=4, max_length=6000)
    used_fact_ids: list[str] = Field(default_factory=list, max_length=12)
    out_of_scope: bool = False


class ToolArgs(BaseModel):
    """Arguments the planner may pass to a tool.

    Flat and typed rather than an open dict: strict ``json_schema`` mode
    rejects unconstrained ``additionalProperties``, so an open mapping would
    force every call down the ``guided_json`` fallback.
    """
    model_config = ConfigDict(extra="forbid")
    area: str = ""
    planet: str = ""
    event: str = ""
    topic: str = ""


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: str = Field(..., max_length=60)
    args: ToolArgs = Field(default_factory=ToolArgs)


class QuestionPlan(BaseModel):
    """What the model understood, and which engines it wants run."""
    model_config = ConfigDict(extra="forbid")
    restated_intent: str = Field(default="", max_length=300)
    in_scope: bool = True
    life_area: str = Field(default="general_destiny", max_length=60)
    target_planet: str = Field(default="", max_length=20)
    tools: list[ToolRequest] = Field(default_factory=list, max_length=4)


class HoraryJudgement(BaseModel):
    """KP horary decision. The model judges; it does not write the answer."""
    model_config = ConfigDict(extra="forbid")
    restated_intent: str = Field(default="", max_length=300)
    in_scope: bool = True
    is_yes_no: bool = True
    # What the reader wants back. A chart can settle occurrence and timing;
    # it cannot return a quantity, so that has to be said rather than dodged.
    asks: Literal["yes_no", "timing", "quantity", "other"] = "other"
    label: Literal["yes", "no", "conditional", "open", "out_of_scope"] = "open"
    confidence: Literal["low", "moderate", "good"] = "low"
    reason: str = Field(default="", max_length=400)


class HoraryPlainAnswer(BaseModel):
    """The whole horary reply: a verdict, a date, a remedy. Nothing else."""
    model_config = ConfigDict(extra="forbid")
    answer: str = Field(..., min_length=10, max_length=220)
    timing: str = Field(default="", max_length=200)
    remedy: str = Field(default="", max_length=220)


class PlainSummarySection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(..., min_length=4, max_length=120)
    body: str = Field(..., min_length=20, max_length=900)
    # insight = a finding from the reading; locked = what the paid half holds;
    # cta = the closing line the UI renders as the unlock button.
    role: Literal["insight", "locked", "cta"] = "insight"


class PlainSummaryProse(BaseModel):
    """Executive plain-English summary of a finished customer report."""
    model_config = ConfigDict(extra="forbid")
    headline: str = Field(default="", max_length=180)
    sections: list[PlainSummarySection] = Field(..., min_length=1, max_length=8)


class LlmRunMeta(BaseModel):
    """Internal monitoring — never enter customer HTML."""
    model_config = ConfigDict(extra="forbid", protected_namespaces=())
    enabled: bool = False
    model_name: str = ""
    prompt_version: str = ""
    facts_hash: str = ""
    schema_version: str = SCHEMA_VERSION
    retry_count: int = 0
    fallback_used: bool = False
    accepted: int = 0
    rejected: int = 0
    errors: int = 0
    rejection_reasons: dict[str, int] = Field(default_factory=dict)
