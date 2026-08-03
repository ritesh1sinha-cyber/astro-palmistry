#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
combined_report.py — one report that clubs both palmistry lanes:

  1. Descriptive palmistry (palm_api): numbered overlay, major/minor lines,
     mounts, marks, and the confluence life-aspect reading (book-cited).
  2. Astro-palmistry (Saraswati Ch. XVII): phalange line counts -> rough birth
     sketch (tithi, solar sign, weekday, ascendant, outer-planet triplicities).

A short bridge ties the two together (e.g. a full Mount of Jupiter in the
descriptive lane reinforces a Jupiter-strong signature in the astro lane).
"""
from __future__ import annotations

import html
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Optional

from palm_api.pipeline import (
    analyze_image_paths,
    render_lane_html,
    _guess_hand,
    _img_src,
)
from palm_api.report_format import book_label
from astro_palmistry_phalange_cv import analyze_from_paths
from astro_palmistry_engine import counts_from_manual_table, derive_from_lines
from astro_palmistry_longevity import (
    longevity_confluence,
    saraswati_age_fractions,
    _poly_len,
    _point_at_arc_fraction,
    SPAN_YEARS,
    TICK_INTERVAL,
)
from astro_palmistry_morphology import analyze_morphology_both_hands

try:
    from astro_chart_bridge import compute_chart, RITZ_BIRTH
except Exception:  # pragma: no cover - bridge optional
    compute_chart = None  # type: ignore
    RITZ_BIRTH = {}  # type: ignore


def _e(s: Any) -> str:
    return html.escape(str(s))


def _astro_extra_css() -> str:
    # The prediction sections reuse the descriptive report's .aspect-card style,
    # so only a couple of extra classes are needed.
    return """
.bridge{background:#f6f2fa;border-left:4px solid var(--magenta);padding:.7rem 1rem;border-radius:6px;margin:.6rem 0;font-size:.92rem}
.retake li{font-size:.84rem;margin:.25rem 0}
.vchart-lane{--vc-ink:#1c1c28;--vc-accent:#4a3f6b;--vc-green:#1f6b42;--vc-amber:#b86b00;--vc-red:#a82828;--vc-muted:#64647a;--vc-blue:#1a5f8a;--vc-border:#ddd5cb;color:var(--vc-ink)}
.vchart-lane .section-h{font-size:1.08rem;color:var(--vc-accent);margin:1.4rem 0 .6rem;padding-bottom:.3rem;border-bottom:2px solid var(--vc-accent);font-weight:600}
.vchart-lane .card{background:#fff;border:1px solid var(--vc-border);border-radius:10px;padding:1rem 1.1rem;margin-bottom:.8rem}
.vchart-lane .card h3{margin:0 0 .4rem;font-size:1.02rem;font-weight:600}
.vchart-lane .card h4{margin:.8rem 0 .3rem;font-size:.97rem;color:var(--vc-accent)}
.vchart-lane .card .when{font-size:.8rem;color:var(--vc-muted);margin-bottom:.4rem}
.vchart-lane .card .body{margin:.2rem 0;font-size:.95rem}
.vchart-lane .card.green{border-left:4px solid var(--vc-green)}
.vchart-lane .card.amber{border-left:4px solid var(--vc-amber)}
.vchart-lane .card.red{border-left:4px solid var(--vc-red)}
.vchart-lane .card.blue{border-left:4px solid var(--vc-blue)}
.vchart-lane .pill{display:inline-block;font-size:.7rem;font-weight:600;padding:.15rem .6rem;border-radius:20px;margin-top:.5rem}
.vchart-lane .pill.hi{background:#d8f0e0;color:var(--vc-green)}
.vchart-lane .pill.mid{background:#fdebd0;color:var(--vc-amber)}
.vchart-lane .pill.lo{background:#ececf0;color:var(--vc-muted)}
.vchart-lane .bullets{margin:0;padding-left:0;list-style:none}
.vchart-lane .bullets li{margin:.5rem 0;padding-left:1.3rem;position:relative}
.vchart-lane .bullets li::before{content:"\\25C6";position:absolute;left:0;color:var(--vc-accent);font-size:.72rem;top:.15rem}
.vchart-lane .tl{width:100%;border-collapse:collapse;font-size:.86rem;margin-top:.5rem}
.vchart-lane .tl th,.vchart-lane .tl td{border:1px solid var(--vc-border);padding:.4rem .6rem;text-align:left;vertical-align:top}
.vchart-lane .tl th{background:#f0ebe4;font-weight:600}
.vchart-lane .dot-g{color:var(--vc-green);font-weight:700}
.vchart-lane .dot-a{color:var(--vc-amber);font-weight:700}
.vchart-lane .dot-r{color:var(--vc-red);font-weight:700}
.vchart-lane .grid2{display:grid;grid-template-columns:1fr 1fr;gap:.8rem}
@media(max-width:640px){.vchart-lane .grid2{grid-template-columns:1fr}}
.vchart-lane .fine{font-size:.8rem;color:var(--vc-muted);margin-top:.5rem}
.vchart-lane .remedy{background:#f6f2fa;border-radius:8px;padding:.6rem .9rem;margin-top:.6rem;font-size:.9rem}
.vchart-lane .verdict{background:#f8f6ff;border-left:4px solid var(--vc-accent);padding:.7rem .9rem;border-radius:8px;margin-top:.6rem;font-size:.92rem}
"""


# ---------------------------------------------------------------------------
# Book-cited interpretation tables (human prediction, no numbers).
# Each entry: (prediction sentence, book_id, page, verbatim/near-verbatim quote)
# ---------------------------------------------------------------------------
_FINGER_MEANINGS: dict[str, dict[str, tuple]] = {
    "index": {
        "long": (
            "Your index (Jupiter) finger is long and assertive — the finger of ambition and "
            "command. You like to lead, set the rules and be looked up to.",
            "palmistry_for_all", None,
            "The first finger is considered as the Dictator, the Lawgiver, the finger of Ambition.",
        ),
        "short": (
            "Your index finger is short — you would rather not carry the burden of command or "
            "heavy responsibility, and dislike being ordered about.",
            "palmistry_for_all", None,
            "lest your first finger is short in proportion ... you too will have to toe the line.",
        ),
    },
    "ring": {
        "long": (
            "Your ring (Apollo) finger is long — a real desire for glory, recognition and the "
            "limelight; you are drawn to art, display and a touch of risk.",
            "palmistry_for_all", None,
            "The third finger, if extremely long and straight, indicates an extraordinary desire "
            "for glory, celebrity, publicity and the like.",
        ),
    },
    "pinky": {
        "long": (
            "Your little (Mercury) finger is long — a gift for speech, persuasion and language; "
            "you can talk and write your way through life.",
            "palmistry_for_all", None,
            "The fourth, or little finger, if long ... is indicative of power of speech and "
            "subtlety in choice of language.",
        ),
        "short": (
            "Your little finger is short — you express yourself better in writing than aloud, and "
            "can be reserved or shy in front of strangers.",
            "palmistry_for_all", None,
            "A short little finger ... find the greatest difficulty in expressing what they want "
            "to say, but they can write better than speak.",
        ),
    },
}

_TIP_MEANINGS: dict[str, tuple] = {
    "spatulate": (
        "Your fingertips are mainly spatulate (broad, fan-shaped) — you are active, practical and "
        "energetic, a natural doer who needs movement, independence and results you can see.",
        "palmistry_for_all", None,
        "The spatulate hand denotes energy, activity and love of action and independence.",
    ),
    "square": (
        "Your fingertips are mainly square — orderly, methodical and dependable; you respect "
        "routine, fairness and getting things done correctly.",
        "palmistry_for_all", None,
        "The square hand ... is the useful hand, orderly, punctual and methodical.",
    ),
    "conic": (
        "Your fingertips are mainly conic (rounded, tapering) — artistic, quick and led by "
        "feeling and first impressions rather than cold routine.",
        "palmistry_for_all", None,
        "The conic hand ... is the artistic hand, impulsive and guided by impulse and instinct.",
    ),
    "pointed": (
        "Your fingertips are fine and pointed — idealistic, imaginative and drawn to beauty and "
        "the spiritual side of life rather than the practical.",
        "palmistry_for_all", None,
        "The pointed or psychic hand belongs to the idealist and dreamer.",
    ),
}

_NAIL_MEANINGS: dict[str, tuple] = {
    "pink": (
        "Your nails read mostly pink and well-formed — a sign of good circulation, vitality and a "
        "steady, confident temperament that keeps its balance under stress.",
        "palmistry_how_to_master", None,
        "Large nails are auspicious. People with such nails do not lose their balance of mind even "
        "under stress or shocks.",
    ),
    "yellow": (
        "A yellowish tone shows on the nails — a more Saturnine, cautious note; pay attention to "
        "digestion and rest, and temper seriousness with ease.",
        "palmistry_how_to_master", None,
        "The colour and texture of the nails reveal the state of the health and temperament.",
    ),
    "blue": (
        "A bluish or pale tone on the nails points to weaker circulation — protect your energy and "
        "keep warm and well-rested in demanding periods.",
        "palmistry_how_to_master", None,
        "The colour and texture of the nails reveal the state of the health and temperament.",
    ),
    "red": (
        "A reddish nail tone shows a fiery, quick temperament — strong drive and warmth, but watch "
        "a tendency to flare up under pressure.",
        "palmistry_how_to_master", None,
        "The colour and texture of the nails reveal the state of the health and temperament.",
    ),
}

_PLANET_MEANINGS: dict[str, tuple] = {
    "Jupiterian": (
        "Yours reads as a Jupiterian hand — ambitious, proud and naturally commanding; you are "
        "drawn to leadership, honour and a cause to believe in.",
        "palmistry_for_all", 124, "Jupiter = Ambition, power, domination, love of nature.",
    ),
    "Saturnian": (
        "Yours reads as a Saturnian hand — serious, studious and self-contained; you think deeply, "
        "value solitude and earn your wisdom through patience.",
        "palmistry_for_all", 124, "Saturn = Reserve, melancholy, seriousness, study.",
    ),
    "Leonine (Sun)": (
        "Yours reads as a Sun (Apollonian) hand — bright, artistic and warm; you are drawn to "
        "beauty, recognition and self-expression.",
        "palmistry_for_all", 124, "Sun (Apollo) = brilliancy, art, success, celebrity.",
    ),
    "Mercurian": (
        "Yours reads as a Mercurian hand — quick, clever and persuasive; you shine in "
        "communication, business and practical, scientific thinking.",
        "palmistry_for_all", 124, "Mercury = Mentality, commerce, science, expression.",
    ),
    "Martian": (
        "Yours reads as a Martian hand — courageous, energetic and resilient; you meet resistance "
        "head-on and bounce back quickly.",
        "palmistry_for_all", 124, "Mars = courage, resolution, fighting spirit, endurance.",
    ),
    "Venusian": (
        "Yours reads as a Venusian hand — warm, sociable and affectionate; you love comfort, "
        "beauty and good company.",
        "palmistry_for_all", 124, "Venus = Love, sensuality, passion, sympathy.",
    ),
    "Lunar": (
        "Yours reads as a Lunar hand — imaginative, sensitive and restless; you are drawn to "
        "travel, water and the world of dreams and ideas.",
        "palmistry_for_all", 124, "Moon = Imagination, romance, changeability, mysticism.",
    ),
}

_STRENGTH_CLS = {
    "strong": "aspect-strong",
    "moderate": "aspect-moderate",
    "tentative": "aspect-tentative",
}

# ---------------------------------------------------------------------------
# Vedic chart fallback — interpretation tables for the planet positions the
# engine derives from palm lines (Jyotis Saraswati, Chapter XVII).
# ---------------------------------------------------------------------------
_ASC_TRAITS: dict[str, str] = {
    "Aries": "bold, energetic and pioneering — you lead from the front and dislike waiting around.",
    "Taurus": "steady, patient and grounded — you value security, comfort, loyalty and the good things in life.",
    "Gemini": "curious, quick-witted and communicative — you thrive on variety, talk and fresh ideas.",
    "Cancer": "sensitive, nurturing and protective — home, family and feelings are your anchor.",
    "Leo": "warm, proud and expressive — a natural performer who needs to be seen and appreciated.",
    "Virgo": "analytical, precise and helpful — you refine, organise and serve, often quietly.",
    "Libra": "diplomatic, charming and fair-minded — you seek balance, beauty and good partnership.",
    "Scorpio": "intense, determined and private — you probe beneath the surface and transform through crisis.",
    "Sagittarius": "optimistic, free-spirited and philosophical — you chase meaning, travel and truth.",
    "Capricorn": "disciplined, ambitious and responsible — you climb steadily toward lasting achievement.",
    "Aquarius": "independent, original and humane — you think ahead and guard your freedom.",
    "Pisces": "compassionate, imaginative and intuitive — you feel deeply and dream widely.",
}

_SUN_TRAITS: dict[str, str] = {
    "Aries": "a fiery, competitive life-force; channel the drive so it doesn't burn out.",
    "Taurus": "a robust, enduring constitution; watch comfort-eating and stubborn habits.",
    "Gemini": "restless, nervous energy; rest the mind and protect breath and nerves.",
    "Cancer": "vitality tied to emotional security; your digestion mirrors your moods.",
    "Leo": "a strong heart and proud spirit; you shine when appreciated, wilt when ignored.",
    "Virgo": "sensitive digestion and a busy mind; routine and clean living keep you well.",
    "Libra": "vitality through balance; stress shows up in kidneys, skin and sleep.",
    "Scorpio": "deep reserves of regenerative power; intensity needs healthy outlets.",
    "Sagittarius": "abundant, sporty energy; mind the liver, hips and over-indulgence.",
    "Capricorn": "slow-burning stamina; look after bones, knees, joints and avoid overwork.",
    "Aquarius": "uneven, electric energy; keep circulation and ankles moving.",
    "Pisces": "a tender, impressionable constitution; protect your feet, sleep and emotional boundaries.",
}

_JUP_BY_ELEMENT: dict[str, str] = {
    "fire": "growth and good fortune come through bold action, leadership and faith in yourself.",
    "earth": "fortune builds slowly and solidly — through work, property, patience and practical wisdom.",
    "air": "luck flows through communication, learning, networks and ideas; teaching and writing favour you.",
    "water": "blessings arrive through intuition, family, compassion and emotional or spiritual depth.",
}

_SAT_BY_ELEMENT: dict[str, str] = {
    "fire": "your discipline is tested around ego, impatience and leadership — learn measured action.",
    "earth": "Saturn rewards steady duty with material security; the lesson is patience over shortcuts.",
    "air": "lessons come through words, commitments and social duty — say less and mean more.",
    "water": "your tests are emotional — fear, family and letting go; depth and resilience are the reward.",
}

_ELEMENT_PULL: dict[str, str] = {
    "fire": "bold self-assertion",
    "earth": "practical security",
    "air": "ideas and connection",
    "water": "emotional and spiritual depth",
}

_WEEKDAY_TEMPER: dict[str, str] = {
    "Sunday": "a Sun-day temperament — proud, warm and leadership-minded.",
    "Monday": "a Moon-day temperament — sensitive, caring and adaptable.",
    "Tuesday": "a Mars-day temperament — energetic, assertive and courageous.",
    "Wednesday": "a Mercury-day temperament — clever, communicative and versatile.",
    "Thursday": "a Jupiter-day temperament — wise, generous and principled.",
    "Friday": "a Venus-day temperament — loving, artistic and pleasure-appreciating.",
    "Saturday": "a Saturn-day temperament — disciplined, serious and enduring.",
}

_TRIPLICITY_ELEMENT: dict[str, str] = {
    "Aries": "fire", "Leo": "fire", "Sagittarius": "fire",
    "Taurus": "earth", "Virgo": "earth", "Capricorn": "earth",
    "Gemini": "air", "Libra": "air", "Aquarius": "air",
    "Cancer": "water", "Scorpio": "water", "Pisces": "water",
}


def _tri_element(tri) -> str:
    if not tri:
        return "fire"
    return _TRIPLICITY_ELEMENT.get(tri[0], "fire")


def _sign_card(title: str, summary: str, cites: list[tuple], strength: str = "moderate") -> str:
    cl = ""
    seen: set[str] = set()
    for q, b, pg in cites:
        q = (q or "").strip()
        if not q or q in seen:
            continue
        seen.add(q)
        lbl = book_label(b) if b else ""
        pgs = f" p{pg}" if pg else ""
        cl += (
            f'<li><span class="quote">&ldquo;{_e(q)}&rdquo;</span>'
            f'<span class="src">— {_e(lbl)}{_e(pgs)}</span></li>'
        )
    cites_html = f'<ul class="aspect-cites">{cl}</ul>' if cl else ""
    scls = _STRENGTH_CLS.get(strength, "")
    return (
        f'<div class="aspect-card {scls}"><h3>{_e(title)}</h3>'
        f'<p class="aspect-body">{_e(summary)}</p>{cites_html}</div>'
    )


def _dom_hand_morph(morph: dict[str, Any], active_hand: str) -> dict[str, Any]:
    return morph.get(active_hand) or morph.get("right") or morph.get("left") or {}


def _section_lines(hand_morph: dict[str, Any], section: str) -> list[str]:
    return ((hand_morph.get("sections") or {}).get(section) or {}).get("lines") or []


def _section_status(hand_morph: dict[str, Any], section: str) -> str:
    return ((hand_morph.get("sections") or {}).get(section) or {}).get("status") or "poor"


def _dominant_tip_shape(hand_morph: dict[str, Any]) -> str | None:
    shapes: list[str] = []
    for ln in _section_lines(hand_morph, "finger_tips"):
        m = re.match(r"\s*\w+:\s*([a-zA-Z]+)", ln)
        if m:
            shapes.append(m.group(1).lower())
    return Counter(shapes).most_common(1)[0][0] if shapes else None


def _dominant_nail_family(hand_morph: dict[str, Any]) -> str | None:
    text = " ".join(_section_lines(hand_morph, "nail_colour")).lower()
    counts = {
        "pink": text.count("pink") + text.count("white"),
        "yellow": text.count("yellow"),
        "blue": text.count("blue") + text.count("pale"),
        "red": text.count("red"),
    }
    fam = max(counts, key=counts.get)
    return fam if counts[fam] else None


def _has_sacred_mark(hand_morph: dict[str, Any], word: str) -> bool:
    return any(word.lower() in ln.lower() for ln in _section_lines(hand_morph, "special_marks"))


def _build_longevity_overlay(image_path: Path, feats: dict[str, Any], longevity: dict[str, Any] | None,
                             out_path: Path) -> bool:
    """
    Draw the Saraswati longevity overlay on the original photo: the four major
    lines (gold/green/red/orange) with labels and pixel length, plus 5-year age
    ticks along the life line, with age 20 anchored at the Jupiter–Saturn
    perpendicular and the decades 20/40/60/80 labelled.
    """
    import cv2
    import numpy as np

    bgr = cv2.imread(str(image_path))
    if bgr is None:
        return False
    img = bgr.copy()
    h, w = img.shape[:2]
    scale = max(1.0, w / 900.0)
    lines = feats.get("lines") or {}

    colors = {  # BGR
        "life": (30, 180, 220), "head": (60, 170, 40),
        "heart": (40, 40, 220), "fate": (0, 140, 255),
    }
    names = {"life": "Life", "head": "Head", "heart": "Heart", "fate": "Fate"}

    # Draw each detected line + label with measured length
    legend: list[tuple[str, tuple[int, int, int]]] = []
    for k in ("life", "head", "heart", "fate"):
        poly = (lines.get(k) or {}).get("points") or []
        if len(poly) < 2:
            continue
        arr = np.asarray(poly, dtype=np.int32).reshape(-1, 1, 2)
        cv2.polylines(img, [arr], False, colors[k], max(2, int(2 * scale)), cv2.LINE_AA)
        length_px = int(_poly_len(poly))
        legend.append((f"{names[k]} line: {length_px}px", colors[k]))

    # Age ticks along the life line, age 20 anchored at Jupiter-Saturn perpendicular
    life_poly = [(float(x), float(y)) for x, y in ((lines.get("life") or {}).get("points") or [])]
    if len(life_poly) >= 2:
        jup_sat_mid = None
        try:
            from palm_api.analyzer import detect_hand_landmarks
            pts, _ = detect_hand_landmarks(bgr)
            if pts is not None:
                jup_sat_mid = (float((pts[5][0] + pts[9][0]) / 2), float((pts[5][1] + pts[9][1]) / 2))
        except Exception:
            jup_sat_mid = None
        fracs = saraswati_age_fractions(life_poly, jup_sat_mid)
        for age in range(0, SPAN_YEARS + 1, TICK_INTERVAL):
            x, y = _point_at_arc_fraction(life_poly, fracs[age])
            decade = age % 20 == 0
            r = int((5 if decade else 3) * scale)
            cv2.circle(img, (x, y), r, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(img, (x, y), r, (30, 120, 200), max(1, int(scale)), cv2.LINE_AA)
            if decade:
                cv2.putText(img, str(age), (x + int(8 * scale), y + int(5 * scale)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55 * scale, (20, 20, 20),
                            max(1, int(scale)), cv2.LINE_AA)
        if jup_sat_mid:
            jx, jy = _point_at_arc_fraction(life_poly, fracs[20])
            cv2.putText(img, "age 20 (Jupiter/Saturn)", (jx + int(8 * scale), jy - int(8 * scale)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5 * scale, (120, 40, 40),
                        max(1, int(scale)), cv2.LINE_AA)

    # Legend + estimate banner (top-left)
    est_txt = ""
    if longevity and longevity.get("estimate_years"):
        rng = longevity.get("range_years") or []
        est_txt = f"Longevity ~{longevity['estimate_years']} yr"
        if len(rng) == 2:
            est_txt += f" ({rng[0]}-{rng[1]})"
    pad = int(10 * scale)
    line_h = int(22 * scale)
    box_h = pad * 2 + line_h * (len(legend) + (1 if est_txt else 0))
    box_w = int(260 * scale)
    cv2.rectangle(img, (pad, pad), (pad + box_w, pad + box_h), (255, 255, 255), -1)
    cv2.rectangle(img, (pad, pad), (pad + box_w, pad + box_h), (180, 180, 180), 1)
    y = pad + line_h
    if est_txt:
        cv2.putText(img, est_txt, (pad + int(8 * scale), y - int(5 * scale)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6 * scale, (20, 20, 20), max(1, int(scale)), cv2.LINE_AA)
        y += line_h
    for label, col in legend:
        cv2.line(img, (pad + int(8 * scale), y - int(11 * scale)),
                 (pad + int(28 * scale), y - int(11 * scale)), col, max(2, int(3 * scale)), cv2.LINE_AA)
        cv2.putText(img, label, (pad + int(34 * scale), y - int(6 * scale)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5 * scale, (20, 20, 20), max(1, int(scale)), cv2.LINE_AA)
        y += line_h

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    return True


def _longevity_summary(longevity: dict[str, Any] | None, cross_notes: list[str] | None = None,
                       lengths: dict[str, float] | None = None) -> str | None:
    if not longevity or not longevity.get("estimate_years"):
        return None
    est = int(longevity["estimate_years"])
    lo, hi = longevity.get("range_years") or [max(40, est - 7), min(98, est + 7)]
    palm = longevity.get("palm") or {}
    base = longevity.get("palm_base", est)
    delta = longevity.get("chart_delta", 0)
    q = palm.get("life_quality", "clear")
    reach = palm.get("life_reach", "")
    qual = "deep and clearly marked" if q == "clear" else "lightly marked"
    reach_txt = (
        "sweeps well down and around the ball of the thumb"
        if reach == "wrist"
        else "runs a good, even length"
    )
    decade = f"your {int(est // 10 * 10)}s"
    out = (
        f"On the book's 80-year scale (Saturn finger = 80 years; age 20 fixed where the "
        f"Jupiter–Saturn perpendicular meets the life line), your life line is {qual} and "
        f"{reach_txt}, reading to about <strong>{base}</strong> on its own. "
    )
    if cross_notes:
        joined = " ".join(cross_notes)
        sign = "+" if delta >= 0 else ""
        out += (
            f"Cross-checking the other lines then adjusts this by {sign}{delta} years: {joined} "
        )
    out += (
        f"Taken together that points to an active life well into {decade} — about "
        f"<strong>{est}</strong> years (a fair margin of {lo}–{hi}). This reads constitution and "
        f"vitality, never a fixed date."
    )
    return out


def _render_palm_signs(
    analysis: dict[str, Any],
    morph: dict[str, Any],
    longevity: dict[str, Any] | None,
    active_hand: str,
    *,
    cross_notes: list[str] | None = None,
    lengths: dict[str, float] | None = None,
    longevity_overlay_src: str = "",
) -> str:
    """Human, book-cited cards for hand-shape / fingers / tips / nails / lifespan / sacred marks."""
    dom = analysis.get(active_hand) or analysis.get("right") or analysis.get("left") or {}
    feats = dom.get("features") or {}
    fingers = feats.get("fingers") or (feats.get("morphology") or {}).get("fingers") or {}
    hand_morph = _dom_hand_morph(morph, active_hand)

    cards: list[str] = []

    # 1) Lifespan & vitality — book 80-year formula across life/head/heart/fate,
    #    with the four lines + 5-year age ticks marked on the palm.
    lon = _longevity_summary(longevity, cross_notes, lengths)
    if lon:
        img_html = ""
        if longevity_overlay_src:
            img_html = (
                f'<div style="max-width:24rem;margin:.5rem 0"><img src="{longevity_overlay_src}" '
                f'alt="Longevity overlay" style="width:100%;border:1px solid var(--border);border-radius:4px"/>'
                f'<p class="fine" style="text-align:center">Life (gold), Head (green), Heart (red), '
                f'Fate (orange); white dots = 5-year marks, labelled at 20/40/60/80.</p></div>'
            )
        len_html = ""
        if lengths:
            parts = [f"{k.title()} {int(v)}px" for k, v in lengths.items() if v]
            if parts:
                len_html = f'<p class="fine">Measured line lengths on your photo: {_e(", ".join(parts))}.</p>'
        cards.append(
            f'<div class="aspect-card aspect-strong"><h3>Lifespan &amp; vitality</h3>{img_html}'
            f'<p class="aspect-body">{lon}</p>{len_html}</div>'
        )

    # 2) Planetary hand type
    planetary = ((hand_morph.get("sections") or {}).get("hand_type") or {}).get("planetary") or {}
    primary = planetary.get("primary")
    if primary in _PLANET_MEANINGS:
        s, b, pg, q = _PLANET_MEANINGS[primary]
        cards.append(_sign_card("Your ruling hand type", s, [(q, b, pg)]))

    # 3) Fingers — ambition, art & expression
    fcites: list[tuple] = []
    fsent: list[str] = []
    for fn in ("index", "ring", "pinky"):
        lc = (fingers.get(fn) or {}).get("length_class")
        meaning = _FINGER_MEANINGS.get(fn, {}).get(lc)
        if meaning:
            s, b, pg, q = meaning
            fsent.append(s)
            fcites.append((q, b, pg))
    if fsent:
        cards.append(_sign_card("Your fingers — ambition, art & expression", " ".join(fsent), fcites))

    # 4) Fingertips — working style
    tip = _dominant_tip_shape(hand_morph)
    if tip in _TIP_MEANINGS:
        s, b, pg, q = _TIP_MEANINGS[tip]
        cards.append(_sign_card("How you work — fingertip shape", s, [(q, b, pg)]))

    # 5) Nails — constitution (only when nails were actually readable; on a
    #    full-palm photo the nails aren't visible, so we skip this rather than guess).
    nail = _dominant_nail_family(hand_morph)
    if nail in _NAIL_MEANINGS and _section_status(hand_morph, "nail_colour") != "poor":
        s, b, pg, q = _NAIL_MEANINGS[nail]
        cards.append(_sign_card("Nails & constitution", s, [(q, b, pg)]))

    # 6) Sacred / fortunate Indian marks (only when actually seen)
    sacred_bits: list[str] = []
    if _has_sacred_mark(hand_morph, "Yav"):
        sacred_bits.append(
            "A Yav (barley-grain) sign shows at the base of your thumb — a classic mark of "
            "prosperity, learning and good fortune in Indian palmistry."
        )
    if _has_sacred_mark(hand_morph, "Diksha"):
        sacred_bits.append(
            "A Diksha mark under Jupiter points to a spiritual or initiatory turn — a pull toward "
            "guidance, faith or teaching."
        )
    if sacred_bits:
        cards.append(_sign_card(
            "Fortunate & sacred marks", " ".join(sacred_bits),
            [("The Yav (barley) at the thumb base is a sign of fortune and prosperity.",
              "easy_understanding_samudrik", None)],
            strength="tentative",
        ))

    if not cards:
        return ""
    return f"""
<article class="report-card" style="border-left:4px solid var(--magenta)">
  <h2>What your hand shape says about you</h2>
  <p class="lead">Beyond the lines, the <strong>shape</strong> of your hand and fingers
  tells its own story. Each reading below is backed by the books it comes from, and I only
  include what your photos actually show clearly.</p>
  {''.join(cards)}
</article>"""


def _render_astro_identity(derived, quality: str, needs_retake: list[dict]) -> str:
    """
    Vedic chart fallback: when the phalange counts aren't clear (or even when they
    are), turn the planet positions the engine derives from the palm lines into a
    human, life-area prediction — rising sign, Sun, Jupiter, Saturn, Rahu/Ketu and
    Moon temperament. No counts or calculation tables are shown.
    """
    if derived is None:
        return ""

    poor = quality in ("poor", "?")
    asc = derived.ascendant_sign
    sun = derived.solar_sign
    jup_el = _tri_element(derived.jupiter_triplicity)
    sat_el = _tri_element(derived.saturn_triplicity)
    rahu_el = _tri_element(derived.rahu_triplicity)
    ketu_el = _tri_element(derived.ketu_triplicity)

    cards: list[str] = []

    # Nature / lagna
    cards.append(_sign_card(
        f"Your nature — {asc} rising",
        f"With {asc} as your rising sign, you come across as "
        f"{_ASC_TRAITS.get(asc, 'a distinctive blend of traits')} This is the lens through which "
        f"you meet the world and how others first read you.",
        [], strength="moderate",
    ))

    # Vitality / Sun
    cards.append(_sign_card(
        f"Vitality & spirit — Sun in {sun}",
        f"Your Sun in {sun} gives {_SUN_TRAITS.get(sun, 'a distinct core vitality.')} "
        f"This is your inner fuel — protect it and your whole chart runs brighter.",
        [], strength="moderate",
    ))

    # Mind & temperament — paksha + weekday + tithi
    waxing = "Shukla" in (derived.paksha or "")
    moon_mind = (
        "a waxing-Moon mind — outgoing, growth-minded and forward-looking"
        if waxing else
        "a waning-Moon mind — introspective, deep and oriented to results and release"
    )
    cards.append(_sign_card(
        "Mind & temperament",
        f"Born in the {derived.paksha} fortnight around lunar day {derived.tithi}, you carry "
        f"{moon_mind}. Your {derived.weekday} birth-weekday adds {_WEEKDAY_TEMPER.get(derived.weekday, 'a distinct flavour')}",
        [], strength="moderate",
    ))

    # Jupiter — fortune & growth
    cards.append(_sign_card(
        f"Fortune & growth — Jupiter in {jup_el} signs",
        f"Your Jupiter falls in the {jup_el} group ({_e(', '.join(derived.jupiter_triplicity))}); "
        f"{_JUP_BY_ELEMENT.get(jup_el, 'fortune comes in its own way.')}",
        [], strength="moderate",
    ))

    # Saturn — discipline & karma
    cards.append(_sign_card(
        f"Discipline & lessons — Saturn in {sat_el} signs",
        f"Your Saturn falls in the {sat_el} group ({_e(', '.join(derived.saturn_triplicity))}); "
        f"{_SAT_BY_ELEMENT.get(sat_el, 'discipline is asked of you in its own area.')}",
        [], strength="moderate",
    ))

    # Rahu/Ketu — karmic axis
    cards.append(_sign_card(
        "Your karmic axis — Rahu & Ketu",
        f"Your nodal axis runs from {_ELEMENT_PULL.get(ketu_el, 'the familiar')} (Ketu in the "
        f"{ketu_el} group — already-mastered, comfortable ground) toward "
        f"{_ELEMENT_PULL.get(rahu_el, 'new growth')} (Rahu in the {rahu_el} group — where this life "
        f"pulls you to stretch and grow). Lean into the Rahu direction without abandoning your Ketu gifts.",
        [], strength="tentative",
    ))

    # Provenance + (if poor) how to sharpen it
    if poor:
        slots = [r.get("slot", "") for r in (needs_retake or []) if r.get("slot")][:6]
        items = "".join(f"<li>{_e(s)}</li>" for s in slots)
        sharpen = (
            '<div class="callout-warn"><p><strong>This is a provisional fallback.</strong> '
            "On full-palm photos the fine finger-joint creases this method counts can't be resolved "
            "cleanly, so the planet positions above are a rough first pass. For a sharper birth-sketch, "
            "add a single-finger close-up (fill the frame with one finger, base to nail) of:</p>"
            f'<ul class="retake">{items}</ul></div>'
            if slots else
            '<div class="callout-warn"><p><strong>This is a provisional fallback</strong> from rough '
            "phalange counts; confirm the signs against a birth ephemeris.</p></div>"
        )
        lead = (
            "Even though the finger-joint photos weren't sharp enough for a precise count, your palm "
            "lines still sketch a set of planet positions. Here is the <strong>fallback reading from "
            "those positions</strong> — treat it as indicative until confirmed against a real birth chart."
        )
    else:
        sharpen = ""
        lead = (
            "Your palm lines convert into a set of Vedic planet positions (Jyotis Saraswati, Ch. XVII). "
            "Here is what those positions say about you — to be confirmed against a birth ephemeris."
        )

    return f"""
<article class="report-card" style="border-left:4px solid var(--accent)">
  <h2>A second view — your stars, read from your palm</h2>
  <p class="lead">{lead}</p>
  {''.join(cards)}
  <p class="fine">Planet positions derived from your palm lines via the Saraswati phalange method
  (Jyotis Saraswati, Chapter XVII). Sign interpretations follow classical Vedic jyotish and are
  indicative, not a substitute for a calculated birth chart.</p>
  {sharpen}
</article>"""


def _render_birth_chart(pc: dict[str, Any] | None, birth: dict[str, Any] | None,
                        image_paths: list[str | Path] | None = None) -> str:
    """
    Real-ephemeris chart lane: when birth details are supplied we compute the
    actual Vedic chart (PyJHora + Swiss Ephemeris via astro_chart_bridge) and
    read life areas, timeline and health windows from the derived planet
    positions — far more reliable than the palm-derived triplicity sketch.
    """
    if not pc:
        return ""
    try:
        import astro_chart_bridge
        astro_chart_bridge._ensure_on_path()
        from client_report_html import (
            seven_pillars_html, traffic_light_html,
            transition_calendar_html, health_section_html, remedies_html,
        )
        from confluence_longevity_lane import build_longevity_context
    except Exception:
        return ""

    meta = pc.get("meta", {})
    lagna = meta.get("lagna_sign", "?")
    lagna_lord = meta.get("lagna_lord", "?")
    planets = pc.get("planets", {})

    if birth:
        bdesc = (f"computed from your birth details "
                 f"({_e(birth.get('dob', ''))} {_e(birth.get('birth_time', ''))}, "
                 f"{_e(birth.get('place', ''))}) using the Swiss Ephemeris")
    else:
        bdesc = "computed from your birth details using the Swiss Ephemeris"

    key_bits = []
    for nm in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        d = planets.get(nm) or {}
        if d.get("sign"):
            dig = d.get("dignity", "")
            digtxt = f", {dig.replace('_', ' ')}" if dig and dig not in ("neutral_sign", "unknown") else ""
            key_bits.append(
                f"<li><strong>{nm}</strong> in {_e(d['sign'])} "
                f"(house {d.get('house', '?')}{digtxt})</li>"
            )
    snapshot = (
        f'<div class="card"><h3>Your birth chart at a glance</h3>'
        f'<p class="body">This reading is {bdesc}. Your rising sign (lagna) is '
        f'<strong>{_e(lagna)}</strong>, ruled by {_e(lagna_lord)}.</p>'
        f'<ul class="bullets">{"".join(key_bits)}</ul></div>'
    )

    # Per-domain life reading: chart anchors cross-checked against the actual
    # palm mount zones (real chart + palm confluence, not chart-only).
    conf_html = ""
    try:
        from astro_palmistry_anchor_engine import (
            build_anchor_analysis, apply_cv_evidence, human_confluence_html,
        )
        pl = {
            k: v for k, v in planets.items()
            if isinstance(v, dict) and v.get("sign") and v.get("house") is not None and v.get("dignity")
        }
        analysis = build_anchor_analysis(pl, lagna)

        # Inspect the palm zones the chart anchors point to.
        zone_metrics: dict[str, Any] = {}
        try:
            import cv2
            from astro_palmistry_zone_cv import mark_chart_zones_on_palm, aggregate_zone_metrics
            cv_hands: list[list[dict]] = []
            for p in (image_paths or []):
                pth = Path(p)
                if not pth.is_file():
                    continue
                bgr = cv2.imread(str(pth))
                if bgr is None:
                    continue
                res = mark_chart_zones_on_palm(
                    bgr, analysis.get("zone_plan", []), None,
                    draw_house_zones=False, draw_longevity_lines=False,
                    show_zodiac_grid=False, draw_sacred_marks=False,
                )
                mz = res.get("marked_zones") or []
                if mz:
                    cv_hands.append(mz)
            if cv_hands:
                zone_metrics = aggregate_zone_metrics(cv_hands)
        except Exception:
            zone_metrics = {}

        analysis = apply_cv_evidence(analysis, zone_metrics)
        conf_html = human_confluence_html(analysis)
    except Exception:
        conf_html = ""

    try:
        lctx = build_longevity_context(pc)
    except Exception:
        lctx = None

    def _safe(fn, *a, **k) -> str:
        try:
            return fn(*a, **k)
        except Exception:
            return ""

    pillars = _safe(seven_pillars_html, pc, {}, lctx)
    transitions = _safe(transition_calendar_html, pc)
    traffic = _safe(traffic_light_html, pc, lctx)
    health = _safe(health_section_html, pc, lctx)
    remedies = _safe(remedies_html, pc, lctx)

    return f"""
<article class="report-card vchart-lane" style="border-left:4px solid var(--accent)">
  <h2>Your birth chart — derived planet positions</h2>
  <p class="lead">A full Vedic chart computed from your birth date, time and place anchors the palm
  reading to your actual planetary positions. The sections below read your life areas, life timeline
  and health windows from that chart.</p>
  {snapshot}
  {pillars}
  {conf_html}
  {transitions}
  {traffic}
  {health}
  {remedies}
  <p class="fine">Chart engine: PyJHora + Swiss Ephemeris (Lahiri ayanamsa). Educational guidance only,
  not medical or financial advice.</p>
</article>"""


_CONF_THEMES: list[tuple[str, tuple[str, ...]]] = [
    ("Character & nature", ("character", "temperament", "nature", "personality")),
    ("Mind & thinking", ("mind", "intellect", "mental", "thought")),
    ("Love & relationships", ("love", "marriage", "emotion", "relationship", "heart")),
    ("Work & direction", ("career", "destiny", "work", "profession", "fate")),
    ("Money & fortune", ("wealth", "fortune", "money", "finance", "prosper")),
    ("Health & vitality", ("health", "vitality", "longevity", "body")),
]


def _palm_aspect(aspects: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, Any] | None:
    for a in aspects or []:
        title = (a.get("title") or "").lower()
        if any(k in title for k in keys):
            return a
    return None


def _star_note_for(theme: str, derived, pc: dict[str, Any] | None,
                   longevity: dict[str, Any] | None) -> str:
    """One short sentence from the star side for a given life theme (or '')."""
    asc = getattr(derived, "ascendant_sign", None)
    sun = getattr(derived, "solar_sign", None)
    if pc:
        meta = pc.get("meta", {})
        asc = asc or meta.get("lagna_sign")
    if theme.startswith("Character") and asc:
        return f"Your {asc} rising agrees — you meet the world as {_ASC_TRAITS.get(asc, 'a distinctive blend of traits').rstrip('. ')}."
    if theme.startswith("Mind") and derived is not None:
        waxing = "Shukla" in (getattr(derived, "paksha", "") or "")
        mood = ("an outgoing, forward-looking turn of mind" if waxing
                else "a deep, reflective, results-minded turn of mind")
        wk = _WEEKDAY_TEMPER.get(getattr(derived, "weekday", ""), "").rstrip(". ")
        tail = f" with {wk}" if wk else ""
        return f"Your Moon points the same way — {mood}{tail}."
    if theme.startswith("Love") and sun:
        return f"Your Sun in {sun} colours how you love and bond."
    if theme.startswith("Work") and derived is not None:
        el = _tri_element(getattr(derived, "saturn_triplicity", None))
        return f"Saturn in your {el} group shapes your work lessons: {_SAT_BY_ELEMENT.get(el, 'steady effort over shortcuts').rstrip('. ')}."
    if theme.startswith("Money") and derived is not None:
        el = _tri_element(getattr(derived, "jupiter_triplicity", None))
        return f"Jupiter in your {el} group shapes how fortune reaches you — {_JUP_BY_ELEMENT.get(el, 'in its own way').rstrip('. ')}."
    if theme.startswith("Health"):
        bits = []
        if sun:
            bits.append(f"your Sun in {sun} sets your core vitality")
        if longevity and longevity.get("estimate_years"):
            r = longevity.get("range_years") or []
            rng = f" (around {r[0]}–{r[1]} years on the palm's 80-year measure)" if len(r) == 2 else ""
            bits.append(f"the life-line reads long{rng}")
        if bits:
            return "On the star side, " + " and ".join(bits) + "."
    return ""


_CONF_PILL = {"strong": ("hi", "Strong"), "moderate": ("mid", "Moderate"),
              "tentative": ("lo", "Tentative"), "weak": ("lo", "Faint")}


def _render_palm_star_confluence(analysis: dict[str, Any], derived,
                                 pc: dict[str, Any] | None,
                                 longevity: dict[str, Any] | None) -> str:
    """
    Lead section: for each life theme, show what the palm says and what the
    stars say side by side, and whether the two agree. This is the confluence
    of the descriptive-palmistry and astro-palmistry lanes in one short read.
    """
    conf = analysis.get("confluence") or {}
    aspects = conf.get("life_aspects") or []
    if not aspects:
        return ""

    rows = ""
    pairs = 0
    for theme, keys in _CONF_THEMES:
        a = _palm_aspect(aspects, keys)
        if not a:
            continue
        palm_txt = (a.get("summary") or "").strip()
        if not palm_txt:
            continue
        strength = (a.get("strength") or "moderate").lower()
        pill_cls, pill_lbl = _CONF_PILL.get(strength, ("mid", strength.title() or "Moderate"))
        both = a.get("reinforced_count") or 0
        both_badge = f' <span class="badge">{both} on both hands</span>' if both else ""
        star_txt = _star_note_for(theme, derived, pc, longevity)
        if star_txt:
            pairs += 1
            verdict = ('<span class="pill hi">Palm &amp; stars agree</span>'
                       if strength in ("strong", "moderate")
                       else '<span class="pill mid">Palm &amp; stars lean the same way</span>')
            star_html = f'<p class="body"><strong>Your stars:</strong> {_e(star_txt)}</p>'
        else:
            verdict = '<span class="pill lo">Read from your palm</span>'
            star_html = ""
        rows += f"""
  <div class="card {('green' if star_txt and strength in ('strong','moderate') else 'amber' if star_txt else 'blue')}">
    <h3>{_e(theme)} <span class="pill {pill_cls}">{_e(pill_lbl)} on the palm</span>{both_badge}</h3>
    <p class="body"><strong>Your palm:</strong> {_e(palm_txt)}</p>
    {star_html}
    <p class="body">{verdict}</p>
  </div>"""

    if not rows:
        return ""

    intro = (
        "I've read your hands two ways here — once from the <strong>lines and mounts themselves</strong>, "
        "and once from the <strong>planets your palm points to</strong>. "
        "When both say the same thing, that's when you should really sit up and listen — it's where your hand "
        "is telling you something true about your life. "
        + (f"On {pairs} of the areas below, the lines and the stars say the same thing. " if pairs else "")
        + "After this, I'll take you through the full hand reading and then the star reading, one at a time."
    )
    return f"""
<article class="report-card vchart-lane" style="border-left:4px solid var(--vc-accent)">
  <h2>Your life, where palm and stars meet</h2>
  <p class="lead">{intro}</p>
  {rows}
</article>"""


def generate_combined_report(
    image_paths: list[str | Path],
    out_html_path: str | Path,
    *,
    client_name: str = "Client",
    active_hand: str = "right",
    embed_overlays: bool = True,
    bright_half: bool = False,
    yav_crossed: bool = False,
    birth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run both lanes and write one combined HTML report. Returns both results."""
    out_html_path = Path(out_html_path)
    overlay_dir = out_html_path.parent
    overlay_dir.mkdir(parents=True, exist_ok=True)

    # --- Lane 1: descriptive palmistry (+ confluence life aspects) ---
    analysis = analyze_image_paths(image_paths, active_hand=active_hand, overlay_dir=overlay_dir)

    # --- Lane 2: astro-palmistry (phalange counts -> birth sketch) ---
    img_paths = [Path(p) for p in image_paths if Path(p).is_file()]
    cv_analysis = analyze_from_paths(img_paths, overlay_dir)
    derived = None
    agg = cv_analysis.get("aggregated")
    if agg:
        try:
            counts = counts_from_manual_table(**agg, bright_half=bright_half, yav_crossed=yav_crossed)
            derived = derive_from_lines(counts)
        except Exception:
            derived = None

    # --- Longevity: Saraswati 80-year formula across life/head/heart/fate ---
    longevity = None
    cross_notes: list[str] = []
    lengths: dict[str, float] = {}
    longevity_overlay_src = ""
    dom = analysis.get(active_hand) or analysis.get("right") or analysis.get("left") or {}
    dom_feats = dom.get("features") or {}
    try:
        # Book confluence: life-line 80-yr base + head/heart/fate cross-check
        # (lives in astro_palmistry_longevity.longevity_confluence).
        longevity = longevity_confluence(dom_feats)
        cross_notes = longevity.get("line_notes") or []
        lengths = longevity.get("line_lengths") or {}
    except Exception:
        longevity = None

    # Longevity overlay (four lines + lengths + 5-year age ticks) on dominant photo.
    try:
        dom_src = dom.get("path") or dom_feats.get("source_image")
        if dom_src and Path(dom_src).is_file():
            ov_path = overlay_dir / f"Longevity_{active_hand}_overlay.jpg"
            if _build_longevity_overlay(Path(dom_src), dom_feats, longevity, ov_path):
                longevity_overlay_src = _img_src(str(ov_path), embed_overlays)
    except Exception:
        longevity_overlay_src = ""

    # --- Morphology (computation runs in background; only predictions shown) ---
    morph: dict[str, Any] = {}
    try:
        left_path = next((Path(p) for p in image_paths if _guess_hand(Path(p)) == "left"), None)
        right_path = next((Path(p) for p in image_paths if _guess_hand(Path(p)) == "right"), None)
        if left_path and right_path:
            morph = analyze_morphology_both_hands(left_path, right_path, None)
    except Exception:
        morph = {}

    # Prediction-only sections: hand-shape reading + a short astro birth-sketch.
    signs_section = _render_palm_signs(
        analysis, morph, longevity, active_hand,
        cross_notes=cross_notes, lengths=lengths,
        longevity_overlay_src=longevity_overlay_src,
    )
    # --- Real birth chart (if birth details supplied) ---
    pc = None
    if birth and compute_chart is not None:
        try:
            pc = compute_chart(**birth)
        except Exception:
            pc = None

    if pc:
        # A computed ephemeris chart is authoritative — lead with it and skip the
        # rougher palm-derived triplicity fallback (it disagrees on poor photos).
        astro_section = _render_birth_chart(pc, birth, image_paths)
    else:
        astro_section = _render_astro_identity(
            derived, cv_analysis.get("quality", "?"), cv_analysis.get("needs_retake") or []
        )

    # The hand-shape reading belongs with the palmistry detail; the star reading
    # is the separate astro-palmistry section under its own divider.
    section2_hdr = (
        '<h2 class="section-divider" style="margin:2rem 0 .4rem;color:var(--muted);'
        'border-top:1px solid var(--border);padding-top:1.2rem">Section 2 — Your stars, read from your palm</h2>'
    )
    astro_html = signs_section + section2_hdr + astro_section

    # --- Combined confluence (palm + stars) that leads the report ---
    confluence_lead = _render_palm_star_confluence(analysis, derived, pc, longevity)

    # --- Compose one document (lead confluence + palm detail + astro section) ---
    html_doc = render_lane_html(
        analysis,
        client_name=client_name,
        embed_overlays=embed_overlays,
        extra_sections_html=astro_html,
        lead_sections_html=confluence_lead,
    )
    # Inject the small astro-only CSS just before </style>.
    html_doc = html_doc.replace("</style>", _astro_extra_css() + "</style>", 1)
    # Strip author/source/proof attributions, then add the section nav pane.
    try:
        from client_report_html import finalize_report_html
        html_doc = finalize_report_html(html_doc, client_name)
    except Exception:
        pass
    out_html_path.write_text(html_doc, encoding="utf-8")

    return {
        "out_html": str(out_html_path),
        "descriptive": analysis,
        "astro_cv": cv_analysis,
        "astro_derived": derived,
        "longevity": longevity,
        "chart": pc,
    }


if __name__ == "__main__":
    BASE = Path(__file__).resolve().parent
    OCR = BASE / "palmistry_ocr"
    OUT = BASE / "ritz_report" / "ritz_combined_report.html"
    images = [str(OCR / "ritz_rightpalm.jpg"), str(OCR / "ritz_leftpalm.jpg")]
    result = generate_combined_report(
        images, OUT, client_name="Ritz", active_hand="right",
        birth=RITZ_BIRTH or None,
    )
    print("Combined report:", result["out_html"])
    pc = result.get("chart")
    if pc:
        m = pc.get("meta", {})
        print(f"Birth chart: lagna {m.get('lagna_sign')} (lord {m.get('lagna_lord')}), "
              f"MD {pc.get('vimshottari', {}).get('current_md', {}).get('md_lord')}")
    d = result["astro_derived"]
    print("Astro CV quality:", result["astro_cv"].get("quality"))
    print("Aggregated counts:", result["astro_cv"].get("aggregated"))
    if d is not None:
        print(f"Derived: tithi={d.tithi} {d.paksha}, solar={d.solar_sign}, "
              f"weekday={d.weekday}, ascendant={d.ascendant_sign}")
    else:
        print("Derived birth sketch: unavailable (insufficient phalange counts)")
    lon = result.get("longevity")
    if lon and lon.get("estimate_years"):
        print(f"Longevity (Saraswati 80-yr): ~{lon['estimate_years']} yrs "
              f"(range {lon['range_years'][0]}-{lon['range_years'][1]})")
    else:
        print("Longevity: life line not readable for Saraswati division")
