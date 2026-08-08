"""Unified per-area confluence report — one contract for cards and Q&A.

Inputs (engine-only): house lord, karaka, Vim/Jaimini/Yogini, SAV, varga,
transit, multi-method votes, area timing window.

Customer output: prediction + 1–2 line proof + when + remedy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

from report_language import client_prose, normalize_sentence_dashes

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

MANTRA = {
    "Sun": "Om Suryaya Namah at sunrise", "Moon": "Om Chandraya Namah on Mondays",
    "Mars": "Om Angarakaya Namah on Tuesdays", "Mercury": "Om Budhaya Namah on Wednesdays",
    "Jupiter": "Om Gurave Namah on Thursdays", "Venus": "Om Shukraya Namah on Fridays",
    "Saturn": "Om Sham Shanaishcharaya Namah on Saturdays",
    "Rahu": "Om Rahave Namah on Saturday evenings",
    "Ketu": "Om Ketave Namah on Tuesday evenings",
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
                   max_len: int = 220) -> str:
    """One or two compressed proof lines — not a calculation dump."""
    today = today or date.today()
    parts: list[str] = []

    hl = (pc.get("house_lords", {}) or {}).get(str(house)) or {}
    lord = hl.get("lord", "")
    if lord:
        clause = f"{lord} rules your {_ord(house)} house, {_dig_plain(hl.get('lord_dignity', ''))}"
        lh = hl.get("lord_house")
        if lh:
            clause += f", placed in the {_ord(lh)}"
        parts.insert(0, clause)

    try:
        import deep_evidence as DE
        de = DE.for_area(area_key, house=house)
        varga = de.get("varga") or {}
        chart = VARGA_PLAIN.get(area_key, "specialised chart")
        fld = varga.get("field_lord") or varga.get("ruler", "")
        if fld:
            parts.append(
                f"{chart}: {fld} {_dig_plain(varga.get('field_lord_dignity') or varga.get('ruler_dignity', ''))}"
            )
        elif chart:
            parts.append(f"{chart} {varga.get('strength', 'mixed')}")
    except Exception:  # noqa: BLE001
        pass

    sav = _sav_word(pc, house)
    if sav:
        parts.append(f"house strength {sav}")

    try:
        import report_confluence as CF
        vim = CF.vimshottari_at(pc, today)
        yog = CF.yogini_at(pc, today) or {}
        jai = CF.jaimini_at(pc, today) or {}
        period_bits = []
        if vim.get("md") and vim.get("ad"):
            period_bits.append(f"{vim['md']}–{vim['ad']}")
        if yog.get("lord"):
            period_bits.append(f"lunar {yog['lord']}")
        if jai.get("sign"):
            period_bits.append(f"sign {jai['sign']}")
        if period_bits:
            parts.append("; ".join(period_bits[:2]))
    except Exception:  # noqa: BLE001
        pass

    try:
        import deep_evidence as DE
        tr = (DE.for_area(area_key, house=house).get("transit") or {})
        if tr.get("support"):
            parts.append(tr["support"][0][:60])
        elif tr.get("pressure"):
            parts.append(tr["pressure"][0][:60])
    except Exception:  # noqa: BLE001
        pass

    line = "; ".join(p for p in parts[:3] if p)
    if len(line) > max_len:
        line = line[: max_len - 1].rsplit(";", 1)[0] + "…"
    return client_prose(line or "your chart points here from several independent reads")


def _area_remedy(pc: dict, area_key: str, house: int, direction: str, *,
                   question: str = "") -> tuple[str, str]:
    """Practical remedy + optional mantra for this area."""
    lord = (pc.get("house_lords", {}) or {}).get(str(house)) or {}
    planet = lord.get("lord", "")

    practical = ""
    try:
        import remedy_block as RB
        block = RB.build(pc, domain=area_key, question=question)
        practical = (block.get("practical") or "").strip()
    except Exception:  # noqa: BLE001
        pass

    if not practical and planet:
        practical = ACTIONS.get(planet, "")

    mantra = MANTRA.get(planet, "") if direction == "down" and planet else ""
    if mantra and practical:
        practical = f"{practical} {mantra}"
    elif mantra:
        practical = mantra

    return client_prose(practical), ""


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

    prediction = client_prose(pred.scenario)
    proof = _build_proof(pc, area_key, house, today=today)
    when = _area_when(pc, area_key, house, today=today)
    remedy, _mantra = _area_remedy(pc, area_key, house, direction, question=question)

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
