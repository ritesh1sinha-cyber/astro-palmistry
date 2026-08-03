#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OCR-backed longevity/maraka/MB context for confluence + user reports."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from types import SimpleNamespace
from typing import Any

from longevity_analysis import (
    check_mb,
    classify_ad_book,
    functional_killer,
    primary_marakas,
    scan_mb_all,
)
from longevity_book_data import load_longevity_book

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
    "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}


def _house_of(sign: str, lagna: str) -> int:
    return (SIGNS.index(sign) - SIGNS.index(lagna)) % 12 + 1


def _parse_date_short(s: str) -> str:
    if not s:
        return ""
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date().strftime("%b %Y")
    except ValueError:
        return s[:10]


def _ad_window(ad: dict) -> str:
    return f"{_parse_date_short(ad.get('start', ''))} - {_parse_date_short(ad.get('end', ''))}"


RISK_WATCH = frozenset({"Moderate", "High", "Highest"})
RISK_ALERT = frozenset({"High", "Highest"})


def classify_ad_risk(pc: dict, ad_lord: str, md_lord: str | None = None) -> tuple[str, str, str, str]:
    """Return (class_label, mb_status, risk_tier, theme) using the same book engine as vedic_longevity_report."""
    book = load_longevity_book()
    lg = _mini_longevity(pc, book)
    md = md_lord or pc.get("vimshottari", {}).get("current_md", {}).get("md_lord", "")
    return classify_ad_book(lg, ad_lord, md, book, lg.mb_rows)


def classify_future_ads(pc: dict) -> list[dict]:
    """Risk assessment for current + future antardashas in the active mahadasha."""
    md_lord = pc.get("vimshottari", {}).get("current_md", {}).get("md_lord", "")
    out: list[dict] = []
    for ad in pc.get("vimshottari", {}).get("current_md_antardashas", []):
        if ad.get("status") not in ("current", "future"):
            continue
        ad_lord = ad["ad_lord"]
        cls, mb_st, risk, theme = classify_ad_risk(pc, ad_lord, md_lord)
        out.append({
            "window": _ad_window(ad),
            "ad_lord": ad_lord,
            "status": ad.get("status", ""),
            "class": cls,
            "mb": mb_st,
            "risk": risk,
            "theme": theme,
        })
    return out


def health_light_for_risk(risk: str) -> str:
    return {"Low": "🟢", "Moderate": "🟡", "High": "🔴", "Highest": "🔴"}.get(risk, "🟡")


@dataclass
class LongevityContext:
    maraka_1: str
    maraka_2: str
    unqualified: list[str]
    critical_mb: list[str]
    near_mb: list[str]
    mb_detail: list[dict]
    health_watch_windows: list[str]
    high_risk_ads: list[dict]
    functional_note: str
    plain_lines: list[str] = field(default_factory=list)
    ad_assessments: list[dict] = field(default_factory=list)
    max_future_risk: str = "Low"


def _mini_longevity(pc: dict, book: dict) -> Any:
    lagna = pc["meta"]["lagna_sign"]
    lagna_idx = SIGNS.index(lagna)
    planets = {}
    for nm, v in pc["planets"].items():
        planets[nm] = {
            "sign": v["sign"],
            "degree": float(v.get("degree_in_sign", v.get("degree", 0))),
            "functional": v.get("functional_status", "neutral"),
            "dignity": v.get("dignity", "neutral_sign"),
            "house": _house_of(v["sign"], lagna),
        }
    house_sign = {h: SIGNS[(lagna_idx + h - 1) % 12] for h in range(1, 13)}
    lord_of = {h: SIGN_LORD[house_sign[h]] for h in range(1, 13)}
    m1, m2 = primary_marakas(book, lagna)
    mb_rows = scan_mb_all(
        book, planets, lagna, float(pc["meta"].get("lagna_degree", 0))
    )
    return SimpleNamespace(
        lagna=lagna,
        lagna_lord=pc["meta"]["lagna_lord"],
        planets=planets,
        lord_of=lord_of,
        maraka_lords={m1, m2},
        mb_rows=mb_rows,
        book=book,
    )


def build_longevity_context(pc: dict) -> LongevityContext:
    book = load_longevity_book()
    lg = _mini_longevity(pc, book)
    m1, m2 = primary_marakas(book, lg.lagna)
    mb_rows = lg.mb_rows
    critical = [r["planet"] for r in mb_rows if r.get("status") == "IN MB" and r["planet"] != "Lagna"]
    near = [r["planet"] for r in mb_rows if r.get("status") == "Near MB"]
    md_lord = pc.get("vimshottari", {}).get("current_md", {}).get("md_lord", "")

    ad_assessments = classify_future_ads(pc)
    risk_rank = {"Low": 0, "Moderate": 1, "High": 2, "Highest": 3}
    max_future_risk = "Low"
    if ad_assessments:
        max_future_risk = max(ad_assessments, key=lambda a: risk_rank.get(a["risk"], 0))["risk"]

    health_windows: list[str] = []
    high_risk: list[dict] = []
    for ad in ad_assessments:
        if ad["risk"] in RISK_WATCH:
            w = ad["window"]
            if w not in health_windows:
                health_windows.append(w)
        if ad["risk"] in RISK_ALERT:
            high_risk.append({
                "window": ad["window"],
                "ad_lord": ad["ad_lord"],
                "risk": ad["risk"],
                "class": ad["class"],
                "mb": ad["mb"],
                "theme": ad["theme"],
            })

    plain: list[str] = []
    if critical:
        names = " and ".join(critical)
        plain.append(
            f"Your chart carries a sensitive-degree signature on {names} - "
            "periods when those themes run need extra health awareness and steady routines, not fear."
        )
    elif not health_windows and max_future_risk == "Low":
        plain.append(
            "Book OCR longevity scan finds no strict Mrityu Bhaga degree hits at birth, and upcoming "
            "sub-chapters within the current mahadasha rate low on the maraka risk scale - "
            "steady routines and annual check-ups are sufficient, not emergency mode."
        )
    else:
        plain.append(
            f"The strongest life-risk lords for your rising sign are the rulers of the second and seventh "
            f"life areas ({m1} and {m2} in the technical map) - their elevated sub-chapters deserve "
            "preventive check-ups and calm pacing."
        )
    if health_windows:
        win_txt = health_windows[0] if len(health_windows) == 1 else f"{health_windows[0]} onward"
        moderate = [a for a in ad_assessments if a["risk"] == "Moderate"]
        if moderate:
            lords = ", ".join(dict.fromkeys(a["ad_lord"] for a in moderate))
            plain.append(
                f"Moderate maraka-awareness window ({win_txt}) when {lords} leads the sub-chapter - "
                "keep health routines firm; this is prudence, not a crisis forecast."
            )
    fk = functional_killer(book, lg.lagna)
    if fk and (critical or max_future_risk in RISK_ALERT):
        plain.append(f"Classical note for your rising sign: {fk}")

    mb_detail = []
    for r in mb_rows:
        if r.get("status") in ("IN MB", "Near MB"):
            mb_detail.append({
                "planet": r["planet"],
                "sign": r.get("sign", ""),
                "status": r["status"],
                "mb": r.get("mb"),
                "diff_minutes": r.get("diff_minutes"),
            })

    return LongevityContext(
        maraka_1=m1,
        maraka_2=m2,
        unqualified=list(book.get("unqualified_marakas", [])),
        critical_mb=critical,
        near_mb=near,
        mb_detail=mb_detail,
        health_watch_windows=health_windows,
        high_risk_ads=high_risk,
        functional_note=fk or "",
        plain_lines=plain,
        ad_assessments=ad_assessments,
        max_future_risk=max_future_risk,
    )


def longevity_signals(pc: dict) -> list[dict]:
    """Signals for vedic_confluence_report.Signal harvest."""
    ctx = build_longevity_context(pc)
    out: list[dict] = []
    base_dir = "caution" if ctx.critical_mb or ctx.max_future_risk in RISK_ALERT else "neutral"
    timing = ctx.health_watch_windows[0] if ctx.health_watch_windows else ""
    for line in ctx.plain_lines[:3]:
        out.append({
            "system": "Longevity",
            "domain": "health",
            "direction": base_dir if ctx.critical_mb else "neutral",
            "timing": timing,
            "text": line,
        })
    for ad in ctx.high_risk_ads[:4]:
        out.append({
            "system": "Longevity",
            "domain": "health",
            "direction": "caution",
            "timing": ad["window"],
            "text": (
                f"Elevated health-awareness window ({ad['window']}): "
                f"{ad['theme']} Educational only - not a medical diagnosis."
            ),
        })
    if ctx.critical_mb:
        crit = ", ".join(ctx.critical_mb)
        out.append({
            "system": "Longevity",
            "domain": "health",
            "direction": "caution",
            "timing": "natal baseline",
            "text": (
                f"Mrityu Bhaga (book OCR) flags {crit} at sensitive degrees - "
                "build sleep, labs, and stress caps before those planets lead sub-chapters."
            ),
        })
    elif ctx.max_future_risk == "Low" and not ctx.critical_mb:
        out.append({
            "system": "Longevity",
            "domain": "health",
            "direction": "positive",
            "timing": timing or "current mahadasha",
            "text": (
                "Longevity lane (book OCR): no strict MB degree hits and upcoming sub-chapters rate low risk - "
                "maintenance habits are enough; no elevated crisis window is flagged."
            ),
        })
    return out


def collect_longevity_claims(pc: dict) -> list:
    from lane_claim import LaneClaim

    ctx = build_longevity_context(pc)
    claims: list[LaneClaim] = []
    for i, line in enumerate(ctx.plain_lines):
        claims.append(LaneClaim(
            lane="Longevity",
            section_id=f"mb_{i}",
            domain="health",
            direction="caution" if ctx.critical_mb else "neutral",
            text=line,
            timing=ctx.health_watch_windows[0] if ctx.health_watch_windows else "",
            tone="amber" if ctx.critical_mb else "neutral",
        ))
    for ad in ctx.high_risk_ads[:3]:
        claims.append(LaneClaim(
            lane="Longevity",
            section_id="maraka_ad",
            domain="health",
            direction="caution",
            text=ad["theme"],
            timing=ad["window"],
            tone="amber",
        ))
    return claims
