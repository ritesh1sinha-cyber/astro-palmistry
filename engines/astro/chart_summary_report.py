#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Client-specific *summary tables* for the three pillars of a horoscope:

  1. The 12 Houses (bhavas)        – sign, lord & its placement, occupants, strength
  2. The 9 Planets (grahas)        – sign/house, dignity, functional role, strength
  3. The 20 Divisional charts (D1-D60) – governing area, lagna, lagna-lord, varga strength

Each table is computed **independently** from the precomputed chart (`pc`) and rendered
in the same colour-coded style as the 108-rule verdict table: green = strong / well
supported, amber = mixed, red = weak / afflicted.
"""
from __future__ import annotations

import html as _htmllib
import re
from pathlib import Path

from prediction108_report import _css, _esc
from prediction108_rules import (
    DUSTHANA, NAT_BENEFIC, NAT_MALEFIC, PLANETS,
    _ord, _dig_word, occupants, hlord, psign, phouse, pdig, pdeg,
    pnak, navsign, pretro, afflicted, lagna, evaluate_all,
)
from astro_precompute import SIGNS, SIGN_LORDS, sign_index, get_dignity, house_sign

BASE_DIR = Path(__file__).resolve().parent

GOOD_HOUSES = {1, 4, 5, 7, 9, 10}      # kendra + trikona

HOUSE_SIG = {
    1: "Self · body · personality · vitality",
    2: "Wealth · family · speech · food",
    3: "Courage · siblings · effort · communication",
    4: "Home · mother · property · inner peace",
    5: "Children · intelligence · romance · creativity",
    6: "Health · enemies · debts · daily work",
    7: "Marriage · partnerships · business",
    8: "Longevity · upheavals · inheritance · secrets",
    9: "Luck · father · dharma · higher learning",
    10: "Career · status · authority · karma",
    11: "Gains · income · friends · fulfilment",
    12: "Losses · expenses · foreign lands · liberation",
}

PLANET_KARAKA = {
    "Sun": "Soul · father · authority · vitality",
    "Moon": "Mind · mother · emotions · public",
    "Mars": "Energy · siblings · courage · property",
    "Mercury": "Intellect · speech · trade · learning",
    "Jupiter": "Wisdom · wealth · children · guru",
    "Venus": "Love · marriage · luxury · arts",
    "Saturn": "Discipline · longevity · career · sorrow",
    "Rahu": "Ambition · foreign · obsession · the unconventional",
    "Ketu": "Detachment · spirituality · past karma",
}

# 20 vargas: D1 (rasi) + the 19 stored divisionals
VARGA_GOV = [
    ("D1", "Rasi", "Body & overall life — the foundation chart"),
    ("D2", "Hora", "Wealth & financial prosperity"),
    ("D3", "Drekkana", "Siblings, courage & initiative"),
    ("D4", "Chaturthamsha", "Property, home, fortune & happiness"),
    ("D5", "Panchamsha", "Faith, worship & chosen deity (viveka)"),
    ("D6", "Shashthamsha", "Health vulnerabilities, disease & enemies"),
    ("D7", "Saptamsha", "Children & progeny"),
    ("D8", "Ashtamsha", "Sudden events, accidents & longevity"),
    ("D9", "Navamsha", "Marriage, dharma & overall strength (key chart)"),
    ("D10", "Dashamsha", "Career, profession & status"),
    ("D11", "Ekadashamsha", "Gains, income & fulfilment of desires"),
    ("D12", "Dwadashamsha", "Parents & ancestry"),
    ("D16", "Shodashamsha", "Vehicles, luxuries & comforts"),
    ("D20", "Vimshamsha", "Spiritual progress & worship"),
    ("D24", "Chaturvimshamsha", "Education & learning"),
    ("D27", "Bhamsha", "Innate strengths & weaknesses"),
    ("D30", "Trimshamsha", "Misfortunes, evils & character flaws"),
    ("D40", "Khavedamsha", "Maternal lineage & auspicious effects"),
    ("D45", "Akshavedamsha", "Paternal lineage & overall character"),
    ("D60", "Shashtiamsha", "Past-life karma & fine overall results (key chart)"),
]

EXTRA_CSS = """
tr.row-weak{background:#2a1418}
.v.weak{color:#ff8a8a} .v.strong{color:var(--hit)} .v.mixed{color:var(--partial)}
.t.weak .n{color:#ff8a8a}
.cell-note{font-size:13.5px}
.sub-h{color:var(--mut);font-size:13px;margin:-8px 0 14px}
"""


# ── scoring helpers ─────────────────────────────────────────────────
def _dig_score(d: str) -> float:
    return {"exalted": 2, "moolatrikona": 2, "own_sign": 2, "friendly_sign": 1,
            "neutral_sign": 0, "enemy_sign": -1, "debilitated": -2}.get(d, 0)


def _verdict(score: float):
    if score >= 2:
        return ("strong", "✓ Strong")
    if score <= -1:
        return ("weak", "△ Weak / afflicted")
    return ("mixed", "◐ Mixed")


_ROWCLS = {"strong": "row-hit", "mixed": "row-partial", "weak": "row-weak"}


def _house_kind(h: int) -> str:
    if h in (1, 4, 7, 10):
        return "kendra"
    if h in (1, 5, 9):
        return "trikona"
    if h in DUSTHANA:
        return "dusthana"
    if h in (3, 11):
        return "upachaya"
    return ""


def _tally(cells):
    return f"""<div class="tally">
    <div class="t strong"><div class="n">{cells.get('strong',0)}</div><div class="l">Strong</div></div>
    <div class="t partial"><div class="n">{cells.get('mixed',0)}</div><div class="l">Mixed</div></div>
    <div class="t weak"><div class="n">{cells.get('weak',0)}</div><div class="l">Weak / afflicted</div></div>
  </div>"""


# ── TABLE 1 · 12 houses ─────────────────────────────────────────────
# Natural significator (bhava karaka) of each house and what it governs.
BHAVA_KARAKA = {
    1: ("Sun", "vitality"), 2: ("Jupiter", "wealth"), 3: ("Mars", "courage"),
    4: ("Moon", "home & mother"), 5: ("Jupiter", "children"), 6: ("Saturn", "resilience"),
    7: ("Venus", "marriage"), 8: ("Saturn", "longevity"), 9: ("Jupiter", "fortune"),
    10: ("Sun", "career"), 11: ("Jupiter", "gains"), 12: ("Saturn", "liberation"),
}
_NODES = {"Rahu", "Ketu"}
# node placement that classically hurts a key signification
_NODE_FLAG = {4: "home life & peace of mind", 5: "progeny (children)", 7: "marriage & partnership",
              2: "family & savings", 9: "fortune & faith", 11: "fulfilment of desires"}

_NEG_KW = ("debilit", "afflict", "malefic", "weak", " loss", "delay", "obstacl", "difficult",
           "enemy", "combust", "maraka", "dusthana", "dushthana", "sorrow", "disease", "hurdle",
           "suffer", "deny", "denied", "harm", "stress", "pressure", "problem", "fear", "trik",
           "papa", "wound", "separat", "broken")
_POS_KW = ("exalt", "own sign", "own-sign", "moolatrikona", "moolatrik", "strong", "benefic",
           "raj yoga", "rajayoga", "dignif", "protect", "gain", "support", "prosper", "success",
           "fortune", "blessing", "auspicious", "well placed", "well-placed", "vipreet", "vipareet",
           "boost", "favour", "favor")


def _sav_house(pc, h):
    av = pc.get("ashtakavarga", {}) or {}
    sav = av.get("sav") or []
    if len(sav) != 12 or not lagna(pc):
        return None
    try:
        return int(sav[sign_index(house_sign(h, lagna(pc)))])
    except Exception:
        return None


def _rule_polarity(low: str) -> int:
    pos = sum(1 for k in _POS_KW if k in low)
    neg = sum(1 for k in _NEG_KW if k in low)
    if pos > neg:
        return 1
    if neg > pos:
        return -1
    return 0


def _mentions_house(low: str, h: int) -> bool:
    return bool(re.search(rf"\b{_ord(h).lower()}\b", low)) or f"house {h}" in low


def _house_rule_signals(pc):
    """Per-house tally of HIT/PARTIAL 108-rule verdicts that touch that house."""
    cache = pc.get("_house_rule_sig")
    if cache is not None:
        return cache
    sig = {h: {"pos": 0, "neg": 0, "lines": []} for h in range(1, 13)}
    try:
        verdicts = evaluate_all(pc)
    except Exception:
        verdicts = []
    for v in verdicts:
        if getattr(v, "verdict", "") not in ("HIT", "PARTIAL"):
            continue
        low = f"{getattr(v,'title','')} {getattr(v,'finding','')} {getattr(v,'prediction','')}".lower()
        pol = _rule_polarity(low)
        if pol == 0:
            continue
        for h in range(1, 13):
            if _mentions_house(low, h):
                sig[h]["pos" if pol > 0 else "neg"] += 1
                if len(sig[h]["lines"]) < 2:
                    sig[h]["lines"].append((pol, getattr(v, "title", "")))
    pc["_house_rule_sig"] = sig
    return sig


# ── confluence rollup ───────────────────────────────────────────────
#  The three summary tables are NOT a separate scoring engine — each row's
#  verdict + reading is pulled straight from that item's *detailed* confluence
#  report (house_confluence_report / planet_confluence_report /
#  divisional_confluence_report). Summary and drill-down therefore always agree.
#  The factual columns (sign, lord, occupants…) are plain chart facts and are
#  identical either way.

def _house_vcls(pct, pos, cau):
    """Mirror house_confluence_report._verdict_word, mapped to a colour class."""
    if pct >= 70 and pos > cau:
        return ("strong", "✓ Strong & well supported")
    if pct >= 55:
        return ("mixed", "◐ Broadly favourable")
    if pct >= 40:
        return ("mixed", "◐ Mixed")
    return ("weak", "△ Needs strengthening")


def _planet_vcls(score):
    """Mirror planet_confluence_report._strength_label, mapped to a colour class."""
    if score >= 75:
        return ("strong", "✓ Strong")
    if score >= 58:
        return ("strong", "✓ Moderately strong")
    if score >= 42:
        return ("mixed", "◐ Average")
    if score >= 28:
        return ("weak", "△ Below average")
    return ("weak", "△ Weak — needs support")


def _varga_vcls(pct):
    if pct >= 60:
        return ("strong", "✓ Strong")
    if pct >= 45:
        return ("mixed", "◐ Mixed")
    return ("weak", "△ Weak / afflicted")


def _plain(s):
    """Strip any HTML tags/entities so a confluence lead is safe in a table cell."""
    s = re.sub(r"<[^>]+>", "", s or "")
    return _htmllib.unescape(s).strip()


def _conf_cache(pc):
    c = pc.get("_conf_rollup")
    if c is None:
        c = {}
        pc["_conf_rollup"] = c
    return c


def _house_items(pc, name="Client"):
    c = _conf_cache(pc)
    if "houses" not in c:
        try:
            from house_confluence_report import generate_house_confluence_html
        except Exception:
            generate_house_confluence_html = None
        out = {}
        for h in range(1, 13):
            html, s = "", {}
            if generate_house_confluence_html is not None:
                try:
                    html, s = generate_house_confluence_html(pc, h, name)
                except Exception:
                    html, s = "", {}
            pct = int(round(s.get("confluence_pct", 50)))
            pos, cau = s.get("positive", 0), s.get("caution", 0)
            vcls, vlabel = _house_vcls(pct, pos, cau)
            out[h] = {"pct": pct, "pos": pos, "cau": cau, "neu": s.get("neutral", 0),
                      "conf": s.get("confidence", ""), "vcls": vcls, "vlabel": vlabel,
                      "word": s.get("verdict_word", vlabel),
                      "lead": s.get("lead") or s.get("detail") or "", "html": html}
        c["houses"] = out
    return c["houses"]


def _planet_items(pc, name="Client"):
    c = _conf_cache(pc)
    if "planets" not in c:
        try:
            from planet_confluence_report import generate_planet_confluence_html
        except Exception:
            generate_planet_confluence_html = None
        out = {}
        for p in PLANETS:
            html, s = "", {}
            if generate_planet_confluence_html is not None:
                try:
                    html, s = generate_planet_confluence_html(pc, p, name)
                except Exception:
                    html, s = "", {}
            score = int(round(s.get("strength_score", 50)))
            vcls, vlabel = _planet_vcls(score)
            out[p] = {"pct": int(round(s.get("confluence_pct", 50))), "score": score,
                      "conf": s.get("confidence", ""), "vcls": vcls, "vlabel": vlabel,
                      "word": s.get("verdict_word", vlabel),
                      "lead": s.get("lead", ""), "html": html}
        c["planets"] = out
    return c["planets"]


def _varga_items(pc, name="Client"):
    c = _conf_cache(pc)
    if "varga" not in c:
        try:
            from divisional_confluence_report import generate_divisional_confluence_html
        except Exception:
            generate_divisional_confluence_html = None
        out = {}
        for code, vname, gov in VARGA_GOV:
            html, s = "", {}
            if generate_divisional_confluence_html is not None:
                try:
                    html, s = generate_divisional_confluence_html(pc, code, name)
                except Exception:
                    html, s = "", {}
            pct = int(round(s.get("confluence_pct", 50)))
            vcls, vlabel = _varga_vcls(pct)
            out[code] = {"pct": pct, "conf": s.get("confidence", ""),
                         "vcls": vcls, "vlabel": vlabel, "html": html}
        c["varga"] = out
    return c["varga"]


def _house_data(pc, h):
    hls = pc.get("house_lords", {}) or {}
    hl = hls.get(h) or hls.get(str(h)) or {}
    sign = hl.get("sign", "")
    lord = hl.get("lord", "")
    lsign = hl.get("lord_sign", "")
    # fall back to live planet placement if the cached record is thin
    pdata = (pc.get("planets", {}) or {}).get(lord, {}) if lord else {}
    if not sign and lord:
        sign = SIGNS[(sign_index(lagna(pc)) + h - 1) % 12] if lagna(pc) else ""
    if not lsign:
        lsign = pdata.get("sign", "")
    lhouse = hl.get("lord_house") or pdata.get("house") or (phouse(pc, lord) if lord else 0)
    if not isinstance(lhouse, int):
        lhouse = 0
    ldig = hl.get("lord_dignity", "") or (pdig(pc, lord) if lord else "")
    occ = occupants(pc, h)
    upachaya = h in (3, 6, 11)

    # 1) house lord — dignity + placement
    score = _dig_score(ldig)
    if lhouse in GOOD_HOUSES:
        score += 1.0
    elif lhouse in DUSTHANA:
        score -= 1.0

    # 2) occupants — nodes are harsh; other malefics do well only in upachaya;
    #    an exalted/own benefic occupant lifts the house more than a weak one.
    nodes_here, malefics_here = [], []
    for o in occ:
        odig = pdig(pc, o)
        odig_bonus = {"exalted": 0.5, "moolatrikona": 0.5, "own_sign": 0.4,
                      "debilitated": -0.4}.get(odig, 0.0)
        if o in _NODES:
            nodes_here.append(o)
            score += -0.4 if upachaya else -1.25
        elif o in NAT_MALEFIC:
            malefics_here.append(o)
            score += (0.4 if h in (3, 6, 10, 11) else -0.75) + odig_bonus
        elif o in NAT_BENEFIC:
            score += 0.75 + odig_bonus

    # 3) Ashtakavarga support of the house (28 ≈ average)
    sav = _sav_house(pc, h)
    if sav is not None:
        score += max(-1.5, min(1.5, (sav - 28) / 6.0))

    # 4) bhava karaka (natural significator) condition
    bk, bk_area = BHAVA_KARAKA[h]
    bkdig = pdig(pc, bk)
    score += {"exalted": 0.5, "moolatrikona": 0.5, "own_sign": 0.5,
              "debilitated": -0.75, "enemy_sign": -0.4}.get(bkdig, 0.0)
    bkhouse = phouse(pc, bk)
    if bkhouse in DUSTHANA:
        score -= 0.4

    # 5) the classical 108 rules that touch this house
    rs = _house_rule_signals(pc).get(h, {"pos": 0, "neg": 0})
    rule_net = rs.get("pos", 0) - rs.get("neg", 0)
    score += max(-1.2, min(1.2, 0.3 * rule_net))

    vcls, vlabel = _verdict_house(score)
    return {
        "h": h, "sign": sign, "lord": lord, "lsign": lsign, "lhouse": lhouse,
        "ldig": ldig, "occ": occ, "vcls": vcls, "vlabel": vlabel,
        "sav": sav, "bk": bk, "bk_area": bk_area, "bkdig": bkdig, "bkhouse": bkhouse,
        "nodes_here": nodes_here, "rule_net": rule_net, "score": round(score, 2),
        "note": _house_note(pc, h, lord, lhouse, ldig, occ, vcls,
                            sav, bk, bk_area, bkdig, bkhouse, nodes_here, rule_net),
    }


def _houses_table(pc, name="Client"):
    items = _house_items(pc, name)
    rows, counts = [], {}
    for h in range(1, 13):
        d = _house_data(pc, h)                     # factual columns only
        it = items.get(h, {})
        vcls = it.get("vcls", d["vcls"])
        vlabel = it.get("vlabel", d["vlabel"])
        note = it.get("lead") or d["note"]
        pct = it.get("pct")
        counts[vcls] = counts.get(vcls, 0) + 1
        kind = _house_kind(d["lhouse"])
        kind_txt = f" — a {kind} placement" if kind else ""
        lord_txt = (f"<b>{_esc(d['lord'])}</b> in {_esc(d['lsign'])} ({_ord(d['lhouse'])} house), "
                    f"{_esc(_dig_word(d['ldig']))}")
        occ_txt = ", ".join(_esc(o) for o in d["occ"]) if d["occ"] else "<span style='color:#6b7280'>empty</span>"
        link = f"details/House_{h:02d}_{_esc(name)}.html"
        pct_txt = f"<br><span class='cell-note'>confluence {pct}%</span>" if pct is not None else ""
        rows.append(f"""<tr class="{_ROWCLS[vcls]}">
      <td><b><a href="{link}">{h}</a></b><br><span class="badge">{_esc(HOUSE_SIG[h].split(' · ')[0])}</span></td>
      <td class="cell-rule">{_esc(HOUSE_SIG[h])}</td>
      <td>{_esc(d['sign'])}</td>
      <td class="cell-note">{lord_txt}{_esc(kind_txt)}</td>
      <td>{occ_txt}</td>
      <td><span class="v {vcls}">{_esc(vlabel)}</span>{pct_txt}<br><span class="cell-note">{_esc(_plain(note))}</span></td>
    </tr>""")
    head = ("<tr><th>House</th><th>Signifies</th><th>Sign</th>"
            "<th>Lord &amp; placement</th><th>Occupants</th><th>Strength &amp; reading</th></tr>")
    return counts, head, "\n".join(rows)


def _verdict_house(score: float):
    if score >= 2.0:
        return ("strong", "✓ Strong")
    if score <= -1.3:
        return ("weak", "△ Weak / afflicted")
    return ("mixed", "◐ Mixed")


def _house_note(pc, h, lord, lhouse, ldig, occ, vcls, sav, bk, bk_area, bkdig, bkhouse, nodes_here, rule_net):
    area = HOUSE_SIG[h].split(" · ")[0].lower()
    if vcls == "strong":
        base = f"In matters of {area}, your chart is supportive"
    elif vcls == "weak":
        base = f"In matters of {area}, your chart is under strain"
    else:
        base = f"In matters of {area}, results are mixed"
    bits = []
    # house lord
    if ldig in ("exalted", "moolatrikona", "own_sign"):
        bits.append(f"the lord {lord} is dignified")
    elif ldig == "debilitated":
        bits.append(f"the lord {lord} is debilitated")
    elif ldig == "enemy_sign":
        bits.append(f"the lord {lord} sits in an enemy sign")
    if lhouse in DUSTHANA:
        bits.append(f"its lord falls in the {_ord(lhouse)} (a difficult house)")
    elif lhouse in GOOD_HOUSES:
        bits.append(f"its lord sits in a strong {_ord(lhouse)}")
    # nodes (called out by signification when sensitive)
    if nodes_here and not (h in (3, 6, 11)):
        flag = _NODE_FLAG.get(h)
        nd = ", ".join(nodes_here)
        if flag:
            bits.append(f"{nd} in the {_ord(h)} is a classical challenge for {flag}")
        else:
            bits.append(f"{nd} here unsettles this house")
    # other malefics / benefics
    ben = [o for o in occ if o in NAT_BENEFIC]
    mal = [o for o in occ if o in NAT_MALEFIC and o not in _NODES]
    if ben:
        bits.append(f"benefic {', '.join(ben)} here helps")
    if mal and h not in (3, 6, 11):
        bits.append(f"malefic {', '.join(mal)} here adds pressure")
    # bhava karaka (natural significator)
    if bkdig == "debilitated":
        bits.append(f"{bk}, the natural significator of {bk_area}, is debilitated")
    elif bkhouse in DUSTHANA:
        bits.append(f"{bk}, the significator of {bk_area}, hides in the {_ord(bkhouse)}")
    elif bkdig in ("exalted", "moolatrikona", "own_sign"):
        bits.append(f"{bk}, the significator of {bk_area}, is strong")
    # ashtakavarga
    if sav is not None:
        if sav <= 25:
            bits.append(f"Ashtakavarga support is low ({sav} bindus)")
        elif sav >= 32:
            bits.append(f"Ashtakavarga support is strong ({sav} bindus)")
    # 108 rules
    if rule_net <= -1:
        bits.append("classical (108) rules flag stress here")
    elif rule_net >= 1:
        bits.append("classical (108) rules favour it")
    return base + (" — " + "; ".join(bits) if bits else "") + "."


# ── TABLE 2 · 9 planets ─────────────────────────────────────────────
def _planet_data(pc, p):
    nodes = {"Rahu", "Ketu"}
    sign = psign(pc, p)
    deg = pdeg(pc, p)
    house = phouse(pc, p)
    dig = pdig(pc, p)
    func = (pc.get("planets", {}).get(p, {}) or {}).get("functional_status", "")
    nav = navsign(pc, p)
    retro = pretro(pc, p)
    score = 0 if p in nodes else _dig_score(dig)
    if house in GOOD_HOUSES:
        score += 1
    elif house in DUSTHANA:
        score -= 1
    if func == "functional_benefic":
        score += 0.5
    elif func == "functional_malefic":
        score -= 0.5
    if p not in nodes and afflicted(pc, p):
        score -= 1
    if retro and p not in nodes and p not in ("Sun", "Moon"):
        score += 0.5
    vcls, vlabel = _verdict(score)
    return {
        "p": p, "sign": sign, "deg": deg, "house": house, "dig": dig, "func": func,
        "nav": nav, "retro": retro, "is_node": p in nodes, "nak": pnak(pc, p),
        "vcls": vcls, "vlabel": vlabel,
        "note": _planet_note(p, sign, house, dig, func, retro, p in nodes, vcls),
    }


def _planets_table(pc, name="Client"):
    items = _planet_items(pc, name)
    rows, counts = [], {}
    for p in PLANETS:
        d = _planet_data(pc, p)                    # factual columns only
        it = items.get(p, {})
        vcls = it.get("vcls", d["vcls"])
        vlabel = it.get("vlabel", d["vlabel"])
        note = it.get("lead") or d["note"]
        pct = it.get("pct")
        counts[vcls] = counts.get(vcls, 0) + 1
        func_txt = {"functional_benefic": "benefic for you",
                    "functional_malefic": "malefic for you",
                    "neutral": "neutral"}.get(d["func"], _esc(d["func"]))
        place = (f"<b>{_esc(d['sign'])}</b> {d['deg']:.1f}°{' ℞' if d['retro'] else ''}"
                 f"<br><span class='cell-note'>{_ord(d['house'])} house · {_esc(_house_kind(d['house']) or 'neutral')}</span>")
        link = f"details/Planet_{_esc(p)}_{_esc(name)}.html"
        pct_txt = f"<br><span class='cell-note'>confluence {pct}%</span>" if pct is not None else ""
        rows.append(f"""<tr class="{_ROWCLS[vcls]}">
      <td><b><a href="{link}">{_esc(p)}</a></b><br><span class="badge">{_esc(PLANET_KARAKA[p].split(' · ')[0])}</span></td>
      <td class="cell-rule">{_esc(PLANET_KARAKA[p])}</td>
      <td>{place}</td>
      <td>{_esc(d['nak'])}</td>
      <td>{_esc(_dig_word(d['dig']).replace('in ',''))}</td>
      <td>{func_txt}</td>
      <td><span class="v {vcls}">{_esc(vlabel)}</span>{pct_txt}<br><span class="cell-note">{_esc(_plain(note))}</span></td>
    </tr>""")
    head = ("<tr><th>Planet</th><th>Signifies (karaka)</th><th>Placement</th>"
            "<th>Nakshatra</th><th>Dignity</th><th>For you</th><th>Strength &amp; reading</th></tr>")
    return counts, head, "\n".join(rows)


def _planet_note(p, sign, house, dig, func, retro, is_node, vcls):
    head = {"strong": f"{p} is strong", "weak": f"{p} is weak/under pressure",
            "mixed": f"{p} gives mixed results"}[vcls]
    bits = []
    if not is_node:
        if dig in ("exalted", "moolatrikona", "own_sign"):
            bits.append(f"{_dig_word(dig)}")
        elif dig == "debilitated":
            bits.append("debilitated")
    if house in DUSTHANA:
        bits.append(f"placed in the {_ord(house)} (a trik house)")
    elif house in GOOD_HOUSES:
        bits.append(f"well placed in the {_ord(house)}")
    if func == "functional_benefic":
        bits.append("a natural good for this lagna")
    elif func == "functional_malefic":
        bits.append("a functional malefic here")
    if retro and not is_node and p not in ("Sun", "Moon"):
        bits.append("retrograde (adds strength)")
    area = PLANET_KARAKA[p].split(" · ")[0].lower()
    tail = f" — so matters of {area} are favoured." if vcls == "strong" else (
        f" — so matters of {area} need effort." if vcls == "weak" else
        f" — {area} results come with effort.")
    return head + (" (" + "; ".join(bits) + ")" if bits else "") + tail


# ── TABLE 3 · 20 divisional charts ──────────────────────────────────
def _varga_lagna(pc, code):
    if code == "D1":
        return pc.get("meta", {}).get("lagna_sign", "") or lagna(pc)
    return (pc.get("divisional", {}).get(code, {}) or {}).get("Lagna", "")


def _varga_sign(pc, code, planet):
    if code == "D1":
        return psign(pc, planet)
    return (pc.get("divisional", {}).get(code, {}) or {}).get(planet, "")


def _varga_data(pc, code, name, gov):
    lg = _varga_lagna(pc, code)
    if not lg:
        return None
    lord = SIGN_LORDS.get(lg, "")
    lordsign = _varga_sign(pc, code, lord)
    try:
        ldig = get_dignity(lord, lordsign) if lordsign else ""
    except Exception:
        ldig = ""
    lhouse = ((sign_index(lordsign) - sign_index(lg)) % 12 + 1) if lordsign else 0
    score = _dig_score(ldig)
    if lhouse in GOOD_HOUSES:
        score += 1
    elif lhouse in DUSTHANA:
        score -= 1
    for p in PLANETS:
        if _varga_sign(pc, code, p) == lg:
            if p in NAT_BENEFIC:
                score += 1
            elif p in NAT_MALEFIC:
                score -= 0.5
    strong_here, strong_list = 0, []
    for p in PLANETS:
        s = _varga_sign(pc, code, p)
        try:
            if s and get_dignity(p, s) in ("exalted", "moolatrikona", "own_sign"):
                strong_here += 1
                strong_list.append(p)
        except Exception:
            pass
    score += min(strong_here * 0.25, 1)
    vcls, vlabel = _verdict(score)
    return {
        "code": code, "name": name, "gov": gov, "lg": lg, "lord": lord,
        "lordsign": lordsign, "ldig": ldig, "lhouse": lhouse,
        "strong_here": strong_here, "strong_list": strong_list,
        "vcls": vcls, "vlabel": vlabel,
        "note": _varga_note(name, lord, ldig, lhouse, strong_here, vcls),
    }


def _divisional_table(pc, name="Client"):
    items = _varga_items(pc, name)
    rows, counts = [], {}
    for code, vname, gov in VARGA_GOV:
        d = _varga_data(pc, code, vname, gov)
        if d is None:
            continue
        it = items.get(code, {})
        vcls = it.get("vcls", d["vcls"])
        vlabel = it.get("vlabel", d["vlabel"])
        pct = it.get("pct")
        # reading text re-headed by the confluence verdict so it matches the badge
        note = _varga_note(vname, d["lord"], d["ldig"], d["lhouse"], d["strong_here"], vcls)
        counts[vcls] = counts.get(vcls, 0) + 1
        lord_txt = (f"<b>{_esc(d['lord'])}</b> in {_esc(d['lordsign'])} "
                    f"({_ord(d['lhouse'])}), {_esc(_dig_word(d['ldig']))}") if d["lordsign"] else "—"
        link = f"details/Chart_{code}_{_esc(name)}.html"
        pct_txt = f"<br><span class='cell-note'>confluence {pct}%</span>" if pct is not None else ""
        rows.append(f"""<tr class="{_ROWCLS[vcls]}">
      <td><b><a href="{link}">{code}</a></b><br><span class="badge">{_esc(vname)}</span></td>
      <td class="cell-rule">{_esc(gov)}</td>
      <td>{_esc(d['lg'])}</td>
      <td class="cell-note">{lord_txt}</td>
      <td>{d['strong_here']}</td>
      <td><span class="v {vcls}">{_esc(vlabel)}</span>{pct_txt}<br><span class="cell-note">{_esc(_plain(note))}</span></td>
    </tr>""")
    head = ("<tr><th>Chart</th><th>Governs</th><th>Lagna</th>"
            "<th>Lagna lord &amp; placement</th><th>Exalted/own planets</th><th>Strength &amp; reading</th></tr>")
    return counts, head, "\n".join(rows)


def _varga_note(name, lord, ldig, lhouse, strong_here, vcls):
    area = {"Rasi": "your overall life", "Hora": "your wealth", "Drekkana": "siblings & courage",
            "Chaturthamsha": "property & happiness", "Saptamsha": "children",
            "Navamsha": "marriage & inner strength", "Dashamsha": "career",
            "Dwadashamsha": "parents", "Shodashamsha": "comforts & vehicles",
            "Vimshamsha": "spiritual life", "Chaturvimshamsha": "education",
            "Bhamsha": "innate strengths", "Trimshamsha": "troubles & character",
            "Khavedamsha": "maternal legacy", "Akshavedamsha": "paternal legacy & character",
            "Shashtiamsha": "past-life karma"}.get(name, "this area")
    head = {"strong": f"This division of life — {area} — is well supported",
            "weak": f"This division of life — {area} — is under strain",
            "mixed": f"This division of life — {area} — is mixed"}[vcls]
    bits = []
    if ldig in ("exalted", "moolatrikona", "own_sign"):
        bits.append(f"its lagna lord {lord} is dignified")
    elif ldig == "debilitated":
        bits.append(f"its lagna lord {lord} is debilitated")
    if lhouse in DUSTHANA:
        bits.append(f"the lord falls in the {_ord(lhouse)}")
    elif lhouse in GOOD_HOUSES:
        bits.append(f"the lord sits in a strong {_ord(lhouse)}")
    if strong_here:
        bits.append(f"{strong_here} planet(s) exalted/own here")
    return head + (" — " + "; ".join(bits) if bits else "") + "."


# ── assembly helpers ────────────────────────────────────────────────
COLOUR_NOTE = ("""<div class="note"><b>How to read the colours:</b> green = strong / well supported,
  amber = mixed (works with effort), red = weak / afflicted (needs care &amp; remedies).
  Each verdict here is the <b>confluence of every technique</b> in that item's detailed report
  (Parashari, dignity &amp; placement, Ashtakavarga, the relevant divisional chart, nodes, the
  natural significator and the 108 classical rules) — click a House / Planet / Chart to open the
  full drill-down it is summarising. Timing of results still depends on the running dasha and transits.</div>""")


def _hero(client_name, lg, meta, title, sub):
    return f"""<div class="hero">
    <h1>{title}</h1>
    <div class="sub">{sub}</div>
    <div class="meta">
      <span class="chip">Name: <b>{_esc(client_name)}</b></span>
      <span class="chip">Lagna: <b>{_esc(lg)}</b></span>
      <span class="chip">DOB: <b>{_esc(meta.get('dob',''))}</b></span>
      <span class="chip">Time: <b>{_esc(meta.get('birth_time',''))}</b></span>
      <span class="chip">Place: <b>{_esc(meta.get('birth_place',''))}</b></span>
    </div>
  </div>"""


def _doc(title, body, client_name="Client"):
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>{_css()}{EXTRA_CSS}</style></head>
<body><div class="wrap">
{body}
  <div class="foot">Computed independently from your birth chart.
  For guidance, not a substitute for a personal consultation.</div>
</div></body></html>"""
    try:
        from client_report_html import finalize_report_html
        return finalize_report_html(html, client_name)
    except ImportError:
        return html


def _section(heading, lead, counts, head, rows):
    return f"""<h2>{heading}</h2>
  <p class="lead">{lead}</p>
  {_tally(counts)}
  <table><thead>{head}</thead><tbody>{rows}</tbody></table>"""


# ── combined report (all three tables in one page) ──────────────────
def build_html(pc: dict, client_name: str = "Client") -> str:
    meta = pc.get("meta", {})
    lg = lagna(pc)
    h_counts, h_head, h_rows = _houses_table(pc, client_name)
    p_counts, p_head, p_rows = _planets_table(pc, client_name)
    d_counts, d_head, d_rows = _divisional_table(pc, client_name)
    body = (
        _hero(client_name, lg, meta, "Chart Summary — Houses, Planets &amp; Divisional Charts",
              "Three independent at-a-glance tables: the 12 houses, the 9 planets and the 20 divisional "
              "charts (D1–D60), each scored for strength and read in plain English.")
        + _section("1 · The 12 Houses (Bhavas)",
                   "Each house, the sign on it, its lord and where that lord sits, who occupies it, "
                   "and how well that life-area is supported.", h_counts, h_head, h_rows)
        + _section("2 · The 9 Planets (Grahas)",
                   "Each planet's sign, house and dignity, whether it is benefic or malefic for your "
                   "lagna, and its overall strength.", p_counts, p_head, p_rows)
        + _section("3 · The 20 Divisional Charts (D1–D60)",
                   "Each varga governs a specific area of life. The strength of its ascendant lord and "
                   "the planets dignified within it show how strong that area is.", d_counts, d_head, d_rows)
        + COLOUR_NOTE
    )
    return _doc(f"Chart Summary Tables — {_esc(client_name)}", body, client_name)


# ── standalone single-table reports ─────────────────────────────────
def build_houses_html(pc: dict, client_name: str = "Client") -> str:
    meta, lg = pc.get("meta", {}), lagna(pc)
    counts, head, rows = _houses_table(pc, client_name)
    body = (_hero(client_name, lg, meta, "The 12 Houses (Bhavas) — Summary",
                  "Each house, the sign on it, its lord and placement, occupants and how well that "
                  "life-area is supported.")
            + _section("The 12 Houses (Bhavas)",
                       "Green = well supported, amber = mixed, red = under strain.", counts, head, rows)
            + COLOUR_NOTE)
    return _doc(f"12 Houses — {_esc(client_name)}", body, client_name)


def build_planets_html(pc: dict, client_name: str = "Client") -> str:
    meta, lg = pc.get("meta", {}), lagna(pc)
    counts, head, rows = _planets_table(pc, client_name)
    body = (_hero(client_name, lg, meta, "The 9 Planets (Grahas) — Summary",
                  "Each planet's sign, house and dignity, whether it is benefic or malefic for your "
                  "lagna, and its overall strength.")
            + _section("The 9 Planets (Grahas)",
                       "Green = strong, amber = mixed, red = weak / afflicted.", counts, head, rows)
            + COLOUR_NOTE)
    return _doc(f"9 Planets — {_esc(client_name)}", body, client_name)


def build_divisional_html(pc: dict, client_name: str = "Client") -> str:
    meta, lg = pc.get("meta", {}), lagna(pc)
    counts, head, rows = _divisional_table(pc, client_name)
    body = (_hero(client_name, lg, meta, "The 20 Divisional Charts (D1–D60) — Summary",
                  "Each varga governs a specific area of life. The strength of its ascendant lord and "
                  "the planets dignified within it show how strong that area is.")
            + _section("The 20 Divisional Charts (D1–D60)",
                       "Green = strong, amber = mixed, red = weak / afflicted.", counts, head, rows)
            + COLOUR_NOTE)
    return _doc(f"20 Divisional Charts — {_esc(client_name)}", body, client_name)


# ── granular per-item detail pages (building blocks for the summaries) ─
def _facts(items):
    cells = "".join(
        f"<div class='t'><div class='l'>{_esc(lab)}</div><div class='n' style='font-size:17px'>{val}</div></div>"
        for lab, val in items if val not in (None, "", "—")
    )
    return f"<div class='tally'>{cells}</div>"


def _detail_page(client_name, lg, meta, title, sub, facts, vcls, vlabel, note, table=""):
    body = (
        _hero(client_name, lg, meta, title, sub)
        + f"<div class='tally' style='margin-top:0'><div class='t {('strong' if vcls=='strong' else 'partial' if vcls=='mixed' else 'weak')}'>"
          f"<div class='n'>{_esc(vlabel)}</div><div class='l'>Strength</div></div></div>"
        + _facts(facts)
        + f"<h2>Reading</h2><p class='lead' style='font-size:15.5px;color:var(--ink)'>{_esc(note)}</p>"
        + table
        + COLOUR_NOTE
    )
    return _doc(f"{title} — {_esc(client_name)}", body, client_name)


def build_one_house_html(pc, h, client_name="Client"):
    it = _house_items(pc, client_name).get(h, {})
    if it.get("html"):
        return it["html"]
    d = _house_data(pc, h)
    meta, lg = pc.get("meta", {}), lagna(pc)
    occ = ", ".join(d["occ"]) if d["occ"] else "empty"
    facts = [
        ("Signifies", _esc(HOUSE_SIG[h])),
        ("Sign on house", _esc(d["sign"])),
        ("House lord", _esc(d["lord"])),
        ("Lord placed in", f"{_esc(d['lsign'])} · {_ord(d['lhouse'])} house"),
        ("Lord dignity", _esc(_dig_word(d["ldig"]).replace("in ", ""))),
        ("Occupants", _esc(occ)),
    ]
    return _detail_page(client_name, lg, meta,
                        f"House {h} — {HOUSE_SIG[h].split(' · ')[0]}",
                        f"A close look at your {_ord(h)} house and how well it is supported.",
                        facts, d["vcls"], d["vlabel"], d["note"])


def build_one_planet_html(pc, p, client_name="Client"):
    it = _planet_items(pc, client_name).get(p, {})
    if it.get("html"):
        return it["html"]
    d = _planet_data(pc, p)
    meta, lg = pc.get("meta", {}), lagna(pc)
    pada = (pc.get("planets", {}).get(p, {}) or {}).get("pada", "")
    func_txt = {"functional_benefic": "benefic for this lagna",
                "functional_malefic": "malefic for this lagna",
                "neutral": "neutral"}.get(d["func"], d["func"])
    facts = [
        ("Signifies (karaka)", _esc(PLANET_KARAKA[p])),
        ("Sign", f"{_esc(d['sign'])} {d['deg']:.1f}°{' ℞' if d['retro'] else ''}"),
        ("House", f"{_ord(d['house'])} ({_esc(_house_kind(d['house']) or 'neutral')})"),
        ("Nakshatra", f"{_esc(d['nak'])}{f' · pada {pada}' if pada else ''}"),
        ("Dignity", _esc(_dig_word(d["dig"]).replace("in ", ""))),
        ("Functional role", _esc(func_txt)),
        ("Navāmsa (D9)", _esc(d["nav"])),
    ]
    return _detail_page(client_name, lg, meta,
                        f"{p} — {PLANET_KARAKA[p].split(' · ')[0]}",
                        f"A close look at {p} in your chart and its overall strength.",
                        facts, d["vcls"], d["vlabel"], d["note"])


def build_one_varga_html(pc, code, name, gov, client_name="Client"):
    it = _varga_items(pc, client_name).get(code, {})
    if it.get("html"):
        return it["html"]
    d = _varga_data(pc, code, name, gov)
    meta, lg = pc.get("meta", {}), lagna(pc)
    if d is None:
        return _doc(f"{code} — {_esc(client_name)}",
                    _hero(client_name, lg, meta, f"{code} ({name})", "Chart data unavailable."),
                    client_name)
    facts = [
        ("Governs", _esc(d["gov"])),
        ("Lagna (ascendant)", _esc(d["lg"])),
        ("Lagna lord", _esc(d["lord"])),
        ("Lord placed in", f"{_esc(d['lordsign'])} · {_ord(d['lhouse'])}" if d["lordsign"] else "—"),
        ("Lord dignity", _esc(_dig_word(d["ldig"]).replace("in ", ""))),
        ("Exalted / own planets here", ", ".join(d["strong_list"]) or "none"),
    ]
    return _detail_page(client_name, lg, meta,
                        f"{code} · {name}",
                        f"{_esc(gov)} — the strength of this division of life.",
                        facts, d["vcls"], d["vlabel"], d["note"])


def write_granular(pc: dict, out_dir: Path, client_name: str = "Client") -> list[Path]:
    """Write the 12 house + 9 planet + 20 divisional detail pages into out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for h in range(1, 13):
        f = out_dir / f"House_{h:02d}_{client_name}.html"
        f.write_text(build_one_house_html(pc, h, client_name), encoding="utf-8")
        written.append(f)
    for p in PLANETS:
        f = out_dir / f"Planet_{p}_{client_name}.html"
        f.write_text(build_one_planet_html(pc, p, client_name), encoding="utf-8")
        written.append(f)
    for code, name, gov in VARGA_GOV:
        f = out_dir / f"Chart_{code}_{client_name}.html"
        f.write_text(build_one_varga_html(pc, code, name, gov, client_name), encoding="utf-8")
        written.append(f)
    return written


def write_report(pc: dict, out_dir: Path, client_name: str = "Client") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"Chart_Summary_{client_name}.html"
    out.write_text(build_html(pc, client_name), encoding="utf-8")
    return out


if __name__ == "__main__":
    import argparse
    from astro_chart_bridge import compute_chart

    ap = argparse.ArgumentParser(description="House / planet / divisional summary tables")
    ap.add_argument("--name", default="Ritesh")
    ap.add_argument("--dob", default="1985-03-08")
    ap.add_argument("--time", default="13:05")
    ap.add_argument("--place", default="Patna, India")
    ap.add_argument("--lat", type=float, default=25.5941)
    ap.add_argument("--lon", type=float, default=85.1376)
    ap.add_argument("--tz", type=float, default=5.5)
    ap.add_argument("-o", "--out", default="")
    args = ap.parse_args()

    pc = compute_chart(client_name=args.name, dob=args.dob, birth_time=args.time,
                       place=args.place, latitude=args.lat, longitude=args.lon, timezone=args.tz)
    out_dir = Path(args.out) if args.out else (BASE_DIR / "reports" / args.name)
    path = write_report(pc, out_dir, args.name)
    print(f"Wrote {path}")
