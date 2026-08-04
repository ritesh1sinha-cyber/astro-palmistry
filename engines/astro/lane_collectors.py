#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect LaneClaim objects from today's book-backed lane pipelines."""
from __future__ import annotations

import re
from typing import Callable

from astro_precompute import precompute
from lane_claim import LaneClaim, map_domain, tone_to_direction
from report_language import client_prose


def _strip_html(raw: str) -> str:
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw or "", flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&(?:nbsp|#160);", " ", s, flags=re.I)
    s = re.sub(r"&#x27;|&apos;", "'", s, flags=re.I)
    s = re.sub(r"&quot;", '"', s, flags=re.I)
    s = re.sub(r"&lt;|&gt;|&amp;", " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


def _claim(lane: str, sid: str, title: str, prediction: str, tone: str, timing: str = "") -> LaneClaim | None:
    text = client_prose(_strip_html(prediction or ""))
    if len(text) < 40:
        return None
    return LaneClaim(
        lane=lane,
        section_id=sid,
        domain=map_domain(sid, title),
        direction=tone_to_direction(tone),
        text=text[:600],
        timing=timing or "",
        tone=tone,
    )


def _split_parents(c: LaneClaim) -> list[LaneClaim]:
    parts = re.split(r"(?<=[.!?])\s+", c.text)
    father, mother, other = [], [], []
    for p in parts:
        pl = p.lower()
        if "mother" in pl or "moon in" in pl or ("home" in pl and "father" not in pl):
            mother.append(p)
        elif "father" in pl or "sun in" in pl or "9th" in pl or "guru line" in pl:
            father.append(p)
        else:
            other.append(p)
    out: list[LaneClaim] = []
    if father:
        out.append(LaneClaim(c.lane, c.section_id, "father", c.direction, " ".join(father)[:600], c.timing, c.tone))
    if mother:
        out.append(LaneClaim(c.lane, c.section_id, "mother", c.direction, " ".join(mother)[:600], c.timing, c.tone))
    if not out and other:
        out.append(LaneClaim(c.lane, c.section_id, "family", c.direction, " ".join(other)[:600], c.timing, c.tone))
    return out or [c]


def _refine_domain(c: LaneClaim) -> LaneClaim:
    tl = c.text.lower()
    sid = c.section_id.lower()
    if sid in ("parents",):
        return c
    if sid in ("siblings", "ch03"):
        return LaneClaim(c.lane, c.section_id, "family", c.direction, c.text, c.timing, c.tone)
    if sid in ("dasha", "pratyantar", "ch15", "ch14", "remedies", "spiritual", "birth_star"):
        return c
    if "brother" in tl or "sister" in tl or "sibling" in tl:
        return LaneClaim(c.lane, c.section_id, "family", c.direction, c.text, c.timing, c.tone)
    if c.lane == "Bhardwaj":
        if "father" in tl or "9th house" in tl or "paternal" in tl:
            return LaneClaim(c.lane, c.section_id, "father", c.direction, c.text, c.timing, c.tone)
        if ("mother" in tl or "4th house" in tl) and "landlord" not in tl and "property" not in tl:
            return LaneClaim(c.lane, c.section_id, "mother", c.direction, c.text, c.timing, c.tone)
    return c


def _split_mother_from_home(c: LaneClaim) -> list[LaneClaim]:
    if c.section_id.lower() not in ("ch04", "property", "gems_kl_4th"):
        return [c]
    parts = re.split(r"(?<=[.!?])\s+", c.text)
    mother, home = [], []
    for p in parts:
        pl = p.lower()
        if "mother" in pl or "moon in" in pl or "moon occupies" in pl:
            mother.append(p)
        else:
            home.append(p)
    out: list[LaneClaim] = []
    if mother:
        out.append(LaneClaim(c.lane, c.section_id, "mother", c.direction, " ".join(mother)[:600], c.timing, c.tone))
    if home:
        out.append(LaneClaim(c.lane, c.section_id, "property", c.direction, " ".join(home)[:600], c.timing, c.tone))
    return out or [c]


def _normalize_claims(claims: list[LaneClaim]) -> list[LaneClaim]:
    out: list[LaneClaim] = []
    for c in claims:
        if c.section_id.lower() == "parents":
            out.extend(_split_parents(c))
        elif c.section_id.lower() in ("ch04", "property", "gems_kl_4th"):
            out.extend(_split_mother_from_home(c))
        else:
            out.append(_refine_domain(c))
    return out


def collect_bnn(extracted: str, name: str, dob: str, pc: dict | None = None) -> list[LaneClaim]:
    from bnn_analysis import analyze_all_chapters
    from bnn_chart import load_bnn_chart

    pc = pc or precompute(extracted, name, dob)
    ch, bt = load_bnn_chart(extracted, name, dob, pc)
    out: list[LaneClaim] = []
    for s in analyze_all_chapters(ch, bt):
        text = s.prediction or getattr(s, "html_body", "")
        c = _claim("BNN", s.id, s.title, text, s.tone)
        if c:
            out.append(c)
    return out


def collect_kp(extracted: str, name: str, dob: str, pc: dict | None = None) -> list[LaneClaim]:
    from kp_analysis import analyze_all_chapters
    from kp_chart import load_kp_chart

    pc = pc or precompute(extracted, name, dob)
    kp = load_kp_chart(extracted, name, dob, pc)
    out: list[LaneClaim] = []
    for s in analyze_all_chapters(kp):
        text = s.prediction or getattr(s, "html_body", "")
        c = _claim("KP", s.id, s.title, text, s.tone)
        if c:
            out.append(c)
    return out


def collect_mehta(extracted: str, name: str, dob: str, pc: dict | None = None) -> list[LaneClaim]:
    import json
    from pathlib import Path

    from mehta_analysis import analyze_all_sections
    from mehta_chart import MehtaChart

    book_path = Path(__file__).resolve().parent / "mehta_book_data.json"
    book = json.loads(book_path.read_text(encoding="utf-8"))
    pc = pc or precompute(extracted, name, dob)
    chart = MehtaChart(pc, book)
    out: list[LaneClaim] = []
    for s in analyze_all_sections(chart):
        c = _claim("Mehta", s.id, s.title, s.prediction, s.tone)
        if c:
            out.append(c)
    return out


def collect_jaimini(extracted: str, name: str, dob: str, pc: dict | None = None) -> list[LaneClaim]:
    from jaimini_books_analysis import analyze_all_sections
    from jaimini_books_chart import JaiminiBooksChart
    from jaimini_book_data import load_book

    pc = pc or precompute(extracted, name, dob)
    chart = JaiminiBooksChart.from_precompute(pc)
    book = load_book()
    out: list[LaneClaim] = []
    for s in analyze_all_sections(chart, book):
        c = _claim("Jaimini", s.section_id, s.title, s.prediction, s.tone)
        if c:
            out.append(c)
    return out


def collect_bhardwaj(extracted: str, name: str, dob: str, pc: dict | None = None) -> list[LaneClaim]:
    from bhardwaj_semantic import BhardwajSemanticEngine, build_chart_signals, load_corpus
    from vedic_bhardwaj_report import BhardwajChart, _load_book

    pc = pc or precompute(extracted, name, dob)
    book = _load_book()
    chart = BhardwajChart(pc, book)
    engine = BhardwajSemanticEngine(book)
    signals = build_chart_signals(chart, pc)
    clusters = engine.cluster(signals)
    out: list[LaneClaim] = []
    for cl in clusters:
        if cl.score < 1:
            continue
        text = cl.affirmation or (cl.book_refs[0] if cl.book_refs else "")
        if len(text) < 40:
            continue
        out.append(LaneClaim(
            lane="Bhardwaj",
            section_id=cl.domain,
            domain=cl.domain,
            direction=cl.direction,
            text=text[:600],
            timing=cl.timing,
            tone="good" if cl.direction == "positive" else ("amber" if cl.direction == "caution" else "neutral"),
        ))
    return out


def collect_disease(pc: dict) -> list[LaneClaim]:
    from confluence_human import health_claim_from_goel

    out: list[LaneClaim] = []
    for i, line in enumerate(health_claim_from_goel(pc)):
        if len(line) < 35:
            continue
        caution = any(w in line.lower() for w in ("watch", "chronic", "stress", "illness", "flare"))
        out.append(LaneClaim(
            lane="Goel",
            section_id=f"disease_{i}",
            domain="health",
            direction="caution" if caution else "neutral",
            text=line[:600],
            tone="amber" if caution else "neutral",
        ))
    return out


def collect_kvs(pc: dict) -> list[LaneClaim]:
    try:
        from nakshatra_human import human_birth_star
        pred, _ = human_birth_star(pc)
        if not pred:
            return []
        return [
            LaneClaim("KVS", "birth_star", "personality", "neutral", pred[:600], "birth star"),
        ]
    except Exception:
        return []


def collect_longevity(pc: dict) -> list[LaneClaim]:
    from confluence_longevity_lane import collect_longevity_claims
    return collect_longevity_claims(pc)


def collect_ashtakavarga(extracted: str, name: str, dob: str, pc: dict | None = None) -> list[LaneClaim]:
    from vedic_ashtakavarga_report import AV, build_confluence_claims

    pc = pc or precompute(extracted, name, dob)
    return build_confluence_claims(AV(pc))


LANE_COLLECTORS: list[tuple[str, Callable]] = [
    ("BNN", collect_bnn),
    ("KP", collect_kp),
    ("Mehta", collect_mehta),
    ("Jaimini", collect_jaimini),
    ("Bhardwaj", collect_bhardwaj),
]


def _isolated(meta: dict, lane_name: str, fn: Callable, *args) -> list[LaneClaim]:
    """Run one collector so that its failure costs only its own claims.

    The chart-driven lanes (KVS, Goel, Longevity, Ashtakavarga) used to run
    outside the try/except, so a single raise there lost every other lane's
    claims as well. Everything goes through the same gate now.
    """
    try:
        batch = fn(*args)
    except Exception as exc:
        meta[lane_name] = 0
        meta[f"{lane_name}_error"] = f"{type(exc).__name__}: {exc}"[:120]
        return []
    meta[lane_name] = len(batch)
    return batch


def collect_all_lanes(extracted: str, name: str, dob: str, pc: dict | None = None) -> tuple[list[LaneClaim], dict]:
    pc = pc or precompute(extracted, name, dob)
    claims: list[LaneClaim] = []
    meta: dict[str, int] = {}
    for lane_name, fn in LANE_COLLECTORS:
        claims.extend(_isolated(meta, lane_name, fn, extracted, name, dob, pc))
    claims.extend(_isolated(meta, "KVS", collect_kvs, pc))
    claims.extend(_isolated(meta, "Goel", collect_disease, pc))
    claims.extend(_isolated(meta, "Longevity", collect_longevity, pc))
    claims.extend(_isolated(meta, "Ashtakavarga", collect_ashtakavarga,
                            extracted, name, dob, pc))
    return _normalize_claims(claims), meta
