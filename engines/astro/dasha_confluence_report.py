#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dasha + Transit CONFLUENCE timeline.

A forward-looking forecast matrix where:
  * Vimshottari Mahadasha → Antardasha give the date divisions (the rows).
  * Each window is overlaid with the Jaimini Chara sign-dasha, the Yogini
    period and the Saturn / Jupiter transit active at that time.
  * For each of 9 life-fields the verdict (favourable / mixed / challenging)
    is reasoned from the confluence of:
        - the strength of the active dasha lords (planet table)
        - the houses they rule / occupy (house table)
        - the relevant divisional-chart strength (D10 career, D9 marriage, …)
        - the 108 predictive rules that touch that field
        - the current transit of Saturn & Jupiter over the window.

Output: a single matrix HTML report (same theme as the other summaries) plus
optional per-antardasha detail pages.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

from chart_summary_report import (
    _house_data, _planet_data, _varga_data, VARGA_GOV,
)
from prediction108_report import _css, _esc
from chart_summary_report import _hero, _doc
from prediction108_rules import (
    PLANETS, NAT_BENEFIC, NAT_MALEFIC, hlord, phouse, lagna, psign,
)
from prediction108_transit import build_transit_context
from astro_precompute import SIGN_LORDS

BASE_DIR = Path(__file__).resolve().parent

VIM_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
VIM_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
             "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
DAYS_YR = 365.25

# field → (divisional chart, significator houses, fixed karaka planets)
FIELDS = [
    ("Career",        "Career",   "D10", [10, 6, 11], ["Sun", "Saturn", "Mercury", "Jupiter"]),
    ("Wealth",        "Wealth",   "D2",  [2, 11, 9],  ["Jupiter", "Venus"]),
    ("Marriage",      "Marriage", "D9",  [7, 2, 11],  ["Venus", "Jupiter"]),
    ("Health",        "Health",   "D30", [1, 6, 8],   ["Sun", "Mars"]),
    ("Children",      "Children", "D7",  [5, 9],      ["Jupiter"]),
    ("Education",     "Educ.",    "D24", [4, 5, 2],   ["Mercury", "Jupiter"]),
    ("Property/Home", "Home",     "D4",  [4, 2],      ["Mars", "Moon", "Venus"]),
    ("Travel/Foreign","Travel",   None,  [3, 9, 12],  ["Rahu", "Mercury"]),
    ("Spirituality/Mind", "Spirit", "D20", [12, 9, 5], ["Ketu", "Jupiter", "Moon"]),
]

VNUM = {"strong": 1.0, "mixed": 0.0, "weak": -1.0}
TONE_OK = {"auspicious", "benefic", "good"}

EXTRA_CSS = """
.scrollx{overflow-x:auto;border:1px solid var(--line);border-radius:12px;margin-top:8px}
table.matrix{min-width:1180px;font-size:13px}
table.matrix th,table.matrix td{padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top}
table.matrix thead th{position:sticky;top:0;background:#0d1019;z-index:2}
td.period{white-space:nowrap;font-weight:600}
td.period .now{display:inline-block;font-size:10px;color:#0f1117;background:var(--hit);
  border-radius:5px;padding:1px 6px;margin-left:6px;font-weight:700}
td.active{font-size:12px;line-height:1.45;color:var(--mut);white-space:nowrap}
td.active b{color:var(--ink)}
td.fld{text-align:center;font-weight:800;cursor:help;font-size:14px;min-width:46px}
.cell-fav{background:#10301f;color:var(--hit)}
.cell-mix{background:#2a2410;color:var(--partial)}
.cell-chal{background:#2a1418;color:#ff8a8a}
.conf{white-space:nowrap}
.conf .bar{display:inline-block;font-size:11px;color:var(--mut)}
.legend{display:flex;flex-wrap:wrap;gap:14px;margin:14px 0 4px;font-size:13px;color:var(--mut)}
.legend span b{color:var(--ink)}
.glyph-fav{color:var(--hit)} .glyph-mix{color:var(--partial)} .glyph-chal{color:#ff8a8a}
.fieldkey{color:var(--mut);font-size:12.5px;margin:6px 0 0}
"""

GLYPH = {"fav": "▲", "mix": "◆", "chal": "▼"}
CELLCLS = {"fav": "cell-fav", "mix": "cell-mix", "chal": "cell-chal"}


# ── date helpers ────────────────────────────────────────────────────
def _d(s):
    try:
        return _dt.date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def _add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(year=d.year + n, day=28)


def _fmt(d):
    return d.strftime("%b %Y") if d else "—"


# ── 1. Vimshottari antardashas across the window ────────────────────
def _vimsottari_antardashas(pc, win_start, win_end):
    seq = (pc.get("vimshottari", {}) or {}).get("sequence", []) or []
    rows = []
    for md in seq:
        lord = md.get("md_lord")
        ms = _d(md.get("start"))
        me = _d(md.get("end"))
        yrs = float(md.get("md_years") or 0)
        if not (lord and ms and me) or lord not in VIM_YEARS:
            continue
        if me < win_start or ms > win_end:
            continue
        order = VIM_ORDER[VIM_ORDER.index(lord):] + VIM_ORDER[:VIM_ORDER.index(lord)]
        cur = ms
        for ad in order:
            dur = _dt.timedelta(days=yrs * (VIM_YEARS[ad] / 120.0) * DAYS_YR)
            ad_s, ad_e = cur, cur + dur
            cur = ad_e
            if ad_e < win_start or ad_s > win_end:
                continue
            rows.append({"md": lord, "ad": ad, "start": ad_s, "end": ad_e})
    rows.sort(key=lambda r: r["start"])
    return rows


# ── 2. confluence overlays (chara, yogini, transit) ─────────────────
def _chara_at(pc, mid):
    for m in (pc.get("chara_dasha", {}) or {}).get("maha", []) or []:
        s, e = _d(m.get("start")), _d(m.get("end"))
        if s and e and s <= mid < e and s != e:
            sign = m.get("sign", "")
            return sign, SIGN_LORDS.get(sign, "")
    return "", ""


def _yogini_cycle(pc, win_end):
    cyc = (pc.get("yogini", {}) or {}).get("full_cycle", []) or []
    if not cyc:
        return []
    # template of (yogini, lord, years, tone) in cycle order
    tmpl, seen = [], set()
    for y in cyc:
        nm = y.get("yogini")
        if nm and nm not in seen:
            seen.add(nm)
            tmpl.append((nm, y.get("lord", ""), float(y.get("years") or 0), y.get("tone", "")))
    start = _d(cyc[0].get("start"))
    if not tmpl or not start:
        return []
    out, cur, i = [], start, 0
    guard = 0
    while cur <= win_end and guard < 400:
        nm, lord, yy, tone = tmpl[i % len(tmpl)]
        e = cur + _dt.timedelta(days=yy * DAYS_YR)
        out.append({"yogini": nm, "lord": lord, "tone": tone, "start": cur, "end": e})
        cur = e
        i += 1
        guard += 1
    return out


def _yogini_at(cyc, mid):
    for y in cyc:
        if y["start"] <= mid < y["end"]:
            return y
    return None


def _transit_at(pc, mid, _cache):
    key = (mid.year, mid.month)
    if key in _cache:
        return _cache[key]
    try:
        tx = build_transit_context(pc, on=mid)
        pos = tx.get("positions", {})
        out = {
            "sa_sign": pos.get("Saturn", {}).get("sign", ""),
            "sa_house": pos.get("Saturn", {}).get("house_natal", 0),
            "sa_moon": pos.get("Saturn", {}).get("from_moon", 0),
            "ju_sign": pos.get("Jupiter", {}).get("sign", ""),
            "ju_house": pos.get("Jupiter", {}).get("house_natal", 0),
            "ju_moon": pos.get("Jupiter", {}).get("from_moon", 0),
        }
    except Exception:
        out = {}
    _cache[key] = out
    return out


# ── 3. scoring ──────────────────────────────────────────────────────
def _planet_quality(pc, L, cache):
    if not L:
        return 0.0
    if L not in cache:
        try:
            d = _planet_data(pc, L)
            q = VNUM.get(d["vcls"], 0.0)
        except Exception:
            q = 0.0
        if L in NAT_BENEFIC:
            q += 0.3
        if L in NAT_MALEFIC:
            q -= 0.2
        cache[L] = max(-1.2, min(1.3, q))
    return cache[L]


def _house_num(pc, h, cache):
    if h not in cache:
        try:
            cache[h] = VNUM.get(_house_data(pc, h)["vcls"], 0.0)
        except Exception:
            cache[h] = 0.0
    return cache[h]


def _varga_num(pc, code, cache):
    if not code:
        return None
    if code not in cache:
        meta = {c: (n, g) for c, n, g in VARGA_GOV}
        try:
            n, g = meta.get(code, (code, ""))
            d = _varga_data(pc, code, n, g)
            cache[code] = VNUM.get(d["vcls"], 0.0) if d else 0.0
        except Exception:
            cache[code] = 0.0
    return cache[code]


def _field_base(pc, field, caches):
    _, _, varga, houses, karakas = field
    parts = []
    hs = [_house_num(pc, h, caches["h"]) for h in houses]
    if hs:
        parts.append(sum(hs) / len(hs))
    kk = list(karakas) + [hlord(pc, houses[0])]
    ks = [_planet_quality(pc, k, caches["p"]) for k in kk if k]
    if ks:
        parts.append(sum(ks) / len(ks))
    vv = _varga_num(pc, varga, caches["v"])
    if vv is not None:
        parts.append(vv)
    return sum(parts) / len(parts) if parts else 0.0


def _conn_w(pc, L, field):
    """How strongly planet L is tied to a field: rules/sits the primary house (1.0),
    touches a secondary field house (0.7), or is only a generic karaka (0.5)."""
    if not L:
        return 0.0
    houses, karakas = field[3], field[4]
    primary = houses[0]
    if hlord(pc, primary) == L or phouse(pc, L) == primary:
        return 1.0
    if any(hlord(pc, h) == L for h in houses) or phouse(pc, L) in houses:
        return 0.7
    if L in karakas:
        return 0.5
    return 0.0


def _field_activation(pc, field, row, ov, caches):
    name, houses = field[0], field[3]
    act = 0.0
    for L, w in ((row["md"], 1.0), (row["ad"], 1.0),
                 (ov["chara_lord"], 0.5), (ov["yogini_lord"], 0.4)):
        cw = _conn_w(pc, L, field)
        if cw:
            act += w * cw * _planet_quality(pc, L, caches["p"])
    act /= 1.6  # soft-normalise the four weighted contributors
    act += 0.15 if ov["yogini_tone"] in TONE_OK else -0.15
    tr = ov["transit"]
    if tr.get("ju_house") in houses:
        act += 0.4
    if tr.get("sa_house") in houses and name in ("Health", "Marriage", "Spirituality/Mind"):
        act -= 0.3
    if name in ("Health", "Spirituality/Mind") and tr.get("sa_moon") in (12, 1, 2):
        act -= 0.3  # Sade Sati weighs on mind/health
    return act


def _rate(score):
    if score >= 0.32:
        return "fav"
    if score <= -0.4:
        return "chal"
    return "mix"


def _cell_reason(pc, field, row, ov, base, act, rating, caches):
    name = field[0]
    houses = field[3]
    bits = []
    drivers = []
    for L, lab in ((row["md"], "Maha"), (row["ad"], "Antar"),
                   (ov["chara_lord"], "Chara"), (ov["yogini_lord"], "Yogini")):
        if L and _conn_w(pc, L, field) > 0:
            q = _planet_quality(pc, L, caches["p"])
            drivers.append(f"{lab}-lord {L} ({'supports' if q > 0 else 'strains' if q < 0 else 'touches'})")
    if drivers:
        bits.append("; ".join(drivers))
    else:
        bits.append("no period-lord directly rules this area")
    tr = ov["transit"]
    if tr.get("ju_house") in houses:
        bits.append(f"Jupiter transits the {tr['ju_house']}th (boost)")
    if tr.get("sa_house") in houses and name in ("Health", "Marriage", "Spirituality/Mind"):
        bits.append(f"Saturn transits the {tr['sa_house']}th (pressure)")
    verdict = {"fav": "Favourable", "mix": "Mixed", "chal": "Challenging"}[rating]
    return f"{name} — {verdict}. " + "; ".join(bits) + "."


# ── window + overlay computation (reusable) ─────────────────────────
def compute_windows(pc, lat=None, lon=None, tz=None, years=10):
    """Return (windows, caches). Each window = {row, ov, mid, is_now}."""
    if lat is not None and lon is not None:
        pc.setdefault("meta", {})["_coords"] = {
            "latitude": lat, "longitude": lon, "timezone": 5.5 if tz is None else tz}
    today = _dt.date.today()
    win_end = _add_years(today, years)
    ads = _vimsottari_antardashas(pc, today, win_end)
    yog_cycle = _yogini_cycle(pc, win_end)
    tcache = {}
    caches = {"p": {}, "h": {}, "v": {}}
    windows = []
    for r in ads:
        mid = r["start"] + (r["end"] - r["start"]) / 2
        if mid < today:
            mid = today + (r["end"] - today) / 2
        chara_sign, chara_lord = _chara_at(pc, mid)
        yg = _yogini_at(yog_cycle, mid)
        ov = {
            "chara_sign": chara_sign, "chara_lord": chara_lord,
            "yogini": (yg or {}).get("yogini", ""), "yogini_lord": (yg or {}).get("lord", ""),
            "yogini_tone": (yg or {}).get("tone", ""),
            "transit": _transit_at(pc, mid, tcache),
        }
        windows.append({"row": r, "ov": ov, "mid": mid,
                        "is_now": r["start"] <= today < r["end"]})
    return windows, caches


def rate_field(pc, field, win, caches):
    """Rate one field tuple for one window. Returns dict rating/reason/score."""
    r, ov = win["row"], win["ov"]
    base = _field_base(pc, field, caches)
    act = _field_activation(pc, field, r, ov, caches)
    score = 0.6 * base + 0.6 * act
    rating = _rate(score)
    return {"rating": rating, "score": score,
            "reason": _cell_reason(pc, field, r, ov, base, act, rating, caches)}


def _build_rows(pc, lat=None, lon=None, tz=None, years=10):
    windows, caches = compute_windows(pc, lat, lon, tz, years)
    rows = []
    for w in windows:
        cells = [rate_field(pc, field, w, caches) for field in FIELDS]
        rows.append({
            "row": w["row"], "ov": w["ov"], "cells": cells,
            "is_now": w["is_now"],
            "conf": _row_confluence(pc, w["row"], w["ov"], caches),
        })
    return rows


def _row_confluence(pc, r, ov, caches):
    vim = (_planet_quality(pc, r["md"], caches["p"]) + _planet_quality(pc, r["ad"], caches["p"])) / 2
    jai = _planet_quality(pc, ov["chara_lord"], caches["p"]) if ov["chara_lord"] else 0.0
    yog = 0.5 if ov["yogini_tone"] in TONE_OK else -0.5
    tr = ov["transit"]
    trv = 0.0
    if tr.get("ju_moon") in (2, 5, 7, 9, 11):
        trv += 0.5
    elif tr.get("ju_moon") in (6, 8, 12):
        trv -= 0.3
    if tr.get("sa_moon") in (3, 6, 11):
        trv += 0.4
    elif tr.get("sa_moon") in (1, 2, 12, 4, 8):
        trv -= 0.4
    parts = [vim, jai, yog, trv]
    favours = sum(1 for x in parts if x > 0.1)
    overall = sum(parts) / len(parts)
    rating = "fav" if overall >= 0.25 else "chal" if overall <= -0.25 else "mix"
    return {"rating": rating, "favours": favours, "total": len(parts), "score": overall}


# ── render ──────────────────────────────────────────────────────────
def build_html(pc, client_name="Client", lat=None, lon=None, tz=None, years=10):
    meta, lg = pc.get("meta", {}), lagna(pc)
    rows = _build_rows(pc, lat, lon, tz, years)

    head_fields = "".join(
        f"<th class='fld' title='{_esc(full)} · chart {varga or '—'}'>{_esc(short)}</th>"
        for full, short, varga, _h, _k in FIELDS
    )
    body_rows = []
    for R in rows:
        r, ov, conf = R["row"], R["ov"], R["conf"]
        period = (f"{_fmt(r['start'])} – {_fmt(r['end'])}"
                  + ("<span class='now'>now</span>" if R["is_now"] else ""))
        active = (f"<b>Vim:</b> {_esc(r['md'])} → {_esc(r['ad'])}<br>"
                  f"<b>Jai:</b> {_esc(ov['chara_sign'] or '—')} ({_esc(ov['chara_lord'] or '—')})<br>"
                  f"<b>Yog:</b> {_esc(ov['yogini'] or '—')} {'⊕' if ov['yogini_tone'] in TONE_OK else '⊖'}")
        tr = ov["transit"]
        transit = (f"Sa {_esc(tr.get('sa_sign','—'))} ({tr.get('sa_house','?')}H)<br>"
                   f"Ju {_esc(tr.get('ju_sign','—'))} ({tr.get('ju_house','?')}H)") if tr else "—"
        cbadge = (f"<span class='v {('hit' if conf['rating']=='fav' else 'partial' if conf['rating']=='mix' else 'weak')}'>"
                  f"{GLYPH[conf['rating']]} {conf['favours']}/{conf['total']}</span>")
        cells = "".join(
            f"<td class='fld {CELLCLS[c['rating']]}' title='{_esc(c['reason'])}'>{GLYPH[c['rating']]}</td>"
            for c in R["cells"]
        )
        body_rows.append(
            f"<tr><td class='period'>{period}</td><td class='active'>{active}</td>"
            f"<td class='active'>{transit}</td><td class='conf'>{cbadge}</td>{cells}</tr>")

    legend = ("<div class='legend'>"
              "<span><b class='glyph-fav'>▲</b> favourable</span>"
              "<span><b class='glyph-mix'>◆</b> mixed</span>"
              "<span><b class='glyph-chal'>▼</b> challenging</span>"
              "<span>Hover any cell for the reasoning.</span></div>")
    fieldkey = "<p class='fieldkey'>Fields: " + " · ".join(
        f"<b>{_esc(s)}</b>={_esc(f)}" for f, s, _v, _h, _k in FIELDS) + "</p>"

    body = (
        _hero(client_name, lg, meta,
              "Dasha &amp; Transit Confluence — life forecast timeline",
              "Each window is one Vimshottari antardasha. Vimshottari, Jaimini Chara and Yogini "
              "dashas plus the Saturn/Jupiter transit are read together, and every life-field is "
              "rated from the confluence of your planet, house, divisional-chart and 108-rule strengths.")
        + legend + fieldkey
        + "<div class='scrollx'><table class='matrix'><thead><tr>"
          "<th>Period</th><th>Active dashas</th><th>Transit (mid)</th><th>Confluence</th>"
        + head_fields + "</tr></thead><tbody>" + "\n".join(body_rows) + "</tbody></table></div>"
        + "<div class='note'><b>How to read this:</b> the date rows come from your Vimshottari "
          "antardashas. For every window the three dasha systems and the live Saturn/Jupiter transit "
          "are combined; a field turns green when the active period-lords are strong and connect to "
          "that area (and benefic transit supports it), amber when signals are mixed, red when the "
          "rulers are weak/afflicted or malefic transit presses the area. Timing is indicative — use "
          "the confluence column to see how many systems agree.</div>"
    )
    return _doc(f"Dasha Confluence Timeline — {_esc(client_name)}", body), rows


def build_doc(pc, client_name="Client", lat=None, lon=None, tz=None, years=10):
    html, rows = build_html(pc, client_name, lat, lon, tz, years)
    html = html.replace("</style>", EXTRA_CSS + "</style>", 1)  # inject matrix CSS
    return html, rows


# ── granular per-antardasha detail pages ────────────────────────────
def write_details(pc, rows, out_dir, client_name="Client"):
    out_dir.mkdir(parents=True, exist_ok=True)
    meta, lg = pc.get("meta", {}), lagna(pc)
    written = []
    for R in rows:
        r, ov, conf = R["row"], R["ov"], R["conf"]
        items = "".join(
            f"<div class='card {('' if c['rating']=='fav' else 'partial')}'>"
            f"<div class='top'><span class='title'>{GLYPH[c['rating']]} {_esc(FIELDS[i][0])}</span></div>"
            f"<div class='pred'>{_esc(c['reason'])}</div></div>"
            for i, c in enumerate(R["cells"]))
        body = (
            _hero(client_name, lg, meta,
                  f"{_esc(r['md'])} → {_esc(r['ad'])} · {_fmt(r['start'])}–{_fmt(r['end'])}",
                  f"Confluence {conf['favours']}/{conf['total']} systems favour this window. "
                  f"Jaimini {_esc(ov['chara_sign'] or '—')}, Yogini {_esc(ov['yogini'] or '—')}.")
            + "<h2>What to expect, field by field</h2><div class='cards'>" + items + "</div>")
        doc = _doc(f"{r['md']}-{r['ad']} {_fmt(r['start'])} — {_esc(client_name)}", body)
        doc = doc.replace("</style>", EXTRA_CSS + "</style>", 1)
        fn = out_dir / f"Dasha_{r['start'].isoformat()}_{r['md']}-{r['ad']}_{client_name}.html"
        fn.write_text(doc, encoding="utf-8")
        written.append(fn)
    return written


def write_report(pc, out_dir, client_name="Client", lat=None, lon=None, tz=None):
    out_dir.mkdir(parents=True, exist_ok=True)
    html, rows = build_doc(pc, client_name, lat, lon, tz)
    try:
        from client_report_html import finalize_report_html
        html = finalize_report_html(html, client_name)
    except ImportError:
        pass
    out = out_dir / f"Dasha_Confluence_{client_name}.html"
    out.write_text(html, encoding="utf-8")
    return out, rows


if __name__ == "__main__":
    import argparse
    from astro_chart_bridge import compute_chart

    ap = argparse.ArgumentParser(description="Dasha + transit confluence timeline")
    ap.add_argument("--name", default="Sample")
    ap.add_argument("--dob", default="1990-01-15")
    ap.add_argument("--time", default="12:00")
    ap.add_argument("--place", default="New Delhi, India")
    ap.add_argument("--lat", type=float, default=28.6139)
    ap.add_argument("--lon", type=float, default=77.2090)
    ap.add_argument("--tz", type=float, default=5.5)
    ap.add_argument("-o", "--out", default="")
    args = ap.parse_args()

    pc = compute_chart(client_name=args.name, dob=args.dob, birth_time=args.time,
                       place=args.place, latitude=args.lat, longitude=args.lon, timezone=args.tz)
    out_dir = Path(args.out) if args.out else (BASE_DIR / "reports" / args.name)
    path, rows = write_report(pc, out_dir, args.name, args.lat, args.lon, args.tz)
    det = write_details(pc, rows, out_dir / "details", args.name)
    print(f"Wrote {path}  ({len(rows)} antardasha rows, {len(det)} detail pages)")
