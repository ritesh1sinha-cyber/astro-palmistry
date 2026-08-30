#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reading_palms_book_data.py — Complete Palmistry Rule Base & Dermatoglyphic Neural Data

Synthesizes classical dermatoglyphic models, whole-hand morphology, and neural topography.
"""
from __future__ import annotations

# ═════════════════════════════════════════════════════════════════════════════
# 1. SCIENTIFIC PALMISTRY & NEURAL LAWS
# ═════════════════════════════════════════════════════════════════════════════
SCIENTIFIC_PALMISTRY_FACTS = [
    {
        "id": "brain_hand_neural_highway",
        "title": "The Brain-Hand Direct Neural Highway",
        "subtitle": "Why the hand mirrors the subconscious mind",
        "scientific_fact": (
            "The human hand has the highest concentration of sensory nerve endings and motor cortex representations in the entire body. "
            "The major lines on your palm are not random wrinkles; they are bio-electrical creases formed by continuous neural feedback "
            "from the sub-cortex and autonomic nervous system. Your palm is literally a dynamic brain readout."
        ),
        "entertainment_insight": "When you think, worry, plan, or create, your brain sends micro-electrical impulses that subtly shape the vascular and muscular tension of your palm.",
    },
    {
        "id": "six_month_line_evolution",
        "title": "The Dynamic 6-Month Line Transformation Law",
        "subtitle": "Lines are not set in stone — they evolve with conscious effort",
        "scientific_fact": (
            "Unlike fingerprints which remain permanent from birth, palm lines are dynamic living channels. "
            "When an individual makes a decisive career pivot, adopts disciplined mental routines, or overcomes severe stress, "
            "new upward effort branches and cross-bars physically appear or fade within 6 to 12 months."
        ),
        "entertainment_insight": "Your passive hand (left) records your inborn genetic potential, but your active hand (right) is a living chalkboard constantly being rewritten by your daily willpower.",
    },
    {
        "id": "money_triangle_vault",
        "title": "The Closed Great Triangle (The Wealth Vault)",
        "subtitle": "The capacity to accumulate and retain capital",
        "scientific_fact": (
            "When the Line of Head, Line of Fate, and Line of Mercury intersect in the center of the palm to form a completely enclosed triangle, "
            "it forms the classical 'Dhana Triangle' or Wealth Vault. A tightly closed triangle signifies that wealth earned is preserved, "
            "invested prudently, and compounded rather than leaking out through impulsive expenditures."
        ),
        "entertainment_insight": "A wide Head Line paired with an ascending Fate Line ensures high earning velocity, but a sealed triangle guarantees long-term financial sovereignty.",
    },
    {
        "id": "quadrangle_mental_bandwidth",
        "title": "The Quadrangle & Intellectual Sovereignty",
        "subtitle": "The space between Head and Heart lines",
        "scientific_fact": (
            "The Quadrangle (the central arena between the Line of Head and Line of Heart) measures mental equilibrium. "
            "A well-proportioned, uncrowded quadrangle indicates broad-mindedness, emotional composure under pressure, and independent judgment. "
            "When the Mystic Cross sits freely inside this space, it grants uncanny intuitive hunches."
        ),
        "entertainment_insight": "People with a clean, spacious Quadrangle cannot be easily gaslit or manipulated—their internal radar instantly flags inconsistencies.",
    },
    {
        "id": "solomon_ring_psychic_radar",
        "title": "The Ring of Solomon (The Human Character Radar)",
        "subtitle": "Instant first-impression accuracy",
        "scientific_fact": (
            "The subtle semi-circular arc wrapping the base of the index finger (Mount of Jupiter) is the classical Ring of Solomon. "
            "In modern scientific palmistry, it marks heightened subconscious micro-expression reading—enabling the native to instinctively "
            "gauge a person's true character within the first two minutes of conversation."
        ),
        "entertainment_insight": "If your gut feeling tells you someone is untrustworthy, believe it—your Solomon Ring is processing subtle body language faster than your conscious brain.",
    },
]

# ═════════════════════════════════════════════════════════════════════════════
# 2. THE FOUR ELEMENTAL HAND SHAPES
# ═════════════════════════════════════════════════════════════════════════════
HAND_SHAPES = {
    "Earth": {
        "palm_shape": "Square palm",
        "finger_length": "Short fingers (finger length < palm length)",
        "skin_texture": "Coarse, firm, warm",
        "lines_count": "Few, deep, clear, uncluttered major lines",
        "elemental_temperament": "Practical, grounded, dependable, tactile, straightforward, nature-oriented.",
        "professional_affinity": [
            "Engineering", "Agriculture", "Construction", "Craftsmanship",
            "Physical trades", "Manufacturing", "Field operations", "Logistics"
        ],
        "psychological_drive": "Seeks tangible security, physical output, and reliable, unpretentious routines.",
        "stress_pattern": "Stubbornness, resistance to abstract changes, holding physical tension.",
    },
    "Air": {
        "palm_shape": "Square palm",
        "finger_length": "Long fingers (finger length >= palm length)",
        "skin_texture": "Dry, smooth, fine",
        "lines_count": "Moderate to many fine lines, clear major lines",
        "elemental_temperament": "Intellectual, analytical, articulate, objective, communicative, systems-oriented.",
        "professional_affinity": [
            "Software Architecture", "Data Science", "Writing & Journalism",
            "Law & Auditing", "Education & Research", "Strategic Consulting", "Media"
        ],
        "psychological_drive": "Seeks mental stimulation, conceptual clarity, exchange of ideas, and intellectual autonomy.",
        "stress_pattern": "Mental restlessness, overthinking, anxiety neurosis, nervous fatigue.",
    },
    "Fire": {
        "palm_shape": "Oblong / Rectangular palm",
        "finger_length": "Short fingers (finger length < palm length)",
        "skin_texture": "Warm, elastic, vibrant",
        "lines_count": "Vibrant, deep lines with dynamic offshoots",
        "elemental_temperament": "Dynamic, enthusiastic, visionary, courageous, impulsive, charismatic leader.",
        "professional_affinity": [
            "Entrepreneurship", "Executive Leadership", "Sales & Marketing",
            "Sports & Defense", "Emergency Response", "Creative Directing", "Public Speaking"
        ],
        "psychological_drive": "Seeks excitement, visible impact, autonomy in leadership, and rapid manifestation.",
        "stress_pattern": "Burnout, impatience with routine details, sharp temper, restless boredom.",
    },
    "Water": {
        "palm_shape": "Oblong / Rectangular palm",
        "finger_length": "Long fingers (finger length >= palm length)",
        "skin_texture": "Soft, cool, delicate",
        "lines_count": "Rich tapestry of fine, delicate, criss-crossing lines",
        "elemental_temperament": "Intuitive, empathetic, aesthetic, imaginative, receptive, spiritually sensitive.",
        "professional_affinity": [
            "Psychology & Counseling", "Fine Arts & Design", "Healing & Medicine",
            "Music & Poetry", "Spiritual/Occult Practice", "Human Resources", "Hospitality"
        ],
        "psychological_drive": "Seeks emotional resonance, artistic beauty, authentic depth, and harmonious sanctuary.",
        "stress_pattern": "Emotional absorption, vulnerability to toxic environments, boundary dissolution.",
    },
}

# ═════════════════════════════════════════════════════════════════════════════
# 3. THE MAJOR LINES (LIFE, HEAD, HEART, FATE)
# ═════════════════════════════════════════════════════════════════════════════
MAJOR_LINES_RULES = {
    "Life_Line": {
        "wide_arc_venus": {
            "title": "Wide Sweeping Arc (Robust Vitality & Social Warmth)",
            "condition": "Life line swings wide across the palm, maximizing the Venus mount area.",
            "prediction": "Abundant physical stamina, robust immune resilience, warm generosity, strong digestive heat, and high social appetite. Easily recovers from fatigue.",
            "timing_note": "Indicates steady physical vigor spanning well into advanced age (80+ benchmark).",
        },
        "narrow_arc_venus": {
            "title": "Narrow Arc Hugging Thumb (Guarded Energy & Solitude)",
            "condition": "Life line runs close to the base of the thumb, constricting the Venus mount.",
            "prediction": "Cautious physical output, selective social boundaries, sensitive nervous system. Prefers quiet home sanctuary over crowded social environments.",
            "timing_note": "Requires disciplined energy budgeting; benefits from regular restorative retreats.",
        },
        "chained_origin": {
            "title": "Chained or Feathered Early Section (Early Sensitivities)",
            "condition": "Islands or chained loops near the origin between Jupiter and thumb (Ages 0–18).",
            "prediction": "Delicate childhood constitution, respiratory or digestive sensitivities during formative years, or strong dependence on family environment before finding independent stride.",
            "timing_note": "Clears into a sharp, singular channel after age 20–22, marking full physiological independence.",
        },
        "upward_branches_jupiter": {
            "title": "Upward Effort Branches Toward Jupiter (Ambition Milestones)",
            "condition": "Fine sharp branches rising off the upper Life line toward the index finger (Jupiter mount).",
            "prediction": "Major educational or professional breakthroughs achieved through conscious personal willpower, competitive exam success, or launching independent ventures.",
            "timing_note": "Each branch pinpoints an exact age milestone of triumph (typically ages 21, 28, or 35).",
        },
        "sister_mars_line": {
            "title": "Sister Mars Line / Line of Vitality Shield",
            "condition": "A strong parallel line running inside the Life line on the Lower Mars / Venus mount.",
            "prediction": "Exceptional recuperative guardian shield. Protects against severe physical illnesses or accidents, provides hidden reservoir of stamina, and grants loyal support from close allies.",
            "timing_note": "Operates as a continuous vitality booster throughout the decades it runs parallel.",
        },
        "forked_base_travel": {
            "title": "Forked Termination Toward Luna Mount (Travel / Dual Residence)",
            "condition": "Life line splits into two distinct branches at the wrist, one branch sweeping toward the Mount of Luna.",
            "prediction": "Strong impulse for foreign travel, long-distance relocation, or maintaining residences in multiple cities/countries. Restless in later life, finding peace away from the birth town.",
            "timing_note": "Activates strongly in mid-to-late career (Ages 40+).",
        },
    },

    "Head_Line": {
        "straight_practical": {
            "title": "Straight & Level Head Line (Pragmatic & Analytical Posture)",
            "condition": "Head line traverses straight across the palm toward Upper Mars.",
            "prediction": "Logical, methodical, evidence-driven intellect. Excels in systems architecture, quantitative reasoning, financial auditing, contract review, and cool-headed crisis execution.",
            "cognitive_style": "Linear, factual, objective; assesses outcomes before emotions.",
        },
        "gentle_slope_creative": {
            "title": "Gentle Sloping Head Line (Harmonized Logic & Imagination)",
            "condition": "Head line slopes gently downward into the upper sector of the Mount of Luna.",
            "prediction": "Balanced intellectual versatility. Combines structured logic with creative problem-solving and psychological intuition. Highly adaptable in executive or advisory capacities.",
            "cognitive_style": "Holistic, strategic, perceptive; integrates technical facts with human nuances.",
        },
        "deep_curve_luna": {
            "title": "Deeply Curved Head Line (Deeply Imaginative & Intuitive)",
            "condition": "Head line curves deeply down into the lower Mount of Luna.",
            "prediction": "Profoundly imaginative, artistic, psychological, and occult-minded intellect. Excels in narrative arts, profound research, holistic healing, and abstract innovation.",
            "cognitive_style": "Subjective, associative, intuitive; senses underlying emotional currents.",
        },
        "writers_fork": {
            "title": "Writer's Fork / Dual Aptitude Bifurcation",
            "condition": "Head line divides into two clear forks at its termination (one branch straight, one dipping to Luna).",
            "prediction": "The classic mark of dual intellectual mastery: simultaneously possesses the commercial shrewdness to monetize ideas (straight branch) and the creative genius to envision original concepts (dipping branch). Outstanding for authorship, product design, and consulting.",
            "cognitive_style": "Dual-processing: bridges commercial realism with visionary imagination.",
        },
        "joined_life_line_origin": {
            "title": "Joined Origin with Life Line (Thoughtful & Measured Beginnings)",
            "condition": "Head line and Life line are tied together for a short distance at their origin.",
            "prediction": "Prudent, cautious, respectful of family counsel in youth. Thinks through consequences thoroughly before acting; avoids reckless gambling.",
            "cognitive_style": "Deliberate and protective of personal reputation.",
        },
        "independent_gap_origin": {
            "title": "Separated Origin with Life Line (Independent & Pioneering)",
            "condition": "A visible gap exists between the start of the Head line and Life line.",
            "prediction": "Fiercely independent, self-reliant, pioneering spirit from early youth. Hates micromanagement, makes instant decisions, and carves out an original career path.",
            "cognitive_style": "Fast, decisive, confident risk-taker.",
        },
    },

    "Heart_Line": {
        "curved_to_jupiter": {
            "title": "Curved Heart Line Ending on Mount of Jupiter (Idealistic & Warm)",
            "condition": "Heart line sweeps upward ending clearly under the index finger on Jupiter mount.",
            "prediction": "High emotional nobility, warmth, devotion, and high standards in love and friendship. Expressive, honorable, loyal partner who leads with integrity.",
            "relational_style": "Openhearted, dignified, seeks an inspiring and respected life companion.",
        },
        "straight_to_saturn": {
            "title": "Straight Heart Line Ending Under Saturn Mount (Pragmatic & Boundary-Conscious)",
            "condition": "Heart line runs straight across the palm terminating under the middle finger.",
            "prediction": "Emotionally self-contained, private, selective in opening up. Values concrete loyalty and practical support over dramatic emotional displays. Master of maintaining professional composure.",
            "relational_style": "Grounded, protective, shows love through actions and material stability.",
        },
        "forked_ending_trident": {
            "title": "Trident / Three-Pronged Ending (Solomon's Emotional Equilibrium)",
            "condition": "Heart line branches into a three-pronged fork touching Jupiter, Saturn, and the gap between them.",
            "prediction": "The ideal emotional balance: combines Jupiterian warmth and devotion, Saturnian discernment and loyalty, and practical common sense. Highly revered as a mediator and mentor.",
            "relational_style": "Empathetic yet discerning, balanced, socially beloved.",
        },
    },

    "Fate_Line": {
        "origin_wrist_center": {
            "title": "Origin from Base Center / Wrist (Self-Made Anchor)",
            "condition": "Fate line rises from the bottom center of the palm straight toward Saturn mount.",
            "prediction": "Self-driven career trajectory. Takes full personal accountability from young adulthood; builds status through personal grit and direct individual competence.",
            "timing_milestone": "Steady career ascent from early 20s onwards.",
        },
        "origin_luna_mount": {
            "title": "Origin from Mount of Luna (Public Patronage & Client Success)",
            "condition": "Fate line begins diagonally from the Mount of Luna and joins the upward career channel.",
            "prediction": "Career success heavily amplified by public popularity, client trust, international partnerships, and patronage from influential benefactors. Thrives in consulting, advisory, and public-facing enterprises.",
            "timing_milestone": "Major career leaps coincide with expanding public networks.",
        },
        "origin_life_line": {
            "title": "Origin Tied to Life Line (Early Duty Transforming to Autonomy)",
            "condition": "Fate line emerges directly out of the Life line in the lower palm.",
            "prediction": "Early career shaped by family responsibilities or parental expectations. In mid-life, personal identity breaks free to build independent commercial legacy.",
            "timing_milestone": "Full career independence unlocks around ages 28–32.",
        },
        "shift_at_head_line": {
            "title": "Mid-Life Career Pivot at Head Line (Age 35 Structural Milestone)",
            "condition": "Fate line pauses, shifts, or strengthens as it intersects the Head line.",
            "prediction": "A decisive conscious realignment of professional focus around age 35. Transitioning from working for others to independent executive authority or major business re-structuring.",
            "timing_milestone": "Ages 35–38 mark the launch of the core life work.",
        },
        "continuation_past_heart": {
            "title": "Strong Continuation Past Heart Line (Productive Golden Years)",
            "condition": "Fate line crosses the Heart line and climbs deeply onto the Mount of Saturn.",
            "prediction": "Active, lucrative, and intellectually fulfilling career running well past traditional retirement (Ages 50–75+). Never truly retires; continues generating authority, advisory income, and legacy.",
            "timing_milestone": "Peak authority and institutional respect after age 50.",
        },
        "double_fate_line": {
            "title": "Double Fate Line / Parallel Career Streams",
            "condition": "Two parallel Fate lines run concurrently up the central palm.",
            "prediction": "Simultaneous dual professional vocations: e.g. running a core technical/executive enterprise while maintaining a lucrative consulting, advisory, or investment stream.",
            "timing_milestone": "Generates dual streams of income and prestige.",
        },
    },
}

# ═════════════════════════════════════════════════════════════════════════════
# 4. THE MOUNTS & SPECIAL MARKINGS
# ═════════════════════════════════════════════════════════════════════════════
MOUNTS_DATA = {
    "Jupiter": {
        "location": "Base of Index Finger",
        "archetype": "Guru / King / Leader",
        "strong_attributes": "Natural leadership authority, philosophical wisdom, social dignity, administrative command, ambition.",
        "flat_attributes": "Humility, prefers supporting roles over public leadership.",
        "special_marks": {
            "Cross": "A single clear cross on Jupiter mount is one of the most auspicious marks in palmistry: signifies a deeply happy, spiritually fulfilling marriage and high social status.",
            "Square": "Teacher's Square: grants innate talent for teaching, consulting, mentoring, and protection from social slander.",
            "Star": "Extraordinary, sudden rise to high public leadership and lasting renown.",
        },
    },
    "Saturn": {
        "location": "Base of Middle Finger",
        "archetype": "Philosopher / Architect / Master Builder",
        "strong_attributes": "Discipline, patience, deep research acumen, love for solitude, structural execution, financial prudence.",
        "flat_attributes": "Optimistic, light-hearted, dislikes heavy routines.",
        "special_marks": {
            "Square": "Protection against financial ruin and physical accidents.",
            "Single Vertical Line": "Steady financial security and peaceful independence in mature age.",
        },
    },
    "Apollo_Sun": {
        "location": "Base of Ring Finger",
        "archetype": "Artist / Visionary / Sovereign",
        "strong_attributes": "Aesthetic refinement, creative brilliance, social charisma, fame, love for luxury and elegance.",
        "flat_attributes": "Modest, utilitarian, unconcerned with public applause.",
        "special_marks": {
            "Sun_Line": "Line of Apollo running to the mount: guarantees public recognition, financial wealth from creative/intellectual output.",
            "Star": "World-class fame, artistic brilliance, and massive commercial rewards.",
        },
    },
    "Mercury": {
        "location": "Base of Little Finger",
        "archetype": "Merchant / Diplomat / Scholar",
        "strong_attributes": "Commercial acumen, eloquent speech, software/technical agility, negotiation mastery, scientific intellect.",
        "flat_attributes": "Blunt speech, prefers simple linear trade.",
        "special_marks": {
            "Medical_Stigmata": "Three or four vertical lines on Mercury mount: innate healing gift, natural counseling empathy, and diagnostic intuition.",
            "Trident": "Exceptional commercial wealth and business empire building.",
        },
    },
    "Upper_Mars": {
        "location": "Percussion Edge between Heart Line and Head Line",
        "archetype": "Defender / Resilient Warrior",
        "strong_attributes": "Moral courage, mental resilience, patience under pressure, steady self-control, steadfast endurance.",
    },
    "Lower_Mars": {
        "location": "Inside the Life Line, above the Thumb",
        "archetype": "Pioneer / Dynamic Combatant",
        "strong_attributes": "Physical bravery, initiative, competitive drive, physical assertiveness.",
    },
    "Luna_Moon": {
        "location": "Lower Percussion opposite Venus",
        "archetype": "Dreamer / Seer / Mystic",
        "strong_attributes": "Rich subconscious imagination, poetic intuition, psychic sensitivity, affinity for foreign travels and water.",
        "special_marks": {
            "Travel_Lines": "Horizontal lines entering from the percussion: foreign journeys, overseas residences, and international trade.",
            "Via_Lascivia": "Heightened sensory receptivity and desire for transcendent experiences.",
        },
    },
    "Venus": {
        "location": "Base of Thumb inside Life Line",
        "archetype": "Lover / Provider / Force of Life",
        "strong_attributes": "Warmth, passionate vitality, aesthetic joy, physical stamina, generosity, love for music and comfort.",
    },
    "Plain_of_Mars": {
        "location": "Center of Palm (Quadrangle & Great Triangle)",
        "archetype": "Inner Arena",
        "special_marks": {
            "Mystic_Cross": "La Croix Mystique situated in the Quadrangle between Head line and Heart line: grants profound intuitive perception, occult insights, and uncanny accurate hunches about people and future trends.",
            "Solomon_Ring": "Curved line wrapping under Jupiter mount: psychological empathy, wisdom of Solomon, natural ability to read human character.",
        },
    },
}

# ═════════════════════════════════════════════════════════════════════════════
# 5. THE THUMB — WILL & LOGIC RATIOS
# ═════════════════════════════════════════════════════════════════════════════
THUMB_RULES = {
    "will_logic_balance": {
        "balanced": {
            "title": "Harmonized Will & Logic (Strategic Manifestation)",
            "condition": "1st phalange (Will) and 2nd phalange (Logic) are equal in length and well-formed.",
            "prediction": "Plans carefully with sound reasoning, then executes decisively with sustained willpower. The hallmark of effective executives and master craftsmen.",
        },
        "dominant_logic": {
            "title": "Dominant Logic over Will (Deep Analyst / Advisor)",
            "condition": "2nd phalange (Logic) is longer than 1st phalange (Will).",
            "prediction": "Brilliant in theoretical analysis, strategic advisory, and problem diagnosis. Benefits from setting strict deadlines to prevent analysis paralysis.",
        },
        "dominant_will": {
            "title": "Dominant Will over Logic (Bold Action-Taker)",
            "condition": "1st phalange (Will) is longer and stronger than 2nd phalange (Logic).",
            "prediction": "Fierce determination and unstoppable drive. Acts swiftly on conviction; achieves breakthroughs through sheer persistence.",
        },
    },
    "flexibility": {
        "supple": {
            "title": "Supple / Flexible Thumb (Adaptable & Generous)",
            "condition": "Top joint bends backward with light pressure.",
            "prediction": "Open-minded, generous, socially adaptable, readily assimilates new ideas and changes.",
        },
        "stiff": {
            "title": "Stiff / Firm Thumb (Resolute & Principled)",
            "condition": "Thumb remains rigid with zero backward bend.",
            "prediction": "Unyielding integrity, rock-solid reliability, cautious with resources, highly disciplined.",
        },
    },
}
