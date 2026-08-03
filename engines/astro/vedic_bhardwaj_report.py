#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vedic_bhardwaj_report.py - Deterministic predictive report from Krishan Kant Bhardwaj's
The Complete Book of Indian Predictive Astrology (2021). Standalone lane: no rules1-38,
no LLM. Book text lives in bhardwaj_book_data.json (build via build_bhardwaj_data.py).

Sections: lagna personality, birth nakshatra, planets-in-houses, house-lord placements,
yogas (Nabhas subset, Gajakesari, Panchmahapurusha, Manglik, etc.), Vimshottari dasha
(book principles), gochar (Swiss Ephemeris sidereal Lahiri), classical remedies.

Usage:
    python3 vedic_bhardwaj_report.py <name> <YYYY-MM-DD> [--precomputed path.json]
    python3 vedic_bhardwaj_report.py <name> <YYYY-MM-DD> --time HH:MM --lat ... --lon ... --tz ...
"""
from __future__ import annotations

import argparse
import html
import json
import re
from datetime import date, datetime
from pathlib import Path

from astro_precompute import resolve_precompute
from chart_resolve import add_chart_source_args, chart_kwargs_from_args

from bhardwaj_semantic import (
    BhardwajSemanticEngine,
    DOMAIN_TITLE,
    build_chart_signals,
    Cluster,
)
from goel_disease_analysis import analyze_disease_chart
from goel_disease_prose import render_disease_section
from goel_navamsha_analysis import analyze_navamsha_chart
from goel_navamsha_prose import render_navamsha_section
from goel_dashamsha_analysis import analyze_dashamsha_chart
from goel_dashamsha_prose import render_dashamsha_section
from blind_chart_analysis import analyze_blind_chart
from blind_chart_prose import render_blind_chart_section
from goel_trishamsha_analysis import analyze_trishamsha_chart
from goel_trishamsha_prose import render_trishamsha_section
from goel_saptamsha_analysis import analyze_saptamsha_chart
from goel_saptamsha_prose import render_saptamsha_section
from bhardwaj_prose import (
    gochar_narrative,
    nakshatra_narrative,
    remedy_narrative,
    synthesize_domain_narrative,
    synthesize_period_narrative,
    yoga_narrative,
    year_ahead_narrative,
)
from boney_divisional_timing import render_boney_dasha_bridge, render_boney_varga_goel_bridge, score_active_period
from gk_transit_dasha import render_gk_gochar_bridge, render_gk_transit_dasha_block, score_transit_dasha_synergy

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "bhardwaj_book_data.json"

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}
MOVABLE = {"Aries", "Cancer", "Libra", "Capricorn"}
FIXED = {"Taurus", "Leo", "Scorpio", "Aquarius"}
DUAL = {"Gemini", "Virgo", "Sagittarius", "Pisces"}
KENDRA = {1, 4, 7, 10}
TRIKONA = {1, 5, 9}
BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
STRONG_DIGNITY = {"exalted", "own_sign", "moolatrikona", "great_friend_sign"}
WEAK_DIGNITY = {"debilitated", "enemy_sign"}
HOUSE_TOPIC = {
    1: "self, body & temperament", 2: "wealth, speech & family", 3: "courage, siblings & skills",
    4: "home, mother & property", 5: "children, education & creativity", 6: "service, enemies & health",
    7: "marriage & partnerships", 8: "longevity, inheritance & hidden matters", 9: "fortune, dharma & father",
    10: "career & public status", 11: "gains & fulfilment of desires", 12: "expenses, foreign lands & moksha",
}
REMEDIES = {
    "Sun": "Surya remedies (Bhardwaj): Sunday worship, Surya Namaskar, ruby only if advised, "
           "donate wheat/jaggery on Sundays, respect father and authority.",
    "Moon": "Chandra remedies: Monday fast or simple white-food meal, pearl only if suitable, "
            "serve mother/elderly women, keep emotions steady.",
    "Mars": "Mangal remedies: Hanuman worship on Tuesdays, donate masoor dal/red cloth, channel anger into sport/work.",
    "Mercury": "Budh remedies: Wednesday green charity, study and honest speech, emerald only if suitable.",
    "Jupiter": "Guru remedies: Thursday yellow charity, teaching/mentoring, respect teachers and dharma.",
    "Venus": "Shukra remedies: Friday white sweets charity, arts and harmony in relationships.",
    "Saturn": "Shani remedies: Saturday service to poor/elderly, discipline and patience, blue sapphire only if suitable.",
    "Rahu": "Rahu remedies: Durga/Chandi path, avoid intoxicants and speculation, hessonite if suitable.",
    "Ketu": "Ketu remedies: Ganesha worship, meditation, cat's eye only if suitable, reduce restlessness.",
}


def _e(s) -> str:
    return html.escape(str(s))


def _ord(n: int) -> str:
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n if n < 20 else n % 10, 'th')}"


def house_of(sign: str, lagna: str) -> int:
    return (SIGNS.index(sign) - SIGNS.index(lagna)) % 12 + 1


def _load_book() -> dict:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Run build_bhardwaj_data.py first  missing {DATA_PATH}")
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _pd(iso: str) -> date:
    return datetime.strptime(iso[:10], "%Y-%m-%d").date()


def _dmy(d: date) -> str:
    return d.strftime("%d %b %Y").lstrip('0')


def _clip(text: str, n: int = 480) -> str:
    text = " ".join(text.split())
    if len(text) <= n:
        return text
    return text[: n - 1].rsplit(" ", 1)[0] + "..."


class BhardwajChart:
    def __init__(self, pc: dict, book: dict):
        self.pc = pc
        self.book = book
        self.lagna = pc["meta"]["lagna_sign"]
        self.lagna_idx = SIGNS.index(self.lagna)
        self.name = pc["meta"]["client"]
        self.age = int(pc["meta"]["age"])
        self.moon_sign = pc["planets"]["Moon"]["sign"]
        self.moon_nak = pc["planets"]["Moon"].get("nakshatra", "")
        self.planets: dict = {}
        for nm, v in pc["planets"].items():
            self.planets[nm] = {
                "sign": v["sign"],
                "house": house_of(v["sign"], self.lagna),
                "dignity": v.get("dignity", "neutral_sign"),
                "nakshatra": v.get("nakshatra", ""),
                "retro": bool(v.get("retrograde", False)),
            }
        self.rules: dict[str, list[int]] = {p: [] for p in self.planets}
        self.houses: dict[int, dict] = {}
        for h in range(1, 13):
            sign = SIGNS[(self.lagna_idx + h - 1) % 12]
            lord = SIGN_LORD[sign]
            self.houses[h] = {
                "sign": sign,
                "lord": lord,
                "tenants": [nm for nm, pl in self.planets.items() if pl["sign"] == sign],
            }
            if lord in self.rules:
                self.rules[lord].append(h)
        self.cur_md = pc["vimshottari"]["current_md"]
        self.antars = pc["vimshottari"]["current_md_antardashas"]

    def personality_sign(self) -> str:
        """Book: stronger of lagna vs moon sign  use lagna primary, moon as modifier."""
        lagna_txt = self.book["lagna_signs"].get(self.lagna, "")
        moon_txt = self.book["lagna_signs"].get(self.moon_sign, "")
        parts = []
        if lagna_txt:
            parts.append(
                f"<p class='pred'><strong>{self.lagna} ascendant (Bhardwaj):</strong> "
                f"{_e(_clip(lagna_txt, 650))}</p>"
            )
        if moon_txt and self.moon_sign != self.lagna:
            parts.append(
                f"<p class='pred'><strong>{self.moon_sign} birth Moon-sign tone:</strong> "
                f"{_e(_clip(moon_txt, 420))}</p>"
            )
        if not parts:
            parts.append("<p class='pred'>Lagna sign text not found in book corpus.</p>")
        return "".join(parts)

    def nakshatra_section(self) -> str:
        gand = self.book.get("gandmool_nakshatras", [])
        nk = self.moon_nak
        is_gand = any(g.lower() in nk.lower() for g in gand)
        bits = [f"<p class='pred'>Birth nakshatra (Moon): <strong>{_e(nk)}</strong>.</p>"]
        if is_gand:
            bits.append(
                "<p class='pred tag-warn-inline'><strong>Gandmool nakshatra</strong>  Bhardwaj notes "
                "Gandant births need Shanti; peace ritual when Moon transits the same nakshatra (often ~28th day rule).</p>"
            )
        fx = self.book.get("nakshatra_effects", {}).get(nk, "")
        if fx:
            bits.append(f"<p class='pred'>{_e(_clip(fx, 500))}</p>")
        return "".join(bits)

    def planet_house_predictions(self) -> str:
        pih = self.book.get("planet_in_house", {})
        rows = []
        for pl in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
            info = self.planets[pl]
            h = info["house"]
            txt = pih.get(str(h), {}).get(pl, "")
            dig = info["dignity"].replace("_", " ")
            rows.append(
                f"<tr><td><strong>{pl}</strong></td><td>{_ord(h)} ({info['sign']})</td>"
                f"<td>{_e(dig)}</td>"
                f"<td>{_e(_clip(txt, 320) if txt else 'See book chapter for this house placement.')}</td></tr>"
            )
        return (
            "<table class='simple'><tr><th>Planet</th><th>House</th><th>Dignity</th>"
            "<th>Bhardwaj prediction (house placement)</th></tr>"
            + "".join(rows) + "</table>"
        )

    def house_lord_section(self) -> str:
        hlh = self.book.get("house_lord_in_house", {})
        paras = []
        for h in range(1, 13):
            lord = self.houses[h]["lord"]
            occ = self.planets[lord]["house"]
            txt = hlh.get(str(h), {}).get(str(occ), "")
            ruled = " & ".join(_ord(x) for x in self.rules.get(lord, []))
            lead = (
                f"<p class='pred'><strong>{_ord(h)} lord {lord}</strong> (rules {ruled or ''}) "
                f"sits in the <strong>{_ord(occ)} house</strong> ({HOUSE_TOPIC[occ]})."
            )
            if txt:
                lead += f" {_e(_clip(txt, 380))}"
            else:
                lead += " (Detailed lord-in-house text: grep Bhardwaj OCR for this lord.)"
            lead += "</p>"
            paras.append(lead)
        return "".join(paras)

    def detect_yogas(self) -> list[dict]:
        found: list[dict] = []
        pl = self.planets
        moon_h = pl["Moon"]["house"]
        jup_h = pl["Jupiter"]["house"]
        if abs((jup_h - moon_h) % 12) in (0, 3, 6, 9):
            if pl["Jupiter"]["dignity"] not in WEAK_DIGNITY:
                found.append({
                    "name": "Gajakesari Yoga",
                    "result": "Rich, brave, meritorious, virtuous, royal favour (Bhardwaj).",
                })

        for yname, spec in self.book.get("panchmahapurusha", {}).items():
            p = spec["planet"]
            if pl[p]["house"] not in spec["houses"]:
                continue
            if pl[p]["sign"] in spec["signs"] or pl[p]["dignity"] in STRONG_DIGNITY:
                found.append({"name": f"Panchmahapurusha - {yname}", "result": spec["result"]})

        m_h = pl["Mars"]["house"]
        if m_h in (1, 4, 7, 8, 12):
            found.append({
                "name": "Manglik Dosha",
                "result": "Mars in 1/4/7/8/12  marriage delay/obstacles unless cancelled; "
                          "Bhardwaj treats with Ashtkoot matching and remedies.",
            })

        signs_occupied = {pl[p]["sign"] for p in pl if p not in ("Rahu", "Ketu")}
        if signs_occupied <= MOVABLE and len(signs_occupied) >= 5:
            found.append({"name": "Nabhas  Rajju Yoga", "result": "Travel-loving, changeable, foreign links."})
        if signs_occupied <= FIXED and len(signs_occupied) >= 5:
            found.append({"name": "Nabhas  Moosal Yoga", "result": "Stable, respected, wealthy, royal favour."})
        if signs_occupied <= DUAL and len(signs_occupied) >= 5:
            found.append({"name": "Nabhas  Nal Yoga", "result": "Rich, skilled with siblings, beautiful."})

        tenth = (self.lagna_idx + 9) % 12
        tenth_sign = SIGNS[tenth]
        tenants_10 = [p for p, v in pl.items() if v["sign"] == tenth_sign]
        if tenants_10 and all(p in BENEFICS for p in tenants_10):
            found.append({"name": "Amla Yoga", "result": "Famous, royal, benevolent, talented (10th from lagna)."})

        ll = SIGN_LORD[self.lagna]
        bh_lord = SIGN_LORD[SIGNS[(self.lagna_idx + 8) % 12]]
        if pl[ll]["dignity"] in STRONG_DIGNITY and pl[bh_lord]["house"] in KENDRA | TRIKONA:
            if pl[bh_lord]["dignity"] in STRONG_DIGNITY:
                found.append({"name": "Lakshmi Yoga", "result": "Beautiful, religious, wealthy, blessed with progeny."})

        b6 = [(self.lagna_idx + 5) % 12, (self.lagna_idx + 6) % 12, (self.lagna_idx + 7) % 12]
        lagna_adhi = all(
            any(pl[p]["sign"] == SIGNS[i] for p in BENEFICS)
            and not any(pl[p]["sign"] == SIGNS[i] for p in MALEFICS)
            for i in b6
        )
        if lagna_adhi:
            found.append({"name": "Lagnadhi Yoga", "result": "Humble, learned, successful, happy (benefics 6-8 from lagna)."})

        return found

    def yoga_section(self) -> str:
        yogas = self.detect_yogas()
        if not yogas:
            return "<p class='pred'>No major Bhardwaj yoga flag detected in this quick scan  full Nabhas needs all seven planets.</p>"
        items = "".join(
            f"<li><strong>{_e(y['name'])}:</strong> {_e(y['result'])}</li>" for y in yogas
        )
        return f"<ul>{items}</ul>"

    def dasha_section(self) -> str:
        cur = next((a for a in self.antars if a.get("status") == "current"), None)
        md = self.cur_md["md_lord"]
        ad = cur["ad_lord"] if cur else md
        principles = "".join(f"<li>{_e(p)}</li>" for p in self.book.get("dasha_principles", []))
        pih = self.book.get("planet_in_house", {})

        def lord_reading(p: str) -> str:
            h = self.planets[p]["house"]
            ruled = self.rules.get(p, [])
            occ_txt = pih.get(str(h), {}).get(p, "")
            ruled_txt = ", ".join(_ord(x) for x in ruled) if ruled else ""
            return (
                f"<strong>{p}</strong> rules {ruled_txt}, occupies {_ord(h)} "
                f"({HOUSE_TOPIC[h]}). {_e(_clip(occ_txt, 280))}"
            )

        body = (
            f"<p class='pred'>Current <strong>{md}</strong> mahadasha until "
            f"<strong>{_dmy(_pd(self.cur_md['end']))}</strong>"
            + (f"; antardasha <strong>{ad}</strong> until <strong>{_dmy(_pd(cur['end']))}</strong>."
               if cur else ".")
            + "</p>"
            f"<p class='pred'>{lord_reading(md)}</p>"
        )
        if ad != md:
            body += f"<p class='pred'>Antardasha lord: {lord_reading(ad)}</p>"
        boney_period = score_active_period(md, ad, self.pc)
        body += render_boney_dasha_bridge(boney_period)
        gk_synergy = score_transit_dasha_synergy(md=md, ad=ad, pc=self.pc)
        body += render_gk_transit_dasha_block(gk_synergy)
        body += f"<p class='fine'>Bhardwaj dasha principles:</p><ul>{principles}</ul>"
        return body

    def gochar_section(self) -> str:
        try:
            import swisseph as swe
        except ImportError:
            return "<p class='pred'>Install pyswisseph for live gochar section.</p>"

        swe.set_sid_mode(swe.SIDM_LAHIRI)
        jd = swe.julday(date.today().year, date.today().month, date.today().day, 12.0)
        bodies = {
            "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
            "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN,
            "Rahu": swe.TRUE_NODE,
        }
        ref = self.moon_sign  # Chandra lagna primary per Bhardwaj / Phaladeepika
        ref_idx = SIGNS.index(ref)
        aus_tbl = self.book.get("gochar_auspicious", {})
        inaus_tbl = self.book.get("gochar_inauspicious", {})
        rows = []
        for name, pid in bodies.items():
            lon = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)[0][0]
            sign = SIGNS[int(lon // 30) % 12]
            pos = (SIGNS.index(sign) - ref_idx) % 12 + 1
            birth = self.planets.get(name, {})
            strong = birth.get("dignity", "") in STRONG_DIGNITY
            weak = birth.get("dignity", "") in WEAK_DIGNITY
            if pos in aus_tbl.get(name, []):
                tone = "auspicious gochar house"
                if weak:
                    tone += " (birth weak  muted benefit per Bhardwaj rule 1)"
                elif strong:
                    tone += " (birth strong  full benefit)"
            elif pos in inaus_tbl.get(name, []):
                tone = "inauspicious gochar house"
                if strong:
                    tone += " (birth strong  resisted per rule 2)"
                elif weak:
                    tone += " (birth weak  sharper stress)"
            else:
                tone = "neutral transit band"
            rows.append(
                f"<tr><td>{name}</td><td>{sign}</td><td>{pos} from Moon ({ref})</td><td>{tone}</td></tr>"
            )
        rules = "".join(f"<li>{_e(r)}</li>" for r in self.book.get("transit_rules", []))
        return (
            f"<p class='pred'>Gochar counted from <strong>Chandra lagna ({ref})</strong> "
            f"as Bhardwaj emphasises Moon ascendant for transit (Phaladeepika).</p>"
            "<table class='simple'><tr><th>Planet</th><th>Sign today</th><th>House from Moon</th><th>Verdict</th></tr>"
            + "".join(rows) + "</table>"
            f"<ul>{rules}</ul>"
        )

    def domain_block(self, title: str, houses: set[int]) -> str:
        hits = []
        for pl, v in self.planets.items():
            if v["house"] in houses or any(h in houses for h in self.rules.get(pl, [])):
                pih = self.book.get("planet_in_house", {}).get(str(v["house"]), {}).get(pl, "")
                if pih:
                    hits.append(f"<li><strong>{pl}</strong> ({_ord(v['house'])}): {_e(_clip(pih, 200))}</li>")
        if not hits:
            return f"<p class='pred'>{title}: no strong book hit in mapped houses.</p>"
        return f"<h2>{title}</h2><ul>{''.join(hits[:5])}</ul>"

    def remedies_section(self) -> str:
        items = []
        for pl, v in self.planets.items():
            if v["dignity"] in WEAK_DIGNITY or v["house"] in (6, 8, 12):
                items.append(f"<li>{REMEDIES.get(pl, pl)}</li>")
        if not items:
            items.append("<li>No acute Bhardwaj remedy flag  maintain simple weekly planet-day discipline.</li>")
        return "<ul>" + "".join(items[:7]) + "</ul>"


def _badge(conf: str) -> str:
    cls = {"HIGH": "hi", "MODERATE": "mod", "LOW": "lo", "SPECULATIVE": "sp"}.get(conf, "mod")
    return f'<span class="badge {cls}">{conf}</span>'


def _cluster_card(cl: Cluster, members: list, chart: "BhardwajChart") -> str:
    tone = "green" if cl.direction == "positive" else ("amber" if cl.direction == "caution" else "neutral")
    timing = f'<p class="fine">Active timing: {_e(cl.timing)}</p>' if cl.timing else ""
    body = synthesize_domain_narrative(cl, members, chart)
    return f"""
<div class="pred-card {tone}">
  <div class="pred-head">{_e(DOMAIN_TITLE.get(cl.domain, cl.domain.title()))} {_badge(cl.confidence)}</div>
  <div class="pred-body">{_e(body)}</div>
  {timing}
</div>"""


def _gochar_affirmation(chart: "BhardwajChart", engine: BhardwajSemanticEngine) -> str:
    try:
        import swisseph as swe
    except ImportError:
        return "<p class='pred'>Install pyswisseph for live gochar narrative.</p>"

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(date.today().year, date.today().month, date.today().day, 12.0)
    ref = chart.moon_sign
    ref_idx = SIGNS.index(ref)
    aus = chart.book.get("gochar_auspicious", {})
    inaus = chart.book.get("gochar_inauspicious", {})
    lines: list[str] = [
        f"Today's sky is read from your Moon sign {ref}, as Bhardwaj follows classical gochar on Chandra lagna.",
    ]
    for name, pid in {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
        "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN,
    }.items():
        lon = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)[0][0]
        sign = SIGNS[int(lon // 30) % 12]
        pos = (SIGNS.index(sign) - ref_idx) % 12 + 1
        birth = chart.planets[name]
        dig = birth["dignity"].replace("_", " ")
        if pos in aus.get(name, []):
            lines.append(
                f"{name} transits your {_ord(pos)} house from Moon ({sign})  "
                f"an auspicious gochar band; natal {name} in the {_ord(birth['house'])} ({dig}) "
                f"shapes how strongly you receive this boost."
            )
        elif pos in inaus.get(name, []):
            lines.append(
                f"{name} crosses a stressed gochar house ({pos} from Moon); "
                f"birth {name} in the {_ord(birth['house'])} ({dig}) sets how sharply you feel it."
            )
    return f'<div class="callout">{_e(" ".join(lines[:5]))}</div>'


def _remedy_cards(chart: "BhardwajChart", engine: BhardwajSemanticEngine) -> str:
    cards = []
    for pl, v in chart.planets.items():
        if v["dignity"] not in WEAK_DIGNITY and v["house"] not in (6, 8, 12):
            continue
        book_line = lookup_planet_house(chart.book, pl, v["house"], v["dignity"], "caution")
        anchor = (
            f"Your {pl} needs classical support ({v['dignity'].replace('_', ' ')} "
            f"in the {_ord(v['house'])} house)."
        )
        remedy = REMEDIES.get(pl, "")
        body = anchor
        if remedy:
            body += f" {remedy}"
        cards.append(f'<div class="pred-card amber"><div class="pred-body">{_e(body)}</div></div>')
    if not cards:
        cards.append(
            '<div class="pred-card neutral"><div class="pred-body">'
            "Your chart does not flag acute classical remedy pressure on weak dusthana lords right now. "
            "Maintain simple weekly planet-day discipline and charity."
            "</div></div>"
        )
    return "".join(cards[:5])


def _css() -> str:
    return """
body{font-family:Georgia,serif;max-width:46rem;margin:auto;padding:1.5rem;line-height:1.62;color:#1a1a1a}
.card{background:#fff;border:1px solid #ddd;border-radius:8px;padding:1.25rem 1.75rem}
h1{font-size:1.22rem;color:#4e342e;margin-top:1.5rem}
.lead{font-size:1.03rem;color:#444}
.pred{margin:.65rem 0}
.fine{font-size:.86rem;color:#666;margin:.35rem 0 0}
.meta{display:grid;grid-template-columns:auto 1fr;gap:.25rem .75rem;font-size:.92rem}
.meta dt{font-weight:600;color:#5d4037}
.note{font-size:.85rem;color:#666;border-top:1px solid #eee;margin-top:1.5rem;padding-top:.75rem}
.callout{background:#fff8e1;border-left:4px solid #ff8f00;padding:.9rem 1rem;margin:1rem 0;border-radius:4px}
.hero{background:linear-gradient(135deg,#fff8e1,#fff3e0);border-left:4px solid #e65100;padding:1rem 1.15rem;margin:1rem 0;border-radius:4px;font-size:1.05rem}
.pred-card{border:1px solid #e0e0e0;border-radius:6px;padding:.85rem 1rem;margin:.75rem 0}
.pred-card.green{border-left:4px solid #2e7d32;background:#f1f8f4}
.pred-card.amber{border-left:4px solid #f9a825;background:#fffde7}
.pred-card.neutral{border-left:4px solid #78909c;background:#fafafa}
.pred-head{font-weight:600;color:#4e342e;margin-bottom:.45rem}
.pred-body{font-size:.98rem}
.badge{font-size:.72rem;font-weight:700;padding:.12rem .45rem;border-radius:3px;margin-left:.35rem;vertical-align:middle}
.badge.hi{background:#e8f5e9;color:#2e7d32}
.badge.mod{background:#fff8e1;color:#e65100}
.badge.lo{background:#ffebee;color:#c62828}
.badge.sp{background:#eceff1;color:#546e7a}
details.appendix{margin-top:1.25rem;font-size:.88rem}
table.simple{width:100%;border-collapse:collapse;font-size:.85rem}
table.simple th,table.simple td{border:1px solid #e0e0e0;padding:.4rem;vertical-align:top}
.tag-warn-inline{color:#e65100;font-weight:600}
"""


def render_semantic(
    chart: "BhardwajChart",
    clusters: list[Cluster],
    signals: list,
    engine: BhardwajSemanticEngine,
    pc: dict,
    dob_disp: str,
    tob: str = "",
    place: str = "",
    extracted_path: str = "",
) -> str:
    nm = _e(chart.name)
    today = date.today()
    by_dom = {c.domain: c for c in clusters}
    members_by_dom: dict[str, list] = {}
    for sig in signals:
        members_by_dom.setdefault(sig.domain, []).append(sig)

    hero_text = synthesize_period_narrative(chart, signals)

    domain_order = [
        "personality", "career", "finance", "marriage", "children",
        "health", "property", "travel", "spiritual", "current",
    ]
    domain_html = ""
    for dom in domain_order:
        cl = by_dom.get(dom)
        if cl:
            domain_html += _cluster_card(cl, members_by_dom.get(dom, []), chart)

    yoga_html = yoga_narrative(chart.detect_yogas())
    gand = nakshatra_narrative(chart)

    cur_ad = next((a for a in chart.antars if a.get("status") == "current"), None)
    boney_period = score_active_period(
        chart.cur_md["md_lord"],
        cur_ad["ad_lord"] if cur_ad else chart.cur_md["md_lord"],
        pc,
    )
    boney_varga_bridge_nav = render_boney_varga_goel_bridge(boney_period, focus="marriage")
    boney_varga_bridge_d10 = render_boney_varga_goel_bridge(boney_period, focus="career")
    gk_synergy = score_transit_dasha_synergy(
        md=chart.cur_md["md_lord"],
        ad=cur_ad["ad_lord"] if cur_ad else chart.cur_md["md_lord"],
        pc=pc,
    )
    gk_gochar_bridge = render_gk_gochar_bridge(gk_synergy)

    try:
        disease_analysis = analyze_disease_chart(pc)
        disease_html = render_disease_section(disease_analysis, pc)
    except FileNotFoundError:
        disease_html = (
            "<p class='pred'>Run <code>python3 build_goel_disease_data.py</code> "
            "to enable the Goel disease section.</p>"
        )

    try:
        nav_analysis = analyze_navamsha_chart(pc)
        navamsha_html = render_navamsha_section(nav_analysis, pc)
    except FileNotFoundError:
        navamsha_html = (
            "<p class='pred'>Run <code>python3 build_navamsha_data.py</code> "
            "to enable the Goel Navamsha section.</p>"
        )

    extract_text = ""
    female = False
    g = pc.get("meta", {}).get("gender", pc.get("gender"))
    if g is not None:
        female = g == 1 or g == "female"
    if extracted_path:
        extract_text = Path(extracted_path).read_text(encoding="utf-8", errors="ignore")
        if not female:
            female = bool(re.search(r"\bSex\s+Female\b", extract_text, re.I))
    try:
        sap_analysis = analyze_saptamsha_chart(pc, extract_text, female=female)
        saptamsha_html = render_saptamsha_section(sap_analysis, female=female)
    except Exception as exc:
        saptamsha_html = f"<div class='pred-card amber'><div class='pred-body'>{_e(str(exc))}</div></div>"

    try:
        d10_analysis = analyze_dashamsha_chart(pc, extract_text)
        dashamsha_html = render_dashamsha_section(d10_analysis)
    except Exception as exc:
        dashamsha_html = f"<div class='pred-card amber'><div class='pred-body'>{_e(str(exc))}</div></div>"

    try:
        d30_analysis = analyze_trishamsha_chart(pc, extract_text, female=female)
        trishamsha_html = render_trishamsha_section(d30_analysis)
    except Exception as exc:
        trishamsha_html = f"<div class='pred-card amber'><div class='pred-body'>{_e(str(exc))}</div></div>"

    try:
        blind_analysis = analyze_blind_chart(pc, extract_text, female=female)
        blind_chart_html = render_blind_chart_section(blind_analysis)
    except Exception as exc:
        blind_chart_html = f"<div class='pred-card amber'><div class='pred-body'>{_e(str(exc))}</div></div>"

    evidence_rows = ""
    for sig in signals[:24]:
        evidence_rows += (
            f"<tr><td>{_e(sig.source)}</td><td>{_e(sig.domain)}</td>"
            f"<td>{_e(_clip(sig.anchor or sig.text, 160))}</td></tr>"
        )

    body = f"""
<article class="card">
  <h1 style="margin-top:0;color:#4e342e;">Your Bhardwaj Reading</h1>
  <dl class="meta">
    <dt>Client</dt><dd>{nm}</dd>
    <dt>Born</dt><dd>{_e(dob_disp)}{('  ' + _e(tob)) if tob else ''}{('  ' + _e(place)) if place else ''}</dd>
    <dt>Map</dt><dd>{chart.lagna} rising  Moon {chart.moon_sign} ({_e(chart.moon_nak)})</dd>
    <dt>Dasha</dt><dd>{chart.cur_md['md_lord']} mahadasha</dd>
    <dt>Report</dt><dd>{today.strftime('%d %B %Y').lstrip('0')}</dd>
  </dl>
  <p class="lead">A personalised reading from <em>The Complete Book of Indian Predictive Astrology</em> (Krishan Kant Bhardwaj, 2021).
  Your birth chart is matched to the book line by line - written in plain language you can use in daily life.</p>

  <div class="hero">{_e(hero_text)}</div>

  <h1>Your year ahead</h1>
  {year_ahead_narrative(chart, pc)}

  <h1>Your Vimshottari dasha</h1>
  {chart.dasha_section()}

  <h1>Your life areas</h1>
  <p class="fine">Each section below combines your chart placements with Bhardwaj&apos;s predictions for those same positions.</p>
  {domain_html}

  <h1>Birth star</h1>
  {gand}

  <h1>Special yogas in your chart</h1>
  {yoga_html}

  <h1>Today&apos;s planetary transits (gochar)</h1>
  {gk_gochar_bridge}
  {gochar_narrative(chart)}

  <h1>Supportive remedies</h1>
  {remedy_narrative(chart)}

  <h1>Goel lanes &amp; blind chart (Nadi)</h1>
  <p class="fine">Goel book lanes - health (<em>Locate Disease</em>); marriage (<em>Navamsha</em>); children (<em>Saptamsha</em>);
  career (<em>Dashamsha</em>); fortune/adversity (<em>Trishamsha</em>).
  Blind chart lane: Guru Rajesh Nadi past-reconstruction from D1 karakas + Jupiter/Saturn progression.</p>

  <h2 style="font-size:1.05rem;margin-top:1rem">Health vulnerability map</h2>
  {disease_html}

  <h2 style="font-size:1.05rem;margin-top:1.25rem">Navamsha predictions</h2>
  {boney_varga_bridge_nav}
  {navamsha_html}

  <h2 style="font-size:1.05rem;margin-top:1.25rem">Saptamsha predictions (children)</h2>
  {saptamsha_html}

  <h2 style="font-size:1.05rem;margin-top:1.25rem">Dashamsha predictions (career)</h2>
  {boney_varga_bridge_d10}
  {dashamsha_html}

  <h2 style="font-size:1.05rem;margin-top:1.25rem">Trishamsha predictions (fortune &amp; adversity)</h2>
  {trishamsha_html}

  <h2 style="font-size:1.05rem;margin-top:1.25rem">Blind chart (Nadi - past &amp; life domains)</h2>
  {blind_chart_html}

  <details class="appendix">
    <summary>Chart signals used (technical)</summary>
    <table class="simple">
      <tr><th>Source</th><th>Domain</th><th>Chart fact</th></tr>
      {evidence_rows}
    </table>
  </details>

  <p class="note">Educational astrology only. Engine: all-MiniLM-L6-v2 + Bhardwaj OCR corpus. Rebuild corpus: <code>python3 build_bhardwaj_data.py</code>.</p>
</article>"""
    return (
        f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'/>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'/>"
        f"<title>Bhardwaj reading  {nm}</title><style>{_css()}</style></head><body>{body}</body></html>"
    )


def render(chart: BhardwajChart, dob_disp: str, tob: str = "", place: str = "") -> str:
    """Legacy alias  use render_semantic via generate_bhardwaj_html."""
    raise NotImplementedError("Use generate_bhardwaj_html()  semantic render only.")


def generate_bhardwaj_html(
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
    book = _load_book()
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
    chart = BhardwajChart(pc, book)
    engine = BhardwajSemanticEngine(book)
    signals = build_chart_signals(chart, pc)
    clusters = engine.cluster(signals)
    d = datetime.strptime(dob, "%Y-%m-%d").date()
    doc = render_semantic(
        chart, clusters, signals, engine, pc, d.strftime("%d %B %Y").lstrip('0'), tob, place,
        extracted_path or "",
    )
    cur = next((a for a in chart.antars if a.get("status") == "current"), None)
    summary = {
        "lagna": chart.lagna,
        "moon_sign": chart.moon_sign,
        "moon_nakshatra": chart.moon_nak,
        "yogas": [y["name"] for y in chart.detect_yogas()],
        "current_md": chart.cur_md["md_lord"],
        "current_ad": cur["ad_lord"] if cur else None,
        "signals": len(signals),
        "clusters": len(clusters),
        "corpus_chunks": len(engine.chunks),
    }
    return doc, summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Bhardwaj Complete Indian Predictive Astrology report")
    ap.add_argument("name")
    ap.add_argument("dob")
    ap.add_argument("extracted", nargs="?", default=None, help="Optional legacy AstroSage extract")
    add_chart_source_args(ap)
    ap.add_argument("--tob", default="")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    kw = chart_kwargs_from_args(args)
    doc, summary = generate_bhardwaj_html(
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
    out = Path(args.out) if args.out else BASE_DIR / "reports" / f"Bhardwaj_{args.name}_preview.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(f"signals={summary['signals']} clusters={summary['clusters']} corpus={summary['corpus_chunks']}")
    print(f"lagna={summary['lagna']} moon={summary['moon_sign']} yogas={summary['yogas']}")
    print(f"MD={summary['current_md']} AD={summary['current_ad']}")
    print(f"written -> {out}")


if __name__ == "__main__":
    main()
