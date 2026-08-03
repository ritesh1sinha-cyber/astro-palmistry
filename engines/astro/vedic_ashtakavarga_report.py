#!/usr/bin/env python3
"""
vedic_ashtakavarga_report.py — Deterministic Ashtakavarga transit report (NO LLM).

Replaces the Cursor Ashtakavarga lane. Computes Bhinnāṣṭakavarga (BAV) and
Sarvāṣṭakavarga (SAV) bindus from the natal chart using the classical Parāśarī
benefic-point tables (grand total 337, verified), then builds a prediction-first
transit forecast.  Jupiter and Saturn sign-transit timing is computed from the
Swiss Ephemeris (sidereal Lahiri, Moshier) so windows are real, not guessed.

Output matches the gold reference
``reports/Ritz_reprot/Vedic_Ashtakavarga_Ritz_20260408.html``.

Fully offline and reproducible — no model, no network.
"""
from __future__ import annotations

import argparse
import html
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from astro_precompute import resolve_precompute
from chart_resolve import add_chart_source_args, chart_kwargs_from_args
from ashtakavarga_analysis import (
    assess_md_ad_criticality,
    bav_transit_meaning,
    donor_analysis,
    donor_table_html,
    house_lords,
    kakshaya_sector,
    methodology_html,
    parse_extract_ashtakavarga,
    sade_sati_status,
    sav_house_meaning,
    validate_against_extract,
)

try:
    import swisseph as swe
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    _SWE = True
except Exception:
    _SWE = False

BASE_DIR = Path(__file__).resolve().parent
GOLD = BASE_DIR / "reports" / "Vedic_Ashtakavarga_Ritz_20260408.html"

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}
CONTRIBUTORS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Lagna"]
SEVEN = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

# Classical Parāśarī Ashtakavarga benefic-point tables.
# TABLE[planet][contributor] = houses (counted from the contributor's sign,
# 1 = same sign) that receive one bindu. Grand SAV total = 337 (verified).
TABLE = {
    "Sun": {
        "Sun": [1, 2, 4, 7, 8, 9, 10, 11], "Moon": [3, 6, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11], "Mercury": [3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [5, 6, 9, 11], "Venus": [6, 7, 12],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11], "Lagna": [3, 4, 6, 10, 11, 12]},
    "Moon": {
        "Sun": [3, 6, 7, 8, 10, 11], "Moon": [1, 3, 6, 7, 10, 11],
        "Mars": [2, 3, 5, 6, 9, 10, 11], "Mercury": [1, 3, 4, 5, 7, 8, 10, 11],
        "Jupiter": [1, 2, 4, 7, 8, 10, 11], "Venus": [3, 4, 5, 7, 9, 10, 11],
        "Saturn": [3, 5, 6, 11], "Lagna": [3, 6, 10, 11]},
    "Mars": {
        "Sun": [3, 5, 6, 10, 11], "Moon": [3, 6, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11], "Mercury": [3, 5, 6, 11],
        "Jupiter": [6, 10, 11, 12], "Venus": [6, 8, 11, 12],
        "Saturn": [1, 4, 7, 8, 9, 10, 11], "Lagna": [1, 3, 6, 10, 11]},
    "Mercury": {
        "Sun": [5, 6, 9, 11, 12], "Moon": [2, 4, 6, 8, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11], "Mercury": [1, 3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [6, 8, 11, 12], "Venus": [1, 2, 3, 4, 5, 8, 9, 11],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11], "Lagna": [1, 2, 4, 6, 8, 10, 11]},
    "Jupiter": {
        "Sun": [1, 2, 3, 4, 7, 8, 9, 10, 11], "Moon": [2, 5, 7, 9, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11], "Mercury": [1, 2, 4, 5, 6, 9, 10, 11],
        "Jupiter": [1, 2, 3, 4, 7, 8, 10, 11], "Venus": [2, 5, 6, 9, 10, 11],
        "Saturn": [3, 5, 6, 12], "Lagna": [1, 2, 4, 5, 6, 7, 9, 10, 11]},
    "Venus": {
        "Sun": [8, 11, 12], "Moon": [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "Mars": [3, 5, 6, 9, 11, 12], "Mercury": [3, 5, 6, 9, 11],
        "Jupiter": [5, 8, 9, 10, 11], "Venus": [1, 2, 3, 4, 5, 8, 9, 10, 11],
        "Saturn": [3, 4, 5, 8, 9, 10, 11], "Lagna": [1, 2, 3, 4, 5, 8, 9, 11]},
    "Saturn": {
        "Sun": [1, 2, 4, 7, 8, 10, 11], "Moon": [3, 6, 11],
        "Mars": [3, 5, 6, 10, 11, 12], "Mercury": [6, 8, 9, 10, 11, 12],
        "Jupiter": [5, 6, 11, 12], "Venus": [6, 11, 12],
        "Saturn": [3, 5, 6, 11], "Lagna": [1, 3, 4, 6, 10, 11]},
}

GLYPH = {"Sun": "☉", "Moon": "☽", "Mars": "♂", "Mercury": "☿", "Jupiter": "♃",
         "Venus": "♀", "Saturn": "♄"}
SWE_ID = {"Jupiter": "JUPITER", "Saturn": "SATURN", "Sun": "SUN", "Moon": "MOON",
          "Mars": "MARS", "Mercury": "MERCURY", "Venus": "VENUS"}

HOUSE_NAME = {
    1: "Self/Lagna", 2: "Wealth/Family", 3: "Courage/Siblings", 4: "Home/Emotions",
    5: "Children/Creativity", 6: "Work/Health/Struggle", 7: "Partnership",
    8: "Depth/Research", 9: "Fortune/Dharma", 10: "Career/Reputation",
    11: "Gains/Income", 12: "Expense/Abroad",
}


def _e(s) -> str:
    return html.escape(str(s))


def house_of(sign: str, lagna: str) -> int:
    return (SIGNS.index(sign) - SIGNS.index(lagna)) % 12 + 1


class AV:
    """Ashtakavarga model for one natal chart."""

    def __init__(self, pc: dict):
        self.pc = pc
        self.lagna = pc["meta"]["lagna_sign"]
        self.name = pc["meta"]["client"]
        # Natal sign index (0-11) for the 7 planets + Lagna.
        self.pos = {"Lagna": SIGNS.index(self.lagna)}
        for p in SEVEN:
            self.pos[p] = SIGNS.index(pc["planets"][p]["sign"])
        self.bav = {p: self._compute_bav(p) for p in SEVEN}
        self.sav = [sum(self.bav[p][s] for p in SEVEN) for s in range(12)]

    def _compute_bav(self, planet: str) -> list[int]:
        out = [0] * 12
        for s in range(12):
            score = 0
            for c in CONTRIBUTORS:
                dist = (s - self.pos[c]) % 12 + 1
                if dist in TABLE[planet][c]:
                    score += 1
            out[s] = score
        return out

    def house(self, sign_idx: int) -> int:
        return (sign_idx - self.pos["Lagna"]) % 12 + 1

    def residents(self, sign_idx: int) -> list[str]:
        names = []
        for p in SEVEN + ["Rahu", "Ketu"]:
            pl = self.pc["planets"].get(p)
            if pl and SIGNS.index(pl["sign"]) == sign_idx:
                tag = p + ("[R]" if pl.get("retrograde") else "")
                names.append(tag)
        return names


# ───────────────────────── transit timing (swisseph) ─────────────────────────


def _jd(d: date) -> float:
    return swe.julday(d.year, d.month, d.day, 12.0)


def _sid_sign_and_deg(d: date, planet: str) -> tuple[int, float]:
    if not _SWE:
        return 0, 0.0
    xx, _ = swe.calc_ut(_jd(d), getattr(swe, SWE_ID[planet]),
                        swe.FLG_MOSEPH | swe.FLG_SIDEREAL)
    lon = xx[0] % 360
    return int(lon // 30) % 12, lon % 30


def _sid_sign(d: date, planet: str) -> int:
    return _sid_sign_and_deg(d, planet)[0]


# Fast antardasha lords — club 1–2 month windows listing every sign crossed.
FAST_AD_LORDS = frozenset({"Moon", "Mercury", "Sun"})
INGRESS_STEP = {
    "Moon": timedelta(days=1),
    "Sun": timedelta(days=2),
    "Mercury": timedelta(days=2),
}
DEFAULT_INGRESS_STEP = timedelta(days=4)
FAST_AD_CADENCE = {
    "Moon": "~2.5 days per sign",
    "Sun": "~30 days per sign",
    "Mercury": "~15–40 days per sign (retrograde loops)",
}


def transit_ingresses(planet: str, start: date, end: date) -> list[tuple[date, int]]:
    """Return [(ingress_date, sign_idx)] for sign changes in [start, end]."""
    if not _SWE:
        return []
    events = []
    prev = _sid_sign(start, planet)
    events.append((start, prev))
    d = start
    step = INGRESS_STEP.get(planet, DEFAULT_INGRESS_STEP)
    while d < end:
        nd = min(d + step, end)
        cur = _sid_sign(nd, planet)
        if cur != prev:
            lo, hi = d, nd
            while (hi - lo).days > 1:
                mid = lo + timedelta(days=(hi - lo).days // 2)
                if _sid_sign(mid, planet) == prev:
                    lo = mid
                else:
                    hi = mid
            events.append((hi, cur))
            prev = cur
        d = nd
    return events


def transit_timeline(av: AV, planet: str, start: date, end: date) -> list[dict]:
    """Sign-by-sign segments with BAV score and house."""
    ings = transit_ingresses(planet, start, end)
    segs = []
    for i, (d, sign_idx) in enumerate(ings):
        nxt = ings[i + 1][0] if i + 1 < len(ings) else end
        segs.append({
            "start": d, "end": nxt, "sign_idx": sign_idx,
            "sign": SIGNS[sign_idx], "house": av.house(sign_idx),
            "bav": av.bav[planet][sign_idx], "sav": av.sav[sign_idx],
        })
    return segs


# ───────────────────────────── interpretation ─────────────────────────────


def rate_sav(v: int) -> tuple[str, str]:
    if v >= 32:
        return ("Strong ✓", "strong")
    if v >= 30:
        return ("Above avg ✓", "strong")
    if v >= 25:
        return ("Near-average", "avg")
    return ("Weak ✗", "weak")


def quality_bav(v: int) -> tuple[str, str]:
    if v >= 7:
        return ("Excellent", "strong")
    if v >= 5:
        return ("Very Good", "strong")
    if v == 4:
        return ("Average", "avg")
    if v == 3:
        return ("Poor", "weak")
    return ("Very Unfortunate", "weak")


def donors(av: AV, planet: str, sign_idx: int) -> list[tuple[str, bool]]:
    """Which of the 8 contributors gave a bindu for `planet` in `sign_idx`."""
    out = []
    for c in CONTRIBUTORS:
        dist = (sign_idx - av.pos[c]) % 12 + 1
        out.append((c, dist in TABLE[planet][c]))
    return out


def big_three(av: AV, planet: str, sign_idx: int) -> dict:
    lagnesh = SIGN_LORD[av.lagna]
    d = dict(donors(av, planet, sign_idx))
    return {"Lagna": d["Lagna"], "Lagnesh": d.get(lagnesh, False), "Moon": d["Moon"],
            "all": d["Lagna"] and d.get(lagnesh, False) and d["Moon"]}


def transit_verdict(av: AV, planet: str, seg: dict) -> str:
    bt = big_three(av, planet, seg["sign_idx"])
    q, _ = quality_bav(seg["bav"])
    house = seg["house"]
    self_gives = dict(donors(av, planet, seg["sign_idx"]))[planet]
    bits = [
        f"{planet} transits your {_ord(house)} house ({HOUSE_NAME[house]}) at BAV {seg['bav']}/8 — {q.lower()}.",
        bav_transit_meaning(planet, house, seg["bav"], seg["sav"]),
    ]
    if bt["all"]:
        bits.append("All three of the Big Three (Lagna, chart-lord, Moon) approve — a genuinely supportive window.")
    elif not bt["Lagna"] and not bt["Lagnesh"]:
        bits.append("Both Lagna and the chart-lord withhold — a health-cautious, low-traction window.")
    elif bt["Moon"]:
        bits.append("The Moon (mind/finance) approves, softening the period.")
    if self_gives:
        lords = house_lords(av.lagna)
        ruled = [h for h in range(1, 13) if lords[h] == planet]
        if ruled:
            bits.append(
                f"{planet} gives to itself — houses {', '.join(str(h) for h in ruled)} stay actively protected."
            )
        else:
            bits.append(f"{planet} gives to itself — its own houses stay actively protected.")
    return " ".join(bits)


# ───────────────────────────── helpers ─────────────────────────────


def _ord(n: int) -> str:
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th"))


def _fmt(d) -> str:
    if isinstance(d, date):
        return d.strftime("%b %Y")
    return str(d)


def _fmtd(d) -> str:
    return d.strftime("%d %b %Y").lstrip('0') if isinstance(d, date) else str(d)


def _parse_date_short(iso: str) -> str:
    d = _d(iso)
    return d.strftime("%b %Y") if d else (iso or "")


def _ad_dates(ad: dict) -> tuple[date | None, date | None]:
    return _d(ad.get("start")), _d(ad.get("end"))


def _seg_at_date(segs: list[dict], when: date) -> dict | None:
    for seg in segs:
        if seg["start"] <= when < seg["end"]:
            return seg
    return segs[-1] if segs else None


def _snippet(text: str, n: int = 140) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


def _badge(v: int) -> str:
    return f'<span class="score-badge s{v}">{v}</span>'


def _md_backdrop_text(av: AV, md_lord: str, start: date, end: date) -> str:
    if md_lord not in SEVEN:
        return f"Mahadasha lord {md_lord} sets the chapter tone."
    segs = transit_timeline(av, md_lord, start, end)
    if not segs:
        return f"{md_lord} mahadasha transit data unavailable for this window."
    parts = []
    for seg in segs:
        q, _ = quality_bav(seg["bav"])
        parts.append(
            f"{md_lord} in {seg['sign']} ({_ord(seg['house'])} house) BAV {seg['bav']}/8 ({q.lower()}) "
            f"from {_fmt(seg['start'])} – {_fmt(seg['end'])} — "
            f"{bav_transit_meaning(md_lord, seg['house'], seg['bav'], seg['sav'])}"
        )
    return " ".join(parts)


def _ad_transit_text(av: AV, ad_lord: str, start: date, end: date) -> str:
    if ad_lord not in SEVEN:
        pl = av.pc["planets"].get(ad_lord, {})
        h = pl.get("house", 0)
        sign = pl.get("sign", "?")
        from ashtakavarga_analysis import PLANET_THEME
        theme = PLANET_THEME.get(ad_lord, ad_lord)
        return (
            f"{ad_lord} has no classical BAV row. Antardasha colour comes from natal {ad_lord} "
            f"in {sign} (house {h}) — {theme}. Weight the mahadasha lord's transit as the primary filter."
        )
    segs = transit_timeline(av, ad_lord, start, end)
    if not segs:
        return f"{ad_lord} transit data unavailable."
    parts = []
    for seg in segs:
        da = donor_analysis(av, ad_lord, seg["sign_idx"], donors, TABLE)
        q, _ = quality_bav(seg["bav"])
        parts.append(
            f"<strong>{ad_lord}</strong> crosses {seg['sign']} ({_ord(seg['house'])} — {HOUSE_NAME[seg['house']]}) "
            f"BAV {seg['bav']}/8 ({q.lower()}) {_fmt(seg['start'])} – {_fmt(seg['end'])}. "
            f"{bav_transit_meaning(ad_lord, seg['house'], seg['bav'], seg['sav'])} "
            f"Donor read: {da['verdict_txt']}"
        )
    return " ".join(parts)


def _net_ad_read(av: AV, md_lord: str, ad_lord: str, start: date, end: date) -> str:
    """Combine MD backdrop + AD transit into one plain-English sub-period verdict."""
    mid = start + (end - start) / 2
    md_seg = _seg_at_date(transit_timeline(av, md_lord, start, end) if md_lord in SEVEN else [], mid)
    ad_seg = _seg_at_date(transit_timeline(av, ad_lord, start, end) if ad_lord in SEVEN else [], mid)
    if not md_seg and md_lord in SEVEN:
        return "Transit qualification unavailable — rely on Vimshottari theme alone."
    md_bav = md_seg["bav"] if md_seg else 4
    ad_bav = ad_seg["bav"] if ad_seg else 4
    combo = md_bav + (ad_bav - 4) * 0.6
    if combo >= 5.5:
        tone = "Supportive sub-period — dasha themes meet a cooperative transit environment."
    elif combo <= 3:
        tone = "Friction sub-period — dasha may run, but transit environment resists easy delivery."
    else:
        tone = "Mixed sub-period — results depend on discipline and picking one lane at a time."
    if ad_lord in SEVEN and ad_seg:
        da = donor_analysis(av, ad_lord, ad_seg["sign_idx"], donors, TABLE)
        if da["verdict"] == "challenging":
            tone += " Antardasha lord donors are thin — guard health routines and cash buffers."
        elif da["verdict"] == "positive":
            tone += " Antardasha lord donors approve — lean into the houses they rule."
    return tone


def _transit_at(av: AV, planet: str, when: date) -> dict | None:
    if planet not in SEVEN:
        return None
    seg = _seg_at_date(
        transit_timeline(av, planet, when - timedelta(days=2), when + timedelta(days=2)),
        when,
    )
    if not seg:
        return None
    q, cls = quality_bav(seg["bav"])
    return {
        "planet": planet,
        "sign": seg["sign"],
        "house": seg["house"],
        "house_name": HOUSE_NAME[seg["house"]],
        "bav": seg["bav"],
        "quality": q,
        "cls": cls,
        "sav": seg["sav"],
        "short": _snippet(bav_transit_meaning(planet, seg["house"], seg["bav"], seg["sav"]), 72),
    }


def _natal_ad_note(av: AV, ad_lord: str) -> str:
    pl = av.pc["planets"].get(ad_lord, {})
    h = pl.get("house", "?")
    sign = pl.get("sign", "?")
    from ashtakavarga_analysis import PLANET_THEME
    return f"Natal {ad_lord} in {sign} (H{h}) — {PLANET_THEME.get(ad_lord, ad_lord)}; no BAV row"


def _area_dot(bav: int) -> str:
    if bav >= 5:
        return "🟢"
    if bav <= 3:
        return "🔴"
    return "🟡"


AREA_HOUSES = {
    "Career": {10},
    "Wealth": {2, 11},
    "Home": {4},
    "Health": {6, 8},
    "Marriage": {7},
    "Children": {5},
}


def _month_end(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _month_ranges(start: date, end: date) -> list[tuple[date, date]]:
    """Calendar-month slices within [start, end)."""
    out: list[tuple[date, date]] = []
    d = start
    while d < end:
        m_end = min(_month_end(d), end)
        if m_end > d:
            out.append((d, m_end))
        d = m_end
    return out


def _month_range_label(m_start: date, m_end: date) -> str:
    """Single month → 'Jun 2026'; span → 'Jun 2026 – Jul 2026'."""
    last = m_end - timedelta(days=1)
    if m_start.year == last.year and m_start.month == last.month:
        return _fmt(m_start)
    return f"{_fmt(m_start)} – {_fmt(last)}"


def _date_range_label(start: date, end: date) -> str:
    """Exclusive end — short spans for critical caution windows."""
    last = end - timedelta(days=1)
    if start >= end:
        return _fmtd(start)
    if start == last:
        return _fmtd(start)
    if start.year == last.year and start.month == last.month:
        return f"{start.day} – {last.day} {start.strftime('%b %Y')}"
    return f"{_fmtd(start)} – {_fmtd(last)}"


def _two_month_ranges(start: date, end: date) -> list[tuple[date, date]]:
    """Pair calendar months for past/future Moon antardasha summaries."""
    months = _month_ranges(start, end)
    if not months:
        return []
    paired: list[tuple[date, date]] = []
    i = 0
    while i < len(months):
        a0, a1 = months[i]
        if i + 1 < len(months):
            _, b1 = months[i + 1]
            paired.append((a0, b1))
            i += 2
        else:
            paired.append((a0, a1))
            i += 1
    return paired


def _is_fast_ad(ad_lord: str) -> bool:
    return ad_lord in FAST_AD_LORDS


def _fast_tour_string(av: AV, planet: str, start: date, end: date, *, compact: bool = True) -> str:
    """All sign-hops + BAV for a fast-moving antardasha lord in a window."""
    segs = transit_timeline(av, planet, start, end)
    if not segs:
        return f"{planet} transit data unavailable"
    parts = [f"{s['sign']} H{s['house']}·{s['bav']}" for s in segs]
    max_show = 14 if planet == "Moon" else 8
    if compact and len(parts) > max_show:
        head = " → ".join(parts[:4])
        tail = " → ".join(parts[-3:])
        return f"{head} → … → {tail} ({len(parts)} sign-hops)"
    return " → ".join(parts)


def _fast_month_summary(av: AV, planet: str, start: date, end: date) -> str:
    segs = transit_timeline(av, planet, start, end)
    if not segs:
        return ""
    best = max(segs, key=lambda s: s["bav"])
    worst = min(segs, key=lambda s: s["bav"])
    return (
        f"Peak hop: {best['sign']} H{best['house']}·{best['bav']} · "
        f"Thin hop: {worst['sign']} H{worst['house']}·{worst['bav']}"
    )


def _find_critical_overlaps(
    av: AV, md_lord: str, ad_lord: str, win_start: date, win_end: date,
) -> list[dict]:
    """MD×AD sign overlaps in [win_start, win_end) that meet book criticality."""
    if md_lord not in SEVEN or ad_lord not in SEVEN:
        return []
    md_segs = transit_timeline(av, md_lord, win_start, win_end)
    ad_segs = transit_timeline(av, ad_lord, win_start, win_end)
    hits: list[dict] = []
    for ms in md_segs:
        for ads in ad_segs:
            o_start = max(ms["start"], ads["start"], win_start)
            o_end = min(ms["end"], ads["end"], win_end)
            if o_start >= o_end:
                continue
            residents = av.residents(ads["sign_idx"])
            crit = assess_md_ad_criticality(
                av, md_lord, ad_lord,
                ms["sign_idx"], ms["house"], ms["bav"], ms["sav"],
                ads["sign_idx"], ads["house"], ads["bav"], ads["sav"],
                donors, TABLE, residents,
            )
            if crit["critical"]:
                hits.append({
                    "start": o_start, "end": o_end,
                    "md": ms, "ad": ads, "crit": crit,
                })
    hits.sort(key=lambda h: h["start"])
    return hits


def _life_area_dots_from_segs(segs: list[dict]) -> dict[str, str]:
    dots = {k: "·" for k in AREA_HOUSES}
    touched: dict[str, list[int]] = {k: [] for k in AREA_HOUSES}
    for s in segs:
        for area, houses in AREA_HOUSES.items():
            if s["house"] in houses:
                touched[area].append(s["bav"])
    for area, bavs in touched.items():
        if not bavs:
            continue
        if any(b <= 3 for b in bavs):
            dots[area] = "🔴"
        elif any(b >= 5 for b in bavs):
            dots[area] = "🟢"
        else:
            dots[area] = "🟡"
    return dots


def _life_area_dots(md_t: dict | None, ad_t: dict | None) -> dict[str, str]:
    dots = {k: "·" for k in AREA_HOUSES}
    for t in (md_t, ad_t):
        if not t:
            continue
        h = t["house"]
        for area, houses in AREA_HOUSES.items():
            if h in houses:
                dots[area] = _area_dot(t["bav"])
    return dots


def _combined_line_fast_month(
    md_lord: str, ad_lord: str, md_t: dict | None, ad_segs: list[dict],
) -> str:
    if not md_t:
        return "Transit data unavailable."
    md_part = f"{md_lord} in {md_t['sign']} (H{md_t['house']}, BAV {md_t['bav']}/8)"
    if not ad_segs:
        return md_part
    bavs = [s["bav"] for s in ad_segs]
    avg = sum(bavs) / len(bavs)
    cadence = FAST_AD_CADENCE.get(ad_lord, "fast sign changes")
    if md_t["bav"] >= 5 and avg >= 4.5:
        tone = f"supportive month — {ad_lord} tours mostly workable signs"
    elif md_t["bav"] <= 3 or avg <= 3:
        tone = f"caution month — finish one thread at a time ({cadence})"
    else:
        tone = f"mixed month — house tone shifts as {ad_lord} moves ({cadence})"
    hops = len(ad_segs)
    return f"{md_part} + {ad_lord} {hops} sign-hops (avg BAV {avg:.1f}) → {tone}"


def _combined_line_critical(md_lord: str, ad_lord: str, md: dict, ad: dict, reasons: list[str]) -> str:
    md_part = f"{md_lord} {md['sign']} H{md['house']} BAV {md['bav']}/8"
    ad_part = f"{ad_lord} {ad['sign']} H{ad['house']} BAV {ad['bav']}/8"
    why = "; ".join(reasons[:3])
    return f"⚠ Narrow caution: {md_part} + {ad_part} — {why}"


def _combined_line_month(md_lord: str, ad_lord: str, md_t: dict | None, ad_segs: list[dict]) -> str:
    return _combined_line_fast_month(md_lord, ad_lord, md_t, ad_segs)


def _combined_line(md_lord: str, ad_lord: str, md_t: dict | None, ad_t: dict | None) -> str:
    if not md_t:
        return "Transit data unavailable."
    md_part = f"{md_lord} in {md_t['sign']} (H{md_t['house']}, BAV {md_t['bav']}/8)"
    if not ad_t:
        return f"{md_part} — chapter backdrop for {md_t['short']}"
    ad_part = f"{ad_lord} in {ad_t['sign']} (H{ad_t['house']}, BAV {ad_t['bav']}/8)"
    md_b, ad_b = md_t["bav"], ad_t["bav"]
    if md_b >= 5 and ad_b >= 5:
        tone = "both transits supportive"
    elif md_b <= 3 or ad_b <= 3:
        tone = "one layer thin — pace yourself"
    else:
        tone = "mixed — steady effort wins"
    return f"{md_part} + {ad_part} → {tone}"


def _next_md_shift_in_ad(av: AV, md_lord: str, cur_ad: dict, today: date) -> str:
    if md_lord not in SEVEN:
        return ""
    start, end = _ad_dates(cur_ad)
    if not start or not end or today >= end:
        return ""
    segs = [s for s in transit_timeline(av, md_lord, today, end) if s["start"] > today]
    if not segs:
        return ""
    nxt = segs[0]
    q, _ = quality_bav(nxt["bav"])
    return (
        f"<p class='future'><strong>Next shift inside this antardasha (~{_fmt(nxt['start'])}):</strong> "
        f"{md_lord} enters <strong>{nxt['sign']}</strong> (H{nxt['house']}, BAV {nxt['bav']}/8, {q.lower()}) — "
        f"{_snippet(bav_transit_meaning(md_lord, nxt['house'], nxt['bav'], nxt['sav']), 90)}</p>"
    )


def _current_snapshot_html(av: AV, md_lord: str, cur_ad: dict, today: date) -> str:
    ad_lord = cur_ad.get("ad_lord", "")
    md_t = _transit_at(av, md_lord, today)
    ad_t = _transit_at(av, ad_lord, today) if ad_lord in SEVEN else None
    rng = f"{_parse_date_short(cur_ad.get('start', ''))} – {_parse_date_short(cur_ad.get('end', ''))}"
    rows = []
    if md_t:
        rows.append(
            f"<tr class='cur'><td><strong>{md_lord}</strong> (mahadasha)</td>"
            f"<td>{md_t['sign']}</td><td>{_ord(md_t['house'])} — {md_t['house_name']}</td>"
            f"<td>{_badge(md_t['bav'])}</td><td class='{md_t['cls']}'>{md_t['short']}</td></tr>"
        )
    if ad_t:
        rows.append(
            f"<tr class='cur'><td><strong>{ad_lord}</strong> (antardasha)</td>"
            f"<td>{ad_t['sign']}</td><td>{_ord(ad_t['house'])} — {ad_t['house_name']}</td>"
            f"<td>{_badge(ad_t['bav'])}</td><td class='{ad_t['cls']}'>{ad_t['short']}</td></tr>"
        )
    elif ad_lord:
        rows.append(
            f"<tr class='cur'><td><strong>{ad_lord}</strong> (antardasha)</td>"
            f"<td colspan='4'>{_natal_ad_note(av, ad_lord)}</td></tr>"
        )
    combined = _combined_line(md_lord, ad_lord, md_t, ad_t)
    dots = _life_area_dots(md_t, ad_t)
    dot_cells = "".join(f"<td style='text-align:center'>{dots[a]}</td>" for a in AREA_HOUSES)
    next_shift = _next_md_shift_in_ad(av, md_lord, cur_ad, today)
    fast_note = ""
    if ad_lord in FAST_AD_LORDS:
        fast_note = (
            f"<p class='fine'><strong>{ad_lord}</strong> changes sign on "
            f"<strong>{FAST_AD_CADENCE.get(ad_lord, 'a fast cadence')}</strong> — "
            "the monthly tour table below lists every sign-hop with BAV; "
            "this snapshot is today's position only. "
            "Narrow ⚠ rows appear only when book-backed criticality triggers (BAV ≤2/≤3 stack, "
            "weak SAV &lt;25, donor withhold, natal-sign BAV).</p>"
        )
    return (
        f'<div class="now"><strong>Right now ({_fmtd(today)}) — {md_lord}–{ad_lord} antardasha</strong> '
        f'<span class="period-label current">{rng}</span></div>'
        f"{fast_note}"
        "<table><tr><th>Planet</th><th>Transit sign</th><th>Your house</th><th>BAV</th><th>What it means</th></tr>"
        + "".join(rows) + "</table>"
        f'<p class="pred"><strong>Combined (today):</strong> {combined}</p>'
        f"{next_shift}"
        "<table><tr><th>Career</th><th>Wealth</th><th>Home</th><th>Health</th><th>Marriage</th><th>Children</th></tr>"
        f"<tr>{dot_cells}</tr></table>"
        "<p class='fine'>🟢 supportive transit · 🟡 mixed · 🔴 thin traction · · not activated by current MD/AD signs</p>"
    )


def _merge_dots(md_t: dict | None, ad_segs: list[dict]) -> dict[str, str]:
    dots = _life_area_dots(md_t, None)
    ad_dots = _life_area_dots_from_segs(ad_segs)
    for k in AREA_HOUSES:
        if ad_dots[k] == "·":
            continue
        if dots[k] == "·":
            dots[k] = ad_dots[k]
        elif ad_dots[k] == "🔴" or dots[k] == "🔴":
            dots[k] = "🔴"
        elif ad_dots[k] == "🟢" and dots[k] != "🔴":
            dots[k] = "🟢"
        else:
            dots[k] = "🟡"
    return dots


def _critical_window_row(
    av: AV, md_lord: str, ad_lord: str, hit: dict, today: date,
) -> str:
    o_start, o_end = hit["start"], hit["end"]
    ms, ads = hit["md"], hit["ad"]
    crit = hit["crit"]
    rng = _date_range_label(o_start, o_end)
    row_cls = "bad" if crit["tier"] == "bad" else "warn"
    md_cell = f"{ms['sign']} H{ms['house']} {_badge(ms['bav'])}"
    ad_cell = f"{ads['sign']} H{ads['house']} {_badge(ads['bav'])}"
    combined = _combined_line_critical(md_lord, ad_lord, ms, ads, crit["reasons"])
    dots = _life_area_dots(
        {"house": ms["house"], "bav": ms["bav"]},
        {"house": ads["house"], "bav": ads["bav"]},
    )
    dot_cells = "".join(f"<td style='text-align:center'>{dots[a]}</td>" for a in AREA_HOUSES)
    return (
        f"<tr class='{row_cls}'>"
        f"<td><span class='period-label {row_cls}'>⚠ Caution</span><br/>{rng}</td>"
        f"<td><strong>{md_lord}–{ad_lord}</strong></td>"
        f"<td>{md_cell}<br/><span class='fine'>MD backdrop this slice</span></td>"
        f"<td>{ad_cell}<br/><span class='fine'>{ad_lord} hop — narrowed span (rules10)</span></td>"
        f"<td>{_e(_snippet(combined, 140))}</td>"
        f"{dot_cells}</tr>"
    )


def _fast_month_row(
    av: AV, md_lord: str, ad_lord: str, m_start: date, m_end: date, today: date,
) -> str:
    mid = m_start + (m_end - m_start) // 2
    md_t = _transit_at(av, md_lord, mid)
    ad_segs = transit_timeline(av, ad_lord, m_start, m_end)
    rng = _month_range_label(m_start, m_end)
    row_cls = "cur" if m_start <= today < m_end else ("future" if m_start > today else "past")
    label = "NOW" if row_cls == "cur" else {"past": "Past", "future": "Ahead"}.get(row_cls, _fmt(m_start))
    md_cell = f"{md_t['sign']} H{md_t['house']} {_badge(md_t['bav'])}" if md_t else "—"
    md_mean = md_t["short"] if md_t else ""
    cadence = FAST_AD_CADENCE.get(ad_lord, "fast sign changes")
    tour = _fast_tour_string(av, ad_lord, m_start, m_end)
    summary = _fast_month_summary(av, ad_lord, m_start, m_end)
    ad_cell = (
        f"<strong>{ad_lord} tour</strong> ({cadence})<br/>"
        f"<span class='fine'>{_e(tour)}</span>"
    )
    if summary:
        ad_cell += f"<br/><span class='fine'>{_e(summary)}</span>"
    criticals = _find_critical_overlaps(av, md_lord, ad_lord, m_start, m_end)
    if criticals:
        cues = "; ".join(
            _date_range_label(c["start"], c["end"]) for c in criticals[:3]
        )
        ad_cell += (
            f"<br/><span class='fine'><strong>Book-critical slices</strong> (narrow rows below): {cues}</span>"
        )
    combined = _combined_line_fast_month(md_lord, ad_lord, md_t, ad_segs)
    dots = _merge_dots(md_t, ad_segs)
    dot_cells = "".join(f"<td style='text-align:center'>{dots[a]}</td>" for a in AREA_HOUSES)
    month_row = (
        f"<tr class='{row_cls}'>"
        f"<td><span class='period-label {row_cls}'>{label}</span><br/>{rng}</td>"
        f"<td><strong>{md_lord}–{ad_lord}</strong></td>"
        f"<td>{md_cell}<br/><span class='fine'>{_e(md_mean)}</span></td>"
        f"<td>{ad_cell}</td>"
        f"<td>{_e(_snippet(combined, 120))}</td>"
        f"{dot_cells}</tr>"
    )
    crit_rows = "".join(
        _critical_window_row(av, md_lord, ad_lord, h, today) for h in criticals
    )
    return month_row + crit_rows


def _fast_monthly_rows(av: AV, md_lord: str, ad: dict, today: date) -> str:
    ad_lord = ad.get("ad_lord", "")
    start, end = _ad_dates(ad)
    if not start or not end or ad_lord not in FAST_AD_LORDS:
        return ""
    status = ad.get("status", "")
    if status == "current":
        win_start = max(start, date(today.year, today.month, 1))
        win_end = min(end, today + timedelta(days=200))
    elif status == "past":
        win_start, win_end = start, end
        ranges = _two_month_ranges(win_start, win_end)
        return "".join(
            _fast_month_row(av, md_lord, ad_lord, a, b, today) for a, b in ranges
        )
    else:
        win_start = start
        win_end = min(end, start + timedelta(days=120))
    return "".join(
        _fast_month_row(av, md_lord, ad_lord, a, b, today)
        for a, b in _month_ranges(win_start, win_end)
    )


def _antardasha_rows_html(av: AV, md_lord: str, ad: dict, today: date) -> str:
    if _is_fast_ad(ad.get("ad_lord", "")):
        return _fast_monthly_rows(av, md_lord, ad, today)
    return _antardasha_row(av, md_lord, ad, today)


def _antardasha_row(av: AV, md_lord: str, ad: dict, today: date) -> str:
    ad_lord = ad.get("ad_lord", "")
    start, end = _ad_dates(ad)
    if not start or not end:
        return ""
    status = ad.get("status", "")
    when = today if status == "current" else start + (end - start) // 2
    md_t = _transit_at(av, md_lord, when)
    ad_t = _transit_at(av, ad_lord, when) if ad_lord in SEVEN else None
    rng = f"{_parse_date_short(ad.get('start', ''))} – {_parse_date_short(ad.get('end', ''))}"
    row_cls = "cur" if status == "current" else ("past" if status == "past" else "future")
    label = {"current": "NOW", "past": "Past", "future": "Ahead"}.get(status, status)
    md_cell = (
        f"{md_t['sign']} H{md_t['house']} {_badge(md_t['bav'])}" if md_t else "—"
    )
    if ad_t:
        ad_cell = f"{ad_t['sign']} H{ad_t['house']} {_badge(ad_t['bav'])}"
        ad_mean = ad_t["short"]
    elif ad_lord:
        ad_cell = f"{ad_lord} natal H{av.pc['planets'].get(ad_lord, {}).get('house', '?')}"
        ad_mean = _snippet(_natal_ad_note(av, ad_lord), 60)
    else:
        ad_cell, ad_mean = "—", ""
    combined = _combined_line(md_lord, ad_lord, md_t, ad_t)
    dots = _life_area_dots(md_t, ad_t)
    dot_cells = "".join(f"<td style='text-align:center'>{dots[a]}</td>" for a in AREA_HOUSES)
    md_mean = md_t["short"] if md_t else ""
    return (
        f"<tr class='{row_cls}'>"
        f"<td><span class='period-label {row_cls}'>{label}</span><br/>{rng}</td>"
        f"<td><strong>{md_lord}–{ad_lord}</strong></td>"
        f"<td>{md_cell}<br/><span class='fine'>{_e(md_mean)}</span></td>"
        f"<td>{ad_cell}<br/><span class='fine'>{_e(ad_mean)}</span></td>"
        f"<td>{_e(_snippet(combined, 110))}</td>"
        f"{dot_cells}</tr>"
    )


def _antardasha_confluence_section(av: AV, vim: dict, md_lord: str, today: date) -> str:
    ads = vim.get("current_md_antardashas", [])
    cur = next((a for a in ads if a.get("status") == "current"), None)
    show = [a for a in ads if a.get("status") == "past"][-2:]
    if cur:
        show.append(cur)
    show.extend([a for a in ads if a.get("status") == "future"][:4])
    rows = "".join(_antardasha_rows_html(av, md_lord, ad, today) for ad in show)
    snapshot = _current_snapshot_html(av, md_lord, cur or {}, today) if cur else ""
    headers = "".join(f"<th>{a}</th>" for a in AREA_HOUSES)
    fast_hdr = (
        "<p class='fine'>For <strong>Moon / Mercury / Sun</strong> antardasha: one row per "
        "<strong>calendar month</strong> (or two-month club for past), listing <em>all</em> "
        "sign-hops with house + BAV. Narrow <strong>⚠ Caution</strong> rows appear only when "
        "rules10 criticality fires (never hardcoded signs) — e.g. MD+AD BAV ≤2, weak SAV, "
        "donor withhold, natal-sign BAV ≤2.</p>"
    )
    return (
        "<h1>3 · Mahadasha + Antardasha transit confluence</h1>"
        "<p>Mahadasha lord = slow chapter backdrop. Antardasha lord = filter — "
        "<strong>Moon (~2.5d), Mercury (~15–40d), Sun (~30d)</strong> use monthly sign tours; "
        "slower lords keep one sign per sub-period.</p>"
        f"{snapshot}"
        f"{fast_hdr}"
        "<h2>Sub-period table (near past · now · near future)</h2>"
        "<table><tr><th>Period</th><th>Dasha</th><th>Mahadasha transit</th>"
        "<th>Antardasha transit</th><th>Combined meaning</th>" + headers + "</tr>"
        + rows + "</table>"
    )


def _css() -> str:
    try:
        t = GOLD.read_text(encoding="utf-8")
        i, j = t.find("<style>"), t.find("</style>")
        if i != -1 and j != -1:
            return t[i + 7:j]
    except Exception:
        pass
    return "body{font-family:Georgia,serif;max-width:48rem;margin:auto;padding:1.5rem}table{width:100%;border-collapse:collapse}td,th{border:1px solid #ccc;padding:.4rem}"


# ───────────────────────────── render ─────────────────────────────


def _sav_table(av: AV) -> str:
    rows = []
    order = sorted(range(12), key=lambda s: av.house(s))
    for s in order:
        h = av.house(s)
        rating, cls = rate_sav(av.sav[s])
        res = ", ".join(av.residents(s)) or "—"
        meaning = sav_house_meaning(h, av.sav[s], SIGNS[s], res)
        star = " ★" if av.sav[s] == max(av.sav) else ""
        strong = f"<strong>{av.sav[s]}</strong>" if av.sav[s] >= 30 else str(av.sav[s])
        rows.append(
            f"<tr><td>{SIGNS[s]}</td><td>{_ord(h)} — {HOUSE_NAME[h]}</td>"
            f"<td>{strong}</td><td class='{cls}'>{rating}{star}</td><td>{res}</td>"
            f"<td>{_e(meaning)}</td></tr>"
        )
    return (
        "<table><tr><th>Sign</th><th>House (from lagna)</th><th>SAV</th><th>Rating</th>"
        "<th>Resident(s)</th><th>What transit here means for you</th></tr>"
        + "".join(rows) + "</table>"
    )


def _bav_table(av: AV, planet: str) -> str:
    rows = []
    order = sorted(range(12), key=lambda s: av.house(s))
    for s in order:
        h = av.house(s)
        q, cls = quality_bav(av.bav[planet][s])
        meaning = bav_transit_meaning(planet, h, av.bav[planet][s], av.sav[s])
        rows.append(
            f"<tr><td>{SIGNS[s]}</td><td>{_ord(h)} — {HOUSE_NAME[h]}</td>"
            f"<td>{_badge(av.bav[planet][s])}</td><td class='{cls}'>{q}</td>"
            f"<td>{_e(meaning)}</td></tr>"
        )
    return (
        "<table><tr><th>Sign</th><th>House</th><th>" + planet + " BAV</th><th>Quality</th>"
        "<th>Transit meaning</th></tr>" + "".join(rows) + "</table>"
    )


def _donor_table(av: AV, planet: str, sign_idx: int) -> str:
    da = donor_analysis(av, planet, sign_idx, donors, TABLE)
    return donor_table_html(da, av.lagna)


def _ad_lord_at(vim: dict, when: date) -> tuple[str, dict | None]:
    for ad in vim.get("current_md_antardashas", []):
        start, end = _ad_dates(ad)
        if start and end and start <= when < end:
            return ad.get("ad_lord", ""), ad
    return "", None


def _sade_sati_html(av: AV, cur_sat: dict | None) -> str:
    moon_idx = av.pos["Moon"]
    sat_idx = cur_sat["sign_idx"] if cur_sat else av.pos["Saturn"]
    ss = sade_sati_status(moon_idx, sat_idx)
    moon_bav = av.bav["Saturn"][moon_idx]
    pre_idx = (moon_idx - 1) % 12
    post_idx = (moon_idx + 1) % 12
    if not ss["active"]:
        return (
            '<h1>6 · Saturn and Sade Sati qualification</h1>'
            '<p class="future">Saturn is not in the classic Sade Sati band relative to your natal Moon '
            f'({SIGNS[moon_idx]}). Structural Saturn backdrop: BAV {av.bav["Saturn"][sat_idx]}/8 '
            f'in {SIGNS[sat_idx]}.</p>'
        )
    q, _ = quality_bav(moon_bav)
    tone = "can still deliver gains when dasha and Jupiter cooperate" if moon_bav >= 5 else "needs patience and routine"
    return (
        '<h1>6 · Saturn and Sade Sati qualification</h1>'
        f'<div class="caution"><strong>Sade Sati active</strong> - phase: {ss["phase"]}. '
        f'Saturn BAV in Moon sign ({SIGNS[moon_idx]}): {moon_bav}/8 ({q.lower()}). '
        f'Pre-Moon sign BAV: {av.bav["Saturn"][pre_idx]}; post-Moon: {av.bav["Saturn"][post_idx]}. '
        f'Book rule: high Saturn BAV in Moon sign {tone}.</div>'
    )


def _kakshaya_note(av: AV, planet: str, d: date) -> str:
    if not _SWE:
        return ""
    _, deg = _sid_sign_and_deg(d, planet)
    sec = kakshaya_sector(deg)
    sign_idx = _sid_sign(d, planet)
    gave = dict(donors(av, planet, sign_idx)).get(sec["ruler"], False)
    if sec["ruler"] == "Lagna":
        gave = dict(donors(av, planet, sign_idx)).get("Lagna", False)
    state = "switched on" if gave else "switched off"
    return (
        f'<p class="fine"><strong>Kakshaya:</strong> {planet} at {deg:.2f} in sign '
        f'is in sector {sec["sector"]} ruled by {sec["ruler"]} ({state} for this BAV).</p>'
    )


def _confluence_table(av: AV, md_lord: str, jup_segs: list[dict], sat_segs: list[dict], today: date) -> str:
    rows = []
    for seg in [s for s in jup_segs if s["end"] > today][:4]:
        sat = next((s for s in sat_segs if s["start"] <= seg["start"] < s["end"]), None)
        da = donor_analysis(av, md_lord, seg["sign_idx"], donors, TABLE)
        rows.append(
            f"<tr><td>{_fmt(seg['start'])} - {_fmt(seg['end'])}</td>"
            f"<td>{md_lord} {seg['sign']} BAV {seg['bav']}</td>"
            f"<td>{da['verdict']}</td>"
            f"<td>{sat['sign'] if sat else '-'} BAV {sat['bav'] if sat else '-'}</td></tr>"
        )
    if not rows:
        return ""
    return (
        '<h1>10 - Multi-system confluence note</h1>'
        '<p class="fact">High BAV + supportive dasha = strong event window; low BAV dampens even good dasha themes.</p>'
        '<table><tr><th>Window</th><th>MD lord transit</th><th>Donor verdict</th><th>Saturn backdrop</th></tr>'
        + "".join(rows) + "</table>"
    )


def _transit_rows(av: AV, segs: list[dict], planet: str) -> str:
    out = []
    today = date.today()
    for seg in segs:
        cur = seg["start"] <= today < seg["end"]
        q, cls = quality_bav(seg["bav"])
        rowcls = "cur" if cur else ("peak" if seg["bav"] >= 5 else ("bad" if seg["bav"] <= 2 else "warn"))
        meaning = _e(_snippet(bav_transit_meaning(planet, seg["house"], seg["bav"], seg["sav"]), 120))
        out.append(
            f"<tr class='{rowcls}'><td>{_fmt(seg['start'])} – {_fmt(seg['end'])}</td>"
            f"<td>{seg['sign']} ({_ord(seg['house'])})</td><td>{_badge(seg['bav'])}</td>"
            f"<td class='{cls}'>{q}</td><td>{meaning}</td></tr>"
        )
    return (
        "<table><tr><th>Window</th><th>" + planet + " transit</th><th>BAV</th><th>Quality</th>"
        "<th>Life meaning</th></tr>" + "".join(out) + "</table>"
    )


def render(av: AV, dob_disp: str, extract_path: str = "") -> str:
    vim = av.pc.get("vimshottari", {})
    md = vim.get("current_md", {})
    md_lord = md.get("md_lord", "Jupiter")
    cur_ad = next((a for a in vim.get("current_md_antardashas", []) if a["status"] == "current"), {})
    today = date.today()
    win_start = date(today.year - 5, 1, 1)
    win_end = date(today.year + 6, 1, 1)

    md_segs = transit_timeline(av, md_lord, win_start, win_end) if md_lord in SEVEN else []
    jup_segs = transit_timeline(av, "Jupiter", win_start, win_end)
    sat_segs = transit_timeline(av, "Saturn", win_start, win_end)
    focus_segs = md_segs if md_segs else jup_segs
    cur_md_seg = next((s for s in focus_segs if s["start"] <= today < s["end"]), None)
    cur_jup = next((s for s in jup_segs if s["start"] <= today < s["end"]), None)
    cur_sat = next((s for s in sat_segs if s["start"] <= today < s["end"]), None)
    nxt_md = next((s for s in focus_segs if s["start"] > today), None)

    extract_av = None
    validation_note = ""
    if extract_path:
        try:
            extract_av = parse_extract_ashtakavarga(Path(extract_path).read_text(encoding="utf-8", errors="ignore"))
            validation_note = validate_against_extract(av.sav, extract_av)
        except Exception:
            pass

    high_sign = max(range(12), key=lambda s: av.sav[s])
    nm = _e(av.name)
    book_method = methodology_html()

    lead_extra = ""
    if cur_md_seg and nxt_md:
        lead_extra = (f"<p>The pivotal near-term story: <strong>{md_lord} — your mahadasha lord — "
                      f"is in {cur_md_seg['sign']} (BAV {cur_md_seg['bav']}/8)</strong> and shifts into "
                      f"<strong>{nxt_md['sign']} (BAV {nxt_md['bav']}/8)</strong> around "
                      f"<strong>{_fmt(nxt_md['start'])}</strong>"
                      + (" — a clear lift." if nxt_md['bav'] > cur_md_seg['bav']
                         else " — a step down to watch." if nxt_md['bav'] < cur_md_seg['bav'] else ".")
                      + "</p>")

    spotlight = ""
    target = cur_md_seg if (cur_md_seg and cur_md_seg["bav"] >= 5) else nxt_md
    if target:
        bt = big_three(av, md_lord, target["sign_idx"])
        spotlight = f"""
<div class="peak-box">
  <h3 style="color:var(--green);margin-top:.2rem;">★ {md_lord} in {target['sign']} ({_ord(target['house'])} house) — BAV {target['bav']}/8</h3>
  <p>{transit_verdict(av, md_lord, target)}</p>
  {_donor_table(av, md_lord, target['sign_idx'])}
  <p><strong>{'All three Big Three gave' if bt['all'] else 'Mixed Big-Three support'}.</strong>
  Window: approximately {_fmtd(target['start'])} – {_fmtd(target['end'])}.</p>
</div>"""

    # Near-future snapshot: monthly rows (Moon = full sign tour each month).
    snap_end = today + timedelta(days=240)
    snap_rows = []
    for m_start, m_end in _month_ranges(today, snap_end):
        mid = m_start + (m_end - m_start) // 2
        md_t = _transit_at(av, md_lord, mid)
        if not md_t:
            continue
        sat = _seg_at_date(transit_timeline(av, "Saturn", m_start, m_end), mid)
        ad_lord, ad = _ad_lord_at(vim, mid)
        if ad_lord in FAST_AD_LORDS:
            tour = _fast_tour_string(av, ad_lord, m_start, m_end)
            summ = _fast_month_summary(av, ad_lord, m_start, m_end)
            cadence = FAST_AD_CADENCE.get(ad_lord, "fast")
            ad_note = f"<strong>{ad_lord} monthly tour</strong> ({cadence}): {_e(tour)}"
            if summ:
                ad_note += f"<br/><span class='fine'>{_e(summ)}</span>"
            criticals = _find_critical_overlaps(av, md_lord, ad_lord, m_start, m_end)
            if criticals:
                ad_note += "<br/><span class='fine'><strong>⚠ Narrow slices:</strong> " + _e(
                    "; ".join(_date_range_label(c["start"], c["end"]) for c in criticals[:2])
                ) + "</span>"
            overall = _combined_line_fast_month(
                md_lord, ad_lord, md_t, transit_timeline(av, ad_lord, m_start, m_end),
            )
        elif ad_lord and ad_lord in SEVEN:
            ad_seg = _transit_at(av, ad_lord, mid)
            ad_note = (
                f"{ad_lord} in {ad_seg['sign']} (H{ad_seg['house']}) BAV {ad_seg['bav']}/8"
                if ad_seg else "—"
            )
            overall = _combined_line(md_lord, ad_lord, md_t, ad_seg) if ad_seg else "—"
        elif ad_lord:
            ad_note = f"{ad_lord} — natal filter (no BAV)"
            overall = _snippet(_combined_line(md_lord, ad_lord, md_t, None), 80)
        else:
            ad_note = "—"
            overall = "—"
        rc = "cur" if m_start <= today < m_end else "warn"
        if md_t["bav"] >= 5:
            rc = "peak"
        elif md_t["bav"] <= 2:
            rc = "bad"
        snap_rows.append(
            f"<tr class='{rc}'><td>{_month_range_label(m_start, m_end)}</td>"
            f"<td>{md_lord}–{ad_lord or '?'}</td>"
            f"<td>{md_t['sign']} (H{md_t['house']})</td><td>{_badge(md_t['bav'])}</td>"
            f"<td>{ad_note}</td>"
            f"<td>{sat['sign'] if sat else '—'} ({_badge(sat['bav']) if sat else '—'})</td>"
            f"<td>{_e(_snippet(overall, 100))}</td></tr>"
        )
        if len(snap_rows) >= 8:
            break
    snapshot = (
        "<table><tr><th>Month</th><th>Antardasha</th><th>" + md_lord + " transit</th><th>MD BAV</th>"
        "<th>AD transit (fast lords = all signs in month)</th><th>Saturn backdrop</th><th>Combined</th></tr>"
        + "".join(snap_rows) + "</table>"
        "<p class='fine'>Moon / Mercury / Sun antardasha: each row clubs every sign crossed that month. "
        "⚠ Caution slices narrow only on rules10 criticality. Jupiter/Saturn spans are slow.</p>"
    )

    events = _event_signals(av)
    antardasha = _antardasha_confluence_section(av, vim, md_lord, today)
    sade_sati = _sade_sati_html(av, cur_sat)
    kakshaya = _kakshaya_note(av, md_lord, today)
    confluence = _confluence_table(av, md_lord, focus_segs, sat_segs, today)

    body = f"""
<div class="uncal-banner" style="background:#fff8e1;border-left:4px solid #f9a825;padding:12px 18px;margin-bottom:22px;border-radius:8px;font-size:.9rem;line-height:1.55;">
<strong>⚠ Uncalibrated — first pass.</strong> Predictions follow standard Ashtakavarga methodology with Swiss-Ephemeris transit timing; treat dates as provisional until past milestones are confirmed.
</div>

<div class="cover">
  <div class="sub">VEDIC ASTROLOGY · PREDICTIVE READING</div>
  <h1>Ashtakavarga Transit Report</h1>
  <div class="sub">{nm} &nbsp;·&nbsp; {av.lagna} Ascendant &nbsp;·&nbsp; {_fmtd(today)}</div>
  <div class="tag">NEAR PAST · CURRENT · FUTURE TRANSIT FORECAST</div>
</div>

<div class="card lead">
  <p>Ashtakavarga scores every planetary transit from 0 to 8, by counting how many of the eight cosmic
  factors (seven planets + Ascendant) "approve" of it. A score of 6+ means the system is broadly behind
  that transit; 1–2 means almost everything resists it.</p>
  {lead_extra}
  <p class="fine">Bindus computed from the natal chart via the classical Parashari Ashtakavarga tables
  (grand total 337). Transit timing from Swiss Ephemeris (sidereal Lahiri). Mahadasha: {md_lord}
  ({_fmt(_d(md.get('start')))} – {_fmt(_d(md.get('end')))}). Current antardasha: {md_lord}–{cur_ad.get('ad_lord','')}.
  {validation_note}</p>
</div>

{book_method}

<h1>1 · House Strength Map (Sarvāṣṭakavarga)</h1>
<p>The SAV total for each sign shows how well that house performs when planets transit it. Average is 28
of a maximum 56; above 30 is favourable, below 25 is weak.</p>
{_sav_table(av)}
<div class="highlight"><strong>Key insight:</strong> Your strongest house is
<strong>{SIGNS[high_sign]} ({_ord(av.house(high_sign))} — {HOUSE_NAME[av.house(high_sign)]}, SAV {av.sav[high_sign]})</strong>
— transits there produce the most tangible results. {_sav_weak_note(av)}</div>

<h1>2 · {md_lord}'s Transit Scorecard (BAV — Mahādaśā Lord)</h1>
<p>{md_lord} rules your current mahādaśā, so the quality of each chapter depends heavily on which sign
{md_lord} transits and how many bindus it earns there.</p>
{_bav_table(av, md_lord)}

{antardasha}

<h1>4 · Current {md_lord} transit (mahadasha backdrop)</h1>
<div class="now"><strong>Right now ({_fmtd(today)}):</strong> {transit_verdict(av, md_lord, cur_md_seg) if cur_md_seg else 'transit data unavailable.'}</div>
{kakshaya}
{spotlight}

<h1>5 · {md_lord} transit timeline ({win_start.year}–{win_end.year-1})</h1>
{_transit_rows(av, focus_segs, md_lord)}

{sade_sati}

<h1>7 · Saturn background transit</h1>
<p>Saturn is slow and structural; its BAV colours the backdrop against which faster transits play out.</p>
{_transit_rows(av, sat_segs, "Saturn")}

<h1>8 · Monthly near-future snapshot</h1>
{snapshot}

<h1>9 · Event-specific signals (by house SAV)</h1>
{events}

{confluence}

<h1>11 · How to use this layer</h1>
<div class="card"><p>Ashtakavarga is a <em>qualifying layer</em>, not a standalone predictor. When its signal
agrees with the running Vimśottarī dasha, treat the reading as high-confidence; when they diverge, weight
the dasha first (it governs karma delivery) and use Ashtakavarga to gauge the ease or friction of the
transit environment.</p></div>

<footer>
  Vedic Ashtakavarga Transit Report · {nm} · generated {_fmtd(today)}<br/>
  Bindus: classical Parāśarī tables (SAV total 337). Transit timing: Swiss Ephemeris, sidereal Lahiri.<br/>
  Educational and self-awareness purposes only — cross-reference with Vimśottarī, Yogini, Jaimini, and BNN.
</footer>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Vedic Reading — Ashtakavarga Transit — {nm}</title>
<style>{_css()}</style></head><body>{body}</body></html>"""


def _overall_signal(jup: int, sat: int) -> str:
    score = jup + (sat - 4) * 0.5
    if jup >= 6 and sat >= 3:
        return "<span class='strong'>Strong positive lift</span>"
    if jup >= 5:
        return "<span class='strong'>Good — supported window</span>"
    if jup <= 2:
        return "<span class='weak'>Compressed — low traction</span>"
    return "<span class='avg'>Mixed — moderate</span>"


def _sav_weak_note(av: AV) -> str:
    weak = [(SIGNS[s], av.house(s), av.sav[s]) for s in range(12) if av.sav[s] < 25]
    if not weak:
        return "No house falls in the structurally weak band."
    parts = ", ".join(f"{sg} ({_ord(h)}, {v})" for sg, h, v in sorted(weak, key=lambda x: x[2]))
    return f"Structurally weaker houses where events take extra effort: {parts}."


def _event_signals(av: AV) -> str:
    def line(area: str, house: int, extra: str = "") -> str:
        s = av.pos["Lagna"]
        sign_idx = (s + house - 1) % 12
        rating, cls = rate_sav(av.sav[sign_idx])
        meaning = sav_house_meaning(house, av.sav[sign_idx], SIGNS[sign_idx])
        return (
            f"<li><strong>{area} ({_ord(house)} — {SIGNS[sign_idx]}, SAV {av.sav[sign_idx]}):</strong> "
            f"<span class='{cls}'>{rating}</span>. {meaning} {extra}</li>"
        )
    return (
        "<ul>"
        + line("Career / Profession", 10, "Watch for mahadasha lord transits with BAV 5+ through this sign.")
        + line("Financial / Wealth", 2, "Income lifts when benefics transit with 2nd-lord donating bindus.")
        + line("Financial / Gains", 11, "Peer-network and income experiments track transit quality here.")
        + line("Partnerships", 7, "Marriage/partner events need supportive 7th-house transit BAV, not SAV alone.")
        + line("Health / Service", 6, "Strong 6th SAV favours competitive wins when Lagna/Lagnesh also donate.")
        + line("Children / Creativity", 5, "Creative and progeny themes need both dasha promise and 5th-house transit support.")
        + "</ul>"
    )


def build_confluence_claims(av: AV) -> list:
    """Structured LaneClaim-like dicts for confluence harvest."""
    from lane_claim import LaneClaim

    claims: list[LaneClaim] = []
    vim = av.pc.get("vimshottari", {})
    md_lord = vim.get("current_md", {}).get("md_lord", "Jupiter")
    today = date.today()
    cur_ad = next((a for a in vim.get("current_md_antardashas", []) if a.get("status") == "current"), {})
    ad_lord = cur_ad.get("ad_lord", "")
    win_start, win_end = today - timedelta(days=30), today + timedelta(days=30)

    if md_lord in SEVEN:
        md_seg = _seg_at_date(transit_timeline(av, md_lord, win_start, win_end), today)
        if md_seg:
            direction = "positive" if md_seg["bav"] >= 5 else ("caution" if md_seg["bav"] <= 3 else "neutral")
            dom = {2: "finance", 4: "property", 5: "children", 6: "health", 7: "marriage",
                   9: "travel", 10: "career", 11: "finance", 12: "travel"}.get(md_seg["house"], "career")
            claims.append(LaneClaim(
                lane="Ashtakavarga",
                section_id="dasha",
                domain=dom,
                direction=direction,
                text=(
                    f"Mahadasha lord {md_lord} transits {md_seg['sign']} ({_ord(md_seg['house'])} house) at BAV "
                    f"{md_seg['bav']}/8 — {bav_transit_meaning(md_lord, md_seg['house'], md_seg['bav'], md_seg['sav'])}"
                ),
                timing=_fmt(md_seg["start"]) + " – " + _fmt(md_seg["end"]),
            ))

    if ad_lord and ad_lord in SEVEN:
        a_start, a_end = _ad_dates(cur_ad)
        if a_start and a_end:
            ad_seg = _seg_at_date(transit_timeline(av, ad_lord, a_start, a_end), today)
            if ad_seg:
                direction = "positive" if ad_seg["bav"] >= 5 else ("caution" if ad_seg["bav"] <= 3 else "neutral")
                dom = {2: "finance", 4: "property", 5: "children", 6: "health", 7: "marriage",
                       9: "travel", 10: "career", 11: "finance", 12: "travel"}.get(ad_seg["house"], "current")
                claims.append(LaneClaim(
                    lane="Ashtakavarga",
                    section_id="antardasha",
                    domain=dom,
                    direction=direction,
                    text=(
                        f"Antardasha lord {ad_lord} filters the sub-period from {ad_seg['sign']} "
                        f"({_ord(ad_seg['house'])} house) at BAV {ad_seg['bav']}/8 — "
                        f"{bav_transit_meaning(ad_lord, ad_seg['house'], ad_seg['bav'], ad_seg['sav'])} "
                        f"Net: {_net_ad_read(av, md_lord, ad_lord, a_start, a_end)}"
                    ),
                    timing=_parse_date_short(cur_ad.get("start", "")) + " – " + _parse_date_short(cur_ad.get("end", "")),
                ))

    for house, dom in ((10, "career"), (2, "finance"), (7, "marriage"), (6, "health"), (5, "children")):
        sign_idx = (av.pos["Lagna"] + house - 1) % 12
        if av.sav[sign_idx] >= 32:
            claims.append(LaneClaim(
                lane="Ashtakavarga",
                section_id=f"sav_{house}",
                domain=dom,
                direction="positive",
                text=(
                    f"Structural strength: {_ord(house)} house ({SIGNS[sign_idx]}) SAV {av.sav[sign_idx]} — "
                    f"{sav_house_meaning(house, av.sav[sign_idx], SIGNS[sign_idx])}"
                ),
            ))
        elif av.sav[sign_idx] < 25:
            claims.append(LaneClaim(
                lane="Ashtakavarga",
                section_id=f"sav_{house}",
                domain=dom,
                direction="caution",
                text=(
                    f"Structural thin spot: {_ord(house)} house ({SIGNS[sign_idx]}) SAV {av.sav[sign_idx]} — "
                    f"{sav_house_meaning(house, av.sav[sign_idx], SIGNS[sign_idx])}"
                ),
            ))
    return claims


def _d(iso: Optional[str]) -> Optional[date]:
    if not iso:
        return None
    try:
        return datetime.strptime(iso, "%Y-%m-%d").date()
    except Exception:
        return None


def generate_ashtakavarga_html(
    client_name: str,
    dob: str,
    *,
    extracted_path: Optional[str] = None,
    precomputed_path: Optional[str] = None,
    birth_time: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    timezone: Optional[float] = None,
    place_name: str = "",
    gender: int = 0,
) -> tuple[str, dict]:
    pc = resolve_precompute(
        client_name, dob,
        extracted_path=extracted_path,
        precomputed_path=precomputed_path,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        place_name=place_name,
    )
    av = AV(pc)
    try:
        dob_disp = datetime.strptime(dob, "%Y-%m-%d").strftime("%d %B %Y").lstrip('0')
    except Exception:
        dob_disp = dob
    source_label = precomputed_path or extracted_path or (
        f"PyJHora ({place_name or 'birth data'})" if birth_time else "chart"
    )
    doc = render(av, dob_disp, source_label)
    summary = {"lagna": av.lagna, "sav": {SIGNS[s]: av.sav[s] for s in range(12)},
               "jupiter_bav": {SIGNS[s]: av.bav["Jupiter"][s] for s in range(12)},
               "sav_total": sum(av.sav)}
    return doc, summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Deterministic Ashtakavarga report (no LLM)")
    ap.add_argument("name")
    ap.add_argument("dob")
    ap.add_argument("extracted", nargs="?", default=None, help="AstroSage extract (optional if --precomputed or birth flags)")
    add_chart_source_args(ap)
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--validate", action="store_true", help="print SAV/BAV and exit")
    args = ap.parse_args()
    kw = chart_kwargs_from_args(args)
    pc = resolve_precompute(
        args.name, args.dob,
        extracted_path=args.extracted,
        **kw,
    )
    av = AV(pc)
    if args.validate:
        print("SAV total:", sum(av.sav), "(expect 337)")
        for s in range(12):
            print(f"  {SIGNS[s]:11} H{av.house(s):<2} SAV={av.sav[s]:<3} JupBAV={av.bav['Jupiter'][s]}")
        for p in SEVEN:
            print(f"{p} BAV total:", sum(av.bav[p]))
        return
    doc, summary = generate_ashtakavarga_html(
        args.name, args.dob,
        extracted_path=args.extracted,
        **kw,
    )
    out = Path(args.out) if args.out else BASE_DIR / "reports" / f"Vedic_Ashtakavarga_{args.name}_preview.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(f"SAV total={summary['sav_total']} (337 expected) · written → {out}")


if __name__ == "__main__":
    main()
