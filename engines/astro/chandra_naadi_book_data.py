"""
Chandra Naadi Astrology Data Reference

This module contains all astrological rules, matrices, and predictions for the Chandra Naadi engine.
This is a standalone reference data file intended for use by the analysis engine.
"""

CONJUNCTION_RULES = {
    # Sun Combinations
    frozenset({"Sun", "Moon"}): {
        "predictions": [
            "Parents live in harmony.",
            "Frequent travels for father.",
            "Prone to eye ailments.",
            "Native executes actions covertly.",
            "Generally unfruitful for Moon (loses strength near Sun)."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Sun", "Mars"}): {
        "predictions": [
            "Quits jobs abruptly.",
            "Highly prone to accidents, wounds, high BP, boils, spinal cord issues, pox, fevers.",
            "Impairs full marital happiness.",
            "Hot-tempered, adventurous, aggressive, authoritative."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Sun", "Mercury"}): {
        "predictions": [
            "Father is educated, intelligent, with commercial interests."
        ],
        "modifiers": [
            "If Mercury degree > Sun degree: High math proficiency, formal academics, intellectual prowess.",
            "If Sun degree > Mercury degree: Low formal education; employed in unrelated fields."
        ],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Sun", "Jupiter"}): {
        "predictions": [
            "Noble family, high admin skills, honorable employment, honesty, broad social respect.",
            "Leadership in temple admin or public welfare trusts."
        ],
        "modifiers": [
            "If afflicted by malefics: paternal Pitru Dosha."
        ],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Sun", "Venus"}): {
        "predictions": [
            "Father is wealthy with luxury.",
            "Support from govt officials.",
            "Radiant eyes.",
            "Affection for girl children.",
            "Artistic skills."
        ],
        "modifiers": [
            "If Sun-Venus closer than 5° (deep combustion): male native suffers depleted sperm count."
        ],
        "male_specific": [
            "If Sun-Venus closer than 5° (deep combustion): male native suffers depleted sperm count."
        ],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Sun", "Saturn"}): {
        "predictions": [
            "Son does not inherit father's legacy.",
            "Severe friction/estrangement between father and son.",
            "Superiors bully at workplace.",
            "Life oscillates rough/smooth.",
            "Deficient sperm count or very few male children."
        ],
        "modifiers": [
            "If in BOTH husband-wife charts: extreme craving for progeny but charts must NEVER be matched."
        ],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Sun", "Rahu"}): {
        "predictions": [
            "Father suffered immense hardships.",
            "Eye defects (asymmetry), heart ailments, spinal/back pain.",
            "Sudden cessation of income.",
            "Constant yearning for public recognition that evades them."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Sun", "Ketu"}): {
        "predictions": [
            "Small eyes.",
            "Father spiritually inclined, saintly.",
            "Troubles from govt authorities, misappropriation charges, penalties.",
            "Father has spinal cord defects, hip dislocation, diseased small intestine.",
            "Favorable for spiritual liberation, disastrous for domestic bliss."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },

    # Moon Combinations
    frozenset({"Moon", "Mars"}): {
        "predictions": [
            "Athletic physique, bravery, agriculture affinity, voracious eater of salty/spicy food.",
            "Acquires property and hereditary diseases from maternal side.",
            "Disputes with mother.",
            "One brother prospers, another struggles.",
            "Danger near water."
        ],
        "modifiers": [
            "If Mercury joins: female chart illicit affairs leading to secret marriage.",
            "If Venus joins: male chart secret affairs.",
            "If Moon+Mars+Mercury: native becomes heavy drunkard."
        ],
        "male_specific": [
            "If Venus joins: secret affairs."
        ],
        "female_specific": [
            "If Mercury joins: illicit affairs leading to secret marriage."
        ],
        "yoga_name": None
    },
    frozenset({"Moon", "Mercury"}): {
        "predictions": [
            "Strategic planning, counseling, vivid imagination, vivid dreams, forgetfulness, high analytical intellect.",
            "Prone to nervous breakdowns, mental tension, anxiety neurosis.",
            "Poetic/romantic but afflicted with Putra Dosha and thieving tendencies."
        ],
        "modifiers": [
            "If Mars+Venus aspect: native becomes lecherous/promiscuous."
        ],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Moon", "Jupiter"}): {
        "predictions": [
            "Oval face.",
            "Accumulates wealth for children.",
            "High moral conduct, extensive travel, remembered by society.",
            "Receives hospitality wherever they travel.",
            "Prone to allergies, substance abuse, suspicious mentality, nostalgic attachment to ancestral property, susceptible to flattery.",
            "Blessed materially, cursed domestically."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": "Gaja Kesari Yoga"
    },
    frozenset({"Moon", "Venus"}): {
        "predictions": [
            "Charming, beautiful face.",
            "Well-dressed, fond of perfumes, expensive ornaments.",
            "Adept in literature, music, fine arts.",
            "Delayed marriage for native's sister.",
            "Greedy, lustful, prone to cold diseases, extramarital affairs."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Moon", "Saturn"}): {
        "predictions": [
            "Restless, frequent relocations.",
            "Fructification of any event is doubtful till last moment — extreme obstacles initially but grand celebration after delay.",
            "Workaholic, isolated, calcium deficiency, chronic leg pain, clinical depression, inferiority complex, fault-finding."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": "Punarpoo Dosha"
    },
    frozenset({"Moon", "Rahu"}): {
        "predictions": [
            "Larger left eye.",
            "Compulsive liar, fearful, chronic paranoia of black magic.",
            "Food poisoning, insect bites, allergies, excessive sweating, loss by theft."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [
            "Menstrual irregularities, religious conversion, secret marriage."
        ],
        "yoga_name": None
    },
    frozenset({"Moon", "Ketu"}): {
        "predictions": [
            "Smaller left eye.",
            "Conflicts with mother-in-law.",
            "Mental depression, dry skin, insect bites, food poisoning, suicidal tendencies, total detachment from conjugal life, renunciation."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },

    # Mars Combinations
    frozenset({"Mars", "Mercury"}): {
        "predictions": [
            "Break in academic studies.",
            "High math/analytical acumen.",
            "Sparkling teeth.",
            "Stomach ulcers.",
            "Owns landed property."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [
            "Mars=Husband, Mercury=Lover → illicit connections, secret affairs, civil registry marriage."
        ],
        "yoga_name": None
    },
    frozenset({"Mars", "Jupiter"}): {
        "predictions": [
            "Decent character, generous, courageous commander, respected in temple affairs.",
            "Emotional, likes hot/spicy food, affectionate toward brothers."
        ],
        "modifiers": [
            "If afflicted: blood cancer, cunning personality, unhappy marriage."
        ],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Mars", "Venus"}): {
        "predictions": [
            "High albumin, excessive body hair, delayed second child.",
            "Fine real estate, multi-trade businesses.",
            "Passionate, lustful disguised as romantic."
        ],
        "modifiers": [
            "If afflicted: disastrous illicit physical indulgences."
        ],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Mars", "Saturn"}): {
        "predictions": [
            "Rebellious, warring, fanaticism.",
            "Skilled mechanical/revolutionary laborer.",
            "Prone to major accidents, surgeries, physical disfigurements.",
            "Transit query: 'Can I buy old house, used vehicle, disputed land, second-hand machinery?'"
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [
            "Severe friction with husband (accuses of laziness/passivity → separation)."
        ],
        "yoga_name": "Mandaara Yoga / Thaara Dosha"
    },
    frozenset({"Mars", "Rahu"}): {
        "predictions": [
            "Neighbor has two marriages/childless/separated.",
            "Impure blood, weak teeth, Vaastu Dosha, severe machine-related accidents."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [
            "Husband uncooperative, harsh."
        ],
        "yoga_name": None
    },
    frozenset({"Mars", "Ketu"}): {
        "predictions": [
            "Delayed marriage, marital affliction.",
            "Disputes over mortgaged properties/land/vehicles.",
            "Tailors, cable winders, carpenters, bachelors.",
            "Low BP, stomach ulcers.",
            "Worship Lord Kalabhairava for relief."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },

    # Mercury Combinations
    frozenset({"Mercury", "Jupiter"}): {
        "predictions": [
            "Intellectual scholar, author of books, dignified, impartial, authoritative orator, round face.",
            "Lends money against documents.",
            "Academic guide, consultant.",
            "Prone to jaundice."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Mercury", "Venus"}): {
        "predictions": [
            "Connoisseur of art/music.",
            "Refined dressing, polite, generous advice.",
            "Extreme weakness for fair sex."
        ],
        "modifiers": [],
        "male_specific": [
            "Knows secret art of seducing women."
        ],
        "female_specific": [],
        "yoga_name": "Madhana Gopala Yoga"
    },
    frozenset({"Mercury", "Saturn"}): {
        "predictions": [
            "Consummate cheat or constantly cheated.",
            "Vacant land trade, forged accounting, duplicate documents.",
            "Dull-headed, hermaphrodite/impotent behavior, arthritis, vatha diseases, laziness, argumentative."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Mercury", "Rahu"}): {
        "predictions": [
            "Large forehead.",
            "Severe affliction to maternal uncle.",
            "Skin diseases, itching, mental delusions, allergies, black magic fears.",
            "High intuitive oratory."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Mercury", "Ketu"}): {
        "predictions": [
            "Psychic behavior, absent-mindedness, skin ailments, illiteracy/academic breaks, tangled love affairs, delayed marriage."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },

    # Jupiter Combinations
    frozenset({"Jupiter", "Venus"}): {
        "predictions": [
            "Fair complexion, luxurious life, patron of fine arts, revered posts.",
            "Denied or severely delayed childbirth.",
            "Love marriage with mutual compatibility."
        ],
        "modifiers": [
            "If Rahu joins or planetary war in 6/8/12: marital life and progeny completely destroyed."
        ],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Jupiter", "Saturn"}): {
        "predictions": [
            "Devout, calm, spiritual, vatha constitution.",
            "Breadwinner from young age.",
            "Duty is devotion.",
            "Supports siblings unconditionally.",
            "Fond of sour foods.",
            "Prone to nervous breakdowns or paralytic attacks."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Jupiter", "Rahu"}): {
        "predictions": [
            "Academician acting contrary to traditions/family customs.",
            "Constantly embroiled in social crisis and ill fame.",
            "Frequent travels, untimely death."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": "Guru Chandal Yoga"
    },
    frozenset({"Jupiter", "Ketu"}): {
        "predictions": [
            "Birthplace has strong religious environment.",
            "Saintly, detached, barren worldly existence.",
            "Untimely death and unmerited bad reputation despite pious living."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },

    # Venus Combinations
    frozenset({"Venus", "Saturn"}): {
        "predictions": [
            "Profession deals with large cash, finance, banking, luxury merchandise.",
            "Influential, wealthy, profitable.",
            "Estranged friends rejoin automatically.",
            "Daughters well-employed."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Venus", "Rahu"}): {
        "predictions": [
            "Multiple clandestine relationships.",
            "Marital destruction.",
            "Wife is incessant chatterbox/quarrelsome.",
            "Financial volatility (sudden windfalls then crises).",
            "Cinema/TV/media/photography careers."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Venus", "Ketu"}): {
        "predictions": [
            "Frequent breakdown of household electronics.",
            "Wife sickly/domineering/divorced.",
            "Wife files police cases/dowry harassment.",
            "Halting of profession.",
            "Suicidal thoughts."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },

    # Saturn Combinations
    frozenset({"Saturn", "Rahu"}): {
        "predictions": [
            "Lifetime intense struggle financially and family.",
            "Affected by black magic.",
            "Severe career crises, total stoppage.",
            "Inclination toward unlawful activities, menial labor, unceremonious marriages."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    },
    frozenset({"Saturn", "Ketu"}): {
        "predictions": [
            "Deeply depressed, spiritual detachment.",
            "Jobs in machinery, painting, tailoring, weaving.",
            "Universally ditched/defrauded by business partners.",
            "Career halts, suicidal tendencies."
        ],
        "modifiers": [],
        "male_specific": [],
        "female_specific": [],
        "yoga_name": None
    }
}

# Special multi-planet note:
# - Saturn+Moon in 12th Bhava: Strong affinity for hotel, baking, catering, provision store business. Must NEVER run individually (compulsory partnership), otherwise total bankruptcy.


RASHI_KARAKATHWAS = {
    "Fire": {
        "signs": ["Aries", "Leo", "Sagittarius"],
        "places": ["Mountains", "head offices", "weapon stores", "forests", "halls of fame", "govt docs", "war fields", "rocky areas", "capital cities"],
        "body_parts": ["Head", "brain", "heart", "thigh"]
    },
    "Earth": {
        "signs": ["Taurus", "Virgo", "Capricorn"],
        "places": ["Cattle sheds", "schools/colleges", "slushy land", "farmlands", "lover's rendezvous", "business centers", "ATMs", "floral gardens", "industrial zones"],
        "body_parts": ["Face", "eyes", "neck", "stomach", "genital organs", "hip"]
    },
    "Air": {
        "signs": ["Gemini", "Libra", "Aquarius"],
        "places": ["Middle of road", "marketplaces", "hidden rooms", "guest houses", "courts", "dark corners", "trade centers", "cinema halls", "liquor shops", "gambling dens"],
        "body_parts": ["Shoulders", "arms", "lower abdomen", "pelvic bones", "knees", "feet"]
    },
    "Water": {
        "signs": ["Cancer", "Scorpio", "Pisces"],
        "places": ["Ladies clubs", "public wells", "pools", "beaches", "holy rivers", "valleys", "riverbanks", "low-lying areas", "tunnels", "water bodies"],
        "body_parts": ["Chest", "breasts", "lungs", "kidneys", "urinary system", "uterus", "anus", "varicose veins", "feet/toes"]
    }
}


PLANET_DISEASE_MAP = {
    "Sun": ["Eye diseases", "spinal cord", "infections", "mental delusions", "sperm depletion", "heart/brain bone failures"],
    "Moon": ["Eyes", "blood circulation", "body fluid sacs (uterus/scrotum/urinary bladder/abdominal sacs)", "mental disorders"],
    "Mars": ["Blood", "lips", "nails", "teeth", "spleen", "vitality", "eyelids", "sternum", "pelvic bone"],
    "Mercury": ["All skin disorders", "stammering", "nervous system", "lung disorders", "touch sense impairment", "fingers", "tongue"],
    "Jupiter": ["Large boneless organs", "liver", "pancreas", "cell destruction", "ears", "fat accumulation", "childlessness", "endocrine glands"],
    "Venus": ["Cheeks", "complexion", "leprosy", "hormonal imbalances", "diabetes", "kidneys", "skin pigmentation loss"],
    "Saturn": ["Chronic karmic diseases", "leg disorders", "varicose veins", "mucus/cold infections", "knee pain", "toxicity", "tooth decay", "kidney stones"],
    "Rahu": ["Surgeries", "modern machinery diagnostics", "colon", "fear/paranoia", "body aches", "itching", "chemotherapy", "undetectable allergies"],
    "Ketu": ["Surgeries", "lung allergies", "loneliness-induced mental illness", "Varma therapies", "undetectable ailments"]
}


MARS_TRANSIT_BHAVA = {
    1: "Temporary efforts maintaining physical body; temporary harsh/violent behavior with family. If natal Mars also in 1st, behavior is permanent.",
    2: "Sharp temperamental speech; harsh tone with family; disputes about money/food.",
    3: "Interest in short travel; quick decisions to sell properties; getting cheated by lending money; major accident risk; dynamic business growth efforts.",
    4: "Vehicle purchase/repairs, real estate, mother's health, home modification queries.",
    5: "Child welfare/temperament issues; speculative investments; sports/physical training.",
    6: "Immediate health complications (blood disorders, BP, kidney/rectum/uterine); medical treatments; loan applications.",
    7: "Marital arguments; friction with spouse/business partners; marriage negotiations activated.",
    8: "Fear of crisis, accident, surgeries, sudden energy loss, disputes over ancestral properties.",
    9: "Conflicts with father/preceptor; journeys related to ancestral property or religious shrines.",
    10: "Intense work pressure; technical/engineering changes; authoritative professional actions.",
    11: "Financial gains through machinery/land/siblings; sudden profits from property disposal.",
    12: "Expenditure on hospital bills/surgeries; loss of land; travel to remote/foreign places."
}


BHAVA_QUERY_MAP = {
    1: {"domain": "Self", "significations": ["Health", "personality", "longevity", "vitality", "self-effort", "social honor", "missing person alive/dead", "body marks"]},
    2: {"domain": "Wealth", "significations": ["Liquid cash", "speech (truth/lies, sweet/harsh)", "family additions", "eye problems", "food habits", "secondary marriage", "clearing dues"]},
    3: {"domain": "Courage & Siblings", "significations": ["Agreements", "contracts", "cheque clearance/bouncing", "gold pledging", "mobile phones", "younger siblings", "short trips", "transfers", "retail business", "courage"]},
    4: {"domain": "Comforts & Mother", "significations": ["Formal schooling/college", "study branch", "vehicle purchase/accident", "agriculture", "landed assets", "house construction/type", "mother's health"]},
    5: {"domain": "Progeny & Intellect", "significations": ["Progeny", "child gender", "Putra Dosha", "mantra chanting", "speculative markets", "ancestral home", "mental composure", "romantic relationships"]},
    6: {"domain": "Disease, Debt, Enemies", "significations": ["Timing/nature of illness", "debts/loans", "service employment", "legal battles", "divorce litigations", "domestic animals", "maternal uncle"]},
    7: {"domain": "Spouse & Partnerships", "significations": ["Marriage timing", "spouse description/direction", "love vs arranged marriage", "business partnerships", "open enemies", "diplomacy"]},
    8: {"domain": "Longevity & Obstacles", "significations": ["Wills", "legacies", "unearned wealth", "dowry", "chronic fatal diseases", "surgeries", "suicide", "accidents", "hidden treasures", "longevity"]},
    9: {"domain": "Dharma & Father", "significations": ["Father", "higher research", "pilgrimage", "Guru", "second marriage", "foreign assignments", "ancestral rituals", "luck"]},
    10: {"domain": "Profession & Karma", "significations": ["Profession", "job change (if Moon connected)", "promotions", "government authority", "parental death ceremonies", "boss dynamics"]},
    11: {"domain": "Gains & Elder Siblings", "significations": ["Realization of ambitions", "elder siblings", "recovery from chronic disease", "extramarital connections", "multiple marriages (3rd+)", "election victory"]},
    12: {"domain": "Losses & Moksha", "significations": ["Hospitalization", "overseas settlement", "bedroom pleasures", "amputations/fractures", "vision loss", "financial insolvency", "Moksha"]}
}


DEBT_MATRIX = {
    frozenset({"Sun", "Ketu"}): ["Debts for father", "heart/eye/spine treatments", "govt penalties", "son's welfare", "political aspirations"],
    frozenset({"Sun", "Rahu"}): ["Debts for father", "heart/eye/spine treatments", "govt penalties", "son's welfare", "political aspirations"],
    frozenset({"Moon", "Ketu"}): ["Debts for mother", "personal health crises", "court trials", "family maintenance", "repaying others' debts"],
    frozenset({"Moon", "Rahu"}): ["Debts for mother", "personal health crises", "court trials", "family maintenance", "repaying others' debts"],
    frozenset({"Mars", "Ketu"}): ["Debts for house building", "land purchase", "vehicles", "helping brother/husband/brother-in-law", "buying machinery"],
    frozenset({"Mars", "Rahu"}): ["Debts for house building", "land purchase", "vehicles", "helping brother/husband/brother-in-law", "buying machinery"],
    frozenset({"Mercury", "Ketu"}): ["Debts for higher education", "bank loans", "uncle/friends", "partnership investments", "land registration", "younger sister"],
    frozenset({"Mercury", "Rahu"}): ["Debts for higher education", "bank loans", "uncle/friends", "partnership investments", "land registration", "younger sister"],
    frozenset({"Jupiter", "Ketu"}): ["Debts to maintain social dignity", "IVF/childbirth", "running business investment", "honoring promises", "child welfare"],
    frozenset({"Jupiter", "Rahu"}): ["Debts to maintain social dignity", "IVF/childbirth", "running business investment", "honoring promises", "child welfare"],
    frozenset({"Venus", "Ketu"}): ["Debts for luxury goods", "sisters", "marriage expenses", "wife/in-laws", "luxury cars", "defending wife's lawsuits"],
    frozenset({"Venus", "Rahu"}): ["Debts for luxury goods", "sisters", "marriage expenses", "wife/in-laws", "luxury cars", "defending wife's lawsuits"],
    frozenset({"Saturn", "Ketu"}): ["Debts for business/employment", "income-less household", "rectifying ancestral doshas", "family deity temple works", "chronic karmic disease treatments", "WARNING: Native must NEVER take leadership in rectifying ancestral/temple problems → catastrophic lifetime debts."],
    frozenset({"Saturn", "Rahu"}): ["Debts for business/employment", "income-less household", "rectifying ancestral doshas", "family deity temple works", "chronic karmic disease treatments", "WARNING: Native must NEVER take leadership in rectifying ancestral/temple problems → catastrophic lifetime debts."],
    frozenset({"Maandi", "Ketu"}): ["Debts leading to fatal crisis", "absconding from town", "suicide attempt due to lender harassment"],
    frozenset({"Maandi", "Rahu"}): ["Debts leading to fatal crisis", "absconding from town", "suicide attempt due to lender harassment"],
    frozenset({"6thLord", "Ketu"}): ["Debts from faulty executive/management decisions"],
    frozenset({"6thLord", "Rahu"}): ["Debts from faulty executive/management decisions"]
}


MAANDI_WEEKDAY_CONSTANTS = {
    "Sunday": {"day": 156.0, "night": 240.0},
    "Monday": {"day": 132.0, "night": 216.0},
    "Tuesday": {"day": 108.0, "night": 192.0},
    "Wednesday": {"day": 84.0, "night": 336.0},
    "Thursday": {"day": 60.0, "night": 312.0},
    "Friday": {"day": 36.0, "night": 288.0},
    "Saturday": {"day": 12.0, "night": 264.0}
}


TRANSIT_SATURN_EFFECTS = {
    "Sun": {
        "effect": "Workers/laborers demand work from executives.",
        "warning": "If Saturn combusts Sun: subordinate caught by inspectors. If transit Sun over natal Saturn: seniors harass workers."
    },
    "Moon": {
        "effect": "Restless urge to change jobs. High motivation to start hotel/restaurant/catering/food/grocery trade."
    },
    "Mars": {
        "effect": "Severe business stagnation from lack of machinery, factory land disputes, machine breakdowns, labor strikes."
    },
    "Mercury": {
        "effect": "Business planning, bank loan applications, joint ventures. Profits multiply through partners.",
        "warning": "WARNING: Excessive capital investment leads to being defrauded."
    },
    "Jupiter": {
        "effect": "Heavy workload. Expanding commercial capacity using available cash flow."
    },
    "Venus": {
        "effect": "Substantial financial gains, lucrative turnover, active patronage from women."
    },
    "Saturn": {
        "effect": "Strenuous self-driven efforts to stabilize and expand business."
    },
    "Rahu": {
        "effect": "Incomprehensible business obstacles, unexpected enemies, partnership rupture, sudden losses, tax/legal lawsuits, enterprise relocation."
    },
    "Ketu": {
        "effect": "Same as Rahu effects."
    }
}


YOGA_DEFINITIONS = [
    {
        "name": "Parivarthana Yoga",
        "planets": "Two planets exchange houses",
        "condition": "Exchange of houses between two planets",
        "results": "Results undergo complete inversion (first good then bad, or vice versa). Houses NOT involved get disrupted. Planets in non-exchange bhavas give malefic results during dasha.",
        "activation_rule": "Activated ONLY when transit planet travels over/aspects the exchanged natal planet."
    },
    {
        "name": "Gaja Kesari Yoga",
        "planets": "Moon, Jupiter",
        "condition": "Moon conjunct/aspecting Jupiter",
        "results": "Wealth for progeny, lasting legacy, food/honors. But mental restlessness, allergy, poor domestic satisfaction."
    },
    {
        "name": "Madhana Gopala Yoga",
        "planets": "Mercury, Venus",
        "condition": "Mercury conjunct Venus",
        "results": "Aesthetic elegance, master of music/arts, charming speech, weakness for opposite sex."
    },
    {
        "name": "Mandaara Yoga",
        "planets": "Mars, Saturn",
        "condition": "Mars conjunct Saturn",
        "results": "Fanatic, rebellious mechanical worker. Limb fractures, surgical amputations, marital hostility."
    },
    {
        "name": "Thaara Dosha",
        "planets": "Mars, Saturn",
        "condition": "Mars+Saturn conjunction in natal chart",
        "results": "Mistakes early in marriage treated as crimes later.",
        "activation_rule": "Remedy: ignore mistakes privately, no divorce if kept private. If exposed to courts → permanent separation."
    }
]


MARRIAGE_SCENARIOS = {
    "male": [
        {"scenario": "Mercury strong + Venus strong", "description": "Girlfriend noble, post-marriage blissful."},
        {"scenario": "Mercury strong + Venus weak", "description": "Girlfriend pleasant during dating, becomes intolerable quarrelsome wife after marriage."},
        {"scenario": "Mercury weak + Venus strong", "description": "Courtship troublesome and sour, post-marriage wonderful."},
        {"scenario": "Mercury weak + Venus weak", "description": "Both lover and wife vicious, life accompanied solely by toxic people."}
    ],
    "female": [
        {"scenario": "Mercury strong + Mars strong", "description": "Boyfriend noble, post-marriage blissful."},
        {"scenario": "Mercury strong + Mars weak", "description": "Boyfriend charming like a God during dating, turns abusive cruel husband after marriage."},
        {"scenario": "Mercury weak + Mars strong", "description": "Dating rocky/unpleasant, post-marriage stable and prosperous."},
        {"scenario": "Mercury weak + Mars weak", "description": "Both boyfriend and husband abusive, marriage is a nightmare."}
    ]
}


CHILDBIRTH_RULES = [
    {
        "rule_id": "IVF_SUCCESS",
        "condition": "Natal Jupiter+Rahu connected with transit Jupiter+Rahu",
        "prediction": "Success. Not connected → failure, follow natural medication."
    },
    {
        "rule_id": "SPERM_MOTILITY_BLOCK",
        "condition": "Natal Jupiter conjunct Saturn + transit Jupiter over natal Saturn",
        "prediction": "Sperm can't swim. When transit Jupiter moves ahead leaving Saturn → motility increases, pregnancy occurs."
    },
    {
        "rule_id": "FETAL_SURVIVAL",
        "condition": "Transit Jupiter moved completely away from natal Saturn degree",
        "prediction": "Embryo 100% safe, healthy child."
    },
    {
        "rule_id": "BIRTH_WEIGHT",
        "condition": "Natal Jupiter+Ketu (significantly reduced), Transit Jupiter+Rahu (heavy), Transit Jupiter+Ketu (drastically decreased)",
        "prediction": "Affects birth weight as specified."
    },
    {
        "rule_id": "CHILDREN_BITTERNESS",
        "condition": "Saturn in trine to natal Jupiter",
        "prediction": "Children experience struggles ages 24-36 (delayed marriage, separation, childlessness). Give children complete freedom."
    }
]


DEATH_RULES = [
    {
        "rule_id": "PRIMARY_INDICATORS",
        "condition": "Any TWO connecting among: 8th Lord, 3rd Lord (8th from 8th), Maandi/Gulika indicates death. Any THREE among 2/7/8/11 lords in dasha-bhukti causes death.",
        "prediction": "Indicates death."
    },
    {
        "rule_id": "RULE_1",
        "condition": "Transit Moon over natal Maandi",
        "prediction": "Death event."
    },
    {
        "rule_id": "RULE_2",
        "condition": "Transit Maandi over natal Moon",
        "prediction": "Death event."
    },
    {
        "rule_id": "RULE_3",
        "condition": "Transit Moon very close to natal Maandi degree",
        "prediction": "Imminent fatal crisis."
    },
    {
        "rule_id": "RULE_4",
        "condition": "Transit Moon crossing and moving away from natal Maandi",
        "prediction": "Safe zone entered."
    },
    {
        "rule_id": "RULE_5",
        "condition": "The natal planet pinpointing client query transiting over natal Maandi",
        "prediction": "Death crisis before answer reaches them."
    },
    {
        "rule_id": "RULE_6",
        "condition": "A planet transiting over natal Maandi",
        "prediction": "Delivers death message concerning that planet's signified relative (Venus=aunt/wife, Sun=father, Jupiter=guru/elder). If Maraka dasha active → actual death. If non-Maraka → only news."
    }
]


REMEDIES = [
    {
        "condition": "Putra Dosha/Jupiter afflicted by Saturn/Ketu/Rahu",
        "remedy": "Worship Kula Devatha and Naga Devatha. If heavily obstructed, sponsor/adopt underprivileged child. For female obesity blocking conception (Jupiter+Ketu): weight reduction + medical fertility treatment."
    },
    {
        "condition": "Mars+Ketu afflictions (marital delay, legal battles)",
        "remedy": "Devotion to Lord Kalabhairava."
    },
    {
        "condition": "Saturn aspecting Sun in Pisces from Capricorn",
        "remedy": "Worship Goddess Kaali of the Cremation Ground."
    },
    {
        "condition": "Thaara Dosha (Mars+Saturn in marriage)",
        "remedy": "Behavioral — neither partner must publicly expose small marital errors. Overlook mistakes privately."
    },
    {
        "condition": "Aquarius/Saturn-Mars desire control (debt prevention)",
        "remedy": "Restrain fantasies of amassing real estate on borrowed capital. Contentment is sole remedy."
    },
    {
        "condition": "Medical astrological adherence (6th house/Sun/Moon/Mars afflicted without Rahu)",
        "remedy": "Strict medical prescription, not magical rituals."
    }
]


SPECIAL_RULES = [
    {
        "condition": "Retrograde planets",
        "prediction": "Adamant nature. Creates fracture in results, severe heartburns. Native refuses advice. Retrograde NOT afflicted by Rahu/Ketu. Only Time can change results. When turns direct: stuck matters suddenly materialize."
    },
    {
        "condition": "Empty sign between two planets",
        "prediction": "Adverse effect continues unabated from Rahu to Ketu across empty signs until Moon leaves Ketu. Benefic transit intervening mitigates suffering."
    },
    {
        "condition": "Planet alone in sign",
        "prediction": "Dispositor operates in background, injecting its karakathwas."
    },
    {
        "condition": "Saturn in Aquarius + Mars aspecting",
        "prediction": "Massive inflation of wild fantasies/ambitions/greed for land/buildings/machinery. Anyone flattering = friend, anyone cautioning = enemy. Leads to gigantic loans, disastrous litigation."
    },
    {
        "condition": "Scorpio sign predisposition",
        "prediction": "Severe disorders in rectum, kidneys, uterus."
    },
    {
        "condition": "10th lord in 6th",
        "prediction": "Disease is strictly karmic. If 10th lord is Sun: hereditary paternal disease."
    },
    {
        "condition": "6th lord in 8th / 8th lord in 6th",
        "prediction": "Disease causes death or death-equivalent agony."
    },
    {
        "condition": "6th lord in 12th / 12th lord in 6th",
        "prediction": "Compulsory hospitalization."
    },
    {
        "condition": "Jupiter placement vs aspect paradox",
        "prediction": "Placement DECREASES disease intensity. Aspect INCREASES/expands disease intensity."
    },
    {
        "condition": "Sun+Jupiter close conjunction",
        "prediction": "Predisposition to cancer, epilepsy, severe skin infections, severe mental illness. Transit Rahu crossing Sun+Jupiter degree → permanent eradication through medical care."
    },
    {
        "condition": "Surgical intervention",
        "prediction": "Transit Moon contacts natal Mars+Venus. If Rahu NOT involved → no surgery, cured by medicine. If Rahu connected → surgery compulsory."
    },
    {
        "condition": "Rahu in 7th + 7th lord debilitated in 3rd",
        "prediction": "Husband inflicts knife injuries/domestic abuse, native attempts suicide repeatedly."
    },
    {
        "condition": "Business renovation",
        "prediction": "Transit Moon heading toward Rahu/Ketu + dasha lords unconnected → DON'T renovate. Transit Moon contacts natal Moon then touches benefic Jupiter/Venus → renovation yields spectacular growth."
    }
]
