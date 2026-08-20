"""Divisional profile engine for the About You section.

Provides a balanced Vedic analysis of all 9 key divisional charts
(D1, D2, D3, D7, D9, D10, D12, D24, D30), examining both:
1. Natural strengths & positive yogas (exalted/own planets, kendra/trikona placements)
2. Vulnerabilities & friction points (trik house 6/8/12 placements, debilitations, afflictions)
3. Practical remedial & lifestyle guidance to navigate those friction points.
4. Gating: Remedies blurred in Free report, fully visible in Paid report.
5. Scannability: Important lines and phrases highlighted in bold for clarity.
"""
from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any

from astro_precompute import (
    SIGN_LORDS,
    SIGNS,
    get_dignity,
    house_from_lagna,
    sign_index,
)

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
DUSTHANA = {6, 8, 12}
GOOD_HOUSES = {1, 2, 4, 5, 7, 9, 10, 11}
NAT_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
NAT_MALEFIC = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}

FREE_ALLOWED_VARGAS = {"D1", "D2", "D3", "D12"}
LOCKED_TEASER_VARGAS = ["D7", "D9", "D10", "D24", "D30"]


@dataclass
class DivisionalInsight:
    code: str
    name: str
    governs: str
    lagna_sign: str
    lord: str
    lord_sign: str
    lord_house: int
    lord_dignity: str
    strength: str  # strong | mixed | weak
    headline: str
    prediction: str
    remedy: str
    evidence: str


VARGA_META: dict[str, dict[str, str]] = {
    "D1": {
        "name": "Birth Chart (D1)",
        "governs": "Core Constitution & Temperament",
        "desc": "Your foundational personality, physical vitality, and overall life orientation.",
    },
    "D2": {
        "name": "Wealth Division (D2)",
        "governs": "Wealth & Financial Capacity",
        "desc": "Your wealth accumulation instincts, asset building, and liquid resource holding power.",
    },
    "D3": {
        "name": "Courage & Enterprise Division (D3)",
        "governs": "Siblings, Courage & Initiative",
        "desc": "Your personal drive, executive courage, and relationships with siblings and peers.",
    },
    "D7": {
        "name": "Lineage & Progeny Division (D7)",
        "governs": "Children & Creative Legacy",
        "desc": "Your progeny prospects, creative continuation, and family lineage fulfillment.",
    },
    "D9": {
        "name": "Soul Purpose & Marriage Division (D9)",
        "governs": "Dharma, Soul Purpose & Marriage",
        "desc": "Your inner spiritual maturity, spouse compatibility, and lifelong partnership harmony.",
    },
    "D10": {
        "name": "Profession & Status Division (D10)",
        "governs": "Career, Status & Leadership",
        "desc": "Your professional karma, public recognition, authority, and vocational trajectory.",
    },
    "D12": {
        "name": "Ancestral Lineage Division (D12)",
        "governs": "Parents & Ancestral Roots",
        "desc": "Your ancestral foundation, parental heritage, and inherited moral grounding.",
    },
    "D24": {
        "name": "Higher Learning Division (D24)",
        "governs": "Education & Intellectual Acumen",
        "desc": "Your higher learning potential, analytical skills, and capacity to master complex disciplines.",
    },
    "D30": {
        "name": "Resilience & Protection Division (D30)",
        "governs": "Hardships, Karmic Obstacles & Resilience",
        "desc": "Your inner psychological immunity, overcoming life friction, and converting adversity into strength.",
    },
}


def _get_varga_lagna(pc: dict, code: str) -> str:
    if code == "D1":
        return (
            pc.get("meta", {}).get("lagna_sign", "")
            or pc.get("planets", {}).get("Lagna", {}).get("sign", "")
            or (pc.get("divisional", {}).get("D1", {}) or {}).get("Lagna", "")
            or ""
        )
    return (pc.get("divisional", {}).get(code, {}) or {}).get("Lagna", "")


def _get_varga_planet_sign(pc: dict, code: str, planet: str) -> str:
    if code == "D1":
        return (pc.get("planets", {}).get(planet, {}) or {}).get("sign", "")
    return (pc.get("divisional", {}).get(code, {}) or {}).get(planet, "")


def build_divisional_insights(pc: dict) -> list[DivisionalInsight]:
    """Generates rigorous, balanced predictive observations for all 9 key vargas."""
    insights: list[DivisionalInsight] = []
    codes = ["D1", "D2", "D3", "D7", "D9", "D10", "D12", "D24", "D30"]

    d1_lagna = _get_varga_lagna(pc, "D1")
    moon_sign = _get_varga_planet_sign(pc, "D1", "Moon")
    nakshatra = (pc.get("planets", {}).get("Moon", {}) or {}).get("nakshatra", "")

    for code in codes:
        meta = VARGA_META.get(code, {})
        v_lagna = _get_varga_lagna(pc, code)
        if not v_lagna:
            continue

        lagna_idx = sign_index(v_lagna)
        lord = SIGN_LORDS.get(v_lagna, "")
        lord_sign = _get_varga_planet_sign(pc, code, lord)
        lord_dig = get_dignity(lord, lord_sign) if (lord and lord_sign) else ""
        lord_house = ((sign_index(lord_sign) - lagna_idx) % 12 + 1) if (lord_sign and v_lagna) else 1

        strong_planets = []
        debilitated_planets = []
        trik_planets = []

        for p in PLANETS:
            ps = _get_varga_planet_sign(pc, code, p)
            if not ps:
                continue
            h = ((sign_index(ps) - lagna_idx) % 12 + 1)
            dig = get_dignity(p, ps)
            if dig in ("exalted", "moolatrikona", "own_sign"):
                strong_planets.append(f"{p} ({dig.replace('_', ' ').title()})")
            elif dig == "debilitated":
                debilitated_planets.append(p)
            if h in DUSTHANA:
                trik_planets.append(f"{p} (H{h})")

        is_lord_in_trik = lord_house in DUSTHANA
        is_lord_debilitated = lord_dig == "debilitated"

        if is_lord_in_trik or is_lord_debilitated or len(debilitated_planets) >= 2 or len(trik_planets) >= 3:
            strength = "weak" if (is_lord_in_trik and is_lord_debilitated) else "mixed"
        elif lord_dig in ("exalted", "moolatrikona", "own_sign") and not is_lord_in_trik and len(strong_planets) >= 2:
            strength = "strong"
        else:
            strength = "mixed"

        headline, prediction, remedy = _interpret_varga_balanced(
            code=code,
            v_lagna=v_lagna,
            lord=lord,
            lord_sign=lord_sign,
            lord_house=lord_house,
            lord_dig=lord_dig,
            strong_planets=strong_planets,
            debilitated_planets=debilitated_planets,
            trik_planets=trik_planets,
            strength=strength,
            d1_lagna=d1_lagna,
            moon_sign=moon_sign,
            nakshatra=nakshatra,
            pc=pc,
        )

        evidence_parts = [f"Ascendant: <b>{v_lagna}</b>"]
        if lord and lord_sign:
            dig_str = f" ({lord_dig.replace('_', ' ').title()})" if lord_dig else ""
            evidence_parts.append(f"Ruler: <b>{lord}</b> in {lord_sign} (House {lord_house}){dig_str}")
        if strong_planets:
            evidence_parts.append(f"Strengths: <b>{', '.join(strong_planets)}</b>")
        if is_lord_in_trik:
            evidence_parts.append(f"Friction Marker: <b>Ruler in House {lord_house} (Trik/Dusthana)</b>")
        if debilitated_planets:
            evidence_parts.append(f"Debilitated: <b>{', '.join(debilitated_planets)}</b>")

        insights.append(
            DivisionalInsight(
                code=code,
                name=meta.get("name", code),
                governs=meta.get("governs", ""),
                lagna_sign=v_lagna,
                lord=lord,
                lord_sign=lord_sign,
                lord_house=lord_house,
                lord_dignity=lord_dig,
                strength=strength,
                headline=headline,
                prediction=prediction,
                remedy=remedy,
                evidence=" · ".join(evidence_parts),
            )
        )

    return insights


PLANET_REMEDIES: dict[str, dict[str, str]] = {
    "Sun": {
        "debilitated": "Offer Surya Arghya (water with red kumkum in a copper vessel) to the rising Sun daily while reciting Aditya Hridaya Stotram. Chant the Gayatri Mantra (108x) on Sundays to restore vitality, confidence, and authority.",
        "dusthana": "Offer Surya Arghya at sunrise on Sundays and donate wheat or jaggery to elders or spiritual teachers to resolve authority friction.",
        "strengthen": "Chant Om Suryaya Namaha (108x) on Sunday mornings and practice Surya Namaskar at dawn to amplify solar vitality and executive stature.",
    },
    "Moon": {
        "debilitated": "Offer raw milk or water to a Shiva Lingam on Monday mornings while chanting Om Namah Shivaya (108x). Donate white rice or milk to underprivileged women to steady mental peace.",
        "dusthana": "Perform Jal Abhishek on Shiva Lingam on Mondays and meditate for 15 minutes to dissolve subconscious restlessness and emotional strain.",
        "strengthen": "Chant Om Som Somaya Namaha (108x) on Monday evenings to deepen intuitive perception and emotional balance.",
    },
    "Mars": {
        "debilitated": "Recite Hanuman Chalisa on Tuesdays. Donate red lentils (masoor dal) to laborers on Tuesday evenings to pacify impetuous friction and rebuild stamina.",
        "dusthana": "Recite Hanuman Ashtak on Tuesday mornings and light a jasmine or mustard oil lamp before Lord Hanuman to channel turbulent energy into disciplined executive action.",
        "strengthen": "Chant Om Bhaumaya Namaha (108x) on Tuesday mornings to harness decisive courage and project leadership.",
    },
    "Mercury": {
        "debilitated": "Recite Vishnu Sahasranama on Wednesday mornings and feed green grass or soaked moong dal to cows. Water a sacred Tulsi plant daily.",
        "dusthana": "Chant Om Budhaya Namaha (108x) on Wednesday mornings and donate green fruits or educational stationery to students to sharpen analytical clarity and communication.",
        "strengthen": "Chant the Budha Beej Mantra Om Bram Breem Braum Sah Budhaya Namah (108x) on Wednesdays to activate commercial genius and negotiation eloquence.",
    },
    "Jupiter": {
        "debilitated": "Chant the Guru Beej Mantra Om Gram Greem Graum Sah Gurave Namah (108x) on Thursday mornings. Donate yellow split chickpeas (chana dal) or bananas to spiritual seekers or temples.",
        "dusthana": "Recite Guru Stotram on Thursdays, offer yellow flowers to Lord Vishnu, and seek blessings from elders to dissolve career stagnation and timing delays.",
        "strengthen": "Chant Om Brihaspataye Namaha (108x) on Thursdays to magnify divine wisdom, financial stability, and dharma.",
    },
    "Venus": {
        "debilitated": "Chant the Shukra Beej Mantra Om Dram Dreem Draum Sah Shukraya Namah (108x) on Friday mornings. Donate white sweets, curd, or rice to underprivileged women on Fridays.",
        "dusthana": "Recite Sri Suktam or Durga Chalisa on Friday evenings to harmonize partnership dynamics and prevent financial dissipation.",
        "strengthen": "Chant Om Shum Shukraya Namaha (108x) on Fridays to enhance artistic appreciation, domestic harmony, and magnetic charm.",
    },
    "Saturn": {
        "debilitated": "Light a mustard oil lamp with black sesame seeds under a Peepal tree on Saturday evenings. Recite Dasharatha Shani Stotram and donate black umbrellas or footwear to the needy.",
        "dusthana": "Chant Om Sham Shanaishcharaya Namaha (108x) on Saturday evenings and feed stray black dogs or crows to remove chronic delays and karmic obstacles.",
        "strengthen": "Practice selfless service (seva) on Saturdays and maintain strict integrity to harness Saturnian perseverance and lasting achievements.",
    },
    "Rahu": {
        "debilitated": "Chant the Rahu Beej Mantra Om Bhram Bhreem Bhraum Sah Rahave Namah (108x) at sunset. Feed stray dogs and keep living spaces free of cluttered electronics.",
        "dusthana": "Recite Kalabhairava Ashtakam on Saturday evenings to dissolve illusions, anxiety, and unpredictable lifestyle upheavals.",
        "strengthen": "Donate coconut or blue cloth to cleaning staff on Saturdays to channel unorthodox innovation and rapid breakthroughs.",
    },
    "Ketu": {
        "debilitated": "Recite Ganesha Dwadashanama Stotram and offer fresh Durva grass to Lord Ganesha on Wednesdays. Donate blankets or food to stray animals.",
        "dusthana": "Chant Om Kem Ketave Namah (108x) on Tuesday mornings and practice daily Pranayama to convert detachment into profound spiritual clarity.",
        "strengthen": "Worship Lord Ganesha regularly to sharpen intuitive diagnostic insight and deep research depth.",
    },
}

VEDIC_VARGA_PREDICTIONS: dict[str, dict[str, Any]] = {
    "D1": {
        "title": "Birth Chart (D1) · Core Nature, Health & Life Path",
        "intro_kendra": "Vedic astrology indicates a <b>prominent, self-reliant, and active life path</b> with strong vitality and capacity to establish your own standing in society.",
        "intro_trikona": "Your birth chart carries <b>strong Poorva Punya (past meritorious karma)</b>, granting natural dharma, good intellect, and fortune that protects you in critical times.",
        "intro_upachaya": "Your life path follows <b>steady progressive growth (Upachaya)</b>, where success, reputation, and material stability compound as you grow older.",
        "intro_6th": "Your constitution builds strength through <b>overcoming challenges, competition, and hard work</b>, giving you sharp diagnostic ability and resilience.",
        "intro_8th": "Your chart signifies <b>profound longevity, deep intuitive insight, and major life turning points</b> that transform your personal destiny.",
        "intro_12th": "Your life orientation thrives through <b>spiritual detachment, reflective wisdom, or success in distant/foreign lands</b>.",
        "planet_gifts": {
            "Sun": "strong physical vitality, dignified self-respect, and natural leadership authority",
            "Moon": "a calm, adaptable mind, strong emotional memory, and widespread goodwill from people",
            "Mars": "fearless courage, executive decisiveness, and strong physical stamina",
            "Mercury": "sharp intellect, eloquent communication, and mastery in commerce or analytical fields",
            "Jupiter": "high ethical wisdom, noble character, and protection from elders and divine grace",
            "Venus": "cultured speech, artistic refinement, social charm, and domestic happiness",
            "Saturn": "stoic endurance, immense patience, and the ability to bear heavy responsibilities",
        },
        "planet_frictions": {
            "Sun": "occasional friction with superiors or fluctuations in vitality and self-confidence",
            "Moon": "mental restlessness, emotional mood swings, or sensitivity to environmental stress",
            "Mars": "impulsive actions, temper flare-ups, or minor cuts/burns and physical strain",
            "Mercury": "nervous over-thinking, analytical fatigue, or miscalculated communications",
            "Jupiter": "over-optimism leading to missed practical details or digestive sluggishness",
            "Venus": "over-indulgence in comfort or relationship misunderstandings",
            "Saturn": "feeling burdened by chronic delays, heavy duties, or periods of loneliness",
            "Rahu": "sudden mental illusions, ungrounded restlessness, or chasing volatile desires",
            "Ketu": "bouts of sudden disinterest in worldly affairs and a desire for isolation",
            "6th": "health vigilance regarding digestion/immunity and managing competitive friction",
            "8th": "sudden unexpected events or changes in plans requiring patience and calm",
            "12th": "sleep restlessness, unexpected expenses, or feeling drained in crowds",
        },
    },
    "D2": {
        "title": "Hora (D2) · Wealth, Prosperity & Assets",
        "intro_kendra": "Classical Hora analysis promises <b>active accumulation of wealth, tangible assets, and financial standing through direct self-effort</b>.",
        "intro_trikona": "Your wealth division is blessed with <b>Lakshmi Yoga potential</b>, indicating natural financial prosperity, auspicious earnings, and family comfort.",
        "intro_upachaya": "Your financial trajectory shows <b>continuous long-term accumulation</b>, where savings, property, and earnings expand steadily with time.",
        "intro_6th": "Wealth accumulation requires <b>careful debt management, strict budgeting, and overcoming financial competition</b> through service.",
        "intro_8th": "Your financial life experiences <b>sudden fluctuations, ancestral inheritances, or unexpected monetary shifts</b> that require solid liquid reserves.",
        "intro_12th": "Your highest financial earnings connect with <b>foreign sources, distant trade, institutional investments, or behind-the-scenes commerce</b>.",
        "planet_gifts": {
            "Sun": "steady income through government, administration, high-status positions, or family heritage",
            "Moon": "fluid financial liquidity, prosperity in consumer trade, and maternal asset support",
            "Mars": "lucrative gains through landed property, real estate, engineering, or bold commercial enterprise",
            "Mercury": "exceptional trade acumen, multi-source income, bookkeeping skill, and commercial profits",
            "Jupiter": "substantial wealth accumulation, sound financial counsel, and ethical asset preservation",
            "Venus": "luxury assets, vehicle prosperity, artistic commerce, and lucrative partnership gains",
            "Saturn": "long-term property retention, secure conservative investments, and enduring material stability",
        },
        "planet_frictions": {
            "Sun": "heavy expenditures to maintain social status or tax and regulatory penalties",
            "Moon": "fluctuating liquid cash flow and impulsive emotional spending",
            "Mars": "losses from hasty financial speculation, property disputes, or unexpected damages",
            "Mercury": "losses from poorly vetted contracts, loan guarantees, or calculation oversights",
            "Jupiter": "losses from lending money without security or overly generous financial commitments",
            "Venus": "high expenditures on luxury lifestyle, entertainment, or relationship upkeep",
            "Saturn": "cash flow tightness in early years and delays in realizing investment returns",
            "Rahu": "severe financial volatility from speculative trading, crypto, or get-rich-quick gambles",
            "Ketu": "negligence in tracking financial accounts or sudden disinterest in savings",
            "6th": "loan burdens or dispute-related expenses if financial agreements lack documentation",
            "8th": "sudden unexpected expenses or unannounced asset taxations requiring reserve funds",
            "12th": "hidden financial leakage, high recurring family overheads, or foreign currency loss",
        },
    },
    "D3": {
        "title": "Drekkana (D3) · Siblings, Courage & Endeavor",
        "intro_kendra": "The Drekkana chart signifies <b>high enterprise, direct courage (Parakrama), and the capacity to take bold, self-made initiatives</b>.",
        "intro_trikona": "Your endeavors are guided by <b>creative inspiration, high self-confidence, and auspicious support from younger associates</b>.",
        "intro_upachaya": "You possess <b>immense physical stamina and long-term perseverance</b>, where every struggle enhances your executive capacity.",
        "intro_6th": "Your success is forged through <b>tactical grit, overcoming rivalries, and triumphing over competitors through sheer discipline</b>.",
        "intro_8th": "You possess <b>hidden reserves of mental courage</b>, stepping up to take command during emergencies when others lose nerve.",
        "intro_12th": "Your efforts bear the greatest fruit in <b>independent, solitary projects or work executed away from your home territory</b>.",
        "planet_gifts": {
            "Sun": "commanding confidence, noble leadership, and respect from siblings and peers",
            "Moon": "adaptable initiative, cooperative teamwork, and helpful relations with siblings",
            "Mars": "fearless physical courage, athletic prowess, and unstoppable drive to finish goals",
            "Mercury": "brilliant technical skill, writing/communication talent, and strategic dexterity",
            "Jupiter": "righteous motivation, principled guidance, and harmonious sibling bonds",
            "Venus": "diplomatic negotiation, artistic/hand craft mastery, and pleasant peer relations",
            "Saturn": "iron patience, unmatched endurance, and structured project execution",
        },
        "planet_frictions": {
            "Sun": "ego clashes with brothers/peers or disputes over leadership credit",
            "Moon": "fluctuating motivation and enthusiasm depending heavily on emotional state",
            "Mars": "temper flare-ups, impatience, or disputes with brothers and close teammates",
            "Mercury": "over-analyzing steps or abandoning projects halfway due to scattered focus",
            "Jupiter": "over-committing to too many initiatives without practical follow-through",
            "Venus": "hesitation to take bold stands due to an excessive desire to avoid conflict",
            "Saturn": "heavy burdens placed on your shoulders by siblings or delayed recognition of effort",
            "Rahu": "misunderstandings with brothers or undertaking risky, ill-conceived ventures",
            "Ketu": "sudden loss of enthusiasm or emotional distance from siblings and childhood friends",
            "6th": "rivalries with associates or legal/contractual friction with partners",
            "8th": "sudden disruptions in projects or unexpected obstacles requiring tactical pivots",
            "12th": "feeling that your hard labor benefits others more than yourself",
        },
    },
    "D7": {
        "title": "Saptamsha (D7) · Progeny, Lineage & Children",
        "intro_kendra": "Classical Saptamsha analysis promises <b>active family fulfillment, continuity of lineage, and capable, well-established children</b>.",
        "intro_trikona": "Your chart carries <b>divine Santana Bhagyodaya (progeny fortune)</b>, blessing your children with good character, intelligence, and moral standing.",
        "intro_upachaya": "Your relationship with children and family legacy <b>flourishes and deepens with time</b>, bringing immense happiness in your later years.",
        "intro_6th": "Parenting requires <b>patient attention to children's routine habits, diet, and navigating competitive education cycles</b>.",
        "intro_8th": "Family dynamics involve <b>deep karmic lessons, requiring patience during children's major developmental transitions</b>.",
        "intro_12th": "Your lineage indicators suggest <b>children studying, settling, or traveling far from the ancestral home</b>.",
        "planet_gifts": {
            "Sun": "children who attain high social stature, noble character, and leadership capability",
            "Moon": "gentle, deeply affectionate children with strong moral upbringing and artistic talent",
            "Mars": "energetic, courageous, and athletic children who excel in technical or leadership fields",
            "Mercury": "exceptionally sharp, scholarly children with high academic aptitude and communication gifts",
            "Jupiter": "blessings of learned, virtuous progeny who bring honor, spiritual merit, and prosperity to the family",
            "Venus": "charming, well-mannered, and creative children with high aesthetic and social success",
            "Saturn": "responsible, humble, and hardworking children who achieve enduring stability",
        },
        "planet_frictions": {
            "Sun": "strong-willed headbutting or authority disagreements with children as they mature",
            "Moon": "excessive parental worry, over-protectiveness, or emotional sensitivities in the home",
            "Mars": "hyperactivity, minor sports injuries, or childhood temper flare-ups requiring sports channels",
            "Mercury": "distracted study focus, restlessness, or nervous habits in schooling years",
            "Jupiter": "high expectations that create subtle academic pressure on progeny",
            "Venus": "over-indulging children with material comforts at the expense of strict discipline",
            "Saturn": "delays in progeny milestones or generational communication gaps requiring patience",
            "Rahu": "children pursuing unconventional life choices or modern fields that surprise traditional elders",
            "Ketu": "children being highly introspective, independent, or living physically distant for education",
            "6th": "attentiveness needed toward seasonal childhood health and digestive immunity",
            "8th": "navigating unexpected family transitions or anxious phases during adolescent years",
            "12th": "coping with emotional distance as children relocate abroad for education or employment",
        },
    },
    "D9": {
        "title": "Navamsha (D9) · Marriage, Spouse & Post-Marriage Fortune",
        "intro_kendra": "The Navamsha promises <b>a supportive, capable life partner and an active, shared rise in social status after marriage</b>.",
        "intro_trikona": "Your marriage chart carries <b>auspicious Bhagyodaya (fortune activation through spouse)</b>, indicating deep dharmic harmony and mutual prosperity.",
        "intro_upachaya": "Marital harmony and prosperity <b>steadily strengthen and mature over time</b>, overcoming early adjustments.",
        "intro_6th": "Marital life requires <b>conscious tolerance and avoiding petty fault-finding</b>, learning to resolve domestic differences with patience.",
        "intro_8th": "Marriage brings <b>deep emotional transformation and joint financial restructuring</b>, requiring absolute honesty and mutual trust.",
        "intro_12th": "The partnership thrives through <b>shared spiritual values, private family peace, and opportunities connected with travel or foreign lands</b>.",
        "planet_gifts": {
            "Sun": "a dignified, high-principled spouse from an honorable background who elevates your standing",
            "Moon": "a gentle, compassionate, and deeply devoted spouse who creates a peaceful, nurturing home",
            "Mars": "an active, passionate, and protective spouse who fiercely champions your life goals",
            "Mercury": "an intelligent, witty, and highly articulate spouse who provides brilliant practical counsel",
            "Jupiter": "a wise, virtuous, and spiritually grounded spouse who brings immense good fortune and family happiness",
            "Venus": "a loving, charming, and aesthetically refined spouse who brings great romance, beauty, and comfort",
            "Saturn": "a loyal, steadfast, and mature spouse who provides unwavering stability through all life storms",
        },
        "planet_frictions": {
            "Sun": "ego clashes, pride battles, or career competition between partners",
            "Moon": "hypersensitivity to spoken words, mood fluctuations, or emotional insecurity",
            "Mars": "heated arguments, impatience, or hasty reactions during stressful weeks",
            "Mercury": "over-analyzing emotional situations or using sharp, sarcastic speech during debates",
            "Jupiter": "unrealistic expectations of perfection or becoming overly moralistic with each other",
            "Venus": "romantic disillusionment if unrealistic expectations are placed on daily married life",
            "Saturn": "emotional reserve, slow verbal affection, or feeling heavy domestic responsibilities",
            "Rahu": "unconventional relationship dynamics or sudden outside misunderstandings that require clarity",
            "Ketu": "phases of emotional detachment or feeling distant even within the domestic sphere",
            "6th": "daily routine disagreements, in-law interference, or chore distribution disputes",
            "8th": "trust anxieties, sudden financial shifts with in-laws, or emotional secretiveness",
            "12th": "temporary physical separations due to career travel or intimacy misunderstandings",
        },
    },
    "D10": {
        "title": "Dashamsha (D10) · Career, Authority & Professional Karma",
        "intro_kendra": "The Dashamsha confirms <b>high vocational standing, executive responsibility, and leadership authority in your profession</b>.",
        "intro_trikona": "Your professional karma is blessed with <b>natural patronage, public recognition, and smooth upward mobility into influential roles</b>.",
        "intro_upachaya": "Your career follows an <b>ascending growth curve (Upachaya)</b>, where your highest professional honors and wealth manifest in mature years.",
        "intro_6th": "You excel in <b>demanding, high-competition environments</b>, excelling as a problem-solver, strategist, or operational leader.",
        "intro_8th": "Your career involves <b>strategic reinventions and major vocational transformations</b>, often rising to higher authority after sudden industry shifts.",
        "intro_12th": "Your greatest professional success lies in <b>multinational companies, foreign clients, research institutions, or remote operations</b>.",
        "planet_gifts": {
            "Sun": "government favor, C-suite authority, high public prestige, and administrative command",
            "Moon": "outstanding public relations, commercial popularity, human resource leadership, and market instinct",
            "Mars": "formidable technical execution, project leadership, crisis management, and engineering authority",
            "Mercury": "commercial brilliance, financial analytics, negotiation mastery, and media/communication success",
            "Jupiter": "strategic advisory, legal/financial governance, corporate mentorship, and trusted executive status",
            "Venus": "creative brand leadership, client diplomacy, design elegance, and luxury/entertainment commerce",
            "Saturn": "large-scale organizational control, enduring corporate tenure, and unmatched operational mastery",
        },
        "planet_frictions": {
            "Sun": "friction with top management, bureaucratic hurdles, or political roadblocks during promotions",
            "Moon": "career instability caused by workplace atmosphere changes or emotional stress burnout",
            "Mars": "workplace disputes with peers, aggressive deadline pressure, or impetuous job changes",
            "Mercury": "miscommunicated project deliverables, contractual misunderstandings, or multitasking overload",
            "Jupiter": "underestimating office politics or relying on informal promises that fail to materialize",
            "Venus": "office favoritism politics or spending excessive capital on superficial branding",
            "Saturn": "delayed recognition, heavy workloads without immediate reward, and slow initial promotions",
            "Rahu": "sudden corporate restructurings, imposter syndrome, or navigating volatile industry disruptions",
            "Ketu": "sudden loss of motivation in conventional corporate ladders and desiring independent work",
            "6th": "workplace rivalries, team insubordination, or audit-related scrutiny",
            "8th": "sudden management shake-ups, corporate acquisitions, or unexpected role transfers",
            "12th": "feeling sidelined from central office politics or thriving best only when working autonomously",
        },
    },
    "D12": {
        "title": "Dwadashamsha (D12) · Parents & Ancestral Heritage",
        "intro_kendra": "The Dwadashamsha confirms <b>honorable family lineage, principled moral heritage, and strong backing from parents</b>.",
        "intro_trikona": "Your chart carries <b>rich ancestral blessings (Pitru Kripa)</b>, endowing you with inherited spiritual protection and good family standing.",
        "intro_upachaya": "Your appreciation of your family roots and bond with elders <b>deepens and matures with age</b>.",
        "intro_6th": "Family heritage carries <b>lessons of duty, overcoming past ancestral struggles, and resolving family responsibilities</b>.",
        "intro_8th": "Your lineage holds <b>deep ancestral heritage or generational property assets</b> that require prudent legal management.",
        "intro_12th": "Your destiny indicates <b>establishing your life and prospering away from your ancestral birthplace</b>.",
        "planet_gifts": {
            "Sun": "noble paternal lineage, strong moral grounding from father, and honorable ancestral reputation",
            "Moon": "deep maternal affection, emotional comfort, and auspicious blessings from mother's lineage",
            "Mars": "inherited land, ancestral real estate assets, and a family tradition of courage and enterprise",
            "Mercury": "inherited commercial acumen, scholarly family traditions, and intellectual guidance from elders",
            "Jupiter": "profound ancestral dharma, virtuous family reputation, and spiritual guidance from ancestors",
            "Venus": "cultured, harmonious home environment, aesthetic refinement, and domestic comforts from family",
            "Saturn": "family longevity, grounded traditional values, and enduring stability across generations",
        },
        "planet_frictions": {
            "Sun": "paternal health sensitivities or high parental expectations creating emotional burden",
            "Moon": "maternal health concerns, domestic worries, or emotional distance from family during stress",
            "Mars": "property disagreements with relatives or fiery temperaments within the extended family",
            "Mercury": "differing viewpoints with elders or conflicting advice regarding career decisions",
            "Jupiter": "ideological or philosophical differences with conservative family traditions",
            "Venus": "financial or lifestyle friction connected with extended family obligations",
            "Saturn": "heavy family duties falling on your shoulders or strict elder restrictions in youth",
            "Rahu": "feeling like an unconventional thinker or outlier within the traditional family tree",
            "Ketu": "physical relocation away from ancestral home or detachment from traditional rituals",
            "6th": "managing elderly family health requirements or resolving family land disputes",
            "8th": "sudden ancestral property transitions or resolving generational legal obligations",
            "12th": "living far from parents or feeling emotionally distant during foreign postings",
        },
    },
    "D24": {
        "title": "Chaturvimshamsha (D24) · Education & Intellectual Acumen",
        "intro_kendra": "The D24 promises <b>practical, applied mastery and high academic/technical competence</b> that directly converts into career success.",
        "intro_trikona": "You possess <b>Saraswati Yoga potential</b>, endowing you with exceptional conceptual synthesis, creative insight, and ease in higher learning.",
        "intro_upachaya": "Your specialized expertise and cognitive depth <b>expand exponentially with experience, turning you into a recognized subject matter authority</b>.",
        "intro_6th": "You excel in <b>rigorous, demanding technical fields</b> that require exhaustive diagnostic analysis, research, and flaw detection.",
        "intro_8th": "You possess a talent for <b>deep, investigative, and occult or specialized research</b>, uncovering insights that conventional scholars miss.",
        "intro_12th": "Your highest intellectual breakthroughs occur through <b>solitary, immersive study, research, or higher education in foreign/distant institutions</b>.",
        "planet_gifts": {
            "Sun": "commanding academic authority, original intellectual thought, and high prestige in educational institutions",
            "Moon": "sponge-like memory retention, creative writing eloquence, and rapid absorption of complex ideas",
            "Mars": "sharp mathematical logic, engineering/scientific acumen, and razor-sharp debate skills",
            "Mercury": "encyclopedic data retention, multilingual fluency, and flawless analytical clarity in trade and science",
            "Jupiter": "profound theoretical mastery, philosophical depth, higher degree success, and natural teaching ability",
            "Venus": "creative design brilliance, artistic sophistication, literary flair, and persuasive rhetoric",
            "Saturn": "enduring study discipline, capacity for arduous research, and deep technical mastery",
        },
        "planet_frictions": {
            "Sun": "intellectual dogmatism or difficulty accepting critique on academic research",
            "Moon": "exam anxiety, mood-dependent study focus, or mental saturation during intensive tests",
            "Mars": "intellectual impatience, arguing over technicalities, or rushing exam papers",
            "Mercury": "cognitive overload, overthinking simple problems, or scattered attention across too many courses",
            "Jupiter": "getting lost in abstract theory without finishing practical implementation",
            "Venus": "procrastination on demanding technical studies due to creative distractions",
            "Saturn": "slow initial comprehension or feeling imposter syndrome before reaching mastery",
            "Rahu": "study interruptions, intellectual restlessness, or chasing too many unrelated certifications",
            "Ketu": "bouts of intellectual apathy or losing interest in formal degree structures",
            "6th": "academic stress, competitive exam pressure, or study fatigue",
            "8th": "sudden changes in study streams or research roadblocks requiring pivot",
            "12th": "feeling isolated during intensive study periods or foreign education hurdles",
        },
    },
    "D30": {
        "title": "Trimsamsha (D30) · Resilience & Overcoming Adversity",
        "intro_kendra": "The Trimsamsha confirms <b>an active, warrior-like fighting spirit</b> that directly tackles adversities and defeats obstacles head-on.",
        "intro_trikona": "You possess <b>innate divine protection and strong psychological immunity</b>, allowing you to bounce back rapidly from life's setbacks.",
        "intro_upachaya": "Every crisis and obstacle you endure <b>permanently upgrades your endurance, mental toughness, and tactical mastery</b>.",
        "intro_6th": "Your constitution is built to <b>outlast chronic hurdles, health sensitivities, and competitive rivalries through strict discipline</b>.",
        "intro_8th": "You possess <b>phenomenal regenerative power</b>, capable of emerging victorious from life's most intense turning points.",
        "intro_12th": "Your ultimate healing and crisis resolution come through <b>spiritual surrender, meditation, and regular charitable remedies</b>.",
        "planet_gifts": {
            "Sun": "unbreakable core vitality, strong immune resilience, and sovereign inner courage",
            "Moon": "calm emotional composure, steady nervous system, and rapid psychological recovery",
            "Mars": "fearless crisis leadership, physical stamina, and an indomitable will to win",
            "Mercury": "rational problem-solving, mental agility under pressure, and tactical crisis navigation",
            "Jupiter": "divine protection, moral clarity in difficult times, and protection from chronic harms",
            "Venus": "grace under pressure, emotional healing, and peaceful resolution of disputes",
            "Saturn": "iron endurance, stoic tolerance for hardship, and unyielding perseverance",
        },
        "planet_frictions": {
            "Sun": "vitality drops during prolonged authority battles or pride-related stress",
            "Moon": "sleep disturbances, anxiety loops, or psychosomatic stress manifestations",
            "Mars": "inflammatory flare-ups, accidents from rushing, or internal anger burnout",
            "Mercury": "nervous exhaustion, obsessive worry, or digestive sensitivity to stress",
            "Jupiter": "liver sluggishness or complacency in health routines during busy periods",
            "Venus": "hormonal or kidney sensitivities, or turning to comfort food during stress",
            "Saturn": "chronic joint/back stiffness, fatigue, or lingering pessimism under heavy loads",
            "Rahu": "unexplainable phobias, health anxiety, or toxic environmental sensitivities",
            "Ketu": "sudden low-energy phases or difficult-to-diagnose seasonal sensitivities",
            "6th": "managing lifestyle inflammation, digestive discipline, and work-life balance",
            "8th": "sudden unpredictable stress spikes requiring strict emotional composure",
            "12th": "restless sleep, sensory overload, or energy depletion from excessive socializing",
        },
    },
}

ORDINALS = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", 6: "6th", 7: "7th", 8: "8th", 9: "9th", 10: "10th", 11: "11th", 12: "12th"}


VARGA_DOMAINS_CLEAN = {
    "D1": {"title": "Birth Chart (D1) · Core Nature, Health & Life Path", "focus": "your foundational constitution, vitality, and overall life orientation"},
    "D2": {"title": "Hora (D2) · Wealth, Prosperity & Assets", "focus": "wealth accumulation, asset building, and financial capacity"},
    "D3": {"title": "Drekkana (D3) · Siblings, Courage & Endeavor", "focus": "initiative, executive courage, and relationships with siblings and peers"},
    "D7": {"title": "Saptamsha (D7) · Progeny, Lineage & Children", "focus": "progeny prospects, family legacy, and children"},
    "D9": {"title": "Navamsha (D9) · Marriage, Spouse & Post-Marriage Fortune", "focus": "marriage, spouse compatibility, and lifelong partnership harmony"},
    "D10": {"title": "Dashamsha (D10) · Career, Authority & Professional Karma", "focus": "career trajectory, executive authority, and vocational status"},
    "D12": {"title": "Dwadashamsha (D12) · Parents & Ancestral Heritage", "focus": "ancestral foundation, parental heritage, and family lineage"},
    "D24": {"title": "Chaturvimshamsha (D24) · Education & Intellectual Acumen", "focus": "higher education, analytical expertise, and intellectual mastery"},
    "D30": {"title": "Trimsamsha (D30) · Resilience & Overcoming Adversity", "focus": "inner resilience, crisis recovery, and overcoming karmic obstacles"},
}


def _interpret_varga_balanced(
    code: str,
    v_lagna: str,
    lord: str,
    lord_sign: str,
    lord_house: int,
    lord_dig: str,
    strong_planets: list[str],
    debilitated_planets: list[str],
    trik_planets: list[str],
    strength: str,
    d1_lagna: str,
    moon_sign: str,
    nakshatra: str,
    pc: dict,
) -> tuple[str, str, str]:
    """Generates cohesive, non-contradictory Vedic confluence verdicts with targeted remedies."""
    meta = VARGA_DOMAINS_CLEAN.get(code, {"title": f"{code} Division", "focus": "this life area"})
    domain_title = meta["title"]
    domain_focus = meta["focus"]
    headline = f"{domain_title} ({v_lagna} Lagna)"

    h_ord = ORDINALS.get(lord_house, f"House {lord_house}")
    lord_dig_clean = lord_dig.replace("_", " ").title() if lord_dig else ""

    strong_names = {sp.split()[0] for sp in strong_planets}
    
    # Filter trik_planets to only genuinely afflicted planets (exclude planets that are exalted or in own sign!)
    genuine_trik_afflicted = []
    for tp in trik_planets:
        p_name = tp.split()[0]
        if p_name not in strong_names and p_name != lord:
            genuine_trik_afflicted.append(tp)

    reading_parts: list[str] = []

    # 1. STRUCTURAL CONFLUENCE & LAGNESHA ANALYSIS
    if lord_dig in ("exalted", "moolatrikona", "own_sign") and lord_house in DUSTHANA:
        reading_parts.append(
            f"Your {code} chart carries a powerful <b>Ucha / Swa-Kshetra Dusthana signature</b> with Lagna lord <b>{lord} {lord_dig_clean} in the {h_ord} House ({lord_sign})</b>. "
            f"Rather than creating an obstruction, this dignified placement acts as a protective shield, converting potential hurdles into profound depth, enduring resilience, and specialized mastery in {domain_focus}."
        )
    elif lord_dig in ("exalted", "moolatrikona", "own_sign"):
        reading_parts.append(
            f"Your {code} chart is strongly anchored by Lagna lord <b>{lord} {lord_dig_clean} in the {h_ord} House ({lord_sign})</b>, "
            f"establishing natural authority, structural stability, and high static promise for {domain_focus}."
        )
    elif lord_house in (1, 4, 7, 10):
        reading_parts.append(
            f"Your {code} chart establishes an <b>active, commanding foundation</b> with Lagna lord <b>{lord} placed in the {h_ord} Kendra house ({lord_sign})</b>, "
            f"driving direct initiative and visible progress in {domain_focus}."
        )
    elif lord_house in (5, 9):
        reading_parts.append(
            f"Your {code} chart is blessed with <b>auspicious Poorva Punya and dharmic merit</b> through Lagna lord <b>{lord} in the {h_ord} Trikona house ({lord_sign})</b>, "
            f"attracting natural patronage, good counsel, and smooth upward momentum in {domain_focus}."
        )
    elif lord_house in (2, 3, 11):
        reading_parts.append(
            f"Your {code} chart indicates <b>progressive compounding growth (Upachaya)</b> with Lagna lord <b>{lord} seated in the {h_ord} House ({lord_sign})</b>, "
            f"where results, stability, and recognition in {domain_focus} strengthen steadily over time through persistent effort."
        )
    elif lord_house in DUSTHANA:
        reading_parts.append(
            f"Your {code} chart indicates that {domain_focus} evolves through <b>perseverance and navigating periodic transitions</b>, "
            f"as Lagna lord <b>{lord} occupies the {h_ord} House ({lord_sign})</b>."
        )
    else:
        reading_parts.append(
            f"Your {code} chart provides the core blueprint for {domain_focus}, steered by Lagna lord <b>{lord} in the {h_ord} House ({lord_sign})</b>."
        )

    # 2. KEY BENEFIC FORTIFICATIONS (WHAT EMPOWERS YOU)
    other_strong = [sp for sp in strong_planets if sp.split()[0] != lord]
    if len(other_strong) >= 2:
        s1 = f"{other_strong[0]}"
        s2 = f"{other_strong[1]}"
        reading_parts.append(
            f"This division receives major positive fortification from <b>{s1}</b> and <b>{s2}</b>, "
            f"granting natural competence, protective grace, and enduring success."
        )
    elif len(other_strong) == 1:
        s1 = f"{other_strong[0]}"
        reading_parts.append(
            f"This division receives major positive fortification from <b>{s1}</b>, "
            f"granting natural competence, protective grace, and enduring strength."
        )

    # 3. GENUINE VULNERABILITIES & TIMING (NO CONTRADICTIONS)
    remedy_planet = None
    remedy_type = "strengthen"
    remedy_reason = ""

    d_info = VEDIC_VARGA_PREDICTIONS.get(code, VEDIC_VARGA_PREDICTIONS["D1"])
    d_frictions = d_info.get("planet_frictions", {})

    if debilitated_planets:
        p_deb = debilitated_planets[0]
        impact = d_frictions.get(p_deb, "friction and delays")
        reading_parts.append(
            f"The primary karmic challenge stems from <b>debilitated {p_deb}</b>. "
            f"During the <b>Mahadasha or Antardasha of {p_deb}</b>, exercise extra caution against {impact}."
        )
        remedy_planet = p_deb
        remedy_type = "debilitated"
        remedy_reason = f"To Pacify Debilitated {p_deb}"
    elif genuine_trik_afflicted:
        p_aff = genuine_trik_afflicted[0].split()[0]
        h_str = "Dusthana House"
        if "(H6)" in genuine_trik_afflicted[0]:
            h_str = "6th House"
        elif "(H8)" in genuine_trik_afflicted[0]:
            h_str = "8th House"
        elif "(H12)" in genuine_trik_afflicted[0]:
            h_str = "12th House"
        
        impact = d_frictions.get(p_aff, "unexpected pacing delays or friction")
        reading_parts.append(
            f"During the <b>Mahadasha or Antardasha of {p_aff} (placed in the {h_str})</b>, guard against {impact}, "
            f"maintaining steady discipline and clear communication."
        )
        remedy_planet = p_aff
        remedy_type = "dusthana"
        remedy_reason = f"To Harmonize {p_aff} in the {h_str}"
    elif lord_house in DUSTHANA and not lord_dig:
        impact = d_frictions.get(str(lord_house), "managing energy drainage and pacing yourself")
        reading_parts.append(
            f"During the <b>periods of Lagna lord {lord}</b>, focus on {impact}, as ruler placement in the {h_ord} house requires steady pacing."
        )
        remedy_planet = lord
        remedy_type = "dusthana"
        remedy_reason = f"To Harmonize {h_ord} House Ruler ({lord})"
    else:
        reading_parts.append(
            "Overall, this division carries clean astrological confluence with minimal malefic friction, allowing steady realization of your goals."
        )
        remedy_planet = list(strong_names)[0] if strong_names else lord
        remedy_type = "strengthen"
        remedy_reason = f"To Energize Favorable {remedy_planet}"

    prediction = " ".join(reading_parts)

    # 4. TARGETED REMEDY
    if remedy_planet and remedy_planet in PLANET_REMEDIES:
        rem_text = PLANET_REMEDIES[remedy_planet].get(remedy_type, PLANET_REMEDIES[remedy_planet]["strengthen"])
        remedy = f"<b>{remedy_reason}:</b> {rem_text}"
    else:
        remedy = "Maintain regular spiritual grounding and daily meditation."

    return headline, prediction, remedy


def get_108_snapshot_summary_paragraph(pc: dict) -> str:
    """Synthesizes the active classical rules into a single cohesive, flowing natural paragraph without author/book names."""
    try:
        from prediction108_rules import evaluate_all
        verdicts = evaluate_all(pc)
        hits = [v for v in verdicts if v.verdict == "HIT" and v.prediction and len(v.finding.strip()) > 15]

        key_hits = []
        priority_rule_nos = [1, 2, 3, 4, 15, 17, 21, 11]
        for r_no in priority_rule_nos:
            for v in hits:
                if v.no == r_no and v not in key_hits:
                    key_hits.append(v)
                    break

        if not key_hits:
            key_hits = hits[:4]

        sentences = []
        for v in key_hits:
            p = v.prediction.strip()
            if p:
                if not p.endswith(('.', '!', '?')):
                    p += '.'
                sentences.append(p)

        if not sentences:
            return (
                "Your birth chart carries the classical signatures of a fortunate birth where self-effort and disciplined focus "
                "consistently unlock key opportunities across major planetary cycles."
            )

        merged = " ".join(sentences[:4])
        return merged
    except Exception as exc:
        print(f"[divisional_profile] 108 summary error: {exc}", flush=True)
        return (
            "Your birth chart carries classical foundational strengths: your personal efforts find natural external backing, "
            "and leaning into key supportive planetary periods delivers long-term stability and fulfillment."
        )


def render_divisional_about_you_html(pc: dict, *, paid: bool = False) -> str:
    """Renders the comprehensive 9-divisional charts + 108 snapshot HTML block.

    Free tier:
      - Full cards for D1 (Self), D2 (Wealth), D3 (Siblings/Drive), D12 (Parents).
      - Remedy boxes blurred with lock overlay.
      - Locked teaser preview for D7 (Kids), D9 (Marriage), D10 (Career), D24 (Education), D30 (Hardships).
    Paid tier:
      - All 9 divisional cards rendered in full depth with strengths, friction points, and unblurred remedies.
    """
    insights = build_divisional_insights(pc)
    summary_108 = get_108_snapshot_summary_paragraph(pc)

    div_cards_html = []
    teaser_items = []

    for ins in insights:
        pill_cls = "up" if ins.strength == "strong" else "down" if ins.strength == "weak" else "mixed"
        pill_lbl = "Well Supported" if ins.strength == "strong" else "Needs Care" if ins.strength == "weak" else "Mixed / Active"
        border_color = "#1c6b45" if ins.strength == "strong" else "#a3341f" if ins.strength == "weak" else "#8a6a1f"

        is_free_allowed = ins.code in FREE_ALLOWED_VARGAS

        if paid or is_free_allowed:
            # Remedy display: Clear if paid, blurred with lock overlay if free
            if paid:
                remedy_box = (
                    f'  <div style="background:#f9f8f5;border-left:3px solid #8a6a1f;padding:8px 12px;border-radius:6px;margin:8px 0 10px;font-size:0.84rem;line-height:1.45;color:#4a453c;">\n'
                    f'    <b>Remedial Key &amp; Action:</b> {ins.remedy}\n'
                    f'  </div>\n'
                )
            else:
                remedy_box = (
                    f'  <div class="lock-wrap" style="margin:8px 0 10px;border-radius:8px;">\n'
                    f'    <div class="lock-blur" style="padding:8px 12px;font-size:0.84rem;line-height:1.45;">\n'
                    f'      <b>Remedial Key &amp; Action:</b> {ins.remedy}\n'
                    f'    </div>\n'
                    f'    <div class="lock-over">\n'
                    f'      <span class="lock-chip" style="font-size:0.65rem;padding:4px 10px;">🔒 Remedial Action in Full Reading</span>\n'
                    f'    </div>\n'
                    f'  </div>\n'
                )

            card = (
                f'<article class="card div-card" style="margin-bottom:16px;border-left:4px solid {border_color};background:#fff;border-radius:12px;padding:16px 18px;">\n'
                f'  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;">\n'
                f'    <span style="font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:700;color:#6a7080;">{html.escape(ins.code)} · {html.escape(ins.governs)}</span>\n'
                f'    <span class="pill {pill_cls}" style="font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:99px;">{pill_lbl}</span>\n'
                f'  </div>\n'
                f'  <h3 style="font-family:Georgia,serif;font-size:1.05rem;margin:4px 0 8px;color:#1f2430;font-weight:600;">{html.escape(ins.headline)}</h3>\n'
                f'  <p style="margin:0 0 10px;font-size:0.9rem;line-height:1.55;color:#2c3140;">{ins.prediction}</p>\n'
                f'{remedy_box}'
                f'  <div style="border-top:1px solid #eeeae3;padding-top:8px;font-size:0.75rem;color:#7a756c;line-height:1.4;">\n'
                f'    <b>Astrological Basis ({html.escape(ins.name)}):</b> {ins.evidence}\n'
                f'  </div>\n'
                f'</article>'
            )
            div_cards_html.append(card)
        else:
            meta = VARGA_META.get(ins.code, {})
            teaser_items.append(
                f'<li style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #e2ded5;">'
                f'  <div>'
                f'    <b style="font-size:0.9rem;color:#1f2430;">{html.escape(ins.code)} · {html.escape(meta.get("governs", ins.governs))}</b><br>'
                f'    <span style="font-size:0.78rem;color:#6a7080;">{html.escape(meta.get("desc", ""))}</span>'
                f'  </div>'
                f'  <span style="font-size:0.75rem;font-weight:700;color:#8a6a1f;background:#fbf6e4;padding:4px 10px;border-radius:99px;white-space:nowrap;margin-left:12px;">🔒 In Full Reading</span>'
                f'</li>'
            )

    teaser_html = ""
    if not paid and teaser_items:
        teaser_html = (
            f'<div class="card div-teaser-card" style="background:#fcfbf9;border:1px dashed #d5cfc4;border-radius:12px;padding:18px 20px;margin-bottom:16px;">\n'
            f'  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">\n'
            f'    <span style="font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:700;color:#7a4b18;">Specialized Life Divisions (D7, D9, D10, D24, D30)</span>\n'
            f'    <span style="font-size:0.68rem;font-weight:700;background:#ebdcc7;color:#6b4012;padding:2px 8px;border-radius:99px;">Available in Full Reading</span>\n'
            f'  </div>\n'
            f'  <p style="font-size:0.84rem;color:#5a554c;margin:0 0 12px;line-height:1.45;">\n'
            f'    Your remaining divisional charts map deep career karma (D10), marriage and soul purpose (D9), progeny dynamics (D7), intellectual mastery (D24), and overcoming life obstacles (D30):\n'
            f'  </p>\n'
            f'  <ul style="list-style:none;margin:0;padding:0;">\n'
            f'    {"".join(teaser_items)}\n'
            f'  </ul>\n'
            f'  <div style="text-align:center;margin-top:14px;">\n'
            f'    <a href="#unlock" data-unlock="1" style="display:inline-block;background:#16181d;color:#f7f5f1;font-size:0.82rem;font-weight:600;padding:8px 18px;border-radius:99px;text-decoration:none;">Unlock Complete Divisional Breakdown</a>\n'
            f'  </div>\n'
            f'</div>'
        )

    snap_summary_html = (
        f'<div class="card snapshot-summary-box" style="background:#fbfaf6;border:1px solid #e6e1d6;border-left:4px solid #b57c38;border-radius:12px;padding:16px 18px;margin-top:18px;">\n'
        f'  <div style="font-size:0.7rem;letter-spacing:0.14em;text-transform:uppercase;color:#7a4b18;font-weight:800;margin-bottom:8px;">Core Astrological Signatures &amp; In-Built Strengths</div>\n'
        f'  <p style="margin:0;font-size:0.9rem;color:#2c3140;line-height:1.6;font-family:Georgia,serif;">\n'
        f'    {summary_108}\n'
        f'  </p>\n'
        f'</div>'
    )

    intro_lead = (
        f'<p style="font-size:0.9rem;color:#5a554c;margin-bottom:14px;line-height:1.5;">\n'
        f'  A complete Vedic reading examines specialized <b>Divisional Charts</b> alongside the birth chart. '
        f'  Each division reveals both your natural strengths and the specific friction points that require conscious remedial attention:\n'
        f'</p>'
    )

    return (
        f'<div class="divisional-grid" style="margin-top:16px;">\n'
        f'  {intro_lead}\n'
        f'  {"".join(div_cards_html)}\n'
        f'  {teaser_html}\n'
        f'  {snap_summary_html}\n'
        f'</div>'
    )
