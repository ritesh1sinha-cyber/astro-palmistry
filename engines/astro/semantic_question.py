#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared MiniLM question understanding — domain, house, horary topic.

Phase-1 premium path (no cloud LLM): extract *semantic* meaning from free-text
questions so Parashari / KP / Western / confluence all map the same ask to the
same house and life domain — even when wording differs.

Keywords are assist / tie-break only. When sentence-transformers or weights are
missing, falls back to keyword tables and reports method=\"keyword\".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Anchor tables (classical house meanings + life domains)
# ---------------------------------------------------------------------------

HOUSE_ANCHORS: dict[int, list[str]] = {
    1: [
        "querent self body vitality health appearance identity life force",
        "how I am seen personal strength physical condition",
    ],
    2: [
        "money wealth income savings family resources speech voice movable possessions",
        "salary earnings afford buy pay funds financial security",
    ],
    3: [
        "siblings brother sister neighbours short travel communication documents courage",
        "writing media skills initiative short trips messages",
    ],
    4: [
        "home house property land real estate mother vehicle comfort domestic",
        "flat apartment father end of matter peace of mind",
    ],
    5: [
        "children pregnancy romance creativity pleasure speculation education intelligence",
        "baby son daughter conceive love affair artistic work",
    ],
    6: [
        "illness disease health recovery surgery enemies litigation court debt service work",
        "hospital sick heal competition daily job service",
    ],
    7: [
        "marriage spouse partner husband wife relationship divorce open enemy other party",
        "wedding business partner love commitment",
    ],
    8: [
        "inheritance death surgery chronic longevity insurance partner money hidden fear",
        "accident scandal transformation shared resources",
    ],
    9: [
        "long journey foreign abroad visa higher study religion law court luck father guru",
        "pilgrimage college degree immigration fortune dharma",
    ],
    10: [
        "career job promotion profession employer boss status fame reputation government",
        "work position raise seniority public standing mother career",
    ],
    11: [
        "gains income friends hopes wishes network profit bonus groups fulfilment",
        "wish fulfilment social circle career gains",
    ],
    12: [
        "loss expense foreign abroad hospital confinement secret enemies sleep isolation",
        "letting go spiritual retreat large animals self undoing",
    ],
}

DOMAIN_ANCHORS: dict[str, list[str]] = {
    "career": [
        "career job promotion profession work employer boss status business startup",
        "will I get promoted change of job resignation new role",
    ],
    "finance": [
        "money wealth income salary savings loan investment profit financial rise",
        "will I get rich afford pay debt bonus",
    ],
    "marriage": [
        "marriage spouse partner husband wife wedding divorce relationship love",
        "will I marry when will I get married",
    ],
    "children": [
        "children pregnancy baby son daughter conceive childbirth education of child",
        "will I have a child speech of child",
    ],
    "health": [
        "health illness disease recovery surgery hospital sick heal chronic",
        "will I recover from illness",
    ],
    "property": [
        "property house home land flat real estate vehicle mother domestic",
        "will I buy a house",
    ],
    "travel": [
        "travel abroad foreign visa relocation immigration journey onsite settle overseas",
        "will I go abroad",
    ],
    "spiritual": [
        "spiritual meditation dharma religion philosophy detachment meaning purpose",
    ],
    "personality": [
        "personality character temperament mind intellect who am I identity",
    ],
    "legal": [
        "court litigation lawsuit legal case dispute bail win the case",
    ],
    "education": [
        "exam study education college university degree admission course result",
    ],
    "speech": [
        "speech stammer stutter voice speak communication teeth",
    ],
    "current": [
        "right now current period last six months recent past present window",
        "how have the last months been where do I stand now",
    ],
}

# Horary / client_question topic keys (must match TOPIC_BHAVAS / TOPIC_KEYWORDS)
TOPIC_ANCHORS: dict[str, list[str]] = {
    "disease_cure": ["will the disease be cured recovery heal get well remission"],
    "disease": ["disease illness sickness diagnosis what is wrong with health"],
    "recovery": ["recover recovery cure heal get well after surgery"],
    "children": ["child children pregnancy baby son daughter conceive"],
    "marriage": ["marriage marry wedding spouse husband wife relationship"],
    "career": ["career job promotion profession work employer boss business"],
    "health": ["health hospital surgery operation sick"],
    "finance": ["money finance loan wealth investment property income"],
    "travel": ["travel trip foreign abroad visa relocation journey"],
    "education": ["exam study education college university course degree"],
    "litigation": ["court litigation lawsuit legal case win the case dispute"],
    "general": ["general life question outcome of the matter"],
}

# Map semantic domain → default primary house (classical)
DOMAIN_PRIMARY_HOUSE: dict[str, int] = {
    "career": 10, "finance": 2, "marriage": 7, "children": 5,
    "health": 6, "property": 4, "travel": 9, "spiritual": 12,
    "personality": 1, "legal": 6, "education": 9, "speech": 2,
    "current": 1, "general": 1,
}

TOPIC_TO_DOMAIN: dict[str, str] = {
    "disease": "health", "disease_cure": "health", "recovery": "health",
    "litigation": "legal", "job": "career", "children": "children",
    "marriage": "marriage", "career": "career", "health": "health",
    "finance": "finance", "travel": "travel", "education": "education",
    "property": "property", "general": "general",
}

# question_answer.Topic keys ↔ semantic domain / house
QA_TOPIC_BY_DOMAIN: dict[str, str] = {
    "career": "promotion",  # refined further by text
    "finance": "money",
    "property": "property",
    "travel": "foreign",
    "health": "health",
    "education": "study",
    "marriage": "general",
    "children": "general",
}


# ---------------------------------------------------------------------------
# User-selectable life area (frontend dropdown, both horary and "ask your
# chart"). Free text stays primary — a specific word in the question always
# wins over the dropdown — but when wording is vague ("how are things
# looking?") the dropdown gives every engine a real signal instead of a
# guess. One shared list keeps the three question engines (natal, Vedic
# horary, Western horary) and the frontend from drifting out of sync.
# ---------------------------------------------------------------------------
LIFE_AREAS: list[tuple[str, str]] = [
    ("", "Let it work out the area from your question"),
    ("career", "Job / career"),
    ("promotion", "Promotion or raise"),
    ("business", "Business / self-employment"),
    ("finance", "Money / wealth"),
    ("property", "Property / home"),
    ("marriage", "Marriage / relationship"),
    ("children", "Children"),
    ("education", "Education / study"),
    ("health", "Health"),
    ("travel", "Foreign travel / relocation"),
    ("legal", "Legal / court matter"),
    ("general", "Something else"),
]

# area -> question_answer.py Topic key
AREA_TO_QA_TOPIC: dict[str, str] = {
    "career": "job_change", "promotion": "promotion", "business": "business",
    "finance": "money", "property": "property", "marriage": "marriage",
    "children": "children", "education": "study", "health": "health",
    "travel": "foreign", "legal": "legal",
}

# area -> horary_precompute.py TOPIC_KEYWORDS key
AREA_TO_HORARY_TOPIC: dict[str, str] = {
    "career": "career", "promotion": "career", "business": "career",
    "finance": "finance", "property": "finance", "marriage": "marriage",
    "children": "children", "education": "education", "health": "health",
    "travel": "travel", "legal": "general",
}

# area -> classical house, for western_horary_rules.py's scoring bias
AREA_TO_HOUSE: dict[str, int] = {
    "career": 10, "promotion": 10, "business": 10, "finance": 2,
    "property": 4, "marriage": 7, "children": 5, "education": 9,
    "health": 6, "travel": 9, "legal": 9,
}

# area -> semantic DOMAIN_ANCHORS key (promotion/business fold into career)
AREA_TO_DOMAIN: dict[str, str] = {
    "career": "career", "promotion": "career", "business": "career",
    "finance": "finance", "property": "property", "marriage": "marriage",
    "children": "children", "education": "education", "health": "health",
    "travel": "travel", "legal": "legal", "general": "general",
}

# Valid area keys the frontend may send (empty string = auto)
VALID_AREAS = frozenset(k for k, _ in LIFE_AREAS if k)


def normalize_area(area: str) -> str:
    a = (area or "").strip().lower()
    return a if a in VALID_AREAS else ""


@dataclass
class SemanticRoute:
    question: str
    domain: str
    primary_house: int
    houses: list[int] = field(default_factory=list)
    topic: str = "general"
    method: str = "keyword"  # minilm | keyword
    domain_score: float = 0.0
    house_score: float = 0.0
    topic_score: float = 0.0
    house_scores: dict[int, float] = field(default_factory=dict)
    degraded: bool = False


_ENGINE = None
_ENGINE_FAILED = False


def _ensure_fallback() -> None:
    try:
        import semantic_fallback
        semantic_fallback.install()
    except Exception:
        pass


def have_minilm() -> bool:
    try:
        import semantic_fallback
        return not semantic_fallback.degraded()
    except Exception:
        try:
            from local_models import is_model_ready, MINILM_DIR
            return bool(is_model_ready(MINILM_DIR))
        except Exception:
            return False


def _model():
    """Lazy MiniLM loader shared across callers."""
    global _ENGINE, _ENGINE_FAILED
    if _ENGINE is not None:
        return _ENGINE
    if _ENGINE_FAILED:
        return None
    _ensure_fallback()
    try:
        from local_models import load_sentence_transformer
        import numpy as np

        model = load_sentence_transformer()
        house_emb: dict[int, Any] = {}
        for h, anchors in HOUSE_ANCHORS.items():
            house_emb[h] = model.encode(anchors, normalize_embeddings=True)
        domain_emb: dict[str, Any] = {}
        for dom, anchors in DOMAIN_ANCHORS.items():
            domain_emb[dom] = model.encode(anchors, normalize_embeddings=True)
        topic_emb: dict[str, Any] = {}
        for topic, anchors in TOPIC_ANCHORS.items():
            topic_emb[topic] = model.encode(anchors, normalize_embeddings=True)
        _ENGINE = {
            "model": model, "np": np,
            "house": house_emb, "domain": domain_emb, "topic": topic_emb,
            "degraded": not have_minilm(),
        }
        return _ENGINE
    except Exception as exc:  # noqa: BLE001
        print(f"[semantic_question] MiniLM unavailable: {type(exc).__name__}: {exc}",
              flush=True)
        _ENGINE_FAILED = True
        return None


def _best_key(emb, table: dict, np) -> tuple[Any, float]:
    best_k, best_sc = None, -1.0
    for k, amat in table.items():
        sc = float(np.max(amat @ emb))
        if sc > best_sc:
            best_sc, best_k = sc, k
    return best_k, best_sc


def _keyword_houses(q: str) -> list[int]:
    """Assist table — same vocabulary as client_question_engine.HOUSE_KEYWORDS."""
    from client_question_engine import HOUSE_KEYWORDS
    ql = q.lower()
    hits: list[tuple[int, int]] = []
    for h, kws in HOUSE_KEYWORDS.items():
        n = sum(1 for kw in kws if kw in ql)
        if n:
            hits.append((h, n))
    hits.sort(key=lambda x: (-x[1], x[0]))
    return [h for h, _ in hits]


def _keyword_topic(q: str) -> str:
    try:
        from horary_precompute import detect_topic as _kw_topic
        # Avoid recursion if we patch detect_topic — call keyword body directly
        from horary_precompute import TOPIC_KEYWORDS
        ql = q.lower()
        priority = ["disease_cure", "disease", "children", "marriage", "career",
                    "health", "finance", "travel", "education", "litigation"]
        for topic in priority:
            keywords = TOPIC_KEYWORDS.get(topic, [])
            if any(kw in ql for kw in keywords):
                return topic
        # litigation keywords live in intent elsewhere
        if any(w in ql for w in ("court", "lawsuit", "litigation", "legal case")):
            return "litigation"
        return "general"
    except Exception:
        return "general"


def route(question: str, *, area: str = "", min_score: float = 0.28) -> SemanticRoute:
    """Map free text (+ optional life-area dropdown) → domain / houses / topic.

    When the reader picks an area from the dropdown, that area wins the domain,
    primary house and horary topic — the free-text question still refines the
    read inside that area. An explicit house number in the wording (handled by
    callers such as question_answer.classify) is the only stronger signal.
    """
    q = (question or "").strip()
    area = normalize_area(area)
    if not q and not area:
        return SemanticRoute(question="", domain="general", primary_house=1,
                             houses=[1], topic="general", method="keyword",
                             degraded=True)

    eng = _model()
    kw_houses = _keyword_houses(q) if q else []
    kw_topic = _keyword_topic(q) if q else "general"

    if eng is None:
        primary = kw_houses[0] if kw_houses else DOMAIN_PRIMARY_HOUSE.get(
            TOPIC_TO_DOMAIN.get(kw_topic, "general"), 1)
        houses = kw_houses[:3] or [primary]
        domain = TOPIC_TO_DOMAIN.get(kw_topic, "general")
        if domain == "general" and primary:
            for d, h in DOMAIN_PRIMARY_HOUSE.items():
                if h == primary and d not in ("current", "general"):
                    domain = d
                    break
        topic = kw_topic
        if area:
            domain = AREA_TO_DOMAIN.get(area, domain)
            primary = AREA_TO_HOUSE.get(area, primary)
            topic = AREA_TO_HORARY_TOPIC.get(area, topic)
            houses = [primary] + [h for h in houses if h != primary]
        return SemanticRoute(
            question=q, domain=domain, primary_house=primary, houses=houses[:4],
            topic=topic, method="keyword", degraded=True)

    np = eng["np"]
    emb = eng["model"].encode([q or area or "general"],
                              normalize_embeddings=True)[0]
    domain, d_sc = _best_key(emb, eng["domain"], np)
    house, h_sc = _best_key(emb, eng["house"], np)
    topic, t_sc = _best_key(emb, eng["topic"], np)

    # Full house score vector for diagnostics / confluence
    house_scores = {
        h: float(np.max(amat @ emb)) for h, amat in eng["house"].items()
    }
    ranked = sorted(house_scores, key=lambda h: -house_scores[h])

    # Keyword assist: do not let a weak embedding steal the house from a clear lexical hit
    # (e.g. "promotion" → H10). Prefer keyword house when scores are close or semantic is soft.
    # Strong single-token markers always win (avoids MiniLM / noisy fake-encoder drift).
    _STRONG = (
        (10, "career", (
            "promotion", "promoted", "raise", "employer", "boss",
            "hike", "increment", "salary increase", "pay rise", "appraisal",
        )),
        (7, "marriage", ("marriage", "wedding", "spouse", "husband", "wife")),
        (5, "children", ("pregnancy", "conceive", "childbirth")),
        (4, "property", ("real estate", "apartment", "property purchase")),
        (9, "travel", ("visa", "immigration", "abroad study")),
    )
    ql = q.lower()
    # Skip strong-token override when the reader already named the area —
    # otherwise "promotion" inside a vague children question could steal H10.
    if not area:
        for h_force, d_force, terms in _STRONG:
            if any(t in ql for t in terms):
                house, h_sc = h_force, max(float(h_sc or 0), 0.55)
                domain, d_sc = d_force, max(float(d_sc or 0), 0.55)
                if h_force not in ranked:
                    ranked.insert(0, h_force)
                break
    if kw_houses and not area:
        kw_h = kw_houses[0]
        kw_sc = float(house_scores.get(kw_h, 0.0))
        if kw_h != house:
            if h_sc < 0.50 or kw_sc + 0.08 >= h_sc:
                house = kw_h
                h_sc = max(h_sc, kw_sc)
        for h in kw_houses:
            if h not in ranked[:4]:
                ranked.insert(0, h)

    if t_sc < min_score and kw_topic != "general":
        topic = kw_topic
    if d_sc < min_score:
        domain = TOPIC_TO_DOMAIN.get(topic, domain or "general")

    # Align domain with house when topic is general
    if domain in ("general", None) or d_sc < min_score:
        domain = next(
            (d for d, h0 in DOMAIN_PRIMARY_HOUSE.items()
             if h0 == house and d not in ("current", "general")),
            TOPIC_TO_DOMAIN.get(topic, "general"))

    primary = int(house or DOMAIN_PRIMARY_HOUSE.get(domain, 1))
    houses = []
    for h in ranked:
        if house_scores[h] >= min_score or h in kw_houses[:2] or h == primary:
            houses.append(h)
        if len(houses) >= 4:
            break
    if primary not in houses:
        houses = [primary] + houses
    houses = list(dict.fromkeys(houses))[:4]

    # Dropdown area is an explicit reader choice — pin domain / house / topic
    # to it. Free text still shaped the ranking above for supporting houses.
    if area:
        domain = AREA_TO_DOMAIN.get(area, domain)
        primary = AREA_TO_HOUSE.get(area, primary)
        topic = AREA_TO_HORARY_TOPIC.get(area, topic)
        houses = [primary] + [h for h in houses if h != primary]
        houses = list(dict.fromkeys(houses))[:4]
        d_sc = max(float(d_sc or 0), 0.9)
        h_sc = max(float(h_sc or 0), 0.9)
        t_sc = max(float(t_sc or 0), 0.9)

    return SemanticRoute(
        question=q,
        domain=str(domain or "general"),
        primary_house=primary,
        houses=houses,
        topic=str(topic or "general"),
        method="keyword" if eng.get("degraded") else "minilm",
        domain_score=float(d_sc or 0),
        house_score=float(h_sc or 0),
        topic_score=float(t_sc or 0),
        house_scores=house_scores,
        degraded=bool(eng.get("degraded")),
    )


def assign_domain(text: str) -> str:
    return route(text).domain


def assign_house(text: str) -> int:
    return route(text).primary_house


def assign_topic(text: str) -> str:
    return route(text).topic


def status() -> dict:
    eng = _model()
    return {
        "ready": eng is not None and not (eng or {}).get("degraded"),
        "method": "minilm" if (eng and not eng.get("degraded")) else "keyword",
        "have_minilm": have_minilm(),
    }
