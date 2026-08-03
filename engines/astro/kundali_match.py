#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kundali matching: Ashtakoota (PyJHora) + Bhardwaj doshas + Goel D9 synastry."""
from __future__ import annotations

from typing import Any

from astro_precompute import normalize_nakshatra, precompute_from_chart
from goel_navamsha_coverage import SIGN_LORD
from goel_varga import SIGNS, house_from_sign, navamsha_sign
from kundali_remedies import assess_remissions, remedies_for_match
from natal_from_pyjhora import BirthInput, compute_chart_btr, _ensure_pyjhora

MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
BENEFICS = {"Moon", "Mercury", "Jupiter", "Venus"}
TRIK = {6, 8, 12}

# Sign triplicity (element) for D9 lagna harmony.
SIGN_ELEMENT = {
    "Aries": "fire", "Leo": "fire", "Sagittarius": "fire",
    "Taurus": "earth", "Virgo": "earth", "Capricorn": "earth",
    "Gemini": "air", "Libra": "air", "Aquarius": "air",
    "Cancer": "water", "Scorpio": "water", "Pisces": "water",
}
# Elements that get along (classical: fire-air active, earth-water receptive).
_FRIENDLY_ELEMENTS = {("fire", "air"), ("air", "fire"), ("earth", "water"), ("water", "earth")}

KOOT_LABELS = [
    ("varna", "Varna", 1),
    ("vashya", "Vashya", 2),
    ("tara", "Tara / Dina", 3),
    ("yoni", "Yoni", 4),
    ("maitri", "Graha Maitri", 5),
    ("gana", "Gana", 6),
    ("bhakoot", "Bhakoot", 7),
    ("nadi", "Nadi", 8),
]

PJ_NAK_ALIASES = {
    "Mrigashira": "Mrigshira",
    "Jyeshtha": "Jyestha",
    "Shatabhisha": "Satabhisha",
    "Shravana": "Shravana",
    "Sravana": "Shravana",
    "Dhanishtha": "Dhanishta",
}


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in (name or "Match").strip())[:40].strip("_") or "Match"


def build_person_chart(
    *,
    name: str,
    dob: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    timezone: float,
    place_name: str,
    gender: int = 0,
) -> dict:
    base = birth_time if birth_time.count(":") >= 2 else birth_time + ":00"
    inp = BirthInput(
        client_name=name or "Person",
        dob=dob,
        birth_time=base,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        place_name=place_name or "BirthPlace",
        gender=gender,
    )
    parsed = compute_chart_btr(inp)
    pc = precompute_from_chart(parsed, name or "Person", dob, source="pyjhora_match")
    pc.setdefault("meta", {})["dob"] = dob
    pc["meta"]["latitude"] = latitude
    pc["meta"]["longitude"] = longitude
    pc["meta"]["timezone"] = timezone
    pc["meta"]["place"] = place_name
    pc["chart_raw"] = parsed
    return pc


def _nakshatra_pj_index(nak: str) -> int:
    from jhora.horoscope.match.compatibility import nakshatra_list

    canon = normalize_nakshatra(nak or "")
    pj_name = PJ_NAK_ALIASES.get(canon, canon)
    if pj_name in nakshatra_list:
        return nakshatra_list.index(pj_name) + 1
    key = pj_name.lower().replace(" ", "")
    for i, nj in enumerate(nakshatra_list):
        if nj.lower().replace(" ", "") == key:
            return i + 1
    raise ValueError(f"Unknown nakshatra for matching: {nak!r}")


def _moon_nak_pada(pc: dict) -> tuple[str, int]:
    moon = (pc.get("planets") or {}).get("Moon") or {}
    nak = moon.get("nakshatra") or moon.get("nakshatra_name") or ""
    pada = int(moon.get("pada") or moon.get("nakshatra_pada") or 1)
    if not nak:
        raise ValueError("Moon nakshatra missing from chart.")
    return normalize_nakshatra(nak), max(1, min(4, pada))


def _moon_display(moon: dict) -> str:
    """Human-readable Moon position for audit (sign + degree drives nakshatra)."""
    sign = moon.get("sign") or "?"
    deg = moon.get("degree_in_sign")
    if deg is None:
        return sign
    d = int(deg)
    m = int(round((deg - d) * 60))
    s = int(round(((deg - d) * 60 - m) * 60))
    return f"{sign} {d}d {m:02d}m {s:02d}s"


KOOT_DEFS_NORTH = [
    ("varna", "Varna", 1),
    ("vashya", "Vashya", 2),
    ("gana", "Gana", 6),
    ("tara", "Tara / Dina", 3),
    ("yoni", "Yoni", 4),
    ("maitri", "Graha Maitri", 5),
    ("bhakoot", "Bhakoot", 7),
    ("nadi", "Nadi", 8),
]


def _koot_score(fn) -> float:
    got = fn()
    if isinstance(got, tuple):
        return float(got[0])
    if isinstance(got, bool):
        return 1.0 if got else 0.0
    return float(got)


def _guna_band(total: float) -> tuple[str, str]:
    if total < 18:
        return "avoid", "Not recommended (below 18 guns - Bhardwaj rules37)"
    if total <= 21:
        return "moderate", "Moderate match (18-21 guns - proceed with caution and remedies)"
    if total < 28:
        return "good", f"Good match ({total:g} guns - above 21, below excellent 28)"
    return "excellent", "Excellent match (28+ guns)"


def _assess_manglik(pc: dict) -> dict[str, Any]:
    from jhora.horoscope.chart import charts, dosha
    from jhora.panchanga import drik
    from jhora import utils

    raw = pc.get("chart_raw") or {}
    meta = pc.get("meta") or {}
    dob = meta.get("dob") or raw.get("birth_time", "")[:10]
    if not dob or len(str(dob)) < 10:
        return {"active": False, "note": "Birth data incomplete for Manglik check."}

    dob_parts = tuple(int(x) for x in str(dob)[:10].split("-"))
    tob = tuple(int(x) for x in str(raw.get("birth_time", "12:00:00")).split(":")[:3])
    while len(tob) < 3:
        tob = (*tob, 0)
    birth = raw.get("birth_place") or meta.get("place") or "BirthPlace"
    lat = float(meta.get("latitude") or 28.6)
    lon = float(meta.get("longitude") or 77.2)
    tz = float(meta.get("timezone") or 5.5)
    place = drik.Place(birth, lat, lon, tz)
    jd = utils.julian_day_number(dob_parts, tob[:3])
    pp = charts.rasi_chart(jd, place)

    from jhora import const

    checks = {}
    for ref, label in [
        ("L", "from Lagna"),
        (const.MOON_ID, "from Moon"),
        (const.VENUS_ID, "from Venus"),
    ]:
        m = dosha.manglik(pp, manglik_reference_planet=ref, include_lagna_house=False, apply_exceptions=True)
        checks[label] = {
            "manglik": bool(m[0]),
            "exception": bool(m[1]),
            "exception_codes": m[2] if len(m) > 2 else [],
        }
    primary = checks.get("from Lagna", {})
    return {
        "active": primary.get("manglik", False) and not primary.get("exception", False),
        "cancelled_by_exception": primary.get("exception", False),
        "checks": checks,
        "note": (
            "Manglik active from Lagna reference"
            if primary.get("manglik") and not primary.get("exception")
            else "No Manglik from Lagna (or cancelled by classical exception)"
        ),
    }


def _d9_bundle(pc: dict) -> dict[str, Any]:
    lagna = (pc.get("lagna") or {}).get("sign") or (pc.get("d1") or {}).get("lagna", "")
    lagna_deg = float((pc.get("lagna") or {}).get("degree_in_sign") or 0)
    if not lagna:
        return {}
    d9_lagna = navamsha_sign(lagna, lagna_deg)
    d9_map: dict[str, str] = {}
    for pl, data in (pc.get("planets") or {}).items():
        if pl in ("Rahu", "Ketu"):
            continue
        d1 = data.get("sign", "")
        deg = float(data.get("degree_in_sign") or 0)
        if d1:
            d9_map[pl] = navamsha_sign(d1, deg)
    lord7_sign = SIGNS[(SIGNS.index(d9_lagna) + 6) % 12]
    return {
        "d9_lagna": d9_lagna,
        "d9_lagna_lord": SIGN_LORD[d9_lagna],
        "d9_7th_sign": lord7_sign,
        "d9_7th_lord": SIGN_LORD[lord7_sign],
        "d9_map": d9_map,
    }


def _birth_dasha_lords(pc: dict) -> tuple[str, str]:
    raw = pc.get("chart_raw") or {}
    meta = pc.get("meta") or {}
    dob_s = meta.get("dob", "")
    try:
        _ensure_pyjhora()
        from jhora.horoscope.chart import house as pj_house
        from jhora.horoscope.dhasa.graha import vimsottari
        from jhora.panchanga import drik
        from jhora import utils

        dob_parts = tuple(int(x) for x in str(dob_s)[:10].split("-"))
        tob = tuple(int(x) for x in str(raw.get("birth_time", "12:00:00")).split(":")[:3])
        while len(tob) < 3:
            tob = (*tob, 0)
        place = drik.Place(
            meta.get("place") or "BirthPlace",
            float(meta.get("latitude") or 28.6),
            float(meta.get("longitude") or 77.2),
            float(meta.get("timezone") or 5.5),
        )
        jd = utils.julian_day_number(dob_parts, tob[:3])
        planet_list = pj_house.planet_list
        _, md_rows = vimsottari.get_vimsottari_dhasa_bhukthi(jd, place, dhasa_level_index=1)
        _, ad_rows = vimsottari.get_vimsottari_dhasa_bhukthi(jd, place, dhasa_level_index=2)
        md_lord = planet_list[md_rows[0][0]] if md_rows else ""
        md_id = md_rows[0][0] if md_rows else 0
        ad_lord = md_lord
        for row in ad_rows:
            if row[0] == md_id:
                ad_lord = planet_list[row[1]]
                break
        return md_lord, ad_lord
    except Exception:
        moon = (pc.get("planets") or {}).get("Moon") or {}
        lord = moon.get("dasha_lord_from_nak", "")
        return lord, lord


def _lord7_d1(pc: dict) -> str:
    lagna = (pc.get("lagna") or {}).get("sign") or ""
    if not lagna:
        return ""
    return SIGN_LORD[SIGNS[(SIGNS.index(lagna) + 6) % 12]]


def _planet_links_partner_seventh(planet: str, partner: dict) -> list[str]:
    if not planet:
        return []
    lagna = (partner.get("lagna") or {}).get("sign") or ""
    if not lagna:
        return []
    h7_sign = SIGNS[(SIGNS.index(lagna) + 6) % 12]
    lord7 = SIGN_LORD[h7_sign]
    hits: list[str] = []
    pdata = (partner.get("planets") or {}).get(planet) or {}
    ph = pdata.get("house")
    if ph == 7:
        hits.append("occupies partner 7th house")
    if planet == lord7:
        hits.append("is partner 7th lord")
    for other, od in (partner.get("planets") or {}).items():
        if od.get("house") == 7 and other == planet:
            hits.append("sits in partner 7th house")
    if planet in (partner.get("planets") or {}) and pdata.get("sign") == h7_sign:
        hits.append("in partner 7th sign")
    return hits


def _goel_synastry(groom_pc: dict, bride_pc: dict) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    g_md, g_ad = _birth_dasha_lords(groom_pc)
    b_md, b_ad = _birth_dasha_lords(bride_pc)

    for label, planet, partner, role in [
        ("Groom birth mahadasha vs bride 7th", g_md, bride_pc, "groom_md_bride_7"),
        ("Groom birth antardasha vs bride 7th", g_ad, bride_pc, "groom_ad_bride_7"),
        ("Bride birth mahadasha vs groom 7th", b_md, groom_pc, "bride_md_groom_7"),
        ("Bride birth antardasha vs groom 7th", b_ad, groom_pc, "bride_ad_groom_7"),
    ]:
        links = _planet_links_partner_seventh(planet, partner)
        partner_l7 = _lord7_d1(partner)
        ok = bool(links) or (planet and planet == partner_l7)
        checks.append({
            "id": role,
            "name": label,
            "ok": ok,
            "detail": "; ".join(links) if links else (
                f"{planet} does not strongly link to partner 7th axis (Goel Ch.3 ideal)"
            ),
        })

    g_d9 = _d9_bundle(groom_pc)
    b_d9 = _d9_bundle(bride_pc)
    if g_d9 and b_d9:
        gl = g_d9["d9_lagna_lord"]
        bl = b_d9["d9_lagna_lord"]
        g_in_b = (b_d9.get("d9_map") or {}).get(gl, "")
        b_in_g = (g_d9.get("d9_map") or {}).get(bl, "")
        if g_in_b:
            gh = house_from_sign(g_in_b, b_d9["d9_lagna"])
            ok = gh not in TRIK
            checks.append({
                "id": "groom_d9_lagna_lord_in_bride_d9",
                "name": "Groom D9 lagna lord in bride D9",
                "ok": ok,
                "detail": f"{gl} in {g_in_b} (house {gh} from bride D9 lagna)"
                + (" - not in trik" if ok else " - in trik 6/8/12 or stressed"),
            })
        if b_in_g:
            bh = house_from_sign(b_in_g, g_d9["d9_lagna"])
            ok = bh not in TRIK
            checks.append({
                "id": "bride_d9_lagna_lord_in_groom_d9",
                "name": "Bride D9 lagna lord in groom D9",
                "ok": ok,
                "detail": f"{bl} in {b_in_g} (house {bh} from groom D9 lagna)"
                + (" - not in trik" if ok else " - in trik 6/8/12 or stressed"),
            })

    passed = sum(1 for c in checks if c["ok"])
    total = len(checks) or 1
    return {
        "checks": checks,
        "passed": passed,
        "total": total,
        "score_pct": round(100 * passed / total),
        "verdict": "strong" if passed >= total - 1 else ("mixed" if passed >= total // 2 else "weak"),
    }


def _full_d9(pc: dict) -> dict[str, Any]:
    """All-graha D9 (Navamsha) chart for synastry.

    Prefers PyJHora's precomputed D9 (includes Lagna + Rahu/Ketu); falls back to
    the Parashari navamsha computed from D1 longitudes when D9 is not stored.
    """
    from astro_precompute import get_dignity

    pj = (pc.get("divisional") or {}).get("D9") or {}
    lagna = (pc.get("lagna") or {}).get("sign") or (pc.get("d1") or {}).get("lagna", "")
    lagna_deg = float((pc.get("lagna") or {}).get("degree_in_sign") or 0)
    d9_lagna = pj.get("Lagna") or (navamsha_sign(lagna, lagna_deg) if lagna else "")
    if not d9_lagna:
        return {}

    signs: dict[str, str] = {}
    for pl, data in (pc.get("planets") or {}).items():
        s = pj.get(pl)
        if not s:
            d1 = data.get("sign", "")
            deg = float(data.get("degree_in_sign") or 0)
            s = navamsha_sign(d1, deg) if d1 else ""
        if s:
            signs[pl] = s

    bodies: dict[str, dict[str, Any]] = {}
    for pl, s in signs.items():
        try:
            dig = get_dignity(pl, s)
        except Exception:  # noqa: BLE001
            dig = "unknown"
        bodies[pl] = {
            "sign": s,
            "house": house_from_sign(s, d9_lagna),
            "dignity": dig,
            "vargottama": (pc.get("planets") or {}).get(pl, {}).get("sign") == s,
        }
    lord7_sign = SIGNS[(SIGNS.index(d9_lagna) + 6) % 12]
    return {
        "lagna": d9_lagna,
        "lagna_lord": SIGN_LORD[d9_lagna],
        "lagna_element": SIGN_ELEMENT.get(d9_lagna, ""),
        "h7_sign": lord7_sign,
        "h7_lord": SIGN_LORD[lord7_sign],
        "bodies": bodies,
    }


def _afflicted(dignity: str) -> bool:
    return dignity in ("debilitated", "enemy_sign")


def _dignified(dignity: str) -> bool:
    return dignity in ("exalted", "moolatrikona", "own_sign", "friendly_sign")


def _seventh_health(d9: dict, role: str) -> dict[str, Any]:
    """Quality of the D9 7th house (marital harmony promise) for one person."""
    h7_lord = d9["h7_lord"]
    bodies = d9["bodies"]
    tenants = [p for p, b in bodies.items() if b["house"] == 7]
    mal = [p for p in tenants if p in MALEFICS]
    ben = [p for p in tenants if p in BENEFICS]
    lord_b = bodies.get(h7_lord, {})
    lord_dig = lord_b.get("dignity", "unknown")
    lord_house = lord_b.get("house")
    ok = True
    notes = []
    if mal and not ben:
        ok = False
        notes.append(f"malefic(s) {', '.join(mal)} on the 7th — friction/adjustment needed")
    elif ben:
        notes.append(f"benefic(s) {', '.join(ben)} on the 7th — warmth in partnership")
    if _afflicted(lord_dig):
        ok = False
        notes.append(f"7th lord {h7_lord} {lord_dig.replace('_', ' ')}")
    elif _dignified(lord_dig):
        notes.append(f"7th lord {h7_lord} {lord_dig.replace('_', ' ')}")
    if lord_house in TRIK:
        ok = False
        notes.append(f"7th lord in trik house {lord_house}")
    if not notes:
        notes.append("7th house and its lord neutral")
    return {
        "id": f"{role}_d9_seventh",
        "name": f"{role} D9 7th-house marital promise",
        "ok": ok,
        "detail": "; ".join(notes),
    }


def _karaka_health(d9: dict, karaka: str, role: str, topic: str) -> dict[str, Any]:
    """Dignity of the marriage karaka (Venus for husband, Jupiter for wife) in D9."""
    b = d9["bodies"].get(karaka, {})
    dig = b.get("dignity", "unknown")
    house = b.get("house")
    ok = not _afflicted(dig) and house not in TRIK
    bits = [f"{karaka} in {b.get('sign', '?')} ({dig.replace('_', ' ')}), house {house}"]
    if _afflicted(dig):
        bits.append("afflicted — work on " + topic)
    elif _dignified(dig):
        bits.append("well placed — supports " + topic)
    if house in TRIK:
        bits.append(f"in trik {house}")
    return {
        "id": f"{role}_d9_karaka_{karaka.lower()}",
        "name": f"{role} marriage karaka {karaka} in D9",
        "ok": ok,
        "detail": "; ".join(bits),
    }


def _overlay_synastry(mover_d9: dict, anchor_d9: dict, mover_role: str, anchor_role: str) -> dict[str, Any]:
    """Overlay one person's D9 planets onto the partner's D9 lagna (synastry).

    Benefics landing on the partner's 1/5/7/9/11 build harmony; malefics on the
    sensitive 7th (and 1st) signal friction.
    """
    anchor_lagna = anchor_d9["lagna"]
    harmony_houses = {1, 4, 5, 7, 9, 11}
    plus, minus = [], []
    for pl, b in mover_d9["bodies"].items():
        h = house_from_sign(b["sign"], anchor_lagna)
        if pl in BENEFICS and h in harmony_houses:
            plus.append(f"{pl}→H{h}")
        if pl in MALEFICS and h in (1, 7):
            minus.append(f"{pl}→H{h}")
    score = len(plus) - len(minus)
    ok = score >= 0 and len(minus) <= 1
    detail = []
    if plus:
        detail.append("supportive: " + ", ".join(plus))
    if minus:
        detail.append("tension: " + ", ".join(minus))
    if not detail:
        detail.append("neutral overlay")
    return {
        "id": f"{mover_role}_over_{anchor_role}_d9",
        "name": f"{mover_role} planets on {anchor_role} D9 (overlay)",
        "ok": ok,
        "detail": "; ".join(detail),
    }


def d9_compatibility(groom_pc: dict, bride_pc: dict) -> dict[str, Any]:
    """Dedicated Navamsha (D9) marriage-compatibility lane.

    The D9 is the primary chart for marriage. This reads both partners' D9
    independently (7th house, 7th lord, marriage karakas) and then overlays
    each chart onto the other (synastry) for relational harmony.
    """
    g = _full_d9(groom_pc)
    b = _full_d9(bride_pc)
    if not g or not b:
        return {"available": False, "reason": "D9 chart could not be built for one partner."}

    # 1) D9 lagna harmony (element + house axis between the two ascendants).
    g_in_b_house = house_from_sign(g["lagna"], b["lagna"])
    g_el, b_el = g["lagna_element"], b["lagna_element"]
    same = g["lagna"] == b["lagna"]
    axis_ok = same or g_in_b_house in (1, 7, 5, 9, 4, 10, 3, 11)
    el_ok = (g_el == b_el) or ((g_el, b_el) in _FRIENDLY_ELEMENTS)
    axis_word = {
        1: "same ascendant (1/1) — deep familiarity",
        7: "7/1 axis — the natural marriage axis, strong attraction",
        5: "5/9 trine — affection and dharma", 9: "5/9 trine — affection and dharma",
        4: "4/10 — home vs duty, workable", 10: "4/10 — home vs duty, workable",
        3: "3/11 — friendly and growth-oriented", 11: "3/11 — friendly and growth-oriented",
        2: "2/12 — give-and-take, needs effort", 12: "2/12 — give-and-take, needs effort",
        6: "6/8 — friction axis, handle with care", 8: "6/8 — friction axis, handle with care",
    }.get(g_in_b_house, "")
    lagna_check = {
        "id": "d9_lagna_harmony",
        "name": "D9 ascendant harmony",
        "ok": axis_ok and el_ok,
        "detail": (
            f"Groom D9 lagna {g['lagna']} ({g_el}) · Bride D9 lagna {b['lagna']} ({b_el}); "
            f"{axis_word or 'mixed axis'}"
            + ("" if el_ok else "; elements not naturally compatible")
        ),
    }

    checks: list[dict[str, Any]] = [
        lagna_check,
        _seventh_health(g, "Groom"),
        _seventh_health(b, "Bride"),
        _karaka_health(g, "Venus", "Groom", "marital comfort & spouse bond"),
        _karaka_health(b, "Jupiter", "Bride", "husband bond & wisdom in union"),
        _overlay_synastry(g, b, "Groom", "Bride"),
        _overlay_synastry(b, g, "Bride", "Groom"),
    ]

    passed = sum(1 for c in checks if c["ok"])
    total = len(checks)
    pct = round(100 * passed / total)
    if passed >= total - 1:
        verdict, headline = "strong", "Navamsha (D9) strongly supports the marriage — promise and harmony both hold."
    elif passed >= total * 0.5:
        verdict, headline = "mixed", "Navamsha (D9) is broadly supportive but uneven — note the flagged areas and use remedies."
    else:
        verdict, headline = "weak", "Navamsha (D9) shows real strain — proceed only with remedies and open eyes."

    return {
        "available": True,
        "groom_d9_lagna": g["lagna"],
        "groom_d9_lagna_lord": g["lagna_lord"],
        "bride_d9_lagna": b["lagna"],
        "bride_d9_lagna_lord": b["lagna_lord"],
        "checks": checks,
        "passed": passed,
        "total": total,
        "score_pct": pct,
        "verdict": verdict,
        "headline": headline,
    }


def run_ashtakoota(
    groom_pc: dict,
    bride_pc: dict,
    *,
    method: str = "North",
) -> dict[str, Any]:
    _ensure_pyjhora()
    from jhora.horoscope.match.compatibility import Ashtakoota, nakshatra_list

    g_nak, g_pada = _moon_nak_pada(groom_pc)
    b_nak, b_pada = _moon_nak_pada(bride_pc)
    g_idx = _nakshatra_pj_index(g_nak)
    b_idx = _nakshatra_pj_index(b_nak)

    ak = Ashtakoota(g_idx, g_pada, b_idx, b_pada, method=method)
    results = ak.compatibility_score()

    if method.lower().startswith("south"):
        total = float(results[8])
        koots = []
        return {
            "method": "South",
            "total_guna": total,
            "max_guna": 10,
            "band": "good" if total >= 7 else ("moderate" if total >= 5 else "avoid"),
            "band_plain": f"South Indian porutham score {total}/10",
            "koots": koots,
            "groom_nakshatra": g_nak,
            "groom_pada": g_pada,
            "bride_nakshatra": b_nak,
            "bride_pada": b_pada,
            "bhakoot_dosha": not bool(results[6]),
            "nadi_dosha": not bool(results[7]),
            "extra_porutham": {
                "mahendra": bool(results[9]),
                "vedha": bool(results[10]),
                "rajju": bool(results[11]),
                "sthree_dheerga": bool(results[12]),
            },
        }

    scores = results[:8]
    total = float(results[8])
    band, band_plain = _guna_band(total)
    koot_fns = {
        "varna": ak.varna_porutham,
        "vashya": ak.vasiya_porutham,
        "gana": ak.gana_porutham,
        "tara": ak.tara_porutham,
        "yoni": ak.yoni_porutham,
        "maitri": ak.raasi_adhipathi_porutham,
        "bhakoot": ak.raasi_porutham,
        "nadi": ak.naadi_porutham,
    }
    koots = []
    for key, label, mx in KOOT_DEFS_NORTH:
        score = _koot_score(koot_fns[key])
        koots.append({
            "id": key,
            "label": label,
            "score": score,
            "max": mx,
            "ok": score > 0,
        })

    g_moon = (groom_pc.get("planets") or {}).get("Moon") or {}
    b_moon = (bride_pc.get("planets") or {}).get("Moon") or {}

    return {
        "method": "North",
        "total_guna": total,
        "max_guna": 36,
        "band": band,
        "band_plain": band_plain,
        "koots": koots,
        "groom_nakshatra": g_nak,
        "groom_pada": g_pada,
        "bride_nakshatra": b_nak,
        "bride_pada": b_pada,
        "groom_moon_sign": g_moon.get("sign", ""),
        "bride_moon_sign": b_moon.get("sign", ""),
        "groom_moon_degree": g_moon.get("degree_in_sign"),
        "bride_moon_degree": b_moon.get("degree_in_sign"),
        "groom_moon_display": _moon_display(g_moon),
        "bride_moon_display": _moon_display(b_moon),
        "groom_nak_pj": nakshatra_list[g_idx - 1],
        "bride_nak_pj": nakshatra_list[b_idx - 1],
        "bhakoot_dosha": _koot_score(ak.raasi_porutham) == 0,
        "nadi_dosha": _koot_score(ak.naadi_porutham) == 0,
        "extra_porutham": {
            "mahendra": bool(results[9]),
            "vedha": bool(results[10]),
            "rajju": bool(results[11]),
            "sthree_dheerga": bool(results[12]),
        },
    }


def assess_doshas(
    ashtakoota: dict[str, Any],
    groom_manglik: dict[str, Any],
    bride_manglik: dict[str, Any],
) -> dict[str, Any]:
    total = float(ashtakoota.get("total_guna") or 0)
    max_g = float(ashtakoota.get("max_guna") or 36)
    items: list[dict[str, Any]] = []

    if ashtakoota.get("nadi_dosha"):
        waived = total >= 28 and ashtakoota.get("method") == "North"
        items.append({
            "name": "Nadi dosha",
            "active": True,
            "waived": waived,
            "detail": "Same Nadi - classical obstruction to health/progeny"
            + ("; waived when 28+ guns (Bhardwaj)" if waived else ""),
        })
    if ashtakoota.get("bhakoot_dosha"):
        waived = total >= 28 and ashtakoota.get("method") == "North"
        items.append({
            "name": "Bhakoot dosha",
            "active": True,
            "waived": waived,
            "detail": (
                f"Moon signs {ashtakoota.get('groom_moon_sign')} / {ashtakoota.get('bride_moon_sign')} "
                "- 2-12, 5-9 or 6-8 axis per Bhardwaj"
            )
            + ("; waived when 28+ guns (Bhardwaj)" if waived else ""),
        })

    g_act = groom_manglik.get("active", False)
    b_act = bride_manglik.get("active", False)
    if g_act or b_act:
        mutual = g_act and b_act
        waived = (total >= 28 and ashtakoota.get("method") == "North") or mutual
        items.append({
            "name": "Manglik dosha",
            "active": True,
            "waived": waived,
            "detail": (
                "Both partners Manglik - often treated as mutual cancellation"
                if mutual
                else "One partner Manglik - match the other or use remedies"
            )
            + ("; also waived at 28+ guns per Bhardwaj" if total >= 28 else ""),
        })

    active_hard = [d for d in items if d["active"] and not d["waived"]]
    return {
        "items": items,
        "active_count": len([d for d in items if d["active"]]),
        "blocking": active_hard,
        "has_blocking": bool(active_hard),
    }


def final_verdict(
    ashtakoota: dict[str, Any],
    doshas: dict[str, Any],
    goel: dict[str, Any],
    d9_compat: dict[str, Any] | None = None,
) -> dict[str, Any]:
    band = ashtakoota.get("band", "avoid")
    blocking = doshas.get("has_blocking", False)
    goel_v = goel.get("verdict", "weak")
    d9_v = (d9_compat or {}).get("verdict", "")

    if band == "avoid" or (blocking and band == "moderate"):
        v, headline = "no", "This pairing is not recommended on classical gun Milan."
    elif blocking:
        v, headline = "caution", "Guns are acceptable but active doshas need remedies before marriage."
    elif band in ("good", "excellent") and goel_v in ("strong", "mixed"):
        v, headline = "yes", "Good gun Milan with supportive Navamsha synastry."
    elif band == "moderate":
        v, headline = "caution", "Moderate gun Milan - workable with strong Navamsha support and remedies."
    else:
        v, headline = "caution", "Mixed picture - review doshas and D9 synastry before deciding."

    # The D9 is the primary marriage chart: a weak D9 tempers a 'yes', while a
    # strong D9 can lift a borderline-moderate match.
    if d9_v == "weak" and v == "yes":
        v, headline = "caution", "Guns are good, but the Navamsha (D9) shows strain — address it with remedies first."
    elif d9_v == "strong" and v == "caution" and band == "moderate" and not blocking:
        headline += " Navamsha (D9) is strong, which is a meaningful point in favour."

    return {"verdict": v, "headline": headline, "d9_verdict": d9_v}


def match_kundali(
    *,
    groom: dict[str, Any],
    bride: dict[str, Any],
    method: str = "North",
    groom_name: str = "",
    bride_name: str = "",
    groom_dob: str = "",
    bride_dob: str = "",
) -> dict[str, Any]:
    """Full 3-layer match. groom/bride = build_person_chart() outputs."""
    ashtakoota = run_ashtakoota(groom, bride, method=method)
    groom_manglik = _assess_manglik(groom)
    bride_manglik = _assess_manglik(bride)
    doshas = assess_doshas(ashtakoota, groom_manglik, bride_manglik)
    goel = _goel_synastry(groom, bride)
    d9_compat = d9_compatibility(groom, bride)
    remissions = assess_remissions(groom, bride, ashtakoota)
    remedies = remedies_for_match(ashtakoota, doshas, remissions)
    verdict = final_verdict(ashtakoota, doshas, goel, d9_compat)

    g_name = groom_name or (groom.get("meta") or {}).get("name") or ""
    b_name = bride_name or (bride.get("meta") or {}).get("name") or ""
    g_dob = groom_dob or (groom.get("meta") or {}).get("dob") or ""
    b_dob = bride_dob or (bride.get("meta") or {}).get("dob") or ""

    numerology: dict[str, Any] = {"available": False}
    try:
        from numerology_marriage_compat import marriage_numerology_compat

        numerology = marriage_numerology_compat(
            groom_name=g_name,
            groom_dob=g_dob,
            bride_name=b_name,
            bride_dob=b_dob,
        )
    except Exception as exc:
        numerology = {"available": False, "reason": str(exc)}

    sources = (
        "PyJHora Ashtakoota + Bhardwaj rules37 OCR + Goel rules3 Ch.3 + Navamsha (D9) synastry"
        + (" + Woods/Avasthi numerology + 7-phase advanced protocol" if numerology.get("available") else "")
    )

    return {
        "available": True,
        "ashtakoota": ashtakoota,
        "manglik": {"groom": groom_manglik, "bride": bride_manglik},
        "doshas": doshas,
        "remissions": remissions,
        "remedies": remedies,
        "goel_synastry": goel,
        "d9_compatibility": d9_compat,
        "numerology": numerology,
        "verdict": verdict,
        "sources": sources,
        "audit_note": (
            "Scores are computed using the classical Ashtakoota method."
        ),
    }
