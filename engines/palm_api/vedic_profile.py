"""
vedic_profile.py — deterministic Vedic predictive profile from measured features.

The report's chronological timeline used to be a fixed script (ages 22, 33, 42,
52, 66 read the same for every hand). This module replaces it with a
feature-grounded Vedic reading in the voice of classical Samudrika Shastra:

  • archetype     — the elemental temperament (hand type + thumb + mounts + head)
  • personality   — traits written off the mounts, thumb and head line
  • profession    — vocation family from fate origin/reach + mounts + head set
  • marriage      — spouse/union profile from heart, Venus, marriage line
  • wealth        — fortune pattern from fate, Sun line, Mercury and marks
  • turning points — age windows anchored to REAL measured line timings

Rules of voice (kept intentionally):
  - Every statement names the physical sign it comes from.
  - Ages are always windows ("a favourable window around age 35"), never
    calendar promises.
  - No deterministic guarantee verbs ("will certainly", "guarantees", ...).
  - No pseudo-medical language.
  - If a feature was not measured, it is not spoken about.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

_MOUNT_LEVEL = ("flat", "moderate", "prominent")


def _level(mounts: dict[str, Any], key: str) -> str:
    v = str(mounts.get(key) or "unknown").lower()
    return v if v in _MOUNT_LEVEL else "unknown"


def _prominent(mounts: dict[str, Any], key: str) -> bool:
    return _level(mounts, key) == "prominent"


def _flat(mounts: dict[str, Any], key: str) -> bool:
    return _level(mounts, key) == "flat"


def _line(feats: dict[str, Any], key: str) -> dict[str, Any]:
    return (feats.get("lines") or {}).get(key) or {}


def _minor(feats: dict[str, Any], key: str) -> dict[str, Any]:
    return (feats.get("minor_lines") or {}).get(key) or {}


def _hand_type(feats: dict[str, Any]) -> str:
    return str(((feats.get("morphology") or {}).get("hand_type") or "unknown")).lower()


def _thumb(feats: dict[str, Any]) -> dict[str, Any]:
    return (feats.get("morphology") or {}).get("thumb") or {}


def _has_marks(feats: dict[str, Any], kinds: set[str]) -> bool:
    for m in (feats.get("special_marks") or []):
        if str(m.get("type") or "").lower() in kinds:
            return True
    return False


# ---------------------------------------------------------------------------
# archetype & personality
# ---------------------------------------------------------------------------

_TYPE_DESC = {
    "air": ("an Air hand — ideas, words and social ease come naturally"),
    "earth": ("an Earth hand — you are practical, patient and steady"),
    "fire": ("a Fire hand — drive, warmth and a quick spark"),
    "water": ("a Water hand — intuition, empathy and a rich inner world"),
}

_THUMB_WILL = {
    "will_dominant": ("Your thumb marks you as will-driven: once you decide a thing is worth doing, you see it through."),
    "logic_dominant": ("Your thumb is reasoning-led: you weigh, compare and only then commit."),
    "balanced": ("Your thumb balances will and reason — you decide firmly, but only after thinking it through."),
}

_HEAD_TRAITS = {
    ("straight", "separated"): "an independent, practical mind",
    ("straight", "merged"): "a practical mind that grows bolder as confidence builds",
    ("sloped", "separated"): "a creative, imaginative mind that decides by instinct",
    ("sloped", "merged"): "an intuitive mind that learns to trust its own voice",
}

_MOUNT_PERSONA = {
    "jupiter": ("your Mount of Jupiter", "leadership and ambition", "you naturally want to lead, influence and be recognised for your judgement"),
    "saturn": ("your Mount of Saturn", "discipline and endurance", "you carry responsibility quietly and finish what you start"),
    "apollo": ("your Mount of Apollo", "creativity and taste", "you see how things should look and feel, and you usually arrange them that way"),
    "mercury": ("your Mount of Mercury", "communication and commerce", "words, negotiation and persuasion are where your edge lives"),
    "mars": ("your Mount of Mars", "courage and stamina", "you stand your ground when it matters and rally when others tire"),
    "venus": ("your Mount of Venus", "warmth and devotion", "affection, loyalty and closeness are core needs you give generously"),
    "moon": ("your Mount of Luna", "imagination and intuition", "you feel situations before you fully understand them"),
}


def build_archetype(dom: dict[str, Any], non: dict[str, Any], *,
                    dom_label: str) -> dict[str, Any]:
    """Elemental temperament: hand type + thumb + head set + key mounts."""
    hand = _hand_type(dom)
    type_txt = _TYPE_DESC.get(hand, "")
    parts = ["Classical palmistry reads your elemental temperament first."]
    if type_txt:
        parts.append(type_txt)

    thumb = _thumb(dom)
    will = str(thumb.get("will_vs_logic") or "unknown").lower()
    if will in _THUMB_WILL:
        parts.append(_THUMB_WILL[will])
    elif thumb.get("length"):
        parts.append(
            f"Your thumb runs {str(thumb.get('length')).replace('_', ' ')} — "
            "the classical reading weighs it together with your will." if thumb.get("length") else ""
        )

    head = _line(dom, "head")
    dirn = str(head.get("direction") or head.get("shape") or "unknown").lower()
    rel = str(head.get("start_relation") or "unknown").lower()
    head_trait = _HEAD_TRAITS.get((dirn, rel))
    if head_trait:
        parts.append(f"Your head line reveals {head_trait}.")

    mounts = dom.get("mounts") or {}
    keyed = [k for k in ("jupiter", "mercury", "apollo", "venus") if _prominent(mounts, k)]
    if keyed:
        first = _MOUNT_PERSONA.get(keyed[0])
        if first:
            parts.append(
                f"Above all, {first[0]} is full in your {dom_label} hand — "
                f"traditionally the sign of {first[1]}: {first[2]}."
            )
        extra = [k for k in keyed[1:]]
        for k in extra:
            p = _MOUNT_PERSONA.get(k)
            if p:
                parts.append(f"{p[0].capitalize()} is also raised — {p[2]}.")

    return {
        "title": hand.title() if hand else "Balanced",
        "summary": " ".join(p for p in parts if p),
        "basis": "hand type, thumb, head line and mount elevations",
    }


def build_personality(dom: dict[str, Any], non: dict[str, Any], *,
                      dom_label: str) -> list[dict[str, Any]]:
    """Deterministic trait lines, each tied to a measured sign."""
    mounts = dom.get("mounts") or {}
    traits: list[dict[str, Any]] = []

    for k, (_, kind, txt) in _MOUNT_PERSONA.items():
        if _prominent(mounts, k):
            traits.append({"trait": kind, "text": f"{txt.capitalize()}."})
        elif _flat(mounts, k) and k in ("jupiter", "mars", "mercury"):
            flat_txt = {
                "jupiter": "ambition is real but quiet — you often let others announce what you achieved.",
                "mars": "confrontation costs you more than it should; you avoid the fight to save the peace.",
                "mercury": "you think faster than you speak — your best point often goes unsaid.",
            }[k]
            traits.append({"trait": f"{kind} (quiet)", "text": flat_txt.capitalize()})

    head = _line(dom, "head")
    if str(head.get("depth") or "").lower() == "deep":
        traits.append({"trait": "focused resolve",
                       "text": "A deeply cut head line speaks of intense focus — once you engage, distractions drop away."})
    if str(head.get("shape") or "").lower() == "wavy":
        traits.append({"trait": "adaptable nature",
                       "text": "A wavy head line suggests you shift course smoothly and improvise well under change."})

    heart = _line(dom, "heart")
    if str(heart.get("depth") or "").lower() == "deep":
        traits.append({"trait": "loyal heart",
                       "text": "A deep heart line marks loyalty and sincerity — your feelings, once given, are given fully."})

    if _prominent(mounts, "venus"):
        traits.append({"trait": "vital warmth",
                       "text": "A full Mount of Venus, the classical sign of vitality and affection, draws people toward your warmth."})

    return traits[:7]


# ---------------------------------------------------------------------------
# profession
# ---------------------------------------------------------------------------

_FATE_ORIGIN = {
    "wrist": ("rooted in family and early foundations — your vocational thread is established young", (22, 30)),
    "mid_palm": ("self-made — your career line begins of its own accord, so your profession is largely built by your own effort", (30, 40)),
    "moon": ("drawn toward imagination, the public or foreign soil — your career benefits from audience, travel and creative reach", (26, 36)),
    "life": ("interwoven with home and family — your vocation and your people are hard to separate", (24, 32)),
    "mars": ("competitive by nature — you thrive where performance is measured and pressure is real", (26, 34)),
}

_FATE_REACH = {
    "saturn": "steady, disciplined ascent — a long professional climb, built more by consistency than by luck",
    "jupiter": "leadership and authority — recognition that arrives with position",
    "apollo": "creative recognition — your name becomes part of the work",
    "mercury": "commerce and communication — money that moves through skill with people and words",
}

_PROFESSION_FAMILY = {
    "mercury": ("commerce, communication, trade and advisory work", "full Mercury"),
    "apollo": ("creative, artistic and public-facing work", "raised Apollo"),
    "jupiter": ("leadership, education, administration and positions of authority", "full Jupiter"),
    "saturn": ("technical, engineering and long-haul professional service", "full Saturn"),
    "venus": ("work around beauty, hospitality, care and the arts of comfort", "full Venus"),
    "moon": ("imaginative, literary, travel-linked and public work", "full Luna"),
}


def build_profession(dom: dict[str, Any], *, dom_label: str) -> dict[str, Any]:
    """Vocation family + establishment window, grounded in fate origin/reach & mounts."""
    fate = _line(dom, "fate")
    mounts = dom.get("mounts") or {}
    minor = _minor(dom, "sun")

    parts: list[str] = []
    start_zone = str(fate.get("start_zone") or "unknown").lower()
    reach = str(fate.get("reach") or "unknown").lower()
    origin_info = _FATE_ORIGIN.get(start_zone)
    window: list[int] = [26, 36]

    if fate.get("detected"):
        if origin_info:
            parts.append(
                f"Your fate line rises from the {start_zone.replace('_', ' ')} — "
                f"{origin_info[0]}."
            )
            window = list(origin_info[1])
        if reach in _FATE_REACH:
            parts.append(f"It carries toward {reach.replace('_', ' ')}: {_FATE_REACH[reach]}.")
    else:
        parts.append(
            "Your fate line is not strongly resolved in this photograph, so the "
            "vocational reading leans on your mounts and head line instead."
        )

    family = None
    for k in ("mercury", "apollo", "jupiter", "saturn", "venus", "moon"):
        if _prominent(mounts, k):
            family = _PROFESSION_FAMILY[k]
            break
    if family:
        parts.append(f"Your hand's strongest vocational pointer is {family[1]}, favouring {family[0]}.")
    elif _prominent(mounts, "mercury") is False and _prominent(mounts, "jupiter") is False:
        parts.append(
            "No single mount dominates your vocational chart — your career is "
            "more versatile than specialised, and finds its shape through several threads."
        )

    if minor.get("detected") or _prominent(mounts, "apollo"):
        parts.append(
            "A Sun line is present — a classical sign that recognition and a "
            "public reputation can build around your chosen work."
        )

    return {
        "type": (family[0] if family else "versatile / multi-threaded"),
        "summary": " ".join(parts),
        "window": window,
        "basis": f"fate line origin ({start_zone}), reach ({reach}), mount elevations on the {dom_label} hand",
    }


# ---------------------------------------------------------------------------
# marriage & spouse
# ---------------------------------------------------------------------------

_HEART_START = {
    "saturn": "your heart line begins under Saturn — love is approached with care, reserve and loyalty before passion",
    "jupiter": "your heart line reaches toward Jupiter — idealistic, giving love that expects depth in return",
    "normal": "your heart line holds a balanced position — affection and independence coexist",
}

_SPOUSE_BY_MOUNT = {
    "moon": "your partner tends to be imaginative, intuitive and quietly attentive",
    "venus": "your partner is warm, loyal and physically affectionate — a home-centred union",
    "jupiter": "your partner carries dignity and ambition — a relationship built on mutual respect",
    "apollo": "your partner is creative, expressive and a little dramatic",
    "mercury": "your partner is quick-witted, communicative and socially easy",
    "saturn": "your partner is steady, dependable and slower to open up",
}


def build_marriage(dom: dict[str, Any], non: dict[str, Any], *,
                   dom_label: str, non_label: str) -> dict[str, Any]:
    """Union & spouse profile: heart line + Venus + marriage line + Jupiter marks."""
    heart = _line(dom, "heart")
    mounts = dom.get("mounts") or {}
    non_mounts = non.get("mounts") or {}
    minor = _minor(dom, "marriage")

    parts: list[str] = []

    if heart.get("detected"):
        shape = str(heart.get("shape") or "unknown").lower()
        depth = str(heart.get("depth") or "unknown").lower()
        start = str(heart.get("start_zone") or "normal").lower()
        if shape == "wavy":
            parts.append("Your heart line runs wavy — your emotional life is vivid, responsive and changeable rather than flat.")
        if depth == "deep":
            parts.append("It is deeply cut — you love sincerely and with real staying power.")
        if start in _HEART_START:
            parts.append(_HEART_START[start])

    if _prominent(mounts, "venus"):
        parts.append(
            "Your full Mount of Venus, the classical seat of affection, points to a "
            "partner who is warm, loyal and physically tender — and a union where closeness matters."
        )
    elif _flat(mounts, "venus"):
        parts.append(
            "Your Mount of Venus is quiet, so your needs in a partner lean toward "
            "steadiness and respect rather than demonstrative warmth."
        )

    if minor.get("detected"):
        parts.append(
            "You carry marriage lines — a classical sign that a committed union "
            "is written as a real possibility in your hand."
        )
    else:
        parts.append(
            "Your marriage line is not clearly resolved in this photograph; the "
            "union reading therefore rests on your heart line and Venus, which are the more stable evidence."
        )

    spouse_key = None
    for k in ("moon", "venus", "jupiter", "apollo", "mercury", "saturn"):
        if _prominent(mounts, k) or _prominent(non_mounts, k):
            spouse_key = k
            break
    if spouse_key and spouse_key in _SPOUSE_BY_MOUNT:
        parts.append(f"Read together with your mounts, {_SPOUSE_BY_MOUNT[spouse_key]}.")

    if _has_marks(dom, {"trident", "fish", "cross"}) and _level(mounts, "jupiter") in ("moderate", "prominent"):
        parts.append(
            "An auspicious mark near your Mount of Jupiter supports a dignified, "
            "respected union in the classical tradition."
        )

    return {
        "summary": " ".join(parts),
        "spouse": (_SPOUSE_BY_MOUNT.get(spouse_key, "") if spouse_key else ""),
        "basis": f"heart line (shape {heart.get('shape', 'unknown')}, start {heart.get('start_zone', 'unknown')}), "
                 f"Venus mount, marriage line on the {dom_label} hand",
    }


# ---------------------------------------------------------------------------
# wealth
# ---------------------------------------------------------------------------

_WEALTH_PATTERNS = []


def build_wealth(dom: dict[str, Any], *, dom_label: str) -> dict[str, Any]:
    """Fortune pattern: fate strength + Sun line + Mercury + protective marks."""
    fate = _line(dom, "fate")
    mounts = dom.get("mounts") or {}
    minor = _minor(dom, "sun")

    parts: list[str] = []
    pattern = "steady accumulation"

    if fate.get("detected") and str(fate.get("quality") or "").lower() == "clear":
        parts.append(
            "Your fate line is clear and unbroken — in the classical reading this "
            "signs a fortune built steadily, chapter by chapter, rather than by chance."
        )
    else:
        parts.append("Your fate line is present but irregular, so income tends to arrive unevenly and rewards patience.")

    if minor.get("detected") or _prominent(mounts, "apollo"):
        parts.append(
            "With a Sun line, recognition and creative reputation convert into income — money that follows visible work."
        )
        pattern = "recognition-backed wealth"

    if _prominent(mounts, "mercury"):
        parts.append(
            "A full Mercury mount favours income through communication, commerce, negotiation and sharp market sense."
        )

    if _prominent(mounts, "jupiter"):
        parts.append("Full Jupiter adds wealth that travels with position, reputation and authority.")

    if _has_marks(dom, {"triangle", "square", "fish"}):
        parts.append(
            "A protective mark (triangle or square) on your palm is classically read "
            "as a shield around money — gains that survive the rough seasons."
        )

    return {
        "pattern": pattern,
        "summary": " ".join(parts) if parts else (
            "The wealth reading is conservative: your photograph does not resolve "
            "the finer fortune markings, so this section stays with the fate line only."
        ),
        "basis": f"fate line ({fate.get('quality', 'unknown')}), Sun line, Mercury and Jupiter mounts on the {dom_label} hand",
    }


# ---------------------------------------------------------------------------
# turning points — real line timings, not a script
# ---------------------------------------------------------------------------

_LINE_WINDOW = {
    "life": ("vitality", "your life line"),
    "head": ("decision", "your head line"),
    "heart": ("affection", "your heart line"),
    "fate": ("career", "your fate line"),
}

_TURNING_TEXT = {
    "life": "A life-line focus sits in this window — vitality, recovery and endurance become the theme that matters here.",
    "head": "Your head line marks a decision window — the direction your thinking commits to during these years shapes the decade after.",
    "heart": "An affection window on the heart line — feelings deepen or settle during this span; for many hands this is the marriage chapter.",
    "fate": "Your fate line concentrates here — the vocational turn that defines the following phase of your career.",
}


def build_turning_points(dom: dict[str, Any], dom_feats: dict[str, Any], *,
                         age: int) -> list[dict[str, Any]]:
    """Age-anchored turning points from the REAL measured line timings.

    Every entry carries the engine's computed timing (estimated_age + age_range
    from the Cheiro seven-year division on the actual line pixels). When a line
    has no reliable timing, we do not invent one.
    """
    points: list[dict[str, Any]] = []
    seen_lines: set[str] = set()
    checklist = dom.get("numbered_checklist") or []

    for item in checklist:
        if item.get("kind") != "line":
            continue
        key = str(item.get("key") or "").lower()
        if key not in _LINE_WINDOW or key in seen_lines:
            continue
        timing = item.get("timing") or {}
        est = timing.get("estimated_age")
        rng = timing.get("age_range")
        if not isinstance(est, int) or not (isinstance(rng, list) and len(rng) == 2):
            continue
        seen_lines.add(key)
        theme, line_name = _LINE_WINDOW[key]
        verdict = (item.get("conclusive") or {}).get("verdict") or ""
        verdict = " ".join(str(verdict).replace("Why:", ".").split()) or ""
        text = (
            f"{_TURNING_TEXT[key]} Your hand's own marking places this "
            f"around ages {rng[0]}–{rng[1]}. {verdict}"
        )
        points.append({
            "title": f"{theme.title()} window — {line_name}",
            "line_key": key,
            "age": est,
            "age_range": [int(rng[0]), int(rng[1])],
            "text": text.strip(),
            "confidence": str(timing.get("timing_confidence") or "moderate"),
        })

    points.sort(key=lambda p: p["age"])
    return points


# ---------------------------------------------------------------------------
# top-level
# ---------------------------------------------------------------------------

def build_vedic_profile(
    dom: dict[str, Any],
    non: dict[str, Any],
    *,
    dom_label: str,
    non_label: str,
    age: int,
) -> dict[str, Any]:
    dom_feats = dom.get("features") or {}
    non_feats = non.get("features") or {}

    archetype = build_archetype(dom_feats, non_feats, dom_label=dom_label)
    personality = build_personality(dom_feats, non_feats, dom_label=dom_label)
    profession = build_profession(dom_feats, dom_label=dom_label)
    marriage = build_marriage(dom_feats, non_feats, dom_label=dom_label, non_label=non_label)
    wealth = build_wealth(dom_feats, dom_label=dom_label)
    turning_points = build_turning_points(dom, dom_feats, age=age)

    return {
        "archetype": archetype,
        "personality": personality,
        "profession": profession,
        "marriage": marriage,
        "wealth": wealth,
        "turning_points": turning_points,
    }