"""
Rahu & Ketu Nodal Astrology - Rule Data Reference
This module serves as a reference data file for the nodal analysis engine.
"""

RAHU_KETU_NATURE = {
    "rahu": {
        "direction": "South-West",
        "element": "Air (Vayu)",
        "form": "Head / Large / Scissor (Cuts/Separates)",
        "dasha_span": 18,
        "core_nature": "Eroticism, Material Craving, Illusion, Rude",
        "action_mode": "Illegal, Unethical, Fake, Crime, Fluctuating",
        "trouble_type": "Gives active trouble/disruption before events",
        "scale": "Macro/Bigger Level Distress",
        "physical_sign": "Black patches on skin, Beard, Canine teeth",
        "speech": "Chatty, loud, boasting",
        "grains_flowers": "Black Urad Dal / Blue Orchid Flower",
        "deity": "Goddess Durga, Mahakali, Deities without human head",
        "temple": "Thirunageswaram (Tamil Nadu)",
        "professions": [
            "Shadow work", "photography", "cinematography", "media", "IT", 
            "aerospace", "electronics/electrical repairs", "watch/TV repair", 
            "black magic/sorcery", "pharmacology", "skin doctors", 
            "artificial organ manufacture", "IVF/insemination clinics", 
            "plastic/PVC goods", "tailoring/scissors", "scrap recycling", 
            "lathe/quarry", "pawn brokering", "smuggling", "narcotics"
        ],
        "places": [
            "Dark bunkers", "deep scary pits", "narrow lanes", "platform edges", 
            "underground drainage", "bushes/shrubs"
        ],
        "relatives": "Grandfathers on both sides",
    },
    "ketu": {
        "direction": "North-East",
        "element": "Fire (Agni)",
        "form": "Tail / Small / Needle (Stitches/Ties)",
        "dasha_span": 7,
        "core_nature": "Wisdom (Gnana), Asceticism, Renunciation, Polite",
        "action_mode": "Legal, Ethical, Real, Penalty/Justice, Straightforward",
        "trouble_type": "Gives litigation/arbitration/separation after events",
        "scale": "Micro/Small Level Distress",
        "physical_sign": "Red patches on skin, Moustache, Incisor teeth",
        "speech": "Silent, brief, cutting short conversation",
        "grains_flowers": "Barnyard Millet / Red Oleander (Arali) Flower",
        "deity": "Lord Ganesha, Hanuman, Deities with tails / Bachelor gods",
        "temple": "Srikalahasti (Andhra Pradesh)",
        "professions": [
            "Law", "judiciary", "courts", "arbitration", "mediation", 
            "indigenous medicine/Ayurveda", "yoga/meditation centres", 
            "astrology", "priesthood/temple service", "weaving", 
            "tailoring/knitting", "wiring/winding", "typists", "surgeons", 
            "veterinary medicine", "security forces", "poison treatment"
        ],
        "places": [
            "Courts", "arbitration halls", "bar council", "one-way streets", 
            "narrow lanes", "thatched sheds", "platform stalls"
        ],
        "relatives": "Grandmothers on both sides",
    },
}

FUNDAMENTAL_RULES = [
    {
        "rule_id": "FR_1",
        "title": "No exaltation/debilitation",
        "description": "Rahu and Ketu do NOT have exaltation, debilitation, or own houses. They reflect the house/sign they occupy and the star they're posited on."
    },
    {
        "rule_id": "FR_2",
        "title": "Control not Aspect",
        "description": "Rahu/Ketu do NOT have traditional Dristi (aspects). They exercise CONTROL over 1st, 3rd, and 11th houses from their placement. Control constrains action to karmic parameters."
    },
    {
        "rule_id": "FR_3",
        "title": "Permanent Retrograde",
        "description": "Rahu/Ketu are permanent retrograde planets. They do NOT harm other retrograde planets; they welcome and strengthen them. Direct-moving planets travel head-on towards Nodes causing clashes."
    },
    {
        "rule_id": "FR_4",
        "title": "Orb of Influence",
        "description": "Karmic force begins 21-22 degrees prior to exact conjunction."
    },
    {
        "rule_id": "FR_5",
        "title": "Approaching vs Separating",
        "description": "Planet moving TOWARDS Rahu/Ketu = severe immediate affliction. Planet already CROSSED Rahu/Ketu = delayed, reduced affliction."
    },
    {
        "rule_id": "FR_6",
        "title": "Karmic Trinity",
        "description": "Ketu = previous birth karma (seed), Rahu = consequence/execution in present life, Saturn = duration/nature of suffering."
    }
]

RAHU_IN_SIGNS = {
    "Aries": "Frequent suicidal ideation; interest in martial arts, weapons, defense. Indecisive due to ancestral traditions. Friction with life partner.",
    "Taurus": "Extreme uncompromising drive for financial status. Runs family under tight control and hard struggle.",
    "Gemini": "Craves luxury/prestige but faces frequent failures. Attracted to music/media. Surrounded by fake relatives. Success in advertising/public media.",
    "Cancer": "Tiresome lifestyle, detached saint-like existence. Works for others, takes leftovers. Deep emotional disappointments. High interest in occult/Vedas/yoga. Elevated sexual cravings alongside asceticism. Expenses before income.",
    "Leo": "Highly strategic, conquers enemies, reaches top positions. Indomitable in debates/litigation. Loses initial assets to gain massive later wealth. Expert financial manager.",
    "Virgo": "Good looking, independent thinker, sharp in statistics/auditing. Ensures love marriage. Vacant land boundary disputes. High financial drainage via mortgage. Speculation losses.",
    "Libra": "Severe domestic disturbances, more than one marriage. Court cases, chronic health issues. Persistent professional errors. Lower earner in family. Extreme wealth drive.",
    "Scorpio": "Highly virulent/poisonous placement. Severe karmic distress to native or intimate partner. Worst affected person in lineage. Constant fight against harsh circumstances.",
    "Sagittarius": "Strives to protect joint family prestige. Disturbs equally as it grants immense prosperity. Children may suffer physical/mental deformities.",
    "Capricorn": "Spiritual wisdom (Gnana), forces detachment from domestic life. Supports only one side: pure family life OR complete spiritual distance. Interest in astrology/occult.",
    "Aquarius": "Subdues powerful rivals, forces opponents to bow. Strange/controversial victory. Respiratory troubles, lung disorders, colon infections. Relentless fault-finding.",
    "Pisces": "Enormously powerful Node. Minor problems blow up into gigantic crises. Vast talents but cannot utilize them. Loss of ancestral links. Easily cheated by close friends."
}

KETU_IN_SIGNS = {
    "Aries": "Physical wounds, impulsive actions leading to court disputes, lack of domestic peace.",
    "Taurus": "Severe family dispute over ancestral wealth, dental/speech ailments, detachment from savings.",
    "Gemini": "Complex love relations, communication/document disputes, breathing/nerve weakness, renunciation through inquiry.",
    "Cancer": "Deep emotional turbulence, mother's chronic illness, property litigations near water, surgical interventions chest/breast.",
    "Leo": "Conflict with government/authorities, paternal property disputes, ascetic leanings, spiritual leadership.",
    "Virgo": "Intestinal/digestive ailments, litigation with maternal uncles, excellence in legal/auditing, nervous complaints.",
    "Libra": "Severe marital friction, legal battles in partnerships, kidney/urinary tract sensitivities, ascetic mindset towards luxury.",
    "Scorpio": "Occult mastery, chronic undiagnosed reproductive/rectal diseases, sudden financial ups/downs, deep spiritual transformation.",
    "Sagittarius": "High spiritual attainment, temple building, pilgrimage, detachment from father, mastery of ancient scriptures.",
    "Capricorn": "Knee/joint stiffness, unsteady career unless law/medicine/spirituality, service without desire for fame.",
    "Aquarius": "Solitary life, unconventional philosophy, detachment from elder siblings, neurological sensitivities.",
    "Pisces": "Final human incarnation if in 12th house; profound detachment, foreign residence, hospital/charity connection."
}

RAHU_KETU_IN_HOUSES = {
    1: {
        "rahu": "Isolated life, infatuation with married persons, criminal/unethical tendencies, forced cohabitation. Child/native raised by foster parents/grandparents; childhood in hostels or late life in old-age homes.",
        "ketu": "Physical weakness, introversion, highly spiritual, head/migraine problems."
    },
    2: {
        "rahu": "Financial deficit despite good earnings; divorce/separation via family courts during Rahu Dasha; extra-marital affairs; mortgage business; inability to retain family wealth.",
        "ketu": "Financial deficit despite good earnings; divorce/separation via family courts during Rahu Dasha; extra-marital affairs; mortgage business; inability to retain family wealth."
    },
    3: {
        "rahu": "Frustration in initiatives; delay in crucial information; constant friction/legal disputes with siblings. Rahu gives serious illness in early childhood. Suppresses sexual desire when Kalathra planets connect.",
        "ketu": "Frustration in initiatives; delay in crucial information; constant friction/legal disputes with siblings. Suppresses sexual desire when Kalathra planets connect."
    },
    4: {
        "rahu": "Sufferings to mother; ancestral real estate boundary disputes, encumbrances, document flaws; early education interruptions; moral suspicions about native.",
        "ketu": "Sufferings to mother; ancestral real estate boundary disputes, encumbrances, document flaws; early education interruptions; moral suspicions about native."
    },
    5: {
        "rahu": "Prime cause for Poorvika Dosha (ancestral curse), Puthra Dosha (childlessness), Puthra Sogam (mental agony from children); uterine disorders in women; progressive loss of ancestral estate.",
        "ketu": "Prime cause for Poorvika Dosha (ancestral curse), Puthra Dosha (childlessness), Puthra Sogam (mental agony from children); uterine disorders in women; progressive loss of ancestral estate."
    },
    6: {
        "rahu": "Conquers open enemies; causes skin diseases, poisonous bites, indigestion, gastritis. If debts occur, native absconds temporarily. Tough employee or demanding boss.",
        "ketu": "Conquers open enemies; causes skin diseases, poisonous bites, indigestion, gastritis. If debts occur, native absconds temporarily. Tough employee or demanding boss."
    },
    7: {
        "rahu": "Severe marital disharmony leading to court cases/separation; excessive/perverted sexual urges; accidents to spouse/business associates; delayed social recognition.",
        "ketu": "Severe marital disharmony leading to court cases/separation; excessive/perverted sexual urges; accidents to spouse/business associates; delayed social recognition."
    },
    8: {
        "rahu": "Sudden unpredictable fortunes alternating with catastrophic downfalls; secret theft/disappearance; accidents; image tarnished by rumors. If greedy, extreme torment.",
        "ketu": "Sudden unpredictable fortunes alternating with catastrophic downfalls; secret theft/disappearance; accidents; image tarnished by rumors. If greedy, extreme torment."
    },
    9: {
        "rahu": "Heavy affliction to father; inter-caste/inter-religious marriage; atheistic/rebellious religious views; settlement in distant/foreign lands but blocks visits to native place/family deity.",
        "ketu": "Heavy affliction to father; inter-caste/inter-religious marriage; atheistic/rebellious religious views; settlement in distant/foreign lands but blocks visits to native place/family deity."
    },
    10: {
        "rahu": "Interest in mysticism/sorcery; poverty if 10th lord debilitated with no planets in Node stars; daily commodity trading; good wealth during Dasha-Bhukti but transit instability.",
        "ketu": "Interest in mysticism/sorcery; poverty if 10th lord debilitated with no planets in Node stars; daily commodity trading; good wealth during Dasha-Bhukti but transit instability."
    },
    11: {
        "rahu": "Elder siblings hide income, break joint families; partners commit embezzlement; blocks beneficial results after age 18; profits enjoyed by ungrateful dependents.",
        "ketu": "Elder siblings hide income, break joint families; partners commit embezzlement; blocks beneficial results after age 18; profits enjoyed by ungrateful dependents."
    },
    12: {
        "rahu": "Uncontrolled expenditure before income; diseases treated without diagnosis; severe allergies; family separation during Dasha/Bhukti; lack of peace from sons/daughters-in-law.",
        "ketu": "Uncontrolled expenditure before income; diseases treated without diagnosis; severe allergies; family separation during Dasha/Bhukti; lack of peace from sons/daughters-in-law. Ketu in 12th = final human birth."
    }
}

RAHU_CONJUNCTIONS = {
    "Sun": {
        "predictions": [
            "Severe hardship to father",
            "Destruction/heavy reduction of ancestral patrimony",
            "Father forced to live in another state/country, followed by native",
            "Prevents family elders from gathering for auspicious functions",
            "Political fanaticism (works tirelessly for a movement)",
            "Male fertility defects (low sperm count/motility)",
            "Gaps between children",
            "Fire/weapon wounds",
            "Eye, spine, and gastritis issues",
            "Vulnerable to false bribery cases and misuse of governmental authority"
        ],
        "medical": []
    },
    "Moon": {
        "predictions": [
            "Severe chronic mental depression, bipolar mood swings, hallucinations",
            "Lying habit to escape blame, fake persona",
            "Extramarital connections, more than one marriage",
            "Highly creative in cinema, media, photography, theater"
        ],
        "medical": [
            "Intestinal/digestive troubles",
            "Severe gastritis",
            "Food poisoning",
            "Skin allergies",
            "Uterine complications in women (diagnosed only via laparoscopy/endoscopy)"
        ]
    },
    "Mars": {
        "predictions": [
            "Rigid extreme perfectionism and fault-finding",
            "Expects absolute adherence to promises",
            "Outbursts of uncontrollable rage pushing others to depression/suicide",
            "Vasthu Dosha in owned properties",
            "Boundary/title disputes, loss of ancestral lands",
            "Nausea/vomiting in family children during travel (fear psychosis inherited by fetus)",
            "Less than 5% of women with this combination are happily married unless partner is sickly",
            "Supports competitive athletics"
        ],
        "medical": [
            "Blood contamination",
            "Genetic disorders",
            "Acute calcium deficiency",
            "Bone/teeth fractures"
        ]
    },
    "Mercury": {
        "predictions": [
            "Disruption in formal education",
            "Works in jobs unrelated to qualification",
            "Financial betrayal by maternal uncles or friends",
            "Document fraud, forgery, erroneous agreements ending in legal penalties",
            "Benefits through IT, telecommunications, media",
            "Association with opposite sex partners significantly older or younger"
        ],
        "medical": [
            "Skin infections",
            "Allergy to insect bites",
            "Adverse drug reactions"
        ]
    },
    "Jupiter": {
        "predictions": [
            "Puthra Dosha (delays/defects in childbirth, recurrent miscarriages, organ flaws in children till age 12)",
            "Prime configuration for Test-Tube Baby/IVF treatments",
            "Sudden unexpected economic windfalls",
            "Cursed with public defamation/scandal from intimate circles at least once"
        ],
        "medical": [
            "Soft tissue ailments",
            "Liver disorders",
            "Muscular dystrophy"
        ]
    },
    "Venus": {
        "predictions": [
            "Severe financial instability, heavy mortgaging, exorbitant interest liabilities",
            "Illegal/shadow money transactions, bribery, forgery",
            "Second marriage for men, polygamy, non-traditional sexual relationships",
            "Defamation through women",
            "Success and massive wealth in cinema, visual media, luxury trades, overseas employment"
        ],
        "medical": [
            "STD/genital tract infections"
        ]
    },
    "Saturn": {
        "predictions": [
            "Highly destructive configuration",
            "Acute stress, sudden sluggishness, collapse of business/career",
            "Forced relocation from hometown",
            "Persistent debt trap",
            "Vicious legal battles with blood relatives",
            "Generates immense wealth ONLY if native is completely devoid of greed; if greedy, total ruin, imprisonment, suicide",
            "If found in multiple family charts, confirms deep hereditary family curse"
        ],
        "medical": []
    },
    "Mandhi": {
        "predictions": [
            "High risk of fatal poisonous insect/reptile bites",
            "Infant mortality",
            "Mysterious poisoning",
            "Suicide attempts via toxic ingestion"
        ],
        "medical": []
    }
}

RAHU_TRIPLE_CONJUNCTIONS = [
    {
        "planets": ["Rahu", "Mandhi", "Moon"],
        "predictions": ["Manufacturing/dealing in toxic substances, pesticides, mass casualties, death soon after remarriage."]
    },
    {
        "planets": ["Rahu", "Mandhi", "Venus", "Moon"],
        "predictions": ["Severe drug addiction, intoxication, narcotics involvement."]
    },
    {
        "planets": ["Rahu", "Saturn", "Mandhi"],
        "predictions": ["Troublesome life, absconding from creditors, suicidal attempts."]
    },
    {
        "planets": ["Rahu", "Mars", "Mandhi"],
        "predictions": ["Cruel accidents, homicide, suicide, fatal falls from heights, blood feuds."]
    },
    {
        "planets": ["Rahu", "Sun", "Moon"],
        "predictions": ["Native raised by non-parents; parental health fragile with marital friction; leucoderma, anemia, poor immunity, piles."]
    },
    {
        "planets": ["Rahu", "Sun", "Mars"],
        "predictions": ["Severe discord father-brother; encumbered patrimony; loss of male progeny; kidney/heart/brain ailment fear; brother cheats business."]
    },
    {
        "planets": ["Rahu", "Sun", "Mercury"],
        "predictions": ["Enmity father-maternal uncle; errors in land records; real estate loss through mortgage defaults; cheated by partners."]
    },
    {
        "planets": ["Rahu", "Sun", "Jupiter"],
        "predictions": ["Friction father-children; domestic gold/jewels misplaced/stolen; hereditary cancer/muscular dystrophy paternal lineage."]
    },
    {
        "planets": ["Rahu", "Sun", "Venus"],
        "predictions": ["Misunderstanding father-sister/daughter; business managed by female relatives ends catastrophically; tragic death paternal female kin."]
    },
    {
        "planets": ["Rahu", "Sun", "Saturn"],
        "predictions": ["Severe dispute management-laborers; extremely low sperm count/deformed spermatozoa; loss of male progeny; bone fractures."]
    },
    {
        "planets": ["Rahu", "Moon", "Mars"],
        "predictions": ["Severe mother-brother discord; heavy agricultural losses; ancestral deaths via drowning; pet animals die mysteriously; defective doors/toilets."]
    },
    {
        "planets": ["Rahu", "Moon", "Mercury"],
        "predictions": ["Mother favors one child abnormally; GERD, lung infection; severe love failures; mental depression."]
    },
    {
        "planets": ["Rahu", "Moon", "Jupiter"],
        "predictions": ["Discord native-mother; wife tortured by mother-in-law; uterine tumors, eye defects."]
    },
    {
        "planets": ["Rahu", "Moon", "Venus"],
        "predictions": ["Conflict mother-wife/sister; heavy financial loss and emotional trauma by women."]
    },
    {
        "planets": ["Rahu", "Moon", "Saturn"],
        "predictions": ["Punarphoo Dosha aggravated; last-minute wedding cancellations; mother denied ancestral support; epilepsy, fits, severe pessimism."]
    },
    {
        "planets": ["Rahu", "Mars", "Mercury"],
        "predictions": ["Friction brother-sister; criminal/extremist tendencies; boundary disputes; excellence in mathematics/research if in benefic sign."]
    },
    {
        "planets": ["Rahu", "Mars", "Jupiter"],
        "predictions": ["High/low BP, fatty tumors; defamation during temple service; obsession with hidden treasures."]
    },
    {
        "planets": ["Rahu", "Mars", "Venus"],
        "predictions": ["Severe marital disharmony, divorce, quick remarriage; Rahu moves to Mars=husband defective, to Venus=wife defective."]
    },
    {
        "planets": ["Rahu", "Mars", "Saturn"],
        "predictions": ["Most dangerous for catastrophic accidents, organ amputation, enslavement; property disputes. Suits only manual laborers."]
    },
    {
        "planets": ["Rahu", "Mercury", "Jupiter"],
        "predictions": ["Blocks benefic Jupiter/Mercury results; fraudulent bookkeeping; children cheated by friends; nerve/skin diseases; atheism."]
    },
    {
        "planets": ["Rahu", "Mercury", "Venus"],
        "predictions": ["Multiple love affairs, marital infidelity; native manipulated and ruined by women."]
    },
    {
        "planets": ["Rahu", "Mercury", "Saturn"],
        "predictions": ["Swindling, counterfeit documents, bogus products; aerospace education success; heavy agricultural losses."]
    },
    {
        "planets": ["Rahu", "Jupiter", "Venus"],
        "predictions": ["Financial ruin through greed/chit-fund scams; artificial organ transplantation; fame in media; inter-caste marriages."]
    },
    {
        "planets": ["Rahu", "Jupiter", "Saturn"],
        "predictions": ["Worse than Brahmahatya Dosha; initially grants massive assets then wipes them out; wealth usurped by undeserving strangers."]
    },
    {
        "planets": ["Rahu", "Venus", "Saturn"],
        "predictions": ["\"Give and Spoil\" combination; polygamy, public disgrace; native lives alone despite multiple marriages."]
    }
]

KETU_CONJUNCTIONS = {
    "Sun": {
        "predictions": [
            "Strict, unbending father/father-in-law",
            "Persistent obstruction in family income",
            "Father wastes lifetime in income-less public associations",
            "Native easily masters Surya Gayatri Mantra",
            "Spiritual initiations during Sun-Ketu Dasha",
            "Litigations with government regarding administrative powers or paternal lands"
        ]
    },
    "Moon": {
        "predictions": [
            "Deep mental depression, amnesia, psychiatric ailments in mother/elderly women",
            "Past tragic deaths of maternal ancestors due to mental illness",
            "Disinterest in domestic life, attraction to asceticism/occult wisdom",
            "Success in spiritual items and electronics business",
            "Litigations regarding maternal properties, adulteration, food industries"
        ]
    },
    "Mars": {
        "predictions": [
            "Highly destructive for marital life in female charts",
            "Continuous hostility with husband and brother",
            "Divorce within 9th, 14th, 18th, or 23rd year of marriage",
            "Accidents through fire, weapons, bomb blasts, acid burns, dog/poisonous bites",
            "Vasthu Dosha in residence",
            "Boundary disputes in immovable properties",
            "Success ONLY if husband in Ketu careers (law, medicine, tailoring, spirituality, weaving)"
        ]
    },
    "Mercury": {
        "predictions": [
            "Love Net/Magical Web leading to unconventional complex love affairs",
            "Perverted sexual desires",
            "Intense friction with maternal uncle and younger sister",
            "Fails in known subjects, passes in unknown ones",
            "Legal disputes regarding land partition, bank transactions, breach of contracts"
        ]
    },
    "Jupiter": {
        "predictions": [
            "Aandi Yoga (Beggar/Ascetic Yoga): Detachment from worldly pleasures, saint in family life",
            "98% of natives/children trapped in heavy debts losing major income to interest",
            "High vulnerability in chit-fund/finance businesses",
            "Grants easy uncollateralized loans based on trust which balloon into crises"
        ]
    },
    "Venus": {
        "predictions": [
            "Severe marital litigation, police complaints, mutual harassment",
            "Divorce common unless aspected by Jupiter",
            "Unidentified chronic uterine/pelvic diseases in wife",
            "Wealth squandered on disgraceful purposes",
            "Sister files property suits",
            "Ardent devotion to Lord Ganesha and Hanuman"
        ]
    },
    "Saturn": {
        "predictions": [
            "Unsteady employment, low income, sudden career disasters",
            "Constant hostility at workplace",
            "Severe Brahmahatya Dosha",
            "Early separation in young marriage",
            "Isolated ascetic lifestyle",
            "Native suffers ONLY if greedy; if in Ketu professions (law, medicine, auditing, tailoring, weaving, temple service) brings immense success"
        ]
    },
    "Mandhi": {
        "predictions": [
            "Confirms Pretha Shapam (curse of deceased ancestors) via maternal lineage",
            "Universally disliked",
            "Struggles to find purpose in life"
        ]
    }
}

KETU_TRIPLE_CONJUNCTIONS = [
    {
        "planets": ["Ketu", "Sun", "Moon"],
        "predictions": ["Tragic total separation father-mother; severe Puthra Dosha; recurring financial disasters every 12 years."]
    },
    {
        "planets": ["Ketu", "Sun", "Mars"],
        "predictions": ["Bitter feud/litigation father-brother; blood disorders, low sperm vitality."]
    },
    {
        "planets": ["Ketu", "Sun", "Jupiter"],
        "predictions": ["Complete estrangement father-son based on financial differences."]
    },
    {
        "planets": ["Ketu", "Sun", "Saturn"],
        "predictions": ["Deep friction management-labor; political success through agitation; chronic bone ailments."]
    },
    {
        "planets": ["Ketu", "Moon", "Mars"],
        "predictions": ["Uterine disorders in women; disputes over maternal estate; mother-brother estrangement."]
    },
    {
        "planets": ["Ketu", "Moon", "Mercury"],
        "predictions": ["Massive capital loss in share markets; deceit by maternal uncle; mental instability from failed strategies."]
    },
    {
        "planets": ["Ketu", "Moon", "Jupiter"],
        "predictions": ["Friction with wife due to over-attachment to mother; mother-in-law vs daughter-in-law enmity."]
    },
    {
        "planets": ["Ketu", "Moon", "Venus"],
        "predictions": ["Bitter warfare between female relatives of husband and wife; financial drainage by women."]
    },
    {
        "planets": ["Ketu", "Moon", "Saturn"],
        "predictions": ["Friction with public for retail/service workers; chronic depression/fatigue among family women."]
    },
    {
        "planets": ["Ketu", "Mars", "Mercury"],
        "predictions": ["Severe property disputes brother-sister; bank loan defaults using land collateral."]
    },
    {
        "planets": ["Ketu", "Mars", "Venus"],
        "predictions": ["Legal battles/divorce husband-wife; severe rift elder sister-younger brother."]
    },
    {
        "planets": ["Ketu", "Mars", "Jupiter"],
        "predictions": ["Obstacles in male progeny (only daughters); financial ruin in speculative markets; fatty blood clots."]
    },
    {
        "planets": ["Ketu", "Mars", "Saturn"],
        "predictions": ["Severe bone/joint fractures, surgical plaster, accidents; obstruction in Kula Deivatham worship."]
    },
    {
        "planets": ["Ketu", "Mercury", "Venus"],
        "predictions": ["Breach of trust by women; disputes over educational fees; double marriages; separation maternal uncle-wife."]
    },
    {
        "planets": ["Ketu", "Mercury", "Saturn"],
        "predictions": ["Business partnership collapse due to betrayal; speech/hearing impairments."]
    },
    {
        "planets": ["Ketu", "Jupiter", "Venus"],
        "predictions": ["Litigation over common family assets with sister; financial insolvency from reckless expansion."]
    },
    {
        "planets": ["Ketu", "Jupiter", "Saturn"],
        "predictions": ["Fatal Brahmahatya Dosha; native climbs to dizzying heights then crashes into bankruptcy; families abscond or commit mass suicide."]
    },
    {
        "planets": ["Ketu", "Venus", "Saturn"],
        "predictions": ["Severe workplace disputes caused by women; danger of imprisonment, bankruptcy, suicidal ideation."]
    }
]

KALA_SARPA_TYPES = [
    {
        "name": "Ananda",
        "rahu_house": 1,
        "ketu_house": 7,
        "karma_cause": "Betrayal of spouse.",
        "prediction": "Bad acquaintances, raised by non-parents, lack of marital pleasure. Marriage must be for lineage not sensual."
    },
    {
        "name": "Kalikala",
        "rahu_house": 2,
        "ketu_house": 8,
        "karma_cause": "Ruined another family, black magic, withheld laborers' wages.",
        "prediction": "Destroys family peace, effortless lying, collective curses, children stray immoral."
    },
    {
        "name": "Vasuki",
        "rahu_house": 3,
        "ketu_house": 9,
        "karma_cause": "Malicious rumors, ghost-fear extortion.",
        "prediction": "Good deeds for siblings misconstrued, inferiority complex, loss of siblings."
    },
    {
        "name": "Sankalpa",
        "rahu_house": 4,
        "ketu_house": 10,
        "karma_cause": "Destroyed creature habitats, ruined livelihoods.",
        "prediction": "Character suspected unfairly, mediocre jobs, no peaceful home, chronic real estate trouble."
    },
    {
        "name": "Padma",
        "rahu_house": 5,
        "ketu_house": 11,
        "karma_cause": "Encroached temple properties, stole profits.",
        "prediction": "Severe childbirth impediments, children with deformities, inability to enjoy ancestral estates."
    },
    {
        "name": "Maha Padma",
        "rahu_house": 6,
        "ketu_house": 12,
        "karma_cause": "Deprived people of sleep/peace, malicious lawsuits.",
        "prediction": "Chronic debts, heavy litigation. Ketu in 12th = final human incarnation."
    },
    {
        "name": "Nasaka",
        "rahu_house": 7,
        "ketu_house": 1,
        "karma_cause": "Coveted another's spouse.",
        "prediction": "Cheated even by good partners, money locked in another's custody, secrets exposed to humiliation."
    },
    {
        "name": "Karkodaka",
        "rahu_house": 8,
        "ketu_house": 2,
        "karma_cause": "Immoral wealth accumulation.",
        "prediction": "Deprived of career/wealth, loss of will to live."
    },
    {
        "name": "Sankaha",
        "rahu_house": 9,
        "ketu_house": 3,
        "karma_cause": "Traitor to Guru, unpaid Dakshina.",
        "prediction": "Mantra chanting ineffective, disrespect from subordinates."
    },
    {
        "name": "Padahaka",
        "rahu_house": 10,
        "ketu_house": 4,
        "karma_cause": "Land grabbing by breach of trust.",
        "prediction": "Defective education, residential trouble, chronic sickness."
    },
    {
        "name": "Vysalai",
        "rahu_house": 11,
        "ketu_house": 5,
        "karma_cause": "Profiting from abortions, stealing temple idols.",
        "prediction": "Expectations never matched, sacrifices unappreciated, insults from kin."
    },
    {
        "name": "Sesha Naga",
        "rahu_house": 12,
        "ketu_house": 6,
        "karma_cause": "Enslaving others, selling adulterated food.",
        "prediction": "Undiagnosed abdominal ailments, lifelong battle for rights."
    }
]

KALA_SARPA_RECTIFICATION_AGES = {
    (1, 7): 27,
    (2, 8): 33,
    (3, 9): 36,
    (4, 10): 42,
    (5, 11): 48,
    (6, 12): 56
}

# Kala Sarpa Yoga vs Dosha rules as a dict
KALA_SARPA_NOTES = {
    "Yoga": "All 7 planets travel TOWARDS Ketu (away from Rahu's mouth) - 25% ill, 75% yoga.",
    "Dosha": "All 7 planets travel TOWARDS Rahu (into Rahu's head) - 100% affliction.",
    "Manifestation": "Benefits manifest ONLY after age 33."
}

SPECIAL_NADI_PRINCIPLES = [
    {
        "rule_id": "SNP_1",
        "title": "Separated Planet Rule",
        "description": "When all planets hemmed within Rahu-Ketu axis and only ONE planet sits outside.",
        "prediction": "That planet's Karaka relative is alienated. Include all 8 variants (Sun/Moon/Mars/Mercury/Jupiter/Venus/Saturn/Lagna separated with their specific predictions)."
    },
    {
        "rule_id": "SNP_2",
        "title": "Sarpa Chandra (Ambuli) Point",
        "description": "Formula: Rahu_degree - Moon_degree = Distance. Sarpa_Chandra_degree = Moon_degree + Distance/2.",
        "prediction": "Any natal planet within ±2° of this point = completely paralyzed/ruined significations."
    },
    {
        "rule_id": "SNP_3",
        "title": "Center/Midpoint of Rahu-Ketu Axis",
        "description": "4th and 10th signs from Rahu/Ketu.",
        "prediction": "Planet in midpoint sign = 25% impact. On exact degree (±2°) = 75-100% life-transforming."
    },
    {
        "rule_id": "SNP_4",
        "title": "Shadow Planet Punarphoo",
        "description": "If house lord of Rahu and house lord of Ketu aspect each other, combine, or interchange signs.",
        "prediction": "Catastrophic separation/divorce within 30 days to a few years after marriage."
    },
    {
        "rule_id": "SNP_5",
        "title": "Dubious Character Rule",
        "description": "Mars/Venus in 3rd from Lagna, OR Rahu/Ketu in 3rd/11th from Mars/Venus.",
        "prediction": "Perpetual suspicion/mistrust between husband-wife."
    },
    {
        "rule_id": "SNP_6",
        "title": "Retrograde Attraction",
        "description": "If Person A's Rahu/Ketu in same signs as Person B's.",
        "prediction": "Deep unbreakable attraction in Rasi chart (never divorce), unexpressed love in Navamsa."
    }
]

PROGENY_RULES = [
    {
        "rule_id": "PR_1",
        "condition": "Direct Contact: Jupiter/Moon/5th Lord FIRST touches Rahu or Ketu in forward progression",
        "prediction": "Severe Puthra Dosha."
    },
    {
        "rule_id": "PR_2",
        "condition": "5th from Nodes: Rahu/Ketu in 5th house of Sun or Saturn",
        "prediction": "Ancestral descent obstructed."
    },
    {
        "rule_id": "PR_3",
        "condition": "Puthra Sogam triggers: Mars touching Rahu/Ketu; Rahu/Ketu in 1/3/5/9 from Mars; Sun+Saturn with Rahu/Ketu.",
        "prediction": "Mental agony from children."
    },
    {
        "rule_id": "PR_4",
        "condition": "Only female progeny: Masculine planets (Sun/Mars/Jupiter) meeting Rahu/Ketu first; Rahu/Ketu in 5th in Mercury/Saturn signs; Sun+Saturn aspecting Nodes in Trikona. Medical reason: genetic sperm deformity.",
        "prediction": "Only female progeny born."
    }
]

MEDICAL_RULES = [
    {
        "planets": ["Rahu", "Mars"],
        "diseases": ["Contaminated blood", "calcium depletion", "brittle bones", "dental diseases"]
    },
    {
        "planets": ["Rahu", "8thLord", "Sun"],
        "diseases": ["Virulent fevers", "heat boils", "burns"]
    },
    {
        "planets": ["Rahu", "Moon", "Mars"],
        "diseases": ["Severe high fever", "convulsions", "fits", "pneumonia"]
    },
    {
        "planets": ["Rahu", "Jupiter", "Saturn"],
        "diseases": ["Chronic paralysis", "motor neuron diseases", "stroke"]
    },
    {
        "planets": ["Ketu", "Saturn", "Jupiter"],
        "diseases": ["Chronic paralysis", "motor neuron diseases", "stroke"]
    },
    {
        "planets": ["Rahu", "Mercury"],
        "diseases": ["Skin disorders", "eczema", "nervous debility", "finger deformities"]
    },
    {
        "planets": ["Rahu", "Moon", "Mercury"],
        "diseases": ["Itching", "psoriasis", "vitiligo/leucoderma"]
    },
    {
        "planets": ["Rahu", "Moon"],
        "diseases": ["Chronic indigestion", "severe gastritis", "food allergies", "deep psychosis"]
    },
    {
        "planets": ["Rahu", "Mars", "Jupiter"],
        "diseases": ["Severe BP fluctuations", "lipid disorders", "fatty tumors"]
    },
    {
        "planets": ["Rahu", "Saturn", "Moon"],
        "diseases": ["Lifelong incurable chronic illness", "splenic enlargement"]
    },
    {
        "planets": ["Rahu", "Saturn", "Mandhi"],
        "diseases": ["Genetic/hereditary diseases", "ancestral karmic ailments"]
    },
    {
        "planets": ["Rahu", "Jupiter", "Sun"],
        "diseases": ["Malignancies", "cancer", "cellular mutations"]
    },
    {
        "planets": ["Rahu in Scorpio", "Ketu in Scorpio"],
        "diseases": ["Chronic uterine diseases", "PCOD", "rectal disorders", "fistula"]
    },
    {
        "planets": ["Rahu", "Jupiter"],
        "diseases": ["Liver cirrhosis", "jaundice", "biliary dysfunction"]
    },
    {
        "planets": ["Ketu", "Jupiter"],
        "diseases": ["Liver cirrhosis", "jaundice", "biliary dysfunction"]
    },
    {
        "planets": ["PCOD rules"],
        "diseases": ["4 conditions (Scorpio Asc/Moon, Rahu/Ketu in Scorpio, Rahu/Ketu in 8th, Rahu/Ketu+Moon in watery signs)"]
    },
    {
        "planets": ["IVF success rules"],
        "diseases": ["Transit Rahu over natal Jupiter, transit Rahu over natal 5th Lord, or transit Jupiter over natal Rahu"]
    },
    {
        "planets": ["Accident Triad rules"],
        "diseases": ["Mars+Saturn combining/aspecting + Rahu/Ketu in 3rd/11th from them"]
    },
    {
        "planets": ["Amputation rules"],
        "diseases": ["If afflicted sign houses combusted planet or sign lord is combusted = organ amputation"]
    },
    {
        "planets": ["Survival rules"],
        "diseases": ["If Dasha lord not in Maraka + Jupiter aspects Ketu = survives"]
    }
]

DASHA_BHUKTI_RULES = [
    {
        "rule_id": "DB_1",
        "description": "Rahu/Ketu in Dasha perform core functions of Bhava they occupy."
    },
    {
        "rule_id": "DB_2",
        "description": "If joined with another planet, they execute that planet's portfolio alongside house matters."
    },
    {
        "rule_id": "DB_3",
        "description": "Star Dispersal: If other planets posited in Rahu/Ketu stars (Ardra, Swati, Shatabhisha, Ashwini, Magha, Moola), Nodes reduce direct house impact."
    },
    {
        "rule_id": "DB_4",
        "description": "Benefic Dasha + Node Bhukti: Problems resolve rapidly once Bhukti ends. Node Dasha + Benefic Bhukti: Problems worsen."
    },
    {
        "rule_id": "DB_5",
        "description": "Problems in Rahu Dasha-Jupiter Bhukti reappear magnified in Jupiter Dasha-Rahu Bhukti."
    },
    {
        "rule_id": "DB_6",
        "description": "Transit Mirroring: When transit Rahu/Ketu recreate exact natal degree/sign alignment, landmark events occur."
    }
]

PERILOUS_DASHA_PERIODS = [
    ("Rahu", "Mercury"),
    ("Mercury", "Rahu"),
    ("Rahu", "Venus"),
    ("Venus", "Rahu"),
    ("Rahu", "Saturn"),
    ("Saturn", "Rahu"),
    ("Rahu", "Ketu"),
    ("Ketu", "Rahu"),
    ("Mars", "Rahu"),
    ("Jupiter", "Ketu"),
    ("Ketu", "Jupiter"),
    ("Saturn", "Ketu")
]

KARMA_EXPOSURE_AGES = {
    "jupiter_ketu_distance": {
        0: "0-2 years",
        1: "0-12 years",
        2: "12-24 years",
        3: "24-36 years",
        4: "36-48 years",
        5: "48-60 years",
        6: "24-36 and 60-72 years",
        10: "36-48 years",
        11: "48-60 years",
        12: "24-36 and 60-72 years"
    },
    "saturn_rahu_distance": {
        0: "0-2 years",
        1: "0-12 years",
        2: "12-24 years",
        3: "24-36 years",
        4: "36-48 years",
        5: "48-60 years",
        6: "36-48 and 60-72 years",
        10: "36-48 years",
        11: "48-60 years",
        12: "36-48 and 60-72 years"
    }
}

SAYA_YOGA = {
    1: {"kalapurusha_lord": "Mars", "prediction": "Police/surgery/military/engineering/automobile (e.g. Henry Ford)"},
    2: {"kalapurusha_lord": "Venus", "prediction": "Arts/cinema/luxury/politics/astrology (e.g. Karunanidhi, B.V. Raman)"},
    3: {"kalapurusha_lord": "Mercury", "prediction": "Auditing/strategy/journalism/music (e.g. Ilayaraja)"},
    4: {"kalapurusha_lord": "Moon", "prediction": "Carnatic vocals/mass arts/liquid trading (e.g. M.S. Subbulakshmi)"},
    5: {"kalapurusha_lord": "Sun", "prediction": "High admin/executive leadership/political power"},
    6: {"kalapurusha_lord": "Mercury", "prediction": "Astrology teaching/legal mastery/journalism (e.g. Indira Gandhi)"},
    7: {"kalapurusha_lord": "Venus", "prediction": "Law/diplomacy/foreign trade"},
    8: {"kalapurusha_lord": "Mars", "prediction": "Industrial machinery/manufacturing/sudden inheritance (e.g. Tagore)"},
    9: {"kalapurusha_lord": "Jupiter", "prediction": "High overseas posts/statecraft/teaching (e.g. APJ Abdul Kalam, Shastri)"},
    10: {"kalapurusha_lord": "Saturn", "prediction": "Mass leadership/oil business/cinema acting/military (e.g. Kamal Haasan)"},
    11: {"kalapurusha_lord": "Saturn", "prediction": "Revolutionary industrialist/mass political power (e.g. Jayalalithaa, Queen Victoria)"},
    12: {"kalapurusha_lord": "Jupiter", "prediction": "Multimillionaire/medical pediatrics/nuclear physics"}
}

MAHA_SAKTHI_YOGA = {
    "description": "Lagna/Moon/Sun in close proximity to Rahu/Ketu.",
    "factors": "1 factor=33%, 2=66%, 3=100%.",
    "results": "Destroys domestic peace but if native dedicates to selfless public service, grants global fame."
}

DHANA_YOGA_RULES = [
    "2nd and 11th lords of Kalapurusha in 8th house.",
    "Transit Jupiter/Saturn over 8th house Venus.",
    "Transit Venus/Saturn over 8th house Jupiter.",
    "Transit Venus/Jupiter over 8th house Saturn."
]

SPORTS_RULES = {
    "moon_kendra_percentage": None,
    "moon_trikona_percentage": None,
    "moon_adjacent_percentage": None,
    "moon_nakshatra_percentage": None,
    "additional_rules": "No specific sports rules provided in the prompt besides the dict keys."
}

POORVIKA_DOSHA = {
    "paternal": [
        "Sun+Rahu", "Sun+Ketu", "Sun+Saturn", "Saturn+Rahu", "Saturn+Ketu"
    ],
    "maternal": [
        "Moon+Rahu", "Moon+Ketu", "Moon+Mars+Saturn"
    ],
    "manifestation": {
        "paternal": "Forced to abandon hometown, ancestral properties lost, obstruction of Kula Deivatham worship, nocturnal anxiety.",
        "maternal": "Maternal heritage ruined, mental illness in women, properties alienated."
    }
}

REMEDIES = [
    {
        "condition": "Sarpa Dosha general",
        "remedy": "Pilgrimage to Thirunageswaram, Srikalahasti, Thirupamburam, etc. (list all 11 temples)",
        "temple": "Thirunageswaram, Srikalahasti, Thirupamburam"
    },
    {
        "condition": "Sun+Ketu/Rahu",
        "remedy": "Shiva, Rudra, Surya Gayatri Mantras"
    },
    {
        "condition": "Moon+Ketu/Rahu",
        "remedy": "Shakthi, Ambal, Virgin Goddess Gayatri Mantras"
    },
    {
        "condition": "Mars+Ketu/Rahu",
        "remedy": "Lord Murugan (male signs) or Virulent Bhadrakali/Bhagavathi (female signs)"
    },
    {
        "condition": "Mercury+Ketu/Rahu",
        "remedy": "Lord Vishnu (male signs) or Lakshmi/Mahalakshmi (female signs)"
    },
    {
        "condition": "Jupiter+Ketu/Rahu",
        "remedy": "Dakshinamurthy/Hayagrivar (male signs) or Saraswathi (female signs)"
    },
    {
        "condition": "Venus+Ketu/Rahu",
        "remedy": "Ayyappan/Murugan (male signs) or Annapoorani/Kamakshi (female signs)"
    },
    {
        "condition": "Saturn+Ketu/Rahu",
        "remedy": "Lord Shiva/Bhairava (male signs) or Kaali/Bhagavathi (female signs)"
    }
]
