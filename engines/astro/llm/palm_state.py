"""Current palm state — what the hands suggest may be live right now.

The free half of the palm report has to earn the unlock the same way the
astrology one does: the reader should recognise themselves before they pay for
the life-area detail. This module produces that block, plus the two-hand
contrast that is palmistry's own best trust material.

Two boundaries matter here and neither is negotiable.

Palmistry in this design has no dasha or transit clock, so nothing in this
module invents a period, an age or a date. Ages reach the model only through
``future_windows``, which is where the existing age gate can see them. And the
palm engine's own vocabulary is full of planet-named mounts and detector ids;
only plain theme and trait words cross into the facts.
"""

from __future__ import annotations

from typing import Any, Iterable

from .schemas import (
    DomainStateFact,
    HandContrastFacts,
    MindTopicFact,
    PalmStateFacts,
)

# How strongly a life aspect reads, before banding. The palm engine grades an
# aspect by how many rules matched and how many held on both hands, and photo
# quality has already capped it upstream.
_STRENGTH_WEIGHT = {
    "very strong": 0.92, "very_strong": 0.92,
    "strong": 0.85,
    "moderate": 0.55,
    "tentative": 0.3,
    "weak": 0.25,
    "none": 0.12,
}
_CONFIDENCE_WEIGHT = {"high": 0.9, "moderate": 0.6, "low": 0.3}
_BAND_ORDER = {"none": 0, "low": 1, "moderate": 2, "high": 3, "very_high": 4}

# Areas where a palm reading describes attention and routine, never an outcome.
_OUTCOME_RESTRICTED = frozenset({"health"})

_AREA_LABELS = {
    "character": "Character & Temperament",
    "mind": "Mind & Intellect",
    "love": "Relationships & Emotions",
    "career": "Career & Direction",
    "wealth": "Money & Resources",
    "health": "Health & Vitality",
    "travel": "Change & Imagination",
    "fortune": "Opportunity & Direction",
}
# The life-aspect engine, the card renderer and the LLM titles each spell some
# of these differently. An area we fail to recognise loses its experience words
# and drops out of the block in silence, so every spelling resolves to one key.
_AREA_ALIASES = {
    "money": "wealth", "finance": "wealth", "resources": "wealth",
    "profession": "career", "work": "career", "destiny": "career",
    "relationship": "love", "relationships": "love", "emotions": "love",
    "vitality": "health", "wellbeing": "health",
    "intellect": "mind", "mind_decision": "mind", "decisions": "mind",
    "temperament": "character", "self": "character", "will": "character",
    "imagination": "travel", "change": "travel",
    "luck": "fortune", "opportunity": "fortune", "social": "fortune",
}

# Controlled vocabulary. The model may express these in its own sentences; it
# may not invent a different experience for an area. Palm phrasing stays with
# what a hand can support — tendency and need, not events.
_EXPERIENCE = {
    "character": {
        "pressure": ("questions about which parts of yourself to lead with",
                     "pressure to prove what you are capable of"),
        "support": ("a clearer sense of your own way of doing things",
                    "confidence in your own judgement"),
        "mixed": ("reassessing how you want to come across rather than changing who you are",),
    },
    "mind": {
        "pressure": ("a decision you keep turning over", "mental tiredness rather than physical",
                     "wanting certainty before you commit"),
        "support": ("clearer thinking than usual", "trusting your own read of a situation"),
        "mixed": ("thinking something through in stages rather than settling it at once",),
    },
    "love": {
        "pressure": ("wanting to be understood without having to explain",
                     "the need for a clearer conversation", "guarding your feelings more than you used to"),
        "support": ("closer connection", "more warmth than there has been", "steadier footing"),
        "mixed": ("closeness alongside the work of managing expectations",),
    },
    "career": {
        "pressure": ("more responsibility than recognition", "uncertainty about direction",
                     "wanting the work to add up to something"),
        "support": ("forward movement", "more visibility for what you do",
                    "work that fits how you actually think"),
        "mixed": ("progress alongside responsibility", "wanting change while protecting stability"),
    },
    "wealth": {
        "pressure": ("careful money decisions", "wanting more security than you feel",
                     "carrying the practical side for others"),
        "support": ("steadier resources", "a chance to build rather than only manage"),
        "mixed": ("opportunity alongside the need for careful judgement",),
    },
    "health": {
        "pressure": ("more attention to routine", "energy that runs out sooner than it used to",
                     "the need for rest and consistency"),
        "support": ("scope to improve your routine", "benefit from steady, unglamorous care"),
        "mixed": ("taking your energy more seriously without assuming anything medical",),
    },
    "travel": {
        "pressure": ("restlessness with how things are", "wanting a change of scene or setting"),
        "support": ("room for movement and new surroundings", "curiosity that is worth following"),
        "mixed": ("wanting change while weighing what it would cost",),
    },
    "fortune": {
        "pressure": ("waiting for an opening that has not come yet",
                     "wanting recognition for effort already made"),
        "support": ("openings that come through people who know your work",
                    "recognition catching up with effort"),
        "mixed": ("openings that need you to ask rather than wait",),
    },
}

# Line keys the confluence engine compares across hands, in plain words.
_LINE_THEME = {
    "life": "your energy and vitality",
    "head": "the way you think and decide",
    "heart": "your emotional and relationship life",
    "fate": "your work and sense of direction",
}
# Mount keys are planet names. The trait each one stands for is the only part
# of that vocabulary a customer-facing reading may use.
_MOUNT_TRAIT = {
    "jupiter": "ambition",
    "saturn": "steadiness under responsibility",
    "apollo": "creativity",
    "sun": "creativity",
    "mercury": "communication",
    "mars": "courage under pressure",
    "venus": "warmth and closeness",
    "moon": "imagination",
}


def _vocab_key(area: str) -> str:
    key = str(area or "").strip().lower().replace("-", "_").replace(" ", "_")
    return _AREA_ALIASES.get(key, key)


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


def _get(obj: Any, key: str, default: Any = "") -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _weights(
    aspect: Any,
    *,
    demanding: str,
    latent_areas: frozenset[str],
) -> tuple[float, float, float]:
    """Support, pressure and activation for one palm life aspect.

    Palm aspects almost never come back as a caution: the engine grades how
    much evidence agrees, so a hard area shows up as thin support rather than
    as a warning. Pressure therefore comes from three places — an aspect the
    report already calls the demanding one, an aspect with little behind it,
    and a theme the other hand carries more strongly than the lived one, which
    is a need that is not getting room.
    """
    strength = str(_get(aspect, "strength", "") or "").lower()
    direction = str(_get(aspect, "direction", "") or "").lower()
    confidence = str(_get(aspect, "confidence", "moderate") or "moderate").lower()
    area = _vocab_key(str(_get(aspect, "aspect", "") or ""))
    score = float(_get(aspect, "score", 0) or 0)

    base = _STRENGTH_WEIGHT.get(strength, 0.3)
    conf = _CONFIDENCE_WEIGHT.get(confidence, 0.6)
    # The dominant hand is the present expression, so how loudly an aspect
    # reads there is the closest thing palmistry has to activation.
    act = max(base, conf)

    if direction in ("caution", "down"):
        support, pressure = 0.0, base
    elif direction in ("support", "up"):
        support, pressure = base, 0.0
    else:
        # A mixed direction is the palm engine's default, not a hedge: it only
        # says "support" once the evidence is strong. Discounting mixed heavily
        # would put every fair-photo reading below the band, so nothing could
        # ever read as going well and the block would only name problems.
        support, pressure = base * 0.85, 0.0
    if score >= 2:
        # Signs that held on both hands are the engine's own strongest claim.
        support = max(support, min(0.9, support + 0.12))

    if base <= 0.35:
        # Thin evidence in an area someone came to ask about is felt as an
        # open question, and that is what belongs in "on your mind".
        pressure = max(pressure, 0.45)
    if area in latent_areas:
        pressure = max(pressure, 0.55)
    if area and area == _vocab_key(demanding):
        # The page already tells this reader which area asks for more care. If
        # this block disagreed, one palm report would name two different hard
        # areas a few paragraphs apart.
        pressure = max(pressure, 0.62)
    return support, pressure, act


def _domain_state(
    aspect: Any,
    *,
    demanding: str,
    latent_areas: frozenset[str],
) -> DomainStateFact | None:
    area = str(_get(aspect, "aspect", "") or "").strip()
    if not area:
        return None
    support, pressure, act = _weights(
        aspect, demanding=demanding, latent_areas=latent_areas)
    score = float(_get(aspect, "score", 0) or 0)
    # `score` carries the reinforced count: how many of the signs behind this
    # aspect held on both hands.
    agreement = "strong" if score >= 2 else "partial" if score >= 1 else "weak"
    contradiction = bool(support >= 0.45 and pressure >= 0.45)

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
        label=str(_get(aspect, "title", "") or _AREA_LABELS.get(
            _vocab_key(area), area.title()))[:80],
        activation=_level(act),                              # type: ignore[arg-type]
        pressure=_level(pressure),                           # type: ignore[arg-type]
        support=_level(support),                             # type: ignore[arg-type]
        confidence=str(_get(aspect, "confidence", "low") or "low"),  # type: ignore[arg-type]
        agreement=agreement,                                 # type: ignore[arg-type]
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
    """The few themes most likely to be occupying them, as possibilities.

    Pressure leads, because that is what a reader recognises fastest. One slot
    is held for a well-supported area instead: a block that only names problems
    reads as a warning rather than a reading.
    """
    usable = [d for d in domains if d.experience]
    pressured = sorted(
        (d for d in usable if _BAND_ORDER[d.pressure] >= 2),
        key=lambda d: (_BAND_ORDER[d.pressure], _BAND_ORDER[d.activation]),
        reverse=True,
    )
    openings = sorted(
        (d for d in usable
         if d not in pressured and _BAND_ORDER[d.support] >= 2),
        key=lambda d: (_BAND_ORDER[d.support], _BAND_ORDER[d.activation]),
        reverse=True,
    )
    picked = pressured[:2] + openings[:1] + pressured[2:] + openings[1:]
    return [_topic(d) for d in picked[:3]]


def _themes(domains: list[DomainStateFact], contrast: HandContrastFacts | None) -> list[str]:
    heavy = {_vocab_key(d.area) for d in domains if _BAND_ORDER[d.pressure] >= 3}
    backed = {_vocab_key(d.area) for d in domains if _BAND_ORDER[d.support] >= 3}
    themes: list[str] = []
    if "career" in heavy:
        themes.append("career_direction")
    if "wealth" in heavy:
        themes.append("financial_security")
    if "health" in heavy:
        themes.append("wellbeing_attention")
    if "love" in heavy:
        themes.append("closeness_and_expectations")
    if "mind" in heavy:
        themes.append("decision_fatigue")
    if "character" in heavy or "fortune" in heavy:
        themes.append("recognition")
    if "travel" in heavy:
        themes.append("restlessness")
    if backed:
        themes.append("something_working")
    if contrast is not None and contrast.latent:
        themes.append("unexpressed_potential")
    if contrast is not None and contrast.developed:
        themes.append("grown_through_experience")
    if any(d.contradiction for d in domains):
        themes.append("mixed_signals")
    if not themes:
        themes.append("reassessment")
    return sorted(set(themes))[:6]


def _average(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def build_hand_contrast(confluence: Any, *, dominant_hand: str = "right") -> HandContrastFacts | None:
    """Read the two-hand comparison the confluence engine already produced.

    Only the agreement verdict and the line/mount keys are used. The engine's
    own statements are written for the card renderer and carry mount names, so
    they are not a source for this block.
    """
    if not isinstance(confluence, dict):
        return None
    lines = [x for x in (confluence.get("lines") or []) if isinstance(x, dict)]
    mounts = [x for x in (confluence.get("mounts") or []) if isinstance(x, dict)]
    if not lines and not mounts:
        return None

    steady: list[str] = []
    developed: list[str] = []
    latent: list[str] = []
    for item in lines:
        theme = _LINE_THEME.get(str(item.get("key") or "").lower())
        if not theme:
            continue
        agreement = str(item.get("agreement") or "").lower()
        if agreement == "reinforced":
            steady.append(theme)
        elif agreement == "developed":
            developed.append(theme)
        elif agreement == "latent":
            latent.append(theme)
        # "one_hand" says more about the photograph than about the person, so
        # it is left out rather than reported as a change.

    developed_traits: list[str] = []
    latent_traits: list[str] = []
    for item in mounts:
        trait = _MOUNT_TRAIT.get(str(item.get("mount") or "").lower())
        if not trait:
            continue
        statement = str(item.get("statement") or "").lower()
        # The engine phrases a dominant-hand gain as something grown into and a
        # non-dominant one as something underneath; that is the only bit of the
        # statement used, and never its wording.
        if "underlying hand" in statement or "may not" in statement or "under-used" in statement:
            latent_traits.append(trait)
        else:
            developed_traits.append(trait)

    total = len(steady) + len(developed) + len(latent)
    if not total:
        agreement_band = "partial"
    elif len(steady) >= max(1, total - 1):
        agreement_band = "high"
    elif steady:
        agreement_band = "partial"
    else:
        agreement_band = "low"

    return HandContrastFacts(
        dominant_hand=str(dominant_hand or "right"),
        agreement=agreement_band,                            # type: ignore[arg-type]
        steady=steady[:4],
        developed=developed[:4],
        latent=latent[:4],
        developed_traits=sorted(set(developed_traits))[:4],
        latent_traits=sorted(set(latent_traits))[:4],
    )


def build_palm_state(
    aspects: list,
    *,
    contrast: HandContrastFacts | None = None,
    demanding_aspect: str = "",
    photo_grade: str = "fair",
) -> PalmStateFacts:
    """Build the current-palm-state block from the sanitized palm aspects.

    ``demanding_aspect`` is the area the report itself already names as asking
    for care; it is passed in rather than recomputed so the two cannot differ.
    """
    latent_areas: frozenset[str] = frozenset()
    if contrast is not None:
        # A theme the underlying hand carries more strongly is a need with less
        # room than it wants, which is pressure in the area it belongs to.
        theme_to_area = {
            "your energy and vitality": "health",
            "the way you think and decide": "mind",
            "your emotional and relationship life": "love",
            "your work and sense of direction": "career",
        }
        latent_areas = frozenset(
            theme_to_area[t] for t in contrast.latent if t in theme_to_area
        )

    domains = [
        d for d in (
            _domain_state(a, demanding=demanding_aspect, latent_areas=latent_areas)
            for a in (aspects or [])
        ) if d is not None
    ]
    domains.sort(
        key=lambda d: (
            max(_BAND_ORDER[d.pressure], _BAND_ORDER[d.support]),
            _BAND_ORDER[d.activation],
        ),
        reverse=True,
    )

    grade = str(photo_grade or "fair").lower()
    note = ""
    if grade == "poor":
        note = ("The photographs are not clear enough for firm detail, so this "
                "reads as a direction to consider rather than a verdict.")
    elif grade == "fair":
        note = ("Fine detail is less certain in these photographs, so the "
                "broader pattern carries more weight than any single sign.")
    if not domains:
        return PalmStateFacts(chapter_tone="mixed", confidence_note=note)

    band_value = {"none": 0.0, "low": 0.2, "moderate": 0.5, "high": 0.75, "very_high": 1.0}
    emotional = _average(band_value[d.pressure] for d in domains)
    decision = _average(
        band_value[d.pressure] for d in domains
        if _vocab_key(d.area) in ("career", "wealth", "mind", "travel")
    )
    themes = _themes(domains, contrast)

    heavy = any(_BAND_ORDER[d.pressure] >= 3 for d in domains)
    backed = any(_BAND_ORDER[d.support] >= 3 for d in domains)
    if (heavy and backed) or any(d.contradiction for d in domains):
        tone = "mixed"
    elif heavy:
        tone = "pressured"
    elif backed:
        tone = "supported"
    else:
        tone = "steady"

    return PalmStateFacts(
        chapter_tone=tone,                                   # type: ignore[arg-type]
        themes=themes,
        emotional_pressure=_level(emotional),                # type: ignore[arg-type]
        decision_pressure=_level(decision),                  # type: ignore[arg-type]
        # Hands that disagree with each other, or a photograph that cannot
        # support detail, are the two honest reasons to tell someone this is a
        # period to reassess rather than commit.
        uncertainty=(
            "high" if (any(d.contradiction for d in domains) or grade == "poor")
            else "moderate" if (contrast is not None and contrast.agreement == "low")
            else "low"
        ),                                                   # type: ignore[arg-type]
        domains=domains[:10],
        mind_now=_mind_now(domains),
        confidence_note=note,
    )
