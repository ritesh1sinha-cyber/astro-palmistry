#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vedic daily confluence: Vim + Jaimini Chara MD/AD/PD + Moon + gochar + AV (rules1/rules6/rules11)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from astro_precompute import SIGNS
from ashtakavarga_analysis import HOUSE_LIFE_THEME
from jaimini_chara_dasha import active_jaimini_chara
from vedic_jaimini_report import MAHA_PLAIN as JAIMINI_MAHA_PLAIN, PERIOD_PLAIN as JAIMINI_SIGN_PLAIN, house_of
from jaimini_daily_confluence import build_jaimini_daily_confluence
from daily_reading_plain import build_plain_daily_reading
from gk_transit_dasha import is_karmic_dasha, score_transit_dasha_synergy
from boney_divisional_timing import dignity_crosscheck_for_lord

VIM_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
VIM_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}

SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

VIM_MAHA_PLAIN = {
    "Sun": "visibility and authority",
    "Moon": "home, feelings, and emotional security",
    "Mars": "drive, courage, and pushing through blocks",
    "Mercury": "deals, study, writing, and short travel",
    "Jupiter": "growth, mentors, and fair expansion",
    "Venus": "love, comfort, creativity, and what you enjoy earning",
    "Saturn": "duty, patience, and reputation built slowly",
    "Rahu": "ambition, foreign links, and unconventional moves",
    "Ketu": "letting go, research, and fewer material attachments",
}

VIM_PERIOD_PLAIN = {
    "Sun": "step up cleanly; watch ego heat and overexposure",
    "Moon": "feelings and family colour the day; rest matters",
    "Mars": "energy is high; act, but do not pick fights to vent",
    "Mercury": "mail, study, and paperwork convert if you organise first",
    "Jupiter": "mentors and modest growth help; skip over-promising",
    "Venus": "comfort, taste, and relationship warmth are available",
    "Saturn": "discipline beats shortcuts; boring tasks pay off",
    "Rahu": "restless appetite for change; ground one practical move",
    "Ketu": "quiet inward work; release one draining habit or object",
}

# Signs that tend to lift a daily mood in Chara pratyantar (rules6 heuristic).
JAIMINI_PD_BOOST = {"Taurus", "Gemini", "Cancer", "Leo", "Sagittarius", "Libra"}
JAIMINI_PD_CAUTION = {"Scorpio", "Capricorn", "Aquarius", "Pisces"}


def _parse_d(iso: str) -> date:
    return datetime.strptime(iso[:10], "%Y-%m-%d").date()


def _fmt_d(d: date) -> str:
    return d.strftime("%d %b %Y")


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def compute_pratyantars(ad_lord: str, ad_start: date, ad_end: date) -> list[dict[str, Any]]:
    total_days = (ad_end - ad_start).days
    if total_days <= 0:
        return []
    start_i = VIM_ORDER.index(ad_lord)
    order = VIM_ORDER[start_i:] + VIM_ORDER[:start_i]
    out: list[dict[str, Any]] = []
    cur = ad_start
    for k, pd_lord in enumerate(order):
        end = ad_start + timedelta(
            days=round(sum(VIM_YEARS[order[i]] for i in range(k + 1)) / 120.0 * total_days)
        )
        out.append({"lord": pd_lord, "start": cur, "end": end})
        cur = end
    if out:
        out[-1]["end"] = ad_end
    return out


def active_vimshottari(pc: dict, target: date) -> dict[str, Any]:
    vim = pc.get("vimshottari", {})
    md_row = vim.get("current_md", {})
    md = md_row.get("md_lord", "")
    md_start = md_row.get("start", "")
    md_end = md_row.get("end", "")

    ad, ad_start_s, ad_end_s = "", "", ""
    for row in vim.get("current_md_antardashas", []):
        start, end = row.get("start", ""), row.get("end", "")
        if start and end and start <= target.isoformat() <= end:
            ad = row.get("ad_lord", "")
            ad_start_s, ad_end_s = start, end
            break

    pd, pd_start, pd_end = "", None, None
    if ad and ad_start_s and ad_end_s:
        ad_start, ad_end = _parse_d(ad_start_s), _parse_d(ad_end_s)
        for row in compute_pratyantars(ad, ad_start, ad_end):
            if row["start"] <= target <= row["end"]:
                pd = row["lord"]
                pd_start, pd_end = row["start"], row["end"]
                break

    return {
        "md": md,
        "ad": ad,
        "pd": pd,
        "md_start": md_start,
        "md_end": md_end,
        "ad_start": ad_start_s,
        "ad_end": ad_end_s,
        "pd_start": pd_start.isoformat() if pd_start else "",
        "pd_end": pd_end.isoformat() if pd_end else "",
        "stack": "-".join(x for x in (md, ad, pd) if x),
    }


def _planet_daily_note(lord: str, pc: dict, lagna: str) -> str:
    pl = pc.get("planets", {}).get(lord, {})
    if not pl:
        return VIM_PERIOD_PLAIN.get(lord, "")
    house = pl.get("house") or (
        (SIGNS.index(pl.get("sign", "Aries")) - SIGNS.index(lagna)) % 12 + 1
        if pl.get("sign") and lagna in SIGNS else 1
    )
    theme = HOUSE_LIFE_THEME.get(int(house), "this life area")
    plain = VIM_PERIOD_PLAIN.get(lord, "")
    return f"{plain.capitalize()}. {lord} sits in your {_ordinal(int(house))} house ({theme})."


def _sign_daily_note(sign: str, lagna: str) -> str:
    if not sign or sign not in SIGNS:
        return ""
    h = house_of(sign, lagna)
    theme = HOUSE_LIFE_THEME.get(h, "this life area")
    plain = JAIMINI_SIGN_PLAIN.get(sign, "mixed sign themes - stay steady.")
    return f"{plain} From your {lagna} lagna this sign maps to the {_ordinal(h)} house ({theme})."


def _transit_hits_vim_lords(moon_sign: str, pc: dict, lords: tuple[str, ...]) -> list[str]:
    hits = []
    for lord in lords:
        if not lord:
            continue
        natal = pc.get("planets", {}).get(lord, {})
        if natal.get("sign") == moon_sign:
            hits.append(lord)
    return hits


def _transit_hits_chara_signs(moon_sign: str, signs: tuple[str, ...]) -> list[str]:
    labels = []
    for sign in signs:
        if sign and moon_sign == sign:
            labels.append(sign)
    return labels


def _dual_pd_agreement(vim_pd: str, jaimini_pd: str, pc: dict) -> str:
    """When Vim PD lord's natal sign matches Jaimini PD sign, both systems agree."""
    if not vim_pd or not jaimini_pd:
        return ""
    natal_sign = pc.get("planets", {}).get(vim_pd, {}).get("sign", "")
    if natal_sign == jaimini_pd:
        return (
            f"Vimshottari {vim_pd} pratyantar and Jaimini {jaimini_pd} pratyantar concur - "
            f"natal {vim_pd} already sits in {jaimini_pd}, so both clocks point at the same life theatre."
        )
    return ""


def build_vedic_daily_confluence(
    *,
    client: str,
    target: date,
    pc: dict,
    lagna: str,
    moon_transit: dict[str, Any],
    sun_transit: dict[str, Any],
    mercury_transit: dict[str, Any],
    tara: dict[str, Any],
    chandra: dict[str, Any],
    tone: str,
    moon_sav: int,
    moon_bav: int,
    moon_aus: bool,
    moon_inaus: bool,
    sun_aus: bool,
    sun_inaus: bool,
    merc_aus: bool,
    merc_inaus: bool,
    sav_line: str,
    bav_line: str,
    slow_notes: list[str],
) -> dict[str, Any]:
    name = (client or "You").strip().split()[0]
    vim = active_vimshottari(pc, target)
    jai = active_jaimini_chara(pc, target)
    md, ad, pd = vim["md"], vim["ad"], vim["pd"]
    jm, ja, jp = jai["maha"], jai["antar"], jai["pd"]
    moon_sign = moon_transit.get("sign", "")
    moon_h = int(moon_transit.get("house_from_moon", 1))
    theme = HOUSE_LIFE_THEME.get(moon_h, "today's focus")

    vim_pd_note = _planet_daily_note(pd, pc, lagna) if pd else ""
    vim_ad_note = _planet_daily_note(ad, pc, lagna) if ad else ""
    vim_md_note = VIM_MAHA_PLAIN.get(md, "")

    jai_pd_note = _sign_daily_note(jp, lagna) if jp else ""
    jai_ad_note = _sign_daily_note(ja, lagna) if ja else ""
    jai_md_note = JAIMINI_MAHA_PLAIN.get(jm, JAIMINI_SIGN_PLAIN.get(jm, ""))

    vim_stack = f"{md} mahadasha, {ad} antardasha"
    if pd:
        pd_end = _fmt_d(_parse_d(vim["pd_end"])) if vim.get("pd_end") else ""
        vim_stack += f", {pd} pratyantar until {pd_end}"

    jai_stack = ""
    if jm:
        jai_stack = f"{jm} Chara mahadasha, {ja} antardasha"
        if jp:
            jpd_end = _fmt_d(_parse_d(jai["pd_end"])) if jai.get("pd_end") else ""
            jai_stack += f", {jp} pratyantar until {jpd_end}"

    moon_lane = (
        f"Transit Moon in {moon_sign} ({moon_transit.get('nakshatra', '')}) "
        f"lights your {_ordinal(moon_h)} house from birth Moon ({theme}). "
        f"Tarabala: {tara.get('name', '')} ({tara.get('tone', '')}). "
        f"Chandrabal: {chandra.get('name', '')} ({chandra.get('tone', '')})."
    )

    gochar_bits: list[str] = []
    if moon_aus:
        gochar_bits.append("Moon gochar is supportive for emotional initiatives")
    elif moon_inaus:
        gochar_bits.append("Moon gochar is tense; keep emotional stakes modest")
    if sun_aus:
        gochar_bits.append("Sun gochar favours one visible task")
    elif sun_inaus:
        gochar_bits.append("Sun gochar presses authority moves; stay modest")
    if merc_aus:
        gochar_bits.append("Mercury gochar helps mail and study")
    elif merc_inaus:
        gochar_bits.append("Mercury gochar warns against rushed signatures")
    gochar_lane = "; ".join(gochar_bits) if gochar_bits else "Fast graha gochar is mixed."

    av_lane = f"Moon crosses a {moon_sav}-point sign (BAV {moon_bav}/8 for Moon)."

    vim_hits = _transit_hits_vim_lords(moon_sign, pc, (pd, ad, md))
    jai_hits = _transit_hits_chara_signs(moon_sign, (jp, ja, jm))
    period_lane = ""
    if vim_hits:
        period_lane = (
            f"Vimshottari trigger: Moon crosses natal {'/'.join(vim_hits)} "
            f"({'/'.join(vim_hits)} period lords)."
        )
    if jai_hits:
        jai_bit = (
            f"Jaimini trigger: Moon is in {moon_sign}, matching your running "
            f"{'/'.join(jai_hits)} Chara sign slice."
        )
        period_lane = f"{period_lane} {jai_bit}".strip()

    dual_agree = _dual_pd_agreement(pd, jp, pc)
    if moon_sign == jp and jp:
        dual_agree = (
            dual_agree or
            f"Strong dual-clock day: transit Moon in {jp} is also your Jaimini pratyantar sign."
        )

    gk = score_transit_dasha_synergy(md=md, ad=ad, pc=pc, target=target)
    ad_boney = dignity_crosscheck_for_lord(pc, ad) if ad else {"available": False}
    pd_boney = dignity_crosscheck_for_lord(pc, pd) if pd else {"available": False}
    karmic = is_karmic_dasha(md, ad)

    jaimini_conf = build_jaimini_daily_confluence(pc=pc, birth_lagna=lagna, jaimini=jai)

    gk_lane = "neutral"
    if gk.get("available"):
        if gk.get("supportive"):
            gk_lane = "Jupiter/Saturn trigger on MD/AD natal signs today"
        elif gk.get("dampened") or karmic:
            gk_lane = "transits active but karmic Saturn-Rahu dasha may mute benefit"
        elif gk.get("md_transit_hits") or gk.get("ad_transit_hits"):
            gk_lane = "; ".join(gk.get("md_transit_hits", []) + gk.get("ad_transit_hits", []))[:80]
        else:
            gk_lane = "dasha sets tone; no major slow-graha on MD/AD signs today"

    boney_lane = ""
    if ad_boney.get("available"):
        boney_lane = f"AD {ad}: {ad_boney.get('tier', 'neutral')}"
        if pd_boney.get("available") and pd != ad:
            boney_lane += f"; PD {pd}: {pd_boney.get('tier', 'neutral')}"

    verdict = _confluence_verdict(
        tone, pd, ad, moon_aus, moon_inaus, tara.get("tone", ""),
        jaimini_pd=jp, jaimini_ad=ja, moon_sign=moon_sign, vim_hits=vim_hits, jai_hits=jai_hits,
        gk_supportive=gk.get("supportive", False),
        karmic_dasha=karmic,
        ad_dignity_tier=ad_boney.get("tier", ""),
        jaimini_score=jaimini_conf.get("score", 0),
        jaimini_tone=jaimini_conf.get("tone", ""),
    )

    reading_technical_parts = [
        f"{name}, Vimshottari today: {vim_stack}. "
        f"Long chapter: {vim_md_note}. Antardasha: {vim_ad_note} "
        f"{'Pratyantar: ' + vim_pd_note if vim_pd_note else ''}",
    ]
    if jai_stack:
        reading_technical_parts.append(
            f"Jaimini Chara: {jai_stack}. "
            f"Chapter tone: {jai_md_note} Antardasha: {jai_ad_note} "
            f"{'Pratyantar sign-slice: ' + jai_pd_note if jai_pd_note else ''}"
        )
    if jaimini_conf.get("available") and jaimini_conf.get("reading"):
        reading_technical_parts.append(f"Jaimini karaka detail: {jaimini_conf['reading']}")
        if jaimini_conf.get("bav_summary"):
            reading_technical_parts.append(jaimini_conf["bav_summary"])
    reading_technical_parts.extend([moon_lane, f"{gochar_lane}. {av_lane}"])
    if period_lane:
        reading_technical_parts.append(period_lane)
    if gk.get("available") and gk.get("note"):
        reading_technical_parts.append(f"Transit+dasha: {gk['note']}")
    if karmic:
        reading_technical_parts.append(
            "Karmic Saturn-Rahu MD-AD - even good transits may feel muted."
        )
    if ad_boney.get("available") and ad_boney.get("note"):
        reading_technical_parts.append(f"Navamsha check on antardasha lord: {ad_boney['note']}")
    if dual_agree:
        reading_technical_parts.append(dual_agree)
    if slow_notes:
        reading_technical_parts.append(f"Slow-graha: {slow_notes[0]}")
    reading_technical_parts.append(f"Day verdict: {verdict}")

    plain = build_plain_daily_reading(
        name=name,
        md=md,
        ad=ad,
        pd=pd,
        pc=pc,
        lagna=lagna,
        moon_sign=moon_sign,
        moon_h=moon_h,
        tara=tara,
        chandra=chandra,
        moon_aus=moon_aus,
        moon_inaus=moon_inaus,
        sun_aus=sun_aus,
        sun_inaus=sun_inaus,
        merc_aus=merc_aus,
        merc_inaus=merc_inaus,
        jaimini_conf=jaimini_conf,
        gk=gk,
        karmic=karmic,
        ad_boney=ad_boney,
        vim_hits=vim_hits,
        jai_hits=jai_hits,
        dual_agree=dual_agree,
        slow_notes=slow_notes,
        verdict=verdict,
        jai_stack=jai_stack,
    )

    lanes = [
        {"lane": "Vimshottari", "signal": vim_stack, "weight": "high"},
        {"lane": "Moon transit", "signal": f"{moon_sign}, {_ordinal(moon_h)} from Moon", "weight": "high"},
        {"lane": "Tarabala", "signal": f"{tara.get('name', '')} ({tara.get('tone', '')})", "weight": "medium"},
        {"lane": "Chandrabal", "signal": f"{chandra.get('name', '')} ({chandra.get('tone', '')})", "weight": "medium"},
        {"lane": "Gochar", "signal": gochar_lane, "weight": "medium"},
        {"lane": "Ashtakavarga", "signal": f"SAV {moon_sav}, Moon BAV {moon_bav}", "weight": "medium"},
    ]
    if pd:
        lanes.insert(1, {"lane": "Vim pratyantar", "signal": f"{pd} until {vim.get('pd_end', '')}", "weight": "high"})
    if jai.get("stack"):
        lanes.insert(2 if pd else 1, {
            "lane": "Jaimini Chara",
            "signal": jai["stack"],
            "weight": "high",
        })
    for jl in jaimini_conf.get("lanes", []):
        lanes.insert(4 if pd else 3, jl)
    if jp:
        lanes.insert(3 if pd else 2, {
            "lane": "Jaimini pratyantar",
            "signal": f"{jp} until {jai.get('pd_end', '')}",
            "weight": "high",
        })
    if gk.get("available"):
        lanes.append({
            "lane": "GK transit+dasha",
            "signal": gk_lane,
            "weight": "high" if gk.get("supportive") else "medium",
        })
    if ad_boney.get("available"):
        lanes.append({
            "lane": "Boney D9 cross-check",
            "signal": boney_lane or ad_boney.get("note", "")[:100],
            "weight": "medium",
        })

    dasha_note = (
        f"Life timing: {vim_stack}. "
        f"Parallel track: {jai['stack'] or 'unavailable'}."
    )
    if jaimini_conf.get("highlights"):
        dasha_note += f" Strong karaka pulse: {', '.join(jaimini_conf['highlights'][:2])}."
    if gk.get("supportive"):
        dasha_note += " Sky and timing agree today."
    elif karmic:
        dasha_note += " Mixed sky - keep expectations modest."

    return {
        "reading": plain["reading"],
        "reading_paragraphs": plain["paragraphs"],
        "reading_technical": " ".join(reading_technical_parts),
        "verdict": verdict,
        "verdict_plain": plain["verdict_plain"],
        "work_hint": plain.get("work_hint", ""),
        "personal_hint": plain.get("personal_hint", ""),
        "lanes": lanes,
        "dasha": vim,
        "jaimini": jai,
        "dasha_note": dasha_note,
        "md_note": vim_md_note,
        "ad_note": vim_ad_note,
        "pd_note": vim_pd_note,
        "jaimini_pd_note": jai_pd_note,
        "jaimini_ad_note": jai_ad_note,
        "jaimini_md_note": jai_md_note,
        "dual_agreement": dual_agree,
        "gk": gk,
        "boney_ad": ad_boney,
        "boney_pd": pd_boney,
        "karmic_dasha": karmic,
        "jaimini_confluence": jaimini_conf,
        "sav_line": sav_line,
        "bav_line": bav_line,
    }


def _confluence_verdict(
    tone: str,
    pd: str,
    ad: str,
    moon_aus: bool,
    moon_inaus: bool,
    tara_tone: str,
    *,
    jaimini_pd: str = "",
    jaimini_ad: str = "",
    moon_sign: str = "",
    vim_hits: list[str] | None = None,
    jai_hits: list[str] | None = None,
    gk_supportive: bool = False,
    karmic_dasha: bool = False,
    ad_dignity_tier: str = "",
    jaimini_score: int = 0,
    jaimini_tone: str = "",
) -> str:
    score = 0
    if tone in ("bright", "mixed-positive"):
        score += 1
    if tone in ("sensitive", "mixed-caution"):
        score -= 1
    if moon_aus:
        score += 1
    if moon_inaus:
        score -= 1
    if tara_tone == "auspicious":
        score += 1
    elif tara_tone == "caution":
        score -= 1
    if pd in ("Jupiter", "Venus", "Moon", "Mercury"):
        score += 1
    if pd in ("Saturn", "Rahu", "Ketu") and ad in ("Ketu", "Saturn"):
        score -= 1
    if jaimini_pd in JAIMINI_PD_BOOST:
        score += 1
    if jaimini_pd in JAIMINI_PD_CAUTION:
        score -= 1
    if vim_hits:
        score += 1
    if jai_hits:
        score += 1
    if moon_sign and moon_sign == jaimini_pd:
        score += 1
    if gk_supportive:
        score += 1
    if karmic_dasha:
        score -= 1
    if ad_dignity_tier in ("strong_both", "upgrade"):
        score += 1
    elif ad_dignity_tier in ("weak_both", "downgrade"):
        score -= 1
    if jaimini_tone == "supportive":
        score += 1
    elif jaimini_tone == "caution":
        score -= 1
    elif jaimini_score >= 3:
        score += 1

    if score >= 3:
        return "supportive for steady progress when Vim and Jaimini clocks are respected - avoid rash launches."
    if score <= -2:
        return "thin for big bets; handle essentials, rest, and low-stakes tasks."
    return "mixed; use the morning for clarity work and keep the afternoon flexible."
