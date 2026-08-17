"""Current life state — what may be occupying the person right now.

The free half of the conversational report has to earn the unlock: the reader
should recognise their own present situation before they pay for the life-area
detail. This module produces that block.

It makes no astrological judgement of its own. Every level it reports is read
off the canonical ``CardFacts`` the confluence engine already produced, so the
"what may be on your mind" block and the paid life-area cards can never
disagree with each other. Scores stay inside this module: the facts that leave
it carry banded levels and a controlled vocabulary of experience phrases, so
the LLM has words to choose from and no numbers to print.
"""

from __future__ import annotations

from typing import Any, Iterable

from .schemas import DomainStateFact, LifeStateFacts, MindTopicFact

# Where a canonical card sits on support / pressure, before banding.
_STATUS_WEIGHT = {
    "strongly_supported": 0.92, "strongly_indicated": 0.92,
    "supported": 0.74, "indicated": 0.74,
    "mixed": 0.5,
    "weak": 0.28,
    "insufficient_evidence": 0.12,
}
_ACTIVATION_WEIGHT = {
    "strongly_active": 1.0, "active": 0.8, "mixed": 0.55,
    "weak": 0.35, "inactive": 0.12, "insufficient_evidence": 0.12,
}
_BAND_ORDER = {"none": 0, "low": 1, "moderate": 2, "high": 3, "very_high": 4}

# Areas where the reading describes attention and routine, never an outcome.
_OUTCOME_RESTRICTED = frozenset({"health", "parents", "children"})

_AREA_LABELS = {
    "self": "You",
    "parents": "Parents & Family Responsibility",
    "siblings": "Siblings & Close Circle",
    "love": "Relationships & Partnership",
    "children": "Children",
    "career": "Work & Career",
    "learning": "Learning & Luck",
    "money": "Money",
    "home": "Home & Family",
    "health": "Health & Energy",
    "inner": "Inner Peace & Spirituality",
}
# The report cards, the question router and the canonical areas each name the
# same part of life slightly differently. An area whose name we fail to
# recognise loses its experience words and drops out of the block silently, so
# every known spelling resolves to one vocabulary key.
_AREA_ALIASES = {
    "profession": "career", "work": "career", "business": "career",
    "wealth": "money", "finance": "money", "debt": "money",
    "relationship": "love", "marriage": "love", "partnership": "love",
    "family": "home", "property": "home", "parents": "parents",
    "education": "learning", "study": "learning",
    "wellbeing": "health",
    "strengths": "self", "reputation": "self",
    "spiritual": "inner", "emotional": "inner", "mind": "inner",
}


def _vocab_key(area: str) -> str:
    key = str(area or "").strip().lower().replace("-", "_").replace(" ", "_")
    return _AREA_ALIASES.get(key, key)

# Controlled vocabulary. The LLM may express these in its own sentences; it may
# not invent a different experience for an area.
_EXPERIENCE = {
    "self": {
        "pressure": ("questions about your own direction", "pressure to prove yourself",
                     "wanting change while protecting stability"),
        "support": ("a clearer sense of your own direction", "confidence in your own judgement"),
        "mixed": ("reassessment of what you want rather than a simple win or loss",),
    },
    "parents": {
        "pressure": ("concern about a parent's wellbeing", "greater family responsibility"),
        "support": ("family support", "closer involvement with your parents"),
        "mixed": ("care for your parents alongside your other responsibilities",),
    },
    "siblings": {
        "pressure": ("responsibility inside the family", "needing to keep the peace"),
        "support": ("support from those closest to you", "easier give and take at home"),
        "mixed": ("family closeness alongside the effort of holding it together",),
    },
    "home": {
        "pressure": ("responsibility at home", "wanting the household to feel settled",
                     "decisions about where and how you live"),
        "support": ("more ease at home", "scope to settle house and family matters"),
        "mixed": ("home decisions alongside practical limits",),
    },
    "love": {
        "pressure": ("expectations in a close relationship", "the need for clearer conversation",
                     "emotional uncertainty"),
        "support": ("closer connection", "more goodwill than there has been", "steadier footing"),
        "mixed": ("connection alongside the work of managing expectations",),
    },
    "children": {
        "pressure": ("concern about a child's wellbeing or progress", "more parenting responsibility"),
        "support": ("growth at home", "support around children"),
        "mixed": ("care and responsibility around children alongside real openings",),
    },
    "career": {
        "pressure": ("more responsibility than recognition", "uncertainty about direction",
                     "wanting to be seen for the work you do"),
        "support": ("forward movement", "more visibility", "a professional opening"),
        "mixed": ("progress alongside responsibility", "wanting change while protecting stability"),
    },
    "learning": {
        "pressure": ("study pressure", "decisions about what to learn next"),
        "support": ("real progress in learning", "sharper focus"),
        "mixed": ("progress that asks for sustained effort",),
    },
    "money": {
        "pressure": ("financial caution", "concern about stability", "heavier money decisions"),
        "support": ("improving cash flow", "a chance to strengthen savings"),
        "mixed": ("opportunity alongside the need for careful judgement",),
    },
    "health": {
        "pressure": ("more attention to routine", "concern about your own wellbeing",
                     "the need for rest and consistency"),
        "support": ("scope to improve your routine", "benefit from steady preventive care"),
        "mixed": ("taking wellbeing more seriously without assuming anything medical",),
    },
    "inner": {
        "pressure": ("uncertainty", "decision fatigue", "wanting reassurance"),
        "support": ("clarity", "renewed confidence", "steadier ground"),
        "mixed": ("reassessment rather than a simple good or bad phase",),
    },
}


def _level(value: float) -> str:
    if value >= 0.78:
        return "very_high"
    if value >= 0.58:
        return "high"
    if value >= 0.35:
        return "moderate"
    if value > 0.12:
        return "low"
    return "none"


def _get(card: Any, key: str, default: Any = "") -> Any:
    if isinstance(card, dict):
        return card.get(key, default)
    return getattr(card, key, default)


def _weights(card: Any, needs_care: frozenset[str]) -> tuple[float, float, float]:
    """Support, pressure and activation for one canonical card."""
    status = str(_get(card, "status", "") or "").lower()
    activation = str(_get(card, "activation_status", "") or "").lower()
    kind = str(_get(card, "kind", "promise") or "promise").lower()
    direction = str(_get(card, "direction", "") or "").lower()
    support_n = int(_get(card, "support_n", 0) or 0)
    caution_n = int(_get(card, "caution_n", 0) or 0)

    act = _ACTIVATION_WEIGHT.get(activation, 0.12)
    base = _STATUS_WEIGHT.get(status, 0.12)
    # An inactive theme is still real, just quieter — hence the floor.
    graded = base * (0.35 + 0.65 * act)

    if kind == "challenge":
        support, pressure = 0.0, graded
    else:
        support, pressure = graded, 0.0
        if direction in ("caution", "down"):
            pressure = max(pressure * 0.4, 0.62 * act)
        elif direction == "mixed" and caution_n:
            pressure = max(pressure, 0.45 * act)
        total = support_n + caution_n
        if total:
            # Evidence pulling against a promise is felt as pressure even when
            # the verdict still reads supported.
            pressure = max(pressure, (caution_n / total) * act)
        if status in ("weak", "insufficient_evidence") and act >= 0.75:
            # Wanting movement in a live phase with nothing backing it is its
            # own kind of pressure, and it is the one readers describe most.
            pressure = max(pressure, 0.5)
    if str(_get(card, "area", "") or "") in needs_care:
        # The report's own dashboard already tells the reader this area needs
        # care. If this block disagreed, the same page would name two different
        # sets of hard areas a few paragraphs apart.
        pressure = max(pressure, 0.5)
    return support, pressure, act


def _domain_state(card: Any, needs_care: frozenset[str]) -> DomainStateFact | None:
    area = str(_get(card, "area", "") or "").strip()
    if not area:
        return None
    support, pressure, act = _weights(card, needs_care)
    support_n = int(_get(card, "support_n", 0) or 0)
    caution_n = int(_get(card, "caution_n", 0) or 0)
    agreement = str(_get(card, "agreement", "weak") or "weak").lower()
    contradiction = bool(
        (support_n and caution_n and agreement in ("weak", "insufficient"))
        or (support >= 0.45 and pressure >= 0.45)
    )

    if contradiction:
        mode = "mixed"
    elif pressure > support + 0.08:
        mode = "pressure"
    elif support > pressure + 0.08:
        mode = "support"
    else:
        mode = "mixed"
    phrases = _EXPERIENCE.get(_vocab_key(area), {}).get(mode, ())

    return DomainStateFact(
        area=area,
        label=str(_get(card, "label", "") or _AREA_LABELS.get(area, area.title()))[:80],
        activation=_level(act),                              # type: ignore[arg-type]
        pressure=_level(pressure),                           # type: ignore[arg-type]
        support=_level(support),                             # type: ignore[arg-type]
        confidence=str(_get(card, "confidence", "low") or "low"),  # type: ignore[arg-type]
        agreement=agreement if agreement in ("strong", "partial", "weak", "insufficient") else "weak",  # type: ignore[arg-type]
        contradiction=contradiction,
        experience=list(phrases)[:3],
        outcome_language_restricted=_vocab_key(area) in _OUTCOME_RESTRICTED,
    )


def _topic(d: DomainStateFact) -> MindTopicFact:
    p, a = _BAND_ORDER[d.pressure], _BAND_ORDER[d.activation]
    return MindTopicFact(
        area=d.area,
        label=d.label,
        likelihood="likely" if (p >= 3 and a >= 2) else "possible",  # type: ignore[arg-type]
        experience=list(d.experience)[:3],
    )


def _mind_now(domains: list[DomainStateFact]) -> list[MindTopicFact]:
    """The few areas most likely to be on their mind, as possibilities.

    Pressure leads, because that is what a reader recognises fastest. One slot
    is held for an area that is wide open instead: a block that only ever names
    problems reads as a warning rather than a reading, and the good news is as
    much a part of what someone is thinking about.
    """
    usable = [d for d in domains if d.experience]
    pressured = sorted(
        (d for d in usable if _BAND_ORDER[d.pressure] >= 2 and _BAND_ORDER[d.activation] >= 2),
        key=lambda d: (_BAND_ORDER[d.pressure], _BAND_ORDER[d.activation]),
        reverse=True,
    )
    openings = sorted(
        (d for d in usable
         if d not in pressured
         and _BAND_ORDER[d.activation] >= 4 and _BAND_ORDER[d.support] >= 3),
        key=lambda d: (_BAND_ORDER[d.support], _BAND_ORDER[d.activation]),
        reverse=True,
    )
    picked = pressured[:2] + openings[:1] + pressured[2:] + openings[1:]
    return [_topic(d) for d in picked[:3]]


def _themes(domains: list[DomainStateFact]) -> list[str]:
    heavy = {_vocab_key(d.area) for d in domains if _BAND_ORDER[d.pressure] >= 3}
    live = {_vocab_key(d.area) for d in domains if _BAND_ORDER[d.activation] >= 2}
    themes: list[str] = []
    if heavy:
        themes.append("responsibility")
    if "career" in heavy:
        themes.append("career_direction")
    if "money" in heavy:
        themes.append("financial_security")
    if heavy & {"parents", "children", "siblings", "home"}:
        themes.append("family_responsibility")
    if "health" in heavy:
        themes.append("wellbeing_attention")
    if "love" in heavy:
        themes.append("closeness_and_expectations")
    if "self" in heavy:
        themes.append("recognition")
    if any(d.contradiction for d in domains):
        themes.append("mixed_signals")
    if "inner" in live:
        themes.append("inner_change")
    if not themes:
        themes.append("reassessment")
    return sorted(set(themes))[:6]


def _average(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def build_life_state(
    cards: list,
    *,
    phase_tone: str = "",
    needs_care: Iterable[str] = (),
) -> LifeStateFacts:
    """Build the current-life-state block from canonical life-area cards.

    ``needs_care`` is the report's own list of areas asking for attention. It
    is passed in rather than recomputed so this block and the dashboard cannot
    name different hard areas on the same page.
    """
    care = frozenset(str(a) for a in (needs_care or ()) if a)
    domains = [d for d in (_domain_state(c, care) for c in (cards or [])) if d is not None]
    domains.sort(
        key=lambda d: (
            max(_BAND_ORDER[d.pressure], _BAND_ORDER[d.support]),
            _BAND_ORDER[d.activation],
        ),
        reverse=True,
    )
    if not domains:
        return LifeStateFacts(chapter_tone="mixed")

    top = domains[0]
    live = [d for d in domains if _BAND_ORDER[d.activation] >= 2] or domains[:3]
    band_value = {"none": 0.0, "low": 0.2, "moderate": 0.5, "high": 0.75, "very_high": 1.0}
    emotional = _average(band_value[d.pressure] for d in live)
    decision = _average(
        band_value[d.pressure] for d in live
        if _vocab_key(d.area) in ("career", "money", "home", "learning")
    )
    themes = _themes(domains)

    # Tone reads the whole page, not the first row. Ranking by the louder of
    # pressure and support leaves ties in an arbitrary order, and a chart with
    # a strongly backed area and a strongly pressured one is a mixed chapter
    # whichever of the two happens to sort first.
    heavy = any(_BAND_ORDER[d.pressure] >= 3 for d in domains)
    backed = any(_BAND_ORDER[d.support] >= 3 for d in domains)
    if (heavy and backed) or top.contradiction:
        tone = "mixed"
    elif heavy:
        tone = "pressured"
    elif backed:
        tone = "supported"
    else:
        tone = "steady"
    # A demanding running phase is part of how now feels; the card verdicts
    # alone can read calm while the phase itself is the harder part.
    if tone == "steady" and str(phase_tone or "").lower() == "demanding":
        tone = "pressured"

    return LifeStateFacts(
        chapter_tone=tone,                                   # type: ignore[arg-type]
        strongest_theme=top.area,
        strongest_theme_label=top.label,
        themes=themes,
        emotional_pressure=_level(emotional),                # type: ignore[arg-type]
        decision_pressure=_level(decision),                  # type: ignore[arg-type]
        responsibility="high" if {"responsibility", "family_responsibility"} & set(themes) else "moderate",  # type: ignore[arg-type]
        # Uncertainty is about methods that disagree, not about how busy the
        # chart is: the prose built on it tells the reader to reassess rather
        # than commit, which is only honest when something really conflicts.
        uncertainty=(
            "high" if any(d.contradiction for d in domains)
            else "moderate" if "inner_change" in themes else "low"
        ),                                                   # type: ignore[arg-type]
        domains=domains[:12],
        mind_now=_mind_now(domains),
    )
