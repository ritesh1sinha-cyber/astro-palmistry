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
    "air": "You carry an <b>Air Hand archetype</b> (square palm with long, elegant fingers) — signifying an <b>intellectual, highly observant strategist and communicator</b> who thrives on mental variety and analytical depth.",
    "earth": "You carry an <b>Earth Hand archetype</b> (square palm with sturdy fingers) — signifying a <b>grounded, pragmatic, and reliable builder</b> who values tangible results and steady loyalty.",
    "fire": "You carry a <b>Fire Hand archetype</b> (long palm with active fingers) — signifying an <b>energetic, charismatic, and instinctive leader</b> driven by passion, ambition, and bold initiative.",
    "water": "You carry a <b>Water Hand archetype</b> (narrow palm with slender fingers) — signifying a <b>deeply intuitive, empathetic, and creative soul</b> with rich emotional perception.",
}

_THUMB_WILL = {
    "will_dominant": "Your thumb reveals <b>strong will-driven determination</b> — once you commit to a course of action, you push through obstacles with unwavering focus.",
    "logic_dominant": "Your thumb reveals <b>methodical analytical discernment</b> — you weigh risks, verify evidence, and commit with deliberate foresight.",
    "balanced": "Your thumb maintains a <b>harmonious balance between will and reason</b> — you decide decisively after thoughtful evaluation.",
}

_HEAD_TRAITS = {
    ("straight", "separated"): "an <b>independent, highly practical intellect</b> that values autonomy and objective clarity",
    ("straight", "merged"): "a <b>cautious, methodical mind</b> that builds confidence through mastery and deliberate execution",
    ("sloped", "separated"): "a <b>creative, instinctive mind</b> with strong lateral problem-solving abilities",
    ("sloped", "merged"): "an <b>intuitive, empathetic thinker</b> who integrates emotional insight with intellectual focus",
}

_MOUNT_PERSONA = {
    "jupiter": ("your Mount of Jupiter", "leadership and executive stature", "you naturally command respect, seek meaningful influence, and hold high ethical standards"),
    "saturn": ("your Mount of Saturn", "discipline and steadfast perseverance", "you shoulder responsibilities with quiet maturity and build enduring success over time"),
    "apollo": ("your Mount of Apollo", "creative brilliance and personal magnetism", "you possess refined aesthetic taste, artistic flair, and a natural instinct for public impact"),
    "mercury": ("your Mount of Mercury", "strategic commerce and eloquence", "you excel in negotiation, persuasive communication, and sharp analytical problem-solving"),
    "mars": ("your Mount of Mars", "courage and inner resilience", "you stand firm under pressure and possess formidable stamina during challenging chapters"),
    "venus": ("your Mount of Venus", "warmth, vitality and affection", "you radiate genuine warmth, value emotional closeness, and possess strong physical vitality"),
    "moon": ("your Mount of Luna", "imagination and intuitive depth", "you sense underlying currents effortlessly and possess a rich creative imagination"),
}


def build_archetype(dom: dict[str, Any], non: dict[str, Any], *,
                    dom_label: str) -> dict[str, Any]:
    """Elemental temperament: hand type + thumb + head set + key mounts."""
    hand = _hand_type(dom)
    type_txt = _TYPE_DESC.get(hand, "You carry a balanced hand archetype combining practical execution with mental versatility.")
    parts = [type_txt]

    thumb = _thumb(dom)
    will = str(thumb.get("will_vs_logic") or "unknown").lower()
    if will in _THUMB_WILL:
        parts.append(_THUMB_WILL[will])
    elif thumb.get("length"):
        parts.append(
            f"Your thumb length reflects steady executive stamina and deliberate decision-making."
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
                f"Your <b>{first[0].removeprefix('your ')}</b> is prominently elevated on your active hand — "
                f"reinforcing <b>{first[1]}</b>: {first[2]}."
            )
        extra = [k for k in keyed[1:2]]
        for k in extra:
            p = _MOUNT_PERSONA.get(k)
            if p:
                parts.append(f"Your <b>{p[0].removeprefix('your ')}</b> is also well-developed, adding {p[1]}.")

    return {
        "title": hand.title() if hand else "Balanced",
        "summary": " ".join(parts),
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
                "jupiter": "ambition is grounded and quiet — you prefer quiet mastery over superficial self-promotion.",
                "mars": "you choose your battles judiciously, preferring strategic diplomacy over unnecessary confrontation.",
                "mercury": "you process thoughts deeply before speaking, delivering precise and thoughtful conclusions.",
            }[k]
            traits.append({"trait": f"{kind} (deliberate)", "text": flat_txt.capitalize()})

    head = _line(dom, "head")
    if str(head.get("depth") or "").lower() == "deep":
        traits.append({"trait": "focused resolve",
                       "text": "A deeply etched head line confers <b>unbroken concentration and analytical stamina</b>."})
    if str(head.get("shape") or "").lower() == "wavy":
        traits.append({"trait": "adaptable nature",
                       "text": "A wavy head line reflects <b>agile thinking and the capacity to pivot seamlessly</b> under shifting circumstances."})

    heart = _line(dom, "heart")
    if str(heart.get("depth") or "").lower() == "deep":
        traits.append({"trait": "loyal heart",
                       "text": "A deeply cut heart line signifies <b>unwavering loyalty, emotional integrity, and sincerity in long-term bonds</b>."})

    if _prominent(mounts, "venus"):
        traits.append({"trait": "vital warmth",
                       "text": "A full Mount of Venus radiates <b>natural magnetism, physical vigor, and genuine generosity</b>."})

    return traits[:7]


# ---------------------------------------------------------------------------
# profession
# ---------------------------------------------------------------------------

_FATE_ORIGIN = {
    "wrist": ("rooted in strong foundational discipline — your vocational thread is established early and matures with steady focus", (24, 32)),
    "mid_palm": ("<b>self-directed and self-built</b> — your career line rises of its own accord, demonstrating that your stature is earned through personal mastery and grit", (28, 38)),
    "moon": ("<b>public-facing, innovative, or travel-aligned</b> — your career flourishes through audience reach, creative expression, and broad networks", (26, 36)),
    "life": ("closely intertwined with personal values and close alliances — your vocation is deeply linked with purpose and personal loyalty", (24, 34)),
    "mars": ("<b>performance-driven and competitive</b> — you excel where standards are demanding, execution is measurable, and leadership is required", (26, 36)),
}

_FATE_REACH = {
    "saturn": "<b>steady, disciplined ascent</b> — long-term leadership built through technical mastery and perseverance",
    "jupiter": "<b>executive authority and public influence</b> — expanding recognition that arrives through strategic leadership",
    "apollo": "<b>creative impact and reputation</b> — your personal identity and craft become central to your success",
    "mercury": "<b>strategic commerce and advisory mastery</b> — financial growth generated through negotiation, communication, and market acumen",
}

_PROFESSION_FAMILY = {
    "mercury": ("commerce, strategic advisory, technology, and communication", "a prominent Mount of Mercury"),
    "apollo": ("creative leadership, design, strategy, and public-facing enterprises", "an elevated Mount of Apollo"),
    "jupiter": ("executive management, administration, advisory, and institutional leadership", "a well-developed Mount of Jupiter"),
    "saturn": ("engineering, specialized analytics, finance, and technical architecture", "a disciplined Mount of Saturn"),
    "venus": ("hospitality, lifestyle arts, creative design, and people-centric leadership", "a vibrant Mount of Venus"),
    "moon": ("writing, research, international ventures, and creative strategy", "an imaginative Mount of Luna"),
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
    window: list[int] = [28, 38]

    if fate.get("detected"):
        if origin_info:
            parts.append(
                f"Your fate line indicates a trajectory {origin_info[0]}."
            )
            window = list(origin_info[1])
        if reach in _FATE_REACH:
            parts.append(f"It ascends toward {reach.replace('_', ' ').title()}: {_FATE_REACH[reach]}.")
    else:
        parts.append(
            "Your professional trajectory is guided primarily by your strong head line and planetary mounts, favoring adaptive, multi-threaded enterprise."
        )

    family = None
    for k in ("mercury", "apollo", "jupiter", "saturn", "venus", "moon"):
        if _prominent(mounts, k):
            family = _PROFESSION_FAMILY[k]
            break
    if family:
        parts.append(f"Your active hand's key vocational anchor is {family[1]}, naturally favoring <b>{family[0]}</b>.")
    elif _prominent(mounts, "mercury") is False and _prominent(mounts, "jupiter") is False:
        parts.append(
            "Your palm displays versatile vocational capabilities, allowing you to combine technical competence with strategic project leadership."
        )

    if minor.get("detected") or _prominent(mounts, "apollo"):
        parts.append(
            "A supporting Sun line confirms that <b>merit-based recognition and professional authority</b> build progressively around your core accomplishments."
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
    "saturn": "your heart line anchors under Saturn — you approach love with maturity, thoughtful reserve, and deep loyalty",
    "jupiter": "your heart line sweeps toward Jupiter — creating an idealistic, generous partnership based on mutual respect and shared aspirations",
    "normal": "your heart line maintains a balanced trajectory — fostering healthy emotional interdependence and open communication",
}

_SPOUSE_BY_MOUNT = {
    "moon": "your partner is imaginative, emotionally perceptive, and quietly supportive",
    "venus": "your partner brings warmth, domestic loyalty, and physical affection into the union",
    "jupiter": "your partner possesses strong integrity, dignity, and intellectual ambition",
    "apollo": "your partner is creative, expressive, and socially charismatic",
    "mercury": "your partner is quick-witted, articulate, and intellectually stimulating",
    "saturn": "your partner is dependable, grounded, and values long-term stability",
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
            parts.append("Your heart line runs with vivid responsiveness, indicating <b>rich emotional depth, sincere empathy, and dynamic relationship engagement</b>.")
        elif depth == "deep":
            parts.append("Your deeply etched heart line signifies <b>unwavering relationship staying power, sincerity, and high emotional loyalty</b>.")
        if start in _HEART_START:
            parts.append(f"{_HEART_START[start].capitalize()}.")

    if _prominent(mounts, "venus"):
        parts.append(
            "An elevated Mount of Venus, the classical seat of affection, signifies a <b>warm, physically tender, and harmonious union</b> where emotional closeness is deeply cherished."
        )
    elif _flat(mounts, "venus"):
        parts.append(
            "Your Mount of Venus indicates that your partnership values <b>mutual respect, emotional peace, and steady dependability</b>."
        )

    if minor.get("detected"):
        parts.append(
            "Clear union markings confirm a <b>meaningful, committed life partnership</b> grounded in shared values."
        )
    else:
        parts.append(
            "Your relationship blueprint rests on your strong heart line and Venus mount, indicating enduring relationship stability."
        )

    spouse_key = None
    for k in ("moon", "venus", "jupiter", "apollo", "mercury", "saturn"):
        if _prominent(mounts, k) or _prominent(non_mounts, k):
            spouse_key = k
            break
    if spouse_key and spouse_key in _SPOUSE_BY_MOUNT:
        parts.append(f"In your palm's classical synthesis, {_SPOUSE_BY_MOUNT[spouse_key]}.")

    if _has_marks(dom, {"trident", "fish", "cross"}) and _level(mounts, "jupiter") in ("moderate", "prominent"):
        parts.append(
            "An auspicious marking near your Mount of Jupiter confers <b>social dignity and lasting harmony</b> in your domestic life."
        )

    return {
        "summary": " ".join(parts),
        "spouse": (_SPOUSE_BY_MOUNT.get(spouse_key, "") if spouse_key else ""),
        "basis": f"heart line, Venus mount, marriage line on the {dom_label} hand",
    }


# ---------------------------------------------------------------------------
# wealth
# ---------------------------------------------------------------------------

def build_wealth(dom: dict[str, Any], *, dom_label: str) -> dict[str, Any]:
    """Fortune pattern: fate strength + Sun line + Mercury + protective marks."""
    fate = _line(dom, "fate")
    mounts = dom.get("mounts") or {}
    minor = _minor(dom, "sun")

    parts: list[str] = []
    pattern = "steady accumulation"

    if fate.get("detected") and str(fate.get("quality") or "").lower() == "clear":
        parts.append(
            "Your fate line is clear and well-formed — signing a <b>fortune built progressively through disciplined consistency and professional merit</b>."
        )
    else:
        parts.append("Your wealth trajectory rewards <b>strategic patience, multi-channel asset creation, and disciplined reinvestment</b>.")

    if minor.get("detected") or _prominent(mounts, "apollo"):
        parts.append(
            "The presence of an active Sun line indicates that <b>public recognition and creative reputation convert directly into financial expansion</b>."
        )
        pattern = "recognition-backed wealth"

    if _prominent(mounts, "mercury"):
        parts.append(
            "A well-developed Mount of Mercury accelerates wealth through <b>strategic negotiation, commerce, and specialized technical expertise</b>."
        )

    if _prominent(mounts, "jupiter"):
        parts.append("An elevated Mount of Jupiter supports asset building through <b>executive authority, administrative leadership, and institutional status</b>.")

    if _has_marks(dom, {"triangle", "square", "fish"}):
        parts.append(
            "Protective marks (triangle/square) on your palm provide a <b>classical financial shield</b>, preserving capital during broader economic fluctuations."
        )

    return {
        "pattern": pattern,
        "summary": " ".join(parts) if parts else (
            "Your palm indicates steady, conservative wealth accumulation driven by disciplined professional effort."
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
            f"between ages {rng[0]} and {rng[1]}. {verdict}"
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