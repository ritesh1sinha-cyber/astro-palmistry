#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
divisional_confluence_report.py — one HTML report per divisional chart (Varga).

Starts with D1 (Rashi / birth chart). Primary reading rules come from
divisional_chart-tillD10.pdf (OCR corpus). Confluence rows reuse the live
multi-technique engine (KP, Jaimini, Daśā, Aṣṭakavarga, pillar, etc.).

CLI:
    python divisional_confluence_report.py --varga D1 --name Sample
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Optional

from astro_precompute import SIGNS, SIGN_LORDS, get_dignity, house_sign
from client_question_engine import QuestionContext, evaluate_question_techniques, synthesize_answer
from client_report_html import client_css, finalize_report_html
from divisional_book_corpus import (
    D1_CONFLUENCE_LANES,
    D1_EXAMINATION_RULES,
    D1_HOUSE_SIGNIFICATIONS,
    D1_INTRO,
    D2_CONFLUENCE_LANES,
    D2_EXAMINATION_RULES,
    D2_HOUSE_SIGNIFICATIONS,
    D2_INTRO,
    D2_MANSAGRI_HORA,
    D3_CONFLUENCE_LANES,
    D3_EXAMINATION_RULES,
    D3_HOUSE_SIGNIFICATIONS,
    D3_INTRO,
    D3_NATURE_GUNA,
    D4_CONFLUENCE_LANES,
    D4_EXAMINATION_RULES,
    D4_HOUSE_SIGNIFICATIONS,
    D4_INTRO,
    D4_PART_DEITY,
    D7_CONFLUENCE_LANES,
    D7_EXAMINATION_RULES,
    D7_HOUSE_SIGNIFICATIONS,
    D7_INTRO,
    D7_SAPTAMSHA_LORDS,
    D9_CONFLUENCE_LANES,
    D9_EXAMINATION_RULES,
    D9_HOUSE_SIGNIFICATIONS,
    D9_INTRO,
    HIGHER_VARGA_CORPUS,
    lagna_key_planet_row,
    lagna_sign_reading,
)
from divisional_varga import (
    build_parashari_d2_chart,
    build_parashari_d3_chart,
    build_parashari_d4_chart,
    build_parashari_d7_chart,
    build_parashari_d9_chart,
    build_varga_chart_from_pc,
    D7_PART_LABELS,
    d7_part_index,
    hora_type_label,
    d3_decanate_index,
    sign_quality,
)
from house_confluence_report import (
    HOUSE_AREAS,
    PLANET_REMEDY,
    _e,
    _humanize_note,
    _planets_in_house,
    _sav_for_house,
    _sav_note,
    _verdict_word,
)
from goel_saptamsha_analysis import analyze_saptamsha_chart
from goel_saptamsha_prose import saptamsha_client_cards
from goel_navamsha_analysis import analyze_navamsha_chart
from varga_goel_inspection import goel_inspection_html, inspect_d1_pillar, inspect_varga_chart
from varga_house_interpretation import build_d1_varga_chart, house_label, human_house_reading
from varga_rule_inspection import (
    SPECIAL_INSPECTORS,
    inspect_d9,
    inspect_varga_generic,
    rule_findings_html,
    rule_inspection_css,
    varga_remedy_deity_html,
)
from vedic_pillar_report import Pillar, SPECIAL_ASPECT
from vedic_vimshottari_report import Vim

BASE_DIR = Path(__file__).resolve().parent
GOEL_D7_BOOK = BASE_DIR / "goel_saptamsha_book_data.json"

# ─────────────────── shared dasha + narrative helpers ───────────────────


def _active_dasha(pc: dict) -> dict[str, str]:
    """Return active MD and AD lord + date info from precomputed chart."""
    vim = pc.get("vimshottari") or {}
    cmd = vim.get("current_md") or {}
    ads = vim.get("current_md_antardashas") or []
    md_lord = cmd.get("md_lord") or cmd.get("lord") or ""
    md_start = str(cmd.get("start", ""))[:10]
    md_end = str(cmd.get("end", ""))[:10]
    active_ad = next(
        (a for a in ads if a.get("status") == "current"),
        ads[0] if ads else {},
    )
    ad_lord = active_ad.get("ad_lord") or active_ad.get("lord") or ""
    ad_start = str(active_ad.get("start", ""))[:10]
    ad_end = str(active_ad.get("end", ""))[:10]
    return {
        "md_lord": md_lord, "md_start": md_start, "md_end": md_end,
        "ad_lord": ad_lord, "ad_start": ad_start, "ad_end": ad_end,
    }


_PLANET_NATURE: dict[str, str] = {
    "Sun":     "authority, leadership, father, vitality, and the will to shine",
    "Moon":    "mind, emotions, mother, home, public dealings, and nurturing",
    "Mars":    "courage, drive, ambition, siblings, property, and physical energy",
    "Mercury": "intelligence, communication, trade, skills, and analytical ability",
    "Jupiter": "wisdom, teaching, wealth, children, spirituality, and expansion",
    "Venus":   "beauty, relationships, creativity, luxury, and sensory pleasure",
    "Saturn":  "discipline, persistence, service, longevity, and karmic lessons",
    "Rahu":    "worldly desire, obsession, innovation, foreign things, and intensity",
    "Ketu":    "spiritual liberation, detachment, past-life gifts, and letting go",
}

_HOUSE_MEANING: dict[int, str] = {
    1:  "your identity, health, and the first impression you make on the world",
    2:  "accumulated wealth, speech, family, and what you hold dear",
    3:  "courage, personal initiative, communication, and younger siblings",
    4:  "home life, mother, emotional foundations, land, and inner peace",
    5:  "creativity, children, intellect, and the actions born of pure joy",
    6:  "daily work, health challenges, rivals, and the discipline to overcome them",
    7:  "partnerships, marriage, business alliances, and the public",
    8:  "transformation, sudden changes, hidden assets, longevity, and legacy",
    9:  "fortune, higher learning, father's legacy, and dharma",
    10: "career, public status, authority, and the deeds you are remembered for",
    11: "gains, social network, elder siblings, and the fulfilment of desires",
    12: "expenditure, solitude, spiritual liberation, and matters far from home",
}

_DIGNITY_SENTENCE: dict[str, str] = {
    "exalted":           "sits in its highest dignity — it delivers results with remarkable ease and strength.",
    "own_sign":          "occupies its own sign — fully in charge, giving reliable and unadulterated results.",
    "moolatrikona":      "is in moolatrikona — a powerful, mature placement that brings consistent benefit.",
    "great_friend_sign": "is in a great friend's sign — it cooperates willingly and produces good results.",
    "friendly":          "is in a friendly sign — supportive results, though some friction is possible.",
    "neutral_sign":      "is in a neutral sign — results come with effort; neither hindered nor especially helped.",
    "neutral":           "is in a neutral sign — results come with effort; neither hindered nor especially helped.",
    "enemy_sign":        "is in an enemy's sign — it must work against resistance; results arrive after struggle.",
    "debilitated":       "is debilitated — its significations face real difficulty; patience and focused remedies help.",
}


def _dig_sentence(dignity: str) -> str:
    return _DIGNITY_SENTENCE.get(dignity, _DIGNITY_SENTENCE["neutral"])


def _planet_para(planet: str, house: int, dignity: str, extra: str = "") -> str:
    nat = _PLANET_NATURE.get(planet, planet)
    h_m = _HOUSE_MEANING.get(house, f"house {house}")
    dig_s = _dig_sentence(dignity)
    txt = (
        f"<strong>{planet}</strong> — carrier of {nat} — sits in the house of "
        f"{h_m}. It {dig_s}"
    )
    if extra:
        txt += f" {extra}"
    return txt


def _lagna_intro(lagna: str, varga_label: str) -> str:
    traits: dict[str, str] = {
        "Aries":       "an Aries {v} lagna gives a direct, action-first quality. You lead by doing and trust your instincts.",
        "Taurus":      "a Taurus {v} lagna grounds everything in patience and persistence. You build slowly but surely, drawn to security and beauty.",
        "Gemini":      "a Gemini {v} lagna makes expression quick and multi-channelled. You gather information fast and adapt easily.",
        "Cancer":      "a Cancer {v} lagna channels all action through emotion and belonging. Loyalty and family ties drive your decisions.",
        "Leo":         "a Leo {v} lagna places authority and creative presence at the centre. You are drawn to lead and inspire.",
        "Virgo":       "a Virgo {v} lagna operates through analysis, precision, and service. You notice what others miss and feel compelled to improve.",
        "Libra":       "a Libra {v} lagna seeks balance and fairness. Partnerships and aesthetic values are central to how you operate.",
        "Scorpio":     "a Scorpio {v} lagna brings intensity and penetrating insight. You sense what lies beneath and handle crises better than most.",
        "Sagittarius": "a Sagittarius {v} lagna is expansive and freedom-seeking. Higher purpose guides your actions more than immediate utility.",
        "Capricorn":   "a Capricorn {v} lagna is systematic and built for the long game. Structure and sustained effort produce lasting results.",
        "Aquarius":    "an Aquarius {v} lagna thinks independently and works for collective goals. You bring originality and humanitarian intent.",
        "Pisces":      "a Pisces {v} lagna dissolves boundaries between self and world. Intuition and spiritual sensitivity shape your approach.",
    }
    return traits.get(lagna, f"{lagna} lagna shapes the {varga_label} chart.").replace("{v}", varga_label)


_VARGA_BENEFICS = frozenset({"Moon", "Mercury", "Jupiter", "Venus"})
_VARGA_MALEFICS = frozenset({"Sun", "Mars", "Saturn", "Rahu", "Ketu"})
_VARGA_TRIK = frozenset({6, 8, 12})
_VARGA_WEALTH = frozenset({1, 2, 5, 9, 10, 11})
_VARGA_KEY_HOUSES: dict[str, frozenset[int]] = {
    "D1": frozenset({1, 2, 3, 4, 5, 7, 9, 10, 11}),
    "D2": frozenset({1, 2, 9, 11, 12}),
    "D3": frozenset({1, 3, 5, 8, 9, 11}),
    "D4": frozenset({1, 4, 9, 10, 12}),
    "D7": frozenset({1, 5, 7, 9}),
    "D9": frozenset({1, 4, 7, 8, 9}),
}


def _evaluate_varga_house(
    h: int,
    chart: dict,
    varga: str,
) -> dict[str, Any]:
    """Score one divisional house from sign, lord, and tenants (not planet narratives)."""
    hs = chart["houses"].get(h, {})
    sign = hs.get("sign", "")
    lord = hs.get("lord", "")
    tenants: list[str] = list(hs.get("tenants") or [])
    lord_pl = chart["planets"].get(lord) or {}
    lord_h = lord_pl.get("house")
    lord_sign = lord_pl.get("sign", "")
    lord_dig = get_dignity(lord, lord_sign) if lord_sign else "unknown"

    score = 0
    notes: list[str] = []
    malefics = [p for p in tenants if p in _VARGA_MALEFICS]
    benefics = [p for p in tenants if p in _VARGA_BENEFICS]

    if varga == "D3" and h == 3:
        if malefics:
            score += 2
            notes.append("malefics in 3rd support raw courage (classical D3 rule)")
        elif benefics and not malefics:
            score -= 1
            notes.append("only benefics in 3rd — initiative may stay soft")
        elif tenants:
            notes.append(f"planets here: {', '.join(tenants)}")
        else:
            notes.append("empty — lord's placement decides")
    elif benefics and not malefics:
        score += 2
        notes.append(f"benefics ({', '.join(benefics)}) occupy this house")
    elif malefics and not benefics:
        score -= 2
        notes.append(f"malefics ({', '.join(malefics)}) occupy this house")
    elif tenants:
        notes.append(f"planets here: {', '.join(tenants)}")
    else:
        notes.append("empty — lord's placement decides")

    if lord_h in (1, 4, 5, 7, 9, 10, 11):
        score += 1
        notes.append(f"lord {lord} in house {lord_h} (supportive)")
    elif lord_h in _VARGA_TRIK:
        score -= 1
        notes.append(f"lord {lord} in trik house {lord_h}")

    if lord_dig in ("exalted", "own_sign", "moolatrikona"):
        score += 1
    elif lord_dig in ("debilitated", "enemy_sign"):
        score -= 1

    # Varga-specific classical adjustments
    if varga == "D2":
        if h == 12 and malefics:
            score -= 1
            notes.append("D2 12th malefic — expenditure / loss theme")
        if h == 2 and malefics and not benefics:
            score -= 1
            notes.append("D2 2nd afflicted — savings and consumption need discipline")
        if h in (2, 11) and benefics:
            score += 1
    elif varga == "D3":
        if h == 8 and malefics:
            score -= 1
    elif varga == "D4":
        if h == 4 and benefics:
            score += 1
        if h == 10 and "Mars" in tenants:
            score += 2
            notes.append("Mars in D4 10th — strong fixed-asset signature")
        if h == 9 and malefics and not benefics:
            score -= 1
            notes.append("afflicted 9th — relocation or fortune strain on home")
    elif varga == "D7":
        if h == 5 and benefics:
            score += 1
        if h == 5 and malefics and not benefics:
            score -= 2
        if h == 1 and "Jupiter" in tenants and len(tenants) == 1:
            score -= 1
            notes.append("Jupiter alone on D7 lagna can reduce desire for children")
    elif varga == "D9":
        if h == 7:
            if benefics and not malefics:
                score += 2
                notes.append("benefics on D9 7th support marriage (Bharyamsha)")
            elif malefics and not benefics:
                score -= 2
                notes.append("malefics on D9 7th strain partnership")
        if h == 4 and benefics:
            score += 1
            notes.append("benefics on D9 4th support marital happiness (Sukhamsha)")
        if h == 12 and "Venus" in tenants:
            score += 1
            notes.append("Venus in D9 12th — classical favourable exception")
        if h == 1 and tenants == ["Venus"]:
            score -= 2
            notes.append("Venus alone on D9 lagna — marriage desire may be reduced")
        if h == 1 and tenants == ["Jupiter"]:
            score -= 1
            notes.append("Jupiter alone on D9 lagna — check female-chart marriage rule")

    verdict = "positive" if score >= 2 else ("caution" if score <= -1 else "neutral")
    return {
        "house": h,
        "sign": sign,
        "lord": lord,
        "lord_house": lord_h,
        "lord_dignity": lord_dig,
        "tenants": tenants,
        "verdict": verdict,
        "notes": notes,
        "score": score,
    }


def _varga_house_examination_html(
    chart: dict,
    house_sigs: dict[int, str],
    varga: str,
    section_title: str,
) -> tuple[str, list[dict]]:
    """Prominent house-by-house examination in plain language."""
    readings: list[dict] = []
    for h in range(1, 13):
        ev = _evaluate_varga_house(h, chart, varga)
        ev["signification"] = house_sigs.get(h, "")
        ev["outcome"] = human_house_reading(varga, h, ev)
        ev["label"] = house_label(varga, h)
        readings.append(ev)

    key = _VARGA_KEY_HOUSES.get(varga, frozenset())
    blocks: list[str] = [
        f'<h2 class="section-h">{section_title}</h2>',
        '<div class="card"><p class="fine">Each section below is written for you personally — siblings, money, home, '
        "children, health, career, and so on — based on your chart's house lords and occupants, not generic textbook lines.</p></div>",
    ]
    for ev in readings:
        h = ev["house"]
        badge = {"positive": "Favourable", "caution": "Watch this", "neutral": "Mixed"}.get(ev["verdict"], "Mixed")
        cls = ev["verdict"]
        bdg_cls = {"positive": "pos", "caution": "cau", "neutral": "neu"}.get(cls, "neu")
        key_mark = " ★" if h in key else ""
        blocks.append(f'<div class="house-read {cls}">')
        blocks.append(
            f'<div class="house-read-hdr"><strong>House {h} — {_e(ev["label"])}{key_mark}</strong> '
            f'<span class="bdg {bdg_cls}">{badge}</span></div>'
        )
        blocks.append(f'<p>{ev["outcome"]}</p>')
        blocks.append("</div>")

    return "\n".join(blocks), readings


def _varga_examination_summary_html(
    readings: list[dict],
    varga: str,
    varga_theme: str,
) -> str:
    """Short conclusion from house examination scores."""
    supported = [r for r in readings if r["verdict"] == "positive"]
    stressed = [r for r in readings if r["verdict"] == "caution"]
    key = _VARGA_KEY_HOUSES.get(varga, frozenset())
    key_supported = [r for r in supported if r["house"] in key]
    key_stressed = [r for r in stressed if r["house"] in key]

    def _hlist(rs: list[dict]) -> str:
        if not rs:
            return "nothing stands out strongly"
        return "; ".join(f"{r.get('label', house_label(varga, r['house']))}" for r in rs[:4])

    if key_supported and not key_stressed:
        verdict = f"Taken together, your {varga_theme} picture is largely favourable — the main life areas marked ★ look workable."
        tone = "positive"
    elif key_stressed and not key_supported:
        verdict = f"Your {varga_theme} chart puts real weight on the stressed areas below — timing, health checks, and remedies matter."
        tone = "caution"
    elif key_supported and key_stressed:
        verdict = f"You have both strong and weak zones for {varga_theme} — lean on the favourable areas while you fix the stressed ones."
        tone = "neutral"
    else:
        verdict = f"For {varga_theme}, no single house dominates — dasha periods and your own choices will decide how things unfold."
        tone = "neutral"

    return (
        f'<h2 class="section-h">Overall reading from your {varga} houses</h2>'
        f'<div class="card d7-conclusion {tone}">'
        f'<p class="verdict">{verdict}</p>'
        f'<p><strong>Life areas working for you:</strong> {_hlist(supported)}.</p>'
        f'<p><strong>Life areas to watch:</strong> {_hlist(stressed)}.</p>'
        f"</div>"
    )


VARGA_META: dict[str, dict[str, Any]] = {
    "D1": {
        "title": "Rashi Chart (D1)",
        "subtitle": "Birth chart — the main skeleton of your life",
        "factor": 1,
        "filename_tag": "Rashi",
    },
    "D2": {
        "title": "Hora Chart (D2)",
        "subtitle": "Wealth — Parashari Cancer / Leo hora",
        "factor": 2,
        "filename_tag": "Hora",
    },
    "D3": {
        "title": "Drekkana Chart (D3)",
        "subtitle": "Courage, siblings & karma fruits",
        "factor": 3,
        "filename_tag": "Drekkana",
    },
    "D4": {
        "title": "Chaturthamsha Chart (D4)",
        "subtitle": "Home, property & happiness",
        "factor": 4,
        "filename_tag": "Chaturthamsha",
    },
    "D7": {
        "title": "Saptamsha Chart (D7)",
        "subtitle": "Children, progeny & future lineage",
        "factor": 7,
        "filename_tag": "Saptamsha",
    },
    "D9": {
        "title": "Navamsha Chart (D9)",
        "subtitle": "Marriage, spouse & dharma maturity",
        "factor": 9,
        "filename_tag": "Navamsha",
    },
}

# Register higher vargas (D10-D60) from the book corpus.
for _v, _c in HIGHER_VARGA_CORPUS.items():
    VARGA_META.setdefault(_v, {
        "title": _c.get("title", f"{_v} Chart"),
        "subtitle": _c.get("subtitle", ""),
        "factor": _c.get("factor"),
        "filename_tag": _c.get("tag", _v),
    })
    _VARGA_KEY_HOUSES.setdefault(_v, frozenset(_c.get("key_houses", [])))

DIGNITY_PLAIN = {
    "exalted": "exalted",
    "debilitated": "debilitated",
    "own_sign": "own sign",
    "moolatrikona": "moolatrikona",
    "friendly": "friendly sign",
    "neutral": "neutral sign",
    "neutral_sign": "neutral sign",
    "enemy_sign": "enemy sign",
    "great_friend_sign": "great friend's sign",
}


def _hk(house_lords: dict, h: int) -> dict:
    return house_lords.get(h) or house_lords.get(str(h)) or {}


def _dignity_plain(dig: str) -> str:
    return DIGNITY_PLAIN.get(dig, dig.replace("_", " "))


def _house_confluence(pc: dict, house: int, birth_kw: dict) -> dict[str, Any]:
    area = HOUSE_AREAS[house]
    ctx = QuestionContext(
        question=area["question"],
        topic="general",
        domain=area["domain"],
        title=f"Your {area['title']}",
        intent="general",
        primary_house=house,
        houses=[house],
        favorable_houses=[],
        denying_houses=[],
    )
    verdicts = evaluate_question_techniques(ctx, pc, birth_kw=birth_kw)
    return synthesize_answer(ctx, verdicts)


def _chart_level_techniques(pc: dict, pillar: Pillar, birth_kw: dict) -> list[tuple[str, str, str]]:
    """Return (label, direction, note) for D1 chart-level confluence rows."""
    rows: list[tuple[str, str, str]] = []
    meta = pc.get("meta", {})
    lagna = meta.get("lagna_sign", "")
    ll = pillar.lagna_lord
    ll_pl = pillar.ll
    sc = pillar.score()

    if sc["overall"] >= 60:
        d_pillar = "positive"
    elif sc["overall"] >= 45:
        d_pillar = "neutral"
    else:
        d_pillar = "caution"
    rows.append((
        "Lagna pillar strength",
        d_pillar,
        f"Lagna {lagna}; {ll} in house {ll_pl['house']} ({_dignity_plain(ll_pl['dignity'])}) "
        f"— pillar {pillar.verdict_word(sc['overall']).lower()} ({sc['overall']}%).",
    ))

    sav = (pc.get("ashtakavarga") or {}).get("sav") or []
    if len(sav) >= 12:
        avg = sum(int(x) for x in sav[:12]) / 12
        d_sav = "positive" if avg >= 28 else ("caution" if avg < 24 else "neutral")
        rows.append(("Average SAV bindus", d_sav, f"Chart average {avg:.1f} bindus per sign (28+ supportive)."))

    d9 = (pc.get("divisional") or {}).get("D9") or {}
    d9_lagna = d9.get("Lagna", "")
    if d9_lagna:
        vargottama = d9_lagna == lagna
        d_v9 = "positive" if vargottama else "neutral"
        note = f"D9 lagna {d9_lagna}" + (" — same as D1 (vargottama lagna)." if vargottama else f"; D1 lagna {lagna}.")
        rows.append(("D9 lagna link", d_v9, note))

    vim = pc.get("vimshottari", {})
    md = vim.get("current_md", {}).get("md_lord", "")
    ad = next((a["ad_lord"] for a in vim.get("current_md_antardashas", []) if a.get("status") == "current"), "")
    ruled = pillar.rules.get(ll, [])
    d_vim = "positive" if md == ll or ad == ll or md in ruled or ad in ruled else "neutral"
    rows.append((
        "Vimśottarī activation",
        d_vim,
        f"Current {md}-{ad}; lagna lord {ll} rules houses {', '.join(str(h) for h in ruled) or '—'}.",
    ))

    ak = next((k for k in (pc.get("cara_karakas") or {}).get("karakas", []) if k.get("role") == "Atmakarak"), {})
    if ak.get("planet"):
        ak_h = pillar.planets.get(ak["planet"], {}).get("house", "?")
        rows.append(("Atmakaraka in D1", "neutral", f"{ak['planet']} (AK) in house {ak_h} — soul agenda in D1."))

    kp = pc.get("kp") or {}
    if kp.get("cusps"):
        try:
            from kp_event_timing import load_kp_chart
            from kp_chart import KPChart
            from datetime import date
            kpc = KPChart.from_block(pc, kp, date.fromisoformat(meta.get("dob", "2000-01-01")[:10]), meta.get("client", ""))
            csl1 = kpc.cusp_sublord(1) if hasattr(kpc, "cusp_sublord") else ""
            if csl1:
                rows.append(("KP lagna sub-lord", "neutral", f"Lagna cusp sub-lord: {csl1}."))
        except Exception:
            pass

    ctx1 = QuestionContext(
        "D1 chart", "general", "personality", "Self", "general", 1, [1], [], [],
    )
    for v in evaluate_question_techniques(ctx1, pc, birth_kw=birth_kw):
        if v.technique_id in ("chara_goel", "yogini_goel", "jaimini", "ashtakavarga") and v.direction != "abstain":
            rows.append((v.label, v.direction, _humanize_note(v.note)))

    return rows


def _aggregate_d1_confluence(house_scores: list[dict[str, Any]]) -> dict[str, Any]:
    pcts = [h["confluence_pct"] for h in house_scores]
    avg = int(round(sum(pcts) / len(pcts))) if pcts else 0
    pos = sum(h.get("positive_votes", 0) for h in house_scores)
    cau = sum(h.get("caution_votes", 0) for h in house_scores)
    neu = sum(h.get("neutral_votes", 0) for h in house_scores)
    if avg >= 70 and pos > cau:
        conf = "HIGH"
    elif avg >= 55:
        conf = "MODERATE"
    else:
        conf = "LOW"
    return {
        "confluence_pct": avg,
        "confidence": conf,
        "positive_votes": pos,
        "caution_votes": cau,
        "neutral_votes": neu,
    }


def _extra_css() -> str:
    return """
.vtag{font-size:.8rem;letter-spacing:.16em;text-transform:uppercase;opacity:.8}
.gauge{display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.gnum{font-size:2.6rem;font-weight:800;line-height:1}
.pill{display:inline-block;padding:3px 12px;border-radius:999px;font-size:.78rem;font-weight:700}
.pill.HIGH,.pill.VERY{background:#e6f4ea;color:#1f6b42}
.pill.MODERATE{background:#fdf2dd;color:#9a5a00}
.pill.LOW{background:#fae7e7;color:#9a2a2a}
table.tech{width:100%;border-collapse:collapse;font-size:.9rem;margin:8px 0 0}
table.tech th,table.tech td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--border);vertical-align:top}
table.tech th{font-size:.74rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.fam{font-weight:700;color:var(--accent);background:#f6f4fb}
.bdg{display:inline-block;padding:2px 9px;border-radius:999px;font-size:.74rem;font-weight:700;white-space:nowrap}
.bdg.pos{background:#e6f4ea;color:#1f6b42}
.bdg.cau{background:#fdf2dd;color:#9a5a00}
.bdg.neu{background:#eee;color:#555}
.rules li{margin:.35rem 0}
.planet-grid{font-size:.88rem}
.d7-conclusion{border-left:4px solid var(--accent);background:#f6f4fb;padding:18px 22px;margin:16px 0 24px;border-radius:8px}
.d7-conclusion p{margin:.55rem 0;line-height:1.55}
.d7-conclusion .verdict{font-size:1.05rem;font-weight:600;color:var(--accent)}
.d7-conclusion.positive{border-left-color:#1f6b42;background:#e6f4ea}
.d7-conclusion.caution{border-left-color:#9a5a00;background:#fdf2dd}
.d7-conclusion.neutral{border-left-color:#666;background:#f4f4f4}
.goel-card{margin:12px 0;padding:14px 18px;border-radius:8px;border:1px solid var(--border);background:var(--card)}
.goel-card.green{border-left:3px solid #1f6b42}
.goel-card.amber{border-left:3px solid #9a5a00}
.goel-card.neutral{border-left:3px solid #888}
.goel-card .goel-title{font-weight:700;margin-bottom:6px;color:var(--accent)}
.coverage-ok{color:#1f6b42}.coverage-partial{color:#9a5a00}
.house-read{margin:10px 0;padding:14px 18px;border-radius:8px;border:1px solid var(--border);background:var(--card)}
.house-read.positive{border-left:3px solid #1f6b42}
.house-read.caution{border-left:3px solid #9a5a00}
.house-read.neutral{border-left:3px solid #888}
.house-read-hdr{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:6px}
.house-sig{font-size:.88rem;color:var(--muted);margin:0 0 6px;font-style:italic}
.bdg.pos{background:#e6f4ea;color:#1f6b42}
.bdg.cau{background:#fdf2dd;color:#9a5a00}
""" + rule_inspection_css()


def generate_d1_confluence_html(pc: dict, client_name: str = "Client") -> tuple[str, dict]:
    meta = pc.get("meta", {})
    pillar = Pillar(pc)
    lagna = meta.get("lagna_sign", "")
    lagna_deg = meta.get("lagna_degree", "")
    try:
        lagna_deg = f"{float(lagna_deg):.1f}°"
    except (TypeError, ValueError):
        lagna_deg = str(lagna_deg)
    birth_kw = {"dob": meta.get("dob", ""), "birth_time": meta.get("birth_time", "")}

    house_scores = []
    house_rows = ""
    for h in range(1, 13):
        merged = _house_confluence(pc, h, birth_kw)
        house_scores.append(merged)
        hs = house_sign(h, lagna)
        lord_rec = _hk(pc.get("house_lords") or {}, h)
        lord = lord_rec.get("lord", SIGN_LORDS.get(hs, ""))
        tenants = ", ".join(n for n, _ in _planets_in_house(pc, h)) or "empty"
        sav = _sav_for_house(pc, hs)
        sav_txt = _sav_note(sav) if sav is not None else "SAV n/a"
        pct = merged["confluence_pct"]
        badge = "pos" if pct >= 60 else ("cau" if pct < 45 else "neu")
        house_rows += (
            f"<tr><td>House {h}</td>"
            f"<td>{_e(D1_HOUSE_SIGNIFICATIONS[h][:120])}…</td>"
            f"<td>{_e(hs)} · lord {_e(lord)} · {_e(tenants)} · {_e(sav_txt)}</td>"
            f'<td><span class="bdg {badge}">{pct}%</span></td></tr>'
        )

    merged = _aggregate_d1_confluence(house_scores)
    pct = merged["confluence_pct"]
    conf = merged["confidence"]
    conf_cls = "VERY" if conf.startswith("VERY") else conf
    verdict = _verdict_word(pct, merged["positive_votes"], merged["caution_votes"])

    sign_read = lagna_sign_reading(lagna)
    kp_row = lagna_key_planet_row(lagna)

    # Planet snapshot
    plines = []
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        pl = pillar.planets.get(name, {})
        body = pc.get("planets", {}).get(name, {})
        dig = _dignity_plain(pl.get("dignity", "neutral"))
        retro = " R" if pl.get("retro") else ""
        nak = body.get("nakshatra", "")
        plines.append(
            f"<tr><td>{_e(name)}</td><td>{_e(pl.get('sign',''))}</td>"
            f"<td>{pl.get('house','')}</td><td>{_e(dig)}{retro}</td>"
            f"<td>{_e(nak)}</td></tr>"
        )

    chart_tech = _chart_level_techniques(pc, pillar, birth_kw)
    tech_rows = ""
    tech_rows += '<tr><td class="fam" colspan="3">Primary book — D1 examination</td></tr>'
    for rule in D1_EXAMINATION_RULES[:4]:
        tech_rows += f"<tr><td>Examination rule</td><td><span class=\"bdg neu\">Reference</span></td><td>{_e(rule)}</td></tr>"
    tech_rows += '<tr><td class="fam" colspan="3">Confluence cross-check</td></tr>'
    for label, direction, note in chart_tech:
        btxt, cls = {"positive": ("Supportive", "pos"), "caution": ("Caution", "cau"), "neutral": ("Neutral", "neu")}.get(
            direction, ("Neutral", "neu")
        )
        tech_rows += f"<tr><td>{_e(label)}</td><td><span class=\"bdg {cls}\">{btxt}</span></td><td>{_e(note)}</td></tr>"

    rules_html = "".join(f"<li>{_e(r)}</li>" for r in D1_EXAMINATION_RULES)
    lanes_html = "".join(f"<li><strong>{_e(l)}</strong> — {_e(d)}</li>" for l, d in D1_CONFLUENCE_LANES)

    weak_houses = sorted(
        [(h, house_scores[h - 1]["confluence_pct"]) for h in range(1, 13)],
        key=lambda x: x[1],
    )[:3]
    strong_houses = sorted(
        [(h, house_scores[h - 1]["confluence_pct"]) for h in range(1, 13)],
        key=lambda x: -x[1],
    )[:3]

    # ── Narrative block ──────────────────────────────────────────────────
    dasha = _active_dasha(pc)
    md_lord = dasha["md_lord"]
    ad_lord = dasha["ad_lord"]
    md_end = dasha["md_end"]
    ad_start = dasha["ad_start"]
    ad_end = dasha["ad_end"]

    ll_name = pillar.lagna_lord
    ll_pl_data = pillar.ll
    ll_house = ll_pl_data.get("house")
    ll_dig = ll_pl_data.get("dignity", "neutral")

    lagna_intro_txt = _lagna_intro(lagna, "D1")
    ll_sentence = (
        f"Your lagna lord <strong>{ll_name}</strong> sits in house {ll_house} "
        f"({_e(ll_pl_data.get('sign',''))}, {_dignity_plain(ll_dig)}). "
        + _dig_sentence(ll_dig)
    )

    notable_paras = []
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        body = pc.get("planets", {}).get(name, {})
        dig = body.get("dignity", "neutral")
        h = body.get("house") or pillar.planets.get(name, {}).get("house")
        if not h:
            continue
        notable = dig in ("exalted", "own_sign", "moolatrikona", "debilitated") or h in (1, 5, 9, 10)
        if notable:
            d1_sign = body.get("sign", "")
            extra = ""
            d9_sign = ((pc.get("divisional") or {}).get("D9") or {}).get(name, "")
            if d9_sign and d9_sign == d1_sign:
                extra = f" In D9 it remains in {d9_sign} — a vargottama planet of exceptional strength."
            notable_paras.append(f"<p>{_planet_para(name, h, dig, extra)}</p>")
        if len(notable_paras) >= 4:
            break

    md_h = pillar.planets.get(md_lord, {}).get("house") or ""
    ad_h = pillar.planets.get(ad_lord, {}).get("house") or ""
    md_hm = _HOUSE_MEANING.get(md_h, f"house {md_h}") if md_h else ""
    ad_hm = _HOUSE_MEANING.get(ad_h, f"house {ad_h}") if ad_h else ""
    dasha_para = (
        f"Currently running <strong>{md_lord} Mahādaśā</strong> until {md_end}, "
        f"sub-period of <strong>{ad_lord}</strong> ({ad_start} → {ad_end}). "
    )
    if md_hm:
        dasha_para += f"{md_lord} governs {md_hm} — this is the overarching life theme for this entire cycle. "
    if ad_hm:
        dasha_para += f"The current sub-period brings {ad_lord}'s themes of {ad_hm} to the foreground. "
    strong_txt = ", ".join(f"house {h} ({p}%)" for h, p in strong_houses)
    weak_txt = ", ".join(f"house {h} ({p}%)" for h, p in weak_houses)
    dasha_para += (
        f"Your chart's strongest areas: {strong_txt}. "
        f"Areas asking more conscious work: {weak_txt}."
    )

    narrative_html = f"""
<h2 class="section-h">Your birth chart — who you are and how life moves through you</h2>
<div class="card"><p>In your D1 Rashi chart, {lagna_intro_txt} This is the master lens through which every other chart is read. {ll_sentence}</p></div>
<h2 class="section-h">Key planets and what they mean for your life</h2>
<div class="card">{''.join(notable_paras)}</div>
<h2 class="section-h">Current period — what the chart is activating right now</h2>
<div class="card"><p>{dasha_para}</p></div>
"""

    d1_chart = build_d1_varga_chart(pc)
    house_exam_html, house_readings = _varga_house_examination_html(
        d1_chart, D1_HOUSE_SIGNIFICATIONS, "D1",
        "Your twelve life areas — what they mean for you personally",
    )
    house_summary_html = _varga_examination_summary_html(house_readings, "D1", "life overall")
    house_summary_html += varga_remedy_deity_html(d1_chart, "D1", "", "your life overall")
    d1_inspection = inspect_d1_pillar(pillar, pc)
    goel_html = goel_inspection_html(d1_inspection, "Birth chart foundation — lagna & lagna lord strength")
    goel_html += rule_findings_html(
        inspect_varga_generic("D1", d1_chart, pc),
        title="Every Rashi rule, checked against your chart",
    )

    remedy_block = ""
    if pct < 55:
        ll = pillar.lagna_lord
        remedy_block = f"""
<div class="card amber">
  <h3>Strengthen the birth chart backbone</h3>
  <p>{_e(PLANET_REMEDY.get(ll, 'Honour the lagna lord through consistent daily discipline.'))}</p>
  <p class="fine">D1 is the trunk — strengthen lagna and lagna lord before working on any divisional chart.</p>
</div>"""

    today = datetime.now().strftime("%d %B %Y")
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>D1 Rashi Chart — {_e(client_name)}</title>
<style>{client_css()}{_extra_css()}</style></head><body>
<div class="wrap">
  <p class="vtag">Divisional chart · D1 · Rashi (birth chart)</p>
  <h1>Rashi Chart — your main life map</h1>
  <p class="lead">{_e(D1_INTRO)}</p>

  {narrative_html}

  {goel_html}

  {house_summary_html}

  {house_exam_html}

  {remedy_block}

  <h2 class="section-h">Lagna sign &amp; key planets for {_e(lagna)}</h2>
  <div class="card">
    <p><strong>Character:</strong> {_e(sign_read['trait'])}</p>
    <p><strong>Physical tone:</strong> {_e(sign_read['physical'])}</p>
    <p><strong>Mental tone:</strong> {_e(sign_read['mental'])}</p>
    <table class="tech" style="margin-top:.8rem">
      <tr><th>Role</th><th>Planets for {_e(lagna)} lagna</th></tr>
      <tr><td>Yogakaraka</td><td>{_e(kp_row.get('yogkaraka','—'))}</td></tr>
      <tr><td>Benefic</td><td>{_e(kp_row.get('benefic','—'))}</td></tr>
      <tr><td>Malefic</td><td>{_e(kp_row.get('malefic','—'))}</td></tr>
      <tr><td>Maraka</td><td>{_e(kp_row.get('maraka','—'))}</td></tr>
    </table>
    <p class="fine">{_e(kp_row.get('note',''))}</p>
  </div>

  <details>
  <summary class="sec-hdr">House snapshot table (reference)</summary>
  <div class="card">
    <table class="tech">
      <tr><th>House</th><th>What it covers</th><th>Your chart</th><th>Confluence</th></tr>
      {house_rows}
    </table>
  </div>
  </details>

  <details>
  <summary class="sec-hdr">Technical reference — confluence &amp; examination rules</summary>
  <div class="card">
    <div class="gauge">
      <div><div class="gnum">{pct}%</div><div class="tally">average house confluence</div></div>
      <div><span class="pill {conf_cls}">{conf}</span></div>
    </div>
    <p class="fine" style="margin-top:.4rem">Birth: {_e(meta.get('dob',''))} {_e(meta.get('birth_time',''))} · Lagna {_e(lagna)} {_e(lagna_deg)}</p>
    <table class="tech" style="margin-top:.8rem">
      <tr><th>Technique</th><th>Verdict</th><th>Reading</th></tr>
      {tech_rows}
    </table>
  </div>
  <div class="card">
    <h3>Graha snapshot</h3>
    <table class="tech planet-grid">
      <tr><th>Graha</th><th>Sign</th><th>House</th><th>Dignity</th><th>Nakshatra</th></tr>
      {''.join(plines)}
    </table>
  </div>
  <div class="card">
    <h3>Examination rules (primary book)</h3>
    <ul class="rules">{rules_html}</ul>
  </div>
  </details>

  <p class="fine">Report date: {_e(today)}</p>
</div>
</body></html>"""

    summary = {
        "varga": "D1",
        "confluence_pct": pct,
        "confidence": conf,
        "lagna": lagna,
        "lagna_lord": pillar.lagna_lord,
    }
    return finalize_report_html(doc, client_name), summary


def _finance_confluence(pc: dict, birth_kw: dict) -> dict[str, Any]:
    ctx = QuestionContext(
        question="How are my wealth, savings and financial gains?",
        topic="general",
        domain="finance",
        title="Wealth & Finance",
        intent="general",
        primary_house=2,
        houses=[2, 11, 9, 1],
        favorable_houses=[],
        denying_houses=[],
    )
    verdicts = evaluate_question_techniques(ctx, pc, birth_kw=birth_kw)
    return synthesize_answer(ctx, verdicts)


def _d2_technique_rows(d2: dict[str, Any], pc: dict, pillar: Pillar, birth_kw: dict) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    d2_lagna = d2["lagna"]
    ll = d2["lagna_lord"]
    rows.append(("D2 lagna hora", "neutral", f"{d2_lagna} — {d2['lagna_hora_type']}"))

    sun_n = len(d2["sun_hora_planets"])
    moon_n = len(d2["moon_hora_planets"])
    if sun_n > moon_n + 1:
        d_bal, bal_note = "positive", f"{sun_n} planets in Sun hora (Leo) vs {moon_n} in Moon hora — self-effort wealth tone dominates."
    elif moon_n > sun_n + 1:
        d_bal, bal_note = "neutral", f"{moon_n} planets in Moon hora (Cancer) vs {sun_n} in Sun hora — ancestral/family blessing tone dominates."
    else:
        d_bal, bal_note = "neutral", f"Mixed: {sun_n} in Sun hora, {moon_n} in Moon hora — both effort and inheritance channels active."
    rows.append(("Sun vs Moon hora balance", d_bal, bal_note))

    h2 = d2["houses"][2]
    h11 = d2["houses"][11]
    h2_lord = h2["lord"]
    h11_lord = h11["lord"]
    h2_pl = d2["planets"].get(h2_lord, {})
    if h2_pl:
        dig = get_dignity(h2_lord, h2_pl.get("d1_sign", ""))
        d2d = "positive" if dig in ("exalted", "own_sign", "moolatrikona") else (
            "caution" if dig in ("debilitated", "enemy_sign") else "neutral"
        )
        rows.append((
            "D2 2nd lord (accumulation)",
            d2d,
            f"{h2_lord} D2 house {h2_pl.get('house')} ({h2_pl.get('sign')}, {h2_pl.get('hora')} hora); "
            f"D1 {_dignity_plain(dig)} in {h2_pl.get('d1_sign')}.",
        ))
    rows.append((
        "D2 11th lord (gains)",
        "neutral",
        f"{h11_lord} rules D2 house 11 ({h11['sign']}); tenants: {', '.join(h11['tenants']) or 'none'}.",
    ))

    jup = d2["planets"].get("Jupiter", {})
    if jup:
        d_j = "positive" if jup["house"] in (1, 2, 4, 5, 7, 9, 10, 11) else (
            "caution" if jup["house"] in (6, 8, 12) else "neutral"
        )
        rows.append((
            "Jupiter in D2 (family karaka)",
            d_j,
            f"Jupiter in D2 house {jup['house']} ({jup['sign']}, {jup['hora']} hora) — book karaka for family prosperity.",
        ))

    ll_dig = d2.get("lagna_lord_dignity_d1", "neutral")
    ll_v_h = d2.get("lagna_lord_varga_house")
    ll_v_dig = d2.get("lagna_lord_dignity_varga", "unknown")
    if ll_v_h in (1, 4, 5, 7, 9, 10) and ll_v_dig in ("exalted", "own_sign", "moolatrikona"):
        d_ll = "positive"
        ll_note = f"{ll} in D2 house {ll_v_h} ({_dignity_plain(ll_v_dig)}) — strong D2 lagna lord for wealth."
    elif ll_v_h in (3, 6, 8, 12):
        d_ll = "caution"
        ll_note = f"{ll} in D2 house {ll_v_h} — dusthana; wealth channel needs deliberate work."
    elif ll_v_dig in ("debilitated", "enemy_sign"):
        d_ll = "caution"
        ll_note = f"{ll} in D2 house {ll_v_h} ({_dignity_plain(ll_v_dig)}) — weak D2 lagna lord."
    else:
        d_ll = "positive" if ll_dig in ("exalted", "own_sign", "moolatrikona") else (
            "caution" if ll_dig in ("debilitated", "enemy_sign") else "neutral"
        )
        ll_note = (
            f"{ll} in D2 house {ll_v_h} ({_dignity_plain(ll_v_dig)}); "
            f"D1 dignity {_dignity_plain(ll_dig)} in house {d2.get('lagna_lord_d1_house')}."
        )
    rows.append(("D2 lagna lord in D2", d_ll, ll_note))
    d1_ll = pillar.lagna_lord
    d1_ll_h = (d2["planets"].get(d1_ll) or {}).get("house")
    if d1_ll_h in (1, 4, 5, 7, 9, 10, 2, 11):
        rows.append(("D1 lagna lord in D2", "positive", f"Birth lagna lord {d1_ll} in D2 house {d1_ll_h}."))
    elif d1_ll_h in (3, 6, 8, 12):
        rows.append(("D1 lagna lord in D2", "caution", f"Birth lagna lord {d1_ll} in D2 house {d1_ll_h} — stress on wealth from D1 anchor."))

    d1_lagna = pc.get("meta", {}).get("lagna_sign", "")
    sav2 = _sav_for_house(pc, house_sign(2, d1_lagna))
    if sav2 is not None:
        d_s = "positive" if sav2 >= 28 else ("caution" if sav2 < 22 else "neutral")
        rows.append(("D1 2nd house SAV", d_s, _sav_note(sav2)))

    fin = _finance_confluence(pc, birth_kw)
    rows.append((
        "D1 finance confluence",
        "positive" if fin["confluence_pct"] >= 60 else ("caution" if fin["confluence_pct"] < 45 else "neutral"),
        f"Live multi-technique score on houses 2/11/9: {fin['confluence_pct']}% ({fin['confidence']} confidence).",
    ))

    ctx = QuestionContext(
        "Wealth timing", "general", "finance", "Wealth", "general", 2, [2, 11], [], [],
    )
    for v in evaluate_question_techniques(ctx, pc, birth_kw=birth_kw):
        if v.technique_id in ("vimshottari", "chara_goel", "yogini_goel", "kp") and v.direction != "abstain":
            rows.append((v.label, v.direction, _humanize_note(v.note)))
    return rows


def generate_d2_confluence_html(pc: dict, client_name: str = "Client") -> tuple[str, dict]:
    meta = pc.get("meta", {})
    pillar = Pillar(pc)
    d2 = build_parashari_d2_chart(pc)
    birth_kw = {"dob": meta.get("dob", ""), "birth_time": meta.get("birth_time", "")}

    tech_rows_list = _d2_technique_rows(d2, pc, pillar, birth_kw)
    pos = sum(1 for _, d, _ in tech_rows_list if d == "positive")
    cau = sum(1 for _, d, _ in tech_rows_list if d == "caution")
    pct = int(round(pos / max(len(tech_rows_list), 1) * 100))
    conf = "HIGH" if (pct >= 70 and pos > cau) else ("MODERATE" if pct >= 55 else "LOW")

    fin = _finance_confluence(pc, birth_kw)
    mansagri = D2_MANSAGRI_HORA.get(d2["lagna"], hora_type_label(d2["lagna"]))
    dasha = _active_dasha(pc)
    md_lord = dasha["md_lord"]
    ad_lord = dasha["ad_lord"]
    md_end = dasha["md_end"]
    ad_start = dasha["ad_start"]
    ad_end = dasha["ad_end"]

    # ── Narrative ─────────────────────────────────────────────────────────
    hora_type = d2["lagna_hora_type"]
    hora_channel = "self-effort and personal ambition" if d2["lagna"] == "Leo" else "family lineage, ancestral blessings, and nurturing relationships"
    ll = d2["lagna_lord"]
    ll_h = d2.get("lagna_lord_d1_house")
    ll_dig = d2.get("lagna_lord_dignity_d1", "neutral")
    ll_sign = d2.get("lagna_lord_d1_sign", "")

    lagna_para = (
        f"Your D2 (Hora) lagna is <strong>{_e(d2['lagna'])}</strong> — a <em>{hora_type.split('—')[0].strip()}</em> chart. "
        f"This tells the primary channel through which wealth enters your life: {hora_channel}. "
        f"{_e(mansagri)} "
        f"The lagna lord is <strong>{_e(ll)}</strong>, placed in D1 house {ll_h} "
        f"({_e(ll_sign)}, {_dignity_plain(ll_dig)}). {_dig_sentence(ll_dig)} "
        f"This means your wealth-generating capacity is {_dignity_plain(ll_dig).replace('_',' ')} and "
        + ("delivers results reliably." if ll_dig in ("exalted","own_sign","moolatrikona") else
           "requires consistent effort to convert income into savings." if ll_dig in ("friendly","neutral_sign","neutral") else
           "faces challenges; disciplined wealth practices and remedies are essential.")
    )

    # Notable D2 placements
    notable_paras = []
    wealth_houses = {1, 2, 5, 9, 10, 11}
    poverty_houses = {6, 8, 12}
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        b = d2["planets"].get(name)
        if not b:
            continue
        h = b["house"]
        d1_dig = get_dignity(name, b["d1_sign"])
        hora = b.get("hora", "")
        notable = h in wealth_houses or h in poverty_houses or d1_dig in ("exalted","debilitated")
        if notable:
            if h in poverty_houses:
                extra = f" In D2 house {h}, its wealth significations face obstacles — expenditure, hidden delays, or losses in that area."
            elif h in (1, 2, 11):
                extra = f" Placed in D2 house {h} (a wealth house), it actively supports financial accumulation."
            elif h in (5, 9, 10):
                extra = f" In D2 house {h}, wealth flows through fortune, learning, or career action."
            else:
                extra = ""
            if hora:
                extra += f" This planet operates in the {hora} hora ({hora_channel.split(',')[0]})."
            notable_paras.append(f"<p>{_planet_para(name, h, d1_dig, extra)}</p>")
        if len(notable_paras) >= 4:
            break

    # Dasha timing for wealth
    md_pl = d2["planets"].get(md_lord) or {}
    ad_pl = d2["planets"].get(ad_lord) or {}
    md_h = md_pl.get("house") or ""
    ad_h = ad_pl.get("house") or ""
    dasha_para = (
        f"Currently in <strong>{md_lord} Mahādaśā</strong> (until {md_end}), "
        f"sub-period of <strong>{ad_lord}</strong> ({ad_start} → {ad_end}). "
    )
    if md_h:
        md_hm = "wealth accumulation" if md_h in (1,2,11) else (
            "fortunate gains" if md_h in (5,9) else
            "financial challenges" if md_h in (6,8,12) else f"house {md_h} themes"
        )
        dasha_para += f"In your D2 chart, {md_lord} sits in house {md_h} — this Mahādaśā period is one of {md_hm}. "
    if ad_h:
        ad_hm = "wealth gains" if ad_h in (1,2,11) else (
            "fortune and opportunity" if ad_h in (5,9) else
            "financial caution needed" if ad_h in (6,8,12) else f"house {ad_h} activation"
        )
        dasha_para += f"The sub-period of {ad_lord} (D2 house {ad_h}) brings {ad_hm} for this short window. "
    dasha_para += (
        f"D1 finance confluence: {fin['confluence_pct']}%. "
        + ("Strong financial period overall." if fin['confluence_pct'] >= 65 else
           "Mixed financial signals — prioritise savings and avoid speculative risk." if fin['confluence_pct'] >= 50 else
           "Financial caution period — protect existing assets, avoid major outlays.")
    )

    narrative_html = f"""
<h2 class="section-h">How wealth moves through your chart</h2>
<div class="card"><p>{lagna_para}</p></div>
<h2 class="section-h">Key planets and their wealth impact</h2>
<div class="card">{''.join(notable_paras)}</div>
<h2 class="section-h">Current dasha — wealth timing right now</h2>
<div class="card"><p>{dasha_para}</p></div>
"""

    house_exam_html, house_readings = _varga_house_examination_html(
        d2, D2_HOUSE_SIGNIFICATIONS, "D2",
        "House examination — what each area of your wealth chart means for you",
    )
    house_summary_html = _varga_examination_summary_html(house_readings, "D2", "wealth and resources")
    house_summary_html += varga_remedy_deity_html(d2, "D2", "Jupiter", "wealth and resources")
    goel_result = inspect_varga_chart("D2", d2, pc, pillar.lagna_lord)
    goel_html = goel_inspection_html(goel_result)
    goel_html += rule_findings_html(
        inspect_varga_generic("D2", d2, pc),
        title="Every Hora rule, checked against your chart",
    )

    # Tables (technical reference)
    plines = []
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        b = d2["planets"].get(name)
        if not b:
            continue
        plines.append(
            f"<tr><td>{_e(name)}</td><td>{_e(b['sign'])}</td><td>{b['house']}</td>"
            f"<td>{_e(b['hora'])} hora</td><td>{_e(b['d1_sign'])} {b['d1_degree']:.1f}°</td></tr>"
        )

    house_rows = ""
    for h in range(1, 13):
        hs = d2["houses"][h]
        tenants = ", ".join(hs["tenants"]) or "empty"
        house_rows += (
            f"<tr><td>H{h}</td>"
            f"<td>{_e(D2_HOUSE_SIGNIFICATIONS[h][:90])}…</td>"
            f"<td>{_e(hs['sign'])} · {_e(hs['lord'])} · {_e(tenants)}</td></tr>"
        )

    tech_rows = '<tr><td class="fam" colspan="3">Examination rules (primary book)</td></tr>'
    for rule in D2_EXAMINATION_RULES[:4]:
        tech_rows += (
            f"<tr><td>Rule</td><td><span class='bdg neu'>Ref</span></td><td>{_e(rule)}</td></tr>"
        )
    tech_rows += '<tr><td class="fam" colspan="3">Live chart confluence</td></tr>'
    for label, direction, note in tech_rows_list:
        btxt, cls = {"positive": ("Supportive", "pos"), "caution": ("Caution", "cau"), "neutral": ("Neutral", "neu")}.get(
            direction, ("Neutral", "neu")
        )
        tech_rows += (
            f"<tr><td>{_e(label)}</td><td><span class='bdg {cls}'>{btxt}</span></td>"
            f"<td>{_e(note)}</td></tr>"
        )

    remedy_block = ""
    if pct < 55 or fin["confluence_pct"] < 50:
        remedy_block = f"""
<div class="card amber">
  <h3>Strengthening wealth (D2)</h3>
  <p>{_e(PLANET_REMEDY.get('Jupiter', ''))}</p>
  <p>{_e(PLANET_REMEDY.get(d2['lagna_lord'], ''))}</p>
  <p class="fine">Sun hora responds to personal effort and ambition; Moon hora responds to family respect and regular savings habits.</p>
</div>"""

    today = datetime.now().strftime("%d %B %Y")
    d1_lagna = meta.get("lagna_sign", "")
    try:
        lagna_deg_str = f"{float(meta.get('lagna_degree') or 0):.1f}°"
    except (TypeError, ValueError):
        lagna_deg_str = ""

    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>D2 Hora Chart — {_e(client_name)}</title>
<style>{client_css()}{_extra_css()}</style></head><body>
<div class="wrap">
  <p class="vtag">Divisional chart · D2 · Hora (wealth)</p>
  <h1>Hora Chart — Wealth &amp; Resources</h1>
  <p class="lead">{_e(D2_INTRO)}</p>

  {narrative_html}

  {goel_html}

  {house_summary_html}

  {house_exam_html}

  {remedy_block}

  <details>
  <summary class="sec-hdr">House snapshot table (reference)</summary>
  <div class="card">
    <table class="tech">
      <tr><th>House</th><th>What it means (D2)</th><th>Your hora chart</th></tr>
      {house_rows}
    </table>
  </div>
  </details>

  <details>
  <summary class="sec-hdr">Technical reference — confluence table</summary>
  <div class="card">
    <p class="fine">D1 lagna {_e(d1_lagna)} {_e(lagna_deg_str)} → D2 lagna {_e(d2['lagna'])}</p>
    <div class="gauge" style="margin:.4rem 0 .6rem">
      <div><div class="gnum">{pct}%</div><div class="tally">D2 technique support</div></div>
      <div><span class="pill {conf}">{conf}</span></div>
    </div>
    <table class="tech">
      <tr><th>Technique</th><th>Verdict</th><th>Detail</th></tr>
      {tech_rows}
    </table>
  </div>
  <div class="card">
    <h3>Graha snapshot (Parashari Hora)</h3>
    <table class="tech planet-grid">
      <tr><th>Graha</th><th>D2 sign</th><th>D2 H</th><th>Hora</th><th>D1 source</th></tr>
      {''.join(plines)}
    </table>
  </div>
  </details>

  <p class="fine">Report date: {_e(today)}</p>
</div>
</body></html>"""

    summary = {
        "varga": "D2",
        "confluence_pct": pct,
        "confidence": conf,
        "lagna": d2["lagna"],
        "lagna_lord": d2["lagna_lord"],
        "finance_confluence_pct": fin["confluence_pct"],
    }
    return finalize_report_html(doc, client_name), summary


# ─────────────────────────── D3 Drekkana ─────────────────────────────────


def _d3_technique_rows(
    d3: dict, pc: dict, pillar: Any, birth_kw: dict
) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []

    # 1. D3 lagna lord — Goel: must be well placed in D3 (not only D1)
    ll = d3["lagna_lord"]
    ll_v_h = d3.get("lagna_lord_varga_house")
    ll_v_dig = d3.get("lagna_lord_dignity_varga", "unknown")
    ll_d1_dig = d3["lagna_lord_dignity_d1"]
    if ll_v_h in (1, 4, 5, 7, 9, 10) and ll_v_dig in ("exalted", "own_sign", "moolatrikona"):
        rows.append(("D3 lagna lord in D3", "positive",
                     f"{ll} in D3 house {ll_v_h} ({_dignity_plain(ll_v_dig)}) — strong D3 foundation for sibling/courage themes."))
    elif ll_v_h in (3, 6, 8, 12):
        rows.append(("D3 lagna lord in D3", "caution",
                     f"{ll} in D3 house {ll_v_h} ({_dignity_plain(ll_v_dig)}) — dusthana placement; D3 results need effort."))
    elif ll_v_dig in ("debilitated", "enemy_sign"):
        rows.append(("D3 lagna lord in D3", "caution",
                     f"{ll} in D3 house {ll_v_h} ({_dignity_plain(ll_v_dig)}) — weak dignity slows D3 delivery."))
    else:
        rows.append(("D3 lagna lord in D3", "neutral",
                     f"{ll} in D3 house {ll_v_h} ({_dignity_plain(ll_v_dig)}) — moderate D3 lagna lord."))
    # D1 lagna lord in D3 (Goel rule 1 — birth lagna lord in divisional)
    d1_ll = pillar.lagna_lord
    d1_ll_h = (d3["planets"].get(d1_ll) or {}).get("house")
    if d1_ll_h in (1, 4, 5, 7, 9, 10, 2, 11):
        rows.append(("D1 lagna lord in D3", "positive",
                     f"Birth lagna lord {d1_ll} in D3 house {d1_ll_h} — trunk supports D3 karma fruits."))
    elif d1_ll_h in (3, 6, 8, 12):
        rows.append(("D1 lagna lord in D3", "caution",
                     f"Birth lagna lord {d1_ll} in D3 house {d1_ll_h} — birth-chart anchor under stress in D3."))
    # D3 lagna strength — tenants on D3 lagna
    lagna_t = d3["houses"].get(1, {}).get("tenants") or []
    if lagna_t and "Mars" not in lagna_t:
        benefics = [p for p in lagna_t if p in ("Moon", "Mercury", "Jupiter", "Venus")]
        if benefics:
            rows.append(("D3 lagna occupants", "positive",
                         f"Benefic(s) {', '.join(benefics)} on D3 lagna strengthen the chart."))
    elif not lagna_t:
        rows.append(("D3 lagna occupants", "neutral", "D3 lagna empty — strength rides on lagna lord placement."))

    # Legacy D1 dignity note for lagna lord
    if ll_d1_dig in ("exalted", "own_sign", "moolatrikona"):
        rows.append(("D3 lagna lord in D1", "positive",
                     f"{ll} in {_dignity_plain(ll_d1_dig)} in birth chart — supports D3 from D1 side."))
    elif ll_d1_dig in ("debilitated", "enemy_sign"):
        rows.append(("D3 lagna lord in D1", "caution",
                     f"{ll} in {_dignity_plain(ll_d1_dig)} in birth chart — D3 themes need more effort from D1 side."))

    # 2. D3 3rd house (courage/co-born)
    h3 = d3["houses"].get(3, {})
    tenants3 = h3.get("tenants", [])
    malefics = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
    if tenants3 and any(p in malefics for p in tenants3):
        rows.append(("D3 3rd house (courage)", "positive",
                     f"Malefic(s) {', '.join(t for t in tenants3 if t in malefics)} in D3 3rd — gives initiative and fighting spirit."))
    elif tenants3:
        rows.append(("D3 3rd house (courage)", "neutral",
                     f"Benefic(s) {', '.join(tenants3)} in D3 3rd — actions are gentle; drive comes from planning."))
    else:
        lord3 = h3.get("lord", "")
        l3_sign = (pc.get("planets", {}).get(lord3) or {}).get("sign", "")
        rows.append(("D3 3rd house (courage)", "neutral",
                     f"Empty D3 3rd; 3rd lord {lord3} in {l3_sign} in D1 — judge courage by lord's position."))

    # 3. D3 8th house / 22nd Drekkana
    d22_sign = d3.get("d22_sign", "")
    h8 = d3["houses"].get(8, {})
    tenants8 = h8.get("tenants", [])
    d22_note = f"22nd Drekkana (Kharesh) in {d22_sign}."
    if tenants8:
        rows.append(("22nd Drekkana / D3 8th", "caution",
                     d22_note + f" Planets {', '.join(tenants8)} in D3 8th — longevity theme needs attention."))
    else:
        rows.append(("22nd Drekkana / D3 8th", "neutral", d22_note + " D3 8th is unoccupied."))

    # 4. D1 Pillar strength
    ps = pillar.score()["overall"]
    if ps >= 7:
        rows.append(("Lagna pillar strength", "positive",
                     f"Pillar score {ps} — strong D1 lagna underpins D3 karma fruits."))
    elif ps >= 4:
        rows.append(("Lagna pillar strength", "neutral",
                     f"Pillar score {ps} — moderate D1 lagna; D3 delivery depends on effort."))
    else:
        rows.append(("Lagna pillar strength", "caution",
                     f"Pillar score {ps} — D1 lagna under stress; D3 karma delivery is variable."))

    # 5. Vimshottari — fixed: use _active_dasha, not nonexistent Vim methods
    dasha = _active_dasha(pc)
    md_lord = dasha["md_lord"]
    ad_lord = dasha["ad_lord"]
    action_lords = {
        SIGN_LORDS.get(d3["houses"].get(3, {}).get("sign", ""), ""),
        SIGN_LORDS.get(d3["houses"].get(11, {}).get("sign", ""), ""),
        "Mars",
    }
    if md_lord in action_lords or ad_lord in action_lords:
        rows.append(("Vimśottarī Daśā (D3 activation)", "positive",
                     f"Current {md_lord}–{ad_lord} daśā activates D3 courage/sibling themes directly."))
    else:
        rows.append(("Vimśottarī Daśā (D3 activation)", "neutral",
                     f"Current {md_lord}–{ad_lord} daśā is not a primary D3 activator this cycle."))

    # 6. Ashtakavarga SAV on D3 3rd house sign
    h3_sign = h3.get("sign", "")
    sav3 = _sav_for_house(pc, h3_sign)
    sav3_note = _sav_note(sav3)
    if sav3 is not None:
        direction3 = "positive" if sav3 >= 30 else ("neutral" if sav3 >= 25 else "caution")
        rows.append(("Aṣṭakavarga — D3 3rd house sign", direction3,
                     f"Sign {h3_sign}: {sav3_note}"))

    # 7. Ātma–jīvātma–paramātma (1-5-9) connection
    h5 = d3["houses"].get(5, {})
    h9 = d3["houses"].get(9, {})
    connected_lords = {ll, SIGN_LORDS.get(h5.get("sign", ""), ""), SIGN_LORDS.get(h9.get("sign", ""), "")}
    trinity_houses = {1, 5, 9}
    connected = any(
        (d3["planets"].get(lo) or {}).get("house") in trinity_houses
        for lo in connected_lords if lo
    )
    if connected:
        rows.append(("Ātma–jīvātma–paramātma (1-5-9)", "positive",
                     "Lords of D3 1st/5th/9th are inter-connected — purposeful, happy life indicated."))
    else:
        rows.append(("Ātma–jīvātma–paramātma (1-5-9)", "neutral",
                     "D3 1-5-9 lords not strongly connected; purpose unfolds gradually through effort."))

    return rows


def _d3_narrative(d3: dict, pc: dict, client_name: str) -> str:
    """Return HTML narrative paragraphs — the human reading of D3."""
    lagna = d3["lagna"]
    ll = d3["lagna_lord"]
    ll_house = d3.get("lagna_lord_d1_house")
    ll_dig = d3["lagna_lord_dignity_d1"]
    d22_sign = d3.get("d22_sign", "")
    dasha = _active_dasha(pc)
    md_lord = dasha["md_lord"]
    ad_lord = dasha["ad_lord"]
    ad_start = dasha["ad_start"]
    ad_end = dasha["ad_end"]
    md_end = dasha["md_end"]

    # Lagna para
    lagna_para = (
        f"In the Drekkana chart, {_lagna_intro(lagna, 'D3')} "
        f"This shapes how you approach personal effort, how you fight your battles, "
        f"and the pattern of karma fruits you experience over the course of life. "
        f"Your D3 lagna lord is <strong>{ll}</strong>, sitting in D3 house {d3.get('lagna_lord_varga_house')} "
        f"({_e(d3.get('lagna_lord_varga_sign',''))}, {_dignity_plain(d3.get('lagna_lord_dignity_varga','unknown'))}) "
        f"and in the birth chart in house {ll_house} "
        f"({_e(d3.get('lagna_lord_d1_sign',''))}, {_dignity_plain(ll_dig)}). "
    )
    ll_v_dig = d3.get("lagna_lord_dignity_varga", "unknown")
    if ll_v_dig in ("exalted", "own_sign", "moolatrikona"):
        lagna_para += (
            f"In D3 itself, {ll} is strong — sibling, courage, and karma themes have a solid base to deliver."
        )
    elif ll_v_dig in ("debilitated", "enemy_sign"):
        lagna_para += (
            f"In D3, {ll} is under pressure — courage and sibling results mature through friction. Remedies for {ll} directly strengthen your D3."
        )
    elif ll_dig in ("exalted", "own_sign", "moolatrikona"):
        lagna_para += (
            f"This is a strong position — {ll} fully backs your initiative, courage, and karma-bearing capacity."
        )
    elif ll_dig in ("debilitated", "enemy_sign"):
        lagna_para += (
            f"This is a challenging position — {ll} has to work uphill. Your courage and initiative are real, "
            f"but they mature through friction. Remedies for {ll} directly strengthen your D3."
        )
    else:
        lagna_para += (
            f"This gives a workmanlike quality — initiative develops steadily through consistent effort."
        )

    # Pick the 3 most notable placements
    notable_paras = []
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        b = d3["planets"].get(name)
        if not b:
            continue
        h = b["house"]
        sign = b["sign"]
        d1_sign = b["d1_sign"]
        d1_dig = get_dignity(name, d1_sign)
        notable = False
        extra = ""
        # Own sign in D3 is very significant
        if sign == d1_sign and name not in ("Rahu", "Ketu"):
            notable = True
            extra = f" Being in its own D1 sign ({d1_sign}) in D3 as well makes this a vargottama planet — its karma in D3 is especially strong and pure."
        elif d1_dig in ("exalted", "debilitated"):
            notable = True
        # Key D3 houses
        if h in (1, 3, 5, 8, 9, 10):
            notable = True
        if notable:
            guna = D3_NATURE_GUNA.get(b.get("guna_key", ""), "")
            guna_txt = f" The nature here is {guna.split('—')[0].strip().lower()}." if guna else ""
            notable_paras.append(
                f"<p>{_planet_para(name, h, d1_dig, extra)}{guna_txt}</p>"
            )
        if len(notable_paras) >= 4:
            break

    # Dasha reading
    md_pl = d3["planets"].get(md_lord) or {}
    ad_pl = d3["planets"].get(ad_lord) or {}
    md_house = md_pl.get("house")
    ad_house = ad_pl.get("house")
    dasha_para = (
        f"<strong>Right now</strong> you are running <strong>{md_lord} Mahādaśā</strong> "
        f"(until {md_end}), sub-period of <strong>{ad_lord}</strong> ({ad_start} → {ad_end}). "
    )
    if md_house:
        md_hm = _HOUSE_MEANING.get(md_house, f"house {md_house}")
        dasha_para += (
            f"In your D3 chart, {md_lord} sits in house {md_house} — the area of {md_hm}. "
            f"This entire Mahādaśā is therefore focusing your karma fruits around these themes. "
        )
    if ad_house:
        ad_hm = _HOUSE_MEANING.get(ad_house, f"house {ad_house}")
        dasha_para += (
            f"The current sub-period lord {ad_lord} occupies D3 house {ad_house} — "
            f"the area of {ad_hm}. "
        )
        if ad_house in (3,):
            dasha_para += "Courage, initiative, and sibling matters are front and centre during this sub-period. Take bold action."
        elif ad_house in (5,):
            dasha_para += "Creative and intellectual karma comes due. Also a time to re-evaluate your relationship with children or learning."
        elif ad_house in (8,):
            dasha_para += "This sub-period brings transformation — old patterns are being dismantled to make room for new karma."
        elif ad_house in (9,):
            dasha_para += "Fortune-bearing. Your luck factor and dharma path are activated. Travel, study, or a teacher may appear."
        elif ad_house in (12,):
            dasha_para += "Introspection, withdrawal, or foreign/spiritual matters become relevant. Effort-reward cycle may feel delayed — invest internally."
        else:
            dasha_para += f"The themes of {ad_hm} are active and ripe for conscious engagement."
    if d22_sign:
        dasha_para += (
            f" Note: the 22nd Drekkana (Kharesh) falls in {d22_sign} — avoid recklessness during sub-periods of its lord."
        )

    blocks = [
        '<h2 class="section-h">Your Drekkana — the nature of your effort and karma fruits</h2>',
        f'<div class="card"><p>{lagna_para}</p></div>',
        '<h2 class="section-h">Key placements and what they mean</h2>',
        f'<div class="card">{"".join(notable_paras)}</div>',
        '<h2 class="section-h">Current dasha in this chart</h2>',
        f'<div class="card"><p>{dasha_para}</p></div>',
    ]
    return "\n".join(blocks)


def generate_d3_confluence_html(pc: dict, client_name: str = "Client") -> tuple[str, dict]:
    meta = pc.get("meta", {})
    pillar = Pillar(pc)
    d3 = build_parashari_d3_chart(pc)
    birth_kw = {"dob": meta.get("dob", ""), "birth_time": meta.get("birth_time", "")}

    tech_rows_list = _d3_technique_rows(d3, pc, pillar, birth_kw)
    pos = sum(1 for _, d, _ in tech_rows_list if d == "positive")
    cau = sum(1 for _, d, _ in tech_rows_list if d == "caution")
    pct = int(round(pos / max(len(tech_rows_list), 1) * 100))
    conf = "HIGH" if (pct >= 70 and pos > cau) else ("MODERATE" if pct >= 55 else "LOW")

    narrative_html = _d3_narrative(d3, pc, client_name)

    house_exam_html, house_readings = _varga_house_examination_html(
        d3, D3_HOUSE_SIGNIFICATIONS, "D3",
        "House examination — siblings, courage & karma — what it means for you",
    )
    house_summary_html = _varga_examination_summary_html(house_readings, "D3", "courage, siblings and karma fruits")
    house_summary_html += varga_remedy_deity_html(d3, "D3", "Mars", "courage and siblings")
    goel_result = inspect_varga_chart("D3", d3, pc, pillar.lagna_lord)
    goel_html = goel_inspection_html(goel_result)
    goel_html += rule_findings_html(
        inspect_varga_generic("D3", d3, pc),
        title="Every Drekkana rule, checked against your chart",
    )

    # Planet snapshot table (technical reference)
    plines = []
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        b = d3["planets"].get(name)
        if not b:
            continue
        guna_desc = D3_NATURE_GUNA.get(b.get("guna_key", ""), "").split("—")[0].strip()
        plines.append(
            f"<tr><td>{_e(name)}</td><td>{_e(b['sign'])}</td><td>{b['house']}</td>"
            f"<td>Dec {b['decanate']}</td><td>{_e(guna_desc)}</td>"
            f"<td>{_e(b['d1_sign'])} {b['d1_degree']:.1f}°</td></tr>"
        )

    # House meaning grid
    house_rows = ""
    for h in range(1, 13):
        hs = d3["houses"][h]
        tenants = ", ".join(hs["tenants"]) or "empty"
        sig = D3_HOUSE_SIGNIFICATIONS.get(h, "")[:100]
        house_rows += (
            f"<tr><td>H{h}</td><td>{_e(sig)}…</td>"
            f"<td>{_e(hs['sign'])} · {_e(hs['lord'])} · {_e(tenants)}</td></tr>"
        )

    # Confluence table (technical)
    tech_rows = '<tr><td class="fam" colspan="3">Examination rules (primary book)</td></tr>'
    for rule in D3_EXAMINATION_RULES[:4]:
        tech_rows += (
            f"<tr><td>Rule</td><td><span class='bdg neu'>Ref</span></td><td>{_e(rule)}</td></tr>"
        )
    tech_rows += '<tr><td class="fam" colspan="3">Live chart confluence</td></tr>'
    for label, direction, note in tech_rows_list:
        btxt, cls = {"positive": ("Supportive", "pos"), "caution": ("Caution", "cau"), "neutral": ("Neutral", "neu")}.get(
            direction, ("Neutral", "neu")
        )
        tech_rows += (
            f"<tr><td>{_e(label)}</td><td><span class='bdg {cls}'>{btxt}</span></td>"
            f"<td>{_e(note)}</td></tr>"
        )

    d22_sign = d3.get("d22_sign", "")
    d1_lagna = meta.get("lagna_sign", "")
    try:
        lagna_deg_str = f"{float(meta.get('lagna_degree') or 0):.1f}°"
    except (TypeError, ValueError):
        lagna_deg_str = ""

    remedy_block = ""
    if pct < 55 or cau > pos:
        mars_remedy = PLANET_REMEDY.get("Mars", "Strengthen Mars through physical discipline and courage practice.")
        ll_remedy = PLANET_REMEDY.get(d3["lagna_lord"], "")
        remedy_block = f"""
<div class="card amber">
  <h3>Activating D3 (courage &amp; karma fruits)</h3>
  <p>{_e(mars_remedy)}</p>
  <p>{_e(ll_remedy)}</p>
  <p class="fine">D3 responds to consistent effort, honouring siblings, and taking initiative rather than waiting.</p>
</div>"""

    today = datetime.now().strftime("%d %B %Y")
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>D3 Drekkana — {_e(client_name)}</title>
<style>{client_css()}{_extra_css()}</style></head><body>
<div class="wrap">
  <p class="vtag">Divisional chart · D3 · Drekkana</p>
  <h1>Drekkana — Courage, Siblings &amp; Karma Fruits</h1>
  <p class="lead">{_e(D3_INTRO)}</p>

  {narrative_html}

  {goel_html}

  {house_summary_html}

  {house_exam_html}

  {remedy_block}

  <details>
  <summary class="sec-hdr">House snapshot table (reference)</summary>
  <div class="card">
    <table class="tech">
      <tr><th>House</th><th>What it governs in D3</th><th>Your D3 chart</th></tr>
      {house_rows}
    </table>
  </div>
  </details>

  <details>
  <summary class="sec-hdr">Technical reference — confluence table</summary>
  <div class="card">
    <p class="fine">D1 lagna {_e(d1_lagna)} {_e(lagna_deg_str)} → D3 lagna {_e(d3['lagna'])} · 22nd Drekkana (Kharesh): {_e(d22_sign)}</p>
    <div class="gauge" style="margin-bottom:.6rem">
      <div><div class="gnum">{pct}%</div><div class="tally">technique support</div></div>
      <div><span class="pill {conf}">{conf}</span></div>
    </div>
    <table class="tech">
      <tr><th>Technique</th><th>Verdict</th><th>Detail</th></tr>
      {tech_rows}
    </table>
  </div>
  <div class="card">
    <h3>Graha snapshot (Parashari Drekkana)</h3>
    <table class="tech planet-grid">
      <tr><th>Graha</th><th>D3 sign</th><th>D3 H</th><th>Dec</th><th>Guna</th><th>D1 source</th></tr>
      {''.join(plines)}
    </table>
  </div>
  </details>

  <p class="fine">Report date: {_e(today)}</p>
</div>
</body></html>"""

    summary = {
        "varga": "D3",
        "confluence_pct": pct,
        "confidence": conf,
        "lagna": d3["lagna"],
        "lagna_lord": d3["lagna_lord"],
        "d22_sign": d22_sign,
    }
    return finalize_report_html(doc, client_name), summary


# ─────────────────────────── D4 Chaturthamsha ────────────────────────────


def _home_confluence(pc: dict, birth_kw: dict) -> dict[str, Any]:
    ctx = QuestionContext(
        question="How are my home, property, mother and peace of mind?",
        topic="general",
        domain="property",
        title="Home & Property",
        intent="general",
        primary_house=4,
        houses=[4, 2, 11, 9],
        favorable_houses=[],
        denying_houses=[],
    )
    verdicts = evaluate_question_techniques(ctx, pc, birth_kw=birth_kw)
    return synthesize_answer(ctx, verdicts)


def _d4_technique_rows(
    d4: dict, pc: dict, pillar: Any, birth_kw: dict
) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    ll = d4["lagna_lord"]
    ll_dig = d4["lagna_lord_dignity_d1"]
    ll_v_h = d4.get("lagna_lord_varga_house")
    ll_v_dig = d4.get("lagna_lord_dignity_varga", "unknown")
    if ll_v_h in (1, 4, 5, 7, 9, 10) and ll_v_dig in ("exalted", "own_sign", "moolatrikona"):
        rows.append(("D4 lagna lord in D4", "positive",
                     f"{ll} in D4 house {ll_v_h} ({_dignity_plain(ll_v_dig)}) — strong foundation for home/property."))
    elif ll_v_h in (3, 6, 8, 12):
        rows.append(("D4 lagna lord in D4", "caution",
                     f"{ll} in D4 house {ll_v_h} — domestic happiness needs deliberate strengthening."))
    elif ll_v_dig in ("debilitated", "enemy_sign"):
        rows.append(("D4 lagna lord in D4", "caution",
                     f"{ll} in D4 house {ll_v_h} ({_dignity_plain(ll_v_dig)}) — weak D4 lagna lord."))
    else:
        rows.append(("D4 lagna lord in D4", "neutral",
                     f"{ll} in D4 house {ll_v_h} ({_dignity_plain(ll_v_dig)}) — moderate D4 lagna lord."))
    d1_ll = pillar.lagna_lord
    d1_ll_h = (d4["planets"].get(d1_ll) or {}).get("house")
    if d1_ll_h in (1, 4, 5, 7, 9, 10, 2, 11):
        rows.append(("D1 lagna lord in D4", "positive", f"Birth lagna lord {d1_ll} in D4 house {d1_ll_h}."))
    elif d1_ll_h in (3, 6, 8, 12):
        rows.append(("D1 lagna lord in D4", "caution", f"Birth lagna lord {d1_ll} in D4 house {d1_ll_h}."))
    moon_h = (d4["planets"].get("Moon") or {}).get("house")
    if moon_h in (1, 4, 5, 7, 9, 10, 2, 11):
        rows.append(("Moon karaka in D4", "positive", f"Moon (home karaka) in D4 house {moon_h}."))
    elif moon_h in (3, 6, 8, 12):
        rows.append(("Moon karaka in D4", "caution", f"Moon in D4 house {moon_h} — emotional/home karaka under stress."))
    if ll_dig in ("exalted", "own_sign", "moolatrikona"):
        rows.append(("D4 lagna lord in D1", "positive",
                     f"{ll} in {_dignity_plain(ll_dig)} in birth chart — D1 support for property."))
    elif ll_dig in ("debilitated", "enemy_sign"):
        rows.append(("D4 lagna lord in D1", "caution",
                     f"{ll} in {_dignity_plain(ll_dig)} in birth chart."))

    h4 = d4["houses"].get(4, {})
    tenants4 = h4.get("tenants", [])
    benefics = {"Moon", "Mercury", "Jupiter", "Venus"}
    if tenants4 and any(p in benefics for p in tenants4):
        rows.append(("D4 4th house (home/mother)", "positive",
                     f"Benefic(s) {', '.join(t for t in tenants4 if t in benefics)} in D4 4th — supports home, mother, and contentment."))
    elif tenants4:
        rows.append(("D4 4th house (home/mother)", "caution",
                     f"Malefic influence {', '.join(tenants4)} in D4 4th — domestic peace may face friction."))
    else:
        lord4 = h4.get("lord", "")
        l4_d4 = (d4["planets"].get(lord4) or {}).get("house", "")
        rows.append(("D4 4th house (home/mother)", "neutral",
                     f"Empty D4 4th; 4th lord {lord4} in D4 house {l4_d4} — judge home themes by lord placement."))

    mars = d4["planets"].get("Mars", {})
    if mars:
        mh = mars.get("house")
        if mh == 10:
            rows.append(("Mars in D4 (fixed assets)", "positive",
                         "Mars in D4 10th — best placement for land, buildings, and immovable property."))
        elif mh in (1, 4, 11):
            rows.append(("Mars in D4 (fixed assets)", "positive",
                         f"Mars in D4 house {mh} — supports ownership of property and fixed assets."))
        elif mh in (6, 8, 12):
            rows.append(("Mars in D4 (fixed assets)", "caution",
                         f"Mars in D4 house {mh} — property gains face obstacles or disputes."))
        else:
            rows.append(("Mars in D4 (fixed assets)", "neutral",
                         f"Mars in D4 house {mh} — mixed signal for land and buildings."))

    jup = d4["planets"].get("Jupiter", {})
    if jup:
        jh = jup.get("house")
        d_j = "positive" if jh in (1, 2, 4, 5, 7, 9, 10, 11) else (
            "caution" if jh in (6, 8, 12) else "neutral"
        )
        rows.append(("Jupiter in D4 (happiness karaka)", d_j,
                     f"Jupiter in D4 house {jh} ({jup.get('sign')}) — karaka for contentment and wise use of property."))

    ps = pillar.score()["overall"]
    if ps >= 60:
        rows.append(("Lagna pillar strength", "positive",
                     f"Pillar score {ps} — strong D1 lagna underpins D4 happiness."))
    elif ps >= 45:
        rows.append(("Lagna pillar strength", "neutral",
                     f"Pillar score {ps} — moderate D1 lagna; home themes depend on effort."))
    else:
        rows.append(("Lagna pillar strength", "caution",
                     f"Pillar score {ps} — D1 lagna under stress; property delivery is variable."))

    dasha = _active_dasha(pc)
    md_lord = dasha["md_lord"]
    ad_lord = dasha["ad_lord"]
    home_lords = {
        SIGN_LORDS.get(d4["houses"].get(4, {}).get("sign", ""), ""),
        "Moon", "Venus", "Mars",
    }
    if md_lord in home_lords or ad_lord in home_lords:
        rows.append(("Vimśottarī Daśā (D4 activation)", "positive",
                     f"Current {md_lord}–{ad_lord} daśā activates home, property, or mother themes."))
    else:
        rows.append(("Vimśottarī Daśā (D4 activation)", "neutral",
                     f"Current {md_lord}–{ad_lord} daśā is not a primary D4 activator this cycle."))

    h4_sign = h4.get("sign", "")
    d1_lagna = pc.get("meta", {}).get("lagna_sign", "")
    sav4 = _sav_for_house(pc, house_sign(4, d1_lagna))
    sav4_note = _sav_note(sav4)
    if sav4 is not None:
        direction4 = "positive" if sav4 >= 30 else ("neutral" if sav4 >= 25 else "caution")
        rows.append(("Aṣṭakavarga — D1 4th house", direction4, f"D1 4th house sign {house_sign(4, d1_lagna)}: {sav4_note}"))

    return rows


def _d4_narrative(d4: dict, pc: dict) -> str:
    lagna = d4["lagna"]
    ll = d4["lagna_lord"]
    ll_house = d4.get("lagna_lord_d1_house")
    ll_dig = d4["lagna_lord_dignity_d1"]
    lagna_part = d4.get("lagna_part", 1)
    part_deity = D4_PART_DEITY.get(lagna_part, d4.get("lagna_part_deity", ""))
    dasha = _active_dasha(pc)
    md_lord = dasha["md_lord"]
    ad_lord = dasha["ad_lord"]
    ad_start = dasha["ad_start"]
    ad_end = dasha["ad_end"]
    md_end = dasha["md_end"]

    part_name = part_deity.split("—")[0].strip()
    part_tail = (part_deity.split("—", 1)[-1].strip() if "—" in part_deity else part_deity).rstrip(".")
    lagna_para = (
        f"In the Chaturthamsha chart, {_lagna_intro(lagna, 'D4')} "
        f"D4 is the map of your destiny through property, home, mother, and the happiness "
        f"you derive from what you own. Your lagna falls in the <strong>{part_name}</strong> "
        f"quarter — {part_tail}. "
        f"Your D4 lagna lord is <strong>{ll}</strong>, in D1 house {ll_house} "
        f"({_e(d4.get('lagna_lord_d1_sign', ''))}, {_dignity_plain(ll_dig)}). "
    )
    if ll_dig in ("exalted", "own_sign", "moolatrikona"):
        lagna_para += f"{ll} strongly backs your capacity for home, land, and lasting contentment."
    elif ll_dig in ("debilitated", "enemy_sign"):
        lagna_para += (
            f"{ll} works uphill here — property and peace of mind come through patience, "
            f"not instant gratification. Remedies for {ll} directly help D4."
        )
    else:
        lagna_para += "Steady effort builds domestic security over time."

    notable_paras = []
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        b = d4["planets"].get(name)
        if not b:
            continue
        h = b["house"]
        d1_dig = get_dignity(name, b["d1_sign"])
        notable = h in (1, 4, 9, 10, 12) or d1_dig in ("exalted", "debilitated") or name in ("Mars", "Jupiter", "Moon")
        if notable:
            part_txt = D4_PART_DEITY.get(b.get("part", 0), "")
            extra = ""
            if name == "Mars" and h == 10:
                extra = " Mars in D4 10th is the classic signature for owning land and built property."
            elif h == 4:
                extra = " Sitting in D4 4th, this directly colours mother, home, and inner peace."
            elif h == 12:
                extra = " D4 12th can indicate spending on home, foreign residence, or letting go of birthplace."
            elif part_txt:
                extra = f" In the {part_txt.split('—')[0].strip()} quarter of the sign."
            notable_paras.append(f"<p>{_planet_para(name, h, d1_dig, extra)}</p>")
        if len(notable_paras) >= 4:
            break

    md_pl = d4["planets"].get(md_lord) or {}
    ad_pl = d4["planets"].get(ad_lord) or {}
    md_h = md_pl.get("house")
    ad_h = ad_pl.get("house")
    dasha_para = (
        f"<strong>Right now</strong> you are in <strong>{md_lord} Mahādaśā</strong> (until {md_end}), "
        f"sub-period of <strong>{ad_lord}</strong> ({ad_start} → {ad_end}). "
    )
    if md_h:
        md_hm = _HOUSE_MEANING.get(md_h, f"house {md_h}")
        dasha_para += (
            f"In D4, {md_lord} sits in house {md_h} — the area of {md_hm}. "
            f"This Mahādaśā cycle shapes how property, home, and happiness unfold. "
        )
    if ad_h:
        ad_hm = _HOUSE_MEANING.get(ad_h, f"house {ad_h}")
        dasha_para += f"The sub-period lord {ad_lord} occupies D4 house {ad_h} — {ad_hm}. "
        if ad_h == 4:
            dasha_para += "Mother, home, and property matters are active now — good time to invest in domestic stability."
        elif ad_h == 9:
            dasha_para += "Fortune and possible change of residence; travel or relocation themes may surface."
        elif ad_h == 12:
            dasha_para += "Expenditure on home or a pull toward living away from birthplace — plan moves carefully."
        elif ad_h == 10:
            dasha_para += "Career and property link strongly — government land, office space, or status through assets."

    return "\n".join([
        '<h2 class="section-h">Your Chaturthamsha — home, property &amp; happiness</h2>',
        f'<div class="card"><p>{lagna_para}</p></div>',
        '<h2 class="section-h">Key placements and what they mean</h2>',
        f'<div class="card">{"".join(notable_paras)}</div>',
        '<h2 class="section-h">Current dasha in this chart</h2>',
        f'<div class="card"><p>{dasha_para}</p></div>',
    ])


def generate_d4_confluence_html(pc: dict, client_name: str = "Client") -> tuple[str, dict]:
    meta = pc.get("meta", {})
    pillar = Pillar(pc)
    d4 = build_parashari_d4_chart(pc)
    birth_kw = {"dob": meta.get("dob", ""), "birth_time": meta.get("birth_time", "")}

    tech_rows_list = _d4_technique_rows(d4, pc, pillar, birth_kw)
    pos = sum(1 for _, d, _ in tech_rows_list if d == "positive")
    cau = sum(1 for _, d, _ in tech_rows_list if d == "caution")
    pct = int(round(pos / max(len(tech_rows_list), 1) * 100))
    conf = "HIGH" if (pct >= 70 and pos > cau) else ("MODERATE" if pct >= 55 else "LOW")

    home = _home_confluence(pc, birth_kw)
    narrative_html = _d4_narrative(d4, pc)

    house_exam_html, house_readings = _varga_house_examination_html(
        d4, D4_HOUSE_SIGNIFICATIONS, "D4",
        "House examination — home, mother & property — what it means for you",
    )
    house_summary_html = _varga_examination_summary_html(house_readings, "D4", "home, property and happiness")
    house_summary_html += varga_remedy_deity_html(d4, "D4", "Moon", "home and happiness")
    goel_result = inspect_varga_chart("D4", d4, pc, pillar.lagna_lord)
    goel_html = goel_inspection_html(goel_result)
    goel_html += rule_findings_html(
        inspect_varga_generic("D4", d4, pc),
        title="Every Chaturthamsha rule, checked against your chart",
    )

    plines = []
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        b = d4["planets"].get(name)
        if not b:
            continue
        part_deity = D4_PART_DEITY.get(b.get("part", 0), "").split("—")[0].strip()
        plines.append(
            f"<tr><td>{_e(name)}</td><td>{_e(b['sign'])}</td><td>{b['house']}</td>"
            f"<td>Part {b['part']}</td><td>{_e(part_deity)}</td>"
            f"<td>{_e(b['d1_sign'])} {b['d1_degree']:.1f}°</td></tr>"
        )

    house_rows = ""
    for h in range(1, 13):
        hs = d4["houses"][h]
        tenants = ", ".join(hs["tenants"]) or "empty"
        sig = D4_HOUSE_SIGNIFICATIONS.get(h, "")[:100]
        house_rows += (
            f"<tr><td>H{h}</td><td>{_e(sig)}…</td>"
            f"<td>{_e(hs['sign'])} · {_e(hs['lord'])} · {_e(tenants)}</td></tr>"
        )

    tech_rows = '<tr><td class="fam" colspan="3">Examination rules (primary book)</td></tr>'
    for rule in D4_EXAMINATION_RULES[:4]:
        tech_rows += (
            f"<tr><td>Rule</td><td><span class='bdg neu'>Ref</span></td><td>{_e(rule)}</td></tr>"
        )
    tech_rows += '<tr><td class="fam" colspan="3">Live chart confluence</td></tr>'
    for label, direction, note in tech_rows_list:
        btxt, cls = {"positive": ("Supportive", "pos"), "caution": ("Caution", "cau"), "neutral": ("Neutral", "neu")}.get(
            direction, ("Neutral", "neu")
        )
        tech_rows += (
            f"<tr><td>{_e(label)}</td><td><span class='bdg {cls}'>{btxt}</span></td>"
            f"<td>{_e(note)}</td></tr>"
        )

    d1_lagna = meta.get("lagna_sign", "")
    try:
        lagna_deg_str = f"{float(meta.get('lagna_degree') or 0):.1f}°"
    except (TypeError, ValueError):
        lagna_deg_str = ""

    remedy_block = ""
    if pct < 55 or home["confluence_pct"] < 50:
        remedy_block = f"""
<div class="card amber">
  <h3>Strengthening home &amp; property (D4)</h3>
  <p>{_e(PLANET_REMEDY.get('Moon', 'Honour the mother principle; keep home peaceful and clean on Mondays.'))}</p>
  <p>{_e(PLANET_REMEDY.get(d4['lagna_lord'], ''))}</p>
  <p class="fine">D4 responds to respect for home, care for mother, and patient building of property rather than speculation.</p>
</div>"""

    today = datetime.now().strftime("%d %B %Y")
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>D4 Chaturthamsha — {_e(client_name)}</title>
<style>{client_css()}{_extra_css()}</style></head><body>
<div class="wrap">
  <p class="vtag">Divisional chart · D4 · Chaturthamsha (home &amp; property)</p>
  <h1>Chaturthamsha — Home, Property &amp; Happiness</h1>
  <p class="lead">{_e(D4_INTRO)}</p>

  {narrative_html}

  {goel_html}

  {house_summary_html}

  {house_exam_html}

  {remedy_block}

  <details>
  <summary class="sec-hdr">House snapshot table (reference)</summary>
  <div class="card">
    <table class="tech">
      <tr><th>House</th><th>What it governs in D4</th><th>Your D4 chart</th></tr>
      {house_rows}
    </table>
  </div>
  </details>

  <details>
  <summary class="sec-hdr">Technical reference — confluence table</summary>
  <div class="card">
    <p class="fine">D1 lagna {_e(d1_lagna)} {_e(lagna_deg_str)} → D4 lagna {_e(d4['lagna'])} · D1 home confluence: {home['confluence_pct']}%</p>
    <div class="gauge" style="margin-bottom:.6rem">
      <div><div class="gnum">{pct}%</div><div class="tally">D4 technique support</div></div>
      <div><span class="pill {conf}">{conf}</span></div>
    </div>
    <table class="tech">
      <tr><th>Technique</th><th>Verdict</th><th>Detail</th></tr>
      {tech_rows}
    </table>
  </div>
  <div class="card">
    <h3>Graha snapshot (Parashari Chaturthamsha)</h3>
    <table class="tech planet-grid">
      <tr><th>Graha</th><th>D4 sign</th><th>D4 H</th><th>Part</th><th>Deity quarter</th><th>D1 source</th></tr>
      {''.join(plines)}
    </table>
  </div>
  </details>

  <p class="fine">Report date: {_e(today)}</p>
</div>
</body></html>"""

    summary = {
        "varga": "D4",
        "confluence_pct": pct,
        "confidence": conf,
        "lagna": d4["lagna"],
        "lagna_lord": d4["lagna_lord"],
        "home_confluence_pct": home["confluence_pct"],
    }
    return finalize_report_html(doc, client_name), summary


# ══════════════════════════════════════════════════════════════════════════════
# D7 — Saptamsha: children, progeny, future lineage
# ══════════════════════════════════════════════════════════════════════════════

def _children_confluence(pc: dict) -> dict:
    """Evaluate D1 5th-house strength for children promise using Pillar."""
    try:
        p = Pillar(pc, 5)
        score = p.score()
        total = p.max_score() or 1
        pct = round(score / total * 100)
        conf = "high" if total >= 5 else ("medium" if total >= 3 else "low")
        verdict = "positive" if pct >= 60 else ("neutral" if pct >= 40 else "caution")
        return {"confluence_pct": float(pct), "confidence": conf, "verdict": verdict}
    except Exception:
        return {"confluence_pct": 50.0, "confidence": "low", "verdict": "neutral"}


def _d7_technique_rows(d7: dict, pc: dict) -> list[tuple[str, str, str]]:
    """Return list of (technique, verdict, note) for D7 techniques."""
    rows: list[tuple[str, str, str]] = []

    lagna = d7["lagna"]
    ll = d7["lagna_lord"]
    ll_dig = d7.get("lagna_lord_dignity_d7", "unknown")
    if ll_dig in ("exalted", "own_sign", "moolatrikona"):
        rows.append(("D7 Lagna lord", "positive", f"{ll} in {ll_dig} in D7 — strong progeny constitution."))
    elif ll_dig in ("debilitated", "enemy_sign"):
        rows.append(("D7 Lagna lord", "caution", f"{ll} in {ll_dig} in D7 — children may come after effort/delay."))
    else:
        rows.append(("D7 Lagna lord", "neutral", f"{ll} in {ll_dig} in D7 — average capacity; other factors decide."))

    # Jupiter in D7
    jup_h = d7.get("jupiter_d7_house")
    jup_sign = d7.get("jupiter_d7_sign", "")
    jup_d7_dig = get_dignity("Jupiter", jup_sign) if jup_sign else "unknown"
    if jup_h in (1, 5, 9):
        jup_v = "positive"
        jup_note = f"Jupiter (karaka for children) in D7 house {jup_h} — auspicious for progeny."
    elif jup_h in (6, 8, 12):
        jup_v = "caution"
        jup_note = f"Jupiter in D7 house {jup_h} — children karaka under pressure; timing and effort needed."
    else:
        jup_v = "neutral"
        jup_note = f"Jupiter in D7 house {jup_h} — moderate; aspect to 5th house matters."
    if jup_d7_dig in ("exalted", "debilitated"):
        jup_note += f" (Jupiter is {_dignity_plain(jup_d7_dig)} in D7.)"
    rows.append(("Jupiter in D7", jup_v, jup_note))

    # D7 5th house
    h5_d7 = d7["houses"].get(5, {})
    h5_sign = h5_d7.get("sign", "")
    h5_lord = h5_d7.get("lord", "")
    h5_tenants = h5_d7.get("tenants", [])
    h5_lord_data = d7["planets"].get(h5_lord) or {}
    h5_lord_house = h5_lord_data.get("house")
    malefics_in_5 = [p for p in h5_tenants if p in ("Saturn", "Mars", "Rahu", "Ketu", "Sun")]
    benefics_in_5 = [p for p in h5_tenants if p in ("Jupiter", "Venus", "Mercury", "Moon")]
    if benefics_in_5 and not malefics_in_5:
        rows.append(("D7 5th house", "positive", f"D7 5th ({h5_sign}) hosts {', '.join(benefics_in_5)} — benefic environment for children."))
    elif malefics_in_5 and not benefics_in_5:
        rows.append(("D7 5th house", "caution", f"D7 5th ({h5_sign}) afflicted by {', '.join(malefics_in_5)} — challenges in children matters."))
    elif h5_lord_house in (5, 9, 1, 11):
        rows.append(("D7 5th house", "positive", f"5th lord {h5_lord} in D7 house {h5_lord_house} — supportive for progeny."))
    elif h5_lord_house in (6, 8, 12):
        rows.append(("D7 5th house", "caution", f"5th lord {h5_lord} in D7 house {h5_lord_house} — 5th lord under stress."))
    else:
        rows.append(("D7 5th house", "neutral", f"D7 5th in {h5_sign}, lord {h5_lord} in house {h5_lord_house} — moderate indication."))

    # D7 7th house — children from second marriage (Rao book rule)
    h7_d7 = d7["houses"].get(7, {})
    h7_tenants = h7_d7.get("tenants", [])
    h7_lord = h7_d7.get("lord", "")
    if benefics_in_5 or jup_h in (1, 5, 9):
        if h7_tenants:
            rows.append(("D7 7th house (2nd marriage)", "neutral",
                         f"D7 7th ({h7_d7.get('sign','')}) has {', '.join(h7_tenants)} — "
                         "children from second marriage read here if applicable."))
    elif h7_lord:
        h7_lord_h = (d7["planets"].get(h7_lord) or {}).get("house")
        rows.append(("D7 7th house (2nd marriage)", "neutral",
                     f"7th lord {h7_lord} in D7 house {h7_lord_h} — second-marriage progeny axis."))

    # D1 5th house (confluence check)
    children_conf = _children_confluence(pc)
    rows.append(("D1 5th house (birth chart)", children_conf["verdict"],
                 f"Birth chart 5th house: {children_conf['confluence_pct']:.0f}% positive ({children_conf['confidence']} confidence)."))

    # Ashtakavarga D1 5th
    d1_lagna = pc.get("meta", {}).get("lagna_sign", "")
    sav5 = _sav_for_house(pc, house_sign(5, d1_lagna))
    sav5_note = _sav_note(sav5)
    if sav5 is not None:
        direction5 = "positive" if sav5 >= 30 else ("neutral" if sav5 >= 25 else "caution")
        rows.append(("Aṣṭakavarga — D1 5th house", direction5,
                     f"D1 5th house sign {house_sign(5, d1_lagna)}: {sav5_note}"))

    # Vimshottari Dasha activation
    dasha = _active_dasha(pc)
    md_lord = dasha["md_lord"]
    md_end = dasha["md_end"]
    md_pl = d7["planets"].get(md_lord) or {}
    md_h7 = md_pl.get("house")
    if md_h7 in (5, 9, 1, 11):
        rows.append(("Vimśottarī Daśā (D7 activation)", "positive",
                     f"{md_lord} Mahādaśā (until {md_end}): {md_lord} in D7 house {md_h7} — children themes active."))
    elif md_h7 in (6, 8, 12):
        rows.append(("Vimśottarī Daśā (D7 activation)", "caution",
                     f"{md_lord} Mahādaśā (until {md_end}): {md_lord} in D7 house {md_h7} — challenging period for progeny themes."))
    else:
        md_note = f"Dasha data available ({md_lord} MD until {md_end})" if md_lord != "N/A" else "Dasha data unavailable."
        rows.append(("Vimśottarī Daśā (D7 activation)", "neutral", md_note))

    return rows


def _d7_narrative(d7: dict, pc: dict) -> str:
    lagna = d7["lagna"]
    ll = d7["lagna_lord"]
    ll_house_d7 = d7.get("lagna_lord_d7_house")
    ll_dig_d7 = d7.get("lagna_lord_dignity_d7", "unknown")
    ll_house_d1 = d7.get("lagna_lord_d1_house")
    ll_dig_d1 = d7.get("lagna_lord_dignity_d1", "unknown")
    jup_h = d7.get("jupiter_d7_house")
    dasha = _active_dasha(pc)
    md_lord = dasha["md_lord"]
    ad_lord = dasha["ad_lord"]
    ad_start = dasha["ad_start"]
    ad_end = dasha["ad_end"]
    md_end = dasha["md_end"]

    lagna_para = (
        f"In the Saptamsha chart, {_lagna_intro(lagna, 'D7')} "
        f"D7 maps your lineage capacity — children born, their nature, and the continuation "
        f"of your family's story into the next generation. "
        f"Your D7 lagna lord is <strong>{ll}</strong>, sitting in D1 house {ll_house_d1} "
        f"({_e(d7.get('lagna_lord_d1_sign', ''))}, {_dignity_plain(ll_dig_d1)}) "
        f"and in D7 house {ll_house_d7} ({_dignity_plain(ll_dig_d7)}). "
    )
    if ll_dig_d7 in ("exalted", "own_sign", "moolatrikona"):
        lagna_para += f"{ll} powerfully secures your children's wellbeing and your bond with them."
    elif ll_dig_d7 in ("debilitated", "enemy_sign"):
        lagna_para += (
            f"{ll} is under strain in D7 — children may come through effort, or the relationship "
            f"with progeny may need conscious nurturing. Remedies for {ll} ease the path."
        )
    else:
        lagna_para += "Steady commitment to family brings the expected outcomes."

    # Jupiter paragraph
    if jup_h:
        jup_sign = d7.get("jupiter_d7_sign", "")
        jup_dig = get_dignity("Jupiter", jup_sign) if jup_sign else "unknown"
        if jup_h in (1, 5, 9):
            jup_para = (
                f"<strong>Jupiter</strong>, the primary karaka for children, occupies D7 house {jup_h} "
                f"— one of its strongest positions. This clearly supports the promise of children "
                f"and a warm parent–child bond. {_dig_sentence(jup_dig)}"
            )
        elif jup_h in (6, 8, 12):
            jup_para = (
                f"<strong>Jupiter</strong> (children's karaka) is in D7 house {jup_h}, a trik position. "
                f"Progeny themes need extra attention — timing, health of children, or delays may feature. "
                f"{_dig_sentence(jup_dig)}"
            )
        else:
            jup_para = (
                f"<strong>Jupiter</strong> (children's karaka) sits in D7 house {jup_h}. "
                f"Its aspect to the 5th house from here determines whether children flourish. "
                f"{_dig_sentence(jup_dig)}"
            )
    else:
        jup_para = ""

    notable_paras: list[str] = []
    if jup_para:
        notable_paras.append(f"<p>{jup_para}</p>")

    for name in ("Sun", "Moon", "Mars", "Mercury", "Venus", "Saturn", "Rahu", "Ketu"):
        b = d7["planets"].get(name)
        if not b:
            continue
        h = b["house"]
        d1_dig = get_dignity(name, b["d1_sign"])
        notable = h in (1, 5, 9, 12) or d1_dig in ("exalted", "debilitated")
        if notable:
            extra = ""
            if h == 5:
                extra = " Direct influence on D7 5th — shapes the environment of children's birth."
            elif h == 9:
                extra = " D7 9th gives luck and blessings to children; grandchildren also indicated."
            elif h == 12:
                extra = " D7 12th: children may live abroad, or a child theme of release or letting go."
            elif d1_dig == "exalted":
                extra = " Its exaltation power flows into the children's area it touches."
            elif d1_dig == "debilitated":
                extra = " Debilitation adds complexity to how this planet's D7 house theme plays out."
            notable_paras.append(f"<p>{_planet_para(name, h, d1_dig, extra)}</p>")
        if len(notable_paras) >= 5:
            break

    md_pl = d7["planets"].get(md_lord) or {}
    ad_pl = d7["planets"].get(ad_lord) or {}
    md_h = md_pl.get("house")
    ad_h = ad_pl.get("house")
    dasha_para = (
        f"<strong>Right now</strong> you are in <strong>{md_lord} Mahādaśā</strong> (until {md_end}), "
        f"sub-period of <strong>{ad_lord}</strong> ({ad_start} → {ad_end}). "
    )
    if md_h:
        md_hm = _HOUSE_MEANING.get(md_h, f"house {md_h}")
        dasha_para += (
            f"In D7, {md_lord} sits in house {md_h} — the area of {md_hm}. "
        )
        if md_h == 5:
            dasha_para += "The Mahādaśā directly activates the children's house — conception or major events around progeny likely."
        elif md_h == 9:
            dasha_para += "Fortune around children or grandchildren; blessed times for family expansion."
        elif md_h in (6, 8):
            dasha_para += "Some strain in progeny matters during this period; patience and health attention needed."
    if ad_h:
        ad_hm = _HOUSE_MEANING.get(ad_h, f"house {ad_h}")
        dasha_para += f"The sub-period lord {ad_lord} is in D7 house {ad_h} — {ad_hm}. "
        if ad_h == 5:
            dasha_para += "Sub-period activates 5th — a meaningful window for progeny events."
        elif ad_h == 11:
            dasha_para += "Fulfilment of children wish; gains through progeny."
        elif ad_h in (6, 8, 12):
            dasha_para += "Be attentive to children's health and wellbeing during this sub-period."

    return "\n".join([
        '<h2 class="section-h">Your Saptamsha — children &amp; future lineage</h2>',
        f'<div class="card"><p>{lagna_para}</p></div>',
        '<h2 class="section-h">Key placements and what they mean</h2>',
        f'<div class="card">{"".join(notable_paras)}</div>',
        '<h2 class="section-h">Current dasha in this chart</h2>',
        f'<div class="card"><p>{dasha_para}</p></div>',
    ])


def _load_goel_d7_book() -> dict:
    if GOEL_D7_BOOK.is_file():
        try:
            return json.loads(GOEL_D7_BOOK.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _is_female_chart(pc: dict) -> bool:
    g = pc.get("meta", {}).get("gender", pc.get("gender"))
    if g is None and pc.get("raw_sections", {}).get("gender") is not None:
        g = pc["raw_sections"]["gender"]
    return g == 1 or g == "female"


def _d7_promise_verdict(goel: dict) -> tuple[str, str]:
    """Return (tone, summary sentence) for overall D7 children promise."""
    denial = goel.get("denial_hits") or []
    score = goel.get("d7_lagna_score", 0)
    bc = goel.get("beeja_kshetra") or {}
    if denial:
        return "caution", (
            "Progeny is strained or blocked on the saptamsha map. "
            + denial[0]
            + ". Benefic support on D7 lagna or adoption paths may still apply."
        )
    if score >= 1 and bc.get("promise_ok"):
        return "positive", (
            "D7 confirms children promise — saptamsha lagna is supported and "
            "the fertility sphuta aligns with the classical odd/even sign rule."
        )
    if score >= 1:
        return "positive", (
            "D7 confirms the desire for children; saptamsha lagna is supported "
            "and effort can bear fruit even if sphuta needs pairing with dasha timing."
        )
    if score <= -1:
        return "caution", (
            "Malefic weight on saptamsha lagna — delay, fewer children, or a "
            "non-biological path needs honest consideration alongside remedies."
        )
    return "neutral", (
        "D7 is mixed — children are not denied outright, but timing, patience, "
        "and dasha cooperation matter more than in an open chart."
    )


def _d7_conclusion_html(goel: dict, pc: dict, d7: dict, book: dict) -> str:
    """Prominent D7 conclusion: promise, count, gender, timing, final verdict."""
    if goel.get("error"):
        return (
            '<h2 class="section-h">D7 conclusion — progeny reading</h2>'
            f'<div class="card d7-conclusion neutral"><p>{_e(goel["error"])}</p></div>'
        )

    tone, promise_text = _d7_promise_verdict(goel)
    cc = goel.get("child_count") or {}
    band = cc.get("band", "unclear")
    stop = cc.get("stop_reason", "")
    genders = goel.get("child_genders") or []
    timing = goel.get("children_timing_detail") or {}
    ages = timing.get("display_ages") or []
    final_say = book.get("d7_final_say", "D7 confirms or denies D1 fifth-house promise for progeny.")
    d1_conf = _children_confluence(pc)

    gender_lines: list[str] = []
    ord_map = {1: "First", 2: "Second", 3: "Third", 4: "Fourth", 5: "Fifth"}
    for g in genders[:5]:
        idx = g.get("child_index", len(gender_lines) + 1)
        ord_ = ord_map.get(idx, f"{idx}th")
        gender_lines.append(
            f"<strong>{ord_} child:</strong> {g.get('label', 'mixed')} indication "
            f"({g.get('method', 'child-house decider rule').replace('Goel ', '')})"
        )
    if not gender_lines:
        gender_lines.append("Gender sequence could not be derived — check D9 linkage.")

    count_para = f"<strong>Number of children:</strong> {band}."
    if stop:
        count_para += f" {stop}"
    bahu = (goel.get("extras") or {}).get("bahu_putra") or {}
    kak = (goel.get("extras") or {}).get("kakvandhya") or {}
    if bahu.get("active"):
        count_para += " Bahu Putra yoga suggests the upper band is possible when dasha supports."
    if kak.get("active"):
        count_para += " Kakvandhya yoga caps the count — treat as one child or difficulty conceiving again."
    count_para += " In classical saptamsha rules, the mother's chart weighs on count; the father's on sex."

    timing_para = ""
    if ages:
        timing_para = (
            f"<p><strong>Likely childbirth windows (approximate ages):</strong> "
            f"{', '.join(str(a) for a in ages)}.</p>"
        )

    # D7 vs D1 reconciliation
    d1_pct = d1_conf.get("confluence_pct", 50)
    if tone == "positive" and d1_pct >= 55:
        reconcile = (
            f"D1 fifth house ({d1_pct:.0f}% supported) and D7 both point toward progeny. "
            f"{final_say} Here, D7 <strong>confirms</strong> the birth-chart promise."
        )
    elif tone == "caution" and d1_pct >= 55:
        reconcile = (
            f"D1 fifth house looks open ({d1_pct:.0f}%), but D7 raises caution. "
            f"{final_say} Here, D7 <strong>delays or modifies</strong> what D1 suggests."
        )
    elif tone == "positive" and d1_pct < 45:
        reconcile = (
            f"D1 fifth house is weak ({d1_pct:.0f}%), yet D7 lagna supports children. "
            f"{final_say} Here, D7 <strong>overrides</strong> a weak D1 and keeps promise alive."
        )
    else:
        reconcile = f"{final_say} D1 fifth house at {d1_pct:.0f}%; D7 reading is {tone}."

    delay_note = ""
    if goel.get("saturn_delay"):
        relief = goel.get("saturn_delay_relief")
        delay_note = (
            "<p><strong>Delay factor:</strong> Saturn touches D7 lagna, 5th, or 9th — "
            "conception may wait. "
            + ("Benefic relief on Saturn shortens the delay." if relief
               else "Without benefic relief the wait can extend into the thirties.")
            + "</p>"
        )

    santana = (goel.get("extras") or {}).get("santana_tithi") or {}
    santana_para = ""
    if santana.get("computed"):
        santana_para = (
            f"<p><strong>Santana tithi (progeny karma):</strong> {santana.get('label', '')}. "
            f"{santana.get('verdict', '')}</p>"
        )

    bc = goel.get("beeja_kshetra") or {}
    sphuta_para = ""
    if bc.get("computed"):
        need = "even" if _is_female_chart(pc) else "odd"
        sphuta_para = (
            f"<p><strong>{bc.get('label', 'Sphuta')}:</strong> "
            f"D1 {bc.get('d1_sign')}, D9 {bc.get('d9_sign')}, D7 {bc.get('d7_sign')} "
            f"(house {bc.get('d7_house')}) — matches {need}-sign fertility rule in "
            f"{bc.get('match_count', 0)} of 3 charts."
            + (" Fertility sphuta supports progeny." if bc.get("promise_ok")
               else " Pair with Santana tithi and D7 lagna before a firm yes.")
            + "</p>"
        )

    gender_block = "<br/>".join(gender_lines)

    return "\n".join([
        '<h2 class="section-h">D7 conclusion — progeny reading</h2>',
        f'<div class="card d7-conclusion {tone}">',
        f'<p class="verdict">{promise_text}</p>',
        f'<p>{count_para}</p>',
        f'<p><strong>Gender indications:</strong><br/>{gender_block}</p>',
        timing_para,
        delay_note,
        santana_para,
        sphuta_para,
        f'<p><strong>Final D7 verdict:</strong> {reconcile}</p>',
        '</div>',
    ])


def _d7_goel_detail_html(goel: dict, female: bool) -> str:
    """Goel book topics as readable prediction cards (grandchildren, health, bond, etc.)."""
    if goel.get("error"):
        return ""
    cards = saptamsha_client_cards(goel, female)
    # Skip cards already covered in conclusion block
    skip = {"promise", "count", "beeja", "santana", "delay", "timing"}
    skip |= {f"gender_{i}" for i in range(1, 6)}
    filtered = [c for c in cards if c.get("theme_id") not in skip]
    if not filtered:
        return ""

    parts = ['<h2 class="section-h">Further D7 themes (children, lineage &amp; bond)</h2>']
    for c in filtered:
        parts.append(f'<div class="goel-card {c.get("tone", "neutral")}">')
        parts.append(f'<div class="goel-title">{_e(c["title"])}</div>')
        parts.append(f'<p>{_e(c["text"])}</p></div>')
    return "\n".join(parts)


def _d7_goel_technique_rows(goel: dict) -> list[tuple[str, str, str]]:
    """Technique rows from Goel coverage map (book JSON analysis themes)."""
    if goel.get("error"):
        return []
    rows: list[tuple[str, str, str]] = []
    coverage = goel.get("coverage") or {}
    for theme, (status, detail) in coverage.items():
        label = theme.replace("_", " ").title()
        verdict = "positive" if status == "checked" and "strong" in detail.lower() else (
            "caution" if status == "partial" or "risk" in detail.lower() or "weak" in detail.lower()
            else "neutral"
        )
        if theme == "child_gender" and detail:
            verdict = "neutral"
        if theme == "child_count" and ("several" in detail or "two to three" in detail):
            verdict = "positive"
        if theme == "d7_promise" and goel.get("d7_lagna_score", 0) >= 1:
            verdict = "positive"
        elif theme == "d7_promise" and goel.get("d7_lagna_score", 0) <= -1:
            verdict = "caution"
        rows.append((f"Saptamsha — {label}", verdict, detail))
    return rows


def generate_d7_confluence_html(pc: dict, client_name: str = "Client") -> tuple[str, dict]:
    meta = VARGA_META["D7"]
    today = datetime.now().strftime("%d %b %Y")
    d7 = build_parashari_d7_chart(pc)
    book = _load_goel_d7_book()
    female = _is_female_chart(pc)
    goel = analyze_saptamsha_chart(pc, female=female)

    rows = _d7_technique_rows(d7, pc) + _d7_goel_technique_rows(goel)
    pos = sum(1 for _, v, _ in rows if v == "positive")
    cau = sum(1 for _, v, _ in rows if v == "caution")
    tot = len(rows) or 1
    pct = round(pos / tot * 100)
    conf = "high" if tot >= 5 and (pos + cau) >= 4 else ("medium" if tot >= 3 else "low")

    conclusion = _d7_conclusion_html(goel, pc, d7, book)
    narrative = _d7_narrative(d7, pc)
    goel_detail = _d7_goel_detail_html(goel, female)

    house_exam_html, house_readings = _varga_house_examination_html(
        d7, D7_HOUSE_SIGNIFICATIONS, "D7",
        "House examination — children & lineage — what it means for you",
    )
    house_summary_html = _varga_examination_summary_html(house_readings, "D7", "children and lineage")
    house_summary_html += varga_remedy_deity_html(d7, "D7", "Jupiter", "children and progeny")
    pillar_d7 = Pillar(pc)
    goel_result = inspect_varga_chart("D7", d7, pc, pillar_d7.lagna_lord)
    goel_html = goel_inspection_html(goel_result)
    goel_html += rule_findings_html(
        inspect_varga_generic("D7", d7, pc),
        title="Every Saptamsha rule, checked against your chart",
    )

    remedy_planets = [ll for ll in [d7["lagna_lord"]] if ll]
    remedy_block = ""
    if remedy_planets:
        rems = [PLANET_REMEDY.get(p, "") for p in remedy_planets if PLANET_REMEDY.get(p)]
        if rems:
            remedy_block = (
                '<h2 class="section-h">Remedies &amp; strengthening</h2>'
                '<div class="card"><ul>'
                + "".join(f"<li>{_e(r)}</li>" for r in rems)
                + "</ul></div>"
            )

    # house table rows
    hrows = ""
    for h in range(1, 13):
        hd = d7["houses"].get(h, {})
        sig = D7_HOUSE_SIGNIFICATIONS.get(h, "")
        tenants = ", ".join(hd.get("tenants") or []) or "—"
        hrows += (
            f"<tr><td>{h}</td><td>{_e(hd.get('sign',''))}</td>"
            f"<td>{_e(hd.get('lord',''))}</td><td>{_e(tenants)}</td>"
            f"<td>{_e(sig)}</td></tr>"
        )

    # planet table rows
    plines = ""
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        b = d7["planets"].get(name)
        if not b:
            continue
        d7_dig = get_dignity(name, b["sign"]) if b["sign"] else "—"
        plines += (
            f"<tr><td>{name}</td><td>{_e(b['sign'])}</td><td>{b['house']}</td>"
            f"<td>{_e(_dignity_plain(d7_dig))}</td><td>{_e(b.get('part_label',''))}</td>"
            f"<td>{_e(b['d1_sign'])}</td></tr>"
        )

    # technique table rows
    trows = ""
    for tech, verdict, note in rows:
        badge = {"positive": "✔ Positive", "caution": "⚠ Caution", "neutral": "→ Neutral"}.get(verdict, verdict)
        trows += f"<tr><td>{_e(tech)}</td><td class='vd-{verdict}'>{badge}</td><td>{_e(note)}</td></tr>"

    # rules
    rule_items = "".join(f"<li>{_e(r)}</li>" for r in D7_EXAMINATION_RULES)
    lane_rows = "".join(
        f"<tr><td>{_e(lane)}</td><td>{_e(desc)}</td></tr>"
        for lane, desc in D7_CONFLUENCE_LANES
    )
    # saptamsha quality table
    sq_rows = "".join(
        f"<tr><td>{_e(k)}</td><td>{_e(v)}</td></tr>"
        for k, v in D7_SAPTAMSHA_LORDS.items()
    )

    lagna_part_label = ""
    lagna_d7_deg = d7.get("d1_lagna_degree", 0)
    lagna_part_label = D7_PART_LABELS.get(d7_part_index(lagna_d7_deg), "")

    cc = goel.get("child_count") or {}
    child_band = cc.get("band", "—")
    child_count_score = cc.get("count_score", 0)

    # Goel child-house sequence from book JSON
    seq_key = "even_lagna" if d7["lagna"] in (
        "Taurus", "Cancer", "Virgo", "Scorpio", "Capricorn", "Pisces"
    ) else "odd_lagna"
    child_seq = book.get("child_house_sequences", {}).get(seq_key, [])
    seq_txt = ", ".join(str(h) for h in child_seq[:6]) if child_seq else "5, 7, 9, …"

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{_e(meta['title'])} — {_e(client_name)}</title>
<style>
{client_css()}
{_extra_css()}
</style>
</head>
<body>
<div class="report-wrap">
  <h1>{_e(meta['title'])}</h1>
  <p class="subtitle">{_e(meta['subtitle'])}</p>
  <p><strong>Client:</strong> {_e(client_name)} &nbsp;|&nbsp;
     <strong>D7 lagna:</strong> {_e(d7['lagna'])} &nbsp;|&nbsp;
     <strong>Lagna lord:</strong> {_e(d7['lagna_lord'])} &nbsp;|&nbsp;
     <strong>Children (D7 reading):</strong> {_e(child_band)} &nbsp;|&nbsp;
     <strong>Confluence:</strong> {pct}%</p>

  {conclusion}

  {narrative}

  {goel_html}

  {goel_detail}

  {house_summary_html}

  {house_exam_html}

  {remedy_block}

  <details>
  <summary class="sec-hdr">House snapshot table (reference)</summary>
  <div class="card">
    <table>
      <tr><th>H</th><th>Sign</th><th>Lord</th><th>Tenants</th><th>Signification</th></tr>
      {hrows}
    </table>
  </div>
  </details>

  <details>
  <summary class="sec-hdr">Technical reference</summary>
  <div class="card">
    <h3>Confluence checks ({pct}% positive, {conf} confidence)</h3>
    <table>
      <tr><th>Technique</th><th>Verdict</th><th>Note</th></tr>
      {trows}
    </table>
    <h3>Child-house sequence ({seq_key.replace('_', ' ')})</h3>
    <p>Houses read for 1st, 2nd, 3rd child…: {_e(seq_txt)}</p>
    <h3>D7 analysis coverage</h3>
    <table class="tech">
      <tr><th>Theme</th><th>Status</th><th>Detail</th></tr>
      {''.join(
        f"<tr><td>{_e(k.replace('_',' ').title())}</td>"
        f"<td class='coverage-{('ok' if v[0]=='checked' else 'partial')}'>{_e(v[0])}</td>"
        f"<td>{_e(v[1])}</td></tr>"
        for k, v in (goel.get('coverage') or {}).items()
      ) if not goel.get('error') else '<tr><td colspan="3">Saptamsha analysis unavailable</td></tr>'}
    </table>
    <h3>Examination rules (Parashari Saptamsha)</h3>
    <ul>{rule_items}</ul>
    <h3>Confluence lanes (what to cross-check)</h3>
    <table>
      <tr><th>Lane</th><th>What it checks</th></tr>
      {lane_rows}
    </table>
    <h3>Saptamsha part quality</h3>
    <table>
      <tr><th>Part name</th><th>Meaning</th></tr>
      {sq_rows}
    </table>
    <h3>Graha snapshot in D7</h3>
    <table>
      <tr><th>Graha</th><th>D7 sign</th><th>D7 H</th><th>D7 dignity</th><th>Part</th><th>D1 source</th></tr>
      {plines}
    </table>
    <h3>About this chart</h3>
    <p>{_e(D7_INTRO)}</p>
  </div>
  </details>

  <p class="fine">Report date: {_e(today)}</p>
</div>
</body></html>"""

    summary = {
        "varga": "D7",
        "confluence_pct": pct,
        "confidence": conf,
        "lagna": d7["lagna"],
        "lagna_lord": d7["lagna_lord"],
        "jupiter_d7_house": d7.get("jupiter_d7_house"),
        "child_count_band": child_band,
        "child_count_score": child_count_score,
        "child_genders": [g.get("label") for g in (goel.get("child_genders") or [])],
        "d7_promise_tone": _d7_promise_verdict(goel)[0] if not goel.get("error") else "unknown",
    }
    return finalize_report_html(doc, client_name), summary


# ─────────────────────────── D9 Navamsha ─────────────────────────────────


def _d9_technique_rows(
    d9: dict, pc: dict, pillar: Any, nav: dict, female: bool
) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    ll = d9["lagna_lord"]
    ll_v_h = d9.get("lagna_lord_varga_house")
    ll_v_dig = d9.get("lagna_lord_dignity_varga", "unknown")

    if ll_v_h in (1, 4, 5, 7, 9, 10) and ll_v_dig in ("exalted", "own_sign", "moolatrikona"):
        rows.append(("D9 lagna lord in D9", "positive",
                     f"{ll} in D9 house {ll_v_h} ({_dignity_plain(ll_v_dig)}) — strong marriage/dharma foundation."))
    elif ll_v_h in (3, 6, 8, 12):
        rows.append(("D9 lagna lord in D9", "caution",
                     f"{ll} in D9 house {ll_v_h} — partnership themes need effort and timing."))
    else:
        rows.append(("D9 lagna lord in D9", "neutral",
                     f"{ll} in D9 house {ll_v_h} ({_dignity_plain(ll_v_dig)})."))

    d1_ll = pillar.lagna_lord
    d1_ll_h = (d9["planets"].get(d1_ll) or {}).get("house")
    if d1_ll_h in (1, 4, 5, 7, 9, 10, 2, 11):
        rows.append(("D1 lagna lord in D9", "positive", f"Birth lagna lord {d1_ll} in D9 house {d1_ll_h}."))
    elif d1_ll_h in (3, 6, 8, 12):
        rows.append(("D1 lagna lord in D9", "caution", f"Birth lagna lord {d1_ll} in D9 house {d1_ll_h}."))

    if d9.get("vargottama_lagna"):
        rows.append(("Vargottama lagna", "positive",
                     f"D9 lagna {d9['lagna']} same as D1 — inner and outer self align; navamsha results are pure."))

    h7 = d9["houses"].get(7, {})
    t7 = h7.get("tenants") or []
    malefics = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
    benefics = {"Moon", "Mercury", "Jupiter", "Venus"}
    if t7 and any(p in benefics for p in t7) and not any(p in malefics for p in t7):
        rows.append(("D9 7th house (marriage)", "positive",
                     f"Benefic(s) {', '.join(t7)} in D9 7th ({h7.get('sign','')}) — Bharyamsha supported."))
    elif t7 and any(p in malefics for p in t7) and not any(p in benefics for p in t7):
        rows.append(("D9 7th house (marriage)", "caution",
                     f"Malefic(s) {', '.join(t7)} in D9 7th — partnership needs care."))
    else:
        lord7 = h7.get("lord", "")
        l7h = (d9["planets"].get(lord7) or {}).get("house")
        rows.append(("D9 7th house (marriage)", "neutral",
                     f"D9 7th in {h7.get('sign','')}; lord {lord7} in D9 house {l7h}."))

    karaka = "Jupiter" if female else "Venus"
    k = d9["planets"].get(karaka) or {}
    if k:
        kh = k.get("house")
        kd = k.get("d9_dignity", "unknown")
        if kh in (1, 4, 5, 7, 9, 10, 2, 11) and kd in ("exalted", "own_sign", "moolatrikona"):
            rows.append((f"{karaka} karaka in D9", "positive",
                         f"{karaka} in D9 house {kh} ({_dignity_plain(kd)}) — marriage karaka strong."))
        elif kh == 12 and karaka == "Venus":
            rows.append((f"{karaka} karaka in D9", "positive",
                         f"Venus in D9 12th — classical favourable placement for marital comfort."))
        elif kh in (6, 8) or kd in ("debilitated", "enemy_sign"):
            rows.append((f"{karaka} karaka in D9", "caution",
                         f"{karaka} in D9 house {kh} ({_dignity_plain(kd)}) — karaka under pressure."))
        else:
            rows.append((f"{karaka} karaka in D9", "neutral",
                         f"{karaka} in D9 house {kh} ({_dignity_plain(kd)})."))

    pushkar = [n for n, b in d9["planets"].items() if b.get("pushkar")]
    if pushkar:
        rows.append(("Pushkar navamsha", "positive",
                     f"Pushkar pada: {', '.join(pushkar[:4])} — enhanced benefic results."))
    vish = [n for n, b in d9["planets"].items() if b.get("vish")]
    if vish:
        rows.append(("Vish navamsha", "caution",
                     f"Vish pada: {', '.join(vish[:4])} — caution in their dasha periods."))

    if nav.get("trajectory"):
        rows.append(("D1 → D9 trajectory", "positive",
                     "; ".join(nav["trajectory"][:2])))
    if nav.get("denial_hits"):
        rows.append(("Marriage denial flags", "caution",
                     "; ".join(nav["denial_hits"][:2])))
    elif not nav.get("error"):
        rows.append(("Marriage denial flags", "positive", "No strong denial cluster fired."))

    d1_h7 = nav.get("d1_h7_planets") or []
    if d1_h7:
        rows.append(("D1 7th vs D9 7th", "neutral",
                     f"D1 7th: {', '.join(d1_h7) or 'empty'}; D9 7th: {', '.join(t7) or 'empty'}."))

    ps = pillar.score()["overall"]
    if ps >= 7:
        rows.append(("Lagna pillar strength", "positive", f"Pillar score {ps} — D1 trunk supports D9."))
    elif ps >= 4:
        rows.append(("Lagna pillar strength", "neutral", f"Pillar score {ps} — moderate D1 support for D9."))
    else:
        rows.append(("Lagna pillar strength", "caution", f"Pillar score {ps} — strengthen D1 before expecting full D9 results."))

    dasha = _active_dasha(pc)
    md_lord = dasha["md_lord"]
    timing_lords = {ll, karaka, h7.get("lord", ""), nav.get("lord7_d9", "")} - {""}
    md_pl = d9["planets"].get(md_lord) or {}
    md_h = md_pl.get("house")
    if md_lord in timing_lords or md_h in (1, 4, 7, 9):
        rows.append(("Vimśottarī Daśā (D9 activation)", "positive",
                     f"{md_lord} Mahādaśā — in D9 house {md_h or '?'}; marriage/dharma themes active."))
    else:
        rows.append(("Vimśottarī Daśā (D9 activation)", "neutral",
                     f"Current {md_lord}–{dasha['ad_lord']} daśā — not primary D9 activator."))

    d1_lagna = pc.get("meta", {}).get("lagna_sign", "")
    sav7 = _sav_for_house(pc, house_sign(7, d1_lagna))
    if sav7 is not None:
        d_s = "positive" if sav7 >= 28 else ("caution" if sav7 < 22 else "neutral")
        rows.append(("D1 7th house SAV", d_s, _sav_note(sav7)))

    return rows


def _d9_conclusion_html(nav: dict, d9: dict) -> str:
    if nav.get("error"):
        return (
            '<h2 class="section-h">D9 conclusion — marriage &amp; dharma</h2>'
            f'<div class="card caution"><p class="verdict">{_e(nav["error"])}</p></div>'
        )

    denial = nav.get("denial_hits") or []
    trajectory = nav.get("trajectory") or []
    t7 = (d9["houses"].get(7) or {}).get("tenants") or []
    benefics = {"Moon", "Mercury", "Jupiter", "Venus"}

    if len(denial) >= 2:
        tone = "caution"
        verdict = (
            "Navamsha shows real stress on marriage promise — partner choice, timing, and remedies matter. "
            "This does not automatically deny union, but rushed marriage is not advised."
        )
    elif not denial and t7 and any(p in benefics for p in t7):
        tone = "positive"
        verdict = (
            "Navamsha supports marriage — the 7th house has protective influence and denial rules did not cluster. "
            "Partnership can be a genuine source of growth."
        )
    elif trajectory and any("D1 debil" in t for t in trajectory):
        tone = "positive"
        verdict = (
            "Several planets ripen more favourably in navamsha than in the birth chart — "
            "marriage and life quality often improve in the second half of life."
        )
    else:
        tone = "neutral"
        verdict = (
            "Marriage is mixed in navamsha — neither fully blocked nor effortlessly easy. "
            "Dasha periods of the 7th lord, Venus/Jupiter, and D9 lagna lord decide when promise becomes event."
        )

    if d9.get("vargottama_lagna"):
        verdict += " Vargottama lagna (same sign in D1 and D9) strengthens the whole reading."

    windows = nav.get("marriage_windows") or []
    if windows:
        win_txt = "; ".join(
            f"{w.get('lord', '?')} ({w.get('range', '')})" for w in windows[:3]
        )
    else:
        win_txt = "No dasha window flagged — see current period section."

    flags = nav.get("flags") or []
    flag_txt = ", ".join(flags[:4]) if flags else "none flagged"

    return (
        '<h2 class="section-h">D9 conclusion — marriage &amp; dharma</h2>'
        f'<div class="card d7-conclusion {tone}">'
        f'<p class="verdict">{verdict}</p>'
        f'<p><strong>Commitment timing (dasha):</strong> {_e(win_txt)}.</p>'
        f'<p><strong>Special navamsha flags:</strong> {_e(flag_txt)}.</p>'
        f"</div>"
    )


def _d9_narrative(d9: dict, pc: dict, nav: dict) -> str:
    lagna = d9["lagna"]
    d1_lagna = d9["d1_lagna"]
    ll = d9["lagna_lord"]
    ll_v_h = d9.get("lagna_lord_varga_house")
    ll_v_dig = d9.get("lagna_lord_dignity_varga", "unknown")
    ll_h_d1 = d9.get("lagna_lord_d1_house")
    ll_dig_d1 = d9.get("lagna_lord_dignity_d1", "unknown")
    dasha = _active_dasha(pc)
    md_lord = dasha["md_lord"]
    ad_lord = dasha["ad_lord"]
    ad_start = dasha["ad_start"]
    ad_end = dasha["ad_end"]
    md_end = dasha["md_end"]

    lagna_para = (
        f"In the Navamsha chart, {_lagna_intro(lagna, 'D9')} "
        f"D9 shows how your birth-chart promise matures — especially marriage, spouse, and inner dharma. "
        f"Your D9 lagna lord <strong>{ll}</strong> sits in D9 house {ll_v_h} "
        f"({_dignity_plain(ll_v_dig)}) and in the birth chart in house {ll_h_d1} "
        f"({_dignity_plain(ll_dig_d1)}). "
    )
    if d9.get("vargottama_lagna"):
        lagna_para += (
            f"Your D9 lagna <strong>{lagna}</strong> is the same as D1 — vargottama lagna — "
            f"so inner and outer life direction align strongly."
        )
    elif ll_v_dig in ("exalted", "own_sign", "moolatrikona"):
        lagna_para += f"{ll} is strong in D9 — partnership and dharma themes have a solid base."
    elif ll_v_dig in ("debilitated", "enemy_sign"):
        lagna_para += (
            f"{ll} is under pressure in D9 — marriage matures through lessons; "
            f"patience and remedies for {ll} help."
        )
    else:
        lagna_para += "Results unfold steadily as dasha activates the navamsha."

    notable_paras: list[str] = []
    for name in ("Venus", "Jupiter", "Moon", "Mars", "Saturn", "Mercury", "Sun", "Rahu", "Ketu"):
        b = d9["planets"].get(name)
        if not b:
            continue
        h = b["house"]
        notable = False
        extra = ""
        if b.get("vargottama"):
            notable = True
            extra = f" Vargottama in D9 — {name}'s navamsha promise is especially pure."
        if b.get("pushkar"):
            extra += " Pushkar navamsha pada — results enhanced."
        if b.get("vish"):
            extra += " Vish navamsha pada — dasha periods need caution."
        if h in (1, 4, 7, 8, 9, 12) or name in ("Venus", "Jupiter"):
            notable = True
        if b.get("d9_dignity") in ("exalted", "debilitated"):
            notable = True
        if notable:
            dig = b.get("d9_dignity", "unknown")
            notable_paras.append(f"<p>{_planet_para(name, h, dig, extra)}</p>")
        if len(notable_paras) >= 4:
            break

    md_pl = d9["planets"].get(md_lord) or {}
    ad_pl = d9["planets"].get(ad_lord) or {}
    md_h = md_pl.get("house")
    ad_h = ad_pl.get("house")
    dasha_para = (
        f"<strong>Right now</strong> you are in <strong>{md_lord} Mahādaśā</strong> (until {md_end}), "
        f"sub-period of <strong>{ad_lord}</strong> ({ad_start} → {ad_end}). "
    )
    if md_h:
        md_hm = _HOUSE_MEANING.get(md_h, f"house {md_h}")
        dasha_para += f"In D9, {md_lord} sits in house {md_h} — {md_hm}. "
        if md_h == 7:
            dasha_para += "This Mahādaśā strongly activates marriage and partnership themes."
        elif md_h in (4, 9):
            dasha_para += "Domestic happiness and dharma through union are emphasised."
    if ad_h:
        ad_hm = _HOUSE_MEANING.get(ad_h, f"house {ad_h}")
        dasha_para += f"The sub-period lord {ad_lord} is in D9 house {ad_h} — {ad_hm}."
    if nav.get("trajectory"):
        dasha_para += f" Trajectory note: {nav['trajectory'][0]}."

    return "\n".join([
        '<h2 class="section-h">Your Navamsha — marriage, spouse &amp; inner maturity</h2>',
        f'<div class="card"><p>{lagna_para}</p></div>',
        '<h2 class="section-h">Key placements and what they mean</h2>',
        f'<div class="card">{"".join(notable_paras) or "<p>See house examination below for full detail.</p>"}</div>',
        '<h2 class="section-h">Current dasha in this chart</h2>',
        f'<div class="card"><p>{dasha_para}</p></div>',
    ])


def generate_d9_confluence_html(pc: dict, client_name: str = "Client") -> tuple[str, dict]:
    meta = pc.get("meta", {})
    pillar = Pillar(pc)
    d9 = build_parashari_d9_chart(pc)
    female = _is_female_chart(pc)
    nav = analyze_navamsha_chart(pc)
    birth_kw = {"dob": meta.get("dob", ""), "birth_time": meta.get("birth_time", "")}

    tech_rows_list = _d9_technique_rows(d9, pc, pillar, nav, female)
    pos = sum(1 for _, d, _ in tech_rows_list if d == "positive")
    cau = sum(1 for _, d, _ in tech_rows_list if d == "caution")
    pct = int(round(pos / max(len(tech_rows_list), 1) * 100))
    conf = "HIGH" if (pct >= 70 and pos > cau) else ("MODERATE" if pct >= 55 else "LOW")

    narrative_html = _d9_narrative(d9, pc, nav)
    conclusion_html = _d9_conclusion_html(nav, d9)

    house_exam_html, house_readings = _varga_house_examination_html(
        d9, D9_HOUSE_SIGNIFICATIONS, "D9",
        "House examination — marriage &amp; dharma — what it means for you",
    )
    house_summary_html = _varga_examination_summary_html(
        house_readings, "D9", "marriage, partnership and dharma maturity",
    )
    house_summary_html += varga_remedy_deity_html(
        d9, "D9", "Jupiter" if female else "Venus", "marriage and partnership",
    )
    goel_result = inspect_varga_chart("D9", d9, pc, pillar.lagna_lord)
    goel_html = goel_inspection_html(goel_result)

    d9_findings = inspect_d9(d9, pc, nav)
    rule_html = rule_findings_html(
        d9_findings,
        title="Every navamsha rule, checked against your chart",
        intro="",
    )

    plines = []
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        b = d9["planets"].get(name)
        if not b:
            continue
        flags = []
        if b.get("vargottama"):
            flags.append("vargottama")
        if b.get("pushkar"):
            flags.append("pushkar")
        if b.get("vish"):
            flags.append("vish")
        flag_txt = ", ".join(flags) or "—"
        plines.append(
            f"<tr><td>{_e(name)}</td><td>{_e(b['sign'])}</td><td>{b['house']}</td>"
            f"<td>{_e(_dignity_plain(b.get('d9_dignity', 'unknown')))}</td>"
            f"<td>Pada {b.get('navamsha_part', '?')} · {_e(flag_txt)}</td>"
            f"<td>{_e(b['d1_sign'])} {b['d1_degree']:.1f}°</td></tr>"
        )

    house_rows = ""
    for h in range(1, 13):
        hs = d9["houses"][h]
        tenants = ", ".join(hs["tenants"]) or "empty"
        sig = D9_HOUSE_SIGNIFICATIONS.get(h, "")[:100]
        house_rows += (
            f"<tr><td>H{h}</td><td>{_e(sig)}…</td>"
            f"<td>{_e(hs['sign'])} · {_e(hs['lord'])} · {_e(tenants)}</td></tr>"
        )

    tech_rows = '<tr><td class="fam" colspan="3">Examination rules (primary book)</td></tr>'
    for rule in D9_EXAMINATION_RULES[:4]:
        tech_rows += f"<tr><td>Rule</td><td><span class='bdg neu'>Ref</span></td><td>{_e(rule)}</td></tr>"
    tech_rows += '<tr><td class="fam" colspan="3">Live chart confluence</td></tr>'
    for label, direction, note in tech_rows_list:
        btxt, cls = {"positive": ("Supportive", "pos"), "caution": ("Caution", "cau"), "neutral": ("Neutral", "neu")}.get(
            direction, ("Neutral", "neu")
        )
        tech_rows += (
            f"<tr><td>{_e(label)}</td><td><span class='bdg {cls}'>{btxt}</span></td>"
            f"<td>{_e(note)}</td></tr>"
        )

    d1_lagna = meta.get("lagna_sign", "")
    try:
        lagna_deg_str = f"{float(meta.get('lagna_degree') or 0):.1f}°"
    except (TypeError, ValueError):
        lagna_deg_str = ""

    karaka = "Jupiter" if female else "Venus"
    remedy_block = ""
    if pct < 55 or (nav.get("denial_hits") and len(nav["denial_hits"]) >= 1):
        remedy_block = f"""
<div class="card amber">
  <h3>Strengthen marriage &amp; navamsha themes</h3>
  <p>{_e(PLANET_REMEDY.get(karaka, 'Honour relationship values with steady conduct.'))}</p>
  <p>{_e(PLANET_REMEDY.get(d9['lagna_lord'], ''))}</p>
  <p class="fine">D9 responds to fair conduct in partnership, respect for dharma, and patience with timing — not forcing events.</p>
</div>"""

    today = datetime.now().strftime("%d %B %Y")
    vargottama_note = " · vargottama lagna" if d9.get("vargottama_lagna") else ""
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>D9 Navamsha — {_e(client_name)}</title>
<style>{client_css()}{_extra_css()}</style></head><body>
<div class="wrap">
  <p class="vtag">Divisional chart · D9 · Navamsha (marriage &amp; dharma)</p>
  <h1>Navamsha — Marriage, Spouse &amp; Inner Maturity</h1>
  <p class="lead">{_e(D9_INTRO)}</p>

  {narrative_html}

  {conclusion_html}

  {goel_html}

  {rule_html}

  {house_summary_html}

  {house_exam_html}

  {remedy_block}

  <details>
  <summary class="sec-hdr">House snapshot table (reference)</summary>
  <div class="card">
    <table class="tech">
      <tr><th>House</th><th>What it governs in D9</th><th>Your D9 chart</th></tr>
      {house_rows}
    </table>
  </div>
  </details>

  <details>
  <summary class="sec-hdr">Technique confluence table</summary>
  <div class="card">
    <table class="tech">
      <tr><th>Technique</th><th>Verdict</th><th>Reading</th></tr>
      {tech_rows}
    </table>
  </div>
  </details>

  <details>
  <summary class="sec-hdr">Graha snapshot in D9</summary>
  <div class="card">
    <p class="fine">D1 lagna {_e(d1_lagna)} {_e(lagna_deg_str)} → D9 lagna {_e(d9['lagna'])}{vargottama_note}</p>
    <table class="tech">
      <tr><th>Graha</th><th>D9 sign</th><th>D9 H</th><th>D9 dignity</th><th>Pada / flags</th><th>D1 source</th></tr>
      {''.join(plines)}
    </table>
  </div>
  </details>

  <details>
  <summary class="sec-hdr">Book examination rules &amp; confluence lanes</summary>
  <div class="card">
    <h3>Examination rules</h3>
    <ul class="rules">{"".join(f"<li>{_e(r)}</li>" for r in D9_EXAMINATION_RULES)}</ul>
    <h3>Confluence lanes</h3>
    <ul class="rules">{"".join(f"<li><strong>{_e(l)}</strong> — {_e(d)}</li>" for l, d in D9_CONFLUENCE_LANES)}</ul>
  </div>
  </details>

  <p class="fine">Report date: {_e(today)} · Confluence score {pct}% ({conf})</p>
</div>
</body></html>"""

    summary = {
        "varga": "D9",
        "confluence_pct": pct,
        "confidence": conf,
        "lagna": d9["lagna"],
        "lagna_lord": d9["lagna_lord"],
        "vargottama_lagna": d9.get("vargottama_lagna"),
        "venus_d9_house": d9.get("venus_d9_house"),
        "marriage_denial_count": len(nav.get("denial_hits") or []),
        "d9_promise_tone": "caution" if len(nav.get("denial_hits") or []) >= 2 else "neutral",
    }
    return finalize_report_html(doc, client_name), summary


def _generic_varga_narrative(chart: dict, cfg: dict) -> str:
    """Short, prediction-first orienting paragraph for a higher varga."""
    varga = chart.get("varga", "")
    theme = cfg.get("theme", "this area of life")
    ll = chart.get("lagna_lord", "")
    ll_h = chart.get("lagna_lord_varga_house")
    ll_dig = chart.get("lagna_lord_dignity_varga", "")
    vgt = " It repeats its birth-chart sign (vargottama), a strong sign of consistency." if chart.get("vargottama_lagna") else ""
    foundation = ""
    if ll and ll_h:
        if ll_h in (6, 8, 12):
            foundation = (
                f"The ruler of this chart, {ll}, sits in a testing {_ordinal_word(ll_h)} house, "
                f"so the headline matters of {theme} ask for patience and effort before they settle."
            )
        else:
            foundation = (
                f"The ruler of this chart, {ll}, is reasonably placed in the {_ordinal_word(ll_h)} house, "
                f"giving {theme} a workable foundation."
            )
    return (
        f'<h2 class="section-h">What this chart means for you</h2>'
        f'<div class="card"><p>This is your <strong>{_e(chart.get("lagna",""))}</strong>-rising '
        f'{_e(varga)} chart — the lens for {_e(theme)}.{vgt} {_e(foundation)}</p>'
        f'<p class="fine">Read the rule check and house-by-house sections below for the specifics; '
        f'the divisional chart fine-tunes what the birth chart already promises.</p></div>'
    )


def _ordinal_word(n) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


_GOOD_DIG = frozenset({"exalted", "moolatrikona", "own_sign", "friendly_sign", "great_friend_sign"})
_WEAK_DIG = frozenset({"debilitated", "enemy_sign"})


def _dig_tone(dig: str) -> int:
    """+1 strong, -1 weak, 0 neutral — for a dignity string."""
    if dig in _GOOD_DIG:
        return 1
    if dig in _WEAK_DIG:
        return -1
    return 0


def _link_pos(name: str, sign: str, house, dig: str) -> str:
    """One readable 'X in <sign> (<dignity>), Hn' phrase."""
    parts = [f"<strong>{_e(name)}</strong>"]
    if sign:
        parts.append(f"in {_e(sign)}")
    if dig and dig != "unknown":
        parts.append(f"({_e(_dignity_plain(dig))})")
    if house:
        parts.append(f"· {_ordinal_word(house)} house")
    return " ".join(parts)


def _varga_linking_html(pc: dict, chart: dict, cfg: dict) -> str:
    """Cross-varga *linking* card — trace the chart's ruler and karaka across
    D1 (root) and D9 (strength/maturity) charts.

    Implements the classical 'linking of divisional charts' method (take the
    significator of one varga into another) applied to a single nativity: a
    varga promise delivers only when its ruler is also sound in the foundation
    (D1) and strength (D9) charts.
    """
    varga = chart.get("varga", "")
    theme = cfg.get("theme", "this area of life")
    ll = chart.get("lagna_lord", "")
    if not ll:
        return ""

    # D9 positions (strength chart) for the same grahas.
    try:
        d9 = build_varga_chart_from_pc(pc, "D9")
    except Exception:  # noqa: BLE001
        d9 = {"planets": {}}
    d9_bodies = d9.get("planets", {})

    rows = []
    notes_tone = 0

    def _add_link(graha: str, role: str):
        nonlocal notes_tone
        if not graha:
            return
        p1 = pc.get("planets", {}).get(graha, {})
        d1_sign = p1.get("sign", "")
        d1_house = p1.get("house")
        try:
            d1_dig = get_dignity(graha, d1_sign) if d1_sign else "unknown"
        except Exception:  # noqa: BLE001
            d1_dig = "unknown"
        vb = chart.get("planets", {}).get(graha, {})
        v_sign = vb.get("sign", "")
        v_house = vb.get("house")
        v_dig = vb.get("varga_dignity", "unknown")
        d9b = d9_bodies.get(graha, {})
        d9_sign = d9b.get("sign", "")
        d9_house = d9b.get("house")
        try:
            d9_dig = get_dignity(graha, d9_sign) if d9_sign else "unknown"
        except Exception:  # noqa: BLE001
            d9_dig = "unknown"
        tone = _dig_tone(d1_dig) + _dig_tone(v_dig) + _dig_tone(d9_dig)
        notes_tone += tone
        vgt = " · vargottama" if (d1_sign and d1_sign == v_sign) else ""
        rows.append(
            f"<tr><td>{_e(role)}<br><span class='fine'>{_e(graha)}</span></td>"
            f"<td>{_link_pos(graha, d1_sign, d1_house, d1_dig)}</td>"
            f"<td>{_link_pos(graha, v_sign, v_house, v_dig)}{vgt}</td>"
            f"<td>{_link_pos(graha, d9_sign, d9_house, d9_dig)}</td></tr>"
        )

    _add_link(ll, f"{varga} ruler")
    karaka = cfg.get("karaka", "")
    if karaka and karaka != ll:
        _add_link(karaka, f"{theme.split(',')[0].strip().capitalize()} karaka")

    if not rows:
        return ""

    if notes_tone >= 2:
        verdict = (
            f"The ruler of this chart carries weight in the birth chart and navamsha too, "
            f"so the {varga} promise for <strong>{_e(theme)}</strong> is well-rooted and tends to deliver."
        )
    elif notes_tone <= -2:
        verdict = (
            f"The ruler of this chart is under strain in the foundation (D1) and strength (D9) charts, "
            f"so the {varga} reading for <strong>{_e(theme)}</strong> needs effort and the remedies below before it settles."
        )
    else:
        verdict = (
            f"The ruler of this chart is mixed across the birth chart and navamsha — "
            f"the {varga} promise for <strong>{_e(theme)}</strong> is workable but uneven; lean on its stronger periods."
        )

    return (
        '<h2 class="section-h">Linking across charts — does the promise carry through?</h2>'
        '<div class="card">'
        f'<p>{verdict}</p>'
        '<table class="tech">'
        '<tr><th>Significator</th><th>Birth chart (D1)</th>'
        f'<th>This chart ({_e(varga)})</th><th>Strength chart (D9)</th></tr>'
        f'{"".join(rows)}'
        '</table>'
        '<p class="fine">Linking method (Comprehensive Prediction by Divisional Charts): a varga '
        'is read together with the charts it depends on — its ruler and karaka are traced into the '
        'birth chart and navamsha. Strong in all three = a promise that delivers; weak there dilutes it.</p>'
        '</div>'
    )


def generate_generic_varga_html(
    pc: dict,
    varga: str,
    client_name: str = "Client",
) -> tuple[str, dict]:
    """Data-driven report for higher vargas (D10-D60) from the book corpus."""
    varga = varga.upper()
    cfg = HIGHER_VARGA_CORPUS[varga]
    meta = pc.get("meta", {})
    pillar = Pillar(pc)
    chart = build_varga_chart_from_pc(pc, varga)
    theme = cfg["theme"]
    house_sigs = cfg["house_sigs"]

    # Narrative — D10 reuses the rich dashamsha analysis when available.
    narrative_html = _generic_varga_narrative(chart, cfg)
    if varga == "D10":
        try:
            from goel_dashamsha_analysis import analyze_dashamsha_chart
            from goel_dashamsha_prose import render_dashamsha_section
            d10a = analyze_dashamsha_chart(pc)
            if d10a and not d10a.get("error"):
                narrative_html += (
                    '<h2 class="section-h">Your career chart in plain language</h2>'
                    f'<div class="card">{render_dashamsha_section(d10a)}</div>'
                )
        except Exception:  # noqa: BLE001 - fall back to generic narrative
            pass

    linking_html = _varga_linking_html(pc, chart, cfg)

    goel_result = inspect_varga_chart(varga, chart, pc, pillar.lagna_lord)
    goel_html = goel_inspection_html(goel_result)
    goel_html += rule_findings_html(
        inspect_varga_generic(varga, chart, pc),
        title=f"Every {cfg['tag']} rule, checked against your chart",
    )
    special = SPECIAL_INSPECTORS.get(varga)
    if special:
        goel_html += rule_findings_html(
            special(chart, pc),
            title=f"Special {cfg['tag']} checks — the classical {varga} technique",
            intro=(
                f"Beyond the shared rules, {varga} has its own signature method the "
                f"author leans on. Here it is, run against your chart — matches the text "
                f"emphasises are marked in colour."
            ),
        )

    house_exam_html, house_readings = _varga_house_examination_html(
        chart, house_sigs, varga,
        f"House examination — {theme} — what it means for you",
    )
    house_summary_html = _varga_examination_summary_html(house_readings, varga, theme)

    pos = sum(1 for r in house_readings if r["verdict"] == "positive")
    cau = sum(1 for r in house_readings if r["verdict"] == "caution")
    pct = int(round(pos / 12 * 100))
    conf = "HIGH" if (pos >= 5 and pos > cau) else ("MODERATE" if pos >= 3 else "LOW")

    plines = []
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        b = chart["planets"].get(name)
        if not b:
            continue
        flag = "vargottama" if b.get("vargottama") else "—"
        plines.append(
            f"<tr><td>{_e(name)}</td><td>{_e(b['sign'])}</td><td>{b['house']}</td>"
            f"<td>{_e(_dignity_plain(b.get('varga_dignity', 'unknown')))}</td>"
            f"<td>{_e(flag)}</td><td>{_e(b['d1_sign'])} {b['d1_degree']:.1f}°</td></tr>"
        )

    house_rows = ""
    for h in range(1, 13):
        hs = chart["houses"][h]
        tenants = ", ".join(hs["tenants"]) or "empty"
        sig = house_sigs.get(h, "")[:100]
        house_rows += (
            f"<tr><td>H{h}</td><td>{_e(sig)}</td>"
            f"<td>{_e(hs['sign'])} · {_e(hs['lord'])} · {_e(tenants)}</td></tr>"
        )

    remedy_block = varga_remedy_deity_html(chart, varga, cfg.get("karaka", ""), theme)

    today = datetime.now().strftime("%d %B %Y")
    d1_lagna = meta.get("lagna_sign", "")
    vargottama_note = " · vargottama lagna" if chart.get("vargottama_lagna") else ""
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{_e(varga)} {_e(cfg['tag'])} — {_e(client_name)}</title>
<style>{client_css()}{_extra_css()}</style></head><body>
<div class="wrap">
  <p class="vtag">Divisional chart · {_e(varga)} · {_e(cfg['tag'])} ({_e(cfg['subtitle'])})</p>
  <h1>{_e(cfg['title'])} — {_e(cfg['subtitle'])}</h1>
  <p class="lead">{_e(cfg['intro'])}</p>

  {narrative_html}

  {linking_html}

  {goel_html}

  {house_summary_html}

  {house_exam_html}

  {remedy_block}

  <details>
  <summary class="sec-hdr">House snapshot table (reference)</summary>
  <div class="card">
    <table class="tech">
      <tr><th>House</th><th>What it governs in {_e(varga)}</th><th>Your {_e(varga)} chart</th></tr>
      {house_rows}
    </table>
  </div>
  </details>

  <details>
  <summary class="sec-hdr">Graha snapshot in {_e(varga)}</summary>
  <div class="card">
    <p class="fine">D1 lagna {_e(d1_lagna)} → {_e(varga)} lagna {_e(chart['lagna'])}{vargottama_note}</p>
    <table class="tech">
      <tr><th>Graha</th><th>{_e(varga)} sign</th><th>{_e(varga)} H</th><th>Dignity</th><th>Flag</th><th>D1 source</th></tr>
      {''.join(plines)}
    </table>
  </div>
  </details>

  <details>
  <summary class="sec-hdr">Book examination rules</summary>
  <div class="card">
    <ul class="rules">{"".join(f"<li>{_e(r)}</li>" for r in cfg.get('rules', []))}</ul>
  </div>
  </details>

  <p class="fine">Report date: {_e(today)} · Confluence score {pct}% ({conf})</p>
</div>
</body></html>"""

    summary = {
        "varga": varga,
        "confluence_pct": pct,
        "confidence": conf,
        "lagna": chart["lagna"],
        "lagna_lord": chart["lagna_lord"],
        "vargottama_lagna": chart.get("vargottama_lagna"),
    }
    return finalize_report_html(doc, client_name), summary


def generate_divisional_confluence_html(
    pc: dict,
    varga: str,
    client_name: str = "Client",
) -> tuple[str, dict]:
    varga = varga.upper()
    if varga == "D1":
        return generate_d1_confluence_html(pc, client_name)
    if varga == "D2":
        return generate_d2_confluence_html(pc, client_name)
    if varga == "D3":
        return generate_d3_confluence_html(pc, client_name)
    if varga == "D4":
        return generate_d4_confluence_html(pc, client_name)
    if varga == "D7":
        return generate_d7_confluence_html(pc, client_name)
    if varga == "D9":
        return generate_d9_confluence_html(pc, client_name)
    if varga in HIGHER_VARGA_CORPUS:
        return generate_generic_varga_html(pc, varga, client_name)
    raise ValueError(
        f"Unsupported varga {varga}; implemented: D1-D4, D7, D9, and "
        f"{', '.join(HIGHER_VARGA_CORPUS.keys())}"
    )


def write_divisional_confluence_report(
    pc: dict,
    varga: str,
    out_dir: Path,
    client_name: str = "Client",
    slug: str = "",
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    html_doc, _ = generate_divisional_confluence_html(pc, varga, client_name)
    meta = VARGA_META.get(varga.upper(), {"filename_tag": varga})
    slug = slug or client_name.strip().replace(" ", "_")
    path = out_dir / f"{varga}_{meta.get('filename_tag', varga)}_{slug}.html"
    path.write_text(html_doc, encoding="utf-8")
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Divisional chart confluence report")
    ap.add_argument("--varga", default="D1",
                    help="D1, D2, D3, D4, D7, D9, D10, D12, D16, D20, D24, D27, D30, D40, D45, D60 (or 'all')")
    ap.add_argument("--name", default="Sample")
    ap.add_argument("--dob", default="1990-01-15")
    ap.add_argument("--time", default="12:00")
    ap.add_argument("--place", default="New Delhi, India")
    ap.add_argument("--lat", type=float, default=28.6139)
    ap.add_argument("--lon", type=float, default=77.2090)
    ap.add_argument("--tz", type=float, default=5.5)
    ap.add_argument("-o", "--out", default="")
    args = ap.parse_args()

    from astro_chart_bridge import compute_chart

    pc = compute_chart(
        client_name=args.name, dob=args.dob, birth_time=args.time,
        place=args.place, latitude=args.lat, longitude=args.lon, timezone=args.tz,
    )
    if not pc:
        raise SystemExit("Could not compute chart.")

    out_dir = Path(args.out) if args.out else (BASE_DIR / "reports" / args.name)
    if args.varga.lower() == "all":
        vargas = ["D1", "D2", "D3", "D4", "D7", "D9", *HIGHER_VARGA_CORPUS.keys()]
        for v in vargas:
            try:
                p = write_divisional_confluence_report(pc, v, out_dir, args.name)
                print(f"Wrote {p}")
            except Exception as exc:  # noqa: BLE001
                print(f"FAILED {v}: {exc}")
    else:
        path = write_divisional_confluence_report(pc, args.varga, out_dir, args.name)
        print(f"Wrote {path}")
