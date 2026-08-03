#!/usr/bin/env python3
"""
vedic_longevity_report.py — Deterministic Longevity & Life-Risk report (NO LLM).

Replaces the Cursor Longevity lane. Implements the maraka / Mrtyu Bhaga / Jaimini
longevity methodology (Marc Boney's *Lord Yama Pays a Visit* and *Inauspicious
Planetary Stations*, rules25/26) on top of ``astro_precompute``, which already
computes maraka lords, the full Mrtyu Bhaga scan, maraka mahadasha periods and a
longevity-span estimate.

EDUCATIONAL ONLY — this is not, and must never be read as, a death prediction.

Whole-sign houses are recomputed from sign + Lagna (the precompute's stored
``house`` field is unreliable for Saturn-ruled placements).

Fully offline and reproducible — no model, no network.
"""
from __future__ import annotations

import argparse
import html
from datetime import datetime, date
from pathlib import Path

from astro_precompute import resolve_precompute
from chart_resolve import add_chart_source_args, chart_kwargs_from_args
from longevity_analysis import (
    arista_assessment,
    check_mb,
    classify_ad_book,
    functional_killer,
    maraka_rank_note,
    methodology_html,
    primary_marakas,
    scan_mb_all,
)
from longevity_book_data import load_longevity_book

BASE_DIR = Path(__file__).resolve().parent

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = {"Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
             "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
             "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
             "Pisces": "Jupiter"}
SIGN_TYPE = {"Aries": "movable", "Cancer": "movable", "Libra": "movable", "Capricorn": "movable",
             "Taurus": "fixed", "Leo": "fixed", "Scorpio": "fixed", "Aquarius": "fixed",
             "Gemini": "dual", "Virgo": "dual", "Sagittarius": "dual", "Pisces": "dual"}
NATURAL_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
DIGNITY_WORD = {"exalted": "exalted", "moolatrikona": "moolatrikona", "own_sign": "own sign",
                "debilitated": "debilitated", "neutral_sign": "neutral",
                "friend_sign": "friend's sign", "enemy_sign": "enemy's sign",
                "great_friend_sign": "great friend's sign"}


def _e(s) -> str:
    return html.escape(str(s))


def _ord(n) -> str:
    n = int(n)
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th"))


def house_of(sign: str, lagna: str) -> int:
    return (SIGNS.index(sign) - SIGNS.index(lagna)) % 12 + 1


def _dms(deg: float) -> str:
    d = int(deg)
    m = int(round((deg - d) * 60))
    if m == 60:
        m = 0
        d += 1
    return f"{d}°{m:02d}'"


SPAN_YEARS = {
    "Short": "before 32 years (Parāśara band)",
    "Medium": "32–64 years",
    "Long": "64–100 years",
}


def jaimini_span(sa: str, sb: str) -> str:
    """Jaimini rāśi-pair longevity rule — Marc Boney / Jaimini Sūtras Ch.2 Pt.1 (rules26 OCR)."""
    ta, tb = SIGN_TYPE[sa], SIGN_TYPE[sb]
    pair = {ta, tb}
    if ta == tb:
        return {"movable": "Long", "fixed": "Short", "dual": "Medium"}[ta]
    if pair == {"movable", "fixed"}:
        return "Medium"
    if pair == {"movable", "dual"}:
        return "Short"
    if pair == {"fixed", "dual"}:
        return "Long"
    return "Medium"


def _house_sign(h: int, lagna: str) -> str:
    return SIGNS[(SIGNS.index(lagna) + h - 1) % 12]


def _eighth_sign_vriddha(lagna: str, lagna_lord: str, planets: dict) -> tuple[str, str]:
    """8th-house sign for Group I per Boney vriddha-kārikā table + Aries/Libra proviso."""
    ll_sign = planets[lagna_lord]["sign"]
    h8_std = _house_sign(8, lagna)
    if lagna in ("Aries", "Libra") and lagna_lord == SIGN_LORD[h8_std]:
        # Same planet owns lagna and 8th — take 8th from sign occupied by lagna lord.
        vk = _house_sign(8, ll_sign)
        return vk, f"vriddha-kārikā 8th from {lagna_lord} in {ll_sign} → {vk}"
    return h8_std, f"standard 8th from {lagna} → {h8_std}"


def _hora_lagna_sign(pc: dict) -> tuple[str | None, str]:
    """Parāśara hora lagna via PyJHora when birth coordinates exist in precompute."""
    meta = pc.get("meta", {})
    birth = pc.get("birth", {})
    raw = pc.get("raw_sections", {})
    lat = birth.get("latitude") or meta.get("latitude") or raw.get("latitude")
    lon = birth.get("longitude") or meta.get("longitude") or raw.get("longitude")
    tz = birth.get("timezone") or meta.get("timezone") or raw.get("timezone")
    tob = meta.get("birth_time") or birth.get("birth_time")
    dob = meta.get("dob")
    if lat is None or lon is None or tz is None or not tob or not dob:
        return None, "birth coordinates/time unavailable — Group III omitted"
    try:
        import sys
        pj_src = BASE_DIR / "pyjhora" / "src"
        if str(pj_src) not in sys.path:
            sys.path.insert(0, str(pj_src))
        from jhora.panchanga import drik
        from jhora import utils
        y, m, d = (int(x) for x in dob.split("-"))
        parts = [int(float(x)) for x in str(tob).split(":")]
        while len(parts) < 3:
            parts.append(0)
        jd = utils.julian_day_number((y, m, d), tuple(parts[:3]))
        place = drik.Place(meta.get("birth_place", "Birth"), float(lat), float(lon), float(tz))
        hl = drik.hora_lagna(jd, place)
        return SIGNS[int(hl[0])], "Parāśara hora lagna (PyJHora)"
    except Exception as exc:
        return None, f"hora lagna not computed ({exc})"


def synthesize_jaimini_span(
    g1: str, g2: str, g3: str | None, *, moon_house: int, lagna: str, moon_sign: str
) -> tuple[str, str]:
    """Combine three Jaimini groups per Boney tie-breakers."""
    groups = [g1, g2] + ([g3] if g3 else [])
    counts = {s: groups.count(s) for s in ("Short", "Medium", "Long")}
    winner = max(counts, key=lambda s: counts[s])
    if counts[winner] >= 2:
        note = f"Two or more groups agree on {winner} span."
        return winner, note
    if g3 and len(set(groups)) == 3:
        return g3, "All three groups differ — Boney: take Group III (lagna + hora lagna)."
    if moon_house in (1, 7):
        return g2, f"Moon in the {_ord(moon_house)} house — Boney: take Group II (lagna + Moon)."
    if g3:
        return g3, "Groups disagree — default to Group III when hora lagna is available."
    return g2, "Groups disagree and hora lagna unavailable — provisional Group II (lagna + Moon)."


def jaimini_longevity_block(lg: "Longevity") -> dict:
    """Full Jaimini three-group longevity assessment."""
    ll_sign = lg.planets[lg.lagna_lord]["sign"]
    h8_sign, h8_note = _eighth_sign_vriddha(lg.lagna, lg.lagna_lord, lg.planets)
    h8_lord = lg.lord_of[8]
    # For display: if vk 8th sign differs from lord's natal sign, show the reckoned sign.
    g1_b_sign = h8_sign if lg.lagna in ("Aries", "Libra") and lg.lagna_lord == h8_lord else lg.planets[h8_lord]["sign"]
    g1 = jaimini_span(ll_sign, g1_b_sign)
    g2 = jaimini_span(lg.lagna, lg.planets["Moon"]["sign"])
    hl_sign, hl_src = _hora_lagna_sign(lg.pc)
    g3 = jaimini_span(lg.lagna, hl_sign) if hl_sign else None
    final, synth_note = synthesize_jaimini_span(
        g1, g2, g3, moon_house=lg.planets["Moon"]["house"], lagna=lg.lagna,
        moon_sign=lg.planets["Moon"]["sign"],
    )
    band = f"{final} ({SPAN_YEARS[final]})"
    return {
        "g1": g1, "g2": g2, "g3": g3,
        "g1_b_sign": g1_b_sign, "h8_note": h8_note,
        "hl_sign": hl_sign, "hl_src": hl_src,
        "final": final, "band": band, "synth_note": synth_note,
    }


class Longevity:
    def __init__(self, pc: dict, dob: date):
        self.pc = pc
        self.book = load_longevity_book()
        self.dob = dob
        self.lagna = pc["meta"]["lagna_sign"]
        self.lagna_idx = SIGNS.index(self.lagna)
        self.name = pc["meta"]["client"]
        self.age = int(pc["meta"]["age"])
        self.lagna_lord = pc["meta"]["lagna_lord"]
        self.L = pc["longevity"]
        self.planets = {}
        for nm, v in pc["planets"].items():
            self.planets[nm] = {"sign": v["sign"], "degree": v.get("degree_in_sign", 0.0),
                                "nakshatra": v.get("nakshatra", ""), "pada": v.get("pada", ""),
                                "dignity": v.get("dignity", "neutral_sign"),
                                "functional": v.get("functional_status", "neutral"),
                                "house": house_of(v["sign"], self.lagna)}
        self.house_sign = {h: SIGNS[(self.lagna_idx + h - 1) % 12] for h in range(1, 13)}
        self.lord_of = {h: SIGN_LORD[self.house_sign[h]] for h in range(1, 13)}
        m1, m2 = primary_marakas(self.book, self.lagna)
        self.maraka_lords = {m1, m2}
        self.mb_rows = scan_mb_all(
            self.book, self.planets, self.lagna, float(pc["meta"].get("lagna_degree", 0))
        )
        self.mb = {r["planet"]: r for r in self.mb_rows if r["planet"] != "Lagna"}

    def role(self, p: str) -> str:
        tags = []
        if p == self.lagna_lord:
            tags.append("Lagna lord")
        houses_ruled = [h for h in range(1, 13) if self.lord_of[h] == p]
        if 2 in houses_ruled or 7 in houses_ruled:
            mk = "2nd lord" if 2 in houses_ruled else "7th lord"
            tags.append(f"PRIMARY MARAKA ({mk})")
        if p in self.book.get("unqualified_marakas", []):
            tags.append("unqualified maraka")
        mbinfo = self.mb.get(p)
        if mbinfo and mbinfo.get("status") == "IN MB":
            tags.append("IN Mrtyu Bhaga")
        elif mbinfo and mbinfo.get("status") == "Near MB":
            tags.append("Near Mrtyu Bhaga")
        fn = self.planets[p]["functional"]
        if fn == "functional_malefic":
            tags.append("functional malefic")
        elif fn == "functional_benefic":
            tags.append("functional benefic")
        return " · ".join(tags) if tags else "neutral"

    def maraka_md_periods(self):
        return self.L.get("maraka_md_periods", [])

    def classify_ad(self, ad_lord: str, md_lord: str) -> tuple[str, str, str]:
        cls, mb_status, risk, _ = classify_ad_book(self, ad_lord, md_lord, self.book, self.mb_rows)
        return cls, mb_status, risk


# ───────────────────────────── render ─────────────────────────────


def _css() -> str:
    return """
:root { --ink:#1a1a2e; --muted:#5a6270; --border:#d8dce3; --red:#b71c1c; --amber:#e65100; --green:#2e7d32; --blue:#1565c0; }
body { font-family: Georgia, 'Times New Roman', serif; color: var(--ink); max-width: 1020px; margin: auto; padding: 1.5rem; line-height: 1.55; }
h1,h2,h3 { font-weight: 600; }
table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: .92rem; }
td, th { border: 1px solid var(--border); padding: .45rem .55rem; vertical-align: top; }
th { background: #f4f6f8; }
.hl-red { background: #ffebee; } .hl-amber { background: #fff8e1; } .hl-green { background: #e8f5e9; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: .78rem; font-weight: 600; }
.badge-red { background: #ffcdd2; color: var(--red); } .badge-amber { background: #ffe0b2; color: var(--amber); }
.badge-green { background: #c8e6c9; color: var(--green); } .badge-blue { background: #bbdefb; color: var(--blue); }
.callout { border-left: 4px solid #90a4ae; padding: 10px 14px; margin: 12px 0; border-radius: 6px; background: #f8f9fa; }
.callout.red { border-color: var(--red); background: #fff5f5; } .callout.amber { border-color: var(--amber); background: #fffaf0; }
.callout.blue { border-color: var(--blue); background: #f0f7ff; } .callout.green { border-color: var(--green); background: #f1f8f4; }
.disclaimer { background: #fff3e0; border: 1px solid #ffcc80; padding: 14px 18px; border-radius: 8px; margin-bottom: 20px; }
.lead-box { background: #f5f5f5; padding: 14px 18px; border-radius: 8px; margin: 18px 0; }
.meta span { display: inline-block; margin-right: 14px; font-size: .88rem; color: var(--muted); }
.fine { font-size: .86rem; color: var(--muted); } .sub-note { font-size: .84rem; color: var(--muted); margin-top: 8px; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.footer { margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--border); font-size: .84rem; color: var(--muted); }
"""


_BADGE = {"Highest": "badge-red", "High": "badge-red", "Moderate": "badge-amber", "Low": "badge-green"}
_ROW = {"Highest": "hl-red", "High": "hl-amber", "Moderate": "", "Low": "hl-green"}


def _chart_essentials(lg: Longevity) -> str:
    order = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    rows = [f"<tr><td>ASC (Lagna)</td><td>{lg.lagna}</td><td>{_dms(lg.pc['meta']['lagna_degree']%30)}</td>"
            f"<td>{_ord(1)}</td><td>{lg.pc['meta']['lagna_nakshatra']}</td><td>Identity, body, vitality</td></tr>"]
    for p in order:
        v = lg.planets[p]
        mbinfo = lg.mb.get(p)
        cls = ""
        if mbinfo and mbinfo.get("status") == "IN MB":
            cls = ' class="hl-red"'
        rows.append(
            f"<tr{cls}><td>{p}</td><td>{v['sign']}</td><td>{_dms(v['degree'])}</td>"
            f"<td>{_ord(v['house'])}</td><td>{v['nakshatra']} Pada {v['pada']}</td><td>{lg.role(p)}</td></tr>")
    return ("<table><thead><tr><th>Planet</th><th>Sign</th><th>Degree</th><th>House</th>"
            "<th>Naksatra</th><th>Role</th></tr></thead><tbody class='planet-row'>"
            + "".join(rows) + "</tbody></table>")


def _mb_table(lg: Longevity) -> str:
    rows = []
    for r in lg.mb_rows:
        p = r["planet"]
        if p == "Lagna":
            continue
        diff = r.get("diff")
        if r["status"] == "IN MB":
            badge, cls, status = "badge-red", "hl-red", "IN MB"
        elif r["status"] == "Near MB":
            badge, cls, status = "badge-amber", "hl-amber", "Near MB"
        else:
            badge, cls, status = "badge-green", "", "Clear"
        impact = (
            f"{p} at {r.get('natal_degree', '?')} in {r['sign']}; MB={r.get('mb')} "
            f"(orb {r.get('orb_minutes', '?')} min); distance {r.get('diff_minutes', '?')} min. "
        )
        if r["status"] == "IN MB":
            impact += f"Book: {p} periods need extra care. Role: {lg.role(p)}."
        elif r["status"] == "Near MB":
            impact += "Outside strict book orb but within near-MB zone."
        else:
            impact += "Outside book near-MB range."
        rows.append(
            f"<tr class='{cls}'><td><strong>{p}</strong></td><td>{r['sign']}</td>"
            f"<td>{r.get('natal_degree', '')}</td><td>{r.get('mb', '')}</td>"
            f"<td>{r.get('diff_minutes', '')} min</td>"
            f"<td><span class='badge {badge}'>{status}</span></td><td>{impact}</td></tr>"
        )
    lag = next((x for x in lg.mb_rows if x["planet"] == "Lagna"), None)
    if lag:
        rows.insert(0,
            f"<tr><td><strong>Lagna</strong></td><td>{lag['sign']}</td>"
            f"<td>{_dms(lg.pc['meta']['lagna_degree']%30)}</td><td>{lag.get('mb','')}</td>"
            f"<td>{lag.get('diff_minutes','')} min</td>"
            f"<td><span class='badge {'badge-red' if lag['status']=='IN MB' else 'badge-green'}'>"
            f"{lag['status']}</span></td><td>Ascendant degree vs book MB for {lag['sign']}.</td></tr>"
        )
    return ("<table><thead><tr><th>Planet</th><th>Sign</th><th>Natal deg</th><th>MB deg</th>"
            "<th>Distance</th><th>Status</th><th>Impact</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


def _maraka_table(lg: Longevity) -> str:
    m1 = lg.L["maraka_1"]
    m2 = lg.L["maraka_2"]
    rows = [
        f"<tr class='hl-red'><td><strong>1st</strong></td><td>{m1['lord']}</td><td>2nd lord (strongest killer)</td>"
        f"<td>{m1['lord_sign']} · {_ord(lg.planets[m1['lord']]['house'])} house</td>"
        f"<td><span class='badge badge-red'>HIGHEST</span>{' — IN Mrtyu Bhaga' if lg.mb.get(m1['lord'],{}).get('status')=='IN MB' else ''}</td></tr>",
        f"<tr class='hl-amber'><td><strong>2nd</strong></td><td>{m2['lord']}</td><td>7th lord</td>"
        f"<td>{m2['lord_sign']} · {_ord(lg.planets[m2['lord']]['house'])} house "
        f"({DIGNITY_WORD.get(m2['lord_dignity'],'')})</td>"
        f"<td><span class='badge badge-amber'>HIGH</span></td></tr>",
    ]
    return ("<table><thead><tr><th>Rank</th><th>Planet</th><th>Qualification</th><th>Placement</th>"
            "<th>Strength as Maraka</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>")


def _arista_html(lg: Longevity) -> str:
    prot, risk, level = arista_assessment(lg, lg.mb_rows, lg.book)
    prot_rows = "".join(f"<tr><td>{p}</td></tr>" for p in prot) or "<tr><td>No strong protective factors flagged.</td></tr>"
    risk_rows = "".join(f"<tr><td>{p}</td></tr>" for p in risk) or "<tr><td>No major static risk factors flagged.</td></tr>"
    return (
        '<section class="section"><h2>Arista (Natal Risk) Assessment</h2>'
        f'<p class="fine">{maraka_rank_note(lg.book)}</p>'
        '<div class="grid2"><table><thead><tr><th>Protective factors</th></tr></thead><tbody>'
        + prot_rows + '</tbody></table><table><thead><tr><th>Risk factors</th></tr></thead><tbody>'
        + risk_rows + f'</tbody></table></div>'
        f'<div class="callout amber"><strong>Arista level: {level}.</strong> '
        'High arista plus maraka antardasha = heightened health-awareness; '
        'protective lagna/AK factors mitigate extreme readings.</div></section>'
    )


def _dasha_table(lg: Longevity) -> str:
    md = lg.pc["vimshottari"]["current_md"]
    md_lord = md["md_lord"]
    rows = []
    for a in lg.pc["vimshottari"]["current_md_antardashas"]:
        adl = a["ad_lord"]
        cls, mb_status, risk, theme = classify_ad_book(lg, adl, md_lord, lg.book, lg.mb_rows)
        sy, ey = a["start"][:4], a["end"][:4]
        sage = int(sy) - lg.dob.year
        eage = int(ey) - lg.dob.year
        cur = ' class="' + (_ROW[risk] or "") + '"'
        bold = ("<strong>", "</strong>") if risk in ("Highest", "High") else ("", "")
        rows.append(
            f"<tr{cur}><td>{bold[0]}{md_lord[:3]}–{adl[:3]}{bold[1]}</td>"
            f"<td>{a['start']} – {a['end']}</td><td>{sage}–{eage}</td><td>{cls}</td>"
            f"<td>{mb_status}</td><td><span class='badge {_BADGE[risk]}'>{risk}</span></td><td>{theme}</td></tr>")
    return ("<table><thead><tr><th>Antardasa</th><th>Period</th><th>Age</th><th>Maraka class</th>"
            "<th>MB status</th><th>Risk</th><th>Theme</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


def render(lg: Longevity, dob_disp: str, tob: str, place: str) -> str:
    nm = _e(lg.name)
    crit = [r["planet"] for r in lg.mb_rows if r.get("status") == "IN MB" and r["planet"] != "Lagna"]
    crit_txt = ", ".join(crit) if crit else "none in strict book MB orb"
    fk = functional_killer(lg.book, lg.lagna)
    md = lg.pc["vimshottari"]["current_md"]
    md_lord = md["md_lord"]
    md_is_maraka = md_lord in lg.maraka_lords
    m1, m2 = primary_marakas(lg.book, lg.lagna)
    if md_is_maraka:
        md_maraka_lead = "(a primary maraka by lordship)"
    else:
        md_maraka_lead = (
            f"(<strong>{m1}</strong> is the primary maraka planet for {lg.lagna} lagna; "
            f"current mahadasha lord <strong>{md_lord}</strong> is not the maraka lord)"
        )

    remedy_rows = ""
    if md_is_maraka:
        remedy_rows += (
            f"<tr><td>{md_lord} (maraka mahadasha lord)</td><td>Strengthen via weekday discipline, "
            f"charity, and mantra; heightened health-awareness for this full mahadasha.</td></tr>"
        )
    else:
        remedy_rows += (
            f"<tr><td>{md_lord} (current mahadasha — not maraka lord)</td><td>General upaya for the "
            f"running mahadasha; maraka risk peaks in <strong>{m1}</strong> antardasha bands below.</td></tr>"
        )
        for pl in sorted(lg.maraka_lords):
            remedy_rows += (
                f"<tr><td>{pl} (primary maraka planet)</td><td>Mantra, charity, and preventive care — "
                f"especially during {pl} antardasha within any mahadasha.</td></tr>"
            )
    remedy_rows += "".join(
        f"<tr><td>{p} (in/near MB)</td><td>Weekday upaya and preventive health care during its antardasa.</td></tr>"
        for p in crit
    )

    # Jaimini groups (Marc Boney Ch.2 — rules26 OCR)
    jai = jaimini_longevity_block(lg)
    span = jai["band"]
    g3_row = ""
    if jai["hl_sign"]:
        g3_row = (
            f"<tr><td>Group III</td><td>Lagna — {lg.lagna} ({SIGN_TYPE[lg.lagna]})</td>"
            f"<td>Hora lagna — {jai['hl_sign']} ({SIGN_TYPE[jai['hl_sign']]}) "
            f"<span class='sub-note'>({jai['hl_src']})</span></td>"
            f"<td>{SIGN_TYPE[lg.lagna].title()} + {SIGN_TYPE[jai['hl_sign']].title()}</td>"
            f"<td><span class='badge badge-blue'>{jai['g3']}</span></td></tr>"
        )
    else:
        g3_row = (
            f"<tr><td>Group III</td><td colspan='4' class='sub-note'>{jai['hl_src']}</td></tr>"
        )
    lived_note = (
        f"The native has completed {lg.age} years — past the Parāśara short band (&lt;32), "
        f"so lived life already excludes a strict short-span reading."
        if lg.age >= 32 and jai["final"] != "Short"
        else f"The native has completed {lg.age} years."
    )

    unq = " and ".join(lg.book.get("unqualified_marakas", ["Saturn", "Rahu"]))
    body = f"""
<div class="page">
<div class="uncal-banner" style="background:#fff8e1;border-left:4px solid #f9a825;padding:12px 18px;margin-bottom:22px;border-radius:8px;font-size:.9rem;line-height:1.55;">
<strong>⚠ Uncalibrated — first pass.</strong> No dated life events were supplied. Predictions follow standard book methodology; treat timelines as provisional.
</div>
<div class="report-header">
  <h1>Longevity &amp; Life-Risk Period Analysis</h1>
  <div class="subtitle">Maraka Planets · Mrtyu Bhaga · Jaimini Longevity Span — deterministic rule engine (no LLM)</div>
  <div class="meta">
    <span>Native: {nm}</span>
    <span>DOB: {_e(dob_disp)}{(' · ' + _e(tob)) if tob else ''}{(' · ' + _e(place)) if place else ''}</span>
    <span>Lagna: {lg.lagna} {_dms(lg.pc['meta']['lagna_degree']%30)}</span>
    <span>Current Age: {lg.age} · Report Date: {date.today().strftime('%d %B %Y').lstrip('0')}</span>
  </div>
</div>

<div class="disclaimer">
  <strong>⚠ EDUCATIONAL PURPOSE ONLY — NOT A DEATH PREDICTION</strong>
  <p>This analysis follows Marc Boney's <em>Lord Yama Pays a Visit</em> and <em>Inauspicious Planetary Stations</em>.
  The techniques identify karmic life themes and periods of heightened challenge — they are <strong>not</strong>
  predictive of the date, timing, or manner of death for any living person.</p>
</div>

<div class="lead-box">
  <p><strong>Key findings:</strong> the Mrtyu Bhaga scan flags <strong>{crit_txt}</strong> at a sensitive degree.
  Combined with the currently running <strong>{md_lord} mahadasha</strong>
  {md_maraka_lead}, the coming years carry a heightened
  "transformation" signature. The arista (protective) factors below indicate these are periods of restructuring
  and health-awareness, not forecasts of crisis. Vigilance and remedies are appropriate.</p>
</div>

{methodology_html()}

<section class="section">
  <h2>Chart Essentials — Planetary Positions</h2>
  {_chart_essentials(lg)}
  <div class="sub-note">Whole-sign houses from {lg.lagna} Lagna, recomputed from sign + Lagna.</div>
</section>

<section class="section">
  <h2>Primary Maraka Identification — {lg.lagna} Lagna</h2>
  <div class="callout red"><strong>Maraka rule:</strong> the lords of the 2nd ({lg.house_sign[2]} → {lg.lord_of[2]})
  and 7th ({lg.house_sign[7]} → {lg.lord_of[7]}) houses are the primary marakas. {unq} act as
  unqualified marakas independent of placement (Boney OCR).</div>
  {_maraka_table(lg)}
  <div class="callout amber"><strong>Parashara per-lagna note:</strong> {_e(fk)}</div>
</section>

{_arista_html(lg)}

<section class="section">
  <h2>Jaimini Longevity Span (indicative)</h2>
  <div class="callout blue"><strong>Caveat (Marc Boney):</strong> even broad span determination is "rather a
  quagmire" — multiple scholarly interpretations exist. The result below is indicative, not definitive.</div>
  <table>
    <thead><tr><th>Group</th><th>Factor (a)</th><th>Factor (b)</th><th>Sign types</th><th>Span</th></tr></thead>
    <tbody>
      <tr><td>Group I</td><td>Lagna lord {lg.lagna_lord} — {lg.planets[lg.lagna_lord]['sign']}
      ({SIGN_TYPE[lg.planets[lg.lagna_lord]['sign']]})</td>
      <td>8th reckoning — {jai['g1_b_sign']} ({SIGN_TYPE[jai['g1_b_sign']]});
      lord {lg.lord_of[8]} natal {lg.planets[lg.lord_of[8]]['sign']}
      <span class='sub-note'>({jai['h8_note']})</span></td>
      <td>{SIGN_TYPE[lg.planets[lg.lagna_lord]['sign']].title()} + {SIGN_TYPE[jai['g1_b_sign']].title()}</td>
      <td><span class="badge badge-blue">{jai['g1']}</span></td></tr>
      <tr><td>Group II</td><td>Lagna — {lg.lagna} ({SIGN_TYPE[lg.lagna]})</td>
      <td>Moon — {lg.planets['Moon']['sign']} ({SIGN_TYPE[lg.planets['Moon']['sign']]})</td>
      <td>{SIGN_TYPE[lg.lagna].title()} + {SIGN_TYPE[lg.planets['Moon']['sign']].title()}</td>
      <td><span class="badge badge-blue">{jai['g2']}</span></td></tr>
      {g3_row}
    </tbody>
  </table>
  <div class="callout green"><strong>Jaimini synthesis:</strong> {jai['synth_note']}
  <strong>Computed span estimate: {span}.</strong> {lived_note}</div>
</section>

<section class="section">
  <h2>Mrtyu Bhaga Scan — Book Orbs (Boney 2021)</h2>
  <p style="font-size:.9rem;color:var(--muted);margin-bottom:14px;">
  MB degrees from Marc Boney table (Lahiri). Orbs: Lagna 1 degree; Sun/Moon/Mercury 40 minutes;
  Mars/Jupiter/Saturn/Rahu/Ketu 30 minutes. Near MB = within 1 degree outside strict orb.
  {f' OCR could not resolve {len(lg.book.get("mb_table_gaps", []))} table cells (garbled PDF scan) — those pairs show n/a, not invented values.' if lg.book.get('mb_table_gaps') else ''}</p>
  {_mb_table(lg)}
</section>

<section class="section">
  <h2>Vimsottari Dasha Sequence — Maraka Classification</h2>
  <p style="font-size:.9rem;color:var(--muted);margin-bottom:14px;">Current mahadasha: {md_lord}
  ({md['start']} – {md['end']}).
  {'Because ' + md_lord + ' is a primary maraka lord, the whole mahadasha is a heightened backdrop — each antardasa quality depends on its lord.' if md_is_maraka else 'Primary maraka for this lagna is ' + m1 + ' (2nd/7th lord) — watch Venus antardasha rows below, not the mahadasha lord label alone.'}</p>
  {_dasha_table(lg)}
</section>

<section class="section">
  <h2>Remedies (Upaya) — Classical Recommendations</h2>
  <div class="callout blue"><strong>Primary Upaya — Maha-Mrtyunjaya Mantra:</strong> the classical remedy for
  maraka periods and MB activations; daily recitation during sensitive dasha periods.</div>
  <table>
    <thead><tr><th colspan="2">Planet-specific upaya</th></tr></thead>
    <tbody>
      {remedy_rows}
    </tbody>
  </table>
</section>

<section class="section">
  <h2>Multi-System Confluence Note</h2>
  <p>Cross-check the highest-risk antardasa windows above with the Vimsottari, Ashtakavarga, RTVD and Yogini lanes.
  Where several systems flag the same window, treat it as the highest-priority period for preventive health action.</p>
</section>

<div class="footer">
  <p><strong>EDUCATIONAL PURPOSE ONLY</strong> — Marc Boney maraka + Mrityu Bhaga books (OCR corpus).
  No statement herein constitutes a prediction of death or its timing. Deterministic rule engine — no LLM.</p>
  <p style="margin-top:8px;color:#aaa;">Generated {date.today().strftime('%d %B %Y').lstrip('0')} · Native: {nm} ·
  Lagna: {lg.lagna} · Current: {md_lord} mahadasha</p>
</div>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Longevity &amp; Life-Risk Periods — {nm}</title>
<style>{_css()}</style></head><body>{body}</body></html>"""


def generate_longevity_html(
    client_name: str,
    dob: str,
    *,
    extracted_path: str | None = None,
    tob: str = "",
    place: str = "",
    precomputed_path: str | None = None,
    birth_time: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone: float | None = None,
    gender: int | None = None,
) -> tuple[str, dict]:
    pc = resolve_precompute(
        client_name, dob,
        extracted_path=extracted_path,
        precomputed_path=precomputed_path,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        place_name=place,
        gender=gender,
    )
    d = datetime.strptime(dob, "%Y-%m-%d").date()
    lg = Longevity(pc, d)
    jai = jaimini_longevity_block(lg)
    doc = render(lg, d.strftime("%d %B %Y").lstrip('0'), tob, place)
    summary = {"lagna": lg.lagna, "maraka_lords": sorted(lg.maraka_lords),
               "critical_mb": [r["planet"] for r in lg.mb_rows if r.get("status") == "IN MB"],
               "span": jai["band"], "jaimini": jai}
    return doc, summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Deterministic Longevity report (no LLM)")
    ap.add_argument("name")
    ap.add_argument("dob")
    ap.add_argument("extracted", nargs="?", default=None, help="Optional legacy AstroSage extract")
    add_chart_source_args(ap)
    ap.add_argument("--tob", default="")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    kw = chart_kwargs_from_args(args)
    doc, summary = generate_longevity_html(
        args.name, args.dob,
        extracted_path=args.extracted,
        tob=args.tob, place=args.place or kw.get("place_name", ""),
        precomputed_path=kw.get("precomputed_path"),
        birth_time=kw.get("birth_time"),
        latitude=kw.get("latitude"),
        longitude=kw.get("longitude"),
        timezone=kw.get("timezone"),
        gender=kw.get("gender"),
    )
    out = Path(args.out) if args.out else BASE_DIR / "reports" / f"Vedic_Longevity_{args.name}_preview.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(f"maraka={summary['maraka_lords']} critical_mb={summary['critical_mb']} span={summary['span']}")
    print(f"written → {out}")


if __name__ == "__main__":
    main()
