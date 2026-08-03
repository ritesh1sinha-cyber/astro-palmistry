#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KP event timing - M. Ravichandran *Mastering KP Astrology: Timing Life Events with Precision* (rules21).
Promise (CSL) + dasha signification (MD/AD/sub) + transit over cusp/significators.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from kp_book_data import event_group, links_verdict
from kp_chart import KPChart
from natal_from_pyjhora import BirthInput, compute_chart_btr

KP_RULES_SOURCE = "rules21.md (Ravichandran - Mastering KP Astrology: Timing Life Events with Precision)"

EVENT_KIND_TO_KP_DOMAIN: dict[str, str] = {
    "marriage": "marriage",
    "child": "children",
    "career": "career",
    "property": "property",
    "education": "education",
    "travel": "travel",
    "business": "career",
    "recovery": "recovery",
    "wealth": "wealth",
    "status": "status",
}


def _parse_tob(birth_time: str) -> str:
    base = birth_time.strip()
    return base if base.count(":") >= 2 else base + ":00"


def load_kp_chart(
    *,
    client_name: str,
    dob: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    timezone: float,
    place_name: str = "BirthPlace",
    gender: int = 0,
) -> KPChart | None:
    """Build KPChart from PyJHora KP block (Placidus cusps + significators)."""
    try:
        from datetime import date as dt_date
        from kp_from_pyjhora import compute_kp_block

        inp = BirthInput(
            client_name=client_name,
            dob=dob,
            birth_time=_parse_tob(birth_time),
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            place_name=place_name or "BirthPlace",
            gender=gender,
        )
        block = compute_kp_block(inp)
        if not block.get("cusps"):
            return None
        d = dt_date.fromisoformat(dob[:10])
        pc = {"meta": {"client": client_name, "lagna_sign": block.get("lagna_sign", "")}}
        return KPChart.from_block(pc, block, d, client_name)
    except Exception:
        return None


def attach_kp_to_chart_pc(
    parsed: dict,
    pc: dict,
    *,
    client_name: str,
    dob: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    timezone: float,
    place_name: str,
    gender: int,
) -> KPChart | None:
    """Ensure parsed/pc carry kp block; return KPChart if available."""
    if not parsed.get("kp"):
        try:
            from kp_from_pyjhora import compute_kp_block

            inp = BirthInput(
                client_name=client_name,
                dob=dob,
                birth_time=_parse_tob(birth_time),
                latitude=latitude,
                longitude=longitude,
                timezone=timezone,
                place_name=place_name or "BirthPlace",
                gender=gender,
            )
            parsed["kp"] = compute_kp_block(inp)
        except Exception:
            parsed["kp"] = {}
    pc["kp"] = parsed.get("kp") or {}
    if not pc["kp"].get("cusps"):
        return None
    from datetime import date as dt_date
    d = dt_date.fromisoformat(dob[:10])
    return KPChart.from_block(pc, pc["kp"], d, client_name)


def _lord_event_links(kp: KPChart, lord: str, domain: str) -> tuple[bool, str, set[int], set[int]]:
    if not lord:
        return False, "", set(), set()
    links = kp.links(lord)
    g = event_group(domain)
    fav = set(g.get("fav", []))
    unf = set(g.get("unfav", []))
    primary = int(g.get("primary") or 0)
    hit_f = links & fav
    hit_u = links & unf
    if primary and primary in links:
        return True, f"{lord} links primary H{primary}", hit_f, hit_u
    if hit_f and len(hit_u) <= len(hit_f):
        return True, f"{lord} links {sorted(hit_f)}", hit_f, hit_u
    if hit_f:
        return True, f"{lord} partial {sorted(hit_f)}", hit_f, hit_u
    return False, "", hit_f, hit_u


def _sub_lord_confirm(kp: KPChart, lord: str, domain: str) -> tuple[bool, str]:
    """Planet sub lord confirm/deny per rules21 step 4."""
    sub = (kp.planets.get(lord) or {}).get("sub", "")
    if not sub:
        return False, ""
    links = kp.links(sub)
    verdict, hit_f, hit_u = links_verdict(links, domain)
    if verdict == "denied" and hit_u and len(hit_u) >= len(hit_f):
        return False, f"{lord} sub {sub} denies ({sorted(hit_u)})"
    if verdict in ("promised", "mixed") or hit_f:
        return True, f"{lord} sub {sub} ok ({verdict})"
    return False, f"{lord} sub {sub} weak"


def _cusp_sidereal(kp: KPChart, house: int) -> float | None:
    c = kp.cusp(house)
    if c.get("sidereal_deg") is not None:
        return float(c["sidereal_deg"])
    deg = c.get("degree", "")
    if not deg:
        return None
    try:
        d = int(deg[:3])
        return float(d % 360)
    except (ValueError, TypeError):
        return None


def _angular_distance(a: float, b: float) -> float:
    d = abs((a - b) % 360.0)
    return min(d, 360.0 - d)


def _kp_transit_support(
    kp: KPChart,
    when: date,
    primary_house: int,
    latitude: float,
    longitude: float,
    timezone: float,
    place_name: str = "BirthPlace",
    orb_deg: float = 5.0,
) -> tuple[bool, list[str]]:
    """Jupiter/Saturn transit over primary cusp or house significators (rules21 sec 6)."""
    cusp_lon = _cusp_sidereal(kp, primary_house)
    if cusp_lon is None:
        return False, []
    targets: list[tuple[str, float]] = [(f"H{primary_house} cusp", cusp_lon)]
    for pl in kp.signif.get(primary_house, [])[:3]:
        plon = (kp.planets.get(pl) or {}).get("sidereal_deg")
        if plon is not None:
            targets.append((pl, float(plon)))

    try:
        import os
        import sys
        from pathlib import Path

        src = Path(os.environ.get("PYJHORA_SRC", Path(__file__).parent / "pyjhora" / "src"))
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
        from jhora.panchanga import drik
        from jhora import utils, const

        drik.set_ayanamsa_mode("KP")
        place = drik.Place(place_name, latitude, longitude, timezone)
        jd = utils.julian_day_number((when.year, when.month, when.day), (12, 0, 0))
        clues: list[str] = []
        for pname, pid in (("Jupiter", const._JUPITER), ("Saturn", const._SATURN)):
            lon = drik.sidereal_longitude(jd, pid) % 360.0
            for label, tlon in targets:
                if _angular_distance(lon, tlon) <= orb_deg:
                    clues.append(f"Transit {pname} on {label}")
                    break
        return bool(clues), clues[:4]
    except Exception:
        return False, []


def assess_kp_csl_promise(kp: KPChart, event_kind: str) -> dict[str, Any]:
    """Static CSL promise for event primary house (rules21 steps 3-5)."""
    domain = EVENT_KIND_TO_KP_DOMAIN.get(event_kind, event_kind)
    g = event_group(domain)
    primary = int(g.get("primary") or 7)
    sub = kp.csl(primary)
    if not sub:
        return {"yes": False, "note": "CSL unavailable", "verdict": "weak", "primary_house": primary}
    verdict, hit_f, hit_u = links_verdict(kp.links(sub), domain)
    yes = verdict in ("promised", "mixed")
    note = f"H{primary} CSL {sub} - {verdict}"
    if hit_f:
        note += f" fav {sorted(hit_f)}"
    if hit_u:
        note += f" unfav {sorted(hit_u)}"
    return {
        "yes": yes,
        "note": note,
        "verdict": verdict,
        "primary_house": primary,
        "csl": sub,
        "hit_favorable": sorted(hit_f),
        "hit_unfavorable": sorted(hit_u),
    }


def score_kp_event_window(
    kp: KPChart | None,
    *,
    event_kind: str,
    md_lord: str,
    ad_lord: str,
    window_mid: date,
    latitude: float = 0.0,
    longitude: float = 0.0,
    timezone: float = 0.0,
    place_name: str = "",
) -> dict[str, Any]:
    """Return per-technique KP votes for one Vimshottari window."""
    empty = {
        "available": False,
        "source": KP_RULES_SOURCE,
        "csl_promise": {"yes": False, "note": "KP data unavailable"},
        "md_signifies": {"yes": False, "note": ""},
        "ad_signifies": {"yes": False, "note": ""},
        "sub_lord_confirm": {"yes": False, "note": ""},
        "transit_cusp": {"yes": False, "note": ""},
    }
    if not kp:
        return empty

    domain = EVENT_KIND_TO_KP_DOMAIN.get(event_kind, event_kind)
    csl = assess_kp_csl_promise(kp, event_kind)
    primary_h = csl.get("primary_house", 7)

    md_ok, md_note, _, _ = _lord_event_links(kp, md_lord, domain)
    ad_ok, ad_note, _, _ = _lord_event_links(kp, ad_lord, domain)

    sub_md_ok, sub_md_note = _sub_lord_confirm(kp, md_lord, domain)
    sub_ad_ok, sub_ad_note = _sub_lord_confirm(kp, ad_lord, domain)
    sub_ok = sub_md_ok or sub_ad_ok
    sub_note = "; ".join(x for x in (sub_md_note, sub_ad_note) if x)

    transit_ok, transit_clues = _kp_transit_support(
        kp, window_mid, primary_h, latitude, longitude, timezone, place_name,
    )

    return {
        "available": True,
        "source": KP_RULES_SOURCE,
        "domain": domain,
        "csl_promise": {"yes": csl["yes"], "note": csl["note"], "verdict": csl["verdict"]},
        "md_signifies": {"yes": md_ok, "note": md_note},
        "ad_signifies": {"yes": ad_ok, "note": ad_note},
        "sub_lord_confirm": {"yes": sub_ok, "note": sub_note},
        "transit_cusp": {"yes": transit_ok, "note": "; ".join(transit_clues)},
    }
