"""LLM prose layer: facts in, structured prose out, deterministic fallback."""

from __future__ import annotations

from .fallback import card_fallback, conversational_fallback, report_fallback
from .facts import project_for_access, seal_facts
from .humanize import humanize
from .schemas import (
    CardProse,
    ChatAnswer,
    ConversationalPalmProse,
    ConversationalProse,
    HoraryFacts,
    HoraryProse,
    PalmFacts,
    PalmProse,
    QuestionFacts,
    QuestionProse,
    ReportFacts,
    ReportProse,
)
from .validate import validate_prose_against_facts

__all__ = [
    "humanize",
    "project_for_access",
    "seal_facts",
    "validate_prose_against_facts",
    "card_fallback",
    "conversational_fallback",
    "report_fallback",
    "CardProse",
    "ChatAnswer",
    "ConversationalPalmProse",
    "ConversationalProse",
    "HoraryFacts",
    "HoraryProse",
    "PalmFacts",
    "PalmProse",
    "QuestionFacts",
    "QuestionProse",
    "ReportFacts",
    "ReportProse",
]
