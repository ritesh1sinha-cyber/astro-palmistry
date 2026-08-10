"""Report-level QA gates for prediction copy."""

from qa_checks.age_context_check import age_violations
from qa_checks.duplicate_check import DuplicateTracker, exact_duplicate
from qa_checks.grammar_check import fix_grammar
from qa_checks.health_safety_check import health_violations
from qa_checks.report_diversity import ReportDiversityGate
from qa_checks.semantic_similarity import semantic_too_similar
from qa_checks.specificity import is_specific_enough, specificity_score
from qa_checks.unsupported_claims import unsupported_event_detected

__all__ = [
    "DuplicateTracker",
    "ReportDiversityGate",
    "age_violations",
    "exact_duplicate",
    "fix_grammar",
    "health_violations",
    "is_specific_enough",
    "semantic_too_similar",
    "specificity_score",
    "unsupported_event_detected",
]
