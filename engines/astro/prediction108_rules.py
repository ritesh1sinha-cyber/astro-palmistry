#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Predictive Technique – 108 Rules engine.

Encodes the 108 chapters of "Saral Jyotish Part V – Astrology Simplified"
(predictivetechnique.pdf) as testable rules and checks a user's precomputed
chart (`pc`) against each one.

Chapters 1-83 are natal-chart techniques and are evaluated directly.
Chapters 84-108 are Saturn/Jupiter-transit and annual (Varshaphal) techniques;
they need a transit or annual chart, so they are reported as N/A with the exact
condition the reader should examine manually.

Each rule returns a `RuleVerdict` with a verdict of:
  HIT      – the rule's condition is fully present in the chart
  PARTIAL  – some (not all) of the rule's conditions are present
  NO       – the condition is not present
  NA       – needs a transit / annual chart (not auto-evaluated)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from astro_precompute import (
    SIGNS, SIGN_LORDS, DIGNITY_TABLE, FRIENDS, ENEMIES, FUNCTIONAL,
    NAK_TO_DASHA_LORD, sign_index, house_from_lagna, house_sign,
    get_dignity, get_functional_status,
)

# ── classifications ────────────────────────────────────────────────
KENDRA      = {1, 4, 7, 10}
TRIKONA     = {1, 5, 9}
DUSTHANA    = {6, 8, 12}          # trik houses
UPACHAYA    = {3, 6, 10, 11}
TRISHADAYA  = {3, 6, 11}
NAT_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
NAT_MALEFIC = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}

# Signs that are the exaltation sign of some planet (ch5)
EXALT_SIGN_PLANET = {DIGNITY_TABLE[p]["exalted"]: p for p in DIGNITY_TABLE}

# weekday lord (Python: Mon=0 .. Sun=6)
WEEKDAY_LORD = {0: "Moon", 1: "Mars", 2: "Mercury", 3: "Jupiter",
                4: "Venus", 5: "Saturn", 6: "Sun"}

# Special graha drishti (houses counted from the planet, 1-based; 7 = opposition)
SPECIAL_ASPECTS = {"Mars": [4, 7, 8], "Jupiter": [5, 7, 9], "Saturn": [3, 7, 10]}

# Prishtodaya (back-rising) signs – used in ch69
PRISHTODAYA = {"Aries", "Taurus", "Cancer", "Sagittarius", "Capricorn"}

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


# ── verdict container ───────────────────────────────────────────────
@dataclass
class RuleVerdict:
    no: int
    title: str
    category: str          # natal | transit | annual
    condition: str         # what the book rule says (the test)
    verdict: str           # HIT | PARTIAL | NO | NA
    finding: str           # chart-specific explanation
    prediction: str = ""   # human prediction when it hits


# ── basic accessors ─────────────────────────────────────────────────
def _pl(pc, name):
    return pc.get("planets", {}).get(name, {}) or {}

def psign(pc, name):
    return _pl(pc, name).get("sign", "")

def phouse(pc, name):
    d = _pl(pc, name)
    h = d.get("house")
    if h is None and d.get("sign"):
        h = house_from_lagna(d["sign"], lagna(pc))
    return h or 0

def pdig(pc, name):
    return _pl(pc, name).get("dignity") or get_dignity(name, psign(pc, name))

def pdeg(pc, name):
    return _pl(pc, name).get("degree_in_sign", 0.0) or 0.0

def pretro(pc, name):
    return bool(_pl(pc, name).get("retrograde"))

def pnak(pc, name):
    return _pl(pc, name).get("nakshatra", "")

def navsign(pc, name):
    return _pl(pc, name).get("navamsha_sign", "")

def lagna(pc):
    return pc.get("meta", {}).get("lagna_sign", "") or pc.get("lagna", {}).get("sign", "")

def lagna_lord(pc):
    return SIGN_LORDS.get(lagna(pc), "")

def along(pc, name):
    """Absolute sidereal longitude 0-360."""
    return sign_index(psign(pc, name)) * 30 + pdeg(pc, name)

def hlord(pc, house):
    """Planet lording house `house` (whole-sign from lagna)."""
    return SIGN_LORDS.get(house_sign(house, lagna(pc)), "")

def house_of_sign(pc, sign):
    return house_from_lagna(sign, lagna(pc)) if sign else 0

def occupants(pc, house):
    return [p for p in PLANETS if phouse(pc, p) == house]

def houses_lorded_by(pc, planet):
    return [h for h in range(1, 13) if hlord(pc, h) == planet]


# ── strength / nature helpers ───────────────────────────────────────
def moon_waxing(pc):
    return 0 < (along(pc, "Moon") - along(pc, "Sun")) % 360 < 180

def is_benefic(pc, p):
    if p in ("Jupiter", "Venus", "Mercury"):
        return True
    if p == "Moon":
        return moon_waxing(pc)
    return False

def is_malefic(pc, p):
    if p in ("Sun", "Mars", "Saturn", "Rahu", "Ketu"):
        return True
    if p == "Moon":
        return not moon_waxing(pc)
    return False

def friend(a, b):
    return b in FRIENDS.get(a, [])

def enemy(a, b):
    return b in ENEMIES.get(a, [])

WEAK_DIG = {"debilitated", "enemy_sign"}
STRONG_DIG = {"exalted", "moolatrikona", "own_sign"}

def is_strong(pc, p):
    return pdig(pc, p) in STRONG_DIG

def is_weak(pc, p):
    return pdig(pc, p) in WEAK_DIG

def afflicted(pc, p):
    """Planet conjunct or aspected by a natural malefic (not itself)."""
    for m in NAT_MALEFIC:
        if m == p:
            continue
        if psign(pc, m) and conj_or_aspect(pc, m, p):
            return True
    if is_weak(pc, p):
        return True
    return False


# ── aspect engine ───────────────────────────────────────────────────
def aspected_signs(planet, sign):
    if not sign:
        return set()
    offs = SPECIAL_ASPECTS.get(planet, [7])
    idx = sign_index(sign)
    return {SIGNS[(idx + off - 1) % 12] for off in offs}

def aspects_sign(pc, p_from, target_sign):
    return bool(target_sign) and target_sign in aspected_signs(p_from, psign(pc, p_from))

def aspects_planet(pc, p_from, p_to):
    return aspects_sign(pc, p_from, psign(pc, p_to))

def aspects_house(pc, p_from, house):
    return aspects_sign(pc, p_from, house_sign(house, lagna(pc)))

def conjunct(pc, a, b):
    sa, sb = psign(pc, a), psign(pc, b)
    return bool(sa) and sa == sb

def conj_or_aspect(pc, a, b):
    return conjunct(pc, a, b) or aspects_planet(pc, a, b) or aspects_planet(pc, b, a)

def planets_aspecting_sign(pc, sign, only=None):
    out = []
    for p in (only or PLANETS):
        if psign(pc, p) and aspects_sign(pc, p, sign):
            out.append(p)
    return out

def planets_in_sign(pc, sign):
    return [p for p in PLANETS if psign(pc, p) == sign]


def _ord(n):
    if not n:
        return "?"
    return {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", 6: "6th", 7: "7th",
            8: "8th", 9: "9th", 10: "10th", 11: "11th", 12: "12th"}.get(int(n), f"{n}th")

def _dig_word(d):
    return {"exalted": "exalted", "moolatrikona": "in moolatrikona", "own_sign": "in own sign",
            "friendly_sign": "in a friendly sign", "neutral_sign": "in a neutral sign",
            "enemy_sign": "in an enemy sign", "debilitated": "debilitated"}.get(d, d or "")


# ════════════════════════════════════════════════════════════════════
#  RULE METADATA – all 108 chapters
#  category: natal (evaluated) | transit | annual (reported N/A)
# ════════════════════════════════════════════════════════════════════
RULE_META: dict[int, dict] = {}

def _meta(no, title, category, condition, manual=""):
    RULE_META[no] = {"title": title, "category": category,
                     "condition": condition, "manual": manual}

# registry of checkers
CHECKERS: dict[int, object] = {}

def rule(no):
    def deco(fn):
        CHECKERS[no] = fn
        return fn
    return deco

def V(no, verdict, finding, prediction=""):
    m = RULE_META[no]
    return RuleVerdict(no, m["title"], m["category"], m["condition"],
                       verdict, finding, prediction)


# ── metadata for every chapter ──────────────────────────────────────
_meta(1,  "Day of Birth", "natal",
      "The weekday lord of birth should not be the 6th/8th lord; if so, illness in their mutual dasha. If the weekday lord sits in the 6th/8th the house it owns suffers; if exalted it gives fine results, if debilitated it troubles the house it occupies.")
_meta(2,  "Day or Night Birth (visible/invisible half)", "natal",
      "Day birth: 4+ planets (incl. Rahu/Ketu) in the visible half (houses 7-12) is auspicious. Night birth: 4+ planets in the invisible half (houses 1-6) gives the same result.")
_meta(3,  "Day or Night Birth (Moon support)", "natal",
      "For a day birth, Jupiter aspecting/conjunct the Moon is auspicious; for a night birth, Venus aspecting/conjunct the Moon is auspicious.")
_meta(4,  "Uttarayan Birth", "natal",
      "Birth while the Sun is in its northward course (Sun in Capricorn → Gemini) is auspicious; a waxing Moon adds strength.")
_meta(5,  "Sign Rising in Lagna", "natal",
      "If the rising sign is the exaltation sign of a planet, and that planet is aspected by a benefic from a kendra, a king is born.")
_meta(6,  "Lagna Lord 1 (ruler yoga)", "natal",
      "Person becomes a ruler when: a benefic is in lagna, the lagna lord sits in a kendra, and the lagna lord is conjunct/aspected by a friend — all three together.")
_meta(7,  "Lagna Lord 2 (trustworthiness)", "natal",
      "If the lagna lord is afflicted by/with a malefic (and not relieved by its own dispositor), the person is not fully trustworthy; the dispositor of the lagna lord with/aspecting it is a benefic connection.")
_meta(8,  "Lagna Lord & Moon Sign Lord", "natal",
      "Lagna lord and Moon-sign lord in mutual kendra (or conjunct), aspected by a common friend, makes a king; strongest if the two lords are mutual friends and aspect each other.")
_meta(9,  "Moon & Moon-Sign Lord (prosperity)", "natal",
      "When the Moon and the Moon-sign lord both occupy an upachaya house (3,6,10,11) from lagna, there is all-round prosperity.")
_meta(10, "Ninth Lord & Lagna Lord (between Moon)", "natal",
      "Lagna lord placed between the Moon and the 9th lord (in the arc joining them) is a fortunate placement for status and luck.")
_meta(11, "Nakshatra Lord of Karaka", "natal",
      "A planet in the 5th/7th from Moon or lagna empowers the karaka whose nakshatra it tenants; if that nakshatra lord is in 6/8/12 the significations weaken.")
_meta(12, "Planet in Own Sign in Kendra", "natal",
      "Even one planet in its own sign occupying a kendra from lagna or Moon (and unafflicted) raises the chart's power to deliver good results.")
_meta(13, "Trik Lords (suffering house)", "natal",
      "When a benefic occupies the 6th/8th from a trik (6/8/12) lord, the house so counted suffers (temporarily if a malefic instead) in the relevant dasha; the afflicted house must be occupied.")
_meta(14, "Lord of Exaltation/Debilitation Sign", "natal",
      "Only the jeeva (living) significations of the planet whose exaltation/debilitation sign is involved are affected — an important refinement used with divisional charts.")
_meta(15, "Trik Lord in its Other (own) Sign", "natal",
      "A trik (6/8/12) lord that owns two signs and sits in its OTHER own sign becomes strong and withholds the bad effects of the trik house.")
_meta(16, "Trik Lord gains strength", "natal",
      "Continuation of ch15: such a trik lord placed in its own (non-trik) sign gains strength and protects its significations.")
_meta(17, "Trishadaya Lords", "natal",
      "Lords of 3/6/11 (trishadaya) give good results when placed in an upachaya house (3,6,10,11); otherwise the result is weak (except under Vipreet Raj Yoga).")
_meta(18, "Conjunction of Lagna & Eighth Lord", "natal",
      "Conjunction of the lagna lord and the 8th lord (esp. in lagna/8th) bears on longevity and inheritance — favourable if unafflicted.")
_meta(19, "Eighth Lord (placement)", "natal",
      "The 8th lord tends to harm the house it sits in; but if it is in a friend's sign that house instead prospers. Its aspect also matters.")
_meta(20, "Eighth Lord harms a house", "natal",
      "The 8th lord is capable of harming the house of its placement (and the house it aspects); judge by friendship and affliction.")
_meta(21, "Planet in Eighth House", "natal",
      "A planet in the 8th aspects the 2nd (wealth). A friend of the 2nd lord there gives wealth; an enemy causes loss — though wealth comes with some calamity/difficulty.")
_meta(22, "Exchange of Lagna Lord & Eighth Lord", "natal",
      "Parivartana (sign exchange) of the lagna lord and the 8th lord gives inheritance and long life, provided the planets are unafflicted.")
_meta(23, "Lagna & Eighth Lord in own sign", "natal",
      "Lagna lord and 8th lord placed in their own signs assure long life (especially for Aries/Taurus where they are the same planet), if unafflicted.")
_meta(24, "Eighth Lord afflicted (lifespan)", "natal",
      "If the 8th lord is afflicted, it reduces the lifespan / vitality.")
_meta(25, "Lord of Exaltation/Debilitation Sign (status)", "natal",
      "When the lord of a planet's exaltation (and the planet) are strong, high status is born; more than one such placement multiplies status across fields.")
_meta(26, "Government Service", "natal",
      "When the 9th lord is in a trine (5th/9th) from lagna — or similarly placed in Navamsha — the person serves or is supported by the Government.")
_meta(27, "Ninth Lord (luxury)", "natal",
      "If the 9th lord occupies any trine FROM the 9th house (i.e. 9/1/5), the person is wealthy, builds a strong home and lives in luxury; in a trik house he loses everything.")
_meta(28, "Endless Suffering", "natal",
      "When the 10th lord is debilitated and a malefic sits in the 2nd house, the sufferings are endless (unless the debilitated 10th lord aspects the 10th).")
_meta(29, "No Suffering", "natal",
      "When a benefic is placed in the 2nd house, sufferings are manageable / few.")
_meta(30, "Rahu and Venus", "natal",
      "Rahu-Venus conjunction in the 4th or 8th can give unknown fears and harms conjugal happiness; in a kendra/trikona Rahu acts as that lord and can give good results.")
_meta(31, "House Lord & Debilitation Sign", "natal",
      "When a house lord is debilitated, that house suffers in line with the planet's natural significations and the house its dispositor occupies.")
_meta(32, "Yogda (Yogakaraka) Planet", "natal",
      "The Yogakaraka (and esp. the dispositor of the Moon acting as Yogda) strongly enhances the significations and wealth of the house it governs.")
_meta(33, "Ninth House (debilitated planet)", "natal",
      "A debilitated planet in the 9th gives problems and poverty in life — except where the debilitation is itself a yoga (e.g. 8th lord debilitated).")
_meta(34, "Civil Service", "natal",
      "A relation between a trine lord and a kendra lord (a Raj Yoga) focused in the 5th/10th — especially echoed in Navamsha/Dashamsha — gives civil-service / high office.")
_meta(35, "Richest in Clan", "natal",
      "A relation between the 5th lord and the 11th lord (trine + gains) makes one the richest in the clan; even being well placed from each other suffices.")
_meta(36, "Lives away from Birth Place", "natal",
      "Indications (movable signs / 4th-house affliction / 12th involvement of lagna or 4th lord) showing the person settles away from the birth place/country.")
_meta(37, "Rich (planet in 10th)", "natal",
      "When the 2nd or 11th lord (wealth/gains) is placed in the 10th house — the strongest kendra — the person becomes rich.")
_meta(38, "Tenth House (lord's house)", "natal",
      "Examine the house whose lord sits in the 10th; if that house is afflicted by a functional malefic the 10th-house results are boosted but mis-directed.")
_meta(39, "Obstacle in Marriage", "natal",
      "Affliction of the 7th house / 7th lord / Venus (malefic in 7th, or 7th lord in a dusthana) delays marriage even after it is fixed; the cause can be illness or mishap.")
_meta(40, "Exchange of Sun and Moon", "natal",
      "Parivartana (sign exchange) between the Sun and the Moon is a yoga for positive results.")
_meta(41, "Exchange of Lagna Lord & Moon Sign Lord", "natal",
      "Sign exchange between the lagna lord and the Moon-sign lord is a Raj Yoga giving high status (weak if the lagna lord is exalted/debilitated by it).")
_meta(42, "Abhijit Mahurat Birth", "natal",
      "Birth within ~2 ghati (≈48 min, i.e. about ±24 min) of local midday or midnight gives a king-like, undefeatable nature.")
_meta(43, "Second House (wealth)", "natal",
      "When the 2nd house / 2nd lord is strong (own/friendly sign, benefic support), the person is wealthy.")
_meta(44, "Wealth in Dasha of Nodes (Trikona)", "natal",
      "When Rahu/Ketu are in a trikona (or own/exaltation per Parashar/Phaladeepika tables), their dasha gives wealth.")
_meta(45, "Karma-Dharma relation (9th & 10th)", "natal",
      "A relation (conjunction/exchange/aspect) between the lords governing a house and the house of Karma strengthens that house — strongest reckoned from lagna (9th-10th Dharma-Karma yoga).")
_meta(46, "Dispositor of Nodes", "natal",
      "Rahu/Ketu give good results when their dispositor (the lord of their sign) is well placed — best if that dispositor is a trik lord who is also a trikona lord.")
_meta(47, "Fifth Navamsha", "natal",
      "Per the 5th-Navamsha table: when a planet's birth sign and its navamsha sign are in trine, it gives good results.")
_meta(48, "Dispositor of Rahu", "natal",
      "If the dispositor of Rahu is afflicted / in an enemy sign / in the 8th from Rahu, the house it signifies suffers.")
_meta(49, "Planet Exalted in Trik", "natal",
      "A planet exalted in a trik (6/8/12) house: its jeeva significations and the houses it owns suffer (malefic association aggravates).")
_meta(50, "Ruling power", "natal",
      "Specific exaltation/own-sign strength in a kendra/trikona (per ch49-50) confers ruling power.")
_meta(51, "Second Lord Exalted", "natal",
      "An exalted 2nd lord (possible for Aries, Gemini, Leo, Aquarius lagnas) gives wealth in its Vimshottari dasha.")
_meta(52, "Three Benefics", "natal",
      "Specific configuration of three benefics: when poorly placed (e.g. in trik houses) the person is poor; well placed they give wealth.")
_meta(53, "Three Malefics", "natal",
      "A configuration of three natural malefics (only natural malefics counted) shaping temperament and hardship.")
_meta(54, "Wicked", "natal",
      "Indicators of a deceitful nature: Mercury in Drekkana lagna/sign aspected by Moon, waning Moon and Mars in trik houses, lagna-lord afflictions.")
_meta(55, "Successful Lives", "natal",
      "Balance of malefic (material drive) and benefic (living/ethical) influence on the chart marks a materially successful life.")
_meta(56, "Big Inheritances", "natal",
      "Strong 4th/8th axis with benefic/own-sign lords (property + legacy) indicates large inheritances.")
_meta(57, "Subh Adhi Yoga", "natal",
      "Three benefics in the 6th/7th/8th from lagna (lagna Adhi) or from Moon (Chandra Adhi) make one famous, wealthy, healthy and legendary.")
_meta(58, "Papa Adhi Yoga", "natal",
      "Three malefics in the 6th/7th/8th from Moon form Papa Adhi Yoga (pure when the malefic is not the lagna lord and unrelated to any benefic).")
_meta(59, "Astrologer", "natal",
      "Ketu conjunct/aspected by Jupiter/Venus/Mercury and a trine lord, or 5th & 8th lords related, gives astrological/predictive power and learning.")
_meta(60, "Three Pairs", "natal",
      "Three planetary pairs in mutual relation (kendra/trine) bringing success in life.")
_meta(61, "Dasha of Eleventh Lord", "natal",
      "When the 11th lord is an enemy of lagna (or owns a bad second house), its dasha can bring harm of both its houses.")
_meta(62, "Karaka and Lord", "natal",
      "A house flourishes when its karaka (significator) and its lord are both strong and related; if the karaka is afflicted the result suffers.")
_meta(63, "Palai Yoga", "natal",
      "Venus in direct motion influencing the Sun (Jupiter in the 12th from Sun, etc.) gives Palai-yoga results; retrograde Venus weakens it.")
_meta(64, "Lords of 6th/7th/8th (from Moon)", "natal",
      "A potent Adhi-type rule using lords of 6/7/8 reckoned from the Moon/Sun (Sudarshan chakra); lords may be benefic or malefic.")
_meta(65, "Speech", "natal",
      "When Mercury is in an enemy sign and aspected by Jupiter, the speech is harsh/unconsidered; otherwise judge speech by Mercury's state.")
_meta(66, "Sixth House / Lord", "natal",
      "A strong 6th lord gives victory over enemies; a functional-malefic 6th lord brings out the adverse 6th-house significations (disease, debt, enemies).")
_meta(67, "Ashta Laxmi Yoga", "natal",
      "Specific benefic placements (Jupiter in a kendra, not Rahu in the 6th) generating the eight forms of Laxmi — happiness, wealth and long life.")
_meta(68, "Rahu with a Planet (Kartari)", "natal",
      "Rahu hemmed (kartari) by planets, or strongly placed with a planet, lets the person live like a king even in adversity.")
_meta(69, "Sun and Mercury (Budha-Aditya)", "natal",
      "Sun-Mercury conjunction gives intelligence/yoga; weak if Mercury is in a Prishtodaya sign or lacks a 9th/10th-lord link (then cunning and suffering).")
_meta(70, "Sun and Saturn Conjunction", "natal",
      "Sun-Saturn conjunction strains the father/authority and can give disease; judge the houses they own and occupy.")
_meta(71, "Venus from Mars", "natal",
      "Venus placed in a difficult relation from Mars affects conjugal happiness; Mars-Venus link gives victory over relatives/enemies but marital friction.")
_meta(72, "Tharai Yoga (kendra rule)", "natal",
      "The relevant planets placed in kendra from lagna give superior results, especially when they are kendra/trikona lords.")
_meta(73, "Honest Persons", "natal",
      "Benefic conjunction with Rahu in a good house, or saintly combinations, make an honest, fearless, long-lived and saint-like person.")
_meta(74, "Learned (Saturn)", "natal",
      "When Saturn (planet of concentration) influences the lagna, 2nd and 5th (the three learning factors) and is a benefic for the chart, the person is deeply learned.")
_meta(75, "Miserable lives", "natal",
      "A trik lord with only malefic relation (the malefic not being that trik lord, not debilitated, not aspected by the trik lord) gives a miserable life.")
_meta(76, "Tenth Lord", "natal",
      "Strength and placement of the 10th lord measure the mental + physical effort and success in career.")
_meta(77, "Sign in Tenth house", "natal",
      "When the planet that exalts in the 10th sign (the elevated planet for that sign) occupies the 10th from lagna or Moon, it lifts the career/status.")
_meta(78, "Wealthy (debilitated planet)", "natal",
      "A debilitated planet that gains Neecha-Bhanga (or is aspected/disposed favourably) becomes strong and gives wealth.")
_meta(79, "Ketu, Venus, Mars", "natal",
      "Ketu with Venus and Mars (by conjunction/Jaimini aspect) makes a king-like, respected life; in 6th/8th it gives high position with problems.")
_meta(80, "Two Benefics", "natal",
      "Two benefics in mutual relation strengthening their shared significations.")
_meta(81, "Nara Yoga", "natal",
      "A specific benefic-influence configuration (Nara yoga) for a sound body and progeny.")
_meta(82, "Good Yoga (Jupiter)", "natal",
      "Jupiter in a kendra with a benefic relation (and Rahu in the 6th) makes one honoured and never defeated.")
_meta(83, "Maha Shakti Yoga", "natal",
      "Maha-Shakti yoga (computed on longitudes, esp. seen in Navamsha) gives unshakable conviction and undefeatable resolve.")
# ── transit / annual (reported N/A) ─────────────────────────────────
_meta(84, "Big Change (Saturn transit)", "transit",
      "Major life change when Saturn transits the sign of the relevant planet (fully felt on the exact degree).",
      "Track Saturn's current transit sign/degree against the chart.")
_meta(85, "Transit of Saturn 1 (Navamsha)", "transit",
      "Take the Navamsha sign & lord; when transiting Saturn relates to the trine of that Navamsha sign/lord, the related event occurs.",
      "Needs current Saturn transit position.")
_meta(86, "Transit of Saturn 2 (house table)", "transit",
      "Each transited house signifies a set of relations; read events from Saturn's transit house per the book's table.",
      "Needs current Saturn transit position.")
_meta(87, "Transit of Saturn Favourable", "transit",
      "Saturn transit gives gains when supported by a favourable Chara dasha (dasha sign/lord with good aspects/argala, not in a trik house).",
      "Needs current Saturn transit + running Chara dasha.")
_meta(88, "Transit of Saturn Unfavourable", "transit",
      "Saturn transit is adverse when the running dasha sign-lord is in a trik house, etc.",
      "Needs current Saturn transit + running dasha.")
_meta(89, "Transit Saturn & Natal Jupiter 1", "transit",
      "Saturn's transit relation with natal Jupiter triggers specific events.",
      "Needs current Saturn transit position.")
_meta(90, "Transit Saturn & Natal Jupiter 2", "transit",
      "Continuation: Saturn-transit / natal-Jupiter timing technique.",
      "Needs current Saturn transit position.")
_meta(91, "Transit from Dwadamsha 1", "transit",
      "Using the 8th-lord axis (and its opposite) in the birth chart, a malefic transit on the axis times past-karma results.",
      "Needs current transit positions.")
_meta(92, "Transit from Dwadamsha 2", "transit",
      "Read the D12 (Dwadasamsha) sign/lord in the birth chart and watch the transit over them.",
      "Needs current transit positions.")
_meta(93, "Outstanding Event", "transit",
      "Transit alignment over the event-axis times an outstanding (possibly unfavourable) event.",
      "Needs current transit positions.")
_meta(94, "Disaster (64th Navamsha)", "transit",
      "Influence on the 64th Navamsha / Khara axis times a disaster (physical, and mental too if the 64th navamsha is hit).",
      "Needs current transit positions.")
_meta(95, "Unfortunate Event", "transit",
      "Malefic transit influence on the relevant sign times an unfortunate event; a benefic may avert it.",
      "Needs current transit positions.")
_meta(96, "Disease", "transit",
      "Transit / dasha influence on the 6th and 8th and their lords times disease.",
      "Needs current transit + running dasha.")
_meta(97, "Sade Sati", "transit",
      "Sade Sati runs while Saturn transits the 12th, 1st and 2nd from natal Moon (modified: 45° before to 45° after the Moon's longitude).",
      "Needs current Saturn transit position vs natal Moon.")
_meta(98, "Strength of Year Lord", "annual",
      "Rate the Year Lord's Panch-Vargiya strength: >15 extraordinary, 10-15 strong, 5-10 medium, 0-5 weak (>10 = good year).",
      "Needs the annual (Varshaphal) chart.")
_meta(99, "Same Sign (annual)", "annual",
      "A natal planet repeating its birth sign in the annual chart makes that year eventful (more so in exaltation/own sign).",
      "Needs the annual (Varshaphal) chart.")
_meta(100, "Annual Lagna Lord", "annual",
      "Judge the year from the annual lagna lord's birth-chart lordship, its associations/aspects in the annual chart, and Parashari yogas there.",
      "Needs the annual (Varshaphal) chart.")
_meta(101, "Birth Lagna Lord (annual)", "annual",
      "Assess the birth lagna lord by its Panch-Vargiya strength inside the annual chart.",
      "Needs the annual (Varshaphal) chart.")
_meta(102, "Raj Yoga (annual)", "annual",
      "A natal Raj Yoga fully fruits in a year only when the Raj-yoga planets and the annual lagna are strong in the annual chart.",
      "Needs the annual (Varshaphal) chart.")
_meta(103, "Tri Rashi Pati", "annual",
      "The Tri-Rashi-Pati (tri-sign lord) governs the year's tenor; its strength/affliction sets the result.",
      "Needs the annual (Varshaphal) chart.")
_meta(104, "Marriage (annual)", "annual",
      "Marriage year: annual lagna lord influences the 1-7 axis in the annual chart, Muntha lord the 1-7 axis in its Navamsha.",
      "Needs the annual (Varshaphal) chart.")
_meta(105, "Year Lord", "annual",
      "The Year Lord's house ownership decides gains/losses for the year.",
      "Needs the annual (Varshaphal) chart.")
_meta(106, "Tri Rashi Pati (afflicted)", "annual",
      "When the Tri-Rashi-Pati is afflicted, the year proves very bad.",
      "Needs the annual (Varshaphal) chart.")
_meta(107, "Muntha Lord", "annual",
      "The Muntha lord's placement and strength in the annual chart shape that year's main theme.",
      "Needs the annual (Varshaphal) chart.")
_meta(108, "Birth Lagna Lord (year closeness)", "annual",
      "The closeness/relation of the birth lagna lord to the annual lagna is important for the year.",
      "Needs the annual (Varshaphal) chart.")


# ════════════════════════════════════════════════════════════════════
#  CHECKERS – chapters 1-83
# ════════════════════════════════════════════════════════════════════

@rule(1)
def _c1(pc):
    dob = pc.get("meta", {}).get("dob", "")
    try:
        wd = date.fromisoformat(dob).weekday()
    except Exception:
        return V(1, "NA", "Birth date unavailable.")
    lord = WEEKDAY_LORD[wd]
    notes, hit = [], False
    owns = houses_lorded_by(pc, lord)
    if lord == hlord(pc, 6) or lord == hlord(pc, 8):
        hit = True
        notes.append(f"the weekday lord {lord} is also your 6th/8th lord — the classic illness flag in its dasha")
    h = phouse(pc, lord)
    if h in (6, 8):
        hit = True
        notes.append(f"{lord} sits in the {_ord(h)}, so the houses it owns ({', '.join(_ord(x) for x in owns) or '—'}) feel strain in its period")
    d = pdig(pc, lord)
    if d == "exalted":
        hit = True
        notes.append(f"{lord} is exalted — its dasha is set to give very good results")
    elif d == "debilitated":
        hit = True
        notes.append(f"{lord} is debilitated — it can trouble the {_ord(h)} house it occupies")
    base = f"You were born on a {['Mon','Tues','Wednes','Thurs','Fri','Satur','Sun'][wd]}day, so your weekday lord is {lord} ({_dig_word(d)}, {_ord(h)} house)."
    if hit:
        return V(1, "HIT", base + " " + "; ".join(notes) + ".",
                 f"Your destiny is tied to {lord}'s periods. " +
                 ("Lean into its dasha for opportunities. " if d == 'exalted' else "Keep health and the affected houses guarded during its dasha. "))
    return V(1, "NO", base + " It is neither the 6th/8th lord nor in 6/8, and not exalted/debilitated — no special weekday flag.")


@rule(2)
def _c2(pc):
    visible = sum(1 for p in PLANETS if phouse(pc, p) in (7, 8, 9, 10, 11, 12))
    invisible = 9 - visible
    sun_h = phouse(pc, "Sun")
    day_birth = sun_h in (7, 8, 9, 10, 11, 12)
    half = "day" if day_birth else "night"
    need_in = visible if day_birth else invisible
    where = "visible half (7-12)" if day_birth else "invisible half (1-6)"
    if need_in >= 4:
        return V(2, "HIT",
                 f"This is a {half} birth (Sun in the {_ord(sun_h)}). {need_in} planets sit in the {where} — the auspicious 4+ count is met.",
                 "The chart carries the in-built strength of a fortunate birth — your efforts tend to find backing and your potential delivers.")
    return V(2, "NO",
             f"This is a {half} birth (Sun in the {_ord(sun_h)}) but only {need_in} planets are in the {where} (need 4+). The success here is more earned than gifted.")


@rule(3)
def _c3(pc):
    sun_h = phouse(pc, "Sun")
    day_birth = sun_h in (7, 8, 9, 10, 11, 12)
    if day_birth:
        ok = conj_or_aspect(pc, "Jupiter", "Moon")
        who = "Jupiter"
    else:
        ok = conj_or_aspect(pc, "Venus", "Moon")
        who = "Venus"
    half = "day" if day_birth else "night"
    if ok:
        return V(3, "HIT",
                 f"This is a {half} birth and {who} aspects/joins the Moon — the prescribed support is present.",
                 f"Your mind ({who}'s grace on the Moon) stays steady and blessed, smoothing emotional and domestic life.")
    return V(3, "NO", f"This is a {half} birth but {who} does not aspect/join the Moon, so this particular support is absent.")


@rule(4)
def _c4(pc):
    s = psign(pc, "Sun")
    uttar = {"Capricorn", "Aquarius", "Pisces", "Aries", "Taurus", "Gemini"}
    if s in uttar:
        wax = moon_waxing(pc)
        return V(4, "HIT",
                 f"Your Sun is in {s} — within the Uttarayan (northward) arc Capricorn→Gemini." +
                 (" The Moon is also waxing, adding strength." if wax else " (The Moon is waning, so a touch less force.)"),
                 "Born in the months of the gods, you carry an in-built lift to rise high in life.")
    return V(4, "NO", f"Your Sun is in {s}, in the Dakshinayana (southward) arc — this auspicious Uttarayan flag does not apply.")


@rule(5)
def _c5(pc):
    lg = lagna(pc)
    planet = EXALT_SIGN_PLANET.get(lg)
    if not planet:
        return V(5, "NO", f"Your lagna {lg} is not the exaltation sign of any planet, so this 'king is born' rule does not apply.")
    # benefic aspecting that planet from a kendra
    for b in NAT_BENEFIC:
        if b == planet:
            continue
        if is_benefic(pc, b) and phouse(pc, b) in KENDRA and aspects_planet(pc, b, planet):
            return V(5, "HIT",
                     f"Your lagna {lg} is the exaltation sign of {planet}, and benefic {b} aspects {planet} from a kendra (the {_ord(phouse(pc,b))}).",
                     "A royal signature — leadership, authority and a commanding presence are promised by the rising sign itself.")
    return V(5, "PARTIAL",
             f"Your lagna {lg} is the exaltation sign of {planet}, but no benefic aspects {planet} from a kendra — the regal promise is only latent.")


@rule(6)
def _c6(pc):
    ll = lagna_lord(pc)
    cond1 = any(is_benefic(pc, p) and phouse(pc, p) == 1 for p in NAT_BENEFIC)
    cond2 = phouse(pc, ll) in KENDRA
    cond3 = any(friend(ll, f) and conj_or_aspect(pc, f, ll) for f in PLANETS if f != ll)
    met = sum([cond1, cond2, cond3])
    detail = (f"benefic in lagna: {'yes' if cond1 else 'no'}; "
              f"lagna lord {ll} in a kendra: {'yes ('+_ord(phouse(pc,ll))+')' if cond2 else 'no ('+_ord(phouse(pc,ll))+')'}; "
              f"{ll} conjunct/aspected by a friend: {'yes' if cond3 else 'no'}")
    if met == 3:
        return V(6, "HIT", "All three ruler conditions are met — " + detail + ".",
                 "A powerful leadership yoga: authority, command and the ability to rule your domain.")
    if met >= 1:
        return V(6, "PARTIAL", f"{met} of 3 ruler conditions are met — " + detail + ".",
                 "Partial leadership strength — you can rise to authority, though not the full 'ruler' promise.")
    return V(6, "NO", "None of the three ruler conditions are met — " + detail + ".")


@rule(7)
def _c7(pc):
    ll = lagna_lord(pc)
    disp = SIGN_LORDS.get(psign(pc, ll), "")
    relieved = disp and disp != ll and conj_or_aspect(pc, disp, ll)
    bad = [m for m in NAT_MALEFIC if m != ll and enemy(ll, m) and conj_or_aspect(pc, m, ll)]
    if bad and not relieved:
        return V(7, "HIT",
                 f"Your lagna lord {ll} is afflicted by enemy malefic(s) {', '.join(bad)} and its dispositor {disp or '—'} does not relieve it.",
                 "A caution on dependability under pressure — guard against impulsive or self-serving choices; the lagna lord is 'the doer'.")
    note = (f"its dispositor {disp} supports it" if relieved else "no enemy-malefic affliction on it")
    return V(7, "NO", f"Your lagna lord {ll} is not compromised ({note}) — trustworthiness is intact.")


@rule(8)
def _c8(pc):
    ll = lagna_lord(pc)
    msl = SIGN_LORDS.get(psign(pc, "Moon"), "")
    if not msl:
        return V(8, "NO", "Moon-sign lord could not be determined.")
    same = (ll == msl)
    mutual_kendra = abs((phouse(pc, ll) - phouse(pc, msl))) % 3 == 0 and phouse(pc, ll) and phouse(pc, msl)
    # mutual kendra: difference of houses is 0/3/6/9
    diff = (sign_index(psign(pc, ll)) - sign_index(psign(pc, msl))) % 12
    mutual_kendra = diff in (0, 3, 6, 9)
    common_friend = any(friend(ll, f) and friend(msl, f) and conj_or_aspect(pc, f, ll) and conj_or_aspect(pc, f, msl)
                        for f in PLANETS if f not in (ll, msl))
    if same:
        return V(8, "PARTIAL", f"Lagna lord and Moon-sign lord are the same planet ({ll}); the two-lord yoga collapses into one strong significator.")
    if mutual_kendra and (common_friend or friend(ll, msl)):
        return V(8, "HIT",
                 f"Lagna lord {ll} and Moon-sign lord {msl} are in mutual kendra" +
                 (" and are mutual friends" if friend(ll, msl) else " with a common friend's aspect") + ".",
                 "A king-making bond between body (lagna) and mind (Moon) — strong identity, popularity and rise.")
    if mutual_kendra:
        return V(8, "PARTIAL", f"Lagna lord {ll} and Moon-sign lord {msl} are in mutual kendra, but the friendly-aspect rider is missing.",
                 "Body and mind cooperate well, though short of the full king-making promise.")
    return V(8, "NO", f"Lagna lord {ll} and Moon-sign lord {msl} are neither conjunct nor in mutual kendra.")


@rule(9)
def _c9(pc):
    mh = phouse(pc, "Moon")
    msl = SIGN_LORDS.get(psign(pc, "Moon"), "")
    mlh = phouse(pc, msl) if msl else 0
    if mh in UPACHAYA and mlh in UPACHAYA:
        return V(9, "HIT",
                 f"Both the Moon (in the {_ord(mh)}) and its lord {msl} (in the {_ord(mlh)}) occupy upachaya houses (3/6/10/11).",
                 "An assurance of an all-round prosperous, steadily-improving life — one of the most reliable single signatures of a good life.")
    return V(9, "NO", f"The Moon is in the {_ord(mh)} and its lord {msl} in the {_ord(mlh)} — not both in upachaya houses.")


@rule(10)
def _c10(pc):
    llh = phouse(pc, lagna_lord(pc))
    mh = phouse(pc, "Moon")
    n9 = hlord(pc, 9)
    n9h = phouse(pc, n9)
    if not (llh and mh and n9h):
        return V(10, "NO", "Required positions unavailable.")
    lo, hi = sorted([mh, n9h])
    between = lo < llh < hi or (hi < lo)  # simple arc check
    inside = lo <= llh <= hi
    if mh != n9h and lo < llh < hi:
        return V(10, "HIT",
                 f"Your lagna lord sits in the {_ord(llh)}, between the Moon ({_ord(mh)}) and the 9th lord {n9} ({_ord(n9h)}).",
                 "Identity, fortune and the mind are linked — luck tends to follow your own initiative.")
    return V(10, "NO",
             f"Your lagna lord ({_ord(llh)}) does not fall in the arc between the Moon ({_ord(mh)}) and the 9th lord {n9} ({_ord(n9h)}).")


@rule(11)
def _c11(pc):
    # planets in 5th/7th from Moon or lagna empower the karaka tenanting their nakshatra
    hits = []
    targets = set()
    for ref_house_planet, label in (("Moon", "Moon"),):
        pass
    # planets in 5th or 7th from lagna and from Moon
    key_houses_lagna = {5, 7}
    energised = []
    for p in PLANETS:
        h_l = phouse(pc, p)
        # house from Moon
        mh = phouse(pc, "Moon")
        h_m = ((sign_index(psign(pc, p)) - sign_index(psign(pc, "Moon"))) % 12) + 1
        if h_l in key_houses_lagna or h_m in key_houses_lagna:
            energised.append(p)
    # the nakshatra lord of these energised planets gains strength
    boosted = []
    for p in energised:
        nl = NAK_TO_DASHA_LORD.get(pnak(pc, p), "")
        if nl:
            boosted.append((p, nl))
    if boosted:
        txt = "; ".join(f"{nl} (lord of {p}'s nakshatra)" for p, nl in boosted)
        return V(11, "HIT",
                 f"Planets in the 5th/7th from lagna or Moon ({', '.join(energised)}) empower their nakshatra lords: {txt}.",
                 "These significators carry extra force — the matters they rule (children, partner, wisdom, vitality) get a quiet boost.")
    return V(11, "NO", "No planet sits in the 5th/7th from lagna or Moon, so no karaka is specially empowered through its nakshatra lord.")


@rule(12)
def _c12(pc):
    found = []
    for p in PLANETS:
        if pdig(pc, p) == "own_sign" and (phouse(pc, p) in KENDRA) and not afflicted(pc, p):
            found.append(p)
        else:
            # also kendra from Moon
            h_m = ((sign_index(psign(pc, p)) - sign_index(psign(pc, "Moon"))) % 12) + 1
            if pdig(pc, p) == "own_sign" and h_m in (1, 4, 7, 10) and not afflicted(pc, p):
                found.append(p)
    if found:
        return V(12, "HIT",
                 f"{', '.join(sorted(set(found)))} sit(s) in own sign in a kendra (from lagna/Moon) and unafflicted.",
                 "The chart's power to deliver good results is raised — a dependable pillar of strength in life.")
    return V(12, "NO", "No planet is in its own sign in a kendra (from lagna or Moon) while unafflicted.")


@rule(13)
def _c13(pc):
    # benefic in 6th/8th from a trik lord, that house occupied → it suffers
    flags = []
    for trik in (6, 8, 12):
        tl = hlord(pc, trik)
        tlh = phouse(pc, tl)
        if not tlh:
            continue
        for off, lbl in ((6, "6th"), (8, "8th")):
            target_house = ((tlh - 1 + off - 1) % 12) + 1
            occ = occupants(pc, target_house)
            ben = [p for p in occ if is_benefic(pc, p)]
            if ben:
                flags.append(f"benefic {', '.join(ben)} sits {lbl} from the {_ord(trik)} lord {tl} (in the {_ord(target_house)} house)")
    if flags:
        return V(13, "HIT",
                 "; ".join(flags) + " — those houses are flagged to suffer in the relevant dasha.",
                 "Certain life areas can face temporary setbacks during the linked planetary periods — plan buffers around them.")
    return V(13, "NO", "No occupied benefic falls in the 6th/8th from a trik (6/8/12) lord — this suffering pattern is absent.")


@rule(14)
def _c14(pc):
    pls = [p for p in DIGNITY_TABLE if p not in ("Rahu", "Ketu") and pdig(pc, p) in ("exalted", "debilitated")]
    if pls:
        txt = ", ".join(f"{p} ({pdig(pc,p)})" for p in pls)
        return V(14, "HIT",
                 f"Planets in exaltation/debilitation: {txt}. Per this rule it is mainly their living (jeeva) significations that are affected.",
                 "Read these planets' personal/relationship significations (people, vitality) as the ones most coloured — material results are steadier.")
    return V(14, "NO", "No planet is exalted or debilitated, so this exaltation/debilitation refinement does not apply.")


@rule(15)
def _c15(pc):
    found = []
    for trik in (6, 8, 12):
        tl = hlord(pc, trik)
        if tl in ("Sun", "Moon"):
            continue
        own = DIGNITY_TABLE.get(tl, {}).get("own", [])
        # other own sign (not the trik sign)
        trik_sign = house_sign(trik, lagna(pc))
        if psign(pc, tl) in own and psign(pc, tl) != trik_sign:
            found.append(f"{_ord(trik)} lord {tl} sits in its other own sign {psign(pc, tl)}")
    if found:
        return V(15, "HIT",
                 "; ".join(found) + " — strong, withholding the bad trik-house effects.",
                 "A built-in protection: the difficult 6/8/12 themes are softened because their lord stands strong in its own sign.")
    return V(15, "NO", "No two-sign trik lord sits in its other own sign — this protective placement is absent.")


@rule(16)
def _c16(pc):
    # continuation of 15: same logic, report as supporting
    r = _c15(pc)
    if r.verdict == "HIT":
        return V(16, "HIT", r.finding.replace("withholding", "and gains strength, withholding"),
                 "Reinforces ch15 — the trik lord's strength shields its significations.")
    return V(16, "NO", "No trik lord gains this extra own-sign strength (see ch15).")


@rule(17)
def _c17(pc):
    res = []
    for h in (3, 6, 11):
        tl = hlord(pc, h)
        th = phouse(pc, tl)
        good = th in UPACHAYA
        res.append((h, tl, th, good))
    goods = [r for r in res if r[3]]
    if goods:
        txt = "; ".join(f"{_ord(h)} lord {tl} in the {_ord(th)} (upachaya)" for h, tl, th, _ in goods)
        return V(17, "HIT", f"Trishadaya lords well placed: {txt}.",
                 "Effort, competition and gains are supported — you grow stronger over time and through challenges.")
    txt = "; ".join(f"{_ord(h)} lord {tl} in the {_ord(th)}" for h, tl, th, _ in res)
    return V(17, "NO", f"No trishadaya (3/6/11) lord sits in an upachaya house: {txt}.")


@rule(18)
def _c18(pc):
    ll = lagna_lord(pc)
    l8 = hlord(pc, 8)
    if ll == l8:
        return V(18, "PARTIAL", f"Lagna lord and 8th lord are the same planet ({ll}); judge longevity/inheritance from its single placement.")
    if conjunct(pc, ll, l8):
        h = phouse(pc, ll)
        return V(18, "HIT",
                 f"Lagna lord {ll} and 8th lord {l8} are conjunct (in the {_ord(h)}).",
                 "A strong tie between self and longevity/legacy — favourable for inheritance and a resilient constitution if unafflicted.")
    return V(18, "NO", f"Lagna lord {ll} and 8th lord {l8} are not conjunct.")


@rule(19)
def _c19(pc):
    l8 = hlord(pc, 8)
    h = phouse(pc, l8)
    dig = pdig(pc, l8)
    if h:
        if dig == "friendly_sign":
            return V(19, "HIT",
                     f"The 8th lord {l8} sits in the {_ord(h)} in a friendly sign — by the exception, that house prospers rather than suffers.",
                     f"The {_ord(h)}-house matters are unexpectedly supported despite the 8th lord's touch.")
        return V(19, "HIT",
                 f"The 8th lord {l8} sits in the {_ord(h)} ({_dig_word(dig)}); classically it can dent that house's significations.",
                 f"Watch the {_ord(h)}-house themes for sudden ups and downs; {l8} brings transformation there.")
    return V(19, "NO", "8th lord placement unavailable.")


@rule(20)
def _c20(pc):
    l8 = hlord(pc, 8)
    h = phouse(pc, l8)
    aspd = [hx for hx in range(1, 13) if aspects_house(pc, l8, hx) and hx != h]
    if h:
        return V(20, "HIT",
                 f"The 8th lord {l8} occupies the {_ord(h)} and aspects house(s) {', '.join(_ord(x) for x in aspd) or '—'} — these are the areas it can unsettle.",
                 f"Keep an eye on {_ord(h)}-house affairs; transformation/obstacles can surface there.")
    return V(20, "NO", "8th lord placement unavailable.")


@rule(21)
def _c21(pc):
    occ = occupants(pc, 8)
    if not occ:
        return V(21, "NO", "No planet occupies the 8th house, so this wealth-with-calamity rule does not fire.")
    l2 = hlord(pc, 2)
    notes = []
    for p in occ:
        if p in ("Rahu", "Ketu"):
            rel = "node"
        elif friend(p, l2) or p == l2:
            rel = "friendly to the 2nd lord — gives more wealth"
        elif enemy(p, l2):
            rel = "enemy of the 2nd lord — risk of loss/damage" + (" (but debilitated, so it can still give wealth)" if is_weak(pc, p) else "")
        else:
            rel = "neutral to the 2nd lord"
        notes.append(f"{p} in the 8th ({rel})")
    return V(21, "HIT",
             "; ".join(notes) + ". Every 8th-house planet aspects the 2nd (wealth).",
             "Wealth can come — often through inheritance, insurance, others' resources or sudden gains — but usually with some upheaval attached.")


@rule(22)
def _c22(pc):
    ll = lagna_lord(pc)
    l8 = hlord(pc, 8)
    if ll == l8:
        return V(22, "NO", f"Lagna lord and 8th lord are the same planet ({ll}); no exchange possible.")
    # exchange: ll in 8th sign and l8 in lagna sign
    if psign(pc, ll) == house_sign(8, lagna(pc)) and psign(pc, l8) == lagna(pc):
        return V(22, "HIT",
                 f"Lagna lord {ll} sits in the 8th sign and 8th lord {l8} in the lagna sign — a parivartana of the 1st and 8th lords.",
                 "Strong promise of inheritance and long life — self and longevity reinforce each other (provided both are unafflicted).")
    return V(22, "NO", f"No sign-exchange between lagna lord {ll} and 8th lord {l8}.")


@rule(23)
def _c23(pc):
    ll = lagna_lord(pc)
    l8 = hlord(pc, 8)
    notes = []
    if ll == l8:
        if pdig(pc, ll) == "own_sign":
            return V(23, "HIT", f"For your {lagna(pc)} lagna the lagna+8th lord is the same planet {ll}, and it sits in its own sign.",
                     "A classic assurance of long life and vitality.")
        return V(23, "NO", f"Lagna/8th lord {ll} is not in its own sign.")
    if pdig(pc, ll) == "own_sign":
        notes.append(f"lagna lord {ll} in own sign")
    if pdig(pc, l8) == "own_sign":
        notes.append(f"8th lord {l8} in own sign")
    if notes and not (afflicted(pc, ll) and afflicted(pc, l8)):
        return V(23, "HIT", " and ".join(notes) + " — long life is favoured.",
                 "Sound longevity and recuperative power, as long as these lords stay unafflicted.")
    return V(23, "NO", f"Neither lagna lord {ll} nor 8th lord {l8} sits in own sign.")


@rule(24)
def _c24(pc):
    l8 = hlord(pc, 8)
    if afflicted(pc, l8):
        why = []
        if is_weak(pc, l8):
            why.append(_dig_word(pdig(pc, l8)))
        mals = [m for m in NAT_MALEFIC if m != l8 and conj_or_aspect(pc, m, l8)]
        if mals:
            why.append("hit by " + ", ".join(mals))
        return V(24, "HIT",
                 f"The 8th lord {l8} is afflicted ({'; '.join(why)}) — flagged to reduce vitality/lifespan.",
                 "Treat health and recuperation as a priority lane; preventive care and a disciplined lifestyle matter more for you.")
    return V(24, "NO", f"The 8th lord {l8} is not afflicted — no lifespan-reduction flag from this rule.")


@rule(25)
def _c25(pc):
    strong_exalt = [p for p in DIGNITY_TABLE if p not in ("Rahu", "Ketu") and pdig(pc, p) == "exalted"
                    and phouse(pc, p) in (KENDRA | TRIKONA)]
    if strong_exalt:
        return V(25, "HIT",
                 f"Exalted planet(s) in a kendra/trikona: {', '.join(p+' ('+psign(pc,p)+')' for p in strong_exalt)}.",
                 "High status is promised — and with more than one such placement it multiplies across fields (office, wealth, learning or fame).")
    any_exalt = [p for p in DIGNITY_TABLE if p not in ("Rahu", "Ketu") and pdig(pc, p) == "exalted"]
    if any_exalt:
        return V(25, "PARTIAL",
                 f"Exalted planet(s) present ({', '.join(any_exalt)}) but not in a kendra/trikona — status rises, but less commandingly.")
    return V(25, "NO", "No planet is exalted, so this status-multiplier rule does not apply.")


@rule(26)
def _c26(pc):
    l9 = hlord(pc, 9)
    h = phouse(pc, l9)
    in_trine_d1 = h in (5, 9)
    # navamsha: 9th lord's navamsha house from D9 lagna unavailable simply; use D9 sign trine of D9 lagna
    d9 = pc.get("divisional", {}).get("D9", {})
    d9_note = ""
    in_trine_d9 = False
    if d9:
        d9_lagna = d9.get("Lagna") or d9.get("lagna")
        d9_l9 = d9.get(l9)
        if d9_lagna and d9_l9:
            hh = (sign_index(d9_l9) - sign_index(d9_lagna)) % 12 + 1
            in_trine_d9 = hh in (5, 9)
            d9_note = f" In Navamsha the 9th lord is in the {_ord(hh)} from D9 lagna."
    if in_trine_d1 or in_trine_d9:
        where = "the birth chart" if in_trine_d1 else "Navamsha"
        return V(26, "HIT",
                 f"The 9th lord {l9} is in a trine (5th/9th) from lagna in {where} (D1 house {_ord(h)}).{d9_note}",
                 "A strong pull toward government / public-sector work or state support — service, consultancy or contracts tied to the Government.")
    return V(26, "NO", f"The 9th lord {l9} (in the {_ord(h)}) is not in a 5th/9th trine from lagna in D1 or D9 — this government-service signature is absent.")


@rule(27)
def _c27(pc):
    l9 = hlord(pc, 9)
    h = phouse(pc, l9)
    # trine FROM the 9th house = houses 9, 1, 5
    trine_from9 = {9, 1, 5}
    if h in trine_from9:
        return V(27, "HIT",
                 f"The 9th lord {l9} occupies the {_ord(h)} — a trine reckoned from the 9th house (9/1/5).",
                 "Fortune runs deep: wealth, a strong home and a comfortable, luxurious life are indicated by a well-placed lord of luck.")
    if h in DUSTHANA:
        return V(27, "NO",
                 f"The 9th lord {l9} sits in the {_ord(h)} (a trik house) — instead of the luxury promise this warns of luck-related losses; guard your fortune-houses.")
    return V(27, "NO", f"The 9th lord {l9} (in the {_ord(h)}) is not in a trine from the 9th (9/1/5) — this luxury rule does not fire.")


@rule(28)
def _c28(pc):
    l10 = hlord(pc, 10)
    deb = pdig(pc, l10) == "debilitated"
    mal2 = [m for m in NAT_MALEFIC if phouse(pc, m) == 2]
    if deb and mal2:
        # exception: debilitated 10th lord aspects 10th
        relief = aspects_house(pc, l10, 10)
        if relief:
            return V(28, "PARTIAL",
                     f"The 10th lord {l10} is debilitated and malefic(s) {', '.join(mal2)} sit in the 2nd — but {l10} aspects the 10th, the stated exception that softens it.")
        return V(28, "HIT",
                 f"The 10th lord {l10} is debilitated and malefic(s) {', '.join(mal2)} occupy the 2nd house.",
                 "A hard combination for prolonged struggle around career and family resources — but it also calls for resilience; targeted remedies for the 10th lord help.")
    return V(28, "NO",
             f"Condition not met (10th lord {l10} debilitated: {'yes' if deb else 'no'}; malefic in 2nd: {', '.join(mal2) or 'no'}).")


@rule(29)
def _c29(pc):
    ben2 = [p for p in occupants(pc, 2) if is_benefic(pc, p)]
    if ben2:
        return V(29, "HIT",
                 f"Benefic {', '.join(ben2)} occupies the 2nd house — the 'no (little) suffering' placement.",
                 "Life's hardships stay manageable; family and resources offer a cushion against the worst troubles.")
    return V(29, "NO", "No benefic occupies the 2nd house — this protective placement is absent.")


@rule(30)
def _c30(pc):
    if not conjunct(pc, "Rahu", "Venus"):
        return V(30, "NO", "Rahu and Venus are not conjunct — this rule does not apply.")
    h = phouse(pc, "Rahu")
    if h in (4, 8):
        return V(30, "HIT",
                 f"Rahu-Venus conjunction in the {_ord(h)} house.",
                 "Can bring unusual fears and friction in love/marriage — handle relationships with patience; spiritual remedies for Rahu/Venus help.")
    if h in (KENDRA | TRIKONA):
        return V(30, "HIT",
                 f"Rahu-Venus conjunction in the {_ord(h)} (a kendra/trikona) — here Rahu acts as that lord and can give good results.",
                 "A worldly, ambitious charm that can lift status and gains, though guard the relationship sphere.")
    return V(30, "HIT", f"Rahu-Venus conjunction in the {_ord(h)} house.",
             "A strong desire-nature; channel it consciously in relationships and pleasures.")


@rule(31)
def _c31(pc):
    deb_lords = []
    for h in range(1, 13):
        lord = hlord(pc, h)
        if pdig(pc, lord) == "debilitated":
            deb_lords.append((h, lord))
    if deb_lords:
        txt = "; ".join(f"{_ord(h)} lord {l} debilitated (in the {_ord(phouse(pc,l))})" for h, l in deb_lords)
        return V(31, "HIT",
                 f"Debilitated house lord(s): {txt}. Those houses' significations weaken along the planet's nature.",
                 "The flagged houses need conscious effort and remedies for the debilitated lord; not every signification suffers — read by the planet's nature.")
    return V(31, "NO", "No house lord is debilitated — this house-suffering rule does not fire.")


@rule(32)
def _c32(pc):
    yk = FUNCTIONAL.get(lagna(pc), {}).get("yogakaraka", [])
    if yk:
        y = yk[0]
        owns = houses_lorded_by(pc, y)
        return V(32, "HIT",
                 f"{y} is the Yogakaraka (Yogda) for {lagna(pc)} lagna, owning the {' & '.join(_ord(x) for x in owns)} houses ({_dig_word(pdig(pc,y))}, in the {_ord(phouse(pc,y))}).",
                 f"{y} is your single most powerful lever — its periods and strength uplift status, wealth and the houses it rules. Strengthen it.")
    # Moon dispositor acting as Yogda
    msl = SIGN_LORDS.get(psign(pc, "Moon"), "")
    return V(32, "NO",
             f"{lagna(pc)} lagna has no classical single Yogakaraka. (Watch the Moon's dispositor {msl} as a wealth-giver instead.)")


@rule(33)
def _c33(pc):
    occ9 = [p for p in occupants(pc, 9) if p not in ("Rahu", "Ketu")]
    deb = [p for p in occ9 if pdig(pc, p) == "debilitated"]
    if deb:
        # exception: debilitation that is itself a yoga (8th/12th lord debilitated etc.)
        ben_excuse = [p for p in deb if set(houses_lorded_by(pc, p)) & {6, 8, 12}]
        if deb and not (set(deb) <= set(ben_excuse)):
            return V(33, "HIT",
                     f"Debilitated planet {', '.join(deb)} in the 9th house.",
                     "A caution around luck, father and higher fortune — fortune is earned the hard way; faith, mentors and 9th-lord remedies help.")
        return V(33, "PARTIAL",
                 f"Debilitated planet {', '.join(deb)} in the 9th, but it owns a trik house — the debilitation works more as a yoga than as misfortune.")
    return V(33, "NO", "No debilitated planet sits in the 9th house — this poverty/problem rule does not fire.")


@rule(34)
def _c34(pc):
    # trine lord + kendra lord related, focused in 5th/10th
    trine_lords = {hlord(pc, h) for h in (1, 5, 9)}
    kendra_lords = {hlord(pc, h) for h in (1, 4, 7, 10)}
    pairs = []
    for tl in trine_lords:
        for kl in kendra_lords:
            if tl == kl:
                continue
            if conj_or_aspect(pc, tl, kl):
                # focus in 5th/10th?
                if phouse(pc, tl) in (5, 10) or phouse(pc, kl) in (5, 10) or conjunct(pc, tl, kl) and phouse(pc, tl) in (5, 10):
                    pairs.append(f"{tl}~{kl}")
    if pairs:
        return V(34, "HIT",
                 f"A trine-lord/kendra-lord Raj Yoga touching the 5th/10th: {', '.join(sorted(set(pairs)))}.",
                 "Strong potential for civil service or high office; the link to the 5th/10th points the Raj Yoga at authority and administration.")
    # generic raja yoga without 5/10 focus
    generic = [f"{tl}~{kl}" for tl in trine_lords for kl in kendra_lords if tl != kl and conj_or_aspect(pc, tl, kl)]
    if generic:
        return V(34, "PARTIAL",
                 f"Trine-lord/kendra-lord Raj Yoga present ({', '.join(sorted(set(generic)))}) but not focused in the 5th/10th — high office is possible, less specifically civil-service.")
    return V(34, "NO", "No trine-lord/kendra-lord relation found — this civil-service rule does not fire.")


@rule(35)
def _c35(pc):
    l5, l11 = hlord(pc, 5), hlord(pc, 11)
    if l5 == l11:
        return V(35, "PARTIAL", f"5th and 11th lord are the same planet ({l5}); wealth potential rests on its single strength.")
    related = conj_or_aspect(pc, l5, l11)
    well = phouse(pc, l5) not in DUSTHANA and phouse(pc, l11) not in DUSTHANA
    if related:
        return V(35, "HIT",
                 f"The 5th lord {l5} and 11th lord {l11} are related (conjunction/aspect/exchange).",
                 "A wealth signature that can make you the richest in your circle — gains (11th) backed by fortune and intelligence (5th).")
    if well:
        return V(35, "PARTIAL",
                 f"5th lord {l5} and 11th lord {l11} are not directly related but both are decently placed — moderate clan-wealth potential.")
    return V(35, "NO", f"The 5th lord {l5} and 11th lord {l11} are neither related nor well placed for this clan-wealth rule.")


@rule(36)
def _c36(pc):
    l4 = hlord(pc, 4)
    flags = []
    if phouse(pc, l4) == 12 or phouse(pc, l4) in (3, 9):
        flags.append(f"4th lord {l4} in the {_ord(phouse(pc,l4))} (home pulled abroad / to travel)")
    if phouse(pc, lagna_lord(pc)) in (3, 9, 12):
        flags.append(f"lagna lord in the {_ord(phouse(pc,lagna_lord(pc)))}")
    if psign(pc, "Moon") in ("Aries", "Cancer", "Libra", "Capricorn"):
        flags.append("Moon in a movable sign (restless, relocating mind)")
    if flags:
        return V(36, "HIT", "; ".join(flags) + ".",
                 "Strong likelihood of building your life away from your birth place — possibly another city or country.")
    return V(36, "NO", "No clear away-from-home indicators (4th lord in 12/3/9, lagna lord in 3/9/12, movable Moon) — you likely stay near roots.")


@rule(37)
def _c37(pc):
    occ10 = occupants(pc, 10)
    l2, l11 = hlord(pc, 2), hlord(pc, 11)
    rich = [p for p in occ10 if p in (l2, l11)]
    if rich:
        which = "; ".join(f"{p} (the {'2nd' if p==l2 else '11th'} lord)" for p in rich)
        return V(37, "HIT",
                 f"Wealth lord in the 10th: {which} occupies the strongest kendra.",
                 "A clear richness signature — your work/status (10th) becomes a direct channel for accumulation (2nd) or gains (11th).")
    return V(37, "NO", "Neither the 2nd nor the 11th lord sits in the 10th house — this 'rich' placement is absent.")


@rule(38)
def _c38(pc):
    occ10 = [p for p in occupants(pc, 10) if p not in ("Rahu", "Ketu")]
    if not occ10:
        return V(38, "NO", "No planet occupies the 10th house, so this 'house whose lord is in the 10th' analysis is muted.")
    notes = []
    for p in occ10:
        owned = houses_lorded_by(pc, p)
        for oh in owned:
            afl = any(get_functional_status(m, lagna(pc)) == "functional_malefic" and conj_or_aspect(pc, m, p)
                      for m in NAT_MALEFIC if m != p)
            notes.append(f"{p} (lord of the {_ord(oh)}) is in the 10th" + (" and afflicted — its house's results get boosted but mis-directed" if afl else " — that house's affairs surface through career/status"))
    return V(38, "HIT", "; ".join(notes) + ".",
             "Your career/public life becomes the stage for the houses these planets own — for better or, if afflicted, in a distorted way.")


@rule(39)
def _c39(pc):
    l7 = hlord(pc, 7)
    flags = []
    mal7 = [m for m in NAT_MALEFIC if phouse(pc, m) == 7]
    if mal7:
        flags.append(f"malefic {', '.join(mal7)} in the 7th house")
    if phouse(pc, l7) in DUSTHANA:
        flags.append(f"7th lord {l7} in the {_ord(phouse(pc,l7))} (a trik house)")
    if afflicted(pc, "Venus"):
        flags.append("Venus (marriage karaka) afflicted")
    if phouse(pc, l7) in DUSTHANA or mal7:
        return V(39, "HIT", "; ".join(flags) + ".",
                 "Marriage may face delays or obstacles even once arranged — guard against haste; strengthening the 7th lord/Venus and patience smooth the path.")
    if flags:
        return V(39, "PARTIAL", "; ".join(flags) + " — mild marriage-delay caution.",
                 "Small bumps possible around partnership timing; nothing severe.")
    return V(39, "NO", f"The 7th house and its lord {l7} (and Venus) are reasonably clear — no strong marriage-obstacle flag.")


@rule(40)
def _c40(pc):
    if psign(pc, "Sun") == "Cancer" and psign(pc, "Moon") == "Leo":
        return V(40, "HIT", "Sun in Cancer and Moon in Leo — a full Sun-Moon parivartana (sign exchange).",
                 "A luminary exchange that strengthens identity, vitality and emotional confidence together.")
    return V(40, "NO", f"No Sun-Moon sign exchange (Sun in {psign(pc,'Sun')}, Moon in {psign(pc,'Moon')}).")


@rule(41)
def _c41(pc):
    ll = lagna_lord(pc)
    msl = SIGN_LORDS.get(psign(pc, "Moon"), "")
    if ll == msl:
        return V(41, "NO", f"Lagna lord and Moon-sign lord are the same planet ({ll}); no exchange possible.")
    if psign(pc, ll) == psign(pc, "Moon") and psign(pc, msl) == lagna(pc):
        return V(41, "HIT",
                 f"Lagna lord {ll} sits in the Moon's sign and Moon-sign lord {msl} in the lagna — a Raj-Yoga parivartana.",
                 "A high-status Raj Yoga linking body and mind — a strong lift to standing and recognition.")
    return V(41, "NO", f"No sign-exchange between lagna lord {ll} and Moon-sign lord {msl}.")


@rule(42)
def _c42(pc):
    bt = pc.get("meta", {}).get("birth_time", "")
    try:
        hh, mm = [int(x) for x in str(bt).split(":")[:2]]
        minutes = hh * 60 + mm
    except Exception:
        return V(42, "NA", "Birth time unavailable to test the Abhijit (midday/midnight) window.")
    # within ~48 min of local noon (720) or midnight (0/1440)
    near_noon = abs(minutes - 720) <= 48
    near_mid = min(minutes, abs(minutes - 1440)) <= 48
    if near_noon or near_mid:
        when = "midday" if near_noon else "midnight"
        return V(42, "HIT",
                 f"Birth at {bt} falls within ~2 ghati of {when} (the Abhijit window).",
                 "A king-like, undefeatable streak — strong willpower and the knack of prevailing in contests.")
    return V(42, "NO", f"Birth at {bt} is not within ~48 min of midday or midnight — the Abhijit-Mahurat rule does not apply.")


@rule(43)
def _c43(pc):
    l2 = hlord(pc, 2)
    strong = pdig(pc, l2) in STRONG_DIG or pdig(pc, l2) == "friendly_sign"
    ben2 = [p for p in occupants(pc, 2) if is_benefic(pc, p)]
    if strong or ben2:
        bits = []
        if strong:
            bits.append(f"2nd lord {l2} is {_dig_word(pdig(pc,l2))}")
        if ben2:
            bits.append(f"benefic {', '.join(ben2)} sits in the 2nd")
        return V(43, "HIT", "; ".join(bits) + " — the 2nd (wealth) gains strength.",
                 "A well-supported wealth house — savings, family resources and earning capacity are favoured.")
    return V(43, "NO", f"The 2nd house is not specially strong (2nd lord {l2} is {_dig_word(pdig(pc,l2))}, no benefic tenant).")


@rule(44)
def _c44(pc):
    res = []
    for node in ("Rahu", "Ketu"):
        h = phouse(pc, node)
        if h in TRIKONA:
            res.append(f"{node} in the {_ord(h)} (a trine)")
    if res:
        return V(44, "HIT", "; ".join(res) + " — the node's dasha is flagged to give wealth.",
                 "The node's major period can open a notable wealth window — position yourself for gains during it.")
    return V(44, "NO", "Neither Rahu nor Ketu sits in a trine (1/5/9) — this nodal-wealth rule does not fire.")


@rule(45)
def _c45(pc):
    l9, l10 = hlord(pc, 9), hlord(pc, 10)
    if l9 == l10:
        return V(45, "PARTIAL", f"9th and 10th lord are the same planet ({l9}); Dharma-Karma strength rests on it alone.")
    if conj_or_aspect(pc, l9, l10):
        rel = "conjunction" if conjunct(pc, l9, l10) else "mutual aspect"
        return V(45, "HIT",
                 f"The 9th (Dharma) lord {l9} and 10th (Karma) lord {l10} are in {rel} — a Dharma-Karmadhipati Yoga.",
                 "One of the finest yogas for success: fortune and action reinforce each other, lifting career and reputation.")
    return V(45, "NO", f"The 9th lord {l9} and 10th lord {l10} have no direct relation — this Karma-Dharma yoga is absent.")


@rule(46)
def _c46(pc):
    res = []
    for node in ("Rahu", "Ketu"):
        disp = SIGN_LORDS.get(psign(pc, node), "")
        if not disp:
            continue
        good = (phouse(pc, disp) not in DUSTHANA) and not is_weak(pc, disp)
        also_trine_lord = bool(set(houses_lorded_by(pc, disp)) & {1, 5, 9}) and bool(set(houses_lorded_by(pc, disp)) & {6, 8, 12})
        if good:
            res.append(f"{node}'s dispositor {disp} is well placed ({_dig_word(pdig(pc,disp))}, {_ord(phouse(pc,disp))})" + (" and is a trik+trikona lord (ideal)" if also_trine_lord else ""))
    if res:
        return V(46, "HIT", "; ".join(res) + ".",
                 "The nodes deliver good results through their well-placed dispositors — their periods tend to be constructive.")
    return V(46, "NO", "The dispositors of Rahu/Ketu are not well placed — the nodes lack this supportive channel.")


@rule(47)
def _c47(pc):
    res = []
    for p in PLANETS:
        bs, ns = psign(pc, p), navsign(pc, p)
        if not bs or not ns:
            continue
        diff = (sign_index(ns) - sign_index(bs)) % 12
        if diff in (0, 4, 8):  # trine relation between birth sign and navamsha sign
            res.append(f"{p} (birth {bs} / navamsha {ns})")
    if res:
        return V(47, "HIT", "Planets whose birth and navamsha signs are in trine: " + "; ".join(res) + ".",
                 "These planets sit in dignified harmony between the visible and inner chart — they give steady, good results.")
    return V(47, "NO", "No planet has its birth sign and navamsha sign in trine — this 5th-Navamsha harmony is absent.")


@rule(48)
def _c48(pc):
    disp = SIGN_LORDS.get(psign(pc, "Rahu"), "")
    if not disp:
        return V(48, "NO", "Rahu's dispositor could not be determined.")
    h_from_rahu = (sign_index(psign(pc, disp)) - sign_index(psign(pc, "Rahu"))) % 12 + 1
    bad = is_weak(pc, disp) or h_from_rahu == 8 or afflicted(pc, disp)
    if bad:
        why = []
        if is_weak(pc, disp):
            why.append(_dig_word(pdig(pc, disp)))
        if h_from_rahu == 8:
            why.append("in the 8th from Rahu")
        if afflicted(pc, disp) and not is_weak(pc, disp):
            why.append("afflicted by malefics")
        return V(48, "HIT",
                 f"Rahu's dispositor {disp} is compromised ({', '.join(why)}; sits in the {_ord(phouse(pc,disp))}).",
                 f"The affairs of {disp} and the house Rahu sits in can suffer — give those areas care and Rahu/{disp} remedies.")
    return V(48, "NO", f"Rahu's dispositor {disp} is sound ({_dig_word(pdig(pc,disp))}, {_ord(phouse(pc,disp))}) — this suffering rule does not fire.")


@rule(49)
def _c49(pc):
    res = []
    for p in DIGNITY_TABLE:
        if p in ("Rahu", "Ketu"):
            continue
        if pdig(pc, p) == "exalted" and phouse(pc, p) in DUSTHANA:
            owns = houses_lorded_by(pc, p)
            res.append(f"{p} exalted in the {_ord(phouse(pc,p))} (trik), owning {', '.join(_ord(x) for x in owns)}")
    if res:
        return V(49, "HIT", "; ".join(res) + " — its living significations and owned houses can suffer.",
                 "A strong planet placed in a difficult house: its brilliance is real but its personal significations need protection.")
    return V(49, "NO", "No planet is exalted while sitting in a trik (6/8/12) house — this rule does not fire.")


@rule(50)
def _c50(pc):
    strong = [p for p in DIGNITY_TABLE if p not in ("Rahu", "Ketu")
              and pdig(pc, p) in ("exalted", "own_sign", "moolatrikona") and phouse(pc, p) in KENDRA]
    if strong:
        return V(50, "HIT", "Dignified planet(s) in a kendra: " + ", ".join(f"{p} ({_dig_word(pdig(pc,p))}, {_ord(phouse(pc,p))})" for p in strong) + ".",
                 "Ruling power and command — strong, dignified planets in the angles give the authority to lead.")
    return V(50, "NO", "No exalted/own-sign planet sits in a kendra — this ruling-power signature is absent.")


@rule(51)
def _c51(pc):
    l2 = hlord(pc, 2)
    if pdig(pc, l2) == "exalted":
        return V(51, "HIT", f"The 2nd lord {l2} is exalted in {psign(pc,l2)}.",
                 f"The dasha of {l2} is set to be a strong wealth window — earnings and family resources flourish in its period.")
    return V(51, "NO", f"The 2nd lord {l2} is not exalted ({_dig_word(pdig(pc,l2))}).")


@rule(52)
def _c52(pc):
    benefics = ["Jupiter", "Venus", "Mercury"]
    in_trik = [p for p in benefics if phouse(pc, p) in DUSTHANA]
    in_good = [p for p in benefics if phouse(pc, p) in (KENDRA | TRIKONA | {2, 11})]
    if len(in_trik) >= 2:
        return V(52, "HIT", f"Two or more benefics ({', '.join(in_trik)}) are tucked into trik houses (6/8/12).",
                 "Wealth and ease come less freely — benefic gifts are partly locked away; remedies and effort unlock them.")
    if len(in_good) >= 3:
        return V(52, "HIT", f"All three benefics ({', '.join(in_good)}) are well placed (kendra/trine/2/11).",
                 "A benefic-rich chart — comfort, support and resources tend to flow.")
    return V(52, "PARTIAL", f"Benefic placement is mixed (well placed: {', '.join(in_good) or '—'}; in trik: {', '.join(in_trik) or '—'}).")


@rule(53)
def _c53(pc):
    mals = ["Sun", "Mars", "Saturn"]
    clustered = {}
    for p in mals:
        clustered.setdefault(phouse(pc, p), []).append(p)
    groups = [(h, ps) for h, ps in clustered.items() if len(ps) >= 2]
    if any(len(ps) == 3 for _, ps in groups):
        h, ps = next((h, ps) for h, ps in groups if len(ps) == 3)
        return V(53, "HIT", f"Three natural malefics ({', '.join(ps)}) cluster in the {_ord(h)} house.",
                 "A bold, hardy temperament forged by malefic concentration — powerful drive, but watch for friction in that house's affairs.")
    if groups:
        h, ps = groups[0]
        return V(53, "PARTIAL", f"Two malefics ({', '.join(ps)}) sit together in the {_ord(h)} — partial malefic concentration.")
    return V(53, "NO", "Natural malefics are scattered — no three-malefic concentration.")


@rule(54)
def _c54(pc):
    flags = []
    if psign(pc, "Mercury") in ENEMIES.get("Mercury", []) and aspects_planet(pc, "Moon", "Mercury"):
        flags.append("Mercury in an enemy sign aspected by the Moon")
    waning = not moon_waxing(pc)
    if waning and phouse(pc, "Mars") in DUSTHANA and phouse(pc, "Moon") in DUSTHANA:
        flags.append("waning Moon and Mars both in trik houses")
    ll = lagna_lord(pc)
    if afflicted(pc, ll) and phouse(pc, ll) in DUSTHANA:
        flags.append(f"lagna lord {ll} afflicted in a trik house")
    if flags:
        return V(54, "HIT", "; ".join(flags) + ".",
                 "Indicators of a sharp, sometimes unscrupulous streak — conscious ethics and Moon/Mercury remedies channel it well.")
    return V(54, "NO", "None of the 'wicked' indicators (enemy Mercury+Moon, waning Moon+Mars in trik, afflicted lagna lord in trik) are present.")


@rule(55)
def _c55(pc):
    mal_strong = sum(1 for p in ["Sun", "Mars", "Saturn"] if pdig(pc, p) in STRONG_DIG or phouse(pc, p) in UPACHAYA)
    ben_strong = sum(1 for p in ["Jupiter", "Venus", "Mercury"] if pdig(pc, p) in STRONG_DIG or phouse(pc, p) in (KENDRA | TRIKONA))
    if mal_strong >= 2 and ben_strong >= 1:
        return V(55, "HIT",
                 f"Balanced strength — {mal_strong} malefics give material drive and {ben_strong} benefic(s) give ethical grounding.",
                 "The classic mix for a materially successful life: ambition with conscience.")
    return V(55, "PARTIAL",
             f"Strength balance is uneven (strong malefics: {mal_strong}, strong benefics: {ben_strong}) — success comes, shaped by whichever side dominates.")


@rule(56)
def _c56(pc):
    l4, l8 = hlord(pc, 4), hlord(pc, 8)
    rel = conj_or_aspect(pc, l4, l8) or l4 == l8
    strong = (pdig(pc, l4) in STRONG_DIG) or (pdig(pc, l8) in STRONG_DIG)
    ben8 = [p for p in occupants(pc, 8) if is_benefic(pc, p)]
    if rel and (strong or ben8):
        return V(56, "HIT",
                 f"The 4th lord {l4} and 8th lord {l8} are linked, with strength/benefic support on the property-legacy (4/8) axis.",
                 "A strong indication of inheritance / unearned assets — property, legacy or hidden wealth can come your way.")
    return V(56, "NO", f"The property-legacy axis (4th lord {l4}, 8th lord {l8}) lacks the linked strength this big-inheritance rule needs.")


@rule(57)
def _c57(pc):
    def adhi(ref_house):
        signs = [house_sign(((ref_house - 1 + k) % 12) + 1, lagna(pc)) for k in (5, 6, 7)]  # 6th,7th,8th from ref
        bens = [p for p in NAT_BENEFIC if is_benefic(pc, p) and psign(pc, p) in signs]
        return bens
    lagna_adhi = adhi(1)
    # Chandra adhi: 6/7/8 from Moon
    moon_h = phouse(pc, "Moon")
    moon_signs = [house_sign(((moon_h - 1 + k) % 12) + 1, lagna(pc)) for k in (5, 6, 7)]
    chandra_adhi = [p for p in NAT_BENEFIC if is_benefic(pc, p) and psign(pc, p) in moon_signs]
    if len(set(lagna_adhi)) >= 2 or len(set(chandra_adhi)) >= 2:
        which = "lagna Adhi" if len(set(lagna_adhi)) >= 2 else "Chandra Adhi"
        bens = lagna_adhi if which == "lagna Adhi" else chandra_adhi
        return V(57, "HIT",
                 f"{which} Yoga: benefics ({', '.join(sorted(set(bens)))}) gather in the 6th/7th/8th from {'lagna' if which.startswith('lagna') else 'the Moon'}.",
                 "A yoga of fame, wealth, health and a legendary standing — quiet benefic strength that builds a respected life.")
    return V(57, "NO", "No Subh-Adhi yoga — benefics do not gather in the 6th/7th/8th from lagna or Moon.")


@rule(58)
def _c58(pc):
    moon_h = phouse(pc, "Moon")
    moon_signs = [house_sign(((moon_h - 1 + k) % 12) + 1, lagna(pc)) for k in (5, 6, 7)]  # 6/7/8 from Moon
    mals = [p for p in NAT_MALEFIC if psign(pc, p) in moon_signs]
    if len(set(mals)) >= 2:
        return V(58, "HIT",
                 f"Papa-Adhi Yoga: malefics ({', '.join(sorted(set(mals)))}) occupy the 6th/7th/8th from the Moon.",
                 "A hardy, combative make-up — strength through struggle; it can give grit and a fighter's edge, but guard relationships and health.")
    return V(58, "NO", "No Papa-Adhi yoga — malefics do not gather in the 6th/7th/8th from the Moon.")


@rule(59)
def _c59(pc):
    trine_lords = {hlord(pc, h) for h in (1, 5, 9)}
    flags = []
    for guru in ("Jupiter", "Venus", "Mercury"):
        if conj_or_aspect(pc, "Ketu", guru) and any(conj_or_aspect(pc, "Ketu", tl) or guru in trine_lords for tl in trine_lords):
            flags.append(f"Ketu with {guru} + a trine lord")
    l5, l8 = hlord(pc, 5), hlord(pc, 8)
    if l5 != l8 and conj_or_aspect(pc, l5, l8):
        flags.append("5th & 8th lords related (strong predictive power)")
    if flags:
        return V(59, "HIT", "; ".join(flags) + ".",
                 "A genuine gift for astrology, intuition and the occult — your insight into hidden patterns is a real strength.")
    return V(59, "NO", "No 'astrologer' combination (Ketu + guru-planet + trine lord, or 5th-8th lord link) is present.")


@rule(60)
def _c60(pc):
    pairs = 0
    seen = []
    checklist = [("Sun", "Moon"), ("Mars", "Saturn"), ("Mercury", "Jupiter"), ("Venus", "Jupiter")]
    for a, b in checklist:
        if conj_or_aspect(pc, a, b):
            pairs += 1
            seen.append(f"{a}~{b}")
    if pairs >= 3:
        return V(60, "HIT", f"Three+ planetary pairs in mutual relation: {', '.join(seen)}.",
                 "Many planetary partnerships work together for you — a cooperative chart that finds success through alliances.")
    if pairs >= 1:
        return V(60, "PARTIAL", f"{pairs} planetary pair(s) in relation: {', '.join(seen)} (rule wants three pairs).")
    return V(60, "NO", "No significant planetary pairs in mutual relation for this 'three pairs' rule.")


@rule(61)
def _c61(pc):
    l11 = hlord(pc, 11)
    if enemy(lagna_lord(pc), l11) or phouse(pc, l11) in DUSTHANA:
        owns = houses_lorded_by(pc, l11)
        return V(61, "HIT",
                 f"The 11th lord {l11} is unfriendly to the lagna / placed in a trik house (owns {', '.join(_ord(x) for x in owns)}).",
                 f"The dasha of {l11} can mix gains with strain — enjoy the gains but stay cautious about its other house's troubles during its period.")
    return V(61, "NO", f"The 11th lord {l11} is not hostile to the lagna nor in a trik house — its dasha is not specially flagged.")


@rule(62)
def _c62(pc):
    KARAKA = {1: "Sun", 2: "Jupiter", 3: "Mars", 4: "Moon", 5: "Jupiter",
              6: "Mars", 7: "Venus", 9: "Jupiter", 10: "Sun", 11: "Jupiter"}
    notes = []
    for h, kar in KARAKA.items():
        lord = hlord(pc, h)
        if lord == kar:
            continue
        if conj_or_aspect(pc, kar, lord) and not afflicted(pc, kar) and not afflicted(pc, lord):
            notes.append(f"{_ord(h)}: karaka {kar} & lord {lord} both strong and related")
    if notes:
        return V(62, "HIT", "; ".join(notes) + ".",
                 "Where the significator and the house-lord stand strong together, those life areas flourish reliably.")
    return V(62, "NO", "No house shows its karaka and its lord both strong and mutually related in the clean way this rule wants.")


@rule(63)
def _c63(pc):
    # Jupiter in 12th from Sun (always direct) influencing Sun; Venus direct near Sun
    sun_h = sign_index(psign(pc, "Sun"))
    jup_from_sun = (sign_index(psign(pc, "Jupiter")) - sun_h) % 12 + 1
    flags = []
    if jup_from_sun == 12:
        flags.append("Jupiter in the 12th from the Sun (benefic Palai influence)")
    if conj_or_aspect(pc, "Venus", "Sun") and not pretro(pc, "Venus"):
        flags.append("direct Venus influencing the Sun")
    if flags:
        return V(63, "HIT", "; ".join(flags) + ".",
                 "A refining benefic touch on the Sun (soul/authority) — dignity and grace in how you carry power.")
    return V(63, "NO", "Palai-yoga conditions (Jupiter 12th from Sun / direct Venus on Sun) are not met.")


@rule(64)
def _c64(pc):
    def from_ref(ref):
        ref_idx = sign_index(psign(pc, ref))
        signs = [SIGNS[(ref_idx + k) % 12] for k in (5, 6, 7)]  # 6/7/8 from ref
        return [p for p in PLANETS if psign(pc, p) in signs]
    moon_occ = from_ref("Moon")
    sun_occ = from_ref("Sun")
    if len(moon_occ) >= 3 or len(sun_occ) >= 3:
        ref = "Moon" if len(moon_occ) >= 3 else "Sun"
        occ = moon_occ if ref == "Moon" else sun_occ
        return V(64, "HIT",
                 f"Strong occupation of the 6th/7th/8th from the {ref}: {', '.join(occ)} (a potent Adhi-type yoga via Sudarshan chakra).",
                 "Read from the luminary, this gathering gives an unusually self-made, influential life.")
    return V(64, "NO", "No strong planetary gathering in the 6th/7th/8th from the Sun/Moon for this rule.")


@rule(65)
def _c65(pc):
    if psign(pc, "Mercury") in ENEMIES.get("Mercury", []) and aspects_planet(pc, "Jupiter", "Mercury"):
        return V(65, "HIT",
                 f"Mercury is in an enemy sign ({psign(pc,'Mercury')}) and aspected by Jupiter.",
                 "Speech can be blunt or unfiltered — a powerful voice that benefits from a moment's pause before it lands.")
    dig = pdig(pc, "Mercury")
    if dig in STRONG_DIG:
        return V(65, "PARTIAL", f"Mercury is {_dig_word(dig)} — speech is articulate and measured (the harsh-speech condition is absent).")
    return V(65, "NO", f"Mercury ({_dig_word(dig)}) does not meet the harsh-speech condition (enemy sign + Jupiter aspect).")


@rule(66)
def _c66(pc):
    l6 = hlord(pc, 6)
    fstatus = get_functional_status(l6, lagna(pc))
    strong = pdig(pc, l6) in STRONG_DIG or phouse(pc, l6) in UPACHAYA
    if fstatus == "functional_malefic" and (afflicted(pc, l6) or phouse(pc, l6) in DUSTHANA):
        return V(66, "HIT",
                 f"The 6th lord {l6} is a functional malefic and stressed (in the {_ord(phouse(pc,l6))}).",
                 "The 6th-house themes (debts, disease, disputes, enemies) can be active — strong immunity routines and prudent finances pay off.")
    if strong:
        return V(66, "HIT",
                 f"The 6th lord {l6} is strong ({_dig_word(pdig(pc,l6))}, {_ord(phouse(pc,l6))}).",
                 "Real power to defeat enemies, clear debts and win disputes — a fighter's advantage in conflict.")
    return V(66, "PARTIAL", f"The 6th lord {l6} is moderately placed ({_dig_word(pdig(pc,l6))}, {_ord(phouse(pc,l6))}).")


@rule(67)
def _c67(pc):
    jup_kendra = phouse(pc, "Jupiter") in KENDRA
    rahu_not_6 = phouse(pc, "Rahu") != 6
    if jup_kendra and rahu_not_6 and is_benefic(pc, "Jupiter"):
        return V(67, "HIT",
                 f"Jupiter sits in a kendra (the {_ord(phouse(pc,'Jupiter'))}) and Rahu is not in the 6th.",
                 "An Ashta-Laxmi blessing — the eight forms of fortune (wealth, food, courage, victory, children, status) are favoured for a happy, long life.")
    return V(67, "NO",
             f"Ashta-Laxmi conditions not fully met (Jupiter in kendra: {'yes' if jup_kendra else 'no'}; Rahu out of 6th: {'yes' if rahu_not_6 else 'no'}).")


@rule(68)
def _c68(pc):
    rh = phouse(pc, "Rahu")
    rs_idx = sign_index(psign(pc, "Rahu"))
    before = [p for p in PLANETS if p != "Rahu" and sign_index(psign(pc, p)) == (rs_idx - 1) % 12]
    after = [p for p in PLANETS if p != "Rahu" and sign_index(psign(pc, p)) == (rs_idx + 1) % 12]
    same = [p for p in PLANETS if p != "Rahu" and psign(pc, p) == psign(pc, "Rahu")]
    if (before and after) or same:
        det = "hemmed (kartari) by planets on both sides" if (before and after) else f"strongly joined by {', '.join(same)}"
        return V(68, "HIT",
                 f"Rahu (in the {_ord(rh)}) is {det}.",
                 "A survivor's signature — you can live like a king even through adversity, holding your ground when others fold.")
    return V(68, "NO", f"Rahu (in the {_ord(rh)}) is neither hemmed by planets nor strongly joined — this rule does not fire.")


@rule(69)
def _c69(pc):
    if not conjunct(pc, "Sun", "Mercury"):
        return V(69, "NO", "Sun and Mercury are not conjunct — no Budha-Aditya yoga.")
    pst = psign(pc, "Mercury") in PRISHTODAYA
    link = any(conj_or_aspect(pc, lord, "Mercury") for lord in (hlord(pc, 9), hlord(pc, 10)))
    if pst:
        return V(69, "PARTIAL",
                 f"Sun-Mercury conjunction, but in a Prishtodaya sign ({psign(pc,'Mercury')}) — sharp intellect that can turn cunning; channel it ethically.")
    return V(69, "HIT",
             f"Budha-Aditya yoga: Sun-Mercury conjunction in {psign(pc,'Mercury')}" + (" with a 9th/10th-lord link" if link else "") + ".",
             "Keen intelligence, good communication and administrative skill — a fine asset for study, writing and clever work.")


@rule(70)
def _c70(pc):
    if conjunct(pc, "Sun", "Saturn"):
        h = phouse(pc, "Sun")
        return V(70, "HIT",
                 f"Sun-Saturn conjunction in the {_ord(h)} house.",
                 "Authority earned the hard way, and some strain with father/bosses or chronic-type complaints — discipline turns this into endurance and earned respect.")
    return V(70, "NO", "Sun and Saturn are not conjunct — this rule does not fire.")


@rule(71)
def _c71(pc):
    # Venus and Mars relation affecting conjugal life
    if conj_or_aspect(pc, "Venus", "Mars"):
        rel = "conjunct" if conjunct(pc, "Venus", "Mars") else "in mutual aspect"
        return V(71, "HIT",
                 f"Venus and Mars are {rel}.",
                 "Strong passion and drive — magnetic in love, but the heat can spill into friction; conscious patience protects conjugal happiness. It also gives boldness over rivals.")
    return V(71, "NO", "Venus and Mars have no direct relation — this conjugal/passion rule does not fire.")


@rule(72)
def _c72(pc):
    kendra_planets = [p for p in PLANETS if phouse(pc, p) in KENDRA]
    strong_kendra = [p for p in kendra_planets if (set(houses_lorded_by(pc, p)) & (KENDRA | TRIKONA)) and not is_weak(pc, p)]
    if len(strong_kendra) >= 2:
        return V(72, "HIT",
                 f"Several kendra/trikona lords sit in kendras ({', '.join(strong_kendra)}) — the Tharai (kendra) strength.",
                 "Angular strength gives a commanding, stable life-structure — you build on solid ground.")
    if kendra_planets:
        return V(72, "PARTIAL", f"Planets in kendras ({', '.join(kendra_planets)}) but few are kendra/trikona lords — moderate Tharai strength.")
    return V(72, "NO", "Kendras are largely empty — this angular-strength rule is weak here.")


@rule(73)
def _c73(pc):
    flags = []
    for b in ("Jupiter", "Venus"):
        if conjunct(pc, "Rahu", b) and phouse(pc, "Rahu") not in DUSTHANA:
            flags.append(f"{b} with Rahu in a good house (saintly, honest streak)")
    if phouse(pc, "Jupiter") in (KENDRA | TRIKONA) and not afflicted(pc, "Jupiter"):
        flags.append("strong, clean Jupiter (principled nature)")
    if flags:
        return V(73, "HIT", "; ".join(flags) + ".",
                 "A fundamentally honest, fearless and principled nature — people trust you, and you tend to a long, upright life.")
    return V(73, "NO", "No clear 'honest person' combination (benefic+Rahu in good house, or clean strong Jupiter) is present.")


@rule(74)
def _c74(pc):
    factors = []
    if conj_or_aspect_house(pc, "Saturn", 1):
        factors.append("lagna")
    if conj_or_aspect_house(pc, "Saturn", 2):
        factors.append("2nd")
    if conj_or_aspect_house(pc, "Saturn", 5):
        factors.append("5th")
    sat_benefic = get_functional_status("Saturn", lagna(pc)) in ("functional_benefic", "yogakaraka")
    if len(factors) >= 2:
        return V(74, "HIT",
                 f"Saturn influences the learning factors ({', '.join(factors)})" + (" and is a benefic for your lagna" if sat_benefic else "") + ".",
                 "Deep, disciplined learning — concentration and persistence let you master subjects others give up on." if sat_benefic
                 else "Strong focus, though Saturn's pressure on learning can feel heavy — steady effort wins.")
    return V(74, "NO", f"Saturn touches only {len(factors)} of the three learning factors (lagna/2nd/5th) — this 'learned' rule is weak here.")


@rule(75)
def _c75(pc):
    flags = []
    for trik in (6, 8, 12):
        tl = hlord(pc, trik)
        # malefic (not the trik lord) afflicting trik lord, not debilitated, not aspected by trik lord
        for m in NAT_MALEFIC:
            if m == tl:
                continue
            if conj_or_aspect(pc, m, tl) and not is_weak(pc, m) and not aspects_planet(pc, tl, m):
                flags.append(f"{_ord(trik)} lord {tl} has a pure malefic affliction from {m}")
    if flags:
        return V(75, "HIT", "; ".join(set(flags)) + ".",
                 "A flag for periods of real hardship — but forewarned is forearmed; remedies for the afflicting malefic and the trik lord lighten it considerably.")
    return V(75, "NO", "No trik lord carries the 'pure malefic relation' this miserable-life rule requires.")


@rule(76)
def _c76(pc):
    l10 = hlord(pc, 10)
    dig = pdig(pc, l10)
    h = phouse(pc, l10)
    if dig in STRONG_DIG or h in (KENDRA | TRIKONA | {11}):
        return V(76, "HIT",
                 f"The 10th lord {l10} is well placed ({_dig_word(dig)}, in the {_ord(h)}).",
                 "Career rewards your effort — a strong 10th lord means your mental and physical work translates into real success.")
    if dig in WEAK_DIG or h in DUSTHANA:
        return V(76, "HIT",
                 f"The 10th lord {l10} is under pressure ({_dig_word(dig)}, in the {_ord(h)}).",
                 "Career success comes through extra effort and a few detours — persistence and 10th-lord remedies steady the climb.")
    return V(76, "PARTIAL", f"The 10th lord {l10} is moderately placed ({_dig_word(dig)}, {_ord(h)}) — a workmanlike career path.")


@rule(77)
def _c77(pc):
    tenth_sign = house_sign(10, lagna(pc))
    elevated = EXALT_SIGN_PLANET.get(tenth_sign)
    notes = []
    if elevated and phouse(pc, elevated) == 10:
        notes.append(f"{elevated} (which exalts in your 10th sign {tenth_sign}) actually sits in the 10th")
    # from Moon
    moon_tenth_sign = SIGNS[(sign_index(psign(pc, "Moon")) + 9) % 12]
    elevated_m = EXALT_SIGN_PLANET.get(moon_tenth_sign)
    if elevated_m and ((sign_index(psign(pc, elevated_m)) - sign_index(psign(pc, "Moon"))) % 12 + 1) == 10:
        notes.append(f"{elevated_m} occupies the 10th from the Moon (mental chart)")
    if notes:
        return V(77, "HIT", "; ".join(notes) + ".",
                 "Your career sign is graced by its 'elevated' planet — a natural lift to status and professional recognition.")
    return V(77, "NO", f"The elevated planet for your 10th sign ({tenth_sign}) does not occupy the 10th from lagna or Moon.")


@rule(78)
def _c78(pc):
    from astro_precompute import check_neecha_bhanga
    res = []
    for p in DIGNITY_TABLE:
        if p in ("Rahu", "Ketu"):
            continue
        if pdig(pc, p) == "debilitated":
            nb = check_neecha_bhanga(p, psign(pc, p), pc.get("planets", {}), lagna(pc))
            if nb.get("applicable") and nb.get("rules_fired" if False else "verdict"):
                res.append(f"{p} (debilitated in {psign(pc,p)}) gains Neecha-Bhanga")
            elif nb.get("applicable"):
                # check if any cancellation present via 'verdict'
                if nb.get("verdict") and "no cancellation" not in str(nb.get("verdict", "")).lower():
                    res.append(f"{p} (debilitated in {psign(pc,p)}) gains Neecha-Bhanga")
    if res:
        return V(78, "HIT", "; ".join(res) + " — the debilitation reverses into strength.",
                 "A 'rags-to-riches' spring: a fallen planet that bounces back gives wealth and success, often after an early struggle.")
    return V(78, "NO", "No debilitated planet gains Neecha-Bhanga cancellation here, so this wealth-from-reversal rule does not fire.")


@rule(79)
def _c79(pc):
    pair_house = {}
    for p in ("Ketu", "Venus", "Mars"):
        pair_house.setdefault(phouse(pc, p), []).append(p)
    together = [(h, ps) for h, ps in pair_house.items() if len(ps) >= 2]
    all_related = conj_or_aspect(pc, "Ketu", "Venus") and conj_or_aspect(pc, "Ketu", "Mars")
    if any(len(ps) == 3 for _, ps in together) or all_related:
        in_trik = phouse(pc, "Ketu") in DUSTHANA
        return V(79, "HIT",
                 "Ketu, Venus and Mars are joined/related" + (f" (in the {_ord(phouse(pc,'Ketu'))})" if any(len(ps)==3 for _,ps in together) else "") + ".",
                 ("A king-like, widely-respected life — though in the 6th/8th it gives high position with attached troubles." if in_trik
                  else "A king-like, widely-respected life — dignity and regard from those around you, even without high office."))
    if together:
        h, ps = together[0]
        return V(79, "PARTIAL", f"Two of Ketu/Venus/Mars ({', '.join(ps)}) meet in the {_ord(h)}, but not all three — partial yoga.")
    return V(79, "NO", "Ketu, Venus and Mars are not joined/related — this royal combination is absent.")


@rule(80)
def _c80(pc):
    pairs = []
    bens = ["Jupiter", "Venus", "Mercury", "Moon"]
    for i in range(len(bens)):
        for j in range(i + 1, len(bens)):
            a, b = bens[i], bens[j]
            if is_benefic(pc, a) and is_benefic(pc, b) and conj_or_aspect(pc, a, b):
                pairs.append(f"{a}~{b}")
    if pairs:
        return V(80, "HIT", f"Benefic pair(s) in mutual relation: {', '.join(pairs)}.",
                 "Two benefics reinforcing each other smooth the significations they share — a gentle, supportive thread in life.")
    return V(80, "NO", "No two natural benefics are in mutual relation for this rule.")


@rule(81)
def _c81(pc):
    fifth = phouse_occ_benefic(pc, 5)
    jup_ok = conj_or_aspect(pc, "Jupiter", "Moon") or phouse(pc, "Jupiter") in (KENDRA | TRIKONA)
    if fifth or jup_ok:
        bits = []
        if fifth:
            bits.append(f"benefic influence on the 5th ({', '.join(fifth)})")
        if jup_ok:
            bits.append("Jupiter well linked")
        return V(81, "HIT", "; ".join(bits) + " (Nara-yoga support).",
                 "A sound body and the blessing of children/creativity — vitality and progeny are favoured.")
    return V(81, "NO", "Nara-yoga support (benefic on the 5th / well-linked Jupiter) is not clearly present.")


@rule(82)
def _c82(pc):
    jup_kendra = phouse(pc, "Jupiter") in KENDRA
    rahu6 = phouse(pc, "Rahu") == 6
    ben_rel = any(is_benefic(pc, b) and b != "Jupiter" and conj_or_aspect(pc, "Jupiter", b) for b in NAT_BENEFIC)
    if jup_kendra and (ben_rel or rahu6):
        return V(82, "HIT",
                 f"Jupiter in a kendra (the {_ord(phouse(pc,'Jupiter'))})" + (" with a benefic relation" if ben_rel else "") + (" and Rahu in the 6th" if rahu6 else "") + ".",
                 "An 'honoured and never defeated' yoga — wisdom and grace win you respect and protect you in conflict.")
    if jup_kendra:
        return V(82, "PARTIAL", f"Jupiter is in a kendra (the {_ord(phouse(pc,'Jupiter'))}) but the supporting benefic-relation / Rahu-in-6th rider is missing.")
    return V(82, "NO", "Jupiter is not in a kendra — this 'Good Yoga' does not fire.")


@rule(83)
def _c83(pc):
    # Maha Shakti: strong Mars/Saturn or malefic conviction, esp. echoed in Navamsha
    strong_warrior = (pdig(pc, "Mars") in STRONG_DIG and phouse(pc, "Mars") in (KENDRA | TRIKONA))
    nav_echo = navsign(pc, "Mars") and get_dignity("Mars", navsign(pc, "Mars")) in STRONG_DIG
    if strong_warrior or nav_echo:
        return V(83, "HIT",
                 f"Mars stands powerful ({_dig_word(pdig(pc,'Mars'))}, the {_ord(phouse(pc,'Mars'))})" + (" and strong again in Navamsha" if nav_echo else "") + ".",
                 "A Maha-Shakti resolve — once you set a goal you are hard to stop; this conviction is your superpower." + (" Felt permanently, as it is confirmed in Navamsha." if nav_echo else ""))
    return V(83, "NO", "Mars/Maha-Shakti strength (dignified Mars in kendra/trikona, or confirmed in Navamsha) is not present.")


# ── extra small helpers used above ──────────────────────────────────
def conj_or_aspect_house(pc, planet, house):
    return phouse(pc, planet) == house or aspects_house(pc, planet, house)

def phouse_occ_benefic(pc, house):
    return [p for p in occupants(pc, house) if is_benefic(pc, p)] + \
           [p for p in NAT_BENEFIC if is_benefic(pc, p) and aspects_house(pc, p, house)]


# ════════════════════════════════════════════════════════════════════
#  TRANSIT / ANNUAL ACCESSORS  (need pc["_transit"] / pc["_annual"])
# ════════════════════════════════════════════════════════════════════
def _tx(pc):
    t = pc.get("_transit")
    return t if isinstance(t, dict) and not t.get("error") else None

def _an(pc):
    a = pc.get("_annual")
    return a if isinstance(a, dict) and not a.get("error") else None

def tsign(pc, p):
    return ((_tx(pc) or {}).get("positions", {}).get(p, {}) or {}).get("sign", "")

def t_house_natal(pc, p):
    return ((_tx(pc) or {}).get("positions", {}).get(p, {}) or {}).get("house_natal", 0)

def t_from_moon(pc, p):
    return ((_tx(pc) or {}).get("positions", {}).get(p, {}) or {}).get("from_moon", 0)

def _sign_in_trine(sign_a, sign_b):
    if not sign_a or not sign_b:
        return False
    return (sign_index(sign_a) - sign_index(sign_b)) % 12 in (0, 4, 8)

def _t_aspects_sign(pc, p_from, target_sign):
    """Does the transiting planet aspect target_sign (whole-sign graha drishti)?"""
    s = tsign(pc, p_from)
    return bool(target_sign) and target_sign in aspected_signs(p_from, s)

def _an_house_lord(pc, h):
    """Lord of house h reckoned from the annual lagna."""
    an = _an(pc) or {}
    al = an.get("lagna_sign", "")
    if not al:
        return ""
    return SIGN_LORDS.get(SIGNS[(sign_index(al) + h - 1) % 12], "")

def _an_planet_house(pc, p):
    return ((_an(pc) or {}).get("positions", {}).get(p, {}) or {}).get("house", 0)

def _strength_category(score):
    if score is None:
        return "unknown"
    if score > 15:
        return "extraordinary"
    if score >= 10:
        return "strong"
    if score >= 5:
        return "medium"
    return "weak"

def _NA_transit(no):
    return V(no, "NA", RULE_META[no].get("manual", "Needs current transit positions."))

def _NA_annual(no):
    return V(no, "NA", RULE_META[no].get("manual", "Needs the annual (Varshaphal) chart."))


# ════════════════════════════════════════════════════════════════════
#  CHECKERS – chapters 84-97 (Saturn / Jupiter transits)
# ════════════════════════════════════════════════════════════════════
HOUSE_TRANSIT_THEME = {
    1: "self, health and overall direction", 2: "wealth, family and speech",
    3: "courage, siblings and initiative", 4: "home, mother, property and peace of mind",
    5: "children, studies, romance and creativity", 6: "work, debts, health and rivals",
    7: "marriage, partnerships and public dealings", 8: "upheaval, transformation and joint resources",
    9: "luck, father, dharma and long journeys", 10: "career, status and reputation",
    11: "gains, income and fulfilment of desires", 12: "expenses, travel, sleep and letting-go",
}


@rule(84)
def _c84(pc):
    if not _tx(pc):
        return _NA_transit(84)
    sat = tsign(pc, "Saturn")
    natal_here = [p for p in PLANETS if psign(pc, p) == sat]
    if natal_here:
        return V(84, "HIT",
                 f"Transiting Saturn is in {sat}, the very sign of your natal {', '.join(natal_here)}.",
                 f"A phase of major, structural change tied to {', '.join(natal_here)} — it builds while Saturn is in {sat} and peaks as it crosses the exact degree. Use it to rebuild, not resist.")
    return V(84, "NO", f"Transiting Saturn ({sat}) is not yet on the sign of any natal planet — no 'big change' trigger right now.")


@rule(85)
def _c85(pc):
    if not _tx(pc):
        return _NA_transit(85)
    d9 = pc.get("divisional", {}).get("D9", {})
    nav_lagna = d9.get("Lagna") or d9.get("lagna")
    if not nav_lagna:
        return V(85, "NA", "Navamsha lagna not available to apply the Saturn-transit-in-Navamsha rule.")
    nav_lord = SIGN_LORDS.get(nav_lagna, "")
    sat = tsign(pc, "Saturn")
    if _sign_in_trine(sat, nav_lagna) or (nav_lord and (psign(pc, nav_lord) == sat or _sign_in_trine(sat, psign(pc, nav_lord)))):
        return V(85, "HIT",
                 f"Transiting Saturn ({sat}) relates to the trine of your Navamsha lagna ({nav_lagna}) / its lord {nav_lord}.",
                 "By the Navamsha-Saturn method this is an event-bearing transit — significant, karmically-weighted developments are due in this window.")
    return V(85, "NO", f"Transiting Saturn ({sat}) does not relate to the trine of your Navamsha lagna {nav_lagna} — no event trigger by this method now.")


@rule(86)
def _c86(pc):
    if not _tx(pc):
        return _NA_transit(86)
    h = t_house_natal(pc, "Saturn")
    theme = HOUSE_TRANSIT_THEME.get(h, "")
    return V(86, "HIT",
             f"Transiting Saturn is moving through your {_ord(h)} house ({tsign(pc,'Saturn')}).",
             f"Saturn is currently working on your {theme}. Expect slow, serious lessons here — patience, discipline and honest effort are rewarded; shortcuts are not.")


@rule(87)
def _c87(pc):
    if not _tx(pc):
        return _NA_transit(87)
    fm = t_from_moon(pc, "Saturn")
    if fm in (3, 6, 11):
        return V(87, "HIT",
                 f"Transiting Saturn is in the {_ord(fm)} from your natal Moon — a classically favourable Saturn transit.",
                 "A constructive Saturn window: steady gains, the upper hand over rivals, and rewards for disciplined effort. A good time to consolidate.")
    return V(87, "NO", f"Transiting Saturn is in the {_ord(fm)} from your Moon — not one of the favourable (3/6/11) transit positions just now.")


@rule(88)
def _c88(pc):
    if not _tx(pc):
        return _NA_transit(88)
    fm = t_from_moon(pc, "Saturn")
    if fm in (1, 2, 12, 4, 8):
        return V(88, "HIT",
                 f"Transiting Saturn is in the {_ord(fm)} from your natal Moon — a demanding Saturn transit position.",
                 "A testing Saturn window: extra responsibility, slower results and a need for caution in health and big decisions. Steady routines and remedies for Saturn help you through.")
    return V(88, "NO", f"Transiting Saturn is in the {_ord(fm)} from your Moon — not one of the stressful (1/2/4/8/12) positions just now.")


@rule(89)
def _c89(pc):
    if not _tx(pc):
        return _NA_transit(89)
    jsign = psign(pc, "Jupiter")
    sat = tsign(pc, "Saturn")
    if sat == jsign or _t_aspects_sign(pc, "Saturn", jsign):
        rel = "sits on" if sat == jsign else "aspects"
        return V(89, "HIT",
                 f"Transiting Saturn {rel} your natal Jupiter ({jsign}).",
                 "A Saturn-on-Jupiter phase — a meeting of discipline and wisdom that often marks a turning point in growth, finances or beliefs. Big commitments mature now.")
    return V(89, "NO", f"Transiting Saturn ({sat}) does not currently contact your natal Jupiter ({jsign}).")


@rule(90)
def _c90(pc):
    if not _tx(pc):
        return _NA_transit(90)
    jsign = psign(pc, "Jupiter")
    sat = tsign(pc, "Saturn")
    if _sign_in_trine(sat, jsign) and sat != jsign:
        return V(90, "HIT",
                 f"Transiting Saturn ({sat}) is trine to your natal Jupiter ({jsign}).",
                 "A supportive Saturn-Jupiter trine — patient effort meets good fortune; a favourable stretch for long-term plans and steady advancement.")
    return V(90, "NO", f"Transiting Saturn ({sat}) is not in trine to your natal Jupiter ({jsign}) right now.")


@rule(91)
def _c91(pc):
    if not _tx(pc):
        return _NA_transit(91)
    l8 = hlord(pc, 8)
    axis = {psign(pc, l8), SIGNS[(sign_index(psign(pc, l8)) + 6) % 12]}
    if tsign(pc, "Saturn") in axis:
        return V(91, "HIT",
                 f"Transiting Saturn is on your 8th-lord ({l8}) axis ({'/'.join(sorted(axis))}).",
                 "A karmically-loaded transit on the transformation axis — old patterns and past actions surface for settlement. Handle health and obligations carefully; results depend on the running dasha.")
    return V(91, "NO", f"Transiting Saturn is not on your 8th-lord ({l8}) axis just now — this past-karma transit is not active.")


@rule(92)
def _c92(pc):
    if not _tx(pc):
        return _NA_transit(92)
    l8 = hlord(pc, 8)
    axis = {psign(pc, l8), SIGNS[(sign_index(psign(pc, l8)) + 6) % 12]}
    hot = [m for m in ("Mars", "Rahu", "Ketu") if tsign(pc, m) in axis]
    if hot:
        return V(92, "HIT",
                 f"Malefic transit ({', '.join(hot)}) on your 8th-lord ({l8}) axis.",
                 "A fast trigger on the past-karma axis — events can move suddenly here. Stay measured; the effect ripens only when the dasha agrees.")
    return V(92, "NO", f"No fast malefic (Mars/Rahu/Ketu) is on your 8th-lord ({l8}) axis right now.")


@rule(93)
def _c93(pc):
    if not _tx(pc):
        return _NA_transit(93)
    ll = lagna_lord(pc)
    l10 = hlord(pc, 10)
    triggers = []
    for slow in ("Saturn", "Rahu", "Jupiter"):
        for tgt, lbl in ((ll, "lagna lord " + ll), (l10, "10th lord " + l10)):
            if tsign(pc, slow) == psign(pc, tgt) or _t_aspects_sign(pc, slow, psign(pc, tgt)):
                triggers.append(f"{slow} on/aspecting your {lbl}")
    if triggers:
        return V(93, "HIT",
                 "; ".join(sorted(set(triggers))) + ".",
                 "The makings of a stand-out event around identity or career are in the air — a slow planet is spotlighting a key chart-ruler. Whether it lands well depends on the running dasha.")
    return V(93, "NO", "No slow planet is currently spotlighting your lagna lord or 10th lord — no outstanding-event trigger now.")


@rule(94)
def _c94(pc):
    if not _tx(pc):
        return _NA_transit(94)
    triggers = []
    for m in ("Saturn", "Mars", "Rahu", "Ketu"):
        if t_house_natal(pc, m) == 8:
            triggers.append(f"{m} transiting your 8th house")
        if tsign(pc, m) == psign(pc, "Moon"):
            triggers.append(f"{m} over your natal Moon")
    if triggers:
        return V(94, "HIT",
                 "; ".join(sorted(set(triggers))) + ".",
                 "A sensitive, accident/upheaval-prone window — not a prophecy, a caution. Avoid unnecessary risks and keep health and travel guarded; benefic days and remedies soften it.")
    return V(94, "NO", "No heavy malefic is on your 8th house or natal Moon right now — this disaster-window is not active.")


@rule(95)
def _c95(pc):
    if not _tx(pc):
        return _NA_transit(95)
    lg = lagna(pc)
    ll = lagna_lord(pc)
    mal_on_lagna = [m for m in ("Saturn", "Mars", "Rahu", "Ketu")
                    if tsign(pc, m) == lg or tsign(pc, m) == psign(pc, ll)]
    jup_guard = (tsign(pc, "Jupiter") == lg) or _t_aspects_sign(pc, "Jupiter", lg)
    if mal_on_lagna and not jup_guard:
        return V(95, "HIT",
                 f"Malefic transit ({', '.join(mal_on_lagna)}) on your lagna / lagna lord, with no Jupiter protection.",
                 "A delicate stretch where setbacks can crop up — stay conservative with big moves. A Jupiter day, charity and patience act as the shield the chart is missing now.")
    if mal_on_lagna and jup_guard:
        return V(95, "PARTIAL",
                 f"Malefic transit ({', '.join(mal_on_lagna)}) touches the lagna, but Jupiter is also guarding it — the bad effect is largely averted.")
    return V(95, "NO", "No malefic is stressing your lagna/lagna lord right now — this unfortunate-event window is not active.")


@rule(96)
def _c96(pc):
    if not _tx(pc):
        return _NA_transit(96)
    l6, l8 = hlord(pc, 6), hlord(pc, 8)
    triggers = []
    for m in ("Saturn", "Mars", "Rahu", "Ketu"):
        if t_house_natal(pc, m) in (6, 8):
            triggers.append(f"{m} in your {_ord(t_house_natal(pc,m))} house")
        if tsign(pc, m) in (psign(pc, l6), psign(pc, l8)):
            triggers.append(f"{m} on your {'6th' if tsign(pc,m)==psign(pc,l6) else '8th'} lord")
    if triggers:
        return V(96, "HIT",
                 "; ".join(sorted(set(triggers))) + ".",
                 "A health-watch window — the disease axis (6th/8th) is being stirred by malefic transit. Prioritise rest, diet and check-ups; most of this passes with care.")
    return V(96, "NO", "The 6th/8th disease axis is not under malefic transit right now — no special health flag from transits.")


@rule(97)
def _c97(pc):
    if not _tx(pc):
        return _NA_transit(97)
    fm = t_from_moon(pc, "Saturn")
    if fm in (12, 1, 2):
        phase = {12: "first (rising) phase", 1: "peak (middle) phase", 2: "last (setting) phase"}[fm]
        return V(97, "HIT",
                 f"Saturn is transiting the {_ord(fm)} from your natal Moon — you are in the {phase} of Sade Sati.",
                 "Sade Sati is on: a maturing, sometimes heavy 7½-year passage that restructures life and builds lasting strength. Keep routines steady, serve others, and lean on Saturn/Hanuman remedies — this phase rewards endurance.")
    return V(97, "NO", f"Saturn is in the {_ord(fm)} from your Moon — you are NOT currently in Sade Sati (it runs over the 12th/1st/2nd from the Moon).")


# ════════════════════════════════════════════════════════════════════
#  CHECKERS – chapters 98-108 (annual / Varshaphal chart)
# ════════════════════════════════════════════════════════════════════
def _yr(pc):
    an = _an(pc)
    return f" (year from {an['return_date']})" if an else ""


@rule(98)
def _c98(pc):
    an = _an(pc)
    if not an:
        return _NA_annual(98)
    yl, cat, bala = an.get("year_lord"), an.get("year_lord_strength"), an.get("year_lord_bala")
    base = f"This year's Year Lord (Varshesha) is {yl}, with {bala} units of Panch-Vargiya strength — rated '{cat}'.{_yr(pc)}"
    if cat in ("extraordinary", "strong"):
        return V(98, "HIT", base, "A strong Year Lord promises a productive, supportive year — your plans find backing and momentum.")
    if cat == "medium":
        return V(98, "PARTIAL", base, "A moderate year — results come with steady effort rather than easy flow.")
    return V(98, "NO", base + " A weak Year Lord asks for patience this year; consolidate rather than over-extend.")


@rule(99)
def _c99(pc):
    an = _an(pc)
    if not an:
        return _NA_annual(99)
    same = []
    for p in PLANETS:
        ns = an.get("positions", {}).get(p, {}).get("sign", "")
        if ns and ns == psign(pc, p):
            tag = ""
            if get_dignity(p, ns) in STRONG_DIG:
                tag = f" ({_dig_word(get_dignity(p,ns))} — extra weight)"
            same.append(f"{p} ({ns}){tag}")
    if same:
        return V(99, "HIT",
                 f"Planet(s) repeating their birth sign in this year's chart: {', '.join(same)}.{_yr(pc)}",
                 "These planets are 'reactivated' this year — the life areas they rule (per their natal role) become eventful and prominent.")
    return V(99, "NO", f"No planet repeats its exact birth sign in this year's annual chart — a relatively routine year on this count.{_yr(pc)}")


@rule(100)
def _c100(pc):
    an = _an(pc)
    if not an:
        return _NA_annual(100)
    al, all_ = an.get("lagna_sign"), an.get("lagna_lord")
    h = _an_planet_house(pc, all_)
    bala = an.get("pvb", {}).get(all_)
    cat = _strength_category(bala) if bala is not None else "unknown"
    base = f"This year's ascendant is {al}; its lord {all_} sits in the {_ord(h)} of the annual chart with '{cat}' strength ({bala})."
    if cat in ("extraordinary", "strong") and h not in (6, 8, 12):
        return V(100, "HIT", base, "The year's ruler is strong and well placed — a year that moves in your favour and rewards initiative.")
    if cat == "weak" or h in (6, 8, 12):
        return V(100, "PARTIAL", base + " Pace yourself — the year asks for prudence in the affairs of that house.")
    return V(100, "PARTIAL", base)


@rule(101)
def _c101(pc):
    an = _an(pc)
    if not an:
        return _NA_annual(101)
    cat, bala, lord = an.get("natal_lagna_lord_strength"), an.get("natal_lagna_lord_bala"), an.get("natal_lagna_lord")
    base = f"Your birth lagna lord {lord} carries {bala} units ('{cat}') in this year's chart.{_yr(pc)}"
    if cat in ("extraordinary", "strong"):
        return V(101, "HIT", base, "Your core self is well supported this year — confidence, health and personal agendas get a green light.")
    if cat == "medium":
        return V(101, "PARTIAL", base, "A workable year for personal goals — push steadily.")
    return V(101, "NO", base + " Protect health and energy this year and avoid over-commitment; strengthen your lagna lord.")


@rule(102)
def _c102(pc):
    an = _an(pc)
    if not an:
        return _NA_annual(102)
    pvb = an.get("pvb", {})
    all_ = an.get("lagna_lord")
    annual_lagna_strong = (pvb.get(all_, 0) or 0) >= 10
    trine_lords = {hlord(pc, h) for h in (1, 5, 9)}
    kendra_lords = {hlord(pc, h) for h in (1, 4, 7, 10)}
    raj_planets = (trine_lords & kendra_lords) or set()
    # planets forming natal raj yoga (trine-kendra lord relation)
    raj_strong = [p for p in (trine_lords | kendra_lords) if (pvb.get(p, 0) or 0) >= 10]
    if annual_lagna_strong and raj_strong:
        return V(102, "HIT",
                 f"This year the annual lagna lord {all_} is strong and your Raj-Yoga planet(s) {', '.join(sorted(set(raj_strong)))} are also strong in the year chart.{_yr(pc)}",
                 "A year when your birth Raj Yoga can actually fruit — favourable for promotion, recognition and a jump in status.")
    if raj_strong:
        return V(102, "PARTIAL",
                 f"Raj-Yoga planet(s) {', '.join(sorted(set(raj_strong)))} are strong this year, but the annual lagna lord {all_} is not strong enough to fully deliver — partial fruiting.")
    return V(102, "NO", f"This year's chart does not strongly activate your Raj Yoga (annual lagna lord {all_} / raj-yoga planets are not strong enough).{_yr(pc)}")


@rule(103)
def _c103(pc):
    an = _an(pc)
    if not an:
        return _NA_annual(103)
    trp = an.get("tri_rashi_pati")
    bala = an.get("pvb", {}).get(trp)
    cat = _strength_category(bala) if bala is not None else "unknown"
    h = _an_planet_house(pc, trp)
    base = f"The Tri-Rashi-Pati for this year is {trp} (in the {_ord(h)} of the annual chart, '{cat}' strength {bala}).{_yr(pc)}"
    if cat in ("extraordinary", "strong") and h not in (6, 8, 12):
        return V(103, "HIT", base, "The year's alternate ruler is strong — it adds a steadying, favourable hand to the whole year.")
    if cat == "weak" or h in (6, 8, 12):
        return V(103, "PARTIAL", base + " It is not at its best, so keep expectations grounded.")
    return V(103, "PARTIAL", base)


@rule(104)
def _c104(pc):
    an = _an(pc)
    if not an:
        return _NA_annual(104)
    all_ = an.get("lagna_lord")
    ml = an.get("muntha_lord")
    h_all = _an_planet_house(pc, all_)
    h_ml = _an_planet_house(pc, ml)
    flags = []
    if h_all in (1, 7):
        flags.append(f"annual lagna lord {all_} on the 1-7 (marriage) axis")
    if h_ml in (1, 7):
        flags.append(f"Muntha lord {ml} on the 1-7 axis")
    if flags:
        return V(104, "HIT", "; ".join(flags) + f".{_yr(pc)}",
                 "A year that activates the marriage/partnership axis — relevant for marriage, a new partnership, or a notable development with the spouse.")
    return V(104, "NO", f"Neither the annual lagna lord {all_} nor the Muntha lord {ml} sits on the 1-7 axis this year — not a flagged marriage year.{_yr(pc)}")


@rule(105)
def _c105(pc):
    an = _an(pc)
    if not an:
        return _NA_annual(105)
    yl = an.get("year_lord")
    al = an.get("lagna_sign")
    owned = []
    if al and yl:
        for h in range(1, 13):
            if SIGN_LORDS.get(SIGNS[(sign_index(al) + h - 1) % 12], "") == yl:
                owned.append(h)
    h = _an_planet_house(pc, yl)
    good = bool(set(owned) & (KENDRA | TRIKONA | {11, 2})) and h not in (6, 8, 12)
    base = f"The Year Lord {yl} owns the {', '.join(_ord(x) for x in owned) or '—'} of the annual chart and sits in the {_ord(h)}.{_yr(pc)}"
    if good:
        return V(105, "HIT", base, "Its houses point to gains this year — income, status and the affairs it owns tend to grow.")
    if set(owned) & {6, 8, 12} or h in (6, 8, 12):
        return V(105, "PARTIAL", base + " Some of its houses are difficult, so guard those areas and expenses.")
    return V(105, "PARTIAL", base)


@rule(106)
def _c106(pc):
    an = _an(pc)
    if not an:
        return _NA_annual(106)
    trp = an.get("tri_rashi_pati")
    bala = an.get("pvb", {}).get(trp)
    h = _an_planet_house(pc, trp)
    afflicted_trp = (bala is not None and bala < 5) or h in (6, 8, 12)
    base = f"Tri-Rashi-Pati {trp}: strength {bala}, placed in the {_ord(h)} of the annual chart.{_yr(pc)}"
    if afflicted_trp:
        return V(106, "HIT", base + " It is afflicted/weak.",
                 "A caution flag for a difficult year — go slow on risky ventures, double-check commitments, and keep remedies up for a smoother passage.")
    return V(106, "NO", base + " It is not afflicted, so this 'very bad year' warning does not apply.")


@rule(107)
def _c107(pc):
    an = _an(pc)
    if not an:
        return _NA_annual(107)
    ml = an.get("muntha_lord")
    msign = an.get("muntha_sign")
    mh = an.get("muntha_house")
    bala = an.get("pvb", {}).get(ml)
    cat = _strength_category(bala) if bala is not None else "unknown"
    base = f"Muntha is in {msign} (the {_ord(mh)} of the annual chart); its lord {ml} has '{cat}' strength ({bala}).{_yr(pc)}"
    if cat in ("extraordinary", "strong") and mh not in (6, 8, 12):
        return V(107, "HIT", base, f"The year's main theme ({HOUSE_TRANSIT_THEME.get(mh,'that house')}) is well supported — a constructive focus for the year.")
    if cat == "weak" or mh in (6, 8, 12):
        return V(107, "PARTIAL", base + f" The year's focus ({HOUSE_TRANSIT_THEME.get(mh,'that house')}) needs care.")
    return V(107, "PARTIAL", base)


@rule(108)
def _c108(pc):
    an = _an(pc)
    if not an:
        return _NA_annual(108)
    bl = an.get("natal_lagna_lord")
    al = an.get("lagna_sign")
    bl_house = _an_planet_house(pc, bl)
    close = bl_house in (KENDRA | TRIKONA)
    same = an.get("positions", {}).get(bl, {}).get("sign", "") == al
    if same or close:
        rel = "sits in the annual ascendant itself" if same else f"is in a kendra/trikona (the {_ord(bl_house)}) from the annual ascendant"
        return V(108, "HIT",
                 f"Your birth lagna lord {bl} {rel} this year.{_yr(pc)}",
                 "A close tie between your core self and the year's chart — your personal goals and the year's flow are well aligned; a year to act on your own initiative.")
    return V(108, "NO", f"Your birth lagna lord {bl} is in the {_ord(bl_house)} from the annual ascendant — not closely tied to this year's chart, so the year feels less personally yours.{_yr(pc)}")


# ════════════════════════════════════════════════════════════════════
#  DRIVER
# ════════════════════════════════════════════════════════════════════
def evaluate_all(pc: dict) -> list[RuleVerdict]:
    out: list[RuleVerdict] = []
    for no in range(1, 109):
        meta = RULE_META[no]
        fn = CHECKERS.get(no)
        if fn is None:
            out.append(RuleVerdict(no, meta["title"], meta["category"], meta["condition"],
                                   "NA", meta.get("manual", "Requires a transit/annual chart — not auto-evaluated."),
                                   ""))
            continue
        try:
            out.append(fn(pc))
        except Exception as exc:  # noqa: BLE001
            out.append(RuleVerdict(no, meta["title"], meta["category"], meta["condition"],
                                   "NA", f"(could not evaluate: {exc})", ""))
    return out


def summarize(verdicts: list[RuleVerdict]) -> dict:
    counts = {"HIT": 0, "PARTIAL": 0, "NO": 0, "NA": 0}
    for v in verdicts:
        counts[v.verdict] = counts.get(v.verdict, 0) + 1
    return counts


if __name__ == "__main__":
    import argparse
    from astro_chart_bridge import compute_chart

    ap = argparse.ArgumentParser(description="Check a chart against the 108 predictive-technique rules")
    ap.add_argument("--name", default="Ritesh")
    ap.add_argument("--dob", default="1985-03-08")
    ap.add_argument("--time", default="13:05")
    ap.add_argument("--place", default="Patna, India")
    ap.add_argument("--lat", type=float, default=25.5941)
    ap.add_argument("--lon", type=float, default=85.1376)
    ap.add_argument("--tz", type=float, default=5.5)
    args = ap.parse_args()

    pc = compute_chart(client_name=args.name, dob=args.dob, birth_time=args.time,
                       place=args.place, latitude=args.lat, longitude=args.lon, timezone=args.tz)
    vs = evaluate_all(pc)
    c = summarize(vs)
    print(f"Lagna {lagna(pc)} | counts: {c}")
    for v in vs:
        if v.verdict in ("HIT", "PARTIAL"):
            print(f"  #{v.no:>3} [{v.verdict:7}] {v.title}: {v.finding[:120]}")
