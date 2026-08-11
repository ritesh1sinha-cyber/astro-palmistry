"""Area-specific divisional sub-signals and master-correlation manifestations.

`personalized_confluence.resolve_promise` already reads D9/D7/D10 as one more
vote inside the natal promise. This module goes one layer deeper for the
three areas where a single flat vote loses real information — spouse (D9),
children (D7) and profession (D10) — by breaking each divisional chart into
typed sub-signals (house lord, key karaka) instead of one number. Those
sub-signals never re-score the promise; `resolve_promise` stays the single
source of truth for status/score. They exist so a renderer can explain *why*
a manifestation was picked, and so several near-duplicate techniques land on
one bounded, stable meaning (P2-1 / P2-2) instead of four independent
sentences that half-repeat each other.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from astro_precompute import SIGN_LORDS, SIGNS, sign_index

_MASTER_IDS: Optional[dict[str, str]] = None


def master_correlation_ids() -> dict[str, str]:
    """Stable semantic-ID -> internal description table (P2-1). Never shown raw to a customer."""
    global _MASTER_IDS
    if _MASTER_IDS is None:
        path = os.path.join(
            os.path.dirname(__file__), "interpretation", "config", "master_correlation.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                _MASTER_IDS = json.load(fh)
        except Exception:  # noqa: BLE001
            _MASTER_IDS = {}
    return _MASTER_IDS


# ---------------------------------------------------------------------------
# typed D9 / D7 / D10 sub-signals
# ---------------------------------------------------------------------------

_DIVISIONAL_SPEC: dict[str, dict[str, Any]] = {
    "spouse": {"varga": "D9", "house": 7, "karakas": ["Venus", "Jupiter"]},
    "children": {"varga": "D7", "house": 5, "karakas": ["Jupiter"]},
    "profession": {"varga": "D10", "house": 10, "karakas": ["Sun", "Saturn"]},
}


def _varga_lagna(pc: dict, varga: str) -> str:
    block = (pc.get("divisional", {}) or {}).get(varga) or {}
    return block.get("Lagna") or block.get("lagna") or block.get("ascendant") or ""


def _varga_sign(pc: dict, varga: str, planet: str) -> str:
    if varga == "D9":
        return (pc.get("planets", {}).get(planet) or {}).get("navamsha_sign", "")
    return (pc.get("divisional", {}).get(varga) or {}).get(planet, "")


def _dignity_score(planet: str, sign: str) -> float:
    try:
        from personalized_confluence import _dignity
        return _dignity(planet, sign)
    except Exception:  # noqa: BLE001
        return 0.0


def divisional_subsignals(pc: dict, area_key: str) -> list[dict[str, Any]]:
    """Typed D9/D7/D10 sub-signals for spouse/children/profession: house lord + karaka(s)."""
    spec = _DIVISIONAL_SPEC.get(area_key)
    if not spec:
        return []
    varga, house = spec["varga"], spec["house"]
    vl = _varga_lagna(pc, varga)
    signals: list[dict[str, Any]] = []
    if vl:
        hsign = SIGNS[(sign_index(vl) + house - 1) % 12]
        lord = SIGN_LORDS.get(hsign, "")
        if lord:
            lsign = _varga_sign(pc, varga, lord)
            signals.append({
                "id": f"{varga}_HOUSE_LORD",
                "planet": lord,
                "dignity": round(_dignity_score(lord, lsign), 3),
            })
    for k in spec.get("karakas", []):
        ksign = _varga_sign(pc, varga, k)
        if ksign:
            signals.append({
                "id": f"{varga}_{k.upper()}",
                "planet": k,
                "dignity": round(_dignity_score(k, ksign), 3),
            })
    return signals


# ---------------------------------------------------------------------------
# manifestations — one bounded, life-stage-aware meaning per area
# ---------------------------------------------------------------------------

_CATALOG: dict[str, dict[str, list[str]]] = {
    "profession": {
        "strong": [
            "role expansion or a step up in responsibility",
            "recognition for work you have already done",
            "leadership or greater decision-making ownership",
            "an opening to specialise further in your field",
        ],
        "mixed": [
            "recognition for existing work, though growth stays gradual",
            "a role change worth evaluating carefully before committing",
            "more responsibility arriving before full recognition",
        ],
        "weak": [
            "steady, incremental progress rather than a sudden leap",
            "consolidating your current position before expanding it",
        ],
    },
    "spouse": {
        "strong_adult": [
            "a serious relationship or commitment decision",
            "strengthening of an existing bond",
            "clearer emotional connection and companionship",
            "an important relationship milestone",
        ],
        "strong_young": [
            "closer friendships and emotionally significant bonds",
            "a meaningful new connection",
            "learning what lasting partnership feels like",
        ],
        "mixed_adult": [
            "relationship matters that need conscious, steady effort",
            "growing clarity in an existing relationship",
            "communication and stability needing more attention",
        ],
        "mixed_young": ["evolving friendships and social bonds"],
        "weak_adult": [
            "relationships that need patience rather than a rushed decision",
            "strain easing when expectations stay realistic",
        ],
        "weak_young": ["learning what you value in close relationships"],
    },
    "children": {
        "strong_adult": [
            "parenthood or family expansion where timing also qualifies",
            "a stronger bond with an existing child",
            "family responsibility growing in a positive way",
            "child wellbeing becoming a clearer priority",
        ],
        "strong_young": [
            "mentorship or guidance from an elder",
            "creative projects and self-expression",
            "developmental growth rather than near-term parenthood",
        ],
        "mixed_adult": [
            "family matters that need patience",
            "a gradual strengthening of the parent-child bond",
            "child-related opportunity that is not a guarantee on timing alone",
        ],
        "mixed_young": ["mixed signals around creative or academic pursuits"],
        "weak_adult": ["this theme needs more deliberate attention and patience"],
        "weak_young": ["a quieter phase for creative or family themes"],
    },
    "wealth": {
        "strong": [
            "steady income growth",
            "stronger savings discipline",
            "a business or property opportunity worth exploring",
        ],
        "mixed": [
            "income potential without matching accumulation, so discipline matters",
            "a mixed period for financial decisions",
        ],
        "weak": [
            "guarding against financial leakage",
            "avoiding high-risk financial moves right now",
        ],
    },
    "home": {
        "strong": [
            "settling a recurring domestic matter",
            "a favourable property-related decision",
            "a stronger family routine",
        ],
        "mixed": ["home matters progressing slowly but steadily"],
        "weak": ["patience needed with domestic or property matters"],
    },
    "troubles": {
        # For challenge kind, "strong" means the vulnerability pattern is
        # strongly indicated — not that resilience is strong.
        "strong": [
            "accumulated stress if left unmanaged",
            "responsibility or workload that needs pacing",
            "avoidable complications from rushing or skipping routine care",
        ],
        "mixed": [
            "a small issue that benefits from early attention",
            "routine and recovery mattering more than usual",
        ],
        "weak": [
            "good resilience, provided routine and prevention are kept up",
            "only light wellbeing sensitivity in this phase",
        ],
    },
    "education": {
        "strong": [
            "a useful learning opportunity",
            "guidance from a mentor or teacher",
        ],
        "mixed": ["progress that depends on sustained focus"],
        "weak": ["a slower pace of learning that steadies with consistency"],
    },
    "spiritual": {
        "strong": [
            "meaningful spiritual or philosophical growth",
            "clarity emerging from quieter reflection",
        ],
        "mixed": ["a gradual shift in priorities or outlook"],
        "weak": ["a need for more deliberate quiet time and reflection"],
    },
}


def manifestations_for(
    area_key: str,
    *,
    promise_status: str = "",
    activation_status: str = "",
    age_band: str = "adult",
    limit: int = 3,
    pc: Optional[dict] = None,
) -> list[str]:
    """Bounded (2-4 item) manifestation list — one canonical source, not four near-duplicates.

    When `pc` is provided for spouse/children/profession, D9/D7/D10 sub-signal
    dignity softly reorders the catalog so stronger karaka/house-lord evidence
    surfaces first. It never invents a new promise score.
    """
    from narration.status_vocab import promise_bucket

    p = promise_bucket(promise_status)
    a = (activation_status or "").lower()
    catalog = _CATALOG.get(area_key)
    if not catalog:
        return []
    if area_key in ("spouse", "children"):
        band = (age_band or "adult").lower()
        stage = "young" if band in ("child", "teen", "young_adult") else "adult"
        items = list(catalog.get(f"{p}_{stage}") or catalog.get(f"{p}_adult") or [])
    else:
        items = list(catalog.get(p) or [])

    if pc and area_key in _DIVISIONAL_SPEC and items:
        signals = divisional_subsignals(pc, area_key)
        avg_dig = (
            sum(float(s.get("dignity") or 0.0) for s in signals) / len(signals)
            if signals else 0.0
        )
        # Soft reorder: strong dignity prefers recognition/commitment-style
        # lines (earlier catalog entries); weak dignity prefers patience/strain.
        if avg_dig < -0.4:
            items = list(reversed(items))
        elif a in ("weak", "inactive", "insufficient_evidence") and len(items) > 1:
            # Promised but not active — keep potential lines, de-emphasise "now".
            items = items[1:] + items[:1]

    return list(items[: max(2, min(limit, 4))])
