"""
Lal Kitab Core Knowledge Base & Rule Constants.
Contains the fundamental principles, planetary house placements, aspect mechanics (Takkar, Dhoka, Buniyad),
Pakka Ghar (permanent houses), Soya Graha/Ghar (sleeping planets/houses), Masnui Grahas (compound planets),
Pitra Rina (ancestral debts), house precautions (Parhez), conjunction remedies, and classical Upayas.
Zero author or publisher attributions are included.
"""

# 1. PERMANENT HOUSES (PAKKA GHAR)
LAL_KITAB_PAKKA_GHAR = {
    "Sun": [1],
    "Moon": [4],
    "Mars": [3, 8],
    "Mercury": [6, 7],
    "Jupiter": [2, 5, 9, 11, 12],
    "Venus": [2, 7],
    "Saturn": [8, 10],
    "Rahu": [12],
    "Ketu": [6]
}

# 2. HOUSE SIGNIFICATIONS AND NATURAL LAL KITAB RULERS
LAL_KITAB_HOUSE_KARAKAS = {
    1: {"natural_sign": "Aries", "ruler": "Mars", "co_ruler": "Sun", "domain": "Self, vitality, physical temperament, head, honor"},
    2: {"natural_sign": "Taurus", "ruler": "Venus", "co_ruler": "Jupiter", "domain": "Wealth, liquid cash, speech, family inheritance, temple/altar"},
    3: {"natural_sign": "Gemini", "ruler": "Mercury", "co_ruler": "Mars", "domain": "Siblings, courage, hand-skills, direct enterprise, bold ventures"},
    4: {"natural_sign": "Cancer", "ruler": "Moon", "co_ruler": "Moon", "domain": "Mother, inner peace, vehicles, water sources, ancestral land"},
    5: {"natural_sign": "Leo", "ruler": "Sun", "co_ruler": "Jupiter", "domain": "Progeny, intellect, future destiny, purva punya, mantra wisdom"},
    6: {"natural_sign": "Virgo", "ruler": "Mercury", "co_ruler": "Ketu", "domain": "Diseases, debts, maternal uncles, secret enemies, daily service"},
    7: {"natural_sign": "Libra", "ruler": "Venus", "co_ruler": "Mercury", "domain": "Spouse, marriage, commercial partnerships, public dealings, household balance"},
    8: {"natural_sign": "Scorpio", "ruler": "Mars", "co_ruler": "Saturn", "domain": "Longevity, sudden events, hidden liabilities, transformations, occult depths"},
    9: {"natural_sign": "Sagittarius", "ruler": "Jupiter", "co_ruler": "Jupiter", "domain": "Father, fortune, higher dharma, ancestral blessings, guru counsel"},
    10: {"natural_sign": "Capricorn", "ruler": "Saturn", "co_ruler": "Saturn", "domain": "Career status, executive authority, government favor, professional karma"},
    11: {"natural_sign": "Aquarius", "ruler": "Saturn", "co_ruler": "Jupiter", "domain": "Gains, regular revenues, elder siblings, major aspiration fulfillment"},
    12: {"natural_sign": "Pisces", "ruler": "Jupiter", "co_ruler": "Rahu", "domain": "Expenditures, isolation, foreign connections, hospital/bedroom, moksha"}
}

# 3. PLANETARY DIGNITIES IN LAL KITAB HOUSES
LAL_KITAB_DIGNITIES = {
    "Sun": {"exalted_house": 1, "debilitated_house": 7, "benefic_houses": [1, 2, 3, 4, 5, 9, 10, 11], "malefic_houses": [6, 7, 8, 12]},
    "Moon": {"exalted_house": 2, "debilitated_house": 8, "benefic_houses": [1, 2, 3, 4, 5, 7, 9, 10, 11], "malefic_houses": [6, 8, 12]},
    "Mars": {"exalted_house": 10, "debilitated_house": 4, "benefic_houses": [1, 2, 3, 5, 6, 9, 10, 11], "malefic_houses": [4, 8, 12]},
    "Mercury": {"exalted_house": 6, "debilitated_house": 12, "benefic_houses": [1, 2, 4, 5, 6, 7, 10, 11], "malefic_houses": [3, 8, 9, 12]},
    "Jupiter": {"exalted_house": 4, "debilitated_house": 10, "benefic_houses": [1, 2, 3, 4, 5, 7, 8, 9, 11, 12], "malefic_houses": [6, 7, 10]},
    "Venus": {"exalted_house": 12, "debilitated_house": 6, "benefic_houses": [1, 2, 3, 4, 5, 7, 8, 11, 12], "malefic_houses": [6, 9, 10]},
    "Saturn": {"exalted_house": 7, "debilitated_house": 1, "benefic_houses": [2, 3, 7, 8, 9, 10, 11, 12], "malefic_houses": [1, 4, 5, 6]},
    "Rahu": {"exalted_house": 3, "debilitated_house": 9, "benefic_houses": [3, 4, 6, 10, 11, 12], "malefic_houses": [1, 2, 5, 7, 8, 9]},
    "Ketu": {"exalted_house": 9, "debilitated_house": 3, "benefic_houses": [1, 2, 5, 6, 9, 11, 12], "malefic_houses": [3, 4, 7, 8, 10]}
}

# 4. KISMAT JAGANE WALE GRAHA (DESTINY AWAKENING AGES)
LAL_KITAB_DESTINY_AWAKENING = {
    1: {"planet": "Mars", "age": 28, "theme": "Awakening of self-direction, personal independence, and executive boldness"},
    2: {"planet": "Moon", "age": 24, "theme": "Awakening of financial liquidity, family settlement, and wealth foundation"},
    3: {"planet": "Mercury", "age": 34, "theme": "Awakening of commercial enterprise, marketing reach, and sibling cooperation"},
    4: {"planet": "Moon", "age": 24, "theme": "Awakening of real estate acquisitions, domestic bliss, and emotional peace"},
    5: {"planet": "Sun", "age": 22, "theme": "Awakening of intellectual recognition, creative brilliance, and progeny blessing"},
    6: {"planet": "Rahu", "age": 42, "theme": "Awakening of competitive supremacy, debt clearance, and strategic mastery"},
    7: {"planet": "Venus", "age": 25, "theme": "Awakening of marital fortune, lucrative partnerships, and public prestige"},
    8: {"planet": "Moon", "age": 24, "theme": "Awakening of crisis-resolution power, secret wealth, and transformative resilience"},
    9: {"planet": "Jupiter", "age": 16, "theme": "Awakening of higher fortune, institutional mentorship, and ancestral dharma"},
    10: {"planet": "Saturn", "age": 36, "theme": "Awakening of enduring career authority, permanent assets, and executive standing"},
    11: {"planet": "Jupiter", "age": 16, "theme": "Awakening of expanding revenue networks, elder sibling blessings, and dream fulfillment"},
    12: {"planet": "Rahu / Ketu", "age": 48, "theme": "Awakening of international trade, overseas settlement, and spiritual transcendence"}
}

# 5. SPECIAL LAL KITAB ASPECT DYNAMICS
LAL_KITAB_ASPECT_RULES = {
    "direct_100": {
        "description": "Full 100% Sight (Opposite House Interaction)",
        "pairs": [(1, 7), (7, 1), (2, 8), (8, 2), (3, 9), (9, 3), (4, 10), (10, 4), (5, 11), (11, 5), (6, 12), (12, 6)]
    },
    "half_50": {
        "description": "50% Special Sight (Fourth House & Eighth House Gaze)",
        "pairs": [(4, 8), (4, 10)]
    },
    "quarter_25": {
        "description": "25% Foundation Gaze (Third House Forward Rays)",
        "pairs": [(3, 9), (3, 11)]
    },
    "takkar": {
        "description": "Takkar (Direct Collision / Frontal Clash)",
        "pairs": [(1, 8), (8, 1), (2, 8), (8, 2), (6, 12), (12, 6)],
        "effect": "Direct structural collision between planetary forces creating volatile outcomes until balanced by charity or counter-upayas."
    },
    "dhoka": {
        "description": "Dhoka Drishti (Deception / Mutual Undermining)",
        "pairs": [(10, 2), (8, 2), (5, 9)],
        "effect": "The higher positioned house undermines the lower house's yields through unexpected financial leakages or unfulfilled promises."
    },
    "buniyad": {
        "description": "Buniyad (Foundational Pillar Support)",
        "pairs": [(9, 5), (9, 1), (5, 1)],
        "effect": "The 9th house acts as the foundational taproot that feeds growth and resilience to the 5th and 1st houses."
    }
}

# 6. MASNUI GRAHAS (ARTIFICIAL / COMPOUND PLANETS)
LAL_KITAB_MASNUI_GRAHAS = {
    "Sun": {"components": ("Mercury", "Venus"), "nature": "Radiance and executive authority generated through commercial strategy and artistic tact."},
    "Moon": {"components": ("Sun", "Jupiter"), "nature": "Peace of mind and pure intuition formed through spiritual truth and royal integrity."},
    "Mars_Positive": {"components": ("Sun", "Mercury"), "nature": "Mars Nek (Righteous Bravery): Courageous leadership backed by tactical intellect."},
    "Mars_Negative": {"components": ("Sun", "Saturn"), "nature": "Mars Bad (Cruel / Obstinate Fire): Impulsive rage, blood pressure, and conflict."},
    "Mercury": {"components": ("Jupiter", "Rahu"), "nature": "High analytical intellect coupled with quick shrewdness and commercial diplomacy."},
    "Jupiter": {"components": ("Sun", "Venus"), "nature": "Dignified prosperity, righteous wisdom, and high societal counsel."},
    "Venus": {"components": ("Rahu", "Ketu"), "nature": "Sensual fascination, artistic charm, and material beauty."},
    "Saturn": {"components": ("Venus", "Mars"), "nature": "Enduring structural labor, iron discipline, and relentless perseverance."},
    "Rahu": {"components": ("Mars", "Saturn"), "nature": "Explosive ambition, sudden technical transformations, and foreign appetites."},
    "Ketu": {"components": ("Venus", "Saturn"), "nature": "Spiritual renunciation, legal mastery, precision technical skill, and deep detachment."}
}

# 7. PITRA RINA (THE 9 ANCESTRAL DEBTS & AUTHENTIC REMEDIES)
LAL_KITAB_PITRA_RINA = {
    "Pitra_Rina": {
        "name": "Forefathers' Debt (Pitra Rina)",
        "condition": "Jupiter afflicted by Venus, Mercury, Saturn, or Rahu in Houses 2, 5, 9, or 12.",
        "symptoms": "Hair turning grey prematurely, sudden losses in family prestige, obstacles in lineage expansion, educational breaks in children.",
        "remedy": "Collect equal donations from all blood relatives and perform charity in temple/pilgrimage shrines, or plant yellow flowering trees."
    },
    "Matru_Rina": {
        "name": "Mother's Debt (Matru Rina)",
        "condition": "Moon afflicted by Ketu or Rahu in House 4.",
        "symptoms": "Chronic financial liquidity drainage, constant emotional unrest, loss of ancestral property, health struggles for mother.",
        "remedy": "Collect equal silver coins or silver objects from all blood family members and immerse them in running clean river water."
    },
    "Swakathya_Rina": {
        "name": "Self Debt (Swakathya Rina)",
        "condition": "Sun afflicted in Houses 1, 5, or 11 by Saturn, Rahu, or Ketu.",
        "symptoms": "Struggles with governmental authorities, loss of personal reputation, severe heart/spine sensitivity, unmerited legal notices.",
        "remedy": "Collect equal monetary contributions from all blood relatives and perform yagyas / sponsor food for cows and stray animals."
    },
    "Bhratri_Rina": {
        "name": "Sibling / Relative Debt (Bhratri Rina)",
        "condition": "Mars afflicted in Houses 3 or 8 by Mercury or Ketu.",
        "symptoms": "Extreme friction or estrangement with brothers/close peers, property litigations, accidental physical injuries, feeling unhelped.",
        "remedy": "Collect equal copper coins/articles from blood relatives and donate them towards medicine, healthcare, or charitable clinics."
    },
    "Stri_Rina": {
        "name": "Woman / Spouse Debt (Stri Rina)",
        "condition": "Venus afflicted in Houses 2 or 7 by Sun or Rahu.",
        "symptoms": "Marital discord, separation, delayed progeny, sudden destruction of household luxuries, recurring domestic turmoil.",
        "remedy": "Collect equal money from all blood relatives and feed 100 cows with fresh green fodder, or sponsor educational supplies for young girls."
    },
    "Zulm_Rina": {
        "name": "Oppression / Cruelty Debt (Zulm Rina)",
        "condition": "Saturn afflicted in Houses 8, 10, or 11 by Sun, Moon, or Mars.",
        "symptoms": "Sudden legal entrapments, sudden destruction of property through fire/collapse, severe chronic joint or bone diseases.",
        "remedy": "Collect equal money from all blood family members and feed 100 poor laborers, artisans, or distribute black blankets to the needy."
    },
    "Kanya_Rina": {
        "name": "Unborn / Girl Child Debt (Kanya Rina)",
        "condition": "Ketu afflicted in Houses 6 or 12 by Moon or Mars.",
        "symptoms": "Difficulties in child conception, chronic ear/urinary/joint ailments, sudden loss of ancestral legacy.",
        "remedy": "Collect equal yellow bananas or saffron from all relatives and donate them to orphanages, or feed stray dogs regularly."
    },
    "Ishwar_Rina": {
        "name": "Divine / Spiritual Debt (Ishwar Rina)",
        "condition": "Mercury afflicted in Houses 6 or 7 by Jupiter or Moon.",
        "symptoms": "Loss of business acumen, dental/speech ailments, sudden loss of honor through deceitful friends, broken vows.",
        "remedy": "Pierce nose and wear a pure silver wire for 100 days; keep a small solid silver ball in pocket; clean temple floors voluntarily."
    }
}

# 8. GENERAL REMEDY RULES & PROTOCOLS
LAL_KITAB_GENERAL_REMEDY_RULES = {
    "timing": "Perform all remedies between sunrise and sunset; never perform daytime Lal Kitab remedies after sunset unless specifically prescribed.",
    "duration": "Standard individual remedies should be performed continuously for 40 to 43 days without a single day's interruption. If missed, restart from Day 1.",
    "unearned_items": "Never accept free items, unearned donations, iron objects, or electronic gadgets from strangers.",
    "purity": "Maintain strict vegetarianism and avoid alcohol/tobacco during the active 43-day remedial period."
}

# 9. HOUSE-WISE PRECAUTIONS (PARHEZ)
LAL_KITAB_HOUSE_PRECAUTIONS = {
    "Sun": {
        1: "Never keep water containers or leaks right in the bedroom; do not accept free electricity or gifts from superiors.",
        2: "Do not accept silver or coconut in charity; avoid harsh disputes at the dining table.",
        3: "Never misbehave with younger brothers or neighbors; avoid dark blue curtains in the study.",
        4: "Never sell ancestral property or gold in haste; avoid constructing dark rooms beneath the staircase.",
        5: "Never make false promises to children or students; do not disrespect teachers.",
        6: "Do not keep dogs inside the bedroom; avoid borrowing money on Sundays.",
        7: "Never start a partnership in brass or copper without consulting spouse; avoid heated marital arguments at sunset.",
        8: "Never construct a south-facing main entrance without remedies; do not keep unused red cloth in cupboards.",
        9: "Never disrespect paternal lineage or spiritual preceptors; avoid wearing brass ornaments.",
        10: "Never wear black clothes on Sundays; avoid taking free services from government staff.",
        11: "Never consume meat or alcohol on Sundays; do not keep broken watches at home.",
        12: "Never build a completely enclosed courtyard with zero sunlight; avoid sleeping in dark suffocating basements."
    },
    "Moon": {
        1: "Never drink milk in green vessels; do not disrespect mother under any circumstance.",
        2: "Never sell silver received from mother; avoid commercial dairy trade from personal residence.",
        3: "Never speak harshly to sisters or young girls; do not donate white clothes after sunset.",
        4: "Never sell milk or curd for direct commercial profit from home; maintain pristine clean water tanks.",
        5: "Never engage in greedy stock speculation; avoid speaking ill of maternal elders.",
        6: "Never keep underground water tanks in the exact center of the house; avoid wasting drinking water.",
        7: "Never enter into a commercial dairy partnership; respect spouse unconditionally.",
        8: "Never build underground wells or tanks in the central living area; avoid cold damp environments.",
        9: "Never criticize religious philosophies or pilgrimages; avoid donating milk at night.",
        10: "Never consume alcohol; do not construct liquid storage on the direct western rooftop.",
        11: "Never consume milk mixed with sour items; avoid unboiled milk offerings to enemies.",
        12: "Never donate milk or water at night; do not keep open water glasses overnight near the headboard."
    },
    "Mars": {
        1: "Never accept free ivory, iron scrap, or weapons; avoid impulsive temperamental reactions.",
        2: "Never speak harshly while eating; avoid keeping broken electrical appliances at home.",
        3: "Never quarrel with younger brothers; avoid keeping rusty weapons or knives in open sight.",
        4: "Never keep a boiler or tandoor in the northeast corner; avoid domestic screaming.",
        5: "Never break oaths made to children; avoid excessive spicy culinary indulgences.",
        6: "Never disrespect maternal uncles or employees; avoid legal shortcuts.",
        7: "Never indulge in extra-marital flirtation; maintain contractual clarity in partnerships.",
        8: "Never consume alcohol or non-vegetarian food on Tuesdays; avoid high-speed reckless driving.",
        9: "Never criticize family preceptors or temples; avoid false court testimonies.",
        10: "Never serve stale food to guests; keep the central hall free of scrap and heavy iron.",
        11: "Never cheat business partners in land deals; avoid keeping rusty tools under the bed.",
        12: "Never take loans for speculative luxury spending; avoid unnecessary nocturnal arguments."
    },
    "Mercury": {
        1: "Never paint bedroom walls dark green; avoid accepting free electronic gadgets.",
        2: "Never take money through forged accounts or duplicate invoices; avoid deceit in trade.",
        3: "Never deceive younger sisters or female relatives; do not clean teeth with harmful chemicals.",
        4: "Never engage in gambling or reckless speculative day-trading.",
        5: "Never wear green clothes during major academic or business examinations.",
        6: "Never pierce ears without gold/silver wire; do not keep broken clocks or pens.",
        7: "Never disrespect in-laws or commercial brokers; avoid gambling.",
        8: "Never keep dead clocks, broken mirrors, or rusted electronics at home.",
        9: "Never speak foul words or indulge in slander; avoid green colored headwear.",
        10: "Never consume alcohol or non-veg food on Wednesdays; avoid false accounting.",
        11: "Never keep broken glass objects, defective televisions, or unused copper cables at home.",
        12: "Never make empty promises or sign contracts without thorough legal vetting."
    },
    "Jupiter": {
        1: "Never accept unearned charity or gifts from saints; avoid vanity and arrogance.",
        2: "Never disrespect elders, Brahmins, or holy books; avoid taking bribes.",
        3: "Never speak ill of spiritual teachers or mentors; avoid wearing torn yellow clothes.",
        4: "Never insult mother or preceptors; avoid disrespecting family traditions.",
        5: "Never accept alms or donations meant for orphanages/temples for personal use.",
        6: "Never display false religiosity or boast about spiritual practices.",
        7: "Never speak ill of your spouse's character; avoid unprincipled business deals.",
        8: "Never disrespect sages or traditional scriptures; avoid keeping dusty unread holy books.",
        9: "Never abandon traditional family rituals or deities; avoid brass scrap.",
        10: "Never let arrogance cloud your professional duties; avoid drinking alcohol.",
        11: "Never break solemn vows made in front of an altar; avoid corrupt earnings.",
        12: "Never display hypocrisy in charity; avoid unhygienic personal habits."
    },
    "Venus": {
        1: "Never wear unwashed, wrinkled, or torn clothes; avoid dirty living spaces.",
        2: "Never speak harshly to women in the family; avoid hoarding unusable cosmetics.",
        3: "Never speak ill of sisters or daughters; avoid disheveled grooming.",
        4: "Never keep clutter under the bed; avoid arguments in the bedroom.",
        5: "Never indulge in marital infidelity; support the welfare of young girls.",
        6: "Never leave personal clothing strewn across the floor; avoid kidney/sugar neglect.",
        7: "Never insult or belittle your spouse; respect the partner as the living Lakshmi.",
        8: "Never accept free makeup, perfumes, or jewelry from strangers.",
        9: "Never disrespect in-laws or female elders; avoid broken musical instruments.",
        10: "Never allow the workplace to become filthy or chaotic; avoid vanity.",
        11: "Never borrow jewelry or luxury cars to show off false wealth.",
        12: "Never keep dead or artificial plastic flowers in the bedroom; keep commitments."
    },
    "Saturn": {
        1: "Never consume alcohol, meat, or tobacco; avoid taking free iron items.",
        2: "Never cheat laborers or domestic staff of their rightful wages.",
        3: "Never keep rusty iron scrap, old tires, or broken furniture on the rooftop.",
        4: "Never construct the roof of a house during the night; avoid domestic friction.",
        5: "Never gamble or engage in unlawful shortcuts; respect hardworking staff.",
        6: "Never neglect footwear hygiene; avoid mistreating animals or servants.",
        7: "Never deceive your business or marital partner; maintain contractual honesty.",
        8: "Never take free iron tools or oil from others; avoid dark unventilated corners.",
        9: "Never disrespect ancient traditions or elderly mendicants; avoid black paint in prayer room.",
        10: "Never consume alcohol at work; avoid exploiting subordinates.",
        11: "Never hoard junk, scrap metal, or dead electronics in the north or east.",
        12: "Never sleep in a room with a cracked ceiling or broken door frames."
    },
    "Rahu": {
        1: "Never wear dark blue or smoky black clothes during auspicious events; avoid arrogance.",
        2: "Never accept electronic items from strangers; avoid abusive language.",
        3: "Never maintain bad relations with immediate neighbors; avoid hoarding copper scrap.",
        4: "Never store junk, coal, or broken electronics in the northeast corner of the house.",
        5: "Never indulge in fraudulent financial speculation or lottery scams.",
        6: "Never mistreat servants, sanitation workers, or stray dogs.",
        7: "Never keep secrets from your spouse in financial contracts.",
        8: "Never accept free almonds, blankets, or electrical goods.",
        9: "Never disrespect religious institutions or family elders; avoid atheistic arrogance.",
        10: "Never accept free electricity or electronic appliances from official clients.",
        11: "Never consume food from questionable sources; avoid unvetted digital investments.",
        12: "Never eat meals in bed; eat sitting in the kitchen; avoid cluttered bedroom."
    },
    "Ketu": {
        1: "Never harm or kick stray dogs; avoid cynical detachment from family.",
        2: "Never speak with malice or sarcastic sting; avoid unearned wealth.",
        3: "Never cheat siblings or artisans; avoid hoarding broken needles or tailoring tools.",
        4: "Never disrespect mother or spiritual mendicants; avoid noisy home environments.",
        5: "Never mock spiritual or esoteric sciences; support children sincerely.",
        6: "Never ill-treat maternal relatives or children; maintain clean footwear.",
        7: "Never use harsh cutting words with spouse; give mutual emotional space.",
        8: "Never keep broken two-colored blankets or torn rugs at home.",
        9: "Never disrespect spiritual gurus, flagpoles, or temple shrines.",
        10: "Never engage in deceitful precision craftsmanship or forged engineering.",
        11: "Never accept free blankets or multi-colored shawls from strangers.",
        12: "Never maintain unhygienic sleeping arrangements; avoid false asceticism."
    }
}

# 10. PLANETARY CONJUNCTION REMEDIES (DUAL-GRAHA PROTOCOLS)
LAL_KITAB_CONJUNCTION_REMEDIES = {
    frozenset({"Sun", "Saturn"}): {
        "title": "Sun + Saturn Conjunction (Fire-Iron Friction)",
        "prediction": "Creates friction between executive ambition and structural discipline, or paternal misunderstandings.",
        "upaya": "Bury an earthenware pot filled with pure mustard oil underground in a deserted place before sunset; feed monkeys with jaggery and roasted chickpeas on Tuesdays."
    },
    frozenset({"Sun", "Rahu"}): {
        "title": "Sun + Rahu Conjunction (Solar Eclipse Pattern)",
        "prediction": "Sudden ups and downs in social reputation, administrative scrutiny, or paternal health stress.",
        "upaya": "Collect equal money from all blood family members and sponsor food for cows; immerse 1 kg of whole barley (jau) washed in milk into running river water on a Sunday morning."
    },
    frozenset({"Mars", "Rahu"}): {
        "title": "Mars + Rahu Conjunction (Angarak Yoga / High Voltage)",
        "prediction": "Intense internal drive, impatience, accident vulnerability, and property disputes.",
        "upaya": "Keep a solid piece of silver under your pillow; feed stray black dogs with sweet rotis; pour milk at the roots of a Banyan tree on Tuesday mornings."
    },
    frozenset({"Moon", "Saturn"}): {
        "title": "Moon + Saturn Conjunction (Vish Yoga / Emotional Coldness)",
        "prediction": "Mental heaviness, initial delays before major celebrations, and calcium sensitivity.",
        "upaya": "Pour unboiled cow's milk on a Shivalinga on Mondays; offer water mixed with milk to a Peepal tree on Saturdays; keep a solid silver square in your pocket."
    },
    frozenset({"Mercury", "Rahu"}): {
        "title": "Mercury + Rahu Conjunction (Complex Intellect / Nerve Sensitivity)",
        "prediction": "Sharp analytical intellect, digital mastery, but prone to skin allergies or speech stress.",
        "upaya": "Pierce nose and wear a pure silver wire for 100 days; keep a solid silver ball in pocket; feed green grass to goats or birds on Wednesdays."
    },
    frozenset({"Jupiter", "Rahu"}): {
        "title": "Jupiter + Rahu Conjunction (Guru Chandal Pattern)",
        "prediction": "Challenges traditional dogma; requires strict fiduciary ethics in management.",
        "upaya": "Apply a pure saffron (kesar) or turmeric tilak on the forehead and navel daily; clean temple floors voluntarily; wear a pure gold chain."
    },
    frozenset({"Venus", "Ketu"}): {
        "title": "Venus + Ketu Conjunction (Detached Luxury / Electronic Glitches)",
        "prediction": "Spiritual outlook on material wealth; domestic gadgets require frequent upkeep.",
        "upaya": "Donate white and multi-colored blankets to poor elderly persons; feed cows with curd and fodder; maintain mutual space and respect in marriage."
    },
    frozenset({"Saturn", "Rahu"}): {
        "title": "Saturn + Rahu Conjunction (Shrapit / Strenuous Labor)",
        "prediction": "Heavy operational hurdles before achieving breakthrough stability in career.",
        "upaya": "Immerse a whole coconut with husk in flowing clean river water on Saturdays; distribute black blankets and mustard oil to poor laborers."
    }
}

# 11. PLANETARY PLACEMENT RULES AND PRACTICAL UPAYAS (12 HOUSES FOR 9 PLANETS)
LAL_KITAB_PLANET_HOUSE_RULES = {
    "Sun": {
        1: {"title": "Sun in House 1 (Royal King)", "result": "Natural leader, commanding authority, radiant health. If afflicted, ego creates friction.", "upaya": "Build a small water reservoir on the roof; drink water mixed with jaggery before starting important work."},
        2: {"title": "Sun in House 2 (Dhan Sthana)", "result": "High eloquence, strong earning capacity, support from government. Generous host.", "upaya": "Donate coconuts, mustard oil, or religious items to temple shrines."},
        3: {"title": "Sun in House 3 (Courage and Boldness)", "result": "Dynamic valor, prosperous siblings, flourishing enterprise. High mathematical speed.", "upaya": "Maintain cordial relations with younger brothers; serve mother and elderly women."},
        4: {"title": "Sun in House 4 (Domestic Sun)", "result": "Paternal wealth, strong real estate, but requires balance between career and home.", "upaya": "Feed blind persons or support community water installations."},
        5: {"title": "Sun in House 5 (Creative Intelligence)", "result": "Brilliant intellect, successful progeny, high administrative wisdom.", "upaya": "Keep your word strictly; do not make false promises to family or associates."},
        6: {"title": "Sun in House 6 (Subduer of Enemies)", "result": "Crushes competitors, shines in legal/administrative battles. Sensitive digestion.", "upaya": "Serve pure water or milk to guests; feed monkeys or dogs on Sundays."},
        7: {"title": "Sun in House 7 (Marital Balance)", "result": "Partner is proud and honorable; marital harmony demands mutual respect and temper control.", "upaya": "Bury a piece of copper underground in an open area before initiating major business partnerships."},
        8: {"title": "Sun in House 8 (Occult and Transformation)", "result": "Deep research ability, sudden fortunes, but requires ocular and cardiovascular care.", "upaya": "Never keep open red-colored items in the south; do not indulge in illegal shortcuts."},
        9: {"title": "Sun in House 9 (Dharmic Fortune)", "result": "High paternal blessing, fortunate life trajectory, respected in public governance.", "upaya": "Use brass utensils; maintain absolute transparency with elders and mentors."},
        10: {"title": "Sun in House 10 (Executive Summit)", "result": "Reaches top corporate or governmental positions; authoritative executive command.", "upaya": "Wear a white cap or turban during critical executive negotiations; avoid black clothes on Sundays."},
        11: {"title": "Sun in House 11 (Expansive Gains)", "result": "Flourishing revenues, high social connections, prosperous elder siblings.", "upaya": "Keep a solid silver coin at home; maintain strict vegetarian habits on Sundays."},
        12: {"title": "Sun in House 12 (Bed of State)", "result": "Foreign prosperity, spiritual insight, but expenditure on public matters is high.", "upaya": "Always give water to the rising Sun every morning from a copper vessel; keep a courtyard open."}
    },
    "Moon": {
        1: {"title": "Moon in House 1 (Gentle Charm)", "result": "Attractive personality, sharp intuition, peaceful nature. Flourishes near water.", "upaya": "Take blessings from mother daily by touching her feet; keep a silver pot filled with rainwater/Ganga water."},
        2: {"title": "Moon in House 2 (Exalted Wealth)", "result": "Exquisite wealth, sweet speech, uninterrupted liquid cash flow, supportive family.", "upaya": "Receive pure silver or solid silver coins from mother as a protective token."},
        3: {"title": "Moon in House 3 (Creative Journey)", "result": "Short travels, flourishing literary and artistic talents, supportive sisters.", "upaya": "Donate white clothes or kheer (sweet rice pudding) to young girls on Mondays."},
        4: {"title": "Moon in House 4 (Ocean of Motherhood)", "result": "Supreme peace of mind, immense ancestral property, prosperous mother.", "upaya": "Do not sell milk or dairy directly for commercial profit from home; offer milk to shivalinga."},
        5: {"title": "Moon in House 5 (Pure Intuition)", "result": "Wise counselor, gifted children, creative intelligence, high moral character.", "upaya": "Never speak ill of mother or maternal relatives; avoid greed in speculative ventures."},
        6: {"title": "Moon in House 6 (Water in Pit)", "result": "Emotional vulnerability, digestive sensitivities, need to support maternal relatives.", "upaya": "Serve pure water to travelers; keep a water bowl for birds on the terrace."},
        7: {"title": "Moon in House 7 (Charming Partner)", "result": "Graceful spouse, success in retail trade, sea voyages, and public dealings.", "upaya": "Do not engage in dairy trade partnership; respect spouse unconditionally."},
        8: {"title": "Moon in House 8 (Well of Secrets)", "result": "Deep psychological insight, occult fascination, but sensitive to anxiety and cough/phlegm.", "upaya": "Never keep wells or underground water tanks in the center of the house; donate silver in running water."},
        9: {"title": "Moon in House 9 (Spiritual Wave)", "result": "High pilgrimage interest, fortune rises after travel, philosophical mind.", "upaya": "Serve fish with wheat flour balls in natural ponds on Mondays."},
        10: {"title": "Moon in House 10 (Public Popularity)", "result": "Success in public-facing careers, hospitality, travel, and administrative service.", "upaya": "Store rainwater in a glass or silver container on the rooftop; avoid alcohol strictly."},
        11: {"title": "Moon in House 11 (Flowing Gains)", "result": "Steady income, numerous loyal friends, longevity and fulfillment of desires.", "upaya": "Offer milk mixed with saffron to elders; maintain clean water storage at home."},
        12: {"title": "Moon in House 12 (Overseas Ocean)", "result": "Success abroad, peaceful retirement, vivid dreams, deep subconscious strength.", "upaya": "Never donate water or milk at night; keep a square piece of silver in your pocket."}
    },
    "Mars": {
        1: {"title": "Mars in House 1 (Fearless Knight)", "result": "Bold physical vitality, courageous initiative, leadership. Watch against head injuries and anger.", "upaya": "Apply red sandalwood paste on forehead; maintain cordiality with younger brothers."},
        2: {"title": "Mars in House 2 (Dynamic Wealth)", "result": "Earns through bold enterprise and machinery; direct and assertive speech.", "upaya": "Feed sweet jaggery flatbread (roti) to dogs or monkeys on Tuesdays."},
        3: {"title": "Mars in House 3 (Pillar of Valor)", "result": "Mars Nek (Righteous Bravery): Unshakable courage, supportive brothers, flourishing technical ventures.", "upaya": "Wear a pure silver ring on the right ring finger; help siblings in their career."},
        4: {"title": "Mars in House 4 (Fire in Hearth)", "result": "Domestic tension, high property ambition, needs patience with family members.", "upaya": "Offer sweet loaves of bread cooked on an iron griddle to stray dogs on Tuesdays."},
        5: {"title": "Mars in House 5 (Strategic Commander)", "result": "High investigative power, athletic prowess, bold investments, energetic children.", "upaya": "Keep a square piece of copper under your pillow; respect your promises."},
        6: {"title": "Mars in House 6 (Conqueror of Foes)", "result": "Overcomes all legal and operational opposition; excellent stamina and medical acumen.", "upaya": "Serve maternal uncles and distribute sweet items on festivals."},
        7: {"title": "Mars in House 7 (Manglik Calibration)", "result": "Passionate partnership; demands mutual maturity to avoid contractual friction.", "upaya": "Bury a piece of solid silver in an earthenware pot in the ground."},
        8: {"title": "Mars in House 8 (Mars Bad / Subconscious Fire)", "result": "Prone to sudden accidents or impulsive disputes; high technical/mechanical talent.", "upaya": "Bake 8 sweet rotis on a tandoor/oven and feed them to stray dogs; never consume alcohol on Tuesdays."},
        9: {"title": "Mars in House 9 (Righteous Crusader)", "result": "Fortunate father, bold defender of justice, success in defense and engineering.", "upaya": "Respect elders, preceptors, and temple authorities; offer red lentils (masoor dal) to charities."},
        10: {"title": "Mars in House 10 (Supreme General)", "result": "Mars Exalted (Kuldeepak): Rises to highest executive stature; building immense landed assets.", "upaya": "Always serve guests with sweets; keep an open, clutter-free central living room."},
        11: {"title": "Mars in House 11 (Powerhouse of Revenue)", "result": "Magnificent gains through land, engineering, contracting, and trade.", "upaya": "Wear an unheated pure red coral or copper bracelet; maintain honesty in deals."},
        12: {"title": "Mars in House 12 (Silent Warrior)", "result": "Overseas technical work, high energy expenditure, needs emotional grounding.", "upaya": "Offer jaggery and roasted chickpeas (chana) to monkeys on Tuesday mornings."}
    },
    "Mercury": {
        1: {"title": "Mercury in House 1 (Quick Witted)", "result": "Sharp intellect, youthful charm, adaptability, skill in multiple languages.", "upaya": "Wear green emerald or keep a green aventurine; avoid green colored walls in bedroom."},
        2: {"title": "Mercury in House 2 (Commercial Voice)", "result": "Persuasive salesmanship, lucrative trade, excellent accounting intelligence.", "upaya": "Do not accept electronic items for free; maintain absolute honesty in business invoices."},
        3: {"title": "Mercury in House 3 (Master of Pen)", "result": "Writing talent, advertising prowess, courageous commercial initiatives.", "upaya": "Clean teeth with alum (fitkari) daily; feed green spinach to goats or birds."},
        4: {"title": "Mercury in House 4 (Intellectual Home)", "result": "Educated mother, pleasant home library, flourishing commercial assets.", "upaya": "Avoid excessive financial speculation; donate unrefined sugar in running water."},
        5: {"title": "Mercury in House 5 (Sharp Analyst)", "result": "Gifted mathematics, diplomatic strategy, cultured children, authorial talents.", "upaya": "Wear a pure silver chain around the neck; chant the Gayatri mantra regularly."},
        6: {"title": "Mercury in House 6 (Exalted Intelligence)", "result": "Supreme analytical acumen, flawless auditing, thrives in complex technical environments.", "upaya": "Keep a solid silver ball in pocket; pierce nose and wear a silver wire for 100 days if speech hesitates."},
        7: {"title": "Mercury in House 7 (Diplomatic Trader)", "result": "Diplomatic spouse, success in trade, contracts, law, and joint commercial ventures.", "upaya": "Avoid gambling; respect your spouse and in-laws sincerely."},
        8: {"title": "Mercury in House 8 (Cryptic Mind)", "result": "Research intellect, interest in occult, astrology, and cybersecurity.", "upaya": "Bury an earthen pot filled with honey in a deserted place; avoid keeping dead clocks at home."},
        9: {"title": "Mercury in House 9 (Philosophical Scribe)", "result": "Higher studies, travel for trade, spiritual publications, respectful to traditions.", "upaya": "Clean your nose with pure water daily; wear yellow clothes on auspicious occasions."},
        10: {"title": "Mercury in House 10 (Commercial Director)", "result": "Managerial brilliance, lucrative trade in corporate consultancy and administration.", "upaya": "Avoid consumption of alcohol and non-vegetarian food; donate green vegetables on Wednesdays."},
        11: {"title": "Mercury in House 11 (Multiplier of Wealth)", "result": "Diverse income streams, prosperous network of intellectuals and traders.", "upaya": "Wear a copper coin around the neck; avoid keeping broken glass items at home."},
        12: {"title": "Mercury in House 12 (Abstract Thinker)", "result": "Deep subconscious processing, interest in foreign trade, creative visualization.", "upaya": "Wear a yellow thread or golden ring on the index finger; avoid false promises."}
    },
    "Jupiter": {
        1: {"title": "Jupiter in House 1 (Royal Sage)", "result": "Magnificent wisdom, noble character, deep social reverence, protective guardian angel.", "upaya": "Apply saffron (kesar) or turmeric tilak on the forehead and navel daily; respect elders."},
        2: {"title": "Jupiter in House 2 (Treasury of Dharma)", "result": "Enduring family fortune, eloquent speech, generous philanthropist, divine blessings.", "upaya": "Donate yellow items (chana dal, turmeric, brass) to a temple on Thursdays."},
        3: {"title": "Jupiter in House 3 (Wise Enterprise)", "result": "Supportive siblings, respected writing, philosophical ventures, high courage.", "upaya": "Serve elderly teachers and saints; wear a pure gold chain or yellow thread."},
        4: {"title": "Jupiter in House 4 (Exalted Guru)", "result": "Supreme peace, palatial residence, saintly mother, massive prosperity.", "upaya": "Respect mother; never disrespect learned persons or religious institutions."},
        5: {"title": "Jupiter in House 5 (Divine Progeny)", "result": "Cultured and brilliant children, spiritual scholarship, high administrative status.", "upaya": "Clean temple floors; do not accept unearned donations or charity from others."},
        6: {"title": "Jupiter in House 6 (Humble Sage)", "result": "Healer of disputes, quiet wisdom, overcomes rivals through ethical grace.", "upaya": "Feed jaggery and gram dal to cows on Thursdays; avoid ostentatious spiritual display."},
        7: {"title": "Jupiter in House 7 (Blessed Union)", "result": "Virtuous and noble spouse, prosperous marriage, high status in society.", "upaya": "Keep yellow marigold flowers in the home altar; avoid unnecessary arguments."},
        8: {"title": "Jupiter in House 8 (Mystic Scholar)", "result": "Profound research in ancient sciences, occult knowledge, spiritual transformation.", "upaya": "Donate yellow cloth, ghee, and books to scholars or educational trusts."},
        9: {"title": "Jupiter in House 9 (Dharmadhikari)", "result": "Supreme fortune, father is noble and long-lived, pilgrimage leader, highly respected.", "upaya": "Always follow traditional family rituals; offer water to a Peepal tree on Thursdays."},
        10: {"title": "Jupiter in House 10 (Judge of Dharma)", "result": "High judiciary or executive office, ethical leadership; avoid mixing desire with duty.", "upaya": "Clean temple premises; avoid vanity or pride in professional achievements."},
        11: {"title": "Jupiter in House 11 (Limitless Grace)", "result": "Continuous expansion of wealth, loyal noble friends, spiritual and material fulfillment.", "upaya": "Wear a pure yellow sapphire or topaz; maintain sacredness of promises."},
        12: {"title": "Jupiter in House 12 (Moksha Doot)", "result": "Spiritual liberation, generous charitable disposition, prosperity in foreign lands.", "upaya": "Keep a saffron mark on the navel; support spiritual ashrams or schools for underprivileged."}
    },
    "Venus": {
        1: {"title": "Venus in House 1 (Charming Presence)", "result": "Youthful attractiveness, artistic elegance, romantic persona, refined taste.", "upaya": "Wear clean, perfumed, uncrinkled clothes; keep your domestic environment pristine."},
        2: {"title": "Venus in House 2 (Abundance of Beauty)", "result": "Luxurious wealth, jewelry, sweet melodic voice, flourishing family life.", "upaya": "Feed cows with pure white butter, curd, or fresh green fodder regularly."},
        3: {"title": "Venus in House 3 (Artistic Hands)", "result": "Talent in performing arts, painting, fashion, gracious relations with sisters.", "upaya": "Respect all women; avoid speaking ill of females in the family."},
        4: {"title": "Venus in House 4 (Palace of Comfort)", "result": "Luxury vehicles, palatial home, loving domestic environment, affectionate mother.", "upaya": "Bury a silver coin in the floor of your house or keep a solid silver square in safe."},
        5: {"title": "Venus in House 5 (Creative Passion)", "result": "Gifted artist, romantic charm, beautiful daughters, high creative prestige.", "upaya": "Maintain sexual and marital fidelity; support the education of underprivileged girls."},
        6: {"title": "Venus in House 6 (Debilitated Calibration)", "result": "Needs emotional boundaries, health care for reproductive system/kidneys.", "upaya": "Feed white cows with fodder; give clothing to married women on Fridays."},
        7: {"title": "Venus in House 7 (Blissful Marriage)", "result": "Loving, beautiful, supportive spouse; flourishing commercial partnerships.", "upaya": "Respect your wife as the true Lakshmi of the house; donate cosmetics/bangles to women."},
        8: {"title": "Venus in House 8 (Hidden Magnetism)", "result": "Magnetic aura, unexpected inheritances, needs caution against emotional deception.", "upaya": "Donate white flowers or curd at a temple; avoid taking free cosmetics from others."},
        9: {"title": "Venus in House 9 (Fortunate Grace)", "result": "Fortune rises after marriage, long travels for culture and art, graceful lifestyle.", "upaya": "Bury a silver square in the courtyard or keep it in your locker; respect in-laws."},
        10: {"title": "Venus in House 10 (Commercial Prestige)", "result": "High earnings through fashion, media, cosmetics, luxury cars, architecture.", "upaya": "Keep your workplace tidy and aesthetically decorated; avoid arrogance."},
        11: {"title": "Venus in House 11 (Prosperity and Luxuries)", "result": "Enormous financial gains, affluent social circle, fulfillment of luxury desires.", "upaya": "Donate curd, white sweets, or rice to women on Friday evenings."},
        12: {"title": "Venus in House 12 (Exalted Bliss)", "result": "Venus Exalted (Supreme Comforts): Enjoys highest bedroom comforts, luxury travel, vast wealth.", "upaya": "Plant a white fragrant flowering plant at home; keep your commitments strictly."}
    },
    "Saturn": {
        1: {"title": "Saturn in House 1 (Stern Builder)", "result": "Serious, hardworking, slow start turning into enduring monumental achievement.", "upaya": "Serve blind or handicapped persons; apply mustard oil on hair and body on Saturdays."},
        2: {"title": "Saturn in House 2 (Solid Foundation)", "result": "Wealth built through real estate, mining, oil, construction, and patience.", "upaya": "Feed buffaloes or black dogs; avoid alcohol and tobacco strictly."},
        3: {"title": "Saturn in House 3 (Iron Resolve)", "result": "Unstoppable perseverance, independent industrialist, fearlessness in adversity.", "upaya": "Serve stray black dogs; do not keep unused iron scrap or rusty tools on the roof."},
        4: {"title": "Saturn in House 4 (Restructuring Foundation)", "result": "Requires patience in domestic life; builds substantial permanent real estate.", "upaya": "Offer milk or water to snake idols on Saturdays; feed fish with wheat balls."},
        5: {"title": "Saturn in House 5 (Disciplined Mind)", "result": "Deep research intelligence, disciplined children, success in technical fields.", "upaya": "Distribute salty snacks or roasted chickpeas to laborers; avoid gambling."},
        6: {"title": "Saturn in House 6 (Crusher of Adversity)", "result": "Supreme mastery over legal disputes, competitors, and operational bottlenecks.", "upaya": "Serve black cows or stray dogs; feed crows daily before breakfast."},
        7: {"title": "Saturn in House 7 (Exalted Architect)", "result": "Saturn Exalted (Massive Alliances): Immense corporate success, stable marriage, public power.", "upaya": "Respect your domestic and commercial partners; maintain absolute contractual integrity."},
        8: {"title": "Saturn in House 8 (Lord of Longevity)", "result": "Long life, profound crisis management, inheritance of ancient properties.", "upaya": "Pour a few drops of mustard oil into running water on Saturdays; avoid taking free iron objects."},
        9: {"title": "Saturn in House 9 (Philosophical Hermit)", "result": "Enduring wisdom, deep respect for lineage traditions, success in later life.", "upaya": "Bury an earthen pot filled with honey in a deserted spot; keep a brass bell at home."},
        10: {"title": "Saturn in House 10 (Supreme Executive)", "result": "Saturn in Own House (Simhasan): Rises to highest industrial and administrative ranks.", "upaya": "Serve elderly laborers and provide drinking water stations in public areas."},
        11: {"title": "Saturn in House 11 (Permanent Revenue)", "result": "Unfailing wealth, vast properties, longevity, commanding executive presence.", "upaya": "Pour unboiled milk around the roots of a Banyan or Peepal tree on Saturdays."},
        12: {"title": "Saturn in House 12 (Solitary Ascetic)", "result": "Spiritual detachment, overseas success, immunity from secret enemies.", "upaya": "Do not keep dark unventilated corners in the house; donate black umbrellas or blankets to the poor."}
    },
    "Rahu": {
        1: {"title": "Rahu in House 1 (Bold Innovator)", "result": "Unconventional thinker, dynamic presence, attracted to cutting-edge technology.", "upaya": "Wash head with pure raw milk or wear a solid silver chain; avoid blue clothes."},
        2: {"title": "Rahu in House 2 (Volatile Cash)", "result": "Sudden monetary windfalls, fluctuating family ties, foreign commerce.", "upaya": "Keep a solid silver ball in pocket; feed stray dogs with bread."},
        3: {"title": "Rahu in House 3 (Exalted Courage)", "result": "Fearless explorer, breakthrough tech entrepreneur, dominates rivals.", "upaya": "Wear a pure silver square; maintain cordial relations with neighbors."},
        4: {"title": "Rahu in House 4 (Stormy Hearth)", "result": "Restless domestic life, frequent relocations, success away from birthplace.", "upaya": "Bury a silver box with honey in the foundation; avoid dark clutter in the northeast."},
        5: {"title": "Rahu in House 5 (Cryptic Creator)", "result": "Speculative genius, digital media brilliance, needs patience with progeny.", "upaya": "Keep a small silver elephant in your living room; respect your mentors."},
        6: {"title": "Rahu in House 6 (Slayer of Obstacles)", "result": "Crushes enemies, triumphs in litigations, excellent in medical/technical diagnostics.", "upaya": "Keep a lead coin in pocket; feed stray black dogs on Saturday nights."},
        7: {"title": "Rahu in House 7 (Unconventional Partner)", "result": "Cross-cultural or unconventional spouse; foreign commercial contracts.", "upaya": "Bury a silver coin near a flowing river; maintain total transparency in marriage."},
        8: {"title": "Rahu in House 8 (Alchemical Depths)", "result": "Occult mastery, sudden transformations, interest in mysterious phenomena.", "upaya": "Keep 8 pieces of lead immersed in water; donate almond nuts to a temple."},
        9: {"title": "Rahu in House 9 (Unorthodox Seeker)", "result": "Questions rigid dogmas, finds truth through self-directed research, foreign travel.", "upaya": "Wear a pure saffron tilak on the forehead; respect traditional family elders."},
        10: {"title": "Rahu in House 10 (Mass Appeal)", "result": "Political charisma, media dominance, rapid corporate rise through digital platforms.", "upaya": "Wear a white cap/turban; do not accept free electricity or electronic gifts."},
        11: {"title": "Rahu in House 11 (Explosive Gains)", "result": "Massive sudden wealth, affluent network, tech industry success.", "upaya": "Drink water in a pure silver tumbler; wear a silver ring without joints."},
        12: {"title": "Rahu in House 12 (Foreign Realm)", "result": "Flourishes in foreign countries, deep subconscious dreams, high expenditure.", "upaya": "Eat meals sitting in the kitchen; avoid sleeping in rooms cluttered with broken electronics."}
    },
    "Ketu": {
        1: {"title": "Ketu in House 1 (Spiritual Seeker)", "result": "Intuitive, detached from vanity, profound insight into human nature.", "upaya": "Feed black and white spotted dogs with bread; respect family elders."},
        2: {"title": "Ketu in House 2 (Detached Treasury)", "result": "Unattached to wealth, philosophical speech, unexpected legacies.", "upaya": "Apply a saffron or turmeric tilak on the throat and forehead daily."},
        3: {"title": "Ketu in House 3 (Precision Hands)", "result": "Mastery of precision mechanics, coding, surgery, martial discipline.", "upaya": "Wear a gold ring or yellow thread on the right index finger."},
        4: {"title": "Ketu in House 4 (Spiritual Heart)", "result": "Spiritual mother, deep inner meditation, moves toward quiet surroundings.", "upaya": "Keep a pet dog at home or feed stray dogs regularly with milk and bread."},
        5: {"title": "Ketu in House 5 (Mystic Intellect)", "result": "Astrological intuition, cryptographic talent, devoted to higher philosophy.", "upaya": "Donate yellow blankets to religious ascetics or feed birds on Sundays."},
        6: {"title": "Ketu in House 6 (Exalted Healer)", "result": "Crushes hidden enemies, supreme diagnostic ability in indigenous and alternative medicine.", "upaya": "Wear a pure gold earring or gold chain; serve maternal relatives sincerely."},
        7: {"title": "Ketu in House 7 (Detached Union)", "result": "Spiritual spouse, unconventional relationship, thrives through mutual space.", "upaya": "Keep a small silver bowl filled with honey at home; avoid harsh words."},
        8: {"title": "Ketu in House 8 (Secret Mystic)", "result": "Occult knowledge, profound longevity insights, psychological acumen.", "upaya": "Feed multi-colored stray dogs; donate black and white sesame seeds to temples."},
        9: {"title": "Ketu in House 9 (Exalted Dhwaja)", "result": "Flag of Honor: High spiritual elevation, temple builder, royal fame in philosophy.", "upaya": "Wear a pure gold ornament; respect preceptors and spiritual teachers."},
        10: {"title": "Ketu in House 10 (Independent Master)", "result": "Independent profession, precision engineering, architectural consulting.", "upaya": "Keep a vessel of honey in the house; feed stray dogs on Saturday evenings."},
        11: {"title": "Ketu in House 11 (Sudden Expansion)", "result": "Unexpected financial windfalls, highly intuitive friends, spiritual accomplishments.", "upaya": "Donate black and white blankets to orphanages or leprosy homes."},
        12: {"title": "Ketu in House 12 (Gateway to Moksha)", "result": "Supreme spiritual detachment, profound meditation, peaceful sleep, final liberation.", "upaya": "Maintain high ethical purity; sponsor spiritual books or education for seekers."}
    }
}
