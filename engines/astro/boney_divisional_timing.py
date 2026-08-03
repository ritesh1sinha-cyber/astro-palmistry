#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Marc Boney - Intricate Patterns of Destiny (2014): dasha lords in divisional charts.

OCR: book_ocr/intricate_patterns_destiny/ - rules45.md
Core gate: event likely only when D1 + D9 + event varga concur (Boney p.88-91).
Period analysis: D1-D9 dignity cross-check, Vimshopaka, active MD-AD domain scores.
"""
from __future__ import annotations

import html
from typing import Any

from astro_precompute import get_dignity
from vedic_varga_goel import BENEFICS, MALEFICS, PLANET_KEYS, STRONG_DIG, VargaChart, varga_from_divisional

BONEY_RULES_SOURCE = "rules45.md (Boney 2014, Intricate Patterns of Destiny)"

GOOD_HOUSES = frozenset({1, 2, 4, 5, 7, 9, 10, 11})
BAD_HOUSES = frozenset({3, 6, 8, 12})
FRIENDLY_DIG = frozenset({"friend_sign", "great_friend_sign"})
WEAK_DIG = frozenset({"debilitated", "enemy_sign"})
GOOD_DIVISION_DIG = STRONG_DIG + ("friend_sign",)

DIG_SCORE = {
    "exalted": 4,
    "moolatrikona": 4,
    "own_sign": 3,
    "great_friend_sign": 2,
    "friend_sign": 1,
    "neutral_sign": 0,
    "enemy_sign": -1,
    "debilitated": -2,
}

DASHAVARGA_KEYS = ("D1", "D2", "D3", "D7", "D9", "D10", "D12", "D16", "D30", "D60")
ACTIVE_PERIOD_DOMAINS = ("career", "marriage", "children")
VERDICT_ORDER = ("hard", "attention", "good")

DIGNITY_TIER_PLAIN = {
    "strong_both": "strong in both birth chart and Navamsha - period results should land well",
    "upgrade": "dignity improves in Navamsha - better delivery than the birth chart alone suggests",
    "downgrade": "dignity weakens in Navamsha - results may under-deliver versus the birth chart",
    "weak_both": "weak in both charts - yoga or promise may not show strongly in this period",
    "vargottama_debilitated": "vargottama debilitated - some strength, but not full vargottama uplift",
    "neutral": "Navamsha dignity matches the birth chart - steady, predictable delivery",
}

# event_kind (promise key) -> (varga, focal houses, karaka for house-from-karaka check)
BONEY_EVENT_MAP: dict[str, tuple[str, list[int], str | None]] = {
    "marriage": ("D9", [7], "Venus"),
    "child": ("D7", [5, 9], "Jupiter"),
    "career": ("D10", [10], None),
    "property": ("D4", [4], "Moon"),
    "education": ("D24", [5, 9], "Mercury"),
    "business": ("D10", [7, 10], None),
    "travel": ("D9", [9, 12], None),
    "health": ("D30", [1, 8], None),
}


def _house_band(house: int) -> str:
    if house in GOOD_HOUSES:
        return "good"
    if house in BAD_HOUSES:
        return "bad"
    return "neutral"


def _dignity_band(planet: str, sign: str) -> str:
    if not sign:
        return "neutral"
    dig = get_dignity(planet, sign)
    if dig in STRONG_DIG or dig in FRIENDLY_DIG:
        return "good"
    if dig in WEAK_DIG:
        return "bad"
    return "neutral"


def _jupiter_support(vc: VargaChart, house: int) -> bool:
    if not house:
        return False
    if vc.planet_house("Jupiter") == house:
        return True
    return "Jupiter" in vc.tenants(house)


def _score_lord_in_varga(
    vc: VargaChart,
    lord: str,
    focal_houses: list[int],
    *,
    label: str,
) -> tuple[int, list[str]]:
    if not vc or not lord or lord not in vc.signs:
        return 0, []
    h = vc.planet_house(lord)
    if not h:
        return 0, []
    sign = vc.signs.get(lord, "")
    hb = _house_band(h)
    db = _dignity_band(lord, sign)
    score = 0
    notes: list[str] = []

    if h in focal_houses:
        score += 2
        notes.append(f"{label} {lord} in focal {h}th ({vc.name})")
    elif hb == "good":
        score += 1
        notes.append(f"{label} {lord} in supportive {h}th ({vc.name})")
    elif hb == "bad":
        score -= 1
        notes.append(f"{label} {lord} in dusthana {h}th ({vc.name})")

    if db == "good":
        score += 1
    elif db == "bad":
        score -= 1

    if hb == "bad" and db == "good":
        score += 1
        notes.append(f"{label} {lord} dignified despite dusthana ({vc.name})")
    if _jupiter_support(vc, h):
        score += 1
        notes.append(f"Jupiter supports {label} {lord} in {vc.name}")

    malefic_tenants = [p for p in vc.tenants(h) if p in MALEFICS and p != lord]
    if malefic_tenants and not _jupiter_support(vc, h):
        score -= 1
        notes.append(f"Malefic weight on {label} {lord} ({','.join(malefic_tenants)})")

    return score, notes


def _d9_event_support(vc: VargaChart, event_kind: str, md: str, ad: str) -> tuple[int, list[str]]:
    """Navamsha read as full life chart during dasha (Boney p.53-54), not spouse-only."""
    focal = {
        "marriage": [4, 7],
        "child": [5, 9],
        "career": [10, 11],
        "property": [4],
        "education": [5, 9],
        "business": [7, 10],
        "travel": [9, 12],
        "health": [6, 8, 12],
    }.get(event_kind, [7])
    md_s, md_n = _score_lord_in_varga(vc, md, focal, label="MD")
    ad_s, ad_n = _score_lord_in_varga(vc, ad, focal, label="AD")
    return md_s + ad_s, md_n + ad_n


def _d1_chart(pc: dict) -> VargaChart | None:
    d1 = varga_from_divisional(pc, "D1")
    if d1:
        return d1
    meta = pc.get("meta", {})
    lagna = meta.get("lagna_sign") or pc.get("lagna", {}).get("sign")
    if not lagna:
        return None
    signs: dict[str, str] = {"lagna": lagna}
    for pname, data in pc.get("planets", {}).items():
        if pname in PLANET_KEYS[1:] and data.get("sign"):
            signs[pname] = data["sign"]
    return VargaChart("D1", lagna, signs, {})


def score_boney_divisional_window(
    *,
    md_lord: str,
    ad_lord: str,
    event_kind: str,
    pc: dict,
) -> dict[str, Any]:
    """
    Score Vim MD/AD placement in D1, D9, and event varga per Boney rules45.
    tri_confluence = all three layers pass minimum support.
    """
    mapping = BONEY_EVENT_MAP.get(event_kind)
    if not mapping:
        return {"available": False, "yes": False, "note": f"no Boney map for {event_kind}"}

    varga_key, focal, karaka = mapping
    d1 = _d1_chart(pc)
    d9 = varga_from_divisional(pc, "D9")
    dv = varga_from_divisional(pc, varga_key)

    if not d9 or not dv:
        return {
            "available": False,
            "yes": False,
            "note": f"missing {varga_key} or D9 for Boney divisional gate",
        }

    notes: list[str] = []
    layer_scores: dict[str, int] = {}

    if d1:
        s1, n1 = _score_lord_in_varga(d1, md_lord, focal, label="MD")
        s2, n2 = _score_lord_in_varga(d1, ad_lord, focal, label="AD")
        layer_scores["D1"] = s1 + s2
        notes.extend(n1 + n2)

    s9, n9 = _d9_event_support(d9, event_kind, md_lord, ad_lord)
    layer_scores["D9"] = s9
    notes.extend(n9)

    sm, nm = _score_lord_in_varga(dv, md_lord, focal, label="MD")
    sa, na = _score_lord_in_varga(dv, ad_lord, focal, label="AD")
    layer_scores[varga_key] = sm + sa
    notes.extend(nm + na)

    if karaka and karaka in dv.signs:
        k_h = dv.planet_house(karaka)
        if k_h in focal:
            layer_scores[varga_key] = layer_scores.get(varga_key, 0) + 1
            notes.append(f"Karaka {karaka} in focal {k_h}th ({varga_key})")

    d1_ok = layer_scores.get("D1", 0) >= 0
    d9_ok = layer_scores.get("D9", 0) >= 1
    dv_ok = layer_scores.get(varga_key, 0) >= 1
    tri = d1_ok and d9_ok and dv_ok
    total = sum(layer_scores.values())
    yes = tri and total >= 2

    note = "; ".join(notes[:4])
    if tri:
        note = f"D1+D9+{varga_key} confluence (Boney); " + note
    else:
        failed = []
        if not d1_ok:
            failed.append("D1")
        if not d9_ok:
            failed.append("D9")
        if not dv_ok:
            failed.append(varga_key)
        note = f"Tri-chart gate weak ({','.join(failed)}); " + note

    return {
        "available": True,
        "yes": yes,
        "tri_confluence": tri,
        "score": total,
        "layer_scores": layer_scores,
        "varga_key": varga_key,
        "note": note[:400],
        "source": BONEY_RULES_SOURCE,
    }


def _planet_sign_d1(pc: dict, planet: str) -> str:
    d1 = _d1_chart(pc)
    if d1 and planet in d1.signs:
        return d1.signs[planet]
    return pc.get("planets", {}).get(planet, {}).get("sign", "")


def period_lord_dignity_crosscheck(planet: str, d1_sign: str, d9_sign: str) -> dict[str, Any]:
    """
    Boney p.16-17: cross-check period lord dignity in D1 vs D9.
    """
    if not planet or not d1_sign:
        return {"available": False, "tier": "neutral", "note": ""}

    d1_dig = get_dignity(planet, d1_sign)
    d9_dig = get_dignity(planet, d9_sign) if d9_sign else d1_dig
    d1_s = DIG_SCORE.get(d1_dig, 0)
    d9_s = DIG_SCORE.get(d9_dig, 0)
    vargottama = bool(d9_sign) and d1_sign == d9_sign

    if vargottama and d1_dig == "debilitated":
        tier = "vargottama_debilitated"
    elif d1_s >= 2 and d9_s >= 2:
        tier = "strong_both"
    elif d1_s <= -1 and d9_s <= -1:
        tier = "weak_both"
    elif d9_s > d1_s:
        tier = "upgrade"
    elif d9_s < d1_s:
        tier = "downgrade"
    else:
        tier = "neutral"

    dig_word = {
        "exalted": "exalted",
        "own_sign": "own sign",
        "moolatrikona": "moolatrikona",
        "great_friend_sign": "great friend's sign",
        "friend_sign": "friend's sign",
        "neutral_sign": "neutral",
        "enemy_sign": "enemy sign",
        "debilitated": "debilitated",
    }
    d1_w = dig_word.get(d1_dig, d1_dig)
    d9_w = dig_word.get(d9_dig, d9_dig) if d9_sign else d1_w
    note = DIGNITY_TIER_PLAIN[tier]
    if d9_sign:
        note = f"D1 {d1_w}, D9 {d9_w} - {note}."

    return {
        "available": True,
        "planet": planet,
        "d1_sign": d1_sign,
        "d9_sign": d9_sign,
        "d1_dignity": d1_dig,
        "d9_dignity": d9_dig,
        "tier": tier,
        "note": note,
        "source": BONEY_RULES_SOURCE,
    }


def dignity_crosscheck_for_lord(pc: dict, planet: str) -> dict[str, Any]:
    """Convenience wrapper using precomputed D1/D9."""
    d9 = varga_from_divisional(pc, "D9")
    d1_sign = _planet_sign_d1(pc, planet)
    d9_sign = d9.signs.get(planet, "") if d9 else ""
    if not d9_sign:
        return {"available": False, "tier": "neutral", "note": ""}
    return period_lord_dignity_crosscheck(planet, d1_sign, d9_sign)


def score_vimshopaka(pc: dict, planet: str) -> dict[str, Any]:
    """
    Parashara dashavarga good-division count (rules45 p.12-19, summary p.89).
    Uses available precomputed vargas; D2/D16 included when present.
    """
    if not planet:
        return {"available": False, "good": 0, "total": 0, "tier": "unknown", "note": ""}

    good = 0
    total = 0
    for key in DASHAVARGA_KEYS:
        if key == "D1":
            vc = _d1_chart(pc)
        else:
            vc = varga_from_divisional(pc, key)
        if not vc or planet not in vc.signs:
            continue
        sign = vc.signs[planet]
        if not sign:
            continue
        total += 1
        dig = get_dignity(planet, sign)
        if dig in GOOD_DIVISION_DIG:
            good += 1

    if total == 0:
        return {"available": False, "good": 0, "total": 0, "tier": "unknown", "note": ""}

    ratio = good / total
    if good >= 8 or (total >= 8 and ratio >= 0.8):
        tier = "strong"
    elif good >= 6 or ratio >= 0.6:
        tier = "good"
    elif good >= 4 or ratio >= 0.4:
        tier = "moderate"
    else:
        tier = "weak"

    tier_plain = {
        "strong": "exceptional varga strength - yogas involving this planet can deliver fully",
        "good": "solid good-division count - period results should be reliable",
        "moderate": "mixed varga strength - results depend on dasha support and transits",
        "weak": "few good divisions - promise may stay latent unless other factors rescue it",
    }
    note = f"{good}/{total} good divisions (dashavarga) - {tier_plain[tier]}."

    return {
        "available": True,
        "planet": planet,
        "good": good,
        "total": total,
        "tier": tier,
        "note": note,
        "source": BONEY_RULES_SOURCE,
    }


def adjust_verdict_by_crosscheck(base: str, tier: str) -> str:
    """Shift D1-only verdict one step using Boney D1-D9 cross-check tier."""
    idx = VERDICT_ORDER.index(base) if base in VERDICT_ORDER else 1
    if tier == "strong_both":
        idx = min(2, idx + 1)
    elif tier == "upgrade":
        idx = min(2, idx + 1)
    elif tier == "downgrade":
        idx = max(0, idx - 1)
    elif tier == "weak_both":
        idx = max(0, idx - 1)
    elif tier == "vargottama_debilitated" and idx == 0:
        idx = 1
    return VERDICT_ORDER[idx]


def _domain_period_summary(domain: str, window: dict[str, Any]) -> str:
    if not window.get("available"):
        return "Divisional data insufficient for Boney cross-check."
    varga = window.get("varga_key", "")
    if window.get("tri_confluence"):
        return f"D1+D9+{varga} agree for {domain} during this MD-AD pair."
    failed = []
    layers = window.get("layer_scores", {})
    if layers.get("D1", 0) < 0:
        failed.append("D1")
    if layers.get("D9", 0) < 1:
        failed.append("D9")
    if varga and layers.get(varga, 0) < 1:
        failed.append(varga)
    if failed:
        return f"Tri-chart gate soft ({', '.join(failed)}) for {domain} - timing needs other lanes."
    return window.get("note", "")[:180]


def score_active_period(md: str, ad: str, pc: dict) -> dict[str, Any]:
    """
    Active MD-AD analysis without event_kind: dignity cross-check, Vimshopaka,
    and per-domain divisional placement (career/marriage/children).
    """
    d9 = varga_from_divisional(pc, "D9")
    if not d9:
        return {"available": False, "note": "Navamsha missing - Boney period layer skipped."}

    md_cc = dignity_crosscheck_for_lord(pc, md)
    ad_cc = dignity_crosscheck_for_lord(pc, ad)
    md_vim = score_vimshopaka(pc, md)
    ad_vim = score_vimshopaka(pc, ad)

    domains: dict[str, Any] = {}
    for dk in ACTIVE_PERIOD_DOMAINS:
        w = score_boney_divisional_window(md_lord=md, ad_lord=ad, event_kind=dk, pc=pc)
        domains[dk] = {
            "available": w.get("available", False),
            "score": w.get("score", 0),
            "tri_confluence": w.get("tri_confluence", False),
            "varga_key": w.get("varga_key", ""),
            "summary": _domain_period_summary(dk, w),
            "note": w.get("note", "")[:220],
        }

    return {
        "available": True,
        "md_lord": md,
        "ad_lord": ad,
        "md_dignity": md_cc,
        "ad_dignity": ad_cc,
        "md_vimshopaka": md_vim,
        "ad_vimshopaka": ad_vim,
        "domains": domains,
        "source": BONEY_RULES_SOURCE,
    }


def boney_lord_snippet(pc: dict, planet: str) -> str:
    """One plain sentence for a period lord (dignity + vimshopaka)."""
    cc = dignity_crosscheck_for_lord(pc, planet)
    vim = score_vimshopaka(pc, planet)
    parts: list[str] = []
    if cc.get("available") and cc.get("note"):
        parts.append(cc["note"])
    if vim.get("available") and vim.get("tier") in ("weak", "strong"):
        parts.append(vim["note"])
    return " ".join(parts)


def render_boney_dasha_bridge(period: dict[str, Any]) -> str:
    """2-3 sentences for Bhardwaj dasha_section + Goel bridge."""
    if not period.get("available"):
        return ""
    md = period["md_lord"]
    ad = period["ad_lord"]
    md_cc = period.get("md_dignity", {})
    ad_cc = period.get("ad_dignity", {})
    career = period.get("domains", {}).get("career", {})
    marriage = period.get("domains", {}).get("marriage", {})

    lines = [
        f"<p class='pred'><strong>Boney divisional timing (rules45):</strong> "
        f"Mahadasha lord <strong>{html.escape(md)}</strong> - "
        f"{html.escape(md_cc.get('note', 'Navamsha cross-check pending.'))}</p>",
    ]
    if ad != md:
        lines.append(
            f"<p class='pred'>Antardasha lord <strong>{html.escape(ad)}</strong> - "
            f"{html.escape(ad_cc.get('note', ''))}</p>"
        )
    dom_bits = []
    if career.get("available"):
        dom_bits.append(f"career ({career.get('summary', '')})")
    if marriage.get("available"):
        dom_bits.append(f"partnership ({marriage.get('summary', '')})")
    if dom_bits:
        lines.append(
            "<p class='fine'>Current MD-AD in divisional charts: "
            + html.escape("; ".join(dom_bits))
            + ".</p>"
        )
    return "".join(lines)


def render_boney_period_block(period: dict[str, Any]) -> str:
    """HTML callout for Vimshottari active period."""
    if not period.get("available"):
        return ""
    md = period["md_lord"]
    ad = period["ad_lord"]
    md_vim = period.get("md_vimshopaka", {})
    body = (
        f"<p class='pred'><strong>Boney divisional layer (rules45):</strong> "
        f"Active <strong>{html.escape(md)}-{html.escape(ad)}</strong>. "
        f"{html.escape(period['md_dignity'].get('note', ''))}</p>"
    )
    if ad != md:
        body += (
            f"<p class='pred'>Antardasha <strong>{html.escape(ad)}</strong>: "
            f"{html.escape(period['ad_dignity'].get('note', ''))}</p>"
        )
    if md_vim.get("available"):
        body += f"<p class='fine'>{html.escape(md_vim.get('note', ''))}</p>"
    return f"<div class='callout-mehta'>{body}</div>"


def render_boney_varga_goel_bridge(period: dict[str, Any], *, focus: str = "both") -> str:
    """Short bridge before Goel D9/D10 sections in Bhardwaj report."""
    if not period.get("available"):
        return ""
    md = period["md_lord"]
    ad = period["ad_lord"]
    marriage = period.get("domains", {}).get("marriage", {})
    career = period.get("domains", {}).get("career", {})
    bits = [
        f"Current dasha <strong>{html.escape(md)}-{html.escape(ad)}</strong> "
        f"should be read in Navamsha and Dashamsha, not only in the birth chart (Boney rules45)."
    ]
    if focus in ("both", "marriage") and marriage.get("available"):
        bits.append(html.escape(marriage.get("summary", "")))
    if focus in ("both", "career") and career.get("available"):
        bits.append(html.escape(career.get("summary", "")))
    return "<p class='fine'>" + " ".join(bits) + "</p>"
