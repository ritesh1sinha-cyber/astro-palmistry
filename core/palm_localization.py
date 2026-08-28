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

FEATURE_NAMES_TE = {
    "Your hand shape": "Mee Chethi Aakaram (Hand Shape)",
    "Your thumb": "Mee Botana Velu (Thumb Structure)",
    "Thumb length": "Botana Velu Podavu (Thumb Length)",
    "Thumb angle": "Botana Velu Vangadam (Thumb Angle)",
    "Your ring finger": "Mee Ungarapu Velu (Ring Finger)",
    "Your index finger": "Mee Choopudu Velu (Tarjani Index Finger)",
    "Your middle finger": "Mee Madhyama Velu (Middle Finger)",
    "Your little finger": "Mee Chitikena Velu (Little Finger)",
    "Life line": "Jeevana Rekha (Life Line)",
    "Head line": "Masthishka Rekha (Head Line)",
    "Heart line": "Hrudaya Rekha (Heart Line)",
    "Fate line": "Bhagya Rekha (Fate Line)",
    "Sun line": "Surya Rekha (Sun Line)",
    "Health line": "Aarogya Rekha (Mercury Line)",
    "Marriage lines": "Vivaha Rekha (Marriage Line)",
    "Girdle of Venus": "Shukra Valayam (Girdle of Venus)",
    "Ring of Solomon": "Guru Mudrika (Ring of Solomon)",
    "Children lines": "Santhana Rekhalu (Children Lines)",
    "Travel lines": "Prayana Rekhalu (Travel Lines)",
    "Mount of Jupiter": "Guru Parvatham (Mount of Jupiter)",
    "Mount of Saturn": "Shani Parvatham (Mount of Saturn)",
    "Mount of Apollo": "Surya Parvatham (Mount of Sun/Apollo)",
    "Mount of Sun": "Surya Parvatham (Mount of Sun)",
    "Mount of Mercury": "Budha Parvatham (Mount of Mercury)",
    "Mount of Mars": "Kuja/Mangala Parvatham (Mount of Mars)",
    "Mount of Venus": "Shukra Parvatham (Mount of Venus)",
    "Mount of Luna": "Chandra Parvatham (Mount of Moon)",
    "Mount of Moon": "Chandra Parvatham (Mount of Moon)",
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

SIGN_TRANSLATIONS_TE = {
    "a square palm with long, slender fingers — an Air hand": "Chaukone aracheyi podavati velulatho — Air Hand (Vayu Tathvam)",
    "a square palm with sturdy, grounded fingers — an Earth hand": "Chaukone aracheyi balamaina, sthiramaina velulatho — Earth Hand (Prithvi Tathvam)",
    "a long palm with quick, energetic fingers — a Fire hand": "Podavu aracheyi churucoina velulatho — Fire Hand (Agni Tathvam)",
    "a long, elegant palm with sensitive fingers — a Water hand": "Podavu, komalamaina aracheyi sukshma velulatho — Water Hand (Jala Tathvam)",
    "a thumb with strong, determined upper phalanx": "Balamaina ichhashakthi (willpower) chupinche botana velu",
    "a thumb with a longer lower phalanx of reasoning": "Gahana tharkashakthi mariyu vishleshana chupinche botana velu",
    "a thumb with beautifully balanced will and logic sections": "Ichhashakthi (will) mariyu tharkam (logic) madhya chakkani samathoulyam unna Governing Thumb",
    "a long, commanding thumb": "Podavaina mariyu nayakathva lakshanalunna botana velu",
    "a receptive thumb": "Komalamaina mariyu lachila (receptive) botana velu",
    "a wide, open-set thumb": "Vishalamaina mariyu swatantra botana velu (wide-set thumb)",
    "a close-set, protective thumb": "Surakshithamaina mariyu jagrattha gala botana velu (close-set thumb)",
    "an index finger longer than your ring finger": "Ungarapu velu kante podavaina choopudu velu (Index finger)",
    "a ring finger longer than your index finger": "Choopudu velu kante podavaina ungarapu velu (Ring finger)",
    "runs deep, smooth and clearly etched": "Loothuga, spashtamga saguthunna jeevana rekha",
    "runs light or shallow": "Thelika leda saanthamaina jeevana rekha",
    "sweeps wide across the palm": "Aracheyi meeda vishalamga tiruguthunna jeevana rekha",
    "curves close to the thumb": "Botana veli daggaraga tiruguthunna jeevana rekha",
    "straight and long across the palm": "Nittaruga, podavuga unna masthishka rekha",
    "curves down towards the mount of moon": "Chandra parvatham vaipu vanagina kalpanashakthi gala masthishka rekha",
    "joined to the life line at the start": "Modatlo jeevana rekha tho kalisi unna jagrattha masthishka rekha",
    "separated from the life line at the start": "Jeevana rekha nunchi veruga modalaiah swatantra masthishka rekha",
    "curves smoothly up towards jupiter": "Guru parvatham vaipu cherina aadarshavanthamaina hrudaya rekha",
    "runs straight across towards saturn": "Shani parvatham vaipu sidhaga velthunna practical hrudaya rekha",
    "rises from the base towards saturn": "Aracheyi moolam nunchi Shani parvatham vaipu lechina sthira bhagya rekha",
    "rises from the middle of the palm": "Aracheyi madhya nunchi swayam nirmitamaina bhagya rekha",
    "rises from the mount of moon": "Chandra parvatham nunchi lechina prajala aadharana, kalpana aadhara bhagya rekha",
    "well developed and prominent": "Purtiga abhivruddhi chendi ubhina parvatham",
    "moderately developed": "Samathoulyamaina sthira parvatham",
    "flat or low": "Sapaduga unna parvatham",
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

MEANS_TRANSLATIONS_TE = {
    # Hand types
    "You are an intuitive thinker, strategist, and communicator": (
        "Meeru oka strategic thinker, thelivaina vicharavanthulu mariyu fluent communicator. "
        "Meeku kothadanam nerchukovadam, meaningful charchalu mariyu intellectual challenges ishtam. "
        "Routinework meeku tvaraga visugu thepisthundi; meeku spashtamaina lakshyam unappude poorthi energy tho pani chestharu."
    ),
    "You are practical, dependable, and deeply grounded": (
        "Meeru practical, nammadagina mariyu chala sthiramaina vyakthi. "
        "Meeru thos, parinamadayaka mariyu nammakamaina vishayala meeda aadharapadatharu. "
        "Migilina vaaru thadabadina sthithilo kuda meeru sthiramga undi badhyathalanu poorthi chestharu."
    ),
    "You are dynamic, instinctive, and driven by passion": (
        "Meeru utsahavanthulu, dynamic mariyu passion tho munduku velle vyakthi. "
        "Meeru utsahanga kotha projects modalu pedatharu mariyu itharulaku spoorthi istharu. "
        "Mee mukhya shakthi shuru cheyadam mariyu momentum thevadam."
    ),
    "You possess deep emotional intelligence and absorb the atmosphere": (
        "Meeku deep emotional intelligence undi mariyu chuttu unna vatavarananni tvaraga grahistharu. "
        "Mee intuition logic kante mundhe nijaanni thelusukuntundi."
    ),
    # Thumbs
    "Your willpower naturally leads the way": (
        "Mee ichhashakthi (willpower) eppudu munduntundi. Okasari nirnayam theesukunte, dridha sankalpamtho poorthi chestharu. "
        "Ee determination meeku kashtakalamlo kuda pedda vijayanni isthundi."
    ),
    "Your analytical mind sees solutions and risks well ahead": (
        "Mee vishleshana gnanam labhalu mariyu nashtalu renditini mundhe kanugontundi. "
        "Meeru prathi adugunu plan chestharu."
    ),
    "You possess what classical palmistry calls the 'Governing Thumb'": (
        "Samudrika Shastra prakaram meeku 'Governing Thumb' undi — aalochinchi planning cheyadam mariyu saraina samayaniki nirnayam theesukovatam samathoulyamga untundi."
    ),
    "Leadership and managerial responsibility come naturally to you": (
        "Nayakathvam mariyu leadership badhyathalu meeru naturally handle chestharu. Janalu mee daggaraku guidance kosam vastharu."
    ),
    "You lead with heart, empathy, and adaptability": (
        "Meeru hrudayam, samvedana mariyu adaptability tho mundukeltharu."
    ),
    "Generous, independent, and open-minded": (
        "Meeru udaaramaina, swatantra mariyu manchi manasu gala vyakthi."
    ),
    "Prudent and discreet": (
        "Meeru thelivaina mariyu discreet vyakthi. Mee plans mariyu bhavanalanu jagratthaga daachukuntaru."
    ),
    "You have a natural drive for autonomy": (
        "Meeku swatantrata, nayakathvam mariyu sontha standards set chesukune natural drive undi."
    ),
    "You possess creative flair, calculated risk appetite": (
        "Meeku creative pratibha, calculated risk theesukune samarthyam mariyu aakarshaneeya vyakthithvam unnayi."
    ),
    # Lines
    "You possess robust vitality and natural resilience": (
        "Meeku manchi shareeraka stamina, urja mariyu natural resilience unnai. Stress nunchi tvaraga recover avutharu."
    ),
    "Your constitution is sensitive and responsive": (
        "Mee shareeram mariyu manasu sensitive. Niyamitha aaharam, vishranthi meeku avashyakam."
    ),
    "You possess abundant vitality and a generous, hospitable nature": (
        "Meeku prachuramaina jeevana urja mariyu manchi apyayatha gala swabhavam unnai."
    ),
    "You conserve your energy carefully": (
        "Meeru mee urjanu jagratthaga kaapadukuntaru mariyu mukhyamaina panulapai concentrate chestharu."
    ),
    "Clear, structured, and pragmatic intellect": (
        "Mee dimaag spashtam, structured mariyu vyavaharikam. Nijala aadharamga direct nishkarshaku cherukuntaru."
    ),
    "Creative, lateral, and imaginative thinking": (
        "Mee aalochana kalpanasheelam mariyu creative. Kashtamaina samasyalaku kotha solutions kanugontaru."
    ),
    "Cautious, respectful of tradition, and deliberate in action": (
        "Meeru paddhathulu, sampradayam mariyu jagratthaku pradhanyatha istharu. Poorthi tayari thone adugu mundukestharu."
    ),
    "Independent, pioneering, and quick to form original views": (
        "Meeru swatantra aalochanavanthulu mariyu original thinker."
    ),
    "High ideals in relationships, loyalty, and deep devotion": (
        "Meeru sambandhalalo unna aadarshalu, nishtha mariyu nammakanni patistharu."
    ),
    "Pragmatic, steady, and realistic in emotional expression": (
        "Meeru bhavanalalo practical mariyu sthiramga untaru. Natakalu lekunda thos sambandhalaku pradhanyam istharu."
    ),
    "A self-directed, self-made career trajectory": (
        "Mee career swayam nirmitam mariyu swatantra kashtam tho nirminchabaduthundi. Mee prathibha meede mee gurthimpu untundi."
    ),
    "Early foundation and disciplined career progression": (
        "Mee career prarambha anushasanam mariyu kramashikshana tho sthirapaduthundi."
    ),
}

REMEDY_TRANSLATIONS_HI = {
    "Establish your core non-negotiables": "Mahatvapurna baatcheet se pehle apni core boundaries tay karein aur spashtata se vyakt karein.",
    "Focus your energy on completing one primary goal": "Ek samay mein ek mukhya lakshya poora karne par dhyan kendrit karein.",
    "Before major life commitments, intentionally seek out": "Bade faislo se pehle kisi anubhavi vyakti ki salah lena laabhkari rahega.",
    "Set a firm deadline for the decision itself": "Faisla lene ke liye ek pakki deadline tay karein aur tathya spasht hone par kadam uthayein.",
}

REMEDY_TRANSLATIONS_TE = {
    "Establish your core non-negotiables": "Mukhyamaina matladutalo mee core boundaries ni mundhe nischayinchukoni spashtamga cheppandi.",
    "Focus your energy on completing one primary goal": "Oka samayamlo oka mukhya lakshyam poorthi cheyadam meeda drushti pettandi.",
    "Before major life commitments, intentionally seek out": "Pedda nirnayala mundu anubhavagnula salah theesukovadam chala manchidi.",
    "Set a firm deadline for the decision itself": "Nirnayam theesukovadaniki oka pakka deadline pettukoni munduku saagandi.",
}

# ===========================================================================
# 2. Helper Translation Functions
# ===========================================================================

def translate_feature_name(feature: str, is_hinglish: bool = False, is_tenglish: bool = False) -> str:
    f_clean = str(feature or "").strip()
    if is_tenglish:
        return FEATURE_NAMES_TE.get(f_clean, f_clean)
    if is_hinglish:
        return FEATURE_NAMES_HI.get(f_clean, f_clean)
    return feature


def translate_sign_text(sign: str, is_hinglish: bool = False, is_tenglish: bool = False) -> str:
    if not (is_hinglish or is_tenglish):
        return sign
    s_clean = str(sign or "").strip()
    target_dict = SIGN_TRANSLATIONS_TE if is_tenglish else SIGN_TRANSLATIONS_HI
    for eng_k, loc_v in target_dict.items():
        if eng_k.lower() in s_clean.lower():
            return loc_v
    res = s_clean
    if is_hinglish:
        res = re.sub(r"\ba square palm with long, slender fingers\b", "chaukone hatheli lambi ungliyon ke sath", res, flags=re.I)
        res = re.sub(r"\ban Air hand\b", "Air Hand (Vayu Tatva)", res, flags=re.I)
        res = re.sub(r"\ban Earth hand\b", "Earth Hand (Prithvi Tatva)", res, flags=re.I)
        res = re.sub(r"\ba Fire hand\b", "Fire Hand (Agni Tatva)", res, flags=re.I)
        res = re.sub(r"\ba Water hand\b", "Water Hand (Jal Tatva)", res, flags=re.I)
    elif is_tenglish:
        res = re.sub(r"\ba square palm with long, slender fingers\b", "chaukone aracheyi podavati velulatho", res, flags=re.I)
        res = re.sub(r"\ban Air hand\b", "Air Hand (Vayu Tathvam)", res, flags=re.I)
        res = re.sub(r"\ban Earth hand\b", "Earth Hand (Prithvi Tathvam)", res, flags=re.I)
        res = re.sub(r"\ba Fire hand\b", "Fire Hand (Agni Tathvam)", res, flags=re.I)
        res = re.sub(r"\ba Water hand\b", "Water Hand (Jala Tathvam)", res, flags=re.I)
    return res


def translate_means_text(means: str, is_hinglish: bool = False, is_tenglish: bool = False) -> str:
    if not (is_hinglish or is_tenglish):
        return means
    m_clean = str(means or "").strip()
    target_dict = MEANS_TRANSLATIONS_TE if is_tenglish else MEANS_TRANSLATIONS_HI
    for eng_k, loc_v in target_dict.items():
        if eng_k.lower() in m_clean.lower():
            return loc_v
    return m_clean


def translate_remedy_text(remedy: str, is_hinglish: bool = False, is_tenglish: bool = False) -> str:
    if not (is_hinglish or is_tenglish):
        return remedy
    r_clean = str(remedy or "").strip()
    target_dict = REMEDY_TRANSLATIONS_TE if is_tenglish else REMEDY_TRANSLATIONS_HI
    for eng_k, loc_v in target_dict.items():
        if eng_k.lower() in r_clean.lower():
            return loc_v
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

VEDIC_ASPECT_TITLES_TE = {
    "Mind, Intellect & Temperament": ("Mano Sthiti, Thelivithetalu Mariyu Swabhavam", "Buddhi Mariyu Swabhavam"),
    "Career Trajectory, Status & Leadership": ("Udyogam, Career Mariyu Nayakathvam", "Career Mariyu Sthanam"),
    "Love, Marriage & Partner Compatibility": ("Prema, Vivaham Mariyu Jeevitha Bhagiswamy", "Sambandhalu Mariyu Dharmam"),
    "Wealth Accumulation & Financial Trajectory": ("Dhana Sanchayam Mariyu Aarthika Sthiti", "Dhanam Mariyu Sampada"),
    "Health, Physical Vitality & Stamina": ("Aarogyam, Shareeraka Balam Mariyu Praana Shakthi", "Balam Mariyu Praana Shakthi"),
}

VEDIC_UPAYA_HEADINGS_HI = {
    "Mind & Intellect": "Vishesh Vedic Upay (Buddhi Aur Man)",
    "Career & Status": "Vishesh Vedic Upay (Career Aur Pratishtha)",
    "Harmony & Partnership": "Vishesh Vedic Upay (Vivah Aur Sambandh)",
    "Wealth & Abundance": "Vishesh Vedic Upay (Dhan Aur Samriddhi)",
    "Health & Vitality": "Vishesh Vedic Upay (Swasthya Aur Urja)",
}

VEDIC_UPAYA_HEADINGS_TE = {
    "Mind & Intellect": "Prathyeka Vedic Upayam (Mano Sthiti & Buddhi):",
    "Career & Status": "Prathyeka Vedic Upayam (Career & Nayakathvam):",
    "Harmony & Partnership": "Prathyeka Vedic Upayam (Vivaham & Sambandhalu):",
    "Wealth & Abundance": "Prathyeka Vedic Upayam (Dhana Sanchayam & Sampada):",
    "Health & Vitality": "Prathyeka Vedic Upayam (Aarogyam & Prana Shakthi):",
}

def localize_vedic_text(text: str, is_hinglish: bool = False, is_tenglish: bool = False) -> str:
    if not (is_hinglish or is_tenglish) or not text:
        return text
    t = text
    if is_tenglish:
        # Archetype & Hand Type
        t = re.sub(
            r"You carry an <b>Air Hand archetype</b>.*?(thrives on mental variety and analytical depth\.)",
            "Mee cheyi <b>Air Hand archetype (Vayu Tathvam)</b> (chaukone aracheyi podavati velulatho) — idi meeru oka <b>thelivaina, strategic thinker mariyu fluent communicator</b> ani chupisthundi.",
            t, flags=re.I | re.S
        )
        t = re.sub(
            r"You carry an <b>Earth Hand archetype</b>.*?(values tangible results and steady loyalty\.)",
            "Mee cheyi <b>Earth Hand archetype (Prithvi Tathvam)</b> (chaukone aracheyi balamaina velulatho) — idi meeru oka <b>practical, sthiramaina mariyu nammadagina vyakthi</b> ani chupisthundi.",
            t, flags=re.I | re.S
        )
        t = re.sub(
            r"You carry an <b>Fire Hand archetype</b>.*?(driven by passion, ambition, and bold initiative\.)",
            "Mee cheyi <b>Fire Hand archetype (Agni Tathvam)</b> (podavu aracheyi active velulatho) — idi meeru oka <b>urjawan, dynamic mariyu nayakathva lakshanalu unna vyakthi</b> ani chupisthundi.",
            t, flags=re.I | re.S
        )
        t = re.sub(
            r"You carry an <b>Water Hand archetype</b>.*?(with rich emotional perception\.)",
            "Mee cheyi <b>Water Hand archetype (Jala Tathvam)</b> (podavu, komalamaina aracheyi) — idi meeru oka <b>loothaina intuition, empathy mariyu creative manasu</b> unna vyakthi ani chupisthundi.",
            t, flags=re.I | re.S
        )
        # Thumb will vs logic
        t = re.sub(
            r"Your thumb maintains a <b>harmonious balance between will and reason</b>.*?(after thoughtful evaluation\.)",
            "Mee botana velu <b>ichhashakthi (will) mariyu tharkam (logic) madhya chakkani samathoulyam</b> chupisthundi — meeru aalochinchi dridha nirnayam theesukuntaru.",
            t, flags=re.I | re.S
        )
        t = re.sub(
            r"Your thumb reveals <b>strong will-driven determination</b>.*?(with unwavering focus\.)",
            "Mee botana velu <b>balamaina ichhashakthi mariyu dridha sankalpam</b> chupisthundi — anukunnadi sadhinchadaniki sthiramga nilabadatharu.",
            t, flags=re.I | re.S
        )
        t = re.sub(
            r"Your thumb reveals <b>methodical analytical discernment</b>.*?(with deliberate foresight\.)",
            "Mee botana velu <b>tharkika mariyu vishleshana gnanam</b> chupisthundi — prathi risk ni mundhe bhaanpinchi siddham avutharu.",
            t, flags=re.I | re.S
        )
        # Head line traits
        t = re.sub(
            r"Your head line reveals a <b>cautious, methodical mind</b>.*?(deliberate execution\.)?",
            "Mee masthishka rekha mee dimaag <b>jagrattha mariyu methodical</b> ga pani chesthundani chupisthundi.",
            t, flags=re.I | re.S
        )
        t = re.sub(
            r"Your head line reveals an <b>independent, highly practical intellect</b>.*?(objective clarity\.)?",
            "Mee masthishka rekha meeru oka <b>swatantra mariyu practical thinker</b> ani chupisthundi.",
            t, flags=re.I | re.S
        )
        # Mount sentences in archetype
        t = re.sub(
            r"Your <b>your Mount of Mercury</b> is prominently elevated.*?(sharp analytical problem-solving\.)?",
            "Mee active chethilo <b>Budha Parvatham (Mount of Mercury)</b> vikasinchindi — idi <b>vyaparika thelivithetalu, kushal communication mariyu negotiation</b> ku balam isthundi.",
            t, flags=re.I | re.S
        )
        t = re.sub(
            r"Your <b>your Mount of Venus</b> is also well-developed, adding warmth, vitality and affection\.",
            "Mee <b>Shukra Parvatham (Mount of Venus)</b> kuda baaga vikasinchindi, idi prema, aakarshana mariyu shariraka urjanu isthundi.",
            t, flags=re.I | re.S
        )
        t = re.sub(
            r"Your <b>your Mount of Jupiter</b> is prominently elevated.*?(meaningful influence\.)?",
            "Mee <b>Guru Parvatham (Mount of Jupiter)</b> vikasinchindi — idi <b>nayakathvam, gouravam mariyu unna aadarshalu</b> chupisthundi.",
            t, flags=re.I | re.S
        )
        t = re.sub(
            r"Your <b>your Mount of Saturn</b> is prominently elevated.*?(perseverance\.)?",
            "Mee <b>Shani Parvatham (Mount of Saturn)</b> vikasinchindi — idi <b>anushasanam, orpu mariyu kramashikshana</b> tho sthira vijayanni isthundi.",
            t, flags=re.I | re.S
        )
        t = re.sub(
            r"Your <b>your Mount of Apollo</b> is prominently elevated.*?(public impact\.)?",
            "Mee <b>Surya Parvatham (Mount of Sun/Apollo)</b> vikasinchindi — idi <b>creativity, gouravam mariyu keerti</b> ni isthundi.",
            t, flags=re.I | re.S
        )
        # Profession summary
        t = re.sub(
            r"Your fate line indicates a trajectory <b>self-directed and self-built</b>.*?(through personal mastery and grit\.)",
            "Mee bhagya rekha <b>swayam nirmitam mariyu swatantra trajectory</b> ni chupisthundi — mee career mee sontha krushi mariyu samarthyam tho sthirapaduthundi.",
            t, flags=re.I | re.S
        )
        t = re.sub(
            r"It ascends toward Saturn:\s*<b>steady, disciplined ascent</b>.*?leadership built through technical mastery and perseverance\.",
            "Idi Shani parvatham vaipu velthundi: <b>anushasanam mariyu sthira vikasam</b> — technical mastery mariyu orpu tho long-term leadership vasthundi.",
            t, flags=re.I | re.S
        )
        t = re.sub(
            r"Your active hand's key vocational anchor is a prominent Mount of Mercury.*?naturally favoring <b>commerce, strategic advisory, technology, and communication</b>",
            "Mee active chethi mukhya karyesh anchor vikasinchina Budha Parvatham, idi <b>vyaparam, strategic advisory, technology mariyu communication</b> ku sahajanga anukoolam.",
            t, flags=re.I | re.S
        )
        t = re.sub(
            r"A supporting Sun line confirms that <b>merit-based recognition and professional authority</b> build progressively around your core accomplishments\.",
            "Sahayak Surya rekha <b>yogyatha-aadhara gouravam mariyu authority</b> mee vijayalatho paatu kramamga peruguthundani spashtam chesthundi.",
            t, flags=re.I | re.S
        )
        # Marriage summary
        t = re.sub(
            r"Your heart line reflects.*?<b>emotional integrity and enduring loyalty</b>.*?deeply devoted partner\.",
            "Mee hrudaya rekha <b>bhavana imandari mariyu nishtha</b> ni chupisthundi — meeru sambandhalalo loothaina anubandham korukuntaru.",
            t, flags=re.I | re.S
        )
        t = re.sub(
            r"A full Mount of Venus amplifies.*?<b>warmth, affection, and domestic vitality</b>\.",
            "Vikasinchina Shukra Parvatham mee parivarika jeevithamlo <b>prema, aakarshana mariyu shanti</b> ni penchuthundi.",
            t, flags=re.I | re.S
        )
        # Wealth summary
        t = re.sub(
            r"Your palm indicates a financial profile governed by.*?<b>strategic enterprise and steady accumulation</b>\.",
            "Mee aracheyi mee aarthika profile <b>strategic vyaparam mariyu kramika dhana sanchayam</b> tho nirdharinchabaduthundani chupisthundi.",
            t, flags=re.I | re.S
        )
        t = re.sub(
            r"A well-defined fate line combined with active commercial mounts confirms that <b>wealth grows in direct proportion to your specialized mastery</b>\.",
            "Spashtamaina bhagya rekha mariyu vikasinchina vyaparika parvathalu <b>dhanam mee vishesha prathibha mariyu krushi tho paatu peruguthundi</b> ani pushti chesthunnayi.",
            t, flags=re.I | re.S
        )
        # Health summary
        t = re.sub(
            r"Your life line and Mount of Venus indicate <b>steady baseline stamina, natural physical resilience, and strong vital recovery</b>.*?(sustained high-performance energy\.)",
            "Mee jeevana rekha mariyu Shukra Parvatham <b>sthira shareeraka stamina, natural resilience mariyu manchi recovery samarthyam</b> chupisthunnayi. Niyamitha dincharya mee urjanu kapaduthundi.",
            t, flags=re.I | re.S
        )
        return t

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


def localize_trait_item(trait_name: str, trait_text: str, is_hinglish: bool = False, is_tenglish: bool = False) -> tuple[str, str]:
    if not (is_hinglish or is_tenglish):
        return trait_name, trait_text
    
    t_map_hi = {
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

    t_map_te = {
        "strategic commerce and eloquence": ("Vyaparika Kushalatha Mariyu Vak-Chathuryam (Mercury)", "Meeru negotiation, kushal communication mariyu sharp analytical problem-solving lo nipunulu."),
        "courage and inner resilience (deliberate)": ("Dhairyam Mariyu Aantrika Sahasam (Mars)", "Meeru samayam mariyu sthitini batti nirnayam theesukoni vivadala nunchi duranga untaru."),
        "warmth, vitality and affection": ("Prema, Urja Mariyu Apyayatha (Venus)", "Meeru manchi aatmeeyatha, prema mariyu shariraka vitality tho unnaru."),
        "focused resolve": ("Ekagratha Mariyu Sankalpam (Head Line)", "Loothaina masthishka rekha meeku atoota concentration mariyu vishleshana stamina isthundi."),
        "vital warmth": ("Praana Urja Mariyu Aakarshana (Venus)", "Vikasinchina Shukra parvatham sahaja aakarshana, physical vigor mariyu udarathvaniki karanam."),
        "leadership and executive stature": ("Nayakathvam Mariyu Gouravam (Jupiter)", "Meeru sahajanga gouravam pondutharu mariyu unna aadarshalu kaligi untaru."),
        "discipline and steadfast perseverance": ("Anushasanam Mariyu Orpu (Saturn)", "Meeru badhyathalanu prashanthamga poorthi chesi sthira vijayanni sadhistharu."),
        "creative brilliance and personal magnetism": ("Kala Mariyu Aakarshana (Sun)", "Mee daggara creative prathibha mariyu aesthetic sense unnai."),
        "imagination and intuitive depth": ("Kalpana Mariyu Antardrishti (Moon)", "Meeru loothaina bhavanalu mariyu creative kalpanatho unnaru."),
        "loyal heart": ("Nammakamina Hrudayam (Heart Line)", "Loothaina hrudaya rekha sambandhalalo sthira nishtha mariyu nammakanni isthundi."),
        "adaptable nature": ("Lachila Swabhavam (Wavy Head Line)", "Meeru badalina paristhithulaku thaggattu sulabhamga adjust avutharu."),
    }

    t_low = str(trait_name or "").lower().strip()
    target_map = t_map_te if is_tenglish else t_map_hi
    for eng_k, (loc_title, loc_desc) in target_map.items():
        if eng_k in t_low:
            return loc_title, loc_desc
    return trait_name.title(), localize_vedic_text(trait_text, is_hinglish=is_hinglish, is_tenglish=is_tenglish)


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

MARK_NAMES_TE = {
    "fish": "Mathsya Chihnam (Fish Sign)",
    "trident": "Thrishula Chihnam (Trident Mark)",
    "star": "Thaara Chihnam (Star Mark)",
    "square": "Chathurasra Chihnam (Square Protection Mark)",
    "temple": "Gudi/Mandir Chihnam (Temple Sign)",
    "triangle": "Thribhuja Chihnam (Triangle Mark)",
    "cross": "Cross Chihnam (Guru Cross)",
}

def localize_mark(feature: str, sign: str, means: str, remedy: str, is_hinglish: bool = False, is_tenglish: bool = False) -> tuple[str, str, str, str]:
    if not (is_hinglish or is_tenglish):
        return feature, sign, means, remedy
    
    f_clean = feature
    target_names = MARK_NAMES_TE if is_tenglish else MARK_NAMES_HI
    for eng_k, loc_name in target_names.items():
        if eng_k in feature.lower():
            f_clean = loc_name
            break
    
    s_clean = translate_sign_text(sign, is_hinglish=is_hinglish, is_tenglish=is_tenglish)
    m_clean = translate_means_text(means, is_hinglish=is_hinglish, is_tenglish=is_tenglish)
    r_clean = translate_remedy_text(remedy, is_hinglish=is_hinglish, is_tenglish=is_tenglish)
    return f_clean, s_clean, m_clean, r_clean
