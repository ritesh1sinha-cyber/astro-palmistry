"""
Build one clear, rule-backed prediction per numbered palm point.

Combines: measured CV features + Cheiro System-of-Seven age at the circle (life/fate
lines only; see timing.py for verified book sources) + best corpus rule.
"""

from __future__ import annotations

import re
from typing import Any

from palm_api.curated_rules import match_curated_rules
from palm_api.engine import match_rules
from palm_api.personal_tone import (
    finger_phrase,
    line_phrase,
    mount_phrase,
    personalize_book_excerpt,
)
from palm_api.report_format import book_label

# Measured feature → interpretation (second person: your line / your mount)
FEATURE_MEANING: dict[tuple[str, str, str], str] = {
    ("life", "depth", "deep"): "Your life line is deep — traditionally read as a stronger baseline of vitality and resilience; steady routines help you use that energy well.",
    ("life", "depth", "medium"): "Your life line is moderate in depth — your energy may respond noticeably to sleep, routine and lifestyle balance.",
    ("life", "depth", "thin"): "Your life line is thin — you may notice the effects of overwork or poor recovery sooner, so pacing and rest become more important.",
    ("life", "start_zone", "mars"): "Your life line rises from the inner thumb pad — courageous vitality; you may face competitive tests.",
    ("life", "start_zone", "jupiter"): "Your life line rises toward Jupiter — ambition and self-belief shape your early direction.",
    ("life", "start_zone", "between"): "Your life line starts between zones — mixed family influence on your vitality.",
    ("head", "depth", "deep"): "Your head line is deep — you focus strongly and think before you act.",
    ("head", "depth", "medium"): "Your head line is balanced — practical, steady thinking.",
    ("head", "depth", "thin"): "Your head line is fine — you may process things sensitively and need more mental recovery after prolonged concentration.",
    ("head", "start_relation", "merged"): (
        "Your head line is merged with your life line at the start — early caution, reliance on family, "
        "and hesitation in asserting yourself until experience builds your confidence."
    ),
    ("head", "start_relation", "separated"): (
        "Your head line is separate from your life line — independent thinking from youth; "
        "you tend to have your own way and make self-directed choices."
    ),
    ("head", "start_relation", "separated_wide"): (
        "Your head line starts well away from your life line — strongly independent and impulsive; "
        "you act on your own judgement and can be careless or reckless if the thumb is weak."
    ),
    ("head", "direction", "straight"): "Your head line runs straight — logical, practical mind; you favour reason.",
    ("head", "direction", "moon"): "Your head line slopes toward the Moon — imagination, creativity, changeable ideas.",
    ("heart", "depth", "deep"): "Your heart line is deep — you feel strongly and love intensely.",
    ("heart", "depth", "medium"): "Your heart line is moderate — balanced emotional expression.",
    ("heart", "depth", "thin"): "Your heart line is thin — reserved feelings; you show affection quietly.",
    ("heart", "height", "high"): "Your heart line is high — idealistic, romantic expectations in love.",
    ("heart", "height", "normal"): "Your heart line is at normal height — practical balance in relationships.",
    ("heart", "start_zone", "jupiter"): "Your heart line starts under Jupiter — idealistic love; high standards in partners.",
    ("heart", "start_zone", "saturn"): "Your heart line starts under Saturn — serious, cautious in love; duty-bound attachments.",
    ("heart", "start_zone", "mercury_side"): "Your heart line trends toward Mercury — affection tied to communication and wit.",
    ("fate", "depth", "deep"): "Your fate line is strong — clear drive in career and vocation.",
    ("fate", "depth", "medium"): "Your fate line is moderate — your career path develops with steady effort.",
    ("fate", "depth", "thin"): "Your fate line is light — career direction may shift or feel unclear at times.",
    ("fate", "start_zone", "wrist"): "Your fate line rises from the wrist — work and duty are prominent from early life.",
    ("fate", "start_zone", "mid_palm"): "Your fate line starts mid-palm — vocation clarifies after youth.",
    ("fate", "quality", "broken"): "Your fate line shows breaks — career or role change at the timed age on your palm.",
    ("fate", "quality", "clear"): "Your fate line is clear — steady progress in your vocation.",
    ("fate", "reach", "partial"): "Your fate line reaches part-way — goals fulfil later in life.",
    ("fate", "reach", "saturn"): "Your fate line reaches Saturn — discipline and responsibility in your career.",
}

MOUNT_MEANING: dict[tuple[str, str], str] = {
    ("jupiter", "prominent"): "You carry natural confidence and a desire to lead — pride and recognition matter to you.",
    ("jupiter", "flat"): "You may underplay your ambition; building self-belief is the work here.",
    ("jupiter", "moderate"): "Balanced confidence — you want recognition without needing to dominate.",
    ("saturn", "prominent"): "Discipline and seriousness run deep; you carry responsibility patiently.",
    ("saturn", "flat"): "You take duties lightly — avoid chronic avoidance of what must be done.",
    ("saturn", "moderate"): "A steady sense of responsibility without heaviness.",
    ("venus", "prominent"): "Warmth, family bonds and sensual vitality come easily to you.",
    ("venus", "flat"): "Affection runs cooler until trust grows — warmth is there, but guarded.",
    ("venus", "moderate"): "Balanced warmth in love and family life.",
    ("apollo", "prominent"): "Creativity, recognition and love of the arts are strong in you.",
    ("apollo", "flat"): "You prefer private success over public fame.",
    ("apollo", "moderate"): "Balanced creative confidence without needing applause.",
    ("mercury", "prominent"): "Business skill and sharp communication are natural strengths.",
    ("mercury", "flat"): "Simple speech; less drive in commerce unless you push it.",
    ("mercury", "moderate"): "Practical communication and wit in balance.",
    ("mars", "prominent"): "Courage, fight and physical resilience are pronounced.",
    ("mars", "flat"): "You avoid conflict; your energy is gentle rather than combative.",
    ("mars", "moderate"): "Balanced courage and stamina.",
    ("moon", "prominent"): "Imagination, travel and restlessness colour your temperament.",
    ("moon", "flat"): "You are grounded; less wanderlust than most.",
    ("moon", "moderate"): "Balanced imagination without constant restlessness.",
}

FINGER_MEANING: dict[tuple[str, str], str] = {
    ("index", "long"): "Your index (Jupiter) finger is long — strong self-belief, leadership, self-reflection.",
    ("index", "short"): "Your index finger is short — modest self-image; consciously build confidence.",
    ("index", "average"): "Your index finger is average — balanced ego and self-regard.",
    ("middle", "reference"): "Your middle (Saturn) finger is the reference length — sense of duty and structure.",
    ("ring", "long"): "Your ring (Apollo) finger is long — love of beauty, display, creative pride.",
    ("ring", "short"): "Your ring finger is short — modest need for applause; quiet creativity.",
    ("ring", "average"): "Your ring finger is average — balanced material and artistic desires.",
    ("pinky", "long"): "Your little (Mercury) finger is long — eloquence, business sense, persuasion.",
    ("pinky", "short"): "Your little finger is short — plain speech; you prefer simplicity in deals.",
    ("pinky", "average"): "Your little finger is average — balanced communication skills.",
}

# Index (Jupiter) vs ring (Apollo) finger length — classic personality clue.
# Book basis: All the Secrets of Palmistry (index longer -> Jupiter/ambition
# heightened; ring longer -> more self-confidence, love of fame/success, zest).
INDEX_RING_MEANING: dict[str, str] = {
    "index_longer": (
        "Your index (Jupiter) finger is longer than your ring finger — ambition, pride and a "
        "natural urge to lead; you want recognition and to be in charge."
    ),
    "ring_longer": (
        "Your ring (Apollo) finger is longer than your index finger — you may carry "
        "strong self-confidence and a love of success, fame and creative display; "
        "achievement may matter more to you than immediate financial reward."
    ),
    "equal": (
        "Your index and ring fingers are about equal — a balance between ambition for status and "
        "desire for recognition."
    ),
}

# Thumb meanings (50 Case Studies in Modern Palmistry).
THUMB_LENGTH_MEANING: dict[str, str] = {
    "long": "Your thumb is long — a strong will, leadership and self-control; you drive your own decisions.",
    "short": "Your thumb is short — a romantic, feeling-led nature; the heart often leads over cold logic.",
    "average": "Your thumb is of balanced length — a workable mix of will-power and adaptability.",
}
THUMB_WILL_MEANING: dict[str, str] = {
    "will_dominant": "You act first and think afterwards — decisive, sometimes impulsive.",
    "logic_dominant": "You plan and reason carefully, though you may hesitate to act.",
    "balanced": "You weigh things, then act — will and reason in balance.",
}
THUMB_OPEN_MEANING: dict[str, str] = {
    "wide": "Your thumb opens wide from the hand — generous, open-handed and independent.",
    "narrow": "Your thumb is held close to the hand — cautious, careful with resources, sometimes anxious.",
    "moderate": "Your thumb sits at a moderate angle — a balance of generosity and caution.",
}

HAND_TYPE_MEANING: dict[str, str] = {
    "earth": "Your hand is an Earth type — practical, steady, reliable temperament.",
    "air": "Your hand is an Air type — mental, communicative, sociable nature.",
    "fire": "Your hand is a Fire type — energetic, impulsive, passionate temperament.",
    "water": "Your hand is a Water type — sensitive, intuitive, emotionally receptive.",
}

# Life-stage framework by age. This is a SYNTHESIZED life-phase map (not a verbatim
# book table): it follows Cheiro's emphasis that the important phase of life is
# ~21–63 (corpus: "on the Life Line it is between 21 and 63 years of age") and his
# 7-year blocks after 56/63. The phase wording is our plain-language summary.
def _age_phase(age: int) -> dict[str, str]:
    if age < 14:
        return {"label": "childhood", "event": "family health and early temperament"}
    if age < 21:
        return {"label": "youth", "event": "education, identity, leaving childhood home"}
    if age < 28:
        return {"label": "early adulthood", "event": "first career steps, independence, early relationships"}
    if age < 35:
        return {"label": "establishing years", "event": "consolidating work, home, and partnerships"}
    if age < 42:
        return {"label": "mid-life build", "event": "responsibility peak; health and partnership tests"}
    if age < 49:
        return {"label": "mid-life", "event": "reassessment of career and vitality; course corrections"}
    if age < 56:
        return {"label": "mature phase", "event": "authority, legacy, Saturn-period duties"}
    if age < 63:
        return {"label": "pre-retirement", "event": "slowing pace; family and health priorities"}
    if age < 77:
        return {"label": "senior years (7-yr block)", "event": "inheritance, health vigilance, spiritual focus"}
    return {"label": "late life", "event": "legacy, withdrawal, reflection"}


LINE_AGE_EVENT: dict[str, str] = {
    "life": "vitality, relocation, family crisis, or major health turning point",
    "head": "mental outlook shift, education, or decision that changes thinking",
    "heart": "love, marriage, or emotional commitment",
    "fate": "career change, vocation, or public-status event",
}

INTERP_RE = re.compile(
    r"[^.!?]*\b(indicates?|means?|shows?|suggests?|denotes?|signifies?|represents?|"
    r"will be|may be|likely to|person who|tendency)\b[^.!?]*[.!?]",
    re.I,
)

# Meta / filler sentences that are about the book itself, not a palmistry rule.
# These slipped into the auto-extracted corpus and make weak citations.
FILLER_RE = re.compile(
    r"\b(this (book|chapter|section)|in this chapter|as (explained|follows|shown)|"
    r"i (am|will|shall) (giving|give|explain|show|describe)|we (shall|will) (see|discuss)|"
    r"let us|for example|see fig|figure \d|scanned with|camscanner|copyright|"
    r"all rights reserved|table of contents|the (author|reader)|various confusion|"
    r"ignore anything average|in the next|previous chapter|page \d)\b",
    re.I,
)


def _is_filler(text: str) -> bool:
    t = re.sub(r"\s+", " ", (text or "")).strip()
    if len(t) < 35:
        return True
    if FILLER_RE.search(t):
        return True
    # A citation should read like a rule: it must say what something *means*.
    return not INTERP_RE.search(t)


def _extract_clause(text: str, max_len: int = 420) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return ""
    for m in INTERP_RE.finditer(text):
        clause = m.group(0).strip()
        if len(clause) >= 40:
            return clause[:max_len]
    # fallback: first two sentences
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = ""
    for p in parts[:2]:
        if len(out) + len(p) > max_len:
            break
        out = (out + " " + p).strip()
    return out[:max_len] if out else text[:max_len]


def _feature_meanings(line_key: str, props: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for k, v in props.items():
        if k == "detected" or v is None:
            continue
        key = (line_key, k, str(v))
        if key in FEATURE_MEANING:
            out.append(FEATURE_MEANING[key])
    return out


def _point_tags(item: dict[str, Any], props: dict[str, Any], level: str | None = None) -> set[str]:
    tags: set[str] = set()
    kind = item.get("kind")
    key = item.get("key", "")
    if kind == "line":
        tags.add(key)
        tags.add(f"lines.{key}.detected.true")
        for k, v in props.items():
            if k != "detected":
                tags.add(f"lines.{key}.{k}.{v}")
                tags.update(str(v).split())
    elif kind == "mount" and level:
        tags.add(key)
        tags.add(f"mount.{key}.{level}")
        tags.add(f"mounts.{key}.{level}")
    elif kind == "finger":
        tags.add("fingers")
        tags.add(key)
        tags.add(f"finger.{key}")
        if isinstance(props, dict):
            lc = props.get("length_class")
            if lc:
                tags.add(lc)
    elif kind == "morphology":
        tags.add("fingers")
        if isinstance(props, dict):
            ht = props.get("hand_type")
            if ht:
                tags.add(str(ht))
    return tags


def build_conclusive_reading(
    item: dict[str, Any],
    *,
    features: dict[str, Any],
    timing: dict[str, Any] | None,
    corpus: dict[str, Any],
    matched_rules: list[dict[str, Any]],
) -> dict[str, Any]:
    """Single headline + body + citation for this palm point."""
    kind = item.get("kind")
    key = item.get("key", "")
    title = item.get("title", "Finding")
    num = item.get("num")
    lines = features.get("lines") or {}
    mounts = features.get("mounts") or {}
    morphology = features.get("morphology") or {}

    props: dict[str, Any] = {}
    fingers = morphology.get("fingers") or features.get("fingers") or {}
    if kind == "line":
        props = dict(lines.get(key) or {})
    elif kind == "mount":
        props = {"level": mounts.get(key, "unknown")}
    elif kind == "finger":
        props = dict(fingers.get(key) or {})
    elif kind == "morphology":
        props = dict(morphology)
    elif kind == "thumb":
        props = dict(morphology.get("thumb") or {})

    meanings: list[str] = []
    if kind == "line":
        meanings = _feature_meanings(key, props)
    elif kind == "mount":
        level = mounts.get(key, "")
        m = MOUNT_MEANING.get((key, str(level)))
        if m:
            meanings.append(m)
    elif kind == "finger":
        ivr = morphology.get("index_vs_ring")
        if key in ("index", "ring") and ivr in INDEX_RING_MEANING:
            # Index/ring comparison is canonical — do not also describe each
            # finger's length vs middle, which reads as contradictory.
            pass
        else:
            lc = props.get("length_class", "average")
            m = FINGER_MEANING.get((key, str(lc)))
            if m:
                meanings.append(m)
        if props.get("setting") == "low":
            meanings.append(f"{finger_phrase(key)} has a low setting at the palm — hesitation in that finger's qualities.")
    elif kind == "morphology":
        ht = morphology.get("hand_type")
        if ht and ht in HAND_TYPE_MEANING:
            meanings.append(HAND_TYPE_MEANING[ht])
        ivr = morphology.get("index_vs_ring")
        if ivr in INDEX_RING_MEANING:
            meanings.append(INDEX_RING_MEANING[ivr])
        ratio = morphology.get("finger_palm_ratio")
        if ratio == "long":
            meanings.append("Your fingers are long relative to your palm — intellectual, detail-oriented nature.")
        elif ratio == "short":
            meanings.append("Your fingers are short relative to your palm — instinctive, hands-on approach.")
    elif kind == "mark":
        mk_meaning = item.get("meaning")
        if mk_meaning:
            mk = str(mk_meaning)
            meanings.append(mk[:1].upper() + mk[1:])
    elif kind == "thumb":
        if props.get("length") in THUMB_LENGTH_MEANING:
            meanings.append(THUMB_LENGTH_MEANING[props["length"]])
        if props.get("will_vs_logic") in THUMB_WILL_MEANING:
            meanings.append(THUMB_WILL_MEANING[props["will_vs_logic"]])
        if props.get("opening") in THUMB_OPEN_MEANING:
            meanings.append(THUMB_OPEN_MEANING[props["opening"]])

    age = timing.get("estimated_age") if timing else None
    age_clause = ""
    age_range = (timing or {}).get("age_range")
    if age is not None and kind == "line":
        phase = _age_phase(age)
        event = LINE_AGE_EVENT.get(key, "significant life event")
        sys_note = (
            "Cheiro's System of Seven timing"
            if key in ("life", "fate")
            else "approximate timing — the head/heart lines are not age-marked in Cheiro's system"
        )
        if age_range and len(age_range) == 2:
            window = f"About {age_range[0]}–{age_range[1]}"
        else:
            window = f"About age {age}"
        age_clause = (
            f"{window} on {line_phrase(key)} ({phase['label']}, {sys_note}): "
            f"this point marks {phase['event']} for you, especially {event}."
        )

    best = matched_rules[0] if matched_rules else None
    book_clause = ""
    citation: dict[str, Any] = {}
    if best:
        excerpt = personalize_book_excerpt(_extract_clause(best.get("text", "")))
        if excerpt:
            book_clause = excerpt
        citation = {
            "book": best.get("book"),
            "book_label": best.get("book_label") or book_label(best.get("book")),
            "page": best.get("page"),
            "score": best.get("score"),
            "excerpt": book_clause,
        }

    # Conclusive headline
    if age and kind == "line":
        headline = f"Point {num} — Your {key} line at about age {age}"
    elif kind == "mount":
        headline = f"Point {num} — {mount_phrase(key)}"
    elif kind == "finger":
        headline = f"Point {num} — {finger_phrase(key)}"
    elif kind == "mark":
        headline = f"Point {num} — {item.get('title', 'Special mark')}"
    elif kind == "thumb":
        headline = f"Point {num} — Your thumb (will & logic)"
    else:
        headline = f"Point {num} — Your overall hand"

    # User-facing conclusion stays human: measured meanings + life-timing only.
    # Book citations are kept in `citation` for the developer reference file,
    # but NOT shown in the reading text.
    body_parts = [p for p in meanings if p]
    if age_clause:
        body_parts.append(age_clause)

    if not body_parts:
        body_parts.append(
            "Re-check your photo and the numbered circle on the overlay for a clearer reading here."
        )

    conclusion = " ".join(body_parts)
    # Final verdict sentence
    verdict = _make_verdict(kind, key, props, age, meanings, book_clause)

    return {
        "headline": headline,
        "conclusion": conclusion,
        "verdict": verdict,
        "citation": citation,
        "supporting_rule_count": len(matched_rules),
    }


def _make_verdict(
    kind: str,
    key: str,
    props: dict[str, Any],
    age: int | None,
    meanings: list[str],
    book_clause: str,
) -> str:
    """One prediction + Why line in second person."""
    try:
        from palm_api import palm_voice as PV
        if kind == "line":
            return PV.format_line_verdict(key, age, props).text_block()
        if kind == "mount":
            return PV.format_mount_verdict(
                key, props.get("level", ""), meanings[0] if meanings else "").text_block()
        if kind == "finger":
            m = meanings[0] if meanings else f"your {key} finger shows average length."
            return PV.compose(scenario=m, backing=f"{key} finger length").text_block()
        if kind == "morphology":
            return PV.compose(
                scenario=" ".join(meanings[:2]) or "Your hand shape sets the tone for everything below.",
                backing="hand type morphology",
            ).text_block()
        if kind == "mark":
            return PV.format_mark_verdict(key, meanings[0] if meanings else "").text_block()
        if kind == "thumb":
            return PV.compose(
                scenario=meanings[0] if meanings else "Your thumb shows balanced will and logic.",
                backing="thumb proportions",
            ).text_block()
    except Exception:  # noqa: BLE001
        pass
    return "Your hands show a clear pattern here."


def _match_rules_by_keywords(
    corpus: dict[str, Any],
    keywords: list[str],
    *,
    must: tuple[str, ...] = (),
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Generic corpus matcher: rule text must contain all `must` words; score by keyword hits."""
    kws = [k.lower() for k in keywords]
    musts = [m.lower() for m in must]
    scored: list[tuple[float, dict[str, Any]]] = []
    for rule in corpus.get("rules", []):
        text_l = (rule.get("text") or "").lower()
        if musts and not all(m in text_l for m in musts):
            continue
        hits = sum(text_l.count(k) for k in kws)
        if hits <= 0:
            continue
        scored.append((1.0 + hits * 0.5, rule))
    scored.sort(key=lambda x: -x[0])
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for s, rule in scored:
        sig = rule.get("id") or rule.get("text", "")[:80]
        if sig in seen:
            continue
        seen.add(sig)
        out.append(
            {
                "score": round(s, 2),
                "id": rule.get("id"),
                "book": rule.get("book"),
                "page": rule.get("page"),
                "category": rule.get("category", "fingers"),
                "text": rule.get("text"),
                "book_label": book_label(rule.get("book")),
            }
        )
        if len(out) >= limit:
            break
    return out


def _match_rules_for_mark(
    item: dict[str, Any],
    corpus: dict[str, Any],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Find book rules describing this sign (cross/star/fish/…), preferring its mount."""
    keywords = [k.lower() for k in (item.get("keywords") or [str(item.get("key", "")).lower()])]
    zone = str(item.get("zone", "")).lower()
    zone_aliases = {"apollo": ("apollo", "sun"), "moon": ("moon", "luna")}
    zone_words = zone_aliases.get(zone, (zone,)) if zone and zone != "palm" else ()

    scored: list[tuple[float, dict[str, Any]]] = []
    for rule in corpus.get("rules", []):
        text_l = (rule.get("text") or "").lower()
        if not any(kw in text_l for kw in keywords):
            continue
        s = 2.0 + sum(text_l.count(kw) for kw in keywords) * 0.4
        if zone_words and any(zw in text_l for zw in zone_words):
            s += 2.5
        scored.append((s, rule))
    scored.sort(key=lambda x: -x[0])
    seen: set[str] = set()
    rules: list[dict[str, Any]] = []
    for s, rule in scored:
        sig = rule.get("id") or rule.get("text", "")[:80]
        if sig in seen:
            continue
        seen.add(sig)
        rules.append(
            {
                "score": round(s, 2),
                "id": rule.get("id"),
                "book": rule.get("book"),
                "page": rule.get("page"),
                "category": rule.get("category", "marks"),
                "text": rule.get("text"),
                "book_label": book_label(rule.get("book")),
            }
        )
        if len(rules) >= limit:
            break
    return rules


def match_rules_for_point(
    item: dict[str, Any],
    features: dict[str, Any],
    corpus: dict[str, Any],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Citations for one checklist item: curated book rules first, then filtered corpus.

    Curated rules (verbatim, feature-keyed) are the primary citation so the quote
    that backs a verdict actually states that rule. The auto-extracted corpus is a
    fallback, with meta/filler sentences dropped for precision.
    """
    curated = match_curated_rules(item, features)
    corpus_rules = _corpus_rules_for_point(item, features, corpus, limit=limit + 3)
    corpus_rules = [r for r in corpus_rules if not _is_filler(r.get("text", ""))]

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rule in [*curated, *corpus_rules]:
        sig = rule.get("id") or (rule.get("text") or "")[:80]
        if sig in seen:
            continue
        seen.add(sig)
        out.append(rule)
        if len(out) >= limit:
            break
    return out


def _corpus_rules_for_point(
    item: dict[str, Any],
    features: dict[str, Any],
    corpus: dict[str, Any],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Score corpus for this single checklist item only."""
    kind = item.get("kind")
    key = item.get("key", "")
    lines = features.get("lines") or {}
    mounts = features.get("mounts") or {}

    if kind == "mark":
        return _match_rules_for_mark(item, corpus, limit=limit)

    if kind == "thumb":
        thumb = (features.get("morphology") or {}).get("thumb") or {}
        kw = ["thumb"]
        if thumb.get("length") == "long":
            kw += ["long thumb", "strong will"]
        elif thumb.get("length") == "short":
            kw += ["short thumb", "romance"]
        if thumb.get("will_vs_logic") == "will_dominant":
            kw += ["will", "first phalange"]
        elif thumb.get("will_vs_logic") == "logic_dominant":
            kw += ["logic", "reason", "second phalange"]
        return _match_rules_by_keywords(corpus, kw, must=("thumb",), limit=limit)

    cat_map = {
        "life": "vitality",
        "head": "mind",
        "heart": "heart",
        "fate": "career",
    }
    category = None
    props: dict[str, Any] = {}
    if kind == "line":
        category = cat_map.get(key)
        props = dict(lines.get(key) or {})
    elif kind == "mount":
        category = "mounts"
    elif kind == "finger":
        category = "fingers"
        props = dict((features.get("fingers") or features.get("morphology", {}).get("fingers") or {}).get(key) or {})
    elif kind == "morphology":
        category = "fingers"

    if kind == "mount":
        level = str(mounts.get(key, ""))
        extra = _point_tags(item, {}, level=level)
    else:
        extra = _point_tags(item, props)

    if kind == "mount":
        level = str(mounts.get(key, ""))
        prom_words = ("prominent", "full", "high", "raised", "developed", "large", "strong")
        flat_words = ("flat", "low", "small", "weak", "underdeveloped", "depressed")
        scored_m: list[tuple[float, dict[str, Any]]] = []
        for rule in corpus.get("rules", []):
            if rule.get("category") != "mounts":
                continue
            text_l = (rule.get("text") or "").lower()
            mount_names = [key]
            if key == "apollo":
                mount_names.extend(("apollo", "sun"))
            if key == "mars":
                mount_names.append("mars")
            if not any(n in text_l or f"mount of {n}" in text_l for n in mount_names):
                continue
            if level == "prominent" and not any(w in text_l for w in prom_words):
                continue
            if level == "flat" and not any(w in text_l for w in flat_words):
                continue
            s = 1.0 + text_l.count(key) * 0.5
            if f"{key} mount" in text_l:
                s += 2.0
            scored_m.append((s, rule))
        scored_m.sort(key=lambda x: -x[0])
        seen: set[str] = set()
        rules = []
        for s, rule in scored_m:
            sig = rule.get("id") or rule.get("text", "")[:80]
            if sig in seen:
                continue
            seen.add(sig)
            rules.append(
                {
                    "score": round(s, 2),
                    "id": rule.get("id"),
                    "book": rule.get("book"),
                    "page": rule.get("page"),
                    "category": "mounts",
                    "text": rule.get("text"),
                    "book_label": book_label(rule.get("book")),
                }
            )
            if len(rules) >= limit:
                break
        return rules

    if kind == "finger":
        aliases = {
            "index": ("index finger", "jupiter finger", "mirror finger", "first finger"),
            "middle": ("middle finger", "saturn finger", "second finger"),
            "ring": ("ring finger", "apollo finger", "third finger"),
            "pinky": ("little finger", "mercury finger", "pinky", "fourth finger"),
        }
        lc = str(props.get("length_class", ""))
        length_words = (
            ("long", "lengthy", "longer")
            if lc == "long"
            else (("short", "shorter", "small") if lc == "short" else ("average", "normal", "moderate"))
        )
        scored_f: list[tuple[float, dict[str, Any]]] = []
        for rule in corpus.get("rules", []):
            if rule.get("category") != "fingers":
                continue
            text_l = (rule.get("text") or "").lower()
            if not any(a in text_l for a in aliases.get(key, (key,))):
                continue
            if lc in ("long", "short") and not any(w in text_l for w in length_words):
                continue
            s = 2.0
            scored_f.append((s, rule))
        scored_f.sort(key=lambda x: -x[0])
        rules = []
        for s, rule in scored_f[:limit]:
            rules.append(
                {
                    "score": round(s, 2),
                    "id": rule.get("id"),
                    "book": rule.get("book"),
                    "page": rule.get("page"),
                    "category": "fingers",
                    "text": rule.get("text"),
                    "book_label": book_label(rule.get("book")),
                }
            )
        if rules:
            return rules

    rules = match_rules(
        corpus,
        features,
        categories={category} if category else None,
        extra_tags=extra,
        limit=limit,
    )
    return rules
