#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mehta rules4 rule engine - all calculations in background, affirmative prose out."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from mehta_book_data import lookup_mehta_lord, pick_mehta_clause
from mehta_book_data import SIGNS
from mehta_chart import BENEFICS, KENDRA, MALEFICS, STRONG, TRIKONA, UPACHAYA, WEAK

if TYPE_CHECKING:
    from mehta_chart import MehtaChart

KARAKAS: dict[int, list[str]] = {
    1: [],
    2: ["Jupiter"],
    3: ["Mars"],
    4: ["Moon", "Mars", "Venus"],
    5: ["Jupiter"],
    6: [],
    7: ["Venus"],
    8: [],
    9: ["Sun", "Jupiter"],
    10: ["Sun", "Mercury", "Jupiter", "Saturn"],
    11: ["Jupiter"],
    12: ["Saturn"],
}

HOUSE_TOPICS: dict[int, str] = {
    1: "body, vitality, and outer personality",
    2: "wealth, speech, and family resources",
    3: "courage, skills, and siblings",
    4: "home, mother, and property",
    5: "children, creativity, and intellect",
    6: "health, service, rivals, and daily work",
    7: "marriage, partnership, and public dealings",
    8: "longevity, inheritance, and hidden change",
    9: "father, dharma, luck, and long travel",
    10: "career, status, and public reputation",
    11: "income, gains, and fulfilment of wishes",
    12: "expenses, foreign lands, and spiritual release",
}

CHAPTER_TITLES = [
    ("intro", "Introduction - how your chart is judged"),
    ("ch01", "Chapter I - First house"),
    ("ch02", "Chapter II - Second house (wealth)"),
    ("ch03", "Chapter III - Third house"),
    ("ch04", "Chapter IV - Fourth house"),
    ("ch05", "Chapter V - Fifth house"),
    ("ch06", "Chapter VI - Sixth house"),
    ("ch07", "Chapter VII - Seventh house (marriage)"),
    ("ch08", "Chapter VIII - Eighth house"),
    ("ch09", "Chapter IX - Ninth house"),
    ("ch10", "Chapter X - Tenth house (profession)"),
    ("ch11", "Chapter XI - Eleventh house (gains)"),
    ("ch12", "Chapter XII - Twelfth house"),
    ("ch13", "Chapter XIII - Rahu and Ketu"),
    ("ch14", "Chapter XIV - Transits and Sade Sati"),
    ("ch15", "Chapter XV - Vimshottari dasha"),
    ("ch17", "Chapter XVII - Birth nakshatra"),
    ("ch18", "Chapter XVIII - Navamsha and vargas"),
    ("ch19", "Chapter XIX - Yogas"),
]


@dataclass
class MehtaSection:
    id: str
    title: str
    prediction: str
    facts: str
    tone: str = "neutral"
    rules: list[str] = field(default_factory=list)


def _ord(n: int) -> str:
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n if n < 20 else n % 10, 'th')}"


def _humanize(line: str) -> str:
    if not line:
        return ""
    line = re.sub(r"^\d+\.\s*", "", line.strip())
    for a, b in (
        (r"\bOne is\b", "You are"),
        (r"\bHe is\b", "You are"),
        (r"\bHe also\b", "You also"),
        (r"\bNative will\b", "You will"),
        (r"\bNative is\b", "You are"),
        (r"\bthe native\b", "you"),
        (r"\bperson will\b", "you will"),
    ):
        line = re.sub(a, b, line, flags=re.I)
    if line and line[0].islower():
        line = line[0].upper() + line[1:]
    return line


JUNK_CLAUSE = re.compile(
    r"Moksha|Bhadra Yoga|fine instruments|Yoga, combination|With you are not|"
    r"8[\"']?\s*lord deteriorates|electronics\s*-|prosperity,\s*This Yoga|Languages,",
    re.I,
)


def _clause_ok(text: str) -> bool:
    if not text or len(text) < 40:
        return False
    if JUNK_CLAUSE.search(text):
        return False
    if text.count(",") > 5:
        return False
    if not re.search(r"\b(is|are|will|gives|brings|makes|earns|supports|builds|lifts|defines)\b", text, re.I):
        return False
    return True


def _affirm(text: str, *, afflicted: bool = False) -> str:
    """Strip conditional OCR hedging; keep one definitive sentence."""
    if not text:
        return ""
    text = _humanize(text)
    text = re.sub(r"\bUnless afflicted[^.]*\.\s*", "", text, flags=re.I)
    text = re.sub(r"\bIf afflicted[^.]*\.\s*", "", text, flags=re.I)
    text = re.sub(r"\bif not afflicted[^,.;]*[,;]?\s*", "", text, flags=re.I)
    text = re.sub(r"\bWith benefic[^.]*\.\s*", "", text, flags=re.I)
    text = re.sub(r"\bThese are general rules[^.]*\.\s*", "", text, flags=re.I)
    text = re.sub(r"\bshould be used with caution[^.]*\.\s*", "", text, flags=re.I)
    text = re.sub(r"\bmay\b", "will", text, flags=re.I)
    text = re.sub(r"\bmight\b", "will", text, flags=re.I)
    text = re.sub(r"\bcan be\b", "is", text, flags=re.I)
    text = re.sub(r"\bcould mean\b", "means", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    if afflicted and re.search(r"\b(good|wealth|happy|famous|rich|lucky)\b", text, re.I):
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text)
    for p in parts:
        p = p.strip()
        if len(p) >= 40 and not re.match(r"^(According to|If the|When the|With 4 and)", p, re.I):
            out = p.rstrip(".") + "."
            if _clause_ok(out):
                return out
    candidate = text[:280].rsplit(".", 1)[0] + "." if "." in text[:280] else text
    return candidate if _clause_ok(candidate) else ""


def _planet_direction(chart: "MehtaChart", planet: str, house: int) -> str:
    dig = chart.planets[planet]["dignity"]
    if dig in STRONG:
        return "positive"
    if dig in WEAK or house in (6, 8, 12):
        return "caution"
    return "neutral"


def _house_score(chart: "MehtaChart", h: int) -> tuple[float, list[str]]:
    rules: list[str] = []
    score = 0.0
    lord = chart.houses[h]["lord"]
    lord_info = chart.planets[lord]
    lord_h = lord_info["house"]
    lord_dig = lord_info["dignity"]

    if lord_h in KENDRA | TRIKONA:
        score += 2
        rules.append(f"{lord} ({_ord(h)} lord) sits in kendra/trikona ({_ord(lord_h)})")
    elif lord_h in UPACHAYA:
        score += 1
        rules.append(f"{_ord(h)} lord in upachaya {_ord(lord_h)}")
    elif lord_h in (6, 8, 12):
        score -= 2
        rules.append(f"{_ord(h)} lord in dusthana {_ord(lord_h)}")

    if lord_dig in STRONG:
        score += 2
        rules.append(f"{lord} strong by dignity ({lord_dig})")
    elif lord_dig in WEAK:
        score -= 2
        rules.append(f"{lord} weak by dignity ({lord_dig})")

    for t in chart.houses[h]["tenants"]:
        dig = chart.planets[t]["dignity"]
        if t in BENEFICS and dig in STRONG:
            score += 1
            rules.append(f"Benefic {t} occupies {_ord(h)} strongly")
        elif t in MALEFICS and dig not in STRONG:
            score -= 0.5
            rules.append(f"Malefic {t} in {_ord(h)} without full strength")

    if h in (6, 8, 12):
        score -= 0.5

    return score, rules


def _tone_from_score(score: float) -> str:
    if score >= 2.5:
        return "good"
    if score <= -1.5:
        return "amber"
    return "neutral"


def _dig_phrase(d: str) -> str:
    return {
        "exalted": "exalted",
        "debilitated": "debilitated",
        "moolatrikona": "in moolatrikona",
        "own_sign": "in own sign",
        "great_friend_sign": "well placed",
    }.get(d, "moderately placed")


def _computed_house_verdict(chart: "MehtaChart", h: int, score: float) -> str:
    """Definitive Mehta Step-12 verdict from chart math (chart-generic)."""
    lord = chart.houses[h]["lord"]
    li = chart.planets[lord]
    lord_h = li["house"]
    tenants = chart.houses[h]["tenants"]
    topic = HOUSE_TOPICS[h].split(",")[0]
    parts: list[str] = []

    if lord_h == h:
        parts.append(
            f"{lord} as {_ord(h)} lord sits in its own house  -  {topic} is a direct, self-reinforcing theme in this chart."
        )
    elif lord_h in KENDRA | TRIKONA:
        parts.append(
            f"{lord} as {_ord(h)} lord in kendra/trikona {_ord(lord_h)} links {topic} to central life pillars."
        )
    elif lord_h in UPACHAYA:
        parts.append(
            f"{lord} as {_ord(h)} lord in upachaya {_ord(lord_h)} grows {topic} through effort and repetition."
        )
    elif lord_h in (6, 8, 12):
        parts.append(
            f"{lord} as {_ord(h)} lord in dusthana {_ord(lord_h)} tests {topic}  -  dasha timing and remedies matter."
        )

    if tenants:
        strong_t = [t for t in tenants if chart.planets[t]["dignity"] in STRONG]
        if strong_t:
            parts.append(
                f"{' and '.join(strong_t)} in the {_ord(h)} strengthens this house in supportive periods."
            )
        elif any(t in MALEFICS for t in tenants):
            parts.append(
                f"Malefic presence in the {_ord(h)} adds pressure  -  channel it through discipline, not impulse."
            )

    karakas = [k for k in KARAKAS.get(h, []) if k in chart.planets]
    if karakas:
        k = karakas[0]
        parts.append(
            f"Karaka {k} in the {_ord(chart.planets[k]['house'])} colours {topic} alongside the house lord."
        )

    if h == 2:
        wfm = chart.wealth_from_moon()
        parts.append(
            f"2nd from Moon falls in the {_ord(wfm)}  -  emotional security and family rhythm influence how wealth accumulates."
        )

    if score >= 2.5:
        parts.append(
            f"Mehta Step 12 marks {topic} as fruit-bearing when {lord}'s dasha runs."
        )
    elif score <= -1.5:
        parts.append(
            f"{topic} needs patience; {lord} in {_ord(lord_h)} ({_dig_phrase(li['dignity'])}) rewards steady conduct over shortcuts."
        )
    else:
        parts.append(
            f"{lord} in {_ord(lord_h)} ({_dig_phrase(li['dignity'])}) gives workable {topic} results when dasha and karaka align."
        )

    return " ".join(parts)


def _analyze_house(chart: "MehtaChart", h: int, chapter_id: str, title: str) -> MehtaSection:
    score, rules = _house_score(chart, h)
    tone = _tone_from_score(score)
    lord = chart.houses[h]["lord"]
    lord_h = chart.planets[lord]["house"]
    afflicted = score <= -1.5 or chart.planets[lord]["dignity"] in WEAK

    parts = [_computed_house_verdict(chart, h, score)]

    lord_dir = "caution" if lord_h in (6, 8, 12) or afflicted else "positive"
    lord_txt = _affirm(lookup_mehta_lord(chart.book, h, lord_h, lord_dir), afflicted=afflicted)
    if lord_txt and _clause_ok(lord_txt):
        parts.append(lord_txt)

    for t in chart.houses[h]["tenants"]:
        direction = _planet_direction(chart, t, h)
        raw = chart.book.get("planet_in_house", {}).get(str(h), {}).get(t, "")
        if h == 1 and not raw:
            raw = chart.book.get("planet_in_first_house", {}).get(t, "")
        pl_txt = _affirm(
            pick_mehta_clause(raw, chart.planets[t]["dignity"], direction),
            afflicted=direction == "caution",
        )
        if pl_txt and _clause_ok(pl_txt):
            parts.append(pl_txt)
            break

    tenants = ", ".join(chart.houses[h]["tenants"]) or "empty"
    facts = f"{_ord(h)} sign {chart.houses[h]['sign']}; lord {lord} in {_ord(lord_h)}; occupants: {tenants}."
    return MehtaSection(chapter_id, title, " ".join(parts), facts, tone, rules)


def _analyze_intro(chart: "MehtaChart") -> MehtaSection:
    rules: list[str] = []
    yogas = chart.detect_mehta_yogas()
    ll = chart.houses[1]["lord"]
    ll_h = chart.planets[ll]["house"]
    ll_topic = HOUSE_TOPICS[ll_h].split(",")[0]

    parts = [
        f"You were born with {chart.lagna} rising, Moon in {chart.moon_sign}, Sun in {chart.sun_sign}.",
        f"Lagna lord {ll} sits in the {_ord(ll_h)}  -  {ll_topic} is the spine of how Mehta reads your chart.",
    ]
    if ll_h == 10:
        parts.append("Lagna lord in the 10th ties identity and career into one thread.")
        rules.append("Lagna lord in 10th")
    if yogas:
        parts.append(
            f"Structural yogas flagged: {', '.join(y['name'] for y in yogas[:3])}."
        )
        rules.extend(y["name"] for y in yogas[:3])

    ad = next((a for a in chart.antars if a.get("status") == "current"), None)
    if ad:
        ad_h = chart.planets[ad["ad_lord"]]["house"]
        parts.append(
            f"Active period: {chart.cur_md['md_lord']} mahadasha, {ad['ad_lord']} antardasha "
            f"(the {_ord(ad_h)} house themes are loudest now)."
        )

    facts = f"Lagna {chart.lagna}; Moon {chart.moon_sign}; Sun {chart.sun_sign}; lagna lord {ll} in {_ord(ll_h)}."
    return MehtaSection("intro", "Your Mehta snapshot", " ".join(parts), facts, "good" if yogas else "neutral", rules)


def _analyze_rahu_ketu(chart: "MehtaChart") -> MehtaSection:
    rahu_h = chart.planets["Rahu"]["house"]
    ketu_h = chart.planets["Ketu"]["house"]
    parts = [
        f"Rahu in the {_ord(rahu_h)} amplifies hunger for gains, foreign links, and unconventional income.",
        f"Ketu in the {_ord(ketu_h)} pulls toward detachment, research, and spiritualised intelligence.",
        f"Together they axis the {_ord(rahu_h)} and {_ord(ketu_h)} houses - balance material push (Rahu) with inner refinement (Ketu).",
    ]
    rules = [f"Rahu {_ord(rahu_h)}", f"Ketu {_ord(ketu_h)}"]
    return MehtaSection(
        "ch13", CHAPTER_TITLES[13][1], " ".join(parts),
        f"Rahu {_ord(rahu_h)}; Ketu {_ord(ketu_h)}.",
        "neutral", rules,
    )


def _analyze_dasha(chart: "MehtaChart") -> MehtaSection:
    md = chart.cur_md["md_lord"]
    ad = next((a for a in chart.antars if a.get("status") == "current"), None)
    ad_lord = ad["ad_lord"] if ad else md
    md_info = chart.planets[md]
    ad_info = chart.planets[ad_lord]
    timing = ""
    if ad:
        try:
            s = datetime.strptime(ad["start"][:10], "%Y-%m-%d").strftime("%b %Y")
            e = datetime.strptime(ad["end"][:10], "%Y-%m-%d").strftime("%b %Y")
            timing = f" ({s} - {e})"
        except ValueError:
            pass

    md_theme = HOUSE_TOPICS[md_info["house"]].split(",")[0]
    ad_theme = HOUSE_TOPICS[ad_info["house"]].split(",")[0]
    parts = [
        f"You are in {md} mahadasha with {ad_lord} antardasha active now{timing}.",
        f"{md} in the {_ord(md_info['house'])} colours the long chapter around {md_theme}.",
        f"{ad_lord} in the {_ord(ad_info['house'])} steers the current slice toward {ad_theme}.",
    ]
    fut = [a for a in chart.antars if a.get("status") == "future"][:2]
    for fa in fut:
        fl = fa["ad_lord"]
        fh = chart.planets[fl]["house"]
        try:
            fs = datetime.strptime(fa["start"][:10], "%Y-%m-%d").strftime("%b %Y")
            fe = datetime.strptime(fa["end"][:10], "%Y-%m-%d").strftime("%b %Y")
            parts.append(
                f"Next: {fl} antardasha ({fs}  -  {fe}) activates {_ord(fh)}-house themes."
            )
        except ValueError:
            pass

    rules = [f"MD {md} in {_ord(md_info['house'])}", f"AD {ad_lord} in {_ord(ad_info['house'])}"]
    facts = f"{md} mahadasha; {ad_lord} antardasha{timing}."
    return MehtaSection("ch15", CHAPTER_TITLES[15][1], " ".join(parts), facts, "neutral", rules)


def _analyze_nakshatra(chart: "MehtaChart") -> MehtaSection:
    nk = chart.moon_nak or "unknown"
    parts = [
        f"Your birth star is {nk} on the Moon.",
        "Moon nakshatra sets the emotional tone behind every dasha  -  inner rhythm often differs from the lagna mask.",
        f"With {chart.lagna} rising and Moon in {chart.moon_sign}, blend nakshatra instinct with house-lord timing for major decisions.",
    ]
    rules = [f"Moon nakshatra: {nk}"]
    return MehtaSection("ch17", CHAPTER_TITLES[16][1], " ".join(parts), f"Moon in {nk}.", "neutral", rules)


def _analyze_navamsha(chart: "MehtaChart") -> MehtaSection:
    flags = chart.navamsha_dilution_flags()
    weak_d1 = [p for p, i in chart.planets.items() if i["dignity"] in WEAK and p in ("Mercury", "Jupiter")]
    parts: list[str] = []
    if flags:
        parts.append("Navamsha cross-check shows mixed delivery on key planets:")
        for f in flags[:3]:
            parts.append(f.replace("Mehta:", "").strip())
    else:
        parts.append(
            "Navamsha and birth chart read as aligned on the grahas checked - predictions above stand on both rashi and D9 without a major cancellation flag."
        )
    if weak_d1:
        parts.append(
            f"Debilitated {' and '.join(weak_d1)} in rashi still deliver when dasha and dispositor support align - watch their sub-periods for the real-world test."
        )
    rules = flags or ["Navamsha aligned"]
    return MehtaSection("ch18", CHAPTER_TITLES[17][1], " ".join(parts), "D9 cross-check.", "neutral", rules)


YOGA_HUMAN: dict[str, str] = {
    "Kendra-Trikona link (Mercury-Venus)": (
        "Mercury and Venus link kendra and trikona through your career zone - learning, status, and creative income rise together in strong periods."
    ),
    "Group I + Group II lord mix (Mercury-Venus)": (
        "Wealth and comfort are real, but good-house lords mixing with trika stress means money can leak through expenses or wrong alliances - keep clear boundaries."
    ),
    "Benefics in kendras + malefics in upachaya": (
        "Benefics hold the centre of the chart while malefics in 3/6/11 give fight and appetite - classic Mehta rise after struggle, not easy lottery luck."
    ),
}


def _analyze_yogas(chart: "MehtaChart") -> MehtaSection:
    yogas = chart.detect_mehta_yogas()
    if not yogas:
        return MehtaSection(
            "ch19", CHAPTER_TITLES[18][1],
            "No major structural yoga is flagged - steady merit, dasha timing, and house-lord strength carry the chart.",
            "Yoga scan.", "neutral", [],
        )
    parts: list[str] = []
    for y in yogas:
        human = YOGA_HUMAN.get(y["name"])
        if human:
            parts.append(human)
        else:
            result = re.sub(r"\bd\?ridra\b", "daridra", y["result"], flags=re.I)
            parts.append(f"{y['name']}: {result}")
    return MehtaSection(
        "ch19", CHAPTER_TITLES[18][1], " ".join(parts),
        f"{len(yogas)} yoga(s).", "good", [y["name"] for y in yogas],
    )


def _analyze_transits(chart: "MehtaChart") -> MehtaSection:
    moon = chart.moon_sign
    moon_idx = SIGNS.index(moon) if moon in SIGNS else 0
    before = SIGNS[(moon_idx - 1) % 12]
    after = SIGNS[(moon_idx + 1) % 12]
    sat_h = chart.planets["Saturn"]["house"]
    parts = [
        f"With Moon in {moon}, Sade Sati runs when Saturn transits {before}, {moon}, and {after}  -  use those years for discipline, not panic.",
        f"Natal Saturn in the {_ord(sat_h)} ties transit Saturn to {HOUSE_TOPICS[sat_h].split(',')[0]} when Saturn crosses related signs.",
    ]
    rules = [f"Moon {moon}", f"Saturn natal {_ord(sat_h)}"]
    return MehtaSection("ch14", CHAPTER_TITLES[14][1], " ".join(parts), f"Moon {moon}; Saturn {_ord(sat_h)}.", "neutral", rules)


def analyze_all_sections(chart: "MehtaChart") -> list[MehtaSection]:
    """Every Part-A Mehta chapter - rules computed first, affirmative text second."""
    sections: list[MehtaSection] = [_analyze_intro(chart)]
    house_map = [
        ("ch01", 1), ("ch02", 2), ("ch03", 3), ("ch04", 4), ("ch05", 5), ("ch06", 6),
        ("ch07", 7), ("ch08", 8), ("ch09", 9), ("ch10", 10), ("ch11", 11), ("ch12", 12),
    ]
    for cid, h in house_map:
        title = next(t for i, t in CHAPTER_TITLES if i == cid)
        sections.append(_analyze_house(chart, h, cid, title))
    sections.append(_analyze_rahu_ketu(chart))
    sections.append(_analyze_transits(chart))
    sections.append(_analyze_dasha(chart))
    sections.append(_analyze_nakshatra(chart))
    sections.append(_analyze_navamsha(chart))
    sections.append(_analyze_yogas(chart))
    return sections
