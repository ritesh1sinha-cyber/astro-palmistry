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
        r"relationships?", r"life\s+partner", r"(?<!business )partner", r"spouse", r"husband", r"wife",
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
        r"anxi\w*", r"anxious", r"depress\w*", r"stress\w*", r"mental\s+health", r"panic", r"insomnia",
        r"can'?t\s+sleep", r"tired", r"fatigue", r"headache", r"pain", r"weight", r"allerg\w*",
    ),
    "career_profession": (
        r"jobs?", r"career", r"promotion", r"promoted", r"salary", r"hike", r"appraisal",
        r"interview", r"resign\w*", r"unemployed", r"naukri", r"profession", r"business",
        r"startup", r"business\s+partner", r"self\s*-?\s*employ\w*", r"udyogam", r"vyapar",
    ),
    "wealth_finances": (
        r"money", r"wealth", r"income", r"debts?", r"loans?", r"savings?", r"sav(?:e|es|ed|ing)", r"invest\w*",
        r"afford\w*", r"budgets?", r"lottery", r"rich", r"financ\w*", r"paisa", r"paise", r"dhan", r"dabbu",
    ),
    "property_assets": (
        r"buy\s+(?:a\s+|an\s+|my\s+)?(?:house|flat|home|property|land|plot|car|vehicle|bike)",
        r"(?:sell|selling|rent|renting)\s+(?:a\s+|my\s+|the\s+)?(?:house|flat|home|property|land|plot|car|vehicle)",
        r"property", r"vehicle", r"cars?", r"bikes?", r"scooter", r"real\s+estate", r"own\s+(?:a\s+)?(?:house|home|flat)", r"ghar",
    ),
    "foreign_relocation": (
        r"abroad", r"foreign", r"visa", r"immigrat\w*", r"relocat\w*", r"settle\s+(?:in|abroad)",
        r"overseas", r"videsh", r"pardes",
        r"(?:to|in|for)\s+(?:the\s+)?(?:usa|u\.s\.a?|uk|u\.k\.|america|canada|australia|germany|dubai|uae|singapore|europe|london|new\s+zealand|japan|france|ireland|netherlands|gulf|qatar|saudi)",
    ),
    "education_learning": (
        r"exams?", r"stud(?:y|ies|ying)", r"college", r"admission", r"degree", r"scholarship",
        r"neet", r"jee", r"upsc", r"board\s+exams?", r"padhai", r"streams?", r"courses?",
    ),
    "litigation_disputes": (
        r"court", r"lawsuit", r"litigation", r"legal", r"police", r"lawyer", r"verdict", r"bail",
        r"disputes?", r"settlement", r"(?:divorce|criminal|civil|property)\s+case", r"case\s+(?:against|filed)",
        r"enem(?:y|ies)", r"custody", r"alimony", r"mediation", r"arbitration", r"legal\s+notice",
        r"consumer\s+complaint",
    ),
    "speech_neurology": (
        r"speech", r"stammer\w*", r"stutter\w*", r"autis\w*", r"dyslexi\w*", r"adhd", r"neurolog\w*",
        r"not\s+speaking", r"speak\s+(?:late|clearly)", r"memory\s+loss", r"epilep\w*",
    ),
}

# Never decisive on its own against a real subject ("my future career" is a career question).
_GENERAL = re.compile(
    r"(?<![a-z0-9])(?:peace\s+of\s+mind|mental\s+peace|inner\s+peace|purpose|spiritual\w*|meditat\w*|"
    r"right\s+path|my\s+future|bad\s+time|luck|good\s+time|destiny|karma)(?![a-z0-9])")

# "my son / daughter / kids ..." is about the children whatever else is said.
_ABOUT_CHILD = re.compile(r"(?<![a-z0-9])(?:my|our)\s+(?:son|daughter|child|children|kids?|baby)(?![a-z0-9])")

# Two areas named: which one the question is really about.
_PAIR_WINS = {
    frozenset({"education_learning", "foreign_relocation"}): "foreign_relocation",   # study abroad
    frozenset({"marriage_relationship", "litigation_disputes"}): "litigation_disputes",  # divorce case
    frozenset({"property_assets", "litigation_disputes"}): "litigation_disputes",    # property dispute
    frozenset({"career_profession", "litigation_disputes"}): "litigation_disputes",  # case at work
    frozenset({"wealth_finances", "litigation_disputes"}): "litigation_disputes",    # money dispute
    frozenset({"property_assets", "wealth_finances"}): "property_assets",            # sell a house for money
}

_COMPILED = {
    area: re.compile(r"(?<![a-z0-9])(?:" + "|".join(pats) + r")(?![a-z0-9])")
    for area, pats in _AREAS.items()
}


def keyword_domain(question: str) -> str:
    """The one area the question names, or ``""`` when it names none or cannot be told apart."""
    q = re.sub(r"\s+", " ", (question or "").lower()).strip()
    if not q:
        return ""
    named = {area for area, rx in _COMPILED.items() if rx.search(q)}
    if _ABOUT_CHILD.search(q):
        if "litigation_disputes" in named:
            return "litigation_disputes"
        if named - {"children_progeny"} == {"property_assets"} and re.search(r"transfer|gift|inherit", q):
            return "property_assets"
        return "children_progeny"
    if named == {"property_assets", "wealth_finances"} and re.search(r"save|saving|afford|budget", q):
        return "wealth_finances"
    if len(named) == 1:
        return next(iter(named))
    if len(named) == 2 and frozenset(named) in _PAIR_WINS:
        return _PAIR_WINS[frozenset(named)]
    if not named and _GENERAL.search(q):
        return "general_destiny"
    return ""
