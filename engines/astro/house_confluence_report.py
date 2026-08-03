#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
house_confluence_report.py — one report per house (and the planets/areas it
rules), read across every technique in confluence form.

For a chosen house (1..12) it shows:
  * the life-areas that house governs,
  * how each system (Parashari, Vimśottarī, Yoginī/Chara, KP, Jaimini,
    Aṣṭakavarga, Divisional, Transit, Longevity) reads that house — verdict
    + reading + timing,
  * one overall confluence score + confidence,
  * what to expect, and a remedy when the house looks weak.

Reuses the live multi-technique engine in ``client_question_engine`` so the
verdicts are the same ones the confluence/question reports rely on.

CLI:
    python3 house_confluence_report.py --house 1 \
        --name Ritesh --dob 1985-03-08 --time 13:05 --place "Patna, India"
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Optional

from astro_precompute import SIGNS
from client_question_engine import (
    HOUSE_KARAKAS,
    QuestionContext,
    evaluate_question_techniques,
    synthesize_answer,
)
from client_report_html import client_css, finalize_report_html

BASE_DIR = Path(__file__).resolve().parent


# ─────────────────────────── House significations ──────────────────────────
HOUSE_AREAS: dict[int, dict[str, Any]] = {
    1: {
        "title": "Self & Body",
        "domain": "personality",
        "areas": [
            "Your identity, character and the way the world first reads you",
            "The physical body, health and vitality",
            "Confidence, drive and how you begin things",
            "Overall fortune and the broad direction of your life",
        ],
        "summary": "The first house is you yourself — your body, your temperament, "
                   "your presence. It colours your whole chart: a strong first house "
                   "lets every other promise actually reach the ground.",
        "question": "How is my self, body, vitality and overall personality?",
    },
    2: {
        "title": "Wealth & Speech",
        "domain": "finance",
        "areas": [
            "Family wealth, savings and what you accumulate",
            "Speech, voice and the way you express yourself",
            "Face, eyes, teeth and what you eat",
            "Your early family and values",
        ],
        "summary": "The second house holds your money, your voice and your family "
                   "roots — what you save, what you say, and what you were taught to value.",
        "question": "How are my wealth, savings, speech and family values?",
    },
    3: {
        "title": "Courage & Siblings",
        "domain": "general",
        "areas": [
            "Courage, initiative and self-effort",
            "Brothers, sisters and close peers",
            "Communication, writing and hands-on skills",
            "Short travels and everyday hustle",
        ],
        "summary": "The third house is your nerve and your effort — the courage to "
                   "push, your siblings, your skills, and the short journeys of daily life.",
        "question": "How are my courage, siblings, skills and communication?",
    },
    4: {
        "title": "Home & Mother",
        "domain": "property",
        "areas": [
            "Mother and your emotional foundations",
            "Home, property, land and vehicles",
            "Inner peace and sense of security",
            "Schooling and early education",
        ],
        "summary": "The fourth house is your roots — mother, home, land and the inner "
                   "peace you carry. When it is strong, you feel settled wherever you go.",
        "question": "How are my home, property, mother and peace of mind?",
    },
    5: {
        "title": "Children & Mind",
        "domain": "children",
        "areas": [
            "Children and your bond with them",
            "Creativity, romance and the heart",
            "Intelligence, learning and memory",
            "Speculation and sudden gains",
        ],
        "summary": "The fifth house is your creative spark — children, romance, "
                   "intelligence and the things you make from the heart.",
        "question": "How are my children, creativity, intelligence and romance?",
    },
    6: {
        "title": "Health & Rivals",
        "domain": "health",
        "areas": [
            "Illness, recovery and daily health",
            "Enemies, rivals and competition",
            "Debts and money owed",
            "Litigation, disputes and daily service/work",
        ],
        "summary": "The sixth house is your fight — illness you overcome, rivals you "
                   "outwork, debts and disputes you must manage. Well-handled, it makes you resilient.",
        "question": "How are my health, recovery, enemies, debts and disputes?",
    },
    7: {
        "title": "Marriage & Partners",
        "domain": "marriage",
        "areas": [
            "Spouse, marriage and committed love",
            "Business partnerships and contracts",
            "Public dealings and one-to-one relationships",
            "Open rivals and negotiations",
        ],
        "summary": "The seventh house is the other person — your spouse, your partners "
                   "and how you meet the world one-to-one.",
        "question": "How are my marriage, spouse and partnerships?",
    },
    8: {
        "title": "Longevity & Change",
        "domain": "health",
        "areas": [
            "Longevity and chronic or hidden matters",
            "Sudden changes, upheavals and transformations",
            "Inheritance, insurance and other people's money",
            "Research, occult and deep interests",
        ],
        "summary": "The eighth house is transformation — longevity, sudden turns, "
                   "inheritances and the hidden depths you are pulled to explore.",
        "question": "How are my longevity, sudden changes and hidden matters?",
    },
    9: {
        "title": "Fortune & Father",
        "domain": "spiritual",
        "areas": [
            "Luck, dharma and life philosophy",
            "Father, teachers and mentors",
            "Higher learning and wisdom",
            "Long journeys and pilgrimage",
        ],
        "summary": "The ninth house is your good fortune — faith, father, teachers, "
                   "higher learning and the long journeys that broaden you.",
        "question": "How are my fortune, father, higher learning and beliefs?",
    },
    10: {
        "title": "Career & Status",
        "domain": "career",
        "areas": [
            "Career, profession and life's work",
            "Status, reputation and recognition",
            "Authority, bosses and government",
            "Your public role and achievements",
        ],
        "summary": "The tenth house is your work in the world — career, status, "
                   "reputation and the mark you leave through what you do.",
        "question": "How are my career, profession, status and reputation?",
    },
    11: {
        "title": "Gains & Network",
        "domain": "finance",
        "areas": [
            "Income, profits and gains",
            "Fulfilment of wishes and ambitions",
            "Friends, networks and well-wishers",
            "Elder siblings and mentors' circles",
        ],
        "summary": "The eleventh house is your harvest — income, gains, fulfilled "
                   "wishes and the network of friends who lift you.",
        "question": "How are my income, gains, wishes and friendships?",
    },
    12: {
        "title": "Loss & Liberation",
        "domain": "spiritual",
        "areas": [
            "Expenses, losses and letting go",
            "Foreign lands and life away from home",
            "Sleep, rest and the private inner world",
            "Spirituality, retreat and liberation",
        ],
        "summary": "The twelfth house is release — expenses, foreign shores, rest and "
                   "the spiritual surrender that frees you from the rest of the chart.",
        "question": "How are my expenses, foreign matters, rest and spiritual life?",
    },
}

# Clean display name + tradition family for each engine technique_id.
TECH_DISPLAY: dict[str, tuple[str, str]] = {
    "pillar": ("Lagna strength (rising-sign pillar)", "Parāśarī (classical Vedic)"),
    "bhava_lord": ("House-lord placement", "Parāśarī (classical Vedic)"),
    "karaka": ("Natural significator", "Parāśarī (classical Vedic)"),
    "vimshottari": ("Vimśottarī Daśā", "Daśā timing"),
    "yogini_goel": ("Yoginī Daśā", "Daśā timing"),
    "chara_goel": ("Chara Daśā", "Daśā timing"),
    "goel": ("Chara / Yoginī Daśā", "Daśā timing"),
    "kp": ("Cusp sub-lord", "Krishnamurti Paddhati (KP)"),
    "jaimini": ("Chara kārakas", "Jaimini"),
    "ashtakavarga": ("Bindu strength", "Aṣṭakavarga"),
    "varga": ("Divisional (Navāṁśa) support", "Divisional charts"),
    "rtvd": ("Annual / transit activation", "Transit & annual chart"),
    "longevity": ("Health & longevity lane", "Longevity"),
    "event_timing": ("Timing confluence", "Confluence gate"),
}

# Order families appear in the report.
FAMILY_ORDER = [
    "Parāśarī (classical Vedic)",
    "Daśā timing",
    "Krishnamurti Paddhati (KP)",
    "Jaimini",
    "Aṣṭakavarga",
    "Divisional charts",
    "Transit & annual chart",
    "Longevity",
    "Confluence gate",
]

DIGNITY_PLAIN = {
    "exalted": "in its strongest sign (exalted)",
    "debilitated": "in a weak sign (debilitated)",
    "own_sign": "in its own sign (very comfortable)",
    "moolatrikona": "in its power sign (moolatrikona)",
    "friendly": "in a friendly sign",
    "neutral": "in a neutral sign",
    "neutral_sign": "in a neutral sign",
    "enemy": "in an uncomfortable sign",
    "great_friend": "in a very supportive sign",
}

PLANET_REMEDY = {
    "Sun": "Offer water to the rising Sun and respect father-figures; "
           "strengthen confidence with the Sun's mantra on Sundays.",
    "Moon": "Keep a calm routine and good sleep; honour your mother and "
            "offer something white on Mondays to steady the mind.",
    "Mars": "Channel energy through exercise and discipline; serve siblings "
            "and avoid rash anger on Tuesdays.",
    "Mercury": "Read, write and learn daily; keep your word and donate green "
               "items / help students on Wednesdays.",
    "Jupiter": "Seek a teacher's guidance and give to genuine causes; honour "
               "elders and study scripture on Thursdays.",
    "Venus": "Cultivate kindness and beauty in your home; respect your "
             "partner and offer something fragrant on Fridays.",
    "Saturn": "Be patient, consistent and of service to workers and elders; "
              "keep commitments and help the needy on Saturdays.",
    "Rahu": "Avoid shortcuts and intoxicants; keep clean routines and serve "
            "the marginalised to settle a restless mind.",
    "Ketu": "Keep a simple spiritual practice and let go of what is past; "
            "charity to the devout steadies this energy.",
}

# What each graha naturally signifies when judging a given house.
PLANET_HOUSE_ROLE: dict[str, str] = {
    "Sun": "vitality, confidence and authority",
    "Moon": "mind, feelings and nourishment",
    "Mars": "courage, drive and physical energy",
    "Mercury": "speech, trade, learning and skill",
    "Jupiter": "wisdom, wealth and expansion",
    "Venus": "comfort, love and what you attract",
    "Saturn": "discipline, delay and lasting results",
    "Rahu": "ambition, obsession and sudden turns",
    "Ketu": "detachment, past karma and inner focus",
}

DUSTHANAS = {6, 8, 12}
KENDRAS = {1, 4, 7, 10}
TRINES = {1, 5, 9}


def _e(s: Any) -> str:
    return escape(str(s) if s is not None else "")


def _hk(house_lords: dict, h: int) -> dict:
    return house_lords.get(h) or house_lords.get(str(h)) or {}


def _planets_in_house(pc: dict, h: int) -> list[tuple[str, dict]]:
    out = []
    for name, body in (pc.get("planets") or {}).items():
        if isinstance(body, dict) and body.get("house") == h:
            out.append((name, body))
    return out


def _sav_for_house(pc: dict, house_sign_name: str) -> Optional[int]:
    sav = (pc.get("ashtakavarga") or {}).get("sav")
    if not sav or house_sign_name not in SIGNS:
        return None
    try:
        return int(sav[SIGNS.index(house_sign_name)])
    except Exception:
        return None


def _sav_note(bindus: Optional[int]) -> str:
    if bindus is None:
        return ""
    if bindus >= 30:
        return f"{bindus} bindus — strong, this area gets steady support."
    if bindus >= 25:
        return f"{bindus} bindus — moderate; workable with effort."
    return f"{bindus} bindus — on the lighter side; needs conscious strengthening."


_HNOTE = (
    (re.compile(r"(?<!\d)1th\b"), "1st"),
    (re.compile(r"(?<!\d)2th\b"), "2nd"),
    (re.compile(r"(?<!\d)3th\b"), "3rd"),
    (re.compile(r"\bH(\d{1,2})\b"), r"House \1"),
    (re.compile(r"\s*\[\d+\]"), ""),
    (re.compile(r"\bCSL\b"), "cusp sub-lord"),
    (re.compile(r"\(debilitated\)"), "(in a weak sign)"),
    (re.compile(r"\(exalted\)"), "(in its strongest sign)"),
    (re.compile(r"neutral_sign"), "neutral sign"),
    (re.compile(r"own_sign"), "own sign"),
    (re.compile(r"\bfav\b"), "favourable"),
    (re.compile(r"\bMD/AD\b"), "current period"),
    (re.compile(r"cara karaka"), "a soul-significator (Chara kāraka)"),
)


def _humanize_note(note: str) -> str:
    if not note:
        return ""
    out = note
    for pat, repl in _HNOTE:
        out = pat.sub(repl, out)
    return out.strip()


_BADGE = {
    "positive": ("Supportive", "pos"),
    "caution": ("Caution", "cau"),
    "neutral": ("Neutral", "neu"),
}


def _verdict_word(pct: int, pos: int, cau: int) -> str:
    if pct >= 70 and pos > cau:
        return "Strong & well supported"
    if pct >= 55:
        return "Broadly favourable"
    if pct >= 40:
        return "Mixed — real strengths and real friction"
    return "Needs strengthening"


def _what_to_expect(h: int, area: dict, merged: dict, verdicts: list) -> tuple[str, str]:
    """Return (short lead, full detail) so the overall card and the
    what-to-expect section don't repeat the same paragraph."""
    pct = merged["confluence_pct"]
    pos = merged["positive_votes"]
    cau = merged["caution_votes"]
    title = area["title"].lower()
    pos_themes = [
        _humanize_note(v.note) for v in verdicts
        if v.direction == "positive" and v.note
    ][:3]
    cau_themes = [
        _humanize_note(v.note) for v in verdicts
        if v.direction == "caution" and v.note
    ][:3]

    if pct >= 70 and pos > cau:
        lead = (f"Most systems agree your <strong>{_e(title)}</strong> is on solid ground. "
                "You can lean into this area with confidence.")
    elif pct >= 55:
        lead = (f"The weight of evidence is positive for your <strong>{_e(title)}</strong>, "
                "with a few areas to stay mindful of.")
    elif pct >= 40:
        lead = (f"Your <strong>{_e(title)}</strong> is genuinely mixed: clear strengths sit "
                "alongside real friction, so outcomes depend a lot on your effort and timing.")
    else:
        lead = (f"Several systems flag your <strong>{_e(title)}</strong> as a softer spot. "
                "This is not a verdict of failure — it is a signal to strengthen this area deliberately.")

    bits = []
    if pos_themes:
        bits.append("<strong>What works in your favour:</strong> " + "; ".join(pos_themes) + ".")
    if cau_themes:
        bits.append("<strong>Where to stay careful:</strong> " + "; ".join(cau_themes) + ".")
    detail = lead + ("<br>" + "<br>".join(bits) if bits else "")
    return lead, detail


def _lord_line(lord_rec: dict) -> str:
    lord = lord_rec.get("lord", "?")
    lord_house = lord_rec.get("lord_house", "?")
    lord_sign = lord_rec.get("lord_sign", "?")
    dig = DIGNITY_PLAIN.get(str(lord_rec.get("lord_dignity", "")).lower(),
                            lord_rec.get("lord_dignity", ""))
    func = str(lord_rec.get("functional", "")).replace("_", " ")
    extra = f" It is a {func} for you." if func else ""
    return (f"<strong>{_e(lord)}</strong> rules this house and sits in "
            f"House {_e(lord_house)} in {_e(lord_sign)}, {_e(dig)}.{extra}")


def _dignity_plain(dig: str) -> str:
    return DIGNITY_PLAIN.get(str(dig or "").lower(), str(dig or "—"))


def _planet_direction(body: dict, target_house: int) -> str:
    """Supportive / caution / neutral from placement + dignity."""
    dig = str(body.get("dignity", "")).lower()
    phouse = int(body.get("house") or 0)
    strong_dig = dig in ("exalted", "own_sign", "moolatrikona")
    weak_dig = dig in ("debilitated", "enemy", "enemy_sign")

    if phouse == target_house:
        if strong_dig:
            return "positive"
        if weak_dig:
            return "caution"
        return "neutral"

    if strong_dig and phouse not in DUSTHANAS:
        return "positive"
    if weak_dig or phouse in DUSTHANAS:
        return "caution"
    if phouse in KENDRAS or phouse in TRINES:
        return "neutral"
    return "neutral"


def _bav_on_house(pc: dict, planet: str, house_sign: str) -> Optional[int]:
    bav = (pc.get("ashtakavarga") or {}).get("bav") or {}
    row = bav.get(planet)
    if not row or house_sign not in SIGNS:
        return None
    try:
        return int(row[SIGNS.index(house_sign)])
    except Exception:
        return None


def _planet_reading(
    planet: str,
    roles: list[str],
    body: dict,
    direction: str,
    target_house: int,
    bav: Optional[int],
) -> str:
    sign = body.get("sign", "?")
    phouse = body.get("house", "?")
    dig = _dignity_plain(str(body.get("dignity", "")))
    theme = PLANET_HOUSE_ROLE.get(planet, "this life area")
    role_txt = " · ".join(roles)

    if "Ruler of this house" in roles:
        if direction == "positive":
            lead = (f"As house ruler, {planet} is well placed in House {phouse} "
                    f"({dig}), which helps this house deliver its promises.")
        elif direction == "caution":
            lead = (f"As house ruler, {planet} sits in House {phouse} in {sign} "
                    f"({dig}) — the themes of this house need more conscious effort.")
        else:
            lead = (f"As house ruler, {planet} in House {phouse} ({dig}) gives "
                    f"a workable but uneven read on this house.")
    elif "Sitting in this house" in roles:
        if direction == "positive":
            lead = (f"{planet} occupies this house directly in {sign} ({dig}), "
                    f"colouring your {theme} here in a supportive way.")
        elif direction == "caution":
            lead = (f"{planet} sits in this house in {sign} ({dig}) — its {theme} "
                    f"shows here, but with friction or extra demand on you.")
        else:
            lead = (f"{planet} in this house ({sign}, {dig}) adds its {theme} "
                    f"to how this area plays out.")
    else:
        if direction == "positive":
            lead = (f"Natural karaka {planet} is strong in House {phouse} ({dig}), "
                    f"supporting {theme} linked to this house.")
        elif direction == "caution":
            lead = (f"Natural karaka {planet} is under strain in House {phouse} ({dig}), "
                    f"so {theme} tied to this house needs care.")
        else:
            lead = (f"Natural karaka {planet} in House {phouse} ({dig}) gives a "
                    f"moderate influence on {theme} here.")

    if bav is not None:
        if bav >= 5:
            lead += f" Its bindu score on this house sign is {bav} — helpful."
        elif bav <= 3:
            lead += f" Its bindu score on this house sign is {bav} — lighter support."
        else:
            lead += f" Bindu score on this house sign: {bav} (average)."

    return f"<span class='fine'>{_e(role_txt)}</span><br>{_e(lead)}"


def _collect_planet_roles(
    pc: dict,
    house: int,
    lord_rec: dict,
    occupants: list[tuple[str, dict]],
) -> dict[str, set[str]]:
    roles: dict[str, set[str]] = {}
    lord = lord_rec.get("lord")
    if lord:
        roles.setdefault(lord, set()).add("Ruler of this house")
    for k in HOUSE_KARAKAS.get(house, []):
        roles.setdefault(k, set()).add("Natural karaka")
    for name, _ in occupants:
        roles.setdefault(name, set()).add("Sitting in this house")
    return roles


def _render_planet_verdicts(
    pc: dict,
    house: int,
    lord_rec: dict,
    house_sign: str,
    occupants: list[tuple[str, dict]],
) -> str:
    """Per-planet verdict block: ruler, karakas, occupants."""
    role_map = _collect_planet_roles(pc, house, lord_rec, occupants)
    if not role_map:
        return ""

    # Ruler first, then karakas, then occupants-only, then rest.
    def sort_key(name: str) -> tuple:
        r = role_map[name]
        if "Ruler of this house" in r:
            return (0, name)
        if "Natural karaka" in r:
            return (1, name)
        if "Sitting in this house" in r:
            return (2, name)
        return (3, name)

    planets_data = pc.get("planets") or {}
    rows = ""
    for name in sorted(role_map, key=sort_key):
        body = planets_data.get(name) or {}
        if not body:
            continue
        roles = sorted(role_map[name], key=lambda x: (
            0 if x == "Ruler of this house" else 1 if x == "Natural karaka" else 2
        ))
        direction = _planet_direction(body, house)
        label, cls = _BADGE.get(direction, ("Neutral", "neu"))
        bav = _bav_on_house(pc, name, house_sign)
        placement = (
            f"{_e(name)} · House {_e(body.get('house', '?'))} · "
            f"{_e(body.get('sign', '?'))} · {_e(_dignity_plain(str(body.get('dignity', ''))))}"
        )
        reading = _planet_reading(name, roles, body, direction, house, bav)
        rows += (
            f"<tr><td><strong>{_e(name)}</strong><br><span class='fine'>{placement}</span></td>"
            f"<td><span class='bdg {cls}'>{label}</span></td>"
            f"<td>{reading}</td></tr>"
        )

    if not rows:
        return ""

    return f"""
  <div class="card">
    <h2>Planet verdicts for House {house}</h2>
    <p class="fine">The house ruler, natural karakas and any planet sitting here —
    each judged on placement, dignity and bindu strength on this house sign.</p>
    <table class="tech planet">
      <tr><th>Planet</th><th>Verdict</th><th>What it means for you</th></tr>
      {rows}
    </table>
  </div>"""


def _remedy_block(h: int, lord_rec: dict, merged: dict) -> str:
    pct = merged["confluence_pct"]
    cau = merged["caution_votes"]
    weak = pct < 55 or cau >= merged["positive_votes"] or \
        str(lord_rec.get("lord_dignity", "")).lower() == "debilitated"
    if not weak:
        return ""
    lord = lord_rec.get("lord", "")
    rem = PLANET_REMEDY.get(lord, "")
    if not rem:
        return ""
    return f"""
<div class="card amber">
  <h3>What to do — strengthen this house</h3>
  <p>Because the ruler of this house ({_e(lord)}) wants support, a simple, steady
  remedy helps this area deliver more smoothly:</p>
  <p style="margin-top:.4rem"><strong>{_e(lord)} remedy:</strong> {_e(rem)}</p>
  <p class="fine">Remedies work as steady habits, not magic — give them a few months.</p>
</div>"""


def _extra_css() -> str:
    return """
.house-num{font-size:.8rem;letter-spacing:.16em;text-transform:uppercase;opacity:.8}
.areas{list-style:none;padding:0;margin:.4rem 0 0}
.areas li{padding:7px 0 7px 26px;position:relative;border-bottom:1px solid var(--border)}
.areas li:before{content:"\\2022";position:absolute;left:6px;color:var(--accent);font-weight:700}
.gauge{display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.gnum{font-size:2.6rem;font-weight:800;line-height:1}
.pill{display:inline-block;padding:3px 12px;border-radius:999px;font-size:.78rem;font-weight:700}
.pill.HIGH,.pill.VERY{background:#e6f4ea;color:#1f6b42}
.pill.MODERATE{background:#fdf2dd;color:#9a5a00}
.pill.LOW{background:#fae7e7;color:#9a2a2a}
.tally{font-size:.86rem;color:var(--muted)}
table.tech{width:100%;border-collapse:collapse;font-size:.9rem;margin:8px 0 0}
table.tech th,table.tech td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--border);vertical-align:top}
table.tech th{font-size:.74rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.fam{font-weight:700;color:var(--accent);background:#f6f4fb}
.bdg{display:inline-block;padding:2px 9px;border-radius:999px;font-size:.74rem;font-weight:700;white-space:nowrap}
.bdg.pos{background:#e6f4ea;color:#1f6b42}
.bdg.cau{background:#fdf2dd;color:#9a5a00}
.bdg.neu{background:#eee;color:#555}
"""


def generate_house_confluence_html(
    pc: dict,
    house: int,
    client_name: str = "Client",
) -> tuple[str, dict]:
    area = HOUSE_AREAS[house]
    meta = pc.get("meta", {})
    house_lords = pc.get("house_lords", {}) or {}
    lord_rec = _hk(house_lords, house)
    house_sign = lord_rec.get("sign", "")
    lagna_sign = meta.get("lagna_sign", "")
    lagna_deg = meta.get("lagna_degree", "")
    try:
        lagna_deg = f"{float(lagna_deg):.1f}°"
    except (TypeError, ValueError):
        lagna_deg = str(lagna_deg)

    # Live multi-technique verdicts for this house.
    ctx = QuestionContext(
        question=area["question"],
        topic="general",
        domain=area["domain"],
        title=f"Your {area['title']}",
        intent="general",
        primary_house=house,
        houses=[house],
        favorable_houses=[],
        denying_houses=[],
    )
    birth_kw = {"dob": meta.get("dob", ""), "birth_time": meta.get("birth_time", "")}
    verdicts = evaluate_question_techniques(ctx, pc, birth_kw=birth_kw)
    merged = synthesize_answer(ctx, verdicts)

    sav = _sav_for_house(pc, house_sign)
    planets = _planets_in_house(pc, house)
    pct = merged["confluence_pct"]
    pos, cau, neu = merged["positive_votes"], merged["caution_votes"], merged["neutral_votes"]
    conf = merged["confidence"]
    conf_cls = "VERY" if conf.startswith("VERY") else conf

    # Areas list
    areas_html = "".join(f"<li>{_e(a)}</li>" for a in area["areas"])

    # Planets-in-house
    if planets:
        pls = ", ".join(
            f"{_e(n)} ({_e(DIGNITY_PLAIN.get(str(b.get('dignity','')).lower(), b.get('dignity','') or '—'))})"
            for n, b in planets
        )
        planets_line = f"<p><strong>Planets sitting in this house:</strong> {pls}.</p>"
    else:
        planets_line = ("<p><strong>Planets sitting in this house:</strong> none — "
                        "the house is read mainly through its ruler and aspects.</p>")

    # Technique rows grouped by family
    by_family: dict[str, list] = {}
    for v in verdicts:
        if v.direction == "abstain":
            continue
        disp, fam = TECH_DISPLAY.get(v.technique_id, (v.label, "Other"))
        by_family.setdefault(fam, []).append((disp, v))

    rows = ""
    for fam in FAMILY_ORDER + [f for f in by_family if f not in FAMILY_ORDER]:
        items = by_family.get(fam)
        if not items:
            continue
        rows += f'<tr><td class="fam" colspan="3">{_e(fam)}</td></tr>'
        for disp, v in items:
            label, cls = _BADGE.get(v.direction, ("Neutral", "neu"))
            timing = f'<span class="fine">{_e(v.timing)}</span>' if v.timing else ""
            rows += (
                f"<tr><td>{_e(disp)}</td>"
                f'<td><span class="bdg {cls}">{label}</span></td>'
                f"<td>{_e(_humanize_note(v.note))} {timing}</td></tr>"
            )

    lead, detail = _what_to_expect(house, area, merged, verdicts)
    remedy = _remedy_block(house, lord_rec, merged)
    planet_block = _render_planet_verdicts(pc, house, lord_rec, house_sign, planets)
    today = datetime.now().strftime("%d %B %Y")

    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>House {house} — {_e(area['title'])} — {_e(client_name)}</title>
<style>{client_css()}{_extra_css()}</style></head><body>
<div class="wrap">

  <div class="hero">
    <div class="house-num">House {house} of 12</div>
    <h1>House {house} — {_e(area['title'])}</h1>
    <p style="margin:.3rem 0 0;opacity:.92">{_e(area['summary'])}</p>
    <div class="meta" style="margin-top:.6rem"><span>{_e(client_name)}</span>
      <span>Lagna: {_e(lagna_sign)} {_e(lagna_deg)}</span>
      <span>This house: {_e(house_sign)}</span>
      <span>{_e(today)}</span></div>
  </div>

  <div class="card">
    <h2>What House {house} covers</h2>
    <ul class="areas">{areas_html}</ul>
  </div>

  <div class="card">
    <h2>Overall verdict — across all systems</h2>
    <div class="gauge">
      <div><div class="gnum">{pct}%</div><div class="tally">confluence</div></div>
      <div>
        <div style="font-size:1.15rem;font-weight:700">{_e(_verdict_word(pct, pos, cau))}</div>
        <div style="margin:.3rem 0"><span class="pill {conf_cls}">{_e(conf)} confidence</span></div>
        <div class="tally">{pos} systems supportive · {cau} caution · {neu} neutral
          (of {merged['total_techniques']} that weighed in)</div>
      </div>
    </div>
    <p style="margin-top:.8rem">{lead}</p>
  </div>

  <div class="card">
    <h2>Your House {house} snapshot</h2>
    <p>{_lord_line(lord_rec)}</p>
    {planets_line}
    <p><strong>Strength (Aṣṭakavarga):</strong> {_e(_sav_note(sav)) or 'not available'}</p>
  </div>

  {planet_block}

  <div class="card">
    <h2>How each system reads House {house}</h2>
    <p class="fine">Each tradition is judged on its own terms; the overall verdict above is their confluence.</p>
    <table class="tech">
      <tr><th>Technique</th><th>Verdict</th><th>Reading</th></tr>
      {rows}
    </table>
  </div>

  <div class="card">
    <h2>What to expect</h2>
    <p>{detail}</p>
  </div>
  {remedy}

</div></body></html>"""

    summary = {
        "house": house,
        "title": area["title"],
        "confluence_pct": pct,
        "confidence": conf,
        "positive": pos,
        "caution": cau,
        "neutral": neu,
        "lagna": lagna_sign,
        "house_sign": house_sign,
        "house_lord": lord_rec.get("lord"),
        "sav": sav,
        "verdict_word": _verdict_word(pct, pos, cau),
        "lead": lead,
        "detail": detail,
    }
    return finalize_report_html(doc, client_name), summary


def write_house_confluence_reports(
    pc: dict,
    houses: list[int],
    out_dir: Path,
    client_name: str = "Client",
    slug: str = "",
) -> list[Path]:
    """Write one HTML report per house number."""
    paths: list[Path] = []
    for h in houses:
        paths.append(write_house_confluence_report(pc, h, out_dir, client_name, slug))
    return paths


def write_house_confluence_report(
    pc: dict,
    house: int,
    out_dir: Path,
    client_name: str = "Client",
    slug: str = "",
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    html_doc, _summary = generate_house_confluence_html(pc, house, client_name)
    slug = slug or client_name.strip().replace(" ", "_")
    path = out_dir / f"House_{house:02d}_{HOUSE_AREAS[house]['title'].split(' ')[0]}_{slug}.html"
    path.write_text(html_doc, encoding="utf-8")
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Per-house multi-technique confluence report")
    ap.add_argument("--house", type=int, default=0, help="Single house (1-12)")
    ap.add_argument("--houses", default="", help="Batch: comma-separated e.g. 2,3,4")
    ap.add_argument("--name", default="Ritesh")
    ap.add_argument("--dob", default="1985-03-08")
    ap.add_argument("--time", default="13:05")
    ap.add_argument("--place", default="Patna, India")
    ap.add_argument("--lat", type=float, default=25.5941)
    ap.add_argument("--lon", type=float, default=85.1376)
    ap.add_argument("--tz", type=float, default=5.5)
    ap.add_argument("-o", "--out", default="")
    args = ap.parse_args()

    if args.houses.strip():
        house_list = [int(x.strip()) for x in args.houses.split(",") if x.strip()]
    elif args.house:
        house_list = [args.house]
    else:
        house_list = [1]

    from astro_chart_bridge import compute_chart

    pc = compute_chart(
        client_name=args.name, dob=args.dob, birth_time=args.time,
        place=args.place, latitude=args.lat, longitude=args.lon, timezone=args.tz,
    )
    if not pc:
        raise SystemExit("Could not compute chart (PyJHora/ephemeris unavailable).")

    out_dir = Path(args.out) if args.out else (BASE_DIR / "reports" / args.name)
    for h in house_list:
        if h < 1 or h > 12:
            print(f"Skip invalid house {h}")
            continue
        path = write_house_confluence_report(pc, h, out_dir, args.name)
        print(f"Wrote {path}")
