"""Customer-facing report JSON schema.

Defines the ONLY data structure the HTML renderer may consume.
Internal analysis data (lane HTML, anchor logs, scoring artefacts) never enters this schema.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, validator


# ---------------------------------------------------------------------------
# Section A: Meta
# ---------------------------------------------------------------------------
class SubjectMeta(BaseModel):
    name: str = ""
    birth_date: str = ""
    birth_time: str = ""
    birth_place: str = ""
    language: str = "en"
    access: str = "free"
    generated_at: str = ""

    @validator("access")
    def _access_must_be_known(cls, v: str) -> str:  # noqa: N805
        if v not in ("free", "paid"):
            raise ValueError(f"access must be 'free' or 'paid', got {v!r}")
        return v


class LifeAreaMeta(BaseModel):
    key: str
    label: str = ""
    verdict: str = ""


class SummaryBlock(BaseModel):
    headline: str = ""
    opening: str = ""
    strengths: list[str] = Field(default_factory=list)
    watch: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Section B: Tone
# ---------------------------------------------------------------------------
class Tone(BaseModel):
    style: str = "vedic"
    chip: str = ""
    tone_label: str = ""
    tone_class: str = ""


# ---------------------------------------------------------------------------
# Section C: Life Areas (paid only)
# ---------------------------------------------------------------------------
class LifeArea(BaseModel):
    key: str = ""
    label: str = ""
    chip: str = ""
    tone_class: str = ""
    conclusion: str = ""
    astrological_basis: str = ""
    interpretation: str = ""
    outlook: str = ""
    timing: str = ""
    manifestation: str = ""
    remedy: str = ""
    transition_note: str = ""

    @validator("conclusion")
    def _conclusion_not_empty(cls, v: str) -> str:  # noqa: N805
        if not v.strip():
            raise ValueError("conclusion must not be empty")
        return v

    @validator("interpretation")
    def _interpretation_not_empty(cls, v: str) -> str:  # noqa: N805
        if not v.strip():
            raise ValueError("interpretation must not be empty")
        return v


# ---------------------------------------------------------------------------
# Section D: Current Life State (paid only)
# ---------------------------------------------------------------------------
class LifeState(BaseModel):
    what_is_on_your_mind: list[str] = Field(default_factory=list)
    why_this_period_feels_this_way: str = ""
    family_note: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Section E: Timing & Outlook
# ---------------------------------------------------------------------------
class CurrentPeriod(BaseModel):
    vedic_period: str = ""
    phase_label: str = ""
    phase_description: str = ""


class FutureOutlook(BaseModel):
    recent_months: str = ""
    near_term: str = ""
    longer_term: str = ""


# ---------------------------------------------------------------------------
# Section F: Closing Guidance (paid only)
# ---------------------------------------------------------------------------
class ClosingGuidance(BaseModel):
    final_guidance: str = ""


# ---------------------------------------------------------------------------
# Top-level customer report JSON
# ---------------------------------------------------------------------------
class CustomerReport(BaseModel):
    """The single source of truth for the customer-facing report.

    HTML renderer receives ONLY this object. Any field that is empty/missing
    means the section should not render — never invent content.
    """
    schema_version: str = "2.0"
    meta: SubjectMeta = Field(default_factory=SubjectMeta)
    summary: SummaryBlock = Field(default_factory=SummaryBlock)
    tone: Tone = Field(default_factory=Tone)
    life_areas: list[LifeArea] = Field(default_factory=list)
    life_state: LifeState = Field(default_factory=LifeState)
    current_period: CurrentPeriod = Field(default_factory=CurrentPeriod)
    future_outlook: FutureOutlook = Field(default_factory=FutureOutlook)
    closing_guidance: ClosingGuidance = Field(default_factory=ClosingGuidance)

    @validator("life_areas")
    def _no_duplicate_areas(cls, v: list) -> list:  # noqa: N805
        keys = [a.key for a in v]
        dupes = [k for k in keys if keys.count(k) > 1]
        if dupes:
            raise ValueError(f"Duplicate life area keys: {set(dupes)}")
        return v
