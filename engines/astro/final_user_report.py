#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final plain-English consultation report.

Reads like a sitting with a human astrologer:
  1. "What I can see about you" — personality, current life-phase and the
     problems you may be facing right now (built from the chart, before you say
     a word) to establish rapport.
  2. "Your family" — direct, personal notes on parents, siblings, spouse, kids.
  3. Life-area sections tied to the divisional charts (D1 self, D3 siblings,
     D7 children, D9 spouse, D10 profession, D12 parents, D24 education, D27,
     D30, …) with where you stand, what to expect in the next 1–2 years,
     remedies where an area is strained, and caution dates from the transit.

Synthesises the planet, house, divisional and 108-rule strengths plus the
Vimshottari / Jaimini / Yogini + transit confluence already built.
"""
from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path

from prediction108_report import _css, _esc
from chart_summary_report import (
    _house_data, _planet_data, _varga_data, _hero, _doc,
    _varga_lagna, _varga_sign, GOOD_HOUSES, DUSTHANA,
)
from prediction108_rules import (
    hlord, psign, phouse, pdig, pnak, lagna, PLANETS, NAT_BENEFIC, NAT_MALEFIC,
    evaluate_all,
)
from prediction108_transit import build_transit_context, attach_contexts
from dasha_confluence_report import compute_windows, rate_field, _planet_quality, _fmt
from personalized_confluence import resolve_promise
from astro_precompute import SIGNS, SIGN_LORDS, sign_index, house_sign, get_dignity
try:
    from gemstone_remedy import build_remedy_report
except Exception:  # pragma: no cover
    build_remedy_report = None
import final_report_i18n as I18N
from final_report_i18n import (
    PL, SG, MON, ORDw, U, SIGN_TRAIT_HI, MOON_TRAIT_HI, REMEDY_HI,
    FIELD_TITLE_HI, WHERE_HI, FAMILY_HI, PROBLEMS_HI, RATING_NEAR_HI,
)

BASE_DIR = Path(__file__).resolve().parent

VNUM = {"strong": 1.0, "mixed": 0.0, "weak": -1.0}

SIGN_TRAIT = {
    "Aries": "bold, direct and quick to act — you like to lead and dislike waiting",
    "Taurus": "steady, patient and comfort-loving — you value security and finish what you start",
    "Gemini": "curious, talkative and adaptable — your mind moves fast and loves variety",
    "Cancer": "caring, emotional and home-loving — you protect the people close to you",
    "Leo": "warm, proud and generous — you want to shine and be respected",
    "Virgo": "practical, analytical and hard-working — you notice details others miss",
    "Libra": "balanced, charming and relationship-minded — you seek fairness and harmony",
    "Scorpio": "intense, private and determined — you feel deeply and never give up easily",
    "Sagittarius": "optimistic, honest and freedom-loving — you think big and value truth",
    "Capricorn": "disciplined, ambitious and responsible — you carry burdens quietly and rise slowly but surely",
    "Aquarius": "independent, original and humane — you think differently and care about the larger picture",
    "Pisces": "gentle, imaginative and compassionate — you feel for everyone and dream beyond the ordinary",
}

MOON_TRAIT = {
    "Aries": "your mind is restless and needs action",
    "Taurus": "emotionally you crave stability and calm",
    "Gemini": "your thoughts race and you need mental stimulation",
    "Cancer": "you are deeply sensitive and attached to family",
    "Leo": "you need appreciation and feel things grandly",
    "Virgo": "you over-think and want everything just right",
    "Libra": "you seek peace and dislike conflict",
    "Scorpio": "your emotions run deep and you keep them hidden",
    "Sagittarius": "you stay hopeful and dislike being tied down",
    "Capricorn": "you are emotionally guarded and self-reliant",
    "Aquarius": "you process feelings through the mind, not the heart",
    "Pisces": "you are tender, intuitive and easily moved",
}

REMEDY = {
    "Sun": ("Lord Surya / Lord Rama", "offer water to the rising Sun and recite the Gayatri / Aditya Hridaya", "Sunday", "wheat and jaggery to the needy"),
    "Moon": ("Lord Shiva", "chant 'Om Som Somaya Namah' and offer milk/water at a Shiva temple", "Monday", "rice, milk and white clothes"),
    "Mars": ("Lord Hanuman", "read the Hanuman Chalisa and chant 'Om Angarakaya Namah'", "Tuesday", "red lentils (masoor) and jaggery"),
    "Mercury": ("Lord Vishnu / Ganesha", "chant 'Om Budhaya Namah' and feed green fodder to cows", "Wednesday", "green moong and green clothes"),
    "Jupiter": ("Guru / Lord Vishnu", "chant 'Om Gurave Namah' and respect teachers and elders", "Thursday", "turmeric, chana dal and yellow items to a temple or teacher"),
    "Venus": ("Goddess Lakshmi", "chant 'Om Shukraya Namah' and keep clean, honest conduct", "Friday", "white sweets, curd and white clothes to young girls"),
    "Saturn": ("Lord Shani / Hanuman", "light a mustard-oil lamp under a Peepal tree and recite the Hanuman Chalisa", "Saturday", "black sesame, mustard oil and iron to labourers/the poor"),
    "Rahu": ("Goddess Durga", "chant 'Om Rahave Namah' / Durga Saptashati", "Saturday", "mustard oil and blankets to the needy"),
    "Ketu": ("Lord Ganesha", "chant 'Om Ketave Namah' and feed dogs", "Tuesday", "a multi-coloured blanket and sesame to the needy"),
}

# ── area-specific remedies (per divisional life-area, not generic) ──
# key → (deity/focus, the practice tied to that life-area, best day, charity, gem-planet)
AREA_REMEDY = {
    "self": ("Lord Surya & your ruling planet", "offer water to the rising Sun and do a few Surya-Namaskars for vitality",
             "Sunday", "wheat and jaggery to the needy", "Sun"),
    "parents": ("Lord Shiva–Parvati (for both parents)", "light a lamp for your parents' long life and touch their feet for blessings",
                "Monday", "food and clothes to an elderly couple", "Sun"),
    "siblings": ("Lord Kartikeya (Subramanya)", "pray for your siblings' wellbeing and keep the bond warm with regular contact",
                 "Tuesday", "red lentils or sweets shared with siblings/cousins", "Mars"),
    "spouse": ("Gauri–Shankar / Lakshmi–Narayan (for harmony)", "do a joint prayer or fast on Fridays for marital peace and offer flowers to the divine couple",
               "Friday", "white sweets and clothes to a young married woman", "Venus"),
    "children": ("Santana-Gopala (Bala-Krishna)", "recite the Santana-Gopala mantra and feed/serve children",
                 "Thursday", "yellow sweets, bananas and books to children", "Jupiter"),
    "profession": ("Lord Surya & Lord Vishnu", "salute the Sun each morning before work and keep your word at the workplace",
                   "Sunday", "jaggery, copper or service to seniors", "Sun"),
    "education": ("Goddess Saraswati", "recite the Saraswati Vandana before study and keep your study desk clean and east-facing",
                  "Wednesday", "green books, pens and fruit to students", "Mercury"),
    "wealth": ("Goddess Lakshmi & Lord Kubera", "light a ghee lamp on Fridays, recite Shri Suktam and avoid wasteful spending",
               "Friday", "rice, curd and white items on Friday", "Jupiter"),
    "home": ("Bhumi Devi / Vastu Purusha", "do a small Vastu/Bhumi prayer, keep the home clean and the north-east clutter-free",
             "Tuesday", "land/soil care, feeding ants and birds", "Mars"),
    "strengths": ("Lord Hanuman", "read the Hanuman Chalisa to build courage and stamina",
                  "Tuesday", "red flowers and sindoor at a Hanuman temple", "Mars"),
    "troubles": ("Lord Mrityunjaya (Shiva)", "chant the Maha-Mrityunjaya mantra for health and protection and keep a steady routine",
                 "Monday", "medicines or black sesame for the sick/poor", "Saturn"),
    "spiritual": ("Lord Dakshinamurthy / Ganesha", "sit for a few quiet minutes of meditation daily and chant your chosen mantra",
                  "Thursday", "feeding dogs and serving at a temple", "Ketu"),
}

# chara-karaka roles that meaningfully refine a field (used silently in scoring)
KARAKA_FIELD = {
    "self": "Atmakarak",
    "profession": "Amatyakarak",
    "siblings": "Bhratrukaraka",
    "parents": "Matrukaraka",
    "children": "Putrakaraka",
    "spouse": "Darakaraka",
    "troubles": "Gnatikaraka",
}


# narrative fields: (key, title, relation_word, varga, houses, karakas)
def _spouse_karaka(gender):
    return ["Jupiter"] if str(gender) in ("1", "Female", "female") else ["Venus"]


def _narr_fields(gender):
    return [
        ("self", "You — your body, health & temperament", "you", "D1", [1, 6, 8], ["Sun"]),
        ("parents", "Your mother & father", "your parents", "D12", [4, 9], ["Moon", "Sun"]),
        ("siblings", "Your brothers & sisters", "your sibling", "D3", [3, 11], ["Mars"]),
        ("spouse", "Your Relationships & Partnership", "your relationship", "D9", [7, 2, 11], _spouse_karaka(gender)),
        ("children", "Your children", "your child", "D7", [5, 9], ["Jupiter"]),
        ("profession", "Your work & profession", "your career", "D10", [10, 6, 11], ["Sun", "Saturn", "Mercury"]),
        ("education", "Your education & learning", "your studies", "D24", [4, 5, 2], ["Mercury", "Jupiter"]),
        ("wealth", "Your money & finances", "your finances", "D2", [2, 11, 9], ["Jupiter", "Venus"]),
        ("home", "Your home & property", "your home", "D4", [4, 2], ["Mars", "Moon"]),
        ("strengths", "Your inner strengths & stamina", "your strengths", "D27", [1, 11], ["Sun", "Mars"]),
        ("troubles", "Health hazards to guard against", "your health", "D30", [6, 8, 12], ["Saturn", "Mars"]),
        ("spiritual", "Your mind & spiritual side", "your mind", "D20", [12, 9, 5], ["Jupiter", "Ketu", "Moon"]),
    ]

REL_REMEDY_NOTE = ("Treat remedies as supportive, faith-based practices to steady the mind — "
                   "not as a replacement for medical, legal or financial advice. Wear gemstones only "
                   "after expert testing.")


# ── small helpers ───────────────────────────────────────────────────
def _gender_words(gender, lang="en"):
    female = str(gender) in ("1", "Female", "female")
    if lang == "hi":
        if female:
            return {"spouse": "पति", "they": "वह", "their": "उनका"}
        return {"spouse": "पत्नी", "they": "वह", "their": "उनकी"}
    if female:
        return {"spouse": "husband", "they": "she", "their": "her"}
    return {"spouse": "wife", "they": "he", "their": "his"}


# ── background signals: chara karakas + ashtakavarga (silent in text) ─
def _karaka_map(pc):
    out = {}
    for k in (pc.get("cara_karakas", {}) or {}).get("karakas", []) or []:
        if k.get("role") and k.get("planet"):
            out[k["role"]] = k["planet"]
    return out


def _karaka_planet(pc, key):
    return _karaka_map(pc).get(KARAKA_FIELD.get(key, ""), "")


def _sav_for_house(pc, house):
    av = pc.get("ashtakavarga", {}) or {}
    sav = av.get("sav") or []
    if len(sav) != 12:
        return None
    try:
        return int(sav[sign_index(house_sign(house, lagna(pc)))])
    except Exception:
        return None


def _sav_signal(pc, houses):
    """Ashtakavarga bindu strength of the field's primary house, as a -1..1 signal
    (28 bindus ≈ chart average; 8 bindus ≈ one full step)."""
    if not houses:
        return None
    v = _sav_for_house(pc, houses[0])
    if v is None:
        return None
    return max(-1.0, min(1.0, (v - 28) / 8.0))


def _strength_of(pc, houses, karakas, caches, key=None):
    """Structural strength of a life-area, blending house + fixed karaka +
    (silently) the Jaimini chara-karaka and the Ashtakavarga bindus of the house."""
    hv = [VNUM[_house_data(pc, h)["vcls"]] for h in houses]
    kv = [_planet_quality(pc, k, caches) for k in karakas if k]
    kv += [_planet_quality(pc, hlord(pc, houses[0]), caches)]
    ck = _karaka_planet(pc, key) if key else ""
    if ck:
        kv.append(_planet_quality(pc, ck, caches))
    hs = (sum(hv) / len(hv)) if hv else 0.0
    ks = (sum(kv) / len(kv)) if kv else 0.0
    score = hs * 0.45 + ks * 0.45
    sav = _sav_signal(pc, houses)
    if sav is not None:
        score += 0.10 * sav
    return score


def _label(score):
    if score >= 0.4:
        return "strong"
    if score <= -0.35:
        return "weak"
    return "mixed"


def _weakest(pc, houses, karakas, caches):
    cands = list(karakas) + [hlord(pc, h) for h in houses]
    ck = None
    cands = [c for c in cands if c]
    if not cands:
        return None
    return min(cands, key=lambda L: _planet_quality(pc, L, caches))


# ── 108-rule potential & cautions (plain English, no rule jargon) ───
_POS_WORDS = ("raja yoga", "raja-yoga", "rajayoga", "dhana", "wealth", "wealthy", "rich",
              "gain", "success", "fortune", "fortunate", "prosper", "rise", "fame",
              "respect", "authority", "power", "blessed", "benefic", "strong", "auspicious",
              "happiness", "comfort", "yoga for", "promotion", "leadership", "intelligent")
_NEG_WORDS = ("loss", "debt", "disease", "illness", "ill-health", "obstacle", "delay",
              "separation", "divorce", "enemy", "enemies", "litigation", "accident", "injury",
              "afflict", "malefic", "dosha", "weak", "trouble", "struggle", "poverty",
              "fear", "anxiety", "depriv", "denial", "downfall", "expenditure", "quarrel")


_PLAIN_SUB = [
    # multi-word yoga / phrase names first
    ("(a potent Adhi-type yoga via Sudarshan chakra)", ""),
    ("via Sudarshan chakra", ""),
    ("Dharma-Karmadhipati Yoga", "a fortune-and-career success combination"),
    ("Dharma-Karmadhipati", "a fortune-and-career success combination"),
    ("Chandra Adhi Yoga", "a 'benefics around the Moon' blessing"),
    ("Papa-Adhi Yoga", "a 'strength through struggle' pattern"),
    ("Papa Adhi Yoga", "a 'strength through struggle' pattern"),
    ("Adhi-type yoga", "a quiet benefic-strength pattern"),
    ("Subh Adhi Yoga", "a benefic-strength blessing"),
    ("Maha-Shakti", "a great-resolve combination"),
    ("Nara-yoga", "a sound-body blessing"),
    ("Raja Yoga", "a success (Raj) yoga"),
    ("Raj Yoga", "a success (Raj) yoga"),
    ("Neecha-Bhanga", "a cancellation of its weakness"),
    ("Neecha Bhanga", "a cancellation of its weakness"),
    ("the difficult 6/8/12 themes", "the tougher areas of life"),
    ("6/8/12 themes", "the tougher areas of life"),
    ("6/8/12", "the 6th/8th/12th (the tougher houses)"),
    ("6,8,12", "the 6th/8th/12th (the tougher houses)"),
    ("6th-house affairs", "matters of health, work and rivals"),
    ("trik house", "difficult 6th/8th/12th house"),
    ("trik+trikona", "both a difficult and a lucky"),
    ("a trik", "a difficult"),
    ("trik lord", "difficult-house lord"),
    ("trik", "difficult"),
    ("moolatrikona", "its own powerful sign"),
    ("(upachaya)", "(a growth house)"),
    ("upachaya houses (3/6/10/11)", "growth houses"),
    ("upachaya house (3/6/10/11)", "a growth house"),
    ("upachaya", "a growth house"),
    ("dusthana", "the difficult houses"),
    ("functional malefic", "a difficult ruler for you"),
    ("dispositor", "sign-lord"),
    ("significators", "key planets"),
    ("significator", "key planet"),
    ("Navamsha", "the marriage chart (D9)"),
    ("navamsha", "the marriage chart (D9)"),
    ("jeeva", "living"),
    ("Kartari", ""),
    ("trikona", "a lucky trine"),
    ("kendra", "an angle (1/4/7/10)"),
]


def _tidy(s):
    s = re.sub(r"\s+", " ", s).replace(" ;", ";").replace(" .", ".").replace(" ,", ",")
    s = s.replace("( ", "(").replace(" )", ")").replace("()", "")
    s = re.sub(r"\b(a|an) (a|an)\b", r"\1", s)        # collapse 'a a' / 'an a'
    s = s.replace("((", "(").replace("))", ")")
    return s.strip()


def _plainify(s):
    out = s or ""
    for a, b in _PLAIN_SUB:
        out = out.replace(a, b)
    return _tidy(out)


def _classify_rule(v):
    blob = f"{v.title} {v.prediction} {v.finding}".lower()
    pos = sum(1 for w in _POS_WORDS if w in blob)
    neg = sum(1 for w in _NEG_WORDS if w in blob)
    if pos > neg:
        return "pos"
    if neg > pos:
        return "neg"
    return None


def _compose_rule_line(v):
    """Build one plain line that NAMES the planet(s) and house(s) (from the finding)
    and then states what it means (from the prediction)."""
    fact = _plainify((v.finding or "").strip())
    meaning = _plainify((v.prediction or "").strip())
    if fact and not fact.endswith((".", "!", "?")):
        fact += "."
    if fact and meaning:
        # avoid repeating if the meaning is already implied in the fact
        return f"{fact} {meaning}"
    return fact or meaning


def _potential_problems(pc, limit=5):
    """Return (strengths, cautions) — chart-specific lines from the 108-rule engine
    that NAME the planet and house involved, picking the rules that fire for this chart."""
    try:
        verdicts = evaluate_all(pc)
    except Exception:
        return [], []
    pos, neg, seen = [], [], set()
    for v in verdicts:
        if v.verdict not in ("HIT", "PARTIAL"):
            continue
        if not (v.finding or v.prediction):
            continue
        line = _compose_rule_line(v)
        if not line or len(line) < 20:
            continue
        sig = line[:45].lower()
        if sig in seen:
            continue
        seen.add(sig)
        pol = _classify_rule(v)
        if pol == "pos":
            pos.append((v.verdict, line))
        elif pol == "neg":
            neg.append((v.verdict, line))
    # HITs before PARTIALs
    pos.sort(key=lambda x: 0 if x[0] == "HIT" else 1)
    neg.sort(key=lambda x: 0 if x[0] == "HIT" else 1)
    return [l for _, l in pos[:limit]], [l for _, l in neg[:limit]]


# ── dasha-timed gemstone (chart-safe), surfaced plainly ─────────────
def _gem_ctx(pc):
    if build_remedy_report is None:
        return None
    try:
        return build_remedy_report(pc)
    except Exception:
        return None


def _gem_line(gem_report, lang="en"):
    """One plain-English 'lucky stone for this phase' line tied to the current dasha."""
    if not gem_report:
        return ""
    pw = gem_report.get("primary_wear", []) or []
    dasha = gem_report.get("dasha", {}) or {}
    md, ad = dasha.get("md_lord", ""), dasha.get("ad_lord", "")
    pick = next((t for t in pw if t["planet"] in (ad, md)), None) or (pw[0] if pw else None)
    if pick:
        g = pick.get("gem", {})
        name = g.get("gem", "")
        finger, dayw = g.get("finger", ""), g.get("day", "")
        until = pick.get("wear_until", "")
        when = ""
        if until:
            try:
                when = " (suits the current phase up to about " + _dt.date.fromisoformat(until[:10]).strftime("%b %Y") + ")"
            except Exception:
                when = ""
        return (f"<b>Lucky stone for this phase:</b> a <b>{_esc(name)}</b> on the {_esc(finger).lower()} "
                f"({_esc(dayw)} morning, after a 3-day trial){when}. Energise it with the planet's mantra before wearing.")
    # nothing safe to wear now
    ms = gem_report.get("mantra_strict", []) or gem_report.get("mantra_only", [])
    if ms:
        return ("<b>Lucky stone for this phase:</b> no gemstone is advised right now — the planet ruling your "
                "current period is better served by mantra and charity than by a stone. Use the area remedies below instead.")
    return ""


def _field_gem_bit(gem_report, gem_planet):
    """If THIS area's planet is safe to wear in the current chart, add a short gem note."""
    if not gem_report or not gem_planet:
        return ""
    safe = {t["planet"]: t for t in (gem_report.get("primary_wear", []) or [])}
    avoid = {t["planet"] for t in (gem_report.get("avoid", []) or [])}
    if gem_planet in safe:
        g = safe[gem_planet].get("gem", {})
        name = g.get("gem", "")
        if name:
            return (f" If you wish to add a stone for this area, a <b>{_esc(name)}</b> suits it "
                    f"(after a 3-day trial).")
    if gem_planet in avoid:
        return " For this area, stick to the prayer and charity — a gemstone is not advised for you here."
    return ""


# ── overall potential & cautions (driven by the 108 rules) ──────────
def _potential_section(pc, lang="en"):
    strengths, cautions = _potential_problems(pc, limit=5)
    if not strengths and not cautions:
        return ""
    pos_html = "".join(f"<li>{_esc(s)}</li>" for s in strengths)
    neg_html = "".join(f"<li>{_esc(s)}</li>" for s in cautions)
    blocks = ""
    if pos_html:
        blocks += ("<div class='card'><div class='top'><span class='title'>What your chart gives you "
                   "<span class='badge'>strengths</span></span></div>"
                   f"<ul style='line-height:1.85;margin:6px 0 0'>{pos_html}</ul></div>")
    if neg_html:
        blocks += ("<div class='card weak'><div class='top'><span class='title'>What to stay watchful about "
                   "<span class='badge'>cautions</span></span></div>"
                   f"<ul style='line-height:1.85;margin:6px 0 0'>{neg_html}</ul></div>")
    return ("<h2>Your chart's big picture — potential &amp; cautions</h2>"
            "<p class='lead'>Read from the classical predictive rules that actually apply to your chart. "
            "These are the standout themes; the area-by-area cards below show how they play out day to day.</p>"
            f"<div class='cards'>{blocks}</div>")


# ── monthly transit table (for caution dates) ──────────────────────
def _month_dates(months):
    today = _dt.date.today()
    out = []
    for k in range(months + 1):
        y = today.year + (today.month - 1 + k) // 12
        mo = (today.month - 1 + k) % 12 + 1
        out.append(_dt.date(y, mo, 15))
    return out


def _monthly_transits(pc, months=24):
    table = []
    for d in _month_dates(months):
        try:
            tx = build_transit_context(pc, on=d)
            table.append({"date": d, "pos": tx.get("positions", {})})
        except Exception:
            table.append({"date": d, "pos": {}})
    return table


def _caution_windows(table, houses, malefics=("Mars",)):
    """Return grouped windows where a fast malefic (Mars) transits a field house.

    Mars is used as the acute caution trigger because it moves quickly (~6 weeks
    per sign), giving crisp, actionable date windows; slow nodes/Saturn sit in a
    house for many months and are treated as background rather than 'caution dates'.
    """
    flagged = []
    for cell in table:
        hits = []
        for m in malefics:
            h = (cell["pos"].get(m, {}) or {}).get("house_natal", 0)
            if h in houses:
                hits.append((m, h))
        flagged.append((cell["date"], hits))
    windows, cur = [], None
    for d, hits in flagged:
        if hits:
            if cur is None:
                cur = {"start": d, "end": d, "planets": set(), "houses": set()}
            cur["end"] = d
            for m, h in hits:
                cur["planets"].add(m)
                cur["houses"].add(h)
        else:
            if cur:
                windows.append(cur)
                cur = None
    if cur:
        windows.append(cur)
    return windows


# short life-theme of each house (for the elaborated personality read)
HOUSE_THEME = {
    1: "yourself, your body and the way you meet the world",
    2: "family, savings, food and speech",
    3: "courage, initiative, skills and communication",
    4: "home, your mother, vehicles and inner peace",
    5: "creativity, romance, children and learning",
    6: "work, service, health and getting the better of rivals",
    7: "partnership, marriage and dealings with the public",
    8: "deep change, shared resources and hidden matters",
    9: "luck, beliefs, higher learning and long journeys",
    10: "career, reputation and your public standing",
    11: "income, gains, friends and the fulfilment of desires",
    12: "letting go, expenses, foreign lands and the inner world",
}

_TONE_OK = {"auspicious", "benefic", "good"}


def _confluence_now(pc, cur_win, caches):
    """Plain 'supportive / mixed / testing' read of the non-Vimshottari cycles + transit."""
    if not cur_win:
        return "mixed"
    ov = cur_win["ov"]
    vals = []
    if ov.get("chara_lord"):
        vals.append(_planet_quality(pc, ov["chara_lord"], caches))
    vals.append(0.4 if ov.get("yogini_tone") in _TONE_OK else -0.4)
    tr = ov.get("transit", {}) or {}
    if tr.get("ju_moon") in (2, 5, 7, 9, 11):
        vals.append(0.4)
    elif tr.get("ju_moon") in (6, 8, 12):
        vals.append(-0.3)
    if tr.get("sa_moon") in (3, 6, 11):
        vals.append(0.3)
    elif tr.get("sa_moon") in (1, 2, 12, 4, 8):
        vals.append(-0.3)
    avg = sum(vals) / len(vals) if vals else 0.0
    return "supportive" if avg >= 0.2 else "testing" if avg <= -0.2 else "mixed"


_CONFLUENCE_LINE = {
    "supportive": ("Beneath your main period, the other timing cycles in your chart are also running a broadly "
                   "<b>supportive</b> phase right now — when several currents agree like this, sincere effort "
                   "tends to be rewarded faster than usual. This is a good window to begin important things."),
    "mixed": ("Beneath your main period, the other timing cycles in your chart are <b>mixed</b> right now — some "
              "doors open while others ask you to wait. Choose your priorities; push where it flows and hold "
              "back where it resists."),
    "testing": ("Beneath your main period, the other timing cycles in your chart are in a more <b>testing</b> "
                "phase right now — progress is real but slower, so steadiness and patience will serve you far "
                "better than big risks for a while."),
}


# ── opening: personality + current phase + current problems ─────────
def _opening(pc, windows, caches, table, gender, gem_report=None, lang="en"):
    lg = lagna(pc)
    moon = psign(pc, "Moon")
    sun = psign(pc, "Sun")
    ll = SIGN_LORDS.get(lg, "")
    ll_house = phouse(pc, ll)
    trait = (SIGN_TRAIT_HI if lang == "hi" else SIGN_TRAIT).get(lg, "")
    mtrait = (MOON_TRAIT_HI if lang == "hi" else MOON_TRAIT).get(moon, "")
    para1 = U(lang, "p1", lg=_esc(SG(lg, lang)), trait=trait, moon=_esc(SG(moon, lang)),
              moontrait=mtrait, ll=_esc(PL(ll, lang)), ord=ORDw(ll_house, lang))

    # elaborated nature (English; falls back in Hindi until translated)
    nak = pnak(pc, "Moon")
    elab = (f"Your ruling planet {_esc(ll)} placed in the {_ord(ll_house)} house steers a lot of your energy "
            f"toward {HOUSE_THEME.get(ll_house, 'your central concerns')}. "
            f"Your Sun in {_esc(sun)} shows where your pride and sense of purpose lie, "
            f"while the Moon"
            + (f" in {_esc(nak)} nakshatra" if nak else "")
            + " describes your instinctive, emotional self. Together these give you a recognisable inner signature: "
              "the way you react under pressure, what soothes you, and what you secretly want life to give you.")

    # current phase
    md = (pc.get("vimshottari", {}) or {}).get("current_md", {}) or {}
    cur_win = next((w for w in windows if w["is_now"]), windows[0] if windows else None)
    ad_lord = cur_win["row"]["ad"] if cur_win else ""
    sade = ""
    if table:
        sa_moon = (table[0]["pos"].get("Saturn", {}) or {}).get("from_moon", 0)
        if sa_moon in (12, 1, 2):
            phkey = {12: "sade_opening", 1: "sade_peak", 2: "sade_closing"}[sa_moon]
            sade = U(lang, "sade", phase=U(lang, phkey))
    para2 = U(lang, "p2", md=_esc(PL(md.get('md_lord', ''), lang)),
              y1=str(md.get('start', ''))[:4], y2=str(md.get('end', ''))[:4],
              ad=_esc(PL(ad_lord, lang)), sade=sade)
    conf = _CONFLUENCE_LINE[_confluence_now(pc, cur_win, caches)]

    # current problems (fields challenging in current window)
    problems = []
    if cur_win:
        for key, title, rel, varga, houses, karakas in _narr_fields(gender):
            field = (title, key, varga, houses, karakas)
            r = rate_field(pc, field, cur_win, caches)
            if r["rating"] == "chal":
                problems.append(key)
    pmap = PROBLEMS_HI if lang == "hi" else {
        "self": "your own energy and health may feel low, with self-doubt creeping in",
        "profession": "work feels heavy — recognition or growth seems stuck despite your effort",
        "wealth": "money feels tight or unpredictable, with outflows you can't fully control",
        "troubles": "small health niggles or stress are nagging at you",
        "spiritual": "your mind feels restless or low, and you're searching for meaning",
        "spouse": "there's some distance, friction or worry in your closest relationship",
        "children": "you're concerned about a child — their studies, health or direction",
        "education": "studies or skill-building feel like an uphill climb right now",
        "home": "there's tension at home or a property/family matter on your mind",
        "siblings": "things with a brother or sister feel strained or distant",
        "parents": "you're worried about a parent's health or carrying family responsibility",
    }
    probtxt = [pmap[k] for k in problems if k in pmap][:4]
    if probtxt:
        para3 = U(lang, "p3_problems", list="; ".join(probtxt))
    else:
        para3 = U(lang, "p3_none")

    gem = _gem_line(gem_report, lang)
    gem_html = (f"<p class='lead' style='color:var(--ink);font-size:15.5px'>{gem}</p>") if gem else ""

    return (f"<h2>{U(lang,'h_about')}</h2>"
            f"<p class='lead' style='color:var(--ink);font-size:15.5px'>{para1}</p>"
            f"<p class='lead' style='color:var(--ink);font-size:15.5px'>{elab}</p>"
            f"<p class='lead' style='color:var(--ink);font-size:15.5px'>{para2}</p>"
            f"<p class='lead' style='color:var(--ink);font-size:15.5px'>{conf}</p>"
            f"<p class='lead' style='color:var(--ink);font-size:15.5px'>{para3}</p>"
            f"{gem_html}")


# ── family snapshot ─────────────────────────────────────────────────
_FAMILY_EN = {
    "father": {
        "strong": ("is a genuine source of strength — his guidance, blessings and good fortune back you, and his "
                   "own standing in life tends to be sound. You can lean on him and learn from him"),
        "mixed": ("is broadly well, though some responsibility for him, or the occasional worry about his health or "
                  "work, passes through your life. The bond is caring but asks for effort from your side"),
        "weak": ("may face health concerns, distance or ups and downs in his own life — keep in closer touch, look "
                 "after him, and don't leave important words unsaid")},
    "mother": {
        "strong": ("is caring and emotionally very close — she anchors your peace of mind and her wellbeing lifts "
                   "yours. Her affection is one of the quiet foundations of your life"),
        "mixed": ("is generally fine, with the usual ups and downs in mood or health; she gives a lot and "
                  "occasionally needs reassurance and rest in return"),
        "weak": ("may need real attention for her health or state of mind — your care genuinely matters to her now, "
                 "and time spent with her is never wasted")},
    "siblings": {
        "strong": ("share a warm, dependable bond with you — they stand by you, and there is mutual help and pride "
                   "between you. Cousins and close friends often feel like siblings too"),
        "mixed": ("are on good terms with you overall, with the occasional patch of distance, rivalry or silence; "
                  "a little initiative from you keeps the warmth alive"),
        "weak": ("can feel a little distant or strained — old misunderstandings or competition may linger, but a "
                 "small, sincere effort from you will mend most of the gap")},
    "spouse": {
        "strong": ("is a meaningful source of companionship and support — the relationship pattern favours loyalty, "
                   "shared growth and emotional steadiness"),
        "mixed": ("can be caring but needs patience and honest, open conversation; small misunderstandings should not "
                  "be allowed to harden into distance"),
        "weak": ("needs patience and honest conversation — friction, distance or differing expectations can surface, "
                 "so protect the relationship with communication rather than silence")},
    "children": {
        "strong": ("bring you real joy and are progressing well — you are, or will be, genuinely proud of them, and "
                   "they tend to do you credit"),
        "mixed": ("are doing fine overall and mainly need your steady, encouraging involvement in their studies and "
                  "choices; they respond well when you stay closely engaged"),
        "weak": ("are often on your mind — matters of their birth, health, studies or direction may need patience, "
                 "gentle support and a little prayer; stay steady and hopeful for them")},
}

# people significated by a relative's primary house → a short nature read from its sign
_PERSON_HOUSE = {"father": 9, "mother": 4, "siblings": 3, "spouse": 7, "children": 5}


def _person_adjs(sign):
    t = SIGN_TRAIT.get(sign, "")
    return t.split(" — ")[0] if t else ""


def _person_nature(pc, member, gw):
    h = _PERSON_HOUSE.get(member)
    if not h:
        return ""
    adjs = _person_adjs(house_sign(h, lagna(pc)))
    if not adjs:
        return ""
    who = {"father": "your father", "mother": "your mother",
           "siblings": "your sibling", "spouse": f"your {gw['spouse']}",
           "children": "your child"}[member]
    return f" By nature {who} leans {adjs}."


def _family(pc, caches, gw, lang="en"):
    tbl = FAMILY_HI if lang == "hi" else _FAMILY_EN

    def line(label, member, houses, karakas):
        sc = _strength_of(pc, houses, karakas, caches)
        body = tbl[member][_label(sc)]
        nature = _person_nature(pc, member, gw) if lang == "en" else ""
        return f"<li><b>{label}:</b> {body}.{nature}</li>"

    items = [
        line(U(lang, "fam_father"), "father", [9], ["Sun"]),
        line(U(lang, "fam_mother"), "mother", [4], ["Moon"]),
        line(U(lang, "fam_siblings"), "siblings", [3, 11], ["Mars"]),
        line(U(lang, "fam_spouse", spouse=gw["spouse"]), "spouse", [7], ["Venus", "Jupiter"]),
        line(U(lang, "fam_children"), "children", [5], ["Jupiter"]),
    ]
    return (f"<h2>{U(lang,'h_family')}</h2>"
            f"<p class='lead'>{U(lang,'family_lead')}</p>"
            "<ul style='line-height:1.9'>" + "\n".join(items) + "</ul>")


# ── per-field life-area section ─────────────────────────────────────
RATING_NEAR = {
    "fav": "opens up and looks supportive",
    "mix": "stays steady, with a mix of good and testing phases",
    "chal": "needs patience and care",
}


def _near_term(pc, field, windows, caches, lang="en"):
    rn = RATING_NEAR_HI if lang == "hi" else RATING_NEAR
    segs = []
    for w in windows:
        r = rate_field(pc, field, w, caches)
        segs.append((w, r["rating"]))
    if not segs:
        return U(lang, "near_steady")
    first_w, first_r = segs[0]
    txt = U(lang, "near_first",
            md=_esc(PL(first_w['row']['md'], lang)), ad=_esc(PL(first_w['row']['ad'], lang)),
            end=MON(first_w['row']['end'], lang), word=rn[first_r])
    # find the next window whose rating differs
    for w, rr in segs[1:]:
        if rr != first_r:
            txt += U(lang, "near_change", start=MON(w['row']['start'], lang),
                     ad=_esc(PL(w['row']['ad'], lang)), word=rn[rr])
            break
    return txt


# ── varga-specific diagnosis: WHICH part of the divisional chart is the issue ─
_DIG_BAD = {"debilitated", "enemy_sign", "great_enemy_sign"}
_DIG_GOOD = {"exalted", "moolatrikona", "own_sign"}

# field key → (primary house inside the varga, plain meaning of that house, secondary house)
VARGA_FOCUS = {
    "self": (1, "your body and vitality", None),
    "parents": (9, "your father and elders' support", 4),
    "siblings": (3, "your bond with siblings and your courage", 11),
    "spouse": (7, "your marriage and your partner", 2),
    "children": (5, "children and your creative legacy", 9),
    "profession": (10, "your career and public standing", 6),
    "education": (5, "your grasp of subjects and learning", 4),
    "wealth": (2, "your savings and accumulated wealth", 11),
    "home": (4, "your home, land and domestic peace", 2),
    "strengths": (1, "your innate stamina and resolve", 11),
    "troubles": (6, "your health and recurring troubles", 8),
    "spiritual": (9, "your faith and inner growth", 12),
}


def _v_sign_of_house(vl, h):
    return SIGNS[(sign_index(vl) + h - 1) % 12] if vl else ""


def _v_house_of(vl, sign):
    return ((sign_index(sign) - sign_index(vl)) % 12 + 1) if (vl and sign) else 0


def _v_occupants(pc, code, sign):
    return [p for p in PLANETS if _varga_sign(pc, code, p) == sign and sign]


def _dig(p, s):
    try:
        return get_dignity(p, s) if s else ""
    except Exception:
        return ""


def _varga_diagnosis(pc, code, key, karakas):
    """Inspect the actual divisional chart and name the specific strong/weak aspect
    (which house, which lord, which planet) in plain English. No jargon."""
    if not code:
        return ""
    vl = _varga_lagna(pc, code)
    if not vl:
        return ""
    H, plain, _sec = VARGA_FOCUS.get(key, (1, "this area", None))
    hsign = _v_sign_of_house(vl, H)
    hlord = SIGN_LORDS.get(hsign, "")
    hlordsign = _varga_sign(pc, code, hlord)
    hldig = _dig(hlord, hlordsign)
    hlhouse = _v_house_of(vl, hlordsign)
    occ = _v_occupants(pc, code, hsign)
    # malefics only "afflict" when: not in an upachaya house (3/6/10/11 where they do well),
    # not the house's own lord, and not dignified in that sign.
    if H in (3, 6, 10, 11):
        mal = []
    else:
        mal = [m for m in occ if m in NAT_MALEFIC and m != hlord
               and _dig(m, hsign) not in _DIG_GOOD]
    ben = [b for b in occ if b in NAT_BENEFIC and b != hlord]

    kar = next((k for k in karakas if k), "")
    karsign = _varga_sign(pc, code, kar) if kar else ""
    kardig = _dig(kar, karsign)
    karhouse = _v_house_of(vl, karsign)

    problems, strengths = [], []
    if hldig in _DIG_BAD:
        problems.append(f"the planet that governs {plain} ({hlord}) sits weak in this chart")
    elif hldig in _DIG_GOOD:
        strengths.append(f"the planet that governs {plain} ({hlord}) is strong and dignified")
    if hlhouse in DUSTHANA:
        problems.append(f"its ruler slips into a difficult corner of the chart (the {_ord(hlhouse)})")
    elif hlhouse in GOOD_HOUSES:
        strengths.append("its ruler rests in a supportive, well-placed position")
    if mal:
        problems.append(f"a harsh planet ({', '.join(mal)}) sits right on the part that rules {plain}")
    if ben and not mal:
        strengths.append(f"a gentle planet ({', '.join(ben)}) protects the part that rules {plain}")
    if kar:
        role = {"children": "the giver of children", "spouse": "the giver of marriage",
                "wealth": "the giver of wealth", "profession": "the giver of career",
                "education": "the giver of knowledge", "troubles": "the marker of illness",
                "siblings": "the giver of courage", "self": "the lord of vitality",
                "parents": "the marker of the father", "home": "the marker of property",
                "strengths": "the source of strength", "spiritual": "the marker of dharma"}.get(key, "its natural significator")
        if kardig in _DIG_BAD:
            problems.append(f"{kar}, {role}, is weak here")
        elif kardig in _DIG_GOOD:
            strengths.append(f"{kar}, {role}, is strong here")
        if karhouse in DUSTHANA:
            problems.append(f"{kar} ({role}) hides in a difficult house")

    lead = "Looking inside this specific chart: "
    if problems and strengths:
        return f"{lead}{strengths[0]}, but {problems[0]} — that is the precise spot that needs your attention."
    if problems:
        tail = f", and {problems[1]}" if len(problems) > 1 else ""
        return f"{lead}{problems[0]}{tail} — that is where the real difficulty lies."
    if strengths:
        tail = f", and {strengths[1]}" if len(strengths) > 1 else ""
        return f"{lead}{strengths[0]}{tail} — this area is genuinely well-built in your chart."
    return ""


def _promise_status_text(promise: dict, lang: str = "en") -> str:
    """Human-facing promise label; intentionally separate from timing verdict."""
    label = promise.get("label") or "Limited evidence"
    if lang == "hi":
        return {
            "Strongly supported": "बहुत मजबूत समर्थन",
            "Supported": "समर्थित",
            "Mixed promise": "मिश्रित संकेत",
            "Not strongly supported": "मजबूत समर्थन नहीं",
            "Limited evidence": "सीमित प्रमाण",
        }.get(label, label)
    return label


def _promise_teaser(key: str, promise: dict, lang: str = "en") -> str:
    """Free-tier copy: useful promise status, but withholds evidence/timing depth."""
    label = _promise_status_text(promise, lang)
    if lang == "hi":
        return (f"<div class='why'><b>क्या यह क्षेत्र आपके जीवन में समर्थित है?</b> {label}. "
                f"विस्तृत कारण, समय-खिड़की और व्यक्तिगत उपाय पूर्ण रिपोर्ट में उपलब्ध हैं।</div>")
    return (f"<div class='why'><b>Is this area genuinely supported in your chart?</b> "
            f"{_esc(label)}. The detailed evidence, strongest timing window and personalised "
            f"action/remedy are part of the full reading.</div>")


def _promise_timing(pc, field, promise: dict, windows, caches, lang: str = "en") -> str:
    """Find the first strong/usable future activation only after promise passes."""
    if not promise.get("timing_allowed"):
        return ""
    candidates = []
    for w in windows:
        try:
            r = rate_field(pc, field, w, caches)
        except Exception:
            continue
        rating = str(r.get("rating") or "")
        if rating in ("fav", "mix"):
            candidates.append((w, rating))
    if not candidates:
        return ""
    w, rating = candidates[0]
    start = MON(w["row"]["start"], lang)
    end = MON(w["row"]["end"], lang)
    word = (RATING_NEAR_HI if lang == "hi" else RATING_NEAR).get(rating, "supportive")
    if lang == "hi":
        return (f"<div class='why'><b>समय संकेत:</b> {start} – {end} के दौरान "
                f"यह क्षेत्र {word} दिखता है।</div>")
    return (f"<div class='why'><b>Strongest upcoming activation:</b> {start} – {end} — "
            f"this area {word}.</div>")


def _promise_evidence_html(promise: dict, lang: str = "en") -> str:
    support = promise.get("supporting_evidence") or []
    caution = promise.get("caution_evidence") or []
    if lang == "hi":
        items = "".join(f"<li>{_esc(x)}</li>" for x in (support[:3] + caution[:2]))
        return (f"<details><summary>तकनीकी आधार — वादा/संकेत</summary><ul>{items}</ul></details>"
                if items else "")
    items = "".join(f"<li>{_esc(x)}</li>" for x in (support[:3] + caution[:2]))
    return (f"<details><summary>Why Graharekha says this</summary><ul>{items}</ul></details>"
            if items else "")


_PROMISE_HEADLINE_EN = {
    "spouse": {
        "strongly_supported": "Your relationship pattern is strongly supported.",
        "supported": "Your chart supports meaningful relationship potential.",
        "mixed": "Your relationship picture is possible but mixed.",
        "weak": "Relationships need more conscious effort in your chart.",
        "insufficient_evidence": "There is not enough evidence for a strong relationship conclusion.",
    },
    "children": {
        "strongly_supported": "The chart strongly supports children and parenthood themes.",
        "supported": "The chart supports meaningful children and parenthood potential.",
        "mixed": "The children/parenthood picture is possible but mixed.",
        "weak": "The children/parenthood area needs patience and support.",
        "insufficient_evidence": "There is not enough evidence for a strong children conclusion.",
    },
    "profession": {
        "strongly_supported": "Professional growth, status or recognition is strongly supported.",
        "supported": "Career growth and visible contribution are supported.",
        "mixed": "Career growth is possible, but the path is mixed.",
        "weak": "Career growth requires more deliberate effort and skill-building.",
        "insufficient_evidence": "There is not enough evidence for a strong career conclusion.",
    },
    "wealth": {
        "strongly_supported": "The chart strongly supports building income and financial resources.",
        "supported": "Financial growth and accumulation are supported.",
        "mixed": "Income potential is present, but wealth accumulation is mixed.",
        "weak": "Wealth is not strongly promised; disciplined accumulation matters more.",
        "insufficient_evidence": "There is not enough evidence for a strong wealth conclusion.",
    },
    "troubles": {
        "strongly_supported": "The chart shows strong resilience against recurring life difficulties.",
        "supported": "The chart gives useful protection, provided routine and prevention are maintained.",
        "mixed": "Wellbeing and challenge indicators are mixed, so prevention matters.",
        "weak": "This is an area where prevention, routine and practical care deserve extra attention.",
        "insufficient_evidence": "There is not enough evidence for a strong wellbeing conclusion.",
    },
}

_PROMISE_HEADLINE_HI = {
    "spouse": {
        "strongly_supported": "आपके संबंध पैटर्न को मजबूत समर्थन मिलता है।",
        "supported": "आपकी कुंडली सार्थक संबंध की संभावना दिखाती है।",
        "mixed": "संबंध संभव हैं, लेकिन संकेत मिश्रित हैं।",
        "weak": "संबंधों के लिए अधिक सचेत प्रयास की आवश्यकता है।",
        "insufficient_evidence": "मजबूत संबंध निष्कर्ष के लिए पर्याप्त प्रमाण नहीं हैं।",
    },
    "children": {
        "strongly_supported": "संतान और पarenthood के विषय को मजबूत समर्थन मिलता है।",
        "supported": "संतान और पarenthood की सार्थक संभावना दिखती है।",
        "mixed": "संतान का चित्र संभव है, लेकिन मिश्रित है।",
        "weak": "संतान क्षेत्र को धैर्य और सहयोग चाहिए।",
        "insufficient_evidence": "मजबूत संतान निष्कर्ष के लिए पर्याप्त प्रमाण नहीं हैं।",
    },
    "profession": {
        "strongly_supported": "पेशेवर विकास, स्थिति या मान्यता को मजबूत समर्थन मिलता है।",
        "supported": "करियर विकास और दृश्य योगदान समर्थित हैं।",
        "mixed": "करियर विकास संभव है, लेकिन रास्ता मिश्रित है।",
        "weak": "करियर विकास के लिए अधिक जानबूझकर प्रयास चाहिए।",
        "insufficient_evidence": "मजबूत करियर निष्कर्ष के लिए पर्याप्त प्रमाण नहीं हैं।",
    },
    "wealth": {
        "strongly_supported": "आय और वित्तीय संसाधन बनाने को मजबूत समर्थन मिलता है।",
        "supported": "वित्तीय विकास और संचय समर्थित हैं।",
        "mixed": "आय की संभावना है, लेकिन संचय मिश्रित है।",
        "weak": "धन मजबूती से वादा नहीं; अनुशासित संचय अधिक महत्वपूर्ण है।",
        "insufficient_evidence": "मजबूत धन निष्कर्ष के लिए पर्याप्त प्रमाण नहीं हैं।",
    },
    "troubles": {
        "strongly_supported": "आवर्ती कठिनाइयों के खिलाफ मजबूत लचीलापन दिखता है।",
        "supported": "नियमित देखभाल और रोकथाम के साथ उपयोगी सुरक्षा मिलती है।",
        "mixed": "स्वास्थ्य और चुनौती संकेत मिश्रित हैं; रोकथाम महत्वपूर्ण है।",
        "weak": "रोकथाम, दिनचर्या और व्यावहारिक देखभाल पर अतिरिक्त ध्यान दें।",
        "insufficient_evidence": "मजबूत wellbeing निष्कर्ष के लिए पर्याप्त प्रमाण नहीं हैं।",
    },
}


def _field_promise_headline(key: str, promise: dict, lang: str = "en") -> str:
    status = promise.get("status")
    table = _PROMISE_HEADLINE_HI if lang == "hi" else _PROMISE_HEADLINE_EN
    if key in table:
        return table[key].get(status, "")
    return ""


_ACTIVATION_LABEL_HI = {
    "strongly_active": "बहुत सक्रिय",
    "active": "सक्रिय",
    "mixed": "मिश्रित",
    "weak": "कम सक्रियता",
    "inactive": "वर्तमान में सक्रिय नहीं",
    "insufficient_evidence": "पर्याप्त प्रमाण नहीं",
}


def _field_current_activation_status(pc, field, windows, caches) -> str:
    """Timing-only activation for one field — mirrors resolve_activation's intent

    without a second scoring system: it reads the rating this module already
    computes for the *current* window and nothing else, so promise and
    activation stay two separate questions here just as they do in the
    cards-v2 pipeline (P0-8).
    """
    cur_win = next((w for w in windows if w.get("is_now")), windows[0] if windows else None)
    if not cur_win:
        return "insufficient_evidence"
    try:
        rating = rate_field(pc, field, cur_win, caches).get("rating")
    except Exception:  # noqa: BLE001
        return "insufficient_evidence"
    return {"fav": "active", "mix": "mixed", "chal": "weak"}.get(rating, "insufficient_evidence")


def _activation_status_text(status: str, lang: str = "en") -> str:
    if lang == "hi":
        return _ACTIVATION_LABEL_HI.get(status, _ACTIVATION_LABEL_HI["insufficient_evidence"])
    from narration.status_vocab import status_label
    return status_label(status, kind="activation")


def _field_section(pc, fdef, windows, caches, table, gw, gem_report=None, lang="en", access="paid"):
    key, title, rel, varga, houses, karakas = fdef
    field = (title, key, varga, houses, karakas)
    sc = _strength_of(pc, houses, karakas, caches, key=key)
    lab = _label(sc)
    vcls = (_varga_data(pc, varga, varga, "") or {}).get("vcls", "mixed") if varga else "mixed"

    promise = resolve_promise(pc, key)

    title_disp = FIELD_TITLE_HI.get(key, title) if lang == "hi" else title
    where = _where_you_stand(key, lab, vcls, gw, lang)
    diag = _varga_diagnosis(pc, varga, key, karakas) if (lang == "en" and access != "free") else ""
    if diag:
        where = f"{where} {diag}"
    near = (_near_term(pc, field, windows, caches, lang) if access != "free"
            else ("A fuller timing map is available in the complete reading." if lang == "en"
                  else "पूरी समय-रेखा विस्तृत रिपोर्ट में उपलब्ध है।"))

    promise_headline = _field_promise_headline(key, promise, lang)
    promise_html = ""
    if promise_headline:
        if key == "troubles":
            label_word = "चुनौती पैटर्न" if lang == "hi" else "Challenge pattern"
        else:
            label_word = "वादा" if lang == "hi" else "Promise"
        promise_html = f"<div class='pred'><b>{label_word}:</b> {_esc(promise_headline)}</div>"

    # Activation is a separate question from promise (P0-1/P0-8): shown as a
    # short status word on both free and paid so the two never look like the
    # same verdict, with depth reserved for paid via `near`/`timing_html` below.
    activation_status = _field_current_activation_status(pc, field, windows, caches)
    activation_word = "वर्तमान सक्रियता" if lang == "hi" else "Current activation"
    promise_html += (
        f"<div class='pred'><b>{activation_word}:</b> "
        f"{_esc(_activation_status_text(activation_status, lang))}</div>"
    )

    if access == "free":
        promise_html += _promise_teaser(key, promise, lang)
        timing_html = ""
        evidence_html = ""
    else:
        strength_word = "वादा शक्ति" if lang == "hi" else "Promise strength"
        promise_html += (f"<div class='why'><b>{strength_word}:</b> "
                         f"{_esc(_promise_status_text(promise, lang))} "
                         f"({promise.get('confidence', 'low')} confidence).</div>")
        timing_html = _promise_timing(pc, field, promise, windows, caches, lang)
        evidence_html = _promise_evidence_html(promise, lang)

    remedy_html = ""
    if access != "free" and promise.get("status") in {"weak", "insufficient_evidence"} and key in AREA_REMEDY:
        deity, practice, day, charity, gem_planet = AREA_REMEDY[key]
        gem_bit = _field_gem_bit(gem_report, gem_planet)
        remedy_html = (f"<div class='why'><b>If this area feels heavy — supportive action:</b> "
                       f"{_esc(practice)}; best on <b>{_esc(day)}</b>. "
                       f"You may also offer {_esc(charity)} and keep faith in {_esc(deity)}."
                       f"{gem_bit}</div>")
    else:
        strained = lab == "weak" or any(rate_field(pc, field, w, caches)["rating"] == "chal" for w in windows[:2])
        if access != "free" and strained and key in AREA_REMEDY:
            deity, practice, day, charity, gem_planet = AREA_REMEDY[key]
            gem_bit = _field_gem_bit(gem_report, gem_planet)
            remedy_html = (f"<div class='why'><b>If this area feels heavy — supportive action:</b> "
                           f"{_esc(practice)}; best on <b>{_esc(day)}</b>. "
                           f"You may also offer {_esc(charity)} and keep faith in {_esc(deity)}."
                           f"{gem_bit}</div>")

    cau = _caution_windows(table, houses)
    cau_html = ""
    if access != "free" and cau:
        spans = []
        for w in cau[:3]:
            pls = ", ".join(PL(m, lang) for m in sorted(w["planets"]))
            hs = ", ".join(ORDw(h, lang) for h in sorted(w["houses"]))
            spans.append(U(lang, "caution_span",
                           m1=MON(w['start'], lang), m2=MON(w['end'], lang), pls=pls, hs=hs))
        cau_html = (f"<div class='why' style='border-top-color:#5a2a2a'><b>{U(lang,'caution')}</b> "
                    + "; ".join(spans) + ". " + U(lang, "caution_tail") + "</div>")

    cls = {"strong": "", "mixed": "partial", "weak": "weak"}[lab]
    badge = {"strong": U(lang, "badge_strong"), "mixed": U(lang, "badge_mixed"),
             "weak": U(lang, "badge_weak")}[lab]
    return (f"<div class='card {cls}'>"
            f"<div class='top'><span class='title'>{_esc(title_disp)} <span class='badge'>{varga or 'D1'}</span></span>"
            f"<span class='no'>{badge}</span></div>"
            f"{promise_html}"
            f"<div class='pred'><b>{U(lang,'where')}</b> {where}</div>"
            f"<div class='pred'><b>{U(lang,'near')}</b> {near}</div>"
            f"{timing_html}{evidence_html}{remedy_html}{cau_html}</div>")


def _where_you_stand(key, lab, vcls, gw, lang="en"):
    if lang == "hi":
        txt = WHERE_HI.get(key, {}).get(lab, "")
        return txt.format(spouse=gw["spouse"]) if "{spouse}" in txt else txt
    T = {
        "self": {
            "strong": "Your body and vitality are fundamentally strong — you recover well and carry a natural resilience.",
            "mixed": "Your health is generally okay but sensitive to stress and routine — when you slip on sleep or food, you feel it.",
            "weak": "Your constitution needs care — energy dips, and you must guard rest, diet and not overburden yourself.",
        },
        "parents": {
            "strong": "You come from a supportive parental foundation; their blessings and fortune genuinely help you.",
            "mixed": "Your bond with your parents is caring but carries some duty and occasional worry about their health.",
            "weak": "There is karmic weight around your parents — health concerns or responsibility may rest on you; stay attentive.",
        },
        "siblings": {
            "strong": "You enjoy a strong, supportive equation with your brother(s)/sister(s) — they stand by you.",
            "mixed": "Sibling ties are warm but can carry competition or distance; effort keeps them close.",
            "weak": "Sibling relationships need healing — misunderstanding or distance is shown; be the one to reach out.",
        },
        "spouse": {
            "strong": f"Your married life is a real strength — your {gw['spouse']} is loyal and a true partner in your journey.",
            "mixed": f"Your relationship is loving but needs tending; with patience and honest talk, your {gw['spouse']} stays close.",
            "weak": f"Partnership is a growth area — friction or distance with your {gw['spouse']} is shown; communication and patience are your remedy.",
        },
        "children": {
            "strong": "Children are a source of pride and happiness — they progress well and bring you joy.",
            "mixed": "Your children are doing fine overall; their studies or direction will need your steady involvement.",
            "weak": "There is concern around children — conception, health or studies need patience, care and prayer.",
        },
        "profession": {
            "strong": "Your career is well supported — you have the standing and capability to rise and be recognised.",
            "mixed": "Work moves in cycles for you — good growth follows patient effort, with the occasional plateau.",
            "weak": "Career is your test area — progress feels slow and political; persistence and skill-building are key.",
        },
        "education": {
            "strong": "You have a sharp mind for learning — education and skills come to you and open doors.",
            "mixed": "You can study well but need focus and the right environment; distractions are the main obstacle.",
            "weak": "Learning takes extra effort and discipline for you — structured routine and mentorship make the difference.",
        },
        "wealth": {
            "strong": "Money flows reasonably well and you can build solid savings; your financial instincts are sound.",
            "mixed": "Finances rise and fall — you earn well but spending and surprises keep it from settling; budget consciously.",
            "weak": "Wealth needs careful management — income can be irregular and outflows high; avoid risky schemes and debt.",
        },
        "home": {
            "strong": "Home and property are a comfort and an asset — you enjoy domestic peace and can own land/house.",
            "mixed": "Home life is fine with periodic tension or relocation; property matters resolve with patience.",
            "weak": "There is unrest around home/property — disputes, shifts or lack of peace; handle paperwork carefully.",
        },
        "strengths": {
            "strong": "Inwardly you are tough and capable — once committed, your stamina and will see you through.",
            "mixed": "Your strengths are real but come in bursts; consistency is what converts your talent into results.",
            "weak": "You under-rate your own power — build confidence slowly; your resilience is greater than you feel.",
        },
        "troubles": {
            "strong": "You are well-protected from major hazards — your chart resists chronic trouble; basic care is enough.",
            "mixed": "Watch the usual stress-linked issues (digestion, sleep, joints); prevention keeps you clear.",
            "weak": "Be proactive about health — the chart flags vulnerability; regular check-ups and a clean routine matter.",
        },
        "spiritual": {
            "strong": "You have a naturally reflective, spiritual mind — practice and inner work bring you real peace.",
            "mixed": "Your mind seeks meaning but gets pulled by daily noise; a small daily practice steadies you.",
            "weak": "Your mind can feel restless or low — meditation, prayer and routine are not optional for you; they heal.",
        },
    }
    return T.get(key, {}).get(lab, "")


# ── ordinal ─────────────────────────────────────────────────────────
def _ord(n):
    if not n:
        return "?"
    s = {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")
    return s


# ── language-aware hero ─────────────────────────────────────────────
def _hero_lang(client_name, lg, meta, lang):
    return f"""<div class="hero">
    <h1>{U(lang,'title')}</h1>
    <div class="sub">{U(lang,'sub')}</div>
    <div class="meta">
      <span class="chip">{U(lang,'name')}: <b>{_esc(client_name)}</b></span>
      <span class="chip">{U(lang,'lagna')}: <b>{_esc(SG(lg, lang))}</b></span>
      <span class="chip">{U(lang,'dob')}: <b>{_esc(meta.get('dob',''))}</b></span>
      <span class="chip">{U(lang,'time')}: <b>{_esc(meta.get('birth_time',''))}</b></span>
      <span class="chip">{U(lang,'place')}: <b>{_esc(meta.get('birth_place',''))}</b></span>
    </div>
  </div>"""


_LANG_CSS = """
.langbar{position:sticky;top:0;z-index:60;display:flex;gap:8px;justify-content:flex-end;
  align-items:center;padding:8px 0 12px;margin:-6px 0 6px}
.langbar .lbl{margin-right:auto;font-size:12.5px;color:var(--muted);letter-spacing:.04em;text-transform:uppercase}
.langbtn{cursor:pointer;border:1px solid var(--line);background:transparent;color:var(--ink);
  border-radius:999px;padding:6px 16px;font-size:13.5px;font-weight:600;transition:.15s}
.langbtn:hover{border-color:var(--accent)}
.langbtn.active{background:var(--accent);color:#10131a;border-color:var(--accent)}
.langpane[hidden]{display:none}
.lang-hi{font-family:"Noto Sans Devanagari","Nirmala UI","Mangal",system-ui,sans-serif;line-height:1.75}
"""


def _pane(pc, client_name, lg, meta, gender, windows, caches, table, gem_report, lang, access="paid"):
    gw = _gender_words(gender, lang)
    sections = [_field_section(pc, fdef, windows, caches, table, gw, gem_report, lang, access)
                for fdef in _narr_fields(gender)]
    return (
        _hero_lang(client_name, lg, meta, lang)
        + _opening(pc, windows, caches, table, gender, gem_report, lang)
        + _potential_section(pc, lang)
        + _family(pc, caches, gw, lang)
        + f"<h2>{U(lang,'h_areas')}</h2>"
        + f"<p class='lead'>{U(lang,'areas_lead')}</p>"
        + "<div class='cards'>" + "\n".join(sections) + "</div>"
        + f"<div class='note'><b>{U(lang,'remedy_note_title')}</b> {U(lang,'remedy_note')}</div>"
    )


# ── assemble ────────────────────────────────────────────────────────
def build_html(pc, client_name="Client", lat=None, lon=None, tz=None, access="paid"):
    meta = pc.get("meta", {})
    gender = meta.get("gender", 0)
    if lat is not None and lon is not None:
        pc.setdefault("meta", {})["_coords"] = {
            "latitude": lat, "longitude": lon, "timezone": 5.5 if tz is None else tz}

    windows, caches = compute_windows(pc, lat, lon, tz, years=2)
    if not windows:
        windows, caches = compute_windows(pc, lat, lon, tz, years=4)
    table = _monthly_transits(pc, months=24)
    gem_report = _gem_ctx(pc)

    lg = lagna(pc)
    pane_en = _pane(pc, client_name, lg, meta, gender, windows, caches, table, gem_report, "en", access)
    pane_hi = _pane(pc, client_name, lg, meta, gender, windows, caches, table, gem_report, "hi", access)

    langbar = (
        "<div class='langbar'>"
        "<span class='lbl'>Language / भाषा</span>"
        f"<button class='langbtn active' data-lang='en' onclick=\"setLang('en')\">{U('en','toggle_en')}</button>"
        f"<button class='langbtn' data-lang='hi' onclick=\"setLang('hi')\">{U('hi','toggle_hi')}</button>"
        "</div>"
    )
    script = """<script>
function setLang(l){
  document.querySelectorAll('.langpane').forEach(function(p){p.hidden = (p.getAttribute('data-lang')!==l);});
  document.querySelectorAll('.langbtn').forEach(function(b){b.classList.toggle('active', b.getAttribute('data-lang')===l);});
  try{localStorage.setItem('pr_lang', l);}catch(e){}
  document.documentElement.lang = l;
}
(function(){var s='en';try{s=localStorage.getItem('pr_lang')||'en';}catch(e){}setLang(s);})();
</script>"""

    body = (
        f"<style>{_LANG_CSS}</style>"
        + langbar
        + f"<div class='langpane lang-en' data-lang='en'>{pane_en}</div>"
        + f"<div class='langpane lang-hi' data-lang='hi' hidden>{pane_hi}</div>"
        + script
    )
    return _doc(f"Personal Reading — {_esc(client_name)}", body)


def write_report(pc, out_dir, client_name="Client", lat=None, lon=None, tz=None, access="paid"):
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"Personal_Reading_{client_name}.html"
    html = build_html(pc, client_name, lat, lon, tz, access=access)
    try:
        from client_report_html import finalize_report_html
        html = finalize_report_html(html, client_name)
    except ImportError:
        pass
    out.write_text(html, encoding="utf-8")
    return out


if __name__ == "__main__":
    import argparse
    from astro_chart_bridge import compute_chart

    ap = argparse.ArgumentParser(description="Final plain-English consultation report")
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
    path = write_report(pc, out_dir, args.name, args.lat, args.lon, args.tz)
    print(f"Wrote {path}")
