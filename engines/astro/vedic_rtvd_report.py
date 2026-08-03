#!/usr/bin/env python3
"""
vedic_rtvd_report.py — Deterministic Rasi Tulya Vatsara Dasa (RTVD) report (NO LLM).

Dr. K. Guru Rajesh's RTVD method (rules16.md): each year of life activates one house
from the Ascendant; the year-sign's lord and its placement reveal what that year delivers.

Active house = ((age − 1) mod 12) + 1 (book table: ages 1,13,25… = 1st house). Whole-sign from lagna.
Prediction-first HTML — tables relegated to a collapsed appendix.
"""
from __future__ import annotations

import argparse
import html
from datetime import datetime
from pathlib import Path

from astro_precompute import NAK_TO_DASHA_LORD, resolve_precompute
from chart_resolve import add_chart_source_args, chart_kwargs_from_args
from rtvd_foundation import (
    age_reference_html,
    chart_essentials_html,
    methodology_html,
    vimshottari_cross_html,
)
from rtvd_year import (
    illustrative_card_html,
    topic_prose,
    topic_window_years,
)

BASE_DIR = Path(__file__).resolve().parent
GOLD = BASE_DIR / "reports" / "Vedic_RTVD_Ritz_20260408.html"

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

NATURAL_BENEFICS = frozenset({"Jupiter", "Venus", "Moon", "Mercury"})
NATURAL_MALEFICS = frozenset({"Saturn", "Mars", "Rahu", "Ketu", "Sun"})

AREA_USER = {
    1: "your personal image and confidence", 2: "family money and what you save",
    3: "your own effort and networking", 4: "home, roots, and emotional security",
    5: "creativity, children, and romance", 6: "daily work and health habits",
    7: "marriage and committed partnership", 8: "shared finances and deep bonding",
    9: "luck, teachers, and travel", 10: "career and public reputation",
    11: "income from networks and fulfilled goals", 12: "foreign ties, rest, and letting go",
}

HOUSE_YEAR = {
    1: "who you are and how you present yourself",
    2: "money, savings, and family resources",
    3: "courage, skills, and communication",
    4: "home, property, and inner peace",
    5: "children, romance, and creative projects",
    6: "work pressure, service, and health routines",
    7: "marriage, partnerships, and the public other",
    8: "deep change, shared money, and stress tests",
    9: "luck, mentors, long travel, and upliftment",
    10: "career, status, and professional milestones",
    11: "gains, income, and fulfilled desires",
    12: "foreign matters, expenses, and letting go",
}

HOUSE_LABEL = {
    1: "Personal reset", 2: "Wealth & family", 3: "Effort & skills", 4: "Home & roots",
    5: "Creativity & children", 6: "Work & health", 7: "Partnership year",
    8: "Deep change", 9: "Luck & travel", 10: "Career push", 11: "Gains & income",
    12: "Foreign & retreat",
}

# Book topic chapters — which active houses signal each life domain
WEALTH_HOUSES = {1, 2, 4, 5, 9, 10, 11}
CAREER_HOUSES = {1, 4, 10}
MARRIAGE_HOUSES = {1, 4, 7, 12}
CHILDREN_HOUSES = {1, 2, 5, 9, 11}
HEALTH_HOUSES = {6, 8, 12}
GROWTH_HOUSES = {9, 5, 1}

DOMAIN_LEAD = {
    "wealth": "Money in your chart follows year-by-year house activations — steady habits beat lucky swings.",
    "career": "Career years run when the 10th house or your public-life zone turns on.",
    "marriage": "Love years light up on 7th-house ages or when Venus, Jupiter, or Moon colours the year.",
    "children": "Children and creative years favour 2nd and 5th-house activations.",
    "health": "6th, 8th, and 12th-house years ask for extra routine care.",
    "growth": "9th-house years and benefic year-lords open luck, mentors, and travel.",
    "parents": "Father themes track 4th, 8th, and 9th-house years; mother themes track 3rd, 4th, and 11th.",
    "siblings": "Sibling and close-peer years activate on 3rd and 11th-house cycles.",
}

PLANET_REMEDY = {
    "Sun": "Sundays: sunlight walk, respect elders, keep vitamin D and routine check-ups sensible.",
    "Moon": "Mondays: calm evening, simple food, journal feelings, call family.",
    "Mars": "Tuesdays: exercise cleanly, channel anger into sport or work — not arguments.",
    "Mercury": "Wednesdays: clear emails, organise papers, study one useful skill.",
    "Jupiter": "Thursdays: modest charity or teaching; avoid over-promising or risky loans.",
    "Venus": "Fridays: art, kindness, beauty at home — nurture partner or close friends.",
    "Saturn": "Saturdays: discipline, sleep on time, help someone older; patience pays.",
    "Rahu": "Ground weekly: limit screens and speculation; stick to one practical goal.",
    "Ketu": "Quiet hour daily: meditation, finish an old task, let one draining habit go.",
}


def _e(s) -> str:
    return html.escape(str(s))


def _nodot(s: str) -> str:
    return s.rstrip().rstrip(".").rstrip()


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _ord(n) -> str:
    n = int(n)
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th"))


def house_of(sign: str, lagna: str) -> int:
    return (SIGNS.index(sign) - SIGNS.index(lagna)) % 12 + 1


def from_x(sign: str, base_sign: str) -> int:
    return (SIGNS.index(sign) - SIGNS.index(base_sign)) % 12 + 1


class RTVD:
    def __init__(self, pc: dict):
        self.pc = pc
        self.lagna = pc["meta"]["lagna_sign"]
        self.name = pc["meta"]["client"]
        self.age = int(pc["meta"]["age"])
        self.lagna_idx = SIGNS.index(self.lagna)
        self.planets = {}
        for nm, v in pc["planets"].items():
            self.planets[nm] = {
                "sign": v["sign"], "degree": v.get("degree_in_sign", 0.0),
                "nakshatra": v.get("nakshatra", ""), "pada": v.get("pada", ""),
                "dignity": v.get("dignity", "neutral_sign"),
                "house": house_of(v["sign"], self.lagna),
                "retro": bool(v.get("retrograde", False)),
            }
        self.moon_sign = self.planets["Moon"]["sign"]
        self.houses = {}
        for h in range(1, 13):
            sign = SIGNS[(self.lagna_idx + h - 1) % 12]
            lord = SIGN_LORD[sign]
            lp = self.planets.get(lord, {})
            self.houses[h] = {
                "sign": sign, "lord": lord, "lord_sign": lp.get("sign", ""),
                "lord_house": lp.get("house", 0),
                "lord_dignity": lp.get("dignity", "neutral_sign"),
                "tenants": [nm for nm, v in self.planets.items() if v["sign"] == sign],
            }

    def house_for_age(self, age: int) -> int:
        if age < 1:
            return 1
        return ((age - 1) % 12) + 1

    def year(self, age: int) -> dict:
        h = self.house_for_age(age)
        info = dict(self.houses[h])
        info["age"] = age
        info["house"] = h
        info["calendar"] = int(self.pc["meta"]["dob"][:4]) + age
        info["other_house"] = next(
            (hh for hh in range(1, 13) if hh != h and self.houses[hh]["lord"] == info["lord"]), None)
        info["from_moon"] = from_x(info["sign"], self.moon_sign)
        return info


# ───────────────────────── prediction engine (human NL) ─────────────────────────


def _verdict_tag(kind: str) -> str:
    labels = {
        "good": ("Good phase", "tag-good"),
        "attention": ("Needs attention", "tag-warn"),
        "hard": ("Challenging — pace yourself", "tag-hard"),
    }
    text, cls = labels.get(kind, ("Mixed", "tag-warn"))
    return f'<span class="{cls}">{text}</span>'


def _year_verdict(r: RTVD, y: dict) -> str:
    tone = _year_tone(r, y)
    return {"peak": "good", "positive": "good", "caution": "hard", "mixed": "attention"}.get(tone, "attention")


def _area(h: int) -> str:
    return AREA_USER.get(h, "life matters")


def _nak_lord(r: RTVD, planet: str) -> str:
    return NAK_TO_DASHA_LORD.get(r.planets[planet].get("nakshatra", ""), "")


def _mass_on_sign(r: RTVD, sign: str) -> tuple[int, int, list[str]]:
    tenants = [p for p, v in r.planets.items() if v["sign"] == sign]
    ben = sum(1 for p in tenants if p in NATURAL_BENEFICS)
    mal = sum(1 for p in tenants if p in NATURAL_MALEFICS)
    return ben, mal, tenants


def _year_tone(r: RTVD, y: dict) -> str:
    lord = y["lord"]
    lp = r.planets[lord]
    _, mal, _ = _mass_on_sign(r, y["sign"])
    if lp["dignity"] in ("exalted", "own_sign", "moolatrikona") and mal < 2:
        return "peak"
    if y["house"] in (6, 8, 12) or lp["house"] in (6, 8, 12) or mal >= 2:
        return "caution"
    if lp["dignity"] == "debilitated":
        return "caution"
    if y["house"] in (7, 9, 10, 11) or lp["house"] in (7, 10, 11):
        return "positive"
    return "mixed"


def _lord_strength_note(r: RTVD, lord: str) -> str:
    dig = r.planets[lord]["dignity"]
    if dig == "exalted":
        return "The year's ruling planet is strong — results can land well if you stay grounded."
    if dig == "debilitated":
        return "The year's ruling planet is under strain — slow, steady effort beats shortcuts."
    if dig in ("own_sign", "moolatrikona"):
        return "The year's ruling planet is well placed — you have natural support here."
    return ""


def _year_plain(r: RTVD, y: dict, rich: bool = False) -> str:
    """Short plain-English year reading."""
    lord = y["lord"]
    lp = r.planets[lord]
    lh = lp["house"]
    parts = [
        f"<strong>{HOUSE_YEAR[y['house']]}</strong> — results run through {_area(lh)} "
        f"(<strong>{lord}</strong> rules the year)."
    ]
    if y["tenants"]:
        parts.append(f"{', '.join(y['tenants'])} colours the mood.")
    ben, mal, _ = _mass_on_sign(r, y["sign"])
    if mal >= 2:
        parts.append("Go slow — stress planets touch this year; protect health and agreements.")
    elif ben >= 2:
        parts.append("Benefic support is strong.")
    if rich:
        note = _lord_strength_note(r, lord)
        if note:
            parts.append(note)
    return " ".join(parts)


def _domain_line(r: RTVD, y: dict, domain: str) -> str | None:
    """One-line domain prediction for a year, or None if weak signal."""
    lord = y["lord"]
    lp = r.planets[lord]
    lh, h = lp["house"], y["house"]
    tenants = set(y["tenants"])
    cal = f"{y['calendar']}–{y['calendar'] + 1}"

    if domain == "wealth":
        if h in WEALTH_HOUSES or lh in (2, 11) or lord in tenants and lh in (2, 11):
            if lh in (2, 11) or h in (2, 11):
                return (f"<strong>Age {y['age']} ({cal}):</strong> stronger money flow or a chance to "
                        f"consolidate savings — income themes are active.")
            return (f"<strong>Age {y['age']} ({cal}):</strong> finances move — save in good months, "
                    f"clear old dues before new spends.")
    if domain == "career":
        if h in CAREER_HOUSES or lh == 10:
            if lh == 10:
                return (f"<strong>Age {y['age']} ({cal}):</strong> career and public name in focus — "
                        f"push one promotion, project, or role change.")
            return (f"<strong>Age {y['age']} ({cal}):</strong> professional life shifts — "
                    f"build skill first, then visibility.")
    if domain == "marriage":
        strong = h == 7 or lh == 7 or (lord in ("Venus", "Jupiter") and lh in (5, 7, 10))
        mild = h in (4, 12) and lord in ("Venus", "Jupiter", "Moon")
        if strong:
            return (f"<strong>Age {y['age']} ({cal}):</strong> partnership weighs heavily — "
                    f"meeting, deepening, or deciding a bond becomes easier.")
        if mild:
            return (f"<strong>Age {y['age']} ({cal}):</strong> relationship themes surface — "
                    f"honest talk beats polite silence.")
    if domain == "children":
        if h in CHILDREN_HOUSES or lh in (2, 5) or "Jupiter" in tenants:
            if h == 5 or lh == 5:
                return (f"<strong>Age {y['age']} ({cal}):</strong> children, creativity, or romance "
                        f"take centre stage — patience with outcomes, not control.")
            return (f"<strong>Age {y['age']} ({cal}):</strong> family and creative fulfilment active — "
                    f"channel energy into one focused project.")
    if domain == "health":
        if h in HEALTH_HOUSES or lh in (6, 8, 12) or _year_tone(r, y) == "caution":
            return (f"<strong>Age {y['age']} ({cal}):</strong> guard sleep, meals, and check-ups — "
                    f"stress shows when routine slips.")
    if domain == "growth":
        if h in GROWTH_HOUSES or lh == 9:
            return (f"<strong>Age {y['age']} ({cal}):</strong> luck, mentors, study, or travel "
                    f"can lift you — say yes to clean growth.")
    if domain == "parents":
        father_h = {4, 8, 9}
        mother_h = {3, 4, 11}
        if h in father_h or lh in father_h:
            return (f"<strong>Age {y['age']} ({cal}):</strong> father, lineage, or elder-male themes "
                    f"strengthen — respect duties, documents, and health of elders.")
        if h in mother_h or lh in mother_h:
            return (f"<strong>Age {y['age']} ({cal}):</strong> mother, nurture, or home-base themes "
                    f"surface — family care and emotional roots need attention.")
    if domain == "siblings":
        if h in (3, 11) or lh in (3, 11):
            return (f"<strong>Age {y['age']} ({cal}):</strong> siblings, cousins, or close peers "
                    f"feature — teamwork, rivalry, or shared projects may peak.")
    return None


def _domain_verdict(r: RTVD, domain: str) -> str:
    cy = r.year(r.age)
    line = _domain_line(r, cy, domain)
    if line and _year_verdict(r, cy) == "good":
        return "good"
    if line and _year_verdict(r, cy) == "hard":
        return "hard"
    if line:
        return "attention"
    future = [r.year(r.age + i) for i in range(1, 5)]
    if any(_domain_line(r, y, domain) and _year_verdict(r, y) == "good" for y in future):
        return "attention"
    return "attention"


def _timing_years(r: RTVD, domain: str, limit: int = 2) -> str:
    wins = []
    for age in range(r.age, r.age + 10):
        y = r.year(age)
        if not _domain_line(r, y, domain):
            continue
        wins.append(f"age {y['age']} ({y['calendar']}–{y['calendar'] + 1})")
        if len(wins) >= limit:
            break
    if not wins:
        return ""
    return f" <strong>Best windows:</strong> {', '.join(wins)}."


def _enriched_years(r: RTVD, age_min: int, age_max: int) -> list[dict]:
    tone_map = {"peak": "good", "positive": "good", "caution": "bad", "mixed": "mixed"}
    out = []
    for age in range(age_min, age_max + 1):
        y = dict(r.year(age))
        y["tone"] = tone_map.get(_year_tone(r, y), "mixed")
        out.append(y)
    return out


def _peak_warn_ages(r: RTVD, years: list[dict]) -> tuple[set[int], set[int]]:
    peak, warn = set(), set()
    for y in years:
        if _year_tone(r, y) == "peak":
            peak.add(y["age"])
        if _year_tone(r, y) == "caution":
            warn.add(y["age"])
    return peak, warn


def _book_domain_lead(r: RTVD, domain: str) -> str:
    hits = topic_window_years(r, _enriched_years(r, r.age, r.age + 15), domain, r.age, r.age + 15)
    pred, fact, _ = topic_prose(r, domain, hits)
    return f"<p class='fact'>{_e(fact)}</p><p class='pred'>{pred}</p>"


def _domain_section(r: RTVD, domain: str, fallback: str) -> str:
    cy = r.year(r.age)
    tag = _verdict_tag(_domain_verdict(r, domain))
    book_lead = _book_domain_lead(r, domain) if domain in (
        "marriage", "career", "children", "wealth", "health", "parents", "siblings"
    ) else ""
    parts = [book_lead, f"<p class='pred'>{tag} {DOMAIN_LEAD[domain]}{_timing_years(r, domain)}</p>"]
    hits = []
    for age in range(max(0, r.age - 1), r.age + 8):
        y = r.year(age)
        line = _domain_line(r, y, domain)
        if line:
            hits.append(f"<p class='pred'>{_verdict_tag(_year_verdict(r, y))} {line}</p>")
    if hits:
        parts.extend(hits[:4])
    else:
        parts.append(f"<p class='pred'>{_verdict_tag('attention')} {fallback}</p>")
    lord = cy["lord"]
    if lord in PLANET_REMEDY:
        parts.append(f"<p class='pred'><strong>Remedy:</strong> {PLANET_REMEDY[lord]}</p>")
    return "".join(parts)


def _snapshot(r: RTVD) -> str:
    cy = r.year(r.age)
    bits = [
        "<strong>Where you are now:</strong> This reading uses <strong>year-by-year house activation</strong> — "
        "each age turns on one life zone from your Ascendant."
    ]
    bits.append(
        f"Age <strong>{r.age}</strong> ({cy['calendar']}–{cy['calendar'] + 1}) activates the "
        f"<strong>{_ord(cy['house'])}</strong> house {_verdict_tag(_year_verdict(r, cy))}: "
        f"{_year_plain(r, cy)}"
    )
    peak = next((r.year(r.age + i) for i in range(1, 5) if _year_tone(r, r.year(r.age + i)) == "peak"), None)
    if peak:
        bits.append(
            f"<strong>Standout year ahead:</strong> age {peak['age']} ({peak['calendar']}–{peak['calendar'] + 1}) — "
            f"{HOUSE_LABEL[peak['house']]}."
        )
    watch = next((r.year(r.age + i) for i in range(1, 5) if _year_tone(r, r.year(r.age + i)) == "caution"), None)
    if watch:
        bits.append(f"<strong>Watch year:</strong> age {watch['age']} — go slow, protect health and agreements.")
    return " ".join(bits)


def _chart_support(r: RTVD) -> str:
    cy = r.year(r.age)
    bits = [
        f"{_verdict_tag(_year_verdict(r, cy))} This year: <strong>{HOUSE_LABEL[cy['house']]}</strong> — "
        f"{_year_plain(r, cy)}"
    ]
    domain_note = {"marriage": "Partnership", "career": "Career", "wealth": "Wealth"}
    for domain, house in (("marriage", 7), ("career", 10), ("wealth", 2)):
        if cy["house"] == house or _domain_line(r, cy, domain):
            bits.append(
                f"{_verdict_tag('good' if _year_verdict(r, cy) == 'good' else 'attention')} "
                f"<strong>{domain_note[domain]}</strong> themes are active this year."
            )
    return " ".join(bits[:3])


def _timeline(r: RTVD, n: int = 5) -> str:
    rows = []
    for age in range(r.age, r.age + 15):
        if len(rows) >= n:
            break
        y = r.year(age)
        label = "Now" if age == r.age else ("Next" if len(rows) == 1 else "Later")
        cls = ' class="cur"' if age == r.age else ""
        rows.append(
            f"<tr{cls}><td><strong>{label}</strong></td>"
            f"<td>{y['calendar']}–{y['calendar'] + 1}</td>"
            f"<td>{_verdict_tag(_year_verdict(r, y))}</td>"
            f"<td><strong>Age {age}</strong> — {HOUSE_LABEL[y['house']]}: {_year_plain(r, y)}</td></tr>"
        )
    if not rows:
        return "<p class='pred'>Year data unavailable.</p>"
    return (
        "<table class='simple'><tr><th>When</th><th>Year</th><th>Verdict</th><th>What it means for you</th></tr>"
        + "".join(rows) + "</table>"
    )


def _slice_block(r: RTVD, ages: list[int], wrap: str) -> str:
    if not ages:
        return ""
    paras = []
    for age in ages:
        y = r.year(age)
        paras.append(
            f"<p class='pred'>{_verdict_tag(_year_verdict(r, y))} <strong>Age {age} "
            f"({y['calendar']}–{y['calendar'] + 1}):</strong> {_year_plain(r, y, rich=True)}</p>"
        )
    return f"<div class='{wrap}'>" + "".join(paras) + "</div>"


def _recent_past(r: RTVD, n: int = 4) -> str:
    ages = list(range(max(0, r.age - n), r.age))
    return _slice_block(r, ages, "callout-past")


def _future_paras(r: RTVD, n: int = 3) -> str:
    ages = list(range(r.age + 1, r.age + 1 + n))
    return _slice_block(r, ages, "callout-future")


def _personality_section(r: RTVD) -> str:
    h1 = r.houses[1]
    lord = h1["lord"]
    lp = r.planets.get(lord, {})
    ben, mal, tenants = _mass_on_sign(r, h1["sign"])
    v = "good" if ben >= mal and lp.get("dignity") in ("exalted", "own_sign", "moolatrikona") else "attention"
    lines = [
        f"<p class='pred'>{_verdict_tag(v)} You present as <strong>{r.lagna}</strong> rising — "
        f"life starts through {_area(1)}; your chart ruler <strong>{lord}</strong> sits in "
        f"{_area(lp.get('house', 1))}.</p>",
    ]
    if tenants:
        lines.append(
            f"<p class='pred'>Planets in your 1st sign (<strong>{', '.join(tenants)}</strong>) colour how others read you.</p>"
        )
    return "".join(lines)


def _growth_section(r: RTVD) -> str:
    parts = [_domain_section(r, "growth", "Growth comes through steady conduct until a stronger fortune-year arrives.")]
    cy = r.year(r.age)
    if cy["house"] in GROWTH_HOUSES:
        parts.append(
            f"<p class='pred'>{_verdict_tag('good')} This year itself activates luck/travel themes — "
            f"say yes to clean growth.</p>"
        )
    return "".join(parts)


def _remedies_section(r: RTVD) -> str:
    seen, items = set(), []
    cy = r.year(r.age)
    for p in (cy["lord"], r.houses[1]["lord"]):
        if p and p in PLANET_REMEDY and p not in seen:
            seen.add(p)
            label = " (year-lord)" if p == cy["lord"] else " (chart ruler)"
            items.append(f"<li><strong>{p}</strong>{label}: {PLANET_REMEDY[p]}</li>")
    for p in cy.get("tenants", []):
        if p in PLANET_REMEDY and p not in seen:
            seen.add(p)
            items.append(f"<li><strong>{p}</strong> (active year-sign): {PLANET_REMEDY[p]}</li>")
    items.append("<li>Keep agreements written — honest dealing protects luck more than rituals alone.</li>")
    items.append("<li>During heavy years, trim one draining habit; finish one old pending task.</li>")
    return "<ul>" + "".join(items[:6]) + "</ul>"


def _appendix_chart(r: RTVD) -> str:
    rows = []
    for h in range(1, 13):
        v = r.houses[h]
        ten = ", ".join(v["tenants"]) or "—"
        rows.append(
            f"<tr><td>{_ord(h)}</td><td>{v['sign']}</td><td>{v['lord']}</td>"
            f"<td>{v['lord_sign']} ({_ord(v['lord_house'])})</td><td>{ten}</td></tr>"
        )
    return (
        "<table class='simple'><tr><th>House</th><th>Sign</th><th>Lord</th><th>Lord placed in</th>"
        "<th>Planets in sign</th></tr>" + "".join(rows) + "</table>"
    )


def _appendix_age(r: RTVD) -> str:
    rows = []
    for age in range(max(0, r.age - 5), r.age + 12):
        y = r.year(age)
        cur = ' class="cur"' if age == r.age else ""
        lp = r.planets[y["lord"]]
        rows.append(
            f"<tr{cur}><td>{age}</td><td>{_ord(y['house'])}</td><td>{y['sign']}</td>"
            f"<td>{y['lord']}</td><td>{lp['sign']} ({_ord(lp['house'])})</td>"
            f"<td>{HOUSE_LABEL[y['house']]}</td></tr>"
        )
    return (
        "<table class='simple'><tr><th>Age</th><th>House</th><th>Sign</th><th>Year-lord</th>"
        "<th>Lord placement</th><th>Theme</th></tr>" + "".join(rows) + "</table>"
    )


def _illustrative_section(r: RTVD) -> str:
    """Book-style rule walks for top certainty windows (technique display, not biography)."""
    years = _enriched_years(r, max(1, r.age - 5), r.age + 12)
    picks: list[tuple[str, dict, str, str]] = []
    for domain, label in (
        ("career", "Career archetype"),
        ("marriage", "Partnership archetype"),
        ("children", "Progeny archetype"),
    ):
        hits = topic_window_years(r, years, domain, r.age, r.age + 12)
        if not hits:
            continue
        y = hits[0]
        fired = f"Rule 9 Level {y['certainty']}: {label.lower()} — house {y['house']} ({y['sign']})"
        walk = (
            f"Year-lord {y['lord']} in house {y['lord_house']}; "
            f"{y['from_moon']} from Moon. Illustrative only — verify against your dated milestones."
        )
        picks.append((f"{label}, age {y['age']} ({y['calendar']})", y, fired, walk))
    if not picks:
        return ""
    cards = "".join(
        illustrative_card_html(r, y, title, fired, walk)
        for title, y, fired, walk in picks[:3]
    )
    return (
        "<h1>Book rule walks (illustrative)</h1>"
        '<div class="past"><strong>Technique display:</strong> Cards below show how Guru Rajesh chains '
        "year-lord, nakshatra, and certainty levels — not verified life facts.</div>"
        + cards
    )


def _appendix(r: RTVD) -> str:
    return f"""<details class='appendix'><summary>RTVD chart facts (technical)</summary>
<h2>Birth chart houses</h2>{_appendix_chart(r)}
<h2>Age → house reference</h2>{_appendix_age(r)}
</details>"""


# ──────────────────────────── render ──────────────────────────────


def _css() -> str:
    tags = (
        ".tag-good{display:inline-block;background:#e8f5e9;color:#2e7d32;font-size:.82rem;"
        "font-weight:600;padding:.15rem .45rem;border-radius:3px;margin-right:.35rem}"
        ".tag-warn{display:inline-block;background:#fff8e1;color:#e65100;font-size:.82rem;"
        "font-weight:600;padding:.15rem .45rem;border-radius:3px;margin-right:.35rem}"
        ".tag-hard{display:inline-block;background:#ffebee;color:#c62828;font-size:.82rem;"
        "font-weight:600;padding:.15rem .45rem;border-radius:3px;margin-right:.35rem}"
    )
    try:
        t = GOLD.read_text(encoding="utf-8")
        i, j = t.find("<style>"), t.find("</style>")
        if i != -1 and j != -1:
            return t[i + 7:j] + tags
    except Exception:
        pass
    return (
        "body{font-family:Georgia,serif;max-width:46rem;margin:auto;padding:1.5rem;line-height:1.55}"
        ".card{background:#fff;border:1px solid #e0e0e0;border-radius:6px;padding:1.25rem 1.75rem}"
        ".callout{background:#e0f7fa;border-left:4px solid #006064;padding:.85rem 1rem;margin:1rem 0}"
        ".callout-future{background:#e8f5e9;border-left:4px solid #2e7d32;padding:.85rem 1rem;margin:1rem 0}"
        ".callout-past{background:#fff8e1;border-left:4px solid #f9a825;padding:.85rem 1rem;margin:1rem 0}"
        ".pred{margin:.65rem 0}table.simple{width:100%;border-collapse:collapse;font-size:.9rem}"
        "table.simple th,table.simple td{border:1px solid #e0e0e0;padding:.45rem}"
        "tr.cur td{background:#e0f7fa}details.appendix{margin-top:1.5rem;font-size:.88rem}"
        "h1{font-size:1.25rem;color:#006064;margin-top:1.5rem}" + tags
    )


def render(r: RTVD, dob_disp: str, tob: str = "", place: str = "") -> str:
    nm = _e(r.name)
    today = datetime.today()
    cy = r.year(r.age)
    ref_years = _enriched_years(r, max(1, r.age - 5), r.age + 24)
    peak_ages, warn_ages = _peak_warn_ages(r, ref_years)
    book_method = methodology_html()
    chart_ess = chart_essentials_html(r)
    age_ref = age_reference_html(r, ref_years, peak_ages, warn_ages)
    vim_x = vimshottari_cross_html(r.pc, ref_years, r.age, r.age + 12)
    illustrative = _illustrative_section(r)

    body = f"""
  <article class="card">
    <h1 style="color:var(--heading);">Your life reading — Rasi Tulya Vatsara Dasa</h1>
    <dl class="meta">
      <dt>Client</dt><dd>{nm}</dd>
      <dt>Born</dt><dd>{_e(dob_disp)}{(' · ' + _e(tob)) if tob else ''}{(' · ' + _e(place)) if place else ''}</dd>
      <dt>Lagna</dt><dd>{r.lagna} · age {r.age}</dd>
      <dt>Report date</dt><dd>{today.strftime('%d %B %Y').lstrip('0')}</dd>
    </dl>
    <p class="lead">This reading tracks <strong>which life year you are in</strong> — each age activates one house from your Ascendant.
    Each year has a plain verdict: <span class="tag-good">Good phase</span>,
    <span class="tag-warn">Needs attention</span>, or <span class="tag-hard">Challenging</span>.
    Dates come from your birth chart; remedies are simple weekly habits, not fear-based rituals.</p>

    <div class="callout">{_snapshot(r)}</div>

    {book_method}
    {chart_ess}
    {age_ref}
    {vim_x}
    {illustrative}

    <h1>The chapter you are in (big picture)</h1>
    <p class="pred">Age <strong>{r.age}</strong> ({cy['calendar']}–{cy['calendar'] + 1}) activates the <strong>{_ord(cy['house'])}</strong> house
    — <strong>{HOUSE_LABEL[cy['house']]}</strong>. The 12-year cycle repeats; you last hit this theme at age {r.age - 12 if r.age > 12 else '—'}.</p>
    <p class="pred">{_chart_support(r)}</p>

    <h1>Your timeline — what is coming</h1>
    <p class="pred">Each row is one year of life — when the active house matches money, love, or career zones, that theme gets louder.</p>
    {_timeline(r)}

    <h1>Recent past</h1>
    {_recent_past(r) or '<p class="pred">No recent years in window.</p>'}

    <h1>Right now ({today.strftime('%d %B %Y').lstrip('0')})</h1>
    <p class="pred">{_verdict_tag(_year_verdict(r, cy))} You are in <strong>age {r.age}</strong> ({cy['calendar']}–{cy['calendar'] + 1}). {_year_plain(r, cy, rich=True)}</p>

    <h1>Near future</h1>
    {_future_paras(r) or '<p class="pred">No future years parsed.</p>'}

    <h1>Who you are underneath</h1>
    {_personality_section(r)}

    <h1>Job &amp; career</h1>
    {_domain_section(r, 'career', 'Build skill steadily — the next strong career window may be a few years out.')}

    <h1>Marriage &amp; partnership</h1>
    {_domain_section(r, 'marriage', 'No dominant partnership year in the next few years — relationships still grow through daily honesty.')}

    <h1>Children &amp; creativity</h1>
    {_domain_section(r, 'children', 'Creative fulfilment grows through patience — no urgent child-year signal in the near window.')}

    <h1>Wealth &amp; joint resources</h1>
    {_domain_section(r, 'wealth', 'No standout wealth year in the immediate window — steady habits matter more than timing.')}

    <h1>Health &amp; energy</h1>
    {_domain_section(r, 'health', 'No acute health-flag year immediately ahead — keep prevention habits anyway.')}
    <p class="note">Educational only — see a doctor for symptoms.</p>

    <h1>Parents &amp; elders</h1>
    {_domain_section(r, 'parents', 'Parent themes surface on 4th/8th/9th (father) and 3rd/11th (mother) house years.')}

    <h1>Siblings &amp; peers</h1>
    {_domain_section(r, 'siblings', 'Sibling themes favour 3rd and 11th-house activations in the 12-year cycle.')}

    <h1>Growth, mentors &amp; support</h1>
    {_growth_section(r)}

    <h1>Remedies — simple weekly habits</h1>
    {_remedies_section(r)}

    <p class="note">Your Jaimini or KP report may name different timings — that is normal.
    Use this report for <strong>year-by-year life themes</strong>; use planet daśā for month-level precision.</p>

    {_appendix(r)}

    <p class="note">Educational astrology only. Verify important years in your software. This report does not diagnose illness or predict death.</p>
  </article>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>RTVD reading — {nm}</title>
<style>{_css()}</style></head><body>{body}</body></html>"""


def generate_rtvd_html(
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
    r = RTVD(pc)
    d = datetime.strptime(dob, "%Y-%m-%d").date()
    doc = render(r, d.strftime("%d %B %Y").lstrip('0'), tob, place)
    cy = r.year(r.age)
    summary = {
        "lagna": r.lagna, "age": r.age, "current_house": cy["house"],
        "current_sign": cy["sign"], "year_lord": cy["lord"],
    }
    return doc, summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Deterministic RTVD report (no LLM)")
    ap.add_argument("name")
    ap.add_argument("dob")
    ap.add_argument("extracted", nargs="?", default=None, help="Optional legacy AstroSage extract")
    add_chart_source_args(ap)
    ap.add_argument("--tob", default="")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    kw = chart_kwargs_from_args(args)
    doc, summary = generate_rtvd_html(
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
    out = Path(args.out) if args.out else BASE_DIR / "reports" / f"Vedic_RTVD_{args.name}_preview.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(f"age={summary['age']} current_house={summary['current_house']} "
          f"sign={summary['current_sign']} lord={summary['year_lord']}")
    print(f"written → {out}")


if __name__ == "__main__":
    main()
