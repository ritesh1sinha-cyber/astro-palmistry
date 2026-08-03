"""
Match palm features to corpus rules — scored retrieval, no LLM.
"""

from __future__ import annotations

import re
from typing import Any

from palm_api.report_format import (
    CATEGORY_ORDER,
    build_highlights,
    enrich_prediction,
    is_generic_rule,
)
from palm_api.rules_builder import NOISE_RE, load_corpus

FEATURE_TAGS: dict[str, list[str]] = {
    "morphology.finger_palm_ratio.short": ["short", "stumpy", "finger", "animal", "coarse"],
    "morphology.finger_palm_ratio.long": ["long", "finger", "intellect", "mental", "ideal"],
    "morphology.finger_palm_ratio.equal": ["equal", "finger", "palm", "balanced"],
    "morphology.hand_type.earth": ["earth", "square", "practical", "steady"],
    "morphology.hand_type.air": ["air", "square", "communicative", "mental"],
    "morphology.hand_type.fire": ["fire", "energy", "active", "impulsive"],
    "morphology.hand_type.water": ["water", "sensitive", "intuitive", "creative"],
    "morphology.index_vs_ring.index_longer": ["index", "jupiter", "longer", "ambition", "leadership", "pride", "ego"],
    "morphology.index_vs_ring.ring_longer": ["ring", "apollo", "longer", "confidence", "fame", "success", "risk", "enthusiasm"],
    "morphology.index_vs_ring.equal": ["index", "ring", "equal", "balanced"],
    "morphology.thumb.length.long": ["thumb", "long", "strong will", "will", "leadership"],
    "morphology.thumb.length.short": ["thumb", "short", "romance", "romantic"],
    "morphology.thumb.length.average": ["thumb", "balanced", "will"],
    "morphology.thumb.will_vs_logic.will_dominant": ["thumb", "will", "first phalange", "impulsive", "act"],
    "morphology.thumb.will_vs_logic.logic_dominant": ["thumb", "logic", "reason", "second phalange", "plan"],
    "morphology.thumb.opening.wide": ["thumb", "open", "generous", "independent"],
    "morphology.thumb.opening.narrow": ["thumb", "tightly held", "anxious", "cautious"],
    "lines.life.detected.true": ["life line", "vitality", "life"],
    "lines.life.depth.deep": ["deep", "life", "vitality", "strong"],
    "lines.life.depth.medium": ["life", "vitality", "moderate"],
    "lines.life.depth.thin": ["thin", "life", "weak", "delicate"],
    "lines.life.start_zone.jupiter": ["jupiter", "life", "ambition"],
    "lines.life.start_zone.mars": ["mars", "life", "courage", "aggressive"],
    "lines.head.detected.true": ["head line", "mind", "mental"],
    "lines.head.start_relation.merged": ["merged", "head", "life", "dependent", "confidence", "cautious", "joined"],
    "lines.head.start_relation.separated": ["separated", "head", "independent", "self-confident"],
    "lines.head.start_relation.separated_wide": ["separated", "head", "independent", "reckless", "careless", "impulsive"],
    "lines.head.direction.moon": ["moon", "head", "imagination", "creative"],
    "lines.head.direction.straight": ["straight", "head", "logical", "practical"],
    "lines.heart.detected.true": ["heart line", "love", "emotion", "affection"],
    "lines.heart.height.high": ["high", "heart", "ideal", "emotion"],
    "lines.heart.start_zone.jupiter": ["jupiter", "heart", "ideal", "love"],
    "lines.heart.start_zone.saturn": ["saturn", "heart", "practical", "reserved"],
    "lines.fate.detected.true": ["fate line", "career", "destiny"],
    "lines.fate.start_zone.wrist": ["wrist", "fate", "career", "early"],
    "lines.fate.start_zone.mid_palm": ["mid", "fate", "career", "later", "30"],
    "lines.fate.quality.broken": ["break", "fate", "change", "shift"],
    "lines.fate.quality.clear": ["fate", "career", "steady", "destiny"],
    "lines.fate.reach.saturn": ["saturn", "fate", "discipline", "work"],
    "lines.fate.reach.partial": ["fate", "short", "career", "late"],
    "lines.head.direction.straight": ["straight", "head", "logical", "practical"],
    "lines.head.length.long": ["long", "head", "intellect", "broad"],
    "lines.head.length.short": ["short", "head", "focused", "practical"],
    "lines.heart.length.long": ["long", "heart", "devoted", "emotion"],
    "lines.heart.length.short": ["short", "heart", "self", "reserved"],
    "lines.life.sweep.wide": ["wide", "life", "venus", "vitality", "energy"],
    "lines.life.sweep.close_to_thumb": ["narrow", "life", "cautious", "reserved"],
    "lines.life.reach.wrist": ["long", "life", "vitality", "robust"],
    "mounts.jupiter.prominent": ["jupiter", "mount", "leadership", "ambition"],
    "mounts.jupiter.flat": ["jupiter", "mount", "flat", "low", "underdeveloped"],
    "mounts.saturn.prominent": ["saturn", "mount", "discipline", "serious"],
    "mounts.saturn.flat": ["saturn", "mount", "flat", "low"],
    "mounts.venus.prominent": ["venus", "mount", "love", "sensual", "family", "full"],
    "mounts.venus.flat": ["venus", "mount", "flat", "cold"],
    "mounts.moon.prominent": ["moon", "mount", "imagination", "travel"],
    "mounts.moon.flat": ["moon", "mount", "flat", "low"],
    "quality.grade.poor": ["quality", "unclear"],
}

# Minor lines -> keyword tags + (optional) thematic category injected when detected.
MINOR_LINE_TAGS: dict[str, list[str]] = {
    "sun": ["sun line", "apollo", "success", "fame", "recognition", "talent"],
    "mercury": ["mercury line", "health line", "hepatica", "health", "business", "stomach"],
    "marriage": ["marriage line", "affection", "union", "relationship", "partner"],
    "girdle_of_venus": ["girdle of venus", "sensitive", "emotional", "highly strung"],
    "ring_of_solomon": ["ring of solomon", "jupiter", "wisdom", "intuition", "teacher"],
    "children": ["children line", "children", "offspring", "family", "fertility"],
    "travel": ["travel line", "travel", "restlessness", "voyage", "journey", "relocation"],
}
MINOR_LINE_CATEGORY: dict[str, str] = {
    "sun": "fame",
    "mercury": "general",
    "marriage": "heart",
    "girdle_of_venus": "heart",
    "ring_of_solomon": "mounts",
    "children": "heart",
    "travel": "general",
}

MOUNT_LEVEL_WORDS: dict[str, tuple[str, ...]] = {
    "prominent": ("prominent", "full", "high", "raised", "developed", "large", "strong", "well"),
    "flat": ("flat", "low", "underdeveloped", "small", "weak", "depressed", "thin"),
    "moderate": ("moderate", "normal", "medium", "average"),
}

PHRASE_HINTS: list[tuple[re.Pattern[str], float]] = [
    (re.compile(r"life\s*line", re.I), 1.5),
    (re.compile(r"head\s*line", re.I), 1.5),
    (re.compile(r"heart\s*line", re.I), 1.5),
    (re.compile(r"fate\s*line", re.I), 1.5),
    (re.compile(r"\bmount\b", re.I), 1.0),
    (re.compile(r"\bindicates?\b|\bdenotes?\b|\bshows?\b", re.I), 0.75),
]

HEART_LINE_RE = re.compile(r"heart\s*line", re.I)
MOUNT_NAMES = ("jupiter", "saturn", "apollo", "mercury", "mars", "venus", "moon")

CAT_MIN_SCORE: dict[str, float] = {
    "mounts": 2.0,
    "fingers": 2.25,
    "default": 3.0,
}


def _flatten_features(features: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in features.items():
        if k.startswith("_") or k == "points":
            continue
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten_features(v, key))
        elif isinstance(v, list):
            continue
        else:
            out[key] = v
    return out


def _line_flags(features: dict[str, Any]) -> dict[str, bool]:
    lines = features.get("lines") or {}
    return {
        name: bool((lines.get(name) or {}).get("detected"))
        for name in ("life", "head", "heart", "fate")
    }


def _active_tags(flat: dict[str, Any], features: dict[str, Any]) -> set[str]:
    flags = _line_flags(features)
    tags: set[str] = set()
    for k, v in flat.items():
        if k.startswith("lines.heart") and not flags["heart"]:
            continue
        if v is True or v == "true":
            tags.add(f"{k}.true")
        tags.add(f"{k}.{v}")
        if k in FEATURE_TAGS:
            tags.update(FEATURE_TAGS[k])
        # Value-suffixed entries (e.g. "morphology.index_vs_ring.index_longer").
        full = f"{k}.{v}"
        if full in FEATURE_TAGS:
            tags.update(FEATURE_TAGS[full])
        parts = k.split(".")
        if len(parts) >= 2:
            combo = f"{parts[-2]}.{parts[-1]}"
            if combo in FEATURE_TAGS:
                tags.update(FEATURE_TAGS[combo])

    for mount, level in (features.get("mounts") or {}).items():
        if level in ("unknown",):
            continue
        tags.add(f"mount.{mount}.{level}")
        tags.add(mount)
        tags.update(MOUNT_LEVEL_WORDS.get(str(level), ()))

    for mkey, mdata in (features.get("minor_lines") or {}).items():
        if not isinstance(mdata, dict) or not mdata.get("detected"):
            continue
        tags.add(f"minor.{mkey}.detected")
        tags.update(MINOR_LINE_TAGS.get(mkey, [mkey]))
    return tags


def _mount_text_bonus(text_l: str, mounts: dict[str, str]) -> float:
    bonus = 0.0
    for name, level in mounts.items():
        if level not in MOUNT_LEVEL_WORDS:
            continue
        if name not in text_l:
            continue
        level_words = MOUNT_LEVEL_WORDS[level]
        if any(w in text_l for w in level_words):
            bonus += 2.75
        if f"{name} mount" in text_l or f"mount of {name}" in text_l:
            bonus += 1.0
    return bonus


def _score_rule(
    rule: dict[str, Any],
    tags: set[str],
    categories: set[str],
    *,
    line_flags: dict[str, bool],
    mounts: dict[str, str],
    exclude_ids: set[str],
) -> float:
    if rule.get("id") in exclude_ids:
        return -20.0

    text = rule.get("text", "")
    if is_generic_rule(text):
        return -5.0

    text_l = text.lower()
    cat = rule.get("category", "general")
    heart_ok = line_flags["heart"]

    if cat == "heart" and not heart_ok:
        return -12.0
    if not heart_ok and HEART_LINE_RE.search(text):
        if cat in ("heart",):
            return -12.0
        if cat in ("vitality", "mind"):
            return -4.0

    kw = set(rule.get("keywords") or [])
    overlap = len(kw & tags)
    if overlap == 0:
        overlap = sum(1 for t in tags if len(t) > 3 and t in text_l)

    phrase_bonus = 0.0
    for pat, w in PHRASE_HINTS:
        if not pat.search(text):
            continue
        if not heart_ok and "heart" in pat.pattern:
            continue
        phrase_bonus += w

    cat_bonus = 2.5 if cat in categories and overlap >= 1 else 0.0
    mount_bonus = _mount_text_bonus(text_l, mounts) if cat == "mounts" else _mount_text_bonus(text_l, mounts) * 0.65
    length_penalty = -1.0 if len(text) > 500 else 0.0
    short_bonus = 0.5 if 80 <= len(text) <= 280 else 0.0
    noise_penalty = -10.0 if NOISE_RE.search(text) else 0.0

    return overlap + phrase_bonus + cat_bonus + mount_bonus + length_penalty + short_bonus + noise_penalty


def _categories_from_features(features: dict[str, Any]) -> set[str]:
    flags = _line_flags(features)
    cats: set[str] = set()
    if flags["life"]:
        cats.add("vitality")
    if flags["head"]:
        cats.add("mind")
    if flags["heart"]:
        cats.add("heart")
    if flags["fate"]:
        cats.add("career")

    mounts = features.get("mounts") or {}
    if any(v in ("prominent", "flat") for v in mounts.values()):
        cats.add("mounts")

    for mkey, mdata in (features.get("minor_lines") or {}).items():
        if isinstance(mdata, dict) and mdata.get("detected"):
            cats.add(MINOR_LINE_CATEGORY.get(mkey, "general"))

    if features.get("morphology"):
        cats.add("fingers")
    if not cats:
        cats.add("general")
    return cats


def _dedupe_rules(scored: list[tuple[float, dict[str, Any]]]) -> list[tuple[float, dict[str, Any]]]:
    seen: set[str] = set()
    out: list[tuple[float, dict[str, Any]]] = []
    for s, rule in scored:
        key = re.sub(r"\W+", "", rule.get("text", "").lower())[:120]
        if key in seen:
            continue
        seen.add(key)
        out.append((s, rule))
    return out


def _min_score_for_category(cat: str, mounts: dict[str, str]) -> float:
    if cat == "mounts" and any(v in ("prominent", "flat") for v in mounts.values()):
        return CAT_MIN_SCORE["mounts"]
    if cat == "fingers":
        return CAT_MIN_SCORE["fingers"]
    return CAT_MIN_SCORE["default"]


def _pick_by_category(
    scored: list[tuple[float, dict[str, Any]]],
    *,
    per_cat: int = 2,
    mounts: dict[str, str],
) -> dict[str, list[dict[str, Any]]]:
    by_cat: dict[str, list[tuple[float, dict[str, Any]]]] = {}
    for s, rule in scored:
        cat = rule.get("category", "general")
        if s < _min_score_for_category(cat, mounts):
            continue
        by_cat.setdefault(cat, []).append((s, rule))

    result: dict[str, list[dict[str, Any]]] = {}
    for cat in CATEGORY_ORDER:
        items = sorted(by_cat.get(cat, []), key=lambda x: -x[0])[:per_cat]
        if items:
            result[cat] = [
                enrich_prediction({
                    "score": round(s, 2),
                    "id": rule["id"],
                    "book": rule.get("book"),
                    "page": rule.get("page"),
                    "category": cat,
                    "text": rule["text"],
                })
                for s, rule in items
            ]
    return result


def match_rules(
    corpus: dict[str, Any],
    features: dict[str, Any],
    *,
    categories: set[str] | None = None,
    extra_tags: set[str] | None = None,
    limit: int = 5,
    exclude_rule_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Score corpus rules for one palm point or narrowed category."""
    line_flags = _line_flags(features)
    mounts = features.get("mounts") or {}
    tags = _active_tags(_flatten_features(features), features)
    if extra_tags:
        tags |= extra_tags
    cats = categories or _categories_from_features(features)
    exclude = exclude_rule_ids or set()
    floor = min(CAT_MIN_SCORE.values())

    scored: list[tuple[float, dict[str, Any]]] = []
    for rule in corpus.get("rules", []):
        cat = rule.get("category", "general")
        if categories and cat not in categories:
            continue
        s = _score_rule(
            rule,
            tags,
            cats,
            line_flags=line_flags,
            mounts=mounts,
            exclude_ids=exclude,
        )
        if s >= floor:
            scored.append((s, rule))
    scored.sort(key=lambda x: -x[0])
    scored = _dedupe_rules(scored)
    return [
        enrich_prediction(
            {
                "score": round(s, 2),
                "id": rule["id"],
                "book": rule.get("book"),
                "page": rule.get("page"),
                "category": rule.get("category"),
                "text": rule["text"],
            },
            trim_for_snapshot=False,
        )
        for s, rule in scored[:limit]
    ]


def predict(
    features: dict[str, Any],
    *,
    per_category: int = 2,
    corpus: dict[str, Any] | None = None,
    exclude_rule_ids: set[str] | None = None,
) -> dict[str, Any]:
    corpus = corpus or load_corpus()
    flat = _flatten_features(features)
    line_flags = _line_flags(features)
    mounts = features.get("mounts") or {}
    tags = _active_tags(flat, features)
    cats = _categories_from_features(features)
    exclude = exclude_rule_ids or set()
    floor = min(CAT_MIN_SCORE.values())

    scored: list[tuple[float, dict[str, Any]]] = []
    for rule in corpus.get("rules", []):
        s = _score_rule(
            rule,
            tags,
            cats,
            line_flags=line_flags,
            mounts=mounts,
            exclude_ids=exclude,
        )
        if s >= floor:
            scored.append((s, rule))
    scored.sort(key=lambda x: -x[0])
    scored = _dedupe_rules(scored)

    by_category = _pick_by_category(scored, per_cat=per_category, mounts=mounts)
    flat_preds = [p for items in by_category.values() for p in items]
    flat_preds.sort(key=lambda x: -x["score"])

    skip_hl = set()
    if not line_flags["heart"]:
        skip_hl.add("heart")

    highlights = build_highlights(by_category, skip_categories=skip_hl)

    return {
        "corpus_rules_total": corpus.get("rule_count", 0),
        "matched_count": len(flat_preds),
        "predictions": flat_preds[:12],
        "by_category": by_category,
        "highlights": highlights,
        "heart_line_detected": line_flags["heart"],
        "active_feature_tags": sorted(tags)[:40],
    }


def features_to_narrative(features: dict[str, Any]) -> list[str]:
    lines = []
    q = features.get("quality", {})
    lines.append(f"Image quality: {q.get('grade', '?')} (score {q.get('score', '?')})")
    m = features.get("morphology", {})
    lines.append(f"Hand type: {m.get('hand_type', '?')}; finger/palm ratio: {m.get('finger_palm_ratio', '?')}")
    for name in ("life", "head", "heart", "fate"):
        ln = features.get("lines", {}).get(name, {})
        if ln.get("detected"):
            parts = [f"{k}={v}" for k, v in ln.items() if k not in ("detected", "points")]
            lines.append(f"{name.title()} line: detected ({', '.join(parts)})")
        else:
            lines.append(f"{name.title()} line: not reliably detected")
    mounts = features.get("mounts", {})
    if mounts:
        lines.append("Mounts: " + ", ".join(f"{k}={v}" for k, v in mounts.items()))
    minor = features.get("minor_lines", {})
    detected_minor = [m.get("title", k) for k, m in minor.items() if isinstance(m, dict) and m.get("detected")]
    if detected_minor:
        lines.append("Minor lines present: " + ", ".join(detected_minor))
    return lines


def features_to_rows(features: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    q = features.get("quality", {})
    rows.append({"area": "Photo quality", "finding": f"{q.get('grade', '?').title()} ({q.get('score', '?')})"})
    m = features.get("morphology", {})
    rows.append({"area": "Hand type", "finding": str(m.get("hand_type", "?")).title()})
    rows.append({"area": "Finger / palm ratio", "finding": str(m.get("finger_palm_ratio", "?")).title()})
    for name in ("life", "head", "heart", "fate"):
        ln = features.get("lines", {}).get(name, {})
        if ln.get("detected"):
            detail = ", ".join(
                f"{k.replace('_', ' ')}: {v}"
                for k, v in ln.items()
                if k not in ("detected", "points")
            )
            rows.append({"area": f"{name.title()} line", "finding": detail})
        else:
            rows.append({"area": f"{name.title()} line", "finding": "Not reliably detected — check overlay"})
    for mount, level in (features.get("mounts") or {}).items():
        if level and level != "unknown":
            rows.append({"area": f"{mount.title()} mount", "finding": level.title()})
    for mkey, mdata in (features.get("minor_lines") or {}).items():
        if not isinstance(mdata, dict):
            continue
        title = mdata.get("title", mkey.replace("_", " ").title())
        if mdata.get("detected"):
            extra = mdata.get("strength") or ""
            cnt = mdata.get("count")
            detail = "Present" + (f" ({extra})" if extra else "")
            if cnt:
                detail += f" — about {cnt}"
            rows.append({"area": title, "finding": detail})
        else:
            rows.append({"area": title, "finding": "Not clearly present"})
    return rows
