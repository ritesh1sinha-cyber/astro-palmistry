#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tirupur S. Gopalakrishnan (GK) - Planetary Transit and Dasa Period (2023).

OCR: book_ocr/planetary_transit_dasa/ - rules11.md
Core: transit + Vimshottari MD/AD must agree; transit over period-lord signs;
karmic Saturn-Rahu pairs; planetary-combo eventful ages.
"""
from __future__ import annotations

import html
from datetime import date, timedelta
from typing import Any

from astro_precompute import SIGNS

GK_RULES_SOURCE = "rules11.md (GK 2023, Planetary Transit and Dasa Period)"

VIM_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}

SLOW_GRAHAS = ("Jupiter", "Saturn", "Mars", "Venus", "Rahu", "Ketu")
TRANSIT_ACTIVATORS = ("Jupiter", "Saturn", "Mars", "Venus", "Sun", "Moon", "Mercury", "Rahu")

SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}


def _house_of(sign: str, lagna: str) -> int:
    return (SIGNS.index(sign) - SIGNS.index(lagna)) % 12 + 1


def is_karmic_dasha(md: str, ad: str) -> bool:
    """GK 'Karmic Dasa-Bukthi': Saturn-Rahu in either order dampens auspicious transits."""
    pair = frozenset({md, ad})
    return pair == frozenset({"Saturn", "Rahu"})


def gk_combo_eventful_ages(years_a: int, years_b: int) -> list[int]:
    """
    GK Ch.6: for conjunct planets A+B, eventful ages from birth =
    A, B, A+B, (A+B)+A, (A+B)+B (e.g. Jupiter 16 + Saturn 19 -> 16,19,35,51,70).
    """
    ya, yb = years_a, years_b
    cum = ya + yb
    return sorted({ya, yb, cum, cum + ya, cum + yb})


def find_natal_conjunction_combos(pc: dict) -> list[dict[str, Any]]:
    """Whole-sign conjunction groups in D1 (GK planetary combination chapter)."""
    lagna = pc.get("meta", {}).get("lagna_sign") or pc.get("lagna", {}).get("sign", "")
    by_sign: dict[str, list[str]] = {}
    for pname, data in pc.get("planets", {}).items():
        if pname in ("lagna",) or pname not in VIM_YEARS:
            continue
        sign = data.get("sign")
        if sign:
            by_sign.setdefault(sign, []).append(pname)

    combos: list[dict[str, Any]] = []
    for sign, planets in by_sign.items():
        if len(planets) < 2:
            continue
        planets = sorted(planets)
        for i in range(len(planets)):
            for j in range(i + 1, len(planets)):
                a, b = planets[i], planets[j]
                ages = gk_combo_eventful_ages(VIM_YEARS[a], VIM_YEARS[b])
                house = _house_of(sign, lagna) if lagna in SIGNS else 0
                combos.append({
                    "planets": (a, b),
                    "sign": sign,
                    "house": house,
                    "eventful_ages": ages,
                    "note": (
                        f"GK combo {a}+{b} in {sign}"
                        + (f" ({house}th house)" if house else "")
                        + f" - eventful ages {ages} from birth."
                    ),
                })
    return combos


def eventful_ages_for_native(pc: dict, birth_year: int, *, horizon: int = 85) -> list[dict[str, Any]]:
    """Map GK combo ages to calendar years for this native."""
    age = int(pc.get("meta", {}).get("age", 0))
    out: list[dict[str, Any]] = []
    for combo in find_natal_conjunction_combos(pc):
        for a in combo["eventful_ages"]:
            if a > horizon:
                continue
            cal_year = birth_year + a
            out.append({
                "age": a,
                "year": cal_year,
                "planets": combo["planets"],
                "sign": combo["sign"],
                "house": combo["house"],
                "past": a < age,
                "upcoming": a >= age,
                "note": combo["note"],
            })
    out.sort(key=lambda x: x["age"])
    return out


def _sidereal_transits(target: date) -> dict[str, str]:
    try:
        import swisseph as swe
    except ImportError:
        return {}
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(target.year, target.month, target.day, 12.0)
    bodies = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
        "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE,
    }
    out: dict[str, str] = {}
    for name, pid in bodies.items():
        lon = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)[0][0]
        out[name] = SIGNS[int(lon // 30) % 12]
    out["Ketu"] = SIGNS[(SIGNS.index(out["Rahu"]) + 6) % 12]
    return out


def _transit_over_natal_sign(transits: dict[str, str], natal_sign: str) -> list[str]:
    if not natal_sign:
        return []
    hits = []
    for pl in TRANSIT_ACTIVATORS:
        if transits.get(pl) == natal_sign:
            hits.append(pl)
    return hits


def _jup_sat_over_sign(transits: dict[str, str], natal_sign: str) -> list[str]:
    if not natal_sign:
        return []
    return [pl for pl in ("Jupiter", "Saturn") if transits.get(pl) == natal_sign]


def _sample_window_dates(w_start: date, w_end: date) -> list[date]:
    """Sample start, end, midpoint, and ~quarterly points across a dasha window."""
    days = (w_end - w_start).days
    if days <= 0:
        return [w_start]
    samples: set[date] = {w_start, w_end, w_start + timedelta(days=days // 2)}
    step = max(90, days // 4) if days > 120 else max(30, days // 2)
    cur = w_start
    while cur <= w_end:
        samples.add(cur)
        cur += timedelta(days=step)
    return sorted(samples)


def score_gk_transit_dasha_window(
    *,
    md: str,
    ad: str,
    pc: dict,
    w_start: date,
    w_end: date,
) -> dict[str, Any]:
    """
    GK Ch.23 window scan: Jupiter/Saturn (primary) crossing natal MD/AD lord signs
    at any point during the antardasa window; karmic Saturn-Rahu dampens vote.
    """
    samples = _sample_window_dates(w_start, w_end)
    if not _sidereal_transits(w_start):
        return {"available": False, "yes": False, "note": "Install pyswisseph for GK window scan."}

    planets = pc.get("planets", {})
    md_sign = planets.get(md, {}).get("sign", "")
    ad_sign = planets.get(ad, {}).get("sign", "")
    karmic = is_karmic_dasha(md, ad)

    best_score = -99
    best_note = ""
    jup_sat_md_dates: list[str] = []
    jup_sat_ad_dates: list[str] = []
    any_md_hits: list[str] = []
    any_ad_hits: list[str] = []

    for d in samples:
        synergy = score_transit_dasha_synergy(md=md, ad=ad, pc=pc, target=d)
        if synergy.get("score", 0) > best_score:
            best_score = synergy["score"]
            best_note = synergy.get("note", "")
        transits = synergy.get("transits", {})
        js_md = _jup_sat_over_sign(transits, md_sign)
        js_ad = _jup_sat_over_sign(transits, ad_sign) if ad != md else []
        if js_md:
            jup_sat_md_dates.append(d.isoformat())
        if js_ad:
            jup_sat_ad_dates.append(d.isoformat())
        any_md_hits.extend(synergy.get("md_transit_hits", []))
        any_ad_hits.extend(synergy.get("ad_transit_hits", []))

    notes: list[str] = []
    if jup_sat_md_dates:
        notes.append(
            f"Jupiter/Saturn over natal {md} sign {md_sign} during window "
            f"({jup_sat_md_dates[0]} to {jup_sat_md_dates[-1]})"
        )
    if jup_sat_ad_dates and ad != md:
        notes.append(
            f"Jupiter/Saturn over natal {ad} sign {ad_sign} during window "
            f"({jup_sat_ad_dates[0]} to {jup_sat_ad_dates[-1]})"
        )
    if not notes and best_note:
        notes.append(best_note)
    if not notes:
        notes.append(
            f"No Jupiter/Saturn transit over natal {md}/{ad} signs in window "
            f"{w_start.isoformat()} to {w_end.isoformat()} (GK trigger weak)."
        )
    if karmic:
        notes.append("Karmic Saturn-Rahu MD-AD - GK dampens transit delivery.")

    trigger = bool(jup_sat_md_dates or jup_sat_ad_dates or best_score >= 2)
    yes = trigger and not karmic

    return {
        "available": True,
        "yes": yes,
        "trigger": trigger,
        "karmic_dasha": karmic,
        "score": best_score,
        "md_natal_sign": md_sign,
        "ad_natal_sign": ad_sign,
        "jup_sat_md_samples": jup_sat_md_dates[:4],
        "jup_sat_ad_samples": jup_sat_ad_dates[:4],
        "note": "; ".join(notes[:3])[:400],
        "source": GK_RULES_SOURCE,
    }


def gk_window_snippet(gk: dict[str, Any], *, max_len: int = 140) -> str:
    """Plain one-liner for Vim timeline rows."""
    if not gk.get("available"):
        return ""
    tag = "GK transit trigger" if gk.get("yes") else "GK transit"
    return f"{tag}: {gk.get('note', '')[:max_len]}"

def score_transit_dasha_synergy(
    *,
    md: str,
    ad: str,
    pc: dict,
    target: date | None = None,
) -> dict[str, Any]:
    """
    GK Ch.23 + early chapters: transit triggers for running MD/AD lords;
    karmic dampener; Jupiter/Saturn over natal period-lord signs.
    """
    target = target or date.today()
    transits = _sidereal_transits(target)
    if not transits:
        return {"available": False, "note": "Install pyswisseph for GK transit layer."}

    lagna = pc.get("meta", {}).get("lagna_sign") or ""
    planets = pc.get("planets", {})
    md_data = planets.get(md, {})
    ad_data = planets.get(ad, {})
    md_sign = md_data.get("sign", "")
    ad_sign = ad_data.get("sign", "")
    md_house = md_data.get("house") or (_house_of(md_sign, lagna) if md_sign and lagna else 0)
    ad_house = ad_data.get("house") or (_house_of(ad_sign, lagna) if ad_sign and lagna else 0)

    notes: list[str] = []
    score = 0

    md_hits = _transit_over_natal_sign(transits, md_sign)
    ad_hits = _transit_over_natal_sign(transits, ad_sign)
    if md_hits:
        score += 2
        notes.append(
            f"Transit {'/'.join(md_hits)} in {md_sign} (natal {md} mahadasha lord) - GK period trigger."
        )
    if ad_hits and ad != md:
        score += 2
        notes.append(
            f"Transit {'/'.join(ad_hits)} in {ad_sign} (natal {ad} antardasha lord) - GK sub-period trigger."
        )

    for tpl, label in ((md, "MD"), (ad, "AD")):
        if not tpl or tpl not in transits:
            continue
        t_sign = transits[tpl]
        if lagna and t_sign in SIGNS:
            th = _house_of(t_sign, lagna)
            natal_h = planets.get(tpl, {}).get("house") or (
                _house_of(planets.get(tpl, {}).get("sign", ""), lagna)
                if planets.get(tpl, {}).get("sign") else 0
            )
            if natal_h and th == natal_h:
                score += 1
                notes.append(f"Transit {tpl} ({label} lord) returns to natal {th}th house - GK activation.")

    karmic = is_karmic_dasha(md, ad)
    if karmic:
        score -= 2
        notes.append(
            "GK karmic Saturn-Rahu MD-AD pair - auspicious transits may not deliver full personal benefit."
        )

    jup_sign = transits.get("Jupiter", "")
    sat_sign = transits.get("Saturn", "")
    if jup_sign and sat_sign and jup_sign == sat_sign:
        notes.append("Dual slow transit: Jupiter and Saturn share a sign - mixed results; running dasha lord prevails.")

    supportive = score >= 2 and not karmic
    dampened = karmic and score >= 1

    if not notes:
        notes.append(
            f"No major graha currently transits natal {md} ({md_sign}) or {ad} ({ad_sign}) signs - "
            "GK: dasha sets the promise; wait for Jupiter/Saturn/Mars over those signs to trigger."
        )

    return {
        "available": True,
        "md": md,
        "ad": ad,
        "target": target.isoformat(),
        "transits": transits,
        "md_natal_sign": md_sign,
        "ad_natal_sign": ad_sign,
        "md_natal_house": md_house,
        "ad_natal_house": ad_house,
        "md_transit_hits": md_hits,
        "ad_transit_hits": ad_hits,
        "karmic_dasha": karmic,
        "score": score,
        "supportive": supportive,
        "dampened": dampened,
        "note": "; ".join(notes[:4]),
        "source": GK_RULES_SOURCE,
    }


def upcoming_eventful_years(pc: dict, birth_year: int, n: int = 4) -> list[dict[str, Any]]:
    age = int(pc.get("meta", {}).get("age", 0))
    rows = [r for r in eventful_ages_for_native(pc, birth_year) if r["upcoming"]]
    seen: set[int] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        if row["age"] in seen:
            continue
        seen.add(row["age"])
        out.append(row)
        if len(out) >= n:
            break
    return out


def render_gk_transit_dasha_block(synergy: dict[str, Any], combos_upcoming: list[dict[str, Any]] | None = None) -> str:
    if not synergy.get("available"):
        return f"<p class='fine'>{html.escape(synergy.get('note', 'GK transit layer unavailable.'))}</p>"

    md, ad = synergy["md"], synergy["ad"]
    body = (
        f"<p class='pred'><strong>GK transit + dasha (rules11):</strong> "
        f"Active <strong>{html.escape(md)}-{html.escape(ad)}</strong> on "
        f"<strong>{html.escape(synergy.get('target', ''))}</strong>. "
        f"{html.escape(synergy.get('note', ''))}</p>"
    )
    if synergy.get("karmic_dasha"):
        body += (
            "<p class='fine'>Karmic dasha note: even strong Jupiter transits may pass through you "
            "to others or feel like paying interest on old karma (GK Ch.5).</p>"
        )
    if combos_upcoming:
        bits = [
            f"age {r['age']} ({r['year']}): {'+'.join(r['planets'])} in {r['sign']}"
            for r in combos_upcoming[:3]
        ]
        body += (
            "<p class='fine'><strong>GK planetary-combo eventful ages ahead:</strong> "
            + html.escape("; ".join(bits))
            + " - fine-tune with transit of combo lords over natal signs.</p>"
        )
    return f"<div class='callout-gk'>{body}</div>"


def render_gk_gochar_bridge(synergy: dict[str, Any]) -> str:
    """One paragraph for Bhardwaj gochar section."""
    if not synergy.get("available"):
        return ""
    if synergy.get("supportive"):
        tone = "Transit and dasha agree today - GK allows stronger manifestation of period themes."
    elif synergy.get("dampened"):
        tone = "Transits look active but karmic Saturn-Rahu dasha may mute personal enjoyment (GK)."
    elif synergy.get("karmic_dasha"):
        tone = "Karmic dasha pair running - keep gochar expectations modest even in good houses."
    else:
        tone = "Transit layer is neutral - dasha sets the chapter; gochar colours the week."
    return (
        f"<p class='fine'><strong>GK pairing:</strong> {html.escape(tone)} "
        f"{html.escape(synergy.get('note', '')[:200])}</p>"
    )
