#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blind chart prediction-first narratives (Guru Rajesh / rules17).

Prediction body first; one brief chart fact in parentheses - not planet dumps.
"""
from __future__ import annotations

from typing import Any

from vedic_blindchart_report import (
    Blind,
    _chain_phrase,
    _prog_states,
    from_x,
    house_of,
)

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


def _ord(n: int) -> str:
    n = int(n)
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _zone_sign(b: Blind, base: str, offset: int) -> tuple[str, list[str]]:
    bi = SIGNS.index(base)
    sign = SIGNS[(bi + offset) % 12]
    occ = [p for p in b.by_sign.get(sign, []) if p in b.planets]
    return sign, occ


def _prog_event(b: Blind, age: int) -> dict[str, Any]:
    j, s = b.jup_prog(age), b.sat_prog(age)
    j_occ = [p for p in b.by_sign.get(j, []) if p in b.planets]
    s_occ = [p for p in b.by_sign.get(s, []) if p in b.planets]
    return {
        "age": age,
        "year": b.dob.year + age,
        "jup": j,
        "sat": s,
        "jup_occ": j_occ,
        "sat_occ": s_occ,
        "jup_h": house_of(j, b.lagna),
        "sat_h": house_of(s, b.lagna),
    }


def _house_theme(b: Blind, sign: str) -> str:
    h = house_of(sign, b.lagna)
    themes = {
        1: "identity and how the world sees you",
        2: "money, family speech, and stored resources",
        3: "courage, skill, siblings, and short journeys",
        4: "home, mother, and inner peace",
        5: "children, creativity, and romance",
        6: "work pressure, health routines, and competition",
        7: "marriage, partnership, and public face",
        8: "transformation, shared money, and hidden matters",
        9: "father, faith, travel, and higher purpose",
        10: "career, reputation, and authority",
        11: "gains, networks, and fulfilled ambitions",
        12: "expenses, foreign threads, and spiritual retreat",
    }
    return themes.get(h, "life direction")


def _jup_human(b: Blind, sign: str, tense: str = "present") -> str:
    occ = [p for p in b.by_sign.get(sign, []) if p in b.planets]
    ven = b.planets["Venus"]["sign"]
    theme = _house_theme(b, sign)
    past = tense == "past"

    if sign == b.lagna:
        return (
            "you were recasting who you are and how you carry yourself in the world"
            if past else
            "you are recasting who you are and how you carry yourself in the world"
        )
    if sign == ven or "Venus" in occ:
        return (
            "marriage, comfort, and material quality moved to the front of the line"
            if past else
            "marriage, comfort, and material quality move to the front of the line"
        )
    if sign == b.planets["Moon"]["sign"] or "Moon" in occ:
        return (
            "home rhythm, mother themes, and emotional grounding dominated the chapter"
            if past else
            "home rhythm, mother themes, and emotional grounding take centre stage"
        )
    if sign == b.planets["Sun"]["sign"] or "Sun" in occ:
        return (
            "father, authority, and institution-facing duty shaped the year"
            if past else
            "father, authority, and institution-facing duty come forward"
        )
    if sign == b.planets["Saturn"]["sign"] or "Saturn" in occ:
        return (
            "career karma and professional restructuring were unavoidable"
            if past else
            "career karma and professional restructuring lie ahead"
        )
    if sign == b.pressure_sign() or ("Mars" in occ and "Rahu" in occ):
        return (
            "competition sharpened, tempers ran hot, and physical risks cost more than usual"
            if past else
            "competition will sharpen; tempers and physical risks need conscious management"
        )
    if sign == b.planets["Ketu"]["sign"] or "Ketu" in occ:
        return (
            "something had to be released - an unconventional turn or quiet detachment from an old path"
            if past else
            "something must be released - an unconventional turn or detachment from an old path"
        )
    if sign == b.planets["Jupiter"]["sign"]:
        return (
            "life asked for maturity and consolidation after long effort"
            if past else
            "life asks for maturity and consolidation after long effort"
        )
    if sign == SIGNS[(SIGNS.index(b.lagna) + 1) % 12]:
        return (
            "family money, property talk, and what you keep in the bank became the story"
            if past else
            "family money, property talk, and what you keep in the bank become the story"
        )
    if sign == SIGNS[(SIGNS.index(b.lagna) + 2) % 12]:
        return (
            "courage, visibility, and being seen for what you can do mattered most"
            if past else
            "courage, visibility, and being seen for what you can do matter most"
        )
    if sign == SIGNS[(SIGNS.index(b.lagna) + 6) % 12]:
        return (
            "partnership and your visible public role defined the period"
            if past else
            "partnership and your visible public role define the period"
        )
    if occ:
        joined = " and ".join(occ)
        return (
            f"the {joined} chapter of your chart became loud and personal"
            if past else
            f"the {joined} chapter of your chart becomes loud and personal"
        )
    return (
        f"the life area of {theme} moved to the foreground"
        if past else
        f"the life area of {theme} moves to the foreground"
    )


def _sat_human(b: Blind, sign: str, tense: str = "present") -> str:
    occ = [p for p in b.by_sign.get(sign, []) if p in b.planets]
    ven = b.planets["Venus"]["sign"]
    past = tense == "past"

    if sign == ven or "Venus" in occ or "Mercury" in occ:
        return (
            "Saturn rewarded structure over luck - savings, clean deals, and disciplined spending actually worked"
            if past else
            "Saturn is paying you for structure, not luck - this is the band to save, invest, and close sound financial decisions"
        )
    if sign == b.pressure_sign() or ("Mars" in occ and "Rahu" in occ):
        return (
            "Saturn tested the Mars+Rahu fire - arguments over money, hostile competition, or a physical scare taught hard lessons"
            if past else
            "Saturn enters the Mars+Rahu fire - a demanding band where paperwork, boundaries, and fitness matter as much as ambition"
        )
    if sign == b.planets["Moon"]["sign"] or "Moon" in occ:
        return (
            "Saturn pressed on emotional stability - duty at home or health routines could not be postponed"
            if past else
            "Saturn presses emotional stability - home duty and health routines cannot be postponed"
        )
    if sign == b.planets["Jupiter"]["sign"] or "Jupiter" in occ:
        return (
            "Saturn returned to your natal Jupiter - consolidation, weight, and responsibility after years of building"
            if past else
            "Saturn returns to your natal Jupiter - consolidation and heavier responsibility after years of building"
        )
    if sign == b.planets["Saturn"]["sign"]:
        return (
            "Saturn doubled down on career karma - no shortcuts, only depth and endurance"
            if past else
            "Saturn doubles down on career karma - depth and endurance, not shortcuts"
        )
    if occ:
        return (
            f"Saturn weighed on {', '.join(occ)} - slow results, but real ones if you stayed patient"
            if past else
            f"Saturn weighs on {', '.join(occ)} - slow results, but real ones if you stay patient"
        )
    return (
        "Saturn kept the pace sober and the results delayed but durable"
        if past else
        "Saturn keeps the pace sober - results arrive slowly but durably"
    )


def _sat_clause(s_part: str) -> str:
    if not s_part:
        return s_part
    if s_part.startswith("Saturn"):
        return s_part
    return s_part[0].lower() + s_part[1:]


def _merge_prog_sentence(b: Blind, ev: dict[str, Any], tense: str, lead: str) -> str:
    j_part = _jup_human(b, ev["jup"], tense)
    s_part = _sat_human(b, ev["sat"], tense)
    return f"{lead}, {j_part}, while {_sat_clause(s_part)}."


def _past_decade_read(b: Blind, lo: int, hi: int) -> str:
    mid = (lo + min(hi, b.age)) // 2
    if mid > b.age:
        return ""
    ev = _prog_event(b, mid)
    yr = ev["year"]
    hooks = {
        (0, 10): "Home and identity were shaped early - you learned responsibility before ease.",
        (10, 20): "These years were restless and competitive; proving yourself mattered more than comfort.",
        (20, 30): "Independence, authority, and emotional maturity were earned here, not handed to you.",
        (30, 40): "Partnership, public standing, and long-term consolidation locked into place in this decade.",
    }
    label = {0: "childhood", 10: "teens", 20: "twenties", 30: "thirties"}[lo]
    hook = hooks[(lo, hi)]
    core = _merge_prog_sentence(b, ev, "past", f"In your {label} (around {yr}, age {mid})")
    return f"{core} {hook}"


def _sat_pressure_entry_age(b: Blind, from_age: int) -> int | None:
    ps = b.pressure_sign()
    for a in range(from_age, from_age + 15):
        if b.sat_prog(a) == ps:
            return a
    return None


def _now_and_future_narrative(b: Blind) -> dict[str, Any]:
    age = b.age
    cur = _prog_event(b, age)
    ven = b.planets["Venus"]["sign"]
    on_wealth = cur["sat"] == ven or "Venus" in cur["sat_occ"]
    cancer_h = SIGNS[(SIGNS.index(b.lagna) + 1) % 12]
    leo_h = SIGNS[(SIGNS.index(b.lagna) + 2) % 12]

    leo_age = next((a for a in range(age, age + 8) if b.jup_prog(a) == leo_h), None)
    aries_age = _sat_pressure_entry_age(b, age)
    moon_age = next(
        (a for a in range(age + 3, age + 10) if b.jup_prog(a) == b.planets["Moon"]["sign"]),
        None,
    )

    paras: list[str] = []

    if on_wealth:
        paras.append(
            f"You are in one of the stronger financial passages of this decade. "
            f"Saturn is moving through the Venus-Mercury combination in your chart, which converts grace into tangible assets "
            f"when you act with discipline - not speculation, not impulse, but clean property, savings, and long-term security. "
            f"At the same time Jupiter sits on your rising sign: an inner reset is underway. "
            f"You are not merely earning more; you are deciding what kind of person the next chapter requires you to become. "
            f"(Age {age}, ~{cur['year']}; Saturn through {cur['sat']}, Jupiter through {cur['jup']}.)"
        )
    else:
        paras.append(
            _merge_prog_sentence(b, cur, "present", f"Right now, at age {age} (~{cur['year']}),")
        )

    if b.jup_prog(age + 1) == cancer_h or b.jup_prog(age + 2) == cancer_h:
        paras.append(
            f"Through {cur['year'] + 1} and into {b.dob.year + age + 2}, the wealth window stays open while Jupiter shifts into your "
            f"second-house band - family money, property talk, and formal decisions about what you keep. "
            f"If a home purchase, investment, or shared-resource agreement is already on the table, this is the period to execute it, "
            f"not to defer out of caution. The chart favours building now, not waiting for a perfect mood. "
            f"(Jupiter entering {cancer_h}; Saturn still through {cur['sat']}.)"
        )
    elif on_wealth:
        paras.append(
            "The next twelve months continue the same financial emphasis - stay structured, document deals, "
            "and treat every major outlay as a twenty-year decision rather than a short thrill."
        )

    if leo_age and leo_age <= age + 5:
        paras.append(
            f"Around age {leo_age} (~{b.dob.year + leo_age}), Jupiter opens a visibility band - "
            f"recognition for work already done, a teaching or leadership role, or simply being seen for competence you have quietly built. "
            f"This is not overnight fame; it is the chart saying your name travels farther than before. "
            f"Prepare the portfolio, the qualification, or the public face now so that when the window opens you are ready to step into it."
        )

    if aries_age and aries_age <= age + 8:
        end_age = aries_age + 2
        paras.append(
            f"From about age {aries_age} (~{b.dob.year + aries_age}) through {b.dob.year + end_age}, Saturn walks into "
            f"{b.pressure_sign()} where Mars and Rahu already sit - the chart's pressure point. "
            f"Expect sharper competition, hotter arguments over money or property, and a physical environment that punishes carelessness. "
            f"This is survivable and even strengthening if you meet it with paperwork, boundaries, and steady fitness - "
            f"not reactive pride. Finalise shared investments before this band; avoid hostile partnerships during it; "
            f"and do not take avoidable physical risks when your attention is divided. "
            f"Those who discipline the fire here emerge stronger by the time Saturn clears this terrain."
        )

    if moon_age:
        paras.append(
            f"After the Aries test eases, age {moon_age} (~{b.dob.year + moon_age}) brings Jupiter to your Moon - "
            f"emotional grounding, domestic stability, and practical accumulation replace the friction years. "
            f"By then the hardest passage of the late forties is behind you; the rhythm becomes spacious again."
        )

    return {"title": "Right now and near future", "paragraphs": paras, "tone": "green"}


def _past_life_narrative(b: Blind) -> dict[str, Any]:
    bands = [(0, 10), (10, 20), (20, 30), (30, 40)]
    paras: list[str] = []
    for lo, hi in bands:
        if lo >= b.age:
            continue
        text = _past_decade_read(b, lo, hi)
        if text:
            paras.append(text)

    if not paras:
        paras.append(
            "Your dated milestones will sharpen this reconstruction; the planetary chain above still holds for character and domain reads."
        )
    return {"title": "Your life so far", "paragraphs": paras, "tone": "neutral"}


def _personality_narrative(b: Blind) -> dict[str, Any]:
    jup = b.planets["Jupiter"]
    chain = b.chain_ahead("Jupiter", 4)
    chain_txt = _chain_phrase(b, chain)
    pressure = b.pressure_sign()
    paras: list[str] = []

    if jup["dignity"] == "debilitated":
        paras.append(
            "You are built for gains through discipline, pressure, and persistence rather than quick luck. "
            "Life rewards you when you stay structured under stress and refuse shortcuts - "
            "the debilitation is not weakness, it is a chart that matures late and then holds what it earns."
            f" (Jupiter - you - in debilitated {jup['sign']}, {_ord(jup['house'])} house.)"
        )
    else:
        paras.append(
            f"Your life spine is Jupiter in {jup['sign']}: organic confidence and expansion when dignity is respected."
            f" (Jupiter in {_ord(jup['house'])} house.)"
        )

    ven = b.planets["Venus"]
    if ven["dignity"] == "exalted":
        paras.append(
            f"What you walk into next in the zodiac chain is {chain_txt}. "
            "The Venus-Mercury chapter is where grace, refined skill, and earning power show most clearly - "
            "this is not a chart that stays poor if conduct stays clean."
            " (Exalted Venus joins debilitated Mercury in Pisces ahead of Jupiter.)"
        )
    else:
        paras.append(
            f"The sequential story ahead of you reads: {chain_txt}. "
            "Each cluster is an elder influence, a skill chapter, or a life test you meet in order."
        )

    paras.append(
        f"Mars and Rahu together in {pressure} keep returning as your pressure trigger - "
        "when progressions or transits re-touch that sign, competition sharpens, arguments cost more, "
        "and physical risks need conscious avoidance. Channel the fire into clean ambition, not reactive fights."
        f" (Mars+Rahu cluster in {pressure}.)"
    )
    return {"title": "You - core nature and life design", "paragraphs": paras, "tone": "neutral"}


def _parents_narrative(b: Blind) -> dict[str, Any]:
    sun = b.planets["Sun"]
    moon = b.planets["Moon"]
    s10_sign, s10_occ = _zone_sign(b, sun["sign"], 9)
    s2_sign, s2_occ = _zone_sign(b, sun["sign"], 1)
    s12_sign, s12_occ = _zone_sign(b, sun["sign"], 11)
    m2_sign, m2_occ = _zone_sign(b, moon["sign"], 1)

    father = (
        "Your father reads as principled, institution-facing, and duty-heavy - "
        "someone who respected rules, reform, or public responsibility more than glamour."
    )
    if "Saturn" in s10_occ:
        father += " Saturn on the career angle from Sun often marks law, policy, administration, or work beneath official structure."
    if "Jupiter" in s12_occ:
        father += " Jupiter in the twelfth from Sun adds sacrifice, foreign posting, or behind-the-scenes duty in the father story."
    if s2_occ:
        father += (
            f" Income and family speech around him were coloured by {', '.join(s2_occ)} in {s2_sign} - "
            "grace and intelligence in the household economy, not crude trade alone."
        )
    father += f" (Sun in {sun['sign']}; 10th-from-Sun {s10_sign}; 12th-from-Sun {s12_sign}; 2nd-from-Sun {s2_sign}.)"

    mother = (
        "Your mother is practical, detail-conscious, and emotionally grounding - "
        "care shown through service, order, and quiet competence rather than dramatic display."
    )
    if len(b.by_sign.get(moon["sign"], [])) <= 1:
        mother += " Moon stands relatively alone: home-centred, methodical nurturing is the dominant tone."
    if "Ketu" in m2_occ:
        mother += " Ketu in the second from Moon marks a reordering or separation theme in her story - distance, change, or a non-linear family chapter."
    mother += f" (Moon in {moon['sign']}; 2nd-from-Moon {m2_sign}.)"

    return {"title": "Parents", "paragraphs": [father, mother], "tone": "neutral"}


def _siblings_narrative(b: Blind) -> dict[str, Any]:
    chain = b.chain_ahead("Jupiter", 4)
    n_clusters = len(chain)
    text = (
        f"Ahead of Jupiter the book counts {n_clusters} occupied clusters ({_chain_phrase(b, chain)}). "
        "That pattern usually means you are the youngest or among the last-born - "
        "several elder presences (siblings or cousin-equivalents) shaped the home before your turn. "
        "Mars+Rahu in the chain adds a bold, non-conformist, high-drive sibling or elder male influence."
        " (Planets ahead of natal Jupiter in zodiac order.)"
    )
    return {"title": "Siblings and birth order", "paragraphs": [text], "tone": "neutral"}


def _education_narrative(b: Blind) -> dict[str, Any]:
    merc = b.planets["Mercury"]
    ven = b.planets["Venus"]
    same = merc["sign"] == ven["sign"]
    mars2_sign, mars2_occ = _zone_sign(b, merc["sign"], 1)
    paras: list[str] = []

    if merc["dignity"] == "debilitated" and same and ven["dignity"] == "exalted":
        paras.append(
            "You did not fit the textbook mould, but you are genuinely intelligent - intuitive, creative, "
            "and able to connect ideas others miss. Debilitated Mercury joined by exalted Venus is classic "
            "cancellation: the weakness of the learner is outweighed by grace and aesthetic intelligence."
            " (Mercury+Venus in Pisces.)"
        )
    else:
        paras.append(
            f"Education follows Mercury in {merc['sign']} - communicative, analytical, or commercial leaning."
        )

    if mars2_sign == b.pressure_sign() or "Mars" in mars2_occ:
        paras.append(
            "School or college carried friction - competitive peers, authority clashes, or a noisy environment - "
            "yet the Venus companion still delivered usable degrees and street-smart intelligence."
            f" (Mars+Rahu in {_ord(from_x(b.pressure_sign(), merc['sign']))} from Mercury.)"
        )

    paras.append(
        "Fields that fit: finance, management, communication, arts, counselling, or any work where "
        "intelligence meets people-skills - not heavy mechanical engineering unless life later forced it."
    )
    return {"title": "Education", "paragraphs": paras, "tone": "green"}


def _career_narrative(b: Blind) -> dict[str, Any]:
    sat = b.planets["Saturn"]
    _, s11_occ = _zone_sign(b, sat["sign"], 10)
    retro_note = ""
    if sat["retro"]:
        retro_note = (
            " Saturn retrograde adds a Libra undertone - contracts, fairness, and deal-making layered "
            "over Scorpio depth."
        )
    p1 = (
        "Your professional identity is depth work: investigation, research, finance, audit, insurance, "
        "confidential systems, or anything requiring you to see what others avoid. "
        "Scorpio is not a glamour sign - it is trust, secrecy, and transformation."
        f" (Saturn in {sat['sign']}{', retrograde' if sat['retro'] else ''}.){retro_note}"
    )
    p2 = (
        "Income follows care and quality: when you invest emotionally in the outcome for others, money tracks; "
        "when you work mechanically, even good periods feel dry."
    )
    if "Moon" in s11_occ:
        p2 += " Moon in Virgo as 11th-from-Saturn confirms service-minded, detail-perfect earning."
    return {"title": "Career and profession", "paragraphs": [p1, p2], "tone": "green"}


def _marriage_narrative(b: Blind, female: bool) -> dict[str, Any]:
    if female:
        return {
            "title": "Marriage and partner",
            "paragraphs": [
                "Mars defines the spouse in this method for your chart; read Mars sign and zones for partner character and timing."
            ],
            "tone": "neutral",
        }
    ven = b.planets["Venus"]
    moon_from = from_x(b.planets["Moon"]["sign"], ven["sign"])
    mars_from = from_x(b.pressure_sign(), ven["sign"])
    paras = [
        (
            "Your spouse is a person of genuine quality - educated, emotionally capable, and a net positive force. "
            "Exalted Venus is not hedged: the chart promises a partner who elevates the home, not one who drains it."
            " (Venus exalted in Pisces.)"
        ),
        (
            "They are practical and service-minded - manage detail, notice what others miss, show love by doing. "
            "A Virgo-Moon partner type: reliable, analytical, quietly demanding of the same standard they hold themselves to."
            f" (Moon in {_ord(moon_from)} from Venus.)"
        ),
        (
            "Early union years carried heat - arguments, passion, or financial friction before settling - "
            "not because the marriage is weak, but because Mars+Rahu in the wealth-speech zone from Venus tests patience first."
            f" (Mars+Rahu in {_ord(mars_from)} from Venus.)"
        ),
    ]
    return {"title": "Marriage and partner", "paragraphs": paras, "tone": "green"}


def _children_narrative(b: Blind) -> dict[str, Any]:
    ketu = b.planets["Ketu"]
    h5 = ketu["house"]
    hits = []
    h5_sign = SIGNS[(SIGNS.index(b.lagna) + 4) % 12]
    for st in _prog_states(b, 18, 45):
        if st["jup"] == h5_sign or st["jup"] == ketu["sign"]:
            hits.append(st["age"])
        if len(hits) >= 2:
            break
    text = (
        "Children arrive on an unconventional clock - surprise timing, detachment themes, or a path that "
        "does not match the textbook age band. Ketu on the progeny angle rarely denies entirely; "
        "it asks for patience and sometimes a non-standard sequence."
    )
    if hits:
        text += f" Jupiter progression highlights progeny around ages {hits[0]} and {hits[-1]} (+/- 1 year)."
    text += f" (Ketu in {ketu['sign']}, {_ord(h5)} house.)"
    return {"title": "Children", "paragraphs": [text], "tone": "neutral"}


def _wealth_narrative(b: Blind) -> dict[str, Any]:
    ven = b.planets["Venus"]
    age = b.age
    cur_sat = b.sat_prog(age)
    on_ven = cur_sat == ven["sign"] or "Venus" in b.by_sign.get(cur_sat, [])
    paras = [
        (
            "Long-term financial struggle is not the base promise - exalted Venus guarantees that material life "
            "can have quality and grace when conduct stays clean."
            " (Venus exalted in Pisces.)"
        ),
        (
            "The twenties and early thirties saw volatility: money that arrived also left quickly, "
            "risky bets, or competitive drains - Mars+Rahu in the second from Venus is the classic pattern."
        ),
    ]
    if on_ven:
        paras.append(
            f"Right now (age {age}) Saturn progression sits on Venus+Mercury - among the stronger wealth windows "
            "of this decade. Build savings and execute sound property or investment decisions before this band closes; "
            "discipline converts Venus grace into durable assets."
            f" (Saturn progressing through {cur_sat}.)"
        )
    return {"title": "Wealth", "paragraphs": paras, "tone": "green"}


def _health_narrative(b: Blind) -> dict[str, Any]:
    from vedic_blindchart_report import SIGN_BODY
    jup, sat = b.planets["Jupiter"], b.planets["Saturn"]
    paras = [
        (
            "Knees, joints, and bone maintenance matter from your forties onward - not illness, but susceptibility "
            "that responds well to weight-bearing exercise and consistent care."
            f" (Jupiter in {jup['sign']} - {SIGN_BODY[jup['sign']]}.)"
        ),
        (
            "Head and inflammatory sensitivity spike when Mars+Rahu is activated - avoid unnecessary physical risks "
            f"in those years. ({SIGN_BODY[b.pressure_sign()]}.)"
        ),
        (
            "Lower-abdominal and excretory themes need preventive check-ups; slow-building issues respond to routine, not crisis care."
            f" (Saturn in {sat['sign']} - {SIGN_BODY[sat['sign']]}.)"
        ),
        (
            "Stress lands as overthinking and sleep disruption - creative output (writing, music, movement) "
            "is the most effective outlet for your constitution."
            " (Debilitated Mercury.)"
        ),
    ]
    return {"title": "Health - prevention, not diagnosis", "paragraphs": paras, "tone": "amber"}


def build_blind_narratives(b: Blind, female: bool = False) -> list[dict[str, Any]]:
    sections = [
        _personality_narrative(b),
        _parents_narrative(b),
        _siblings_narrative(b),
        _education_narrative(b),
        _career_narrative(b),
        _marriage_narrative(b, female),
        _children_narrative(b),
        _wealth_narrative(b),
        _health_narrative(b),
        _past_life_narrative(b),
        _now_and_future_narrative(b),
    ]
    return sections
