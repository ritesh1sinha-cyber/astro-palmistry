"""Saraswati astro-palmistry book lane — photo-only signals for palm confluence.

The astro_palmistry_* modules live under engines/astro but implement a second
palmistry system (Jyotis Saraswati). This adapter runs the photo-only parts
and returns per-aspect signals that merge into life_aspects confluence — not a
separate HTML section.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

_ASTRO = Path(__file__).resolve().parents[1] / "astro"
if str(_ASTRO) not in sys.path:
    sys.path.insert(0, str(_ASTRO))

METHOD = "Saraswati palmistry"

# Book DOMAIN_ZONES → palm_api life_aspects keys
_ZONE_TO_ASPECT: dict[str, str] = {
    "career": "career",
    "gains": "wealth",
    "home": "wealth",
    "luck": "fortune",
    "health": "health",
    "longevity": "health",
    "children": "love",
}


def _scrub(text: str) -> str:
    if not text:
        return ""
    try:
        from palm_astro_bridge import scrub_lifespan  # noqa: PLC0415
        return scrub_lifespan(text)
    except Exception:  # noqa: BLE001
        return text


def _add(out: dict[str, list], aspect: str, text: str, *,
         direction: str = "positive", agrees: bool = False) -> None:
    text = _scrub(text.strip())
    if not text or len(text) < 18:
        return
    out.setdefault(aspect, []).append({
        "text": text,
        "direction": direction,
        "method": METHOD,
        "reinforced": agrees,
        "book": "jyotis_saraswati",
        "book_label": "Jyotis Saraswati",
        "page": None,
        "quote": None,
    })


def _phalange_signals(image_paths: list[Path]) -> dict[str, list[dict]]:
    out: dict[str, list] = {}
    try:
        from astro_palmistry_phalange_cv import (  # noqa: PLC0415
            analyze_from_paths, aggregate_for_engine,
        )
        from astro_palmistry_engine import (  # noqa: PLC0415
            counts_from_manual_table, derive_from_lines,
        )
    except Exception:  # noqa: BLE001
        return out

    cv = analyze_from_paths(image_paths)
    agg = cv.get("aggregated") or aggregate_for_engine(
        cv.get("left"), cv.get("right"))
    if not agg:
        return out

    try:
        counts = counts_from_manual_table(**agg)
        derived = derive_from_lines(counts)
    except Exception:  # noqa: BLE001
        return out

    _add(out, "character",
         f"You come across as a {derived.ascendant_sign} temperament with a "
         f"{derived.solar_sign} tone — finger length and palm shape should match.",
         direction="mixed")
    _add(out, "mind",
         f"Your thinking rhythm runs {derived.weekday}-born and {derived.paksha} — "
         f"expect quick switches or steady focus depending on the week.",
         direction="mixed")
    tri = derived.jupiter_triplicity[0] if derived.jupiter_triplicity else ""
    if tri:
        _add(out, "career",
             f"Sponsorship and public credit tend to open through {tri} qualities "
             f"in your work life.",
             direction="positive")
    return out


def _morphology_signals(left: Optional[Path], right: Optional[Path]) -> dict[str, list[dict]]:
    out: dict[str, list] = {}
    if not left or not right:
        return out
    try:
        from astro_palmistry_morphology import analyze_morphology_both_hands  # noqa: PLC0415
        morph = analyze_morphology_both_hands(left, right, chart_pc=None)
    except Exception:  # noqa: BLE001
        return out

    for hand_key in ("left", "right"):
        hand = morph.get(hand_key) or {}
        for sec_key, aspect in (
            ("hand_type", "character"),
            ("three_worlds", "mind"),
            ("finger_tips", "mind"),
            ("major_lines", "health"),
            ("special_marks", "fortune"),
        ):
            sec = (hand.get("sections") or {}).get(sec_key) or {}
            for line in (sec.get("lines") or [])[:2]:
                _add(out, aspect, line)

    xvii = morph.get("chapter_xvii") or {}
    for note in (xvii.get("notes") or [])[:2]:
        _add(out, "character", note)
    return out


def _longevity_signal(dom_feats: dict) -> dict[str, list[dict]]:
    out: dict[str, list] = {}
    if not dom_feats:
        return out
    try:
        from astro_palmistry_longevity import longevity_confluence  # noqa: PLC0415
        long = longevity_confluence(dom_feats, planets=None)
    except Exception:  # noqa: BLE001
        return out

    verdict = str(long.get("verdict") or "").strip()
    if verdict:
        _add(out, "health",
             f"Vitality reads {verdict} on your life line — recovery responds to "
             f"routine, not force.",
             direction="positive" if "strong" in verdict.lower()
             or "good" in verdict.lower() else "mixed")
    return out


def _zone_signals(image_paths: list[Path]) -> dict[str, list[dict]]:
    out: dict[str, list] = {}
    try:
        import cv2  # noqa: PLC0415
        from astro_palmistry_zone_cv import (  # noqa: PLC0415
            DOMAIN_ZONES, inspect_roi, mount_zones_from_landmarks,
        )
    except Exception:  # noqa: BLE001
        return out

    try:
        import mediapipe as mp  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return out

    hands = mp.solutions.hands
    for path in image_paths[:2]:
        bgr = cv2.imread(str(path))
        if bgr is None:
            continue
        h, w = bgr.shape[:2]
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        with hands.Hands(static_image_mode=True, max_num_hands=1) as det:
            res = det.process(rgb)
        if not res.multi_hand_landmarks:
            continue
        pts = res.multi_hand_landmarks[0].landmark
        zones = mount_zones_from_landmarks(pts, w, h)
        for domain, zids in DOMAIN_ZONES.items():
            aspect = _ZONE_TO_ASPECT.get(domain, "fortune")
            for zid in zids[:2]:
                box = zones.get(zid)
                if not box:
                    continue
                x0, y0, x1, y1 = box
                roi = bgr[y0:y1, x0:x1]
                if roi.size < 100:
                    continue
                metrics = inspect_roi(roi)
                if not metrics.get("readable"):
                    continue
                stress = metrics.get("stress_lines", 0)
                sparse = metrics.get("sparse", False)
                if stress >= 2:
                    _add(out, aspect,
                         f"Line stress shows in your {domain} area — "
                         f"go steady and avoid haste.",
                         direction="mixed")
                elif not sparse and metrics.get("line_count", 0) >= 2:
                    _add(out, aspect,
                         f"Clear lines in your {domain} area — "
                         f"{domain} themes have workable support on the hand.",
                         direction="positive")
    return out


def signals(
    image_paths: list[str | Path],
    dom_feats: dict[str, Any],
    active_hand: str = "right",
) -> dict[str, list[dict[str, Any]]]:
    """aspect key → signal dicts for merge into build_life_aspects."""
    paths = [Path(p) for p in image_paths if Path(p).is_file()]
    if not paths:
        return {}

    left = next((p for p in paths if "left" in p.name.lower()), None)
    right = next((p for p in paths if "right" in p.name.lower()), None)
    if not left and len(paths) >= 2:
        left, right = paths[0], paths[1]
    elif not right:
        right = paths[0]

    merged: dict[str, list] = {}
    for block in (_phalange_signals(paths),
                  _morphology_signals(left, right),
                  _longevity_signal(dom_feats or {}),
                  _zone_signals(paths)):
        for key, rows in block.items():
            merged.setdefault(key, []).extend(rows)
    return merged
