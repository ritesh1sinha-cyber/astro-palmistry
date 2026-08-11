"""Personalized life-area promise engine.

A promise is a natal/divisional structural question: is the life area strongly
supported, supported, mixed, weak, or not sufficiently evidenced?

Timing is deliberately NOT used to create the promise. This keeps:

    PROMISE -> TIMING -> MANIFESTATION -> ACTION

as separate decisions.
"""
from __future__ import annotations

from typing import Any

from astro_precompute import SIGN_LORDS, SIGNS, get_dignity, sign_index
from prediction108_rules import NAT_BENEFIC, NAT_MALEFIC, PLANETS, hlord, phouse

AREA_CONFIG = {
    "self": {
        "label": "Self, vitality & temperament", "house": 1, "secondary": [6, 8],
        "varga": "D1", "varga_house": 1, "karakas": ["Sun"],
    },
    "parents": {
        "label": "Parents & family roots", "house": 4, "secondary": [9],
        "varga": "D12", "varga_house": 4, "karakas": ["Moon", "Sun"],
    },
    "siblings": {
        "label": "Siblings & support network", "house": 3, "secondary": [11],
        "varga": "D3", "varga_house": 3, "karakas": ["Mars"],
    },
    "spouse": {
        "label": "Relationships & marriage", "house": 7, "secondary": [2, 5, 11],
        "varga": "D9", "varga_house": 7, "karakas": ["Venus", "Jupiter"],
    },
    "children": {
        "label": "Children & parenthood", "house": 5, "secondary": [9, 2, 11],
        "varga": "D7", "varga_house": 5, "karakas": ["Jupiter"],
    },
    "profession": {
        "label": "Career, status & recognition", "house": 10, "secondary": [6, 11, 2],
        "varga": "D10", "varga_house": 10, "karakas": ["Sun", "Saturn", "Mercury"],
    },
    "education": {
        "label": "Education & learning", "house": 5, "secondary": [4, 2, 9],
        "varga": "D24", "varga_house": 5, "karakas": ["Mercury", "Jupiter"],
    },
    "wealth": {
        "label": "Income, wealth & accumulation", "house": 2, "secondary": [11, 9, 5],
        "varga": "D2", "varga_house": 2, "karakas": ["Jupiter", "Venus"],
    },
    "home": {
        "label": "Home, property & domestic peace", "house": 4, "secondary": [2, 11],
        "varga": "D4", "varga_house": 4, "karakas": ["Moon", "Mars"],
    },
    "strengths": {
        "label": "Strength, resilience & confidence", "house": 1, "secondary": [3, 6, 11],
        "varga": "D27", "varga_house": 1, "karakas": ["Sun", "Mars"],
    },
    "troubles": {
        "label": "Challenges, obstacles & wellbeing", "house": 6, "secondary": [8, 12, 1],
        "varga": "D30", "varga_house": 6, "karakas": ["Saturn", "Mars"],
        # D30 answers "how strongly is a challenge/vulnerability pattern
        # indicated", never "how strongly is illness promised". kind
        # switches _status onto CHALLENGE_STATUS and every evidence
        # sentence onto wellbeing-safe wording (see _pos_word/_neg_word).
        "kind": "challenge",
    },
    "spiritual": {
        "label": "Inner life, faith & spiritual growth", "house": 9, "secondary": [5, 12],
        "varga": "D20", "varga_house": 9, "karakas": ["Jupiter", "Ketu", "Moon"],
    },
}

AREA_ALIASES = {
    "love": "spouse",
    "marriage": "spouse",
    "relationship": "spouse",
    "children": "children",
    "career": "profession",
    "money": "wealth",
    "health": "troubles",
    "learning": "education",
    "inner": "spiritual",
    "family": "home",
    "self": "self",
    "home": "home",
}

GOOD_HOUSES = {1, 4, 5, 7, 9, 10}
DUSTHANA = {6, 8, 12}

_PROMISE_CACHE: dict[tuple[str, str], dict[str, Any]] = {}


def canonical_area(area: str) -> str:
    return AREA_ALIASES.get(str(area or "").lower(), str(area or "").lower())


def _pc_cache_key(pc: dict) -> str:
    meta = pc.get("meta") or {}
    return str(pc.get("chart_hash") or meta.get("chart_hash") or id(pc))


def _empty_promise(key: str) -> dict[str, Any]:
    return {
        "area": key,
        "kind": "promise",
        "status": "insufficient_evidence",
        "label": "Limited evidence",
        "score": 0.0,
        "confidence": "low",
        "evidence_families": [],
        "supporting_evidence": [],
        "caution_evidence": [],
        "contradiction": 0.0,
        "timing_allowed": False,
        "promise_only": True,
    }


def _sign(pc: dict, planet: str) -> str:
    return (pc.get("planets", {}).get(planet) or {}).get("sign", "")


def _varga_sign(pc: dict, varga: str, planet: str) -> str:
    if varga == "D9":
        return (pc.get("planets", {}).get(planet) or {}).get("navamsha_sign", "")
    return (pc.get("divisional", {}).get(varga) or {}).get(planet, "")


def _varga_lagna(pc: dict, varga: str) -> str:
    block = (pc.get("divisional", {}).get(varga) or {})
    return block.get("Lagna") or block.get("lagna") or block.get("ascendant") or ""


def _varga_house(vl: str, sign: str) -> int:
    if not vl or not sign:
        return 0
    return ((sign_index(sign) - sign_index(vl)) % 12) + 1


def _dignity(planet: str, sign: str) -> float:
    if not planet or not sign:
        return 0.0
    try:
        d = str(get_dignity(planet, sign) or "").lower()
    except Exception:
        return 0.0
    return {
        "exalted": 2.0,
        "moolatrikona": 1.7,
        "own_sign": 1.5,
        "friendly_sign": 0.8,
        "neutral_sign": 0.0,
        "enemy_sign": -0.8,
        "great_enemy_sign": -1.2,
        "debilitated": -2.0,
    }.get(d, 0.0)


def _house_lord(pc: dict, house: int) -> str:
    try:
        return hlord(pc, house) or ""
    except Exception:
        return (pc.get("house_lords", {}).get(str(house)) or {}).get("lord", "")


def _house_of(pc: dict, planet: str) -> int:
    try:
        return int(phouse(pc, planet) or 0)
    except Exception:
        return int((pc.get("planets", {}).get(planet) or {}).get("house") or 0)


def _pos_word(kind: str) -> str:
    return "protective" if kind == "challenge" else "supportive"


def _neg_word(kind: str) -> str:
    return "sensitive" if kind == "challenge" else "difficult"


def _support_word(kind: str) -> str:
    return "resilience" if kind == "challenge" else "support"


def _natal_family(pc: dict, cfg: dict, kind: str = "promise") -> tuple[float, list[str], list[str]]:
    house = cfg["house"]
    lord = _house_lord(pc, house)
    score = 0.0
    evidence, cautions = [], []

    if lord:
        dig = _dignity(lord, _sign(pc, lord))
        score += dig
        if dig >= 1.2:
            evidence.append(
                f"{lord} gives solid {_support_word(kind)} to this life theme in the birth chart"
            )
        elif dig <= -1.0:
            cautions.append(
                f"{lord} is under strain for this life theme in the birth chart"
            )

        lh = _house_of(pc, lord)
        if lh in GOOD_HOUSES:
            score += 0.8
            evidence.append(
                f"the chart structure for this theme sits in a {_pos_word(kind)} position"
            )
        elif lh in DUSTHANA:
            score -= 0.8
            cautions.append(
                f"the chart structure for this theme sits in a {_neg_word(kind)} position"
            )

    planets = pc.get("planets", {}) or {}
    for p in PLANETS:
        if int((planets.get(p) or {}).get("house") or 0) == house:
            if p in NAT_BENEFIC:
                score += 0.65
                evidence.append(f"{p} adds {_pos_word(kind)} influence to this theme")
            elif p in NAT_MALEFIC:
                score -= 0.55
                cautions.append(f"{p} adds pressure that needs steady handling here")

    for h in cfg.get("secondary", []):
        sl = _house_lord(pc, h)
        if not sl:
            continue
        d = _dignity(sl, _sign(pc, sl))
        if d >= 1.2:
            score += 0.35
        elif d <= -1.0:
            score -= 0.35

    return max(-2.0, min(2.0, score)), evidence[:4], cautions[:4]


def _varga_family(pc: dict, cfg: dict, kind: str = "promise") -> tuple[float, list[str], list[str]]:
    varga = cfg.get("varga")
    if not varga or varga == "D1":
        return 0.0, [], []
    vl = _varga_lagna(pc, varga)
    if not vl:
        return 0.0, [], ["the specialised chart for this theme is unavailable"]
    hsign = SIGNS[(sign_index(vl) + cfg["varga_house"] - 1) % 12]
    lord = SIGN_LORDS.get(hsign, "")
    score = 0.0
    evidence, cautions = [], []
    if lord:
        vs = _varga_sign(pc, varga, lord)
        d = _dignity(lord, vs)
        score += d
        if d >= 1.2:
            evidence.append(
                f"{lord} is strong in the specialised chart for this theme"
            )
        elif d <= -1.0:
            cautions.append(
                f"{lord} is weaker in the specialised chart, reducing "
                f"{_support_word(kind)} here"
            )
        vh = _varga_house(vl, vs)
        if vh in GOOD_HOUSES:
            score += 0.6
            evidence.append(
                f"the specialised chart places this theme in a {_pos_word(kind)} setting"
            )
        elif vh in DUSTHANA:
            score -= 0.6
            cautions.append(
                f"the specialised chart places this theme in a {_neg_word(kind)} setting"
            )

    for k in cfg.get("karakas", []):
        ks = _varga_sign(pc, varga, k)
        if not ks:
            continue
        d = _dignity(k, ks)
        score += 0.45 if d >= 1.2 else -0.45 if d <= -1.0 else 0.0
        if d >= 1.2:
            evidence.append(f"{k} reinforces this specialised theme")
        elif d <= -1.0:
            cautions.append(f"{k} adds a caution signal in the specialised chart")

    return max(-2.0, min(2.0, score)), evidence[:4], cautions[:4]


def _cap_divisional_to_natal(nf: float, vf: float) -> float:
    """D1 is the baseline (P1-18): a divisional chart can refine but never

    manufacture a promise the birth chart itself does not support. If the
    natal family is clearly weak/negative, a strongly positive divisional
    reading is capped rather than allowed to flip the overall verdict.
    """
    if nf <= -0.5 and vf > 0.6:
        return 0.6
    if nf >= 0.5 and vf < -0.6:
        # Symmetric guard: a single weak divisional vote should not by
        # itself drag a solid natal promise all the way down either.
        return -0.6
    return vf


def _cached_rule_verdicts(pc: dict) -> list:
    try:
        import deep_evidence as DE
        ctx = DE.current()
        if ctx is not None:
            return list(ctx.verdicts())
    except Exception:
        pass
    try:
        from prediction108_rules import evaluate_all
        return list(evaluate_all(pc))
    except Exception:
        return []


def _rule_family(pc: dict, key: str, kind: str = "promise") -> tuple[float, list[str], list[str]]:
    verdicts = _cached_rule_verdicts(pc)
    if not verdicts:
        return 0.0, [], []
    terms = {
        "spouse": ("marriage", "spouse", "partnership", "wife", "husband"),
        "children": ("child", "children", "progeny", "son", "daughter"),
        "profession": ("career", "profession", "job", "authority", "promotion", "status"),
        "wealth": ("wealth", "income", "money", "gain", "rich", "financial", "dhana"),
        "home": ("property", "house", "home", "vehicle", "land"),
        "education": ("education", "learning", "study", "intelligent"),
        "troubles": ("health", "illness", "disease", "injury", "obstacle"),
        "parents": ("father", "mother", "parents"),
        "siblings": ("sibling", "brother", "sister"),
        "spiritual": ("spiritual", "dharma", "moksha", "religion"),
        "strengths": ("courage", "strength", "stamina", "resilience"),
        "self": ("personality", "temperament", "body", "vitality"),
    }.get(key, ())
    pos, neg = [], []
    for v in verdicts:
        verdict = str(getattr(v, "verdict", ""))
        if verdict not in ("HIT", "PARTIAL"):
            continue
        text = " ".join(str(getattr(v, a, "")) for a in ("finding", "prediction", "because"))
        low = text.lower()
        if not any(t in low for t in terms):
            continue
        try:
            from final_user_report import _classify_rule
            pol = _classify_rule(v)
        except Exception:
            pol = "pos" if any(t in low for t in ("success", "gain", "happy", "strong", "favour")) else "neg"
        if pol == "pos":
            pos.append(v)
        elif pol == "neg":
            neg.append(v)
    if not pos and not neg:
        return 0.0, [], []
    score = (1.0 if pos else 0.0) - (0.8 if neg else 0.0)
    score = max(-1.0, min(1.0, score))
    if kind == "challenge":
        support_line = "Classical checks add protective support for this theme"
        caution_line = (
            "Classical checks point to added pressure that benefits from "
            "routine and care"
        )
    else:
        support_line = "Classical checks add supporting evidence for this theme"
        caution_line = (
            "Classical checks add caution, so steady effort matters more here"
        )
    return score, ([support_line] if pos else []), ([caution_line] if neg else [])


def _status(score: float, evidence_count: int, conflict: float,
           kind: str = "promise") -> tuple[str, str]:
    from narration.status_vocab import status_label

    if kind == "challenge":
        if evidence_count < 2:
            status = "insufficient_evidence"
        elif conflict >= 0.45 and abs(score) < 0.75:
            status = "mixed"
        elif score >= 1.05:
            status = "strongly_indicated"
        elif score >= 0.35:
            status = "indicated"
        elif score <= -0.85:
            status = "weak"
        else:
            status = "mixed"
        return status, status_label(status, kind="challenge")

    if evidence_count < 2:
        return "insufficient_evidence", "Limited evidence"
    if conflict >= 0.45 and abs(score) < 0.75:
        return "mixed", "Mixed promise"
    if score >= 1.05:
        return "strongly_supported", "Strongly supported"
    if score >= 0.35:
        return "supported", "Supported"
    if score <= -0.85:
        return "weak", "Not strongly supported"
    return "mixed", "Mixed promise"


def resolve_promise(pc: dict, area_key: str) -> dict[str, Any]:
    """Return the canonical natal/divisional promise for one life area."""
    key = canonical_area(area_key)
    cache_key = (_pc_cache_key(pc), key)
    if cache_key in _PROMISE_CACHE:
        return _PROMISE_CACHE[cache_key]

    cfg = AREA_CONFIG.get(key)
    if not cfg:
        result = _empty_promise(key)
        _PROMISE_CACHE[cache_key] = result
        return result

    kind = cfg.get("kind", "promise")
    nf, ne, nc = _natal_family(pc, cfg, kind=kind)
    vf, ve, vc = _varga_family(pc, cfg, kind=kind)
    # P1-18: D1 is the baseline. A divisional chart refines the natal
    # promise but is not allowed to manufacture one the birth chart itself
    # does not support (or erase one it clearly does).
    vf = _cap_divisional_to_natal(nf, vf)
    rf, re, rc = _rule_family(pc, key, kind=kind)

    families = {"natal": nf, "divisional": vf, "rules": rf}
    score = nf * 1.0 + vf * 1.0 + rf * 0.55
    denom = 1.0 + 1.0 + (0.55 if rf else 0.0)
    score = max(-2.0, min(2.0, score / denom * 1.55))

    support = [x for x in (ne + ve + re) if x]
    caution = [x for x in (nc + vc + rc) if x]
    pos_families = sum(1 for v in families.values() if v > 0.35)
    neg_families = sum(1 for v in families.values() if v < -0.35)
    conflict = min(1.0, (min(pos_families, neg_families) / 2.0))
    status, label = _status(score, pos_families + neg_families, conflict, kind=kind)

    strong_status = {"strongly_supported", "strongly_indicated"}
    moderate_status = {"supported", "indicated", "mixed"}
    if status in strong_status:
        confidence = "high"
    elif status in moderate_status:
        confidence = "moderate"
    else:
        confidence = "low"

    result = {
        "area": key,
        "kind": kind,
        "label": label,
        "status": status,
        "score": round(score, 3),
        "confidence": confidence,
        "evidence_families": [
            {"family": "natal", "score": round(nf, 3)},
            {"family": "divisional", "score": round(vf, 3)},
            {"family": "rules", "score": round(rf, 3)},
        ],
        "supporting_evidence": support[:6],
        "caution_evidence": caution[:6],
        "contradiction": round(conflict, 3),
        # Timing is never read here (P1-19) — this flag only tells a
        # renderer whether it is *safe* to layer a timing/activation read
        # on top of this promise; it never contributes to score/status.
        "timing_allowed": status in (strong_status | moderate_status),
        "promise_only": True,
    }
    _PROMISE_CACHE[cache_key] = result
    return result


def resolve_activation(*, direction: str, score: float = 0.0,
                       confidence: str = "low", agreement: str = "weak",
                       promise_status: str = "") -> dict[str, Any]:
    """Timing-only activation status (P0-8 / P1-19).

    Built strictly from the values `build_confluence` already computes
    (direction/score/confidence/agreement) — no new astrology runs here,
    and nothing from `resolve_promise` feeds into the score. Promise status
    is accepted only so a renderer can be told when timing is not allowed
    to speak at all (`status == "insufficient_evidence"`); it never changes
    the activation math itself.
    """
    from narration.status_vocab import status_label

    direction = (direction or "mixed").lower()
    confidence = (confidence or "low").lower()
    agreement = (agreement or "weak").lower()
    strong_conf = confidence in ("very high", "high")

    if direction == "up":
        status = "strongly_active" if strong_conf else "active"
    elif direction == "down":
        status = "inactive" if strong_conf else "weak"
    else:
        status = "mixed"
    if agreement == "weak" and confidence == "low" and direction == "mixed":
        status = "insufficient_evidence"

    strength = "strong" if strong_conf else ("moderate" if confidence == "moderate" else "low")
    return {
        "status": status,
        "label": status_label(status, kind="activation"),
        "confidence": confidence,
        "strength": strength,
        "direction": direction,
        "score": round(float(score or 0.0), 3),
        "promise_status": promise_status,
        "activation_only": True,
    }


# ---------------------------------------------------------------------------
# wealth sub-promises (P1-8 / workstream 3) — decomposed inside the one
# Money card, reusing the same natal/divisional machinery with narrower
# house sets rather than inventing a second scoring system.
# ---------------------------------------------------------------------------

WEALTH_SUBAREAS: dict[str, dict[str, Any]] = {
    "income": {
        "label": "Income", "house": 2, "secondary": [11],
        "varga": "D2", "varga_house": 2, "karakas": ["Jupiter"],
    },
    "accumulation": {
        "label": "Accumulation & savings", "house": 2, "secondary": [4],
        "varga": "D2", "varga_house": 2, "karakas": ["Venus"],
    },
    "business_gains": {
        "label": "Business gains", "house": 7, "secondary": [10, 11],
        "varga": "D10", "varga_house": 7, "karakas": ["Mercury"],
    },
    "sudden_gains": {
        "label": "Sudden gains", "house": 11, "secondary": [5, 8],
        "varga": "D2", "varga_house": 11, "karakas": ["Rahu"],
    },
}


def resolve_wealth_subareas(pc: dict) -> dict[str, dict[str, Any]]:
    """Bounded income / accumulation / business / windfall sub-promises.

    Sudden-gain (and similarly high-bar) claims need both natal and
    divisional families supportive — one family alone is not enough for
    a strong windfall statement.
    """
    from narration.status_vocab import status_label

    out: dict[str, dict[str, Any]] = {}
    for key, cfg in WEALTH_SUBAREAS.items():
        nf, _ne, _nc = _natal_family(pc, cfg)
        vf, _ve, _vc = _varga_family(pc, cfg)
        vf = _cap_divisional_to_natal(nf, vf)
        score = max(-2.0, min(2.0, (nf + vf) / 2.0 * 1.3))
        pos = sum(1 for v in (nf, vf) if v > 0.35)
        neg = sum(1 for v in (nf, vf) if v < -0.35)
        conflict = min(1.0, min(pos, neg))
        status, label = _status(score, pos + neg, conflict)

        if key == "sudden_gains":
            # High threshold: both families must be clearly supportive.
            if nf <= 0.35 or vf <= 0.35:
                if status in ("strongly_supported", "supported"):
                    status = "mixed" if (nf > 0 or vf > 0) else "insufficient_evidence"
                    label = status_label(status, kind="promise")
                if status == "insufficient_evidence":
                    label = (
                        "The chart supports financial improvement, but a "
                        "specific sudden-gain claim is not strong enough"
                    )

        out[key] = {
            "key": key,
            "label": cfg["label"],
            "status": status,
            "status_label": label,
            "score": round(score, 3),
            "natal_score": round(nf, 3),
            "divisional_score": round(vf, 3),
        }
    return out


def wealth_comparison_sentence(subs: dict[str, dict[str, Any]]) -> str:
    """Single free-tier sentence comparing the strongest and weakest sub-promise."""
    order = ["income", "accumulation", "business_gains", "sudden_gains"]
    names = {
        "income": "ability to earn",
        "accumulation": "steady accumulation and savings",
        "business_gains": "gains through business",
        "sudden_gains": "sudden windfalls",
    }
    # Prefer status rank, then score — keeps free sentence aligned with paid rows.
    _rank = {
        "strongly_supported": 4, "supported": 3, "mixed": 2,
        "weak": 1, "insufficient_evidence": 0,
    }
    present = [k for k in order if k in subs]
    if len(present) < 2:
        return ""

    def _key(k: str) -> tuple:
        return (_rank.get(subs[k]["status"], 0), subs[k]["score"])

    strongest = max(present, key=_key)
    weakest = min(present, key=_key)
    if strongest == weakest or (
        _key(strongest)[0] == _key(weakest)[0]
        and abs(subs[strongest]["score"] - subs[weakest]["score"]) < 0.25
    ):
        return (
            "Your income, savings and gains indications are broadly similar "
            "in strength, without one standing out sharply from the others."
        )
    # Grammar: plural noun phrases take "are", singular take "is".
    plural = {"steady accumulation and savings", "gains through business",
              "sudden windfalls"}
    verb = "are" if names[strongest] in plural else "is"
    if strongest == "income" and weakest in ("accumulation", "sudden_gains"):
        return (
            "Your ability to earn is better supported than effortless "
            "wealth accumulation. Financial progress is more naturally "
            "supported through consistent income and disciplined saving."
        )
    return (
        f"Your {names[strongest]} {verb} stronger in the chart than your "
        f"indication for {names[weakest]}, so sustained effort is likely to "
        f"pay off more reliably than waiting for a single lucky break."
    )


def wealth_pressure_action(subs: dict[str, dict[str, Any]]) -> str:
    """Practical line when accumulation lags income — for money pressure/action."""
    inc = subs.get("income") or {}
    acc = subs.get("accumulation") or {}
    if not inc or not acc:
        return ""
    if float(inc.get("score") or 0) - float(acc.get("score") or 0) < 0.25:
        return ""
    return (
        "Protect gains, reduce leakage and prioritize consistent accumulation."
    )


def resolve_all_promises(pc: dict) -> dict[str, dict[str, Any]]:
    return {key: resolve_promise(pc, key) for key in AREA_CONFIG}


def clear_promise_cache() -> None:
    _PROMISE_CACHE.clear()
