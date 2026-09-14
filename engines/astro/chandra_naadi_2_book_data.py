"""
Chandra Naadi Part 2 Rule Constants & Knowledge Base.
Contains all rules extracted from the second volume of the classical Nadi literature.
Provides pure astrological rule mappings for planetary combinations, transit mechanics,
Manthi computations, Badhaka indicators, Punarpoo dosha, property signatures, and medical triggers.
"""

# 1. BADHAKA_RULES
BADHAKA_RULES = {
    "Movable": {"badhaka_house": 11, "description": "For Cardinal/Movable ascendants, the 11th house is the Badhaka (obstruction) sign."},
    "Fixed": {"badhaka_house": 9, "description": "For Fixed ascendants, the 9th house is the Badhaka (obstruction) sign."},
    "Dual": {"badhaka_house": 7, "description": "For Dual ascendants, the 7th house is the Badhaka (obstruction) sign."}
}

ASCENDANT_MODES = {
    "Aries": "Movable", "Cancer": "Movable", "Libra": "Movable", "Capricorn": "Movable",
    "Taurus": "Fixed", "Leo": "Fixed", "Scorpio": "Fixed", "Aquarius": "Fixed",
    "Gemini": "Dual", "Virgo": "Dual", "Sagittarius": "Dual", "Pisces": "Dual"
}

# 2. CONJUNCTION_RULES_VOL2
CONJUNCTION_RULES_VOL2 = {
    frozenset({"Sun", "Moon"}): {
        "title": "Sun + Moon (Solar-Lunar Union)",
        "predictions": [
            "Both parents lead a harmonious and affectionate life, with the mother managing the family.",
            "Father is frequently on the move and inclined towards travel.",
            "Potential sensitivity in eyesight or subtle ocular imbalances.",
            "Mood and behavioral clarity fluctuate with the lunar waxing/waning phase."
        ],
        "category": "Conjunction",
        "severity": "info"
    },
    frozenset({"Sun", "Mars"}): {
        "title": "Sun + Mars (High Internal Fire & Willpower)",
        "predictions": [
            "High internal body heat, intense energy drives, and tendency to make sudden impulsive vocational exits.",
            "Prone to blood pressure spikes, inflammatory boils, fevers, or spinal strain when under stress.",
            "Father tends to bestow disproportionate benefits upon younger siblings.",
            "Marital harmony requires deliberate patience and temper management."
        ],
        "category": "Conjunction",
        "severity": "warning"
    },
    frozenset({"Sun", "Mercury"}): {
        "title": "Sun + Mercury (Intellectual & Administrative Acumen)",
        "predictions": [
            "Younger sister or sibling is sharp-witted, academically oriented, and articulate.",
            "The native often masters one field academically but finds career success in an entirely different domain."
        ],
        "category": "Conjunction",
        "severity": "positive"
    },
    frozenset({"Sun", "Jupiter"}): {
        "title": "Sun + Jupiter (Dignified Leadership & Paternal Nobility)",
        "predictions": [
            "Father is an individual of high principles, social dignity, honesty, and spiritual integrity.",
            "Bestows administrative capacity and community respect; if afflicted, caution is needed with public funds."
        ],
        "category": "Conjunction",
        "severity": "positive"
    },
    frozenset({"Sun", "Venus"}): {
        "title": "Sun + Venus (Radiant Status & Material Comfort)",
        "predictions": [
            "Father enjoys material wealth, social luxuries, and executive comforts.",
            "Native possesses bright, expressive eyes, affection for daughters, and refined social tastes.",
            "Reproductive vitality benefits from regular health maintenance."
        ],
        "category": "Conjunction",
        "severity": "info"
    },
    frozenset({"Sun", "Saturn"}): {
        "title": "Sun + Saturn (Karmic Duty & Paternal Friction)",
        "predictions": [
            "Father leads an austere, strenuous existence and may struggle with systematic financial management.",
            "Progeny timing or lineage responsibilities require patience and disciplined effort."
        ],
        "category": "Conjunction",
        "severity": "caution"
    },
    frozenset({"Sun", "Rahu"}): {
        "title": "Sun + Rahu (Unconventional Expansion & Paternal Karma)",
        "predictions": [
            "Attracted to cross-cultural or unconventional partnerships.",
            "Complex relationship with father or paternal lineage; income experiences sudden periodic fluctuations."
        ],
        "category": "Conjunction",
        "severity": "warning"
    },
    frozenset({"Sun", "Ketu"}): {
        "title": "Sun + Ketu (Ascetic Spirit & Paternal Sensitivities)",
        "predictions": [
            "Father possesses an intensely spiritual, detached mindset, but may suffer from intestinal, spine, or hip sensitivities.",
            "Native must maintain meticulous transparency with governmental and statutory authorities to avoid penalties."
        ],
        "category": "Conjunction",
        "severity": "caution"
    },
    frozenset({"Moon", "Mars"}): {
        "title": "Moon + Mars (Energetic Mind & Agricultural Affinity)",
        "predictions": [
            "Stout, athletic constitution, bold initiative, and fondness for savory/spicy foods.",
            "Inheritance of maternal real estate or hereditary physical traits.",
            "Prone to blood circulation sensitivity; siblings share a strong mutual bond."
        ],
        "category": "Conjunction",
        "severity": "info"
    },
    frozenset({"Moon", "Mercury"}): {
        "title": "Moon + Mercury (Vivid Imagination & Strategic Mind)",
        "predictions": [
            "Exceptional imaginative faculties, strategic planning skills, and creative intellect.",
            "Susceptible to nervous exhaustion, anxiety neurosis, or sleep tension under excessive workload.",
            "Maternal relatives have predominantly female progeny; family planning benefits from medical care."
        ],
        "category": "Conjunction",
        "severity": "info"
    },
    frozenset({"Moon", "Jupiter"}): {
        "title": "Moon + Jupiter (Gaja Kesari Fortune & Moral Standing)",
        "predictions": [
            "Auspicious combination bestowing a gracious persona, round facial features, and broad social goodwill.",
            "Accumulates assets and wealth for future generations; receives warm hospitality wherever they go."
        ],
        "category": "Conjunction",
        "severity": "positive"
    },
    frozenset({"Moon", "Venus"}): {
        "title": "Moon + Venus (Artistic Elegance & Sensual Refinement)",
        "predictions": [
            "Charming demeanor, high aesthetic refinement, and deep affinity for fine arts, literature, and luxury.",
            "Strong financial earning capacity; requires ethical mindfulness in romantic and marital relationships."
        ],
        "category": "Conjunction",
        "severity": "positive"
    },
    frozenset({"Moon", "Saturn"}): {
        "title": "Moon + Saturn (Punarpoo Dosha - Obstacles & Delay Factor)",
        "predictions": [
            "Prone to restless travels and persistent uncertainty until the final moment of completion in critical ventures.",
            "Delays in marital timing or initial roadblocks before grand celebratory outcomes.",
            "Sensitive to calcium deficiency, joint stiffness, and periods of emotional isolation."
        ],
        "category": "Conjunction",
        "severity": "caution"
    },
    frozenset({"Moon", "Rahu"}): {
        "title": "Moon + Rahu (Emotional Waves & Psychic Sensitivity)",
        "predictions": [
            "Highly intuitive but prone to sudden unexplained fears, mental illusions, or allergy flare-ups.",
            "Attracted to secret unions or unconventional beliefs; respiratory and digestive sensitivity."
        ],
        "category": "Conjunction",
        "severity": "warning"
    },
    frozenset({"Moon", "Ketu"}): {
        "title": "Moon + Ketu (Spiritual Detachment & Mental Solitude)",
        "predictions": [
            "Deep psychological introspection, periodic dejection, and detachment from worldly trivialities.",
            "Prone to dry skin, nervous sensitivity, or ocular imbalance; maternal health requires dedicated care."
        ],
        "category": "Conjunction",
        "severity": "warning"
    },
    frozenset({"Mars", "Mercury"}): {
        "title": "Mars + Mercury (Technical Genius & Analytical Speed)",
        "predictions": [
            "Sharp intellectual capacity in engineering, statistics, auditing, computing, and tactical strategy.",
            "Analytical clarity fluctuates with the lunar waxing/waning cycle; high investigative ability."
        ],
        "category": "Conjunction",
        "severity": "positive"
    },
    frozenset({"Mars", "Jupiter"}): {
        "title": "Mars + Jupiter (Commander & High Preceptor Energy)",
        "predictions": [
            "Natural leadership, courageous authority, and dedication to public welfare and societal infrastructure.",
            "Fond of rich/spicy culinary choices; requires vigilance against blood heat, inflammation, or metabolic strain.",
            "Deep protective affection for brothers and younger peers."
        ],
        "category": "Conjunction",
        "severity": "positive"
    },
    frozenset({"Mars", "Venus"}): {
        "title": "Mars + Venus (Passionate Drive & Multi-Trade Mastery)",
        "predictions": [
            "Versatile multi-skilled capability ('Jack of all trades'); capable of building substantial property and palatial homes.",
            "High physical vitality and passionate romantic drive; second child timing experiences a natural hiatus."
        ],
        "category": "Conjunction",
        "severity": "positive"
    },
    frozenset({"Mars", "Saturn"}): {
        "title": "Mars + Saturn (Mechanical Realism & Structural Endurance)",
        "predictions": [
            "Exceptional endurance in handling heavy machinery, manufacturing, construction, and older physical assets.",
            "Prone to surgical interventions, fractures, or acute physical strain if rushed.",
            "Marital life demands calm mutual forbearance to avoid legal arbitration."
        ],
        "category": "Conjunction",
        "severity": "warning"
    },
    frozenset({"Mars", "Rahu"}): {
        "title": "Mars + Rahu (Aggressive Innovation & Property Disputes)",
        "predictions": [
            "Breakthrough energy in cutting-edge technology, heavy machines, or explosive growth ventures.",
            "Disputed boundaries or litigation risks in real estate; dental and blood vitality require monitoring."
        ],
        "category": "Conjunction",
        "severity": "warning"
    },
    frozenset({"Mars", "Ketu"}): {
        "title": "Mars + Ketu (Precision Focus & Property Mortgages)",
        "predictions": [
            "Adept in precision technical crafts, electronics wiring, surgery, or specialized instrumentation.",
            "Real estate is often acquired through loans or mortgages; spiritual reverence for fierce deities brings stability."
        ],
        "category": "Conjunction",
        "severity": "caution"
    },
    frozenset({"Mercury", "Jupiter"}): {
        "title": "Mercury + Jupiter (Scholarship, Advisory & High Counsel)",
        "predictions": [
            "Round facial features, philosophical wisdom, high ethical standards, and philanthropic temperament.",
            "Natural academic counselor, author, or financial advisor; liver/digestive balance needs attention."
        ],
        "category": "Conjunction",
        "severity": "positive"
    },
    frozenset({"Mercury", "Venus"}): {
        "title": "Mercury + Venus (Artistic Elegance & Legal Brilliance)",
        "predictions": [
            "Refined speech, charm, success in legal advocacy, media, diplomacy, and commercial trade.",
            "Enjoys comfortable lifestyle, artistic circles, and gracious social relations."
        ],
        "category": "Conjunction",
        "severity": "positive"
    },
    frozenset({"Mercury", "Saturn"}): {
        "title": "Mercury + Saturn (Pragmatic Trade & Real Estate Brokerage)",
        "predictions": [
            "Methodical commercial mind well-suited for brokerage, document auditing, accounting, and land transactions.",
            "Prone to joint stiffness, skin dryness, or periodic communication hesitation under heavy stress."
        ],
        "category": "Conjunction",
        "severity": "info"
    },
    frozenset({"Mercury", "Rahu"}): {
        "title": "Mercury + Rahu (Broad Forehead & High Oratory)",
        "predictions": [
            "Prominent forehead, persuasive public speaking, quick grasping of foreign languages, and digital technology.",
            "Skin allergies or nervous hypersensitivity require gentle herbal and dietary care."
        ],
        "category": "Conjunction",
        "severity": "info"
    },
    frozenset({"Mercury", "Ketu"}): {
        "title": "Mercury + Ketu (Intuitive Research & Astrological Mind)",
        "predictions": [
            "Deep intuitive intellect, fascination with astrology, mysticism, cryptography, and esoteric coding.",
            "Occasional speech hesitation or stammering under pressure; contracts must be thoroughly documented."
        ],
        "category": "Conjunction",
        "severity": "info"
    },
    frozenset({"Jupiter", "Venus"}): {
        "title": "Jupiter + Venus (Dual Guru Prosperity & Secret Wealth)",
        "predictions": [
            "Amasses substantial wealth through advisory, finance, luxury assets, and gracious social connections.",
            "Maintains confidential financial reserves; family life is blessed and comfortable."
        ],
        "category": "Conjunction",
        "severity": "positive"
    },
    frozenset({"Jupiter", "Saturn"}): {
        "title": "Jupiter + Saturn (Dharma-Karma Union & Early Responsibility)",
        "predictions": [
            "Begins professional career and assumes family responsibilities from an early age.",
            "Work is treated as ultimate worship; enduring stamina, prone to nervous or rheumatic stiffness in later years."
        ],
        "category": "Conjunction",
        "severity": "positive"
    },
    frozenset({"Jupiter", "Rahu"}): {
        "title": "Jupiter + Rahu (Guru-Chandal Challenge & Unconventional Expansion)",
        "predictions": [
            "Challenges orthodox conventions; expands knowledge through cross-cultural or unconventional channels.",
            "Requires strict ethical integrity in public and fiduciary matters to prevent reputational slander."
        ],
        "category": "Conjunction",
        "severity": "warning"
    },
    frozenset({"Jupiter", "Ketu"}): {
        "title": "Jupiter + Ketu (Gnana Yoga & Spiritual Detachment)",
        "predictions": [
            "Saintly thoughts, profound spiritual wisdom, and natural inclination towards higher philosophy.",
            "Requires careful financial planning to prevent debt accumulation or unmerited social blame."
        ],
        "category": "Conjunction",
        "severity": "info"
    },
    frozenset({"Venus", "Saturn"}): {
        "title": "Venus + Saturn (Commercial Finance & Lasting Alliances)",
        "predictions": [
            "Lucrative earnings through corporate finance, luxury goods, banking, and real estate management.",
            "Estranged friends and old professional alliances naturally re-enter life and bring enduring profit."
        ],
        "category": "Conjunction",
        "severity": "positive"
    },
    frozenset({"Venus", "Rahu"}): {
        "title": "Venus + Rahu (Unconventional Fortunes & Volatile Romance)",
        "predictions": [
            "Unexpected financial windfalls through media, cinema, foreign trade, or luxury markets.",
            "Marital relationships require clear communication and mutual transparency to avoid discord."
        ],
        "category": "Conjunction",
        "severity": "warning"
    },
    frozenset({"Venus", "Ketu"}): {
        "title": "Venus + Ketu (Detachment in Luxury & Technical Devices)",
        "predictions": [
            "Spiritual outlook regarding material luxuries; electronic appliances and gadgets require regular upkeep.",
            "Marital harmony is sustained through emotional maturity and mutual space."
        ],
        "category": "Conjunction",
        "severity": "caution"
    },
    frozenset({"Saturn", "Rahu"}): {
        "title": "Saturn + Rahu (Strenuous Breakthroughs & Labor Management)",
        "predictions": [
            "Navigates immense operational hurdles before achieving career stability in industrial or shadow domains.",
            "Vigilance required against toxic workplace politics or abrupt strikes; benefits from steady routine."
        ],
        "category": "Conjunction",
        "severity": "warning"
    },
    frozenset({"Saturn", "Ketu"}): {
        "title": "Saturn + Ketu (Mukti Karaka & Solitary Enterprise)",
        "predictions": [
            "Deep spiritual detachment from career ambitions; flourishes in independent or specialized technical trades.",
            "Must avoid blind trust in unvetted business partnerships."
        ],
        "category": "Conjunction",
        "severity": "caution"
    }
}

# 3. MULTI_PLANET_VOCATIONS_VOL2
MULTI_PLANET_VOCATIONS_VOL2 = [
    {"planets": frozenset({"Sun", "Jupiter", "Moon"}), "vocation": "Religious Head, Preceptor, Philanthropist, University Chancellor, Trust Administrator"},
    {"planets": frozenset({"Sun", "Jupiter", "Mars"}), "vocation": "Civic President, Executive Magistrate, High Administrative Governance, Defense Management"},
    {"planets": frozenset({"Sun", "Saturn"}), "vocation": "Senior Accounts Officer, Public Administrative Auditing, Family Enterprise, Orthopedic / Bone Medicine"},
    {"planets": frozenset({"Sun", "Jupiter", "Mercury"}), "vocation": "Hereditary Enterprise, Fiduciary Accounts Manager, Educational Trust Director"},
    {"planets": frozenset({"Moon", "Ketu", "Jupiter", "Mars"}), "vocation": "Textile Manufacturing (Silk & Cotton Thread), Temple Merchandising, Indigenous Medicinal Supplies"},
    {"planets": frozenset({"Moon", "Mars", "Saturn"}), "vocation": "Transport Logistics, Heavy Commercial Fleet Management, Agriculture Machinery, Civil Engineering"},
    {"planets": frozenset({"Moon", "Venus", "Mercury"}), "vocation": "Maritime Logistics, Luxury Cruise Enterprises, Architectural Complexes, Skyscraper Construction"},
    {"planets": frozenset({"Moon", "Venus"}), "vocation": "Advanced Electronic Media, Cinematic Photography, Haute Couture, Sophisticated Communication Equipment"},
    {"planets": frozenset({"Moon", "Saturn"}), "vocation": "Dairy Distribution, Pure Water Plants, Hospitality Catering, Food Processing, Travel Agency"},
    {"planets": frozenset({"Jupiter", "Venus"}), "vocation": "Wealth Asset Management, Vehicle Financing, Gold Jewelry Bullion, Commercial Banking"},
    {"planets": frozenset({"Jupiter", "Venus", "Rahu"}), "vocation": "Automobile Leasing, Precious Metal Imports, International Foreign Exchange Trade"},
    {"planets": frozenset({"Jupiter", "Sun"}), "vocation": "High Political Statesmanship, Executive Bureaucratic Administration, Advisory To Leaders"}
]

# 4. MARS_PROPERTY_SIGNATURES
MARS_PROPERTY_SIGNATURES = {
    "Sun": "Paternal landed estates, grand civic structures, stately administrative buildings.",
    "Moon": "Maternal landed property, fertile waterfront plots, agricultural tracts near water sources.",
    "Mercury": "Lush agricultural green fields, commercial shopping plazas, prime urban business spaces.",
    "Jupiter": "Highly valuable ancestral land, temple endowments, institutional trusts, properties secured for future generations.",
    "Venus": "Commercial showrooms in busy marketplaces, prime luxury residences registered in spouse's name.",
    "Saturn": "Hereditary ancestral acres, old industrial estates, factories, workshops, and commercial operational sites.",
    "Rahu": "Encumbered real estate, disputed acquisitions, land with high development density or complex titles.",
    "Ketu": "Disputed corner plots, ancestral holdings subject to legal clearance, small compact landholdings."
}

# 5. MANTHI_BHAVA_EFFECTS
MANTHI_BHAVA_EFFECTS = {
    1: {"title": "Manthi in House 1", "effect": "Impulsive temperamental bursts, sleepy ocular expression, sharp quick reactions, and intense internal drive."},
    2: {"title": "Manthi in House 2", "effect": "Stammering under stress, harsh vocal delivery, uneven cash flow, and need for ocular care."},
    3: {"title": "Manthi in House 3", "effect": "Friction with siblings, bold audacious courage, self-willed stubbornness, and inner emotional moodiness."},
    4: {"title": "Manthi in House 4", "effect": "Domestic friction, maternal health vigilance, vehicular repair expenses, and seeking peace outside hometown."},
    5: {"title": "Manthi in House 5", "effect": "Sharp critical thinking, academic distractions in early youth, and progeny care requiring medical attention."},
    6: {"title": "Manthi in House 6", "effect": "Acute dispute resolution capacity, overcoming secret competitors, and managing digestive/intestinal acidity."},
    7: {"title": "Manthi in House 7", "effect": "Marital frictions, delay in nuptials, eccentric business partnerships, and interpersonal adjustments."},
    8: {"title": "Manthi in House 8", "effect": "Chronic piles or rectal sensitivity, sudden unexpected hurdles, occult interests, and fear of intoxication."},
    9: {"title": "Manthi in House 9", "effect": "Paternal health sensitivities, ancestral karmic duties, and expenditure on traditional rituals."},
    10: {"title": "Manthi in House 10", "effect": "Frugal financial management, career transitions, independent working style, and needing workplace self-respect."},
    11: {"title": "Manthi in House 11", "effect": "Substantial profits and material accumulation, commanding physique, but complex friendship dynamics."},
    12: {"title": "Manthi in House 12", "effect": "Heavy expenditure, hospital or lab expenses, interest in alchemy/occult research, and overseas settlement drives."}
}

# 6. MANTHI_PLANET_CONJUNCTIONS
MANTHI_PLANET_CONJUNCTIONS = {
    "Sun": "Karmic sensitivity to father, paternal lineage duties, and administrative scrutiny.",
    "Moon": "Karmic sensitivity to mother, fluctuating emotional composure, and psychological anxiety.",
    "Mars": "Blood-related vitality sensitivity, friction with brothers/peers, and accident vulnerability.",
    "Mercury": "Sensitivity to maternal uncles, speech or grasping delays in early childhood, and contract caution.",
    "Jupiter": "Progeny delays, needing dedicated traditional prayers for family prosperity.",
    "Venus": "Marital tensions, expenditure on spouse's health, and reproductive sensitivity.",
    "Saturn": "Lethargy or professional slowdowns, ancestral karmic burdens, and bone/rheumatic stiffness.",
    "Rahu": "Severe toxic or poisoning risks, hidden obstacles, and intense karmic challenges.",
    "Ketu": "Ancestral maternal curses, litigations, separation risks, and profound spiritual turning points."
}

# 7. CHANDRASHTAMA_BHAVA_MANIFESTATIONS
CHANDRASHTAMA_BHAVA_MANIFESTATIONS = {
    1: "Liquid cash leakage, relocation from home, and misunderstandings within the domestic circle.",
    2: "Financial squandering through peers, communication lapses, and unkept financial commitments.",
    3: "Fatigue, residence disputes, physical stamina drop, and temporary feelings of defeat.",
    4: "Medical expenses for children, domestic disharmony, and unpleasant travel hurdles.",
    5: "Emotional distress, urge to borrow money, and workplace stress.",
    6: "Interpersonal arguments with partner, profit reduction, and friction with relatives.",
    7: "Tension with spouse/business partners, and contract delays.",
    8: "Unsettling news from afar, spousal discord, and long-distance communication confusion.",
    9: "Meagre immediate revenues, paternal stress, and spiritual doubts.",
    10: "Losses from hasty commercial decisions, minor mishaps, and tenant/workplace disputes.",
    11: "Ineffective initiatives, domestic security caution, and souring of well-intentioned acts.",
    12: "Wasteful travel expenses, misunderstandings with younger family members, and sleeplessness."
}

# 8. TRANSIT_STRENGTH_MODULATION_TABLE
TRANSIT_STRENGTH_MODULATION_TABLE = {
    "Mars": {
        "exalted_sign": "Capricorn", "debilitated_sign": "Cancer", "own_signs": ["Aries", "Scorpio"],
        "transit_exalted_mult": 2.5, "transit_debilitated_mult": 0.25, "transit_own_mult": 1.5
    },
    "Jupiter": {
        "exalted_sign": "Cancer", "debilitated_sign": "Capricorn", "own_signs": ["Sagittarius", "Pisces"],
        "transit_exalted_mult": 2.5, "transit_debilitated_mult": 0.25, "transit_own_mult": 1.5
    },
    "Saturn": {
        "exalted_sign": "Libra", "debilitated_sign": "Aries", "own_signs": ["Capricorn", "Aquarius"],
        "transit_exalted_mult": 2.5, "transit_debilitated_mult": 0.25, "transit_own_mult": 1.5
    },
    "Venus": {
        "exalted_sign": "Pisces", "debilitated_sign": "Virgo", "own_signs": ["Taurus", "Libra"],
        "transit_exalted_mult": 2.5, "transit_debilitated_mult": 0.25, "transit_own_mult": 1.5
    },
    "Mercury": {
        "exalted_sign": "Virgo", "debilitated_sign": "Pisces", "own_signs": ["Gemini", "Virgo"],
        "transit_exalted_mult": 2.5, "transit_debilitated_mult": 0.25, "transit_own_mult": 1.5
    },
    "Sun": {
        "exalted_sign": "Aries", "debilitated_sign": "Libra", "own_signs": ["Leo"],
        "transit_exalted_mult": 2.5, "transit_debilitated_mult": 0.25, "transit_own_mult": 1.5
    },
    "Moon": {
        "exalted_sign": "Taurus", "debilitated_sign": "Scorpio", "own_signs": ["Cancer"],
        "transit_exalted_mult": 2.5, "transit_debilitated_mult": 0.25, "transit_own_mult": 1.5
    }
}
