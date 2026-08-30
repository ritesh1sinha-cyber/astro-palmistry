#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
transit_planet_book_data.py — Complete Planetary Transit Matrix Data Reference

Contains all fundamental transit rules, 9x9 transit-over-natal matrices, combustion rules,
Nakshatra triad principles, and remedial protocols.
"""
from __future__ import annotations

# ══════════════════════════════════════════════════════════════════
#  1. FOUNDATIONAL TRANSIT PRINCIPLES (Chapter 1 & 2)
# ══════════════════════════════════════════════════════════════════

FOUNDATIONAL_PRINCIPLES = [
    {
        "rule_id": "TP_FUND_01",
        "title": "Transit Sign as Temporary Lagna",
        "description": "The sign currently occupied by a transiting planet acts as a temporary Lagna for that planet's significations, altering how the native's external environment responds."
    },
    {
        "rule_id": "TP_FUND_02",
        "title": "Transit Over Friendly Natal Planet",
        "description": "When a transiting planet enters a sign occupied by a natural or temporary friend, its fruits amplify smoothly and bring assistance, joy, and constructive partnerships."
    },
    {
        "rule_id": "TP_FUND_03",
        "title": "Transit Over Inimical Natal Planet",
        "description": "When a transiting planet enters a sign occupied by an inimical planet, friction, delays, and sharp tests occur like two rivals meeting at the same event."
    },
    {
        "rule_id": "TP_FUND_04",
        "title": "Degree-Wise Chronological Unfolding",
        "description": "When multiple planets occupy a natal sign, the transiting planet delivers the results of each natal planet in the exact chronological order of their degree placements."
    },
    {
        "rule_id": "TP_FUND_05",
        "title": "Nakshatra Triad Warning & Manifestation (Janma, Anujanma, Trijanma)",
        "description": "Every natal planet sits in a star triad (1st, 10th, 19th nakshatras). When a transiting planet travels across the earlier two stars in the triad, it signals premonitory events before fully manifesting when it contacts the exact natal star."
    },
    {
        "rule_id": "TP_FUND_06",
        "title": "Transit Planet in Own Nakshatra",
        "description": "A transiting planet entering its own ruled star in any zodiac sign gains sudden heightened strength (e.g. Venus in Leo gains peak strength in Purva Phalguni)."
    },
    {
        "rule_id": "TP_FUND_07",
        "title": "Dasha-Bhukti Convergence Principle",
        "description": "Transit effects are temporary and awaken desires/opportunities, but permanent real-world manifestation requires the sanction of the running Dasha and Bhukti lords."
    },
    {
        "rule_id": "TP_FUND_08",
        "title": "Planetary Combustion in Transit",
        "description": "When any planet transits within close degrees of the transit Sun, its external manifestation is temporarily eclipsed and internal contemplation is required."
    }
]

# ══════════════════════════════════════════════════════════════════
#  2. TRANSIT OF SUN OVER NATAL PLANETS (Chapter 3)
# ══════════════════════════════════════════════════════════════════

TRANSIT_SUN_OVER_NATAL = {
    "Sun": {
        "title": "Transit Sun Contacting Natal Sun (Solar Return Month)",
        "prediction": "Recharges vitality, increases desire for administrative leadership, brings interactions with government authorities or senior executives, and activates paternal matters.",
        "severity": "positive"
    },
    "Moon": {
        "title": "Transit Sun Contacting Natal Moon",
        "prediction": "Triggers short travels, heightened public visibility, changes in daily routine, emotional shifts, and active focus on mother's welfare or domestic properties.",
        "severity": "info"
    },
    "Mars": {
        "title": "Transit Sun Contacting Natal Mars",
        "prediction": "High physical stamina and dynamic drive. Acquaintances with high-level officials who help formulate new earning strategies. Elders visit the native; watch sharp speech.",
        "severity": "positive"
    },
    "Mercury": {
        "title": "Transit Sun Contacting Natal Mercury",
        "prediction": "Sharp intellectual clarity, signing important official documents, commercial agreements, audit clearances, and recognition in academic or communication domains.",
        "severity": "positive"
    },
    "Jupiter": {
        "title": "Transit Sun Contacting Natal Jupiter",
        "prediction": "Royal dignity, spiritual blessings, financial counseling opportunities, elevation in social prestige, and auspicious recognition from preceptors or institutions.",
        "severity": "positive"
    },
    "Venus": {
        "title": "Transit Sun Contacting Natal Venus",
        "prediction": "Prosperity through luxury, vehicle acquisitions, support from women in executive roles, affection for daughters, and artistic appreciation.",
        "severity": "positive"
    },
    "Saturn": {
        "title": "Transit Sun Contacting Natal Saturn",
        "prediction": "Temporary friction with superiors or father, heavy work responsibilities, scrutiny of pending tasks, and delays requiring disciplined perseverance.",
        "severity": "caution"
    },
    "Rahu": {
        "title": "Transit Sun Contacting Natal Rahu",
        "prediction": "Sudden intense ambition for public recognition, paternal health vigilance, eye/heart sensitivity, and need to avoid deceptive shortcuts.",
        "severity": "warning"
    },
    "Ketu": {
        "title": "Transit Sun Contacting Natal Ketu",
        "prediction": "Spiritual introspection, philosophical clarity, settling government tax/documentation matters, and detachment from superficial praise.",
        "severity": "info"
    }
}

# ══════════════════════════════════════════════════════════════════
#  3. TRANSIT OF MOON OVER NATAL PLANETS
# ══════════════════════════════════════════════════════════════════

TRANSIT_MOON_OVER_NATAL = {
    "Sun": "Illuminates personal status, father's matters, administrative tasks, and executive clarity.",
    "Moon": "Monthly emotional reset, focus on domestic comfort, personal wellbeing, and financial liquidity.",
    "Mars": "Spur-of-the-moment courage, swift decisions regarding land/tools, athletic drive, and spicy culinary cravings.",
    "Mercury": "Vivid imagination, commercial negotiations, friendly discussions, writing, and accounting tasks.",
    "Jupiter": "Generous mood, spiritual contentment, auspicious domestic discussions, and hospitality.",
    "Venus": "Refined aesthetic pleasure, romantic harmony, shopping for luxuries, and social elegance.",
    "Saturn": "Serious mood, introspective work, managing pending duties, and initial hesitation before execution.",
    "Rahu": "Creative artistic imagination, vivid dreams, sudden unusual desires; watch against anxiety.",
    "Ketu": "Meditative stillness, disinterest in material show, philosophical inquiry, and craving for solitude."
}

# ══════════════════════════════════════════════════════════════════
#  4. TRANSIT OF MARS OVER NATAL PLANETS
# ══════════════════════════════════════════════════════════════════

TRANSIT_MARS_OVER_NATAL = {
    "Sun": {
        "title": "Transit Mars Contacting Natal Sun",
        "prediction": "Assertive executive command, dynamic physical boldness, but warns against fiery arguments with seniors or father.",
        "severity": "warning"
    },
    "Moon": {
        "title": "Transit Mars Contacting Natal Moon",
        "prediction": "Impulsive physical drive, swift travel decisions, real estate transactions, dynamic maternal interactions, and high appetite.",
        "severity": "caution"
    },
    "Mars": {
        "title": "Transit Mars Contacting Natal Mars (Mars Return)",
        "prediction": "Peak physical vitality, initiation of engineering/machinery ventures, real estate development, and dynamic leadership.",
        "severity": "positive"
    },
    "Mercury": {
        "title": "Transit Mars Contacting Natal Mercury",
        "prediction": "Fast computational reflexes, sharp debating skills, technical drafting, but warns against hasty contractual signatures.",
        "severity": "caution"
    },
    "Jupiter": {
        "title": "Transit Mars Contacting Natal Jupiter",
        "prediction": "Righteous courage, executive triumph, successful defense of family interests, and dynamic institutional leadership.",
        "severity": "positive"
    },
    "Venus": {
        "title": "Transit Mars Contacting Natal Venus",
        "prediction": "High romantic magnetism, vehicle purchase or customization, property acquisition, and energetic commercial partnerships.",
        "severity": "positive"
    },
    "Saturn": {
        "title": "Transit Mars Contacting Natal Saturn",
        "prediction": "Mandaara transit: Tough physical endurance, mechanical labor, demands marital communication patience and bone/joint caution.",
        "severity": "warning"
    },
    "Rahu": {
        "title": "Transit Mars Contacting Natal Rahu",
        "prediction": "Intense competitive force, electronics/machinery breakthroughs, but demands strict caution against rash driving and machinery hazards.",
        "severity": "critical"
    },
    "Ketu": {
        "title": "Transit Mars Contacting Natal Ketu",
        "prediction": "Surgical precision, electrical/wiring mastery, resolution of property disputes through arbitration; Lord Kalabhairava worship recommended.",
        "severity": "warning"
    }
}

# ══════════════════════════════════════════════════════════════════
#  5. TRANSIT OF MERCURY OVER NATAL PLANETS
# ══════════════════════════════════════════════════════════════════

TRANSIT_MERCURY_OVER_NATAL = {
    "Sun": "Official correspondence, clearing administrative documentation, tax planning, and intellectual recognition.",
    "Moon": "Creative writing, counseling, rapid trade communication, marketing, and emotional adaptability.",
    "Mars": "Technical drafting, engineering calculations, business negotiation, and fast computational tasks.",
    "Mercury": "Intellectual return: New learning courses, auditing precision, trade expansions, and commercial alliances.",
    "Jupiter": "Publishing, academic honors, financial advisory consulting, and philosophical discussions.",
    "Venus": "Madhana Gopala transit: Eloquent speech, refined artistic collaboration, diplomacy, and lucrative trade alliances.",
    "Saturn": "Legal documentation, auditing scrutiny, property title verification, and structured accounting.",
    "Rahu": "Digital media innovation, IT/telecom advancements, marketing campaigns; watch fine print in contracts.",
    "Ketu": "Specialized analytical research, legal arbitration, coding mastery, and intuitive breakthroughs."
}

# ══════════════════════════════════════════════════════════════════
#  6. TRANSIT OF JUPITER OVER NATAL PLANETS
# ══════════════════════════════════════════════════════════════════

TRANSIT_JUPITER_OVER_NATAL = {
    "Sun": {
        "title": "Transit Jupiter Contacting Natal Sun",
        "prediction": "Grand royal honors, governmental promotion, paternal prosperity, broad societal respect, and divine blessings.",
        "severity": "positive"
    },
    "Moon": {
        "title": "Transit Jupiter Contacting Natal Moon (Gaja Kesari Transit)",
        "prediction": "Supreme emotional peace, lasting legacy, generous hospitality, auspicious celebrations at home, and wealth for children.",
        "severity": "positive"
    },
    "Mars": {
        "title": "Transit Jupiter Contacting Natal Mars",
        "prediction": "Magnanimous victory, acquisition of prime real estate, successful leadership in family/temple affairs, and high physical vigor.",
        "severity": "positive"
    },
    "Mercury": {
        "title": "Transit Jupiter Contacting Natal Mercury",
        "prediction": "Academic scholarship, publication of books, successful financial investments, and authoritative advisory positions.",
        "severity": "positive"
    },
    "Jupiter": {
        "title": "Transit Jupiter Contacting Natal Jupiter (Jupiter Return - 12 Year Cycle)",
        "prediction": "Major 12-year life expansion, spiritual awakening, childbirth/progeny milestones, financial prosperity, and ethical leadership.",
        "severity": "positive"
    },
    "Venus": {
        "title": "Transit Jupiter Contacting Natal Venus",
        "prediction": "Abundant luxury, marital bliss, acquisition of premium vehicles, cultural patronage, and high domestic happiness.",
        "severity": "positive"
    },
    "Saturn": {
        "title": "Transit Jupiter Contacting Natal Saturn",
        "prediction": "Career expansion, steady accumulation of assets, dependable leadership in family and business, and enduring reputation.",
        "severity": "positive"
    },
    "Rahu": {
        "title": "Transit Jupiter Contacting Natal Rahu",
        "prediction": "Guru Chandal transit: Breakthroughs in foreign or non-traditional fields, mass expansion, and dismantling obsolete boundaries.",
        "severity": "info"
    },
    "Ketu": {
        "title": "Transit Jupiter Contacting Natal Ketu",
        "prediction": "Profound spiritual wisdom, sacred pilgrimages, initiation into higher knowledge, and philanthropic fulfillment.",
        "severity": "positive"
    }
}

# ══════════════════════════════════════════════════════════════════
#  7. TRANSIT OF VENUS OVER NATAL PLANETS
# ══════════════════════════════════════════════════════════════════

TRANSIT_VENUS_OVER_NATAL = {
    "Sun": "Aristocratic contacts, government favors, luxury enjoyment, and radiant personal presentation.",
    "Moon": "Charming domestic atmosphere, exquisite cuisine, musical/artistic indulgence, and liquid cash flow.",
    "Mars": "Passionate romantic energy, real estate improvements, purchasing stylish vehicles or jewelry.",
    "Mercury": "Eloquent conversations, diplomacy, commercial profits through design/arts, and refined dressing.",
    "Jupiter": "Auspicious celebrations, generous gifts, spiritual and material harmony, and relationship bliss.",
    "Venus": "Venus Return: Peak aesthetic charm, romantic renewal, financial liquidity, and luxury shopping.",
    "Saturn": "Substantial financial returns, banking success, luxury merchandise trade, and long-standing corporate gains.",
    "Rahu": "Glamour, media charisma, sudden financial windfalls, and unconventional romantic magnetism.",
    "Ketu": "Spiritual refinement, detachment from superficial ostentation, and peaceful domestic life."
}

# ══════════════════════════════════════════════════════════════════
#  8. TRANSIT OF SATURN OVER NATAL PLANETS
# ══════════════════════════════════════════════════════════════════

TRANSIT_SATURN_OVER_NATAL = {
    "Sun": {
        "title": "Transit Saturn Contacting Natal Sun",
        "prediction": "Demands self-discipline, tests dynamics with superiors and father, culminating in hard-earned permanent authority.",
        "severity": "caution"
    },
    "Moon": {
        "title": "Transit Saturn Contacting Natal Moon (Punarpoo Transit / Sade Sati Axis)",
        "prediction": "Deep emotional maturity forged through persistent hurdles. Methodical work ethic turns initial delays into solid lifelong success.",
        "severity": "warning"
    },
    "Mars": {
        "title": "Transit Saturn Contacting Natal Mars",
        "prediction": "Severe industrial/mechanical tests, machine maintenance, requires patience in marriage and caution against physical limb injury.",
        "severity": "warning"
    },
    "Mercury": {
        "title": "Transit Saturn Contacting Natal Mercury",
        "prediction": "Business planning, bank loan structuring, meticulous legal auditing, and joint ventures. Caution: Avoid excessive speculative over-investment.",
        "severity": "caution"
    },
    "Jupiter": {
        "title": "Transit Saturn Contacting Natal Jupiter",
        "prediction": "Heavy workload, expanding institutional capacity using existing cash flow, and steady breadwinner responsibilities.",
        "severity": "positive"
    },
    "Venus": {
        "title": "Transit Saturn Contacting Natal Venus",
        "prediction": "Substantial financial gains, lucrative commercial turnover, and active patronage from women in corporate networks.",
        "severity": "positive"
    },
    "Saturn": {
        "title": "Transit Saturn Contacting Natal Saturn (Saturn Return - 30 Year Cycle)",
        "prediction": "Major 30-year life restructuring milestone, establishing long-term professional foundations, duty, and mature stability.",
        "severity": "positive"
    },
    "Rahu": {
        "title": "Transit Saturn Contacting Natal Rahu",
        "prediction": "Transformative career struggles leading to extraordinary mastery, mass influence, and technological breakthroughs.",
        "severity": "warning"
    },
    "Ketu": {
        "title": "Transit Saturn Contacting Natal Ketu",
        "prediction": "Deep spiritual dispassion, success in technical/craft/judicial fields; success achieved through complete freedom from greed.",
        "severity": "caution"
    }
}

# ══════════════════════════════════════════════════════════════════
#  9. TRANSIT OF RAHU OVER NATAL PLANETS
# ══════════════════════════════════════════════════════════════════

TRANSIT_RAHU_OVER_NATAL = {
    "Sun": {
        "title": "Transit Rahu Contacting Natal Sun",
        "prediction": "Sudden public recognition drives, paternal health vigilance, eye/spine sensitivity, and need to avoid illusionary deals.",
        "severity": "warning"
    },
    "Moon": {
        "title": "Transit Rahu Contacting Natal Moon",
        "prediction": "Hyper-imaginative visual creativity, media breakthroughs, but requires vigilance against anxiety, allergies, or food reactions.",
        "severity": "warning"
    },
    "Mars": {
        "title": "Transit Rahu Contacting Natal Mars",
        "prediction": "Aggressive competitive drive, technology/machinery breakthroughs, but demands strict caution against rash driving and accidents.",
        "severity": "critical"
    },
    "Mercury": {
        "title": "Transit Rahu Contacting Natal Mercury",
        "prediction": "Brilliant digital marketing, IT/software innovation, rapid commercial expansion; watch fine print in contracts.",
        "severity": "info"
    },
    "Jupiter": {
        "title": "Transit Rahu Contacting Natal Jupiter",
        "prediction": "Guru Chandal transit: Breakthroughs in foreign or mass institutions, challenging orthodox dogmas, and unconventional wealth.",
        "severity": "info"
    },
    "Venus": {
        "title": "Transit Rahu Contacting Natal Venus",
        "prediction": "Glamour, cinema/media magnetism, sudden financial windfalls, and unconventional luxury/relationship dynamics.",
        "severity": "warning"
    },
    "Saturn": {
        "title": "Transit Rahu Contacting Natal Saturn",
        "prediction": "Major career trials leading to breakthroughs, mass labor leadership, and transformative industrial restructuring.",
        "severity": "warning"
    },
    "Rahu": {
        "title": "Transit Rahu Contacting Natal Rahu (Nodal Return - 18 Year Cycle)",
        "prediction": "18-year karmic cycle renewal: Massive redirection of worldly desires, foreign associations, and material expansion.",
        "severity": "info"
    },
    "Ketu": {
        "title": "Transit Rahu Contacting Natal Ketu (Nodal Inversion - 9 Year Cycle)",
        "prediction": "9-year karmic polarity inversion: Forces resolution of past liabilities and shifts focus toward new evolutionary growth.",
        "severity": "caution"
    }
}

# ══════════════════════════════════════════════════════════════════
#  10. TRANSIT OF KETU OVER NATAL PLANETS
# ══════════════════════════════════════════════════════════════════

TRANSIT_KETU_OVER_NATAL = {
    "Sun": {
        "title": "Transit Ketu Contacting Natal Sun",
        "prediction": "Paternal spiritual heritage, administrative detachment, settling government tax/penalties, and deep intuitive wisdom.",
        "severity": "info"
    },
    "Moon": {
        "title": "Transit Ketu Contacting Natal Moon",
        "prediction": "Deep occult intuition, mental detachment, maternal health vigilance, and seeking quietude away from emotional drama.",
        "severity": "warning"
    },
    "Mars": {
        "title": "Transit Ketu Contacting Natal Mars",
        "prediction": "Surgical/technical precision, wiring and electrical mastery, settling property encumbrances; Lord Kalabhairava worship advised.",
        "severity": "warning"
    },
    "Mercury": {
        "title": "Transit Ketu Contacting Natal Mercury",
        "prediction": "Analytical auditing precision, break in standard routine followed by specialized wisdom in law, code, or mathematics.",
        "severity": "info"
    },
    "Jupiter": {
        "title": "Transit Ketu Contacting Natal Jupiter",
        "prediction": "Profound spiritual wisdom, saintly disposition in daily life, pilgrimage pursuits, and philanthropic fulfillment.",
        "severity": "positive"
    },
    "Venus": {
        "title": "Transit Ketu Contacting Natal Venus",
        "prediction": "Detachment from superficial luxury, electronic gadget repairs, partner's spiritual inclination, and lasting inner peace.",
        "severity": "caution"
    },
    "Saturn": {
        "title": "Transit Ketu Contacting Natal Saturn",
        "prediction": "Ascetic detachment at work, success in law, medicine, auditing, and institutional services; greedlessness brings total success.",
        "severity": "caution"
    },
    "Rahu": {
        "title": "Transit Ketu Contacting Natal Rahu (Nodal Inversion - 9 Year Cycle)",
        "prediction": "9-year karmic polarity inversion: Dismantles obsolete material attachments and accelerates spiritual evolution.",
        "severity": "caution"
    },
    "Ketu": {
        "title": "Transit Ketu Contacting Natal Ketu (Nodal Return - 18 Year Cycle)",
        "prediction": "18-year spiritual cycle renewal: Deep karmic purification, settling ancestral debts, and profound spiritual clarity.",
        "severity": "positive"
    }
}
