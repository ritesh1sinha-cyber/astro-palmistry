"""
Confluence reading: synthesize LEFT + RIGHT palms into one combined report.

Palmistry convention:
- Dominant hand  = conscious self; current, developed, what you have made of life.
- Non-dominant   = subconscious; innate wiring and inherited potential.

We compare each major line and mount across hands and produce a single, plain
verdict per feature plus an overall synthesis and a merged, deduped set of
book-backed predictions.
"""

from __future__ import annotations

from typing import Any

from palm_api.life_aspects import build_life_aspects

LINE_TITLES: dict[str, str] = {
    "life": "Life line",
    "head": "Head line",
    "heart": "Heart line",
    "fate": "Fate line",
}

LINE_THEME: dict[str, str] = {
    "life": "vitality and life energy",
    "head": "thinking and decision-making",
    "heart": "emotional and relationship life",
    "fate": "career direction and life path",
}

_DEPTH_RANK = {"thin": 1, "faint": 1, "medium": 2, "deep": 3}
_QUALITY_RANK = {"broken": 1, "faint": 1, "clear": 2}
_LEN_RANK = {"short": 1, "partial": 1, "long": 2, "wrist": 2}
_MOUNT_RANK = {"flat": 1, "moderate": 2, "prominent": 3, "unknown": 0}


def _line_strength(props: dict[str, Any]) -> int:
    try:
        from palm_api.measurements import line_strength_score
        return line_strength_score(props)
    except Exception:  # noqa: BLE001
        if not props or not props.get("detected"):
            return 0
        score = _DEPTH_RANK.get(str(props.get("depth")), 1)
        score += _QUALITY_RANK.get(str(props.get("quality")), 1)
        score += _LEN_RANK.get(str(props.get("length") or props.get("reach")), 1)
        return score


def _line_confluence(
    key: str,
    dom: dict[str, Any],
    non: dict[str, Any],
    dom_label: str,
    non_label: str,
) -> dict[str, Any] | None:
    dom_det = bool(dom.get("detected"))
    non_det = bool(non.get("detected"))
    theme = LINE_THEME.get(key, "this area")
    title = LINE_TITLES.get(key, key.title())

    if not dom_det and not non_det:
        return None
    if dom_det != non_det:
        present = dom_label if dom_det else non_label
        try:
            from palm_api import palm_voice as PV
            pred = PV.compose(
                scenario=(
                    f"Your {theme} reads clearly on your {present} hand only — "
                    + ("actively expressed in your current life."
                       if dom_det else "more an innate tendency than a developed trait yet.")
                ),
                backing=f"{PV._line_name(key)} one-hand ({present})",
            )
            statement = pred.text_block()
        except Exception:  # noqa: BLE001
            statement = (
                f"Your {theme} reads clearly on your {present} hand only."
            )
        return {"key": key, "title": title, "agreement": "one_hand", "statement": statement}

    ds, ns = _line_strength(dom), _line_strength(non)
    try:
        from palm_api import palm_voice as PV
        if ds > ns + 1:
            agreement = "developed"
            pred = PV.line_confluence_statement(key, dom_label, theme, "developed")
        elif ns > ds + 1:
            agreement = "latent"
            pred = PV.line_confluence_statement(key, non_label, theme, "latent")
        else:
            agreement = "reinforced"
            pred = PV.line_confluence_statement(key, dom_label, theme, "reinforced")
        statement = pred.text_block()
    except Exception:  # noqa: BLE001
        agreement = "reinforced"
        statement = f"Your {theme} is consistent across both hands."
    return {"key": key, "title": title, "agreement": agreement, "statement": statement}


def _mount_confluence(
    dom_mounts: dict[str, str],
    non_mounts: dict[str, str],
    dom_label: str,
    non_label: str,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    names = {
        "jupiter": "Jupiter (ambition)",
        "saturn": "Saturn (discipline)",
        "apollo": "Sun/Apollo (creativity)",
        "mercury": "Mercury (communication)",
        "mars": "Mars (courage)",
        "venus": "Venus (warmth)",
        "moon": "Moon (imagination)",
    }
    for m, label in names.items():
        d = _MOUNT_RANK.get(str(dom_mounts.get(m, "unknown")), 0)
        n = _MOUNT_RANK.get(str(non_mounts.get(m, "unknown")), 0)
        if d == 0 and n == 0:
            continue
        if abs(d - n) >= 1:
            # `label` is "Planet (trait)" — the trait word is what belongs in a
            # jargon-free sentence; the planet name itself is astrology jargon
            # that has no place in a palmistry reading.
            trait = label.split("(", 1)[1].rstrip(")").strip().lower() if "(" in label else label.lower()
            try:
                from palm_api import palm_voice as PV
                plain = PV._mount_name(m)
                if d > n:
                    developed_templates = {
                        "ambition": "You seem to have grown into a stronger need to lead, influence decisions or be recognized for your contribution.",
                        "discipline": "You seem to have grown more comfortable carrying responsibility and staying steady when things get demanding.",
                        "creativity": "Your lived hand suggests you have developed a stronger need to create, improve or put your own stamp on things.",
                        "communication": "Your lived hand suggests communication has become a more active strength — explaining, negotiating or connecting people may come more naturally now.",
                        "warmth": "Your lived hand suggests you have developed a stronger need for warmth, closeness and supportive relationships.",
                        "courage": "Your lived hand suggests greater confidence in facing pressure, competition or difficult situations.",
                        "imagination": "Your lived hand suggests a stronger need for variety, imagination or a change of scene.",
                    }
                    scenario = developed_templates.get(
                        trait, f"You seem to have developed more {trait} in the way you handle life now."
                    )
                    pred = PV.compose(
                        scenario=scenario,
                        backing=f"{plain} stronger on {dom_label} hand",
                    )
                else:
                    latent_templates = {
                        "ambition": "The underlying hand suggests more ambition and leadership drive than you may currently express openly.",
                        "discipline": "The underlying hand suggests a natural capacity for discipline that may be stronger than your current circumstances require.",
                        "creativity": "The underlying hand suggests creative ability that you may not always give enough room to express.",
                        "communication": "The underlying hand suggests communication ability that may be under-used in your current routine.",
                        "warmth": "The underlying hand suggests a strong need for warmth and close family connection, even if you express it selectively.",
                        "courage": "The underlying hand suggests more courage and resilience than you may show until a situation really demands it.",
                        "imagination": "The underlying hand suggests a strong imaginative side that may need more variety or creative space.",
                    }
                    scenario = latent_templates.get(
                        trait, f"The underlying hand suggests more {trait} than you may currently express."
                    )
                    pred = PV.compose(
                        scenario=scenario,
                        backing=f"{plain} stronger on {non_label} hand",
                    )
                txt = pred.text_block()
            except Exception:  # noqa: BLE001
                txt = f"Your {trait} reads differently between hands."
            out.append({"mount": m, "statement": txt})
    return out


_AUSPICIOUS = {"fish", "trident", "triangle", "square", "star"}


def _marks_confluence(
    dom: dict[str, Any],
    non: dict[str, Any],
    dom_label: str,
    non_label: str,
) -> list[dict[str, str]]:
    dom_marks = {(m.get("type"), m.get("zone")): m for m in (dom.get("special_marks") or [])}
    non_marks = {(m.get("type"), m.get("zone")): m for m in (non.get("special_marks") or [])}
    def _base(m: dict[str, Any]) -> str:
        meaning = (m.get("meaning") or "").strip()
        if meaning:
            return meaning
        title = m.get("title", "A mark")
        zone = str(m.get("zone", "palm")).lower()
        try:
            from palm_api import palm_voice as PV
            loc = PV._mount_name(zone)
            return f"{title} on {loc}."
        except Exception:  # noqa: BLE001
            return f"{title} on your palm."

    out: list[dict[str, str]] = []
    for kz, m in dom_marks.items():
        base = _base(m)
        try:
            from palm_api import palm_voice as PV
            if kz in non_marks:
                pred = PV.compose(
                    scenario=f"{base} It shows on both hands — give it real weight.",
                    backing=f"mark on {PV._mount_name(str(m.get('zone', 'palm')))} both hands",
                )
            else:
                pred = PV.compose(
                    scenario=f"{base} It shows on your {dom_label} hand — active in your life now.",
                    backing=f"mark on {PV._mount_name(str(m.get('zone', 'palm')))} ({dom_label})",
                )
            txt = pred.text_block()
        except Exception:  # noqa: BLE001
            txt = base
        out.append({"statement": txt})
    for kz, m in non_marks.items():
        if kz in dom_marks:
            continue
        base = _base(m)
        out.append({"statement": (
            f"{base} It shows only on your {non_label} hand — an inborn potential "
            f"you have not fully expressed yet."
        )})
    return out


def _build_chronological_predictions(
    dom_checklist: list[dict[str, Any]],
    dom_feats: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Age-anchored turning points from the REAL measured line timings.

    Every dated prediction carries the engine's own computed age window from the
    Cheiro seven-year division on the actual line pixels — never a fixed script.
    When no line timing resolves, we fall back to a conservative set of windows
    anchored to whatever the photograph actually supports.
    """
    try:
        from palm_api.vedic_profile import build_turning_points
        points = build_turning_points({"numbered_checklist": dom_checklist, "features": dom_feats or {}},
                                      dom_feats or {}, age=0)
        if points:
            return points
    except Exception:  # noqa: BLE001
        pass
    return []


def build_confluence(
    blocks: dict[str, Any],
    active_hand: str,
    *,
    saraswati_signals: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any] | None:
    """Combine right + left analysis blocks into one confluence reading."""
    right = blocks.get("right")
    left = blocks.get("left")
    if not right or not left:
        return None

    dom_key = "left" if active_hand == "left" else "right"
    non_key = "right" if dom_key == "left" else "left"
    dom = blocks[dom_key]
    non = blocks[non_key]
    dom_label = dom_key.title()
    non_label = non_key.title()

    dom_feats = dom.get("features") or {}
    non_feats = non.get("features") or {}
    dom_lines = dom_feats.get("lines") or {}
    non_lines = non_feats.get("lines") or {}

    line_items: list[dict[str, Any]] = []
    for key in ("life", "head", "heart", "fate"):
        item = _line_confluence(
            key, dom_lines.get(key) or {}, non_lines.get(key) or {}, dom_label, non_label
        )
        if item:
            line_items.append(item)

    mount_items = _mount_confluence(
        dom_feats.get("mounts") or {}, non_feats.get("mounts") or {}, dom_label, non_label
    )

    predictions = _build_chronological_predictions(dom.get("numbered_checklist") or [], dom_feats=dom_feats)
    marks = _marks_confluence(dom_feats, non_feats, dom_label, non_label)

    vedic_profile = {}
    try:
        from palm_api.vedic_profile import build_vedic_profile
        vedic_profile = build_vedic_profile(
            dom, non, dom_label=dom_label, non_label=non_label, age=30)
    except Exception:  # noqa: BLE001
        vedic_profile = {}

    reinforced = [i["title"] for i in line_items if i["agreement"] == "reinforced"]
    developed = [i["title"] for i in line_items if i["agreement"] == "developed"]
    latent = [i["title"] for i in line_items if i["agreement"] == "latent"]

    summary_parts: list[str] = [
        f"Your {dom_label.lower()} hand is read here as the way these qualities are being expressed now; "
        f"your {non_label.lower()} hand is treated as the underlying tendency you started with."
    ]
    if reinforced:
        summary_parts.append(
            "These areas look similar on both hands, so the reading treats them as relatively stable parts of your life: "
            + ", ".join(reinforced) + "."
        )
    if developed:
        summary_parts.append(
            "The areas that look stronger on your dominant hand suggest qualities you may have developed through experience: "
            + ", ".join(developed) + "."
        )
    if latent:
        summary_parts.append(
            "The areas that look stronger on your other hand suggest abilities or needs that may be present underneath but less fully expressed: "
            + ", ".join(latent) + "."
        )

    life_aspects = build_life_aspects(
        blocks, active_hand, saraswati_signals=saraswati_signals)

    return {
        "dominant_hand": dom_key,
        "non_dominant_hand": non_key,
        "summary": " ".join(summary_parts),
        "lines": line_items,
        "mounts": mount_items,
        "marks": marks,
        "predictions": predictions,
        "vedic_profile": vedic_profile,
        "life_aspects": life_aspects,
    }
