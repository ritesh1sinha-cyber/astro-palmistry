#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deep-dive answer block for the Main Question section.

Given a routed question (its domain + houses), this builds a detailed, plain-English
reading of the SPECIFIC life-area that pulls together every layer before answering:

  * the relevant divisional chart (D7 children, D9 marriage, D10 career, …) with a
    precise diagnosis of which part of that chart is strong or weak,
  * the natal houses + their lords and the natural significators,
  * the Ashtakavarga support of the house,
  * the dasha + transit CONFLUENCE (Vimshottari + Jaimini Chara + Yogini + Sa/Ju/Ma
    transit) over the next ~3 years,
  * the classical 108 predictive rules that actually touch this area,

and ends with a house-specific remedy (practice + charity + a chart-safe gemstone
note for the running dasha).

Reuses the scoring + diagnosis engine already built in final_user_report.py so the
Main Question answer is consistent with the Personal Reading.
"""
from __future__ import annotations

import datetime as _dt

from prediction108_report import _esc
from prediction108_rules import evaluate_all, hlord, phouse, pdig
from chart_summary_report import _varga_data, VARGA_GOV
from dasha_confluence_report import compute_windows, rate_field

from final_user_report import (
    _varga_diagnosis, _strength_of, _label, AREA_REMEDY, _gem_ctx, _gem_line,
    _confluence_now, _CONFLUENCE_LINE, _ord, _compose_rule_line, _classify_rule,
)

# domain → (varga code, field-key for diagnosis/remedy, plain area name, karakas)
_DEEP = {
    "children":  ("D7",  "children",   "children & progeny",        ["Jupiter"]),
    "marriage":  ("D9",  "spouse",     "marriage & your partner",   ["Venus", "Jupiter"]),
    "career":    ("D10", "profession", "career & profession",       ["Sun", "Saturn", "Mercury"]),
    "finance":   ("D2",  "wealth",     "wealth & finances",         ["Jupiter", "Venus"]),
    "health":    ("D30", "troubles",   "health & vitality",         ["Sun", "Mars", "Saturn"]),
    "education": ("D24", "education",  "education & learning",       ["Mercury", "Jupiter"]),
    "speech":    ("D1",  "self",       "speech & communication",    ["Mercury", "Jupiter"]),
    "legal":     ("D1",  "troubles",   "disputes & legal matters",  ["Mars", "Saturn"]),
    "property":  ("D4",  "home",       "home & property",           ["Mars", "Moon", "Venus"]),
    "travel":    ("D1",  "self",       "travel & relocation",       ["Rahu", "Mercury"]),
    "spiritual": ("D20", "spiritual",  "faith & inner growth",      ["Jupiter", "Ketu"]),
    "status":    ("D10", "profession", "status & recognition",      ["Sun", "Jupiter"]),
    "general":   ("D1",  "self",       "your overall life",         ["Sun"]),
}

# transit special-case name expected by dasha_confluence_report.rate_field
_RATE_NAME = {"marriage": "Marriage", "health": "Health", "spiritual": "Spirituality/Mind"}

# keywords to pick the 108 rules that touch this area
_DOMAIN_KW = {
    "children":  ["child", "children", "progeny", "5th", "fifth", "putra"],
    "marriage":  ["marri", "spouse", "wife", "husband", "partner", "7th", "seventh", "venus"],
    "career":    ["career", "profession", "job", "10th", "tenth", "status", "government", "civil service", "raj"],
    "finance":   ["wealth", "money", "rich", "income", "gain", "2nd", "11th", "second", "eleventh", "dhana"],
    "health":    ["health", "disease", "illness", "vital", "lifespan", "longevity", "6th", "8th", "sixth", "eighth"],
    "education": ["educat", "learn", "study", "intellig", "knowledge", "4th", "5th"],
    "speech":    ["speech", "2nd", "voice", "mercury"],
    "legal":     ["litig", "enemy", "enemies", "dispute", "debt", "6th", "8th"],
    "property":  ["home", "property", "house", "land", "vehicle", "4th", "mother"],
    "spiritual": ["spiritual", "moksha", "dharma", "12th", "9th", "ketu", "mind"],
    "status":    ["status", "fame", "authority", "power", "10th", "raj"],
}

_RATEWORD = {"fav": "favourable and opening up", "mix": "mixed — good and testing patches",
             "chal": "demanding patience and care"}
_VLABEL = {"strong": "strong and well-built", "mixed": "workable but mixed", "weak": "under strain"}


def _fmt(d):
    return d.strftime("%b %Y") if d else "—"


def _resolve(domain, primary_house):
    cfg = _DEEP.get(domain) or _DEEP["general"]
    varga, key, area, karakas = cfg
    return varga, key, area, karakas


def _house_facts(pc, houses, karakas):
    """Plain lord + karaka placements for the natal houses of this area."""
    out = []
    seen = set()
    for h in houses:
        L = hlord(pc, h)
        if not L or L in seen:
            continue
        seen.add(L)
        out.append(f"the {_ord(h)} house (its ruler {L} sits in the {_ord(phouse(pc, L))}, {pdig(pc, L) or 'neutral'})")
    for k in karakas:
        if k and k not in seen:
            seen.add(k)
            out.append(f"{k} (the natural significator) in the {_ord(phouse(pc, k))} ({pdig(pc, k) or 'neutral'})")
    return out


def _rules_for_domain(pc, domain, houses, limit=4):
    """108-rule HIT/PARTIALs that touch this area, as plain planet+house lines."""
    kws = list(_DOMAIN_KW.get(domain, []))
    kws += [f"{_ord(h)}" for h in houses]          # e.g. '7th'
    kws = [k.lower() for k in kws]
    pos, neg, seen = [], [], set()
    try:
        verdicts = evaluate_all(pc)
    except Exception:
        return [], []
    for v in verdicts:
        if v.verdict not in ("HIT", "PARTIAL"):
            continue
        blob = f"{v.title} {v.finding} {v.prediction}".lower()
        if not any(k in blob for k in kws):
            continue
        line = _compose_rule_line(v)
        if not line or len(line) < 20:
            continue
        sig = line[:45].lower()
        if sig in seen:
            continue
        seen.add(sig)
        pol = _classify_rule(v)
        (neg if pol == "neg" else pos).append(line)
    return pos[:limit], neg[:limit]


def _transit_note(pc, houses):
    try:
        from prediction108_transit import build_transit_context
        tx = build_transit_context(pc, on=_dt.date.today())
        pos = tx.get("positions", {}) or {}
    except Exception:
        return ""
    support, press = [], []
    for p in ("Jupiter", "Saturn", "Mars", "Rahu", "Ketu"):
        h = (pos.get(p, {}) or {}).get("house_natal", 0)
        if h in houses:
            if p == "Jupiter":
                support.append(f"Jupiter is transiting your {_ord(h)} house (a blessing on this area)")
            else:
                press.append(f"{p} is transiting your {_ord(h)} house")
    bits = []
    if support:
        bits.append("; ".join(support))
    if press:
        bits.append("pressure from " + ", ".join(press) + " — go steady and avoid haste")
    return ". ".join(bits)


def _near_term(pc, domain, key, varga, houses, karakas, lat, lon, tz):
    name = _RATE_NAME.get(domain, key.title())
    field = (name, key, varga, houses, karakas)
    try:
        windows, caches = compute_windows(pc, lat, lon, tz, years=3)
    except Exception:
        return [], None, None, {}
    cur_win = next((w for w in windows if w.get("is_now")), windows[0] if windows else None)
    rows = []
    cur_rating = None
    for w in windows[:5]:
        r = rate_field(pc, field, w, caches)
        if w.get("is_now") and cur_rating is None:
            cur_rating = r["rating"]
        rows.append({
            "period": f"{_fmt(w['row']['start'])} – {_fmt(w['row']['end'])}",
            "now": w.get("is_now"),
            "md": w["row"]["md"], "ad": w["row"]["ad"],
            "jai": w["ov"].get("chara_sign", ""), "yog": w["ov"].get("yogini", ""),
            "rating": r["rating"], "word": _RATEWORD[r["rating"]],
        })
    if cur_rating is None and rows:
        cur_rating = rows[0]["rating"]
    return rows, cur_rating, cur_win, caches


def _overall(varga_cls, house_label, npos, nneg, cur_rating, transit_press):
    score = 0.0
    score += {"strong": 1, "mixed": 0, "weak": -1}.get(varga_cls, 0)
    score += {"strong": 1, "mixed": 0, "weak": -1}.get(house_label, 0)
    score += 0.4 * (npos - nneg)
    score += {"fav": 1, "mix": 0, "chal": -1}.get(cur_rating, 0)
    if transit_press:
        score -= 0.4
    if score >= 1.0:
        return "fav", "Broadly favourable — the chart supports this area."
    if score <= -1.0:
        return "chal", "This area needs patience, effort and remedy — the chart flags real friction here."
    return "mix", "A mixed picture — workable with the right timing and steady effort."


def build_deepdive(pc, ctx, *, lat=None, lon=None, tz=None, gender=0):
    """Return an HTML section (string) for the question's house deep-dive."""
    domain = getattr(ctx, "domain", "general") or "general"
    primary_house = getattr(ctx, "primary_house", 0) or 0
    houses = list(getattr(ctx, "houses", []) or []) or [primary_house or 1]
    varga, key, area, karakas = _resolve(domain, primary_house)

    # 1) divisional chart strength + precise diagnosis
    vmeta = {c: (n, g) for c, n, g in VARGA_GOV}
    vname, vgov = vmeta.get(varga, (varga, ""))
    vd = _varga_data(pc, varga, vname, vgov) if varga != "D1" else None
    vcls = (vd or {}).get("vcls", "mixed")
    diag = _varga_diagnosis(pc, varga, key, karakas)

    # 2) natal house + karaka strength
    sc = _strength_of(pc, houses, karakas, {}, key=key)
    house_label = _label(sc)
    facts = _house_facts(pc, houses, karakas)

    # 3) the 108 rules touching this area
    pos, neg = _rules_for_domain(pc, domain, houses)

    # 4) dasha + transit confluence (Vim + Jaimini + Yogini + Sa/Ju/Ma)
    rows, cur_rating, cur_win, caches = _near_term(pc, domain, key, varga, houses, karakas, lat, lon, tz)
    try:
        conf_word = _confluence_now(pc, cur_win, caches) if cur_win else "mixed"
    except Exception:
        conf_word = "mixed"
    transit = _transit_note(pc, houses)

    # 5) overall verdict for this house
    overall, overall_txt = _overall(vcls, house_label, len(pos), len(neg), cur_rating or "mix", "pressure from" in transit)

    # 6) house-specific remedy + chart-safe gemstone for the running dasha
    deity = practice = dayw = charity = gem_planet = ""
    if key in AREA_REMEDY:
        deity, practice, dayw, charity, gem_planet = AREA_REMEDY[key]
    gem_line = ""
    try:
        gem_line = _gem_line(_gem_ctx(pc))
    except Exception:
        gem_line = ""

    # ── render ──────────────────────────────────────────────────────
    vcls_word = _VLABEL.get(vcls, vcls)
    pill = {"fav": "hi", "mix": "mid", "chal": "lo"}.get(overall, "mid")

    facts_html = "".join(f"<li>{_esc(f)}</li>" for f in facts) or "<li>—</li>"
    pos_html = "".join(f"<li>{_esc(s)}</li>" for s in pos)
    neg_html = "".join(f"<li>{_esc(s)}</li>" for s in neg)
    rules_block = ""
    if pos_html:
        rules_block += f"<p class='body'><strong>Classical rules in your favour:</strong></p><ul class='bullets'>{pos_html}</ul>"
    if neg_html:
        rules_block += f"<p class='body'><strong>Classical rules to be watchful about:</strong></p><ul class='bullets'>{neg_html}</ul>"
    if not rules_block:
        rules_block = "<p class='body'>No standout classical rule fires sharply on this area — it is governed mainly by the houses and dasha above.</p>"

    tl_rows = ""
    for r in rows:
        nowtag = " <strong>(now)</strong>" if r["now"] else ""
        extra = []
        if r["jai"]:
            extra.append(f"Jaimini {r['jai']}")
        if r["yog"]:
            extra.append(f"Yogini {r['yog']}")
        tl_rows += (f"<tr><td>{_esc(r['period'])}{nowtag}</td>"
                    f"<td>{_esc(r['md'])} → {_esc(r['ad'])}</td>"
                    f"<td>{_esc(', '.join(extra)) or '—'}</td>"
                    f"<td>{_esc(r['word'])}</td></tr>")
    tl_html = (f"<table class='tl'><thead><tr><th>Period</th><th>Dasha (Vim)</th>"
               f"<th>Jaimini / Yogini</th><th>Outlook for this area</th></tr></thead>"
               f"<tbody>{tl_rows or '<tr><td colspan=4>—</td></tr>'}</tbody></table>")

    diag_html = f"<p class='body'>{_esc(diag)}</p>" if diag else ""
    transit_html = f"<p class='body'><strong>Right now in the sky:</strong> {_esc(transit)}.</p>" if transit else ""
    conf_html = f"<p class='body'>{_CONFLUENCE_LINE.get(conf_word, '')}</p>"

    remedy_html = ""
    if practice:
        remedy_html = (
            f"<div class='card blue'><h3>Remedy for {_esc(area)}</h3>"
            f"<p class='body'>{_esc(practice)}; best done on <strong>{_esc(dayw)}</strong>. "
            f"You may also offer {_esc(charity)}, and keep faith in {_esc(deity)}.</p>"
            + (f"<p class='body'>{gem_line}</p>" if gem_line else "")
            + "</div>"
        )

    return f"""
<h2 class="section-h">Deep-Dive on Your Question — {_esc(area)}</h2>
<div class="card {'green' if overall=='fav' else 'amber' if overall=='mix' else 'red'}">
  <h3>{_esc(overall_txt)}</h3>
  <span class="pill {pill}">This area: {_esc(_VLABEL.get('strong' if overall=='fav' else 'weak' if overall=='chal' else 'mixed'))}</span>
  <p class="body" style="margin-top:10px"><strong>The {_esc(varga)} chart ({_esc(vname)} — {_esc(vgov)})</strong> that governs this
   question is <strong>{_esc(vcls_word)}</strong>. {diag_html}</p>
  <p class="body"><strong>In your birth chart</strong>, this area rests on {_esc('; '.join(facts))}. Overall it reads as
   <strong>{_esc(_VLABEL.get(house_label, house_label))}</strong>.</p>
</div>

<div class="card">
  <h4 style="margin:0 0 8px">When it moves — dasha &amp; transit confluence</h4>
  {conf_html}
  {tl_html}
  {transit_html}
</div>

<div class="card">
  <h4 style="margin:0 0 8px">What the classical rules say about this area</h4>
  {rules_block}
</div>
{remedy_html}
"""
