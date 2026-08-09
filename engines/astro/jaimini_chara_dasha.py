"""
jaimini_chara_dasha.py - Chara (Jaimini) dasha via PyJHora.

Uses K.N. Rao method (chara_method=2) with rotated antardasha order
(AstroSage / standard Jaimini: first antar = next sign after maha lord).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional

from astro_precompute import SIGNS

PJ_SIGN = {s: i for i, s in enumerate(SIGNS)}


def _jd_to_date(jd_str: str) -> date:
    return date.fromisoformat(jd_str[:10])


def _add_years(start: date, years: float) -> date:
    days = int(round(years * 365.25636))
    return start + timedelta(days=days)


def compute_chara_dasha(
    dob: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    timezone: float,
    *,
    gender: int = 0,
    chara_method: int = 2,
    place_name: str = "BirthPlace",
    ayanamsa: str = "LAHIRI",
    pyjhora_src: str | None = None,
) -> dict[str, Any]:
    """
    Compute Chara maha + antar tables from PyJHora.

    Returns:
      maha: [{sign, years, start, end}, ...]
      antar: [{sign, start, end, maha_sign?}, ...]  (flat chronological)
    """
    import os
    import re
    import sys
    from pathlib import Path

    src = Path(pyjhora_src or os.environ.get("PYJHORA_SRC", Path(__file__).parent / "pyjhora" / "src"))
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from jhora.panchanga import drik
    from jhora.horoscope.chart import charts
    from jhora.horoscope.dhasa.raasi import chara
    from jhora import const, utils as pj_utils

    def _parse_hms(text: str) -> tuple[int, int, int]:
        text = text.strip().replace(".", ":")
        parts = [int(p) for p in re.split(r"[:]", text)]
        while len(parts) < 3:
            parts.append(0)
        return parts[0], parts[1], parts[2]

    h, m, s = _parse_hms(birth_time)
    y, mo, d = [int(x) for x in dob.split("-")]
    dob_tuple = (y, mo, d)
    tob_tuple = (h, m, s)

    drik.set_ayanamsa_mode(ayanamsa)
    place = drik.Place(place_name or "BirthPlace", latitude, longitude, timezone)
    jd = pj_utils.julian_day_number(dob_tuple, tob_tuple)
    pp = charts.rasi_chart(jd, place)[: const._pp_count_upto_ketu]

    if chara_method == 2:
        progression = chara._dhasa_progression_knrao_method(pp)
        duration_func = chara._dhasa_duration_knrao_method
        antar_method = 1  # rotate: first antar = sign after maha lord
    elif chara_method == 1:
        progression = chara._dhasa_progression_pvnrao_method(pp)
        duration_func = chara._dhasa_duration_pvnrao_method
        antar_method = 1
    else:
        rows = chara.get_dhasa_antardhasa(
            dob_tuple, tob_tuple, place,
            chara_method=chara_method, gender=gender,
            dhasa_level_index=2,
        )
        return _rows_to_maha_antar(rows)

    bhukthis = chara._antardhasa(progression, method=antar_method)
    one_year = const.sidereal_year

    maha: list[dict] = []
    antar: list[dict] = []
    jd_cur = float(jd)
    # One 12-sign pass is not a lifetime — short Chara years (this 1955 chart
    # ended ~2023) leave older natives without a current maha. Keep cycling
    # the same progression until we cover ~120 years from birth.
    jd_limit = float(jd) + 120.0 * one_year
    guard = 0
    while jd_cur < jd_limit and guard < 36:
        guard += 1
        for lord_idx in progression:
            years = float(duration_func(pp, lord_idx))
            jd_m_start = jd_cur
            ddb = years / 12.0
            jd_a = jd_m_start
            maha_sign = SIGNS[lord_idx]

            for bh_idx in bhukthis:
                start_str = pj_utils.julian_day_to_date_time_string(jd_a)
                antar.append({
                    "maha_sign": maha_sign,
                    "sign": SIGNS[bh_idx],
                    "start": _jd_to_date(start_str),
                    "years": round(ddb, 4),
                })
                jd_a += ddb * one_year

            m_start = _jd_to_date(pj_utils.julian_day_to_date_time_string(jd_m_start))
            m_end = _jd_to_date(pj_utils.julian_day_to_date_time_string(jd_cur + years * one_year))
            maha.append({
                "sign": maha_sign,
                "years": int(years) if years == int(years) else round(years, 2),
                "start": m_start,
                "end": m_end,
            })
            jd_cur += years * one_year
            if jd_cur >= jd_limit:
                break

    for i, row in enumerate(antar):
        row["end"] = antar[i + 1]["start"] if i + 1 < len(antar) else _add_years(row["start"], row.get("years", 1))

    return {
        "engine": "pyjhora",
        "chara_method": chara_method,
        "gender": gender,
        "maha": maha,
        "antar": antar,
        "current_maha": _current(maha),
        "current_antar": _current(antar),
    }


def _rows_to_maha_antar(rows: list) -> dict[str, Any]:
    """Convert PyJHora get_dhasa_antardhasa rows to report schema."""
    maha: list[dict] = []
    antar: list[dict] = []
    seen_maha: set[int] = set()

    for r in rows:
        if len(r) == 3:
            lord, start_str, yrs = r
            if lord in seen_maha:
                continue
            seen_maha.add(lord)
            maha.append({
                "sign": SIGNS[lord],
                "years": yrs,
                "start": _jd_to_date(start_str),
                "end": None,
            })
        elif len(r) >= 4:
            lord, bh, start_str, yrs = r[0], r[1], r[2], r[3]
            antar.append({
                "maha_sign": SIGNS[lord],
                "sign": SIGNS[bh],
                "start": _jd_to_date(start_str),
                "years": yrs,
                "end": None,
            })

    for i, m in enumerate(maha):
        m["end"] = maha[i + 1]["start"] if i + 1 < len(maha) else _add_years(m["start"], float(m["years"]))
    for i, a in enumerate(antar):
        a["end"] = antar[i + 1]["start"] if i + 1 < len(antar) else _add_years(a["start"], float(a.get("years", 1)))

    return {
        "engine": "pyjhora",
        "maha": maha,
        "antar": antar,
        "current_maha": _current(maha),
        "current_antar": _current(antar),
    }


def _current(periods: list[dict]) -> dict | None:
    today = date.today()
    for p in periods:
        try:
            start = _as_date(p.get("start"))
            end = _as_date(p.get("end"))
        except Exception:  # noqa: BLE001
            continue
        if start <= today < end:
            return p
    return None


def _as_date(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def _iso(d: date | str) -> str:
    return d.isoformat() if isinstance(d, date) else str(d)[:10]


def chara_covers(block: dict | None, when: date) -> bool:
    for m in (block or {}).get("maha") or []:
        try:
            a, b = _as_date(m.get("start")), _as_date(m.get("end"))
        except Exception:  # noqa: BLE001
            continue
        if a <= when <= b:
            return True
    return False


def extend_chara_block(block: dict, until: date) -> dict:
    """Repeat the first 12-sign cycle until `until` falls inside a maha.

    Used when older precomputes only stored one Chara pass (~60–80 years for
    short-year charts) and the person is already past the last listed maha.
    """
    maha = [dict(m) for m in (block.get("maha") or [])]
    antar = [dict(a) for a in (block.get("antar") or [])]
    if len(maha) < 12:
        return block
    try:
        if _as_date(maha[-1]["end"]) > until:
            return block
    except Exception:  # noqa: BLE001
        return block

    template = [{"sign": m["sign"], "years": float(m.get("years") or 1)}
                for m in maha[:12]]
    bh_by_maha: dict[str, list[str]] = {}
    for a in antar:
        ms = a.get("maha_sign") or ""
        if not ms:
            continue
        bh_by_maha.setdefault(ms, [])
        if len(bh_by_maha[ms]) < 12 and a.get("sign"):
            bh_by_maha[ms].append(a["sign"])
    default_bh = [t["sign"] for t in template]

    guard = 0
    while _as_date(maha[-1]["end"]) <= until and guard < 24:
        guard += 1
        for t in template:
            start = _as_date(maha[-1]["end"])
            years = float(t["years"])
            end = _add_years(start, years)
            yrs_out: Any = int(years) if years == int(years) else round(years, 2)
            maha.append({
                "sign": t["sign"], "years": yrs_out,
                "start": _iso(start), "end": _iso(end),
            })
            bh = bh_by_maha.get(t["sign"]) or default_bh
            total_days = max((end - start).days, 1)
            for i, bs in enumerate(bh[:12]):
                a_start = start + timedelta(days=round(total_days * i / 12.0))
                a_end = end if i == 11 else start + timedelta(
                    days=round(total_days * (i + 1) / 12.0))
                antar.append({
                    "maha_sign": t["sign"], "sign": bs,
                    "start": _iso(a_start), "end": _iso(a_end),
                    "years": round(years / 12.0, 4),
                })

    out = dict(block)
    out["maha"] = maha
    out["antar"] = antar
    # stamp currents with date objects for _current, then leave JSON-friendly
    stamped = [{**m, "start": _as_date(m["start"]), "end": _as_date(m["end"])}
               for m in maha]
    stamped_a = [{**a, "start": _as_date(a["start"]), "end": _as_date(a["end"])}
                 for a in antar]
    cm, ca = _current(stamped), _current(stamped_a)
    out["current_maha"] = (
        {**cm, "start": _iso(cm["start"]), "end": _iso(cm["end"])} if cm else None)
    out["current_antar"] = (
        {**ca, "start": _iso(ca["start"]), "end": _iso(ca["end"])} if ca else None)
    out["extended"] = True
    return out


def ensure_chara_covers(pc: dict, when: Optional[date] = None) -> dict:
    """Return a Chara block that includes `when`, extending in place if needed."""
    when = when or date.today()
    block = get_chara_dasha(pc)
    if not block.get("maha"):
        return block
    if chara_covers(block, when):
        return block
    # Cover a few years past `when` so near-future windows also resolve.
    extended = extend_chara_block(block, when + timedelta(days=365 * 5))
    if extended.get("maha"):
        pc["chara_dasha"] = extended
        pc.setdefault("jaimini", {})["chara_dasha"] = extended
    return extended


def get_chara_dasha(pc: dict | None) -> dict[str, Any]:
    """Return the Chara dasha block from a precompute dict (top-level or jaimini nest)."""
    if not pc:
        return {}
    top = pc.get("chara_dasha") if isinstance(pc.get("chara_dasha"), dict) else {}
    nested = (pc.get("jaimini") or {}).get("chara_dasha")
    nested = nested if isinstance(nested, dict) else {}
    if top.get("maha"):
        return top
    if nested.get("maha"):
        return nested
    return top or nested or {}


def sync_chara_dasha_keys(pc: dict) -> None:
    """Mirror Chara dasha to both pc['chara_dasha'] and pc['jaimini']['chara_dasha']."""
    block = get_chara_dasha(pc)
    if not block.get("maha"):
        return
    pc["chara_dasha"] = block
    pc.setdefault("jaimini", {})["chara_dasha"] = block


def chara_dasha_from_precompute(pc: dict) -> tuple[list[dict], list[dict]]:
    """Load maha/antar lists for Jaimini report from precomputed JSON."""
    block = get_chara_dasha(pc)
    maha = []
    for m in block.get("maha", []):
        maha.append({**m, "start": _as_date(m["start"]), "end": _as_date(m["end"])})
    antar = []
    for a in block.get("antar", []):
        antar.append({**a, "start": _as_date(a["start"]), "end": _as_date(a["end"])})
    return maha, antar


def chara_bhukthi_order(pc: dict) -> list[str]:
    """Global Chara sub-period sign order (KN Rao rotate — matches precomputed antar tables)."""
    block = get_chara_dasha(pc)
    maha = block.get("maha", [])
    if not maha:
        return SIGNS[:]
    progression = [m["sign"] for m in maha[:12] if m.get("sign") in SIGNS]
    if len(progression) < 12:
        return SIGNS[:]
    return progression[1:] + progression[:1]


def compute_chara_pratyantars(
    antar_start: date,
    antar_end: date,
    bhukthi_order: list[str],
) -> list[dict[str, Any]]:
    """Split one Chara antardasha into 12 equal pratyantar sign slices (PyJHora rules)."""
    total_days = (antar_end - antar_start).days
    if total_days <= 0:
        return []
    order = bhukthi_order[:12] if len(bhukthi_order) >= 12 else SIGNS[:]
    out: list[dict[str, Any]] = []
    cur = antar_start
    for i, sign in enumerate(order):
        if i == len(order) - 1:
            end = antar_end
        else:
            end = antar_start + timedelta(days=round(total_days * (i + 1) / 12.0))
        out.append({"sign": sign, "start": cur, "end": end})
        cur = end
    if out:
        out[-1]["end"] = antar_end
    return out


def active_jaimini_chara(pc: dict, target: date) -> dict[str, Any]:
    """Active Chara maha / antar / pratyantar (sign-based) for a calendar day."""
    block = get_chara_dasha(pc)
    maha_sign, antar_sign, pd_sign = "", "", ""
    maha_start_s, maha_end_s = "", ""
    antar_start_s, antar_end_s = "", ""
    pd_start, pd_end = None, None

    for m in block.get("maha", []):
        start, end = str(m.get("start", ""))[:10], str(m.get("end", ""))[:10]
        if start and end and start <= target.isoformat() <= end:
            maha_sign = m.get("sign", "")
            maha_start_s, maha_end_s = start, end
            break

    antar_start_d: date | None = None
    antar_end_d: date | None = None
    for a in block.get("antar", []):
        start, end = str(a.get("start", ""))[:10], str(a.get("end", ""))[:10]
        if start and end and start <= target.isoformat() <= end:
            antar_sign = a.get("sign", "")
            antar_start_s, antar_end_s = start, end
            antar_start_d, antar_end_d = _as_date(start), _as_date(end)
            if not maha_sign:
                maha_sign = a.get("maha_sign", "")
            break

    if antar_start_d and antar_end_d:
        bhukthi = chara_bhukthi_order(pc)
        for row in compute_chara_pratyantars(antar_start_d, antar_end_d, bhukthi):
            if row["start"] <= target <= row["end"]:
                pd_sign = row["sign"]
                pd_start, pd_end = row["start"], row["end"]
                break

    return {
        "maha": maha_sign,
        "antar": antar_sign,
        "pd": pd_sign,
        "maha_start": maha_start_s,
        "maha_end": maha_end_s,
        "antar_start": antar_start_s,
        "antar_end": antar_end_s,
        "pd_start": pd_start.isoformat() if pd_start else "",
        "pd_end": pd_end.isoformat() if pd_end else "",
        "stack": "-".join(x for x in (maha_sign, antar_sign, pd_sign) if x),
    }
