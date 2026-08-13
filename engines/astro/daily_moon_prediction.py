#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Personal daily Moon guide  -  Python-only, book-backed confluence.

Sources woven in:
  - Bhardwaj gochar tables (bhardwaj_book_data.json / rules3)
  - Ashtakavarga transit qualification (rules10 / ashtakavarga_analysis)
  - GK transit + dasha pairing (rules11)
  - Numerology lucky series (rules23, precomputed numerology block)
  - Gemstone/day colours (rules40/41, gemstone_remedy)
  - Tarabala / Chandrabal (classical panchang on natal Moon)
  - Moonology Daily Moon + phase + remedy (rules44/Boland, sidereal-aligned)
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from astro_precompute import NAKSHATRAS, NAK_TO_DASHA_LORD, SIGN_LORDS, SIGNS, degree_to_nakshatra
from ashtakavarga_analysis import HOUSE_LIFE_THEME, PLANET_THEME, bav_transit_meaning, sav_house_meaning
from daily_moon_personalized_dos import build_personalized_dos_donts
from daily_vedic_confluence import active_vimshottari, build_vedic_daily_confluence
from daily_reading_plain import plain_opening
from muhurat_daily import build_daily_muhurat
from lunation_timing import is_new_moon_applicable
from daily_moon_rules_data import (
    CHANDRA_RULES,
    LUCKY_SERIES,
    TARABALA_RULES,
    color_from_gem_rules,
)
from moonology_extended_data import apply_moonology_extras
from moonology_rules_data import (
    DAILY_MOON_HOUSE_RULES,
    DAILY_MOON_SIGN_RULES,
    ELEMENT_FLAVOUR,
    MOON_PHASE_RULES,
    SIGN_ELEMENTS,
    SOURCE_TAG as MOONOLOGY_SOURCE,
)

BASE_DIR = Path(__file__).resolve().parent

try:
    import swisseph as swe

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    _SWE = True
except Exception:
    _SWE = False

_PLANET_IDS = {
    "Sun": getattr(swe, "SUN", 0),
    "Moon": getattr(swe, "MOON", 1),
    "Mars": getattr(swe, "MARS", 4),
    "Mercury": getattr(swe, "MERCURY", 2),
    "Jupiter": getattr(swe, "JUPITER", 5),
    "Venus": getattr(swe, "VENUS", 3),
    "Saturn": getattr(swe, "SATURN", 6),
    "Rahu": getattr(swe, "TRUE_NODE", 11),
} if _SWE else {}

WEEKDAY_LORD = {
    0: "Moon", 1: "Mars", 2: "Mercury", 3: "Jupiter", 4: "Venus", 5: "Saturn", 6: "Sun",
}


def _ordinal_suffix(value: Any) -> str:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return "th"
    if 10 <= n % 100 <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _load_gochar_tables() -> tuple[dict, dict]:
    path = BASE_DIR / "bhardwaj_book_data.json"
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("gochar_auspicious", {}), data.get("gochar_inauspicious", {})
    return {}, {}


def _jd_ut(d: date, hour_ut: float = 6.0) -> float:
    return swe.julday(d.year, d.month, d.day, hour_ut) if _SWE else 0.0


_EPHE_PATH: Optional[str] = None


def _ephe_path() -> str:
    global _EPHE_PATH
    if _EPHE_PATH is None:
        try:
            from jhora import const as _jconst
            _EPHE_PATH = str(getattr(_jconst, "_ephe_path", "") or "")
        except Exception:
            _EPHE_PATH = ""
    return _EPHE_PATH


def ensure_sidereal() -> None:
    """Re-assert this module's ephemeris settings before any transit maths.

    swisseph keeps one ayanamsa and one set of open ephemeris handles per
    process, and three other engines in this codebase move them: kp_horary_engine
    switches the ayanamsa to Krishnamurti, PyJHora points the path at its own
    bundled files, and PyJHora closes the handles when it is finished. Whichever
    ran last in the worker would otherwise decide silently which ayanamsa a
    daily reading is computed in, and a closed handle makes the lunar-node
    call fail outright — which is why the first daily reading in a process
    succeeded and later ones did not.

    The module-level `set_sid_mode` at import runs once and cannot defend
    against that. Setting it per reading costs nothing measurable.
    """
    if not _SWE:
        return
    swe.set_ephe_path(_ephe_path())
    swe.set_sid_mode(swe.SIDM_LAHIRI)


def _sid_lon(planet: str, jd_ut: float) -> float:
    if not _SWE:
        return 0.0
    pid = _PLANET_IDS[planet]
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED
    target = swe.TRUE_NODE if planet == "Rahu" else pid
    try:
        lon = swe.calc_ut(jd_ut, target, flags)[0][0]
    except swe.Error:
        # Another engine left the ephemeris closed mid-process. Reopen once.
        ensure_sidereal()
        lon = swe.calc_ut(jd_ut, target, flags)[0][0]
    return lon % 360.0


def _moon_phase_name(elongation: float) -> str:
    """Eight Boland phases from Sun-Moon elongation (0=new, 180=full)."""
    e = elongation % 360.0
    if e >= 337.5 or e < 22.5:
        return "New Moon"
    if e < 67.5:
        return "Waxing Crescent"
    if e < 112.5:
        return "First Quarter"
    if e < 157.5:
        return "Gibbous Moon"
    if e < 202.5:
        return "Full Moon"
    if e < 247.5:
        return "Disseminating Moon"
    if e < 292.5:
        return "Third Quarter"
    return "Balsamic Moon"


def _build_moonology(
    jd: float,
    moon_sign: str,
    lagna_sign: str,
) -> dict[str, Any]:
    """Boland Moonology lane - same sidereal Moon sign + natal lagna as the Vedic transit block."""
    sun_lon = _sid_lon("Sun", jd)
    moon_lon = _sid_lon("Moon", jd)
    elongation = (moon_lon - sun_lon) % 360.0
    phase = _moon_phase_name(elongation)
    computed_sign = SIGNS[int(moon_lon // 30) % 12]
    if computed_sign != moon_sign:
        moon_sign = computed_sign
    house = _house_from(lagna_sign, moon_sign)

    sign_rules = DAILY_MOON_SIGN_RULES.get(moon_sign, {})
    phase_rules = MOON_PHASE_RULES.get(phase, {})
    house_rules = DAILY_MOON_HOUSE_RULES.get(house, {})
    element = SIGN_ELEMENTS.get(moon_sign, "")

    return {
        "zodiac_system": "Sidereal (Lahiri)",
        "moon_sign": moon_sign,
        "element": element,
        "element_note": ELEMENT_FLAVOUR.get(element, ""),
        "phase": phase,
        "phase_keywords": phase_rules.get("keywords", ""),
        "elongation_deg": round(elongation, 1),
        "house_from_asc": house,
        "natal_asc_sign": lagna_sign,
        "sign_summary": sign_rules.get("summary", ""),
        "good_for": sign_rules.get("good_for", ""),
        "not_good_for": sign_rules.get("not_good_for", ""),
        "sign_do": sign_rules.get("do", ""),
        "sign_dont": sign_rules.get("dont", ""),
        "sign_remedy": sign_rules.get("remedy", ""),
        "phase_summary": phase_rules.get("summary", ""),
        "phase_remedy": phase_rules.get("remedy", ""),
        "phase_dos": [
            {"text": t, "source": s} for t, s in phase_rules.get("dos", [])[:2]
        ],
        "phase_donts": [
            {"text": t, "source": s} for t, s in phase_rules.get("donts", [])[:1]
        ],
        "house_summary": house_rules.get("summary", ""),
        "house_do": house_rules.get("do", ""),
        "house_remedy": house_rules.get("remedy", ""),
        "source": MOONOLOGY_SOURCE,
    }

def _sign_idx(lon: float) -> int:
    return int(lon // 30) % 12


def _house_from(ref_sign: str, transit_sign: str) -> int:
    return (SIGNS.index(transit_sign) - SIGNS.index(ref_sign)) % 12 + 1


def _nak_index(name: str) -> int:
    for i, n in enumerate(NAKSHATRAS):
        if n.lower() == (name or "").lower():
            return i
    return 0


def _pancha_index(diff: int) -> int:
    return (diff % 9) + 1


def _active_ad(pc: dict, d: date) -> tuple[str, str]:
    vim = pc.get("vimshottari", {})
    md = vim.get("current_md", {}).get("md_lord", "")
    ad = ""
    for row in vim.get("current_md_antardashas", []):
        start = row.get("start", "")
        end = row.get("end", "")
        if start and end and start <= d.isoformat() <= end:
            ad = row.get("ad_lord", "")
            break
    return md, ad


def _sign_residents(pc: dict, sign: str) -> list[str]:
    out = []
    for pl, v in pc.get("planets", {}).items():
        if v.get("sign") == sign:
            out.append(pl)
    return out


def _same_sign_or_close(lon_a: float, lon_b: float, orb: float = 8.0) -> bool:
    diff = abs((lon_a - lon_b + 180) % 360 - 180)
    return diff <= orb


def _score_tone(ausp: bool, inaus: bool, sav: int, bav: int, tara: str, chandra: str) -> str:
    score = 0
    if ausp:
        score += 2
    if inaus:
        score -= 2
    if sav >= 30:
        score += 1
    elif sav < 25:
        score -= 1
    if bav >= 5:
        score += 1
    elif bav <= 3:
        score -= 1
    if tara == "auspicious":
        score += 1
    elif tara == "caution":
        score -= 1
    if chandra == "auspicious":
        score += 1
    elif chandra == "caution":
        score -= 1
    if score >= 3:
        return "bright"
    if score >= 1:
        return "mixed-positive"
    if score <= -3:
        return "sensitive"
    if score <= -1:
        return "mixed-caution"
    return "steady"


def _day_seed(target: date, transit_nak: str, moon_house: int, tara_idx: int, chandra_idx: int, ad_lord: str) -> int:
    nak_i = 0
    for i, n in enumerate(NAKSHATRAS):
        if n == transit_nak:
            nak_i = i
            break
    return (
        target.toordinal() * 13
        + nak_i * 7
        + moon_house * 11
        + tara_idx * 3
        + chandra_idx * 5
        + sum(ord(c) for c in (ad_lord or ""))
    )


def _lucky_numbers(pc: dict, target: date, tara_idx: int, chandra_idx: int, transit_nak_idx: int) -> dict:
    num = pc.get("numerology", {})
    lp = int(num.get("life_path") or num.get("birth_day") or 1)
    lp = ((lp - 1) % 9) + 1
    series = LUCKY_SERIES.get(lp, LUCKY_SERIES[1])
    seed = target.toordinal() + transit_nak_idx + tara_idx
    primary = series[seed % len(series)]
    secondary = series[(seed + chandra_idx + target.day) % len(series)]
    tertiary = series[(seed + tara_idx * 2 + 1) % len(series)]
    anchors = [
        {"value": str(primary), "source": "lucky number series", "reason": f"Life-path {lp} series index from date+nakshatra+Tarabala ({tara_idx})"},
        {"value": str(secondary), "source": "lucky number series", "reason": f"Rotated by Chandrabal ({chandra_idx}) and calendar day"},
        {"value": str(tertiary), "source": "lucky number series", "reason": f"Tarabala band offset in LP{lp} series"},
    ]
    return {
        "primary": primary,
        "secondary": secondary,
        "tertiary": tertiary,
        "anchors": anchors,
        "series_note": f"Life-path {lp} series (rules23): {', '.join(str(x) for x in series[:5])}",
        "avoid": [18],
        "avoid_note": "rules23: 18 is unfavourable for relationship choices",
    }


def _lucky_colors(
    weekday_lord: str,
    moon_nak_lord: str,
    transit_moon_sign: str,
    tone: str,
) -> list[dict]:
    sign_lord = SIGN_LORDS.get(transit_moon_sign, "Moon")
    colors: list[dict] = []
    # The weekday lord, the nakshatra lord and the sign lord are frequently the
    # same planet, and listing one colour three times reads like a bug.
    seen: set[str] = set()
    for planet, role in (
        (weekday_lord, "the planet ruling today"),
        (moon_nak_lord, f"the lord of today's star"),
        (sign_lord, f"the lord of {transit_moon_sign}, where the Moon is"),
    ):
        if not planet or planet in seen:
            continue
        seen.add(planet)
        name, note = color_from_gem_rules(planet)
        colors.append({
            "name": name,
            "why": f"{planet} is {role}. {note}".strip(),
            "source": f"rules40/41 GEM_DATA ({role}: {planet})",
        })
    if tone in ("sensitive", "mixed-caution") and "Moon" not in seen:
        w, _ = color_from_gem_rules("Moon")
        colors.append({
            "name": w,
            "why": "A cooling neutral, because Tarabala and Chandrabala are both stressed today.",
            "source": "rules40/41 Moon",
        })
    return colors[:3]


def _rule_item(text: str, source: str) -> dict:
    return {"text": text, "source": source}


def _dasha_lord_ashtakavarga(
    *,
    lords: list[tuple[str, str]],
    transits: dict[str, dict],
    jd: float,
    sav_list: list,
    bav: dict,
    natal_moon_sign: str,
    lagna: str,
    residents_of,
) -> list[dict[str, Any]]:
    """Bindus on the sign each running dasha lord is crossing today.

    The daily block already scores Moon, Sun and Mercury, which are the fast
    movers  -  but the planet actually running the chart is the mahadasha /
    antardasha / pratyantardasha lord, and nothing was reading its transit
    sign. That number is the bridge between the clock and the sky: a period
    lord crossing a sign where it owns few bindus is exactly the case where the
    remedy is worth naming, and where a promising-looking dasha underdelivers.

    Rahu and Ketu have no bhinnashtakavarga of their own in the Parashari
    scheme, so they are reported on the sign's sarvashtakavarga alone rather
    than being handed a fabricated bindu count.
    """
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for role, lord in lords:
        if not lord or lord in seen:
            continue
        seen.add(lord)

        t = transits.get(lord)
        if t is not None:
            sign = t["sign"]
            h_moon = t["house_from_moon"]
            h_lagna = t["house_from_lagna"]
        elif lord == "Ketu":
            lon = (_sid_lon("Rahu", jd) + 180.0) % 360.0
            sign = SIGNS[_sign_idx(lon)]
            h_moon = _house_from(natal_moon_sign, sign)
            h_lagna = _house_from(lagna, sign)
        else:
            continue

        si = SIGNS.index(sign)
        sav = sav_list[si] if si < len(sav_list) else 28
        own = bav.get(lord)
        bv = own[si] if own and si < len(own) else None

        if bv is None:
            meaning = sav_house_meaning(h_lagna, sav, sign, residents_of(sign))
            meaning += (f" {lord} carries no bindus of its own in the classical "
                        f"scheme, so the sign's own total is the reading.")
        else:
            meaning = bav_transit_meaning(lord, h_lagna, bv, sav)

        rows.append({
            "role": role,
            "planet": lord,
            "sign": sign,
            "sav": sav,
            "bav": bv,
            "house_from_moon": h_moon,
            "house_from_lagna": h_lagna,
            "meaning": meaning,
        })
    return rows


def compute_daily_moon_guide(
    pc: dict,
    target: date | None = None,
    *,
    latitude: float = 28.6,
    longitude: float = 77.2,
    timezone: float = 5.5,
) -> dict[str, Any]:
    """Build structured daily guide from precomputed chart JSON."""
    if not _SWE:
        raise RuntimeError("pyswisseph required for daily transit math")

    target = target or date.today()
    ensure_sidereal()
    meta = pc.get("meta", {})
    client = meta.get("client", "Client")
    lagna = meta.get("lagna_sign") or pc.get("lagna", {}).get("sign", "Aries")
    birth = pc.get("birth", {})
    raw = pc.get("raw_sections", {})
    latitude = float(
        birth.get("latitude")
        or meta.get("latitude")
        or raw.get("latitude")
        or latitude
    )
    longitude = float(
        birth.get("longitude")
        or meta.get("longitude")
        or raw.get("longitude")
        or longitude
    )
    moon_natal = pc.get("planets", {}).get("Moon", {})
    moon_sign = moon_natal.get("sign", "Cancer")
    moon_nak = moon_natal.get("nakshatra", "Rohini")
    moon_nak_idx = _nak_index(moon_nak)

    # Local sunrise approximation ? UT hour for chart
    ut_hour = max(0.0, 6.0 - timezone)
    jd = _jd_ut(target, ut_hour)

    transits: dict[str, dict] = {}
    for pl in ("Sun", "Moon", "Mercury", "Mars", "Jupiter", "Venus", "Saturn", "Rahu"):
        lon = _sid_lon(pl, jd)
        sign = SIGNS[_sign_idx(lon)]
        deg = lon % 30
        nak = degree_to_nakshatra(lon)
        h_moon = _house_from(moon_sign, sign)
        h_lagna = _house_from(lagna, sign)
        transits[pl] = {
            "sign": sign,
            "degree": round(deg, 2),
            "longitude": round(lon, 2),
            "nakshatra": nak.get("nakshatra"),
            "pada": nak.get("pada"),
            "house_from_moon": h_moon,
            "house_from_lagna": h_lagna,
        }

    moon_t = transits["Moon"]
    sun_t = transits["Sun"]
    merc_t = transits["Mercury"]

    tara_idx = _pancha_index(_nak_index(moon_t["nakshatra"]) - moon_nak_idx)
    chandra_idx = _pancha_index(SIGNS.index(moon_t["sign"]) - SIGNS.index(moon_sign))
    tara = TARABALA_RULES[tara_idx]
    chandra = CHANDRA_RULES[chandra_idx]
    tara_name, tara_tone, tara_note = tara["name"], tara["tone"], tara["summary"]
    chandra_name, chandra_tone, chandra_note = chandra["name"], chandra["tone"], chandra["dos"][0][0] if chandra["dos"] else ""

    aus_tbl, inaus_tbl = _load_gochar_tables()

    def gochar_flag(pl: str) -> tuple[bool, bool]:
        h = transits[pl]["house_from_moon"]
        return h in aus_tbl.get(pl, []), h in inaus_tbl.get(pl, [])

    av = pc.get("ashtakavarga", {})
    sav_list = av.get("sav", [28] * 12)
    bav = av.get("bav", {})

    def av_for(sign: str, planet: str) -> tuple[int, int]:
        si = SIGNS.index(sign)
        sav = sav_list[si] if si < len(sav_list) else 28
        pb = bav.get(planet, [4] * 12)
        return sav, pb[si] if si < len(pb) else 4

    moon_sav, moon_bav = av_for(moon_t["sign"], "Moon")
    sun_sav, sun_bav = av_for(sun_t["sign"], "Sun")
    merc_sav, merc_bav = av_for(merc_t["sign"], "Mercury")

    moon_aus, moon_inaus = gochar_flag("Moon")
    sun_aus, sun_inaus = gochar_flag("Sun")
    merc_aus, merc_inaus = gochar_flag("Mercury")

    day_tone = _score_tone(moon_aus, moon_inaus, moon_sav, moon_bav, tara_tone, chandra_tone)

    dasha_active = active_vimshottari(pc, target)
    md_lord, ad_lord, pd_lord = dasha_active["md"], dasha_active["ad"], dasha_active["pd"]
    weekday = target.weekday()
    weekday_lord = WEEKDAY_LORD[weekday]

    # Slow-planet confluence with today's Moon / Sun / Mercury
    slow_notes: list[str] = []
    moon_lon = _sid_lon("Moon", jd)
    for pl in ("Jupiter", "Saturn", "Mars", "Venus", "Rahu", "Ketu"):
        lon = _sid_lon("Rahu" if pl == "Ketu" else pl, jd)
        if pl == "Ketu":
            lon = (lon + 180) % 360
        sign = SIGNS[_sign_idx(lon)]
        h = _house_from(moon_sign, sign)
        natal = pc.get("planets", {}).get(pl, {})
        natal_sign = natal.get("sign", "")
        natal_house = natal.get("house", 0)
        if sign == moon_t["sign"]:
            slow_notes.append(
                f"Transit {pl} shares {moon_t['sign']} with today's Moon  -  "
                f"GK transit rule: blended mood; natal {pl} in {natal_sign} (house {natal_house}) colours how you feel it."
            )
        elif _same_sign_or_close(lon, moon_lon, 10.0):
            slow_notes.append(
                f"Transit {pl} conjunct today's Moon within tight orb  -  emotional amplifier; "
                f"natal {pl} dignity {natal.get('dignity', 'neutral')} sets the volume."
            )
        elif h in (aus_tbl.get(pl, [])):
            sav, bv = av_for(sign, pl)
            slow_notes.append(
                f"{pl} in supportive {h}{_ordinal_suffix(h)}-from-natal-Moon ({sign}); SAV {sav}, {pl} BAV {bv}."
            )
        elif h in (inaus_tbl.get(pl, [])):
            slow_notes.append(
                f"{pl} crosses stressed gochar house {h} from your Moon ({sign})  -  pace major {pl.lower()} themes."
            )
    if pd_lord:
        pd_natal = pc.get("planets", {}).get(pd_lord, {})
        if pd_natal.get("sign") == moon_t["sign"]:
            slow_notes.insert(
                0,
                f"Transit Moon shares {moon_t['sign']} with natal {pd_lord} ({pd_lord} pratyantar lord)  -  "
                f"the fine dasha clock and lunar weather align today.",
            )

    moon_house = moon_t["house_from_moon"]
    theme = HOUSE_LIFE_THEME.get(moon_house, "today's emotional focus")
    residents = ", ".join(_sign_residents(pc, moon_t["sign"]))

    sav_line = sav_house_meaning(
        moon_house, moon_sav, moon_t["sign"], residents,
    )
    bav_line = bav_transit_meaning("Moon", moon_house, moon_bav, moon_sav)

    sun_line = ""
    if sun_aus and not sun_inaus:
        sun_line = (
            f"Sun in {sun_t['sign']} ({sun_t['house_from_moon']}th from your Moon) rides an auspicious gochar lane  -  "
            f"visibility and {PLANET_THEME['Sun'].split(',')[0]} get a cleaner channel."
        )
    elif sun_inaus:
        sun_line = (
            f"Sun stresses the {sun_t['house_from_moon']}th-from-Moon gochar house  -  keep authority moves modest."
        )
    else:
        sun_line = f"Sun in {sun_t['sign']} ({sun_t['house_from_moon']}th from Moon) sets the daylight backdrop."

    merc_line = ""
    if merc_aus:
        merc_line = (
            f"Mercury in {merc_t['sign']} favours mail, study, and trade loops (gochar + BAV {merc_bav}/8)."
        )
    elif merc_inaus:
        merc_line = (
            f"Mercury in {merc_t['sign']} warns against rushed signatures  -  read the fine print twice."
        )
    else:
        merc_line = f"Mercury in {merc_t['sign']} ({merc_t['house_from_moon']}th from Moon) shapes thinking tempo."

    vedic = build_vedic_daily_confluence(
        client=client,
        target=target,
        pc=pc,
        lagna=lagna,
        moon_transit=moon_t,
        sun_transit=sun_t,
        mercury_transit=merc_t,
        tara={"name": tara_name, "tone": tara_tone},
        chandra={"name": chandra_name, "tone": chandra_tone},
        tone=day_tone,
        moon_sav=moon_sav,
        moon_bav=moon_bav,
        moon_aus=moon_aus,
        moon_inaus=moon_inaus,
        sun_aus=sun_aus,
        sun_inaus=sun_inaus,
        merc_aus=merc_aus,
        merc_inaus=merc_inaus,
        sav_line=sav_line,
        bav_line=bav_line,
        slow_notes=slow_notes,
    )
    dasha_note = vedic["dasha_note"]

    lord_av = _dasha_lord_ashtakavarga(
        lords=[("Mahadasha", md_lord), ("Antardasha", ad_lord),
               ("Pratyantardasha", pd_lord)],
        transits=transits,
        jd=jd,
        sav_list=sav_list,
        bav=bav,
        natal_moon_sign=moon_sign,
        lagna=lagna,
        residents_of=lambda s: ", ".join(_sign_residents(pc, s)),
    )
    if lord_av:
        scored = [r for r in lord_av if r["bav"] is not None]
        signal = "; ".join(
            (f"{r['planet']} {r['bav']}/8 in {r['sign']}" if r["bav"] is not None
             else f"{r['planet']} in {r['sign']}, sign SAV {r['sav']}")
            for r in lord_av)
        # Weight follows the weakest lord: one thin period lord is the whole
        # point of computing this, and it should not be averaged away.
        weakest = min((r["bav"] for r in scored), default=4)
        vedic.setdefault("lanes", []).append({
            "lane": "Dasha-lord Ashtakavarga",
            "signal": signal,
            "weight": "high" if (weakest <= 3 or weakest >= 5) else "medium",
        })

    nak_lord = NAK_TO_DASHA_LORD.get(moon_t["nakshatra"], "Moon")
    transit_nak_idx = _nak_index(moon_t["nakshatra"])

    lucky_nums = _lucky_numbers(pc, target, tara_idx, chandra_idx, transit_nak_idx)
    lucky_cols = _lucky_colors(weekday_lord, nak_lord, moon_t["sign"], day_tone)
    moon_elong = (_sid_lon("Moon", jd) - _sid_lon("Sun", jd)) % 360.0
    moon_phase = _moon_phase_name(moon_elong)
    nm_applicable = is_new_moon_applicable(target, timezone)

    dos, donts, dos_donts_intro = build_personalized_dos_donts(
        client=client,
        target=target,
        natal_moon_sign=moon_sign,
        natal_moon_nak=moon_nak,
        lagna=lagna,
        moon_transit=moon_t,
        sun_transit=sun_t,
        merc_transit=merc_t,
        tara_idx=tara_idx,
        chandra_idx=chandra_idx,
        weekday_lord=weekday_lord,
        md_lord=md_lord,
        ad_lord=ad_lord,
        pd_lord=pd_lord,
        jaimini_pd_sign=vedic.get("jaimini", {}).get("pd", ""),
        moon_aus=moon_aus,
        moon_inaus=moon_inaus,
        sun_aus=sun_aus,
        sun_inaus=sun_inaus,
        merc_aus=merc_aus,
        merc_inaus=merc_inaus,
        moon_sav=moon_sav,
        moon_bav=moon_bav,
        slow_notes=slow_notes,
        moon_phase=moon_phase,
        new_moon_applicable=nm_applicable,
    )

    opening = plain_opening(
        client=client,
        target=target,
        tone=day_tone,
        moon_t=moon_t,
        tara={"name": tara_name, "tone": tara_tone},
        chandra={"name": chandra_name, "tone": chandra_tone},
        moon_h=int(moon_t.get("house_from_moon", 1)),
        verdict_plain=vedic.get("verdict_plain") or vedic.get("verdict", ""),
    )

    natal_sun = pc.get("planets", {}).get("Sun", {}).get("sign", "")
    birth_place = meta.get("birth_place") or birth.get("place") or raw.get("place") or ""
    moonology = apply_moonology_extras(
        _build_moonology(jd, moon_t["sign"], lagna),
        target=target,
        client=client,
        natal_sun_sign=natal_sun,
        natal_lagna=lagna,
        timezone=timezone,
        place=birth_place,
    )

    muhurat = build_daily_muhurat(
        pc=pc,
        target=target,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        place_name=birth_place or "BirthPlace",
    )

    return {
        "client": client,
        "date": target.isoformat(),
        "weekday": target.strftime("%A"),
        "weekday_lord": weekday_lord,
        "tone": day_tone,
        "opening": opening,
        "moon_transit": moon_t,
        "sun_transit": sun_t,
        "mercury_transit": merc_t,
        "tarabala": {"index": tara_idx, "name": tara_name, "tone": tara_tone, "note": tara_note},
        "chandrabal": {
            "index": chandra_idx, "name": chandra_name, "tone": chandra_tone,
            # Do/Don't must not be swapped — a "do" under Don't reads as broken English.
            "do_note": (chandra["dos"][0][0] if chandra.get("dos") else ""),
            "note": (chandra["donts"][0][0] if chandra.get("donts") else ""),
        },
        "natal_moon": {"sign": moon_sign, "nakshatra": moon_nak},
        # Public daily context used only to explain the already-computed
        # activated house/significator. No second prediction is calculated.
        "lagna": lagna,
        "natal_planets": {
            str(k): {
                "sign": (v or {}).get("sign", ""),
                "house": (v or {}).get("house", ""),
                "dignity": (v or {}).get("dignity", ""),
            }
            for k, v in (pc.get("planets") or {}).items()
        },
        "gochar": {
            "moon": {"auspicious": moon_aus, "inauspicious": moon_inaus},
            "sun": {"auspicious": sun_aus, "inauspicious": sun_inaus},
            "mercury": {"auspicious": merc_aus, "inauspicious": merc_inaus},
        },
        "ashtakavarga": {
            "moon": {"sav": moon_sav, "bav": moon_bav, "sav_line": sav_line, "bav_line": bav_line},
            "sun": {"sav": sun_sav, "bav": sun_bav},
            "mercury": {"sav": merc_sav, "bav": merc_bav},
            "dasha_lords": lord_av,
        },
        "slow_planet_notes": slow_notes[:5],
        "sun_narrative": sun_line,
        "mercury_narrative": merc_line,
        "dasha": {
            "md": md_lord,
            "ad": ad_lord,
            "pd": pd_lord,
            "stack": dasha_active.get("stack", ""),
            "pd_start": dasha_active.get("pd_start", ""),
            "pd_end": dasha_active.get("pd_end", ""),
            "note": dasha_note,
        },
        "jaimini": vedic.get("jaimini", {}),
        "vedic_confluence": vedic,
        "lucky_numbers": lucky_nums,
        "lucky_colors": lucky_cols,
        "dos": dos,
        "donts": donts,
        "dos_donts_intro": dos_donts_intro,
        "moonology": moonology,
        "muhurat": muhurat,
        "sources": [
            "Tarabala/Chandrabal (classical panchang)",
            "Bhardwaj gochar tables (bhardwaj_book_data.json)",
            "Bhardwaj nakshatra_effects (transit star)",
            "Ashtakavarga SAV/BAV (rules10)",
            "Ashtakavarga bindus on the transit signs of the running dasha lords (rules10 x Vimshottari)",
            "GK transit+dasha pairing incl. Vim/Jaimini pratyantar (rules11)",
            "D9 dignity cross-check on period lords (rules45)",
            "Jaimini Chara karakas + SAV on dasha signs (rules6/rules10)",
            "Numerology lucky series (rules23/Woods)",
            "Planet-day colours (rules40/41 GEM_DATA)",
            "Moonology Daily Moon + phase (rules44/Boland, sidereal-aligned)",
            "Muhurat day + event election (rules37 + PyJHora choghadiya/Abhijit/Rahu Kaal/Hora)",
        ],
        "meta": {
            "lagna": lagna,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
        },
    }


def _opening_paragraph(
    client: str,
    target: date,
    tone: str,
    moon_t: dict,
    tara: str,
    chandra: str,
    theme: str,
    md: str,
    ad: str,
    pd: str,
    verdict: str,
    jaimini: dict | None = None,
) -> str:
    tone_word = {
        "bright": "a genuinely supportive",
        "mixed-positive": "a quietly promising",
        "steady": "a balanced, workmanlike",
        "mixed-caution": "a mixed-signal",
        "sensitive": "a emotionally thin",
    }.get(tone, "a nuanced")
    vim_stack = "-".join(x for x in (md, ad, pd) if x)
    pd_clause = f", Vim {pd} pratyantar" if pd else ""
    jai = jaimini or {}
    jai_stack = jai.get("stack", "")
    jai_clause = f" Jaimini Chara {jai_stack}." if jai_stack else ""
    return (
        f"{client}, {target.strftime('%A %d %B %Y')} opens with {tone_word} day climate. "
        f"Vimshottari {vim_stack}{pd_clause}.{jai_clause} "
        f"Transit Moon in {moon_t['sign']} ({moon_t['nakshatra']} pada {moon_t['pada']}) "
        f"activates {theme} as the {moon_t['house_from_moon']}th house from your birth Moon. "
        f"Tarabala is {tara}; Chandrabal is {chandra}. "
        f"{verdict.capitalize() if verdict else 'See Vedic confluence below for the full weave.'}"
    )


compute_daily_prediction = compute_daily_moon_guide


def load_pc_for_session(session_dir: Path) -> dict:
    manifest = session_dir / "session_manifest.json"
    if manifest.is_file():
        m = json.loads(manifest.read_text(encoding="utf-8"))
        rel = m.get("precomputed_json", "")
        if rel:
            p = BASE_DIR / rel
            if p.is_file():
                return json.loads(p.read_text(encoding="utf-8"))
    for p in sorted(session_dir.glob("input/*_precomputed.json")):
        return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError("No precomputed chart JSON for session")


def compute_from_session(
    session_dir: Path,
    target: date | None = None,
) -> dict[str, Any]:
    pc = load_pc_for_session(session_dir)
    return compute_daily_moon_guide(pc, target)
