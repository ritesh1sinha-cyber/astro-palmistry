"""Unified per-area confluence report — one contract for cards and Q&A.

Inputs (engine-only): house lord, karaka, Vim/Jaimini/Yogini, SAV, varga,
transit, multi-method votes, area timing window.

Customer output: prediction + 1–2 line proof + when + remedy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Optional

from report_language import (
    client_prose,
    fix_house_ordinals,
    humanise_client_language,
    strip_visible_claim_jargon,
)

VARGA_PLAIN = {
    "career": "career chart",
    "money": "wealth chart",
    "love": "marriage chart",
    "home": "home chart",
    "children": "children chart",
    "health": "health chart",
    "learning": "learning chart",
    "inner": "spiritual chart",
}

SAV_WORD = {
    "high": "well supported",
    "low": "under strain",
    "mid": "average support",
}

ACTIONS: dict[str, str] = {
    # Legacy domain-blind slogans — DO NOT use for per-area "What helps".
    # Kept only so old imports/tests that reference the name do not break.
    "Sun": "Deal directly with whoever actually decides. This stalls one level below the authority.",
    "Moon": "Protect your sleep and your home routine. Your focus is downstream of both.",
    "Mars": "Do not escalate this month. Let the other side move first.",
    "Mercury": "Put it in writing. The misunderstanding here is in the wording, not the intent.",
    "Jupiter": "Ask someone senior to speak for you. This opens through a sponsor.",
    "Venus": "Repair the relationship before pressing the request again.",
    "Saturn": "Finish the boring, verifiable part first. Saturn only blocks what is half-done.",
    "Rahu": "Verify the thing that looks too convenient.",
    "Ketu": "Step back for a fortnight. This one loosens when you stop gripping it.",
}

# Classical planet upaya (shared wording with house_confluence_report).
CLASSICAL_UPAYA: dict[str, str] = {
    "Sun": "Offer water to the rising Sun and respect father-figures; "
           "strengthen confidence with the Sun's mantra on Sundays.",
    "Moon": "Keep a calm routine and good sleep; honour your mother and "
            "offer something white on Mondays to steady the mind.",
    "Mars": "Channel energy through exercise and discipline; serve siblings "
            "and avoid rash anger on Tuesdays.",
    "Mercury": "Read, write and learn daily; keep your word and donate green "
               "items / help students on Wednesdays.",
    "Jupiter": "Seek a teacher's guidance and give to genuine causes; honour "
               "elders and study scripture on Thursdays.",
    "Venus": "Cultivate kindness and beauty in your home; respect your "
             "partner and offer something fragrant on Fridays.",
    "Saturn": "Be patient, consistent and of service to workers and elders; "
              "keep commitments and help the needy on Saturdays.",
    "Rahu": "Avoid shortcuts and intoxicants; keep clean routines and serve "
            "the marginalised to settle a restless mind.",
    "Ketu": "Keep a simple spiritual practice and let go of what is past; "
            "charity to the devout steadies this energy.",
}

MANTRA = {
    "Sun": "Om Suryaya Namah at sunrise", "Moon": "Om Chandraya Namah on Mondays",
    "Mars": "Om Angarakaya Namah on Tuesdays", "Mercury": "Om Budhaya Namah on Wednesdays",
    "Jupiter": "Om Gurave Namah on Thursdays", "Venus": "Om Shukraya Namah on Fridays",
    "Saturn": "Om Sham Shanaishcharaya Namah on Saturdays",
    "Rahu": "Om Rahave Namah on Saturday evenings",
    "Ketu": "Om Ketave Namah on Tuesday evenings",
}

# Primary house + support houses (must match report_cards.AREAS).
_AREA_HOUSES: dict[str, tuple[int, tuple[int, ...]]] = {
    "career": (10, (6, 11)),
    "money": (2, (11,)),
    "love": (7, (5,)),
    "home": (4, (2,)),
    "children": (5, (9,)),
    "health": (1, (6, 8)),
    "learning": (9, (5,)),
    "inner": (12, (9,)),
}

# Natural significators consulted when an area is under strain.
_AREA_NATURAL: dict[str, tuple[str, ...]] = {
    "health": ("Sun", "Moon", "Mars"),
    "career": ("Sun", "Saturn", "Mercury"),
    "money": ("Jupiter", "Venus"),
    "love": ("Venus", "Jupiter"),
    "home": ("Moon", "Mars", "Venus"),
    "children": ("Jupiter", "Mercury"),
    "learning": ("Jupiter", "Mercury"),
    "inner": ("Ketu", "Jupiter", "Saturn"),
}

_WEAK_DIGNITY = {
    "exalted": -2, "moolatrikona": -2, "own_sign": -1.5, "own sign": -1.5,
    "friendly_sign": -1, "friend": -1, "neutral_sign": 0, "neutral": 0,
    "enemy_sign": 1, "enemy": 1, "debilitated": 2,
}

_DIGNITY_PLAIN = {
    "exalted": "strong", "moolatrikona": "strong", "own_sign": "strong",
    "own sign": "strong", "friendly_sign": "comfortable", "friend": "comfortable",
    "neutral_sign": "mixed", "neutral": "mixed",
    "enemy_sign": "strained", "enemy": "strained", "debilitated": "weak",
}


@dataclass
class AreaReport:
    area: str
    direction: str
    prediction: str
    proof: str
    when: str
    remedy: str
    confidence: str
    score: float = 0.0


def _ord(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    return f"{n}" + ("th" if 10 <= n % 100 <= 20
                     else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def _d(value: Any) -> Optional[date]:
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _pretty(d: Optional[date]) -> str:
    return f"{d:%b %Y}".replace(" 0", " ") if d else ""


def _window_label(start: Any, end: Any, today: Optional[date] = None) -> str:
    today = today or date.today()
    a, b = _d(start), _d(end)
    if not b:
        return ""
    if a and a <= today <= b:
        return f"Now → {_pretty(b)}"
    return f"{_pretty(a)} → {_pretty(b)}"


def _dig_plain(code: str) -> str:
    return _DIGNITY_PLAIN.get((code or "").lower().replace(" ", "_"), "mixed")


def _sav_word(pc: dict, house: int) -> str:
    sav = (pc.get("ashtakavarga", {}) or {}).get("sav") or []
    if len(sav) < house:
        return ""
    v = sav[house - 1]
    if v >= 30:
        return SAV_WORD["high"]
    if v <= 25:
        return SAV_WORD["low"]
    return SAV_WORD["mid"]


def _area_when(pc: dict, area_key: str, house: int, *,
               today: Optional[date] = None) -> str:
    """Best dated window for this area, not the global AD."""
    today = today or date.today()
    try:
        import deep_evidence as DE
        de = DE.for_area(area_key, house=house)
        cw = de.get("current_window") or {}
        if cw.get("period"):
            return str(cw["period"]).replace(" – ", " → ")
        for w in (de.get("windows") or []):
            if w.get("now"):
                return str(w.get("period", "")).replace(" – ", " → ")
    except Exception:  # noqa: BLE001
        pass

    try:
        import report_timing as RT
        rows = RT.windows_for_area(pc, area_key, house, start=today, years=3)
        if rows:
            best = max(rows, key=lambda r: r.get("score", 0))
            return _window_label(best.get("start"), best.get("end"), today)
    except Exception:  # noqa: BLE001
        pass

    try:
        import report_confluence as CF
        vim = CF.vimshottari_at(pc, today)
        ad_rows = (pc.get("vimshottari", {}) or {}).get("current_md_antardashas") or []
        for ad in ad_rows:
            if ad.get("status") == "current":
                return _window_label(ad.get("start"), ad.get("end"), today)
        md = (pc.get("vimshottari", {}) or {}).get("current_md", {}) or {}
        return _window_label(md.get("start"), md.get("end"), today)
    except Exception:  # noqa: BLE001
        return ""


def _build_proof(pc: dict, area_key: str, house: int, *,
                   today: Optional[date] = None,
                   direction: str = "mixed",
                   confidence: str = "") -> str:
    """Structured Why block for expandable evidence — engine facts only."""
    today = today or date.today()
    area_name = {
        "career": "career and public standing",
        "money": "money and resources",
        "love": "relationships and partnership",
        "home": "home and family",
        "children": "children and creativity",
        "health": "health and vitality",
        "learning": "learning and direction",
        "inner": "inner life and space",
    }.get(area_key, "this area")
    lines: list[str] = []

    # Birth chart / specialised support — human English, no contradictions.
    chart_label = {
        "career": "Career", "money": "Money", "love": "Relationship",
        "home": "Home", "children": "Children and creativity",
        "health": "Health and energy", "learning": "Learning",
        "inner": "Inner life",
    }.get(area_key, area_name.title())
    strength = ""
    fld = ""
    dig = ""
    try:
        import deep_evidence as DE
        de = DE.for_area(area_key, house=house)
        varga = de.get("varga") or {}
        strength = (varga.get("strength") or "").lower()
        fld = varga.get("field_lord") or varga.get("ruler", "")
        dig = _dig_plain(varga.get("field_lord_dignity")
                         or varga.get("ruler_dignity", ""))
    except Exception:  # noqa: BLE001
        pass

    sav = _sav_word(pc, house)
    if strength in ("strong", "favourable", "up") and sav == "under strain":
        birth = (f"{chart_label} has a supportive foundation, although some "
                 f"underlying factors make progress more gradual")
    elif strength in ("strong", "favourable", "up") or sav == "well supported":
        birth = (f"{chart_label} has a generally solid foundation"
                 + (", although some factors can create periods of fluctuation"
                    if dig == "mixed" else ""))
    elif strength in ("weak", "challenging", "down") or sav == "under strain":
        birth = (f"{chart_label} needs more care right now; progress is "
                 f"possible but less automatic")
    elif fld:
        birth = (f"{chart_label} has mixed underlying support"
                 + (f", with {fld} playing a key role" if fld else ""))
    else:
        birth = f"{chart_label} has mixed underlying support"
    lines.append(f"Birth chart: {birth.rstrip('.')}.")

    # Current timing
    timing = ""
    secondary = ""
    try:
        import report_confluence as CF
        vim = CF.vimshottari_at(pc, today) or {}
        yog = CF.yogini_at(pc, today) or {}
        if vim.get("md") and vim.get("ad"):
            timing = f"{vim['md']}–{vim['ad']} is active"
        if yog.get("lord"):
            secondary = (
                f"Another timing method also points toward {yog['lord']}")
    except Exception:  # noqa: BLE001
        pass
    if timing:
        lines.append(f"Current timing: {timing}.")

    # Transit
    transit_line = ""
    try:
        import deep_evidence as DE
        tr = (DE.for_area(area_key, house=house).get("transit") or {})
        if tr.get("support"):
            transit_line = humanise_client_language(str(tr["support"][0])[:120])
        elif tr.get("pressure"):
            transit_line = humanise_client_language(str(tr["pressure"][0])[:120])
    except Exception:  # noqa: BLE001
        pass
    if not transit_line:
        try:
            import report_timing as RT
            segs = RT.transit_segments(
                pc, start=today - timedelta(days=30), years=1)
            hits = []
            for planet, arr in (segs or {}).items():
                for seg in arr or []:
                    if (seg.get("house") == house
                            and seg.get("start") <= today <= seg.get("end")):
                        hits.append(planet)
            if hits:
                transit_line = (
                    f"{' and '.join(hits)} currently influencing the "
                    f"{area_name} area")
        except Exception:  # noqa: BLE001
            pass
    if transit_line:
        lines.append(f"Transit: {transit_line.rstrip('.')}.")

    if secondary:
        lines.append(f"Secondary confirmation: {secondary.rstrip('.')}.")

    agree = {
        "strong agreement": "Overall: Strong agreement.",
        "strong": "Overall: Strong agreement.",
        "strong read": "Overall: Strong agreement.",
        "moderate agreement": "Overall: Partial agreement.",
        "partial agreement": "Overall: Partial agreement.",
        "mixed evidence": "Overall: Mixed evidence.",
        "mixed read": "Overall: Mixed evidence.",
        "mixed": "Overall: Mixed evidence.",
        "split read": "Overall: Mixed evidence.",
        "cautious read": "Overall: Partial agreement.",
        "demanding read": "Overall: Mixed evidence.",
    }.get((confidence or "").lower())
    if not agree:
        if direction == "mixed":
            agree = "Overall: Mixed evidence."
        elif direction == "up":
            agree = "Overall: Partial agreement."
        else:
            agree = "Overall: Mixed evidence."
    lines.append(agree)

    return fix_house_ordinals("\n".join(lines))


def _planet_stress(pc: dict, planet: str) -> float:
    """Higher = more under strain (used to pick which planet the area remedy targets)."""
    if not planet:
        return -99.0
    planets = pc.get("planets") or {}
    info = planets.get(planet) or {}
    dig = str(info.get("dignity") or info.get("sign_dignity") or "").lower()
    score = float(_WEAK_DIGNITY.get(dig.replace(" ", "_"), 0))
    # Fall back to house-lord row dignity when planet table is thin.
    if score == 0.0 and dig == "":
        for hinfo in (pc.get("house_lords") or {}).values():
            if isinstance(hinfo, dict) and hinfo.get("lord") == planet:
                dig2 = str(hinfo.get("lord_dignity") or "").lower()
                score = float(_WEAK_DIGNITY.get(dig2.replace(" ", "_"), 0))
                house = hinfo.get("lord_house")
                if house in (6, 8, 12):
                    score += 1.0
                break
    house = info.get("house")
    if house in (6, 8, 12):
        score += 1.0
    return score


def _stress_planet_for_area(pc: dict, area_key: str, house: int) -> str:
    """Planet to remedy for this life area — house lord / support lords / natural karakas.

    Never the bare running dasha lord alone: that made Health show Venus's
    relationship slogan whenever Venus was the current antardasha.
    """
    primary, support = _AREA_HOUSES.get(area_key, (house, ()))
    houses = (primary,) + tuple(support)
    hl = pc.get("house_lords") or {}
    candidates: list[str] = []
    for h in houses:
        lord = (hl.get(str(h)) or {}).get("lord") or ""
        if lord:
            candidates.append(lord)
    for pl in _AREA_NATURAL.get(area_key, ()):
        candidates.append(pl)

    # Dasha lords only if they touch this area (rule the house or sit there).
    vim = pc.get("vimshottari") or {}
    md = (vim.get("current_md") or {}).get("md_lord") or ""
    ad = ""
    for row in vim.get("current_md_antardashas") or []:
        if row.get("status") == "current":
            ad = row.get("ad_lord") or ""
            break
    planets = pc.get("planets") or {}
    for pl in (ad, md):
        if not pl:
            continue
        sits = (planets.get(pl) or {}).get("house")
        rules = any((hl.get(str(h)) or {}).get("lord") == pl for h in houses)
        if rules or sits in houses:
            candidates.append(pl)

    # Prefer the most stressed candidate; house lord of the primary house
    # wins ties so the remedy stays tied to this area.
    primary_lord = (hl.get(str(primary)) or {}).get("lord") or ""
    best, best_score = "", -99.0
    for pl in candidates:
        s = _planet_stress(pc, pl)
        if pl == primary_lord:
            s += 0.15  # mild bias to the area's own lord on ties
        if s > best_score:
            best, best_score = pl, s
    return best or primary_lord


def classical_area_remedy(pc: dict, area_key: str, house: int, direction: str) -> str:
    """Rule-backed classical upaya for the stressed planet of this area."""
    if direction == "up":
        return ""
    planet = _stress_planet_for_area(pc, area_key, house)
    if not planet:
        return ""
    body = CLASSICAL_UPAYA.get(planet, "")
    mantra = MANTRA.get(planet, "")
    parts: list[str] = []
    if body:
        parts.append(f"Support {planet}: {body}")
    elif mantra:
        parts.append(f"Support {planet}.")
    if mantra:
        parts.append(f"Mantra: {mantra}.")
    try:
        from gemstone_remedy import _gem_safety
        ev = _gem_safety(pc, planet, role=f"{area_key} area")
        verdict = str(ev.get("verdict") or "")
        gem = (ev.get("gem") or {}).get("gem") or ""
        if verdict == "avoid" and gem:
            parts.append(f"Do not wear {gem} for {planet} — mantra and charity only.")
        elif verdict == "mantra_only":
            parts.append(f"No primary gem for {planet} — mantra and charity only.")
        elif verdict in ("recommended", "test_required") and gem:
            day = (ev.get("gem") or {}).get("day") or ""
            finger = (ev.get("gem") or {}).get("finger") or ""
            bits = [gem]
            if finger:
                bits.append(finger)
            if day:
                bits.append(f"first on a {day}")
            parts.append(f"If a stone is used: {' · '.join(bits)}.")
    except Exception:  # noqa: BLE001
        pass
    return client_prose(" ".join(parts).strip())


def _area_remedy(pc: dict, area_key: str, house: int, direction: str, *,
                   question: str = "") -> tuple[str, str]:
    """Classical upaya for this area's stressed planet — not dasha slogans."""
    _ = question  # reserved for callers that pass a question context
    if direction == "up":
        return "", ""
    return classical_area_remedy(pc, area_key, house, direction), ""


def build_area(pc: dict, area_key: str, house: int, *,
                 today: Optional[date] = None,
                 question: str = "") -> AreaReport:
    """Compose the unified area report from scattered engine inputs."""
    today = today or date.today()
    import predict_voice as PV
    import report_confluence as CF

    verdict = CF.area_verdict(pc, area_key, house)
    verdict = CF.merge_semantic_verdict(area_key, verdict)
    pred = PV.compose_from_area(pc, area_key, house, today=today)
    direction = verdict.get("direction", pred.direction)

    votes = verdict.get("votes") or []
    decided = [v for v in votes if getattr(v, "direction", "mixed") != "mixed"]
    same = sum(1 for v in decided
               if getattr(v, "direction", "mixed") == direction)
    confidence = PV.confidence_word(same, len(decided) or len(votes), direction)

    prediction = strip_visible_claim_jargon(
        humanise_client_language(client_prose(pred.scenario)))
    proof = _build_proof(
        pc, area_key, house, today=today,
        direction=direction, confidence=confidence)
    when = _area_when(pc, area_key, house, today=today)
    remedy, _mantra = _area_remedy(pc, area_key, house, direction, question=question)
    remedy = humanise_client_language(remedy)

    if len(prediction) > 220:
        prediction = prediction[:217].rsplit(" ", 1)[0] + "…"

    return AreaReport(
        area=area_key,
        direction=direction,
        prediction=prediction,
        proof=proof,
        when=when,
        remedy=remedy,
        confidence=confidence,
        score=verdict.get("score", 0.0),
    )
