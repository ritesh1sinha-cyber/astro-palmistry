#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Saraswati hand morphology lane: finger length, phalange ratios, thumb, hand type,
three worlds, minor lines, Chapter XVII cross-check.

Each section returns readable / fair / poor and retake slots when unclear.
"""
from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import numpy as np

# Book standard phalange proportions (of total finger length)
BOOK_PHALANGE = (0.20, 0.35, 0.45)

FINGER_ZODIAC = {
    "index": ("Aries", "Taurus", "Gemini"),
    "middle": ("Capricorn", "Aquarius", "Pisces"),
    "ring": ("Cancer", "Leo", "Virgo"),
    "pinky": ("Libra", "Scorpio", "Sagittarius"),
}

PLANET_HAND = {
    "jupiter": "Jupiterian",
    "saturn": "Saturnian",
    "apollo": "Leonine (Sun)",
    "mercury": "Mercurian",
    "mars": "Martian",
    "venus": "Venusian",
    "moon": "Lunar",
}

CAPTURE_GUIDE: dict[str, list[str]] = {
    "full_palm": [
        "Lay hand flat on a plain light background (white or grey paper).",
        "Camera directly above, 25-35 cm distance, no side angle.",
        "Spread fingers naturally ? not tight, not fully splayed.",
        "Use daylight or two soft lamps; avoid shadow across palm centre.",
        "Include full palm from finger bases to wrist crease; thumb fully visible.",
        "Hold phone still; tap to focus on the life-line area before shooting.",
    ],
    "finger_closeup": [
        "Fill the frame with ONE finger from base to nail tip.",
        "Same lighting as full palm; sharp focus on crease lines on phalanges.",
        "Shoot index, middle, ring, pinky separately for each hand if full palm is blurry.",
        "File names: left_index.jpg, right_middle.jpg, left_thumb.jpg, etc.",
    ],
    "thumb_closeup": [
        "Close-up of thumb showing both phalanges and nail.",
        "Thumb opened slightly (30-45 degrees) so base creases are visible.",
        "Check for Yav mark at thumb base ? needs sharp macro focus.",
    ],
    "percussion": [
        "Close-up of outer palm edge (little-finger side) from mid-palm to wrist.",
        "Marriage / travel / Moon mount lines live here; avoid glare on skin.",
    ],
    "nails_skin": [
        "Include nail colour and texture in finger close-ups.",
        "Natural light shows white/pink (Sun) vs yellow (Saturn) better than warm LED.",
    ],
}


def _e(s: Any) -> str:
    return html.escape(str(s))


def _phalange_ratios(pts: np.ndarray, chain: tuple[int, ...]) -> dict[str, Any]:
    """Three phalange fractions for mcp-pip-dip-tip chain."""
    seg = [
        float(np.linalg.norm(pts[chain[i + 1]] - pts[chain[i]]))
        for i in range(len(chain) - 1)
    ]
    total = sum(seg) or 1.0
    fracs = [s / total for s in seg]
    book = BOOK_PHALANGE
    dev = [round(abs(f - b), 2) for f, b in zip(fracs, book)]
    avg_dev = sum(dev) / 3
    if avg_dev < 0.06:
        balance = "book_proportions"
    elif avg_dev < 0.12:
        balance = "moderate_deviation"
    else:
        balance = "strong_deviation"
    signs = None
    return {
        "fractions": [round(f, 2) for f in fracs],
        "book_target": list(book),
        "deviation": dev,
        "balance": balance,
        "avg_deviation": round(avg_dev, 2),
    }


def _planetary_hand_type(mounts: dict[str, str], elemental: str, fingers: dict) -> dict[str, Any]:
    """Book: classify Jupiterian/Saturnian etc. from dominant mount + shape."""
    scores: dict[str, int] = {}
    for m, label in mounts.items():
        if label == "prominent":
            scores[m] = scores.get(m, 0) + 3
        elif label == "moderate":
            scores[m] = scores.get(m, 0) + 1
    # Elemental hints
    if elemental == "air":
        scores["mercury"] = scores.get("mercury", 0) + 2
    elif elemental == "fire":
        scores["mars"] = scores.get("mars", 0) + 2
        scores["apollo"] = scores.get("apollo", 0) + 1
    elif elemental == "earth":
        scores["saturn"] = scores.get("saturn", 0) + 2
        scores["venus"] = scores.get("venus", 0) + 1
    elif elemental == "water":
        scores["moon"] = scores.get("moon", 0) + 2
        scores["venus"] = scores.get("venus", 0) + 1
    # Long index -> Jupiter
    idx = (fingers.get("index") or {}).get("length_class")
    if idx == "long":
        scores["jupiter"] = scores.get("jupiter", 0) + 1
    pinky = (fingers.get("pinky") or {}).get("length_class")
    if pinky == "long":
        scores["mercury"] = scores.get("mercury", 0) + 1

    if not scores:
        primary, secondary = "mixed", "unknown"
    else:
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        primary = PLANET_HAND.get(ranked[0][0], ranked[0][0])
        secondary = PLANET_HAND.get(ranked[1][0], ranked[1][0]) if len(ranked) > 1 else ""
    return {
        "primary": primary,
        "secondary": secondary,
        "elemental_shape": elemental,
        "mount_scores": scores,
    }


def _three_worlds(pts: np.ndarray, w: int, h: int) -> dict[str, Any]:
    """Upper=mind, middle=practical, lower=material (book three worlds)."""
    wrist_y = float(pts[0][1])
    mcp_y = float(np.mean([pts[5][1], pts[9][1], pts[13][1], pts[17][1]]))
    tip_y = float(np.mean([pts[8][1], pts[12][1], pts[16][1], pts[20][1]]))
    heart_y = float((pts[5][1] + pts[9][1]) / 2 + 12)
    return {
        "upper_mind": {"y0": int(tip_y), "y1": int(mcp_y), "share": round((mcp_y - tip_y) / (wrist_y - tip_y + 1), 2)},
        "middle_practical": {"y0": int(mcp_y), "y1": int(heart_y)},
        "lower_material": {"y0": int(heart_y), "y1": int(wrist_y)},
        "concrete_thumb_zone": "wrist to thumb CMC (childhood / past imprint, book)",
    }


def _section_status(quality_grade: str, sharp: float, detected: bool = True, *, geometry: bool = False) -> str:
    if not detected:
        return "poor"
    if geometry and quality_grade in ("good", "fair"):
        return "good" if quality_grade == "good" else "fair"
    if quality_grade == "good" and sharp >= 80:
        return "good"
    if quality_grade in ("good", "fair") and sharp >= 50:
        return "fair"
    if detected and quality_grade == "good":
        return "fair"
    return "poor"


def analyze_one_hand(image_path: Path, hand_label: str) -> dict[str, Any]:
    from palm_api.analyzer import extract_features

    path = Path(image_path)
    if not path.is_file():
        return {"hand": hand_label, "error": f"missing:{path}", "sections": {}}

    feat = extract_features(path, hand=hand_label)
    q = feat.get("quality") or {}
    grade = q.get("grade", "poor")
    score = float(q.get("score") or 0)
    # quality dict has no raw sharpness; approximate from score when needed
    sharp = score * 220.0 if score else 0.0
    morph = feat.get("morphology") or {}
    fingers = feat.get("fingers") or morph.get("fingers") or {}
    mounts = feat.get("mounts") or {}
    lines = feat.get("lines") or {}
    minor = feat.get("minor_lines") or {}
    marks = feat.get("special_marks") or []

    # Phalange proportions (landmarks on warped frame via re-detect)
    from palm_api.analyzer import detect_hand_landmarks, _prepare_warped_palm

    import cv2
    bgr = cv2.imread(str(path))
    pts, _ = detect_hand_landmarks(bgr)
    phalange: dict[str, Any] = {}
    if pts is not None:
        _, wpts, _ = _prepare_warped_palm(bgr, pts)
        chains = {
            "index": (5, 6, 7, 8),
            "middle": (9, 10, 11, 12),
            "ring": (13, 14, 15, 16),
            "pinky": (17, 18, 19, 20),
        }
        for fname, chain in chains.items():
            pr = _phalange_ratios(wpts, chain)
            pr["zodiac_phalanges"] = list(FINGER_ZODIAC[fname])
            phalange[fname] = pr
        thumb_chain = (2, 3, 4)
        tseg = [
            float(np.linalg.norm(wpts[thumb_chain[i + 1]] - wpts[thumb_chain[i]]))
            for i in range(len(thumb_chain) - 1)
        ]
        tt = sum(tseg) or 1.0
        phalange["thumb"] = {
            "will_fraction": round(tseg[1] / tt, 2) if len(tseg) > 1 else 0,
            "logic_fraction": round(tseg[0] / tt, 2) if tseg else 0,
            "zodiac": "1st=Aries (Mars+), 2nd=renunciation signs",
        }
        worlds = _three_worlds(wpts, int(bgr.shape[1]), int(bgr.shape[0]))
    else:
        worlds = {}

    p_hand = _planetary_hand_type(
        mounts, morph.get("hand_type", "unknown"), fingers
    )

    # Section 1: Finger lengths
    finger_lines = []
    for fn in ("index", "middle", "ring", "pinky"):
        fi = fingers.get(fn) or {}
        finger_lines.append(
            f"{fn.title()}: {fi.get('length_class', '?')} vs middle "
            f"(ratio {fi.get('ratio_to_middle', '?')}), setting {fi.get('setting', 'normal')}"
        )
    s1_status = _section_status(grade, sharp, bool(fingers), geometry=True)

    # Section 2: Phalange ratios
    ph_lines = []
    for fn, pr in phalange.items():
        if fn == "thumb":
            ph_lines.append(
                f"Thumb will/logic split {pr.get('will_fraction')}/{pr.get('logic_fraction')}"
            )
        else:
            ph_lines.append(
                f"{fn}: fracs {pr.get('fractions')} book {pr.get('book_target')} "
                f"({pr.get('balance')}) -> signs {', '.join(pr.get('zodiac_phalanges', []))}"
            )
    s2_status = _section_status(grade, sharp, bool(phalange), geometry=True)

    # Section 3: Thumb
    thumb = morph.get("thumb") or {}
    thumb_lines = [
        f"Length vs index: {thumb.get('length', '?')} (ratio {thumb.get('length_ratio', '?')})",
        f"Will vs logic: {thumb.get('will_vs_logic', '?')}",
        f"Opening angle: {thumb.get('opening', '?')} ({thumb.get('angle_deg', '?')} deg)",
    ]
    s3_status = _section_status(grade, sharp, bool(thumb), geometry=True)

    # Section 4: Hand type
    ht_lines = [
        f"Elemental palm shape: {morph.get('hand_type', '?')}",
        f"Finger-to-palm ratio: {morph.get('finger_palm_ratio', '?')}",
        f"Index vs ring: {morph.get('index_vs_ring', '?')}",
        f"Book planetary hand: {p_hand['primary']}"
        + (f" + {p_hand['secondary']}" if p_hand.get("secondary") else ""),
    ]
    s4_status = _section_status(grade, sharp, geometry=True)

    # Section 5: Three worlds
    s5_status = "fair" if worlds else "poor"

    # Section 6: Minor lines
    minor_det = [k for k, v in minor.items() if v.get("detected")]
    minor_lines = [
        f"{minor[k].get('title', k)}: detected" for k in minor_det
    ] or ["No minor lines confidently detected on this print."]
    s6_status = "fair" if minor_det else "poor"

    # Section 7: Major lines (morphology cross-check)
    maj = []
    for k in ("life", "head", "heart", "fate"):
        li = lines.get(k) or {}
        if li.get("detected"):
            maj.append(f"{k}: {li.get('depth', '?')} / {li.get('quality', '?')}")
    s7_status = "good" if len(maj) >= 4 else ("fair" if len(maj) >= 2 else "poor")

    # Section 8: Special marks
    mark_lines = [f"{m.get('type')}: {m.get('meaning', '')[:60]}" for m in marks[:5]]
    s8_status = "fair" if marks else "poor"

    # Section 10: Finger tip shapes (book)
    tip_lines: list[str] = []
    nail_lines: list[str] = []
    s10_status = "poor"
    s11_status = "poor"
    if pts is not None and bgr is not None:
        from astro_palmistry_book_cv import classify_finger_tips, classify_nail_colours, detect_yav_diksha

        tips = classify_finger_tips(pts, bgr)
        nails = classify_nail_colours(pts, bgr)
        sacred = detect_yav_diksha(bgr, pts)
        tip_lines = [f"{k}: {v.get('shape')} (ratio {v.get('tip_to_pip_ratio')})" for k, v in tips.items()]
        # Only report nail colour for nails the detector could actually read — on a
        # full-palm photo the nails are not visible, so we must not guess from skin.
        nail_lines = [
            f"{k}: {v.get('label', '?')}" for k, v in nails.items() if v.get("readable")
        ]
        s10_status = _section_status(grade, sharp, bool(tips), geometry=True)
        nail_readable = sum(1 for v in nails.values() if v.get("readable"))
        s11_status = "good" if nail_readable >= 3 else ("fair" if nail_readable else "poor")
        if sacred.get("yav", {}).get("detected"):
            mark_lines.append(f"Yav at thumb base (conf {sacred['yav']['confidence']})")
            s8_status = "fair"
        if sacred.get("diksha", {}).get("detected"):
            mark_lines.append(f"Diksha under Jupiter (conf {sacred['diksha']['confidence']})")
            s8_status = "fair"

    retake: list[dict[str, str]] = []
    if s2_status == "poor" or grade == "poor":
        retake.append({"slot": f"{hand_label}_finger_closeups", "reason": "phalange creases unclear"})
    if s3_status == "poor":
        retake.append({"slot": f"{hand_label}_thumb", "reason": "thumb base not sharp"})
    if s6_status == "poor":
        retake.append({"slot": f"{hand_label}_percussion", "reason": "minor lines not readable"})
    if s8_status == "poor":
        retake.append({"slot": f"{hand_label}_thumb", "reason": "Yav/special marks need macro"})
    if s10_status == "poor":
        retake.append({"slot": f"{hand_label}_finger_closeups", "reason": "fingertip shape needs macro"})
    if s11_status == "poor":
        retake.append({"slot": f"{hand_label}_finger_closeups", "reason": "nail colour needs finger close-up"})

    return {
        "hand": hand_label,
        "path": str(path),
        "quality": grade,
        "sharpness": round(sharp, 1),
        "sections": {
            "finger_length": {"status": s1_status, "lines": finger_lines},
            "phalange_ratio": {"status": s2_status, "lines": ph_lines},
            "thumb": {"status": s3_status, "lines": thumb_lines},
            "hand_type": {"status": s4_status, "lines": ht_lines, "planetary": p_hand},
            "three_worlds": {"status": s5_status, "data": worlds},
            "minor_lines": {"status": s6_status, "lines": minor_lines, "detected": minor_det},
            "major_lines": {"status": s7_status, "lines": maj},
            "special_marks": {"status": s8_status, "lines": mark_lines or ["None detected"]},
            "finger_tips": {"status": s10_status, "lines": tip_lines or ["Tip shapes need sharper finger close-ups"]},
            "nail_colour": {"status": s11_status, "lines": nail_lines or ["Nails not readable on full palm"]},
        },
        "retake": retake,
        "mounts": mounts,
    }


def chapter_xvii_crosscheck(left_path: Path, right_path: Path, chart: dict | None) -> dict[str, Any]:
    from astro_palmistry_engine import counts_from_manual_table, derive_from_lines
    from astro_palmistry_phalange_cv import analyze_from_paths, aggregate_for_engine

    analysis = analyze_from_paths([left_path, right_path])
    if analysis.get("quality") == "poor":
        return {
            "status": "poor",
            "verdict": "Chapter XVII line counts blocked ? phalange ROIs too blurry on full palms.",
            "needs_retake": analysis.get("needs_retake", []),
            "derived": None,
        }

    agg = analysis.get("aggregated") or {}
    if not agg:
        return {"status": "poor", "verdict": "No phalange counts aggregated.", "derived": None}

    counts = counts_from_manual_table(**agg)
    derived = derive_from_lines(counts)
    verdict_lines = [
        f"CV ascendant sketch: {derived.ascendant_sign}",
        f"Tithi {derived.tithi} ({derived.paksha}), solar {derived.solar_sign}, weekday {derived.weekday}",
        f"Jupiter triplicity: {', '.join(derived.jupiter_triplicity)}",
        f"Saturn triplicity: {', '.join(derived.saturn_triplicity)}",
    ]
    status = "fair"
    chart_notes = []
    if chart:
        lagna = chart.get("lagna") or chart.get("meta", {}).get("lagna")
        if lagna and derived.ascendant_sign != lagna:
            chart_notes.append(f"Chart lagna {lagna} vs palm sketch {derived.ascendant_sign} ? verify with finger close-ups.")
            status = "fair"
        else:
            chart_notes.append(f"Palm ascendant sketch matches chart lagna {lagna}.")
            status = "good"

    return {
        "status": status,
        "verdict": " ".join(verdict_lines),
        "chart_notes": chart_notes,
        "needs_retake": analysis.get("needs_retake", []),
        "derived": {
            "ascendant_sign": derived.ascendant_sign,
            "tithi": derived.tithi,
            "paksha": derived.paksha,
            "solar_sign": derived.solar_sign,
            "weekday": derived.weekday,
        },
    }


def analyze_morphology_both_hands(
    left_path: Path,
    right_path: Path,
    chart_pc: dict | None = None,
) -> dict[str, Any]:
    left = analyze_one_hand(left_path, "left")
    right = analyze_one_hand(right_path, "right")
    ch17 = chapter_xvii_crosscheck(left_path, right_path, chart_pc)

    all_retake: list[dict[str, str]] = []
    for h in (left, right):
        all_retake.extend(h.get("retake") or [])
    if ch17.get("needs_retake"):
        for n in ch17["needs_retake"][:6]:
            all_retake.append({"slot": n.get("slot", "?"), "reason": n.get("reason", "Ch.XVII blurry")})

    # dedupe
    seen: set[str] = set()
    uniq_retake = []
    for r in all_retake:
        if r["slot"] in seen:
            continue
        seen.add(r["slot"])
        uniq_retake.append(r)

    return {
        "left": left,
        "right": right,
        "chapter_xvii": ch17,
        "retake_slots": uniq_retake,
    }


def _status_badge(st: str) -> str:
    colours = {"good": "green", "fair": "amber", "poor": "red"}
    return f'<span class="tag {colours.get(st, "amber")}">{_e(st)}</span>'


def morphology_html(morph: dict[str, Any] | None, chart_lagna: str = "") -> str:
    if not morph:
        return ""

    blocks: list[str] = []
    section_titles = [
        ("finger_length", "1. Finger length (vs middle finger)"),
        ("phalange_ratio", "2. Phalange proportions & zodiac map"),
        ("thumb", "3. Thumb (will / logic / opening)"),
        ("hand_type", "4. Palm shape & planetary hand type"),
        ("three_worlds", "5. Three worlds (mind / practical / material)"),
        ("minor_lines", "6. Minor lines (Sun, Mercury health, marriage, girdle)"),
        ("major_lines", "7. Major line quality cross-check"),
        ("special_marks", "8. Special marks (Yav, Diksha, fish, grille)"),
        ("finger_tips", "10. Finger tip shapes (spatulate / square / conic)"),
        ("nail_colour", "11. Nail colour (Sun / Saturn / Rahu book)"),
    ]

    for hand_key, title in (("left", "Left hand"), ("right", "Right hand")):
        h = morph.get(hand_key) or {}
        if h.get("error"):
            blocks.append(f'<div class="card red"><p><strong>{title}:</strong> {_e(h["error"])}</p></div>')
            continue
        blocks.append(
            f'<div class="card"><h4>{title} ? quality {_status_badge(h.get("quality", "?"))} '
            f'sharpness {_e(h.get("sharpness", "?"))}</h4>'
        )
        secs = h.get("sections") or {}
        for sid, stitle in section_titles:
            sec = secs.get(sid) or {}
            st = sec.get("status", "poor")
            lines = sec.get("lines") or []
            if sid == "three_worlds" and sec.get("data"):
                lines = [
                    "Upper (mind): finger tip to MCP",
                    "Middle (practical): MCP to heart band",
                    "Lower (material): heart band to wrist",
                    f"Concrete zone: {sec['data'].get('concrete_thumb_zone', '')}",
                ]
            ul = "".join(f"<li>{_e(ln)}</li>" for ln in lines)
            blocks.append(
                f'<p class="body"><strong>{_e(stitle)}</strong> {_status_badge(st)}</p>'
                f'<ul class="bullets">{ul}</ul>'
            )
            if sid == "hand_type" and sec.get("planetary"):
                ph = sec["planetary"]
                if chart_lagna:
                    blocks.append(
                        f'<p class="fine">Chart lagna <strong>{_e(chart_lagna)}</strong> - '
                        f'palm suggests <strong>{_e(ph.get("primary", "?"))}</strong> hand '
                        f'(book: use planetary hand, not only square/spatulate).</p>'
                    )
        blocks.append("</div>")

    retake = morph.get("retake_slots") or []

    ch = morph.get("chapter_xvii") or {}
    ch_st = ch.get("status", "poor")
    ch_ul = "".join(f"<li>{_e(n)}</li>" for n in ch.get("chart_notes") or [])
    blocks.append(
        f'<div class="card blue"><h4>9. Chapter XVII phalange line-count cross-check '
        f'{_status_badge(ch_st)}</h4>'
        f'<p class="body">{_e(ch.get("verdict", ""))}</p>'
        f'<ul class="bullets">{ch_ul}</ul>'
        f'<p class="fine">Birth-sketch from phalange line counts needs per-finger close-ups '
        f'when full-palm ROIs are blurry.</p></div>'
    )

    if retake or ch_st == "poor":
        steps_html = ""
        master = CAPTURE_GUIDE["full_palm"]
        steps_html += "<p class='body'><strong>Standard full-palm setup</strong></p>"
        steps_html += "<ol class='steps'>" + "".join(f"<li>{_e(g)}</li>" for g in master) + "</ol>"
        for r in retake[:10]:
            slot = r.get("slot", "")
            guide_key = "finger_closeup"
            if "thumb" in slot:
                guide_key = "thumb_closeup"
            elif "percussion" in slot:
                guide_key = "percussion"
            guide = CAPTURE_GUIDE.get(guide_key, CAPTURE_GUIDE["finger_closeup"])
            steps_html += (
                f'<p class="body"><strong>Slot: {_e(slot)}</strong> - {_e(r.get("reason", ""))}</p>'
                f"<ol class='steps'>" + "".join(f"<li>{_e(g)}</li>" for g in guide) + "</ol>"
            )
        blocks.append(
            f'<div class="card amber"><h4>Photo capture guide (re-shoot checklist)</h4>'
            f"<p class='fine'>Upload as <code>left_index.jpg</code>, <code>right_thumb.jpg</code>, etc.</p>"
            f"{steps_html}</div>"
        )

    return (
        '<div class="section-h">Hand morphology (book sections 1-9)</div>'
        + "".join(blocks)
    )
