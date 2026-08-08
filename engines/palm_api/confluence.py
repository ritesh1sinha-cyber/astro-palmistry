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
            import palm_voice as PV
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
        import palm_voice as PV
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
            try:
                import palm_voice as PV
                plain = PV._mount_name(m)
                if d > n:
                    pred = PV.compose(
                        scenario=f"You have grown into more {label.split('(')[0].strip().lower()} — "
                                 f"it shows more on your {dom_label} hand than you were born with.",
                        backing=f"{plain} stronger on {dom_label} hand",
                    )
                else:
                    pred = PV.compose(
                        scenario=f"Natural {label.split('(')[0].strip().lower()} is there — "
                                 f"express it more; your {non_label} hand shows the fuller pattern.",
                        backing=f"{plain} stronger on {non_label} hand",
                    )
                txt = pred.text_block()
            except Exception:  # noqa: BLE001
                txt = f"Your {label} reads differently between hands."
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
            import palm_voice as PV
            loc = PV._mount_name(zone)
            return f"{title} on {loc}."
        except Exception:  # noqa: BLE001
            return f"{title} on your palm."

    out: list[dict[str, str]] = []
    for kz, m in dom_marks.items():
        base = _base(m)
        try:
            import palm_voice as PV
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


def _human_predictions(dom_checklist: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Human, second-person predictions with age-of-event — no book text."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for it in dom_checklist or []:
        conc = it.get("conclusive") or {}
        verdict = conc.get("verdict")
        if not verdict:
            continue
        sig = verdict[:60]
        if sig in seen:
            continue
        seen.add(sig)
        age = (it.get("timing") or {}).get("estimated_age")
        out.append({
            "title": it.get("title", "Reading"),
            "age": age,
            "text": verdict,
        })
    return out


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

    predictions = _human_predictions(dom.get("numbered_checklist") or [])
    marks = _marks_confluence(dom_feats, non_feats, dom_label, non_label)

    reinforced = [i["title"] for i in line_items if i["agreement"] == "reinforced"]
    developed = [i["title"] for i in line_items if i["agreement"] == "developed"]
    latent = [i["title"] for i in line_items if i["agreement"] == "latent"]

    summary_parts: list[str] = [
        f"This is a combined reading of both hands. Your {dom_label.lower()} (dominant) hand "
        f"shows your current, lived patterns; your {non_label.lower()} hand shows your innate "
        f"wiring and potential."
    ]
    if reinforced:
        summary_parts.append(
            "Reinforced across both hands (stable core traits): " + ", ".join(reinforced) + "."
        )
    if developed:
        summary_parts.append(
            "Grown beyond your blueprint through effort: " + ", ".join(developed) + "."
        )
    if latent:
        summary_parts.append(
            "Innate strengths you may be under-using: " + ", ".join(latent) + "."
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
        "life_aspects": life_aspects,
    }
