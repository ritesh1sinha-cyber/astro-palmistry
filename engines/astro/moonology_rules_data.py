#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yasmin Boland Moonology (Hay House 2016) - Daily Moon + phase rules. Source: rules44."""
from __future__ import annotations

SIGN_ELEMENTS: dict[str, str] = {
    "Aries": "Fire",
    "Leo": "Fire",
    "Sagittarius": "Fire",
    "Taurus": "Earth",
    "Virgo": "Earth",
    "Capricorn": "Earth",
    "Gemini": "Air",
    "Libra": "Air",
    "Aquarius": "Air",
    "Cancer": "Water",
    "Scorpio": "Water",
    "Pisces": "Water",
}

ELEMENT_FLAVOUR: dict[str, str] = {
    "Fire": "fiery, impulsive, passionate emotional tone",
    "Earth": "grounded, practical, stable emotional tone",
    "Air": "chatty, flighty, intellectual emotional tone",
    "Water": "emotional, psychic, mysterious emotional tone",
}

# Eight lunar phases - Boland Ch.2 (pp.19-26 OCR)
MOON_PHASE_RULES: dict[str, dict] = {
    "New Moon": {
        "keywords": "clean slate, potential, dreams",
        "summary": "Plant seeds; meditate on what you want; avoid dwelling on what you do not want.",
        "dos": [
            ("Write or sketch wishes; read them aloud and feel them fulfilled.", "rules44/Boland New Moon phase"),
            ("Recite the mantra 'I am blessed' at this point in the cycle.", "rules44/Boland New Moon remedy"),
            ("Massage, warm bath, or embodied self-care that reminds you you are alive.", "rules44/Boland New Moon phase"),
        ],
        "donts": [
            ("Do not focus mental energy on fears or what you lack.", "rules44/Boland New Moon phase"),
        ],
        "remedy": "Mantra: I am blessed. Put wishes in writing or a small drawing; feel the wish fulfilled.",
    },
    "Waxing Crescent": {
        "keywords": "courage, moving forwards, faith",
        "summary": "Keep faith as dreams begin to show; revisit New Moon wish lists.",
        "dos": [
            ("Read New Moon wishes aloud; visualize until they feel real.", "rules44/Boland Waxing Crescent"),
            ("Chase what you want with courage - do not quit before you start.", "rules44/Boland Waxing Crescent"),
        ],
        "donts": [
            ("Do not abandon fresh intentions because of fear of failure.", "rules44/Boland Waxing Crescent"),
        ],
        "remedy": "Re-read and speak your wish list; feel the feeling of the wish fulfilled.",
    },
    "First Quarter": {
        "keywords": "challenges, confidence, commitment",
        "summary": "Commit or release; crises may push you to act on dreams.",
        "dos": [
            ("Re-read, re-feel, and re-visualize New Moon wishes; double-commit if still aligned.", "rules44/Boland First Quarter"),
            ("Treat any itch or crisis as a call to take constructive action.", "rules44/Boland First Quarter"),
        ],
        "donts": [
            ("Do not cling to wishes your heart has outgrown - let them go cleanly.", "rules44/Boland First Quarter"),
        ],
        "remedy": "Re-feel your top wish; take one concrete step that proves commitment.",
    },
    "Gibbous Moon": {
        "keywords": "tweak, hone, adjust",
        "summary": "Stay on course; review and refine plans before fullness.",
        "dos": [
            ("Review plans; tweak what is fading and build momentum on what works.", "rules44/Boland Gibbous"),
            ("Restart good habits or routines you let slip.", "rules44/Boland Gibbous"),
        ],
        "donts": [
            ("Do not become impatient or quit when success is near.", "rules44/Boland Gibbous/Lao Tzu"),
        ],
        "remedy": "Spend 10 minutes adjusting one plan; stay as careful at the end as at the start.",
    },
    "Full Moon": {
        "keywords": "results, forgiveness, gratitude",
        "summary": "Emotional peak; release, forgive, then refill with gratitude.",
        "dos": [
            ("Forgive anyone or anything that hurt you in the past month - detoxifying release.", "rules44/Boland Full Moon remedy"),
            ("Count blessings; replace released upset with gratitude.", "rules44/Boland Full Moon remedy"),
        ],
        "donts": [
            ("Do not blame others during release - bless what did not work and move on.", "rules44/Boland Full Moon"),
        ],
        "remedy": "Forgiveness list + gratitude list; let unsettled feelings surface, then let go.",
    },
    "Disseminating Moon": {
        "keywords": "relax, accept, regroup",
        "summary": "Breathe after Full Moon intensity; share wisdom; accept what is.",
        "dos": [
            ("Rest and regroup; share what you learned with someone who can use it.", "rules44/Boland Disseminating"),
            ("Accept where you are - down tools briefly before the next build phase.", "rules44/Boland Disseminating"),
        ],
        "donts": [
            ("Do not launch major new projects - this is waning recovery time.", "rules44/Boland Disseminating"),
        ],
        "remedy": "B-r-e-a-t-h-e; pass on one lesson from the last fortnight.",
    },
    "Third Quarter": {
        "keywords": "re-evaluate, balance, trust",
        "summary": "Crossroads between Full and New; let go to make room.",
        "dos": [
            ("Look back on progress; decide what to carry into the next cycle.", "rules44/Boland Third Quarter"),
            ("Break a bad habit at this turning point.", "rules44/Boland Third Quarter remedy"),
        ],
        "donts": [
            ("Do not rest on laurels - tension here asks for honest adjustment.", "rules44/Boland Third Quarter"),
        ],
        "remedy": "Name one habit to break and one intention to keep for the coming New Moon.",
    },
    "Balsamic Moon": {
        "keywords": "healing, soothing, surrender",
        "summary": "Surrender, rest, dream; prepare softly for the next New Moon.",
        "dos": [
            ("Chant Om Namo Narayani - 'I surrender to the Divine'.", "rules44/Boland Balsamic remedy"),
            ("Rest, daydream, smile; release upset in relationships you wish to keep.", "rules44/Boland Balsamic"),
        ],
        "donts": [
            ("Do not force outcomes - live gently and allow hope to return.", "rules44/Boland Balsamic"),
        ],
        "remedy": "Chant Om Namo Narayani; rest, heal, and end what no longer serves.",
    },
}

# Daily Moon in each sign - Boland Ch.9 (pp.184-193 OCR)
DAILY_MOON_SIGN_RULES: dict[str, dict] = {
    "Aries": {
        "summary": "Emotions run high; channel Mars drive into constructive action, not arguments.",
        "good_for": "Racing through the day.",
        "not_good_for": "Quiet introspection.",
        "do": "Go faster.",
        "dont": "Pick a fight.",
        "remedy": "Take deep breaths before replying; extra meditation/Zen when Moon is in Aries.",
    },
    "Taurus": {
        "summary": "Sensual, relaxing No Rush day; slow steady plod aids goals and abundance visualizations.",
        "good_for": "Relaxing, canoodling, eating, basking.",
        "not_good_for": "Unpleasant tasks.",
        "do": "Indulge your senses and enjoy creature comforts.",
        "dont": "Be stubborn.",
        "remedy": "Massage, tea, or unhurried comfort - watch overeating if weight is a concern.",
    },
    "Gemini": {
        "summary": "Mental buzz - talks, errands, presentations; distinct from Aries action-days.",
        "good_for": "Socializing, thinking, reading, talking.",
        "not_good_for": "Being totally Zen.",
        "do": "Call siblings, parents, or your must-call list.",
        "dont": "Keep gabbing on social media until you embarrass yourself.",
        "remedy": "Use communications gifts for one meaningful conversation, then stop when you know to stop.",
    },
    "Cancer": {
        "summary": "Home-loving, domestic, entrepreneurial underbelly - feather your nest.",
        "good_for": "Baking, staying in, cosy time with loved ones, dynamic planning.",
        "not_good_for": "Being detached, aloof, unemotional.",
        "do": "Spend time with kids you adore; be hospitable; take time out.",
        "dont": "Drag yourself somewhere you do not feel like going unless you must.",
        "remedy": "Tidy home, cook, or name one fear and work on it instead of hiding.",
    },
    "Leo": {
        "summary": "Show-stopper creative day - put your best foot forward with confidence.",
        "good_for": "Partying, performing, making them laugh, being awesome.",
        "not_good_for": "Feeling like a shrinking violet.",
        "do": "Put your best foot forward.",
        "dont": "Fake humility - no one will fall for it today.",
        "remedy": "Organize something fun; let your light show in one creative act.",
    },
    "Virgo": {
        "summary": "Monocle-on efficiency - stock-take, health, routines, complementary care.",
        "good_for": "Releasing addictions, getting life in order, new routines.",
        "not_good_for": "Going wild or reckless.",
        "do": "Be helpful.",
        "dont": "Be too critical.",
        "remedy": "Crunch numbers or start one health routine; see a GP if pain persists.",
    },
    "Libra": {
        "summary": "Partnership, romance, negotiation, wine-and-dine diplomacy.",
        "good_for": "Romance and partnerships of all kinds.",
        "not_good_for": "Being alone.",
        "do": "Be ready to come to an agreement.",
        "dont": "Let your head rule your heart.",
        "remedy": "Shower people you love with love; open one peace-making conversation.",
    },
    "Scorpio": {
        "summary": "Shadow-side sting possible - transformational if handled consciously.",
        "good_for": "Investigating a mystery; focused devotion (not obsession).",
        "not_good_for": "Snooping, bad habits, excess obsession.",
        "do": "Lighten up.",
        "dont": "Give in to the shadow.",
        "remedy": "Meditate if you carry a sharp tongue; tread carefully with short-fuse people.",
    },
    "Sagittarius": {
        "summary": "Jupiter excess and adventure - dream big, travel/study mind, stay grateful.",
        "good_for": "Fun, rolling the dice, first steps, adventure.",
        "not_good_for": "Reining in enthusiasm or limiting yourself.",
        "do": "Go for it - fortune favours Sagittarius.",
        "dont": "Play it cautious.",
        "remedy": "See the big picture; write or plan the book/journey/study you envision.",
    },
    "Capricorn": {
        "summary": "Sensible strategy, career goals, month-ahead planning without killing joy.",
        "good_for": "Achieving career goals.",
        "not_good_for": "Lounging around.",
        "do": "Use the day to get back on your success path.",
        "dont": "Forget to have some fun.",
        "remedy": "Draft month-ahead goals; behave maturely with bosses or as a boss.",
    },
    "Aquarius": {
        "summary": "Progressive, non-conformist, charitable gatherings and forward thinking.",
        "good_for": "Making wishes.",
        "not_good_for": "Doing things the old-fashioned way; halting progress.",
        "do": "Be fashion-forward, forward-thinking, and forward.",
        "dont": "Be surprised if frankness offends - watch your tone.",
        "remedy": "Meet friends for a cause; make one wish aligned with collective good.",
    },
    "Pisces": {
        "summary": "Dreamy, soulful, poetic - spiritual practice over escapist excess.",
        "good_for": "Swimming, dreaming, bathing.",
        "not_good_for": "Rigorous mental/physical work, arguments, being down to earth.",
        "do": "Dream a little or big dream.",
        "dont": "Expect dreams to manifest without concrete follow-through.",
        "remedy": "Meditation or soulful connection; guard against self-pity and addictions.",
    },
}

# Daily Moon in each House - Boland Ch.10 (pp.195+ OCR) - abbreviated action lines
DAILY_MOON_HOUSE_RULES: dict[int, dict] = {
    1: {
        "summary": "Show yourself; feelings at the front door; makeover or self-presentation day.",
        "do": "Deal with feelings openly; refresh appearance if desired.",
        "remedy": "Short self-care or style tweak that matches how you want to be seen.",
    },
    2: {
        "summary": "Money, possessions, self-worth feelings - stay honest about cash flow.",
        "do": "Review spending/saving calmly; affirm your worth.",
        "remedy": "One practical money step (budget line, advisor call, or savings move).",
    },
    3: {
        "summary": "Meaningful conversations, errands, siblings/neighbours, heartfelt writing.",
        "do": "Engage fully; write a heartfelt note.",
        "remedy": "Call or message someone with a sincere, feeling-led conversation.",
    },
    4: {
        "summary": "Home, family, pottering, cooking, introspection on how far you have come.",
        "do": "Stay home if you can; nurture self and family.",
        "remedy": "Cook or tidy one corner of home; private recharge.",
    },
    5: {
        "summary": "Fun, creativity, kids, romance, hobbies - shake off melancholy.",
        "do": "Schedule play, creativity, or romance.",
        "remedy": "Do one thing that makes you laugh or creates joy.",
    },
    6: {
        "summary": "Service, health recommitment, productivity, tidying.",
        "do": "Help others without expecting payback; tidy one area.",
        "remedy": "Recommit to one healthy habit; complete a useful chore.",
    },
    7: {
        "summary": "One-on-one relating - love, business partnerships, seeing the real you.",
        "do": "Slow down with partner or shore up a professional alliance.",
        "remedy": "Quality time or honest talk with an important other.",
    },
    8: {
        "summary": "Depth, intimacy, shared finances, inner shadow work - stay calm.",
        "do": "Deep inner work or calm handling of joint money matters.",
        "remedy": "Address one shared-finance or trust topic without drama.",
    },
    9: {
        "summary": "Escape mentally or literally - expand horizons via travel, study, or foreign flavours.",
        "do": "Broaden perspective; handle legal matters calmly if they arise.",
        "remedy": "Armchair travel, ethnic meal, or one step toward study or journey planning.",
    },
    10: {
        "summary": "Ambition and career feelings surface - recognition, bosses, or your public mark.",
        "do": "Face professional emotions honestly; be fair if you hold authority.",
        "remedy": "One visible career action or conversation about long-term aims.",
    },
    11: {
        "summary": "Friends, groups, and wishes in focus - give and receive within your tribe.",
        "do": "Socialize with allies; revisit whether old dreams still matter.",
        "remedy": "Reach out to a friend group or community you belong to.",
    },
    12: {
        "summary": "Retreat, secrets, and unconscious patterns - ideal for solitude and month review.",
        "do": "Withdraw if possible; journal what may surface when Moon hits your ascendant soon.",
        "remedy": "Quiet hour alone; release a hidden worry without forcing outcomes.",
    },
}

SOURCE_TAG = "rules44/Boland Moonology (Hay House 2016)"
