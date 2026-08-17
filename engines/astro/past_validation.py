"""Historical validation layer for Graharekha (V5.1).

The free past section builds trust through dated, multi-signal checkpoints.
It never asks the customer for dates first and never converts a single transit
into a claimed factual event.

Customer shape per event:
  WHEN -> AREA -> WHAT IT FELT LIKE -> HOW IT MAY HAVE SHOWN UP
  -> PLANETS -> TIMING -> HUMAN WHY -> optional ASTROLOGY detail
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional


AREA_NAMES = {
    "career": "work and career",
    "money": "money and financial decisions",
    "love": "relationships and partnership",
    "home": "home and family",
    "children": "children and creativity",
    "health": "health and energy",
    "learning": "learning and direction",
    "inner": "your peace of mind and spirituality",
}

# Headline (WHAT) + concrete manifestations (HOW IT MAY HAVE SHOWN UP).
PAST_PACK = {
    "career": {
        "up": {
            "headline": "Your work was easier to move forward, and people were more likely to notice you.",
            "manifest": [
                "additional responsibility or a wider role",
                "a senior person noticing your work",
                "a useful contact or conversation opening a door",
                "a project or decision finally moving after delay",
            ],
        },
        "mixed": {
            "headline": "Work became harder to ignore. Progress was possible, but it asked for extra effort.",
            "manifest": [
                "chasing a decision or approval",
                "carrying extra responsibility",
                "fixing something before progress showed",
                "pressure to make an important professional choice",
            ],
        },
        "down": {
            "headline": "Work asked more from you than usual. Pressure was clearer than ease.",
            "manifest": [
                "delays or blocked approvals",
                "a demanding person or heavier workload",
                "competition or comparison at work",
                "a problem that needed fixing before anything else moved",
            ],
        },
    },
    "money": {
        "up": {
            "headline": "Money matters felt more open. Useful decisions were easier to make.",
            "manifest": [
                "income, payment or reimbursement moving more easily",
                "a clearer financial decision",
                "a chance to strengthen your position",
                "less friction around paperwork or follow-ups",
            ],
        },
        "mixed": {
            "headline": "Money was moving, but not always staying where you wanted it.",
            "manifest": [
                "higher expenses or family commitments",
                "paperwork or account details needing attention",
                "a financial decision that needed patience",
                "income arriving in uneven patches",
            ],
        },
        "down": {
            "headline": "Money needed caution. Outgoings or uncertainty were harder to ignore.",
            "manifest": [
                "a larger expense arriving at a difficult moment",
                "delay around payment or approval",
                "financial pressure from family or work",
                "uncertainty about whether a decision was safe",
            ],
        },
    },
    "love": {
        "up": {
            "headline": "Relationships had more room to breathe and reconnect.",
            "manifest": [
                "a conversation that cleared the air",
                "warmer connection or reconciliation",
                "a commitment or next-step discussion",
                "easier goodwill after a tense phase",
            ],
        },
        "mixed": {
            "headline": "The relationship mattered more, but it was not completely effortless.",
            "manifest": [
                "a conversation that needed patience",
                "a small issue that had to be cleared up",
                "mixed signals that required careful talk",
                "more emotional attention than usual",
            ],
        },
        "down": {
            "headline": "Relationships needed more care. Distance or friction was harder to overlook.",
            "manifest": [
                "silence or emotional distance",
                "disagreement that took longer to settle",
                "uncertainty about where things stood",
                "a need to repair trust before moving forward",
            ],
        },
    },
    "home": {
        "up": {
            "headline": "Home and family felt steadier and easier to manage.",
            "manifest": [
                "a family matter settling",
                "a household or property decision moving",
                "more sense of stability at home",
                "support from someone close",
            ],
        },
        "mixed": {
            "headline": "Home and family took more of your attention.",
            "manifest": [
                "a recurring household issue",
                "family responsibility staying on your mind",
                "a property or living-arrangement matter",
                "the need to reorganise routines at home",
            ],
        },
        "down": {
            "headline": "Home life carried extra weight for a while.",
            "manifest": [
                "family pressure or obligation",
                "a property concern",
                "disruption to living arrangements",
                "needing to reorganise people or space",
            ],
        },
    },
    "children": {
        "up": {
            "headline": "Something around children, creativity or a personal project showed clearer movement.",
            "manifest": [
                "noticeable progress for a child or project",
                "encouragement that actually helped",
                "a study or creative milestone",
                "easier motivation around a personal goal",
            ],
        },
        "mixed": {
            "headline": "Progress around children or a personal project was uneven.",
            "manifest": [
                "needing patience more than pressure",
                "start-stop motivation",
                "a decision that could not be rushed",
                "extra attention to someone's development",
            ],
        },
        "down": {
            "headline": "A child-related matter or personal project needed more patience.",
            "manifest": [
                "delay or worry around progress",
                "added responsibility",
                "difficulty keeping momentum",
                "a personal project stalling despite effort",
            ],
        },
    },
    "health": {
        "up": {
            "headline": "Your energy was easier to manage and recover.",
            "manifest": [
                "better sleep or steadier energy",
                "recovery after a strained stretch",
                "routines that actually held",
                "feeling more capable day to day",
            ],
        },
        "mixed": {
            "headline": "Your energy was workable, but not unlimited.",
            "manifest": [
                "sleep or stress affecting capacity",
                "needing more recovery time",
                "pushing through while knowing you should rest",
                "routine slipping under pressure",
            ],
        },
        "down": {
            "headline": "Your body asked for more attention than usual.",
            "manifest": [
                "fatigue standing out more clearly",
                "disrupted sleep or routine",
                "stress showing up physically",
                "a health matter needing follow-up",
            ],
        },
    },
    "learning": {
        "up": {
            "headline": "Learning and new ideas moved more easily.",
            "manifest": [
                "a course, exam or useful connection opening up",
                "clearer guidance from someone senior",
                "a decision about your direction",
                "ideas converting into action",
            ],
        },
        "mixed": {
            "headline": (
                "Something you were trying to learn, understand or complete may have "
                "taken longer than expected."
            ),
            "manifest": [
                "having to revisit it or wait for the right guidance",
                "working harder than expected for a result",
                "uncertainty about the next skill to build",
                "a plan needing simplification before it could move",
            ],
        },
        "down": {
            "headline": "Progress in study or direction may have felt slower than you hoped.",
            "manifest": [
                "confusion about the next step",
                "delay getting guidance",
                "difficulty keeping momentum",
                "a plan needing simplification",
            ],
        },
    },
    "inner": {
        "up": {
            "headline": "You may have had more clarity about what actually matters to you.",
            "manifest": [
                "useful reflection or spiritual practice",
                "letting something unnecessary go",
                "wanting quieter routines",
                "a clearer sense of priorities",
            ],
        },
        "mixed": {
            "headline": (
                "You may have found yourself questioning where your time was going, "
                "wanting more personal space, or becoming less willing to spend energy "
                "on things that felt unnecessary."
            ),
            "manifest": [
                "questioning what deserves your energy",
                "wanting more space from noise",
                "trying to make peace with something unfinished",
                "mixed motivation socially or inwardly",
            ],
        },
        "down": {
            "headline": "You may have needed more quiet than usual.",
            "manifest": [
                "withdrawal from people or noise",
                "uncertainty about direction",
                "sleep disruption from mental load",
                "a strong need to step back before deciding",
            ],
        },
    },
}

DIRECTION_LABEL = {
    "up": "More supportive",
    "mixed": "Mixed period",
    "down": "More demanding",
}

_META_BULLET_MARKERS = (
    "timing activity without a confidently specific",
    "activity in this area without a clear single event",
)


def _is_meta_bullet(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in _META_BULLET_MARKERS)


def _pack_manifest_bullets(
    area: str,
    direction: str,
    meaning,
    gate: "ReportDiversityGate",
    row: dict,
) -> list[str]:
    """Area-specific concrete bullets when rubric path yields nothing."""
    pool = list((_pack(area, direction).get("manifest") or []))
    if not pool:
        return []
    seed = hash((
        area, direction, str(row.get("start")), row.get("planet"), row.get("house"),
    )) & 0xFFFF
    rotated = [pool[(seed + i) % len(pool)] for i in range(len(pool))]
    picked = gate.validate_bullets(rotated, meaning)
    if picked:
        return picked[:3]
    from qa_checks.age_context_check import age_violations
    from qa_checks.specificity import is_specific_enough
    from qa_checks.unsupported_claims import unsupported_event_detected

    for bullet in rotated:
        if _is_meta_bullet(bullet):
            continue
        if unsupported_event_detected(bullet, meaning.manifestations):
            continue
        if age_violations(bullet, meaning.age_band):
            continue
        if not is_specific_enough(bullet, minimum=3):
            continue
        return [bullet]
    return []


def _d(v: Any) -> Optional[date]:
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except (ValueError, TypeError):
        return None


def _range(a: Optional[date], b: Optional[date]) -> str:
    if not a or not b:
        return ""
    if a == b:
        return f"{a.day} {a:%B %Y}"
    if a.year == b.year and a.month == b.month:
        return f"{a.day}–{b.day} {b:%B %Y}"
    if a.year == b.year:
        return f"{a.day} {a:%B} – {b.day} {b:%B %Y}"
    return f"{a.day} {a:%B %Y} – {b.day} {b:%B %Y}"


def _clip(a: Optional[date], b: Optional[date], start: date, end: date):
    if not a or not b or b < start or a > end:
        return None
    return max(a, start), min(b, end)


def _area_map():
    import report_cards as RC
    return [(a.key, a.house, a.label) for a in RC.AREAS]


def _extra_house_areas() -> list[tuple[str, int, str]]:
    """Classical house links used only for dated past checkpoints.

    These do not change card engines. They only let a real slow-planet
    transit that activates a traditional correlative house surface as a
    checkable window (e.g. 3rd = skills / communication / initiative).
    """
    return [
        ("learning", 3, "Learning & communication"),
        ("money", 11, "Gains & opportunities"),
        ("health", 8, "Recovery & resilience"),
    ]


def _vim_segments(pc: dict, start: date, end: date) -> list[dict]:
    """Historical Vimshottari MD/AD envelopes overlapping [start, end]."""
    import astro_precompute as AP

    vim = pc.get("vimshottari") or {}
    out = []
    md_lord = (vim.get("current_md") or {}).get("md_lord", "")
    for ad in (vim.get("current_md_antardashas") or []):
        a, b = _d(ad.get("start")), _d(ad.get("end"))
        c = _clip(a, b, start, end)
        if c:
            out.append({
                "start": c[0], "end": c[1],
                "md": md_lord or ad.get("md_lord", ""),
                "ad": ad.get("ad_lord", ""),
                "ad_start": a,
            })
    if out:
        out.sort(key=lambda x: x["start"])
        return out

    sequence = vim.get("sequence") or []
    lords = list(getattr(AP, "VIMSH_LORDS", ()))
    for md in sequence:
        ms, me = _d(md.get("start")), _d(md.get("end"))
        if not _clip(ms, me, start, end):
            continue
        md_lord = md.get("md_lord", "")
        try:
            ads = AP.build_antardashas(md, lords.index(md_lord))
        except Exception:
            ads = []
        for ad in ads:
            a, b = _d(ad.get("start")), _d(ad.get("end"))
            c = _clip(a, b, start, end)
            if c:
                out.append({"start": c[0], "end": c[1], "md": md_lord,
                            "ad": ad.get("ad_lord", ""), "ad_start": a})
    out.sort(key=lambda x: x["start"])
    return out


def _direction(row: dict) -> str:
    promise = row.get("promise", "mixed")
    dasha = row.get("dasha", "mixed")
    bav = int(row.get("bav", 0) or 0)
    planet = row.get("planet", "")
    if promise != "down" and dasha != "down" and bav >= 5:
        return "up"
    if promise == "down" and dasha == "down":
        return "down"
    if bav <= 3 and (promise == "down" or dasha == "down"):
        return "down"
    if planet == "Saturn" and (promise == "down" or dasha == "down"):
        return "down"
    return "mixed"


def _touches_area(pc: dict, planet: str, house: int) -> bool:
    if not planet:
        return False
    hl = (pc.get("house_lords") or {}).get(str(house)) or {}
    if hl.get("lord") == planet:
        return True
    return (pc.get("planets") or {}).get(planet, {}).get("house") == house


def _varga_leans(area: str) -> str:
    try:
        import deep_evidence as DE
        varga = (DE.for_area(area) or {}).get("varga") or {}
        return str(varga.get("strength") or "mixed")
    except Exception:  # noqa: BLE001
        return "mixed"


def _internal_score(pc: dict, row: dict, dasha: dict, area: str,
                    house: int) -> int:
    """Spec section 4 multi-signal score. Customer never sees the number."""
    score = 0
    promise = row.get("promise", "mixed")
    if promise in ("up", "down"):
        score += 1

    vim = dasha.get("vim") or {}
    md, ad = vim.get("md", ""), vim.get("ad", "")
    if _touches_area(pc, md, house):
        score += 1
    if _touches_area(pc, ad, house):
        score += 1

    planet = row.get("planet", "")
    if planet in ("Jupiter", "Saturn", "Rahu", "Ketu"):
        score += 1

    bav = int(row.get("bav", 0) or 0)
    if bav >= 5 or bav <= 3:
        score += 1

    vstrength = _varga_leans(area)
    if vstrength in ("strong", "weak"):
        score += 1

    # Support houses counting as soft MD/AD relevance.
    try:
        import report_cards as RC
        area_obj = next((a for a in RC.AREAS if a.key == area), None)
        supports = tuple(area_obj.support) if area_obj else ()
    except Exception:  # noqa: BLE001
        supports = ()
    for h in supports:
        if _touches_area(pc, md, h) or _touches_area(pc, ad, h):
            score += 1
            break

    agreement = dasha.get("agreement")
    try:
        agree_n = int(agreement)
    except (TypeError, ValueError):
        agree_n = 2 if dasha.get("unanimous") else 0
    if dasha.get("unanimous") or agree_n >= 2:
        score += 1

    return score


def _confidence_label(points: int, direction: str) -> str:
    if points >= 7:
        return "Strong indication"
    if points >= 5:
        return "Good indication"
    if direction == "mixed":
        return "Mixed period"
    return "Possible"


def _human_why(row: dict, dasha: dict, direction: str) -> str:
    planet = row.get("planet", "")
    area = AREA_NAMES.get(row.get("area", ""), "this area")
    bav = int(row.get("bav", 0) or 0)
    promise = row.get("promise", "mixed")

    planet_clause = {
        "Jupiter": f"Jupiter was bringing more attention to {area}",
        "Saturn": f"Saturn was making {area} slower and more demanding",
    }.get(planet, f"{planet} was activating {area}" if planet else
                  f"Timing was focused on {area}")

    if promise == "up" and bav >= 5:
        chart_clause = "Your birth chart already supports movement here"
    else:
        chart_clause = (
            "This area looks mixed for you. There is support, "
            "but it is not completely smooth"
        )

    feel = {
        "up": "so this was more likely to show as progress than as a dead end",
        "down": ("so this was more likely to feel like something that needed "
                 "attention than like an effortless phase"),
        "mixed": "so this was more likely to feel active than settled",
    }.get(direction, "so this was more likely to feel active than settled")

    agree = ""
    if dasha.get("unanimous"):
        agree = " Several timing systems also pointed in the same direction."

    return f"{planet_clause}. {chart_clause}, {feel}.{agree}"


def _astro_why(row: dict, dasha: dict) -> str:
    from report_language import house_ordinal, fix_house_ordinals
    planet = row.get("planet", "")
    vim = dasha.get("vim") or {}
    bits = []
    if planet:
        bits.append(f"{planet} transit")
    if vim.get("md") and vim.get("ad"):
        bits.append(f"{vim['md']}–{vim['ad']} period")
    house = row.get("house")
    if house:
        bits.append(f"{house_ordinal(house)}-house activation")
    return fix_house_ordinals(" + ".join(bits) if bits else "dated transit and running period")


def _render_past_copy(
    pc: dict,
    *,
    area: str,
    house: int,
    direction: str,
    row: dict,
    dasha: dict,
    gate: "ReportDiversityGate",
    today: date,
) -> tuple[str, list[str]]:
    """Evidence → meaning → QA → headline + manifest bullets."""
    from interpretation.evidence_builder import build_evidence
    from interpretation.life_stage import age_band_at
    from interpretation.prediction_meaning import build_meaning
    from narration.human_renderer import render_manifest_bullets, transparent_headline
    from qa_checks.specificity import is_specific_enough

    start = row.get("start")
    band = age_band_at(pc, start if hasattr(start, "year") else today)
    try:
        from datetime import date as _date
        if isinstance(start, str):
            start = _date.fromisoformat(start[:10])
            band = age_band_at(pc, start)
    except Exception:  # noqa: BLE001
        pass
    evidence = build_evidence(
        pc, area=area, house=house, direction=direction,
        row=row, dasha=dasha, age_band=band,
        period_start=start, period_end=row.get("end"))
    meaning = build_meaning(evidence)
    headline, meaning = gate.validate_headline("", meaning, past=True)
    manis = render_manifest_bullets(meaning, n=4, paid=True)
    manis = [m for m in gate.validate_bullets(manis, meaning) if not _is_meta_bullet(m)]
    if not is_specific_enough(headline, minimum=3):
        headline = transparent_headline(paid=True)
    if not manis:
        manis = _pack_manifest_bullets(area, direction, meaning, gate, row)
    manis = [m for m in manis if not _is_meta_bullet(m)][:3]
    return headline, manis


def _pack(area: str, direction: str) -> dict:
    bucket = PAST_PACK.get(area) or {}
    packed = bucket.get(direction)
    if packed:
        return packed
    return {
        "headline": (
            "The timing is active, but the chart does not provide enough evidence "
            "to describe one specific event with confidence."
        ),
        "manifest": [
            "a follow-up or decision that needed patience",
            "responsibility staying on your mind during this stretch",
            "something in this area asking for extra attention",
        ],
    }


def build(pc: dict, *, today: Optional[date] = None,
          months: int = 6, max_events: int = 5) -> dict:
    """Select dated, multi-signal six-month history for the free trust layer."""
    today = today or date.today()
    start = today - timedelta(days=30 * months)

    import report_timing as RT
    import report_confluence as CF
    import report_cards as RC
    from interpretation.life_stage import age_band, age_band_at
    from narration.area_labels import area_label as _age_area_label
    from qa_checks.report_diversity import ReportDiversityGate

    gate = ReportDiversityGate()
    band = age_band(pc, today=today)
    segments = RT.transit_segments(pc, start=start - timedelta(days=45), years=1)
    events: list[dict] = []

    area_houses: list[tuple[str, int, str]] = []
    for area, house, label in list(_area_map()) + _extra_house_areas():
        area_houses.append((area, house, label))
        area_obj = next((a for a in RC.AREAS if a.key == area), None)
        for h in (area_obj.support if area_obj else ()):
            area_houses.append((area, int(h), label))

    seen_window: set[tuple] = set()
    for area, house, label in area_houses:
        try:
            rows = RT.windows_for_area(
                pc, area, house, start=start - timedelta(days=45), years=1,
                segments=segments)
        except Exception:  # noqa: BLE001
            rows = []

        for row in rows:
            clipped = _clip(_d(row.get("start")), _d(row.get("end")), start, today)
            if not clipped:
                continue
            s, e = clipped
            wkey = (area, s, e, row.get("planet"))
            if wkey in seen_window:
                continue
            seen_window.add(wkey)
            row = dict(row)
            row["area"] = area
            row["house"] = house

            dasha = CF.dasha_confluence(pc, s)
            points = _internal_score(pc, row, dasha, area, house)
            if points < 2:
                continue
            # Prefer multi-signal reads. Points >= 2 means at least two
            # independent chart cues already agreed — enough to show without
            # inventing an event.

            direction = _direction(row)
            try:
                headline, manis = _render_past_copy(
                    pc, area=area, house=house, direction=direction,
                    row=row, dasha=dasha, gate=gate, today=today)
            except Exception:  # noqa: BLE001
                pack = _pack(area, direction)
                headline = pack["headline"]
                manis = list(pack.get("manifest") or [])[:4]
            display_label = _age_area_label(area, age_band_at(pc, s))
            planets = []
            for p in (row.get("planet"), (dasha.get("vim") or {}).get("md"),
                      (dasha.get("vim") or {}).get("ad")):
                if p and p not in planets:
                    planets.append(p)

            events.append({
                "start": s, "end": e,
                "area": area, "label": display_label,
                "direction": direction,
                "direction_label": DIRECTION_LABEL[direction],
                "headline": headline,
                "why": headline,
                "manifests": manis,
                "astro_why": _astro_why(row, dasha),
                "planets": planets,
                "dasha": "–".join(
                    p for p in ((dasha.get("vim") or {}).get("md"),
                                (dasha.get("vim") or {}).get("ad")) if p),
                "signal": _confidence_label(points, direction),
                "score": points,
                "source": "multi-signal past validation",
            })

    hl = pc.get("house_lords") or {}
    planets = pc.get("planets") or {}
    previous = None
    for seg in _vim_segments(pc, start - timedelta(days=120), today):
        key = (seg["md"], seg["ad"])
        if previous and previous != key:
            md, ad = key
            ad_start = seg.get("ad_start") or seg["start"]
            if start <= ad_start <= today:
                touched = []
                for a in RC.AREAS:
                    for p in (md, ad):
                        if ((hl.get(str(a.house), {}) or {}).get("lord") == p
                                or (planets.get(p, {}) or {}).get("house")
                                == a.house):
                            touched.append(a)
                            break
                if touched:
                    a = touched[0]
                    evt_band = age_band_at(pc, ad_start)
                    evt_label = _age_area_label(a.key, evt_band)
                    evt_area_name = _age_area_label(a.key, evt_band).lower()
                    events.append({
                        "start": ad_start, "end": min(seg["end"], today),
                        "area": a.key, "label": evt_label,
                        "direction": "mixed",
                        "direction_label": DIRECTION_LABEL["mixed"],
                        "headline": (
                            f"Your focus around {evt_area_name} "
                            f"may have shifted when the {md}–{ad} period began."
                        ),
                        "why": (
                            f"Your focus around {evt_area_name} "
                            f"may have shifted when the {md}–{ad} period began."
                        ),
                        "manifests": [
                            "a shift in what needed attention during this period",
                            "priorities rearranging without one dramatic day",
                        ],
                        "astro_why": f"{md}–{ad} period change",
                        "planets": [p for p in (md, ad) if p],
                        "dasha": f"{md}–{ad}",
                        "signal": "Good indication",
                        "score": 5,
                        "source": "Vimshottari transition",
                    })
        previous = key

    events.sort(key=lambda x: (-x["score"], x["start"]))
    picked: list[dict] = []
    seen_areas: set[str] = set()
    seen_windows: set[tuple] = set()

    def _wkey(ev: dict) -> tuple:
        planets = tuple(ev.get("planets") or [])
        return (ev["start"], ev["end"], planets)

    for ev in events:
        wk = _wkey(ev)
        if wk in seen_windows:
            continue
        # Prefer area diversity first, then allow a second hit in a strong area.
        if ev["area"] in seen_areas and len(picked) < 3:
            continue
        picked.append(ev)
        seen_areas.add(ev["area"])
        seen_windows.add(wk)
        if len(picked) >= max_events:
            break

    if len(picked) < min(3, max_events):
        chosen = {id(x) for x in picked}
        for ev in sorted(events, key=lambda x: (-x["score"], x["start"])):
            if id(ev) in chosen:
                continue
            wk = _wkey(ev)
            if wk in seen_windows:
                continue
            if any(abs((ev["start"] - p["start"]).days) < 10
                   and ev["area"] == p["area"] for p in picked):
                continue
            picked.append(ev)
            seen_windows.add(wk)
            if len(picked) >= max_events:
                break

    # Still short? allow one more transition/window that is spaced out.
    if len(picked) < min(3, max_events):
        chosen = {id(x) for x in picked}
        for ev in sorted(events, key=lambda x: (-x["score"], x["start"])):
            if id(ev) in chosen:
                continue
            wk = _wkey(ev)
            if wk in seen_windows:
                continue
            if any(abs((ev["start"] - p["start"]).days) < 7 for p in picked):
                continue
            picked.append(ev)
            seen_windows.add(wk)
            if len(picked) >= min(3, max_events):
                break

    picked.sort(key=lambda x: x["start"])
    return {"today": today, "since": start, "events": picked}


def render(block: dict) -> str:
    if not block or not block.get("events"):
        return ""
    import html

    rows = []
    for ev in block["events"]:
        headline = ev.get("headline") or ""
        manis = list(ev.get("manifests") or [])[:4]
        # Deduplicate bullets that already appear verbatim in the headline.
        hl_l = headline.lower()
        noticed = []
        for m in manis:
            if m and not _is_meta_bullet(m) and m.lower() not in hl_l:
                noticed.append(m)
        if not noticed:
            noticed = [m for m in manis[:3] if m and not _is_meta_bullet(m)]
        bullets = "".join(
            f"<li>{html.escape(m)}</li>" for m in noticed)
        noticed_html = ""
        if bullets:
            noticed_html = (
                '<div class="past-noticed">'
                '<div class="ev-label">You may have noticed this as</div>'
                f'<ul>{bullets}</ul></div>')
        rows.append(f"""
        <article class="past-event {html.escape(ev['direction'])}">
          <div class="past-date">{html.escape(_range(ev['start'], ev['end']))}</div>
          <div class="past-main">
            <div class="past-title">{html.escape(ev['label'])}
              <span class="past-signal">{html.escape(ev.get('signal',''))}</span></div>
            <div class="past-headline">{html.escape(headline)}</div>
            {noticed_html}
            <details class="past-astro">
              <summary>Why this period?</summary>
              <p><b>Planets:</b> {html.escape(" · ".join(ev.get("planets") or []) or "—")}<br/>
              <b>Timing:</b> {html.escape(ev.get("dasha") or "—")}<br/>
              {html.escape(ev.get("astro_why") or "")}</p>
            </details>
          </div>
        </article>""")

    return f"""
<section class="proof past-validation">
  <div class="present-head">
    <span class="ev-label">Recent past · free and checkable</span>
    <h3>Did these things happen in the last six months?</h3>
  </div>
  <p class="present-lede">These are specific time windows from your chart, not
  general personality statements. We only show a window when more than one part
  of the chart points to the same part of life.</p>
  <div class="past-timeline">{''.join(rows)}</div>
  <div class="present-ask">
    <span>How closely did this match your life?</span>
    <button type="button" class="pillbtn" data-mm="yes">Yes, closely</button>
    <button type="button" class="pillbtn" data-mm="partly">Partly</button>
    <button type="button" class="pillbtn" data-mm="no">Not at all</button>
  </div>
</section>"""
