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
SCHEMA_VERSION = "1.0"
PROMPT_VERSIONS = {
    "full_report": "REPORT_PROSE_PROMPT_V1",
    "user_question": "QUESTION_PROSE_PROMPT_V1",
    "horary": "HORARY_PROSE_PROMPT_V1",
    "palm": "PALM_PROSE_PROMPT_V1",
    "chat": "CHAT_PROSE_PROMPT_V1",
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


class CardFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    area: str
    label: str = ""
    kind: Kind = "promise"
    status: str = "insufficient_evidence"
    activation_status: str = "inactive"
    confidence: Confidence = "low"
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
    # Paid-only fields — stripped by project_for_access("free")
    wealth_sub: list[dict[str, Any]] = Field(default_factory=list)
    remedy_eligible: bool = False
    approved_remedies: list[str] = Field(default_factory=list, max_length=3)
    allowed_planets: list[str] = Field(default_factory=list, max_length=8)
    allowed_dates: list[str] = Field(default_factory=list, max_length=12)


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
    access: Literal["free", "paid"] = "free"
    cards: list[CardFacts] = Field(default_factory=list)
    dashboard_buckets: dict[str, list[str]] = Field(default_factory=dict)
    timing_windows: list[WindowFact] = Field(default_factory=list, max_length=8)


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
    allowed_planets: list[str] = Field(default_factory=list, max_length=8)
    allowed_dates: list[str] = Field(default_factory=list, max_length=12)


class HoraryLaneFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lane: Literal["vedic", "western"] = "vedic"
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
    label: str = ""
    confidence: Confidence = "low"
    score: float = 0.0
    contradicted: bool = False
    favourable: bool = False
    lanes: list[HoraryLaneFact] = Field(default_factory=list)
    allowed_dates: list[str] = Field(default_factory=list, max_length=8)


class PalmAspectFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aspect: str
    direction: Direction = "mixed"
    confidence: Confidence = "low"
    signal_ids: list[str] = Field(default_factory=list, max_length=12)
    point_ids: list[str] = Field(default_factory=list, max_length=8)
    semantic_tags: list[str] = Field(default_factory=list, max_length=6)
    semantic_summary: str = Field(default="", max_length=220)
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
    access: Literal["free", "paid"] = "free"
    dominant_hand: str = "right"
    photo_grade: str = "fair"
    aspects: list[PalmAspectFacts] = Field(default_factory=list)
    future_windows: list[dict[str, Any]] = Field(default_factory=list, max_length=6)
    special_mark_ids: list[str] = Field(default_factory=list, max_length=8)


# ---------------------------------------------------------------------------
# Prose models (LLM output — language only, no prediction authority)
# ---------------------------------------------------------------------------
class CardProse(BaseModel):
    """Language-only card prose. Authoritative statuses stay in CardFacts."""
    model_config = ConfigDict(extra="forbid")
    area: str
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
    cards: list[CardProse] = Field(default_factory=list, max_length=12)


class QuestionProse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    opening: str = Field(..., min_length=8, max_length=280)
    answer: str = Field(..., min_length=8, max_length=420)
    timing: str = Field(default="", max_length=220)
    action: str = Field(default="", max_length=180)


class HoraryProse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lead: str = Field(..., min_length=8, max_length=280)
    verdict_line: str = Field(..., min_length=8, max_length=220)
    why: str = Field(default="", max_length=280)
    action: str = Field(default="", max_length=180)


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
    answer: str = Field(..., min_length=4, max_length=600)
    used_fact_ids: list[str] = Field(default_factory=list, max_length=12)
    out_of_scope: bool = False


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
