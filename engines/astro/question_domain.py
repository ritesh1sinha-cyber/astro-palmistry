"""Which area of life a question is about, decided by plain words before any model.

The planner model and the MiniLM router are both soft: "when will I get a
girlfriend" came back as *health* (planner) and *children* (router), and the
reader was given a health reading. When a question names its subject outright
we do not need a guess, so this is a small, auditable word list.

``keyword_domain`` returns a DOMAINS_CONFIG key only when exactly one area is
named. Anything mixed ("a job abroad", "my girlfriend's health") or unnamed
returns ``""`` and the softer routers decide, as before.
"""
from __future__ import annotations

import re

# Whole-word / whole-phrase patterns, matched on lower-cased text. English plus the
# Roman-script Hindi and Telugu a reader is likely to type.
_AREAS: dict[str, tuple[str, ...]] = {
    "marriage_relationship": (
        r"girl\s*friends?", r"boy\s*friends?", r"gf", r"bf", r"crush", r"soul\s*mates?",
        r"dating", r"date\s+someone", r"love\s+life", r"in\s+love", r"fall\s+in\s+love",
        r"love\s+marriage", r"propos(?:e|al|als)", r"my\s+ex", r"ex\s*-?\s*(?:girl|boy)friend",
        r"get\s+back\s+(?:together|with)", r"break\s*-?\s*up", r"patch\s*-?\s*up",
        r"relationships?", r"life\s+partner", r"partner", r"spouse", r"husband", r"wife",
        r"marriage", r"marry", r"married", r"engagement", r"divorce", r"affair",
        r"meet\s+(?:someone|somebody|my\s+match)", r"find\s+(?:someone|somebody|love|a\s+partner)",
        r"single", r"lover", r"romance", r"romantic",
        r"shaadi", r"shadi", r"vivah", r"rishta", r"rishte", r"jodi", r"pyaar", r"pyar", r"prem",
        r"premika", r"premikudu", r"pelli", r"pellam", r"bharya", r"bhartha",
        r"mil(?:egi|ega)\s+meri\s+(?:girlfriend|premika)", r"girlfriend\s+kab",
    ),
    "children_progeny": (
        r"children", r"child", r"kids?", r"baby", r"pregnan\w*", r"conceiv\w*", r"conception",
        r"progeny", r"ivf", r"santan", r"bacha", r"bachcha", r"bachche", r"pillalu", r"santhanam",
    ),
    "health_vitality": (
        r"health", r"healthy", r"disease", r"illness", r"sick", r"sickness", r"surgery",
        r"operation", r"hospital", r"medicine", r"diabet\w*", r"fever", r"injury", r"recover\w*",
        r"get\s+well", r"swasthya", r"sehat", r"bimari", r"aarogyam",
    ),
    "career_profession": (
        r"jobs?", r"career", r"promotion", r"promoted", r"salary", r"hike", r"appraisal",
        r"interview", r"resign\w*", r"unemployed", r"naukri", r"profession", r"business",
        r"startup", r"self\s*-?\s*employ\w*", r"udyogam", r"vyapar",
    ),
    "wealth_finances": (
        r"money", r"wealth", r"income", r"debts?", r"loans?", r"savings?", r"invest\w*",
        r"lottery", r"rich", r"financ\w*", r"paisa", r"paise", r"dhan", r"dabbu",
    ),
    "property_assets": (
        r"buy\s+(?:a\s+|an\s+|my\s+)?(?:house|flat|home|property|land|plot|car|vehicle|bike)",
        r"property", r"real\s+estate", r"own\s+(?:a\s+)?(?:house|home|flat)", r"ghar",
    ),
    "foreign_relocation": (
        r"abroad", r"foreign", r"visa", r"immigrat\w*", r"relocat\w*", r"settle\s+(?:in|abroad)",
        r"overseas", r"videsh", r"pardes",
    ),
    "education_learning": (
        r"exams?", r"stud(?:y|ies|ying)", r"college", r"admission", r"degree", r"scholarship",
        r"neet", r"jee", r"upsc", r"board\s+exams?", r"padhai",
    ),
    "litigation_disputes": (
        r"court", r"lawsuit", r"litigation", r"legal", r"police", r"lawyer", r"verdict",
    ),
}

_COMPILED = {
    area: re.compile(r"(?<![a-z0-9])(?:" + "|".join(pats) + r")(?![a-z0-9])")
    for area, pats in _AREAS.items()
}


def keyword_domain(question: str) -> str:
    """The one area the question names, or ``""`` when it names none or several."""
    q = re.sub(r"\s+", " ", (question or "").lower()).strip()
    if not q:
        return ""
    named = [area for area, rx in _COMPILED.items() if rx.search(q)]
    return named[0] if len(named) == 1 else ""
