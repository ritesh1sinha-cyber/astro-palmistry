"""Life-area transition maps built from the canonical timing windows.

This module does not invent a new astrology clock.  It consumes the same
validated timing rows already produced by report_timing/canonical_result and
adds a customer-useful view of *why the tone changes* inside a long forecast.

Each node is one dated subset-window.  Its overlap stack is sampled at the
window midpoint from the existing Vimshottari/Yogini/Chara confluence, while
Jupiter/Saturn + Ashtakavarga come directly from the timing row.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

_FILLER = re.compile(r"timing evidence is included", re.I)
_LEAK = re.compile(r"\b(vimshottari|yogini|chara|nadi)\b", re.I)

SHORT_PHASE = {
    "Pressure / Restructuring": "Pressure",
    "Pressure → Opening": "Opening",
    "Adjustment → Opening": "Opening",
    "Expansion → Pressure": "Change",
    "Momentum → Adjustment": "Change",
    "Pressure → Adjustment": "Change",
    "Adjustment → Caution": "Change",
    "Opening / Expansion": "Opening",
    "Opportunity / Evaluation": "Opening",
    "Adjustment / Reassessment": "Build",
}


def field_of(obj: Any, name: str, default: Any = "") -> Any:
    """Read a field from a dict or a model without raising."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        val = obj.get(name, default)
    else:
        val = getattr(obj, name, default)
    return default if val is None else val


def _d(v: Any):
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _mid(start: Any, end: Any):
    a, b = _d(start), _d(end)
    if not a or not b:
        return a or b
    return a + (b - a) / 2


def _iso(v: Any) -> str:
    parsed = _d(v)
    if parsed:
        return parsed.isoformat()
    return str(v or "")[:20]


def _month_label(v: Any) -> str:
    parsed = _d(v)
    if parsed:
        return f"{parsed:%b %Y}"
    text = str(v or "").strip()
    return text


def _conf(value: Any) -> str:
    raw = str(value or "low").strip().lower()
    if raw in ("high", "moderate", "low"):
        return raw
    if "high" in raw:
        return "high"
    if "mod" in raw:
        return "moderate"
    return "low"


def _phase(direction: str, previous: str, *, event_type: str = "") -> tuple[str, str]:
    d = (direction or "mixed").lower()
    p = (previous or "").lower()
    if p == "down" and d == "up":
        return "Pressure → Opening", "The pressure phase gives way to an opening."
    if p == "mixed" and d == "up":
        return "Adjustment → Opening", "An uncertain phase begins to open into opportunity."
    if p == "up" and d == "down":
        return "Expansion → Pressure", "An earlier opening becomes more demanding."
    if p == "up" and d == "mixed":
        return "Momentum → Adjustment", "Momentum remains, but the conditions become less straightforward."
    if p == "down" and d == "mixed":
        return "Pressure → Adjustment", "The heavier tone begins to ease, but the matter is not fully settled."
    if p == "mixed" and d == "down":
        return "Adjustment → Caution", "An uncertain phase becomes more demanding and needs care."
    if d == "up":
        return "Opening / Expansion", "This is an opportunity-oriented part of the cycle."
    if d == "down":
        return "Pressure / Restructuring", "This is the part of the cycle where effort, correction or patience matters most."
    if event_type and "opportunity" in event_type.lower():
        return "Opportunity / Evaluation", "An opening is present, but it should be evaluated carefully."
    return "Adjustment / Reassessment", "The chart is asking for adjustment rather than an all-or-nothing move."


def short_phase(phase: str, *, last: bool = False, direction: str = "") -> str:
    label = SHORT_PHASE.get(str(phase or "").strip(), "")
    if last and (direction or "").lower() in ("up", "support") and label in ("Opening", "Build"):
        return "Recognition"
    return label or "Change"


def customer_label(text: str) -> str:
    """Keep genuine confluence names; drop filler and internal method tokens."""
    t = str(text or "").strip()
    if not t or _FILLER.search(t):
        return ""
    low = t.lower()
    if "vimshottari" in low:
        return "Dasha period"
    if "nadi" in low:
        return "Secondary timing cross-check"
    if _LEAK.search(t) and "yogini" not in low and "chara" not in low:
        return ""
    return t


def customer_list(items: list[Any] | None, *, limit: int = 7) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items or []:
        label = customer_label(str(item))
        if not label:
            continue
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(label)
        if len(out) >= limit:
            break
    return out


def _stack(pc: dict, when) -> dict[str, Any]:
    parsed = _d(when)
    cache = getattr(_stack, "_memo", None)
    if cache is None:
        cache = {}
        setattr(_stack, "_memo", cache)
    pc_id = id(pc)
    key = (pc_id, parsed.year if parsed else 0, parsed.month if parsed else 0)
    if key in cache:
        return cache[key]
    try:
        import report_confluence as CF
        dc = CF.dasha_confluence(pc, parsed or when) or {}
    except Exception:
        dc = {}
    readings = list(dc.get("readings") or [])
    out: dict[str, Any] = {
        "vimshottari": "",
        "yogini": "",
        "chara": "",
        "bnn": "",
        "agreement": str(dc.get("agreement") or ""),
        "direction": str(dc.get("direction") or "mixed"),
    }
    for r in readings:
        kind = str(r.get("kind") or "")
        label = str(r.get("label") or "").strip()
        if kind == "vimshottari":
            out["vimshottari"] = label
        elif kind == "yogini":
            out["yogini"] = label
        elif kind == "chara":
            out["chara"] = label
        elif kind == "bnn":
            out["bnn"] = label
    cache[key] = out
    if len(cache) > 128:
        cache.clear()
        cache[key] = out
    return out


def build_transition_map(pc: dict, area_key: str, timing_windows: list[dict], *, limit: int = 6) -> list[dict]:
    """Turn canonical timing windows into a small, ordered transition map."""
    rows = [r for r in (timing_windows or []) if isinstance(r, dict) and (r.get("start") or r.get("end"))]
    rows.sort(key=lambda r: str(r.get("start") or ""))
    out: list[dict] = []
    previous = ""
    for r in rows[:limit]:
        when = _mid(r.get("start"), r.get("end"))
        stack = _stack(pc, when) if when else {}
        direction = "up" if r.get("aligned") else (
            "down" if r.get("dasha") == "down"
            or r.get("promise") == "down"
            or int(r.get("bav", 0) or 0) <= 3
            else "mixed"
        )
        phase, meaning = _phase(direction, previous, event_type=str(r.get("event_type") or ""))
        previous = direction
        # Three identical paragraphs inside one card read as a template. The
        # running period is what actually separates two same-tone stretches.
        if any(node["phase"] == phase for node in out):
            period = str(r.get("dasha_label") or "").split(" · ")[0].strip()
            if period:
                meaning = f"Under {period}, {meaning[0].lower()}{meaning[1:]}"

        drivers = []
        # The timing row joins every system into one label; the other systems
        # are added separately below, so only the dasha part belongs here.
        dasha = str(r.get("dasha_label") or "").split(" · ")[0].strip()
        if dasha:
            drivers.append(dasha)
        planet = str(r.get("planet") or "").strip()
        if planet:
            drivers.append(f"{planet} transit")
        bav = r.get("bav")
        if bav not in (None, ""):
            drivers.append(f"Ashtakavarga {bav} bindus")
        if stack.get("yogini"):
            drivers.append(f"Yogini: {stack['yogini']}")
        if stack.get("chara"):
            drivers.append(f"Chara: {stack['chara']}")
        if stack.get("bnn"):
            drivers.append(f"Nadi timing: {stack['bnn']}")

        overlap = [x for x in (
            stack.get("vimshottari"), stack.get("yogini"),
            stack.get("chara"),
            f"Nadi timing: {stack['bnn']}" if stack.get("bnn") else "",
        ) if x]
        if planet:
            overlap.append(f"{planet} transit")
        if bav not in (None, ""):
            overlap.append(f"{bav} bindus")

        try:
            bav_value = int(float(bav)) if bav not in (None, "") else 0
        except (TypeError, ValueError):
            bav_value = 0

        out.append({
            "start": _iso(r.get("start")),
            "end": _iso(r.get("end")),
            "area": area_key,
            "direction": direction,
            "phase": phase,
            "meaning": meaning,
            "event_type": str(r.get("event_type") or "")[:100],
            "planet": planet[:30],
            "dasha": dasha[:100],
            "bav": bav_value,
            "score": float(r.get("score") or 0.0),
            "confidence": _conf(r.get("confidence")),
            "source": str(r.get("source") or "")[:100],
            "overlap": overlap[:7],
            "drivers": drivers[:7],
            "timing_systems": stack,
        })
    return out


_BAV_PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
_FAST_MOVERS = ("Mercury", "Sun", "Venus")
# The Moon changes sign every couple of days; dating that on a multi-year map
# would bury the slow transits that actually mark a turn.
_TOO_FAST = ("Moon",)


def _transit_segments_for(pc: dict, planet: str, start: date, years: int) -> list[dict]:
    """Sign-by-sign stays for one planet, memoized per chart and planet."""
    cache = getattr(_transit_segments_for, "_memo", None)
    if cache is None:
        cache = {}
        setattr(_transit_segments_for, "_memo", cache)
    key = (id(pc), planet, start.isoformat(), years)
    if key in cache:
        return cache[key]
    segs: list[dict] = []
    try:
        from vedic_ashtakavarga_report import AV, transit_timeline
        av = AV(pc)
        if planet in _BAV_PLANETS:
            segs = list(transit_timeline(av, planet, start, start + timedelta(days=365 * years)))
    except Exception:  # noqa: BLE001
        segs = []
    if len(cache) > 64:
        cache.clear()
    cache[key] = segs
    return segs


def _node_segments(pc: dict, planet: str, start: date, years: int) -> list[dict]:
    """Rahu/Ketu sign stays. The nodes carry no bindus, only a house."""
    cache = getattr(_node_segments, "_memo", None)
    if cache is None:
        cache = {}
        setattr(_node_segments, "_memo", cache)
    key = (id(pc), planet, start.isoformat(), years)
    if key in cache:
        return cache[key]
    segs: list[dict] = []
    try:
        import swisseph as swe

        swe.set_sid_mode(swe.SIDM_LAHIRI)
        signs = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
                 "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")
        lagna = str(((pc or {}).get("meta") or {}).get("lagna_sign") or "")
        lagna_idx = signs.index(lagna) if lagna in signs else 0
        offset = 180.0 if planet.lower() == "ketu" else 0.0

        def sign_at(when: date) -> int:
            jd = swe.julday(when.year, when.month, when.day, 12.0)
            xx, _ = swe.calc_ut(jd, swe.MEAN_NODE,
                                swe.FLG_MOSEPH | swe.FLG_SIDEREAL)
            return int(((xx[0] + offset) % 360) // 30) % 12

        end = start + timedelta(days=365 * years)
        step = timedelta(days=5)
        edges: list[tuple[date, int]] = [(start, sign_at(start))]
        cursor = start
        while cursor < end:
            nxt = min(cursor + step, end)
            cur_sign = sign_at(nxt)
            if cur_sign != edges[-1][1]:
                lo, hi = cursor, nxt
                while (hi - lo).days > 1:
                    mid = lo + timedelta(days=(hi - lo).days // 2)
                    if sign_at(mid) == edges[-1][1]:
                        lo = mid
                    else:
                        hi = mid
                edges.append((hi, cur_sign))
            cursor = nxt
        for i, (when, sign_idx) in enumerate(edges):
            nxt_date = edges[i + 1][0] if i + 1 < len(edges) else end
            segs.append({
                "start": when, "end": nxt_date, "sign": signs[sign_idx],
                "house": (sign_idx - lagna_idx) % 12 + 1, "bav": None,
            })
    except Exception:  # noqa: BLE001
        segs = []
    if len(cache) > 32:
        cache.clear()
    cache[key] = segs
    return segs


def _transit_tone(bav: Any, in_house: bool) -> tuple[str, bool]:
    """Supportive / testing / steady, plus whether it is a major trigger."""
    if bav is None:
        # Rahu and Ketu have no Ashtakavarga score, so the only honest claim
        # is where they sit and for how long.
        return ("onhouse", True) if in_house else ("background", False)
    try:
        score = int(float(bav))
    except (TypeError, ValueError):
        score = 4
    if not in_house:
        return "background", False
    if score >= 5:
        return "supportive", True
    if score <= 3:
        return "testing", True
    return "steady", False


def build_context_transits(
    pc: dict,
    house: int,
    *,
    today: date | None = None,
    years: int = 3,
    md_lord: str = "",
    ad_lord: str = "",
    limit: int = 14,
) -> list[dict]:
    """Transits of the house ruler and the running dasha lords.

    Jupiter and Saturn are the classical slow triggers already carried by the
    timing rows.  A reader also wants the planet that actually owns the house
    being discussed, and the lords of the period they are living in, even when
    those stays are quiet — a quiet stay is itself an answer to "why nothing is
    moving yet".
    """
    today = today or date.today()
    house = int(house or 0)
    roles: dict[str, list[str]] = {}

    lords = (pc or {}).get("house_lords") or {}
    # Charts reach this point with either int or str house keys.
    info = lords.get(str(house)) or lords.get(house) or {}
    ruler = str((info or {}).get("lord") or "").strip()
    if ruler:
        roles.setdefault(ruler, []).append(f"ruler of house {house}")
    if md_lord:
        roles.setdefault(str(md_lord).strip(), []).append("mahadasha lord")
    if ad_lord:
        roles.setdefault(str(ad_lord).strip(), []).append("antardasha lord")
    roles.pop("", None)

    rows: list[dict] = []
    for planet, planet_roles in roles.items():
        fast = planet in _FAST_MOVERS
        if planet in _TOO_FAST:
            continue
        if planet in _BAV_PLANETS:
            segments = _transit_segments_for(pc, planet, today, 1 if fast else years)
        elif planet in ("Rahu", "Ketu"):
            segments = _node_segments(pc, planet, today, years)
        else:
            continue
        planet_rows: list[dict] = []
        for seg in segments:
            start, end = _d(seg.get("start")), _d(seg.get("end"))
            if not start or not end or end < today:
                continue
            seg_house = int(seg.get("house") or 0)
            in_house = bool(house) and seg_house == house
            # A fast planet crosses every house several times a year; listing
            # each crossing is noise, so only its visits to this house count.
            if fast and not in_house:
                continue
            tone, major = _transit_tone(seg.get("bav"), in_house)
            planet_rows.append({
                "planet": planet,
                "role": " · ".join(planet_roles),
                "sign": str(seg.get("sign") or ""),
                "house": seg_house,
                "start": _iso(start),
                "end": _iso(end),
                "bav": int(seg.get("bav") or 0),
                "tone": tone,
                "major": major,
                "in_house": in_house,
            })
        rows.extend(planet_rows[:3] if fast else planet_rows)
    # Stays that touch this house are the point; the rest is background that
    # still deserves a date, so it fills whatever room is left.
    rows.sort(key=lambda r: (r["start"], r["planet"]))
    on_house = [r for r in rows if r["in_house"]]
    background = [r for r in rows if not r["in_house"]]
    keep = on_house[:limit] + background[: max(0, limit - len(on_house[:limit]))]
    keep.sort(key=lambda r: (r["start"], r["planet"]))
    return keep


def transit_caption(row: Any) -> str:
    """One customer-readable line for a context transit row."""
    planet = str(field_of(row, "planet") or "")
    role = str(field_of(row, "role") or "")
    sign = str(field_of(row, "sign") or "")
    house = int(field_of(row, "house", 0) or 0)
    tone = str(field_of(row, "tone") or "steady")
    bits = [f"{planet} in {sign}" if sign else planet]
    if house:
        bits.append(f"house {house}")
    if role:
        bits.append(role)
    lead = " · ".join(bits)
    tail = {
        "supportive": "supportive bindu score for this area",
        "testing": "low bindu score, so this stay asks for care",
        "steady": "an average stay on this area",
        "onhouse": "a long stay sitting directly on this area",
        "background": "away from this area, so it stays in the background",
    }.get(tone, "")
    return f"{lead} — {tail}" if tail else lead


def window_state(nodes: list[Any], *, today: date | None = None) -> dict[str, Any]:
    """Is the dated stretch running now, or is it still a promise?

    The engine can mark an area "active" from the period alone while every
    dated window on the card still sits years out.  Printing "Active now"
    above "Dec 2028" is the single fastest way to lose a reader's trust, so
    the dates decide the wording.
    """
    today = today or date.today()
    spans: list[tuple[date, date]] = []
    for node in nodes or []:
        a, b = _d(field_of(node, "start")), _d(field_of(node, "end"))
        if not a and not b:
            continue
        a = a or b
        b = b or a
        spans.append((a, b))
    if not spans:
        return {"state": "unknown", "opens": "", "opens_iso": "", "ends": ""}
    spans.sort()
    for a, b in spans:
        if a <= today <= b:
            return {"state": "running", "opens": _month_label(a),
                    "opens_iso": a.isoformat(), "ends": _month_label(b)}
    upcoming = [s for s in spans if s[0] > today]
    if upcoming:
        a, b = upcoming[0]
        return {"state": "upcoming", "opens": _month_label(a),
                "opens_iso": a.isoformat(), "ends": _month_label(b)}
    a, b = spans[-1]
    return {"state": "past", "opens": _month_label(a),
            "opens_iso": a.isoformat(), "ends": _month_label(b)}


def problem_nodes(nodes: list[Any]) -> list[Any]:
    """Nodes a reader would experience as a difficult stretch."""
    out = []
    for node in nodes or []:
        direction = str(field_of(node, "direction") or "").lower()
        try:
            bav = int(float(field_of(node, "bav", 0) or 0))
        except (TypeError, ValueError):
            bav = 0
        if direction in ("down", "caution") or (bav and bav <= 3):
            out.append(node)
    return out


def easing_note(nodes: list[Any], *, today: date | None = None) -> str:
    """When the difficult stretch lifts, in the reader's own timeline."""
    today = today or date.today()
    hard = problem_nodes(nodes)
    if not hard:
        return ""
    first_hard_start = min(
        (_d(field_of(n, "start")) or today) for n in hard
    )
    for node in sorted(nodes or [], key=lambda n: str(field_of(n, "start") or "")):
        if node in hard:
            continue
        start = _d(field_of(node, "start"))
        if not start or start < first_hard_start:
            continue
        if str(field_of(node, "direction") or "").lower() in ("up", "support", "mixed"):
            word = "opens up" if str(field_of(node, "direction")).lower() in ("up", "support") else "starts to ease"
            return f"This {word} from {_month_label(start)}."
    last_end = max((_d(field_of(n, "end")) or today) for n in hard)
    if last_end > today:
        return (
            f"The demanding stretch holds to {_month_label(last_end)}, so treat "
            f"the step below as the way through it rather than a quick fix."
        )
    return ""


def _pct(when: date, axis_start: date, axis_end: date) -> float:
    span = (axis_end - axis_start).days or 1
    return max(0.0, min(100.0, (when - axis_start).days / span * 100.0))


def _clip_bar(start, end, axis_start: date, axis_end: date) -> tuple[float, float] | None:
    a, b = _d(start), _d(end)
    if not a or not b:
        return None
    if b < axis_start or a > axis_end:
        return None
    left = _pct(max(a, axis_start), axis_start, axis_end)
    right = _pct(min(b, axis_end), axis_start, axis_end)
    width = max(2.0, right - left)
    if left + width > 100:
        width = 100.0 - left
    return round(left, 2), round(width, 2)


def _clip_named_periods(
    rows: list,
    axis_start: date,
    axis_end: date,
    *,
    kind: str,
    label_keys: tuple[str, ...],
    prefix: str,
    lord_key: str = "",
    limit: int = 4,
) -> list[dict]:
    out: list[dict] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        bar = _clip_bar(row.get("start"), row.get("end"), axis_start, axis_end)
        if not bar:
            continue
        name = ""
        for key in label_keys:
            name = str(row.get(key) or "").strip()
            if name:
                break
        if not name:
            continue
        lord = str(row.get(lord_key) or "").strip() if lord_key else ""
        label = f"{prefix} {name}".strip()
        if lord and lord.lower() not in label.lower():
            label = f"{label} ({lord})"
        out.append({
            "kind": kind,
            "label": label,
            "left_pct": bar[0],
            "width_pct": bar[1],
        })
        if len(out) >= limit:
            break
    return out


def build_transition_lanes(
    pc: dict,
    nodes: list[Any],
    *,
    area: str = "",
    context: list[Any] | None = None,
) -> dict[str, Any]:
    """Percent-positioned lanes for the horizontal map."""
    parsed: list[dict] = []
    for node in nodes or []:
        start = field_of(node, "start")
        end = field_of(node, "end")
        a, b = _d(start), _d(end)
        if not a and not b:
            continue
        parsed.append({
            "start": a or b,
            "end": b or a,
            "direction": str(field_of(node, "direction") or "mixed"),
            "phase": str(field_of(node, "phase") or ""),
            "meaning": str(field_of(node, "meaning") or ""),
            "planet": str(field_of(node, "planet") or ""),
            "score": float(field_of(node, "score") or 0.0),
            "event_type": str(field_of(node, "event_type") or ""),
            "overlap": list(field_of(node, "overlap") or []),
            "drivers": list(field_of(node, "drivers") or []),
            "raw": node,
        })
    if not parsed:
        return {}
    parsed.sort(key=lambda r: r["start"])
    axis_start = parsed[0]["start"]
    axis_end = max(r["end"] for r in parsed)
    if axis_end <= axis_start:
        axis_end = axis_start + timedelta(days=180)

    # Ticks sit on the window boundaries rather than on even intervals: an
    # interpolated month is a date this report never validated, and the date
    # guard would rightly soften it into "later in the cycle".
    ticks: list[dict] = []
    candidates = [r["start"] for r in parsed] + [axis_end]
    for when in sorted(set(candidates)):
        left = round(_pct(when, axis_start, axis_end), 2)
        if ticks and left - ticks[-1]["left_pct"] < 12:
            continue
        ticks.append({"label": _month_label(when), "left_pct": left})
    if len(ticks) > 1 and ticks[-1]["left_pct"] < 99:
        last = {"label": _month_label(axis_end), "left_pct": 100.0}
        if last["left_pct"] - ticks[-1]["left_pct"] < 12:
            ticks[-1] = last
        else:
            ticks.append(last)

    phases = []
    last_i = len(parsed) - 1
    for i, row in enumerate(parsed):
        bar = _clip_bar(row["start"], row["end"], axis_start, axis_end)
        if not bar:
            continue
        left, width = bar
        phases.append({
            "left_pct": left,
            "width_pct": width,
            "label": short_phase(row["phase"], last=(i == last_i), direction=row["direction"]),
            "phase": row["phase"],
            "direction": row["direction"],
            "caption": row["meaning"],
            "when": f"{_month_label(row['start'])} → {_month_label(row['end'])}",
        })

    dasha_bars = []
    vim = (pc or {}).get("vimshottari") or {}
    md = vim.get("current_md") or {}
    if isinstance(md, dict) and (md.get("md_lord") or md.get("lord")):
        bar = _clip_bar(md.get("start"), md.get("end"), axis_start, axis_end)
        if bar:
            lord = str(md.get("md_lord") or md.get("lord") or "")
            dasha_bars.append({
                "kind": "md",
                "label": f"{lord} MD",
                "left_pct": bar[0],
                "width_pct": bar[1],
            })
    for ad in list(vim.get("current_md_antardashas") or []):
        if not isinstance(ad, dict):
            continue
        bar = _clip_bar(ad.get("start"), ad.get("end"), axis_start, axis_end)
        if not bar:
            continue
        lord = str(ad.get("ad_lord") or ad.get("lord") or "")
        dasha_bars.append({
            "kind": "ad",
            "label": f"{lord} AD" if lord else "AD",
            "left_pct": bar[0],
            "width_pct": bar[1],
        })

    yogini_bars = _clip_named_periods(
        list(((pc or {}).get("yogini") or {}).get("full_cycle") or []),
        axis_start, axis_end,
        kind="yogini",
        label_keys=("yogini", "name"),
        prefix="Yogini",
        lord_key="lord",
        limit=4,
    )
    if not yogini_bars:
        cur = ((pc or {}).get("yogini") or {}).get("current_yogini") or {}
        if isinstance(cur, dict):
            yogini_bars = _clip_named_periods(
                [cur], axis_start, axis_end, kind="yogini",
                label_keys=("yogini", "name"), prefix="Yogini",
                lord_key="lord", limit=2,
            )
    chara_block = (pc or {}).get("chara_dasha") or {}
    if not isinstance(chara_block, dict) or not (chara_block.get("maha") or chara_block.get("antar")):
        nested = ((pc or {}).get("jaimini") or {}).get("chara_dasha") or {}
        if isinstance(nested, dict):
            chara_block = nested
    chara_bars = _clip_named_periods(
        list(chara_block.get("maha") or []),
        axis_start, axis_end,
        kind="chara",
        label_keys=("sign", "lord"),
        prefix="Chara",
        limit=3,
    )
    chara_antar = _clip_named_periods(
        list(chara_block.get("antar") or []),
        axis_start, axis_end,
        kind="chara",
        label_keys=("sign", "lord"),
        prefix="Chara",
        limit=3,
    )
    if chara_antar:
        chara_bars.extend(chara_antar)

    by_planet: dict[str, list] = {}
    for row in parsed:
        planet = row["planet"]
        if not planet:
            continue
        by_planet.setdefault(planet, []).append(row)
    transits = []
    for planet, group in by_planet.items():
        start = min(r["start"] for r in group)
        end = max(r["end"] for r in group)
        bar = _clip_bar(start, end, axis_start, axis_end)
        if not bar:
            continue
        word = "influence" if planet.lower() == "saturn" else "transit"
        transits.append({
            "label": f"{planet} {word}",
            "left_pct": bar[0],
            "width_pct": bar[1],
            "planet": planet,
        })

    # House ruler and dasha-lord stays. Only the ones that actually land on the
    # area's own house get a lane; the rest are listed under the map so the
    # dates are still on record without crowding the picture.
    context_bars: list[dict] = []
    context_rows: list[dict] = []
    for row in context or []:
        start = field_of(row, "start")
        end = field_of(row, "end")
        entry = {
            "planet": str(field_of(row, "planet") or ""),
            "role": str(field_of(row, "role") or ""),
            "sign": str(field_of(row, "sign") or ""),
            "house": int(field_of(row, "house", 0) or 0),
            "bav": int(field_of(row, "bav", 0) or 0),
            "tone": str(field_of(row, "tone") or "steady"),
            "major": bool(field_of(row, "major", False)),
            "in_house": bool(field_of(row, "in_house", False)),
            "when": f"{_month_label(start)} → {_month_label(end)}",
            "caption": transit_caption(row),
        }
        context_rows.append(entry)
        if not entry["major"]:
            continue
        bar = _clip_bar(start, end, axis_start, axis_end)
        if not bar:
            continue
        context_bars.append({
            "label": f"{entry['planet']} · house {entry['house']}" if entry["house"] else entry["planet"],
            "tone": entry["tone"],
            "role": entry["role"],
            "left_pct": bar[0],
            "width_pct": bar[1],
        })

    confluence = None
    ranked = sorted(
        parsed,
        key=lambda r: (
            1 if r["direction"] in ("up", "support") else 0,
            r["score"],
        ),
        reverse=True,
    )
    if ranked:
        pick = ranked[0]
        mid = pick["start"] + (pick["end"] - pick["start"]) / 2
        area_word = (area or str(field_of(pick["raw"], "area") or "")).replace("_", " ").title() or "This area"
        up = pick["direction"] in ("up", "support")
        caption = f"{area_word} opens" if up else f"{area_word} needs care"
        confluence = {
            "left_pct": round(_pct(mid, axis_start, axis_end), 2),
            "caption": caption,
            "when": _month_label(mid),
            # The marker is drawn at the middle of the stretch it points at, so
            # the caption alone reads as an undated flag. These are the dates
            # of that stretch, and they come from the timing row rather than
            # from the midpoint, so the date guard recognises them.
            "start": _month_label(pick["start"]),
            "end": _month_label(pick["end"]),
            "direction": "up" if up else "down",
        }

    return {
        "axis": {
            "start": axis_start.isoformat(),
            "end": axis_end.isoformat(),
            "ticks": ticks,
        },
        "phases": phases,
        "dasha": dasha_bars,
        "yogini": yogini_bars,
        "chara": chara_bars,
        "transits": transits,
        "context_bars": context_bars[:6],
        "context_rows": context_rows[:14],
        "confluence": confluence,
    }
