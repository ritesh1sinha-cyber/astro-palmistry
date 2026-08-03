#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Human prediction-first prose for Jaimini books lane (Goel + Gems + Jewels)."""
from __future__ import annotations

from dataclasses import dataclass

from jaimini_books_chart import (
    NAT_BENEFIC,
    ROLE_SHORT,
    JaiminiBooksChart,
    _ord,
    house_of,
    sign_at,
)

KARAKA_LIFE = {
    "Atmakarak": {
        "Sun": "You define yourself through visibility, integrity, and being taken seriously.",
        "Moon": "Your inner core is emotional, nurturing, and changeable - home and mood steer big decisions.",
        "Mars": "You lead with courage, competition, and direct action - idle periods feel wrong.",
        "Mercury": "You are wired to think, speak, trade, and connect - boredom is your real enemy.",
        "Jupiter": "You grow through teaching, faith, and fair judgment - meaning matters as much as money.",
        "Venus": "You lead with charm, artistry, and relationship intelligence - beauty and fairness are non-negotiable.",
        "Saturn": "You are built for endurance, duty, and slow mastery - shortcuts rarely satisfy you.",
    },
    "Amatyakarak": {
        "Sun": "Career runs through authority, government, medicine, or any role where you are visibly in charge.",
        "Moon": "Work favours public care, food, hospitality, HR, or mood-led people businesses.",
        "Mars": "Profession suits engineering, sport, surgery, defence, or competitive fields.",
        "Mercury": "Best roles use writing, IT, analytics, teaching, or sharp communication.",
        "Jupiter": "Advisory, law, finance, counselling, or education fit your public karma.",
        "Venus": "Design, arts, diplomacy, luxury trades, or people-facing grace roles suit you.",
        "Saturn": "Institutional roles, research, compliance, or the long professional climb are your lane.",
    },
    "Darakaraka": {
        1: "Partner type: independent, self-directed, strong-willed.",
        7: "Partner type: partnership-focused, fair-minded, relationship-oriented.",
        11: "Partner type: socially active, goal-driven, needs freedom within the couple.",
        5: "Partner type: romantic, playful, creative.",
        9: "Partner type: philosophical, worldly, freedom-loving.",
    },
}

KL_HOUSE_HUMAN = {
    4: {
        "empty": "Home life is not the loudest theme from your inner chart - you may invest more in career or travel before settling roots.",
        "Moon": "Home and mother themes are central - emotional security and a comfortable base drive major life choices.",
        "Venus": "You are built for a beautiful, comfortable home - property and aesthetics matter deeply.",
        "Jupiter": "A spacious, dignified home or family property is strongly indicated.",
        "Saturn": "Home comes through patience - you may delay buying or carry family duty heavily.",
        "Sun": "Home life links to status - you want a base that reflects who you have become.",
        "default": "Your inner chart colours home and property through {pls} - expect life decisions to loop back to where you live.",
    },
    5: {
        "empty": "Children and creative projects are not the primary headline from your inner chart, though they can still flourish in good periods.",
        "Moon": "Strong writer, teacher, or creative intelligence - ideas and children both need nurturing visibility.",
        "Jupiter": "Knowledge, students, and creative legacy are blessed - teaching or authorship suits you.",
        "Mercury": "Quick mind, sharp student, or multi-project creative - you juggle intellectual babies easily.",
        "default": "Creativity and progeny run through {pls} - what you nurture wants to be seen.",
    },
    9: {
        "empty": "Dharma and guru themes are quiet from the inner chart - you may find philosophy later in life.",
        "Jupiter": "Truth, teachers, and long journeys are strongly favoured - mentors change your trajectory.",
        "Saturn": "Duty and discipline shape your belief system - you respect tradition and hard-earned wisdom.",
        "Sun": "Father, government, or visible authority figures act as teachers in your story.",
        "default": "Your moral compass is shaped by {pls} in the wisdom house - travel and study alter your path.",
    },
    10: {
        "empty": "Career promise from the inner chart is carried more by your soul and work planets in the birth map than by a packed 10th-from-KL - still, public life can rise in strong periods.",
        "Mercury": "Professional life peaks through communication, commerce, or technical mastery - you can become very accomplished in your field.",
        "Sun": "Public authority, government links, or visible leadership are strongly indicated.",
        "Saturn": "Career success is slow, solid, and enduring - reputation outlasts quick wins.",
        "Jupiter": "Status rises through advisors, judges, or dignified roles - people trust your judgment.",
        "default": "Career visibility runs through {pls} - your name and your inner promise align when these periods run.",
    },
    12: {
        "empty": "Spiritual retreat is optional in your script - worldly life can stay primary without conflict.",
        "Ketu": "A genuine pull toward meditation, renunciation, or inner liberation - not just weekend spirituality.",
        "Jupiter": "Devotion, charity, and guru-bhakti soften the ego - foreign or ashram threads are possible.",
        "Sun": "Ego learns to surrender through solitude, father-guru figures, or foreign spiritual study.",
        "Venus": "Beauty in devotion - art, music, or loving service become spiritual paths.",
        "default": "The 12th-from-inner-chart activates through {pls} - retreat, foreign lands, or charity reshape you.",
    },
}

OCCUPATION_HUMAN = {
    "Sun": "government, leadership, or advisory authority",
    "Moon": "care, hospitality, or public-facing nurture trades",
    "Mars": "technical, fire/metal, sport, or competitive fields",
    "Mercury": "commerce, writing, law, IT, or craftsmanship",
    "Jupiter": "teaching, counsel, finance, or spiritual guidance",
    "Venus": "arts, diplomacy, luxury, or relationship-based work",
    "Saturn": "institutional work or the family trade pursued with discipline",
    "Rahu": "technology, machinery, unconventional or foreign-linked careers",
    "Ketu": "specialist, research, or unusual niche trades",
}


@dataclass
class LifeSection:
    title: str
    prediction: str
    fact: str
    tone: str = "neutral"
    domain: str = ""


def _fact(*parts: str) -> str:
    return " ".join(p for p in parts if p)


def build_life_sections(chart: JaiminiBooksChart) -> list[LifeSection]:
    sections: list[LifeSection] = []
    ak = chart.role("Atmakarak")
    amk = chart.role("Amatyakarak")
    dk = chart.role("Darakaraka")
    pk = chart.role("Putrakaraka")
    mk = chart.role("Matrukaraka")
    gk = chart.role("Gnatikaraka")
    akp = ak.get("planet", "")
    kl = chart.karakamsa or "?"
    pairs = chart.raja_yoga_pairs()
    ag_lagna = chart.argala_on(chart.lagna)
    ag_kl = chart.argala_on(chart.karakamsa) if chart.karakamsa else {"open": [], "blocked": [], "open_houses": []}

    # Hero / snapshot
    yoga_note = (
        f"You carry {len(pairs)} strong status combinations - recognition and rise are part of the script, "
        "though not always on the easy path."
        if pairs else "Status combinations are moderate - steady effort matters more than one lucky yoga."
    )
    struggle = ""
    if amk.get("sign") and ak.get("sign"):
        rel = house_of(amk["sign"], ak["sign"])
        if rel in (6, 8, 12):
            struggle = " Career and soul purpose connect, but success often arrives after delay, rivalry, or a proving period."
    akp = ak.get("planet", "")
    inner_line = KARAKA_LIFE["Atmakarak"].get(akp, "Your soul planet colours every major chapter.")
    sections.append(LifeSection(
        "Your Jaimini snapshot",
        f"You rise with {chart.lagna} on the outside and {kl} in Karakamsha - an {akp}-soul chart. "
        f"{inner_line}{struggle} {yoga_note}",
        _fact(f"AK {akp}, KL {kl}, lagna {chart.lagna}."),
        "good" if pairs else "neutral",
        "snapshot",
    ))

    # Inner self - karakas + KL
    inner = KARAKA_LIFE["Atmakarak"].get(akp, "Your soul planet colours every major chapter.")
    amk_line = KARAKA_LIFE["Amatyakarak"].get(amk.get("planet", ""), "")
    pkp = pk.get("planet", "")
    pk_same = pk.get("sign") == ak.get("sign")
    inner_body = (
        f"{inner} With Karakamsha in {kl}, your private truth is softer and more imaginative than your "
        f"{chart.lagna} rising may show - you need work and love that feel meaningful, not merely successful."
    )
    if pk_same:
        inner_body += (
            f" Children, students, or creative projects ({pkp}) share the same inner zone as your soul - "
            "what you nurture and who you are become hard to separate."
        )
    sections.append(LifeSection(
        "Who you are underneath",
        inner_body,
        _fact(f"AK {akp} in {ak.get('sign')}; AmK {amk.get('planet')} in {amk.get('sign')}."),
        "good",
        "personality",
    ))

    # Public image vs private
    if chart.arudha_lagna != kl:
        image = (
            f"Public image ({chart.arudha_lagna}) and inner Karakamsha ({kl}) differ - "
            "what people see and what you feel inside may not match; protect private recharge time."
        )
    else:
        image = "What people see and what you feel inside line up - less performance anxiety, more authentic presence."
    sections.append(LifeSection(
        "How others see you",
        image,
        _fact(f"Arudha {chart.arudha_lagna}, KL {kl}."),
        "neutral",
        "personality",
    ))

    # Career & status
    raja_txt = ""
    if pairs:
        raja_txt = (
            " Status links your soul planet to creativity and partnership - "
            "promotion and public name open when those life themes peak together."
        )
    occ_bits = []
    for pl, info in chart.pc["planets"].items():
        kh = chart.kl_house(info["sign"])
        if kh in (1, 2) and pl in OCCUPATION_HUMAN:
            occ_bits.append(OCCUPATION_HUMAN[pl])
    occ_txt = (
        " Inner-chart vocation threads include " + ", ".join(dict.fromkeys(occ_bits[:3])) + "."
        if occ_bits else ""
    )
    tenth = chart.planets_in_kl_house(10)
    tenth_txt = KL_HOUSE_HUMAN[10].get(tenth[0], KL_HOUSE_HUMAN[10]["default"].format(pls=", ".join(tenth))) if tenth else KL_HOUSE_HUMAN[10]["empty"]
    sections.append(LifeSection(
        "Career & public name",
        f"{amk_line}{raja_txt}{occ_txt} {tenth_txt}",
        _fact(f"AmK {amk.get('planet')} in {_ord(amk.get('house', 0))} house; 10th-from-KL: {', '.join(tenth) or 'empty'}."),
        "good" if pairs or amk.get("house") in (9, 10) else "neutral",
        "career",
    ))

    # Love & marriage
    dk_h = dk.get("house", 0)
    dk_style = KARAKA_LIFE["Darakaraka"].get(dk_h, KARAKA_LIFE["Darakaraka"].get(7, "Partner is warm and expressive."))
    up_pl = chart.planets_in(chart.upapada)
    up_note = (
        f" Marriage scripts run serious and structured ({chart.upapada} Upapada)"
        + (f" with {', '.join(up_pl)} colouring commitment - loyalty and long-term building matter."
           if up_pl else " - you take vows and reputation in love seriously.")
    )
    sections.append(LifeSection(
        "Love & marriage",
        f"{dk_style} Your love planet {dk.get('planet')} sits in the {_ord(dk_h)} life area - "
        f"partnership and friendship networks overlap.{up_note}",
        _fact(f"DK {dk.get('planet')}, UP {chart.upapada}."),
        "good" if up_pl and any(p in NAT_BENEFIC for p in up_pl) else "neutral",
        "marriage",
    ))

    # Home & family
    mkp = mk.get("planet", "")
    fourth = chart.planets_in_kl_house(4)
    fourth_txt = (
        KL_HOUSE_HUMAN[4].get(fourth[0], KL_HOUSE_HUMAN[4]["default"].format(pls=", ".join(fourth)))
        if fourth else KL_HOUSE_HUMAN[4]["empty"]
    )
    sections.append(LifeSection(
        "Home, mother & emotional roots",
        f"Mother and home planet {mkp} in {mk.get('sign')} anchors family feeling in the {_ord(mk.get('house', 0))} sector. "
        f"{fourth_txt}",
        _fact(f"MK {mkp}; 4th-from-KL {', '.join(fourth) or 'empty'}."),
        "good" if mk.get("house") in (4, 5) else "neutral",
        "property",
    ))

    # Wisdom & travel
    ninth = chart.planets_in_kl_house(9)
    ninth_txt = (
        KL_HOUSE_HUMAN[9].get(ninth[0], KL_HOUSE_HUMAN[9]["default"].format(pls=", ".join(ninth)))
        if ninth else KL_HOUSE_HUMAN[9]["empty"]
    )
    sections.append(LifeSection(
        "Teachers, travel & belief",
        ninth_txt + f" Your sibling-father-guru planet {chart.role('Bhratrukaraka').get('planet')} "
        f"in {chart.role('Bhratrukaraka').get('sign')} adds courage and mentor themes abroad or in study.",
        _fact(f"9th-from-KL: {', '.join(ninth) or 'empty'}."),
        "good" if ninth and ninth[0] in NAT_BENEFIC else "neutral",
        "travel",
    ))

    # Children & creativity
    fifth = chart.planets_in_kl_house(5)
    fifth_txt = (
        KL_HOUSE_HUMAN[5].get(fifth[0], KL_HOUSE_HUMAN[5]["default"].format(pls=", ".join(fifth)))
        if fifth else KL_HOUSE_HUMAN[5]["empty"]
    )
    sections.append(LifeSection(
        "Children & creative life",
        f"{fifth_txt} Putra karaka {pkp} in {pk.get('sign')} ties children, students, or creative projects to "
        f"your {_ord(pk.get('house', 0))}-house life themes.",
        _fact(f"PK {pkp}; 5th-from-KL {', '.join(fifth) or 'empty'}."),
        "good" if pk.get("house") in (5, 10) else "neutral",
        "children",
    ))

    # Wealth & gains - argala 11th
    if ag_lagna["open"]:
        backers = "; ".join(ag_lagna["open"][:2])
        wealth = (
            f"Gains and income get a push from open argala on your lagna"
            + (f": {backers}." if backers else ".")
            + " Read contracts carefully when malefics back the argala."
        )
        tone = "good"
    else:
        wealth = "Wealth builds more through steady karaka strength than through one lucky argala burst - diversify skills, not gossip."
        tone = "neutral"
    sections.append(LifeSection(
        "Money & fulfilled goals",
        wealth,
        _fact(f"Argala on lagna: {len(ag_lagna['open'])} open, {len(ag_lagna['blocked'])} blocked."),
        tone,
        "finance",
    ))

    # Health & friction
    gkp = gk.get("planet", "")
    sections.append(LifeSection(
        "Health & daily friction",
        f"Friction planet {gkp} in the {_ord(gk.get('house', 0))} house shows stress through rivals, workload, or "
        "immune dips before the body breaks down. Prevention beats crisis - sleep, meals, and boundaries at work matter.",
        _fact(f"GK {gkp} in {_ord(gk.get('house', 0))}."),
        "attention" if gk.get("house") in (6, 8, 12) else "neutral",
        "health",
    ))

    # Spiritual
    twelfth = chart.planets_in_kl_house(12)
    twelfth_txt = (
        KL_HOUSE_HUMAN[12].get(twelfth[0], KL_HOUSE_HUMAN[12]["default"].format(pls=", ".join(twelfth)))
        if twelfth else KL_HOUSE_HUMAN[12]["empty"]
    )
    sections.append(LifeSection(
        "Spiritual life & retreat",
        f"{twelfth_txt} This is not a mandatory monk chart - but foreign travel, charity, or quiet practice "
        "can reset you when worldly noise gets loud.",
        _fact(f"12th-from-KL: {', '.join(twelfth) or 'empty'}."),
        "good" if twelfth and twelfth[0] in ("Ketu", "Jupiter", "Venus") else "neutral",
        "spiritual",
    ))

    # Support pattern - argala summary
    support_parts = []
    if ag_lagna["open"]:
        support_parts.append("Your confidence gets tailwind from planets backing the lagna directly.")
    if ag_lagna["blocked"]:
        support_parts.append("Some support patterns compete with blockers - results arrive, but with delay or rivalry.")
    if ag_kl.get("open"):
        support_parts.append("Inner-chart argala favours holding gains once they arrive.")
    if not support_parts:
        support_parts.append("Life outcomes depend more on which karaka periods run than on one fixed support lock.")
    sections.append(LifeSection(
        "What backs you vs what blocks you",
        " ".join(support_parts),
        _fact(
            f"Lagna argala: {'open' if ag_lagna['open'] else 'quiet'}; "
            f"KL argala: {'open' if ag_kl.get('open') else 'quiet'}."
        ),
        "good" if ag_lagna["open"] and not ag_lagna["blocked"] else "attention" if ag_lagna["blocked"] else "neutral",
        "support",
    ))

    return sections
