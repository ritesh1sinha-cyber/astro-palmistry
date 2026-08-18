#!/usr/bin/env python3
"""
vedic_horary_report.py — Deterministic Vedic horary / prashna report (NO LLM).

Replaces the Cursor-AI "Vedic horary" lane. Casts the prashna chart with
``horary_precompute.precompute_horary`` (Swiss Ephemeris sidereal Lahiri when
pyswisseph is installed), then applies three classical horary systems as
deterministic rules and renders an HTML report matching the gold reference
``reports/Horary_ChildSpeech_20260407.html``:

  • Jamakkol Prasanam     — Aarudam / Udhayam / Veedhi / Kavippu (precomputed)
  • Prashna Kundali        — Arudha, Lagna lord, Jupiter drishti, topic modules (rules39)
  • KP Horary              — cuspal sub-lord significators vs favourable bhavas,
                             cross-checked with the Ruling Planets

A confluence vote of the three systems gives the final verdict + confidence.
Everything is rule-derived — no model, no network, fully reproducible.
"""
from __future__ import annotations

import argparse
import html
from pathlib import Path
from typing import Optional

from horary_precompute import (
    precompute_horary, SIGN_LORDS, TOPIC_BHAVAS, house_lord, house_sign,
)
from prashna_kundali_engine import analyze_prashna

BASE_DIR = Path(__file__).resolve().parent
GOLD_TEMPLATE = BASE_DIR / "reports" / "Horary_ChildSpeech_20260407.html"

GLYPH = {
    "Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀", "Mars": "♂",
    "Jupiter": "♃", "Saturn": "♄", "Rahu": "☊", "Ketu": "☋",
}
NATURAL_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
NATURAL_MALEFIC = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}

# Short bhava themes for the house-layout table.
HOUSE_THEME = {
    1: "Self, the questioner, the body of the matter",
    2: "Wealth, speech, family, accumulated resources",
    3: "Effort, courage, siblings, short journeys, communication",
    4: "Home, mother, property, vehicles, inner peace",
    5: "Children, intelligence, romance, speculation",
    6: "Disease, debts, enemies, service, obstacles",
    7: "Spouse, partnerships, the other party, contracts",
    8: "Hidden matters, transformation, longevity, sudden events",
    9: "Fortune, dharma, father, higher learning, long travel",
    10: "Career, status, action, public standing",
    11: "Gains, fulfilment of desire, income, friends",
    12: "Loss, expenditure, foreign lands, isolation, liberation",
}

# Natural significators (karakas) per topic — used for remedies + emphasis.
TOPIC_KARAKA = {
    "children": ["Jupiter"], "marriage": ["Venus", "Jupiter"],
    "career": ["Sun", "Saturn", "Mercury"], "job": ["Sun", "Saturn", "Mercury"],
    "health": ["Sun", "Moon"], "disease": ["Sun", "Mars"],
    "finance": ["Jupiter", "Venus", "Mercury"], "travel": ["Mercury", "Moon"],
    "property": ["Mars", "Venus"], "education": ["Mercury", "Jupiter"],
    "litigation": ["Mars", "Saturn"], "loan": ["Jupiter", "Mercury"],
    "general": ["Jupiter"],
}

TOPIC_PHRASE = {
    "children": "having a child / your child's matter", "marriage": "this relationship",
    "career": "this work matter", "job": "this job", "health": "your health",
    "disease": "recovering from this illness", "finance": "this money matter",
    "travel": "this travel plan", "property": "this property matter",
    "education": "this study / exam", "litigation": "this dispute",
    "loan": "this loan", "general": "what you've asked about",
}

PLANET_REMEDY = {
    "Sun": ("Surya", "Sundays", "Om Suryaya Namaha", "ruby", "offer water to the rising Sun"),
    "Moon": ("Chandra", "Mondays", "Om Chandraya Namaha", "pearl", "offer white flowers / milk to water"),
    "Mars": ("Mangala", "Tuesdays", "Om Mangalaya Namaha", "red coral", "feed jaggery to others, Hanuman Chalisa"),
    "Mercury": ("Budha", "Wednesdays", "Om Budhaya Namaha", "emerald", "donate green moong, support students"),
    "Jupiter": ("Guru", "Thursdays", "Om Gurave Namaha", "yellow sapphire", "feed Brahmins / teachers, donate turmeric"),
    "Venus": ("Shukra", "Fridays", "Om Shukraya Namaha", "diamond / white sapphire", "offer white sweets, honour women"),
    "Saturn": ("Shani", "Saturdays", "Om Shanaye Namaha", "blue sapphire (with caution)", "serve the elderly, feed crows, donate black sesame"),
    "Rahu": ("Rahu", "Saturdays", "Om Rahave Namaha", "hessonite", "donate to the marginalised, avoid intoxicants"),
    "Ketu": ("Ketu", "Tuesdays", "Om Ketave Namaha", "cat's-eye", "feed dogs, support spiritual causes"),
}

# ──────────────────────────── helpers ────────────────────────────


def _hl(data: dict, h: int) -> dict:
    """House-lord record tolerating int or str keys."""
    hl = data["house_lords"]
    return hl.get(h) or hl.get(str(h)) or {}


def fmt_deg(degree: float) -> str:
    d = int(degree)
    m = int(round((degree - d) * 60))
    if m == 60:
        d, m = d + 1, 0
    return f"{d}°{m:02d}'"


def ordinal(n: int) -> str:
    return f"{n}{'tsnrhtdd'[(n//10%10!=1)*(n%10<4)*n%10::4]}"


# ───────────────────── KP significator engine ─────────────────────


def kp_significations(planet: str, data: dict) -> set[int]:
    """Houses a planet signifies in KP (occupied/owned by it and by its star-lord)."""
    planets, houses = data["planets"], data["houses"]
    sig: set[int] = set()
    if planet in houses:
        sig.add(houses[planet])
    for h in range(1, 13):
        if _hl(data, h).get("lord") == planet:
            sig.add(h)
    star_lord = planets.get(planet, {}).get("star_lord")
    if star_lord and star_lord in houses:
        sig.add(houses[star_lord])
        for h in range(1, 13):
            if _hl(data, h).get("lord") == star_lord:
                sig.add(h)
    return sig


# ───────────────────────── verdict synthesis ──────────────────────

LABEL_CHIP = {  # per-system label → (chip class, display word, fact-value class)
    "YES":         ("chip-favorable", "Favourable", "good"),
    "CONDITIONAL": ("chip-conditional", "Conditional", "mixed"),
    "NO":          ("chip-challenging", "Challenging", "bad"),
    "NEUTRAL":     ("chip-conditional", "Inconclusive", "mixed"),
}


def _label(score: float) -> str:
    if score >= 0.5:
        return "YES"
    if score <= -0.5:
        return "NO"
    if -0.15 < score < 0.15:
        return "NEUTRAL"
    return "CONDITIONAL"


def judge_jamakkol(data: dict) -> dict:
    jk = data["jamakkol"]
    v = (jk.get("verdict") or "CONDITIONAL").upper()
    kav = jk["kavippu"]
    kh = kav.get("kavippu_house_from_udhayam")
    score = {"YES": 1.0, "NO": -1.0, "CONDITIONAL": 0.0}.get(v, 0.0)
    # Kavippu in the 11th (fulfilment) is the strongest positive; in 6/8/12 strongly negative.
    if kh == 11:
        score = 1.0
    elif kh in (6, 8, 12):
        score = min(score, -0.6)
    label = _label(score) if v == "CONDITIONAL" else v
    return {"score": score, "label": label, "verdict": v,
            "reason": jk.get("verdict_reason", ""), "kavippu_house": kh,
            "kavippu_sign": kav.get("kavippu_sign"),
            "conjunct": jk.get("kavippu_conjunct_planets", [])}


def judge_prashna(data: dict) -> dict:
    direction = data.get("meta", {}).get("arudha_direction")
    return analyze_prashna(data, arudha_direction=direction)


def judge_kp(data: dict) -> dict:
    kp = data.get("kp_data") or {}
    topic = data["meta"]["detected_topic"]
    tb = TOPIC_BHAVAS.get(topic, TOPIC_BHAVAS["general"])
    rp = data["ruling_planets"]["all_ruling_planets"]
    promise = kp.get("promise") or {}

    if promise:
        sub_lord = promise.get("cusp_sub_lord")
        star_lord = promise.get("star_lord")
        fav = promise.get("fav_hits", [])
        den = promise.get("den_hits", [])
        sig = promise.get("significations", [])
        pv = promise.get("verdict", "CONDITIONAL")
        pts = {"YES": 0.8, "NO": -0.8, "CONDITIONAL": 0.0}.get(pv, 0.0)
        if sub_lord in rp:
            pts += 0.3
        fav_lords = {_hl(data, h).get("lord") for h in tb["favorable"]}
        if fav_lords & set(rp):
            pts += 0.2
        score = max(-1.0, min(1.0, pts))
        return {
            "score": score, "label": _label(score), "available": True,
            "sub_lord": sub_lord, "star_lord": star_lord,
            "kp_lagna": kp.get("sign"), "nakshatra": kp.get("nakshatra"),
            "kp_number": kp.get("kp_number"), "auto": kp.get("auto_derived", False),
            "significations": sig, "fav_hits": fav, "den_hits": den,
            "in_rp": sub_lord in rp, "signifies_primary": tb["primary"] in sig,
            "rp": rp, "promise_verdict": pv, "promise_reason": promise.get("reason", ""),
            "list_a": kp.get("list_a", []), "list_c": kp.get("list_c", []),
            "primary_bhava": promise.get("primary_bhava", tb["primary"]),
            "favorable": tb["favorable"], "denying": tb["denying"],
            "cusp_sub_lord": promise.get("cusp_sub_lord"),
            "sub_lord_house": promise.get("sub_lord_house"),
        }

    sub_lord = kp.get("sub_lord")
    if not sub_lord:
        return {"score": 0.0, "label": "NEUTRAL", "available": False, "rp": rp}

    sig = kp_significations(sub_lord, data)
    fav = sorted(sig & set(tb["favorable"]))
    den = sorted(sig & set(tb["denying"]))
    in_rp = sub_lord in rp
    signifies_primary = tb["primary"] in sig

    pts = 0.0
    pts += 0.6 * len(fav)
    pts -= 0.6 * len(den)
    if signifies_primary:
        pts += 0.6
    if in_rp:
        pts += 0.4
    fav_lords = {_hl(data, h).get("lord") for h in tb["favorable"]}
    if fav_lords & set(rp):
        pts += 0.3
    score = max(-1.0, min(1.0, pts / 2.0))
    return {
        "score": score, "label": _label(score), "available": True,
        "sub_lord": sub_lord, "kp_lagna": kp.get("sign"),
        "nakshatra": kp.get("nakshatra"), "star_lord": kp.get("star_lord"),
        "kp_number": kp.get("kp_number"), "auto": kp.get("auto_derived", False),
        "significations": sorted(sig), "fav_hits": fav, "den_hits": den,
        "in_rp": in_rp, "signifies_primary": signifies_primary, "rp": rp,
        "primary_bhava": tb["primary"], "favorable": tb["favorable"], "denying": tb["denying"],
    }


VERDICT_TEXT = {  # final confluence → (word, chip, headline mood)
    "YES":       ("YES", "good", "The chart supports a favourable outcome"),
    "LIKELY":    ("LIKELY", "good", "The weight of testimony leans favourable"),
    "UNCERTAIN": ("UNCERTAIN", "mixed", "The systems are divided — a conditional, effort-dependent outcome"),
    "UNLIKELY":  ("UNLIKELY", "bad", "The weight of testimony leans against the matter"),
    "NO":        ("NO", "bad", "The chart argues against the matter as asked"),
}


def judge_vedic(data: dict) -> dict:
    jam = judge_jamakkol(data)
    pra = judge_prashna(data)
    kp = judge_kp(data)

    # Weighted confluence — KP is the most decision-oriented, then Prashna, then Jamakkol.
    parts = [(kp["score"], 1.2 if kp.get("available") else 0.0),
             (pra["score"], 1.0), (jam["score"], 0.8)]
    wsum = sum(w for _, w in parts) or 1.0
    total = sum(s * w for s, w in parts) / wsum

    if total >= 0.5:
        final = "YES"
    elif total >= 0.15:
        final = "LIKELY"
    elif total > -0.15:
        final = "UNCERTAIN"
    elif total > -0.5:
        final = "UNLIKELY"
    else:
        final = "NO"

    signs = [1 if x["score"] > 0.15 else (-1 if x["score"] < -0.15 else 0)
             for x in (jam, pra, kp)]
    rad = data["radicality"]
    agree = len({s for s in signs if s != 0}) <= 1 and signs.count(0) <= 1
    if rad.get("is_likely_test"):
        conf = "LOW"
    elif agree and 0 not in signs:
        conf = "HIGH"
    elif signs.count(0) <= 1 and len({s for s in signs if s != 0}) == 1:
        conf = "MODERATE"
    else:
        conf = "LOW"

    return {"jamakkol": jam, "prashna": pra, "kp": kp,
            "total": round(total, 3), "verdict": final, "confidence": conf}


# ──────────────────────────── rendering ───────────────────────────


def _css() -> str:
    """Reuse the gold template's stylesheet for visual parity; minimal fallback otherwise."""
    try:
        txt = GOLD_TEMPLATE.read_text(encoding="utf-8")
        i, j = txt.find("<style>"), txt.find("</style>")
        if i != -1 and j != -1:
            base = txt[i + len("<style>"):j]
    except Exception:
        base = ":root{--bg:#0d1117;--card:#21262d;--border:#30363d;--gold:#d4a843;--text:#e6edf3;--text-dim:#8b949e;--green:#3fb950;--red:#e05555;--amber:#f0a500}body{background:#0d1117;color:#e6edf3;font-family:system-ui,sans-serif;line-height:1.7}.container{max-width:960px;margin:0 auto;padding:0 1.5rem}"
    # Add the favourable (green) chip / system-verdict classes the gold file lacks.
    base += """
  .chip-favorable { background: rgba(63,185,80,0.15); color: var(--green); border: 1px solid rgba(63,185,80,0.3); }
  .sv-favorable { color: var(--green); }
  .sv-yes { color: var(--green); }
"""
    return base


def _planet_table(data: dict) -> str:
    rows = []
    order = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu"]
    for p in order:
        pl = data["planets"][p]
        rows.append(
            f"<tr><td>{p} {GLYPH[p]}</td><td>{pl['sign']} {fmt_deg(pl['degree'])}</td>"
            f"<td>{pl['nakshatra']}</td><td>{pl.get('star_lord','')}</td></tr>")
    lg = data["lagna"]
    rows.append(
        f"<tr style='background:rgba(212,168,67,0.06)'><td><strong>Lagna</strong></td>"
        f"<td><strong>{lg['sign']} {fmt_deg(lg['degree'])}</strong></td>"
        f"<td>{lg['nakshatra']}</td><td>{lg.get('star_lord','')}</td></tr>")
    return ("<table class='calc-table'><thead><tr><th>Body</th><th>Sidereal</th>"
            "<th>Nakshatra</th><th>Star lord</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


def _house_table(data: dict, j: dict) -> str:
    topic = data["meta"]["detected_topic"]
    tb = TOPIC_BHAVAS.get(topic, TOPIC_BHAVAS["general"])
    houses = data["houses"]
    occupants = {h: [] for h in range(1, 13)}
    for p, h in houses.items():
        occupants[h].append(p)
    rows = []
    for h in range(1, 13):
        rec = _hl(data, h)
        sign, lord = rec.get("sign", ""), rec.get("lord", "")
        occ = occupants[h]
        occ_str = " ".join(f"{p}{GLYPH[p]}" for p in occ) if occ else "—"
        cls = ""
        if h == tb["primary"]:
            cls = "flag-note"
        elif h in tb["denying"] and any(p in NATURAL_MALEFIC for p in occ):
            cls = "flag-bad"
        relevance = HOUSE_THEME[h]
        tag = ""
        if h == tb["primary"]:
            tag = " <strong>(primary house of the question)</strong>"
        elif h in tb["favorable"]:
            tag = " <em>(favourable for the matter)</em>"
        elif h in tb["denying"]:
            tag = " <em>(denying / obstacle house)</em>"
        rows.append(
            f"<tr class='{cls}'><td>{h}</td><td>{sign}</td><td>{occ_str}</td>"
            f"<td>{relevance}. Lord {lord}.{tag}</td></tr>")
    return ("<div class='card' style='padding:0;overflow:hidden'>"
            "<table class='house-table'><thead><tr><th>#</th><th>Sign</th>"
            "<th>Occupants</th><th>Relevance to the query</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def _plain_reading(data: dict, j: dict) -> str:
    """A warm, plain-language summary spoken as a human astrologer would — no jargon."""
    topic = data["meta"]["detected_topic"]
    phrase = TOPIC_PHRASE.get(topic, TOPIC_PHRASE["general"])
    v = j["verdict"]
    opener = {
        "YES": f"Yes — the chart genuinely backs you on {phrase}.",
        "LIKELY": f"Most of the signs lean towards <strong>yes</strong> on {phrase}, with a small caveat or two.",
        "UNCERTAIN": f"Honestly, {phrase} sits on a knife's edge right now — the chart is genuinely mixed.",
        "UNLIKELY": f"The chart leans towards <strong>no</strong> on {phrase}, at least the way things stand today.",
        "NO": f"The honest answer on {phrase} is <strong>no</strong> — not as the question stands right now.",
    }[v]

    pra, kp, jam = j["prashna"], j["kp"], j["jamakkol"]
    pieces = []
    pra_say = {"YES": "your own position in the matter looks strong",
               "CONDITIONAL": "your own position is workable but mixed",
               "NO": "your own position looks a little strained",
               "NEUTRAL": "your own position is neither strong nor weak"}[pra["label"]]
    pieces.append(pra_say)
    if kp.get("available"):
        kp_say = {"YES": "the deciding factor in the chart supports it",
                  "CONDITIONAL": "the deciding factor is split between help and hindrance",
                  "NO": "the deciding factor works against it",
                  "NEUTRAL": "the deciding factor is unclear"}[kp["label"]]
        pieces.append(kp_say)
    jam_say = {"YES": "the timing method agrees",
               "CONDITIONAL": "the timing method is cautious",
               "NO": "the timing method flags some friction (often around money, family, or delay)",
               "NEUTRAL": "the timing method is neutral"}[jam["label"]]
    pieces.append(jam_say)
    why = "In short: " + "; ".join(pieces) + "."

    conf_say = {
        "HIGH": "All three traditional methods point the same way, so you can lean on this with real confidence.",
        "MODERATE": "Two of the three methods agree — treat this as a solid leaning rather than a guarantee.",
        "LOW": "The three methods don't fully agree, so please take this as a gentle leaning, not a promise.",
    }[j["confidence"]]

    rp = data["ruling_planets"]["all_ruling_planets"]
    timing_say = (f"For timing, the planets carrying this matter are <strong>{', '.join(rp)}</strong> — "
                  f"watch the stretches when these are strong (their periods or transits) for movement.")

    return f"""
<div class="section">
  <div class="section-title">The Short Answer — In Plain Words</div>
  <div class="card" style="border-left:3px solid var(--gold);">
    <p style="font-size:1.02rem;margin-bottom:0.7rem;">{opener}</p>
    <p style="margin-bottom:0.7rem;">{why}</p>
    <p style="margin-bottom:0.7rem;color:var(--text-dim);">{conf_say}</p>
    <p style="margin:0;">{timing_say}</p>
  </div>
</div>"""


def _chip(label: str) -> str:
    cls, word, _ = LABEL_CHIP.get(label, LABEL_CHIP["NEUTRAL"])
    return f"<div class='verdict-chip {cls}'>{word}</div>"


def _fact(label: str, value: str, cls: str = "") -> str:
    c = f" {cls}" if cls else ""
    return f"<div class='fact-row'><span class='fact-label'>{label}</span><span class='fact-value{c}'>{value}</span></div>"


def _jamakkol_plain_text(jam: dict, jk: dict) -> str:
    return {
        "YES": "the immediate planetary momentum gives a clean green light.",
        "CONDITIONAL": "the planetary momentum indicates success is achievable with proactive effort.",
        "NO": f"the planetary momentum points to obstacles — {jk.get('verdict_reason', '').lower() or 'temporary blockages exist'}.",
        "NEUTRAL": "the planetary momentum is currently balanced — neither a clear yes nor no.",
    }[jam["label"]]


def _prashna_plain_text(pra: dict) -> str:
    return {
        "YES": "the chart of the moment puts you in a strong spot and the matter's natural ruler is well placed.",
        "CONDITIONAL": "the chart of the moment is encouraging in parts and resistant in others — a mixed, effort-dependent picture.",
        "NO": "the chart of the moment puts the matter's natural ruler in a weak spot, which argues against an easy outcome.",
        "NEUTRAL": "the chart of the moment is fairly balanced, without a strong push either way.",
    }[pra["label"]]


def _kp_plain_text(kp: dict) -> str:
    if not kp.get("available"):
        return "the secondary timing factor was not active for this reading."
    sub = kp["sub_lord"]
    return {
        "YES": f"the key timing planet ({sub}) is supporting you and aligns with current ruling significators.",
        "CONDITIONAL": f"the key timing planet ({sub}) shows mixed influences — positive prospects with necessary conditions.",
        "NO": f"the key timing planet ({sub}) creates resistance for the matter.",
        "NEUTRAL": f"the key timing planet ({sub}) is neutrally positioned.",
    }[kp["label"]]


def _step_icon(i: int) -> str:
    """Circled step number. The card grows an extra step whenever the chart
    has classical notes to add, so a fixed seven-glyph string ran off the end
    and took the whole horary report down with it."""
    return chr(0x2460 + i) if 0 <= i < 20 else str(i + 1)


def _jamakkol_card(data: dict, jam: dict) -> str:
    jk = data["jamakkol"]
    kav = jk["kavippu"]
    steps = [
        f"<strong>Aarudam</strong> (query indicator): <strong>{jk['aarudam']}</strong>, "
        f"the {ordinal(jk['aarudam_house_from_udhayam'])} house from Udhayam — the area the question truly concerns.",
        f"<strong>Udhayam</strong> (rising sign / outcome indicator): <strong>{jk['udhayam']}</strong>.",
        f"<strong>Veedhi</strong> (path of the Sun in {data['planets']['Sun']['sign']}): "
        f"<strong>{kav['veedhi']} Veedhi</strong> (endpoint {kav['veedhi_target']}).",
        f"<strong>Kavippu</strong> (decisive outcome point): <strong>{kav['kavippu_sign']}</strong>, "
        f"the {ordinal(kav['kavippu_house_from_udhayam'])} house from Udhayam — "
        f"<em>{kav['kavippu_meaning']}</em>.",
    ]
    conj = jk.get("kavippu_conjunct_planets") or []
    if conj:
        steps.append(f"<strong>Kavippu conjunct {', '.join(conj)}</strong> — these planets colour the outcome.")
    steps_html = "".join(
        f"<li><span class='step-icon'>{_step_icon(i)}</span><span>{s}</span></li>"
        for i, s in enumerate(steps))
    kh = jam["kavippu_house"]
    kav_cls = "good" if kh == 11 else ("bad" if kh in (6, 8, 12) else "mixed")
    facts = (
        _fact("Aarudam", f"{jk['aarudam']} ({ordinal(jk['aarudam_house_from_udhayam'])} from Udhaya)")
        + _fact("Udhayam", jk["udhayam"])
        + _fact("Veedhi", f"{kav['veedhi']} Veedhi")
        + _fact("Kavippu", f"{kav['kavippu_sign']} — {ordinal(kh)} from Udhaya", kav_cls)
        + _fact("Verdict", f"{LABEL_CHIP[jam['label']][1]} — {jk.get('verdict_reason','')}", LABEL_CHIP[jam["label"]][2]))
    plain = _jamakkol_plain_text(jam, jk)
    return _technique_card("JK", "badge-jk", "Jamakkol Prasanam",
                           "Tamil Prasanam — Aarudam / Udhayam / Veedhi / Kavippu method",
                           jam["label"], steps_html, "Jamakkol Summary", facts, plain=plain)


def _prashna_card(data: dict, pra: dict) -> str:
    ll = pra["lagna_lord"]
    steps = [
        f"<strong>Arudha (query anchor):</strong> {pra['arudha_sign']} "
        f"(house {ordinal(pra['arudha_house_from_lagna'])} from Lagna; source: {pra['arudha_source']}).",
        f"<strong>Lagna lord {ll}</strong> sits in the {ordinal(pra['ll_house'])} house "
        f"({pra['ll_status'].lower()} placement) — this shows the questioner's standing in the matter.",
        ("<strong>Jupiter aspects the Lagna</strong> — the benefic's grace protects the question."
         if pra["jup_aspects_lagna"] else
         f"<strong>Jupiter</strong> sits in the {ordinal(pra['jup_house'])} and does not aspect the Lagna — no special protective grace."),
        ("<strong>Jupiter aspects the Moon</strong> — emotional support for the matter."
         if pra.get("jup_aspects_moon") else
         f"<strong>Moon</strong> in the {ordinal(pra.get('moon_house', 0))} "
         f"({pra.get('paksha', 'Shukla')} paksha) without Jupiter's aspect."),
        (f"<strong>Malefics in the Lagna:</strong> {', '.join(pra['malefics_in_lagna'])} — they stress the matter."
         if pra["malefics_in_lagna"] else
         "<strong>No malefic occupies the Lagna</strong> — the ascendant is clean."),
        (f"<strong>Benefics in kendra:</strong> {', '.join(pra.get('benefics_in_kendra', []))}."
         if pra.get("benefics_in_kendra") else ""),
        f"<strong>Topic house ({ordinal(pra['primary_bhava'])}) lord {pra['topic_lord']}</strong> "
        f"is in the {ordinal(pra['tl_house'])} — status <strong>{pra['tl_status']}</strong>; "
        f"this is the heart of the Prashna judgment.",
    ]
    steps = [s for s in steps if s]
    if pra.get("notes"):
        steps.append("<strong>Classical notes:</strong> " + "; ".join(html.escape(n) for n in pra["notes"][:4]))
    steps_html = "".join(
        f"<li><span class='step-icon'>{_step_icon(i)}</span><span>{s}</span></li>"
        for i, s in enumerate(steps))
    tl_cls = {"FAVORABLE": "good", "DENYING": "bad"}.get(pra["tl_status"], "mixed")
    facts = (
        _fact("Arudha", f"{pra['arudha_sign']} (H{pra['arudha_house_from_lagna']})")
        + _fact(f"Lagna lord ({ll})", f"in {ordinal(pra['ll_house'])} — {pra['ll_status']}",
              "good" if pra["ll_status"] == "GOOD" else ("bad" if pra["ll_status"] == "WEAK" else "mixed"))
        + _fact("Jupiter aspect on Lagna", "Yes — protective" if pra["jup_aspects_lagna"] else "No", "good" if pra["jup_aspects_lagna"] else "mixed")
        + _fact("Paksha", pra.get("paksha", "Shukla"))
        + _fact("Malefics in Lagna", ", ".join(pra["malefics_in_lagna"]) or "None — clean", "bad" if pra["malefics_in_lagna"] else "good")
        + _fact(f"{ordinal(pra['primary_bhava'])} lord ({pra['topic_lord']})", f"in {ordinal(pra['tl_house'])} — {pra['tl_status']}", tl_cls)
        + _fact("Verdict", LABEL_CHIP[pra["label"]][1], LABEL_CHIP[pra["label"]][2]))
    plain = _prashna_plain_text(pra)
    return _technique_card("PK", "badge-pk", "Prashna Kundali Siddhanta",
                           "Chart-based prashna — Arudha, Lagna, Jupiter grace, topic-bhava lord",
                           pra["label"], steps_html, "Prashna Kundali Summary", facts, plain=plain)


def _kp_card(data: dict, kp: dict) -> str:
    if not kp.get("available"):
        body = ("<p style='color:var(--text-dim)'>No KP number was supplied and none could be derived, "
                "so the KP cuspal analysis is omitted. Provide a KP number (1–249) for this lane.</p>")
        return _technique_card("KP", "badge-kp", "KP Horary",
                               "Krishnamurti Paddhati — cuspal sub-lord + Ruling Planets",
                               "NEUTRAL", "", "", "", body_override=body)
    sub = kp["sub_lord"]
    sig = ", ".join(ordinal(h) for h in kp["significations"]) or "—"
    steps = [
        f"<strong>KP Lagna:</strong> {kp['kp_lagna']} (number {kp['kp_number']}"
        + (", auto-derived" if kp["auto"] else "") + f"), nakshatra {kp['nakshatra']} (star lord {kp['star_lord']}).",
        f"<strong>Cuspal sub-lord = {sub}</strong> — in KP the sub-lord is the final arbiter of the matter.",
        f"<strong>{sub} signifies houses {sig}.</strong> "
        + (f"Favourable hits: {', '.join(ordinal(h) for h in kp['fav_hits'])}. " if kp["fav_hits"] else "No favourable-house signification. ")
        + (f"Denying hits: {', '.join(ordinal(h) for h in kp['den_hits'])}." if kp["den_hits"] else "No denying-house signification."),
        f"<strong>Ruling Planets:</strong> {', '.join(kp['rp'])}. "
        + (f"The sub-lord {sub} is itself a Ruling Planet — a strong confirmation." if kp["in_rp"]
           else f"The sub-lord {sub} is not among the Ruling Planets."),
    ]
    steps_html = "".join(
        f"<li><span class='step-icon'>{_step_icon(i)}</span><span>{s}</span></li>"
        for i, s in enumerate(steps))
    facts = (
        _fact("KP Lagna sub-lord", sub)
        + _fact("Sub-lord signifies", sig, "good" if kp["fav_hits"] and not kp["den_hits"] else ("bad" if kp["den_hits"] and not kp["fav_hits"] else "mixed"))
        + _fact("Favourable bhavas", ", ".join(ordinal(h) for h in kp["favorable"]))
        + _fact("Ruling Planets", " · ".join(kp["rp"]))
        + _fact("Verdict", LABEL_CHIP[kp["label"]][1], LABEL_CHIP[kp["label"]][2]))
    plain = _kp_plain_text(kp)
    return _technique_card("KP", "badge-kp", "KP Horary",
                           "Krishnamurti Paddhati — cuspal sub-lord + Ruling Planets",
                           kp["label"], steps_html, "KP Summary", facts, plain=plain)


def _technique_card(badge: str, badge_cls: str, title: str, subtitle: str,
                    label: str, steps_html: str, facts_title: str, facts_html: str,
                    body_override: str = "", plain: str = "") -> str:
    plain_html = (f"<p style='background:rgba(212,168,67,0.07);border-radius:8px;padding:0.6rem 0.8rem;"
                  f"margin-bottom:0.9rem;font-size:0.92rem;'><strong>In plain words:</strong> {plain}</p>"
                  if plain else "")
    body = body_override or (
        plain_html
        + f"<ul class='step-list'>{steps_html}</ul>"
        f"<div class='key-facts'><div class='key-facts-title'>{facts_title}</div>{facts_html}</div>")
    return f"""
  <div class="technique-card">
    <div class="technique-header">
      <div class="technique-badge {badge_cls}">{badge}</div>
      <div>
        <div class="technique-title">{title}</div>
        <div class="technique-subtitle">{subtitle}</div>
      </div>
      {_chip(label)}
    </div>
    <div class="technique-body">{body}</div>
  </div>"""


def _confluence(data: dict, j: dict) -> str:
    jam, pra, kp = j["jamakkol"], j["prashna"], j["kp"]
    word, mood, headline = VERDICT_TEXT[j["verdict"]]
    sv = {"good": "sv-favorable", "mixed": "sv-conditional", "bad": "sv-challenging"}

    def card(name, sub_j, note):
        cls, disp, _ = LABEL_CHIP[sub_j["label"]]
        svc = {"chip-favorable": "sv-favorable", "chip-conditional": "sv-conditional",
               "chip-challenging": "sv-challenging"}.get(cls, "sv-conditional")
        return (f"<div class='score-card'><div class='sys-name'>{name}</div>"
                f"<div class='sys-verdict {svc}'>{disp}</div>"
                f"<div style='font-size:0.7rem;color:var(--text-dim);margin-top:0.3rem'>{note}</div></div>")

    kp_note = (f"sub-lord {kp.get('sub_lord','—')}" if kp.get("available") else "no KP number")
    pra_note = f"{ordinal(pra['primary_bhava'])} lord {pra['topic_lord']} {pra['tl_status'].lower()}"
    jam_note = f"Kavippu {ordinal(jam['kavippu_house'])} from Udhaya"

    agree_line = {
        "HIGH": "All three systems point the same way — a clear, consistent reading.",
        "MODERATE": "Two of the three systems agree; the third is mixed or conditional.",
        "LOW": "The systems disagree, or the chart's radicality is questionable — treat the answer as tentative.",
    }[j["confidence"]]
    rad = data["radicality"]
    rad_line = (f"Radicality: {rad['score']}/{rad['max_score']} caution flags — {rad['interpretation']}.")

    return f"""
<div class="section">
  <div class="section-title">Confluence Verdict</div>
  <div class="verdict-box">
    <div class="verdict-head">
      <div class="verdict-icon">⚖️</div>
      <div>
        <div class="verdict-title">{word} — {headline}</div>
        <div style="font-size:0.8rem;color:var(--text-dim);margin-top:0.2rem">{agree_line}</div>
      </div>
      <div class="verdict-conf">Confidence: {j['confidence'].title()}</div>
    </div>
    <div class="verdict-body">
      <p>I weighed three independent classical methods cast for the exact moment you asked —
      KP (the sharpest for a yes/no), then the Prashna chart, then Jamakkol timing — and let the
      stronger testimony carry the most weight. Together they give a verdict of <strong>{word}</strong>.</p>
      <p style="color:var(--text-dim);font-size:0.86rem;">{rad_line}
      <span title="internal weighting">(internal confidence score {j['total']:+.2f} on a −1…+1 scale)</span></p>
      <div class="score-row">
        {card("Jamakkol", jam, jam_note)}
        {card("Prashna Kundali", pra, pra_note)}
        {card("KP Horary", kp, kp_note)}
      </div>
    </div>
  </div>
</div>"""


def _timing(data: dict, j: dict) -> str:
    rp = data["ruling_planets"]["all_ruling_planets"]
    topic = data["meta"]["detected_topic"]
    karakas = TOPIC_KARAKA.get(topic, TOPIC_KARAKA["general"])
    jup = data["planets"]["Jupiter"]
    items = []
    items.append(
        f"<div class='tl-item tl-key'><div class='tl-date'>Ruling-Planet periods ★</div>"
        f"<div class='tl-title'>Activation by the Ruling Planets — {', '.join(rp)}</div>"
        f"<div class='tl-desc'>In KP, the matter ripens during the daśā/bhukti or transit of the "
        f"Ruling Planets. Watch the periods and transits of <strong>{', '.join(rp)}</strong>; "
        f"these are the planets most likely to trigger the event described above.</div></div>")
    kar_in_rp = [k for k in karakas if k in rp]
    if kar_in_rp:
        items.append(
            f"<div class='tl-item'><div class='tl-date'>Karaka window</div>"
            f"<div class='tl-title'>{', '.join(kar_in_rp)} — natural significator of the topic, also a Ruling Planet</div>"
            f"<div class='tl-desc'>Because the topic's natural significator is also ruling now, its sub-period "
            f"is the most precise trigger for movement on the question.</div></div>")
    items.append(
        f"<div class='tl-item'><div class='tl-date'>Jupiter transit</div>"
        f"<div class='tl-title'>Jupiter currently in sidereal {jup['sign']}</div>"
        f"<div class='tl-desc'>Jupiter's change of sign and its aspect onto the relevant houses mark broad "
        f"chapter-shifts for the matter. Note the months when Jupiter aspects the "
        f"{ordinal(j['prashna']['primary_bhava'])} house of the question.</div></div>")
    note = ("<div class='card' style='margin-bottom:1.2rem'><p style='font-size:0.82rem;color:var(--text-dim)'>"
            "These are <strong>symbolic windows of heightened potential</strong> based on the Ruling Planets and "
            "transits — exact dates require the querent's natal Vimśottarī daśā sequence. They use "
            "<strong>sidereal (Lahiri)</strong> positions and are <strong>not</strong> the same calendar as the "
            "Western Tropical horary report for the same question.</p></div>")
    return (f"<div class='section'><div class='section-title'>Astrological Timing Windows</div>"
            f"{note}<div class='timeline'>{''.join(items)}</div></div>")


def _remedies(data: dict, j: dict) -> str:
    topic = data["meta"]["detected_topic"]
    karakas = TOPIC_KARAKA.get(topic, TOPIC_KARAKA["general"])
    # Strengthen: topic karaka + topic-house lord. Pacify: malefics afflicting the matter.
    pra = j["prashna"]
    strengthen = list(dict.fromkeys(karakas + [pra["topic_lord"], pra["lagna_lord"]]))
    afflict = []
    tb = TOPIC_BHAVAS.get(topic, TOPIC_BHAVAS["general"])
    for p, h in data["houses"].items():
        if h in tb["denying"] and p in NATURAL_MALEFIC:
            afflict.append(p)

    def remedy_list(planets):
        lis = []
        for p in planets:
            if p not in PLANET_REMEDY:
                continue
            dev, day, mantra, gem, act = PLANET_REMEDY[p]
            lis.append(f"<li><strong>{p} ({dev}):</strong> chant <em>{mantra}</em> 108× on {day}; {act}. "
                       f"Supportive gem: {gem} (only after consulting an astrologer).</li>")
        return "".join(lis) or "<li>Maintain steady devotion and ethical effort.</li>"

    return f"""
<div class="section">
  <div class="section-title">Astrological Remedies</div>
  <div class="remedy-grid">
    <div class="remedy-card">
      <h4>Strengthen — supporters of the matter</h4>
      <ul class="remedy-list">{remedy_list(strengthen)}</ul>
    </div>
    <div class="remedy-card">
      <h4>Pacify — planets obstructing the matter</h4>
      <ul class="remedy-list">{remedy_list(afflict) if afflict else '<li>No malefic strongly obstructs the relevant houses — no special pacification needed.</li>'}</ul>
    </div>
  </div>
</div>"""


def _disclaimer(topic: str) -> str:
    if topic in ("health", "disease", "children"):
        extra = ("It is NOT a substitute for qualified medical, neurological, or psychological "
                 "evaluation. All health decisions must be made with licensed healthcare professionals.")
    elif topic in ("litigation", "loan", "finance"):
        extra = ("It is NOT legal or financial advice. Consult qualified legal and financial "
                 "professionals before acting.")
    else:
        extra = ("Astrology offers a probabilistic, symbolic perspective only; outcomes depend on "
                 "effort, free will, and circumstances beyond any chart.")
    return (f"<div class='disclaimer'><strong>Educational Purpose Only.</strong> This Prashna (Horary) "
            f"report is prepared for educational and contemplative purposes. {extra} The timing windows "
            f"are astrological correlations and carry no guarantee of outcome.</div>")


def render(data: dict, j: dict) -> str:
    meta = data["meta"]
    lg = data["lagna"]
    q = html.escape(meta["question"])
    topic = meta["detected_topic"]
    word, mood, _ = VERDICT_TEXT[j["verdict"]]
    badge_cls = {"good": "chip-favorable", "mixed": "chip-conditional", "bad": "chip-challenging"}[mood]
    hero_meta = "".join(
        f"<div class='pill'><strong>{lbl}:</strong> {val}</div>" for lbl, val in [
            ("Time", f"{meta['q_time_ist']} IST, {meta['q_date']}"),
            ("Location", f"{meta['location']} ({meta['lat']}°N {meta['lon']}°E)"),
            ("Prashna Lagna", f"{lg['sign']} {fmt_deg(lg['degree'])} ({lg['nakshatra']})"),
            ("Topic", topic.title()),
        ])

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Prashna (Horary) Report — {q}</title>
<style>{_css()}</style></head>
<body>
<div class="hero"><div class="container">
  <div class="tag">Horary · Prashna Jyotish</div>
  <h1>{q}</h1>
  <div class="sub">Confluence of three classical horary systems — KP · Jamakkol Prasanam · Prashna Kundali</div>
  <div class="meta-grid">{hero_meta}</div>
  <div style="margin-top:1rem"><span class="verdict-chip {badge_cls}" style="font-size:0.95rem">Verdict: {word} · Confidence {j['confidence'].title()}</span></div>
</div></div>

<div class="container">

{_plain_reading(data, j)}

<div class="section">
  <div class="section-title">Prashna Chart — Calculation Details</div>
  <div class="card" style="padding:0;overflow:hidden;margin-bottom:1rem">{_planet_table(data)}</div>
  <p style="font-size:0.78rem;color:var(--text-dim);margin-bottom:1rem">
    Sidereal Lahiri ayanāṁśa {lg.get('ayanamsa','')}° · whole-sign houses from {lg['sign']} Lagna ·
    source: {lg.get('asc_source','computed')}.</p>
  {_house_table(data, j)}
</div>

<div class="section">
  <div class="section-title">Analysis — Three Independent Systems</div>
  {_jamakkol_card(data, j['jamakkol'])}
  {_prashna_card(data, j['prashna'])}
  {_kp_card(data, j['kp'])}
</div>

{_confluence(data, j)}
{_timing(data, j)}
{_remedies(data, j)}

<div class="section">
  <div class="section-title">Disclaimer</div>
  {_disclaimer(topic)}
</div>

</div>
<footer><div class="container">
  Prashna chart cast for {meta['q_time_ist']} IST, {meta['q_date']}, {meta['location']} ·
  {lg['sign']} {fmt_deg(lg['degree'])} Lagna ({lg['nakshatra']}) · Lahiri ayanāṁśa {lg.get('ayanamsa','')}°<br>
  Systems: Jamakkol Prasanam · Prashna Kundali Siddhanta · KP Horary (cuspal sub-lord + Ruling Planets)<br>
  Generated: {meta['q_date']}
</div></footer>
</body></html>"""


# Map internal verdict to the DONE.json / frontend contract.
VERDICT_TO_DONE = {"YES": "YES", "LIKELY": "LIKELY", "UNCERTAIN": "UNCERTAIN",
                   "UNLIKELY": "UNLIKELY", "NO": "NO"}


def _vedic_customer_summary(data: dict, j: dict) -> dict:
    """Everything the customer-facing confluence answer (horary_answer.py) needs,
    already reduced to plain sentences and short planet lists — no engine
    internals (house tables, dignity scores, checklists) leak past this point.
    """
    jam, pra, kp = j["jamakkol"], j["prashna"], j["kp"]
    jk = data["jamakkol"]
    rp = data["ruling_planets"]["all_ruling_planets"]
    topic = data["meta"]["detected_topic"]
    karakas = TOPIC_KARAKA.get(topic, TOPIC_KARAKA["general"])
    tb = TOPIC_BHAVAS.get(topic, TOPIC_BHAVAS["general"])

    strengthen = list(dict.fromkeys(karakas + [pra["topic_lord"], pra["lagna_lord"]]))[:4]
    pacify = [p for p, h in data["houses"].items() if h in tb["denying"] and p in NATURAL_MALEFIC][:4]

    # A simple, defensible net score per planet from the three systems' own
    # structured signals — not a re-interpretation, just a tally of what each
    # system already flagged as helping or hurting.
    net: dict[str, int] = {}

    def _bump(names, weight):
        if not weight:
            return
        for n in names:
            if n:
                net[n] = net.get(n, 0) + weight

    if kp.get("available"):
        _bump([kp["sub_lord"]], 2 if kp["label"] == "YES" else (-2 if kp["label"] == "NO" else 0))
        _bump(rp[:3], 1)
    _bump(pra.get("benefics_in_kendra", []), 1)
    _bump(pra.get("malefics_in_lagna", []), -1)
    _bump([pra["lagna_lord"]], 1 if pra["label"] == "YES" else (-1 if pra["label"] == "NO" else 0))
    conj = jk.get("kavippu_conjunct_planets") or []
    _bump(conj, -1 if jam["label"] in ("NO", "CONDITIONAL") else (1 if jam["label"] == "YES" else 0))

    favour_planets = [p for p, v in sorted(net.items(), key=lambda kv: -kv[1]) if v > 0][:5]
    against_planets = [p for p, v in sorted(net.items(), key=lambda kv: kv[1]) if v < 0][:5]

    jup_sign = data["planets"]["Jupiter"]["sign"]
    timing_lines = [
        f"Ruling-Planet periods — watch {', '.join(rp[:4])}; their daśā/bhukti or transit tends to trigger movement.",
    ]
    kar_in_rp = [k for k in karakas if k in rp]
    if kar_in_rp:
        names = ", ".join(kar_in_rp)
        if len(kar_in_rp) == 1:
            timing_lines.append(
                f"{names} is both the topic's natural karaka and a Ruling Planet right now — "
                f"its period is the sharpest trigger.")
        else:
            timing_lines.append(
                f"{names} are both topic karakas and Ruling Planets right now — "
                f"their periods are the sharpest triggers.")
    else:
        timing_lines.append(
            f"Jupiter is currently in sidereal {jup_sign} — its next sign change marks a broader "
            f"chapter-shift for the matter.")

    return {
        "jamakkol": {"label": jam["label"], "plain": _jamakkol_plain_text(jam, jk)},
        "prashna": {"label": pra["label"], "plain": _prashna_plain_text(pra)},
        "kp": {"label": kp["label"], "plain": _kp_plain_text(kp), "available": kp.get("available", False)},
        "rp": rp,
        "favour_planets": favour_planets,
        "against_planets": against_planets,
        "strengthen_planets": strengthen,
        "pacify_planets": pacify,
        "timing_lines": timing_lines[:2],
    }


def generate_vedic_horary_html(question: str, q_date: str, q_time: str,
                               location: str = "New Delhi",
                               kp_number: str = "",
                               area: str = "") -> tuple[str, dict]:
    """Deterministic Vedic prashna report. Returns (html, judgment dict)."""
    data = precompute_horary(question, q_date, q_time, location,
                             kp_number or "", area=area)
    j = judge_vedic(data)
    html_doc = render(data, j)
    j_out = {
        "verdict": VERDICT_TO_DONE.get(j["verdict"], j["verdict"]),
        "confidence": j["confidence"],
        "score": j["total"],
        "systems": {
            "jamakkol": j["jamakkol"]["label"],
            "prashna": j["prashna"]["label"],
            "kp": j["kp"]["label"],
        },
        "topic": data["meta"]["detected_topic"],
        "customer": _vedic_customer_summary(data, j),
    }
    return html_doc, j_out


def main() -> None:
    ap = argparse.ArgumentParser(description="Deterministic Vedic horary/prashna report (no LLM)")
    ap.add_argument("question")
    ap.add_argument("q_date", help="YYYY-MM-DD")
    ap.add_argument("q_time", help="HH:MM (24h IST)")
    ap.add_argument("location", nargs="?", default="New Delhi")
    ap.add_argument("kp_number", nargs="?", default="")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    html_doc, j = generate_vedic_horary_html(args.question, args.q_date, args.q_time,
                                             args.location, args.kp_number)
    out = Path(args.out) if args.out else BASE_DIR / "reports" / "VedicHorary_preview.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_doc, encoding="utf-8")
    print(f"verdict={j['verdict']} confidence={j['confidence']} score={j['score']:+.2f} "
          f"systems={j['systems']}")
    print(f"written → {out}")


if __name__ == "__main__":
    main()
