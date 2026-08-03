#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Birth-chart  -  palm correlation lane (Jyotis Saraswati Astro-Palmistry).

When palm photos are unclear, derive what the hand should show from known
D1 planet positions (house, sign, dignity) per the book's house/mount mapping
and Lal Kitab-style combinations.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Optional

from astro_precompute import get_dignity, house_from_lagna, resolve_precompute
from astro_palmistry_anchor_engine import anchor_analysis_html, apply_cv_evidence, build_anchor_analysis
from astro_palmistry_longevity import longevity_html
from astro_palmistry_morphology import analyze_morphology_both_hands, morphology_html
from astro_palmistry_book_cv import book_extensions_html, line_timing_html
from astro_palmistry_zone_cv import aggregate_zone_metrics

BASE = Path(__file__).resolve().parent
REPORTS = BASE / "reports"

ZONE_LEGEND_HTML = """
<p class="fine" style="margin-bottom:10px">Mounts = book finger-root zones. Dashed = house sectors (5/6/8/10).
<span style="color:#888">Zodiac grid</span> = 12 signs (Ari-Pis). Sacred: <span style="color:#00ffff">YAV</span> thumb base,
<span style="color:#ffc800">DIKSHA</span> under Jupiter.
Lines: <span style="color:#dcb41e">Life</span> + 5-yr ticks (80-yr scale),
<span style="color:#2828dc">Heart</span>, <span style="color:#28aa3c">Head</span>,
<span style="color:#285adc">Fate</span> (all lines carry 5-yr age dots). Yellow tick = age 20 (Jupiter-Saturn perpendicular).</p>
<ul class="bullets" style="font-size:.82rem">
  <li><span style="color:#3cb43c">&#9632;</span> Jupiter &nbsp; <span style="color:#b47828">&#9632;</span> Saturn &nbsp;
  <span style="color:#288cdc">&#9632;</span> Sun &nbsp; <span style="color:#c83cc8">&#9632;</span> Mercury (pinky root) &nbsp;
  <span style="color:#3c3cdc">&#9632;</span> Venus &nbsp; <span style="color:#dcb43c">&#9632;</span> Moon (lower edge)</li>
  <li><span style="color:#2828dc">&#9632;</span> Mars (Plain) &nbsp; <span style="color:#28dcdc">&#9632;</span> Rahu (above heart) &nbsp;
  <span style="color:#dc28b4">&#9632;</span> Ketu (upper Mars, outer edge)</li>
  <li>Dashed: <span style="color:#c878ff">5th</span> <span style="color:#8c8cc8">6th</span>
  <span style="color:#78c878">8th longevity</span> <span style="color:#c8c850">10th career</span></li>
</ul>
"""


def embed_overlay_images(paths: list[Path]) -> list[dict[str, str]]:
    """Read overlay JPGs and return list with base64 data URIs for inline HTML."""
    import base64

    out: list[dict[str, str]] = []
    for p in paths:
        p = Path(p)
        if not p.is_file():
            continue
        raw = p.read_bytes()
        if len(raw) < 100:
            continue
        b64 = base64.b64encode(raw).decode("ascii")
        out.append({
            "label": p.name,
            "data_uri": f"data:image/jpeg;base64,{b64}",
            "path": str(p),
        })
    return out

PLANET_IDS = {
    "Sun": "Sun", "Moon": "Moon", "Mars": "Mars", "Merc": "Mercury",
    "Jupt": "Jupiter", "Venu": "Venus", "Satn": "Saturn", "Saturn": "Saturn",
    "Rahu": "Rahu", "Ketu": "Ketu",
}

HOUSE_PALM: dict[int, dict[str, str]] = {
    1: {
        "themes": "Self, body, vitality, general fortune",
        "palm": "Plain of Mars, thumb base, Life / Head / Heart lines (1st house zone).",
    },
    2: {
        "themes": "Wealth, family, speech, savings",
        "palm": "Mounts of Jupiter and Sun; fate / Sun lines toward percussion.",
    },
    3: {
        "themes": "Siblings, courage, short travel, documents",
        "palm": "Mount of Moon, Mercury lines, Head line branches, travel marks on Venus mount.",
    },
    4: {
        "themes": "Mother, home, property, vehicles",
        "palm": "Mount of Moon, Sun / fate lines, heart line base toward Luna.",
    },
    5: {
        "themes": "Children, creativity, romance, speculation",
        "palm": "Mounts of Venus and Moon; Heart line, marriage / children lines, girdle of Venus.",
    },
    6: {
        "themes": "Health, service, debts, enemies",
        "palm": "Upper Mars, Moon and Jupiter mounts; health / Hepatica lines.",
    },
    7: {
        "themes": "Marriage, partnership, public dealings",
        "palm": "Venus and Moon mounts; marriage lines, heart line, attachment lines.",
    },
    8: {
        "themes": "Longevity, legacies, sudden events, hidden matters",
        "palm": "Mars, Moon, Saturn mounts; life, heart, fate, marriage lines crossed here.",
    },
    9: {
        "themes": "Luck, father-guru, religion, long travel",
        "palm": "Moon, Sun, Jupiter, Saturn; intuition line, travel lines, ring of Solomon.",
    },
    10: {
        "themes": "Career, status, father, authority",
        "palm": "Jupiter, Sun, Mercury mounts and fingers; fate, Sun, business lines.",
    },
    11: {
        "themes": "Gains, friends, elder siblings, fulfilment",
        "palm": "Venus, Sun mounts; heart, life, fate lines with gain branches.",
    },
    12: {
        "themes": "Expenses, foreign lands, bed-pleasures, secret sorrows",
        "palm": "Mars and Moon mounts; life, fate, sun lines  -  often secret grille marks.",
    },
}

NODE_PALM = {
    "Rahu": "Area above Heart line (Great Triangle / upper zone). Heavy fine cross-lines = Rahu affliction.",
    "Ketu": "Area below Heart line; upper Mars mount = Ketu sector. Grille on upper Mars = Ketu-Mars stress.",
}

DIGNITY_PALM: dict[str, dict[str, str]] = {
    "Mars": {
        "debilitated": (
            "Hand often rough with hard fingers; heart and fate lines weak. "
            "Both Mars mounts wide; Plain of Mars narrow and depressed; thumb long, stiff "
            "(Mars debilitated in Cancer  -  book Mars chapter)."
        ),
        "exalted": "Plain of Mars firm, upper/lower Mars well developed without heavy grille.",
        "moolatrikona": "Strong Mars mounts; active Plain of Mars with auspicious marks, not hollow.",
        "own_sign": "Prominent Mars mounts; courageous line pattern on Plain of Mars.",
    },
    "Mercury": {
        "debilitated": (
            "Mount under Mercury (4th) finger weak, flat, crossed  -  Mercury debilitated in Pisces."
        ),
        "exalted": "Mercury mount smooth, well developed; supple hand, long thumb.",
        "own_sign": "Mercury finger and mount clearly developed; business / head lines clean.",
    },
    "Venus": {
        "debilitated": (
            "Mount of Venus much crossed and rayed; short smooth fingers; broken girdle of Venus "
            "(Venus debilitated in Virgo)."
        ),
        "exalted": "Large firm Venus mount, auspicious marks, normal girdle; soft well-shaped nails.",
        "own_sign": "Venus mount full and even; affection / marriage lines clear.",
    },
    "Jupiter": {
        "debilitated": "Jupiter mount flat or heavily rayed; fate line twisted toward Saturn.",
        "exalted": "Jupiter mount high under index finger; benevolent trident or upward branches on fate line.",
        "own_sign": "Index finger dominant; Jupiter mount rounded and firm.",
    },
    "Saturn": {
        "debilitated": "Saturn mount depressed; fate line barred from Taurus / upper-Mars sector.",
        "exalted": "Saturn finger straight; fate line deep, single, reaching middle finger base.",
        "own_sign": "Prominent Saturn mount; disciplined, sparse line pattern.",
    },
    "Sun": {
        "debilitated": "Sun mount under ring finger weak; Sun line faint or broken.",
        "exalted": "Ring finger long; Sun mount radiant; Sun line clear toward Apollo mount.",
        "own_sign": "Sun line and mount active; dignified ring finger.",
    },
    "Moon": {
        "debilitated": "Mount of Moon flat, many cross lines; life line branch toward Moon weak.",
        "exalted": "Luna mount full at percussion; travel lines from Moon mount clear.",
        "own_sign": "Moon mount developed; emotional / travel lines active.",
    },
    "Rahu": {
        "neutral_sign": "Check Rahu zone above Heart line for grille, islands, dark colour.",
        "exalted": "Rahu zone may show strong fate branches if chart Rahu is well placed in trikona.",
        "debilitated": "Heavy cross-hatching above Heart line; blackish life/heart junction.",
    },
    "Ketu": {
        "neutral_sign": "Upper Mars (Ketu sector): watch for grille, sudden-ending lines.",
        "exalted": "Curved line Jupiter - thumb base (Ketu in Scorpio yoga) when nodes favourable.",
        "debilitated": "Upper Mars rayed; Ketu-Mars affliction marks near Plain of Mars.",
    },
}

# Book-backed house combos  -  palm read hints (predicate on normalized planet dict)
ComboRule = tuple[Callable[[dict[str, dict]], bool], str]

def _h(chart: dict[str, dict], planet: str) -> int:
    return int(chart.get(planet, {}).get("house", 0) or 0)

def _dig(chart: dict[str, dict], planet: str) -> str:
    return str(chart.get(planet, {}).get("dignity", "") or "")

def _sign(chart: dict[str, dict], planet: str) -> str:
    return str(chart.get(planet, {}).get("sign", "") or "")


COMBO_RULES: list[ComboRule] = [
    (
        lambda c: _h(c, "Mars") == 12 and _h(c, "Ketu") == 5,
        "Mars in 12th + Ketu in 5th (book): Mars in 12th indicates a <em>benefic Ketu</em> on the "
        "node axis, while Ketu in 5th stresses children, ears, spine, and knees. On the palm, read "
        "12th-house Mars marks (depressed Plain of Mars, secret grille on Luna/Mars) together with "
        "5th-house Venus/Moon mounts and upper-Mars (Ketu) sector.",
    ),
    (
        lambda c: _h(c, "Mars") == 12,
        "Mars in 12th (book): benefic Rahu/Ketu modulation; palm shows 12th-zone Mars/Moon marks  -  "
        "expenses, foreign tie, or hidden strain lines on life/fate toward percussion.",
    ),
    (
        lambda c: _dig(c, "Mars") == "debilitated",
        "Mars debilitated (Cancer): expect rough palm, depressed Plain of Mars, stiff thumb, "
        "weak heart/fate lines regardless of house  -  verify on close-up Mars zone photos.",
    ),
    (
        lambda c: _h(c, "Ketu") == 5,
        "Ketu in 5th (book): children / creativity house stressed  -  inspect Heart line, Venus mount, "
        "and upper Mars (Ketu area) for grille or broken branches.",
    ),
    (
        lambda c: _h(c, "Mercury") == 10 and _dig(c, "Mercury") == "debilitated",
        "Mercury debilitated in 10th: career line twisted; Mercury mount under little finger weak  -  "
        "matches Neecha Mercury on karma bhava (status earned through remedial discipline).",
    ),
    (
        lambda c: _h(c, "Jupiter") == 8 and _dig(c, "Jupiter") == "debilitated",
        "Jupiter debilitated in 8th: Jupiter mount rayed; fate line may bend toward Saturn  -  "
        "legacy, in-law, or sudden-turn themes on Saturn/Mars mounts.",
    ),
    (
        lambda c: _h(c, "Venus") == 10 and _dig(c, "Venus") == "exalted",
        "Venus exalted in 10th: strong Venus mount with clean girdle supports public career and "
        "comfort through arts, finance, or partnership visibility.",
    ),
    (
        lambda c: _h(c, "Saturn") in (6, 8, 12),
        f"Saturn in dusthana ({'6/8/12'}): Saturn mount and fate line often barred; health or "
        "service strain marks on upper Mars / Hepatica zone.",
    ),
    (
        lambda c: _h(c, "Rahu") == _h(c, "Mars") and _h(c, "Rahu") > 0,
        "Rahu conjoined Mars by house (whole sign): Plain of Mars and Rahu zone above Heart line "
        "should both be active  -  accidents, engineering, or sharp-tool karma marks.",
    ),
]


def _normalize_pc(pc: dict) -> tuple[str, dict[str, dict]]:
    lagna = pc.get("meta", {}).get("lagna_sign") or pc.get("lagna", {}).get("sign") or "Aries"
    raw = pc.get("planets") or {}
    out: dict[str, dict] = {}
    for key, data in raw.items():
        if not isinstance(data, dict):
            continue
        pname = PLANET_IDS.get(key, key)
        sign = data.get("sign", "")
        house = data.get("house") or (house_from_lagna(sign, lagna) if sign else 0)
        dignity = data.get("dignity") or (get_dignity(pname, sign) if sign else "neutral_sign")
        out[pname] = {
            "sign": sign,
            "house": int(house),
            "dignity": dignity,
            "degree_in_sign": data.get("degree_in_sign"),
            "nakshatra": data.get("nakshatra", ""),
        }
    return lagna, out


def _chart_from_planets_d1(path: Path) -> Optional[dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    lagna = "Gemini"
    for r in rows:
        if r.get("id") == "ASC":
            lagna = r["sign"]
            break
    planets: dict[str, dict] = {}
    for r in rows:
        pid = r.get("id", "")
        if pid == "ASC":
            continue
        pname = PLANET_IDS.get(pid, pid)
        sign = r.get("sign", "")
        planets[pname] = {
            "sign": sign,
            "house": house_from_lagna(sign, lagna),
            "dignity": get_dignity(pname, sign),
            "nakshatra": r.get("nakshatra", ""),
        }
    return {
        "meta": {"lagna_sign": lagna, "source": str(path.name)},
        "lagna": {"sign": lagna},
        "planets": planets,
    }


def _find_extract(slug: str) -> Optional[Path]:
    for p in sorted(REPORTS.glob(f"**/*{slug}*_extracted.txt"), reverse=True):
        return p
    for p in sorted(REPORTS.glob("**/*_extracted.txt"), reverse=True):
        if slug.lower() in p.name.lower():
            return p
    return None


def _find_precomputed(slug: str, session_dir: Optional[Path]) -> Optional[Path]:
    if session_dir and session_dir.is_dir():
        manifest = session_dir / "session_manifest.json"
        if manifest.is_file():
            m = json.loads(manifest.read_text(encoding="utf-8"))
            rel = m.get("precomputed_json", "")
            if rel:
                p = BASE / rel
                if p.is_file():
                    return p
        for p in sorted(session_dir.glob("input/*_precomputed.json")):
            return p
    client_dir = REPORTS / slug
    if client_dir.is_dir():
        for p in sorted(client_dir.glob("*_precomputed.json")):
            return p
    for p in sorted(REPORTS.glob(f"**/*{slug}*_precomputed.json"), reverse=True):
        return p
    return None


def load_chart_for_client(
    *,
    client_name: str,
    dob: str = "",
    birth_time: str = "",
    birth_place: str = "",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    timezone: Optional[float] = None,
    session_dir: Optional[Path] = None,
) -> dict:
    """Resolve D1 chart dict (precomputed shape) from session, reports, or birth data."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", client_name.strip()).strip("_") or "Client"

    pre = _find_precomputed(slug, session_dir)
    if pre:
        return json.loads(pre.read_text(encoding="utf-8"))

    for p in sorted(REPORTS.glob(f"**/*{slug}*_planets_d1.json"), reverse=True):
        built = _chart_from_planets_d1(p)
        if built:
            return built

    extract = _find_extract(slug)
    if extract and dob.strip():
        return resolve_precompute(
            client_name.strip(),
            dob.strip(),
            extracted_path=str(extract),
            precomputed_path=None,
            birth_time=birth_time.strip() or None,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            place_name=birth_place.strip(),
        )

    if dob.strip() and birth_time.strip() and latitude is not None and longitude is not None and timezone is not None:
        return resolve_precompute(
            client_name.strip(),
            dob.strip(),
            birth_time=birth_time.strip(),
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            place_name=birth_place.strip(),
        )

    raise FileNotFoundError(
        "No birth chart found. Generate Vedic reports first (session precomputed JSON), "
        "upload VedicReport PDF, or enter DOB + time + place with coordinates."
    )


def _planet_palm_hint(planet: str, info: dict) -> str:
    sign = info.get("sign", "")
    house = info.get("house", 0)
    dignity = info.get("dignity", "neutral_sign")
    house_note = HOUSE_PALM.get(house, {}).get("palm", "")
    dig_notes = DIGNITY_PALM.get(planet, {})
    palm_sig = dig_notes.get(dignity) or dig_notes.get("neutral_sign", "")
    if planet in NODE_PALM:
        palm_sig = f"{palm_sig} {NODE_PALM[planet]}".strip()
    parts = [
        f"<strong>{planet}</strong> in {sign} (house {house}, {dignity.replace('_', ' ')})",
    ]
    if palm_sig:
        parts.append(palm_sig)
    if house_note:
        parts.append(f"House zone on palm: {house_note}")
    return "  -  ".join(parts[:1]) + ". " + " ".join(parts[1:])


def analyze_chart(
    pc: dict,
    cv_marked: list[dict] | None = None,
    cv_hands: list[list[dict]] | None = None,
    cv_longevity: list[dict] | None = None,
    morphology: dict[str, Any] | None = None,
    palm_paths: tuple[Path, Path] | None = None,
) -> dict[str, Any]:
    lagna, planets = _normalize_pc(pc)
    anchor = build_anchor_analysis(planets, lagna)
    if cv_hands:
        zone_metrics = aggregate_zone_metrics(cv_hands)
    elif cv_marked:
        zone_metrics = aggregate_zone_metrics([cv_marked])
    else:
        zone_metrics = {}
    anchor = apply_cv_evidence(anchor, zone_metrics)

    # Best longevity confluence from palm photos (prefer hand with detected life line)
    longevity: dict[str, Any] | None = None
    for lv in cv_longevity or []:
        if lv and lv.get("estimate_years"):
            if longevity is None or lv["estimate_years"] > longevity.get("estimate_years", 0):
                longevity = lv
    if longevity is None and cv_longevity:
        longevity = cv_longevity[0]

    if morphology is None and palm_paths:
        lp, rp = palm_paths
        if lp.is_file() and rp.is_file():
            morphology = analyze_morphology_both_hands(lp, rp, pc)

    planet_rows = []
    for pname in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        if pname not in planets:
            continue
        info = planets[pname]
        planet_rows.append({
            "planet": pname,
            "sign": info["sign"],
            "house": info["house"],
            "dignity": info["dignity"],
            "palm_hint": _planet_palm_hint(pname, info),
        })

    return {
        "mode": "birth_chart",
        "lagna": lagna,
        "source": pc.get("meta", {}).get("source", "precomputed"),
        "dob": pc.get("meta", {}).get("dob", ""),
        "birth_time": pc.get("meta", {}).get("birth_time", ""),
        "planets": planet_rows,
        "anchors": anchor["anchors"],
        "confluence": anchor["confluence"],
        "zone_plan": anchor["zone_plan"],
        "cv_marked": cv_marked or [],
        "zone_metrics": anchor.get("zone_metrics", {}),
        "cv_inspected": anchor.get("cv_inspected", False),
        "longevity": longevity,
        "morphology": morphology,
        "summary": (
            f"Lagna {lagna}. Each chart planet is a line-main for its house; sub-planets in other "
            f"houses modify the palm read per book rules. CV marks mount zones when photos are supplied."
        ),
    }


def chart_analysis_html(analysis: dict) -> str:
    """HTML: anchor/sub-planet structure + CV overlay images (embedded base64)."""
    overlay = ""
    embedded = analysis.get("cv_overlay_embedded") or []
    if embedded:
        imgs = "".join(
            f'<figure style="margin:12px 0;text-align:center">'
            f'<img src="{e["data_uri"]}" alt="CV zones {e["label"]}" '
            f'style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px"/>'
            f'<figcaption class="fine">{e["label"]}</figcaption></figure>'
            for e in embedded[:4]
        )
        overlay = (
            f'<div class="section-h">CV zone markers on palm</div>'
            f'<div class="card">{ZONE_LEGEND_HTML}{imgs}</div>'
        )
    elif analysis.get("cv_overlays"):
        imgs = "".join(
            f'<figure style="margin:12px 0"><p class="hint" style="color:var(--red)">'
            f'Overlay image missing: {p}. Re-generate report with palm photos.</p></figure>'
            for p in analysis.get("cv_overlays", [])[:2]
        )
        overlay = f'<div class="section-h">CV zone markers on palm</div><div class="card">{imgs}</div>'

    return overlay + longevity_html(analysis.get("longevity") or {}) + line_timing_html(
        analysis.get("timing_marks"), analysis.get("lines_summary")
    ) + book_extensions_html(analysis.get("book_extensions")) + morphology_html(
        analysis.get("morphology"), chart_lagna=analysis.get("lagna", "")
    ) + anchor_analysis_html(analysis)
