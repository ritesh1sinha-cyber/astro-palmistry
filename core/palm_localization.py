"""
palm_localization.py — Authentic Roman Hindi (Hinglish) localization for Palmistry reports.

Provides translations for:
  • Hand shapes, thumb, and finger archetypes
  • Major and minor palm lines (Life, Head, Heart, Fate, Sun, Mercury, Marriage)
  • Planetary mounts (Guru, Shani, Surya, Budh, Mangal, Shukra, Chandra)
  • Auspicious markings (Trishul, Matsya, Tara, Chaukone, Mandir, Tribhuj)
  • Vedic predictive profiles (Mind, Career, Marriage, Wealth, Health)
  • Daily Upayas, Mudras, and Mantras
  • Lived Timeline chapters and Innate vs. Made hand comparison
"""

from __future__ import annotations
import re
from typing import Any

# ===========================================================================
# 1. Hand Shape, Thumb & Finger Archetypes
# ===========================================================================

FEATURE_NAMES_HI = {
    "Your hand shape": "Aapka Haath Ka Aakar (Hand Shape)",
    "Your thumb": "Aapka Angutha (Thumb Structure)",
    "Thumb length": "Anguthe Ki Lambai (Thumb Length)",
    "Thumb angle": "Anguthe Ka Jhookav (Thumb Angle)",
    "Your ring finger": "Aapki Anamika Ungli (Ring Finger)",
    "Your index finger": "Aapki Tarjani Ungli (Index Finger)",
    "Your middle finger": "Aapki Madhyama Ungli (Middle Finger)",
    "Your little finger": "Aapki Kanishtha Ungli (Little Finger)",
    "Life line": "Jeevan Rekha (Life Line)",
    "Head line": "Mastishk Rekha (Head Line)",
    "Heart line": "Hridaya Rekha (Heart Line)",
    "Fate line": "Bhagya Rekha (Fate Line)",
    "Sun line": "Surya Rekha (Sun Line)",
    "Health line": "Swasthya Rekha (Mercury Line)",
    "Marriage lines": "Vivah Rekha (Marriage Line)",
    "Girdle of Venus": "Shukra Valaya (Girdle of Venus)",
    "Ring of Solomon": "Guru Mudrika (Ring of Solomon)",
    "Children lines": "Santan Rekha (Children Lines)",
    "Travel lines": "Yaatra Rekha (Travel Lines)",
    "Mount of Jupiter": "Guru Parvat (Mount of Jupiter)",
    "Mount of Saturn": "Shani Parvat (Mount of Saturn)",
    "Mount of Apollo": "Surya Parvat (Mount of Sun/Apollo)",
    "Mount of Sun": "Surya Parvat (Mount of Sun)",
    "Mount of Mercury": "Budh Parvat (Mount of Mercury)",
    "Mount of Mars": "Mangal Parvat (Mount of Mars)",
    "Mount of Venus": "Shukra Parvat (Mount of Venus)",
    "Mount of Luna": "Chandra Parvat (Mount of Moon)",
    "Mount of Moon": "Chandra Parvat (Mount of Moon)",
}

SIGN_TRANSLATIONS_HI = {
    "a square palm with long, slender fingers — an Air hand": "Chaukone hatheli lambi, patli ungliyon ke sath — Air Hand (Vayu Tatva)",
    "a square palm with sturdy, grounded fingers — an Earth hand": "Chaukone hatheli mazboot, sthir ungliyon ke sath — Earth Hand (Prithvi Tatva)",
    "a long palm with quick, energetic fingers — a Fire hand": "Lambi hatheli tezi se kaam karne wali ungliyon ke sath — Fire Hand (Agni Tatva)",
    "a long, elegant palm with sensitive fingers — a Water hand": "Lambi, komal hatheli samvedansheel ungliyon ke sath — Water Hand (Jal Tatva)",
    "a thumb with strong, determined upper phalanx": "Majboot ichhashakti (willpower) darshane wala balshali angutha",
    "a thumb with a longer lower phalanx of reasoning": "Gahan tarkshakti aur vishleshan darshane wala angutha",
    "a thumb with beautifully balanced will and logic sections": "Ichhashakti (will) aur tark (logic) ka sundar santulan darshane wala Governing Thumb",
    "a long, commanding thumb": "Lamba aur netritvashali angutha",
    "a receptive thumb": "Komal aur lachila (receptive) angutha",
    "a wide, open-set thumb": "Khula aur azaad vishal angutha (wide-set thumb)",
    "a close-set, protective thumb": "Surakshit aur savdhan angutha (close-set thumb)",
    "an index finger longer than your ring finger": "Anamika se lambi tarjani ungli (Index finger)",
    "a ring finger longer than your index finger": "Tarjani se lambi anamika ungli (Ring finger)",
    "runs deep, smooth and clearly etched": "Gehri, spasht aur bina rukavat ke chalti jeevan rekha",
    "runs light or shallow": "Halki ya barik jeevan rekha",
    "sweeps wide across the palm": "Hatheli par vishal gherav leti hui jeevan rekha",
    "curves close to the thumb": "Anguthe ke paas simti hui jeevan rekha",
    "straight and long across the palm": "Sidhi aur hatheli ke aar-paar lambi mastishk rekha",
    "curves down towards the mount of moon": "Chandra parvat ki or jhuki hui kalpanasheel mastishk rekha",
    "joined to the life line at the start": "Shuruat mein jeevan rekha se judi hui savdhan mastishk rekha",
    "separated from the life line at the start": "Jeevan rekha se alag shuru hone wali azaad mastishk rekha",
    "curves smoothly up towards jupiter": "Guru parvat ki or uthti hui aadarshwadi hridaya rekha",
    "runs straight across towards saturn": "Shani parvat ki or sidhi jati hui practical hridaya rekha",
    "rises from the base towards saturn": "Hatheli ke aadhar se Shani parvat ki or uthti hui sthir bhagya rekha",
    "rises from the middle of the palm": "Hatheli ke beech (mid-palm) se swayam nirmit bhagya rekha",
    "rises from the mount of moon": "Chandra parvat se uthti hui janta aur kalpana se judi bhagya rekha",
    "well developed and prominent": "Purna viksit aur ubhra hua parvat",
    "moderately developed": "Santulit aur sthir parvat",
    "flat or low": "Sapat ya kam ubhra hua parvat",
}

MEANS_TRANSLATIONS_HI = {
    # Hand types
    "You are an intuitive thinker, strategist, and communicator": (
        "Aap ek strategic thinker, vicharsheel aur fluent communicator hain. "
        "Aapko nayi baatein seekhna, meaningful charcha aur intellectual challenges pasand aate hain. "
        "Monotony ya bina karan ka routine kaam aapko jaldi thaka deta hai; aapko kisi bhi kaam mein judne se pehle spasht uddeshya chahiye."
    ),
    "You are practical, dependable, and deeply grounded": (
        "Aap vyavaharik, vishwasniya aur behad sthir vyakti hain. "
        "Aap thos, parinaamdayak aur bharosemand cheezon par vishwas karte hain. "
        "Jahan baaki log chaos mein pareshan ho jate hain, wahan aap sthir rehkar jimmedariyon ko antim parinaam tak pahunchate hain."
    ),
    "You are dynamic, instinctive, and driven by passion": (
        "Aap urjawan, dynamic aur junoon se aage badhne wale vyakti hain. "
        "Aap utsah ke sath naye projects shuru karte hain aur doosro ko inspire karte hain. "
        "Aapki mukhya shakti shuruat karna aur momentum banana hai."
    ),
    "You possess deep emotional intelligence and absorb the atmosphere": (
        "Aapke paas gehari bhavnatmak samajh (emotional intelligence) hai aur aap aaspas ke mahaul ko turant bhaap lete hain. "
        "Aapki intuition logic se pehle sach pehchan leti hai, jisse empathy aapki sabse badi takat banti hai."
    ),
    # Thumbs
    "Your willpower naturally leads the way": (
        "Aapki ichhashakti (willpower) hamesha aage rehti hai. Ek baar jo faisla aap le lete hain, use dridh sankalp ke sath poora karte hain. "
        "Yeh determination aapko mushkil sthitiyon mein bhi badi safalta dilati hai."
    ),
    "Your analytical mind sees solutions and risks well ahead": (
        "Aapka vishleshnatmak dimaag fayde aur nuksan dono ko pehle hi dekh leta hai. "
        "Aap har kadam ko plan karte hain, halanki kabhi-kabhi aakhiri action lene mein thoda extra time lag sakta hai."
    ),
    "You possess what classical palmistry calls the 'Governing Thumb'": (
        "Samudrika Shastra ke anusar aapke paas 'Governing Thumb' hai — jahan soch-samajhkar planning karna aur sahi samay par decisive action lena bilkul santulit rehta hai."
    ),
    "Leadership and managerial responsibility come naturally to you": (
        "Netritva aur leadership ki jimmedari aap naturally handle karte hain. Log aapse guidance lene aate hain aur aap pehal karke situation ko sambhalte hain."
    ),
    "You lead with heart, empathy, and adaptability": (
        "Aap dil, samvedansheelata aur adaptability ke sath aage badhte hain. Aap baat-cheet mein udar hain, halanki negotiations mein apne hiton ki suraksha rakhna zaroori hai."
    ),
    "Generous, independent, and open-minded": (
        "Aap udar, azaad khayal aur khule dil ke vyakti hain. Aap apna gyan, resources aur sahayata bina kisi sankoch ke sajha karte hain."
    ),
    "Prudent and discreet": (
        "Aap samajhdar aur discreet vyakti hain. Aap apne resources, yojanaon aur bhavnaon ko savdhani se surakshit rakhte hain."
    ),
    "You have a natural drive for autonomy": (
        "Aapko swatantrata, netritva aur apne standard tay karne ka natural drive hai. Jab aapko poori ownership milti hai, tab aap sabse shreshth parinaam dete hain."
    ),
    "You possess creative flair, calculated risk appetite": (
        "Aapke paas creative chamak, calculated risk lene ki kshamta aur aakarshak vyaktitva hai. Recognition aur meaningful impact aapko prerna dete hain."
    ),
    # Lines
    "You possess robust vitality and natural resilience": (
        "Aapke paas achhi sharirik urja, stamina aur natural resilience hai. Aap thakan aur stress se jaldi recover kar lete hain."
    ),
    "Your constitution is sensitive and responsive": (
        "Aapka sharir aur man sensitive hai. Niyamit aahar, samay par vishram aur dhyan aapki vitality ko banaye rakhte hain."
    ),
    "You possess abundant vitality and a generous, hospitable nature": (
        "Aapke paas prachur jeevan urja, mehmannawazi aur dil kholkar jeene ka swabhav hai."
    ),
    "You conserve your energy carefully": (
        "Aap apni urja ko savdhani se bachakar rakhte hain aur chuni hui prathmiktaon par hi concentrate karte hain."
    ),
    "Clear, structured, and pragmatic intellect": (
        "Aapka dimaag spasht, structured aur vyavaharik hai. Aap tathyon ke aadhar par bina kisi bhatkav ke seedhe nishkarsh par pahunchte hain."
    ),
    "Creative, lateral, and imaginative thinking": (
        "Aapki soch kalpanasheel aur creative hai. Aap mushkil samasyaon ke anokhe aur innovative hal nikalte hain."
    ),
    "Cautious, respectful of tradition, and deliberate in action": (
        "Aap niyam, parampara aur savdhani ko mahatva dete hain. Poori tayyari ke baad hi kadam aage badhate hain."
    ),
    "Independent, pioneering, and quick to form original views": (
        "Aap swabhav se azaad aur original thinker hain. Aap shuruat se hi apne vishwas par vishwas karte hain."
    ),
    "High ideals in relationships, loyalty, and deep devotion": (
        "Aap rishto mein uchha aadarsh, nishtha aur gehari samvedna rakhte hain. Aap dil se sath nibhate hain."
    ),
    "Pragmatic, steady, and realistic in emotional expression": (
        "Aap bhavnaon mein practical aur sthir hain. Vyarth ke drame se door rehkar thos rishto ko tarjih dete hain."
    ),
    "A self-directed, self-made career trajectory": (
        "Aapka career swayam nirmit aur swatantra mehnat se banta hai. Aap apni kshamta ke bal par pehchan banate hain."
    ),
    "Early foundation and disciplined career progression": (
        "Aapka career shuruati anushasan aur lagan se nirdharit hota hai jo samay ke sath sthirata lata hai."
    ),
}

REMEDY_TRANSLATIONS_HI = {
    "Establish your core non-negotiables": "Mahatvapurna baatcheet se pehle apni core boundaries tay karein aur spashtata se vyakt karein.",
    "Focus your energy on completing one primary goal": "Ek samay mein ek mukhya lakshya poora karne par dhyan kendrit karein.",
    "Before major life commitments, intentionally seek out": "Bade faislo se pehle kisi anubhavi vyakti ki salah lena laabhkari rahega.",
    "Set a firm deadline for the decision itself": "Faisla lene ke liye ek pakki deadline tay karein aur tathya spasht hone par kadam uthayein.",
}

# ===========================================================================
# 2. Helper Translation Functions
# ===========================================================================

def translate_feature_name(feature: str, is_hinglish: bool = False) -> str:
    if not is_hinglish:
        return feature
    f_clean = str(feature or "").strip()
    return FEATURE_NAMES_HI.get(f_clean, f_clean)


def translate_sign_text(sign: str, is_hinglish: bool = False) -> str:
    if not is_hinglish:
        return sign
    s_clean = str(sign or "").strip()
    for eng_k, hi_v in SIGN_TRANSLATIONS_HI.items():
        if eng_k.lower() in s_clean.lower():
            return hi_v
    # Common replacements
    res = s_clean
    res = re.sub(r"\ba square palm with long, slender fingers\b", "chaukone hatheli lambi ungliyon ke sath", res, flags=re.I)
    res = re.sub(r"\ban Air hand\b", "Air Hand (Vayu Tatva)", res, flags=re.I)
    res = re.sub(r"\ban Earth hand\b", "Earth Hand (Prithvi Tatva)", res, flags=re.I)
    res = re.sub(r"\ba Fire hand\b", "Fire Hand (Agni Tatva)", res, flags=re.I)
    res = re.sub(r"\ba Water hand\b", "Water Hand (Jal Tatva)", res, flags=re.I)
    res = re.sub(r"\ba thumb with beautifully balanced will and logic sections\b", "ichhashakti aur tark ka santulan darshane wala Governing Thumb", res, flags=re.I)
    res = re.sub(r"\ba receptive thumb\b", "komal aur lachila (receptive) angutha", res, flags=re.I)
    res = re.sub(r"\ba wide, open-set thumb\b", "khula aur swatantra vishal angutha", res, flags=re.I)
    res = re.sub(r"\ba ring finger longer than your index finger\b", "tarjani se lambi anamika ungli", res, flags=re.I)
    res = re.sub(r"\ban index finger longer than your ring finger\b", "anamika se lambi tarjani ungli", res, flags=re.I)
    return res


def translate_means_text(means: str, is_hinglish: bool = False) -> str:
    if not is_hinglish:
        return means
    m_clean = str(means or "").strip()
    for eng_k, hi_v in MEANS_TRANSLATIONS_HI.items():
        if eng_k.lower() in m_clean.lower():
            return hi_v
    return m_clean


def translate_remedy_text(remedy: str, is_hinglish: bool = False) -> str:
    if not is_hinglish:
        return remedy
    r_clean = str(remedy or "").strip()
    for eng_k, hi_v in REMEDY_TRANSLATIONS_HI.items():
        if eng_k.lower() in r_clean.lower():
            return hi_v
    return r_clean


# ===========================================================================
# 3. Vedic Life Profile Translations (Personality, Profession, Marriage, Wealth)
# ===========================================================================

VEDIC_ASPECT_TITLES_HI = {
    "Mind, Intellect & Temperament": ("Buddhi, Manasthiti Aur Swabhav", "Buddhi Aur Swabhav"),
    "Career Trajectory, Status & Leadership": ("Career, Pad-Pratishtha Aur Netritva", "Career Aur Karya-Kshetra"),
    "Love, Marriage & Partner Compatibility": ("Prem, Vivah Aur Jeevansathi Sambandh", "Sambandh Aur Dharma"),
    "Wealth Accumulation & Financial Trajectory": ("Dhan Sanchay Aur Aarthik Sthiti", "Dhan Aur Sampatti"),
    "Health, Physical Vitality & Stamina": ("Swasthya, Sharirik Urja Aur Prana Shakti", "Urja Aur Prana Shakti"),
}

VEDIC_UPAYA_HEADINGS_HI = {
    "Mind & Intellect": "Vishesh Vedic Upay (Buddhi Aur Man)",
    "Career & Status": "Vishesh Vedic Upay (Career Aur Pratishtha)",
    "Harmony & Partnership": "Vishesh Vedic Upay (Vivah Aur Sambandh)",
    "Wealth & Abundance": "Vishesh Vedic Upay (Dhan Aur Samriddhi)",
    "Health & Vitality": "Vishesh Vedic Upay (Swasthya Aur Urja)",
}

def localize_vedic_text(text: str, is_hinglish: bool = False) -> str:
    if not is_hinglish or not text:
        return text
    t = text
    # Archetype & Hand Type
    t = re.sub(
        r"You carry an <b>Air Hand archetype</b>.*?(thrives on mental variety and analytical depth\.)",
        "Aapka <b>Air Hand archetype (Vayu Tatva)</b> hai (chaukone hatheli lambi ungliyon ke sath) — jo darshata hai ki aap ek <b>buddhimaan, strategic thinker aur fluent communicator</b> hain jinko vishleshnatmak gahanata pasand hai.",
        t, flags=re.I | re.S
    )
    t = re.sub(
        r"You carry an <b>Earth Hand archetype</b>.*?(values tangible results and steady loyalty\.)",
        "Aapka <b>Earth Hand archetype (Prithvi Tatva)</b> hai (chaukone hatheli mazboot ungliyon ke sath) — jo darshata hai ki aap ek <b>vyavaharik, sthir aur bharosemand vyakti</b> hain jo thos parinaamo aur nishtha ko mahatva dete hain.",
        t, flags=re.I | re.S
    )
    t = re.sub(
        r"You carry an <b>Fire Hand archetype</b>.*?(driven by passion, ambition, and bold initiative\.)",
        "Aapka <b>Fire Hand archetype (Agni Tatva)</b> hai (lambi hatheli active ungliyon ke sath) — jo darshata hai ki aap ek <b>urjawan, dynamic aur pehal karne wale leader</b> hain jo utsah aur junoon se chalte hain.",
        t, flags=re.I | re.S
    )
    t = re.sub(
        r"You carry an <b>Water Hand archetype</b>.*?(with rich emotional perception\.)",
        "Aapka <b>Water Hand archetype (Jal Tatva)</b> hai (lambi, komal hatheli ke sath) — jo darshata hai ki aap ek <b>gehari intuition, empathy aur creative soul</b> wale vyakti hain.",
        t, flags=re.I | re.S
    )
    # Thumb will vs logic
    t = re.sub(
        r"Your thumb maintains a <b>harmonious balance between will and reason</b>.*?(after thoughtful evaluation\.)",
        "Aapka angutha <b>ichhashakti (will) aur tark (logic) ke sundar santulan</b> ko darshata hai — aap soch-vichar ke baad dridh faisla lete hain.",
        t, flags=re.I | re.S
    )
    t = re.sub(
        r"Your thumb reveals <b>strong will-driven determination</b>.*?(with unwavering focus\.)",
        "Aapka angutha <b>balshali ichhashakti aur dridh sankalp</b> ko darshata hai — aap jo tay karte hain, use poora karke hi dum lete hain.",
        t, flags=re.I | re.S
    )
    t = re.sub(
        r"Your thumb reveals <b>methodical analytical discernment</b>.*?(with deliberate foresight\.)",
        "Aapka angutha <b>tark aur vishleshnatmak dhyan</b> ko darshata hai — aap har risk ko pehle se bhaanp kar tayyari karte hain.",
        t, flags=re.I | re.S
    )
    # Head line traits
    t = re.sub(
        r"Your head line reveals a <b>cautious, methodical mind</b>.*?(deliberate execution\.)?",
        "Aapki mastishk rekha darshati hai ki aapka dimaag <b>savdhan aur methodical</b> hai jo anubhav aur abhyas ke sath aage badhta hai.",
        t, flags=re.I | re.S
    )
    t = re.sub(
        r"Your head line reveals an <b>independent, highly practical intellect</b>.*?(objective clarity\.)?",
        "Aapki mastishk rekha darshati hai ki aap ek <b>azaad aur vyavaharik thinker</b> hain jo spashtata ko prathmikta dete hain.",
        t, flags=re.I | re.S
    )
    # Mount sentences in archetype
    t = re.sub(
        r"Your <b>your Mount of Mercury</b> is prominently elevated.*?(sharp analytical problem-solving\.)?",
        "Aapke active haath par <b>Budh Parvat (Mount of Mercury)</b> viksit hai — jo <b>strategic vyapar, kushal baatcheet aur negotiation</b> ko mazbooti deta hai.",
        t, flags=re.I | re.S
    )
    t = re.sub(
        r"Your <b>your Mount of Venus</b> is also well-developed, adding warmth, vitality and affection\.",
        "Aapka <b>Shukra Parvat (Mount of Venus)</b> bhi achhi tarah viksit hai, jo aapko aakarshan, prem aur sharirik urja pradan karta hai.",
        t, flags=re.I | re.S
    )
    t = re.sub(
        r"Your <b>your Mount of Jupiter</b> is prominently elevated.*?(meaningful influence\.)?",
        "Aapka <b>Guru Parvat (Mount of Jupiter)</b> viksit hai — jo <b>leadership, samman aur uchha aadarshon</b> ko darshata hai.",
        t, flags=re.I | re.S
    )
    t = re.sub(
        r"Your <b>your Mount of Saturn</b> is prominently elevated.*?(perseverance\.)?",
        "Aapka <b>Shani Parvat (Mount of Saturn)</b> viksit hai — jo <b>anushasan, dheeraj aur lagan</b> se sthir safalta dilata hai.",
        t, flags=re.I | re.S
    )
    t = re.sub(
        r"Your <b>your Mount of Apollo</b> is prominently elevated.*?(public impact\.)?",
        "Aapka <b>Surya Parvat (Mount of Sun/Apollo)</b> viksit hai — jo <b>creativity, samman aur pehchan</b> deta hai.",
        t, flags=re.I | re.S
    )

    # Profession summary
    t = re.sub(
        r"Your fate line indicates a trajectory <b>self-directed and self-built</b>.*?(through personal mastery and grit\.)",
        "Aapki bhagya rekha <b>swayam nirmit aur swatantra trajectory</b> ko darshati hai — aapka career aapki apni lagan, kshamta aur mehnat se sthir hota hai.",
        t, flags=re.I | re.S
    )
    t = re.sub(
        r"It ascends toward Saturn:\s*<b>steady, disciplined ascent</b>.*?leadership built through technical mastery and perseverance\.",
        "Yeh Shani parvat ki or uthti hai: <b>anushasan aur sthir vikas</b> — jahan technical mastery aur dheeraj se long-term leadership banti hai.",
        t, flags=re.I | re.S
    )
    t = re.sub(
        r"Your active hand's key vocational anchor is a prominent Mount of Mercury.*?naturally favoring <b>commerce, strategic advisory, technology, and communication</b>",
        "Aapke active haath ka mukhya karyesh anchor viksit Budh Parvat hai, jo <b>vyapar, strategic advisory, technology aur communication</b> ko naturally favor karta hai.",
        t, flags=re.I | re.S
    )
    t = re.sub(
        r"A supporting Sun line confirms that <b>merit-based recognition and professional authority</b> build progressively around your core accomplishments\.",
        "Sahayak Surya rekha pushti karti hai ki <b>yogyata-adharit samman aur authority</b> aapki uplabdhiyon ke sath nirantar badhti hai.",
        t, flags=re.I | re.S
    )

    # Marriage summary
    t = re.sub(
        r"Your heart line reflects.*?<b>emotional integrity and enduring loyalty</b>.*?deeply devoted partner\.",
        "Aapki hridaya rekha <b>bhavnatmak imandari aur nishtha</b> ko darshati hai — aap rishto mein gehara sath aur vishwas chahte hain.",
        t, flags=re.I | re.S
    )
    t = re.sub(
        r"A full Mount of Venus amplifies.*?<b>warmth, affection, and domestic vitality</b>\.",
        "Viksit Shukra Parvat aapke parivarik jeevan mein <b>prem, aakarshan aur sauhard</b> ko badhata hai.",
        t, flags=re.I | re.S
    )

    # Wealth summary
    t = re.sub(
        r"Your palm indicates a financial profile governed by.*?<b>strategic enterprise and steady accumulation</b>\.",
        "Aapki hatheli darshati hai ki aapka aarthik profile <b>strategic vyapar aur kramik dhan sanchay</b> se nirdharit hota hai.",
        t, flags=re.I | re.S
    )
    t = re.sub(
        r"A well-defined fate line combined with active commercial mounts confirms that <b>wealth grows in direct proportion to your specialized mastery</b>\.",
        "Spasht bhagya rekha aur viksit vyaparik parvat pushti karte hain ki <b>dhan aapki vishesh yogyata aur mehnat ke sath badhta hai</b>.",
        t, flags=re.I | re.S
    )

    # Health summary
    t = re.sub(
        r"Your life line and Mount of Venus indicate <b>steady baseline stamina, natural physical resilience, and strong vital recovery</b>.*?(sustained high-performance energy\.)",
        "Aapki jeevan rekha aur Shukra Parvat <b>sthir sharirik stamina, natural resilience aur achhi recovery kshamta</b> ko darshate hain. Niyamit dhyan aur santulit routine aapki urja ko banaye rakhta hai.",
        t, flags=re.I | re.S
    )

    return t


def localize_trait_item(trait_name: str, trait_text: str, is_hinglish: bool = False) -> tuple[str, str]:
    if not is_hinglish:
        return trait_name, trait_text
    
    t_map = {
        "strategic commerce and eloquence": ("Vyaparik Kushalta Aur Vani (Mercury)", "Aap negotiation, kushal communication aur sharp analytical problem-solving mein nipun hain."),
        "courage and inner resilience (deliberate)": ("Dheeraj Aur Aantrik Sahas (Mars)", "Aap samay aur sthiti dekhkar nirnay lete hain aur vyarth ke takrav se bachte hain."),
        "warmth, vitality and affection": ("Prem, Urja Aur Sauhard (Venus)", "Aap sachhi aatmiyata, prem aur sharirik vitality se paripoorn hain."),
        "focused resolve": ("Ekagrata Aur Sankalp (Head Line)", "Gehri mastishk rekha aapko atoot concentration aur vishleshnatmak stamina pradan karti hai."),
        "vital warmth": ("Prana Urja Aur Aakarshan (Venus)", "Viksit Shukra parvat natural aakarshan, physical vigor aur udarta deta hai."),
        "leadership and executive stature": ("Netritva Aur Samman (Jupiter)", "Aap naturally aadar prapt karte hain aur uchha moral standards rakhte hain."),
        "discipline and steadfast perseverance": ("Anushasan Aur Lagan (Saturn)", "Aap jimmedariyon ko shanti se nibhate hain aur sthir safalta banate hain."),
        "creative brilliance and personal magnetism": ("Kala Aur Aakarshan (Sun)", "Aapke paas creative chamak aur aesthetic sense hai."),
        "imagination and intuitive depth": ("Kalpana Aur Antardrishti (Moon)", "Aap gehri bhavnaon aur creative kalpana se paripoorn hain."),
        "loyal heart": ("Wafadar Hridaya (Heart Line)", "Gehri hridaya rekha rishto mein pakki nishtha aur imandari deti hai."),
        "adaptable nature": ("Lachila Swabhav (Wavy Head Line)", "Aap badalti sthitiyon ke sath aasaani se dhal jaate hain."),
    }

    t_low = str(trait_name or "").lower().strip()
    for eng_k, (hi_title, hi_desc) in t_map.items():
        if eng_k in t_low:
            return hi_title, hi_desc
    return trait_name.title(), localize_vedic_text(trait_text, True)


# ===========================================================================
# 4. Special Marks Localization
# ===========================================================================

MARK_NAMES_HI = {
    "fish": "Matsya Chinh (Fish Sign)",
    "trident": "Trishul Chinh (Trident Mark)",
    "star": "Tara Chinh (Star Mark)",
    "square": "Chaukone Chinh (Square Protection Mark)",
    "temple": "Mandir Chinh (Temple Sign)",
    "triangle": "Tribhuj Chinh (Triangle Mark)",
    "cross": "Cross Mark (Brihaspati Cross)",
}

def localize_mark(feature: str, sign: str, means: str, remedy: str, is_hinglish: bool = False) -> tuple[str, str, str, str]:
    if not is_hinglish:
        return feature, sign, means, remedy
    
    f_clean = feature
    for eng_k, hi_name in MARK_NAMES_HI.items():
        if eng_k in feature.lower():
            f_clean = hi_name
            break
    
    s_clean = translate_sign_text(sign, True)
    m_clean = translate_means_text(means, True)
    r_clean = translate_remedy_text(remedy, True)
    return f_clean, s_clean, m_clean, r_clean
