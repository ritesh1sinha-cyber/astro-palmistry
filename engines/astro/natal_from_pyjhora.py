#!/usr/bin/env python3
"""
natal_from_pyjhora.py - Birth data to precomputed JSON via PyJHora (Swiss Ephemeris).

Replaces AstroSage PDF extract for core chart facts: D1, divisional signs,
Ashtakavarga, Vimshottari. Output matches astro_precompute.py schema.

Usage:
  python3 natal_from_pyjhora.py --name "Aditi Shipra" --dob 1989-07-29 \\
      --time 00:05:00 --lat 25.6 --lon 85.117 --tz 5.5 --place Patna \\
      -o Aditi_Shipra_precomputed_pyjhora.json \\
      --diff _astro_sessions/.../Aditi_Shipra_precomputed.json

Requires PyJHora source (default: pyjhora/src in workspace) and:
  pip install pyswisseph numpy geocoder geopy timezonefinder
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from astro_precompute import (
    NAK_SPAN,
    NAK_TO_DASHA_LORD,
    SIGNS,
    VIMSH_YEARS,
    degree_to_nakshatra,
    house_from_lagna,
    parse_extract,
    precompute_from_chart,
)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PYJHORA_SRC = BASE_DIR / "pyjhora" / "src"

PJ_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
DIV_FACTORS = {
    "D1": 1, "D2": 2, "D3": 3, "D4": 4, "D5": 5, "D6": 6,
    "D7": 7, "D8": 8, "D9": 9, "D10": 10, "D11": 11, "D12": 12, "D16": 16, "D20": 20,
    "D24": 24, "D27": 27, "D30": 30, "D40": 40, "D45": 45, "D60": 60,
}


@dataclass
class BirthInput:
    client_name: str
    dob: str  # YYYY-MM-DD
    birth_time: str  # HH:MM:SS or HH:MM
    latitude: float
    longitude: float
    timezone: float
    place_name: str = ""
    ayanamsa: str = "LAHIRI"
    gender: int = 0  # 0=male, 1=female (Chara dasha)
    true_nodes: bool = False
    effective_time: str | None = None
    lmt_correction: str | None = None  # AstroSage-style HH.MM.SS added to clock time


def _ensure_pyjhora(src: Path | None = None) -> Path:
    src = src or Path(os.environ.get("PYJHORA_SRC", DEFAULT_PYJHORA_SRC))
    if not src.is_dir():
        raise FileNotFoundError(
            f"PyJHora source not found at {src}. "
            "Copy PyJHora to pyjhora/ in the workspace or set PYJHORA_SRC."
        )
    s = str(src)
    if s not in sys.path:
        sys.path.insert(0, s)
    return src


def _parse_hms(text: str) -> tuple[int, int, int]:
    text = text.strip().replace(".", ":")
    parts = [int(p) for p in re.split(r"[:]", text)]
    while len(parts) < 3:
        parts.append(0)
    return parts[0], parts[1], parts[2]


def _effective_tob(inp: BirthInput) -> tuple[int, int, int]:
    if inp.effective_time:
        return _parse_hms(inp.effective_time)
    h, m, s = _parse_hms(inp.birth_time)
    if inp.lmt_correction:
        ch, cm, cs = _parse_hms(inp.lmt_correction)
        base = datetime(2000, 1, 1, h, m, s) + timedelta(hours=ch, minutes=cm, seconds=cs)
        return base.hour, base.minute, base.second
    return h, m, s


def _parse_pj_date(text: str) -> date:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text or "")
    if not m:
        raise ValueError(f"Cannot parse date from {text!r}")
    return date.fromisoformat(m.group(1))


def _nak_from_longitude(sign_idx: int, deg_in_sign: float) -> dict:
    abs_deg = sign_idx * 30.0 + deg_in_sign
    info = degree_to_nakshatra(abs_deg)
    info["degree_in_nakshatra"] = round(abs_deg % NAK_SPAN, 4)
    if info.get("nakshatra"):
        info["dasha_lord_from_nak"] = NAK_TO_DASHA_LORD.get(info["nakshatra"])
    return info


def _body_from_position(sign_idx: int, deg_in_sign: float, *, retro: bool = False) -> dict:
    nak = _nak_from_longitude(sign_idx, deg_in_sign)
    out = {
        "sign": SIGNS[sign_idx],
        "degree_in_sign": round(deg_in_sign, 4),
        "nakshatra": nak.get("nakshatra"),
        "pada": nak.get("pada"),
    }
    if retro:
        out["retrograde"] = True
    return out


def _vimshottari_from_pyjhora(jd: float, place, pj) -> dict:
    """Convert PyJHora vimshottari tables ? astro_precompute vimshottari block."""
    from jhora.horoscope.chart import house as pj_house
    from jhora.horoscope.dhasa.graha import vimsottari

    today = date.today()
    planet_list = pj_house.planet_list

    _, md_rows = vimsottari.get_vimsottari_dhasa_bhukthi(
        jd, place, dhasa_level_index=1,
    )
    _, ad_rows = vimsottari.get_vimsottari_dhasa_bhukthi(
        jd, place, dhasa_level_index=2,
    )

    sequence = []
    for i, row in enumerate(md_rows):
        lord = planet_list[row[0]]
        start = _parse_pj_date(row[1])
        end = _parse_pj_date(md_rows[i + 1][1]) if i + 1 < len(md_rows) else start
        yrs = round((end - start).days / 365.25, 2) if end > start else float(VIMSH_YEARS.get(lord, 0))
        sequence.append({
            "md_lord": lord,
            "md_years": yrs,
            "start": str(start),
            "end": str(end),
            "status": "past" if end < today else ("current" if start <= today <= end else "future"),
        })

    current_md = next((m for m in sequence if m["status"] == "current"), sequence[-1] if sequence else {})
    md_lord = current_md.get("md_lord", "")
    md_id = planet_list.index(md_lord) if md_lord in planet_list else 0
    md_end = date.fromisoformat(str(current_md.get("end", ""))[:10]) if current_md.get("end") else None

    ads = []
    md_ads = [r for r in ad_rows if r[0] == md_id]
    for j, row in enumerate(md_ads):
        ad_lord = planet_list[row[1]]
        start = _parse_pj_date(row[2])
        if j + 1 < len(md_ads):
            end = _parse_pj_date(md_ads[j + 1][2])
        elif md_end:
            end = md_end
        else:
            end = start
        if md_end and end > md_end:
            end = md_end
        ad_yrs = round((end - start).days / 365.25, 2) if end > start else 0
        ads.append({
            "ad_lord": ad_lord,
            "start": str(start),
            "end": str(end),
            "status": "past" if end < today else ("current" if start <= today <= end else "future"),
            "ad_years": ad_yrs,
        })

    return {
        "sequence": sequence,
        "current_md": current_md,
        "current_md_antardashas": ads,
        "source": "pyjhora",
        "llm_note_md": (
            f"PyJHora Vimshottari (ayanamsa via drik.set_ayanamsa_mode). "
            f"Current MD = {md_lord} ({current_md.get('start')}  {current_md.get('end')})."
        ),
        "llm_note_ad": "Antardasha rows computed from PyJHora level-2 table for current mahadasha.",
    }


# Event vargas (D4-D60) + ultra-fine rectification micro-charts (D81/D108/D144).
# The latter change lagna within ~1 minute of birth time, so they serve only as
# the final tie-break inside the D60 (~2 min) slot — see btr_rectify.py.
BTR_DIV_FACTORS = {
    "D4": 4, "D7": 7, "D9": 9, "D10": 10, "D24": 24, "D60": 60,
    "D81": 81, "D108": 108, "D144": 144,
}


def compute_chart_btr(
    inp: BirthInput,
    *,
    pyjhora_src: Path | None = None,
    extra_vargas: dict[str, int] | None = None,
) -> dict:
    """Lightweight chart for BTR scanning (D1 + event vargas + Vimshottari only).

    ``extra_vargas`` lets a caller (e.g. the event predictor) request additional
    divisional charts (e.g. D6/D8/D11) for promise checks without changing the
    per-candidate cost of the rectification scan, which omits them.
    """
    _ensure_pyjhora(pyjhora_src)
    from jhora.panchanga import drik
    from jhora import utils
    from jhora.horoscope.chart import charts
    from jhora.horoscope.chart import house as pj_house

    drik.set_ayanamsa_mode(inp.ayanamsa)

    dob_parts = tuple(int(x) for x in inp.dob.split("-"))
    tob = _effective_tob(inp)
    place = drik.Place(inp.place_name or "BirthPlace", inp.latitude, inp.longitude, inp.timezone)
    jd = utils.julian_day_number(dob_parts, tob)

    pp = charts.rasi_chart(jd, place)
    retro_ids = set(drik.planets_in_retrograde(jd, place) or [])

    lagna_si, lagna_deg = pp[0][1]
    lagna = _body_from_position(lagna_si, lagna_deg)
    lagna["degree_in_sign"] = round(lagna_deg, 4)

    planets: dict[str, dict] = {}
    for entry in pp[1:]:
        pid = entry[0]
        if not isinstance(pid, int) or pid < 0 or pid >= len(PJ_PLANETS):
            continue
        name = PJ_PLANETS[pid]
        si, deg = entry[1]
        body = _body_from_position(si, deg, retro=(pid in retro_ids))
        body["house"] = house_from_lagna(body["sign"], lagna["sign"])
        if name == "Moon":
            body["nakshatra_pada"] = body.get("pada")
            body["degree_in_nakshatra"] = _nak_from_longitude(si, deg).get("degree_in_nakshatra")
            body["dasha_lord_from_nak"] = NAK_TO_DASHA_LORD.get(body.get("nakshatra", ""), "")
        planets[name] = body

    divisional: dict[str, dict] = {}
    factors = {**BTR_DIV_FACTORS, **(extra_vargas or {})}
    for label, factor in factors.items():
        dpp = charts.divisional_chart(jd, place, divisional_chart_factor=factor)
        div_map: dict[str, str] = {}
        for entry in dpp:
            pid = entry[0]
            if pid == "L":
                div_map["Lagna"] = SIGNS[entry[1][0]]
            elif isinstance(pid, int) and pid < len(PJ_PLANETS):
                div_map[PJ_PLANETS[pid]] = SIGNS[entry[1][0]]
        divisional[label] = div_map

    vimsh = _vimshottari_from_pyjhora(jd, place, pj_house)
    h, m, s = tob
    return {
        "lagna": lagna,
        "planets": planets,
        "divisional": divisional,
        "vimshottari": vimsh,
        "birth_place": inp.place_name,
        "birth_time": f"{h:02d}:{m:02d}:{s:02d}",
        "ayanamsa": inp.ayanamsa,
        "gender": inp.gender,
    }


def compute_chart_parsed(inp: BirthInput, *, pyjhora_src: Path | None = None) -> dict:
    """Run PyJHora and return parse_extract-shaped dict (+ extras)."""
    _ensure_pyjhora(pyjhora_src)
    from jhora.panchanga import drik
    from jhora import utils
    from jhora.horoscope.chart import charts, ashtakavarga
    from jhora.horoscope.chart import house as pj_house

    drik.set_ayanamsa_mode(inp.ayanamsa)
    if hasattr(drik, "set_planet_list"):
        try:
            import jhora.const as pj_const
            pj_const.use_rahu_ketu_as_true_nodes = inp.true_nodes
        except Exception:
            pass

    dob_parts = tuple(int(x) for x in inp.dob.split("-"))
    tob = _effective_tob(inp)
    place = drik.Place(inp.place_name or "BirthPlace", inp.latitude, inp.longitude, inp.timezone)
    jd = utils.julian_day_number(dob_parts, tob)

    pp = charts.rasi_chart(jd, place)
    retro_ids = set(drik.planets_in_retrograde(jd, place) or [])

    lagna_si, lagna_deg = pp[0][1]
    lagna = _body_from_position(lagna_si, lagna_deg)
    lagna["degree_in_sign"] = round(lagna_deg, 4)

    planets: dict[str, dict] = {}
    for entry in pp[1:]:
        pid = entry[0]
        if not isinstance(pid, int) or pid < 0 or pid >= len(PJ_PLANETS):
            continue
        name = PJ_PLANETS[pid]
        si, deg = entry[1]
        body = _body_from_position(si, deg, retro=(pid in retro_ids))
        body["house"] = house_from_lagna(body["sign"], lagna["sign"])
        if name == "Moon":
            body["nakshatra_pada"] = body.get("pada")
            body["degree_in_nakshatra"] = _nak_from_longitude(si, deg).get("degree_in_nakshatra")
            body["dasha_lord_from_nak"] = NAK_TO_DASHA_LORD.get(body.get("nakshatra", ""), "")
        planets[name] = body

    # Divisional signs (D9/D10 + common vargas)
    divisional: dict[str, dict] = {}
    for label, factor in DIV_FACTORS.items():
        if factor == 1:
            continue
        dpp = charts.divisional_chart(jd, place, divisional_chart_factor=factor)
        div_map: dict[str, str] = {}
        for entry in dpp:
            pid = entry[0]
            if pid == "L":
                div_map["Lagna"] = SIGNS[entry[1][0]]
            elif isinstance(pid, int) and pid < len(PJ_PLANETS):
                div_map[PJ_PLANETS[pid]] = SIGNS[entry[1][0]]
        divisional[label] = div_map
        if label == "D9":
            for pname, sign in div_map.items():
                if pname in planets:
                    planets[pname]["navamsha_sign"] = sign

    # Ashtakavarga
    htp = utils.get_house_planet_list_from_planet_positions(pp)
    bav_rows, sav, _pra = ashtakavarga.get_ashtaka_varga(htp)
    bav = {PJ_PLANETS[i]: bav_rows[i] for i in range(7)}
    ashtakavarga_block = {
        "sav": sav,
        "sav_total": sum(sav),
        "bav": bav,
        "source": "pyjhora",
    }

    vimsh = _vimshottari_from_pyjhora(jd, place, pj_house)

    from jaimini_chara_dasha import compute_chara_dasha
    chara_dasha = compute_chara_dasha(
        inp.dob, inp.birth_time,
        inp.latitude, inp.longitude, inp.timezone,
        gender=inp.gender,
        place_name=inp.place_name,
        ayanamsa=inp.ayanamsa,
        pyjhora_src=str(pyjhora_src) if pyjhora_src else None,
    )

    from kp_from_pyjhora import compute_kp_block
    kp_block = compute_kp_block(inp, pyjhora_src=pyjhora_src)

    h, m, s = tob
    return {
        "lagna": lagna,
        "planets": planets,
        "divisional": divisional,
        "ashtakavarga": ashtakavarga_block,
        "vimshottari": vimsh,
        "chara_dasha": chara_dasha,
        "kp": kp_block,
        "birth_place": inp.place_name,
        "birth_time": f"{h:02d}:{m:02d}:{s:02d}",
        "ayanamsa": inp.ayanamsa,
        "gender": inp.gender,
        "raw_sections": {
            "engine": "PyJHora",
            "julian_day": jd,
            "latitude": inp.latitude,
            "longitude": inp.longitude,
            "timezone": inp.timezone,
        },
    }


def precompute_from_pyjhora(inp: BirthInput, *, pyjhora_src: Path | None = None) -> dict:
    parsed = compute_chart_parsed(inp, pyjhora_src=pyjhora_src)
    return precompute_from_chart(parsed, inp.client_name, inp.dob, source="pyjhora")


def diff_precompute(
    pyjhora_pc: dict,
    reference_pc: dict,
    *,
    degree_tol: float = 0.5,
) -> dict:
    """Compare PyJHora precompute vs AstroSage/extract precompute."""
    report: dict[str, Any] = {"ok": True, "checks": [], "warnings": []}

    def add_check(name: str, ok: bool, detail: str):
        report["checks"].append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            report["ok"] = False

    def add_warn(detail: str):
        report["warnings"].append(detail)

    rmeta, pmeta = reference_pc.get("meta", {}), pyjhora_pc.get("meta", {})
    add_check(
        "lagna_sign",
        rmeta.get("lagna_sign") == pmeta.get("lagna_sign"),
        f"ref={rmeta.get('lagna_sign')} pyjhora={pmeta.get('lagna_sign')}",
    )

    ref_planets = reference_pc.get("planets", {})
    pj_planets = pyjhora_pc.get("planets", {})
    for pname in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        ref, pj = ref_planets.get(pname, {}), pj_planets.get(pname, {})
        if not ref:
            continue
        sign_ok = ref.get("sign") == pj.get("sign")
        deg_diff = abs(ref.get("degree_in_sign", 0) - pj.get("degree_in_sign", 0))
        deg_ok = deg_diff <= degree_tol
        add_check(
            f"{pname}_sign",
            sign_ok,
            f"ref={ref.get('sign')} pyjhora={pj.get('sign')}",
        )
        if sign_ok:
            add_check(
                f"{pname}_degree",
                deg_ok,
                f"delta={deg_diff:.2f} ref={ref.get('degree_in_sign')} pyjhora={pj.get('degree_in_sign')}",
            )

    ref_sav = reference_pc.get("ashtakavarga", {}).get("sav_total")
    pj_sav = pyjhora_pc.get("ashtakavarga", {}).get("sav_total")
    if ref_sav is None:
        pj_bav = pyjhora_pc.get("ashtakavarga", {}).get("bav", {})
        if pj_bav:
            add_warn("Reference has no ashtakavarga block  compare SAV manually from extract.")
    else:
        add_check("sav_total", ref_sav == pj_sav, f"ref={ref_sav} pyjhora={pj_sav}")

    ref_md = reference_pc.get("vimshottari", {}).get("current_md", {})
    pj_md = pyjhora_pc.get("vimshottari", {}).get("current_md", {})
    add_check(
        "current_md_lord",
        ref_md.get("md_lord") == pj_md.get("md_lord"),
        f"ref={ref_md.get('md_lord')} pyjhora={pj_md.get('md_lord')}",
    )

    ref_ad = next(
        (a for a in reference_pc.get("vimshottari", {}).get("current_md_antardashas", [])
         if a.get("status") == "current"),
        {},
    )
    pj_ad = next(
        (a for a in pyjhora_pc.get("vimshottari", {}).get("current_md_antardashas", [])
         if a.get("status") == "current"),
        {},
    )
    if ref_ad:
        add_check(
            "current_ad_lord",
            ref_ad.get("ad_lord") == pj_ad.get("ad_lord"),
            f"ref={ref_ad.get('ad_lord')} pyjhora={pj_ad.get('ad_lord')}",
        )

    ref_d9 = {p: ref_planets.get(p, {}).get("navamsha_sign") for p in ref_planets}
    pj_d9 = pyjhora_pc.get("divisional", {}).get("D9", {})
    for pname, rs in ref_d9.items():
        if rs and rs != "?":
            add_check(
                f"D9_{pname}",
                rs == pj_d9.get(pname),
                f"ref={rs} pyjhora={pj_d9.get(pname)}",
            )

    for varga in ("D7", "D10", "D30", "D60"):
        ref_v = reference_pc.get("divisional", {}).get(varga, {})
        pj_v = pyjhora_pc.get("divisional", {}).get(varga, {})
        if not ref_v and not pj_v:
            continue
        for pname in ["Lagna", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
            rs, ps = ref_v.get(pname), pj_v.get(pname)
            if rs and ps:
                add_check(f"{varga}_{pname}", rs == ps, f"ref={rs} pyjhora={ps}")

    ref_jm = reference_pc.get("jaimini", {})
    pj_jm = pyjhora_pc.get("jaimini", {})
    if ref_jm and pj_jm:
        add_check(
            "jaimini_atmakaraka",
            ref_jm.get("atmakaraka") == pj_jm.get("atmakaraka"),
            f"ref={ref_jm.get('atmakaraka')} pyjhora={pj_jm.get('atmakaraka')}",
        )
        add_check(
            "jaimini_karakamsa",
            ref_jm.get("karakamsa_sign") == pj_jm.get("karakamsa_sign"),
            f"ref={ref_jm.get('karakamsa_sign')} pyjhora={pj_jm.get('karakamsa_sign')}",
        )
        add_check(
            "jaimini_swamsa",
            ref_jm.get("swamsa_sign") == pj_jm.get("swamsa_sign"),
            f"ref={ref_jm.get('swamsa_sign')} pyjhora={pj_jm.get('swamsa_sign')}",
        )

    return report


def diff_against_extract(pyjhora_pc: dict, extracted_path: str, degree_tol: float = 0.5) -> dict:
    text = Path(extracted_path).read_text(encoding="utf-8", errors="ignore")
    parsed = parse_extract(text)
    ref = precompute_from_chart(
        {**parsed, "raw_sections": {"extract_path": extracted_path}},
        pyjhora_pc.get("meta", {}).get("client", "Client"),
        pyjhora_pc.get("meta", {}).get("dob", "2000-01-01"),
        source="astrosage_extract",
    )
    return diff_precompute(pyjhora_pc, ref, degree_tol=degree_tol)


def _print_diff(report: dict) -> None:
    status = "PASS" if report.get("ok") else "DIFFS FOUND"
    print(f"\n=== Validation: {status} ===")
    for c in report.get("checks", []):
        mark = "OK" if c["ok"] else "FAIL"
        print(f"  {mark} {c['name']}: {c['detail']}")
    for w in report.get("warnings", []):
        print(f"  ! {w}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Birth data to precomputed JSON via PyJHora")
    ap.add_argument("--name", required=True)
    ap.add_argument("--dob", required=True, help="YYYY-MM-DD")
    ap.add_argument("--time", required=True, help="HH:MM:SS birth clock time")
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--tz", type=float, required=True, help="Timezone offset, e.g. 5.5 for IST")
    ap.add_argument("--place", default="", help="Place label")
    ap.add_argument("--ayanamsa", default="LAHIRI")
    ap.add_argument("--gender", type=int, choices=[0, 1], default=0, help="0=male 1=female (Chara dasha)")
    ap.add_argument("--true-nodes", action="store_true")
    ap.add_argument("--effective-time", help="Override clock time (HH:MM:SS)")
    ap.add_argument("--lmt-correction", help="Add AstroSage LMT correction HH.MM.SS to --time")
    ap.add_argument("-o", "--output", help="Write precomputed JSON here")
    ap.add_argument("--diff", help="Reference precomputed JSON to compare")
    ap.add_argument("--extract", help="AstroSage extracted.txt to compare (alternative to --diff)")
    ap.add_argument("--degree-tol", type=float, default=0.5)
    ap.add_argument("--pyjhora-src", help="Path to PyJHora src/jhora parent (src folder)")
    args = ap.parse_args()

    inp = BirthInput(
        client_name=args.name,
        dob=args.dob,
        birth_time=args.time,
        latitude=args.lat,
        longitude=args.lon,
        timezone=args.tz,
        place_name=args.place,
        ayanamsa=args.ayanamsa,
        true_nodes=args.true_nodes,
        effective_time=args.effective_time,
        lmt_correction=args.lmt_correction,
        gender=args.gender,
    )
    src = Path(args.pyjhora_src) if args.pyjhora_src else None

    print(f"Computing chart via PyJHora for {inp.client_name} ({inp.dob} {inp.birth_time})...")
    pc = precompute_from_pyjhora(inp, pyjhora_src=src)

    out = args.output or f"{inp.client_name.replace(' ', '_')}_precomputed_pyjhora.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(pc, f, indent=2, default=str)
    print(f"Written -> {out}")
    print(f"Lagna: {pc['meta']['lagna_sign']} | SAV total: {pc.get('ashtakavarga', {}).get('sav_total', '?')}")
    md = pc.get("vimshottari", {}).get("current_md", {})
    ad = next((a for a in pc.get("vimshottari", {}).get("current_md_antardashas", []) if a.get("status") == "current"), {})
    print(f"Dasha: {md.get('md_lord')} MD  {ad.get('ad_lord')} AD")

    if args.diff:
        ref = json.loads(Path(args.diff).read_text(encoding="utf-8"))
        _print_diff(diff_precompute(pc, ref, degree_tol=args.degree_tol))
    if args.extract:
        _print_diff(diff_against_extract(pc, args.extract, degree_tol=args.degree_tol))


if __name__ == "__main__":
    main()
